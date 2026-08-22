"""W3c + CK-2b: the planner -- the objective's spender, now reaching from both ends.

Breadth-first search over sequences of applicable EFFECT atoms (Gamma entries for
the game, still valid at (game, level)) driving d -> identity. The stopping test
is compute_d(state, reference)["differing"] == 0 -- never a period. A missing
operator is an empty slot, not an invented step (no solution -> None). Feasibility
is checked against measured cost: a correct plan can be unaffordable, and that is
part of the answer.

CK-2b (inverse closure): typed atoms have computable inverses, so the search runs
BIDIRECTIONALLY under the same budget -- a forward frontier from current via
apply_effect and a backward frontier from REFERENCE via inverse application, meeting
in the middle. Every backward step is verified by forward replay before it joins the
frontier (inversion is a proposal; the forward mechanics are the proof), so a stitched
plan is executable by construction -- and the final plan is replayed once more end to
end before it is returned. Raw atoms (no ttype) are not invertible: they simply never
join the backward frontier, and a Gamma with no typed atoms degrades to the exact
forward-only search as before.

BUDGET: depth alone does not bound the search -- a handful of context-matches-
anywhere atoms branch every frontier state every way and the product hangs a live
run. _MAX_NODES is a hard node-expansion cap counted across BOTH frontiers; on
exhaustion the answer is None -- plans are speculation, and a too-big search is a
shadow (the same empty slot as a missing operator), never a stall. Within one call
the Gamma is treated as read-only: atoms are fetched from the fabric once, and every
(atom, state) application is memoized by state key, so the anchor scans inside
apply_effect run at most once per pair.

G-C (PREREG_FINAL_GAPS): a SECOND target mode. With `reference=None` and a
`goal_predicate` (the goal_abduction vocabulary -- region-uniform, colour-count-zero,
regions-equal), the stopping test becomes PREDICATE SATISFACTION on the state
(satisfies(goal_predicate, state)) instead of d == 0 against a reference frame. The
search is forward-only in this mode -- there is no reference frame to walk backward
from, so the backward frontier simply stays empty (the same degradation as an
untyped Gamma). No reference AND no predicate -> None: a target is evidence-backed
or absent, never invented. Everything else -- budget, depth, memoization, replay
verification, feasibility -- is shared between the two modes.

W2a STAGE 1 (PREREG_W2_APPLICABILITY_INDEX): the APPLICABILITY PRE-FILTER.
D5 measured 95.3% of a slow worker's runtime inside apply_effect -- every atom
applied at every anchor. Before the search starts, the frame's signature (dims
+ palette, plus the reference's in reference mode) is read ONCE and the
candidate set is pruned to atoms whose ANCHOR SIGNATURES can possibly match
(applicability.prune_candidates -- O(1) set/dim comparisons per atom, palette
closure over introduced colours, inverse-path aware). Conservative: an atom
that CAN apply is never pruned; pruned-to-empty is the same ANCHOR_MISS the
exhaustive search would have reached with zero applications fired. Only WHICH
candidates are evaluated changes -- never how apply_effect judges them.

L1 (KNOBS A2, REGISTER L): cost_per_action is a MEASURED LATENT, not a
constant. A caller may still pass an explicit cost (behavior and the returned
dict byte-identical to current); with cost_per_action=None the planner asks
the GLOBAL latents.ESTIMATOR for the (game, level) estimate from the books
(gamma.fabric's collective settlements -- see latents.py for the discovered
evidence source and the completion-run derivation) and reports the estimate ON
the plan as data ("cost_per_action", "cost_missing" -- the honest fallback of
1.0 rides a MISSING flag, never silence). Estimates price feasibility only --
the DRIVE gates (verification, site, veto) are untouched.

W2c (PREREG_W2C_PLANNER_RETENTION.md): RETENTION. The per-call memo above is
the produced-and-destroyed-at-production shape -- every application re-earned
on the next call. With `retained` (a retention.RetentionStore, owned by the
W2b scheduler and cleared at level change / fission) the memo is served
THROUGH the store: (a) every EFFECT / EFFECT_IF application and every verified
inverse hits by (atom CONTENT key, state key); (b) a matched-nowhere negative
for a RAW-path atom carries to the child state across the change set
(parent -> child delta inside the search; previous root -> root across calls)
via the BAND scan; (c) a state at which every candidate failed is a DEAD-END
under (direction, state key, candidate-set key) -- re-encountered, the loop is
skipped but `expanded` is still spent. Retention changes WORK, never the
ANSWER: plans, reasons and `expanded` are identical cold or warm (R4).
retained=None is today's per-call behaviour, byte-identical (the undo).

Deterministic: sorted atom-id expansion order, visited-state dedup, level-by-level
frontier alternation, no RNG. Stdlib + numpy only.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from engines.egocentric import retention as _retention
from engines.egocentric import standing as _standing
from engines.egocentric.applicability import frame_signature, prune_candidates
from engines.egocentric.discrepancy import compute_d
from engines.egocentric.effects import apply_effect, apply_inverse, invert_transform
from engines.egocentric.goal_abduction import satisfies

__all__ = ["plan_to_identity", "NONE_REASONS", "last_reason", "reason_counts",
           "gate_summary"]

_MAX_DEPTH = 8
_MAX_NODES = 2000       # hard node-expansion budget, spent across BOTH frontiers


# ── INSTRUMENT (proctor-named): why was the outcome empty? ────────────────────
#
# plan_to_identity's None/empty returns were indistinguishable -- NOTHING ARRIVED
# and ARRIVED-AND-REJECTED read identically in every log. Every empty outcome now
# names its reason on an OUT-OF-BAND channel (module-level, never in the returned
# dict -- behavior byte-identical). Fixed enum, game-agnostic, no free strings:
#   NO_APPLICABLE_ATOMS  Gamma holds no valid entries for (game, level)
#   BUDGET_EXHAUSTED     the _MAX_NODES expansion cap was spent (either frontier)
#   NO_MEET              applications fired but the frontiers drained without meeting
#   ANCHOR_MISS          no target given (no reference AND no predicate), OR atoms
#                        exist but ZERO applications fired on this frame across both
#                        frontiers -- nothing anchored
#   INFEASIBLE_COST      a plan WAS found and returned, but priced over budget
#                        (empty for driving purposes; the dict is unchanged)
# last_reason() reflects the most recently COMPLETED call (None after a feasible
# plan). Counts are bounded: fixed key set, values capped at NONE_COUNT_CAP.

NONE_REASONS = ("NO_APPLICABLE_ATOMS", "BUDGET_EXHAUSTED", "NO_MEET",
                "ANCHOR_MISS", "INFEASIBLE_COST")
NONE_COUNT_CAP = 10 ** 9
_LAST_REASON: List[Optional[str]] = [None]    # 1-slot holder (house rule: no `global`)
_REASON_COUNTS: Dict[str, int] = dict.fromkeys(NONE_REASONS, 0)


def _set_reason(reason: Optional[str]) -> None:
    """Record the outcome of one completed call. None clears (feasible plan)."""
    if reason is not None and reason not in _REASON_COUNTS:
        raise ValueError("free-string reason refused: %r" % (reason,))
    _LAST_REASON[0] = reason
    if reason is not None:
        _REASON_COUNTS[reason] = min(_REASON_COUNTS[reason] + 1, NONE_COUNT_CAP)


def last_reason() -> Optional[str]:
    """Pure read: the reason of the last completed call's empty outcome (or None)."""
    return _LAST_REASON[0]


def reason_counts() -> Dict[str, int]:
    """Pure read: a copy of the bounded reason counters."""
    return dict(_REASON_COUNTS)


def gate_summary() -> str:
    """Fixed tokens for the [PLAN-GATE] narration line. Pure read."""
    c = _REASON_COUNTS
    return ("r_noat=%d r_budget=%d r_meet=%d r_anchor=%d r_cost=%d"
            % (c["NO_APPLICABLE_ATOMS"], c["BUDGET_EXHAUSTED"], c["NO_MEET"],
               c["ANCHOR_MISS"], c["INFEASIBLE_COST"]))


# THE state key: ONE hash function for the search, the W2b scheduler and the
# W2c retention store (retention.state_key -- the definition moved there so the
# store can hash results without importing the planner; the bytes are unchanged).
_state_key = _retention.state_key


def _candidate_ids(gamma, game: str, level: int, standing=None) -> List[str]:
    """Gamma's stored entries for the game, still valid at (game, level).

    standing=None: sorted lexically -- today's behaviour, byte-identical (the
    undo). With a standing.StandingBook (R3/R4,
    PREREG_STANDING_HALF_LIFE_ATOMS.md) the set is RANKED by S descending
    (ties keeping the lexical order) and ids whose LAST atoms-stream record
    carries `evicted: true` are DROPPED. The order is the search's visit
    order, so under _MAX_NODES it decides which plans are found at all -- a
    demoted atom is reached LATER, and a dropped one is never applied. The
    population itself is unchanged: standing.valid_ids IS this function's
    pre-build body, so the eviction sweep's fence is computed over exactly the
    atoms the search would otherwise have visited."""
    ids = _standing.valid_ids(gamma, game, level)
    if standing is None:
        return ids
    return standing.rank(gamma, ids, game)


def _invertible(atom: Optional[Dict[str, Any]]) -> bool:
    """Only a typed EFFECT atom with a computable inverse can step backward."""
    return (atom is not None and atom.get("kind") == "EFFECT"
            and bool(atom.get("ttype")) and atom.get("ttype") != "NONE"
            and invert_transform(atom["ttype"], atom.get("params") or {}) is not None)


def plan_to_identity(workspace: np.ndarray, reference: Optional[np.ndarray], gamma,
                     game: str, level: int,
                     budget: float, cost_per_action: Optional[float],
                     goal_predicate: Optional[Dict[str, Any]] = None,
                     retained: Optional[_retention.RetentionStore] = None,
                     standing: Optional[_standing.StandingBook] = None,
                     ) -> Optional[Dict[str, Any]]:
    """None | {"steps": [atom ids in order], "feasible": bool}.

    W2c: `retained` (retention.RetentionStore, the scheduler's) serves the
    application memo, the band negatives and the dead-end marks across
    calls; None keeps the per-call memo exactly as before (the undo).

    R3/R4: `standing` (standing.StandingBook, also the scheduler's) RANKS the
    candidate set by S descending and drops evicted ids -- the search visits
    stronger atoms first, so under _MAX_NODES standing decides which plans are
    found at all. READ-ONLY here: the eviction/re-entry WRITER runs at the
    scheduler's engagement seam, never inside a search (this call still treats
    Gamma as read-only). None = today's lexical order (the undo).

    TWO TARGET MODES (G-C): with `reference` an array, the stopping test is
    compute_d(state, reference)["differing"] == 0 (unchanged). With
    reference=None and `goal_predicate` an abduced structural predicate, the
    stopping test is satisfies(goal_predicate, state) and the search runs
    forward-only (no reference to invert from). Neither target -> None.

    L1: cost_per_action=None -> the global latents.ESTIMATOR prices steps from
    the books (gamma.fabric) and the plan dict additionally carries
    "cost_per_action" + "cost_missing" (estimates are data). An explicit cost
    keeps the exact current behavior and dict shape."""
    estimate: Optional[Dict[str, Any]] = None
    if cost_per_action is None:
        from engines.egocentric.latents import ESTIMATOR  # late: no import cycle
        estimate = ESTIMATOR.cost_per_action(gamma.fabric, game, level)
        cost_per_action = float(estimate["cost"])

    def _annotate(plan: Dict[str, Any]) -> Dict[str, Any]:
        if estimate is not None:
            plan["cost_per_action"] = float(cost_per_action)
            plan["cost_missing"] = bool(estimate["missing"])
        return plan

    def _ret(plan: Dict[str, Any]) -> Dict[str, Any]:
        """INSTRUMENT: a returned-but-unaffordable plan is an empty outcome for
        driving purposes -- name it out-of-band; the dict itself is untouched."""
        _set_reason(None if plan.get("feasible") else "INFEASIBLE_COST")
        return plan

    ws = np.asarray(workspace)
    pred_mode = reference is None
    if pred_mode and goal_predicate is None:
        _set_reason("ANCHOR_MISS")        # no target: nothing to anchor a plan to
        return None                       # no target is no plan -- never invented
    ref = None if pred_mode else np.asarray(reference)

    def _done(state: np.ndarray) -> bool:
        """The stopping test, per target mode. Reference mode keeps the cheap
        equality pre-filter with compute_d as the authority (unchanged)."""
        if pred_mode:
            return bool(satisfies(goal_predicate, state))
        return (state.shape == ref.shape and bool((state == ref).all())
                and compute_d(state, ref)["differing"] == 0)

    if _done(ws):
        return _ret(_annotate({"steps": [], "feasible": True}))

    ids = _candidate_ids(gamma, game, level, standing)
    if not ids:
        _set_reason("NO_APPLICABLE_ATOMS")
        return None
    atoms = {aid: gamma.get(aid) for aid in ids}
    # ── W2a STAGE 1 (PREREG_W2_APPLICABILITY_INDEX): the applicability pre-filter.
    # The frame signature is read ONCE per call; each candidate then costs O(1)
    # dim/set comparisons -- no apply_effect, no array scans (F4). An atom whose
    # context dims exceed every target frame, or whose required palette no
    # reachable colour set covers (closure over kept atoms' outputs; inverse
    # path counted in reference mode), CANNOT match anywhere and is skipped.
    # Conservative only (F2): when in doubt the candidate is kept; pruned-to-
    # empty is the same ANCHOR_MISS the exhaustive search would have reached
    # with zero applications fired.
    fsig = frame_signature([ws] if pred_mode else [ws, ref])
    ids = prune_candidates(ids, atoms, fsig, resolver=gamma.get,
                           bidirectional=not pred_mode)
    if not ids:
        _set_reason("ANCHOR_MISS")        # atoms exist but none can anchor here
        return None
    inv_ids = [aid for aid in ids if _invertible(atoms[aid])]

    # -- one call, one Gamma read: atoms fetched once, applications memoized --------
    memo: Dict[Tuple[str, str], Optional[np.ndarray]] = {}
    # W2c: the session over the retained store (None = per-call memo only).
    # The store is (game, level)-bound here; every key it writes carries the
    # atom's CONTENT key, so a superseded atom misses by construction.
    sess = None if retained is None else _retention.Session(retained, game, level)

    def _get(aid: str) -> Optional[Dict[str, Any]]:
        if aid not in atoms:
            atoms[aid] = gamma.get(aid)       # composite parts outside the candidate set
        return atoms[aid]

    def _run(aid: str, state: np.ndarray, key: str,
             lineage=None) -> Optional[np.ndarray]:
        """gamma.apply with the fabric read done once per atom and every
        (atom, state) application memoized by state key -- the anchor scans inside
        apply_effect run at most once per pair. Results are never mutated.
        W2c: with a session, EFFECT / EFFECT_IF applications go through the
        retained memo (tier 1) and, given `lineage` = (parent key, changed
        cells), the band negative (tier 2). COMPOSITEs recurse through their
        parts (each part hits by its OWN content key -- a superseded part can
        never serve a stale composite result)."""
        mk = (aid, key)
        if mk in memo:
            return memo[mk]
        atom = _get(aid)
        if atom is None:
            res: Optional[np.ndarray] = None
        elif atom.get("kind") == "COMPOSITE":
            cur: Optional[np.ndarray] = state
            ck = key
            lin = lineage
            for pid in atom.get("parts") or []:
                cur = _run(pid, cur, ck, lin)
                if cur is None:
                    break
                ck = _state_key(cur)
                lin = None
            res = cur
        elif atom.get("kind") in ("EFFECT", "EFFECT_IF"):
            res = (apply_effect(atom, state) if sess is None
                   else sess.apply(aid, atom, state, key, lineage))
        else:
            res = None                                    # INERT / lexical: nothing to run
        memo[mk] = res
        return res

    def _inverse(aid: str, state: np.ndarray, key: str) -> Optional[np.ndarray]:
        """apply_inverse, through the retained memo when a session exists."""
        if sess is None:
            return apply_inverse(atoms[aid], state)
        return sess.apply_inverse(aid, atoms[aid], state, key)

    ws_key = _state_key(ws)
    # W2c lineage across calls: (previous root key, argwhere(prev != cur)) from
    # the store's retained root -- the band carries the last call's negatives
    # to this root; then this root is retained for the next call.
    root_lineage = None if sess is None else sess.root(ws_key, ws)
    fwd_set = None if sess is None else sess.set_key(
        (aid, sess.ckey(aid, atoms[aid])) for aid in ids)
    bwd_set = None if sess is None else sess.set_key(
        (aid, sess.ckey(aid, atoms[aid])) for aid in inv_ids)

    def _finish(steps: List[str]) -> Optional[Dict[str, Any]]:
        """Replay the stitched plan forward from current; only a plan that reaches
        the TARGET (reference identity, or predicate satisfaction in goal mode)
        is returned. A failed replay is not a plan -- keep searching."""
        cur, ck = ws, ws_key
        for aid in steps:
            cur = _run(aid, cur, ck)
            if cur is None:
                return None
            ck = _state_key(cur)
        if not _done(cur):
            return None
        feasible = len(steps) * cost_per_action <= budget
        return _ret(_annotate({"steps": list(steps), "feasible": bool(feasible)}))

    fwd_paths = {ws_key: []}                  # state key -> steps from current
    # frontier entries carry a 4th slot: the W2c lineage (parent key, changed
    # cells) the band negative reads -- None without a session (unchanged work)
    fwd_frontier = deque([(ws, [], ws_key, root_lineage)])
    # goal mode has no reference frame to invert from: the backward frontier
    # stays empty and the loop degrades to the exact forward-only BFS
    if pred_mode:
        bwd_paths: Dict[str, List[str]] = {}
        bwd_frontier: deque = deque()
    else:
        ref_key = _state_key(ref)
        bwd_paths = {ref_key: []}             # state key -> forward-direction suffix to REFERENCE
        bwd_frontier = deque([(ref, [], ref_key, None)])
    expanded = 0                              # nodes expanded, summed over BOTH frontiers
    applied = 0                               # INSTRUMENT: successful applications, both frontiers

    while fwd_frontier or bwd_frontier:
        # -- forward level: current outward via apply_effect ------------------------
        for _ in range(len(fwd_frontier)):
            state, steps, skey, lineage = fwd_frontier.popleft()
            if len(steps) >= _MAX_DEPTH:
                continue
            if expanded >= _MAX_NODES:
                _set_reason("BUDGET_EXHAUSTED")
                return None                   # budget spent: a shadow, not a stall
            expanded += 1
            # W2c (c): a retained dead-end -- every candidate returned None here
            # under this exact candidate set -- skips the loop; `expanded` was
            # spent above exactly as on the cold path (budget/depth unchanged)
            if sess is not None and sess.dead(_retention.FWD, skey, fwd_set):
                continue
            any_hit = False
            for aid in ids:
                nxt = _run(aid, state, skey, lineage)
                if nxt is None:
                    continue
                any_hit = True
                applied += 1
                key = _state_key(nxt)
                if key in fwd_paths:
                    continue
                path = steps + [aid]
                fwd_paths[key] = path
                # the stopping test, per target mode (_done keeps the cheap
                # equality pre-filter with compute_d as the reference-mode
                # authority; goal mode checks predicate satisfaction)
                if _done(nxt):
                    out = _finish(path)
                    if out is not None:
                        return out
                if key in bwd_paths:                      # the meet: stitch and verify
                    out = _finish(path + bwd_paths[key])
                    if out is not None:
                        return out
                fwd_frontier.append((nxt, path, key,
                                     None if sess is None
                                     else _lineage(sess, skey, state, nxt)))
            if sess is not None and not any_hit:
                sess.mark_dead(_retention.FWD, skey, fwd_set)
        # -- backward level: REFERENCE inward via verified inverses -----------------
        # (no typed atoms -> inv_ids empty -> this level only drains the frontier,
        #  and the search is exactly the forward-only BFS it always was)
        for _ in range(len(bwd_frontier)):
            state, suffix, skey, _lin = bwd_frontier.popleft()
            if len(suffix) >= _MAX_DEPTH:
                continue
            if expanded >= _MAX_NODES:
                _set_reason("BUDGET_EXHAUSTED")
                return None                   # budget spent: a shadow, not a stall
            expanded += 1
            if sess is not None and sess.dead(_retention.BWD, skey, bwd_set):
                continue                      # W2c (c): every inverse failed here before
            all_failed = bool(inv_ids)        # nothing tried (no typed atoms) marks nothing
            for aid in inv_ids:
                prev = _inverse(aid, state, skey)
                if prev is None:
                    continue
                key = _state_key(prev)
                if key in bwd_paths:
                    all_failed = False        # the inverse fired: not a dead-end
                    continue
                redo = _run(aid, prev, key)               # forward replay is the proof
                if (redo is None or redo.shape != state.shape
                        or not (redo == state).all()):
                    continue
                all_failed = False
                applied += 1                              # a verified backward application
                sfx = [aid] + suffix
                bwd_paths[key] = sfx
                if key in fwd_paths:                      # the meet: stitch and verify
                    out = _finish(fwd_paths[key] + sfx)
                    if out is not None:
                        return out
                bwd_frontier.append((prev, sfx, key, None))
            if sess is not None and all_failed:
                sess.mark_dead(_retention.BWD, skey, bwd_set)
    # frontiers drained: ZERO applications means nothing ever anchored to this
    # frame (ANCHOR_MISS); otherwise the search ran and never met (NO_MEET)
    _set_reason("ANCHOR_MISS" if applied == 0 else "NO_MEET")
    return None


# ── W2c module-bottom helper ──────────────────────────────────────────────────

def _lineage(sess: _retention.Session, parent_key: str, parent: np.ndarray,
             child: np.ndarray) -> Optional[Tuple[str, np.ndarray]]:
    """(parent key, argwhere(parent != child)) -- the change set the band
    negative carries across inside the search (one counted delta compare per
    child); None when the shapes differ (no band can be drawn)."""
    delta = sess.delta(parent, child)
    return None if delta is None else (parent_key, delta)
