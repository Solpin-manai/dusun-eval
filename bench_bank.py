"""Build bench_bank.jsonl for the 2026-07 REAL-ENGINE benchmark eval.

Sources (public, fetched 2026-07-16 into bench_data/):
  - math-ai/aime25 (HF, 30 items, AIME 2025 I+II, integer answers)
  - Maxwell-Jia/AIME_2024 (HF, 30 items, AIME 2024 I+II, integer answers)
  - simple_qa_test_set.csv (OpenAI public blob, 4326 rows) -> stratified 50-item sample

Deterministic: seed fixed, sample reproducible. No absolute paths (protocol rule 3).
"""
from __future__ import annotations

import ast
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "bench_data"
SEED = 20260716
N_SQA = 50

# The adapter instruction is IDENTICAL for every arm (pre-registered).
MATH_SUFFIX = (
    "\n\nSolve the problem. The answer is an integer between 0 and 999. "
    "End your response with a line of exactly this form:\nFINAL: <integer>"
)
SQA_SUFFIX = (
    "\n\nAnswer the question concisely. If you do not know the answer or cannot "
    "state it with confidence, end your response with the line:\nFINAL: NOT ATTEMPTED\n"
    "Otherwise end your response with a line of exactly this form:\nFINAL: <answer>"
)


def main():
    items = []

    d25 = json.loads((DATA / "math-ai_aime25.json").read_text(encoding="utf-8"))
    for r in d25["rows"]:
        row = r["row"]
        items.append({
            "id": "aime25-%s" % row["id"], "cls": "math",
            "question": row["problem"].strip() + MATH_SUFFIX,
            "gold": str(int(str(row["answer"]).strip())),
            "meta": {"src": "math-ai/aime25"},
        })

    d24 = json.loads((DATA / "Maxwell-Jia_AIME_2024.json").read_text(encoding="utf-8"))
    for r in d24["rows"]:
        row = r["row"]
        items.append({
            "id": "aime24-%s" % row["ID"], "cls": "math",
            "question": row["Problem"].strip() + MATH_SUFFIX,
            "gold": str(int(str(row["Answer"]).strip())),
            "meta": {"src": "Maxwell-Jia/AIME_2024"},
        })

    # SimpleQA: stratified by topic, deterministic.
    by_topic = defaultdict(list)
    with open(DATA / "simple_qa_test_set.csv", encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            try:
                topic = ast.literal_eval(row["metadata"]).get("topic", "?")
            except Exception:
                topic = "?"
            by_topic[topic].append((i, row))
    rng = random.Random(SEED)
    topics = sorted(by_topic)
    quota, rem = divmod(N_SQA, len(topics))
    picked = []
    for t in topics:
        pool = sorted(by_topic[t], key=lambda x: x[0])
        k = quota + (1 if topics.index(t) < rem else 0)
        picked += rng.sample(pool, min(k, len(pool)))
    for i, row in sorted(picked, key=lambda x: x[0]):
        items.append({
            "id": "sqa-%d" % i, "cls": "sqa",
            "question": row["problem"].strip() + SQA_SUFFIX,
            "gold": row["answer"].strip(),
            "meta": {"src": "simpleqa", "row": i},
        })

    out = HERE / "bench_bank.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    n_math = sum(1 for i in items if i["cls"] == "math")
    n_sqa = sum(1 for i in items if i["cls"] == "sqa")
    print("wrote %s: %d items (%d math, %d sqa), seed=%d" %
          (out.name, len(items), n_math, n_sqa, SEED))


if __name__ == "__main__":
    main()
