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

  SURPRISE (CK-2c, Rescorla-Wagner): evidence should surprise, not merely count. Per
  (game, level, action, transition-signature) -- the signature a cheap stable hash of
  the changed-cell pattern (bbox delta bytes) -- the effective support of a piece of
  evidence is 1/(1+seen): full (1.0) on first occurrence, decaying with repetition.
  Only full support carries a novel candidate to MDL, so N repetitions of one
  transition accumulate the harmonic sum (~ln N), asymptotically below the N that N
  distinct transitions clear. A transition already reproduced by an atom in Gamma is
  still a "rederivation" (unchanged). The seen-count map is LRU-bounded (SEEN_CAP).
  Weighted verdicts carry an optional "w" field; no bar, verdict name, MDL inequality,
  or bbox clause changed.

Every call, whatever the verdict, appends a record to the fabric's collective
"mint_verdicts" topic. Nothing silent. Deterministic throughout; malformed inputs bump
an errors counter and quarantine instead of raising.
"""
from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

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
# CK-2c (Rescorla-Wagner): evidence contributes support weighted by SURPRISE.
# weight = 1 / (1 + seen) per (game, level, action, transition-signature); the first
# occurrence carries full support (1.0) and only full support clears the SUPPORT gate,
# so N identical repetitions accumulate the harmonic sum (~ln N) -- asymptotically below
# the N that N distinct transitions clear. No bar/threshold below changes value.
SUPPORT_FULL = 1.0
# Memory bound on the seen-count map: LRU-evicted beyond this many signatures.
SEEN_CAP = 4096


class MDLMint:
    """The W3a mint over a typed Gamma store: SUPPORT x NOVELTY x MDL, verdicts ledgered.
    CK-2c: SUPPORT is surprise-weighted -- repetition of one transition-signature decays
    its effective support (1/(1+seen)); rederivations stay rederivations."""

    def __init__(self, gamma, seen_cap: int = SEEN_CAP):
        self.gamma = gamma
        self.errors = 0
        self._split: Dict[str, int] = {"structural": 0, "lexical": 0}
        # (game, level, action, signature) -> times seen; LRU-bounded at seen_cap.
        self._seen: OrderedDict[Tuple[str, int, int, str], int] = OrderedDict()
        self._seen_cap = max(1, int(seen_cap))

    # -- internals -----------------------------------------------------------------

    def _record(self, verdict: str, game: str, level: int,
                key: Optional[str] = None, w: Optional[float] = None) -> None:
        rec: Dict[str, Any] = {"verdict": verdict, "game": str(game), "level": int(level)}
        if key is not None:
            rec["key"] = key
        if w is not None:
            rec["w"] = float(w)
        self.gamma.fabric.append("collective", VERDICT_TOPIC, rec)

    @staticmethod
    def _signature(b: np.ndarray, a: np.ndarray, action) -> str:
        """Cheap stable hash of the changed-cell pattern: the bbox delta bytes -- changed
        mask plus before/after values AT the changed cells, bbox-relative. Deliberately
        coarser than the atom key (which hashes the whole bbox patches): unchanged debris
        inside the bbox does not make the same transition 'new' again."""
        diff = b != a
        rows = np.flatnonzero(diff.any(axis=1))
        cols = np.flatnonzero(diff.any(axis=0))
        m = diff[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
        bb = b[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
        aa = a[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
        blob = b"|".join((
            str(int(action)).encode("utf-8"),
            str(m.shape).encode("utf-8"),
            np.packbits(m).tobytes(),
            np.asarray(bb[m], dtype=np.int64).tobytes(),
            np.asarray(aa[m], dtype=np.int64).tobytes(),
        ))
        return hashlib.sha1(blob).hexdigest()[:16]

    def _surprise(self, game, level, action, sig: str) -> float:
        """Rescorla-Wagner-shaped support weight: 1/(1+seen), then bump the count.
        LRU-bounded: the map can never exceed self._seen_cap entries."""
        k = (str(game), int(level), int(action), sig)
        seen = self._seen.pop(k, 0)
        self._seen[k] = seen + 1                       # re-insert at the fresh end
        while len(self._seen) > self._seen_cap:
            self._seen.popitem(last=False)             # evict the stalest signature
        return 1.0 / (1.0 + float(seen))

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

        # CK-2c SURPRISE: weight this evidence's support by novelty of the transition.
        # Every well-formed supported event bumps the (game, level, action, signature)
        # seen-count -- rederivations included, so grinding a known transition also
        # stales its near-variants.
        sig = self._signature(b, a, phi.get("action", 0))
        w = self._surprise(game, level, phi.get("action", 0), sig)

        # NOVELTY: a known key is a re-derivation, never a second atom. (Unchanged --
        # a transition already reproduced by an existing atom contributes rederivation.)
        if key in self._known_keys():
            self._record("rederivation", game, level, key=key)
            return {"verdict": "rederivation", "id": None}

        # SUPPORT, surprise-weighted: only full support (a first-seen transition
        # signature) carries a novel candidate forward. Repetition contributes
        # 1/(1+seen) -- the harmonic accumulation asymptotes below what the same
        # count of distinct transitions clears. The bar itself is unchanged.
        if w < SUPPORT_FULL:
            self._record("reject", game, level, key=key, w=w)
            return {"verdict": "reject", "id": None, "w": w}

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

        # Mint: pay the cost, cash the pocket. Full-surprise support is ledgered as w.
        aid = self.gamma.add(phi, game, level)
        typ = "structural" if phi.get("transform") is not None else "lexical"
        self._split[typ] = self._split.get(typ, 0) + 1
        self._record("mint", game, level, key=key, w=w)
        return {"verdict": "mint", "id": aid, "w": w}

    # -- the letters-wall watchdog ------------------------------------------------------

    def split(self) -> Dict[str, int]:
        """Accepted mints by atom type: structural (has transform) vs lexical."""
        return dict(self._split)
