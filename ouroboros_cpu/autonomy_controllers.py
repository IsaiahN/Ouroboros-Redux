"""autonomy_controllers.py -- C1..C6, the CONTROLLERS that convert the manual in-game reasoning documented in the
cn04 autonomy audit into autonomous mechanisms, plus the general MATCH-o-SKILL schema.

Framing (see cn04_autonomy_audit.md): P0-P4 built the EFFECTORS (the hands -- residual loop, selection probe,
isolation, rotation fit). These are the CONTROLLER (the head) -- the part that decides *what* to pursue, notices when
the model or the atom is wrong, and recognises a game it has effectively seen before.

  C1  induce_objective_from_reward   -- the crux: discover the win predicate from the reward, not from a human
  C2  individuate_by_comovement      -- objects/self from what-moves-when-I-act, not colour labels
  C3  FidelityMonitor                -- standing model-vs-real monitor + auto-recalibration (P0 as a reflex)
  C4  detect_coupling_granularity    -- automate the atom-granularity law (coarsen when per-part optima stall global)
  C5  extrapolate_worst_predictable  -- hold the arity-invariant general form from one observation
  C6  HypothesisLattice + recognize_schema + next_probe_by_infogain + dead_frontier_mint

  match_skill_plan / match_by_key    -- the general MATCH_BY_KEY o PER_PAIR_SKILL schema (cn04 & vc33 as instances)

All heavy helpers (grammar, discrepancy, segmentation, joint solve) are imported LAZILY from objective_validator so
this module never creates a circular import. Nothing here mutates the trunk; wire in incrementally and validate live.
"""

import math
import itertools
import numpy as np
from collections import defaultdict, deque
import objective_validator as OV   # LAYER-0 primitives (see LAYERING note in the docstring). Top-level,
                                   # one-way: this module is Layer 1; objective_validator (Layer 0+flow)
                                   # MUST NOT import this module -- the flow receives controllers by
                                   # INJECTION, which keeps the dependency graph an acyclic DAG.

# ---- tunable thresholds (frame-only, no game identity) --------------------------------------------------------
FIDELITY_MISMATCH_TOL = 12      # C3: per-action predicted-vs-real cell mismatch above which an effect is "wrong"
LOCAL_OPT_TOL = 1.0             # C4: a part is "locally optimal" when its own sub-discrepancy is <= this
GLOBAL_UNMET_TOL = 1.0         # C4: the global objective is "unmet" when its discrepancy is > this


def _bg(g):
    g = np.asarray(g)
    return int(np.bincount(g.ravel()).argmax())


# =================================================================================================================
# C1 -- OBJECTIVE INDUCTION FROM REWARD  (the crux: the composer discovers the win condition itself)
# =================================================================================================================
def _spec_complexity(spec):
    """Kolmogorov-ish: how many words to express the objective. Simpler explanations of the reward are preferred."""
    if not isinstance(spec, tuple):
        return 1
    if spec and spec[0] in ("AND", "THEN", "ALL", "COUNT"):
        return 1 + sum(_spec_complexity(x) for x in spec[1:] if isinstance(x, tuple)) + 1
    return 2  # atomic (relation, target)


def induce_objective_from_reward(frames, reward_idx, ctrl, co=None,
                                 relations=("SAME", "TOUCH", "BE_AT", "COVER", "BECOME",
                                            "CONTAIN_FIT", "ASSEMBLY", "NONE.EXIST")):
    """C1. A reward fired at frame `reward_idx`. Diff the winning transition (frames[reward_idx-1] -> [reward_idx])
    and find which grammar predicate went FALSE->TRUE exactly there -- the reward becomes the supervision, replacing
    the human-specified objective. Returns candidate specs ranked (simplest explanation of the reward first).

    This is the seed-problem resolution: blind search triggers a reward; the reward transition is then *read* to
    instantiate the objective, which is thereafter dense feedback. The composer never faced this on cn04 because we
    hand-built `_TipOverlapDisc`; C1 is what removes the human from every game, not one."""
    frames = [np.asarray(f) for f in frames]
    if reward_idx < 1 or reward_idx >= len(frames):
        return []
    before, after = frames[reward_idx - 1], frames[reward_idx]
    bg = _bg(after)
    colours = [int(c) for c in np.unique(after) if int(c) != bg]
    cands = []
    for rel in relations:
        for tgt in list(colours) + [None]:
            spec = (rel, tgt)
            try:
                d = OV.compile_objective(spec, ctrl, before)
                mb = float(d.measure(before)); ma = float(d.measure(after))
            except Exception:
                continue
            if mb > 0 and ma <= 0:                          # predicate transitioned false->true AT the reward
                cands.append((_spec_complexity(spec), -(mb - ma), spec))
    cands.sort(key=lambda x: (x[0], x[1]))                  # simplest, then largest satisfying drop
    return [spec for _, _, spec in cands]


def generalize_induced(spec):
    """C1+C5 bridge: an objective induced over ONE object is immediately lifted to its ALL-quantified form, so the
    first win already carries the general law for later levels (worst-predictable-case, held not committed)."""
    return extrapolate_worst_predictable(spec)


# =================================================================================================================
# C2 -- MOTION-COHERENT INDIVIDUATION + SELF-DETECTION  (objects/self without colour labels)
# =================================================================================================================
def _components(g):
    """Non-background 4-connected components as cell-sets (colour-agnostic)."""
    g = np.asarray(g); bg = _bg(g); H, W = g.shape
    seen = np.zeros((H, W), bool); comps = []
    for r in range(H):
        for c in range(W):
            if g[r, c] == bg or seen[r, c]:
                continue
            q = deque([(r, c)]); seen[r, c] = True; cells = []
            while q:
                y, x = q.popleft(); cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy, xx] and g[yy, xx] != bg:
                        seen[yy, xx] = True; q.append((yy, xx))
            comps.append(set(cells))
    return comps


def _centroid(cells):
    ys = [c[0] for c in cells]; xs = [c[1] for c in cells]
    return (sum(ys) / len(ys), sum(xs) / len(xs))


def individuate_by_comovement(frames, actions):
    """C2. Individuate OBJECTS by co-movement and identify SELF (the controllable) as the object whose motion
    correlates with the agent's actions -- not from colour labels (which cn04 showed can be shared across pieces).
    Returns {'objects': [cellset,...] (from the first frame), 'self_idx': int|None, 'mobility': [float,...]}.

    Method: per action transition, measure the dominant rigid displacement of each first-frame component (tracked by
    nearest-centroid match on non-bg components). A component that repeatedly displaces under action = self; ones that
    never move = static anchors/targets. Colour-agnostic, so shared-colour games (cn04) individuate correctly."""
    frames = [np.asarray(f) for f in frames]
    if len(frames) < 2:
        return {"objects": _components(frames[0]) if frames else [], "self_idx": None, "mobility": []}
    base = _components(frames[0])
    mobility = [0.0] * len(base)
    for k in range(1, len(frames)):
        cb = [_centroid(c) for c in _components(frames[k - 1])]
        ca = [_centroid(c) for c in _components(frames[k])]
        if not cb or not ca:
            continue
        for i, bc in enumerate(base):
            bcen = _centroid(bc)
            # nearest before-centroid, then its nearest after-centroid = displacement magnitude
            nb = min(cb, key=lambda p: abs(p[0] - bcen[0]) + abs(p[1] - bcen[1])) if cb else bcen
            na = min(ca, key=lambda p: abs(p[0] - nb[0]) + abs(p[1] - nb[1])) if ca else nb
            disp = abs(na[0] - nb[0]) + abs(na[1] - nb[1])
            if disp > 0.5:
                mobility[i] += disp
    self_idx = int(np.argmax(mobility)) if mobility and max(mobility) > 0 else None
    return {"objects": base, "self_idx": self_idx, "mobility": mobility}


# =================================================================================================================
# C3 -- STANDING FIDELITY MONITOR + AUTO-RECALIBRATION  (P0 promoted from a one-off diff to a reflex)
# =================================================================================================================
class FidelityMonitor:
    """C3. After every real action, compare the forward model's prediction to the real next frame, track per-action
    fidelity, and when an effect is systematically wrong, RECALIBRATE it from the observed real displacement. This is
    the reflex the cn04 campaign performed by hand (the P0 diff, then manual re-measurement). It makes the P-series
    effectors self-deploying: the model notices it is wrong and fixes itself, no human reading the diff."""

    def __init__(self, amap, rotate_actions, ctrl, co=None, rotate_model=None):
        self.amap = dict(amap or {})
        self.rotate_actions = set(str(a) for a in (rotate_actions or ()))
        self.ctrl = ctrl
        self.co = list(co) if co else None
        self.rotate_model = dict(rotate_model or {})
        self.err = defaultdict(list)
        self.recalibrated = set()

    def observe(self, g_before, action, g_after):
        """Record the prediction error for `action`; recalibrate if systematically wrong. Returns the mismatch."""
        gb, ga = np.asarray(g_before), np.asarray(g_after)
        try:
            pred = np.asarray(OV._model_apply(gb, action, self.amap, self.rotate_actions,
                                              self.ctrl, self.co, self.rotate_model))
            mism = int((pred != ga).sum())
        except Exception:
            mism = -1
        if mism >= 0:
            self.err[str(action)].append(mism)
            recent = self.err[str(action)][-3:]
            if len(recent) >= 3 and float(np.median(recent)) > FIDELITY_MISMATCH_TOL:
                self._recalibrate(action, gb, ga)
        return mism

    def _recalibrate(self, action, gb, ga):
        """Re-measure this action's TRUE effect on the isolated controllable and update the model."""
        cb = OV._ctrl_component(gb, self.ctrl, self.co)
        ca = OV._ctrl_component(ga, self.ctrl, self.co)
        if not cb or not ca:
            return
        bce = _centroid(cb); ace = _centroid(ca)
        dr, dc = ace[0] - bce[0], ace[1] - bce[1]
        if str(action) in self.rotate_actions:
            return  # rotation recalibration is handled by the rigid-fit in explore; leave rotate_model as gated
        self.amap[action] = (dr, dc)                        # translate: adopt the real observed displacement
        self.recalibrated.add(str(action))

    def fidelity(self, action=None):
        if action is not None:
            e = self.err.get(str(action), [])
            return None if not e else max(0.0, 1.0 - float(np.median(e)) / 64.0)
        allv = [v for lst in self.err.values() for v in lst]
        return None if not allv else max(0.0, 1.0 - float(np.median(allv)) / 64.0)


# =================================================================================================================
# C4 -- COUPLING-GRANULARITY DETECTION  (automate the atom-granularity law)
# =================================================================================================================
def detect_coupling_granularity(parts, per_part_disc, global_disc, state):
    """C4. The atom-granularity law made mechanical: if EVERY part is at its own local optimum yet the GLOBAL
    objective is still unmet, the parts are jointly coupled and the atom is TOO FINE -- a joint constraint was
    dropped. Signal to COARSEN (merge the coupled parts into one unit and re-solve them jointly).

    `per_part_disc(part, state) -> float`, `global_disc(state) -> float`. Returns a coarsen decision. This is exactly
    the reasoning Claude did after watching the per-piece assembler stall at one-pair-connected on cn04."""
    try:
        locals_ok = all(float(per_part_disc(p, state)) <= LOCAL_OPT_TOL for p in parts)
        g = float(global_disc(state))
    except Exception:
        return {"coarsen": False, "reason": "disc-eval-failed"}
    if locals_ok and g > GLOBAL_UNMET_TOL:
        return {"coarsen": True, "granularity": "join_all",
                "reason": "per-part optima reached but global objective unmet -> joint coupling; coarsen the atom"}
    return {"coarsen": False, "global": g}


# =================================================================================================================
# C5 -- WORST-PREDICTABLE-CASE EXTRAPOLATION / INVARIANCE PROBES  (hold the general form from one observation)
# =================================================================================================================
def extrapolate_worst_predictable(spec):
    """C5. Lift an objective observed over ONE object to its arity-invariant ALL-quantified form -- the *top* of the
    hypothesis lattice, held but not committed. (relation, tc) --over one--> ('ALL', relation, tc) --over all matching
    objects. This is 'stay maximally general, specialise on forced divergence': the general law is present from the
    first observation, and only specialised down when evidence forces it."""
    if isinstance(spec, tuple) and len(spec) == 2 and isinstance(spec[0], str) and spec[0] not in (
            "AND", "THEN", "ALL", "COUNT"):
        rel, tc = spec
        return ("ALL", rel, tc)
    return spec


def invariance_probe(disc_measure, state, scale_fn):
    """C5. Does the observed invariant survive scaling? `scale_fn(state) -> state'` adds MORE objects / grows the grid;
    the invariant is deemed to survive if the discrepancy stays structurally finite (not a degenerate blow-up) on the
    scaled state. Returns True if it is safe to HOLD the general form along that dimension. A probe you can run in the
    model, cheaply, before the environment forces the scale."""
    try:
        base = float(disc_measure(state))
        scaled = float(disc_measure(scale_fn(state)))
        return math.isfinite(scaled) and scaled < 1e6 and (base < 1e6)
    except Exception:
        return False


# =================================================================================================================
# C6 -- SCHEMA RECOGNITION + HYPOTHESIS LATTICE + COST-WEIGHTED BST + DEAD-FRONTIER MINT
# =================================================================================================================
class HypothesisLattice:
    """C6. Holds objective hypotheses from concrete to maximally-general and prunes ONLY on divergent observations
    (fork/keep where hypotheses predict *different* outcomes; collapse where they agree). Keeps the branch graph
    small: you carry the surviving-consistent set, not the whole tree. When it empties, the answer was outside the
    grammar -- the dead-frontier mint trigger.

    Each hypothesis is a dict: {'spec':..., 'weight':float, 'predict': callable(state, action)->hashable | None}."""

    def __init__(self, hypotheses):
        self.live = [dict(h) for h in hypotheses]

    def observe(self, state, action, real_obs):
        """Prune hypotheses whose prediction diverges from the real observation. Hypotheses without a predictor, or
        whose prediction matches, survive. If the observation did not discriminate (all agree), nothing is pruned."""
        keep, drop = [], []
        for h in self.live:
            pf = h.get("predict")
            if pf is None:
                keep.append(h); continue
            try:
                ok = (pf(state, action) == real_obs)
            except Exception:
                ok = True
            (keep if ok else drop).append(h)
        if keep:                                            # never prune to empty on a single obs unless truly dead
            self.live = keep
        return self.live

    def divergent(self, state, action):
        """Do the live hypotheses disagree about the outcome of `action`? Only then is a probe worth spending."""
        preds = set()
        for h in self.live:
            pf = h.get("predict")
            if pf is None:
                continue
            try:
                preds.add(pf(state, action))
            except Exception:
                pass
        return len(preds) > 1

    def dead_frontier(self):
        return len(self.live) == 0

    def committed(self):
        """The single surviving hypothesis, if the lattice has collapsed to one; else None (stay general)."""
        return self.live[0]["spec"] if len(self.live) == 1 else None


def next_probe_by_infogain(lattice, candidate_actions, predict_for, cost_fn=lambda a: 1.0):
    """C6. Cost-weighted BST: choose the action whose outcome splits the surviving hypotheses closest to in half
    (max information gain) PER UNIT action cost. Reads are free; actions cost budget and can end a level -- so this
    is optimal-decision-tree-under-test-costs, not textbook BST. `predict_for(hyp, action) -> hashable`."""
    best, best_score = None, -1.0
    n = len(lattice.live) or 1
    for a in candidate_actions:
        buckets = defaultdict(int)
        for h in lattice.live:
            try:
                buckets[predict_for(h, a)] += 1
            except Exception:
                buckets[None] += 1
        counts = [c for c in buckets.values() if c]
        ent = -sum((c / n) * math.log2(c / n) for c in counts) if len(counts) > 1 else 0.0
        score = ent / max(1e-6, float(cost_fn(a)))
        if score > best_score:
            best_score, best = score, a
    return best, best_score


def dead_frontier_mint(lattice, growth_candidates):
    """C6. When EVERY grammar-expressible hypothesis is falsified at once, that is a *proof* the answer lies outside
    the current grammar -- the clean, principled signal to MINT a new primitive from the growth candidates, rather
    than keep pruning a tree that cannot contain the answer."""
    if lattice.dead_frontier():
        return {"mint": True, "candidates": list(growth_candidates),
                "reason": "dead frontier: all expressible hypotheses falsified -> answer is outside the grammar"}
    return {"mint": False}


# Known schemas by SIGNATURE (frame-only structural cues), used to recognise a new game as an instance of a solved
# shape -- so cn04's win transfers to vc33 without reasoning it out in-game each time.
SCHEMAS = {
    "MATCH_SKILL": {
        "gloss": "match a set of controllables to a set of targets by a KEY, then apply a per-pair placement SKILL",
        "signature": "multiple controllable objects AND multiple targets in >=2 correspondence classes",
        "instances": {"cn04": ("key=tip_geometry", "skill=interlock"),
                      "vc33": ("key=colour", "skill=accumulate")},
    },
    "ACCUMULATE": {
        "gloss": "drive ONE quantity along an axis to a target level (MORE/LESS until SAME)",
        "signature": "single controllable, single target, 1-D drive",
        "instances": {"vc33-level0": ("key=colour", "skill=accumulate")},
    },
}


def recognize_schema(individuation, n_target_classes):
    """C6. Recognise which known schema a game is an instance of, from structural cues (how many controllable objects
    move, how many target/correspondence classes). Returns the schema name + its per-instance (key, skill) slots to
    plug into `match_skill_plan`. Multiple movers or >=2 correspondence classes => the general MATCH_SKILL; a single
    mover to a single target => the ACCUMULATE special case (a MATCH_SKILL with N=1)."""
    mob = individuation.get("mobility") or []
    n_movers = sum(1 for m in mob if m > 0)
    if n_movers >= 2 or n_target_classes >= 2:
        return {"schema": "MATCH_SKILL", "n_movers": n_movers, "n_classes": n_target_classes}
    return {"schema": "ACCUMULATE", "n_movers": n_movers, "n_classes": n_target_classes}


# =================================================================================================================
# THE GENERAL MATCH_BY_KEY o PER_PAIR_SKILL SCHEMA  (cn04 & vc33 as pluggable instances; arity-invariant)
# =================================================================================================================
def match_by_key(controllables, targets, key_fn):
    """Scale-free correspondence: greedily pair each controllable with the target minimising key_fn (no arity cap --
    identical path at N=1 and N=10^4). `key_fn(c, t) -> float` (0 = perfect match; large = incompatible). Returns
    [(ctrl_idx, tgt_idx, cost), ...]."""
    edges = sorted((float(key_fn(c, t)), i, j)
                   for i, c in enumerate(controllables) for j, t in enumerate(targets))
    uc, ut, pairs = set(), set(), []
    for d, i, j in edges:
        if i in uc or j in ut:
            continue
        uc.add(i); ut.add(j); pairs.append((i, j, d))
    return pairs


def key_colour(c, t):
    """vc33 correspondence key: 0 if the controllable's marker colour equals the target's colour, else large."""
    return 0.0 if c.get("colour") == t.get("colour") else 1e6


def key_geometry(c, t):
    """cn04 correspondence key: mirror/size similarity of the two pieces (smaller = more similar)."""
    return abs(c.get("size", 0) - t.get("size", 0))


def skill_accumulate(controllable, target, amap):
    """vc33 PER-PAIR SKILL: drive the controllable's marker to the target coordinate -- MORE/LESS until SAME. The step
    count is closed-form via the learned per-action displacement (`amap`); no search."""
    mp = controllable.get("marker_pos"); tp = target.get("pos")
    if mp is None or tp is None:
        return []
    return OV._translate_actions(tp[0] - mp[0], tp[1] - mp[1], dict(amap or {}))


def skill_interlock(controllable, target, nullary, amap, rotate_actions, ctrl):
    """cn04 PER-PAIR SKILL: rotate to orient + closed-form joint translation so both tip pairs coincide, bodies
    disjoint. Delegates to the built pairwise-joint atom."""
    seq, _cost = OV._pair_joint_solve(controllable, OV._clusters_cen(target.get("tips", set())),
                                      target.get("body", set()), list(nullary), dict(amap or {}),
                                      set(rotate_actions or ()), ctrl)
    return seq


def match_skill_plan(controllables, targets, key_fn, skill_fn, select_action=None):
    """THE GENERAL SCHEMA: MATCH_BY_KEY(controllables, targets, key) then PER_PAIR_SKILL for each matched pair.
    Arity-invariant -- N=1 (the ACCUMULATE special case) and N=many are the SAME code path. `skill_fn(c, t) -> action
    sequence`. If `select_action` is given, a (select_action, ctrl_idx) is emitted before each pair's skill (grounded
    by C-P3's induced selection semantics). cn04: key_geometry + skill_interlock. vc33: key_colour + skill_accumulate.

    This is the transfer artifact: the cn04 win generalises to vc33 by swapping the KEY (geometry->colour) and the
    SKILL (interlock->accumulate); the outer matching + per-pair structure is unchanged."""
    pairs = match_by_key(controllables, targets, key_fn)
    plan = []
    for (i, j, _d) in pairs:
        if select_action is not None:
            plan.append((select_action, i))
        seq = skill_fn(controllables[i], targets[j])
        if seq:
            plan += list(seq)
    return plan


# =================================================================================================================
# WIRING (Layer-2 direction) -- the ONLY place the two layers connect, and it runs one-way (orchestrator -> both).
# =================================================================================================================
def wire(register=None):
    """Register the Layer-1 controllers into the flow's hook registry (inversion of control). Call ONCE from the
    orchestrator/harness -- e.g. `import autonomy_controllers as AC; AC.wire()`. After this, the flow reaches a
    controller via `OV.controller_hook(name)` and never imports this module, so the dependency graph stays an acyclic
    DAG (objective_validator <- autonomy_controllers <- orchestrator). Returns the registered hook names."""
    reg = register or OV.register_controller_hook
    reg("objective_induction", induce_objective_from_reward)      # C1
    reg("individuation", individuate_by_comovement)               # C2
    reg("fidelity_monitor", FidelityMonitor)                      # C3 (factory)
    reg("coupling_granularity", detect_coupling_granularity)      # C4
    reg("worst_case_extrapolation", extrapolate_worst_predictable)# C5
    reg("invariance_probe", invariance_probe)                     # C5
    reg("schema_recognizer", recognize_schema)                    # C6
    reg("hypothesis_lattice", HypothesisLattice)                  # C6 (factory)
    reg("next_probe", next_probe_by_infogain)                     # C6
    reg("dead_frontier_mint", dead_frontier_mint)                 # C6
    reg("schema_planner", match_skill_plan)                       # MATCH o SKILL
    return sorted(getattr(OV, "_CONTROLLER_HOOKS", {}).keys())
