"""W1 FALSIFIER-ARMS GATE (PREREG_W1_NARRATION.md, "Operationalised, with the
null PINNED" + "ARM C's CONSUMPTION MUST BE REAL").

Two arms over the SAME loop: C (narrate-and-consume) vs W (narrate-only --
today's exact behaviour, the default). Arm C consumes narration at two named
decision points where the decision DIFFERS BY CONSTRUCTION, with narration as
the only carrier of the consumed fact:

  WIRE 1 -- ROUTE consumes the prior BET. Inside router.AMBIGUOUS_BAND of the
            router's eps threshold (the discriminating fact's own tie region)
            the immediately-prior BET record's stated expectation resolves
            the TRANSFERRED-vs-neighbour tie; arm W applies the bare rule.
  WIRE 2 -- MINT consumes its own guard-zero history. A transition signature
            whose LAST MINT narration named a guard-zero, with that guard's
            input unchanged (support count same, offer route same), is NOT
            re-offered; the skip is narrated ("guard-zero unchanged") citing
            the consumed record id. Arm W re-offers every cycle.

Under test here, gating the experiment itself:
  THE WIRE CHECK -- constructed episodes where consumption provably FLIPS a
            decision: (a) one borderline residual routes BOTH ways depending
            only on the prior bet's presence; (b) one guard-zero repeat that
            arm C skips and arm W re-offers (observable in the mint's own
            support state and verdict ledger). Sensitivity for the wire.
  THE W NO-OP -- with the switch absent/W the consumption code paths are not
            reached: router.consumed stays 0, spine.last_mint stays empty,
            no record grows an extra field. Byte-identical behaviour.
  R4       -- constructed sequences reproduce the expected arm-C decisions
            exactly (routing decisions and narrated mint verdicts).
  THE ARM LABEL -- game start emits the ARM record (episode->arm labeling is
            read from data); a consumed decision's narration cites the
            consumed record's id -- provenance of the consumption itself.
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
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import narration as na  # noqa: E402
from engines.egocentric import router as rt  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402
from engines.egocentric.router import (  # noqa: E402
    NOVEL,
    TRANSFERRED,
    ResidualRouter,
)


def _fab(tmp_path, name="f"):
    return KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")


def _settle(residual, bet=True, stale=False, known=False):
    return {"bet": bet, "residual": float(residual), "binding_stale": stale,
            "from_known_atom": known}


def _event():
    """A mintable 1-cell recolour on 5x5 (mint.py's own docstring example)."""
    before = np.zeros((5, 5), dtype=int)
    before[2, 2] = 3
    after = before.copy()
    after[2, 2] = 7
    return before, after


def _cf():
    return SimpleNamespace(action_confidence=0.0, rung_name="",
                           action_speed="explore")


def _loop(tmp_path, name="f", arm=None):
    """A constructed loop namespace at the narration seams (the
    test_planner_scheduling pattern): enough real state for _narr_bet /
    _narr_close and the arm helpers to run the LOOP'S OWN code paths."""
    s = SimpleNamespace(
        _ego_fabric=_fab(tmp_path, name), _game_id="g1", _actions_taken=0,
        _ego_agent_id="a", _ego_level=0,
        _w2b_sched=None, _w2b_narr=None, _w2b_driven=None, _w2b_key=None,
        _w4c_counters={"mint_passed": 0}, _narr_import_n=0,
        _narration=None, _narr_slots=None, _atom_verified={},
        _residual_router=None, _plan_gate={"cycles": 1},
        _narr_settle=None, _narr_mint=None, _prev_frame=None,
        _ego_seeded={}, _ego_seeded_clicks={},
        _narr_route_consumed=None, _narr_mint_sig=None)
    if arm is not None:
        s._narr_arm = arm
    return s


def _recs(loop, point=None):
    out = loop._ego_fabric.query("personal", na.TOPIC)
    return out if point is None else [r for r in out if r["point"] == point]


# ---------------------------------------------------------------------------
# THE ARM SWITCH -- read once, narrated at game start, labeled from data
# ---------------------------------------------------------------------------

class TestTheArmSwitch:

    def test_resolve_arm_defaults_to_w_and_only_an_explicit_c_consumes(
            self, monkeypatch):
        monkeypatch.delenv(na.ARM_ENV, raising=False)
        assert na.resolve_arm() == na.ARM_W, (
            "the switch absent must be arm W -- today's behaviour, the default")
        monkeypatch.setenv(na.ARM_ENV, "C")
        assert na.resolve_arm() == na.ARM_C
        monkeypatch.setenv(na.ARM_ENV, " c ")
        assert na.resolve_arm() == na.ARM_C
        for junk in ("W", "consume", "1", "true", ""):
            assert na.resolve_arm(junk) == na.ARM_W, (
                "anything but an explicit C must resolve W: %r" % junk)

    def test_the_arm_is_narrated_once_at_game_start(self, tmp_path):
        sp = na.NarrationSpine(_fab(tmp_path), game="g1")
        rid = sp.narrate_arm(na.ARM_C, step=0)
        assert rid is not None
        assert sp.narrate_arm(na.ARM_C, step=1) is None, "once means once"
        arms = [r for r in sp.fabric.query("personal", na.TOPIC)
                if r["point"] == na.ARM]
        assert len(arms) == 1, "exactly one ARM record per game"
        r = arms[0]
        assert r["arm"] == na.ARM_C and r["consume"] is True
        assert r["side"] == na.SIDE_META, "config, never a decision"
        assert r["range"] in na.RANGES

    def test_the_loop_seam_emits_the_arm_record_from_loop_state(self, tmp_path):
        """Episode->arm labeling must be READ FROM DATA: the first bet of a
        game carries the ARM record onto the stream, once."""
        s = _loop(tmp_path, arm=na.ARM_C)
        cl._narr_bet(s, 6, _cf(), {})
        s._actions_taken = 1
        cl._narr_bet(s, 6, _cf(), {})
        arms = _recs(s, na.ARM)
        assert len(arms) == 1, "the ARM record is emitted once per game"
        assert arms[0]["arm"] == na.ARM_C
        bets = _recs(s, na.BET)
        assert len(bets) == 2, "the arm record must not displace the bets"

    def test_a_loop_without_arm_state_emits_no_arm_record(self, tmp_path):
        """The pre-arms record shape is preserved for loops that never ran
        start_new_game (constructed harnesses): no ARM record, no crash."""
        s = _loop(tmp_path)
        cl._narr_bet(s, 6, _cf(), {})
        assert _recs(s, na.ARM) == []


# ---------------------------------------------------------------------------
# THE WIRE CHECK, WIRE 1 -- a borderline residual flips on the prior bet
# ---------------------------------------------------------------------------

class TestWire1RouteConsumesThePriorBet:

    def test_the_flip_same_inputs_both_directions(self):
        """THE GENUINE FLIP: one constructed borderline settlement (residual
        inside AMBIGUOUS_BAND of eps, above it) routes NOVEL absent the bet
        and TRANSFERRED with it -- same inputs, the bet's presence the only
        difference."""
        borderline = _settle(0.3)
        absent = ResidualRouter()
        present = ResidualRouter()
        assert absent.route("BODY", dict(borderline)) == NOVEL, (
            "bare rule: 0.3 > eps routes NOVEL")
        assert present.route("BODY", dict(borderline),
                             expected_bin=TRANSFERRED) == TRANSFERRED, (
            "arm C: the prior bet's stated TRANSFERRED resolves the in-band "
            "tie -- the consumption did not flip the decision (wire 1 is thin)")
        assert absent.consumed == 0 and present.consumed == 1

    def test_the_flip_downward_direction_too(self):
        """The mirrored construction: an exactly-zero residual (in band) with
        a prior bet stating NOVEL routes NOVEL; absent the bet, TRANSFERRED."""
        zero = _settle(0.0)
        absent = ResidualRouter()
        present = ResidualRouter()
        assert absent.route("BODY", dict(zero)) == TRANSFERRED
        assert present.route("BODY", dict(zero),
                             expected_bin=NOVEL) == NOVEL

    def test_outside_the_band_the_bare_rule_holds_even_with_a_bet(self):
        """The consumption is a TIE-BREAK, not an override: a whole-unit
        residual (the smallest the substrate can testify to) is out of band
        and the bet is ignored."""
        r = ResidualRouter()
        assert r.route("BODY", _settle(2.0),
                       expected_bin=TRANSFERRED) == NOVEL
        assert r.consumed == 0 and r.last_consumed is False

    def test_the_band_is_a_named_constant_around_the_routers_own_threshold(
            self):
        assert rt.AMBIGUOUS_BAND == 0.5, (
            "the ambiguous band moved -- re-derive and update KNOBS G27")
        r = ResidualRouter()
        inside = r.eps + rt.AMBIGUOUS_BAND        # the band edge, inclusive
        outside = r.eps + rt.AMBIGUOUS_BAND + 1e-6
        assert r.route("BODY", _settle(inside),
                       expected_bin=TRANSFERRED) == TRANSFERRED
        assert r.route("BODY", _settle(outside),
                       expected_bin=TRANSFERRED) == NOVEL

    def test_arm_w_no_op_structural(self):
        """W changes NOTHING: the same calls without the kwarg are
        byte-identical to today and the consumption path is never reached."""
        r = ResidualRouter()
        seq = [_settle(0.3), _settle(0.0), _settle(2.0, known=True),
               _settle(1.0, bet=False)]
        assert [r.route("BODY", dict(s)) for s in seq] == [
            NOVEL, TRANSFERRED, "BROKEN_MECHANISM", None]
        assert r.consumed == 0 and r.last_consumed is False, (
            "arm W reached the consumption path -- the arms are not separated")

    def test_the_helper_reads_spine_memory_and_only_in_arm_c(self, tmp_path):
        sp = na.NarrationSpine(_fab(tmp_path), game="g1")
        sp.start_step(0)
        b, w = na.predict_bin(True, False)
        sp.bet({"WORKSPACE": {"predicted": "holds"}}, b, w, None,
               na.GUARD_SUPPORT, rng=na.EP)
        c = SimpleNamespace(_narr_arm=na.ARM_C, _narration=sp)
        assert cl._narr_expected_bin(c, "WORKSPACE") == TRANSFERRED, (
            "the staked slot's stated expectation was not read from the "
            "spine's in-memory last-bet state")
        assert cl._narr_expected_bin(c, "BODY") is None, (
            "an unstaked slot has no stated expectation")
        w_arm = SimpleNamespace(_narr_arm=na.ARM_W, _narration=sp)
        assert cl._narr_expected_bin(w_arm, "WORKSPACE") is None, (
            "arm W read the consumption source -- the arms are not separated")
        assert cl._narr_expected_bin(SimpleNamespace(), "WORKSPACE") is None

    def test_a_consumed_route_narration_cites_the_consumed_bet_id(
            self, tmp_path):
        """PROVENANCE OF THE CONSUMPTION: the step's ROUTE record cites the
        consumed BET record's id, and that id resolves in the same stream."""
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game="g1")
        sp.start_step(0)
        b, w = na.predict_bin(True, False)
        sp.bet({"BODY": {"predicted": "holds"}}, b, w, None,
               na.GUARD_SUPPORT, rng=na.EP)
        s = SimpleNamespace(_narration=sp, _ego_fabric=fab,
                            _narr_settle={"BODY": {"bet": True,
                                                   "residual": 0.3,
                                                   "bin": TRANSFERRED}},
                            _narr_mint=None, _w4c_pre_frame=None,
                            _narr_route_consumed=sp.last_bet["id"],
                            _narr_mint_sig=None)
        cl._narr_close(s, None, frame_changed=False)
        routes = [r for r in fab.query("personal", na.TOPIC)
                  if r["point"] == na.ROUTE]
        assert len(routes) == 1
        by_id = {r["id"]: r for r in fab.query("personal", na.TOPIC)}
        assert routes[0].get("consumed") in by_id, (
            "the consumed id does not resolve -- provenance broken")
        assert by_id[routes[0]["consumed"]]["point"] == na.BET
        assert s._narr_route_consumed is None, "the stash is one step only"

    def test_arm_w_route_narration_grows_no_extra_field(self, tmp_path):
        fab = _fab(tmp_path)
        sp = na.NarrationSpine(fab, game="g1")
        sp.start_step(0)
        b, w = na.predict_bin(True, False)
        sp.bet({}, b, w, None, na.GUARD_SUPPORT, rng=na.EP)
        s = SimpleNamespace(_narration=sp, _ego_fabric=fab,
                            _narr_settle=None, _narr_mint=None,
                            _w4c_pre_frame=None)
        cl._narr_close(s, None, frame_changed=False)
        routes = [r for r in fab.query("personal", na.TOPIC)
                  if r["point"] == na.ROUTE]
        assert "consumed" not in routes[0], (
            "arm W's ROUTE record grew a consumption field -- W is no longer "
            "byte-identical to today")


# ---------------------------------------------------------------------------
# THE WIRE CHECK, WIRE 2 -- a guard-zero repeat skips in C, re-offers in W
# ---------------------------------------------------------------------------

class TestWire2MintConsumesItsGuardZeroHistory:

    def _mint_loop(self, tmp_path, arm, name="f"):
        fab = _fab(tmp_path, name)
        s = _loop(tmp_path, name=name + "x", arm=arm)
        s._narration = na.NarrationSpine(fab, game="g1")
        s._ego_fabric = fab
        s._mdl_mint = MDLMint(E.Gamma(fab))
        return s

    def _cycle(self, s, before, after, step, route="queue", action=6):
        """One constructed offer cycle at the loop's own seams: the WIRE 2
        skip decision, the real mint consider when not skipped, the mark, and
        the outcome-side close (which emits + retains the MINT narration)."""
        sp = s._narration
        sp.start_step(step)
        b, w = na.predict_bin(True, False)
        sp.bet({"WORKSPACE": {"predicted": "holds"}}, b, w, None,
               na.GUARD_SUPPORT, rng=na.EP)
        skipped = cl._narr_mint_skip(s, before, after, action, route)
        if not skipped:
            wv = s._mdl_mint.consider(before=before, action=action,
                                      after=after, game="g1", level=1)
            s._narr_mint = dict(wv)
            cl._narr_mint_mark(s, before, after, action, route)
        s._narr_settle = None
        s._w4c_pre_frame = before
        cl._narr_close(s, after, True)
        return skipped

    def _seen(self, s, before, after, action=6):
        sig = cl._narr_sig(before, after, action)
        return s._mdl_mint._seen.get(("g1", 1, action, sig), 0)

    def test_the_flip_arm_c_skips_the_unchanged_guard_zero_repeat(
            self, tmp_path):
        """THE GENUINE FLIP: the identical third offer is WITHHELD in arm C
        (the mint's support state does not advance, no verdict is ledgered)
        and MADE in arm W (support advances, a verdict lands). Same
        constructed inputs; the arm the only difference."""
        before, after = _event()
        c = self._mint_loop(tmp_path, na.ARM_C, "c")
        assert self._cycle(c, before, after, 0) is False   # first: real mint
        assert self._cycle(c, before, after, 1) is False   # repeat: NOVELTY 0
        seen2 = self._seen(c, before, after)
        v2 = len(c._mdl_mint.gamma.fabric.query("collective", "mint_verdicts"))
        assert self._cycle(c, before, after, 2) is True, (
            "arm C re-offered an unchanged guard-zero repeat -- the consume "
            "arm is thin (wire 2 did not flip the decision)")
        assert self._seen(c, before, after) == seen2, (
            "the skipped offer still bumped the mint's support state -- the "
            "skip was not a real withhold")
        assert len(c._mdl_mint.gamma.fabric.query(
            "collective", "mint_verdicts")) == v2, (
            "the skipped offer still ledgered a verdict")

        w_arm = self._mint_loop(tmp_path, na.ARM_W, "w")
        assert self._cycle(w_arm, before, after, 0) is False
        assert self._cycle(w_arm, before, after, 1) is False
        seen2w = self._seen(w_arm, before, after)
        assert self._cycle(w_arm, before, after, 2) is False, (
            "arm W skipped -- W must re-offer every cycle, today's behaviour")
        assert self._seen(w_arm, before, after) == seen2w + 1, (
            "arm W's third offer did not reach the mint")

    def test_the_skip_is_narrated_with_reason_and_consumed_id(self, tmp_path):
        before, after = _event()
        s = self._mint_loop(tmp_path, na.ARM_C, "n")
        self._cycle(s, before, after, 0)
        self._cycle(s, before, after, 1)
        self._cycle(s, before, after, 2)                   # the skip
        mints = [r for r in s._narration.fabric.query("personal", na.TOPIC)
                 if r["point"] == na.MINT]
        assert [m["verdict"] for m in mints] == [
            "mint", "rederivation", "skip"], (
            "the constructed arm-C mint sequence was not reproduced (R4)")
        skip = mints[-1]
        assert skip["reason"] == "guard-zero unchanged", (
            "the skip must be narrated with its reason")
        assert skip["guard_zero"] == na.GUARD_NOVELTY, (
            "the skip must name the consumed guard")
        by_id = {r["id"]: r for r in
                 s._narration.fabric.query("personal", na.TOPIC)}
        assert skip.get("consumed") in by_id, (
            "the consumed record id does not resolve -- provenance broken")
        consumed = by_id[skip["consumed"]]
        assert consumed["point"] == na.MINT
        assert consumed["guard_zero"] == na.GUARD_NOVELTY, (
            "the consumed record is not the guard-zero it claims")

    def test_a_changed_guard_input_reoffers(self, tmp_path):
        """'until the narrated zero's input has changed': a different offer
        route, or a moved support count, re-opens the offer."""
        before, after = _event()
        s = self._mint_loop(tmp_path, na.ARM_C, "r")
        self._cycle(s, before, after, 0)
        self._cycle(s, before, after, 1)
        assert self._cycle(s, before, after, 2, route="primal") is False, (
            "a CHANGED route must re-offer -- the guard input moved")
        sig = cl._narr_sig(before, after, 6)
        s._mdl_mint._seen[("g1", 1, 6, sig)] += 1          # support grew
        assert self._cycle(s, before, after, 3, route="primal") is False, (
            "a GROWN support count must re-offer -- the guard input moved")

    def test_arm_w_no_op_structural(self, tmp_path):
        """With arm W the consumption machinery holds no state and the MINT
        narration records carry not one extra field -- byte-identical shape
        to today's records."""
        before, after = _event()
        s = self._mint_loop(tmp_path, na.ARM_W, "s")
        for i in range(3):
            self._cycle(s, before, after, i)
        assert len(s._narration.last_mint) == 0, (
            "arm W retained consumption state -- the arms are not separated")
        assert s._narr_mint_sig is None
        for m in [r for r in s._narration.fabric.query("personal", na.TOPIC)
                  if r["point"] == na.MINT]:
            for k in ("sig", "support", "route", "reason", "consumed"):
                assert k not in m, (
                    "arm W's MINT record grew %r -- W is no longer "
                    "byte-identical to today" % k)

    def test_a_successful_mint_clears_the_retained_zero(self, tmp_path):
        """A signature whose offer MINTED has no zero to consume: the
        retained record clears rather than blocking a live signature."""
        sp = na.NarrationSpine(_fab(tmp_path), game="g1")
        sp.start_step(0)
        sp.mint_point(None, "rederivation", na.GUARD_NOVELTY, None, rng=na.EP,
                      extra={"sig": "s1", "support": 2, "route": "queue"})
        assert "s1" in sp.last_mint
        sp.mint_point("atom:1", "mint", None, None, rng=na.EP,
                      extra={"sig": "s1", "support": 3, "route": "queue"})
        assert "s1" not in sp.last_mint


# ---------------------------------------------------------------------------
# R4 -- constructed sequences reproduce the expected arm-C decisions exactly
# ---------------------------------------------------------------------------

class TestR4ArmCSequences:

    def test_a_constructed_borderline_sequence_reproduces_arm_c_routing(self):
        """Sensitivity: the exact expected bin sequence, decision for
        decision, including in-band consumption both ways, out-of-band bare
        rule, and the no-hint default."""
        r = ResidualRouter()
        seq = [
            (_settle(0.3), TRANSFERRED, TRANSFERRED),   # in band, bet holds
            (_settle(2.0), TRANSFERRED, NOVEL),         # out of band: bare
            (_settle(0.0), NOVEL, NOVEL),               # in band, bet says no
            (_settle(0.4), None, NOVEL),                # no hint: bare rule
            (_settle(0.0), None, TRANSFERRED),          # no hint: bare rule
        ]
        got = [r.route("BODY", dict(s), expected_bin=hint)
               for s, hint, _want in seq]
        assert got == [w for _s, _h, w in seq], (
            "the constructed arm-C routing sequence was not reproduced "
            "exactly (R4 sensitivity): %r" % (got,))
        assert r.consumed == 2, "exactly the two in-band hints consumed"

    def test_specificity_a_no_bet_settlement_consumes_nothing(self):
        r = ResidualRouter()
        assert r.route("BODY", _settle(0.3, bet=False),
                       expected_bin=TRANSFERRED) is None
        assert r.consumed == 0, (
            "a no-bet settlement consumed a hint -- there was no decision "
            "to resolve (R4 specificity)")


# ---------------------------------------------------------------------------
# THE WIRING -- the live call sites consult the arms (source law)
# ---------------------------------------------------------------------------

class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def _body(self, src, name):
        i = src.find("def %s" % name)
        assert i != -1, "%s missing from cognitive_loop.py" % name
        j = src.find("\n    def ", i + 10)
        return src[i:j if j != -1 else len(src)]

    def test_the_router_call_site_consults_the_prior_bet(self):
        body = self._body(self._src(), "record_result")
        assert "expected_bin=_narr_expected_bin(self" in body, (
            "record_result's routing does not consult the prior bet -- "
            "wire 1 is unwired")

    def test_all_three_offer_sites_consult_the_guard_zero_history(self):
        body = self._body(self._src(), "record_result")
        assert body.count("_narr_mint_skip(") == 3, (
            "every mint offer site (bootstrap, queue, primal) must consult "
            "the skip -- an unguarded site re-offers in arm C")
        assert body.count("_narr_mint_mark(") == 3, (
            "every offer site must retain its offer for the next cycle's "
            "skip decision")

    def test_the_arm_is_narrated_at_both_game_entry_seams(self):
        src = self._src()
        assert self._body(src, "_narr_bet").count("narrate_arm(") == 1
        assert self._body(src, "_ego_feed").count("narrate_arm(") == 1, (
            "a replay-first game would carry no arm label")

    def test_the_switch_is_read_once_at_game_init(self):
        body = self._body(self._src(), "start_game")
        assert "resolve_arm" in body, (
            "the arm switch is not read at game init -- the arm would be "
            "inferred, not read from data")

    def test_the_emitter_is_still_one_append_no_queries(self):
        """The F2 law survives the arms: consumption reads IN-MEMORY spine
        state, never the stream -- narration.py still holds exactly one
        fabric append and no query."""
        src = open(os.path.join(REPO, "engines", "egocentric", "narration.py"),
                   encoding="utf-8", errors="replace").read()
        assert src.count(".append(") == 1
        assert ".query" not in src and "query_tail" not in src
