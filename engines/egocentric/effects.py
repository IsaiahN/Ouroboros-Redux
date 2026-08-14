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
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

__all__ = ["learn_effect", "apply_effect", "classify_transform", "Gamma",
           "invert_transform", "apply_inverse",
           "encoding_cost_route", "encoding_cost_atom"]


# ── canonical patches and keys ────────────────────────────────────────────────

def _to_lists(a: np.ndarray) -> List[List[int]]:
    return [[int(v) for v in row] for row in np.asarray(a)]


def _key_of(ctx: List[List[int]], out: List[List[int]], action: int) -> str:
    """Stable content key: (before-patch, after-patch, action), position-free."""
    blob = json.dumps({"ctx": ctx, "out": out, "action": int(action)},
                      sort_keys=True, separators=(",", ":"))
    return "eff-" + hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


# ── CK-1a: typed parameterized transforms ─────────────────────────────────────

def _match_translate(b: np.ndarray, a: np.ndarray) -> Optional[Dict[str, Any]]:
    """after == before shifted by (dx,dy), vacated cells a single fill colour, nothing
    shifted out of the bbox but fill. Smallest shift wins (deterministic order)."""
    h, w = b.shape
    cands = sorted(((dx, dy) for dx in range(-(h - 1), h) for dy in range(-(w - 1), w)
                    if (dx, dy) != (0, 0)),
                   key=lambda p: (abs(p[0]) + abs(p[1]), p[0], p[1]))
    for dx, dy in cands:
        ar0, ar1 = max(0, dx), h + min(0, dx)
        ac0, ac1 = max(0, dy), w + min(0, dy)
        in_a = np.zeros((h, w), dtype=bool)
        in_a[ar0:ar1, ac0:ac1] = True
        in_b = np.zeros((h, w), dtype=bool)
        in_b[ar0 - dx:ar1 - dx, ac0 - dy:ac1 - dy] = True
        if not (a[in_a] == b[in_b]).all():
            continue
        fills = a[~in_a]
        if fills.size == 0 or not (fills == fills[0]).all():
            continue
        fill = int(fills[0])
        if not (b[~in_b] == fill).all():
            continue                                      # content vanished -- not a shift
        return {"ttype": "TRANSLATE", "params": {"dx": int(dx), "dy": int(dy), "fill": fill}}
    return None


def classify_transform(before_patch, after_patch) -> Dict[str, Any]:
    """Name the mechanism relating two changed-region bbox patches, exactly or not at all:
    TRANSLATE(dx,dy,fill) / ROTATE(k) / REFLECT(axis) / SCALE(fx,fy,mode) / COLOUR_PERM
    (mapping) / NONE. Pure, deterministic; first exact match wins. TRANSLATE runs first --
    the cheapest description (an object moved) must not be eaten by an incidental symmetry
    (a 1-cell mover's corridor always equals its own reflection); the remaining checks are
    single-comparison and run cheapest-first."""
    none = {"ttype": "NONE", "params": {}}
    b = np.asarray(before_patch)
    a = np.asarray(after_patch)
    if b.ndim != 2 or a.ndim != 2 or b.size == 0 or a.size == 0:
        return none
    same = b.shape == a.shape
    if same and (b == a).all():
        return none                                       # identity is no transform
    if same:
        t = _match_translate(b, a)
        if t:
            return t
    for k in (1, 2, 3):                                   # ROTATE: after == rot90(before, k)
        r = np.rot90(b, k)
        if r.shape == a.shape and (r == a).all():
            return {"ttype": "ROTATE", "params": {"k": int(k)}}
    if same:                                              # REFLECT: h = up-down, v = left-right
        if (np.flipud(b) == a).all():
            return {"ttype": "REFLECT", "params": {"axis": "h"}}
        if (np.fliplr(b) == a).all():
            return {"ttype": "REFLECT", "params": {"axis": "v"}}
    (h, w), (H, W) = b.shape, a.shape                     # SCALE: exact integer factors
    if H % h == 0 and W % w == 0 and (H // h, W // w) != (1, 1):
        fx, fy = H // h, W // w
        if (np.kron(b, np.ones((fx, fy), dtype=b.dtype)) == a).all():
            return {"ttype": "SCALE", "params": {"fx": int(fx), "fy": int(fy), "mode": "up"}}
    if h % H == 0 and w % W == 0 and (h // H, w // W) != (1, 1):
        fx, fy = h // H, w // W
        if (np.kron(a, np.ones((fx, fy), dtype=a.dtype)) == b).all():
            return {"ttype": "SCALE", "params": {"fx": int(fx), "fy": int(fy), "mode": "down"}}
    if same:                                              # COLOUR_PERM: same geometry, injective remap
        mapping: Dict[int, int] = {}
        for s, d in zip(b.ravel().tolist(), a.ravel().tolist(), strict=False):
            if mapping.setdefault(int(s), int(d)) != int(d):
                return none                               # one colour, two fates: not a map
        if len(set(mapping.values())) != len(mapping):
            return none                                   # colours merged: not a perm
        pairs = sorted([s, d] for s, d in mapping.items() if s != d)
        if pairs:
            return {"ttype": "COLOUR_PERM", "params": {"mapping": pairs}}
    return none


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
    atom = {
        "kind": "EFFECT",
        "arity": 2,
        "key": _key_of(ctx, out, action),
        "action": int(action),
        "context": ctx,                                   # canonical before-patch (bbox crop)
        "transform": {"before": ctx, "after": out},       # before-patch -> after-patch
        "changed": int(diff.sum()),                       # what pricing is based on
    }
    t = classify_transform(ctx, out)                      # CK-1a: name the mechanism when exact
    if t["ttype"] != "NONE":
        atom["ttype"] = t["ttype"]
        atom["params"] = t["params"]
    return atom


def _apply_translate(ctx: np.ndarray, params: Dict[str, Any],
                     b: np.ndarray) -> Optional[np.ndarray]:
    """Bind the moving object (the non-fill content of ctx) wherever it sits in the frame
    -- corridor debris and never-seen surroundings included -- and shift it by (dx,dy).
    First row-major match whose destination is clear; None if the op cannot fire."""
    dx, dy = int(params.get("dx", 0)), int(params.get("dy", 0))
    fill = int(params.get("fill", 0))
    m = ctx != fill
    if not m.any() or (dx, dy) == (0, 0):
        return None
    rows, cols = np.flatnonzero(m.any(axis=1)), np.flatnonzero(m.any(axis=0))
    obj = ctx[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    om = obj != fill
    oh, ow = obj.shape
    bh, bw = b.shape
    for r in range(bh - oh + 1):
        for c in range(bw - ow + 1):
            if not (b[r:r + oh, c:c + ow] == obj).all():
                continue
            tr, tc = r + dx, c + dy
            if tr < 0 or tc < 0 or tr + oh > bh or tc + ow > bw:
                continue                                  # would shift off the frame
            res = b.copy()
            res[r:r + oh, c:c + ow][om] = fill            # vacate the source
            tgt = res[tr:tr + oh, tc:tc + ow]
            if not (tgt[om] == fill).all():
                continue                                  # destination blocked
            tgt[om] = obj[om]
            return res
    return None


def _apply_typed(atom: Dict[str, Any], b: np.ndarray) -> Optional[np.ndarray]:
    """PARAMETERIZED application: run the atom's named op at the pattern's position in the
    frame, whatever that position is. None -> caller falls back to the raw exact path."""
    ttype = atom.get("ttype")
    params = atom.get("params") or {}
    ctx = np.asarray(atom["context"])
    if ctx.ndim != 2 or b.ndim != 2:
        return None
    if ttype == "TRANSLATE":
        return _apply_translate(ctx, params, b)
    if ttype == "ROTATE":
        rep = np.rot90(ctx, int(params.get("k", 0)) % 4)
    elif ttype == "REFLECT":
        rep = np.flipud(ctx) if params.get("axis") == "h" else np.fliplr(ctx)
    elif ttype == "SCALE":
        fx, fy = int(params.get("fx", 1)), int(params.get("fy", 1))
        if fx < 1 or fy < 1:
            return None
        rep = (np.kron(ctx, np.ones((fx, fy), dtype=ctx.dtype))
               if params.get("mode") == "up" else ctx[::fx, ::fy])
    elif ttype == "COLOUR_PERM":
        rep = ctx.copy()
        for s, d in (params.get("mapping") or []):
            rep[ctx == int(s)] = int(d)
    else:
        return None
    ph, pw = ctx.shape
    rh, rw = rep.shape
    bh, bw = b.shape
    for r in range(bh - ph + 1):                          # scan for the pattern, apply the op
        for c in range(bw - pw + 1):
            if (b[r:r + ph, c:c + pw] == ctx).all() and r + rh <= bh and c + rw <= bw:
                res = b.copy()
                res[r:r + rh, c:c + rw] = rep
                return res
    return None


def apply_effect(atom: Dict[str, Any], before: np.ndarray) -> Optional[np.ndarray]:
    """Match the atom's context patch anywhere in `before` (exact content, any position);
    write the after-patch there. First match in row-major order; None if no match.
    CK-1a: an atom carrying a ttype tries its PARAMETERIZED op first (the mechanism fires
    in contexts never literally seen); the raw exact-context scan is the fallback."""
    if not atom or atom.get("kind") != "EFFECT":
        return None
    if atom.get("ttype") and atom.get("ttype") != "NONE":
        try:
            res = _apply_typed(atom, np.asarray(before))
        except Exception:
            res = None                                    # typed path must never break raw
        if res is not None:
            return res
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


# ── CK-2b: inverse closure -- typed mechanisms form a group ───────────────────

def invert_transform(ttype: str, params: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """The computable inverse of a typed mechanism, or None if there is none.
    TRANSLATE negates its deltas; ROTATE(k) -> ROTATE(4-k); REFLECT is self-inverse;
    COLOUR_PERM reverses its pairs (injective by construction, checked anyway);
    SCALE swaps up<->down with the same factors. Anything else -- raw atoms, NONE,
    malformed params -- is not cleanly invertible: None, never a guess. Pure."""
    p = dict(params or {})
    if ttype == "TRANSLATE":
        return ("TRANSLATE", {"dx": -int(p.get("dx", 0)), "dy": -int(p.get("dy", 0)),
                              "fill": int(p.get("fill", 0))})
    if ttype == "ROTATE":
        return ("ROTATE", {"k": (4 - int(p.get("k", 0))) % 4})
    if ttype == "REFLECT":
        axis = p.get("axis")
        if axis not in ("h", "v"):
            return None
        return ("REFLECT", {"axis": axis})
    if ttype == "COLOUR_PERM":
        mapping = p.get("mapping") or []
        try:
            inv = sorted([int(d), int(s)] for s, d in mapping)
        except (TypeError, ValueError):
            return None
        if not inv or len({d for d, _ in inv}) != len(inv):
            return None                                   # colours merged: no inverse map
        return ("COLOUR_PERM", {"mapping": inv})
    if ttype == "SCALE":
        fx, fy = int(p.get("fx", 0)), int(p.get("fy", 0))
        mode = p.get("mode")
        if fx < 1 or fy < 1 or mode not in ("up", "down"):
            return None
        return ("SCALE", {"fx": fx, "fy": fy, "mode": "down" if mode == "up" else "up"})
    return None


def apply_inverse(atom: Dict[str, Any], frame: np.ndarray) -> Optional[np.ndarray]:
    """Step a frame BACKWARD through a typed atom: build the inverse atom (after-patch
    becomes the context, the mechanism inverted) and run it through apply_effect. Raw
    atoms name no mechanism -- nothing to invert -> None. Pure; None on any failure.
    A caller planning backward should verify the forward replay (apply_effect of the
    original atom on the result) -- application is context-dependent, inversion is not
    a proof."""
    if not atom or atom.get("kind") != "EFFECT":
        return None
    ttype = atom.get("ttype")
    if not ttype or ttype == "NONE":
        return None                                       # raw atoms are not invertible
    inv = invert_transform(ttype, atom.get("params") or {})
    if inv is None:
        return None
    inv_ttype, inv_params = inv
    transform = atom.get("transform") or {}
    ctx, out = atom.get("context"), transform.get("after")
    if ctx is None or out is None:
        return None
    inv_atom = {
        "kind": "EFFECT",
        "action": atom.get("action"),
        "context": out,                                   # the inverse acts on the AFTER patch
        "transform": {"before": out, "after": ctx},
        "changed": atom.get("changed"),
        "ttype": inv_ttype,
        "params": inv_params,
    }
    try:
        return apply_effect(inv_atom, np.asarray(frame))
    except Exception:
        return None                                       # inversion must never break a caller


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
