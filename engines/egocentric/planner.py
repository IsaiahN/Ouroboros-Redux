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

Deterministic: sorted atom-id expansion order, visited-state dedup, level-by-level
frontier alternation, no RNG. Stdlib + numpy only.
"""
from __future__ import annotations

import hashlib
from collections import deque
from typing import Any, Dict, List, Optional

import numpy as np

from engines.egocentric.discrepancy import compute_d
from engines.egocentric.effects import apply_inverse, invert_transform

__all__ = ["plan_to_identity"]

_MAX_DEPTH = 8


def _state_key(state: np.ndarray) -> str:
    a = np.ascontiguousarray(state)
    h = hashlib.sha1()
    h.update(str(a.shape).encode("utf-8"))
    h.update(str(a.dtype).encode("utf-8"))
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

    def _finish(steps: List[str]) -> Optional[Dict[str, Any]]:
        """Replay the stitched plan forward from current; only a plan that reproduces
        REFERENCE exactly is returned. A failed replay is not a plan -- keep searching."""
        cur = ws
        for aid in steps:
            cur = gamma.apply(aid, cur)
            if cur is None:
                return None
        if compute_d(cur, ref)["differing"] != 0:
            return None
        feasible = len(steps) * cost_per_action <= budget
        return {"steps": list(steps), "feasible": bool(feasible)}

    fwd_paths = {_state_key(ws): []}          # state key -> steps from current
    bwd_paths = {_state_key(ref): []}         # state key -> forward-direction suffix to REFERENCE
    fwd_frontier = deque([(ws, [])])
    bwd_frontier = deque([(ref, [])])

    while fwd_frontier or bwd_frontier:
        # -- forward level: current outward via apply_effect ------------------------
        for _ in range(len(fwd_frontier)):
            state, steps = fwd_frontier.popleft()
            if len(steps) >= _MAX_DEPTH:
                continue
            for aid in ids:
                nxt = gamma.apply(aid, state)
                if nxt is None:
                    continue
                key = _state_key(nxt)
                if key in fwd_paths:
                    continue
                path = steps + [aid]
                fwd_paths[key] = path
                if compute_d(nxt, ref)["differing"] == 0:
                    out = _finish(path)
                    if out is not None:
                        return out
                if key in bwd_paths:                      # the meet: stitch and verify
                    out = _finish(path + bwd_paths[key])
                    if out is not None:
                        return out
                fwd_frontier.append((nxt, path))
        # -- backward level: REFERENCE inward via verified inverses -----------------
        # (no typed atoms -> inv_ids empty -> this level only drains the frontier,
        #  and the search is exactly the forward-only BFS it always was)
        for _ in range(len(bwd_frontier)):
            state, suffix = bwd_frontier.popleft()
            if len(suffix) >= _MAX_DEPTH:
                continue
            for aid in inv_ids:
                prev = apply_inverse(atoms[aid], state)
                if prev is None:
                    continue
                redo = gamma.apply(aid, prev)             # forward replay is the proof
                if (redo is None or redo.shape != state.shape
                        or not (redo == state).all()):
                    continue
                key = _state_key(prev)
                if key in bwd_paths:
                    continue
                sfx = [aid] + suffix
                bwd_paths[key] = sfx
                if key in fwd_paths:                      # the meet: stitch and verify
                    out = _finish(fwd_paths[key] + sfx)
                    if out is not None:
                        return out
                bwd_frontier.append((prev, sfx))
    return None
