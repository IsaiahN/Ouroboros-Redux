"""Two-COLOUR coupling recall (beat J). Beat I's investigation of ka59 (charter says two-body; rendered = a single
cursor navigating two regions, correctly routed DIRECTIONAL) surfaced a real generalization gap: the coupling
detector only found SAME-colour two-body pairs, so two DIFFERENT-coloured co-moving bodies (a common ARC pattern,
likely on the eval set) were invisible. This adds the two-colour case. Precision is preserved by the SAME downstream
gate: `is_coupled` still requires co-movement under >= min_both actions AND a conserved sum/diff invariant, so two
UNRELATED different-coloured movers are still rejected. Names no game; the dev set has no two-colour coupler (verified
m0r0 stays same-colour two_body, ka59 directional, tr87 effect), so this is eval-facing recall, honestly labelled."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.coupled import (find_two_colour_bodies, learn_two_body, TwoBodyAgency)
from newhorse.redux_arch.live_goal_run import _two_bodies


def _mirror_world():
    """Two different-coloured 1x1 bodies on bg=0: RED (colour 2) left, BLUE (colour 3) right. Four co-moving actions
    so the >=3 co-move + conserved-invariant gate is genuinely exercised: A3/A4 mirror in col (col-sum conserved),
    A1/A2 rigid in row (row-diff conserved). Returns (frames, acts)."""
    frames, acts = [], []
    red = [5, 4]; blue = [5, 11]                              # [row, col]
    def draw():
        g = np.zeros((10, 16), dtype=int)
        g[red[0], red[1]] = 2; g[blue[0], blue[1]] = 3
        return g
    frames.append(draw()); acts.append("RESET")
    for a in ["A3", "A4", "A1", "A2", "A3", "A4", "A1", "A2"]:
        if a == "A3":                                        # mirror col: red +1, blue -1
            red[1] += 1; blue[1] -= 1
        elif a == "A4":                                      # mirror col: red -1, blue +1
            red[1] -= 1; blue[1] += 1
        elif a == "A1":                                      # rigid up: both row -1
            red[0] -= 1; blue[0] -= 1
        elif a == "A2":                                      # rigid down: both row +1
            red[0] += 1; blue[0] += 1
        frames.append(draw()); acts.append(a)
    return frames, acts


def _independent_world():
    """Two different-coloured bodies that move INDEPENDENTLY (no conserved relation): red moves on A3 only, blue on
    A1 only. Should be detected as a candidate PAIR but rejected by is_coupled (no co-move, no invariant)."""
    frames, acts = [], []
    red = [5, 2]; blue = [2, 12]
    def draw():
        g = np.zeros((10, 16), dtype=int)
        g[red[0], red[1]] = 2; g[blue[0], blue[1]] = 3
        return g
    frames.append(draw()); acts.append("RESET")
    for a in ["A3", "A1", "A3", "A1", "A3", "A1"]:
        if a == "A3":
            red[1] += 1                                      # only red moves
        elif a == "A1":
            blue[0] -= 1                                     # only blue moves
        frames.append(draw()); acts.append(a)
    return frames, acts


def test_detects_two_different_coloured_movers():
    frames, _ = _mirror_world()
    pair = find_two_colour_bodies(frames)
    assert pair == (2, 3)                                     # both colours mobile -> surfaced as the pair


def test_two_colour_mirror_is_coupled():
    frames, acts = _mirror_world()
    colour, ag = learn_two_body(frames, acts)
    assert colour == (2, 3) and ag is not None
    assert ag.two_colour is True
    assert ag.n_controllable() == 2
    assert ag.is_coupled()                                    # co-moves under >= min_both actions + conserved invariant
    # bodies recoverable per-frame for the driver
    assert len(_two_bodies(frames[-1], (2, 3))) == 2


def test_two_independent_movers_not_coupled():
    frames, acts = _independent_world()
    colour, ag = learn_two_body(frames, acts)
    # even if a pair is surfaced, the invariant gate rejects it -> NOT accepted as two-body
    if ag is not None and getattr(ag, "two_colour", False):
        assert not ag.is_coupled()                            # precision: no conserved coupling


def test_same_colour_still_preferred_when_present():
    """A same-colour two-body world must still resolve via the same-colour path (back-compat), not the two-colour one."""
    frames, acts = [], []
    a, b = [5, 3], [5, 10]                                    # two colour-2 bodies, mirror in col
    def draw():
        g = np.zeros((10, 16), dtype=int); g[a[0], a[1]] = 2; g[b[0], b[1]] = 2; return g
    frames.append(draw()); acts.append("RESET")
    for act in ["A3", "A4", "A1", "A2", "A3", "A4", "A1", "A2"]:
        if act == "A3":
            a[1] += 1; b[1] -= 1                              # mirror col
        elif act == "A4":
            a[1] -= 1; b[1] += 1
        elif act == "A1":
            a[0] -= 1; b[0] -= 1                              # rigid row
        elif act == "A2":
            a[0] += 1; b[0] += 1
        frames.append(draw()); acts.append(act)
    colour, ag = learn_two_body(frames, acts)
    assert colour == 2                                        # int, not a tuple -> same-colour path won
    assert ag.is_coupled()
