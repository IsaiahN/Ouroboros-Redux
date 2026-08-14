"""W3b: the discrepancy engine -- d, the self-authored objective.

d is a role-aware MATCH between WORKSPACE and REFERENCE: an axis-wise residual
transform over aligned cells, COMPUTED not perceived. It says not just HOW MANY
cells differ but WHICH transformation is owed ((from, to) -> count). d is a
HYPOTHESIS: d -> 0 without a level advance falsifies the objective (the
anti-elaboration check -- d must never become a proxy).

Deterministic; stdlib + numpy only.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np

__all__ = ["compute_d", "is_identity", "objective_falsified"]


def compute_d(workspace: np.ndarray, reference: np.ndarray) -> Dict[str, Any]:
    """Axis-wise residual between aligned arrays.

    Returns {"differing": int, "by_value": {(from, to): count}}.
    Misaligned shapes are a defensive non-answer: {"differing": -1, "by_value": {}}.
    """
    ws = np.asarray(workspace)
    ref = np.asarray(reference)
    if ws.shape != ref.shape:
        return {"differing": -1, "by_value": {}}
    diff = ws != ref
    by_value: Dict[Tuple[int, int], int] = {}
    for frm, to in zip(ws[diff].ravel(), ref[diff].ravel(), strict=False):
        key = (int(frm), int(to))
        by_value[key] = by_value.get(key, 0) + 1
    return {"differing": int(diff.sum()), "by_value": by_value}


def is_identity(d: Dict[str, Any]) -> bool:
    """The stopping test: d is identity iff nothing differs."""
    return d["differing"] == 0


def objective_falsified(d_is_zero: bool, level_advanced: bool) -> bool:
    """d -> 0 with no level advance means the objective was WRONG -- pariah, not victory."""
    return bool(d_is_zero and not level_advanced)
