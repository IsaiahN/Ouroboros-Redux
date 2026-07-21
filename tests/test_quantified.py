"""
Tests for quantified objectives (brick 18): ALL(x in COLOUR-CLASS) -- the cursor must reach EVERY member of
a class, not just one. The map's point: a composite/quantified win must be discovered by reward, and reaching
ONE member must not masquerade as satisfying the whole set (the goodhart guard).
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.relations import quantified_candidates, class_member_cells
from newhorse.perception import Object
from newhorse.agent_loop import AgentLoop


def _obj(cells, colour):
    return Object(cells=frozenset(cells), colours=frozenset({colour}))


def test_quantified_candidate_proposed_for_repeated_colour():
    objs = [_obj([(0, 0)], 4),                              # cursor
            _obj([(2, 2)], 7), _obj([(8, 8)], 7),          # colour 7 appears twice -> ALL(7)
            _obj([(5, 5)], 6)]                             # colour 6 once -> not quantified
    q = quantified_candidates(objs, cursor_colour=4, stride=1)
    keys = {k for k, _ in q}
    assert ("ALL", 7) in keys
    assert ("ALL", 6) not in keys
    assert set(class_member_cells(objs, 7, 1)) == {(2, 2), (8, 8)}


# ---------------- integration: discover "visit ALL markers" wins, one does not ----------------
class AllMarkersWorld:
    """Two markers (colour 7); the win is visiting BOTH (an ALL objective). Visiting only one does NOT win.
    A decoy (colour 6) does nothing. Small board -> stride 1."""

    def __init__(self):
        self.h, self.w = 14, 14
        self.pos = [7, 1]
        self.markers = [(2, 11), (11, 11)]
        self.decoy = (7, 7)
        self.visited = set()
        self.levels = 0
        self.secret = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

    def _frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        for m in self.markers:
            g[m] = 7                                        # the two markers (a class) stay visible
        g[self.decoy] = 6
        g[tuple(self.pos)] = 4
        return g

    def frame(self):
        return self._frame()

    def step(self, action):
        dr, dc = self.secret.get(action, (0, 0))
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if 0 <= nr < self.h and 0 <= nc < self.w:
            self.pos = [nr, nc]
        if tuple(self.pos) in self.markers:
            self.visited.add(tuple(self.pos))
        if self.visited == set(self.markers):              # ALL markers visited -> win
            self.levels += 1
            self.visited = set(); self.pos = [7, 1]
        return self._frame()


def test_agent_discovers_visit_all_markers_wins():
    world = AllMarkersWorld()
    agent = AgentLoop(actions=["U", "D", "L", "R"], background=0)
    levels_seen = 0
    for _ in range(800):
        frame = world.frame()
        ctrl = agent.perceive(frame)
        if ctrl is None:
            world.step(agent.actions[0]); continue
        action, t, _ = agent.choose(frame, ctrl)
        before = world.levels
        after = world.step(action)
        if world.levels > before:
            agent.signal_reward()
        agent.observe(frame, ctrl, action, t, after)
        levels_seen = world.levels
        if levels_seen >= 2:
            break
    assert agent.agency.ready()
    assert levels_seen >= 2, "never discovered the ALL(markers) objective (levels=%d)" % levels_seen
    # the winning hypothesis is the quantified ALL over the marker colour, priced above single-target relations
    top_key = max(agent.goals.price, key=agent.goals.price.get)
    assert top_key == ("ALL", 7), (top_key, sorted(agent.goals.price.items(), key=lambda kv: -kv[1])[:4])
