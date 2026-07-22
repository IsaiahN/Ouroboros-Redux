"""
redux-triality: the BFS pathfinder (reclaimed from new-horse navigation.py, re-pointed at the DISCOVERED passable
set) fixes the greedy planner's wall-stick. A maze with a wall that forces a detour: greedy (serve φ_goal among
passable one-steps) dead-ends; BFS routes around and reaches the target. Walls are discovered by colour, not baked.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.planner import bfs_path_action, plan_action
from newhorse.redux_arch.dsl import Predicate, make_atom

VECS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}   # stride 1 for the test
ACTS = Predicate(frozenset({make_atom("ACTS_TOWARD")}))
PASS = {0}          # floor colour
WALL = 1


def _maze():
    """11x11, floor=0, a vertical wall (col 5) with a gap only at the BOTTOM (row 10). Avatar top-left, target
    top-right: the ONLY route is down the left, across the bottom gap, up the right -- a hard case for greedy."""
    g = np.zeros((11, 11), dtype=int)
    for r in range(0, 10):        # wall on column 5, rows 0..9; row 10 is the gap
        g[r, 5] = WALL
    return g


def _passable_at(g, cell):
    r, c = cell
    return 0 <= r < 11 and 0 <= c < 11 and int(g[r, c]) in PASS


def _run(agent_fn, start, target, budget=200):
    g = _maze()
    pos = list(start)
    for _ in range(budget):
        if tuple(pos) == target:
            return True, _
        a = agent_fn(g, tuple(pos), target)
        if a is None:
            return False, _
        dr, dc = VECS[a]
        nxt = (pos[0] + dr, pos[1] + dc)
        if _passable_at(g, nxt):
            pos = list(nxt)
    return tuple(pos) == target, budget


def test_bfs_reaches_target_through_the_detour():
    start, target = (0, 0), (0, 10)
    def bfs_agent(g, cur, tgt):
        return bfs_path_action(g, cur, tgt, VECS, PASS, stride=1)
    reached, steps = _run(bfs_agent, start, target)
    assert reached, "BFS failed to route around the wall"


def test_greedy_wall_sticks_on_the_same_maze():
    # greedy serves ACTS_TOWARD among passable one-steps; with the wall between start and target it cannot make
    # toward-progress and dead-ends (never reaches). This is the failure the live ls20 run hit.
    start, target = (0, 0), (0, 10)
    def greedy_agent(g, cur, tgt):
        passable = lambda dest: _passable_at(g, dest)
        return plan_action(cur, tgt, VECS, ACTS, passable)
    reached, _ = _run(greedy_agent, start, target, budget=200)
    assert not reached, "greedy unexpectedly solved the detour maze (test no longer discriminates)"


def test_bfs_heads_to_nearest_passable_when_target_is_a_wall():
    # the target object is NOT floor (like ls20's grey box). BFS should still make progress -- head to the
    # passable cell nearest the target, not return None.
    g = _maze()
    g[0, 10] = 9                                # a non-floor 'object' at the corner (not in PASS)
    a = bfs_path_action(g, (0, 0), (0, 10), VECS, PASS, stride=1)
    assert a in ("D", "R"), a                   # a first step along the only viable route (down or right)
