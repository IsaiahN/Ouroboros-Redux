"""retention.py -- W2c: THE PLANNER RETAINS WHAT IT LEARNS
(PREREG_W2C_PLANNER_RETENTION.md).

Seat 3: "Every call discovers things about the environment, the objects, and
what applies where -- and discards all of it on return. That is the spent-
discriminator shape again... Retention means the next call starts from what
the last one found rather than from nothing."

THE GENUS this closes: produced-and-destroyed-at-production. The planner
computed memo[(aid, key)] per call and dropped it on return; the composer
re-scanned anchors, re-simulated seams and rebuilt the enabler index per
attempt. Same shape, same fix: ONE store, level-scoped, owned by the W2b
scheduler (PlannerScheduler.retained) and cleared INSIDE its on_level_change /
on_fission -- the two clears it already has. The planner and the composer
receive it as an optional argument (retained=None -> today's per-call
behaviour, byte-identical: that absence IS the undo).

VALIDITY LIVES IN THE KEY, THE LEVEL CLEAR IS THE BOUND. apply_effect is a
pure function of (atom content, state), so every key below carries an ATOM
CONTENT KEY (content_key: sha1 over the fields apply_effect reads -- kind,
ttype, params, context, transform, condition/then/else, parts), computed once
per atom per call (Session.ckey). A superseded atom (minimised context, a
conflict reinstate, a settle) misses by construction, never by a clear someone
remembered to call. Every entry is additionally tagged (game, level): a lookup
under any other (game, level) is a miss AND clears the store (the belt under
the event's braces -- the scope is part of every key, so an entry written
under (game, L) is unreadable under (game, L+1) with NO clear called).

THE SUBSTRUCTURES (caps STATED, insertion-order eviction, no clock):
  (a) THE APPLICATION MEMO  (scope, content key, state key) -> None | result
      state key, with a SEPARATE state store (state key -> array) so results
      dedup (many pairs reach one state). Arrays are stored and served
      writeable=False -- a consumer that mutates raises rather than poisons.
      An evicted state turns every memo entry pointing at it into a counted
      miss (recompute, re-store). ONE memo serves the planner's _run and the
      composer's _simulate: a seam the planner applied is a hit for the
      composer, and vice versa.
  (b) THE PER-STATE NEGATIVE + BAND  a None entry is the matched-nowhere
      record for that exact state (tier 1). Tier 2 carries it ACROSS a board
      change when the change set C is known (inside the search every child is
      parent + C; across calls the previous root and argwhere(prev != cur)):
      a negative for (X, K) plus C licenses, on K' = K + C, a scan of ONLY the
      anchors whose window covers a changed cell (effects._context_anchors'
      `band`) -- off-band anchors were all non-matching on K and K' equals K
      there. RAW-path atoms only (tier2_eligible: EFFECT, no ttype / "NONE"):
      their only scan is the context window. Typed, EFFECT_IF and COMPOSITE
      atoms stay tier 1. A band HIT falls through to the full apply_effect
      (how apply_effect judges is untouched); only the band MISS is served
      from the band (a fresh negative for K', no application fired).
  (c) DEAD-ENDS  (scope, direction, state key, candidate-set key) -> marked,
      where the candidate-set key hashes the sorted (id, content key) pairs
      of the call's pruned ids. Target-independent; a mint or import changes
      the set key and the mark misses. The planner spends `expanded` on a
      re-encountered dead-end exactly as before and skips only the loop.
  (d) THE COMPOSER'S SEAMS  anchors (scope, content key, frame key) ->
      anchor tuple (a SEPARATE structure: an empty anchor list is raw-path-
      only knowledge and is never read as a typed None); the enabler index
      keyed by (scope, pool mark, frame signature dims+palette), FIFO of 8;
      named-anchor stamps (_apply_at) through memo (a) under a content key
      derived from the atom's plus the anchor.

THE INSTRUMENT (out-of-band, the planner's reason_counts pattern): fixed keys
INSTRUMENT_KEYS, counted per Session (one planner call or one compose
attempt -- store.last_call / retention.last_call()) and cumulatively on the
store (store.counts). Never a stream record.

BOUNDS: MEMO_CAP / STATE_BYTES_CAP / DEAD_CAP / ANCHORS_CAP / ENABLERS_CAP
(KNOBS G30-G34, PINNED by the prereg). Evictions and store misses are
COUNTED, never raised. Never the sole holder: every entry is rebuildable from
Gamma + apply_effect; deleting the store mid-level changes cost only.

Deterministic throughout: sha1 content addressing, insertion-order eviction,
no RNG, no wall-clock. Stdlib + numpy only.
"""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from engines.egocentric import effects as _effects

__all__ = ["RetentionStore", "Session", "content_key", "state_key",
           "tier2_eligible", "INSTRUMENT_KEYS", "last_call",
           "MEMO_CAP", "STATE_BYTES_CAP", "DEAD_CAP", "ANCHORS_CAP",
           "ENABLERS_CAP", "FWD", "BWD"]

# ── THE CAPS (KNOBS G30-G34; PINNED by PREREG_W2C_PLANNER_RETENTION.md) ───────
MEMO_CAP = 65_536                 # ~8 calls at the widest observed breadth (8.3k)
STATE_BYTES_CAP = 64 * 1024 * 1024  # >= 2,048 frames at 64x64 int64
DEAD_CAP = 16_384                 # 2x the 4 calls x _MAX_NODES observed ceiling
ANCHORS_CAP = 8_192
ENABLERS_CAP = 8

FWD = "fwd"
BWD = "bwd"

INSTRUMENT_KEYS = ("applied_cold", "memo_hits", "band_anchors", "full_anchors",
                   "dead_end_skips", "store_misses", "evictions",
                   "delta_compares")

# the fields apply_effect reads -- the content key is sha1 over exactly these
_CONTENT_FIELDS = ("kind", "ttype", "params", "context", "transform",
                   "condition", "then", "else", "parts")

_LAST_CALL: List[Dict[str, int]] = [dict.fromkeys(INSTRUMENT_KEYS, 0)]


def last_call() -> Dict[str, int]:
    """Pure read: a copy of the most recently opened Session's counts (a
    planner call or a compose attempt; complete once that call returned)."""
    return dict(_LAST_CALL[0])


def state_key(state: np.ndarray) -> str:
    """THE state key (the planner's own, moved here so planner, scheduler and
    store share ONE hash): sha1 over shape, dtype and bytes."""
    a = np.ascontiguousarray(state)
    h = hashlib.sha1()
    h.update(str(a.shape).encode("utf-8"))
    h.update(a.dtype.str.encode("utf-8"))     # C-level attr: str(dtype) is hot-path slow
    h.update(a.tobytes())
    return h.hexdigest()


def content_key(atom: Optional[Dict[str, Any]]) -> str:
    """sha1 over the fields apply_effect reads. Position-free, id-free: the
    same mechanism under two ids is one key; a superseded atom (same id, new
    context) is a NEW key -- validity lives here, not in a clear."""
    if not isinstance(atom, dict):
        return "none"
    blob = json.dumps({f: atom.get(f) for f in _CONTENT_FIELDS if f in atom},
                      sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def tier2_eligible(atom: Optional[Dict[str, Any]]) -> bool:
    """RAW-path atoms only: kind EFFECT with no ttype (or "NONE") and a
    non-empty 2-D context. Their ONLY scan is the context window, so a
    matched-nowhere negative is exactly "no anchor" and the band carries it.
    Typed atoms (_apply_typed has its own anchor search), EFFECT_IF and
    COMPOSITE never enter tier 2."""
    if not isinstance(atom, dict) or atom.get("kind") != "EFFECT":
        return False
    tt = atom.get("ttype")
    if tt and tt != "NONE":
        return False
    try:
        ctx = np.asarray(atom.get("context"))
    except Exception:
        return False
    return ctx.ndim == 2 and ctx.size > 0


class RetentionStore:
    """THE STORE: one per scheduler, level-scoped, bounded, counted. Every
    public read is a pure lookup plus an instrument bump; every write is an
    insertion-order append with oldest-first eviction at its cap. Scope
    (game, level) is carried in every key AND tracked as the bound-scope:
    binding a different scope clears everything (the belt)."""

    def __init__(self, memo_cap: int = MEMO_CAP,
                 state_bytes_cap: int = STATE_BYTES_CAP,
                 dead_cap: int = DEAD_CAP, anchors_cap: int = ANCHORS_CAP,
                 enablers_cap: int = ENABLERS_CAP) -> None:
        self.memo_cap = max(1, int(memo_cap))
        self.state_bytes_cap = max(0, int(state_bytes_cap))
        self.dead_cap = max(1, int(dead_cap))
        self.anchors_cap = max(1, int(anchors_cap))
        self.enablers_cap = max(1, int(enablers_cap))
        self._scope: Optional[Tuple[str, int]] = None
        # keys: (scope, content key, state key) -> None | result state key
        self._memo: OrderedDict[Tuple[Tuple[str, int], str, str], Optional[str]] = OrderedDict()
        # (scope, state key) -> frozen array
        self._states: OrderedDict[Tuple[Tuple[str, int], str], np.ndarray] = OrderedDict()
        self._state_bytes = 0
        # (scope, direction, state key, candidate-set key) -> marked
        self._dead: OrderedDict[Tuple[Tuple[str, int], str, str, str], bool] = OrderedDict()
        # (scope, content key, frame key) -> anchors
        self._anchors: OrderedDict[Tuple[Tuple[str, int], str, str],
                                   Tuple[Tuple[int, int], ...]] = OrderedDict()
        # (scope, pool mark, frame signature) -> enabler index
        self._enablers: OrderedDict[Tuple[Tuple[str, int], Any, Any],
                                    Dict[str, List[str]]] = OrderedDict()
        self._root: Optional[Tuple[Tuple[str, int], str]] = None  # last root (scope, key)
        self.counts: Dict[str, int] = dict.fromkeys(INSTRUMENT_KEYS, 0)
        self.last_call: Dict[str, int] = dict.fromkeys(INSTRUMENT_KEYS, 0)
        self._call: Optional[Dict[str, int]] = None
        self.errors = 0

    # -- scope, clear, sizes --------------------------------------------------

    def bind(self, game: Any, level: Any) -> Tuple[str, int]:
        """Bind the store to (game, level). A different scope than the one the
        entries were written under is a counted miss AND a clear."""
        scope = (str(game), int(level))
        if self._scope is not None and self._scope != scope:
            self._bump("store_misses")
            self.clear()
        self._scope = scope
        return scope

    def clear(self) -> None:
        """The level-scoped clear (inside the scheduler's on_level_change /
        on_fission). Entries go; the instrument's counts stay."""
        self._memo.clear()
        self._states.clear()
        self._state_bytes = 0
        self._dead.clear()
        self._anchors.clear()
        self._enablers.clear()
        self._root = None
        self._scope = None

    def sizes(self) -> Dict[str, int]:
        """Entry counts per substructure (F2 / F3 read)."""
        return {"memo": len(self._memo), "states": len(self._states),
                "state_bytes": int(self._state_bytes), "dead": len(self._dead),
                "anchors": len(self._anchors), "enablers": len(self._enablers),
                "root": 0 if self._root is None else 1}

    # -- the instrument -------------------------------------------------------

    def open_call(self) -> Dict[str, int]:
        """A fresh per-call count dict; it is ALSO the store's last_call and
        the module's last_call() from this moment (live during the call,
        complete after it returns)."""
        self._call = dict.fromkeys(INSTRUMENT_KEYS, 0)
        self.last_call = self._call
        _LAST_CALL[0] = self._call
        return self._call

    def _bump(self, key: str, n: int = 1) -> None:
        self.counts[key] += int(n)
        if self._call is not None:
            self._call[key] += int(n)

    # -- (a) the application memo + the state store ---------------------------

    def memo_get(self, scope: Tuple[str, int], ckey: str, skey: str
                 ) -> Tuple[bool, Optional[np.ndarray]]:
        """(hit, result). A None result on a hit is the matched-nowhere
        negative. A memo entry whose result state was evicted is a counted
        store miss (the caller recomputes and re-stores)."""
        k = (scope, ckey, skey)
        if k not in self._memo:
            return False, None
        rk = self._memo[k]
        if rk is None:
            self._bump("memo_hits")
            return True, None
        arr = self._states.get((scope, rk))
        if arr is None:
            self._bump("store_misses")
            del self._memo[k]
            return False, None
        self._bump("memo_hits")
        return True, arr

    def negative(self, scope: Tuple[str, int], ckey: str, skey: str) -> bool:
        """Tier 1 read of the matched-nowhere record, no instrument bump (the
        tier-2 precondition, not a served result)."""
        k = (scope, ckey, skey)
        return k in self._memo and self._memo[k] is None

    def memo_put(self, scope: Tuple[str, int], ckey: str, skey: str,
                 res: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Record one application. The result array is frozen (writeable=
        False) and stored under its own state key; the memo points at it.
        Returns the (frozen) array the caller should serve."""
        if res is None:
            self._memo[(scope, ckey, skey)] = None
            self._evict_memo()
            return None
        rk = state_key(res)
        arr = self.state_put(scope, rk, res)
        self._memo[(scope, ckey, skey)] = rk
        self._evict_memo()
        return arr

    def state_put(self, scope: Tuple[str, int], skey: str,
                  arr: np.ndarray) -> np.ndarray:
        """Store a frame under its key, frozen. Dedup: an already-stored key
        serves the stored object. Oldest-first eviction at STATE_BYTES_CAP."""
        k = (scope, skey)
        have = self._states.get(k)
        if have is not None:
            return have
        a = np.asarray(arr)
        if not a.flags.c_contiguous:
            a = np.ascontiguousarray(a)
        a.flags.writeable = False                # frozen: a mutating consumer raises
        self._states[k] = a
        self._state_bytes += int(a.nbytes)
        while self._state_bytes > self.state_bytes_cap and self._states:
            _k, old = self._states.popitem(last=False)
            self._state_bytes -= int(old.nbytes)
            self._bump("evictions")
        return a

    def state_get(self, scope: Tuple[str, int], skey: str) -> Optional[np.ndarray]:
        return self._states.get((scope, skey))

    def _evict_memo(self) -> None:
        while len(self._memo) > self.memo_cap:
            self._memo.popitem(last=False)
            self._bump("evictions")

    # -- (c) dead-ends ----------------------------------------------------------

    def dead(self, scope: Tuple[str, int], direction: str, skey: str,
             setkey: str) -> bool:
        if (scope, direction, skey, setkey) in self._dead:
            self._bump("dead_end_skips")
            return True
        return False

    def mark_dead(self, scope: Tuple[str, int], direction: str, skey: str,
                  setkey: str) -> None:
        self._dead[(scope, direction, skey, setkey)] = True
        while len(self._dead) > self.dead_cap:
            self._dead.popitem(last=False)
            self._bump("evictions")

    # -- (d) the composer's seams ---------------------------------------------

    def anchors_get(self, scope: Tuple[str, int], ckey: str, fkey: str
                    ) -> Optional[Tuple[Tuple[int, int], ...]]:
        got = self._anchors.get((scope, ckey, fkey))
        if got is not None:
            self._bump("memo_hits")
        return got

    def anchors_put(self, scope: Tuple[str, int], ckey: str, fkey: str,
                    anchors: Iterable[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
        tup = tuple((int(r), int(c)) for r, c in anchors)
        self._anchors[(scope, ckey, fkey)] = tup
        while len(self._anchors) > self.anchors_cap:
            self._anchors.popitem(last=False)
            self._bump("evictions")
        return tup

    def enablers_get(self, scope: Tuple[str, int], mark: Any, sig: Any
                     ) -> Optional[Dict[str, List[str]]]:
        got = self._enablers.get((scope, mark, sig))
        if got is not None:
            self._bump("memo_hits")
        return got

    def enablers_put(self, scope: Tuple[str, int], mark: Any, sig: Any,
                     index: Dict[str, List[str]]) -> Dict[str, List[str]]:
        self._enablers[(scope, mark, sig)] = index
        while len(self._enablers) > self.enablers_cap:
            self._enablers.popitem(last=False)
            self._bump("evictions")
        return index

    # -- the root lineage (tier 2 across calls) -------------------------------

    def note_root(self, scope: Tuple[str, int], key: str, frame: np.ndarray) -> None:
        """Retain this call's root (key + frozen frame in the state store) so
        the NEXT call can carry negatives across argwhere(prev != cur)."""
        self.state_put(scope, key, np.array(frame, copy=True))
        self._root = (scope, key)

    def lineage(self, scope: Tuple[str, int], frame: np.ndarray
                ) -> Optional[Tuple[str, np.ndarray]]:
        """(previous root key, changed cells) when a previous root of the
        same scope/shape/dtype is still held; None otherwise (an evicted
        root is a counted store miss). One delta compare, counted."""
        if self._root is None or self._root[0] != scope:
            return None
        prev = self._states.get(self._root)
        if prev is None:
            self._bump("store_misses")
            return None
        cur = np.asarray(frame)
        if prev.shape != cur.shape or prev.dtype != cur.dtype:
            return None
        self._bump("delta_compares")
        return self._root[1], np.argwhere(prev != cur)


class Session:
    """ONE CALL'S VIEW of the store: (game, level)-bound, content keys cached
    per atom id for the call, the call's instrument dict opened. The planner
    holds one per plan_to_identity call; the composer one per compose_attempt.
    Every method is total over malformed input (None atom -> None result) and
    never raises into its caller beyond what apply_effect itself raises."""

    def __init__(self, store: RetentionStore, game: Any, level: Any) -> None:
        self.store = store
        self.scope = store.bind(game, level)
        self.call = store.open_call()
        self._ckeys: Dict[str, str] = {}

    # -- keys -----------------------------------------------------------------

    def ckey(self, aid: Any, atom: Optional[Dict[str, Any]]) -> str:
        """The atom's content key, computed once per atom per call."""
        k = str(aid)
        got = self._ckeys.get(k)
        if got is None:
            got = content_key(atom)
            self._ckeys[k] = got
        return got

    def set_key(self, pairs: Iterable[Tuple[str, str]]) -> str:
        """The candidate-set key: sha1 over the sorted (id, content key) pairs."""
        blob = json.dumps(sorted((str(a), str(c)) for a, c in pairs),
                          separators=(",", ":"))
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()

    # -- (a) + (b): the application -------------------------------------------

    def apply(self, aid: Any, atom: Optional[Dict[str, Any]], state: np.ndarray,
              skey: str, lineage: Optional[Tuple[str, np.ndarray]] = None
              ) -> Optional[np.ndarray]:
        """apply_effect(atom, state) through the memo: tier 1 (exact key),
        then -- for RAW-path atoms with a parent negative and a known change
        set -- the tier-2 band scan (a band MISS is a fresh negative with no
        application fired; a band HIT falls through to the full apply_effect),
        then the cold application, stored. Served arrays are frozen."""
        if not isinstance(atom, dict):
            return None
        ck = self.ckey(aid, atom)
        hit, res = self.store.memo_get(self.scope, ck, skey)
        if hit:
            return res
        if (lineage is not None and tier2_eligible(atom)
                and self.store.negative(self.scope, ck, lineage[0])):
            b = np.asarray(state)
            ctx = np.asarray(atom["context"])
            if b.ndim == 2:
                self.store._bump("band_anchors",
                                 _effects.band_positions(b.shape, ctx.shape,
                                                         lineage[1]))
                if not _effects._context_anchors(b, ctx, band=lineage[1]):
                    return self.store.memo_put(self.scope, ck, skey, None)
        return self._cold(ck, atom, state, skey)

    def _cold(self, ck: str, atom: Dict[str, Any], state: np.ndarray,
              skey: str) -> Optional[np.ndarray]:
        self.store._bump("applied_cold")
        self.store._bump("full_anchors", _grid_positions(atom, state))
        res = _effects.apply_effect(atom, state)
        return self.store.memo_put(self.scope, ck, skey, res)

    def apply_inverse(self, aid: Any, atom: Optional[Dict[str, Any]],
                      state: np.ndarray, skey: str) -> Optional[np.ndarray]:
        """apply_inverse through memo (a) under the derived key ck+':inv'
        (tier 1 only: an inverse is apply_effect on the inverse atom)."""
        if not isinstance(atom, dict):
            return None
        ck = self.ckey(aid, atom) + ":inv"
        hit, res = self.store.memo_get(self.scope, ck, skey)
        if hit:
            return res
        self.store._bump("applied_cold")
        res = _effects.apply_inverse(atom, state)
        return self.store.memo_put(self.scope, ck, skey, res)

    def apply_at(self, aid: Any, atom: Optional[Dict[str, Any]], frame: np.ndarray,
                 fkey: str, anchor: Tuple[int, int], stamp) -> Optional[np.ndarray]:
        """The composer's named-anchor stamp through memo (a) under the key
        ck+'@r,c'. `stamp(atom, frame, anchor)` is the composer's own stamp
        (the cold path); its result is stored frozen."""
        if not isinstance(atom, dict):
            return None
        ck = "%s@%d,%d" % (self.ckey(aid, atom), int(anchor[0]), int(anchor[1]))
        hit, res = self.store.memo_get(self.scope, ck, fkey)
        if hit:
            return res
        self.store._bump("applied_cold")
        res = stamp(atom, frame, anchor)
        return self.store.memo_put(self.scope, ck, fkey, res)

    # -- (c) dead-ends ----------------------------------------------------------

    def dead(self, direction: str, skey: str, setkey: str) -> bool:
        return self.store.dead(self.scope, direction, skey, setkey)

    def mark_dead(self, direction: str, skey: str, setkey: str) -> None:
        self.store.mark_dead(self.scope, direction, skey, setkey)

    # -- (d) the composer's anchors + enabler index ---------------------------

    def anchors(self, aid: Any, atom: Optional[Dict[str, Any]], frame: np.ndarray,
                fkey: str, scan) -> List[Tuple[int, int]]:
        """The candidate's anchors in `frame`, retained under (content key,
        frame key). `scan(frame, atom)` is the composer's own _anchors cold
        path. An empty list is raw-path-only knowledge: it is stored HERE and
        never as a memo None."""
        if not isinstance(atom, dict):
            return []
        ck = self.ckey(aid, atom)
        got = self.store.anchors_get(self.scope, ck, fkey)
        if got is not None:
            return list(got)
        self.store._bump("full_anchors", _grid_positions(atom, frame))
        return list(self.store.anchors_put(self.scope, ck, fkey, scan(frame, atom)))

    def enablers(self, mark: Any, sig: Any, build) -> Dict[str, List[str]]:
        got = self.store.enablers_get(self.scope, mark, sig)
        if got is not None:
            return got
        return self.store.enablers_put(self.scope, mark, sig, build())

    # -- lineage (tier 2 across calls) ----------------------------------------

    def root(self, key: str, frame: np.ndarray) -> Optional[Tuple[str, np.ndarray]]:
        """Lineage from the previous root (if held), then retain this root."""
        lin = self.store.lineage(self.scope, frame)
        self.store.note_root(self.scope, key, frame)
        return lin

    def delta(self, parent: np.ndarray, child: np.ndarray) -> Optional[np.ndarray]:
        """argwhere(parent != child) for same-shape frames -- ONE counted
        delta compare; None when shapes differ (no band can be drawn)."""
        p = np.asarray(parent)
        c = np.asarray(child)
        if p.shape != c.shape:
            return None
        self.store._bump("delta_compares")
        return np.argwhere(p != c)


# ── module-bottom helpers ─────────────────────────────────────────────────────

def _grid_positions(atom: Dict[str, Any], frame: np.ndarray) -> int:
    """The candidate anchor positions a FULL context scan examines on
    `frame`: (bh-ph+1)*(bw-pw+1), 0 when the patch does not fit or the atom
    carries no 2-D context (the instrument's full_anchors unit)."""
    try:
        ctx = np.asarray(atom.get("context"))
        b = np.asarray(frame)
        if ctx.ndim != 2 or b.ndim != 2:
            return 0
        nr, nc = b.shape[0] - ctx.shape[0] + 1, b.shape[1] - ctx.shape[1] + 1
        return int(nr * nc) if nr > 0 and nc > 0 else 0
    except Exception:
        return 0
