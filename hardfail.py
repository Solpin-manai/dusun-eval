# -*- coding: utf-8 -*-
"""Find a regime where bare Haiku CLEARLY fails, with exact (no-model) grading.
Two generatable, dial-able, verification-recoverable tasks:
  - state-tracking: apply N list operations, report final list   (dial = N ops)
  - multiply: exact product of two d-digit numbers                (dial = d digits)
Screens bare Haiku across difficulty levels and prints the accuracy ladder."""
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common

HERE = Path(__file__).resolve().parent
M = 6          # instances per difficulty level
TEMP = 1.0
WORKERS = 8

# ---------- generators (ground truth computed in Python) ----------
def gen_statetrack(n_ops, seed):
    rng = random.Random(seed)
    lst = [rng.randint(0, 9) for _ in range(rng.randint(5, 7))]
    start = list(lst)
    instr = []
    for _ in range(n_ops):
        op = rng.choice(["reverse", "append", "pop", "insert", "remove_idx", "swap", "rotate", "replace"])
        if op == "reverse":
            lst.reverse(); instr.append("Reverse the list.")
        elif op == "append":
            x = rng.randint(0, 9); lst.append(x); instr.append("Append %d to the end." % x)
        elif op == "pop" and lst:
            lst.pop(); instr.append("Remove the last element.")
        elif op == "insert":
            x = rng.randint(0, 9); i = rng.randint(1, len(lst) + 1); lst.insert(i - 1, x)
            instr.append("Insert %d at position %d (1-indexed, shifting later elements right)." % (x, i))
        elif op == "remove_idx" and lst:
            i = rng.randint(1, len(lst)); del lst[i - 1]
            instr.append("Remove the element at position %d (1-indexed)." % i)
        elif op == "swap" and len(lst) >= 2:
            i, j = rng.sample(range(1, len(lst) + 1), 2); lst[i - 1], lst[j - 1] = lst[j - 1], lst[i - 1]
            instr.append("Swap the elements at positions %d and %d (1-indexed)." % (i, j))
        elif op == "rotate" and len(lst) >= 2:
            k = rng.randint(1, len(lst) - 1); lst = lst[k:] + lst[:k]
            instr.append("Rotate the list left by %d (move the first %d elements to the end)." % (k, k))
        elif op == "replace" and lst:
            a = rng.choice(lst); b = rng.randint(0, 9); lst = [b if x == a else x for x in lst]
            instr.append("Replace every %d with %d." % (a, b))
        else:
            lst.reverse(); instr.append("Reverse the list.")
    prompt = ("Start with the list %s. Apply the following operations in order:\n%s\n\n"
              "What is the final list? Think step by step, then end your answer with the final "
              "list on its own line in exactly this format:\nFINAL: [a, b, c, ...]"
              % (start, "\n".join("%d. %s" % (k + 1, t) for k, t in enumerate(instr))))
    return prompt, lst

def gen_multiply(n_digits, seed):
    rng = random.Random(seed)
    lo, hi = 10 ** (n_digits - 1), 10 ** n_digits - 1
    a, b = rng.randint(lo, hi), rng.randint(lo, hi)
    prompt = ("Compute the exact product of %d and %d. Do not round or approximate. "
              "End your answer with the result on its own line in exactly this format:\nRESULT: <number>" % (a, b))
    return prompt, a * b

# ---------- exact graders ----------
def grade_statetrack(resp, gold):
    if not resp:
        return False
    m = re.search(r"FINAL:\s*\[([^\]]*)\]", resp, re.I)
    if not m:
        brs = re.findall(r"\[([0-9,\s]*)\]", resp)
        if not brs:
            return False
        body = brs[-1]
    else:
        body = m.group(1)
    try:
        got = [int(x) for x in re.findall(r"-?\d+", body)]
    except Exception:
        return False
    return got == gold

def grade_multiply(resp, gold):
    if not resp:
        return False
    m = re.search(r"RESULT:\s*([\d,\s]+)", resp, re.I)
    cand = m.group(1) if m else (re.findall(r"\d[\d,]{3,}", resp) or [""])[-1]
    digits = re.sub(r"[^\d]", "", cand)
    return digits == str(gold)

LEVELS = {
    "statetrack": [6, 10, 16, 24],
    "multiply":   [3, 5, 8, 13],
}
GEN = {"statetrack": gen_statetrack, "multiply": gen_multiply}
GRADE = {"statetrack": grade_statetrack, "multiply": grade_multiply}

def main():
    jobs = []
    for task, levels in LEVELS.items():
        for lvl in levels:
            for i in range(M):
                prompt, gold = GEN[task](lvl, seed=1000 * lvl + i)
                jobs.append({"task": task, "level": lvl, "i": i, "prompt": prompt, "gold": gold})
    print("hardfail screen: %d items (bare Haiku, exact grading)" % len(jobs), flush=True)

    def work(j):
        try:
            resp = common.call_model(None, j["prompt"], temperature=TEMP, max_tokens=2000)
        except Exception:
            resp = None
        ok = GRADE[j["task"]](resp, j["gold"])
        return {**j, "resp": resp, "correct": 1.0 if ok else 0.0}

    res = list(ThreadPoolExecutor(max_workers=WORKERS).map(work, jobs))
    (HERE / "out").mkdir(exist_ok=True)
    with (HERE / "out" / "hardfail.jsonl").open("w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps({k: r[k] for k in ("task", "level", "i", "gold", "resp", "correct")}, ensure_ascii=False) + "\n")

    print("\n=== bare Haiku accuracy ladder (M=%d per level) ===" % M)
    for task, levels in LEVELS.items():
        print("\n%s  (dial = %s):" % (task, "n_ops" if task == "statetrack" else "n_digits"))
        for lvl in levels:
            xs = [r["correct"] for r in res if r["task"] == task and r["level"] == lvl]
            acc = sum(xs) / len(xs)
            flag = "   <== CLEAR FAILURE" if acc <= 0.34 else ("  <- partial" if acc < 0.84 else "")
            print("   level %-3d  acc=%.2f  (%d/%d)%s" % (lvl, acc, int(sum(xs)), len(xs), flag))

    # show one failing example at the hardest level of each task
    for task, levels in LEVELS.items():
        hard = levels[-1]
        ex = next((r for r in res if r["task"] == task and r["level"] == hard and r["correct"] == 0.0), None)
        if ex:
            print("\n----- example FAIL: %s level %d (gold=%s) -----" % (task, hard, ex["gold"]))
            print((ex["resp"] or "")[-300:])
    print("\nDONE")

if __name__ == "__main__":
    main()
