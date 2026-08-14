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

Deterministic: sorted atom-id expansion order, visited-state dedup, level-by-level
frontier alternation, no RNG. Stdlib + numpy only.
"""
from __future__ import annotations

import hashlib
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from engines.egocentric.discrepancy import compute_d
from engines.egocentric.effects import apply_effect, apply_inverse, invert_transform

__all__ = ["plan_to_identity"]

_MAX_DEPTH = 8
_MAX_NODES = 2000       # hard node-expansion budget, spent across BOTH frontiers


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


def plan_to_identity(workspace: np.ndarray, reference: np.ndarray, gamma,
                     game: str, level: int,
                     budget: float, cost_per_action: float) -> Optional[Dict[str, Any]]:
    """None | {"steps": [atom ids in order], "feasible": bool}."""
    ws = np.asarray(workspace)
    ref = np.asarray(reference)

    if compute_d(ws, ref)["differing"] == 0:
        return {"steps": [], "feasible": True}

    ids = _candidate_ids(gamma, game, level)
    if not ids:
        return None
    atoms = {aid: gamma.get(aid) for aid in ids}
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
    ref_key = _state_key(ref)

    def _finish(steps: List[str]) -> Optional[Dict[str, Any]]:
        """Replay the stitched plan forward from current; only a plan that reproduces
        REFERENCE exactly is returned. A failed replay is not a plan -- keep searching."""
        cur, ck = ws, ws_key
        for aid in steps:
            cur = _run(aid, cur, ck)
            if cur is None:
                return None
            ck = _state_key(cur)
        if compute_d(cur, ref)["differing"] != 0:
            return None
        feasible = len(steps) * cost_per_action <= budget
        return {"steps": list(steps), "feasible": bool(feasible)}

    fwd_paths = {ws_key: []}                  # state key -> steps from current
    bwd_paths = {ref_key: []}                 # state key -> forward-direction suffix to REFERENCE
    fwd_frontier = deque([(ws, [], ws_key)])
    bwd_frontier = deque([(ref, [], ref_key)])
    expanded = 0                              # nodes expanded, summed over BOTH frontiers

    while fwd_frontier or bwd_frontier:
        # -- forward level: current outward via apply_effect ------------------------
        for _ in range(len(fwd_frontier)):
            state, steps, skey = fwd_frontier.popleft()
            if len(steps) >= _MAX_DEPTH:
                continue
            if expanded >= _MAX_NODES:
                return None                   # budget spent: a shadow, not a stall
            expanded += 1
            for aid in ids:
                nxt = _run(aid, state, skey)
                if nxt is None:
                    continue
                key = _state_key(nxt)
                if key in fwd_paths:
                    continue
                path = steps + [aid]
                fwd_paths[key] = path
                # cheap equality pre-filter; compute_d stays the stopping test's
                # authority (differing == 0 iff same shape and every cell equal)
                if (nxt.shape == ref.shape and (nxt == ref).all()
                        and compute_d(nxt, ref)["differing"] == 0):
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
                sfx = [aid] + suffix
                bwd_paths[key] = sfx
                if key in fwd_paths:                      # the meet: stitch and verify
                    out = _finish(fwd_paths[key] + sfx)
                    if out is not None:
                        return out
                bwd_frontier.append((prev, sfx, key))
    return None
