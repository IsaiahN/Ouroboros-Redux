"""ar25 -- SYMMETRY-AS-PLACEMENT detector (observe-only candidate).

Measured: pixel-fold symmetry is NOT ar25's objective (win frame 58% mismatched pieces-only; axis unstable).
Grammar form is ALL(p in PIECE: BE_AT(p, mirror_slot(p))): whole-PIECE placement into mirror slots about an
explicit axis marker. This reads pieces as objects and pairs each with a reflected sibling. It is a CANDIDATE
kept observe-only (default flag off in the abductor) until validated live; it does not replace _symmetry_axis_
targets or _mirror_completion_targets -- those stay intact.
"""
import numpy as np


def _bg(g): return int(np.bincount(np.asarray(g).ravel()).argmax())


def _axis_marker(g, bg, frac=0.5):
    """Explicit axis = the colour forming the longest near-full-length straight line (the magenta cross in
    ar25). Returns (colour, orient, position) or None. Not fold-derived -- read off an actual line object."""
    g = np.asarray(g); H, W = g.shape
    best = None
    for c in np.unique(g):
        if int(c) == bg:
            continue
        m = (g == c)
        vcol = [int(m[:, x].sum()) for x in range(W)]
        vrow = [int(m[y, :].sum()) for y in range(H)]
        if max(vcol) >= frac * H:
            cand = (int(c), "v", int(np.argmax(vcol)), max(vcol))
            if best is None or cand[3] > best[3]: best = cand
        if max(vrow) >= frac * W:
            cand = (int(c), "h", int(np.argmax(vrow)), max(vrow))
            if best is None or cand[3] > best[3]: best = cand
    return best[:3] if best else None


def symmetry_place_targets(g, bg=None):
    """Pieces (non-bg, non-axis objects) that lack a mirror-partner across the axis marker. Emits
    ('mirrorplace', axis_orient, axis_pos, (r,c)) for each unpaired piece cell-cluster centroid. Observe-only."""
    import object_seg
    g = np.asarray(g); bg = _bg(g) if bg is None else bg
    mk = _axis_marker(g, bg)
    if mk is None:
        return []
    acol, orient, pos = mk
    objs = [o for o in object_seg.segment_objects(g, bg=bg) if o["size"] >= 3]
    objs = [o for o in objs if not all(int(g[r, c]) == acol for (r, c) in o["cells"])]  # drop the axis line
    if len(objs) < 2:
        return []
    # SYMMETRIC-CONTEXT guard: a symmetry game has piece-mass on BOTH sides of the axis. Wall/structure lines
    # in non-symmetry games (sb26/sk48/sp80) fail this, so they stop mis-firing.
    if orient == "v":
        left = sum(1 for o in objs if o["centroid"][1] < pos); right = sum(1 for o in objs if o["centroid"][1] > pos)
    else:
        left = sum(1 for o in objs if o["centroid"][0] < pos); right = sum(1 for o in objs if o["centroid"][0] > pos)
    if left == 0 or right == 0:
        return []
    out = []
    for o in objs:
        cy, cx = o["centroid"]
        # reflected centroid across the axis
        if orient == "v":
            ry, rx = cy, 2 * pos - cx
        else:
            ry, rx = 2 * pos - cy, cx
        # is there a piece near the reflected position?
        paired = any(abs(oo["centroid"][0] - ry) < 2 and abs(oo["centroid"][1] - rx) < 2
                     for oo in objs if oo is not o)
        if not paired and 0 <= ry < g.shape[0] and 0 <= rx < g.shape[1]:
            out.append(("mirrorplace", orient, pos, (int(round(ry)), int(round(rx)))))
    return out[:6]
