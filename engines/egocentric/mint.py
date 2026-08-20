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
             + EXTENT_RATE * retained   (W2-S2: retained-but-unchanged context cells
                                         PAY -- extent in the bargain, not just the wall)
  Accept iff  cost + 0.0 < R            (residual after phi explains the event is 0)
      AND     cost < 0.9 * R            (the atom must clear R with margin, not scrape it)
      AND     bbox_area < 0.5 * board_area   (compressibility: an "atom" whose
                                              context/transform patch covers half the
                                              world or more is no pocket -- it is as big
                                              as the change it explains; W2-S2 keeps
                                              this clause as the OUTER WALL).

  W2 STAGE 2 + THE RE-POINT AMENDMENT (PREREG_W2_STAGE2_CONTEXT_MIN.md): the
  identity is the RULE, not the situation it was seen in. Every well-formed
  changed event whose COARSE SIGNATURE (_signature below -- change-only,
  deliberately debris-blind) matches a minted atom INTERSECTS that atom's
  context with the observation's (_signature_merge -> _merge_context ->
  effects.minimise_atom): varying cells become DONT_CARE, changed + one ring
  always retained, context_full preserved as the undo, superseding append with
  the same id. The FULL atom key (which hashes unchanged debris too) is NOT the
  trigger -- full-key collisions cannot carry different contexts. THE CONFLICT
  CLAUSE (_conflict_clause, Condition 1): an observation whose signature
  DIFFERS but whose before-frame matches a minimised atom's loosened context
  REINSTATES the distinguishing cells from context_full (pinned via
  ctx_conflict_cells -- divergence tightens, never loosens) and marks the
  record ctx_conflict. context_full is NEVER deleted here (Condition 2). The
  verdicts themselves are unchanged throughout.
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

A3-4 (KNOBS AMENDMENT 3) -- every verdict record additionally carries:

  "ep"    the episode ordinal: an instance-local counter that advances whenever the
          (game, level) context of consider() changes, or when the caller invokes
          bump_episode(). A caller that already owns an episode counter may pass
          consider(..., ep=N) to stamp its own ordinal (the internal counter is
          untouched); ep=None (the default) uses the internal one -- so NO caller
          change is required for the stamp to exist.
  "sigma" the EVENT's sigma in the consumer's shared vocabulary (sigma_of over the
          full before/after frames). Minted atoms already carried it (B13); now
          rederivation/reject/quarantine verdicts carry it too -- the bracket's
          rederivation-time sigma, no longer MISSING. On quarantine the sigma
          degrades (sigma_of never raises) rather than vanishing.

Both fields are ADDITIVE: old books without them still read everywhere.

ORIGIN MARKER (PREREG_DRAIN_ORIGIN.md §B): an accepted mint is the frame's OWN ground
reaching an atom, so the atoms-stream record is stamped origin="local" + mint_seq AT
WRITE TIME (effects.Gamma.add). Only positively-marked records support the
CORROBORATION-vs-SURPLUS split; absence of import fields never did.
"""
from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

import numpy as np

from engines.egocentric import applicability as _applicability
from engines.egocentric import consumer as _consumer
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
# W2 STAGE 2 (PREREG_W2_STAGE2_CONTEXT_MIN.md): THE EXTENT PREMIUM. The accept
# inequality becomes
#     cost = 1.0 + changed + EXTENT_RATE * retained_unchanged_cells
# where retained_unchanged_cells = context cells that are neither DONT_CARE nor
# changed (effects.context_retained_cells) -- so a precondition PAYS per cell it
# insists on instead of merely PASSING the binary half-board clause, which stays
# as the outer wall. At 0.0 the term vanishes and mint decisions are
# byte-identical to the pre-premium code (the F3 dial).
#
# THE STARTING VALUE, derived from the pi-replay median (PI_REPLAY_RESULT.md:
# median context 976 cells licensing changed = 26):
#     R = 2*26 + 1 = 53;  margin bar = 0.9*R = 47.7;  base cost = 1 + 26 = 27.
#     Median-shaped atom: retained = 976 - 26 = 950, so rejection needs
#         27 + rate*950 >= 47.7   =>   rate >= 20.7/950 ~= 0.0218.
#     Tight atom (changed + one ring; worst case 26 fully scattered cells,
#     <= 8 ring cells each => retained <= 208) must still mint comfortably:
#         27 + rate*208 < 47.7    =>   rate < 20.7/208 ~= 0.0995.
# EXTENT_RATE = 0.05 sits between: the median-shaped candidate prices at
# 27 + 0.05*950 = 74.5 (rejected, over both bars) while the fully scattered
# tight twin prices at <= 27 + 0.05*208 = 37.4 (mints with ~10 of margin; a
# compact 26-cell change retains ~0 and prices at 27). In general rejection
# begins near retained ~= 16.4x changed -- i.e. below ~6% change density.
EXTENT_RATE = 0.05
# CK-2c (Rescorla-Wagner): evidence contributes support weighted by SURPRISE.
# weight = 1 / (1 + seen) per (game, level, action, transition-signature); the first
# occurrence carries full support (1.0) and only full support clears the SUPPORT gate,
# so N identical repetitions accumulate the harmonic sum (~ln N) -- asymptotically below
# the N that N distinct transitions clear. No bar/threshold below changes value.
SUPPORT_FULL = 1.0
# Memory bound on the seen-count map: LRU-evicted beyond this many signatures.
SEEN_CAP = 4096
# W2-S2 RE-POINT (THE RE-POINT AMENDMENT): the CONFLICT CLAUSE anchor-scans at
# most this many minimised atoms per consider() call, most-recently-touched
# first, each pre-screened by the applicability signature (dims + palette)
# BEFORE any anchor scan -- the check stays bounded whatever Gamma grows to.
CONFLICT_SCAN_CAP = 64


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
        # A3-4: the episode ordinal -- advances on (game, level) context change
        # or an explicit bump_episode(); stamped on every verdict record.
        self._ep = 0
        self._ep_ctx: Optional[Tuple[str, str]] = None
        # W2-S2 RE-POINT: the coarse-signature index. STATE CHOICE, stated:
        # IN-MEMORY per process, exactly like the _seen support state above --
        # AND lazily derivable from Gamma (_refresh_sig_index scans the atoms
        # stream incrementally and derives each record's signature from its own
        # stored patches), so a RESTARTED worker re-links signature -> atom on
        # its first consider() with no persisted side file. _rec_by_id caches
        # the LAST record per atom id (Gamma.get's last-wins); _min_ids tracks
        # minimised atoms (context_full present) for the conflict clause's
        # bounded scan. Memory is bounded by the atoms stream itself: at most
        # one entry per atom id / distinct signature, never more than Gamma
        # already holds in the fabric.
        self._sig2id: Dict[str, str] = {}
        self._id_sig: Dict[str, str] = {}
        self._rec_by_id: Dict[str, Dict[str, Any]] = {}
        self._min_ids: OrderedDict[str, None] = OrderedDict()
        self._scan_pos = 0

    # -- internals -----------------------------------------------------------------

    def bump_episode(self) -> int:
        """A3-4: advance the episode ordinal explicitly (e.g. on a level retry the
        (game, level) context cannot see). Returns the new ordinal."""
        self._ep += 1
        return self._ep

    def _episode_of(self, game, level, ep: Optional[int]) -> int:
        """The ordinal to stamp: the caller's ep when given, else the internal
        counter -- advanced first if the (game, level) context changed."""
        try:
            ctx = (str(game), str(level))
        except Exception:
            ctx = self._ep_ctx
        if self._ep_ctx is not None and ctx != self._ep_ctx:
            self._ep += 1
        self._ep_ctx = ctx
        if ep is None:
            return self._ep
        try:
            return int(ep)
        except Exception:
            return self._ep

    def _record(self, verdict: str, game: str, level: int,
                key: Optional[str] = None, w: Optional[float] = None,
                ep: Optional[int] = None,
                sigma: Optional[Dict[str, Any]] = None) -> None:
        rec: Dict[str, Any] = {"verdict": verdict, "game": str(game), "level": int(level)}
        if key is not None:
            rec["key"] = key
        if w is not None:
            rec["w"] = float(w)
        if ep is not None:
            rec["ep"] = int(ep)                  # A3-4: the episode ordinal
        if isinstance(sigma, dict):
            rec["sigma"] = dict(sigma)           # A3-4: the event's sigma (own copy)
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

    def consider(self, before, action, after, game, level,
                 ep: Optional[int] = None) -> Dict[str, Any]:
        # A3-4: the episode ordinal for THIS call (context-derived unless given),
        # plus the event's sigma -- both stamped on whatever verdict follows.
        ep_now = self._episode_of(game, level, ep)
        # SUPPORT: evidence exists, checked before any search. Malformed -> quarantine.
        try:
            b = np.asarray(before)
            a = np.asarray(after)
            if b.shape != a.shape or b.ndim != 2 or b.size == 0:
                self.errors += 1
                self._record("quarantine", game, level, ep=ep_now,
                             sigma=_consumer.sigma_of(before, after))
                return {"verdict": "quarantine", "id": None}
            changed = int((b != a).sum())
        except Exception:
            self.errors += 1
            self._record("quarantine", game, level, ep=ep_now,
                         sigma=_consumer.sigma_of(None, None))
            return {"verdict": "quarantine", "id": None}
        # The event's sigma (B13 vocabulary), computed ONCE: it already had to be
        # computed for any minted atom; now every verdict record carries it.
        sigma = _consumer.sigma_of(b, a)
        if changed == 0:
            self._record("reject", game, level, ep=ep_now, sigma=sigma)
            return {"verdict": "reject", "id": None}

        # Candidate atom from the event.
        phi = _effects.learn_effect(b, action, a)
        if phi is None or phi.get("kind") != "EFFECT":
            self.errors += 1
            self._record("reject", game, level, ep=ep_now, sigma=sigma)
            return {"verdict": "reject", "id": None}

        key = phi.get("key")

        # CK-2c SURPRISE: weight this evidence's support by novelty of the transition.
        # Every well-formed supported event bumps the (game, level, action, signature)
        # seen-count -- rederivations included, so grinding a known transition also
        # stales its near-variants.
        sig = self._signature(b, a, phi.get("action", 0))
        w = self._surprise(game, level, phi.get("action", 0), sig)

        # W2-S2 RE-POINT (THE RE-POINT AMENDMENT): the DETECTION POINT -- the
        # coarse signature, the candidate's context and the full before-frame
        # are all in hand right here, for EVERY well-formed changed event. A
        # signature match on a minted atom (full key equal or not) intersects
        # that atom's context with this observation's; a signature MISMATCH
        # whose before-frame matches a minimised atom's loosened context fires
        # the conflict clause. Verdicts below are untouched either way.
        self._signature_merge(sig, phi, b)

        # NOVELTY: a known key is a re-derivation, never a second atom. (Unchanged --
        # a transition already reproduced by an existing atom contributes rederivation.)
        if key in self._known_keys():
            self._record("rederivation", game, level, key=key, ep=ep_now, sigma=sigma)
            return {"verdict": "rederivation", "id": None}

        # SUPPORT, surprise-weighted: only full support (a first-seen transition
        # signature) carries a novel candidate forward. Repetition contributes
        # 1/(1+seen) -- the harmonic accumulation asymptotes below what the same
        # count of distinct transitions clears. The bar itself is unchanged.
        if w < SUPPORT_FULL:
            self._record("reject", game, level, key=key, w=w, ep=ep_now, sigma=sigma)
            return {"verdict": "reject", "id": None, "w": w}

        # MDL: accept iff |phi| + |R given phi| < |R|, with margin and a pocket test.
        # W2-S2: the EXTENT PREMIUM -- every retained-but-unchanged context cell
        # is priced at EXTENT_RATE (arithmetic at the constant's definition).
        cost = (_effects.encoding_cost_atom(phi)               # 1.0 + changed
                + EXTENT_RATE * _effects.context_retained_cells(phi))
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
            self._record("reject", game, level, key=key, ep=ep_now, sigma=sigma)
            return {"verdict": "reject", "id": None}

        # B13: SIGMA AT MINT TIME -- the atom's prediction-signature (the consumer's
        # shared vocabulary, computed once above from the full before/after frames)
        # travels with the record; recognition later is a lookup, not an application loop.
        phi["sigma"] = sigma

        # W2a STAGE 1 (PREREG_W2_APPLICABILITY_INDEX): the ANCHOR SIGNATURE at
        # mint time -- context-patch dims, palette set, cheap content key -- so
        # the planner's pre-filter is a lookup, not a derivation. DERIVED STATE:
        # applicability.signature_of recomputes the identical signature on read
        # for any atom that predates this field (backfill-on-read, never a
        # migration); the stored copy is a cache, never the sole holder.
        phi[_applicability.ASIG_FIELD] = _applicability.anchor_signature(phi)

        # Mint: pay the cost, cash the pocket. Full-surprise support is ledgered as w.
        # THE ORIGIN MARKER (PREREG_DRAIN_ORIGIN.md §B): this is THE LOCAL MINT
        # PATH -- the frame's own ground reached this atom, so the record is
        # stamped origin="local" (+ mint_seq) AT WRITE TIME. Stated explicitly,
        # not left to Gamma.add's default: provenance recorded positively or not
        # at all, and CORROBORATION-vs-SURPLUS cannot be reconstructed later.
        aid = self.gamma.add(phi, game, level,
                             origin=_effects.ORIGIN_LOCAL)
        typ = "structural" if phi.get("transform") is not None else "lexical"
        self._split[typ] = self._split.get(typ, 0) + 1
        self._record("mint", game, level, key=key, w=w, ep=ep_now, sigma=sigma)
        return {"verdict": "mint", "id": aid, "w": w}

    # -- W2 STAGE 2 + RE-POINT: the coarse-signature evidence merge -----------------
    # (PREREG_W2_STAGE2_CONTEXT_MIN.md, THE RE-POINT AMENDMENT)

    @staticmethod
    def _atom_signature(atom: Dict[str, Any]) -> Optional[str]:
        """The coarse signature DERIVED from a stored atom's own patches.
        learn_effect crops context/after to the changed-cell bbox, which is
        exactly the region _signature hashes of a live frame pair -- so
        _signature(context, after, action) reproduces the live event's
        signature. STABLE under minimisation AND conflict reinstatement:
        DONT_CARE (and any reinstated value) lands in context and after
        TOGETHER, never at a changed cell, so the diff mask, the changed
        values and the bbox shape are untouched. None on anything unreadable
        -- such a record simply never joins the index."""
        try:
            ctx = np.asarray(atom.get("context"))
            out = np.asarray((atom.get("transform") or {}).get("after"))
            if (ctx.ndim != 2 or ctx.size == 0 or ctx.shape != out.shape
                    or not bool((ctx != out).any())):
                return None
            return MDLMint._signature(ctx, out, atom.get("action", 0))
        except Exception:
            return None

    def _refresh_sig_index(self) -> None:
        """THE MAPPING (RE-POINT AMENDMENT): coarse signature -> minted atom
        id, plus the last record per id and the minimised-atom roster.
        Incremental: each stream record is processed ONCE per process
        (_scan_pos); a fresh instance starts at 0 and re-derives the whole
        index from Gamma -- the restart re-link. Superseding appends re-map
        to the same id (the signature is stable under minimisation, so the
        mapping never splits an atom). Where two minted atoms share one
        coarse signature (same transition minted in different games/levels),
        the LATEST record wins the mapping -- one merge target, stated."""
        recs = self.gamma.fabric.query("collective", self.gamma.TOPIC)
        if len(recs) < self._scan_pos:
            self._scan_pos = 0                           # stream re-based: full rescan
        for rec in recs[self._scan_pos:]:
            try:
                aid = rec.get("id")
                atom = rec.get("atom") or {}
                if not aid or atom.get("kind") != "EFFECT":
                    continue
                self._rec_by_id[aid] = rec
                s = self._atom_signature(atom)
                if s is not None:
                    self._sig2id[s] = aid
                    self._id_sig[aid] = s
                if ("context_full" in atom or rec.get("ctx_min")
                        or rec.get("ctx_conflict")):
                    self._min_ids.pop(aid, None)
                    self._min_ids[aid] = None            # most-recently-touched last
            except Exception:
                self.errors += 1
        self._scan_pos = len(recs)

    def _signature_merge(self, sig: str, phi: Dict[str, Any],
                         b: np.ndarray) -> None:
        """THE RE-POINT trigger + THE CONFLICT CLAUSE, run once per
        well-formed changed event. Never raises into the verdict path; the
        verdict is untouched either way."""
        try:
            self._refresh_sig_index()
            aid = self._sig2id.get(sig)
            if aid is not None:
                self._merge_context(aid, phi)
            self._conflict_clause(sig, phi.get("action", 0), b)
        except Exception:
            self.errors += 1                             # never break the verdict path

    def _merge_context(self, aid: str, phi: Dict[str, Any]) -> None:
        """At each observation whose COARSE SIGNATURE matches minted atom
        `aid` -- same change pattern, whatever the surrounding debris, so the
        full key may well differ -- intersect the stored atom's context with
        this observation's (effects.minimise_atom): cells that differ become
        DONT_CARE; changed cells + one ring (and conflict-pinned cells) are
        always retained; the stored context only ever SHRINKS; the original
        full context is preserved in `context_full` on first touch (the undo
        -- Seat 3's disposal ruling is outstanding and NOTHING here deletes
        it, Condition 2). The update is a SUPERSEDING APPEND on the atoms
        stream -- same id, marked `ctx_min` -- never an in-place rewrite:
        Gamma.get reads the LAST record for an id, so the append IS the
        update (archive law: evidence added, never replaced). Same-signature
        patches share the changed-cell bbox, hence the patch shape, by
        construction; a same-KEY re-observation carries an identical raw
        context and no-ops here -- the re-point exists precisely because the
        full key could never see a different-debris re-observation."""
        rec = self._rec_by_id.get(aid)
        if rec is None:
            return
        minimised = _effects.minimise_atom(rec.get("atom") or {},
                                           phi.get("context"))
        if minimised is None:
            return                                   # nothing shrank
        # Restamp the anchor signature: the cache must never outlive the
        # context it was derived from (same write-site family as the
        # mint-time stamp in consider()).
        minimised[_applicability.ASIG_FIELD] = (
            _applicability.anchor_signature(minimised))
        sup = dict(rec)
        sup["atom"] = minimised
        sup["ctx_min"] = True                        # the superseding append, marked
        sup.pop("ctx_conflict", None)                # markers are event-scoped
        self.gamma.fabric.append("collective", self.gamma.TOPIC, sup)
        self._rec_by_id[aid] = sup
        self._min_ids.pop(aid, None)
        self._min_ids[aid] = None

    def _conflict_clause(self, sig: str, action: int, b: np.ndarray) -> None:
        """CONDITION 1 (RE-POINT AMENDMENT, Seat 3: outcome-divergence is
        information, not noise). Same-signature observations cannot diverge --
        the signature hashes the change -- so divergence appears BETWEEN
        signatures: after intersection, a loosened context can come to match
        a frame where a DIFFERENT outcome occurred. When this observation's
        signature DIFFERS from a minimised atom's, the action matches, and
        the before-frame matches that atom's minimised context, the
        distinguishing cells -- where context_full is specific and this
        frame differs from it -- are REINSTATED (_reinstate). Bounded: at
        most CONFLICT_SCAN_CAP minimised atoms per call, most-recently-
        touched first, each pre-screened by the applicability signature
        (dims + palette) before any anchor scan runs."""
        if not self._min_ids:
            return
        bh, bw = b.shape
        fpal: Optional[set] = None
        checked = 0
        for aid in list(self._min_ids)[::-1]:
            if checked >= CONFLICT_SCAN_CAP:
                break
            if self._id_sig.get(aid) == sig:
                continue    # same outcome: intersection territory, no conflict
            rec = self._rec_by_id.get(aid)
            atom = (rec or {}).get("atom") or {}
            full = atom.get("context_full")
            if full is None or int(atom.get("action", -1)) != int(action):
                continue    # nothing to reinstate / a different rule family
            checked += 1
            asig = _applicability.signature_of(atom)     # the prefilter pre-screen
            if asig["h"] > bh or asig["w"] > bw:
                continue
            if fpal is None:
                fpal = {int(v) for v in np.unique(b)}
            if not set(asig["pal"]) <= fpal:
                continue
            ctx = np.asarray(atom.get("context"))
            fl = np.asarray(full)
            if ctx.ndim != 2 or ctx.shape != fl.shape:
                continue
            ph, pw = ctx.shape
            for r, c in _effects._context_anchors(b, ctx):
                region = b[r:r + ph, c:c + pw]
                distinguish = (ctx == _effects.DONT_CARE) & (fl != region)
                if not bool(distinguish.any()):
                    continue    # the FULL context matches here too: no discriminator
                self._reinstate(aid, rec, atom, fl, distinguish)
                break           # one conflict event per atom per consider()

    def _reinstate(self, aid: str, rec: Dict[str, Any], atom: Dict[str, Any],
                   full: np.ndarray, distinguish: np.ndarray) -> None:
        """The conflict clause's write: reinstate the distinguishing cells
        from context_full into the context AND the after-patch (a dropped
        cell is unchanged by construction, so its after value IS its
        context_full value), PIN them (ctx_conflict_cells -- minimise_atom
        keeps pinned cells forever after: divergence tightens, never
        loosens), restamp the anchor signature, supersede with the same id,
        record ctx_conflict on the appended record. context_full itself is
        carried forward UNTOUCHED (Condition 2)."""
        ctx = np.asarray(atom["context"]).copy()
        out = np.asarray((atom.get("transform") or {}).get("after")).copy()
        ctx[distinguish] = full[distinguish]
        out[distinguish] = full[distinguish]
        pins = {(int(r), int(c))
                for r, c in (atom.get("ctx_conflict_cells") or [])}
        pins |= {(int(r), int(c)) for r, c in np.argwhere(distinguish)}
        ctx_lists = [[int(v) for v in row] for row in ctx]
        transform = dict(atom.get("transform") or {})
        transform["before"] = ctx_lists
        transform["after"] = [[int(v) for v in row] for row in out]
        restored = dict(atom)
        restored["context"] = ctx_lists
        restored["transform"] = transform
        restored["ctx_conflict_cells"] = sorted([r, c] for r, c in pins)
        restored[_applicability.ASIG_FIELD] = (
            _applicability.anchor_signature(restored))
        sup = dict(rec)
        sup["atom"] = restored
        sup["ctx_conflict"] = True                   # the event, recorded
        sup.pop("ctx_min", None)                     # markers are event-scoped
        self.gamma.fabric.append("collective", self.gamma.TOPIC, sup)
        self._rec_by_id[aid] = sup
        self._min_ids.pop(aid, None)
        self._min_ids[aid] = None

    # -- the letters-wall watchdog ------------------------------------------------------

    def split(self) -> Dict[str, int]:
        """Accepted mints by atom type: structural (has transform) vs lexical."""
        return dict(self._split)
