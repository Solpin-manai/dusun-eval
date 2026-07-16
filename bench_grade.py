"""Grade out/bench_raw.jsonl -> out/bench_graded.jsonl + out/bench_summary.json.

Math: mechanical exact-match on the extracted FINAL integer (no judge, no bias).
SimpleQA: blind judge (claude -p, Haiku on Max) sees ONLY question/gold/prediction —
  never the arm — and returns CORRECT / INCORRECT / NOT_ATTEMPTED (SimpleQA rubric).
selfcons3: majority vote over the 3 extracted answers (ties -> first-sample answer;
  pre-registered).
dusun extraction: FINAL is searched ONLY in the ARBITER section of the run text
  (faculties may emit their own FINAL lines under the shared adapter instruction;
  attributing a faculty's answer to the engine would mis-grade it). No FINAL in the
  arbiter section = unanswered (math: wrong; sqa: NOT_ATTEMPTED). Pre-registered.

MUST run from a clean context (the sqa judge is a claude -p call).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "out" / "bench_raw.jsonl"
GRADED = HERE / "out" / "bench_graded.jsonl"
SUMMARY = HERE / "out" / "bench_summary.json"
BANK = HERE / "bench_bank.jsonl"

JUDGE_MODEL = "claude-haiku-4-5-20251001"
FINAL_RE = re.compile(r"FINAL:\s*(.+?)\s*$", re.I | re.M)
ARBITER_MARK = "-- ARBITER"

import os


def find_claude() -> str:
    cand = os.path.expandvars(r"%APPDATA%\npm\claude.cmd")
    return cand if os.path.exists(cand) else "claude"


CLAUDE = find_claude()
LEAN = ["--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--setting-sources", "project", "--no-session-persistence"]

JUDGE_SYS = (
    "You grade a predicted answer against a gold answer for a short factual "
    "question. Reply with EXACTLY ONE WORD:\n"
    "CORRECT - the prediction fully contains the gold answer's information, "
    "contradicting nothing (formatting/casing/extra detail is fine).\n"
    "INCORRECT - the prediction contradicts the gold answer or states a different one.\n"
    "NOT_ATTEMPTED - the prediction declines to answer / says it does not know.\n"
    "Do not reward confidence; judge content only."
)


def judge_sqa(question: str, gold: str, pred: str) -> str:
    if pred.strip().upper() == "NOT ATTEMPTED" or not pred.strip():
        return "NOT_ATTEMPTED"
    user = "QUESTION:\n%s\n\nGOLD ANSWER:\n%s\n\nPREDICTED ANSWER:\n%s\n\nOne word:" % (
        question.split("\n\nAnswer the question")[0], gold, pred)
    cmd = [CLAUDE, "-p", "--model", JUDGE_MODEL] + LEAN
    try:
        p = subprocess.run(cmd, input=JUDGE_SYS + "\n\n" + user, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=300)
        w = (p.stdout or "").strip().upper()
        for v in ("CORRECT", "INCORRECT", "NOT_ATTEMPTED"):
            if v in w.replace(" ", "_"):
                return v
    except Exception:
        pass
    return "JUDGE_FAILED"


def extract(row: dict) -> str:
    """Extract the FINAL answer per the pre-registered rules."""
    text = row.get("text") or ""
    if row["arm"] == "dusun":
        i = text.find(ARBITER_MARK)
        text = text[i:] if i >= 0 else ""   # no arbiter section -> unanswered
    m = FINAL_RE.findall(text)
    return m[-1].strip() if m else ""


def norm_int(s: str) -> str:
    m = re.search(r"-?\d+", s.replace(",", ""))
    return str(int(m.group())) if m else ""


def main():
    gold = {json.loads(l)["id"]: json.loads(l) for l in
            BANK.read_text(encoding="utf-8").splitlines()}
    rows = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines()]

    # collapse selfcons samples -> one majority row per item
    sc = defaultdict(list)
    singles = []
    for r in rows:
        if r["arm"] == "selfcons":
            sc[r["id"]].append(r)
        else:
            singles.append(r)

    graded = []
    for r in singles:
        it = gold[r["id"]]
        pred = extract(r) if r["ok"] else ""
        g = dict(id=r["id"], cls=r["cls"], arm=r["arm"], ok=r["ok"],
                 err=r.get("err"), secs=r.get("secs"), pred=pred)
        if it["cls"] == "math":
            g["verdict"] = ("CORRECT" if pred and norm_int(pred) == it["gold"]
                            else "INCORRECT")
        else:
            g["verdict"] = judge_sqa(it["question"], it["gold"], pred)
        graded.append(g)
        print(r["id"], r["arm"], g["verdict"], flush=True)

    for iid, samples in sorted(sc.items()):
        it = gold[iid]
        preds = [norm_int(extract(s)) if s["ok"] else "" for s in
                 sorted(samples, key=lambda x: x.get("k", 0))]
        counts = Counter(p for p in preds if p)
        if counts:
            top, n = counts.most_common(1)[0]
            maj = top if n > 1 else preds[0] if preds[0] else top
        else:
            maj = ""
        g = dict(id=iid, cls=it["cls"], arm="selfcons3",
                 ok=any(s["ok"] for s in samples), err=None, pred=maj,
                 samples=preds,
                 verdict="CORRECT" if maj and maj == it["gold"] else "INCORRECT")
        graded.append(g)
        print(iid, "selfcons3", g["verdict"], preds, flush=True)

    with open(GRADED, "w", encoding="utf-8") as f:
        for g in graded:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")

    # summary
    summ = defaultdict(lambda: Counter())
    for g in graded:
        summ["%s/%s" % (g["cls"], g["arm"])][g["verdict"]] += 1
    out = {k: dict(v) for k, v in sorted(summ.items())}
    SUMMARY.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
