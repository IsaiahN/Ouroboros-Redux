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

Deterministic: sorted atom-id expansion order, visited-state dedup, level-by-level
frontier alternation, no RNG. Stdlib + numpy only.
"""
from __future__ import annotations

import hashlib
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

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


def _state_key(state: np.ndarray) -> str:
    a = np.ascontiguousarray(state)
    h = hashlib.sha1()
    h.update(str(a.shape).encode("utf-8"))
    h.update(a.dtype.str.encode("utf-8"))     # C-level attr: str(dtype) is hot-path slow
    h.update(a.tobytes())
    return h.hexdigest()


def _candidate_ids(gamma, game: str, level: int) -> List[str]:
    """Gamma's stored entries for the game, still valid at (game, level), sorted."""
    recs = gamma.fabric.query("collective", "atoms",
                              where=lambda r: r.get("game") == str(game))
    ids = sorted({r["id"] for r in recs if r.get("id") is not None})
    return [aid for aid in ids if gamma.valid_in(aid, game, level)]


def _invertible(atom: Optional[Dict[str, Any]]) -> bool:
    """Only a typed EFFECT atom with a computable inverse can step backward."""
    return (atom is not None and atom.get("kind") == "EFFECT"
            and bool(atom.get("ttype")) and atom.get("ttype") != "NONE"
            and invert_transform(atom["ttype"], atom.get("params") or {}) is not None)


def plan_to_identity(workspace: np.ndarray, reference: Optional[np.ndarray], gamma,
                     game: str, level: int,
                     budget: float, cost_per_action: Optional[float],
                     goal_predicate: Optional[Dict[str, Any]] = None,
                     ) -> Optional[Dict[str, Any]]:
    """None | {"steps": [atom ids in order], "feasible": bool}.

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

    ids = _candidate_ids(gamma, game, level)
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

    def _get(aid: str) -> Optional[Dict[str, Any]]:
        if aid not in atoms:
            atoms[aid] = gamma.get(aid)       # composite parts outside the candidate set
        return atoms[aid]

    def _run(aid: str, state: np.ndarray, key: str) -> Optional[np.ndarray]:
        """gamma.apply with the fabric read done once per atom and every
        (atom, state) application memoized by state key -- the anchor scans inside
        apply_effect run at most once per pair. Results are never mutated."""
        mk = (aid, key)
        if mk in memo:
            return memo[mk]
        atom = _get(aid)
        if atom is None:
            res: Optional[np.ndarray] = None
        elif atom.get("kind") == "COMPOSITE":
            cur: Optional[np.ndarray] = state
            ck = key
            for pid in atom.get("parts") or []:
                cur = _run(pid, cur, ck)
                if cur is None:
                    break
                ck = _state_key(cur)
            res = cur
        elif atom.get("kind") in ("EFFECT", "EFFECT_IF"):
            res = apply_effect(atom, state)
        else:
            res = None                                    # INERT / lexical: nothing to run
        memo[mk] = res
        return res

    ws_key = _state_key(ws)

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
    fwd_frontier = deque([(ws, [], ws_key)])
    # goal mode has no reference frame to invert from: the backward frontier
    # stays empty and the loop degrades to the exact forward-only BFS
    if pred_mode:
        bwd_paths: Dict[str, List[str]] = {}
        bwd_frontier: deque = deque()
    else:
        ref_key = _state_key(ref)
        bwd_paths = {ref_key: []}             # state key -> forward-direction suffix to REFERENCE
        bwd_frontier = deque([(ref, [], ref_key)])
    expanded = 0                              # nodes expanded, summed over BOTH frontiers
    applied = 0                               # INSTRUMENT: successful applications, both frontiers

    while fwd_frontier or bwd_frontier:
        # -- forward level: current outward via apply_effect ------------------------
        for _ in range(len(fwd_frontier)):
            state, steps, skey = fwd_frontier.popleft()
            if len(steps) >= _MAX_DEPTH:
                continue
            if expanded >= _MAX_NODES:
                _set_reason("BUDGET_EXHAUSTED")
                return None                   # budget spent: a shadow, not a stall
            expanded += 1
            for aid in ids:
                nxt = _run(aid, state, skey)
                if nxt is None:
                    continue
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
                fwd_frontier.append((nxt, path, key))
        # -- backward level: REFERENCE inward via verified inverses -----------------
        # (no typed atoms -> inv_ids empty -> this level only drains the frontier,
        #  and the search is exactly the forward-only BFS it always was)
        for _ in range(len(bwd_frontier)):
            state, suffix, skey = bwd_frontier.popleft()
            if len(suffix) >= _MAX_DEPTH:
                continue
            if expanded >= _MAX_NODES:
                _set_reason("BUDGET_EXHAUSTED")
                return None                   # budget spent: a shadow, not a stall
            expanded += 1
            for aid in inv_ids:
                prev = apply_inverse(atoms[aid], state)
                if prev is None:
                    continue
                key = _state_key(prev)
                if key in bwd_paths:
                    continue
                redo = _run(aid, prev, key)               # forward replay is the proof
                if (redo is None or redo.shape != state.shape
                        or not (redo == state).all()):
                    continue
                applied += 1                              # a verified backward application
                sfx = [aid] + suffix
                bwd_paths[key] = sfx
                if key in fwd_paths:                      # the meet: stitch and verify
                    out = _finish(fwd_paths[key] + sfx)
                    if out is not None:
                        return out
                bwd_frontier.append((prev, sfx, key))
    # frontiers drained: ZERO applications means nothing ever anchored to this
    # frame (ANCHOR_MISS); otherwise the search ran and never met (NO_MEET)
    _set_reason("ANCHOR_MISS" if applied == 0 else "NO_MEET")
    return None
