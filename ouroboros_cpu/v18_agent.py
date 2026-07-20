"""Ouroboros ARC-AGI-3 agent — combined single-file build.
Core-Knowledge perception + common-fate cohesion + win-predicate induction +
open-ended feature invention with a persisted germline (return leg). Pure numpy+stdlib.
"""
import os, sys, json, time, math, hashlib
import numpy as np
from collections import defaultdict, deque, Counter
# ===================== relbridge.py (INLINED for Kaggle self-containment) =====================
class _RB:
    pass
try:
    from scipy import ndimage as _ndimage
    def _rb_feature_bank(G):
        import numpy as _np
        G=_np.atleast_2d(_np.asarray(G))
        if G.size==0 or len(_np.unique(G))<=1: return {}
        vals,cnts=_np.unique(G,return_counts=True); bg=int(vals[_np.argmax(cnts)])
        nb=(G!=bg); coords=_np.argwhere(nb); d={}
        if len(coords):
            d['bbox_h']=float(coords[:,0].max()-coords[:,0].min()); d['bbox_w']=float(coords[:,1].max()-coords[:,1].min())
            d['com_r']=float(coords[:,0].mean()); d['com_c']=float(coords[:,1].mean()); d['front_r']=float(coords[:,0].max())
        lbl,ncl=_ndimage.label(nb)
        if ncl: sizes=_ndimage.sum(nb,lbl,range(1,ncl+1)); d['big_sz']=float(max(sizes)); d['ncomp']=float(ncl)
        d['holes']=float(_ndimage.binary_fill_holes(nb).sum()-nb.sum())
        return d
    def _rb_symmetry(G):
        import numpy as _np
        G=_np.atleast_2d(_np.asarray(G))
        if G.size==0: return 0.0
        return 0.5*float(_np.mean(G==G[:,::-1]))+0.5*float(_np.mean(G==G[::-1,:]))
    _RB_LOCAL_FEATS=('bbox_h','bbox_w','com_r','com_c','front_r','big_sz','ncomp','holes')
    class _RelationalBridge:
        def __init__(self, halflife=0.98):
            import numpy as _np
            self.hl=halflife; self.prev=None; self.prev_sym=None
            self.trend={f:0.0 for f in _RB_LOCAL_FEATS}; self.activity={f:0.0 for f in _RB_LOCAL_FEATS}
            self.sym_trend=0.0; self.seen=0
        def observe(self, G):
            import numpy as _np
            fb=_rb_feature_bank(G); sym=_rb_symmetry(G); self.seen+=1
            if self.prev is not None:
                for f in _RB_LOCAL_FEATS:
                    if f in fb and f in self.prev:
                        ch=fb[f]-self.prev[f]
                        self.trend[f]=self.hl*self.trend[f]+(1-self.hl)*_np.sign(ch)
                        self.activity[f]=self.hl*self.activity[f]+(1-self.hl)*abs(ch)
                if self.prev_sym is not None:
                    self.sym_trend=self.hl*self.sym_trend+(1-self.hl)*_np.sign(sym-self.prev_sym)
            self.prev=fb; self.prev_sym=sym
        def drive_feature(self):
            import numpy as _np
            if self.seen<8: return None
            scored={f:abs(self.trend[f])*self.activity[f] for f in _RB_LOCAL_FEATS}
            f=max(scored,key=scored.get)
            if scored[f]<1e-3: return None
            return (f, _np.sign(self.trend[f]))
        def config_score(self, G):
            df=self.drive_feature()
            if df is None: return None
            f,dirn=df; fb=_rb_feature_bank(G)
            return dirn*fb.get(f,0.0) if f in fb else None
    _RB.feature_bank=staticmethod(_rb_feature_bank)
    _RB.RelationalBridge=_RelationalBridge
except Exception:
    _RB=None
# ===================== end inlined relbridge =====================


def _store_dir() -> str:
    """Return the durable memory root for all persisted germline/state JSON files.

    On Kaggle:  /kaggle/working  — the only writable directory in the competition
                environment; files here survive between cells and constitute the
                agent's cross-episode memory.

    Locally:    ARC3_STORE env var if set (e.g. a named experiment directory),
                otherwise ~/.arc3_store (not the cwd, which changes per run).

    All persisted files (germline, sediment, episode log, interventions) resolve
    their paths through this function so the Kaggle/local split is a single toggle.
    """
    if os.path.exists('/kaggle'):
        return '/kaggle/working'
    local = os.environ.get('ARC3_STORE', os.path.join(os.path.expanduser('~'), '.arc3_store'))
    os.makedirs(local, exist_ok=True)
    return local


def _ephemeral_store() -> bool:
    """When ARC3_EPHEMERAL_STORE is set, persistent stores start empty and never write,
    giving fully reproducible, history-independent runs. This is the root determinism
    control: without it, the cohesion sediment + prior-evolver JSON accumulate across runs
    and a later run's perception is warm-started by an earlier run (8 fragments -> 1 sprite,
    or a different color_aware rule), so 'identical' runs diverge. Default OFF preserves the
    cross-agent transfer capability for the submission; the DEV harness turns it ON."""
    return os.environ.get('ARC3_EPHEMERAL_STORE', '').strip().lower() in ('1', 'true', 'yes', 'on')


# ===================== arc3_predicate.py =====================
"""
arc3_predicate.py - win-PREDICATE induction (hardened).

The capability missing from all 26 uploaded agents: induce the symbolic win
condition (the count/identity/position predicate true at the win moment) as a
transferable object that drives planning. The basis decomposition showed the win
basis is number (16/25), object/agency (12/25), relation (7/25).

Hardened vs the first cut:
  - explicit step counter (specificity uses real turns, not a proxy);
  - count(c)==k templates for all k in 0..min(max_k, count) - not just 0/1;
  - position predicates player_near_color(c) - needs the SelfModel's controllable,
    so observe() takes ctrl_oid (the inducer is self-aware);
  - false-positive penalty keyed to FLIPS on non-win turns (a predicate that
    *becomes* true without a win), NOT to merely being true - so a correct win
    predicate that persists after the win is not punished;
  - coarse relation coverage (all_same_color/shape, two-group balance);
  - cross-level accumulation: belief integrates over every win the agent reaches.

belief = max(0, credited - LAMBDA*false_flips) * specificity   (specificity gates uninformative always-true predicates to ~0)
"""
from collections import Counter
from typing import Dict, List, Optional, Callable

LAMBDA = 0.5
MAX_K = 8


class Predicate:
    def __init__(self, name: str, fn: Callable[[list, dict], bool]):
        self.name = name
        self.fn = fn
        self.belief = 0.0
        self.credited = 0
        self.false_flips = 0
        self.seen_true = 0
    def __repr__(self):
        return f"<{self.name} b={self.belief:.2f} +{self.credited}/-{self.false_flips}>"


class PredicateInducer:
    def __init__(self, max_k: int = MAX_K):
        self.preds: List[Predicate] = []
        self._count_built = False
        self._pos_built = False
        self._prev_truth: Dict[str, bool] = {}
        self._last_progress = 0.0
        self._n_steps = 0
        self._wins_seen = 0          # total wins observed (denominator for credit reliability)
        self.max_k = max_k

    def _build_count_and_relation(self, objs):
        cc = Counter(o.color for o in objs)
        P = self.preds
        for c in sorted(cc):
            for k in range(0, min(self.max_k, cc[c]) + 1):
                P.append(Predicate(f"count_color({c})=={k}",
                                   lambda objs, ctx, c=c, k=k: sum(o.color == c for o in objs) == k))
        P.append(Predicate("all_same_color",
                           lambda objs, ctx: bool(objs) and len({o.color for o in objs}) <= 1))
        P.append(Predicate("all_same_shape",
                           lambda objs, ctx: bool(objs) and len({o.norm_shape for o in objs}) <= 1))
        P.append(Predicate("total_count==1", lambda objs, ctx: len(objs) == 1))
        P.append(Predicate("total_count==2", lambda objs, ctx: len(objs) == 2))
        def _balanced(objs, ctx):
            cc = Counter(o.color for o in objs)
            top = [n for _, n in cc.most_common(2)]
            return len(top) == 2 and top[0] == top[1]
        P.append(Predicate("two_groups_balanced", _balanced))
        self._count_built = True

    def _build_position(self, objs):
        cc = Counter(o.color for o in objs)
        for c in sorted(cc):
            def _near(objs, ctx, c=c):
                ctrl = next((o for o in objs if o.oid == ctx.get("ctrl")), None)
                if ctrl is None:
                    return False
                tgt = [cell for o in objs if o.color == c and o.oid != ctx.get("ctrl") for cell in o.cells]
                if not tgt:
                    return False
                cr, cc_ = ctrl.centroid
                return min(abs(r - cr) + abs(cl - cc_) for r, cl in tgt) <= 1.0
            self.preds.append(Predicate(f"player_near_color({c})", _near))
        self._pos_built = True

    def observe(self, objs, progress: float, ctrl_oid: Optional[int] = None):
        if objs and not self._count_built:
            self._build_count_and_relation(objs)
        if objs and not self._pos_built and ctrl_oid is not None:
            self._build_position(objs)
        self._n_steps += 1
        ctx = {"ctrl": ctrl_oid}
        truth = {p.name: bool(p.fn(objs, ctx)) for p in self.preds}
        win = progress > self._last_progress
        if win:
            self._wins_seen += 1
        for p in self.preds:
            if truth[p.name]:
                p.seen_true += 1
            became_true = truth[p.name] and not self._prev_truth.get(p.name, False)
            if win:
                # observability-correct: the winning (terminal) state is the PREVIOUS
                # frame; auto-advance means count==0 is never observed, so credit the
                # predicate that held just before progress jumped.
                if self._prev_truth.get(p.name, False):
                    p.credited += 1
            elif became_true:
                p.false_flips += 1          # flipped true with no win = spurious
            spec = 1.0 - p.seen_true / max(1, self._n_steps)
            # credit RELIABILITY: a real win condition is credited at ~every win; a
            # coincidence is credited at a small fraction. Weighting by credited/wins_seen
            # makes a spurious single credit self-correct as soon as a later win is reached
            # WITHOUT it holding (wins_seen rises, credited doesn't -> belief decays).
            # Preserves intended cross-level transfer; bounds a spurious credit to ~1 level.
            reliability = p.credited / max(1, self._wins_seen)
            p.belief = max(0.0, p.credited - LAMBDA * p.false_flips) * spec * reliability
        self._prev_truth = truth
        self._last_progress = progress

    def top(self) -> Optional[Predicate]:
        cand = [p for p in self.preds if p.credited > 0 and p.belief > 0]
        return max(cand, key=lambda p: p.belief) if cand else None

    def monitor(self):
        """Observability for the cross-level-bias watch item: returns the top predicate,
        its credit reliability (credited/wins_seen), and wins seen. reliability < 1.0 with
        wins_seen > 1 means the top predicate did NOT hold at every win -> suspect a
        spuriously-credited carryover from an earlier level."""
        t = self.top()
        if t is None:
            return {"top": None, "wins_seen": self._wins_seen}
        return {"top": t.name, "credited": t.credited, "wins_seen": self._wins_seen,
                "reliability": t.credited / max(1, self._wins_seen),
                "false_flips": t.false_flips, "belief": round(t.belief, 3)}

    def target(self, objs, ctrl_oid: Optional[int]):
        t = self.top()
        if not t:
            return None
        ctrl = next((o for o in objs if o.oid == ctrl_oid), None)
        if ctrl is None:
            return None
        cr, cc_ = ctrl.centroid
        if t.name.startswith("count_color("):
            inside = t.name[t.name.index("(") + 1:]
            c = int(inside[:inside.index(")")]); k = int(t.name.split("==")[1])
            cur = sum(o.color == c for o in objs)
            if cur > k:
                cells = [cell for o in objs if o.color == c and o.oid != ctrl_oid for cell in o.cells]
                if cells:
                    return min(cells, key=lambda p: abs(p[0] - cr) + abs(p[1] - cc_)), "reduce"
        if t.name.startswith("player_near_color("):
            c = int(t.name[t.name.index("(") + 1: t.name.index(")")])
            cells = [cell for o in objs if o.color == c and o.oid != ctrl_oid for cell in o.cells]
            if cells:
                return min(cells, key=lambda p: abs(p[0] - cr) + abs(p[1] - cc_)), "approach"
        return None

    def report(self, n: int = 5):
        return sorted(self.preds, key=lambda p: -p.belief)[:n]

# ===================== arc3_priors.py =====================
"""
arc3_priors.py — Core Knowledge prior layer for an ARC-AGI-3 agent.

Implements the reconciled basis set (Spelke / Kant / NSM / image-schemas /
Carey / Gardenfors / Talmy / Lake-Tenenbaum) as concrete detectors over a
64x64 integer grid (values 0..15). Pure numpy: no torch / arcengine, so the
whole prior layer is importable and unit-testable without the ARC harness.

Families implemented (research-doc section -> code):
  A. Physical/object      -> ObjectExtractor, ObjectTracker (persistence)
  B. Agentive/intentional -> SelfModel (self detection via action-deltas),
                             GoalModel (inverse-planning + free-energy)
  C. Numerical            -> NumberOps (subitize, ANS)
  D. Spatial/topological  -> GeometryOps (containment, symmetry, connectivity)
  E. Logical/relational   -> Relations (same/other, part-whole) + Primitive tags
  F. Force-dynamic        -> PhysicsModel (inertia, gravity, blockage, push)

The keystone for ARC-AGI-3 (where frontier models score <1%) is SelfModel +
PhysicsModel + GoalModel: these are *intervention-built*, recoverable only by
acting and watching frame deltas — exactly the loop LLMs lack.
"""

import numpy as np
from collections import deque, defaultdict, Counter
try:
    PredicateInducer = globals().get('PredicateInducer')  # inlined
except ImportError:
    pass  # in combined module, PredicateInducer is already defined above
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, FrozenSet

Grid = np.ndarray
Cell = Tuple[int, int]


# ======================================================================
# A. PHYSICAL / OBJECT PRIMITIVES
# ======================================================================
@dataclass
class Obj:
    """An object parsed from a frame (cohesion + persistence)."""
    color: int
    cells: FrozenSet[Cell]
    oid: int = -1                       # persistent id (assigned by tracker)
    def __post_init__(self):
        rs = [r for r, _ in self.cells]; cs = [c for _, c in self.cells]
        self.rmin, self.rmax = min(rs), max(rs)
        self.cmin, self.cmax = min(cs), max(cs)
        self.area = len(self.cells)
        self.h = self.rmax - self.rmin + 1
        self.w = self.cmax - self.cmin + 1
        self.centroid = (sum(rs) / self.area, sum(cs) / self.area)
    @property
    def bbox(self): return (self.rmin, self.cmin, self.rmax, self.cmax)
    @property
    def norm_shape(self) -> FrozenSet[Cell]:
        """Translation-invariant shape signature (for identity across moves)."""
        return frozenset((r - self.rmin, c - self.cmin) for r, c in self.cells)
    def shifted(self, dr: int, dc: int) -> FrozenSet[Cell]:
        return frozenset((r + dr, c + dc) for r, c in self.cells)


class ObjectExtractor:
    """OBJECT / COHESION (Spelke objecthood, image-schema OBJECT/PART-WHOLE).

    Connected-components over the grid. ``color_aware`` -> only same-color cells
    cohere (Gestalt similarity); else any non-background cell coheres.
    """
    def __init__(self, background: int = 0, connectivity: int = 4, color_aware: bool = True):
        self.bg = background
        self.nbrs = ([(-1, 0), (1, 0), (0, -1), (0, 1)] if connectivity == 4
                     else [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)])
        self.color_aware = color_aware

    def extract(self, grid: Grid) -> List[Obj]:
        H, W = grid.shape
        seen = np.zeros((H, W), bool)
        objs: List[Obj] = []
        for i in range(H):
            for j in range(W):
                if seen[i, j] or grid[i, j] == self.bg:
                    continue
                col = int(grid[i, j])
                comp, dq = [], deque([(i, j)])
                seen[i, j] = True
                while dq:
                    r, c = dq.popleft()
                    comp.append((r, c))
                    for dr, dc in self.nbrs:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and not seen[nr, nc] and grid[nr, nc] != self.bg:
                            if (not self.color_aware) or int(grid[nr, nc]) == col:
                                seen[nr, nc] = True
                                dq.append((nr, nc))
                objs.append(Obj(color=col, cells=frozenset(comp)))
        return objs


class ObjectTracker:
    """PERSISTENCE / CONTINUITY (object permanence; flags VOE anomalies).

    Matches objects across consecutive frames by (shape, color, proximity) and
    assigns stable ids. Reports MOVE / APPEAR / DISAPPEAR / TELEPORT / TRANSFORM.
    """
    def __init__(self, teleport_thresh: float = 6.0):
        self.teleport_thresh = teleport_thresh
        self._next = 0
        self.prev: List[Obj] = []

    def _new_id(self):
        self._next += 1
        return self._next

    def update(self, objs: List[Obj]) -> Dict[str, list]:
        events = {"move": [], "appear": [], "disappear": [], "teleport": [], "transform": []}
        used_prev: Set[int] = set()
        # 1) exact shape+color matches (allow displacement)
        for o in objs:
            best, best_d = None, 1e9
            for k, p in enumerate(self.prev):
                if k in used_prev or p.color != o.color or p.norm_shape != o.norm_shape:
                    continue
                d = abs(p.centroid[0] - o.centroid[0]) + abs(p.centroid[1] - o.centroid[1])
                if d < best_d:
                    best, best_d, best_k = p, d, k
            if best is not None:
                o.oid = best.oid
                used_prev.add(best_k)
                dr = round(o.centroid[0] - best.centroid[0]); dc = round(o.centroid[1] - best.centroid[1])
                if best_d > self.teleport_thresh:
                    events["teleport"].append((o.oid, dr, dc))
                elif best_d > 0.4:
                    events["move"].append((o.oid, dr, dc))
        # 2) same-color, changed-shape -> transform; else appear
        for o in objs:
            if o.oid != -1:
                continue
            cand = [(k, p) for k, p in enumerate(self.prev)
                    if k not in used_prev and p.color == o.color
                    and abs(p.centroid[0] - o.centroid[0]) + abs(p.centroid[1] - o.centroid[1]) < self.teleport_thresh]
            if cand:
                k, p = min(cand, key=lambda kp: abs(kp[1].centroid[0] - o.centroid[0]) + abs(kp[1].centroid[1] - o.centroid[1]))
                o.oid = p.oid
                used_prev.add(k)
                events["transform"].append((o.oid, p.area, o.area))
            else:
                o.oid = self._new_id()
                events["appear"].append(o.oid)
        for k, p in enumerate(self.prev):
            if k not in used_prev:
                events["disappear"].append(p.oid)
        self.prev = objs
        return events


# ======================================================================
# B. AGENTIVE / INTENTIONAL PRIMITIVES
# ======================================================================
class SelfModel:
    """SELF / AGENCY — *intervention-built* (the ARC-AGI-3 keystone).

    Logs, per action, which persistent object moved and by how much. The object
    whose displacement is most reliably *caused* by movement actions is 'me'.
    Builds a per-action effect (dr,dc) table for planning.
    """
    def __init__(self):
        # per-oid, THIS level only — used to identify which object is 'me' now.
        self.act_obj_disp: Dict[int, Dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))
        # identity-free, ACROSS levels — the transferable action->displacement knowledge.
        # ("up moves me up" holds on every level; only *which oid* is me changes.)
        self.consolidated: Dict[int, Counter] = defaultdict(Counter)
        self.act_count: Counter = Counter()

    def observe(self, action: int, events: Dict[str, list]):
        self.act_count[action] += 1
        moves = events.get("move", []) + events.get("teleport", [])
        for oid, dr, dc in moves:
            self.act_obj_disp[action][oid][(dr, dc)] += 1
        ctrl = self.controllable()
        if ctrl is not None:                 # consolidate the self-locus's displacement
            for oid, dr, dc in moves:
                if oid == ctrl:
                    self.consolidated[action][(dr, dc)] += 1

    def controllable(self) -> Optional[int]:
        """Which oid is 'me' on the CURRENT level (most consistent action-response)."""
        score: Counter = Counter()
        for action, per_obj in self.act_obj_disp.items():
            for oid, disps in per_obj.items():
                tot = sum(disps.values())
                score[oid] += max(disps.values()) / max(1, tot) * tot
        return score.most_common(1)[0][0] if score else None

    def effect(self, action: int) -> Optional[Tuple[int, int]]:
        """Identity-free: the transferable displacement for an action."""
        d = self.consolidated.get(action)
        return d.most_common(1)[0][0] if d else None

    def action_model(self) -> Dict[int, Tuple[int, int]]:
        """Identity-free transferable action->delta map (survives level changes)."""
        return {a: self.effect(a) for a in self.consolidated if self.effect(a)}

    def reset_level(self):
        """New layout: forget stale per-oid identity, KEEP the transferable deltas.
        Fixes the cross-level transfer bug where a fresh tracker reassigned oids and
        controllable() returned a ghost oid absent from the new frame."""
        self.act_obj_disp.clear()


class GoalModel:
    """GOAL-DIRECTEDNESS (Gergely-Csibra teleology; Baker inverse planning).

    Tracks the external progress signal (score / levels_completed) and records
    which actions have ever yielded progress. Goal *selection* is delegated to the
    PredicateInducer (induced win condition) with the geometric heuristic as
    fallback; the active-inference epistemic drive lives in PriorPolicy._explore
    (least-sampled actions). This object is deliberately thin — the earlier EFE
    state-scoring was never wired into the BFS planner, so it has been removed
    rather than left as dead code."""
    def __init__(self):
        self.last_progress: Optional[float] = None
        self.progress_actions: Counter = Counter()    # which actions ever yielded progress

    def observe(self, progress: float, action: int):
        if self.last_progress is not None and progress > self.last_progress:
            self.progress_actions[action] += 1
        self.last_progress = progress


# ======================================================================
# C. NUMERICAL PRIMITIVES
# ======================================================================
class NumberOps:
    """SUBITIZE (parallel individuation, exact <=4) + ANS (ratio comparison)."""
    @staticmethod
    def subitize(n: int) -> Optional[int]:
        return n if n <= 4 else None        # exact only in the small range
    @staticmethod
    def count_by_color(objs: List[Obj]) -> Dict[int, int]:
        return dict(Counter(o.color for o in objs))
    @staticmethod
    def compare(a: int, b: int) -> str:     # ANS: more/fewer/same
        return "same" if a == b else ("more" if a > b else "fewer")
    @staticmethod
    def extremum(objs: List[Obj], key="area", which="max") -> Optional[Obj]:
        if not objs:
            return None
        f = {"area": lambda o: o.area, "h": lambda o: o.h, "w": lambda o: o.w}[key]
        return (max if which == "max" else min)(objs, key=f)


# ======================================================================
# D. SPATIAL-GEOMETRIC / TOPOLOGICAL PRIMITIVES
# ======================================================================
class GeometryOps:
    """CONTAINMENT (image-schema CONTAINER), SYMMETRY (Euclidean transforms),
    CONNECTIVITY (LINK / adjacency)."""

    @staticmethod
    def symmetries(grid: Grid) -> Set[str]:
        s = set()
        if np.array_equal(grid, grid[:, ::-1]): s.add("mirror_h")
        if np.array_equal(grid, grid[::-1, :]): s.add("mirror_v")
        if grid.shape[0] == grid.shape[1]:
            if np.array_equal(grid, grid.T): s.add("transpose")
            if np.array_equal(grid, np.rot90(grid, 2)): s.add("rot180")
            if np.array_equal(grid, np.rot90(grid)): s.add("rot90")
        return s

    @staticmethod
    def holes(obj: Obj, grid_shape: Tuple[int, int]) -> int:
        """Count enclosed background regions (topological holes) of an object."""
        r0, c0, r1, c1 = obj.bbox
        H, W = r1 - r0 + 3, c1 - c0 + 3                     # pad by 1
        mask = np.zeros((H, W), bool)
        for r, c in obj.cells:
            mask[r - r0 + 1, c - c0 + 1] = True
        # flood exterior from (0,0); enclosed empties = holes
        ext = np.zeros((H, W), bool); dq = deque([(0, 0)]); ext[0, 0] = True
        while dq:
            r, c = dq.popleft()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and not ext[nr, nc] and not mask[nr, nc]:
                    ext[nr, nc] = True; dq.append((nr, nc))
        # count connected components of (empty and not exterior)
        enclosed = (~mask) & (~ext)
        seen = np.zeros_like(enclosed); n = 0
        for i in range(H):
            for j in range(W):
                if enclosed[i, j] and not seen[i, j]:
                    n += 1; dq = deque([(i, j)]); seen[i, j] = True
                    while dq:
                        r, c = dq.popleft()
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < H and 0 <= nc < W and enclosed[nr, nc] and not seen[nr, nc]:
                                seen[nr, nc] = True; dq.append((nr, nc))
        return n

    @staticmethod
    def contains(outer: Obj, inner: Obj) -> bool:
        """Is inner geometrically inside outer's bounding region and enclosed?"""
        r0, c0, r1, c1 = outer.bbox
        return all(r0 < r < r1 and c0 < c < c1 for r, c in inner.cells)


# ======================================================================
# E. LOGICAL / RELATIONAL PRIMITIVES
# ======================================================================
class Relations:
    """IDENTITY/SAME-OTHER, PART-WHOLE, SIMILARITY (Gardenfors feature geometry)."""
    @staticmethod
    def same_shape(a: Obj, b: Obj) -> bool:
        return a.norm_shape == b.norm_shape
    @staticmethod
    def odd_one_out(objs: List[Obj]) -> Optional[Obj]:
        if len(objs) < 3:
            return None
        sig = Counter(o.norm_shape for o in objs)
        rare = [o for o in objs if sig[o.norm_shape] == 1]
        return rare[0] if len(rare) == 1 else None
    @staticmethod
    def adjacency(objs: List[Obj]) -> Dict[int, Set[int]]:
        g: Dict[int, Set[int]] = defaultdict(set)
        for i, a in enumerate(objs):
            for j, b in enumerate(objs):
                if i >= j:
                    continue
                touch = any(abs(ra - rb) + abs(ca - cb) == 1
                            for ra, ca in a.cells for rb, cb in b.cells)
                if touch:
                    g[a.oid].add(b.oid); g[b.oid].add(a.oid)
        return g


# ======================================================================
# F. FORCE-DYNAMIC PRIMITIVES
# ======================================================================
class PhysicsModel:
    """INERTIA, GRAVITY, BLOCKAGE/SOLIDITY, COMPULSION/PUSH (Talmy force dynamics;
    intuitive-physics engine). Induced from observed move events over time."""
    def __init__(self):
        self.free_moves = 0          # moves with no action input (inertia/gravity)
        self.drift = Counter()       # direction of input-free motion
        self.blocked = 0             # actions that produced no motion (blockage)
        self.acted_moves = 0
        self.push_events = 0         # self moved -> another object also moved

    def observe(self, action_was_move: bool, events: Dict[str, list], self_oid: Optional[int]):
        moves = events.get("move", []) + events.get("teleport", [])
        if not action_was_move:
            for _, dr, dc in moves:
                self.free_moves += 1; self.drift[(np.sign(dr), np.sign(dc))] += 1
        else:
            if moves:
                self.acted_moves += 1
            else:
                self.blocked += 1
            if self_oid is not None and len([m for m in moves if m[0] != self_oid]) > 0 \
               and any(m[0] == self_oid for m in moves):
                self.push_events += 1

    def report(self) -> dict:
        gravity = self.drift.most_common(1)[0][0] if self.free_moves >= 3 else None
        return {
            "inertia_or_gravity": self.free_moves >= 3,
            "gravity_dir": gravity,
            "has_blockage": self.blocked > 0,
            "block_rate": self.blocked / max(1, self.blocked + self.acted_moves),
            "pushes_objects": self.push_events >= 2,
        }


# ======================================================================
# TASK-DECOMPOSITION INSTRUMENT (second deliverable)
# ======================================================================
PRIMITIVES = [
    "object", "persistence", "self_agent", "goal", "number_subitize", "number_ans",
    "containment", "symmetry", "connectivity", "holes", "same_other", "force_dynamics",
]


def decompose_frames(frames: List[Grid], actions: Optional[List[int]] = None,
                     background: int = 0) -> Dict[str, float]:
    """Run the detector bank over a transcript and emit a primitive-requirement
    vector: which Core-Knowledge primitives a task actually exercises. Works on a
    single frame (static) or a sequence (interactive)."""
    ex = ObjectExtractor(background=background)
    tr = ObjectTracker()
    req = {p: 0.0 for p in PRIMITIVES}
    prev_objs = None
    for t, g in enumerate(frames):
        objs = ex.extract(g)
        if objs:
            req["object"] = 1.0
        ev = tr.update(objs)
        if t > 0 and (ev["move"] or ev["transform"]):
            req["persistence"] = 1.0
        if t > 0 and (ev["disappear"] or ev["appear"]):
            req["persistence"] = max(req["persistence"], 0.6)
        # number
        if objs:
            cc = NumberOps.count_by_color(objs)
            if any(v <= 4 for v in cc.values()):
                req["number_subitize"] = max(req["number_subitize"], 0.5)
            if len(objs) > 4:
                req["number_ans"] = max(req["number_ans"], 0.5)
        # geometry / topology
        if GeometryOps.symmetries(g):
            req["symmetry"] = 1.0
        for o in objs:
            if GeometryOps.holes(o, g.shape) > 0:
                req["holes"] = 1.0
        for i, a in enumerate(objs):
            for b in objs[i + 1:]:
                if GeometryOps.contains(a, b) or GeometryOps.contains(b, a):
                    req["containment"] = 1.0
        if len(Relations.adjacency(objs)) > 0:
            req["connectivity"] = 0.5
        if Relations.odd_one_out(objs) is not None:
            req["same_other"] = 1.0
        prev_objs = objs
    # interactive-only primitives
    if actions is not None and len(frames) > 1:
        req["self_agent"] = 1.0       # an agent acting across frames implicates self/agency
        req["goal"] = 0.5
        req["force_dynamics"] = 0.5
    return req


# ======================================================================
# PRIOR POLICY — harness-independent agent brain (online, intervention-built)
# ======================================================================
class PriorPolicy:
    """Turns the prior layer into a policy for ARC-AGI-3's explore->exploit loop.

    Loop each turn: perceive + track -> update self/physics/goal from the delta ->
    ACT. The agent EXPLORES (active-inference epistemic drive: complete its own
    action model) until it has learned how every move-action displaces it, THEN
    EXPLOITS by planning a path to an inferred goal with an internal BFS over the
    *learned* action model and the *observed* obstacles (no env calls, no torch).
    """
    def __init__(self, move_actions=(1, 2, 3, 4), extra_actions=(5,), background=0, seed=0):
        self.move_actions = list(move_actions)
        self.all_actions = list(move_actions) + list(extra_actions)
        self.ex = ObjectExtractor(background=background)
        self.tr = ObjectTracker()
        self.sm = SelfModel()
        self.pm = PhysicsModel()
        self.gm = GoalModel()
        self._relbridge = _RB.RelationalBridge() if _RB is not None else None
        self._use_fallback_drive = True   # local-gradient/relational drive as a FALLBACK only
        self._amodel_cache = {}
        self.pred = PredicateInducer()
        try:
            _CFM = globals().get('CommonFateMerger')  # inlined
        except Exception:
            _CFM = globals().get('CommonFateMerger')              # combined module
        self.merger = _CFM() if _CFM else None
        self.use_cohesion = self.merger is not None   # off iff the merger couldn't load
        self.carver = None            # optional ComposableCarving (invented-feature perception)
        self._prev_frame = None
        self.rng = np.random.RandomState(seed)
        self.last_action = None
        self.turn = 0
        self._last_blocked = False
        self._prev_ctrl_pos = None
        self._impassable = set()
        # --- state-novelty exploration (ported from Ouroboros v1 get_novelty_bonus) ---
        # v1's explorer rewarded reaching UNSEEN STATES; the clean agent regressed to
        # count-balancing ACTIONS (uniform histogram, undirected wandering). Restore
        # state-novelty: credit each action with an EMA of whether it produced a state
        # not recently seen, and bias exploration toward high-novelty-yield actions.
        self._state_counts = {}            # state sig -> recent visit count
        self._novel_yield = {a: 1.0 for a in self.all_actions}  # optimistic init
        self._last_sig = None
        self._novelty_ema = 0.30           # EMA rate for per-action novelty yield
        self._recent_novelty = 1.0         # running novelty of the last few states
        # --- autonomous dynamics isolation (the no-op as control condition) ---
        # ~1/3 of games evolve WITHOUT agent input (enemies/timers). Attributing that
        # autonomous motion to the agent's action corrupts the causal model. The no-op
        # measures the autonomous baseline; we then subtract autonomously-moving objects
        # from the events before crediting an action. (Spelke agency + time.)
        self.last_was_noop = False         # set by MyAgent when the last action was a no-op
        self._auto_objs = {}               # oid -> count of autonomous moves observed
        self._auto_cells_ema = 0.0         # EMA of cells that change under a no-op
        self._noop_samples = 0             # how many no-op observations we have
        self._prev_raw = None              # previous raw frame, for autonomous cell-diff
        # --- goal induction (ported from v1 symbolic_reasoning_engine + meta-reasoner) ---
        # The measured #1 gap: the agent finds the self + action model but has NO goal
        # hypothesis, so it wanders a mapped space with no target. Enumerate candidate
        # goal TYPES from core knowledge, pursue one, and rotate on no-progress (fluid
        # intervene-and-induce on goals). Feeds the existing BFS planner.
        self._goal_types = ["reach_nearest", "reach_rarest", "reach_farthest", "collect_all"]
        self._goal_w = {t: 1.0 for t in self._goal_types}
        self._goal_active = "reach_nearest"
        self._goal_turns = 0               # turns spent on the active hypothesis
        self._goal_prog = 0                # progress events while active
        self._goal_lastprog = 0.0

    def set_object_prior(self, connectivity: int = 4, color_aware: bool = True,
                         common_fate: bool = True):
        """Apply an object-definition rule chosen by PriorEvolver (the return leg at the
        rule level). Rebuilds the extractor's carving and toggles common-fate cohesion."""
        self.ex = ObjectExtractor(background=self.ex.bg, connectivity=connectivity,
                                  color_aware=color_aware)
        if self.merger is not None:
            self.merger.frag_ex = ObjectExtractor(background=self.ex.bg,
                                                  connectivity=connectivity, color_aware=True)
            self.use_cohesion = bool(common_fate)
        else:
            self.use_cohesion = False

    def reset_level(self):
        """New layout: keep transferable self-model deltas + induced predicate;
        forget per-level identity, walls, and visited states."""
        self.sm.reset_level()
        self.gm.progress_actions.clear()
        self._impassable.clear()
        self._prev_ctrl_pos = None
        self._prev_frame = None
        self.last_action = None

    def set_composable_carver(self, carver):
        """Perceive through an invented-feature carving (ComposableCarving from
        arc3_compose), which can use temporal features (motion). None -> default path."""
        self.carver = carver

    def _perceive(self, frame: Grid):
        """Common-fate cohesion front-end: learn co-moving fragment groups from the
        last transition, then return a CONSISTENT segmentation (multi-color sprites
        recovered as single objects). Falls back to raw fragments before anything is
        learned. No-op on single-color worlds (group_conf stays empty)."""
        if self.carver is not None:
            labels = self.carver.segment_labels(frame, self._prev_frame, bg=self.ex.bg)
            groups = defaultdict(list)
            for cell, lab in labels.items():
                groups[lab].append(cell)
            objs = []
            for cells in groups.values():
                cnt = Counter(int(frame[r, c]) for (r, c) in cells)
                objs.append(Obj(color=cnt.most_common(1)[0][0], cells=frozenset(cells)))
            self._prev_frame = frame.copy()
            return objs
        if not self.use_cohesion or self.merger is None:
            return self.ex.extract(frame)
        if self._prev_frame is not None:
            self.merger.merge_from_transition(self._prev_frame, frame, learn=True)
        objs = self.merger.segment(frame)
        self._prev_frame = frame.copy()
        return objs

    def observe(self, frame: Grid, progress: float = 0.0):
        objs = self._perceive(frame)
        ev = self.tr.update(objs)
        if self.last_was_noop:
            # CONTROL CONDITION: no real action was taken, so EVERY change here is
            # autonomous (world-driven). Measure it from the RAW frame diff (captures
            # color-flips/appearance, not just rigid moves) and record which objects
            # translated (for isolation). This is the confound's measurement.
            cells = 0
            if self._prev_raw is not None and self._prev_raw.shape == frame.shape:
                cells = int((frame != self._prev_raw).sum())
            for oid, dr, dc in ev.get("move", []) + ev.get("teleport", []):
                self._auto_objs[oid] = self._auto_objs.get(oid, 0) + 1
            self._noop_samples += 1
            r = 0.4
            self._auto_cells_ema = (1 - r) * self._auto_cells_ema + r * cells
            c = self.sm.controllable()
            self.pred.observe(objs, progress, ctrl_oid=c)
            self._prev_raw = frame.copy()
            return objs
        if self.last_action is not None:
            # ISOLATION: strip autonomously-moving objects from the events before
            # crediting the action, so SelfModel/PhysicsModel learn the TRUE self-effect.
            ev = self._isolate_self_events(ev)
            was_move = self.last_action in self.move_actions
            self.sm.observe(self.last_action, ev)
            self.pm.observe(was_move, ev, self.sm.controllable())
            self.gm.observe(progress, self.last_action)
            ctrl = self.sm.controllable()
            moved = any(oid == ctrl for oid, _, _ in ev.get("move", []) + ev.get("teleport", []))
            self._last_blocked = was_move and not moved
            if self._last_blocked and self._prev_ctrl_pos is not None:
                d = self.sm.effect(self.last_action)
                if d is None and ctrl is not None:
                    d = None
                if d is not None:
                    self._impassable.add((self._prev_ctrl_pos[0] + d[0], self._prev_ctrl_pos[1] + d[1]))
        c = self.sm.controllable()
        self.pred.observe(objs, progress, ctrl_oid=c)
        self._prev_ctrl_pos = self._ctrl_pos(objs, c) if c is not None else self._prev_ctrl_pos
        self._prev_raw = frame.copy()
        return objs

    def _isolate_self_events(self, ev):
        """Remove objects known to move autonomously (seen moving under a no-op) from
        the event set, so an action isn't credited with the world's own motion. An
        object that has moved autonomously >=2 times is treated as world-driven."""
        if not self._auto_objs:
            return ev
        auto = {oid for oid, n in self._auto_objs.items() if n >= 2}
        if not auto:
            return ev
        out = dict(ev)
        for k in ("move", "teleport"):
            if k in out:
                out[k] = [(oid, dr, dc) for (oid, dr, dc) in out[k] if oid not in auto]
        return out

    def has_autonomous_dynamics(self) -> bool:
        return self._noop_samples >= 1 and self._auto_cells_ema >= 1.0

    def _ctrl_pos(self, objs, ctrl):
        o = next((o for o in objs if o.oid == ctrl), None)
        return (int(round(o.centroid[0])), int(round(o.centroid[1]))) if o else None

    def _wall_color(self, objs):
        """Walls usually line the grid perimeter. Prefer the color occupying the most
        BORDER cells over the most AREA, so large interior colored goals are not
        mistaken for walls (Bug 4). Falls back to max-area if nothing is on the border."""
        if not objs:
            return None
        H = max(o.rmax for o in objs) + 1
        W = max(o.cmax for o in objs) + 1
        border, area = Counter(), Counter()
        for o in objs:
            area[o.color] += o.area
            for (r, c) in o.cells:
                if r == 0 or c == 0 or r == H - 1 or c == W - 1:
                    border[o.color] += 1
        if border:
            return border.most_common(1)[0][0]
        return area.most_common(1)[0][0]

    def _goal_cells(self, objs, ctrl):
        wall = self._wall_color(objs)
        ctrl_color = next((o.color for o in objs if o.oid == ctrl), None)
        cands = [o for o in objs if o.oid != ctrl and o.color != wall and o.color != ctrl_color]
        if not cands:
            cands = [o for o in objs if o.oid != ctrl and o.color != ctrl_color]
        singles = [o for o in cands if o.area <= 4]
        return [next(iter(o.cells)) for o in (singles or cands)]

    def _detect_goal_objs(self, objs, ctrl, grid):
        """Robust goal-object detection (ported from meta-reasoner detect_goals): exclude
        UI chrome — row-0 level dots, bottom win/gameover bar, side edges, and the top-2
        most-common colors (padding + background) plus wall + self color. Returns list of
        (obj, centroid_cell). This is what the crude _goal_cells failed to exclude."""
        H = max((o.rmax for o in objs), default=grid.shape[0] - 1) + 1
        W = max((o.cmax for o in objs), default=grid.shape[1] - 1) + 1
        vals, cnts = np.unique(grid, return_counts=True)
        order = sorted(zip(cnts.tolist(), vals.tolist()), reverse=True)
        common = {v for c, v in order[:2] if c > grid.size * 0.03}
        common.add(self.ex.bg)
        wall = self._wall_color(objs)
        if wall is not None:
            common.add(wall)
        ctrl_color = next((o.color for o in objs if o.oid == ctrl), None)
        if ctrl_color is not None:
            common.add(ctrl_color)
        bot = max(1, min(2, H // 8))
        out = []
        for o in objs:
            if o.oid == ctrl or o.color in common:
                continue
            r, c = int(round(o.centroid[0])), int(round(o.centroid[1]))
            if r == 0 or r >= H - bot or c == 0 or c >= W - 1:    # UI-chrome zone
                continue
            out.append((o, (r, c)))
        return out

    def _induce_goal(self, objs, ctrl, grid, start, progress):
        """Fluid goal-type induction: pursue the active hypothesis, reward it on progress,
        rotate to another when it stalls. Returns a target cell for the BFS planner."""
        if progress > self._goal_lastprog:                     # active hypothesis worked
            self._goal_w[self._goal_active] += 1.0
            self._goal_prog += 1
        self._goal_lastprog = progress
        self._goal_turns += 1
        if self._goal_turns > 40 and self._goal_prog == 0:     # stalled -> demote & rotate
            self._goal_w[self._goal_active] *= 0.5
            ranked = sorted(self._goal_types, key=lambda t: -self._goal_w[t])
            nxt = next((t for t in ranked if t != self._goal_active), ranked[0])
            self._goal_active = nxt
            self._goal_turns = 0
            self._goal_prog = 0
        gc = self._detect_goal_objs(objs, ctrl, grid)
        if not gc:
            cells = self._goal_cells(objs, ctrl)               # fallback to crude detector
            return min(cells, key=lambda g: abs(g[0] - start[0]) + abs(g[1] - start[1])) if cells else None
        cells = [cell for (_, cell) in gc]
        t = self._goal_active
        if t == "reach_farthest":
            return max(cells, key=lambda g: abs(g[0] - start[0]) + abs(g[1] - start[1]))
        if t == "reach_rarest":
            colcount = Counter(o.color for o in objs)
            return min(gc, key=lambda oc: colcount[oc[0].color])[1]
        # reach_nearest / collect_all -> nearest (collect_all re-detects after each pickup)
        return min(cells, key=lambda g: abs(g[0] - start[0]) + abs(g[1] - start[1]))

    def _obstacles(self, objs, ctrl, goal):
        obs = set(self._impassable)
        wall = self._wall_color(objs)
        for o in objs:
            if o.oid == ctrl or o.color != wall:
                continue
            for cell in o.cells:
                if cell != goal:
                    obs.add(cell)
        obs.discard(goal)
        return obs

    def _plan(self, start, goal, obstacles, amodel, shape):
        """BFS over grid cells using learned action deltas; return first action."""
        H, W = shape
        from collections import deque as _dq
        q = _dq([start]); came = {start: (None, None)}
        while q:
            cur = q.popleft()
            if cur == goal:
                # backtrack to first action
                a = None
                while came[cur][0] is not None:
                    cur, a = came[cur]
                return a
            for act, (dr, dc) in amodel.items():
                nxt = (cur[0] + dr, cur[1] + dc)
                if (0 <= nxt[0] < H and 0 <= nxt[1] < W and nxt not in obstacles
                        and nxt not in came):
                    came[nxt] = (cur, act); q.append(nxt)
        return None

    def _note_state(self, frame) -> None:
        """Credit the last action with the novelty of the state it produced, then
        record the current state. Novelty = 1/(1+times_seen): high for fresh states,
        decaying as a state is revisited. This is the ported v1 state-novelty signal."""
        try:
            sig = hash(frame.tobytes())
        except Exception:
            return
        seen = self._state_counts.get(sig, 0)
        novelty = 1.0 / (1.0 + seen)
        changed = (self._last_sig is not None and sig != self._last_sig)
        if self.last_action is not None and self.last_action in self._novel_yield:
            target = max(novelty, 1.0 if changed else 0.0)
            r = self._novelty_ema
            self._novel_yield[self.last_action] = (
                (1 - r) * self._novel_yield[self.last_action] + r * target)
        self._recent_novelty = 0.7 * self._recent_novelty + 0.3 * novelty
        self._state_counts[sig] = seen + 1
        if len(self._state_counts) > 4096:
            self._state_counts.pop(next(iter(self._state_counts)))
        self._last_sig = sig

    def _explore(self, amodel):
        # Prefer actions whose effect is still unknown (model-completion drive, kept),
        # else explore the full set. Among the pool, choose by NOVELTY YIELD (state-
        # novelty, ported from v1) blended with count-coverage, not pure count-balancing.
        unknown = [a for a in self.move_actions if a not in amodel]
        pool = unknown if unknown else self.all_actions
        if self._last_blocked and self.last_action in pool and len(pool) > 1:
            pool = [a for a in pool if a != self.last_action]
        def score(a):
            cnt = self.sm.act_count[a]
            return self._novel_yield.get(a, 1.0) - 0.15 * (cnt / (1.0 + self.turn)) \
                + 1e-3 * self.rng.rand()
        return max(pool, key=score)

    def act(self, frame: Grid, progress: float = 0.0) -> int:
        self._note_state(frame)
        if self._relbridge is not None and self._use_fallback_drive:
            try: self._relbridge.observe(frame)
            except Exception: pass
        self._last_frame_for_drive = frame
        objs = self.observe(frame, progress)
        self.turn += 1
        ctrl = self.sm.controllable()
        amodel = self.sm.action_model()   # identity-free; survives level reset
        model_complete = ctrl is not None and len(amodel) >= len(self.move_actions)

        if model_complete:
            start = self._ctrl_pos(objs, ctrl)
            if start:
                # predicate-driven target (induced win condition) takes priority
                goal = None
                ptgt = self.pred.target(objs, ctrl)
                if ptgt is not None:
                    goal = ptgt[0]
                if goal is None:
                    goal = self._induce_goal(objs, ctrl, frame, start, progress)
                # OVER-COMMITMENT GUARD: if recent states are stale (we're looping on a
                # goal that isn't paying off), divert to novelty-exploration instead of
                # re-committing. Probability rises as recent novelty falls. This is what
                # let random out-explore the agent: model_complete bypassed exploration.
                stuck = max(0.0, 0.30 - self._recent_novelty) * 3.0
                if goal is not None and self.rng.rand() >= stuck:
                    a = self._plan(start, goal, self._obstacles(objs, ctrl, goal), amodel, frame.shape)
                    if a is not None:
                        self.last_action = a
                        return a
        a = self._drive_fallback(objs, amodel, frame)
        if a is None:
            a = self._explore(amodel)
        self.last_action = a
        return a

    def _drive_fallback(self, objs, amodel, frame):
        """FALLBACK (only reached when no self-goal): steer toward the online-discovered
        drive feature (local-gradient §11.15-11.16 + relational §11.23). Gated; returns None
        to defer to blind exploration when no usable drive exists."""
        if not self._use_fallback_drive or self._relbridge is None:
            return None
        df = self._relbridge.drive_feature()
        if df is None:
            return None
        feat, want_dir = df
        cur = _RB.feature_bank(frame).get(feat) if _RB is not None else None
        if cur is None:
            return None
        # 30% epsilon so the fallback still explores; otherwise pick the move whose learned
        # effect (from amodel: action->(dr,dc)) most plausibly pushes the feature the right way.
        if self.rng.rand() < 0.30 or not amodel:
            return None
        # heuristic effect->feature mapping (frame-invariant): com_r/front_r/bbox_h move with dr;
        # com_c/bbox_w move with dc; big_sz/ncomp/holes are size-like (no directional amodel cue).
        best, best_score = None, -1e9
        for act, eff in amodel.items():
            dr, dc = (eff if isinstance(eff,(tuple,list)) and len(eff)>=2 else (0,0))
            if feat in ("com_r","front_r","bbox_h"): proj = dr
            elif feat in ("com_c","bbox_w"):         proj = dc
            else:                                    proj = (abs(dr)+abs(dc))*want_dir  # size: any motion
            score = proj*want_dir
            if score > best_score:
                best, best_score = act, score
        return best if best_score > 0 else None

    def family(self) -> str:
        """Online family classification from the agent's own models (not source).
        Tells you which solver the game needs; the spine solves number_self /
        object_self; force/geometry/persistence await the ported solvers."""
        ctrl = self.sm.controllable()
        if ctrl is None:
            return "no_self_yet"          # geometry/persistence-like, or under-explored
        top = self.pred.top()
        if top is not None and top.name.startswith("count_color"):
            return "number_self"          # SOLVED (predicate + navigate)
        phys = self.pm.report()
        if phys.get("gravity_dir") or phys.get("pushes_objects"):
            return "force_object"         # PARTIAL (explore only; needs physics planner)
        return "object_self"              # SOLVED (navigate)

    def report(self) -> dict:
        c = self.sm.controllable()
        return {"turn": self.turn, "self_oid": c,
                "action_model": self.sm.action_model(),
                "physics": self.pm.report(),
                "progress_actions": dict(self.gm.progress_actions)}

# ===================== arc3_cohesion.py =====================
"""
arc3_cohesion.py — common-fate object cohesion.

The measured problem (74% of game sprites are multi-color): connected-components-
of-constant-color FRAGMENTS a true object into one piece per color. The dialogue's
proposed fix was common fate — group fragments that move together into one object,
regardless of color — which should (a) recover multi-color sprites and (b) separate
same-color distinct agents. This module builds that and is tested against the games'
real sprite definitions.

Design = "reasonable default, corrected by intervention":
  - with NO motion, fall back to the adjacency prior (contiguous region = object);
  - with motion, MERGE adjacent fragments sharing a displacement (a rigid sprite)
    and keep apart fragments with different displacements (distinct agents).
The merge relations are accumulated across transitions into a persistent model, so
later static frames inherit the corrections learned from earlier motion.
"""
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple, FrozenSet

Obj = globals().get('Obj')  # inlined
ObjectExtractor = globals().get('ObjectExtractor')  # inlined

Cell = Tuple[int, int]


def _adjacent(a: Obj, b: Obj) -> bool:
    bcells = b.cells
    for (r, c) in a.cells:
        if (r - 1, c) in bcells or (r + 1, c) in bcells or (r, c - 1) in bcells or (r, c + 1) in bcells:
            return True
    return False


def _dominant_color(grid: Optional[np.ndarray], cells: FrozenSet[Cell], fallback: int) -> int:
    if grid is None:
        return fallback
    cnt = Counter(int(grid[r, c]) for (r, c) in cells)
    return cnt.most_common(1)[0][0] if cnt else fallback


class CommonFateMerger:
    """Merge color-fragments into objects by shared motion (common fate)."""

    def __init__(self, require_adjacent: bool = True):
        self.frag_ex = ObjectExtractor(color_aware=True)     # the fragmenting (default) prior
        self.require_adjacent = require_adjacent
        # persistent merge model: translation-invariant signature of a co-moving
        # fragment group -> confidence. Signature = sorted tuple of
        # (color, rel_row, rel_col) of the fragments, anchored at the group min.
        self.group_conf: Dict[tuple, float] = defaultdict(float)

    def warm_start_groups(self, seeded: Dict[tuple, float]):
        """Pre-seed learned object-groups from a previous agent (the return leg):
        the next agent recognises these multi-color sprites as one object from frame 0,
        without re-observing them move. A sedimented group is pre-validated, so its
        confidence is floored to a usable level (segment() trusts conf >= 1)."""
        for sig, conf in (seeded or {}).items():
            self.group_conf[sig] = max(self.group_conf.get(sig, 0.0), float(conf), 1.0)

    def export_groups(self) -> Dict[tuple, float]:
        """The object-groups this agent learned, to sediment for the next generation."""
        return dict(self.group_conf)

    # ---- core: one observed transition --------------------------------------
    def _displacements(self, A: List[Obj], B: List[Obj]) -> Dict[int, Tuple[int, int]]:
        disp, usedB = {}, set()
        for i, a in enumerate(A):
            cands = [(j, b) for j, b in enumerate(B)
                     if j not in usedB and b.color == a.color and b.norm_shape == a.norm_shape]
            if cands:
                j, b = min(cands, key=lambda jb: abs(jb[1].centroid[0] - a.centroid[0])
                           + abs(jb[1].centroid[1] - a.centroid[1]))
                disp[i] = (int(round(b.centroid[0] - a.centroid[0])),
                           int(round(b.centroid[1] - a.centroid[1])))
                usedB.add(j)
        return disp

    def _union_find(self, n, pairs):
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        for i, j in pairs:
            parent[find(i)] = find(j)
        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)
        return list(groups.values())

    def _group_signature(self, frags: List[Obj]) -> tuple:
        r0 = min(f.rmin for f in frags); c0 = min(f.cmin for f in frags)
        return tuple(sorted((f.color, f.rmin - r0, f.cmin - c0) for f in frags))

    def merge_from_transition(self, frame_t: np.ndarray, frame_t1: np.ndarray,
                              learn: bool = True, compact: int = 24) -> List[Obj]:
        A = self.frag_ex.extract(frame_t)
        B = self.frag_ex.extract(frame_t1)
        disp = self._displacements(A, B)
        # group fragment indices by their displacement
        by_disp: Dict[tuple, list] = defaultdict(list)
        for i, d in disp.items():
            by_disp[d].append(i)
        pairs = []
        for d, idxs in by_disp.items():
            if len(idxs) < 2 or d == (0, 0):
                continue                   # never merge static fragments (e.g. a still
                                           # player must not fuse with an adjacent wall);
                                           # static multi-color cohesion needs motion first.
            rs = [r for i in idxs for r, _ in A[i].cells]
            cs = [c for i in idxs for _, c in A[i].cells]
            span = max(max(rs) - min(rs), max(cs) - min(cs))
            if span <= compact:            # one LOCAL moving object -> merge all (even non-adjacent)
                for k in range(1, len(idxs)):
                    pairs.append((idxs[0], idxs[k]))
            else:                          # frame-wide co-motion (scroll) -> adjacency only
                for a in range(len(idxs)):
                    for b in range(a + 1, len(idxs)):
                        if _adjacent(A[idxs[a]], A[idxs[b]]):
                            pairs.append((idxs[a], idxs[b]))
        groups = self._union_find(len(A), pairs)
        merged = []
        for g in groups:
            frags = [A[i] for i in g]
            cells = frozenset().union(*[f.cells for f in frags])
            color = max(frags, key=lambda f: f.area).color
            merged.append(Obj(color=color, cells=cells))
            if learn and len(g) > 1:
                self.group_conf[self._group_signature(frags)] += 1
        return merged

    # ---- persistent: apply learned merges to a single (possibly static) frame
    def segment(self, frame: np.ndarray) -> List[Obj]:
        """Apply learned co-moving groups to a single frame for CONSISTENT segmentation
        (static or moving). Once motion has revealed that a set of color-fragments is
        one sprite, merge that arrangement wherever it appears."""
        A = self.frag_ex.extract(frame)
        if not self.group_conf:
            return A
        pos = {(o.color, o.rmin, o.cmin): i for i, o in enumerate(A)}
        used: set = set()
        merge_sets = []
        for sig, conf in sorted(self.group_conf.items(), key=lambda kv: (-len(kv[0]), -kv[1])):
            if conf < 1 or len(sig) < 2:
                continue
            anc_col, anc_rr, anc_rc = sig[0]
            for i, o in enumerate(A):
                if i in used or o.color != anc_col:
                    continue
                tlr, tlc = o.rmin - anc_rr, o.cmin - anc_rc
                grp, ok = [], True
                for (col, rr, rc) in sig:
                    key = (col, tlr + rr, tlc + rc)
                    if key in pos and pos[key] not in used and pos[key] not in grp:
                        grp.append(pos[key])
                    else:
                        ok = False
                        break
                if ok and len(grp) == len(sig):
                    used.update(grp)
                    merge_sets.append(grp)
        out = []
        for grp in merge_sets:
            frags = [A[i] for i in grp]
            cells = frozenset().union(*[f.cells for f in frags])
            out.append(Obj(color=max(frags, key=lambda f: f.area).color, cells=cells))
        for i, o in enumerate(A):
            if i not in used:
                out.append(o)
        return out

# ===================== arc3_evolve.py =====================
"""
arc3_evolve.py — the RETURN LEG: revise object-definition priors across agents.

Within a life, an agent recovers structure by intervention (forward stroke). Nothing
in the spine wrote that structure *back* into the prior the next agent starts from —
the carving of "what is one object" was frozen. This module closes the loop at the
object-definition level, the one place the spine never revised:

  (1) CohesionSediment  — instance level. Persists the co-moving fragment groups a
      CommonFateMerger learned (group_conf) and warm-starts the next agent's
      segmentation from them. The next agent recognises a multi-color sprite as one
      object *from frame 0*, without having to re-observe it move.

  (2) PriorEvolver      — RULE level. Holds a population of object-definition rules
      (connectivity x color_aware x common_fate) and SELECTS among them by sedimented
      downstream win-rate (UCB across generations). This is the return leg proper:
      which way of carving objects actually leads to wins, learned by selection over
      agents rather than written by hand.

HONEST SCOPE: (2) selects among a fixed menu of 8 rules; it does not *invent* new
carving rules, so it is bounded search over priors, not open-ended generation. But the
selection-by-fitness-across-generations is the genuine loop the spine lacked.

Persistence assumes a writable, durable path across runs (taken on good faith for the
Kaggle working dir); locally it writes to cwd so the generational loop is real on disk.
"""
import os, json, math, hashlib
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np


# --------------------------------------------------------------------------- #
# family key: a rule-INDEPENDENT signature of a game, stable across its levels  #
# --------------------------------------------------------------------------- #
def family_key(grid: np.ndarray, background: int = 0) -> str:
    """Coarse, stable signature of a game from a frame. Must NOT depend on the carving
    rule (the thing we're selecting), so it uses only colors + dims + density buckets."""
    g = np.asarray(grid)
    colors = tuple(sorted(int(c) for c in np.unique(g) if int(c) != background))
    dens = float((g != background).mean())
    dens_bucket = int(dens * 10)
    h, w = g.shape[-2], g.shape[-1]
    raw = f"{colors}|{h}x{w}|d{dens_bucket}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


# --------------------------------------------------------------------------- #
# (1) CohesionSediment — persist & warm-start learned object groups            #
# --------------------------------------------------------------------------- #
def _sig_to_str(sig: tuple) -> str:
    return ";".join(f"{c},{r},{cc}" for (c, r, cc) in sig)

def _str_to_sig(s: str) -> tuple:
    return tuple(tuple(int(x) for x in part.split(",")) for part in s.split(";"))


class CohesionSediment:
    """Cross-agent memory of which fragment groups are one object (per family)."""
    EMA_OLD = 0.80
    EMA_NEW = 0.20

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(_store_dir(), 'arc3_cohesion_sediment.json')
        self.store: Dict[str, Dict[str, float]] = {}
        self.load()

    def load(self):
        if _ephemeral_store():
            return
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    self.store = json.load(f)
            except Exception:
                self.store = {}

    def save(self):
        if _ephemeral_store():
            return
        try:
            with open(self.path, 'w') as f:
                json.dump(self.store, f)
        except Exception:
            pass

    def warm_start(self, fkey: str) -> Dict[tuple, float]:
        """Group signatures (as tuples) -> confidence, to pre-seed merger.group_conf.
        Only groups that survived sedimentation above a small trust floor are returned."""
        raw = self.store.get(fkey, {})
        out = {}
        for s, c in raw.items():
            try:
                if float(c) >= 0.1:
                    out[_str_to_sig(s)] = float(c)
            except Exception:
                continue
        return out

    def sediment(self, fkey: str, group_conf: Dict[tuple, float]):
        """EMA-merge an agent's learned groups into the durable store."""
        if not group_conf:
            return
        cur = self.store.setdefault(fkey, {})
        for sig, c in group_conf.items():
            k = _sig_to_str(sig)
            cur[k] = self.EMA_OLD * cur.get(k, 0.0) + self.EMA_NEW * float(c)
        self.save()


# --------------------------------------------------------------------------- #
# (2) PriorEvolver — select the object-definition RULE by win-rate            #
# --------------------------------------------------------------------------- #
RULES: List[dict] = [
    {"connectivity": conn, "color_aware": ca, "common_fate": cf}
    for conn in (4, 8) for ca in (True, False) for cf in (True, False)
]  # 8 carving rules


class PriorEvolver:
    """Bandit over object-definition rules, sedimented across generations.

    select(fkey) -> rule_idx via UCB1 (explore unseen rules first, then exploit the
    rule whose carving has the best downstream win-rate for this family). note_play /
    note_win accrue the fitness that persists to disk and shapes the next generation.
    """
    UCB_C = 1.4

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(_store_dir(), 'arc3_prior_evolver.json')
        self.plays: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.wins: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.load()

    def load(self):
        if _ephemeral_store():
            return
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    d = json.load(f)
                for fk, m in d.get('plays', {}).items():
                    for ri, n in m.items():
                        self.plays[fk][int(ri)] = int(n)
                for fk, m in d.get('wins', {}).items():
                    for ri, n in m.items():
                        self.wins[fk][int(ri)] = int(n)
            except Exception:
                pass

    def save(self):
        if _ephemeral_store():
            return
        try:
            d = {'plays': {fk: {str(ri): n for ri, n in m.items()} for fk, m in self.plays.items()},
                 'wins':  {fk: {str(ri): n for ri, n in m.items()} for fk, m in self.wins.items()}}
            with open(self.path, 'w') as f:
                json.dump(d, f)
        except Exception:
            pass

    def select(self, fkey: str) -> int:
        plays = self.plays[fkey]
        # explore any rule not yet tried for this family
        for ri in range(len(RULES)):
            if plays.get(ri, 0) == 0:
                return ri
        total = sum(plays.values())
        wins = self.wins[fkey]
        best_ri, best_u = 0, -1.0
        for ri in range(len(RULES)):
            n = plays[ri]
            rate = wins.get(ri, 0) / n
            u = rate + self.UCB_C * math.sqrt(math.log(total) / n)
            if u > best_u:
                best_u, best_ri = u, ri
        return best_ri

    def note_play(self, fkey: str, rule_idx: int):
        self.plays[fkey][rule_idx] += 1
        self.save()

    def note_win(self, fkey: str, rule_idx: int):
        self.wins[fkey][rule_idx] += 1
        self.save()

    def best_rule(self, fkey: str) -> Tuple[int, dict, float]:
        """Current champion rule for a family + its win-rate (for inspection/tests)."""
        plays = self.plays.get(fkey, {})
        if not plays:
            return 0, RULES[0], 0.0
        wins = self.wins.get(fkey, {})
        ri = max(plays, key=lambda r: wins.get(r, 0) / plays[r])
        return ri, RULES[ri], wins.get(ri, 0) / plays[ri]

# ===================== arc3_pixelgen.py =====================
"""
arc3_pixelgen.py — the pixel-expression generative substrate (the last seam).

Every prior layer composed features over a FIXED atom vocabulary
(same, diff1, moved1, ...). Those atoms are hand-authored predicates over a cell-pair,
and crucially the carver's eval interface only ever sees (c1, c2, is_orth, m1, m2) —
the boolean "did it move" flags, with the raw previous-frame colors p1, p2 already
thrown away. So a primitive like the SIGN of a pixel change (did this cell brighten or
dim?) is not merely unbuilt — it is structurally UNREACHABLE by composing the atoms,
because the information (the sign) was discarded before composition ever runs.

This module drops BELOW the atoms: it generates candidate primitives as arithmetic
expression trees over the raw cross-frame sensors {c1, c2, p1, p2, orth}, evolves them
under a verifiable (win-shaped) objective, and PROMOTES the ones that earn into named
primitives the composition layer can reuse. This is genetic programming with ADFs /
evolution of the primitive vocabulary — the open seam identified across the whole arc.

Two structural results it makes testable, not assertable:
  (1) OVERLAP (not exact rediscovery): the substrate can express an APPROXIMATE cross-frame
      change predicate such as (c1 != p1). Note this is NOT identical to the engine's
      displacement-tracked `moved1`: (c1 != p1) detects any color change at a fixed cell
      (a repaint trips it without motion; a sprite vacating a cell reads as change-at-cell
      though the object moved elsewhere). The claim is only that the hand atoms live NEAR
      the reachable set — the substrate extends the vocabulary, it does not reproduce the
      engine's exact semantics.
  (2) TRANSISTOR vs TORQUE-WRENCH: a signed-derivative / cross-frame primitive solves a task
      the fixed boolean atoms provably cannot exceed chance on — invention beyond the
      reachable set of the old grammar, not just a new composition within it.

Speciation (seam-two containment): primitives are promoted into ISLANDS keyed by game
family. Islands evolve independently (no shared germline by default), so a risky deeper
generator can be tried in one island without betting the others — and inter-island
migration is GATED, not automatic. Persistence is JSON under the working dir. No SQLite.
"""
import os, json, hashlib
import numpy as np
from typing import Optional

SENSORS = ["c1", "c2", "p1", "p2", "orth"]          # raw cross-frame inputs at a cell-pair
NUM_OPS = ["sub", "add", "absdiff", "sign", "neg"]   # numeric-producing
BOOL_OPS = ["eq", "lt", "le", "and", "or", "not"]    # boolean-producing


# ---- evaluation: an expression maps a sensor env -> scalar (bool coerced 0/1) --------
def eval_expr(e, env) -> float:
    tag = e[0]
    if tag == "var":
        return float(env[e[1]])
    if tag == "const":
        return float(e[1])
    if tag == "sub":
        return eval_expr(e[1], env) - eval_expr(e[2], env)
    if tag == "add":
        return eval_expr(e[1], env) + eval_expr(e[2], env)
    if tag == "absdiff":
        return abs(eval_expr(e[1], env) - eval_expr(e[2], env))
    if tag == "neg":
        return -eval_expr(e[1], env)
    if tag == "sign":
        v = eval_expr(e[1], env)
        return float((v > 0) - (v < 0))
    if tag == "eq":
        return float(eval_expr(e[1], env) == eval_expr(e[2], env))
    if tag == "lt":
        return float(eval_expr(e[1], env) < eval_expr(e[2], env))
    if tag == "le":
        return float(eval_expr(e[1], env) <= eval_expr(e[2], env))
    if tag == "and":
        return float(bool(eval_expr(e[1], env)) and bool(eval_expr(e[2], env)))
    if tag == "or":
        return float(bool(eval_expr(e[1], env)) or bool(eval_expr(e[2], env)))
    if tag == "not":
        return float(not bool(eval_expr(e[1], env)))
    raise ValueError(f"bad expr tag {tag}")


def expr_bool(e, env) -> bool:
    return bool(eval_expr(e, env))


def canonical_expr(e) -> str:
    tag = e[0]
    if tag == "var":
        return e[1]
    if tag == "const":
        return f"#{int(e[1])}"
    if tag in ("eq", "and", "or", "add", "absdiff"):          # commutative -> sort args
        a, b = canonical_expr(e[1]), canonical_expr(e[2])
        lo, hi = sorted([a, b])
        return f"{tag}({lo},{hi})"
    if tag in ("sub", "lt", "le"):
        return f"{tag}({canonical_expr(e[1])},{canonical_expr(e[2])})"
    return f"{tag}({canonical_expr(e[1])})"


def primitive_name(e) -> str:
    return "px_" + hashlib.sha1(canonical_expr(e).encode()).hexdigest()[:8]


# ---- the generative substrate: random arithmetic over raw sensors --------------------
class PixelExpressionGenerator:
    def __init__(self, seed=0, max_depth=3, consts=(0, 1, 2)):
        self.rng = np.random.RandomState(seed)
        self.max_depth = max_depth
        self.consts = consts

    def _num(self, depth):
        if depth <= 0 or self.rng.rand() < 0.4:
            if self.rng.rand() < 0.7:
                return ("var", SENSORS[self.rng.randint(len(SENSORS))])
            return ("const", int(self.consts[self.rng.randint(len(self.consts))]))
        op = NUM_OPS[self.rng.randint(len(NUM_OPS))]
        if op in ("sign", "neg"):
            return (op, self._num(depth - 1))
        return (op, self._num(depth - 1), self._num(depth - 1))

    def bool_expr(self, depth=None):
        depth = self.max_depth if depth is None else depth
        if depth <= 0:
            op = ["eq", "lt", "le"][self.rng.randint(3)]
            return (op, self._num(1), self._num(1))
        op = BOOL_OPS[self.rng.randint(len(BOOL_OPS))]
        if op == "not":
            return ("not", self.bool_expr(depth - 1))
        if op in ("and", "or"):
            return (op, self.bool_expr(depth - 1), self.bool_expr(depth - 1))
        return (op, self._num(depth), self._num(depth))      # eq/lt/le over numerics

    def mutate(self, e):
        # 30%: regrow a fresh boolean expr; else point-mutate a subtree
        if self.rng.rand() < 0.3:
            return self.bool_expr()
        return self._mut(e, 0)

    def _mut(self, e, depth):
        if self.rng.rand() < 0.25:
            if e[0] in ("eq", "lt", "le", "and", "or", "not"):
                return self.bool_expr(max(1, self.max_depth - depth))
            return self._num(max(1, self.max_depth - depth))
        if len(e) == 1:
            return e
        return tuple([e[0]] + [self._mut(a, depth + 1) if isinstance(a, tuple) else a for a in e[1:]])


# ---- segmentation driven by an arbitrary cohesion predicate over raw sensors ---------
def _sensors(frame, prev, r, c, nr, nc, is_orth):
    return {"c1": int(frame[r, c]), "c2": int(frame[nr, nc]),
            "p1": int(prev[r, c]),  "p2": int(prev[nr, nc]),
            "orth": 1.0 if is_orth else 0.0}


def segment_with_expr(frame, prev, expr, bg=0):
    """Union-find: two adjacent non-bg cells share a label iff expr coheres them."""
    H, W = frame.shape
    if prev is None:
        prev = frame
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    cells = [(r, c) for r in range(H) for c in range(W) if frame[r, c] != bg]
    for (r, c) in cells:
        find((r, c))
    for (r, c) in cells:
        for dr, dc, is_orth in [(0, 1, True), (1, 0, True), (1, 1, False), (1, -1, False)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and frame[nr, nc] != bg:
                env = _sensors(frame, prev, r, c, nr, nc, is_orth)
                if expr_bool(expr, env):
                    union((r, c), (nr, nc))
    labels = {}
    nxt = 0; canon = {}
    for (r, c) in cells:
        root = find((r, c))
        if root not in canon:
            canon[root] = nxt; nxt += 1
        labels[(r, c)] = canon[root]
    return labels


# ---- the realistic objective: get discriminating pairs' cohere-verdict right ---------
def discriminating_pairs(inst, colors=None):
    """Yield (p1,p2,same_object?) for adjacent cell-pairs flagged as the hard cases."""
    prev, cur, gt = inst
    H, W = cur.shape
    out = []
    for r in range(H):
        for c in range(W):
            if cur[r, c] == 0:
                continue
            for dr, dc in [(0, 1), (1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and cur[nr, nc] != 0 and (r, c) in gt and (nr, nc) in gt:
                    out.append(((r, c), (nr, nc), gt[(r, c)] == gt[(nr, nc)]))
    return out


def expr_fitness(expr, battery) -> float:
    ok = tot = 0
    for inst in battery:
        prev, cur, gt = inst
        for p1, p2, same in discriminating_pairs(inst):
            is_orth = (p1[0] == p2[0] or p1[1] == p2[1])
            env = _sensors(cur, prev, p1[0], p1[1], p2[0], p2[1], is_orth)
            ok += int(expr_bool(expr, env) == same); tot += 1
    return ok / max(1, tot)


def expr_size(e) -> int:
    if not isinstance(e, tuple):
        return 1
    return 1 + sum(expr_size(a) for a in e[1:] if isinstance(a, tuple)) + \
           sum(1 for a in e[1:] if not isinstance(a, tuple))


# ---- the evolver that INVENTS atoms --------------------------------------------------
class PixelExpressionEvolver:
    def __init__(self, seed=0, pop=40, max_depth=3, seed_exprs=None, parsimony=0.01):
        self.gen = PixelExpressionGenerator(seed=seed, max_depth=max_depth)
        self.rng = np.random.RandomState(seed + 7)
        self.pop = pop
        self.parsimony = parsimony          # Occam pressure: select compressible primitives
        self.population = [self.gen.bool_expr() for _ in range(pop)]
        for e in (seed_exprs or []):        # warm-start from inherited primitives
            self.population[self.rng.randint(pop)] = e

    def run(self, battery, gens=20):
        best, best_f = None, -1.0           # best by RAW fitness (what we report/promote)
        for _ in range(gens):
            raw = [(expr_fitness(e, battery), e) for e in self.population]
            # selection uses parsimony-regularized score; reporting uses raw fitness
            reg = sorted(((f - self.parsimony * expr_size(e), f, e) for f, e in raw),
                         key=lambda t: -t[0])
            if reg[0][1] > best_f or (abs(reg[0][1] - best_f) < 1e-9 and best is not None
                                      and expr_size(reg[0][2]) < expr_size(best)):
                best_f, best = reg[0][1], reg[0][2]
            survivors = [e for _, _, e in reg[:max(2, self.pop // 4)]]
            nxt = list(survivors)
            while len(nxt) < self.pop:
                parent = survivors[self.rng.randint(len(survivors))]
                nxt.append(self.gen.mutate(parent))
            self.population = nxt
        return best, best_f


# ---- the speciated germline: island-keyed promotion + gated migration ----------------
class SpeciatedGermline:
    MIN_PLAYS = 1
    EARN_RATE = 0.5      # a promoted primitive must beat chance on its island's task

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(_store_dir(), 'arc3_pixel_germline.json')
        self.islands = {}      # family_key -> {sig: {expr, name, plays, wins}}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    self.islands = json.load(f).get("islands", {})
        except Exception:
            self.islands = {}

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump({"islands": self.islands}, f)
        except Exception:
            pass

    def observe(self, family_key, expr, won: bool):
        """RLVR writeback: credit a candidate primitive within its island."""
        isl = self.islands.setdefault(family_key, {})
        sig = canonical_expr(expr)
        rec = isl.setdefault(sig, {"expr": list(_jsonable(expr)), "name": primitive_name(expr),
                                   "plays": 0, "wins": 0})
        rec["plays"] += 1; rec["wins"] += int(won)
        self._save()

    def promoted(self, family_key):
        """Named primitives that earned their keep in THIS island (speciation: per-family)."""
        isl = self.islands.get(family_key, {})
        out = []
        for sig, rec in isl.items():
            if rec["plays"] >= self.MIN_PLAYS and rec["wins"] / rec["plays"] >= self.EARN_RATE:
                out.append((rec["name"], _from_jsonable(rec["expr"]),
                            rec["wins"] / rec["plays"]))
        out.sort(key=lambda t: -t[2])
        return out

    def seed_exprs(self, family_key, k=4):
        return [e for _, e, _ in self.promoted(family_key)[:k]]

    def migrate(self, src_family, dst_family, min_rate=0.9):
        """GATED inter-island transfer (NOT automatic): copy only primitives that are
        strongly proven in the source island into the destination island as candidates.
        Speciation default is isolation; migration is an explicit, thresholded act."""
        moved = []
        for name, expr, rate in self.promoted(src_family):
            if rate >= min_rate:
                self.observe(dst_family, expr, won=True)   # enters dst as a credited candidate
                moved.append(name)
        return moved


def _jsonable(e):
    return [e[0]] + [list(_jsonable(a)) if isinstance(a, tuple) else a for a in e[1:]]

def _from_jsonable(x):
    return tuple(_from_jsonable(a) if isinstance(a, list) else a for a in x)

# ===================== arc3_compose.py =====================
"""
arc3_compose.py — feature INVENTION at the perception layer.

arc3_kernel tuned weights over a FIXED feature basis; it could discover novel rules
but never a novel *feature*, and family E (locally identical to D under static color
features) proved the basis itself is the ceiling. The thing missing — proven in
neither the fixed-menu PriorEvolver nor the fixed-basis kernel — is a loop that
COMPOSES new measurement features from a primitive vocabulary, the way stitch composes
new program abstractions from a base DSL. The one feature E needs is motion, which
requires a TEMPORAL primitive (prev-frame access) in the vocabulary.

This module supplies exactly that join:
  - a feature is an expression tree over atoms; atoms include STATIC ones (same color,
    adjacency, palette distance) and TEMPORAL ones (this cell changed since prev frame);
  - a carving genome = a set of such features + weights; cohere iff weighted sum > 0;
  - FeatureInventingEvolver mutates by REWEIGHTING and by COMPOSING new features
    (and/or/not of existing ones) — it grows its own feature space.

The decisive test (test_compose.py): a vocabulary WITH temporal atoms can compose a
"both cells moved" feature and separate D from E (breaking the static ceiling); a
vocabulary WITHOUT them cannot, and plateaus at the static ceiling — measuring that the
PRIMITIVE VOCABULARY, not the search, is now the binding constraint. Honest scope: the
atoms are still hand-supplied; composition invents features over them, not the atoms
themselves. That is the next ceiling, one flight up.
"""
import numpy as np
from itertools import combinations

# ---- primitive atoms: (c1,c2,is_orth,m1,m2) -> float -------------------------
# m1,m2 = did pos1/pos2 change since the previous frame (temporal access).
STATIC_ATOMS = ["same", "orth", "diag", "diff1", "diff2"]
TEMPORAL_ATOMS = ["moved1", "moved2"]

def _atom(name, c1, c2, is_orth, m1, m2):
    if name == "same":   return float(c1 == c2)
    if name == "orth":   return float(is_orth)
    if name == "diag":   return float(not is_orth)
    if name == "diff1":  return float(abs(c1 - c2) <= 1)
    if name == "diff2":  return float(abs(c1 - c2) <= 2)
    if name == "moved1": return float(m1)
    if name == "moved2": return float(m2)
    return 0.0

def eval_feature(feat, c1, c2, is_orth, m1, m2) -> float:
    """feat is ('atom',name) | ('and',f,f) | ('or',f,f) | ('not',f)."""
    tag = feat[0]
    if tag == "atom":
        return _atom(feat[1], c1, c2, is_orth, m1, m2)
    if tag == "and":
        return eval_feature(feat[1], c1, c2, is_orth, m1, m2) * eval_feature(feat[2], c1, c2, is_orth, m1, m2)
    if tag == "or":
        a = eval_feature(feat[1], c1, c2, is_orth, m1, m2); b = eval_feature(feat[2], c1, c2, is_orth, m1, m2)
        return max(a, b)
    if tag == "not":
        return 1.0 - eval_feature(feat[1], c1, c2, is_orth, m1, m2)
    return 0.0


# registry-aware eval: promoted pixel-primitives (name -> pixel-expr) evaluate from raw
# cross-frame sensors {c1,c2,p1,p2,orth}; legacy atoms ignore p1,p2 (backward compatible).
try:
    _eval_px = globals().get('eval_expr')  # inlined
except Exception:
    _eval_px = None

def eval_feature_reg(feat, c1, c2, is_orth, m1, m2, p1, p2, registry) -> float:
    tag = feat[0]
    if tag == "atom":
        name = feat[1]
        if registry and name in registry and _eval_px is not None:
            env = {"c1": c1, "c2": c2, "p1": p1, "p2": p2, "orth": 1.0 if is_orth else 0.0}
            return float(bool(_eval_px(registry[name], env)))
        return _atom(name, c1, c2, is_orth, m1, m2)
    if tag == "and":
        return eval_feature_reg(feat[1], c1, c2, is_orth, m1, m2, p1, p2, registry) * \
               eval_feature_reg(feat[2], c1, c2, is_orth, m1, m2, p1, p2, registry)
    if tag == "or":
        return max(eval_feature_reg(feat[1], c1, c2, is_orth, m1, m2, p1, p2, registry),
                   eval_feature_reg(feat[2], c1, c2, is_orth, m1, m2, p1, p2, registry))
    if tag == "not":
        return 1.0 - eval_feature_reg(feat[1], c1, c2, is_orth, m1, m2, p1, p2, registry)
    return 0.0

def feature_str(feat) -> str:
    t = feat[0]
    if t == "atom": return feat[1]
    if t == "not":  return f"not({feature_str(feat[1])})"
    return f"{t}({feature_str(feat[1])},{feature_str(feat[2])})"

def feature_uses_temporal(feat) -> bool:
    if feat[0] == "atom":
        return feat[1] in TEMPORAL_ATOMS
    return any(feature_uses_temporal(f) for f in feat[1:])


_NBRS8 = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


class ComposableCarving:
    """Carving rule = weighted sum of composed features; cohere iff sum + bias > 0."""
    def __init__(self, features, weights, bias=0.0, registry=None):
        self.features = list(features)
        self.weights = np.asarray(weights, dtype=np.float64)
        self.bias = float(bias)
        self.registry = registry or {}        # name -> pixel-expr for promoted primitives

    def cohere(self, c1, c2, is_orth, m1, m2, p1=None, p2=None) -> bool:
        s = self.bias
        if self.registry:
            if p1 is None: p1 = c1
            if p2 is None: p2 = c2
            for f, w in zip(self.features, self.weights):
                if w != 0.0:
                    s += w * eval_feature_reg(f, c1, c2, is_orth, m1, m2, p1, p2, self.registry)
        else:
            for f, w in zip(self.features, self.weights):
                if w != 0.0:
                    s += w * eval_feature(f, c1, c2, is_orth, m1, m2)
        return s > 0.0

    def to_dict(self):
        def j(feat):
            return [feat[0]] + [j(f) if isinstance(f, tuple) else f for f in feat[1:]]
        d = {"features": [j(f) for f in self.features],
             "weights": [float(w) for w in self.weights], "bias": float(self.bias)}
        if self.registry:
            d["registry"] = {k: (list(v) if isinstance(v, tuple) else v)
                             for k, v in self.registry.items()}
        return d

    @staticmethod
    def from_dict(d):
        def t(x):
            return tuple(t(e) if isinstance(e, list) else e for e in x)
        reg = {k: t(v) for k, v in d.get("registry", {}).items()}
        return ComposableCarving([t(f) for f in d["features"]], d["weights"],
                                 d.get("bias", 0.0), registry=reg)

    def segment_labels(self, frame: np.ndarray, prev: np.ndarray = None, bg: int = 0):
        H, W = frame.shape
        has_prev = prev is not None and prev.shape == frame.shape
        moved = (frame != prev) if has_prev else np.zeros_like(frame, bool)
        cells = [(r, c) for r in range(H) for c in range(W) if frame[r, c] != bg]
        idx = {p: i for i, p in enumerate(cells)}
        parent = list(range(len(cells)))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        for (r, c) in cells:
            v1 = int(frame[r, c]); m1 = bool(moved[r, c])
            pp1 = int(prev[r, c]) if has_prev else v1
            for (dr, dc) in _NBRS8:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and frame[nr, nc] != bg:
                    is_orth = (dr == 0 or dc == 0)
                    pp2 = int(prev[nr, nc]) if has_prev else int(frame[nr, nc])
                    if self.cohere(v1, int(frame[nr, nc]), is_orth, m1,
                                   bool(moved[nr, nc]), pp1, pp2):
                        parent[find(idx[(r, c)])] = find(idx[(nr, nc)])
        return {p: find(idx[p]) for p in cells}


def partition_agreement(cells, pred, gt) -> float:
    if len(cells) < 2:
        return 1.0
    agree = total = 0
    for a, b in combinations(cells, 2):
        total += 1
        if (pred[a] == pred[b]) == (gt[a] == gt[b]):
            agree += 1
    return agree / total

def fitness(carver, battery) -> float:
    s = 0.0
    for prev, cur, gt in battery:
        s += partition_agreement(list(gt.keys()), carver.segment_labels(cur, prev), gt)
    return s / max(1, len(battery))


class FeatureInventingEvolver:
    """Evolves ComposableCarving genomes. Mutation REWEIGHTS and COMPOSES new features
    from `vocab` atoms — so the reachable feature space depends on which atoms exist."""
    def __init__(self, vocab=None, pop=30, sigma=0.6, seed=0, max_feats=8, max_depth=2,
                 seed_features=None, fitness_fn=None):
        self.vocab = list(vocab) if vocab is not None else (STATIC_ATOMS + TEMPORAL_ATOMS)
        self.seed_features = list(seed_features) if seed_features else []   # invented library
        self.pop = pop; self.sigma = sigma; self.max_feats = max_feats; self.max_depth = max_depth
        self.fitness_fn = fitness_fn or fitness
        self.rng = np.random.RandomState(seed)
        self.population = [self._random_genome() for _ in range(pop)]

    def _atom_feat(self):
        # a building block is an atom OR a previously-invented feature (library reuse)
        if self.seed_features and self.rng.rand() < 0.35:
            return self.seed_features[self.rng.randint(len(self.seed_features))]
        return ("atom", self.vocab[self.rng.randint(len(self.vocab))])

    def _random_feature(self, depth=0):
        if depth >= self.max_depth or self.rng.rand() < 0.5:
            return self._atom_feat()
        op = ["and", "or", "not"][self.rng.randint(3)]
        if op == "not":
            return ("not", self._random_feature(depth + 1))
        return (op, self._random_feature(depth + 1), self._random_feature(depth + 1))

    def _random_genome(self):
        k = self.rng.randint(2, 4)
        feats = [self._atom_feat() for _ in range(k)]
        w = self.rng.randn(k)
        return ComposableCarving(feats, w, bias=self.rng.randn() * 0.5)

    def _mutate(self, g: ComposableCarving) -> ComposableCarving:
        feats = list(g.features); w = list(g.weights); bias = g.bias
        roll = self.rng.rand()
        if roll < 0.45:                                   # reweight
            i = self.rng.randint(len(w)); w[i] += self.rng.randn() * self.sigma
        elif roll < 0.80 and len(feats) < self.max_feats: # COMPOSE a new feature (grow basis)
            feats.append(self._random_feature()); w.append(self.rng.randn() * 0.5)
        elif roll < 0.90 and len(feats) > 1:              # drop a feature
            i = self.rng.randint(len(feats)); feats.pop(i); w.pop(i)
        else:                                             # nudge bias
            bias += self.rng.randn() * self.sigma
        return ComposableCarving(feats, np.array(w), bias)

    def step(self, battery):
        scored = sorted(((self.fitness_fn(g, battery), g) for g in self.population), key=lambda t: -t[0])
        elite_n = max(2, self.pop // 4)
        elites = [g for _, g in scored[:elite_n]]
        children = []
        while len(elites) + len(children) < self.pop:
            children.append(self._mutate(elites[self.rng.randint(len(elites))]))
        self.population = elites + children
        return scored[0]

    def run(self, battery, gens=60):
        best, hist = None, []
        for _ in range(gens):
            bf, bg = self.step(battery); hist.append(bf); best = bg
        return best, hist

# ===================== arc3_openended.py =====================
"""
arc3_openended.py — the capstone: open-ended growth of the FEATURE alphabet.

Every prior layer either tuned weights over a fixed basis (arc3_kernel) or composed
features over a fixed ATOM vocabulary (arc3_compose). The vocabulary itself never grew:
the alphabet was hand-authored, the ceiling no selection could break. This module
closes that seam — the one genuinely-missing piece across both the ARC agent and the
Ouroboros repo — by making agent-INVENTED features persist and reseed the next
generation:

  invent (compose) -> score by RLVR (win-credit) -> if novel AND earning, PERSIST to a
  durable germline -> warm-start the next agent's vocabulary with it -> repeat.

Storage = a single JSON file under the working dir (taken on good faith as durable
across runs). No SQLite. Degrades to in-memory if the path is unwritable, so it can
never hard-fail a submission.
"""
import os, json
from collections import defaultdict
from typing import List, Optional

# feature trees use the arc3_compose schema: ('atom',name)|('and',f,f)|('or',f,f)|('not',f)


def canonical(feat) -> str:
    """Structural signature: normal form so commutative ops dedup (the LIKE detector)."""
    tag = feat[0]
    if tag == "atom":
        return feat[1]
    if tag == "not":
        return f"not({canonical(feat[1])})"
    parts, stack = [], [feat[1], feat[2]]
    while stack:
        f = stack.pop()
        if f[0] == tag:
            stack.extend([f[1], f[2]])
        else:
            parts.append(canonical(f))
    return f"{tag}(" + ",".join(sorted(parts)) + ")"


def _to_jsonable(feat):
    return [feat[0]] + [_to_jsonable(f) if isinstance(f, tuple) else f for f in feat[1:]]

def _from_jsonable(x):
    return tuple(_from_jsonable(e) if isinstance(e, list) else e for e in x)

def uses_temporal(feat, temporal_atoms=("moved1", "moved2")) -> bool:
    if feat[0] == "atom":
        return feat[1] in temporal_atoms
    return any(uses_temporal(f, temporal_atoms) for f in feat[1:])

def is_composite(feat) -> bool:
    return feat[0] != "atom"


class InventedFeatureStore:
    """Durable JSON germline for agent-invented features, scored by RLVR win-credit."""

    MIN_PLAYS = 1
    EARN_RATE = 0.34

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(_store_dir(), 'arc3_invented_features.json')
        # feats: sig -> {expr, plays, wins, temporal}
        self.feats = {}
        self.op_credit = defaultdict(lambda: 1.0)
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    d = json.load(f)
                self.feats = d.get("feats", {})
                for op, c in d.get("op_credit", {}).items():
                    self.op_credit[op] = float(c)
        except Exception:
            self.feats = {}

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump({"feats": self.feats, "op_credit": dict(self.op_credit)}, f)
        except Exception:
            pass        # in-memory only if unwritable: never hard-fail

    def is_novel(self, feat) -> bool:
        if not is_composite(feat):
            return False
        return canonical(feat) not in self.feats

    def observe(self, feat, won: bool):
        if not is_composite(feat):
            return
        sig = canonical(feat)
        e = self.feats.setdefault(sig, {"expr": _to_jsonable(feat), "plays": 0, "wins": 0,
                                        "temporal": int(uses_temporal(feat))})
        e["plays"] += 1
        if won:
            e["wins"] += 1
            for op in self._ops_in(feat):
                self.op_credit[op] += 1.0
        self._save()

    def _ops_in(self, feat):
        if feat[0] == "atom":
            return []
        return [feat[0]] + [op for f in feat[1:] for op in self._ops_in(f)]

    def top_features(self, k: int = 8, prefer_temporal: bool = True) -> List[tuple]:
        scored = []
        for sig, e in self.feats.items():
            plays = e.get("plays", 0)
            if plays < self.MIN_PLAYS:
                continue
            rate = e.get("wins", 0) / plays
            if rate >= self.EARN_RATE:
                score = rate + (0.25 if (prefer_temporal and e.get("temporal")) else 0.0)
                scored.append((score, e["expr"]))
        scored.sort(reverse=True, key=lambda t: t[0])
        out = []
        for _, expr in scored[:k]:
            try:
                out.append(_from_jsonable(expr))
            except Exception:
                continue
        return out

    def op_weights(self) -> dict:
        ops = ["and", "or", "not"]
        tot = sum(self.op_credit[o] for o in ops)
        return {o: self.op_credit[o] / tot for o in ops} if tot > 0 else {o: 1 / 3 for o in ops}

    # ---- validated CARVER genomes (complete features+weights), keyed by family ----
    def store_carver(self, family_key: str, genome: dict, won: bool):
        """Persist a complete evolved carver genome so a live agent can inherit a
        WORKING carver (correct weights), not just raw features."""
        carvers = getattr(self, "_carvers", None)
        if carvers is None:
            self._carvers = carvers = self.feats.get("__carvers__", {}) if isinstance(
                self.feats.get("__carvers__"), dict) else {}
        lst = carvers.setdefault(family_key, [])
        key = json.dumps(genome, sort_keys=True)
        for rec in lst:
            if rec["key"] == key:
                rec["plays"] += 1; rec["wins"] += int(won)
                break
        else:
            lst.append({"key": key, "genome": genome, "plays": 1, "wins": int(won)})
        self.feats["__carvers__"] = carvers
        self._save()

    def best_carver(self, family_key: str):
        """Return the highest win-rate carver genome dict for a family, or None."""
        carvers = self.feats.get("__carvers__", {})
        lst = carvers.get(family_key, [])
        best, best_rate = None, -1.0
        for rec in lst:
            rate = rec["wins"] / rec["plays"] if rec["plays"] else 0.0
            if rate > best_rate:
                best_rate, best = rate, rec["genome"]
        return best

# ===================== arc3_metaevolve.py =====================
"""
arc3_metaevolve.py — open-ended self-modification under empirical containment.

The Oracle (in the Ouroboros lineage) chooses among a FIXED menu of ~5 interventions
(unlock-primitive, lower-threshold, increase-budget, ...). That is the de-novo-invention
seam at the META level: the set of self-modifications the system can attempt is
hand-authored, exactly as the carver's atoms were before the pixel-expression substrate.

This module closes that seam the same way pixelgen closed the object-level one, but it
does NOT pretend to be a Godel machine. A Godel machine commits a self-rewrite only after
PROVING it raises expected utility — which is impossible here, because ARC's utility
function (the win condition) is hidden and discovered empirically. So instead of a proof
we use the honest empirical stand-in: an intervention is committed only if its measured
improvement clears a VARIANCE-AWARE lower-confidence-bound across multiple seeds (it must
be robustly good, not lucky-once), and every commit is REVERSIBLE (rollback = the
blast-radius the proof would otherwise make unnecessary).

  invent (compose interventions over an op-grammar)
    -> score by measured improvement across N seeds (lower-confidence-bound, not mean)
    -> commit only if robustly positive; else discard
    -> promote robust earners to a persisted library (the menu GROWS, open-ended)
    -> warm-start the next round from the library
    -> ROLLBACK any committed intervention that later degrades on held-out episodes.

This is meta-evolution of the system's own configuration: the menu of self-modifications
is no longer fixed, yet the loop can never destabilize, because commits are gated by
robust measured improvement and bounded by rollback. Pure numpy + stdlib json. No SQLite.
"""
import os, json
import numpy as np
from typing import List, Optional, Tuple

# An intervention is a program over knobs (the agent's own tunable configuration):
#   ("inc", k, a) | ("dec", k, a) | ("set", k, v) | ("seq", intv, intv)
# Applying it transforms a state vector (normalized knobs in [0,1]).


def apply_intervention(state: np.ndarray, intv) -> np.ndarray:
    s = state.copy()
    tag = intv[0]
    if tag == "inc":
        k, a = intv[1], intv[2]; s[k] = min(1.0, s[k] + a)
    elif tag == "dec":
        k, a = intv[1], intv[2]; s[k] = max(0.0, s[k] - a)
    elif tag == "set":
        k, v = intv[1], intv[2]; s[k] = float(np.clip(v, 0.0, 1.0))
    elif tag == "seq":
        s = apply_intervention(apply_intervention(s, intv[1]), intv[2])
    return s


def intervention_size(intv) -> int:
    if intv[0] == "seq":
        return 1 + intervention_size(intv[1]) + intervention_size(intv[2])
    return 1


def canonical_intervention(intv) -> str:
    tag = intv[0]
    if tag == "seq":
        # seq is order-sensitive in general; keep order but normalize nesting
        return f"seq({canonical_intervention(intv[1])},{canonical_intervention(intv[2])})"
    return f"{tag}({intv[1]},{round(float(intv[2]),3)})"


# ---- the generative grammar over self-modification ops -------------------------------
class InterventionGenerator:
    def __init__(self, n_knobs, seed=0, max_depth=3, amounts=(0.1, 0.2, 0.3)):
        self.n = n_knobs
        self.rng = np.random.RandomState(seed)
        self.max_depth = max_depth
        self.amounts = amounts

    def _primitive(self):
        op = ["inc", "dec", "set"][self.rng.randint(3)]
        k = self.rng.randint(self.n)
        if op == "set":
            return ("set", k, float(self.rng.rand()))
        return (op, k, float(self.amounts[self.rng.randint(len(self.amounts))]))

    def random(self, depth=None):
        depth = self.max_depth if depth is None else depth
        if depth <= 0 or self.rng.rand() < 0.45:
            return self._primitive()
        return ("seq", self.random(depth - 1), self.random(depth - 1))   # COMPOSE

    def mutate(self, intv):
        if self.rng.rand() < 0.3:
            return self.random()
        return self._mut(intv, 0)

    def _mut(self, intv, d):
        if self.rng.rand() < 0.3:
            return self.random(max(0, self.max_depth - d))
        if intv[0] == "seq":
            return ("seq", self._mut(intv[1], d + 1), self._mut(intv[2], d + 1))
        # perturb a primitive
        if intv[0] in ("inc", "dec") and self.rng.rand() < 0.5:
            return (intv[0], intv[1], float(self.amounts[self.rng.randint(len(self.amounts))]))
        return self._primitive()


# ---- the variance-aware gate: robust improvement, not lucky improvement ---------------
def robust_gain(intv, base_state, perf_fn, rng, n_seeds=8, z=1.0):
    """Lower-confidence-bound of (perf(after) - perf(before)) across noisy trials.
    z>0 penalizes variance: an intervention that's great-on-average but swingy is
    NOT robustly good. This is the empirical stand-in for a proof of improvement."""
    after = apply_intervention(base_state, intv)
    gains = np.array([perf_fn(after, rng) - perf_fn(base_state, rng) for _ in range(n_seeds)])
    return float(gains.mean() - z * gains.std())


# ---- the meta-evolver: invents composed interventions under the gate -----------------
class MetaEvolver:
    def __init__(self, n_knobs, seed=0, pop=40, parsimony=0.01, seed_intervs=None,
                 allow_compose=True, max_depth=3):
        self.gen = InterventionGenerator(n_knobs, seed=seed,
                                         max_depth=max_depth if allow_compose else 0)
        self.rng = np.random.RandomState(seed + 11)
        self.pop = pop
        self.parsimony = parsimony
        self.population = [self.gen.random() for _ in range(pop)]
        for iv in (seed_intervs or []):
            self.population[self.rng.randint(pop)] = iv

    def run(self, base_state, perf_fn, gens=20, n_seeds=8, z=1.0):
        best, best_g = None, -1e9
        rng = np.random.RandomState(0)
        for _ in range(gens):
            scored = []
            for iv in self.population:
                g = robust_gain(iv, base_state, perf_fn, rng, n_seeds=n_seeds, z=z)
                scored.append((g - self.parsimony * intervention_size(iv), g, iv))
            scored.sort(key=lambda t: -t[0])
            if scored[0][1] > best_g:
                best_g, best = scored[0][1], scored[0][2]
            surv = [iv for _, _, iv in scored[:max(2, self.pop // 4)]]
            nxt = list(surv)
            while len(nxt) < self.pop:
                nxt.append(self.gen.mutate(surv[self.rng.randint(len(surv))]))
            self.population = nxt
        return best, best_g


# ---- the persisted, island-keyed intervention library (the GROWING menu) -------------
class InterventionGermline:
    MIN_TRIALS = 3       # an intervention must prove robust across >=3 evaluations
    COMMIT_LCB = 0.0     # commit only if robust lower-confidence-bound > 0

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(_store_dir(), 'arc3_interventions.json')
        self.islands = {}    # pathology/family -> {sig: {intv, trials, lcb_sum, committed}}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    self.islands = json.load(f).get("islands", {})
        except Exception:
            self.islands = {}

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump({"islands": self.islands}, f)
        except Exception:
            pass

    def observe(self, island, intv, lcb):
        """Record a robust-gain measurement for a (composed) intervention."""
        isl = self.islands.setdefault(island, {})
        sig = canonical_intervention(intv)
        rec = isl.setdefault(sig, {"intv": _jsonable(intv), "trials": 0,
                                   "lcb_sum": 0.0, "committed": False})
        rec["trials"] += 1
        rec["lcb_sum"] += float(lcb)
        rec["committed"] = (rec["trials"] >= self.MIN_TRIALS and
                            rec["lcb_sum"] / rec["trials"] > self.COMMIT_LCB)
        self._save()

    def promoted(self, island):
        """Interventions that ROBUSTLY earned commit status (the grown menu)."""
        isl = self.islands.get(island, {})
        out = [(sig, _from_jsonable(r["intv"]), r["lcb_sum"] / max(1, r["trials"]))
               for sig, r in isl.items() if r.get("committed")]
        out.sort(key=lambda t: -t[2])
        return out

    def seed_intervs(self, island, k=4):
        return [iv for _, iv, _ in self.promoted(island)[:k]]

    def candidates(self, island, k=6):
        """Top not-yet-committed interventions, for re-evaluation toward MIN_TRIALS."""
        isl = self.islands.get(island, {})
        out = [(sig, _from_jsonable(r["intv"]), r["lcb_sum"] / max(1, r["trials"]))
               for sig, r in isl.items()
               if not r.get("committed") and r["lcb_sum"] / max(1, r["trials"]) > self.COMMIT_LCB]
        out.sort(key=lambda t: -t[2])
        return out[:k]

    def is_committed(self, island, intv) -> bool:
        isl = self.islands.get(island, {})
        rec = isl.get(canonical_intervention(intv))
        return bool(rec and rec.get("committed"))

    def rollback(self, island, intv):
        """Demote a committed intervention that later degraded (blast-radius revert)."""
        isl = self.islands.get(island, {})
        sig = canonical_intervention(intv)
        if sig in isl:
            isl[sig]["committed"] = False
            isl[sig]["lcb_sum"] = min(isl[sig]["lcb_sum"], -1.0)  # poison so it won't re-commit
            self._save()
            return True
        return False


# ---- the Oracle wrapper: diagnose -> propose -> gate-commit -> rollback ---------------
class MetaController:
    """Wraps the meta-evolver + germline as a drop-in upgrade to the fixed-menu Oracle.
    propose_and_commit returns (new_state, committed_intervention) — committing ONLY a
    robustly-improving intervention, and leaving state untouched (safe no-op) otherwise.

    CONTRACT (the integration gap, stated so nobody trips it): perf_fn must be a PURE
    function of cached telemetry, never a live game rollout. Meta-evolution runs OFFLINE
    between episodes/sessions, not inside an episode — there is no rollout budget for
    pop*gens*seeds simulations mid-game, and no counterfactual to measure live. Use
    EpisodeTelemetry.perf_fn (below): it interpolates logged (knobs, outcome) pairs in
    O(n_logged), and its bootstrap resampling makes robust_gain's variance reflect REAL
    outcome uncertainty given the data — so the lower-confidence-bound gate is honest."""

    def __init__(self, n_knobs, germline: Optional[InterventionGermline] = None):
        self.n = n_knobs
        self.germ = germline or InterventionGermline()

    def propose_and_commit(self, state, perf_fn, island="default",
                           seed=0, gens=14, n_seeds=10, z=1.0):
        # re-evaluate existing candidates first so they accumulate trials toward MIN_TRIALS
        rng = np.random.RandomState(seed + 99)
        for sig, iv, _ in self.germ.candidates(island):
            self.germ.observe(island, iv, robust_gain(iv, state, perf_fn, rng,
                                                       n_seeds=n_seeds, z=z))
        best, lcb = MetaEvolver(self.n, seed=seed,
                                seed_intervs=self.germ.seed_intervs(island)).run(
            state, perf_fn, gens=gens, n_seeds=n_seeds, z=z)
        if best is None:
            return state, None
        self.germ.observe(island, best, lcb)
        committed = self.germ.is_committed(island, best)
        if committed and lcb > self.germ.COMMIT_LCB:
            return apply_intervention(state, best), best
        return state, None                              # not yet robustly proven -> no-op


class EpisodeTelemetry:
    """Cached episode outcomes. The ONLY legitimate source for a meta-evolution perf_fn.

    The agent logs (knobs-used, outcome) per episode; perf_fn(state) is kernel regression
    over that log. Three properties make it safe as well as cheap:

    - AGGREGATION: episodes are binned into knob-cells (visit count + outcome mean). This is
      the calibration fix: the bootstrap/uncertainty reads DISTINCT-cell coverage, so 1000
      repeats of one config cannot masquerade as 1000 independent observations and tighten
      the lower-confidence-bound. Repetition refines a cell's mean; it does not add coverage.
    - AGE DECAY: kernel weight is multiplied by a half-life decay in episode-time, so stale
      episodes from an earlier regime are down-weighted IN THE ESTIMATOR — not merely by
      deletion. (Knob-distance alone never down-weights a stale-but-nearby config; this does.)
    - BOUNDED COST: cells are capped (oldest-by-time evicted), so a long competition run
      stays O(n_cells) per call instead of growing unboundedly with episodes.

    Uncertainty: se = sqrt(p(1-p) / (coverage + shrink)), where coverage = total kernel mass
    over DISTINCT cells near the query. Far from data -> coverage->0 -> wide (honest
    extrapolation uncertainty); many distinct nearby cells -> tight; many repeats of ONE
    cell -> coverage stays ~1 -> stays wide. O(n_cells), never a rollout."""

    def __init__(self, path: Optional[str] = None, n_knobs=6, bandwidth=0.25, prior=0.5,
                 resolution=0.1, max_cells=1000, age_halflife=500.0, shrink=2.0):
        self.path = path or os.path.join(_store_dir(), 'arc3_episode_log.json')
        self.n = n_knobs; self.bw = bandwidth; self.prior = prior
        self.res = resolution; self.max_cells = max_cells
        self.age_halflife = age_halflife; self.shrink = shrink
        self.cells = {}      # cell_key -> {"knobs":[...], "wins":float, "visits":int, "t":int}
        self.t = 0
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    d = json.load(f)
                self.cells = {tuple(map(int, k.split(','))): v
                              for k, v in d.get("cells", {}).items()}
                self.t = int(d.get("t", 0))
        except Exception:
            self.cells = {}; self.t = 0

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump({"cells": {",".join(map(str, k)): v for k, v in self.cells.items()},
                           "t": self.t}, f)
        except Exception:
            pass

    def _key(self, knobs):
        return tuple(int(round(float(k) / self.res)) for k in knobs)

    def record(self, knobs, outcome: float):
        """Bin an episode into its knob-cell (aggregation, not append)."""
        self.t += 1
        key = self._key(knobs)
        c = self.cells.get(key)
        if c is None:
            c = {"knobs": [float(x) for x in np.asarray(knobs).tolist()],
                 "wins": 0.0, "visits": 0, "t": self.t}
            self.cells[key] = c
        c["wins"] += float(outcome); c["visits"] += 1; c["t"] = self.t
        if len(self.cells) > self.max_cells:                 # evict oldest by time (recency)
            oldest = min(self.cells, key=lambda k: self.cells[k]["t"])
            if oldest != key:
                del self.cells[oldest]
        self._save()

    def _contributions(self, state):
        """Per-DISTINCT-cell (p, weight) with knob-kernel x age-decay weighting."""
        out = []
        for c in self.cells.values():
            d2 = float(np.sum((np.asarray(c["knobs"]) - state) ** 2))
            wk = np.exp(-d2 / (2 * self.bw ** 2))
            age = self.t - c["t"]
            wa = 0.5 ** (age / self.age_halflife)
            w = wk * wa
            if w > 1e-6 and c["visits"] > 0:
                out.append((c["wins"] / c["visits"], w))
        return out

    def estimate(self, state):
        """Point estimate + (mean, coverage) — coverage = distinct-cell kernel mass."""
        contrib = self._contributions(np.asarray(state))
        if not contrib:
            return self.prior, 0.0
        W = sum(w for _, w in contrib)
        mean = (sum(p * w for p, w in contrib) + self.shrink * self.prior) / (W + self.shrink)
        return mean, W

    def perf_fn(self):
        """Returns perf(state, rng): a posterior-predictive sample whose spread reflects
        DISTINCT-cell coverage (not episode count). Pure, O(n_cells)."""
        def perf(state, rng):
            mean, coverage = self.estimate(state)
            se = np.sqrt(max(mean * (1 - mean), 0.01) / (coverage + self.shrink))
            return float(mean + rng.normal(0, se))
        return perf


def _jsonable(iv):
    if iv[0] == "seq":
        return ["seq", _jsonable(iv[1]), _jsonable(iv[2])]
    return [iv[0], iv[1], iv[2]]

def _from_jsonable(x):
    if x[0] == "seq":
        return ("seq", _from_jsonable(x[1]), _from_jsonable(x[2]))
    return (x[0], int(x[1]), float(x[2]))

# ===================== nsm_strategy.py =====================
"""nsm_strategy.py - the BINDER as a story-generator over an NSM grammar.

The missing 'generator' the whole project circled: a librarian who, dropped into a new
game, COMPOSES a navigation strategy on the spot from primitives -- "if I see an agent,
move toward the goal; if I see clickable buttons, press the highest-impact one; if the
world moves on its own, wait for the right moment; otherwise explore" -- and, when that
story stops paying off, GENERATES a different one. The strategy is a procedure composed
from the grammar, NOT a stored fact. That is the binder.

This is the Serendipity Engine's pattern applied to action: a grammar of primitives, a
generation pipeline conditioned on what's perceived + cross-game priors, failure-mode
guardrails that trigger regeneration, and the one rule that matters -- when stale, VARY
(regression to the mean is the failure mode; the constraint is the generativity).

NSM grammar
-----------
Perceptual primitives:  SEE(agent), SEE(clickable), SEE(change), SEE(autonomous),
                        SEE(goal_object), COUNT(objects)
Action primitives:      MOVE(toward), CLICK(impact), WAIT, EXPLORE
Control primitives:     IF(cond)->DO  BECAUSE(hypothesis)   (ordered rule list = the story)
"""
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Rule:
    """IF condition THEN action BECAUSE hypothesis -- one clause of the story."""
    cond: str            # perceptual predicate name (SEE_AGENT, SEE_CLICKABLE, ...)
    action: str          # NSM action primitive (MOVE, CLICK, WAIT, EXPLORE)
    because: str         # hypothesis label (reach / button / timing / coverage)


class Strategy:
    """A generated story: an ordered list of rules. decide() fires the first whose
    condition the current percept satisfies."""
    def __init__(self, rules, variant=0):
        self.rules = rules
        self.variant = variant

    def decide(self, percept: dict):
        for r in self.rules:
            if percept.get(r.cond, False):
                return r.action, r.because
        return "EXPLORE", "coverage"

    def __repr__(self):
        body = " ; ".join(f"IF {r.cond}->{r.action}({r.because})" for r in self.rules)
        return f"Strategy#{self.variant}[{body}]"


# The hypothesis pool: each is a (perceptual-condition, action, hypothesis) clause.
# A strategy is a PERMUTATION/SELECTION over these, conditioned on perception + priors.
_POOL = [
    Rule("SEE_GOAL_OBJECT", "MOVE",  "reach"),     # agent + a distinct target -> navigate
    Rule("SEE_CLICKABLE",   "CLICK", "button"),    # clickable elements -> press buttons
    Rule("SEE_AUTONOMOUS",  "WAIT",  "timing"),    # world moves on its own -> time it
    Rule("SEE_AGENT",       "MOVE",  "reach"),     # an agent but no clear goal -> probe-move
]


import math


class TaskBelief:
    """The BAMDP belief b_t = p(task-type | history): a posterior over which BASIN-FAMILY
    this game's win condition lives in (reach / button / timing). Starts from the cross-game
    prior (the 'seedline'), and SHARPENS as within-game evidence accumulates -- the time-
    integration the static generator priors lacked. The strategy generator conditions on
    this posterior, so accumulated evidence (not just the instantaneous percept) shapes the
    strategy. This is Stage 0 of the feasibility assessment (approximate BAMDP), NOT the
    explicit-geometry route (no Lyapunov/manifold machinery -- the report flagged those as
    unproven research bets).

    Evidence cues are log-likelihood nudges, kept small so a single observation can't
    collapse the belief; the posterior concentrates only under repeated, consistent evidence.
    """
    TYPES = ("reach", "button", "timing")

    def __init__(self, prior: dict | None = None):
        # prior: cross-game success frequencies from policy memory (the seedline). Uniform
        # if absent. Stored as log-probabilities.
        if prior:
            tot = sum(prior.get(t, 0.0) for t in self.TYPES) or 1.0
            self.logp = {t: math.log(1e-3 + prior.get(t, 0.0) / tot) for t in self.TYPES}
        else:
            self.logp = {t: 0.0 for t in self.TYPES}
        self._n_evidence = 0

    def update(self, cues: dict):
        """cues: {type: strength in ~[-1,1]} log-likelihood nudges. Positive = evidence FOR
        that basin-family. Bounded step so the posterior sharpens gradually, not on one frame."""
        STEP = 0.35
        CAP = 2.5                                    # max log-odds gap -> top posterior ~0.86
        moved = False
        for t, strength in cues.items():
            if t in self.logp and strength:
                self.logp[t] += STEP * max(-1.0, min(1.0, strength))
                moved = True
        if moved:
            self._n_evidence += 1
            m = max(self.logp.values())              # renormalize for numerical stability
            for t in self.logp:
                # clamp to [-CAP, 0]: a game can be BUTTON-and-TIMING (e.g. ft09); without
                # this the belief saturates to one corner and loses the secondary family.
                self.logp[t] = max(-CAP, self.logp[t] - m)

    def posterior(self) -> dict:
        ex = {t: math.exp(v) for t, v in self.logp.items()}
        z = sum(ex.values()) or 1.0
        return {t: ex[t] / z for t in self.TYPES}

    def top(self):
        p = self.posterior()
        return max(p, key=p.get)

    def concentration(self) -> float:
        """How sharp the belief is: 0 = uniform (no idea), 1 = certain. Lets the policy know
        whether to explore-to-disambiguate or commit-and-flow."""
        p = list(self.posterior().values())
        ent = -sum(x * math.log(x + 1e-12) for x in p)
        return 1.0 - ent / math.log(len(p))


class StrategyGenerator:
    """Composes a Strategy from percept + cross-game priors, and regenerates a VARIED
    one when the current story stalls (the anti-regression rule)."""

    def __init__(self, priors: Optional[dict] = None):
        # priors: {'reach':w, 'button':w, 'timing':w, ...} success frequencies from
        # the policy memory (substrate-general, not mechanics). Bias ORDER, not content.
        self.priors = priors or {}

    def generate(self, percept: dict, variant: int = 0, belief: dict | None = None) -> Strategy:
        # keep only clauses whose perceptual condition is plausibly relevant; if none,
        # the strategy degenerates to EXPLORE (the always-available fallback).
        applicable = [r for r in _POOL if percept.get(r.cond, False) or r.cond == "SEE_AGENT"]
        if not applicable:
            applicable = list(_POOL)
        # rank by the BELIEF posterior over basin-family (b_t) if given -- so accumulated
        # evidence about what kind of game this is orders the strategy -- else fall back to
        # the static cross-game prior. belief subsumes prior (prior = initial belief).
        weight = belief if belief else self.priors
        applicable.sort(key=lambda r: -weight.get(r.because, 1.0))
        # VARIATION (the 'keep it strange' rule): each regeneration rotates the order so
        # a stalled story is replaced by a genuinely different one, not the same default.
        if variant and applicable:
            k = variant % len(applicable)
            applicable = applicable[k:] + applicable[:k]
        return Strategy(applicable, variant)


# ---- failure-mode guardrails (the Seven Deaths, the two that bite an agent) --------
def is_monoculture(recent_novelty: float, thresh: float = 0.18) -> bool:
    """Monoculture/Stasis: repeating instead of varying; states going stale. The cue to
    regenerate the story (vary) rather than re-run the same one (regress to the mean)."""
    return recent_novelty < thresh

# ===================== arc3_agent.py =====================
"""
arc3_agent.py — thin ARC-AGI-3 harness adapter around the cognitive-prior brain.

Wires PriorPolicy (arc3_priors) into the ARC-AGI-3 `Agent` contract. Imports of
the harness (`agents.agent`, `arcengine`) are guarded so this module is importable
and unit-testable without the competition environment.

Design choice that matters: the SELF-MODEL (action->displacement) is *transferable
structure* and is reused across levels of the same game; only the layout-specific
maps (goal candidates, learned walls, visited states) reset on level advance. That
is the "carry the world-model to an unseen level" capability humans use — and the
thing a replay memoizer cannot do.
"""
import numpy as np

try:
    PriorPolicy = globals().get('PriorPolicy')  # inlined
    ObjectExtractor = globals().get('ObjectExtractor')  # inlined
except ImportError:
    pass  # combined module: names already defined above

# ---- arcengine is present BOTH offline and on Kaggle: import it independently of the
# agent framework so we always use the REAL GameAction/GameState API (RESET, set_data,
# WIN) instead of a stub that silently diverges from Kaggle behavior. ----
try:
    from arcengine import FrameData, GameAction, GameState, ActionInput
except Exception:                                              # pragma: no cover
    class _GA:                                                 # GameAction stub (no arcengine)
        RESET = 0; ACTION1 = 1; ACTION2 = 2; ACTION3 = 3; ACTION4 = 4; ACTION5 = 5; ACTION6 = 6; ACTION7 = 7
        @staticmethod
        def from_id(i): return i
    GameAction = _GA()
    class GameState:                                           # GameState stub
        NOT_PLAYED = "NOT_PLAYED"; NOT_FINISHED = "NOT_FINISHED"; WIN = "WIN"; GAME_OVER = "GAME_OVER"
    class ActionInput:                                         # ActionInput stub
        def __init__(self, id=None, x=None, y=None): self.id, self.x, self.y = id, x, y

# ---- the agent framework (ARC-AGI-3-Agents) is present only on Kaggle; offline we
# subclass a minimal stub so the same MyAgent class works in both. ----
try:
    from agents.agent import Agent
    _HARNESS = True
except Exception:                                              # pragma: no cover
    _HARNESS = False

    class Agent:                                               # minimal stub
        def __init__(self, *a, **kw):
            self.game_id = kw.get("game_id", "stub")
            self.frames = []
            self.arc_env = None


# action-id -> GameAction (parameterized; do not hard-code the action count)
def _ga(i):
    return {1: GameAction.ACTION1, 2: GameAction.ACTION2, 3: GameAction.ACTION3,
            4: GameAction.ACTION4, 5: GameAction.ACTION5}.get(i, GameAction.ACTION5)


class MyAgent(Agent):
    """Core-Knowledge-prior ARC-AGI-3 agent."""
    MAX_ACTIONS = float("inf")

    def __init__(self, *a, **kw):
        pm = kw.pop("policy_memory", None)
        super().__init__(*a, **kw)
        self.pm = pm                            # ACQUISITION POLICY slow-weights (or None)
        # STABLE master seed: Python's hash() on strings is per-process randomized (PYTHONHASHSEED),
        # which a Kaggle kernel cannot set for its own already-running process -> a different seed
        # every container -> non-reproducible runs. Use a deterministic, import-free string hash.
        self.policy = PriorPolicy(move_actions=(1, 2, 3, 4), extra_actions=(5,),
                                  seed=(sum((i + 1) * ord(ch) for i, ch in enumerate(str(self.game_id))) & 0xffff))
        # --- warm-start the per-game mechanic from the (frozen) acquisition policy ---
        # We bias INITIAL hypotheses with cross-game invariants; we never inject a
        # mechanic. A new game still has to acquire its own self/action/goal/buttons.
        self._click_floor_hint = None
        self._auto_prior = 0.0
        if pm is not None:
            self.policy._goal_w = pm.goal_weights(self.policy._goal_types)
            self.policy._goal_active = max(self.policy._goal_w, key=self.policy._goal_w.get)
            self._click_floor_hint = pm.button_floor_hint()
            self._auto_prior, _ = pm.expects_autonomous()
        self.ex = ObjectExtractor()
        self._last_progress = 0.0
        self._turns_since_change = 0
        self._click_mode = False                # discovered to be a click/select game
        self._prev_sig = None
        self._clicked = set()                   # cells already clicked (avoid repeats)
        self._click_sig = None                  # grid signature when clicks began
        # feedback-directed clicking, IMPACT-WEIGHTED (measured: some objects are
        # high-impact 'buttons' — vc33 color-9 click changes 266 cells, r11l certain
        # cells change 55-62 locally — while most clicks change 1 cell). Rank targets
        # by magnitude of change they produce; prefer high-impact buttons.
        self._click_pending = None              # target whose effect we're awaiting
        self._click_impact = {}                 # target -> EMA cells changed (impact)
        self._click_dead = set()                # targets measured at ~0 impact
        self._click_prev_grid = None            # grid when the pending click was emitted
        # action-space awareness: the engine declares which actions are legal per game
        # (frame.available_actions). 6/25 games are ACTION6-only; 6/25 have no click.
        # Using the declared set (not a static-turn heuristic) is the principled fix.
        self._avail = None                      # set of legal action ids for this game
        # death-avoidance (ported from v1 terminal_pattern_detector): key terminal
        # signatures by (state_hash, action); avoid a planned action that previously
        # led to GAME_OVER from a similar state. Confidence grows with repeats, decays
        # on false positives. Lets a life last long enough to develop insight.
        self._term_fatal = {}                   # (frame_hash, action) -> confidence
        self._term_fp = {}                      # (frame_hash, action) -> false-pos count
        self._prev_state = None                 # last frame's GameState string
        self._death_prev_sig = None             # frame sig before the last action
        self._death_prev_act = None             # last action id taken
        self._prev_was_noop = False             # was the previously-emitted action a no-op
        self._consec_noop = 0                   # consecutive no-ops (capped to avoid perpetual wait)
        # --- the BINDER: an NSM story-generator that composes a per-game strategy and
        # regenerates a varied one when the current story stalls (Serendipity pattern). ---
        StrategyGenerator = globals().get('StrategyGenerator')  # inlined
        is_monoculture = globals().get('is_monoculture')  # inlined
        TaskBelief = globals().get('TaskBelief')  # inlined
        self._stratgen = StrategyGenerator(priors=(pm.goal_type_prior if pm else None))
        self._belief = TaskBelief(prior=(dict(pm.goal_type_prior) if pm else None))
        self._is_monoculture = is_monoculture
        self._strategy = None
        self._strategy_variant = 0
        self.family = "no_self_yet"             # online family classification
        # ---- return-leg: cross-agent object-prior memory --------------------
        try:
            CohesionSediment = globals().get('CohesionSediment')  # inlined
            PriorEvolver = globals().get('PriorEvolver')  # inlined
            family_key = globals().get('family_key')  # inlined
            RULES = globals().get('RULES')  # inlined
        except Exception:
            CohesionSediment = globals().get('CohesionSediment')
            PriorEvolver = globals().get('PriorEvolver')
            family_key = globals().get('family_key')
            RULES = globals().get('RULES')
        self._family_key_fn = family_key
        self._RULES = RULES
        self._sediment = CohesionSediment() if CohesionSediment else None
        self._evolver = PriorEvolver() if PriorEvolver else None
        try:
            InventedFeatureStore = globals().get('InventedFeatureStore')  # inlined
        except Exception:
            InventedFeatureStore = globals().get('InventedFeatureStore')
        try:
            ComposableCarving = globals().get('ComposableCarving')  # inlined
        except Exception:
            ComposableCarving = globals().get('ComposableCarving')
        self._invented = InventedFeatureStore() if InventedFeatureStore else None
        self._Carving = ComposableCarving
        self._active_carver_dict = None
        self._fkey = None                       # set on first frame
        self._rule_idx = None
        self._win_recorded = False

    def _init_object_prior(self, grid):
        """First frame: pick the carving rule by sedimented win-rate, warm-start the
        cohesion prior with previously-learned sprite groups. The return leg in action."""
        if self._fkey is not None or self._family_key_fn is None:
            return
        self._fkey = self._family_key_fn(grid)
        if self._evolver is not None and self._RULES is not None:
            self._rule_idx = self._evolver.select(self._fkey)
            self._evolver.note_play(self._fkey, self._rule_idx)
            rule = self._RULES[self._rule_idx]
            self.policy.set_object_prior(**rule)
        if self._sediment is not None and self.policy.merger is not None:
            self.policy.merger.warm_start_groups(self._sediment.warm_start(self._fkey))
        # INHERIT a validated invented-feature carver for this family, if one earned its
        # keep in a past generation. Falls back to common-fate when the germline is empty.
        if self._invented is not None and self._Carving is not None:
            genome = self._invented.best_carver(self._fkey)
            if genome:
                try:
                    self._active_carver_dict = genome
                    self.policy.set_composable_carver(self._Carving.from_dict(genome))
                except Exception:
                    self._active_carver_dict = None

    # ---- frame helpers -------------------------------------------------------
    @staticmethod
    def _grid(fd) -> np.ndarray:
        arr = np.array(fd.frame, dtype=np.int64)
        return arr[-1] if arr.ndim == 3 else arr

    @staticmethod
    def _progress(fd) -> float:
        return float(getattr(fd, "score", None) or getattr(fd, "levels_completed", 0) or 0)

    def _level_advanced(self, progress: float) -> bool:
        return progress > self._last_progress

    def _reset_layout_state(self):
        """Keep transferable self-model deltas + induced predicate; reset layout maps.
        On level advance (a win) also write the return leg: sediment the object-groups
        learned this life, and credit the carving rule that produced the win."""
        # --- return leg: a completed level is a win for this family's chosen rule ---
        if self._fkey is not None and not self._win_recorded:
            if self._sediment is not None and self.policy.merger is not None:
                self._sediment.sediment(self._fkey, self.policy.merger.export_groups())
            if self._evolver is not None and self._rule_idx is not None:
                self._evolver.note_win(self._fkey, self._rule_idx)
            if self._active_carver_dict is not None and self._invented is not None:
                self._invented.store_carver(self._fkey, self._active_carver_dict, won=True)
            self._win_recorded = True
        self.policy.tr = type(self.policy.tr)()              # fresh tracker for new layout
        self.policy.reset_level()                            # resets self-id, keeps deltas
        self._clicked.clear()                                # new level -> new things to click
        self._click_impact.clear(); self._click_dead.clear()  # re-open impact probing
        self._click_pending = None; self._click_prev_grid = None
        self._click_sig = None

    # ---- main loop -----------------------------------------------------------
    @staticmethod
    def _avail_actions(fd):
        """Read the engine-declared legal action set from the frame, as a set of ints.
        Returns None if unavailable (then the agent falls back to its defaults)."""
        av = getattr(fd, "available_actions", None)
        if not av:
            return None
        out = set()
        for a in av:
            v = getattr(a, "value", a)
            try:
                out.add(int(v))
            except Exception:
                name = getattr(a, "name", str(a))      # e.g. 'ACTION6'
                digits = "".join(ch for ch in name if ch.isdigit())
                if digits:
                    out.add(int(digits))
        return out or None

    @staticmethod
    def _frame_state(fd) -> str:
        s = getattr(fd, "state", "")
        return getattr(s, "name", str(s)).upper()

    def choose_action(self, frames, lf=None):
        fd = lf if lf is not None else (frames[-1] if isinstance(frames, (list, tuple)) else frames)
        grid = self._grid(fd)
        progress = self._progress(fd)

        # --- death-avoidance bookkeeping: did the last action just kill us? ---
        state = self._frame_state(fd)
        if ("GAME_OVER" in state or "OVER" in state) and self._death_prev_sig is not None \
                and self._death_prev_act is not None:
            key = (self._death_prev_sig, int(self._death_prev_act))
            self._term_fatal[key] = self._term_fatal.get(key, 0.0) + 1.0   # confirmed lethal
        self._prev_state = state

        # --- FRAMEWORK CONTRACT: the agent must RETURN GameAction.RESET to START the game
        # (first frame is NOT_PLAYED) and to RESTART after GAME_OVER. The offline harness
        # reset the env itself, which masked this; the real ARC-AGI-3 framework does not. ---
        # RESET BAN [Isaiah]: NOT_PLAYED is game-START (a legitimate RESET to begin play). GAME_OVER/OVER is a RESTART
        # back to level 0 -- it DISCARDS earned progress, so it is an EARNED privilege (reset_earned: corroborated-L4
        # AND the agent reasoned its way to needing reset). Until earned, do NOT reset here; the session ends at
        # GAME_OVER via _is_done_impl. (Defense-in-depth: the harness normally breaks before this on the game-over frame.)
        if "NOT_PLAYED" in state:
            self._death_prev_sig = None; self._death_prev_act = None
            return GameAction.RESET
        if "GAME_OVER" in state or "OVER" in state:
            _earned_v = False
            try:
                import objective_validator as _OVv
                _earned_v = bool((_OVv._GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("reset_earned"))
            except Exception:
                _earned_v = False
            self._death_prev_sig = None; self._death_prev_act = None
            if _earned_v:
                return GameAction.RESET
            return GameAction.ACTION1                       # non-destructive; session ends at GAME_OVER via is_done

        # --- action-space awareness: restrict repertoire to engine-declared legal acts ---
        avail = self._avail_actions(fd)
        if avail is not None and avail != self._avail:
            self._avail = avail
            self._apply_action_space(avail)

        self._init_object_prior(grid)                        # first frame: select rule + warm-start

        if self._level_advanced(progress):
            self._reset_layout_state()                       # new level: transfer self-model, reset maps
            self._win_recorded = False                       # next level can register its own win
        self._last_progress = progress

        # click-game detection: PRINCIPLED (declared action space) first, heuristic fallback.
        sig = hash(grid.tobytes())
        if sig == self._prev_sig:
            self._turns_since_change += 1
        else:
            self._turns_since_change = 0
        self._prev_sig = sig
        self._update_belief(grid)            # BAMDP: integrate this turn's evidence into b_t
        click_only = self._avail is not None and self._avail.issubset({6, 7}) and 6 in self._avail
        no_self = self.policy.sm.controllable() is None
        if click_only:
            self._click_mode = True              # only clicks are legal -> always click
        elif self._turns_since_change >= 8 and no_self and not self._click_mode \
                and (self._avail is None or 6 in self._avail):
            self._click_mode = True              # heuristic fallback (only if click is legal)

        if self._click_mode:
            self.policy._note_state(grid)        # keep novelty live so the click guard fires
            # GENERATOR: when the click story stalls (Monoculture), regenerate a varied
            # strategy; if it now says WAIT (timing hypothesis), emit a no-op to let
            # autonomous dynamics advance -- the missing timing capability for games like
            # ft09 (click-only + autonomous). Bounded by the consecutive-no-op cap.
            if self._is_monoculture(getattr(self.policy, "_recent_novelty", 1.0)):
                percept = self._build_percept(grid)
                self._strategy_variant += 1
                self._strategy = self._stratgen.generate(percept, self._strategy_variant,
                                                         belief=self._belief.posterior())
                act_prim, _ = self._strategy.decide(percept)
                noop = self._noop_action()
                if act_prim == "WAIT" and noop is not None and self._consec_noop < 2:
                    self._consec_noop += 1; self._prev_was_noop = True
                    self.policy.last_was_noop = True
                    self._record_pending_death(sig, _ga(noop))
                    return _ga(noop)
            self._consec_noop = 0
            act = self._click_action(grid)
            self._record_pending_death(sig, act)
            self._prev_was_noop = False
            return act

        # tell the policy whether the PREVIOUS emitted action was a no-op, so observe
        # attributes the prev->current frame delta correctly (autonomous vs self-caused).
        self.policy.last_was_noop = self._prev_was_noop
        aid = self.policy.act(grid, progress)        # observe + attribution + action choice

        # --- no-op / wait (autonomous-dynamics control + timing) ---
        # Override with a no-op when: (a) the autonomous baseline isn't measured yet
        # (first couple turns), or (b) dynamics are autonomous and we're stuck with no
        # controllable self and a blocked move — wait for a better world configuration.
        noop = self._noop_action()
        measuring = self.policy._noop_samples < 3            # a few early baseline samples
        stuck = (self.policy.has_autonomous_dynamics()
                 and self.policy._last_blocked
                 and self.policy.sm.controllable() is None)
        # cap consecutive no-ops at 2 so a persistently-stuck game can't wait forever
        want_noop = noop is not None and (measuring or stuck) and self._consec_noop < 2
        if want_noop:
            self._consec_noop += 1
            self._prev_was_noop = True
            self._record_pending_death(sig, noop)
            return _ga(noop)

        self._consec_noop = 0
        self._prev_was_noop = False
        aid = self._avoid_fatal(sig, aid)            # death-avoidance substitution
        self.family = self.policy.family()
        self._record_pending_death(sig, aid)
        return _ga(aid)

    def _update_belief(self, grid):
        """BAMDP belief update: turn this frame's observations into log-likelihood cues over
        basin-family. button-evidence = a high-impact click just happened; timing-evidence =
        the world moves on its own (autonomous dynamics); reach-evidence = a controllable
        self exists and there are distinct goal-objects to move toward. Small nudges, so the
        posterior concentrates only under repeated consistent evidence."""
        cues = {}
        # button: fire only when a NEW high-impact click was registered THIS turn (event,
        # not the persistent presence of an old high value -- else button drowns timing).
        if self._click_impact:
            floor = self._click_floor()
            hi = max(self._click_impact.values())
            prev_hi = getattr(self, "_belief_prev_hi", 0.0)
            if hi > prev_hi and hi > floor + max(1.0, floor):
                cues["button"] = 0.6
            self._belief_prev_hi = hi
        # timing: autonomous dynamics present (fires per-turn while the world self-evolves)
        if self.policy.has_autonomous_dynamics():
            cues["timing"] = 0.5
        # reach: a controllable self + distinct goal-objects (movement-to-target basin)
        ctrl = self.policy.sm.controllable()
        if ctrl is not None:
            cues["reach"] = 0.3
        if cues:
            self._belief.update(cues)

    def _build_percept(self, grid):
        """Translate the agent's perception into NSM perceptual primitives for the
        generator: what the librarian SEEs before composing a strategy."""
        clickable = self._avail is None or 6 in self._avail
        ctrl = self.policy.sm.controllable()
        try:
            objs = self.policy._perceive(grid)
            n = len(objs)
            goal_objs = bool(self.policy._detect_goal_objs(objs, ctrl, grid)) if ctrl is not None else (n > 1)
        except Exception:
            n = 0; goal_objs = False
        return {
            "SEE_AGENT": ctrl is not None,
            "SEE_CLICKABLE": bool(clickable) and n > 0,
            "SEE_AUTONOMOUS": self.policy.has_autonomous_dynamics(),
            "SEE_GOAL_OBJECT": goal_objs,
            "COUNT_OBJECTS": n,
        }

    def _noop_action(self):
        """Return an action id guaranteed ILLEGAL for this game (a true no-op that lets
        autonomous dynamics advance while contributing nothing). None if every action is
        legal (no clean no-op available)."""
        if self._avail is None:
            return None
        for cand in (7, 5, 6, 1, 2, 3, 4):
            if cand not in self._avail:
                return cand
        return None                                  # all actions legal: no clean no-op

    def _apply_action_space(self, avail):
        """Restrict the movement policy to engine-declared legal actions."""
        moves = tuple(a for a in (1, 2, 3, 4) if a in avail)
        extra = tuple(a for a in (5,) if a in avail)
        if moves or extra:
            mv = moves or (1, 2, 3, 4)
            self.policy.move_actions = list(mv)
            self.policy.all_actions = list(mv) + list(extra)
            for a in self.policy.all_actions:
                self.policy._novel_yield.setdefault(a, 1.0)

    def _avoid_fatal(self, sig, aid, min_conf: float = 2.0):
        """If (state, aid) is a confirmed killer, substitute the least-fatal legal action."""
        key = (sig, int(aid))
        if self._term_fatal.get(key, 0.0) < min_conf:
            return aid
        pool = self.policy.all_actions if self.policy.all_actions else [aid]
        ranked = sorted(pool, key=lambda a: self._term_fatal.get((sig, int(a)), 0.0))
        for a in ranked:
            if self._term_fatal.get((sig, int(a)), 0.0) < min_conf:
                self._term_fp[key] = self._term_fp.get(key, 0) + 1   # we avoided it; if benign, demote later
                return a
        return aid                                       # all known-fatal: no safe choice

    def _record_pending_death(self, sig, act):
        """Remember (state, action) so the next frame can attribute a GAME_OVER to it."""
        self._death_prev_sig = sig
        aid = getattr(act, "id", act)
        aid = getattr(aid, "value", aid)
        try:
            self._death_prev_act = int(aid)
        except Exception:
            self._death_prev_act = None

    def _click_floor(self):
        """Robust 'dead' floor = median of observed per-target impacts. On games with
        autonomous dynamics (r11l: a 1-cell tick on every frame) every click measures
        impact>=1, so an absolute threshold mislabels all clicks as buttons. The median
        captures that autonomous/dead floor; real buttons sit well above it. Before we
        have enough observations, fall back to the cross-game button-floor prior."""
        vals = sorted(self._click_impact.values())
        if len(vals) < 4 and self._click_floor_hint is not None:
            return self._click_floor_hint * 0.5   # prior: buttons beat ~half the typical button impact
        if not vals:
            return 0.0
        return vals[len(vals) // 2]

    def _click_action(self, grid):
        """Impact-weighted click discovery (the interface/button expert). Measures HOW
        MANY cells each click changes (not just whether), RELATIVE to the autonomous/dead
        floor, so it finds the high-impact 'buttons' (vc33 color-9 -> 266 cells) and
        prefers them over clicks that only ride the autonomous tick. Probe untried targets
        to learn impact, then prioritize the highest-impact-above-floor buttons."""
        sig = hash(grid.tobytes())
        if self._click_pending is not None:
            impact = 0
            if self._click_prev_grid is not None and self._click_prev_grid.shape == grid.shape:
                impact = int((grid != self._click_prev_grid).sum())
            prev = self._click_impact.get(self._click_pending, 0.0)
            self._click_impact[self._click_pending] = 0.5 * prev + 0.5 * impact
            self._click_pending = None
        self._click_sig = sig
        floor = self._click_floor()
        margin = max(1.0, floor)                       # a button must beat the floor by >=1x floor

        objs = self.ex.extract(grid)
        targets = [(int(round(o.centroid[0])), int(round(o.centroid[1])))
                   for o in sorted(objs, key=lambda o: o.area)]
        # 1) probe untried object centroids (learn their impact)
        for rc in targets:
            if rc not in self._click_impact:
                self._click_pending = rc; self._click_prev_grid = grid.copy()
                return self._complex(rc[1], rc[0])
        # 2) probe untried raw foreground cells
        for r, c in zip(*np.nonzero(grid != self.ex.bg)):
            rc = (int(r), int(c))
            if rc not in self._click_impact:
                self._click_pending = rc; self._click_prev_grid = grid.copy()
                return self._complex(rc[1], rc[0])
        # 3) exploit: click the highest-impact-ABOVE-FLOOR buttons (rotate among top-3)
        ranked = sorted(((v, k) for k, v in self._click_impact.items() if v > floor + margin), reverse=True)
        # OVER-COMMITMENT GUARD (click): if states are stale, the top-3 rotation is just
        # toggling among a few states (vc33 57 states vs random 131). Diversify with a
        # random foreground re-probe (click effects are state-dependent, so re-probing
        # finds new transitions). Probability rises as recent novelty falls.
        rn = getattr(self.policy, "_recent_novelty", 1.0)
        stuck = max(0.0, 0.30 - rn) * 3.0
        if (not ranked) or self.policy.rng.rand() < stuck:
            fg = list(zip(*np.nonzero(grid != self.ex.bg)))
            if fg:
                r, c = fg[self.policy.rng.randint(len(fg))]
                rc = (int(r), int(c)); self._click_pending = rc; self._click_prev_grid = grid.copy()
                return self._complex(rc[1], rc[0])
        if ranked:
            turn = getattr(self.policy, "turn", 0)
            rc = ranked[turn % min(3, len(ranked))][1]
            self._click_pending = rc; self._click_prev_grid = grid.copy()
            return self._complex(rc[1], rc[0])
        # nothing clearly above the floor -> re-open probing
        self._click_impact.clear()
        return _ga(5)

    def export_to_memory(self, mem):
        """At the GAME BOUNDARY, distill per-game mechanics into substrate-general
        invariants and write them to the acquisition policy. Only aggregates cross the
        membrane: which goal-type worked (not where), button-impact magnitudes (not
        coordinates), whether autonomous dynamics existed (not the frame). No mechanic."""
        if mem is None:
            return
        p = self.policy
        # goal-type that the per-game induction settled on (if it beat the baseline)
        if getattr(p, "_goal_w", None):
            best = max(p._goal_w, key=p._goal_w.get)
            if p._goal_w[best] > 1.0:
                mem.note_goal_progress(best)
        # button-impact magnitudes that cleared this game's floor (magnitudes only)
        floor = self._click_floor()
        for impact in self._click_impact.values():
            if impact > floor + max(1.0, floor):
                mem.note_button_impact(impact)
        # autonomous-dynamics presence + magnitude
        had_auto = p.has_autonomous_dynamics()
        mem.note_game_end(had_auto, p._auto_cells_ema if had_auto else 0.0, None)

    def _complex(self, x, y):
        """A complex (click) action for the framework: a GameAction.ACTION6 carrying x,y via
        set_data -- the contract the real harness expects. Falls back to ActionInput only if
        the real API is unavailable (no-arcengine stub)."""
        a = GameAction.ACTION6
        if hasattr(a, "set_data"):
            try:
                a.set_data({"x": int(x), "y": int(y)})   # mutate the enum in place; env.step reads action_data
                return a                                  # return the ENUM (.value/.name); ComplexAction crashes step
            except Exception:
                pass
        return ActionInput(id=GameAction.ACTION6, x=int(x), y=int(y))

    def is_done(self, frames, lf=None):
        # FRAMEWORK CONTRACT: tell the harness the game is finished on WIN, so it stops and
        # advances. Returning False forever (the old stub) hangs the run until timeout.
        fd = lf if lf is not None else (frames[-1] if isinstance(frames, (list, tuple)) and frames else None)
        if fd is None:
            return False
        return "WIN" in self._frame_state(fd)
