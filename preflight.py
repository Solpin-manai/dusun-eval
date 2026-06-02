# -*- coding: utf-8 -*-
"""Preflight: validate model IDs, the live dusun hook, and end-to-end calls."""
import json, urllib.request
import common

def list_models():
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/models?limit=100",
        headers={"x-api-key": common._key(), "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return [m["id"] for m in json.loads(r.read().decode("utf-8"))["data"]]

ids = list_models()
print("GEN_MODEL   ", common.GEN_MODEL, "present:", common.GEN_MODEL in ids)
print("GRADER_MODEL", common.GRADER_MODEL, "present:", common.GRADER_MODEL in ids)
print("haiku ids :", [i for i in ids if "haiku" in i])
print("sonnet ids:", [i for i in ids if "sonnet" in i])

try:
    r = common.reading("In what year did Einstein win the Nobel Prize for relativity?")
    print("\n--- reading() OK, len=%d ---" % len(r))
    print(r[:700])
except Exception as e:
    import traceback; print("reading() FAILED:", repr(e)); traceback.print_exc()

try:
    a = common.call_model(None, "Say OK.", max_tokens=10)
    print("\nHaiku end-to-end OK:", repr(a[:60]))
except Exception as e:
    print("Haiku FAILED:", repr(e))

try:
    a = common.call_model("Reply one word.", "Reply READY.",
                          model=common.GRADER_MODEL, temperature=0, max_tokens=5)
    print("Grader end-to-end OK:", repr(a[:60]))
except Exception as e:
    print("Grader FAILED:", repr(e))
