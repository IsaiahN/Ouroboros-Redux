"""W4 QA routed fixes — regression gate.

F1 engines/reasoning/symbolic_reasoning_engine.py: symbolic-integration enablement is a
   caller decision (constructor parameter, default disabled) — no game-id list anywhere.
F2 engines/cognition/cognitive_router.py: the "player not localised" sentinel is the
   board's own center (h//2, w//2) derived from the frame in the context — a memorized
   absolute coordinate never decides.
F3 engines/egocentric/perception.py + agency.py: scipy is optional — label_components
   dispatches to scipy.ndimage.label when installed and to a behaviorally equivalent
   pure-numpy fallback (same counts, same membership) on a bare interpreter.
F4 settlements carry atom identity: the bank's known-atom WORKSPACE settlement names
   WHICH atom bet ("atom_key"); BetBook.settle threads it (with the routed bin) into
   the fabric "settlements" record — the n=1 metric's linkage, additive, null-safe.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


# ── F1: symbolic integration is caller-opt-in, never game-id-keyed ────────────

class TestSymbolicEnablementIsCallerOptIn:

    def test_disabled_by_default(self):
        from engines.reasoning.symbolic_reasoning_engine import SymbolicGameplayIntegration
        integ = SymbolicGameplayIntegration("any_game")
        assert integ.enabled is False
        assert integ.should_use_symbolic(1) is False

    def test_caller_opts_in_regardless_of_game(self):
        from engines.reasoning.symbolic_reasoning_engine import SymbolicGameplayIntegration
        for game in ("game_a", "game_b", "totally_new_game"):
            assert SymbolicGameplayIntegration(game, enabled=True).enabled is True

    def test_factory_config_is_data_not_game_id(self):
        from engines.reasoning.symbolic_reasoning_engine import (
            ObjectType,
            create_symbolic_engine_for_game,
        )
        engine = create_symbolic_engine_for_game(
            "any_game", level=1,
            color_mappings={1: ObjectType.AGENT, 2: ObjectType.GOAL},
            min_learning_actions=12)
        assert engine.min_learning_actions == 12
        assert engine.parser.color_mappings[1] is ObjectType.AGENT
        # default: no per-game overrides at all
        default = create_symbolic_engine_for_game("other_game")
        assert default.min_learning_actions == 8


# ── F2: the localiser sentinel is the board's own center ──────────────────────

class TestBoardCenterSentinel:

    def _center(self, game_state):
        from engines.cognition.cognitive_router import _board_center
        return _board_center(game_state)

    def test_default_64x64_board_keeps_old_behavior(self):
        frame = [[0] * 64 for _ in range(64)]
        assert self._center({"frame_data": frame}) == (32, 32)

    def test_no_frame_falls_back_to_standard_extent(self):
        assert self._center({}) == (32, 32)
        assert self._center({"frame_data": None}) == (32, 32)

    def test_nested_animation_frames_unwrap(self):
        frame = [[[0] * 64 for _ in range(64)]]        # API frame: list of grids
        assert self._center({"frame_data": frame}) == (32, 32)

    def test_center_tracks_the_actual_board_shape(self):
        frame = [[0] * 32 for _ in range(16)]
        assert self._center({"frame_data": frame}) == (8, 16)

    def test_numpy_frames_use_shape(self):
        assert self._center({"frame_data": np.zeros((48, 64), dtype=int)}) == (24, 32)


# ── F3: scipy-free labeling, behaviorally equivalent to scipy ─────────────────

class TestScipyFreeLabeling:

    def _masks(self):
        rng = np.random.RandomState(7)
        yield np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], dtype=bool)
        for density in (0.2, 0.5, 0.8):
            yield rng.rand(24, 31) < density

    @staticmethod
    def _centroids(lab, n):
        return sorted(
            (float(np.mean(np.where(lab == i)[0])), float(np.mean(np.where(lab == i)[1])))
            for i in range(1, n + 1))

    def test_pure_fallback_matches_scipy_counts_and_centroids(self):
        pytest.importorskip("scipy")
        from scipy import ndimage

        from engines.egocentric.perception import _label_pure
        for connectivity in (1, 2):
            structure = ndimage.generate_binary_structure(2, connectivity)
            for mask in self._masks():
                s_lab, s_n = ndimage.label(mask, structure=structure)
                p_lab, p_n = _label_pure(mask, connectivity)
                assert p_n == int(s_n), "component count diverges from scipy"
                assert np.allclose(self._centroids(p_lab, p_n),
                                   self._centroids(s_lab, int(s_n))), (
                    "component centroids diverge from scipy")

    def test_dispatch_survives_scipy_absence(self, monkeypatch):
        from engines.egocentric import perception
        monkeypatch.setattr(perception, "_ndimage", None)
        mask = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], dtype=bool)
        _, n4 = perception.label_components(mask, 1)
        _, n8 = perception.label_components(mask, 2)
        assert n4 == 5 and n8 == 1

    def test_segment_and_cursor_centroid_scipy_free(self, monkeypatch):
        from engines.egocentric import perception
        from engines.egocentric.agency import CursorAgency
        monkeypatch.setattr(perception, "_ndimage", None)
        grid = np.zeros((8, 8), dtype=int)
        grid[1:3, 1:3] = 4
        grid[5, 6] = 2
        objs = perception.segment(grid)
        assert {frozenset(o.cells) for o in objs} == {
            frozenset({(1, 1), (1, 2), (2, 1), (2, 2)}),
            frozenset({(5, 6)}),
        }
        # agency tracks the LARGEST component of a colour, scipy-free
        frame = np.zeros((8, 8), dtype=int)
        frame[1:3, 1:3] = 3                              # the body (4 cells)
        frame[6, 6] = 3                                  # a static same-colour twin
        cen = CursorAgency()._centroid(frame, 3)
        assert cen == (1.5, 1.5)


# ── F4: settlements carry atom identity ───────────────────────────────────────

class TestSettlementAtomIdentity:

    def _fab(self, tmp_path):
        from engines.egocentric.fabric import KnowledgeFabric
        return KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")

    def _minted(self, fab):
        """One learned EFFECT atom in Gamma; returns (gamma, atom id, before, after)."""
        from engines.egocentric.effects import Gamma, learn_effect
        g = Gamma(fab)
        before = np.zeros((5, 5), dtype=int)
        before[1:3, 1:3] = np.array([[1, 2], [3, 4]])
        after = before.copy()
        after[1:3, 1:3] = np.array([[5, 6], [7, 8]])
        atom = learn_effect(before, 6, after)
        assert atom is not None and atom.get("kind") == "EFFECT"
        aid = g.add(atom, "g1", 1)
        return g, aid, before, after

    def test_bank_workspace_settlement_names_which_atom_bet(self, tmp_path):
        from engines.egocentric.bank import PredictorBank
        fab = self._fab(tmp_path)
        g, aid, before, after = self._minted(fab)
        bank = PredictorBank(gamma=g, game="g1", level=1)
        bank.commit({"WORKSPACE": before}, action=6)
        stl = bank.settle({"WORKSPACE": after})["WORKSPACE"]
        assert stl["from_known_atom"] is True
        assert stl["atom_key"] == aid

    def test_betbook_record_carries_atom_key_and_bin(self, tmp_path):
        from engines.egocentric.betting import BetBook
        b = BetBook(self._fab(tmp_path), agent_id="a", game="g1")
        before = np.zeros((4, 4), dtype=int)
        after = before.copy()
        after[1, 1] = 5
        b.commit(action=6, before=before, paste=before.copy(), transform=None)
        out = b.settle(post=after, executed_action=6,
                       atom_key="eff-abc:0", atom_bin="TRANSFERRED")
        assert out["atom_key"] == "eff-abc:0"
        rec = b.fabric.query("collective", "settlements")[-1]
        assert rec["atom_key"] == "eff-abc:0"
        assert rec["atom_bin"] == "TRANSFERRED"

    def test_betbook_without_atom_writes_null(self, tmp_path):
        from engines.egocentric.betting import BetBook
        b = BetBook(self._fab(tmp_path), agent_id="a", game="g1")
        before = np.zeros((4, 4), dtype=int)
        b.commit(action=6, before=before, paste=before.copy(), transform=None)
        b.settle(post=before.copy(), executed_action=6)
        rec = b.fabric.query("collective", "settlements")[-1]
        assert rec["atom_key"] is None
        assert rec["atom_bin"] is None

    def test_n1_metric_measures_linkage_on_new_records(self, tmp_path):
        from engines.egocentric.betting import BetBook
        fab = self._fab(tmp_path)
        _, aid, before, after = self._minted(fab)
        b = BetBook(fab, agent_id="a", game="g1")
        b.commit(action=6, before=before, paste=after.copy(), transform=None)
        b.settle(post=after, executed_action=6, atom_key=aid, atom_bin="TRANSFERRED")
        spec = importlib.util.spec_from_file_location(
            "n1_metric_under_test", os.path.join(REPO, "tools", "n1_metric.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rc = mod.main([str(tmp_path / "f")])
        assert rc == 0, "n=1 metric still reports MISSING LINKAGE on new-shape records"
