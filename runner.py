"""Generation pass: bank x 4 arms x N samples -> out/raw.jsonl (Haiku, temp 1.0)."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import common

HERE = Path(__file__).resolve().parent
BANK = HERE / "bank.jsonl"
OUT = HERE / "out" / "raw.jsonl"
N = 5
TEMP = 1.0
WORKERS = 8


def load_bank():
    return [json.loads(l) for l in BANK.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    items = load_bank()
    jobs = [(it, arm, s) for it in items for arm in common.ARMS for s in range(N)]
    print("%d items x %d arms x %d samples = %d calls"
          % (len(items), len(common.ARMS), N, len(jobs)), flush=True)

    def work(job):
        it, arm, s = job
        sysp = common.arm_system(arm, it["q"])
        resp = common.call_model(sysp, it["q"], temperature=TEMP)
        return {"id": it["id"], "type": it["type"], "arm": arm, "sample": s,
                "question": it["q"], "system": sysp, "response": resp}

    results, done = [], 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, j): j for j in jobs}
        for f in as_completed(futs):
            try:
                results.append(f.result())
            except Exception as e:
                it, arm, s = futs[f]
                results.append({"id": it["id"], "type": it["type"], "arm": arm,
                                "sample": s, "question": it["q"], "system": None,
                                "response": None, "error": str(e)})
            done += 1
            if done % 40 == 0:
                print("  %d/%d" % (done, len(jobs)), flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    errs = sum(1 for r in results if r.get("error"))
    print("wrote %d -> %s (errors=%d)" % (len(results), OUT, errs), flush=True)


if __name__ == "__main__":
    main()
