# -*- coding: utf-8 -*-
import json
from collections import defaultdict
from pathlib import Path
import common

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "out" / "hard_arms.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

print("total rows:", len(rows))
for arm in common.ARMS:
    xs = [r["correct"] for r in rows if r["arm"] == arm and r["correct"] is not None]
    print("  %-8s overall=%.3f n=%d" % (arm, sum(xs) / len(xs), len(xs)))

print("\n--- the live dusun injection for H10 ---")
h10q = next(r["q"] for r in rows if r["id"] == "H10")
print(common.reading(h10q))

print("\n--- H10 dusun samples (correct flag :: response tail) ---")
for r in [x for x in rows if x["id"] == "H10" and x["arm"] == "dusun"]:
    resp = (r["resp"] or "")
    print("\n[correct=%s] ...%s" % (r["correct"], resp[-320:].replace("\n", " ")))
