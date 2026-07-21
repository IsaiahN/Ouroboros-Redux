"""
Smoke test for brick 9 (live-run wiring), THE MAP §9.6 closed against a world -- OFFLINE, no network.

A FakeSession mirrors the exact Arc3Session interface (open/step/close -> snapshot dicts) over a tiny
controllable-dot world whose action->effect map is the WORLD'S SECRET. One action moves the dot down;
reaching the bottom row is a LEVEL-UP (auto-advances, dot respawns near the top). The test proves the
run wires end-to-end AND that the honest properties hold: the loop discovers the secret mover, racks up
`levels_completed`, mints EARNED reset credits on level-up (and never resets in play), keeps full
resolution, and reports what it learned. The real network run is exercised separately, best-effort.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.live_run import run_live, _learned_summary
from newhorse.agent_loop import AgentLoop


class FakeSession:
    """An in-process ARC-3-shaped session: one dot on a board, one SECRET mover action, bottom row = level."""

    def __init__(self, shape=(8, 8), secret_mover=1, colour=4, available=(1, 2)):
        self.h, self.w = shape
        self.colour = colour
        self.secret = {secret_mover: (1, 0)}          # ONLY this action moves the dot DOWN; others are no-ops
        self.available = list(available)
        self.pos = [1, 3]
        self.levels = 0
        self.view_url = "fake://session"
        self._opened = False
        self._closed = False

    def _frame(self):
        g = np.zeros((self.h, self.w), dtype=int); g[tuple(self.pos)] = self.colour; return g

    def _snap(self, done=False, state="NOT_FINISHED"):
        return dict(grid=self._frame(), available=list(self.available),
                    levels_completed=self.levels, state=state, done=done)

    def open(self):
        self._opened = True; self.pos = [1, 3]; return self._snap()

    def step(self, value, data=None, reasoning=None):
        dr, dc = self.secret.get(int(value), (0, 0))
        self.pos[0] = min(self.h - 1, max(0, self.pos[0] + dr))
        self.pos[1] = min(self.w - 1, max(0, self.pos[1] + dc))
        if self.pos[0] == self.h - 1:                 # reached the bottom -> LEVEL-UP, respawn near the top
            self.levels += 1; self.pos = [1, 3]
            return self._snap(done=False, state="NOT_FINISHED")   # a level-win auto-advances; not episode-done
        return self._snap()

    def close(self):
        self._closed = True; return None


def test_run_wires_end_to_end_and_completes_levels():
    sess = FakeSession(secret_mover=1)
    res = run_live(sess, wall_cap_s=30.0, max_actions=200)
    assert sess._opened
    assert res["levels_completed"] >= 1, res            # the loop actually cleared levels: the GATE metric
    assert res["steps"] > 0 and isinstance(res["outcome"], str)
    assert res["view_url"] == "fake://session"


def test_it_discovers_the_secret_mover():
    # the secret is ACTION1->DOWN; the loop must LEARN it (never told). Its belief for A1 argmaxes to DOWN.
    sess = FakeSession(secret_mover=1)
    res = run_live(sess, wall_cap_s=30.0, max_actions=200)
    a1 = res["learned"]["per_action"].get("A1")
    assert a1 is not None and a1["best_transform"] == "DOWN", res["learned"]


def test_level_up_mints_earned_reset_credits():
    # progress is the ONLY thing that earns a reset -- the credits in the summary come from real level-ups.
    sess = FakeSession(secret_mover=1)
    res = run_live(sess, wall_cap_s=30.0, max_actions=200)
    assert res["learned"]["reset_credits"] >= 1
    assert res["learned"]["reset_credits"] == res["levels_completed"]   # one earned credit per completed level


def test_full_resolution_preserved_through_the_live_loop():
    # every frame stayed 8x8: the ResolutionBound admitted them all without a DownsampleError.
    sess = FakeSession(shape=(8, 8), secret_mover=1)
    res = run_live(sess, wall_cap_s=30.0, max_actions=120)
    assert res["outcome"] in ("action_cap", "WIN", "GAME_OVER")   # ran to completion, no downsample raise


def test_the_brake_grew_and_nothing_silent():
    sess = FakeSession(secret_mover=1)
    res = run_live(sess, wall_cap_s=30.0, max_actions=120)
    assert res["learned"]["pe_integral"] > 0.0          # it was surprised (learned from real error)
    assert 0.0 <= res["learned"]["pose_alpha"] <= 1.0


def test_no_discrete_actions_is_handled_not_crashed():
    # a click-only game (only value 6 available) can't be driven by the unit-transform loop yet -> honest no-op.
    sess = FakeSession(available=(6,))
    res = run_live(sess, wall_cap_s=5.0, max_actions=10)
    assert res["outcome"] == "no_discrete_actions" and res["learned"] is None
