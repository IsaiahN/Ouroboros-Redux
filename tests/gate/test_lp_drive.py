"""G-D GATE: the LP drive — C33's three-arm control, finally run (PREREG_FINAL_GAPS.md).

LP_DRIVE_ARM selects the arm per worker: "fixed" (default) and "random" leave the
loop's choice path BYTE-IDENTICAL to current behavior (random exists as a label for
the control harness — C33 §1: the presupposition retires against RANDOM, not fixed);
"lp" is a pure, bounded steering signal that reweights EXPLORATION toward sites whose
recent NOVEL-bin residuals were LARGE and COMPRESSIBLE — the router's persisted
import_queue records scored by the mint's own published MDL inequality and its
ledgered surprise-support "w" (the mint's output AIMS, it is never a metric).

Prereg falsifiers pinned here: fixed/random arms byte-identical to current given
identical seeds (the loop's choice path driven directly); the lp arm reweights toward
the high-|R|-compressible synthetic site; the signal is pure/replayable and bounded;
[LP] narration appears on the lp arm only; supervisor arm assignment deterministic
(sha1 mod 3 — stable across processes); the .credit/.route window laws hold, measured.
"""
from __future__ import annotations

import ast
import hashlib
import os
import random
import sys
from types import SimpleNamespace

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.affect import AffectGains
from engines.egocentric.fabric import KnowledgeFabric

GAME = "g1"


def _LP():
    try:
        from engines.egocentric.lp_drive import (
            LPDrive,  # noqa: F401 -- the import IS the availability probe
            arm,  # noqa: F401
            assign_arm,  # noqa: F401
        )
    except Exception as e:
        pytest.fail("engines.egocentric.lp_drive missing (%s) -- G-D has not landed" % e)
    from engines.egocentric import lp_drive
    return lp_drive


def _loop_src():
    with open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
              errors="replace") as f:
        return f.read()


def _supervisor_src():
    with open(os.path.join(REPO, "tools", "swarm_supervisor.py"), encoding="utf-8",
              errors="replace") as f:
        return f.read()


# ── the synthetic NOVEL-bin evidence (all frames derived, no magic constants) ────────

def _compressible_pair():
    """A 2x2 recolour on 8x8: changed=4, bbox 4 < 32, cost 5 < 0.9*R=8.1 -> a pocket.
    The site covers cells x,y in {1,2} -- candidate (2,2) sits inside it."""
    b = np.zeros((8, 8), dtype=int)
    b[1:3, 1:3] = 3
    a = np.zeros((8, 8), dtype=int)
    a[1:3, 1:3] = 5
    return b, a


def _incompressible_pair():
    """Two far corners changed on 8x8: bbox 64 >= 0.5*64 -- no pocket, never aimed at."""
    b = np.zeros((8, 8), dtype=int)
    a = np.zeros((8, 8), dtype=int)
    a[0, 0] = 1
    a[7, 7] = 2
    return b, a


def _enqueue(fab, before, after, residual):
    """One NOVEL-bin record in the POST-FIX live shape (Fig 9,
    test_queue_characterization.py): sigma always, bbox-cropped patches when
    the changed region is a pocket -- exactly what W4c-4 writes. Sigma-less
    records are structurally inert to the drive (the arm-clock restart)."""
    from engines.egocentric import consumer
    rec = {"slot": "WORKSPACE", "residual": float(residual)}
    rec.update(consumer.characterize(before, after, slot="WORKSPACE",
                                     residual=residual))
    return fab.append("collective", "import_queue", rec)


def _armed_fabric(tmp_path, name="f"):
    """A fabric whose ledger carries one LARGE+COMPRESSIBLE NOVEL residual around
    (2,2) and one small incompressible one around (5,5), plus mint w evidence."""
    fab = KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")
    cb, ca = _compressible_pair()
    _enqueue(fab, cb, ca, residual=9.0)
    ib, ia = _incompressible_pair()
    _enqueue(fab, ib, ia, residual=1.0)
    fab.append("collective", "mint_verdicts",
               {"verdict": "mint", "game": GAME, "level": 1, "key": "k1", "w": 1.0})
    return fab


# ── driving the loop's ACTUAL choice path (SPEED 3a, the explore-widen site) ─────────

class _Map:
    def __init__(self, productive):
        self.productive = productive

    def get_productive_targets(self):
        return self.productive


def _stub_loop(affect, productive):
    return SimpleNamespace(
        _causal_map=_Map(productive), _goal_cells_total=4,
        _available_actions=[1, 6], _productive_rotation_index=0,
        _ego_explore_widen=1.0, _decision_system=None,
        _agent_position=None, _affect=affect, _game_id=GAME)


def _drive(stub, n):
    """n passes through CognitiveLoop._act on the explore path, seeds pinned."""
    from cognitive_loop import CognitiveLoop
    random.seed(1234)
    np.random.seed(1234)
    out = []
    for _ in range(n):
        cf = SimpleNamespace(plan_length=0)
        a, d = CognitiveLoop._act(stub, None, "explore", 0.5, None, None,
                                  "agent", "role", 0.0, 0.0, cf)
        out.append((a, None if d is None else dict(d)))
    return out


# Current behavior at the explore-widen site, replicated as the reference: rotate
# among the top-3 productive targets (widen 1.0), index modulo top_n.
_PRODUCTIVE4 = [((7, 1), 0.9), ((5, 5), 0.8), ((2, 2), 0.7), ((3, 3), 0.6)]
_REFERENCE6 = [(6, {"x": 7, "y": 1}), (6, {"x": 5, "y": 5}), (6, {"x": 2, "y": 2}),
               (6, {"x": 7, "y": 1}), (6, {"x": 5, "y": 5}), (6, {"x": 2, "y": 2})]


class TestTheArms:

    def test_default_and_unknown_arms_are_fixed(self, monkeypatch):
        lp = _LP()
        monkeypatch.delenv("LP_DRIVE_ARM", raising=False)
        assert lp.arm() == "fixed", "no env -> the fixed arm (current behavior)"
        monkeypatch.setenv("LP_DRIVE_ARM", "emotional")
        assert lp.arm() == "fixed", "an unknown arm label must fall back to fixed"
        monkeypatch.setenv("LP_DRIVE_ARM", "LP")
        assert lp.arm() == "lp", "arm labels are case-insensitive"

    def test_fixed_arm_is_byte_identical_to_current(self, tmp_path, monkeypatch):
        """Even with live signal in the ledger, the fixed arm's choice path equals
        the pre-G-D rotation exactly, and the candidate list is untouched."""
        _LP()
        monkeypatch.setenv("LP_DRIVE_ARM", "fixed")
        affect = AffectGains(_armed_fabric(tmp_path))
        productive = [tuple(p) for p in _PRODUCTIVE4]
        stub = _stub_loop(affect, productive)
        assert _drive(stub, 6) == _REFERENCE6
        assert stub._causal_map.productive == _PRODUCTIVE4, "candidates mutated"

    def test_absent_env_is_byte_identical_to_current(self, tmp_path, monkeypatch):
        _LP()
        monkeypatch.delenv("LP_DRIVE_ARM", raising=False)
        stub = _stub_loop(AffectGains(_armed_fabric(tmp_path)), list(_PRODUCTIVE4))
        assert _drive(stub, 6) == _REFERENCE6

    def test_random_arm_is_byte_identical_to_current(self, tmp_path, monkeypatch):
        """The random arm is a LABEL for the harness (C33 §1): behavior identical."""
        _LP()
        monkeypatch.setenv("LP_DRIVE_ARM", "random")
        stub = _stub_loop(AffectGains(_armed_fabric(tmp_path)), list(_PRODUCTIVE4))
        assert _drive(stub, 6) == _REFERENCE6


class TestTheLpArm:

    def test_lp_reweights_toward_the_high_R_compressible_site(self, tmp_path,
                                                              monkeypatch):
        """The falsifier: with the lp arm on, exploration provably reweights toward
        the high-|R|-compressible site -- (2,2) outranks the higher-rate (5,5)."""
        _LP()
        monkeypatch.setenv("LP_DRIVE_ARM", "lp")
        affect = AffectGains(_armed_fabric(tmp_path))
        out = affect.lp_steer([((5, 5), 0.9), ((2, 2), 0.5)], GAME)
        assert out[0][0] == (2, 2), (
            "the lp arm must put the large+compressible NOVEL residual site first")

    def test_lp_drives_the_loop_toward_the_site(self, tmp_path, monkeypatch):
        _LP()
        monkeypatch.setenv("LP_DRIVE_ARM", "lp")
        stub = _stub_loop(AffectGains(_armed_fabric(tmp_path)),
                          [((5, 5), 0.9), ((2, 2), 0.5)])
        first = _drive(stub, 1)[0]
        assert first == (6, {"x": 2, "y": 2}), (
            "the loop's first explore click must land on the reweighted site")

    def test_zero_signal_leaves_the_order_unchanged(self, tmp_path, monkeypatch):
        _LP()
        monkeypatch.setenv("LP_DRIVE_ARM", "lp")
        fab = KnowledgeFabric(str(tmp_path / "empty"), agent_id="a", kin_key="v4")
        cands = [((5, 5), 0.9), ((2, 2), 0.5)]
        assert AffectGains(fab).lp_steer(list(cands), GAME) == cands, (
            "no ledger evidence -> no reweighting (never invented)")

    def test_incompressible_residual_is_never_aimed_at(self, tmp_path, monkeypatch):
        """A residual whose bbox is no pocket fails the mint's own inequality --
        large |R| alone must not attract the drive."""
        _LP()
        monkeypatch.setenv("LP_DRIVE_ARM", "lp")
        fab = KnowledgeFabric(str(tmp_path / "inc"), agent_id="a", kin_key="v4")
        ib, ia = _incompressible_pair()
        _enqueue(fab, ib, ia, residual=99.0)
        cands = [((2, 2), 0.9), ((5, 5), 0.5)]
        assert AffectGains(fab).lp_steer(list(cands), GAME) == cands

    def test_steers_only_never_prices(self, tmp_path, monkeypatch):
        """The write-contract: lp_steer touches nothing but the candidate order --
        gains() keys and values unchanged, and lp_drive never writes the fabric."""
        lp = _LP()
        monkeypatch.setenv("LP_DRIVE_ARM", "lp")
        affect = AffectGains(_armed_fabric(tmp_path))
        before = affect.gains()
        affect.lp_steer([((5, 5), 0.9), ((2, 2), 0.5)], GAME)
        after = affect.gains()
        assert before == after and set(after) == {"seed_bias", "mint_bar"}
        with open(lp.__file__, encoding="utf-8") as f:
            src = f.read()
        assert ".append(" not in src.replace("out.append(", ""), (
            "lp_drive must be a PURE READ of the ledger -- no fabric appends")


class TestTheSignal:

    def test_pure_and_replayable(self, tmp_path, monkeypatch):
        """affect(t) = f(ledger[0:t]): two instances over the same fabric prefix
        (different agent ids) return the identical signal, call after call."""
        lp = _LP()
        monkeypatch.setenv("LP_DRIVE_ARM", "lp")
        _armed_fabric(tmp_path, name="shared")
        fa = KnowledgeFabric(str(tmp_path / "shared"), agent_id="a", kin_key="v4")
        fb = KnowledgeFabric(str(tmp_path / "shared"), agent_id="b", kin_key="v4")
        da, db = lp.LPDrive(fa), lp.LPDrive(fb)
        s1 = da.signal(GAME)
        assert s1 == da.signal(GAME) == db.signal(GAME), "the replay law broke"
        cands = [((5, 5), 0.9), ((2, 2), 0.5)]
        assert da.steer(list(cands), GAME) == db.steer(list(cands), GAME)

    def test_bounded(self, tmp_path):
        """Weights are clamped into [0, CEIL] -- a monstrous residual cannot buy
        more than the ceiling (bounded, hysteresis-safe steering)."""
        lp = _LP()
        fab = _armed_fabric(tmp_path)
        cb, ca = _compressible_pair()
        _enqueue(fab, cb, ca, residual=1e9)
        sig = lp.LPDrive(fab).signal(GAME)
        assert sig, "the armed fabric must yield a signal"
        assert all(0.0 <= s["weight"] <= lp.CEIL for s in sig)
        assert max(s["weight"] for s in sig) == lp.CEIL


class TestTheNarration:

    def test_lp_narration_only_on_the_lp_arm(self, tmp_path, monkeypatch, capsys):
        """The legibility law: the lp arm emits [LP]; fixed/random emit nothing."""
        _LP()
        affect = AffectGains(_armed_fabric(tmp_path))
        cands = [((5, 5), 0.9), ((2, 2), 0.5)]
        for a in ("fixed", "random"):
            monkeypatch.setenv("LP_DRIVE_ARM", a)
            affect.lp_steer(list(cands), GAME)
            assert "[LP]" not in capsys.readouterr().out, (
                "%s arm must leave no [LP] trace (byte-identical)" % a)
        monkeypatch.setenv("LP_DRIVE_ARM", "lp")
        affect.lp_steer(list(cands), GAME)
        assert "[LP]" in capsys.readouterr().out, (
            "a steering signal that leaves no trace is the failure")


class TestTheSupervisorAssignment:

    def _games(self):
        tree = ast.parse(_supervisor_src())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "GAMES":
                        return ast.literal_eval(node.value)
        pytest.fail("GAMES list not found in tools/swarm_supervisor.py")

    def test_assignment_is_deterministic_and_pinned(self):
        """sha1(game) mod 3 -- never the salted builtin hash: the same game gets
        the same arm in every process, restart and supervisor reboot."""
        lp = _LP()
        games = self._games()
        for g in games:
            exp = ("fixed", "random", "lp")[
                int(hashlib.sha1(g.encode("utf-8"),
                                 usedforsecurity=False).hexdigest(), 16) % 3]
            assert lp.assign_arm(g) == exp == lp.assign_arm(g)

    def test_the_live_swarm_runs_all_three_arms(self):
        lp = _LP()
        assert {lp.assign_arm(g) for g in self._games()} == {"fixed", "random", "lp"}, (
            "the control needs all three populations live at once")

    def test_the_supervisor_wires_the_env(self):
        src = _supervisor_src()
        spawn = src[src.find("def spawn"):src.find("def working_sets")]
        assert 'env["LP_DRIVE_ARM"]' in spawn and "assign_arm(" in spawn, (
            "spawn() must hand each worker its arm via LP_DRIVE_ARM")


class TestTheWiring:

    def test_the_call_site_sits_in_the_explore_widen_block(self):
        src = _loop_src()
        a = src.index("SPEED 3: EXPLORE")
        b = src.index("Information-gain exploration", a)
        assert "lp_steer" in src[a:b], (
            "the one consumption line belongs at the explore-widen site, "
            "gated on the arm")

    def test_window_laws_hold_measured(self):
        """The 8000-char .credit and 20000-char .route windows from record_result
        survive the wiring -- measured, not assumed."""
        src = _loop_src()
        body = src[src.find("def record_result"):]
        ci = body.find(".credit(")
        ri = body.find(".route(")
        assert 0 <= ci < 8000, "the .credit window law broke (offset %d)" % ci
        assert 0 <= ri < 20000, "the .route window law broke (offset %d)" % ri
