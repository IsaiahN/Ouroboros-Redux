"""PHASE 2 GATE: the goal spine — confirmed reward earns the wheel; everything else is None.

⭐ WHY. The 20-generation baseline: breadth from lottery+banking, ZERO depth. Depth needs
directed play; directed play is allowed only under the wheel rule (EGOCENTRIC_PORT_PLAN.md §7):
blind explore is the incumbent, a level-up CONFIRMS a candidate goal (cue-proposes,
reward-disposes), and only a confirmed goal may drive.

THE CONTRACT (PREREG_PHASE2.md):
  * `engines/egocentric/` gains verbatim `goal`, `relations`, `navigation` (importable);
  * `GoalSpine` (engines/egocentric/spine.py):
      - `note_move(action, delta)` accrues per-action centroid vector deltas; an action's delta
        is ESTABLISHED once seen `min_evidence` times with consistent direction;
      - `propose(cells)` seeds candidate target cells (rank order preserved);
      - `credit(cell)` confirms by reward (delegates to GoalManager.credit);
      - `drive(self_cell) -> Optional[action]`: None unless a CONFIRMED goal exists (price >=
        confirm_bonus) AND some established action reduces Manhattan distance to it; else the
        established action with the greatest distance reduction (deterministic tie-break by
        action name); at the goal already -> None;
      - deterministic; a public `errors` counter; no RNG, no I/O.
  * wiring: ONE pre-empt site in the loop's action path — non-None drive replaces the action,
    None changes nothing; `level_changed` wires to `credit`; `[EGO-GOAL]` log lines exist.

Run pre-build: these failed (module absent), per the beat-49 rule.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _spine():
    try:
        from engines.egocentric.spine import (
            GoalSpine,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.spine is missing (%s) — Phase 2 has not landed; see "
                    "PREREG_PHASE2.md" % e)
    from engines.egocentric.spine import GoalSpine as GS
    return GS


def _established(s, action, delta, times=4):
    for _ in range(times):
        s.note_move(action, delta)


class TestTheWheelRule:

    def test_no_confirmation_means_none_always(self):
        """⭐ THE RULE. Candidates proposed, deltas established — but no reward ever confirmed
        anything. drive() must be None, every call."""
        s = _spine()()
        s.propose([(3, 3), (7, 7)])
        _established(s, "A1", (0, 1))
        _established(s, "A2", (0, -1))
        for _ in range(5):
            assert s.drive((3, 0)) is None

    def test_unestablished_deltas_mean_none_even_when_confirmed(self):
        s = _spine()()
        s.propose([(3, 3)])
        s.credit((3, 3))
        assert s.drive((0, 0)) is None, (
            "the spine drove with no established action-delta map — it cannot know which "
            "action moves the body; the wheel needs BOTH signal and means")

    def test_credit_then_drive_steers_toward_the_confirmed_goal(self):
        s = _spine()()
        s.propose([(3, 6)])
        _established(s, "A1", (0, 1))    # moves +1 column
        _established(s, "A2", (0, -1))
        s.credit((3, 6))
        assert s.drive((3, 0)) == "A1", "must pick the established action that reduces distance"
        assert s.drive((3, 9)) == "A2"

    def test_at_the_goal_is_none(self):
        s = _spine()()
        s.propose([(2, 2)])
        _established(s, "A1", (0, 1))
        s.credit((2, 2))
        assert s.drive((2, 2)) is None

    def test_an_unhelpful_map_is_none(self):
        """Only an away-moving action is established — driving with it would be worse than
        exploring. None."""
        s = _spine()()
        s.propose([(0, 5)])
        _established(s, "A1", (0, -1))
        s.credit((0, 5))
        assert s.drive((0, 0)) is None

    def test_determinism_and_tie_break(self):
        s = _spine()()
        s.propose([(4, 4)])
        _established(s, "B", (1, 0))
        _established(s, "A", (1, 0))     # identical delta -> tie -> lexicographic action name
        s.credit((4, 4))
        picks = {s.drive((0, 4)) for _ in range(5)}
        assert picks == {"A"}


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_the_action_path_consults_drive_and_uses_only_non_none(self):
        src = self._src()
        assert "GoalSpine" in src or "_goal_spine" in src, (
            "cognitive_loop never touches the spine — Phase 2 wiring absent (starvation).")
        assert ".drive(" in src, "the pre-empt site never calls drive()"
        i = src.find(".drive(")
        window = src[max(0, i - 400):i + 600]
        assert "is not None" in window or "if _ego_drive" in window or "if drive_action" in window, (
            "the pre-empt site does not gate on non-None — a None drive must change NOTHING")

    def test_reward_wires_to_credit(self):
        src = self._src()
        i = src.find("def record_result")
        body = src[i:i + 8000]
        assert ".credit(" in body, (
            "record_result never credits the spine on a level-up — reward-disposes is the ONLY "
            "confirmation path and it is unwired (starvation).")
        assert "level_changed" in body

    def test_the_goal_log_exists(self):
        assert "[EGO-GOAL]" in self._src()
