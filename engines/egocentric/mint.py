"""W3a: the MDL mint -- one operator, guards as a product, accept iff the compression pays.

MDLMint.consider(before, action, after, game, level) runs three guards in order:

  SUPPORT (before-search): the event must leave a residual. No changed cell, or malformed
  input, means there is no evidence to mint from -- "reject" (or "quarantine" when the
  inputs themselves are broken). The mint compounds nothing on silence.

  NOVELTY (after-construction): the candidate atom's canonical key is compared against
  every atom already in Gamma's collective "atoms" stream. A known key is a
  "rederivation" -- confirmation, never a second copy.

  MDL (the compression test): let changed = number of changed cells.
      R    = 2.0 * changed + 1.0        (cost of leaving the residual unexplained:
                                         encoding_cost_route's per-element scale plus a
                                         +1.0 leaving-it-unexplained premium)
      cost = encoding_cost_atom(phi)    (= 1.0 + changed)
  Accept iff  cost + 0.0 < R            (residual after phi explains the event is 0)
      AND     cost < 0.9 * R            (the atom must clear R with margin, not scrape it)
      AND     bbox_area < 0.5 * board_area   (compressibility: an "atom" whose
                                              context/transform patch covers half the
                                              world or more is no pocket -- it is as big
                                              as the change it explains).
  A 1-cell recolour on 5x5: cost 2.0 < R 3.0, 2.0 < 2.7, bbox 1 < 12.5 -> mint.
  A 6x6 scramble (24 changed cells, bbox 6x5=30 of 36): 30 >= 18.0 -> reject.

Every call, whatever the verdict, appends a record to the fabric's collective
"mint_verdicts" topic. Nothing silent. Deterministic throughout; malformed inputs bump
an errors counter and quarantine instead of raising.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from engines.egocentric import effects as _effects

__all__ = ["MDLMint"]

VERDICT_TOPIC = "mint_verdicts"

# The residual's per-cell price mirrors encoding_cost_route's 2.0-per-element scale.
RESIDUAL_CELL_COST = 2.0
# Leaving the residual unexplained carries a flat premium (breaks the tie at 1 cell).
UNEXPLAINED_PREMIUM = 1.0
# The atom must clear R with margin, not scrape it.
MDL_MARGIN = 0.9
# Compressibility: the atom's patch (changed-cells bounding box) must be a pocket,
# strictly smaller than half the board -- else it is as big as the world it "explains".
MAX_BBOX_BOARD_FRACTION = 0.5


class MDLMint:
    """The W3a mint over a typed Gamma store: SUPPORT x NOVELTY x MDL, verdicts ledgered."""

    def __init__(self, gamma):
        self.gamma = gamma
        self.errors = 0
        self._split: Dict[str, int] = {"structural": 0, "lexical": 0}

    # -- internals -----------------------------------------------------------------

    def _record(self, verdict: str, game: str, level: int,
                key: Optional[str] = None) -> None:
        rec: Dict[str, Any] = {"verdict": verdict, "game": str(game), "level": int(level)}
        if key is not None:
            rec["key"] = key
        self.gamma.fabric.append("collective", VERDICT_TOPIC, rec)

    def _known_keys(self) -> set:
        keys = set()
        for r in self.gamma.fabric.query("collective", self.gamma.TOPIC):
            atom = r.get("atom") or {}
            k = atom.get("key", r.get("key"))
            if k:
                keys.add(k)
        return keys

    # -- the operator ----------------------------------------------------------------

    def consider(self, before, action, after, game, level) -> Dict[str, Any]:
        # SUPPORT: evidence exists, checked before any search. Malformed -> quarantine.
        try:
            b = np.asarray(before)
            a = np.asarray(after)
            if b.shape != a.shape or b.ndim != 2 or b.size == 0:
                self.errors += 1
                self._record("quarantine", game, level)
                return {"verdict": "quarantine", "id": None}
            changed = int((b != a).sum())
        except Exception:
            self.errors += 1
            self._record("quarantine", game, level)
            return {"verdict": "quarantine", "id": None}
        if changed == 0:
            self._record("reject", game, level)
            return {"verdict": "reject", "id": None}

        # Candidate atom from the event.
        phi = _effects.learn_effect(b, action, a)
        if phi is None or phi.get("kind") != "EFFECT":
            self.errors += 1
            self._record("reject", game, level)
            return {"verdict": "reject", "id": None}

        key = phi.get("key")

        # NOVELTY: a known key is a re-derivation, never a second atom.
        if key in self._known_keys():
            self._record("rederivation", game, level, key=key)
            return {"verdict": "rederivation", "id": None}

        # MDL: accept iff |phi| + |R given phi| < |R|, with margin and a pocket test.
        cost = _effects.encoding_cost_atom(phi)                # 1.0 + changed
        residual_given_phi = 0.0                               # phi explains the event fully
        R = RESIDUAL_CELL_COST * float(changed) + UNEXPLAINED_PREMIUM
        ctx = phi.get("context") or [[]]
        bbox_area = len(ctx) * (len(ctx[0]) if ctx else 0)
        board_area = int(b.size)
        compresses = (
            cost + residual_given_phi < R
            and cost < MDL_MARGIN * R
            and bbox_area < MAX_BBOX_BOARD_FRACTION * board_area
        )
        if not compresses:
            self._record("reject", game, level, key=key)
            return {"verdict": "reject", "id": None}

        # Mint: pay the cost, cash the pocket.
        aid = self.gamma.add(phi, game, level)
        typ = "structural" if phi.get("transform") is not None else "lexical"
        self._split[typ] = self._split.get(typ, 0) + 1
        self._record("mint", game, level, key=key)
        return {"verdict": "mint", "id": aid}

    # -- the letters-wall watchdog ------------------------------------------------------

    def split(self) -> Dict[str, int]:
        """Accepted mints by atom type: structural (has transform) vs lexical."""
        return dict(self._split)
