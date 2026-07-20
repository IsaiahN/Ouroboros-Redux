"""
visual_projection.py  --  VISUAL-FIRST projection / unfolding layer  (observe-only, additive)
================================================================================================
Implements the staged pipeline (scene read -> concept -> projection) that the recomparison showed is
MISSING. The kernel currently abduces a goal predicate first and probes to confirm it; this layer runs
the human order instead:

  Stage 0  visual scene read   -> a SCENE GRAPH (objects + roles + RELATIONS + HUD/resources)
  Stage 1+2 prime projection   -> project the NSM primes onto OBJECTS-IN-RELATION to GENERATE the
                                  environment-specific vocabulary + a structural concept (the few-word
                                  paradigm's machine form), which NARROWS which grammar predicates to search

Design contract (per Isaiah, this session):
  * the kernel is mostly fine -- this does NOT replace goal_cues/objective_abductor; it CONTEXTUALIZES
    objects BEFORE abduction so the search space is narrowed (visual-first, goal-last).
  * OBSERVE-ONLY: nothing here is wired to the scored decision path. Cannot regress lp85.
  * the bar is REPRESENTABILITY (does projection produce the right structural concept), not solving.
  * projection is RELATION-driven (generalizes goal_cues' flat per-object rules) and its binding rules are
    the epigenetic dynamics (coincidence/two-key, precondition, delayed) -- noted at each rule.

Built to run on a raw HxW grid with a self-contained extractor, so it is testable without the live kernel;
when the kernel's extractor / SelfModel are available, pass them in to use real perception.
"""
from __future__ import annotations
import os, sys as _sys
import numpy as np
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

# import the LIVE grammar so projections emit validated predicates and can explain themselves
_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.join(_here, "latest_008"), os.path.join(_here, "ouro")):
    if os.path.isdir(_p) and _p not in _sys.path:
        _sys.path.insert(0, _p)
try:
    import objective_grammar as G
except Exception:
    G = None


# ----------------------------------------------------------------------------------------------------
# Stage 0a -- objects (connected components per color). Falls back to this if no extractor is injected.
# ----------------------------------------------------------------------------------------------------
def _background(grid):
    vals, cnts = np.unique(grid, return_counts=True)
    return int(vals[np.argmax(cnts)])


def _components(grid, bg):
    H, W = grid.shape
    seen = np.zeros((H, W), bool)
    objs = []
    for i in range(H):
        for j in range(W):
            if seen[i, j] or grid[i, j] == bg:
                continue
            col = grid[i, j]
            stack, cells = [(i, j)], []
            seen[i, j] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny, nx] and grid[ny, nx] == col:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            objs.append((int(col), cells))
    return objs


@dataclass
class Obj:
    id: int
    color: int
    cells: frozenset
    size: int
    bbox: tuple        # (y0,x0,y1,x1)
    centroid: tuple
    w: int
    h: int
    shape_sig: frozenset   # cells normalized to bbox top-left (translation-invariant)
    roles: set = field(default_factory=set)


def extract_objects(grid):
    bg = _background(grid)
    out = []
    for k, (col, cells) in enumerate(_components(grid, bg)):
        ys = [c[0] for c in cells]; xs = [c[1] for c in cells]
        y0, x0, y1, x1 = min(ys), min(xs), max(ys), max(xs)
        sig = frozenset((y - y0, x - x0) for y, x in cells)
        out.append(Obj(id=k, color=col, cells=frozenset(cells), size=len(cells),
                       bbox=(y0, x0, y1, x1), centroid=(sum(ys) / len(ys), sum(xs) / len(xs)),
                       w=x1 - x0 + 1, h=y1 - y0 + 1, shape_sig=sig))
    return out, bg


# ----------------------------------------------------------------------------------------------------
# Stage 0b -- ROLES (color meanings). Heuristic + optional injected controllable id.
# ----------------------------------------------------------------------------------------------------
def _is_edge_bar(o: Obj, H, W):
    """HUD bar / counter: confined to the outer <=3 rows/cols AND spanning most of that edge.
    Ported from objective_abductor._is_hud's geometric test (the partial HUD reader already in the kernel)."""
    y0, x0, y1, x1 = o.bbox
    band = 3
    on_top = y1 < band and (x1 - x0 + 1) >= 0.5 * W
    on_bot = y0 >= H - band and (x1 - x0 + 1) >= 0.5 * W
    on_lft = x1 < band and (y1 - y0 + 1) >= 0.5 * H
    on_rgt = x0 >= W - band and (y1 - y0 + 1) >= 0.5 * H
    return on_top or on_bot or on_lft or on_rgt


def assign_roles(objs, grid, controllable_id: Optional[int] = None):
    H, W = grid.shape
    if not objs:
        return
    sizes = sorted(o.size for o in objs)
    med = sizes[len(sizes) // 2]
    color_counts = Counter(o.color for o in objs)
    # per-color occupancy, for an isolation test (collectibles are isolated; structure/walls are clustered)
    occ = defaultdict(set)
    for o in objs:
        occ[o.color] |= o.cells

    def isolated(o):
        y0, x0, y1, x1 = o.bbox
        ring = occ[o.color] - o.cells
        for y in range(y0 - 2, y1 + 3):
            for x in range(x0 - 2, x1 + 3):
                if (y, x) in ring:
                    return False
        return True

    for o in objs:
        if controllable_id is not None and o.id == controllable_id:
            o.roles.add("agent")
        if _is_edge_bar(o, H, W):
            o.roles.add("hud")
        y0, x0, y1, x1 = o.bbox
        spans = (o.w >= 0.8 * W) or (o.h >= 0.8 * H)
        thin = (o.h <= 2 or o.w <= 2)
        if spans and (thin or o.size >= 0.4 * H * W):
            o.roles.add("wall")
        # collectible: small, MANY same-color, AND spatially ISOLATED (not part of a wall/lattice/maze)
        if o.size <= max(2, med) and color_counts[o.color] >= 4 and isolated(o):
            o.roles.add("collectible")
        if not o.roles:
            o.roles.add("inert")


# ----------------------------------------------------------------------------------------------------
# Stage 0c -- RELATIONS between objects (this is the layer goal_cues lacks)
# ----------------------------------------------------------------------------------------------------
def _hflip(sig, w):  return frozenset((y, w - 1 - x) for y, x in sig)
def _vflip(sig, h):  return frozenset((h - 1 - y, x) for y, x in sig)


def detect_relations(objs, grid, bg):
    H, W = grid.shape
    rel = defaultdict(list)

    # PAIR / MATCH: objects sharing an identical normalized shape (translation-invariant) -> match candidates
    by_shape = defaultdict(list)
    for o in objs:
        if "hud" in o.roles or "wall" in o.roles:
            continue
        by_shape[o.shape_sig].append(o)
    for sig, group in by_shape.items():
        if len(group) >= 2 and len(sig) >= 2:
            rel["pairing"].append(tuple(g.id for g in group))

    # MIRROR: a pair where one is the h-/v-flip of the other. Tightened: only SUBSTANTIAL shapes (>=6 cells)
    # whose shape is NOT already self-symmetric (a self-symmetric blob trivially "mirrors" everything) -- this
    # removes the tiny-blob combinatorial explosion that made the relation meaningless.
    cand = [o for o in objs if "hud" not in o.roles and "wall" not in o.roles
            and o.size >= 6 and o.shape_sig != _hflip(o.shape_sig, o.w)
            and o.shape_sig != _vflip(o.shape_sig, o.h)]
    for a_i in range(len(cand)):
        for b_i in range(a_i + 1, len(cand)):
            a, b = cand[a_i], cand[b_i]
            if a.size != b.size or a.w != b.w or a.h != b.h:
                continue
            if b.shape_sig == _hflip(a.shape_sig, a.w):
                rel["mirror"].append((a.id, b.id, "h"))
            elif b.shape_sig == _vflip(a.shape_sig, a.h):
                rel["mirror"].append((a.id, b.id, "v"))

    # CONTAINMENT (INSIDE): A's bbox strictly inside B's bbox, different color (hole/region-in-shape)
    for a in objs:
        for b in objs:
            if a.id == b.id or a.color == b.color:
                continue
            ay0, ax0, ay1, ax1 = a.bbox; by0, bx0, by1, bx1 = b.bbox
            if by0 < ay0 and bx0 < ax0 and by1 > ay1 and bx1 > ax1:
                rel["inside"].append((a.id, b.id))

    # PATH / CONVEYOR: a thin connected line of one non-bg color, length >> width (a track / belt)
    for o in objs:
        if "wall" in o.roles or "hud" in o.roles:
            continue
        longness = max(o.w, o.h) / max(1, min(o.w, o.h))
        if longness >= 5 and o.size >= 6:
            rel["path"].append(o.id)

    # GLOBAL SYMMETRY AXIS: grid is NEARLY h- or v-mirror symmetric but not exactly (a completion target)
    nz = (grid != bg)
    def asym(flipped):
        diff = np.logical_xor(nz, flipped)
        return diff.sum()
    h_as = asym(np.fliplr(nz)); v_as = asym(np.flipud(nz))
    tot = max(1, nz.sum())
    if 0 < h_as <= 0.25 * tot:
        rel["symmetry_axis"].append(("h", int(h_as)))
    if 0 < v_as <= 0.25 * tot:
        rel["symmetry_axis"].append(("v", int(v_as)))

    return dict(rel)


# ----------------------------------------------------------------------------------------------------
# PERCEPTION LAYER 1 -- MOTION (needs a previous frame). Fires temporal (REPLAY) + conveyor evidence.
# ----------------------------------------------------------------------------------------------------
def detect_motion(grid, prev):
    if prev is None:
        return {}
    prev = np.asarray(prev)
    if prev.shape != grid.shape:
        return {}
    bgp, bgn = _background(prev), _background(grid)
    nz_p, nz_n = (prev != bgp), (grid != bgn)
    changed = int((grid != prev).sum())
    vanished = int((nz_p & ~nz_n).sum())   # past-state cells now empty -> a trailing echo (temporal signal)
    appeared = int((~nz_p & nz_n).sum())
    # dominant translation: shift grid by small vectors, pick the one that best matches prev (belt motion)
    best = (0, 0, changed)
    if 0 < changed:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                shifted = np.roll(np.roll(prev, dy, 0), dx, 1)
                mism = int((shifted != grid).sum())
                if mism < best[2]:
                    best = (dy, dx, mism)
    translated = best[2] < 0.5 * max(1, changed)   # a consistent shift explains most of the change -> belt
    return dict(changed=changed, vanished=vanished, appeared=appeared,
                shift=(best[0], best[1]) if translated else None)


# ----------------------------------------------------------------------------------------------------
# PERCEPTION LAYER 2 -- TOPOLOGY / REACHABILITY (single frame). Fires REACH (maze).
# ----------------------------------------------------------------------------------------------------
def detect_topology(grid, bg):
    free = (grid == bg)
    H, W = grid.shape
    wall_frac = 1.0 - free.mean()
    if wall_frac < 0.15:
        return {}
    # corridor-ness: free cells with <=2 free 4-neighbours are passages; >=3 are open rooms
    fy, fx = np.where(free)
    corridor = 0; total = 0
    for y, x in zip(fy.tolist(), fx.tolist()):
        nb = 0
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and free[ny, nx]:
                nb += 1
        total += 1
        if nb <= 2:
            corridor += 1
    corridor_frac = corridor / max(1, total)
    # a maze: substantial walls AND most free space is narrow passage (not open rooms)
    if wall_frac >= 0.25 and corridor_frac >= 0.55:
        return dict(wall_frac=round(float(wall_frac), 2), corridor_frac=round(corridor_frac, 2))
    return {}


# ----------------------------------------------------------------------------------------------------
# PERCEPTION LAYER 3 -- GOAL TEMPLATE (single frame): outline/hollow shapes = target slots to fill/fit.
# Fixes the ar25 case where the symmetry/fit is the GOAL state, not the current frame.
# ----------------------------------------------------------------------------------------------------
def detect_goal_template(objs, grid, bg):
    outlines = []
    for o in objs:
        if "hud" in o.roles or "wall" in o.roles or o.w < 3 or o.h < 3:
            continue
        y0, x0, y1, x1 = o.bbox
        interior = interior_bg = 0
        for y in range(y0 + 1, y1):
            for x in range(x0 + 1, x1):
                interior += 1
                if grid[y, x] == bg:
                    interior_bg += 1
        if interior > 0 and interior_bg / interior > 0.6 and o.size < 0.6 * o.w * o.h:
            outlines.append(o.id)
    return dict(slots=outlines) if outlines else {}


# ----------------------------------------------------------------------------------------------------
# Stage 1+2 -- PROJECTION: primes x objects-in-relation -> vocabulary + structural concept
#   Each rule is (relational trigger present) -> (prime(s), grammar predicate, structural concept).
#   The epigenetic binding rule that governs each is noted in `bind`.
# ----------------------------------------------------------------------------------------------------
@dataclass
class Projection:
    vocab: str            # the environment-specific term generated
    primes: tuple         # which universal primes projected
    predicate: str        # the objective-grammar predicate this NARROWS the abductor toward
    concept: str          # structural concept (machine form of the few-word paradigm)
    bind: str             # epigenetic binding rule governing this projection
    evidence: str         # what in the scene triggered it
    score: float = 0.0    # salience (evidence strength); used for competition + erasure


def project(objs, rel, grid, bg, motion=None, topo=None, goal=None):
    """Generate candidate projections WITH salience scores, then BIND with epigenetic discipline:
       coincidence (min evidence to enter), competition (keep within a margin of the leader), erasure
       (drop the rest). Returns (bound, all_scored, needs). `bound` is the NARROWED concept set."""
    H, W = grid.shape
    n_real = max(1, sum(1 for o in objs if "hud" not in o.roles and "wall" not in o.roles))
    cands = []

    # symmetry: strong only if a SUBSTANTIAL mirror pair exists, or the grid is near-symmetric with low asym
    mir = rel.get("mirror", [])
    axis = rel.get("symmetry_axis", [])
    sym_score = min(1.0, 0.5 * len(mir)) + (0.6 if axis else 0.0)
    if sym_score > 0:
        cands.append(Projection("symmetry_completion", ("SAME", "ALL", "BE_AT"), "SAME/FIT",
            "complete or fit pieces so the configuration becomes mirror-symmetric",
            "coincidence: a real mirror relation between substantial objects (or a near-symmetric grid)",
            f"mirror={len(mir)} axis={axis}", score=sym_score))

    # match/pair: needs >=1 shape-group of >=2 substantial objects
    groups = [g for g in rel.get("pairing", []) if len(g) >= 2]
    if groups:
        cands.append(Projection("match_pairs", ("SAME", "ALL"), "SAME",
            "match / pair the objects sharing a shape",
            "coincidence: >=2 objects share a translation-invariant shape signature",
            f"{len(groups)} shape-group(s)", score=min(1.0, 0.4 * len(groups))))

    # fill/cover: enclosed regions, scored by how many relative to object count
    ins = rel.get("inside", [])
    if ins:
        cands.append(Projection("fillable_region", ("INSIDE", "ALL", "BECOME"), "COVER",
            "fill/cover the enclosed regions to a target color",
            "coincidence: an enclosed region co-occurs with a bounding shape",
            f"{len(ins)} enclosed region(s)", score=min(1.0, len(ins) / n_real)))

    # paint-to-target (cd82): palette of >=3 swatch colors AND enclosed canvas region(s)
    swatches = [o for o in objs if o.size <= 4 and "hud" not in o.roles]
    palette = len({o.color for o in swatches})
    if palette >= 3 and ins:
        cands.append(Projection("paint_to_target", ("BECOME", "ALL", "SAME"), "BECOME/COVER",
            "select a color, then paint region(s) until the canvas matches a target arrangement",
            "two-key + precondition + delayed: effect depends on a SELECTED color and settles over frames",
            f"palette={palette}, regions={len(ins)}", score=min(1.0, 0.3 * palette)))

    # conveyor/intercept: a thin-long track object AND real belt MOTION (a consistent NON-zero shift).
    paths = rel.get("path", [])
    sh = motion.get("shift") if motion else None
    belt = bool(sh and sh != (0, 0) and motion.get("changed", 0) > 0)
    if paths and belt:
        cands.append(Projection("conveyor_intercept", ("BE_AT", "TOUCH", "AFTER"), "BE_AT@locus",
            "intercept the right item as it travels the path/belt past a fixed point (timing)",
            "delayed: the interaction outcome is read AFTER the item reaches the locus",
            f"path={paths} shift={sh}", score=min(1.0, 0.6 + 0.2 * len(paths))))

    # collect-all: isolated small collectibles
    coll = [o for o in objs if "collectible" in o.roles]
    if coll:
        c = Counter(o.color for o in coll).most_common(1)[0]
        cands.append(Projection("collect_all", ("NONE", "EXIST"), "NONE.EXIST",
            "remove/consume every collectible of the target kind",
            "push-pull: a collectible that disappears on contact confirms the erase reading",
            f"{c[1]} isolated collectibles", score=min(1.0, c[1] / n_real)))

    # LAYER 2 -- maze topology (reachability): narrow corridors dominate the free space
    if topo:
        cands.append(Projection("maze_reach", ("ALL", "SOME", "BE_AT"), "REACH",
            "route a mover through the corridors to an exit",
            "topology: free space is corridor-like (reachability), not open rooms",
            f"wall={topo['wall_frac']} corridor={topo['corridor_frac']}",
            score=min(1.0, 0.4 + topo["corridor_frac"])))

    # LAYER 3 -- goal template: outline/hollow shapes are target slots to fit/fill into
    if goal and goal.get("slots"):
        cands.append(Projection("match_goal", ("ALL", "SAME"), "MATCH_GOAL",
            "fit/fill the pieces into the outlined target slots so the area matches the goal",
            "coincidence: outline (hollow) shapes mark intended end-positions",
            f"{len(goal['slots'])} target slot(s)", score=min(1.0, 0.5 + 0.15 * len(goal['slots']))))

    # LAYER 1 -- temporal (past manipulation): a real ECHO leaves cells vanished WITHOUT matching new ones
    # (a trail persists). Symmetric vanished==appeared is ordinary motion, NOT a temporal echo -- exclude it.
    if motion:
        van, app = motion.get("vanished", 0), motion.get("appeared", 0)
        if van >= 8 and van >= 2 * app:
            cands.append(Projection("past_replay", ("SAME", "BEFORE"), "REPLAY",
                "make a state match a past state (manipulate the past)",
                "delayed/temporal: a trailing echo of a prior configuration persists (net disappearance)",
                f"vanished={van} appeared={app}", score=min(1.0, 0.4 + van / 50.0)))

    # ---- BINDING: coincidence gate -> competition -> erasure ----
    GATE = 0.35
    MARGIN = 0.30
    # validate every emitted predicate against the LIVE grammar (drift guard); drop unknown predicates
    if G is not None:
        cands = [c for c in cands if G.validate(c.predicate)]
    gated = [c for c in cands if c.score >= GATE]
    gated.sort(key=lambda c: c.score, reverse=True)
    bound = [c for c in gated if c.score >= gated[0].score - MARGIN] if gated else []

    # only genuinely unprojectable classes remain (tr87 rosetta needs a basis word the grammar lacks)
    needs = [("MAP/CORRESPOND", "rosetta-class symbol mapping; a basis-growth candidate (grammar.GROWTH_CANDIDATES)")]
    return bound, sorted(cands, key=lambda c: c.score, reverse=True), needs


# ----------------------------------------------------------------------------------------------------
# HUD / resource read -- the StepCounter signal the kernel was blind to
# ----------------------------------------------------------------------------------------------------
def read_hud(objs):
    hud = [o for o in objs if "hud" in o.roles]
    return dict(hud_present=bool(hud),
                hud_objects=[o.id for o in hud],
                note=("a HUD/counter band is present (likely a step/score/resource gauge) -- the "
                      "efficiency signal the scored loop must read" if hud else "no edge HUD band detected"))


# ----------------------------------------------------------------------------------------------------
# Top-level: scene read -> projection
# ----------------------------------------------------------------------------------------------------
@dataclass
class SceneRead:
    grid_shape: tuple
    bg: int
    n_objects: int
    roles: dict
    relations: dict
    hud: dict
    projections: list      # BOUND (narrowed) concepts after competition/erasure
    ranked: list           # all scored candidates (for transparency)
    unprojectable: list
    motion: dict = field(default_factory=dict)
    topo: dict = field(default_factory=dict)
    goal: dict = field(default_factory=dict)
    dynamics: dict = field(default_factory=dict)

    def concept_summary(self):
        if not self.projections:
            return "(no structural concept bound from this frame)"
        return " | ".join(f"{p.vocab}({p.score:.2f}):: {p.concept}" for p in self.projections)

    def explain(self):
        """The composer's self-explanation of each bound concept: WORDS + GRAMMAR + PRIMES + evidence.
        This is what the grammar being LIVE buys us -- the composer can say what it sees in the basis."""
        lines = []
        for p in self.projections:
            if G is not None:
                e = G.explain(p.predicate)
                lines.append(f"- {p.vocab} (score {p.score:.2f})\n"
                             f"    words   : {e['words']}\n"
                             f"    grammar : {e['grammar']}\n"
                             f"    primes  : {', '.join(e['primes'])}\n"
                             f"    because : {p.evidence}")
            else:
                lines.append(f"- {p.vocab} -> {p.predicate} (grammar module unavailable)")
        return "\n".join(lines) if lines else "(nothing bound to explain)"


def read_scene(grid, prev_grid=None, frames=None, controllable_id: Optional[int] = None, extractor=None):
    grid = np.asarray(grid)
    if grid.ndim == 1:                      # kernel sometimes returns 1-D; reshape if square-ish
        n = grid.size; s = int(round(n ** 0.5))
        if s * s == n:
            grid = grid.reshape(s, s)
    if extractor is not None:
        objs, bg = extractor(grid)          # use real kernel perception when injected
    else:
        objs, bg = extract_objects(grid)
    assign_roles(objs, grid, controllable_id)
    rel = detect_relations(objs, grid, bg)
    motion = detect_motion(grid, prev_grid) if prev_grid is not None else {}
    topo = detect_topology(grid, bg)
    goal = detect_goal_template(objs, grid, bg)
    bound, ranked, needs = project(objs, rel, grid, bg, motion=motion, topo=topo, goal=goal)

    # MULTI-FRAME DYNAMICS (load-bearing dynamics molecules): only when a real frame SEQUENCE is given.
    # Lazy import avoids a circular dependency (dynamics imports this module). The single-frame prior path
    # used by the abductor passes NO frames, so the scored path (and lp85) is unaffected by construction.
    dyn = {}
    if frames is not None and len(frames) >= 2:
        try:
            import dynamics as _DYN
            dr = _DYN.track(frames)
            dyn = {"molecules": dr.molecules, "scene": {k: v for k, v in dr.scene.items() if k != "counts"}}
            # promote observed physics to bound concepts (observed > inferred), grammar-predicate mapped
            if "CONVEYOR" in dr.molecules and not any(p.vocab == "conveyor_intercept" for p in bound):
                bound.insert(0, Projection("conveyor_intercept", ("BE_AT", "TOUCH", "AFTER"), "BE_AT@locus",
                    "intercept the right item as it travels the observed belt", "OBSERVED motion (tracked)",
                    f"conveyor vec {dr.scene.get('conveyor')}", score=0.95))
            if "GRAVITY" in dr.molecules:
                bound.insert(0, Projection("gravity_settle", ("ALL", "BE_AT", "BELOW"), "BE_AT",
                    "objects fall and settle; place them to their rest positions", "OBSERVED falling (tracked)",
                    f"gravity dir {dr.scene.get('gravity')}", score=0.95))
        except Exception:
            dyn = {}

    role_map = defaultdict(list)
    for o in objs:
        for r in o.roles:
            role_map[r].append(o.id)
    return SceneRead(grid_shape=tuple(grid.shape), bg=bg, n_objects=len(objs),
                     roles=dict(role_map), relations=rel, hud=read_hud(objs),
                     projections=bound, ranked=ranked, unprojectable=needs,
                     motion=motion, topo=topo, goal=goal, dynamics=dyn)


if __name__ == "__main__":
    # tiny smoke test: an enclosed region + a mirror pair
    g = np.zeros((8, 8), int)
    g[1:6, 1:6] = 2; g[2:5, 2:5] = 0      # a frame with a hole (inside)
    g[1, 1] = 3; g[1, 6] = 3              # a trivial mirror pair
    sr = read_scene(g)
    print("objects:", sr.n_objects, "roles:", sr.roles)
    print("relations:", sr.relations)
    print("concept:", sr.concept_summary())
    for p in sr.projections:
        print("  ->", p.vocab, p.primes, "=>", p.predicate, "|", p.bind)
