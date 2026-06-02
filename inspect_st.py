# -*- coding: utf-8 -*-
"""Validate state-tracking ground truth: independently re-derive each instance's
final list by PARSING the rendered instruction text (a different code path than
the generator), and compare to the generator's gold. Catches wording/op mismatch."""
import ast
import re

import hardfail

def parse_apply(start, lines):
    lst = list(start)
    for line in lines:
        if line.startswith("Reverse"):
            lst.reverse()
        elif line.startswith("Append"):
            lst.append(int(re.search(r"Append (\d+)", line).group(1)))
        elif line.startswith("Remove the last"):
            if lst:
                lst.pop()
        elif line.startswith("Insert"):
            m = re.search(r"Insert (\d+) at position (\d+)", line)
            lst.insert(int(m.group(2)) - 1, int(m.group(1)))
        elif line.startswith("Remove the element at position"):
            p = int(re.search(r"position (\d+)", line).group(1))
            del lst[p - 1]
        elif line.startswith("Swap"):
            m = re.search(r"positions (\d+) and (\d+)", line)
            i, j = int(m.group(1)) - 1, int(m.group(2)) - 1
            lst[i], lst[j] = lst[j], lst[i]
        elif line.startswith("Rotate"):
            k = int(re.search(r"left by (\d+)", line).group(1))
            lst = lst[k:] + lst[:k]
        elif line.startswith("Replace"):
            m = re.search(r"Replace every (\d+) with (\d+)", line)
            a, b = int(m.group(1)), int(m.group(2))
            lst = [b if x == a else x for x in lst]
    return lst

allok = True
for i in range(10):
    prompt, gold = hardfail.gen_statetrack(50, seed=4242 + i)
    start = ast.literal_eval(re.search(r"Start with the list (\[[^\]]*\])", prompt).group(1))
    lines = re.findall(r"^\d+\.\s*(.*)$", prompt, re.M)
    indep = parse_apply(start, lines)
    ok = indep == gold
    allok = allok and ok
    print("prob %d: ops=%d gen_gold=%s indep=%s  %s" % (i, len(lines), gold, indep, "OK" if ok else "*** MISMATCH ***"))
print("\nALL GROUND TRUTH VALID:" , allok)
