# -*- coding: utf-8 -*-
"""Run the multi-turn agent across 4 arms; grade submitted code on a HIDDEN suite.
Usage: agent_run.py [smoke]"""
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common
import agent
import codeharness

HERE = Path(__file__).resolve().parent
N = 5
WORKERS = 6

def load():
    return [json.loads(l) for l in (HERE / "bank_agent.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def episode_and_grade(it, arm, s):
    ep = agent.run_episode(arm, it["q"], it["name"])
    res = codeharness.run_tests(ep["submitted"], it["name"], it["tests"])
    return {"id": it["id"], "arm": arm, "sample": s, "did_submit": ep["did_submit"],
            "n_run_python": ep["n_run_python"], "turns": ep["turns"],
            "all_pass": res["all_pass"], "n_pass": res["n_pass"], "n_total": res["n_total"],
            "code": ep["submitted"]}

def smoke():
    it = load()[3]  # AG4 roman strict (verification matters)
    print("SMOKE: %s [bare]" % it["id"], flush=True)
    r = episode_and_grade(it, "bare", 0)
    print({k: r[k] for k in ("id", "arm", "did_submit", "n_run_python", "turns", "all_pass", "n_pass", "n_total")})
    print("--- submitted code (head) ---")
    print((r["code"] or "")[:600])

def main():
    items = load()
    jobs = [(it, arm, s) for it in items for arm in common.ARMS for s in range(N)]
    print("agent_run: %d tasks x %d arms x %d = %d episodes" % (len(items), len(common.ARMS), N, len(jobs)), flush=True)
    results = []
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(episode_and_grade, it, arm, s) for (it, arm, s) in jobs]
        for f in futs:
            results.append(f.result())
            done += 1
            if done % 20 == 0:
                print("  %d/%d" % (done, len(jobs)), flush=True)
    (HERE / "out").mkdir(exist_ok=True)
    with (HERE / "out" / "agent_runs.jsonl").open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    def m(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    print("\n=== AGENT results by arm (N=%d, %d tasks) ===" % (N, len(items)))
    print("%-9s %-10s %-10s %-12s %-12s" % ("arm", "all_pass", "testfrac", "run_python", "premature"))
    for a in common.ARMS:
        rs = [r for r in results if r["arm"] == a]
        allp = m([1.0 if r["all_pass"] else 0.0 for r in rs])
        frac = m([r["n_pass"] / r["n_total"] for r in rs])
        runs = m([r["n_run_python"] for r in rs])
        prem = m([1.0 if (r["did_submit"] and not r["all_pass"]) else 0.0 for r in rs])
        print("%-9s %-10.3f %-10.3f %-12.2f %-12.3f" % (a, allp, frac, runs, prem))

    print("\n=== per-task all_pass by arm ===")
    print("%-6s %-7s %-9s %-7s %-7s" % ("id", "bare", "generic", "dusun", "plain"))
    cell = defaultdict(list)
    for r in results:
        cell[(r["id"], r["arm"])].append(1.0 if r["all_pass"] else 0.0)
    for it in items:
        i = it["id"]
        print("%-6s %-7.2f %-9.2f %-7.2f %-7.2f" % (i, m(cell[(i, "bare")]), m(cell[(i, "generic")]), m(cell[(i, "dusun")]), m(cell[(i, "plain")])))
    print("\nDONE")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        smoke()
    else:
        main()
