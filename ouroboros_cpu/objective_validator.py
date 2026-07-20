"""
objective_validator.py — the abduct -> counterfactual-validate loop (metalanguage line 310),
as ONE general pursuit COMPOSER (not a library of per-relation solvers).

A grammar objective RELATION(controllable, target) is compiled into a single non-negative
DISCREPANCY measure d(state) with d==0 exactly when the objective holds:
    BE_AT/TOUCH   -> distance(controllable, target)          (drive the mover onto the target)
    NONE.EXIST    -> count(target cells)                      (consume them to zero)
    COVER         -> count(unfilled hole cells)              (fill them to zero)
    SAME/BECOME   -> |footprint(controllable) symdiff footprint(target)|  (make shapes coincide)
Every relation is the SAME shape of problem: reduce a discrepancy to zero.  ONE engine then runs
for all of them — a best-first Go-Explore (line 320) over ambient-masked states, expanding the
explored state of lowest discrepancy, backtracking via FREE resets, reading reward.

Two-part validation (tighter than before): a hypothesis validates iff REWARD fires AND the
composed predicate is actually satisfied (d==0) at the rewarding state — so the specific target
BINDING is confirmed, not merely that some reward happened.  The grammar proposes; interaction
disposes; and the disposal checks the exact predicate, not a coincidence.
"""
import numpy as np

SETTLE_STEPS = 25            # frames to wait for a DELAYED win-reward after the predicate is met
from collections import namedtuple
from scipy.ndimage import label
from objective_abductor import abduce, _is_hud, MODALITY_RELATION_PRIOR
try:
    import prediction_error_bus as _pe            # Phase-1 self-reasoning spine (localized, confidence-weighted error)
except Exception:
    _pe = None
def _aid_ok(a):
    """Only real moves carry object-transition evidence. A RESET is not a law about the world."""
    try:
        return int(getattr(a, "value", -1)) in (1, 2, 3, 4)
    except Exception:
        return False


def _perceive_grid(adapter):
    """Single GUARDED grid read for ALL regimes -- routes through the shared Perception gateway, which asserts the
    frame is full resolution (downsampling raises). Drop-in for _perceive_grid(adapter)."""
    import regime_factory as _RF
    return _RF.SHARED.perception.grid(adapter)



def _pe_pub(adapter, *a, **k):
    """Publish an attribution into the per-game bus, routed through the derivation channel.
    Fully guarded: the spine can never crash a solve."""
    if _pe is None:
        return None
    try:
        k.setdefault("emit", lambda s: _emit(adapter, s))
        return _pe.publish(_game_mem(adapter), *a, **k)
    except Exception:
        return None

def _reflex(adapter):
    """Phase-2 GENERALISED ANOMALY REFLEX: the causal-split reflex applied to EVERY binding layer
    via the prediction-error bus. Reads the top PERSISTENT (seen>=2 -- the hysteresis that stops a
    single cold-probe anomaly from triggering a refine) unresolved error and routes it to the refine
    its layer warrants -- so a RECURRING binding error, at any layer, drives the matching self-
    correction instead of the human naming it. Narrates the routing; returns (layer, seen) or None.
    Safe: it reads the bus and routes; the causal/objective refines it names already run; the
    segmentation/role fragmentation is intentionally NOT executed here (would false-split unpumped
    fluid) until the pillar data is confirmed. Fully guarded."""
    if _pe is None:
        return None
    try:
        errs = _pe.persistent_errors(_game_mem(adapter), min_seen=2)
        if not errs:
            return None
        top = errs[0]; layer = top["layer"]
        refine = {"segmentation": "re-bind (common-fate): split same-colour independent movers, mark never-movers static",
                  "roles": "re-classify by dynamic signature (a 'fixed' that moved, or a fluid-colour cell that never moved -> pillar)",
                  "causal": "re-test the inert/untested controls after the state advanced (conditional unlock)",
                  "objective": "re-induce / sequence the objective (the current model keeps plateauing)",
                  "component": "recalibrate the falsified molecule/percept"}.get(layer, "revise this binding")
        # DEDUP the narration (do not re-emit the same reflex every re-attempt -- the flood wart): emit only the
        # FIRST time this (layer, obj) crosses the hysteresis threshold. The bus already tracks recurrence via seen.
        seen_keys = _game_mem(adapter).setdefault("_reflex_narrated", set())
        key = (layer, top.get("obj"))
        if key not in seen_keys:
            seen_keys.add(key)
            _emit(adapter, "REFLEX  persistent %s error (seen %d, conf %.2f) -> REFINE: %s"
                  % (layer, top.get("seen", 1), top.get("confidence", 0.0), refine))
        return (layer, top.get("seen", 1))
    except Exception:
        return None


def _probe_priority(o, cmap, mem):
    """Phase-3 ACTIVE PROBE-SELECTION (epistemic foraging): score a candidate control by expected
    uncertainty-reduction, so probes go where they disambiguate the MOST -- replacing blind size-order.
    Generalises design_ping's 'pick the most DISTINCTIVE probe' from self-recognition to control-typing.
    Higher = probe sooner:
      untested type (no hypothesis)        -> maximal info (its effect is unknown)
      split / conditional type (ambiguous) -> high (a probe resolves which pathway / precondition)
      active type, this instance untested  -> moderate (position-specific effect may differ)
      confirmed-inert type                 -> minimal (re-probing a known dud tells little)
    A live unresolved causal error on the bus lifts the informative probes further. Size is a tiny tie-break."""
    tkey = _type_key(o)
    h = cmap.get(tkey)
    if h is None:
        score = 3.0                                           # untested type -> most informative
    else:
        st = h.get("status"); eff = h.get("effect")
        if st in ("split", "conditional"):
            score = 2.5                                        # ambiguous pathway -> disambiguate
        elif st == "confirmed" and eff == "inert":
            score = 0.2                                        # known dud
        elif eff and eff != "inert":
            score = 1.0                                        # active type, this instance untested
        else:
            score = 1.5
    try:
        if _pe is not None and score >= 2.0 and _pe.top_error(mem, layer="causal") is not None:
            score += 0.5                                       # a causal ambiguity is flagged -> favour informative probes
    except Exception:
        pass
    score += max(0.0, (30 - o.get("size", 0))) * 0.001        # tiny tie-break: button-sized first
    return score

# A compiled objective has TWO faces: measure(state) (0 iff the objective holds) and active(state)
# (the cells driving the discrepancy -- where a LOCATED action should act). One mechanism then lets
# the engine pursue by discrete moves OR located clicks at the cells the objective says are wrong.
Discrepancy = namedtuple("Discrepancy", ["measure", "active"])


# ---- Layer-1 controller injection (inversion of control) ------------------------------------------------------
# DEPENDENCY DAG (one-directional, acyclic):
#   objective_primitives (the Layer-0 helpers, currently co-located in THIS module)
#        ^                                   ^
#        |                                   |
#   autonomy_controllers (Layer 1) ----->   |   (imports the Layer-0 primitives, top-level)
#        ^                                   |
#        |                                   |
#   orchestrator / harness (Layer 2 wiring) --  (imports BOTH, registers hooks below)
#
# INVARIANT: this module (Layer 0 + flow) MUST NOT import autonomy_controllers. The flow calls Layer-1 controllers
# only through the hook registry, so a controller is injected, never imported here -- which is what keeps the graph
# acyclic. A seam calls a hook only if one is registered; unregistered => default behaviour, so this is inert until
# an orchestrator wires it. (The textbook end-state is to split the Layer-0 primitives into their own module; that
# extraction is entangled through compile_objective's closure and is deferred until it can be verified by running.)
_CONTROLLER_HOOKS = {}


def register_controller_hook(name, fn):
    """Wire a Layer-1 controller into the flow by name (e.g. 'objective_induction', 'fidelity_monitor',
    'schema_planner'). Called by an orchestrator that imports both layers -- never by this module."""
    _CONTROLLER_HOOKS[name] = fn


def controller_hook(name):
    """Return the registered Layer-1 controller for `name`, or None (=> default flow behaviour)."""
    return _CONTROLLER_HOOKS.get(name)


def _apply(adapter, a):
    """Dispatch one action: a located tuple (kind, r, c) via step_at, else a nullary action via step.
    The DSL only ever sees 'act at a cell' / 'act'; the adapter owns the ARC encoding."""
    if isinstance(a, tuple) and len(a) == 3 and isinstance(a[0], str):
        _r = adapter.step_at(a[0], a[1], a[2])
    else:
        _r = adapter.step(a)
    # EVERY caller unpacks exactly 4. When that is false the ValueError names the CALLER's line and says nothing about
    # what came back or which adapter sent it, so `COMPOSER DIED: too many values to unpack (expected 4)` is all you
    # get -- from a composer that then keeps walking as a headless fallback and reports a score. Two adapters exist
    # (OnlineArcAdapter, _QueueAdapter) and _apply is the seam between them; a seam that fails anonymously is the
    # worst kind. So: say what actually arrived.
    try:
        _n = len(_r)
    except Exception:
        _n = -1
    if _n != 4:
        import traceback as _tb
        raise ValueError("_apply: adapter=%s step=%r returned %s value(s), not 4\n  action=%r (%s)\n  value=%.300r\n"
                         "  callers:\n%s"
                         % (type(adapter).__name__, getattr(adapter, "step", None), _n, a, type(a).__name__, _r,
                            "".join("    " + l for l in _tb.format_stack()[-5:-1])))
    return _r


def _bg(g):
    return int(np.bincount(g.ravel()).argmax())


def _centroid(g, col):
    ys, xs = np.where(g == col)
    return (ys.mean(), xs.mean()) if len(ys) else None


def _footprint(g, col):
    return (g == col)


def _hud_colors(g):
    """Ambient/HUD colours = non-bg colours confined to an edge bar (the ticking action counter).
    Masking these is what keeps the state space finite: otherwise the counter makes every grid
    unique and dedup never fires."""
    bg = _bg(g)
    return [int(c) for c in np.unique(g) if int(c) != bg and _is_hud(g, int(c))]


def _hud_region(g):
    """Bounding box of all ambient/HUD cells.  Masking the whole REGION (not just the colour) is
    necessary because a depleting counter recolours its own cells (e.g. colour-6 -> colour-0), so
    colour-masking alone leaves a varying footprint that pollutes state dedup."""
    huds = _hud_colors(g)
    if not huds:
        return None
    ys, xs = np.where(np.isin(g, huds))
    if len(ys) == 0:
        return None
    return (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max()))


def _abstract(g, region):
    bg = _bg(g)
    a = g.copy()
    if region:
        r0, r1, c0, c1 = region
        a[r0:r1 + 1, c0:c1 + 1] = bg
    return a.tobytes()


def compile_discrepancy(relation, ctrl, target_color, grid0):
    """Compose a grammar relation into a Discrepancy(measure, active). measure(g)==0 iff the objective
    holds; active(g) is the set of cells driving it -- the cells a located action should act on. This
    is the single point where the relation enters the otherwise relation-agnostic engine."""
    def cells(arr):
        return [tuple(int(x) for x in c) for c in np.argwhere(arr)]

    # ---- perception-source TARGET specs (§11.259): a specific cell, or a symmetry axis ----
    # The COMPOSER binds these from in-frame detectors; the kernel relation consumes them unchanged.
    if isinstance(target_color, tuple):
        kind = target_color[0]
        if kind == "mirrorplace":                 # OBSERVE-ONLY (ar25): drive an unpaired piece to its mirror slot
            try:
                _, orient, pos, (tr, tc) = target_color
                def measure(g):
                    g = np.asarray(g); return 0.0 if int(g[tr, tc]) != _bg(g) else 1.0
                def active(g):
                    g = np.asarray(g); return [] if int(g[tr, tc]) != _bg(g) else [(tr, tc)]
                return measure, active
            except Exception:
                return (lambda g: 1.0), (lambda g: [])   # degrade -> never crash the pursue loop
        if kind == "mapdecode":                   # OBSERVE-ONLY: FRAME-ONLY rosetta decode (no game id). Degrades safely.
            try:
                import map_decode as _MD
                _bgm = _bg(grid0)
                _corr = _MD.discover_correspondence(grid0, _bgm)
                return _MD.map_decode_disc(grid0, _bgm, _corr)
            except Exception:
                return (lambda g: 1.0), (lambda g: [])   # degrade -> never crash the pursue loop
        if kind == "cell":                       # BE_AT a SPECIFIC cell (a perceived goal marker / exit)
            _, tr, tc = target_color
            tcell = np.array([tr, tc])

            def m(g):
                p = _centroid(g, ctrl)
                return 1e9 if p is None else float(np.abs(tcell - np.array(p)).sum())
            return Discrepancy(m, lambda g: [(int(tr), int(tc))])
        if kind == "gridmirror":                  # CONFIG-COMPLETION: FILL the mirror cells of a reference
            _, orient, col = target_color          # 'v' left<->right, 'h' top<->bottom, 'd' diagonal (y=x)

            def _mir(a):
                if orient == "v":
                    return a[:, ::-1]
                if orient == "h":
                    return a[::-1, :]
                return a.T                          # diagonal: proposed only for square grids

            def _unfilled(g):
                ref = (g == col); tgt = _mir(ref); bgc = _bg(g)
                return tgt & (g == bgc) & (~ref)    # target positions still empty (placements may differ in colour)

            def m(g):
                return float(_unfilled(g).sum())

            def active(g):
                return [(int(r), int(c)) for r, c in np.argwhere(_unfilled(g))]
            return Discrepancy(m, active)
        if kind == "objcells":                    # REACH an OBJECT (multi-colour sprite): ctrl -> nearest object cell (11.286)
            cells_arr = np.array(target_color[1])

            def m(g):
                p = _centroid(g, ctrl)
                if p is None or len(cells_arr) == 0:
                    return 1e9
                return float(np.abs(cells_arr - np.array(p)).sum(1).min())
            return Discrepancy(m, lambda g: [tuple(int(x) for x in c) for c in cells_arr])
        if kind == "match":                       # MATCH two OBJECTS: make region A equal region B cell-by-cell (11.286)
            _, (r0a, c0a), (r0b, c0b), hh, ww = target_color

            def m(g):
                A = g[r0a:r0a + hh, c0a:c0a + ww]; B = g[r0b:r0b + hh, c0b:c0b + ww]
                if A.shape != B.shape or A.size == 0:
                    return 1e9
                return float((A != B).sum())

            def active(g):
                A = g[r0a:r0a + hh, c0a:c0a + ww]; B = g[r0b:r0b + hh, c0b:c0b + ww]
                out = []
                if A.shape == B.shape:
                    for (dr, dc) in np.argwhere(A != B):
                        out.append((r0a + int(dr), c0a + int(dc)))
                return out
            return Discrepancy(m, active)
        if kind == "axis":                        # SAME under MIRROR: drive movecol symmetric about a detected axis
            _, orient, p2, movecol = target_color
            bg0 = _bg(grid0)
            ys, xs = np.where(grid0 != bg0)
            r0, c0 = int(ys.min()), int(xs.min()); h = int(ys.max()) - r0 + 1; w = int(xs.max()) - c0 + 1

            def cur(g):
                s = g[r0:r0 + h, c0:c0 + w] == movecol
                return s if orient == "v" else s.T

            def m(g):
                mm = cur(g); W = mm.shape[1]; s = 0
                for c in range(W):
                    cc = p2 - c
                    if 0 <= cc < W:
                        s += int((mm[:, c] != mm[:, cc]).sum())
                return float(s)

            def active(g):
                mm = cur(g); W = mm.shape[1]; out = []
                for c in range(W):
                    cc = p2 - c
                    if 0 <= cc < W:
                        for rr in np.where(mm[:, c] != mm[:, cc])[0]:
                            out.append((r0 + int(rr), c0 + int(c)) if orient == "v" else (r0 + int(c), c0 + int(rr)))
                return out
            return Discrepancy(m, active)
        if kind == "rowmatch":                    # 1D CONFIG-MATCH: make thin band A equal band B, cell by cell.
            _, orient, ar, ac, br, bc, w = target_color   # belt/tile row vs target row; ui_planner searches command
            #                                               sequences (rotations/swaps) that minimise the mismatch.
            def _band(g, r, c):
                return g[r, c:c + w] if orient == "h" else g[r:r + w, c]

            def m(g):
                return float((_band(g, ar, ac) != _band(g, br, bc)).sum())

            def active(g):
                a = _band(g, ar, ac); b = _band(g, br, bc); out = []
                for k in range(w):
                    if a[k] != b[k]:
                        out.append((ar, ac + k) if orient == "h" else (ar + k, ac))
                return out
            return Discrepancy(m, active)
        if kind == "order":                       # SEQUENCE/ORDER: arrange sized bars into DESCENDING order by an
            _, slot_cols, rbot, color = target_color   # intrinsic key (bar height). measure = INVERSION count (a
            slot_cols = list(slot_cols)                # smooth gradient); ui_planner searches swap commands.

            def _heights(g):
                return [int((g[:, c] == color).sum()) for c in slot_cols]

            def m(g):
                hs = _heights(g); n = len(hs); inv = 0
                for i in range(n):
                    for j in range(i + 1, n):
                        if hs[i] < hs[j]:          # out of DESCENDING order
                            inv += 1
                return float(inv)

            def active(g):
                hs = _heights(g); tgt = sorted(hs, reverse=True); out = []
                for i, c in enumerate(slot_cols):
                    if hs[i] != tgt[i]:            # this slot's bar is out of place
                        for rr in range(rbot - hs[i] + 1, rbot + 1):
                            out.append((rr, c))
                return out
            return Discrepancy(m, active)

    if relation in ("BE_AT", "TOUCH"):
        tcells = np.argwhere(grid0 == target_color)

        def m(g):
            p = _centroid(g, ctrl)
            if p is None or len(tcells) == 0:
                return 1e9
            return float(np.abs(tcells - np.array(p)).sum(1).min())   # nearest target cell
        return Discrepancy(m, lambda g: [tuple(int(x) for x in c) for c in tcells])
    if relation == "NONE.EXIST":
        return Discrepancy(lambda g: float((g == target_color).sum()),
                           lambda g: cells(g == target_color))         # the items to consume
    if relation == "COVER":
        return Discrepancy(lambda g: float((g == target_color).sum()),
                           lambda g: cells(g == target_color))         # the holes to fill
    if relation in ("SAME", "BECOME"):
        bg = _bg(grid0)
        lab, n = label(grid0 == target_color)
        boxes = [(int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max()))
                 for ys, xs in (np.where(lab == i) for i in range(1, n + 1))]
        from collections import Counter as _C
        shp = _C((r1 - r0, c1 - c0) for r0, r1, c0, c1 in boxes)
        regions = []
        if boxes and shp:
            modal = shp.most_common(1)[0][0]
            regions = [b for b in boxes if (b[1] - b[0], b[3] - b[2]) == modal]
        if len(regions) >= 2:
            # FAITHFUL config-match: make every same-shaped region equal the TEMPLATE (the fullest
            # region), cell by cell. Dense and monotonic -- each corrected cell drops the discrepancy
            # by one -- and the mismatched cells ARE the located-action targets.
            h, w = modal[0] + 1, modal[1] + 1
            regs = [(r0, c0) for (r0, r1, c0, c1) in regions]

            def _stacks(g):
                return np.stack([g[r0:r0 + h, c0:c0 + w] for (r0, c0) in regs])

            def _tmpl(st):
                return int(np.argmax([(reg != bg).sum() for reg in st]))   # fullest region = template

            def m(g):
                st = _stacks(g); ti = _tmpl(st); t = st[ti]
                return float(sum((st[r] != t).sum() for r in range(len(st)) if r != ti))

            def active(g):
                st = _stacks(g); ti = _tmpl(st); t = st[ti]; out = []
                for r, (r0, c0) in enumerate(regs):
                    if r == ti:
                        continue
                    for (dr, dc) in np.argwhere(st[r] != t):
                        out.append((r0 + int(dr), c0 + int(dc)))
                return out
            return Discrepancy(m, active)
        # fallback: footprint coincidence (a movable shape to register onto a target)
        tgt = _footprint(grid0, target_color)
        return Discrepancy(lambda g: float((_footprint(g, ctrl) ^ tgt).sum()),
                           lambda g: cells(_footprint(g, ctrl) ^ tgt))
    return Discrepancy(lambda g: 0.0, lambda g: [])


class _TipOverlapDisc:
    """ASSEMBLY discrepancy, TWO-CLAUSE (the real win): (1) the controllable's tips must COINCIDE with the target's
    tips [tip distance -> 0], AND (2) the two BODIES must NOT overlap [hard penalty on any body-cell coincidence].
    The valid zero exists only in the INTERLOCK orientation -- tips meet while the bodies stay on opposite sides --
    so this objective has a reachable 0 that pure translation cannot reach (translation drives bodies together;
    only the right rotation interlocks). The stationary target's tips + body are recorded once, at init."""

    _PEN = 50.0

    def __init__(self, ctrl, co_moving, g0):
        self.ctrl = int(ctrl) if ctrl is not None else None
        self.co = set(int(c) for c in (co_moving or ()))
        g0 = np.asarray(g0)
        own = set(self._own_component(g0))
        bg = int(np.bincount(g0.ravel()).argmax())
        self.target_tips = [(int(r), int(c)) for (r, c) in np.argwhere(g0 == self.ctrl) if (int(r), int(c)) not in own]
        self.target_body = set((int(r), int(c)) for (r, c) in np.argwhere((g0 != bg) & (g0 != self.ctrl))
                               if (int(r), int(c)) not in own)
        self.target_clusters = self._cluster_centroids(self.target_tips)   # the target's distinct tip clusters

    @staticmethod
    def _clusters(cells):
        from collections import deque
        cs = set(cells); seen = set(); out = []
        for c in cells:
            if c in seen:
                continue
            comp = []; q = deque([c]); seen.add(c)
            while q:
                p = q.popleft(); comp.append(p)
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        n = (p[0] + dr, p[1] + dc)
                        if n in cs and n not in seen:
                            seen.add(n); q.append(n)
            out.append(comp)
        return out

    def _cluster_centroids(self, cells):
        return [(sum(p[0] for p in cl) / len(cl), sum(p[1] for p in cl) / len(cl)) for cl in self._clusters(cells)]

    def _own_component(self, g):
        from collections import deque
        g = np.asarray(g); bg = int(np.bincount(g.ravel()).argmax()); H, W = g.shape
        if self.co:
            seeds = [tuple(s) for s in np.argwhere(np.isin(g, list(self.co)))]
        else:
            seeds = [tuple(s) for s in np.argwhere(g == self.ctrl)]
        if not seeds:
            return []
        seen = set(seeds); q = deque(seeds); comp = []
        while q:
            r, c = q.popleft(); comp.append((int(r), int(c)))
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W and g[rr, cc] != bg and (rr, cc) not in seen:
                    seen.add((rr, cc)); q.append((rr, cc))
        return comp

    def _own(self, g):
        g = np.asarray(g); comp = self._own_component(g)
        own_tips = [(r, c) for (r, c) in comp if int(g[r, c]) == self.ctrl]
        own_body = [(r, c) for (r, c) in comp if int(g[r, c]) != self.ctrl]
        return own_tips, own_body

    def measure(self, g):
        own_tips, own_body = self._own(g)
        if not own_tips or not self.target_clusters:
            return 1e9
        own_cl = self._cluster_centroids(own_tips)
        tgt_cl = self.target_clusters
        # BOTH pairs must connect: bipartite match own tip-clusters to target tip-clusters, SUM the matched distances
        # (the minimum over pairings). A single connected pair no longer satisfies it -- every pair must be aligned.
        import itertools
        k = min(len(own_cl), len(tgt_cl))
        best = 1e9
        for perm in itertools.permutations(range(len(tgt_cl)), k):
            tot = sum(abs(own_cl[i][0] - tgt_cl[perm[i]][0]) + abs(own_cl[i][1] - tgt_cl[perm[i]][1]) for i in range(k))
            best = min(best, tot)
        best += 6.0 * abs(len(own_cl) - len(tgt_cl))           # penalise a mismatched number of tip clusters
        body_ov = len(set(own_body) & self.target_body)        # clause 2: bodies must be disjoint
        return float(best + self._PEN * body_ov)

    def active(self, g):
        return self.target_tips


def _compile_tip_overlap(ctrl, co_moving, g0):
    return _TipOverlapDisc(ctrl, co_moving, g0)


def compile_objective(spec, ctrl, grid0):
    """Recursively compile a (possibly COMPOSITE) objective into a Discrepancy. Composition lives in
    the OBJECTIVE, not the engine: every operator returns a Discrepancy whose scalar the existing
    relation-agnostic engine minimises unchanged -- no per-game code, no engine change. (11.284)
      atomic:  (relation, target_color)            -- delegates to compile_discrepancy
      AND:     ("AND", a, b)        m = m_a + m_b                       (both must hold)
      THEN:    ("THEN", a, b)       m = m_a*K + m_b  (lexicographic: a before b; act on unmet phase)
      COUNT:   ("COUNT", tc, n, op) m = hinge(count(tc) vs n), op in {'>=','<=','=='}  (thresholds; >0-only counting)
      ALL:     ("ALL", rel, tc)     FORALL components of tc: satisfy rel over each, sequenced (THEN-chain)."""
    op = spec[0] if (isinstance(spec, tuple) and spec and isinstance(spec[0], str)
                     and spec[0] in ("AND", "THEN", "COUNT", "ALL")) else None
    if op == "AND":
        d1 = compile_objective(spec[1], ctrl, grid0); d2 = compile_objective(spec[2], ctrl, grid0)
        return Discrepancy(lambda g: d1.measure(g) + d2.measure(g),
                           lambda g: list(d1.active(g)) + list(d2.active(g)))
    if op == "THEN":
        d1 = compile_objective(spec[1], ctrl, grid0); d2 = compile_objective(spec[2], ctrl, grid0)
        K = 1e3
        return Discrepancy(lambda g: d1.measure(g) * K + d2.measure(g),
                           lambda g: (list(d1.active(g)) if d1.measure(g) > 0 else list(d2.active(g))))
    if op == "COUNT":
        _, tc, n, cop = spec
        def m(g):
            c = float((np.asarray(g) == tc).sum())
            if cop == ">=":
                return max(0.0, n - c)
            if cop == "<=":
                return max(0.0, c - n)
            return abs(c - n)
        return Discrepancy(m, lambda g: [tuple(int(x) for x in cc) for cc in np.argwhere(np.asarray(g) == tc)])
    if op == "ALL":
        _, rel, tc = spec
        lab, ncomp = label(np.asarray(grid0) == tc)
        comps = []
        for i in range(1, ncomp + 1):
            ys, xs = np.where(lab == i)
            comps.append((int(round(ys.mean())), int(round(xs.mean()))))
        if not comps:
            return Discrepancy(lambda g: 0.0, lambda g: [])
        node = (rel, ("cell", comps[0][0], comps[0][1]))
        for (r, c) in comps[1:]:
            node = ("THEN", node, (rel, ("cell", r, c)))
        return compile_objective(node, ctrl, grid0)
    relation, tc = spec
    return compile_discrepancy(relation, ctrl, tc, grid0)


def pursue(adapter, disc, budget=3000, max_clicks=8, adaptive=True, budget_max=None, max_resets=None):
    """ONE general goal-directed pursuit: best-first Go-Explore over ambient-masked states, minimising
    disc.measure, backtracking via free resets. The action set at a state is the discrete (nullary)
    actions PLUS located clicks at disc.active(state) when the adapter offers located actions -- so the
    same engine handles move games and click games. Validates on reward.
    ADAPTIVE BUDGET (11.284): `budget` is a FLOOR, not a cap -- a candidate still reducing its discrepancy
    near the floor is EXTENDED toward budget_max (allocate compute to progress), while a plateaued one is
    cut at the floor (free compute for the next candidate). This is the fix for the 'gives up early'
    symptom: a promising composite no longer dies at a fixed cap before it pays out."""
    g = adapter.reset()
    region = _hud_region(g)
    s0 = _abstract(g, region)
    nullary = list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions())
    located = list(adapter.pointer_actions()) if hasattr(adapter, "pointer_actions") else []
    paths = {s0: []}
    score = {s0: disc.measure(g)}
    grids = {s0: g}
    tried = {}
    total = 0
    total_resets = [1]                                             # count the initial reset above; cap the rest
    init = score[s0]
    best = init; best_actions = []
    eff = budget                                                   # current effective budget (grows with progress)
    budget_max = budget_max if budget_max is not None else budget * 4
    last_improve = 0                                               # action count at last discrepancy improvement

    def actions_at(state):
        acts = list(nullary)
        if located:
            for (r, c) in disc.active(grids[state])[:max_clicks]:
                for kind in located:
                    acts.append((kind, r, c))
        return acts

    while total < eff:
        frontier = [s for s in paths if len(tried.get(s, set())) < len(actions_at(s))]
        if not frontier:
            break
        s = min(frontier, key=lambda s: score[s])                  # best-first on discrepancy
        a = [x for x in actions_at(s) if x not in tried.get(s, set())][0]
        tried.setdefault(s, set()).add(a)
        if max_resets is not None and total_resets[0] >= max_resets:
            # ONLINE reset-budget spent: Go-Explore returns to states by reset+replay, which is free offline
            # but a network RESET online. Stop the reset-and-replay storm; report the best reached so far.
            return dict(validated=False, reason="reset-budget-exhausted",
                        best_discrepancy=round(float(best), 1), explored=total, states=len(paths),
                        best_actions=best_actions)
        adapter.reset(); total_resets[0] += 1
        ok = True
        for pa in paths[s]:
            _, _, d, _ = _apply(adapter, pa); total += 1
            if d:
                ok = False; break
        if not ok:
            continue
        bl = getattr(adapter._obs, "levels_completed", 0) or 0
        g, _, d, _ = _apply(adapter, a); total += 1
        rew = (getattr(adapter._obs, "levels_completed", 0) or 0) > bl or adapter.satisfied()
        h = disc.measure(g)
        if h < best:
            best = h; last_improve = total; best_actions = list(paths[s]) + [a]   # remember route to best
        if rew:
            return dict(validated=True, predicate_confirmed=bool(h <= 0),
                        executed=len(paths[s]) + 1, mapping_cost=total, final_discrepancy=h,
                        actions=list(paths[s]) + [a])
        if h <= 0:                                                  # ABORT 1: predicate met, no reward -> wrong binding
            return dict(validated=False, reason="predicate-satisfied-no-reward",
                        explored=total, states=len(paths), best_actions=best_actions)
        ns = _abstract(g, region)
        if ns not in paths or h < score.get(ns, 1e18):
            paths[ns] = paths[s] + [a]; score[ns] = h; grids[ns] = g
        if d:
            continue
        if len(paths) >= 30 and best >= 0.85 * init and init > 0:   # ABORT 2: discrepancy won't reduce
            return dict(validated=False, reason="discrepancy-not-reducible",
                        best_discrepancy=round(float(best), 1), explored=total, states=len(paths),
                        best_actions=best_actions)
        if adaptive and total >= eff - 1 and eff < budget_max and (total - last_improve) < max(80, budget // 3):
            eff = min(budget_max, eff + budget)                     # still improving at the floor -> extend
    return dict(validated=False, reason="reward-unreached", best_discrepancy=round(float(best), 1),
                explored=total, states=len(paths), eff_budget=eff, best_actions=best_actions)


def _explore_actions(adapter, g0, sample=16):
    """INTERACTION action set: nullary actions + located clicks at object-component centroids."""
    import random as _r
    bg = _bg(g0)
    nullary = list(adapter.discrete_actions()) if hasattr(adapter, "discrete_actions") else list(adapter.actions())
    clicks = []
    if hasattr(adapter, "pointer_actions") and adapter.pointer_actions():
        for c in np.unique(g0):
            if c == bg:
                continue
            lab, n = label(g0 == c)
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                clicks.append(("click", int(ys.mean()), int(xs.mean())))
        _r.shuffle(clicks); clicks = clicks[:sample]
    return nullary + clicks


def interaction_probe(adapter, budget=1200, max_path=22, seed=0, max_resets=None):
    """INTERACTION target source (§11.259/§11.261-262): when the COMPOSER cannot perceive a target,
    DISCOVER reward by a Go-Explore under free resets (line 320). Gradient chosen by the RECOVERY
    EXPERIMENT (§11.262), not by preference: NOVELTY (least-visited expansion) ranked best -- empowerment
    and reachability did not beat it. Per-state action EXHAUSTION (each state expanded at most once per
    action) is what made it recover spatial objectives (tu93, lp85). Recovers EXPLORATION-REACHABLE
    objectives (spatial / navigation / collect); does NOT recover SPECIFIC-TERMINAL-CONFIG ones (e.g. erase
    a colour to zero) -- those need the directed composer-target. Reward-gated."""
    import random as _r
    _r.seed(seed)
    g0 = adapter.reset(); region = _hud_region(g0)
    acts = _explore_actions(adapter, g0); nA = len(acts)
    if nA == 0:
        return dict(reached=False, reason="no-actions")
    s0 = _abstract(g0, region)
    A = {s0: dict(path=[], visits=0, tried=set())}; steps = 0; _resets = 1
    while steps < budget:
        cand = [s for s in A if len(A[s]["tried"]) < nA and len(A[s]["path"]) <= max_path]
        if not cand:
            break
        s = min(cand, key=lambda k: A[k]["visits"])                       # NOVELTY: least-visited
        A[s]["visits"] += 1; path = A[s]["path"]
        if max_resets is not None and _resets >= max_resets:              # ONLINE: stop the reset+replay storm
            return dict(reached=False, explored=steps, states=len(A), gradient="novelty",
                        reason="reset-budget-exhausted")
        adapter.reset(); _resets += 1; ok = True
        for a in path:                                                    # free-reset replay to frontier
            _, r, d, _ = _apply(adapter, a)
            if r and r > 0:
                return dict(reached=True, executed=len(path), explored=steps, gradient="novelty")
            if d:
                ok = False; break
        if not ok:
            A[s]["tried"] = set(range(nA)); continue                      # dead path -> exhaust
        untried = [i for i in range(nA) if i not in A[s]["tried"]]
        ai = _r.choice(untried); A[s]["tried"].add(ai); a = acts[ai]
        g, r, d, _ = _apply(adapter, a); steps += 1
        if (r and r > 0) or adapter.satisfied():
            return dict(reached=True, executed=len(path) + 1, explored=steps, gradient="novelty")
        ns = _abstract(g, region)
        if ns not in A and not d:
            A[ns] = dict(path=path + [a], visits=0, tried=set())
    return dict(reached=False, explored=steps, states=len(A), gradient="novelty")


def _astar_actions(start, goal, dirs, blocked_edges, bounds, max_nodes=6000):
    """A* over a LEARNED passability graph -- the general navigation primitive (greedy distance-descent is
    its degenerate, empty-blocked_edges case). Nodes are integer cells; edges are the learned action
    displacements `dirs` (action -> (dr,dc)) minus `blocked_edges` ((cell,action) known not to move the
    mover). Unknown transitions are optimistically passable; surprises are caught by replanning. Returns the
    ACTION list start->goal, or None. No game identity -- it plans over whatever map was learned at runtime,
    so it transfers across the whole navigation family (O(1)), not per-game (that would be a library)."""
    import heapq
    H, W = bounds
    start = (int(round(start[0])), int(round(start[1])))
    goal = (int(round(goal[0])), int(round(goal[1])))
    if start == goal:
        return []
    def hh(p):
        return abs(p[0] - goal[0]) + abs(p[1] - goal[1])
    openq = [(hh(start), 0, start)]; came = {start: None}; gsc = {start: 0}; seen = 0
    while openq and seen < max_nodes:
        _, gc, cell = heapq.heappop(openq); seen += 1
        if cell == goal:
            acts = []; cur = cell
            while came[cur] is not None:
                pcell, pa = came[cur]; acts.append(pa); cur = pcell
            return list(reversed(acts))
        for a, (dr, dc) in dirs.items():
            if (cell, a) in blocked_edges:
                continue
            nd = (cell[0] + int(dr), cell[1] + int(dc))
            if not (0 <= nd[0] < H and 0 <= nd[1] < W) or nd == cell:
                continue
            ng = gc + 1
            if ng < gsc.get(nd, 1e18):
                gsc[nd] = ng; came[nd] = (cell, a)
                heapq.heappush(openq, (ng + hh(nd), ng, nd))
    return None


# ============================================================================================================
# GENERALIZED TRAVERSAL -- ONE best-first primitive; the whole family is this function under a different
# (goal-type, priority) pair. BFS, A*, Dijkstra, greedy, novelty/frontier exploration, and predicate search
# are NOT separate algorithms to switch between -- they are this primitive with two knobs turned:
#
#   AXIS 1  GOAL TYPE   is the goal a PLACE (a known node) or a PREDICATE (any state where P holds)?
#   AXIS 2  PRIORITY    what ranks the frontier? -- a small CATEGORICAL set, each fitting a situation:
#
#     "distance"   h = metric-to-a-known-place        PLACE  · model trusted · metric space      (= A*/greedy)
#     "cost"       g = sum of per-step costs           PLACE  · WEIGHTED terrain (budget tiles)    (= Dijkstra)
#     "novelty"    -visits / +info-gain of the node    goal UNKNOWN -> head to the FRONTIER         (= explore)
#     "predicate"  h = discrepancy of STATE to P       PREDICATE over a JOINT state (pos x phase)   (= match+nav)
#
# The proctor does NOT pick which; the AGENT reads the situation and selects (goal-type, priority) itself --
# is the goal a place I can name, or a property? is terrain weighted? is the goal location unknown? -- the same
# "the situation picks the gear" move as walk-vs-run, one rung up. Nodes are OPAQUE states, so the same code
# plans over a position grid, an abstract game-state, or the PRODUCT space (avatar-cell x key-phase) where
# "cycle the key AND walk to the door" is a SINGLE search instead of two. That product-space view is why the
# match-and-navigate conjunction stops being a conjugate the egocentric loop keeps flattening.
def _best_first(start, neighbors, is_goal, priority, max_nodes=20000):
    """start: opaque hashable state. neighbors(state) -> iterable of (action, next_state, step_cost>=0).
    is_goal(state) -> bool (a PLACE goal is just `state == target`; a PREDICATE goal is any test). priority(
    state, g_cost) -> float, lower = expanded first (distance: h(state); cost: g_cost; novelty: -info(state);
    predicate: discrepancy(state)). Returns the ACTION list start->goal, or None. Pure planning -- no resets,
    no acting; the caller drives the returned plan through the walk/run follower."""
    import heapq
    came = {start: None}; gsc = {start: 0.0}
    _tie = [0]; openq = [(priority(start, 0.0), 0.0, 0, start)]; seen = 0
    while openq and seen < max_nodes:
        _, gc, _, st = heapq.heappop(openq); seen += 1
        if is_goal(st):
            acts = []; cur = st
            while came[cur] is not None:
                pst, pa = came[cur]; acts.append(pa); cur = pst
            return list(reversed(acts))
        for (a, nst, sc) in neighbors(st):
            ng = gc + float(sc)
            if ng < gsc.get(nst, 1e18):
                gsc[nst] = ng; came[nst] = (st, a)
                _tie[0] += 1
                heapq.heappush(openq, (priority(nst, ng), ng, _tie[0], nst))
    return None


# The categorical PRIORITY set as a taxonomy the agent reads. Each returns a `priority(state, g)` closure for
# _best_first, given the situation's parameters. Named so the selection is whitebox in the log.
def _priority_distance(goal_cell, h=lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])):
    """PLACE goal, metric space, model trusted. Greedy is the h-only degenerate case; A* adds g."""
    return lambda st, g: g + h(st if not isinstance(st, tuple) or len(st) < 2 else st[:2], goal_cell)


def _priority_cost():
    """PLACE goal, WEIGHTED terrain. Rank by cost-so-far only (Dijkstra) -- correct when steps cost unequally
    (a budget-draining tile is 'far' even if spatially near); a distance heuristic would distort that."""
    return lambda st, g: g


def _priority_novelty(info):
    """goal UNKNOWN. Head to the least-known reachable node -- info(state) high = worth visiting (least-visited,
    or highest model-uncertainty / expected information gain). This is the frontier/curiosity compass: 'go where
    I will learn the rule I am missing', not 'go toward the exit' (there is no known exit)."""
    return lambda st, g: g - 3.0 * float(info(st))


def _priority_predicate(discrepancy):
    """PREDICATE goal over any state (incl. the JOINT pos x phase). Rank by how far the STATE is from satisfying
    P -- e.g. |phase - target| + metric-to-exit -- so the search drives the whole state to the goal condition,
    cycling and walking in one plan."""
    return lambda st, g: g + float(discrepancy(st))


def _ctrl_component(g, ctrl, co=None):
    """The CONTROLLABLE piece: the non-bg connected component of the controllable's OWN cells. Seeds from the
    CO-MOVING BODY colours when known -- those are on the controllable ONLY -- so flood-fill isolates it. Seeding
    from the marker/tip colour alone grabs BOTH pieces when tips are shared (cn04): the co-moving seed is the fix."""
    from collections import deque
    g = np.asarray(g); bg = int(np.bincount(g.ravel()).argmax()); H, W = g.shape
    co = set(int(c) for c in (co or ()))
    seeds = [tuple(s) for s in np.argwhere(np.isin(g, list(co)))] if co else []
    if not seeds:
        seeds = [tuple(s) for s in np.argwhere(g == ctrl)]     # fallback: no co-moving body known
    if not seeds:
        return []
    seen = set(seeds); q = deque(seeds); comp = []
    while q:
        r, c = q.popleft(); comp.append((r, c))
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and g[rr, cc] != bg and (rr, cc) not in seen:
                seen.add((rr, cc)); q.append((rr, cc))
    return comp


def _model_apply(g, action, amap, rotate_actions, ctrl, co=None, rotate_model=None):
    """Focused forward model: apply the CONTROLLABLE's learned transformation to its ISOLATED component (seeded from
    the co-moving body) and render. Rotation uses the LEARNED rigid transform (direction + translation, measured from
    real frames) when available -- the bbox rotation was catastrophically wrong. Movement is FREE (overlap allowed);
    the 'bodies must not overlap' clause is a discrepancy PENALTY, so the planner can pass through overlap to the
    interlock instead of stalling at contact."""
    g = np.asarray(g); bg = int(np.bincount(g.ravel()).argmax()); H, W = g.shape
    comp = _ctrl_component(g, ctrl, co)
    if not comp:
        return g
    vals = {(r, c): int(g[r, c]) for (r, c) in comp}
    out = g.copy()
    for (r, c) in comp:
        out[r, c] = bg
    if str(action) in (rotate_actions or ()):
        rm = (rotate_model or {}).get(str(action))
        if rm:                                                 # LEARNED rigid rotate: R (CW/CCW) + translation
            _dir, t = rm; R = (lambda r, c: (c, -r)) if _dir == "CW" else (lambda r, c: (-c, r))
            for (r, c) in comp:
                Rr, Rc = R(r, c); rr, cc = int(round(Rr + t[0])), int(round(Rc + t[1]))
                if 0 <= rr < H and 0 <= cc < W:
                    out[rr, cc] = vals[(r, c)]
        else:                                                  # fallback: 90 CW about the piece centre
            ys = [p[0] for p in comp]; xs = [p[1] for p in comp]
            cy = (min(ys) + max(ys)) / 2.0; cx = (min(xs) + max(xs)) / 2.0
            for (r, c) in comp:
                rr, cc = int(round(cy + (c - cx))), int(round(cx - (r - cy)))
                if 0 <= rr < H and 0 <= cc < W:
                    out[rr, cc] = vals[(r, c)]
    elif action in (amap or {}):
        dr, dc = amap[action]; dr, dc = int(round(dr)), int(round(dc))
        for (r, c) in comp:
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W:
                out[rr, cc] = vals[(r, c)]
    else:
        return g
    return out


def _plan_via_model(g0, disc, actions, amap, rotate_actions, ctrl, depth=12, beam=8, co=None, rotate_model=None):
    """PLAN an action sequence that minimises disc by simulating ONLY the controllable's learned transformation
    (high-fidelity focused model), via beam search. Returns (best_sequence, predicted_best_discrepancy). Spends no
    real actions. This is the 'mental sandbox' -- plan through the dynamics we actually know, then execute."""
    h0 = float(disc.measure(g0))
    beams = [(h0, np.asarray(g0), [])]
    best_seq, best_h = [], h0
    seen = {np.asarray(g0).tobytes()}
    for _ in range(depth):
        cand = []
        for (h, g, seq) in beams:
            for a in actions:
                try:
                    ng = _model_apply(g, a, amap, rotate_actions, ctrl, co, rotate_model)
                except Exception:
                    continue
                key = ng.tobytes()
                if key in seen:
                    continue
                seen.add(key)
                nh = float(disc.measure(ng))
                cand.append((nh, ng, seq + [a]))
                if nh < best_h - 1e-9:
                    best_h, best_seq = nh, seq + [a]
        if not cand:
            break
        cand.sort(key=lambda t: t[0])
        beams = cand[:beam]
        if best_h <= 0:
            break
    return best_seq, best_h


def _seg_pieces(g0, ctrl):
    """Segment the board into PIECES (connected non-bg components). Each: {cells:{(r,c):colour}, tips:set, body:set,
    cen:(r,c)}. Tips = the connector colour; body = the rest. This is the state the selection planner moves."""
    try:
        from object_seg import segment_objects
    except Exception:
        return []
    g0 = np.asarray(g0); bg = int(np.bincount(g0.ravel()).argmax())
    pieces = []
    for o in segment_objects(g0, bg=bg):
        cells = {(int(r), int(c)): int(g0[r, c]) for (r, c) in o["cells"]}
        if len(cells) < 3:
            continue
        tips = set(k for k, v in cells.items() if v == ctrl)
        if not tips:
            continue                                          # only CONNECTOR pieces (with tips) are assembly pieces
        body = set(cells.keys()) - tips
        rs = [k[0] for k in cells]; cs = [k[1] for k in cells]
        pieces.append({"cells": cells, "tips": tips, "body": body,
                       "cen": (int(round(sum(rs) / len(rs))), int(round(sum(cs) / len(cs))))})
    return pieces


def _xform_piece(piece, action, amap, rotate_actions, ctrl):
    """Transform one piece's cells (rotate 90 for a rotate action, else translate by the learned vector)."""
    cells = piece["cells"]
    if str(action) in (rotate_actions or ()):
        # EXACT 90 CW: (r,c)->(c,-r) is bijective integer -- never scatters/collides cells (float-centre rounding
        # degraded the piece over repeated rotations). Re-anchor to the original centroid so it rotates in place.
        rot = [((c, -r), v) for ((r, c), v) in cells.items()]
        ocr = sum(k[0] for k in cells) / len(cells); occ = sum(k[1] for k in cells) / len(cells)
        ncr = sum(p[0][0] for p in rot) / len(rot); ncc = sum(p[0][1] for p in rot) / len(rot)
        dr = int(round(ocr - ncr)); dc = int(round(occ - ncc))
        nc = {(r + dr, c + dc): v for ((r, c), v) in rot}
    elif action in (amap or {}):
        dr, dc = amap[action]; dr, dc = int(round(dr)), int(round(dc))
        nc = {(r + dr, c + dc): v for (r, c), v in cells.items()}
    else:
        return piece
    tips = set(k for k, v in nc.items() if v == ctrl); body = set(nc.keys()) - tips
    rs = [k[0] for k in nc]; cs = [k[1] for k in nc]
    return {"cells": nc, "tips": tips, "body": body,
            "cen": (int(round(sum(rs) / len(rs))), int(round(sum(cs) / len(cs))))}


def _match_pairs(clusters):
    """Scale-free min-weight matching of tip clusters into CROSS-PIECE pairs. Greedy over sorted cross-piece edges:
    polynomial, and with NO arity cap anywhere -- the identical code path runs at N=2 and at N=10000. Returns
    (pairs, total_distance); pairs is a list of (i,j) cluster-index pairs, each spanning two different pieces."""
    n = len(clusters)
    if n < 2:
        return [], 1e9
    edges = []
    for a in range(n):
        pa, ca = clusters[a]
        for b in range(a + 1, n):
            pb, cb = clusters[b]
            if pa != pb:
                edges.append((abs(ca[0] - cb[0]) + abs(ca[1] - cb[1]), a, b))
    edges.sort()
    used = set(); pairs = []; tot = 0.0
    for d, a, b in edges:
        if a in used or b in used:
            continue
        used.add(a); used.add(b); pairs.append((a, b)); tot += d
    if len(used) < n:                                          # an unpaired tip cannot be satisfied
        tot += 1e6 * (n - len(used))
    return pairs, tot


def _match_clusters(clusters):
    return _match_pairs(clusters)[1]


def _sel_obj(pieces):
    """N-PIECE assembly objective: EVERY tip cluster must be PAIRED (perfect matching) with a tip cluster on a
    DIFFERENT piece and coincide with it, AND no two pieces' BODIES may overlap. 0 = all pairs interlocked, bodies
    clear = the win. General over any number of pieces; the 2-piece both-pairs case is the special case."""
    clusters = []
    for i, p in enumerate(pieces):
        for cl in _TipOverlapDisc._clusters(list(p["tips"])):
            cen = (sum(x[0] for x in cl) / len(cl), sum(x[1] for x in cl) / len(cl))
            clusters.append((i, cen))
    tip_cost = _match_clusters(clusters)                       # perfect matching -> ALL pairs must connect
    if tip_cost >= 1e9:
        return 1e9
    body_ov = 0
    for i in range(len(pieces)):
        for j in range(i + 1, len(pieces)):
            body_ov += len(pieces[i]["body"] & pieces[j]["body"])                   # bodies must be disjoint
    return float(tip_cost + 50.0 * body_ov)


def _plan_selection(g0, ctrl, nullary, amap, rotate_actions, located, depth=16, beam=12):
    """Plan over (SELECT, TRANSFORM) across ALL pieces: a click SELECTS which piece the move/rotate actions affect;
    transforms move/rotate the selected piece. Beam search minimising the N-piece objective. Returns a sequence of
    REAL actions (clicks to select + nullary transforms). This is the machine-composing path -- move whichever
    pieces it takes to interlock all tip-pairs -- with selection as first-class state."""
    pieces0 = _seg_pieces(g0, ctrl)
    if len(pieces0) < 2 or not located:
        return []
    clickA = located[0]
    beams = [(_sel_obj(pieces0), pieces0, None, [])]           # (cost, pieces, selected_idx, real_action_plan)
    best_cost, best_plan = beams[0][0], []
    for _ in range(depth):
        cand = []
        for (cost, pieces, sel, plan) in beams:
            for i, p in enumerate(pieces):                     # SELECT piece i (click its current centroid)
                if i == sel:
                    continue
                cand.append((cost, pieces, i, plan + [(clickA, int(p["cen"][0]), int(p["cen"][1]))]))
            if sel is not None:                                # TRANSFORM the selected piece
                for a in nullary:
                    newp = list(pieces); newp[sel] = _xform_piece(pieces[sel], a, amap, rotate_actions, ctrl)
                    c2 = _sel_obj(newp)
                    cand.append((c2, newp, sel, plan + [a]))
                    if c2 < best_cost - 1e-9:
                        best_cost, best_plan = c2, plan + [a]
        if not cand:
            break
        cand.sort(key=lambda t: t[0])
        beams = cand[:beam]
        if best_cost <= 0:
            break
    return best_plan


def _clusters_cen(cells):
    cls = _TipOverlapDisc._clusters(list(cells))
    return [(sum(x[0] for x in cl) / len(cl), sum(x[1] for x in cl) / len(cl)) for cl in cls]


def _assign_cost(srcs, dsts):
    """Min-cost assignment of a PIECE's few tip clusters to its target centroids (small, per-piece -- the global
    matching stays scale-free). Ensures every one of the piece's tips heads to a DISTINCT target."""
    import itertools
    if not srcs or not dsts:
        return 1e9
    k = min(len(srcs), len(dsts))
    best = 1e9
    for perm in itertools.permutations(range(len(dsts)), k):
        best = min(best, sum(abs(srcs[i][0] - dsts[perm[i]][0]) + abs(srcs[i][1] - dsts[perm[i]][1])
                             for i in range(k)))
    return best + 8.0 * abs(len(srcs) - len(dsts))


def _translate_actions(DR, DC, trans):
    """Compose learned translate actions to achieve ~(DR,DC). trans: {action:(dr,dc)}. Greedy over the action set --
    each step takes the action that most reduces the remaining offset (works for any axis-aligned action basis)."""
    seq = []; rem = [float(DR), float(DC)]
    for _ in range(400):
        if abs(rem[0]) + abs(rem[1]) < 1.0:
            break
        best_a = None; best_red = 1e-9
        for a, (dr, dc) in trans.items():
            red = (abs(rem[0]) + abs(rem[1])) - (abs(rem[0] - dr) + abs(rem[1] - dc))
            if red > best_red:
                best_red = red; best_a = a
        if best_a is None:
            break
        dr, dc = trans[best_a]; rem = [rem[0] - dr, rem[1] - dc]; seq.append(best_a)
    return seq


def _pair_joint_solve(mover, anchor_cens, others_body, nullary, amap, rotate_actions, ctrl):
    """THE IRREDUCIBLE PAIRWISE-JOINT ATOM: transform `mover` so BOTH its tip clusters coincide with the anchor's tip
    clusters SIMULTANEOUSLY (the joint constraint that per-piece decomposition can't express), bodies disjoint. For
    each of the <=4 orientations, compute the EXACT translation that jointly best-aligns the matched tip pairs (the
    component-wise median of the per-tip offsets -- 0 when the arrangements match = the interlock), score it, and keep
    the best. Joint-complete AND arity-invariant: it is local to one matched pair, applied N/2 times regardless of N."""
    import itertools
    rot_acts = [a for a in nullary if str(a) in (rotate_actions or ())]
    trans = {a: amap[a] for a in nullary if a in (amap or {}) and str(a) not in (rotate_actions or ())}
    if not anchor_cens or not trans:
        return [], 1e18
    best_cost, best_seq = 1e18, []
    cur = mover; rot_prefix = []
    for _o in range(4 if rot_acts else 1):
        mover_cens = _clusters_cen(cur["tips"])
        if mover_cens:
            k = min(len(mover_cens), len(anchor_cens))
            for perm in itertools.permutations(range(len(anchor_cens)), k):
                diffs = [(anchor_cens[perm[i]][0] - mover_cens[i][0],
                          anchor_cens[perm[i]][1] - mover_cens[i][1]) for i in range(k)]
                trs = sorted(d[0] for d in diffs); tcs = sorted(d[1] for d in diffs)
                t = (trs[len(trs) // 2], tcs[len(tcs) // 2])          # joint-optimal translation (Manhattan median)
                tip_cost = sum(abs(diffs[i][0] - t[0]) + abs(diffs[i][1] - t[1]) for i in range(k))
                tip_cost += 8.0 * abs(len(mover_cens) - len(anchor_cens))
                moved_body = set((int(round(r + t[0])), int(round(c + t[1]))) for (r, c) in cur["body"])
                cost = tip_cost + 50.0 * len(moved_body & others_body)
                if cost < best_cost - 1e-9:
                    best_cost = cost
                    best_seq = list(rot_prefix) + _translate_actions(t[0], t[1], trans)
        if not rot_acts:
            break
        cur = _xform_piece(cur, rot_acts[0], amap, rotate_actions, ctrl); rot_prefix = rot_prefix + [rot_acts[0]]
    return best_seq, best_cost


def _assemble_plan(g0, ctrl, nullary, amap, rotate_actions, located, depth=16, beam=10):
    """ARITY-INVARIANT assembly: (1) global scale-free tip matching -> piece adjacency, (2) spanning tree from an
    ANCHOR piece, (3) place each remaining piece relative to its ALREADY-PLACED neighbours via the per-pair interlock
    SKILL. Placing against fixed, already-placed pieces avoids the oscillation of everything-moves-at-once and makes
    it converge. Loops over pieces with NO fixed count -- 2 pieces and N pieces are the identical code path. Returns
    a plan of REAL actions (clicks to select + nullary transforms)."""
    from collections import deque
    pieces = _seg_pieces(g0, ctrl)
    if len(pieces) < 2 or not located:
        return []
    clickA = located[0]; plan = []
    clusters = [(i, cen) for i, p in enumerate(pieces) for cen in _clusters_cen(p["tips"])]
    pairs, _tot = _match_pairs(clusters)
    adj = {i: set() for i in range(len(pieces))}
    for (a, b) in pairs:
        ia, ib = clusters[a][0], clusters[b][0]
        if ia != ib:
            adj[ia].add(ib); adj[ib].add(ia)
    anchor = max(range(len(pieces)), key=lambda i: len(pieces[i]["cells"]))   # biggest piece stays fixed
    placed = {anchor}; order = []; q = deque([anchor])
    while q:                                                    # BFS spanning tree -> placement order
        u = q.popleft()
        for v in sorted(adj[u]):
            if v not in placed:
                placed.add(v); order.append(v); q.append(v)
    done = {anchor}
    for v in order:                                            # place v by JOINT interlock against placed neighbours
        targets = []
        for nb in adj[v]:
            if nb in done:
                targets += _clusters_cen(pieces[nb]["tips"])   # current tips of already-placed neighbour(s)
        if not targets:
            targets = _clusters_cen(pieces[anchor]["tips"])
        others_body = set()
        for j, p in enumerate(pieces):
            if j != v:
                others_body |= p["body"]
        seq, _cost = _pair_joint_solve(pieces[v], targets, others_body, nullary, amap, rotate_actions, ctrl)
        if seq:
            plan.append((clickA, int(pieces[v]["cen"][0]), int(pieces[v]["cen"][1])))   # select v
            plan += seq
            for a in seq:
                pieces[v] = _xform_piece(pieces[v], a, amap, rotate_actions, ctrl)
        done.add(v)
    return plan


def _real_tip_offset(g, ctrl, co):
    """From the REAL grid: the joint translation that best aligns the CONTROLLABLE's tips onto the nearest other
    piece's tips (both pairs, median-of-offsets). Returns (dr, dc, aligned_bool). Measured from reality, not a model."""
    import itertools
    pieces = _seg_pieces(np.asarray(g), ctrl)
    if len(pieces) < 2:
        return None
    ctrl_cells = set(_ctrl_component(np.asarray(g), ctrl, co))
    mi = max(range(len(pieces)), key=lambda i: len(set(pieces[i]["cells"]) & ctrl_cells))
    mover = pieces[mi]
    others = [p for j, p in enumerate(pieces) if j != mi]
    if not others:
        return None
    tgt = min(others, key=lambda p: abs(p["cen"][0] - mover["cen"][0]) + abs(p["cen"][1] - mover["cen"][1]))
    mt = _clusters_cen(mover["tips"]); tt = _clusters_cen(tgt["tips"])
    if not mt or not tt:
        return None
    k = min(len(mt), len(tt)); best = (0.0, 0.0); bc = 1e18
    for perm in itertools.permutations(range(len(tt)), k):
        diffs = [(tt[perm[i]][0] - mt[i][0], tt[perm[i]][1] - mt[i][1]) for i in range(k)]
        trs = sorted(d[0] for d in diffs); tcs = sorted(d[1] for d in diffs)
        t = (trs[len(trs) // 2], tcs[len(tcs) // 2])
        cost = sum(abs(diffs[i][0] - t[0]) + abs(diffs[i][1] - t[1]) for i in range(k))
        if cost < bc:
            bc = cost; best = t
    return (best[0], best[1], (abs(best[0]) + abs(best[1]) <= 1.0))


def _residual_correct(adapter, disc, ctrl, co, translate_map, budget_left, cycles=5):
    """P1: CLOSED-LOOP residual correction on the REAL grid. Each cycle re-reads the true controllable-vs-target tip
    offset and applies corrective translations to close it. Robust to forward-model bias -- a wrong amap MAGNITUDE
    still converges because the offset is re-measured from reality every step. Hard no-churn guard: bounded cycles,
    break (do not reset-loop) on GAME_OVER, break on no-progress. Returns actions spent."""
    spent = 0
    base = getattr(adapter, "_lvlbase", 0)
    for _ in range(cycles):
        if adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > base:
            return spent
        g = _perceive_grid(adapter)
        off = _real_tip_offset(g, ctrl, co)
        if off is None or off[2]:
            return spent
        seq = _translate_actions(off[0], off[1], translate_map)
        if not seq:
            return spent
        b = float(disc.measure(g))
        for a in seq:
            _, rew, dn, _ = _apply(adapter, a); spent += 1
            if rew > 0 or (getattr(adapter._obs, "levels_completed", 0) or 0) > base:
                return spent
            if dn:                                              # GAME_OVER: stop, do NOT reset-and-retry (no churn)
                return spent
            if spent >= budget_left:
                return spent
        if float(disc.measure(_perceive_grid(adapter))) >= b - 0.5:
            return spent                                        # no progress -> stop
    return spent


def _probe_selection(adapter, ctrl, located, move_action, max_probes=4):
    """P3: ACTIVELY induce CLICK/selection semantics on a multi-piece board instead of assuming click-selects-the-
    piece-underneath (the assumption that broke the assembler live). For each piece: click it, apply a known move,
    observe WHICH piece actually moved -> that is what the click selected. Returns [{click, selected_centroid,
    selects_clicked}]. Bounded, no-churn (stops on GAME_OVER/level-win), frame-only."""
    if not located:
        return []
    clickA = located[0]; out = []
    base = getattr(adapter, "_lvlbase", 0)
    g = _perceive_grid(adapter)
    pieces = _seg_pieces(g, ctrl)
    for p in pieces[:max_probes]:
        cr, cc = int(p["cen"][0]), int(p["cen"][1])
        _, _, dn, _ = _apply(adapter, (clickA, cr, cc))          # click this piece
        if dn:
            adapter.reset(); break
        g1 = _perceive_grid(adapter)
        _, rew, dn, _ = _apply(adapter, move_action)             # apply a known move
        if rew > 0 or (getattr(adapter._obs, "levels_completed", 0) or 0) > base:
            break
        if dn:
            adapter.reset(); break
        g2 = _perceive_grid(adapter)
        changed = np.argwhere(g1 != g2)                          # cells that moved = the selected piece
        if len(changed):
            mr = float(changed[:, 0].mean()); mc = float(changed[:, 1].mean())
            sel_clicked = (abs(mr - cr) + abs(mc - cc)) < max(6.0, 0.5 * (abs(p["cen"][0]) + 1))
            out.append({"click": (cr, cc), "selected_centroid": (round(mr, 1), round(mc, 1)),
                        "selects_clicked": bool(sel_clicked)})
    return out


def _extract_match_objects(g, ctrl, co=None, individuation=None):
    """Extract MATCH-schema objects for the general schema planner: CONTROLLABLES (mobile pieces carrying a distinctive
    marker colour) and TARGETS (static markers of the same colours). Colour-keyed. Heuristic and FALLBACK-SAFE: returns
    ([], []) if it cannot extract cleanly, so the caller falls through to the default regimes. A marker is a controllable
    if it sits on/near a MOBILE object (from C2 individuation), else a target."""
    g = np.asarray(g); H, W = g.shape
    bg = int(np.bincount(g.ravel()).argmax())
    vals, counts = np.unique(g, return_counts=True)
    marker_colours = [int(v) for v, c in zip(vals, counts) if int(v) != bg and 2 <= int(c) <= 0.02 * H * W]
    if not marker_colours:
        return [], []
    mob = (individuation or {}).get("mobility") or []
    objs = (individuation or {}).get("objects") or []
    mobile_cells = set()
    for i, o in enumerate(objs):
        if i < len(mob) and mob[i] > 0:
            mobile_cells |= set(o)
    controllables, targets = [], []
    for mc in marker_colours:
        cells = [tuple(p) for p in np.argwhere(g == mc)]
        for cluster in _TipOverlapDisc._clusters(cells):
            cen = (sum(p[0] for p in cluster) / len(cluster), sum(p[1] for p in cluster) / len(cluster))
            near_mobile = mobile_cells and any((int(round(cen[0])) + dr, int(round(cen[1])) + dc) in mobile_cells
                                               for dr in range(-2, 3) for dc in range(-2, 3))
            if near_mobile:
                controllables.append({"colour": mc, "marker_pos": cen, "cells": set(cluster), "size": len(cluster)})
            else:
                targets.append({"colour": mc, "pos": cen})
    return controllables, targets


def _detect_bar(g0):
    """Find a horizontal TARGET BAR: a row where one non-background colour spans a large fraction of the width. This is
    the 'reach the bar' target of an ACCUMULATE (fill) level -- the fluid must rise to it. Colour-agnostic (any colour
    that forms a wide horizontal band)."""
    g = np.asarray(g0); H, W = g.shape
    bg = int(np.bincount(g.ravel()).argmax())
    best = None; best_span = 0.4 * W
    for r in range(1, H - 1):
        row = g[r]
        for col in np.unique(row):
            if int(col) == bg:
                continue
            span = int((row == col).sum())
            if span > best_span:                               # widest horizontal band wins
                best_span = span; best = (r, int(col))
    return best


def _induce_fill_objective(g0):
    """C1 PRODUCER for ACCUMULATE (fill) levels -- vc33 level 0: 'raise the fluid until it reaches the bar in the
    middle'. The discrepancy is the AIR GAP: the count of background cells directly below the bar that are not yet
    filled. Pumping raises the fill, the air below the bar shrinks, and the objective hits 0 when the fill touches the
    bar. Columns already blocked by a pillar contribute no air, so the measure tracks the fillable gap only. Returns
    None if there is no bar (not a fill level)."""
    bar = _detect_bar(g0)
    if bar is None:
        return None
    bar_row, bar_col = bar
    g = np.asarray(g0); H, W = g.shape
    bg = int(np.bincount(g.ravel()).argmax())
    cols = [c for c in range(W) if g[bar_row, c] == bar_col]   # the bar's own columns
    lo, hi = min(cols), max(cols)
    bar_bottom = bar_row                                       # the bar is several rows THICK -- skip its full extent
    while bar_bottom + 1 < H and int((g[bar_bottom + 1, lo:hi + 1] == bar_col).sum()) > 0.3 * (hi - lo + 1):
        bar_bottom += 1

    def measure(g2):
        g2 = np.asarray(g2); air = 0
        for c in range(lo, hi + 1):
            r = bar_bottom + 1
            while r < H and int(g2[r, c]) == bg:               # contiguous UNFILLED (background) below the bar
                air += 1; r += 1
        return float(air)

    def active(g):
        return []
    return Discrepancy(measure, active)


def _has_avatar(adapter, tries=6):
    """Is there a movable AVATAR (a controllable the discrete actions actually move)? Two cases, one principle:
      - NO discrete/movement actions  -> no avatar, detected for FREE (the action space has no way to move anything).
      - discrete actions EXIST         -> try a HANDFUL; if none of them changes the world (HUD counter excluded),
                                          the movement action space is inert -- an avatar-shaped space with no avatar --
                                          so there is no controllable to co-move, and exploration should switch to
                                          interaction/clicking mode instead of burning the budget hunting one.
    Breaks the moment a move DOES change something (avatar-ish), so an avatar game pays ~1 action of overhead."""
    try:
        discrete = list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions())
    except Exception:
        discrete = []
    if not discrete:
        return False                                           # free detection: empty movement action space
    base = getattr(adapter, "_lvlbase", 0)
    for a in discrete[:tries]:
        before = _perceive_grid(adapter)
        _, rew, dn, _ = _apply(adapter, a)
        after = _perceive_grid(adapter)
        if _real_diff(before, after).any():
            return True                                        # a move moved/changed something -> treat as avatar
        if rew > 0 or (getattr(adapter._obs, "levels_completed", 0) or 0) > base or dn:
            break
    return False                                               # a handful of moves, nothing co-moved -> no avatar


def _marker_type(m, g):
    """COLOUR-AGNOSTIC-ACROSS-FRAMES marker type: within a single frame, two markers of the same colour AND size are
    the same kind (the puck's dot and its target dot are rendered identically). Colour is used only as a WITHIN-frame
    relational cue (re-read every frame), never as an absolute id -- so a colour remap between frames is harmless."""
    g = np.asarray(g)
    cells = m.get("cells") or set()
    from collections import Counter
    col = Counter(int(g[p]) for p in cells).most_common(1)[0][0] if cells else -1
    sz = m.get("size", 0)
    sizeb = 0 if sz <= 4 else 1 if sz <= 10 else 2 if sz <= 20 else 3
    return (col, sizeb)


def _induce_alignment_objective(g0, interaction_probe=None):
    """C1 PRODUCER for alignment/click games. Induces the objective 'drive the MOVABLE marker onto its STATIC target'.
    Structure comes from perception (same-type small markers that should coincide); ROLE comes from the interaction
    probe's motion -- a marker sitting where clicks caused change is the movable puck, one far from all change is the
    static target. The objective then measures puck->target distance, which pumping monotonically reduces (giving the
    exploit loop a drivable gradient). Falls back to symmetric spread if motion is unavailable; None if no structure.
    Colour is a WITHIN-frame cue only (re-read each frame), so colour remaps are harmless."""
    from collections import defaultdict
    g0 = np.asarray(g0)
    markers0 = [o for o in _distinct_objects(g0) if 2 <= o["size"] <= 30]
    if len(markers0) < 2:
        return None
    groups0 = defaultdict(list)
    for m in markers0:
        groups0[_marker_type(m, g0)].append(m)
    coincide_types = [k for k, v in groups0.items() if len(v) >= 2]
    if not coincide_types:
        return None

    # ROLE ASSIGNMENT from probe motion: change centroids mark where the world reacted (the pumped column / moving puck)
    change_pts = [x["change_centroid"] for x in (interaction_probe or [])
                  if x.get("changed") and x.get("change_centroid")]

    def _near_change(cen, rad=7):
        return any(abs(cen[0] - p[0]) + abs(cen[1] - p[1]) <= rad for p in change_pts)

    # ROLE ASSIGNMENT: a type must have at least one MOVABLE member (a marker sitting where the probe caused change --
    # it responded to actions) AND at least one STATIC member (a target). Types with no movable member are two static
    # targets, NOT a puck+target -- pairing them yields an UNREDUCIBLE objective (the frames-diagnosed bug), so they
    # are rejected. The objective drives each movable marker to its NEAREST static target of the same type.
    drive = {}                                                 # type -> list of STATIC target centroids
    for k in coincide_types:
        members = groups0[k]
        movable = [m for m in members if _near_change(m["centroid"])]
        static = [m for m in members if not _near_change(m["centroid"])]
        if movable and static:
            drive[k] = [tuple(s["centroid"]) for s in static]
    if not drive:                                              # NO evidenced-movable marker -> not a drivable alignment
        return None                                            # objective; do NOT fall back to static-static spread

    def _markers(g):
        gg = np.asarray(g)
        grp = defaultdict(list)
        for m in (o for o in _distinct_objects(gg) if 2 <= o["size"] <= 30):
            grp[_marker_type(m, gg)].append(m)
        return grp

    def measure(g):                                            # each MOVABLE marker -> its nearest STATIC target
        grp = _markers(g)
        total = 0.0
        for k, statics in drive.items():
            for m in grp.get(k, []):
                if _near_change(m["centroid"]):                # this is a movable marker (the puck) -> drive it
                    total += min(abs(m["centroid"][0] - s[0]) + abs(m["centroid"][1] - s[1]) for s in statics)
        return total

    def active(g):
        return []                                              # exploit loop drives the triggers
    return Discrepancy(measure, active)


def _volume_state(g0, interaction_probe=None, fluid_colour=None):
    """RESOURCE-ACCOUNTING primitive (volume vs level-flag). Fluid is a FUNGIBLE shared resource, not independent
    per-puck flags. For each movable puck, classify SURPLUS (above its target -> that column holds too much, must DRAIN)
    vs SCARCITY (below target -> too little, must PUMP), with the signed gap. Also reports the GLOBAL BALANCE -- total
    surplus vs total scarcity -- i.e. whether there is enough fluid to cascade from over-filled columns to under-filled
    ones. This is the state vector a cascade allocator plans over (draining surplus to cover scarcity, tolerating
    temporary local violations), which a binary 'at target?' flag cannot express. Colour/orientation-agnostic.

    If `fluid_colour` is given, ALSO measures the fluid BODIES directly (the marker scan misses them): each fluid
    column's fill-top vs its target / its peers. A column filled far higher than the others is a SURPLUS reservoir --
    this is what surfaces the tall over-full column that a marker-only reading reports as '0 surplus'."""
    from collections import defaultdict
    g0 = np.asarray(g0)
    markers = [o for o in _distinct_objects(g0) if 2 <= o["size"] <= 30]
    groups = defaultdict(list)
    for m in markers:
        groups[_marker_type(m, g0)].append(m)
    change_pts = [x["change_centroid"] for x in (interaction_probe or [])
                  if x.get("changed") and x.get("change_centroid")]

    def _near(cen, rad=8):
        return any(abs(cen[0] - p[0]) + abs(cen[1] - p[1]) <= rad for p in change_pts)

    state = []
    for k, members in groups.items():
        static = [m for m in members if not _near(m["centroid"])]
        movable = [m for m in members if _near(m["centroid"])]
        if not (static and movable):
            continue
        for pk in movable:
            tgt = min(static, key=lambda s: abs(s["centroid"][1] - pk["centroid"][1]))   # target in the same column (x)
            gap = pk["centroid"][0] - tgt["centroid"][0]       # row diff: puck BELOW target (gap>0) => must RISE
            kind = "scarcity" if gap > 1 else ("surplus" if gap < -1 else "at_target")
            state.append({"puck": tuple(pk["centroid"]), "target": tuple(tgt["centroid"]), "kind": kind, "gap": gap})
    # FLUID-COLUMN accounting: measure the fluid bodies themselves (the marker scan never looks at them).
    if fluid_colour is not None:
        try:
            from scipy.ndimage import label as _lbl
            _lab, _nb = _lbl(g0 == fluid_colour, structure=np.ones((3, 3)))
            cols = []
            for i in range(1, _nb + 1):
                ys, xs = np.where(_lab == i)
                if len(ys) >= 4:
                    cols.append({"top": int(ys.min()), "xc": float(xs.mean()), "size": len(ys)})
            if cols:
                _med = float(np.median([c["top"] for c in cols]))     # typical fill-top across columns
                _tgts = [o for o in _distinct_objects(g0) if o["size"] <= 4
                         and o["colour"] != fluid_colour and not _near(o["centroid"])]
                for c in cols:
                    _t = min(_tgts, key=lambda t: abs(t["centroid"][1] - c["xc"]), default=None)
                    _by_med = c["top"] - _med                          # filled higher than peers (negative) = reservoir
                    if _by_med < -6:                                   # anomalously tall -> SURPLUS reservoir (robust)
                        kind, gap = "surplus", _by_med
                    elif _t is not None:
                        gap = c["top"] - _t["centroid"][0]             # fill vs its target row
                        kind = "scarcity" if gap > 1 else ("surplus" if gap < -1 else "at_target")
                    else:
                        kind, gap = "at_target", 0
                    _trow = _t["centroid"][0] if _t is not None else _med
                    state.append({"puck": (c["top"], int(c["xc"])), "target": (int(_trow), int(c["xc"])),
                                  "kind": kind, "gap": gap, "column": True})
        except Exception:
            pass
    tot_scarcity = sum(s["gap"] for s in state if s["kind"] == "scarcity")
    tot_surplus = -sum(s["gap"] for s in state if s["kind"] == "surplus")
    return {"cells": state, "scarcity": tot_scarcity, "surplus": tot_surplus,
            "enough_to_cascade": tot_surplus >= tot_scarcity}


def _flow_analysis(g0, fluid_colour, motion=None):
    """CORRECTED + GENERALISED fluid-routing model (no baked colours, no scale heuristic, orientation-free).
      * FLUID COLUMNS: connected components of the fluid colour, ordered along the axis perpendicular to fill.
      * FILL AXIS: from observed `motion` (dr,dc) if given, else inferred from the edge the fluid attaches to (inward).
      * BOUNDARY by FUNCTION, not size: the colour whose objects are tall/thin SEPARATORS sitting between fluid columns
        (a large decoy blob that separates nothing is ignored by construction -- this is the anti-scale-heuristic rule).
      * MARKERS: small foreign objects EMBEDDED in that functional boundary (>=30%% of their border is boundary).
      * PUCKS (per-INSTANCE): a small object ADJACENT to a fluid surface whose colour matches a marker colour; the same
        colour appearing elsewhere (e.g. a HUD instance not touching fluid) is NOT a puck. Base = the puck edge nearest
        the fluid source along the axis.
      * BUTTON EDGES: small objects on the FLOOR (opposite the fill axis), assigned to their nearest column; a button on
        the column's RIGHT pulls from the RIGHT neighbour into this column, LEFT pulls from the LEFT neighbour -> a
        directed transfer edge (donor_neighbour -> receiver_column). Conserved flow on a line graph.
    Additive + legible; symbolic over perceived objects, no grid rescale. Buttons' donor direction is geometry-derived
    here and meant to be confirmed/overridden by observed motion."""
    import regime_factory as _RF
    g0 = np.asarray(g0); H = int(g0.shape[0]); Wd = int(g0.shape[1])
    try:
        from scipy.ndimage import label as _lbl
        bg = int(np.bincount(g0.ravel()).argmax())
        objs = _distinct_objects(g0)
        lab, nb = _lbl(g0 == fluid_colour, structure=np.ones((3, 3)))
        fcols = []
        for i in range(1, nb + 1):
            ys, xs = np.where(lab == i)
            if len(ys) >= 3:
                fcols.append({"xc": int(round(float(xs.mean()))), "top": int(ys.min()), "bot": int(ys.max())})
        if not fcols:
            return None
        fcols.sort(key=lambda c: c["xc"])
        colx = [c["xc"] for c in fcols]
        fys, fxs = np.where(g0 == fluid_colour)
        fluidset = set(zip([int(y) for y in fys], [int(x) for x in fxs]))
        # FILL AXIS
        if motion and (motion[0] or motion[1]):
            axis = (float(motion[0]), float(motion[1]))
        else:
            dists = {"top": int(fys.min()), "bottom": H - 1 - int(fys.max()),
                     "left": int(fxs.min()), "right": Wd - 1 - int(fxs.max())}
            floor = min(dists, key=dists.get)
            axis = {"top": (1.0, 0.0), "bottom": (-1.0, 0.0), "left": (0.0, 1.0), "right": (0.0, -1.0)}[floor]

        def _border_frac(cells, target):
            nbc = tot = 0
            for (y, x) in cells:
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < Wd and (yy, xx) not in cells:
                        tot += 1; nbc += 1 if int(g0[yy, xx]) == target else 0
            return (nbc / tot) if tot else 0.0

        def _touches_fluid(cells):
            for (y, x) in cells:
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (y + dy, x + dx) in fluidset:
                        return True
            return False

        # BOUNDARY BY FUNCTION: tall/thin separators sitting between/adjacent to fluid columns (NOT the biggest region)
        sep = {}
        for o in objs:
            if o.get("colour") in (bg, fluid_colour) or o.get("size", 0) < 6:
                continue
            oy = [p[0] for p in o["cells"]]; ox = [p[1] for p in o["cells"]]
            h = max(oy) - min(oy) + 1; w = max(ox) - min(ox) + 1; xc = sum(ox) / len(ox)
            if h >= 2 * w and any(abs(xc - cx) <= 6 for cx in colx):     # elongated along fill + beside a fluid column
                sep[o["colour"]] = sep.get(o["colour"], 0) + o["size"]
        boundary = max(sep, key=sep.get) if sep else None
        # floor projection: the fluid's extreme OPPOSITE the fill direction (the source edge where buttons sit)
        _proj = lambda y, x: y * axis[0] + x * axis[1]
        floor_proj = min(_proj(int(y), int(x)) for y, x in zip(fys, fxs))
        # SINGLE MUTUALLY-EXCLUSIVE PASS: MARKER (embedded in boundary) XOR BUTTON (at the fluid SOURCE edge/floor) XOR
        # PUCK base (touches fluid on the fill/surface side) -- priority in that order. Buttons sit at the source even
        # though they touch fluid, so the floor test must precede the puck test.
        markers = []; pucks = []; buttons = []
        for o in objs:
            col = o.get("colour")
            if col in (bg, fluid_colour, boundary) or not (1 <= o.get("size", 0) <= 10):
                continue
            cells = o["cells"]; cy = int(round(o["centroid"][0])); cx = int(round(o["centroid"][1]))
            if boundary is not None and _border_frac(cells, boundary) >= 0.30:
                markers.append({"colour": col, "pos": (cy, cx)})                       # embedded in boundary -> MARKER
            elif min(_proj(y, x) for (y, x) in cells) <= floor_proj + 2:               # at the source edge -> BUTTON
                ci = min(range(len(fcols)), key=lambda i: abs(fcols[i]["xc"] - cx))
                side = "right" if cx > fcols[ci]["xc"] else "left"
                donor = ci + 1 if side == "right" else ci - 1      # confirmed: right button pulls from the right neighbour
                if 0 <= donor < len(fcols):
                    buttons.append({"pos": (cy, cx), "receiver": ci, "donor": donor, "side": side})
            elif _touches_fluid(cells):                                                 # on the fill/surface side -> PUCK
                base = min(cells, key=lambda pt: pt[0] * axis[0] + pt[1] * axis[1])
                ci = min(range(len(fcols)), key=lambda i: abs(fcols[i]["xc"] - cx))
                pucks.append({"id": (cy, cx), "colour": col, "base": (int(base[0]), int(base[1])), "col": ci})
        # keep only pucks whose colour has a matching marker (identity correspondence)
        mcols = {m["colour"] for m in markers}
        pucks = [pp for pp in pucks if pp["colour"] in mcols]
        binding = _RF.SHARED.gate_binding.bind(pucks, markers)
        edges = sorted(set((b["donor"], b["receiver"]) for b in buttons))
        # PER-COLUMN CAP (max-fill ceiling), DISTINCT from target: the top of the bounding boundary pillar along the fill
        # axis. For a GATED column it is the pillar carrying that puck's MARKER (Isaiah's rule); for a conduit, the
        # flanking-pillar extent. `target` (marker level, align-to) sits BELOW `cap` (pillar top, staging ceiling).
        pillars = []
        if boundary is not None:
            labb, nbb = _lbl(g0 == boundary)
            for i in range(1, nbb + 1):
                pys, pxs = np.where(labb == i)
                if len(pys) >= 3:
                    pillars.append({"xc": float(pxs.mean()),
                                    "top": max(_proj(int(y), int(x)) for y, x in zip(pys, pxs)),
                                    "cells": set(zip([int(y) for y in pys], [int(x) for x in pxs]))})

        def _marker_pillar_cap(mpos):
            best, bestd = None, 10 ** 9
            for pl in pillars:
                d = min((abs(mpos[0] - yy) + abs(mpos[1] - xx)) for (yy, xx) in pl["cells"]) if pl["cells"] else 10 ** 9
                if d < bestd:
                    bestd, best = d, pl
            return best["top"] if (best is not None and bestd <= 3) else None

        def _flanking_cap(xc):
            near = [pl["top"] for pl in pillars if abs(pl["xc"] - xc) <= 8]
            return max(near) if near else None
        caps = {}
        for p in pucks:
            m = binding["gated"].get(p["id"])
            if m is not None:
                caps[p["col"]] = _marker_pillar_cap(m["target"])            # gated: marker-pillar top
        for fc_i, fc in enumerate(fcols):
            if caps.get(fc_i) is None:
                caps[fc_i] = _flanking_cap(fc["xc"])                        # conduit / fallback: flanking-pillar extent
        # current fluid SURFACE per column (extreme along +axis) -> 'full' when surface reaches cap
        surface = {}
        for fc_i, fc in enumerate(fcols):
            xs = [x for (y, x) in fluidset if abs(x - fc["xc"]) <= 3]
            ys = [y for (y, x) in fluidset if abs(x - fc["xc"]) <= 3]
            surface[fc_i] = (max(_proj(y, x) for y, x in zip(ys, xs)) if xs else None)
        pflow = [{"id": p["id"], "pos": p["base"], "col": p["col"],
                  "target": binding["gated"].get(p["id"], {}).get("target"),
                  "cap": caps.get(p["col"]), "surface": surface.get(p["col"])} for p in pucks]
        full_cols = [ci for ci in range(len(fcols))
                     if caps.get(ci) is not None and surface.get(ci) is not None and surface[ci] >= caps[ci] - 1]
        _sweep = _RF.SHARED.conditional_flow.sweep_direction(edges, len(fcols))
        sched = _RF.SHARED.conditional_flow.schedule(pflow, axis, edges=edges, full_cols=full_cols, sweep_dir=_sweep)
        feas = _RF.SHARED.conditional_flow.feasible(pflow, axis)
        # MODEL-COHERENCE labeling (Gap 3): is this role assignment internally coherent + playable? A salience decoy
        # labeled 'boundary' would separate nothing / embed no markers and be rejected here -- automating "that can't be
        # the boundary". Regime-agnostic checks live in SHARED.coherence.model_coherence.
        labeling = {"boundary_present": 1 if boundary is not None else 0,
                    "boundary_separates": 1 if (boundary is not None and len(fcols) >= 2) else 0,
                    "boundary_embeds_markers": 1 if markers else 0,
                    "gated_count": len(binding.get("gated", {})),
                    "operators_effective": 1 if buttons else 0}
        return {"binding": binding, "axis": axis, "boundary": boundary, "pucks": pucks, "markers": markers,
                "schedule": sched, "feasible": feas, "buttons": buttons, "edges": edges, "fcols": colx,
                "caps": caps, "surface": surface, "full_cols": full_cols, "sweep_dir": _sweep, "labeling": labeling}
    except Exception:
        return None

def _puck_gap_now(adapter, colour, marker, axis, fluid_colour):
    """Re-measure ONE puck's SIGNED alignment gap along the fill axis from the CURRENT frame -- the per-press GAP trace.
    Finds the fluid-adjacent object of `colour` (the puck), takes its base edge (extreme opposite +axis), and returns the
    signed distance to its `marker`. Cheap (single object scan), orientation-free, no grid rescale."""
    try:
        import math
        g = np.asarray(_perceive_grid(adapter))
        fys, fxs = np.where(g == fluid_colour)
        fset = set(zip([int(y) for y in fys], [int(x) for x in fxs]))
        best = None
        for o in _distinct_objects(g):
            if o.get("colour") != colour or o.get("size", 0) > 10:
                continue
            if any((y + dy, x + dx) in fset for (y, x) in o["cells"] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                best = o; break
        if best is None:
            return None
        base = min(best["cells"], key=lambda p: p[0] * axis[0] + p[1] * axis[1])
        n = math.hypot(axis[0], axis[1]) or 1.0
        return ((marker[0] - base[0]) * axis[0] + (marker[1] - base[1]) * axis[1]) / n
    except Exception:
        return None


def _win_predicate_lib(g0):
    """Evaluate the SHARED-GRAMMAR relations that could be a win condition, on one frame -- reusing the same colour
    pairing as _colour_volume and the same SAME(...) relation used across the objective grammar. Each predicate is a
    TEMPLATE (colour/axis-agnostic), not an instance, so it transfers to games never seen. Returns {name: (holds,total)}."""
    from collections import defaultdict
    g0 = np.asarray(g0); bg = int(np.bincount(g0.ravel()).argmax())
    marks = defaultdict(list)
    for o in _distinct_objects(g0):
        if o["colour"] not in (0, bg, 9) and o["size"] <= 14:
            marks[o["colour"]].append((o["centroid"][0], o["centroid"][1]))     # (row, col)
    pairs = {c: pts for c, pts in marks.items() if len(pts) == 2}                # clean puck<->target pairs, by COLOUR
    res = {}
    for name, ax in [("SAME_ROW(puck_c,target_c)", 0), ("SAME_COLUMN(puck_c,target_c)", 1)]:
        if not pairs:
            res[name] = None; continue
        holds = sum(1 for c, (a, b) in pairs.items() if abs(a[ax] - b[ax]) <= 2)
        res[name] = (holds, len(pairs))
    # PROPERTY-MATCH predicates (avatar / locksmith regime): do two mutate-in-place glyphs (key & lock) COINCIDE in
    # shape / orientation / colour? The win-condition learner can then DISCOVER MATCH(key,lock) by the same contrast --
    # it holds at the win (key aligned to lock) and is violated before. Property comparison, not spatial.
    try:
        gl = _frame_glyphs(g0)
        if len(gl) >= 2:
            for name, keyf in [("SAME_SHAPE(glyph_i,glyph_j)", lambda o: o["canon_shape"]),
                               ("SAME_ORIENTATION(glyph_i,glyph_j)", lambda o: o["orient"]),
                               ("SAME_COLOUR(glyph_i,glyph_j)", lambda o: o["colours"])]:
                vals = [keyf(o) for o in gl]
                match = any(vals[i] == vals[j] for i in range(len(vals)) for j in range(i + 1, len(vals)))
                res[name] = (1 if match else 0, 1)
    except Exception:
        pass
    return res


def _induce_win_condition(ring, know):
    """GENERIC WIN-CONDITION INDUCTION (learn the OBJECTIVE like the causal map learns dynamics). Scan a short ring of
    recent frames: the shared-grammar predicate that is VIOLATED in early frames and becomes fully SATISFIED in a later
    one is the discriminative win condition -- that violated->satisfied transition IS the win. Store it as a hypothesis
    with CONFIDENCE that grows each time a new win re-confirms it; a win that also satisfies a NEW predicate COMPOSES
    (AND) it in. `know` persists across levels/games. Returns {formula:[names], conf:{name:count}}."""
    wc = know.setdefault("win_condition", {"formula": [], "conf": {}, "wins": 0})
    if not ring or len(ring) < 2:
        wc["_added"] = []; wc["_pruned"] = []
        return wc
    wc["wins"] = wc.get("wins", 0) + 1
    seq = [_win_predicate_lib(g) for g in ring]
    # TROPISM (observe): rank the generated questions by discrimination and log the answer ranking pins from THIS win.
    # win_mask: the ring's end-state is the win (why induction was called). Non-circular: uses the win-frame POSITION,
    # not the answer. If ranking pins the true predicate from 1 win where passive induction needs 2, the tropism narrows
    # faster -- the falsifiable claim. Changes no decisions in observe mode.
    try:
        import question_tropism as _QT
        if _QT.MODE != "off" and len(seq) >= 2:
            _mask = [False] * (len(seq) - 1) + [True]
            _name, _score, _decisive = _QT.top_answer(seq, _mask)
            wc["_tropism"] = {"top": _name, "score": round(_score, 3), "decisive": _decisive, "at_win": wc["wins"]}
    except Exception:
        pass
    names = set().union(*[set(s.keys()) for s in seq]) if seq else set()
    _added = []
    for name in names:
        vals = [s.get(name) for s in seq if s.get(name) is not None]
        if len(vals) < 2:
            continue
        violated_early = any(v[0] < v[1] for v in vals[:max(1, len(vals) // 2 + 1)])
        satisfied_ever = any(v[0] == v[1] and v[1] > 0 for v in vals)
        # MICRO-HGT MARKET (Gap 1, observe): express every candidate predicate as a competing objective-hypothesis and
        # score it by Friston free-energy (residual 0 on a satisfied win = fit). Advisory only in observe mode -- the
        # single-formula logic below is unchanged; this builds the parallel pool so the market can be A/B'd vs baseline.
        try:
            import regime_factory as _RF
            _mkt = getattr(_RF.SHARED, "hypothesis_market", None)
            if _mkt is not None:
                _mkt.express(name)
                _mkt.score(name, residual=(0.0 if (violated_early and satisfied_ever) else 0.6),
                           precision=1.0, confirmed=bool(violated_early and satisfied_ever))
        except Exception:
            pass
        if violated_early and satisfied_ever:                 # transitions violated -> satisfied within the ring
            wc["conf"][name] = wc["conf"].get(name, 0) + 1     # re-confirmation -> confidence++
            if name not in wc["formula"]:
                wc["formula"].append(name); _added.append(name)   # COMPOSE: AND-in a newly-discriminating predicate
            # RESONANCE (accelerant 1, observe): two INDEPENDENT derivations vote. "perception_transition" (frontier bias:
            # the single-ring violated->satisfied percept) and "induction_reconfirm" (consensus bias: re-confirmed across
            # wins). If both implicate the SAME predicate, resonance>1 = independent convergence. If only one ever votes,
            # the agent has no independent sources here (one source in a trenchcoat) -- that measurement is the discovery.
            try:
                import regime_factory as _RF2
                _rm = getattr(_RF2.SHARED, "resonance_market", None)
                if _rm is not None:
                    _rm.vote(name, "perception_transition")                      # frontier: the raw percept transition
                    if wc["conf"].get(name, 0) >= 2:                             # consensus: it re-confirmed across wins
                        _rm.vote(name, "induction_reconfirm")
                    _rm.tag_context(name, tuple(sorted(names)))                  # context-tag (accelerant 3)
            except Exception:
                pass
    # PRUNE coincidences: once there are >=2 wins, drop any predicate that re-confirmed on fewer than half of them.
    # SELF-REVERTING: the prune is a behavior-preserving restructure -- versioned + regression-gated. A prune that would
    # orphan a VERIFIED predicate (confirmed on EVERY win so far -> a load-bearing invariant, not a coincidence) is
    # reverted; one that only sheds unconfirmed correlates is kept. The composer restructures its own knowledge safely.
    _pruned = []
    if wc["wins"] >= 2:
        _verified = {n for n in wc["formula"] if wc["conf"].get(n, 0) >= wc["wins"]}   # confirmed on ALL wins = invariant
        def _apply_prune(_wcref):
            _keep = [n for n in _wcref["formula"] if _wcref["conf"].get(n, 0) >= max(1, _wcref["wins"] * 0.5)]
            _wcref["_pruned_cand"] = [n for n in _wcref["formula"] if n not in _keep]
            _wcref["formula"] = _keep
        def _verify_prune(_wcref):
            # regression: no VERIFIED (all-wins) predicate may be orphaned by the prune
            return _verified.issubset(set(_wcref["formula"]))
        try:
            import regime_factory as _RF
            _vcs = getattr(_RF.SHARED, "composer_vcs", None)
            if _vcs is not None:
                _res = _vcs.try_restructure(wc, _apply_prune, _verify_prune, msg="win-condition prune")
                _pruned = wc.get("_pruned_cand", []) if _res.get("kept") else []
                wc["_vcs"] = _res   # surface for narration at the call site (adapter-scoped)
            else:
                _apply_prune(wc); _pruned = wc.get("_pruned_cand", [])
        except Exception:
            _keep = [n for n in wc["formula"] if wc["conf"].get(n, 0) >= max(1, wc["wins"] * 0.5)]
            _pruned = [n for n in wc["formula"] if n not in _keep]; wc["formula"] = _keep
    wc["_added"] = _added; wc["_pruned"] = _pruned
    return wc


class _WinCondObjective:
    """Make the LEARNED WIN CONDITION the objective the solver optimises: distance = total |gap| along the induced axis
    across the colour pucks. Because _h() reads this, the existing drive/cascade reduces the column-gaps directly -- the
    transferred goal drives the search, and the control->puck binding is discovered the normal way (a control is driven
    iff pressing it lowers THIS objective, i.e. slides a puck toward its same-colour target)."""
    __slots__ = ("know",)

    def __init__(self, know):
        self.know = know

    def measure(self, g):
        wo = _win_objective(g, self.know)
        if not wo or not wo["pairs"]:
            return 0.0
        return float(sum(abs(p["gap"]) for p in wo["pairs"]))


def _win_objective(g0, know):
    """TRANSFER the induced win condition to THIS level as its objective (comprehension carried forward, not re-derived).
    Read the learned formula (e.g. SAME_COLUMN), pair pucks<->targets by COLOUR, and measure each pair's gap ALONG THE
    INDUCED AXIS (SAME_COLUMN -> column, SAME_ROW -> row). The agent then drives toward the SAME relation that won the
    earlier levels. Returns {axis, formula, conf, pairs:[{colour,gap,puck,target}], satisfied} or None if nothing learned."""
    from collections import defaultdict
    wc = (know or {}).get("win_condition", {}); formula = wc.get("formula", [])
    if not formula:
        return None
    axis = 1 if any("COLUMN" in f for f in formula) else 0     # the induced alignment axis
    g0 = np.asarray(g0); bg = int(np.bincount(g0.ravel()).argmax())
    marks = defaultdict(list)
    for o in _distinct_objects(g0):
        if o["colour"] not in (0, bg, 9) and o["size"] <= 14:
            marks[o["colour"]].append((int(round(o["centroid"][0])), int(round(o["centroid"][1]))))
    pairs = []
    for c, pts in marks.items():
        if len(pts) == 2:
            pairs.append({"colour": int(c), "gap": pts[0][axis] - pts[1][axis], "puck": pts[0], "target": pts[1]})
    return {"axis": axis, "formula": formula, "conf": dict(wc.get("conf", {})), "pairs": pairs,
            "satisfied": (all(abs(p["gap"]) <= 2 for p in pairs) if pairs else False)}


def _colour_volume(g0, fluid_colour):
    """COLOUR-CORRELATED win condition (the rule that transfers from prior levels): each coloured PUCK must reach its
    SAME-COLOUR target block's height. Pair markers by colour -> for each pair, the instance sitting on a fluid column
    is the PUCK (current level), the other is the TARGET. gap = puck_row - target_row: gap>0 (puck BELOW target) =
    SCARCITY (must rise/FILL); gap<0 (puck ABOVE target) = SURPLUS (must descend/DRAIN). This says WHICH column drains
    and WHICH fills -- the correlation that defines the objective and the cascade order, not a generic surplus scan.
    Returns per-column [{col_x, kind, gap, colour, puck, target}]. Colour/scale/rotation-agnostic."""
    from collections import defaultdict
    from scipy.ndimage import label as _lbl
    g0 = np.asarray(g0); bg = int(np.bincount(g0.ravel()).argmax())
    _lab, _n = _lbl(g0 == fluid_colour, structure=np.ones((3, 3)))
    colspans = []
    for i in range(1, _n + 1):
        ys, xs = np.where(_lab == i)
        if len(ys) >= 8:
            colspans.append((int(xs.min()), int(xs.max()), int(ys.min())))   # x0, x1, fill_top

    def _top_dist(x, y):
        """distance from (x,y) up to the nearest fluid-top of a column it sits over; None if over no column."""
        best = None
        for x0, x1, top in colspans:
            if x0 - 2 <= x <= x1 + 2:
                d = abs(y - top)
                best = d if best is None else min(best, d)
        return best

    marks = defaultdict(list)
    for o in _distinct_objects(g0):
        if o["size"] <= 4 and o["colour"] not in (fluid_colour, bg, 9):
            marks[o["colour"]].append((int(round(o["centroid"][0])), int(round(o["centroid"][1]))))  # (row, x)
    out = []
    for col, pts in marks.items():
        if len(pts) != 2:
            continue                                           # a clean puck<->target pair only
        # PUCK = the instance riding a fluid top (smallest distance to a column top); TARGET = the other. This is robust
        # to a target marker sitting near another column (the pairing is by COLOUR; the roles by fluid-proximity).
        scored = sorted(((_top_dist(x, y), (y, x)) for (y, x) in pts),
                        key=lambda s: (s[0] is None, s[0] if s[0] is not None else 1e9))
        (pd, puck), (td, target) = scored[0], scored[1]
        if pd is None:                                         # neither rides a column -> not a fluid puck/target pair
            continue
        colx = min(colspans, key=lambda c: abs((c[0] + c[1]) // 2 - puck[1]))
        colx = (colx[0] + colx[1]) // 2
        gap = puck[0] - target[0]                              # puck below target (gap>0) => FILL; above (gap<0) => DRAIN
        out.append({"col_x": colx, "colour": int(col), "gap": gap,
                    "kind": "scarcity" if gap > 1 else ("surplus" if gap < -1 else "at_target"),
                    "puck": puck, "target": target})
    return out


def _cascade_sequence(model, regions, volume):
    """Phase-4 SEQUENCED CASCADE ALLOCATOR (#6): order the modeled controls so fluid routes SURPLUS -> DEFICIT.
    Greedy delta-order presses the biggest single effect first; but when fluid is fungible and a column is
    OVER-filled, the winning move is to DRAIN the surplus first (freeing fluid) THEN fill the deficits -- an ORDER
    the per-control greedy structurally cannot see. Associate each control with a column via its measured effect
    region, then: tier 0 = drain surplus columns (biggest surplus first), tier 1 = fill deficit columns (deepest
    first), tier 2 = unassociated controls by delta. Pure ordering, no extra actions. Returns [rc, ...] or None."""
    cells = (volume or {}).get("cells", [])
    if not cells:
        return None

    def _col(rc):
        reg = regions.get(rc)
        if reg is None:
            return None
        return min(cells, key=lambda s: abs(s["puck"][1] - reg[1]), default=None)   # nearest column by x

    scored = []
    for rc in model:
        if model[rc]["delta"] <= 1e-9 and regions.get(rc) is None:
            continue
        s = _col(rc); dneg = -model[rc]["delta"]
        if s is None:
            scored.append((2, 0.0, dneg, rc))
        elif s["kind"] == "surplus":
            scored.append((0, -abs(s["gap"]), dneg, rc))       # drain the most-over-filled column first
        elif s["kind"] == "scarcity":
            scored.append((1, -abs(s["gap"]), dneg, rc))       # then fill the deepest deficit
        else:
            scored.append((2, 0.0, dneg, rc))
    scored.sort()
    return [rc for (_t, _g, _d, rc) in scored]


def _construct_objective(roles, volume):
    """Phase-4 OBJECTIVE CONSTRUCTION (#1, reframed): the objective is BUILT from the induced parts -- the roles
    (which colours are fluid / pucks / targets) and the resource accounting (_volume_state: which columns are in
    surplus vs scarcity) -- NOT selected from a fixed menu of objective TYPES. A menu is a front-loaded prior the
    OOD-by-design private set won't transfer; construction assembles the goal from what THIS level's dynamics
    revealed. Returns a short human-readable spec of the constructed objective (for narration/derivation)."""
    r = roles or {}; v = volume or {}
    n_sc = sum(1 for s in v.get("cells", []) if s.get("kind") == "scarcity")
    n_su = sum(1 for s in v.get("cells", []) if s.get("kind") == "surplus")
    return ("objective := ALL(puck_i -> target_i) via FUNGIBLE fluid(colour %s); resource-state: %d scarcity + %d surplus, "
            "enough_to_cascade=%s  [CONSTRUCTED from roles+volume, not selected from a menu]"
            % (r.get("fluid_colour"), n_sc, n_su, v.get("enough_to_cascade")))


def _coverage_state(cands, cmap, type_key):
    """Coverage completeness for the INDUCTION TRIGGER. CONTROLS = candidate objects whose TYPE has shown an effect
    when probed (reduce/change/split -- i.e. actuators, not the fluid/borders). Coverage is COMPLETE when every
    control INSTANCE has been probed (is recorded in the causal map). Once complete, the accumulated map is a full
    picture of what each control does across all lives -> INDUCE the objective from it instead of probing further.
    Returns (n_covered, n_controls, complete)."""
    active = {tk for tk, h in cmap.items()
              if isinstance(h, dict) and (h.get("effect") in ("reduce", "change") or h.get("split"))}
    controls = [o for o in cands if type_key(o) in active]
    if not controls:
        return 0, 0, False
    covered = 0
    for o in controls:
        rc = (int(round(o["centroid"][0])), int(round(o["centroid"][1])))
        h = cmap.get(type_key(o))
        if h and rc in h.get("instances", {}):
            covered += 1
    return covered, len(controls), (covered >= len(controls))


def _detect_bars(g0, max_bars=8, max_thick=8):
    """ALL THIN horizontal target BARS (fill targets), arity-invariant. A bar is a horizontal band that spans a large
    fraction of the width for only a FEW rows -- distinguishing a target bar from a tall fill REGION (whose rows also
    span the width but continue for many rows). Skips past each band so a region isn't counted as many bars."""
    g = np.asarray(g0); H, W = g.shape
    bg = int(np.bincount(g.ravel()).argmax())
    found = []; r = 1
    while r < H - 1 and len(found) < max_bars:
        matched = None
        for col in np.unique(g[r]):
            if int(col) != bg and int((g[r] == col).sum()) > 0.4 * W:
                matched = int(col); break
        if matched is None:
            r += 1; continue
        r2 = r
        while r2 < H and int((g[r2] == matched).sum()) > 0.4 * W:
            r2 += 1
        if (r2 - r) <= max_thick:                              # THIN band -> candidate bar
            above_ok = r > 2 and int((g[r - 1] == bg).sum()) > 0.15 * W
            below_ok = r2 < H - 2 and int((g[r2] == bg).sum()) > 0.15 * W
            if above_ok and below_ok:                          # INTERIOR bar (play-area bg both sides), not a frame/edge band
                found.append((r, matched))
        r = r2 + 1                                             # skip past this band entirely
    return found


def _fill_submeasures(g0):
    """One air-gap sub-measure PER target bar: the unfilled (background) cells below each bar. Arity-invariant."""
    g = np.asarray(g0); H, W = g.shape
    bg = int(np.bincount(g.ravel()).argmax())
    subs = []
    for (bar_row, bar_col) in _detect_bars(g0):
        cols = [c for c in range(W) if g[bar_row, c] == bar_col]
        if not cols:
            continue
        lo, hi = min(cols), max(cols)
        bb = bar_row
        while bb + 1 < H and int((g[bb + 1, lo:hi + 1] == bar_col).sum()) > 0.3 * (hi - lo + 1):
            bb += 1

        def _mk(lo, hi, bb):
            def _sm(g2):
                g2 = np.asarray(g2); air = 0
                for c in range(lo, hi + 1):
                    r = bb + 1
                    while r < H and int(g2[r, c]) == bg:
                        air += 1; r += 1
                return float(air)
            return _sm
        subs.append(_mk(lo, hi, bb))
    return subs


def _alignment_submeasures(g0, interaction_probe=None):
    """One (measure, ANCHOR) sub-goal per MOVABLE marker-group (puck) -> nearest STATIC same-type target (flag). The
    anchor is the movable group's centroid -- the spatial handle the matched planner uses to route the control whose
    effect region sits under this puck. Arity-invariant; requires an evidenced-movable marker (rejects static-static)."""
    from collections import defaultdict
    g0 = np.asarray(g0)
    markers0 = [o for o in _distinct_objects(g0) if 2 <= o["size"] <= 30]
    if len(markers0) < 2:
        return []
    groups0 = defaultdict(list)
    for m in markers0:
        groups0[_marker_type(m, g0)].append(m)
    change_pts = [x["change_centroid"] for x in (interaction_probe or [])
                  if x.get("changed") and x.get("change_centroid")]

    def _near(cen, rad=8):
        return any(abs(cen[0] - p[0]) + abs(cen[1] - p[1]) <= rad for p in change_pts)

    subs = []
    for k, members in groups0.items():
        if len(members) < 2:
            continue
        static = [m for m in members if not _near(m["centroid"])]
        movable = [m for m in members if _near(m["centroid"])]
        if not (static and movable):
            continue
        statics = [tuple(s["centroid"]) for s in static]
        anchor = (sum(m["centroid"][0] for m in movable) / len(movable),
                  sum(m["centroid"][1] for m in movable) / len(movable))

        def _mk(k, statics):
            def _sm(g2):
                grp = defaultdict(list)
                for m in (o for o in _distinct_objects(np.asarray(g2)) if 2 <= o["size"] <= 30):
                    grp[_marker_type(m, g2)].append(m)
                tot = 0.0
                for m in grp.get(k, []):
                    if _near(m["centroid"]):
                        tot += min(abs(m["centroid"][0] - s[0]) + abs(m["centroid"][1] - s[1]) for s in statics)
                return tot
            return _sm
        subs.append((_mk(k, statics), anchor))
    return subs


def _fluid_columns(g0, fluid):
    """The fluid COLUMNS: x-ranges between the boundary walls (the id-5 separators), detected by the WALLS not by fluid
    presence -- so a nearly-empty DEFICIT column (the ones that need filling) is still a column. The boundary colour is
    the dominant non-fluid, non-background colour in the play area (relational, not hard-coded)."""
    g0 = np.asarray(g0); r0, r1, c0, c1 = _play_area(g0)
    bg = int(np.bincount(g0[r0:r1 + 1, c0:c1 + 1].ravel()).argmax())
    from collections import Counter as _C
    nonf = _C(int(v) for v in g0[r0:r1 + 1, c0:c1 + 1].ravel() if int(v) not in (bg, fluid))
    boundary = nonf.most_common(1)[0][0] if nonf else None
    if boundary is None:
        return []
    xs = list(range(c0, c1 + 1))
    is_wall = [int((g0[r0:r1 + 1, x] == boundary).sum()) >= 3 for x in xs]
    cols = []; s = None
    for i, x in enumerate(xs):
        if not is_wall[i] and s is None:
            s = x
        elif is_wall[i] and s is not None:
            cols.append((s, xs[i - 1])); s = None
    if s is not None:
        cols.append((s, c1))
    return [(a, b) for (a, b) in cols if b - a >= 1]


def _fluid_level_objective(g0, fluid, targets=None, pucks=None, mask=None):
    """Objective for CASCADING-VOLUME levels, per COLUMN. Fluid is a fungible resource in columns (id-0) separated by
    id-5 boundaries; each column has a target at its win level. disc = sum over columns of |fluid_top(column) -
    target_row|. Actuators TRANSFER fluid between columns, so driving the objective down IS cascade allocation. When
    `pucks` and `targets` are given, each target is matched to the column containing its same-colour PUCK -- because the
    target markers sit ON the id-5 walls (their own x is unreliable), while the puck is what's IN the column."""
    g0 = np.asarray(g0); r0, r1, c0, c1 = _play_area(g0)
    bg = int(np.bincount(g0[r0:r1 + 1, c0:c1 + 1].ravel()).argmax())
    cols = _fluid_columns(g0, fluid)
    if not cols:
        return None
    coltgt = []
    if pucks and targets:                                      # match each target to its PUCK's column (walls unreliable)
        def _colof(x):
            for (xl, xh) in cols:
                if xl - 1 <= x <= xh + 1:
                    return (xl, xh)
            return None
        seen = set()
        for pk in pucks:
            tg = [t for t in targets if t["colour"] == pk["colour"]]
            col = _colof(pk["centroid"][1])
            if tg and col and col not in seen:
                coltgt.append((col[0], col[1], tg[0]["centroid"][0])); seen.add(col)
    else:
        marker_pool = targets if targets else [o for o in _distinct_objects(g0)
                                               if 2 <= o["size"] <= 8 and o["colour"] not in (fluid, bg)]
        for (xlo, xhi) in cols:
            cm = [m for m in marker_pool if xlo - 1 <= m["centroid"][1] <= xhi + 1]
            if cm:
                coltgt.append((xlo, xhi, min(m["centroid"][0] for m in cm)))
    if not coltgt:
        return None

    def _ftop(g, xlo, xhi):
        tops = [r0 + int(np.where(g[r0:r1 + 1, x] == fluid)[0].min())
                for x in range(xlo, xhi + 1) if (g[r0:r1 + 1, x] == fluid).any()]
        return float(np.median(tops)) if tops else float(r1)

    def measure(g):
        g = np.asarray(g); tot = 0.0
        for (xlo, xhi, ty) in coltgt:
            tot += abs(_ftop(g, xlo, xhi) - ty)
        return tot
    return Discrepancy(measure, lambda g: [])


def _provisional_fill_objective(g0):
    """Fallback objective when no explicit sub-goal is detected yet (e.g. a bordered puck level whose movable elements
    only reveal themselves under fluid flow): a generic 'raise the fluid' measure = the count of unfilled (background)
    cells WITHIN THE SEGMENTED PLAY AREA (frame excluded). Pumping reduces it, getting the solve MOVING and generating
    the motion that re-induction needs to reveal the real puck->target sub-goals. Border/scale-invariant."""
    g0 = np.asarray(g0)
    r0, r1, c0, c1 = _play_area(g0)
    bg = int(np.bincount(g0[r0:r1 + 1, c0:c1 + 1].ravel()).argmax())    # background WITHIN the play area

    def measure(g):
        g = np.asarray(g)
        return float((g[r0:r1 + 1, c0:c1 + 1] == bg).sum())            # unfilled play-area background

    return Discrepancy(measure, lambda g: [])


def _induce_multigoal_objective(g0, interaction_probe=None):
    """GENERAL ARITY-INVARIANT objective inducer (the worst-predictable-case principle at the objective level). Detect
    ALL sub-goals PRESENT this level and make the discrepancy their SUM -- satisfied only when EVERY sub-goal is 0,
    order-independent (your rule: enough fluid in each place so each puck matches its flag). Any number of fill bars +
    any number of puck->target pairs; a sub-goal is included only if its markers are actually present. Level 0
    instantiates it with ONE fill; level 3 with THREE alignments -- the SAME code, the level supplies the N. When no
    explicit sub-goal is detectable yet (movables hidden until fluid flows), falls back to a provisional 'raise the
    fluid' objective that bootstraps the motion re-induction needs."""
    subs = _fill_submeasures(g0) + [m for (m, _a) in _alignment_submeasures(g0, interaction_probe)]
    if not subs:
        return _provisional_fill_objective(g0)                 # bootstrap: get pumping so motion reveals the real goals

    def measure(g):
        return float(sum(sm(g) for sm in subs))

    def active(g):
        return []
    return Discrepancy(measure, active)


def _type_key(obj):
    """Position-INVARIANT object type (size bucket + aspect; colour-agnostic). Same-type objects are HYPOTHESISED to
    share a causal effect, so an effect discovered on one generalises across all of them instead of being re-tested per
    instance -- the behavioural analogue of recognising 'these are all the same kind of thing'."""
    sz = obj.get("size", 0)
    sizeb = 0 if sz <= 4 else 1 if sz <= 10 else 2 if sz <= 20 else 3 if sz <= 60 else 4
    cells = obj.get("cells") or set()
    if cells:
        rs = [p[0] for p in cells]; xs = [p[1] for p in cells]
        h = max(rs) - min(rs) + 1; w = max(xs) - min(xs) + 1
        aspect = 0 if h > w * 1.5 else (2 if w > h * 1.5 else 1)
    else:
        aspect = 1
    return (sizeb, aspect)


import sys as _sys
# PER-RUN RUNTIME MEMORY (Kaggle model): lives in the Python PROCESS, not on disk. Anchored to `sys` so it survives a
# module re-import/reload within the same run, and dies when the process ends -- the VM/one-run semantics of the OOD
# eval. No file persistence by design.
# Memory is split by WHAT IT IS ABOUT, not by which game produced it:
#   * the board in play  -> working memory on the gameplay itself (_game_mem): causal map, solutions, induced mechanics.
#                           Survives every level, death and reset of that gameplay; dies with it.
#   * the world at large -> the MOLECULE registry (_GLOBAL_KNOWLEDGE["patterns"]): that a mechanic of some kind exists.
# The former per-game index ("game X -> everything X taught me") is deliberately gone: it is a library, and it pays
# nothing on a board never seen -- which, the eval being OOD by construction, is the only board that matters.

# CROSS-GAME KNOWLEDGE: the MOLECULES -- mechanic values that have been seen to exist at all, held as a conceptual
# prior for a board never met before ("objective_type has been cascade/fill before"; "a trigger can cycle a property").
# There is deliberately NO per-game layer. A `by_game` index -- "re-encountering game X, reload everything X taught me"
# -- is a LIBRARY: it makes the agent good at games it has already played and no better at the one in front of it, and
# the private eval is OOD by construction, so nothing there will ever be a re-encounter. Only the mechanic transfers,
# never the game. Nothing in here names a game. Anchored to the process, no disk.
_GLOBAL_KNOWLEDGE = getattr(_sys, "_ouroboros_global_knowledge", None)
if _GLOBAL_KNOWLEDGE is None:
    _GLOBAL_KNOWLEDGE = _sys._ouroboros_global_knowledge = {"patterns": {}}


from spatial_map import SpatialMap, BLOCKED as _SM_BLOCKED   # module-level: the shared map + its vocabulary, used by
#                                                              EVERY planner (avatar BFS and descend's A*), not one


def _spatial_mem(adapter, quantum=None, ttl=80):
    """TRAVERSAL MEMORY for the gameplay in progress: what this agent has physically found out about getting around.

    It is deliberately NOT keyed by game identity. A store of "what I know about game X" is a LIBRARY -- it makes the
    agent good at games it has met and no better at a game it hasn't, which is the opposite of the point. Nothing here
    names or looks up a game. This is the composer's own working knowledge of the board it is standing on right now:
    it lives on the live gameplay (the adapter), and it dies with it. What generalises is the MECHANIC (a trigger
    cycles a property; a measured dead-end is impassable) -- and mechanics are held elsewhere, as mechanics.

    Scoped per LEVEL INDEX, because the maze is rebuilt per level -- planning level N's walls on level N+1 would plan
    over a board that no longer exists. But levels keep their OWN map for the whole session, so:
      * losing a life and re-entering a level RESUMES from what earlier attempts mapped -- no re-bumping the same walls;
      * a RESET back to level 0 returns to level 0's map, because that maze did not change when we died.
    That is the "don't forget between losses and resets" property, without ever remembering a game by name.
    """
    store = getattr(adapter, "_spatial_by_level", None)
    if store is None:
        store = adapter._spatial_by_level = {}                 # level index -> the map of THAT board, this session
    try:
        lvl = int(getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0)
    except Exception:
        lvl = 0
    sm = store.get(lvl)
    if sm is None:
        # NOTE (verified 20 Jul): in the LIVE composer path, neither SpatialMap.decay() nor .invalidate() is called
        # (both fire only in the legacy ouroboros_integrated brain). So the map neither time-forgets nor reactively
        # reopens -- it is a permanent accumulator, which suits ls20's maze (proven static: 2165/2172 walls in every
        # L1 frame, IoU 1.0 across 36 lives; map is created ONCE per level and persists across deaths). OURO_SM_TTL
        # is therefore currently INERT in this path (kept as a knob + record). The real dynamism-handling gap
        # (invalidate unwired) is harmless on ls20 -- the only volatile cells are cycling trigger glyphs, not a gate --
        # but is a roadmap item for games that DO open walls.
        import os as _os
        try:
            ttl = int(_os.environ.get("OURO_SM_TTL", ttl))
        except Exception:
            pass
        sm = store[lvl] = SpatialMap(ttl=ttl)
        if _os.environ.get("OURO_SM_DEBUG", "0") == "1":
            try:
                _emit(adapter, "SM-DEBUG  NEW SpatialMap created for level %d  (store now holds levels %s; adapter id %s)"
                      % (lvl, sorted(store.keys()), id(adapter) % 100000))
            except Exception:
                pass
    if quantum:
        adapter._spatial_quantum = int(quantum)                # lets the other planner convert px <-> lattice
    return sm


# Live gameplay working-memories, held as a plain LIST of references so process-wide observers (e.g. the legibility
# audit, which must count grammar steps emitted across the run) can see them. A list, not a dict: there is nothing to
# look anything up BY -- membership is the only fact, and no entry can be found by naming a game.
_WORKING_MEMS = getattr(_sys, "_ouroboros_working_mems", None)
if _WORKING_MEMS is None:
    _WORKING_MEMS = _sys._ouroboros_working_mems = []


def _session_key(adapter):
    """An opaque handle for the GAMEPLAY in progress, for namespacing signals (drives, model-doubt) that must not bleed
    between two different boards being played in the same process.

    Isolation is a real requirement; IDENTITY is not. Keying these on a game's NAME meant the agent could, in principle,
    recognise a board by name and reload its history -- and the private eval is OOD by construction, so that recognition
    can never fire there anyway. An opaque per-gameplay token gives the same separation and cannot become a lookup: it
    is meaningless outside the session that minted it, so nothing can key off "which game is this"."""
    k = getattr(adapter, "_sess_tok", None)
    if k is None:
        _n = getattr(_sys, "_ouroboros_session_n", 0) + 1
        _sys._ouroboros_session_n = _n
        k = adapter._sess_tok = "S%d" % _n
    return k


def _game_mem(adapter):
    """WORKING MEMORY of the gameplay in progress -- the causal map, the solution cache and the mechanics induced for
    the board actually in front of the agent. Scoped to the live gameplay, NOT to a game's identity.

    It used to be keyed by game_id and bootstrapped from a per-game registry, i.e. "I have met this game before, reload
    what it taught me". That is a library: it buys nothing on a board never seen, which is the only board that counts
    here. Nothing in this function knows or asks what game it is playing. What survives a gameplay is the MECHANIC
    (recorded into the game-agnostic molecule registry), never the game.

    It persists across LEVELS and across every death/reset within the gameplay -- an induced mechanic is about the
    world, so it should not be thrown away because a life was lost -- and it dies when the gameplay does."""
    m = getattr(adapter, "_working_mem", None)
    if m is None:
        m = adapter._working_mem = {"causal": {}, "solutions": {}, "mechanics": {}, "_sess": _session_key(adapter)}
        _WORKING_MEMS.append(m)                                # visible to process-wide observers; still nameless
    m.setdefault("mechanics", {})
    return m


def _mechanics(adapter):
    """The MECHANICS induced for the board in play (which colour is fluid, what the objective type is, what a trigger
    does) -- learned once and reused on every level and every life of THIS gameplay, never rebuilt. These describe the
    world the agent is standing in, so they are held by the gameplay, not filed under a game's name; the game-agnostic
    residue (that such a mechanic exists at all) goes to the molecule registry via _record_mechanic."""
    return _game_mem(adapter).setdefault("mechanics", {})


def _emit(adapter, step, once_key=None):
    """Append one step to the agent's GRAMMAR DERIVATION -- its own account, in the McGuffin grammar, of what it did.
    Called ONLY at the point an actual event happens, with the actual measured data, so the narration is GENERATED FROM
    the behaviour and cannot drift from it (same fidelity discipline as everywhere else). This is what makes the system
    categorically different from a brute-force solver: the solution comes with its own derivation, not just a score.

    once_key: if given, the step is emitted at most ONCE PER LEVEL for that key. This kills the whole class of
    per-re-attempt flooding at the source (the solve re-runs each re-attempt, so any unguarded _emit inside it
    repeats) -- instead of guarding each call site individually."""
    try:
        mem = _game_mem(adapter)
        if once_key is not None:
            lvl = getattr(getattr(adapter, "_obs", None), "levels_completed", None)
            seen = mem.setdefault("_emit_once", set())
            k = (lvl, once_key)
            if k in seen:
                return
            seen.add(k)
        mem.setdefault("derivation", []).append(step)
        # ALSO ride this step into the FRAME DATA so the recording/replay carries the COMPLETE grammar chronologically:
        # buffer it as a per-action delta that _ride_reason flushes onto the next action's reasoning. Concatenating the
        # per-action grammar across the frames THEN reconstructs the full derivation -- so the frame data is
        # self-describing and any collected derivation is a derived VIEW, not a separate source of truth. This closes
        # the frame-data / side-structure discrepancy: no grammar exists only in the side structure.
        try:
            pend = getattr(adapter, "_grammar_pending", None)
            if pend is None:
                pend = adapter._grammar_pending = []
            pend.append(step)
        except Exception:
            pass
    except Exception:
        pass


def _install_grammar_ride(adapter):
    """Make EVERY action -- avatar or actuator -- carry the grammar emitted since the last action, by wrapping the single
    action choke point adapter.step(). Only fires when there is UNFLUSHED grammar (so it never overwrites the richer
    _ride_reason meta, which clears the buffer itself). This is what makes the FRAME DATA carry the complete
    chronological grammar for all regimes, so the recording reconstructs the full derivation and the side structure is a
    derived view -- closing the frame-data/side-structure discrepancy regardless of regime."""
    if getattr(adapter, "_grammar_ride_installed", False) or not hasattr(adapter, "step"):
        return
    _orig_step = adapter.step
    import os as _os_gr

    def _play_area(ad):
        try:
            _fr = getattr(getattr(ad, "_obs", None), "frame", None)
            if _fr is None:
                return None
            _g = np.asarray(_fr); _g = _g[0] if _g.ndim == 3 else _g
            return _g[2:56] if _g.shape[0] >= 56 else _g
        except Exception:
            return None

    def _step_with_grammar(a, *args, **kw):
        # NO-FRAME-CHANGE STUCK-BREAK (universal choke -- Isaiah's rule). EVERY action flows through here, including the
        # pathfind executors that bypass _stepw and were pounding one direction into a wall (the ACTION2 xN no-op run).
        # If the same directional action produced NO board change repeatedly, it is a proven no-op -> redirect to an
        # untried available direction. The unchanged frame is the whole signal; no colour/wall guess is needed.
        try:
            if _os_gr.environ.get("OURO_NOCHANGE_BREAK", "1") == "1" and getattr(a, "value", None) in (1, 2, 3, 4) \
                    and getattr(adapter, "_nc_streak", 0) >= 3:
                _avs = [int(getattr(x, "value", 0)) for x in
                        (getattr(getattr(adapter, "_obs", None), "available_actions", None) or [])]
                _dirs = [d for d in (1, 2, 3, 4) if d in _avs] or [1, 2, 3, 4]
                _untried = [d for d in _dirs if d not in getattr(adapter, "_nc_tried", set())]
                if _untried and _untried[0] != int(getattr(a, "value", 0)):
                    from arcengine import GameAction as _GA
                    a = {1: _GA.ACTION1, 2: _GA.ACTION2, 3: _GA.ACTION3, 4: _GA.ACTION4}[_untried[0]]
        except Exception:
            pass
        try:
            pend = getattr(adapter, "_grammar_pending", None)
            if pend and hasattr(adapter, "set_reasoning"):
                meta = dict(getattr(adapter, "_composer_state", {}) or {})
                meta["grammar_steps"] = list(pend)
                meta.setdefault("source", "engine")
                adapter.set_reasoning(meta)
                adapter._grammar_pending = []
        except Exception:
            pass
        # ONE read before, one after, shared by everything that needs the frame. The previous cut called the guarded
        # full-res perceive TWICE per action on top of _play_area's read, and the run did 1928 actions where it
        # normally does ~3000: the budget model was paying for its own accuracy out of the action budget it measures.
        try:
            _fb = _perceive_grid(adapter)
        except Exception:
            _fb = None
        _pa_b = _fb[2:56] if _fb is not None else _play_area(adapter)
        _r = _orig_step(a, *args, **kw)
        try:
            _fa = _perceive_grid(adapter)
        except Exception:
            _fa = None
        try:
            if _fb is not None and _fa is not None:
                import budget_model as _BM
                _BM.get(adapter, emit=lambda m: _emit(adapter, m)).observe(_fb, _fa)   # THE one model, one choke
        except Exception:
            pass
        # THE RE-PARTITIONER, fed. ObjectTransitionInducer induces per-OBJECT rules keyed by
        # (colour_signature, size_bucket, action) -> translate | vanish | recolor | rotate. That is a FACTORED world
        # model -- one rule per object type -- and it has been in this tree, correct, referenced zero times outside
        # its own file. It matches objects by colour SIGNATURE rather than a single colour, which is the one thing
        # this codebase needs and does not have: the avatar here is a two-colour composite and every carve-by-colour
        # ontology cuts it in half.
        #
        # Minting is not creation, it is re-reading: the constraint is the material, the residual is the pressure,
        # and the operation is drawing a new boundary. This is the chisel. Feeding it is what points it at the board.
        try:
            if _fb is not None and _fa is not None and _aid_ok(a):
                import transition_induction as _TI
                _oti = getattr(adapter, "_obj_inducer", None)
                if _oti is None:
                    _oti = adapter._obj_inducer = _TI.ObjectTransitionInducer()
                    # The inducer is per-adapter and the adapter is per-episode; the EVIDENCE must not be. Hand it a
                    # table owned by _GLOBAL_KNOWLEDGE (which lives on sys._ouroboros_global_knowledge and is what
                    # composer_vcs already snapshots), keyed by game so one board's colours cannot vouch for another's.
                    try:
                        _gid = str(getattr(adapter, "game_id", None) or getattr(adapter, "_game_id", None) or "unknown")
                        _gid = _gid.split("-")[0]                      # the GAME, not the session instance
                        _tabs = _GLOBAL_KNOWLEDGE["patterns"].setdefault("obj_tables_by_game", {})
                        _oti.bind_table(_tabs.setdefault(_gid, _TI.new_table()))
                    except Exception:
                        pass                                           # unshared table still works; it just forgets
                _ter = (_GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("terrain_colours")
                _ms = getattr(adapter, "_model_search", None)
                if _ms is None:
                    import model_search as _MS
                    _ms = adapter._model_search = _MS.ModelSearch(_oti, emit=lambda m: _emit(adapter, m))
                try:
                    import budget_model as _BMh
                    _ms.life_horizon = _BMh.get(adapter).one_life()   # you cannot plan further than you can live
                except Exception:
                    pass
                if _ter and _oti.terrain != _ter:
                    _was = set(_oti.terrain or ())
                    _oti.terrain = set(_ter)
                    _oti._tracks = {}                 # identities re-found under the new segmentation; evidence stays
                    _emit(adapter, "SEGMENT  I now believe colours %s are board rather than objects, so I stop growing "
                                   "objects through them (was %s). This is a BELIEF from what I have seen, not a fact: "
                                   "if one of them ever moves or changes it is not board, and I revise. I am NOT "
                                   "discarding what I learned -- those laws were about differently-bounded objects, "
                                   "which is evidence about a different reading, not garbage."
                          % (sorted(_ter), sorted(_was) or "nothing"),
                          once_key="segment_%s" % sorted(_ter))
                _chain = []
                try:
                    import regime_factory as _RFp
                    _lay = _RFp.SHARED.perception.layers(adapter)
                    _chain = [L for L in _lay if getattr(L, "shape", None) == _fb.shape]
                except Exception as _le:
                    _emit(adapter, "LAYERS  could not read the frame stack (%s) -> falling back to the settled frame "
                                   "ONLY. Anything that flashed this action is invisible to me" % type(_le).__name__,
                          once_key="layers_fail")
                    _chain = []
                if not _chain:
                    _chain = [_fa]
                _an = getattr(a, "name", str(a))
                _prev = _fb
                for _i, _L in enumerate(_chain):
                    _oti.observe(_prev, _an if _i == 0 else "__settle__", _L)
                    _prev = _L
                if len(_chain) > 1:
                    _emit(adapter, "LAYERS  this action produced %d frames, not 1; I learn from all of them "
                                   "[the settled frame is what I act on; what FLASHED is only in the early ones]"
                          % len(_chain), once_key="layers_%d" % len(_chain))
                # CADENCE MEASURED, NOT CHOSEN. Reporting every 120 meant the model said nothing about itself for
                # two lives out of three -- a feedback interval longer than the thing it informs. But 30 was just a
                # luckier magic number: a life is a property of THIS GAME, and budget_model measures it off the bar.
                # ~4 reports per life, floored so it cannot become noise, capped so an unmeasurable life cannot
                # produce an unmeasured model.
                import budget_model as _BMi
                _iv = _BMi.get(adapter).report_interval()
                if _oti._n and _oti._n % _iv == 0:
                    _rep = _oti.report()
                    _emit(adapter, "MODEL  [every %d actions = 1/4 of a %s-action life] "
                                   "%d transitions -> %s confirmed object-laws, %s of them MOTION. "
                                   "fidelity NOW %s (lifetime %s -- kept as history, never as the gate: a model "
                                   "starts wrong and must not carry its own learning period forever). "
                                   "contradiction %s. %s"
                          % (_iv, _BMi.get(adapter).one_life() or "?",
                             _rep.get("transitions"), _rep.get("object_rules_confirmed"), _rep.get("motion_rules"),
                             _rep.get("fidelity"), _rep.get("fidelity_lifetime"), _rep.get("contradiction_rate"),
                             "IDENTIFIABLE -- may be planned over." if _rep.get("identifiable") else
                             "NOT identifiable -- I will not plan over this."),
                          once_key="model_%d" % (_oti._n // _iv))
        except Exception:
            pass
        try:
            _aid = getattr(a, "value", None)
            if _aid in (1, 2, 3, 4):
                _pa_a = _fa[2:56] if _fa is not None else _play_area(adapter)
                if _pa_b is not None and _pa_a is not None and np.array_equal(_pa_b, _pa_a):
                    adapter._nc_streak = getattr(adapter, "_nc_streak", 0) + 1      # board unchanged -> this dir is a no-op
                    _t = set(getattr(adapter, "_nc_tried", set())); _t.add(int(_aid)); adapter._nc_tried = _t
                else:
                    adapter._nc_streak = 0; adapter._nc_tried = set()               # moved -> reset the stuck state
        except Exception:
            pass
        return _r          # the STEP result. Nothing in this wrapper may reuse this name: the MODEL report
        #                    once did, on its cadence only, and the composer died on that action.

    try:
        adapter.step = _step_with_grammar
        adapter._grammar_ride_installed = True
    except Exception:
        pass


def _record_mechanic(adapter, key, value):
    """Record an induced mechanic for the gameplay in progress, and propagate only its GAME-AGNOSTIC residue -- that a
    mechanic of this kind, with this value, exists in the world at all -- into the molecule registry, where it serves
    as a prior for a board never met before. The value is filed under the mechanic, never under a game: the old
    `by_game` write ("if I ever replay this exact game, reload this") indexed knowledge by identity, which is the
    library shape this composer is specifically not. Ignores None (only confident facts transfer)."""
    if value is None:
        return
    _mechanics(adapter)[key] = value
    pats = _GLOBAL_KNOWLEDGE["patterns"].setdefault(key, [])
    if value not in pats:
        pats.append(value)


def _level_signature(g):
    """COLOUR-AGNOSTIC, NOISE-STABLE level signature for the solution cache: the target BAR's row band + the multiset
    of MEANINGFUL object TYPES (size/aspect buckets, excluding tiny <=4-cell noise that flickers between frames).
    Never colours (they remap). Must be computed on the LEVEL'S INITIAL frame (before exploration mutates it) so the
    same level re-identifies across attempts -- see adapter._level_sig, captured at level start."""
    g = np.asarray(g)
    from collections import Counter
    bar = _detect_bar(g)
    objs = [o for o in _distinct_objects(g) if o["size"] > 4]   # drop tiny noise that varies frame-to-frame
    types = Counter(_type_key(o) for o in objs)
    return (("bar", (bar[0] // 4) if bar else -1),
            ("types", tuple(sorted(types.items()))))


def _causal_map(adapter):
    """The persistent CAUSATION MAP: object-type -> causal hypothesis {effect, counts, status}. Now lives in the
    per-GAME memory so it survives game-over and carries across a game's levels and re-attempts (a type confirmed a
    pump on level 0 is still a pump on level 1, and after a game-over)."""
    return _game_mem(adapter)["causal"]


def _state_context(adapter):
    """A COARSE signature of the mutable state, for DISTINCT-CONTEXT evidence. Two probes share a context if the
    gross board is the same -- so repeated cold probes under an UNMET precondition (state unchanged) count as ONE
    datum, not many. Coarse (modal colour over a 6x6 block grid of the play area, HUD excluded) so pixel noise and
    the action counter don't spuriously split contexts."""
    try:
        g = _perceive_grid(adapter)
        r0, r1, c0, c1 = _play_area(g)
        sub = g[max(r0, _HUD_ROWS):r1 + 1, c0:c1 + 1]
        H, W = sub.shape
        if H < 6 or W < 6:
            return hash(sub.tobytes())
        sig = []
        for i in range(6):
            for j in range(6):
                blk = sub[i * H // 6:(i + 1) * H // 6, j * W // 6:(j + 1) * W // 6]
                sig.append(int(np.bincount(blk.ravel()).argmax()) if blk.size else -1)
        return hash(tuple(sig))
    except Exception:
        return None


def _causal_status(h):
    n = h["n_tested"]
    if n == 0:
        return "unknown"
    if h["n_effect"] < n:
        return "conditional"                                   # mixed evidence -> holds only under some conditions
    if n >= 3:
        return "confirmed"                                     # all consistent + enough evidence -> trust it
    return "supported" if n >= 2 else "conjectured"


def _update_causal(adapter, tkey, reduced, changed, rc=None, region=None):
    """Vet the causal hypothesis for object-type `tkey` against a fresh observation, WITH ANOMALY-DRIVEN REFINEMENT.
    Effect ranks reduce > change > inert. The core scientific move: a hypothesis 'all type-X do A' is REFUTED the moment
    one instance doesn't -- so when an instance's effect DISAGREES with the others of its type (a same-type button that
    drains a DIFFERENT region, or does nothing), that contradiction is an ANOMALY. It is NOT dismissed as noise or taken
    as ground truth; the hypothesis is SPLIT from 'all do A' into 'some do A, others do B', discriminated by the effect
    REGION (position / what each affects). A split type is never collapsed or type-generalized again -- each instance is
    reasoned about on its own effect. This anomaly->investigate->refine procedure is general and persists in the causal
    memory, because cause-and-effect can change level to level."""
    obs = "reduce" if reduced else ("change" if changed else "inert")
    rank = {"reduce": 2, "change": 1, "inert": 0}
    m = _causal_map(adapter)
    h = m.get(tkey)
    if h is None:
        h = m[tkey] = {"effect": obs, "n_tested": 0, "n_effect": 0, "instances": {}, "regions": {}, "split": False}
    h.setdefault("instances", {}); h.setdefault("regions", {}); h.setdefault("split", False)
    h["n_tested"] += 1
    if rc is not None:
        h["instances"][rc] = obs
        if region is not None:
            h["regions"][rc] = region
        # ANOMALY -> SPLIT: instances of one type are a distinct causal pathway if they (a) disagree on effect LABEL, or
        # (b) act on effect REGIONS that are far apart (button_L drains the LEFT region, button_R the RIGHT -- same
        # type, different what-it-affects). Either contradicts 'all type-X do the same thing' and forces a split.
        split = len(set(h["instances"].values())) > 1
        regs = [v for v in h["regions"].values() if v is not None]
        if len(regs) >= 2:
            maxd = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a in regs for b in regs)
            if maxd > 8:                                       # effect regions far apart -> distinct pathways
                split = True
        if split and not h["split"]:                          # NEWLY split -> narrate the anomaly refinement in grammar
            _emit(adapter, "SPLIT  type%s := MAP(a→region_A) \u2295 MAP(b→region_B)  [BECAUSE same type, effect-regions diverge \u2192 distinct pathways]" % (tkey,))
            # The 'all type-X do one thing' binding just broke -> localize it. A split is a
            # confirmed anomaly (an instance contradicted the type), so sharpness is high.
            _pe_pub(adapter, "causal", tkey, "one-pathway", "two-pathways",
                    sharpness=1.0, note="anomaly-split: same type, effect-regions diverge")
        if split:
            h["split"] = True                                  # 'some do A here, others do B there' -- keep distinct
    if rank[obs] > rank[h["effect"]]:                          # stronger effect than claimed -> re-anchor
        h["effect"] = obs; h["n_effect"] = 1
    elif obs == h["effect"]:
        h["n_effect"] += 1                                     # agreement -> toward confirmed
    h["status"] = "split" if h["split"] else _causal_status(h)
    return h


def _interleaved_solve(adapter, disc, budget, depth_cap=12):
    """OBJECTIVE-FIRST INTERLEAVED SOLVE for irreversible click games (vc33). The decisive constraint: information and
    commitment are the SAME action -- observing a one-shot control fires it, and with resets disabled that cannot be
    undone. So there is no separate blind probe; the objective is present from the start (induced from the static
    frame) and EVERY click is chosen against it and recorded as evidence.

    A control is NOT judged on a single click. Each control is clicked REPEATEDLY to map its full effect RANGE (its
    min->max bound): a pump moves the puck a little per click and only shows an objective reduction after several
    presses, while a one-shot changes once then saturates and a dud never changes at all. So the loop keeps pressing a
    control while it still changes the world (exploring its range) and abandons it only once it SATURATES (the frame
    stops changing) or hits the depth cap. The net reduction each control achieves becomes its effect model; a second
    pass re-drives the controls that modelled a reduction, best first.

    No resets. Returns (best_discrepancy, actions_spent, solved, model)."""
    located = list(adapter.pointer_actions()) if hasattr(adapter, "pointer_actions") else []
    if not located:
        return None, 0, False, {}
    clickA = located[0]; base = getattr(adapter, "_lvlbase", 0)
    _D = {"disc": disc}                                        # MUTABLE objective: re-inducible once motion reveals pucks
    _send_ok = [True]                                          # did the last control's clicks actually EXECUTE? (server-error guard)
    motion = []                                               # change-centroid log -> the motion that reveals movables
    regions = {}                                              # (r,c) -> effect region centroid: the MAP correspondence
    from collections import Counter as _Counter
    fluid_votes = _Counter()                                  # colours that MOVE under pumping -> the fluid/fill colour
    fluid_cells = set()                                       # cells that CHANGE under pumping -> dynamic fluid (not pillars)
    _pa = _play_area(_perceive_grid(adapter))
    _bg_pa = int(np.bincount(_perceive_grid(adapter)[_pa[0]:_pa[1] + 1, _pa[2]:_pa[3] + 1].ravel()).argmax())

    def _h():
        return float(_D["disc"].measure(_perceive_grid(adapter)))

    def _click(r, c):
        # The adapter now handles GAME_OVER (resets to a fresh session) and never latches on a transient error. Here we
        # only report whether the click landed on a LIVE session (`ok`); a non-live result (game-over / reset / send
        # error) is NOT a game signal and must not be read as 'inert'.
        _, rew, dn, info = _apply(adapter, (clickA, int(r), int(c)))
        st = str((info or {}).get("state") if isinstance(info, dict) else "").upper()
        ok = ("OVER" not in st) and (st not in ("API_NONE", "DEADLINE"))
        _ctr = getattr(adapter._obs, "levels_completed", 0) or 0
        won = _ctr > base
        if ok and _ctr > _game_mem(adapter).get("_seen_counter", base):   # counter JUST incremented -> capture the flip
            _raw = np.array(getattr(adapter._obs, "frame", []))            # frame. It is MULTI-LAYER: the aligned WIN-STATE
            _layers = list(_raw) if _raw.ndim == 3 else [_raw]             # is an EARLY layer, not frame[-1] (what _grid uses)
            _game_mem(adapter)["_win_layers"] = [np.asarray(l).copy() for l in _layers]
            _game_mem(adapter)["_seen_counter"] = _ctr
        return rew, dn, won, ok

    g0 = _perceive_grid(adapter)
    cands = sorted(_distinct_objects(g0), key=lambda o: o["size"])   # small controls (likely buttons) first
    try:                                                      # BOARD-CHECK (game-agnostic per-level sanity line)
        _pa = _play_area(g0)
        _hist = {int(c): int((g0 == c).sum()) for c in np.unique(g0)}
        _emit(adapter, "BOARD-CHECK  level=%s  play_area=%dx%d  objects=%d  colours=%s"
              % (getattr(adapter._obs, "levels_completed", "?"),
                 _pa[1] - _pa[0] + 1, _pa[3] - _pa[2] + 1, len(cands), dict(sorted(_hist.items()))),
              once_key="board_check")
    except Exception:
        pass
    cmap = _causal_map(adapter)
    total = 0; best = _h(); model = {}
    _h0 = best                                                # initial objective distance (for the plateau attribution)
    sig = getattr(adapter, "_level_sig", None) or _level_signature(g0)   # stable sig captured at level start
    # SCOPED CACHE INVALIDATION (per-level, provenance by sig): a level that has been re-attempted and is NOT won is a
    # level we are STUCK on -- its own confirmed-inert verdicts are suspect (a skipped control may be conditional, its
    # precondition never met). On such a level, RE-OPEN confirmed-inert (re-test, let PASS 3 catch a conditional unlock).
    # A WON level (sig in solutions) is NEVER re-opened -- so this can never touch a working level (the earlier global
    # mistake). First attempt uses the confident skip; only a repeatedly-failing level re-opens its own negatives.
    _att = _game_mem(adapter).setdefault("level_attempts", {})
    _att[sig] = _att.get(sig, 0) + 1
    _stuck_level = (_att[sig] >= 2) and (sig not in _game_mem(adapter).get("solutions", {}))
    if _stuck_level:
        _emit(adapter, "STRATEGY  level STUCK (>=2 attempts, still unsolved) -> a game-over just means the action budget "
              "ran out; DON'T replay the failed sequence -- spend THIS life probing UNTRIED controls so the causal map "
              "COMPLETES across game-overs, then induce the objective from the full map", once_key="stuck_strategy")
    if _stuck_level:
        # STRATEGY (game-over = the game's action budget ran out): don't replay the failed sequence -- spend THIS life
        # probing UNTRIED controls, so the causal map COMPLETES across game-overs (life 1 covers some controls, life 2
        # the ones it never reached, ...). INSTANCE-aware, because all buttons can share ONE type: prioritise a control
        # whose specific CELL has no observation yet over one already probed. Scoped to stuck levels only -> winning
        # levels (solved on life 1, never stuck) are structurally untouched.
        def _covp(o):
            _rc = (int(round(o["centroid"][0])), int(round(o["centroid"][1]))); _tk = _type_key(o)
            _h = cmap.get(_tk)
            if _h is None:
                return 3.0                                     # untried TYPE -> most information
            if _rc not in _h.get("instances", {}):
                return 2.5                                     # untried INSTANCE of a known type (e.g. the last buttons) -> cover it
            return 0.5                                         # already-probed instance -> don't re-burn the budget replaying it
        cands.sort(key=lambda o: -_covp(o))
        try:
            _covered = sum(len((h or {}).get("instances", {})) for h in cmap.values() if isinstance(h, dict))
            _emit(adapter, "COVERAGE-PROBE  stuck life %d: probing UNTRIED controls first (%d control-instances covered so far this game)"
                  % (_att[sig], _covered), once_key="cov_probe")
        except Exception:
            pass

    _coverage_complete = False                                # INDUCTION TRIGGER: has coverage crossed 'every control probed'?
    if _stuck_level:
        try:
            _cov, _nctrl, _coverage_complete = _coverage_state(cands, cmap, _type_key)
            _emit(adapter, "COVERAGE  %d/%d control-instances probed across lives%s"
                  % (_cov, _nctrl, "  ->  COMPLETE: induce the objective from the full causal map (stop probing, start solving)"
                     if _coverage_complete else "  (still probing)"), once_key="coverage_state")
        except Exception:
            _coverage_complete = False

    def _win(t):
        # cache the COMPRESSED solution -- the reducer controls (the pumps that actually moved the objective), keyed by
        # the colour-agnostic level signature -- so a later attempt can REPLAY this beaten level fast (component 2)
        # instead of re-solving it, preserving actions for the frontier.
        reducers = [rc for rc in model if model[rc]["delta"] > 1e-9]
        if reducers:
            _game_mem(adapter)["solutions"][sig] = list(reducers)
        if fluid_votes:                                        # TRANSFER LEARNING: record the fill/fluid colour that
            _record_mechanic(adapter, "fluid_color", fluid_votes.most_common(1)[0][0])   # transfer: propagate to all levels/games
        _emit(adapter, "OUTCOME  SATISFIED(objective) \u2192 WIN  [%d actions; solution compressed to %d reducer-controls]" % (t, len(reducers)))
        try:                                                   # GENERIC WIN-CONDITION INDUCTION: learn the OBJECTIVE from the
            _ring = [g0] + _game_mem(adapter).get("_win_layers", [])   # level-start (violated) + every layer of the flip
            _wc = _induce_win_condition(_ring, _GLOBAL_KNOWLEDGE["patterns"])   # frame (an early layer holds the aligned win)
            if _wc.get("_added"):
                _emit(adapter, "COMPOSE  win-condition grew by %s  [a newly-discriminating predicate AND-ed in -- the "
                      "objective can gain conditions across levels]" % (_wc["_added"],))
            if _wc.get("_pruned"):
                _emit(adapter, "PRUNE  dropped %s from win-condition  [did not re-confirm on >=half of wins -> a lucky "
                      "correlate, not the true condition]" % (_wc["_pruned"],))
            if _wc.get("formula"):
                _emit(adapter, "INDUCE  win-condition := %s  [%s -- learned from the win itself (violated->satisfied), "
                      "not asserted; carries to the next level as the goal]"
                      % (" \u2227 ".join(_wc["formula"]),
                         ", ".join("%s confirmed \u00d7%d" % (n.split("(")[0], _wc["conf"][n]) for n in _wc["formula"])))
                # NARRATE the session's new machinery into the frame data (DSL mandate: nothing may happen silently) --
                # each line generated from the actual measured state so it cannot drift from behaviour.
                _vr = _wc.get("_vcs")
                if _vr is not None and not _vr.get("kept"):
                    _emit(adapter, "RESTRUCTURE  win-condition prune REVERTED  [would orphan %d verified predictions -- "
                          "self-reverting composer kept the invariant]" % _vr.get("orphaned", 0))
                _tr = _wc.get("_tropism")
                if _tr and _tr.get("top"):
                    _emit(adapter, "RANK  win-questions by info-gain: top=%s (MI=%.2f%s)  [binary-search hypothesis space "
                          "-- most-discriminating question first]"
                          % (_tr["top"].split("(")[0], _tr.get("score", 0.0), ", decisive" if _tr.get("decisive") else ", spread"))
                elif _tr:
                    _emit(adapter, "RANK  win-questions by info-gain: no decisive split this ring  [stay in spread -- "
                          "probe more before committing]")
                try:
                    import regime_factory as _RFn
                    _rm = getattr(_RFn.SHARED, "resonance_market", None)
                    if _rm is not None and _wc.get("formula"):
                        _res = _rm.resonance(_wc["formula"][0])
                        if _res >= 2:
                            _emit(adapter, "RESONANCE  %s: %d independent derivations converge  [cross-source agreement "
                                  "amplifies -- v4 accelerant at n=1]" % (_wc["formula"][0].split("(")[0], _res))
                    _mk = getattr(_RFn.SHARED, "hypothesis_market", None)
                    if _mk is not None and len(_mk.ranked()) >= 2:
                        _w = _mk.winner()
                        _emit(adapter, "MARKET  %d competing objective-hypotheses, winner=%s  [micro-HGT: express-before-"
                              "judge, fitness=-surprise (Friston)]" % (len(_mk.ranked()), _w.split("(")[0] if _w else "?"))
                except Exception:
                    pass
        except Exception:
            pass
        return _h(), t, True, model

    p1_budget = int(budget * 0.6)                              # reserve budget for conditional (precondition) re-testing

    # FAST REPLAY (component 2): if this level's signature is cached from an earlier attempt, drive its known
    # reducer-controls DIRECTLY -- no exploration, no bound-mapping of duds -- to reproduce the win in minimal actions
    # and free the saved budget for the frontier. VERIFIED, not trusted: if the replay does not advance the level, fall
    # straight through to the full solve below (the cache is a fast first guess, never assumed correct).
    cached = _game_mem(adapter)["solutions"].get(sig)
    if cached:
        for (r, c) in cached:
            if total >= budget:
                break
            while total < budget:                              # drive this known control to saturation
                b_frame = _perceive_grid(adapter)
                rew, dn, won, ok = _click(r, c); total += 1
                if not ok:
                    break                                      # server/send failure -- not a game signal; stop driving
                if won or rew > 0:
                    return _h(), total, True, model            # cached solution advanced the level -> done, cheap
                if _h() < best - 1e-9:
                    best = _h()
                if not _real_diff(b_frame, _perceive_grid(adapter)).any():
                    break                                      # saturated -> next cached control
                if dn:
                    return best, total, False, model

    def _map_control(r, c, tkey=None, ocells=None):
        """Press a control to SATURATION, tracking the objective's full effect RANGE, WITH A FIDELITY GATE: if the
        causal model PREDICTS this control's type is active (reduce/change) but the first probe click shows it INERT
        here, the prediction failed -- the model is wrong for this instance -- so stop after the one-action probe
        instead of committing a full drive to a mispredicted control (measure before you build). Also abandons on 2
        no-change presses and stops at the objective plateau (no overshoot). Returns (net_red, changed, solved, done).

        COORDINATE-AGNOSTIC CLICK POINT: the exact centroid pixel may be a coordinate the server REFUSES (400) -- the
        board can be rotated / rescaled / recoloured, so the centre cell is not guaranteed clickable. Rather than
        memorise any pixel, nudge through THIS object's OWN cells (nearest-first) until one lands. The object's extent
        supplies the alternatives at runtime; nothing is hardcoded."""
        nonlocal total, best
        _cells = None; _ci = 0                                  # (retained param for compatibility; nudge no longer needed)
        start = _h(); flat = 0; depth = 0; changed = False
        best_local = start; since = 0; eff = []
        _send_ok[0] = False                                    # until a click actually executes, we have NO real observation
        _hyp = _causal_map(adapter).get(tkey) if tkey else None
        _pred_active = bool(_hyp and not _hyp.get("split") and _hyp.get("status") in ("confirmed", "supported")
                            and _hyp.get("effect") in ("reduce", "change"))
        while total < budget and depth < depth_cap and flat < 2 and since < 3:
            b_frame = _perceive_grid(adapter)
            rew, dn, won, ok = _click(r, c); total += 1; depth += 1
            if not ok:                                          # click hit a non-live session (game-over/reset/error) --
                total -= 1; depth -= 1                          # NOT a game signal: don't bill it, don't count it inert;
                break                                           # stop (the adapter resets a game-over session on its own)
            _send_ok[0] = True                                  # we got at least one REAL observation of this control
            if won or rew > 0:
                return start - _h(), changed, True, False
            a_frame = _perceive_grid(adapter)
            h = _h()
            if h < best - 1e-9:
                best = h
            if h < best_local - 1e-9:
                best_local = h; since = 0                      # objective still improving -> keep driving this control
            elif best_local < start - 1e-9:
                since += 1                                     # was useful, now PLATEAUED -> stop (no overshoot / drain-all)
            _dm = _real_diff(b_frame, a_frame)
            _rc_changed = bool(_dm.any())
            if not _rc_changed:
                flat += 1                                      # no REAL change (counter ignored) -> saturated / dud
            else:
                flat = 0; changed = True                       # real change -> keep mapping this control's range
                _d = np.argwhere(_dm)
                cen = (float(_d[:, 0].mean()), float(_d[:, 1].mean()))
                motion.append(cen); eff.append(cen)            # LOG motion (reveals pucks) + this control's effect region
                for (_yy, _xx) in _d[:60]:                     # FLUID = the non-bg colour that MOVES under pumping
                    fluid_cells.add((int(_yy), int(_xx)))      # + the dynamic cells (fluid, not static pillars)
                    for _cv in (int(b_frame[_yy, _xx]), int(a_frame[_yy, _xx])):
                        if _cv != _bg_pa:
                            fluid_votes[_cv] += 1
            if depth == 1 and _pred_active:
                # FIDELITY GATE. Publish BOTH outcomes so the causal layer's precision
                # calibrates in both directions (a layer that only ever logs misses looks
                # unreliable even when it isn't). HIT: predicted active, observed active ->
                # precision up. MISS: predicted active, observed inert -> localize the
                # failing binding (this control's causal hypothesis mispredicted here) and,
                # as before, probe only.
                _sharp = 1.0 if (_hyp and _hyp.get("status") == "confirmed") else 0.6
                if _rc_changed:
                    _pe_pub(adapter, "causal", (r, c, tkey), "active", "active", sharpness=_sharp)
                else:
                    _pe_pub(adapter, "causal", (r, c, tkey), "active", "inert",
                            sharpness=_sharp, note="fidelity-gate: predicted-active control inert here")
                    break                                      # probe only (behaviour unchanged)
            if dn:
                break
        if eff:                                                # MAP: record WHICH region this specific control affects
            regions[(r, c)] = (sum(e[0] for e in eff) / len(eff), sum(e[1] for e in eff) / len(eff))
        return start - _h(), changed, False, (total >= budget)

    # BUDGET COMPRESSION (component: preserve budget across re-attempts, even on levels not yet won): if a prior attempt
    # already identified the fluid for this level, SKIP the motion-generating exploration and build the fluid-level
    # objective directly -- the ~30% budget the motion pass costs is preserved so the re-attempt reaches further. This
    # is the "compress what you learned so you don't re-pay for it" discipline, applied to perception, not just wins.
    _learned = _game_mem(adapter).setdefault("learned", {}).get(sig)
    _skip_motion = False
    if _learned and _learned.get("fluid") is not None:
        try:
            _fobj = _fluid_level_objective(g0, _learned["fluid"])
            if _fobj is not None and float(_fobj.measure(g0)) > 1e-9:
                _D["disc"] = _fobj; best = _h(); model.clear(); _skip_motion = True
        except Exception:
            pass

    # EARLY RE-INDUCE (hidden-goal / provisional levels): pump a few controls to GENERATE MOTION, then re-induce the
    # real puck->target sub-goals and SWITCH to them BEFORE the main passes -- so the bulk of the budget drives the
    # actual objective, not the provisional bootstrap. (The trace showed the chain was correct but happened too late.)
    for o in ([] if _skip_motion else cands[:12]):
        if total >= max(8, int(budget * 0.3)):
            break
        rr, cc = int(round(o["centroid"][0])), int(round(o["centroid"][1]))
        red, changed, solved, done = _map_control(rr, cc, tkey=_type_key(o), ocells=o.get("cells"))
        _update_causal(adapter, _type_key(o), red > 1e-9, changed, rc=(rr, cc), region=regions.get((rr, cc)))
        if solved:
            return _win(total)
        if red > 1e-9:
            model[(rr, cc)] = {"delta": red, "tkey": _type_key(o)}
        if done:
            return best, total, False, model
    if motion and not _skip_motion:
        # THE MOVABLE IS THE FLUID LEVEL, not a marker. Identify the fluid colour from what actually MOVED under pumping
        # (robust -- not a static colour guess), and build the FLUID-LEVEL objective (each column's top vs its target).
        _new = None
        # TRANSFER LEARNING: think back to what SOLVED the earlier levels. Colours are consistent within a game, so the
        # fluid/fill colour that worked on levels 0/1 identifies the fluid HERE -- instead of re-deriving (and mis-
        # identifying it as the pillars) on a hard level. Verified: used only if present and it makes the objective
        # non-trivial; otherwise fall back to this level's own moved-colour, and let the causal map correct it.
        _cur = _perceive_grid(adapter)
        _fill = _mechanics(adapter).get("fluid_color")   # TRANSFER: fluid identity learned on any prior level/game
        _fluid = None
        if _fill is not None and int((_cur == _fill).sum()) > 4:
            _fluid = _fill                                     # transferred from a solved level
        elif fluid_votes:
            _fluid = fluid_votes.most_common(1)[0][0]          # else re-derive from what moved here
        if _fluid is not None:
            _game_mem(adapter).setdefault("learned", {})[sig] = {"fluid": _fluid}   # cache -> skip re-explore next attempt
            # FIXED-TARGET-VIA-MOTION: the pucks FLOAT on the fluid, so they MOVED during the pumping pass; the win-level
            # TARGETS are fixed and did NOT. Compare markers at solve-start (g0) vs now -- the ones still at their
            # original position are the fixed targets. Drive the objective toward THOSE, not the floating pucks (which
            # sit on the fluid surface and would read |fluid_top - puck| ~ 0). This completes the cascade objective.
            def _mk(g):
                return [o for o in _distinct_objects(np.asarray(g))
                        if 2 <= o["size"] <= 8 and o["colour"] not in (_fluid, _bg_pa)]
            try:
                _m0 = _mk(g0); _m1 = _mk(_perceive_grid(adapter))
                def _same(o, p):
                    return (o["colour"] == p["colour"]
                            and abs(o["centroid"][0] - p["centroid"][0]) + abs(o["centroid"][1] - p["centroid"][1]) <= 1.5)
                _moved = [o for o in _m1 if not any(_same(o, p) for p in _m0)]          # pucks: floated with the fluid
                _puck_cols = set(o["colour"] for o in _moved)                            # each puck's target shares its colour
                _fixed = [o for o in _m1 if o["colour"] in _puck_cols and any(_same(o, p) for p in _m0)]
                try:                                                                     # ROLE INDUCTION (gap #2): label by behaviour
                    _roles = _induce_roles(g0, _moved, _fixed, _fluid,
                                           actuators=[(int(round(o["centroid"][0])), int(round(o["centroid"][1])))
                                                      for o in _distinct_objects(g0) if o.get("colour") is not None][:0] or None)
                    _record_mechanic(adapter, "roles", {k: _roles[k] for k in ("fluid_colour", "boundary_colour", "puck_colours")})
                    _emit(adapter, "ROLES  fluid:=colour %s \u00b7 boundary:=colour %s \u00b7 puck\u00d7%d \u00b7 target\u00d7%d  [BECAUSE classified by DYNAMIC signature: fluid moves, pucks co-move, targets stay fixed]"
                          % (_roles.get("fluid_colour"), _roles.get("boundary_colour"), _roles.get("n_pucks"), _roles.get("n_targets")))
                except Exception:
                    pass
            except Exception:
                _fixed = None
            try:
                _new = _fluid_level_objective(g0, _fluid, targets=(_fixed or None),
                                              pucks=(_moved or None))   # match each target to its puck's column
            except Exception:
                _new = None
        if _new is None:                                       # fallback: puck->target alignment if no fluid identified
            try:
                _fp = [{"changed": True, "change_centroid": cc} for cc in motion]
                _asubs = _alignment_submeasures(g0, _fp)
                if _asubs:
                    _new = Discrepancy(lambda g: float(sum(sm(g) for (sm, _a) in _asubs)), lambda g: [])
            except Exception:
                _new = None
        if _new is not None and float(_new.measure(_perceive_grid(adapter))) > 1e-9:
            _D["disc"] = _new                                  # switch to the CORRECTED objective (the real movable)
            _record_mechanic(adapter, "objective_type", "fluid_level")   # transfer: this game uses fluid-level objectives
            _emit(adapter, "PERCEIVE  play_area := SEGMENT(frame);  fluid := colour %s  [BECAUSE it MOVES under actuation, distinct from static pillars of the same colour]" % _fluid)
            _emit(adapter, "INDUCE  objective := ALL(target_i: SAME(fluid_top(col_i), target_i))  [cascading-volume: the movable resource is the fluid LEVEL, not a marker]")
            try:                                              # Phase-4: make the objective CONSTRUCTION explicit (built from roles+volume, not menu-selected)
                _vol0 = _volume_state(g0, interaction_probe=[{"changed": True, "change_centroid": cc} for cc in motion], fluid_colour=_fluid)
                _emit(adapter, "CONSTRUCT  " + _construct_objective({"fluid_colour": _fluid}, _vol0), once_key="construct")
            except Exception:
                pass
            model.clear(); best = _h()
            # CASCADE ALLOCATOR: drive each control against the GLOBAL fluid-level objective. Because fluid is fungible,
            # draining a SURPLUS column improves the global by cascading to fill DEFICITS -- and _map_control drives
            # while the GLOBAL improves (allowing a column to temporarily over-drain), stopping at the global plateau.
            # So the greedy global drive on the CORRECT objective IS the cascade allocation.
            for o in cands:
                if total >= budget:
                    break
                r2, c2 = int(round(o["centroid"][0])), int(round(o["centroid"][1]))
                red, changed, solved, done = _map_control(r2, c2, tkey=_type_key(o), ocells=o.get("cells"))
                if solved:
                    return _win(total)
                if red > 1e-9:
                    model[(r2, c2)] = {"delta": red, "tkey": _type_key(o)}
                if done:
                    break

    # PASS 1 -- BOUND-MAP + CAUSAL-VET each control (up to p1_budget). A type CONFIRMED inert is skipped for all its
    # instances (generalisation); each control is pressed through its range; the type's causal hypothesis is vetted.
    skipped_inert = []                                         # controls skipped by type-inert generalisation -- may be
    still_inert = []                                           # controls that stay inert even after PASS-3 re-test (bound early)
    for o in cands:                                            # CONDITIONALLY gated (inert cold, active once a precondition
        if total >= p1_budget:                                # is met), so PASS 3 must still re-test them, not retire them.
            break
        r, c = int(round(o["centroid"][0])), int(round(o["centroid"][1]))
        tkey = _type_key(o)
        hyp = cmap.get(tkey)
        if hyp and hyp["status"] == "confirmed" and hyp["effect"] == "inert":
            skipped_inert.append((r, c, tkey))                 # remember it; do NOT let a cold-probe inert retire it forever
            if not _stuck_level:                               # WON/normal level: trust the skip (budget economy preserved)
                continue                                       # GENERALISE: same-type object proven inert -> skip it (for now)
            # STUCK level: re-open -- fall through and re-test, so a conditionally-gated skipped control gets a chance
        if (r, c) in model:
            continue
        red, changed, solved, done = _map_control(r, c, tkey=tkey, ocells=o.get("cells"))
        if not _send_ok[0]:                                    # the click(s) never executed (server error, not the game)
            continue                                           # -> record NO causal evidence; leave the control for retry
        _update_causal(adapter, tkey, red > 1e-9, changed, rc=(r, c), region=regions.get((r, c)))   # vet + anomaly-split
        model[(r, c)] = {"delta": red, "tkey": tkey}
        if solved:
            return _win(total)
        if done:
            return best, total, False, model

    # PASS 2 -- greedy replay on EACH CONTROL'S OWN measured effect (no blind type-mirror). Same-type controls can have
    # POSITION-SPECIFIC effects (button_L drains the left column, button_R the right) -- so a control is driven only if
    # IT individually reduced the objective, keyed by its own effect region, NOT because its type did. This is the
    # active-disambiguation fix: distinct causal pathways are kept distinct instead of collapsed into one global rule.
    # PHASE-4 CASCADE ALLOCATOR (#6): DEFINED (_cascade_sequence) but UNWIRED pending a non-regressing integration --
    # reordering the proven drive path regressed the working levels (1.91 -> 1.37). Now fired ONLY on the INDUCTION
    # TRIGGER: a stuck level whose coverage is COMPLETE (every control probed across lives). At that point the map is
    # a full picture, so we INDUCE the objective from it and drive controls SURPLUS->DEFICIT -- scoped so winning
    # levels (never stuck) and still-incomplete lives are untouched.
    drive_order = sorted((rc for rc in model if model[rc]["delta"] > 1e-9), key=lambda rc: -model[rc]["delta"])
    _fa = None                                                # corrected-model perception (for narration + commit-lock reorder)
    if _coverage_complete:
        try:
            _wobj = _win_objective(g0, _GLOBAL_KNOWLEDGE["patterns"])   # TRANSFER: apply the LEARNED win condition as the goal
            if _wobj and _wobj["pairs"]:
                _ax = "COLUMN" if _wobj["axis"] == 1 else "ROW"
                _emit(adapter, "TRANSFER  apply learned win-condition %s (conf %s) as THIS level's objective: align %d "
                      "puck(s) with their same-colour target along the %s axis  [%s]"
                      % (" \u2227 ".join(_wobj["formula"]), _wobj["conf"], len(_wobj["pairs"]), _ax,
                         "  ".join("c%d gap=%+d" % (p["colour"], p["gap"]) for p in _wobj["pairs"])),
                      once_key="transfer_wincond")
                _D["disc"] = _WinCondObjective(_GLOBAL_KNOWLEDGE["patterns"])   # OBJECTIVE := the learned win condition, so the
                best = _h()                                                     # existing drive reduces the gaps (control->puck
                _emit(adapter, "OBJECTIVE := SATISFY(learned win-condition)  [total %s-gap = %.0f; a control is now driven "
                      "iff it slides a puck toward its same-colour target -- binding discovered by the objective itself]"
                      % (_ax, best), once_key="wincond_objective")               # binding discovered via the objective)
                _cells = [{"puck": p["puck"], "target": p["target"], "gap": p["gap"],
                           "kind": "scarcity" if p["gap"] > 1 else ("surplus" if p["gap"] < -1 else "at_target")}
                          for p in _wobj["pairs"]]
                _volw = {"cells": _cells, "enough_to_cascade": True}
                _seqc = _cascade_sequence(model, regions, _volw)
                if _seqc:
                    drive_order = _seqc
                    _emit(adapter, "CASCADE  drive controls to reduce the %s-gaps toward the learned win-condition "
                          "[objective transferred from earlier wins, not re-derived]" % _ax, once_key="cascade_transfer")
                # CONSTRAINED-ALLOCATION ANALYSIS (SHARED.allocation_planner): compose the assignment the actuator
                # perceives but could not plan -- which control fills which scarcity SINK within the scarce budget -- and,
                # crucially, detect INFEASIBILITY with the BINDING sub-goal, so 'STUCK' becomes 'sub-goal X cannot be
                # filled because ...'. ADDITIVE: narrates the plan / binding constraint; does NOT reorder the proven
                # drive path (reordering regressed working levels before -- see note above). Symbolic over the causal
                # map, no grid.
                try:
                    import regime_factory as _RFa
                    _sinks = [{"id": int(round(cc["puck"][1])), "need": int(abs(cc.get("gap", 0)))}
                              for cc in _cells if cc.get("kind") == "scarcity"]
                    _sources = [{"id": int(round(cc["puck"][1])), "avail": int(abs(cc.get("gap", 0)))}
                                for cc in _cells if cc.get("kind") == "surplus"]
                    _ops = []
                    for _rc, _mv in model.items():
                        if _mv.get("delta", 0) > 1e-9:
                            _reg = regions.get(_rc) if regions else None
                            _aff = [s["id"] for s in _sinks]           # default: could serve any sink
                            try:
                                if _reg is not None and _sinks:
                                    _regc = _reg[1] if isinstance(_reg, (tuple, list)) else _reg.get("centroid", (0, 0))[1]
                                    _aff = [min(_sinks, key=lambda s: abs(s["id"] - int(_regc)))["id"]]  # nearest column
                            except Exception:
                                pass
                            _ops.append({"id": _rc, "affects": tuple(_aff), "cost": 1})
                    if _sinks:
                        _aplan = _RFa.SHARED.allocation_planner.plan(_sinks, _sources, _ops, max(1, int(budget)))
                        _emit(adapter, _RFa.SHARED.allocation_planner.narrate(_aplan), once_key="allocate")
                    # GATE-SCOPED CONSERVATION VIEW (SHARED.gate_binding + conditional_flow): colour-match flags->pucks to
                    # separate GATED columns from INERT conduits, then decide feasibility by CONSERVATION + an ORDERED
                    # see-saw schedule (highest-need-first, subordinated to most-constrained + reachability). ADDITIVE +
                    # LEGIBLE; does NOT change the drive. Guarded to run ONCE per level -- _flow_analysis does connected-
                    # components labelling, so calling it every iteration was a per-iteration cost (the disabled note).
                    _flvl = getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0
                    try:
                        _ffl = _mechanics(adapter).get("fluid_color")   # transferred fluid identity (in scope here)
                        _fa = _flow_analysis(g0, _ffl) if _ffl is not None else None   # computed each descend (for reorder)
                        if _fa and getattr(adapter, "_flow_narrated_lvl", None) != _flvl:
                            adapter._flow_narrated_lvl = _flvl          # narrate ONCE per level (the emits, not the compute)
                            _emit(adapter, _RFa.SHARED.gate_binding.narrate(_fa["binding"]), once_key="gatebind_%d" % _flvl)
                            _emit(adapter, "FLOW  fill-axis %s (orientation-free); %d puck(s), %d marker(s); net "
                                  "alignment demand %.1f, %d unaligned" % (_fa["axis"], len(_fa["pucks"]),
                                  len(_fa["markers"]), _fa["feasible"]["net_demand"], _fa["feasible"]["n_unaligned"]),
                                  once_key="flow_%d" % _flvl)
                            _emit(adapter, _RFa.SHARED.conditional_flow.narrate_schedule(_fa["schedule"]),
                                  once_key="flowsched_%d" % _flvl)
                            _emit(adapter, "EDGES  button transfer-graph (donor col -> receiver col; conserved flow "
                                  "on a line): %s  [%d buttons; end columns asymmetric -- first has right-only, last "
                                  "left-only]" % (_fa["edges"], len(_fa["buttons"])), once_key="edges_%d" % _flvl)
                            # MODEL-COHERENCE (Gap 3): validate the role-labeling is internally coherent (auto-reject a
                            # salience decoy). MODEL-DOUBT (Gaps 1&4): if the objective residual is STRUCTURED+PERSISTENT
                            # (pucks not closing under this model), the MODEL is suspect -> enumerate MECHANICS-HYP.
                            _emit(adapter, _RFa.SHARED.coherence.narrate_model(_fa["labeling"]),
                                  once_key="modelcoh_%d" % _flvl)
                            _RFa.SHARED.model_doubt.bind_store(_GLOBAL_KNOWLEDGE.setdefault("model_doubt", {}))
                            _mkey = "%s:actuator" % _session_key(adapter)   # this gameplay, not this game's name
                            _nun = _fa["feasible"]["n_unaligned"]
                            _RFa.SHARED.model_doubt.observe(_mkey, float(_nun), signature="unaligned")
                            if _RFa.SHARED.model_doubt.is_structured(_mkey):
                                _emit(adapter, _RFa.SHARED.model_doubt.narrate(_mkey), once_key="modeldoubt_%d" % _flvl)
                                _emit(adapter, _RFa.SHARED.mechanics_hypotheses.narrate(
                                      _RFa.SHARED.mechanics_hypotheses.enumerate(
                                          applied=["ROLE_BY_FUNCTION", "CORRESPONDENCE", "PARTITION",
                                                   "ATTRIBUTE_SPLIT", "OPERATOR_RELATION"])),
                                      once_key="mechhyp_%d" % _flvl)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass
    # STEP 3 -- COMMIT-AND-LOCK drive order from the FLOW-SCHEDULE (the anti-oscillation fix). This is a pure REORDERING
    # of the SAME controls in `drive_order` (it cannot press anything the old path could not), turning delta-greedy
    # sloshing into a per-puck monotone descent: the schedule's target puck's controls are driven FIRST (in gap order),
    # and controls that feed an already-aligned puck's column are deprioritised (~locked, never re-opened first). A
    # control is linked to a puck column by its measured effect-region x. Scoped to coverage-complete; the old
    # delta-sorted order is the fallback whenever no schedule/target exists, so working levels are untouched.
    if _coverage_complete and _fa is not None and _fa.get("schedule", {}).get("order") and _fa.get("fcols"):
        try:
            _sched = _fa["schedule"]; _fcolx = _fa["fcols"]
            _pcolx = {p["id"]: _fcolx[p["col"]] for p in _fa["pucks"] if 0 <= p["col"] < len(_fcolx)}
            _order_cols = [_pcolx[pid] for pid in _sched["order"] if pid in _pcolx]     # commit-and-lock column order

            def _ctrl_x(rc):
                reg = regions.get(rc)
                if reg is None:
                    return None
                return reg[1] if isinstance(reg, (tuple, list)) else reg.get("centroid", (0, 0))[1]

            def _rank(rc):
                cx = _ctrl_x(rc)
                if cx is None or not _order_cols:
                    return (len(_order_cols) + 1, 0.0)         # unknown-column controls after the scheduled ones
                dists = [abs(cx - ocx) for ocx in _order_cols]
                i = int(np.argmin(dists))
                return (i, dists[i])                            # rank by position in the commit-and-lock order
            _reordered = sorted(drive_order, key=_rank)
            if _reordered and len(_reordered) == len(drive_order):
                drive_order = _reordered
                _emit(adapter, "DRIVE-COMMIT  drive-order set to the commit-and-lock schedule: serve target puck %s "
                      "first (largest admissible gap), then in gap order; controls feeding aligned pucks deprioritised "
                      "-> monotone per-puck descent, not delta-greedy sloshing" % str(_sched["target"]),
                      once_key="drivecommit_%d" % _flvl)
        except Exception:
            pass
    # GAP TRACE setup (the honest anti-oscillation criterion): identify the schedule's target puck (colour + marker +
    # column) so a press to its column can re-measure and narrate its signed gap -- we want to SEE it go monotone to 0
    # then LOCK, or catch a bounce. Additive; no drive change.
    _trace = None
    if _coverage_complete and _fa is not None and _fa.get("schedule", {}).get("target") is not None and _fa.get("fcols"):
        try:
            _tid = _fa["schedule"]["target"]
            _tp = next((p for p in _fa["pucks"] if p["id"] == _tid), None)
            _tm = _fa["binding"]["gated"].get(_tid, {}).get("target")
            if _tp is not None and _tm is not None and 0 <= _tp["col"] < len(_fa["fcols"]):
                _trace = {"colour": _tp["colour"], "marker": _tm, "axis": _fa["axis"],
                          "fluid": _mechanics(adapter).get("fluid_color"),
                          "col_x": _fa["fcols"][_tp["col"]], "n": 0, "last": None}
        except Exception:
            _trace = None
    p2_budget = int(budget * 0.85)                            # RESERVE ~15% for PASS 3: driving the working controls to
    _committed_drive = False
    # FULL COMMIT-AND-LOCK drive (scoped to coverage-complete with a schedule): serve pucks ONE AT A TIME in the SWEEP
    # order, driving each to alignment (gap~0) before the next, LOCK it, never re-open. A flow-derived sweep means once
    # the accumulation-end puck is aligned it is never pulled from again. The old flat drive_order loop is the fallback.
    if _coverage_complete and _fa is not None and _fa.get("schedule", {}).get("order") and _fa.get("fcols"):
        try:
            _fluidc = _mechanics(adapter).get("fluid_color")
            _order = _fa["schedule"]["order"]; _by_id = {p["id"]: p for p in _fa["pucks"]}
            _spacing = abs(_fa["fcols"][1] - _fa["fcols"][0]) if len(_fa["fcols"]) > 1 else 8
            _locked = set(); _committed_drive = True
            _emit(adapter, "DRIVE-SWEEP  serialised commit-and-lock in sweep direction %s: one puck to alignment then "
                  "LOCK, never re-opened (no more balancing all pucks at once)" % _fa.get("sweep_dir"),
                  once_key="drivesweep_%d" % _flvl)
            for _pid in _order:
                if total >= p2_budget:
                    break
                _p = _by_id.get(_pid); _marker = _fa["binding"]["gated"].get(_pid, {}).get("target")
                if _p is None or _marker is None:
                    continue
                _colx = _fa["fcols"][_p["col"]] if 0 <= _p["col"] < len(_fa["fcols"]) else None
                # SERVED CONTROLS = the puck's column PLUS its DONOR CHAIN toward the fluid source. On a conserved line,
                # pulling into a column drains its donor, so to close the puck we must also restage the chain that feeds
                # it (fixes the donor-drainage stall, not just 'too few presses'). Chain direction from the edge donors.
                _pc = _p["col"]; _chain = {_pc}
                _donors = [d for (d, r) in _fa["edges"] if r == _pc]
                if _donors:
                    _dir = 1 if max(_donors) > _pc else -1
                    _cc = _pc
                    while 0 <= _cc < len(_fa["fcols"]):
                        _chain.add(_cc); _cc += _dir
                _chain_x = [_fa["fcols"][c] for c in sorted(_chain) if 0 <= c < len(_fa["fcols"])]
                _pctrls = [rc for rc in drive_order if (rc in model) and _ctrl_x(rc) is not None
                           and any(abs(_ctrl_x(rc) - cx) <= _spacing * 0.6 for cx in _chain_x)]
                if not _pctrls and _colx is not None:          # fallback: at least the puck's own column
                    _pctrls = [rc for rc in drive_order if (rc in model) and _ctrl_x(rc) is not None
                               and abs(_ctrl_x(rc) - _colx) <= _spacing + 2]
                _last = None; _stall = 0; _ci = 0
                _puck_budget = min(len(_pctrls) * 2 + 6, 18)   # commit HARDER (close the puck) but cap so one can't balloon
                _spent0 = total
                for _rep in range(16):                         # more reps: a gap of ~12 needs ~6 effective presses to lock
                    if total >= p2_budget or not _pctrls or (total - _spent0) >= _puck_budget:
                        break
                    _gp = (_puck_gap_now(adapter, _p["colour"], _marker, _fa["axis"], _fluidc)
                           if _fluidc is not None else None)
                    if _gp is not None and (_last is None or abs(_gp - _last) > 0.5):
                        _d = "" if _last is None else (" (closing)" if abs(_gp) < abs(_last) - 0.5
                             else " (BOUNCE)" if abs(_gp) > abs(_last) + 0.5 else " (flat)")
                        _emit(adapter, "GAP  puck %s signed gap = %+.1f%s  [align at 0 -> LOCK]" % (str(_pid), _gp, _d),
                              once_key="gap_%d_%s_%d" % (_flvl, str(_pid), _rep))
                    if _gp is not None and abs(_gp) <= 1.0:
                        _locked.add(_pid)
                        _emit(adapter, "GAP  puck %s ALIGNED -> LOCK (commit-and-lock: not re-opened)" % str(_pid),
                              once_key="gaplock_%d_%s" % (_flvl, str(_pid)))
                        break
                    if _gp is not None and _last is not None and abs(_gp) >= abs(_last) - 0.5:
                        _stall += 1
                        if _stall >= 4:                        # allow flat spots while the donor chain re-stages
                            _emit(adapter, "GAP  puck %s STALLED (no progress even after restaging) -> next in sweep"
                                  % str(_pid), once_key="gapstall_%d_%s" % (_flvl, str(_pid)))
                            break
                    else:
                        _stall = 0
                    if _gp is not None:
                        _last = _gp
                    (r, c) = _pctrls[_ci % len(_pctrls)]; _ci += 1   # ONE control per rep (finer cadence), cycling
                    if (r, c) in model:
                        red, changed, solved, done = _map_control(r, c, tkey=model[(r, c)]["tkey"])
                        if solved:
                            return _win(total)
                        if done:
                            return best, total, False, model
        except Exception:
            _committed_drive = False
    if not _committed_drive:                                   # FALLBACK + working levels: the proven flat drive
        for (r, c) in drive_order:
            if total >= p2_budget:
                break
            if (r, c) not in model:
                continue
            red, changed, solved, done = _map_control(r, c, tkey=model[(r, c)]["tkey"])
            if solved:
                return _win(total)
            if done:
                return best, total, False, model

    # PASS 3 -- CONDITIONAL / PRECONDITION discovery (the causal-dependency-graph probe). A control that looked inert
    # may have been GATED: its effect unlocks only after other controls changed the state. PASS 1/2 advanced the state,
    # so RE-TEST the previously-inert controls now. Any that reduce the objective NOW were conditional -- upgrade their
    # type from 'inert' to 'conditional_reduce' (it holds under a precondition), record it, and exploit. This is the
    # first-order T(a | precondition) that greedy per-control mapping structurally cannot see.
    # PHASE-2b SURPRISE GATE (System-2 effort follows surprise, not the clock): the conditional re-test is the
    # expensive sweep. Run it only when the bus carries a CONFIDENT unresolved binding error worth chasing
    # (e.g. L2's causal split, conf 0.5 -> deliberate). If surprise is low (nothing flagged), COAST -- skip it.
    # Fail-open (deliberate on any bus error); a no-op on the working levels, which win before PASS 3.
    _deliberate = True
    try:
        if _pe is not None:
            _deliberate = bool(_pe.should_deliberate(_game_mem(adapter)))
    except Exception:
        _deliberate = True
    if not _deliberate:
        _emit(adapter, "COAST  surprise low -> skip conditional re-test (no confident unresolved binding error to chase)")
    _retest = ([rc for rc in model if model[rc]["delta"] <= 1e-9]) if _deliberate else []
    _retest += ([(r, c) for (r, c, _t) in skipped_inert if (r, c) not in model]) if _deliberate else []   # incl. type-skipped (maybe conditional)
    _tkeys = {(r, c): model.get((r, c), {}).get("tkey") for (r, c) in model}
    for (r, c, _t) in skipped_inert:
        _tkeys.setdefault((r, c), _t)
    still_inert = []
    for (r, c) in _retest:
        if total >= budget:
            still_inert.append((r, c)); continue               # ran out before re-testing -> leave it UNCONFIRMED, not inert
        red, changed, solved, done = _map_control(r, c, tkey=_tkeys.get((r, c)))
        if not _send_ok[0]:                                    # re-test click never executed (server error) -- leave it
            still_inert.append((r, c)); continue               # UNCONFIRMED (not a game inert), so it's re-tried, not retired
        if solved:
            return _win(total)
        if red > 1e-9:                                         # inert on cold probe, effective NOW -> conditional (unlocked)
            tkey = _tkeys.get((r, c))
            h = cmap.get(tkey)
            if h is not None:
                h["effect"] = "conditional_reduce"; h["n_effect"] = 1; h["status"] = "conditional"
            model[(r, c)] = {"delta": red, "tkey": tkey}
            _emit(adapter, "UNLOCK  control@(%d,%d) was inert on a cold probe, REDUCES after state advanced -> conditional (precondition met)" % (r, c))
            _pe_pub(adapter, "causal", (r, c, tkey), "reduce", "reduce", sharpness=0.8)  # HIT: resolves this control's error + calibrates precision up
        else:
            still_inert.append((r, c))                          # re-tested AFTER state advanced, still inert -> genuinely inert
        if done:
            break
    # RE-INDUCE FROM MOTION (reveal pucks under fluid flow): PASS 1-3 pumped and LOGGED where the world moved. Those
    # motion centroids identify which markers are movable pucks -- so re-induce the ARITY-INVARIANT multigoal objective
    # with that motion. If it surfaces still-unsatisfied sub-goals (puck->flag pairs the static frame couldn't role-
    # assign), switch to the fuller objective and drive the revealed controls toward them. One extra round (bounded).
    if motion and total < budget:
        try:
            fake_probe = [{"changed": True, "change_centroid": cc} for cc in motion]
            align_subs = _alignment_submeasures(g0, fake_probe)   # did the pumping reveal puck->target sub-goals?
        except Exception:
            align_subs = []
        if align_subs:
            new_d = Discrepancy(lambda g: float(sum(sm(g) for (sm, _a) in align_subs)), lambda g: [])
            if float(new_d.measure(_perceive_grid(adapter))) > 1e-9:
                _D["disc"] = new_d                             # switch to the fuller, motion-revealed puck objective
                best = _h()
                for o in cands:                                # one more bound-map + exploit round on the new sub-goals
                    if total >= budget:
                        break
                    r, c = int(round(o["centroid"][0])), int(round(o["centroid"][1]))
                    red, changed, solved, done = _map_control(r, c, tkey=_type_key(o), ocells=o.get("cells"))
                    if solved:
                        return _win(total)
                    if red > 1e-9:
                        model[(r, c)] = {"delta": red, "tkey": _type_key(o)}
                    if done:
                        break
    # LOCALIZED ATTRIBUTION -- COVERAGE BEFORE OBJECTIVE. The plateau is NOT an objective problem
    # while controls remain UNCONFIRMED: probed inert on a cold press and still inert after the state
    # advanced, OR never re-reached within budget (the B3 case -- a conditionally-gated transfer
    # button abandoned after one probe). You cannot conclude the objective is incomplete while
    # controls are still untested. So localize to CONTROL-COVERAGE first; blame the objective only
    # once every control is confirmed and it STILL plateaus.
    if best > 1e-9:
        # ACTUATOR FILTER (re-scoped A -- no pillars to separate; the pollution is fluid pools/borders/markers
        # counted as controls). Count untested ACTUATORS, not every distinct object: the fluid is the RESOURCE and
        # large bodies are structure -- clicking them is not a control test. Exclude the induced fluid colour and
        # large bodies; keep small non-fluid objects (button-like). Uses the induced fluid colour -> game-agnostic.
        _obj_at = {(int(round(o["centroid"][0])), int(round(o["centroid"][1]))): o for o in cands}
        _paf = _play_area(g0); _pa_area = max(1, (_paf[1] - _paf[0] + 1) * (_paf[3] - _paf[2] + 1))
        def _is_actuator(rc):
            o = _obj_at.get(rc)
            if o is None:
                return True                                    # unknown centroid -> don't over-filter
            if _fluid is not None and o.get("colour") == _fluid:
                return False                                   # the fluid is the resource, not a control
            if o.get("size", 0) > 0.03 * _pa_area:
                return False                                   # a large body (pool/column/wall) is not a button
            return True
        _all_inert = list(dict.fromkeys(still_inert))
        _unconfirmed = [rc for rc in _all_inert if _is_actuator(rc)]
        _filtered = len(_all_inert) - len(_unconfirmed)
        if _unconfirmed:
            _pe_pub(adapter, "causal", "conditional_coverage", "all-actuators-confirmed",
                    "%d-actuators-inert-unconfirmed" % len(_unconfirmed), sharpness=1.0,
                    note=("%d ACTUATOR(s) read inert on a cold probe and were NOT confirmed after the state "
                          "advanced (%d non-control objects -- fluid/borders/markers -- filtered out) -> test "
                          "these (may be conditionally gated) BEFORE concluding the objective is incomplete"
                          % (len(_unconfirmed), _filtered)))
        else:
            _progressed = (_h0 - best) > 1e-9                  # coverage COMPLETE -> a plateau is now genuinely an
            _pe_pub(adapter, "objective", "solve_objective", 0.0, round(float(best), 2),   # objective-model gap
                    sharpness=(1.0 if _progressed else 0.5),
                    note=("plateau after descent %.1f->%.1f, all actuators confirmed: objective incomplete "
                          "(needs sequencing)" % (_h0, best)) if _progressed
                         else "no descent, all actuators confirmed: error below the objective layer")
        _reflex(adapter)                                       # Phase-2: route the top PERSISTENT binding error to its refine
    return best, total, False, model


def _exploit_triggers(adapter, disc, interaction_probe, budget, burst=3):
    """The induction+EXPLOIT loop (C1 consumer): turn discovered triggers into a solve. The probe found which clicks
    react; this asks the objective which of them HELP. Each trigger is tested with a short BURST (not a single click),
    because a control may be slow -- a pump often needs several clicks to move the puck one detectable cell, so a
    one-click test reads as 'no effect' even for the correct control. A trigger whose burst reduces the objective is a
    useful control; the loop then ACCUMULATES on the improving triggers until the objective is met, none help, or
    budget runs out. It never needs to understand the hidden mechanic -- 'this trigger reduces the distance to the
    goal' is a sufficient, colour-agnostic signal. (When even bursts don't help, the control is sequential and needs
    the Simulator's forward model -- see the simulation doc; this loop is the greedy substrate beneath that.)

    Returns (best_discrepancy, actions_spent, solved). No resets (globally disabled); stops on reward/GAME_OVER."""
    reactive = [x for x in (interaction_probe or []) if x.get("changed")]
    if not reactive:
        return None, 0, False
    base = getattr(adapter, "_lvlbase", 0)
    def _h():
        return float(disc.measure(_perceive_grid(adapter)))
    total = 0; best = _h()
    improving = []
    for x in reactive:                                         # INDUCE: burst-test which triggers reduce the objective
        if total >= budget:
            break
        r, c = x["click"]; before = _h()
        for _ in range(burst):
            if total >= budget:
                break
            _, rew, dn, _ = _apply(adapter, ('click', int(r), int(c))); total += 1
            if rew > 0 or (getattr(adapter._obs, "levels_completed", 0) or 0) > base:
                return _h(), total, True
            if dn:
                return _h(), total, False
        after = _h()
        if after < before - 1e-9:
            improving.append((int(r), int(c), before - after)); best = min(best, after)
    improving.sort(key=lambda t: -t[2])                        # steepest-descent triggers first
    stall = 0                                                  # EXPLOIT/ACCUMULATE: hammer improving triggers
    while improving and total < budget and stall < len(improving):
        progressed = False
        for (r, c, _d) in improving:
            if total >= budget:
                break
            before = _h()
            _, rew, dn, _ = _apply(adapter, ('click', r, c)); total += 1
            if rew > 0 or (getattr(adapter._obs, "levels_completed", 0) or 0) > base:
                return _h(), total, True
            after = _h()
            if after < before - 1e-9:
                progressed = True; best = min(best, after)
            if dn:
                return best, total, False
        stall = 0 if progressed else stall + 1
    return best, total, False


def _share_edge(adapter, pos_px, disp, moved):
    """WRITE a measured movement outcome from ANY planner into the one shared spatial memory.

    `descend` and the avatar solve had learned the same facts in two private stores with two conventions (descend:
    (pixel-centroid, action-name); avatar: (lattice-cell, unit-direction)), and descend's died on return -- so the
    agent bumped the same walls every life and neither planner could use what the other had paid actions to learn.
    This normalises to the avatar's lattice convention (the map's native frame) so one belief serves both.
    Silently no-ops when the movement lattice isn't known yet (e.g. a non-avatar game) -- never guesses a quantum.
    """
    try:
        if pos_px is None or not disp:
            return
        sm = _spatial_mem(adapter); q = getattr(adapter, "_spatial_quantum", None)
        if sm is None or not q:
            return                                             # no movement lattice known yet -> never guess one
        d = ((disp[0] > 0) - (disp[0] < 0), (disp[1] > 0) - (disp[1] < 0))
        if d == (0, 0):
            return
        sm.record_neighbour((int(round(pos_px[0] / q)), int(round(pos_px[1] / q))), d, bool(moved))
    except Exception:
        pass


def _seed_edges(adapter, dirs, local_edges):
    """READ the shared memory back into descend's own (pixel-cell, action) convention, so its A* plans over everything
    the game has learned -- including what the avatar solve mapped on earlier lives -- instead of only what this one
    descend call has bumped into so far. Union, never replace: local measurements always stand."""
    try:
        sm = _spatial_mem(adapter); q = getattr(adapter, "_spatial_quantum", None)
        if sm is None or not q or not dirs:
            return local_edges
        out = set(local_edges)
        for (cell, d), st in list(sm.edge.items()):
            if st != _SM_BLOCKED:
                continue
            for a, (dr, dc) in dirs.items():
                if ((dr > 0) - (dr < 0), (dc > 0) - (dc < 0)) == d:
                    out.add(((int(cell[0] * q), int(cell[1] * q)), a))
        return out
    except Exception:
        return local_edges


def descend(adapter, disc, ctrl, budget=400, max_restarts=6, patience=60, reset_first=True,
            rotational=False, rotate_actions=None, plan_amap=None, plan_co=None, plan_rotate_model=None,
            plan_schema=None, plan_individuation=None, plan_interaction=None):
    """FORWARD-DESCENT engine (§11.266-270): the action-ECONOMICAL complement to pursue. It plays FORWARD --
    one committed action per step toward the cells disc.active(g) flags -- and resets ONLY on death. For a
    MOVER it learns the controllable's move-map AND a passability map from committed moves, and navigates by
    A* over that map (routing around walls); greedy distance-descent is the open-field degenerate case of the
    same primitive. The A*-justified move is exempt from the measure-based block (going around a wall is
    locally non-improving but globally correct). Same Discrepancy contract as pursue; reward disposes. Stalls
    only where a richer mechanic-model is needed (e.g. select-then-act) -- pursue is the fallback. A no-
    progress abort (patience) keeps the descend-first pass cheap across many hypotheses.
    reset_first=False (11.301): start from the CURRENT frame instead of a whole-game reset -- used to descend a
    LATER level after an earlier one was completed (the live game auto-advanced; a reset would wipe to level 1)."""
    g = adapter.reset() if reset_first else _perceive_grid(adapter)
    region = _hud_region(g)
    nullary = list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions())
    located = list(adapter.pointer_actions()) if hasattr(adapter, "pointer_actions") else []
    fatal = set(); blocked = set(); blocked_edges = set(); move_map = {}
    total = 0; restarts = 0
    best_h = disc.measure(g); best_dist = None; since = 0
    init_h = best_h; early = max(8, min(patience // 3, 16))     # loss-signal: quit fast if the loss never moves
    _rot_planned = False                                        # bounded rotation plan runs once per episode
    # SEAM (objective-first interleaved solve): a click game (located actions, no movement) with an induced objective
    # -- solve by interleaving observation and exploitation so irreversible one-shot controls are never fired blindly.
    # Replaces the old probe-then-exploit split, which pre-fired controls it never used. Guarded/fallback-safe.
    try:
        if located and not nullary:
            _bh, _sp, _solved, _model = _interleaved_solve(adapter, disc, budget)
            total += _sp
            if _solved or adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                return dict(validated=True, executed=total, mapping_cost=total, engine="descend-interleaved")
            g = _perceive_grid(adapter); best_h = min(best_h, float(disc.measure(g)))
    except Exception:
        pass
    # SEAM (C3): standing fidelity monitor -- observe every action's predicted-vs-real error (observe-only here; it
    # tracks fidelity and can recalibrate, but we do not auto-recalibrate mid-pursuit until validated). Guarded.
    _fmon = None
    try:
        _fm_hook = controller_hook("fidelity_monitor")
        if _fm_hook is not None and (plan_amap or plan_rotate_model):
            _fmon = _fm_hook(plan_amap or {}, rotate_actions or (), ctrl, plan_co, plan_rotate_model or {})
    except Exception:
        _fmon = None
    # SEAM (schema_planner, C6->MATCH_SKILL): if the game was recognised as multi-object correspondence matching,
    # drive it with the general MATCH_BY_KEY o PER_PAIR_SKILL plan (vc33: key=colour, skill=accumulate) instead of the
    # default click/greedy path. Guarded and FALLBACK-SAFE: if objects don't extract or the plan is empty, fall
    # straight through to the existing regimes below. No reset (resets are disabled globally).
    try:
        _sch = (plan_schema or {}).get("schema") if isinstance(plan_schema, dict) else None
        _sp_hook = controller_hook("schema_planner")
        if _sch == "MATCH_SKILL" and _sp_hook is not None and plan_amap:
            ctrls, tgts = _extract_match_objects(g, ctrl, plan_co, plan_individuation)
            if ctrls and tgts:
                import autonomy_controllers as _ACp
                plan = _sp_hook(ctrls, tgts, _ACp.key_colour,
                                lambda c, t: _ACp.skill_accumulate(c, t, plan_amap or {}))
                for a in (plan or []):
                    if isinstance(a, tuple) and a and a[0] == "select":
                        continue
                    if adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                        return dict(validated=True, executed=total, mapping_cost=total, engine="descend-schema")
                    g2, rew, dn, _ = _apply(adapter, a); total += 1
                    if _fmon is not None:
                        try: _fmon.observe(g, a, g2)
                        except Exception: pass
                    if rew > 0 or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                        return dict(validated=True, executed=total, mapping_cost=total, engine="descend-schema")
                    if dn or total >= budget:
                        break
                    g = g2
                best_h = min(best_h, float(disc.measure(g)))
    except Exception:
        pass
    # SELECTION-AWARE MULTI-PIECE PLANNING (the general assembly path): when a CLICK selects which piece the transforms
    # act on and the board has >=2 pieces, plan over (select, transform) across ALL pieces and execute (MPC). Selection
    # is first-class state, so the planner can move whichever pieces it takes to interlock every tip-pair -- and clicks
    # are DELIBERATE (from the plan), never the reactive flail that caused the post-connect select/deselect thrash.
    # The JOINT atom reaches the interlock IN-MODEL (predicted 0), but LIVE it regresses: the selection mechanic
    # (click-selects-piece) is assumed, not validated, and the model-reality gap on selects+moves compounds into
    # click-thrash. So keep it off the 2-piece case (monolith is more reliable there) until the selection model is
    # validated against real behaviour. The atom itself is correct and arity-invariant; this gate is about executor
    # fidelity, not the atom.
    _sel_regime = bool(located) and (plan_amap or rotate_actions) and len(_seg_pieces(g, ctrl)) >= 3
    if _sel_regime:
        _broke = False
        for _rp in range(4):                                    # MPC: assemble, execute, close residual, re-assemble
            if adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                return dict(validated=True, executed=total, mapping_cost=total, engine="descend-assemble")
            plan = _assemble_plan(g, ctrl, list(nullary), plan_amap or {}, rotate_actions or (), located,
                                  depth=16, beam=10)
            if not plan:
                break
            _b = _sel_obj(_seg_pieces(g, ctrl))
            for a in plan:
                if adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                    return dict(validated=True, executed=total, mapping_cost=total, engine="descend-assemble")
                g2, _, dn, _ = _apply(adapter, a); total += 1
                if dn:                                          # GAME_OVER: stop the regime, do NOT reset-loop (churn)
                    _broke = True; break
                g = g2
                if total >= budget:
                    break
            if _broke or total >= budget:
                break
            if isinstance(disc, _TipOverlapDisc):               # P1 residual close on the assembled state
                total += _residual_correct(adapter, disc, ctrl, plan_co, plan_amap or {}, budget - total)
                if adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                    return dict(validated=True, executed=total, mapping_cost=total, engine="descend-assemble")
                g = _perceive_grid(adapter)
            _a = _sel_obj(_seg_pieces(g, ctrl))
            best_h = min(best_h, float(disc.measure(g)))
            if _a >= _b - 0.5 or total >= budget:               # no progress this cycle -> stop
                break
    # PLANNED PURSUIT (direction 1 -- the general fix): if we know the controllable's transformation (a learned
    # translate map and/or a rotate action), PLAN a whole action sequence in the FOCUSED forward model that minimises
    # the discrepancy, then EXECUTE it -- instead of reacting greedily one step at a time. The focused model is
    # high-fidelity by construction (it only simulates what we actually learned about the controllable), so the
    # planner can find "rotate to align, translate to connect" that greedy descent never assembles.
    if (plan_amap or rotate_actions) and nullary:
        for _replan in range(12):                               # MPC: plan -> execute -> re-plan (corrects model error
            if adapter.satisfied():                             # by re-observing the real state each cycle)
                return dict(validated=True, executed=total, mapping_cost=total, engine="descend-plan")
            try:
                seq, _ph = _plan_via_model(g, disc, list(nullary), plan_amap or {}, rotate_actions or (), ctrl,
                                           depth=18, beam=10, co=plan_co, rotate_model=plan_rotate_model)
            except Exception:
                seq = []
            if not seq:
                break
            _before = float(disc.measure(g))
            for a in seq:
                if adapter.satisfied():
                    return dict(validated=True, executed=total, mapping_cost=total, engine="descend-plan")
                g2, _, dn, _ = _apply(adapter, a); total += 1
                if (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0) or adapter.satisfied():
                    return dict(validated=True, executed=total, mapping_cost=total, engine="descend-plan")
                if dn:
                    adapter.reset(); break
                g = g2
                if total >= budget:
                    break
            _after = float(disc.measure(g))
            best_h = min(best_h, _after)
            if _after >= _before - 0.01 or total >= budget:     # truly no progress this cycle -> stop re-planning
                break
        # P1 CLOSED-LOOP RESIDUAL CORRECTION: the model plan set orientation + rough position; now close the REAL
        # observed tip residual (robust to model-magnitude bias -- re-measured from reality each cycle).
        if isinstance(disc, _TipOverlapDisc) and total < budget:
            total += _residual_correct(adapter, disc, ctrl, plan_co, plan_amap or {}, budget - total)
            if adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                return dict(validated=True, executed=total, mapping_cost=total, engine="descend-residual")
            g = _perceive_grid(adapter); best_h = min(best_h, float(disc.measure(g)))
    while total < budget:
        if adapter.satisfied():
            return dict(validated=True, executed=total, mapping_cost=total, engine="descend")
        h = disc.measure(g)
        if h <= 0:                                              # predicate met
            if located and not nullary:                        # click-to-place family: SETTLE for a DELAYED reward
                for _ in range(SETTLE_STEPS):                   # (win animations register reward a few frames late)
                    if adapter.satisfied():
                        return dict(validated=True, executed=total, mapping_cost=total, engine="descend")
                    bl = getattr(adapter._obs, "levels_completed", 0) or 0
                    g, _, d, _ = adapter.step(("click", 0, 0))  # raw top-left corner: benign / ignored mid-animation
                    total += 1
                    if (getattr(adapter._obs, "levels_completed", 0) or 0) > bl or adapter.satisfied():
                        return dict(validated=True, executed=total, mapping_cost=total, engine="descend")
                    if disc.measure(g) > 0 or d:                # config disturbed or episode ended -> stop settling
                        break
            return dict(validated=False, reason="predicate-satisfied-no-reward", mapping_cost=total, engine="descend")
        s = _abstract(g, region)
        active = disc.active(g)
        cpos = _centroid(g, ctrl) if ctrl is not None else None
        chosen = None; astar = False
        # ROTATION PURSUIT: in a reorient regime the actions SPIN the piece; there is no translation to A*-navigate
        # (the move-map is a phantom -- this is the cn04 "spinning instead of connecting" bug). Cycle the actions --
        # each reorients the piece -- and the loop's discrepancy tracking keeps the orientation that aligns the tips.
        if rotational and nullary:
            pool = [a for a in nullary if (s, a) not in fatal and (s, a) not in blocked] or list(nullary)
            chosen = pool[total % len(pool)] if pool else None
        # BOUNDED ROTATION PLAN (the "you only need ~2 rotations" fix): when translation stalls and a rotate action
        # exists, DON'T spin reactively (113x). Enumerate the <=4 orientations ONCE, record the discrepancy at each,
        # rotate to the best, then STOP and let translation resume. Bounded to <=7 rotations, planned not reactive.
        if chosen is None and rotate_actions and since >= 4 and not _rot_planned:
            ra = next((a for a in nullary if str(a) in rotate_actions and (s, a) not in fatal), None)
            if ra is not None:
                _rot_planned = True; orient = []
                for k in range(4):                             # sweep the four orientations, scoring each
                    orient.append((k, float(disc.measure(g))))
                    g, _, dd, _ = _apply(adapter, ra); total += 1
                    if adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                        return dict(validated=True, executed=total, mapping_cost=total, engine="descend-rot")
                best_k = min(orient, key=lambda t: t[1])[0]     # orientation that minimises the discrepancy
                for _ in range(best_k):                         # rotate to it (we are back at orientation 0 now)
                    g, _, dd, _ = _apply(adapter, ra); total += 1
                    if adapter.satisfied() or (getattr(adapter._obs, "levels_completed", 0) or 0) > getattr(adapter, "_lvlbase", 0):
                        return dict(validated=True, executed=total, mapping_cost=total, engine="descend-rot")
                h2 = float(disc.measure(g))
                if h2 < best_h - 1e-9:
                    best_h = h2
                since = 0                                       # aligned: let translation resume toward the target
                continue
        # (1) NAV PRIMITIVE: A* over the learned passability map (greedy is its open-field special case). Used only
        # while movement is still PROGRESSING; once it stalls (since>=6) on a cell-target with pointer actions,
        # fall through to CLICKING the target cell -- some games place the controllable by click, not by sliding
        # (cn04: the feet enter the sealed hole via ACTION6, never by movement). The loss signal picks the modality.
        if chosen is None and not rotational and nullary and cpos is not None and active and not (located and since >= 6):
            dirs = {a: (int(round(dr)), int(round(dc))) for a, (dr, dc) in move_map.items()
                    if abs(dr) + abs(dc) >= 0.5}
            tgt = min(active, key=lambda rc: abs(rc[0] - cpos[0]) + abs(rc[1] - cpos[1]))
            if dirs:
                # PLAN OVER THE SHARED BELIEF: local bumps from this call, UNION everything the game already knows --
                # including walls the avatar solve mapped on an earlier life. One memory, two planners reading it.
                plan = _astar_actions(cpos, tgt, dirs, _seed_edges(adapter, dirs, blocked_edges), g.shape)
                if plan and (s, plan[0]) not in fatal:
                    chosen = plan[0]; astar = True
        # (2) DIRECTED located action at the flagged cells (click-to-place; also the stall fallback for movers)
        if chosen is None and located and active and not _sel_regime:   # in selection regime clicks are DELIBERATE
            #                                                             (plan-only) -- never a reactive flail
            for (r, c) in active:
                cand = (located[0], int(r), int(c))
                if (s, cand) not in fatal and (s, cand) not in blocked:
                    chosen = cand; break
        # (3) MOVER greedy / probe fallback (learns the map A* will use)
        if chosen is None and nullary:
            moves = [a for a in nullary if (s, a) not in fatal and (s, a) not in blocked]
            if moves and cpos is not None and active and move_map:
                tgt = min(active, key=lambda rc: abs(rc[0] - cpos[0]) + abs(rc[1] - cpos[1]))
                cur = abs(tgt[0] - cpos[0]) + abs(tgt[1] - cpos[1])

                def _gain(a):
                    dr, dc = move_map.get(a, (0.0, 0.0))
                    return cur - (abs(tgt[0] - (cpos[0] + dr)) + abs(tgt[1] - (cpos[1] + dc)))
                moves.sort(key=lambda a: -_gain(a))
            chosen = moves[0] if moves else None
        if chosen is None:
            break
        a = chosen; cp0 = cpos
        bl = getattr(adapter._obs, "levels_completed", 0) or 0
        g2, _, d, _ = _apply(adapter, a); total += 1
        if (getattr(adapter._obs, "levels_completed", 0) or 0) > bl or adapter.satisfied():
            return dict(validated=True, executed=total, mapping_cost=total, engine="descend")
        if d:                                                   # death: remember it, restart (bounded)
            fatal.add((s, a))
            if restarts < max_restarts:
                restarts += 1; g = adapter.reset(); total += 1; continue
            break
        if (a in nullary) and ctrl is not None and cp0 is not None and str(a) not in (rotate_actions or ()):
            cp = _centroid(g2, ctrl)
            if cp is not None:
                _disp = (cp[0] - cp0[0], cp[1] - cp0[1])
                if abs(_disp[0]) + abs(_disp[1]) >= 0.5:
                    move_map[a] = _disp                          # LEARN the displacement only from a move that MOVED.
                else:                                            # (rotate actions excluded: their tip-shift is a spin,
                    # A BLOCKED move must not overwrite what this action MEANS. It used to: move_map[a] was set to ~0,
                    # which then failed the `abs(dr)+abs(dc) >= 0.5` filter feeding A*, so the action vanished from the
                    # planner's edge set -- one bump against one wall erased that direction across the whole board.
                    blocked_edges.add(((int(round(cp0[0])), int(round(cp0[1]))), a))   # not a translation -> keep A*
                    _share_edge(adapter, cp0, move_map.get(a), moved=False)            # honest
                _share_edge(adapter, cp0, move_map.get(a), moved=(abs(_disp[0]) + abs(_disp[1]) >= 0.5))
        h2 = disc.measure(g2)
        if a in nullary and h2 >= h and not astar:             # measure-block only for greedy (A* may go around)
            blocked.add((s, a))
        progressed = False                                      # progress = measure dropped OR moved closer
        if h2 < best_h - 1e-9:
            best_h = h2; progressed = True
        cpos2 = _centroid(g2, ctrl) if ctrl is not None else None
        act2 = disc.active(g2)
        if cpos2 is not None and act2:
            dmin = min(abs(r - cpos2[0]) + abs(c - cpos2[1]) for (r, c) in act2)
            if best_dist is None or dmin < best_dist - 1e-9:
                best_dist = dmin; progressed = True
        if progressed:
            since = 0
        else:
            since += 1
            # EARLY-FLAT ABORT (the loss signal): if the discrepancy has not improved AT ALL in the first `early`
            # steps, this objective/mechanic is dead -- quit now instead of spamming patience more identical steps.
            if total >= early and best_h >= init_h - 1e-9 and (best_dist is None):
                return dict(validated=False, reason="flat-loss",
                            best_discrepancy=round(float(best_h), 1), mapping_cost=total, engine="descend")
            if since > patience:                                # ABORT 2: no progress (measure AND distance)
                return dict(validated=False, reason="no-progress",
                            best_discrepancy=round(float(best_h), 1), mapping_cost=total, engine="descend")
        g = g2
    return dict(validated=False, reason="reward-unreached",
                final_discrepancy=round(float(disc.measure(g)), 1), mapping_cost=total, engine="descend")


def _set_composer_state(adapter, world=None, cands=None, belief=None, engine=None):
    """Build the RICH per-frame mental-state snapshot (perception / grammar / ledger / spatial / episodic) once
    per validate(), stored on the adapter so every action's reasoning carries the full picture -- the legible
    snapshot the reason-first brain produced, rebuilt for the engine path."""
    if not hasattr(adapter, "set_reasoning"):
        return
    import numpy as _np
    st = {}
    try:
        w = world or {}
        game = w.get("game") or {}
        gf = _perceive_grid(adapter)
        bg = int(_np.bincount(gf.ravel()).argmax()) if gf.size else 0
        nobj = int((gf != bg).sum())
        st["perception"] = {
            "controllable_color": w.get("controllable"),
            "action_map": {str(k): list(v) for k, v in (w.get("action_map") or {}).items()},
            "task_family": game.get("family"),
            "cell_scale": game.get("scale"),
            "explored_steps": w.get("n_steps"),
            "locus": (w.get("report") or {}).get("locus"),
            "grid": [int(gf.shape[0]), int(gf.shape[1])],
            "nonbg_cells": nobj,
            "coverage": w.get("coverage"),
            "classified": w.get("classified"),
            "world_map": w.get("world"),        # windowed-world hypothesis, held live in every frame's reasoning
            "dynamics": w.get("dynamics"),       # induced environment transition-rule report (identifiability/fidelity)
        }
    except Exception:
        pass
    try:
        st["grammar"] = [h["descriptor"] for (h, _d) in (cands or [])][:12]
    except Exception:
        st["grammar"] = []
    try:
        st["belief"] = {k: round(float(v), 2) for k, v in (belief or {}).items()}
    except Exception:
        st["belief"] = {}
    try:
        st["episodic"] = {"levels_completed": int(getattr(adapter._obs, "levels_completed", 0) or 0)}
    except Exception:
        st["episodic"] = {}
    if engine is not None:
        try:
            st["ledger"] = {"status": "engine-active",
                            "promoted": list(getattr(engine.coopt, "promoted", {}) or {}),
                            "escalations": len(getattr(engine, "escalations", []) or []),
                            "radius": round(float(getattr(engine.radius, "radius", 0)), 2)}
        except Exception:
            st["ledger"] = {"status": "composing"}
    else:
        st["ledger"] = {"status": "composing", "candidates": len(cands or [])}
    # Stamp the DETECTED dynamics regime (avatar / actuator / unknown) so every downstream reasoning payload -- composer
    # bridge AND online adapter -- reports the REAL regime, not a hardcoded guess. Uses the shared detector over signals
    # already on the adapter (self-locus, avatar-handled flag, action space, probe depth). Regime-agnostic; no grid.
    try:
        import regime_factory as _RFreg
        _slm = getattr(adapter, "slm", None)
        _has_self = bool(getattr(adapter, "_avatar_handled", False)) or (
            _slm is not None and getattr(_slm, "locus", None) is not None
            and len(_slm.coherent_actions()) > 0)
        _avail = None
        try:
            _aa = getattr(getattr(adapter, "_obs", None), "available_actions", None)
            _avail = set(int(getattr(a, "value", a)) for a in _aa) if _aa else None
        except Exception:
            _avail = None
        _clicks_only = bool(_avail) and _avail.issubset({6, 7})
        _steps = int(getattr(adapter, "_n_action", 0) or 0)
        _narg = (1 if _has_self else (0 if (_clicks_only or _steps >= 50) else None))
        st["regime"] = _RFreg.SHARED.control_regime.classify(_narg, _clicks_only, _steps)
    except Exception:
        st["regime"] = "unknown"
    adapter._composer_state = st


def _delta_compress_meta(adapter, meta):
    """DELTA FRAME-DATA (keep the recording small + make spam visible). Carry only what CHANGED since the previous
    action: every unchanged field becomes an em-dash '\u2014', and an action with NO new grammar and the SAME decision as
    the last collapses to a single '\u2014' with a running repeat count. Concatenating the recording then reads as a diff --
    fast for a human and for Claude -- and a spammed / duplicate action shows up immediately as a RUN OF DASHES (e.g.
    the wall-pounding would read '\u2014 \u2014 \u2014 ...'). Compares by repr so it is robust to in-place state mutation.
    The agent's live logic reads _composer_state, not this stamped copy, so compressing the recording is side-effect-free."""
    gsteps = meta.get("grammar_steps") or []
    dec = meta.get("decision", {})
    sig = (tuple(gsteps), repr(dec))
    if not gsteps and sig == getattr(adapter, "_prev_meta_sig", None):
        n = getattr(adapter, "_meta_repeat", 0) + 1
        adapter._meta_repeat = n                               # identical action repeated -> one dash, counted
        return {"repeat": "\u2014", "same_as_prev_x": n, "pass": meta.get("pass", "")}
    adapter._meta_repeat = 0
    adapter._prev_meta_sig = sig
    prev_reprs = getattr(adapter, "_prev_meta_reprs", {}) or {}
    out = {}; cur_reprs = {}
    for k, v in meta.items():
        rv = repr(v); cur_reprs[k] = rv
        if k in ("grammar_steps", "decision", "pass", "source"):
            out[k] = v                                         # always carry the delta narration + this decision/pass
        elif prev_reprs.get(k) == rv:
            out[k] = "\u2014"                                  # field unchanged since the last action
        else:
            out[k] = v                                         # field changed -> carry the new value
    adapter._prev_meta_reprs = cur_reprs
    return out


def _ride_reason(adapter, relation=None, target=None, pass_name="", objective=None, extra=None):
    """Stamp the RICH grammar-legible reasoning on the adapter so EVERY action carries the full mental state
    (perception/grammar/ledger/spatial/episodic from _set_composer_state) PLUS this step's decision. Rides the
    replay at data.action_input.reasoning."""
    if not hasattr(adapter, "set_reasoning"):
        return
    words = None
    if relation:
        try:
            from objective_abductor import explain_relation
            words = (explain_relation(relation) or {}).get("words")
        except Exception:
            words = None
    meta = dict(getattr(adapter, "_composer_state", {}) or {})        # rich persistent context
    meta["source"] = "composer"; meta["pass"] = pass_name
    decision = {"pass": pass_name}
    if relation:
        meta["relation"] = relation; meta["grammar_gloss"] = words or relation; decision["relation"] = relation
    if target is not None:
        meta["target"] = str(target); decision["target"] = str(target)
    if objective:
        meta["objective"] = str(objective); decision["objective"] = str(objective)
    if extra:
        meta.update(extra); decision.update(extra)
    meta["decision"] = decision
    # Flush the grammar steps emitted SINCE the last action onto THIS action's reasoning, so the frame data carries the
    # real chronological grammar (not just a state snapshot). Concatenating meta["grammar_steps"] across the recording
    # reconstructs the full derivation -> frame data is complete, side structure is a derived view.
    try:
        pend = getattr(adapter, "_grammar_pending", None)
        if pend:
            meta["grammar_steps"] = list(pend)
            adapter._grammar_pending = []
    except Exception:
        pass
    import os as _os
    if _os.environ.get("OURO_FRAME_DELTA", "1") == "1":        # delta-compress the stamped frame data (spam -> dashes)
        try:
            meta = _delta_compress_meta(adapter, meta)
        except Exception:
            pass
    try:
        adapter.set_reasoning(meta)
    except Exception:
        pass


_HUD_ROWS = 2   # the action COUNTER / HUD occupies the top rows and ticks on EVERY action; excluded from change
                # detection, else every click looks 'reactive', bound-mapping never saturates, and the causal map is
                # polluted (the diagnosed root cause of the agent not distinguishing a real pump from a no-op).


def _induce_roles(g0, moved, fixed, fluid, actuators=None, bind=None):
    """ROLE INDUCTION (gap #2): label objects by their DYNAMIC SIGNATURE, not appearance -- the agent labelling the
    world by behaviour instead of being told 'id-9 is a button, id-5 is a boundary'. From the probing results:
      FLUID     := the colour of the bodies that MOVE under actuation.
      ACTUATOR  := a control whose click moves fluid elsewhere.
      PUCK      := a marker that CO-MOVED with the fluid (floats = current level).
      TARGET    := a static marker sharing a puck's colour (fixed = win level).
      BOUNDARY  := the dominant static structure colour (the walls separating fluid bodies).
      COLUMNS   := the distinct co-moving fluid bodies (from the common-fate bind).
    Returns a role map -- transferable via _record_mechanic, articulable via _emit. Pure classifier over already-probed
    data (no extra actuation)."""
    g0 = np.asarray(g0); r0, r1, c0, c1 = _play_area(g0)
    bg = int(np.bincount(g0[r0:r1 + 1, c0:c1 + 1].ravel()).argmax())
    puck_cols = sorted(set(int(o["colour"]) for o in (moved or [])))
    tgts = [o for o in (fixed or []) if int(o["colour"]) in puck_cols]
    from collections import Counter as _C
    # BOUNDARY := the dominant static structure colour (the walls) -- non-fluid, non-background, non-puck. Derived from
    # the frame directly (no extra actuation); the common-fate `bind` refines it when provided.
    boundary = None
    nonf = _C(int(g0[y, x]) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)
              if int(g0[y, x]) not in (bg, fluid) and int(g0[y, x]) not in puck_cols)
    if bind is not None and bind.get("static"):
        sc = _C(int(g0[y, x]) for (y, x) in bind["static"]
                if int(g0[y, x]) not in (bg, fluid) and int(g0[y, x]) not in puck_cols)
        if sc:
            nonf = sc
    if nonf:
        boundary = nonf.most_common(1)[0][0]
    columns = None
    if bind is not None and bind.get("bodies") and bind.get("distinct_groups"):
        columns = []
        for grp in bind["distinct_groups"]:
            cells = bind["bodies"][grp[0]]
            xs = [x for (_y, x) in cells]
            if xs:
                columns.append((min(xs), max(xs)))
    return {"fluid_colour": fluid, "boundary_colour": boundary,
            "actuator_controls": list(actuators or []), "puck_colours": puck_cols,
            "n_pucks": len(moved or []), "n_targets": len(tgts),
            "columns": columns}


def _cofate_bind(adapter, apply_fn, controls, reps=2):
    """SELF-SUPERVISED BINDING via COMMON FATE (gap #1: the agent generates its own segmentation-error signal instead of
    being told 'those are two things'). Actuate each control and record which cells CO-MOVE. Then correct the appearance
    (colour) segmentation with dynamics:
      - SPLIT: cells of the SAME colour that move under DIFFERENT actuations are DISTINCT bodies (a colour that merged
        separate objects -- e.g. fluid that is really N independent columns; or static structure vs moving fluid of one
        colour). Detected as low cross-control cell overlap.
      - MERGE: cells of DIFFERENT colour that ALWAYS move together are ONE body (an object the colour-segmenter split).
      - STATIC: cells that never move under any actuation are fixed structure (boundaries / targets), not movers.
    Returns {'bodies': {control: frozenset(cells)}, 'static': frozenset(cells), 'n_dynamic_bodies': k}. Dynamics-first,
    appearance-second -- the same dynamics-over-appearance principle as _play_area / the anomaly-split / 'fluid = what
    moves', now applied to fix segmentation itself. Compositional and transferable (feeds _record_mechanic)."""
    base = _perceive_grid(adapter)
    moved_any = np.zeros(base.shape, bool)
    bodies = {}
    for (r, c) in controls:
        b = _perceive_grid(adapter)
        for _ in range(reps):
            apply_fn(adapter, ("click", int(r), int(c)))
        a = _perceive_grid(adapter)
        cells = np.argwhere(_real_diff(b, a))
        if len(cells):
            fs = frozenset(map(tuple, cells))
            bodies[(int(r), int(c))] = fs
            for (yy, xx) in cells:
                moved_any[yy, xx] = True
    # distinct dynamic bodies = control effect-sets with low mutual overlap (independent movers = the SPLIT signal)
    keys = list(bodies)
    distinct = []
    for k in keys:
        merged = False
        for grp in distinct:
            ov = len(bodies[k] & bodies[grp[0]])
            if ov > 0.5 * min(len(bodies[k]), len(bodies[grp[0]])):   # heavy overlap -> same body
                grp.append(k); merged = True; break
        if not merged:
            distinct.append([k])
    # static = cells present in objects but never moved (fixed structure: boundaries/targets)
    r0, r1, c0, c1 = _play_area(base)
    bg = int(np.bincount(base[r0:r1 + 1, c0:c1 + 1].ravel()).argmax())
    static = frozenset((int(y), int(x)) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)
                       if base[y, x] != bg and not moved_any[y, x])
    return {"bodies": bodies, "static": static, "n_dynamic_bodies": len(distinct),
            "distinct_groups": [list(g) for g in distinct]}


def _real_diff(before, after):
    """Boolean mask of cells that changed between two frames, EXCLUDING the top HUD/counter rows. The counter advancing
    every action is not a game effect; ignoring it is what lets a click's REAL effect (or lack of one) be seen."""
    d = (np.asarray(before) != np.asarray(after))
    if d.shape[0] > _HUD_ROWS:
        d[:_HUD_ROWS, :] = False
    return d


_DIR_NAME = {(-1, 0): "UP", (1, 0): "DOWN", (0, -1): "LEFT", (0, 1): "RIGHT"}


def _perceive_cyclic_triggers(frames, avatar_colour):
    """PERCEIVE cyclic remote causality -- the locksmith causal atom. A KEY/LOCK glyph (a mutate-in-place display) whose
    property changes ONLY when the avatar (self) is at a specific cell means that cell is a TRIGGER and the effect is
    STEP_ON(trigger@pos) -> CYCLE(display.property). Excludes the HUD (a display that changes essentially every step is a
    bar/timer, not a triggered glyph -- position-independent change is the tell). Returns [{display, trigger, n}] sorted
    by evidence. Generic: 'a property that advances when I stand somewhere', not locksmith-specific. Cyclic confirmation
    (same trigger -> next value each visit) needs repeated visits, i.e. navigation."""
    from collections import defaultdict, Counter
    from scipy.ndimage import label as _lbl
    frames = [np.asarray(f[0] if np.asarray(f).ndim == 3 else f) for f in frames]
    glyphs = [d["pos"] for d in _perceive_property_displays(frames) if d["is_glyph"]]

    def av_pos(g):
        m = (g == avatar_colour)
        return (int(round(np.where(m)[0].mean())), int(round(np.where(m)[1].mean()))) if m.sum() else None

    def glyph_state(g, pos):
        bg = set(np.argsort(np.bincount(g.ravel()))[-2:].tolist())
        for c in np.unique(g):
            if int(c) in bg or int(c) == avatar_colour:
                continue
            lab, n = _lbl(g == c, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if 2 <= len(ys) <= 40:
                    p = _object_props(g, ys, xs)
                    if abs(int(p["centroid"][0]) - pos[0]) + abs(int(p["centroid"][1]) - pos[1]) <= 4:
                        return (p["shape"], p["orient"])
        return None

    events = []
    for gp in glyphs:
        by_trig = Counter(); prev = glyph_state(frames[0], gp)
        for i in range(1, len(frames)):
            cur = glyph_state(frames[i], gp); ap = av_pos(frames[i - 1])
            if cur is not None and prev is not None and cur != prev and ap is not None:
                by_trig[ap] += 1
            prev = cur if cur is not None else prev
        if by_trig:
            trig, n = by_trig.most_common(1)[0]
            events.append({"display": gp, "trigger": trig, "n": int(n),
                           "spread": len(by_trig)})    # spread==1 across many n => a clean, consistent trigger
    events.sort(key=lambda e: -e["n"])
    return events


def _object_props(g, ys, xs):
    """PROPERTY VECTOR of an object (its cells at ys,xs): what the object IS, not where it is. colour(s); a SHAPE hash
    (bbox-cropped binary mask); a ROTATION-canonical shape (min over the 4 rotations) so the same glyph rotated is
    recognised as the same shape; the current ORIENTATION (0..3); size; centroid. This is the representation the
    locksmith regime needs -- a key/lock is a shape+colour+orientation that a trigger MUTATES, which position-only
    perception cannot express. Colour/scale-agnostic."""
    ys = np.asarray(ys); xs = np.asarray(xs)
    m = np.zeros((int(ys.max() - ys.min() + 1), int(xs.max() - xs.min() + 1)), dtype=np.uint8)
    m[ys - ys.min(), xs - xs.min()] = 1
    # SCALE-INVARIANT shape WITHOUT downsampling: divide out any INTEGER block-upscale factor EXACTLY, so a glyph
    # rendered at 2x reduces to the same primitive as its 1x version. This is lossless -- it removes redundant
    # duplication, it does NOT throw away grid resolution. (A 6x6 that is a 2x-tiled 3x3 -> 3x3; a native 3x3 stays 3x3.)
    def _reduce(a):
        h, w = a.shape
        for k in range(min(h, w), 1, -1):
            if h % k == 0 and w % k == 0:
                b = a.reshape(h // k, k, w // k, k)
                if (b == b[:, :1, :, :1]).all() and (b == b[:, :, :, :1]).all():
                    return a[::k, ::k]
        return a
    mc = _reduce(m)
    rots = [mc, np.rot90(mc, 1), np.rot90(mc, 2), np.rot90(mc, 3)]
    hs = [hash(r.tobytes()) for r in rots]; canon = min(hs)
    cols = tuple(sorted(set(np.asarray(g)[ys, xs].tolist())))
    return {"centroid": (float(ys.mean()), float(xs.mean())), "colours": cols, "shape": hash(mc.tobytes()),
            "canon_shape": canon, "orient": int(hs.index(canon)), "size": int(len(ys))}


def _perceive_property_displays(frames, emit_adapter=None):
    """PERCEIVE property-displays (key / lock): objects that stay at a FIXED position but whose SHAPE / COLOUR /
    ORIENTATION MUTATES over time -- distinct from the avatar (position changes) and walls (nothing changes), and from
    a HUD BAR (size changes monotonically, a glyph does not). Returns a list of {pos, colours, n_shapes, orients,
    is_glyph} sorted by mutation richness. If emit_adapter is given, articulates the grammar. Detection is generic --
    'a thing whose identity changes in place' -- so it fires on any property-mutation game, not just this one."""
    from collections import defaultdict
    from scipy.ndimage import label as _lbl
    hist = defaultdict(list)
    step = max(1, len(frames) // 40)
    for fi in range(0, len(frames), step):
        g = np.asarray(frames[fi]); g = g[0] if g.ndim == 3 else g
        bg = set(np.argsort(np.bincount(g.ravel()))[-2:].tolist())
        for c in np.unique(g):
            if int(c) in bg:
                continue
            lab, n = _lbl(g == c, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if 1 <= len(ys) <= 60:
                    p = _object_props(g, ys, xs)
                    cy, cx = int(round(p["centroid"][0])), int(round(p["centroid"][1]))
                    key = next((k for k in hist if abs(k[0] - cy) + abs(k[1] - cx) <= 4), (cy, cx))   # cluster within 4px
                    hist[key].append(p)                        # (full-res clustering, NOT a grid downsample)
    out = []
    for pos, seq in hist.items():
        if len(seq) < 3:
            continue
        shapes = set(s["shape"] for s in seq); orients = set(s["orient"] for s in seq)
        cols = set(c for s in seq for c in s["colours"]); sizes = set(s["size"] for s in seq)
        mutates = len(shapes) > 1 or len(orients) > 1 or len(cols) > 1
        if not mutates:
            continue
        # KEY/LOCK glyph vs HUD bar: a key/lock ROTATES or swaps between distinct compact glyphs; a depleting bar keeps
        # one orientation and just changes length. Orientation-change is the clean discriminator (a bar never rotates).
        w = max(s.get("size", 1) for s in seq)
        is_glyph = (len(orients) > 1) or (len(shapes) > 2 and len(cols) > 1 and w <= 25)
        out.append({"pos": pos, "colours": tuple(sorted(cols)), "n_shapes": len(shapes),
                    "orients": tuple(sorted(orients)), "is_glyph": bool(is_glyph)})
    out.sort(key=lambda d: (-d["is_glyph"], -d["n_shapes"] - len(d["orients"])))
    if emit_adapter is not None:
        for d in out[:4]:
            if d["is_glyph"]:
                _emit(emit_adapter, "PERCEIVE  property-display := object@%s  [MUTATES in place: %d shape(s), orientations %s, "
                      "colours %s -- a KEY/LOCK glyph (shape/colour/orientation IS its state), not a mover or a wall]"
                      % (d["pos"], d["n_shapes"], d["orients"], d["colours"]))
    return out


def _confirm_cycle_live(adapter, avatar_colour, steer, quantum, wall_colours, trigger_px, display_pos, visits=3):
    """ROBUST CYCLIC CONFIRMATION (needs navigation). Navigate the avatar onto a candidate TRIGGER cell, step on it,
    read the target DISPLAY's property (via _object_props), leave and return, and repeat. If the property ADVANCES to a
    new value each visit -- and eventually repeats (wraps) -- the atom STEP_ON(trigger) -> CYCLE(display.property) is
    confirmed, not just observed once. Returns the observed property sequence. Emits the grammar."""
    def _grid():
        g = _perceive_grid(adapter); return g[0] if g.ndim == 3 else g

    def _disp_state(g):
        from scipy.ndimage import label as _lbl
        bg = set(np.argsort(np.bincount(g.ravel()))[-2:].tolist())
        for c in np.unique(g):
            if int(c) in bg or int(c) == avatar_colour:
                continue
            lab, n = _lbl(g == c, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if 2 <= len(ys) <= 40:
                    p = _object_props(g, ys, xs)
                    if abs(int(p["centroid"][0]) - display_pos[0]) + abs(int(p["centroid"][1]) - display_pos[1]) <= 4:
                        return (p["shape"], p["orient"])
        return None

    seq = []
    for v in range(visits):
        g = _grid(); apos = (np.where(g == avatar_colour)[0].mean(), np.where(g == avatar_colour)[1].mean()) \
            if (g == avatar_colour).sum() else None
        if apos is None:
            break
        path = _avatar_pathfind(g, apos, trigger_px, steer, quantum, wall_colours)
        if not path:
            break
        for act in path[:40]:
            adapter.step(act)
        st = _disp_state(_grid())
        if st is not None:
            seq.append(st)
        # step off and back to re-trigger (a cycle needs a fresh contact)
        try:
            adapter.step(path[-1])
        except Exception:
            pass
    distinct = len(set(seq))
    if len(seq) >= 2 and distinct >= 2:
        _emit(adapter, "CONFIRM  STEP_ON(trigger@%s) \u2192 CYCLE(display@%s.property)  [property advanced through %d "
              "distinct values over %d visits -- a cyclic remote-causal atom, learned by navigating to it repeatedly]"
              % (tuple(int(x) for x in trigger_px), display_pos, distinct, len(seq)))
        try:
            _record_mechanic(adapter, "cyclic_trigger", {"trigger": tuple(int(x) for x in trigger_px), "display": display_pos})
        except Exception:
            pass
    return seq


def _avatar_solve(adapter, av, budget=260):
    """AVATAR-REGIME SCHEMA -- the reusable reasoning template for games where an object IS the agent. Runs the same
    skeleton as the actuator regime (perceive -> model -> derive-objective -> plan -> confirm -> transfer -> revise),
    instantiated with avatar primitives (self / navigation / cyclic-triggers / gates / budget). All learned state
    (steer, trigger causal map, win-condition) persists in the shared knowledge so it CARRIES FORWARD across levels and
    GROWS. Self-correcting: a gate that fires but does NOT win revises the objective hypothesis."""

    # ============================================================================================================
    # NEGATIVE KNOWLEDGE MUST OUTLIVE THE SOLVE.
    #
    # These were closure locals. `_avatar_solve` is re-entered many times per game, and everything it learned in a
    # local died with it -- so the agent re-discovered from scratch, every time: which boosters it had already
    # drained, which targets the what-if proved unreachable, where it had already been.
    #
    # That is I3 ("archives biodegrade") happening INSIDE the episode, which is worse than at the boundary -- the
    # boundary is at least a place you expect to lose things. An agent that forgets which booster it emptied walks
    # back to the empty one and re-learns it is empty, on a board where a level costs 41 actions of 42.
    #
    # The archive is not the driver (I3 is right). But it is the counter-check, and a counter-check that evaporates
    # every time the host function returns is not a counter-check.
    # ============================================================================================================
    try:                                          # the constraints the agent operates under belong IN the record
        import no_posthoc as _NPa
        _NPa.announce(lambda m: _emit(adapter, m, once_key="bound_posthoc"))
    except Exception:
        pass
    _persist = _GLOBAL_KNOWLEDGE.setdefault("patterns", {}).setdefault("avatar_negative", {})
    # The key/lock pair, hoisted. It is discovered ~450 lines below, but the market's chains are built ABOVE that --
    # so a carving that wants to predict "the key cycles" needs somewhere to look that exists before the key is found.
    # Declared here; filled by _keylock() when the board reveals it.
    _kl = [None]
    _install_grammar_ride(adapter)  # every action carries the grammar since the last one (frame-data completeness)
    import random as _rnd

    def _g():
        x = _perceive_grid(adapter); return x[0] if x.ndim == 3 else x  # guarded (full-res) read

    _shape_ids = _persist.setdefault("shape_ids", {})               # object identity across frames (survives the solve)

    def _sid(h):
        if h not in _shape_ids:
            _shape_ids[h] = "S%d" % (len(_shape_ids) + 1)
        return _shape_ids[h]

    def _fmt(pr):
        return "shape=%s orient=%d colour=%s" % (_sid(pr["canon_shape"]), pr["orient"], tuple(pr["colours"]))

    avatar = av["colour"]; steer = av["steer"]; quantum = max(1, int(round(av["magnitude"])))
    av_cols = set(av.get("colours", [avatar])) | {avatar}
    KN = _GLOBAL_KNOWLEDGE["patterns"]
    cmap = KN.setdefault("avatar_cmap", {})            # trigger visual-type -> atom (TRANSFERS across levels/games)
    _name2act = {}
    try:
        for _a in adapter.discrete_actions():
            _name2act[getattr(_a, "name", str(_a))] = _a
    except Exception:
        pass
    _base_ctr = getattr(adapter._obs, "levels_completed", 0) or 0
    _won = [None]; _spent = [0]; _drops = []; _prev_hud = [None]; _traj = []
    _learned = {"wall": set(), "floor": set()}                 # passability LEARNED from move outcomes (not guessed by size)
    _reconcile_state = [None]                                  # last two-frame proprioceptive verdict: moved/blocked/surprise
    # THE MARKET LIVES ON THE GAMEPLAY, NOT THE SOLVE. Held on the adapter like the traversal map, so the population,
    # its track records and its generation counter survive every death and reset of this gameplay and die only with it.
    # (Previously this was a local: each life rebuilt the population from nothing, so "evolution" never saw a second
    # generation. v4 needed 276 to reach level 4; a system reset to gen 0 every ~70 actions is not the same system.)
    _mk_state = getattr(adapter, "_micro_market", None)
    if _mk_state is None:
        _mk_state = adapter._micro_market = {"arena": None, "ctx": None, "evo": None, "pariah": None,
                                             "macro": None, "percepts": None, "prev_frame": None,
                                             "n": 0, "epoch_actions": 0, "epoch": 0,
                                             "epoch_levels": 0, "wins_this_epoch": 0}
    _q_ref = [quantum]
    _dead_boosters = _persist.setdefault("dead_boosters", set())   # boosters REACHED that still paid nothing -> spent
    #                                                            NOT carried across lives: a reset refills the budget, so
    #                                                            a booster that was spent may have paid out again.
    # Triggers navigation has actually delivered us to, in LATTICE cells -- the same frame the persisted list uses, so
    # the two can be compared at all. SEEDED from earlier lives: without this the set restarts empty every life and the
    # agent re-derives a route it already owns, which is the whole thing this is supposed to prevent.
    _reached_trigs = set(tuple(t) for t in (_mechanics(adapter).get("reached_triggers") or []))
    # The anti-circling memory. Losing this every solve is why an agent that "already explored there" explores there
    # again: it did, and then it forgot, and the forgetting is invisible from inside because every step is locally
    # reasonable. Bounded, because this one is a RECENCY window by design, not an archive.
    _visited = _persist.setdefault("visited", [])
    from spatial_map import SpatialMap                         # the SHARED spatial-map module (per-cell, dynamic, frontier)
    _sm = _spatial_mem(adapter, quantum, ttl=80)               # THE shared in-game map: what earlier lives explored is
    _last_dir = [None]                                         # still here, so a retry resumes instead of relearning
    _planned_move = [False]                                    # set by _goto_inner around a move that came FROM the
    #                                                            allocentric pathfinder (planned on floor, routed around
    #                                                            walls). The AXIOM wall-redirect must NOT override such a
    #                                                            move -- see the AXIOM note in _stepw.
    from collections import deque as _deque
    _act_hist = _deque(maxlen=6); _pos_hist = _deque(maxlen=8)  # rolling action/position history for A-B-A-B detection
    _osc_broke = [0]; _osc_burst = [0]                         # break counter + a sustained-escape burst (like v1-v4 rung)
    _rr = getattr(adapter, "_residual_router", None)
    if _rr is None:
        try:
            import residual_router as _RRm
            _rr = adapter._residual_router = _RRm.ResidualRouter(emit=lambda m: _emit(adapter, m))
        except Exception:
            _rr = None
    _lv_start = [0]
    try:
        _lv_start[0] = int(getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0)
    except Exception:
        pass
    _exec_ref = [None]                                         # the action ACTUALLY executed by the last _stepw
    _hud_before = [None]                                       # frame before the last action, for the budget inducer
    _nochange = [0]; _stuck_tried = [set()]                    # consecutive NO-FRAME-CHANGE streak + directions already
                                                               # tried-and-failed at this stuck point: "board didn't
                                                               # change" == the action did nothing (no colour guess needed)

    from spatial_map import BLOCKED as _SM_BLOCKED

    def _sm_blocked():
        return {k for k, st in _sm.cell.items() if st == _SM_BLOCKED}   # cells the shared map has learned are impassable

    def _sm_edges():
        """The MEASURED directed dead-ends from the shared map -- (cell, direction) transitions actually tried that
        moved nothing. This is the ALLOCENTRIC belief in the form the planner consumes; `_sm.ego(cell)` is the same
        belief in the form action-selection consumes. One memory, two views."""
        try:
            return _sm.blocked_edges()
        except Exception:
            return None

    def _hud_units(g=None):
        g = _g() if g is None else g
        return int((g[56:63, :] == 11).sum())                  # the bottom HUD bar only (not transition frames)

    def _stepw(actn):
        _exec_ref[0] = actn                                    # what we INTEND; overwritten if anything redirects it
        _hud_before[0] = _g()                                  # the budget is a GLOBAL resource: its model must see
        #                                                        EVERY action, not the ~2% that happen to be market
        #                                                        decisions. Sampling it sparsely means a meter can
        #                                                        drain AND refill between two looks, so the refill --
        #                                                        the only moment that reveals the lives counter -- is
        #                                                        attributed to the wrong frame.
        h0 = _hud_units(); ap0 = _apos(); _dest_col = None
        # AXIOM (universal choke-point): never spend an action pounding a KNOWN wall. If the intended move's DESTINATION
        # cell -- movement direction ONLY, so a corridor with walls on the SIDES is fine; only the single cell actually
        # entered is tested -- is a known wall colour (same colour => same wall), REDIRECT to a traversable direction so
        # the action is spent productively instead of wasted. Boxed in on every side -> take the intended move. The
        # pathfinder plans on floor so its steps never trip this; it catches the greedy/explore/random movers that were
        # pounding wall-4 ~1900x. Prefers continuing the avatar's current heading to avoid oscillation.
        #
        # BUT NOT A PLANNED MOVE. This centroid-cell test is blind to the avatar's body EXTENT and to sub-quantum
        # PHASE: reaching a goal that sits one cell past a wall opening (the ls20 win -- the target glyph is walled and
        # the win is the doorstep just below it) means the LAST planned step aims the centroid at a cell the wall
        # occupies while the 5-wide body actually slips through the 1-cell opening. The pathfinder ALREADY planned on
        # floor and its goal-vicinity rule licensed that final step; the AXIOM then overrode it and redirected the
        # avatar away from the door, so it oscillated at the chamber and never entered (measured: 10 gate-satisfies,
        # 0 clears over 1500 actions with the override on; level 0 CLEARS with it off). The AXIOM's own charter is the
        # greedy/explore/random movers -- so exempt moves that came from the allocentric drive. Displacement is still
        # measured downstream (_stall/_moved_any), so a genuine dead-end planned move is still caught, just not pre-empted.
        import os as _os
        if (_os.environ.get("OURO_WALL_AXIOM", "1") == "1" and ap0 is not None and actn in steer
                and not _planned_move[0]):   # default OFF: the
            _gw = _g()
            def _hits_wall(a):
                vy, vx = steer[a]
                _r = int(round(ap0[0])) + ((vy > 0) - (vy < 0)) * quantum
                _c = int(round(ap0[1])) + ((vx > 0) - (vx < 0)) * quantum
                if not (0 <= _r < _gw.shape[0] and 0 <= _c < _gw.shape[1]):
                    return True
                v = int(_gw[_r, _c]); return v in walls or v in _learned["wall"]
            if _hits_wall(actn):
                _alts = [a for a in steer if not _hits_wall(a)
                         and steer[a] != (-steer[actn][0], -steer[actn][1])]   # not an immediate reversal
                if not _alts:
                    _alts = [a for a in steer if not _hits_wall(a)]
                if _alts:
                    _pref = _dir_to_action(_last_dir[0]) if _last_dir[0] else None
                    actn = _pref if _pref in _alts else _alts[0]   # keep heading if valid -> less oscillation
                    _emit(adapter, "AXIOM  intended move walked into a KNOWN wall -> redirected to a traversable direction "
                          "[same colour => same wall; don't waste the action pounding it]", once_key="wall_axiom")
        # OSCILLATION-BREAKER (ported from Ouroboros v1-v4: CoordinateOscillationRung / InfiniteLoopBreakerRung). The
        # cycle-and-match loop structurally emits A-B-A-B (step onto a trigger, step off to re-trigger, repeat); when the
        # trigger is not actually cycling, that loop runs forever with nothing to escape it -- the exact gap vs v1-v4,
        # which caught it and forced a different action. Detect A-B-A-B in the recent action history AND no positional
        # progress (bouncing between <=2 cells), then FORCE a NOVEL traversable direction (not the oscillating pair,
        # landing on an unvisited cell) -- v1-v4's fix: inject a different action to break out.
        if (_os.environ.get("OURO_ANTI_OSCILLATE", "1") == "1" and ap0 is not None and actn in steer
                and len(_act_hist) >= 6):
            _r6 = list(_act_hist)[-6:]
            _detect = (_r6[0] != _r6[1] and _r6 == [_r6[0], _r6[1]] * 3 and len(set(_pos_hist)) <= 3)   # A-B-A-B, stuck
            if _detect and _osc_burst[0] <= 0:
                _osc_burst[0] = 12                             # start a sustained escape (v1-v4 rung fires until unstuck)
                _osc_broke[0] += 1
                _emit(adapter, "OSCILLATE  A-B-A-B with no progress (bouncing between %d cell(s)) -> BREAK for %d steps: "
                      "forcing NOVEL traversable moves to escape, not the useless loop  [v1-v4 oscillation-breaker]"
                      % (len(set(_pos_hist)), _osc_burst[0]), once_key="osc_%d" % (_osc_broke[0] // 3))
            if _osc_burst[0] > 0:                              # during the burst: steer to an unvisited, non-wall cell
                _osc_burst[0] -= 1
                _go = _g(); _recent = set(_pos_hist)
                def _noveldir(a):
                    vy, vx = steer[a]
                    _r = int(round(ap0[0])) + ((vy > 0) - (vy < 0)) * quantum
                    _c = int(round(ap0[1])) + ((vx > 0) - (vx < 0)) * quantum
                    if not (0 <= _r < _go.shape[0] and 0 <= _c < _go.shape[1]):
                        return None
                    if int(_go[_r, _c]) in walls or int(_go[_r, _c]) in _learned["wall"]:
                        return None
                    return (_r, _c)
                _fresh = [a for a in steer if (_d := _noveldir(a)) is not None and _d not in _recent]
                _any = _fresh or [a for a in steer if _noveldir(a) is not None]
                if _any:
                    actn = _any[0]                             # keep pushing into genuinely new space until unstuck
        # NO-FRAME-CHANGE STUCK-BREAK (the robust wall-stopper Isaiah named): if the recent identical actions produced
        # NO change in the board at all -- the "same_as_prev" runs the delta frame-data exposes -- the action is a pure
        # no-op (hitting a wall / stuck), so REDIRECT to a different traversable direction. Crucially this fires ONLY on
        # a real no-op: any move that actually shifts the avatar OR cycles the key DOES change the board, so it never
        # touches an intentional move -- that was the flaw in the colour-predicting wall-axiom that broke level 0.
        if (_os.environ.get("OURO_NOCHANGE_BREAK", "1") == "1" and ap0 is not None and actn in steer
                and _nochange[0] >= 2):
            _untried = [a for a in steer if a not in _stuck_tried[0]]   # the frame itself is the signal -- no colour
            if _untried:                                               # guess: just try a direction we haven't tried
                actn = _untried[0]                                     # since the board went stuck, until one changes it
                _exec_ref[0] = actn                                    # publish the SUBSTITUTION: anything that staked a
                #                                                        prediction on the intended action must be told the
                #                                                        intended action was never taken.
                _emit(adapter, "STUCK  %d actions with NO board change -> the move does NOTHING; trying an untried "
                      "direction  [no-frame-change stuck-break: the unchanged frame is the signal, not a colour guess]"
                      % _nochange[0], once_key="stuck_break")
        if ap0 is not None and actn in steer:                  # colour of the cell being moved INTO, read BEFORE the step
            dy, dx = steer[actn]; gpre = _g()
            rr = int(round(ap0[0])) + ((dy > 0) - (dy < 0)) * quantum
            cc = int(round(ap0[1])) + ((dx > 0) - (dx < 0)) * quantum
            if 0 <= rr < gpre.shape[0] and 0 <= cc < gpre.shape[1]:
                _dest_col = int(gpre[rr, cc])
        _bnc = _g() if actn in steer else None                 # frame BEFORE the step (no-change tracking, play area only)
        adapter.step(_name2act.get(actn, actn)); _spent[0] += 1
        h1 = _hud_units()
        if _bnc is not None:                                   # did the PLAY AREA (rows 2:56, HUD excluded) change at all?
            _anc = _g()
            if int((np.asarray(_bnc)[2:56] != np.asarray(_anc)[2:56]).sum()) == 0:
                _nochange[0] += 1; _stuck_tried[0].add(actn)   # board unchanged -> this action did NOTHING here
            else:
                _nochange[0] = 0; _stuck_tried[0] = set()      # board changed -> real effect, reset streak + tried set
        if 0 < h0 - h1 <= 8:                                   # a normal depletion tick -> learn the per-action rate
            _drops.append(h0 - h1)
        _traj.append(_g().copy())                              # recent trajectory holds the MATCHED frame just before a
        if len(_traj) > 40:                                    # win, so the win-condition induction can actually see it
            _traj.pop(0)
        ap1 = _apos()
        if actn in steer:                                      # feed the rolling A-B-A-B detector (action + landing cell)
            _act_hist.append(actn)
            _pos_hist.append((int(round(ap1[0])), int(round(ap1[1]))) if ap1 is not None else None)
        # LEARN PASSABILITY from the outcome (measure, don't guess walls by size): a directional move that produced ~no
        # displacement means the avatar is against an IMPASSABLE object -> record the colour just ahead as a wall and
        # GENERALISE it to every cell of that colour, then update the nav graph so we stop wasting actions on it. A move
        # that DID displace confirms the destination colour is passable floor.
        if ap0 is not None and ap1 is not None and actn in steer:
            dy, dx = steer[actn]; moved = abs(ap1[0] - ap0[0]) + abs(ap1[1] - ap0[1])
            _sm.visit(_cell(ap1)); _sm.record_neighbour(_cell(ap0), (dy, dx), moved >= 1.0)   # learn the per-cell map
            if moved >= 1.0:
                _last_dir[0] = (dy, dx)
            # TWO-FRAME PROPRIOCEPTIVE RECONCILIATION. Check the action's outcome in BOTH reference frames in lock-step:
            # egocentric (did I, the avatar, move one step as intended?) and allocentric (did the whole 64x64 frame change
            # consistently with that move?). They describe the SAME event under the translation transform (allocentric
            # coords - avatar pos = egocentric), so agreement is evidence the event is real and disagreement is the signal
            # that my model is wrong. Three outcomes, each a different correction -- this is the audit a human runs when
            # they hold the bird's-eye and the in-maze view at once, and it's what tells them "nothing's moving, stop".
            import os as _os
            if _os.environ.get("OURO_PROPRIOCEPT", "1") == "1" and (abs(dy) + abs(dx)) > 0 and gpre is not None:
                _gpost = np.asarray(_g()); _gpre = np.asarray(gpre)
                _chg = (_gpre != _gpost)
                _avpre = (_gpre == avatar); _avpost = (_gpost == avatar)
                # ALLOCENTRIC GROUND TRUTH: did the avatar's colour-region centroid ACTUALLY shift in the global frame?
                # (Trusting this over _apos -- the frame is what really happened; _apos can drift.) This is the bird's-eye
                # view auditing the egocentric intention in lock-step.
                _pc = np.argwhere(_avpre); _qc = np.argwhere(_avpost)
                if len(_pc) and len(_qc):
                    _disp = _qc.mean(0) - _pc.mean(0); _actual = float(abs(_disp[0]) + abs(_disp[1]))
                else:
                    _actual = moved
                # FULL-BODY POSITIONAL FOOTPRINT. The avatar is a MULTI-COLOUR composite (a colour-12 band between
                # colour-9 bands), but `avatar` names ONE colour, so the other-colour half of the body displaces every
                # step and is miscounted as "my move CO-TRIGGERED N cells elsewhere" -- a self-perception phantom that
                # was ~half of all L1 reasoning and inflated the world-model contradiction. Exclude the body's real
                # POSITIONAL footprint: the connected non-terrain blob(s) that TOUCH the avatar colour, in both frames.
                # Positional (not a colour mask) so a DISTANT same-colour object -- the key/lock, also colour 9 -- is a
                # separate component and stays counted. Falls back to the single-colour mask until terrain is known
                # (an unknown-terrain grow would swallow the whole board). Rule 0 confirmed (render): the 30 "elsewhere"
                # cells sit AT the avatar (dist 0), colours toggling 3<->9 -> the body's colour-9 half, not a mechanic.
                _bodymask = (_avpre | _avpost)
                _terr = set(_learned.get("floor", set())) | set(_learned.get("wall", set())) | set(walls)
                if _os.environ.get("OURO_SELF_FOOTPRINT", "1") == "1" and _terr:
                    try:
                        _board = np.zeros(_chg.shape, dtype=bool); _board[:56, :] = True
                        for _gg in (_gpre, _gpost):
                            _fg = _board & ~np.isin(_gg, list(_terr))
                            _seed = _fg & (_gg == avatar)
                            if _seed.any():
                                _lab, _nn = label(_fg)
                                _keep = [int(x) for x in np.unique(_lab[_seed]) if x]
                                if _keep:
                                    _bodymask = _bodymask | np.isin(_lab, _keep)
                    except Exception:
                        pass
                _elsewhere = int((_chg & ~_bodymask).sum())   # frame changes not explained by my body's footprint
                # REACTIVE DYNAMISM (wire invalidate() into the live path). decay()/invalidate() only ever fired in the
                # legacy ouroboros_integrated brain, so the composer's map had NO way to reopen a wall a trigger opens:
                # a cell it once measured BLOCKED stays BLOCKED forever, even after the frame shows it changed -- which
                # can strand the agent behind a cycling gate (e.g. the row-39 cell that toggles colour 5<->9). Mirror
                # the legacy pattern: a BOARD cell whose pixels changed AWAY from my own body footprint can no longer be
                # trusted as a wall -> reopen it to UNKNOWN so the planner re-checks and the agent re-measures it. Uses
                # the exact body footprint (not a distance heuristic) so my own motion never triggers a spurious reopen.
                if _os.environ.get("OURO_SM_INVALIDATE", "1") == "1":
                    try:
                        _obs = _chg & ~_bodymask
                        _obs[56:, :] = False                       # board only -- HUD budget/readout is not terrain
                        if _obs.any():
                            _q = max(1, int(round(quantum)))
                            _inval = set((int(round(_rr / _q)), int(round(_cc / _q))) for _rr, _cc in np.argwhere(_obs))
                            if _inval:
                                _sm.invalidate(_inval)
                    except Exception:
                        pass
                if _os.environ.get("OURO_PROP_DEBUG", "0") == "1" and _elsewhere > 12:
                    # RULE 0 instrumentation (temporary): does masking the FULL body colour-set (av_cols)
                    # collapse 'elsewhere'? If so, the co-trigger is the body's other colour leaking past the
                    # single-colour mask -- a self-perception phantom, not a real mechanic.
                    _avF = np.zeros_like(_chg)
                    for _bc in av_cols:
                        _avF |= (_gpre == _bc) | (_gpost == _bc)
                    _else_full = int((_chg & ~_avF).sum())
                    _elsecells = _chg & ~(_avpre | _avpost)
                    _histpre = {}; _histpost = {}
                    _pts = np.argwhere(_elsecells)
                    for _rr, _cc in _pts:
                        _histpre[int(_gpre[_rr, _cc])] = _histpre.get(int(_gpre[_rr, _cc]), 0) + 1
                        _histpost[int(_gpost[_rr, _cc])] = _histpost.get(int(_gpost[_rr, _cc]), 0) + 1
                    # spatial spread of the elsewhere cells + distance from the avatar centroid
                    if len(_pts):
                        _bb = (int(_pts[:, 0].min()), int(_pts[:, 0].max()), int(_pts[:, 1].min()), int(_pts[:, 1].max()))
                        _acen = np.argwhere(_avpost); _ac = _acen.mean(0) if len(_acen) else np.array([-1, -1])
                        _cen = _pts.mean(0)
                        _dist = round(float(abs(_cen[0] - _ac[0]) + abs(_cen[1] - _ac[1])), 1)
                    else:
                        _bb = None; _dist = -1
                    _emit(adapter, "PROP-DEBUG  else=%d  from(pre-colours)=%s  to(post-colours)=%s  bbox=%s  dist-from-avatar=%s"
                          % (_elsewhere, _histpre, _histpost, _bb, _dist))
                sr = (dy > 0) - (dy < 0); sc = (dx > 0) - (dx < 0)
                r = int(round(ap0[0])) + sr * quantum; c = int(round(ap0[1])) + sc * quantum
                if _actual >= 1.0:
                    # VALIDATED: intended move + allocentric shift agree -> destination colour is walkable FLOOR.
                    # AXIOM GUARD: a colour already known to be a WALL (terrain-perceived OR bump-confirmed) is NEVER
                    # relabelled floor by a single (multi-cell-avatar-noisy) 'moved-onto' read -- wall evidence, which
                    # is a hard can't-pass fact, dominates. This stops the colour-5-as-floor corruption the frame showed.
                    _reconcile_state[0] = "moved"
                    if (_dest_col is not None and _dest_col not in _learned["floor"] and _dest_col != avatar
                            and _dest_col not in av_cols and _dest_col not in _learned["wall"] and _dest_col not in walls):
                        _learned["floor"].add(_dest_col)
                        _emit(adapter, "PASSABLE  moved onto colour %d -> walkable FLOOR; AXIOM: same colour => same "
                              "passability, so ALL colour-%d cells are floor  [two-frame check: intent and shift agree]"
                              % (_dest_col, _dest_col), once_key="floor_%d" % _dest_col)
                    if _elsewhere > 12:                            # moved AND a chunk changed elsewhere -> a mechanic co-fired
                        _emit(adapter, "PROPRIOCEPT  moved as intended, but %d cells changed ELSEWHERE too -> my move CO-"
                              "TRIGGERED something; noting it for cause-analysis" % _elsewhere,
                              once_key="cofire_%d" % (_elsewhere // 12))
                else:
                    # AGREED-NULL: I intended to move and the allocentric view confirms the avatar did NOT shift -> a
                    # blocker is positively AT the cell ahead. Signal STOP (grind-kill) and learn the wall. HUD noise
                    # elsewhere doesn't change the verdict -- the avatar frame is what matters for 'did I move'.
                    _reconcile_state[0] = "blocked"
                    if 0 <= r < _gpost.shape[0] and 0 <= c < _gpost.shape[1]:
                        wcol = int(_gpost[r, c])
                        if (wcol != avatar and wcol not in av_cols and wcol not in _learned["floor"]
                                and int((_gpost == wcol).sum()) >= 100 and wcol not in _learned["wall"]):
                            _learned["wall"].add(wcol); walls.add(wcol); _learned["floor"].discard(wcol)
                            _emit(adapter, "PROPRIOCEPT  intended %s; allocentric view confirms the avatar did NOT move -> a "
                                  "WALL (colour %d) is AT (%d,%d). Learned it; re-planning, not grinding" %
                                  (_actdir.get(actn, actn), wcol, r, c), once_key="wall_%d" % wcol)
                    if _elsewhere > 12:
                        # I didn't move, yet a chunk changed elsewhere -> my action had a NON-LOCAL effect (hidden mechanic)
                        _emit(adapter, "PROPRIOCEPT  I did NOT move, yet %d cells changed ELSEWHERE -> my action had a NON-"
                              "LOCAL effect (a hidden mechanic?); hypothesise the cause rather than retry" % _elsewhere,
                              once_key="surprise_%d" % (len(_visited) // 16))
        if ap1 is not None:
            _visited.append((int(round(ap1[0])), int(round(ap1[1]))))
            if len(_visited) > 60:
                _visited.pop(0)
        c = getattr(adapter._obs, "levels_completed", 0) or 0
        if c > _base_ctr and _won[0] is None:
            raw = np.array(getattr(adapter._obs, "frame", []))
            _won[0] = [np.asarray(l).copy() for l in (list(raw) if raw.ndim == 3 else [raw])]
        try:
            _hud_feed()                                        # every action, not just the market's own
        except Exception:
            pass

    def _rate():
        import statistics as _stt
        return _stt.median(_drops) if len(_drops) >= 3 else 4.0

    def _budget_actions():
        """ACTIONS remaining this life -- from the ONE budget model, which everything else also reads.

        This used to own a private model: `_hud_units() / _rate()`, area over a guessed constant, which returned 21
        on a board that gives 42. It was unreachable from outside this closure, so the market grew a SECOND model to
        answer the same question, and the two disagreed for hours while each stayed internally consistent. One model
        now, read by both. Merging them is subtractive -- the only kind of change that cannot add a bug it did not
        already have.
        """
        try:
            import budget_model as _BM
            _m = _BM.get(adapter)
            n = _m.bar_actions()
            if n:
                if _m.one_life() and not getattr(_m, "_said_life", False):
                    _m._said_life = True
                    _emit(adapter, "BUDGET  the longest meter I have SEEN so far = %d actions (measured off the "
                                   "bar's LENGTH, not its area over a guessed rate). This is a floor, not the "
                                   "capacity: it can only rise, and it is not settled until I have seen a full "
                                   "refill. meter colour %s, lives colour %s, %s lives in hand."
                          % (_m.one_life(), _m.meter, _m.lives, _m.lives_left()))
                return float(n)
        except Exception:
            pass
        return _hud_units() / 2.0                  # fallback only: the bar is 2 rows tall

    def _floor_now():
        """The PERCEIVED walkable colours: learned floor plus a safe frame-read seed so the map is right before the first
        move. The seed is the large-area colour that dominates the avatar's immediate 4-neighbours (the corridor it sits
        in) -- taken only when it clearly wins, so a wall is never mistaken for floor."""
        fl = set(int(x) for x in _learned["floor"])
        import os as _os
        if _os.environ.get("OURO_FLOOR_INCLUSION", "1") != "1":
            return set()                                       # A/B: fall back to exclusion (bump-learned walls)
        ap = _apos()
        if ap is not None:
            g = np.asarray(_g()); H, W = g.shape; ar, ac = int(round(ap[0])), int(round(ap[1]))
            from collections import Counter
            nb = Counter()
            for dy, dx in ((quantum, 0), (-quantum, 0), (0, quantum), (0, -quantum)):
                r, c = ar + dy, ac + dx
                if 0 <= r < H and 0 <= c < W:
                    v = int(g[r, c])
                    if v != avatar and v not in av_cols and v not in _learned["wall"]:
                        nb[v] += 1
            if nb:
                col, n = nb.most_common(1)[0]
                if n >= 2 and int((g == col).sum()) > 200:     # appears on >=2 sides and is a large region -> a corridor
                    fl.add(col)
        try:
            fl -= set(int(w) for w in walls)                   # AXIOM: a known WALL colour is NEVER floor -- so the
        except Exception:
            pass                                               # pathfinder (inclusion) can never route the avatar onto
        fl -= set(int(w) for w in _learned["wall"])            # a wall, no matter what the noisy floor-learner added
        return fl

    def _navview():
        """The BoardView navigation.py wants. Built here because this is where the board is known."""
        import navigation as _NAV
        return _NAV.BoardView(grid=_g, apos=_apos, blocked=_sm_blocked, quantum=quantum, steer=steer,
                              walls=walls, passable=passable, floor=floor, edges=_sm_edges)

    def _path_cost(target_px):
        """Delegates to navigation.path_cost.

        This was extracted into navigation.py earlier in this session, unit-tested with no game attached, and then
        left unwired -- so the composer went on calling its own nested copy and the module became decoration. That is
        the exact failure this session has been diagnosing in everyone else's code, committed here, hours after
        naming it. Two implementations of one thing is how the budget model came to disagree with itself for hours.
        One implementation now.
        """
        try:
            import navigation as _NAV
            return _NAV.path_cost(_navview(), target_px)
        except Exception:
            return _path_cost_local(target_px)

    def _path_cost_local(target_px):
        ap = _apos()
        if ap is None:
            return None
        p = _avatar_pathfind(_g(), ap, target_px, steer, quantum, walls, blocked=_sm_blocked(), floor=_floor_now(),
                             edges=_sm_edges())
        return len(p) if p else None

    _actdir = {}
    for _a2, _v2 in steer.items():
        _u2 = (0 if _v2[0] == 0 else (1 if _v2[0] > 0 else -1), 0 if _v2[1] == 0 else (1 if _v2[1] > 0 else -1))
        _actdir[_a2] = _DIR_NAME.get(_u2, str(_a2))

    def _summarize(path):
        from itertools import groupby
        return " ".join("%s\u00d7%d" % (_actdir.get(a, a), len(list(gr))) for a, gr in groupby(path)) or "(0)"

    _blocked_targets = _persist.setdefault("blocked_targets", {})   # what the what-if proved unreachable (survives the solve)

    def _closest_reachable(target_px):
        """Delegates to navigation.closest_reachable (same story as _path_cost)."""
        try:
            import navigation as _NAV
            r = _NAV.closest_reachable(_navview(), target_px, emit=lambda m: _emit(adapter, m, once_key="reach_%s" % str(target_px)))
            if r:
                return r
        except Exception:
            pass
        return _closest_reachable_local(target_px)

    def _closest_reachable_local(target_px):
        """Flood-fill the avatar's reachable cells (same passable model as the pathfinder) and return the reachable cell
        CLOSEST to the target -- i.e. HOW CLOSE we can actually get. The gradient behind 'how close did we get'."""
        ap = _apos()
        if ap is None:
            return None
        gg = np.asarray(_g()); H, W = gg.shape
        wall = set(int(w) for w in walls); blk = _sm_blocked() or set()
        dirs = []
        for _a, (dy, dx) in (steer or {}).items():
            uy = 0 if dy == 0 else (quantum if dy > 0 else -quantum)
            ux = 0 if dx == 0 else (quantum if dx > 0 else -quantum)
            if (uy, ux) != (0, 0):
                dirs.append((uy, ux))
        if len(dirs) < 4 or quantum < 1:
            return None
        def passable(r, c):
            if not (0 <= r < H and 0 <= c < W) or int(gg[r, c]) in wall:
                return False
            return (int(round(r / quantum)), int(round(c / quantum))) not in blk
        from collections import deque
        s = (int(round(ap[0])), int(round(ap[1]))); t = (int(round(target_px[0])), int(round(target_px[1])))
        seen = {s}; dq = deque([s]); best = s; bestd = abs(s[0] - t[0]) + abs(s[1] - t[1])
        while dq:
            r, c = dq.popleft()
            for dy, dx in dirs:
                nr, nc = r + dy, c + dx
                if (nr, nc) in seen or not passable(nr, nc):
                    continue
                seen.add((nr, nc)); dq.append((nr, nc))
                d = abs(nr - t[0]) + abs(nc - t[1])
                if d < bestd:
                    bestd = d; best = (nr, nc)
        return {"closest": best, "gap": int(bestd), "reachable": len(seen)}

    def _candidate_doors(target_px):
        """The board is partitioned into floor regions by walls. When a target sits in another region, the ONLY ways
        across are the thin wall-gaps (doorways) bordering the avatar's region. Enumerate those DISTINCT doorways toward
        the target -- the small, finite set of 'possible paths' to TRY (not an open hill-climb). Returns a list of
        (reachable_side_cell, door_cell) sorted by how much closer the door gets us to the target."""
        ap = _apos()
        if ap is None:
            return []
        gg = np.asarray(_g()); H, W = gg.shape
        wall = set(int(w) for w in walls); blk = _sm_blocked() or set()
        q = max(1, int(round(quantum)))
        def floor(r, c):
            return 0 <= r < H and 0 <= c < W and int(gg[r, c]) not in wall and \
                   (int(round(r / q)), int(round(c / q))) not in blk
        # reachable set from avatar
        from collections import deque
        s = (int(round(ap[0])), int(round(ap[1]))); seen = {s}; dq = deque([s])
        dirs = [(q, 0), (-q, 0), (0, q), (0, -q)]
        while dq:
            r, c = dq.popleft()
            for dy, dx in dirs:
                nr, nc = r + dy, c + dx
                if (nr, nc) not in seen and floor(nr, nc):
                    seen.add((nr, nc)); dq.append((nr, nc))
        t = (int(round(target_px[0])), int(round(target_px[1])))
        # a doorway: a reachable floor cell whose neighbour ACROSS 1-2 wall cells is floor NOT in our reachable set and
        # closer to the target. Record the reachable-side cell (where to stand) and the door direction.
        cands = []
        for (r, c) in seen:
            for dy, dx in dirs:
                w1 = (r + dy, c + dx); beyond = (r + 2 * dy, c + 2 * dx); beyond2 = (r + 3 * dy, c + 3 * dx)
                if floor(*w1):
                    continue                                   # not a wall -> not a doorway here
                opened = beyond if floor(*beyond) else (beyond2 if floor(*beyond2) else None)
                if opened is None or opened in seen:
                    continue
                # is crossing here progress toward the target?
                d_here = abs(r - t[0]) + abs(c - t[1]); d_open = abs(opened[0] - t[0]) + abs(opened[1] - t[1])
                if d_open < d_here:
                    cands.append(((r, c), w1, d_open))
        # cluster nearby doorways into DISTINCT doors (merge within ~2*quantum)
        cands.sort(key=lambda x: x[2])
        doors = []
        for cell, wcell, d in cands:
            if all(abs(cell[0] - dc[0][0]) + abs(cell[1] - dc[0][1]) > 2 * q for dc in doors):
                doors.append((cell, wcell, d))
        return doors[:4]

    def _act_toward(dir_yx):
        try:
            import navigation as _NAV
            r = _NAV.act_toward(_navview(), dir_yx)
            if r is not None:
                return r
        except Exception:
            pass
        return _act_toward_local(dir_yx)

    def _act_toward_local(dir_yx):
        """The action whose steer direction best matches a desired (dy,dx) unit direction -- for stepping at a doorway."""
        best = None; bestscore = -1
        for a, (dy, dx) in (steer or {}).items():
            uy = 0 if dy == 0 else (1 if dy > 0 else -1); ux = 0 if dx == 0 else (1 if dx > 0 else -1)
            if (uy, ux) == tuple(dir_yx):
                return a
            score = (uy == dir_yx[0]) + (ux == dir_yx[1])
            if score > bestscore:
                bestscore = score; best = a
        return best

    def _reach_escalate(target_px, reason, cap):
        import os as _os
        if _os.environ.get("OURO_NAV_ESCALATE", "1") != "1":
            return False                                       # A/B: escalation OFF -> original give-up (no doorway drive)
        """SOLVABILITY AXIOM (ARC games are beatable by construction -> a path EXISTS): 'unreachable' is never a reason to
        go limp. Instead: (1) how close can we get? (2) what unfactored resource/condition would close the gap -- a
        BUDGET+ booster to afford a detour, or an unprobed trigger/door to open the route? (3) press to the frontier and
        keep the target ALIVE, never inert. This is inventing out of the box, not concluding impossibility."""
        info = _closest_reachable(target_px)
        _blocked_targets[(int(round(target_px[0])), int(round(target_px[1])))] = reason   # keep the target ALIVE
        _ba = _budget_actions()
        _boost = None
        try:
            # The avatar causal map is nested at patterns["avatar_cmap"]; iterating the PARENT's values compares
            # `.get("effect")` against dicts that have no such key, so this lookup returned None every single time and
            # the budget planner believed no booster existed anywhere.
            _cm = (_GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("avatar_cmap", {}) or {}
            _boost = next((a for a in _cm.values()
                           if isinstance(a, dict) and a.get("effect") == "budget"
                           and (a.get("insts") or a.get("inst"))), None)
        except Exception:
            _boost = None
        if info is None or info["gap"] >= abs(int(round(_apos()[0])) - int(round(target_px[0]))) + abs(int(round(_apos()[1])) - int(round(target_px[1]))):
            if reason:
                _emit(adapter, "REACH-ESCALATE  %s: (%d,%d) not reachable from here yet. SOLVABILITY AXIOM: a path EXISTS "
                      "(ARC is beatable) -> needs a PREREQUISITE (an unprobed trigger/door to open the route)%s. Target "
                      "kept ALIVE, not inert" % (reason, int(target_px[0]), int(target_px[1]),
                      " or the known BUDGET+ booster to afford a longer detour" if _boost else ""),
                      once_key="escalate_%s" % str(reason))
            return False
        cx, cy = info["closest"]; gap = info["gap"]
        doors = _candidate_doors(target_px)
        if doors:
            if reason:
                _emit(adapter, "ENUMERATE-PATHS  %s: target sits in a SEPARATE region; %d candidate doorway(s) bridge toward "
                      "it %s -- a FINITE path set. COMMITTING to walk + test each in turn (not hill-climbing)" %
                      (reason, len(doors), [dc[1] for dc in doors[:4]]), once_key="paths_%s" % str(reason))
            _t = (int(round(target_px[0])), int(round(target_px[1])))
            for _i, (cell, wcell, dd) in enumerate(doors):
                if not _goto(cell, cap=80, reason=None, _escalate=False):   # COMMIT: walk fully to this doorway's near side
                    continue
                _pre = _apos()                                              # ATTEMPT to cross the gap
                _dir = (1 if wcell[0] > cell[0] else (-1 if wcell[0] < cell[0] else 0),
                        1 if wcell[1] > cell[1] else (-1 if wcell[1] < cell[1] else 0))
                _act = _act_toward(_dir); _crossed = False
                if _act is not None:
                    _stepw(_act)
                    _post = _apos()
                    if _post is not None and (abs(_post[0] - _pre[0]) + abs(_post[1] - _pre[1])) > 0:
                        _crossed = True
                if _crossed or (_path_cost(target_px) is not None):
                    if reason:
                        _emit(adapter, "PATH-TRY  doorway %d/%d @(%d,%d): PASSABLE/opened -> route to target found, pursuing"
                              % (_i + 1, len(doors), int(wcell[0]), int(wcell[1])))
                    _blocked_targets.pop(_t, None)
                    return _goto(target_px, cap=cap, reason=None, _escalate=False)
                if reason:
                    _emit(adapter, "PATH-TRY  doorway %d/%d @(%d,%d): BLOCKED -- real wall, avatar can't walk through -> "
                          "this path needs an OPENER (trigger); trying next candidate"
                          % (_i + 1, len(doors), int(wcell[0]), int(wcell[1])), once_key="try_%d_%s" % (_i, str(reason)))
            if reason:
                _emit(adapter, "PATHS-EXHAUSTED  %s: all %d doorways walked + tested, none passable -> each is wall-locked; "
                      "the prerequisite is an OPENER (probe reachable triggers for a route-opener). Solvability holds: a "
                      "path EXISTS, so one of these opens" % (reason, len(doors)), once_key="exhaust_%s" % str(reason))
        if reason:
            _whatif = ("advance to the frontier and expand the map toward it" if gap > 0 else "at the frontier")
            _budget_note = ""
            if _boost is not None:
                _budget_note = "; a booster (+budget) could fund the detour" if _ba < gap else ""
            _emit(adapter, "REACH-ESCALATE  %s: directly UNREACHABLE, CLOSEST reachable (%d,%d) is gap %d from (%d,%d) "
                  "[got this close]. WHAT-IF: %s%s. SOLVABILITY AXIOM: the path exists -> pressing in, not giving up"
                  % (reason, cx, cy, gap, int(target_px[0]), int(target_px[1]), _whatif, _budget_note),
                  once_key="escalate_%s" % str(reason))
        return _goto((cx, cy), cap=cap, reason=None, _escalate=False)   # partial progress -> frontier expansion

    def _goto(target_px, cap=None, reason=None, _escalate=True):
        # cap was 40. A life is 42. ONE navigation call could spend 95% of a life and the caller would never know
        # it had happened -- there is no plan in which walking to a single cell is worth an entire life, and if
        # there were, the agent should have to say so. Half a life, measured off this game's bar.
        if cap is None:
            try:
                import budget_model as _BMg
                cap = _BMg.get(adapter).actions_fraction(0.5, lo=6, default=20)
            except Exception:
                cap = 20
        # EVERY NAMED OBJECTIVE IS A DECISION POINT. The residual used to fire once at the tail of this 1900-line
        # function -- once per ~900 actions -- so no residual could ever reproduce and CUSUM could never license a
        # mint. The engine's own docstring said the buffer resets "at each decision point"; this is that point.
        if reason and _rr is not None:
            try:
                _rr.open_objective(adapter, reason, _g(), footprint=[_apos()] if _apos() else [])
            except Exception:
                pass
        _arr = _goto_inner(target_px, cap=cap, reason=reason, _escalate=_escalate)
        if reason and _rr is not None:
            try:
                _tr = {}
                _cm0 = (_GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("avatar_cmap", {}) or {}
                for _t, _at in _cm0.items():
                    _ins = _at.get("insts") or ([_at.get("inst")] if _at.get("inst") else [])
                    if _ins:
                        _tr[str(_at.get("effect") or _t)] = [tuple(i) for i in _ins if i is not None]
                _rr.close_objective(adapter, bool(_arr), _g(),
                                    ctx_extra={"ctrl": avatar, "traces": _tr, "budget": budget})
            except Exception:
                pass
        return _arr

    def _goto_inner(target_px, cap=20, reason=None, _escalate=True):
        # ALLOCENTRIC DRIVES, EGOCENTRIC FOLLOWS. Plan a route on the perceived floor (allocentric authority) and COMMIT
        # to it; the two-frame reconciliation verifies each step (egocentric follower). A 'blocked' divergence means the
        # plan met an obstacle the map didn't know -- the reconciliation has just LEARNED it -- so RE-PLAN from here and
        # keep driving, rather than abandoning the target and dropping into egocentric wandering. The true traversable
        # map is thus built BY EXECUTION. Bounded, so a genuinely unreachable target still returns.
        import os as _os
        # WALK vs RUN is the AGENT's call, read from the situation -- not a gear the proctor bolts in place. RUN =
        # ballistic single plan: cheap, right for open floor where the map is trusted. WALK = committed re-driven route:
        # re-plan around each obstacle the follower learns and keep driving. The old A/B ("baton") tried WALK ALWAYS-ON
        # and it hurt open-field coverage on L2 -- because it made the agent walk where it should have run. The fix is
        # not to pick the gear for it; it is to let the TERRAIN pick the gear THROUGH the agent's own progress signal:
        # start in RUN, and the first time the light plan DIVERGES (the egocentric follower measured a stall, or a wall
        # the map didn't know), that divergence IS the situation saying "this stretch is tight" -- so shift to WALK for
        # this target and keep driving, instead of abandoning it. Per-stretch, self-selected, whitebox. OURO_DRIVER_BATON
        # forces WALK from the first step (start already committed) for anyone who wants to pin it.
        _committed = _os.environ.get("OURO_DRIVER_BATON", "0") == "1"
        _first = True; _replans = 0; _steps = 0; _cap_total = max(cap, 60)
        while True:
            ap = _apos()
            if ap is None:
                return False
            if abs(ap[0] - target_px[0]) + abs(ap[1] - target_px[1]) <= quantum:
                break                                          # arrived (within one step of the target)
            path = _avatar_pathfind(_g(), ap, target_px, steer, quantum, walls, blocked=_sm_blocked(), floor=_floor_now(),
                                    edges=_sm_edges())
            if not path:
                if _first and _escalate:
                    return _reach_escalate(target_px, reason, cap)   # what-if (gated off by default) instead of limp
                if reason and _first:
                    _emit(adapter, "NAVIGATE  %s: target (%d,%d) UNREACHABLE on the known map -- no floor route" %
                          (reason, int(target_px[0]), int(target_px[1])))
                return False                                    # allocentric: no route on what we know -> stop
            if reason and _first:
                _emit(adapter, "NAVIGATE  %s: (%d,%d)\u2192(%d,%d) via %d-step route [%s]; costs %d of ~%.0f budget-actions"
                      % (reason, int(ap[0]), int(ap[1]), int(target_px[0]), int(target_px[1]),
                         len(path), _summarize(path), len(path), _budget_actions()))
            elif reason and _committed:
                _emit(adapter, "REROUTE  %s: obstacle learned mid-drive -> re-planned %d-step route around it (re-plan #%d) "
                      "[WALK mode: allocentric re-drives; the map is built by execution]" % (reason, len(path), _replans),
                      once_key="reroute_%d" % (_replans % 4))
            _first = False
            _blk = 0; _moved_any = False; _diverged = False
            _best_d = abs(ap[0] - target_px[0]) + abs(ap[1] - target_px[1]); _stall = 0
            for actn in path[:cap]:
                _reconcile_state[0] = None
                _q0 = _apos()
                _planned_move[0] = True                          # this step came from the allocentric plan -> AXIOM must
                try:                                             # not redirect it (it planned on floor already)
                    _stepw(actn)
                finally:
                    _planned_move[0] = False
                _steps += 1
                if _won[0] is not None:
                    return True
                _q1 = _apos()
                if _q1 is not None:
                    _d = abs(_q1[0] - target_px[0]) + abs(_q1[1] - target_px[1])
                    if _d < _best_d - 0.5:                       # EGOCENTRIC PROGRESS: genuinely closer to the goal
                        _best_d = _d; _stall = 0
                    else:
                        _stall += 1                              # moving (or not) but NOT getting closer
                if _q0 is not None and _q1 is not None and (abs(_q1[0] - _q0[0]) + abs(_q1[1] - _q0[1])) >= 1.0:
                    _moved_any = True
                if _stall >= 6:                                  # PROGRESS-STALL := the real divergence. The follower
                    _emit(adapter, "STALL  %d steps without getting closer to (%d,%d) -> the route isn't making PROGRESS "  # judges
                          "(egocentric follower measures progress, not just motion) -> abandon this route, re-plan/explore"  # progress,
                          % (_stall, int(target_px[0]), int(target_px[1])), once_key="stall_%d" % (_steps // 12))  # not motion
                    _diverged = True; break
                if _reconcile_state[0] == "blocked":            # egocentric follower: divergence -> wall AT the cell ahead
                    _blk += 1                                   # (already learned). Stop executing the stale route.
                    if _blk >= 2:
                        _diverged = True; break
                else:
                    _blk = 0
                if _steps >= _cap_total:
                    break
            _replans += 1
            if _diverged and not _committed:                   # RUN just stalled here -> the situation says WALK.
                _committed = True                              # shift gear (agent-selected, from its own progress
                if reason:                                     # signal), re-plan from here, keep driving the target.
                    _emit(adapter, "GEARSHIFT  %s: the ballistic route stalled (a constriction, or a wall the map "
                          "didn't know) -> shifting RUN->WALK: a committed re-driven route around it, not abandoning "
                          "the target  [the terrain picks the gear, through my own stall signal -- not a fixed flag]"
                          % reason, once_key="gearshift_%d" % (_steps // 12))
                continue                                        # re-enter the drive loop in WALK mode
            if not _committed:                                 # RUN, no divergence -> this plan arrived or exhausted
                break
            if _steps >= _cap_total or _replans > 8:
                break                                          # bounded drive budget (WALK)
            if not _moved_any and _replans >= 3:
                return False                                   # three re-plans, zero displacement -> genuinely stuck
        for _ in range(3):                                     # center exactly on the target cell
            ap = _apos()
            if ap is None:
                break
            dy, dx = target_px[0] - ap[0], target_px[1] - ap[1]
            if abs(dy) + abs(dx) <= 1:
                break
            if abs(dy) >= abs(dx):
                act = next((a for a, v in steer.items() if v[0] != 0 and (v[0] < 0) == (dy < 0)), None)
            else:
                act = next((a for a, v in steer.items() if v[1] != 0 and (v[1] < 0) == (dx < 0)), None)
            if act is None:
                break
            _stepw(act)
            if _won[0] is not None:
                return True
        return True

    def _cell(px):
        return (int(round(px[0] / quantum)), int(round(px[1] / quantum)))   # pixel -> movement-lattice cell for the map

    def _dir_to_action(d):
        for a, v in steer.items():
            if ((v[0] > 0) - (v[0] < 0), (v[1] > 0) - (v[1] < 0)) == (d[0], d[1]):
                return a
        return None

    def _hud_feed():
        """Give the budget inducer every transition the agent actually makes."""
        st = getattr(adapter, "_micro_market", None)
        if not st or not st.get("arena") or _hud_before[0] is None:
            return
        try:
            import micro_market as _MM
            after = _g()
            for ch in st["arena"].chains:
                if isinstance(ch, _MM.Q1Hud):
                    ch.observe(st.get("ctx"), _exec_ref[0], _hud_before[0], after)
        except Exception:
            pass

    adapter._hud_feed = _hud_feed

    _adapter_ref = adapter

    def _market_ctx():
        """Bridge: expose the composer's ALREADY-MEASURED perception to the micro market, so its chains are wrappings
        of machinery that works rather than fresh guesses. (The rungs build had the whole coordination layer and scored
        0.015 because its knowledge sources were not competent; coordination is second-order.)"""
        class _Ctx(object):
            quantum = _q_ref[0]
            spatial = _sm
            frame = None
            adapter = _adapter_ref                 # so any chain can reach the ONE budget model

            def avatar_pos(self, f=None):
                """MUST read the frame it is handed. The first version ignored `f` and returned the live position, so
                a chain comparing before-vs-after saw the SAME position twice, inferred zero displacement, and
                concluded every move was blocked. The induced model could never form -- not because the idea was
                wrong, but because the bridge never let it see a difference. Every 0.000 hit-rate measured before
                this fix was measuring that bug, not the model."""
                if f is None:
                    return _apos()
                try:
                    import numpy as _np
                    m = (_np.asarray(f) == avatar)
                    if not m.sum():
                        return None
                    w = _np.where(m)
                    return (float(w[0].mean()), float(w[1].mean()))
                except Exception:
                    return None
            def hud_units(self, f=None):
                return _hud_units(f) if f is not None else _hud_units()
            def hud_rate(self):
                try:
                    return float(_rate())
                except Exception:
                    return None
            def read_prop(self, f, at):
                try:
                    pr = _read_at(at)
                    return pr.get("orient") if pr else None
                except Exception:
                    return None
            def is_trigger_step(self, ap, d):
                """Would this step land on a cell I have SEEN cycle the tracked property?

                This returned False. Unconditionally. So TriggerChain -- the one carving that reads this board by
                "stepping HERE changes THAT", which is the entire mechanic of this game -- could never advocate, and
                it was never enrolled in the arena either, so nothing ever noticed that it was inert. Two independent
                reasons the game's actual mechanic had no voice in the market.

                The agent has known where the triggers are the whole time: avatar_cmap holds trigger -> effect with
                instances, learned live. The knowledge was in the system and not in the carving -- the same shape as
                the wall knowledge living in a veto chain instead of inside the steer rule as context.
                """
                try:
                    if ap is None or not d:
                        return False
                    tgt = (ap[0] + d[0], ap[1] + d[1])
                    cm = (_GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("avatar_cmap", {}) or {}
                    tol = max(1.0, quantum / 2.0)
                    for _at in cm.values():
                        # A BOOSTER IS NOT A TRIGGER. This matched ANY atom in the map, and every atom the agent has
                        # ever learned on this board has effect='budget' -- so it would have called every booster a
                        # key-trigger and staked that the key cycles when it does not. A carving that fires on the
                        # wrong object is worse than one that abstains: it manufactures evidence for a rule it made up.
                        if _at.get("effect") in (None, "budget"):
                            continue
                        for _i in (_at.get("insts") or ([_at.get("inst")] if _at.get("inst") else [])):
                            if _i is None:
                                continue
                            if abs(_i[0] - tgt[0]) <= tol and abs(_i[1] - tgt[1]) <= tol:
                                return True
                    return False
                except Exception:
                    return False
            def is_novel(self, cell):
                try:
                    return _sm.cell.get(tuple(cell)) is None
                except Exception:
                    return True
            def snapshot(self):
                return _g()
            def reward_signal(self, before, after):
                """Q2's ground truth. Deliberately NOT a proxy: a level taken is the only reward the game issues, a
                death the only punishment. Everything else (coverage, novelty, distance) is a story we tell ourselves
                about progress, and pricing valence on a story is how a market learns to want the wrong thing."""
                try:
                    lv = _levels_now()
                    if lv > self._lvl_seen:
                        self._lvl_seen = lv
                        return 1.0
                    st = str(getattr(getattr(adapter, "_obs", None), "state", "") or "").upper()
                    if "GAME_OVER" in st:
                        return -1.0
                except Exception:
                    pass
                return 0.0
            def rarest_colour(self):
                """Q3's salience, exactly as the published trace scores it: rarity. 'rare_color_10 ... only 0.2% of
                frame' -> salience 0.96. Excludes the HUD rows and the background."""
                try:
                    import numpy as _np
                    g = _np.asarray(_g())[2:56]
                    vals, cnts = _np.unique(g, return_counts=True)
                    tot = float(g.size)
                    best = None
                    for v, ct in zip(vals, cnts):
                        frac = ct / tot
                        if frac < 0.001 or frac > 0.20:
                            continue                       # too rare to be an object; too common to be salient
                        if best is None or frac < best[1]:
                            best = (int(v), float(frac))
                    return best
                except Exception:
                    return None
        c = _Ctx(); c._lvl_seen = _levels_now(); c.frame = _g(); return c

    def _induced_report():
        """What the market LEARNED about our own actions, next to what we ASSUME. Reported rather than acted on
        first: the assumed model has been wrong and unopposed for the whole project, and replacing it on the strength
        of one number would repeat that mistake with a different incumbent."""
        st = getattr(adapter, "_micro_market", None)
        if not st or not st.get("arena"):
            return {}
        out = {}
        try:
            import micro_market as _MM
            for ch in st["arena"].chains:
                if isinstance(ch, _MM.Q1Salience) and ch.disp is not None:
                    asm = steer.get(ch.action)
                    assumed = None
                    if asm is not None:
                        assumed = (((asm[0] > 0) - (asm[0] < 0)) * quantum,
                                   ((asm[1] > 0) - (asm[1] < 0)) * quantum)
                    out[str(ch.action)] = {"induced": list(ch.disp), "assumed": list(assumed) if assumed else None,
                                           "n_obs": ch.n_obs, "consistent": ch.agree}
        except Exception:
            pass
        return out

    adapter._induced_report = _induced_report

    def _hud_report():
        """What the agent has WORKED OUT about its own budget, vs what it currently plans with."""
        st = getattr(adapter, "_micro_market", None)
        if not st or not st.get("arena"):
            return {}
        try:
            import micro_market as _MM
            for ch in st["arena"].chains:
                if isinstance(ch, _MM.Q1Hud):
                    r = ch.report()
                    r["assumed_rate"] = _rate()
                    r["assumed_actions_left"] = _budget_actions()
                    return r
        except Exception:
            pass
        return {}

    adapter._hud_report = _hud_report

    def _percept_report():
        st = getattr(adapter, "_micro_market", None)
        if not st or not st.get("percepts"):
            return {}
        r = st["percepts"].report()
        try:
            r["poses"] = {c.id: c.pose() for c in st["arena"].chains[:6]}
        except Exception:
            pass
        try:
            r["niche"] = {"naive_wins": st["arena"].naive_wins, "proven_wins": st["arena"].proven_wins}
        except Exception:
            pass
        return r

    adapter._percept_report = _percept_report

    def _macro_sync(st):
        """Pour what the composer PERCEIVES into what the macro market can COMMIT to.

        The composer already finds boosters and triggers -- it has always found them. What it has never had is
        anywhere to put them that outlives the life that found them, so every death threw the map of the board away
        and the next life started by looking for the same booster in the same place. This is the join.
        """
        mm = st.get("macro")
        if mm is None:
            return
        try:
            # The avatar causal map lives in the MOLECULE registry (patterns["avatar_cmap"]) -- the game-agnostic
            # store, because "objects that look like this are boosters" is a claim about the world, not about a board.
            # Earlier this read working memory and found {}, so the macro shell learned every trigger and not one
            # booster: "it never thinks to pick up the booster", reproduced by reading the wrong dict.
            _cm = (_GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("avatar_cmap", {}) or {}
            for _tt, _atom in (_cm.items() if hasattr(_cm, "items") else []):
                if not hasattr(_atom, "get"):
                    continue
                _kind = "booster" if (_atom.get("effect") == "budget") else "trigger"
                for _bi in (_atom.get("insts") or ([_atom.get("inst")] if _atom.get("inst") else [])):
                    if _bi is None:
                        continue
                    _site = mm.discovery.note(_cell(_bi), _kind, epoch=st["epoch"])
                    if _kind == "booster":
                        _site["gain"] = _atom.get("gain")      # what the CLASS is worth, on every member of it
        except Exception:
            pass
        try:
            for _t in (_mechanics(adapter).get("reached_triggers") or []):
                mm.discovery.note(tuple(_t), "trigger", epoch=st["epoch"])
        except Exception:
            pass

    def _macro_target(st):
        """The cell this life has COMMITTED to, if any. The micro market steers toward it instead of wandering."""
        mm = st.get("macro")
        if mm is None or mm.current is None:
            return None
        return mm.current.target

    def _market_explore():
        """MARKET-PRICED exploration. The frontier rule is ONE carving of the board asserting a monopoly: it always
        wins because nothing else is allowed to bid. Here the carvings compete and the FRAME settles them, at zero
        extra action cost -- every chain stakes on the step we were going to take anyway."""
        import os as _os_m
        if _os_m.environ.get("OURO_MICRO_MARKET", "0") != "1":
            return None
        try:
            import micro_market as _MM
        except Exception:
            return None
        ap = _apos()
        if ap is None:
            return None
        st = _mk_state
        if st.get("arena") is None:
            ctx = _market_ctx()
            chains = []
            for _a, _d in steer.items():
                chains.append(_MM.SteerChain(_a, _d))          # ASSUMED model: pos + direction*quantum. Measured over
                #                                                43 generations at a 0.000 hit-rate -- kept in the
                #                                                market precisely so it can be beaten on the record
                #                                                rather than retired on my say-so.
                chains.append(_MM.WallMemoryChain(_a, _d))     # measured dead-ends (vetoes, never advocates)
                chains.append(_MM.Q1Salience(_a))              # Q1: INDUCED model -- learns what the action does
                # "stepping HERE changes THAT" -- the carving that reads this board the way the board works, and it
                # was built, stubbed to False, and never added to this list. The target is the KEY: the property a
                # trigger cycles. Passed as a callable because the key is DISCOVERED, not known at construction --
                # a carving must be able to be built before the thing it is about has been found, or it can only ever
                # exist for boards we already understand.
                chains.append(_MM.TriggerChain(_a, _d, lambda: (_kl[0][0] if _kl[0] else None)))
            chains.append(_MM.BudgetChain(list(steer.keys())[0]))   # the HUD as a meter (pure observer)
            chains.append(_MM.Q1Hud())                         # Q1 on our OWN RESOURCES: induce meter/lives/rate
            chains.append(_MM.CommitmentChain(steer, lambda: _macro_target(st)))   # the MACRO shell's voice, which
            #                                                    must win its bids like anything else -- a plan that
            #                                                    cannot be outvoted is an order, not a strategy
            chains.append(_MM.Q2Valence())                     # Q2: what rewards / punishes
            chains.append(_MM.Q3Intervention(list(steer.keys())))   # Q3: interact with the most salient variable
            chains.append(_MM.Q4Rule())                        # Q4: the rule that explains it
            st["ctx"] = ctx
            st["arena"] = _MM.FrameArena(ctx, chains, emit=lambda m: _emit(adapter, m, once_key="mk_%d" % (st["n"] // 40)))
            st["evo"] = _MM.Evolution(st["arena"], emit=lambda m: _emit(adapter, m))
            st["pariah"] = _MM.PariahStore(emit=lambda m: _emit(adapter, m))
            st["macro"] = _MM.MacroMarket(emit=lambda m: _emit(adapter, m))
            # PLURAL VANTAGES. Three different answers to "where is the thing that moves", each able to be wrong,
            # each priced by the board. The colour percept is the incumbent and has never had a rival -- which is
            # exactly why it could never be discovered to be wrong.
            st["percepts"] = _MM.PerceptArena(
                [_MM.ColourPercept(avatar), _MM.DeltaPercept(), _MM.RarityPercept(),
                 _MM.ComponentPercept(avatar)],
                emit=lambda m: _emit(adapter, m))
        st["ctx"].quantum = _q_ref[0]
        st["ctx"].frame = _g()
        act, win = st["arena"].decide()
        if act is None:
            return None
        _lvl_before = _levels_now()
        st["n"] += 1
        st["epoch_actions"] += 1
        _f_before = _g()
        _pa = st.get("percepts")
        if _pa is not None:
            _d = steer.get(act)
            _disp = (((_d[0] > 0) - (_d[0] < 0)) * quantum, ((_d[1] > 0) - (_d[1] < 0)) * quantum) if _d else None
            _pa.stake(_f_before, st.get("prev_frame"), _disp)      # every vantage bets on ITS OWN reading
        _stepw(act)
        st["ctx"].frame = _g()
        if _pa is not None:
            _pa.settle(_g(), _f_before)                            # the board decides which vantage was right
        # Each chain's OWN encounter, in ITS OWN order -- I2a's path-dependence, which cannot exist while every
        # chain reads one shared percept and receives one shared outcome.
        try:
            for _ch in st["arena"].chains:
                _r = st["arena"].ledger.get(_ch.id)
                _ch.encounter(1.0 if _r.get("hits", 0.0) > getattr(_ch, "_last_hits", 0.0) else 0.0)
                _ch._last_hits = _r.get("hits", 0.0)
        except Exception:
            pass
        if _pa is not None:
            try:
                _pa.update_poses(st["arena"].chains)   # alpha moves, or I2a is unfalsifiable by construction
            except Exception:
                pass
        st["prev_frame"] = _f_before
        # LEARN from what was ACTUALLY executed -- always, whether or not it was what the market bid. This is how the
        # induced model gets built out of the agent's whole experience rather than the 2% of it that went to plan.
        st["arena"].observe_transition(_exec_ref[0], getattr(st["arena"], "last_before", None), _g())
        if _exec_ref[0] != act:
            # The pipeline substituted a different action (the stuck-break redirects a no-op). The chains staked on the
            # action we ASKED for; grading them against an action we never took convicts them of our substitution --
            # the same error as convicting a trigger we never reached. VOID, do not refute: an unpriced bid is honest,
            # a wrongly-priced one poisons every later selection that reads the ledger.
            st["arena"].void()
            _emit(adapter, "VOID  bids were staked on %s but the pipeline executed %s -> those stakes are void, not "
                  "refuted: a carving is not wrong because we did something else" % (act, _exec_ref[0]),
                  once_key="mk_void_%d" % (st["n"] // 50))
        else:
            st["arena"].settle()
        if _levels_now() > _lvl_before:
            st["wins_this_epoch"] += 1
        _epoch_check(st)
        return True

    def _levels_now():
        try:
            return int(getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0)
        except Exception:
            return 0

    def _epoch_check(st):
        """Delegates to epoch_loop.EpochLoop. The boundary logic was nested here and survived only because it kept
        its state on adapter._micro_market rather than in this closure -- a coin that landed the right way up in a
        file where the same coin landed wrong five times. Selection is the mechanism everything rests on; it should
        not be reachable only from inside one regime's 2002-line function."""
        _el = getattr(adapter, "_epoch_loop", None)
        if _el is None:
            try:
                import epoch_loop as _ELm
                _el = adapter._epoch_loop = _ELm.EpochLoop(emit=lambda m: _emit(adapter, m))
            except Exception:
                return
        rep = _el.step(adapter, st)
        if rep is None:
            return
        why = (_el.history[-1]["why"] if _el.history else "")
        # MACRO: price the life that just ended, then commit the next one. This is the only moment an attempt is
        # finished enough to be judged -- and the moment the previous attempt gets to inform the next.
        _mm = st.get("macro")
        if _mm is not None:
            try:
                _mm.settle_epoch(st["wins_this_epoch"], st["epoch"])
                _macro_sync(st)
                _mm.choose(st["epoch"])
            except Exception:
                pass
        _emit(adapter, "EPOCH %d ends -- %s. %d actions lived, %d level(s) taken. Selection now: %d carvings alive, "
              "%d retired, %d transfers. The population carries forward; only the life ended."
              % (st["epoch"], why, st["epoch_actions"], st["wins_this_epoch"],
                 rep.get("chains", 0), rep.get("culled", 0), rep.get("transfers", 0)),
              once_key="epoch_%d" % st["epoch"])
        st["epoch_actions"] = 0
        st["wins_this_epoch"] = 0

    def _explore_step():
        """ONE frontier-driven exploration step (goal-UNKNOWN traversal). The agent CHOOSES the frontier priority from
        its own situation, the same run->walk escalation one rung up: start on the CHEAP nearest-frontier sweep, and if
        that sweep runs a while without the objective appearing, escalate to the INFO-GAIN frontier -- head to the
        reachable edge that reveals the MOST unknown per step, so a far untouched chamber (the L1 box) gets sought
        instead of grinding every local nook. Not a proctor flag; the stall picks the gear."""
        ap = _apos()
        if ap is None:
            return False
        _xm = _game_mem(adapter); _xn = _xm.get("_explore_n", 0) + 1; _xm["_explore_n"] = _xn
        _info = _xn >= 12                                       # cheap sweep first; escalate to info-gain if it drags on
        d = _sm.frontier_step(_cell(ap), prefer=_last_dir[0], info_gain=_info)
        if d is None:                                          # reachable map fully explored
            return False
        act = _dir_to_action(d)
        if act is None:
            return False
        _emit(adapter, "EXPLORE  %s frontier step %s toward UNCHARTED territory  [%s; coverage=%s]"
              % ("INFO-GAIN" if _info else "nearest", _DIR_NAME.get(d, d),
                 "escalated: nearest sweep dragged, now maximizing unknown-revealed-per-step (curiosity)"
                 if _info else "cheap local sweep", _sm.coverage()), once_key="frontier_%s_%d" % (_info, _sm.t // 8))
        _stepw(act)
        return True

    _probed = _persist.setdefault("probed", set())                  # what has already been tested (survives the solve)

    def _route_summary(path):
        """Summarise an action-sequence path as a human-readable DIRECTIONAL route: 'right x3 -> up x2 -> left x1'."""
        if not path:
            return "direct"
        runs = []
        for a in path:
            nm = _actdir.get(a, a)
            if runs and runs[-1][0] == nm:
                runs[-1][1] += 1
            else:
                runs.append([nm, 1])
        return " -> ".join("%s x%d" % (nm, n) for nm, n in runs)

    def _salient_objects():
        """The objects worth NAVIGATING TO (a human's eye goes straight to these): triggers, booster, the key, and the
        exit. Everything else is dead space -- never wander it."""
        objs = []
        for tt, ins in cand.items():
            objs.append(("trigger-type %s" % (tt,), ins[0]))
        for _a in cmap.values():                               # EVERY booster of EVERY booster class -- `next()` here
            if _a.get("effect") != "budget":                   # meant the agent could only ever see one of them
                continue
            for _bi in (_a.get("insts") or ([_a["inst"]] if _a.get("inst") else [])):
                objs.append(("booster", _bi))
        _kl = _keylock()
        if _kl:
            objs.append(("exit", _exit_cell(_kl[1])))
        return objs

    def _goto_salient():
        """GOAL-DIRECTED: pathfind to the NEAREST unvisited salient object (BFS follows the corridors, so no perpendicular
        wall-waste). Only when every salient object is visited and the objective is unmet do we frontier-explore UNCHARTED
        space -- never re-walk charted dead ends."""
        ap = _apos()
        if ap is None:
            return False
        best = None; bestc = 1e9; _bkey = None
        for nm, pos in _salient_objects():
            if any(nm.split()[0] == pk[0] and abs(pos[0]-pk[1])+abs(pos[1]-pk[2]) <= quantum for pk in _probed):
                continue                                       # jitter-tolerant dedup by DISTANCE (no position bucketing)
            key = (nm.split()[0], int(pos[0]), int(pos[1]))
            pc = _path_cost(pos)                               # reachable? and how far (BFS along corridors)
            if pc is not None and pc < bestc:
                bestc = pc; best = (nm, pos); _bkey = key
        if best is not None:
            # AFFORDABILITY INVARIANT (THE BILL, §1.3a): a walk must leave the whole objective payable. Do not
            # commit to a route that spends so much of the meter that nothing is left to ACT on arrival -- that
            # is how the agent bleeds its budget wandering to a far object and dies before it can use it. Priced
            # in the agent's own measured meter; it still chooses freely among AFFORDABLE targets. Declining a
            # bankrupting walk, it explores locally instead (cheap) rather than throwing the meter away.
            _rem = _budget_actions()
            _reserve = 3                                        # a floor: leave at least this to act where I arrive
            if _rem is not None and bestc is not None and (bestc + _reserve) > _rem:
                _emit(adapter, "AFFORD  nearest salient %s costs %d to reach but I hold ~%.0f budget-actions "
                      "(+%d to act on arrival) -> I cannot afford the walk AND still do anything there. NOT "
                      "committing to a route that bankrupts the objective; exploring locally instead"
                      % (best[0], int(bestc), _rem, _reserve), once_key="afford_reject_%d" % int(bestc))
                best = None
        if best is not None:
            _path = _avatar_pathfind(_g(), ap, best[1], steer, quantum, walls, blocked=_sm_blocked(), floor=_floor_now(),
                                     edges=_sm_edges())
            _route = _route_summary(_path) if _path else "direct"
            _emit(adapter, "TARGET  nearest UNVISITED salient object := %s@%s (%d-step path) -> route: %s  [go straight "
                  "there, don't wander dead space]" % (best[0], best[1], bestc, _route))
            _goto(best[1], reason="reach salient %s" % best[0])
            _probed.add(_bkey)
            return True
        # all salient objects visited -> is there UNCHARTED space left worth exploring? (else stop wasting the budget)
        if _sm.coverage() and _sm.frontier_step(_cell(ap)) is not None:
            _emit(adapter, "TARGET  all known salient objects visited but objective unmet -> explore remaining UNCHARTED "
                  "space (may hold an unfound trigger)", once_key="explore_uncharted")
            return _explore_step()
        _emit(adapter, "TARGET  no unvisited salient object and no uncharted space -> the reachable map is exhausted "
              "[a dead-end situation: the missing piece is not spatial -- it is the objective/model]", once_key="map_exhausted")
        # STOCHASTIC ESCAPE (GAP 3): structured search is exhausted -- before conceding, inject a bounded RANDOM probe to
        # jump out of the stuck attractor (simulated-annealing / random-restart analogue), budget-guarded, narrated.
        try:
            import regime_factory as _RF3
            _all_objs = [p for ins in cand.values() for p in ins] + _novel_objects()
            _pick = _RF3.SHARED.stochastic_escape.perturb(_all_objs, int(_budget_actions()), tried=list(_probed), k=1)
            _emit(adapter, _RF3.SHARED.stochastic_escape.narrate(_pick), once_key="escape_%d" % _sm.t)
            if _pick:
                _goto(_pick[0], reason="stochastic escape probe (break the attractor)")
                _probed.add(("stoch", int(_pick[0][0]), int(_pick[0][1])))
                return True
        except Exception:
            pass
        return False

    def _novel_objects():
        """Objects on the board NOT yet interacted with -- not the avatar (+its parts), walls, floor, HUD, key/lock, or a
        known trigger colour. These are the novelty-flagged classes; when a needed property has no known cycler, THESE
        are the prime suspects for it."""
        from scipy.ndimage import label as _lbl
        g = _g(); known = set(walls) | set(av_cols) | {avatar, floor, HUDC}
        kl = _keylock()
        if kl:
            for (r, c) in kl:
                if 0 <= r < H and 0 <= c < W:
                    known.add(int(g[r, c]))
        for tt in cmap:                                        # known trigger colours (type key = (colour, shape))
            if isinstance(tt, tuple) and tt and isinstance(tt[0], (int, np.integer)):
                known.add(int(tt[0]))
        objs = []
        for c in np.unique(g):
            if int(c) in known:
                continue
            lab, n = _lbl(g == c, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if 3 <= len(ys) <= 40:
                    objs.append((int(round(ys.mean())), int(round(xs.mean()))))
        return objs

    def _probe_for_property(props):
        """OVERRIDE the transfer's 'skip re-probing': the objective needs a property (e.g. orientation) that NO cached
        trigger provides, so a trigger's transferred label (e.g. budget) is a PRIOR, not proof -- on THIS level it may
        cycle the needed property. Actively probe every trigger (recognized ones included), watching the key/lock
        displays for a change in that property, and cache whichever one produces it. This is the general fix for
        'recognised its look, assumed its effect, skipped the probe that would have found the real cycler'."""
        if _budget_actions() < 6:                              # BUDGET GUARD (gap 2): don't burn a tight budget probing
            _emit(adapter, "RE-PROBE  deferred: only %d budget-action(s) left -> protect the current objective; re-probe "
                  "once the budget allows (after a booster)" % _budget_actions(), once_key="reprobe_defer")
            return False
        _emit(adapter, "RE-PROBE  CONTRADICTION: objective needs %s but NO cached trigger provides it, yet I recognised "
              "the triggers by look and skipped probing -> that skip is the bug. Re-probing NOVEL objects FIRST (prime "
              "suspect), then every trigger, for %s (transfer is a prior, not proof)." % (props, props),
              once_key="reprobe_%s" % "_".join(sorted(props)))
        targets = [("NOVEL object", p) for p in _novel_objects()]              # gap 1: novelty first, then triggers
        targets += [("trigger-type %s" % (tt,), ins[0]) for tt, ins in cand.items()
                    if not (tt in cmap and cmap[tt].get("effect") in props)]
        for label, pos in targets:
            if _spent[0] >= budget or _budget_actions() < 3:   # budget guard mid-probe: never spend the last few actions
                break
            pre = _all_glyphs()
            if not _goto(pos, reason="RE-PROBE %s for missing %s" % (label, props)):
                continue
            post = _all_glyphs()
            for p in set(pre) & set(post):
                a, b = pre[p], post[p]
                if not (a and b):
                    continue
                eff = None
                if "orientation" in props and a["canon_shape"] == b["canon_shape"] and a["orient"] != b["orient"]:
                    eff = "orientation"
                elif "colour" in props and a["colours"] != b["colours"]:
                    eff = "colour"
                elif "shape" in props and a["canon_shape"] != b["canon_shape"]:
                    eff = "shape"
                if eff:
                    val = b["orient"] if eff == "orientation" else (b["colours"] if eff == "colour" else b["canon_shape"])
                    _ckey = ("novel", int(round(pos[0])), int(round(pos[1]))) if label.startswith("NOVEL") else label.split()[-1]
                    cmap[_ckey] = {"effect": eff, "display": p, "cycle": [val], "period": 2, "inst": pos}
                    _emit(adapter, "RE-PROBE  %s @%s ACTUALLY cycles %s (the missing property!) -> cached as the %s cycler; "
                          "objective now reachable  [novelty investigation paid off]" % (label, pos, eff, eff))
                    return True
            _smart_step()
        _emit(adapter, "RE-PROBE  probed novel objects + every trigger for %s -> none cycles it on this board's reachable "
              "objects (the %s cycler may be gated behind another change first)" % (props, props),
              once_key="reprobe_none_%s" % "_".join(sorted(props)))
        return False

    def _smart_step(off_from=None, local_only=False):
        """A LOCAL step-off that avoids known walls: pick a direction whose entered cell is NOT a known wall colour, one
        quantum ahead. This is deliberately LOCAL (one cell off) -- cycle-and-match depends on it stepping just off the
        trigger so the next contact re-triggers the cycle. (Systematic frontier coverage lives in _explore_step; using
        the far frontier here breaks the step-on/step-off cycling rhythm.)
        local_only=True FORCES the one-cell step-off and skips the market explorer -- during the operate phase of the
        cycle conjugate the step-off must keep the avatar ADJACENT to the cycler, or the market flings it to a far
        frontier and the re-land costs a full route (the docstring's own warning, previously contradicted below)."""
        # MARKET-PRICED step-off. The fallback below picks at RANDOM among directions whose next cell is not a known
        # wall COLOUR: one carving (colour==wall), one guess, no competitor, nothing settled afterwards. Here the
        # carvings bid, the measured dead-ends VETO, and the frame prices every bid at zero extra action cost.
        if not local_only and _market_explore():
            return
        ap = _apos()
        if ap is None:
            _stepw(_rnd.choice(list(steer.keys()))); return
        g = _g(); r0, c0 = int(round(ap[0])), int(round(ap[1]))
        for a in _rnd.sample(list(steer.keys()), len(steer)):
            dy, dx = steer[a]
            r = r0 + (quantum if dy > 0 else -quantum if dy < 0 else 0)
            c = c0 + (quantum if dx > 0 else -quantum if dx < 0 else 0)
            if 0 <= r < H and 0 <= c < W and int(g[r, c]) not in walls:   # the cell ahead is not a known wall colour
                _stepw(a); return
        _stepw(_rnd.choice(list(steer.keys())))                # boxed in by known walls -> anything

    def _exit_cell(lock):
        """the EXIT is the DOOR = the LOCK itself. With the key matched, the avatar walks INTO the lock to win.
        (Measured at the level-0 win: the avatar reached the lock's cell/column, entering the lock box from its opening
        -- NOT the floor below it.) Target the lock; the pathfinder routes to the box opening / into it."""
        return (int(lock[0]), int(lock[1]))

    def _budget_exit(lock):
        """Retarget the exit through SHARED.budget_path: the lock cell is often BLOCKED (inside a walled box), so route to
        its REACHABLE frontier (the door opening) using the learned cost model, account for the budget and any BUDGET+
        boosters, and NARRATE the horizon. Returns a PIXEL target for _goto. Falls back to the lock cell if unplanned."""
        try:
            import regime_factory as _RF
            ap = _apos()
            if ap is None:
                return _exit_cell(lock)
            _boosters = {}
            for _t, _atom in cmap.items():
                if _atom.get("effect") == "budget" and (_atom.get("insts") or _atom.get("inst")):
                    # The probe MEASURES the booster's worth and stores it as "gain"; this read asked for "boost",
                    # which is never written on an atom, so every booster was silently valued at the default 3 instead
                    # of its measured value (+32 on the board that prompted this). A detour costing ~10 to gain "3" is
                    # always a loss, so the planner correctly refused a trip that was actually worth taking.
                    _gain = int(_atom.get("gain", _atom.get("boost", 3)))
                    for _bi in (_atom.get("insts") or [_atom.get("inst")]):
                        if _bi is not None:                    # the gain is a property of the CLASS -- every member
                            _boosters[_cell(_bi)] = _gain      # is worth it, and all of them are on the board
            _plan = _RF.SHARED.budget_path.plan(_sm, _cell(ap), _cell(lock), int(_budget_actions()), _boosters)
            _emit(adapter, "HORIZON  %s" % _plan["narration"], once_key="horizon_exit_%d"
                  % (getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0))
            # SOMATIC PRUNE (Section 15 #4): cheap visceral score of the exit branch = payoff(win=1) - metabolic effort
            # (the plan's net cost) + prior affect (the game's decayed drive-prior). ORDERING only -- it flags a
            # high-effort/low-affect branch, it never rejects the exit as false.
            try:
                _pv = _RF.SHARED.learning_progress.prior(_session_key(adapter)).get("prior", 0.0)
                _emit(adapter, _RF.SHARED.somatic_prune.narrate("exit", _pv, float(_plan.get("net_cost", 0)), 1.0,
                      max(1, int(_budget_actions()))), once_key="somatic_exit_%d"
                      % (getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0))
            except Exception:
                pass
            _tgt = _plan.get("target")
            if _tgt is not None:
                return (_tgt[0] * quantum, _tgt[1] * quantum)  # lattice cell -> pixel target (the reachable door frontier)
        except Exception:
            pass
        return _exit_cell(lock)

    def _apos():
        """Where I am -- ON MY IDENTITY COLOUR. Deliberately NOT the whole-body centroid. Measured, twice.

        The body is a 5x5 composite (two rows of colour 12 over three of colour 9) and this returns the centroid of
        colour 12 only, ~1.5 rows above the body's true centre. That LOOKS like the composite-avatar bug. It is not,
        and the measurements say so:

          1. THE OFFSET DOES NOT MOVE THE CELL. Navigation quantises by 5; on the full frame the colour-12 centroid
             and the whole-body centroid land in the SAME logical cell (6,7). A 1.5px offset inside a 5px quantum.
          2. THE COLOUR UNDER THE CENTROID DOES CHANGE: 12 -> 9. And `_apos()` is not only a position, it is an
             IDENTITY CLAIM -- call sites read `g[_apos()]` and expect `avatar`. The whole-body centroid sits on
             colour 9, which IS me but is not what `avatar` names, so every colour-keyed self-check starts answering
             "not me".
          3. The consequence is not a crash and not a slowdown. Live, whole-body: the composer CONCLUDES after 49
             actions and max_level falls 1 -> 0. Instrumented inside the composer thread, the whole-body path costs
             3.5% of wall time -- 3.76 ms/step against a 3400 ms/action regression that never existed. `actions=49`
             was the composer stopping, not the composer being slow, and `epochs=0` said so plainly.

        So the contract of this function is "a position that is ON me, keyed by the colour I identify myself by".
        Under that contract the colour-12 centroid is CORRECT and the whole-body centroid is a violation.

        The real defect is upstream and is recorded in UNREACHED.md: `avatar` names ONE colour of a two-colour body.
        Fixing that means changing the IDENTITY (so that `avatar` is a signature, {9,12}, everywhere at once), not
        moving this centroid underneath 28 call sites that still believe the old identity.
        """
        g = _g(); m = (g == avatar)
        return (float(np.where(m)[0].mean()), float(np.where(m)[1].mean())) if m.sum() else None

    g0 = _g(); H, W = g0.shape; hist = [g0.copy()]

    # ---- STEP 2: TERRAIN + BUDGET ----
    from collections import Counter as _C
    ays, axs = np.where(g0 == avatar); adj = _C()
    for r, c in zip(ays, axs):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= r + dr < H and 0 <= c + dc < W and g0[r + dr, c + dc] != avatar:
                adj[int(g0[r + dr, c + dc])] += 1
    floor = adj.most_common(1)[0][0] if adj else -1
    counts = _C(g0.ravel().tolist())
    walls = set(c for c, n in counts.items() if n > 150 and c != floor and c != avatar)
    # TRANSFER colour->passability from prior won levels: the agent should KNOW colour X = floor, colour Y = wall from
    # the first frame, not re-learn it by bumping. Persist + reload the mapping across levels.
    _pass = KN.setdefault("passability", {"wall": set(), "floor": None})
    walls |= set(_pass["wall"]); _pass["wall"] |= walls
    if _pass["floor"] is None:
        _pass["floor"] = floor
    floor = _pass["floor"]
    try:                                              # hand the carve what the agent has been SAYING every run
        _GLOBAL_KNOWLEDGE.setdefault("patterns", {})["terrain_colours"] = (
            set(int(w) for w in walls) | ({int(floor)} if floor is not None else set()))
    except Exception:
        pass
    _emit(adapter, "PERCEIVE  terrain := floor(colour %s), walls(colours %s)  [%s]"
          % (floor, sorted(walls), "TRANSFERRED from prior levels -- known on sight, not by bumping" if _pass["wall"] else "the navigation graph"))
    # SEE the maze at FULL RESOLUTION: the pathfinder reads the exact wall/floor colours from the frame (no downsampling,
    # ever) and plans routes over the real 64x64 grid. Walls are known on sight (transferred colours), not by bumping.
    _emit(adapter, "SEE  maze read at FULL resolution from the frame's wall/floor colours (NO downsampling) -> the "
          "pathfinder plans over the exact grid; walls known on sight, not by touch", once_key="see_board")
    HUDC = 11
    _b0 = _hud_units(g0)
    if _b0 > 0:
        _emit(adapter, "PERCEIVE  budget := %d HUD units  [a depleting resource; I will learn units/action to convert this "
              "to ACTIONS remaining, and a BOOSTER is a trigger whose effect is BUDGET+]" % _b0)

    def _budget():
        return _hud_units()

    def _lives_now():
        """Lives in hand, off the ONE budget model. Needed beside _budget() because the two move TOGETHER on the
        one event that counterfeits a booster: running the bar to zero refills it to full -- for the price of a life."""
        try:
            import budget_model as _BMl
            return _BMl.get(adapter).lives_left()
        except Exception:
            return None

    def _level_now():
        """The level counter. The THIRD thing that refills the bar, after boosters and deaths: a new level starts
        full. Nothing about the object being probed causes that, and the probe cannot see the difference."""
        try:
            return int(getattr(adapter._obs, "levels_completed", 0) or 0)
        except Exception:
            return None

    # ---- perception helpers ----
    def _displays():
        d = [x["pos"] for x in _perceive_property_displays(hist) if x["is_glyph"]]
        return [p for p in d if not (p[0] >= 19 and p[1] >= 8)]     # drop bottom-right HUD

    def _all_glyphs():
        """EVERY compact FIXED glyph (candidate key/lock displays) in the current frame, pos-bucket -> property vector.
        Excludes the avatar by POSITION (objects overlapping the moving self's footprint) rather than by colour -- because
        the avatar's nose shares a colour with parts of the key/lock glyphs, so a colour exclusion would delete the real
        displays. The experiment watches ALL of these (not only known mutators) or it never sees the first mutation."""
        from scipy.ndimage import label as _lbl
        g = _g(); bg = set(np.argsort(np.bincount(g.ravel()))[-2:].tolist()); ap = _apos(); out = {}
        for c in np.unique(g):
            if int(c) in bg or int(c) == avatar:               # background + the avatar BODY colour only
                continue
            lab, n = _lbl(g == c, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if not (2 <= len(ys) <= 40):
                    continue
                cy, cx = float(ys.mean()), float(xs.mean())
                if ap is not None and abs(cy - ap[0]) + abs(cx - ap[1]) <= quantum * 1.5:
                    continue                                   # object sits ON the avatar (its nose) -> the self, not a display
                p = _object_props(g, ys, xs); pos = (int(round(cy)), int(round(cx)))   # FULL-RES centroid, no downsample
                if not (pos[0] >= 57 and pos[1] >= 24):        # drop bottom-right HUD (full-res coords)
                    out[pos] = p
        return out

    def _read_at(pos):
        from scipy.ndimage import label as _lbl
        import os as _os
        g = _g(); bg = set(np.argsort(np.bincount(g.ravel()))[-2:].tolist()); ap = _apos()
        _readfix = _os.environ.get("OURO_READ_FIX", "1") == "1"
        best = None; bestd = 5.0                               # match the glyph whose FULL-RES centroid is nearest pos
        for c in np.unique(g):
            if int(c) in bg or int(c) == avatar:
                continue
            lab, n = _lbl(g == c, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if not (2 <= len(ys) <= 40):
                    continue
                cy, cx = float(ys.mean()), float(xs.mean())
                # A KNOWN glyph is identified by its FIXED position, not by distance to the avatar. The old avatar-
                # proximity exclusion dropped the key exactly when the avatar was adjacent to it (one step-off = quantum
                # = 5px < quantum*1.5 = 7.5px) -> the cycle-and-match loop read _k1 = None and never saw the toggle, so
                # a cycler that DID cycle read as "no change". Reading nearest-to-POS already picks the fixed key over
                # the moving avatar's nose, so the proximity filter is redundant here and only hides the key.
                if (not _readfix) and ap is not None and abs(cy - ap[0]) + abs(cx - ap[1]) <= quantum * 1.5:
                    continue
                d = abs(cy - pos[0]) + abs(cx - pos[1])
                if d < bestd:
                    bestd = d; best = _object_props(g, ys, xs)
        return best

    _kl_votes = []

    def _keylock():
        if _kl[0] is not None:
            return _kl[0]
        from scipy.ndimage import label as _lbl
        g = _g(); ap = _apos(); bg = set(np.argsort(np.bincount(g.ravel()))[-2:].tolist())
        by_col = {}                                            # compact DISPLAY glyphs, grouped by colour
        for c in np.unique(g):
            if int(c) in bg or int(c) == avatar or int(c) == HUDC:   # exclude bg, avatar body, and the HUD colour
                continue
            lab, n = _lbl(g == c, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if not (4 <= len(ys) <= 40):
                    continue
                cy, cx = float(ys.mean()), float(xs.mean())
                if ap is not None and abs(cy - ap[0]) + abs(cx - ap[1]) <= quantum * 1.5:
                    continue                                   # the moving avatar (its nose), not a display
                # THE HUD IS WHERE THE READABLE HALF OF THE PAIR LIVES.
                #
                # I put a chrome-extent test here and it deleted the key. The reasoning was that the status panel is
                # not part of the game -- true of WALKING, false of READING, and this function does not walk. It is
                # the one place in the tree whose whole job is to find the two glyphs the objective compares, and one
                # of them is DRAWN IN THE STATUS BAR, at (56.7, 6.3), 20px, colour 9. A display is exactly the thing
                # you cannot step on: that is what makes it a display and not a trigger. Excluding chrome from a
                # display detector deletes the display.
                #
                # The exclusion belongs in `_candidates()` -- things I STEP ON -- where it already is, correctly, and
                # where it earned its keep by killing the 39 route attempts at row 57. Same board, two questions:
                #
                #     _candidates()  "what can I stand on?"  -> the HUD is not a place. EXCLUDE.
                #     _keylock()     "what am I comparing?"  -> the HUD is the readout. KEEP.
                #
                # So the only bound here is the one that keeps me from trying to WALK to what I read, and that bound
                # is not this function's to enforce. It reads. Navigation is downstream and already refuses.
                #
                # (The `57` literal I removed as a stray was load-bearing by accident: the panel's centroid is 56.7,
                # so `>= 57` let the key through and `>= _HUD_ROW == 56` did not. It was right for the wrong reason,
                # and I replaced it with something wrong for the right reason. Both are worth less than a boundary
                # that says what it means -- so: name the concept, not the row.)
                by_col.setdefault(int(c), []).append((cy, cx, len(ys)))
        # Which glyph is the readout, and which is the target, is settled PER INSTANCE by what my own play has done
        # to each -- never by colour. On this board they are the same colour; a colour test cannot separate them and
        # excluding "not the readout's colour" excludes the target itself.
        _loci = []
        try:
            _otk = getattr(adapter, "_obj_inducer", None)
            if _otk is not None:
                _loci = _otk.loci()
        except Exception:
            _loci = []


        # WHICH IDENTITY is the readout comes from the ranked hypotheses -- "changes only under SOME of what I touch"
        # -- which separates a thing my choice moves from a clock that moves regardless. Raw "ever changed" does not:
        # the lives counter changes every death and wins on that test, which is how this paired the life counter as
        # the key and the readout as the target. WHICH INSTANCE is the key then comes from per-instance history,
        # because both instances share the identity and only one of them answers to me.
        _sig = None
        try:
            import footprint as _FPq
            _q = [c for c in _FPq.readout_hypotheses(_otk) if c[0] not in
                  _game_mem(adapter).setdefault("_readout_dead", set())] if _otk is not None else []
            if _q:
                _sig = _q[0][0]
                _emit(adapter, "HYPOTHESIS  readout identity := %s  [%s; support %d; rank 1 of %d live]"
                      % (sorted(_sig), _q[0][2], _q[0][1], len(_q)), once_key="rid_%s" % sorted(_sig))
        except Exception:
            _sig = None
        if not _sig:
            _emit(adapter, "READOUT  nothing I have done has been confirmed to change any glyph yet -- probe",
                  once_key="readout_none")
            return None
        # ONE SYSTEM. The candidates come from the SAME tracker that holds the change evidence. `by_col` is a
        # separate segmentation, so matching its glyphs to the tracker's loci by centroid proximity was asking two
        # object systems to agree about where things are -- and they do not: at action 110 the tracker had 4 changed
        # objects and NOT ONE colour-9 glyph landed near any of them.
        # The READOUT is the ranked identity: what the evidence says my play moves.
        # The TARGET is anything my play has never changed -- NOT required to share the readout's colour. That they
        # match on this board is an ls20 accident, and requiring it excludes the real target anywhere they differ.
        # RULED 17 July. The READOUT is the ranked identity my play changes AT A DISTANCE -- my body never approached
        # it below a large floor (measured: min-distance 28-42 to the HUD panel vs 2 to on-board glyphs, a 10x gap,
        # no threshold picked). The TARGET is a changed-identity glyph my body HAS reached. This is Signal C -- a
        # positive, causal floor on approach ("closest I ever got was D across the whole run"), not Signal A's
        # absence ("never went there"), which rested on a complete map that never exists mid-episode.
        _NEAR = 8.0                                            # "reached it": adjacent-ish. The gap is 2 vs 28, so
        #                                                        anything in this band is on-board, not HUD.
        # A LOCK IS NOT MY OWN BODY -- AND NEITHER IS MY WAKE. The target is "reachable and unchanged"; my body is
        # maximally reachable (I AM it, nr~0) and its INTRINSIC properties never change though it moves. Worse, the
        # object tracker leaves a TRAIL: every cell my body has occupied persists as its own track carrying my body's
        # composite identity (measured live on ls20 lvl 0: ~25 ghost tracks, id=[9,12], size 25, nr 0.0, flooding the
        # candidate set). Positional `_is_self` only catches the ONE cell I stand on now, so the wake survives and,
        # being large, wins `max(_targs, key=size)` over the real lock -- the fixed 3x3 L-corner (id=[9], size 5,
        # nr 5.8) that is RIGHT THERE and reachable. So the gate read a permanent shape mismatch (my solid body-block
        # vs the L it should compare) that no cycle can close, and the agent cycled the HUD key forever past the
        # orientation match it kept reaching.
        #
        # "That is me" is an IDENTITY, not a place. My body has a derived self-signature (the colour set whose
        # confirmed law is TRANSLATE under my directional actions -- footprint.self_signature, the same test _self_sig
        # uses); anything wearing it is me or my wake, wherever the tracker drew it. Exclude by that identity, and fall
        # back to positional self only when the signature has not yet been learned. This is the same "not the self"
        # exclusion `_candidates()` applies to what I step on -- a reader that can name its own body must not offer that
        # body, or the ghosts it sheds, as the thing to compare against.
        _selfsig = None
        try:
            import footprint as _FPk
            _otk2 = getattr(adapter, "_obj_inducer", None)
            if _otk2 is not None:
                _ss, _ssup = _FPk.self_signature(_otk2)
                if _ss and _ssup >= 3:
                    _selfsig = frozenset(_ss)
        except Exception:
            _selfsig = None

        # THE WHOLE BODY, NOT HALF OF IT. self_signature returns only the single most-supported translate TYPE's
        # colours ([9,12] here); the avatar's TRIM ([0,1]) is a separate co-moving track it drops, so trim-coloured
        # wake ghosts leak past an identity==selfsig test. Read the FULL body from the connected footprint (flood-fill
        # crosses colour boundaries, so it grabs the trim), and take its size. A WAKE GHOST is then unmistakable: a
        # track wearing ONLY body colours AND of body SIZE -- that is a stamp of the body at a cell it stood on, not a
        # display. Measured on ls20 L1: the tracker labels the HUD key's 9<->0 toggle as identity [0], colour 0 is a
        # trim colour, so the readout became [0] and the pairing grabbed a colour-0 body-sized wake at (17,36) --
        # while the real box (id=[9], size 5) sat reachable and ignored. Real displays keep their small size (5, 20);
        # the wake wears size 25. So strip body-colour+body-size; the displays survive.
        _self_cols = set(); _body_size = 0
        try:
            _foot = _self_footprint()
            if _foot:
                _gg = _g()
                _self_cols = set(int(_gg[r, c]) for (r, c) in _foot if 0 <= r < H and 0 <= c < W)
                _body_size = len(_foot)
        except Exception:
            _self_cols = set(); _body_size = 0
        if _selfsig:
            _self_cols |= set(int(c) for c in _selfsig)

        def _is_wake(idt, sz, nr):
            # A WAKE STAMP is body-COLOURED and body-SIZED and STOOD-ON. All three matter: colour 9 is BOTH a body
            # colour (the avatar's lower half) AND the key/lock colour, and the HUD key is nearly body-sized (20 vs
            # 25) -- so colour+size alone strips the real readout (measured: it emptied the pair on L0 and the level
            # stopped clearing). The third clause saves it: a DISPLAY is the thing you cannot step on, so a real key
            # or lock is never at nr~0 (HUD key nr 36, board lock nr 5.8); only the body and its shed stamps sit where
            # I have actually stood (nr~0). Require all three and the strip catches wakes without touching displays.
            return (_self_cols and set(int(c) for c in idt) <= _self_cols
                    and _body_size and abs(int(sz) - _body_size) <= 3
                    and nr <= 2.0)

        def _not_self(cy, cx, idt, sz=0, nr=1e9):
            if _selfsig is not None and frozenset(idt) == _selfsig and nr <= 2.0:
                return False                                   # my body's identity AND stood-on -> me or my wake
            if _is_wake(idt, sz, nr):
                return False                                   # body-coloured + body-sized + stood-on -> a wake stamp
            return not _is_self((int(round(cy)), int(round(cx))))

        _reads = [(cy, cx, sz, tuple(sorted(idt))) for cy, cx, idt, ch, sz, nr in _loci
                  if ch and idt == _sig and nr > _NEAR and _not_self(cy, cx, idt, sz, nr)]
        _targs = [(cy, cx, sz, tuple(sorted(idt))) for cy, cx, idt, ch, sz, nr in _loci
                  if nr <= _NEAR and _not_self(cy, cx, idt, sz, nr)]
        # If nothing unreachable-yet-changed is found, the readout may simply not have been driven at distance yet;
        # fall back to the ranked identity regardless of approach so the agent still forms a working pair to test.
        if not _reads:
            _reads = [(cy, cx, sz, tuple(sorted(idt))) for cy, cx, idt, ch, sz, nr in _loci
                      if ch and idt == _sig and _not_self(cy, cx, idt, sz, nr)]
        import os as _osdbg
        if _osdbg.environ.get("OURO_KL_DEBUG") == "1":
            try:
                with open("/tmp/nb/kl_loci.log", "a") as _fh:
                    _fh.write("LOCI sig=%s selfsig=%s | " % (sorted(_sig), sorted(_selfsig) if _selfsig else None))
                    _fh.write(" ".join("(%.0f,%.0f id=%s ch=%d sz=%d nr=%.1f)" %
                              (cy, cx, sorted(idt), ch, sz, nr) for cy, cx, idt, ch, sz, nr in _loci))
                    _fh.write("\n  reads=%s targs=%s\n" % (_reads, _targs))
            except Exception:
                pass
        best = None
        if _reads and _targs:
            key = max(_reads, key=lambda t: t[2])
            # A KEY AND ITS LOCK ARE THE SAME KIND OF GLYPH. The readout (key) is what my play mutates; its lock is the
            # counterpart it is driven to match -- and in a locksmith the two are instances of ONE displayed type, so
            # they wear the same colour-signature. This is not "the lock is the same colour" hard-coded (games where
            # the CYCLED attribute is colour would break under that -- see the note above); it is a PREFERENCE: when a
            # reachable target shares the readout's identity, pair with it; only if none does fall back to the general
            # largest-reachable. On ls20 lvl 0 the reachable set still carries the avatar's OTHER-colour sub-parts
            # (id=[0,1], the body's trim, which the [9,12] self-signature does not name and the flood-footprint misses
            # across a gap); those outsize the true lock (the fixed L-corner, id=[9], the readout's own identity), so a
            # blind `max(size)` grabs a body-part again. Preferring the readout's identity picks the real lock -- the
            # one thing on the board that is the same TYPE as the key -- and lets the gate read the true sub-goal
            # (orientation), which the cycle can actually close.
            # STRONGEST SIGNAL: the lock is the same SHAPE-FAMILY as the key. A key and its lock are two instances of
            # one displayed glyph, so their ROTATION-CANONICAL shape is identical even when the cycled orientation (or
            # a toggled colour) differs -- canon_shape is rotation-invariant, so "cycle the orientation to match" keeps
            # the family the same. Read each candidate's canon via _read_at and prefer the one that matches the key's;
            # this picks the real box (an L-corner, the key's family) over a same-size decoy (the hollow-square === on
            # L1) or a colour-coincidence. It is the locksmith ontology, not the answer: falls back to same-identity,
            # then largest-reachable, so a genuine shape-cycling game is not broken.
            # _read_at re-segments the whole frame, so bound it: score at most the 12 most-promising candidates
            # (readout-colour first, then largest) and memoize by rounded cell -- the real lock is always among them,
            # and this keeps the per-pairing cost flat instead of one full segmentation per target.
            _kcanon = (_read_at((int(round(key[0])), int(round(key[1])))) or {}).get("canon_shape")
            _sig_targs = [t for t in _targs if set(t[3]) & set(_sig)]
            _canon_cache = {}
            def _tcanon(t):
                _p = (int(round(t[0])), int(round(t[1])))
                if _p not in _canon_cache:
                    _canon_cache[_p] = (_read_at(_p) or {}).get("canon_shape")
                return _canon_cache[_p]
            _cands = sorted(set(_sig_targs) | set(sorted(_targs, key=lambda t: -t[2])[:12]),
                            key=lambda t: -t[2])
            _shape_targs = [t for t in _cands if _kcanon is not None and _tcanon(t) == _kcanon]
            lock = max(_shape_targs or _sig_targs or _targs, key=lambda t: t[2])
            col = key[3]; best = True
            _emit(adapter, "HYPOTHESIS  readout := the glyph at (%d,%d) -- my play HAS changed it. target := the glyph "
                           "at (%d,%d) -- nothing I have done has ever changed it. Same colour, different roles; only "
                           "what I did to each tells them apart. Acting on it; if the gate never opens I am wrong"
                  % (key[0], key[1], lock[0], lock[1]),
                  once_key="kl_%d_%d_%d_%d" % (key[0], key[1], lock[0], lock[1]))
        if best is None:
            _emit(adapter, "READOUT  no pair: %d glyph(s) match the readout identity %s AND sit where my play has "
                           "changed something; %d glyph(s) sit where it never has. I track %d object(s), %d of which "
                           "I have ever changed. Glyphs on the board: %s"
                  % (len(_reads), sorted(_sig), len(_targs), len(_loci),
                     sum(1 for l in _loci if l[3]),
                     [(int(l[0]), int(l[1]), sorted(l[2]), l[3], round(l[5])) for l in _loci][:8]),
                  once_key="readout_none_%d_%d" % (len(_reads), len(_targs)))
            return None
        kl = ((int(round(key[0])), int(round(key[1]))), (int(round(lock[0])), int(round(lock[1]))))
        _kl_votes.append(kl)
        if _kl_votes.count(kl) >= 2:                           # cache only after a 2nd CONFIRMING read of the SAME pair --
            _kl[0] = kl                                        # never lock onto a transient/mid-transition frame
            _emit(adapter, "PERCEIVE  key/lock LOCKED: key@%s, lock@%s (%s)  [layout-independent: a vertically-separated "
                  "display pair confirmed over 2 reads, HUD/noise rejected; cached]"
                  % (kl[0], kl[1], ("same colour %d" % col) if col is not None else "size-matched cross-colour pair"),
                  once_key="kl_locked")
        return kl

    _HUD_ROW, _PLAY_TOP = 56, 2        # the play area is rows 2..55; everything below is the status bar

    def _candidates():
        from scipy.ndimage import label as _lbl
        g = _g(); out = {}; ap = _apos()
        kl = _keylock(); _disp = set(KN.get("display_colours", set()))   # key/lock/nose display colour -- never a trigger
        if kl:
            for (r, c) in kl:
                if 0 <= r < H and 0 <= c < W:
                    _disp.add(int(g[r, c]))
            KN["display_colours"] = _disp
        for c in np.unique(g):
            if int(c) in walls or int(c) in av_cols or int(c) == floor or int(c) in _disp:
                continue
            lab, n = _lbl(g == c, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = np.where(lab == i)
                if not (3 <= len(ys) <= 30):                   # steppable triggers are small boxes; exclude 1-2px noise
                    continue
                # THE HUD IS NOT A PLACE I CAN STAND.
                #
                # `g = _g()` is the FULL 64-row frame, so np.unique(g) picks up HUD colours and _lbl() labels HUD
                # glyphs, and their centroids became "steppable triggers". The agent's own stream convicted this:
                #
                #     REACH-FAIL  never REACHED trigger@(59, 3) -> UNTESTED, not rejected
                #     target (57, 6) aimed at 39x        <- the 2nd most-attempted target in the whole run
                #
                # Row 57. The play area ends at 56. It spent 39 route attempts, plus the STALLs and re-plans that
                # follow each one, walking at a cell that is not on the board -- out of a 42-action life. And the
                # failure was invisible because REACH-FAIL is CORRECT to say "untested, not rejected": it refuses to
                # convict a candidate on a route failure, so an unreachable candidate is retried forever. The policy
                # is right; it was being fed an impossible target.
                if float(ys.mean()) >= _HUD_ROW or float(ys.mean()) < _PLAY_TOP:
                    continue
                p = _object_props(g, ys, xs); pos = (int(p["centroid"][0]), int(p["centroid"][1]))
                if pos[0] >= 57 and pos[1] >= 24:              # bottom HUD (full-res coords)
                    continue
                if _is_self(pos):
                    continue                                   # it is part of MY BODY, not a trigger I am standing on
                out.setdefault((int(c), p["canon_shape"]), []).append(pos)
        return out

    def _self_footprint():
        """Every cell of MY BODY, whatever colours it wears.

        The avatar on this board is a 5x5 COMPOSITE -- two rows of one colour over three rows of another -- and the
        ontology carves by colour, so `avatar` names the top half and `_apos()` returns ITS centroid, sitting ~1.5
        rows above the object's real centre.

        The old test was `within 2px of _apos()`. The lower half's centroid is ~2.5 rows from that point. 2.5 > 2 --
        so THE AGENT'S OWN BODY MISSED THE "THAT IS ME" TEST BY HALF A ROW, was enrolled as a trigger candidate, and
        the agent spent probes walking to itself and recording that the key did not cycle. 11 INERT probes, live.

        A body is not a radius around a colour. Grow the actual connected object and exclude all of it.
        """
        # FIRST ASK THE BOARD. footprint.self_signature() reads the object whose CONFIRMED law is translate-under-a-
        # directional-action -- the thing my action choice steers, by construction -- and returns a colour SIGNATURE,
        # a frozenset, not a colour. That is the causal answer this function fakes with a colour seed, and it costs
        # nothing: the inducer is watching every transition anyway. Fall back to the seed only until the board has
        # taught a translate law.
        try:
            import footprint as _FP
            _oti = getattr(adapter, "_obj_inducer", None)
            if _oti is not None:
                _sig, _sup = _FP.self_signature(_oti)
                if _sig and _sup >= 3:
                    _f = _FP.self_footprint_live(_g(), _sig, terrain=_oti.terrain)
                    if _f:
                        _emit(adapter, "SELF  body := colours %s  [BECAUSE that object type is the one whose "
                                       "CONFIRMED law is TRANSLATE under my directional actions -- derived from %d "
                                       "transitions of my own play, not from a colour I was handed. It is a SET: "
                                       "this body wears two colours and any single-colour answer names half of me]"
                              % (sorted(_sig), _sup), once_key="self_sig_%s" % sorted(_sig))
                        return _f
        except Exception:
            pass
        try:
            g = _g()
            seed = np.where(g == avatar)
            if not len(seed[0]):
                return set()
            counts = np.bincount(g.ravel())
            bgs = set(int(x) for x in np.argsort(-counts)[:2])     # floor + walls: the board, not an object
            H, W = g.shape
            stack = [(int(seed[0][0]), int(seed[1][0]))]
            seen = set(stack)
            while stack and len(seen) <= 120:
                r, c = stack.pop()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in seen and int(g[nr, nc]) not in bgs:
                        seen.add((nr, nc))
                        stack.append((nr, nc))
            return seen
        except Exception:
            return set()

    def _is_self(pos):
        foot = _self_footprint()
        if not foot:
            ap = _apos()
            return ap is not None and max(abs(pos[0] - ap[0]), abs(pos[1] - ap[1])) <= 2
        return any(abs(pos[0] - r) <= 1 and abs(pos[1] - c) <= 1 for (r, c) in foot)

    def _period(seq):
        for p in range(1, len(seq)):
            if len(seq) >= 2 * p and all(seq[i] == seq[i % p] for i in range(len(seq))):
                return p
        return max(1, len(set(seq)))

    # ---- STEP 3+4: DISPLAYS + MODEL (confirm trigger->property->cycle->period) ----
    for d in _displays()[:3]:
        _emit(adapter, "PERCEIVE  property-display := glyph@%s  [KEY/LOCK: shape/orientation IS its state, not position]" % (d,))
    cand = _candidates()
    if cand:
        _emit(adapter, "TYPE  grouped floor objects into %d visual trigger-type(s) by (colour,shape): %s  [same look => "
              "same effect hypothesis; probe one per type, generalise to instances]"
              % (len(cand), {str(t[0]): len(v) for t, v in cand.items()}))
        # NOVELTY / CURIOSITY: which trigger-types have I interacted with before (known causal map) vs are NEW on this
        # board? A KNOWN class -> reuse its learned effect; a NEW class -> SALIENT, worth investigating what it does.
        _known_types = set(KN.setdefault("known_trigger_types", set()))
        _seen_now = set(cand.keys())
        _novel = [t for t in _seen_now if t not in _known_types and t not in cmap]
        if _known_types & _seen_now:
            _emit(adapter, "RECOGNISE  %d trigger-type(s) seen on a PRIOR level -> reuse the learned effect, skip re-probing"
                  % len(_known_types & _seen_now), once_key="recognise")
        if _novel:
            _emit(adapter, "NOVELTY  %d NEW object class(es) never interacted with -> flag SALIENT: investigate what they "
                  "affect on the board (curiosity-driven, before assuming they are inert)" % len(_novel), once_key="novelty")
        KN["known_trigger_types"] = _known_types | _seen_now
    _emit(adapter, "PLAN  %d trigger-type(s) to characterise; navigate to EXACT overlap and run the experiment "
          "[classify -> replicate -> induce cycle -> cache]" % len(cand))
    for ttype, insts in cand.items():
        if _spent[0] >= budget:
            break
        if ttype in cmap and cmap[ttype].get("effect"):        # KNOWN type -> transfer, do not re-probe (type-key)
            # THE CLASS TRANSFERS. THE ADDRESSES DO NOT.
            #
            # `insts` is the FRESH census of THIS board and it was sitting in the loop variable, unused, while the
            # atom kept whichever addresses the level that first minted it happened to have. Measured on ls20: the
            # colour-9 booster type was minted CORRECTLY on level 1, where a colour-9 box really does sit at (11,36)
            # and really does pay +32. On level 2 that cell is bare floor and the colour-9 boxes have moved to
            # (41,15) and (23,56). The agent then spent its tank walking to (11,36), got nothing, and -- being
            # honest -- concluded the BOOSTER was spent and retired it, while the live one sat untouched. A correct
            # class was destroyed by a stale address, and every downstream instrument (BUDGET-MATH, the detour, the
            # dead-booster ledger) reasoned perfectly from it.
            #
            # This is the kernel/library line, in one atom: "small colour-9 box => +32 budget" is KNOWLEDGE and
            # survives the board it was learned on. "(11,36)" is a fact about a board that no longer exists. Carrying
            # the first is generalisation; carrying the second is a lookup table pointing into freed memory.
            _prev = cmap[ttype].get("insts") or ([cmap[ttype]["inst"]] if cmap[ttype].get("inst") else [])
            cmap[ttype]["insts"] = [tuple(i) for i in insts]
            cmap[ttype]["inst"] = tuple(insts[0])
            _emit(adapter, "RECOGNISE  trigger-type %s known -> PREDICT %s (carried from a prior level); %d instance(s) "
                  "share it  [generalised by visual type, not re-probed]" % (ttype, cmap[ttype]["effect"], len(insts)))
            if _prev and set(map(tuple, _prev)) != set(map(tuple, insts)):
                _emit(adapter, "RE-BIND  trigger-type %s: the CLASS carries, the ADDRESSES do not -> re-located %s -> %s "
                               "on THIS board  [what I know is what this kind of object DOES; where it was is a fact "
                               "about a board I am no longer standing on]"
                      % (ttype, sorted(map(tuple, _prev))[:3], sorted(map(tuple, insts))[:3]))
            continue
        ty, tx = insts[0]; seq = []; effect = None; disp_pos = None
        for _visit in range(4):
            if _spent[0] >= budget:
                break
            pre = _all_glyphs(); pb = _budget(); _pl = _lives_now(); _pv = _level_now()
            _pre_reach = {t: (_path_cost(t) is not None) for t in list(_blocked_targets)}   # means-ends: snapshot reach
            if not _goto((ty, tx), reason='probe trigger-type %s' % (ttype,)):
                break
            post = _all_glyphs(); qb = _budget(); _ql = _lives_now(); _qv = _level_now()
            for _t, _was in _pre_reach.items():                # MEANS-END: did this trigger OPEN A ROUTE?
                if (not _was) and (_path_cost(_t) is not None):
                    _emit(adapter, "MEANS-END  trigger-type %s OPENED THE ROUTE to (%d,%d) [%s] -- previously UNREACHABLE, "
                          "now reachable. Prerequisite SOLVED -> the target is pursuable" % (ttype, _t[0], _t[1],
                          str(_blocked_targets.get(_t, "?"))))
                    cmap[ttype] = {"effect": "opens_route", "display": None, "cycle": [], "period": 0, "inst": insts[0]}
                    _blocked_targets.pop(_t, None)
                    _goto(_t, reason="pursue now-reachable %s" % str(_blocked_targets.get(_t, "target")))
            if qb > pb + 4:                                    # BUDGET ROSE -- but WHY?
                # THE CONFOUND: `_goto` is MULTI-STEP. Across a 10-step route the bar can hit zero, cost a life, and
                # refill to FULL on respawn -- a budget rise far bigger than any booster's, arriving while walking
                # toward an object that did nothing. `qb > pb + 4` cannot tell those apart, so it credits the
                # destination and mints a booster out of the death. That is how `booster@(11, 36)` came to sit on
                # empty floor: the agent did not find it there, it DIED on the way there and thanked the scenery.
                #
                # The control is the one reading that separates them: a life. A booster is free; the respawn refill
                # is bought with a life you cannot buy back. Lives fell -> this was the death, not the object.
                # (Same shape as the no_posthoc bound: a test that reads the outcome will always find what it wants.)
                _why = None
                if _pl is not None and _ql is not None and _ql < _pl:
                    _why = "I ALSO LOST A LIFE (%s -> %s), and the respawn refills the bar to full" % (_pl, _ql)
                elif _pv is not None and _qv is not None and _qv > _pv:
                    _why = "THE LEVEL ALSO CHANGED (%s -> %s), and a new level starts with a full bar" % (_pv, _qv)
                if _why is not None:
                    _emit(adapter, "REJECT  budget rose +%d while probing type %s -- BUT %s. The bar refills for "
                                   "THREE reasons on this board (booster, death, new level) and only one of them is "
                                   "this object. I cannot tell them apart from the rise alone, so a rise that "
                                   "coincides with either of the other two is confounded evidence and I throw it "
                                   "away rather than bank a booster I would then spend real budget walking back to"
                          % (qb - pb, ttype, _why))
                    continue                                   # probe again, uncontaminated, if budget allows
                _ba = (qb - pb) / max(1.0, _rate())
                # The atom is keyed by TYPE -- it is a claim about a CLASS of object ("things that look like this are
                # boosters worth +N"). Recording only insts[0] threw the class away and kept one address: the agent
                # learned the general fact and could then act on exactly one object, so retiring that instance left it
                # with no boosters while identical ones sat untouched on the board. Carry the whole class.
                cmap[ttype] = {"effect": "budget", "display": None, "cycle": [], "period": 0, "gain": qb - pb,
                               "inst": insts[0], "insts": [tuple(i) for i in insts]}
                _emit(adapter, "DISCOVER  STEP_ON(type %s) -> BUDGET+ (+%d units \u2248 +%.0f actions)  [a BOOSTER: a budget "
                      "resource to sequence into the plan]" % (ttype, qb - pb, _ba))
                break
            for p in set(pre) & set(post):
                a, b = pre[p], post[p]
                if a and b and (a["canon_shape"], a["orient"], a["colours"]) != (b["canon_shape"], b["orient"], b["colours"]):
                    effect = "colour" if a["colours"] != b["colours"] else ("shape" if a["canon_shape"] != b["canon_shape"] else "orientation")
                    disp_pos = p
                    seq.append(b["orient"] if effect == "orientation" else (b["colours"] if effect == "colour" else b["canon_shape"]))
                    break
            # RE-CONTACT METHOD is the agent's to decide, not Claude's to hardcode. The old loop ALWAYS stepped off
            # and walked back, which hid the alternative forever: the agent could never learn whether staying re-fires
            # the trigger because it never once stayed. Vary it -- stay on the cell on some visits, step off on others
            # -- and record what happened each way, so the agent INDUCES the re-contact rule from its own evidence
            # instead of inheriting Claude's assumption. Claude does not pick leave-vs-stay; it makes both observable.
            if _visit % 2 == 0:
                # STAY: act without leaving the cell. Take a step toward a known wall -- the action registers, the
                # avatar does not move -- so the agent can observe whether the trigger re-fires from an action alone,
                # with no step-off. If no wall is adjacent, fall through to a normal step (the agent still gets the
                # step-off datapoint; it is not forced into a stay it cannot perform).
                _stayed = False
                ap = _apos()
                if ap is not None:
                    g = _g(); r0, c0 = int(round(ap[0])), int(round(ap[1]))
                    for a in _rnd.sample(list(steer.keys()), len(steer)):
                        dy, dx = steer[a]
                        r = r0 + (quantum if dy > 0 else -quantum if dy < 0 else 0)
                        c = c0 + (quantum if dx > 0 else -quantum if dx < 0 else 0)
                        if 0 <= r < H and 0 <= c < W and int(g[r, c]) in walls:   # into a wall -> I do not move
                            _stepw(a); _stayed = True; break
                if _stayed:
                    _emit(adapter, "PROBE-METHOD  visit %d: STAYED on trigger %s and acted (into a wall, so I did not "
                          "move) -> observing whether it re-fires WITHOUT a step-off  [testing my own assumption that "
                          "re-contact needs leaving]" % (_visit, ttype), once_key="probe_stay_%s" % str(ttype))
                else:
                    _smart_step()
            else:
                _smart_step()                                 # step off (map-aware) -> observe re-fire on RETURN
                _emit(adapter, "PROBE-METHOD  visit %d: STEPPED OFF trigger %s -> observing re-fire on return  "
                      "[the other half of the experiment]" % (_visit, ttype), once_key="probe_off_%s" % str(ttype))
        if not (effect and seq):
            _emit(adapter, "PROBE  trigger-type %s -> NO display change detected across %d contact(s)  [not a key/lock "
                  "cycler -- inert or decoration; recorded so it is not re-probed as if unknown]" % (ttype, 4))
            # "I tested this and it does nothing" is a RESULT, not the absence of one. Storing effect=None made it
            # read as untested (the reuse gate checks `.get("effect")`, and None is falsy), so an inert trigger was
            # re-probed every pass -- measured: type (9,..) navigated-to-probe 4x in one life, RECOGNISE never fired.
            # Record inert as a positive verdict and mark the type characterised, so the gate skips it.
            cmap[ttype] = {"effect": "inert", "display": None, "cycle": [], "period": 0, "inst": insts[0],
                           "insts": [tuple(i) for i in insts]}
        if effect and seq:
            per = _period(seq)
            cmap[ttype] = {"effect": effect, "display": disp_pos, "cycle": seq, "period": per, "inst": insts[0]}
            _emit(adapter, "PERCEIVE  effect := %s of display@%s  [classified by property-diff]" % (effect.upper(), disp_pos))
            _emit(adapter, "CONFIRM  replicable := %d/%d contacts produced it  [a law, not an anecdote]" % (len(seq), len(seq)))
            if len(set(seq)) >= 2:
                _emit(adapter, "INDUCE  CYCLE(display@%s.%s) period=%d order=%s  [N contacts advance N mod %d; cached as "
                      "one rule]" % (disp_pos, effect, per, seq, per))
            _emit(adapter, "CACHE  causal-map[type %s] := STEP_ON->CYCLE(%s.%s, period %d)  [transfers forward]" % (ttype, disp_pos, effect, per))
    _emit(adapter, "MODEL  avatar causal map: %d confirmed atom(s)" % len([1 for v in cmap.values() if v.get("effect")]))

    # ---- STEP 5: DERIVE OBJECTIVE (learned win-condition, else worst-case all-properties) ----
    learned = KN.get("win_condition", {}).get("formula", [])
    _has_match = any("MATCH" in f for f in learned)
    props = []
    if _has_match or any("SHAPE" in f for f in learned):
        props.append("shape")
    if _has_match or any("ORIENT" in f for f in learned):
        props.append("orientation")
    if _has_match or any("COLOUR" in f for f in learned):
        props.append("colour")
    if not props:
        props = ["shape", "orientation", "colour"]
    _emit(adapter, "DERIVE  objective := MATCH(key,lock) on %s  [%s]" % (props,
          ("from the LEARNED win-condition %s (transferred from a prior win)" % learned) if learned
          else "no win yet -> WORST-CASE: assume all properties until a win prunes them"))

    def _differ():
        kl = _keylock()
        if kl is None:
            # NOT FOUND IS NOT MATCHED.
            #
            # This returned [] -- and one line below, a FOUND pair that fails to READ correctly returns ["?"]. Two
            # failures of the same kind, and only one of them was honest. Empty means "nothing differs", and the
            # consumer at `if not dif:` reads that as **GATE satisfied -> navigate to the exit**. So "I cannot see a
            # key or a lock on this board" arrived at every downstream instrument as "key == lock, the gate is open".
            #
            # Measured live on ls20 level 2: BUDGET-MATH ~9 actions left; plan ~3 (align 0 + exit 3) [margin OK] --
            # the agent walked to the exit with budget to spare, expecting a win, and nothing resolved. `align 0` was
            # never a claim that they matched. It was the absence of a reading, wearing the costume of one. And the
            # COMPARE line that would have exposed it is gated on `if _gk and _gl`, so the stream stayed silent about
            # the one decision the whole solve turns on.
            #
            # This is the no_posthoc class again, in the objective instead of the predicate: a gate that opens when
            # you cannot see it is a gate that always opens, and it predicts nothing. An unknown must cost something.
            _emit(adapter, "GATE  UNKNOWN  no key/lock pair found on this board -> the gate is NOT satisfied, it is "
                           "UNREAD. Treating not-found as matched is what sent me to the exit with margin and no win; "
                           "an objective I cannot see is an objective I have not met  [re-detect before planning]",
                  once_key="gate_unread")
            return None, None, ["?"]
        key, lock = kl; gk, gl = _read_at(key), _read_at(lock)
        if gk is None or gl is None:
            # A SINGLE-FRAME read miss during cycling -- a glyph caught mid-transition -- is not "the objective is
            # unknown". The pair is still found (kl is not None) and the glyph is still there; I just could not read
            # it THIS frame. Hold the last good reading and let the next frame resolve it, rather than collapsing the
            # sub-goal to ['?'] which the align loop cannot act on. Ground truth: cycling is modular and the readout
            # passes through unreadable intermediate states between steps -- missing one is expected, not a failure.
            _lastkl = _game_mem(adapter).get("_last_kl_read")
            if _lastkl is not None:
                _emit(adapter, "READ  key/lock momentarily unreadable mid-cycle -> holding last reading (differ on %s) "
                               "and re-reading next frame, not treating it as unknown" % _lastkl,
                      once_key="read_hold")
                return key, lock, _lastkl
            return key, lock, ["?"]
        dif = []
        if "shape" in props and gk["canon_shape"] != gl["canon_shape"]:
            dif.append("shape")
        if "orientation" in props and gk["orient"] != gl["orient"]:
            dif.append("orientation")
        if "colour" in props and gk["colours"] != gl["colours"]:
            dif.append("colour")
        _game_mem(adapter)["_last_kl_read"] = dif           # good reading this frame -> hold it through the next miss
        return key, lock, dif

    # ---- STEP 6-8+10: ENUMERATE sub-goals -> ALIGN each -> GATE -> REVISE on failure ----
    _surprise = 0; _kl_hist = []

    def _frame_doubt():
        """Mid-game-aware wrapper around SHARED.frame_doubt (the regime-agnostic DECISION). The avatar solver owns the
        per-level re-arm (it has the level loop) and the narration; the decision itself -- is the evidence enough to
        cross the avatar->non-avatar boundary and re-abduce -- lives in SHARED so no regime re-implements it."""
        import regime_factory as _RF
        _lvl = getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0
        if getattr(adapter, "_frame_doubt_lvl", None) != _lvl:                 # MID-GAME RE-ARM: judge each level afresh
            adapter._frame_doubt_lvl = _lvl
            adapter._kl_ever = False
            if getattr(adapter, "_frame_doubt", False):
                _emit(adapter, "FRAME  new level %d -> re-arming the frame hypothesis (a game can change regime between "
                      "levels; the frame committed earlier is NOT assumed here)" % _lvl, once_key="frame_rearm_%d" % _lvl)
                adapter._frame_doubt = False
        try:
            _key, _lock, _ = _differ()
            if _key is not None:
                adapter._kl_ever = True                        # a real MATCH gate was readable -> avatar frame holds
            _cur = getattr(adapter, "_committed_frame", "avatar")
            _verdict = _RF.SHARED.frame_doubt.evaluate(_g(), _cur, getattr(adapter, "_kl_ever", False), _spent[0])
            if _verdict:
                _sl = _verdict["slot"]
                _emit(adapter, "FRAME-DOUBT  current frame := %s (a self controls toward a MATCH gate). AGAINST it: no "
                      "key/lock gate was EVER readable in %d actions -- an avatar/MATCH game must have one. FOR a "
                      "NON-AVATAR frame: a stationary hollow frame(colour %d) with an interior slot @%s size %d "
                      "(CONTAIN_FIT). This crosses the avatar->non-avatar boundary -> abandon the %s frame, re-abduce "
                      "toward %s." % (_cur.upper(), _spent[0], _sl[0], _sl[1], _sl[2], _cur, _verdict["toward"].upper()),
                      once_key="frame_doubt_obj_%d" % _lvl)
                adapter._frame_doubt = True
                adapter._reabduce_toward = _verdict["toward"]
                return True
        except Exception:
            pass
        return False

    for _round in range(10):
        if _won[0] is not None or _spent[0] >= budget:
            break
        if _frame_doubt():                                     # the model is unmodellable in THIS frame -> stop refining it
            break
        key, lock, dif = _differ()
        if key is None:
            # cn04 stalls HERE. Before giving up, ask whether the reason the gate is unevaluable is that the FRAME is
            # wrong (high forward-model residual), not merely that this frame is ambiguous.
            if _frame_doubt():
                break
            _emit(adapter, "PERCEIVE  key/lock not both identifiable this frame -> cannot evaluate the gate yet", once_key="no_keylock")
            break
        # LEARNING-PROGRESS (GAP 1): track d(error)/dt on this objective -- error proxy = #differing attributes + accrued
        # surprise. The verdict decides persist / pivot / move-on with a MEASURED slope instead of magic thresholds, and
        # is narrated (rides the frame data via _emit). GAP 4 (volatility) uses the same error series to set explore/exploit.
        try:
            import regime_factory as _RF2
            _RF2.SHARED.learning_progress.bind_store(_GLOBAL_KNOWLEDGE.setdefault("drives", {}))   # persist in transferable memory
            _RF2.SHARED.hypothesis_ledger.bind_store(_GLOBAL_KNOWLEDGE.setdefault("hypotheses", {}))
            _RF2.SHARED.coherence.bind_store(_GLOBAL_KNOWLEDGE.setdefault("coherence", {}))
            _lp_lvl = getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0
            # _gid was referenced below (model-doubt key, coherence facts, cross-level consolidation) but NEVER bound in
            # this function -> a NameError swallowed by the surrounding try/except that SILENTLY KILLED the whole SOLVE-
            # phase cascade below, while observe() above still ran (so LP samples still pooled, hiding the dead cascade).
            # Bind it here (same idiom as ~line 2439): the GAME, not the session instance -- game-scoped drive-memory.
            _gid = str(getattr(adapter, "game_id", None) or getattr(adapter, "_game_id", None) or "unknown").split("-")[0]
            _lp_key = "%s:L%d:MATCH" % (_session_key(adapter), _lp_lvl)   # per-GAMEPLAY -> isolated, but not a game name
            _RF2.SHARED.learning_progress.observe(_lp_key, float(len(dif) + _surprise))
            _emit(adapter, _RF2.SHARED.learning_progress.narrate(_lp_key), once_key="progress_%d_%d" % (_lp_lvl, _round))
            # PROTECTED PE INTEGRAL (Section 14 rule 2): accumulate the reality-contradiction at FULL magnitude; no drive
            # may reduce/reattribute it; frame-doubt reads it. This is the un-gameable inner signal (the RLHF substitute).
            _RF2.SHARED.learning_progress.accumulate_pe(_lp_key, float(len(dif) + _surprise))
            _emit(adapter, _RF2.SHARED.learning_progress.narrate_pe_integral(_lp_key), once_key="peint_%d_%d" % (_lp_lvl, _round // 3))
            # WIN-ONLY PROMOTION (Section 14 rule 1): the MATCH hypothesis is PROVISIONAL; a self-measured signal only
            # GUIDES, never confirms. Only a real win promotes (handled at the win site).
            _RF2.SHARED.hypothesis_ledger.note(_lp_key)
            _emit(adapter, _RF2.SHARED.hypothesis_ledger.narrate(_lp_key, signal_name="learning-progress/residual"),
                  once_key="promo_%d" % _lp_lvl)
            # FALSIFICATION STANCE (Section 14 rule 3): seek to DISCONFIRM the frame, not confirm it; proxies rising are INERT.
            _fe = _RF2.SHARED.frame_doubt.falsification_evidence(_g(), getattr(adapter, "_committed_frame", "avatar"),
                                                                 getattr(adapter, "_kl_ever", False))
            _emit(adapter, _RF2.SHARED.frame_doubt.narrate_falsification(_fe), once_key="falsify_%d" % _lp_lvl)
            # MODEL-DOUBT (Gaps 1&4) on the AVATAR path too: if the displacement/objective residual is structured +
            # persistent, the MODEL OF THE RULES (not just the objective) is suspect -> enumerate structural hypotheses.
            # Regime-agnostic: same SHARED.model_doubt the actuator path uses, keyed by game:avatar.
            try:
                _RF2.SHARED.model_doubt.bind_store(_GLOBAL_KNOWLEDGE.setdefault("model_doubt", {}))
                _mkc = "%s:avatar" % _gid
                _hist = _RF2.SHARED.learning_progress.hist.get(_lp_key, [])
                _resid = float(_hist[-1]) if _hist else 0.0     # latest PE/alignment residual (safe, in-scope)
                _RF2.SHARED.model_doubt.observe(_mkc, _resid, signature=getattr(adapter, "_committed_frame", "avatar"))
                if _RF2.SHARED.model_doubt.is_structured(_mkc):
                    _emit(adapter, _RF2.SHARED.model_doubt.narrate(_mkc), once_key="modeldoubt_%d" % _lp_lvl)
                    _emit(adapter, _RF2.SHARED.mechanics_hypotheses.narrate(
                          _RF2.SHARED.mechanics_hypotheses.enumerate()), once_key="mechhyp_%d" % _lp_lvl)
            except Exception:
                pass
            # COLD-START PROTOCOL (Section 16): read the phase from signals we already have -- volatility (novelty),
            # grad-PE (~0 = no traction), and the count of local rules (the discovered trigger-effect atoms). In BOOTSTRAP
            # the objective is EPISTEMIC PLAY (coverage/surprise) and global coherence is GATED OFF; exit to SOLVE once
            # enough local rules accrue. MUST run BEFORE the coherence compass below (which reads _coh_gated) -- computing
            # it after was an UnboundLocalError that (inside the outer try/except) DECAPITATED the rest of this cascade.
            _RF2.SHARED.cold_start.bind_store(_GLOBAL_KNOWLEDGE.setdefault("bootstrap", {}))
            _vr = _RF2.SHARED.volatility.explore_ratio(_RF2.SHARED.learning_progress.hist.get(_lp_key, []))
            # ATTEMPT-MEMORY CONSUME (Fix A, gated OURO_ATTEMPT_MEMORY): if the SAME committed plan for THIS level
            # (target-TYPE signature, recorded at the PLAN step below) has been re-tried without clearing the level,
            # PROPORTIONALLY raise the agent's OWN explore ratio -- escalating with the repeat count, decaying naturally
            # the moment the agent commits a different plan (a new _last_sig resets tries). This does NOT choose a move
            # or encode an answer; it only turns up the agent's exploration pressure so its own reasoning breaks the loop.
            import os as _os_amc
            if _os_amc.environ.get("OURO_ATTEMPT_MEMORY", "0") == "1":
                try:
                    _amc = _GLOBAL_KNOWLEDGE.get("attempts", {}).get("%s:L%d" % (_gid, _lp_lvl), {})
                    _lsc = _amc.get("_last_sig")
                    _triesc = _amc.get(_lsc, {}).get("tries", 0) if _lsc is not None else 0
                    if _triesc >= 3:
                        _boostc = min(0.6, 0.12 * (_triesc - 2))
                        _vr = min(1.0, _vr + _boostc)
                        _emit(adapter, "EXPLORE-PRESSURE  the last committed plan at L%d has repeated %dx with no clear -> "
                              "raising explore ratio by +%.2f (now %.2f) so a DIFFERENT plan gets a turn; decays when the "
                              "agent commits something new" % (_lp_lvl, _triesc, _boostc, _vr),
                              once_key="explpress_%d_%d" % (_lp_lvl, _triesc))
                except Exception:
                    pass
            _ps = _RF2.SHARED.learning_progress.slope(_lp_key)
            _nrules = len(cmap)                                # existing discovered trigger->effect atoms = local rules
            _phase = _RF2.SHARED.cold_start.phase(_vr, _ps, _nrules)
            adapter._bootstrap_mode = (_phase == "bootstrap")  # exploration machinery reads this (epistemic-play bias)
            _emit(adapter, _RF2.SHARED.cold_start.narrate(_phase, _vr, _ps, _nrules), once_key="bootstrap_%d_%d" % (_lp_lvl, _round // 3))
            _coh_gated = _RF2.SHARED.cold_start.coherence_gated(_phase)
            # COHERENCE COMPASS (Section 15 #2), GATED by the cold-start phase (Section 16 Strategy 3): during BOOTSTRAP
            # global coherence is INERT BY DESIGN (only local consistency counts); it re-engages in SOLVE.
            if not _coh_gated:
                _hyp = {"%s:frame" % _gid: getattr(adapter, "_committed_frame", "avatar"), "%s:objective" % _gid: "MATCH"}
                _emit(adapter, _RF2.SHARED.coherence.narrate(_hyp), once_key="coherence_%d" % _lp_lvl)
            else:
                _emit(adapter, "COHERENCE  gated OFF (bootstrap / cold-start) -- global coherence is inert until local "
                      "rules accrue; only local per-action consistency counts", once_key="coherence_gated_%d" % _lp_lvl)
            # cross-level trajectory carried forward (the allostatic baseline) -- remembered across levels of this game
            if getattr(adapter, "_lp_traj_lvl", None) != _lp_lvl:
                if getattr(adapter, "_lp_traj_lvl", None) is not None:
                    # CONSOLIDATE the finished level: compress its raw error series to a somatic marker + prune the raw
                    # series + age old markers (lossy affective compression; semantic facts stay full in KN).
                    _old_key = "%s:L%d:MATCH" % (_gid, adapter._lp_traj_lvl)
                    _solved = (_lp_lvl > adapter._lp_traj_lvl)
                    if _solved:
                        # WIN-ONLY PROMOTION: a real win is the ONLY thing that confirms a hypothesis (Section 14 rule 1)
                        _RF2.SHARED.hypothesis_ledger.confirm_by_win(_old_key)
                        # and the won frame/objective become COHERENCE priors (Section 15 #2): future branches that
                        # contradict them are deprioritised (guide only; a falsifier still overrides).
                        _RF2.SHARED.coherence.assert_fact("%s:frame" % _gid, getattr(adapter, "_committed_frame", "avatar"))
                        _RF2.SHARED.coherence.assert_fact("%s:objective" % _gid, "MATCH")
                        _emit(adapter, "PROMOTION  '%s' CONFIRMED by a real win (levels_completed advanced) -- the only "
                              "promotion authority; no self-measured proxy did this" % _old_key,
                              once_key="promo_win_%d" % adapter._lp_traj_lvl)
                    _mk = _RF2.SHARED.learning_progress.consolidate(_gid, adapter._lp_traj_lvl, _old_key, solved=_solved)
                    _emit(adapter, _RF2.SHARED.learning_progress.narrate_consolidate(_gid, _mk),
                          once_key="consolidate_%d" % adapter._lp_traj_lvl)
                adapter._lp_traj_lvl = _lp_lvl
                # MORNING PRIOR: the recency-decayed markers set the STARTING stance for this new level (hopeful+informed)
                _pn = _RF2.SHARED.learning_progress.narrate_prior(_gid)
                if _pn:
                    _emit(adapter, _pn, once_key="driveprior_%d" % _lp_lvl)
                _tn = _RF2.SHARED.learning_progress.narrate_trajectory(_gid)
                if _tn:
                    _emit(adapter, _tn, once_key="drivemem_%d" % _lp_lvl)
            _lp_v = _RF2.SHARED.learning_progress.verdict(_lp_key)
            _emit(adapter, _RF2.SHARED.volatility.narrate(_RF2.SHARED.learning_progress.hist.get(_lp_key, [])),
                  once_key="volatility_%d" % _lp_lvl)
            if _lp_v["state"] == "learning":                   # GAP 2: closing on it -> persist harder
                _emit(adapter, _RF2.SHARED.persistence.narrate(_lp_v, 6), once_key="persist_%d_%d" % (_lp_lvl, _round))
            elif _lp_v["state"] == "plateaued_high" and _spent[0] >= 8:   # flat+high -> principled pivot (with frame-doubt)
                _emit(adapter, _RF2.SHARED.persistence.narrate(_lp_v, 6), once_key="persist_hi_%d" % _lp_lvl)
        except Exception:
            pass
        _gk, _gl = _read_at(key), _read_at(lock)
        if _gk and _gl:
            _emit(adapter, "COMPARE  key@%s [%s] vs lock@%s [%s] -> %s  [reading BOTH glyph states to check the gate; "
                  "this is what the match decision is based on]" % (key, _fmt(_gk), lock, _fmt(_gl),
                  ("ALL MATCH" if not dif else "differ on %s" % dif)), once_key="compare_r%d" % _round)
        # BUDGET-AWARE PLANNING: cost the remaining plan (align each differing property + reach the exit) in ACTIONS and
        # compare to what's left. If tight and a BOOSTER is known, DETOUR to it first -- sequence resources so the key
        # matches AND there are actions to spare for the exit gate.
        _ba = _budget_actions(); _exit_c = _path_cost(_exit_cell(lock)) or 0
        _align_c = 0
        for _sg in dif:
            _t = next((t for t, a in cmap.items() if a.get("effect") == _sg), None)
            if _t and cmap[_t].get("inst"):
                _pc = _path_cost((cmap[_t]["inst"][0], cmap[_t]["inst"][1])) or 0
                _align_c += (_pc + 1) * max(1, cmap[_t].get("period", 1))
        _plan_c = _align_c + _exit_c
        # EVERY booster of EVERY booster class, nearest reachable first. `next()` here meant one booster ever --
        # the same class-vs-instance bug fixed elsewhere and missed in this consumer, which is the one that decides
        # whether to actually go and get the thing.
        _all_boosts = []
        for _at in cmap.values():
            if _at.get("effect") != "budget":
                continue
            for _bi in (_at.get("insts") or ([_at.get("inst")] if _at.get("inst") else [])):
                if _bi is None or tuple(_bi) in _dead_boosters:
                    continue
                _all_boosts.append((_path_cost((_bi[0], _bi[1])) or 9999, tuple(_bi), _at))
        _all_boosts.sort()
        _boost = dict(_all_boosts[0][2], inst=_all_boosts[0][1]) if _all_boosts else None
        _boost_cost = _all_boosts[0][0] if _all_boosts else None
        _emit(adapter, "BUDGET-MATH  ~%.0f actions left; plan ~%d (align %d + exit %d)  [%s]"
              % (_ba, _plan_c, _align_c, _exit_c,
                 "enough, margin OK" if _ba > _plan_c + 3 else
                 ("TIGHT -> collect booster first" if _boost else "TIGHT -> no booster known, risk game-over")),
              once_key="budget_math_%d" % _round)
        # THE STANDING RULE. Measured: this agent collects boosters ONLY at bar=8 -- eight actions from death, every
        # time -- and dies anyway. At bar=8 a booster is not margin, it is a debt already due. The winning play takes
        # boosters EARLY and never drops below ~57% of the meter, because on this board a level costs ~41 actions of a
        # 42-action meter: the booster is what buys the right to make a mistake, and an agent with no margin cannot
        # afford to be wrong even once.
        _full_meter = 0
        try:
            _st_h = getattr(adapter, "_micro_market", None)
            if _st_h and _st_h.get("arena"):
                import micro_market as _MMh
                for _ch in _st_h["arena"].chains:
                    if isinstance(_ch, _MMh.Q1Hud):
                        _full_meter = getattr(_ch, "full_seen", 0) or 0
        except Exception:
            pass
        # THE STANDING RULE WAS TRIED AND IT LOST. Measured against the panic rule over 900 actions: boosters
        # collected 9 -> 3, deaths 22 -> 26, actions-nearly-dead 79 -> 90. It fires EARLIER (bar 12/20/20 vs 8/8/8)
        # and far rarer, because "still affordable after the detour" is almost never true once the meter is under
        # 55% -- so it made the panic branch pickier without giving it a working alternative. Reverted rather than
        # tuned: the reason it fails is not the threshold.
        #
        # THE REAL FINDING, which no booster policy fixes: at bar=8 with a plan costing more than 8, the agent is
        # ALREADY LOST, and no rule about when to detour can save it. The winner never arrives at bar=8 because it
        # walks a 41-action path on a 42-action meter. Ours wanders. The booster is downstream of navigation, and a
        # resource policy cannot repay a debt that pathing keeps running up.
        _panic = _ba <= _plan_c + 3
        if _panic and _boost is not None and _boost.get("inst") not in _dead_boosters:
            _b_before = _budget_actions()
            _emit(adapter, "PLAN  budget tight -> DETOUR to booster@%s BEFORE aligning  [sequence resources into the path]" % (_boost["inst"],))
            _arrived = _goto((_boost["inst"][0], _boost["inst"][1]), reason="collect booster (budget)")
            if _won[0] is not None:
                break
            if _budget_actions() > _b_before + 1:              # budget rose -> the booster paid out
                _emit(adapter, "SUBGOAL  booster@%s COLLECTED (+%.0f actions) -> resource sequenced into the plan; "
                      "align now with budget to spare" % (_boost["inst"], _budget_actions() - _b_before),
                      once_key="boost_got_%d" % _round)
                continue
            # Budget did NOT rise. That has TWO causes and they call for opposite responses: the booster is spent, OR
            # navigation never got there. _goto TELLS us which -- it returns whether it arrived -- so ask it instead of
            # blaming the booster by default. Blacklisting a booster we never reached retires the one resource that
            # could fund the trip, over a failure that was ours.
            if not _arrived:
                _emit(adapter, "REACH-FAIL  could not REACH booster@%s (navigation failed, budget unchanged) -> this is a "
                      "ROUTE failure, not a dead booster: keep it live and re-try it once the map improves"
                      % (_boost["inst"],), once_key="boost_unreached_%d" % _round)
                # fall through and align with what we have; the booster stays a candidate.
            else:
                _dead_boosters.add(_boost["inst"])             # ARRIVED and it still paid nothing -> genuinely spent/inert
                _emit(adapter, "BUDGET-BREAK  REACHED booster@%s and the budget did not move -> it is spent/inert, mark it "
                      "DEAD, stop re-detouring, and ALIGN with the actions I have  [measured at the booster, not guessed "
                      "from a failed approach]" % (_boost["inst"],), once_key="budget_break")
        if not dif:                                            # GATE satisfied -> navigate to EXIT
            _emit(adapter, "GATE  MATCH(key@%s, lock@%s) on %s SATISFIED -> navigate to the exit (lock)" % (key, lock, props))
            _goto(_budget_exit(lock), cap=60, reason="reach exit gate")
            if _won[0] is not None:
                break
            if set(props) != {"shape", "orientation", "colour"}:   # REVISE (Gap 3): objective was incomplete
                props = ["shape", "orientation", "colour"]
                _emit(adapter, "REVISE  gate fired but NO win -> objective hypothesis INCOMPLETE; broaden MATCH to all "
                      "properties and re-align  [learning from the failed gate]")
                continue
            _emit(adapter, "REVISE  gate fired but no win even with all properties -> attribute to navigation/exit; explore")
            for _ in range(6):
                _smart_step()
                if _won[0] is not None:
                    break
            continue
        _emit(adapter, "ENUMERATE  sub-goals := %s differ (key@%s vs lock@%s)  [align EACH before the gate opens]" % (dif, key, lock))
        _dif0 = len(dif)
        progressed = False
        # ALIGN via the REAL EXIT TEST. Measurement shows the lock is a tiny glyph that reads noisily, but the KEY has few
        # states and some MATCH the lock -- so cycle the key and ATTEMPT THE EXIT after each state. The win itself is the
        # ground-truth match test, robust to a noisy lock readout (don't depend on comparing two noisy small glyphs).
        ktrigs = [(t, a) for t, a in cmap.items() if a.get("effect") in ("shape", "orientation", "colour") and a.get("inst")]
        # CYCLE-AND-MATCH (the fix): the key/lock differ on an attribute a trigger cycles. After EACH step CHECK the
        # match FIRST -- the MOMENT key==lock, STOP cycling and walk out the door. NEVER step again past a matching state
        # (the bug was: step-then-attempt-exit overshoots the match). Use a known cycler if cached, else sweep candidates.
        ktrigs = [(t, a) for t, a in cmap.items() if a.get("effect") in ("shape", "orientation", "colour") and a.get("inst")]
        _cyclers = [a["inst"] for t, a in ktrigs] or [ins[0] for ins in cand.values()]
        _emit(adapter, "PLAN  CYCLE-AND-MATCH: after each cycle step CHECK the match; the instant key==lock STOP and exit "
              "the door -- do NOT cycle past the matching state  [%d cycler candidate(s)]" % len(_cyclers), once_key="cyc_match_%d" % _round)
        # ALIGN AS A CONJUGATE  A.B^k.A^-1 : reach the cycler ONCE (set up), apply the cycle IN PLACE k times (operate),
        # exit on match (undo). The old loop re-walked to the cycler for EVERY cycle step and stepped off with the
        # exploratory step, so on a tight meter the walk drained the bar, the life died, and respawn threw the avatar to
        # start -- the transform (the walk) paid once PER FIRE instead of once. Order candidates by REACH COST so a near
        # cycler is tested before a far one: a walk I can afford proves more than one that costs a life.
        _rank = sorted(_cyclers, key=lambda _i: ((_path_cost((_i[0], _i[1])) is None),
                                                 (_path_cost((_i[0], _i[1])) if _path_cost((_i[0], _i[1])) is not None else 1e9)))
        # ATTEMPT-OUTCOME MEMORY -- SECONDARY CONSUMPTION (RULE 0.8 fix A, the load-bearing half on the mover path). The L1
        # re-live lock lives in the SOLVE regime, where the committed plan is a DETERMINISTIC function of (board, cmap): the
        # reach-cost ranking of cyclers. Raising the explore RATIO (the primary consumption below) governs bootstrap-vs-solve
        # UPSTREAM but never reaches this deterministic ranker, so it left the trajectory unchanged (matched A/B: explore-only
        # consumption gave no robust Jaccard drop). Per the design, make the agent's OWN ranker outcome-aware: coarse cells it
        # has committed-and-FAILED repeatedly (tries>=3, no progress) get DEPRIORITISED -- sorted AFTER untried ones -- so a
        # genuinely-untried ordering gets a turn. Stable re-sort preserves reach-cost order among equals. LAW 0: this only
        # pushes the agent's OWN known-failing choice later; it never names a target or promotes an answer. Gated identically.
        import os as _os_rr
        if _os_rr.environ.get("OURO_ATTEMPT_MEMORY", "0") == "1" and _rank:
            try:
                _amr = _GLOBAL_KNOWLEDGE.get("attempts", {}).get("%s:L%d" % (_gid, _lp_lvl), {})
                _failw = {}
                for _s, _r in _amr.items():
                    if not isinstance(_r, dict):
                        continue
                    _tr = _r.get("tries", 0)
                    if _tr >= 3:
                        for _c in _s:                              # coarse cells of a repeatedly-failed committed plan
                            _failw[_c] = _failw.get(_c, 0) + (_tr - 2)
                if _failw:
                    _rank = sorted(_rank, key=lambda _i: _failw.get((int(_i[0]) // 2, int(_i[1]) // 2), 0))
                    _emit(adapter, "REORDER  the agent's own ranker is now outcome-aware: %d coarse cell(s) it committed-and-"
                          "failed >=3x at L%d are pushed LATER so an untried ordering gets a turn (reach-cost order kept among "
                          "equals) -- its own failure memory, no target chosen" % (len(_failw), _lp_lvl),
                          once_key="reorder_%d_%d" % (_lp_lvl, sum(_failw.values())))
            except Exception:
                pass
        # ATTEMPT-OUTCOME MEMORY (RULE 0.8 fix A; design: DESIGN_attempt_memory_and_rederivation.md). The agent re-lived
        # the SAME failing plan every life (43 lives, occupancy Jaccard 0.94, died at one cell 36/43x) because it carries
        # the PLAN forward across lives but not the OUTCOME. Per the design the attempt SIGNATURE is target-ORDER + region:
        # sign by the ordered, lightly-coarsened committed target instances (_rank) -- this is the reach-cost target-order
        # AND a coarse region in one. Address re-binds ACROSS boards (Layer 6), but the per-level KEY already scopes to one
        # board, so committed positions are stable+meaningful within it. The type-map is EMPTY on the mover path (no typed
        # cyclers), which collapsed a type-only signature to all-None -> it counted lives, not plans; the coarse-instance
        # signature is non-degenerate and DECAYS when the agent commits a genuinely different plan. OUTCOME-GATE (design:
        # made_progress): only count a repeat when the plan made NO progress. DURABLE progress = the running-best objective
        # residual for this level IMPROVED since the last commit -- NOT the flickering within-life "learning" slope, which
        # (diagnosed: 1 stable sig, max_tries stuck at 3 over ~11 lives) reset the counter on transient error dips and stopped
        # the cross-life failure signal from EVER accumulating, so the ranker below never engaged. The running-best is
        # monotone non-increasing over the run, so once the agent plateaus (never beats its best -> never clears L1) the
        # failure count climbs every life and the ranker gets to diversify; a genuine improvement still resets it (don't
        # punish a near-solve). Tally per game:level (clearing the level moves to a new key). Gated OURO_ATTEMPT_MEMORY.
        import os as _os_am
        if _os_am.environ.get("OURO_ATTEMPT_MEMORY", "0") == "1":
            try:
                _sig = tuple((int(_i[0]) // 2, int(_i[1]) // 2) for _i in _rank[:6])   # order + coarse region, one descriptor
                _amem = _GLOBAL_KNOWLEDGE.setdefault("attempts", {}).setdefault("%s:L%d" % (_gid, _lp_lvl), {})
                _amem["_last_sig"] = _sig
                _rec = _amem.setdefault(_sig, {"tries": 0})
                _hist = _RF2.SHARED.learning_progress.hist.get(_lp_key, [])
                _cur_best = min(_hist) if _hist else None                 # best (lowest) objective error seen for this level
                _prev_best = _amem.get("_best_resid")
                _progressed = (_cur_best is not None and _prev_best is not None and _cur_best < _prev_best - 1e-9)
                if _cur_best is not None and (_prev_best is None or _cur_best < _prev_best):
                    _amem["_best_resid"] = _cur_best                     # record the new running-best
                if _progressed:
                    _rec["tries"] = 0                                    # durable improvement -> don't punish a near-solve
                else:
                    _rec["tries"] += 1                                   # same plan, no durable progress -> failure repeating
                    if _rec["tries"] >= 3:
                        _emit(adapter, "ATTEMPT-MEMORY  this plan (%d committed targets, region-signed) re-committed %dx at "
                              "L%d with NO durable progress (best objective residual %s not improved) -> the same approach "
                              "that failed before is failing again; flag for EXPLORE"
                              % (len(_sig), _rec["tries"], _lp_lvl, ("%.3f" % _cur_best) if _cur_best is not None else "n/a"),
                              once_key="attmem_%s_%d" % (str(_sig), _rec["tries"]))
            except Exception:
                pass
        if _rank:
            _emit(adapter, "PLAN  reach-cost order := %s  [cheapest cycler first; a far one swept first spends a life "
                  "proving nothing]" % ([(int(_i[0]), int(_i[1]),
                  (None if _path_cost((_i[0], _i[1])) is None else int(_path_cost((_i[0], _i[1]))))) for _i in _rank[:4]],),
                  once_key="cyc_order_%d" % _round)

        def _try_joint_plan():
            # JOINT (position x phase) PREDICATE SEARCH. "Cycle the key to the lock's value" and "walk to the door"
            # are not two problems in sequence -- they are ONE search over the PRODUCT space (avatar-cell x key-
            # phase), solved by _best_first with the "predicate" priority. Stepping a cycler cell advances the phase;
            # the search finds a route that arrives at the door WITH the phase already right, cycling en route. This
            # is the conjugate the egocentric loop below keeps flattening, read at the altitude where it is one move.
            # LAW 0: nothing here is an answer -- the cycler cells, period, value-order, the key's value, the lock's
            # target value and the exit cell are ALL the agent's own learned perceptions. Returns True iff it won;
            # False (fall through to the proven conjugate loop) on any incompleteness or the first plan desync.
            import os as _oj
            _jdbg = _oj.environ.get("OURO_JOINT_DEBUG") == "1"
            if _oj.environ.get("OURO_JOINT_PLAN", "1") != "1" or len(dif) != 1:
                if _jdbg: _emit(adapter, "JOINT-DBG  gate0 dif=%s (need len1)" % (dif,), once_key="jdbg0_%d" % _round)
                return False
            _att = dif[0]
            _tg = [(t, a) for t, a in cmap.items() if a.get("effect") == _att and a.get("inst")
                   and a.get("period", 0) >= 2 and a.get("cycle")]
            if not _tg:
                if _jdbg: _emit(adapter, "JOINT-DBG  gate1 no cycler for '%s' in cmap. cmap effects=%s" %
                                (_att, [(str(_t), _a.get("effect"), _a.get("period"), bool(_a.get("cycle")))
                                        for _t, _a in cmap.items()][:6]), once_key="jdbg1_%d" % _round)
                return False
            _period = int(_tg[0][1]["period"]); _order = list(_tg[0][1]["cycle"])
            if _period < 2 or len(_order) < 2:
                if _jdbg: _emit(adapter, "JOINT-DBG  gate2 period=%d order=%s" % (_period, _order), once_key="jdbg2_%d" % _round)
                return False
            _trig_cells = set()
            for _t, _a in _tg:
                for _i in (_a.get("insts") or [_a.get("inst")]):
                    if _i is not None:
                        _trig_cells.add(tuple(_cell(_i)))
            def _valof(pr):
                return (pr.get("canon_shape") if _att == "shape" else pr.get("orient") if _att == "orientation"
                        else tuple(pr.get("colours") or ()))
            _kv = _valof(_read_at(key) or {}); _lv = _valof(_read_at(lock) or {})
            if _kv is None or _lv is None or _kv not in _order or _lv not in _order:
                if _jdbg: _emit(adapter, "JOINT-DBG  gate3 kv=%s lv=%s order=%s" % (_kv, _lv, _order), once_key="jdbg3_%d" % _round)
                return False
            ap = _apos()
            if ap is None:
                return False
            _exit_px = _budget_exit(lock); _exitc = _cell(_exit_px)
            g = _g(); _flr = set(_floor_now() or ()); _wl = set(int(w) for w in walls); _blk = _sm_blocked() or set()
            def _passable(cell):
                r, c = cell[0] * quantum, cell[1] * quantum
                if not (0 <= r < H and 0 <= c < W):
                    return False
                if cell in _blk:
                    return False
                v = int(g[r, c])
                return (v in _flr) if _flr else (v not in _wl)
            _acts_inv = {(0 if dy == 0 else (1 if dy > 0 else -1), 0 if dx == 0 else (1 if dx > 0 else -1)): a
                         for a, (dy, dx) in steer.items()}
            _kidx = _order.index(_kv); _tidx = _order.index(_lv)
            def _neighbors(st):
                (cell, ph) = st; out = []
                for u, a in _acts_inv.items():
                    nc = (cell[0] + u[0], cell[1] + u[1])
                    if nc != cell and _passable(nc):
                        nph = (ph + 1) % _period if nc in _trig_cells else ph
                        out.append((a, (nc, nph), 1))
                return out
            def _isgoal(st):
                (cell, ph) = st
                return ph == _tidx and abs(cell[0] - _exitc[0]) + abs(cell[1] - _exitc[1]) <= 1
            def _disc(st):
                (cell, ph) = st
                return ((_tidx - ph) % _period) + abs(cell[0] - _exitc[0]) + abs(cell[1] - _exitc[1])
            _acell = _cell(ap)
            plan = _best_first((_acell, _kidx), _neighbors, _isgoal, _priority_predicate(_disc), max_nodes=20000)
            if not plan:
                return False
            _emit(adapter, "PLAN  JOINT (pos x phase) search: ONE route cycles %s by %d step(s) to the lock's value AND "
                  "walks to the door -- %d actions, the phase and the navigation solved TOGETHER over the product "
                  "space, not in sequence  [predicate priority on _best_first -- the generalized traversal]"
                  % (_att, (_tidx - _kidx) % _period, len(plan)), once_key="joint_plan_%d" % _round)
            _cur = (_acell, _kidx)
            for _a in plan:
                if _won[0] is not None or _spent[0] >= budget or _budget_actions() < 2:
                    break
                _exp = next((nst for (aa, nst, sc) in _neighbors(_cur) if aa == _a), None)
                _planned_move[0] = True
                try:
                    _stepw(_a)
                finally:
                    _planned_move[0] = False
                if _won[0] is not None:
                    return True
                _ap2 = _apos()
                if _ap2 is None:
                    return False
                _now = _cell(_ap2)
                if _exp is not None and abs(_now[0] - _exp[0][0]) + abs(_now[1] - _exp[0][1]) > 1:
                    _emit(adapter, "REROUTE  joint plan desynced (a step met an unmodeled wall) -> handing back to the "
                          "conjugate align loop", once_key="joint_desync_%d" % _round)
                    return False
                _kv2 = _valof(_read_at(key) or {})
                _cur = (_now, _order.index(_kv2) if _kv2 in _order else _cur[1])
                if not _differ()[2]:
                    _goto(_budget_exit(lock), cap=60, reason="exit the door (joint plan matched)")
                    return _won[0] is not None
            return _won[0] is not None

        if _try_joint_plan():
            break

        for _ci, _inst in enumerate(_rank):
            if _won[0] is not None or _spent[0] >= budget or _budget_actions() < 4:
                break
            _o0 = (_read_at(key) or {}).get("orient"); _cyc = False; _lv0 = _lives_now()
            _reached = _goto((_inst[0], _inst[1]), reason="reach cycler %d -- set the cycle up ONCE" % _ci)   # A: set up once
            _tcell = tuple(_cell(_inst))
            if _reached and _tcell not in _reached_trigs:
                _reached_trigs.add(_tcell)
                _rt = _mechanics(adapter).setdefault("reached_triggers", [])
                if _tcell not in _rt:
                    _rt.append(_tcell)
                _emit(adapter, "SUBGOAL  REACHED trigger@%s (cell %s) -- navigation to it is SOLVED and kept, so this is a "
                      "standing capability of the gameplay, not a thing to rediscover each life  [%d reached so far]"
                      % (_inst, _tcell, len(_reached_trigs)), once_key="reach_trig_%s_%d" % (_tcell, _round))
            if not _reached:
                _emit(adapter, "REACH-FAIL  never REACHED trigger@%s -> UNTESTED, not rejected: keep it as a candidate "
                      "rather than convicting it on a route failure" % (_inst,), once_key="trig_unreached_%d_%d" % (_ci, _round))
                continue
            _rc = _mechanics(adapter).setdefault("recontact", {"rule": None})   # the agent's OWN induced re-fire method
            def _sgval():                                       # the key's value(s) for the attribute(s) I am aligning
                r = _read_at(key) or {}
                return tuple((r.get("canon_shape") if _a == "shape" else r.get("orient") if _a == "orientation"
                              else tuple(r.get("colours") or ()) if _a == "colour" else None) for _a in dif)
            _seen_vals = set()                                 # sub-goal states this cycler has produced (loop detector)
            for _c in range(7):                                # B^k: operate IN PLACE -- the transform is already paid
                if _won[0] is not None or _spent[0] >= budget or _budget_actions() < 3:
                    break
                if not _differ()[2]:                           # match -> exit (A^-1), the instant we match
                    _emit(adapter, "COMPARE  key MATCHES lock -> STOP cycling, walk out the door NOW (don't step past it)", once_key="match_exit")
                    _goto(_budget_exit(lock), cap=60, reason="exit the door (key matches lock)")
                    break
                if _lives_now() is not None and _lv0 is not None and _lives_now() < _lv0:
                    _emit(adapter, "RESPAWN  lost a life mid-cycle -> the board threw me back to start and the cycler is no "
                          "longer under me. Re-reach it rather than cycling empty floor", once_key="cyc_respawn_%d" % _round)
                    break                                      # respawn moved me -> outer loop re-reaches; do NOT fire on floor
                _prd = _read_at(key) or {}
                _pre_state = (_prd.get("canon_shape"), _prd.get("orient"), tuple(_prd.get("colours") or ()))
                _pre_diff = set(_differ()[2])
                # RE-FIRE METHOD is the agent's to INDUCE, not mine to hardcode. Test the cheapest hypothesis first --
                # STAY (act into a wall so the avatar does not move) -- and read whether the key CHANGED. Change is read
                # over the WHOLE glyph state (shape+orientation+colour), so a trigger that cycles the agent's ACTUAL
                # sub-goal attribute is never missed by watching a single hardcoded axis (the old bug: watch orient,
                # miss a shape-cycler).
                _fired = False; _changed = False
                if _rc["rule"] in (None, "stay"):
                    ap = _apos(); _stayed = False
                    if ap is not None:
                        g = _g(); r0, c0 = int(round(ap[0])), int(round(ap[1]))
                        for a in _rnd.sample(list(steer.keys()), len(steer)):
                            dy, dx = steer[a]
                            r = r0 + (quantum if dy > 0 else -quantum if dy < 0 else 0)
                            c = c0 + (quantum if dx > 0 else -quantum if dx < 0 else 0)
                            if 0 <= r < H and 0 <= c < W and int(g[r, c]) in walls:
                                _stepw(a); _stayed = True; break
                    if _stayed:
                        _mdd = _read_at(key) or {}
                        _mid_state = (_mdd.get("canon_shape"), _mdd.get("orient"), tuple(_mdd.get("colours") or ()))
                        if _mid_state != _pre_state:
                            if _rc["rule"] is None:
                                _rc["rule"] = "stay"
                                _emit(adapter, "INDUCE  re-contact := STAYING re-fires -- the key changed without my leaving "
                                      "the cell, so I hold position and cycle in place; the walk is paid ONCE  [read from the "
                                      "frame, not assumed]", once_key="rc_stay_%d" % _round)
                            _fired = True; _changed = True
                        elif _rc["rule"] is None:
                            _rc["rule"] = "reland"
                            _emit(adapter, "INDUCE  re-contact := requires RE-LANDING -- staying did not re-fire, so the "
                                  "trigger fires on ARRIVAL. Step one cell off and back on, staying ADJACENT so the re-land "
                                  "stays cheap  [read from the frame]", once_key="rc_reland_%d" % _round)
                if not _fired:
                    # RE-LAND: local one-cell step-off then step back onto the ADJACENT cycler (the transform stays paid-once).
                    _smart_step(local_only=True)
                    _goto((_inst[0], _inst[1]), reason=None)
                    _psd = _read_at(key) or {}
                    _post_state = (_psd.get("canon_shape"), _psd.get("orient"), tuple(_psd.get("colours") or ()))
                    _changed = (_post_state != _pre_state)
                # Judge the trigger by its effect on the SUB-GOAL I enumerated -- not a hardcoded axis. Mismatch shrank =
                # the right cycler; a NEW attribute now mismatched = it cycles the WRONG thing here (reject, try next);
                # same mismatch-set = modular progress on the right attribute (keep going toward the lock's state).
                if _changed:
                    _post_diff = set(_differ()[2])
                    if _post_diff < _pre_diff:
                        _cyc = True
                        _emit(adapter, "PERCEIVE  this trigger SHRANK my mismatch %s -> %s -- it moves what I need; keep "
                              "cycling toward the match" % (sorted(_pre_diff), sorted(_post_diff)), once_key="cyc_shrink_%d" % _round)
                    elif _post_diff - _pre_diff:
                        _emit(adapter, "REVISE  this trigger CHANGES the key but INTRODUCES a new mismatch (%s -> %s) -- it "
                              "cycles the WRONG attribute for sub-goal %s; reject it, try the next candidate"
                              % (sorted(_pre_diff), sorted(_post_diff), sorted(dif)), once_key="trig_wrong_%d_%d" % (_ci, _round))
                        break
                    else:
                        _val = _sgval()
                        _readable = None not in _val           # an unreadable transient is not a looped cycle
                        if _readable and _val in _seen_vals:   # a READABLE state repeated -> the cycle has LOOPED
                            _emit(adapter, "REVISE  this trigger's cycle has LOOPED (state %s seen before) and never "
                                  "produced the lock's value for %s -> its range does NOT contain my target; reject it, "
                                  "try the next candidate" % (list(_val), sorted(dif)), once_key="trig_looped_%d_%d" % (_ci, _round))
                            break
                        if _readable:
                            _seen_vals.add(_val)
                        _cyc = True
                        _emit(adapter, "PERCEIVE  cycle advanced (mismatch still %s, state %s) -> modular cycle on the right "
                              "attribute; keep stepping toward the lock's state" % (sorted(_post_diff), list(_val)),
                              once_key="cyc_advance_%d" % _round)
                progressed = True
                if not _changed and _c >= 2:
                    _emit(adapter, "REVISE  stood on trigger@%s and the key did NOT change -> inert for this sub-goal; try "
                          "the next candidate" % (_inst,), once_key="trig_rejected_%d_%d" % (_ci, _round))
                    break
            if _won[0] is not None:
                break
        # real progress = mismatch shrank OR we won; else fall through to self-correction + exploration
        progressed = (_won[0] is not None) or (len(_differ()[2]) < _dif0) or progressed
        if not progressed:                                     # STUCK this round -> SELF-LOCALISE the error (don't just flail)
            _surprise += 1
            _kl_hist.append((key, lock))
            _recent_locks = set(l for k, l in _kl_hist[-3:])
            _recent_keys = set(k for k, l in _kl_hist[-3:])
            _missing = [sg for sg in dif if not any(a.get("effect") == sg for a in cmap.values())]
            # #3 CUSUM FIRST: if surprise has accumulated past the change-point, the current model keeps failing -> SPECIATE
            # (reset binding, broaden objective, and RE-RUN the confirmation experiment) rather than loop on one layer.
            if _surprise >= 4:
                _emit(adapter, "CUSUM  accumulated surprise S=%d >= change-point -> MODEL-INCOMPLETE / SPECIATE: reset the "
                      "binding, broaden the objective, and RE-RUN trigger confirmation  [#3 -- stop retrying a model that "
                      "keeps failing]" % _surprise)
                _kl[0] = None; props = ["shape", "orientation", "colour"]; _surprise = 0
                for _tt, _ins in list(cand.items())[:4]:       # RE-RUN one confirmation pass on untyped/unconfirmed triggers
                    if _tt in cmap and cmap[_tt].get("effect"):
                        continue
                    _pre = _all_glyphs()
                    if _goto(_ins[0], reason="re-confirm trigger-type %s" % (_tt,)):
                        _post = _all_glyphs()
                        for _p in set(_pre) & set(_post):
                            _a, _b = _pre[_p], _post[_p]
                            if _a and _b and (_a["canon_shape"], _a["orient"], _a["colours"]) != (_b["canon_shape"], _b["orient"], _b["colours"]):
                                _ef = "colour" if _a["colours"] != _b["colours"] else ("shape" if _a["canon_shape"] != _b["canon_shape"] else "orientation")
                                cmap[_tt] = {"effect": _ef, "display": _p, "cycle": [], "period": 1, "inst": _ins[0]}
                                _emit(adapter, "CACHE  (re-induced) causal-map[type %s] := CYCLE(%s.%s)  [confirmed on the "
                                      "speciation pass]" % (_tt, _p, _ef)); break
                    _smart_step()
                    if _won[0] is not None:
                        break
                continue
            # #4 TRIANGULATE via the SHARED evolvability_engine.triangulate (regime-agnostic residual -> shadow), instead
            # of hand-rolled thresholds: score each layer as a correlate, let the engine pick which casts the shadow.
            _perc = 1.0 if (len(_recent_locks) > 1 or len(_recent_keys) > 1) else 0.0
            _modl = 0.8 if _missing else 0.0
            try:
                import evolvability_engine as _EE
                _shadow = _EE.triangulate(type("R", (), {"correlates": {"PERCEPTION": _perc, "MODEL": _modl}})(), min_shadow=0.15)
            except Exception:
                _shadow = {k: v for k, v in (("PERCEPTION", _perc), ("MODEL", _modl)) if v >= 0.15}
            _layer = max(_shadow, key=_shadow.get) if _shadow else None
            if _layer == "PERCEPTION":                          # (a) PERCEPTION layer (shadow strongest here)
                _emit(adapter, "TRIANGULATE  residual -> PERCEPTION layer (engine.triangulate shadow=%s): key/lock binding "
                      "UNSTABLE (%d distinct lock reads/3 rounds) -> a perception artifact, not a real gap"
                      % ({k: round(v, 2) for k, v in _shadow.items()}, len(_recent_locks)))
                _emit(adapter, "RE-INDUCE  object-resolution: reset the key/lock binding and re-detect the displays  [#6]")
                _kl[0] = None                                                   # #6 re-induction: drop the cache -> re-detect
                continue
            if _layer == "MODEL":                                              # (b) MODEL layer
                _emit(adapter, "TRIANGULATE  residual -> MODEL layer (engine.triangulate): no confirmed trigger for %s -> "
                      "causal map INCOMPLETE, re-probe to find the cycler" % _missing, once_key="tri_model_%d" % (_surprise // 2))
                if _probe_for_property(_missing):              # OVERRIDE transfer-skip: find the trigger for the missing
                    continue                                   # property (re-probe recognized triggers) -> objective reachable
                if not _goto_salient():                        # else go to a salient object / explore uncharted space
                    _explore_step()
                continue
            _emit(adapter, "EXPLORE  no deliberate progress, no layer flagged -> GO TO the nearest salient object (not "
                  "wander dead space)", once_key="explore_fb_%d" % _round)
            for _ in range(6):
                if _won[0] is not None:
                    break
                if not _goto_salient():                        # nearest salient object -> else uncharted -> else stop
                    break

    # ---- STEP 9: WIN -> DECONSTRUCT -> TRANSFER + GROW ----
    if _won[0] is not None:
        _emit(adapter, "OUTCOME  reached a WIN  [objective satisfied]")
        # TARGETED avatar win-condition: did the SPECIFIC key/lock pair go DIFFER -> MATCH exactly at the win? This is
        # more precise than the generic "any two glyphs match" and avoids learning spatial coincidences (e.g. SAME_ROW).
        try:
            kl = _keylock()
            if kl:
                from scipy.ndimage import label as _lblw
                _kkey, _klock = kl

                def _rd(gf, pos):
                    gf = np.asarray(gf); bgc = set(np.argsort(np.bincount(gf.ravel()))[-2:].tolist())
                    for c in np.unique(gf):
                        if int(c) in bgc:
                            continue
                        lab, n = _lblw(gf == c, structure=np.ones((3, 3)))
                        for i in range(1, n + 1):
                            ys, xs = np.where(lab == i)
                            if 2 <= len(ys) <= 40 and abs(int(ys.mean()) - pos[0]) + abs(int(xs.mean()) - pos[1]) <= 4:
                                return _object_props(gf, ys, xs)
                    return None
                _mseq = []
                for gf in ([g0] + _traj):                      # scan the trajectory (holds the matched frame before win)
                    gk, gl = _rd(gf, _kkey), _rd(gf, _klock)
                    if gk and gl:
                        _mseq.append(gk["canon_shape"] == gl["canon_shape"] and gk["orient"] == gl["orient"])
                _violated_early = any(not s for s in _mseq[:max(1, len(_mseq) // 2 + 1)])
                _ever_matched = any(_mseq)                      # key reached the lock's state at SOME point (not just last)
                if _mseq and _violated_early and _ever_matched:
                    _wcm = KN.setdefault("win_condition", {"formula": [], "conf": {}, "wins": 0})
                    _nm = "MATCH(key,lock)"
                    _wcm["conf"][_nm] = _wcm["conf"].get(_nm, 0) + 1
                    if _nm not in _wcm["formula"]:
                        _wcm["formula"].append(_nm)
                    _emit(adapter, "INDUCE  win-condition := MATCH(key,lock) confirmed \u00d7%d  [TARGETED: the key/lock glyph "
                          "states went DIFFER->MATCH exactly at the win -> THIS is what winning meant, not a spatial "
                          "coincidence; carried forward]" % _wcm["conf"][_nm])
        except Exception:
            pass
        try:
            wc = _induce_win_condition([g0] + hist[-30:] + _won[0], KN)   # scan the history: it holds the MATCHED frames
            if wc.get("_added"):                                          # (key=lock) before the win, not just the flip frame
                _emit(adapter, "COMPOSE  win-condition grew by %s  [newly-discriminating predicate AND-ed in]" % (wc["_added"],))
            if wc.get("_pruned"):
                _emit(adapter, "PRUNE  dropped %s  [did not re-confirm on >=half of wins -> a coincidence]" % (wc["_pruned"],))
            if wc.get("formula"):
                _emit(adapter, "INDUCE  win-condition := %s  [%s -- DECONSTRUCTED from the win (wins=%d); coincidences "
                      "pruned; TRANSFERRED forward and expected to grow]"
                      % (" \u2227 ".join(wc["formula"]),
                         ", ".join("%s x%d" % (n.split("(")[0], wc["conf"].get(n, 1)) for n in wc["formula"]), wc.get("wins", 1)))
            # NARRATE the session's new machinery into the frame data (DSL mandate: nothing may happen silently). Each
            # line is GENERATED FROM the actual measured state, so it cannot drift from the behaviour.
            _vr = wc.get("_vcs")
            if _vr is not None and not _vr.get("kept"):
                _emit(adapter, "RESTRUCTURE  win-condition prune REVERTED  [would orphan %d verified predictions -- self-"
                      "reverting composer kept the invariant]" % _vr.get("orphaned", 0))
            _tr = wc.get("_tropism")
            if _tr and _tr.get("top"):
                _emit(adapter, "RANK  win-questions by info-gain: top=%s (MI=%.2f%s)  [binary-search hypothesis space -- "
                      "most-discriminating question asked first]"
                      % (_tr["top"].split("(")[0], _tr.get("score", 0.0), ", decisive" if _tr.get("decisive") else ""))
            try:
                import regime_factory as _RFn
                _rm = getattr(_RFn.SHARED, "resonance_market", None)
                if _rm is not None and wc.get("formula"):
                    _w = wc["formula"][0]
                    _res = _rm.resonance(_w)
                    if _res >= 2:
                        _emit(adapter, "RESONANCE  %s: %d independent derivations converge  [cross-source agreement "
                              "amplifies -- v4 accelerant transformed to n=1]" % (_w.split("(")[0], _res))
                _mk = getattr(_RFn.SHARED, "hypothesis_market", None)
                if _mk is not None:
                    _rk = _mk.ranked()
                    if len(_rk) >= 2:
                        _emit(adapter, "MARKET  %d competing objective-hypotheses, winner=%s  [micro-HGT: express-before-"
                              "judge, fitness=-surprise (Friston)]" % (len(_rk), _mk.winner().split("(")[0] if _mk.winner() else "?"))
            except Exception:
                pass
        except Exception:
            pass

    # ===========================================================================================================
    # ROUTE THE RESIDUAL -- the connection the atoms have been waiting on.
    #
    # PASS 4 (the evolvability engine) lives inside validate(). The AVATAR REGIME never calls validate(): it goes
    # regime_factory.AvatarRegime.solve -> _avatar_solve -> return. So on every game this regime plays -- which is
    # ls20, which is the game -- new_engine() is constructed, and on_residual() is never called once. Measured:
    # `_avatar_solve` 2 calls, `validate()` 1, `new_engine()` 1, `on_residual` 0.
    #
    # The mechanism was never missing. It was unreachable. "The atoms exist. The work is connecting them."
    #
    # The residual here is the avatar regime's OWN MODEL_INCOMPLETE: the composer ran its model to exhaustion --
    # aligned what it believed the triggers were, walked where it believed the exit was -- and the world paid
    # nothing. That is precisely "the grammar was satisfied and unrewarded", stated in this regime's terms.
    # ===========================================================================================================
    try:
        _lv_end = 0
        try:
            _lv_end = int(getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0)
        except Exception:
            pass
        if _lv_end <= _lv_start[0] and _rr is not None and _rr.routed == 0:
            # Backstop ONLY: if not one objective produced a residual all solve, the solve itself is the residual.
            # The per-objective route above is the real cadence; this catches a solve that never committed to
            # anything nameable, which is its own kind of finding.
            _route_avatar_residual(adapter, av, budget)
    except Exception:
        pass
    return hist


def _route_avatar_residual(adapter, av, budget):
    """Hand the avatar regime's residual to the evolvability engine.

    Everything below already existed and none of it was reachable from this regime:
      ResidualReporter  -- forward-model prediction error over the objective-keyed transition_buffer
      CUSUM             -- only a STABLE, REPRODUCED residual licenses a mint; one-off noise is pareidolia
      triangulate       -- does the residual cast a SHADOW across existing primitives?
      _route_three_way  -- shadow -> CO-OPT | representable -> MINT | neither -> ESCALATE, and NEVER mint,
                           because minting into a dimension that casts no shadow is representational apophenia
      DirectedMint      -- a new INSTANCE of a tested kind, parametrised BY the residual. Aimed, not open-atom.

    This function is the wire. It authors no new measure-function and invents no atom -- per the engine's own
    discipline, and per Levin, which forbids the alternative anyway.
    """
    try:
        import evolvability_engine as _EEa
    except Exception:
        return None
    _eng = getattr(adapter, "_evo_engine", None)
    if _eng is None:
        try:
            _eng = adapter._evo_engine = _EEa.new_engine()
        except Exception:
            return None
    try:
        g_now = _perceive_grid(adapter)
    except Exception:
        return None
    # THE STATUS BAR IS NOT THE WORLD. The first live routing returned residual bbox rows 40..62 carrying colour 11
    # -- the meter. The agent was reporting its own budget draining as "a dynamic my grammar cannot explain", which is
    # the one thing it explains perfectly. A residual is what the world did that the model did not predict; the model
    # is not surprised that spending an action costs an action. Mask the HUD in every grid handed to the reporter, or
    # the aim points at the agent's own resource display -- and an aim that points at the meter mints a primitive for
    # arithmetic we already have.
    def _mask_hud(gr):
        try:
            import numpy as _np
            _m = _np.array(gr, copy=True)
            _m[56:] = 0
            return _m
        except Exception:
            return gr
    _buf = [_mask_hud(b) for b in (list(getattr(adapter, "transition_buffer", []) or []))]
    g_now = _mask_hud(g_now)
    _g_before = _buf[0] if _buf else g_now
    # The avatar regime's satisfied-but-unrewarded claim, in the shape the reporter expects: the composer's own
    # model of the objective, which it executed and which paid nothing.
    _refuted = [({"descriptor": "avatar_plan_exhausted", "relation": "REACH"}, None)]
    _traces = {}
    try:
        _cm = (_GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("avatar_cmap", {}) or {}
        for _t, _at in _cm.items():
            _ins = _at.get("insts") or ([_at.get("inst")] if _at.get("inst") else [])
            if _ins:
                _traces[str(_at.get("effect") or _t)] = [tuple(i) for i in _ins if i is not None]
    except Exception:
        pass
    ctx = dict(g0=g_now, ctrl=av.get("colour") if isinstance(av, dict) else None,
               refuted=_refuted, atomics=[], g_before=_g_before, g_after=g_now,
               active_traces=_traces, compile_objective=compile_objective,
               compile_discrepancy=compile_discrepancy, descend=descend, pursue=pursue,
               adapter=adapter, budget=budget, buffer=_buf,
               held_grids=getattr(_eng, "held_out_levels", None))
    _won = _eng.on_residual(ctx)
    for _line in (getattr(_eng, "narration", []) or [])[-4:]:
        _emit(adapter, "RESIDUAL  %s" % str(_line)[:150], once_key="residual_%d" % (len(_eng.events) // 3))
    return _won


def _avatar_solve_placeholder():
    pass


def _avatar_pathfind(g, start, target, steer, quantum, wall_colours, blocked=None, floor=None, edges=None):
    """NAVIGATION: BFS over the avatar's grid from `start` (the self's centroid) to `target`, moving in quantum-sized
    steps in the 4 steer directions, blocked by wall_colours AND by `blocked` (lattice cells the shared SpatialMap has
    learned are impassable). Returns the ACTION SEQUENCE (via the inverted steer map) to reach within one quantum of the
    target, or None if unreachable. This is the composer for the avatar regime -- it composes the four primitive moves
    into a route, the way the cascade composed presses into a drain->fill order, over ONE authoritative spatial map.

    PERCEIVE-AND-PLAN: when `floor` (the perceived walkable colours) is given, passability is by INCLUSION -- only floor
    is walkable -- so the optimal, pocket-avoiding route is READ off the allocentric frame instead of discovered by
    bumping, and a mislabeled colour can't poison the path. Without floor it falls back to EXCLUSION (not-a-wall)."""
    from collections import deque
    g = np.asarray(g); H, W = g.shape
    dir2act = {}
    for act, (dy, dx) in (steer or {}).items():
        u = (0 if dy == 0 else (1 if dy > 0 else -1), 0 if dx == 0 else (1 if dx > 0 else -1))
        dir2act[u] = act
    if len(dir2act) < 4 or quantum < 1:
        return None
    wall = set(int(w) for w in wall_colours)
    flr = set(int(f) for f in (floor or ()))
    blk = blocked or set()
    s = (int(round(start[0])), int(round(start[1]))); t = (int(round(target[0])), int(round(target[1])))

    def passable(r, c):
        if not (0 <= r < H and 0 <= c < W):
            return False
        if (int(round(r / quantum)), int(round(c / quantum))) in blk:        # SpatialMap-learned dead ends
            return False
        if (r, c) == s or (abs(r - t[0]) + abs(c - t[1]) <= quantum):        # own cell + goal vicinity always enterable
            return True
        v = int(g[r, c])
        if flr:
            return v in flr                                                 # INCLUSION: plan ONLY on perceived floor
        return v not in wall                                                # EXCLUSION fallback (bump-learned walls)

    q = deque([s]); came = {s: None}
    while q:
        cur = q.popleft()
        if abs(cur[0] - t[0]) + abs(cur[1] - t[1]) <= quantum:
            path = []; n = cur
            while came[n] is not None:
                p = came[n]; du = (int(np.sign(n[0] - p[0])), int(np.sign(n[1] - p[1])))
                if du in dir2act:
                    path.append(dir2act[du])
                n = p
            return path[::-1]
        for u in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cur[0] + u[0] * quantum, cur[1] + u[1] * quantum
            # MEASURED beats INFERRED: if we actually tried this transition and it moved us nowhere, it is impossible --
            # a fact. Unmeasured transitions stay open, so a route is never refused on a colour guess alone.
            if edges and ((int(round(cur[0] / quantum)), int(round(cur[1] / quantum))), u) in edges:
                continue
            if (nr, nc) not in came and passable(nr, nc):
                came[(nr, nc)] = cur; q.append((nr, nc))
    return None


def _frame_glyphs(g):
    """The mutate-in-place glyph candidates in ONE frame (compact non-background objects) with their property vectors.
    Used by the MATCH win-predicates to ask 'do two glyphs (key & lock) coincide in shape / orientation / colour?'."""
    from scipy.ndimage import label as _lbl
    g = np.asarray(g); bg = set(np.argsort(np.bincount(g.ravel()))[-2:].tolist())
    out = []
    for c in np.unique(g):
        if int(c) in bg:
            continue
        lab, n = _lbl(g == c, structure=np.ones((3, 3)))
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            if 3 <= len(ys) <= 30:                             # compact glyph, not a bar or a big region
                h = ys.max() - ys.min() + 1; w = xs.max() - xs.min() + 1
                if max(h, w) <= 8:                             # roughly square-ish icon
                    out.append(_object_props(g, ys, xs))
    return out


def _perceive_avatar(probe):
    """PERCEIVE the SELF (the AVATAR fork of the grammar). `probe` maps colour -> [(action, dy, dx), ...] observed by
    issuing each discrete directional action. The AVATAR is the object whose displacement is a clean FUNCTION of the
    action -- each action produces a consistent, DISTINCT move -- i.e. the actions are its LOCOMOTION, not an actuation
    of some external thing. This is the fork the actuator grammar never tested: 'is one of these objects ME?'. Returns
    {colour, steer:{action:(dy,dx)}, dirs:{action:NAME}, magnitude} or None (-> non-avatar/actuator regime)."""
    best = None
    for col, moves in (probe or {}).items():
        by_act = {}; consistent = True
        for act, dy, dx in moves:
            key = (round(float(dy)), round(float(dx)))
            if act in by_act:
                if by_act[act] != key:
                    consistent = False; break
            else:
                by_act[act] = key
        if not consistent:
            continue
        active = {a: v for a, v in by_act.items() if abs(v[0]) + abs(v[1]) > 0}
        dirs = set(active.values())
        if len(active) >= 2 and len(dirs) >= 2:                # >=2 actions, moving in >=2 distinct directions -> a self
            mag = float(np.mean([abs(v[0]) + abs(v[1]) for v in active.values()]))
            if best is None or mag > best["magnitude"]:
                # normalise each action's move to a unit direction for the STEER map / naming
                names = {}
                for a, (dy, dx) in active.items():
                    u = (0 if dy == 0 else (1 if dy > 0 else -1), 0 if dx == 0 else (1 if dx > 0 else -1))
                    names[a] = _DIR_NAME.get(u, "%+d,%+d" % u)
                best = {"colour": int(col), "steer": active, "dirs": names, "magnitude": mag}
    return best


def _avatar_probe_moves(before, after):
    """One probe step: displacement (dy,dx) of every small object's centroid between two frames. Reused by the live
    prober to build the `probe` dict for _perceive_avatar. Colour/scale/rotation-agnostic."""
    before = np.asarray(before); after = np.asarray(after)
    bg = set(np.argsort(np.bincount(before.ravel()))[-2:].tolist())    # two most common = bg/wall

    def cen(g):
        out = {}
        for c in np.unique(g):
            if int(c) in bg:
                continue
            m = (g == c)
            if 1 <= m.sum() <= 60:
                ys, xs = np.where(m); out[int(c)] = (ys.mean(), xs.mean())
        return out
    a, b = cen(before), cen(after); out = {}
    for c in set(a) & set(b):
        dy, dx = b[c][0] - a[c][0], b[c][1] - a[c][1]
        if abs(dy) + abs(dx) > 0.1:
            out[c] = (dy, dx)
    return out


def _perceive_avatar_live(adapter):
    """LIVE 'PERCEIVE self': issue each discrete directional action once, observe which object co-moves, and identify
    the AVATAR + its locomotion (STEER) map. Emits the avatar-regime grammar and records the steer map as a TRANSFERABLE
    mechanic (avatar_steer), so the causal-map / coverage machinery generalises to the avatar regime -- the action->self
    map is the avatar's causal map, learned once and propagated. Returns the avatar record or None (actuator regime)."""
    try:
        acts = list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions())
    except Exception:
        acts = []
    if len(acts) < 2:
        return None
    from collections import defaultdict
    probe = defaultdict(list)
    for act in acts[:6]:
        before = _perceive_grid(adapter)
        try:
            adapter.step(act)
        except Exception:
            break
        after = _perceive_grid(adapter)
        for c, (dy, dx) in _avatar_probe_moves(before, after).items():
            probe[c].append((getattr(act, "name", str(act)), dy, dx))
    av = _perceive_avatar(dict(probe))
    if av:
        _emit(adapter, "PERCEIVE  self := object(colour %d)  [BECAUSE it moves under MY directional actions: %s -- an "
              "AVATAR: the action IS my locomotion, not an actuation of an external object]"
              % (av["colour"], ", ".join("%s=%s" % (a, av["dirs"][a]) for a in sorted(av["dirs"]))))
        try:
            _record_mechanic(adapter, "avatar_steer", av["dirs"])   # TRANSFER: locomotion map carries across levels/games
        except Exception:
            pass
    return av


def _play_area(g):
    """CANONICALIZATION LAYER 1 -- play-area segmentation. Returns the bbox (r0,r1,c0,c1) of the interior INSIDE any
    frame/border. A border is an outer row/col that is >=85% a single NON-background colour (a frame line); the
    background margin is NOT a border. Peels such lines from all four sides. Coordinates stay in the ORIGINAL grid so
    clicks are unaffected -- this only tells perception WHERE the playable region is, so a border/scale change between
    levels doesn't shift what the system sees. Everything downstream works in play-area terms -> scale/border invariance."""
    g = np.asarray(g); H, W = g.shape
    bg = int(np.bincount(g.ravel()).argmax())
    r0, r1, c0, c1 = 0, H - 1, 0, W - 1

    def _frame(line):
        vals, cnts = np.unique(line, return_counts=True)
        return int(vals[cnts.argmax()]) != bg and int(cnts.max()) >= 0.85 * len(line)

    changed = True; guard = 0
    while changed and (r1 - r0) > 8 and (c1 - c0) > 8 and guard < 40:
        changed = False; guard += 1
        if _frame(g[r0, c0:c1 + 1]): r0 += 1; changed = True
        if _frame(g[r1, c0:c1 + 1]): r1 -= 1; changed = True
        if _frame(g[r0:r1 + 1, c0]): c0 += 1; changed = True
        if _frame(g[r0:r1 + 1, c1]): c1 -= 1; changed = True
    return (r0, r1, c0, c1)


def _distinct_objects(g, max_frac=0.45):
    """Per-COLOUR connected components as candidate objects, restricted to the PLAY AREA (frame/border excluded). Each
    colour is segmented separately, so foreground blocks that share the dominant colour are still found. The play-area
    restriction means a coloured frame is never mistaken for an object or for background -- giving border/scale
    invariance: perception sees the same objects whether or not the level is bordered or resized. Excludes play-area
    background fill (>max_frac) and single-cell noise. Centroids stay in ORIGINAL coordinates (clicks unaffected)."""
    from collections import deque
    g = np.asarray(g); H, W = g.shape
    r0, r1, c0, c1 = _play_area(g)
    pa_area = max(1, (r1 - r0 + 1) * (c1 - c0 + 1))
    objs = []
    for col in [int(c) for c in np.unique(g[r0:r1 + 1, c0:c1 + 1])]:
        mask = (g == col)
        if int(mask[r0:r1 + 1, c0:c1 + 1].sum()) > max_frac * pa_area:   # play-area background fill -> not an object
            continue
        seen = np.zeros((H, W), bool)
        for (r, c) in np.argwhere(mask):
            if r < r0 or r > r1 or c < c0 or c > c1 or seen[r, c]:
                continue
            q = deque([(int(r), int(c))]); seen[r, c] = True; cells = []
            while q:
                y, x = q.popleft(); cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if r0 <= yy <= r1 and c0 <= xx <= c1 and not seen[yy, xx] and g[yy, xx] == col:
                        seen[yy, xx] = True; q.append((yy, xx))
            if len(cells) < 2:
                continue
            ys = [p[0] for p in cells]; xs = [p[1] for p in cells]
            objs.append({"centroid": (sum(ys) / len(ys), sum(xs) / len(xs)), "colour": col,
                         "size": len(cells), "cells": set(cells)})
    return objs


def _classify_change(before, after, obj):
    """What did clicking `obj` do? self_toggle (the clicked object changed = a button), remote_effect (something ELSE
    changed = a control/trigger), mixed_effect, or none. This is the affordance the interaction probe induces."""
    b, a = np.asarray(before), np.asarray(after)
    diff = _real_diff(b, a)
    if not diff.any():
        return "none"
    changed = set(map(tuple, np.argwhere(diff)))
    ocells = obj.get("cells", set())
    on_obj = len(changed & ocells); off_obj = len(changed - ocells)
    if on_obj and not off_obj:
        return "self_toggle"
    if off_obj and not on_obj:
        return "remote_effect"
    return "mixed_effect"


def _obj_descriptor(obj, H, W):
    """COLOUR-AGNOSTIC identity of an object. Colours are remapped/randomised across frames and games, so an
    affordance can NEVER be keyed by colour -- only by SHAPE + SIZE + relative POSITION. Coarse buckets so the same
    trigger re-identifies across frames despite jitter. This is what lets a discovered trigger persist and be reused
    even when its colour changes."""
    cr, cc = obj.get("centroid", (0, 0)); sz = obj.get("size", 0)
    sizeb = 0 if sz <= 4 else 1 if sz <= 12 else 2 if sz <= 40 else 3
    rb = int(cr / max(1, H) * 6); cb = int(cc / max(1, W) * 6)
    cells = obj.get("cells") or set()
    if cells:
        rs = [p[0] for p in cells]; xs = [p[1] for p in cells]
        h = max(rs) - min(rs) + 1; w = max(xs) - min(xs) + 1
        aspect = 0 if h > w * 1.5 else (2 if w > h * 1.5 else 1)
    else:
        aspect = 1
    return (sizeb, rb, cb, aspect)


def _affordances(adapter):
    """The persistent, GROWING trigger store, living on the environment session (like the spatial map). Records what
    each colour-agnostic object descriptor DID when clicked, so the agent accumulates a reusable, updatable body of
    interaction knowledge instead of re-discovering it every session. Frame-only; survives resets and levels."""
    st = getattr(adapter, "_affordances", None)
    if st is None:
        st = adapter._affordances = {}
    return st


def _record_affordance(adapter, descriptor, effect):
    """Record/UPDATE one discovered interaction under its colour-agnostic descriptor. Accumulates hit/react counts and
    keeps the strongest observed effect + reward, so repeated observation strengthens confidence and NEW triggers are
    simply added. This is the space the agent keeps, reuses, updates, and grows."""
    st = _affordances(adapter)
    e = st.get(descriptor)
    if e is None:
        e = st[descriptor] = {"effect": "none", "change_cells": 0, "reward": 0.0, "hits": 0, "reacts": 0}
    e["hits"] += 1
    if effect.get("changed"):
        e["reacts"] += 1
    e["change_cells"] = max(e["change_cells"], int(effect.get("change_cells", 0)))
    e["reward"] = max(e["reward"], float(effect.get("reward", 0) or 0))
    k = effect.get("change_kind")
    if k and k != "none":
        e["effect"] = k
    return e


def _probe_interactions(adapter, budget=48):
    """INTERACTION EXPLORATION -- the first step of exploration whenever a CLICK is available. When there is no avatar
    and no movement actions (an 'inert' world), the agent still has one affordance: clicking. So it explores by
    INTERACTION -- click each distinct object and observe the environment's reaction -- exactly as an avatar explores
    space by moving. This discovers which objects are clickable TRIGGERS/BUTTONS/CONTROLS and what each does, instead
    of treating click as a last-resort flail. No resets (globally disabled); stops on reward/GAME_OVER.

    Returns [{'click':(r,c),'object_colour':int,'changed':bool,'change_cells':int,'change_kind':str,'reward':float}]."""
    located = list(adapter.pointer_actions()) if hasattr(adapter, "pointer_actions") else []
    if not located:
        return []
    clickA = located[0]
    g0 = _perceive_grid(adapter); H, W = g0.shape
    objects = _distinct_objects(g0)
    store = _affordances(adapter)
    # Order candidates so the AGENT probes intelligently, not blindly:
    #   (1) objects whose colour-agnostic descriptor is a KNOWN reactive trigger (reuse accumulated knowledge first),
    #   (2) remaining objects SMALLEST-first (small distinct objects are far more likely to be buttons/triggers than
    #       big background fills -- and hitting the actual objects is the point; you saw no object interaction because
    #       big-region centroids were being clicked),
    #   (3) a coarse grid to cover regions segmentation missed.
    def _known(o):
        e = store.get(_obj_descriptor(o, H, W))
        return (e or {}).get("reacts", 0) > 0
    objects_sorted = sorted(objects, key=lambda o: (0 if _known(o) else 1, o.get("size", 0)))
    cands = [(int(round(o["centroid"][0])), int(round(o["centroid"][1])), o) for o in objects_sorted]
    step_r = max(3, H // 9); step_c = max(3, W // 9)
    for rr in range(step_r // 2, H, step_r):
        for cc in range(step_c // 2, W, step_c):
            if all(abs(rr - r0) + abs(cc - c0) > 3 for (r0, c0, _o) in cands):
                cands.append((rr, cc, {"centroid": (rr, cc), "size": 1, "cells": {(rr, cc)}}))
    base = getattr(adapter, "_lvlbase", 0)
    out = []; spent = 0
    for (cr, cc, obj) in cands:
        if spent >= budget:
            break
        before = _perceive_grid(adapter)
        _, rew, dn, _ = _apply(adapter, (clickA, cr, cc)); spent += 1
        after = _perceive_grid(adapter)
        diff = np.argwhere(_real_diff(before, after))
        changed = int(len(diff))
        ch_cen = (float(diff[:, 0].mean()), float(diff[:, 1].mean())) if changed else None
        eff = {"click": (cr, cc), "changed": changed > 0, "change_cells": changed, "change_centroid": ch_cen,
               "change_kind": _classify_change(before, after, obj) if changed else "none", "reward": rew}
        _record_affordance(adapter, _obj_descriptor(obj, H, W), eff)   # RECORD to the persistent, growing store
        out.append(eff)
        if rew > 0 or (getattr(adapter._obs, "levels_completed", 0) or 0) > base:
            break
        if dn:                                                  # GAME_OVER: stop (resets are disabled)
            break
    return out


def explore_and_map(adapter, budget=120):
    """EXPLORE-FIRST, coverage-driven. Exploration = COVER the reachable grid and COLLIDE with every object and
    wall so the environment reveals its interactions -- not fidget locally. Two phases:
      (1) BOOTSTRAP: cycle the action space briefly to learn the action->shift map + identify the controllable.
      (2) COVERAGE SWEEP: using the learned map, drive the controllable toward a target set = every object
          centroid (collide with objects) + grid corners/edges + unvisited frontier cells (cover the space),
          recording every transition. Collisions (controllable fails to move as predicted) ARE the interaction
          data. Click games get a systematic board-spanning click sweep instead.
    Builds an agency-report-compatible world model so abduce skips the reset-anchored probe. NO reset-per-probe."""
    import numpy as _np
    from effect_classifier import ActionEffectClassifier, DiscoveryController
    try:
        from transition_induction import WorldModel
        tie = WorldModel()                         # pixel + logical + object inducers, fed UNCONDITIONALLY below
    except Exception:
        tie = None
    try:
        from object_seg import segment_objects as _seg
    except Exception:
        _seg = None
    clf = ActionEffectClassifier()
    # LEVEL PROGRESSION: on level>=1 the game auto-advanced to a fresh frame after the win; do NOT reset it
    # away -- perceive the current frame and solve it. Only level 0 (or a genuine game-over) resets.
    if getattr(adapter, "level_local", False) and getattr(adapter, "_obs", None) is not None:
        g = _perceive_grid(adapter)
    else:
        g = _np.asarray(adapter.reset())
    frames = [g]; actions_taken = []
    disc = list(adapter.discrete_actions())
    can_click = bool(adapter.pointer_actions())
    # INTERACTION EXPLORATION (FIRST STEP): when a CLICK is available, probe each object to discover clickable
    # triggers/buttons/controls -- the interaction analogue of an avatar exploring space by moving. Given MORE budget
    # when there are NO movement actions (an inert/click-only world, where this IS the exploration, not a supplement).
    # This is what lets the agent solve games with no avatar. Frame-only; no resets (globally disabled).
    interaction_probe = []
    if can_click:
        try:
            # MINIMAL recon: the objective-first INTERLEAVED solve does its own discovery (and now, with the HUD
            # counter excluded, its bound-mapping actually saturates). A large blind probe just fires irreversible
            # controls before the solve gets a clean shot -- the direct test solved from a fresh state in 17 actions.
            _ib = 3 if not disc else 6
            interaction_probe = _probe_interactions(adapter, budget=min(_ib, budget))
            g = _perceive_grid(adapter)       # re-sync the working frame after the probe's clicks
            frames.append(g)
        except Exception:
            interaction_probe = []
    H, W = g.shape
    # CROSS-RESET MEMORY: the spatial map persists across resets AND across validate() calls -- a reset is a TIME
    # boundary, not a knowledge boundary. The store lives on the ADAPTER instance (the current environment session),
    # keyed by NOTHING game-identifying -- it is just "the world I am currently interacting with". Frame-only: no
    # game-id, so this transfers to every game unchanged. The map is invalidated below if the board geometry differs.
    if not hasattr(adapter, "_map_mem"):
        adapter._map_mem = {}
    _mem = adapter._map_mem
    # invalidate a stale map: if the current start frame's non-bg structure differs a lot from the remembered one,
    # this is a different world (new level geometry) -> re-map rather than carry forward stale cells.
    _bgc0 = int(_np.bincount(g.ravel()).argmax())
    _sig0 = int((g != _bgc0).sum())
    if _mem.get("board_sig") is not None and abs(_mem["board_sig"] - _sig0) > max(20, 0.3 * _sig0):
        _mem = {}
    visited = set(_mem.get("visited") or ())
    status = dict(_mem.get("status") or {})    # cell -> passable|wall|object_block|object_pass (persisted)
    world_off = [0, 0]; world_visited = set(); scrolls = 0; scroll_tests = 0   # world-map stub (window hypothesis)
    _term = "n/a"              # exploration termination reason: saturated | cap-hit | epoch-safety | n/a
    interactions = []          # DEFERRED interaction log: collisions/changes recorded but NOT acted on until
                               # the reachable space is fully covered (then the composer switches to probe/test)
    step = 0

    def _obs_step(a, key):
        nonlocal step
        before = _perceive_grid(adapter)
        try:
            _, _, done, info = adapter.step(a)
        except Exception:
            return None, True, "ERR"
        state = (info or {}).get("state", "")
        after = _perceive_grid(adapter)
        try: clf.observe(before, after, key)
        except Exception: pass
        if tie is not None:
            try: tie.observe(before, key, after)       # UNCONDITIONAL induction: every transition, not gated
            except Exception: pass
        frames.append(_np.asarray(after)); actions_taken.append(key); step += 1
        return _np.asarray(after), done, state

    # ---- (1) BOOTSTRAP: learn the action->shift map -------------------------------------------------
    boot = min(len(disc) * 3, 18) if disc else 0
    for i in range(boot):
        _, done, _ = _obs_step(disc[i % len(disc)], disc[i % len(disc)])
        if done: adapter.reset()
    dc = DiscoveryController(clf)
    try: amap = dc.robust_action_map(frames, actions_taken) or {}
    except Exception: amap = (clf.classify_game().get("move_actions") or {})
    ctrl_color = getattr(dc, "obj_color", None)
    # The planner's notion of "what do I control" comes from DiscoveryController, a separate object system that here
    # returns None while footprint.self_signature() derives [9,12] cleanly from the same transitions. Two systems
    # answer the one question and the empty one feeds the planner. Ask the one that earned an answer. self_signature
    # derives the body from confirmed TRANSLATE under my own directional actions -- nothing handed in.
    if ctrl_color is None:
        try:
            import footprint as _FPc
            _oti_c = getattr(adapter, "_obj_inducer", None)
            if _oti_c is not None:
                _ss, _ssup = _FPc.self_signature(_oti_c)
                if _ss:
                    ctrl_color = sorted(_ss)[-1] if len(_ss) > 1 else next(iter(_ss))
                    _emit(adapter, "CONTROL  what I steer := %s (support %d) -- from the object whose confirmed law is "
                                   "TRANSLATE under my directional actions. DiscoveryController had no answer; this is "
                                   "the same question asked of the system that earned one" % (sorted(_ss), _ssup),
                          once_key="control_from_footprint")
        except Exception:
            pass
    # RESUME the action-effect map + controllable from memory (cumulative): a fresh 76-action life re-learns little,
    # so carry forward what we already know and only fill gaps.
    if _mem.get("amap"):
        for _k, _v in _mem["amap"].items():
            amap.setdefault(_k, _v)
    if ctrl_color is None:
        ctrl_color = _mem.get("ctrl_color")
    # ROTATION-AWARE ACTION CLASSIFIER: an action that changes the controllable piece's ORIENTATION (the tip->body
    # direction swings) is a ROTATE, not a translation -- even though the tip centroid SHIFTS, which robust_action_map
    # misreads as a translation vector. Detect via the angle of (tip_centroid - body_centroid): rotation swings it;
    # translation leaves it fixed. This is the fix for cn04 "spinning" instead of connecting -- the move-map was a lie.
    import math as _math
    rotate_actions = set()
    try:
        def _tipdir(g):
            g = _np.asarray(g); bg = int(_np.bincount(g.ravel()).argmax())
            tip = _np.argwhere(g == ctrl_color)
            body = _np.argwhere((g != bg) & (g != ctrl_color))
            if len(tip) < 1 or len(body) < 1:
                return None
            return _math.degrees(_math.atan2(tip[:, 0].mean() - body[:, 0].mean(),
                                             tip[:, 1].mean() - body[:, 1].mean()))
        per = {}
        for i in range(1, len(frames)):
            a = actions_taken[i - 1] if (i - 1) < len(actions_taken) else None
            if a is None:
                continue
            ab = _tipdir(frames[i - 1]); aa = _tipdir(frames[i])
            if ab is None or aa is None:
                continue
            dd = abs(aa - ab); dd = min(dd, 360 - dd)
            per.setdefault(a, []).append(dd)
        for a, ds in per.items():
            if len(ds) >= 3 and (sum(1 for x in ds if x > 45) / len(ds)) >= 0.4:
                rotate_actions.add(a)                          # this action swings the orientation => a ROTATE
    except Exception:
        pass
    # rotational REGIME: the controllable is reoriented (not translated) by its actions -> A* translation nav is a
    # phantom; pursuit must search the ROTATION space (cycle orientations to align tips) instead.
    rotational = bool(rotate_actions) and len(rotate_actions) >= max(1, len(amap or {}) // 2)
    # MIXED regime (cn04): a DEDICATED rotate action (e.g. ACTION5) alongside translate actions. Remove rotate
    # actions from the TRANSLATION move-map so A* nav uses only true translations; they stay available to the
    # pursuit as orientation-alignment moves (rotate-when-translation-stalls). This stops A* misrouting a spin.
    for _ra in list(rotate_actions):
        if amap and _ra in amap:
            amap.pop(_ra, None)
    # (translate/rotate calibration on the ISOLATED controllable is done below, once co_moving is known)
    # EARLY YIELD: a reorient/assembly game does not need full spatial COVERAGE -- once the action-effects and the
    # controllable are known (bootstrap) and the pieces are perceivable, pursuit should begin. Cap exploration so the
    # ~76-step clock is RESERVED for pursuit; the persisted map + explore<->pursue loop fill any gaps later. Gated on
    # MEASURED rotation (frame-only), not game identity, so it generalises to any reorient game.
    if rotate_actions:
        budget = min(budget, 60)

    def _centroid(color):
        gf = _perceive_grid(adapter)
        cells = _np.argwhere(gf == color)
        return (float(cells[:, 0].mean()), float(cells[:, 1].mean())) if len(cells) else None

    def _best_action(cur, tgt):
        """action whose shift most reduces Manhattan distance to tgt (uses the LEARNED map)."""
        best_a, best_d = None, abs(cur[0]-tgt[0]) + abs(cur[1]-tgt[1])
        for a, (dr, dc) in amap.items():
            nd = abs(cur[0]+dr-tgt[0]) + abs(cur[1]+dc-tgt[1])
            if nd < best_d:
                best_d, best_a = nd, a
        return best_a

    # ---- (2a) NOVELTY-DRIVEN COVERAGE for navigable games ------------------------------------------
    # The explorer is REWARDED for reaching UNVISITED cells (count-based novelty bonus): each step it takes the
    # action leading to the least-visited cell, so it seeks the frontier and never oscillates/retraces. When
    # locally boxed in (all neighbours visited) it jumps toward the nearest unvisited frontier. Collisions and
    # changes are LOGGED but NOT acted on. It stops when the reachable space SATURATES (no new cell for a while)
    # -- "full current-map understanding" -- at which point the composer switches to probe/test/abduce.
    if amap and ctrl_color is not None:
        from collections import Counter as _Ctr
        import random as _rng
        _rng.seed(0)
        visit = _Ctr(_mem.get("visit") or {}); blocked = set(); status = dict(_mem.get("status") or {})
        hazards = set(map(tuple, _mem.get("hazards") or ())); death_count = dict(_mem.get("death_count") or {})
        for _c in visited:
            visit[_c] += 0                         # ensure known cells register (seeded map -> resume, don't re-cover)
        # WORLD-MAP STUB (the "64x64 may be a window into a larger world" hypothesis, held live in reasoning):
        # track the avatar in WORLD coordinates = viewport cell + accumulated scroll offset. At a frame EDGE the
        # explorer PUSHES to test whether the whole frame TRANSLATES (a viewport scroll -> world extends beyond the
        # window) vs stays put (a true world boundary). On cn04 (non-scrolling) this correctly finds no scroll; the
        # machinery is exercised and fires for real if a scrolling game appears.

        def _detect_scroll(before, after, shift):
            b = _np.asarray(before); a = _np.asarray(after)
            if b.shape != a.shape:
                return None
            dr, dc = int(round(shift[0])), int(round(shift[1]))
            if dr == 0 and dc == 0:
                return None
            H2, W2 = b.shape
            rolled = _np.roll(a, shift=(-dr, -dc), axis=(0, 1))     # world scrolled by shift? then roll-back matches
            r0, r1 = max(0, dr), H2 + min(0, dr); c0, c1 = max(0, dc), W2 + min(0, dc)
            if r1 - r0 < 3 or c1 - c0 < 3:
                return None
            overlap = (rolled[r0:r1, c0:c1] == b[r0:r1, c0:c1]).mean()
            static = (a == b).mean()                               # a static-frame move changes only a few cells
            return (dr, dc) if (overlap > 0.92 and static < 0.85) else None

        def _in(c):
            return 0 <= c[0] < H and 0 <= c[1] < W

        def _content(cell):
            gf = _perceive_grid(adapter)
            if not _in(cell):
                return "oob"
            v = int(gf[cell[0], cell[1]]); bgv = int(_np.bincount(gf.ravel()).argmax())
            return "empty" if v == bgv else ("self" if v == ctrl_color else "object")

        def _reachable_unknown(cur):
            # nearest cell across the FULL 64x64 grid we have not yet classified, reachable-ish from a visited cell
            best, bd = None, 1e18
            for (vr, vc) in list(visited):
                for a, (dr, dc) in amap.items():
                    if ((vr, vc), str(a)) in blocked:
                        continue
                    nn = (vr + int(round(dr)), vc + int(round(dc)))
                    if nn not in status and nn not in hazards and _in(nn):
                        d = abs(nn[0]-cur[0]) + abs(nn[1]-cur[1])
                        if d < bd:
                            bd, best = d, nn
            return best

        def _plan_first_action(cur):
            # BFS through KNOWN-PASSABLE cells (avoiding walls/hazards/blocked edges) to the nearest cell that has
            # an UNKNOWN neighbour; return the first action of that route. Path-planned coverage -> reaches every
            # reachable frontier instead of walking greedily into walls.
            from collections import deque as _dq
            start = (int(round(cur[0])), int(round(cur[1])))
            prev = {start: None}; q = _dq([start]); goal = None
            while q:
                c = q.popleft()
                for a, (dr, dc) in amap.items():                 # frontier = adjacent to an unknown non-hazard cell
                    nn = (c[0]+int(round(dr)), c[1]+int(round(dc)))
                    if _in(nn) and nn not in status and nn not in hazards and (c, str(a)) not in blocked:
                        goal = c; break
                if goal is not None:
                    break
                for a, (dr, dc) in amap.items():                 # expand through known-passable neighbours
                    nn = (c[0]+int(round(dr)), c[1]+int(round(dc)))
                    if nn in prev or not _in(nn) or nn in hazards or (c, str(a)) in blocked:
                        continue
                    if status.get(nn) == "passable" or nn in visit:
                        prev[nn] = (c, a); q.append(nn)
            if goal is None:
                return None
            step_c = goal
            while prev.get(step_c) is not None and prev[step_c][0] != start:
                step_c = prev[step_c][0]
            return prev[step_c][1] if prev.get(step_c) is not None else None

        def _epoch():
            nonlocal scrolls, scroll_tests                 # rebound (+=) inside this nested fn -> must be nonlocal
            new_cells = 0; sat = 0; region_visits = _Ctr()
            all_regions = [(rr, cc) for rr in range(0, H, 8) for cc in range(0, W, 8)]   # coarse 8x8 grid over 64x64
            while step < budget and sat < 22:
                cur = _centroid(ctrl_color)
                if cur is None:
                    break
                cell = (int(round(cur[0])), int(round(cur[1])))
                if cell not in visit:
                    new_cells += 1
                visit[cell] += 1; visited.add(cell); status[cell] = "passable"
                region_visits[(cell[0] // 8, cell[1] // 8)] += 1
                cands = [(a, s) for a, s in amap.items()
                         if (cell, str(a)) not in blocked
                         and (cell[0]+int(round(s[0])), cell[1]+int(round(s[1]))) not in hazards
                         and _in((cell[0]+int(round(s[0])), cell[1]+int(round(s[1])))) ]
                # GLOBAL TREK: periodically head to the least-visited coarse region so coverage spans the WHOLE grid
                # (the frame is mostly traversable, so don't puddle locally -- deliberately walk the far regions).
                trek = None
                if step % 10 == 0:
                    lr = min(all_regions, key=lambda r: (region_visits[(r[0]//8, r[1]//8)], _rng.random()))
                    trek = (lr[0] + 4, lr[1] + 4)
                if trek is not None and abs(trek[0]-cell[0]) + abs(trek[1]-cell[1]) > 6:
                    best_a = _best_action(cur, trek) or (cands[0][0] if cands else None)
                    if best_a is None:
                        ba = _plan_first_action(cur)
                        if ba is None:
                            break
                        best_a = ba
                elif not cands:                            # boxed in -> PATH-PLAN through known space to a frontier
                    ba = _plan_first_action(cur)
                    if ba is None:
                        break                              # no reachable unknown frontier -> space truly covered
                    best_a = ba
                else:
                    _rng.shuffle(cands)                    # NOVELTY: least-visited destination, random tiebreak
                    best_a = min(cands, key=lambda ad: visit[(cell[0]+int(round(ad[1][0])), cell[1]+int(round(ad[1][1])))])[0]
                sh = amap[best_a]; tcell = (cell[0]+int(round(sh[0])), cell[1]+int(round(sh[1])))
                cwas = _content(tcell)
                before = _perceive_grid(adapter)
                after, done, dstate = _obs_step(best_a, best_a)
                if dstate == "GAME_OVER":                  # DEATH IS DATA, not a wall. GAME_OVER is often GLOBAL
                    death_count[tcell] = death_count.get(tcell, 0) + 1   # (step/time/rule limit), not this cell being
                    interactions.append(dict(step=step, kind="death", at=list(tcell),  # deadly -- so DON'T wall it off
                                             note=f"GAME_OVER here (death #{death_count[tcell]}); logged, still exploring"))
                    if death_count[tcell] >= 3:            # only a REPEATABLE death at the SAME cell -> positional hazard
                        hazards.add(tcell); status[tcell] = "hazard"
                    adapter.reset()                        # position resets to start, but the MAP persists in memory
                    # FAST-FORWARD RESUME (the reset is a TIME boundary, not a knowledge boundary): don't re-explore
                    # known territory. Replay the shortest KNOWN path back to the exploration frontier -- compress the
                    # action cost of "getting back to where we left off" -- then resume exploring the UNKNOWN with the
                    # remaining clock. This is what turns a 76-action re-explore into a ~10-action fast-forward.
                    for _ff in range(40):
                        if step >= budget:
                            break
                        cur2 = _centroid(ctrl_color)
                        if cur2 is None:
                            break
                        c2 = (int(round(cur2[0])), int(round(cur2[1])))
                        nbrs = [(c2[0] + int(round(s[0])), c2[1] + int(round(s[1]))) for a, s in amap.items()]
                        if any((n not in visited) and _in(n) and (n not in hazards) for n in nbrs):
                            break                          # reached a frontier (an unvisited reachable neighbour)
                        ba = _plan_first_action(cur2)      # BFS over the KNOWN passability map toward the frontier
                        if ba is None:
                            break
                        _a2, _d2, _ds2 = _obs_step(ba, ba)
                        if _ds2 == "GAME_OVER":
                            adapter.reset(); break         # clock hit again mid-replay: restart the fast-forward next loop
                    continue
                nc_ = _centroid(ctrl_color)
                moved = nc_ is not None and (int(round(nc_[0])), int(round(nc_[1]))) != cell
                # WORLD-MAP: at a frame EDGE, test whether pushing scrolled the whole world (window into a bigger map)
                at_edge = (cell[0] <= 2 or cell[0] >= H-3 or cell[1] <= 2 or cell[1] >= W-3)
                pushing_out = (cell[0]+int(round(sh[0])) < 0 or cell[0]+int(round(sh[0])) >= H or
                               cell[1]+int(round(sh[1])) < 0 or cell[1]+int(round(sh[1])) >= W) or at_edge
                if at_edge and pushing_out:
                    scroll_tests += 1
                    sc = _detect_scroll(before, after, sh)
                    if sc is not None:                     # VIEWPORT SCROLL: the world extends beyond the window
                        world_off[0] -= sc[0]; world_off[1] -= sc[1]; scrolls += 1
                        interactions.append(dict(step=step, kind="viewport_scroll", shift=list(sc),
                                                 note="frame translated -> world extends beyond the 64x64 window"))
                        sat = 0                            # new world frontier opened -> keep exploring
                world_visited.add((cell[0] + world_off[0], cell[1] + world_off[1]))
                if not moved:
                    blocked.add((cell, str(best_a)))
                    if cwas == "object":                   # DON'T assume: an object that blocked me (noted, not acted on)
                        status[tcell] = "object_block"
                        interactions.append(dict(step=step, kind="object_blocks", at=list(tcell), note="object here, blocked movement"))
                    else:
                        status[tcell] = "wall"
                        interactions.append(dict(step=step, kind="boundary", at=list(tcell), note="boundary/wall, cannot cross"))
                    sat += 1
                else:
                    nc = (int(round(nc_[0])), int(round(nc_[1])))
                    if cwas == "object":                   # entered a cell that had an object -> it's passable (overlap)
                        status[nc] = "object_pass"
                        interactions.append(dict(step=step, kind="object_overlap", at=list(nc), note="object here, moved through (passable)"))
                    try:
                        b = _np.asarray(before); af = _np.asarray(after)
                        if any(b[r, c] != ctrl_color and af[r, c] != ctrl_color for (r, c) in _np.argwhere(b != af)):
                            interactions.append(dict(step=step, kind="change", at=list(cell), note="environment changed"))
                    except Exception:
                        pass
                    sat = 0 if nc not in visit else sat + 1
                if done:
                    adapter.reset()
            return new_cells

        # GATED RE-EXPLORATION: run until SATURATION -- "I've reached everything my avatar has ungated access to."
        # Saturated = two consecutive epochs find NO new cell, with a gate re-test in between (so a genuinely
        # opened gate still counts as progress and resumes). The budget is a worst-case ceiling ONLY.
        _ep = 0; _stall = 0
        while step < budget:
            got = _epoch(); _ep += 1
            if step >= budget:
                _term = "cap-hit"; break
            if got == 0:
                _stall += 1
                if _stall >= 2:                             # no new reachable space, even after re-testing gates
                    _term = "saturated"; break
                blocked.clear()                             # re-test gated edges once, then confirm with one epoch
            else:
                _stall = 0                                  # made progress -> keep exploring
            if _ep >= 60:
                _term = "epoch-safety"; break
    # ---- (2b) systematic CLICK SWEEP for click games -----------------------------------------------
    elif can_click:
        rows = max(4, min(10, H // 6)); cols = max(4, min(10, W // 6))
        for ri in range(rows):
            for ci in range(cols):
                if step >= budget:
                    break
                r = int((ri + 0.5) * H / rows); c = int((ci + 0.5) * W / cols)
                _, done, _ = _obs_step(("click", c, r), "click")
                if done: adapter.reset()
    else:
        for i in range(min(budget, 24)):
            if not disc: break
            _, done, _ = _obs_step(disc[i % len(disc)], disc[i % len(disc)])
            if done: adapter.reset()

    game = clf.classify_game()
    if not amap:
        try: amap = dc.robust_action_map(frames, actions_taken) or game.get("move_actions") or {}
        except Exception: amap = game.get("move_actions") or {}
    if not isinstance(amap, dict):                              # game.get('move_actions') can be a bool flag
        amap = {}
    ctrl_color = ctrl_color if ctrl_color is not None else getattr(dc, "obj_color", None)
    gf = _perceive_grid(adapter)
    locus = None
    if ctrl_color is not None:
        cells = _np.argwhere(gf == ctrl_color)
        if len(cells):
            locus = tuple(_np.round(cells.mean(0), 1).tolist())
    modality = "translate" if amap else (game.get("family") or "inert")
    # CO-MOVING BODY (cn04 fix): colours whose centroid shifts WITH the controllable's move-actions are part of the
    # SAME rigid body (e.g. white_U + red_feet), NOT targets. Exclude them so abduction targets the STATIONARY
    # object (the frame/container), not a part of the controllable itself. (This is the replay's fatal gap: the
    # agent was chasing color 0, which moves with the controllable.) Populates the report's exclude_markers, which
    # abduce already uses to drop sprite colours that "move WITH the avatar".
    co_moving = set()
    try:
        gf0 = _perceive_grid(adapter)
        bg0 = int(_np.bincount(gf0.ravel()).argmax())
        move_keys = set((amap or {}).keys())
        ncols = [int(c) for c in _np.unique(_np.asarray(frames[0])) if int(c) != bg0]
        seen = {c: 0 for c in ncols}; moved = {c: 0 for c in ncols}
        for i in range(1, len(frames)):
            a = actions_taken[i - 1] if (i - 1) < len(actions_taken) else None
            if a not in move_keys:                              # only movement actions witness co-motion
                continue
            b = _np.asarray(frames[i - 1]); af = _np.asarray(frames[i])
            if b.shape != af.shape:
                continue
            for c in ncols:
                cb = _np.argwhere(b == c); ca = _np.argwhere(af == c)
                if len(cb) and len(ca):
                    seen[c] += 1
                    if abs(ca[:, 0].mean() - cb[:, 0].mean()) + abs(ca[:, 1].mean() - cb[:, 1].mean()) > 0.5:
                        moved[c] += 1
        for c in ncols:
            if c == ctrl_color:
                continue
            if seen[c] >= 4 and moved[c] / max(1, seen[c]) >= 0.5:   # moves with the controllable most of the time
                co_moving.add(int(c))
    except Exception:
        pass
    # CALIBRATE the action model on the ISOLATED controllable (seeded from the co-moving body, so it's the one
    # piece, not both). TRANSLATE: real per-action centroid shift (median). ROTATE: fit the actual rigid transform
    # (90 CW/CCW + translation) from real before/after -- the bbox rotation was catastrophically wrong (P0). Both
    # measured on the isolated piece; polluted two-piece measurements are what gave the doubled translate + un-fit
    # rotation. Stored in rotate_model for the forward model to use.
    rotate_model = {}
    if ctrl_color is not None:
        _cco = sorted(co_moving) if co_moving else []
        def _cc2(gg):
            comp = _ctrl_component(np.asarray(gg), ctrl_color, _cco)
            if not comp:
                return None, None
            ys = [c[0] for c in comp]; xs = [c[1] for c in comp]
            return (sum(ys) / len(ys), sum(xs) / len(xs)), set(comp)
        _ract = set(str(a) for a in rotate_actions)
        for _a in list((amap or {}).keys()):                      # TRANSLATE calibration (isolated)
            drs = []; dcs = []
            for _i in range(1, min(len(frames), len(actions_taken) + 1)):
                if (_i - 1) < len(actions_taken) and actions_taken[_i - 1] == _a:
                    cb, _ = _cc2(frames[_i - 1]); ca, _ = _cc2(frames[_i])
                    if cb is not None and ca is not None:
                        drs.append(ca[0] - cb[0]); dcs.append(ca[1] - cb[1])
            if len(drs) >= 2:
                drs.sort(); dcs.sort(); amap[_a] = (drs[len(drs) // 2], dcs[len(dcs) // 2])
        for _ra in rotate_actions:                                # ROTATE calibration (fit rigid transform, isolated)
            fits = []
            for _i in range(1, min(len(frames), len(actions_taken) + 1)):
                if (_i - 1) < len(actions_taken) and str(actions_taken[_i - 1]) == str(_ra):
                    cb, sb = _cc2(frames[_i - 1]); ca, sa = _cc2(frames[_i])
                    if cb is None or ca is None or len(sb) < 5 or abs(len(sb) - len(sa)) > 0.3 * len(sb):
                        continue
                    for _dir in ("CW", "CCW"):
                        R = (lambda r, c: (c, -r)) if _dir == "CW" else (lambda r, c: (-c, r))
                        Rcb = R(*cb); t = (ca[0] - Rcb[0], ca[1] - Rcb[1])
                        pred = set((int(round(R(r, c)[0] + t[0])), int(round(R(r, c)[1] + t[1]))) for (r, c) in sb)
                        fits.append((len(pred & sa) / max(1, len(sa)), _dir, t))
            if fits:
                fits.sort(reverse=True)
                if fits[0][0] >= 0.7:                          # ONLY use a learned rotate that actually fits (>=70%);
                    rotate_model[str(_ra)] = (fits[0][1], fits[0][2])   # a poor fit is worse than the bbox fallback
    # P3: on a genuine MULTI-piece board (3+), actively induce which CLICK selects which piece (grounds the
    # assembler's selection). Skipped on 1-2 piece boards where the controllable is already selected.
    selection_probe = []
    try:
        _loc = list(adapter.pointer_actions())
        _pcs = _seg_pieces(_perceive_grid(adapter), ctrl_color)
        _mv = next((a for a in (amap or {}).keys()), None)
        if _loc and _mv is not None and len(_pcs) >= 3:
            selection_probe = _probe_selection(adapter, ctrl_color, _loc, _mv, max_probes=4)
    except Exception:
        selection_probe = []
    report = dict(modality=modality, marker_color=ctrl_color, shifts=amap, rotate_model=rotate_model,
                  selection_probe=selection_probe, interaction_probe=interaction_probe,
                  affordances=dict(_affordances(adapter)), causal_map=dict(_causal_map(adapter)),
                  locus=locus, exclude_markers=tuple(sorted(co_moving)), types={}, ambient_size=0,
                  source="explore-first", co_moving_body=sorted(co_moving),
                  rotate_actions=sorted(str(a) for a in rotate_actions), rotational=rotational)
    if rotational:                                              # a reorient regime, not a translate regime
        modality = "rotate"; report["modality"] = "rotate"
    # SEAM (C2 + C6): individuate objects/self by co-movement and recognise the game's SCHEMA (MATCH_SKILL vs the
    # ACCUMULATE special case), attaching both to the report for the planner. Guarded -- default behaviour if the
    # controllers are unwired or error. Controllers are reached via the injection registry, never imported here.
    try:
        _indiv_hook = controller_hook("individuation")
        _schema_hook = controller_hook("schema_recognizer")
        if _indiv_hook is not None and frames:
            _indiv = _indiv_hook(frames, actions_taken)
            report["individuation"] = _indiv
            if _schema_hook is not None:
                _arr = np.asarray(frames[-1]); _bgv = int(np.bincount(_arr.ravel()).argmax())
                _nclasses = len(set(int(c) for c in np.unique(_arr) if int(c) != _bgv))
                report["schema"] = _schema_hook(_indiv, _nclasses)
    except Exception:
        pass
    adapter.reset()
    try:
        from collections import Counter as _C2
        _statusc = dict(_C2(status.values()))
    except Exception:
        _statusc = {}
    # PERSIST the accumulated map on the session instance (cumulative across resets; frame-only, no game-id). The
    # board_sig lets the NEXT call detect a genuinely different world and invalidate, so this transfers to any game.
    try:
        adapter._map_mem.clear()
        adapter._map_mem.update(dict(
            visited=set(visited), status=dict(status), amap=dict(amap or {}), ctrl_color=ctrl_color,
            visit=dict(locals().get("visit", {}) or {}), board_sig=_sig0,
            hazards=[list(h) for h in (locals().get("hazards", set()) or set())],
            death_count=dict(locals().get("death_count", {}) or {}),
            co_moving=sorted(co_moving), rotate_actions=sorted(str(a) for a in rotate_actions)))
    except Exception:
        pass
    # ---- NARRATE ---------------------------------------------------------------------------------------------
    # 540 lines that build a world model and an exploration map, on every run, in total silence. By the standing
    # rule -- the debugging surface is the agent's own narration -- that is indistinguishable from not existing.
    # A whole session was spent diagnosing this agent from a stream this function was absent from, while it ran
    # underneath the entire time. Every value below was ALREADY computed and ALREADY returned; none was ever said.
    # Nothing here changes behaviour. It only stops the agent from keeping its own map a secret from itself.
    try:
        _emit(adapter, "MAP  explored %d cell(s); controllable := %s; action-map %s  [termination: %s]"
              % (len(visited), ctrl_color, ({str(k): str(v) for k, v in (amap or {}).items()} or "NONE LEARNED"), _term),
              once_key="map_%s_%d" % (_term, len(visited)))
        _walls = sum(1 for v in status.values() if str(v).startswith("wall"))
        _pass = sum(1 for v in status.values() if str(v).startswith("passable"))
        _blk = sum(1 for v in status.values() if str(v).startswith("object_block"))
        if status:
            _emit(adapter, "MAP  terrain learned by COLLIDING: %d passable, %d wall, %d object-blocked  "
                           "[this is the allocentric belief -- what the board is like, true regardless of where I stand]"
                  % (_pass, _walls, _blk), once_key="map_terrain_%d" % len(status))
        if interactions:
            _emit(adapter, "MAP  logged %d interaction(s) during the sweep  [collisions ARE the interaction data; "
                           "recorded, not acted on]" % len(interactions), once_key="map_inter_%d" % len(interactions))
        if tie is not None:
            _rep = tie.report() or {}
            _emit(adapter, "WORLD-MODEL  fidelity=%s  degenerate=%s  best=%s  [the forward model I would plan with. A "
                           "degenerate model has learned 'nothing moves' and scores near 1.0 by predicting stillness -- "
                           "so a high number here is only worth what the degenerate flag says it is]"
                  % (_rep.get("fidelity"), _rep.get("degenerate"), _rep.get("best")),
                  once_key="worldmodel_%s" % _rep.get("fidelity"))
    except Exception as _e:
        try:
            _emit(adapter, "MAP  narration failed (%s) -- the map was still built; I just cannot show it to you"
                  % type(_e).__name__)
        except Exception:
            pass
    return dict(report=report, classifier=clf, frames=frames, actions_taken=actions_taken, game=game, n_steps=step,
                controllable=ctrl_color, action_map=amap, coverage=len(visited),
                interactions=interactions, classified=_statusc, termination=_term,
                dynamics=(tie.report() if tie is not None else None), inducer=tie,
                world=dict(offset=world_off, scrolls=scrolls, scroll_tests=scroll_tests,
                           world_coverage=len(world_visited),
                           windowed=bool(scrolls > 0)))


def validate(adapter, budget=3000, max_hyps=4, descend_pass_budget=2000, belief=None, engine=None):
    """HYBRID composer (§11.267-268): abduce cue-proposed RELATION candidates, compile each to a
    discrepancy, and pursue reward through three engines in increasing action-cost order:
      PASS 1  FORWARD-DESCENT as a CHEAP, HARD-BOUNDED pass (descend_pass_budget actions TOTAL across all
              candidates). On the real harness every cross-candidate action is COUNTED, so the descend-first
              pass must live within an action budget to stay cap-viable; it captures clean directed-monotonic
              wins (lp85) for a few actions and lets everything else fall through.
      PASS 2  Go-Explore pursue per candidate -- robust but action-expensive (the fallback).
      PASS 3  INTERACTION novelty probe -- discover reward when no perceived target rewards.
    Cues propose; reward disposes; the predicate confirms binding. `engine` reports which path won. NOTE
    (§11.268): the per-candidate generate-and-test is itself action-expensive on the real harness -- the
    next composer-level lever is CANDIDATE ECONOMY (commit to a belief instead of re-trying 12 from scratch),
    the v18 BAMDP lesson."""
    _install_grammar_ride(adapter)  # every action carries the grammar since the last one (frame-data completeness)
    # PER-LEVEL BASELINE: level-completion checks in the pursuit are relative to THIS level's starting count, so a
    # game already past level 0 doesn't read every later level as pre-solved. Captured before perception/pursuit.
    adapter._lvlbase = getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0
    # EXPLORE-FIRST: map the whole environment in ONE continuous rollout (no reset-probing), THEN abduce
    # against the map. This replaces the reset-anchored agency_report (the "probe in a vacuum" reset storm)
    # with a single exploratory pass that builds the controllable + action->effect model first.
    _ride_reason(adapter, pass_name="explore", objective="map the environment first",
                 extra={"grammar": "explore continuously and build a world model before proposing objectives"})
    # Capture the level signature NOW, on the initial frame, before explore/probe mutates it -- so a level
    # re-identifies stably across attempts and the solution cache can be looked up (component 2 replay).
    try:
        adapter._level_sig = _level_signature(_perceive_grid(adapter))
    except Exception:
        adapter._level_sig = None
    _emit(adapter, "\u2550\u2550\u2550 LEVEL %d \u2550\u2550\u2550" % (getattr(adapter, "_lvlbase", 0)))
    try:                                                       # REGIME FORK: before assuming the actuator grammar, test
        if getattr(adapter, "_obs", None) is None:             # 'is one of these objects ME?' -- needs a first observation
            adapter.reset()                                    # (same first-frame acquisition explore_and_map uses)
        import regime_factory as _RF                           # REGIME FORK via the factory (one place selects the regime;
        _regime, _av = _RF.make_regime(adapter)                # shared mechanisms live in _RF.SHARED, reused by all regimes)
        if _regime is not None:                                # AVATAR regime -> the avatar solver (navigate/trigger/confirm),
            # LIFE ALLOCATION: the regime is known HERE, before an action is spent. Measured: the solve exits when the
            # IN-GAME budget bar runs out (~one life), and everything after that went to the generic descend pass --
            # which resets the game and burns the remaining lives on the explorer this comment already calls flailing.
            # Spend the lives on the solver that fits the regime. The shared spatial memory persists across them, so
            # each life RESUMES from what the last one mapped instead of relearning the maze from zero.
            import os as _os_ab
            _atries = int(_os_ab.environ.get("OURO_AVATAR_RETRIES", "6"))
            for _try in range(max(1, _atries)):               # not the actuator explorer that flails here
                _regime.solve(budget=int(_os_ab.environ.get("OURO_AVATAR_BUDGET", "2000")))
                try:                                          # NB: adapter.satisfied() is STICKY (latches on the first
                    _ob = getattr(adapter, "_obs", None)      # reward, never clears) -> useless as a stop test.
                    if "WIN" in str(getattr(_ob, "state", "") or "").upper():
                        break
                except Exception:
                    pass
                if _try >= _atries - 1:
                    break
                try:
                    _ob = getattr(adapter, "_obs", None)
                    _stnow = str(getattr(_ob, "state", "") or "").upper()
                    # RESET IS ONLY LEGAL IN GAME_OVER. Mid-game it wipes accumulated level progress back to level 0 --
                    # so never force one to start the next attempt. If the game is still running, just re-enter the
                    # solve: the budget bar refills with the life and the shared map is already carried forward.
                    if "GAME_OVER" not in _stnow:
                        _emit(adapter, "RETRY  the avatar solve is the routine that fits this regime -> re-entering it "
                              "with the shared map carried forward, rather than handing the rest of the game to the "
                              "generic pass  [attempt %d/%d]" % (_try + 2, _atries), once_key="avatar_retry_%d" % _try)
                        continue
                    _emit(adapter, "RETRY  life lost (GAME_OVER) -> RESET is legal here; spending the next life on the "
                          "avatar solve too, carrying the shared map forward  [life %d/%d]" % (_try + 2, _atries),
                          once_key="avatar_retry_%d" % _try)
                    adapter.reset()
                except Exception:
                    break
            adapter._avatar_handled = True                     # the avatar's own SpatialMap already mapped this game
            # FRAME-DOUBT RE-ABDUCTION: if the avatar solve doubted its own FRAME (objective unevaluable + a competing
            # signature present), act on it -- re-abduce toward the indicated regime instead of leaving the game in the
            # frame that could not explain it. This closes the local-doubt -> global-doubt loop: the agent's own grammar
            # signal drives a regime switch.
            if getattr(adapter, "_frame_doubt", False) and not getattr(adapter, "_reframing", False):
                _toward = getattr(adapter, "_reabduce_toward", None)
                _emit(adapter, "RE-ABDUCE  the AVATAR frame was doubted with evidence for a NON-AVATAR frame -> abandoning "
                      "it and re-abducing toward '%s'. The failed frame is dropped, not refined; the CONTAIN_FIT target "
                      "(interior slot) becomes the objective." % (_toward or "actuator"))
                adapter._reframed = _toward or "actuator"
                # NOTE: executing the re-abduced frame is deferred -- ContainFitRegime.solve currently delegates to
                # validate(), which would re-enter this flow. The re-abduction DECISION + target are made and narrated
                # here; a non-recursive ContainFitRegime.solve (composing the co-moving body + interior-slot residual
                # drive directly) is the next build. Re-entry is guarded so no recursion occurs.
    except Exception:
        _av = None
    # NO-AVATAR -> INTERACTION MODE (general): if there is no movable avatar -- either no movement actions at all, OR
    # a handful of moves that co-move nothing -- don't let explore click-flail through the whole budget hunting one.
    # Cap it to interaction recon and hand the real budget to the objective-first solve. Free for empty action spaces
    # (vc33), a handful of actions for the avatar-shaped-but-empty case.
    _expl_budget = 6 if not _has_avatar(adapter) else 500
    if getattr(adapter, "_avatar_handled", False):
        _expl_budget = 0                                       # avatar regime already mapped+solved via its own SpatialMap
    world = explore_and_map(adapter, budget=_expl_budget)   # ceiling only; real stop is saturation
    # SEAM (C1): if a REWARD fired during exploration, induce the win-predicate from the winning transition and stash
    # it on the report as an induced objective (the reward becomes supervision -- the composer discovers what winning
    # means instead of receiving it). Guarded/best-effort: the induced spec is available to downstream candidate
    # selection; producing it is the wired half, consuming it as a first-class candidate is the documented next step.
    try:
        _c1 = controller_hook("objective_induction")
        _fr = world.get("frames") or []
        if _c1 is not None and getattr(adapter, "_reward", False) and len(_fr) >= 2:
            _rep = world.get("report") or {}
            _induced = _c1(_fr, len(_fr) - 1, _rep.get("marker_color"), _rep.get("co_moving_body"))
            if _induced:
                _rep["induced_objective"] = _induced[0]; world["report"] = _rep
    except Exception:
        pass
    _ex_cycles = 0                                              # EXPLORE<->PURSUE loop (loss-signal redirect)
    while True:
        wr_ctrl = world.get("controllable"); wr_fam = (world.get("game") or {}).get("family")
        _wm = world.get("world") or {}
        _ride_reason(adapter, pass_name="abduce", objective="propose relations from the map",
                     extra={"grammar": f"explored {world.get('n_steps')} steps; covered {world.get('coverage')} cells; "
                                       f"termination={world.get('termination')}; classified {world.get('classified')}; "
                                       f"logged {len(world.get('interactions') or [])} interactions; family={wr_fam}; "
                                       f"controllable={wr_ctrl}",
                            "world_hypothesis": f"assumed the 64x64 frame may be a window into a larger world; pushed "
                                       f"{_wm.get('scroll_tests',0)} edges, detected {_wm.get('scrolls',0)} scrolls "
                                       f"(windowed={_wm.get('windowed',False)})"})
        ab = abduce(adapter, max_hyps=max_hyps, reset_first=False, prior_report=world.get("report"))
        modality, ctrl = ab["modality"], ab["controllable"]
        g0 = adapter.reset()
        if engine is not None:                       # give the engine the explored world model (residual substrate)
            try:
                engine._world = world
            except Exception:
                pass
        cands = []
        for h in ab["hypotheses"]:
            if h.get("cue") == "assembly":                     # ASSEMBLY: measure TIP OVERLAP, not centroid distance
                disc = _compile_tip_overlap(ctrl, (world.get("report") or {}).get("co_moving_body"), g0)
            elif "spec" in h:
                disc = compile_objective(h["spec"], ctrl, g0)  # COMPOSITE objective (11.284)
            else:
                disc = compile_discrepancy(h["relation"], ctrl, h["target_color"], g0)
            if disc.measure(g0) <= 0:                               # degenerate: objective trivially holds, no action
                continue
            cands.append((h, disc))
        # CANDIDATE ECONOMY (§11.268): order modality-consistent relations FIRST so the likely winner is reached
        # in few cross-candidate actions -- the cumulative cost to the winner is what the harness caps.
        prior = list(MODALITY_RELATION_PRIOR.get(modality, []))
        # CROSS-LEVEL BELIEF (§11.303): a relation confirmed on earlier levels is tried FIRST on this one.
        def _rank(hd):
            rel = hd[0]["relation"]
            b = -(belief.get(rel, 0.0)) if belief else 0.0       # higher belief -> earlier
            p = prior.index(rel) if rel in prior else len(prior) + 1
            return (b, p)
        cands.sort(key=_rank)
        # §11 SIMULATE-BEFORE-PURSUE: rank abduced objectives by simulated discrepancy-reduction (gated).
        try:
            from transition_induction import rank_objectives, RolloutScorer
            wm = world.get("inducer"); acts = list(adapter.discrete_actions())
            adapter._dynamics = world.get("dynamics")
            adapter._explore_term = world.get("termination")
            if wm is not None and acts and cands:
                cand_discs = [(h["descriptor"], disc) for (h, disc) in cands]
                rk = rank_objectives(wm, g0, cand_discs, acts, RolloutScorer(min_fidelity=0.6), ctrl=ctrl)
                adapter._sim_rank = rk
                if rk.get("trustworthy"):
                    order = {descr: i for i, (descr, _s) in enumerate(rk["ranked"])}
                    cands.sort(key=lambda hd: order.get(hd[0]["descriptor"], 1e9))
                    _ride_reason(adapter, pass_name="simulate", objective="rank objectives by simulated progress",
                                 extra={"grammar": "simulated each objective in the induced world model; pursuing the "
                                                   "one that most reduces discrepancy first (dense feedback, no real "
                                                   "actions spent)", "twins": len(rk.get("twins") or []),
                                        "flat_loss": rk.get("n_flat"), "shaped": rk.get("n_shaped")})
        except Exception:
            pass
        # C1 PRODUCER (click games): induce the objective as the SUM of ALL sub-goals present this level (arity-
        # invariant) -- any number of fill bars + any number of puck->target pairs. Level 0 = one fill; level 3 =
        # three alignments; same inducer. Only sub-goals whose markers are present are included. Guarded.
        try:
            if not list(adapter.discrete_actions()):
                _obj = _induce_multigoal_objective(g0, (world.get("report") or {}).get("interaction_probe"))
                if _obj is not None and float(_obj.measure(g0)) > 0:
                    cands.insert(0, ({"relation": "COINCIDE", "descriptor": "induced-MULTIGOAL", "cue": "alignment",
                                      "target_color": None}, _obj))
                    _emit(adapter, "INDUCE  objective := \u03a3(sub_i)  [arity-invariant: satisfy ALL sub-goals present this level, order-independent]")
        except Exception:
            pass
        _set_composer_state(adapter, world=world, cands=cands, belief=belief, engine=engine)  # rich per-frame snapshot
        results = []
        remaining = descend_pass_budget                            # PASS 1 -- bounded cheap descend pass
        _max_prog = 0.0                                            # best discrepancy reduction across candidates
        for h, disc in cands:
            if remaining <= 0:
                break
            _init = float(disc.measure(g0))
            _ride_reason(adapter, relation=h["relation"], target=h.get("target_color"), pass_name="descend",
                         objective=h["descriptor"])
            r = descend(adapter, disc, ctrl, budget=min(remaining, 260), patience=40, max_restarts=2,
                        rotational=bool((world.get("report") or {}).get("rotational")),
                        rotate_actions=set((world.get("report") or {}).get("rotate_actions") or ()),
                        plan_amap=(world.get("report") or {}).get("shifts") or {},
                        plan_co=(world.get("report") or {}).get("co_moving_body") or [],
                        plan_rotate_model=(world.get("report") or {}).get("rotate_model") or {},
                        plan_schema=(world.get("report") or {}).get("schema"),
                        plan_individuation=(world.get("report") or {}).get("individuation"),
                        plan_interaction=(world.get("report") or {}).get("interaction_probe"))
            results.append((h["descriptor"], r))
            remaining -= r.get("mapping_cost", 0)
            _bd = r.get("best_discrepancy", _init)
            _max_prog = max(_max_prog, _init - (float(_bd) if _bd is not None else _init))
            if r.get("validated"):
                return dict(modality=modality, validated=h["descriptor"], won_relation=h["relation"], engine="descend",
                            detail=r, source=ab.get("source"), attempts=results)
        # LOSS-SIGNAL REDIRECT (your point): PASS 1 reduced NO objective's discrepancy -> the target is likely
        # WRONG. Rather than spamming pursuit variants on it, RESUME EXPLORING from here to find the real mechanic,
        # then re-abduce. Bounded to 2 extra cycles (probe, don't spam). Progress -> fall through to deeper passes.
        if _max_prog <= 1e-6 and _ex_cycles < 2 and cands:
            _ex_cycles += 1
            _ride_reason(adapter, pass_name="explore", objective="pursuit stalled -> resume exploration",
                         extra={"grammar": "every objective stalled (loss flat) -> likely the wrong target; explore "
                                           "more to find the real mechanic, then re-abduce (probe, don't spam)",
                                "cycle": _ex_cycles})
            world = explore_and_map(adapter, budget=220)           # resume/extend the map from where we are
            continue
        break                                                      # progress made OR cycles spent -> deeper passes
    # PASS 1.5 (§11.303) -- COMPOSE-ON-REFUTATION: the scientific-method refine step, self-composed.
    # A relation SATISFIED but UNREWARDED is necessary-but-INSUFFICIENT: the level compounds an extra rule
    # the current theory misses. The composer responds to that refuting evidence by building a RICHER
    # objective from primitives -- AND(refuted, X) over the other abduced atomics -- and tries it. No
    # game-specific code: the compound is assembled by the grammar and minimised by the same engine.
    reason_of = {descr: r.get("reason") for descr, r in results}
    try:                                                       # DIAGNOSTIC: closest any candidate got to SATISFIED (0)
        _bd = [r.get("best_discrepancy", r.get("final_discrepancy")) for _, r in results
               if (r.get("best_discrepancy") is not None or r.get("final_discrepancy") is not None)]
        if _bd:
            adapter._min_disc = float(min(_bd))
    except Exception:
        pass
    atomics = [(h, disc) for (h, disc) in cands if "spec" not in h and h.get("target_color") is not None]
    refuted = [(h, disc) for (h, disc) in atomics
               if reason_of.get(h["descriptor"]) == "predicate-satisfied-no-reward"]
    for hb, _ in refuted[:2]:                                  # the satisfied-but-insufficient base(s)
        for hx, _ in atomics:
            if hx["relation"] == hb["relation"] and hx["target_color"] == hb["target_color"]:
                continue
            spec = ("AND", (hb["relation"], hb["target_color"]), (hx["relation"], hx["target_color"]))
            try:
                cdisc = compile_objective(spec, ctrl, g0)
            except Exception:
                continue
            if cdisc.measure(g0) <= 0:
                continue
            _ride_reason(adapter, relation=hb["relation"], target=hb.get("target_color"), pass_name="compose",
                         objective=f"AND({hb['relation']},{hx['relation']})",
                         extra={"grammar": f"require {hb['relation']} AND {hx['relation']}"})
            r = descend(adapter, cdisc, ctrl, budget=min(budget, 300), patience=40, max_restarts=2,
                        reset_first=not getattr(adapter, "level_local", False),
                        rotational=bool((world.get("report") or {}).get("rotational")),
                        rotate_actions=set((world.get("report") or {}).get("rotate_actions") or ()),
                        plan_amap=(world.get("report") or {}).get("shifts") or {},
                        plan_co=(world.get("report") or {}).get("co_moving_body") or [],
                        plan_rotate_model=(world.get("report") or {}).get("rotate_model") or {},
                        plan_schema=(world.get("report") or {}).get("schema"),
                        plan_individuation=(world.get("report") or {}).get("individuation"),
                        plan_interaction=(world.get("report") or {}).get("interaction_probe"))
            if not r.get("validated"):
                r = pursue(adapter, cdisc, budget=min(budget, 1500),
                           max_resets=(5 if getattr(adapter, "online", False) else None))
            results.append((f"AND({hb['relation']},{hx['relation']})", r))
            if r.get("validated"):
                return dict(modality=modality, validated=f"AND({hb['relation']},{hx['relation']})",
                            won_relation=hb["relation"], engine="composed", detail=r,
                            source=(ab.get("source") or "") + "+compose", attempts=results)
    # PASS 1.6 (§11.306) -- DISCOVERY -> COMPOSITION: if a theory was refuted, the missing rule may concern a
    # whole OBJECT the per-colour path fragmented. Pull WHOLE objects from the shared object_seg substrate (the
    # same perception the affordance layer uses) and drive the controllable to CONTACT each, reward disposing.
    # This is the discovery layer feeding candidates the composer recognises -- gated on refutation (free on wins).
    if refuted:
        try:
            from object_seg import segment_objects
            bg0 = int(np.bincount(np.asarray(g0).ravel()).argmax())
            objs = sorted((o for o in segment_objects(np.asarray(g0), bg=bg0) if o["size"] >= 2),
                          key=lambda o: -o["size"])[:8]
            for o in objs:
                r0, r1, c0, c1 = o["bbox"]
                cen = (int(round(o["centroid"][0])), int(round(o["centroid"][1])))
                cdisc = compile_objective(("BE_AT", ("cell",) + cen), ctrl, g0)
                if cdisc.measure(g0) <= 0:
                    continue
                _ride_reason(adapter, relation="BE_AT", pass_name="discovery",
                             objective=f"CONTACT-OBJECT@{cen}",
                             extra={"grammar": "drive the controllable to contact a whole object"})
                r = descend(adapter, cdisc, ctrl, budget=min(budget, 260), patience=100,
                            reset_first=not getattr(adapter, "level_local", False),
                            rotational=bool((world.get("report") or {}).get("rotational")),
                            rotate_actions=set((world.get("report") or {}).get("rotate_actions") or ()),
                            plan_amap=(world.get("report") or {}).get("shifts") or {},
                            plan_co=(world.get("report") or {}).get("co_moving_body") or [],
                            plan_rotate_model=(world.get("report") or {}).get("rotate_model") or {},
                        plan_schema=(world.get("report") or {}).get("schema"),
                        plan_individuation=(world.get("report") or {}).get("individuation"),
                        plan_interaction=(world.get("report") or {}).get("interaction_probe"))
                results.append((f"CONTACT-OBJECT@{cen}", r))
                if r.get("validated"):
                    return dict(modality=modality, validated=f"CONTACT-OBJECT@{cen}",
                                won_relation="BE_AT", engine="discovery", detail=r,
                                source=(ab.get("source") or "") + "+discovery", attempts=results)
        except Exception:
            pass
    _online = getattr(adapter, "online", False)
    _pursue_cap = 5 if _online else None                       # ONLINE: bound Go-Explore reset+replay per candidate
    for h, disc in cands:                                      # PASS 2 -- Go-Explore fallback
        _ride_reason(adapter, relation=h["relation"], target=h.get("target_color"), pass_name="go-explore",
                     objective=h["descriptor"])
        r = pursue(adapter, disc, budget=budget, max_resets=_pursue_cap)
        results.append((h["descriptor"], r))
        if r.get("validated"):
            return dict(modality=modality, validated=h["descriptor"], won_relation=h["relation"], engine="go-explore",
                        detail=r, source=ab.get("source"), attempts=results)
    _ride_reason(adapter, pass_name="interaction", objective="novelty-probe",
                 extra={"grammar": "no perceived target rewards -- probe for reward by novelty"})
    probe = interaction_probe(adapter, budget=min(budget, 1200),
                              max_resets=(20 if _online else None))   # PASS 3 -- INTERACTION fallback (§11.261)
    if probe.get("reached"):
        return dict(modality=modality, validated="INTERACTION(novelty-Go-Explore)", engine="interaction",
                    detail=probe, source=(ab.get("source") or "") + "+interaction", attempts=results)
    # PASS 4 -- EVOLVABILITY ENGINE (MODEL_INCOMPLETE): the grammar was satisfied-but-unrewarded and every
    # existing pass failed -> the world obeys a dynamic the grammar lacks. Hand the RESIDUAL to the engine to
    # mint (residual-parametrised instance) or co-opt (composite of shadow-casting atomics, promoted to a
    # Molecule). This DRIVES the scored path (the new organs commit real actions); see evolvability_engine.py.
    # Built to composer_as_evolvability_engine.md. Fires only when `refuted` exists (the MODEL_INCOMPLETE cue).
    if engine is not None and refuted:
        try:
            g_after = _perceive_grid(adapter) if hasattr(adapter, "_grid") else g0
        except Exception:
            g_after = g0
        active_traces = {}
        for h, disc in atomics:
            try:
                cells = disc.active(g0)
                if cells:
                    active_traces[h.get("descriptor")] = cells
            except Exception:
                pass
        ctx = dict(g0=g0, ctrl=ctrl, refuted=refuted, atomics=atomics,
                   g_before=g0, g_after=g_after, active_traces=active_traces,
                   compile_objective=compile_objective, compile_discrepancy=compile_discrepancy,
                   descend=descend, pursue=pursue, adapter=adapter, budget=budget,
                   buffer=list(getattr(adapter, "transition_buffer", []) or []),   # RF1: forward-model residual
                   held_grids=engine.held_out_levels)                              # RF2: level-split generalisation
        won = engine.on_residual(ctx)
        if won:                                                    # the minted/co-opted organ drove a real win
            won.setdefault("modality", modality)
            won.setdefault("source", (ab.get("source") or "") + "+evolvability")
            won.setdefault("attempts", results)
            return won
    return dict(modality=modality, validated=None, source=ab.get("source"),
                attempts=results, interaction=probe)


def validate_multilevel(adapter, budget=3000, max_hyps=4, max_levels=40, time_budget=None):
    """11.302: pursue FULL game completion, not just level 1 -- the dominant RHAE lever (later levels weigh
    more; a full win >> level-1-everywhere). Mechanism (now WORKING): level-local resets (adapter.level_local
    + engine ONLY_RESET_LEVELS) PRESERVE completed levels, and the engine auto-advances to the next level
    inside the completing action. Loop validate(); gate STRICTLY on a real levels_completed increase (never on
    satisfied(), which latches per level and caused the earlier false 40/40). Returns how many levels were
    actually completed -- the real progress metric. The agent progresses as far as its capability allows;
    later levels add rules and demand the deeper capabilities."""
    import time as _t
    t0 = _t.time()
    adapter.level_local = False                     # level 1: clean (re-made) resets; level 0
    solved = 0
    belief = {}                                     # THEORY: relation -> confidence, carried + refined across levels
    # PER-GAME GENOME (composer_as_evolvability_engine.md): one evolvability engine persists across all levels,
    # so minted instances, co-opted+promoted Molecules, the cadence/EDA prior, the refutation history, the 1/5
    # radius and the posterior/CUSUM state ACCUMULATE within the game (the within-lifetime evolution loop).
    try:
        import evolvability_engine as _EE
        engine = _EE.new_engine()
    except Exception:
        engine = None
    while solved < max_levels:
        if time_budget and _t.time() - t0 > time_budget:
            break
        r = validate(adapter, budget=budget, max_hyps=max_hyps, belief=belief, engine=engine)
        adapter.level_local = True                  # later levels: level-local resets preserve progress
        after = getattr(adapter._obs, "levels_completed", 0) or 0
        if after <= solved:                         # theory did not yield a new level -> stop (novel wall)
            break
        wr = r.get("won_relation")                  # ANALYZE+REFINE: supported theory gains confidence
        if wr:
            belief[wr] = min(1.0, belief.get(wr, 0.4) + 0.3)
        # RF2: bank the just-solved level's frames as a LEVEL-SPLIT held-out set (real generalisation ground
        # truth for Gate 2 — a minted/co-opted primitive must predict a level it was not fit on to be promoted).
        if engine is not None:
            try:
                engine.archive_level(list(getattr(adapter, "transition_buffer", []) or []))
            except Exception:
                pass
        solved = after
        st = getattr(adapter._obs, "state", None)
        if st is not None and "WIN" in str(getattr(st, "name", st)).upper():
            break
    return dict(levels_completed=solved, belief=belief,
                evolvability=(dict(narration=engine.narration[-60:],
                                   events=engine.events[-50:],
                                   escalations=engine.escalations,
                                   promoted=engine.coopt.promoted,
                                   fired=getattr(engine, "fired", 0),
                                   radius=round(float(engine.radius.radius), 2),
                                   posterior=engine.posterior.history[-10:])
                              if engine is not None else None))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/mnt/user-data/outputs")
    from arc_modules import ArcAdapter
    env = sys.argv[1] if len(sys.argv) > 1 else "env/environment_files"
    gid = sys.argv[2] if len(sys.argv) > 2 else "tu93"
    print(gid, validate(ArcAdapter(gid, env_dir=env)))
