# -*- coding: utf-8 -*-
"""Probe documented hard-question techniques against BARE Haiku to find one that
reliably fails (the precondition for a meaningful dusun test)."""
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common

HERE = Path(__file__).resolve().parent
N = 8
TEMP = 1.0
WORKERS = 8

CANDS = [
    {"id": "RIVER", "technique": "misleading-variant / unpuzzle",
     "q": "A farmer is standing on a riverbank with a fox, a chicken, and a bag of grain. He has a large boat that can carry himself and all three of the items together in a single trip. What is the minimum number of boat trips across the river he needs to get himself and all three items to the other side?",
     "gold": "1 trip (the boat holds everything, so he crosses once)"},
    {"id": "AIW", "technique": "Alice in Wonderland relational reasoning",
     "q": "Alice has 3 brothers and 2 sisters. How many sisters does Alice's brother have?",
     "gold": "3 (Alice's 2 sisters plus Alice herself)"},
    {"id": "WEIGHT", "technique": "misleading equal-weight trick",
     "q": "Which is heavier: two pounds of feathers, or one pound of bricks?",
     "gold": "the two pounds of feathers (2 lb > 1 lb)"},
    {"id": "DISTRACT", "technique": "irrelevant numeric distractors",
     "q": "Liam buys 5 apples for $2 each. Two of the apples are smaller than the others, and he also brought 3 oranges from home. How much did Liam pay for the apples?",
     "gold": "$10"},
]

def gen(job):
    c, s = job
    try:
        r = common.call_model(None, c["q"], temperature=TEMP, max_tokens=900)
    except Exception:
        r = None
    return {"id": c["id"], "sample": s, "q": c["q"], "gold": c["gold"], "resp": r}

def grade(rec):
    if not rec["resp"]:
        return {**rec, "correct": None}
    out = common.call_model(
        "You are a strict grader. Reply with exactly one word: CORRECT or WRONG.",
        "Question:\n%s\n\nThe correct answer is: %s\n\nAI response:\n%s\n\nIs the AI's FINAL "
        "answer correct (matches the correct answer, allowing equivalent wording)? Reply CORRECT or WRONG."
        % (rec["q"], rec["gold"], rec["resp"]),
        model=common.GRADER_MODEL, temperature=0, max_tokens=5)
    return {**rec, "correct": 1.0 if out.strip().upper().startswith("C") else 0.0}

def main():
    jobs = [(c, s) for c in CANDS for s in range(N)]
    raw = list(ThreadPoolExecutor(max_workers=WORKERS).map(gen, jobs))
    graded = list(ThreadPoolExecutor(max_workers=WORKERS).map(grade, raw))
    (HERE / "out").mkdir(exist_ok=True)
    with (HERE / "out" / "hardprobe.jsonl").open("w", encoding="utf-8") as f:
        for r in graded:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    agg = defaultdict(list)
    for r in graded:
        if r["correct"] is not None:
            agg[r["id"]].append(r["correct"])
    byid = {c["id"]: c for c in CANDS}
    print("\n=== bare Haiku on documented hard-question techniques (N=%d) ===" % N)
    print("%-9s %-9s %-7s %s" % ("id", "correct", "FAIL", "technique"))
    for cid in [c["id"] for c in CANDS]:
        v = agg.get(cid, [])
        cr = sum(v) / len(v) if v else float("nan")
        print("%-9s %-9.2f %-7.2f %s" % (cid, cr, 1 - cr, byid[cid]["technique"]))

    for cid in [c["id"] for c in CANDS]:
        print("\n----- %s (gold: %s) -----" % (cid, byid[cid]["gold"]))
        for r in [x for x in graded if x["id"] == cid][:3]:
            print("[correct=%s] %s" % (r["correct"], (r["resp"] or "")[:260].replace("\n", " ")))

if __name__ == "__main__":
    main()
