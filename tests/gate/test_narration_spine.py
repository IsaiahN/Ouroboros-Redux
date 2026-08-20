"""W1 GATE (PREREG_W1_NARRATION.md): the narration spine + memory at three ranges.

NARRATION IS THE DECISION, NOT A LOG: the bet-side record (per-slot prediction, ROUTE
bin AND why-not-the-neighbour-bin, mint candidate or which-guard-was-zero, memory-range
tag) is emitted BEFORE the action executes; outcome-side records close against the bet
by referencing its id. One JSONL record per event on the PERSONAL "narration" stream.

The build falsifiers under test:
  F1 · IT NARRATES     -- every step emits exactly ONE bet-side record with bin +
                          why-not-neighbour + memory-range tag; and every ACT record
                          references a BET record with an EARLIER per-step sequence
                          number (the precedence check: an act with no prior bet has
                          skipped step 1 and is refused, never fabricated).
  F3 · KNOWN-NEGATIVE  -- a replayed/observe-only step narrates as [REPLAY], never as
                          a fresh decision (playback is not laundered into reasoning).
  R4 · BOTH WAYS       -- a constructed step sequence with known ROUTE bins reproduces
                          those bins in narration (sensitivity); a no-op step with no
                          staked bet does NOT fabricate a bin (specificity).

(F2, the <=5% wall-clock cap, is measured against the live D-5 baseline, not here; the
build-side half -- O(1) per event, no scans, no queries at emit time -- is asserted
structurally: one append per emit.)
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl  # noqa: E402
from engines.egocentric import narration as na  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.router import (  # noqa: E402
    BROKEN_MECHANISM,
    NOVEL,
    TRANSFERRED,
    ResidualRouter,
)


def _fab(tmp_path, name="f"):
    return KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")


def _bet_step(sp, step, rng=na.EP, col_class=None):
    """One complete bet-side step: BET -> PLAN -> ACT, the cycle's order."""
    sp.start_step(step)
    b, w = na.predict_bin(True, False)
    sp.bet(slots={"WORKSPACE": {"predicted": "holds"}}, route_bin=b, why_not=w,
           mint_candidate=None, guard_zero=na.GUARD_SUPPORT, rng=rng,
           col_class=col_class)
    sp.plan("no-steps", "g1", rng=rng, col_class=col_class)
    sp.act(6, "explore", rng=rng, col_class=col_class)


class TestF1ItNarrates:

    def test_every_step_emits_exactly_one_bet_side_record_with_bin_whynot_range(
            self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game="g1")
        for step in range(3):
            _bet_step(sp, step)
        recs = fab.query("personal", na.TOPIC)
        bets = [r for r in recs if r["point"] == na.BET]
        assert len(bets) == 3, "one bet-side record per step, no step silent"
        for step in range(3):
            step_bets = [r for r in bets if r["step"] == step]
            assert len(step_bets) == 1, "EXACTLY one bet-side record per step"
            r = step_bets[0]
            assert r["side"] == na.SIDE_BET
            assert r["bin"] in na.BINS, "the bet names its ROUTE bin"
            assert r["why_not"].get("not") in na.BINS, "and the neighbour bin"
            assert r["why_not"].get("fact"), "with the discriminating fact"
            assert r["range"] in na.RANGES, "F1 fails if any record lacks the range tag"
            assert "mint_candidate" in r and "guard_zero" in r
            assert "slots" in r, "per-slot prediction rides the bet"

    def test_every_record_carries_a_memory_range_tag(self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game="g1")
        _bet_step(sp, 0)
        sp.perceive({"WORKSPACE": {"bet": True, "residual": 0.0,
                                   "bin": na.TRANSFERRED}}, rng=na.OWN)
        sp.route(na.TRANSFERRED, na.route_why_not(na.TRANSFERRED),
                 {"WORKSPACE": na.TRANSFERRED}, rng=na.OWN)
        sp.mint_point(None, None, na.GUARD_SUPPORT, None, rng=na.OWN)
        sp.echo("settled", {}, rng=na.OWN)
        recs = fab.query("personal", na.TOPIC)
        assert recs, "nothing was emitted at all"
        for r in recs:
            assert r["range"] in na.RANGES, "a record without its range tag fails F1"
            if r["range"] == na.COL:
                assert r["col_class"] in na.COL_CLASSES, (
                    "[COL] must carry contact-class provenance")

    def test_act_references_a_bet_with_an_earlier_sequence_number(self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game="g1")
        for step in range(3):
            _bet_step(sp, step)
        recs = fab.query("personal", na.TOPIC)
        acts = [r for r in recs if r["point"] == na.ACT]
        assert len(acts) == 3
        by_id = {r["id"]: r for r in recs}
        for a in acts:
            assert a["ref"] in by_id, "ACT must reference a record that exists"
            bet = by_id[a["ref"]]
            assert bet["point"] == na.BET and bet["side"] == na.SIDE_BET
            assert bet["step"] == a["step"], "the referenced bet is the SAME step's"
            assert bet["sq"] < a["sq"], (
                "F1 precedence: the bet's sequence number must be EARLIER -- "
                "narration written after the act is a reconstruction")

    def test_an_act_without_a_bet_is_refused_never_fabricated(self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game="g1")
        sp.start_step(0)
        assert sp.act(6, "explore", rng=na.EP) is None, (
            "an act with no prior bet has skipped step 1 -- it must be refused")
        assert sp.errors == 1
        assert fab.query("personal", na.TOPIC) == [], "and nothing was written"

    def test_a_second_bet_on_one_step_is_refused_and_counted(self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game="g1")
        sp.start_step(0)
        b, w = na.predict_bin(True, True)
        first = sp.bet({}, b, w, None, na.GUARD_SUPPORT, rng=na.EP)
        second = sp.bet({}, b, w, None, na.GUARD_SUPPORT, rng=na.EP)
        assert first == second and sp.dup_bets == 1
        bets = [r for r in fab.query("personal", na.TOPIC)
                if r["point"] == na.BET]
        assert len(bets) == 1, "exactly one bet-side record per step"

    def test_the_three_ranges_resolve_with_col_provenance(self):
        assert na.memory_range(replay=True) == (na.REPLAY, None)
        assert na.memory_range(inherited_n=2) == (na.COL, na.INHERITED_LIBRARY)
        assert na.memory_range(kin_n=1) == (na.COL, na.ROLE_POOL)
        assert na.memory_range(collective_n=3) == (na.COL, na.CROSS_ROLE)
        assert na.memory_range(own_n=5) == (na.OWN, None)
        assert na.memory_range() == (na.EP, None)


class TestF3KnownNegative:

    def test_a_replayed_step_narrates_as_replay_never_as_a_fresh_decision(
            self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game="g1")
        sp.replay(3, step=7)
        recs = fab.query("personal", na.TOPIC)
        assert len(recs) == 1
        r = recs[0]
        assert r["range"] == na.REPLAY, "a replayed step must tag [REPLAY]"
        assert r["side"] == na.SIDE_REPLAY, "never the bet side"
        assert r["ref"] is None, "playback references no bet -- there was none"
        assert not [x for x in recs if x["side"] == na.SIDE_BET], (
            "replay must not launder playback into a fresh decision")

    def test_the_loop_replay_feed_emits_the_replay_record(self, tmp_path):
        s = SimpleNamespace(_ego_fabric=_fab(tmp_path), _game_id="g1",
                            _actions_taken=0, _ego_agent_id="a")
        g = np.zeros((12, 12), dtype=int)
        g[6, 3] = 4
        cl.CognitiveLoop._ego_feed(s, g, 1)
        recs = s._ego_fabric.query("personal", na.TOPIC)
        assert len(recs) == 1, "the replay feed emitted no [REPLAY] narration"
        assert recs[0]["range"] == na.REPLAY
        assert recs[0]["side"] == na.SIDE_REPLAY
        assert recs[0]["action"] == 1
        assert not [r for r in recs if r["side"] == na.SIDE_BET], (
            "a replayed step narrated as a fresh decision -- F3 fires")


class TestR4BothWays:

    def _close(self, tmp_path, settle, name="f"):
        """Drive the loop's own outcome-side emitter over a constructed step."""
        fab = _fab(tmp_path, name)
        sp = na.NarrationSpine(fab, game="g1")
        s = SimpleNamespace(_narration=sp, _ego_fabric=fab,
                            _narr_settle=settle, _narr_mint=None,
                            _w4c_pre_frame=None)
        sp.start_step(0)
        b, w = na.predict_bin(bool(settle), False)
        sp.bet({}, b, w, None, na.GUARD_SUPPORT, rng=na.EP)
        cl._narr_close(s, None, frame_changed=bool(settle))
        return fab.query("personal", na.TOPIC)

    def test_sensitivity_a_known_bin_sequence_is_reproduced(self, tmp_path):
        """The bins come from a REAL router: what ROUTE resolved is what
        narration must say, bin for bin."""
        r = ResidualRouter()
        seq = [
            ("s0", {"bet": True, "residual": 0.0, "binding_stale": False,
                    "from_known_atom": False}),
            ("s1", {"bet": True, "residual": 2.0, "binding_stale": False,
                    "from_known_atom": True}),
            ("s2", {"bet": True, "residual": 2.0, "binding_stale": False,
                    "from_known_atom": False}),
        ]
        known = [r.route("WORKSPACE", stl) for _n, stl in seq]
        assert known == [TRANSFERRED, BROKEN_MECHANISM, NOVEL]
        narrated = []
        for i, b in enumerate(known):
            stl = seq[i][1]
            recs = self._close(
                tmp_path,
                {"WORKSPACE": {"bet": True,
                               "residual": float(stl["residual"]), "bin": b}},
                name="sens%d" % i)
            routes = [x for x in recs if x["point"] == na.ROUTE]
            assert len(routes) == 1
            narrated.append(routes[0]["bin"])
            assert routes[0]["why_not"]["not"] in na.BINS, (
                "the settled bin must name its neighbour")
            assert routes[0]["why_not"]["fact"], "and the discriminating fact"
        assert narrated == known, (
            "the constructed bin sequence was not reproduced -- narration is "
            "not reporting the loop it claims to narrate (R4 sensitivity)")

    def test_specificity_a_noop_step_does_not_fabricate_a_bin(self, tmp_path):
        recs = self._close(tmp_path, None, name="spec")
        routes = [x for x in recs if x["point"] == na.ROUTE]
        assert len(routes) == 1
        assert routes[0]["bin"] is None, (
            "a step with no staked bet fabricated a ROUTE bin (R4 specificity)")
        assert routes[0]["bins"] == {}
        percs = [x for x in recs if x["point"] == na.PERCEIVE]
        assert len(percs) == 1 and percs[0]["slots"] == {}, (
            "a no-op step must not invent per-slot outcomes")
        echoes = [x for x in recs if x["point"] == na.ECHO]
        assert len(echoes) == 1 and echoes[0]["status"] == "silent"

    def test_the_outcome_side_closes_against_the_bet_by_reference(self, tmp_path):
        recs = self._close(
            tmp_path,
            {"WORKSPACE": {"bet": True, "residual": 0.0, "bin": TRANSFERRED}},
            name="ref")
        bet = [x for x in recs if x["point"] == na.BET][0]
        for point in (na.PERCEIVE, na.ROUTE, na.MINT, na.ECHO):
            outs = [x for x in recs if x["point"] == point]
            assert len(outs) == 1, "%s missing from the outcome side" % point
            assert outs[0]["side"] == na.SIDE_OUTCOME
            assert outs[0]["ref"] == bet["id"], (
                "%s does not close against the pre-action bet" % point)


class TestTheWiring:
    """The call sites, in the ruled order: the bet-side emitter fires in
    cycle() BEFORE the action is returned for execution; the outcome side
    fires in record_result; the replay feed narrates [REPLAY]."""

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def _body(self, src, name):
        i = src.find("def %s" % name)
        assert i != -1, "%s missing from cognitive_loop.py" % name
        j = src.find("\n    def ", i + 10)
        return src[i:j if j != -1 else len(src)]

    def test_cycle_emits_the_bet_before_returning_the_action(self):
        body = self._body(self._src(), "cycle")
        assert "_narr_bet(self" in body, "cycle() never emits the bet side"
        assert body.index("_narr_bet(self") < body.index(
            "return action_num"), (
            "the bet-side emission must precede the action's return -- "
            "narration after the act is a reconstruction (F1 precedence)")

    def test_record_result_closes_the_loop(self):
        body = self._body(self._src(), "record_result")
        assert "_narr_close(self" in body, (
            "record_result never closes the narration loop -- the bet has no "
            "outcome to be wrong against")

    def test_the_replay_feed_narrates_replay(self):
        body = self._body(self._src(), "_ego_feed")
        assert ".replay(" in body, (
            "_ego_feed does not narrate [REPLAY] -- playback would be the one "
            "unnarrated step shape (F3 unwired)")

    def test_emission_is_one_append_per_event_no_scans_no_queries(self):
        """F2's build-side half, asserted structurally: the emitter contains
        exactly one fabric append and NO query/scan of any stream."""
        src = open(os.path.join(REPO, "engines", "egocentric", "narration.py"),
                   encoding="utf-8", errors="replace").read()
        assert src.count(".append(") == 1, "one append per emit -- O(1)"
        assert ".query" not in src, "no queries at emit time (the F2 law)"
        assert "query_tail" not in src


class TestTheGrammar:
    """Fixed tokens only: the loop's terms + NSM primes as connective glue."""

    def test_plan_verdict_names_the_stopping_gate(self):
        before = {"g1": 1, "g2": 1, "g3": 0}
        assert na.plan_verdict(before, {"g1": 2, "g2": 1}) == {
            "mode": "no-steps", "gate": "g2"}
        assert na.plan_verdict({}, {"drive": 1}) == {"mode": "drove",
                                                     "gate": None}
        assert na.plan_verdict({}, {"shadow": 1}) == {"mode": "shadowed",
                                                      "gate": None}

    def test_mint_close_names_the_zero_guard_and_both_bargain_sides(self):
        m = na.mint_close({"verdict": "mint", "id": "a1"}, 3)
        assert m["candidate"] == "a1" and m["guard_zero"] is None
        assert m["bargain"] == {"atom_cost": 4.0, "residual_cost": 7.0,
                                "paid": True}
        assert na.mint_close({"verdict": "rederivation", "id": None},
                             3)["guard_zero"] == na.GUARD_NOVELTY
        assert na.mint_close({"verdict": "reject", "id": None},
                             3)["guard_zero"] == na.GUARD_MDL
        assert na.mint_close({"verdict": "reject", "id": None, "w": 0.5},
                             3)["guard_zero"] == na.GUARD_SUPPORT
        assert na.mint_close(None, None)["guard_zero"] == na.GUARD_SUPPORT

    def test_every_gloss_is_fixed_tokens_not_free_prose(self):
        for (point, _side), gloss in na.GLOSS.items():
            assert point in na.POINTS
            assert gloss == gloss.upper(), (
                "the gloss field is fixed connective tokens, never free prose")
