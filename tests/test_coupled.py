"""
redux-triality: the two-body perception (reclaimed from new-horse coupled_agency.py) finds BOTH bodies and reads
the MIRROR coupling / conserved quantity -- validated on a synthetic mirror world AND on a real m0r0 recording.
This is the organ a single-body navigator lacks (why the current agent wins 0 on m0r0).
"""
import sys, os, glob, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.coupled import (TwoBodyAgency, find_two_body_colour, learn_two_body,
                                         two_body_drive_action, two_body_search_action)
from scipy import ndimage as _nd


class TwoHalfMaze:
    """13x13, floor 0, a wall on col 6 for rows 0..8 with a CHANNEL open at rows 9..12. Two bodies (colour 7),
    one each side. U/D move both the same; Cv (converge) L+col/R-col; Dv diverge. A body is blocked by wall/edge.
    The only way for the bodies to MEET is DOWN to the channel then converge across it -- greedy stalls at the
    wall (col 6, row 2), the joint search routes through the channel."""
    def __init__(self):
        self.g = np.zeros((13, 13), dtype=int); self.g[0:9, 6] = 1
        self.L = [2, 3]; self.R = [2, 9]

    def _pass(self, cell):
        r, c = cell; return 0 <= r < 13 and 0 <= c < 13 and self.g[r, c] == 0

    def frame(self):
        f = self.g.copy(); f[tuple(self.L)] = 7; f[tuple(self.R)] = 7; return f

    def step(self, a):
        if a in ("U", "D"):
            d = (-1, 0) if a == "U" else (1, 0)
            for b in (self.L, self.R):
                nb = (b[0] + d[0], b[1] + d[1])
                if self._pass(nb): b[0], b[1] = nb
        elif a in ("Cv", "Dv"):
            dl = 1 if a == "Cv" else -1
            if self._pass((self.L[0], self.L[1] + dl)): self.L[1] += dl
            if self._pass((self.R[0], self.R[1] - dl)): self.R[1] -= dl
        return self.frame()


def _bodies_of(frame, colour=7):
    m = frame == colour; lab, k = _nd.label(m); cs = []
    for i in range(1, k + 1):
        ys, xs = np.where(lab == i); cs.append((round(ys.mean()), round(xs.mean())))
    return sorted(cs, key=lambda p: p[1])


def _drive(world, chooser, budget=200):
    for _ in range(budget):
        b = _bodies_of(world.frame())
        if len(b) < 2 or abs(b[0][0] - b[1][0]) + abs(b[0][1] - b[1][1]) <= 1:
            return True
        a = chooser(b)
        if a is None:
            return False
        world.step(a)
    return False


def test_joint_search_merges_where_greedy_stalls():
    warm = TwoHalfMaze()
    frames = [warm.frame()]; acts = ["RESET"]
    for a in (["U", "D", "Cv", "Dv"] * 4):
        frames.append(warm.step(a)); acts.append(a)
    colour, ag = learn_two_body(frames, acts)
    assert colour == 7 and ag.ready()
    pass_px = lambda i, dest: TwoHalfMaze()._pass(dest)          # shared static maze
    # GREEDY stalls at the wall:
    greedy = _drive(TwoHalfMaze(), lambda b: two_body_drive_action(b, ag, pass_px))
    assert greedy is False, "greedy unexpectedly merged (test no longer discriminates)"
    # JOINT SEARCH routes down through the channel and merges:
    searched = _drive(TwoHalfMaze(), lambda b: two_body_search_action(b, ag, lambda i, c: TwoHalfMaze()._pass(c), 1))
    assert searched is True, "joint search failed to merge the two bodies"


class MirrorWorld:
    """Two bodies (colour 7) on a 20x20 field. ACTION1/2 move both vertically the SAME way; ACTION3/4 move them
    MIRRORED horizontally (opposite columns) -> col-sum invariant. Exactly m0r0's measured coupling."""
    def __init__(self):
        self.L = [10, 4]; self.R = [10, 15]
        self.mv = {"U": (-1, 0), "D": (1, 0), "Lm": (0, -1), "Rm": (0, 1)}

    def frame(self):
        g = np.zeros((20, 20), dtype=int)
        g[tuple(self.L)] = 7; g[tuple(self.R)] = 7
        return g

    def step(self, a):
        d = self.mv[a]
        if a in ("U", "D"):                                  # same direction (both bodies)
            self.L = [self.L[0] + d[0], self.L[1] + d[1]]; self.R = [self.R[0] + d[0], self.R[1] + d[1]]
        else:                                                # mirrored horizontally
            self.L = [self.L[0], self.L[1] + d[1]]; self.R = [self.R[0], self.R[1] - d[1]]
        return self.frame()


def test_two_body_perception_reads_the_mirror_coupling_synthetic():
    w = MirrorWorld()
    frames = [w.frame()]; acts = ["RESET"]
    seq = ["U", "D", "Lm", "Rm"] * 6
    for a in seq:
        frames.append(w.step(a)); acts.append(a)
    colour, ag = learn_two_body(frames, acts)
    assert colour == 7 and ag.n_controllable() == 2 and ag.ready()
    m0, m1 = ag.body_map(0), ag.body_map(1)
    assert m0["U"] == (-1, 0) and m1["U"] == (-1, 0)         # vertical: same direction
    assert m0["Lm"][1] == -m1["Lm"][1]                       # horizontal: opposite columns (mirror)
    assert ag.conserved().get("col_sum") is True             # (cL+cR) column-sum invariant


def test_driver_meets_the_two_bodies_via_the_coupling():
    # learn the mirror coupling, then DRIVE the two bodies to MEET (inter-body distance -> adjacent). The win
    # relation for m0r0 is "the two bodies become one component"; the driver reduces their separation.
    w = MirrorWorld()
    frames = [w.frame()]; acts = ["RESET"]
    for a in (["U", "D", "Lm", "Rm"] * 5):
        frames.append(w.step(a)); acts.append(a)
    colour, ag = learn_two_body(frames, acts)
    assert ag.ready()
    # translate the learned world-action labels back through the SAME world; drive toward MEET
    def passable(i, dest):
        return 0 <= dest[0] < 20 and 0 <= dest[1] < 20        # open field (no walls needed for this convergence)
    w2 = MirrorWorld()
    def bodies():
        m = w2.frame() == 7
        from scipy import ndimage as _nd
        lab, k = _nd.label(m); cs = []
        for i in range(1, k + 1):
            ys, xs = np.where(lab == i); cs.append((round(ys.mean()), round(xs.mean())))
        return sorted(cs, key=lambda p: p[1])
    met = False
    for _ in range(30):
        b = bodies()
        if len(b) < 2:
            met = True; break                                # merged into one component
        if abs(b[0][0] - b[1][0]) + abs(b[0][1] - b[1][1]) <= 1:
            met = True; break
        a = two_body_drive_action(b, ag, passable)
        if a is None:
            break
        w2.step(a)
    assert met, "driver failed to bring the two bodies together"


def test_two_body_perception_on_real_m0r0_recording():
    hits = glob.glob(os.path.join(os.path.dirname(__file__), "..", "recordings", "*", "m0r0-*.jsonl"))
    if not hits:
        import pytest; pytest.skip("no m0r0 recording on disk")
    recs = [json.loads(l)["data"] for l in open(sorted(hits)[0]).read().splitlines()]
    frames = [np.array(r["frame"])[-1] for r in recs]
    acts = [r.get("action_input", {}).get("id", "?") for r in recs]
    colour, ag = learn_two_body(frames[:40], acts[:40])
    assert colour == 10, colour                              # the navy bodies
    assert ag.n_controllable() == 2
    m0, m1 = ag.body_map(0), ag.body_map(1)
    # ACTION3 was measured as L col -5 / R col +5 (mirror); ACTION1 both up
    assert "ACTION3" in m0 and m0["ACTION3"][1] == -m1["ACTION3"][1] and m0["ACTION3"][1] != 0
    assert ag.conserved().get("col_sum") is True             # column-sum invariant under the mirror
