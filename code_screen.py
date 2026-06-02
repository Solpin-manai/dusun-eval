# -*- coding: utf-8 -*-
"""Screen coding tasks against BARE Haiku: keep tasks it actually fails (headroom)."""
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common
import codeharness

HERE = Path(__file__).resolve().parent
N = 5
TEMP = 1.0
WORKERS = 8
KEEP_MAX = 0.6  # keep tasks where bare all-pass rate <= 0.6 (fails fully >= 2/5)

def main():
    bank = sys.argv[1] if len(sys.argv) > 1 else "bank_code.jsonl"
    tag = sys.argv[2] if len(sys.argv) > 2 else "code"
    items = [json.loads(l) for l in (HERE / bank).read_text(encoding="utf-8").splitlines() if l.strip()]
    byid = {it["id"]: it for it in items}
    jobs = [(it, s) for it in items for s in range(N)]
    print("code screen: %d tasks x %d bare samples = %d calls" % (len(items), N, len(jobs)), flush=True)

    def gen(job):
        it, s = job
        try:
            resp = common.call_model(None, it["q"], temperature=TEMP, max_tokens=1400)
        except Exception:
            resp = None
        return {"id": it["id"], "name": it["name"], "sample": s, "resp": resp, "tests": it["tests"]}

    raw = list(ThreadPoolExecutor(max_workers=WORKERS).map(gen, jobs))

    def grade(r):
        code = codeharness.extract_code(r["resp"], r["name"])
        res = codeharness.run_tests(code, r["name"], r["tests"])
        return {**r, "code": code, "n_pass": res["n_pass"], "n_total": res["n_total"],
                "all_pass": res["all_pass"], "err": res["error"]}

    graded = list(ThreadPoolExecutor(max_workers=WORKERS).map(grade, raw))

    (HERE / "out").mkdir(exist_ok=True)
    with (HERE / "out" / ("%s_screen.jsonl" % tag)).open("w", encoding="utf-8") as f:
        for r in graded:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ap = defaultdict(list)
    pf = defaultdict(list)
    for r in graded:
        ap[r["id"]].append(1.0 if r["all_pass"] else 0.0)
        pf[r["id"]].append(r["n_pass"] / r["n_total"])
    rows = sorted(((i, sum(ap[i]) / len(ap[i]), sum(pf[i]) / len(pf[i])) for i in ap), key=lambda x: x[1])

    print("\n=== bare-Haiku coding result per task (N=%d) ===" % N)
    print("%-5s %-9s %-10s %s" % ("id", "all_pass", "testfrac", "function"))
    keep = []
    for iid, apr, pfr in rows:
        it = byid[iid]
        mark = "  <== HEADROOM" if apr <= KEEP_MAX else ""
        print("%-5s %-9.2f %-10.2f %s%s" % (iid, apr, pfr, it["name"], mark))
        if apr <= KEEP_MAX:
            keep.append(it)

    hardname = "hard_%s_bank.jsonl" % tag
    with (HERE / hardname).open("w", encoding="utf-8") as f:
        for it in keep:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print("\nKEPT (bare all_pass <= %.1f): %d  ->  %s" % (KEEP_MAX, len(keep), hardname))

if __name__ == "__main__":
    main()
