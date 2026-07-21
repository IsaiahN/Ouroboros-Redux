"""
Tests for grid navigation + goal abduction (brick 13).

GridNav: directed-edge walls (a failed move is a directed BLOCKED fact, not a whole-cell one), BFS pathing
with a greedy fallback, and defeasibility (decay/invalidate). goal.abduce_target: a unique small non-self
object is a provisional destination. Loop integration: on a mover world with a wall, the agent navigates the
cursor to the abduced target, learning the wall by bumping.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.navigation import GridNav
from newhorse.goal import abduce_target
from newhorse.perception import Object
from newhorse.agent_loop import AgentLoop

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def test_blocked_edge_is_directed_not_cellwise():
    nav = GridNav()
    nav.observe_move((2, 2), (0, 1), moved=False)          # moving RIGHT from (2,2) hit a wall
    assert nav.is_blocked((2, 2), (0, 1))
    assert not nav.is_blocked((2, 2), (0, -1))             # LEFT from the same cell is NOT implied blocked
    assert not nav.is_blocked((3, 2), (0, 1))              # a different cell's right edge is unmeasured -> open


def test_bfs_routes_around_a_wall():
    nav = GridNav()
    # a vertical wall on the right edges of column 0 cells forces a detour down-then-right
    for r in range(0, 3):
        nav.observe_move((r, 0), (0, 1), moved=False)      # can't go right from column 0 at rows 0..2
    nav.observe_move((2, 0), (1, 0), moved=True)           # but down from (2,0) is open
    nav.observe_move((3, 0), (0, 1), moved=True)           # and right from (3,0) is open
    step = nav.step_toward((0, 0), (3, 1), DIRS)
    assert step == (1, 0), step                            # first step is DOWN (around the wall), not blocked-right


def test_greedy_fallback_when_no_known_path():
    nav = GridNav()
    # nothing measured -> optimistic: step greedily toward the goal (reduce manhattan), never a known wall
    step = nav.step_toward((0, 0), (0, 5), DIRS)
    assert step == (0, 1)                                  # move right, toward the goal
    nav.observe_move((0, 0), (0, 1), moved=False)          # now right is a known wall
    step2 = nav.step_toward((0, 0), (0, 5), DIRS)
    assert step2 != (0, 1)                                 # must not pick the known wall


def test_decay_reopens_an_old_wall():
    nav = GridNav(ttl=3)
    nav.observe_move((0, 0), (0, 1), moved=False)
    assert nav.is_blocked((0, 0), (0, 1))
    for _ in range(5):
        nav.observe_move((9, 9), (0, 1), moved=True)       # advance time elsewhere
    nav.decay()
    assert not nav.is_blocked((0, 0), (0, 1))              # a stale wall reopens (a trigger may have opened it)


def test_invalidate_reopens_a_wall_whose_cell_changed():
    nav = GridNav()
    nav.observe_move((0, 0), (0, 1), moved=False)          # wall at edge into cell (0,1)
    nav.invalidate([(0, 1)])                               # (0,1)'s pixels changed -> can't trust it as a wall
    assert not nav.is_blocked((0, 0), (0, 1))


def _obj(cells, colour):
    return Object(cells=frozenset(cells), colours=frozenset({colour}))


def test_abduce_target_picks_a_unique_small_landmark():
    objs = [_obj([(0, 0)], 4),                              # the cursor (colour 4)
            _obj([(9, 9)], 7),                              # a UNIQUE small landmark (colour 7 appears once)
            _obj([(1, 1), (1, 2)], 3), _obj([(5, 5), (5, 6)], 3)]   # colour 3 appears twice -> not unique
    tgt = abduce_target(objs, cursor_colour=4)
    assert tgt is not None and 7 in tgt.colours


def test_abduce_target_none_when_no_unique_landmark():
    objs = [_obj([(0, 0)], 4), _obj([(1, 1)], 3), _obj([(2, 2)], 3)]   # colour 3 not unique; only cursor + dupes
    assert abduce_target(objs, cursor_colour=4) is None


# ---------------- loop integration: navigate to the target through a wall ----------------
class MazeMoverWorld:
    """A cursor (colour 4) moving unit steps; a target landmark (colour 7) to the right; a WALL column the
    cursor must go around. The board is small so logical cells == pixels (stride 1)."""

    def __init__(self):
        self.h, self.w = 9, 9
        self.pos = [4, 1]
        self.wall_col = 4                                   # a wall at column 4 (all rows) except a gap at row 5,
        self.gap_row = 5                                   # one row OFF the direct line -> a real reroute is required
        self.secret = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
        self.target = (4, 7)

    def _blocked(self, r, c):
        return c == self.wall_col and r != self.gap_row

    def _frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        for r in range(self.h):
            if r != self.gap_row:
                g[r, self.wall_col] = 2                     # the wall (colour 2)
        g[self.target] = 7                                  # unique landmark
        g[tuple(self.pos)] = 4                              # cursor
        return g

    def frame(self):
        return self._frame()

    def step(self, action):
        dr, dc = self.secret.get(action, (0, 0))
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if 0 <= nr < self.h and 0 <= nc < self.w and not self._blocked(nr, nc):
            self.pos = [nr, nc]                             # move only if not into a wall/off-board
        return self._frame()


def test_loop_navigates_to_target_through_a_wall():
    world = MazeMoverWorld()
    agent = AgentLoop(actions=["U", "D", "L", "R"], background=0)
    reached = False
    for _ in range(150):
        agent.step(world.frame(), world.step)
        if tuple(world.pos) == world.target:
            reached = True
            break
    assert agent.agency.ready()                             # learned its move map
    assert reached, "cursor never reached the target at %s (ended at %s)" % (world.target, world.pos)
    assert len(nav_walls := agent.nav.blocked_edges() if hasattr(agent.nav, "blocked_edges") else
               [k for k, v in agent.nav.edge.items() if v is False]) > 0   # it learned at least one wall by bumping
