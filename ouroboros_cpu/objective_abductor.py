"""
objective_abductor.py — the GRAMMAR composed over the AGENCY-ANCHOR.

Bridges two existing DSL pieces, storing no answer:
  - discriminative_agency.agency_report(adapter) -> {modality, locus, marker_color, shifts}
  - objective_grammar.PRIMES                      -> the universal relation/quantifier basis

The bridge is a single principled prior: the control MODALITY narrows the grammar RELATION.
  translate -> BE_AT / TOUCH      (a mover reaches/contacts a target)
  paint     -> BECOME / SAME      (painting makes a region BECOME a colour / match a template)
  rearrange -> SAME / BECOME      (permuting matches a target configuration)
  erase     -> NONE.EXIST         (consuming removes all targets)
  regional  -> BECOME / SAME
This is composition, not a library: no per-game rule; the modality is measured, the relation is
primed (not fixed), and which target/predicate actually wins is still confirmed by interaction.
"""
import numpy as np
from collections import Counter
from scipy.ndimage import label
from discriminative_agency import agency_report
from goal_cues import read_goal_cues

MODALITY_RELATION_PRIOR = {
    "translate": ["BE_AT", "TOUCH"],
    "paint":     ["BECOME", "SAME", "COVER"],
    "rearrange": ["SAME", "BECOME"],
    "erase":     ["NONE.EXIST"],
    "regional":  ["BECOME", "SAME", "COVER"],
    "counter":   ["BE_AT", "BECOME"],
    "inert":     ["BE_AT", "BECOME", "SAME"],
    "rotate":    ["BECOME", "SAME", "TOUCH"],           # select+spin a piece: reorient (BECOME), match (SAME), link (TOUCH)
}


# Wire the LIVE grammar into the runtime abductor (single source of truth). This lets an abduced
# hypothesis explain itself in the basis -- words + grammar + primes -- which is what makes the
# composer's reasoning legible. Imported softly so it can NEVER break the scored path.
try:
    import objective_grammar as _G
except Exception:
    _G = None

def explain_relation(rel):
    """Explain an abduced relation in the basis (words + grammar + primes). {} if grammar unavailable."""
    return _G.explain(rel) if _G is not None else {}

# Drift surfaced as DATA (never an assert on the scored path): relations this module emits that are
# not yet registered in the grammar. Should be empty; if not, the grammar needs the predicate added.
UNREGISTERED_RELATIONS = (
    ({r for rs in MODALITY_RELATION_PRIOR.values() for r in rs} - _G.relation_vocabulary())
    if _G is not None else set()
)

# ---------------------------------------------------------------------------------------------------
# STAGE-0 VISUAL PRIOR (this session): the visual scene-read narrows/reorders the abductor's relation
# search BEFORE goal-abduction (visual-first). Soft import + flag so it can NEVER break the scored path;
# verified non-regressive on lp85 (differential edited-vs-reverted, both win @296).
# ---------------------------------------------------------------------------------------------------
USE_VISUAL_PRIOR = True
# map a projection predicate -> the base relation the abductor ranks in (collapse molecules to relations)
_PROJ2REL = {"COVER": "COVER", "SAME": "SAME", "NONE.EXIST": "NONE.EXIST", "SAME/FIT": "SAME",
             "BECOME/COVER": "COVER", "BE_AT@locus": "BE_AT", "REACH": "BE_AT",
             "MATCH_GOAL": "SAME", "REPLAY": "SAME"}

def _visual_relation_prior(g):
    """Run the Stage-0 scene-read and return base relations (score-ordered) the visual layer BOUND.
    Wrapped so any failure leaves the abductor's behaviour exactly as before."""
    try:
        import visual_projection as _VP
        sr = _VP.read_scene(g)
        rels = []
        for p in sr.projections:            # bound concepts, already score-ordered + competition-pruned
            r = _PROJ2REL.get(p.predicate)
            if r and r not in rels:
                rels.append(r)
        return rels
    except Exception:
        return []


# ---------------------------------------------------------------------------------------------------
# AFFORDANCE PRIOR (this session): the recon/online-affordance map (action -> dynamics it causes) feeds
# the scored path. Observed dynamics constrain the objective: e.g. seeing GRAVITY/PUSH/SLIDE makes a
# placement objective (BE_AT) likely; APPEAR/DISAPPEAR makes spawn/consume (BECOME / NONE.EXIST) likely.
# Cache is EMPTY by default -> no change -> lp85 safe; the agent fills it passively from its buffer.
# ---------------------------------------------------------------------------------------------------
USE_AFFORDANCE_PRIOR = True

# ---------------------------------------------------------------------------------------------------
# NEW-PIECE OBSERVE-ONLY FLAGS (this integration): P1-P4 stay wired above; these add symmetry-placement
# (ar25) and MAP-decode (tr87) as CANDIDATE config heads. Default OFF -> generated only when flipped, so the
# scored path is byte-identical until each is validated LIVE. Reward disposes once ON. Never outrank the
# validated heads: appended in the TAIL of _ranked.
# ---------------------------------------------------------------------------------------------------
USE_SYMMETRY_PLACE = True    # ACTIVE by default: ar25 whole-piece mirror placement (reward-arbitrated; unvalidated)
USE_MAP_DECODE     = True    # ACTIVE by default: frame-only rosetta discovery (reward-arbitrated; disc measure unrefined)

_AFFORDANCE = {"elicited": []}
_DYN2REL = {"GRAVITY": ["BE_AT"], "FALL": ["BE_AT"], "CONVEYOR": ["BE_AT"], "SLIDE": ["BE_AT"],
            "PUSH": ["BE_AT"], "APPEAR": ["BECOME"], "DISAPPEAR": ["NONE.EXIST"], "COLLECT": ["NONE.EXIST"],
            "GROW": ["BECOME"], "SHRINK": ["NONE.EXIST"], "JOIN": ["SAME"], "BREAK": ["BECOME"]}

def set_affordance(elicited_molecules):
    """Called by the agent with the dynamics molecules its actions have been observed to cause."""
    _AFFORDANCE["elicited"] = list(elicited_molecules or [])

def clear_affordance():
    _AFFORDANCE["elicited"] = []

def _affordance_relations():
    rels = []
    for m in _AFFORDANCE.get("elicited", []):
        for r in _DYN2REL.get(m, []):
            if r not in rels:
                rels.append(r)
    return rels


def _is_hud(grid, color):
    """HUD bars/counters are confined to an edge row/column (the agency analysis types these
    'counter'/ambient; here we also catch full-edge bars geometrically). Strengthened (UI_DETECTION,
    adopted from old-agent forensic): also catch a thick edge BAND -- cells in the outer <=3 rows/cols
    that span most of that edge's length (a move-counter / progress bar), which the 1-2 cell strip test
    missed. The span condition keeps small near-edge OBJECTS (real targets) from being excluded."""
    H, W = grid.shape
    ys, xs = np.where(grid == color)
    if len(ys) == 0:
        return False
    r0, r1, c0, c1 = ys.min(), ys.max(), xs.min(), xs.max()
    confined_row = (r0 >= H - 2) or (r1 <= 1)        # all cells in a top/bottom edge row
    confined_col = (c0 >= W - 2) or (c1 <= 1)        # all cells in a left/right edge col
    band_row = ((r0 >= H - 3) or (r1 <= 2)) and (c1 - c0 + 1) >= 0.5 * W   # thick top/bottom bar
    band_col = ((c0 >= W - 3) or (c1 <= 2)) and (r1 - r0 + 1) >= 0.5 * H   # thick left/right bar
    return confined_row or confined_col or band_row or band_col


def perceive_targets(grid, exclude_color=None, exclude_ambient=()):
    """Candidate TARGET objects: connected components per non-bg colour, excluding the controllable
    AND ambient/HUD colours (the agency anchor already separates these from the game).
    NOTE (11.306): a per-colour path is kept ON PURPOSE. Suppressing per-colour blobs that belong to a
    multi-colour object was tried and REGRESSED both a dense board (cd82: 8-connectivity over-merges adjacent
    distinct-colour targets) and a compact sprite (lp85: a real winning fragment got deleted). The per-colour
    and multi-colour-OBJECT views are COMPLEMENTARY, not redundant; both feed abduce over the SAME object_seg
    substrate (the object-hypothesis branch) and reward arbitrates. So we do NOT merge them here."""
    bg = int(np.bincount(grid.ravel()).argmax())
    targets = []
    for c in np.unique(grid):
        if c == bg or c == exclude_color or int(c) in exclude_ambient:
            continue
        if _is_hud(grid, c):
            continue
        m = (grid == c)
        lab, n = label(m)
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            targets.append(dict(color=int(c), size=int(len(ys)),
                                centroid=(float(ys.mean()), float(xs.mean())),
                                bbox=(int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max()))))
    return targets


def _distinct_cell_targets(g, ctrl, bg, k=6):
    """PERCEPTION source (§11.259): in-frame goal markers = centroids of the smallest/rarest distinct
    components (the game often SHOWS its goal as a small isolated marker). Produces ('cell', r, c)
    BE_AT targets; reward disposes. General -- no game identity."""
    comps = []
    for c in np.unique(g):
        if c == bg or c == ctrl:
            continue
        lab, n = label(g == c)
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            comps.append((len(ys), int(round(ys.mean())), int(round(xs.mean()))))
    comps.sort()                                       # smallest first = most marker-like
    return [("cell", r, c) for _, r, c in comps[:k]]


def _mirror_completion_targets(g, bg):
    """CONFIG-COMPLETION for paint/located games: propose FILLING the mirror cells of each salient colour
    about an axis -- 'v' (left<->right), 'h' (top<->bottom), 'd' (diagonal y=x, square grids only). The
    placed colour may differ from the reference (place-to-target), so the measure tracks 'filled', not
    'same colour'. Fires on a real asymmetry; reward + predicate-satisfied-no-reward dispose. Within-grid only."""
    out = []
    H, W = g.shape
    cols = [int(c) for c in np.unique(g) if int(c) != bg]
    cols = sorted(cols, key=lambda c: -int((g == c).sum()))[:3]
    for col in cols:
        a = (g == col)
        if a.sum() < 2:
            continue
        cand = [("v", a[:, ::-1]), ("h", a[::-1, :])]
        if H == W:
            cand.append(("d", a.T))
        for orient, mir in cand:
            if int(((~a) & mir).sum()) > 0:         # some mirror cells of `col` are not yet filled by `col`
                out.append(("gridmirror", orient, col))
    return out


def _symmetry_axis_targets(g, ctrl, bg):
    """PERCEPTION source (§11.259): fold axes where the STATIC structure (non-bg, non-ctrl) is ALREADY
    symmetric -- there the objective is to complete the MOVABLE colour's symmetry. Fires ONLY when the
    static asymmetry is zero, so it is correctly silent on the non-symmetric residue (§11.258).
    Produces ('axis', orient, p2, ctrl) SAME targets; reward disposes."""
    ys, xs = np.where(g != bg)
    if len(ys) == 0:
        return []
    r0, r1, c0, c1 = ys.min(), ys.max(), xs.min(), xs.max()
    sub = g[r0:r1 + 1, c0:c1 + 1]
    static = (sub != bg) & (sub != ctrl)
    out = []
    for orient in ("v", "h"):
        M = static if orient == "v" else static.T
        w = M.shape[1]; best = (1e18, None)
        for p2 in range(max(1, w - 1 - 6), min(2 * w - 2, w - 1 + 6) + 1):
            s = 0
            for c in range(w):
                cc = p2 - c
                if 0 <= cc < w:
                    s += int((M[:, c] != M[:, cc]).sum())
            if s < best[0]:
                best = (s, p2)
        if best[1] is not None and best[0] == 0 and static.sum() > 0:   # static genuinely symmetric
            out.append(("axis", orient, best[1], ctrl))
    return out


def _row_match_targets(g, bg):
    """PERCEPTION source (P1): a 1D CONFIG-MATCH -- two PARALLEL thin bands (rows or columns) of EQUAL length
    but DIFFERING content -> SAME, keyed to the band coordinates so the discrepancy is a cell-wise string
    mismatch (lp85 belt, ft09 tile row). ui_planner then searches command sequences (rotations/swaps) that drive
    the mismatch to zero. FALSE-POSITIVE GUARDS: (a) skip edge-margin bands, (b) require MULTI-colour bands -- a
    HUD progress bar / level counter is monochrome (and a monochrome slider is P2's ACCUMULATE, not a rowmatch),
    (c) skip _is_hud colours, (d) skip IDENTICAL bands (a degenerate SAME, measure 0). Produces
    ('rowmatch', orient, ar, ac, br, bc, w) SAME targets; reward disposes which band is the movable one."""
    H, W = g.shape
    hud = {c for c in np.unique(g) if int(c) != bg and _is_hud(g, int(c))}

    def _bands(vertical):
        out = []
        n = W if vertical else H
        for i in range(n):
            line = g[:, i] if vertical else g[i]
            nz = np.where(line != bg)[0]
            if len(nz) < 3:
                continue
            a, b = int(nz.min()), int(nz.max())
            if (b - a + 1) != len(nz):                      # must be a CONTIGUOUS band
                continue
            if (vertical and (i <= 1 or i >= W - 2)) or (not vertical and (i <= 1 or i >= H - 2)):
                continue                                     # edge-margin HUD guard
            content = tuple(int(x) for x in line[a:b + 1])
            distinct = set(content)
            if len(distinct) < 2 or distinct <= hud:         # monochrome / all-HUD -> not a config row
                continue
            # ISOLATION guard: a config row is a 1-cell-THICK line (bg on both perpendicular sides). A 2D
            # enclosure column (stencil frame, box wall) has non-bg neighbours -> reject, so a frame is not
            # read as a belt (the COVER-stencil false positive).
            if vertical:
                left = g[a:b + 1, i - 1] if i - 1 >= 0 else np.full(b - a + 1, bg)
                right = g[a:b + 1, i + 1] if i + 1 < W else np.full(b - a + 1, bg)
            else:
                left = g[i - 1, a:b + 1] if i - 1 >= 0 else np.full(b - a + 1, bg)
                right = g[i + 1, a:b + 1] if i + 1 < H else np.full(b - a + 1, bg)
            if int((left != bg).sum()) or int((right != bg).sum()):
                continue
            out.append(("v" if vertical else "h", (a if vertical else i), (i if vertical else a),
                        b - a + 1, content))
        return out

    bands = _bands(False) + _bands(True)
    out = []
    for i in range(len(bands)):
        for j in range(i + 1, len(bands)):
            oi, ri, ci, wi, ki = bands[i]; oj, rj, cj, wj, kj = bands[j]
            if oi != oj or wi != wj or ki == kj:             # same orient+length, DIFFERING content
                continue
            if sorted(ki) != sorted(kj):                     # a rotation/permutation match: same multiset
                continue                                     # (a belt is a permutation of its target)
            out.append(("rowmatch", oi, ri, ci, rj, cj, wi))
    return out[:4]


def _slider_targets(g, bg):
    """PERCEPTION source (P2): a SLIDER / ACCUMULATE quantity. A MONOCHROME contiguous fill run (the bar's filled
    portion) plus a lone distinct TARGET marker aligned above/below it -> drive the fill to the marked level.
    Emits ('COUNT', fill_colour, target_n, '==') so the existing COUNT hinge disc measures |count - target_n| and
    ui_planner drives +/- commands to close it. Guards: fill must be MONOCHROME (a multi-colour band is P1's
    rowmatch, not a slider), the marker a lone distinct cell aligned to a column at/after the fill start, and the
    target must differ from the current fill count (else a degenerate COUNT). Returns ('COUNT',...) spec tuples."""
    H, W = g.shape
    out = []
    for r in range(H):
        row = g[r]
        nz = np.where(row != bg)[0]
        if len(nz) < 4:
            continue
        colors = {int(x) for x in row[nz] if int(x) != bg}
        if len(colors) != 1:                                  # a slider fill is a single colour
            continue
        fill = colors.pop()
        fc = np.where(row == fill)[0]
        if (int(fc.max()) - int(fc.min()) + 1) != len(fc):    # contiguous fill
            continue
        fstart, fcount = int(fc.min()), len(fc)
        for dr in (-2, -1, 1, 2, -3, 3):                      # find an aligned lone target marker
            rr = r + dr
            if not (0 <= rr < H):
                continue
            mk = np.where(g[rr] != bg)[0]
            if len(mk) != 1:
                continue
            mc = int(mk[0])
            if int(g[rr, mc]) == fill or mc < fstart:
                continue
            target_n = mc - fstart + 1
            if target_n != fcount and 1 <= target_n <= (W - fstart):
                out.append(("COUNT", fill, target_n, "=="))
            break
    return out[:2]


def _order_targets(g, bg):
    """PERCEPTION source (P3): a SEQUENCE / ORDER objective -- >=3 same-colour, single-column bars of DISTINCT
    heights at a shared baseline in evenly-spaced slots -> arrange into DESCENDING order by the intrinsic key
    (height). Emits ('order', slot_cols, rbot, colour) so the disc measures INVERSIONS vs the sorted order (a
    smooth gradient) and ui_planner searches swap commands to close it. Guards: >=3 bars (2 is a match-pair, P1);
    DISTINCT heights (a tie has no unambiguous order); single-column vertical runs of ONE colour at a shared
    baseline and even spacing (rejects 2D shapes and collectible blobs, which are erase/NONE.EXIST, not ordered);
    skip an already-sorted set (degenerate)."""
    H, W = g.shape
    bars = {}
    for c in range(W):
        col = g[:, c]
        nz = np.where(col != bg)[0]
        if len(nz) == 0:
            continue
        colors = {int(x) for x in col[nz]}
        if len(colors) != 1:
            continue
        color = colors.pop()
        r0, r1 = int(nz.min()), int(nz.max())
        if (r1 - r0 + 1) != len(nz):                        # contiguous single-column bar
            continue
        bars.setdefault((color, r1), []).append((c, r1 - r0 + 1))
    out = []
    for (color, rbot), lst in bars.items():
        if len(lst) < 3:                                    # >=3 bars for an order (2 = match-pair)
            continue
        lst = sorted(lst, key=lambda t: t[0])
        cols = [c for c, _h in lst]; hts = [_h for _c, _h in lst]
        if len({cols[i + 1] - cols[i] for i in range(len(cols) - 1)}) != 1:   # evenly spaced slots
            continue
        if len(set(hts)) != len(hts):                       # DISTINCT heights -> unambiguous key
            continue
        if hts == sorted(hts, reverse=True):                # already sorted -> degenerate
            continue
        out.append(("order", tuple(cols), rbot, color))
    return out[:2]


def _shape_completion_targets(g, bg):
    """PERCEPTION source (P4): NON-RECTANGULAR shape match. Segment objects and group by translation-invariant
    SHAPE (norm_shape) + bbox dims -- so L/T/sprite shapes are matched by signature, not bbox rectangularity
    (where detect_template_pair fails). Within a group of >=2 same-shape objects, if one's cell CONTENTS (colour
    pattern) differs from the majority, it is a corrupted copy: emit ('match', target_origin, ref_origin, hh, ww)
    so the PROVEN cell-wise match disc drives the odd object to equal a correct sibling (fixes exactly the wrong
    cells). Guards: >=2 same-shape siblings; NON-rectangular shape (a full rectangle is grid-box/rowmatch, not
    shape-match); contents genuinely differ (else degenerate); size >=3 (excludes fragments)."""
    try:
        import object_seg
        objs = object_seg.segment_objects(g, bg=bg)
    except Exception:
        return []
    from collections import Counter
    groups = {}
    for o in objs:
        if o["size"] < 3:
            continue
        r0, r1, c0, c1 = o["bbox"]
        dims = (r1 - r0 + 1, c1 - c0 + 1)
        ns = frozenset((r - r0, c - c0) for (r, c) in o["cells"])
        if len(ns) == dims[0] * dims[1]:                          # full rectangle -> not shape-match
            continue
        content = frozenset(((r - r0, c - c0), int(g[r, c])) for (r, c) in o["cells"])
        groups.setdefault((ns, dims), []).append(((r0, c0), content))
    out = []
    for (ns, dims), members in groups.items():
        if len(members) < 2:
            continue
        cc = Counter(content for _o, content in members)
        maj_content, maj_n = cc.most_common(1)[0]
        if maj_n == len(members):                                 # all identical -> degenerate
            continue
        ref = next(origin for origin, content in members if content == maj_content)
        for origin, content in members:
            if content != maj_content:
                out.append(("match", origin, ref, dims[0], dims[1]))   # A=target (fixed), B=reference
    return out[:2]


def _piece_tip(o, g, tip_color):
    """(b) TIP location of a piece: centroid of the connector-colour cells within its bbox -- the extremity that
    must overlap another piece's tip. Falls back to the piece centroid if the connector colour is absent.
    Scoring TOUCH to the TIP (not the piece centroid) is why min_disc-0-at-centroid never coincided with a win."""
    import numpy as _np
    g = _np.asarray(g); r0, r1, c0, c1 = o["bbox"]
    sub = g[r0:r1 + 1, c0:c1 + 1]
    tp = _np.argwhere(sub == tip_color)
    if len(tp):
        return (int(round(tp[:, 0].mean())) + r0, int(round(tp[:, 1].mean())) + c0)
    return (int(round(o["centroid"][0])), int(round(o["centroid"][1])))


def _enclosed_interiors(g, bg):
    """CONTAIN_FIT perception: find HOLLOW-FRAME interiors -- background cells ENCLOSED by non-bg walls (not
    connected to the grid border). Each such region is a 'slot' a fitting piece must be driven INSIDE. Returns
    [(centroid_r, centroid_c, size), ...] largest first. This is the INSIDE prime made perceptual."""
    import numpy as _np
    from collections import deque as _dq
    g = _np.asarray(g); H, W = g.shape
    reached = _np.zeros((H, W), bool); q = _dq()
    for r in range(H):
        for c in (0, W - 1):
            if g[r, c] == bg and not reached[r, c]:
                reached[r, c] = True; q.append((r, c))
    for c in range(W):
        for r in (0, H - 1):
            if g[r, c] == bg and not reached[r, c]:
                reached[r, c] = True; q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and g[rr, cc] == bg and not reached[rr, cc]:
                reached[rr, cc] = True; q.append((rr, cc))
    enclosed = (g == bg) & (~reached)
    if not enclosed.any():
        return []
    # connected-component the enclosed cells into distinct slots
    lab = _np.zeros((H, W), int); nxt = 0; out = []
    for r in range(H):
        for c in range(W):
            if enclosed[r, c] and lab[r, c] == 0:
                nxt += 1; comp = []; q = _dq([(r, c)]); lab[r, c] = nxt
                while q:
                    y, x = q.popleft(); comp.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and enclosed[yy, xx] and lab[yy, xx] == 0:
                            lab[yy, xx] = nxt; q.append((yy, xx))
                ys = [p[0] for p in comp]; xs = [p[1] for p in comp]
                out.append((int(round(sum(ys) / len(ys))), int(round(sum(xs) / len(xs))), len(comp)))
    out.sort(key=lambda t: -t[2])
    return out


def abduce(adapter, max_hyps=6, reset_first=True, prior_report=None):
    """Ranked grammar hypotheses RELATION(CONTROLLABLE, target).  The RELATION now comes from
    PERCEPTUAL GOAL CUES (read_goal_cues), NOT from the control modality (the §11.243 conflation):
    a translate-marker can serve a reach OR an assemble objective, so the modality is demoted to
    selecting the downstream PURSUIT METHOD, while the relation is read off the goal structure.
    Per §11.246 the cues PROPOSE ranked candidates and reward (the validator) DISPOSES.
    reset_first/prior_report (11.301): for a LATER level, reuse the level-1 agency report (the
    controllable is stable across levels) and abduct on the CURRENT frame without a whole-game reset."""
    rpt = prior_report if prior_report is not None else agency_report(adapter)
    modality = rpt.get("modality", "inert")
    g = adapter.reset() if reset_first else adapter._grid(adapter._obs)
    ctrl = rpt.get("marker_color")
    targets = perceive_targets(g, exclude_color=ctrl)
    # MARKER-SELECTION wire: drop colours empirically not goals -- sprite colours (move WITH the avatar) and the
    # no-reward blacklist (reached >=3x with no reward). Game-local, supplied by the live agent via the report.
    # Removing them HERE propagates the exclusion through salience, the salient list, and the reach-head markers.
    _excl = set(rpt.get("exclude_markers") or ())
    if _excl:
        targets = [t for t in targets if t["color"] not in _excl]
    locus = rpt.get("locus") or (0.0, 0.0)
    colcount = Counter(t["color"] for t in targets)

    def salience(t):
        dist = abs(t["centroid"][0] - locus[0]) + abs(t["centroid"][1] - locus[1])
        rarity = 1.0 / colcount[t["color"]]
        return rarity * (1 + dist / 64.0)
    targets.sort(key=salience, reverse=True)

    def _mk(rel, tcol, cue=None, conf=None):
        quant = "SOME" if rel in ("BE_AT", "TOUCH") else "ALL"
        return dict(quantifier=quant, relation=rel, controllable=ctrl, target_color=tcol, cue=cue,
                    confidence=conf,
                    descriptor=f"{quant}(x: {rel}(CONTROLLABLE[{ctrl}], TARGET[{tcol}]))")

    # --- Gap B: relation from perceptual goal cues; bind each over MULTIPLE candidate targets so
    #     reward (not the abductor) disposes the binding (the tu93 9-vs-14 lesson) ---
    cues = read_goal_cues(g, agent_color=ctrl)
    rel_order, cue_target = [], {}
    for cue in cues:
        rel = cue["relation"]
        if rel not in rel_order:
            rel_order.append(rel)
        tc = cue.get("target_color")
        if tc is None:
            tc = cue.get("frame_color")
        if tc is None:
            tc = cue.get("hole_color")
        if tc is None and cue.get("colors"):
            tc = cue["colors"][-1]
        if tc is not None and rel not in cue_target and int(tc) not in _excl:
            cue_target[rel] = int(tc)
    # Modality CONTRIBUTES relation candidates (it does not NAME the relation, §11.245): the goal cues
    # miss objectives they cannot perceive (e.g. erase->NONE.EXIST on cd82), so append the modality
    # prior's relations to the candidate set and let REWARD dispose. Cues rank first; modality fills gaps.
    for rel in MODALITY_RELATION_PRIOR.get(modality, []):
        if rel not in rel_order:
            rel_order.append(rel)
    if not rel_order:                                          # nothing at all -> generic prior
        rel_order = MODALITY_RELATION_PRIOR.get(modality, ["BE_AT", "BECOME", "SAME"])

    # STAGE-0 VISUAL PRIOR: reorder so relations the visual scene-read BOUND come first (visual-first),
    # and ADD any bound relation the cues/modality missed (the visual layer can introduce a missed
    # objective). Nothing is dropped -> every prior hypothesis is still generated; reward still disposes.
    if USE_VISUAL_PRIOR:
        boost = _visual_relation_prior(g)
        if boost:
            rel_order = boost + [r for r in rel_order if r not in boost]

    # AFFORDANCE PRIOR: observed dynamics (from the agent's action buffer) constrain the objective.
    # Applied AFTER the visual prior (observed > inferred). Empty cache -> no change -> lp85 safe.
    if USE_AFFORDANCE_PRIOR:
        aff = _affordance_relations()
        if aff:
            rel_order = aff + [r for r in rel_order if r not in aff]

    salient = []                                               # distinct target colours, salience order
    for t in targets:
        if t["color"] not in salient:
            salient.append(t["color"])

    rel_tlists = {}
    for rel in rel_order:
        tl = ([cue_target[rel]] if rel in cue_target else [])
        tl += [c for c in salient if c not in tl]
        rel_tlists[rel] = tl[:3]

    color_hyps, seen = [], set()
    for k in range(3):                                         # round-robin: relation breadth before target depth
        for rel in rel_order:
            tl = rel_tlists.get(rel, [])
            if k >= len(tl):
                continue
            tcol = tl[k]
            if (rel, tcol) in seen:
                continue
            seen.add((rel, tcol))
            color_hyps.append(_mk(rel, tcol, cue="goal-cue"))

    # NOTE (P0, reverted): a cue-specificity re-sort of color_hyps (NONE.EXIST<COVER<SAME<BE_AT) was built to
    # "fix" the read_goal_cues confidence miscalibration (SAME outranks NONE.EXIST on equal-shape collectibles).
    # MEASURED: unnecessary AND harmful. Without it, the full pipeline (Option-(c) cue-binding exemption + the
    # non-degenerate objective/_compile selection) already commits erase->NONE.EXIST and match->SAME correctly on
    # every constructed shape; WITH it, a real SAME grid (differing boxes) mis-commits NONE.EXIST and erases the
    # tiles it should match. The read_goal_cues confidence ranking is cosmetic; it does not reach the commit.

    # PERCEPTION-source target candidates (§11.259): the COMPOSER binds in-frame targets the colour
    # abduction cannot name -- distinct-cell goals (BE_AT a specific marker) and symmetry axes (SAME
    # under MIRROR). Both feed the SAME reward-arbitrated set; reward disposes.
    bg = int(np.bincount(g.ravel()).argmax())
    perc_hyps = [_mk("BE_AT", cell, cue="perception:cell") for cell in _distinct_cell_targets(g, ctrl, bg)]
    perc_hyps += [_mk("SAME", ax, cue="perception:axis") for ax in _symmetry_axis_targets(g, ctrl, bg)]
    _has_located = bool(getattr(adapter, "pointer_actions", lambda: [])())
    _has_nullary = bool(list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions()))
    if _has_located and not _has_nullary:        # place-to-target-by-clicking: PURE click-to-place family only
        perc_hyps += [_mk("SAME", mc, cue="perception:gridmirror") for mc in _mirror_completion_targets(g, bg)]

    # WANT fix (reach signature, step-two): a resolved controllable + a distinct SMALL static marker + a
    # navigation modality = a maze/reach game; promote ONE BE_AT(ctrl, nearest small marker) to rank #1.
    # GATED: erase/command games (cd82: ctrl is None) cannot trigger it, so the 11.271 cd82 ordering holds.
    reach_head = []
    if ctrl is not None and modality in ("translate", "counter"):
        comp_count = Counter(t["color"] for t in targets)          # components per colour
        cell_count = {}
        for t in targets:
            cell_count[t["color"]] = cell_count.get(t["color"], 0) + t["size"]
        # A goal MARKER is a colour present as FEW components and FEW cells -- a unique exit/goal cell, not a
        # repeated wall texture (which shows as many same-colour components). Propose BE_AT to each distinct
        # marker; REWARD disposes between them (the propose/dispose design). Walls (many components) excluded.
        markers = sorted({t["color"] for t in targets
                          if comp_count[t["color"]] <= 2 and cell_count[t["color"]] <= 20},
                         key=lambda c: (comp_count[c], cell_count[c]))
        for mc in markers[:3]:
            reach_head.append(_mk("BE_AT", mc, cue="reach-signature"))
        if markers:
            dct = _distinct_cell_targets(g, ctrl, bg)
            if dct:
                reach_head.append(_mk("BE_AT", dct[0], cue="reach-signature:cell"))

    # Colour candidates FIRST -- they carry the proven solves (cd82 NONE.EXIST sits DEEPER than any small
    # protected head, so reordering/interleaving drops it: §11.271 measured that regression). Keep colour
    # ordering intact and reach perception by a LARGER max_hyps instead (cheap: descend fast-aborts wrong
    # candidates, and wall-clock is abundant). Object-level target bindings then live in the tail, reached
    # in deployment; reward + the predicate-satisfied-no-reward brake dispose every candidate.
    # --- COMPOSITE objectives (11.284): general operators over the atomic relations, appended to the
    #     TAIL so atoms are tried first. Reward-arbitrated like every other candidate -> they can neither
    #     false-win (reward gates) nor displace an atom win (ordering). Bounded generation keeps the
    #     program space tractable; adaptive budget (not a fixed cap) is what lets a promising one pay out. ---
    def _cmk(spec, cue):
        return dict(relation="COMPOSITE", target_color=None, spec=spec, quantifier="COMPOSE",
                    cue=cue, confidence=None, descriptor=f"COMPOSE[{cue}]:{spec}")
    comp_hyps = []
    sal2 = salient[:3]
    base = rel_order[0] if rel_order else "BE_AT"
    if len(sal2) >= 2:
        a, b = (base, sal2[0]), (base, sal2[1])
        comp_hyps += [_cmk(("AND", a, b), "and"), _cmk(("THEN", a, b), "then")]
        comp_hyps += [_cmk(("AND", (base, sal2[0]), ("NONE.EXIST", sal2[1])), "and-x"),
                      _cmk(("THEN", (base, sal2[0]), ("COVER", sal2[1])), "then-x")]
    for tc in sal2[:2]:                                          # generalised counting beyond ->0
        cur = int((g == tc).sum())
        comp_hyps.append(_cmk(("COUNT", tc, max(1, cur // 2), "<="), "count-le"))
        comp_hyps.append(_cmk(("COUNT", tc, 2, ">="), "count-ge"))
    if sal2:                                                     # FORALL components: reach every one, sequenced
        comp_hyps.append(_cmk(("ALL", "BE_AT", sal2[0]), "forall-reach"))
    # --- OBJECT-level objectives (11.286): recover multi-colour object perception into the SCORED path.
    #     Objects = multi-colour connected components (a sprite regardless of its internal colours). Generate
    #     reach-an-object and match-two-objects; appended to the TAIL, reward-arbitrated, so over-merge on a
    #     dense board (which the colour path already wins) cannot regress anything. ---
    obj_hyps = []
    try:
        from object_seg import segment_objects
        bgc = int(np.bincount(g.ravel()).argmax())
        objs = [o for o in segment_objects(g, bg=bgc) if 3 <= o["size"] <= 250]
        objs.sort(key=lambda o: -o["size"])
        for o in objs[:4]:                                       # REACH an object (sprite centroid, multi-colour)
            cy, cx = int(round(o["centroid"][0])), int(round(o["centroid"][1]))
            obj_hyps.append(dict(relation="BE_AT", target_color=("cell", cy, cx), quantifier="SOME",
                                 cue="object:reach", confidence=None, descriptor=f"REACH-OBJ({cy},{cx})"))
        for i in range(len(objs)):                               # MATCH two objects of identical bbox (replicate/align)
            for j in range(i + 1, len(objs)):
                a, b = objs[i], objs[j]
                ha, wa = a["bbox"][1] - a["bbox"][0] + 1, a["bbox"][3] - a["bbox"][2] + 1
                hb, wb = b["bbox"][1] - b["bbox"][0] + 1, b["bbox"][3] - b["bbox"][2] + 1
                if (ha, wa) == (hb, wb) and ha * wa >= 4:
                    obj_hyps.append(dict(relation="MATCH", quantifier="ALL", cue="object:match", confidence=None,
                                         target_color=("match", (a["bbox"][0], a["bbox"][2]),
                                                       (b["bbox"][0], b["bbox"][2]), ha, wa),
                                         descriptor="MATCH-OBJ"))
        cents = [(int(round(o["centroid"][0])), int(round(o["centroid"][1]))) for o in objs[:4]]
        for i in range(len(cents)):                              # THEN over OBJECT pairs: reach A then B
            for j in range(len(cents)):                          #   (the key-then-goal / room-to-room structure)
                if i == j:
                    continue
                a = ("BE_AT", ("cell",) + cents[i]); b = ("BE_AT", ("cell",) + cents[j])
                obj_hyps.append(_cmk(("THEN", a, b), "obj-then"))
        if len(cents) >= 2:                                      # AND over the two most salient objects
            obj_hyps.append(_cmk(("AND", ("BE_AT", ("cell",) + cents[0]), ("BE_AT", ("cell",) + cents[1])), "obj-and"))
        obj_hyps = obj_hyps[:16]
    except Exception:
        obj_hyps = []
    # P1 CONFIG HEAD: a 1D row/line-config match is a SPECIFIC two-band objective -- far stronger evidence than a
    # lone-cell marker/erase generated by a command control (a rotation button). It leads so _compile selects its
    # non-degenerate cell-wise-mismatch disc (measure > 0) rather than a spurious NONE.EXIST(button). Fires ONLY on
    # multi-colour differing equal-length bands with a shared multiset (a permutation/rotation), so nav, erase, and
    # monochrome grid-box games produce no rowmatch and are untouched.
    config_hyps = [_mk("SAME", rm, cue="perception:rowmatch") for rm in _row_match_targets(g, bg)]
    config_hyps += [_cmk(sl, "perception:slider") for sl in _slider_targets(g, bg)]
    config_hyps += [_mk("SAME", od, cue="perception:order") for od in _order_targets(g, bg)]
    config_hyps += [_mk("SAME", sm, cue="perception:shapematch") for sm in _shape_completion_targets(g, bg)]
    # --- NEW observe-only config heads (tail-ranked; empty unless flag ON -> regression-safe) ---
    config_hyps_new = []
    if USE_SYMMETRY_PLACE:
        try:
            import symmetry_place as _SP
            config_hyps_new += [_mk("SAME", mp, cue="perception:mirrorplace") for mp in _SP.symmetry_place_targets(g, bg)]
        except Exception:
            pass
    if USE_MAP_DECODE:
        try:
            import map_decode as _MD
            _corr = _MD.discover_correspondence(g, bg)   # FRAME-ONLY mechanic discovery (no game id)
            if _corr.get("found"):
                config_hyps_new += [_mk("SAME", ("mapdecode", _corr.get("n_pairs", 0)), cue="perception:mapdecode")]
        except Exception:
            pass
    # CONTAIN_FIT (INSIDE, BE_AT): a HOLLOW FRAME on the board => the objective is to drive the controllable INSIDE
    # its enclosed slot. This is the specific molecule for a fitting game, and the enclosed-interior percept is a
    # strong signal, so it is ranked at the FRONT (ahead of generic colour/object candidates) -- not buried in the
    # object tail where a small max_hyps would cut it.
    fit_hyps = []
    try:
        _bgc = int(np.bincount(g.ravel()).argmax())
        for (iy, ix, isz) in _enclosed_interiors(g, _bgc)[:2]:
            fit_hyps.append(_mk("BE_AT", ("cell", iy, ix), cue="contain-fit"))
            fit_hyps[-1]["descriptor"] = f"CONTAIN_FIT(SOME(x: BE_AT(CONTROLLABLE[{ctrl}], INSIDE-frame@{iy},{ix})))"
    except Exception:
        fit_hyps = []
    # ASSEMBLY / SHAPE-LINKER (cn04, image-confirmed): a MULTI-PIECE board where the objective is to make the
    # controllable piece's tips OVERLAP another piece's tips (select + rotate + link; the overlap region is what
    # the descriptive classifier miscalls "paint"). The INNATE MIRROR-SIMILAR prior (the missing inductive bias):
    # pair the controllable with the MOST SIMILAR-SIZED piece first -- similar shapes "want" to be brought together
    # and connected -- rather than targeting arbitrary pieces or a hole. Ranked high; rotate modality supplies the
    # reorientation relations (BECOME, SAME, TOUCH); reward disposes.
    assembly_hyps = []
    try:
        from object_seg import segment_objects as _seg2
        _bg2 = int(np.bincount(g.ravel()).argmax())
        pieces = [o for o in _seg2(g, bg=_bg2) if o["size"] >= 6]
        if len(pieces) >= 2:
            ctrl_piece = None
            for o in pieces:                                    # the controllable's own piece (holds the marker colour)
                if ctrl is not None and ctrl in set(o.get("color_sig", ())):
                    ctrl_piece = o; break
            csz = ctrl_piece["size"] if ctrl_piece else max(p["size"] for p in pieces)
            others = [o for o in pieces if o is not ctrl_piece]
            others.sort(key=lambda o: abs(o["size"] - csz))     # MOST SIMILAR-SIZED first = the mirror partner
            for o in others[:4]:
                ty, tx = _piece_tip(o, g, ctrl)             # (b) target the piece's TIP, not its centroid
                sim = round(1.0 / (1.0 + abs(o["size"] - csz)), 2)
                assembly_hyps.append(_mk("TOUCH", ("cell", ty, tx), cue="assembly"))
                assembly_hyps[-1]["descriptor"] = (f"ASSEMBLY/MIRROR(TOUCH(CONTROLLABLE[{ctrl}], "
                                                   f"SIMILAR-PIECE-tip@{ty},{tx}) sim={sim})")
    except Exception:
        assembly_hyps = []
    _ranked = reach_head + fit_hyps + assembly_hyps + config_hyps + color_hyps + perc_hyps + obj_hyps + comp_hyps + config_hyps_new
    _seen_d, hyps = set(), []
    for _h in _ranked:
        _d = _h.get("descriptor")
        if _d in _seen_d:
            continue
        _seen_d.add(_d); hyps.append(_h)
    # OPTION (c), principled form: REACH objectives (BE_AT/TOUCH) and MARKER-targeting objectives outrank any
    # objective aimed at a WALL TEXTURE. A goal marker is <=2 components (the reach-head's own definition); a
    # wall texture is many. The pre-resolution cycle (task_type still unknown, ctrl still None) was committing a
    # relational objective on a wall colour -- first NONE.EXIST(2), then SAME(0) once NONE.EXIST was sunk: pure
    # whack-a-mole. So sink EVERY non-reach hypothesis whose target is a multi-component wall colour, plus any
    # NONE.EXIST in a confirmed nav regime, below everything else BEFORE the max_hyps cut. Re-RANK not drop:
    # demoted candidates stay in the tail and reward can still dispose toward them on a game that needs them.
    _nav_regime = (rpt.get("task_type") == "nav") or (ctrl is not None and modality in ("translate", "counter"))
    def _wall_target(h):
        tc = h.get("target_color")
        return isinstance(tc, int) and colcount.get(tc, 0) > 2          # multi-component target = wall texture
    def _demote_h(h):
        rel = h.get("relation")
        tc = h.get("target_color")
        if rel in ("BE_AT", "TOUCH"):                                   # never demote a reach
            return False
        if isinstance(tc, int) and cue_target.get(rel) == tc:          # a GOAL-CUE binding (collectible NONE.EXIST,
            return False                                               # stencil COVER) is perceptual evidence, not a
        #                                                                spurious wall objective. Walls fire no cue, so
        #                                                                they still sink; this only rescues genuinely
        #                                                                perceived targets that have >2 components.
        # (a) ACTION-CONTINGENT SEMANTICS: on a MULTI-PIECE board under a MOTION modality (translate/rotate), a
        # recolor/paint effect is the OVERLAP of two pieces linking -- contact, not a paint goal. So demote paint
        # heads (BECOME/COVER) below the assembly candidates: the causing action, not the pixel effect, names it.
        if assembly_hyps and modality in ("translate", "rotate") and rel in ("BECOME", "COVER"):
            return True
        if _wall_target(h):                                            # any non-reach objective on a wall sinks
            return True
        return bool(_nav_regime and rel == "NONE.EXIST")                # belt-and-suspenders on confirmed nav
    _demote = [h for h in hyps if _demote_h(h)]
    if _demote:
        hyps = [h for h in hyps if h not in _demote] + _demote
    hyps = hyps[:max_hyps]
    return dict(modality=modality, controllable=ctrl, hypotheses=hyps, report=rpt,
                source=("goal_cues" if cues else "modality_prior") + "+perception")
