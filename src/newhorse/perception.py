"""
perception.py -- THE MAP SS9.2: full-resolution perception with object permanence.

Hard bounds (constitutional, MAP SS9.3 / SSVIII):
  * NEVER DOWNSAMPLE. ARC grids are symbolic, not natural images -- a 5-pixel glyph is an exact
    symbol; averaging destroys it (E1, "three receipts"). check_no_downsampling() enforces it.

Principles (MAP SS9.2, grounded via the FMap on Simon's near-decomposability):
  * SEGMENTATION = near-decomposable clusters: cells that cohere (connected, same symbol) are ONE
    object; the boundary is where cohesion drops. Segmentation is narrated as a REVISABLE BELIEF,
    never a fact (`Object.belief=True`) -- if a "boundary" ever moves or changes, we re-segment.
  * OBJECT PERMANENCE: identity is founded at first sight and carried by OVERLAP, so it survives
    RECOLOUR and RESHAPE (matched by position, not paint). It persists through non-observation
    (occlusion) but DIES on evidence -- when its cells are >=50% occupied by other live objects now.
  * NOTHING SILENT: the tracker records why each id was born, kept, or retired (`events`).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, FrozenSet, Tuple, Dict
import numpy as np
from scipy import ndimage


class DownsampleError(ValueError):
    pass


def check_no_downsampling(before_shape: Tuple[int, int], after_shape: Tuple[int, int]) -> None:
    """HARD BOUND: any op that reduces the grid's cell count is forbidden. Raise, never silently reduce."""
    if after_shape[0] < before_shape[0] or after_shape[1] < before_shape[1]:
        raise DownsampleError("downsampling banned: %s -> %s (a symbolic glyph is exact, never averaged)"
                              % (before_shape, after_shape))


@dataclass
class Object:
    cells: FrozenSet[Tuple[int, int]]     # exact (row, col) membership at full resolution
    colours: FrozenSet[int]               # the symbols it wears (a body can wear several)
    oid: Optional[int] = None             # persistent identity (assigned by the tracker)
    belief: bool = True                   # segmentation is a REVISABLE belief, not a fact

    @property
    def size(self) -> int:
        return len(self.cells)

    @property
    def centroid(self) -> Tuple[float, float]:
        rs = [c[0] for c in self.cells]; cs = [c[1] for c in self.cells]
        return (sum(rs) / len(rs), sum(cs) / len(cs))


def segment(grid: np.ndarray, background: Optional[int] = None, connectivity: int = 1) -> List[Object]:
    """Carve the grid into near-decomposable objects: connected same-symbol components (full-res).
    background defaults to the most common symbol (the board). Returns objects as REVISABLE beliefs."""
    g = np.asarray(grid)
    if g.ndim != 2:
        raise ValueError("grid must be 2-D at full resolution")
    if background is None:
        background = int(np.bincount(g.ravel()).argmax())
    structure = ndimage.generate_binary_structure(2, connectivity)
    objs: List[Object] = []
    for colour in np.unique(g):
        if int(colour) == background:
            continue
        lab, n = ndimage.label(g == colour, structure=structure)
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            cells = frozenset((int(y), int(x)) for y, x in zip(ys, xs))
            objs.append(Object(cells=cells, colours=frozenset({int(colour)})))
    return objs


class ObjectTracker:
    """Founds and carries object identity across frames by cell-overlap (MAP SS9.2, SS9.6 loop closure)."""

    def __init__(self, *, birth_min_overlap: float = 0.30, death_occupancy: float = 0.50):
        self.birth_min_overlap = birth_min_overlap   # min IoU to be judged 'the same object' as a prior track
        self.death_occupancy = death_occupancy        # a track dies when >= this fraction of its cells is others' now
        self._next = 0
        self.tracks: Dict[int, Object] = {}           # oid -> latest Object
        self.events: List[str] = []                    # nothing silent: born/kept/retired narration

    @staticmethod
    def _iou(a: FrozenSet, b: FrozenSet) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def update(self, observed: List[Object]) -> List[Object]:
        """Match observed objects to existing tracks by overlap; found new ids; retire dead ones."""
        prior = dict(self.tracks)
        assigned: Dict[int, Object] = {}
        used_oids = set()
        # 1) greedily match each observed object to the best-overlapping unused prior track
        for obj in sorted(observed, key=lambda o: -o.size):
            best_oid, best_iou = None, 0.0
            for oid, tr in prior.items():
                if oid in used_oids:
                    continue
                j = self._iou(obj.cells, tr.cells)
                if j > best_iou:
                    best_oid, best_iou = oid, j
            if best_oid is not None and best_iou >= self.birth_min_overlap:
                obj.oid = best_oid; used_oids.add(best_oid)          # SAME id -> survives recolour/reshape (overlap, not colour)
                assigned[best_oid] = obj
                self.events.append("KEEP  id=%d (iou=%.2f) -- carried through change" % (best_oid, best_iou))
            else:
                obj.oid = self._next; self._next += 1                 # a genuinely new object -> found a new identity
                assigned[obj.oid] = obj
                self.events.append("BORN  id=%d size=%d" % (obj.oid, obj.size))
        # 2) unmatched prior tracks: DIE only on evidence (cells taken over by others now); else survive (occlusion)
        live_cells = set().union(*[o.cells for o in observed]) if observed else set()
        for oid, tr in prior.items():
            if oid in used_oids:
                continue
            occupied = len(tr.cells & live_cells) / max(1, len(tr.cells))
            if occupied >= self.death_occupancy:
                self.events.append("RETIRE  id=%d -- %.0f%% of its cells taken by others -> dead" % (oid, 100 * occupied))
            else:
                assigned[oid] = tr                                    # persist through non-observation (occlusion)
                self.events.append("OCCLUDED  id=%d -- unseen but not overwritten -> kept" % oid)
        self.tracks = assigned
        return [o for o in assigned.values() if o.oid in {ob.oid for ob in observed}] or list(assigned.values())
