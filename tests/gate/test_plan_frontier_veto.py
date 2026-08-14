"""B3 GATE (BUILD_PROGRAM_2 W1): the planner-DRIVE frontier veto (audit-note fix).

⭐ WHY. The [PLAN] DRIVE site emits a verified click with NO frontier consult —
a plan can drive straight onto a cell the population banked as fatal. B3 checks
the frontier avoid-set / merged-dead cells BEFORE emitting the click; a banked
fatal/dead target falls back to shadow narration instead of driving.

THE CONTRACT: `plan_veto(site, harvest, avoid)` (engines.egocentric.frontier) is
a PURE predicate — True iff the planned target sits in the harvest's fatal/dead
sets or the banked avoid-set; None/empty inputs never veto; it never raises.
Wiring: the [PLAN] DRIVE branch requires `not plan_veto(...)`; the else branch
is the existing shadow narration.

Run pre-build: failed (function absent; DRIVE site consults nothing).
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _veto():
    try:
        from engines.egocentric.frontier import plan_veto
    except Exception as e:
        pytest.fail("frontier.plan_veto missing (%s) — B3 has not landed" % e)
    return plan_veto


class TestTheVeto:

    def test_a_banked_fatal_target_is_vetoed(self):
        assert _veto()((3, 3), {"fatal": {(3, 3)}, "dead": set()}) is True

    def test_a_merged_dead_target_is_vetoed(self):
        assert _veto()((5, 5), {"fatal": set(), "dead": {(5, 5)}}) is True

    def test_the_avoid_set_vetoes_without_a_loaded_harvest(self):
        assert _veto()((7, 7), None, avoid={(7, 7)}) is True

    def test_a_clean_target_drives(self):
        assert _veto()((2, 2), {"fatal": {(3, 3)}, "dead": {(5, 5)}},
                       avoid={(9, 9)}) is False

    def test_no_target_and_no_books_never_veto(self):
        v = _veto()
        assert v(None, {"fatal": {(3, 3)}}) is False
        assert v((1, 1), None) is False
        assert v((1, 1), {}) is False

    def test_the_veto_is_containment_pure(self):
        """Garbage in -> False out, never a raise (the book must not crash
        the loop it advises)."""
        assert _veto()(("x", None), {"fatal": "junk"}, avoid=object()) is False


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_the_drive_site_consults_the_frontier_before_clicking(self):
        src = self._src()
        i = src.find("[PLAN] DRIVE")
        assert i != -1, "the [PLAN] DRIVE site vanished"
        window = src[max(0, i - 3000):i]
        assert "plan_veto" in window, (
            "the planner still drives without a frontier consult — a verified "
            "plan can click a banked-fatal cell (B3 unlanded)")

    def test_a_vetoed_drive_falls_back_to_shadow(self):
        src = self._src()
        i = src.find("plan_veto")
        assert i != -1
        window = src[i:i + 2000]
        assert "shadow" in window, (
            "the vetoed branch must narrate as shadow, not silently drop")
