"""W1a: the EFFECT constructor -- arity-two-over-TIME atoms, canonically keyed, plus typed Gamma.

One contact event (before, action, after) teaches ONE atom: the minimal bounding box around the
changed region, cropped to a before-patch (the CONTEXT) and an after-patch (the TRANSFORM target).
The key is a stable hash of (before-patch content, after-patch content, action) with the bbox
position REMOVED -- the same mechanism at two positions is ONE atom (translation invariance);
different transforms are different atoms. A contact that changes nothing is INERT, ground-priced,
never an EFFECT.

Gamma is the typed hierarchical store on the fabric: EFFECT atoms are "structural"; anything
without a transform is "lexical". compose() memoizes a sequence of ids into a COMPOSITE entry
that get/apply/compose accept exactly like an atom id (composites of composites allowed).
Falsified entries NARROW (a scoped narrowing record) -- they are never deleted.

Pricing: the atom's encoding cost is the size of its canonical patches (changed-cells based),
NOT the board size; a route's cost scales with its total elements. At n=1 a 1-cell recolour atom
must already price below a 3-step route -- that inequality is the acceptance gate.

Deterministic throughout: no RNG, no wall-clock. Stdlib + numpy only; atoms are JSON-serializable
(lists, never ndarrays) so Gamma can store them in the fabric.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

import numpy as np

__all__ = ["learn_effect", "apply_effect", "Gamma",
           "encoding_cost_route", "encoding_cost_atom"]


# ── canonical patches and keys ────────────────────────────────────────────────

def _to_lists(a: np.ndarray) -> List[List[int]]:
    return [[int(v) for v in row] for row in np.asarray(a)]


def _key_of(ctx: List[List[int]], out: List[List[int]], action: int) -> str:
    """Stable content key: (before-patch, after-patch, action), position-free."""
    blob = json.dumps({"ctx": ctx, "out": out, "action": int(action)},
                      sort_keys=True, separators=(",", ":"))
    return "eff-" + hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def learn_effect(before: np.ndarray, action: int, after: np.ndarray) -> Optional[Dict[str, Any]]:
    """Learn ONE atom from ONE contact event. Empty change -> INERT (ground-priced)."""
    b = np.asarray(before)
    a = np.asarray(after)
    if b.shape != a.shape:
        return None
    diff = b != a
    if not diff.any():
        return {"kind": "INERT", "arity": 2, "action": int(action), "changed": 0}
    rows = np.flatnonzero(diff.any(axis=1))
    cols = np.flatnonzero(diff.any(axis=0))
    r0, r1 = int(rows[0]), int(rows[-1])
    c0, c1 = int(cols[0]), int(cols[-1])
    ctx = _to_lists(b[r0:r1 + 1, c0:c1 + 1])
    out = _to_lists(a[r0:r1 + 1, c0:c1 + 1])
    return {
        "kind": "EFFECT",
        "arity": 2,
        "key": _key_of(ctx, out, action),
        "action": int(action),
        "context": ctx,                                   # canonical before-patch (bbox crop)
        "transform": {"before": ctx, "after": out},       # before-patch -> after-patch
        "changed": int(diff.sum()),                       # what pricing is based on
    }


def apply_effect(atom: Dict[str, Any], before: np.ndarray) -> Optional[np.ndarray]:
    """Match the atom's context patch anywhere in `before` (exact content, any position);
    write the after-patch there. First match in row-major order; None if no match."""
    if not atom or atom.get("kind") != "EFFECT":
        return None
    ctx = np.asarray(atom["context"])
    out = np.asarray(atom["transform"]["after"])
    b = np.asarray(before)
    ph, pw = ctx.shape
    bh, bw = b.shape
    for r in range(bh - ph + 1):
        for c in range(bw - pw + 1):
            if (b[r:r + ph, c:c + pw] == ctx).all():
                res = b.copy()
                res[r:r + ph, c:c + pw] = out
                return res
    return None


# ── Gamma: the typed hierarchical store on the fabric ─────────────────────────

class Gamma:
    """Typed store over KnowledgeFabric's collective "atoms" stream. EFFECT atoms are
    "structural" (they carry a transform); atoms without one are "lexical". Composites
    are stored in the same stream and their ids are first-class atom ids."""

    TOPIC = "atoms"
    NARROW_TOPIC = "atom_narrowings"

    def __init__(self, fabric):
        self.fabric = fabric

    # -- store -------------------------------------------------------------------
    def _next_ordinal(self) -> int:
        return len(self.fabric.query("collective", self.TOPIC))

    def add(self, atom: Dict[str, Any], game: str, level: int) -> str:
        typ = "structural" if atom.get("transform") is not None else "lexical"
        aid = "%s:%d" % (atom.get("key", atom.get("kind", "atom")), self._next_ordinal())
        self.fabric.append("collective", self.TOPIC, {
            "id": aid, "type": typ, "game": str(game), "level": int(level),
            "atom": dict(atom),
        })
        return aid

    def get(self, aid: str) -> Optional[Dict[str, Any]]:
        recs = self.fabric.query("collective", self.TOPIC, where=lambda r: r.get("id") == aid)
        if not recs:
            return None
        rec = recs[-1]
        return rec.get("atom") if rec.get("atom") is not None else rec

    # -- composition: memoization above the leaves ---------------------------------
    def compose(self, ids: List[str], game: str, level: int) -> Optional[str]:
        if not ids or any(self.get(i) is None for i in ids):
            return None
        parts = [str(i) for i in ids]
        blob = json.dumps(parts, separators=(",", ":"))
        key = "cmp-" + hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]
        cid = "%s:%d" % (key, self._next_ordinal())
        composite = {"kind": "COMPOSITE", "key": key, "parts": parts}
        self.fabric.append("collective", self.TOPIC, {
            "id": cid, "type": "structural", "kind": "COMPOSITE", "parts": parts,
            "game": str(game), "level": int(level), "atom": composite,
        })
        return cid

    def apply(self, aid: str, before: np.ndarray) -> Optional[np.ndarray]:
        atom = self.get(aid)
        if atom is None:
            return None
        if atom.get("kind") == "COMPOSITE":
            cur = np.asarray(before)
            for pid in atom["parts"]:
                cur = self.apply(pid, cur)
                if cur is None:
                    return None
            return cur
        if atom.get("kind") == "EFFECT":
            return apply_effect(atom, before)
        return None                                       # INERT / lexical: nothing to run

    # -- narrowing: falsified entries are scoped out, never deleted ------------------
    def narrow(self, aid: str, game: str, level: int) -> None:
        self.fabric.append("collective", self.NARROW_TOPIC,
                           {"id": aid, "game": str(game), "level": int(level)})

    def valid_in(self, aid: str, game: str, level: int) -> bool:
        hits = self.fabric.query(
            "collective", self.NARROW_TOPIC,
            where=lambda r: (r.get("id") == aid and r.get("game") == str(game)
                             and r.get("level") == int(level)),
            limit=1)
        return not hits


# ── pricing: the notation's economics ─────────────────────────────────────────

def encoding_cost_route(route) -> float:
    """A route is paid per element: every coordinate/step component costs. Scales with length."""
    total = 0
    for step in route:
        try:
            total += len(step)
        except TypeError:
            total += 1
    return 2.0 * float(total)


def encoding_cost_atom(atom: Optional[Dict[str, Any]]) -> float:
    """The atom costs its canonical patch size (changed cells), NOT the board size."""
    if not atom:
        return float("inf")
    changed = atom.get("changed")
    if changed is None and atom.get("transform") is not None:
        b = np.asarray(atom["transform"]["before"])
        a = np.asarray(atom["transform"]["after"])
        changed = int((b != a).sum()) if b.shape == a.shape else int(a.size)
    return 1.0 + float(changed or 0)
