"""nexus.sensorium.forward -- the efference-copy forward model (the keystone of the sensorium).

The corpus's efference copy: the motor system sends a COPY of the command to the sensory system
BEFORE the movement, predicts its own consequence, and only the UNPREDICTED residual ascends.
That is a literal spec for the organ the agent lacked. Before committing action a on grid G, we
render a prediction G_hat = predict(G, a); after the step we observe G'; the per-cell residual
G' (-) G_hat is the gradient the proposer already consumes.

From this one residual fall out three things the agent could not perceive:
  1. SELF-MASK / ownership : the cells that move PREDICTABLY with my action are ME; the rest is
     the world. Minted by watching what moves when I act -- never hardcoded, so it survives a
     game where "self" looks like nothing we would have guessed (the rubber-hand isolation).
  2. PREDICTIVE NOCICEPTION : if the model has learned a displacement, danger about the cell I
     would ENTER is a before-state fact (fed by the ground's confirmed fatals in the circuit).
  3. ACTIVE-INFERENCE empowerment : prefer the action whose outcome the model is least able to
     predict -- the move most likely to make a silent ground speak.

No pretraining, no parameters: the self and its per-action displacement are discovered online by
the standard "which object translated" test between consecutive grids. When no controllable self
exists (a static-until-click game), self stays empty and every change is attributed to the world
-- which is the honest reading, not a failure.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from typing import Dict, Optional, Set, Tuple
import numpy as np

Coord = Tuple[int, int]


def as_grid2d(grid) -> np.ndarray:
    """Coerce whatever the session hands us into a 2D int array. ARC frames arrive as [H][W] or as
    [frames][H][W]; take the last frame in the 3D case (the current one). Never raises: an
    un-coercible grid becomes an empty array, and the sensorium simply perceives nothing."""
    try:
        a = np.asarray(grid)
        if a.ndim == 3:
            a = a[-1]
        if a.ndim != 2:
            return np.zeros((0, 0), dtype=int)
        return a.astype(int)
    except Exception:
        return np.zeros((0, 0), dtype=int)


def background_colour(a: np.ndarray) -> int:
    """The most common colour -- the presumed background/free space. A presumption the ground can
    overturn, not a hardcoded palette fact: it is recomputed every frame from the board itself."""
    if a.size == 0:
        return 0
    vals, counts = np.unique(a, return_counts=True)
    return int(vals[int(np.argmax(counts))])


class ForwardModel:
    """Efference-copy predictor. Discovers the controllable self and its per-action displacement by
    watching consecutive frames, then predicts the next grid by translating the self."""

    def __init__(self, max_shift: int = 3):
        self.max_shift = max_shift
        self.disp: Dict[str, Counter] = defaultdict(Counter)   # action -> Counter[(dr,dc)]
        self.self_cells: Set[Coord] = set()                    # last confidently-attributed self cells
        self.self_colour: Optional[int] = None
        self._n_obs = 0

    # ---- learning (online, parameter-free) --------------------------------------------------------
    def observe(self, before, action: str, after) -> Tuple[int, int]:
        """Update the self-model from one transition. Returns the (dr,dc) attributed to the action
        this step (0,0 if no coherent translation was found)."""
        a = as_grid2d(before); b = as_grid2d(after)
        if a.size == 0 or a.shape != b.shape:
            return (0, 0)
        self._n_obs += 1
        bg = background_colour(a)
        dr, dc, cells, colour = self._best_translation(a, b, bg)
        if cells:
            self.disp[action][(dr, dc)] += 1
            # the self is the object that MOVED under my command (arrival cells in `after`)
            self.self_cells = {(r + dr, c + dc) for (r, c) in cells}
            self.self_colour = colour
        return (dr, dc)

    def _best_translation(self, a: np.ndarray, b: np.ndarray, bg: int):
        """Find the (dr,dc) that best explains the change as a rigid translation of one object:
        cells non-bg in `a` that were VACATED (bg in `b`) and REAPPEAR shifted by (dr,dc) in `b`.
        Returns (dr, dc, source_cells, colour) or (0,0,set(),None) if nothing coherent moved."""
        h, w = a.shape
        moved = [(r, c) for r in range(h) for c in range(w)
                 if a[r, c] != bg and b[r, c] == bg]          # cells that emptied out
        if not moved:
            return 0, 0, set(), None
        best = (0, 0, set(), None); best_score = 0
        for dr in range(-self.max_shift, self.max_shift + 1):
            for dc in range(-self.max_shift, self.max_shift + 1):
                if dr == 0 and dc == 0:
                    continue
                by_colour: Dict[int, set] = defaultdict(set)
                for (r, c) in moved:
                    rr, cc = r + dr, c + dc
                    # a genuine rigid move VACATES the source AND FILLS a cell that was background.
                    # Requiring the destination to have been background rejects the aliasing where a
                    # retracting bar looks like a 1-cell shift (its 'destination' was already the colour).
                    if 0 <= rr < h and 0 <= cc < w and b[rr, cc] == a[r, c] and a[rr, cc] == bg:
                        by_colour[int(a[r, c])].add((r, c))
                if not by_colour:
                    continue
                colour, cells = max(by_colour.items(), key=lambda kv: len(kv[1]))
                score = len(cells)
                if score > best_score:                        # the largest coherently-translated object
                    best_score = score; best = (dr, dc, set(cells), colour)
        return best

    # ---- perception & prediction ------------------------------------------------------------------
    def expected_disp(self, action: str) -> Coord:
        c = self.disp.get(action)
        return c.most_common(1)[0][0] if c else (0, 0)

    def self_mask(self) -> Set[Coord]:
        return set(self.self_cells)

    def has_self(self) -> bool:
        return bool(self.self_cells) and self.self_colour is not None

    def self_centroid(self) -> Optional[Coord]:
        if not self.self_cells:
            return None
        rs = [r for r, _ in self.self_cells]; cs = [c for _, c in self.self_cells]
        return (round(sum(rs) / len(rs)), round(sum(cs) / len(cs)))

    def predict(self, grid, action: str) -> np.ndarray:
        """Render the efference copy: translate the current self by the action's learned displacement.
        With no self learned yet, the prediction is 'nothing changes' -- so the whole observed change
        becomes residual (correctly attributed to the world)."""
        g = as_grid2d(grid).copy()
        if g.size == 0 or not self.self_cells or self.self_colour is None:
            return g
        bg = background_colour(g)
        dr, dc = self.expected_disp(action)
        if (dr, dc) == (0, 0):
            return g
        h, w = g.shape
        present = [(r, c) for (r, c) in self.self_cells if 0 <= r < h and 0 <= c < w and g[r, c] == self.self_colour]
        for (r, c) in present:
            g[r, c] = bg
        for (r, c) in present:
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w:
                g[rr, cc] = self.self_colour
        return g

    def residual(self, grid, action: str, after) -> Set[Coord]:
        """The UNPREDICTED change -- cells where reality diverged from the efference copy. This is the
        surprise the proposer prices; an empty residual means the model fully explained the step."""
        pred = self.predict(grid, action)
        act = as_grid2d(after)
        if pred.shape != act.shape or pred.size == 0:
            return set()
        return {(int(r), int(c)) for r, c in zip(*np.where(pred != act))}

    def surprise(self, grid, action: str, after) -> int:
        return len(self.residual(grid, action, after))
