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

B8: when the whole-bbox classifier is NONE, classify_object_transform segments the changed
region into connected components and names the ONE-coherent-object mechanism (mover TRANSLATE
in clutter, OBJ_APPEAR / OBJ_VANISH, shape-bound COLOUR_PERM); shape signatures are normalized
relative offsets, never absolute coordinates. B9: ConditionalMiner buffers (pre, action, post)
per action, bounded, and constructs arity-3 EFFECT_IF atoms when the same action diverges under
a small REMOTE predicate; apply_effect checks the condition and runs the selected branch.

Deterministic throughout: no RNG, no wall-clock. Stdlib + numpy only; atoms are JSON-serializable
(lists, never ndarrays) so Gamma can store them in the fabric.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

__all__ = ["learn_effect", "apply_effect", "classify_transform", "Gamma",
           "classify_object_transform", "ConditionalMiner",
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


# ── B8: object-level transform classifier ─────────────────────────────────────
#
# classify_transform demands the WHOLE changed-region bbox to transform exactly; one
# coherent object moving or changing inside cluttered context never satisfies that
# (typed=3/585 -- the g7 precondition). classify_object_transform segments the CHANGED
# region into connected components and names the single-object mechanism. Shape
# signatures are NORMALIZED relative cell offsets [dr, dc, colour] -- never absolute
# board coordinates: the same object at any position is the same shape.

def _components(mask: np.ndarray) -> List[List[Tuple[int, int]]]:
    """8-connected components of a boolean mask, in row-major discovery order."""
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    comps: List[List[Tuple[int, int]]] = []
    for r0 in range(h):
        for c0 in range(w):
            if not mask[r0, c0] or seen[r0, c0]:
                continue
            seen[r0, c0] = True
            stack = [(r0, c0)]
            comp: List[Tuple[int, int]] = []
            while stack:
                r, c = stack.pop()
                comp.append((r, c))
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and mask[nr, nc] and not seen[nr, nc]:
                            seen[nr, nc] = True
                            stack.append((nr, nc))
            comps.append(sorted(comp))
    return comps


def _shape_of(cells: List[Tuple[int, int]], grid: np.ndarray) -> List[List[int]]:
    """Normalized shape signature: [dr, dc, colour] offsets from the component's own
    origin (min row, min col) -- relative, NEVER absolute coordinates."""
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    return sorted([r - r0, c - c0, int(grid[r, c])] for r, c in cells)


def _match_object_translate(b: np.ndarray, a: np.ndarray,
                            src: List[Tuple[int, int]],
                            dst: List[Tuple[int, int]]) -> Optional[Dict[str, Any]]:
    """A component disappears at src (one uniform fill restored), an identically
    shaped+coloured component appears at dst where that same fill used to be."""
    if len(src) != len(dst):
        return None
    fills = {int(a[r, c]) for r, c in src}
    if len(fills) != 1:
        return None                                       # the vacated ground is not uniform
    fill = fills.pop()
    if any(int(b[r, c]) != fill for r, c in dst):
        return None                                       # the destination was not clear ground
    shape = _shape_of(src, b)
    if shape != _shape_of(dst, a):
        return None                                       # not the same object
    dx = min(r for r, _ in dst) - min(r for r, _ in src)
    dy = min(c for _, c in dst) - min(c for _, c in src)
    return {"ttype": "TRANSLATE",
            "params": {"dx": int(dx), "dy": int(dy), "fill": fill, "shape": shape}}


def classify_object_transform(before, after) -> Dict[str, Any]:
    """Name the ONE-coherent-object mechanism inside cluttered context, exactly or not
    at all: mover TRANSLATE (component vanishes at A, identical shape appears at B,
    background restored) / OBJ_APPEAR / OBJ_VANISH (component present in exactly one
    frame) / COLOUR_PERM (same cells, colours consistently remapped, injective, bound
    to the component's shape). Pure, deterministic; NONE on anything else."""
    none = {"ttype": "NONE", "params": {}}
    b = np.asarray(before)
    a = np.asarray(after)
    if b.ndim != 2 or a.ndim != 2 or b.shape != a.shape or b.size == 0:
        return none
    diff = b != a
    if not diff.any():
        return none
    comps = _components(diff)

    if len(comps) == 2:                                   # mover: vanish at A, appear at B
        for src, dst in ((comps[0], comps[1]), (comps[1], comps[0])):
            t = _match_object_translate(b, a, src, dst)
            if t is not None:
                return t
        return none

    if len(comps) != 1:
        return none                                       # not ONE coherent object

    cells = comps[0]
    bvals = {int(b[r, c]) for r, c in cells}
    avals = {int(a[r, c]) for r, c in cells}
    if len(bvals) == 1 and len(avals) > 1:                # content in AFTER only
        return {"ttype": "OBJ_APPEAR",
                "params": {"shape": _shape_of(cells, a), "fill": bvals.pop()}}
    if len(avals) == 1 and len(bvals) > 1:                # content in BEFORE only
        return {"ttype": "OBJ_VANISH",
                "params": {"shape": _shape_of(cells, b), "fill": avals.pop()}}
    mapping: Dict[int, int] = {}                          # same cells, remapped colours
    for r, c in cells:
        s, d = int(b[r, c]), int(a[r, c])
        if mapping.setdefault(s, d) != d:
            return none                                   # one colour, two fates: not a map
    if len(set(mapping.values())) != len(mapping):
        return none                                       # colours merged: not a perm
    return {"ttype": "COLOUR_PERM",
            "params": {"mapping": sorted([s, d] for s, d in mapping.items()),
                       "shape": _shape_of(cells, b)}}


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
    if t["ttype"] == "NONE":
        t = classify_object_transform(ctx, out)           # B8: one coherent object in clutter
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


def _iter_shape_anchors(b: np.ndarray, shape: List[List[int]]):
    """Yield (r, c) anchors where every shape cell [dr, dc, colour] matches the frame,
    row-major. The shape is relative; the anchor supplies the absolute position."""
    hr = max(s[0] for s in shape)
    wr = max(s[1] for s in shape)
    bh, bw = b.shape
    for r in range(bh - hr):
        for c in range(bw - wr):
            if all(int(b[r + dr, c + dc]) == int(v) for dr, dc, v in shape):
                yield r, c


def _apply_shape_translate(shape: List[List[int]], params: Dict[str, Any],
                           b: np.ndarray) -> Optional[np.ndarray]:
    """B8: bind the object BY ITS SHAPE wherever it sits -- clutter and all -- vacate the
    source to fill and land it (dx, dy) away. First anchor whose destination is clear."""
    dx, dy = int(params.get("dx", 0)), int(params.get("dy", 0))
    fill = int(params.get("fill", 0))
    if not shape or (dx, dy) == (0, 0):
        return None
    bh, bw = b.shape
    for r, c in _iter_shape_anchors(b, shape):
        cells = [(r + dr, c + dc) for dr, dc, _v in shape]
        tgt = [(rr + dx, cc + dy) for rr, cc in cells]
        if any(not (0 <= rr < bh and 0 <= cc < bw) for rr, cc in tgt):
            continue                                      # would shift off the frame
        res = b.copy()
        for rr, cc in cells:
            res[rr, cc] = fill                            # vacate the source
        if any(int(res[rr, cc]) != fill for rr, cc in tgt):
            continue                                      # destination blocked
        for (rr, cc), (_dr, _dc, v) in zip(tgt, shape, strict=True):
            res[rr, cc] = int(v)
        return res
    return None


def _apply_object_typed(ttype: str, params: Dict[str, Any],
                        b: np.ndarray) -> Optional[np.ndarray]:
    """B8: shape-bound ops. OBJ_APPEAR stamps the shape on the first clear ground of its
    footprint; OBJ_VANISH erases the first shape occurrence to fill; a shape-carrying
    COLOUR_PERM remaps ONLY the object's cells, never look-alike clutter."""
    shape = params.get("shape") or []
    if not shape:
        return None
    fill = int(params.get("fill", 0))
    if ttype == "OBJ_APPEAR":
        ground = [[s[0], s[1], fill] for s in shape]
        for r, c in _iter_shape_anchors(b, ground):
            res = b.copy()
            for dr, dc, v in shape:
                res[r + dr, c + dc] = int(v)
            return res
        return None
    if ttype == "OBJ_VANISH":
        for r, c in _iter_shape_anchors(b, shape):
            res = b.copy()
            for dr, dc, _v in shape:
                res[r + dr, c + dc] = fill
            return res
        return None
    if ttype == "COLOUR_PERM":
        mapping = {int(s): int(d) for s, d in (params.get("mapping") or [])}
        for r, c in _iter_shape_anchors(b, shape):
            res = b.copy()
            for dr, dc, v in shape:
                res[r + dr, c + dc] = mapping.get(int(v), int(v))
            return res
        return None
    return None


def _apply_typed(atom: Dict[str, Any], b: np.ndarray) -> Optional[np.ndarray]:
    """PARAMETERIZED application: run the atom's named op at the pattern's position in the
    frame, whatever that position is. None -> caller falls back to the raw exact path."""
    ttype = atom.get("ttype")
    params = atom.get("params") or {}
    ctx = np.asarray(atom["context"])
    if ctx.ndim != 2 or b.ndim != 2:
        return None
    if ttype in ("OBJ_APPEAR", "OBJ_VANISH") or (ttype == "COLOUR_PERM"
                                                 and params.get("shape")):
        return _apply_object_typed(ttype, params, b)      # B8: shape-bound ops
    if ttype == "TRANSLATE":
        if params.get("shape"):
            return _apply_shape_translate(params["shape"], params, b)
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
    in contexts never literally seen); the raw exact-context scan is the fallback.
    B9: an EFFECT_IF atom checks its remote condition cells first and runs the branch
    the world selected."""
    if not atom:
        return None
    if atom.get("kind") == "EFFECT_IF":
        try:
            return _apply_effect_if(atom, np.asarray(before))
        except Exception:
            return None                                   # conditionals must never break a caller
    if atom.get("kind") != "EFFECT":
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
        out = {"dx": -int(p.get("dx", 0)), "dy": -int(p.get("dy", 0)),
               "fill": int(p.get("fill", 0))}
        if p.get("shape"):
            out["shape"] = [list(s) for s in p["shape"]]  # B8: colours survive a move
        return ("TRANSLATE", out)
    if ttype in ("OBJ_APPEAR", "OBJ_VANISH"):             # B8: mutual inverses
        shape = p.get("shape") or []
        if not shape:
            return None
        return ("OBJ_VANISH" if ttype == "OBJ_APPEAR" else "OBJ_APPEAR",
                {"shape": [list(s) for s in shape], "fill": int(p.get("fill", 0))})
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
        out = {"mapping": inv}
        if p.get("shape"):                                # B8: the inverse hunts the AFTER colours
            fwd = {int(s): int(d) for s, d in mapping}
            out["shape"] = sorted([int(s[0]), int(s[1]), fwd.get(int(s[2]), int(s[2]))]
                                  for s in p["shape"])
        return ("COLOUR_PERM", out)
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


# ── B9: conditional effects -- arity-3 EFFECT_IF atoms ────────────────────────

def _apply_effect_if(atom: Dict[str, Any], b: np.ndarray) -> Optional[np.ndarray]:
    """Check the remote condition cells; run then / else. A false condition with no
    else-transform means the action does nothing: the unchanged frame, not None."""
    cells = (atom.get("condition") or {}).get("cells") or []
    if not cells or b.ndim != 2:
        return None
    bh, bw = b.shape
    holds = True
    for r, c, v in cells:
        if not (0 <= int(r) < bh and 0 <= int(c) < bw):
            return None                                   # the predicate is off this frame
        if int(b[int(r), int(c)]) != int(v):
            holds = False
            break
    branch = atom.get("then") if holds else atom.get("else")
    if branch is None:
        return None if holds else b.copy()                # inert else-branch: nothing happens
    return apply_effect(branch, b)


class ConditionalMiner:
    """B9: the arity-3 constructor. A bounded history of (pre, action, post) frames per
    action; when the SAME action yields DIVERGENT outcomes and the pre-frames differ only
    on a small REMOTE cell set (outside both changed regions), that set is the predicate:
    construct EFFECT_IF {condition: {cells: [[r, c, expected]]}, then, else}. The then
    branch is the observation that changed the frame; an inert other-branch is else=None.
    Pure and bounded: no RNG, no wall-clock, history capped per key and across keys."""

    def __init__(self, per_key: int = 8, max_keys: int = 16, max_condition_cells: int = 4):
        self.per_key = max(2, int(per_key))
        self.max_keys = max(1, int(max_keys))
        self.max_condition_cells = max(1, int(max_condition_cells))
        self._history: Dict[int, List[Tuple[np.ndarray, np.ndarray]]] = {}
        self.constructed: Dict[str, Dict[str, Any]] = {}  # key -> EFFECT_IF atom
        self.errors: int = 0

    def history_len(self, action: int) -> int:
        return len(self._history.get(int(action), []))

    def feed(self, pre_frame, action, post_frame) -> Optional[Dict[str, Any]]:
        """One observed transition in; at most one newly constructed EFFECT_IF out."""
        try:
            pre = np.asarray(pre_frame)
            post = np.asarray(post_frame)
            if pre.ndim != 2 or pre.shape != post.shape or pre.size == 0:
                return None
            act = int(action)
            hist = self._history.setdefault(act, [])
            atom = None
            for p0, q0 in hist:
                if p0.shape != pre.shape:
                    continue
                atom = self._mine(act, p0, q0, pre, post)
                if atom is not None:
                    break
            hist.append((pre.copy(), post.copy()))
            del hist[:-self.per_key]                      # bounded per key
            while len(self._history) > self.max_keys:     # bounded across keys (FIFO)
                self._history.pop(next(iter(self._history)))
            if atom is not None and atom["key"] not in self.constructed:
                self.constructed[atom["key"]] = atom
                return atom
            return None
        except Exception:
            self.errors += 1
            return None

    def _mine(self, action: int, pre1: np.ndarray, post1: np.ndarray,
              pre2: np.ndarray, post2: np.ndarray) -> Optional[Dict[str, Any]]:
        d1 = pre1 != post1
        d2 = pre2 != post2
        sig1 = sorted((int(r), int(c), int(pre1[r, c]), int(post1[r, c]))
                      for r, c in np.argwhere(d1))
        sig2 = sorted((int(r), int(c), int(pre2[r, c]), int(post2[r, c]))
                      for r, c in np.argwhere(d2))
        if sig1 == sig2:
            return None                                   # same outcome: nothing conditional
        cond = [(int(r), int(c)) for r, c in np.argwhere(pre1 != pre2)]
        if not cond or len(cond) > self.max_condition_cells:
            return None                                   # no predicate, or not a SMALL one
        if any(d1[r, c] or d2[r, c] for r, c in cond):
            return None                                   # the predicate must be REMOTE
        if d1.any():                                      # then = the branch that changed things
            then_pre, then_post, else_pre, else_post = pre1, post1, pre2, post2
        else:
            then_pre, then_post, else_pre, else_post = pre2, post2, pre1, post1
        then_atom = learn_effect(then_pre, action, then_post)
        if then_atom is None or then_atom.get("kind") != "EFFECT":
            return None
        else_atom = learn_effect(else_pre, action, else_post)
        if else_atom is not None and else_atom.get("kind") != "EFFECT":
            else_atom = None                              # INERT: no else transform
        cells = sorted([r, c, int(then_pre[r, c])] for r, c in cond)
        blob = json.dumps({"action": action, "cells": cells, "then": then_atom["key"]},
                          sort_keys=True, separators=(",", ":"))
        return {
            "kind": "EFFECT_IF",
            "arity": 3,
            "key": "effif-" + hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16],
            "action": action,
            "condition": {"cells": cells},
            "then": then_atom,
            "else": else_atom,
            "changed": int(then_atom.get("changed", 0)),
        }


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
        typ = ("structural"
               if (atom.get("transform") is not None or atom.get("kind") == "EFFECT_IF")
               else "lexical")
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
        if atom.get("kind") in ("EFFECT", "EFFECT_IF"):
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
