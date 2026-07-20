"""Integrated Ouroboros agent: v18 (0.18) spine + bridged capability layers.

SPINE (native, untouched): v18 MyAgent — continuous play, active-inference policy,
PredicateInducer, SelfModel/GoalModel, Relations/Physics/Number/Geometry, feature-
invention germline, Strategy/TaskBelief.

BRIDGED LAYERS (additive; each guarded so a failure contributes nothing, never crashes):
  - speaking          : emit v18's own belief/strategy/phase + the active goal channel
  - banking           : record per-level winning action sequences
  - goal-injection    : objective_abductor/goal_cues/affordance/object_seg feed v18's
                        _induce_goal (exploit phase) as extra target candidates
  - objective-click   : in click mode, pursue an ABDUCED objective (reward-arbitrated,
                        hypothesis-rotated) instead of pure impact-probing  [cd82/lp85 gate]
  - controllable-est  : cell-motion from the rolling buffer estimates the agent where
                        v18's tracker finds none (advisor; surfaced + feeds the channel)
  - compose-on-refut  : stuck-at-goal (reached target, progress flat) -> push a composed
                        AND target into the goal channel
  - affordance        : attribute-diff across the buffer -> relational-equality goal
  - grid-perception   : detect logical grid (surfaced; click-snap hook ready)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as _np
import v18_agent as _v18

def _imp(n):
    try: return __import__(n)
    except Exception: return None
_sc   = _imp("solution_cache")
_abd  = _imp("objective_abductor")
_gc   = _imp("goal_cues")
_aff  = _imp("affordance_kernel")
_oseg = _imp("object_seg")
_gp   = _imp("grid_perception")
_cf   = _imp("common_fate")


def _ctrl_color(objs, ctrl):
    for o in objs:
        if getattr(o, "oid", None) == ctrl:
            return getattr(o, "color", None)
    return None


_ACTNAME2ID = {"RESET": 0, "ACTION1": 1, "ACTION2": 2, "ACTION3": 3, "ACTION4": 4, "ACTION5": 5, "ACTION6": 6}
def _act_id(action):
    nm = getattr(action, "name", None)
    if nm in _ACTNAME2ID: return _ACTNAME2ID[nm]
    try: return int(getattr(action, "value", action))
    except Exception: return 0


def capability_goals(grid, ctrl_color, start, struct_mask=None):
    """All frame-level objective layers -> ranked [(cell,score,source)]."""
    out = []; g = _np.asarray(grid)
    if _abd is not None:
        try:
            for t in _abd.perceive_targets(g, exclude_color=ctrl_color):
                cr, cc = t["centroid"]
                out.append(((int(round(cr)), int(round(cc))), 0.5 / (1.0 + 0.01 * t["size"]), "abduct"))
        except Exception: pass
    if _gc is not None:
        try:
            for cue in _gc.read_goal_cues(g, agent_color=ctrl_color):
                conf = float(cue.get("confidence", 0.3))
                cell = cue.get("target") or cue.get("cell")
                if cell is None:
                    cs = cue.get("cells") or cue.get("targets")
                    if cs: cell = cs[0]
                if cell is not None:
                    out.append(((int(cell[0]), int(cell[1])), 0.7 * conf, "cue:" + str(cue.get("relation", cue.get("kind", "?")))))
        except Exception: pass
    if _aff is not None:
        try:
            aobjs = _aff.perceive_objects(g)
            for o in aobjs:                                  # CAP 1: attributed-object centroids
                a = o.attrs() if hasattr(o, "attrs") else {}
                cen = a.get("centroid")
                if cen is None and getattr(o, "cells", None):
                    rs = [c[0] for c in o.cells]; cs = [c[1] for c in o.cells]
                    cen = (sum(rs) / len(rs), sum(cs) / len(cs))
                if cen is not None:
                    out.append(((int(round(cen[0])), int(round(cen[1]))), 0.4, "afford"))
            # CAP 6: relational-EQUALITY goals -- two objects sharing shape but differing attribute
            if hasattr(_aff, "equality_measure"):
                for i in range(len(aobjs)):
                    for j in range(i + 1, len(aobjs)):
                        try:
                            d = _aff.equality_measure(aobjs[i], aobjs[j])
                        except Exception:
                            continue
                        if d is not None and 0 < float(d) <= 1.0:     # near-equal: a real "make A equal B" goal
                            b = aobjs[j]; ba = b.attrs() if hasattr(b, "attrs") else {}
                            cen = ba.get("centroid")
                            if cen is None and getattr(b, "cells", None):
                                rs = [c[0] for c in b.cells]; cs = [c[1] for c in b.cells]
                                cen = (sum(rs) / len(rs), sum(cs) / len(cs))
                            if cen is not None:
                                out.append(((int(round(cen[0])), int(round(cen[1]))), 0.65, "equal"))
        except Exception: pass
    if _oseg is not None:
        try:
            for s in (_oseg.segment_objects(g) or []):
                cen = s.get("centroid") if isinstance(s, dict) else None
                if cen is not None:
                    out.append(((int(round(cen[0])), int(round(cen[1]))), 0.35, "objseg"))
        except Exception: pass
    if _cf is not None and struct_mask is not None and hasattr(_cf, "candidate_targets"):
        try:                                                 # common_fate: distinct-colour invariant goal/key regions
            for t in _cf.candidate_targets(g, struct_mask):
                cen = t.get("centroid") if isinstance(t, dict) else t
                if cen is not None:
                    out.append(((int(round(cen[0])), int(round(cen[1]))), 0.45, "cf-target"))
        except Exception: pass
    best = {}
    for cell, sc, src in out:
        if cell not in best or sc > best[cell][0]:
            best[cell] = (sc, src)
    return sorted(((c, v[0], v[1]) for c, v in best.items()), key=lambda x: -x[1])


def _structure_mask(buf):
    """Cells invariant across the recent buffer = structure (common_fate input). Loop-callable
    substitute for adapter-probing decompose: structure is what does NOT change as the agent acts."""
    grids = [b[0] for b in buf[-8:] if b[0] is not None]
    if len(grids) < 3 or any(x.shape != grids[0].shape for x in grids):
        return None
    inv = _np.ones(grids[0].shape, dtype=bool)
    for x in grids[1:]:
        inv &= (x == grids[0])
    return inv & (grids[0] != _np.bincount(grids[0].ravel()).argmax())


# The REAL composer (objective_validator.validate_multilevel via thread-inverted _QueueAdapter)
# is reused verbatim from the composer's my_agent.py -- NOT re-implemented. The router below
# delegates click-regime games to it (the code that actually won lp85/cd82), keeping v18 for movers.
_composer_mod = _imp("my_agent")

# Per-level escalating budget ladder (shared by both arms).
try:
    import budget_ladder as _bl
except Exception:
    _bl = None

def _regime(avail):
    """Action-space regime for difficulty classification."""
    try: avs = set(int(x) for x in (avail or []))
    except Exception: avs = set()
    if not avs: return "mover"
    if avs.issubset({6, 7}): return "click"
    if (avs & {1, 2, 3, 4, 5}) and (avs & {6, 7}): return "mixed"
    return "mover"

def _cheap_action(avail=None):
    """A cheap, deterministic, NON-destructive action for cheap-burn (a move; never RESET/click).

    It must come from the actions the GAME OFFERS. This hardcoded ACTION5 on a board whose available_actions are
    [1,2,3,4]: the engine accepts it and nothing happens, so it reads as harmless -- but it is a spent action, and on
    this game a level costs 41-54 actions against a meter worth ~42. There is no slack in which a free no-op exists.
    A no-op is only ever legitimate as a DELIBERATE choice (letting an animation settle), never as a default.
    """
    try:
        from arcengine import GameAction as GA
    except Exception:
        return None
    avs = set()
    for a in (avail or []):
        try:
            avs.add(int(getattr(a, "value", a)))
        except Exception:
            nm = str(getattr(a, "name", a)).upper()
            if nm.startswith("ACTION"):
                try:
                    avs.add(int(nm[6:]))
                except Exception:
                    pass
    for aid in (5, 1, 2, 3, 4):                      # prefer a true no-op mover, else any offered direction
        if aid in avs:
            return getattr(GA, "ACTION%d" % aid, None)
    return GA.ACTION5 if not avs else None           # nothing offered -> old behaviour rather than a crash


class MyAgent(_v18.MyAgent):
    """v18 spine + bridged capability layers."""
    MAX_ACTIONS = 10000                       # FINITE per-game safety cap (guide trap #4); per-level budget
                                              # controller + cheap-burn keep efficiency well under this
    PER_LEVEL_ACTIONS = 500                  # DIAGNOSTIC per-level cap (all routes): a level should fall in a few
                                              # hundred moves, so >1000 on one level == stuck/spamming -> end the game
                                              # and surface it rather than burn the run. Resets each level. Universal
                                              # backstop atop the composer-arm's own per-level cap.

    def __init__(self, *a, **kw):
        self._speak_on = bool(kw.pop("speak", os.environ.get("OURO_SPEAK")))
        self._bridge_on = kw.pop("bridge", True)
        super().__init__(*a, **kw)
        self.speech_log = []; self._goal_bb = None; self._hook_on = False
        self._act_seq = []; self._banked = {}; self._prev_levels = 0
        self._buf = []                       # rolling (grid, action_id, progress)
        self._agent_est = None               # controllable estimate from buffer
        self._grid_spec = None
        self._hook_calls = 0
        # composer routing (real objective_validator via thread-inversion)
        self._route = None                   # None -> v18 phase; "composer" -> delegate
        self._composer = None
        self._steps = 0
        # per-level budget controller (v18 arm)
        self._lvl_acts = 0                    # actions spent on the current level
        self._last_belief = 0.0              # top predicate belief seen (for belief-rising progress)
        self._budget_now = 0                 # working budget, walked up while yielding
        self._budget_type = "MED"            # judged difficulty (re-judged each step)
        self._budget_verdict = "continue"
        self._cheap_burn = False             # latched once a level exhausts its type ceiling (hopeless)
        self._burn_steps = 0

    # ---------- goal-injection hook (exploit phase) ----------
    def _ensure_hook(self):
        if self._hook_on or not self._bridge_on: return
        pol = getattr(self, "policy", None)
        if pol is None or not hasattr(pol, "_induce_goal"): return
        _orig = pol._induce_goal; agent = self
        def _wrapped(objs, ctrl, grid, start, progress):
            agent._hook_calls += 1
            native = _orig(objs, ctrl, grid, start, progress)
            try:
                sm = _structure_mask(agent._buf)
                caps = capability_goals(grid, _ctrl_color(objs, ctrl), start, struct_mask=sm)
            except Exception: caps = []
            chosen, src = native, "v18"
            composed = agent._compose_on_refutation(caps)
            if composed is not None:
                chosen, src = composed, "compose-AND"
            elif native is None and caps:
                chosen, src = caps[0][0], caps[0][2]
            elif caps and caps[0][1] > 0.6:
                chosen, src = caps[0][0], caps[0][2]
            agent._goal_bb = dict(native=native, caps=caps[:4], chosen=chosen, src=src)
            return chosen
        pol._induce_goal = _wrapped; self._hook_on = True

    def _top_belief(self) -> float:
        """Highest predicate belief in v18's PredicateMemory — the 'belief rising' progress signal."""
        try:
            preds = getattr(self.policy.pred, "preds", [])
            return max((float(getattr(p, "belief", 0.0)) for p in preds), default=0.0)
        except Exception:
            return 0.0

    def _compose_on_refutation(self, caps):
        """Stalled (many goal-hook calls, no level gained) -> aim at a composed AND midpoint
        of the two strongest candidates: self-composed richer objective from refuting evidence."""
        if self._hook_calls < 25 or len(caps) < 2:
            return None
        (a, _, _), (b, _, _) = caps[0], caps[1]
        return ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)

    # ---------- controllable estimate from the rolling buffer ----------
    def _estimate_agent(self):
        """common_fate-style: cells that change under my actions = candidate agent.
        Advisor where v18's tracker finds no controllable."""
        if len(self._buf) < 6: return None
        from collections import Counter
        moved = Counter()
        for (g0, a0, _), (g1, _, _) in zip(self._buf[-8:], self._buf[-7:]):
            if g0 is None or g1 is None or g0.shape != g1.shape: continue
            diff = _np.argwhere(g0 != g1)
            if 0 < len(diff) <= 12:
                for r, c in diff: moved[(int(r), int(c))] += 1
        if not moved: return None
        rc, n = moved.most_common(1)[0]
        return rc if n >= 2 else None

    # ---------- composer routing: delegate click-regime games to the REAL composer ----------
    def _should_route_composer(self):
        # ALL LOGIC REACHABLE: the rich engine (validate_multilevel, driven via the composer) carries EVERY reasoning
        # service -- grammar, compass, model_doubt, mechanics_hypotheses, model_coherence, the fluid routing, unified
        # reasoning -- AND handles BOTH avatar and actuator regimes. v18 (the mover path) has NONE of these, so routing
        # movers to v18 leaves the entire rich stack unreachable. Default: route EVERY game through the rich engine so
        # all logic is usable on all 25. v18 remains the FALLBACK when the composer is unavailable, and the legacy
        # v18-for-movers split is available via OURO_LEGACY_ROUTING for comparison/revert.
        if not self._bridge_on or _composer_mod is None:
            # composer unavailable -> v18 fallback: it PLAYS, and none of the rich engine is reachable. This is the
            # most dangerous state the agent has, because it looks exactly like a normal run: the harness scores it,
            # the recording fills with actions, and the ONLY outward sign is that every action carries
            # reasoning=null -- v18 has no reasoning services to attach. A 456-action recording of this was mistaken
            # for a narration-wiring bug. Silent fallbacks cost exactly what silent failures cost, so: say it.
            self._warn_fallback("_composer_mod is None (my_agent failed to import)" if _composer_mod is None
                                else "bridge=False was passed to the constructor")
            return False
        if os.environ.get("OURO_LEGACY_ROUTING"):
            return self._legacy_should_route_composer()
        return True                                        # ALL games -> rich engine (every reasoning service reachable)

    def _warn_fallback(self, why):
        """Once per agent, loudly, on the same lane the ban lines use. NOT swallowed."""
        if getattr(self, "_fallback_warned", False):
            return
        self._fallback_warned = True
        msg = ("ROUTE  *** COMPOSER UNAVAILABLE -> v18 FALLBACK *** [%s]  The rich engine (grammar, budget model, "
               "abduction, residual routing) is UNREACHABLE for this whole game. Every action from here carries "
               "reasoning=null. This run does NOT reflect the submission brain." % why)
        try:
            self.speech_log.append(msg)
        except Exception:
            pass
        sys.stderr.write("[ouro] %s\n" % msg); sys.stderr.flush()
        if os.environ.get("OURO_STRICT_BRIDGE"):           # dev/CI: refuse to score a run that is not the real brain
            raise RuntimeError(msg)

    def _legacy_should_route_composer(self):
        if not self._bridge_on or _composer_mod is None:
            return False
        av = getattr(self, "_avail", None)
        try: avs = set(int(x) for x in av) if av else set()
        except Exception: avs = set()
        # click-only action space -> the composer's regime, route immediately
        if avs and avs.issubset({6, 7}) and 6 in avs:
            return True
        # no mover after enough probing + clicks legal + no progress -> click/erase regime (e.g. cd82).
        # 50 steps gives v18 ample time to identify a controllable on genuine mover games (g50t IDs by ~30).
        if (self._steps > 50 and getattr(self, "policy", None) is not None
                and self.policy.sm.controllable() is None
                and (6 in avs or not avs)
                and float(getattr(self, "_last_progress", 0.0)) <= 0.0):
            return True
        return False

    # ---------- main loop ----------
    def _attach_reasoning(self, action, lf, mode="mover"):
        """HELM #6 -- ride a REASONING payload on EVERY action so nothing is sent silently (a silent action runs to zero
        on OOD with no teacher). Re-evaluates the dynamics regime each step (SHARED.control_regime: avatar / multi_avatar
        / actuator, re-evaluable so a game can SWITCH) and packages the disciplines: objective-as-hypothesis, only-a-win-
        confirms, and the explicit DISPROOF for this decision. Never raises, never changes the action's effect."""
        try:
            import regime_factory as _RF
            sm = getattr(getattr(self, "policy", None), "sm", None)
            ctrl = sm.controllable() if sm is not None else None
            est = getattr(self, "_agent_est", None)
            avail = None
            try:
                avail = set(int(getattr(a, "value", a)) for a in (self.actions() or []))
            except Exception:
                avail = None
            clicks_only = bool(avail) and avail.issubset({6, 7})
            steps = int(getattr(self, "_steps", 0))
            if ctrl is not None:
                n_arg = len(est) if (isinstance(est, (list, tuple)) and len(est) >= 2) else 1
            elif clicks_only or steps >= 50:
                n_arg = 0
            else:
                n_arg = None                                   # still probing -> 'unknown', keep hunting the self
            regime = _RF.SHARED.control_regime.classify(n_arg, clicks_only, steps)
            frame_read = (("controllable at %s" % (ctrl,)) if ctrl is not None else
                          ("click/actuator dynamics -- no controllable found after %d steps" % steps
                           if regime == "actuator" else "probing for the controllable (co-movement not yet established)"))
            fam = getattr(self, "family", None) or (self.policy.family() if hasattr(getattr(self, "policy", None), "family") else None)
            rule_hyp = ("family=%s objective (provisional -- tested by acting, confirmed only by a level win)" % fam) if fam else None
            payload = _RF.SHARED.decision_reasoning.build(
                regime, action, frame_read=frame_read, rule_hypothesis=rule_hyp,
                expect="advances the provisional objective; forward-model residual should FALL if the read is right",
                disproof="residual stays high, or the controllable/roles behave unlike this read (then RE-DERIVE)",
                step=steps, extra={"mode": mode, "cap": self.MAX_ACTIONS})
            _RF.SHARED.decision_reasoning.attach(action, payload)
        except Exception:
            pass
        return action

    def _ensure_reasoning(self, action):
        # THE LEGALITY GATE lives here because every return in choose_action funnels through this one call. A guard
        # that some paths can bypass is not a guard; putting it at the single choke point is the only way it holds
        # for code that has not been written yet.
        try:
            action = MyAgent._legal(action, getattr(self, "_last_fd", None))
        except Exception:
            pass
        # Framework does `if action.reasoning:`; arcengine.GameAction lacks that attr by default -> AttributeError.
        # Guarantee it exists (keep any real reasoning; else empty string).
        if action is not None:
            try:
                _r = getattr(action, "reasoning", None)
                action.reasoning = _r if _r is not None else ""
            except Exception:
                pass
        return action

    @staticmethod
    def _legal(action, fd):
        """FINAL GATE: never emit an action the game does not offer.

        `available_actions` is the game telling us its vocabulary every single frame. Emitting outside it is not a
        harmless mistake -- the engine accepts it, nothing happens, and a real action is gone. Any component may
        propose whatever it likes; nothing gets past here without being on the board's own list.
        """
        try:
            avail = list(getattr(fd, "available_actions", None) or [])
            if not avail or action is None:
                return action
            ids = set()
            for a in avail:
                try:
                    ids.add(int(getattr(a, "value", a)))
                except Exception:
                    nm = str(getattr(a, "name", a)).upper()
                    if nm.startswith("ACTION"):
                        try:
                            ids.add(int(nm[6:]))
                        except Exception:
                            pass
                    elif nm == "RESET":
                        ids.add(0)
            want = int(getattr(action, "value", -1))
            if want in ids or want == 0:
                return action
            from arcengine import GameAction as _GA
            for aid in sorted(i for i in ids if i > 0):
                sub = getattr(_GA, "ACTION%d" % aid, None)
                if sub is not None:
                    try:
                        sub.reasoning = "substituted: %s is not offered on this board (available=%s)" % (
                            getattr(action, "name", action), sorted(ids))
                    except Exception:
                        pass
                    return sub
            return action
        except Exception:
            return action

    def choose_action(self, frames, lf=None):
        # CRASH GUARD: a single unseen/OOD frame must never kill the whole submission. On any unhandled exception,
        # degrade to a safe legal action so the run continues to the next game instead of terminating.
        # PER-LEVEL DIAGNOSTIC CAP (all routes): count actions on the current level, reset on level advance. When any
        # level exceeds PER_LEVEL_ACTIONS the game is stuck/spamming -> flagged so _is_done_impl ends it cleanly.
        try:
            _capfd = lf if lf is not None else (frames[-1] if isinstance(frames, (list, tuple)) and frames else None)
            self._last_fd = _capfd                          # the frame whose available_actions the gate consults
            _caplvl = (getattr(_capfd, "levels_completed", 0) or 0) if _capfd is not None else 0
            if _caplvl != getattr(self, "_cap_lvl", None):
                self._cap_lvl = _caplvl; self._cap_acts = 0
            self._cap_acts = getattr(self, "_cap_acts", 0) + 1
        except Exception:
            pass
        try:
            _act = self._choose_action_impl(frames, lf)
            return self._ensure_reasoning(_act)
        except Exception as _exc:
            try:
                from arcengine import GameAction as _GA
                _fd = lf if lf is not None else (frames[-1] if isinstance(frames,(list,tuple)) and frames else None)
                _avail = list(getattr(_fd, "available_actions", None) or [])
                for _a in _avail:
                    _nm = str(getattr(_a, "name", _a)).upper()
                    if _nm != "RESET":
                        _ga = _GA.from_name(_nm) if hasattr(_GA, "from_name") else getattr(_GA, _nm, None)
                        if _ga is not None:
                            try: _ga.reasoning = "safe-fallback after %s" % type(_exc).__name__
                            except Exception: pass
                            return self._ensure_reasoning(_ga)
                return self._ensure_reasoning(getattr(_GA, "ACTION1", None))
            except Exception:
                return None

    def is_done(self, frames, lf=None):
        # CRASH GUARD: never let a bad frame raise out of is_done (would abort the game/run).
        try:
            return self._is_done_impl(frames, lf)
        except Exception:
            return False

    def _choose_action_impl(self, frames, lf=None):
        self._steps += 1
        # already routed: the real composer drives the rest of this game
        if self._route == "composer":
            return self._composer.choose_action(frames, lf)
        # CHEAP-BURN: this level exhausted its type ceiling without clearing (hopeless). Stop spending
        # expensive perception/search/bridge compute -- emit a cheap, deterministic, non-destructive move
        # so the shared wall-clock budget is freed for games that can still progress. Never RESET.
        if self._cheap_burn:
            self._burn_steps += 1
            ca = _cheap_action(getattr(_capfd, "available_actions", None) if "_capfd" in dir() else None)
            if ca is not None:
                return self._attach_reasoning(ca, lf, mode="cheap-burn")

        self._ensure_hook()
        action = super().choose_action(frames, lf)   # v18 spine (+ goal injection)

        # rolling buffer + grid-spec + controllable estimate (v18 phase)
        try:
            fd = lf if lf is not None else (frames[-1] if isinstance(frames, (list, tuple)) and frames else None)
            grid = None
            if fd is not None and hasattr(self, "_grid"):
                try: grid = self._grid(fd)
                except Exception: grid = None
            self._buf.append((_np.asarray(grid) if grid is not None else None,
                              getattr(action, "name", action), getattr(self, "_last_progress", 0.0)))
            if len(self._buf) > 40: self._buf.pop(0)
            # PASSIVE online affordance -> scored path: build action->dynamics from the buffer the agent
            # already keeps (no probing, no extra budget) and hand it to objective_abductor. Throttled;
            # any failure leaves the prior empty (-> no behaviour change). lp85 differential-verified.
            if self._steps % 10 == 0 and len(self._buf) >= 6:
                try:
                    import recon as _recon
                    _trans = [(self._buf[i][0], self._buf[i][1], self._buf[i + 1][0])
                              for i in range(len(self._buf) - 1)]
                    _abd.set_affordance(_recon.affordance_from_transitions(_trans).get("elicited", []))
                except Exception: pass
            if self._bridge_on and grid is not None and _gp is not None and self._grid_spec is None:
                try: self._grid_spec = _gp.detect_grid(_np.asarray(grid))
                except Exception: pass
            if self._bridge_on and getattr(self, "policy", None) is not None and self.policy.sm.controllable() is None:
                self._agent_est = self._estimate_agent()
        except Exception: pass

        # ---- per-level budget controller (v18 arm): account, classify, judge yield ----
        # The budget is a RESOURCE walked up while the level yields; type sets the ceiling (HARD ~7k).
        # Conservative: ceilings exceed the real wins, so this never cuts a known solve.
        try:
            if self._bridge_on and self._route is None and _bl is not None and getattr(self, "policy", None) is not None:
                self._lvl_acts += 1
                g = self._buf[-1][0] if self._buf else None
                ctrl = self.policy.sm.controllable() is not None
                fam = getattr(self, "family", None) or (self.policy.family() if hasattr(self.policy, "family") else None)
                self._budget_type = _bl.classify(_regime(getattr(self, "_avail", None)), ctrl, fam,
                                                 grid_cells=int(g.size) if g is not None else None)
                nov = float(getattr(self.policy, "_recent_novelty", 0.0))
                topb = self._top_belief()
                belief_rising = topb > self._last_belief + 1e-9
                if topb > self._last_belief: self._last_belief = topb
                progressing = (nov > 0.05) or belief_rising or ctrl     # per-arm progress signal (v18)
                self._budget_now = _bl.next_budget(self._budget_now, self._budget_type, progressing)
                self._budget_verdict = _bl.verdict(self._lvl_acts, self._budget_type, progressing)
                if self._budget_verdict == "ceiling":
                    self._cheap_burn = True       # hopeless: exhausted the type ceiling -> stop spending compute
        except Exception: pass

        # speaking + banking
        try:
            self.speech_log.append(_speak(self, action))
            if _bl is not None and self._route is None:
                self.speech_log[-1] += (f" | budget[{self._budget_type} "
                                        f"{self._lvl_acts}/{_bl.ceiling(self._budget_type)} {self._budget_verdict}]")
            if self._speak_on: print("  [ouro] " + self.speech_log[-1], flush=True)
        except Exception: pass
        try:
            fd = lf if lf is not None else (frames[-1] if isinstance(frames, (list, tuple)) and frames else None)
            lv = getattr(fd, "levels_completed", None)
            self._act_seq.append(_act_id(action))
            if lv is not None and lv > self._prev_levels:
                seq = list(self._act_seq)
                self._banked[self._prev_levels] = seq
                if _sc is not None:                       # PERSIST the banked level (solution_cache)
                    try: _sc.record_solution(getattr(self, "game_id", "stub"), self._prev_levels, seq)
                    except Exception: pass
                self._act_seq = []; self._prev_levels = lv; self._hook_calls = 0
                self._lvl_acts = 0; self._last_belief = 0.0; self._budget_now = 0   # new level -> fresh budget
                self._cheap_burn = False; self._burn_steps = 0
        except Exception: pass

        # regime decision: hand the rest of the game to the REAL composer if this is its regime
        if self._route is None and self._should_route_composer():
            try:
                self._composer = _composer_mod.MyAgent(game_id=getattr(self, "game_id", "stub"))
                self._route = "composer"
            except Exception as _e:
                # Second silent door to the same room: routing SAID composer, construction failed, and the agent
                # quietly played v18 for the rest of the game with reasoning=null. Same fingerprint, same cost.
                self._warn_fallback("composer construction raised %s: %s" % (type(_e).__name__, _e))
                self._route = None
        return self._attach_reasoning(action, lf, mode="mover")

    def _is_done_impl(self, frames, lf=None):
        """FRAMEWORK CONTRACT (guide §2/§4): finish the game so the harness advances. Composer-routed
        games defer to the composer's own WIN-or-exhausted signal; v18-routed games end on WIN, on a
        hopeless level (cheap-burn past the type ceiling), or at the finite per-game cap. Returning
        False forever is the classic hang."""
        if self._route == "composer" and self._composer is not None:
            try:
                if self._composer.is_done(frames, lf): return True
            except Exception: pass
            if getattr(self, "_cap_acts", 0) > self.PER_LEVEL_ACTIONS:
                return True                                  # per-level diagnostic cap (composer route)
            return self._steps >= self.MAX_ACTIONS       # backstop if the composer's own guard fails
        try:
            if super().is_done(frames, lf):                  # WIN
                return True
        except Exception: pass
        if getattr(self, "_cheap_burn", False) and self._burn_steps > 200:
            return True                                      # current level hopeless -> end game, advance
        if getattr(self, "_cap_acts", 0) > self.PER_LEVEL_ACTIONS:
            return True                                      # per-level diagnostic cap (v18 route)
        if self._steps >= self.MAX_ACTIONS:
            return True
        return False


def _speak(agent, action):
    parts = []
    fam = getattr(agent, "family", None)
    if fam is not None: parts.append(f"family={fam}")
    bel = getattr(agent, "_belief", None)
    if bel is not None:
        try:
            post = bel.posterior()
            if isinstance(post, dict) and post:
                t = max(post.items(), key=lambda kv: kv[1]); parts.append(f"belief:{t[0]}={t[1]:.2f}")
        except Exception: pass
    if getattr(agent, "_agent_est", None) is not None:
        parts.append(f"agent_est={agent._agent_est}")
    bb = getattr(agent, "_goal_bb", None)
    if bb: parts.append(f"goal={bb['chosen']}<{bb['src']}>")
    if getattr(agent, "_grid_spec", None): parts.append("grid+")
    parts.append("phase=" + ("click" if getattr(agent, "_click_mode", False) else "move/explore"))
    parts.append(f"-> {getattr(action,'name',action)}")
    return " | ".join(str(p) for p in parts)
