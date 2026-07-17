# -*- coding: utf-8 -*-
"""SELF-HEALING SUPERVISOR for the H1 power run (2026-07-17).

Context: the overnight run hit the account's HOURLY rate limit (~21:27) and the
runner recorded 48 bare-error + 48 hollow-dusun rows that the resume logic would
otherwise treat as "done" forever. This supervisor, launched in a CLEAN context
by a scheduled task (claude -p 401s if nested in a live Claude Code session):

  loop:
    1. clean poisoned/incomplete rows out of bench_raw_pow.jsonl (keep only items
       whose bare is ok AND dusun is ok AND dusun is NOT hollow),
    2. if 150 clean items -> DONE,
    3. run bench_runner.py once (it now FAIL-FASTs on a spend-limit/hollow hit),
    4. if progress was made -> loop again immediately (window is open),
       else -> sleep SLEEP_S (window still closed) and retry.

Robust to whatever the real reset period is: it just retries until the calls
succeed or the safety caps trip. Writes a status line each pass to resume_pow.log
and a final marker to POW_DONE / POW_STUCK.
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = Path(__file__).resolve().parent
RAW = HERE / "out" / "bench_raw_pow.jsonl"
LOG = HERE / "resume_pow.log"
DONE = HERE / "out" / "POW_DONE"
STUCK = HERE / "out" / "POW_STUCK"
TARGET = 150
SLEEP_S = 1200            # 20 min between retries when the window is still closed
MAX_ITERS = 18           # ~6 h of retries worst case
MAX_WALL_S = 6 * 3600


def log(msg: str):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] %s" % (stamp, msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def hollow(t: str) -> bool:
    t = (t or "").lower()
    return ("spend limit" in t) or ("0/3 faculties returned" in t)


def clean_and_count() -> int:
    """Remove poisoned/incomplete rows; return count of clean items."""
    if not RAW.exists():
        return 0
    rows = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
    item: dict = {}
    for r in rows:
        item.setdefault(r["id"], {})[r["arm"]] = r
    clean_ids = set()
    for iid, d in item.items():
        b, dd = d.get("bare"), d.get("dusun")
        if b and b["ok"] and dd and dd["ok"] and not hollow(dd.get("text", "")):
            clean_ids.add(iid)
    kept = [r for r in rows if r["id"] in clean_ids]
    RAW.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept),
                   encoding="utf-8")
    return len(clean_ids)


def run_once() -> None:
    cmd = [sys.executable, str(HERE / "bench_runner.py"),
           "--bank", "bench_bank_pow.jsonl", "--out", "bench_raw_pow.jsonl"]
    log("launching bench_runner pass ...")
    p = subprocess.run(cmd, cwd=str(HERE), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    tail = "\n".join((p.stdout or "").splitlines()[-3:])
    log("bench_runner returned rc=%d; tail: %s" % (p.returncode, tail.replace("\n", " | ")))


def main():
    t0 = time.time()
    for it in DONE, STUCK:
        try: it.unlink()
        except FileNotFoundError: pass
    log("supervisor start; target=%d clean SQA pairs" % TARGET)
    for i in range(MAX_ITERS):
        n = clean_and_count()
        log("iter %d: %d/%d clean after cleaning" % (i, n, TARGET))
        if n >= TARGET:
            DONE.write_text("%d clean at %s\n" % (n, time.strftime("%Y-%m-%d %H:%M:%S")),
                            encoding="utf-8")
            log("DONE: %d/%d clean." % (n, TARGET))
            return
        if time.time() - t0 > MAX_WALL_S:
            break
        run_once()
        after = clean_and_count()
        log("iter %d: %d -> %d clean after pass" % (i, n, after))
        if after >= TARGET:
            DONE.write_text("%d clean at %s\n" % (after, time.strftime("%Y-%m-%d %H:%M:%S")),
                            encoding="utf-8")
            log("DONE: %d/%d clean." % (after, TARGET))
            return
        if after <= n:                       # no progress -> window still closed
            log("no progress -> sleeping %ds for the rate window to reset" % SLEEP_S)
            time.sleep(SLEEP_S)
        # else: progress made, loop immediately
    STUCK.write_text("stopped at %d/%d clean at %s\n"
                     % (clean_and_count(), TARGET, time.strftime("%Y-%m-%d %H:%M:%S")),
                     encoding="utf-8")
    log("STUCK: hit caps before reaching target; left file clean for a later resume.")


if __name__ == "__main__":
    main()
