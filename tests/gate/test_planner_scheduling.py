"""W2b GATE (PREREG_W2B_PLANNER_SCHEDULING.md): the planner as LAST RESORT.

THE LEAK, measured three times (F2 addendum, F1_VERDICT_AND_SHADOW_TEST.md):
under engage-on-atoms, planner engagement scaled with freed capacity
(5 -> 10 -> 17 calls across three profiling windows) and reabsorbed every
per-call speedup. W2b is the decision of WHEN, separate from the index's HOW
CHEAPLY: GATE A (cheap routes first -- a candidate at or above
CHEAP_ROUTE_CONF_BAR holds the wheel) and GATE B (no re-search of an unchanged
world -- same state key + same (mint, import) mark as the last attempt skips),
with an absolute starvation guard and the shadow-test rider's abort router.

The pinned falsifiers under test:
  F2 · STARVATION GUARD  -- a constructed cycle where every cheap route fails
                            MUST reach the planner in that same cycle; the
                            gates defer within a cycle, never deny across
                            cycles, and the loop seam FAILS OPEN on error.
  F3 · NO RE-SEARCH      -- the same state key twice with no intervening mint/
                            import: the second attempt is SKIPPED and the skip
                            is NARRATED at the PLAN point with its reason;
                            a mint (or import, or key change) reopens GATE B.
  F4 · ABORT ROUTED      -- a driven plan's abort is routed both ways:
                            world-moved (state key changed under the plan ->
                            re-plan, no penalty; the retained key drops) vs
                            plan-wrong (state as predicted, step failed ->
                            recorded against the plan's atoms), each narrated
                            with its discriminator.
  R4 · TRACES            -- constructed schedule traces reproduce expected
                            engage/skip sequences exactly.

(F1 -- the leak stops in a live window -- is the proctor's profile read, not
asserted here.)
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
from engines.egocentric import scheduler as sch  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402


def _fab(tmp_path, name="f"):
    return KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")


def _frame(v=0):
    g = np.zeros((8, 8), dtype=int)
    g[0, 0] = int(v)
    return g


def _cf(conf=0.0, speed="explore"):
    """A constructed CognitiveFrame stand-in: the winning cheap route's speed
    and candidate confidence, as _act leaves them on the frame. Only mapped/
    reasoned speeds produce candidates; explore/random ARE the cheap routes
    having failed."""
    return SimpleNamespace(action_confidence=float(conf), rung_name="",
                           action_speed=str(speed))


def _loop(tmp_path, name="f"):
    """A constructed loop namespace at the planner seam: enough real state for
    _w2b_engage / _w2b_abort / _narr_bet to run the LOOP'S OWN code paths."""
    return SimpleNamespace(
        _ego_fabric=_fab(tmp_path, name), _game_id="g1", _actions_taken=0,
        _ego_agent_id="a", _ego_level=0,
        _w2b_sched=None, _w2b_narr=None, _w2b_driven=None, _w2b_key=None,
        _w4c_counters={"mint_passed": 0}, _narr_import_n=0,
        _narration=None, _narr_slots=None, _atom_verified={},
        _residual_router=None, _plan_gate={"cycles": 1},
        _narr_settle=None, _narr_mint=None, _prev_frame=None,
        _ego_seeded={}, _ego_seeded_clicks={})


def _plan_records(loop):
    return [r for r in loop._ego_fabric.query("personal", na.TOPIC)
            if r["point"] == na.PLAN]


# ---------------------------------------------------------------------------
# F2 · STARVATION GUARD (absolute)
# ---------------------------------------------------------------------------

class TestF2StarvationGuard:

    def test_all_cheap_routes_failed_reaches_the_planner_in_that_cycle(
            self, tmp_path):
        """The constructed starved cycle: every cheap route failed (confidence
        0.0), no retained attempt -- the planner is reached IN THAT CYCLE."""
        s = _loop(tmp_path)
        assert cl._w2b_engage(s, _frame(), _cf(0.0)) is True, (
            "a cycle where every cheap route failed did not reach the "
            "planner -- deferral became denial (F2 fires)")
        assert s._w2b_sched.engages == 1 and s._w2b_sched.skips == 0

    def test_the_guard_holds_for_every_starved_confidence_below_the_bar(self):
        """Provable by construction: conf below the bar + no retained attempt
        means BOTH gates are open -- for any starved confidence, any level."""
        p = sch.PlannerScheduler()
        for i, conf in enumerate((0.0, 0.1, 0.2, 0.49, None)):
            v = p.decide("g1", i, "key-%d" % i, conf, (0, 0))
            assert v["engage"] is True, (
                "starved conf=%r was denied the planner (F2)" % (conf,))
            assert v["reason"] == sch.ENGAGE_FIRST

    def test_a_confident_cheap_route_defers_within_the_cycle(self):
        p = sch.PlannerScheduler()
        v = p.decide("g1", 0, "k", sch.CHEAP_ROUTE_CONF_BAR, (0, 0))
        assert v == {"engage": False, "reason": sch.SKIP_CHEAP_ROUTE}

    def test_deferral_never_becomes_denial_across_cycles(self):
        """GATE A defers while a cheap route holds; the moment the cheap
        routes fail, the SAME state engages (no attempt was retained)."""
        p = sch.PlannerScheduler()
        for _ in range(5):
            assert p.decide("g1", 0, "k", 0.9, (0, 0))["engage"] is False
        assert p.decide("g1", 0, "k", 0.0, (0, 0))["engage"] is True

    def test_a_confident_rung_candidate_defers_at_the_loop_seam(self, tmp_path):
        """GATE A at the seam: a reasoned (rung) candidate at the bar holds
        the wheel, and the deferral is narrated with its reason."""
        s = _loop(tmp_path)
        assert cl._w2b_engage(s, _frame(), _cf(0.9, speed="reasoned")) is False
        assert s._w2b_narr == ("skipped", sch.SKIP_CHEAP_ROUTE)

    def test_a_mapped_plan_step_defers_at_the_loop_seam(self, tmp_path):
        s = _loop(tmp_path)
        assert cl._w2b_engage(s, _frame(), _cf(0.8, speed="mapped")) is False

    def test_explore_confidence_is_not_a_candidate(self, tmp_path):
        """A heuristic info-gain score is not a rung's option above the bar:
        explore/random speeds leave GATE A open whatever number they carry --
        the prereg's 'no rung above a stated confidence produced an option'."""
        s = _loop(tmp_path)
        assert cl._w2b_engage(s, _frame(), _cf(0.9, speed="explore")) is True
        assert cl._w2b_engage(s, _frame(2), _cf(0.9, speed="random")) is True

    def test_the_loop_seam_fails_open_a_scheduler_error_never_starves(
            self, tmp_path):
        s = _loop(tmp_path)
        s._w2b_sched = object()     # no decide(): the seam's internal error
        assert cl._w2b_engage(s, _frame(), _cf(0.0)) is True, (
            "a scheduler error starved the planner -- the seam must fail OPEN")


# ---------------------------------------------------------------------------
# F3 · NO RE-SEARCH OF AN UNCHANGED WORLD (skip narrated; mint reopens)
# ---------------------------------------------------------------------------

class TestF3NoResearchOfAnUnchangedWorld:

    def test_same_key_twice_skips_narrates_and_a_mint_reopens(self, tmp_path):
        s = _loop(tmp_path)
        f = _frame(3)
        assert cl._w2b_engage(s, f, _cf(0.0)) is True, "first attempt engages"
        assert cl._w2b_engage(s, f, _cf(0.0)) is False, (
            "the same state key with nothing minted/imported since was "
            "re-searched (F3 fires)")
        assert s._w2b_narr == ("skipped", sch.SKIP_UNCHANGED)
        # the skip is NARRATED at the PLAN point with its reason, through the
        # loop's own bet-side emitter (the narration spine, W1's pattern)
        cl._narr_bet(s, 6, _cf(0.0), {})
        plans = _plan_records(s)
        assert len(plans) == 1, "exactly one PLAN record per cycle"
        assert plans[0]["mode"] == "skipped", "the skip must be narrated"
        assert plans[0]["gate"] == sch.SKIP_UNCHANGED, (
            "the skip must carry its reason -- a silent deferral fails F3")
        # a mint lands -> the next attempt runs (deferral is not denial)
        s._w4c_counters["mint_passed"] += 1
        assert cl._w2b_engage(s, f, _cf(0.0)) is True, (
            "a mint did not reopen GATE B -- deferral became denial")

    def test_an_import_reopens_gate_b(self, tmp_path):
        s = _loop(tmp_path)
        f = _frame(5)
        assert cl._w2b_engage(s, f, _cf(0.0)) is True
        assert cl._w2b_engage(s, f, _cf(0.0)) is False
        s._narr_import_n += 1
        assert cl._w2b_engage(s, f, _cf(0.0)) is True

    def test_a_changed_state_key_engages(self, tmp_path):
        s = _loop(tmp_path)
        assert cl._w2b_engage(s, _frame(1), _cf(0.0)) is True
        assert cl._w2b_engage(s, _frame(2), _cf(0.0)) is True, (
            "a CHANGED world was refused the planner")

    def test_the_skip_flag_is_consumed_never_stale(self, tmp_path):
        """One skip narrates once; the next cycle's PLAN record is the g-gate
        verdict again, not a stale skip."""
        s = _loop(tmp_path)
        f = _frame(3)
        cl._w2b_engage(s, f, _cf(0.0))
        cl._w2b_engage(s, f, _cf(0.0))              # -> skip flagged
        cl._narr_bet(s, 6, _cf(0.0), {})            # consumes the flag
        s._actions_taken += 1
        cl._narr_bet(s, 6, _cf(0.0), {})            # a fresh, skipless cycle
        plans = _plan_records(s)
        assert len(plans) == 2
        assert plans[0]["mode"] == "skipped"
        assert plans[1]["mode"] != "skipped", "a stale skip leaked (F3/R4)"

    def test_retention_is_scoped_per_game_and_level(self):
        p = sch.PlannerScheduler()
        p.note_attempt("g1", 0, "k", (0, 0))
        assert p.decide("g1", 0, "k", 0.0, (0, 0))["engage"] is False
        assert p.decide("g1", 1, "k", 0.0, (0, 0))["engage"] is True
        assert p.decide("g2", 0, "k", 0.0, (0, 0))["engage"] is True


# ---------------------------------------------------------------------------
# F4 · THE ABORT IS ROUTED (world-moved vs plan-wrong, each narrated)
# ---------------------------------------------------------------------------

class TestF4AbortRouted:

    def test_the_pure_discriminator_routes_both_ways(self):
        r = sch.route_abort("k1", "k2")
        assert r["route"] == sch.ABORT_WORLD_MOVED and r["fact"]
        r = sch.route_abort("k1", "k1")
        assert r["route"] == sch.ABORT_PLAN_WRONG and r["fact"]

    def _driven(self, tmp_path, observed_frame):
        """Construct the seam where a driven plan aborts: an engaged attempt,
        a bet on the step, the drive stash, then the failed step."""
        s = _loop(tmp_path)
        f = _frame(1)
        assert cl._w2b_engage(s, f, _cf(0.0)) is True
        cl._narr_bet(s, 6, _cf(0.0), {})
        s._w2b_driven = {"key": sch.state_key(f), "steps": ["atomA", "atomB"]}
        s._prev_frame = observed_frame
        cl._w2b_abort(s, frame_changed=False, level_changed=False)
        return s, f

    def test_world_moved_replans_without_penalty(self, tmp_path):
        s, f = self._driven(tmp_path, _frame(9))   # key changed under the plan
        aborts = [r for r in _plan_records(s) if r["mode"] == "abort"]
        assert len(aborts) == 1, "the abort was not narrated (F4)"
        assert aborts[0]["gate"] == sch.ABORT_WORLD_MOVED, (
            "the discriminator must be narrated with the abort")
        assert s._w2b_sched.plan_wrong == {}, (
            "world-moved penalised the plan's atoms -- the conflation W2b's "
            "rider exists to close")
        # re-plan is NOT blocked: the retained key was dropped
        assert cl._w2b_engage(s, f, _cf(0.0)) is True

    def test_plan_wrong_is_recorded_against_the_plan(self, tmp_path):
        s, f = self._driven(tmp_path, _frame(1))   # state as predicted
        aborts = [r for r in _plan_records(s) if r["mode"] == "abort"]
        assert len(aborts) == 1
        assert aborts[0]["gate"] == sch.ABORT_PLAN_WRONG
        assert s._w2b_sched.plan_wrong == {"atomA": 1, "atomB": 1}, (
            "plan-wrong must be recorded against the plan's atoms")
        # the world genuinely did not change: GATE B correctly holds
        assert cl._w2b_engage(s, f, _cf(0.0)) is False

    def test_a_landed_step_routes_no_abort(self, tmp_path):
        s = _loop(tmp_path)
        f = _frame(1)
        cl._w2b_engage(s, f, _cf(0.0))
        cl._narr_bet(s, 6, _cf(0.0), {})
        s._w2b_driven = {"key": sch.state_key(f), "steps": ["atomA"]}
        s._prev_frame = f.copy()
        cl._w2b_abort(s, frame_changed=True, level_changed=False)
        assert not [r for r in _plan_records(s) if r["mode"] == "abort"], (
            "a step that LANDED was routed as an abort")
        assert s._w2b_driven is None, "the stash must clear every step"


# ---------------------------------------------------------------------------
# The clears: level change / fission (binder.on_level_change's pattern)
# ---------------------------------------------------------------------------

class TestTheClears:

    def test_level_change_clears_the_retained_key(self, tmp_path):
        s = _loop(tmp_path)
        f = _frame(4)
        assert cl._w2b_engage(s, f, _cf(0.0)) is True
        assert cl._w2b_engage(s, f, _cf(0.0)) is False
        cl._w2b_abort(s, frame_changed=True, level_changed=True)
        assert cl._w2b_engage(s, f, _cf(0.0)) is True, (
            "the level changed and the retained key did not re-earn")

    def test_fission_clears_like_a_level_change(self):
        p = sch.PlannerScheduler()
        p.note_attempt("g1", 0, "k", (0, 0))
        assert p.decide("g1", 0, "k", 0.0, (0, 0))["engage"] is False
        p.on_fission("blob")
        assert p.decide("g1", 0, "k", 0.0, (0, 0))["engage"] is True


# ---------------------------------------------------------------------------
# R4 · constructed schedule traces reproduce engage/skip sequences EXACTLY
# ---------------------------------------------------------------------------

class TestR4ScheduleTraces:

    def test_a_constructed_trace_is_reproduced_exactly(self):
        p = sch.PlannerScheduler()
        trace = [
            # (key, conf, mark)                 expected (engage, reason)
            ("k1", 0.9, (0, 0)),   # cheap route held -> defer, nothing retained
            ("k1", 0.0, (0, 0)),   # starved, first attempt -> ENGAGE
            ("k1", 0.0, (0, 0)),   # unchanged world -> skip
            ("k1", 0.9, (0, 0)),   # cheap route held (A outranks B) -> skip
            ("k2", 0.0, (0, 0)),   # key moved -> ENGAGE
            ("k2", 0.0, (1, 0)),   # a mint landed -> ENGAGE
            ("k2", 0.0, (1, 0)),   # unchanged again -> skip
            ("k2", 0.0, (1, 1)),   # an import landed -> ENGAGE
        ]
        expected = [
            (False, sch.SKIP_CHEAP_ROUTE),
            (True, sch.ENGAGE_FIRST),
            (False, sch.SKIP_UNCHANGED),
            (False, sch.SKIP_CHEAP_ROUTE),
            (True, sch.ENGAGE_CHANGED),
            (True, sch.ENGAGE_CHANGED),
            (False, sch.SKIP_UNCHANGED),
            (True, sch.ENGAGE_CHANGED),
        ]
        got = []
        for key, conf, mark in trace:
            v = p.decide("g1", 0, key, conf, mark)
            got.append((v["engage"], v["reason"]))
            if v["engage"]:
                p.note_attempt("g1", 0, key, mark)   # the loop seam's order
        assert got == expected, (
            "the constructed schedule trace was not reproduced exactly -- the "
            "scheduler is not the machine it claims to be (R4)")
        assert p.engages == 4 and p.skips == 4

    def test_the_counters_are_readout_only_and_consistent(self):
        p = sch.PlannerScheduler()
        for i in range(3):
            v = p.decide("g", 0, "k%d" % i, 0.0, (0, 0))
            assert v["engage"]
            p.note_attempt("g", 0, "k%d" % i, (0, 0))
        assert p.engages == 3 and p.skips == 0 and p.errors == 0


# ---------------------------------------------------------------------------
# The wiring: both plan seams gated; the abort routed in record_result
# ---------------------------------------------------------------------------

class TestTheWiring:
    """The call sites, in the ruled order: BOTH plan seams (reference-mode
    plan_to_identity and the abduced path) pass through _w2b_engage BEFORE the
    search runs; record_result routes the abort and clears on level change;
    the skip narration rides _narr_bet's PLAN emission."""

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def _method(self, src, name):
        i = src.find("def %s" % name)
        assert i != -1, "%s missing from cognitive_loop.py" % name
        j = src.find("\n    def ", i + 10)
        return src[i:j if j != -1 else len(src)]

    def _module_fn(self, src, name):
        i = src.find("def %s" % name)
        assert i != -1, "%s missing from cognitive_loop.py" % name
        j = src.find("\ndef ", i + 10)
        k = src.find("\nclass ", i + 10)
        ends = [x for x in (j, k) if x != -1]
        return src[i:min(ends) if ends else len(src)]

    def test_both_plan_seams_are_gated_before_the_search(self):
        body = self._method(self._src(), "cycle")
        assert body.count("_w2b_engage(self") == 2, (
            "both plan seams (reference + abduced) must pass the scheduler")
        assert body.index("_w2b_engage(self") < body.index("plan_to_identity"), (
            "the gate must sit BEFORE plan_to_identity -- gating after the "
            "search is narration, not scheduling")
        assert body.index("import plan_to_identity") > body.index(
            "_w2b_engage(self"), "the planner import is inside the gated block"

    def test_record_result_routes_the_abort(self):
        body = self._method(self._src(), "record_result")
        assert "_w2b_abort(self" in body, (
            "record_result never routes a driven plan's abort (F4 unwired)")

    def test_the_level_change_clear_follows_the_binder_pattern(self):
        fn = self._module_fn(self._src(), "_w2b_abort")
        assert "on_level_change()" in fn, (
            "a level change must clear the retained state key")

    def test_the_seam_fails_open_by_construction(self):
        fn = self._module_fn(self._src(), "_w2b_engage")
        tail = fn[fn.index("except Exception"):]
        assert "return True" in tail, (
            "the engagement seam must FAIL OPEN -- an error that returns "
            "False lets containment starve the planner (F2)")

    def test_the_skip_narration_rides_the_plan_point(self):
        fn = self._module_fn(self._src(), "_narr_bet")
        assert "_w2b_narr" in fn, (
            "_narr_bet never narrates the scheduler skip -- silent deferral "
            "fails F3")

    def test_the_drive_sites_stash_for_the_abort_router(self):
        body = self._method(self._src(), "cycle")
        assert body.count("_w2b_driven = {") == 2, (
            "every drive site must stash (key, steps) for the abort router")
