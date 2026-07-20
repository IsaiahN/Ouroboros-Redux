"""
goal_cues.py — read the objective RELATION from perceptual GOAL CUES, in the objective_grammar
vocabulary, INDEPENDENT of the control modality (Gap B).

The §11.245 finding: control-modality (translate/paint/click) does NOT determine the win-relation.
A translate-marker can serve a reach (BE_AT) or an assemble (SAME) objective.  So the relation must
be abduced from what the FRAME shows about the goal, not from how the agent moves.

Each detector is a GENERAL perceptual pattern -> a grammar relation (no per-game rule):
  hole/stencil  (enclosed bg inside a shape)            -> COVER   (fill the holes)
  distinct-exit (one small component, isolated)         -> BE_AT   (reach it)
  collectibles  (several small same-size components)    -> NONE.EXIST / TOUCH (collect them)
  template-pair (>=2 similar-shaped regions, differing) -> SAME    (make them match)
The reader returns ranked cues; the agency modality then only constrains FEASIBILITY downstream.
"""
import numpy as np
from collections import Counter
from scipy.ndimage import label


def _bg(grid):
    return int(np.bincount(grid.ravel()).argmax())




def detect_stencil_holes(grid):
    """Small components of a colour H that sit ENCLOSED inside a single other non-bg colour F
    (a stencil whose fill-cells are not the background colour) -> COVER. Generalises detect_holes,
    whose enclosed regions must be the background; here the holes can be any uniform colour
    (e.g. ar25's colour-0 cells inside colour-5 shapes)."""
    bg = _bg(grid)
    best = None
    for H in np.unique(grid):
        if H == bg:
            continue
        lab, n = label(grid == H)
        holes = 0
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            if len(ys) > 2:                                   # a fill-cell is tiny
                continue
            r0, r1 = max(ys.min() - 1, 0), min(ys.max() + 1, grid.shape[0] - 1)
            c0, c1 = max(xs.min() - 1, 0), min(xs.max() + 1, grid.shape[1] - 1)
            win = grid[r0:r1 + 1, c0:c1 + 1]
            comp = (lab[r0:r1 + 1, c0:c1 + 1] == i)
            ring = win[~comp]
            ring = ring[(ring != bg)]                          # frame must be a real (non-bg) colour
            if ring.size and (ring != H).all():
                vals, cnts = np.unique(ring, return_counts=True)
                if cnts.max() / ring.size > 0.7:               # dominated by one frame colour F
                    holes += 1
        if holes >= 3 and (best is None or holes > best["strength"]):
            best = dict(cue="stencil", relation="COVER", hole_color=int(H),
                        strength=holes, confidence=min(1.0, holes / 6.0))
    return best


def detect_holes(grid):
    """SMALL enclosed bg regions (stencil holes inside shapes) -> COVER. Large enclosed bg
    (maze corridors, container interiors) is NOT a fill-stencil and is excluded."""
    bg = _bg(grid)
    lab, n = label(grid == bg)
    border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    small_holes = 0
    for i in range(1, n + 1):
        if i in border:
            continue
        sz = int((lab == i).sum())
        if sz <= 4:                       # a stencil hole is a few cells; a corridor/interior is large
            small_holes += 1
    if small_holes == 0:
        return None
    return dict(cue="hole", relation="COVER", strength=small_holes,
                confidence=min(1.0, small_holes / 6.0))


def detect_distinct_exit(grid, agent_color=None):
    """A non-bg colour with exactly ONE small component -> BE_AT (a unique destination/exit)."""
    bg = _bg(grid)
    cands = []
    for c in np.unique(grid):
        if c == bg or c == agent_color:
            continue
        lab, n = label(grid == c)
        sz = int((grid == c).sum())
        if n == 1 and sz <= 30:
            cands.append((int(c), sz))
    if not cands:
        return None
    cands.sort(key=lambda t: t[1])
    return dict(cue="exit", relation="BE_AT", target_color=cands[0][0],
                strength=len(cands), confidence=0.5 + 0.1 * len(cands))


def detect_collectibles(grid, agent_color=None):
    """A colour with SEVERAL small same-size components -> collect (NONE.EXIST / TOUCH)."""
    bg = _bg(grid)
    best = None
    for c in np.unique(grid):
        if c == bg or c == agent_color:
            continue
        lab, n = label(grid == c)
        if n < 3:
            continue
        sizes = [int((lab == i).sum()) for i in range(1, n + 1)]
        if max(sizes) <= 12 and (max(sizes) - min(sizes)) <= 2:        # many small ~equal blobs
            cue = dict(cue="collectible", relation="NONE.EXIST", target_color=int(c),
                       strength=n, confidence=min(1.0, n / 6.0))
            if best is None or cue["strength"] > best["strength"]:
                best = cue
    return best


def detect_template_pair(grid, agent_color=None):
    """>=2 components with SIMILAR bbox shape but different colour/content -> SAME (match them).
    Also: a single colour forming a GRID of >=3 equal-shaped boxes -> SAME (make boxes match).
    The controllable is NOT excluded here: it is often the very shape being matched (move 9 onto 8),
    so excluding it would delete the cue (the g50t binding hole)."""
    bg = _bg(grid)
    comps = []
    for c in np.unique(grid):
        if c == bg:
            continue
        lab, n = label(grid == c)
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            comps.append((int(c), ys.max() - ys.min() + 1, xs.max() - xs.min() + 1, len(ys)))
    if len(comps) < 2:
        return None
    # grid-of-boxes: one colour with >=3 EQUAL, HOLLOW components (a real template box has a frame
    # with a DIFFERENT interior; a maze's corridor/wall blocks are SOLID and must be excluded).
    bycol = Counter(c for c, _, _, _ in comps)
    for c, k in bycol.items():
        if k >= 3:
            shapes = [(h, w) for cc, h, w, _ in comps if cc == c]
            if len(set(shapes)) <= 2:
                return dict(cue="template-grid", relation="SAME", frame_color=c,
                            strength=k, confidence=min(1.0, k / 4.0))
    # match-pair: two components (different colours) with near-equal bbox -> reproduce one as the other
    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            ci, hi, wi, _ = comps[i]; cj, hj, wj, _ = comps[j]
            if ci != cj and abs(hi - hj) <= 1 and abs(wi - wj) <= 1 and hi >= 3 and wi >= 3:
                return dict(cue="template-pair", relation="SAME", colors=(ci, cj),
                            strength=hi * wi, confidence=0.6)
    return None


def read_goal_cues(grid, agent_color=None):
    """Run all detectors; return cues ranked by confidence. The objective relation is the top cue's."""
    cues = [d for d in (
        detect_holes(grid),
        detect_stencil_holes(grid),
        detect_template_pair(grid, agent_color),
        detect_distinct_exit(grid, agent_color),
        detect_collectibles(grid, agent_color),
    ) if d is not None]
    cues.sort(key=lambda d: d["confidence"], reverse=True)
    return cues
