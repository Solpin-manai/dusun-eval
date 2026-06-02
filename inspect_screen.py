# -*- coding: utf-8 -*-
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "out" / "screen_raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def show(idv, n=5):
    rs = [r for r in rows if r["id"] == idv][:n]
    for r in rs:
        print("-" * 70)
        print("%s s%d confab=%s" % (idv, r["sample"], r["confab"]))
        print((r["resp"] or "")[:480])

print("##### C19 Great Wall (0.40 confab) - all 5, see the split #####")
show("C19")
print("\n##### C10 Ada Lovelace (0.20 confab) #####")
show("C10")
print("\n##### 0.00 subtle items - confirm Haiku GENUINELY flags (1 sample each) #####")
for i in ["C04", "C11", "C13", "C22"]:
    show(i, n=1)
