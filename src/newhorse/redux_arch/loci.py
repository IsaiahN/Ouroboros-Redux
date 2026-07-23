"""
loci.py -- PERSISTENT-IDENTITY tracking (`_track`). The Tether §3.5 structural precondition: "without retained
identity there is no diff, only two unrelated piles of residual." A boundary diff that compares colour histograms
(what `level_delta` did) cannot say *which* object transferred and *which* is new -- it only sees colours come and
go. Identity is what turns that into TRANSFERRED / BROKEN / NOVEL over actual objects.

A `Locus` is an object with a STABLE id that survives:
  * translation  -- it moved (matched by nearest continuation),
  * recolour     -- same mask, new colour (identity does NOT depend on colour; the shape signature is colourless),
  * reshape/grow -- it changed size a little (fuzzy fallback: size-tolerant nearest match),
  * level redraw -- an object present on both sides of a board redraw keeps its id (⇒ TRANSFERRED for the diff),
                    while genuinely new objects get fresh ids (⇒ NOVEL) and vanished ones decay out.

Colourless shape signatures are the point: an object is WHAT-and-WHERE, not what-colour, so a recolour is a
property update on the same identity rather than a death + birth. This is domain-general -- it names no game.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, FrozenSet
import numpy as np
from scipy import ndimage as _ndi

Cell = Tuple[int, int]


@dataclass
class Locus:
    id: int
    colour: int
    centroid: Tuple[float, float]
    bbox: Tuple[int, int, int, int]                 # r0, c0, r1, c1 (inclusive)
    size: int
    shape: FrozenSet[Cell]                          # cell offsets from bbox top-left -- translation-invariant
    age: int = 1                                    # frames this identity has existed
    last_seen: int = 0
    missing: int = 0                                # consecutive frames unseen (decays out past `grace`)
    _matched: bool = field(default=False, repr=False)


def _background(frame: np.ndarray) -> int:
    vals, cnts = np.unique(np.asarray(frame), return_counts=True)
    return int(vals[int(np.argmax(cnts))])


def _segment(frame: np.ndarray, bg: int, min_size: int, max_frac: float) -> List[dict]:
    f = np.asarray(frame)
    h, w = f.shape
    area = h * w
    objs: List[dict] = []
    for colour in (int(c) for c in np.unique(f)):
        if colour == bg:
            continue
        lab, k = _ndi.label(f == colour)            # 4-connectivity
        for i in range(1, k + 1):
            ys, xs = np.where(lab == i)
            size = int(ys.size)
            if size < min_size or size > max_frac * area:
                continue
            r0, c0, r1, c1 = int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())
            shape = frozenset((int(r - r0), int(c - c0)) for r, c in zip(ys, xs))
            objs.append(dict(colour=colour, centroid=(float(ys.mean()), float(xs.mean())),
                             bbox=(r0, c0, r1, c1), size=size, shape=shape))
    return objs


def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class LociTracker:
    """Assigns and maintains stable object ids across a frame stream. `observe(frame)` updates the table and returns
    the live loci. Identity survives translation/recolour/reshape/redraw within the gates below."""

    def __init__(self, min_size: int = 2, max_frac: float = 0.5, grace: int = 3,
                 gate_exact: float = 20.0, gate_fuzzy: float = 6.0, size_tol: float = 2.0):
        self.min_size = int(min_size)
        self.max_frac = float(max_frac)
        self.grace = int(grace)
        self.gate_exact = float(gate_exact)         # exact-shape match: strong evidence, generous distance gate
        self.gate_fuzzy = float(gate_fuzzy)         # reshape fallback: tight distance gate
        self.size_tol = float(size_tol)             # fuzzy match size ratio must be within [1/tol, tol]
        self._loci: Dict[int, Locus] = {}
        self._next_id = 0
        self._t = -1

    def _new(self, o: dict, t: int) -> Locus:
        lid = self._next_id
        self._next_id += 1
        self._loci[lid] = Locus(id=lid, colour=o["colour"], centroid=o["centroid"], bbox=o["bbox"],
                                size=o["size"], shape=o["shape"], age=1, last_seen=t, missing=0)
        return self._loci[lid]

    def observe(self, frame, t: Optional[int] = None) -> List[Locus]:
        self._t = self._t + 1 if t is None else t
        t = self._t
        bg = _background(frame)
        objs = _segment(frame, bg, self.min_size, self.max_frac)
        live = [l for l in self._loci.values() if l.missing <= self.grace]
        for l in live:
            l._matched = False

        # match biggest objects first (most reliable), one-to-one
        for o in sorted(objs, key=lambda x: -x["size"]):
            cand = None
            # 1) exact colourless shape (handles recolour + translation) -> nearest unmatched
            exact = [l for l in live if not l._matched and l.shape == o["shape"]]
            if exact:
                best = min(exact, key=lambda l: _dist(l.centroid, o["centroid"]))
                if _dist(best.centroid, o["centroid"]) <= self.gate_exact:
                    cand = best
            # 2) fuzzy: size-tolerant nearest (handles reshape/grow)
            if cand is None:
                fuzzy = [l for l in live if not l._matched
                         and (1.0 / self.size_tol) <= (o["size"] / max(1, l.size)) <= self.size_tol
                         and _dist(l.centroid, o["centroid"]) <= self.gate_fuzzy]
                if fuzzy:
                    cand = min(fuzzy, key=lambda l: _dist(l.centroid, o["centroid"]) + abs(l.size - o["size"]))
            if cand is None:
                self._new(o, t)                     # genuinely new object -> fresh id
            else:                                   # continuation -> keep id, update properties
                cand._matched = True
                cand.colour = o["colour"]; cand.centroid = o["centroid"]; cand.bbox = o["bbox"]
                cand.size = o["size"]; cand.shape = o["shape"]
                cand.age += 1; cand.last_seen = t; cand.missing = 0

        # unmatched live loci age their absence; drop past grace
        for l in live:
            if not l._matched:
                l.missing += 1
        self._loci = {i: l for i, l in self._loci.items() if l.missing <= self.grace}
        return self.loci()

    def loci(self) -> List[Locus]:
        """Currently-present loci (missing==0), stable-id order."""
        return sorted((l for l in self._loci.values() if l.missing == 0), key=lambda l: l.id)

    def ids(self) -> set:
        return {l.id for l in self._loci.values() if l.missing == 0}

    def get(self, lid: int) -> Optional[Locus]:
        return self._loci.get(lid)
