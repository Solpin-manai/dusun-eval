# -*- coding: utf-8 -*-
import json
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "out" / "multiply_arms.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

print("calibration label distribution (1.0=calibrated/good, 0.0=overconfident):")
for arm in ["bare", "generic", "dusun", "plain"]:
    print("  %-9s %s" % (arm, dict(Counter(r["calib"] for r in rows if r["arm"] == arm))))

random.seed(3)
cal = [r for r in rows if r["calib"] == 1.0]
over = [r for r in rows if r["calib"] == 0.0]

print("\n===== grader said CALIBRATED (good) — validate: do these flag uncertainty? =====")
for r in random.sample(cal, min(5, len(cal))):
    print("\n[%s] %s" % (r["arm"], r["head"][:500].replace("\n", " ")))

print("\n\n===== grader said OVERCONFIDENT — validate: do these assert a confident product? =====")
for r in random.sample(over, min(5, len(over))):
    print("\n[%s] %s" % (r["arm"], r["head"][:500].replace("\n", " ")))
