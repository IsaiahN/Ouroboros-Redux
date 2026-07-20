# -*- coding: utf-8 -*-
"""Regime factory + shared-services registry.

WHY THIS EXISTS
---------------
The avatar vs actuator split is a LEGITIMATE bifurcation: an avatar game ("one of these objects IS me; the action is
my locomotion") and an actuator game ("I act on external objects and read the effect") have genuinely different
dynamics, so each needs its own perception + primitives. That is NOT duplication.

What WOULD be duplication -- and what this module prevents -- is every regime re-implementing the mechanisms that are
regime-AGNOSTIC: shape extraction, win-condition induction, the win-predicate library, the spatial occupancy map,
residual triangulation, and grid pathfinding. Those must live in ONE place and be reused by every regime.

THE PATTERN
-----------
  * SHARED        -- a single registry of the regime-agnostic services (the one source of truth). Lazy imports avoid
                     import cycles; each service resolves to the existing canonical implementation.
  * Regime        -- the ABC every regime implements: the shared reasoning SKELETON
                     (perceive -> model -> derive-objective -> plan -> confirm -> transfer -> revise). Subclasses supply
                     regime-SPECIFIC perception + primitives, and pull every shared mechanism from SHARED.
  * make_regime() -- probes the game once ("is one of these objects ME?") and returns the right Regime. Regime SELECTION
                     lives here, in ONE place.

ADDING A NEW REGIME (the anti-rework contract)
----------------------------------------------
  1. Subclass Regime, implement solve() (and, over time, the skeleton steps) using SHARED for anything agnostic.
  2. Register its detection in make_regime().
  3. Do NOT re-implement anything already in SHARED -- extend SHARED instead, so all regimes gain it at once.
"""


class SharedServices:
    """The SINGLE registry of regime-agnostic mechanisms. Every regime reuses these; nothing here is duplicated per
    regime. Implementations resolve lazily to their canonical home to avoid import cycles."""

    # ---- perception primitives ----
    @staticmethod
    def object_props(g, ys, xs):
        """Scale-invariant shape/orientation/colour descriptor for one object (lossless integer scale-reduction)."""
        from objective_validator import _object_props
        return _object_props(g, ys, xs)

    @staticmethod
    def frame_glyphs(g):
        """Compact non-background glyph candidates in a frame, with property vectors."""
        from objective_validator import _frame_glyphs
        return _frame_glyphs(g)

    # ---- objective learning (shared by BOTH regimes) ----
    @staticmethod
    def win_predicate_lib(g):
        """The shared predicate library: SAME_ROW/COLUMN (spatial) + SAME_SHAPE/ORIENTATION/COLOUR (property)."""
        from objective_validator import _win_predicate_lib
        return _win_predicate_lib(g)

    @staticmethod
    def induce_win_condition(ring, know):
        """Deconstruct a win into a win-condition (violated->satisfied), with AND-growth + coincidence-pruning."""
        from objective_validator import _induce_win_condition
        return _induce_win_condition(ring, know)

    # ---- self-correction (shared) ----
    @staticmethod
    def triangulate(residual, min_shadow=0.15):
        """Regime-agnostic residual triangulation: which layer casts the shadow (correlate >= threshold)."""
        import evolvability_engine as _EE
        return _EE.triangulate(residual, min_shadow=min_shadow)

    # ---- spatial reasoning (shared) ----
    @staticmethod
    def spatial_map(ttl=80):
        """A fresh per-cell occupancy map (learns FREE/BLOCKED from movement outcomes; dynamic; frontier exploration)."""
        from spatial_map import SpatialMap
        return SpatialMap(ttl=ttl)

    @staticmethod
    def pathfind(g, start, target, steer, quantum, wall_colours, blocked=None):
        """Grid BFS -> action sequence, blocked by wall colours AND the shared map's learned dead ends."""
        from objective_validator import _avatar_pathfind
        return _avatar_pathfind(g, start, target, steer, quantum, wall_colours, blocked=blocked)


import numpy as _np


class DownsampleError(Exception):
    """Raised when perception would reduce the grid's native resolution. Downsampling the grid is BANNED (it destroys
    the exact per-cell symbolic signal ARC-3 depends on). See working log Section 7."""


class Perception:
    """The SINGLE regime-agnostic perception gateway. BOTH regimes (avatar + actuator) read the grid and extract objects
    through THIS -- so a perceptual invariant or fix lands for every regime at once, and the no-downsample rule is
    enforced BY CONSTRUCTION rather than by discipline:

      * grid(adapter)  -- returns the FULL-resolution frame and asserts it is never smaller than its native shape
                          (any upstream downsample raises DownsampleError at runtime).
      * object_props()/objects() -- use the LOSSLESS scale-invariant descriptor (integer scale-reduction, never
                          interpolation), so a 2x glyph and a 1x glyph compare equal WITHOUT resizing the grid.

    There is deliberately NO resize / zoom / bucketing primitive on this class: to downsample you would have to bypass
    the gateway, which is visible in review and caught by assert_no_downsampling() in tests."""

    def __init__(self):
        self._native = {}                                      # per-adapter native (H, W)

    def grid(self, adapter):
        raw = _np.asarray(adapter._grid(adapter._obs))
        g2 = raw[0] if raw.ndim == 3 else raw                  # 2D view for the resolution check
        # A detected LOGICAL-CELL spec is a LEGITIMATE, lossless reduction: for a scaled/tiled render each logical cell is
        # a uniform block, and the logical grid IS the game state (this is the composer's NATIVE grain, not a downsample).
        # When the adapter carries such a spec AND the incoming shape matches the detected logical (nr, nc), rebase the
        # native reference to the logical grid instead of tripping the guard -- the ban is for LOSSY / UNVERIFIED
        # resolution loss, which (no spec, or a shape that does not match the spec) still raises below.
        spec = getattr(adapter, "_spec", None)
        if isinstance(spec, dict) and spec.get("nr") and spec.get("nc") and g2.shape == (spec["nr"], spec["nc"]):
            self._native[id(adapter)] = g2.shape               # logical grid becomes the native reference (legitimate)
            return raw
        nat = self._native.setdefault(id(adapter), g2.shape)
        if g2.shape[0] < nat[0] or g2.shape[1] < nat[1]:
            raise DownsampleError("grid %s is smaller than native %s -- downsampling is banned" % (g2.shape, nat))
        return raw                                             # RAW shape returned -> drop-in for np.asarray(adapter._grid(...))

    def layers(self, adapter):
        """Every grid the world produced for this observation, in order, full resolution.

        `grid()` goes through `adapter._grid` == `frame[-1]` -- the SETTLED state. Transients live in the earlier
        layers and are gone by the last one, so anything that flashes is invisible to every caller of `grid()`.
        Same guard, whole stack; mirrors `_ingest`'s logical-spec reduction so the grain matches `grid()`.
        """
        raw = getattr(getattr(adapter, "_obs", None), "frame", None)
        if raw is None:
            return []
        arr = _np.asarray(raw)
        if arr.size == 0:
            return []
        stack = [arr] if arr.ndim == 2 else [_np.asarray(l) for l in arr]
        spec = getattr(adapter, "_spec", None)
        out = []
        for L in stack:
            if getattr(L, "ndim", 0) != 2:
                continue
            if isinstance(spec, dict) and spec.get("nr") and spec.get("nc"):
                try:
                    import grid_perception as _GP
                    L = _np.asarray(_GP.downsample(L, spec))
                except Exception:
                    pass
            else:
                nat = self._native.get(id(adapter))
                if nat and (L.shape[0] < nat[0] or L.shape[1] < nat[1]):
                    raise DownsampleError("layer %s is smaller than native %s -- downsampling is banned"
                                          % (L.shape, nat))
            out.append(L)
        return out

    @staticmethod
    def object_props(g, ys, xs):
        from objective_validator import _object_props           # lossless scale-reduction (never interpolation)
        return _object_props(g, ys, xs)

    @staticmethod
    def objects(g):
        from objective_validator import _frame_glyphs
        return _frame_glyphs(g)

    @staticmethod
    def interiors(g):
        """HOLLOW-FRAME interior detection (full-res): for each non-background colour, the cells enclosed by that colour
        but not OF that colour are its interior slot(s) -- the CONTAIN_FIT target a fitting piece must enter. Returns
        [(frame_colour, (row, col) centroid, size), ...], background excluded. This is the piece cn04 needs to target
        the frame's slot instead of the frame's walls (or its own body). No downsampling."""
        from scipy.ndimage import label as _lbl, binary_fill_holes as _fill
        g = _np.asarray(g)
        bg = int(_np.bincount(g.ravel()).argmax())             # background = most common colour (excluded)
        out = []
        for c in _np.unique(g):
            if int(c) == bg:
                continue
            m = (g == c)
            if m.sum() < 8 or m.sum() > g.size * 0.4:          # a frame is a moderate ring, not tiny, not the background
                continue
            hole = _fill(m) & ~m                               # enclosed-but-not-the-colour = the hollow interior
            lab, n = _lbl(hole, structure=_np.ones((3, 3)))
            for i in range(1, n + 1):
                ys, xs = _np.where(lab == i)
                if len(ys) >= 6:
                    out.append((int(c), (int(ys.mean()), int(xs.mean())), int(len(ys))))
        return out


# Grid-downsampling primitives that are NEVER allowed to touch the perception grid. A static scan (below) fails the
# build if any appear -- so the rule is enforced by the code, not by anyone remembering it.
_BANNED_PATTERNS = [
    (r"cv2\.resize\s*\(", "opencv-resize"),
    (r"\.thumbnail\s*\(", "pil-thumbnail"),
    (r"transform\.resize\s*\(|transform\.rescale\s*\(", "skimage-resize"),
    (r"ndimage\.zoom\s*\(|[^_a-zA-Z]zoom\s*\(", "scipy-zoom"),
    (r"block_reduce\s*\(", "blockreduce"),
    (r"pyrDown\s*\(|pyramid_reduce\s*\(", "pyramid-downsample"),
    (r"interp2d\s*\(|griddata\s*\(", "interp-resample"),
    (r"\[::[2-9][\],]", "stride-subsample"),
]


def assert_no_downsampling(*paths):
    """STATIC GUARD (run in tests/CI): scan the given source files and RAISE DownsampleError if any grid-downsampling
    primitive appears outside a comment. This is how 'no downsampling, ever' is enforced by the code itself. Position
    bucketing for the MOVEMENT lattice (pixel//quantum for navigation) is a navigation graph, not a perception
    downsample, so it is not banned here -- perception must go through Perception, which never resizes."""
    import re, os
    violations = []
    for path in paths:
        if not os.path.exists(path):
            continue
        for i, line in enumerate(open(path), 1):
            s = line.split("#", 1)[0]                           # ignore comments
            if not s.strip():
                continue
            for pat, name in _BANNED_PATTERNS:
                if re.search(pat, s):
                    violations.append("  %s:%d  [%s]  %s" % (os.path.basename(path), i, name, s.strip()[:70]))
    if violations:
        raise DownsampleError("DOWNSAMPLING IS BANNED but found:\n" + "\n".join(violations))
    return True


SHARED = SharedServices()
SHARED.perception = Perception()                               # the one perception gateway, shared by all regimes


class FrameDoubt:
    """Regime-AGNOSTIC frame-doubt, in SHARED so every regime uses the same machinery (no regime re-implements it). A
    regime supplies its CURRENT frame and its frame-specific evidence; this returns the re-abduction target (or None),
    typed by the avatar-vs-non-avatar axis. The competing-frame SIGNATURES come from SHARED.perception, so structural
    detection is never duplicated. Mid-game handling (per-level re-arm) stays with the caller, which owns the level loop."""

    MIN_SLOT = 20

    @staticmethod
    def contain_fit_signature(g):
        """The stationary hollow frame's interior slot (the CONTAIN_FIT target), via the shared perception gateway."""
        slots = SHARED.perception.interiors(g)
        slot = max(slots, key=lambda s: s[2]) if slots else None
        return slot if (slot and slot[2] >= FrameDoubt.MIN_SLOT) else None

    @staticmethod
    def evaluate(g, current_frame, gate_ever_readable, actions_spent):
        """Decide whether to abandon the CURRENT frame and re-abduce. Avatar/MATCH frame: if no key/lock gate was EVER
        readable (not just this frame) AND a NON-AVATAR CONTAIN_FIT signature is present, the game is not an avatar/MATCH
        game -> re-abduce across the avatar boundary. Returns {'toward','slot','from'} or None."""
        if current_frame == "avatar" and not gate_ever_readable and actions_spent >= 8:
            slot = FrameDoubt.contain_fit_signature(g)
            if slot:
                return {"from": "avatar", "toward": "contain_fit", "slot": slot, "crosses_avatar_boundary": True}
        return None

    @staticmethod
    def falsification_evidence(g, current_frame, gate_ever_readable):
        """FALSIFICATION-SEEKING stance (Popperian), the antidote to metric-conviction. Instead of asking 'what SUPPORTS
        my frame' (the confirmation loop the drift trap runs on), name what would FALSIFY the current frame and check
        whether that evidence is PRESENT. Crucially, proxies-going-up are INERT here -- a rising fractional score / a
        closing residual is NOT evidence against the frame, so it cannot be treated as support. A hypothesis survives by
        FAILING TO BE FALSIFIED, never by accumulating proxy-support. Returns {falsifier, present, ...}."""
        if current_frame == "avatar":
            # the avatar/MATCH frame PREDICTS a key/lock gate exists. Its falsifier: no gate ever + a competing
            # (non-avatar) structural signature. If the gate WAS readable, the 'no gate ever' falsifier is absent -> the
            # frame is not falsified (and we needn't inspect the grid).
            if gate_ever_readable:
                return {"frame": current_frame, "falsifier": "no MATCH gate ever + a CONTAIN_FIT signature present",
                        "present": False, "slot": None, "note": "proxies rising are INERT -- only a falsifier counts"}
            slot = FrameDoubt.contain_fit_signature(g)
            present = slot is not None
            return {"frame": current_frame, "falsifier": "no MATCH gate ever + a CONTAIN_FIT signature present",
                    "present": present, "slot": slot, "note": "proxies rising are INERT -- only a falsifier counts"}
        return {"frame": current_frame, "falsifier": None, "present": False,
                "note": "proxies rising are INERT -- only a falsifier counts"}

    @staticmethod
    def narrate_falsification(fe):
        if fe.get("falsifier") is None:
            return "FALSIFY  frame '%s': no typed falsifier defined -> survives by default (proxies rising remain INERT)" % fe.get("frame")
        return ("FALSIFY  frame '%s' -- seeking to DISCONFIRM, not confirm. Falsifier := %s. Observed: %s. %s"
                % (fe.get("frame"), fe.get("falsifier"), "PRESENT -> frame FALSIFIED" if fe.get("present") else
                   "absent -> frame survives (not confirmed -- survival by non-falsification)",
                   "Proxies rising do NOT count as support."))


SHARED.frame_doubt = FrameDoubt()                             # regime-agnostic frame-doubt, reused by all regimes


class BudgetReachability:
    """Regime-agnostic RESOURCE-CONSTRAINED reachability planner, in SHARED. It answers not 'find a path' but 'given my
    budget and the board's economy, is the objective reachable -- possibly THROUGH a booster -- and what does it cost?'
    Inputs are the LEARNED cost model (SpatialMap.distance / nearest_reachable_to -- 'we have crossed the board, so we
    know the costs') plus the budget and known boosters. It returns the retargeted reachable cell, the net cost, a
    reachability verdict, and a NARRATION so the horizon reasoning is legible. Runs on the learned navigation lattice,
    never a perception downsample. Any regime can call it (avatar for the exit, actuator for control-reach)."""

    @staticmethod
    def plan(smap, start, objective, budget, boosters=None):
        boosters = boosters or {}
        near = smap.nearest_reachable_to(start, objective)     # blocked target (e.g. lock in a box) -> reachable frontier
        if near is None:
            return {"verdict": "unmapped", "target": None,
                    "narration": "budget %d; objective @%s is beyond the mapped region -> reachability UNKNOWN; explore "
                                 "toward it within budget rather than declare it infeasible" % (budget, tuple(objective))}
        tgt, man_gap, direct = near
        if direct <= budget:
            return {"verdict": "reachable", "target": tgt, "direct_cost": direct, "via_booster": None, "net_cost": direct,
                    "narration": "budget %d; objective reachable at cost %d (approach cell %s, %d from the target) -> "
                                 "margin %d actions -> go direct" % (budget, direct, tgt, man_gap, budget - direct)}
        best = None
        for bp, boost in boosters.items():
            to_b = smap.distance(start, bp)
            if to_b is None:
                continue
            b_near = smap.nearest_reachable_to(bp, objective)
            if b_near is None:
                continue
            b_tgt, _, from_b = b_near
            net = to_b + from_b - int(boost)                   # actions spent minus the boost collected en route
            solvent = (to_b <= budget) and (from_b <= budget - to_b + int(boost))   # budget never dips below 0
            if solvent and boost > 0 and (best is None or net < best["net"]):
                best = {"booster": bp, "boost": int(boost), "to_b": to_b, "from_b": from_b, "net": net, "b_tgt": b_tgt}
        if best is not None:
            return {"verdict": "reachable_via_booster", "target": best["b_tgt"], "direct_cost": direct,
                    "via_booster": best["booster"], "net_cost": best["net"],
                    "narration": "budget %d < direct cost %d -> not reachable directly. Booster @%s (+%d actions) is %d "
                                 "away, booster->objective is %d, net %d, solvent throughout -> route THROUGH the booster"
                                 % (budget, direct, best["booster"], best["boost"], best["to_b"], best["from_b"], best["net"])}
        return {"verdict": "infeasible", "target": tgt, "direct_cost": direct, "via_booster": None, "net_cost": direct,
                "narration": "budget %d < cost %d and no booster path is solvent -> objective budget-INFEASIBLE this "
                             "attempt (a known reachability fact, not a silent give-up)" % (budget, direct)}


SHARED.budget_path = BudgetReachability()                     # regime-agnostic resource-constrained reachability


class LearningProgress:
    """GAP 1 -- learning-progress curiosity. Tracks d(error)/dt per key (game:level:objective) -- the DERIVATIVE of
    prediction error, NOT its level -- so effort goes where LEARNING is happening. Verdicts: learning (error dropping ->
    persist), plateaued_high (flat+high -> pivot), plateaued_low (~0 -> mastered). Feeds from residual/min_disc/surprise
    the agent ALREADY emits -> a recombination, not a new sensor. Pure signal math -- touches no grid.

    MEMORY: the per-key history and the per-game cross-level TRAJECTORY are backed by the persistent knowledge store
    (_GLOBAL_KNOWLEDGE, injected via bind_store), so the drives are REMEMBERED across levels and games exactly the way
    learned atoms/passability are -- not stranded in an ephemeral singleton. This is the allostatic baseline: how
    learning went on earlier levels carries forward to set expectations on the next."""

    def __init__(self, window=6, hi=8.0, flat=0.5):
        self._local = {"hist": {}, "traj": {}}
        self.store = self._local                               # replaced by bind_store() with the persistent KN store
        self.window = int(window); self.hi = float(hi); self.flat = float(flat)

    def bind_store(self, store):
        """Point the drive memory at the persistent knowledge dict so it transfers/persists like everything else."""
        if store is not None:
            store.setdefault("hist", {}); store.setdefault("traj", {})
            self.store = store

    @property
    def hist(self):
        return self.store["hist"]

    def observe(self, key, error):
        h = self.hist.setdefault(key, [])
        h.append(float(error))
        if len(h) > 4 * self.window:
            del h[:-4 * self.window]

    def slope(self, key):
        h = self.hist.get(key, [])[-self.window:]
        if len(h) < 3:
            return None
        n = len(h); xs = list(range(n)); mx = sum(xs) / n; my = sum(h) / n
        den = sum((x - mx) ** 2 for x in xs) or 1.0
        return sum((xs[i] - mx) * (h[i] - my) for i in range(n)) / den

    def verdict(self, key):
        h = self.hist.get(key, [])
        if len(h) < 3:
            return {"state": "unknown", "slope": None, "level": (h[-1] if h else None)}
        s = self.slope(key); win = h[-self.window:]; lvl = sum(win) / len(win)
        if s is not None and s < -self.flat:
            return {"state": "learning", "slope": s, "level": lvl}
        if lvl <= self.hi * 0.25:
            return {"state": "plateaued_low", "slope": s, "level": lvl}
        if abs(s or 0.0) <= self.flat and lvl > self.hi:
            return {"state": "plateaued_high", "slope": s, "level": lvl}
        return {"state": "mixed", "slope": s, "level": lvl}

    def record_level(self, game, level, key):
        """Snapshot this level's final learning verdict into the per-GAME trajectory (the cross-level memory)."""
        v = self.verdict(key)
        t = self.store["traj"].setdefault(str(game), [])
        t.append({"level": int(level), "state": v["state"], "slope": v.get("slope"), "level_err": v.get("level")})

    def trajectory(self, game):
        """The per-game cross-level learning trajectory carried forward -- the allostatic baseline."""
        return list(self.store["traj"].get(str(game), []))

    def narrate(self, key):
        v = self.verdict(key)
        if v["state"] == "unknown":
            return "PROGRESS  %s: too few samples to gauge learning-progress yet" % (key,)
        _map = {"learning": "error DROPPING -> LEARNING -> persist",
                "plateaued_high": "error flat AND high -> PLATEAUED-HIGH -> unlearnable in this frame -> pivot",
                "plateaued_low": "error ~0 and flat -> PLATEAUED-LOW -> mastered -> cache & move on",
                "mixed": "error mixed -> keep going, watch the trend"}
        return "PROGRESS  %s: d(error)/dt=%.2f level=%.1f -> %s" % (key, (v["slope"] or 0.0), (v["level"] or 0.0), _map[v["state"]])

    def narrate_trajectory(self, game):
        t = self.trajectory(game)
        if not t:
            return None
        seq = " -> ".join("L%d:%s" % (e["level"], e["state"]) for e in t)
        fast = sum(1 for e in t if e["state"] in ("learning", "plateaued_low"))
        return ("DRIVE-MEMORY  game %s learning trajectory so far: %s  [%d/%d levels closed by learning -> %s]"
                % (game, seq, fast, len(t),
                   "this game transfers well, expect to keep learning" if fast >= len(t) - 1
                   else "learning has stalled on some levels -> a new mechanic may need fresh exploration"))

    # ---- LOSSY AFFECTIVE COMPRESSION: consolidate a finished level into a somatic marker, decay old markers, prime new ones ----
    def consolidate(self, game, level, key, solved=None):
        """PEAK-END + systems consolidation. Compress this level's RAW error series into ONE somatic marker
        {peak, end, cost, valence, state} and DROP the raw series (prune the grinding middle -- keep only the peak, the
        end, and the cumulative-cost integral). Age the existing markers (habituation). This compresses the AFFECT only;
        the SEMANTIC facts (atoms/passability/objective) stay full-fidelity in KN. Valence: solved/learning/mastered ->
        +1; stuck (plateaued_high) -> -1; else 0."""
        h = self.hist.get(key, []); v = self.verdict(key); st = v["state"]
        if solved is True or st in ("learning", "plateaued_low"):
            val = 1.0
        elif st == "plateaued_high":
            val = -1.0
        else:
            val = 0.0
        marker = {"level": int(level), "peak": (max(h) if h else 0.0), "end": (h[-1] if h else 0.0),
                  "cost": float(sum(h)), "valence": val, "state": st, "age": 0}
        markers = self.store.setdefault("markers", {}).setdefault(str(game), [])
        for m in markers:                                      # habituation: prior markers recede one step
            m["age"] = m.get("age", 0) + 1
        markers.append(marker)
        if key in self.hist:
            del self.hist[key]                                 # PRUNE the raw series -- the marker is what remains
        self.store["traj"].setdefault(str(game), []).append({"level": int(level), "state": st, "valence": val})
        return marker

    def _effective_valence(self, marker, base_decay=0.8, neg_decay=0.5):
        """Recency-decayed valence. NEGATIVE valence decays FASTER toward neutral (the HEALTHY half of the biology:
        good sleep strips the sting, keeps the lesson) -- so old frustration about a beaten level fades to ~0 rather
        than lingering raw, while positive priming persists a little longer. The lesson lives in KN either way."""
        age = marker.get("age", 0); val = marker.get("valence", 0.0)
        return val * ((neg_decay if val < 0 else base_decay) ** age)

    # ---- PROTECTED PREDICTION-ERROR INTEGRAL: the un-gameable inner signal (the RLHF substitute) ----
    def accumulate_pe(self, key, pe):
        """PROTECTED, MONOTONIC prediction-error integral. Accumulates abs(pe) at FULL magnitude every step. By the
        integral invariant (Section 12.5) NO drive may reduce or reattribute it -- there is deliberately no subtract, no
        decay, no method/frame split to launder failures through. Frame-doubt reads THIS total, so reattributing
        individual failures to 'method' cannot blind it. This is the reality-contradiction the reasoner CANNOT author (a
        forward model is a bet reality settles) -- the property RLHF provided, self-generated."""
        ig = self.store.setdefault("pe_integral", {})
        ig[key] = ig.get(key, 0.0) + abs(float(pe))
        return ig[key]

    def pe_integral(self, key):
        return self.store.get("pe_integral", {}).get(key, 0.0)

    def narrate_pe_integral(self, key):
        return ("PE-INTEGRAL  %s := %.1f (monotonic, un-suppressible, un-reattributable -- frame-doubt reads this; no "
                "drive may reduce it)" % (key, self.pe_integral(key)))

    def prior(self, game):
        """The MORNING PRIOR: aggregate the recency-decayed somatic markers for this game into a drive-prior in
        [-1, +1] that sets the STARTING stance for a new level -- hopeful+informed, not blind or raw."""
        markers = self.store.get("markers", {}).get(str(game), [])
        if not markers:
            return {"prior": 0.0, "n": 0}
        vals = [self._effective_valence(m) for m in markers]
        return {"prior": sum(vals) / len(vals), "n": len(markers)}

    def narrate_consolidate(self, game, marker):
        tone = "positive (learnable)" if marker["valence"] > 0 else ("negative (stuck)" if marker["valence"] < 0 else "neutral")
        return ("CONSOLIDATE  game %s L%d -> somatic marker {peak %.0f, end %.0f, cost %.0f, valence %s}; raw error "
                "series PRUNED (peak+end kept, grinding middle dropped). Semantic facts stay full in KN."
                % (game, marker["level"], marker["peak"], marker["end"], marker["cost"], tone))

    def narrate_prior(self, game):
        p = self.prior(game)
        if p["n"] == 0:
            return None
        pr = p["prior"]
        stance = ("this game has been learnable -> enter with persistence, exploit the known mechanic" if pr > 0.15
                  else ("this game has been hard -> enter cautiously, explore-biased" if pr < -0.15
                        else "fresh, hopeful start (old frustration has decayed toward neutral)"))
        return "DRIVE-PRIOR  game %s: %d decayed marker(s) -> drive-prior %+.2f -> %s" % (game, p["n"], pr, stance)


class Persistence:
    """GAP 2 -- opponent-process persistence (the frustration 'breadcrumb'). Allocate MORE effort where learning-progress
    is positive (the harder-but-closing problem), and cut losses where it has plateaued high. Turns a fixed budget into
    a progress-weighted one."""

    @staticmethod
    def factor(verdict):
        st = (verdict or {}).get("state")
        return {"learning": 1.5, "plateaued_high": 0.0, "plateaued_low": 0.25}.get(st, 1.0)

    @staticmethod
    def allocate(verdict, base):
        return max(1, int(round(base * Persistence.factor(verdict))))

    @staticmethod
    def narrate(verdict, base):
        f = Persistence.factor(verdict)
        return "PERSIST  learning-progress '%s' -> effort x%.2f (%d -> %d actions): %s" % (
            (verdict or {}).get("state", "?"), f, base, Persistence.allocate(verdict, base),
            "double down, we're closing" if f > 1 else ("stop, flat+hopeless" if f == 0 else "minimal, mastered/steady"))


class StochasticEscape:
    """GAP 3 -- the eps-random 'Eureka' term. When structured search is EXHAUSTED and progress has plateaued, inject a
    bounded random perturbation to jump out of the stuck attractor (simulated-annealing / random-restart analogue),
    rather than concede. Bounded + budget-guarded so it cannot thrash."""

    @staticmethod
    def perturb(candidates, budget, tried=None, k=1, rng=None):
        import random as _r
        rng = rng or _r
        tried = set(tried or ())
        pool = [c for c in (candidates or []) if c not in tried]
        if not pool or budget < 2:
            return []
        return rng.sample(pool, min(int(k), len(pool)))

    @staticmethod
    def narrate(picked):
        return ("ESCAPE  structured search exhausted + plateaued -> inject %d RANDOM probe(s) to jump the attractor "
                "(stochastic escape, budget-bounded): %s" % (len(picked), picked)) if picked else \
               "ESCAPE  no unexplored candidate or budget too low for a stochastic jump"


class Volatility:
    """GAP 4 -- volatility-modulated explore/exploit. A NEW/unstable situation (high, VARIABLE prediction error, no
    reliable priors) -> spike EXPLORE; a stable/familiar one -> EXPLOIT (transfer). Maps to Yu-Dayan expected vs
    unexpected uncertainty. Returns an explore ratio in [0,1] to bias probe-vs-transfer."""

    @staticmethod
    def explore_ratio(recent_errors):
        h = [float(e) for e in (recent_errors or [])]
        if len(h) < 3:
            return 1.0                                          # brand-new -> explore wide
        import statistics as _st
        cv = _st.pstdev(h) / (abs(_st.mean(h)) + 1.0)          # coefficient of variation = unexpected uncertainty
        return max(0.0, min(1.0, cv))

    @staticmethod
    def narrate(recent_errors):
        r = Volatility.explore_ratio(recent_errors)
        mode = "EXPLORE-biased (volatile/novel -> map wide, probe)" if r > 0.5 else \
               "EXPLOIT-biased (stable/familiar -> transfer, exploit)"
        return "VOLATILITY  prediction-error volatility -> explore-ratio %.2f -> %s" % (r, mode)


SHARED.learning_progress = LearningProgress()                 # GAP 1: d(error)/dt -- the unifying learning signal
SHARED.persistence = Persistence()                            # GAP 2: progress-weighted effort allocation
SHARED.stochastic_escape = StochasticEscape()                 # GAP 3: eps-random escape from local minima
SHARED.volatility = Volatility()                              # GAP 4: volatility-modulated explore/exploit


class HypothesisLedger:
    """The single PROMOTION AUTHORITY (Section 14, rule 1). A hypothesis -- an objective, a frame, a win-condition -- is
    PROVISIONAL until a REAL WIN promotes it to CONFIRMED. NO self-measured signal (residual, fractional score, coverage,
    probe outcome) may promote it; those only GUIDE search WITHIN a frame. This removes the agent's ability to author its
    own reward by moving a proxy -- the metric-conviction trap -- because only reality (a win) can confirm. Backed by the
    transferable store so confirmations persist/transfer like knowledge. Pure bookkeeping -- no grid, no downsampling."""

    def __init__(self):
        self._local = {"status": {}}
        self.store = self._local

    def bind_store(self, store):
        if store is not None:
            store.setdefault("status", {})
            self.store = store

    def note(self, key):
        """Register/keep a hypothesis as PROVISIONAL (idempotent; never downgrades a confirmed one)."""
        self.store["status"].setdefault(key, {"status": "provisional", "wins": 0})
        return self.store["status"][key]["status"]

    def guide(self, key, signal_name):
        """A self-measured signal touched this hypothesis. It may GUIDE search but NEVER confirm -> status UNCHANGED."""
        self.note(key)
        return self.store["status"][key]["status"]             # still provisional; the signal is inert for promotion

    def confirm_by_win(self, key):
        """The ONLY promotion path. A real win promotes provisional -> confirmed."""
        s = self.store["status"].setdefault(key, {"status": "provisional", "wins": 0})
        s["wins"] += 1; s["status"] = "confirmed"
        return s

    def status(self, key):
        return self.store["status"].get(key, {"status": "provisional", "wins": 0})["status"]

    def narrate(self, key, signal_name=None):
        if signal_name is not None:
            return ("PROMOTION  '%s' touched by self-measured signal '%s' -> GUIDES search only, does NOT confirm "
                    "(status stays %s; only a WIN promotes)" % (key, signal_name, self.status(key)))
        return "PROMOTION  '%s' status := %s (only a real win confirms)" % (key, self.status(key))


SHARED.hypothesis_ledger = HypothesisLedger()
try:
    import composer_vcs as _CVCS, primitive_ledger as _PLED
    SHARED.composer_vcs = _CVCS.ComposerVCS()          # versions the learned knowledge; composer can self-revert
    import hypothesis_market as _HM
    SHARED.hypothesis_market = _HM.HypothesisMarket()  # micro-HGT idea-economy: competing objective-hypotheses (Friston-weighted)
    import resonance_market as _RM
    SHARED.resonance_market = _RM.ResonanceMarket(SHARED.hypothesis_market)  # 4 v4 accelerants, FMap-transformed to n=1
    SHARED.resonance_market.declare_source("perception_transition","frontier")  # ~Pioneer (blind percept)
    SHARED.resonance_market.declare_source("induction_reconfirm","consensus")   # ~Generalist (history)
    SHARED.refactor_ledger = _PLED.PrimitiveLedger()   # regression suite: verified predictions gate restructures
except Exception:
    SHARED.composer_vcs = None; SHARED.refactor_ledger = None
                 # Section 14 rule 1: win is the ONLY promotion authority


class Coherence:
    """Compass #2 (Section 15): global-PE / coherence. Scores a candidate hypothesis against WON-CONFIRMED knowledge --
    does it contradict priors we have actually WON on? (Good reasoning does not require rejecting things already proven.)
    This is a GUIDE / ORDERING signal ONLY: it deprioritises a dissonant branch, but by the invariants it may NOT confirm,
    may NOT reject, and may NOT suppress the PE integral -- only a win confirms, only a falsifier rejects, coherence does
    neither. It reads the confirmed set from wins (via `assert_fact`, called on the win path), so it checks against wins,
    not proxies -> ungameable. Pure bookkeeping, no grid."""

    def __init__(self):
        self._local = {"confirmed_facts": {}}
        self.store = self._local

    def bind_store(self, store):
        if store is not None:
            store.setdefault("confirmed_facts", {})
            self.store = store

    def assert_fact(self, key, value):
        """Record a WON-CONFIRMED fact (a prior we proved). Called only from a win path."""
        self.store["confirmed_facts"][key] = value

    def dissonance(self, hypothesis):
        """How much `hypothesis` (a dict of proposed facts) CONTRADICTS confirmed facts. 0 = coherent; >0 = dissonant
        (deprioritise, do NOT reject)."""
        cf = self.store["confirmed_facts"]
        conflicts = [(k, cf[k], v) for k, v in (hypothesis or {}).items() if k in cf and cf[k] != v]
        return {"n": len(conflicts), "conflicts": conflicts}

    def narrate(self, hypothesis):
        d = self.dissonance(hypothesis)
        if d["n"] == 0:
            return "COHERENCE  hypothesis coherent with all won-confirmed priors -> no dissonance (branch keeps its rank)"
        cs = "; ".join("%s: won=%s vs proposed=%s" % (k, a, b) for k, a, b in d["conflicts"][:3])
        return ("COHERENCE  hypothesis contradicts %d won-confirmed prior(s) [%s] -> DISSONANCE -> deprioritise this "
                "branch (GUIDE only: a win still confirms, a falsifier still rejects -- coherence does neither)"
                % (d["n"], cs))

    @staticmethod
    def model_coherence(labeling):
        """Gap 3: score a MODEL / role-LABELING for INTERNAL coherence -- does this semantic labeling produce a coherent,
        PLAYABLE model? This is regime-agnostic and rejects incoherent labelings REGARDLESS of won priors -- it is what
        would have rejected the salience-based boundary (the id-4 scale-decoy) in favour of boundary-by-function, because
        the decoy labeling separates nothing and embeds no markers. `labeling` is a dict of coherence facts (1/0 or
        counts). Returns {n_incoherent, reasons}. Generic checks: a role that does nothing, a win that can't be
        evaluated, an empty gated set, a self/controllable that never moves."""
        bad = []
        if labeling.get("boundary_present", 0) and not labeling.get("boundary_separates", 1):
            bad.append("boundary separates nothing (salience decoy, not a functional boundary)")
        if labeling.get("boundary_present", 0) and not labeling.get("boundary_embeds_markers", 1):
            bad.append("boundary embeds no markers (labeling a decoy as boundary)")
        if "win_evaluable" in labeling and not labeling.get("win_evaluable"):
            bad.append("win-condition is not evaluable under this model")
        if "gated_count" in labeling and labeling.get("gated_count", 1) == 0:
            bad.append("no gated objects -> nothing to satisfy (degenerate model)")
        if "self_moves" in labeling and not labeling.get("self_moves"):
            bad.append("labeled 'self' never moves under actions (not actually controllable)")
        if "operators_effective" in labeling and labeling.get("operators_effective", 1) == 0:
            bad.append("no operator has any measured effect (model has no dynamics)")
        return {"n": len(bad), "reasons": bad}

    def narrate_model(self, labeling):
        c = Coherence.model_coherence(labeling)
        if c["n"] == 0:
            return "MODEL-COHERENCE  role-labeling is internally coherent + playable -> accept this model structure"
        return ("MODEL-COHERENCE  role-labeling INCOHERENT (%s) -> REJECT this structure and try another mechanics "
                "hypothesis (the automated version of 'that labeling can't be right')" % "; ".join(c["reasons"]))


class SomaticMarker:
    """Compass #4 (Section 15): somatic-marker pruning (Damasio). Before fully evaluating a branch, run a CHEAP, low-res
    'what will this feel like' estimate and prune high-effort/low-payoff branches -- an A*/MCTS value-heuristic analogue.
    Composes EXISTING parts: the consolidated drive VALENCE (learning_progress markers -> how this kind of branch FELT
    before) + the metabolic COST (budget_path distance) + expected payoff. It PRUNES / ORDERS only; it never rejects a
    branch as FALSE (the invariants) -- a pruned branch is deprioritised, not disproven. Pure signal math, no grid."""

    @staticmethod
    def value(prior_valence, cost, payoff, budget):
        """Cheap scalar: payoff - normalised metabolic effort + the decayed somatic prior. High -> pursue; low -> prune."""
        return float(payoff) - (float(cost) / max(1.0, float(budget))) + 0.5 * float(prior_valence)

    @staticmethod
    def verdict(prior_valence, cost, payoff, budget, keep_above=0.0):
        v = SomaticMarker.value(prior_valence, cost, payoff, budget)
        return {"value": v, "prune": v < keep_above}

    @staticmethod
    def narrate(name, prior_valence, cost, payoff, budget):
        r = SomaticMarker.verdict(prior_valence, cost, payoff, budget)
        return ("SOMATIC  branch '%s': payoff %.2f - effort %.2f + prior-affect %.2f -> value %.2f -> %s (cheap visceral "
                "pre-prune; ORDERING only, never a rejection of truth)"
                % (name, float(payoff), float(cost) / max(1.0, float(budget)), 0.5 * float(prior_valence),
                   r["value"], "PRUNE" if r["prune"] else "pursue"))


SHARED.coherence = Coherence()                                # Compass #2: dissonance vs won-confirmed priors (guide only)
SHARED.somatic_prune = SomaticMarker()                        # Compass #4: cheap affective branch pruning (order only)


class ModelDoubt:
    """Gaps 1 & 4: falsify the MODEL, not just the plan/objective. frame_doubt asks 'is my OBJECTIVE/FRAME wrong?';
    ModelDoubt asks 'is my MODEL OF THE RULES wrong?' -- the deeper doubt. A self-consistent model can still be FALSE; the
    only tell is a forward-model residual that is STRUCTURED (systematic -- same aspect/region mispredicted) and
    PERSISTENT (not transient noise). When that holds, the residual should escalate to RE-DERIVING the mechanics, not to
    re-probing controls under the same (wrong) model. Regime-AGNOSTIC: it consumes the residual stream that already flows
    for BOTH the avatar path (displacement/objective residual) and the actuator path (fluid/objective residual, via the
    FidelityMonitor). Pure signal math, no grid. Keyed by game:regime so avatar and non-avatar doubt independently."""

    def __init__(self, persist=3):
        self._local = {"resid": {}}
        self.store = self._local
        self.persist = int(persist)

    def bind_store(self, store):
        if store is not None:
            store.setdefault("resid", {})
            self.store = store

    def observe(self, key, residual, signature=None):
        """Record a forward-model residual for `key` (game:regime). `signature` = a coarse WHERE/WHAT descriptor so we can
        tell a SYSTEMATIC residual (same signature repeatedly) from scattered noise."""
        r = self.store["resid"].setdefault(str(key), {"vals": [], "sigs": []})
        r["vals"].append(float(residual)); r["vals"] = r["vals"][-8:]
        r["sigs"].append(signature); r["sigs"] = r["sigs"][-8:]

    def is_structured(self, key):
        r = self.store["resid"].get(str(key))
        if not r or len(r["vals"]) < self.persist:
            return False
        recent = r["vals"][-self.persist:]
        persistently_high = all(v > 0 for v in recent)          # residual has not gone away
        sigs = [s for s in r["sigs"][-self.persist:] if s is not None]
        systematic = (len(set(sigs)) <= 1) if sigs else True     # same aspect mispredicted (not scattered) -> structured
        return persistently_high and systematic

    def verdict(self, key):
        return "model-suspect" if self.is_structured(key) else "model-ok"

    def narrate(self, key):
        if self.is_structured(key):
            return ("MODEL-DOUBT  forward-model residual for '%s' is STRUCTURED + PERSISTENT -> the MODEL OF THE RULES is "
                    "suspect (a self-consistent model can still be FALSE) -> RE-DERIVE mechanics, do not re-probe under "
                    "the same model" % key)
        return ("MODEL-DOUBT  residual for '%s' unstructured/transient -> model not yet falsified (keep current model)"
                % key)


class MechanicsHypotheses:
    """Gap 2: a search space over the STRUCTURE of the game's rules (not plans within a FIXED model). Generalizable
    META-hypothesis TEMPLATES -- each a structural transform of the current model -- that transfer across games and apply
    to BOTH avatar and non-avatar regimes. When ModelDoubt says the model is suspect, these are the alternatives to test
    (each scored by Coherence.model_coherence + forward-model residual, promoted only by a real win):
      * PARTITION       -- not all role-objects are active; some are INERT (conduits / distractors).
      * ATTRIBUTE_SPLIT -- an object carries TWO distinct attributes (e.g. a target level vs a capacity ceiling).
      * OPERATOR_RELATION -- controls are RELATIONAL edges (donor->receiver) not ABSOLUTE adders.
      * ROLE_BY_FUNCTION -- assign a role by what it DOES, not by salience (size/colour) -> rejects decoys.
      * CORRESPONDENCE  -- bind two object-sets by a shared ATTRIBUTE (e.g. colour), orientation-free (MATCH primitive).
      * FRAME_SWITCH    -- the controllable/self or the whole regime is mis-identified (defer to frame_doubt).
    Pure symbolic, no grid. These are exactly the corrections a human supplied by eye this project -- made enumerable."""

    TEMPLATES = [
        ("PARTITION", "not all role-objects are active; some are inert"),
        ("ATTRIBUTE_SPLIT", "an object carries two distinct attributes (target vs ceiling)"),
        ("OPERATOR_RELATION", "controls are relational edges (donor->receiver), not absolute adders"),
        ("ROLE_BY_FUNCTION", "assign a role by function, not by salience (size/colour) -- reject decoys"),
        ("CORRESPONDENCE", "bind two object-sets by a shared attribute, orientation-free"),
        ("FRAME_SWITCH", "the self/controllable or the whole regime is mis-identified"),
    ]

    @staticmethod
    def enumerate(applied=None):
        applied = set(applied or ())
        return [(n, d) for (n, d) in MechanicsHypotheses.TEMPLATES if n not in applied]

    @staticmethod
    def narrate(hyps):
        if not hyps:
            return "MECHANICS-HYP  all structural hypotheses already applied -> the model structure is exhausted"
        return ("MECHANICS-HYP  MODEL suspect -> structural hypotheses to test (transforms of the RULES, not plans): %s"
                % "; ".join("%s(%s)" % (n, d) for n, d in hyps[:5]))


SHARED.model_doubt = ModelDoubt()                             # Gaps 1&4: structured residual -> re-derive the mechanics
SHARED.mechanics_hypotheses = MechanicsHypotheses()           # Gap 2: search space over the STRUCTURE of the rules


class ControlRegime:
    """The SINGLE dynamics-based regime detector -- REPLACES per-game regimes with one re-evaluable question (HELM
    field-notes #3,#5): 'is one of these objects ME?', answered by CO-MOVEMENT, never by appearance. It classifies over
    signals the agent ALREADY computes (v18's controllable tracker + the buffer estimator + the action space), so it
    adds no new perception -- just a verdict:
      * 'avatar'       -- exactly one object's motion correlates with directional actions (ls20-class locomotion).
      * 'multi_avatar' -- two or more controllables co-move (cn04-class).
      * 'actuator'     -- nothing co-moves after enough probing, or the action space is click-only -> no 'you' on the
                          board; you operate external objects and read the effect (vc33-class).
      * 'unknown'      -- not yet enough evidence -> keep probing (bootstrap), do not commit a regime.
    RE-EVALUABLE MID-GAME: called each decision, so a game that reveals a controllable later (or loses one on a new
    level) SWITCHES path without a restart. The verdict GUIDES routing; only a WIN confirms (HELM #2,#7). Pure logic."""

    @staticmethod
    def classify(n_controllable, clicks_only, steps_probed, probe_threshold=50):
        if n_controllable is not None and n_controllable >= 2:
            return "multi_avatar"
        if n_controllable is not None and n_controllable == 1:
            return "avatar"
        if clicks_only:
            return "actuator"                                  # action space has no locomotion -> operate objects
        if steps_probed >= probe_threshold:
            return "actuator"                                  # probed enough, found no 'me' -> click/lever dynamics
        return "unknown"                                       # still searching for the controllable -> keep probing

    @staticmethod
    def route(regime):
        """Regime -> which real engine drives. NEVER a thin fallback: avatar/multi_avatar -> the mover/locomotion
        engine; actuator -> the composer/actuator engine; unknown -> keep the mover engine PROBING (it is the one that
        finds a controllable) rather than idling."""
        if regime in ("avatar", "multi_avatar"):
            return "mover"
        if regime == "actuator":
            return "composer"
        return "mover"                                         # unknown: probe with the mover engine (it hunts the self)

    @staticmethod
    def narrate(regime, n_controllable, clicks_only, steps_probed):
        detail = ("%d controllable object(s) co-move with directional actions" % n_controllable
                  if n_controllable else ("action space is click-only (no locomotion)" if clicks_only
                  else "no object co-moves after %d probing steps" % steps_probed))
        return ("REGIME  dynamics detector := %s  [%s] -> route to %s engine (re-evaluated every step; a win CONFIRMS, "
                "the read only GUIDES)" % (regime.upper(), detail, ControlRegime.route(regime)))


class DecisionReasoning:
    """Builds the REASONING payload that rides EVERY action to the API + recording (HELM #6: narrate every decision --
    a silent action runs to zero on OOD with no teacher to catch it). Regime-agnostic; BOTH the avatar and actuator
    engines attach it. It encodes the disciplines directly: the objective is a HYPOTHESIS not a fact read off a frame
    (HELM #7), only a WIN confirms it (HELM #2), and it always states what would DISPROVE the current read (HELM #3), so
    every decision is checkable. Keep values EXACT, never 'about' (HELM #1)."""

    @staticmethod
    def build(regime, action, frame_read=None, rule_hypothesis=None, expect=None, disproof=None,
              step=None, confirmed=False, extra=None):
        payload = {
            "regime": regime,
            "action": str(getattr(action, "name", action)),
            "frame_read": frame_read or "(exact objects/roles from the harness descriptor; chrome excluded)",
            "rule_hypothesis": rule_hypothesis or "(provisional: what wins here is a bet being tested by acting)",
            "expect": expect or "(what this action should change if the hypothesis holds)",
            "disproof": disproof or "(what observation would show this reading is WRONG)",
            "status": "CONFIRMED-by-win" if confirmed else "provisional -- only a level win confirms",
            "step": step,
        }
        if extra:
            try:
                payload.update(extra)
            except Exception:
                pass
        return payload

    @staticmethod
    def attach(action, payload):
        """Ride the payload on the framework action's sanctioned `reasoning` lane (sample agent: action.reasoning=...).
        No-op-safe: never raises, never alters the action's effect."""
        try:
            if action is not None and hasattr(action, "reasoning"):
                action.reasoning = dict(payload)
        except Exception:
            pass
        return action


SHARED.control_regime = ControlRegime()                       # ONE dynamics detector (avatar/multi/actuator), re-evaluable
SHARED.decision_reasoning = DecisionReasoning()               # HELM #6: reasoning payload on EVERY action (no silent acts)


class BootstrapProtocol:
    """The COLD-START protocol (Section 16). On a brand-new / OOD game the object-level compass is WEAK by definition --
    you cannot hold a CONTENT prior for unseen rules (only a STRUCTURAL one: how to find rules). The fix is not a stronger
    compass but a PHASED BOOTSTRAP that switches the OBJECTIVE FUNCTION until local rules accrue:
      * BOOTSTRAP (epistemic play): objective := maximise state-COVERAGE / surprise, NOT win-progress (Strategy 2); global
        COHERENCE gated OFF -- inert by design, only LOCAL per-action consistency counts (Strategy 3).
      * SOLVE: once >= exit_rules locally-confirmed rules exist, re-engage the full compass (coherence ON, solve restored).
    Phase is read from signals we ALREADY have: volatility (novelty), grad-PE (~0 = no traction), and the count of local
    rules (the discovered trigger-effect atoms). Local consistency = an action reliably producing a predictable
    frame-delta (the ACC-burst analogue). Exit is driven by ACCRUED LOCAL RULES, never a proxy. Pure signal/bookkeeping,
    no grid."""

    def __init__(self, exit_rules=3, consistency_hits=3):
        self._local = {"rules": {}}
        self.store = self._local
        self.exit_rules = int(exit_rules); self.consistency_hits = int(consistency_hits)

    def bind_store(self, store):
        if store is not None:
            store.setdefault("rules", {})
            self.store = store

    def observe_local(self, action_sig, delta_sig):
        """Bottom-up (Strategy 3): record that `action_sig` produced `delta_sig`. A local RULE is confirmed when the same
        action reliably yields the same delta >= consistency_hits times -- local consistency, not global coherence."""
        r = self.store["rules"].setdefault(str(action_sig), {"delta": delta_sig, "hits": 0, "confirmed": False})
        if r["delta"] == delta_sig:
            r["hits"] += 1
        else:
            r["delta"] = delta_sig; r["hits"] = 1              # the effect changed -> restart the local count
        r["confirmed"] = r["hits"] >= self.consistency_hits
        return r

    def n_confirmed_rules(self, external_count=None):
        n = sum(1 for r in self.store["rules"].values() if r.get("confirmed"))
        return n + int(external_count or 0)                    # + the existing discovered atoms passed by the caller

    def phase(self, volatility_ratio, pe_slope, n_confirmed):
        """BOOTSTRAP if the compass is weak (high volatility + flat grad-PE) AND we have < exit_rules local rules; else
        SOLVE. Exit is by accrued rules, not a proxy."""
        if int(n_confirmed or 0) >= self.exit_rules:
            return "solve"
        weak = (volatility_ratio is None or volatility_ratio > 0.5) and (pe_slope is None or abs(pe_slope) < 0.5)
        return "bootstrap" if weak else "solve"

    @staticmethod
    def coherence_gated(phase):
        """During BOOTSTRAP global coherence is OFF (Strategy 3): inert by design, not weakly-misleading."""
        return phase == "bootstrap"

    def narrate(self, phase, volatility_ratio, pe_slope, n_confirmed):
        if phase == "bootstrap":
            return ("BOOTSTRAP  cold-start / weak compass (volatility %.2f, grad-PE ~%.2f, %d/%d local rules) -> switch "
                    "OBJECTIVE to EPISTEMIC PLAY: maximise state-coverage/surprise, NOT win-progress; global coherence "
                    "GATED OFF, only local per-action consistency counts"
                    % ((volatility_ratio or 0.0), (pe_slope or 0.0), int(n_confirmed or 0), self.exit_rules))
        return ("BOOTSTRAP  exit -> SOLVE: %d local rules confirmed (>= %d) -> re-engage the full compass (coherence ON, "
                "solve-objective restored)" % (int(n_confirmed or 0), self.exit_rules))


SHARED.cold_start = BootstrapProtocol()                       # Section 16: phased bootstrap for the weak (cold-start) compass


class AllocationPlanner:
    """Regime-agnostic CONSTRAINED-ALLOCATION planner -- the assignment/transportation step the actuator PERCEIVES but
    could not COMPOSE (vc33 L2: it read roles + causal map + scarcity, then only probed). Given SINKS (sub-goals needing
    resource -- e.g. scarcity columns with a gap), SOURCES (available resource -- surplus columns), and OPERATORS
    (controls with LEARNED effects -- which sinks each can fill; inert controls affect nothing and are PRUNED), under a
    scarce BUDGET, it produces an ORDERED plan of operator applications that satisfies all sinks, or reports INFEASIBLE
    with the BINDING sub-goal/constraint (not a random probe). Method: the standard fail-first CSP heuristic
    (most-constrained sink first) + a transportation balance check (enough source to cover scarcity). Small instances,
    so greedy-with-most-constrained-first is exact enough. Purely symbolic over the LEARNED causal map -- no grid, no
    downsampling. Generalises to any actuator game shaped as {sub-goals, operators-with-effects, scarce resource}."""

    @staticmethod
    def feasible_balance(sinks, sources):
        need = sum(max(0, int(s.get("need", 0))) for s in sinks)
        have = sum(max(0, int(s.get("avail", 0))) for s in sources)
        return {"need": need, "have": have, "enough": have >= need}

    @staticmethod
    def plan(sinks, sources, operators, budget):
        live = [o for o in operators if o.get("affects")]          # prune inert operators (no learned effect)
        bal = AllocationPlanner.feasible_balance(sinks, sources)
        options = {s["id"]: [o for o in live if s["id"] in o.get("affects", ())] for s in sinks}
        unmet = [s["id"] for s in sinks if not options[s["id"]]]    # a sub-goal no operator can fill -> structurally unmet
        assignment = []; spent = 0
        for s in sorted(sinks, key=lambda x: len(options[x["id"]])):   # fail-first: most-constrained sub-goal first
            if s["id"] in unmet:
                continue
            placed = False
            for o in sorted(options[s["id"]], key=lambda o: o.get("cost", 1)):
                c = int(o.get("cost", 1))
                if spent + c <= budget:
                    assignment.append({"op": o["id"], "sink": s["id"], "cost": c}); spent += c; placed = True; break
            if not placed:
                unmet.append(s["id"])
        feasible = (not unmet) and bal["enough"]
        return {"assignment": assignment, "feasible": feasible, "spent": spent, "budget": int(budget),
                "unmet": unmet, "balance": bal}

    @staticmethod
    def narrate(plan):
        if plan["feasible"]:
            seq = " -> ".join("%s=>%s" % (a["op"], a["sink"]) for a in plan["assignment"]) or "(no ops needed)"
            return ("ALLOCATE  constrained assignment SOLVED: %s  [spent %d/%d resource; all sub-goals covered, source "
                    "balance ok] -> execute in this order" % (seq, plan["spent"], plan["budget"]))
        reasons = []
        if not plan["balance"]["enough"]:
            reasons.append("insufficient source (need %d > have %d)" % (plan["balance"]["need"], plan["balance"]["have"]))
        if plan["unmet"]:
            reasons.append("no known operator fills sub-goal(s) %s" % plan["unmet"])
        return ("ALLOCATE  constrained assignment INFEASIBLE this configuration: %s [spent %d/%d] -> that is the BINDING "
                "constraint (not a random probe): re-probe operators for the unmet sub-goal, or free/replenish resource"
                % ("; ".join(reasons) or "unmet sub-goals", plan["spent"], plan["budget"]))


SHARED.allocation_planner = AllocationPlanner()               # constrained assignment/transportation over the learned causal map


class GateBinding:
    """Generalizable, ORIENTATION-FREE attribute-correspondence -- the MATCH primitive (avatar key/lock) recombined for
    the actuator domain. Binds each PUCK to the MARKER sharing its identity attribute (the puck's BASE colour == the
    marker's colour). ONLY the shared attribute assigns the binding -- never position or orientation -- so it holds
    whether the board is upright, mirrored, or inverted. A puck with a matching marker is GATED (its base must ALIGN to
    that marker); a puck/region with no match is INERT (a conduit that only routes fluid). Symbolic over perceived
    objects -- no grid, no downsampling.
    Input: pucks=[{'id','colour','base'}] (colour = the puck's BASE/identity colour, base = its base position),
    markers=[{'colour','pos'}]. Returns gated={puck_id:{'target':marker_pos,'colour':c}}, inert=[unmatched puck ids]."""

    @staticmethod
    def bind(pucks, markers):
        by_colour = {}
        for m in markers:
            by_colour.setdefault(m.get("colour"), []).append(m)
        gated = {}; inert = []
        for p in pucks:
            hits = by_colour.get(p.get("colour"), [])
            if hits:
                gated[p.get("id")] = {"target": hits[0].get("pos"), "colour": p.get("colour")}
            else:
                inert.append(p.get("id"))
        return {"gated": gated, "inert": inert}

    @staticmethod
    def narrate(binding):
        g = {k: v["target"] for k, v in binding.get("gated", {}).items()}
        return ("GATE-BIND  colour-match PUCK-BASE<->MARKER (orientation-free): GATED pucks (align base to marker) := %s ; "
                "INERT (no matching marker -> conduit) := %s  [only COLOUR assigns the binding -- not position or "
                "orientation; the board may be mirrored/inverted]" % (g or {}, binding.get("inert") or []))


class ConditionalFlow:
    """Per-puck ALIGNMENT along the FLUID FILL AXIS (orientation-free) -- replaces the fill-to-level model. Each gated
    puck must have its BASE aligned to its same-colour marker; the alignment GAP is the SIGNED distance along the fill
    axis, a unit vector DERIVED from observed fluid/puck motion (never assumed up/down -- the base may be on any side or
    inverted). Fluid is CONSERVED (buttons move it through conduits), so serving one puck draws from the shared pool --
    which is exactly why the schedule must COMMIT to one puck and LOCK it once aligned rather than slosh (the
    oscillation). Pure math -- no grid.
    axis=(dr,dc) fill direction (from motion); pucks=[{'id','pos','target','tol'?}]."""

    @staticmethod
    def _gap(pos, target, axis):
        import math
        dr = target[0] - pos[0]; dc = target[1] - pos[1]
        n = math.hypot(axis[0], axis[1]) or 1.0
        return (dr * axis[0] + dc * axis[1]) / n               # signed distance ALONG the fill axis (orientation-free)

    @staticmethod
    def gaps(pucks, axis):
        out = []
        for p in pucks:
            if p.get("target") is None:
                continue
            g = ConditionalFlow._gap(p["pos"], p["target"], axis)
            out.append({"id": p["id"], "gap": g, "abs": abs(g), "aligned": abs(g) <= p.get("tol", 1.0)})
        return out

    @staticmethod
    def feasible(pucks, axis, total_fluid=None):
        """Conservation sanity: the sum of SIGNED gaps indicates net fluid to add (>0) or shed (<0). If total_fluid is
        given, aligning everything is possible only if the net demand does not exceed what conservation allows."""
        gs = ConditionalFlow.gaps(pucks, axis)
        net = sum(g["gap"] for g in gs)                        # net signed alignment demand
        return {"net_demand": net, "n_unaligned": sum(1 for g in gs if not g["aligned"]), "gaps": gs}

    @staticmethod
    def sweep_direction(edges, ncols):
        """Derive the SWEEP direction from the transfer flow (orientation-free). Resolve the accumulation END first, so
        every later press feeds already-solved columns from still-unsolved ones (locked pucks stay locked by
        construction). net = sum(sign(receiver-donor)); net>0 => fluid flows toward higher index (accumulates high) =>
        sweep DESCENDING (resolve high end first); else ASCENDING. Symmetric graph -> ascending default."""
        net = sum((1 if r > d else -1 if r < d else 0) for (d, r) in (edges or []))
        return -1 if net > 0 else 1

    @staticmethod
    def schedule(pucks, axis, route_cost=None, locked=None, edges=None, full_cols=None, sweep_dir=None):
        """COMMIT-AND-LOCK, TRANSFER-GRAPH-, CAPACITY-, and SWEEP-aware schedule. Serialises the win (one puck at a time)
        instead of balancing all pucks at once. PRIMARY order is a deterministic SWEEP along the column line in the
        flow-derived direction (sweep_dir: +1 ascending, -1 descending); WITHIN that, more-EMPTY gated columns (larger
        fill-need toward +axis) come first. Still gated by ADMISSIBILITY (never drain a locked puck) and CAPACITY (a full
        column that still needs to rise is cap-blocked -> wasted press). A left->right sweep means once the accumulation
        end is aligned+locked it is never pulled from again -> monotone. pucks carry 'col'; edges=[(donor,receiver)]."""
        locked = set(locked or ()); full_cols = set(full_cols or ())
        if sweep_dir is None:
            sweep_dir = ConditionalFlow.sweep_direction(edges, 0)
        gaps = {g["id"]: g for g in ConditionalFlow.gaps(pucks, axis)}
        col_of = {p.get("id"): p.get("col") for p in pucks}
        locked_cols = {col_of[i] for i in locked if col_of.get(i) is not None}

        def _admissible(pid):
            c = col_of.get(pid)
            if edges is None or c is None:
                return None
            return [d for (d, r) in edges if r == c and d not in locked_cols]

        rows = []
        for g in gaps.values():
            if g["aligned"] or g["id"] in locked:
                continue
            adm = _admissible(g["id"])
            n_adm = len(adm) if adm is not None else -1
            c = col_of.get(g["id"])
            cap_blocked = (c in full_cols) and (g["gap"] > 0)
            fill_need = g["gap"] if g["gap"] > 0 else 0.0        # 'emptiness': how much this column still needs to rise
            rows.append({"id": g["id"], "gap": g["gap"], "abs": g["abs"], "n_adm": n_adm,
                         "col": (c if c is not None else 10 ** 6), "fill_need": fill_need,
                         "blocked": (adm is not None and n_adm == 0), "cap_blocked": cap_blocked,
                         "rc": (route_cost(g["id"]) if route_cost is not None and route_cost(g["id"]) is not None else 10 ** 9)})
        # serviceable first -> SWEEP position (flow-derived direction) -> more-empty first -> most-constrained -> cheap
        rows.sort(key=lambda r: (r["blocked"] or r["cap_blocked"], sweep_dir * r["col"], -r["fill_need"],
                                 (r["n_adm"] if r["n_adm"] >= 0 else 10 ** 6) or 10 ** 6, r["rc"]))
        target = next((r["id"] for r in rows if not (r["blocked"] or r["cap_blocked"])),
                      (rows[0]["id"] if rows else None))
        return {"order": [r["id"] for r in rows], "gaps": {r["id"]: round(r["gap"], 2) for r in rows},
                "target": target, "locked": sorted(str(x) for x in locked), "sweep_dir": sweep_dir,
                "blocked": [r["id"] for r in rows if r["blocked"]],
                "cap_blocked": [r["id"] for r in rows if r["cap_blocked"]]}

    @staticmethod
    def recheck_locked(pucks, axis, locked, tol=1.0):
        """After a press, which LOCKED pucks are now MISALIGNED (broken)? A press that breaks a locked puck was
        inadmissible -- this is the re-check-locked guard that keeps commit-and-lock honest on a conserved line graph."""
        locked = set(locked or ())
        return [g["id"] for g in ConditionalFlow.gaps(pucks, axis) if g["id"] in locked and abs(g["gap"]) > tol]

    @staticmethod
    def narrate_schedule(s):
        if not s["order"]:
            return "FLOW-SCHEDULE  all gated pucks aligned/locked -> nothing to serve (monotone: no re-opening)"
        tail = ""
        if s.get("blocked"):
            tail += "; BLOCKED (no admissible donor yet -> wait) := %s" % s["blocked"]
        if s.get("cap_blocked"):
            tail += "; CAP-FULL (column at ceiling, cannot raise -> pressing is wasted) := %s" % s["cap_blocked"]
        return ("FLOW-SCHEDULE  COMMIT-AND-LOCK [admissible-donor -> most-constrained -> largest-gap]: target puck %s "
                "(signed gaps %s); locked(never re-opened) := %s%s -> drive ONLY this puck's fluid, pulling from a "
                "conduit/unsatisfied neighbour, until its base aligns, then LOCK" %
                (s["target"], s["gaps"], s["locked"] or "[]", tail))


SHARED.gate_binding = GateBinding()                           # orientation-free puck-base<->marker colour match
SHARED.conditional_flow = ConditionalFlow()                   # per-puck alignment along the fill axis + commit-and-lock


class LegibilityError(Exception):
    """Raised when a regime RUNS but does not NARRATE -- a silent solve. Every decision/perception/plan/self-correction
    must be emitted as grammar into the frame data; a solve that emitted nothing made silent decisions."""


class Legibility:
    """The legibility requirement, enforced the same spirit as the downsampling ban: a regime that runs MUST narrate.
    Legibility is not as cleanly SYNTACTIC as downsampling (there is no single 'decision' token to grep), so it is
    enforced in two layers:
      * RUNTIME (hard): after a solve, the game's grammar derivation must be NON-EMPTY -- a completely silent solve
        raises. Under-coverage of the core vocabulary is reported (soft) rather than raised, since a short game may
        legitimately not reach every stage.
      * STATIC (heuristic): scan_silent_decisions() flags decision-shaped functions that carry no _emit -- a review aid,
        not a hard ban, because the heuristic has false positives/negatives that a syntactic ban does not."""

    CORE_TAGS = ("PERCEIVE", "SEE", "MODEL", "DERIVE", "PLAN", "COMPARE", "TARGET", "OUTCOME", "CACHE", "TRIANGULATE",
                 "RECOGNISE", "NOVELTY", "CONFIRM", "INDUCE", "REVISE")

    @staticmethod
    def _derivations():
        """Every grammar derivation produced in this run, keyed by an opaque per-GAMEPLAY handle. It used to read a
        game_id-keyed store; the audit only ever needed 'which solve emitted this', never 'which game was it'."""
        try:
            from objective_validator import _WORKING_MEMS
        except Exception:
            return {}
        return {m.get("_sess", "S?"): m.get("derivation", []) for m in _WORKING_MEMS if m.get("derivation")}

    @staticmethod
    def _total_steps():
        try:
            from objective_validator import _WORKING_MEMS
        except Exception:
            return 0
        return sum(len(m.get("derivation", [])) for m in _WORKING_MEMS)

    @staticmethod
    def tags(derivation):
        out = set()
        for step in derivation:
            w = str(step).strip().split()
            if w and w[0].isupper() and len(w[0]) >= 3 and w[0].isalpha():
                out.add(w[0])
        return out

    @classmethod
    def assert_narrated(cls, min_steps=1):
        """HARD: the most recent solve must have emitted grammar. A silent solve (no derivation) raises."""
        ds = cls._derivations()
        if not ds:
            return True                                        # nothing has run yet
        gid, deriv = max(ds.items(), key=lambda kv: len(kv[1]))
        if len(deriv) < min_steps:
            raise LegibilityError("SILENT SOLVE: game %s emitted %d grammar step(s) -- its decisions were not narrated"
                                  % (gid, len(deriv)))
        return True

    @classmethod
    def coverage(cls, expected=None):
        """SOFT: which core grammar categories the most recent solve touched, and which it missed (a legibility audit)."""
        expected = set(expected or cls.CORE_TAGS)
        ds = cls._derivations()
        if not ds:
            return {"present": set(), "missing": expected, "steps": 0}
        _, deriv = max(ds.items(), key=lambda kv: len(kv[1]))
        present = cls.tags(deriv)
        return {"present": present & expected, "missing": expected - present, "steps": len(deriv),
                "all_tags": present}


def scan_silent_decisions(*paths):
    """STATIC (heuristic) legibility scan: flag functions that BRANCH on game/decision state and RETURN a choice yet
    contain no _emit -- candidate silent decisions. WARNS (returns a list); does not raise, because legibility is not
    syntactic like downsampling and this heuristic has false positives (pure helpers) and negatives. A review aid."""
    import ast, os
    STATE = ("adapter", "cmap", "objective", "props", " dif", "_won", "cand", "cmove", "slot", "frame")
    warnings = []
    for path in paths:
        if not os.path.exists(path):
            continue
        src = open(path).read()
        try:
            tree = ast.parse(src)
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            seg = ast.get_source_segment(src, node) or ""
            has_branch = any(isinstance(n, ast.If) for n in ast.walk(node))
            returns_val = any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(node))
            touches_state = any(s in seg for s in STATE)
            decides = "decide" in node.name or "choose" in node.name or "select" in node.name or "plan" in node.name
            if (has_branch and returns_val and touches_state and "_emit(" not in seg and (decides or "objective" in seg)):
                warnings.append("  %s:%d  %s()  -- branches on state + returns a choice with no _emit" %
                                (os.path.basename(path), node.lineno, node.name))
    return warnings


class Regime:
    """The shared reasoning skeleton every regime runs. Steps are the SAME across regimes; only the perception +
    primitives behind them differ. Subclasses reuse SHARED for anything regime-agnostic.

    LEGIBILITY IS ENFORCED STRUCTURALLY: __init_subclass__ wraps every subclass's solve() so that a solve which emits
    ZERO grammar steps -- a silent solve -- raises LegibilityError. Just as the factory bans downsampling, it bans
    silent decisions: a regime that runs must narrate its reasoning into the frame data."""
    name = "base"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _orig = cls.__dict__.get("solve")
        if _orig is None:
            return
        import functools

        @functools.wraps(_orig)
        def _legible_solve(self, *a, **k):
            _before = Legibility._total_steps()
            _r = _orig(self, *a, **k)
            if Legibility._total_steps() - _before < 1:        # the solve added NO grammar -> silent decisions
                import sys
                print("[legibility] SILENT SOLVE: regime '%s' emitted 0 grammar steps -- decisions were not narrated"
                      % getattr(cls, "name", cls.__name__), file=sys.stderr)
                raise LegibilityError("regime '%s' made a silent solve (no grammar emitted into the frame data)"
                                      % getattr(cls, "name", cls.__name__))
            return _r
        cls.solve = _legible_solve

    def __init__(self, adapter, shared=SHARED):
        self.adapter = adapter
        self.shared = shared

    # The skeleton (documented contract). A regime may override the whole solve() while it is a thin wrapper over an
    # existing monolith, and progressively break these out as the monolith is decomposed -- WITHOUT changing callers.
    def perceive(self):
        raise NotImplementedError

    def model(self):
        raise NotImplementedError

    def derive_objective(self):
        raise NotImplementedError

    def plan(self):
        raise NotImplementedError

    def confirm(self):
        raise NotImplementedError

    def transfer(self):
        raise NotImplementedError

    def revise(self):
        raise NotImplementedError

    def solve(self, budget):
        raise NotImplementedError


class AvatarRegime(Regime):
    """Games where an object IS the agent (self / navigation / cyclic triggers / gates / budget). Currently a thin
    wrapper over the existing avatar solver; it already runs the skeleton internally and pulls shared mechanisms
    (SpatialMap, triangulate, object_props, induce_win_condition, pathfind) from their canonical homes."""
    name = "avatar"

    def __init__(self, adapter, av, shared=SHARED):
        super().__init__(adapter, shared)
        self.av = av

    def solve(self, budget=260):
        from objective_validator import _avatar_solve
        try:
            self.adapter._committed_frame = "avatar"           # the frame context the doubt reasons RELATIVE to
            self.adapter._has_avatar_frame = True
        except Exception:
            pass
        return _avatar_solve(self.adapter, self.av, budget=budget)


class ContainFitRegime(Regime):
    """cn04-class games: a CONTROLLABLE multi-colour RIGID BODY (co-moving cells) must fit its pegs INTO a STATIONARY
    hollow frame's interior slot -- the CONTAIN_FIT molecule. This regime COMPOSES what already exists rather than
    re-implementing it:
      * co-moving rigid body   -- grouped from cells that move together under actions (NOT segmented by colour);
      * stationary hollow frame -- SHARED.perception.interiors() gives its interior slot (the fit TARGET);
      * objective              -- BE_AT(controllable-body, frame-interior) = CONTAIN_FIT, EXCLUDING the body's own
                                  colours from target candidates (the documented cn04 failure was chasing a co-moving
                                  part of itself -- mathematically unsatisfiable);
      * drive                  -- residual-correction: close the OBSERVED body-to-slot residual on the REAL grid with
                                  corrective moves + online action-effect calibration (re-planning a full pose on a
                                  BIASED forward model oscillates ~3 cells off; closing the observed residual converges).
    This is the scaffold + the perception/objective the replay proved were the wall. The residual-correction drive and
    rotation handling are the deeper P1 build, to be done against a MEASURED gap (model-bias vs objective-incomplete),
    not blind."""
    name = "contain_fit"

    def slot(self, g):
        """The stationary hollow frame's interior slot = the CONTAIN_FIT target (excludes background + the body)."""
        s = self.shared.perception.interiors(g)
        return max(s, key=lambda x: x[2]) if s else None       # the largest enclosed slot is the frame's fit target

    def solve(self, budget=500):
        from objective_validator import validate, _emit, _perceive_grid
        try:
            s = self.slot(_perceive_grid(self.adapter))
            if s:
                _emit(self.adapter, "TARGET  CONTAIN_FIT := frame(colour %d) interior slot @%s size %d  [the fit target: "
                      "the hollow the body's pegs must ENTER -- NOT the frame walls, NOT the body's own co-moving parts]"
                      % (s[0], s[1], s[2]))
        except Exception:
            pass
        return validate(self.adapter, budget=budget)          # composes co-moving body + tip-overlap already present


def make_regime(adapter, shared=SHARED):
    """Probe once: is one of these objects ME (an avatar whose displacement tracks the directional actions)?
    -> AvatarRegime. Otherwise the caller runs the ACTUATOR path (kept in validate() to avoid re-entrancy).
    Returns (regime_or_None, av): a non-None regime means the avatar regime should handle this game."""
    from objective_validator import _perceive_avatar_live
    try:
        av = _perceive_avatar_live(adapter)
    except Exception:
        av = None
    if av is not None:
        return AvatarRegime(adapter, av, shared), av
    return None, None


# ---- IMPORT-TIME ENFORCEMENT: the no-downsampling rule is checked whenever the factory loads. If any banned grid
#      downsampling primitive appears in the perception code, importing the agent FAILS LOUDLY -- so the rule is
#      enforced by the code itself, for both the avatar and actuator regimes, not by anyone remembering it.
def check_no_posthoc():
    """The second hard bound. A predicate that reads the outcome beats the truth on MDL by 16 bits and predicts
    nothing -- so this is enforced where a dial would be gamed, at import, beside the downsampling ban."""
    import no_posthoc as _NP
    return _NP.check_no_posthoc_predicates()


def check_no_downsampling():
    import os
    _here = os.path.dirname(os.path.abspath(__file__))
    # micro_market.py and marketplace.py were added after this list was written and PERCEPTION NOW LIVES IN THEM.
    # A ban that does not scan the files where the percepts are is a ban that reports clean forever.
    _files = [os.path.join(_here, f) for f in ("objective_validator.py", "online_harness.py", "spatial_map.py",
                                               "evolvability_engine.py", "map_decode.py",
                                               "micro_market.py", "marketplace.py")]
    return assert_no_downsampling(*[f for f in _files if os.path.exists(f)])


try:
    check_no_downsampling()
except DownsampleError:
    raise
