# -*- coding: utf-8 -*-
"""Difficulty screen: run BARE Haiku x N on candidate items, grade confabulation
with the blind Sonnet grader, and keep only items bare Haiku actually fails.
Output: hard_bank.jsonl (confab rate >= THRESH) -> the bank with real headroom."""
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common
import grader

HERE = Path(__file__).resolve().parent
CAND = HERE / "bank_calib.jsonl"
N = 5
TEMP = 1.0
WORKERS = 8
THRESH = 0.4  # keep items where bare Haiku confabulates on >= 2 of 5

def main():
    items = [json.loads(l) for l in CAND.read_text(encoding="utf-8").splitlines() if l.strip()]
    byid = {it["id"]: it for it in items}
    jobs = [(it, s) for it in items for s in range(N)]
    print("screen: %d candidates x %d bare samples = %d calls" % (len(items), N, len(jobs)), flush=True)

    def gen(job):
        it, s = job
        try:
            resp = common.call_model(None, it["q"], temperature=TEMP)  # BARE arm
            return {"id": it["id"], "sample": s, "q": it["q"], "truth": it["grade"]["truth"], "resp": resp, "err": None}
        except Exception as e:
            return {"id": it["id"], "sample": s, "q": it["q"], "truth": it["grade"]["truth"], "resp": None, "err": str(e)}

    raw = list(ThreadPoolExecutor(max_workers=WORKERS).map(gen, jobs))

    def gr(r):
        if r["err"] or not r["resp"]:
            return {**r, "confab": None}
        c = grader.grade_f(r["q"], r["resp"], r["truth"])
        return {**r, "confab": 1.0 if c else 0.0}

    graded = list(ThreadPoolExecutor(max_workers=WORKERS).map(gr, raw))

    (HERE / "out").mkdir(exist_ok=True)
    with (HERE / "out" / "screen_raw.jsonl").open("w", encoding="utf-8") as f:
        for r in graded:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    agg = defaultdict(list)
    for r in graded:
        if r["confab"] is not None:
            agg[r["id"]].append(r["confab"])
    rows = sorted(((iid, sum(v) / len(v), len(v)) for iid, v in agg.items()), key=lambda x: -x[1])

    print("\n=== bare-Haiku CONFAB rate per candidate (N=%d; 1.0 = always fooled) ===" % N)
    print("%-5s %-7s %-9s %s" % ("id", "confab", "subtype", "question"))
    hard = []
    for iid, rate, n in rows:
        it = byid[iid]
        mark = "  <== HARD" if rate >= THRESH else ""
        print("%-5s %-7.2f %-9s %s%s" % (iid, rate, it.get("subtype", ""), it["q"][:62], mark))
        if rate >= THRESH:
            hard.append(it)

    with (HERE / "hard_bank.jsonl").open("w", encoding="utf-8") as f:
        for it in hard:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print("\nHARD items (confab >= %.1f): %d  ->  hard_bank.jsonl" % (THRESH, len(hard)))
    print("(if too few, lower THRESH or add candidates)")

if __name__ == "__main__":
    main()
