"""
novelty_ledger.py -- the second honesty tripwire. A NOVEL mint is the ONE verdict the build must never
self-certify (Tether: the frontier is exactly where an LLM would smuggle an answer, and the LLM building this is
its own judge there). So a NOVEL predicate is not promoted on the build's say-so: it is APPENDED to a durable,
append-only claims file flagged UNCONFIRMED, and the build may treat it as real only after a HUMAN moves its key
into the confirmations file. The build writes claims; only a human writes confirmations.

`guarded_promote()` is the gate every promotion path must go through: it records the claim and returns whether the
build is ALLOWED to act on it (True only if a human has confirmed). RE-DERIVATION verdicts pass through untouched --
they invent nothing, so there is nothing to certify.
"""
from __future__ import annotations
import json
import os
import hashlib
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_DOCS = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "docs"))
CLAIMS_PATH = os.path.join(_DOCS, "NOVELTY_CLAIMS.jsonl")        # append-only, build-written, git-tracked
CONFIRMED_PATH = os.path.join(_DOCS, "NOVELTY_CONFIRMED.txt")    # human-written ONLY (one claim key per line)


def claim_key(name: str, game: str) -> str:
    return hashlib.sha1(("%s|%s" % (name, game)).encode("utf-8")).hexdigest()[:12]


def record_novelty_claim(name: str, bits: float, game: str, context: str = "",
                         claims_path: str = CLAIMS_PATH) -> str:
    """Append an UNCONFIRMED novelty claim. Idempotent-ish (append-only log; dedup is on read). Returns the key."""
    key = claim_key(name, game)
    rec = dict(key=key, name=name, bits=float(bits), game=game, context=context, status="UNCONFIRMED")
    os.makedirs(os.path.dirname(claims_path), exist_ok=True)
    with open(claims_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return key


def is_confirmed(name: str, game: str, confirmed_path: str = CONFIRMED_PATH) -> bool:
    """True only if a HUMAN has written this claim's key into the confirmations file."""
    key = claim_key(name, game)
    if not os.path.exists(confirmed_path):
        return False
    for line in open(confirmed_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and line.split()[0] == key:
            return True
    return False


def guarded_promote(verdict: str, name: str, bits: float, game: str, context: str = "",
                    claims_path: str = CLAIMS_PATH, confirmed_path: str = CONFIRMED_PATH) -> bool:
    """The promotion gate. Returns whether the build MAY act on this mint as a genuine novelty.
    - RE-DERIVATION (or anything not NOVEL): returns True -- it invents nothing new to certify.
    - NOVEL: records an UNCONFIRMED claim and returns True ONLY if a human already confirmed it; else False (parked).
    """
    if verdict != "NOVEL":
        return True
    record_novelty_claim(name, bits, game, context, claims_path=claims_path)
    return is_confirmed(name, game, confirmed_path=confirmed_path)
