"""COMMENT-CODE DIVERGENCE — where a comment states a number the code does not use.

THE SHAPE THIS EXISTS FOR. A comment is a CLAIM about the code, and nothing checks it.
Three were found by hand in one session:
  * `database_interface.py:80-81` -- "Checkpoint every 1000 pages ... instead of default
    1000 pages" above `PRAGMA wal_autocheckpoint=100`. Says 1000 TWICE; the code sets 100.
  * `evolution_runner.py:1616` -- "Safe cleanup every 10 generations" calling a function
    whose docstring AND code say every 30.
  * `rungs/exploitation.py` -- `default_priority = 6  # ... before three_try_sequence (8)`
    while the registry registers it at 4 and 5.
A stale comment is not cosmetic: it is the number a reader will believe when deciding
whether a constant is deliberate. **That is exactly the premise pass's input.**

WHAT IT DOES **NOT** DO, STATED SO THE OUTPUT IS NOT OVERREAD. This compares a comment's
integers with the integers on the code it annotates. It is a CANDIDATE FINDER. A comment
can be perfectly true and share no integer with its line (a ratio, a reference to another
module, a unit conversion done in prose), and those show up here as candidates. **Every hit
needs a human read; the value is that the population is small enough to read.**

R4, BOTH WAYS, printed on every run:
  KNOWN-POSITIVE  `wal_autocheckpoint` -- comment says 1000, code says 100. MUST FIRE.
  KNOWN-NEGATIVE  `busy_timeout` -- comment says "5000ms = 5 seconds", code says 5000, three
                  lines above the positive in the same function. MUST STAY CLEAN.
An instrument that only fires proves sensitivity and never specificity.

USAGE
  python tools/comment_divergence.py            # whole repo
  python tools/comment_divergence.py --limit 40
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", ".runs", ".venv", "__pycache__", "node_modules", ".ruff_cache"}

# Only comments that make a QUANTITY CLAIM. Without this the sweep drowns in prose.
QUANTITY = re.compile(
    r"\b(every|each|keep|keeps|top|last|first|limit|limited|max|maximum|min|minimum|"
    r"threshold|timeout|checkpoint|retention|retain|cap|capped|default|pages|rows|lines|"
    r"seconds|ms|generations|records|entries|per)\b", re.I)
INT = re.compile(r"(?<![\w.])(\d{2,7})(?![\w.])")   # >=2 digits: 0/1 are structural noise
# Years, ports and other numbers that are never a tunable claim.
IGNORE_INTS = {"2024", "2025", "2026", "1970", "100000", "utf", "8080"}
# A comment that names a PAST value is not a divergence -- it is provenance, and provenance
# is the thing this project most wants comments to carry. Suppress it explicitly rather than
# letting it inflate the candidate count.
HISTORICAL = re.compile(r"\b(was|were|previously|used to|reduced from|"
                        r"formerly|originally|before)\b", re.I)


def ints(text: str) -> Set[str]:
    return {m for m in INT.findall(text) if m not in IGNORE_INTS}


def strip_comment(line: str) -> Tuple[str, str]:
    """(code_part, comment_part) -- quote-aware enough for the '#' in a string literal."""
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#":
            return line[:i], line[i + 1:]
    return line, ""


def scan_file(path: str) -> List[Tuple[int, str, str, Set[str], Set[str]]]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    out = []
    for i, raw in enumerate(lines):
        code, comment = strip_comment(raw)
        if comment.strip():
            # INLINE: the comment annotates the code on its own line.
            target, tline, tno = code, raw, i + 1
        elif raw.strip().startswith("#"):
            continue     # handled as the "preceding comment" of a later line
        else:
            continue
        if not QUANTITY.search(comment) or HISTORICAL.search(comment):
            continue
        ci, ti = ints(comment), ints(target)
        if ci and ti and not (ci & ti):
            out.append((tno, tline.strip(), comment.strip(), ci, ti))

    # PRECEDING-COMMENT form: a comment line (or block) directly above a code line.
    block: List[str] = []
    for i, raw in enumerate(lines):
        s = raw.strip()
        if s.startswith("#"):
            block.append(s.lstrip("#").strip())
            continue
        if block and s:
            comment = " ".join(block)
            code, _ = strip_comment(raw)
            if QUANTITY.search(comment) and not HISTORICAL.search(comment):
                ci, ti = ints(comment), ints(code)
                if ci and ti and not (ci & ti):
                    out.append((i + 1, s, comment, ci, ti))
        block = []
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=60)
    a = ap.parse_args()

    hits = []
    scanned = 0
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for f in fns:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            scanned += 1
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            for tno, code, comment, ci, ti in scan_file(p):
                hits.append((rel, tno, code, comment, ci, ti))

    print(f"COMMENT-CODE DIVERGENCE — {scanned} files scanned, {len(hits)} candidates\n")
    for rel, tno, code, comment, ci, ti in hits[:a.limit]:
        print(f"{rel}:{tno}")
        print(f"    comment says {sorted(ci)}: {comment[:96]}")
        print(f"    code    uses {sorted(ti)}: {code[:96]}")
    if len(hits) > a.limit:
        print(f"\n... {len(hits) - a.limit} more (raise --limit). NOT TRUNCATED SILENTLY.")

    # ── R4, both directions, on every run ──
    pos = any(r == "database_interface.py" and "wal_autocheckpoint" in c
              for r, _n, c, _cm, _a, _b in hits)
    neg = any(r == "database_interface.py" and "busy_timeout" in c
              for r, _n, c, _cm, _a, _b in hits)
    print("\n" + "-" * 70)
    print(f"R4 KNOWN-POSITIVE (wal_autocheckpoint: comment 1000 vs code 100) must FIRE: "
          f"{'FIRED' if pos else '** DID NOT FIRE - INSTRUMENT SUSPECT **'}")
    print(f"R4 KNOWN-NEGATIVE (busy_timeout: comment 5000 = code 5000) must stay CLEAN: "
          f"{'CLEAN' if not neg else '** FALSE POSITIVE - INSTRUMENT SUSPECT **'}")
    print("CANDIDATES, NOT A CENSUS. A comment can be true and share no integer with its")
    print("line. The point is that the population is now small enough to read by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
