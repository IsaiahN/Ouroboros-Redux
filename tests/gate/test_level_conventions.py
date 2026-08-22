"""THE LEVEL-CONVENTIONS GATE (record/canon/KNOBS.md AMENDMENT 3, A3-2 -- the grain audit's register).

⭐ WHY. "Level" has TWO conventions, both intentional, never registered until
A3-2: bare _ego_level (the COMPLETED level -- harvest/frontier context: banked
experience is keyed by the level it was earned on, the level-up click belongs
below) vs _ego_level + 1 (the PLAYING level -- mint/bank/consumer/goal context:
knowledge is scoped to the level being played). REGISTERED: streams
atoms / mint_verdicts / settlements / import_queue / goal_hypotheses carry the
PLAYING level; the frontier streams (frontier_harvest / frontier_paths) carry
the COMPLETED level. Game ids on knowledge streams ride at the FULL version-id
grain (A3-3), never the 4-char ops prefix.

This gate PINS each stream's declared convention two ways:
  1. behaviorally -- ONE hermetic episode through the REAL loop lands records
     on every registered stream and each record's level field is asserted
     against its stream's convention;
  2. structurally -- the convention comment must exist at the init sites in
     cognitive_loop.py (a source scan), so the register survives refactors.
"""
from __future__ import annotations

import importlib.util
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


def _laws():
    """The shared law bodies (tests/gate/_ast_laws.py). tests/gate is not a
    package, so it is loaded by path and cached in sys.modules for the
    session -- one body per law, one place to argue with it."""
    mod = sys.modules.get("_ouro_ast_laws")
    if mod is None:
        spec = importlib.util.spec_from_file_location(
            "_ouro_ast_laws",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ast_laws.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_ouro_ast_laws"] = mod
        spec.loader.exec_module(mod)
    return mod

from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.frontier import HARVEST_TOPIC, FrontierBook  # noqa: E402

GAME = "lvl25-0c556536"      # FULL version id -- the A3-3 knowledge grain
HARVEST_CELL = (4, 4)


def _loop_src():
    return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                errors="replace").read()


@pytest.fixture(scope="module")
def episode(tmp_path_factory):
    """ONE hermetic episode through the real cycle+record_result path, staged
    so every registered stream receives at least one record; snapshots are
    taken BEFORE the level-up step (the level-up increments _ego_level, so
    records written on that step land at the NEXT playing level by design)."""
    root = tmp_path_factory.mktemp("lvl_run")
    cwd = os.getcwd()
    os.chdir(root)
    try:
        # A COMPLETED-level harvest banked by the population before this
        # episode: the loop must consume it at bare _ego_level (= 0).
        pre_fab = KnowledgeFabric(os.path.join(str(root), "ego_fabric"),
                                  agent_id="agent", kin_key="v4")
        FrontierBook(pre_fab).record_harvest(
            GAME, 0, dead=[], effects=[HARVEST_CELL], fatal=None, deltas={})

        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop()
        loop.start_game(GAME, [1, 2, 3, 4, 5, 6], max_actions=64)
        obs = types.SimpleNamespace(levels_completed=0, score=0)
        base = np.zeros((64, 64), dtype=np.uint8)
        base[::2, :] = 9
        buf = io.StringIO()
        prev = base

        with redirect_stdout(buf):
            # 1-6: effectful steps -- settlements accrue (BetBook), and once
            # the binder binds REFERENCE, its identity bet's residual routes
            # NOVEL into the import_queue (persisted by W4c-4).
            for step in range(6):
                loop.cycle([prev.tolist()], obs)
                post = prev.copy()
                post[step, 0] = 1 + (step % 7)
                loop.record_result([post.tolist()], True, 0.0, False)
                if step == 1:
                    for _ in range(4):
                        loop._role_binder.observe_attributed(
                            9, 6, False, True, {(40, 6), (40, 7)}, {(5, 5)}, 0)
                prev = post
            # 7: the PRIMAL mint path -- a click that changed the frame is
            # offered to the mint directly; the verdict (and the minted atom)
            # must carry the PLAYING level.
            loop.cycle([prev.tolist()], obs)
            post = prev.copy()
            post[10:12, 10:12] = 5
            loop._last_action_info = dict(loop._last_action_info or {},
                                          type=6, x=11, y=11)
            loop.record_result([post.tolist()], True, 0.0, False)
            prev = post

            # Snapshots BEFORE the level-up step.
            fab = loop._ego_fabric
            snap = {t: fab.query("collective", t)
                    for t in ("settlements", "import_queue", "mint_verdicts",
                              "atoms")}
            bank_level = int(loop._predictor_bank.level)

            # 8: the level-up step -- goal abduction banks the frame delta as
            # a goal hypothesis at the playing level of the completed run.
            loop.cycle([prev.tolist()], obs)
            post = np.full((64, 64), 7, dtype=np.uint8)
            obs.levels_completed = 1
            loop.record_result([post.tolist()], True, 0.0, True)
            goals = fab.query("collective", "goal_hypotheses")

        yield {"loop": loop, "fabric": fab, "out": buf.getvalue(),
               "snap": snap, "bank_level": bank_level, "goals": goals}
    finally:
        os.chdir(cwd)


class TestPlayingLevelStreams:
    """atoms / mint_verdicts / settlements / import_queue / goal_hypotheses
    carry the PLAYING level (_ego_level + 1) at the full game-id grain."""

    def test_settlements_carry_the_playing_level(self, episode):
        setts = episode["snap"]["settlements"]
        assert setts, "the episode settled no bets -- the drive is understaged"
        for s in setts:
            assert s.get("game") == GAME, (
                "settlement game grain broke: %r (full id required)" % (s,))
            assert int(s.get("level", -1)) == 1, (
                "A3-2: settlements must carry the PLAYING level (_ego_level+1 "
                "= 1), got %r" % (s,))

    def test_import_queue_records_carry_game_and_playing_level(self, episode):
        raws = [r for r in episode["snap"]["import_queue"] if "kind" not in r]
        assert raws, (
            "no NOVEL residual was persisted -- the REFERENCE identity bet "
            "never routed (understaged binder?)")
        for r in raws:
            assert r.get("game") == GAME and int(r.get("level", -1)) == 1, (
                "A3-2: import_queue records must carry game (full id) + the "
                "PLAYING level, got %r" % (r,))

    def test_mint_verdicts_carry_the_playing_level(self, episode):
        verdicts = episode["snap"]["mint_verdicts"]
        assert verdicts, "the mint never ledgered a verdict -- understaged"
        for v in verdicts:
            assert v.get("game") == GAME and int(v.get("level", -1)) == 1, (
                "A3-2: mint_verdicts must carry the PLAYING level, got %r"
                % (v,))

    def test_atoms_carry_the_playing_level(self, episode):
        atoms = episode["snap"]["atoms"]
        assert atoms, "no atom minted -- the primal path is understaged"
        for a in atoms:
            assert a.get("game") == GAME and int(a.get("level", -1)) == 1, (
                "A3-2: atoms must carry the PLAYING level, got %r" % (a,))

    def test_goal_hypotheses_carry_the_playing_level(self, episode):
        goals = episode["goals"]
        assert goals, "the level-up banked no goal hypothesis -- understaged"
        for g in goals:
            assert g.get("game") == GAME and int(g.get("level", -1)) == 1, (
                "A3-2: goal_hypotheses must carry the playing level of the "
                "completed run (pre-increment _ego_level + 1 = 1), got %r"
                % (g,))

    def test_the_bank_is_scoped_to_the_playing_level(self, episode):
        assert episode["bank_level"] == 1, (
            "PredictorBank.level must be the PLAYING level (_ego_level + 1)")


class TestCompletedLevelStreams:
    """frontier streams carry the COMPLETED level (bare _ego_level)."""

    def test_harvest_is_banked_and_consumed_at_the_completed_level(self, episode):
        recs = episode["fabric"].query(
            "collective", HARVEST_TOPIC,
            where=lambda r: r.get("game") == GAME)
        assert recs and all(int(r.get("level", -1)) == 0 for r in recs), (
            "A3-2: frontier harvest records are keyed by the COMPLETED level "
            "(0 for a level-1 run), got %r" % (recs,))
        assert "[EGO-FRONTIER] harvest loaded level=0" in episode["out"], (
            "the loop must consume the harvest at bare _ego_level (COMPLETED) "
            "-- the read side drifted off the register")
        h = getattr(episode["loop"], "_ego_harvest_cache", {}).get(0) or {}
        assert HARVEST_CELL in (h.get("effects") or set()), (
            "the banked COMPLETED-level harvest never reached the loop's "
            "in-memory harvest")

    def test_the_two_conventions_diverge_in_one_episode(self, episode):
        """The register's point: the SAME episode writes level=1 knowledge
        records and consumes level=0 frontier records -- neither is a bug."""
        assert any(int(s.get("level", -1)) == 1
                   for s in episode["snap"]["settlements"])
        assert all(int(r.get("level", -1)) == 0
                   for r in episode["fabric"].query(
                       "collective", HARVEST_TOPIC,
                       where=lambda r: r.get("game") == GAME))


class TestTheRegisterIsInTheSource:
    """The convention comment must exist at the init sites -- the register
    survives refactors only if it is written where the levels are set."""

    def test_playing_level_convention_is_declared_at_the_init_sites(self):
        src = _loop_src()
        assert src.count("A3-2 CONVENTION (PLAYING level") >= 3, (
            "the PLAYING-level convention comment must sit at the settlement "
            "settle site, the import_queue persist site, and the goal-abduction "
            "bank site (plus the A3-1 hydrator)")
        # The settle site itself: BetBook's level is the playing level.
        i = src.index("A3-2 CONVENTION (PLAYING level): settlements")
        settle_zone = src[i:i + 600]
        assert "_bb.level" in settle_zone and "+ 1" in settle_zone, (
            "the settlements convention comment must annotate the _bb.level "
            "init site (and the site must add 1)")

    def test_completed_level_convention_is_declared_at_the_harvest_site(self):
        src = _loop_src()
        i = src.find("A3-2 CONVENTION (COMPLETED level")
        assert i >= 0, (
            "the COMPLETED-level convention comment is missing from the "
            "frontier harvest site")
        assert "load_harvest" in src[i:i + 1200], (
            "the COMPLETED-level comment must sit at the harvest load site")

    def test_window_laws_hold_measured(self):
        """L1 and L2 -- the facts the 8000/20000-character windows were proxies
        for, now stated as containment (PREREG_SYMBOL_RECEIPTS.md section 2).
        The name is kept so the history is followable; nothing here is measured
        in characters any more."""
        L = _laws()
        L.l1_credit_inside_record_result()
        L.l2_route_inside_record_result()
