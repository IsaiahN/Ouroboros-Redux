"""
Tests for agent-vs-environment separation (brick 12).

The module test pins the discriminative + axis-aligned cursor guard directly. The integration test is the
real ls20 fix in miniature: a mover world with HEAVY action-independent background churn, where the
whole-frame unit-transform belief stays ~0 (reproducing the live ls20 failure) but the agency isolates the
cursor and learns its true multi-cell per-action move anyway.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.agency import CursorAgency
from newhorse.agent_loop import AgentLoop


# ---------------- module: the discriminative cursor guard --------------------------------
def _frame(dot, colour=4, churn=None, shape=(16, 16)):
    g = np.zeros(shape, dtype=int)
    if churn:
        for (r, c, v) in churn:
            g[r, c] = v
    g[dot] = colour
    return g


def test_learns_per_action_move_map_and_stride():
    ag = CursorAgency()
    # secret: A1 up-3, A2 down-3, A3 left-3, A4 right-3 (stride 3, axis-aligned, discriminative)
    moves = {"A1": (-3, 0), "A2": (3, 0), "A3": (0, -3), "A4": (0, 3)}
    pos = [8, 8]
    for _ in range(4):
        for a, (dr, dc) in moves.items():
            b = _frame(tuple(pos))
            pos = [min(15, max(0, pos[0] + dr)), min(15, max(0, pos[1] + dc))]
            ag.observe(b, a, _frame(tuple(pos)))
    assert ag.ready()
    assert ag.cursor_colour() == 4
    assert ag.stride() == 3
    for a, mv in moves.items():
        assert ag.predict(a) == mv, (a, ag.action_map())


def test_uniform_drift_is_rejected_goodhart_guard():
    # a colour that moves the SAME way under EVERY action (a scrolling background) is consistent but NOT
    # discriminative -> it must not be claimed as the cursor.
    ag = CursorAgency()
    pos = [2, 2]
    for a in ["A1", "A2", "A3", "A4"] * 4:
        b = _frame(tuple(pos), colour=7)
        pos = [min(15, pos[0] + 1), pos[1]]                # always drifts down, regardless of action
        ag.observe(b, a, _frame(tuple(pos), colour=7))
    assert ag.cursor_colour() is None                      # consistent-but-not-discriminative -> not self
    assert not ag.ready()


def test_static_object_is_never_the_cursor():
    ag = CursorAgency()
    for a in ["A1", "A2"] * 4:
        f = _frame((5, 5), colour=3)
        ag.observe(f, a, f.copy())                          # never moves
    assert ag.cursor_colour() is None


def test_nothing_silent():
    ag = CursorAgency()
    ag.observe(_frame((1, 1)), "A1", _frame((2, 1)))
    assert any(s.startswith("AGENCY") for s in ag.log)


# ---------------- integration: the ls20 fix in miniature ---------------------------------
class ChurnMoverWorld:
    """A cursor (colour 4) that moves a SECRET 3-cell vector per action, on a board with HEAVY
    action-independent background churn (a big block of colour 8 that reshuffles every step regardless of
    the action -- like ls20's maze redraw). Whole-frame prediction error is dominated by the churn."""

    def __init__(self, shape=(20, 20)):
        self.h, self.w = shape
        self.pos = [10, 10]
        self.secret = {"A1": (-3, 0), "A2": (3, 0), "A3": (0, -3), "A4": (0, 3)}
        self.t = 0

    def _frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        # action-INDEPENDENT churn: a 6x6 block of colour 8 whose interior pattern cycles every step
        for r in range(2, 8):
            for c in range(12, 18):
                g[r, c] = 8 if ((r + c + self.t) % 2 == 0) else 3
        g[tuple(self.pos)] = 4                               # the cursor
        return g

    def frame(self):
        return self._frame()

    def step(self, action):
        dr, dc = self.secret.get(action, (0, 0))
        self.pos = [min(self.h - 1, max(0, self.pos[0] + dr)), min(self.w - 1, max(0, self.pos[1] + dc))]
        self.t += 1
        return self._frame()


def test_loop_learns_the_mover_despite_background_churn():
    world = ChurnMoverWorld()
    agent = AgentLoop(actions=["A1", "A2", "A3", "A4"], background=0)
    for _ in range(40):
        agent.step(world.frame(), world.step)
    # the agency SEPARATED the cursor from the churn and learned its true 3-cell move map
    assert agent.agency.ready()
    assert agent.agency.cursor_colour() == 4               # the cursor, not the churning colour 8/3
    assert agent.agency.stride() == 3
    truth = {"A1": (-3, 0), "A2": (3, 0), "A3": (0, -3), "A4": (0, 3)}
    for a, mv in truth.items():
        assert agent.agency.predict(a) == mv, agent.agency.action_map()


def test_whole_frame_unit_belief_fails_on_the_same_world():
    # CONTROL: the OLD signal (whole-frame unit-transform salience) cannot learn here -- the churn drowns it.
    # This is why brick 12 was needed; the agency (centroid-localized) succeeds where this fails.
    world = ChurnMoverWorld()
    agent = AgentLoop(actions=["A1", "A2", "A3", "A4"], background=0)
    for _ in range(40):
        agent.step(world.frame(), world.step)
    # no single unit-transform belief ever became confident (all swamped by ~35 cells of churn per step)
    best_unit = max((agent.belief.get((a, t), 0.0)
                     for a in agent.actions for t in agent.transforms), default=0.0)
    assert best_unit < 0.2, best_unit                      # the whole-frame path is drowned -> agency was essential
