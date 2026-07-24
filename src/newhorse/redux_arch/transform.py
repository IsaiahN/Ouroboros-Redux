"""transform.py -- Lane C of the Tether: the R_T FRAME-TRANSFORM bracket, the third residual stream. Lanes A
(R_τ→affordances) and B (R_ρ→goal / don't-die) explain change as per-OBJECT dynamics: a cursor translates, a button
toggles, two bodies couple. Some games change the board by a GLOBAL transform instead -- the whole frame rotates,
reflects, recolours, or shifts. A per-object/translation model has huge residual there (every cell "moved"); a single
whole-frame transform T explains it with a few bits. Detecting that T IS the bracket: it says "the mechanism here is a
global T," which no Lane-A/B organ can express.

Domain-general: names no game, privileges no colour or position. The transform vocabulary is the dihedral group D4
(8 rigid symmetries), a colour PERMUTATION (bijection over the palette), their composition, and a whole-frame
TRANSLATION. detect_global_transform returns the SIMPLEST T (fewest description bits) that maps before→after exactly;
None if no global transform explains the change (i.e. it is a per-object game, correctly left to Lanes A/B).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from collections import Counter
import numpy as np

# The 8 rigid symmetries of the square (D4). Each maps a grid to a grid; shape may change (rot90 of HxW is WxH), so
# callers gate on shape-match with the target. identity is included so a pure recolour is expressible as identity+perm.
GEOMS = {
    "identity": lambda a: a,
    "rot90": lambda a: np.rot90(a, 1),
    "rot180": lambda a: np.rot90(a, 2),
    "rot270": lambda a: np.rot90(a, 3),
    "flip_lr": lambda a: np.fliplr(a),
    "flip_ud": lambda a: np.flipud(a),
    "transpose": lambda a: np.asarray(a).T,
    "anti_transpose": lambda a: np.rot90(a, 2).T,
}
_GEOM_BITS = 3.0                                              # log2(8): which dihedral element


@dataclass(frozen=True)
class Transform:
    kind: str                     # "geom" | "recolour" | "geom+recolour" | "translate"
    name: Optional[str]           # dihedral element name (geom kinds) else None
    detail: Optional[object]      # recolour: frozenset of (from,to); translate: (dr,dc)
    bits: float                   # MDL description length of this transform (the bracket's cost)

    @property
    def key(self) -> Tuple:
        return (self.kind, self.name, self.detail)


def _colour_perm(x, y) -> Optional[frozenset]:
    """If y is a consistent, injective RECOLOUR of x (same shape): a bijection mapping each colour in x to one colour
    in y. Returns the mapping as a frozenset of (from,to) pairs, or None. A non-injective or inconsistent map is not
    a permutation."""
    x, y = np.asarray(x), np.asarray(y)
    if x.shape != y.shape:
        return None
    fwd: Dict[int, int] = {}
    rev: Dict[int, int] = {}
    for a, b in zip(x.ravel().tolist(), y.ravel().tolist()):
        if a in fwd and fwd[a] != b:
            return None                                      # inconsistent (a maps to two colours)
        if b in rev and rev[b] != a:
            return None                                      # non-injective (two colours map to b)
        fwd[a] = b; rev[b] = a
    return frozenset(fwd.items())


def _perm_bits(perm: frozenset) -> float:
    moved = [1 for (a, b) in perm if a != b]
    k = len(perm)
    return len(moved) * float(np.log2(max(2, k)))            # ~ (#recoloured) * log2(palette)


def _is_identity_perm(perm: frozenset) -> bool:
    return all(a == b for (a, b) in perm)


def _detect_translation(before, after, max_shift: int = 8) -> Optional[Tuple[int, int]]:
    """Whole-frame shift by (dr,dc): after == before rolled by (dr,dc) on the overlap, for a NON-ZERO shift that
    actually matches the full overlap. Rejects the trivial (0,0)."""
    b, a = np.asarray(before), np.asarray(after)
    if b.shape != a.shape:
        return None
    H, W = b.shape
    best = None
    for dr in range(-max_shift, max_shift + 1):
        for dc in range(-max_shift, max_shift + 1):
            if dr == 0 and dc == 0:
                continue
            r0, r1 = max(0, dr), min(H, H + dr)
            c0, c1 = max(0, dc), min(W, W + dc)
            if r1 - r0 < H // 2 or c1 - c0 < W // 2:         # require a substantial overlap
                continue
            src = b[r0 - dr:r1 - dr, c0 - dc:c1 - dc]
            dst = a[r0:r1, c0:c1]
            if src.shape == dst.shape and src.size and np.array_equal(src, dst):
                cost = abs(dr) + abs(dc)
                if best is None or cost < best[0]:
                    best = (cost, (dr, dc))
    return best[1] if best else None


def detect_global_transform(before, after) -> Optional[Transform]:
    """The simplest whole-frame transform T with after == T(before), or None if no global transform explains it.
    Preference (fewest bits first): pure geometry < geometry+recolour < pure recolour < translation.

    PRECISION: a global transform is claimed only when a SUBSTANTIAL fraction of cells change -- which is exactly
    when a per-OBJECT model (Lane A/B) has high residual. A few-cell change (one cursor stepping or teleporting) is
    per-object territory even if a global T could formally reproduce it on the sparse background, so we return None
    and leave the game to Lanes A/B. This is the whole point of the residual split."""
    b, a = np.asarray(before), np.asarray(after)
    if np.array_equal(b, a):
        return None                                          # nothing changed -> no bracket
    changed = int((b != a).sum())
    if changed < max(6, int(0.08 * b.size)):                 # too few cells moved -> per-object, not a frame transform
        return None
    # 1) pure geometry (incl. identity=no-op, skipped above) and geometry+recolour
    geom_recolour = None
    for name, g in GEOMS.items():
        gb = np.asarray(g(b))
        if gb.shape != a.shape:
            continue
        if np.array_equal(gb, a):
            if name == "identity":
                continue                                     # identity with equal handled above; unequal impossible
            return Transform("geom", name, None, _GEOM_BITS)
        perm = _colour_perm(gb, a)
        if perm is not None and not _is_identity_perm(perm):
            cand = Transform("recolour" if name == "identity" else "geom+recolour",
                             None if name == "identity" else name,
                             perm, (_perm_bits(perm) if name == "identity" else _GEOM_BITS + _perm_bits(perm)))
            if geom_recolour is None or cand.bits < geom_recolour.bits:
                geom_recolour = cand
    if geom_recolour is not None:
        return geom_recolour
    # 2) whole-frame translation
    t = _detect_translation(b, a)
    if t is not None:
        return Transform("translate", None, t, float(abs(t[0]) + abs(t[1])) + 1.0)
    return None


class TransformProbe:
    """Accumulates which global transform (if any) relates successive frames of a stream. The dominant recurring
    non-None transform is the level's frame-transform bracket; if transitions are mostly None, the game is per-object
    (Lanes A/B) and this correctly stays silent."""
    def __init__(self) -> None:
        self.hits: Counter = Counter()
        self.n_obs = 0
        self.n_transform = 0

    def observe(self, before, after) -> Optional[Transform]:
        self.n_obs += 1
        t = detect_global_transform(before, after)
        if t is not None:
            self.hits[t.key] += 1
            self.n_transform += 1
        return t

    def dominant(self) -> Optional[Tuple[Tuple, int]]:
        if not self.hits:
            return None
        key, cnt = self.hits.most_common(1)[0]
        return (key, cnt)

    def frac_transform(self) -> float:
        return self.n_transform / self.n_obs if self.n_obs else 0.0
