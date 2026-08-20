"""CROSS-WAVE COMPOSITION GATE: producers of one wave feeding consumers of another.

Four compositions the 416 unit/falsifier tests never chain end to end:

  (a) IMPORT -> VERIFY -> PLAN: an atom planted in a SIBLING fabric is
      recognized by the triangulation consumer (signature-first), entered into
      the home Gamma by seed_imports, and the REAL loop's [PLAN] gate drives on
      it ONLY after two TRANSFERRED settlements accrued through the real
      bank -> _atom_verified path (the wheel rule outranks imports).
  (c) frontier x planner: the same verified plan is SUPPRESSED (shadow, never
      drive) once its target cell is banked as a fatal opening -- plan_veto
      composed inside the live loop. Plus, direct: an object-typed atom
      inverts (OBJ_APPEAR <-> OBJ_VANISH) and the bidirectional planner still
      returns a forward-replayable plan.
  (b) EFFECT_IF through apply: a ConditionalMiner-constructed arity-3 atom,
      stored in Gamma, honors its remote condition through gamma.apply /
      apply_effect AND through plan_to_identity (a false condition yields no
      plan -- the else branch is inert).
  (d) class fission -> bank keyed per subclass -> the settlement record on the
      fabric carries the SUBCLASS atom identity.

Hermetic: tmp cwd, synthetic frames, no RNG consumed by the assertions.
"""
from __future__ import annotations

import io
import os
import sys
import types
from contextlib import redirect_stdout

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer  # noqa: E402
from engines.egocentric.bank import ClassFissionSocket, PredictorBank  # noqa: E402
from engines.egocentric.betting import BetBook  # noqa: E402
from engines.egocentric.effects import (  # noqa: E402
    ConditionalMiner,
    Gamma,
    apply_effect,
    apply_inverse,
    invert_transform,
    learn_effect,
)
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.planner import plan_to_identity  # noqa: E402

GAME = "xw_gate_g1"
CELL = (20, 20)          # the transforming cell: colour 3 -> 4


def _frames():
    before = np.zeros((64, 64), dtype=int)
    before[CELL] = 3
    after = before.copy()
    after[CELL] = 4
    return before, after


# ═══════════════════════════════════════════════════════════════════════════
# (a) + (c, loop half): IMPORT -> VERIFY -> PLAN -> VETO through the real loop
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def import_verify_plan(tmp_path_factory):
    root = tmp_path_factory.mktemp("xw_run")
    cwd = os.getcwd()
    saved_env = os.environ.get("OURO_FABRIC_SEEDS")
    os.chdir(root)
    try:
        before, after = _frames()

        # 1. The SIBLING's fabric: the atom is minted elsewhere, sigma at birth.
        sib_root = os.path.join(str(root), "sibling_fabric")
        sib = KnowledgeFabric(sib_root, agent_id="sibling", kin_key="other_kin")
        atom = learn_effect(before, 6, after)
        assert atom is not None and atom["kind"] == "EFFECT"
        atom["sigma"] = consumer.sigma_of(before, after)
        Gamma(sib).add(atom, "someone_elses_game", 1)

        # 2. The home loop mounts the sibling through the shipped env-var path.
        os.environ["OURO_FABRIC_SEEDS"] = sib_root
        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop()
        loop.start_game(GAME, [6], max_actions=200)
        obs = types.SimpleNamespace(levels_completed=1)
        stage: dict = {"out": {}}

        def run_cycle(name, frame):
            # W2b STAGING (PREREG_W2B_PLANNER_SCHEDULING.md): this fixture
            # replays an IDENTICAL board frame to stage verification, which a
            # live episode reaches only through a CHANGED world (the settle
            # that verifies also moves the frame) -- so the scheduler's
            # retained attempt key is cleared before each staged cycle, or
            # GATE B would (correctly) refuse to re-search an unchanged world.
            # The unchanged-world skip has its own gate:
            # tests/gate/test_planner_scheduling.py (F3).
            loop._w2b_sched = None
            buf = io.StringIO()
            with redirect_stdout(buf):
                action, data, _cf = loop.cycle(frame, obs)
            stage["out"][name] = buf.getvalue()
            return action, data

        def run_record(frame, changed):
            buf = io.StringIO()
            with redirect_stdout(buf):
                loop.record_result(post_frame=frame, frame_changed=changed,
                                   score_delta=0.0, level_changed=False)

        # priming step: fabric + gamma + binder + bank lazy-init
        run_cycle("prime", before)
        run_record(before, False)
        fab = loop._ego_fabric
        assert fab is not None and sib_root in fab.seeds, (
            "the loop's fabric did not mount OURO_FABRIC_SEEDS")

        # 3. A residual lands on the HOME import queue with its patches.
        fab.append("collective", "import_queue",
                   {"slot": "WORKSPACE", "residual": 1.0,
                    "before": before.tolist(), "after": after.tolist()})
        report = consumer.consume(fab, GAME, 2, 20)
        stage["report"] = report
        stage["cands"] = consumer.candidates(fab, GAME, 2)

        # 4. The candidate enters the home Gamma, flagged imported.
        stage["seeded"] = consumer.seed_imports(loop._gamma, fab, GAME, 2)
        recs = loop._gamma.fabric.query(
            "collective", "atoms", where=lambda r: r.get("game") == GAME)
        stage["imported_recs"] = recs
        aid = recs[0]["id"] if recs else None
        stage["aid"] = aid

        # 5. Plan-gate preconditions the loop earns live in a real episode:
        #    level >= 1, a REFERENCE-bound class, a reference snapshot.
        loop._ego_level = 1
        for _ in range(4):
            loop._role_binder.observe_attributed(
                9, 6, False, True, {(40, 6), (40, 7)}, {(5, 5)}, 0)
        loop._reference_snapshot = after.copy()

        # 6. Unverified: the plan must SHADOW (the wheel rule outranks imports).
        run_cycle("shadow1", before)
        run_record(after, True)                    # TRANSFERRED settle #1
        stage["verified_after_1"] = dict(loop._atom_verified)
        run_cycle("shadow2", before)
        run_record(after, True)                    # TRANSFERRED settle #2
        stage["verified_after_2"] = dict(loop._atom_verified)

        # 7. Verified twice: the plan DRIVES, at the atom's context site.
        stage["drive_action"] = run_cycle("drive", before)

        # 8. (c) The frontier veto: the drive site becomes a banked fatal
        #    opening; the SAME verified plan must fall back to shadow.
        loop._ego_frontier_book.record_fatal_opening(GAME, 1, CELL)
        stage["veto_action"] = run_cycle("veto", before)

        stage["loop"] = loop
        stage["fabric"] = fab
        yield stage
    finally:
        os.chdir(cwd)
        if saved_env is None:
            os.environ.pop("OURO_FABRIC_SEEDS", None)
        else:
            os.environ["OURO_FABRIC_SEEDS"] = saved_env


class TestImportVerifyPlan:

    def test_consumer_recognized_the_sibling_atom(self, import_verify_plan):
        s = import_verify_plan
        assert s["report"]["candidates"] >= 1, (
            "the consumer never matched the sibling's atom: %r" % (s["report"],))
        cand = s["cands"][0]
        tc = cand.get("three_conditions") or {}
        assert tc.get("priority_seq", 99) < tc.get("match_seq", -1), (
            "condition 1 (priority): sigma persisted at seq %r, match at %r"
            % (tc.get("priority_seq"), tc.get("match_seq")))
        assert tc.get("atom_mint_seq") == 1, (
            "condition 2 (prior existence): the sibling atom's mint seq must "
            "ride the candidate")
        assert cand.get("kin_echo") is False
        assert cand.get("source_game") == "someone_elses_game"

    def test_seed_imports_entered_exactly_one_flagged_atom(self, import_verify_plan):
        s = import_verify_plan
        assert s["seeded"] == 1
        assert len(s["imported_recs"]) == 1
        atom = s["imported_recs"][0]["atom"]
        assert atom.get("imported") is True, (
            "an imported atom must be flagged imported=True in the home Gamma")

    def test_unverified_import_only_shadows(self, import_verify_plan):
        s = import_verify_plan
        assert "[PLAN] shadow" in s["out"]["shadow1"], (
            "an imported, UNVERIFIED atom must shadow-narrate, never drive:\n%s"
            % s["out"]["shadow1"])
        assert "[PLAN] DRIVE" not in s["out"]["shadow1"]
        assert "verified=False" in s["out"]["shadow1"]

    def test_verification_accrues_through_the_real_bank_path(self, import_verify_plan):
        s = import_verify_plan
        assert s["verified_after_1"].get(s["aid"]) == 1, (
            "one TRANSFERRED workspace settlement must verify the atom once -- "
            "got %r" % (s["verified_after_1"],))
        assert s["verified_after_2"].get(s["aid"]) == 2

    def test_twice_verified_plan_drives_at_the_atom_site(self, import_verify_plan):
        s = import_verify_plan
        assert "[PLAN] DRIVE" in s["out"]["drive"], (
            "2x TRANSFERRED accrued yet the plan still shadows:\n%s"
            % s["out"]["drive"])
        action, data = s["drive_action"]
        assert action == 6 and data == {"x": CELL[1], "y": CELL[0]}, (
            "the drive click must land on the atom's context site %r -- got "
            "action=%r data=%r" % (CELL, action, data))

    def test_transferred_settlement_carries_the_imported_atom_key(self, import_verify_plan):
        s = import_verify_plan
        setts = s["fabric"].query("collective", "settlements")
        keyed = [x for x in setts if x.get("atom_key") == s["aid"]]
        assert keyed, ("no settlement record names the imported atom %r"
                       % (s["aid"],))
        assert any(x.get("atom_bin") == "TRANSFERRED" for x in keyed), (
            "the imported atom's settlements never recorded bin=TRANSFERRED: %r"
            % (keyed,))


class TestFrontierVetoOverPlan:

    def test_banked_fatal_site_suppresses_the_verified_plan(self, import_verify_plan):
        s = import_verify_plan
        out = s["out"]["veto"]
        assert "[PLAN] DRIVE" not in out, (
            "a plan targeting a banked-fatal cell still DROVE:\n%s" % out)
        assert "[PLAN] shadow" in out and "veto=True" in out, (
            "the veto must be narrated in the shadow line:\n%s" % out)
        # The gate ledger: exactly one drive (the pre-veto cycle) and three
        # shadows (unverified x2 + vetoed x1). The explorer may still click
        # wherever it likes -- the veto binds the PLANNER, not the explorer.
        pg = s["loop"]._plan_gate
        assert pg["drive"] == 1, (
            "the vetoed cycle drove the plan anyway (drive=%d)" % pg["drive"])
        assert pg["shadow"] == 3, (
            "expected shadow narrations for unverified x2 + vetoed x1 -- got "
            "shadow=%d" % pg["shadow"])


# ═══════════════════════════════════════════════════════════════════════════
# (c, direct half): object-typed atom -> invert -> bidirectional plan
# ═══════════════════════════════════════════════════════════════════════════

class TestObjectTypedInversePlanning:

    def _obj_frames(self):
        """The appearing object sits at the board's FIRST clear anchor (top
        left): apply_effect stamps OBJ_APPEAR at the first row-major anchor,
        so this is the configuration where the forward replay reproduces the
        reference exactly."""
        base = np.zeros((9, 9), dtype=int)
        base[7, 0] = 8                        # clutter the whole-bbox path chokes on
        base[0, 8] = 8
        after = base.copy()
        after[0, 0] = 4                       # a two-colour L: OBJ_APPEAR territory
        after[0, 1] = 6
        after[1, 0] = 4
        return base, after

    def test_appear_atom_is_typed_and_invertible(self):
        base, after = self._obj_frames()
        atom = learn_effect(base, 6, after)
        assert atom is not None and atom.get("ttype") == "OBJ_APPEAR", (
            "the multi-colour appearance must classify OBJ_APPEAR -- got %r"
            % (atom.get("ttype"),))
        inv = invert_transform(atom["ttype"], atom.get("params") or {})
        assert inv is not None and inv[0] == "OBJ_VANISH"
        back = apply_inverse(atom, after)
        assert back is not None and (back == base).all(), (
            "stepping the after-frame BACKWARD through the appear atom must "
            "restore the before-frame")

    def test_bidirectional_planner_returns_a_replayable_plan(self, tmp_path):
        base, after = self._obj_frames()
        atom = learn_effect(base, 6, after)
        fab = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        gm = Gamma(fab)
        aid = gm.add(atom, "obj_g", 1)
        plan = plan_to_identity(base, after, gm, "obj_g", 1,
                                budget=10.0, cost_per_action=1.0)
        assert plan is not None and plan["steps"] == [aid] and plan["feasible"], (
            "the typed atom must plan base -> reference -- got %r" % (plan,))
        replay = gm.apply(aid, base)
        assert replay is not None and (replay == after).all()


# ═══════════════════════════════════════════════════════════════════════════
# (b) EFFECT_IF: miner -> Gamma -> apply -> planner honors the condition
# ═══════════════════════════════════════════════════════════════════════════

class TestConditionalAtomThroughApply:

    def _mine(self):
        miner = ConditionalMiner()
        pre_true = np.zeros((8, 8), dtype=int)
        pre_true[0, 7] = 1                    # the remote predicate cell
        pre_true[4, 4] = 2
        post_true = pre_true.copy()
        post_true[4, 4] = 6                   # condition holds: the object recolours
        pre_false = pre_true.copy()
        pre_false[0, 7] = 0                   # condition fails: the action is inert
        post_false = pre_false.copy()
        assert miner.feed(pre_true, 4, post_true) is None
        atom = miner.feed(pre_false, 4, post_false)
        assert atom is not None and atom["kind"] == "EFFECT_IF", (
            "divergent outcomes under one action with a 1-cell remote predicate "
            "must construct an EFFECT_IF")
        return atom, pre_true, post_true, pre_false

    def test_gamma_apply_honors_the_condition_both_ways(self, tmp_path):
        atom, pre_true, post_true, pre_false = self._mine()
        fab = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        gm = Gamma(fab)
        aid = gm.add(atom, "cond_g", 1)
        stored = gm.fabric.query("collective", "atoms")[-1]
        assert stored.get("type") == "structural"
        fired = gm.apply(aid, pre_true)
        assert fired is not None and (fired == post_true).all(), (
            "a TRUE condition must run the then-branch through gamma.apply")
        inert = gm.apply(aid, pre_false)
        assert inert is not None and (inert == pre_false).all(), (
            "a FALSE condition with an inert else must return the frame "
            "unchanged, not None")
        assert apply_effect(atom, pre_true) is not None

    def test_planner_uses_the_conditional_only_where_it_fires(self, tmp_path):
        atom, pre_true, post_true, pre_false = self._mine()
        fab = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        gm = Gamma(fab)
        aid = gm.add(atom, "cond_g", 1)
        plan = plan_to_identity(pre_true, post_true, gm, "cond_g", 1,
                                budget=10.0, cost_per_action=1.0)
        assert plan is not None and plan["steps"] == [aid], (
            "with the condition TRUE the conditional atom must carry the plan")
        ref_false = pre_false.copy()
        ref_false[4, 4] = 6
        plan2 = plan_to_identity(pre_false, ref_false, gm, "cond_g", 1,
                                 budget=10.0, cost_per_action=1.0)
        assert plan2 is None, (
            "with the condition FALSE the atom is inert -- the planner must "
            "find NO plan, not pretend the then-branch fires")


# ═══════════════════════════════════════════════════════════════════════════
# (d) fission -> bank keyed per subclass -> settlement carries the identity
# ═══════════════════════════════════════════════════════════════════════════

class TestFissionKeyedSettlement:

    def _fissioned(self):
        s = ClassFissionSocket()
        for _ in range(3):
            s.note_outcome("blob", "i1", verified=True, features={"colour": 4})
            s.note_outcome("blob", "i2", verified=False, features={"colour": 7})
        assert len(s.fission_events) == 1
        return s

    def test_bank_families_key_on_the_resolved_subclass(self):
        s = self._fissioned()
        a = s.resolve("blob", "i1")
        b = s.resolve("blob", "i2")
        assert (a, b) == ("blob__a", "blob__b")
        bank = PredictorBank(min_evidence=2)
        for step in range(4):
            bank.note_motion(a, (10, 10 + step))          # self-propelled mover
            bank.note_motion(b, (30, 30))                 # inert
        assert bank.agent_family(a), (
            "the moving subclass must EARN the AGENT_MOTION family under its "
            "own resolved identity")
        assert not bank.agent_family(b), (
            "the inert subclass must NOT inherit the sibling's family -- "
            "predictions are keyed per subclass")
        assert bank.commit_agent(a, (10, 13), target=(10, 20)) is True
        settled = bank.settle_agent(a, (10, 14))
        assert settled.get("bet") is True and settled.get("family") == "AGENT_MOTION"

    def test_settlement_record_carries_the_subclass_identity(self, tmp_path):
        s = self._fissioned()
        sub = s.resolve("blob", "i1")
        fab = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        book = BetBook(fab, agent_id="a", game="fiss_g")
        before = np.zeros((6, 6), dtype=int)
        post = before.copy()
        post[2, 2] = 5
        book.commit(action=6, before=before, paste=post, transform=None)
        out = book.settle(post=post, executed_action=6,
                          atom_key="%s:atom0" % sub, atom_bin="TRANSFERRED")
        assert out is not None and out.get("void") is False
        recs = fab.query("collective", "settlements")
        assert len(recs) == 1
        assert recs[0]["atom_key"] == "blob__a:atom0", (
            "the fabric settlement must carry the SUBCLASS atom identity -- "
            "got %r" % (recs[0].get("atom_key"),))
        assert recs[0]["atom_bin"] == "TRANSFERRED"
        assert recs[0]["nontrivial"] is True
