# -*- coding: utf-8 -*-
"""Deep state-tracking ladder: find an op-count where bare Haiku CLEARLY fails
AND the failure is genuine reasoning error (not output truncation). This is the
verification-recoverable regime where a 'verify before done' nudge has a mechanism."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common
import hardfail

HERE = Path(__file__).resolve().parent
LEVELS = [30, 40, 50, 60]
M = 8
TEMP = 1.0
WORKERS = 8
MAXTOK = 8000

def has_final(resp):
    return bool(re.search(r"FINAL:\s*\[", resp or "", re.I))

def main():
    jobs = []
    for lvl in LEVELS:
        for i in range(M):
            prompt, gold = hardfail.gen_statetrack(lvl, seed=9000 * lvl + i)
            jobs.append({"level": lvl, "i": i, "prompt": prompt, "gold": gold})
    print("statetrack deep screen: %d items (bare Haiku)" % len(jobs), flush=True)

    def work(j):
        try:
            resp = common.call_model(None, j["prompt"], temperature=TEMP, max_tokens=MAXTOK)
        except Exception:
            resp = None
        return {**j, "resp": resp, "correct": 1.0 if hardfail.grade_statetrack(resp, j["gold"]) else 0.0,
                "final": 1.0 if has_final(resp) else 0.0}

    res = list(ThreadPoolExecutor(max_workers=WORKERS).map(work, jobs))
    (HERE / "out").mkdir(exist_ok=True)
    with (HERE / "out" / "hardfail2.jsonl").open("w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps({k: r[k] for k in ("level", "i", "gold", "resp", "correct", "final")}, ensure_ascii=False) + "\n")

    print("\n=== bare Haiku state-tracking deep ladder (M=%d) ===" % M)
    print("%-7s %-8s %-12s %s" % ("n_ops", "acc", "has_FINAL", "verdict"))
    for lvl in LEVELS:
        xs = [r["correct"] for r in res if r["level"] == lvl]
        fs = [r["final"] for r in res if r["level"] == lvl]
        acc = sum(xs) / len(xs); fr = sum(fs) / len(fs)
        if fr < 0.7:
            verdict = "(truncation confound - low FINAL rate)"
        elif acc <= 0.34:
            verdict = "<== CLEAR reasoning FAILURE (good dusun regime)"
        elif acc < 0.84:
            verdict = "<- partial"
        else:
            verdict = ""
        print("%-7d %-8.2f %-12.2f %s" % (lvl, acc, fr, verdict))
    print("\nDONE")

if __name__ == "__main__":
    main()
