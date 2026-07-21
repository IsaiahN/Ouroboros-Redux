"""
Tests for the typed win-relation space (brick 17): BE_AT / TOUCH / COVER proposed per object, priced by
reward. The integration test is the map's point: a world whose win is COVER (get INSIDE a hollow slot) with
a decoy solid object (BE_AT does nothing) -- the agent DISCOVERS that COVER is the winning relation by reward,
not by assumption.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.relations import candidate_relations, _hollow_interior
from newhorse.perception import Object
from newhorse.agent_loop import AgentLoop


def _obj(cells, colour):
    return Object(cells=frozenset(cells), colours=frozenset({colour}))


def _ring(r0, c0, n, colour):
    """An n×n hollow frame (outline) at (r0,c0) -- object cells on the border, hollow centre."""
    cells = []
    for r in range(r0, r0 + n):
        for c in range(c0, c0 + n):
            if r in (r0, r0 + n - 1) or c in (c0, c0 + n - 1):
                cells.append((r, c))
    return _obj(cells, colour)


def test_relation_space_proposes_be_at_touch_cover():
    solid = _obj([(5, 5)], 4)
    ring = _ring(10, 10, 3, 7)                              # a hollow 3x3 slot
    cands = candidate_relations([solid, ring], cursor_colour=None, stride=1)
    rels = {k[0] for k, _ in cands}
    assert "BE_AT" in rels and "TOUCH" in rels
    assert "COVER" in rels                                  # the hollow ring yields a COVER hypothesis
    # COVER's target is the ring's hollow centre
    cover = [k for k, _ in cands if k[0] == "COVER"][0]
    assert cover[1] == (11, 11)


def test_hollow_detection_frame_vs_solid():
    assert _hollow_interior(_ring(0, 0, 5, 7), 1) == (2, 2)   # frame -> centre
    assert _hollow_interior(_obj([(r, c) for r in range(3) for c in range(3)], 7), 1) is None  # solid -> None


# ---------------- integration: DISCOVER that COVER wins (not BE_AT) ----------------
class CoverWorld:
    """Win = get the cursor INSIDE the hollow slot (colour 7 ring); reaching its centre grants a level and
    respawns the cursor. A decoy SOLID object (colour 6) does nothing when reached. Small board -> stride 1."""

    def __init__(self):
        self.h, self.w = 16, 16
        self.pos = [8, 2]
        self.slot_c = (4, 12)                               # centre of the hollow slot
        self.decoy = (12, 2)
        self.levels = 0
        self.secret = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

    def _frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        # the hollow slot: a 3x3 ring of colour 7 centred on slot_c, with an OPENING at the bottom-centre
        # (an enterable doorway) so the interior can be reached -- COVER = get inside.
        r0, c0 = self.slot_c[0] - 1, self.slot_c[1] - 1
        door = (r0 + 2, c0 + 1)                             # bottom-centre cell left open
        for r in range(r0, r0 + 3):
            for c in range(c0, c0 + 3):
                if (r in (r0, r0 + 2) or c in (c0, c0 + 2)) and (r, c) != door:
                    g[r, c] = 7
        g[self.decoy] = 6                                   # solid decoy
        g[tuple(self.pos)] = 4                              # cursor
        return g

    def frame(self):
        return self._frame()

    def step(self, action):
        dr, dc = self.secret.get(action, (0, 0))
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if 0 <= nr < self.h and 0 <= nc < self.w and self._frame()[nr, nc] != 7:  # the ring is solid; centre is open
            self.pos = [nr, nc]
        if tuple(self.pos) == self.slot_c:                 # INSIDE the slot -> win
            self.levels += 1
            self.pos = [8, 2]
        return self._frame()


def test_agent_discovers_cover_is_the_winning_relation():
    world = CoverWorld()
    agent = AgentLoop(actions=["U", "D", "L", "R"], background=0)
    levels_seen = 0
    for _ in range(600):
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
    assert levels_seen >= 2, "never discovered COVER (levels=%d)" % levels_seen
    # the top-priced relation is a COVER (the discovered winning relation), above any BE_AT/TOUCH
    top_key = max(agent.goals.price, key=agent.goals.price.get)
    assert top_key[0] == "COVER", (top_key, sorted(agent.goals.price.items(), key=lambda kv: -kv[1])[:4])
