"""P5 -- MAP / correspondence decode (tr87 rosetta). The grammar already carries MAP_DECODE
(ALL(x: SAME(meaning(x), MAP(x)))) built on the LIKE prime; what is missing is the executable pair: (1) LEARN a
correspondence M: src_symbol -> tgt_symbol from an in-scene legend, and (2) a discrepancy that drives a target
region to its decoded form using M.

This is the one build with IN-EPISODE LEARNING, which the rest of the stack does not do. It is therefore kept
OBSERVE-ONLY: learn_map is logged and its disc is available, but it is NOT placed in the scored config head. A
half-learned M produces a confident-but-wrong non-degenerate disc -- the worst failure mode -- so it must earn
the scored path by provably converging first. Validated here standalone on a synthetic legend.
"""
import numpy as np


def learn_map(g, bg, max_gap=2):
    """Learn M: src_colour -> tgt_colour from a LEGEND: pairs of near-adjacent distinct-colour cells on the same
    row (src on the left, tgt within `max_gap` to the right), a stable src->tgt association repeated in the scene.
    Returns dict M. This is the correspondence-LEARNING primitive; it reads the legend, it does not act."""
    g = np.asarray(g)
    H, W = g.shape
    votes = {}
    for r in range(H):
        nz = [c for c in range(W) if g[r, c] != bg]
        for i in range(len(nz)):
            for j in range(i + 1, len(nz)):
                c0, c1 = nz[i], nz[j]
                if c1 - c0 > max_gap:
                    break
                s, t = int(g[r, c0]), int(g[r, c1])
                if s != t:
                    votes.setdefault(s, {}).setdefault(t, 0)
                    votes[s][t] += 1
    # majority target per source; require a clean winner (a legend is unambiguous)
    M = {}
    for s, tv in votes.items():
        t_best, n_best = max(tv.items(), key=lambda kv: kv[1])
        if n_best >= 1 and list(tv.values()).count(n_best) == 1:
            M[s] = t_best
    return M


def map_discrepancy(target_cells, M, grid0):
    """Decode disc: each target cell whose ORIGINAL colour s (from grid0) has a learned mapping should become M[s].
    measure(g) = count of target cells not yet at their decoded value; active(g) = those cells. Uses grid0 so the
    original source is known after cells have been recoloured."""
    grid0 = np.asarray(grid0)
    tgt = [((r, c), int(grid0[r, c])) for (r, c) in target_cells if int(grid0[r, c]) in M]

    def measure(g):
        g = np.asarray(g)
        return float(sum(1 for (r, c), s in tgt if int(g[r, c]) != M[s]))

    def active(g):
        g = np.asarray(g)
        return [(r, c) for (r, c), s in tgt if int(g[r, c]) != M[s]]

    return measure, active


if __name__ == "__main__":
    BG = 0
    # Legend (rows 1-3): src @col2 -> tgt @col4  =>  1->7, 2->8, 3->9
    g0 = np.zeros((16, 16), dtype=int)
    for r, (s, t) in zip((1, 2, 3), ((1, 7), (2, 8), (3, 9))):
        g0[r, 2] = s; g0[r, 4] = t
    # Target region (rows 8-9, cols 6-9): src symbols to decode
    target = [(8, 6), (8, 10), (9, 6), (9, 10)]   # spaced > max_gap so they aren't spurious legend pairs
    src_at = {(8, 6): 1, (8, 10): 2, (9, 6): 3, (9, 10): 1}
    for cell, s in src_at.items():
        g0[cell] = s

    M = learn_map(g0, BG)
    print("learned M:", M, "(expected {1:7, 2:8, 3:9})")
    measure, active = map_discrepancy(target, M, g0)
    print("disc measure(start):", measure(g0), "| active:", active(g0))

    # apply the decode (as a solver would: recolour each target cell to M[src]) and confirm the disc closes
    g = g0.copy()
    for (r, c) in list(active(g)):
        s = int(g0[r, c]); g[r, c] = M[s]
    print("disc measure(after decode):", measure(g), "-> solved:", measure(g) == 0)


def find_legend_panel(g, bg, board_frac=0.25):
    """PERCEPTION BRIDGE (P5, tr87): locate a LEGEND -- equal-size symbol objects arranged in exactly TWO columns
    (src | tgt) over >=2 rows. Returns dict(found, pairs=[(src_obj, tgt_obj)...], shape_map). Keys the map by the
    src sprite's translation+colour signature so decode is shape->shape, not colour->colour (real rosettas map
    sprites). Tested on the real tr87 board. The typing 'left=src,right=tgt' is inferred from layout, not certain."""
    import numpy as np, object_seg as OS
    g = np.asarray(g); H, W = g.shape
    objs = [o for o in OS.segment_objects(g, bg=bg) if o['size'] < board_frac * H * W]
    if len(objs) < 4:
        return dict(found=False, pairs=[], shape_map={})
    # equal-size symbol set?
    from collections import Counter
    sz = Counter(o['size'] for o in objs)
    common_sz, n = sz.most_common(1)[0]
    syms = [o for o in objs if o['size'] == common_sz]
    if n < 4 or n % 2 != 0:
        return dict(found=False, pairs=[], shape_map={})
    # two columns by centroid-col (k=2 split around the median)
    cols = sorted(o['centroid'][1] for o in syms)
    split = (cols[len(cols)//2 - 1] + cols[len(cols)//2]) / 2
    left = sorted([o for o in syms if o['centroid'][1] < split], key=lambda o: o['centroid'][0])
    right = sorted([o for o in syms if o['centroid'][1] >= split], key=lambda o: o['centroid'][0])
    if len(left) != len(right) or not left:
        return dict(found=False, pairs=[], shape_map={})

    def sig(o):
        r0, r1, c0, c1 = o['bbox']
        return frozenset(((int(r)-r0, int(c)-c0), int(g[r, c])) for (r, c) in o['cells'])

    pairs, shape_map = [], {}
    for l, r in zip(left, right):
        pairs.append((l['bbox'], r['bbox']))
        shape_map[sig(l)] = sig(r)
    # a legend is meaningful only if src != tgt in at least one pair (a real transformation)
    meaningful = any(shape_map[s] != s for s in shape_map)
    return dict(found=meaningful and len(pairs) >= 2, n_pairs=len(pairs), pairs=pairs,
                distinct_maps=len({(s, t) for s, t in shape_map.items()}), meaningful=meaningful)


# ===================================================================================================
# FRAME-ONLY MECHANIC DISCOVERY (this fix): the eval is frame-only with novel game ids, so a "mapping
# game" must be DISCOVERED from frame features -- a consistent, repeated symbol correspondence shown in
# the scene -- never from game identity. Generalises past tr87. Replaces the game-specific stub.
# ===================================================================================================
def _norm_shape(o, g):
    r0, r1, c0, c1 = o["bbox"]
    return frozenset((int(r) - r0, int(c) - c0) for (r, c) in o["cells"])

def discover_correspondence(g, bg=None, board_frac=0.25, min_sym=5):
    """Frame-only rosetta discovery. Each legend ENTRY is one multi-colour object holding a src-colour
    sub-shape and a tgt-colour sub-shape side by side (tr87 encodes it this way). Decompose objects into
    colour sub-shapes, pick the two symbol-colour ROLES that co-occur most across objects, and learn
    src_subshape->tgt_subshape. found=False unless a CONSISTENT function of >=2 distinct src shapes (src!=tgt)
    emerges -- so games without a repeated correspondence (r11l, re86) stay silent. Game-agnostic."""
    import numpy as np, object_seg as OS
    from collections import Counter
    g = np.asarray(g); H, W = g.shape
    bg = int(np.bincount(g.ravel()).argmax()) if bg is None else bg
    objs = [o for o in OS.segment_objects(g, bg=bg) if min_sym <= o["size"] < board_frac * H * W]
    if len(objs) < 3:
        return dict(found=False, M={}, n_pairs=0)
    # decompose each object into per-colour sub-shapes (ignore tiny connector colours < min_sym cells)
    decomp = []
    role_hist = Counter()
    for o in objs:
        r0, r1, c0, c1 = o["bbox"]
        by = {}
        for (r, c) in o["cells"]:
            by.setdefault(int(g[r, c]), []).append((r - r0, c - c0))
        subs = {col: frozenset(cells) for col, cells in by.items() if len(cells) >= min_sym}
        if len(subs) >= 2:
            decomp.append((o, subs, {col: np.mean([cc[1] for cc in cells]) for col, cells in by.items() if len(cells) >= min_sym}))
            for col in subs: role_hist[col] += 1
    if len(decomp) < 2 or len(role_hist) < 2:
        return dict(found=False, M={}, n_pairs=0)
    (ca, _), (cb, _) = role_hist.most_common(2)     # the two symbol-colour roles
    # src = the role that sits LEFT within the object (smaller mean column), tgt = right; consistent across entries
    votes = {}
    for o, subs, meancol in decomp:
        if ca in subs and cb in subs:
            src_c, tgt_c = (ca, cb) if meancol[ca] <= meancol[cb] else (cb, ca)
            votes.setdefault(subs[src_c], Counter())[subs[tgt_c]] += 1
    M = {}
    for ss, tc in votes.items():
        ts, n = tc.most_common(1)[0]
        if list(tc.values()).count(n) == 1 and ts != ss:
            M[ss] = ts
    # A rosetta is a CODE: require >=3 CONSISTENT distinct correspondences (a 2-tone coloring/tile game has
    # at most a couple). Game-agnostic threshold; observe-only downstream so reward disposes any residual FP.
    return dict(found=len(M) >= 3, M=M, n_pairs=len(M), src_color=int(min(ca, cb)), tgt_color=int(max(ca, cb)))


def map_decode_disc(g, bg, corr):
    """Real (frame-only) decode measure: target-region = src-coloured symbols NOT in the legend pairing whose
    shape has a learned mapping; measure(g) = count still showing src-shape (undecoded). Pursuit is live, but
    the MEASURE is frame-computable, so the disc is non-degenerate and observe-only until pursuit is wired."""
    import numpy as np, object_seg as OS
    M = corr.get("M", {})
    if not M:
        return (lambda g: 1.0), (lambda g: [])
    src_c = corr.get("src_color")
    def _srcobjs(gg):
        gg = np.asarray(gg); bgg = int(np.bincount(gg.ravel()).argmax())
        return [o for o in OS.segment_objects(gg, bg=bgg)
                if o["size"] >= 2 and int(np.bincount([int(gg[r,c]) for (r,c) in o["cells"]]).argmax()) == src_c
                and _norm_shape(o, gg) in M]
    def measure(gg):
        return float(len(_srcobjs(gg)))
    def active(gg):
        return [tuple(int(x) for x in o["centroid"]) for o in _srcobjs(gg)]
    return measure, active
