"""CK-2b falsifier: INVERSE CLOSURE + BACKWARD CHAINING (Klein group; Newell & Simon).

(1) invert_transform gives each typed mechanism a computable inverse: TRANSLATE negates
its deltas, ROTATE(k) -> ROTATE(4-k), REFLECT is self-inverse, COLOUR_PERM reverses its
(injective) pairs, SCALE swaps up<->down; anything not cleanly invertible is None.
(2) apply_inverse steps a FRAME backward through a typed atom -- invert-then-apply is
identity per ttype; raw atoms (no ttype) are NOT invertible and return None.
(3) THE FALSIFIER: a synthetic chain whose goal is reachable in 2k steps (k = the
planner's per-frontier depth). Forward-only BFS (raw atoms -- the graceful-degradation
path) explores depth k and finds NOTHING; the same board with typed atoms lets the
planner run backward from REFERENCE via inverses, meet in the middle, and return a
stitched plan -- whose forward replay from current must reproduce REFERENCE exactly.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


def _E():
    from engines.egocentric import effects as E
    for fn in ("invert_transform", "apply_inverse"):
        if not hasattr(E, fn):
            pytest.fail("effects.%s missing -- CK-2b has not landed" % fn)
    return E


def _P():
    from engines.egocentric import planner as P
    from engines.egocentric.planner import plan_to_identity  # noqa: F401
    return P


# ── (1) the inverse is computable, per ttype ─────────────────────────────────

class TestInvertTransform:

    def test_translate_negates_deltas(self):
        E = _E()
        t, p = E.invert_transform("TRANSLATE", {"dx": 2, "dy": -3, "fill": 7})
        assert t == "TRANSLATE"
        assert p == {"dx": -2, "dy": 3, "fill": 7}

    def test_rotate_is_4_minus_k(self):
        E = _E()
        for k, want in ((1, 3), (2, 2), (3, 1)):
            t, p = E.invert_transform("ROTATE", {"k": k})
            assert t == "ROTATE" and p["k"] == want

    def test_reflect_is_self_inverse(self):
        E = _E()
        for axis in ("h", "v"):
            t, p = E.invert_transform("REFLECT", {"axis": axis})
            assert t == "REFLECT" and p == {"axis": axis}

    def test_colour_perm_reverses_pairs(self):
        E = _E()
        t, p = E.invert_transform("COLOUR_PERM", {"mapping": [[1, 5], [2, 3]]})
        assert t == "COLOUR_PERM"
        assert p["mapping"] == [[3, 2], [5, 1]]

    def test_scale_swaps_up_and_down(self):
        E = _E()
        t, p = E.invert_transform("SCALE", {"fx": 2, "fy": 3, "mode": "up"})
        assert (t, p["fx"], p["fy"], p["mode"]) == ("SCALE", 2, 3, "down")
        t2, p2 = E.invert_transform("SCALE", {"fx": 2, "fy": 3, "mode": "down"})
        assert (t2, p2["fx"], p2["fy"], p2["mode"]) == ("SCALE", 2, 3, "up")

    def test_not_cleanly_invertible_is_none(self):
        E = _E()
        assert E.invert_transform("SCALE", {"fx": 2, "fy": 2, "mode": "sideways"}) is None
        assert E.invert_transform("SCALE", {"fx": 0, "fy": 2, "mode": "up"}) is None
        assert E.invert_transform("REFLECT", {"axis": "diagonal"}) is None
        assert E.invert_transform("NONE", {}) is None
        assert E.invert_transform("MYSTERY", {"x": 1}) is None


# ── (2) invert-then-apply is identity on synthetic patches ───────────────────

class TestApplyInversePerType:

    def test_translate_round_trip(self):
        E = _E()
        before = np.zeros((10, 10), dtype=int)
        before[2, 2], before[2, 3] = 3, 7
        after = np.zeros((10, 10), dtype=int)
        after[2, 5], after[2, 6] = 3, 7
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "TRANSLATE"
        assert (E.apply_effect(atom, before) == after).all()
        back = E.apply_inverse(atom, after)
        assert back is not None and (back == before).all(), (
            "TRANSLATE inverse must move the object straight back")

    def test_rotate_round_trip(self):
        E = _E()
        patch = np.array([[5, 0, 0], [5, 0, 0], [5, 5, 0]])
        before = np.zeros((7, 7), dtype=int)
        before[1:4, 1:4] = patch
        after = np.zeros((7, 7), dtype=int)
        after[1:4, 1:4] = np.rot90(patch, 1)
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "ROTATE" and atom["params"]["k"] == 1
        back = E.apply_inverse(atom, after)
        assert back is not None and (back == before).all(), (
            "ROTATE(1) inverse is ROTATE(3): the patch turns back")

    def test_reflect_round_trip(self):
        E = _E()
        patch = np.array([[1, 2, 0], [0, 1, 1]])
        before = np.zeros((6, 6), dtype=int)
        before[2:4, 1:4] = patch
        after = np.zeros((6, 6), dtype=int)
        after[2:4, 1:4] = np.fliplr(patch)
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "REFLECT" and atom["params"]["axis"] == "v"
        back = E.apply_inverse(atom, after)
        assert back is not None and (back == before).all(), (
            "REFLECT is self-inverse: flipping again restores the patch")

    def test_colour_perm_round_trip(self):
        E = _E()
        before = np.zeros((5, 5), dtype=int)
        before[1:3, 1:3] = np.array([[1, 2], [2, 1]])
        after = np.zeros((5, 5), dtype=int)
        after[1:3, 1:3] = np.array([[5, 3], [3, 5]])
        atom = E.learn_effect(before, 6, after)
        assert atom.get("ttype") == "COLOUR_PERM"
        back = E.apply_inverse(atom, after)
        assert back is not None and (back == before).all(), (
            "COLOUR_PERM inverse maps every colour home (injective by construction)")

    def test_scale_round_trip_on_patches(self):
        E = _E()
        small = np.array([[1, 2], [3, 4]])
        big = np.kron(small, np.ones((2, 3), dtype=int))
        t, p = E.invert_transform("SCALE", {"fx": 2, "fy": 3, "mode": "up"})
        assert (t, p["mode"]) == ("SCALE", "down")
        assert (big[::p["fx"], ::p["fy"]] == small).all(), (
            "down(up(patch)) is the patch itself")
        t2, p2 = E.invert_transform(t, p)                 # invert twice: back to up
        assert (t2, p2["mode"]) == ("SCALE", "up")
        assert (np.kron(small, np.ones((p2["fx"], p2["fy"]), dtype=int)) == big).all()

    def test_raw_atoms_are_not_invertible(self):
        E = _E()
        before = np.zeros((10, 10), dtype=int)
        before[2, 2], before[2, 3] = 3, 7
        after = np.zeros((10, 10), dtype=int)
        after[2, 5], after[2, 6] = 3, 7
        atom = E.learn_effect(before, 6, after)
        raw = {k: v for k, v in atom.items() if k not in ("ttype", "params")}
        assert E.apply_inverse(raw, after) is None, (
            "a raw atom names no mechanism -- there is nothing to invert")


# ── (3) THE FALSIFIER: meet-in-the-middle beats forward-only under one budget ─

def _chain_gamma(tmp_path, name: str, n: int, typed: bool):
    """n one-cell recolour atoms v -> v+1 (v = 3..3+n-1). Typed -> COLOUR_PERM atoms
    (invertible); typed=False strips the ttype -> raw atoms (forward-only)."""
    from engines.egocentric import effects as E
    g = E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))
    for v in range(3, 3 + n):
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = v
        a = b.copy()
        a[2, 2] = v + 1
        atom = E.learn_effect(b, 6, a)
        if typed:
            assert atom.get("ttype") == "COLOUR_PERM", "chain atoms must be typed"
        else:
            atom.pop("ttype", None)
            atom.pop("params", None)
        g.add(atom, game="g1", level=1)
    return g


class TestBackwardChaining:
    K = 8                                                 # the planner's per-frontier depth

    def _boards(self):
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int)
        ref[2, 2] = 3 + 2 * self.K
        return ws, ref

    def test_forward_only_finds_nothing_at_2k(self, tmp_path):
        """Raw atoms: no inverses exist, the planner degrades to forward-only BFS,
        depth k -- and the 2k-step goal is out of reach. This MUST hold or the
        bidirectional test proves nothing."""
        P = _P()
        g = _chain_gamma(tmp_path, "raw", n=2 * self.K, typed=False)
        ws, ref = self._boards()
        out = P.plan_to_identity(ws, ref, g, game="g1", level=1,
                                 budget=1000, cost_per_action=1)
        assert out is None, "forward-only BFS under depth k must NOT reach 2k"

    def test_bidirectional_meets_in_the_middle(self, tmp_path):
        """Typed atoms: backward frontier from REFERENCE via inverses meets the forward
        frontier; the stitched plan is 2k forward-direction atom ids and its REPLAY from
        current reproduces REFERENCE exactly."""
        P = _P()
        g = _chain_gamma(tmp_path, "typed", n=2 * self.K, typed=True)
        ws, ref = self._boards()
        out = P.plan_to_identity(ws, ref, g, game="g1", level=1,
                                 budget=1000, cost_per_action=1)
        assert out is not None, "bidirectional search must find the meet"
        assert len(out["steps"]) == 2 * self.K
        assert out["feasible"] is True
        cur = ws
        for aid in out["steps"]:                          # the replay IS the verdict
            cur = g.apply(aid, cur)
            assert cur is not None, "every stitched step must fire forward"
        assert (cur == ref).all(), (
            "applying the stitched plan forward from current must reproduce REFERENCE")

    def test_forward_fallback_still_plans_short_goals(self, tmp_path):
        """Graceful degradation: a raw-only Gamma still plans what forward BFS can
        reach -- backward chaining is an extension, never a regression."""
        P = _P()
        g = _chain_gamma(tmp_path, "short", n=2, typed=False)
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int)
        ref[2, 2] = 5
        out = P.plan_to_identity(ws, ref, g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is not None and len(out["steps"]) == 2 and out["feasible"] is True

    def test_mixed_gamma_degrades_gracefully(self, tmp_path):
        """A Gamma holding BOTH typed and raw atoms: raw atoms simply never join the
        backward frontier; the typed chain still meets in the middle."""
        from engines.egocentric import effects as E
        P = _P()
        g = _chain_gamma(tmp_path, "mixed", n=2 * self.K, typed=True)
        b = np.zeros((5, 5), dtype=int)
        b[0, 0] = 1
        a = b.copy()
        a[0, 0] = 2
        raw = E.learn_effect(b, 6, a)
        raw.pop("ttype", None)
        raw.pop("params", None)
        g.add(raw, game="g1", level=1)                    # an uninvertible bystander
        ws, ref = self._boards()
        out = P.plan_to_identity(ws, ref, g, game="g1", level=1,
                                 budget=1000, cost_per_action=1)
        assert out is not None and len(out["steps"]) == 2 * self.K
        cur = ws
        for aid in out["steps"]:
            cur = g.apply(aid, cur)
        assert cur is not None and (cur == ref).all()
