# -*- coding: utf-8 -*-
"""Round 2: NOVEL (non-canonical) instances of the documented techniques."""
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
    {"id": "BATBALL", "technique": "misleading lure (resembles famous bat-and-ball)",
     "q": "A bat and a ball cost $1.15 in total. The bat costs $1.00. How much does the ball cost?",
     "gold": "$0.15"},
    {"id": "TOMMARY", "technique": "novel relational reasoning",
     "q": "Tom has twice as many sisters as he has brothers. His sister Mary has the same number of brothers as she has sisters. How many boys and how many girls are in the family?",
     "gold": "3 boys and 4 girls"},
    {"id": "COINS", "technique": "novel 'all but' counting",
     "q": "I have a collection of coins, each of which is a quarter, a dime, or a nickel. All but 4 of them are quarters, all but 4 of them are dimes, and all but 4 of them are nickels. How many coins do I have in total?",
     "gold": "6"},
    {"id": "DISTRACT2", "technique": "multi-step with multiple distractors",
     "q": "A baker has 8 trays and bakes 12 cookies on each tray. Three of the trays are blue, and the shop is open 7 days a week. If he packs the cookies into boxes that hold 5 cookies each, how many full boxes can he pack from one complete batch?",
     "gold": "19"},
    {"id": "SOCKS_RED", "technique": "color-specific twist on the sock-pair puzzle",
     "q": "A drawer contains 6 red socks and 8 blue socks, all mixed together. In complete darkness, how many socks must you take out to be guaranteed of having a matching pair of RED socks?",
     "gold": "10"},
]

def gen(job):
    c, s = job
    try:
        r = common.call_model(None, c["q"], temperature=TEMP, max_tokens=1000)
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
    with (HERE / "out" / "hardprobe2.jsonl").open("w", encoding="utf-8") as f:
        for r in graded:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    agg = defaultdict(list)
    for r in graded:
        if r["correct"] is not None:
            agg[r["id"]].append(r["correct"])
    byid = {c["id"]: c for c in CANDS}
    print("\n=== bare Haiku on NOVEL hard constructions (N=%d) ===" % N)
    print("%-10s %-9s %-7s %s" % ("id", "correct", "FAIL", "technique"))
    for cid in [c["id"] for c in CANDS]:
        v = agg.get(cid, [])
        cr = sum(v) / len(v) if v else float("nan")
        flag = "  <== HOLDS (fails)" if (1 - cr) >= 0.4 else ""
        print("%-10s %-9.2f %-7.2f %s%s" % (cid, cr, 1 - cr, byid[cid]["technique"], flag))

    for cid in [c["id"] for c in CANDS]:
        print("\n----- %s (gold: %s) -----" % (cid, byid[cid]["gold"]))
        for r in [x for x in graded if x["id"] == cid][:3]:
            print("[correct=%s] %s" % (r["correct"], (r["resp"] or "")[:280].replace("\n", " ")))

if __name__ == "__main__":
    main()
