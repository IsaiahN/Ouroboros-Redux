"""W3c: the planner -- the objective's spender.

Breadth-first search over sequences of applicable EFFECT atoms (Gamma entries for
the game, still valid at (game, level)) driving d -> identity. The stopping test
is compute_d(state, reference)["differing"] == 0 -- never a period. A missing
operator is an empty slot, not an invented step (no solution -> None). Feasibility
is checked against measured cost: a correct plan can be unaffordable, and that is
part of the answer.

Deterministic: sorted atom-id expansion order, visited-state dedup, no RNG.
Stdlib + numpy only.
"""
from __future__ import annotations

import hashlib
from collections import deque
from typing import Any, Dict, List, Optional

import numpy as np

from engines.egocentric.discrepancy import compute_d

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

    visited = {_state_key(ws)}
    frontier = deque([(ws, [])])
    while frontier:
        state, steps = frontier.popleft()
        if len(steps) >= _MAX_DEPTH:
            continue
        for aid in ids:
            nxt = gamma.apply(aid, state)
            if nxt is None:
                continue
            key = _state_key(nxt)
            if key in visited:
                continue
            visited.add(key)
            path = steps + [aid]
            if compute_d(nxt, ref)["differing"] == 0:
                feasible = len(path) * cost_per_action <= budget
                return {"steps": path, "feasible": bool(feasible)}
            frontier.append((nxt, path))
    return None
