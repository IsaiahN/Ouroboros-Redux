"""
Tests for the budget model (brick 15): induce the remaining action budget by watching a HUD bar deplete,
measured (bar length / measured cols-per-action), never a guessed constant. Plus the decisiveness nudge:
as the budget runs low, the agent persists longer on its best goal (optimal foraging).
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.budget import BudgetModel
from newhorse.agent_loop import AgentLoop


def _frame_with_bar(bar_cols, meter_colour=11, fill_colour=3, W=64):
    """A 64x64 frame with a bottom HUD bar (rows 60-62): `bar_cols` columns of the meter colour (remaining),
    the rest filled with the elapsed colour."""
    g = np.zeros((64, W), dtype=int)
    for r in range(60, 63):
        for c in range(W):
            g[r, c] = meter_colour if c < bar_cols else fill_colour
    return g


def test_induces_the_meter_and_measures_budget():
    bm = BudgetModel()
    length = 40
    prev = _frame_with_bar(length)
    for _ in range(12):
        nxt = _frame_with_bar(length - 2)                  # the bar shrinks 2 columns per action
        bm.observe(prev, nxt)
        prev = nxt; length -= 2
    assert bm.meter == 11                                  # the depleting colour is the meter (not the growing fill)
    assert abs(bm.cols_per_action() - 2.0) < 1e-6          # MEASURED drain rate, not guessed
    left = bm.actions_left(prev)
    assert left is not None and abs(left - (length / 2.0)) < 1.0   # actions left = bar length / cols-per-action


def test_fraction_left_tracks_depletion():
    bm = BudgetModel()
    prev = _frame_with_bar(50)
    for L in range(48, 10, -2):
        nxt = _frame_with_bar(L)
        bm.observe(prev, nxt); prev = nxt
    frac = bm.fraction_left(prev)
    assert frac is not None and frac < 0.4                  # deep into the bar -> low remaining fraction


def test_no_meter_before_evidence():
    bm = BudgetModel()
    f = _frame_with_bar(40)
    bm.observe(f, f)                                        # one static observation -> not enough to induce
    assert bm.actions_left(f) is None and bm.fraction_left(f) is None


def test_nothing_silent():
    bm = BudgetModel()
    bm.observe(_frame_with_bar(40), _frame_with_bar(38))
    assert any(s.startswith("BUDGET") for s in bm.log)


def test_low_budget_makes_the_goal_pursuit_more_persistent():
    # a mover world with a DEPLETING bar; once budget is low, the agent's goal stall tolerance rises
    # (commit to the best goal), and it drops back when budget is ample.
    class BarMoverWorld:
        def __init__(self):
            self.h, self.w = 64, 64
            self.pos = [30, 30]
            self.bar = 50
            self.secret = {"U": (-5, 0), "D": (5, 0), "L": (0, -5), "R": (0, 5)}
        def _frame(self):
            g = np.zeros((self.h, self.w), dtype=int)
            for r in range(60, 63):
                for c in range(self.w):
                    g[r, c] = 11 if c < self.bar else 3
            g[7, 50] = 7                                    # a distinct landmark target
            r, c = self.pos
            g[r:r+2, c:c+2] = 12                            # the cursor
            return g
        def frame(self): return self._frame()
        def step(self, a):
            dr, dc = self.secret.get(a, (0, 0))
            self.pos = [min(58, max(0, self.pos[0]+dr)), min(self.w-1, max(0, self.pos[1]+dc))]
            self.bar = max(0, self.bar - 1)                # deplete
            return self._frame()
    world = BarMoverWorld()
    agent = AgentLoop(actions=["U", "D", "L", "R"], background=0)
    saw_raised = False
    base = agent.goals.stall_steps
    for _ in range(48):
        agent.step(world.frame(), world.step)
        if agent.budget.meter is not None and agent.goals.stall_steps > base:
            saw_raised = True
    assert agent.budget.meter == 11                        # induced the depleting bar as the meter
    assert saw_raised                                      # as the budget dropped, pursuit got more persistent
