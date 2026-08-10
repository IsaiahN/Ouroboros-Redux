"""PHASE 3b2 GATE: the click-side economy — credit the ACTED-ON cell.

⭐ WHY. The 3b trial dropped a real level-up on the floor: the credit wire required the
controllable's centroid, and click games never have one (nothing moves WITH the choice, so
contingency can never name a self). The reward-attribution rule generalises: credit the cell
the agent ACTED ON when the reward arrived — the clicked cell for clicks, the body's cell for
movement. Same wheel rule on the way back out: a confirmed CLICK_AT goal may drive (click that
cell), one clicked-without-reward falsifies it shut.

THE CONTRACT (PREREG_PHASE3B2.md):
  * spine: `seed_confirmed_click(cell, price)`, `demote_inherited_click(cell)` — symmetric to
    the BE_AT pair, on key ("CLICK_AT", cell);
  * spine: `credit_click(cell)` — GoalManager credit on the CLICK_AT key (confirm-bonus price);
  * spine: `drive_click() -> (x, y) | None` — None unless some CLICK_AT key's price >=
    confirm_bonus; else the highest-priced confirmed CLICK_AT cell (deterministic tie-break by
    cell); INDEPENDENT of the movement delta map (clicking needs no locomotion);
  * loop wiring: in the credit branch, a click action's (x, y) credits/mints
    {"kind": "CLICK_AT", "cell": [x, y]} WITHOUT needing a centroid; the pre-empt site consults
    movement drive first, then drive_click (action 6 + those coords); falsify-on-
    clicked-without-reward mirrors the BE_AT write-back.

Run pre-build: these failed (methods absent).
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _spine():
    from engines.egocentric.spine import GoalSpine
    s = GoalSpine()
    for m in ("credit_click", "drive_click", "seed_confirmed_click", "demote_inherited_click"):
        if not hasattr(s, m):
            pytest.fail("GoalSpine.%s missing — Phase 3b2 has not landed" % m)
    return s


class TestTheClickWheelRule:

    def test_no_confirmation_means_none(self):
        s = _spine()
        assert s.drive_click() is None

    def test_credit_then_drive_clicks_the_confirmed_cell(self):
        s = _spine()
        s.credit_click((60, 20))
        assert s.drive_click() == (60, 20)

    def test_click_drive_needs_no_movement_map(self):
        """Clicking is not locomotion — an empty delta map must not block it."""
        s = _spine()
        assert not s.established(), "precondition: no movement actions established"
        s.credit_click((5, 5))
        assert s.drive_click() == (5, 5)

    def test_seeded_click_goal_opens_and_demote_closes(self):
        s = _spine()
        s.seed_confirmed_click((7, 8), price=s.manager.confirm_bonus)
        assert s.drive_click() == (7, 8), "an inherited confirmed CLICK_AT must open the gate"
        s.demote_inherited_click((7, 8))
        assert s.drive_click() is None, "falsified inherited click-goal must close the gate"

    def test_highest_price_wins_deterministically(self):
        s = _spine()
        s.credit_click((1, 1))
        s.credit_click((2, 2))
        s.credit_click((1, 1))         # (1,1) now higher-priced
        picks = {s.drive_click() for _ in range(5)}
        assert picks == {(1, 1)}

    def test_movement_side_is_untouched(self):
        """The BE_AT machinery must behave exactly as Phase 2 pinned it."""
        s = _spine()
        s.propose([(3, 6)])
        for _ in range(4):
            s.note_move("A1", (0, 1))
        s.credit((3, 6))
        assert s.drive((3, 0)) == "A1"


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_the_credit_branch_handles_clicks_without_a_centroid(self):
        src = self._src()
        assert "credit_click" in src, (
            "the credit branch never credits the clicked cell — click-game rewards are still "
            "dropped on the floor (the 3b trial's exact failure)")
        i = src.find("credit_click")
        window = src[max(0, i - 1500):i]
        assert "level_changed" in window, "credit_click must live inside the level-up branch"

    def test_click_at_ideas_are_minted(self):
        assert "CLICK_AT" in self._src()

    def test_the_preempt_site_consults_click_drive(self):
        src = self._src()
        assert "drive_click" in src
        i = src.find(".drive_click(")
        assert i != -1
        window = src[max(0, i - 800):i + 400]
        assert "is not None" in window, "a None click-drive must change nothing"

    def test_the_click_falsify_writeback_exists(self):
        src = self._src()
        assert "demote_inherited_click" in src or "falsified inherited click" in src, (
            "no clicked-without-reward write-back — the pariah loop must close on the click "
            "side too")
