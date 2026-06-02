# -*- coding: utf-8 -*-
"""The actual 4-arm dusun test on hard multi-constraint reasoning items.
bare / generic / dusun(live hook) / plain  x N samples; correctness via blind Sonnet grader.
The 'bare' column doubles as the difficulty screen."""
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common

HERE = Path(__file__).resolve().parent
N = 8
TEMP = 1.0
WORKERS = 8

def main():
    items = [json.loads(l) for l in (HERE / "bank_hard.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    byid = {it["id"]: it for it in items}
    jobs = [(it, arm, s) for it in items for arm in common.ARMS for s in range(N)]
    print("hard_arms: %d items x %d arms x %d samples = %d calls" % (len(items), len(common.ARMS), N, len(jobs)), flush=True)

    def gen(job):
        it, arm, s = job
        sysp = common.arm_system(arm, it["q"])
        try:
            resp = common.call_model(sysp, it["q"], temperature=TEMP, max_tokens=1200)
        except Exception as e:
            resp = None
        return {"id": it["id"], "arm": arm, "sample": s, "q": it["q"], "gold": it["gold"], "resp": resp}

    raw = list(ThreadPoolExecutor(max_workers=WORKERS).map(gen, jobs))

    def grade(rec):
        if not rec["resp"]:
            return {**rec, "correct": None}
        out = common.call_model(
            "You are a strict grader. Reply with exactly one word: CORRECT or WRONG.",
            "Question:\n%s\n\nThe correct answer is: %s\n\nAI response:\n%s\n\nIs the AI's FINAL answer "
            "correct (matches the correct answer, allowing equivalent wording/order)? Reply CORRECT or WRONG."
            % (rec["q"], rec["gold"], rec["resp"]),
            model=common.GRADER_MODEL, temperature=0, max_tokens=5)
        return {**rec, "correct": 1.0 if out.strip().upper().startswith("C") else 0.0}

    graded = list(ThreadPoolExecutor(max_workers=WORKERS).map(grade, raw))
    (HERE / "out").mkdir(exist_ok=True)
    with (HERE / "out" / "hard_arms.jsonl").open("w", encoding="utf-8") as f:
        for r in graded:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cell = defaultdict(list)
    for r in graded:
        if r["correct"] is not None:
            cell[(r["id"], r["arm"])].append(r["correct"])

    def m(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    # overall per arm
    overall = {a: m([r["correct"] for r in graded if r["arm"] == a and r["correct"] is not None]) for a in common.ARMS}
    print("\n=== OVERALL correctness by arm (N=%d, %d items) ===" % (N, len(items)))
    print("  ".join("%s=%.3f" % (a, overall[a]) for a in common.ARMS))

    # per-item table (focus: items with bare < 1.0 = real headroom)
    print("\n=== per-item correctness (bare is the screen) ===")
    print("%-5s %-6s %-8s %-7s %-7s  %s" % ("id", "bare", "generic", "dusun", "plain", "gold"))
    head = []
    for it in items:
        i = it["id"]
        b = m(cell[(i, "bare")]); g = m(cell[(i, "generic")]); d = m(cell[(i, "dusun")]); p = m(cell[(i, "plain")])
        mark = "  <==headroom" if b < 1.0 else ""
        print("%-5s %-6.2f %-8.2f %-7.2f %-7.2f  %s%s" % (i, b, g, d, p, it["gold"], mark))
        if b < 1.0:
            head.append(it["id"])

    # restricted to headroom items only
    if head:
        print("\n=== restricted to HEADROOM items only (bare<1.0): %s ===" % ", ".join(head))
        for a in common.ARMS:
            xs = [r["correct"] for r in graded if r["arm"] == a and r["id"] in head and r["correct"] is not None]
            print("  %-8s %.3f (n=%d)" % (a, m(xs), len(xs)))
    print("\nDONE")

if __name__ == "__main__":
    main()
