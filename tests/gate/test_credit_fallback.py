"""3b3: credit is NON-DROPPABLE — a real level-up must always leave a trace.

Two live trials dropped real level-ups: first the click path (no centroid on click games),
then the movement path (the level-up step carries the NEW level's first frame and the pick
fails exactly then). The rule completed: click coords -> current centroid -> LAST-KNOWN
centroid -> bare LEVEL mint. Source-contract tests; the live half is the standing conditional
live-wire falsifier.
"""
from __future__ import annotations
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _src():
    return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                errors="replace").read()


def test_the_credit_branch_keeps_a_pre_overwrite_centroid():
    src = _src()
    assert "_ego_last_known_cen" in src, (
        "no last-known-centroid retention -- the level-up step's broken pick still drops "
        "movement rewards (the pop3b3 mechanism, unfixed)")


def test_the_bare_level_mint_exists():
    src = _src()
    assert '"LEVEL"' in src or "'LEVEL'" in src, (
        "no bare LEVEL mint -- a level-up with no attributable cell still leaves zero trace "
        "in the fabric")
    i = src.find("LEVEL\"") if '"LEVEL"' in src else src.find("LEVEL'")
    window = src[max(0, i - 1500):i]
    assert "level_changed" in window, "the bare mint must live inside the level-up branch"
