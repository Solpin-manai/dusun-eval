"""Shared helpers for the dusun-eval pilot: API key, model call, the four arms.

No absolute paths (protocol rule 3). API key read in-process from Windows
Credential Manager via CredRead -- never written to an env var or the CLI
(the global ANTHROPIC_API_KEY name is deliberately avoided; see memory).
"""
from __future__ import annotations

import ctypes
import importlib.util
import json
import time
import urllib.error
import urllib.request
from ctypes import wintypes
from pathlib import Path

API_URL = "https://api.anthropic.com/v1/messages"
GEN_MODEL = "claude-haiku-4-5-20251001"      # subject under test
GRADER_MODEL = "claude-sonnet-4-6"           # blind grader for F and M
ARMS = ["bare", "generic", "dusun", "plain"]


# ── API key from Credential Manager (in-process only) ──────────────────────
class _CRED(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_char)), ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
    ]


def get_api_key(target: str = "mailer:anthropic") -> str:
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    fn = adv.CredReadW
    fn.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
                   ctypes.POINTER(ctypes.POINTER(_CRED))]
    fn.restype = wintypes.BOOL
    p = ctypes.POINTER(_CRED)()
    if not fn(target, 1, 0, ctypes.byref(p)):
        raise RuntimeError("CredRead failed: %d" % ctypes.get_last_error())
    c = p.contents
    raw = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
    adv.CredFree(p)
    try:
        return raw.decode("utf-16-le").strip()
    except Exception:
        return raw.decode("utf-8").strip()


_KEY = None


def _key() -> str:
    global _KEY
    if _KEY is None:
        _KEY = get_api_key()
    return _KEY


def call_model(system, user, model=GEN_MODEL, temperature=1.0,
               max_tokens=1024, retries=5) -> str:
    body = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
            "messages": [{"role": "user", "content": user}]}
    if system:
        body["system"] = system
    data = json.dumps(body).encode("utf-8")
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(API_URL, data=data, method="POST", headers={
                "x-api-key": _key(), "anthropic-version": "2023-06-01",
                "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                resp = json.loads(r.read().decode("utf-8"))
            return "".join(b.get("text", "") for b in resp.get("content", [])
                           if b.get("type") == "text")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(2 * (i + 1) + 1)
                continue
            detail = ""
            try:
                detail = e.read().decode("utf-8")[:300]
            except Exception:
                pass
            raise RuntimeError("HTTP %d: %s" % (e.code, detail))
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
            continue
    raise RuntimeError("call_model failed after retries: %r" % last)


# ── dusun arm: the REAL production injection, computed per question ─────────
_READING = None


def reading(q: str) -> str:
    """Import the live UserPromptSubmit hook and call its _reading(prompt)."""
    global _READING
    if _READING is None:
        hook = (Path(__file__).resolve().parent.parent
                / "risalian-operator" / "hook" / "dusun_hook.py")
        spec = importlib.util.spec_from_file_location("dusun_hook", hook)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _READING = m._reading
    return _READING(q)


# Generic control: plain-English careful-reasoning + calibration, matched
# in length/intensity to the dusun line but NOT derived from it.
GENERIC = (
    "Think step by step before you answer. Be thorough and double-check your work. "
    "If a question contains a false, impossible, or nonsensical premise, point that "
    "out instead of answering it. State only what you can verify; if you are not "
    "sure, say so."
)

# Plain-language rendering of the dusun line's own content (tests whether the
# terse/mystical encoding, not the ideas, is what helps or hurts on Haiku).
PLAIN = (
    "Approach this with reason but also with intuition and care, not cold logic "
    "alone. Aim to open up and explore the question rather than just hand over a "
    "final verdict. Remember that no answer is ever complete — at least one "
    "aspect will stay unaddressed. Do not mistake the form of an answer for its "
    "truth: verify before claiming anything is correct or settled."
)


def arm_system(arm: str, q: str):
    if arm == "bare":
        return None
    if arm == "generic":
        return GENERIC
    if arm == "plain":
        return PLAIN
    if arm == "dusun":
        return reading(q)
    raise ValueError("unknown arm: %r" % arm)
