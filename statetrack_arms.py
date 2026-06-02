# -*- coding: utf-8 -*-
"""The dusun test on the verify-recoverable failing regime: state-tracking @ 50 ops.
Paired design: every arm sees the same K problems, N samples each. Exact grading."""
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common
import hardfail

HERE = Path(__file__).resolve().parent
OPS = 50
K = 10          # distinct problems (shared across arms)
N = 6           # samples per (problem, arm)
MAXTOK = 8000
TEMP = 1.0
WORKERS = 8

INSTANCES = [hardfail.gen_statetrack(OPS, seed=4242 + i) for i in range(K)]  # (prompt, gold)

def has_final(resp):
    return bool(re.search(r"FINAL:\s*\[", resp or "", re.I))

def work(job):
    idx, arm, s = job
    prompt, gold = INSTANCES[idx]
    sysp = common.arm_system(arm, prompt)
    try:
        resp = common.call_model(sysp, prompt, temperature=TEMP, max_tokens=MAXTOK)
    except Exception as e:
        resp = None
    return {"idx": idx, "arm": arm, "sample": s,
            "correct": 1.0 if hardfail.grade_statetrack(resp, gold) else 0.0,
            "final": 1.0 if has_final(resp) else 0.0}

def main():
    jobs = [(idx, arm, s) for idx in range(K) for arm in common.ARMS for s in range(N)]
    print("statetrack_arms: %d problems x %d arms x %d = %d calls (50 ops each)" % (K, len(common.ARMS), N, len(jobs)), flush=True)
    res = []
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(work, jobs):
            res.append(r); done += 1
            if done % 40 == 0:
                print("  %d/%d" % (done, len(jobs)), flush=True)
    (HERE / "out").mkdir(exist_ok=True)
    with (HERE / "out" / "statetrack_arms.jsonl").open("w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def m(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    print("\n=== state-tracking @ %d ops: accuracy by arm (K=%d problems, N=%d) ===" % (OPS, K, N))
    for a in common.ARMS:
        xs = [r["correct"] for r in res if r["arm"] == a]
        fr = [r["final"] for r in res if r["arm"] == a]
        n = len(xs); acc = m(xs)
        se = (acc * (1 - acc) / n) ** 0.5 if n else 0
        print("  %-9s acc=%.3f  +/-%.3f  (n=%d, has_FINAL=%.2f)" % (a, acc, se, n, m(fr)))

    print("\n=== per-problem accuracy (bare vs dusun) ===")
    print("%-5s %-7s %-9s %-7s %-7s" % ("prob", "bare", "generic", "dusun", "plain"))
    cell = defaultdict(list)
    for r in res:
        cell[(r["idx"], r["arm"])].append(r["correct"])
    for idx in range(K):
        print("%-5d %-7.2f %-9.2f %-7.2f %-7.2f" % (idx, m(cell[(idx, "bare")]), m(cell[(idx, "generic")]), m(cell[(idx, "dusun")]), m(cell[(idx, "plain")])))
    print("\nDONE")

if __name__ == "__main__":
    main()
