"""FORK DIVERGENCE — does a fix that was made in one lineage exist in the sibling?

THE SHAPE THIS EXISTS FOR (F-1b): zero-score deletion was found and disabled in one
lineage in February 2026. The SAME bug ate the census in the sibling in August --
re86 112->8, tu93 97->12, four and a half months later. **THE FIX DID NOT CROSS THE FORK,
AND NOTHING NOTICED**, because nothing was looking.

THE ASYMMETRY, WHICH IS STRUCTURAL AND NOT AN OVERSIGHT:
  **DEFECTS PROPAGATE BY INHERITANCE** -- a fork copies everything present at fork time.
  **FIXES PROPAGATE ONLY BY SOMEONE REMEMBERING.**
So divergence grows monotonically in one direction unless an instrument looks.

USAGE
  python tools/fork_divergence.py                       # check against the default sibling
  python tools/fork_divergence.py --other <path>        # explicit
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OTHER = os.path.join(os.path.dirname(ROOT), "Ouroboros")

# (label, file, marker, kind)
#   kind "FIX"    -> present HERE and absent THERE means the fix did not cross
#   kind "DEFECT" -> present in BOTH means the defect is in both lineages
MARKERS: List[Tuple[str, str, str, str]] = [
    ("evidence-rule replaces score (2026-08-13)",
     "safe_cleanup.py", "win_detected = 1", "FIX"),
    ("D-3 verifier counts by evidence (2026-08-18)",
     "safe_cleanup.py", "good_games_evidence_partial", "FIX"),
    ("D-1 checkpoint deletion keyed on SCORE",
     "safe_cleanup.py", "survival_score DESC", "DEFECT"),
    ("D-2 prefix merge deletes the MORE GENERAL rule",
     "safe_cleanup.py", "strict prefix of B", "DEFECT"),
]

# R4: the instrument checks itself before it is read.
KNOWN_POSITIVE = "evidence-rule replaces score (2026-08-13)"   # MUST report NOT CROSSED
KNOWN_NEGATIVE = "D-1 checkpoint deletion keyed on SCORE"      # MUST report BOTH, not a gap


def count(root: str, rel: str, marker: str) -> int:
    p = os.path.join(root, rel)
    if not os.path.exists(p):
        return -1
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read().count(marker)
    except OSError:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--other", default=DEFAULT_OTHER)
    a = ap.parse_args()
    if not os.path.isdir(a.other):
        print(f"sibling not found: {a.other}")
        return 0

    print("FORK DIVERGENCE")
    print(f"  here:    {ROOT}")
    print(f"  sibling: {a.other}\n")
    results = {}
    uncrossed = 0
    for label, rel, marker, kind in MARKERS:
        h, t = count(ROOT, rel, marker), count(a.other, rel, marker)
        if kind == "FIX":
            if h > 0 and t == 0:
                verdict = "** FIX DID NOT CROSS **"
                uncrossed += 1
            elif h > 0 and t > 0:
                verdict = "crossed"
            elif t < 0:
                verdict = "sibling file absent"
            else:
                verdict = "absent here too"
        else:
            if h > 0 and t > 0:
                verdict = "** DEFECT IN BOTH LINEAGES **"
            elif h > 0:
                verdict = "defect here only"
            elif t > 0:
                verdict = "defect in sibling only"
            else:
                verdict = "absent both"
        results[label] = verdict
        print(f"  [{kind:6s}] here={h:<4} sibling={t:<4}  {verdict}")
        print(f"            {label}")

    print(f"\nFIXES THAT DID NOT CROSS: {uncrossed}")
    print("  DEFECTS PROPAGATE BY INHERITANCE. FIXES PROPAGATE ONLY BY SOMEONE")
    print("  REMEMBERING. That asymmetry is why divergence only ever grows.")

    print("\n" + "-" * 70)
    kp = results.get(KNOWN_POSITIVE, "")
    kn = results.get(KNOWN_NEGATIVE, "")
    print(f"R4 KNOWN-POSITIVE (the 08-13 evidence fix must report NOT CROSSED): "
          f"{'FIRED' if 'NOT CROSS' in kp else '** DID NOT FIRE - INSTRUMENT SUSPECT **'}")
    print(f"R4 KNOWN-NEGATIVE (D-1 must report BOTH, never a false gap): "
          f"{'CLEAN' if 'BOTH' in kn else '** MISREPORTED - INSTRUMENT SUSPECT **'}")
    print("CANDIDATES, NOT A CENSUS. A marker is a proxy for a fix, not the fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
