"""H1 POWER RUN 2 on the Anthropic API (2026-11-03) -- bare vs the real engine, n=200 SimpleQA.

Pre-registered in PRE-REGISTRATION_BENCH.md, section "POWER RUN 2 (API)", committed before
this runner produced its first row. The July runner (bench_runner.py, claude -p on Max) stays
frozen as the record of the first runs.

Arms per item: bare (one Messages call, no system prompt) and dusun (the real engine,
`dusun_engine.py --api --n 3`), both on MODEL. Same raw-row shape as bench_runner.py, so the
grader reads either file.

Spend: every API call (bare here, every engine call via DUSUN_USAGE_LEDGER) appends its token
usage to LEDGER; before each item the runner prices the ledger and stops cleanly once it passes
CAP_USD. Kill switch: bench_data/API_KILL. Resumable: (id, arm) rows already written are
skipped. Items run WORKERS at a time; within an item, bare then dusun.

Usage:
  py bench_runner_api.py --limit 2          # smoke
  py bench_runner_api.py                    # full run
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "dusun-engine" / "dusun_engine.py"
BANKS = [HERE / "bench_bank.jsonl", HERE / "bench_bank_pow.jsonl"]
OUT = HERE / "out" / "bench_raw_api.jsonl"
LEDGER = HERE / "out" / "api_usage_ledger.jsonl"
KILL = HERE / "bench_data" / "API_KILL"      # own switch; July's BENCH_KILL keeps the old runner stopped
KEY_FILE = os.path.expanduser("~/.niluvera_anthropic.key")

MODEL = "claude-opus-4-8"
DUSUN_N = "3"
CAP_USD = 150.0
WORKERS = 3
PRICE = {"in": 5.0, "out": 25.0, "cr": 0.5, "cw": 6.25}   # USD per 1M tokens, claude-opus-4-8
DUSUN_TIMEOUT = 2400

_lock = threading.Lock()


def spent_usd() -> float:
    if not LEDGER.exists():
        return 0.0
    t = 0.0
    for ln in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(ln)
        except Exception:
            continue
        t += sum(r.get(k, 0) * PRICE[k] for k in PRICE) / 1e6
    return t


def bare_call(prompt: str):
    key = open(KEY_FILE, encoding="utf-8").read().strip()
    body = json.dumps({"model": MODEL, "max_tokens": 2048,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
            u = data.get("usage") or {}
            with _lock, open(LEDGER, "a", encoding="utf-8") as lf:
                lf.write(json.dumps({"t": time.time(), "model": data.get("model"),
                                     "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
                                     "cr": u.get("cache_read_input_tokens", 0) or 0,
                                     "cw": u.get("cache_creation_input_tokens", 0) or 0,
                                     "stop": data.get("stop_reason"), "src": "bare"}) + "\n")
            if data.get("model") != MODEL:
                return "", "served by %s, not %s" % (data.get("model"), MODEL)
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            return (text.strip(), None) if text.strip() else ("", "empty text, stop=%s" % data.get("stop_reason"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504, 529) and attempt < 3:
                time.sleep(15 * (attempt + 1))
                continue
            return "", "HTTP %d: %s" % (e.code, e.read().decode("utf-8", "replace")[:160])
        except Exception as e:
            if attempt < 3:
                time.sleep(10)
                continue
            return "", repr(e)
    return "", "retries exhausted"


def dusun_call(question: str):
    stamp = "%d_%d" % (int(time.time() * 1000), threading.get_ident())
    outfile = HERE / "out" / ("dusun_api_tmp_%s.txt" % stamp)
    qfile = HERE / "out" / ("dusun_api_q_%s.txt" % stamp)
    env = dict(os.environ, DUSUN_API_KEY_FILE=KEY_FILE, DUSUN_API_NO_FALLBACK="1", DUSUN_API_CLI_PARITY="1",
               DUSUN_USAGE_LEDGER=str(LEDGER))
    try:
        qfile.write_text(question, encoding="utf-8")
        cmd = [sys.executable, str(ENGINE), "--api", "--model", MODEL, "--n", DUSUN_N,
               "--question-file", str(qfile), "--out", str(outfile)]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=DUSUN_TIMEOUT, env=env)
        text = outfile.read_text(encoding="utf-8", errors="replace").strip() if outfile.exists() else ""
        if not text:
            text = (p.stdout or "").strip()
        if not text:
            return "", "empty engine output (rc=%d) %s" % (p.returncode, (p.stderr or "")[:200])
        return text, None
    except subprocess.TimeoutExpired:
        return "", "timeout (%ds)" % DUSUN_TIMEOUT
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
                if r.get("ok"):
                    done.add((r["id"], r["arm"]))
            except Exception:
                pass
    return done


def emit(row):
    with _lock, open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


STOP = threading.Event()


def run_item(idx, n, it, done):
    for arm in ("bare", "dusun"):
        if STOP.is_set() or KILL.exists():
            return
        if (it["id"], arm) in done:
            continue
        if spent_usd() >= CAP_USD:
            print("CAP reached (%.2f >= %.2f USD) -- stopping cleanly." % (spent_usd(), CAP_USD), flush=True)
            STOP.set()
            return
        t0 = time.time()
        text, err = bare_call(it["question"]) if arm == "bare" else dusun_call(it["question"])
        emit({"id": it["id"], "cls": it["cls"], "arm": arm, "k": 0, "ok": err is None, "err": err,
              "secs": round(time.time() - t0, 1), "text": text, "model": MODEL, "backend": "api"})
        print("[%d/%d] %s %s %s (%.0fs) spent=%.2f" % (idx + 1, n, it["id"], arm,
              "ok" if err is None else "ERR:" + str(err)[:80], time.time() - t0, spent_usd()), flush=True)


def main():
    global CAP_USD, OUT
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    if "--out" in args:                       # smoke rows never enter the measured file
        OUT = HERE / "out" / args[args.index("--out") + 1]
    if "--cap" in args:
        CAP_USD = float(args[args.index("--cap") + 1])
    items = []
    for b in BANKS:
        items += [json.loads(l) for l in b.read_text(encoding="utf-8").splitlines()]
    items = [i for i in items if i["cls"] == "sqa"]
    if limit:
        items = items[:limit]
    OUT.parent.mkdir(exist_ok=True)
    done = load_done()
    print("bench_runner_api: %d items, %d rows done, model=%s, cap=%.2f USD, spent so far=%.2f"
          % (len(items), len(done), MODEL, CAP_USD, spent_usd()), flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(run_item, idx, len(items), it, done) for idx, it in enumerate(items)]
        for f in futs:
            try:
                f.result()
            except Exception as e:                # a worker crash is reported, never swallowed
                print("WORKER ERROR: %r" % (e,), flush=True)
    print("bench_runner_api: %s. spent=%.2f USD" % ("STOPPED at cap" if STOP.is_set() else "complete",
                                                     spent_usd()), flush=True)


if __name__ == "__main__":
    main()
