# -*- coding: utf-8 -*-
"""Extract a function from a model response and execute it against test cases
in an isolated subprocess (timeout-guarded). Correctness is GROUND TRUTH."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

_FENCE = re.compile(r"```(?:python)?\s*(.*?)```", re.S | re.I)

def extract_code(resp, name):
    if not resp:
        return ""
    blocks = _FENCE.findall(resp)
    for b in blocks:
        if ("def %s" % name) in b:
            return b
    if blocks:
        return blocks[0]
    if ("def %s" % name) in resp:
        return resp
    return ""

_RUNNER = (
    "import json, sys, importlib.util\n"
    "spec = importlib.util.spec_from_file_location('sol', 'sol.py')\n"
    "m = importlib.util.module_from_spec(spec)\n"
    "try:\n"
    "    spec.loader.exec_module(m)\n"
    "except Exception as e:\n"
    "    print(json.dumps({'err': 'load:' + repr(e)[:120]})); sys.exit()\n"
    "fn = getattr(m, sys.argv[1], None)\n"
    "if fn is None:\n"
    "    print(json.dumps({'err': 'nofunc'})); sys.exit()\n"
    "tests = json.load(open('tests.json', encoding='utf-8'))\n"
    "res = []\n"
    "for args, exp in tests:\n"
    "    try:\n"
    "        res.append(bool(fn(*args) == exp))\n"
    "    except Exception:\n"
    "        res.append(False)\n"
    "print(json.dumps({'res': res}))\n"
)

def run_tests(code, name, tests, timeout=8):
    n_total = len(tests)
    if not code.strip():
        return {"n_pass": 0, "n_total": n_total, "all_pass": False, "error": "no code"}
    d = tempfile.mkdtemp(prefix="ev_")
    try:
        with open(os.path.join(d, "sol.py"), "w", encoding="utf-8") as f:
            f.write(code)
        with open(os.path.join(d, "tests.json"), "w", encoding="utf-8") as f:
            json.dump(tests, f)
        with open(os.path.join(d, "_run.py"), "w", encoding="utf-8") as f:
            f.write(_RUNNER)
        p = subprocess.run([sys.executable, "_run.py", name], cwd=d,
                           capture_output=True, text=True, timeout=timeout)
        lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
        last = lines[-1] if lines else ""
        data = json.loads(last) if last.startswith("{") else {"err": "noout:" + p.stderr[:80]}
        if "res" in data:
            npass = sum(1 for x in data["res"] if x)
            return {"n_pass": npass, "n_total": n_total, "all_pass": npass == n_total, "error": None}
        return {"n_pass": 0, "n_total": n_total, "all_pass": False, "error": data.get("err")}
    except subprocess.TimeoutExpired:
        return {"n_pass": 0, "n_total": n_total, "all_pass": False, "error": "timeout"}
    except Exception as e:
        return {"n_pass": 0, "n_total": n_total, "all_pass": False, "error": repr(e)[:120]}
    finally:
        shutil.rmtree(d, ignore_errors=True)
