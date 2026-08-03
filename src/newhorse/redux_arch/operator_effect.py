"""operator_effect.py -- Locksmith L2: the OPERATOR-EFFECT learner. The deepest, widest lever in the
GIF-archetype audit (the shared driver for MATCH-edit family A, CONNECT-draw family C, ARRANGE-push
family D -- ~18 of the 23 zero-win games), and the consumer the MATCH relation already exposes its
residual for (`relation.py: match_residual ... consumed by L2`).

The concept (game-agnostic): the agent's BODY moving in physical space is INSTRUMENTAL -- it applies
abstract OPERATORS by proxy. A world SITE (a trigger, a button, an editable cell) is an operator: when
the body CONTACTS it, the WORKSPACE (the panel that mutates under the agent -- the key in ls20, the
edited tile in ft09) undergoes a change in an abstract attribute space. This organ learns, purely by
INTERVENTION, the map  site -> effect-on-workspace, where the effect is expressed in the SAME transform
vocabulary the MATCH relation measures against (Lane-C `panel_transform_distance`: a D4 rotation/
reflection, a colour recolour, or -- when the change is a same-shape non-transform cell edit -- a raw
EDIT). That is Isaiah's "mapping correlation to meaning and causality": a physical contact bound to an
abstract-state change.

Ground-priced, never asserted: a contact that produces a real workspace change teaches an operator; a
contact that changes nothing teaches that the site is INERT. Names no game, privileges no colour or
position (answer_lint-clean). It does not decide the plan -- it records the causal operator map the L3
attribute-space planner consumes (which sites, in what multiset/order, drive the residual to identity).
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Hashable, List, Optional, Tuple
import numpy as np
from .transform import panel_transform_distance, Transform

BBox = Tuple[int, int, int, int]                              # (r0, c0, r1, c1) inclusive -- matches Referent
EDIT_KEY: Tuple = ("edit", None, None)                        # same-shape, non-transform change (ft09 cell edit)


def _within(pt: Tuple[float, float], bbox: BBox, pad: int) -> bool:
    r, c = pt
    r0, c0, r1, c1 = bbox
    return (r0 - pad) <= r <= (r1 + pad) and (c0 - pad) <= c <= (c1 + pad)


def _effect_key(ws_before, ws_after) -> Optional[Tuple]:
    """Read the workspace's change as a transform-space operator, or None if it did not change / shapes differ.
    A clean D4/recolour transform -> its Transform.key (axis + cyclic step). A same-shape non-transform change
    -> EDIT_KEY. Uses the exact vocabulary the MATCH relation scores against, so an operator's effect and the
    match residual live in ONE space (an operator reduces the residual iff its key composes toward identity)."""
    d, t = panel_transform_distance(ws_before, ws_after)
    if d is None or d == 0:                                   # incomparable, or no change -> not an operator here
        return None
    if t is not None:
        return t.key                                         # ("geom","rot90",None) / ("recolour",None,perm) / ...
    return EDIT_KEY                                           # same shape, changed, not transform-related


@dataclass
class SiteModel:
    contacts: int = 0                                        # total times the body contacted this site
    inert: int = 0                                           # contacts that changed the workspace not at all
    effects: Counter = None                                  # effect-key -> count (the operator(s) observed)

    def __post_init__(self):
        if self.effects is None:
            self.effects = Counter()

    def dominant(self) -> Optional[Tuple]:
        if not self.effects:
            return None
        return self.effects.most_common(1)[0][0]

    def confidence(self) -> float:
        """Fraction of contacts that produced the DOMINANT effect -- how reliably this site is that operator."""
        if not self.contacts:
            return 0.0
        top = self.effects.most_common(1)[0][1] if self.effects else 0
        return top / self.contacts


class OperatorEffectLearner:
    """Learns site -> effect-on-workspace by intervention. Two entry points:
      attribute(site, ws_before, ws_after) -- core: credit the workspace change since contacting `site`.
      step(body_rc, sites, ws_before, ws_after) -- detect which site the body contacted this step, then attribute.
    `sites` is a list of (site_key, bbox); `site_key` is any hashable id (a Referent, an object id, a coord)."""

    def __init__(self, contact_pad: int = 1, min_confidence: float = 0.5, min_contacts: int = 2):
        self.contact_pad = int(contact_pad)
        self.min_confidence = float(min_confidence)
        self.min_contacts = int(min_contacts)
        self.sites: Dict[Hashable, SiteModel] = defaultdict(SiteModel)

    # ---- learning ---------------------------------------------------------------------------------
    def attribute(self, site: Hashable, ws_before, ws_after) -> Optional[Tuple]:
        """Credit the workspace's change to a contact with `site`. Returns the effect-key learned this contact
        (a Transform.key or EDIT_KEY), or None if the site was inert this contact."""
        m = self.sites[site]
        m.contacts += 1
        key = _effect_key(np.asarray(ws_before), np.asarray(ws_after))
        if key is None:
            m.inert += 1
            return None
        m.effects[key] += 1
        return key

    def _contacted(self, body_rc: Optional[Tuple[float, float]], sites: List[Tuple[Hashable, BBox]]) -> Optional[Hashable]:
        if body_rc is None:
            return None
        hit = [s for (s, bb) in sites if _within(body_rc, bb, self.contact_pad)]
        return hit[0] if len(hit) == 1 else None             # ambiguous overlap -> attribute to none (honest)

    def step(self, body_rc: Optional[Tuple[float, float]], sites: List[Tuple[Hashable, BBox]],
             ws_before, ws_after) -> Optional[Tuple]:
        """One live step: if the body contacted exactly one site, attribute the workspace change to it."""
        s = self._contacted(body_rc, sites)
        if s is None:
            return None
        return self.attribute(s, ws_before, ws_after)

    # ---- the learned operator map (what L3 planning consumes) --------------------------------------
    def operator(self, site: Hashable) -> Optional[Tuple]:
        """The dominant effect-key of a site once it is CONFIDENT and has enough evidence, else None
        (an unproven or inert site contributes no operator to the plan)."""
        m = self.sites.get(site)
        if m is None or m.contacts < self.min_contacts:
            return None
        if m.confidence() < self.min_confidence:
            return None
        return m.dominant()

    def operators(self) -> Dict[Hashable, Tuple]:
        """The confident causal map site -> operator effect-key -- the toolbox the planner drives the match
        residual to identity with."""
        return {s: op for s in list(self.sites) if (op := self.operator(s)) is not None}

    def is_inert(self, site: Hashable) -> bool:
        m = self.sites.get(site)
        return bool(m and m.contacts >= self.min_contacts and not m.effects)

    def report(self) -> Dict[str, object]:
        return {"n_sites": len(self.sites),
                "operators": {str(s): list(op) for s, op in self.operators().items()},
                "inert": [str(s) for s in self.sites if self.is_inert(s)]}
