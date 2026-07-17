"""REAL-ENGINE benchmark runner — bare / selfcons3 / dusun on Max via claude -p.

MUST run from a CLEAN context (terminal or scheduled task): `claude -p` 401s when
nested inside a live Claude Code session (verified 2026-05-30, dusun-engine gotchas).

Design (pre-registered in PRE-REGISTRATION_BENCH.md — read it first):
  - Arms per item: bare (1 call) on all items; selfcons3 (3 independent bare samples,
    majority at grade time) on MATH items only; dusun (the REAL engine,
    `py dusun_engine.py --n 3 <q>`) on all items.
  - Item-interleaved order (bare -> selfcons -> dusun per item) so all arms sample
    the same hours of the account's throttle state.
  - Incremental + resumable: out/bench_raw.jsonl keyed (id, arm, k); completed keys
    are skipped on restart. Kill switch: bench_data/BENCH_KILL (checked between calls).
  - Every failure is recorded as a row (ok=false, err=...), never silently dropped.

Usage:
  py bench_runner.py                # full run
  py bench_runner.py --limit 2      # smoke: first 2 items only
  py bench_runner.py --cls math     # one class only
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "dusun-engine" / "dusun_engine.py"
BANK = HERE / "bench_bank.jsonl"
OUT = HERE / "out" / "bench_raw.jsonl"
KILL = HERE / "bench_data" / "BENCH_KILL"

MODEL = "claude-opus-4-8"          # subject model, BOTH arms (paired design)
DUSUN_N = "3"                      # first 3 faculties (P3), per refgate-eval precedent
BARE_TIMEOUT = 1500                # s; AIME items can think for minutes
DUSUN_TIMEOUT = 2400               # s; engine bounds its own arbiter phase (v0.20)
LEAN = ["--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--setting-sources", "project", "--no-session-persistence"]


def find_claude() -> str:
    cand = os.path.expandvars(r"%APPDATA%\npm\claude.cmd")
    return cand if os.path.exists(cand) else "claude"


CLAUDE = find_claude()


def bare_call(prompt: str, timeout: int = BARE_TIMEOUT):
    """One claude -p call. Returns (text, err)."""
    cmd = [CLAUDE, "-p", "--model", MODEL] + LEAN
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        out = (p.stdout or "").strip()
        if p.returncode != 0:
            return "", "rc=%d %s" % (p.returncode, (out or p.stderr or "")[:200])
        if not out:
            return "", "empty stdout"
        return out, None
    except subprocess.TimeoutExpired:
        return "", "timeout (%ds)" % timeout
    except Exception as e:
        return "", repr(e)


def dusun_call(question: str, timeout: int = DUSUN_TIMEOUT):
    """One REAL engine run. Returns (full_run_text, err). The question goes via
    --question-file (LaTeX/$/newlines survive; raw argv on Windows would not) and
    the run body comes back via --out (robust to console encoding). The engine
    also writes its own runs/<ts>.txt as usual."""
    stamp = int(time.time() * 1000)
    outfile = HERE / "out" / ("dusun_tmp_%d.txt" % stamp)
    qfile = HERE / "out" / ("dusun_q_%d.txt" % stamp)
    try:
        qfile.parent.mkdir(exist_ok=True)
        qfile.write_text(question, encoding="utf-8")
        cmd = [sys.executable, str(ENGINE), "--n", DUSUN_N,
               "--question-file", str(qfile), "--out", str(outfile)]
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        text = ""
        if outfile.exists():
            text = outfile.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            text = (p.stdout or "").strip()
        if not text:
            return "", "empty engine output (rc=%d) %s" % (
                p.returncode, (p.stderr or "")[:200])
        return text, None
    except subprocess.TimeoutExpired:
        return "", "timeout (%ds)" % timeout
    except Exception as e:
        return "", repr(e)
    finally:
        for f in (outfile, qfile):
            try:
                f.unlink()
            except Exception:
                pass


def load_done():
    done = set()
    if OUT.exists():
        for ln in OUT.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
                done.add((r["id"], r["arm"], r.get("k", 0)))
            except Exception:
                pass
    return done


def emit(row: dict):
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    global BANK, OUT
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    only_cls = args[args.index("--cls") + 1] if "--cls" in args else None
    if "--bank" in args:                      # power run: separate bank + raw file
        BANK = HERE / args[args.index("--bank") + 1]
    if "--out" in args:
        OUT = HERE / "out" / args[args.index("--out") + 1]
    print("bank=%s out=%s" % (BANK.name, OUT.name), flush=True)

    items = [json.loads(l) for l in BANK.read_text(encoding="utf-8").splitlines()]
    if only_cls:
        items = [i for i in items if i["cls"] == only_cls]
    if limit:
        items = items[:limit]
    done = load_done()
    print("bench_runner: %d items, %d rows already done, model=%s"
          % (len(items), len(done), MODEL), flush=True)

    for idx, it in enumerate(items):
        plan = [("bare", 1)]
        if it["cls"] == "math":
            plan.append(("selfcons", 3))
        plan.append(("dusun", 1))
        for arm, n_samples in plan:
            for k in range(n_samples):
                if KILL.exists():
                    print("KILL file present -- stopping cleanly.", flush=True)
                    return
                key = (it["id"], arm, k)
                if key in done:
                    continue
                t0 = time.time()
                if arm == "dusun":
                    text, err = dusun_call(it["question"])
                else:
                    text, err = bare_call(it["question"])
                emit({"id": it["id"], "cls": it["cls"], "arm": arm, "k": k,
                      "ok": err is None, "err": err, "secs": round(time.time() - t0, 1),
                      "text": text})
                print("[%d/%d] %s %s k=%d %s (%.0fs)" % (
                    idx + 1, len(items), it["id"], arm, k,
                    "ok" if err is None else "ERR:" + str(err)[:60],
                    time.time() - t0), flush=True)
                # FAIL-FAST on the hourly spend-limit (2026-07-17): a bare call
                # returns err "…spend limit…"; a dusun call returns non-empty but
                # HOLLOW text (all faculties errored → "0/3 faculties returned").
                # Abort the pass immediately so the supervisor can re-clean the
                # just-emitted bad row and retry after the window resets, instead
                # of grinding the whole remaining bank into hollow rows.
                low_err = str(err).lower() if err else ""
                low_txt = (text or "").lower()
                if ("spend limit" in low_err or "spend limit" in low_txt
                        or "0/3 faculties returned" in low_txt):
                    print("SPEND-LIMIT/hollow detected -- aborting pass for "
                          "supervisor retry.", flush=True)
                    return
    print("bench_runner: complete.", flush=True)


if __name__ == "__main__":
    main()
