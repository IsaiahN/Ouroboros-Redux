"""ouroboros_integrated.py -- THE SWITCHOVER, built non-destructively.

Wires the six reason-first layers + temporal + validation into ONE runnable agent, with a LIVE causal
history feeding the validation engine every step:

    perception/proprioception  ->  type self/world/constraint/autonomous (evidence + falsifiable claims)
    temporal.probe_temporal    ->  past-manipulation self (descriptive; not generically checkable yet)
    objective_abductor.abduce  ->  ranked objective over the controllable
    kernel.Kernel              ->  compose-first loop; OBJECTIVE_INVALID vs PURSUIT_FAILED attribution
    coast.CoastController       ->  adaptive pursue budget
    persistent_model           ->  never-reset accumulation + explanation_quality
    validation                 ->  check_prediction per step + is_understanding (internal PROCTOR gate)

What this module does NOT do (deliberately, deferred to a with-Isaiah game-gate moment):
  * it does NOT replace integrated_agent.MyAgent.choose_action -- the scored entry point is untouched;
  * it does NOT thread-invert into the platform's per-call interface (that is the entry-swap);
  * the driver here is a DIRECT soundness/smoke test (does the wiring run, does causal history populate,
    does validation produce verdicts) -- NOT the game gate (does it WIN by composition).

So this is the switchover assembled and exercised, with the irreversible swap held back on purpose.
"""
import numpy as np

import proprioception as _prop_mod
import persistent_model as _pm_mod
import coast as _coast_mod
import kernel as _kernel_mod
import validation as _val
import temporal as _temporal
import delay_operator as _dly
import self_recognition as _selfrec
import active_test as _active
import ui_planner as _uiplan
import molecule_prediction as _mp
import refutation_ledger as _rl
import perception as _perc
import match_abduction as _matchab
import trigger_effect as _te
import spatial_map as _smap_mod
try:
    import self_model as _self_model
except Exception:
    _self_model = None

try:
    import objective_abductor as _abd
except Exception:
    _abd = None
try:
    import objective_validator as _ov
except Exception:
    _ov = None


def _read(adapter):
    return np.asarray(adapter._grid(adapter._obs)).copy()


import collections as _collections


class ResetPolicy:
    """RESET is a guarded DECISION, not a characterization reflex (recovered from the ouro v1/v2 doctrine and
    v2's should_proactive_reset). A level RESET destroys forward progress, and sprayed with no guard it pins the
    agent in NOT_FINISHED -- stuck by default -- so it is LICENSED only by a fired guard: stuck (no score-
    progress for `stuck_actions` actions), oscillation (a long run with no frame change), or proactively near
    the action-budget end (so we get a fresh attempt instead of dying). It is CAPPED per level. The game-START
    reset (entering the game once) is always licensed. The policy holds no game state, so knowledge is preserved
    across a reset. This is the single place a reset is allowed; everything else is DENIED."""

    def __init__(self, budget=400, stuck_actions=60, max_resets_per_level=2, osc_window=24, osc_frac=0.85):
        self.budget = int(budget) if budget else 400
        self.stuck_actions = int(stuck_actions)
        self.max_resets_per_level = int(max_resets_per_level)
        self.osc_window = int(osc_window)
        self.osc_frac = float(osc_frac)
        self.total_actions = 0
        self.started = False
        self._new_level(0)

    def _new_level(self, level):
        self.level = level
        self.since_progress = 0
        self.resets_this_level = 0
        self.recent_changed = _collections.deque(maxlen=self.osc_window)

    def observe(self, *, progressed=False, frame_changed=True, level=None):
        self.total_actions += 1
        if level is not None and level > self.level:
            self._new_level(level)                          # advanced a level -> progress, fresh per-level state
            return
        self.since_progress = 0 if progressed else self.since_progress + 1
        self.recent_changed.append(bool(frame_changed))

    def _oscillating(self):
        if len(self.recent_changed) < self.osc_window:
            return False
        nochange = sum(1 for c in self.recent_changed if not c)
        return nochange >= int(self.osc_frac * self.osc_window)

    def license_reset(self, deliberate_reason=None):
        """Return a reason string (GRANT) or None (DENY). The ONLY licensing point for a level RESET."""
        if not self.started:
            self.started = True
            return "game-start"                             # the game must be entered exactly once
        if self.resets_this_level >= self.max_resets_per_level:
            return None                                     # per-level cap reached
        if deliberate_reason:
            return deliberate_reason                        # control loop made an explicit, capped decision
        if self.since_progress >= self.stuck_actions:
            return "stuck:%da-no-progress" % self.since_progress
        if self._oscillating():
            return "oscillation:no-frame-change"
        if self.total_actions >= int(0.9 * self.budget) and self.since_progress > 0:
            return "near-budget-end"
        return None                                         # DENY: no guard fired -> reset is not a reflex

    def commit(self, reason):
        if reason != "game-start":
            self.resets_this_level += 1
        self.since_progress = 0
        self.recent_changed.clear()


class OuroborosIntegrated:
    def __init__(self, pursue_cap=300):
        self.prop = _prop_mod.Proprioception()
        self.pm = _pm_mod.PersistentModel()
        self.coast = _coast_mod.CoastController()
        self.components = []
        self.molecules = []               # abduced molecules carrying CHECKABLE predictions (refuted live)
        self.ledger = _rl.RefutationLedger()   # persists refuted molecules ACROSS resets
        self._last_level = None                # for cross-level re-licensing (new_episode on advance)
        self.temporal = None
        self.recognized_selves = []
        self.history = []                 # LIVE causal history: dict(action, clicked, before, after, won, phase)
        self.objective = None
        self.phase = "explore"
        self._command_game = False
        self._commands = []
        self.active_recognition = dict(confirmed={}, recommend="explore")
        self.pursue_cap = pursue_cap
        self._adapter = None
        self._disc = None
        self._act_cycle = 0
        self._match = None                # composition layer: abduced (mutable->template) MATCH sub-objective
        self._dmap = None                 # cached self action->displacement map (navigation primitive)
        self._self_color = None           # avatar body colour (for movement-based tracking)
        self._te_model = _te.TriggerEffectModel()   # OO-MDP condition-effect model (persistent across rollouts)
        self._decision = None             # last per-action decision rationale (for reasoning traces)

    # ---------------- compose ----------------
    def compose_fn(self, perception):
        adapter = perception                                  # perception IS the adapter
        self._adapter = adapter
        live_mode = getattr(self, "_live_mode", False)
        new_game = getattr(self, "_probed_adapter", None) is not adapter
        if new_game:
            self._probed_adapter = adapter
            self._abd_report = None
            self._probe_licensed_level = False
            self.components = []
            self.temporal = None
            self.recognized_selves = []
            self._map_explored = False                        # explore-first: reachable map not yet mapped
            self._level_start_actions = getattr(getattr(self, "_reset_policy", None), "total_actions", 0)
        if live_mode:
            # HYBRID-C: characterize from LIVED experience by default -- no stepping, no resets. The self is
            # typed from the (before,action,after) history (proprioception.from_buffer) and the brain's live
            # slm; the agency report abduce needs is read passively off the slm. The reset-anchored probe is
            # NOT a reflex -- it is a LICENSED decision spent only when this live evidence is insufficient.
            buf = self._transitions()
            try:
                self.components = list(self.prop.from_buffer(buf)) if buf else []
            except Exception:
                self.components = []
            self._abd_report = self._live_agency(adapter)
            live_ok = bool(self.components) or (self._abd_report is not None)
            if self._should_license_probe(live_ok):
                # live typing was insufficient AND we have played enough to know it -> spend ONE reset-anchored
                # probe this level (a deliberate decision; the gate permits its resets only inside this block).
                self._probe_licensed_level = True
                with self._reset_license("characterization-probe"):
                    try:
                        self.components = list(self.prop.probe(adapter)) or self.components
                    except Exception:
                        pass
                    try:
                        self.temporal = _temporal.probe_temporal(adapter) or self.temporal
                    except Exception:
                        pass
                    try:
                        self.recognized_selves = self._recognize_selves(adapter) or self.recognized_selves
                    except Exception:
                        pass
                    try:
                        self._abd_report = _abd.agency_report(adapter) if _abd is not None else self._abd_report
                    except Exception:
                        pass
        elif new_game:
            # LEGACY path (gate disabled): reset-anchored probe once per game.
            try:
                self.components = list(self.prop.probe(adapter))
            except Exception:
                self.components = []
            try:
                self.temporal = _temporal.probe_temporal(adapter)
            except Exception:
                self.temporal = None
            try:
                self.recognized_selves = self._recognize_selves(adapter)
            except Exception:
                self.recognized_selves = []
        comps = self.components
        try:
            self.pm.absorb(comps)                             # never-reset accumulation
        except Exception:
            pass
        rpt = None
        if _abd is not None:
            try:
                if live_mode:
                    # PASSIVE abduction: abduct on the current frame using the live agency report. Never call
                    # the stepping agency_report here (it would drift the avatar). No report yet -> defer.
                    if self._abd_report is not None:
                        rpt = _abd.abduce(adapter, reset_first=False, prior_report=self._abd_report)
                else:
                    # The agency report (controllable/locus/modality) is reset-heavy -- it runs its own action
                    # probe. Compute it ONCE per game, then abduct on the CURRENT frame WITHOUT a whole-game
                    # reset (the documented reset_first=False / prior_report path).
                    if getattr(self, "_abd_report", None) is None:
                        self._abd_report = _abd.agency_report(adapter)
                    rpt = _abd.abduce(adapter, reset_first=False, prior_report=self._abd_report)
            except Exception:
                rpt = None
        selfdesc = self.prop.self_for_composer()
        committed = _val.committed(self.components)
        temporal_committed = bool(self.temporal and self.temporal.get("modality") == "temporal")
        spec = (rpt["hypotheses"][0] if (rpt and rpt.get("hypotheses")) else None)
        self._disc = self._compile(rpt, adapter)
        # MOLECULE LAYER: lift checkable predictions onto the abduced relations so each is causally
        # refutable per-transition (the precondition for the refutation ledger). Routed through the SAME
        # validation path; uncommitted (no checkable prediction) molecules are dropped, exactly as percepts.
        self.molecules = self._molecules_from(rpt, self._disc, adapter)
        # ACTION-INDEXED CAUSAL molecules (Layer 2): complement the abductor's GLOBAL relations with LOCAL,
        # per-action effect hypotheses grounded in observed transitions -- the ARC-3 ontology the global
        # vocabulary cannot express. Routed through the SAME validation/ledger path as every other molecule.
        try:
            if live_mode:
                self.molecules = self.molecules + self._action_effect_molecules_from_history()
            else:
                self.molecules = self.molecules + self._action_effect_molecules(adapter)
        except Exception:
            pass
        # COMPOSITION LAYER: from the ACCUMULATED history (where the agent has seen the key change), abduce a
        # MATCH sub-objective -- a mutable object (key) whose property vector should reach an invariant
        # template (lock). If found, license it (refutable) and arm it as the active sub-objective so pursuit
        # achieves the MATCH before the terminal goal (match THEN reach). None unless the structure is real.
        self._match = None
        try:
            frames = self._recent_frames()
            sc = self.prop.self_component()
            self_c = None
            if sc is not None and getattr(sc, "cells", None):
                cs = list(sc.cells)
                self_c = (sum(r for r, _ in cs) / len(cs), sum(c for _, c in cs) / len(cs))
            roles = _matchab.abduce_match_roles(frames, self_centroid=self_c) if len(frames) >= 3 else None
            if roles is not None:
                loc = _matchab.nearest_object_locator(roles["mutable_centroid"])
                mm = _mp.match_molecule("MATCH(key->lock)", loc, roles["template_vec"])
                self.molecules = self.molecules + [mm]
                self._match = dict(measure=mm.prediction["measure"], roles=roles)
        except Exception:
            self._match = None
        committed_mols = _val.committed(self.molecules)
        # REFUTATION LEDGER: license what the abductor proposed (observation-gated) and eliminate the
        # refuted across resets. The ledger persists, so re-abducing the same molecule never re-tests a
        # closed branch; exhaustion is judged from the licensed space being empty, not from no-reward.
        self.ledger.license(self.molecules)
        self.ledger.update(self.history, phase=self.phase)
        # unexplainable = uncommitted: bind an objective only if SOMETHING is justified
        if selfdesc is None and not committed and not temporal_committed and not committed_mols:
            return None                                       # -> Outcome.OBJECTIVE_INVALID
        # the kernel enforces unexplainable=uncommitted via obj['justification']; surface it honestly
        if selfdesc is not None:
            justification = selfdesc["justification"]
        elif temporal_committed:
            justification = self.temporal["evidence"]
        elif committed:
            justification = committed[0].evidence
        else:
            justification = [f"molecule:{committed_mols[0].identity}"]   # a committed molecule justifies
        # EXPLORE-FIRST: when a navigable (translate) avatar is recognised, its FIRST objective is to MAP its
        # reachable space -- not to commit a relational target (COVER) on something it may not even have seen,
        # and not to give up, while reachable ground is still unvisited. Hold this objective until the reachable
        # map is covered (frontier gone) or the explore budget is spent, then fall through to the relation.
        mod = (self._abd_report or {}).get("modality")
        if selfdesc is not None and mod == "translate" and not self._reachable_explored():
            self._command_game = False
            self.objective = dict(
                spec={"relation": "EXPLORE", "descriptor": "EXPLORE(reachable-map)", "target_color": None},
                justification=list(justification) + ["explore-first: map the avatar's reachable space"],
                self=selfdesc, explore=True, abduction=rpt, committed=len(committed),
                temporal=self.temporal, disc=(self._disc is not None), command_game=False,
                molecules=len(committed_mols))
            return self.objective
        # COMMAND game (no self-target relation): set up the UI planner over command SEQUENCES (11.334).
        # The self-target discrepancy compiles degenerately here; planning over commands is the right tool.
        self._command_game = bool(selfdesc and selfdesc.get("modality") == "command")
        self._commands = _uiplan.commands_from_proprioception(self.prop) if self._command_game else []
        self.objective = dict(spec=spec, justification=justification, self=selfdesc, abduction=rpt,
                              committed=len(committed), temporal=self.temporal,
                              disc=(self._disc is not None), command_game=self._command_game,
                              n_commands=len(self._commands), molecules=len(committed_mols))
        return self.objective

    def _compile(self, rpt, adapter):
        """Best-effort: compile the top abduced relation into a Discrepancy. Returns None on any failure --
        the wiring (history + validation) does not depend on a valid discrepancy; pursuit just degrades to
        exploration. A real game gate would harden this path."""
        if _ov is None or not rpt or not rpt.get("hypotheses"):
            return None
        grid0 = _read(adapter)
        ctrl = self.prop.controllable_for_mover()
        for hyp in rpt["hypotheses"]:
            try:
                rel = hyp.get("relation") if isinstance(hyp, dict) else hyp
                disc = _ov.compile_discrepancy(rel, ctrl, None, grid0)
                if disc is not None and hasattr(disc, "measure") and hasattr(disc, "active"):
                    return disc
            except Exception:
                continue
        return None

    def _recognize_selves(self, adapter, steps=12):
        """Collect per-object centroid trajectories over a short rollout, take the proprioceptive self as the
        reference footprints, and INDUCE which other objects are the self lagged (DELAY). Guarded; returns []
        on any failure. We do NOT label objects as avatar/ghost -- the DELAY fit against the self's own trace
        is what recognises a lagged self, leaving the rest as reactive triggers."""
        s = self.prop.self_component()
        if s is None or not getattr(s, "cells", None):
            return []
        try:
            tracker = _perc.Perception()
            adapter.reset()
            acts = list(adapter.discrete_actions() or [])
            traj = {}
            shape = _read(adapter).shape
            self_cells = {tuple(int(x) for x in c) for c in s.cells}
            self_oid = None
            for i in range(steps):
                g = _read(adapter)
                objs, _ = tracker.update(g)
                for o in objs:
                    traj.setdefault(o.oid, [None] * i).append(tuple(round(v) for v in o.centroid))
                for oid in traj:                                   # pad to frame i
                    if len(traj[oid]) < i + 1:
                        traj[oid] += [None] * (i + 1 - len(traj[oid]))
                if self_oid is None:                               # bind self by OVERLAP with its footprint smear
                    best = None
                    for o in objs:
                        oc = {tuple(int(x) for x in c) for c in getattr(o, "cells", [])}
                        ov = len(oc & self_cells)
                        if ov > 0 and (best is None or ov > best[1]):
                            best = (o.oid, ov)
                    if best:
                        self_oid = best[0]
                if acts:
                    adapter.step(acts[i % len(acts)])
            if self_oid is None or self_oid not in traj:
                return []
            self_fp = traj.pop(self_oid)
            out = _selfrec.induce(self_fp, traj, shape)
            return out["recognized_selves"]
        except Exception:
            return []

    def active_recognize(self, adapter, rounds=2, length=3):
        """ACTIVE phase: rather than waiting for the world to reveal a delayed self, INJECT distinctive pings
        and confirm which objects echo them (pinning the lag), via active_test. Uses the proprioceptive self
        as the reference. Guarded -> returns {} on any failure. Stores results on self.active_recognition."""
        self.active_recognition = dict(confirmed={}, recommend="explore")
        try:
            s = self.prop.self_component()
            if s is None or not getattr(s, "cells", None):
                self.prop.probe(adapter); s = self.prop.self_component()
            if s is None or not getattr(s, "cells", None):
                return self.active_recognition
            self.active_recognition = _active.active_self_recognition(adapter, s.cells, rounds=rounds,
                                                                      length=length)
        except Exception:
            pass
        return self.active_recognition

    # ---------------- pursue (records LIVE causal history -> validation) ----------------
    def _action_effect_molecules(self, adapter):
        """Probe each discrete action once from a clean reset, read its colour-transition signature, and lift
        an action-indexed causal-effect molecule per action. Game-agnostic (the same probe runs everywhere;
        the signature is measured, never a per-game rule). Guarded -> [] on any failure; resets the adapter
        at the end so pursuit starts from a clean episode."""
        try:
            acts = list(adapter.discrete_actions() or [])
        except Exception:
            return []
        if not acts:
            return []
        sigs = {}
        try:
            for a in acts:
                adapter.reset()
                bf = _read(adapter)
                self._step(adapter, a, None)
                af = _read(adapter)
                if getattr(bf, "shape", None) != getattr(af, "shape", None):
                    continue
                diff = np.argwhere(bf != af)
                sig = {(int(bf[r, c]), int(af[r, c])) for r, c in diff}
                if sig:
                    sigs[getattr(a, "name", a)] = sig          # key matches the action logged in pursue
            adapter.reset()
        except Exception:
            return []
        try:
            return _mp.action_effect_molecules(sigs)
        except Exception:
            return []

    # ---------------- HYBRID-C: live-by-default characterization, reset-anchored probe as a LICENSED decision ----------------
    def _transitions(self, k=40):
        """The lived (before, action, after) tuples from causal history -- the substrate the live, no-reset
        characterization types the self from. Bounded to the most recent k."""
        out = []
        for e in self.history[-k:]:
            bf = e.get("before"); af = e.get("after"); a = e.get("action")
            if bf is None or af is None or e.get("clicked") is not None:
                continue
            out.append((np.asarray(bf), a, np.asarray(af)))
        return out

    def _action_effect_molecules_from_history(self, k=60):
        """Action-indexed causal-effect molecules built from LIVED transitions instead of reset-probing. Same
        builder/validation path as the reset version -- the signatures just come from play, not from resets."""
        sigs = {}
        for e in self.history[-k:]:
            if e.get("clicked") is not None:
                continue
            a = e.get("action"); bf = e.get("before"); af = e.get("after")
            if a is None or bf is None or af is None:
                continue
            bf = np.asarray(bf); af = np.asarray(af)
            if getattr(bf, "shape", None) != getattr(af, "shape", None):
                continue
            diff = np.argwhere(bf != af)
            if len(diff):
                sigs.setdefault(a, set()).update((int(bf[r, c]), int(af[r, c])) for r, c in diff)
        if not sigs:
            return []
        try:
            return _mp.action_effect_molecules({a: s for a, s in sigs.items() if s})
        except Exception:
            return []

    def _live_agency(self, adapter):
        """A PASSIVE agency report (modality / marker_color / locus) read off the brain's live slm -- no
        stepping, no resets. This is what abduce needs (it reads only those three keys) so abduction runs on
        the current frame without the reset-heavy probe. None until the slm has seen a coherent move."""
        slm = getattr(self, "_slm", None)
        if slm is None or not getattr(slm, "move", None):
            return None
        try:
            coh = slm.coherent_actions()
        except Exception:
            coh = [a for a, d in slm.move.items() if (d[0] or d[1])]
        if not coh:
            return None
        loc = getattr(slm, "locus", None)
        mc = None
        try:
            g = _read(adapter)
            if loc is not None:
                rr, cc = int(round(loc[0])), int(round(loc[1]))
                if 0 <= rr < g.shape[0] and 0 <= cc < g.shape[1]:
                    v = int(g[rr, cc])
                    if v != 0:
                        mc = v
        except Exception:
            pass
        return {"modality": "translate", "marker_color": mc,
                "locus": (None if loc is None else (float(loc[0]), float(loc[1]))),
                "controllable": list(coh), "located": None}

    def _reset_license(self, reason):
        """Context manager that LICENSES reset-anchored probing as a deliberate decision (recovered doctrine:
        reset is a decision, not a reflex). Inside the block the gate permits the probe's resets; outside, they
        are denied. Use only when live characterization is insufficient and a guard says the probe is worth it."""
        outer = self

        class _Lic:
            def __enter__(self_):
                outer._reset_license_active = reason
                return self_

            def __exit__(self_, *a):
                outer._reset_license_active = None
                return False
        return _Lic()

    def _should_license_probe(self, live_ok):
        """Guard for spending a reset-anchored characterization probe: ONLY when the live, no-reset path could
        not type a controllable, we have not already spent the probe this level, and either (a) we have played
        enough that "no controllable" is informative, or (b) there were no discrete actions to bootstrap from at
        all (a pure-click game -- the live path is empty by construction, so the licensed probe is the right
        first move). Keeps the expensive probe a rare, deliberate decision."""
        if live_ok:
            return False
        if getattr(self, "_resets_disabled", False):
            return False                                   # resets disabled -> the reset-probe is pointless
        if getattr(self, "_probe_licensed_level", False):
            return False
        try:
            acts = list(self._adapter.discrete_actions() or [])
        except Exception:
            acts = []
        if not acts:
            return True                                    # pure-click: nothing to bootstrap -> license now
        return len(self.history) >= 6                      # played enough that "no controllable" is informative

    def _bootstrap_live(self, adapter, k=2):
        """Seed the live action->effect model with a SHORT recorded play burst (no resets) so compose can type
        the self from lived experience instead of stepping/drifting. Bounded to k per action; stops on done so
        it never plays into a terminal state. Records to history exactly like pursue/explore."""
        try:
            acts = list(adapter.discrete_actions() or [])
        except Exception:
            return
        self.phase = "bootstrap"
        for a in acts:
            for _ in range(k):
                before = _read(adapter)
                r = self._step(adapter, a, None)
                after = _read(adapter)
                self.history.append(dict(action=getattr(a, "name", a), clicked=None,
                                         before=before, after=after, won=bool(r.get("won")), phase="bootstrap"))
                if r.get("done"):
                    return

    # ---------------- composition layer (MATCH sub-objective) ----------------
    def _recent_frames(self, k=14):
        """The recent grid trajectory from causal history -- where the agent may have seen the key change."""
        if not self.history:
            return []
        h = self.history[-k:]
        frames = [np.asarray(h[0]["before"])]
        for e in h:
            frames.append(np.asarray(e["after"]))
        return frames

    def _self_color_of(self, grid):
        """Avatar body colour = the dominant NON-background colour among the proprioceptive self cells. Sampling
        the raw self component can return the background when the avatar leaves a background-coloured trail (its
        past cells have reverted), which mis-identifies the self and makes every wall look like a navigable object;
        excluding the global background recovers the true body colour."""
        sc = self.prop.self_component()
        cs = list(sc.cells) if (sc and getattr(sc, "cells", None)) else []
        if not cs:
            return None
        g = np.asarray(grid)
        bg = int(np.bincount(g.ravel()).argmax())               # global background = most common colour
        vals = np.asarray([g[r, c] for (r, c) in cs]).ravel()
        nonbg = vals[vals != bg]
        if len(nonbg) == 0:
            return int(np.bincount(vals).argmax())              # avatar genuinely is bg-coloured -> fall back
        return int(np.bincount(nonbg).argmax())

    def _avatar_track(self, before, after, prev, R):
        """Absolute avatar localisation by CONTINUITY: centroid of cells that changed this step AND lie within
        radius R of the previous avatar position. The avatar is the only local mover, so this tracks it cleanly
        even when it shares colour with a large static region; the radius excludes far-away autonomous elements
        (HUD/step-counter). Returns prev unchanged when the avatar didn't move (blocked) or only the HUD did."""
        try:
            b = np.asarray(before); a = np.asarray(after)
            if b.shape != a.shape:
                return prev
            p = np.argwhere(b != a)
            if len(p) == 0:
                return prev
            d = np.abs(p[:, 0] - prev[0]) + np.abs(p[:, 1] - prev[1])
            loc = p[d <= R]
            if len(loc) == 0:
                return prev
            return (float(loc[:, 0].mean()), float(loc[:, 1].mean()))
        except Exception:
            return prev

    def _avatar_track_expected(self, before, after, prev, exp, R):
        """Localise the avatar among MULTIPLE movers using its KNOWN move: the avatar should appear near the
        PREDICTED position prev+exp, so take the changed cells within R of that prediction rather than within R
        of prev. Other movers (HUD, autonomous elements) that aren't near where the avatar's action predicts it
        get excluded -- which the plain prev-centred centroid cannot do. Falls back to the prev-centred tracker
        when nothing changed near the prediction (e.g. the avatar was blocked)."""
        try:
            b = np.asarray(before); a = np.asarray(after)
            if b.shape != a.shape:
                return self._avatar_track(before, after, prev, R)
            p = np.argwhere(b != a)
            if len(p) == 0:
                return prev
            ex0 = prev[0] + (exp[0] if exp else 0.0)
            ex1 = prev[1] + (exp[1] if exp else 0.0)
            d = np.abs(p[:, 0] - ex0) + np.abs(p[:, 1] - ex1)
            loc = p[d <= R]
            if len(loc) == 0:
                return self._avatar_track(before, after, prev, R)   # nothing near prediction -> prev-centred
            return (float(loc[:, 0].mean()), float(loc[:, 1].mean()))
        except Exception:
            return self._avatar_track(before, after, prev, R)

    def _self_pos0(self):
        """Initial avatar position = centroid of the proprioceptive self cells."""
        sc = self.prop.self_component()
        cs = list(sc.cells) if (sc and getattr(sc, "cells", None)) else []
        if not cs:
            return None
        return (sum(r for r, _ in cs) / len(cs), sum(c for _, c in cs) / len(cs))

    def _locate_avatar(self, grid, color):
        """Avatar centroid in the CURRENT grid = the self-coloured cells. Lets exploration RESUME from where the
        avatar actually is, so we don't RESET (which wipes all progress, like Undo) merely to re-localise to the
        start. Returns None only when the self colour is absent (avatar genuinely lost)."""
        try:
            g = np.asarray(grid)
            ys, xs = np.where(g == color)
            if len(ys) == 0:
                return None
            return (float(ys.mean()), float(xs.mean()))
        except Exception:
            return None

    def _probe_action(self, adapter, a, pos0, settle_first=None):
        """Settled-delta probe of one action's displacement. settle_first is an optional list of actions applied
        first (to move the avatar off a wall so a start-blocked action can reveal its true direction)."""
        adapter.reset(); pos = pos0
        if settle_first:
            for sa in settle_first:
                b = _read(adapter); self._step(adapter, sa, None); af = _read(adapter)
                pos = self._avatar_track(b, af, pos, R=14)
        b0 = _read(adapter); self._step(adapter, a, None); a1 = _read(adapter)
        p1 = self._avatar_track(b0, a1, pos, R=14)             # settle to the avatar's true centre
        self._step(adapter, a, None); a2 = _read(adapter)
        p2 = self._avatar_track(a1, a2, p1, R=14)              # true per-step displacement
        return (p2[0] - p1[0], p2[1] - p1[1])

    def _self_action_directions(self, adapter):
        """Probe which discrete action TRANSLATES the avatar and in what direction (dr,dc), via the CONTINUITY
        tracker (correct-signed). Position-robust: an action blocked by a wall at the start (e.g. 'down' when the
        avatar starts against a bottom edge) is re-probed after displacing the avatar with a known mover, so the
        full action basis is recovered. The navigation primitive; the agent has no other goal-directed nav."""
        try:
            acts = list(adapter.discrete_actions() or [])
        except Exception:
            return {}
        g0 = _read(adapter); color = self._self_color_of(g0)
        if color is None:
            return {}
        self._self_color = color
        pos0 = self._self_pos0()
        if pos0 is None:
            return {}
        dmap = {}
        for a in acts:                                          # first pass: probe from start
            try:
                d = self._probe_action(adapter, a, pos0)
                if abs(d[0]) + abs(d[1]) > 0.5:
                    dmap[a] = d
            except Exception:
                continue
        movers = list(dmap.keys())
        for a in acts:                                          # second pass: unblock start-walled actions
            if a in dmap:
                continue
            for m in movers:
                try:
                    d = self._probe_action(adapter, a, pos0, settle_first=[m, m, m])
                    if abs(d[0]) + abs(d[1]) > 0.5:
                        dmap[a] = d; break
                except Exception:
                    continue
        try:
            adapter.reset()
        except Exception:
            pass
        return dmap

    def _pursue_match(self, adapter):
        """Single-rollout 'MATCH then reach': PHASE A navigates the self to candidate triggers to drive the
        property mismatch to 0 (greedy on the match measure, marking triggers that don't help), then PHASE B
        navigates to the template (lock). One episode -- a reset would wipe the match. Returns None (fall back
        to ordinary pursuit) if it cannot even build a navigation map."""
        meas = self._match["measure"]; tmpl_cent = self._match["roles"].get("template_centroid")
        dmap = self._self_action_directions(adapter)
        if not dmap:
            return None
        pos0 = self._self_pos0(); color = self._self_color
        if pos0 is None or color is None:
            return None
        avg_step = sum(abs(d[0]) + abs(d[1]) for d in dmap.values()) / max(1, len(dmap))
        step_r = max(4.0, 1.5 * avg_step); track_r = max(8.0, 2.2 * avg_step)
        self.ledger.mark_reset()
        try:
            adapter.reset()
        except Exception:
            return None
        budget = int(min(self.pursue_cap, max(60, self.coast.adaptive_budget())))
        won = False; reason = "match-unreached"; tried = set(); matched_at = None
        self_pos = list(pos0); blocked = set()
        bg = _matchab._bg(_read(adapter))
        lock_vec = self._match["roles"].get("template_vec")
        key_pos = self._match["roles"].get("mutable_centroid") or tuple(pos0)

        def locate_key(grid):
            objs = self._other_objects(grid, self_pos, color)
            if not objs:
                return None, None
            ko = min(objs, key=lambda o: abs(o["centroid"][0] - key_pos[0]) + abs(o["centroid"][1] - key_pos[1]))
            try:
                kv = _mp.object_property_vector(grid, list(ko["cells"]), bg)
            except Exception:
                kv = None
            return kv, ko

        def trigger_under_self(grid, kobj):
            """Non-self, non-key object the avatar is standing on (the cause candidate for a key change)."""
            for o in self._other_objects(grid, self_pos, color):
                if kobj is not None and o is kobj:
                    continue
                if abs(o["centroid"][0] - self_pos[0]) + abs(o["centroid"][1] - self_pos[1]) <= step_r:
                    return o
            return None

        for step in range(budget):
            before = _read(adapter); d0 = meas(before)
            key_vec_before, kobj = locate_key(before)
            if kobj is not None:
                key_pos = kobj["centroid"]
            if d0 > 0:                                   # PHASE A: reduce mismatch via triggers
                target = None
                plan = self._te_model.plan(key_vec_before, lock_vec) if (key_vec_before and lock_vec) else []
                if plan:                                 # MODEL-DRIVEN: regress to the trigger the plan calls for
                    want_sig = plan[0][0]
                    cands = [o for o in self._other_objects(before, self_pos, color)
                             if _te._sig(_mp.object_property_vector(before, list(o["cells"]), bg)) == want_sig]
                    if cands:
                        target = min(cands, key=lambda o: abs(o["centroid"][0] - self_pos[0])
                                     + abs(o["centroid"][1] - self_pos[1]))["centroid"]
                    elif want_sig in self._te_model.centroid:
                        target = self._te_model.centroid[want_sig]
                if target is None:                       # fall back: greedy nearest untried trigger (also LEARNS)
                    others = self._other_objects(before, self_pos, color)
                    untried = [o for o in others
                               if (round(o["centroid"][0]), round(o["centroid"][1])) not in tried]
                    pool = untried or others
                    if not pool:
                        break
                    target = min(pool, key=lambda o: abs(o["centroid"][0] - self_pos[0])
                                 + abs(o["centroid"][1] - self_pos[1]))["centroid"]
            else:                                        # PHASE B: matched -> head to the lock/terminal
                if matched_at is None:
                    matched_at = step
                target = tmpl_cent or tuple(self_pos)
            action = self._nav_action(self_pos, target, dmap, blocked)
            if action is None:                           # stuck against everything toward target
                tried.add((round(target[0]), round(target[1]))); blocked.clear(); continue
            t_under = trigger_under_self(before, kobj)   # trigger the avatar is on (cause candidate)
            self._decision = dict(
                engine="match-pursuit",
                phase=("A: drive key->lock via trigger" if d0 > 0 else "B: matched, reach lock/exit"),
                target=(round(target[0], 1), round(target[1], 1)),
                key=({"color": key_vec_before[0], "size": key_vec_before[2]} if key_vec_before else None),
                lock=({"color": lock_vec[0], "size": lock_vec[2]} if lock_vec else None),
                mismatch_dims=[("color", "shape", "size")[c] for c in (0, 1, 2)
                               if (key_vec_before and lock_vec and key_vec_before[c] != lock_vec[c])],
                model_plan=bool(self._te_model.plan(key_vec_before, lock_vec)) if (key_vec_before and lock_vec) else False,
                rationale=("navigating to a trigger to transform the key toward the lock" if d0 > 0
                           else "key already matches the lock; heading to the exit"))
            res = self._step(adapter, action, None); after = _read(adapter); won = bool(res.get("won"))
            self.history.append(dict(action=getattr(action, "name", action), clicked=None,
                                     before=before, after=after, won=won, phase=self.phase))
            for c in _val.committed(self.components + self.molecules):
                _val.check_prediction(c, self.history[-1])
            key_vec_after, _ = locate_key(after)         # LEARN the condition-effect if the key changed on a trigger
            if (t_under is not None and key_vec_before is not None and key_vec_after is not None
                    and tuple(key_vec_before) != tuple(key_vec_after)):
                self._te_model.observe(_te._sig(_mp.object_property_vector(before, list(t_under["cells"]), bg)),
                                       key_vec_before, key_vec_after, t_under["centroid"])
            prev = tuple(self_pos)
            self_pos = list(self._avatar_track(before, after, prev, track_r))
            if abs(self_pos[0] - prev[0]) + abs(self_pos[1] - prev[1]) < 0.5:
                blocked.add(action)                      # this action is walled here -> avoid it
            else:
                blocked.clear()
            if won:
                reason = "won"; break
            if res.get("done"):
                reason = "game-over"; break             # episode ended (GAME_OVER) -- not a win, stop the rollout
            if abs(self_pos[0] - target[0]) + abs(self_pos[1] - target[1]) <= step_r:
                tried.add((round(target[0]), round(target[1]))); blocked.clear()
            if d0 > 0 and meas(after) == 0:
                matched_at = step
        if won:
            reason = "won"
        elif matched_at is not None:
            reason = "matched-no-terminal"
        understanding = _val.is_understanding(self.components + self.molecules, self.history)
        try:                                             # Phase-1 spine: a FALSIFIED component verdict is a committed
            _pe = getattr(_ov, "_pe", None)              # prediction that broke -> localize it into the shared bus.
            if _pe is not None:                          # Guarded: can never affect the (reason-first) run's control flow.
                _mem = _ov._game_mem(adapter)
                for _c in _val.committed(self.components + self.molecules):
                    _v = _val.validate(_c, self.history, phase=getattr(self, "phase", "exploit"))
                    _pe.ingest_verdict(_mem, getattr(_c, "name", str(_c)), _v,
                                       emit=lambda s: _ov._emit(adapter, s))
        except Exception:
            pass
        return dict(success=won, validated=won, reason=reason, understanding=understanding,
                    engine="match_pursuit", matched=(matched_at is not None), history_len=len(self.history))

    def _other_objects(self, grid, self_pos, self_color):
        """Mask-objects excluding the avatar (the self-coloured blob nearest self_pos)."""
        bg = _matchab._bg(grid); objs = _matchab._segment_mask(grid, bg)
        if not objs:
            return []
        same = [o for o in objs if o["vec"][0] == self_color] or objs
        avatar = min(same, key=lambda o: abs(o["centroid"][0] - self_pos[0])
                     + abs(o["centroid"][1] - self_pos[1]))
        return [o for o in objs if o is not avatar]

    def _nav_action(self, self_pos, target, dmap, blocked):
        """Best probed action toward target, excluding actions known to be walled at this position."""
        want = (target[0] - self_pos[0], target[1] - self_pos[1])
        best, bs = None, -1e18
        for a, (dr, dc) in dmap.items():
            if a in blocked:
                continue
            s = dr * want[0] + dc * want[1]
            if s > bs:
                bs, best = s, a
        return best

    def _dmap_cached(self, adapter):
        # Primary: the reset-anchored probe (clean per-action displacement) when it can run. Fallback: the LIVE
        # self-model's direction map (action -> mean change-centroid displacement), learned from lived
        # transitions with NO resets. The fallback is what lets navigation work when the probe yields nothing --
        # e.g. resets are off, or a multi-mover/multi-colour frame defeats the probe's displacement measurement --
        # and it is robust to multi-colour sprites because the change-centroid tracks whatever MOVED. We keep the
        # probe primary so games where it already works (and the slm map would be noisier) are unaffected.
        if self._dmap is None:
            d = {}
            try:
                d = self._self_action_directions(adapter) or {}
            except Exception:
                d = {}
            if not d:
                slm = getattr(self, "_slm", None)
                if slm is not None:
                    try:
                        d = dict(slm.coherent_actions())
                    except Exception:
                        d = {}
            self._dmap = d
        return self._dmap or {}

    def _reachable_explored(self):
        """Has the avatar's reachable map been explored enough to stop deferring the relational objective?
        True when: no navigable (translate) avatar is in play (the gate doesn't apply); OR the directed explorer
        has covered the reachable map (frontier exhausted -> self._map_explored); OR a generous explore budget
        has been spent (so a game whose avatar we cannot yet segment -- no map can be built -- does not explore
        forever). While this is False, the agent keeps exploring rather than committing a target or giving up."""
        if (getattr(self, "_abd_report", None) or {}).get("modality") != "translate":
            return True                                      # gate only applies to a navigable avatar
        if getattr(self, "_map_explored", False):
            return True
        cap = max(100, int(0.4 * (getattr(self, "pursue_cap", 300) or 300)))
        used = (getattr(getattr(self, "_reset_policy", None), "total_actions", 0)
                - getattr(self, "_level_start_actions", 0))   # actions spent on THIS level so far
        return used >= cap

    def _least_visited_free(self, smap, visits, cur, min_visits=2):
        """The 'novel coordinate' target: the least-visited reachable FREE cell still under-explored (visited
        fewer than min_visits times), with FARTHEST as the tiebreak so the avatar is pulled OUT of a local
        cluster toward unexplored ground (this is what breaks an oscillation). Returns a lattice cell, or None
        when every reachable free cell has been visited enough -- i.e. the reachable area is genuinely covered,
        not merely discovered."""
        best = None; bestkey = None
        for c, st in smap.cell.items():
            if st != _smap_mod.FREE or c == cur:
                continue
            v = visits.get(c, 0)
            if v >= min_visits:
                continue
            dist = abs(c[0] - cur[0]) + abs(c[1] - cur[1])
            k = (v, -dist)                                   # least-visited first, then farthest
            if bestkey is None or k < bestkey:
                bestkey = k; best = c
        return best

    def _pursue_explore(self, adapter):
        """DIRECTED exploration: navigate the self to visit distinct non-self objects (candidate triggers) to
        SURFACE the causal evidence abduction needs (action effects + key changes) -- blind action-cycling
        oscillates and never reaches a trigger on a large grid. Reuses the navigation primitive. Returns a
        result dict, or None to fall back to the blind soundness driver when no nav map can be built."""
        dmap = self._dmap_cached(adapter)
        if not dmap:
            return None
        slm = getattr(self, "_slm", None)
        slm_pos = None
        if slm is not None and getattr(slm, "locus", None) is not None:
            slm_pos = (float(slm.locus[0]), float(slm.locus[1]))   # live motion locus (multi-colour robust)
        pos0 = self._self_pos0() or slm_pos                        # proprioceptive self centre, else live locus
        color = self._self_color or self._self_color_of(_read(adapter))
        if pos0 is None:
            return None                                            # genuinely no avatar position -> cannot nav
        avg_step = sum(abs(d[0]) + abs(d[1]) for d in dmap.values()) / max(1, len(dmap))
        step_r = max(4.0, 1.5 * avg_step); track_r = max(8.0, 2.2 * avg_step)
        # RESET is a last resort -- it destroys all progress (the same failure mode as Undo) and must NOT be
        # spammed while the agent is merely exploring and not stuck. Resume from where the avatar IS: the
        # self-coloured blob if we have a clean colour, else the live motion locus (robust to multi-colour
        # sprites). Only RESET when the avatar cannot be located at all or the deduction space is exhausted.
        cur = self._locate_avatar(_read(adapter), color) if color is not None else None
        if cur is None:
            cur = slm_pos                                          # colour localisation unavailable -> motion locus
        try:
            stuck = (self.ledger.verdict(won=False).get("status") == "deduction_exhausted")
        except Exception:
            stuck = False
        if cur is None or stuck:
            self.ledger.mark_reset()
            try:
                adapter.reset()
            except Exception:
                return None
            cur = self._self_pos0() or slm_pos or pos0
        budget = int(min(self.pursue_cap, max(60, self.coast.adaptive_budget())))
        won = False; reason = "reward-unreached"; visited = set(); disc_was_positive = False
        self_pos = list(cur); blocked = set()
        key = lambda cen: (round(cen[0]), round(cen[1]))
        avg = max(1.0, avg_step)
        latq = lambda p: (int(round(p[0] / avg)), int(round(p[1] / avg)))   # avatar position -> movement lattice
        smap = _smap_mod.SpatialMap(ttl=max(40, budget // 3))               # persistent traversability map
        self._smap = smap
        last_dir = None
        visits = _collections.Counter()                                     # per-cell visit counts (novelty)
        recent = _collections.deque(maxlen=14)                              # recent lattice cells (oscillation)
        for _ in range(budget):
            before = _read(adapter)
            here = latq(self_pos)
            smap.visit(here); smap.decay()
            visits[here] += 1; recent.append(here)
            oscillating = (len(recent) >= 10 and len(set(recent)) <= 3)     # bouncing among <=3 cells = stuck
            mode = None; target = None; action = None
            others = self._other_objects(before, self_pos, color)
            unvisited = [o for o in others if key(o["centroid"]) not in visited
                         and smap.status(latq(o["centroid"])) != _smap_mod.BLOCKED]  # skip learned walls
            # GLOBAL ANTI-OSCILLATION (runs BEFORE object-chasing, which is where the bouncing happens): if the
            # avatar is cycling among a few cells, whatever it is chasing is unreachable from here -- so stop
            # chasing nearby objects (mark them visited, which also forces the transition OUT of object mode into
            # map coverage), drop the stuck-action memory, and head to the FARTHEST least-visited reachable cell.
            if oscillating:
                for o in others:
                    if abs(o["centroid"][0] - self_pos[0]) + abs(o["centroid"][1] - self_pos[1]) <= 2 * track_r:
                        visited.add(key(o["centroid"]))
                blocked.clear()
                nb = self._least_visited_free(smap, visits, here)
                if nb is not None:
                    target = (nb[0] * avg, nb[1] * avg)
                    action = self._nav_action(self_pos, target, dmap, blocked); mode = "novel-osc"
                unvisited = [o for o in others if key(o["centroid"]) not in visited
                             and smap.status(latq(o["centroid"])) != _smap_mod.BLOCKED]
            if action is None and unvisited:                 # PRIMARY: visit distinct objects (goals / triggers)
                target = min(unvisited, key=lambda o: abs(o["centroid"][0] - self_pos[0])
                             + abs(o["centroid"][1] - self_pos[1]))["centroid"]
                action = self._nav_action(self_pos, target, dmap, blocked)
                mode = "object"
                if action is None:
                    visited.add(key(target)); blocked.clear(); continue
            if action is None:                               # objects covered -> COVER THE REST OF THE MAP
                fdir = smap.frontier_step(latq(self_pos), prefer=last_dir)
                if fdir is not None and fdir != (0, 0):
                    target = (self_pos[0] + fdir[0] * avg, self_pos[1] + fdir[1] * avg)
                    action = self._nav_action(self_pos, target, dmap, blocked); mode = "frontier"
                if action is None:                           # no UNKNOWN frontier -> SEEK A NOVEL (least-visited)
                    novel = self._least_visited_free(smap, visits, here)     # reachable FREE cell, farthest tiebreak
                    if novel is not None:
                        target = (novel[0] * avg, novel[1] * avg)
                        action = self._nav_action(self_pos, target, dmap, blocked); mode = "novel"
                if action is None:                           # map + objects covered AND nothing novel left
                    if others:
                        visited.clear()
                        target = min(others, key=lambda o: abs(o["centroid"][0] - self_pos[0])
                                     + abs(o["centroid"][1] - self_pos[1]))["centroid"]
                        action = self._nav_action(self_pos, target, dmap, blocked); mode = "revisit"
                    if action is None:
                        action = self._explore_choose(adapter) or list(dmap.keys())[self._act_cycle % len(dmap)]
                        self._act_cycle += 1; target = None; mode = "probe"
            if mode in ("revisit", "probe"):
                self._map_explored = True                    # objects + frontier covered -> reachable map mapped
            cov = smap.coverage()
            self._decision = dict(
                engine="directed-explore", mode=mode,
                target=((round(target[0], 1), round(target[1], 1)) if target is not None else None),
                coverage="%d free / %d walls / %d known" % (cov["free"], cov["blocked"], cov["known"]),
                rationale=("navigating to a distinct object to surface what stepping on it triggers"
                           if mode == "object" else
                           "objects covered -> heading to the nearest UNEXPLORED region via a learned "
                           "traversability map (free vs wall from collisions); stale walls expire so triggers / "
                           "moving objects get re-checked" if mode == "frontier" else
                           "no unknown frontier -> heading to the least-visited reachable cell to finish "
                           "covering the ground" if mode == "novel" else
                           "oscillating among a few cells -> jumping to the farthest least-visited cell to "
                           "break the cycle" if mode == "novel-osc" else
                           "map + objects covered -> revisiting" if mode == "revisit" else
                           "no reachable target -> probing dynamics"))
            res = self._step(adapter, action, None); after = _read(adapter); won = bool(res.get("won"))
            self.history.append(dict(action=getattr(action, "name", action), clicked=None,
                                     before=before, after=after, won=won, phase=self.phase))
            for c in _val.committed(self.components + self.molecules):
                _val.check_prediction(c, self.history[-1])
            prev = tuple(self_pos)
            exp = dmap.get(action, (0.0, 0.0))                       # known displacement of the chosen move
            self_pos = list(self._avatar_track_expected(before, after, prev, exp, track_r))
            moved = abs(self_pos[0] - prev[0]) + abs(self_pos[1] - prev[1]) >= 0.5
            if action in dmap:
                smap.record_neighbour(latq(prev), dmap[action], moved)   # collision -> wall; moved -> free
            if moved:
                last_dir = (int(np.sign(self_pos[0] - prev[0])), int(np.sign(self_pos[1] - prev[1])))
                blocked.clear()
            else:
                blocked.add(action)
            if target is not None and abs(self_pos[0] - target[0]) + abs(self_pos[1] - target[1]) <= step_r:
                visited.add(key(target)); blocked.clear()
            try:                                          # REACTIVE dynamism: pixels that changed AWAY from the
                bb = np.asarray(before); aa = np.asarray(after)   # avatar's own move mean the space changed there,
                if bb.shape == aa.shape:                          # so any wall belief at those cells is stale
                    ch = np.argwhere(bb != aa)
                    far = set((int(round(r / avg)), int(round(c / avg))) for (r, c) in ch
                              if abs(r - prev[0]) + abs(c - prev[1]) > track_r)
                    if far:
                        smap.invalidate(far)
            except Exception:
                pass
            if won:
                reason = "won"; break
            if res.get("done"):
                reason = "game-over"; break             # episode ended (GAME_OVER) -- not a win, stop the rollout
            if mode in ("object", "revisit"):           # the black-box trap only applies while PURSUING a target
                try:
                    if self._disc is not None:
                        m = float(self._disc.measure(after))
                        if m > 0:
                            disc_was_positive = True              # a real predicate is in play
                        elif disc_was_positive and m == 0.0:
                            # predicate descriptively satisfied but UNREWARDED: this target taught us what it
                            # could, so mark it done and KEEP EXPLORING the map (gather more evidence / coverage)
                            # rather than aborting the rollout. The reason is still recorded -> the kernel will
                            # recompose afterward; we just refuse to sit idle in the meantime.
                            if target is not None:
                                visited.add(key(target))
                            disc_was_positive = False
                            reason = "predicate-satisfied-no-reward"
                except Exception:
                    pass
        understanding = _val.is_understanding(self.components + self.molecules, self.history)
        return dict(success=won, validated=won, reason=reason, understanding=understanding,
                    engine="directed_explore", history_len=len(self.history))

    def _molecules_from(self, rpt, disc, adapter):
        """Lift checkable predictions onto abduced relations -> refutable molecules. Uncommitted (no
        checkable prediction) ones are dropped, exactly as percepts are."""
        if not rpt or not rpt.get("hypotheses"):
            return []
        try:
            grid0 = _read(adapter)
        except Exception:
            grid0 = None
        mols = []
        for hyp in rpt["hypotheses"]:
            try:
                m = _mp.molecule_from_hypothesis(hyp, disc=disc, grid0=grid0)
            except Exception:
                continue
            if m.prediction is not None:
                mols.append(m)
        return mols

    def pursue_fn(self, objective):
        adapter = self._adapter
        # Pursuing a committed, justified objective IS exploitation: we are acting on a believed rule, so a
        # prediction violated here is LOAD-BEARING (a real refutation), not the expected noise of probing.
        # This is what turns the refutation engine on -- without it every committed-pursuit transition is
        # logged as 'explore' and validate() can only ever return 'provisional' (the ledger never moves).
        self.phase = "exploit"
        ctrl = self.prop.controllable_for_mover()
        # EXPLORE-FIRST objective: pursuit == mapping the reachable space (directed frontier explorer; falls back
        # to the bounded sweep if no nav map can be built). Skip the match/command branches entirely.
        if isinstance(objective, dict) and objective.get("explore"):
            try:
                r = self._pursue_explore(adapter)
                if r is not None:
                    return r
            except Exception:
                pass
        # COMPOSITION LAYER: if a MATCH sub-objective was abduced, pursue 'match THEN reach' in one rollout
        # before falling back to ordinary pursuit. Gated entirely on self._match -> no effect on other games.
        if self._match is not None and not self._command_game:
            try:
                r = self._pursue_match(adapter)
                if r is not None:
                    return r
            except Exception:
                pass
        # COMMAND game: pursue by SEARCHING command SEQUENCES toward a target world-config (ui_planner),
        # not by self-target navigation. The true target abduction is the documented open piece, so the
        # target measure is best-effort (the compiled discrepancy if any); a real win is still the game's.
        if self._command_game and self._commands:
            try:
                target = self._disc.measure if self._disc is not None else (lambda g: 1.0)
                self.ledger.mark_reset()
                plan = _uiplan.plan_commands(adapter, self._commands, target, budget=120, max_depth=6)
                adapter.reset()
                won = False
                for cmd in plan.get("sequence", []):
                    before = _read(adapter)
                    if cmd[0] == "click":
                        res = self._step(adapter, ("click", None), (cmd[1], cmd[2])); clicked = (cmd[1], cmd[2])
                    else:
                        res = self._step(adapter, cmd[0], None); clicked = None
                    after = _read(adapter); won = bool(res.get("won"))
                    self.history.append(dict(action=(None if clicked else cmd[0]), clicked=clicked,
                                             before=before, after=after, won=won, phase=self.phase))
                    for c in _val.committed(self.components + self.molecules):
                        _val.check_prediction(c, self.history[-1])
                    if won:
                        break
                reason = "won" if won else ("command-plan-solved-no-reward" if plan.get("solved")
                                            else "reward-unreached")
                understanding = _val.is_understanding(self.components + self.molecules, self.history)
                return dict(success=won, validated=won, reason=reason, understanding=understanding,
                            engine="ui_planner", plan_len=len(plan.get("sequence", [])),
                            history_len=len(self.history))
            except Exception:
                pass                                          # fall through to general pursuit
        # DIRECTED exploration (translate games): visit objects to surface causal evidence, instead of blind
        # action-cycling that oscillates near the start. Falls back to the soundness driver if no nav map.
        try:
            r = self._pursue_explore(adapter)
            if r is not None:
                return r
        except Exception:
            pass
        try:
            budget = int(min(self.pursue_cap, max(20, self.coast.adaptive_budget())))
        except Exception:
            budget = min(self.pursue_cap, 200)
        self.ledger.mark_reset()
        won = False
        reason = "reward-unreached"
        for _ in range(budget):
            before = _read(adapter)
            action, clicked = self._pick(adapter, before, ctrl)
            self._decision = dict(
                engine=("command/ui-plan" if self._command_game else "soundness-driver (fallback)"),
                action_kind=("click" if clicked is not None else "discrete"),
                rationale=("executing the planned command sequence" if self._command_game
                           else "no committed nav/match plan; cycling actions to find a world-changing effect"))
            res = self._step(adapter, action, clicked)
            after = _read(adapter)
            won = bool(res.get("won"))
            entry = dict(action=(None if clicked is not None else getattr(action, "name", action)),
                         clicked=clicked, before=before, after=after, won=won, phase=self.phase)
            self.history.append(entry)
            for c in _val.committed(self.components + self.molecules):          # LIVE validation, every step
                _val.check_prediction(c, entry)
            if won:                                            # a REAL win = the game's reward/done, only
                reason = "won"
                break
            try:
                if self._disc is not None and float(self._disc.measure(after)) == 0.0:
                    # internal model says the predicate is met, but the game gave NO reward -> the binding
                    # is wrong (descriptive alignment != reward). Recompose, do NOT declare victory. This is
                    # the black-box trap refused from inside.
                    reason = "predicate-satisfied-no-reward"
                    break
            except Exception:
                pass
        verdicts = {}
        for c in self.components:
            try:
                verdicts[getattr(c, "modality", None) or c.ctype] = _val.validate(c, self.history, self.phase)
            except Exception:
                pass
        understanding = _val.is_understanding(self.components + self.molecules, self.history)
        return dict(success=won, validated=won, reason=reason, understanding=understanding,
                    verdicts=verdicts, history_len=len(self.history))

    def _explore_choose(self, adapter):
        """Discrete-action exploration as a BOUNDED, COVERAGE-FIRST sweep -- distilled from the old
        DiscoveryEngine.MOVEMENT_TEST (try each action a few times, note its effect, then move on). The previous
        rule ("persist one direction while it keeps changing the world, turn only on a wall/no-op") fixates
        catastrophically on games where movement NEVER hits a wall and never reverts: every step changes the
        world, so the turn-trigger never fires and one action gets ridden indefinitely (measured: 105 in a row).
        The fix: (a) SWEEP -- try each action at least MIN_SWEEP times before committing to any (breadth first);
        (b) CAP -- persist a productive direction only up to CAP consecutive steps, then rotate REGARDLESS of
        whether it was blocked; (c) keep the wall-turn and revert/undo-ban from before. The next direction is
        chosen by COVERAGE (least-tried, then least-walled), so no action can monopolise the budget. Prior-free
        and OOD-safe: 'wall'/'undo' are read from the observed grid effect, not action names."""
        try:
            acts = list(adapter.discrete_actions() or [])
        except Exception:
            acts = []
        if not acts:
            return None
        if not hasattr(self, "_exp"):
            self._exp = dict(banned=set(), noop={}, revert={}, dir=None, last=None, before=None, hist=[],
                             tried={}, run=0)
        E = self._exp
        E.setdefault("tried", {}); E.setdefault("run", 0)
        CAP = 16            # max consecutive steps in one direction before a forced rotation (anti-fixation)
        MIN_SWEEP = 2       # try each action at least this many times before persisting one (breadth first)
        cur = _read(adapter)
        # 1) classify the PREVIOUS chosen action's effect from the grid we observe now
        if E["last"] is not None and E["before"] is not None and getattr(E["before"], "shape", None) == cur.shape:
            if np.array_equal(E["before"], cur):                       # nothing changed -> wall / no-op
                E["noop"][E["last"]] = E["noop"].get(E["last"], 0) + 1
                E["revert"][E["last"]] = 0
                if E["dir"] == E["last"]:
                    E["dir"] = None                                    # hit a wall -> turn next
            else:
                reverted = any(g is not None and getattr(g, "shape", None) == cur.shape and np.array_equal(g, cur)
                               for g in E["hist"][-3:-1])              # came back to a recent prior state
                if reverted:
                    E["revert"][E["last"]] = E["revert"].get(E["last"], 0) + 1
                    if E["revert"][E["last"]] >= 2:                    # consistently reverts -> it's an Undo; drop it
                        E["banned"].add(E["last"])
                    E["dir"] = None
                else:
                    E["noop"][E["last"]] = 0
                    E["revert"][E["last"]] = 0
        # 2) candidates exclude undo-type actions (fall back to all if everything got banned)
        cand = [a for a in acts if a not in E["banned"]] or acts
        # 3) choose: SWEEP each action MIN_SWEEP times first; then persist a productive direction but only up to
        #    CAP consecutive steps; on a wall / undo / cap, ROTATE to the least-tried (then least-walled) action.
        swept = all(E["tried"].get(x, 0) >= MIN_SWEEP for x in cand)
        capped = (E["dir"] is not None and E["run"] >= CAP)
        if (not swept) or capped or E["dir"] is None or E["dir"] not in cand:
            a = min(cand, key=lambda x: (E["tried"].get(x, 0), E["noop"].get(x, 0)))
        else:
            a = E["dir"]                                               # persist (productive, still under the cap)
        # 4) bookkeeping: consecutive-run length, per-action try count, effect-classification memory
        E["run"] = (E["run"] + 1) if a == E["dir"] else 1
        E["dir"] = a
        E["tried"][a] = E["tried"].get(a, 0) + 1
        E["last"] = a; E["before"] = cur
        E["hist"].append(cur); E["hist"] = E["hist"][-4:]
        return a

    def _pick(self, adapter, grid, ctrl):
        """Action selection toward the objective: click an active (objective-driving) cell on click games;
        otherwise cycle the discrete actions. Deliberately simple -- this is a soundness driver."""
        try:
            pointer = adapter.pointer_actions()
        except Exception:
            pointer = []
        if pointer and self._disc is not None:
            try:
                active = list(self._disc.active(grid))
                if active:
                    r, c = active[0]
                    return ("click", (int(r), int(c)))
            except Exception:
                pass
        a = self._explore_choose(adapter)
        if a is not None:
            return (a, None)
        # pure click game with no disc: click a non-background cell to generate causal evidence
        if pointer:
            nz = np.argwhere(grid != int(np.bincount(grid.ravel()).argmax()))
            if len(nz):
                r, c = nz[0]
                return ("click", (int(r), int(c)))
        return (None, None)

    def _step(self, adapter, action, clicked):
        try:
            if clicked is not None:
                g, rew, done, info = adapter.step_at("click", clicked[0], clicked[1])
            elif action is not None:
                g, rew, done, info = adapter.step(action)
            else:
                return dict(won=False, rew=0, done=False)
            return dict(won=((float(rew) > 0.0) or ((info or {}).get("state") == "WIN")),
                        rew=rew, done=bool(done), state=(info or {}).get("state"))
        except Exception:
            return dict(won=False, rew=0, done=False)

    # ---------------- explore ----------------
    def explore_fn(self, objective):
        adapter = self._adapter
        self.phase = "explore"          # probing without a commitment: violations are expected, not refutations
        # CONTIGUOUS, map-driven exploration. Whether the objective is still UNKNOWN (explore to DISCOVER what is
        # in the space and surface the causal evidence a justifiable objective needs) or committed-but-unreached
        # (explore to NAVIGATE the obstacle), the activity is the same: cover the map, learn walls, visit objects
        # to see what they do. Run the directed-explore loop when the self is a localizable mover; fall back to
        # the one-shot persist-until-wall chooser only when there is no navigation map (e.g. pure click games).
        if self._dmap_cached(adapter):
            n0 = len(self.history)
            try:
                self._pursue_explore(adapter)
            except Exception:
                pass
            return len(self.history) > n0          # "moved" iff the exploration rollout actually took steps
        before = _read(adapter)
        a = self._explore_choose(adapter)
        if a is None:
            return False
        self._decision = {"engine": "explore (directed)",
                          "rationale": "persist a direction until it stops changing the world, then turn; "
                                       "Undo-type actions that revert progress are excluded so they don't burn "
                                       "the budget / RHAE -- no blind round-robin",
                          "action": getattr(a, "name", str(a))}
        self._step(adapter, a, None)
        return not np.array_equal(before, _read(adapter))

    # ---------------- driver (DIRECT soundness smoke test; NOT the game gate) ----------------
    def _read_level(self, adapter):
        v = getattr(adapter, "_lvl0", None)
        if isinstance(v, int):
            return v
        v = getattr(getattr(adapter, "_obs", None), "levels_completed", None)
        return int(v) if isinstance(v, int) else None

    def _install_reset_gate(self, adapter):
        """Make `adapter.reset()` the single licensed chokepoint for a level RESET (recovered v1/v2 doctrine).
        Every reset must be licensed by the ResetPolicy (game-start, or a fired stuck/oscillation/near-budget
        guard, capped per level); unlicensed resets -- the probe reflexes -- are DENIED and return the current
        frame WITHOUT resetting. `step()` is wrapped only to feed the policy progress/frame-change/budget. Can be
        disabled via ARC3_RESET_GATE=0 for A/B measurement."""
        import os
        if os.environ.get("ARC3_RESET_GATE", "1") == "0":
            self._live_mode = False
            return
        if getattr(adapter, "_ouro_gated", False):
            return
        self._live_mode = True                              # hybrid-C: characterize live by default
        # RESET DISABLED (for now, per direction): only the unavoidable game-START reset is allowed; every
        # other reset -- probes, stuck-recovery, licensed characterization -- is DENIED. Pure no-reset play.
        self._resets_disabled = os.environ.get("ARC3_RESET_DISABLE", "1") not in ("0", "")
        if _self_model is not None:
            try:
                self._slm = _self_model.SelfLocusModel()    # brain-owned live action->effect model
            except Exception:
                self._slm = None
        self._reset_license_active = None
        rp = self._reset_policy = ResetPolicy(budget=getattr(self, "pursue_cap", 400) or 400)
        self._reset_denied = 0
        self._reset_granted = 0
        self._reset_reasons = _collections.Counter()
        _oreset = adapter.reset
        _ostep = adapter.step
        prev = {"g": None}

        def gated_reset(reason=None):
            lic = reason or getattr(self, "_reset_license_active", None)
            if getattr(self, "_resets_disabled", False):
                # only the unavoidable game-START is allowed; everything else is denied (no-reset operation)
                if not rp.started:
                    rp.started = True
                    self._reset_granted += 1
                    self._reset_reasons["game-start"] += 1
                    prev["g"] = None
                    return _oreset()
                self._reset_denied += 1
                return _read(adapter)
            if lic and str(lic).startswith("characterization-probe"):
                # a LICENSED reset-anchored probe -- a deliberate, capped-per-level characterization decision
                self._reset_granted += 1
                self._reset_reasons[lic] += 1
                prev["g"] = None
                return _oreset()
            r = rp.license_reset(deliberate_reason=lic)
            if r is None:
                self._reset_denied += 1
                return _read(adapter)                       # DENY: no licensed reason -> current frame, no reset
            rp.commit(r)
            self._reset_granted += 1
            self._reset_reasons[r] += 1
            prev["g"] = None
            return _oreset()

        def observed_step(a):
            out = _ostep(a)
            try:
                g, rew, done, info = out
                changed = True
                pg = prev["g"]
                if pg is not None and getattr(pg, "shape", None) == getattr(g, "shape", None):
                    changed = bool(np.any(pg != g))
                    slm = getattr(self, "_slm", None)        # LIVE characterization: learn action->effect free
                    if slm is not None and not isinstance(a, tuple):
                        try:
                            slm.update(pg, a, g)
                        except Exception:
                            pass
                prev["g"] = g
                rp.observe(progressed=bool(rew and rew > 0), frame_changed=changed)
            except Exception:
                rp.observe(progressed=False)
            return out

        adapter.reset = gated_reset
        adapter.step = observed_step
        adapter._ouro_gated = True

    def run(self, adapter, max_steps=600):
        # max_steps is the GENEROUS hard ceiling, not the operating point. Within it, coast.adaptive_budget()
        # drives the real budget: ~800 (base 400 x skepticism 2) for full exploration before any win, then it
        # tightens toward the steps-to-win trend once a level is understood (explore wide, then optimize down).
        # Online MEASUREMENT runs pass a smaller max_steps deliberately, to finish inside the wall-clock.
        self._adapter = adapter
        self.pursue_cap = max_steps
        self._install_reset_gate(adapter)                   # RESET becomes a guarded decision, not a reflex
        if getattr(self, "_live_mode", False):
            try:
                adapter.reset()                             # the one allowed game-START reset (enters the game)
            except Exception:
                pass
        if getattr(self, "_live_mode", False) and not self.history:
            self._bootstrap_live(adapter)                   # seed the live action->effect model w/ recorded play
        # CROSS-LEVEL RE-LICENSING: on a genuine level advance the ledger starts a fresh episode --
        # refuted clears (re-testable under the new mechanic), confirmed carries as established.
        lvl = self._read_level(adapter)
        if lvl is not None:
            if self._last_level is not None and lvl > self._last_level:
                self.ledger.new_episode(level=lvl)
                self._map_explored = False                              # a new level = a fresh reachable map
                self._level_start_actions = self._reset_policy.total_actions
            self._last_level = lvl
        k = _kernel_mod.Kernel(self.compose_fn, self.pursue_fn, self.explore_fn)
        outcome, obj, trace = k.run_level(adapter)
        # SUSTAINED PLAY (resets off), ADAPTIVE-BY-PERFORMANCE: a single run_level can give up with most of the
        # budget unspent. Don't abandon the episode and don't stop at an arbitrary count -- keep playing from the
        # CURRENT state (no reset), re-composing from the live evidence that grows as we act. Continue WHILE the
        # agent is still learning (new ledger verdicts / components / score) up to the generous ceiling; give up
        # only when the deduction space is genuinely exhausted (EARNED) or progress has stalled for a long window
        # (no new learning -> spending more actions won't help). This is what lets a hard level take hundreds of
        # actions to understand, then coast down.
        if getattr(self, "_live_mode", False):
            ceiling = max(int(max_steps), 1)
            def _progress_sig():
                try:
                    led = len(self.ledger.refuted) + len(self.ledger.confirmed)
                except Exception:
                    led = 0
                wins = sum(1 for e in self.history if e.get("won"))
                return (len(self.components), led, wins)
            stall_window = max(140, int(0.30 * ceiling))    # generous no-progress window before earned give-up
            guard = 0
            stalled = 0
            last_sig = _progress_sig()
            while (outcome != _kernel_mod.Outcome.SUCCESS
                   and not any(e.get("won") for e in self.history)
                   and getattr(getattr(self, "_reset_policy", None), "total_actions", 0) < ceiling
                   and guard < 400):
                before_n = self._reset_policy.total_actions
                outcome, obj, trace = k.run_level(adapter)
                guard += 1
                if getattr(adapter, "_api_failed", False):
                    break                                   # live session died (NOT_STARTED w/ resets off): stop
                try:
                    if self.ledger.verdict(won=False).get("status") == "deduction_exhausted":
                        break                               # EARNED give-up: licensed space ruled out
                except Exception:
                    pass
                advanced = self._reset_policy.total_actions - before_n
                if advanced <= 0:
                    break                                   # run_level took no actions -> nothing to gain
                if not self._reachable_explored():
                    continue                                # EXPLORE-FIRST: reachable map still has frontier --
                    #                                         keep exploring; do NOT stall-give-up yet
                sig = _progress_sig()
                if sig == last_sig:
                    stalled += advanced
                    if stalled >= stall_window:
                        break                               # adaptive give-up: budget left but no new learning
                else:
                    stalled = 0
                    last_sig = sig
        # ACTIVE phase: if passive recognition found no delayed self but there ARE action-invariant
        # (autonomous) components, actively probe -- inject distinctive pings to force the rule out (11.336).
        if not self.recognized_selves and any(getattr(c, "ctype", None) == "autonomous"
                                              for c in self.components):
            try:
                self.active_recognize(adapter)
            except Exception:
                pass
        won_any = any(e.get("won") for e in self.history)
        led_verdict = self.ledger.verdict(won=won_any)
        if outcome in (_kernel_mod.Outcome.OBJECTIVE_INVALID, _kernel_mod.Outcome.PURSUIT_FAILED):
            if led_verdict["status"] == "deduction_exhausted":
                outcome = _kernel_mod.Outcome.DEDUCTION_EXHAUSTED   # earned give-up: space ruled out
            elif led_verdict["status"] == "inert":
                outcome = _kernel_mod.Outcome.INERT                 # earned give-up: committed but inert
        try:
            eq = self.pm.explanation_quality(self.components)
        except Exception:
            eq = None
        return dict(
            outcome=outcome,
            # GENUINE commitment, not just "compose returned a dict": the kernel returns a non-None obj even
            # when it rejects it for lacking justification (unexplainable=uncommitted), so keying off
            # `obj is not None` reports True on an objective the kernel treated as uncommitted -- which
            # defeats any consumer (e.g. the stall backstop) that reads this flag. A justified objective is
            # the commitment the action flows from.
            objective_committed=(obj is not None and bool(obj.get("justification"))),
            history_len=len(self.history),
            understanding=_val.is_understanding(self.components + self.molecules, self.history),
            explanation_quality=eq,
            n_components=len(self.components),
            recognized_selves=[r["description"] for r in self.recognized_selves],
            active_recognition=self.active_recognition,
            command_game=self._command_game, n_commands=len(self._commands),
            temporal=(self.temporal.get("modality") if self.temporal else None),
            proprioception=self.prop.explain(),
            persistent=self.pm.explain(),
            ledger=led_verdict,
            ledger_explain=self.ledger.explain(),
        )


# ==================================================================================================
# REASONING TRACE -- compile the brain's cognitive state into a per-action dict for replays/proctors.
# Used by reason_first_agent (scored path) and online_harness (dev). grid is optional; when supplied,
# the live MATCH mismatch distance is included.
# ==================================================================================================
def _short(x, n=90):
    try:
        s = str(x)
    except Exception:
        return None
    return s if len(s) <= n else s[:n] + "\u2026"


def reasoning_snapshot(oi, action, grid=None):
    """What the brain is trying to do and why, the hypotheses (molecule grammar) in play, what it has ruled
    out, the key/lock it is matching, the causal effects it has learned, and the rationale for THIS action."""
    if isinstance(action, tuple):
        name = f"{action[0]}({action[1]},{action[2]})" if len(action) >= 3 else str(action[0])
    else:
        name = getattr(action, "name", str(action))
    r = {"action": name, "phase": getattr(oi, "phase", None)}
    try:
        obj = oi.objective
        if obj:
            just = obj.get("justification")
            if isinstance(just, str):
                just = [just]
            r["objective"] = {"spec": _short(obj.get("spec"), 180),
                              "why": [_short(j, 80) for j in (just or [])][:3],
                              "command_game": obj.get("command_game")}
            sd = obj.get("self")
            if sd:
                r["self_model"] = {"modality": sd.get("modality"), "why": _short(sd.get("justification"), 80)}
    except Exception:
        pass
    try:
        committed = [m for m in (oi.molecules or []) if getattr(m, "prediction", None) is not None]
        r["grammar"] = [f"{m.identity} [{(m.prediction or {}).get('kind', '?')}]" for m in committed][:6]
    except Exception:
        pass
    try:
        v = oi.ledger.verdict()
        led = {k: v.get(k) for k in ("status", "licensed", "refuted", "confirmed", "live") if k in v}
        if led.get("status") == "objective_invalid":
            led["status"] = "objective_unknown"   # ledger's "invalid" only ever means "never licensed anything yet"
        r["ledger"] = led
    except Exception:
        pass
    try:
        if oi._match is not None:
            roles = oi._match.get("roles", {}); tv = roles.get("template_vec"); m = {"armed": True}
            if tv is not None:
                m["lock"] = {"color": tv[0], "size": tv[2]}
            if grid is not None:
                try:
                    m["mismatch_distance"] = float(oi._match["measure"](grid))
                except Exception:
                    pass
            r["match"] = m
    except Exception:
        pass
    try:
        te = oi._te_model
        if te.n_events > 0:
            eff = {}
            for tsig in te.known_triggers()[:5]:
                comps = te.effect_of(tsig)
                desc = {("color", "shape", "size")[c]: f"{e[0]}->{_short(e[1], 24)}"
                        for c, e in comps.items() if e is not None}
                if desc:
                    eff[f"trigger@color{tsig[0]}"] = desc
            if eff:
                r["trigger_effects"] = eff
            r["te_events"] = te.n_events
    except Exception:
        pass
    try:
        sm = getattr(oi, "_smap", None)
        if sm is not None:
            cov = sm.coverage()
            if cov["known"] > 0:
                r["spatial"] = {"free": cov["free"], "walls": cov["blocked"], "known": cov["known"]}
    except Exception:
        pass
    try:
        if getattr(oi, "_decision", None):
            r["decision"] = oi._decision
    except Exception:
        pass
    if "objective" not in r:
        ph = r.get("phase")
        r["note"] = ("exploring to surface a world-changing effect -- no objective committed yet "
                     "(status objective_unknown)" if ph == "explore"
                     else "probing perception to type the self and license candidate molecules -- no objective yet"
                     if ph in ("compose", "probe", None)
                     else "no objective committed yet")
    return r
