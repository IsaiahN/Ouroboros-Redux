"""
Tests for brick 25 CARVE 1: multi-controllable perception (CoupledAgency).

Rendered + measured on m0r0 and ka59: both are TWO-BODY games where a shared action moves both bodies, MIRRORED
on the horizontal axis (one left, one right). The single-cursor agency can't model this. CoupledAgency must:
detect the 2 bodies, learn EACH body's per-action displacement, and READ the conserved quantity (column-sum is
invariant under mirror moves) -- the barrier the planner must later break with a wall.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.coupled_agency import CoupledAgency


class MirrorTwoBodyWorld:
    """Two bodies of the same colour (8). ACTION1/2 move BOTH up/down together (parallel); ACTION3/4 move them
    in OPPOSITE columns (mirror) -- so column-sum is conserved, exactly m0r0's structure. Small board, stride 1."""

    def __init__(self):
        self.h, self.w = 12, 20
        self.L = [6, 4]     # left body [row,col]
        self.R = [6, 15]    # right body
        self.secret = {"U": ((-1, 0), (-1, 0)), "D": ((1, 0), (1, 0)),      # vertical: parallel
                       "L": ((0, -1), (0, 1)), "R": ((0, 1), (0, -1))}      # horizontal: MIRROR

    def frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        g[tuple(self.L)] = 8
        g[tuple(self.R)] = 8
        return g

    def step(self, action):
        (dl, dr) = self.secret.get(action, ((0, 0), (0, 0)))
        for body, d in ((self.L, dl), (self.R, dr)):
            nr, nc = body[0] + d[0], body[1] + d[1]
            if 0 <= nr < self.h and 0 <= nc < self.w:
                body[0], body[1] = nr, nc
        return self.frame()


def test_detects_two_bodies_and_learns_each_map():
    world = MirrorTwoBodyWorld()
    ag = CoupledAgency(colour=8, background=0)
    acts = ["U", "D", "L", "R"]
    for i in range(60):
        before = world.frame()
        a = acts[i % len(acts)]
        after = world.step(a)
        ag.observe(before, a, after)
    assert ag.n_controllable() == 2, ag.n_controllable()
    assert ag.ready()
    left, right = ag.body_map(0), ag.body_map(1)
    # body 0 is the left one (sorted by column); ACTION 'L' sends it left, the right body right (mirror)
    assert left["L"] == (0, -1) and right["L"] == (0, 1), (left, right)
    assert left["R"] == (0, 1) and right["R"] == (0, -1), (left, right)
    assert left["U"] == (-1, 0) and right["U"] == (-1, 0), (left, right)   # vertical parallel


def test_reads_the_conserved_column_sum():
    world = MirrorTwoBodyWorld()
    ag = CoupledAgency(colour=8, background=0)
    acts = ["U", "D", "L", "R"]
    for i in range(60):
        before = world.frame(); a = acts[i % len(acts)]
        after = world.step(a); ag.observe(before, a, after)
    cons = ag.conserved_axes()
    # mirror horizontal + parallel vertical => COLUMN-SUM is invariant under every action; row-diff is invariant
    # (rows always move together). The planner reads col_sum=True as the barrier to break with a wall.
    assert cons.get("col_sum") is True, cons
    assert cons.get("col_diff") is False, cons          # ACTION L/R DO change the column difference
    assert cons.get("row_diff") is True, cons           # rows move in lockstep -> their difference is fixed


def test_single_body_is_not_flagged_coupled():
    # a lone body -> n_controllable 1, not "ready" as a coupled system (don't hallucinate coupling)
    ag = CoupledAgency(colour=8, background=0)
    pos = [5, 5]
    for i in range(20):
        g = np.zeros((10, 10), int); g[tuple(pos)] = 8; before = g.copy()
        pos[1] = min(9, pos[1] + 1)
        after = np.zeros((10, 10), int); after[tuple(pos)] = 8
        ag.observe(before, "R", after)
    assert ag.n_controllable() == 1
    assert not ag.ready()
    assert ag.conserved_axes() == {}
