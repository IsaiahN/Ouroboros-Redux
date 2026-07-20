# object_seg.py — OBJECT-level perception: group cells into coherent multi-color connected components
# (a sprite is an object regardless of its internal colors), with identity tracked across frames. This is
# the substrate beneath discovery/control/objective-search: those failed because they worked on single
# COLORS while real objects (e.g. a cursor that is colors 0+4) are multi-color.
import numpy as np
from collections import Counter

try:
    from scipy import ndimage
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


def _label(mask):
    if _HAVE_SCIPY:
        return ndimage.label(mask, structure=np.ones((3, 3)))   # 8-connectivity
    # fallback BFS labeling
    lbl = np.zeros(mask.shape, int); nxt = 0
    H, W = mask.shape
    for i in range(H):
        for j in range(W):
            if mask[i, j] and lbl[i, j] == 0:
                nxt += 1; stack = [(i, j)]; lbl[i, j] = nxt
                while stack:
                    r, c = stack.pop()
                    for dr in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < H and 0 <= nc < W and mask[nr, nc] and lbl[nr, nc] == 0:
                                lbl[nr, nc] = nxt; stack.append((nr, nc))
    return lbl, nxt


def segment_objects(frame, bg=None, ignore_colors=None):
    """Connected components of the non-background mask. Each object may span MULTIPLE colors (a sprite).
    ignore_colors: large static structure colors to treat as background too."""
    frame = np.asarray(frame)
    if bg is None:
        bg = int(np.bincount(frame.ravel()).argmax())
    mask = frame != bg
    if ignore_colors:
        for c in ignore_colors:
            mask &= (frame != c)
    lbl, n = _label(mask)
    objs = []
    for i in range(1, n + 1):
        cells = np.argwhere(lbl == i)
        if len(cells) == 0:
            continue
        colors = Counter(int(frame[r, c]) for r, c in cells)
        r0, c0 = cells.min(0); r1, c1 = cells.max(0)
        objs.append(dict(size=len(cells), centroid=(float(cells[:, 0].mean()), float(cells[:, 1].mean())),
                         bbox=(int(r0), int(r1), int(c0), int(c1)),
                         cells=frozenset((int(r), int(c)) for r, c in cells),   # shared substrate: raw cells
                         colors=dict(colors), color_sig=frozenset(colors)))
    return objs


def structure_colors(frames, bg, area_frac=0.15):
    """Colors that are LARGE and STATIC across frames = board/structure (treat as background for objects)."""
    frames = [np.asarray(f) for f in frames]
    H, W = frames[0].shape; tot = H * W
    out = []
    counts0 = Counter(frames[0].ravel().tolist())
    for c, n in counts0.items():
        c = int(c)
        if c == bg or n < area_frac * tot:
            continue
        # static if its cell-set barely changes across frames
        masks = [(f == c) for f in frames]
        change = np.mean([np.mean(masks[i] != masks[0]) for i in range(1, len(masks))]) if len(masks) > 1 else 0
        if change < 0.02:
            out.append(c)
    return out


def match_objects(prev_objs, cur_objs):
    """Track identity across frames by nearest centroid + compatible color-signature/size."""
    matches = {}
    used = set()
    for pi, p in enumerate(prev_objs):
        best, bd = None, 1e9
        for ci, c in enumerate(cur_objs):
            if ci in used:
                continue
            if not (p["color_sig"] & c["color_sig"]):
                continue
            d = abs(p["centroid"][0] - c["centroid"][0]) + abs(p["centroid"][1] - c["centroid"][1])
            if d < bd and abs(p["size"] - c["size"]) <= max(4, 0.5 * p["size"]):
                bd, best = d, ci
        if best is not None:
            matches[pi] = best; used.add(best)
    return matches
