"""Ouroboros Redux -- the recombination. See OUROBOROS_REDUX_ARCHITECTURE.md.

REORDER, not elaborate. The two strong builds were an either/or: v18 (rich perception + feature-invention +
win-predicate induction, reactive control, 0.18) OR reason-first (compose-first control + articulation, thin
perception, 0.07-0.15). They were never stacked. Redux places v18's perception/agency/feature/predicate
machinery UNDERNEATH the proven reason-first control spine (OuroborosIntegrated) as ONE layered stack along the
project's canonical reasoning spine KNOW -> WANT -> AFFORD -> DO, governed by META -- attacking the measured
controllable-ID / perception bottleneck by putting the strongest perception at the bottom of the strongest control.

It does NOT rewrite the proven modules; it subclasses the control spine and injects a v18-powered KnowLayer plus a
multi-mover motion attributor (the one genuine gap-fill). Every injection is DEFENSIVE: a v18 interface mismatch
degrades silently to the proven path, so Redux always imports and runs (version control is the net; the build
discipline this push is parse/import sanity only -- no battery, no dev set). Design law: unexplainable => uncommitted.
"""
import numpy as np
from collections import deque, defaultdict, Counter

import ouroboros_integrated as _OI
from ouroboros_integrated import _read
try:
    import objective_validator as _OV          # proven descend/pursue execution engines (verified to solve a
except Exception:                               # click-erase board in isolation); routed into the AFFORD layer
    _OV = None

try:
    import v18_agent as _v18
    _HAVE_V18 = True
except Exception:                                   # pragma: no cover - degrade to pure reason-first
    _v18 = None
    _HAVE_V18 = False

try:
    import match_abduction as _M
except Exception:
    _M = None

try:
    from self_model import SelfLocusModel as _SLM
except Exception:
    _SLM = None

try:
    import grid_perception as _gp
except Exception:
    _gp = None


# ============================================================================================================
# KNOW layer -- v18 perception front-end as the sensory substrate + the multi-mover attributor (gap-fill).
# ============================================================================================================
class PerceptBus:
    """Unified KNOW output for one step: what every downstream layer reads. Lightweight + tolerant of missing
    fields (any sub-percept that failed is just None)."""
    __slots__ = ("objects", "events", "controllable_oid", "predicate_count", "action_model", "frame")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class KnowLayer:
    """Runs v18's perception/agency/feature/predicate machinery as the substrate beneath the control spine.
    Stateful within a level (tracker/agency/predicate accumulate). Every operation is wrapped so a failure in
    any v18 component disables only that component, never the whole layer."""

    def __init__(self, background: int = 0):
        self.bg = background
        self.ok = _HAVE_V18
        self.ex_mask = self._mk(lambda: _v18.ObjectExtractor(background=background, color_aware=False))
        self.merger = self._mk(lambda: _v18.CommonFateMerger())
        self.tracker = self._mk(lambda: _v18.ObjectTracker())
        self.selfm = self._mk(lambda: _v18.SelfModel())
        self.physics = self._mk(lambda: _v18.PhysicsModel())
        self.pred = self._mk(lambda: _v18.PredicateInducer())
        self.belief = self._mk(lambda: _v18.TaskBelief())
        self.slm = self._mk(lambda: _SLM()) if _SLM is not None else None  # change-based controllable
        self._cl_disp = {}     # colour-locus: colour -> {action -> Counter(displacement)}
        self._cl_color = None  # resolved controllable colour (distinctive small mover)
        self._cl_dmap = {}     # action -> mean displacement (the clean single-cell-avatar dmap)
        self._cl_locus = None  # centroid of the controllable colour in the latest frame
        self._prev_objs = None
        self._last = None
        self.ctrl_oid = None
        # telemetry (safe aggregates only)
        self.steps = 0
        self.obj_adds = 0
        self._obs_n = 0                      # directional-transition count, for the task-type prior (critique 3)
        # ---- step-1: controllable-ID synthesis (autonomous-mover isolation + attributor cross-check) ----
        self._oid_act_disp = defaultdict(lambda: defaultdict(Counter))  # oid -> action -> Counter[(dr,dc)]
        self._oid_moves = Counter()
        self._auto_oids = set()              # movers judged world-driven (action-independent motion)
        self.ctrl_oid_isolated = None        # controllable AFTER isolation -- feeds v18 internals; does NOT
                                             # override the spine's live avatar localization (observe-first)
        self.attr_checks = 0                 # attributor vs v18-controllable agreement (cross-check confidence)
        self.attr_agree = 0
        # ---- marker-selection wire (sprite co-location): a colour whose cells stay within step_r of the avatar
        #      ACROSS FRAMES WHERE THE AVATAR MOVED is part of the controllable sprite, not a distant goal. ----
        self._colo_hits = Counter()          # per-colour moving-frames the colour stayed co-located with the avatar
        self._colo_obs = Counter()           # per-colour moving-frame observations
        self._prev_cl_locus = None           # avatar locus on the previous observe (to detect movement)

    @staticmethod
    def _mk(factory):
        try:
            return factory()
        except Exception:
            return None

    def reset_level(self):
        """New layout: forget per-oid identity, keep transferable agency deltas (v18's own contract)."""
        try:
            self.tracker = _v18.ObjectTracker()
            if self.selfm is not None and hasattr(self.selfm, "reset_level"):
                self.selfm.reset_level()
            self.physics = _v18.PhysicsModel()
        except Exception:
            pass
        self._prev_objs = None
        self.ctrl_oid = None

    def _cohesive_objs(self, before, after):
        """Motion-merged (common-fate) objects: colour-aware fragments re-merged by shared motion across
        the before->after transition -- the real multi-colour cohesion (NOT the redundant colour-blind
        blob). Falls back to single-frame mask extraction."""
        if self.merger is not None:
            try:
                objs = self.merger.merge_from_transition(np.asarray(before), np.asarray(after), learn=True)
                if objs:
                    return objs
            except Exception:
                pass
        return self._mask_objs(after)

    def _mask_objs(self, grid):
        if self.ex_mask is None:
            return []
        try:
            return self.ex_mask.extract(np.asarray(grid))
        except Exception:
            return []

    def observe(self, before, action, after):
        """Feed one lived transition. action is the ORIGINAL GameAction object -- v18 keys its agency tables by
        whatever hashable we pass, so action_model() comes back keyed by GameAction (a drop-in dmap)."""
        if not self.ok:
            return self._last
        try:
            b = np.asarray(before); a = np.asarray(after)
            if b.shape != a.shape:
                return self._last
            self.steps += 1
            self._obs_n += 1
            objs = self._cohesive_objs(b, a)
            if self.slm is not None:
                try:
                    self.slm.update(b, action, a)        # change-based controllable (segmentation-free)
                except Exception:
                    pass
            try:
                self._cl_update(b, action, a)            # discriminative colour-locus (single-cell avatars)
            except Exception:
                pass
            try:
                self._track_colocation(a)                # sprite co-location: colours that move WITH the avatar
            except Exception:
                pass
            events = {}
            if self.tracker is not None:
                try:
                    events = self.tracker.update(objs) or {}
                except Exception:
                    events = {}
            moved = not np.array_equal(b, a)
            if self.selfm is not None:
                try:
                    self._update_autonomy(action, events)        # step-1: learn which movers are world-driven
                    fev = self._isolate_autonomous(events)        # ...and subtract them before crediting agency
                    self.selfm.observe(action, fev)
                    self.ctrl_oid_isolated = self.selfm.controllable()
                    self.ctrl_oid = self.ctrl_oid_isolated        # isolation-cleaned controllable (v18-internal)
                except Exception:
                    pass
            if self.physics is not None:
                try:
                    self.physics.observe(moved, events, self.ctrl_oid)
                except Exception:
                    pass
            if self.pred is not None and objs:
                try:
                    self.pred.observe(objs, 0.0, self.ctrl_oid)
                except Exception:
                    pass
            self._prev_objs = objs
            self._last = PerceptBus(objects=objs, events=events, controllable_oid=self.ctrl_oid,
                                    predicate_count=(len(self.pred.preds) if self.pred is not None else 0),
                                    action_model=self.clean_action_model(), frame=a)
            return self._last
        except Exception:
            return self._last

    def _update_autonomy(self, action, events):
        """An oid whose motion is ACTION-INDEPENDENT (same dominant displacement under >=2 distinct actions,
        persistently) is world-driven, not self. v18's no-op control condition, generalized to need no no-op."""
        try:
            for k in ("move", "teleport"):
                for (oid, dr, dc) in events.get(k, []):
                    self._oid_act_disp[oid][action][(int(dr), int(dc))] += 1
                    self._oid_moves[oid] += 1
            for oid, per_act in self._oid_act_disp.items():
                if self._oid_moves[oid] < 3 or len(per_act) < 2 or oid in self._auto_oids:
                    continue
                doms = {disps.most_common(1)[0][0] for disps in per_act.values()}
                if len(doms) == 1:                  # moves the same way regardless of action => world-driven
                    self._auto_oids.add(oid)
        except Exception:
            pass

    def _isolate_autonomous(self, events):
        """Subtract autonomous movers from the move/teleport events, so agency selects the controllable and
        consolidates its action-model WITHOUT contamination from other simultaneous movers."""
        try:
            if not self._auto_oids:
                return events
            out = dict(events)
            for k in ("move", "teleport"):
                if k in out:
                    out[k] = [(oid, dr, dc) for (oid, dr, dc) in out[k] if oid not in self._auto_oids]
            return out
        except Exception:
            return events

    def ctrl_centroid(self):
        if self.ctrl_oid is None or not self._prev_objs:
            return None
        o = next((o for o in self._prev_objs if getattr(o, "oid", None) == self.ctrl_oid), None)
        return o.centroid if o is not None else None

    def cross_check(self, attr_centroid):
        """Observe-only confidence: how often the spatial attributor's avatar pick agrees with v18's
        (isolation-cleaned) controllable-oid centroid. Two independent attacks on controllable-ID concurring is
        the signal that the synthesis is trustworthy. Changes NO decision; surfaced via articulate()."""
        try:
            c = self.ctrl_centroid()
            if c is None:
                return
            self.attr_checks += 1
            if abs(attr_centroid[0] - c[0]) + abs(attr_centroid[1] - c[1]) <= 2.0:
                self.attr_agree += 1
        except Exception:
            pass

    _CL_MAXCELLS = 40    # avatar/marker scale; larger colour regions are not single-cell avatars

    def _cl_update(self, before, action, after):
        """Passive discriminative-agency: track each distinctive (rare) colour's centroid displacement per
        action. The controllable is the colour whose per-action moves are direction-consistent and DIFFER
        across actions (the discriminative-agency principle, run passively from the live stream -- no probes,
        no resets). Resolves single-cell avatars where identity-tracking and change-centroid both collapse."""
        if action is None:
            return
        _an = str(getattr(action, 'name', '')).upper()
        if _an.endswith('RESET') or getattr(action, 'value', None) == 0:
            return                                    # RESET is not a navigation move
        ba = np.asarray(before); aa = np.asarray(after)
        if ba.shape != aa.shape:
            return
        vals, counts = np.unique(aa, return_counts=True)
        bg = int(vals[int(counts.argmax())])
        for c in vals.tolist():
            c = int(c)
            if c == bg:
                continue
            if int((aa == c).sum()) > self._CL_MAXCELLS:
                continue
            yb, xb = np.where(ba == c); ya, xa = np.where(aa == c)
            if len(yb) == 0 or len(ya) == 0:
                continue
            dr = round(float(ya.mean()) - float(yb.mean()))
            dc = round(float(xa.mean()) - float(xb.mean()))
            if dr == 0 and dc == 0:
                continue
            self._cl_disp.setdefault(c, {}).setdefault(action, Counter())[(dr, dc)] += 1
        self._resolve_color_locus(aa)

    @staticmethod
    def _axis_dir(dr, dc):
        return (1 if dr > 0 else -1, 0) if abs(dr) >= abs(dc) else (0, 1 if dc > 0 else -1)

    @staticmethod
    def _is_steer_action(act):
        """A controllable is STEERED by directional (nullary) actions. A located/click action is a world-
        transform, not self-motion: on an erase board, clicking shifts a colour's centroid, faking a 'mover'
        that resolves the erase-target colour as the avatar -> task_type=nav, that colour excluded as 'self',
        the NONE.EXIST cue suppressed, a garbage objective committed (measured cd82 as COVER(border)=0). Only
        directional-action displacement counts as evidence of control. OOD-safe: keyed on action KIND, not id."""
        return (not isinstance(act, tuple)) and (getattr(act, "name", "") != "ACTION6")

    def _resolve_color_locus(self, aa):
        best = None; best_score = -1
        for c, per in self._cl_disp.items():
            dirs = {}; dmap = {}
            for act, ctr in per.items():
                if not self._is_steer_action(act):     # located/click shifts are world effects, not control
                    continue
                total = sum(ctr.values())
                if total < 1:
                    continue
                # DEBIAS BY MODAL DIRECTION (Outcome-A fix): a single action's centroid samples can be bimodal --
                # a clean move plus outlier jumps (multi-colour sprite centroid splits / wraps). A count-weighted
                # mean over the mixed set collapses the true axis: tu93 ACTION2 had ~14 clean DOWN (+6,+7) samples
                # plus ~6 (-12,-13) outliers, averaging to (1,-2) -> mis-read as LEFT, leaving the row pitch zero
                # so _cell_nav bailed 351/351. Pick the modal axis-direction by sample count, then average ONLY
                # the samples on that axis-direction (magnitude may still vary: slide-to-wall).
                axis_count = Counter()
                for d, n in ctr.items():
                    axis_count[self._axis_dir(d[0], d[1])] += n
                dom = axis_count.most_common(1)[0][0]
                kept = [(d, n) for d, n in ctr.items() if self._axis_dir(d[0], d[1]) == dom]
                kn = sum(n for _, n in kept)
                if kn < 1 or (kn / total) < 0.5:        # the modal direction must be a genuine plurality
                    continue
                sr = sum(d[0] * n for d, n in kept) / kn
                sc = sum(d[1] * n for d, n in kept) / kn
                dirs[act] = dom
                dmap[act] = (round(sr), round(sc))
            distinct = len(set(dirs.values()))
            if distinct >= 2:                                  # discriminative across actions
                score = distinct * 100 + sum(sum(ctr.values()) for ctr in per.values())
                if score > best_score:
                    best_score = score; best = (c, dmap)
        if best is not None:
            self._cl_color, self._cl_dmap = best
            ya, xa = np.where(aa == self._cl_color)
            self._cl_locus = (round(float(ya.mean()), 1), round(float(xa.mean()), 1)) if len(ya) else None

    def _raw_sample_dmap(self):
        """Best-effort dmap straight from the accumulating displacement samples (_cl_disp), debiased by modal
        direction. Available DURING the run before _resolve_color_locus crosses its >=2-direction gate, so the
        nav primitive isn't pinned on the degenerate slm fallback (pitch ~(0,1)) while the controllable is still
        resolving -- the tu93 bootstrap failure where _cell_nav bailed 351/351 on a stale fallback dmap."""
        per = self._cl_disp.get(self._cl_color) if self._cl_color is not None else None
        if not per and self._cl_disp:
            c = max(self._cl_disp, key=lambda k: sum(sum(ctr.values()) for ctr in self._cl_disp[k].values()))
            per = self._cl_disp.get(c)
        dmap = {}
        for act, ctr in (per or {}).items():
            axis_count = Counter()
            for d, n in ctr.items():
                axis_count[self._axis_dir(d[0], d[1])] += n
            if not axis_count:
                continue
            dom = axis_count.most_common(1)[0][0]
            kept = [(d, n) for d, n in ctr.items() if self._axis_dir(d[0], d[1]) == dom]
            kn = sum(n for _, n in kept)
            if kn < 2:                                  # need a little evidence before trusting an action
                continue
            sr = round(sum(d[0] * n for d, n in kept) / kn)
            sc = round(sum(d[1] * n for d, n in kept) / kn)
            if abs(sr) + abs(sc) > 0:
                dmap[act] = (sr, sc)
        return dmap

    def _cl_directions(self):
        return set(self._axis_dir(v[0], v[1]) for v in self._cl_dmap.values() if (abs(v[0]) + abs(v[1])) > 0)

    def _step_r(self):
        """One move-cell radius from the colour-locus dmap (fallback ~8px); the co-location threshold."""
        try:
            dm = self._cl_dmap or {}
            if dm:
                avg = sum(abs(v[0]) + abs(v[1]) for v in dm.values()) / max(1, len(dm))
                return max(2.0, 0.8 * avg)
        except Exception:
            pass
        return 8.0

    def _track_colocation(self, a):
        """Per observe: on a frame where the AVATAR MOVED, score each non-self colour as co-located if it has a
        cell within step_r of the avatar. A colour that stays co-located across moving frames moves WITH the
        avatar -> it is part of the controllable sprite (e.g. a colour-9 halo on a colour-4 core), NOT a distant
        goal marker. A static start-adjacent decoy fails this test (its distance grows as the avatar moves away)
        and is left to the no-reward blacklist instead."""
        loc = self._cl_locus
        if loc is None:
            return
        prev = self._prev_cl_locus
        self._prev_cl_locus = loc
        if prev is None:
            return
        if abs(loc[0] - prev[0]) + abs(loc[1] - prev[1]) < 1.0:    # avatar did not move -> uninformative frame
            return
        g = np.asarray(a)
        if g.ndim != 2:
            return
        bg = int(np.bincount(g.ravel()).argmax())
        R = self._step_r()
        self_c = self._cl_color
        for c in np.unique(g):
            c = int(c)
            if c == bg or c == self_c:
                continue
            ys, xs = np.where(g == c)
            if len(ys) == 0:
                continue
            d = float(np.min(np.abs(ys - loc[0]) + np.abs(xs - loc[1])))
            self._colo_obs[c] += 1
            if d <= R:
                self._colo_hits[c] += 1

    def sprite_colors(self):
        """Colours empirically attached to the moving avatar: >=4 moving-frame observations and co-located on
        >=80% of them. These are excluded from goal-marker candidates (the multi-colour-sprite confound)."""
        out = set()
        for c, n in self._colo_obs.items():
            if n >= 4 and self._colo_hits.get(c, 0) / float(n) >= 0.8:
                out.add(int(c))
        return out

    def clean_action_model(self):
        """v18's identity-free, reset-free action->displacement map, keyed by the original GameAction object.
        A strong navigation-map fallback that needs no resets and survives multi-colour sprites."""
        # 1) discriminative colour-locus dmap -- the verified fix for single-cell avatars (tu93 canary)
        if self._cl_dmap and len(self._cl_directions()) >= 2:
            return {a: (float(d[0]), float(d[1])) for a, d in self._cl_dmap.items()
                    if (abs(d[0]) + abs(d[1])) > 0.0}
        # 2) v18 identity model -- but REJECT the degenerate phantom signature (>=2 actions, duplicate displacement)
        am = {}
        if self.selfm is not None:
            try:
                raw = {a: (float(d[0]), float(d[1])) for a, d in (self.selfm.action_model() or {}).items()
                       if d is not None and (abs(d[0]) + abs(d[1])) > 0.0}
                disps = list(raw.values())
                degenerate = len(disps) >= 2 and len(set(disps)) < len(disps)
                if not degenerate:
                    am = raw
            except Exception:
                am = {}
        # 3) change-based slm fallback (segmentation-hard, scene-wide dynamics)
        if not am and self.slm is not None:
            try:
                ca = self.slm.coherent_actions() or {}
                am = {a: (float(d[0]), float(d[1])) for a, d in ca.items()
                      if d is not None and (abs(d[0]) + abs(d[1])) > 0.0}
            except Exception:
                pass
        return am

    def merged_objects(self, grid):
        """Multi-colour-cohesive object dicts in the integrated build's _other_objects format
        (centroid / cells / vec). Surfaces sprites that single-component mask-CC would split."""
        if not self.ok or _M is None:
            return []
        try:
            objs = self.merger.segment(np.asarray(grid)) if self.merger is not None else self._mask_objs(grid)
            if not objs:
                objs = self._mask_objs(grid)
            g = np.asarray(grid); bg = _M._bg(g)
            out = []
            for o in objs:
                cells = [(int(r), int(c)) for (r, c) in o.cells]
                if not cells:
                    continue
                out.append(dict(cells=cells, centroid=o.centroid,
                                vec=_M._mp.object_property_vector(g, cells, bg)))
            return out
        except Exception:
            return []

    def attribute_controllable(self, before, after, prev, expected, R):
        """MULTI-MOVER ATTRIBUTION (the gap-fill). Cluster the changed cells into connected components; the
        avatar is the component whose centroid lands nearest where the action's KNOWN displacement predicts it
        (prev + expected). Isolates the controllable from other simultaneous movers, which a plain
        all-changed-cells centroid cannot. Returns the avatar centroid, or None to defer to the caller."""
        try:
            b = np.asarray(before); a = np.asarray(after)
            if b.shape != a.shape:
                return None
            ch = np.argwhere(b != a)
            if len(ch) == 0:
                return prev
            chset = {(int(r), int(c)) for r, c in ch}
            seen = set(); comps = []
            for cell in chset:
                if cell in seen:
                    continue
                comp = []; dq = deque([cell]); seen.add(cell)
                while dq:
                    r, c = dq.popleft(); comp.append((r, c))
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        n = (r + dr, c + dc)
                        if n in chset and n not in seen:
                            seen.add(n); dq.append(n)
                cr = sum(r for r, _ in comp) / len(comp); cc = sum(c for _, c in comp) / len(comp)
                comps.append((cr, cc))
            if not comps:
                return prev
            ex0 = prev[0] + (expected[0] if expected else 0.0)
            ex1 = prev[1] + (expected[1] if expected else 0.0)
            best = min(comps, key=lambda p: abs(p[0] - ex0) + abs(p[1] - ex1))
            if abs(best[0] - ex0) + abs(best[1] - ex1) <= max(R, 6.0):
                return best
            return None
        except Exception:
            return None

    def _locus(self):
        if self._cl_locus is not None:
            return self._cl_locus
        if self.slm is None:
            return None
        try:
            ac = getattr(self.slm, 'agent_cell', None)
            loc = ac() if callable(ac) else getattr(self.slm, 'locus', None)
            if loc is not None:
                return (round(float(loc[0]), 1), round(float(loc[1]), 1))
        except Exception:
            pass
        return None

    def _locus_is_localized(self, max_frac=0.05):
        """Safety guard (critique 1 + oracle soft-rejection): the resolved controllable colour must be a SMALL
        localized footprint, not a scene-wide colour. Stops a phantom 'controllable' (e.g. a colour that flickers
        across the whole board) from hijacking self-localization the way the cd82 scene-wide dynamics would."""
        try:
            if self._cl_color is None or self._last is None or getattr(self._last, "frame", None) is None:
                return self._cl_color is not None        # no frame to check -> defer to the discriminative gate
            g = np.asarray(self._last.frame)
            n = int(np.count_nonzero(g == self._cl_color))
            return 0 < n <= max_frac * g.size
        except Exception:
            return self._cl_color is not None

    def task_type(self):
        """Revisable task-type PRIOR computed in KNOW (critique 3), NOT a hard gate. NAV when a discriminative,
        localized controllable mover resolved. COMMAND only on POSITIVE evidence -- enough directional
        observations with NO controllable action-model at all (directional actions move nothing steerable) --
        because controllable==None alone is ambiguous (perception failure on a nav game is indistinguishable
        from a true selection game at this sensor). Else UNKNOWN. Conservative by design: it biases routing,
        reward/abduction can still overturn it."""
        try:
            if self._cl_dmap and len(self._cl_directions()) >= 2 and self._locus_is_localized():
                return "nav"
            if self._obs_n >= 8 and not self._cl_dmap and not (self.clean_action_model() or {}):
                return "command"
        except Exception:
            pass
        return "unknown"

    def causal_graph(self):
        """KNOW output (critique 4): salient objects tagged with a causal ROLE -- self / autonomous / static.
        Autonomous movers are DELIVERED here, not subtracted from the world model (_isolate_autonomous only
        removes them from agency CREDIT; segmentation and predicates still see them). This is the data an
        AVOID / TRIGGER_BY_MOVEMENT objective would consume. OBSERVE-ONLY: surfaced in the trace, drives no
        decision. Wiring a new AVOID/TRIGGER objective primitive into the scored path is deliberately DEFERRED
        (elaboration trap: a new capability earns the scored path only after a held-out signal, and there is
        none yet)."""
        nodes = []
        try:
            if self._cl_locus is not None and self._cl_color is not None and self._locus_is_localized():
                nodes.append({"role": "self", "color": int(self._cl_color),
                              "centroid": (round(float(self._cl_locus[0]), 1), round(float(self._cl_locus[1]), 1))})
            objs = self._prev_objs or []
            by_oid = {getattr(o, "oid", None): o for o in objs}
            for oid in sorted(x for x in (self._auto_oids or set()) if x is not None):
                o = by_oid.get(oid)
                cen = getattr(o, "centroid", None) if o is not None else None
                nodes.append({"role": "autonomous", "oid": int(oid),
                              "centroid": (round(float(cen[0]), 1), round(float(cen[1]), 1)) if cen else None})
        except Exception:
            pass
        return nodes

    def articulate(self):
        """Legible KNOW summary for the META articulator (safe aggregates only)."""
        agree = (self.attr_agree / self.attr_checks) if self.attr_checks else None
        return dict(v18_perception=self.ok, steps=self.steps,
                    controllable_oid=self.ctrl_oid,
                    autonomous_movers=len(self._auto_oids),
                    controllable_locus=self._locus(),
                    task_type=self.task_type(),
                    causal_graph=self.causal_graph(),
                    attributor_v18_agreement=(round(agree, 3) if agree is not None else None),
                    attributor_checks=self.attr_checks,
                    predicate_hypotheses=(len(self.pred.preds) if self.pred is not None else 0),
                    agency_actions=len(self.clean_action_model()),
                    obj_set_upgrades=self.obj_adds)


# ============================================================================================================
# DO: v18 PriorPolicy._plan, ATOMIZED -- BFS shortest-path over the learned action->delta map, obstacle-aware.
# Pure function: returns the FIRST action toward goal, or None (caller falls back to greedy nav). Strictly
# stronger than greedy alignment nav because it routes AROUND obstacles instead of pushing into them.
# ============================================================================================================
def _bfs_first_action(start, goal, obstacles, amodel, shape):
    try:
        if not amodel or start is None or goal is None or shape is None:
            return None
        H, W = int(shape[0]), int(shape[1])
        from collections import deque as _dq
        s = (int(round(start[0])), int(round(start[1])))
        g = (int(round(goal[0])), int(round(goal[1])))
        q = _dq([s]); came = {s: (None, None)}
        steps = 0
        while q and steps < H * W + 4:
            steps += 1
            cur = q.popleft()
            if cur == g:
                a = None
                while came[cur][0] is not None:
                    cur, a = came[cur]
                return a
            for act, (dr, dc) in amodel.items():
                nxt = (cur[0] + int(round(dr)), cur[1] + int(round(dc)))
                if 0 <= nxt[0] < H and 0 <= nxt[1] < W and nxt not in obstacles and nxt not in came:
                    came[nxt] = (cur, act); q.append(nxt)
        return None
    except Exception:
        return None



# ============================================================================================================
# META: in-memory EPISODIC MEMORY (learn from wins AND losses, with active in-process retrieval). Lives on the
# agent instance for the whole session -- no Kaggle/working-space files -- so credit is retrievable every
# decision. On a WIN it credits the objective(s) that led there (and recent contributors); on a GAME_OVER it
# debits the active objective and, after repeated losses with no win, raises an EXHAUSTED signal that reinforces
# the existing refutation-ledger give-up. HONEST: this COMPOUNDS wins; it cannot create the first one. Recording
# + articulation are live; biasing the kernel's commit is exposed (weight/exhausted) but held for validation.
# ============================================================================================================
class EpisodicMemory:
    def __init__(self, trace=200):
        self.win_credit = Counter()
        self.loss_credit = Counter()
        self.wins = 0
        self.losses = 0
        self.recent = deque(maxlen=trace)   # in-memory trace of (objective_key, phase)

    @staticmethod
    def _key(objective):
        if not objective:
            return None
        try:
            if isinstance(objective, dict):
                return str(objective.get("spec"))[:120]
            return str(objective)[:120]
        except Exception:
            return None

    def note(self, objective, phase):
        k = self._key(objective)
        self.recent.append((k, phase))

    def on_win(self, objective):
        self.wins += 1
        k = self._key(objective)
        if k:
            self.win_credit[k] += 1.0
        for k2 in {kk for kk, _ in self.recent if kk}:   # spread partial credit to recent contributors
            self.win_credit[k2] += 0.25

    def on_loss(self, objective):
        self.losses += 1
        k = self._key(objective)
        if k:
            self.loss_credit[k] += 1.0

    def weight(self, objective):
        """Active-retrieval bias for an objective: net win-credit. Higher = more reliably led to wins."""
        k = self._key(objective)
        if not k:
            return 0.0
        return self.win_credit[k] - 0.5 * self.loss_credit[k]

    def exhausted(self, objective, thresh=4):
        """Repeated losses on an objective with zero wins -> reinforce the earned give-up (feeds the ledger)."""
        k = self._key(objective)
        return bool(k) and self.loss_credit[k] >= thresh and self.win_credit[k] == 0.0

    def articulate(self):
        return dict(wins=self.wins, losses=self.losses,
                    top_winning=[(k, round(v, 2)) for k, v in self.win_credit.most_common(3)],
                    top_losing=[(k, round(v, 2)) for k, v in self.loss_credit.most_common(3)])


# ============================================================================================================
# OUROBOROS REDUX -- the reason-first control spine with v18 perception placed underneath it.
# ============================================================================================================
class OuroborosRedux(_OI.OuroborosIntegrated):
    """Inherits the proven kernel / coast / validation / ledger / ui_planner / active_test / delay / temporal /
    match-abduction / spatial explorer wiring UNCHANGED. Upgrades exactly the bottleneck layer: object perception
    (v18 multi-colour cohesion union), controllable-ID (multi-mover attribution), and the navigation map (v18's
    reset-free identity-free agency action-model as an extra dmap fallback). v18's predicate/belief feed META
    articulation. Reorder realized; control spine untouched."""

    def __init__(self, pursue_cap=300):
        super().__init__(pursue_cap=pursue_cap)
        self._know = KnowLayer()
        self._episodic = EpisodicMemory()   # in-memory win/loss credit (active retrieval)
        self._last_shape = None
        self._redux = True

    # ---- KNOW: feed v18 perception every executed action (before, action, after) ----
    def _step(self, adapter, action, clicked):
        before = _read(adapter)
        res = super()._step(adapter, action, clicked)
        if action is not None:
            try:
                after = _read(adapter)
                self._last_shape = np.asarray(after).shape       # for the BFS nav (step-2)
                self._know.observe(before, action, after)
            except Exception:
                pass
        try:
            em = self._episodic
            em.note(getattr(self, 'objective', None), getattr(self, 'phase', None))
            if isinstance(res, dict):
                # TERMINAL-STATE GATE (critique 2): credit/debit on the GameState, never on the overloaded
                # `done`. won == (rew>0 or state==WIN) so a level-up credits as a sub-goal win; a loss is
                # ONLY a real GAME_OVER. The retired `(done and not won)` clause fired on every latched-done
                # post-level-up frame -- that was the 111-vs-7 over-count.
                if res.get('won'):
                    em.on_win(getattr(self, 'objective', None))            # learn from success (incl. sub-goal)
                elif res.get('state') == 'GAME_OVER':
                    em.on_loss(getattr(self, 'objective', None))           # learn from failure (terminal only)
                # Clear the EMPIRICAL no-reward marker blacklist on a genuine LEVEL ADVANCE: a colour that was a
                # decoy on this level may be the goal on the next (and vice versa), so the blacklist is level-local.
                # The structural sprite-colour exclusion persists (a sprite stays a sprite); only this clears.
                lv = res.get('levels_completed')
                if lv is not None:
                    last = self.__dict__.get('_last_seen_level')
                    if last is not None and lv > last:
                        self.__dict__.setdefault('_bad_markers', set()).clear()
                        self.__dict__.setdefault('_marker_noreward', Counter()).clear()
                    self.__dict__['_last_seen_level'] = lv
        except Exception:
            pass
        return res

    # ---- KNOW: non-avatar objects for the explore navigator. ROBUST + self-sufficient. ----
    # The spine's _other_objects routes through match_abduction._segment_mask -> molecule_prediction.
    # object_property_vector, which is UNDEFINED in this build, so it throws; KnowLayer.merged_objects hits the
    # same undefined function (wrapped, so it silently returned []). Latent until the dmap fix routed the
    # explorer into _other_objects, where the throw was swallowed by the dispatch and dropped the agent into
    # blind driving (nav unreached). The explore loop only reads centroids (never `vec`), so we segment directly
    # for cells+centroid, exclude the avatar, drop background-sized blobs, and never raise.
    def _other_objects(self, grid, self_pos, self_color):
        try:
            know = getattr(self, "_know", None)
            g = np.asarray(grid)
            objs = []
            if know is not None and getattr(know, "merger", None) is not None:
                try:
                    objs = know.merger.segment(g) or []
                except Exception:
                    objs = []
            if not objs and know is not None:
                objs = know._mask_objs(g)
            big = 0.30 * g.size
            out = []
            for o in objs:
                cells = [(int(r), int(c)) for (r, c) in getattr(o, "cells", [])]
                if not cells or len(cells) > big:                     # skip empty + background-sized blobs
                    continue
                cr = sum(r for r, _ in cells) / len(cells); cc = sum(c for _, c in cells) / len(cells)
                out.append(dict(cells=cells, centroid=(cr, cc)))
            if out and self_pos is not None:                          # exclude the avatar (nearest to self_pos)
                av = min(out, key=lambda o: abs(o["centroid"][0] - self_pos[0])
                         + abs(o["centroid"][1] - self_pos[1]))
                out = [o for o in out if o is not av]
            return out
        except Exception:
            return []

    # ---- AFFORD/DO (Option b): route the committed BE_AT marker into the working navigator ----
    def _compile(self, rpt, adapter):
        """Redux override. The anchor's _compile passed target_color=None to compile_discrepancy, so every
        relational disc (NONE.EXIST / COVER / SAME) came out vacuously 0 and BE_AT came out 1e9 -- tolerable
        when _disc only had to 'degrade to exploration', but the routed descend/pursue engines need a REAL
        measure to close. Compile each abduced hypothesis with its ACTUAL target (int colour OR a ('cell',..)/
        composite spec) and return the first NON-degenerate disc (0 < measure(grid0) < 1e9) -- a genuine,
        closable gap that matches the committed objective. Falls back to the anchor behaviour on any failure."""
        try:
            if _OV is None or not rpt or not rpt.get("hypotheses"):
                return super()._compile(rpt, adapter)
            grid0 = _read(adapter)
            ctrl = self.prop.controllable_for_mover()
            first = None
            for hyp in rpt["hypotheses"]:
                if not isinstance(hyp, dict):
                    continue
                spec = hyp.get("spec")
                try:
                    if spec is not None:
                        disc = _OV.compile_objective(spec, ctrl, grid0)
                    else:
                        disc = _OV.compile_discrepancy(hyp.get("relation"), ctrl,
                                                       hyp.get("target_color"), grid0)
                except Exception:
                    continue
                if disc is None or not (hasattr(disc, "measure") and hasattr(disc, "active")):
                    continue
                if first is None:
                    first = disc
                try:
                    m = float(disc.measure(grid0))
                except Exception:
                    continue
                if 0.0 < m < 1e9:                     # a genuine, closable gap -> prefer this disc
                    return disc
            return first if first is not None else super()._compile(rpt, adapter)
        except Exception:
            return super()._compile(rpt, adapter)

    def _pursue_explore(self, adapter):
        """The spine's _pursue_explore is pure COVERAGE -- it ignores self.objective, so on a committed
        BE_AT(controllable, colour-marker) the avatar covered its start corner (351 nav calls clustered near the
        origin) instead of heading to the exit. When a reach objective is committed with a RESOLVED controllable
        and a visible marker colour distinct from the avatar, drive the (already-working) navigator straight at
        the marker. Strictly gated: anything else (EXPLORE objective, command game, unresolved controllable,
        target == self colour) falls through to the proven coverage routine unchanged."""
        try:
            obj = getattr(self, "objective", None)
            spec = obj.get("spec") if isinstance(obj, dict) else None
            cl = self.current_locus()
            if isinstance(spec, dict) and spec.get("relation") in ("BE_AT", "TOUCH") and cl is not None:
                tcol = spec.get("target_color")
                if isinstance(tcol, int) and tcol != cl[2]:
                    r = self._reach_marker(adapter, tcol)
                    if r is not None:
                        return r
        except Exception:
            pass
        # AFFORD: route the PROVEN descend/pursue execution engines onto a committed, NON-degenerate discrepancy
        # for click/config games (SAME / NONE.EXIST / COVER / erase). These minimise disc.measure by clicking the
        # disc.active(g) cells (plus discrete moves) -- the exact capability the reach/nav path lacks -- and were
        # verified to solve a click-erase board in isolation (pursue: validated, 5/5 erased). Gated HARD: a real
        # disc with a real gap (measure>0) on a located-action (click) game; nav games fall through unchanged.
        try:
            disc = getattr(self, "_disc", None)
            located = bool(adapter.pointer_actions()) if hasattr(adapter, "pointer_actions") else False
            _is_command = bool(getattr(self, "_command_game", False) and getattr(self, "_commands", None))
            if _OV is not None and disc is not None and located and not _is_command:
                cur = _read(adapter)
                if float(disc.measure(cur)) > 0.0:        # non-degenerate: there is a discrepancy to close
                    self._decision = dict(engine="descend/pursue",
                                          rationale="closing a committed config discrepancy by located clicks "
                                                    "(SAME / NONE.EXIST / COVER)")
                    ctrl = self.current_locus()
                    r = None
                    try:
                        r = _OV.descend(adapter, disc, ctrl, budget=300)
                    except Exception:
                        r = None
                    if not (isinstance(r, dict) and r.get("validated")):
                        try:
                            r2 = _OV.pursue(adapter, disc, budget=800, max_clicks=8)
                            if isinstance(r2, dict):
                                r = r2
                        except Exception:
                            pass
                    if isinstance(r, dict):
                        ok = bool(r.get("validated"))
                        return dict(success=ok, validated=ok,
                                    reason=("won" if ok else "discrepancy-unclosed"),
                                    engine=r.get("engine") or "descend/pursue", history_len=len(self.history))
        except Exception:
            pass
        return super()._pursue_explore(adapter)

    def _reach_marker(self, adapter, tcol):
        """Focused reach: navigate the controllable to the nearest cell of the marker colour, using the unified
        locus + the colour-locus dmap + the working _nav_action. Mirrors the spine's _pursue_match reach loop
        (nav -> step -> avatar_track -> blocked.add(action) on no-move -> win/done/reached checks)."""
        dmap = self._dmap_cached(adapter)
        cl = self.current_locus()
        if not dmap or cl is None:
            return None
        d = self.__dict__.setdefault('_nav_reach_dbg', Counter())
        def marker_target(grid, sp):
            g = np.asarray(grid); ys, xs = np.where(g == tcol)
            if len(ys) == 0:
                return None
            k = int(np.argmin(np.abs(ys - sp[0]) + np.abs(xs - sp[1])))   # nearest marker cell to the avatar
            return (float(ys[k]), float(xs[k]))
        try:
            budget = int(min(self.pursue_cap, max(60, self.coast.adaptive_budget())))
        except Exception:
            budget = min(self.pursue_cap, 150)
        avg = max(1.0, sum(abs(v[0]) + abs(v[1]) for v in dmap.values()) / max(1, len(dmap)))
        step_r = max(2.0, 0.6 * avg); track_r = max(8.0, 2.2 * avg)
        self_pos = [cl[0], cl[1]]; blocked = set(); won = False; reason = "reward-unreached"; stuck = 0
        try:
            self.ledger.mark_reset()
        except Exception:
            pass
        for _ in range(budget):
            before = _read(adapter)
            target = marker_target(before, self_pos)
            if target is None:
                reason = "marker-gone"; break
            action = self._nav_action(self_pos, target, dmap, blocked)
            if action is None or action not in dmap:
                blocked.clear(); stuck += 1
                if stuck >= 3:
                    reason = "walled-from-marker"; break
                continue
            stuck = 0
            self._decision = dict(engine="redux-reach", target=(round(target[0], 1), round(target[1], 1)),
                                  marker_color=int(tcol),
                                  rationale="navigating the controllable to the committed goal marker")
            res = self._step(adapter, action, None); after = _read(adapter); won = bool(res.get("won"))
            self.history.append(dict(action=getattr(action, "name", action), clicked=None,
                                     before=before, after=after, won=won, phase="reach"))
            d['steps'] += 1
            prev = tuple(self_pos)
            nl = self.current_locus()
            self_pos = [nl[0], nl[1]] if nl is not None else list(self._avatar_track(before, after, prev, track_r))
            blocked.add(action) if (abs(self_pos[0] - prev[0]) + abs(self_pos[1] - prev[1]) < 0.5) else blocked.clear()
            if won:
                reason = "won"; break
            if res.get("done"):
                reason = "game-over"; break
            if abs(self_pos[0] - target[0]) + abs(self_pos[1] - target[1]) <= step_r:
                d['reached_marker'] += 1            # on the marker cell but no win => marker isn't the goal (abduction wrong)
                reason = "on-marker-no-reward"
                # DISPOSE: a colour reached repeatedly with no reward is empirically not a goal, whatever its
                # structural signature. Count it; on the 3rd no-reward reach, blacklist it for this game so the
                # abductor commits the next-best marker instead of re-committing this one (the 89-reach loop).
                nr = self.__dict__.setdefault('_marker_noreward', Counter())
                bad = self.__dict__.setdefault('_bad_markers', set())
                nr[int(tcol)] += 1
                if nr[int(tcol)] >= 3:
                    bad.add(int(tcol))
                break
        return dict(success=won, validated=won, reason=reason, engine="redux-reach", history_len=len(self.history))

    # ---- KNOW: multi-mover controllable attribution (the gap-fill) + cross-check (step-1, observe-only) ----
    def _avatar_track_expected(self, before, after, prev, exp, R):
        got = self._know.attribute_controllable(before, after, prev, exp, R)
        if got is not None:
            try:
                self._know.cross_check(got)      # record attributor vs v18-controllable agreement; drives nothing
            except Exception:
                pass
            return got
        return super()._avatar_track_expected(before, after, prev, exp, R)

    # ---- DO: BFS shortest-path nav (v18 _plan, atomized) with greedy fallback (step-2) ----
    def _live_agency(self, adapter):
        """Feed the FIXED KnowLayer controllable (colour-locus) into the abductor's report. The spine's slm
        gives a phantom locus on single-cell avatars (tu93: 63,10), so its marker_color is wall/background and
        the abductor cannot form BE_AT. When the KnowLayer resolved a discriminative colour-locus, override
        marker_color/locus/controllable with it -- this is what lets the abductor abduce BE_AT(avatar, exit)."""
        rpt = None
        try:
            rpt = super()._live_agency(adapter)
        except Exception:
            rpt = None
        try:
            know = getattr(self, "_know", None)
            if know is not None and getattr(know, "_cl_color", None) is not None:
                rpt = dict(rpt) if isinstance(rpt, dict) else {"modality": "translate", "located": None}
                rpt["modality"] = rpt.get("modality") or "translate"
                rpt["marker_color"] = int(know._cl_color)
                if getattr(know, "_cl_locus", None) is not None:
                    rpt["locus"] = (float(know._cl_locus[0]), float(know._cl_locus[1]))
                dm = know.clean_action_model() or {}
                if dm:
                    rpt["controllable"] = list(dm.keys())
            elif know is not None and know.task_type() == "command":
                # TASK-TYPE PRIOR (critique 3): no localized controllable resolved AND positive command evidence
                # (directional actions move nothing steerable). Bias the spine's command classifier toward
                # ui_planner routing. A PRIOR, not a gate: abduction/reward downstream can still overturn it.
                rpt = dict(rpt) if isinstance(rpt, dict) else {"located": None}
                rpt["modality"] = "command"
            # Stamp the (stable) task-type onto the report so abduce can see the nav regime even on a cycle whose
            # own controllable read is momentarily empty (Option c: sink NONE.EXIST below BE_AT on nav games).
            if know is not None and isinstance(rpt, dict):
                rpt["task_type"] = know.task_type()
                # MARKER-SELECTION wire: colours to exclude from goal-marker candidates = sprite colours (move
                # WITH the avatar) | the no-reward blacklist (reached >=3x with no reward). Game-local.
                try:
                    excl = set(know.sprite_colors()) | set(self.__dict__.get("_bad_markers", set()))
                    if excl:
                        rpt["exclude_markers"] = sorted(int(c) for c in excl)
                except Exception:
                    pass
        except Exception:
            pass
        return rpt

    def compose_fn(self, perception):
        """Redux override. The spine sets _command_game from selfdesc.modality=='command', but a command game
        has NO self-object -> selfdesc is None -> _command_game stays False even when task_type()=='command',
        so the ui_planner (sequence-search) branch never fires. Reconcile: a POSITIVELY-classified command game
        (KNOW's task_type prior) routes the ui_planner path -- distinct from the descend/pursue click-active-cells
        path. commands_from_proprioception finds nothing when no component is modality-tagged, so fall back to the
        salient clickable controls. Wraps super() (which sets the objective + disc); we only reconcile the flag."""
        out = super().compose_fn(perception)
        try:
            know = getattr(self, "_know", None)
            if know is not None and know.task_type() == "command" and not self._command_game:
                self._command_game = True
                if not self._commands:
                    self._commands = self._command_cells(perception)
                if isinstance(getattr(self, "objective", None), dict):
                    self.objective["command_game"] = True
                    self.objective["n_commands"] = len(self._commands)
        except Exception:
            pass
        return out

    def _command_cells(self, perception, cap=12):
        """Clickable command controls for ui_planner, when proprioception tagged none: one representative cell per
        distinct non-background component (candidate buttons/controls). Bounded so the sequence search stays cheap;
        reward disposes which command actually transforms the world. Located clicks only -- pure ('click', r, c)."""
        try:
            g = np.asarray(_read(perception))
        except Exception:
            try:
                g = np.asarray(perception._grid(getattr(perception, "_obs", None)))
            except Exception:
                return []
        try:
            from scipy.ndimage import label as _label
            bg = int(np.bincount(g.ravel()).argmax())
            cells = []
            for c in np.unique(g):
                if int(c) == bg:
                    continue
                lab, n = _label(g == c)
                for i in range(1, n + 1):
                    ys, xs = np.where(lab == i)
                    if len(ys) <= 20:                       # a control is small; skip large structures/fields
                        cells.append(("click", int(ys.min()), int(xs.min())))
            # nearest-to-origin first (stable), bounded
            cells.sort(key=lambda t: (t[1], t[2]))
            return cells[:cap]
        except Exception:
            return []

    # ---- UNIFIED STATE ESTIMATOR (critique 1): ONE source of truth for "where/what am I". ----
    # The abductor (via _live_agency), the pursuit SEED (_self_pos0), the pursuit UPDATER (_avatar_track), and
    # the avatar-mask colour (_self_color_of) read from three different sensors -- proprioception, the slm
    # phantom, and radius-R continuity -- none of them the discriminative colour-locus. On a single-cell avatar
    # proprioception is empty, so _self_pos0 returned None, the pursuit bailed at `if pos0 is None`, run_level
    # aborted at entry, and _nav_action was never reached (empty _nav_dbg). These overrides route every
    # downstream reader to the colour-locus when it has resolved (and is a small localized footprint), falling
    # back to the proven spine estimate otherwise. Spine class itself stays untouched.
    def current_locus(self):
        """The single self-estimate: (row, col, body_colour) from the discriminative colour-locus when it has
        resolved AND is localized, else None so callers fall back to the spine."""
        know = getattr(self, "_know", None)
        if know is None:
            return None
        loc = getattr(know, "_cl_locus", None); col = getattr(know, "_cl_color", None)
        if loc is None or col is None:
            return None
        try:
            if not know._locus_is_localized():
                return None
        except Exception:
            pass
        return (float(loc[0]), float(loc[1]), int(col))

    def _self_pos0(self):
        cl = self.current_locus()
        if cl is not None:
            self._self_color = cl[2]            # keep the colour wire synced at this single point
            return (cl[0], cl[1])
        return super()._self_pos0()

    def _self_color_of(self, grid):
        cl = self.current_locus()
        if cl is not None:
            return cl[2]
        return super()._self_color_of(grid)

    def _avatar_track(self, before, after, prev, R):
        # After an executed step the colour-locus centroid IS the avatar's current cell (it equals prev when the
        # avatar was blocked, so the spine's blocked-detection still holds). Prefer it over radius-R continuity,
        # which is only as good as its seed; fall back when the locus is unresolved.
        cl = self.current_locus()
        if cl is not None:
            return (cl[0], cl[1])
        return super()._avatar_track(before, after, prev, R)

    def _dmap_cached(self, adapter):
        # UNIFIED STATE, extended to the action-model (the dmap is the same provenance bug as the locus): the
        # explore navigator plans over a dmap the spine builds from the reset-probe or the noisy slm -- neither
        # is the discriminative colour-locus dmap that _live_agency already resolved. On a single-cell avatar the
        # probe cannot measure displacement and the slm map is phantom, so _dmap_cached returned {} and
        # _pursue_explore bailed at `if not dmap: return None` BEFORE _nav_action -- the empty _nav_dbg. Prefer
        # the colour-locus action-model when it has >=2 directions; fall back to the proven spine sources.
        try:
            know = getattr(self, "_know", None)
            if know is not None:
                cm = know.clean_action_model() or {}
                if cm and len(cm) >= 2:
                    self._dmap = dict(cm)        # unify the spine's dmap cache onto the good source
                    return self._dmap
        except Exception:
            pass
        return super()._dmap_cached(adapter)

    def _nav_action(self, self_pos, target, dmap, blocked):
        try:
            d=self.__dict__.setdefault('_nav_dbg', Counter()); d['calls']+=1
            d['has_dmap']+= (1 if dmap else 0)
            bus=getattr(self._know,'_last',None)
            d['has_frame']+= (1 if (bus is not None and getattr(bus,'frame',None) is not None) else 0)
            if target is not None:
                d['tgt_'+str((int(round(target[0])//8), int(round(target[1])//8)))] += 1
            # A-vs-B discriminator: is the avatar MOVING across calls, or stuck (re-planning from one cell)?
            if self_pos is not None:
                cur=(int(round(self_pos[0])), int(round(self_pos[1])))
                prev=self.__dict__.get('_nav_last_sp')
                if prev is not None:
                    d['sp_moved' if (abs(cur[0]-prev[0])+abs(cur[1]-prev[1])>=1) else 'sp_stuck'] += 1
                self.__dict__['_nav_last_sp']=cur
                d['selfcell_'+str((cur[0]//8, cur[1]//8))] += 1     # self_pos cell histogram (coarse, safe)
        except Exception: pass
        # AFFORD information-probe: complete the action->displacement map. Nav only ever issues actions TOWARD
        # the target, so a direction never needed (e.g. UP when the exit is down-right) is never sampled -> its
        # dmap entry stays unknown -> BFS cannot route through it (tu93 stayed red with ACTION1/UP unsampled).
        # Before planning, if an available discrete action has no observed displacement yet, ISSUE it to learn
        # its vector. Bounded per cell (a wall-blocked direction can't stall nav) and per action total (a true
        # no-op is abandoned), re-armed as the avatar moves so UP gets retried from cells where up is open.
        try:
            adp = getattr(self, "_adapter", None)
            if adp is not None and self._know is not None:
                avail = list(adp.discrete_actions() or [])
                # "sampled" must match the bar nav actually uses: _raw_sample_dmap trusts an action only at
                # kn>=2 modal samples. Probing only until the action first appears in _cl_disp (1 move) leaves
                # it one sample short, so nav's dmap stayed 3-directional all run (measured dmapdirs_3 x274) and
                # UP never entered the move-grid. Probe until the direction is TRUSTED into the live dmap.
                try:
                    sampled = set(self._know._raw_sample_dmap().keys())
                except Exception:
                    sampled = set(a for per in self._know._cl_disp.values() for a in per)
                cell = None if self_pos is None else (int(round(self_pos[0])) // 8, int(round(self_pos[1])) // 8)
                pt = self.__dict__.setdefault("_probe_tries", {})     # (action, cell) -> count
                ptt = self.__dict__.setdefault("_probe_total", {})    # action -> total probes
                unknown = [a for a in avail if a not in sampled and ptt.get(a, 0) < 12]
                cand = [a for a in unknown if pt.get((a, cell), 0) < 3]
                if cand:
                    a = min(cand, key=lambda x: pt.get((x, cell), 0))
                    pt[(a, cell)] = pt.get((a, cell), 0) + 1
                    ptt[a] = ptt.get(a, 0) + 1
                    self.__dict__.setdefault("_nav_dbg", Counter())["probe_" + str(getattr(a, "name", a))] += 1
                    return a
        except Exception:
            pass
        # LOGICAL-CELL navigation on the avatar's MOVE grid. Sub-pixel boards step ~one move-cell per action
        # (tu93: ~7px, landing 6-8px by alignment); the engine wins on move-CELL overlap, not pixel-exact, so
        # pixel-BFS (matching an exact landing coordinate) never converges and the avatar steps past the exit.
        # Plan in move-cells (cell pitch = the dmap displacement, aligned to the avatar), emit the next step.
        try:
            if dmap and self._know is not None:
                bus = getattr(self._know, "_last", None)
                frame = np.asarray(bus.frame) if (bus is not None and getattr(bus, "frame", None) is not None) else None
                if frame is not None and frame.ndim == 2:
                    a = self._cell_nav(frame, self_pos, target, dmap, blocked)
                    if a is not None:        # _cell_nav may plan on the raw-sample dmap, whose actions are real
                        return a             # observed moves but need not appear in the (degenerate) passed dmap
        except Exception:
            pass
        shape = getattr(self, "_last_shape", None)
        if shape is not None and dmap:
            a = _bfs_first_action(self_pos, target, set(blocked or ()), dmap, shape)
            if a is not None and a in dmap:
                return a
        return super()._nav_action(self_pos, target, dmap, blocked)

    def _cell_nav(self, frame, self_pos, target, dmap, blocked):
        """BFS over the avatar's MOVE grid (pitch = dmap displacement, NOT the render pitch). Walls = non-bg
        cells (excluding avatar+target colour). Returns the action whose move-direction is the first path step."""
        _cd = self.__dict__.setdefault('_cell_dbg', Counter()); _cd['calls'] += 1
        def _pitch_of(dm):
            rm = [abs(d[0]) for d in dm.values() if abs(d[0]) > abs(d[1])]
            cm = [abs(d[1]) for d in dm.values() if abs(d[1]) >= abs(d[0]) and abs(d[1]) > 0]
            return (int(round(float(np.median(rm)))) if rm else 0,
                    int(round(float(np.median(cm)))) if cm else 0)
        pr, pc = _pitch_of(dmap)
        # Prefer the live raw-sample dmap (straight from _cl_disp) when it covers MORE cardinal directions than
        # the passed dmap. The passed dmap can be non-degenerate (good pitch) yet INCOMPLETE -- e.g. missing UP
        # before the ACTION1 probe sampled it -- and an incomplete dmap strips a whole axis from the move-grid,
        # so BFS fails on any path needing that direction (measured: avail=3, bfs_failed > bfs_found). Also still
        # rescues the degenerate-pitch case (the slm bootstrap fallback). OOD-safe: directions read from samples.
        def _ndirs(dm):
            s = set()
            for d in dm.values():
                if abs(d[0]) >= abs(d[1]) and d[0] != 0:
                    s.add((1 if d[0] > 0 else -1, 0))
                elif d[1] != 0:
                    s.add((0, 1 if d[1] > 0 else -1))
            return len(s)
        try:
            rd = self._know._raw_sample_dmap() if self._know is not None else {}
        except Exception:
            rd = {}
        if rd:
            pr2, pc2 = _pitch_of(rd)
            if (pr2 >= 2 or pc2 >= 2) and (_ndirs(rd) > _ndirs(dmap) or pr < 2 or pc < 2):
                dmap = rd; pr, pc = pr2, pc2; _cd['used_raw_sample'] += 1
        if pr == 0 and pc >= 2:                           # single-axis pitch -> square move-grid (Outcome-B)
            pr = pc
        if pc == 0 and pr >= 2:
            pc = pr
        _cd['pitch_%d_%d' % (pr, pc)] += 1                # effective pitch after raw-sample + single-axis fixes
        if pr < 2 or pc < 2:
            _cd['ret_pitch_too_small'] += 1
            return None                                   # not a coarse move-grid -> let pixel-BFS handle it
        H, W = frame.shape
        or_ = int(round(self_pos[0])) % pr
        oc = int(round(self_pos[1])) % pc
        nr = (H - or_) // pr; nc = (W - oc) // pc
        if nr < 2 or nc < 2:
            _cd['ret_grid_too_small'] += 1
            return None
        spec = {"pr": pr, "pc": pc, "or_": or_, "oc": oc, "nr": nr, "nc": nc, "H": H, "W": W}
        def to_cell(p):
            rr = int(round((float(p[0]) - or_) / pr)); cc = int(round((float(p[1]) - oc) / pc))
            return (max(0, min(nr - 1, rr)), max(0, min(nc - 1, cc)))
        s = to_cell(self_pos); t = to_cell(target)
        if s == t:
            _cd['ret_already_on_cell'] += 1               # avatar+target collapse to one logical cell
            return None                                   # already on the move-cell -> base finishes (overlap)
        cell_dir = {}
        for a, d in dmap.items():
            if abs(d[0]) >= abs(d[1]) and d[0] != 0:
                cell_dir[a] = (1 if d[0] > 0 else -1, 0)
            elif d[1] != 0:
                cell_dir[a] = (0, 1 if d[1] > 0 else -1)
        small = _gp.downsample(frame, spec) if _gp is not None else None
        walls = set()
        if small is not None:
            bg = int(np.bincount(frame.ravel()).argmax())
            av = getattr(self._know, "_cl_color", None)
            tgt_col = int(small[t[0], t[1]])
            for i in range(nr):
                for j in range(nc):
                    v = int(small[i, j])
                    if v != bg and v != tgt_col and (av is None or v != av):
                        walls.add((i, j))
            walls.discard(s); walls.discard(t)
        _cd['wallcells'] += len(walls); _cd['gridcells'] += nr * nc    # (A) perception: wall fraction of the grid
        # diagnostic: which colours became walls, and is the START cell walled-in by them? (halo-trap test)
        if small is not None:
            try:
                for (i, j) in walls:
                    _cd['wallcol_%d' % int(small[i, j])] += 1
            except Exception:
                pass
        avail = [(a, cd) for a, cd in cell_dir.items() if a not in (blocked or set())]
        try:
            _cd['celldirs_%d' % len(cell_dir)] += 1
            _cd['blocked_%d' % len(blocked or ())] += 1
            _cd['dmapdirs_%d' % _ndirs(dmap)] += 1
        except Exception:
            pass
        nbr_walled = sum(1 for (_a, (dr, dc)) in avail
                         if not (0 <= s[0]+dr < nr and 0 <= s[1]+dc < nc) or (s[0]+dr, s[1]+dc) in walls)
        _cd['sNbrWalled_%d_of_%d' % (nbr_walled, len(avail))] += 1
        from collections import deque
        came = {s: None}; q = deque([s])
        while q:
            cur = q.popleft()
            if cur == t:
                break
            for a, (dr, dc) in avail:
                nx = (cur[0] + dr, cur[1] + dc)
                if 0 <= nx[0] < nr and 0 <= nx[1] < nc and nx not in walls and nx not in came:
                    came[nx] = (cur, a); q.append(nx)
        if t in came and came[t] is not None:
            _cd['bfs_found'] += 1                          # (C) search: BFS found a path to the target cell
            node, first = t, None
            while came[node] is not None:
                node, first = came[node][0], came[node][1]
            return first
        _cd['bfs_failed'] += 1                             # (C) no path -> greedy fallback drives toward target
        dr, dc = t[0] - s[0], t[1] - s[1]                 # walled-in -> greedy toward target cell
        for a, (cdr, cdc) in avail:
            if (dr != 0 and cdr != 0 and (cdr > 0) == (dr > 0)) or (dc != 0 and cdc != 0 and (cdc > 0) == (dc > 0)):
                _cd['greedy_fired'] += 1
                return a
        _cd['no_action'] += 1
        return None

    # ---- KNOW->DO: v18 agency action-model as an extra reset-free dmap fallback ----
    def _dmap_cached(self, adapter):
        d = super()._dmap_cached(adapter)
        if d:
            return d
        try:
            am = self._know.clean_action_model()
            if am:
                return am
        except Exception:
            pass
        return d


# ============================================================================================================
# META: articulation. The refactor checklist's STANDING INVARIANT -- the only failure allowed to halt the
# build -- is the agent's ability to ARTICULATE its typed components + evidence. This surfaces the KnowLayer's
# perception/agency state into the per-action reasoning trace, alongside the spine's objective/molecule
# articulation. Never raises; the proven reasoning_snapshot is untouched (this only augments it for Redux).
# ============================================================================================================
def redux_reasoning(oi, action, grid=None):
    try:
        snap = _OI.reasoning_snapshot(oi, action, grid)
    except Exception:
        snap = {"action": getattr(action, "name", str(action))}
    try:
        know = getattr(oi, "_know", None)
        if know is not None:
            snap["perception"] = know.articulate()
        em = getattr(oi, "_episodic", None)
        if em is not None:
            snap["episodic"] = em.articulate()
    except Exception:
        pass
    return snap
