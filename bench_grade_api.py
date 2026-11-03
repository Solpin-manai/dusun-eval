"""Grade POWER RUN 2 (API): out/bench_raw_api.jsonl -> out/bench_graded_api.jsonl + summary.

Rules fixed in PRE-REGISTRATION_BENCH.md, "POWER RUN 2 (API)": extraction exactly as the
July grader (`bench_grade.extract`), blind judge claude-opus-5-5 via the API (question, gold,
prediction only; order shuffled with seed 20261103), co-primaries H1a (INCORRECT) and H1b
(CORRECT) by two-sided exact McNemar with Holm across the two. Also writes the 30-item hand
validation sheet (seed 20261103), blind to arm.

Usage: py bench_grade_api.py
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

from bench_grade import JUDGE_SYS, extract

HERE = Path(__file__).resolve().parent
RAW = HERE / "out" / "bench_raw_api.jsonl"
GRADED = HERE / "out" / "bench_graded_api.jsonl"
SUMMARY = HERE / "out" / "bench_summary_api.json"
SHEET = HERE / "out" / "api_handcheck_sheet.json"
LEDGER = HERE / "out" / "api_usage_ledger.jsonl"
BANKS = [HERE / "bench_bank.jsonl", HERE / "bench_bank_pow.jsonl"]
KEY_FILE = os.path.expanduser("~/.niluvera_anthropic.key")
JUDGE = "claude-opus-5-5"
SEED = 20261103


def judge(question, gold, pred):
    if not pred.strip() or pred.strip().upper() == "NOT ATTEMPTED":
        return "NOT_ATTEMPTED"
    user = "QUESTION:\n%s\n\nGOLD ANSWER:\n%s\n\nPREDICTED ANSWER:\n%s\n\nOne word:" % (
        question.split("\n\nAnswer the question")[0], gold, pred)
    key = open(KEY_FILE, encoding="utf-8").read().strip()
    body = json.dumps({"model": JUDGE, "max_tokens": 2000, "system": JUDGE_SYS,
                       "output_config": {"effort": "medium"},
                       "messages": [{"role": "user", "content": user}]}).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
            u = data.get("usage") or {}
            with open(LEDGER, "a", encoding="utf-8") as lf:
                lf.write(json.dumps({"t": time.time(), "model": data.get("model"),
                                     "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
                                     "cr": 0, "cw": 0, "stop": data.get("stop_reason"),
                                     "src": "judge"}) + "\n")
            w = "".join(b.get("text", "") for b in data.get("content", [])
                        if b.get("type") == "text").strip().upper().replace(" ", "_")
            for v in ("NOT_ATTEMPTED", "INCORRECT", "CORRECT"):   # INCORRECT before CORRECT
                if v in w:
                    return v
            return "JUDGE_FAILED"
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504, 529) and attempt < 3:
                time.sleep(15 * (attempt + 1))
                continue
            return "JUDGE_FAILED"
        except Exception:
            time.sleep(10)
    return "JUDGE_FAILED"


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, p)


def main():
    gold = {}
    for b in BANKS:
        for l in b.read_text(encoding="utf-8").splitlines():
            it = json.loads(l)
            gold[it["id"]] = it
    rows = {}
    for l in RAW.read_text(encoding="utf-8").splitlines():
        r = json.loads(l)
        if r.get("ok") or (r["id"], r["arm"]) not in rows:   # a later ok row wins over a failed one
            rows[(r["id"], r["arm"])] = r
    items = sorted({i for i, a in rows if (i, "bare") in rows and (i, "dusun") in rows})
    jobs = [(i, a) for i in items for a in ("bare", "dusun")]
    random.Random(SEED).shuffle(jobs)                        # judge order hides the arm pattern

    graded = {}
    for n, (i, a) in enumerate(jobs, 1):
        r, it = rows[(i, a)], gold[i]
        pred = extract(r) if r.get("ok") else ""
        v = judge(it["question"], it["gold"], pred)
        graded[(i, a)] = dict(id=i, arm=a, ok=r.get("ok"), err=r.get("err"), pred=pred,
                              verdict=v, arbiter=("-- ARBITER" in (r.get("text") or "")) if a == "dusun" else None)
        print("%d/%d judged" % (n, len(jobs)), flush=True)
    with open(GRADED, "w", encoding="utf-8") as f:
        for k in sorted(graded):
            f.write(json.dumps(graded[k], ensure_ascii=False) + "\n")

    def pair(ind):
        b = sum(1 for i in items if ind(graded[(i, "bare")]) and not ind(graded[(i, "dusun")]))
        c = sum(1 for i in items if ind(graded[(i, "dusun")]) and not ind(graded[(i, "bare")]))
        return b, c
    inc_b, inc_d = pair(lambda g: g["verdict"] == "INCORRECT")   # bare-only vs dusun-only wrong
    cor_b, cor_d = pair(lambda g: g["verdict"] == "CORRECT")
    p_a, p_b = mcnemar_exact(inc_b, inc_d), mcnemar_exact(cor_b, cor_d)
    lo, hi = sorted([p_a, p_b])                               # Holm, two hypotheses
    holm = {lo: min(1.0, 2 * lo), hi: max(min(1.0, 2 * lo), hi)}
    per_arm = {a: dict(Counter(graded[(i, a)]["verdict"] for i in items)) for a in ("bare", "dusun")}
    avail = sum(1 for i in items if graded[(i, "dusun")]["arbiter"]) / max(1, len(items))
    out = {"n_items": len(items), "judge": JUDGE, "per_arm": per_arm,
           "H1a_incorrect": {"bare_only": inc_b, "dusun_only": inc_d, "p": p_a, "p_holm": holm[p_a]},
           "H1b_correct": {"bare_only": cor_b, "dusun_only": cor_d, "p": p_b, "p_holm": holm[p_b]},
           "dusun_arbiter_availability": round(avail, 3),
           "inconclusive_availability": avail < 0.80,
           "judge_failed": sum(1 for g in graded.values() if g["verdict"] == "JUDGE_FAILED")}
    SUMMARY.write_text(json.dumps(out, indent=1), encoding="utf-8")

    attempted = [k for k in sorted(graded) if graded[k]["verdict"] in ("CORRECT", "INCORRECT")]
    pick = random.Random(SEED).sample(attempted, min(30, len(attempted)))
    sheet = [{"n": n, "question": gold[i]["question"].split("\n\nAnswer the question")[0],
              "gold": gold[i]["gold"], "pred": graded[(i, a)]["pred"], "judge": graded[(i, a)]["verdict"],
              "_key": "%s|%s" % (i, a)} for n, (i, a) in enumerate(pick, 1)]
    SHEET.write_text(json.dumps(sheet, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
