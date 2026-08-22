import os

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # Rule 1: Disable pycache

"""
Cognitive Loop - Perceive -> Think -> Map -> Act

This is the central nervous system that makes the agent an ORGANISM
rather than a bag of organs. It orchestrates:

1. PERCEIVE: Multimodal scene understanding (parallel channels)
2. THINK: Phenomenological compression (felt-state + strategy)
3. MAP: Causal knowledge update/query (the leapfrog enabler)
4. ACT: Three-speed decision making (mapped/reasoned/explore)

And crucially: the output of ACT feeds back into PERCEIVE on the next
cycle, closing the loop. The causal map informs perception, perception
informs thinking, thinking consults the map, the map drives action.

This module does NOT replace the existing DecisionRungSystem.
It WRAPS it, adding structured perception and causal reasoning around
the existing rung evaluation. Rungs become the "REASONED" speed of
action selection — the middle path between fast mapped execution and
slow exploratory discovery.

Usage:
    loop = CognitiveLoop(decision_system, db)
    loop.start_game(game_id, available_actions)

    # Per action:
    action, data, frame_record = loop.cycle(frame, obs)
    # ... execute action ...
    loop.record_result(frame_changed, score_delta, level_changed)

    # After game:
    replay = loop.get_replay()
"""

import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from engines.cognition.causal_map import CausalMap, PlannedAction
from engines.cognition.cognitive_frame import CognitiveFrame
from engines.cognition.phenomenology_layer import FeltState, PhenomenologyLayer, Valence
from engines.egocentric.swallow import swallow_note as _swal  # B4: swallow counter
from engines.perception.perceiver import Perceiver
from engines.perception.perceptual_field import PerceptualField

logger = logging.getLogger(__name__)

# ── Movement-stack + reset-discipline knobs (Register G; provenance GUESSED,
#    arm-testable — the A5 law: marked so they never read as settled;
#    registered in record/canon/KNOBS.md AMENDMENT 9) ─────────────────────────────────────
NAV_BIAS_P = 0.5     # GUESSED: cap on the [NAV] steer's share of blind draws
RESET_MIN_RUN = 3    # GUESSED: frame-changing steps that make a run "solid"
#                      (the [RESET] counter is INSTRUMENTATION ONLY — no
#                      selection guard ships until the counter has reported)


def _neg_feed(loop, mut) -> None:
    """B6 (BUILD_PROGRAM_2 W1): the negative-evidence feeder — every W4c-1
    class comparison examined counts neg_tried; an UNMUTATED comparison IS a
    negative instance accrued (neg_passed). Feeds the reserved
    NO_NEGATIVE_INSTANCES starvation socket (R1). One-line call site by the
    .credit/.route window law; containment: never raises."""
    try:
        _c = getattr(loop, "_w4c_counters", None)
        if _c is not None:
            _c["neg_tried"] = _c.get("neg_tried", 0) + 1
            if not mut:
                _c["neg_passed"] = _c.get("neg_passed", 0) + 1
    except Exception:
        pass


def _seed_imp(loop) -> None:
    """W1 (CONSUMER DRIVER, seed side): enter this agent's import_candidates
    for (game, playing level) into Gamma at the gamma init site — episode N's
    end_game consumed the queue; episode N+1 seeds the candidates here, each
    atom flagged imported=True (consumer.seed_imports' exact signature; the
    wheel rule outranks imports — 2x TRANSFERRED still required to drive).
    One-line call site by the .credit/.route window law; containment: never
    raises."""
    try:
        _g = getattr(loop, "_gamma", None)
        _f = getattr(loop, "_ego_fabric", None)
        if _g is not None and _f is not None:
            from engines.egocentric.consumer import seed_imports
            _n = seed_imports(_g, _f, str(getattr(loop, "_game_id", "") or "game"),
                              int(getattr(loop, "_ego_level", 0) or 0) + 1)
            # W1 narration: cross-role candidates in play -> [COL]/cross-role
            loop._narr_import_n = int(_n or 0)
            if _n:
                print(f"[IMPORT] seeded {_n} candidate atom(s) imported=True")
    except Exception:
        _swal(loop, "OTHER")


def _goal_bank(loop, game, level, pre, post) -> int:
    """G-C: THE ONE BANKING CORE — every route to the abduction bank enters here.

    LINK3_AUDIT: `_goal_abd` used to hold this body and had exactly ONE call
    site, inside the cognitive cycle. A level-up reached by PREFIX REPLAY never
    enters that cycle, so it never reached the bank — which is why every banked
    record was level 1 (level 1 is reached by exploration, level 2 only by
    replay: SUCCESS SUPPRESSES THE EVIDENCE CHANNEL). The body is therefore
    factored out here rather than copied, so the two routes cannot drift and
    the cognitive cycle is not duplicated.

    Mines the pre->post frame delta for STRUCTURAL predicates (mechanics, never
    answers) and banks them as game+level-scoped GOAL HYPOTHESES on the
    collective "goal_hypotheses" stream; a level-up WITHOUT a known predicate
    falsifies it (credibility drops). Returns the number banked; containment:
    0 on anything at all, never raises."""
    _n = 0
    try:
        if pre is None or post is None:
            return 0
        _fab = getattr(loop, "_ego_fabric", None)
        if _fab is None:
            # REACHABILITY, not tidiness: the cycle's lazy fabric init lives in
            # record_result, and the REPLAY seam runs BEFORE the cycle is ever
            # entered (play_game replays a banked prefix ahead of the explore
            # loop) on a loop built fresh for this episode. Without this the hook
            # would be reachable and INERT -- banking into a None fabric -- the
            # exact severed-organ shape this build exists to close. Same root,
            # same agent, no seeds.
            from engines.egocentric.fabric import KnowledgeFabric
            _fab = KnowledgeFabric(
                "ego_fabric",
                agent_id=str(getattr(loop, "_ego_agent_id", "") or "agent"),
                kin_key="v4")
            loop._ego_fabric = _fab
        # ...and REBIND when the cycle's init later swaps in the SEEDED fabric:
        # hypotheses() reads seed mounts, so a book left on the seedless
        # pre-cycle instance would silently lose every inherited hypothesis.
        _bk = getattr(loop, "_goal_book", None)
        if _bk is None or getattr(_bk, "fabric", None) is not _fab:
            from engines.egocentric.goal_abduction import GoalBook
            _bk = GoalBook(_fab)
            loop._goal_book = _bk
        for _b in loop._goal_book.observe_levelup(
                str(game or "game"), int(level),
                np.asarray(pre), np.asarray(post)):
            _n += 1
            print(f"[GOAL] banked {_b.get('sig')} (level-up delta hypothesis)")
    except Exception:
        _swal(loop, "SPINE")
    return _n


def _goal_abd(loop, level_changed, post_array) -> None:
    """G-C (PREREG_FINAL_GAPS): goal abduction's COGNITIVE-CYCLE bank site — on a
    level-up, hand the pre->post frame delta to `_goal_bank`. A3-2 CONVENTION
    (PLAYING level): _ego_level has already been incremented on this
    level-changed step, so the bare value banked here IS the playing level at
    which the goal was achieved (pre-increment + 1). One-line call site placed
    AFTER the .credit/.route anchors by the window law; containment: never
    raises."""
    try:
        _pre = getattr(loop, "_prev_frame", None)
        if not level_changed or _pre is None or post_array is None:
            return
        _goal_bank(loop, str(getattr(loop, "_game_id", "") or "game"),
                   int(getattr(loop, "_ego_level", 0) or 0), _pre, post_array)
    except Exception:
        _swal(loop, "SPINE")


def _hyd_ver(loop) -> Dict[str, int]:
    """A3-1 (record/canon/KNOBS.md AMENDMENT 3): "verified" is BOOK-DERIVED. Hydrate the
    planner's per-atom TRANSFERRED tally from the settlements books at the W4c
    lazy-init, so cross-episode verification persists (pre-fix the dict was
    born empty and every atom -- imported atoms especially -- had to re-earn
    its 2x TRANSFERRED inside a single episode). The in-episode increment path
    is unchanged: it adds to this hydrated base.

    Scope: THIS game at the FULL version-id grain (A3-3 knowledge grain) at
    the PLAYING level (_ego_level + 1 -- A3-2 CONVENTION (PLAYING level):
    settlements carry the level being played). Reads the personal AND
    collective settlements streams (BetBook writes collective today; personal
    is the forward-compatible half of the pair), BOUNDED to the last N=500
    records per scope -- the janitor's settlements retention is 100 raw
    records, so 500 covers every survivor without an unbounded scan. One-line
    call site by the .credit/.route window law; containment: empty dict,
    never raises."""
    out: Dict[str, int] = {}
    try:
        fab = getattr(loop, "_ego_fabric", None)
        if fab is None:
            return out
        g = str(getattr(loop, "_game_id", "") or "game")
        lv = int(getattr(loop, "_ego_level", 0) or 0) + 1
        for scope in ("personal", "collective"):
            try:
                rows = fab.query(scope, "settlements")
            except Exception:
                continue
            for rec in rows[-500:]:                  # bounded read: last N=500
                try:
                    if (rec.get("atom_bin") == "TRANSFERRED"
                            and rec.get("atom_key") is not None
                            and str(rec.get("game")) == g
                            and int(rec.get("level", -1)) == lv):
                        k = str(rec.get("atom_key"))
                        out[k] = out.get(k, 0) + 1
                except Exception:
                    continue
        if out:
            print("[VERIFIED] hydrated %d atom(s) from the books "
                  "(game=%s level=%d)" % (len(out), g, lv))
    except Exception:
        pass
    return out


def _narr_range(loop):
    """W1 (PREREG_W1_NARRATION.md): the step's memory-range tag, resolved from
    O(1) IN-HAND state only (no scans, no queries -- the F2 overhead law):
    read-only seed mounts with inherited ideas active -> [COL]/inherited-library;
    cross-agent import candidates seeded into Gamma -> [COL]/cross-role;
    book-hydrated own history (or own re-seeded priors) -> [OWN]; else [EP].
    Nothing reads the kin scope at decision time today, so role-pool is
    resolvable by the pure function but never claimed falsely here."""
    from engines.egocentric import narration as _na
    _fab = getattr(loop, "_ego_fabric", None)
    _seeded = (len(getattr(loop, "_ego_seeded", None) or {})
               + len(getattr(loop, "_ego_seeded_clicks", None) or {}))
    _inh = _seeded if (_fab is not None and getattr(_fab, "seeds", None)) else 0
    _own = (len(getattr(loop, "_atom_verified", None) or {})
            + (0 if _inh else _seeded))
    return _na.memory_range(
        replay=False, inherited_n=_inh, kin_n=0,
        collective_n=int(getattr(loop, "_narr_import_n", 0) or 0), own_n=_own)


def _narr_bet(loop, action_num, cf, pg0, frame=None) -> None:
    """W1 (PREREG_W1_NARRATION.md): the BET-SIDE narration -- emitted in
    cycle() BEFORE the action executes. Narration is the decision, not a log:
    the per-slot prediction, ROUTE bin + why-not-the-neighbour-bin, mint
    candidate/guard-zero and the memory-range tag are written at decision
    time, and ACT then references the BET record's id (earlier per-step
    sequence number -- falsifier F1's precedence check). PLAN narrates
    drove/shadowed/no-steps with the g-gate that stopped it (pg0 = the gate
    counters before this cycle's plan block ran). One-line call site by the
    window law; containment: never raises. O(1) per event."""
    try:
        from engines.egocentric import narration as _na
        _fab = getattr(loop, "_ego_fabric", None)
        _gid = str(getattr(loop, "_game_id", "") or "")
        if _fab is None:
            if not _gid:
                return          # no started game: nothing to narrate about
            # REACHABILITY (the _goal_bank seam): the lazy fabric init lives in
            # record_result, so without this the first step's bet would be
            # silent -- and a bet recorded after the action is no bet at all.
            from engines.egocentric.fabric import KnowledgeFabric
            _fab = KnowledgeFabric(
                "ego_fabric",
                agent_id=str(getattr(loop, "_ego_agent_id", "") or "agent"),
                kin_key="v4")
            loop._ego_fabric = _fab
        _nsp = getattr(loop, "_narration", None)
        if _nsp is None or _nsp.fabric is not _fab:
            # rebind when the seeded fabric replaces the pre-cycle instance
            _nsp = _na.NarrationSpine(_fab, game=_gid or "game")
            loop._narration = _nsp
        _pm_attach(loop, _nsp)   # PERSISTENCE MONITOR: the one attach site
        _nsp.start_step(int(getattr(loop, "_actions_taken", 0) or 0))
        # W1 FALSIFIER ARMS: the switch narrated once at game start (the ARM
        # record -- idempotent per spine; absent on loops with no arm state)
        _narm = getattr(loop, "_narr_arm", None)
        if _narm is not None:
            _nsp.narrate_arm(_narm)
        _rng, _cc = _narr_range(loop)
        # per-slot predictions: the bank's committed slots (consumed here)
        _slots = getattr(loop, "_narr_slots", None) or []
        loop._narr_slots = None
        _own_n = len(getattr(loop, "_atom_verified", None) or {})
        _pbin, _why = _na.predict_bin(bool(_slots), _own_n > 0)
        _slotmap = {str(_s): {"predicted": "holds"} for _s in _slots}
        # mint at bet time: a queued candidate, or SUPPORT is the zero (no
        # residual exists before the action lands)
        _rt = getattr(loop, "_residual_router", None)
        _pend = bool(_rt is not None and _rt.mint_queue)
        _nsp.bet(slots=_slotmap, route_bin=_pbin, why_not=_why,
                 mint_candidate=("pending" if _pend else None),
                 guard_zero=(None if _pend else _na.GUARD_SUPPORT),
                 rng=_rng, col_class=_cc,
                 level=int(getattr(loop, "_ego_level", 0) or 0))   # additive
        # W2b (PREREG_W2B_PLANNER_SCHEDULING.md): a scheduler skip owns the
        # PLAN point this cycle -- the skip is narrated WITH ITS REASON (F3,
        # mode="skipped", gate=reason), never silent; otherwise the g-gate
        # verdict narrates exactly as before. One PLAN record per cycle.
        _w2s = getattr(loop, "_w2b_narr", None)
        loop._w2b_narr = None
        if _w2s is not None:
            # COMPOSER STAGE 4: a third element carries the composite's
            # citation state (settled/unsettled, driven step) on the record.
            _nsp.plan(str(_w2s[0]), _w2s[1], rng=_rng, col_class=_cc,
                      extra=(_w2s[2] if len(_w2s) > 2 else None))
        else:
            _pv = _na.plan_verdict(pg0, getattr(loop, "_plan_gate", None) or {})
            _nsp.plan(_pv["mode"], _pv["gate"], rng=_rng, col_class=_cc)
        _rung = (getattr(cf, "rung_name", "") or getattr(cf, "action_speed", "")
                 or "")
        _nsp.act(int(action_num), _rung, rng=_rng, col_class=_cc,
                 fallback=bool(getattr(cf, "fallback", False)))   # D-8
        _gate_step(loop, action_num, cf, _nsp, frame)   # GATE STAGE 1: shadow, void
        # clear the outcome caches: record_result closes THIS step only
        loop._narr_settle = None
        loop._narr_mint = None
        loop._narr_route_consumed = None    # WIRE 1 stash: this step only
        loop._narr_mint_sig = None          # WIRE 2 stash: this step only
    except Exception:
        _swal(loop, "OTHER")


def _narr_close(loop, post_array, frame_changed) -> None:
    """W1 (PREREG_W1_NARRATION.md): the OUTCOME-SIDE narration -- record_result
    closes the loop against the pre-action bet by reference: PERCEIVE (per
    slot, never aggregated), ROUTE (settled bin + why-not-the-neighbour), MINT
    (candidate or guard-zero + both sides of the MDL bargain), ECHO (settled
    vs candidate). Reads ONLY this step's cached settle/mint state -- no
    scans, no queries (F2). One-line call site; containment: never raises."""
    try:
        from engines.egocentric import narration as _na
        _nsp = getattr(loop, "_narration", None)
        if _nsp is None:
            return
        _rng, _cc = _narr_range(loop)
        _ns = getattr(loop, "_narr_settle", None) or {}
        loop._narr_settle = None
        # PERCEIVE: prediction vs outcome, PER SLOT -- never aggregated
        _slots = {str(_s): {"bet": bool(_v.get("bet")),
                            "residual": float(_v.get("residual", 0.0) or 0.0),
                            "bin": _v.get("bin")}
                  for _s, _v in _ns.items()}
        _nsp.perceive(_slots, rng=_rng, col_class=_cc)
        # ROUTE: the primary slot's bin + the discriminating fact vs neighbour
        # (arm C: a consumed in-band tie-break cites the consumed BET id)
        _prim = ("WORKSPACE" if "WORKSPACE" in _ns
                 else (sorted(_ns)[0] if _ns else None))
        _pbin = (_ns.get(_prim) or {}).get("bin") if _prim else None
        _rcons = getattr(loop, "_narr_route_consumed", None)
        loop._narr_route_consumed = None
        _nsp.route(_pbin, _na.route_why_not(_pbin),
                   {_s: _v.get("bin") for _s, _v in _ns.items()},
                   rng=_rng, col_class=_cc,
                   extra=({"consumed": _rcons} if _rcons else None))
        # MINT: the verdict this step (if any offer reached the mint), the
        # guard that zeroed otherwise, and both sides of the MDL bargain
        # (arm C: the offer's signature/support/route ride the record and are
        # retained in-memory; a WIRE 2 skip carries reason + consumed id)
        _mv = getattr(loop, "_narr_mint", None)
        loop._narr_mint = None
        _chg = None
        _pre = getattr(loop, "_w4c_pre_frame", None)
        if (_pre is not None and post_array is not None
                and getattr(_pre, "shape", None) == post_array.shape):
            _chg = int((_pre != post_array).sum())
        _mc = _na.mint_close(_mv, _chg)
        _mx = {_k: _mc[_k] for _k in ("reason", "consumed")
               if _mc.get(_k) is not None}
        _msig = getattr(loop, "_narr_mint_sig", None)
        loop._narr_mint_sig = None
        if _msig:
            _mx.update(_msig)
        _nsp.mint_point(_mc["candidate"], _mc["verdict"], _mc["guard_zero"],
                        _mc["bargain"], rng=_rng, col_class=_cc,
                        extra=(_mx or None))
        # ECHO: what settled, or *candidate* stated as such
        _settled = any(bool(_v.get("bet")) for _v in _ns.values())
        _status = ("candidate" if _mc["candidate"]
                   else ("settled" if _settled else "silent"))
        _nsp.echo(_status, {"frame_changed": bool(frame_changed)},
                  rng=_rng, col_class=_cc)
    except Exception:
        _swal(loop, "OTHER")


def _w2b_mark(loop) -> tuple:
    """W2b (PREREG_W2B_PLANNER_SCHEDULING.md): the world-change mark GATE B
    compares -- (Gamma mints passed, cross-role imports seeded, standing
    RE-ENTRIES), all three already counted by the loop's own organs (R1 mint
    socket counter + the _seed_imp narration count + standing.StandingBook's
    reentry counter). O(1) reads of in-hand state; an unchanged mark alongside
    an unchanged state key means nothing was minted, imported or re-admitted
    since the last planner attempt.

    THE THIRD COMPONENT (R3/R4, PREREG_STANDING_HALF_LIFE_ATOMS.md): a
    RE-ENTRY grew the candidate set, so the search would no longer return the
    same nothing. An EVICTION shrank it and deliberately does NOT reopen the
    gate -- asking the same question of a strictly smaller set gets the same
    answer, and the starvation guard is untouched either way."""
    return (int((getattr(loop, "_w4c_counters", None) or {}
                 ).get("mint_passed", 0) or 0),
            int(getattr(loop, "_narr_import_n", 0) or 0),
            int(getattr(getattr(getattr(loop, "_w2b_sched", None),
                                "standing", None), "reentries", 0) or 0))


def _w2b_engage(loop, pframe, cf) -> bool:
    """W2b (PREREG_W2B_PLANNER_SCHEDULING.md): THE PLANNER AS LAST RESORT --
    the ONE engagement decision, shared by both plan seams in cycle() (the
    reference-mode identity search and the abduced-goal path). NOTE: the
    planner's own name is deliberately not written here -- the source laws in
    tests/gate key on its FIRST occurrence being the live seam, not a
    docstring mention.

    GATE A (cheap routes first): a CANDIDATE-PRODUCING route (mapped = a plan
    step from the causal map; reasoned = a rung's decision -- cf.action_speed,
    set by _act before this runs) whose cf.action_confidence is at or above
    scheduler.CHEAP_ROUTE_CONF_BAR already holds the wheel and no search runs.
    Explore/random speeds ARE the cheap routes having failed to produce a
    candidate (a heuristic info-gain score is not an option above a rung's
    confidence), so they pass conf=None and GATE A stays open -- the prereg's
    "no rung above a stated confidence produced an option this cycle" read
    literally. GATE B (no re-search of an unchanged
    world): same state key + same (mint, import) mark as the last attempt on
    (game, level) -> SKIP. STARVATION GUARD (absolute, F2): conf below the bar
    with no retained identical attempt opens BOTH gates by construction -- a
    cycle where every cheap route failed reaches the planner IN THAT CYCLE;
    the gates defer within a cycle, never deny across cycles. A skip is
    narrated at the PLAN point with its reason (F3) via _narr_bet's emitter
    (loop._w2b_narr), never silent. Containment: FAILS OPEN -- any internal
    error engages the planner, so the scheduler can never starve it."""
    try:
        from engines.egocentric import scheduler as _s2b
        if getattr(loop, "_w2b_sched", None) is None:
            loop._w2b_sched = _s2b.PlannerScheduler()
        _g = str(getattr(loop, "_game_id", "") or "game")
        _lv = int(getattr(loop, "_ego_level", 0) or 0)
        _key = _s2b.state_key(pframe)
        _spd = str(getattr(cf, "action_speed", "") or "")
        _conf = (float(getattr(cf, "action_confidence", 0.0) or 0.0)
                 if _spd in ("mapped", "reasoned") else None)
        _v = loop._w2b_sched.decide(_g, _lv, _key, _conf, _w2b_mark(loop))
        if _v["engage"]:
            loop._w2b_sched.note_attempt(_g, _lv, _key, _w2b_mark(loop))
            loop._w2b_key = _key    # the abort router's plan-time key
            print(f"[PLAN] engage reason={_v['reason']}")
            # R3/R4 (PREREG_STANDING_HALF_LIFE_ATOMS.md): THE ENGAGEMENT
            # SWEEP -- tau is recomputed over the atoms valid at this
            # (game, level) and the eviction / re-entry transitions are
            # written HERE, not inside the search itself, which goes on
            # treating Gamma as read-only. Ordered AFTER note_attempt on
            # purpose: a re-entry written now differs from the mark just
            # retained, so it reopens GATE B on the NEXT cycle.
            _std_sweep(loop, _g, _lv)
            return True
        loop._w2b_narr = ("skipped", _v["reason"])
        print(f"[PLAN] skip reason={_v['reason']}")
        return False
    except Exception:
        _swal(loop, "PLANNER")
        return True     # the starvation guard outranks: never deny on error


def _w2b_abort(loop, frame_changed, level_changed) -> None:
    """W2b RIDER (the shadow test's Interruption finding): ROUTE a driven
    plan's abort -- WORLD-MOVED (the state key changed under the plan:
    re-plan, no penalty; the retained key drops so GATE B cannot block the
    re-plan) vs PLAN-WRONG (state as predicted, the step failed: recorded
    against the plan's atoms). Each narrated at the PLAN point with its
    discriminator (F4). Today a driven plan is a single same-cycle step, so
    live aborts compare equal keys and route PLAN-WRONG; WORLD-MOVED is the
    seam a multi-cycle drive inherits, gate-tested via constructed calls
    (tests/gate/test_planner_scheduling.py). A level change also clears the
    retained state key here (binder.on_level_change's pattern). One-line call
    site in record_result; containment: never raises."""
    try:
        _sch = getattr(loop, "_w2b_sched", None)
        _dr = getattr(loop, "_w2b_driven", None)
        loop._w2b_driven = None          # one step, one routing -- never stale
        if _sch is None:
            return
        if level_changed:
            _sch.on_level_change()       # the board redraws; the key re-earns
            return
        if _dr is None or _dr.get("key") is None:
            return                       # no driven plan
        if frame_changed:
            # THE NO-ABORT BRANCH (R3/R4): the step LANDED. This early return
            # recorded nothing until now, so an atom that held a hundred times
            # was indistinguishable from one that had never been tried. It is
            # recorded per step atom as an EARN event (e3) and the routing
            # below is skipped exactly as before.
            _std_held(loop, list(_dr.get("steps") or []))
            return
        from engines.egocentric import scheduler as _s2b
        _pf = getattr(loop, "_prev_frame", None)
        _obs = _s2b.state_key(_pf) if _pf is not None else str(_dr.get("key"))
        _rt = _s2b.route_abort(str(_dr.get("key")), _obs)
        _steps = [str(_s) for _s in (_dr.get("steps") or [])]
        _sch.on_abort(_rt["route"], str(getattr(loop, "_game_id", "") or "game"),
                      int(getattr(loop, "_ego_level", 0) or 0), _steps)
        _nsp = getattr(loop, "_narration", None)
        if _nsp is not None:
            _rng, _cc = _narr_range(loop)
            # R3/R4: `steps` + `ep` on the record that ALREADY fires -- the
            # ledger's in-memory increment made durable without a second
            # stream. A world-moved abort carries the same pair and is never
            # counted: the reader keys on the gate, and those atoms were never
            # given the state they bet on (FIGURE 2 -- no penalty without a
            # contact with the ground).
            _ep = _std_ep(loop)
            _nsp.plan("abort", _rt["route"], rng=_rng, col_class=_cc,
                      extra=({"steps": _steps, "ep": int(_ep)}
                             if _ep is not None else {"steps": _steps}))
        print(f"[PLAN] abort routed={_rt['route']} ({_rt['fact']})")
    except Exception:
        _swal(loop, "PLANNER")


# ═════════════════════════════════════════════════════════════════════════════
# R3/R4 -- STANDING AT THE ATOM GRAIN (PREREG_STANDING_HALF_LIFE_ATOMS.md):
# the loop-side seams. Three one-line call sites (the engagement sweep in
# _w2b_engage, the HELD record in _w2b_abort, the composite settle's ordinal
# in _w3d_settle) and one clock read. Nothing here computes S: the book does,
# and S leaves this module only as a VISIT ORDER (FIGURE 1 -- never a price,
# never a report). Containment: every seam swallows.
# ═════════════════════════════════════════════════════════════════════════════

def _std_ep(loop):
    """THE ONE CLOCK: the A3-4 episode ordinal in force, read from the mint
    that already stamps it on every verdict. None when there is no mint --
    and by the module's law an event with no ordinal is not counted, never
    counted at a guessed one."""
    from engines.egocentric import standing as _std
    return _std.episode_of(getattr(loop, "_mdl_mint", None))


def _std_book(loop):
    """The scheduler's standing book (it owns it beside the W2c retention
    store), or None before the scheduler exists."""
    return getattr(getattr(loop, "_w2b_sched", None), "standing", None)


def _std_held(loop, steps) -> None:
    """EARN EVENT e3: a driven plan step that LANDED, recorded per step atom
    at the PLAN point with the fixed token `held`. The record carries `steps`
    + `ep` -- exactly the pair the plan-wrong abort record carries, so one
    reader reads both sides of the ledger and neither side is a special
    case."""
    try:
        from engines.egocentric import standing as _std
        _nsp = getattr(loop, "_narration", None)
        _ep = _std_ep(loop)
        if _nsp is None or _ep is None or not steps:
            return
        _rng, _cc = _narr_range(loop)
        _nsp.plan(_std.PLAN_HELD, _std.HELD_GATE, rng=_rng, col_class=_cc,
                  extra={"steps": [str(_s) for _s in steps], "ep": int(_ep)})
    except Exception:
        _swal(loop, "PLANNER")


def _std_sweep(loop, game, level) -> None:
    """THE ENGAGEMENT SWEEP: recompute tau over the atoms valid at
    (game, level) and write the eviction / re-entry transitions
    (standing.StandingBook.engage -- the ONE writer). Each transition is
    narrated at the PLAN point with the FIXED tokens `evicted` / `re-entered`
    and the atom id, carrying tau and the decay rate beside it (FIGURE 10:
    the append itself carries S / tau / ep / cause, so a later reader can
    locate the error rather than feel it)."""
    try:
        _bk = _std_book(loop)
        _gm = getattr(loop, "_gamma", None)
        if _bk is None or _gm is None:
            return
        from engines.egocentric import standing as _std
        _out = _bk.engage(_gm, str(game), int(level))
        _nsp = getattr(loop, "_narration", None)
        for _tok, _slot in ((_std.PLAN_EVICTED, "evicted"),
                            (_std.PLAN_REENTERED, "re_entered")):
            for _aid in _out.get(_slot) or []:
                if _nsp is not None:
                    _rng, _cc = _narr_range(loop)
                    _nsp.plan(_tok, str(_aid), rng=_rng, col_class=_cc,
                              extra={"tau": _out.get("tau"),
                                     "d": _out.get("d"),
                                     "borrowed": _out.get("borrowed")})
                print(f"[PLAN] {_tok} id={_aid} tau={_out.get('tau')} "
                      f"d={_out.get('d'):.4f} borrowed={_out.get('borrowed')}")
    except Exception:
        _swal(loop, "PLANNER")


# =============================================================================
# PERCEPTUAL BLACKBOARD ADAPTER
# =============================================================================


class PerceptualBlackboardAdapter:
    """
    Adapter that makes PerceptualField + CognitiveLoop state look like a
    Blackboard for PhenomenologyLayer.

    PhenomenologyLayer reads from ``blackboard.get(key, default)`` and writes
    via ``blackboard.slot(key, value, source_rung=...)``.  This adapter
    translates those reads into live PerceptualField fields and CognitiveLoop
    game state so PhenomenologyLayer can compress perception without
    depending on the full Blackboard infrastructure.

    Written values (from ``inject()``) are stored in a local overlay dict
    and returned on subsequent ``get()`` calls, closing the feedback loop.
    """

    def __init__(self) -> None:
        self._percept: Optional[PerceptualField] = None
        self._loop_state: Dict[str, Any] = {}
        self._injected: Dict[str, Any] = {}
        self._prev_confidence: float = 0.0
        self._recent_strategies: List[str] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def update(
        self, percept: PerceptualField, loop_state: Dict[str, Any]
    ) -> None:
        """Refresh with fresh perception + loop state each cycle."""
        if self._percept is not None:
            self._prev_confidence = self._percept.overall_confidence
        self._percept = percept
        self._loop_state = loop_state

    def reset(self) -> None:
        """Reset for a new game."""
        self._percept = None
        self._loop_state = {}
        self._injected = {}
        self._prev_confidence = 0.0
        self._recent_strategies = []

    # ------------------------------------------------------------------
    # Blackboard-compatible read (used by PhenomenologyLayer.compress)
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Blackboard-compatible ``get``."""
        # Injected values (written by PhenomenologyLayer.inject) win
        if key in self._injected:
            return self._injected[key]

        if self._percept is None:
            return default

        value = self._resolve(key)
        return value if value is not None else default

    # ------------------------------------------------------------------
    # Blackboard-compatible write (used by PhenomenologyLayer.inject)
    # ------------------------------------------------------------------

    def slot(
        self,
        key: str,
        value: Any = None,
        *,
        source_rung: str = "unknown",
        confidence: float = 1.0,
        source_primitive: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Any:
        """Blackboard-compatible ``slot`` (write when *value* given)."""
        if value is not None:
            self._injected[key] = value
            return value
        return self._injected.get(key)

    # ------------------------------------------------------------------
    # Slot resolution: maps blackboard key -> PerceptualField/loop state
    # ------------------------------------------------------------------

    def _resolve(self, key: str) -> Any:  # noqa: C901 — intentionally flat dispatch
        """Translate a single blackboard key to perception data."""
        p = self._percept
        s = self._loop_state
        if p is None:
            return None

        # -- Epistemic quadrant (derived from confidence) --
        if key == "epistemic_quadrant":
            c = p.overall_confidence
            if c > 0.7:
                return "KK"
            if c > 0.4:
                return "KU"
            if c > 0.2:
                return "UK"
            return "UU"

        # -- Theory / control --
        if key == "working_theory":
            return True if (p.has_plan or p.map_completeness > 0.5) else None
        if key == "controlled_object":
            return True if len(p.known_effects) > 2 else None

        # -- Threat signals --
        if key == "contradiction_detected":
            return p.surprise > 0.7
        if key == "cascade_failure":
            return False
        if key == "action_budget_critical":
            max_a = s.get("max_actions", 500)
            return p.actions_remaining < max_a * 0.1

        # -- Frame / delta --
        if key == "frame_delta_magnitude":
            eff = p.last_action_effect
            return eff.pixels_changed if eff else 0
        if key == "no_change_frames":
            return p.consecutive_no_change

        # -- Strategy stability --
        if key == "strategy_stability":
            strats = self._recent_strategies
            if len(strats) < 3:
                return 1.0
            recent = strats[-5:]
            same = sum(1 for a, b in zip(recent, recent[1:]) if a == b)
            return same / max(len(recent) - 1, 1)

        # -- Success rate --
        if key == "recent_success_rate":
            if p.actions_taken == 0:
                return 0.5
            base_rate = max(
                0.0,
                1.0 - p.consecutive_no_change / max(p.actions_taken, 1),
            )
            # Penalize monotonous action repetition: repeating the same
            # action isn't "success" even if the frame changes (e.g.
            # walking in one direction forever).  Each repetition past 5
            # reduces the success rate by 10%.
            same_action = getattr(self, '_consecutive_same_action', 0)
            if same_action > 5:
                penalty = min(0.8, (same_action - 5) * 0.10)
                base_rate = max(0.0, base_rate - penalty)
            return base_rate

        # -- Novelty / surprise --
        if key == "novelty_score":
            return p.surprise * 0.5
        if key == "surprise_score":
            return p.surprise
        if key == "pattern_break":
            return p.surprise > 0.5

        # -- Stuck --
        if key == "stuck_detected":
            return p.consecutive_no_change > 5

        # -- Game progress --
        if key == "levels_completed":
            return s.get("levels_completed", 0)
        if key == "total_levels":
            return s.get("total_levels", 6)
        if key == "death_count":
            return 0

        # -- Confidence delta --
        if key == "confidence_delta":
            return p.overall_confidence - self._prev_confidence

        # -- Score delta --
        if key == "score_delta":
            eff = p.last_action_effect
            return eff.score_delta if eff else 0

        # -- Open questions / unknowns --
        if key == "known_unknowns":
            return list(p.unexplored_positions)
        if key == "open_questions":
            return list(p.unexplored_positions)

        # -- Tick / path --
        if key == "current_tick":
            return s.get("actions_taken", 0)
        if key == "recent_path":
            return s.get("recent_path", [])

        return None


class CognitiveLoop:
    """
    Perceive -> Think -> Map -> Act orchestrator.

    Wraps the existing DecisionRungSystem with structured perception
    and causal reasoning. Produces observable CognitiveFrames.
    """

    def __init__(
        self,
        decision_system: Any = None,
        context_builder: Any = None,
        db: Any = None,
        verbose: bool = False,
    ):
        """
        Initialize the cognitive loop.

        Args:
            decision_system: DecisionRungSystem instance (for REASONED speed)
            context_builder: ContextBuilder instance (for backward compat context)
            db: Database interface for loading prior knowledge
            verbose: Print cognitive frames to console
        """
        self._decision_system = decision_system
        self._context_builder = context_builder
        self._db = db
        self._verbose = verbose

        # Core components
        self._perceiver = Perceiver()
        self._causal_map: Optional[CausalMap] = None

        # Phenomenology: blackboard adapter + compression layer
        self._bb_adapter = PerceptualBlackboardAdapter()
        self._phenomenology = PhenomenologyLayer(self._bb_adapter)  # type: ignore[arg-type]

        # Game state
        self._game_id: str = ""
        self._available_actions: List[int] = []
        self._max_actions: int = 500
        self._actions_taken: int = 0
        self._current_level: int = 1
        self._score: float = 0.0

        # Frame tracking
        self._prev_frame: Optional[np.ndarray] = None
        self._consecutive_no_change: int = 0

        # Action repetition tracking (monopoly detection)
        self._last_action_type: Optional[int] = None
        self._consecutive_same_action: int = 0

        # Replay
        self._frames: List[CognitiveFrame] = []
        self._current_frame: Optional[CognitiveFrame] = None

        # Last action info (for temporal perception)
        self._last_action_info: Optional[Dict[str, Any]] = None

        # Prior knowledge state
        self._prior_knowledge_loaded: bool = False
        self._prior_effects_count: int = 0  # How many position effects loaded from DB
        self._prior_rules_count: int = 0    # How many rules loaded from DB

        # ═══ GAP 1: Frame history for stable region detection ═══
        self._frame_history: List[np.ndarray] = []  # Last N frames
        self._stable_mask: Optional[np.ndarray] = None  # Boolean: True = never changed
        self._stable_region_attempts: int = 0  # How many times we've tried (allow retry)
        self._reference_snapshot: Optional[np.ndarray] = None  # Stable pixels snapshot

        # ═══ GAP 2: Goal-delta tracking ═══
        self._last_goal_delta_count: int = 0  # Cells wrong before last action
        self._goal_cells_total: int = 0  # Total goal cells detected

        # ═══ GAP 3: Active plan for execution ═══
        self._active_plan: List[Any] = []
        self._agent_position: Optional[Tuple[int, int]] = None  # For movement games

        # ═══ GAP 5: HUD state tracking ═══
        self._prev_hud_hash: int = 0
        self._hud_edge_size: int = 6  # Pixels from frame edge considered HUD

        # ═══ GAP 5C: Per-region HUD tracking ═══
        self._prev_hud_region_hashes: Dict[str, int] = {
            'top': 0, 'bottom': 0, 'left': 0, 'right': 0
        }
        self._prev_hud_region_states: Dict[str, Dict[str, Any]] = {}
        # Tracks per-region: {hash, unique_colors, colored_fraction, object_count}

        # ═══ SEMANTIC GOAL: Reference panel detection ═══
        self._reference_panel: Optional[Dict[str, Any]] = None
        # {region: (y1,y2,x1,x2), cells: {(x,y): color}, detected_at_action: N}

    # ─── Game Lifecycle ───────────────────────────────────────────────

    def start_game(
        self,
        game_id: str,
        available_actions: List[int],
        max_actions: int = 500,
    ):
        """Initialize for a new game."""
        self._game_id = game_id
        self._available_actions = available_actions
        self._max_actions = max_actions
        self._actions_taken = 0
        self._current_level = 1
        self._score = 0.0
        self._prev_frame = None
        self._consecutive_no_change = 0
        self._last_action_type = None
        self._consecutive_same_action = 0
        self._last_action_info = None
        self._frames = []
        self._current_frame = None

        # Reset gap state
        self._frame_history = []
        self._stable_mask = None
        self._stable_region_attempts = 0
        self._reference_snapshot = None
        self._last_goal_delta_count = 0
        self._goal_cells_total = 0
        self._active_plan = []
        self._agent_position = None
        self._prev_hud_hash = 0
        self._prev_hud_region_hashes = {
            'top': 0, 'bottom': 0, 'left': 0, 'right': 0
        }
        self._prev_hud_region_states = {}
        self._reference_panel = None
        self._productive_rotation_index = 0  # Fix 3: rotate among productive targets

        # ═══ W1 (PREREG_W1_NARRATION.md): fresh narration state per game ═══
        self._narration = None      # spine rebinds to this game's fabric/id
        self._narr_slots = None     # the bet's per-slot stake (per step)
        self._narr_settle = None    # the step's per-slot outcome (per step)
        self._narr_mint = None      # the step's mint verdict (per step)
        self._narr_import_n = 0     # cross-role candidates seeded (per game)
        # W1 FALSIFIER ARMS ("ARM C's CONSUMPTION MUST BE REAL"): the switch,
        # read ONCE here at game init -- explicit "C" consumes narration at
        # ROUTE/MINT; anything else is "W" (narrate-only, today's behaviour,
        # the default). Narrated once at game start via narrate_arm at the
        # first bet/replay seam -- the ARM record on the personal narration
        # stream is the telemetry episode->arm labeling is read from.
        from engines.egocentric.narration import resolve_arm as _resolve_arm
        self._narr_arm = _resolve_arm()
        self._narr_route_consumed = None    # WIRE 1 provenance (per step)
        self._narr_mint_sig = None          # WIRE 2 retention stash (per step)
        print(f"[NARR] arm={self._narr_arm} "
              f"consume={'on' if self._narr_arm == 'C' else 'off'}")

        # ═══ RESET COUNTER (instrumentation pair) + MOVEMENT STACK state ═══
        self._reset_anchor = None        # (shape, bytes) of the anchor board
        self._reset_run = 0              # frame-changing steps since the anchor
        self._reset_ep_count = 0         # resets detected this episode
        self._reset_actions = {}         # action -> times it caused a reset
        self._ep_settled = False         # end_game settle (bump_episode) ran
        self._cursor_agency = None       # first activation: own-avatar map
        self._grid_nav = None            # first activation: BFS traversability
        self._nav_cell = None            # the body's current logical cell
        self._nav_goal_px = None         # abduced-goal site (px x,y) if any
        self._nav_steers = 0             # [NAV] fires this episode (the arm marker)

        # Create fresh causal map for this game
        self._causal_map = CausalMap(game_id=game_id)

        # Reset perceiver
        self._perceiver.reset()

        # Reset phenomenology layer for fresh game
        self._bb_adapter.reset()
        self._phenomenology.reset()

        # Reset prior knowledge state
        self._prior_knowledge_loaded = False
        self._prior_effects_count = 0
        self._prior_rules_count = 0

        # ═══ LOAD PRIOR KNOWLEDGE FROM DATABASE ═══
        # This is the key difference from a blank-slate approach:
        # we seed the causal map with knowledge from prior games,
        # so the agent starts with understanding, not ignorance.
        self._load_prior_knowledge(game_id)

        # Import any existing causal knowledge from context builder
        if self._context_builder is not None:
            try:
                wm = getattr(self._context_builder, '_world_model', None)
                if wm:
                    self._causal_map.import_from_world_model(wm)
            except Exception:
                pass

        if self._verbose:
            print(f"\n[COGNITIVE-LOOP] Game started: {game_id}")
            print(f"    Available actions: {available_actions}")
            print(f"    Budget: {max_actions} actions")
            if self._prior_knowledge_loaded:
                print(
                    f"    Prior knowledge: {self._prior_effects_count} effects, "
                    f"{self._prior_rules_count} rules loaded"
                )
                print(f"    {self._causal_map.summary()}")
            else:
                print("    Prior knowledge: none (first encounter)")

    def end_game(self) -> List[CognitiveFrame]:
        """End the game and return the replay."""
        # ═══ R1 (EGO-STARVE): the episode boundary settles the starvation book ═══
        # record/prereg/PREREG_READOUTS.md: a socket exercised all episode with ZERO passes
        # emits ONE enum-coded record to the PERSONAL "starvation" stream —
        # pure function of the counters (plan gates + mint/bank), narrated,
        # <= 1 per socket per episode (guarded by the settled flag).
        try:
            _sfab = getattr(self, "_ego_fabric", None)
            if _sfab is not None and not getattr(self, "_starve_settled", False):
                from engines.egocentric.starvation import StarvationBook
                _sc = dict(getattr(self, "_plan_gate", None) or {})
                _sc.update(getattr(self, "_w4c_counters", None) or {})
                StarvationBook(_sfab).settle_episode(
                    _sc, game=str(getattr(self, "_game_id", "") or "game"),
                    level=int(getattr(self, "_ego_level", 0) or 0),
                    budget_spent=int(getattr(self, "_actions_taken", 0) or 0))
                self._starve_settled = True
        except Exception:
            _swal(self, "STARVATION")
        # ═══ W1 (CONSUMER DRIVER): the SAME boundary drains the import queue ═══
        # consumer.consume was built (B12) but had NO production call site —
        # the queue never drained at runtime. Once per episode, budgeted:
        # sigma-match the queued residuals against every mounted fabric's
        # atoms; candidates land in import_candidates and the NEXT episode's
        # gamma init seeds them (seed_imports, imported=True).
        try:
            _cofab = getattr(self, "_ego_fabric", None)
            if _cofab is not None and not getattr(self, "_consume_settled", False):
                from engines.egocentric import consumer as _con
                _crep = _con.consume(
                    _cofab, str(getattr(self, "_game_id", "") or "game"),
                    int(getattr(self, "_ego_level", 0) or 0) + 1, budget_n=8)
                self._consume_settled = True
                if _crep.get("drained") or _crep.get("reopened"):
                    print(f"[IMPORT] consumed drained={_crep['drained']} "
                          f"candidates={_crep['candidates']} "
                          f"not_found={_crep['not_found']} "
                          f"declined={_crep.get('declined', 0)} "
                          f"reopened={_crep['reopened']}")
        except Exception:
            _swal(self, "OTHER")
        # ═══ B4 (BUILD_PROGRAM_2 W1): the SAME boundary settles the swallow book ═══
        # <= 1 enum-coded record per guarded block per episode to the PERSONAL
        # "swallow" stream, [SWALLOW]-narrated — a pure function of the counts
        # the instrumented except-branches accrued via _swal.
        try:
            _swfab = getattr(self, "_ego_fabric", None)
            if _swfab is not None and not getattr(self, "_swallow_settled", False):
                from engines.egocentric.swallow import SwallowBook
                SwallowBook(_swfab).settle_episode(
                    getattr(self, "_swallow_counts", None) or {},
                    game=str(getattr(self, "_game_id", "") or "game"),
                    level=int(getattr(self, "_ego_level", 0) or 0))
                self._swallow_settled = True
        except Exception:
            _swal(self, "OTHER")
        # ═══ MAINTAINER'S ORDER: the SAME boundary settles the RESET testimony ═══
        # (instrumentation pair: the counter REPORTS; no selection guard ships
        # until it has) and advances the mint's episode ordinal EXACTLY ONCE
        # (A3-4 bump_episode) so ep stamps are retry-precise across same-level
        # retries the (game, level) context cannot see. Guarded by the settled
        # flag: a double end_game never double-bumps.
        try:
            if not getattr(self, "_ep_settled", False):
                self._ep_settled = True
                _rc = int(getattr(self, "_reset_ep_count", 0) or 0)
                print(f"[RESET] episode resets={_rc} actions="
                      f"{sorted((getattr(self, '_reset_actions', None) or {}).items())}")
                if getattr(self, "_cursor_agency", None) is not None:
                    # the comparison verdict's arm marker: steers>0 episodes
                    # vs steers=0 incumbents, same game+level move books
                    print(f"[NAV] episode steers="
                          f"{int(getattr(self, '_nav_steers', 0) or 0)}")
                _mm = getattr(self, "_mdl_mint", None)
                if _mm is not None:
                    _mm.bump_episode()
        except Exception:
            _swal(self, "OTHER")
        if self._verbose and self._frames:
            print(f"\n[COGNITIVE-LOOP] Game ended: {self._game_id}")
            print(f"    Actions: {self._actions_taken}")
            print(f"    Level: {self._current_level}")
            print(f"    Score: {self._score}")
            if self._causal_map:
                print(f"    {self._causal_map.summary()}")
        return self._frames

    # ─── Prior Knowledge Loading ──────────────────────────────────────

    def _load_prior_knowledge(self, game_id: str):
        """
        Load accumulated knowledge from the database into the causal map.

        This is what makes the system LEARN ACROSS GAMES rather than
        starting from scratch. We load:

        1. World model states — causal maps from prior sessions with
           this same game, containing position-effect mappings that
           were empirically discovered.

        2. Action effectiveness — which actions produce frame changes
           for this game type, so the agent knows what kinds of actions
           are productive before taking its first step.

        3. Game lessons — distilled insights from hundreds of games,
           like "clicking toggles neighbors" or "avoid edges."

        The loaded knowledge seeds the causal map with non-zero
        completeness, which shifts strategy from "explore" (random)
        to "experiment"/"exploit" (rung-system-informed), so the
        cognitive architecture actually gets used.
        """
        if self._db is None:
            return
        if self._causal_map is None:
            return

        import json

        causal_map = self._causal_map  # Local ref for Pylance narrowing
        game_type = game_id[:4] if len(game_id) >= 4 else game_id
        effects_loaded = 0
        rules_loaded = 0

        # ─── 1. Load best causal map from prior sessions ─────────────
        try:
            # First: try exact game_id match (best — same game instance)
            rows = self._db.execute_query("""
                SELECT objects_json FROM world_model_states
                WHERE game_id = ?
                ORDER BY step_number DESC
                LIMIT 1
            """, (game_id,))

            # Second: if no exact match, load from same game TYPE
            # (cross-agent knowledge — other agents who played the
            # same game type, including horizontal transfers)
            if not rows:
                rows = self._db.execute_query("""
                    SELECT objects_json FROM world_model_states
                    WHERE game_id LIKE ?
                    ORDER BY step_number DESC
                    LIMIT 3
                """, (f'{game_type}%',))

            if rows:
                for row_entry in rows:
                    obj_json = row_entry.get('objects_json') if isinstance(row_entry, dict) else row_entry[0]
                    if not obj_json:
                        continue
                    data = json.loads(obj_json)
                    causal_data = data.get('causal_map', {})

                    for pos_key, effect_data in causal_data.items():
                        try:
                            if isinstance(pos_key, str):
                                parts = pos_key.strip('()').split(',')
                                pos = (int(parts[0].strip()), int(parts[1].strip()))
                            elif isinstance(pos_key, tuple):
                                pos = pos_key
                            else:
                                continue

                            # Import into causal map
                            observations = effect_data.get('observations', [])
                            obs_count = effect_data.get('observation_count', 0)
                            productive = effect_data.get('productive_count', 0)
                            destructive = effect_data.get('destructive_count', 0)
                            if observations:
                                # Determine if this position produces changes
                                any_change = any(
                                    len(obs.get('changes', [])) > 0
                                    for obs in observations
                                )
                                affected: list = []
                                # color_transitions must use tuple keys and
                                # list-of-tuple values to match TileEffect's
                                # type: Dict[Tuple[int,int], List[Tuple[int,int]]]
                                color_transitions: dict = {}

                                for obs in observations:
                                    for ch in obs.get('changes', []):
                                        cell = (ch.get('x', 0), ch.get('y', 0))
                                        if cell not in affected:
                                            affected.append(cell)
                                        from_c = ch.get('from_color', 0)
                                        to_c = ch.get('to_color', 0)
                                        if cell not in color_transitions:
                                            color_transitions[cell] = []
                                        color_transitions[cell].append(
                                            (from_c, to_c)
                                        )

                                from engines.cognition.causal_map import TileEffect
                                causal_map._effects[pos] = TileEffect(
                                    position=pos,
                                    affected=affected,
                                    color_transitions=color_transitions,
                                    observation_count=max(len(observations), obs_count),
                                    last_frame_changed=any_change,
                                    productive_count=productive,
                                    destructive_count=destructive,
                                )
                                causal_map._explored.add(pos)
                                causal_map._all_positions.add(pos)
                                effects_loaded += 1

                        except Exception:
                            continue

                    # ── Load color cycles ──
                    color_cycles_data = data.get('color_cycles', {})
                    for pos_key, cycle in color_cycles_data.items():
                        try:
                            if isinstance(pos_key, str):
                                parts = pos_key.strip('()').split(',')
                                pos = (int(parts[0].strip()), int(parts[1].strip()))
                            else:
                                continue
                            if isinstance(cycle, list) and cycle:
                                causal_map._color_cycles[pos] = cycle
                        except Exception:
                            continue

                    # ── Load walls ──
                    walls_data = data.get('walls', [])
                    for wall in walls_data:
                        try:
                            wpos = wall.get('pos', [])
                            wact = wall.get('action', 0)
                            if len(wpos) == 2:
                                causal_map._walls.add(
                                    (tuple(wpos), wact)
                                )
                        except Exception:
                            continue

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] World model load failed: {e}")

        # ─── 2. Load action effectiveness for this game ──────────────
        try:
            rows = self._db.execute_query("""
                SELECT action_number, success_rate, attempts, successes
                FROM action_effectiveness
                WHERE game_id = ?
            """, (game_id,))

            if rows:
                for row in rows:
                    if isinstance(row, dict):
                        action_num = row.get('action_number', 0)
                        success_rate = row.get('success_rate', 0.0)
                    else:
                        action_num = row[0]
                        success_rate = row[1] if len(row) > 1 else 0.0

                    # Store as a rule-like insight
                    if success_rate > 0.5:
                        from engines.cognition.causal_map import CausalRule
                        causal_map._rules.append(CausalRule(
                            rule_type=f"action{action_num}_effective",
                            description=(
                                f"ACTION{action_num} produces frame changes "
                                f"{success_rate:.0%} of the time"
                            ),
                            evidence_count=1,
                            confidence=min(0.8, success_rate),
                        ))
                        rules_loaded += 1

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] Action effectiveness load failed: {e}")

        # ─── 3. Load game lessons ────────────────────────────────────
        try:
            rows = self._db.execute_query("""
                SELECT lesson_text, lesson_type, confidence, key_action
                FROM game_lessons_learned
                WHERE game_type = ? AND confidence > 0.5
                ORDER BY times_retrieved DESC, confidence DESC
                LIMIT 10
            """, (game_type,))

            if rows:
                for row in rows:
                    if isinstance(row, dict):
                        lesson = row.get('lesson_text', '')
                        lesson_type = row.get('lesson_type', 'info')
                        confidence = row.get('confidence', 0.5)
                    else:
                        lesson = row[0] if row else ''
                        lesson_type = row[1] if len(row) > 1 else 'info'
                        confidence = row[2] if len(row) > 2 else 0.5

                    # Store as rules in the causal map
                    from engines.cognition.causal_map import CausalRule
                    causal_map._rules.append(CausalRule(
                        rule_type=f"lesson_{lesson_type}",
                        description=str(lesson)[:200],
                        evidence_count=1,
                        confidence=float(confidence) * 0.7,  # Discount slightly
                    ))
                    rules_loaded += 1

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] Game lessons load failed: {e}")

        # ─── 4. Load death zones as anti-knowledge ───────────────────
        try:
            rows = self._db.execute_query("""
                SELECT x_min, x_max, y_min, y_max, danger_score
                FROM death_zones
                WHERE game_type = ? AND is_active = 1
                ORDER BY danger_score DESC
                LIMIT 20
            """, (game_type,))

            if rows:
                for row in rows:
                    if isinstance(row, dict):
                        x_min = row.get('x_min', 0)
                        x_max = row.get('x_max', 0)
                        y_min = row.get('y_min', 0)
                        y_max = row.get('y_max', 0)
                    else:
                        x_min, x_max, y_min, y_max = row[0], row[1], row[2], row[3]

                    # Mark these positions as explored-and-dangerous
                    for x in range(x_min, x_max + 1):
                        for y in range(y_min, y_max + 1):
                            pos = (x, y)
                            causal_map._explored.add(pos)
                            causal_map._all_positions.add(pos)

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] Death zones load failed: {e}")

        # ─── 5. Cross-game mechanic transfer ─────────────────────────
        # Query ALL learned mechanics from ALL game types. Mechanics
        # from the *same* game type arrive with full confidence.
        # Mechanics from *other* game types arrive discounted — they
        # are hypotheses ("this new game MIGHT work like that one"),
        # not certainties. This is the meta-level transfer path.
        try:
            rows = self._db.execute_query("""
                SELECT game_type, mechanic_type, mechanic_data,
                       observation_count, confidence
                FROM learned_game_mechanics
                WHERE confidence > 0.3
                ORDER BY confidence DESC
                LIMIT 50
            """)

            if rows:
                from engines.cognition.causal_map import CausalRule
                for row in rows:
                    if isinstance(row, dict):
                        src_game = row.get('game_type', '')
                        mech_type = row.get('mechanic_type', '')
                        mech_data = row.get('mechanic_data', '{}')
                        obs_count = row.get('observation_count', 1)
                        confidence = row.get('confidence', 0.3)
                    else:
                        src_game = row[0] if row else ''
                        mech_type = row[1] if len(row) > 1 else ''
                        mech_data = row[2] if len(row) > 2 else '{}'
                        obs_count = row[3] if len(row) > 3 else 1
                        confidence = row[4] if len(row) > 4 else 0.3

                    # Same game type -> full import
                    # Different game type -> heavy discount (hypothesis only)
                    same_game = src_game == game_type
                    weight = float(confidence) if same_game else float(confidence) * 0.25

                    # Skip very weak cross-game signals
                    if weight < 0.1:
                        continue

                    origin_tag = "same-type" if same_game else f"transfer:{src_game}"

                    # Parse mechanic data to surface relevant params
                    try:
                        params = json.loads(mech_data)
                    except Exception:
                        params = {}

                    causal_map._rules.append(CausalRule(
                        rule_type=f"mechanic_{mech_type}",
                        description=(
                            f"[{origin_tag}] Mechanic '{mech_type}' "
                            f"(obs={obs_count})"
                        ),
                        evidence_count=int(obs_count),
                        confidence=weight,
                        parameters=params,
                    ))
                    rules_loaded += 1

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] Cross-game mechanics load failed: {e}")

        # ─── Summary ─────────────────────────────────────────────────
        if effects_loaded > 0 or rules_loaded > 0:
            self._prior_knowledge_loaded = True
            self._prior_effects_count = effects_loaded
            self._prior_rules_count = rules_loaded

    # ─── The Main Loop: Perceive -> Think -> Map -> Act ───────────────

    def cycle(
        self,
        frame: Any,
        obs: Any,
        agent_id: str = "",
        agent_role: str = "pioneer",
        w_A: float = 0.5,
        w_B: float = 0.5,
        available_actions: Optional[List[int]] = None,
        **extra_context,
    ) -> Tuple[int, Optional[Dict], CognitiveFrame]:
        """
        Execute one complete Perceive-Think-Map-Act cycle.

        Args:
            frame: Raw game frame (64x64)
            obs: Full observation object from API
            agent_id: Agent identifier
            agent_role: Agent role
            w_A: Stream A weight
            w_B: Stream B weight
            available_actions: Current available actions from API
                (may change between levels — e.g. FT09 Level 1 has
                [6] only, later levels add [1,2,3,4,5,6]).
            **extra_context: Additional context passed to rung system

        Returns:
            (action_number, action_data, cognitive_frame)
            action_number: 1-7
            action_data: {x, y} for ACTION6, None otherwise
            cognitive_frame: Observable record of this cycle
        """
        # ═══ Per-level action availability update ═══
        # Games can change available_actions between levels (e.g. FT09
        # Level 1 = [6] only, Level 2+ = [1,2,3,4,5,6] with camera pan).
        # Update our internal state when the API reports a change.
        if available_actions and sorted(available_actions) != sorted(self._available_actions):
            old = self._available_actions
            self._available_actions = list(available_actions)
            if self._verbose:
                print(
                    f"    [ACTIONS-UPDATE] Available actions changed: "
                    f"{old} -> {self._available_actions}"
                )
            # Reset stable regions since new actions may change the viewport
            # (e.g. camera pan actions reveal new parts of the board)
            if any(a in available_actions for a in (1, 2, 3, 4)) and not any(a in old for a in (1, 2, 3, 4)):
                self._stable_region_attempts = 0
                self._stable_mask = None
                self._reference_snapshot = None
                self._reference_panel = None
        cf = CognitiveFrame(
            action_number=self._actions_taken,
            timestamp=time.time(),
            level=self._current_level,
        )
        # W1 narration: the plan-gate counters BEFORE this cycle's plan block
        # runs -- the delta names drove/shadowed/no-steps + the stopping gate.
        _npg0 = dict(getattr(self, "_plan_gate", None) or {})

        # ═══════════════════════════════════════════════════════════════
        # PHASE 1: PERCEIVE
        # ═══════════════════════════════════════════════════════════════
        percept = self._perceive(frame, cf)

        # ═══════════════════════════════════════════════════════════════
        # PHASE 2: THINK
        # ═══════════════════════════════════════════════════════════════
        strategy, certainty = self._think(percept, cf)

        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: MAP (consult, don't update yet — update after action)
        # ═══════════════════════════════════════════════════════════════
        plan_action = self._consult_map(percept, strategy, cf)

        # ═══════════════════════════════════════════════════════════════
        # PHASE 4: ACT (three speeds)
        # ═══════════════════════════════════════════════════════════════
        action_num, action_data = self._act(
            percept, strategy, certainty, plan_action,
            obs, agent_id, agent_role, w_A, w_B, cf, **extra_context,
        )

        # ═══ PHASE 2 (EGO-GOAL): the ONE pre-empt site — a confirmed goal earns the wheel ═══
        # drive() is None unless a reward CONFIRMED a goal AND an established action helps;
        # None changes NOTHING, ever (the wheel rule, record/prereg/PREREG_PHASE2.md).
        try:
            # PHASE 3a: remember the agent's identity for the knowledge fabric
            self._ego_agent_id = str(agent_id) if agent_id else "agent"
            _spine = getattr(self, "_goal_spine", None)
            _cen = getattr(self, "_ego_prev_centroid", None)
            _ego_drive = None
            if _spine is not None and _cen is not None:
                _self_cell = (int(round(_cen[0])), int(round(_cen[1])))
                _ego_drive = _spine.drive(_self_cell)
                if _ego_drive is not None:
                    action_num = int(_ego_drive)
                    if action_num != 6:
                        action_data = None   # a movement action carries no click coordinates
                    print(f"[EGO-GOAL] DRIVE action={action_num} from={_self_cell}")
            # ═══ PHASE 3b2: movement drive first, then click drive (needs no centroid) ═══
            if _spine is not None and _ego_drive is None:
                _click = _spine.drive_click()
                if _click is not None:
                    action_num = 6
                    action_data = {'x': int(_click[0]), 'y': int(_click[1])}
                    print(f"[EGO-GOAL] DRIVE-CLICK at {_click}")
            # ═══ 3d-i (EGO-FRONTIER): a banked fatal opening vetoes the final click ═══
            # Handoff episodes learn the frontier from the observation (max seen);
            # exploration ORDERING only — the remap never claims a goal.
            self._ego_level = max(int(getattr(self, "_ego_level", 0) or 0),
                                  int(getattr(obs, 'levels_completed', 0) or 0))
            _book = getattr(self, "_ego_frontier_book", None)
            _shape = getattr(self, "_ego_frame_shape", None)
            # B1 (BUILD_PROGRAM_2 W1): level 0 admitted — the CK-1b write was
            # un-gated; the read side now matches (same conservative rules).
            if (_book is not None and _shape is not None and _spine is not None
                    and self._ego_level >= 0 and int(action_num) == 6
                    and action_data and action_data.get('x') is not None
                    and action_data.get('y') is not None):
                _fcell = (int(action_data['x']), int(action_data['y']))
                _h = (getattr(self, "_ego_harvest_cache", None)
                      or {}).get(self._ego_level)
                if _h is not None:
                    # 3d-ii: the harvest veto — a fatal or merged-dead cell is
                    # remapped to the nearest UNTRIED cell (one cumulative sweep)
                    if _fcell in _h["fatal"] or _fcell in _h["dead"]:
                        _re = _spine.remap_to_untried(
                            _fcell, _h["tried"], _h["fatal"], _shape)
                        action_data = {'x': int(_re[0]), 'y': int(_re[1])}
                        print(f"[EGO-FRONTIER] avoid {_fcell} -> {_re} "
                              f"(level={self._ego_level} "
                              f"tried={len(_h['tried'])})")
                else:
                    # 3d-i fallback: no harvest loaded yet — the fatal-opening ban
                    _avoid = _book.avoid_set(
                        str(getattr(self, "_game_id", "") or "game"),
                        self._ego_level)
                    if _fcell in _avoid:
                        _re = _spine.remap_avoided(_fcell, _avoid, _shape)
                        action_data = {'x': int(_re[0]), 'y': int(_re[1])}
                        print(f"[EGO-FRONTIER] avoid {_fcell} -> {_re} "
                              f"(level={self._ego_level} banked={len(_avoid)})")
            # ═══ W4c (EGO-PLAN): the wheel rule in code — a plan DRIVES only on atoms
            # salience-grounded by >= 2 TRANSFERRED settlements (self._atom_verified);
            # anything less is shadow-narrated. A fresh box has no atoms: nothing drives. ═══
            try:
                # PREREG_PLAN_WIRE: per-gate pass counters (narration only) — the
                # [PLAN-GATE] line names the first gate whose count collapses to ~0.
                if not hasattr(self, "_plan_gate"):
                    self._plan_gate = {"g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0,
                                       "g6": 0, "g7": 0, "shadow": 0, "drive": 0,
                                       "cycles": 0}
                _pg = self._plan_gate
                _pg["cycles"] += 1
                if _pg["cycles"] % 200 == 0:
                    print(f"[PLAN-GATE] cyc={_pg['cycles']} g1={_pg['g1']} "
                          f"g2={_pg['g2']} g3={_pg['g3']} g4={_pg['g4']} "
                          f"g5={_pg['g5']} g6={_pg['g6']} g7={_pg['g7']} "
                          f"shadow={_pg['shadow']} drive={_pg['drive']} "
                          f"{__import__('engines.egocentric.planner', fromlist=['gate_summary']).gate_summary()} "
                          f"{__import__('engines.egocentric.effects', fromlist=['none_summary']).none_summary()}")
                _gm = getattr(self, "_gamma", None)
                _rbind = getattr(self, "_role_binder", None)
                _refsnap = getattr(self, "_reference_snapshot", None)
                if _gm is not None and _rbind is not None:
                    _pg["g1"] += 1
                    if _refsnap is not None:
                        _pg["g2"] += 1
                        if int(getattr(self, "_ego_level", 0) or 0) >= 1:
                            _pg["g3"] += 1
                # ═══ COMPOSER STAGE 4 (PREREG_COMPOSER_STAGE4_SETTLEMENT.md): a
                # composite drive IN PROGRESS continues here -- the plan rung
                # already fired (g7 counted at the drive); the next part issues
                # against the chain's predicted state or the abort router names
                # world-moved. No search, no new engagement: a plan in execution
                # IS the option. None changes nothing below. ═══
                _w3d = _w3d_continue(self, frame)
                if _w3d is not None:
                    action_num, action_data = _w3d
                elif (_gm is not None and _rbind is not None and _refsnap is not None
                        and int(getattr(self, "_ego_level", 0) or 0) >= 1):
                    # v1 trigger: a REFERENCE-bound class exists AND its region
                    # snapshot is stored; if unavailable, log NOTHING.
                    _ref_bound = any(
                        (_rbind.binding(_kc) or {}).get("slot") == "REFERENCE"
                        for _kc in list(getattr(_rbind, "_evidence", {}) or {}))
                    if _ref_bound:
                        _pg["g4"] += 1
                    _pframe = self._perceiver._to_numpy(frame)
                    if (_ref_bound and _pframe is not None
                            and _pframe.shape == _refsnap.shape):
                        _pg["g5"] += 1
                        _atoms = _gm.fabric.query(
                            "collective", "atoms",
                            where=lambda r: r.get("game") == str(self._game_id))
                        if _atoms:
                            _pg["g6"] += 1
                        # ═══ W2b (PREREG_W2B_PLANNER_SCHEDULING.md): LAST RESORT.
                        # GATE A (cheap routes first) + GATE B (no re-search of an
                        # unchanged world) + the absolute STARVATION GUARD live in
                        # _w2b_engage; skips are narrated at the PLAN point. ═══
                        if _atoms and _w2b_engage(self, _pframe, cf):
                            from engines.egocentric.discrepancy import compute_d
                            from engines.egocentric.planner import plan_to_identity
                            _d = compute_d(_pframe, _refsnap)
                            _plan = plan_to_identity(
                                _pframe, _refsnap, _gm,
                                game=str(self._game_id),
                                level=int(getattr(self, "_ego_level", 0) or 0) + 1,
                                budget=float(max(
                                    0, self._max_actions - self._actions_taken)),
                                cost_per_action=None,  # L1 LIVE: the books price it
                                # W2c: the scheduler's retention store (None = undo)
                                retained=getattr(getattr(self, "_w2b_sched", None),
                                                 "retained", None),
                                # R3/R4: the scheduler's standing book -- RANK
                                # + the evicted filter only (None = undo)
                                standing=_std_book(self))
                            if _plan is not None and "cost_per_action" in _plan:
                                # L1 narration -- BOTH values on the line: the
                                # estimate AND the 1.0 constant it replaced.
                                if _plan.get("cost_missing"):
                                    print("[COST] fallback=1.0")
                                else:
                                    print(f"[COST] "
                                          f"est={_plan['cost_per_action']:.2f} "
                                          f"(was 1.0)")
                            if _plan is not None and _plan.get("steps"):
                                _pg["g7"] += 1
                                _av = getattr(self, "_atom_verified", None) or {}
                                # verified = every step atom carries >= 2 TRANSFERRED
                                # settlements (the salience-grounding bar)
                                _verified = all(int(_av.get(_sid, 0)) >= 2
                                                for _sid in _plan["steps"])
                                _site = None
                                if _verified:
                                    _a0 = _gm.get(_plan["steps"][0])
                                    if _a0 is not None and _a0.get("kind") == "EFFECT":
                                        _ctx0 = np.asarray(_a0["context"])
                                        _ph0, _pw0 = _ctx0.shape
                                        _bh0, _bw0 = _pframe.shape[:2]
                                        for _r0 in range(_bh0 - _ph0 + 1):
                                            for _c0 in range(_bw0 - _pw0 + 1):
                                                if (_pframe[_r0:_r0 + _ph0,
                                                            _c0:_c0 + _pw0]
                                                        == _ctx0).all():
                                                    _site = (_c0 + _pw0 // 2,
                                                             _r0 + _ph0 // 2)
                                                    break
                                            if _site is not None:
                                                break
                                # B3 (BUILD_PROGRAM_2 W1): the frontier veto —
                                # a banked fatal/dead target never drives; the
                                # plan falls back to the shadow narration.
                                from engines.egocentric.frontier import plan_veto
                                _fb3 = getattr(self, "_ego_frontier_book", None)
                                _veto = plan_veto(
                                    _site,
                                    (getattr(self, "_ego_harvest_cache", None)
                                     or {}).get(self._ego_level),
                                    avoid=(_fb3.avoid_set(
                                        str(getattr(self, "_game_id", "")
                                            or "game"),
                                        int(getattr(self, "_ego_level", 0) or 0))
                                        if _fb3 is not None else None))
                                if _verified and _site is not None and not _veto:
                                    action_num = 6
                                    action_data = {'x': int(_site[0]),
                                                   'y': int(_site[1])}
                                    _pg["drive"] += 1
                                    # W2b rider: the abort router's stash --
                                    # plan-time key + the plan's step atoms
                                    self._w2b_driven = {
                                        "key": getattr(self, "_w2b_key", None),
                                        "steps": list(_plan["steps"])}
                                    print(f"[PLAN] DRIVE steps={len(_plan['steps'])} "
                                          f"site={_site} d={_d.get('differing')}")
                                else:
                                    _pg["shadow"] += 1
                                    print(f"[PLAN] shadow steps={len(_plan['steps'])} "
                                          f"feasible={_plan.get('feasible')} "
                                          f"verified={_verified} veto={_veto} "
                                          f"d={_d.get('differing')}")
                            # ═══ COMPOSER STAGE 3 (PROPOSAL_COMPOSER_DESIGN.md
                            # par.3/6.3): the search found NOTHING -- the compose
                            # fallback runs INSIDE the same open W2b gate, with
                            # the SAME WANT (the reference diff, cellwise).
                            # Outcome narrated at the PLAN point. ═══
                            if _plan is None:
                                _w3r = _w3c_compose(self, _pframe,
                                                    _w3c_want_cells(_pframe, _refsnap))
                                # STAGE 4: the candidate DRIVES under the
                                # planner's own gates (verified/site/veto) --
                                # the plan rung firing, g7 counted there.
                                _w3d = _w3d_drive(self, _pframe, _w3r)
                                if _w3d is not None:
                                    action_num, action_data = _w3d
                # ═══ G-C (PREREG_FINAL_GAPS): reference first, then ABDUCED ═══
                # The g4=0 episodes get a target: with NO reference snapshot but
                # a credible abduced goal (>= 2 co-occurrences on the collective
                # "goal_hypotheses" stream), plan toward the predicate. The
                # DRIVE gates are UNCHANGED — verified (2x TRANSFERRED per step
                # atom) + site + frontier veto — and anything less is shadow.
                elif (_gm is not None and _rbind is not None and _refsnap is None
                        and getattr(self, "_ego_fabric", None) is not None):
                    _pframe = self._perceiver._to_numpy(frame)
                    # W2b: the abduced path is the SAME planner engagement --
                    # the same two gates + starvation guard decide it.
                    if _pframe is not None and _w2b_engage(self, _pframe, cf):
                        from engines.egocentric.goal_abduction import (
                            GoalBook, abduced_plan)
                        # LINK3: rebind when the fabric instance changed — the
                        # replay seam may have bound the book to the pre-cycle
                        # SEEDLESS fabric, and this consumer must read the seeds.
                        _gb = getattr(self, "_goal_book", None)
                        if (_gb is None
                                or getattr(_gb, "fabric", None) is not self._ego_fabric):
                            self._goal_book = GoalBook(self._ego_fabric)
                        _fb4 = getattr(self, "_ego_frontier_book", None)
                        _lv4 = int(getattr(self, "_ego_level", 0) or 0)
                        _ap = abduced_plan(
                            _gm, self._goal_book, _pframe,
                            game=str(self._game_id), level=_lv4 + 1,
                            budget=float(max(
                                0, self._max_actions - self._actions_taken)),
                            verified_counts=getattr(self, "_atom_verified",
                                                    None) or {},
                            harvest=(getattr(self, "_ego_harvest_cache", None)
                                     or {}).get(_lv4),
                            avoid=(_fb4.avoid_set(
                                str(getattr(self, "_game_id", "") or "game"),
                                _lv4) if _fb4 is not None else None),
                            # W2c: the scheduler's retention store (None = undo)
                            retained=getattr(getattr(self, "_w2b_sched", None),
                                             "retained", None),
                            # R3/R4: the same standing book, passed through
                            standing=_std_book(self))
                        if _ap is not None:
                            # [NAV] the abduced predicate's site doubles as the
                            # movement stack's target (px x,y; a steer, only)
                            self._nav_goal_px = _ap.get("site")
                            print(f"[GOAL] plan targets {_ap['sig']} "
                                  f"cred={_ap['credibility']}")
                            if (_ap["verified"] and _ap["site"] is not None
                                    and not _ap["veto"]):
                                action_num = 6
                                action_data = {'x': int(_ap["site"][0]),
                                               'y': int(_ap["site"][1])}
                                _pg["drive"] += 1
                                # W2b rider: the abort router's stash
                                self._w2b_driven = {
                                    "key": getattr(self, "_w2b_key", None),
                                    "steps": list(_ap["steps"])}
                                print(f"[PLAN] DRIVE steps={len(_ap['steps'])} "
                                      f"site={_ap['site']} goal={_ap['sig']}")
                            else:
                                _pg["shadow"] += 1
                                print(f"[PLAN] shadow steps={len(_ap['steps'])} "
                                      f"feasible={_ap['feasible']} "
                                      f"verified={_ap['verified']} "
                                      f"veto={_ap['veto']} goal={_ap['sig']}")
                        # COMPOSER STAGE 3: the abduced twin -- same open gate,
                        # same fallback; the WANT is the top abduced predicate
                        # (an empty producer means no WANT: nothing runs).
                        if _ap is None:
                            _t3 = self._goal_book.top(str(self._game_id),
                                                      _lv4 + 1)
                            if _t3 is not None and _t3.get("pred") is not None:
                                _w3r = _w3c_compose(self, _pframe, _t3["pred"])
                                _w3d = _w3d_drive(self, _pframe, _w3r)  # STAGE 4
                                if _w3d is not None:
                                    action_num, action_data = _w3d
            except Exception:
                _swal(self, "PLANNER")
            # ═══ C33 STEP 1 (EGO-BET): every action carries a bet — commit at choice ═══
            # A prediction family is committed on the FINAL action (after every
            # pre-empt) and settled in record_result. NO CONSUMER in this step:
            # nothing in _think/_act/pre-empt reads the book (containment).
            try:
                _fab = getattr(self, "_ego_fabric", None)
                if _fab is not None:
                    if getattr(self, "_bet_book", None) is None:
                        from engines.egocentric.betting import BetBook
                        self._bet_book = BetBook(
                            _fab,
                            agent_id=str(getattr(self, "_ego_agent_id", "") or "agent"),
                            game=str(getattr(self, "_game_id", "") or "game"))
                        self._bet_transitions = {}  # action -> (before, after) at settle
                    _bframe = self._perceiver._to_numpy(frame)
                    if _bframe is not None:
                        _bact = int(action_num)
                        # paste member: the current frame with the taken action's
                        # LAST observed delta applied (the iced family's anchor)
                        _paste = _bframe.copy()
                        _btr = (getattr(self, "_bet_transitions", None) or {}).get(_bact)
                        if _btr is not None:
                            _lb, _la = _btr
                            if (_lb is not None and _la is not None
                                    and _lb.shape == _paste.shape
                                    and _la.shape == _paste.shape):
                                _dmask = (_la != _lb)
                                _paste[_dmask] = _la[_dmask]
                        # transform member: None until harvest v2 lands the
                        # temporal-transform (the tests allow transform=None)
                        self._bet_book.commit(action=_bact, before=_bframe,
                                              paste=_paste, transform=None)
            except Exception:
                _swal(self, "OTHER")
            # ═══ W4c (EGO-BANK): every capable slot bets the FINAL settled action ═══
            # Committed at choice; settled (and routed) in record_result.
            try:
                _pbk = getattr(self, "_predictor_bank", None)
                if _pbk is not None:
                    _cframe = self._perceiver._to_numpy(frame)
                    if _cframe is not None:
                        _slot_states = {"WORKSPACE": _cframe}
                        # BODY: the ego centroid cell when the binder binds the
                        # controllable's class to BODY — falling back to the mere
                        # existence of a last-known centroid (v1 pragmatics).
                        _cen_b = getattr(self, "_ego_last_known_cen", None)
                        if _cen_b is not None:
                            _slot_states["BODY"] = (int(round(_cen_b[0])),
                                                    int(round(_cen_b[1])))
                        _rb_b = getattr(self, "_role_binder", None)
                        if _rb_b is not None and any(
                                (_rb_b.binding(_kb) or {}).get("slot") == "REFERENCE"
                                for _kb in list(getattr(_rb_b, "_evidence", {}) or {})):
                            # v1: the REFERENCE "region" is still the full frame
                            _slot_states["REFERENCE"] = _cframe
                        self._predictor_bank.commit(_slot_states,
                                                    action=int(action_num))
                        # W1 narration: the bet's per-slot stake, consumed by
                        # the bet-side emitter below (O(1))
                        self._narr_slots = sorted(_slot_states)
                        # retain the committed pre-frame: the mint's `before`
                        self._w4c_pre_frame = _cframe.copy()
            except Exception:
                _swal(self, "BANK_SETTLE")
        except Exception:
            _swal(self, "SPINE")

        # ═══ W1 (PREREG_W1_NARRATION.md): BET BEFORE ACT — the bet-side narration
        # (BET, PLAN, ACT) is emitted HERE, after every pre-empt has settled the
        # final action but BEFORE the action executes (the caller executes it
        # after cycle returns). ACT references the BET record's id with an
        # earlier per-step sequence number — falsifier F1's precedence check. ═══
        _narr_bet(self, action_num, cf, _npg0, frame)

        # Store frame and action info for next cycle
        frame_array = self._perceiver._to_numpy(frame)
        self._prev_frame = frame_array
        # Track action repetition (monopoly detection)
        if self._last_action_type == action_num:
            self._consecutive_same_action += 1
        else:
            self._consecutive_same_action = 0
        self._last_action_type = action_num

        self._last_action_info = {
            'type': action_num,
            'x': action_data.get('x') if action_data else None,
            'y': action_data.get('y') if action_data else None,
            'frame_changed': False,  # Will be updated by record_result
            'score_delta': 0.0,
            'level_changed': False,
            'consecutive_no_change': self._consecutive_no_change,
            'consecutive_same_action': self._consecutive_same_action,
        }

        self._actions_taken += 1
        self._current_frame = cf
        self._frames.append(cf)

        # NOTE: Don't print cf.to_log_line() here — frame_changed is not yet known.
        # The caller should print AFTER calling record_result().

        return action_num, action_data, cf

    def _ego_feed(self, frame, action):
        """Observe-only feed for replayed steps: replayed actions TEACH, never SIGNAL.

        Feeds the egocentric observer and accrues the per-action centroid delta
        map on the goal spine (the same sensing path record_result uses), so a
        post-replay handoff arrives with a named body and an established
        move-map instead of frontier amnesia. No seeding and absolutely no
        synthetic reward from replayed steps (the wheel rule); the ONE write is
        the [REPLAY] narration record (F3, PREREG_W1_NARRATION.md) -- playback
        marked as playback, never a fresh decision, never a bet.
        """
        try:
            if getattr(self, "_ego_observer", None) is None:
                from engines.egocentric.observer import EgoObserver
                self._ego_observer = EgoObserver()
            if getattr(self, "_goal_spine", None) is None:
                from engines.egocentric.spine import GoalSpine
                self._goal_spine = GoalSpine()
                self._ego_prev_centroid = None
                self._ego_last_known_cen = None
            info = self._ego_observer.observe(np.asarray(frame), action)
            _cen = info.get('centroid') if isinstance(info, dict) else None
            if _cen is not None:
                self._ego_last_known_cen = _cen
            if _cen is not None and self._ego_prev_centroid is not None:
                _dr = _cen[0] - self._ego_prev_centroid[0]
                _dc = _cen[1] - self._ego_prev_centroid[1]
                self._goal_spine.note_move(
                    str(action), (int(round(_dr)), int(round(_dc))))
            self._ego_prev_centroid = _cen
            # COMPOSER STAGE 4.5: the self-locus EXACT cell (single-cell body)
            # for the compose seam; None -> _w3c_compose states its fallback
            self._ego_self_cell = (info.get("cell")
                                   if isinstance(info, dict) else None)
        except Exception:
            self._ego_feed_errors = getattr(self, "_ego_feed_errors", 0) + 1
            _swal(self, "OBSERVER")
        # ═══ W1/F3 (PREREG_W1_NARRATION.md): a replayed/observe-only step
        # narrates as [REPLAY] — side="replay", range=REPLAY, no bet, no
        # reference. Playback is never laundered into reasoning. ═══
        try:
            _fab = getattr(self, "_ego_fabric", None)
            _gid = str(getattr(self, "_game_id", "") or "")
            if _fab is None and _gid:
                # the _goal_bank REACHABILITY seam: replay runs BEFORE the
                # cycle's lazy fabric init on a loop built fresh this episode.
                # Gated on a STARTED game (_game_id set): a bare loop with no
                # game has nothing to narrate and creates nothing on disk.
                from engines.egocentric.fabric import KnowledgeFabric
                _fab = KnowledgeFabric(
                    "ego_fabric",
                    agent_id=str(getattr(self, "_ego_agent_id", "") or "agent"),
                    kin_key="v4")
                self._ego_fabric = _fab
            if _fab is not None:
                _nsp = getattr(self, "_narration", None)
                if _nsp is None or _nsp.fabric is not _fab:
                    from engines.egocentric.narration import NarrationSpine
                    _nsp = NarrationSpine(_fab, game=_gid or "game")
                    self._narration = _nsp
                # W1 FALSIFIER ARMS: a replay-first game still labels itself
                _narm = getattr(self, "_narr_arm", None)
                if _narm is not None:
                    _nsp.narrate_arm(
                        _narm,
                        step=int(getattr(self, "_actions_taken", 0) or 0))
                _nsp.replay(int(action),
                            step=int(getattr(self, "_actions_taken", 0) or 0))
        except Exception:
            _swal(self, "OTHER")

    def bank_replay_levelup(self, game, level, pre, post) -> int:
        """G-C REPLAY SEAM (LINK3_AUDIT addendum): the second — and until now
        missing — route into the abduction bank.

        The cognitive cycle banks a level-up at `_goal_abd`; a level-up reached
        by PREFIX REPLAY never enters that cycle, so link 3 only ever saw the
        transitions the agent achieved WITHOUT goals. This is the sibling of
        `_ego_feed` and carries the same rule: REPLAYED STEPS TEACH, NEVER
        SIGNAL. What crosses here is an OBSERVATION — the pre/post frames the
        environment produced at the boundary — and never the replayed prefix
        itself, so the membrane law (no replay material in a knowledge stream)
        is untouched and no synthetic credit is minted.

        `level` is the NEW levels_completed, matching the cycle's A3-2 PLAYING
        level convention (`_ego_level` post-increment). Returns the number of
        hypotheses banked; containment: 0, never raises into the replay path."""
        return _goal_bank(self, game, level, pre, post)

    def record_result(
        self,
        post_frame: Any,
        frame_changed: bool,
        score_delta: float,
        level_changed: bool,
        new_level: int = 0,
        new_score: float = 0.0,
    ):
        """
        Record the result of the last action.

        This is where MAP gets updated -- we now know what our action DID.
        This closes the loop: the updated map will inform the next PERCEIVE.

        Enhanced with Gap 1-5 cognitive machinery:
        - Gap 1: Frame history for stable region detection
        - Gap 4: Rich action outcome (goal-progress tracking)
        - Gap 4B: Feed goal progress into CausalMap
        - Gap 5: HUD state change detection
        """
        cf = self._current_frame
        if cf is None:
            return

        # Update cognitive frame with result
        cf.frame_changed = frame_changed
        cf.score_delta = score_delta
        cf.level_changed = level_changed

        if frame_changed:
            self._consecutive_no_change = 0
        else:
            self._consecutive_no_change += 1

        # ═══ GAP 1: Update frame history for stable region detection ═══
        post_array = self._perceiver._to_numpy(post_frame)
        if post_array is not None:
            self._frame_history.append(post_array.copy())
            # Keep last 15 frames (enough to detect stable vs changing regions)
            if len(self._frame_history) > 15:
                self._frame_history = self._frame_history[-15:]

            # Compute stable regions: first try at 5 frames, retry at 10 if first attempt
            # failed to find a useful split (e.g. intro animation, camera panning)
            min_frames = 5 if self._stable_region_attempts == 0 else 10
            if (len(self._frame_history) >= min_frames
                    and self._stable_mask is None
                    and self._stable_region_attempts < 2):
                self._compute_stable_regions()

        # ═══ PHASE 1 (EGO): read-only egocentric observation — feeds NOTHING ═══
        # The observer senses (segment/track/contingency) but no decision code reads it.
        try:
            if getattr(self, "_ego_observer", None) is None:
                from engines.egocentric.observer import EgoObserver
                self._ego_observer = EgoObserver()
            _ego_action = (getattr(self, "_last_action_info", None) or {}).get('type', 0)
            info = self._ego_observer.observe(post_array, _ego_action)
            if self._ego_observer.calls % 10 == 0:
                print(f"[EGO] colour={info.get('colour')} objects={info.get('objects')}")
        except Exception:
            _swal(self, "OBSERVER")

        # ═══ PHASE 2 (EGO-GOAL): the goal spine — confirmed reward earns the wheel ═══
        # Accrue the per-action centroid delta map (the means), propose candidate cells
        # (cue-proposes), and on a level-up credit the controllable's cell (reward-disposes).
        # Only spine.drive() — the ONE pre-empt site in cycle() — ever reads this back.
        try:
            if getattr(self, "_goal_spine", None) is None:
                from engines.egocentric.spine import GoalSpine
                self._goal_spine = GoalSpine()
                self._ego_prev_centroid = None
                self._ego_last_known_cen = None  # AMENDMENT 3b3: survives None steps
            # ═══ PHASE 3a: the knowledge fabric — lazy init + SEED once per game ═══
            # Relative root (cwd-scoped: hermetic). Priors feed the spine at an
            # INHERITED price (credibility>=1 opens the gate; below, bias only).
            # Init-once flag: replay-fed episodes still need fabric + seeding.
            if not getattr(self, "_ego_fabric_inited", False):
                try:
                    from engines.egocentric.fabric import KnowledgeFabric
                    _sd = [_s.strip() for _s in os.environ.get(
                        "OURO_FABRIC_SEEDS", "").split(";")
                        if _s.strip() and os.path.isdir(_s.strip())]
                    self._ego_fabric = KnowledgeFabric(
                        "ego_fabric", seeds=_sd,
                        agent_id=str(getattr(self, "_ego_agent_id", "") or "agent"),
                        kin_key="v4")
                    self._ego_seeded = {}          # seeded cell -> prior idea id
                    self._ego_seeded_clicks = {}   # PHASE 3b2: seeded CLICK_AT cell -> prior id
                    self._ego_self_clicks = set()  # PHASE 3b2: self-confirmed CLICK_AT cells
                    _gkey = str(getattr(self, "_game_id", "") or "game")
                    _bonus = self._goal_spine.manager.confirm_bonus
                    _plv = int(getattr(self, "_ego_level", 0) or 0) + 1
                    for _p in self._ego_fabric.priors(_gkey, level=_plv)[:3]:
                        if _p.get("pariah"):
                            continue
                        _pi = _p.get("idea") or {}
                        _pk = _pi.get("kind")
                        if _pk not in ("BE_AT", "CLICK_AT"):
                            continue
                        _pc = _pi.get("cell") or []
                        if len(_pc) != 2:
                            continue
                        _pcell = (int(_pc[0]), int(_pc[1]))
                        _price = _bonus if _p.get("credibility", 0) >= 1 else _bonus * 0.6
                        if _pk == "CLICK_AT":
                            self._goal_spine.seed_confirmed_click(_pcell, price=_price)
                            self._ego_seeded_clicks[_pcell] = _p["id"]
                        else:
                            self._goal_spine.seed_confirmed(_pcell, price=_price)
                            self._ego_seeded[_pcell] = _p["id"]
                    self._ego_seed_level = _plv
                    if self._ego_seeded or self._ego_seeded_clicks:
                        print(f"[EGO-SEED] level={_plv} n="
                              f"{len(self._ego_seeded) + len(self._ego_seeded_clicks)}")
                except Exception:
                    self._ego_fabric = None
                    self._ego_seeded = {}
                    self._ego_seeded_clicks = {}
                    self._ego_self_clicks = set()
                self._ego_fabric_inited = True  # once per game, success or fail
            # hoisted above credit: mints carry the reward's level
            self._ego_level = (int(getattr(self, "_ego_level", 0) or 0)
                               + (1 if level_changed else 0))
            _cen = info.get('centroid') if isinstance(info, dict) else None
            if _cen is not None:
                # AMENDMENT 3b3: retain the last non-None centroid — the level-up
                # frame breaks the pick; attribution needs the pre-transition cell.
                self._ego_last_known_cen = _cen
            if _cen is not None and self._ego_prev_centroid is not None:
                _delta = (int(round(_cen[0] - self._ego_prev_centroid[0])),
                          int(round(_cen[1] - self._ego_prev_centroid[1])))
                self._goal_spine.note_move(str(_ego_action), _delta)
            self._ego_prev_centroid = _cen
            # Candidates: non-self objects, smallest (marker-like) first, cap 5
            _colour = info.get('colour') if isinstance(info, dict) else None
            _objs = list(getattr(self._ego_observer, "_prev_objs", None) or [])
            _objs = [o for o in _objs if _colour is None or _colour not in o.colours]
            _objs.sort(key=lambda o: o.size)
            self._goal_spine.propose(
                (int(round(o.centroid[0])), int(round(o.centroid[1]))) for o in _objs[:5])
            _lai = getattr(self, "_last_action_info", None) or {}
            _ax, _ay = _lai.get('x'), _lai.get('y')
            if level_changed and _cen is not None:
                _cell = (int(round(_cen[0])), int(round(_cen[1])))
                self._goal_spine.credit(_cell)
                print(f"[EGO-GOAL] CONFIRM at {_cell} (level-up credits the market's winner)")
                # ═══ PHASE 3a: MINT on credit — signal only (the wheel rule for memory) ═══
                try:
                    _fab = getattr(self, "_ego_fabric", None)
                    if _fab is not None:
                        _gkey = str(getattr(self, "_game_id", "") or "game")
                        _mi = {"kind": "BE_AT", "cell": [_cell[0], _cell[1]]}
                        _sig = {"type": "level_up"}
                        _id_p = _fab.mint(_mi, game=_gkey, signal=_sig, scope="personal",
                                          level=self._ego_level)
                        _id_c = _fab.mint(_mi, game=_gkey, signal=_sig, scope="collective",
                                          level=self._ego_level)
                        print(f"[EGO-MINT] {_id_p} {_id_c}")
                        # a level-up at a SEEDED cell corroborates the inherited idea
                        _pid = (getattr(self, "_ego_seeded", None) or {}).get(_cell)
                        if _pid is not None:
                            _fab.echo(_pid, by=_fab.agent_id)
                except Exception:
                    pass
            # ═══ AMENDMENT 3b3: NON-DROPPABLE — fall back to the LAST-KNOWN centroid ═══
            # (the body's cell BEFORE the transition — the correct attribution anyway)
            elif level_changed and getattr(self, "_ego_last_known_cen", None) is not None:
                _lkc = self._ego_last_known_cen
                _cell = (int(round(_lkc[0])), int(round(_lkc[1])))
                self._goal_spine.credit(_cell)
                print(f"[EGO-GOAL] CONFIRM at {_cell} (level-up credits the last-known cell)")
                try:
                    _fab = getattr(self, "_ego_fabric", None)
                    if _fab is not None:
                        _gkey = str(getattr(self, "_game_id", "") or "game")
                        _mi = {"kind": "BE_AT", "cell": [_cell[0], _cell[1]]}
                        _sig = {"type": "level_up"}
                        _id_p = _fab.mint(_mi, game=_gkey, signal=_sig, scope="personal",
                                          level=self._ego_level)
                        _id_c = _fab.mint(_mi, game=_gkey, signal=_sig, scope="collective",
                                          level=self._ego_level)
                        print(f"[EGO-MINT] {_id_p} {_id_c}")
                        # a level-up at a SEEDED cell corroborates the inherited idea
                        _pid = (getattr(self, "_ego_seeded", None) or {}).get(_cell)
                        if _pid is not None:
                            _fab.echo(_pid, by=_fab.agent_id)
                except Exception:
                    pass
            # ═══ AMENDMENT 3b3: last resort — a bare LEVEL mint, no spine credit ═══
            # (only when NO cell is attributable at all: no centroid, no last-known,
            #  no click coords — a real level-up must never leave zero trace)
            elif level_changed and (_ax is None or _ay is None):
                try:
                    _fab = getattr(self, "_ego_fabric", None)
                    if _fab is not None:
                        _gkey = str(getattr(self, "_game_id", "") or "game")
                        _mi = {"kind": "LEVEL", "action": int(_lai.get('type') or 0)}
                        _sig = {"type": "level_up"}
                        _id_p = _fab.mint(_mi, game=_gkey, signal=_sig, scope="personal",
                                          level=self._ego_level)
                        _id_c = _fab.mint(_mi, game=_gkey, signal=_sig, scope="collective",
                                          level=self._ego_level)
                        print(f"[EGO-MINT] {_id_p} {_id_c}")
                except Exception:
                    pass
            # ═══ PHASE 3b2: credit the ACTED-ON cell — a click needs no centroid ═══
            if level_changed and _ax is not None and _ay is not None:
                _ccell = (int(_ax), int(_ay))
                self._goal_spine.credit_click(_ccell)
                getattr(self, "_ego_self_clicks", set()).add(_ccell)
                print(f"[EGO-GOAL] CONFIRM-CLICK at {_ccell} (level-up credits the acted-on cell)")
                # MINT on click-credit — same fabric guards as the BE_AT path
                try:
                    _fab = getattr(self, "_ego_fabric", None)
                    if _fab is not None:
                        _gkey = str(getattr(self, "_game_id", "") or "game")
                        _mi = {"kind": "CLICK_AT", "cell": [_ccell[0], _ccell[1]]}
                        _sig = {"type": "level_up"}
                        _id_p = _fab.mint(_mi, game=_gkey, signal=_sig, scope="personal",
                                          level=self._ego_level)
                        _id_c = _fab.mint(_mi, game=_gkey, signal=_sig, scope="collective",
                                          level=self._ego_level)
                        print(f"[EGO-MINT] {_id_p} {_id_c}")
                        # a level-up at a SEEDED click cell corroborates the inherited idea
                        _pid = (getattr(self, "_ego_seeded_clicks", None) or {}).get(_ccell)
                        if _pid is not None:
                            _fab.echo(_pid, by=_fab.agent_id)
                except Exception:
                    pass
            # ═══ W4c (EGO-WIRE): every producer's consumer, named in code ═══
            # Lazy init alongside the fabric: binder/bank/router/mint/gamma/affect/mute.
            try:
                _wfab = getattr(self, "_ego_fabric", None)
                if _wfab is not None and getattr(self, "_gamma", None) is None:
                    from engines.egocentric.binder import RoleBinder
                    from engines.egocentric.bank import PredictorBank
                    from engines.egocentric.router import ResidualRouter
                    from engines.egocentric.mint import MDLMint
                    from engines.egocentric.affect import AffectGains
                    from engines.egocentric.verdicts import MuteHandler
                    from engines.egocentric.effects import Gamma
                    self._gamma = Gamma(_wfab)
                    self._role_binder = RoleBinder()
                    self._predictor_bank = PredictorBank(
                        gamma=self._gamma,
                        game=str(getattr(self, "_game_id", "") or "game"),
                        level=int(getattr(self, "_ego_level", 0) or 0) + 1)
                    self._residual_router = ResidualRouter()
                    self._mdl_mint = MDLMint(self._gamma)
                    self._affect = AffectGains(_wfab)
                    self._mute = MuteHandler()
                    self._atom_verified = _hyd_ver(self)  # A3-1 book-derived
                    # R1: per-episode mint/bank socket counters
                    self._w4c_counters = {"mint_tried": 0, "mint_passed": 0,
                                          "bank_tried": 0, "bank_passed": 0,
                                          "neg_tried": 0, "neg_passed": 0}
                    self._w4c_calls = 0
                    self._w4c_cls_prev = None
                    _seed_imp(self)
            except Exception:
                _swal(self, "FABRIC")
            # W4c-1: FEED THE BINDER — per-step, per-class invariance evidence.
            try:
                _rb = getattr(self, "_role_binder", None)
                if _rb is not None:
                    if level_changed:
                        _rb.on_level_change()  # the maze redraws; bindings re-earn
                        self._w4c_cls_prev = None
                    _w_lai = getattr(self, "_last_action_info", None) or {}
                    _w_act = int(_w_lai.get('type', 0) or 0)
                    _w_x, _w_y = _w_lai.get('x'), _w_lai.get('y')
                    _w_click = (_w_act == 6 and _w_x is not None
                                and _w_y is not None)
                    # CK-2a: the efference copy — cells MY action should change
                    _pmask = (_rb.predicted_change_mask(
                        getattr(self, "_w4c_pre_frame", None), _w_act,
                        (int(_w_y), int(_w_x)),
                        bank=getattr(self, "_predictor_bank", None))
                        if _w_click else set())
                    _now = {}
                    for _wo in (getattr(self._ego_observer, "_prev_objs", None)
                                or []):
                        _now.setdefault(min(_wo.colours), set()).update(_wo.cells)
                    _prevmap = getattr(self, "_w4c_cls_prev", None)
                    if _prevmap is not None and not level_changed:
                        for _wc, _wcells in _now.items():
                            _pcells = _prevmap.get(_wc)
                            if not _pcells or not _wcells:
                                continue
                            _cn = (sum(p[0] for p in _wcells) / len(_wcells),
                                   sum(p[1] for p in _wcells) / len(_wcells))
                            _cp = (sum(p[0] for p in _pcells) / len(_pcells),
                                   sum(p[1] for p in _pcells) / len(_pcells))
                            _moved = (int(round(_cn[0])) != int(round(_cp[0]))
                                      or int(round(_cn[1])) != int(round(_cp[1])))
                            _mut = _wcells != _pcells
                            _neg_feed(self, _mut)  # B6: negative evidence
                            # CK-2a: subtract the efference copy — self-caused
                            # iff the change intersects the predicted mask
                            self._role_binder.observe_attributed(
                                _wc, _w_act, _moved,
                                bool(_w_click and _mut),
                                _pcells ^ _wcells, _pmask, 0)
                    self._w4c_cls_prev = _now
            except Exception:
                _swal(self, "BINDER_FEED")
            # W4c-2: THE BANK settles at result; EVERY settlement routes.
            try:
                _pb = getattr(self, "_predictor_bank", None)
                _rt = getattr(self, "_residual_router", None)
                if _pb is not None and _rt is not None and post_array is not None:
                    _pb.game = str(getattr(self, "_game_id", "") or "game")
                    _pb.level = int(getattr(self, "_ego_level", 0) or 0) + 1
                    _obs_states = {"WORKSPACE": post_array,
                                   "REFERENCE": post_array}
                    _bcen = (getattr(self, "_ego_prev_centroid", None)
                             or getattr(self, "_ego_last_known_cen", None))
                    if _bcen is not None:
                        _obs_states["BODY"] = (int(round(_bcen[0])),
                                               int(round(_bcen[1])))
                    _wexec = int((getattr(self, "_last_action_info", None)
                                  or {}).get('type', 0) or 0)
                    _wpre = getattr(self, "_w4c_pre_frame", None)
                    out = self._predictor_bank.settle(_obs_states)
                    # R1: bank socket counters — a non-REFERENCE bet is a
                    # learned family (REFERENCE's identity bet is free)
                    _wct = getattr(self, "_w4c_counters", None)
                    if _wct is not None:
                        _wct["bank_tried"] += 1
                        if any(_sv.get("bet") and _sk != "REFERENCE"
                               for _sk, _sv in out.items()):
                            _wct["bank_passed"] += 1
                    # F4 n=1 linkage: this step's known-atom bet (id, bin)
                    self._w4c_step_atom = (None, None)
                    for _slot, _stl in out.items():
                        _bin = self._residual_router.route(
                            _slot, _stl,
                            expected_bin=_narr_expected_bin(self, _slot))
                        # W1 FALSIFIER WIRE 1 (arm C only; _narr_expected_bin
                        # returns None on arm W and the router's consumption
                        # branch is never entered): an in-band tie resolved by
                        # the prior BET's stated expectation cites that BET
                        # record's id on this step's ROUTE narration.
                        if getattr(_rt, "last_consumed", False):
                            self._narr_route_consumed = (getattr(
                                getattr(self, "_narration", None),
                                "last_bet", None) or {}).get("id")
                        # W1 narration: per-slot outcome (bet/residual/bin) for
                        # the close; lazy init AFTER the .route anchor (the
                        # window law), cleared per step by bet/close.
                        if getattr(self, "_narr_settle", None) is None:
                            self._narr_settle = {}
                        self._narr_settle[_slot] = {
                            "bet": bool(_stl.get("bet")),
                            "residual": float(_stl.get("residual", 0.0) or 0.0),
                            "bin": _bin}
                        if (_slot == "WORKSPACE"
                                and _stl.get("from_known_atom")
                                and _stl.get("atom_key") is not None):
                            self._w4c_step_atom = (_stl.get("atom_key"), _bin)
                        # the wheel rule's ledger: a TRANSFERRED WORKSPACE
                        # settlement from a known atom verifies WHICH atom bet
                        # (re-scan gamma: whose apply reproduces the post frame)
                        if (_bin == "TRANSFERRED" and _slot == "WORKSPACE"
                                and _stl.get("from_known_atom")
                                and _wpre is not None):
                            from engines.egocentric.effects import (
                                Gamma as _Gm, apply_effect as _apf)
                            for _rec2 in self._gamma.fabric.query(
                                    "collective", _Gm.TOPIC):
                                _at = _rec2.get("atom") or {}
                                if (_at.get("kind") != "EFFECT"
                                        or str(_rec2.get("game")) != _pb.game
                                        or int(_rec2.get("level", -1)) != _pb.level
                                        or int(_at.get("action", -1)) != _wexec):
                                    continue
                                _pr2 = _apf(_at, np.asarray(_wpre))
                                if (_pr2 is not None
                                        and _pr2.shape == post_array.shape
                                        and bool((_pr2 == post_array).all())):
                                    _aid2 = _rec2.get("id")
                                    self._atom_verified[_aid2] = (
                                        self._atom_verified.get(_aid2, 0) + 1)
                                    break
            except Exception:
                _swal(self, "BANK_SETTLE")
            _goal_abd(self, level_changed, post_array)  # G-C: bank the level-up delta
            # W2b RIDER: route a driven plan's abort (world-moved vs plan-wrong,
            # each narrated with its discriminator -- F4); a level change clears
            # the retained planner state key (binder.on_level_change's pattern).
            # One-line call site placed AFTER the .credit/.route anchors by the
            # window law; containment inside: never raises.
            # COMPOSER STAGE 4.5: the self-locus EXACT cell (single-cell body)
            # for the compose seam; None -> _w3c_compose states its fallback.
            # Stamped BELOW the .route anchor (the window law; the STAGE 4.5
            # structural repair moved it out of the .credit window): the same
            # `info` PHASE 1 bound, inside the same PHASE 2 try, and the ONLY
            # reader is _w3c_compose in cycle -- the value is identical.
            self._ego_self_cell = (info.get("cell")
                                   if isinstance(info, dict) else None)
            # COMPOSER STAGE 4: a driven composite's step settles or routes
            # FIRST (it consumes its own stash; the planner's is untouched).
            _w3d_settle(self, post_array, level_changed)
            _w2b_abort(self, frame_changed, level_changed)
            # W4c-3: THE MINT — bar-gated by affect (picky when desperate).
            try:
                _rt = getattr(self, "_residual_router", None)
                _aff = getattr(self, "_affect", None)
                if (getattr(self, "_mdl_mint", None) is not None
                        and _rt is not None and _aff is not None):
                    _bar = float(_aff.gains()["mint_bar"])
                    # R1: mint socket counters ride every offer below (readout
                    # only — no verdict, bar, or support is touched)
                    _wct = getattr(self, "_w4c_counters", None)
                    _wpre = getattr(self, "_w4c_pre_frame", None)
                    _wexec = int((getattr(self, "_last_action_info", None)
                                  or {}).get('type', 0) or 0)
                    # COMPOSER STAGE 2 (PREREG_COMPOSER_STAGE2_ENABLES.md):
                    # the acting cell, (row, col) = (y, x) — the click
                    # coordinates already in _last_action_info — captured so
                    # the mint can stamp act_offset at write time. None
                    # unless the executed action was a click with recorded
                    # coordinates (movement actions carry none).
                    _wlai0 = getattr(self, "_last_action_info", None) or {}
                    _wact = ((int(_wlai0['y']), int(_wlai0['x']))
                             if (_wexec == 6
                                 and _wlai0.get('x') is not None
                                 and _wlai0.get('y') is not None) else None)
                    # MINT BOOTSTRAP: with an empty Gamma, BROKEN-mechanism can
                    # never fire (it needs a KNOWN atom to be wrong), so every
                    # residual routes NOVEL and the mint starves. NOVEL WORKSPACE
                    # evidence is the mint's first meal, offered under the SAME
                    # bar; the mint's guards (SUPPORT x NOVELTY x MDL) filter.
                    # Peek only -- W4c-4 still persists these to the fabric.
                    for _wit in list(_rt.import_queue):
                        if (_wit.get("slot") == "WORKSPACE"
                                and float(_wit.get("residual", 0.0)) >= _bar
                                and _wpre is not None
                                and post_array is not None
                                and not _narr_mint_skip(
                                    self, _wpre, post_array, _wexec,
                                    "bootstrap")):
                            _wv = self._mdl_mint.consider(
                                before=_wpre, action=_wexec, after=post_array,
                                game=str(getattr(self, "_game_id", "") or "game"),
                                level=int(getattr(self, "_ego_level", 0) or 0) + 1,
                                act=_wact)
                            if _wct is not None:
                                _wct["mint_tried"] += 1
                                _wct["mint_passed"] += (
                                    1 if _wv.get("verdict") == "mint" else 0)
                            self._narr_mint = dict(_wv)  # W1 narration
                            _narr_mint_mark(self, _wpre, post_array, _wexec,
                                            "bootstrap")
                            print(f"[MINT] verdict={_wv.get('verdict')} "
                                  f"id={_wv.get('id')} (NOVEL bootstrap)")
                    while _rt.mint_queue:
                        _wit = _rt.mint_queue.pop(0)
                        if (float(_wit.get("residual", 0.0)) >= _bar
                                and _wpre is not None
                                and post_array is not None
                                and not _narr_mint_skip(
                                    self, _wpre, post_array, _wexec,
                                    "queue")):
                            _wv = self._mdl_mint.consider(
                                before=_wpre, action=_wexec, after=post_array,
                                game=str(getattr(self, "_game_id", "") or "game"),
                                level=int(getattr(self, "_ego_level", 0) or 0) + 1,
                                act=_wact)
                            if _wct is not None:
                                _wct["mint_tried"] += 1
                                _wct["mint_passed"] += (
                                    1 if _wv.get("verdict") == "mint" else 0)
                            self._narr_mint = dict(_wv)  # W1 narration
                            _narr_mint_mark(self, _wpre, post_array, _wexec,
                                            "queue")
                            print(f"[MINT] verdict={_wv.get('verdict')} "
                                  f"id={_wv.get('id')}")
                        # below the bar: dropped — desperation makes the
                        # mint pickier, never looser
                    # PRIMAL path: a click that CHANGED the frame is offered
                    # to the mint DIRECTLY — no routing, no bet (WORKSPACE
                    # cannot bet with an empty Gamma, so the starvation moved
                    # one link up). NOVELTY dedups repeats, MDL filters junk;
                    # the SAME bar gates, with changed-cell count as residual.
                    _wlai = getattr(self, "_last_action_info", None) or {}
                    if (frame_changed and _wlai.get('x') is not None
                            and _wlai.get('y') is not None
                            and _wpre is not None and post_array is not None):
                        _wpa = np.asarray(_wpre)
                        _wres = (float((_wpa != post_array).sum())
                                 if _wpa.shape == post_array.shape
                                 else float(post_array.size))
                        if _wres >= _bar and not _narr_mint_skip(
                                self, _wpre, post_array, _wexec, "primal"):
                            _wv = self._mdl_mint.consider(
                                before=_wpre, action=_wexec, after=post_array,
                                game=str(getattr(self, "_game_id", "") or "game"),
                                level=int(getattr(self, "_ego_level", 0) or 0) + 1,
                                act=_wact)
                            if _wct is not None:
                                _wct["mint_tried"] += 1
                                _wct["mint_passed"] += (
                                    1 if _wv.get("verdict") == "mint" else 0)
                            self._narr_mint = dict(_wv)  # W1 narration
                            _narr_mint_mark(self, _wpre, post_array, _wexec,
                                            "primal")
                            print(f"[MINT] verdict={_wv.get('verdict')} "
                                  f"id={_wv.get('id')} (primal)")
            except Exception:
                _swal(self, "MINT_DRAIN")
            # W4c-4: NOVEL items persist — the endogenous agenda stays visible.
            # Fig 9: a residual is CHARACTERIZED, not named — with before/after
            # in hand the record also carries sigma (the enqueue-time
            # description, the priority condition) + bounded bbox patches
            # (consumer.characterize; oversized regions keep sigma only).
            try:
                _rt = getattr(self, "_residual_router", None)
                _wfab = getattr(self, "_ego_fabric", None)
                if _rt is not None and _wfab is not None:
                    from engines.egocentric import consumer as _con9
                    _wpre = getattr(self, "_w4c_pre_frame", None)
                    while _rt.import_queue:
                        _wit = _rt.import_queue.pop(0)
                        # A3-2 CONVENTION (PLAYING level): import_queue records
                        # carry game (full-id grain) + the level being played.
                        _wrec = {"slot": _wit.get("slot"),
                                 "residual": float(_wit.get("residual", 0.0)),
                                 "game": str(getattr(self, "_game_id", "")
                                             or "game"),
                                 "level": int(getattr(self, "_ego_level", 0)
                                              or 0) + 1}
                        if _wpre is not None and post_array is not None:
                            _wrec.update(_con9.characterize(
                                _wpre, post_array, slot=_wrec["slot"],
                                residual=_wrec["residual"]))
                        _wfab.append("collective", "import_queue", _wrec)
            except Exception:
                _swal(self, "MINT_DRAIN")
            # ── THE REBINDING BIN GETS A DESTINATION (record/prereg/PREREG_REFIT_DESTINATION.md,
            # Seat 3 ruling 2026-08-19) ──────────────────────────────────────────
            # ROUTE has four bins. Three drained somewhere: NOVEL -> import_queue
            # (above), BROKEN·mechanism -> mint_queue -> the mint, TRANSFERRED ->
            # settlements. BROKEN·rebinding appended to router.refit_queue, an
            # in-memory list referenced NOWHERE ELSE in the tree -- so the one bin
            # that says "repair this, do not mint" died with the process.
            #
            # SCOPE: THE DESTINATION ONLY. `binding_stale` is still set by nothing
            # in production, so this drain is a NO-OP today and the bin still
            # cannot fire. That is the ruled order: a diagnosis that dies with the
            # process is not a diagnosis, so the destination lands before the
            # switch. Its own try/except so a refit failure cannot kill the
            # import drain above.
            try:
                _rt2 = getattr(self, "_residual_router", None)
                _rfab = getattr(self, "_ego_fabric", None)
                if _rt2 is not None and _rfab is not None:
                    while _rt2.refit_queue:
                        _rit = _rt2.refit_queue.pop(0)
                        # Same record shape and same A3-2 PLAYING-level convention
                        # as the import_queue drain -- one pattern, not two.
                        _rfab.append("collective", "refit_queue", {
                            "slot": _rit.get("slot"),
                            "residual": float(_rit.get("residual", 0.0)),
                            "game": str(getattr(self, "_game_id", "") or "game"),
                            "level": int(getattr(self, "_ego_level", 0) or 0) + 1,
                        })
            except Exception:
                # MINT_DRAIN, not a new code: the guarded-block enum is
                # PREREGISTERED and takes no additions on the fly (the swallow
                # gate says so, and it caught me adding one). This drain is the
                # same family as the import_queue drain above -- a router queue
                # emptied to the fabric -- so it shares its block.
                _swal(self, "MINT_DRAIN")
            # W4c-6: AFFECT NARRATES — no channel moves without the state emitted.
            # B5 (BUILD_PROGRAM_2 W1): the SEED-BIAS consumption site — the
            # APPLIED bias (seed_gain: starvation+swallow-widened, bounded,
            # multiplicative) feeds the explore rotation and rides the line.
            try:
                if getattr(self, "_affect", None) is not None:
                    self._w4c_calls = int(getattr(self, "_w4c_calls", 0)) + 1
                    _sg = self._affect.seed_gain(
                        str(getattr(self, "_game_id", "") or "game"))
                    self._ego_explore_widen = float(_sg["boost"])
                    if self._w4c_calls % 25 == 0:
                        print("[AFFECT] " + self._affect.narrate()
                              + " seed_applied=%.4f widen=%.2f"
                              % (_sg["applied"], _sg["boost"]))
            except Exception:
                _swal(self, "AFFECT")
            # ═══ PHASE 3a: FALSIFY write-back — a seeded cell reached WITHOUT reward ═══
            _seeded = getattr(self, "_ego_seeded", None)
            if _seeded and not level_changed and _cen is not None:
                _cur = (int(round(_cen[0])), int(round(_cen[1])))
                _pid = _seeded.get(_cur)
                if _pid is not None:
                    try:
                        _fab = getattr(self, "_ego_fabric", None)
                        if _fab is not None:
                            _fab.falsify(_pid, by=_fab.agent_id)
                        self._goal_spine.demote_inherited(_cur)
                        del _seeded[_cur]
                        print("[EGO-GOAL] falsified inherited")
                    except Exception:
                        pass
            # ═══ PHASE 3b2: click falsify write-back — clicked WITHOUT reward closes it ═══
            if not level_changed and _ax is not None and _ay is not None:
                _ccell = (int(_ax), int(_ay))
                _sclk = getattr(self, "_ego_seeded_clicks", None)
                if _sclk and _ccell in _sclk:
                    try:
                        _fab = getattr(self, "_ego_fabric", None)
                        if _fab is not None:
                            _fab.falsify(_sclk[_ccell], by=_fab.agent_id)
                        self._goal_spine.demote_inherited_click(_ccell)
                        del _sclk[_ccell]
                        print("[EGO-GOAL] falsified inherited click")
                    except Exception:
                        pass
                elif _ccell in (getattr(self, "_ego_self_clicks", None) or set()):
                    # a SELF-confirmed click that failed on re-click: demote, don't falsify
                    self._goal_spine.demote_inherited_click(_ccell)
                    self._ego_self_clicks.discard(_ccell)
                    print("[EGO-GOAL] demoted self-confirmed click (no reward)")
            # ═══ W4c-7 (EGO-MUTE): a seeded goal demoted by the falsify path is MUTE —
            # the ground said nothing; quarantine the prior and answer with the
            # empowerment probe (least-observed untried cell from the harvest). ═══
            try:
                if getattr(self, "_mute", None) is not None:
                    _cur_ids = (
                        set((getattr(self, "_ego_seeded", None) or {}).values())
                        | set((getattr(self, "_ego_seeded_clicks", None)
                               or {}).values()))
                    _prev_ids = getattr(self, "_w4c_seed_ids", None)
                    _slv_now = getattr(self, "_ego_seed_level", None)
                    if (_prev_ids is not None and not level_changed
                            and _slv_now == getattr(self, "_w4c_seed_lvl", None)):
                        for _mid in sorted(_prev_ids - _cur_ids):
                            _hh = getattr(self, "_ego_harvest", None) or {}
                            _tried2 = _hh.get("tried") or set()
                            _shape3 = (getattr(self, "_ego_frame_shape", None)
                                       or (64, 64))
                            # R1 CONSUMER (one-currency law): the agent's own
                            # starvation records STEER exploration effort —
                            # a bounded multiplicative widening of the probe's
                            # candidate budget. Never a bar/support/price.
                            _scap = 5
                            try:
                                _aff3 = getattr(self, "_affect", None)
                                if _aff3 is not None:
                                    _scap = int(round(5 * float(
                                        _aff3.starvation_steer(
                                            str(getattr(self, "_game_id", "")
                                                or "game"))["explore_boost"])))
                            except Exception:
                                _scap = 5
                            _cands = []  # untried cells from the harvest
                            for _my in range(4, int(_shape3[0]), 8):
                                for _mx in range(4, int(_shape3[1]), 8):
                                    if len(_cands) >= _scap:
                                        break
                                    if (_mx, _my) not in _tried2:
                                        _cands.append((_mx, _my))
                                if len(_cands) >= _scap:
                                    break
                            _pv = self._mute.mute(
                                item={"id": _mid, "kind": "objective"},
                                candidates=_cands,
                                observed_counts={_cc: 0 for _cc in _cands})
                            # no explore-aim variable exists yet: log the probe
                            print(f"[MUTE] probe={_pv.get('probe')} item={_mid}")
                    self._w4c_seed_ids = _cur_ids
                    self._w4c_seed_lvl = _slv_now
            except Exception:
                _swal(self, "OTHER")
            # ═══ 3d-i (EGO-FRONTIER): frontier level + first post-frontier click ═══
            # Per-episode by construction (the loop instance is per-episode).
            # The fatal-opening book rides the fabric (lazy, once per episode).
            if not hasattr(self, "_ego_frontier_book"):
                try:
                    from engines.egocentric.frontier import FrontierBook
                    _fab = getattr(self, "_ego_fabric", None)
                    self._ego_frontier_book = (
                        FrontierBook(_fab) if _fab is not None else None)
                except Exception:
                    self._ego_frontier_book = None
                    _swal(self, "FRONTIER")
                # 3d-ii: per-episode harvest material (banked at episode end)
                self._ego_frontier_dead = []      # frontier clicks with NO effect
                self._ego_frontier_effects = []   # frontier clicks that changed the frame
            if post_array is not None:
                self._ego_frame_shape = post_array.shape[:2]
            # ═══ LEVEL-SCOPED IDEAS: RE-SEED on level change ═══
            # The playing level is levels_completed + 1; whenever it drifts from
            # the seeded level (live increment above, OR the obs-based max in
            # cycle() on a handoff), demote the previous level's inherited seeds
            # (their gate closes; pariah status untouched) and reload priors
            # scoped to the level now being played. Runs AFTER the credit
            # branches so a level-up at a seeded cell still echoes its prior.
            try:
                _fab = getattr(self, "_ego_fabric", None)
                _plv = self._ego_level + 1
                if (_fab is not None
                        and getattr(self, "_ego_seed_level", None) != _plv):
                    for _dc in list(getattr(self, "_ego_seeded", None) or {}):
                        self._goal_spine.demote_inherited(_dc)
                    for _dc in list(getattr(self, "_ego_seeded_clicks", None)
                                    or {}):
                        self._goal_spine.demote_inherited_click(_dc)
                    self._ego_seeded = {}
                    self._ego_seeded_clicks = {}
                    _gkey = str(getattr(self, "_game_id", "") or "game")
                    _bonus = self._goal_spine.manager.confirm_bonus
                    for _p in _fab.priors(_gkey, level=_plv)[:3]:
                        if _p.get("pariah"):
                            continue
                        _pi = _p.get("idea") or {}
                        _pk = _pi.get("kind")
                        if _pk not in ("BE_AT", "CLICK_AT"):
                            continue
                        _pc = _pi.get("cell") or []
                        if len(_pc) != 2:
                            continue
                        _pcell = (int(_pc[0]), int(_pc[1]))
                        _price = (_bonus if _p.get("credibility", 0) >= 1
                                  else _bonus * 0.6)
                        if _pk == "CLICK_AT":
                            self._goal_spine.seed_confirmed_click(
                                _pcell, price=_price)
                            self._ego_seeded_clicks[_pcell] = _p["id"]
                        else:
                            self._goal_spine.seed_confirmed(_pcell, price=_price)
                            self._ego_seeded[_pcell] = _p["id"]
                    self._ego_seed_level = _plv
                    print(f"[EGO-SEED] level={_plv} n="
                          f"{len(self._ego_seeded) + len(self._ego_seeded_clicks)}")
            except Exception:
                _swal(self, "FABRIC")
            # The FIRST click made AT the frontier (not the one that opened it):
            # a level-up step's click belongs to the level below, so it is skipped.
            if (not level_changed and self._ego_level >= 1
                    and getattr(self, "_ego_first_frontier_click", None) is None
                    and _ax is not None and _ay is not None):
                self._ego_first_frontier_click = (int(_ax), int(_ay))
            # ═══ 3d-ii (EGO-FRONTIER): accrue the harvest material ═══
            # Every click is an OBSERVATION — effectful or dead — banked at
            # episode end. CK-1b (record/prereg/PREREG_CK_WAVE1.md): level 0 accrues too —
            # the affordance harvest is un-gated from the frontier (18 level-0
            # games banked nothing across 48-112 episodes each). A level-up
            # step's click belongs to the level below, so it is skipped (the
            # same convention as the first-frontier click).
            if (not level_changed
                    and _ax is not None and _ay is not None):
                (self._ego_frontier_effects if frame_changed
                 else self._ego_frontier_dead).append((int(_ax), int(_ay)))
            # ═══ 3d-ii (EGO-FRONTIER): consume the population harvest, ONCE per level ═══
            # deltas pre-establish the spine's move-map (means, not signal — drive still
            # requires a confirmed goal); dead/fatal/tried feed the pre-empt veto.
            # B1 (BUILD_PROGRAM_2 W1): _ego_level >= 0 — level-0 records load
            # too (18 level-0 games banked harvests nobody consumed); the
            # conservative >=2-report dead rule lives in load_harvest itself.
            # A3-2 CONVENTION (COMPLETED level): frontier streams (harvest /
            # fatal openings / moves) are keyed by bare _ego_level -- the level
            # already completed, where the banked experience was earned.
            if self._ego_frontier_book is not None and self._ego_level >= 0:
                if not hasattr(self, "_ego_harvest_cache"):
                    self._ego_harvest_cache = {}
                if self._ego_level not in self._ego_harvest_cache:
                    _h = self._ego_frontier_book.load_harvest(
                        str(getattr(self, "_game_id", "") or "game"),
                        self._ego_level)
                    self._ego_harvest_cache[self._ego_level] = _h
                    for _ha, _hd in _h["deltas"].items():
                        for _ in range(self._goal_spine.min_evidence):
                            self._goal_spine.note_move(str(_ha), _hd)
                    print(f"[EGO-FRONTIER] harvest loaded level={self._ego_level} "
                          f"dead={len(_h['dead'])} effects={len(_h['effects'])} "
                          f"fatal={len(_h['fatal'])} tried={len(_h['tried'])} "
                          f"deltas={len(_h['deltas'])}")
                self._ego_harvest = self._ego_harvest_cache[self._ego_level]
            # ═══ C33 STEP 1 (EGO-BET): settle the pending bet in the result path ═══
            # Settled against the EXECUTED action's frame; committed != executed is
            # VOID (nothing priced) but the executed transition is recorded either
            # way — it feeds the NEXT commit's paste member, never a decision.
            try:
                _bb = getattr(self, "_bet_book", None)
                if (_bb is not None and getattr(_bb, "pending", None) is not None
                        and post_array is not None):
                    # A3-2 CONVENTION (PLAYING level): settlements carry the
                    # level being played (_ego_level + 1) -- registered with
                    # atoms/mint_verdicts/import*/goal_hypotheses; the frontier
                    # streams alone carry the COMPLETED level. A3-1's hydrator
                    # (_hyd_ver) reads this back at the same grain.
                    _bb.level = int(getattr(self, "_ego_level", 0) or 0) + 1
                    _bexec = int((getattr(self, "_last_action_info", None)
                                  or {}).get('type', 0) or 0)
                    _bbefore = _bb.pending.get("before")
                    # F4: thread this step's known-atom bet (id + bin) from the
                    # bank settle above into the settlement record; consume it
                    # so a stale key never rides a later settle.
                    _wsa = getattr(self, "_w4c_step_atom", None) or (None, None)
                    self._w4c_step_atom = (None, None)
                    _bout = _bb.settle(post=post_array, executed_action=_bexec,
                                       atom_key=_wsa[0], atom_bin=_wsa[1])
                    if _bout is not None and _bbefore is not None:
                        if not hasattr(self, "_bet_transitions"):
                            self._bet_transitions = {}
                        self._bet_transitions[_bexec] = (_bbefore, post_array.copy())
                    if _bout is not None and _bb.settled % 25 == 0:
                        print(f"[BET] settles={_bb.settled} voids={_bb.voided} "
                              f"actions={len(_bb.records)} errors={_bb.errors}")
            except Exception:
                _swal(self, "BANK_SETTLE")
            if self._ego_observer.calls % 25 == 0:
                print(f"[EGO-GOAL] confirmed={self._goal_spine.has_confirmed()} "
                      f"candidates={len(self._goal_spine.manager.price)} "
                      f"established={sorted(self._goal_spine.established())}")
        except Exception:
            _swal(self, "SPINE")

        # ═══ W1 (PREREG_W1_NARRATION.md): the outcome-side narration closes the
        # loop against this step's pre-action bet by reference — PERCEIVE (per
        # slot), ROUTE (bin + why-not), MINT (candidate/guard-zero + bargain),
        # ECHO (settled vs candidate). O(1): cached step state only. ═══
        _narr_close(self, post_array, frame_changed)

        # ═══ MOVEMENT STACK (FIRST ACTIVATION, rung 0c): CursorAgency + GridNav ═══
        # CursorAgency learns the own-avatar displacement map from REAL move
        # outcomes (pre/post frames + the executed action); GridNav builds
        # directed-edge traversability from that map + the observed frames.
        # Consumed ONLY by the [NAV] steer in _act (a capped bias, wheel rule).
        # House containment: never raises; compact site.
        try:
            _mvact = int((getattr(self, "_last_action_info", None)
                          or {}).get('type', 0) or 0)
            _mvpre = getattr(self, "_prev_frame", None)
            if level_changed and getattr(self, "_grid_nav", None) is not None:
                from engines.egocentric.navigation import GridNav
                self._grid_nav = GridNav()   # the maze redraws: walls re-earn
                self._nav_cell = None
            if (_mvact in (1, 2, 3, 4, 5) and not level_changed
                    and _mvpre is not None and post_array is not None
                    and getattr(_mvpre, "shape", None) == post_array.shape):
                if getattr(self, "_cursor_agency", None) is None:
                    from engines.egocentric.agency import CursorAgency
                    from engines.egocentric.navigation import GridNav
                    self._cursor_agency = CursorAgency()
                    self._grid_nav = GridNav()
                    self._nav_cell = None
                _ag = self._cursor_agency
                _ag.observe(_mvpre, str(_mvact), post_array)
                if _ag.ready():
                    _st = int(_ag.stride() or 1) or 1
                    _p0 = _ag.locate(_mvpre)
                    _p1 = _ag.locate(post_array)
                    _sh = _ag.predict(str(_mvact))
                    if _p0 is not None and _p1 is not None:
                        _cl0 = (int(round(_p0[0] / _st)),
                                int(round(_p0[1] / _st)))
                        _cl1 = (int(round(_p1[0] / _st)),
                                int(round(_p1[1] / _st)))
                        if _sh is not None:
                            self._grid_nav.observe_move(_cl0, _sh, _cl1 != _cl0)
                            self._grid_nav.decay()
                        self._nav_cell = _cl1
        except Exception:
            _swal(self, "OTHER")

        # ═══ RESET COUNTER (maintainer's order, part a — instrumentation) ═══
        # A board reverting to the episode/level ANCHOR frame after a solid run
        # (>= RESET_MIN_RUN frame-changing steps) is a RESET: counted,
        # attributed to the executed action, narrated [RESET]; the end_game
        # settle line testifies the count. INSTRUMENTATION ONLY — the counter
        # REPORTS; any selection guard enters singly, later, after the books
        # read. Returning to the anchor WITHOUT a solid run is ordinary
        # back-and-forth and counts nothing.
        try:
            if post_array is not None:
                _rsig = (post_array.shape, post_array.tobytes())
                if getattr(self, "_reset_anchor", None) is None:
                    _rpre = getattr(self, "_prev_frame", None)
                    self._reset_anchor = ((_rpre.shape, _rpre.tobytes())
                                          if _rpre is not None else _rsig)
                if level_changed:
                    self._reset_anchor = _rsig   # the new level's start board
                    self._reset_run = 0
                elif _rsig == self._reset_anchor:
                    if int(getattr(self, "_reset_run", 0)) >= RESET_MIN_RUN:
                        self._reset_ep_count = int(
                            getattr(self, "_reset_ep_count", 0) or 0) + 1
                        _rsa = int((getattr(self, "_last_action_info", None)
                                    or {}).get('type', 0) or 0)
                        _rd = getattr(self, "_reset_actions", None)
                        if _rd is None:
                            _rd = self._reset_actions = {}
                        _rd[_rsa] = int(_rd.get(_rsa, 0)) + 1
                        print(f"[RESET] detected action={_rsa} "
                              f"resets={self._reset_ep_count} "
                              f"run={self._reset_run}")
                    self._reset_run = 0
                elif frame_changed:
                    self._reset_run = int(getattr(self, "_reset_run", 0)) + 1
        except Exception:
            _swal(self, "OTHER")

        # ═══ GAP 4: Rich action outcome computation ═══
        self._compute_rich_outcome(cf, post_array)

        # ═══ GAP 5: HUD state tracking ═══
        self._check_hud_state(cf, post_array)

        # ═══ GAP 5B: Feed HUD changes into CausalMap ═══
        # If the HUD changed after this action, record the association
        # so the system learns which actions affect environmental state.
        if cf.hud_state_changed and self._causal_map and self._last_action_info:
            action_pos = None
            if self._last_action_info.get('x') is not None:
                action_pos = (self._last_action_info['x'], self._last_action_info['y'])
            self._causal_map.record_hud_change(
                action_pos=action_pos,
                action_type=self._last_action_info.get('type', 0),
                _timer_urgency=cf.timer_urgency,
            )

        # Calculate surprise using the CausalMap's prediction system
        if self._causal_map and self._last_action_info:
            click_pos = None
            if self._last_action_info.get('x') is not None:
                click_pos = (self._last_action_info['x'], self._last_action_info['y'])

            if click_pos:
                prediction = self._causal_map.predict(click_pos)
                if prediction is not None:
                    # We had a prediction -- how surprising is the result?
                    if prediction.confidence > 0.5:
                        expected_change = len(prediction.expected_affected) > 0
                        if expected_change == frame_changed:
                            cf.surprise = 0.1  # As expected
                        else:
                            cf.surprise = 0.8  # Surprising!
                    else:
                        cf.surprise = 0.4  # Low-confidence prediction
                else:
                    cf.surprise = 0.5  # No prediction, moderate surprise
            else:
                cf.surprise = 0.3  # Non-click action

        # ═══ MAP UPDATE: Learn from the action's consequence ═══
        if self._causal_map and self._last_action_info:
            click_x = self._last_action_info.get('x')
            click_y = self._last_action_info.get('y')
            action_type = self._last_action_info.get('type', 0)

            # ═══ CONTEXT TRACKING: Record every action type ═══
            # This feeds the prediction-surprise system. Non-click
            # actions (pans, movements) are the CONTEXT that explains
            # why click effects change. Must record ALL actions.
            self._causal_map.record_action_context(action_type)

            # ═══ TEMPORAL CAUSAL LEARNING: Feed frame to delayed observers ═══
            # Every frame is fed into active delayed observation windows,
            # regardless of what action was just taken. This lets us detect
            # effects that unfold over multiple frames (VC33 fluid dynamics).
            if post_array is not None and self._causal_map.has_active_delayed_observations:
                self._causal_map.observe_delayed_frame(post_array)

            if click_x is not None and click_y is not None:
                pre = self._prev_frame
                post = post_array

                self._causal_map.update_from_action(
                    click_pos=(click_x, click_y),
                    pre_frame=pre,
                    post_frame=post,
                    frame_changed=frame_changed,
                )

                # ═══ GAP 2A: Feed abstract state to CausalMap ═══
                # Keep CausalMap aware of current cell states for planning
                if post is not None:
                    abstract_state = self._abstract_frame_state(post)
                    if abstract_state:
                        self._causal_map.set_current_state(abstract_state)

                # ═══ TEMPORAL CAUSAL LEARNING: Start delayed observation ═══
                # For click-only games (likely VC33), start watching for
                # delayed effects that unfold over subsequent frames.
                # Only for click actions that DIDN'T produce immediate change.
                is_click_only_game = (
                    6 in self._available_actions
                    and not any(a in self._available_actions for a in (1, 2, 3, 4))
                )
                if is_click_only_game and post is not None:
                    # Start delayed observation for EVERY click in click-only games
                    # because even "immediate" changes may have delayed secondary effects
                    self._causal_map.start_delayed_observation(
                        action_pos=(click_x, click_y),
                        action_type=action_type,
                        frame_at_action=post,
                        window_size=5,
                    )

                # ═══ GAP 4B: Feed goal progress into CausalMap ═══
                if cf.goal_progress_delta != 0 or cf.was_productive or cf.was_destructive:
                    self._causal_map.record_goal_progress(
                        click_pos=(click_x, click_y),
                        goal_delta_before=cf.goal_delta_before,
                        goal_delta_after=cf.goal_delta_after,
                    )

                cf.map_update = f"Recorded effect at ({click_x},{click_y})"
                if not frame_changed:
                    cf.map_update += " [no effect]"
                elif cf.was_productive:
                    cf.map_update += f" [PRODUCTIVE +{cf.goal_progress_delta}]"
                elif cf.was_destructive:
                    cf.map_update += f" [destructive {cf.goal_progress_delta}]"

                # Update map summary
                cf.map_completeness = self._causal_map.completeness
                cf.effects_known = len(self._causal_map._effects)
                cf.positions_explored = len(self._causal_map._explored)
                cf.map_summary = self._causal_map.summary()

            # ═══ GAP 3C: Track movement results for directional games ═══
            elif action_type in (1, 2, 3, 4) and post_array is not None:
                # ═══ CAMERA-PAN DETECTION ═══
                # For hybrid games (FT09): directional actions may PAN
                # the camera rather than move an agent. A pan shifts >80%
                # of pixels uniformly. Detect this to avoid misclassifying
                # a pan as agent movement.
                is_hybrid = (6 in self._available_actions
                             and any(a in self._available_actions for a in (1, 2, 3, 4)))
                detected_pan = False

                if is_hybrid and self._prev_frame is not None:
                    try:
                        if self._prev_frame.shape == post_array.shape:
                            diff_mask = self._prev_frame != post_array
                            total_px = diff_mask.size
                            changed_px = int(diff_mask.sum())
                            # Pan: >80% of pixels changed (whole viewport shifted)
                            if total_px > 0 and changed_px / total_px > 0.80:
                                detected_pan = True
                                cf.map_update = (
                                    f"Camera pan via ACTION{action_type}"
                                    f" ({changed_px}/{total_px} px changed)"
                                )
                                # Reset stable regions since the viewport changed
                                self._stable_region_attempts = 0
                                self._stable_mask = None
                                self._reference_snapshot = None
                    except Exception:
                        pass

                if not detected_pan:
                    # Directional action -- detect agent movement
                    new_agent_pos = self._detect_agent_position(post_array)
                    if new_agent_pos is not None:
                        self._causal_map.record_movement_result(
                            action_type=action_type,
                            agent_pos_before=self._agent_position,
                            agent_pos_after=new_agent_pos,
                        )
                        if self._agent_position != new_agent_pos:
                            cf.map_update = f"Moved to ({new_agent_pos[0]},{new_agent_pos[1]})"

                            # ═══ Object Collision Detection (LS20) ═══
                            # If the agent moved AND extra frame changes
                            # occurred beyond agent movement, the agent
                            # may have collided with an interactive object.
                            if (self._prev_frame is not None
                                    and post_array is not None
                                    and frame_changed):
                                try:
                                    diff_mask = self._prev_frame != post_array
                                    changed_px = int(diff_mask.sum())
                                    # Agent movement alone changes ~10-30 pixels.
                                    # If >50 pixels changed, something else happened.
                                    if changed_px > 50:
                                        # Check what color was at the new position
                                        # in the PREVIOUS frame (before collision)
                                        nx, ny = new_agent_pos
                                        if (0 <= ny < self._prev_frame.shape[0]
                                                and 0 <= nx < self._prev_frame.shape[1]):
                                            object_color = int(self._prev_frame[ny, nx])
                                            bg_color = 0  # Background is usually black
                                            if object_color != bg_color:
                                                self._causal_map.record_collision(
                                                    agent_pos=new_agent_pos,
                                                    object_color=object_color,
                                                    hud_snapshot_before=None,
                                                    hud_snapshot_after=None,
                                                )
                                                cf.map_update += (
                                                    f" [COLLISION color={object_color}"
                                                    f" extra_px={changed_px}]"
                                                )
                                except Exception:
                                    pass
                        else:
                            cf.map_update = f"Wall at ({self._agent_position[0] if self._agent_position else '?'},{self._agent_position[1] if self._agent_position else '?'}) dir={action_type}"
                        self._agent_position = new_agent_pos

        # Update last action info for next temporal perception
        if self._last_action_info:
            self._last_action_info['frame_changed'] = frame_changed
            self._last_action_info['score_delta'] = score_delta
            self._last_action_info['level_changed'] = level_changed
            self._last_action_info['consecutive_no_change'] = self._consecutive_no_change

        # Update game state
        if level_changed:
            self._current_level = new_level if new_level > 0 else self._current_level + 1
            # Reset stable regions for new level (visual layout may change)
            self._stable_region_attempts = 0
            self._stable_mask = None
            self._reference_snapshot = None
            self._frame_history = []
            self._active_plan = []  # Plan is invalid for new level
            # Fix 2: Reset goal tracking so stale data from previous level
            # doesn't produce phantom deltas on the first action of new level
            self._goal_cells_total = 0
            self._last_goal_delta_count = 0
            self._productive_rotation_index = 0
            # Reset action monotony -- new level is a fresh context
            self._consecutive_same_action = 0
            self._last_action_type = None
            # Reset level-specific causal map data while preserving
            # game-level mechanics (rules, effects, color cycles)
            if self._causal_map:
                self._causal_map.reset_for_new_level()
        self._score = new_score if new_score else self._score + score_delta

        # Build result summary
        parts = []
        if frame_changed:
            parts.append("Frame changed")
        else:
            parts.append(f"No change (x{self._consecutive_no_change})")
        if score_delta > 0:
            parts.append(f"score +{score_delta:.2f}")
        elif score_delta < 0:
            parts.append(f"score {score_delta:.2f}")
        if level_changed:
            parts.append("[LEVEL-UP]")
        if cf.goal_cells_total > 0:
            parts.append(f"goal:{cf.goal_cells_correct}/{cf.goal_cells_total}")
        if cf.was_productive:
            parts.append("[PROGRESS]")
        cf.result_summary = " | ".join(parts)

    # ═══════════════════════════════════════════════════════════════════
    # GAP IMPLEMENTATIONS: Cognitive machinery for learning
    # ═══════════════════════════════════════════════════════════════════

    def _compute_stable_regions(self):
        """
        Gap 1: Identify pixels that NEVER change across frame history.

        Stable regions are likely reference/goal displays, HUD elements,
        or background. Changing regions are likely interactive workspace.

        This is game-agnostic: the agent discovers the goal structure
        from observation, not from game-specific knowledge.
        """
        if len(self._frame_history) < 3:
            return

        self._stable_region_attempts += 1

        try:
            base = self._frame_history[0]
            # Build a mask: True where pixel NEVER changed from the base
            stable = np.ones(base.shape, dtype=bool)

            for frame in self._frame_history[1:]:
                if frame.shape == base.shape:
                    stable &= (frame == base)

            # ═══ Fix 4: Exclude HUD edge pixels from stable mask ═══
            # Edge strips contain timer bars, lives, and decorations that
            # are stable initially but change later (timer ticks, life lost).
            # Including them corrupts the workspace delta computation.
            edge = self._hud_edge_size
            h, w = stable.shape[:2]
            if h > edge * 2 and w > edge * 2:
                stable[:edge, :] = False   # top strip
                stable[-edge:, :] = False  # bottom strip
                stable[:, :edge] = False   # left strip
                stable[:, -edge:] = False  # right strip

            # A region is "stable" if a meaningful fraction of its pixels
            # never changed. Compute the fraction of stable pixels.
            total_pixels = stable.size
            stable_pixels = int(stable.sum())
            stable_fraction = stable_pixels / max(total_pixels, 1)

            # Only accept if there's a meaningful split (not all stable, not all changing)
            if 0.1 < stable_fraction < 0.95:
                self._stable_mask = stable
                self._reference_snapshot = base.copy()

                if self._verbose:
                    print(f"    [GAP1-STABLE] Stable region: {stable_fraction:.0%} pixels never changed")

                # Try to detect a reference/goal panel among the stable pixels
                self._detect_reference_panel(base)
            else:
                # Everything changes or nothing changes -- can't split
                # Don't set _stable_mask so retry is possible with more frames
                if self._verbose:
                    print(f"    [GAP1-STABLE] No useful split ({stable_fraction:.0%} stable, attempt {self._stable_region_attempts})")

        except Exception as e:
            logger.debug(f"[GAP1] Stable region computation failed: {e}")

    def _abstract_frame_state(
        self, frame: np.ndarray
    ) -> Dict[Tuple[int, int], int]:
        """
        Gap 2A: Convert raw frame into abstract {(x,y): color} dict.

        Uses the stable mask to focus on the INTERACTIVE workspace
        (changing pixels only). Each pixel in the workspace becomes
        a keyed cell. This abstract state is suitable for:
        - Goal comparison (diff against reference)
        - CausalMap state tracking (set_current_state)
        - Frame-to-frame delta computation

        Returns empty dict if stable mask hasn't been computed yet.
        """
        if self._stable_mask is None:
            return {}

        try:
            if frame.shape != self._stable_mask.shape:
                return {}

            # The changing region IS the interactive workspace
            changing = ~self._stable_mask
            if not changing.any():
                return {}

            # Extract (y, x) positions of changing pixels
            ys, xs = np.where(changing)

            state: Dict[Tuple[int, int], int] = {}
            for i in range(len(ys)):
                pos = (int(xs[i]), int(ys[i]))
                state[pos] = int(frame[ys[i], xs[i]])

            return state

        except Exception:
            return {}

    def _compute_workspace_delta(
        self, current_frame: np.ndarray
    ) -> Tuple[int, int]:
        """
        Gap 1 + Gap 2: Measure how much the workspace has changed.

        Compares the CHANGING regions of the current frame against
        the initial snapshot (frame[0]). This measures "cells that
        have been modified" — exploration coverage — NOT "cells
        matching a goal." We don't know the goal state.

        The score_delta from the API is the ground truth for whether
        modifications are moving toward the goal. This method just
        counts HOW MANY cells have been touched.

        Returns (total_workspace_cells, cells_modified_from_initial).
        """
        if self._stable_mask is None or self._reference_snapshot is None:
            return 0, 0

        try:
            if current_frame.shape != self._reference_snapshot.shape:
                return 0, 0

            # The changing pixels are the interactive workspace.
            changing = ~self._stable_mask
            if not changing.any():
                return 0, 0

            # Count workspace cells that DIFFER from initial state.
            # More modified = more exploration coverage.
            total = int(changing.sum())
            modified = int((current_frame[changing] != self._reference_snapshot[changing]).sum())

            return total, modified

        except Exception:
            return 0, 0

    def _detect_reference_panel(self, frame: np.ndarray) -> bool:
        """
        Goal-discovery: find stable colored regions that may encode goals.

        IMPORTANT: This does NOT assume a separate "reference panel" that
        spatially maps to the workspace. In many games:
        - FT09: Key sprites are INLINE within the interactive grid,
          adjacent to each tile. The agent sees through a camera viewport.
        - LS20: Lock pattern is displayed in the HUD (already tracked
          by _check_hud_state's region analysis).
        - VC33: Goals are dynamic (fluid reaching target positions).

        Game-agnostic strategy:
        1. Find stable, non-background, non-HUD colored pixels
        2. Group them into small clusters (connected components)
        3. Record each cluster's position and color — these are
           candidate "goal indicators" (key sprites, markers, etc.)
        4. Do NOT assume a single bounding-box panel or spatial scaling

        The CausalMap + constraint decoder use these indicators to
        determine per-tile target colors.

        Returns True if any goal indicators were found or updated.
        """
        if self._stable_mask is None:
            return False

        try:
            h, w = frame.shape[:2]
            edge = self._hud_edge_size

            # Build mask: stable, non-HUD, non-background
            stable_inner = self._stable_mask.copy()
            if h > edge * 2 and w > edge * 2:
                stable_inner[:edge, :] = False
                stable_inner[-edge:, :] = False
                stable_inner[:, :edge] = False
                stable_inner[:, -edge:] = False

            non_bg = frame != 0
            indicator_mask = stable_inner & non_bg

            if not indicator_mask.any():
                return False

            # Find individual colored pixels that are stable
            ys, xs = np.where(indicator_mask)
            if len(ys) < 2:
                return False

            # Group into clusters using simple flood-fill
            visited = set()
            clusters: list = []
            for i in range(len(ys)):
                pos = (int(xs[i]), int(ys[i]))
                if pos in visited:
                    continue
                # BFS to find connected component
                cluster_cells: Dict[Tuple[int, int], int] = {}
                stack = [pos]
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in visited:
                        continue
                    if not (0 <= cy < h and 0 <= cx < w):
                        continue
                    if not indicator_mask[cy, cx]:
                        continue
                    visited.add((cx, cy))
                    cluster_cells[(cx, cy)] = int(frame[cy, cx])
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = cx + dx, cy + dy
                        if (nx, ny) not in visited:
                            stack.append((nx, ny))

                if len(cluster_cells) >= 2:
                    # Compute cluster centroid and color
                    cxs = [p[0] for p in cluster_cells]
                    cys = [p[1] for p in cluster_cells]
                    centroid = (
                        sum(cxs) // len(cxs),
                        sum(cys) // len(cys),
                    )
                    colors = list(set(cluster_cells.values()))
                    clusters.append({
                        'centroid': centroid,
                        'cells': cluster_cells,
                        'colors': colors,
                        'primary_color': colors[0] if len(colors) == 1 else max(
                            set(cluster_cells.values()),
                            key=list(cluster_cells.values()).count,
                        ),
                        'size': len(cluster_cells),
                    })

            if not clusters:
                return False

            # Store as goal indicators (not a single panel)
            self._reference_panel = {
                'type': 'distributed_indicators',
                'clusters': clusters,
                'total_indicators': len(clusters),
                'region': None,  # No single bounding box
                'cells': {},  # Flatten for backward compat
            }
            # Flatten all cluster cells into cells dict
            for cluster in clusters:
                self._reference_panel['cells'].update(cluster['cells'])

            if self._verbose:
                print(
                    f"    [GOAL-DETECT] Found {len(clusters)} goal indicators, "
                    f"{sum(c['size'] for c in clusters)} pixels, "
                    f"colors: {sorted(set(c['primary_color'] for c in clusters))}"
                )

            return True

        except Exception as e:
            logger.debug(f"[GOAL-DETECT] Goal indicator detection failed: {e}")
            return False

    def _compute_goal_match(
        self, frame: np.ndarray
    ) -> Tuple[int, int, float]:
        """
        Goal-match: compare current interactive cells against known targets.

        Instead of assuming a spatial correspondence between a "reference
        panel" and the "workspace," this method uses the CausalMap's
        knowledge to count how many interactive tiles currently match
        their target colors.

        Target colors come from:
        1. Goal indicators (stable colored clusters detected by
           _detect_reference_panel) — used as hints, not spatial maps
        2. CausalMap's goal_cells (if set by constraint decoder)
        3. Score-delta feedback (positions where changes improved score)

        For camera-viewport games (FT09): the goal match is computed
        only for the CURRENTLY VISIBLE portion of the game. The agent
        must pan to see other quadrants.

        Returns (match_cells, mismatch_cells, match_fraction).
        """
        if self._causal_map is None:
            return 0, 0, 0.0

        try:
            # Strategy 1: Use CausalMap's goal cells if available
            goal_cells = self._causal_map._goal_cells
            if goal_cells:
                match_count = 0
                mismatch_count = 0
                h, w = frame.shape[:2]
                for (gx, gy), target_color in goal_cells.items():
                    if 0 <= gy < h and 0 <= gx < w:
                        current_color = int(frame[gy, gx])
                        if current_color == target_color:
                            match_count += 1
                        else:
                            mismatch_count += 1
                total = match_count + mismatch_count
                if total > 0:
                    return match_count, mismatch_count, match_count / total

            # Strategy 2: Use goal indicators + CausalMap effects to
            # count tiles at their target color. Each indicator cluster
            # near a known interactive position suggests a target color.
            if (self._reference_panel
                    and self._reference_panel.get('type') == 'distributed_indicators'):
                clusters = self._reference_panel.get('clusters', [])
                if not clusters:
                    return 0, 0, 0.0

                match_count = 0
                mismatch_count = 0
                h, w = frame.shape[:2]

                for cluster in clusters:
                    indicator_color = cluster.get('primary_color', 0)
                    centroid = cluster.get('centroid', (0, 0))

                    # Find the nearest interactive (explored) position
                    nearest_pos = None
                    nearest_dist = float('inf')
                    for pos in self._causal_map._explored:
                        dist = abs(pos[0] - centroid[0]) + abs(pos[1] - centroid[1])
                        if dist < nearest_dist:
                            nearest_dist = dist
                            nearest_pos = pos

                    if nearest_pos and nearest_dist < 20:
                        px, py = nearest_pos
                        if 0 <= py < h and 0 <= px < w:
                            current_color = int(frame[py, px])
                            if current_color == indicator_color:
                                match_count += 1
                            else:
                                mismatch_count += 1

                total = match_count + mismatch_count
                if total > 0:
                    return match_count, mismatch_count, match_count / total

            # Strategy 3: Use productive target tracking as a proxy
            # (positions where clicking improved the score)
            productive = self._causal_map.get_productive_targets()
            if productive:
                # Count how many productive positions still need clicks
                match_count = len([p for p in productive if p[1] >= 0.8])
                mismatch_count = len([p for p in productive if p[1] < 0.8])
                total = match_count + mismatch_count
                if total > 0:
                    return match_count, mismatch_count, match_count / total

            return 0, 0, 0.0

        except Exception as e:
            logger.debug(f"[GOAL-MATCH] Goal match computation failed: {e}")
            return 0, 0, 0.0

    def _compute_rich_outcome(self, cf: CognitiveFrame, post_array: Optional[np.ndarray]):
        """
        Gap 4: Compute rich action outcome with goal-progress tracking.

        Replaces binary frame_changed with multi-dimensional signal:
        - pixels_changed: raw pixel count
        - goal_delta_before/after: cells wrong before/after action
        - goal_progress_delta: improvement toward goal
        - was_productive/destructive/neutral/wasted: categorical outcome
        """
        # Compute pixels changed
        if self._prev_frame is not None and post_array is not None:
            try:
                if self._prev_frame.shape == post_array.shape:
                    diff = self._prev_frame != post_array
                    cf.pixels_changed = int(diff.sum())
            except Exception:
                pass

        # Goal-delta tracking: how many workspace cells differ from initial state
        # This tracks "exploration coverage" not "goal correctness" since we
        # don't know the target state game-agnostically.
        cf.goal_delta_before = self._last_goal_delta_count

        if post_array is not None:
            goal_total, cells_modified = self._compute_workspace_delta(post_array)
            cf.goal_cells_total = goal_total
            cf.goal_cells_correct = cells_modified  # cells touched, not "correct"
            cf.goal_completion = cells_modified / max(goal_total, 1)
            cf.goal_delta_after = goal_total - cells_modified
            # Update loop-level goal awareness
            if goal_total > 0:
                self._goal_cells_total = goal_total

            # ═══ Semantic goal matching: use TRUE goal match when available ═══
            # If we have a detected reference panel, compute how many
            # workspace cells actually match the goal pattern. This
            # replaces the "exploration coverage" proxy with a real metric.
            if self._reference_panel is not None:
                match_cells, mismatch_cells, match_frac = (
                    self._compute_goal_match(post_array)
                )
                cf.reference_panel_detected = True
                cf.goal_match_cells = match_cells
                cf.goal_mismatch_cells = mismatch_cells
                cf.goal_match_fraction = match_frac

                # Override the exploration-based goal_cells with true match
                ref_total = match_cells + mismatch_cells
                if ref_total > 0:
                    cf.goal_cells_total = ref_total
                    cf.goal_cells_correct = match_cells
                    cf.goal_completion = match_frac
                    cf.goal_delta_after = mismatch_cells

            # Update for next action
            self._last_goal_delta_count = cf.goal_delta_after
        else:
            cf.goal_delta_after = cf.goal_delta_before

        # Compute goal progress delta (change in remaining cells)
        cf.goal_progress_delta = cf.goal_delta_before - cf.goal_delta_after

        # Categorize outcome — score_delta from API is the ground truth.
        # Pixel-based delta is a secondary signal when score is flat.
        if not cf.frame_changed:
            cf.was_wasted = True
        elif cf.score_delta > 0:
            # API says we scored — this is definitively productive
            cf.was_productive = True
        elif cf.score_delta < 0:
            # API says we lost — this is definitively destructive
            cf.was_destructive = True
        elif cf.goal_progress_delta > 0:
            # Score flat but workspace delta improved — cautiously productive
            cf.was_productive = True
        elif cf.goal_progress_delta < 0:
            # Score flat but workspace delta worsened
            cf.was_destructive = True
        elif cf.goal_cells_total > 0:
            cf.was_neutral = True  # Frame changed but neither score nor delta moved
        # If no goal detected yet, frame_changed is the only signal

    def _check_hud_state(self, cf: CognitiveFrame, frame_array: Optional[np.ndarray]):
        """
        Gap 5 + 5C: Semantic HUD state extraction from frame edges.

        Splits the HUD into 4 independent sub-regions (top, bottom,
        left, right). For each region:
        - Tracks hash for change detection
        - Extracts color composition
        - Counts discrete objects (connected non-background blobs)
        - Estimates timer (bottom row shrinking bar)
        - Detects carried-state changes (non-timer regions changing)
        - Estimates lives (discrete same-colored objects)

        Game-agnostic: discovers what the edges mean by observing
        how they change over time.
        """
        if frame_array is None:
            return

        try:
            h, w = frame_array.shape[:2]
            edge = self._hud_edge_size

            if h <= edge * 2 or w <= edge * 2:
                return

            # Extract the 4 edge regions as 2D arrays (not raveled)
            regions: Dict[str, np.ndarray] = {
                'top': frame_array[:edge, :],
                'bottom': frame_array[-edge:, :],
                'left': frame_array[:, :edge],
                'right': frame_array[:, -edge:],
            }

            # ─── Overall hash (backward compat) ───
            all_edges = np.concatenate([r.ravel() for r in regions.values()])
            hud_hash = hash(all_edges.tobytes())
            cf.hud_state_hash = hud_hash
            cf.hud_state_changed = (
                self._prev_hud_hash != 0 and hud_hash != self._prev_hud_hash
            )
            self._prev_hud_hash = hud_hash

            # ─── Per-region semantic analysis ───
            region_changes: Dict[str, bool] = {}
            region_states: Dict[str, Dict[str, Any]] = {}
            non_timer_changed = False

            for name, region_2d in regions.items():
                region_flat = region_2d.ravel()
                region_hash = hash(region_flat.tobytes())

                # Did this specific region change?
                prev_hash = self._prev_hud_region_hashes.get(name, 0)
                changed = (prev_hash != 0 and region_hash != prev_hash)
                region_changes[name] = changed
                self._prev_hud_region_hashes[name] = region_hash

                # Color composition
                unique_colors = set(int(c) for c in np.unique(region_flat))
                colored_pixels = int(np.count_nonzero(region_flat))
                total_pixels = len(region_flat)
                colored_fraction = colored_pixels / max(total_pixels, 1)

                # Object counting: connected non-background blobs
                # Use simple run-length counting on rows for speed
                object_count = self._count_hud_objects(region_2d)

                state = {
                    'hash': region_hash,
                    'unique_colors': sorted(unique_colors),
                    'colored_fraction': round(colored_fraction, 3),
                    'object_count': object_count,
                    'changed': changed,
                }
                region_states[name] = state

                # Non-timer regions changing = carried state change
                if changed and name != 'bottom':
                    non_timer_changed = True

            # ─── Timer estimation (bottom region) ───
            bottom_state = region_states.get('bottom', {})
            cf.timer_fraction = bottom_state.get('colored_fraction', 1.0)
            if cf.timer_fraction < 0.2:
                cf.timer_urgency = "critical"
            elif cf.timer_fraction < 0.5:
                cf.timer_urgency = "moderate"
            else:
                cf.timer_urgency = "safe"

            # ─── Lives estimation ───
            # Look for discrete objects in top or right region that
            # could be life indicators. Prefer top region.
            lives_region = region_states.get('top', {})
            obj_count = lives_region.get('object_count', 0)
            if obj_count > 0 and obj_count <= 10:
                # Plausible life count (1-10)
                cf.lives_remaining = obj_count
            else:
                cf.lives_remaining = -1  # Unknown

            # ─── Carried state ───
            cf.carried_state_changed = non_timer_changed
            cf.hud_region_changes = region_changes
            cf.carried_state = {
                name: {
                    'colors': st.get('unique_colors', []),
                    'colored_frac': st.get('colored_fraction', 0),
                    'objects': st.get('object_count', 0),
                    'changed': st.get('changed', False),
                }
                for name, st in region_states.items()
            }

            self._prev_hud_region_states = region_states

        except Exception as e:
            logger.debug(f"[GAP5C] Semantic HUD check failed: {e}")

    @staticmethod
    def _count_hud_objects(region_2d: np.ndarray) -> int:
        """
        Count discrete non-background objects in a HUD region.

        Uses simple flood-fill on non-zero pixels. Objects are
        connected components of non-background color. Counts
        objects >= 2 pixels to filter noise.

        Returns count of distinct objects found.
        """
        if region_2d.size == 0:
            return 0
        try:
            # Binary mask: non-background pixels
            mask = region_2d != 0
            if not mask.any():
                return 0

            h, w = mask.shape
            visited = np.zeros_like(mask, dtype=bool)
            objects = 0

            for y in range(h):
                for x in range(w):
                    if mask[y, x] and not visited[y, x]:
                        # Flood-fill this component
                        size = 0
                        stack = [(y, x)]
                        while stack:
                            cy, cx = stack.pop()
                            if (0 <= cy < h and 0 <= cx < w
                                    and mask[cy, cx]
                                    and not visited[cy, cx]):
                                visited[cy, cx] = True
                                size += 1
                                stack.extend([
                                    (cy - 1, cx), (cy + 1, cx),
                                    (cy, cx - 1), (cy, cx + 1),
                                ])
                        if size >= 2:  # Filter single-pixel noise
                            objects += 1

            return objects
        except Exception:
            return 0

    def _detect_agent_position(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Gap 3C: Detect agent position in a movement game.

        For movement games, the agent is typically the only object
        that moves between frames. We detect it by diffing against
        the previous frame and finding where the "moved object"
        ended up.

        Game-agnostic: finds the centroid of the largest changed
        region that appeared in the new frame.
        """
        if self._prev_frame is None or frame.shape != self._prev_frame.shape:
            return self._agent_position

        try:
            diff = frame != self._prev_frame
            if not diff.any():
                return self._agent_position  # No change, same position

            # Find positions that are NEW (present in post but not pre)
            # These are where the agent moved TO
            changed_ys, changed_xs = np.where(diff)
            if len(changed_xs) == 0:
                return self._agent_position

            # Use centroid of changed pixels as approximate agent position
            cx = int(np.mean(changed_xs))
            cy = int(np.mean(changed_ys))
            return (cx, cy)

        except Exception:
            return self._agent_position

    # ─── Phase Implementations ────────────────────────────────────────

    def _perceive(self, frame: Any, cf: CognitiveFrame) -> PerceptualField:
        """PHASE 1: Run all perception channels and integrate."""
        percept = self._perceiver.perceive(
            frame,
            last_action=self._last_action_info,
            causal_map=self._causal_map,
            available_actions=self._available_actions,
            actions_taken=self._actions_taken,
            max_actions=self._max_actions,
            game_id=self._game_id,
        )

        # ── Bridge: Feed perception back into the causal map ──────────
        if self._causal_map:
            # Register discovered positions so completeness can rise above 0%
            positions_to_register = []

            # From detected objects (centroid positions)
            # Filter to small objects (< 1/8 frame area) = likely interactive
            # tiles, not background panels. Large blobs add noise.
            frame_area = 64 * 64
            for obj in percept.objects:
                if obj.get('size', frame_area) >= frame_area // 8:
                    continue  # Skip large background regions
                cx = int(obj.get('centroid_x', obj.get('x', 0)))
                cy = int(obj.get('centroid_y', obj.get('y', 0)))
                if 0 < cx < 64 and 0 < cy < 64:
                    positions_to_register.append((cx, cy))

            # From tile grid (inferred cell centers)
            if percept.tile_count > 0 and percept.interactive_bounds:
                y_min, x_min, y_max, x_max = percept.interactive_bounds
                rows = max(1, percept.grid_rows)
                cols = max(1, percept.grid_cols)
                tile_h = (y_max - y_min) // rows
                tile_w = (x_max - x_min) // cols
                for r in range(rows):
                    for c in range(cols):
                        tx = x_min + c * tile_w + tile_w // 2
                        ty = y_min + r * tile_h + tile_h // 2
                        positions_to_register.append((tx, ty))

            if positions_to_register:
                self._causal_map.register_positions(positions_to_register)

            # ── Bridge: Feed tile grid structure into CausalMap ────────
            # When VisualCortex detects a tile grid, pass the grid geometry
            # to CausalMap so it can aggregate pixel-level diffs into
            # tile-level effects. This is the key fix for the pixel-vs-tile
            # granularity problem.
            if (percept.tile_count > 0
                    and percept.interactive_bounds
                    and self._causal_map._tile_map is None):
                y_min, x_min, y_max, x_max = percept.interactive_bounds
                rows = max(1, percept.grid_rows)
                cols = max(1, percept.grid_cols)
                tile_h = (y_max - y_min) // rows if rows > 0 else 0
                tile_w = (x_max - x_min) // cols if cols > 0 else 0

                # Also try to get separator width from visual scene
                sep_w = 0
                if percept.visual_scene_dict:
                    tg_list = percept.visual_scene_dict.get('tile_grids', [])
                    if tg_list:
                        sep_w = tg_list[0].get('separator_width', 0)
                        # Use more precise tile dimensions if available
                        precise_tw = tg_list[0].get('tile_width', 0)
                        precise_th = tg_list[0].get('tile_height', 0)
                        precise_rows = tg_list[0].get('tile_rows', 0)
                        precise_cols = tg_list[0].get('tile_cols', 0)
                        if precise_tw > 0 and precise_th > 0:
                            tile_w = precise_tw
                            tile_h = precise_th
                        if precise_rows > 0:
                            rows = precise_rows
                        if precise_cols > 0:
                            cols = precise_cols

                if tile_w > 0 and tile_h > 0:
                    self._causal_map.set_tile_map(
                        bounds=(y_min, x_min, y_max, x_max),
                        rows=rows,
                        cols=cols,
                        tile_w=tile_w,
                        tile_h=tile_h,
                        sep_w=sep_w,
                    )

            # Forward goal cells to causal map so plan_to_goal() can work
            if percept.has_goal and percept.goal_cells:
                self._causal_map.set_goal(percept.goal_cells)
            if percept.current_cells:
                self._causal_map.set_current_state(percept.current_cells)

        # Record in cognitive frame
        cf.perception_summary = percept.summary()
        cf.panel_count = percept.panel_count
        cf.tile_count = percept.tile_count
        cf.goal_progress = percept.goal_progress
        cf.delta_count = len(percept.delta)
        cf.colors_present = sorted(percept.colors_present)
        cf.puzzle_type = percept.puzzle_type
        cf.spatial_confidence = percept.spatial_confidence
        cf.overall_confidence = percept.overall_confidence

        # ═══ GAP 1: Enrich with stable-region workspace detection ═══
        # If the perceiver's Channel 3 didn't find a goal (reference_panel
        # is None), use our frame-history approach to identify the workspace
        # and track modification coverage.
        if not percept.has_goal and self._stable_mask is not None:
            frame_array = self._perceiver._to_numpy(frame)
            if frame_array is not None:
                goal_total, cells_modified = self._compute_workspace_delta(
                    frame_array
                )
                if goal_total > 0:
                    cf.goal_cells_total = goal_total
                    cf.goal_cells_correct = cells_modified
                    cf.goal_completion = cells_modified / max(goal_total, 1)
                    cf.stable_region_detected = True
                    self._goal_cells_total = goal_total  # loop-level
                    # Update percept so downstream strategy can use it
                    percept.cells_total = goal_total
                    percept.cells_matching_goal = cells_modified
                    percept.goal_progress = cells_modified / max(goal_total, 1)
                    percept.has_goal = True
                    # Store delta count for strategy
                    cf.delta_count = goal_total - cells_modified
                    self._last_goal_delta_count = cf.delta_count

        # ═══ GAP 5: Detect agent position on first frame ═══
        if self._agent_position is None and 6 not in self._available_actions:
            # Movement-only game: try to detect agent position
            frame_array = self._perceiver._to_numpy(frame)
            if frame_array is not None:
                self._agent_position = self._detect_agent_position(frame_array)

        return percept

    def _think(
        self, percept: PerceptualField, cf: CognitiveFrame
    ) -> Tuple[str, float]:
        """
        PHASE 2: Phenomenological compression + strategy selection.

        Delegates to PhenomenologyLayer.compress() which produces a 5-D
        FeltState (valence, arousal, certainty, agency, salience) with
        momentum, hysteresis stabilization, and trace logging.  The
        FeltState is then injected back into the adapter so that the
        next cycle's compression is informed by the previous one (the
        consciousness-like feedback loop).

        Strategy is derived from FeltState + game-specific signals.
        """
        # Prepare loop-level state for the adapter
        recent_path: List[Any] = [
            (f.action_x, f.action_y)
            for f in self._frames[-5:]
            if f.action_x is not None
        ]
        loop_state: Dict[str, Any] = {
            "levels_completed": max(0, self._current_level - 1),
            "total_levels": 6,
            "max_actions": self._max_actions,
            "actions_taken": self._actions_taken,
            "recent_path": recent_path,
        }

        # Feed fresh perception into adapter -> PhenomenologyLayer
        self._bb_adapter.update(percept, loop_state)

        # Compress perception to 5-D FeltState
        felt: FeltState = self._phenomenology.compress()

        # Inject back for feedback loop (writes felt_* into adapter)
        self._phenomenology.inject(felt)

        # Derive action strategy from FeltState + game signals
        strategy = self._derive_strategy(
            felt, percept, _prior_loaded=self._prior_knowledge_loaded
        )

        # Track strategy history for stability computation
        self._bb_adapter._recent_strategies.append(strategy)
        if len(self._bb_adapter._recent_strategies) > 10:
            self._bb_adapter._recent_strategies = (
                self._bb_adapter._recent_strategies[-10:]
            )

        # Record on cognitive frame
        cf.thought_summary = (
            f"{felt.valence.value.upper()} | "
            f"certainty:{felt.certainty:.2f} | "
            f"strategy:{strategy}"
        )
        cf.valence = felt.valence.value  # Valence enum -> string
        cf.arousal = felt.arousal
        cf.certainty = felt.certainty
        cf.agency = felt.agency
        cf.salience = felt.salience
        cf.momentum = felt.momentum
        cf.dominant_contributors = list(felt.dominant_contributors)
        cf.information_gain = felt.compression_ratio
        cf.strategy = strategy

        # Try to get epistemic state from cognitive router
        if self._decision_system:
            try:
                router = getattr(self._decision_system, '_cognitive_router', None)
                if router and hasattr(router, 'epistemic_tracker'):
                    cf.epistemic_state = (
                        router.epistemic_tracker.current_state.primary_quadrant.name
                    )
            except Exception:
                pass

        return strategy, felt.certainty

    # ------------------------------------------------------------------
    # Strategy derivation from FeltState
    # ------------------------------------------------------------------

    def _derive_strategy(
        self,
        felt: FeltState,
        percept: PerceptualField,
        _prior_loaded: bool = False,
    ) -> str:
        """
        Derive action strategy from FeltState + game state.

        Strategy hierarchy (most to least committed):
          execute   - Plan exists, high certainty, favourable valence
          exploit   - Good understanding, use what we know
          experiment - Something is wrong, break out of local optimum
          explore   - Low understanding, gather information

        Enhanced with Gap 2C (goal-delta awareness) and
        Gap 5D (timer urgency awareness).
        """
        # ═══ ACTION MONOPOLY BREAKER ═══
        # If the same action has been repeated many times without level
        # progress, the rung system is stuck in a loop.  Force a strategy
        # change so the agent tries something different.
        if self._consecutive_same_action >= 8:
            # Escalating response: experiment first, then explore
            if self._consecutive_same_action >= 20:
                return "explore"   # Full reset — random walk
            return "experiment"    # Break the pattern

        # ═══ GAP 5D: Timer urgency override ═══
        # When the timer is critical, stop exploring — exploit what we know NOW.
        last_cf = self._frames[-1] if self._frames else None
        if last_cf is not None:
            if last_cf.timer_urgency == "critical":
                # No time left to explore — use whatever knowledge we have
                if percept.has_plan:
                    return "execute"
                return "exploit"

            # HUD state changed → something new happened in the environment.
            # Re-evaluate by experimenting (the world just shifted).
            if last_cf.hud_state_changed and felt.certainty < 0.7:
                return "experiment"

            # ═══ GAP 5C: Lives awareness ═══
            # If we detect lives and they're dropping, shift to exploit
            # (stop experimenting, use what we know before game over).
            if (getattr(last_cf, 'lives_remaining', -1) > 0
                    and getattr(last_cf, 'lives_remaining', -1) <= 1):
                if percept.has_plan:
                    return "execute"
                return "exploit"

            # Carried-state change (non-timer HUD changed, e.g. picked up key)
            # → something interesting happened, experiment to learn the effect
            if getattr(last_cf, 'carried_state_changed', False) and felt.certainty < 0.6:
                return "experiment"
        # EXECUTE: plan ready + confident + positive valence
        if (
            percept.has_plan
            and percept.map_completeness > 0.7
            and felt.valence in (Valence.OPPORTUNITY, Valence.STABILITY)
        ):
            return "execute"

        # Gap 2C: Goal-delta-aware strategy
        if percept.has_goal and percept.cells_total > 0:
            cells_remaining = percept.cells_total - percept.cells_matching_goal
            fraction_done = percept.cells_matching_goal / max(percept.cells_total, 1)

            # Close to goal -- exploit known causal rules to finish
            if cells_remaining <= 3 and percept.map_completeness > 0.2:
                return "exploit"

            # Far from goal and map is reasonably complete -- can plan
            if percept.map_completeness > 0.5 and fraction_done > 0.3:
                return "execute"

        # EXPERIMENT: bored / stuck / confidently threatened
        if felt.valence == Valence.BOREDOM:
            return "experiment"
        if felt.valence == Valence.THREAT and felt.certainty > 0.5:
            return "experiment"
        if percept.consecutive_no_change > 8:
            return "experiment"

        # With prior knowledge, we start with enough understanding to
        # use the rung system (experiment/exploit) rather than random explore.
        if _prior_loaded:
            # EXPLOIT: even modest map coverage suffices with prior knowledge
            if percept.map_completeness > 0.1 or felt.certainty > 0.2:
                return "exploit"
            # EXPERIMENT: we have knowledge, try applying it
            return "experiment"

        # EXPLOIT: medium-high certainty with some map coverage
        if felt.certainty > 0.5 and percept.map_completeness > 0.4:
            return "exploit"
        if felt.valence == Valence.OPPORTUNITY and felt.agency > 0.5:
            return "exploit"

        # EXPLORE: default -- gather information
        return "explore"

    def _consult_map(
        self,
        percept: PerceptualField,
        strategy: str,
        cf: CognitiveFrame,
    ) -> Optional[PlannedAction]:
        """
        PHASE 3: Consult the causal map for planned actions.

        If strategy is "execute" and we have a plan, return the next step.
        Otherwise, return None and let ACT decide.
        """
        if self._causal_map is None:
            cf.map_summary = "[MAP] No causal map"
            return None

        # Record map state
        cf.map_completeness = self._causal_map.completeness
        cf.effects_known = len(self._causal_map._effects)
        cf.positions_explored = len(self._causal_map._explored)
        cf.positions_total = len(self._causal_map._all_positions)
        cf.rules_discovered = [r.rule_type for r in self._causal_map._rules]
        cf.has_plan = self._causal_map.has_plan
        cf.plan_length = len(self._causal_map._plan)
        cf.plan_step = self._causal_map.plan_step
        cf.map_summary = self._causal_map.summary()

        # If strategy is execute and we have a plan, return next step
        if strategy == "execute":
            plan_action = self._causal_map.get_next_plan_action()
            if plan_action:
                return plan_action

            # Try to generate a plan
            plan = self._causal_map.plan_to_goal()
            if plan:
                return plan[0]

        return None

    def _movebias(self, _cands):
        """B2 (BUILD_PROGRAM_2 W1): banked movement affordances deprioritize
        actions with many observed no-op outcomes for this game+level — a
        bounded bias, never a veto (frontier.bias_moves weights, no removal).
        Loaded once per level through the frontier book; neutral without one."""
        try:
            from engines.egocentric.frontier import bias_moves
            _bk = getattr(self, "_ego_frontier_book", None)
            _lv = int(getattr(self, "_ego_level", 0) or 0)
            _mc = getattr(self, "_ego_moves_cache", None)
            if _bk is not None and (_mc is None or _mc[0] != _lv):
                _mc = (_lv, _bk.load_moves(
                    str(getattr(self, "_game_id", "") or "game"), _lv))
                self._ego_moves_cache = _mc
            return bias_moves(_cands, _mc[1] if _mc else {})
        except Exception:
            return list(_cands)

    def _nav_step_action(self):
        """[NAV] FIRST ACTIVATION (movement stack, rung 0c): GridNav's BFS
        next step as an ACTION NUMBER, or None. None unless the game shows
        mover-behavior (CursorAgency confident: ready(), >= 2 mapped
        directions currently available) AND a target exists — the abduced
        goal predicate's site when banked, else the nearest unexplored
        region. The wheel rule: a None changes NOTHING downstream, and this
        helper consumes no RNG."""
        ag = getattr(self, "_cursor_agency", None)
        nav = getattr(self, "_grid_nav", None)
        cell = getattr(self, "_nav_cell", None)
        if ag is None or nav is None or cell is None or not ag.ready():
            return None
        st = int(ag.stride() or 1) or 1
        dirs = {}
        for a, shift in ag.action_map().items():
            try:
                ai = int(a)
            except (TypeError, ValueError):
                continue
            u = ((shift[0] > 0) - (shift[0] < 0),
                 (shift[1] > 0) - (shift[1] < 0))
            if ai in self._available_actions and 1 <= ai <= 5 and u != (0, 0):
                dirs[u] = ai
        if len(dirs) < 2:
            return None
        # Target: the abduced-goal predicate site first (px x,y -> cell) ...
        goal = None
        gp = getattr(self, "_nav_goal_px", None)
        if gp is not None:
            try:
                goal = (int(round(int(gp[1]) / st)),
                        int(round(int(gp[0]) / st)))
            except (TypeError, ValueError, IndexError):
                goal = None
        if goal is None or goal == cell:
            # ... else the nearest unexplored region (bounded ring scan)
            shape = getattr(self, "_ego_frame_shape", None) or (64, 64)
            mr, mc = max(1, int(shape[0]) // st), max(1, int(shape[1]) // st)
            goal = None
            for rad in range(1, 9):
                ring = []
                for dr in range(-rad, rad + 1):
                    cols = ((-rad, rad) if abs(dr) != rad
                            else range(-rad, rad + 1))
                    for dc in cols:
                        cand = (cell[0] + dr, cell[1] + dc)
                        if (0 <= cand[0] < mr and 0 <= cand[1] < mc
                                and cand not in nav.visits):
                            ring.append(cand)
                if ring:
                    goal = min(ring, key=lambda c: (abs(c[0] - cell[0])
                                                    + abs(c[1] - cell[1]), c))
                    break
            if goal is None:
                return None
        d = nav.step_toward(cell, goal, list(dirs))
        return dirs.get(d) if d is not None else None

    def _act(
        self,
        percept: PerceptualField,
        strategy: str,
        certainty: float,
        plan_action: Optional[PlannedAction],
        obs: Any,
        agent_id: str,
        agent_role: str,
        w_A: float,
        w_B: float,
        cf: CognitiveFrame,
        **extra_context,
    ) -> Tuple[int, Optional[Dict]]:
        """
        PHASE 4: Three-speed action selection.

        SPEED 1 - MAPPED (fast): Execute plan step from causal map
        SPEED 2 - REASONED (medium): Use rung system with enriched context
        SPEED 3 - EXPLORE (slow): Maximize information gain
        """
        action_num: int = 1
        action_data: Optional[Dict] = None

        # ─── SPEED 1: MAPPED ─────────────────────────────────────────
        if plan_action is not None and strategy == "execute":
            pos = plan_action.position
            action_num = 6  # Click action
            action_data = {'x': pos[0], 'y': pos[1]}

            cf.action_speed = "mapped"
            cf.action_type = 6
            cf.action_x = pos[0]
            cf.action_y = pos[1]
            cf.action_reason = plan_action.reason
            cf.action_confidence = plan_action.confidence
            cf.action_summary = (
                f"MAPPED: Click ({pos[0]},{pos[1]}) | "
                f"plan step {plan_action.step_number + 1}/{cf.plan_length}"
            )

            # Advance the plan
            if self._causal_map:
                self._causal_map.advance_plan()

            return action_num, action_data

        # ─── SPEED 1b: MAPPED MOVEMENT (BFS pathfinding) ─────────────
        # For movement games with a known target, use BFS to find
        # shortest path avoiding known walls (Gap 3C).
        if (strategy == "execute"
                and self._causal_map
                and self._agent_position is not None
                and any(a in self._available_actions for a in (1, 2, 3, 4))
                and 6 not in self._available_actions):
            # Movement-only game: try BFS to an unvisited position
            visited = self._causal_map.get_visited_positions()
            # Pick an exploration target: nearest unvisited adjacent cell
            # or a known interesting position from perception
            target = None
            if percept.visual_scene_dict:
                # Try to reach an interesting detected object
                objects = percept.visual_scene_dict.get('objects', [])
                for obj in objects:
                    obj_pos = (obj.get('cx', 0), obj.get('cy', 0))
                    if obj_pos not in visited:
                        target = obj_pos
                        break

            if target is not None:
                path = self._causal_map.find_path_bfs(
                    self._agent_position, target
                )
                if path:
                    action_num = path[0]  # Take first step
                    cf.action_speed = "mapped"
                    cf.action_type = action_num
                    cf.action_reason = (
                        f"BFS path to ({target[0]},{target[1]}), "
                        f"{len(path)} steps"
                    )
                    cf.action_summary = (
                        f"MAPPED-BFS: ACTION{action_num}"
                        f" | target=({target[0]},{target[1]})"
                        f" | path_len={len(path)}"
                    )
                    return action_num, None

        # ─── SPEED 2: REASONED (delegate to rung system) ─────────────
        if self._decision_system is not None and strategy in ("exploit", "experiment"):
            try:
                # Build context for the rung system (backward compatible)
                context = self._build_rung_context(
                    percept, obs, agent_id, agent_role, w_A, w_B, **extra_context
                )

                result = self._decision_system.decide(obs, context)
                if isinstance(result, tuple):
                    action_str, reason = result
                    if isinstance(action_str, str) and action_str.startswith('ACTION'):
                        action_num = int(action_str.replace('ACTION', ''))
                    else:
                        action_num = random.choice(self._available_actions)

                    # Extract coordinates for ACTION6
                    if action_num == 6 and hasattr(self._decision_system, 'last_decision_metadata'):
                        metadata = self._decision_system.last_decision_metadata or {}
                        if 'pixel_position' in metadata:
                            px, py = metadata['pixel_position']
                            action_data = {'x': int(px), 'y': int(py)}
                        elif 'target' in metadata:
                            t = metadata['target']
                            action_data = {'x': int(t.get('x', 32)), 'y': int(t.get('y', 32))}
                        elif 'x' in metadata and 'y' in metadata:
                            action_data = {'x': int(metadata['x']), 'y': int(metadata['y'])}

                    cf.action_speed = "reasoned"
                    cf.action_type = action_num
                    cf.action_reason = reason[:100] if reason else "rung decision"
                    cf.rung_name = ""
                    if hasattr(self._decision_system, 'last_decision_metadata'):
                        md = self._decision_system.last_decision_metadata or {}
                        cf.rung_name = md.get('rung_name', md.get('rung', ''))
                        cf.fallback = _d8_fallback(md)     # D-8: rides beside rung_name
                        cf.action_confidence = md.get('confidence', 0.0)

                    if action_data:
                        cf.action_x = action_data.get('x')
                        cf.action_y = action_data.get('y')

                    cf.action_summary = (
                        f"REASONED: ACTION{action_num}"
                        + (f" @({cf.action_x},{cf.action_y})" if cf.action_x else "")
                        + (f" [{cf.rung_name}]" if cf.rung_name else "")
                    )

                    return action_num, action_data

            except Exception as e:
                logger.debug(f"[COGNITIVE-LOOP] Rung system failed: {e}")

        # ─── SPEED 3: EXPLORE (maximize information gain) ─────────────

        # --- 3a: Goal-guided exploration for click games ---
        # If we have goal awareness AND productive targets, rotate among
        # the top candidates to avoid fixating on one position.
        if self._causal_map and 6 in self._available_actions:
            productive = self._causal_map.get_productive_targets()
            if productive and self._goal_cells_total > 0:
                # G-D (PREREG_FINAL_GAPS): the lp arm may REORDER the explore
                # candidates toward large+compressible NOVEL residual sites —
                # steering only; fixed/random arms return them unchanged.
                if getattr(self, "_affect", None) is not None:
                    productive = self._affect.lp_steer(
                        productive, str(getattr(self, "_game_id", "") or "game"))
                # Rotate among the top productive positions. B5: starvation
                # widens the rotation window (bounded, STARVE_CEIL caps at x2).
                top_n = min(max(1, int(round(
                    3 * getattr(self, "_ego_explore_widen", 1.0)))),
                    len(productive))
                idx = self._productive_rotation_index % top_n
                self._productive_rotation_index += 1
                chosen_pos = productive[idx][0]
                rate = productive[idx][1]
                action_num = 6
                action_data = {'x': chosen_pos[0], 'y': chosen_pos[1]}

                cf.action_speed = "explore"
                cf.action_type = 6
                cf.action_x = chosen_pos[0]
                cf.action_y = chosen_pos[1]
                cf.action_reason = f"Guided: productive_rate={rate:.2f} [#{idx+1}/{top_n}]"
                cf.action_confidence = min(0.8, rate)
                cf.action_summary = (
                    f"EXPLORE-GUIDED: Click ({chosen_pos[0]},{chosen_pos[1]})"
                    f" | productive_rate={rate:.2f} [#{idx+1}/{top_n}]"
                )
                return action_num, action_data

        # --- 3b: Information-gain exploration for click games ---
        if self._causal_map and 6 in self._available_actions:
            target = self._causal_map.best_exploration_target()
            if target:
                action_num = 6
                action_data = {'x': target[0], 'y': target[1]}
                info_gain = self._causal_map.information_gain(target)

                cf.action_speed = "explore"
                cf.action_type = 6
                cf.action_x = target[0]
                cf.action_y = target[1]
                cf.action_reason = f"Explore: info_gain={info_gain:.2f}"
                cf.action_confidence = info_gain
                cf.information_gain = info_gain
                cf.action_summary = (
                    f"EXPLORE: Click ({target[0]},{target[1]})"
                    f" | info_gain={info_gain:.2f}"
                )
                return action_num, action_data

        # --- 3c: Perception-guided fallback for click games ---
        if 6 in self._available_actions:
            target_x, target_y = self._find_explore_target(percept)
            action_num = 6
            action_data = {'x': target_x, 'y': target_y}

            cf.action_speed = "explore"
            cf.action_type = 6
            cf.action_x = target_x
            cf.action_y = target_y
            cf.action_reason = "Explore: perception-guided"
            cf.action_confidence = 0.2
            cf.action_summary = (
                f"EXPLORE: Click ({target_x},{target_y})"
                " | perception-guided"
            )
            return action_num, action_data

        # --- 3c.5: Occasional pan for hybrid games (e.g. FT09) ---
        # Hybrid games have both click (6) and movement/pan (1-4) actions.
        # Sections 3a-3c always return clicks, so pan is never explored.
        # Periodically choose a pan action to discover other quadrants.
        movement_actions = [a for a in self._available_actions if a in (1, 2, 3, 4)]
        if movement_actions and 6 in self._available_actions:
            # Hybrid game: pan every 5th EXPLORE action
            if self._actions_taken % 5 == 0:
                action_num = random.choice(movement_actions)
                cf.action_speed = "explore"
                cf.action_type = action_num
                cf.action_reason = "Explore: pan to new quadrant (hybrid game)"
                cf.action_summary = (
                    f"EXPLORE-PAN: ACTION{action_num}"
                    f" | periodic quadrant discovery"
                )
                return action_num, None

        # --- 3d: Wall-avoiding exploration for movement-only games ---
        if movement_actions and self._causal_map:
            # ═══ [NAV] FIRST ACTIVATION (movement stack, rung 0c) ═══
            # CursorAgency confident + a target (abduced-goal site or nearest
            # unexplored region) -> GridNav's BFS next step steers the blind
            # draw. A BIAS under the wheel rule: blind explore stays
            # incumbent, the steer's share is capped at NAV_BIAS_P (<=0.5,
            # Register G GUESSED), never a veto; with no confidence this
            # block consumes NO RNG and the path stays byte-identical.
            try:
                _nava = self._nav_step_action()
                if (_nava is not None and _nava in movement_actions
                        and random.random() < NAV_BIAS_P):
                    self._nav_steers = int(
                        getattr(self, "_nav_steers", 0) or 0) + 1
                    cf.action_speed = "explore"
                    cf.action_type = _nava
                    cf.action_reason = "Explore: [NAV] gridnav step"
                    cf.action_summary = (
                        f"EXPLORE-NAV: ACTION{_nava}"
                        f" | cell={getattr(self, '_nav_cell', None)}")
                    print(f"[NAV] steer action={_nava} "
                          f"cell={getattr(self, '_nav_cell', None)} "
                          f"(p<={NAV_BIAS_P})")
                    return _nava, None
            except Exception:
                _swal(self, "OTHER")
            # Filter out known walls from current position
            pos = self._agent_position
            open_dirs = []
            unknown_dirs = []
            for a in movement_actions:
                if pos and self._causal_map.is_wall(pos, a):
                    continue  # skip known walls
                # Check if we know this direction is open
                if pos and (pos, a) in self._causal_map._open_paths:
                    open_dirs.append(a)
                else:
                    unknown_dirs.append(a)

            # Prefer unknown directions (exploration), then open ones.
            # B2: every blind draw passes through the banked-move bias.
            if unknown_dirs:
                action_num = random.choice(self._movebias(unknown_dirs))
                cf.action_reason = "Explore: unknown direction"
            elif open_dirs:
                action_num = random.choice(self._movebias(open_dirs))
                cf.action_reason = "Explore: open path"
            else:
                # All known walls from here - try any direction
                action_num = random.choice(self._movebias(movement_actions))
                cf.action_reason = "Explore: all-walls-retry"

            cf.action_speed = "explore"
            cf.action_type = action_num
            cf.action_summary = (
                f"EXPLORE-MOVE: ACTION{action_num}"
                f" | pos={pos} | {cf.action_reason}"
            )
            return action_num, None

        # Absolute fallback: random available action (B2: bias-weighted)
        action_num = random.choice(self._movebias(self._available_actions))
        cf.action_speed = "random"
        cf.action_type = action_num
        cf.action_reason = "random fallback"
        cf.action_summary = f"RANDOM: ACTION{action_num}"

        return action_num, action_data

    # ─── Context Bridge ───────────────────────────────────────────────

    def _find_explore_target(
        self, percept: PerceptualField
    ) -> tuple:
        """
        Find an interesting position to click based on perception.

        Uses multiple strategies in priority order:
        1. Object centroids from perception
        2. Tile positions from spatial analysis
        3. Positions with non-background colors
        4. Random position within interactive bounds
        """

        # Strategy 1: Click objects we haven't clicked yet
        # For click games, prefer small discrete objects (tiles/buttons) over
        # large background regions. Sort by size ascending so we try tiles first.
        if percept.objects:
            explored = set()
            if self._causal_map:
                explored = self._causal_map._explored
            sorted_objects = sorted(
                percept.objects,
                key=lambda o: o.get('size', 9999),
            )
            for obj in sorted_objects:
                cx = int(obj.get('centroid_x', obj.get('x', 0)))
                cy = int(obj.get('centroid_y', obj.get('y', 0)))
                if (cx, cy) not in explored and 0 < cx < 64 and 0 < cy < 64:
                    return (cx, cy)

        # Strategy 2: Use tile positions if available
        if percept.tile_count > 0 and percept.interactive_bounds:
            y_min, x_min, y_max, x_max = percept.interactive_bounds
            rows = max(1, percept.grid_rows)
            cols = max(1, percept.grid_cols)
            tile_h = (y_max - y_min) // rows
            tile_w = (x_max - x_min) // cols
            tiles = []
            for r in range(rows):
                for c in range(cols):
                    tx = x_min + c * tile_w + tile_w // 2
                    ty = y_min + r * tile_h + tile_h // 2
                    tiles.append((tx, ty))
            explored = set()
            if self._causal_map:
                explored = self._causal_map._explored
            unexplored = [t for t in tiles if t not in explored]
            if unexplored:
                return random.choice(unexplored)
            if tiles:
                return random.choice(tiles)

        # Strategy 3: Find non-background pixels in the frame
        if percept.frame is not None:
            try:
                arr = self._perceiver._to_numpy(percept.frame)
                if arr is not None:
                    nonzero = list(zip(*np.where(arr > 0)))
                    if nonzero:
                        # Sample a few and pick one not yet explored
                        sample = random.sample(nonzero, min(20, len(nonzero)))
                        explored = set()
                        if self._causal_map:
                            explored = self._causal_map._explored
                        for (y, x) in sample:
                            if (int(x), int(y)) not in explored:
                                return (int(x), int(y))
                        y, x = sample[0]
                        return (int(x), int(y))
            except Exception:
                pass

        # Strategy 4: Random position within interactive bounds or full frame
        if percept.interactive_bounds:
            y_min, x_min, y_max, x_max = percept.interactive_bounds
            return (random.randint(x_min, x_max), random.randint(y_min, y_max))

        return (random.randint(5, 58), random.randint(5, 58))

    def _build_rung_context(
        self,
        percept: PerceptualField,
        obs: Any,
        agent_id: str,
        agent_role: str,
        w_A: float,
        w_B: float,
        **extra_context,
    ) -> Dict[str, Any]:
        """
        Build a context dict compatible with the existing rung system.

        This bridges the new PerceptualField to the old 60-key context dict.
        Existing rungs continue to work unchanged.

        NEW: Adds 'percept' key with the full PerceptualField,
        so rungs that want structured perception can use it.
        """
        # Start with context_builder output if available
        context: Dict[str, Any] = {}

        if self._context_builder is not None:
            try:
                dc = self._context_builder.build_from_runner_state(
                    game_id=self._game_id,
                    obs=obs,
                    agent_id=agent_id,
                    agent_role=agent_role,
                    w_A=w_A,
                    w_B=w_B,
                    actions_taken=self._actions_taken,
                    max_actions=self._max_actions,
                    available_actions=self._available_actions,
                    win_levels=self._current_level - 1,
                    score=self._score,
                    **{k: v for k, v in extra_context.items()
                       if k in {
                           'last_action', 'recent_actions', 'last_frame_changed',
                           'failed_actions', 'score_delta', 'last_outcome',
                           'has_full_win', 'active_sequence', 'sequence_position',
                           'is_replay_mode', 'has_level_sequence', 'stuck_count',
                           'tried_colors', 'frame_hash', 'level_start_action_index',
                           'session_id', 'scorecard_id',
                       }},
                )
                context = dc.to_dict()
            except Exception as e:
                logger.debug(f"[COGNITIVE-LOOP] Context builder failed: {e}")

        # Enrich with structured perception
        context['percept'] = percept
        context['perceptual_field'] = percept.to_dict()
        context['causal_map'] = self._causal_map

        # Ensure visual_scene is populated (backward compat)
        if percept.visual_scene_dict and 'visual_scene' not in context:
            context['visual_scene'] = percept.visual_scene_dict

        # Ensure world_model is populated
        if 'world_model' not in context:
            context['world_model'] = {}
        if self._causal_map:
            context['world_model']['causal_map_typed'] = self._causal_map
            context['world_model']['map_completeness'] = self._causal_map.completeness

        # ═══ GAP 4D: Inject last-action outcome so rungs can read it ═══
        # Rungs can use these to adjust confidence: a rung whose last
        # suggestion was_destructive should lower its confidence.
        last_cf = self._frames[-1] if self._frames else None
        if last_cf is not None:
            context['last_was_productive'] = last_cf.was_productive
            context['last_was_destructive'] = last_cf.was_destructive
            context['last_was_wasted'] = last_cf.was_wasted
            context['last_was_neutral'] = last_cf.was_neutral
            context['last_goal_progress_delta'] = last_cf.goal_progress_delta
            context['last_pixels_changed'] = last_cf.pixels_changed
        # ═══ GAP 5D: Inject timer/HUD state for strategy-aware rungs ═══
        context['timer_urgency'] = getattr(last_cf, 'timer_urgency', 'safe') if last_cf else 'safe'
        context['hud_state_changed'] = getattr(last_cf, 'hud_state_changed', False) if last_cf else False

        # ═══ GAP 5C: Inject semantic HUD state for rungs ═══
        if last_cf is not None:
            context['carried_state'] = getattr(last_cf, 'carried_state', {})
            context['carried_state_changed'] = getattr(last_cf, 'carried_state_changed', False)
            context['lives_remaining'] = getattr(last_cf, 'lives_remaining', -1)
            context['hud_region_changes'] = getattr(last_cf, 'hud_region_changes', {})

        # ═══ Semantic goal matching: inject reference panel awareness ═══
        if last_cf is not None and getattr(last_cf, 'reference_panel_detected', False):
            context['reference_panel_detected'] = True
            context['goal_match_fraction'] = getattr(last_cf, 'goal_match_fraction', 0.0)
            context['goal_match_cells'] = getattr(last_cf, 'goal_match_cells', 0)
            context['goal_mismatch_cells'] = getattr(last_cf, 'goal_mismatch_cells', 0)

        return context

    # ─── Replay Access ────────────────────────────────────────────────

    def get_replay(self) -> List[CognitiveFrame]:
        """Get all cognitive frames from this game session."""
        return self._frames

    def print_replay(self, start: int = 0, end: Optional[int] = None):
        """Print replay to console in dashboard format."""
        frames = self._frames[start:end]
        for cf in frames:
            print(cf.to_dashboard())
            print()

    def print_log(self, start: int = 0, end: Optional[int] = None):
        """Print replay to console in single-line log format."""
        frames = self._frames[start:end]
        for cf in frames:
            print(cf.to_log_line())

    @property
    def causal_map(self) -> Optional[CausalMap]:
        """Access the causal map for external inspection."""
        return self._causal_map


# =============================================================================
# W1 FALSIFIER ARMS -- THE CONSUMPTION HELPERS (PREREG_W1_NARRATION.md,
# "ARM C's CONSUMPTION MUST BE REAL"). Defined at MODULE BOTTOM deliberately:
# runtime name lookup does not need definition-before-use, and appending here
# moves NO existing receipt line in record/canon/WIRING_REGISTRY.md and NO window-law
# anchor offset (the record_result .credit/.route windows have <60 chars of
# headroom). Every helper is arm-gated: on arm W (or a loop with no arm
# state) it returns its inert value BEFORE touching any state, so arm W is
# byte-identical to today -- the consumption code paths are never reached.
# =============================================================================


def _narr_expected_bin(loop, slot):
    """WIRE 1 source (ARM C ONLY): the immediately-prior BET narration
    record's stated expected bin for this slot, read from the NarrationSpine's
    IN-MEMORY last-bet state (never the JSONL on the hot path). The bet's
    slots name what it staked; its bin field is the stated expectation for
    every staked slot (predict_bin). The router consults the value ONLY
    inside AMBIGUOUS_BAND of its eps threshold (engines/egocentric/router.py
    -- the WIRE 1 decision point). Arm W: None, always -- the router's
    consumption branch is structurally unreachable."""
    try:
        from engines.egocentric import narration as _na
        if getattr(loop, "_narr_arm", None) != _na.ARM_C:
            return None
        _lb = getattr(getattr(loop, "_narration", None), "last_bet", None)
        if not _lb or str(slot) not in (_lb.get("slots") or ()):
            return None
        return _lb.get("bin")
    except Exception:
        return None


def _narr_sig(pre, post, action):
    """WIRE 2's key: the mint's own coarse transition signature (the
    support-count key), computed READ-ONLY at the offer seam via the same
    static hash the mint uses -- same bytes, no mint state touched. None when
    no cell changed or anything is malformed (no signature exists there)."""
    try:
        from engines.egocentric.mint import MDLMint
        _b = np.asarray(pre)
        _a = np.asarray(post)
        if (_b.shape != _a.shape or _b.ndim != 2 or _b.size == 0
                or not bool((_b != _a).any())):
            return None
        return MDLMint._signature(_b, _a, int(action))
    except Exception:
        return None


def _narr_seen(loop, sig, action):
    """The current support count for a transition signature -- the mint's
    (game, level, action, signature) seen-counter, read without bumping it.
    This IS the guard input WIRE 2 compares: 'support count same' means this
    number equals the one retained on the last MINT narration record."""
    _mint = getattr(loop, "_mdl_mint", None)
    if _mint is None:
        return 0
    _g = str(getattr(loop, "_game_id", "") or "game")
    _lv = int(getattr(loop, "_ego_level", 0) or 0) + 1
    return int(getattr(_mint, "_seen", {}).get((_g, _lv, int(action), sig), 0))


def _narr_mint_skip(loop, pre, post, action, route) -> bool:
    """WIRE 2 decision point (ARM C ONLY): MINT consumes its own guard-zero
    history. True (= withhold the offer this cycle) iff the LAST narration
    MINT record for this transition signature (NarrationSpine.last_mint --
    in-memory, never a JSONL re-read) named a guard as the zero AND that
    guard's input has not changed: support count same, offer route same. The
    skip is itself narrated at the MINT point with reason "guard-zero
    unchanged" and the consumed record's id (the stash below; _narr_close
    emits it). Arm W: False before touching anything -- every cycle
    re-offers, byte-identical to today. Containment: never raises; any
    failure re-offers (fails open toward today's behaviour)."""
    try:
        from engines.egocentric import narration as _na
        if getattr(loop, "_narr_arm", None) != _na.ARM_C:
            return False
        _nsp = getattr(loop, "_narration", None)
        if _nsp is None:
            return False
        sig = _narr_sig(pre, post, action)
        if sig is None:
            return False
        rec = (getattr(_nsp, "last_mint", None) or {}).get(sig)
        if not rec or not rec.get("guard_zero"):
            return False
        support = _narr_seen(loop, sig, action)
        if (support != int(rec.get("support") or 0)
                or route != rec.get("route")):
            return False        # the narrated zero's input changed: re-offer
        loop._narr_mint = {"verdict": "skip",
                           "reason": "guard-zero unchanged",
                           "consumed": rec.get("id"),
                           "guard_zero": rec.get("guard_zero")}
        loop._narr_mint_sig = {"sig": sig, "support": support, "route": route}
        print(f"[MINT] skip reason=guard-zero-unchanged route={route} "
              f"consumed={rec.get('id')}")
        return True
    except Exception:
        _swal(loop, "MINT_DRAIN")
        return False


def _narr_mint_mark(loop, pre, post, action, route) -> None:
    """WIRE 2's retention half (ARM C ONLY): after a REAL offer, stash the
    offer's signature + post-offer support count + route so this step's MINT
    narration record carries them and the spine retains the (guard-zero,
    guard-input) pair for the next cycle's skip decision. Arm W: no-op -- no
    extra fields on any record, no retained state, streams byte-identical to
    today. Containment: never raises."""
    try:
        from engines.egocentric import narration as _na
        if getattr(loop, "_narr_arm", None) != _na.ARM_C:
            return
        sig = _narr_sig(pre, post, action)
        if sig is None:
            return
        loop._narr_mint_sig = {"sig": sig,
                               "support": _narr_seen(loop, sig, action),
                               "route": route}
    except Exception:
        _swal(loop, "MINT_DRAIN")


# ═════════════════════════════════════════════════════════════════════════════
# COMPOSER STAGE 3 (PROPOSAL_COMPOSER_DESIGN.md par.3/6.3): the compose
# fallback's loop-side seam. Appended at MODULE BOTTOM (the ARM build's
# pattern) so the helper block itself moves no registry receipt.
# ═════════════════════════════════════════════════════════════════════════════


def _w3c_want_cells(pframe, refsnap):
    """The reference WANT as CELLS -- the SAME diff the planner just searched
    (compute_d's mask, kept cellwise instead of counted): every cell where
    the workspace differs from the reference, target = the reference's value.
    [] on any doubt (shape mismatch, unreadable arrays): no WANT is never an
    invented WANT. (row, col, target) triples, row-major."""
    try:
        ws, ref = np.asarray(pframe), np.asarray(refsnap)
        if ws.ndim != 2 or ws.shape != ref.shape:
            return []
        return [(int(r), int(c), int(ref[r, c]))
                for r, c in np.argwhere(ws != ref)]
    except Exception:
        return []


def _w3c_compose(loop, pframe, want):
    """THE ONE compose_attempt CALL SITE (COMPOSER STAGE 3). Reached ONLY
    from cycle()'s two plan seams, ONLY inside an open W2b gate (_w2b_engage
    True -- no new scheduling), ONLY after the planner's search returned
    None (the fallback ordering: a found plan means no compose attempt).
    Assembles the loop-held inputs -- Gamma, the self-locus cell (row, col):
    the observer's EXACT cell where the body is a single cell (stage 4.5,
    token self-cell), else the rounded centroid as the STATED fallback
    (token centroid-rounded, on the PLAN record), the action book's deltas
    (enables.book_deltas), the frontier mask (enables.fatal_cells, the one
    (x, y) -> (row, col) conversion) -- and narrates the outcome at the PLAN
    point via the W2b channel (loop._w2b_narr): mode "composed" with the
    composite id (+ its citation state: settled False -- stage 4; + the
    avatar source and, for a reach chain, the prefix verdict), or
    "compose-none" with the attempt's fixed reason token. The composite is
    a CANDIDATE: nothing here cites it; stage 4's _w3d_drive may DRIVE it
    (the test), and only the live settle makes it citable. Returns the
    attempt's result dict on a compose, else None. Containment: never
    raises; an internal error narrates nothing new and changes nothing."""
    try:
        from engines.egocentric import composer as _cmp
        from engines.egocentric import enables as _en
        _gm = getattr(loop, "_gamma", None)
        if _gm is None:
            return None
        _g = str(getattr(loop, "_game_id", "") or "game")
        _lv = int(getattr(loop, "_ego_level", 0) or 0)
        _cell = getattr(loop, "_ego_self_cell", None)
        _cen = getattr(loop, "_ego_prev_centroid", None)
        if _cell is not None:
            _av, _src = (int(_cell[0]), int(_cell[1])), _cmp.AVATAR_EXACT
        elif _cen is not None:
            _av = (int(round(_cen[0])), int(round(_cen[1])))
            _src = _cmp.AVATAR_CENTROID          # the stated fallback
        else:
            _av, _src = None, _cmp.AVATAR_NONE
        _bk = getattr(loop, "_ego_frontier_book", None)
        _res = _cmp.compose_attempt(
            want, pframe, _gm, _av, _en.book_deltas(_g),
            (_en.fatal_cells(_bk, _g, _lv) if _bk is not None else set()),
            _g, _lv + 1,
            # W2c: the ONE memo the planner shares (None = the undo)
            retained=getattr(getattr(loop, "_w2b_sched", None), "retained", None))
        _res["avatar"] = _src
        if _res.get("composite"):
            _extra = {"settled": False, "driven": False, "avatar": _src}
            if _res.get("prefix") is not None:
                _extra["prefix"] = str(_res["prefix"])
            loop._w2b_narr = ("composed", str(_res["composite"]), _extra)
            print(f"[PLAN] composed id={_res['composite']} "
                  f"parts={len(_res.get('chain') or [])} "
                  f"price={_res.get('price')} avatar={_src} "
                  f"prefix={_res.get('prefix')} "
                  f"refused={len(_res.get('refused') or [])}")
            return _res
        loop._w2b_narr = ("compose-none", str(_res.get("reason")))
        print(f"[PLAN] compose-none reason={_res.get('reason')} "
              f"candidates={_res.get('candidates')} "
              f"proposed={_res.get('proposed')} "
              f"verified={_res.get('verified')} "
              f"refused={_res.get('refused')} notes={_res.get('notes')} "
              f"avatar={_src}")
        return None
    except Exception:
        _swal(loop, "PLANNER")
        return None


# ═════════════════════════════════════════════════════════════════════════════
# COMPOSER STAGE 4 (PREREG_COMPOSER_STAGE4_SETTLEMENT.md): THE SETTLEMENT
# WIRE's loop-side seams. Appended at MODULE BOTTOM (the ARM build's pattern)
# so the helper block itself moves no registry receipt.
#
#   _w3d_drive     the DRIVE: a CANDIDATE composite drives under the planner's
#                  OWN gates (verified x2-TRANSFERRED per part, site, frontier
#                  veto -- the same three the plan_to_identity path applies);
#                  g7 and drive increment on THE SAME self._plan_gate dict the
#                  planner path increments (one counter, asserted by identity
#                  in tests/gate/test_composer_stage4.py F4).
#   _w3d_continue  the multi-cycle chain: each later part issues ONLY if the
#                  live frame's state key equals the predicted one (else the
#                  abort router says world-moved: chain dropped, no penalty).
#   _w3d_settle    the ONE live_settle call site: after the last part, the
#                  LIVE frame vs the predicted frame on the WANT cells and
#                  every predicted cell -> settled (superseding append) or
#                  routed plan-wrong on the MISPREDICTING component via the
#                  mint's conflict/reinstate path. Nothing deleted.
# Each driven part rides the EXISTING _w2b_driven stash (key = the state key
# the part bet on, steps = [the part]) exactly as a planner step does;
# _w3d_settle consumes composite stashes before _w2b_abort sees them.
# ═════════════════════════════════════════════════════════════════════════════


def _w3d_site(pframe, atom, anchor):
    """The click site (x, y) for a Gamma part on `pframe`: the RECONCILED
    anchor (the cell the reach chose and the simulation stamped at --
    carried per part on the drive record, stage 4.5) + the stored
    act_offset (stage 2's stamp, the cell the action was actually performed
    at). None when the atom carries NO act_offset (compose-only: the
    NO-ACT-OFFSET composite is never driven from a synthesised site), when
    no anchor was reconciled, or when that anchor no longer matches on the
    frame the part faces. No site is never a guessed site -- the patch-
    centre convention is gone from this seam."""
    try:
        from engines.egocentric import composer as _cmp
        from engines.egocentric import enables as _en
        off = _en.act_offset_of(atom)
        if off is None or anchor is None:
            return None
        a = (int(anchor[0]), int(anchor[1]))
        if a not in _cmp._anchors(np.asarray(pframe), atom):
            return None
        return (int(a[1] + off[1]), int(a[0] + off[0]))
    except Exception:
        return None


def _w3d_offsetless(loop, drive):
    """The click parts (action 6) of a driven chain that carry NO act_offset
    -- the composite is then compose-only (NO-ACT-OFFSET): it is shadowed,
    never driven. [] when every click part carries its offset."""
    from engines.egocentric import enables as _en
    _gm = getattr(loop, "_gamma", None)
    out = []
    for _pid in drive["chain"]:
        atom = _gm.get(_pid) if _gm is not None else None
        if not isinstance(atom, dict):
            continue
        try:
            is_click = int(atom.get("action")) == 6
        except (TypeError, ValueError):
            is_click = False
        if is_click and _en.act_offset_of(atom) is None:
            out.append(str(_pid))
    return out


def _w3d_step(loop, pframe, drive, i):
    """(action_num, action_data) for part i of a driven chain on `pframe`:
    the part atom's own action; a click (6) needs its site resolved on the
    frame it faces AT THE RECONCILED ANCHOR (drive["anchors"][i]), a
    movement carries no coordinates. None when the part cannot be issued."""
    try:
        _gm = getattr(loop, "_gamma", None)
        atom = _gm.get(drive["chain"][i]) if _gm is not None else None
        if not isinstance(atom, dict) or atom.get("kind") != "EFFECT":
            return None
        act = int(atom.get("action"))
        if act == 6:
            _anchors = drive.get("anchors") or []
            site = _w3d_site(pframe, atom,
                             (_anchors[i] if i < len(_anchors) else None))
            if site is None:
                return None
            return (6, {'x': int(site[0]), 'y': int(site[1])})
        return (act, None)
    except Exception:
        return None


def _w3d_narrate(loop, mode, gate, extra):
    """A PLAN-point record at record_result time (the abort router's own
    idiom in _w2b_abort): mode + gate + the composite's state."""
    _nsp = getattr(loop, "_narration", None)
    if _nsp is not None:
        _rng, _cc = _narr_range(loop)
        _nsp.plan(str(mode), gate, rng=_rng, col_class=_cc, extra=extra)


def _w3d_abort(loop, chain, route, fact, component, pre_frame):
    """Apply a routed failure to a driven composite through the EXISTING
    machinery only: PlannerScheduler.on_abort (world-moved drops GATE B's
    retained key, penalises nothing; plan-wrong ledgers the mispredicting
    component), composer.conflict_component for plan-wrong (the mint's
    reinstate path, on THAT component only), the PLAN-point narration with
    the discriminator. The chain is dropped; the composite stays a
    CANDIDATE -- nothing is deleted."""
    from engines.egocentric import composer as _cmp
    from engines.egocentric import scheduler as _s2b
    loop._w3d_chain = None
    _cid = chain["drive"]["composite"]
    _sch = getattr(loop, "_w2b_sched", None)
    _steps = [str(component)] if component else []
    if _sch is not None:
        _sch.on_abort(route, str(getattr(loop, "_game_id", "") or "game"),
                      int(getattr(loop, "_ego_level", 0) or 0), _steps)
    _conf = None
    if route == _s2b.ABORT_PLAN_WRONG and component:
        _conf = _cmp.conflict_component(getattr(loop, "_mdl_mint", None),
                                        getattr(loop, "_gamma", None),
                                        str(component), pre_frame)
    # R3/R4: the SAME `steps` + `ep` pair the planner's abort record carries,
    # so one reader reads both paths. The stage-4 plan-wrong ALSO wrote a
    # ctx_conflict just above -- that append is stamped via="plan-wrong" and
    # is counted under m1 only: one event, one count.
    _ep = _std_ep(loop)
    _extra = {"composite": _cid, "settled": False,
              "component": (str(component) if component else None),
              "conflict": _conf, "steps": _steps}
    if _ep is not None:
        _extra["ep"] = int(_ep)
    _w3d_narrate(loop, "abort", route, _extra)
    print(f"[PLAN] composite abort routed={route} id={_cid} "
          f"component={component} ({fact})")


def _w3d_drive(loop, pframe, res):
    """THE DRIVE (stage 4, wire 1): a CANDIDATE composite just minted by
    _w3c_compose drives under the planner's OWN three gates -- verified
    (every part atom carries >= 2 TRANSFERRED settlements, the salience bar
    self._atom_verified), site (the final Gamma part's click site resolves
    on the frame the simulation says it will face), frontier veto
    (frontier.plan_veto on that site) -- and the first part issues THIS
    cycle. Driving IS the plan rung firing: g7 and drive increment on the
    SAME self._plan_gate dict the plan_to_identity path increments (one
    counter; no parallel). The chain continuation is stashed on
    loop._w3d_chain; the part rides the existing _w2b_driven stash. Anything
    short of the gates is shadow-narrated (the composite stays a candidate,
    un-driven). Returns (action_num, action_data) or None; never raises."""
    try:
        from engines.egocentric import composer as _cmp
        from engines.egocentric import scheduler as _s2b
        if not hasattr(loop, "_plan_gate") or loop._plan_gate is None:
            loop._plan_gate = {"g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0,
                               "g6": 0, "g7": 0, "shadow": 0, "drive": 0,
                               "cycles": 0}
        _pg = loop._plan_gate                  # THE planner path's counter dict
        _src = (res.get("avatar") if isinstance(res, dict) else None)
        drive = _cmp.drive_record(res)
        if drive is None:
            if isinstance(res, dict) and res.get("reason") == _cmp.COMPOSED:
                # a composed result whose prediction is malformed (no frame
                # per part, no WANT to verify, a predicate already true):
                # stated on the PLAN record, never driven
                _pg["shadow"] = int(_pg.get("shadow", 0) or 0) + 1
                loop._w2b_narr = ("composed", str(res.get("composite")),
                                  {"settled": False, "driven": False,
                                   "reason": "drive-record-malformed",
                                   "avatar": _src})
                print(f"[PLAN] composite shadow id={res.get('composite')} "
                      f"reason=drive-record-malformed")
            return None
        _cid = drive["composite"]
        _n = len(drive["chain"])
        _prefix = drive.get("prefix")
        # STAGE 4.5 (silent #3): an offset-less click part is compose-only
        _offless = _w3d_offsetless(loop, drive)
        if _offless:
            _pg["shadow"] = int(_pg.get("shadow", 0) or 0) + 1
            loop._w2b_narr = ("composed", _cid,
                              {"settled": False, "driven": False,
                               "reason": _cmp.NO_ACT_OFFSET,
                               "parts": list(_offless), "avatar": _src,
                               "prefix": _prefix})
            print(f"[PLAN] composite shadow id={_cid} parts={_n} "
                  f"reason={_cmp.NO_ACT_OFFSET} offset-less={_offless}")
            return None
        _av = getattr(loop, "_atom_verified", None) or {}
        _verified = all(int(_av.get(_pid, 0) or 0) >= 2 for _pid in drive["chain"])
        _gm = getattr(loop, "_gamma", None)
        _last = _gm.get(drive["chain"][-1]) if _gm is not None else None
        _pre_last = drive["frame0"] if _n == 1 else drive["frames"][-2]
        _site = _w3d_site(_pre_last, _last, drive.get("anchor"))
        from engines.egocentric.frontier import plan_veto
        _fb = getattr(loop, "_ego_frontier_book", None)
        _lv = int(getattr(loop, "_ego_level", 0) or 0)
        _g = str(getattr(loop, "_game_id", "") or "game")
        _veto = plan_veto(
            _site, (getattr(loop, "_ego_harvest_cache", None) or {}).get(_lv),
            avoid=(_fb.avoid_set(_g, _lv) if _fb is not None else None))
        _step = (_w3d_step(loop, pframe, drive, 0)
                 if (_verified and _site is not None and not _veto) else None)
        if _step is None:
            _pg["shadow"] = int(_pg.get("shadow", 0) or 0) + 1
            loop._w2b_narr = ("composed", _cid,
                              {"settled": False, "driven": False,
                               "verified": bool(_verified),
                               "site": _site is not None, "veto": bool(_veto),
                               "avatar": _src, "prefix": _prefix})
            print(f"[PLAN] composite shadow id={_cid} parts={_n} "
                  f"verified={_verified} site={_site} veto={_veto}")
            return None
        _pg["g7"] = int(_pg.get("g7", 0) or 0) + 1      # the plan rung fired
        _pg["drive"] = int(_pg.get("drive", 0) or 0) + 1
        loop._w3d_chain = {"drive": drive, "cursor": 0, "game": _g,
                           "level": _lv}
        loop._w2b_driven = {"key": _s2b.state_key(pframe),
                            "steps": [drive["chain"][0]],
                            "composite": _cid, "step": 0}
        loop._w2b_narr = ("composed", _cid,
                          {"settled": False, "driven": True, "step": 0,
                           "of": _n, "avatar": _src, "prefix": _prefix})
        print(f"[PLAN] DRIVE composite id={_cid} parts={_n} step=0/{_n} "
              f"action={_step[0]} site={_site} anchor={drive.get('anchor')} "
              f"prefix={_prefix}")
        return _step
    except Exception:
        _swal(loop, "PLANNER")
        return None


def _w3d_continue(loop, frame):
    """THE MULTI-CYCLE CHAIN (stage 4): a composite drive in progress issues
    its next part -- ONLY if the live frame's state key equals the key of
    the frame the simulation predicted for this point (the planner's own
    key, scheduler.state_key). A differing key is the abort router's
    world-moved: the chain is dropped without penalty and narrated. Each
    issued part re-stashes _w2b_driven (key = the predicted pre-state's
    key, steps = [the part]) so _w3d_settle routes it like the first.
    Returns (action_num, action_data) or None; never raises."""
    try:
        chain = getattr(loop, "_w3d_chain", None)
        if chain is None:
            return None
        from engines.egocentric import scheduler as _s2b
        drive = chain["drive"]
        i = int(chain["cursor"])
        _n = len(drive["chain"])
        if i <= 0 or i >= _n:
            loop._w3d_chain = None             # nothing pending
            return None
        pframe = loop._perceiver._to_numpy(frame)
        if pframe is None:
            return None
        _pred_pre = drive["frames"][i - 1]
        _rt = _s2b.route_abort(_s2b.state_key(_pred_pre),
                               _s2b.state_key(pframe))
        if _rt["route"] == _s2b.ABORT_WORLD_MOVED:
            _w3d_abort(loop, chain, _rt["route"], _rt["fact"], None, pframe)
            return None
        _step = _w3d_step(loop, pframe, drive, i)
        if _step is None:
            loop._w3d_chain = None
            _w3d_narrate(loop, "abort", "could-not-issue",
                         {"composite": drive["composite"], "settled": False,
                          "component": None, "part": i,
                          "reason": "could-not-issue"})
            print(f"[PLAN] composite step {i}/{_n} could not issue; "
                  f"id={drive['composite']} dropped (candidate intact)")
            return None
        loop._w2b_driven = {"key": _s2b.state_key(_pred_pre),
                            "steps": [drive["chain"][i]],
                            "composite": drive["composite"], "step": i}
        loop._w2b_narr = ("composite-drive", drive["composite"],
                          {"settled": False, "driven": True, "step": i,
                           "of": _n})
        print(f"[PLAN] DRIVE composite id={drive['composite']} "
              f"step={i}/{_n} action={_step[0]}")
        return _step
    except Exception:
        _swal(loop, "PLANNER")
        return None


def _w3d_settle(loop, post_array, level_changed):
    """THE SETTLE SEAM (stage 4, wire 2 + 3): the ONE live_settle call site.
    Consumes a COMPOSITE drive stash only (a planner stash is left for
    _w2b_abort untouched). After part i landed: the LIVE post-frame vs the
    predicted frame after part i on every cell the chain predicted so far
    (composer.divergence). No divergence -> the chain advances; after the
    LAST part composer.live_settle writes settled: True (the superseding
    append) and narrates "settled". A divergence -> scheduler.route_abort on
    (the key the part bet on, the live pre-frame's key): plan-wrong (the
    state was as predicted, the prediction failed) -> ctx_conflict on the
    mispredicting component ONLY via the mint's reinstate path, the
    composite unsettled; world-moved -> candidate intact, no penalty. A
    level change drops the chain (the board redrew; the candidate stays).
    Simulation never reaches this seam's writer: only the live frame does.
    Containment: never raises."""
    try:
        _dr = getattr(loop, "_w2b_driven", None)
        if not isinstance(_dr, dict) or "composite" not in _dr:
            return                              # the planner's stash: not ours
        loop._w2b_driven = None                 # consumed here, once
        chain = getattr(loop, "_w3d_chain", None)
        if chain is None or chain["drive"]["composite"] != _dr["composite"]:
            return
        from engines.egocentric import composer as _cmp
        from engines.egocentric import scheduler as _s2b
        drive = chain["drive"]
        i = int(_dr.get("step", chain["cursor"]))
        _n = len(drive["chain"])
        if level_changed:
            loop._w3d_chain = None
            _w3d_narrate(loop, "abort", _s2b.ABORT_WORLD_MOVED,
                         {"composite": drive["composite"], "settled": False,
                          "component": None, "reason": "level-changed"})
            print(f"[PLAN] composite chain dropped on level change "
                  f"id={drive['composite']} (candidate intact)")
            return
        v = _cmp.divergence(drive, i, post_array)
        if v["diverged"]:
            _pf = getattr(loop, "_prev_frame", None)
            _obs = (_s2b.state_key(_pf) if _pf is not None
                    else str(_dr.get("key")))
            _rt = _s2b.route_abort(str(_dr.get("key")), _obs)
            _w3d_abort(loop, chain, _rt["route"], _rt["fact"],
                       (v["component"] if _rt["route"] == _s2b.ABORT_PLAN_WRONG
                        else None), _pf)
            return
        if i < _n - 1:
            chain["cursor"] = i + 1             # the chain continues next cycle
            return
        loop._w3d_chain = None
        # R3/R4: the settle append carries the episode ordinal -- the
        # CANDIDATE -> SETTLED transition is the composite's earn event (e3).
        _res = _cmp.live_settle(getattr(loop, "_gamma", None), drive,
                                post_array, ep=_std_ep(loop))
        _w3d_narrate(loop, "settled" if _res["settled"] else "abort",
                     drive["composite"] if _res["settled"] else _res["reason"],
                     {"composite": drive["composite"],
                      "settled": bool(_res["settled"]), "reason": _res["reason"]})
        print(f"[PLAN] composite settle id={drive['composite']} "
              f"settled={_res['settled']} reason={_res['reason']}")
    except Exception:
        _swal(loop, "PLANNER")


def _d8_fallback(md) -> bool:
    """D-8 (PREREG_D8_FALLBACK_INSTRUMENT.md): the loop's ONE read of the rung
    system's ``weighted_fallback`` flag -- it rides beside rung_name onto cf in
    cycle()'s REASONED block and from there onto the ACT narration record in
    _narr_bet. A strict bool: a strategy that never reaches the cognitive
    router leaves the key absent and that reads False, never unknown. Module
    bottom by the registry's placement law (moves no receipt)."""
    try:
        return bool((md or {}).get("weighted_fallback", False))
    except Exception:
        return False


# ═════════════════════════════════════════════════════════════════════════════
# THE PERSISTENCE MONITOR (PREREG_PERSISTENCE_MONITOR.md): the loop-side seam.
# Placed directly ABOVE _gate_step, which tests/gate/test_gate_stage1.py pins
# as the module's LAST function; the only receipts this block moves are the
# two gate-step rows below it, refreshed by grep in record/canon/WIRING_REGISTRY.md.
# ═════════════════════════════════════════════════════════════════════════════


def _pm_attach(loop, nsp) -> None:
    """THE ONE ATTACH SITE (called from _narr_bet, every step, O(1) after the
    first). Ensures the spine carries a PersistenceMonitor -- constructed ONCE
    per spine and PRIMED from the agent's own narration stream (the single
    O(stream) read, once per game/spine, never per record: the spine's
    observer hook feeds it in memory from here on) -- and hands the SAME
    monitor to the affect gains, so the `persist` channel reads the live fold
    (AffectGains is built lazily in record_result, after the first bet; the
    handoff lands on the next step, when a run can first exist). Containment:
    never raises; a failure leaves the spine unmonitored -- the records are
    unchanged and the channel reads 0."""
    try:
        if getattr(nsp, "monitor", None) is None:
            from engines.egocentric.persistence import PersistenceMonitor
            nsp.monitor = PersistenceMonitor.from_fabric(nsp.fabric)
        _aff = getattr(loop, "_affect", None)
        if _aff is not None and getattr(_aff, "monitor", None) is not nsp.monitor:
            _aff.monitor = nsp.monitor
    except Exception:
        _swal(loop, "OTHER")


def _gate_step(loop, action_num, cf, nsp, frame) -> None:
    """REASONING GATE STAGE 1 -- SHADOW (PREREG_GATE_STAGE1_SHADOW.md): THE ONE
    HOOK, a void call beside the spine's act() in _narr_bet. Assembles the
    utterance-builder's AGENT STATE from what the loop already holds (the
    opener it perceives, the previous frame it tracked, the plan/composite
    atoms it drove, the frontier book, the bank's last settlement, its
    reference snapshot, the action book as its own citable ledger) and the
    gate's LEDGER (Gamma, the fatal set, the book's deltas) and hands both to
    ReasoningGate.step, which evaluates PERCEIVE -> BET -> ACT and logs on the
    personal `gate` topic. Returns None; nothing here reaches action_num (F5,
    asserted by AST). Off -> nothing. The gate is constructed once per game
    (mode resolved once from REASONING_GATE, narrated once). Module bottom by
    the registry's placement law (moves no receipt); containment: never
    raises."""
    try:
        from engines.egocentric import gate as _gt
        _fab = getattr(loop, "_ego_fabric", None)
        if _fab is None or nsp is None:
            return
        _g = getattr(loop, "_reasoning_gate", None)
        if _g is None or _g.fabric is not _fab or _g.game != nsp.game:
            _g = _gt.ReasoningGate(
                _fab, game=nsp.game,
                game_dir=os.path.dirname(os.path.abspath(str(_fab.root))))
            loop._reasoning_gate = _g
        if _g.mode == _gt.MODE_OFF:
            return
        _op = loop._perceiver._to_numpy(frame) if frame is not None else None
        _gm = getattr(loop, "_gamma", None)
        _gid, _lv = nsp.game, int(getattr(loop, "_ego_level", 0) or 0)
        _rung = str(getattr(cf, "rung_name", "") or getattr(cf, "action_speed", "") or "")
        _drv = getattr(loop, "_w2b_driven", None) or {}
        _ch = getattr(loop, "_w3d_chain", None) or {}
        _drive = _ch.get("drive") if isinstance(_ch, dict) else None
        _cid = _drv.get("composite")
        _cp = None
        if _cid and _gm is not None:
            from engines.egocentric.applicability import csig_of as _csig
            _cp = (_csig(_gm.get(str(_cid))) or {}).get("price")
        _fatal = set()
        if _rung == _gt.WALL_AWARE_RUNG:              # the only class that reads it
            from engines.egocentric.enables import fatal_cells as _fc
            _fb = getattr(loop, "_ego_frontier_book", None)
            _fatal = _fc(_fb, _gid, _lv) if _fb is not None else set()
        _cen = getattr(loop, "_ego_last_known_cen", None)
        _av = ((int(round(_cen[0])), int(round(_cen[1]))) if _cen is not None else None)
        _ref = getattr(loop, "_reference_snapshot", None)
        _want = None
        if (_op is not None and _ref is not None
                and getattr(_ref, "shape", None) == _op.shape):
            _want = [(int(r), int(c), int(_ref[r, c])) for r, c in np.argwhere(_op != _ref)]
        _sa = getattr(loop, "_w4c_step_atom", None) or (None, None)
        from engines.egocentric import action_book as _ab
        _state = {
            "step": int(getattr(loop, "_actions_taken", 0) or 0), "action": int(action_num),
            "rung": _rung, "anchor": None, "spine_bet": nsp.bet_id, "opener": _op,
            "prev": getattr(loop, "_prev_frame", None),
            "plan_steps": list(_drv.get("steps") or []), "composite": _cid,
            "drive": _drive, "chain_cursor": (_ch.get("cursor") if _drive else 0),
            "composite_price": _cp,
            "atom_of": ((lambda aid: _gt.record_of(_gm, aid)) if _gm is not None else None),
            "fatal": _fatal, "avatar": _av, "settled_atom": _sa, "want_cells": _want,
            "game": _gid, "level": _lv, "book_loaded": _g.book_loaded,
            "cost": (_ab.cost_of(_gid, int(action_num)) if _g.book_loaded else None)}
        from engines.egocentric.enables import book_deltas as _bd
        _ledger = {
            "gamma": _gm, "game": _gid, "level": _lv, "fatal": _fatal, "avatar": _av,
            "settled_atom": _sa, "book_loaded": _g.book_loaded, "composite_price": _cp,
            "held_for_action": ((lambda a: _gt.held_for_action(_gm, _gid, a))
                                if _gm is not None else (lambda a: [])),
            "deltas": (_bd(_gid) if _g.book_loaded else {})}
        _g.step(_state["step"], _state, _ledger)
    except Exception:
        _swal(loop, "OTHER")
