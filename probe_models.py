# -*- coding: utf-8 -*-
"""Are weaker Claude models reachable on this key? (headroom for the hook to help)"""
import common
for m in ["claude-3-5-haiku-20241022", "claude-3-5-haiku-latest",
          "claude-3-haiku-20240307", "claude-3-opus-20240229"]:
    try:
        r = common.call_model(None, "Reply with just: OK", model=m, max_tokens=5)
        print("OK   ", m, "->", repr(r[:20]))
    except Exception as e:
        print("FAIL ", m, "->", str(e)[:140])
