"""operator_planner.py -- Locksmith L3: turn the MATCH residual + the learned operator map into a DRIVE
target (the piece that makes MATCH `drivable`). Consumes:
  - the RESIDUAL transform (what still separates workspace from reference; MATCH.residual, in the
    Lane-C transform vocabulary: a D4 geom + a colour recolour, or an EDIT),
  - the OPERATOR MAP site->effect-key learned by INTERVENTION (operator_effect.OperatorEffectLearner),
  - the candidate SITES (operator locations) + the workspace location,
and returns the next site to CONTACT so the workspace is transformed toward the reference.

Game-agnostic (answer_lint-clean): names no game, privileges no colour/position. It plans in the
ABSTRACT attribute space (which operator reduces the residual) and hands a spatial target to the
existing router/click. When operators are unknown, it EXPLORES (contact an untried site to learn its
effect) -- the discovery is the agent's, priced by whether the residual actually shrinks (the ground),
never asserted. The concept behind ls20/cd82/ft09/dc22: navigation is INSTRUMENTAL; the goal is an
abstract MATCH the agent produces by applying learned operators by proxy.
"""
from __future__ import annotations
from typing import Dict, Hashable, List, Optional, Tuple
from .operator_effect import EDIT_KEY

BBox = Tuple[int, int, int, int]
Cell = Tuple[int, int]


def _centre(bb: BBox) -> Cell:
    return ((bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2)


def _residual_kinds(residual) -> set:
    """Which operator KINDS would help null this residual: a geom residual wants a geom operator, a
    recolour residual wants a recolour, an EDIT residual wants an edit. Empty if the residual is None
    or already identity (nothing to drive)."""
    if residual is None:
        return set()
    kind = getattr(residual, "kind", None)
    if kind in (None, "identity"):
        return set()
    want = set()
    if "geom" in kind:
        want.add("geom")
    if "recolour" in kind:
        want.add("recolour")
    if kind == "edit":
        want.add("edit")
    return want


def _op_kind(effect_key: Tuple) -> str:
    if effect_key == EDIT_KEY:
        return "edit"
    return str(effect_key[0]) if effect_key else ""


class OperatorPlanner:
    """Given the current residual + the operator map + the sites, choose the next site to contact.
    Pure function of its inputs (no state); the LEARNING lives in OperatorEffectLearner, the MEASUREMENT
    in the MATCH relation. Returns (target_cell, note) or (None, note) when nothing to drive / no site."""

    def plan(self, residual, operators: Dict[Hashable, Tuple], sites: List[Tuple[Hashable, BBox]],
             workspace_bbox: Optional[BBox] = None) -> Tuple[Optional[Cell], str]:
        want = _residual_kinds(residual)
        if not want:
            return None, "match:solved-or-no-residual"           # identity / None -> MATCH satisfied, no drive
        if not sites:
            # click-modality with no separate operator sites: act ON the workspace itself (clicking it
            # applies its own transform, e.g. cd82/ft09). The workspace centre is the target.
            if workspace_bbox is not None:
                return _centre(workspace_bbox), "match:act-on-workspace"
            return None, "match:no-site"
        site_bb = {s: bb for s, bb in sites}
        # 1) a KNOWN operator whose effect kind matches what the residual needs -> exploit it.
        relevant = [s for s, key in operators.items() if _op_kind(key) in want and s in site_bb]
        if relevant:
            s = relevant[0]
            return _centre(site_bb[s]), "match:apply-operator(%s)" % str(s)
        # 2) no known-relevant operator -> EXPLORE an untried site to learn its effect (priced by the
        #    ground: L2 will attribute the workspace change, MATCH will report if the residual shrank).
        untried = [s for s, _ in sites if s not in operators]
        if untried:
            s0 = untried[0]
            return _centre(site_bb[s0]), "match:explore-site(%s)" % str(s0)
        # 3) all sites tried, none relevant: fall back to acting on the workspace (or the first site).
        if workspace_bbox is not None:
            return _centre(workspace_bbox), "match:fallback-workspace"
        return _centre(sites[0][1]), "match:fallback-site"
