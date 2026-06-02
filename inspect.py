# -*- coding: utf-8 -*-
"""Sample-validate the graded output: read real responses, judge grader labels."""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
graded = [json.loads(l) for l in (HERE / "out" / "graded.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def show(idv, arm="bare", s=0):
    for r in graded:
        if r["id"] == idv and r["arm"] == arm and r["sample"] == s:
            print("=" * 72)
            print("%s [%s] score=%s metric=%s" % (idv, arm, r["score"], r.get("metric")))
            print("Q:", r["question"])
            print("A:", (r["response"] or "")[:1000])
            return

print("##### FALSE-PREMISE (F) — bare arm, sample 0 — should be FLAGGED if confab=0 #####")
for i in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
    show(i)

print("\n\n##### REASONING (R) — bare arm, sample 0 — the hard traps #####")
for i in ["R1", "R4", "R7", "R8"]:
    show(i)

print("\n\n##### distributions across ALL cells #####")
for t in ["F", "R", "M"]:
    c = Counter(r["score"] for r in graded if r["type"] == t)
    print(t, "score dist:", dict(sorted(c.items())))
