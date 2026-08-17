"""MOVEMENT-STACK GATE (rung 0c FIRST ACTIVATION, the pair): CursorAgency +
GridNav wired into the live path.

THE CONTRACT (maintainer's order, PIPELINE_AUDIT.md "the unwired
movement-game stack"):

  * CursorAgency learns the own-avatar displacement map from REAL move
    outcomes: record_result feeds it pre/post frames + the executed action
    (house try/except, compact site);
  * GridNav builds traversability from CursorAgency's map + observed frames
    and provides BFS pathing (walls learned by bumping, first-step queries);
  * the loop's blind-explore movement path (actions 1-4) PREFERS GridNav's
    next step over random rotation ONLY when the game shows mover-behavior
    (CursorAgency confident) AND a target exists (abduced-goal predicate
    site or nearest-unexplored-region) -- as a BIAS consistent with the
    wheel rule: blind explore stays incumbent, the steer is narrated [NAV],
    never a veto, and its share is capped (NAV_BIAS_P <= 0.5, Register G
    GUESSED);
  * WHEEL RULE INTACT: with no confidence (or no target) the selection path
    is byte-identical to the incumbent draw -- same action, same RNG stream
    (no extra draw is ever consumed).

Run pre-build: failed (no feed site, no steer, no knob).
"""
from __future__ import annotations

import io
import os
import random
import sys
from contextlib import redirect_stdout
from types import SimpleNamespace

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.agency import CursorAgency  # noqa: E402
from engines.egocentric.navigation import GridNav  # noqa: E402

GAME_ID = "mvstack_g1"


# ── the synthetic mover episode ──────────────────────────────────────────────
# 64x64 world: static walls (colour 5), a 2x2 cursor (colour 3) that moves at
# stride 2 -- action 1=up, 2=down, 3=left, 4=right. Deterministic throughout.

def _frame(r, c):
    f = np.zeros((64, 64), dtype=int)
    f[0, 0:64] = 5                    # a static wall strip (must be rejected)
    f[63, 0:64] = 5
    f[r:r + 2, c:c + 2] = 3           # the cursor body
    return f


_SHIFT = {"1": (-2, 0), "2": (2, 0), "3": (0, -2), "4": (0, 2)}


def _mover_steps(n_rounds=3, start=(30, 30)):
    """(before, action, after) triples of a scripted mover episode."""
    r, c = start
    steps = []
    for _ in range(n_rounds):
        for a in ("4", "4", "3", "1", "2", "3"):
            dr, dc = _SHIFT[a]
            before = _frame(r, c)
            r, c = r + dr, c + dc
            steps.append((before, a, _frame(r, c)))
    return steps


def _trained_agency():
    ag = CursorAgency()
    for b, a, f in _mover_steps():
        ag.observe(b, a, f)
    return ag


class TestCursorAgencyLearnsTheMap:

    def test_synthetic_mover_episode_maps_actions(self):
        ag = _trained_agency()
        assert ag.ready(), "a consistent scripted mover must be identified"
        assert ag.cursor_colour() == 3, "the mover colour is the cursor"
        m = ag.action_map()
        assert m.get("4") == (0, 2) and m.get("3") == (0, -2), (
            "the per-action displacement map must recover the scripted shifts")
        assert ag.stride() == 2, "the move quantum is recovered from the map"

    def test_the_wall_strip_is_never_the_cursor(self):
        ag = _trained_agency()
        assert ag.cursor_colour() != 5, (
            "a static decoration must never be adopted as the body")


class TestGridNavPathsAroundAWall:

    DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def test_open_terrain_beelines(self):
        assert GridNav().step_toward((0, 0), (0, 3), self.DIRS) == (0, 1)

    def test_first_step_avoids_the_measured_wall(self):
        nav = GridNav()
        nav.observe_move((0, 0), (0, 1), False)      # bumped: wall east of (0,0)
        d = nav.step_toward((0, 0), (0, 3), self.DIRS)
        assert d is not None, "a wall never strands the pather"
        assert d != (0, 1), "the measured wall edge must not be re-chosen"


# ── the live-path feed (record_result) ──────────────────────────────────────

@pytest.fixture(scope="module")
def fed_loop(tmp_path_factory):
    """A hermetic loop driven through record_result with a scripted mover."""
    run_dir = tmp_path_factory.mktemp("mvstack_run")
    cwd = os.getcwd()
    os.chdir(run_dir)
    try:
        from cognitive_loop import CognitiveLoop
        from engines.cognition.cognitive_frame import CognitiveFrame
        random.seed(77)
        loop = CognitiveLoop(verbose=False)
        loop.start_game(GAME_ID, [1, 2, 3, 4], max_actions=500)
        buf = io.StringIO()
        with redirect_stdout(buf):
            for before, a, after in _mover_steps():
                loop._current_frame = CognitiveFrame()
                loop._prev_frame = before
                loop._last_action_info = {
                    "type": int(a), "x": None, "y": None,
                    "frame_changed": False, "score_delta": 0.0,
                    "level_changed": False,
                    "consecutive_no_change": 0, "consecutive_same_action": 0,
                }
                loop.record_result(post_frame=after, frame_changed=True,
                                   score_delta=0.0, level_changed=False)
        yield {"loop": loop, "out": buf.getvalue()}
    finally:
        os.chdir(cwd)


class TestTheLoopFeedsTheStack:

    def test_cursor_agency_is_fed_from_record_result(self, fed_loop):
        ag = getattr(fed_loop["loop"], "_cursor_agency", None)
        assert ag is not None, (
            "record_result never fed CursorAgency -- the movement stack is "
            "still SEVERED (no production caller)")
        assert ag.ready() and ag.cursor_colour() == 3

    def test_grid_nav_built_traversability_from_the_frames(self, fed_loop):
        nav = getattr(fed_loop["loop"], "_grid_nav", None)
        assert nav is not None, "GridNav never constructed in the live path"
        assert nav.t > 0 and nav.free, (
            "GridNav recorded no measured move outcomes -- traversability "
            "was never built from the agency's map + observed frames")
        assert getattr(fed_loop["loop"], "_nav_cell", None) is not None


# ── the [NAV] steer in the blind-explore movement path ──────────────────────

def _armed_loop(with_agency=True):
    from cognitive_loop import CognitiveLoop
    loop = CognitiveLoop(verbose=False)
    loop.start_game("mvstack_g2", [1, 2, 3, 4], max_actions=500)
    if with_agency:
        loop._cursor_agency = _trained_agency()
        loop._grid_nav = GridNav()
        loop._nav_cell = (5, 5)          # cell grain (stride 2)
        loop._nav_goal_px = (30, 10)     # (x, y) px -> cell (5, 15): due east
        loop._ego_frame_shape = (64, 64)
    return loop


def _act(loop):
    from engines.cognition.cognitive_frame import CognitiveFrame
    cf = CognitiveFrame()
    percept = SimpleNamespace()          # click sections are 6-gated: untouched
    buf = io.StringIO()
    with redirect_stdout(buf):
        a, d = loop._act(percept, "explore", 0.2, None, None,
                         "agent", "pioneer", 0.5, 0.5, cf)
    return a, buf.getvalue()


class TestTheNavBias:

    def test_fires_when_confident_with_target_under_the_cap(self, monkeypatch):
        import cognitive_loop as cl
        loop = _armed_loop()
        monkeypatch.setattr(cl.random, "random", lambda: 0.0)   # under the cap
        a, out = _act(loop)
        assert a == 4, (
            "confident agency + due-east target must steer the draw to the "
            "mapped east action (GridNav first step)")
        assert "[NAV]" in out, "the steer must narrate [NAV]"

    def test_the_cap_is_respected_never_a_veto(self, monkeypatch):
        import cognitive_loop as cl
        assert float(cl.NAV_BIAS_P) <= 0.5, (
            "the steer's share must be capped at p<=0.5 (Register G GUESSED)")
        loop = _armed_loop()
        monkeypatch.setattr(cl.random, "random", lambda: 0.51)  # over the cap
        a, out = _act(loop)
        assert a in (1, 2, 3, 4)
        assert "[NAV]" not in out, (
            "over the cap the incumbent blind draw must run -- a steer, "
            "never a veto")

    def test_wheel_rule_no_confidence_is_byte_identical(self):
        """No agency -> the selection AND the RNG stream match the incumbent
        draw exactly (no extra random consumed)."""
        from engines.egocentric.frontier import bias_moves
        loop = _armed_loop(with_agency=False)
        random.seed(31)
        a, out = _act(loop)
        r_after = random.random()
        random.seed(31)
        expected = random.choice(bias_moves([1, 2, 3, 4], {}))
        r_expected = random.random()
        assert a == expected, (
            "with no confidence the chosen action must be byte-identical to "
            "the incumbent blind draw")
        assert r_after == r_expected, (
            "the steer consumed an RNG draw while unconfident -- the wheel "
            "rule broke (downstream stream shifted)")
        assert "[NAV]" not in out
