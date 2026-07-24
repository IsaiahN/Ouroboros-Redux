"""referent.py -- Brick 2 of the solution-reasoning scaffold (see claude/DESIGN_solution_reasoning_scaffold.md).

The solution authors' FIRST move is to find the REFERENCE that specifies the goal: a bordered panel that shows the
target configuration, a side LEGEND that keys colours to meaning, or matched ENDPOINT markers that name what must be
connected. Only after locating that referent do they assign roles and hypothesise the win relation. The agent has no
such organ yet -- it treats every coloured region alike. This reads candidate referents FRAME-NATIVELY: purely from
structure (rectangular frame rings, thin edge bands of distinct tokens, matched small component pairs) -- no game-id,
no embodied nouns, no per-game answer. It only NAMES where the reference plausibly is; the agent still has to discover
downstream (Brick 3) what relation that reference implies and test it against the environment's own signal.

Precision-first: on a plain board with no structure it returns nothing. A false referent would mislead Brick 3, so
each detector is gated to fire only on an unmistakable structural signature.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class Referent:
    """A candidate reference region the agent found in a frame, described structurally (no game meaning attached).
    kind: 'panel' (a bordered sub-grid), 'legend' (a thin edge strip of >=3 distinct tokens), or 'endpoints' (a
    matched pair of small same-colour markers). bbox is (r0, c0, r1, c1) inclusive. colour is the defining frame/marker
    colour where one exists (the border colour for a panel, the marker colour for endpoints, None for a legend strip).
    detail carries a compact content descriptor for Brick 3 to reason over."""
    kind: str
    bbox: Tuple[int, int, int, int]
    colour: Optional[int]
    detail: Dict[str, Any] = field(default_factory=dict)


def _bg(g: np.ndarray, bg: Optional[int]) -> int:
    if bg is not None:
        return int(bg)
    vals, cnts = np.unique(g, return_counts=True)
    return int(vals[int(np.argmax(cnts))])


def _components(mask: np.ndarray) -> List[List[Tuple[int, int]]]:
    """4-connected components of a boolean mask (no scipy dependency)."""
    H, W = mask.shape
    seen = np.zeros((H, W), dtype=bool)
    comps: List[List[Tuple[int, int]]] = []
    for i in range(H):
        for j in range(W):
            if mask[i, j] and not seen[i, j]:
                q = deque([(i, j)]); seen[i, j] = True; cells = []
                while q:
                    r, c = q.popleft(); cells.append((r, c))
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and mask[nr, nc] and not seen[nr, nc]:
                            seen[nr, nc] = True; q.append((nr, nc))
                comps.append(cells)
    return comps


def _bbox(cells: List[Tuple[int, int]]) -> Tuple[int, int, int, int]:
    rs = [r for r, _ in cells]; cs = [c for _, c in cells]
    return min(rs), min(cs), max(rs), max(cs)


def _find_panels(g: np.ndarray, bg: int, min_area: int = 20) -> List[Referent]:
    """A reference PANEL: a dense, rectangular, internally-structured region of non-background cells, set apart from the
    background sea (the block the authors read the target configuration from). A CONNECTED non-bg block whose bounding
    box is mostly filled and holds >=2 distinct colours qualifies. If that block's perimeter is dominated by a single
    colour it is a bordered RING and the enclosed INTERIOR is reported; otherwise the whole structured block is. This
    is the frame-native shape real reference panels take: thick or multi-colour frames whose colours recur elsewhere
    (so a global-bbox ring test misses them), but which are locally a solid, separated, structured rectangle."""
    H, W = g.shape
    out: List[Referent] = []
    for comp in _components(g != bg):
        if len(comp) < 8:                                     # a panel is a block, not a handful of cells
            continue
        r0, c0, r1, c1 = _bbox(comp)
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if h < 3 or w < 3:                                    # not a line/strip
            continue
        area = h * w
        if area < min_area or area >= 0.9 * H * W:            # too small to be a panel; the whole board is not one
            continue
        sub = g[r0:r1 + 1, c0:c1 + 1]
        fill = float((sub != bg).mean())
        if fill < 0.5:                                        # a solid separated block, not a sparse scatter
            continue
        distinct = sorted(int(v) for v in np.unique(sub) if int(v) != bg)
        if len(distinct) < 2:                                # a single-colour blob carries no internal structure
            continue
        ring = np.zeros((h, w), dtype=bool)
        ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = True
        perim = sub[ring]
        pvals, pcnts = np.unique(perim, return_counts=True)
        pc = int(pvals[int(np.argmax(pcnts))]); pfrac = float(pcnts.max() / perim.size)
        if pfrac >= 0.8 and pc != bg:                         # a uniform border -> report the enclosed interior
            interior = sub[1:-1, 1:-1]
            icols = sorted(int(v) for v in np.unique(interior) if int(v) not in (bg, pc))
            if interior.size and bool((interior != bg).any()) and icols:
                out.append(Referent("panel", (r0 + 1, c0 + 1, r1 - 1, c1 - 1), pc,
                                     {"via": "ring", "interior_colours": icols,
                                      "fill": round(float((interior != bg).mean()), 3),
                                      "border_frac": round(pfrac, 3), "area": (h - 2) * (w - 2)}))
                continue
        out.append(Referent("panel", (r0, c0, r1, c1), None,
                            {"via": "block", "colours": distinct, "fill": round(fill, 3), "area": area}))
    return out


def _distinct_nonbg(a: np.ndarray, bg: int) -> List[int]:
    return sorted(int(v) for v in np.unique(a) if int(v) != bg)


def _ordered_tokens(band: np.ndarray, horizontal: bool, bg: int) -> List[int]:
    """Read a legend band's tokens in READING ORDER (left-to-right for a horizontal strip, top-to-bottom for a vertical
    one), run-length collapsed: consecutive cells of the same colour are ONE token, a background gap ends a token, so
    [r r . b b] -> [r, b] and [r r . r r] -> [r, r]. This is the ORDER structure (family B) that a distinct-token SET
    throws away. Frame-native; names no game."""
    from collections import Counter
    band = np.asarray(band)
    L = band.shape[1] if horizontal else band.shape[0]
    seq: List[int] = []
    prev = None
    for i in range(L):
        line = band[:, i] if horizontal else band[i, :]
        nz = [int(v) for v in np.asarray(line).ravel().tolist() if int(v) != bg]
        col = Counter(nz).most_common(1)[0][0] if nz else None
        if col is not None and col != prev:
            seq.append(col)
        prev = col
    return seq


def _find_legends(g: np.ndarray, bg: int) -> List[Referent]:
    """A thin edge LEGEND strip: a band of width <=3 along one edge holding >=3 distinct tokens, separated from the
    play area by a mostly-bg gap line. The key that names what the colours mean -- now with the tokens in READING ORDER
    (detail['sequence']) so ORDER games (family B) can compare sequences, not just sets."""
    H, W = g.shape
    out: List[Referent] = []
    cands = []
    for width in (1, 2, 3):
        if width < H:
            cands.append(("top", (0, 0, width - 1, W - 1), (width, slice(None))))
            cands.append(("bottom", (H - width, 0, H - 1, W - 1), (H - 1 - width, slice(None))))
        if width < W:
            cands.append(("left", (0, 0, H - 1, width - 1), (slice(None), width)))
            cands.append(("right", (0, W - width, H - 1, W - 1), (slice(None), W - 1 - width)))
    for _edge, (r0, c0, r1, c1), sep in cands:
        band = g[r0:r1 + 1, c0:c1 + 1]
        tokens = _distinct_nonbg(band, bg)
        if len(tokens) < 3:                                    # a legend keys at least a few tokens
            continue
        sep_line = g[sep]
        if float((np.asarray(sep_line) == bg).mean()) < 0.6:   # must be set APART from the interior by a bg gap
            continue
        seq = _ordered_tokens(band, horizontal=_edge in ("top", "bottom"), bg=bg)
        out.append(Referent("legend", (r0, c0, r1, c1), None,
                            {"tokens": tokens, "n_tokens": len(tokens), "sequence": seq}))
    # merge only the width-1/2/3 duplicates of the SAME strip (they OVERLAP in position); keep two DISTINCT-edge legends
    # even when their sequences later coincide (a reference vs a workspace row that has been brought to match it).
    def _ov(a, b):
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
    kept: List[Referent] = []
    for r in sorted(out, key=lambda x: _area(x.bbox)):        # smallest (most compact) strip first
        if not any(_ov(r.bbox, k.bbox) for k in kept):
            kept.append(r)
    return kept


def _area(b: Tuple[int, int, int, int]) -> int:
    r0, c0, r1, c1 = b
    return (r1 - r0 + 1) * (c1 - c0 + 1)


def _find_endpoints(g: np.ndarray, bg: int, cell_cap: int = 12) -> List[Referent]:
    """Matched ENDPOINT markers: a colour that appears as EXACTLY two small, similarly-sized components -- a pair that
    names two things to be joined (connect/route) or matched. Frame-native: it does not say WHAT joins them."""
    H, W = g.shape
    out: List[Referent] = []
    for c in [int(v) for v in np.unique(g) if int(v) != bg]:
        comps = _components(g == c)
        if len(comps) != 2:
            continue
        s0, s1 = len(comps[0]), len(comps[1])
        if max(s0, s1) > cell_cap:                             # endpoints are small markers, not big regions
            continue
        if min(s0, s1) / max(s0, s1) < 0.5:                    # a matched pair is similar in size
            continue
        b0, b1 = _bbox(comps[0]), _bbox(comps[1])
        cen = [(round(np.mean([r for r, _ in cm]), 1), round(np.mean([cc for _, cc in cm]), 1)) for cm in comps]
        union = (min(b0[0], b1[0]), min(b0[1], b1[1]), max(b0[2], b1[2]), max(b0[3], b1[3]))
        out.append(Referent("endpoints", union, c, {"centroids": cen, "sizes": [s0, s1]}))
    return out


def _centroid(cells: List[Tuple[int, int]]) -> Tuple[float, float]:
    return float(np.mean([r for r, _ in cells])), float(np.mean([c for _, c in cells]))


def _cluster_two(cents: List[Tuple[float, float]]):
    """Deterministically split centroids into TWO groups: seed with the farthest-apart pair, then 3 Lloyd iterations.
    Returns (labels, mean0, mean1) or None if it cannot form two non-empty groups. No randomness (resume-safe)."""
    import math
    n = len(cents)
    if n < 2:
        return None
    si, sj, best = 0, 1, -1.0
    for i in range(n):
        for j in range(i + 1, n):
            d = math.hypot(cents[i][0] - cents[j][0], cents[i][1] - cents[j][1])
            if d > best:
                best, si, sj = d, i, j
    m0, m1 = cents[si], cents[sj]
    labels = [0] * n
    for _ in range(3):
        for k, p in enumerate(cents):
            d0 = math.hypot(p[0] - m0[0], p[1] - m0[1]); d1 = math.hypot(p[0] - m1[0], p[1] - m1[1])
            labels[k] = 0 if d0 <= d1 else 1
        g0 = [cents[k] for k in range(n) if labels[k] == 0]
        g1 = [cents[k] for k in range(n) if labels[k] == 1]
        if not g0 or not g1:
            return None
        m0 = (float(np.mean([p[0] for p in g0])), float(np.mean([p[1] for p in g0])))
        m1 = (float(np.mean([p[0] for p in g1])), float(np.mean([p[1] for p in g1])))
    return labels, m0, m1


def _find_node_pairs(g: np.ndarray, bg: int, seen_colours: set, min_frag: int = 2,
                     max_share: float = 0.15) -> List[Referent]:
    """A colour whose (noise-filtered) components cluster into TWO well-SEPARATED groups -- the general 'two nodes to
    connect' the exact-2-small-pair detector misses when a node is fragmented or the two nodes differ in size. Emitted
    as an ENDPOINTS referent (so CONNECT consumes it). Precision-first: only when the two clusters are far apart
    relative to their own spread, the colour is not a large structural fill, and it isn't already an exact pair."""
    import math
    H, W = g.shape
    area = H * W
    out: List[Referent] = []
    for c in [int(v) for v in np.unique(g) if int(v) != bg and int(v) not in seen_colours]:
        comps = [cm for cm in _components(g == c) if len(cm) >= min_frag]   # drop single-cell noise
        if len(comps) < 2:
            continue
        total = sum(len(cm) for cm in comps)
        if total > max_share * area:                          # a big structural colour (maze/wall) is not a node set
            continue
        cents = [_centroid(cm) for cm in comps]
        sizes = [len(cm) for cm in comps]
        res = _cluster_two(cents)
        if res is None:
            continue
        labels, m0, m1 = res
        inter = math.hypot(m0[0] - m1[0], m0[1] - m1[1])
        intra = 0.0
        for k, p in enumerate(cents):
            m = m0 if labels[k] == 0 else m1
            intra = max(intra, math.hypot(p[0] - m[0], p[1] - m[1]))
        if inter < max(3.0 * max(intra, 1.0), 0.15 * min(H, W)):   # clearly separated AND a real fraction apart
            continue
        s0 = sum(sizes[k] for k in range(len(comps)) if labels[k] == 0)
        s1 = sum(sizes[k] for k in range(len(comps)) if labels[k] == 1)
        allcells = [cell for cm in comps for cell in cm]
        union = _bbox(allcells)
        cen = [(round(m0[0], 1), round(m0[1], 1)), (round(m1[0], 1), round(m1[1], 1))]
        out.append(Referent("endpoints", union, c, {"centroids": cen, "sizes": [s0, s1], "clustered": True}))
    return out


def _panel_sequence(g: np.ndarray, bbox: Tuple[int, int, int, int], bg: int) -> Optional[List[int]]:
    """If a detected panel's region is an ELONGATED linear strip (a bordered token ROW/COLUMN -- the sequence bars that
    sit in the INTERIOR of family-B games like tr87/sb26, which the edge-only legend scan misses), read its tokens in
    reading order along the long axis. >=3 distinct tokens required. None if the region is not elongated (a square
    symbol display or a big panel stays a panel, not a sequence). General: names no game; aspect-ratio + token-count
    gated, no pixel threshold."""
    r0, c0, r1, c1 = bbox
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if min(h, w) < 1 or max(h, w) < 3 * min(h, w):            # not clearly elongated -> not a linear sequence
        return None
    seq = _ordered_tokens(g[r0:r1 + 1, c0:c1 + 1], horizontal=(w >= h), bg=bg)
    return seq if len(seq) >= 3 else None


def _find_panel_sequences(g: np.ndarray, panels: List[Referent], bg: int) -> List[Referent]:
    """Re-read each elongated panel as an ordered token SEQUENCE (a legend), so framed INTERIOR token strips -- not just
    thin EDGE bands -- feed the ORDER relation. Reuses the detected panels + `_ordered_tokens`; precision from
    `_panel_sequence` (elongated + >=3 tokens)."""
    out: List[Referent] = []
    for p in panels:
        seq = _panel_sequence(g, p.bbox, bg)
        if seq is not None:
            out.append(Referent("legend", p.bbox, None,
                                {"tokens": sorted(set(seq)), "n_tokens": len(set(seq)), "sequence": seq}))
    return out


def find_referents(frame, bg: Optional[int] = None) -> List[Referent]:
    """Every frame-native referent in a single frame: bordered panels, legends (thin EDGE bands AND elongated INTERIOR
    framed token strips, each with an ordered `sequence`), matched endpoint pairs (exact-small and clustered node pairs).
    Empty on a structureless board (precision-first). Order: panels, legends, endpoints."""
    g = np.asarray(frame)
    if g.ndim != 2 or g.size == 0:
        return []
    b = _bg(g, bg)
    panels = _find_panels(g, b)
    eps = _find_endpoints(g, b)
    node_pairs = _find_node_pairs(g, b, seen_colours={r.colour for r in eps})
    return panels + _find_legends(g, b) + _find_panel_sequences(g, panels, b) + eps + node_pairs
