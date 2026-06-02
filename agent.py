# -*- coding: utf-8 -*-
"""Multi-turn tool-use agent loop on Haiku. The model may run_python (execute
arbitrary code to test itself) and submit_solution (declare done). Returns the
submitted code + verification behavior. System prompt = the arm (incl. live dusun hook)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import common
import codeharness

API_URL = "https://api.anthropic.com/v1/messages"

TOOLS = [
    {"name": "run_python",
     "description": "Execute arbitrary Python code and return its stdout and stderr. Use this to experiment with or test your solution before submitting.",
     "input_schema": {"type": "object", "properties": {
         "code": {"type": "string", "description": "Python source to execute."}}, "required": ["code"]}},
    {"name": "submit_solution",
     "description": "Submit your final solution. Call this when you believe the solution is complete and correct. This ends the task.",
     "input_schema": {"type": "object", "properties": {
         "code": {"type": "string", "description": "The complete final Python source containing the required function."}}, "required": ["code"]}},
]

def _exec(code, timeout=8):
    d = tempfile.mkdtemp(prefix="ag_")
    try:
        with open(os.path.join(d, "s.py"), "w", encoding="utf-8") as f:
            f.write(code or "")
        p = subprocess.run([sys.executable, "s.py"], cwd=d, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "")[-1400:]
        err = (p.stderr or "")[-1000:]
        return ("STDOUT:\n%s\nSTDERR:\n%s" % (out, err))[:2500]
    except subprocess.TimeoutExpired:
        return "ERROR: execution timed out (possible infinite loop)"
    except Exception as e:
        return "ERROR: " + repr(e)[:200]
    finally:
        shutil.rmtree(d, ignore_errors=True)

def _post(body, retries=5):
    data = json.dumps(body).encode("utf-8")
    for i in range(retries):
        try:
            req = urllib.request.Request(API_URL, data=data, method="POST", headers={
                "x-api-key": common._key(), "anthropic-version": "2023-06-01",
                "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(2 * (i + 1) + 1); continue
            raise RuntimeError("HTTP %d: %s" % (e.code, e.read().decode("utf-8")[:200]))
        except Exception:
            time.sleep(2 * (i + 1)); continue
    raise RuntimeError("post failed after retries")

def run_episode(arm, task_prompt, name, model=common.GEN_MODEL, max_turns=14, temperature=1.0):
    system = common.arm_system(arm, task_prompt)
    user = (task_prompt + "\n\nYou have two tools: run_python (execute code) and "
            "submit_solution (submit your final code, which ends the task). "
            "You have a limited number of steps, so once your solution works, "
            "call submit_solution to finish.")
    messages = [{"role": "user", "content": user}]
    n_run = 0
    submitted = None
    last_good_code = ""
    last_text = ""
    turns = 0
    while turns < max_turns:
        turns += 1
        body = {"model": model, "max_tokens": 1600, "temperature": temperature,
                "tools": TOOLS, "messages": messages}
        if system:
            body["system"] = system
        resp = _post(body)
        content = resp.get("content", [])
        messages.append({"role": "assistant", "content": content})
        for b in content:
            if b.get("type") == "text":
                last_text = b.get("text", "")
        tool_uses = [b for b in content if b.get("type") == "tool_use"]
        if not tool_uses:
            break
        results = []
        stop = False
        for tu in tool_uses:
            if tu["name"] == "submit_solution":
                submitted = tu["input"].get("code", "")
                results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": "Submitted. Task complete."})
                stop = True
            elif tu["name"] == "run_python":
                n_run += 1
                rc = tu["input"].get("code", "")
                if ("def %s" % name) in rc:
                    last_good_code = rc
                results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": _exec(rc)})
            else:
                results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": "unknown tool"})
        messages.append({"role": "user", "content": results})
        if stop:
            break
    did_submit = bool(submitted)
    # fallback if it never formally submitted: its last working code, else code in final text
    final_code = submitted or last_good_code or codeharness.extract_code(last_text, name) or ""
    return {"arm": arm, "submitted": final_code, "did_submit": did_submit,
            "n_run_python": n_run, "turns": turns}
