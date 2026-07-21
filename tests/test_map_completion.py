"""
Tests for brick 22: MAP-COMPLETION RE-PROBING.

The bug (measured on tu93 by LAW-0 replay): the agent completed only a PARTIAL action-map -- it probed each
action just twice during coverage, and an action whose two tries both landed on a BLOCKED cell (UP at the top
edge -> off-board -> no move) was written off as inert. The agent then over-committed to navigation with a
2-direction map and oscillated.

The fix: before committing to nav, keep re-probing UNMAPPED actions from wherever the cursor now sits, up to
`probe_limit` honest tries. An action that was inert only because it was tried from a blocked cell gets
re-tried after the cursor has moved -- and its true effect is discovered. An action that is GENUINELY inert
is written off only after enough tries (falsified-ledger discipline: inert is a verdict earned by trials).

FMap: falsified_ledger / express-before-judge -- a hypothesis (this action does nothing) is refuted or
confirmed by RUNNING it enough times, never assumed from too few trials.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.navigation import _unit
from newhorse.agent_loop import AgentLoop


PEN = 3   # UP is inert while the cursor is in the top "pen" (rows 0..PEN-1); it moves only at row >= PEN


class TopEdgeWorld:
    """A cursor (colour 4) that starts in a top 'pen' (rows 0..PEN-1) where UP does nothing -- so UP looks
    inert during the initial corner probing (both coverage tries land in the pen). UP only actually moves
    once the cursor has descended to row >= PEN. A COMPLETE 4-direction map therefore requires re-probing UP
    from OUTSIDE the pen after nav has driven the cursor down (brick 22). L/R/D are real movers everywhere.
    Small board -> stride 1."""

    def __init__(self):
        self.h, self.w = 12, 12
        self.pos = [0, 6]                                   # start pinned to the top edge, inside the pen
        self.secret = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
        self.target = (9, 6)                               # a landmark BELOW the pen -> nav drives D, exits pen

    def _up_inert_here(self):
        return self.pos[0] < PEN

    def _frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        g[self.target] = 7                                  # a landmark so goals/nav have something to chase
        g[tuple(self.pos)] = 4
        return g

    def frame(self):
        return self._frame()

    def step(self, action):
        if action == "U" and self._up_inert_here():
            return self._frame()                            # UP is dead inside the pen
        dr, dc = self.secret.get(action, (0, 0))
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if 0 <= nr < self.h and 0 <= nc < self.w:           # move only if it stays on the board
            self.pos = [nr, nc]
        return self._frame()


class InertActionWorld(TopEdgeWorld):
    """UP is GENUINELY inert everywhere (a horizontal/vertical-restricted mover). Re-probing must not loop
    forever: after `probe_limit` honest tries the agent gives up on the inert action and proceeds."""
    def step(self, action):
        if action == "U":
            return self._frame()                            # UP never does anything, anywhere
        return super().step(action)


def test_reprobe_completes_a_map_that_coverage_alone_leaves_partial():
    world = TopEdgeWorld()
    agent = AgentLoop(actions=["U", "D", "L", "R"], background=0)
    for _ in range(200):
        agent.step(world.frame(), world.step)
        if len(agent.agency.action_map()) == 4:
            break
    amap = agent.agency.action_map()
    dirs = {_unit(v) for v in amap.values()}
    assert agent.agency.ready()
    assert len(amap) == 4, "map never completed to all 4 actions: %s" % amap
    assert (-1, 0) in dirs, "UP direction never mapped despite re-probing: %s" % amap
    assert any("REPROBE" in line for line in agent.log), "re-probe never fired"


def test_reprobe_gives_up_on_a_genuinely_inert_action():
    world = InertActionWorld()
    agent = AgentLoop(actions=["U", "D", "L", "R"], background=0)
    for _ in range(200):
        agent.step(world.frame(), world.step)
    amap = agent.agency.action_map()
    # UP is truly inert -> it must NOT be in the map, and re-probing must GIVE UP after probe_limit honest
    # tries (not retry forever) -- while the real movers stay mapped.
    assert "U" not in amap, amap
    assert agent._action_tries.get("U", 0) == agent.probe_limit, agent._action_tries   # gave up at the limit
    assert not any(a not in amap and agent._action_tries.get(a, 0) < agent.probe_limit  # nothing left to probe
                   for a in agent.actions), (amap, agent._action_tries)
    assert "L" in amap and "R" in amap, amap                                            # real movers survive
