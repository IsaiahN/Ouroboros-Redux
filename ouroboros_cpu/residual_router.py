"""
RESIDUAL ROUTER  —  the wire between "my grammar failed to explain that" and "aim a new primitive at it".

WHY THIS FILE EXISTS
--------------------
The evolvability engine (mint / co-opt / gap-report) lived behind `validate()` PASS 4. The avatar regime never calls
`validate()` -- it goes AvatarRegime.solve -> _avatar_solve -> return -- so on every game that regime plays, which is
the game, the engine was CONSTRUCTED on each run and never once called. Measured: new_engine() 1, on_residual 0.

The first wiring fixed reachability and inherited a cadence bug: it fired at the tail of `_avatar_solve`, a
1900-line function, so the residual was sampled ONCE PER ~900 ACTIONS. CUSUM licenses a mint only on a REPRODUCED
residual, and nothing reproduces at one sample per solve. The loop was closed and not turning.

The engine's own spec said where this belongs, in its own docstring, the whole time:

    "buffer = list of grids for the CURRENT objective (RESET AT EACH DECISION POINT)"

A decision point is not a solve. It is every time the composer commits to an objective -- "walk to this trigger",
"collect that booster", "reach the exit" -- and finds out whether the world agreed. That is the cadence this runs at.

WHAT A RESIDUAL IS, HERE
------------------------
The composer commits to an objective and ARRIVES: by its own model, the thing it wanted is done. If the world then
does nothing -- no reward, and no change outside the avatar's own footprint -- the model is satisfied and unrewarded.
That is MODEL_INCOMPLETE stated in the avatar regime's terms, and it is the residual: the world obeys a dynamic the
grammar does not carry.

WHAT THIS FILE MAY NOT DO
-------------------------
Author atoms. Every mechanism it reaches already exists and is already tested:
    ResidualReporter -> forward-model prediction error over the objective-keyed buffer
    CUSUM            -> only a REPRODUCED residual licenses a mint; one occurrence is pareidolia
    triangulate      -> does the residual cast a shadow across primitives already held?
    _route_three_way -> shadow -> CO-OPT | representable -> MINT | neither -> ESCALATE, and NEVER mint
    DirectedMint     -> a new INSTANCE of a tested kind, parametrised BY the residual
This module is a wire. Levin forbids the alternative anyway: a closed loop cannot mint information, so the only
honest generator is one aimed by something the environment supplied.

THE STATUS BAR IS NOT THE WORLD
-------------------------------
Masked on every grid handed to the reporter. The first live routing returned a residual whose bounding box was the
HUD and whose colours included the meter: the agent reporting its own budget draining as a dynamic it cannot explain
-- the one thing it explains perfectly. An aim pointed at the meter mints a primitive for arithmetic already held.
(Third instrument this poisoned in one session: the delta percept, the booster detector, and the residual itself.)
"""

import numpy as np

HUD_ROW = 56                     # rows >= this are the agent's own instruments, not the world
MINT_PROBE_FRACTION = 0.25       # a licensed mint may spend a QUARTER of a life proving itself. Measured, not
#                                  chosen: this was 24 actions, sitting under a comment reading "a probe, not a
#                                  campaign", on a board where a life is 42. 24/42 = 57%. It WAS the campaign.
MINT_PROBE_FALLBACK = 8          # only until the bar has been read once
MAX_LICENSED_PER_LEVEL = 2       # and it may not re-litigate the same level forever


def mask_hud(grid):
    """The agent's resource display is not evidence about the environment's dynamics."""
    try:
        m = np.array(grid, copy=True)
        if m.ndim == 3:
            m = m[0]
        m[HUD_ROW:] = 0
        return m
    except Exception:
        return grid


def _mint_probe_budget(adapter):
    """A quarter of a life, measured off this game's bar."""
    try:
        import budget_model as _BM
        return _BM.get(adapter).actions_fraction(MINT_PROBE_FRACTION, lo=4, default=MINT_PROBE_FALLBACK)
    except Exception:
        return MINT_PROBE_FALLBACK


def _outside(grid, footprint_cells):
    """The board minus the avatar's own body -- 'did the WORLD move, or only me?'"""
    try:
        g = np.array(grid, copy=True)
        if g.ndim == 3:
            g = g[0]
        for (r, c) in (footprint_cells or []):
            r0, c0 = int(r), int(c)
            g[max(0, r0 - 3):r0 + 4, max(0, c0 - 3):c0 + 4] = 0
        return g
    except Exception:
        return grid


class ResidualRouter:
    """Per-objective residual routing. One instance per adapter, held across the whole game."""

    def __init__(self, emit=None):
        self.engine = None
        self.emit = emit or (lambda s: None)
        self.opened = 0
        self.closed = 0
        self.routed = 0
        self.routes = {}
        self.reproduced_hits = 0
        self.licensed = 0
        self._spent = {}
        self._open = None

    def _engine(self):
        if self.engine is None:
            try:
                import evolvability_engine as _EE
                self.engine = _EE.new_engine()
            except Exception:
                return None
        try:                                       # the board is not an object -- tell the shadow test what terrain is
            import evolvability_engine as _EE2, objective_validator as _OV2
            _t = (_OV2._GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("terrain_colours")
            if _t:
                _EE2.TERRAIN = set(_t)
        except Exception:
            pass
        return self.engine

    def open_objective(self, adapter, name, grid, footprint=None):
        """The composer commits. Reset the objective-keyed buffer: the residual is prediction error for THIS
        objective, and carrying frames across objectives measures the wrong thing."""
        try:
            self.opened += 1
            self._open = dict(name=str(name)[:60], g0=mask_hud(grid), foot=list(footprint or []),
                              lv=self._levels(adapter), buf=[mask_hud(grid)])
        except Exception:
            self._open = None

    def observe(self, grid):
        """One frame inside the current objective. RF1 wants a buffer, not a two-frame diff."""
        if self._open is None:
            return
        try:
            self._open["buf"].append(mask_hud(grid))
            if len(self._open["buf"]) > 8:
                self._open["buf"].pop(0)
        except Exception:
            pass

    def close_objective(self, adapter, arrived, grid, ctx_extra=None):
        """The composer finds out whether the world agreed.

        Routes ONLY when the objective was SATISFIED (arrived -- the model got what it asked for) and the world paid
        nothing: no reward, and nothing changed outside the avatar's own footprint. Not-arriving is a pathing
        failure, not a residual; routing it would aim the generator at the agent's own incompetence.
        """
        op, self._open = self._open, None
        if op is None or not arrived:
            return None
        self.closed += 1
        try:
            g_after = mask_hud(grid)
            rewarded = self._levels(adapter) > op["lv"]
            if rewarded:
                return None                                     # the model was right; nothing to explain
            # NO FURTHER GATE. An earlier version filtered on "did anything change outside the avatar" and routed
            # 0 of 107 satisfied-but-unrewarded objectives, because the world almost always changes SOMETHING. But
            # "the world responded" is not "the model predicted the response" -- and deciding that is precisely what
            # ResidualReporter's forward-prediction-error over the buffer is FOR. Pre-filtering here re-implemented
            # the mechanism badly and hid it from its own evidence. The engine's definition is the whole condition:
            # satisfied, and unrewarded.
            return self._route(adapter, op, g_after, ctx_extra)
        except Exception:
            return None

    def _route(self, adapter, op, g_after, ctx_extra):
        """CHEAP PATH: characterise the residual, count it, ask CUSUM, route it. No actions spent.

        `engine.on_residual()` is NOT an observer -- it proposes candidate organs and then descend/pursue-s them with
        real actions. Firing that at every decision point ate the whole run: objectives 305 -> 3, and max_level fell
        1 -> 0, below the band. The report is cheap and the EXECUTION is expensive, and they were welded together.

        So: report and accumulate on every objective, and only hand the engine the wheel when CUSUM says the residual
        has REPRODUCED and a mint is licensed. That is the engine's own rule -- a one-off residual is pareidolia --
        applied to its own budget. An agent that spends its entire meter investigating the first surprise it meets is
        not doing science; it is doing the thing the meter is measuring.
        """
        eng = self._engine()
        if eng is None:
            return None
        try:
            import evolvability_engine as _EE
            res = eng.reporter.report(op["g0"], g_after,
                                      [({"descriptor": op["name"], "relation": "REACH"}, None)],
                                      (ctx_extra or {}).get("traces", {}), buffer=list(op["buf"]))
            eng.residual_counts[res.key()] += 1
            res.reproduced = eng.residual_counts[res.key()]
            speciate = eng.cusum.push(1.0 if res.reproduced >= 1 else 0.0)
            shadow = _EE.triangulate(res)
            route, _handle = _EE._route_three_way(res, shadow)
            self.routed += 1
            self.routes[route] = self.routes.get(route, 0) + 1
            if res.reproduced > 1:
                self.reproduced_hits += 1
            self.emit("RESIDUAL  [%s] %s x%d -> %s%s" % (op["name"], res.key()[0], res.reproduced, route.upper(),
                      "  [REPRODUCED -> licensed to act]" if speciate else "  [first sighting -- watching, not minting]"))
            # CROSS-LEVEL MEMORY (refutation_ledger + persistent_model, previously reachable only from the retired
            # brain -- now wired to the live molecule reach). Molecules used on a level the agent CLEARS become
            # established and carry forward; persistent_model accumulates the component model across levels and its
            # MODEL-BREAK signal GATES that carry-forward -- a genuinely different next level holds prior molecules
            # as context only, it does not trust them. This is "stop re-deducing what you established", with a
            # "but this is a different game now" guard (the consumer that makes persistent_model do real work).
            try:
                import refutation_ledger as _RL, persistent_model as _PM, objective_validator as _OVk
                _gk = _OVk._GLOBAL_KNOWLEDGE.setdefault("patterns", {})
                _led = _gk.get("refutation_ledger") or _gk.setdefault("refutation_ledger", _RL.RefutationLedger())
                _pm = _gk.get("persistent_model") or _gk.setdefault("persistent_model", _PM.PersistentModel())
                _lv_now = self._levels(adapter)
                _lv_prev = getattr(self, "_led_lv", None)
                if _lv_now != _lv_prev:
                    _comps = []
                    try:
                        import object_seg as _OS2, numpy as _np3
                        _gg = _np3.asarray(g_after); _bg = int(_np3.bincount(_gg.ravel()).argmax())
                        _comps = [{"type": (o.get("color_sig"), o["size"] // 4),
                                   "identity": (o.get("color_sig"), o["size"]), "confidence": 0.5}
                                  for o in _OS2.segment_objects(_gg, bg=_bg)]
                    except Exception:
                        _comps = []
                    _mb = _pm.is_model_break(_comps) if _comps else False   # is the NEW level a different game?
                    if _lv_prev is not None and _lv_now > _lv_prev:
                        if not _mb:
                            for _id in list(_led.candidates):    # SAME game -> molecules on the cleared level established
                                _led.confirmed[_id] = {"via": "level-cleared"}
                        else:
                            self.emit("MODEL-BREAK  level %s reuses little of my accumulated model -> a different "
                                      "mechanic; prior molecules held as context, not trusted" % _lv_now)
                    _eq = _pm.explanation_quality(_comps) if _comps else 1.0
                    _pm.absorb(_comps)                           # layer the new level UNDER the accumulated model
                    _led.new_episode(level=_lv_now)
                    self._led_lv = _lv_now
                    if _lv_prev is not None:
                        self.emit("MODEL  level %s: %.0f%% of its components are already in my accumulated model "
                                  "(%d types known)%s" % (_lv_now, 100.0 * _eq, len(_pm.known_types()),
                                  "  [MODEL-BREAK -> re-learn]" if _mb else "  [known -> carry the model]"))
                    self._self_assess(adapter)                 # the agent scores its own developmental rung + gap
            except Exception:
                _led = None
            # self-assess also fires on a within-life cadence, not only on level change -- a life that never
            # advances a level is still a full reasoning episode, and its gap (reason at L3, corroborate at L2)
            # is exactly what the agent needs to see. Every ~40 residual routes.
            try:
                self._assess_n = getattr(self, "_assess_n", 0) + 1
                if self._assess_n % 8 == 0:                    # residuals are sparse -> re-assess every few, so the
                    self._self_assess(adapter)                 # reading tracks the agent as it climbs into L3, not a
                    #                                            stale early-life snapshot
            except Exception:
                pass
            # GRAMMAR REACH (this session): the agent reaches its WHOLE grammar to NAME the residual -- an
            # existing molecule it already holds, a composite of tools it has, or a gap it must compose. This is
            # Candidate-2 access: compose_or_invent reaches all ~116 molecules and was dormant (one hardcoded
            # caller). invent only when the residual REPRODUCED -> the library grows a molecule only when the
            # world confirms the gap, never on a one-off (that is apophenia / bloat). No actions spent.
            try:
                import objective_grammar as _G
                _prs = sorted(ResidualRouter._observed_primes(adapter, shadow)
                              | ResidualRouter._residual_effect_primes(op, g_after))
                _reach = None
                if len(_prs) > 2:                    # more than the base {BECOME, BECAUSE}: a real effect was
                    #                                  derived from the agent's confirmed dynamics. Reaching the
                    #                                  grammar with only "a caused change" is vacuous -> skip it
                    #                                  (and never mint a vacuous provisional). The feed enriches
                    #                                  as the agent confirms trigger effects on the board.
                    _reach = _G.compose_or_invent(_prs, context=op["name"], invent=bool(res.reproduced > 1))
                _m = _reach.get("mode") if _reach else None
                _nm = _reach.get("name") if _reach else None
                if _led is not None and _nm:                     # feed + consult the cross-level memory
                    if _nm in _led.established:
                        self.emit("MEMORY  [%s] %s is ESTABLISHED from a prior level -- I already understand this "
                                  "mechanic, not re-deducing it" % (op["name"], _nm))
                    else:
                        _led.seen.add(_nm); _led.candidates.setdefault(_nm, _nm)
                if _m in ("library", "nearest"):
                    self.emit("GRAMMAR  [%s] residual reads as %s -- reached a prior I already hold, no new atom needed"
                              % (op["name"], _reach["name"]))
                elif _m == "composite":
                    self.emit("GRAMMAR  [%s] residual composes from %s -- built from tools I have"
                              % (op["name"], " + ".join(_reach["from"])))
                elif _m == "invent" and _G.promote_temp_molecule(_reach["name"], gloss="reproduced residual on %s" % op["name"]):
                    self.emit("GRAMMAR  [%s] COMPOSED a new molecule %s from primes %s -- the library lacked it and the "
                              "residual reproduced, so I built it and kept it" % (op["name"], _reach["name"], list(_reach["primes"])))
                elif _m == "gap" and res.reproduced > 1:
                    self.emit("GRAMMAR  [%s] GAP -- nearest tool %s doesn't cover primes %s"
                              % (op["name"], _reach.get("nearest"), _reach.get("primes")))
            except Exception:
                pass
            if not speciate:
                return None                      # accumulate. Do not spend the board's budget on one surprise.
        except Exception:
            return None
        # EXPENSIVE PATH -- reached only on a reproduced, CUSUM-licensed residual, and rate-limited even then.
        _lv = self._levels(adapter)
        if self._spent.get(_lv, 0) >= MAX_LICENSED_PER_LEVEL:
            return None
        self._spent[_lv] = self._spent.get(_lv, 0) + 1
        import objective_validator as _OV
        ctx = dict(g0=g_after, ctrl=(ctx_extra or {}).get("ctrl"),
                   refuted=[({"descriptor": op["name"], "relation": "REACH"}, None)],
                   atomics=ResidualRouter._atomics(adapter), g_before=op["g0"], g_after=g_after,
                   active_traces=(ctx_extra or {}).get("traces", {}),
                   compile_objective=_OV.compile_objective,
                   compile_discrepancy=_OV.compile_discrepancy,
                   descend=_OV.descend, pursue=_OV.pursue,
                   # A MINT IS A PROBE, NOT A CAMPAIGN.
                   #
                   # Handing it the solve's budget (260) meant three licensed mints spent the whole run: the market
                   # made 6 decisions in 3062 actions and the macro shell discovered nothing, because the engine was
                   # off testing hypotheses with the agent's entire meter. CUSUM licensing a mint says "this residual
                   # is real enough to look at", not "spend the game on it". A new organ has to earn its budget the
                   # same way every other claim does -- by paying off small first.
                   adapter=adapter, budget=_mint_probe_budget(adapter),
                   buffer=list(op["buf"]),
                   held_grids=getattr(eng, "held_out_levels", None))
        self.licensed += 1
        won = eng.on_residual(ctx)
        for line in (getattr(eng, "narration", []) or [])[-2:]:
            self.emit("RESIDUAL  [%s] %s" % (op["name"], str(line)[:130]))
        return won

    @staticmethod
    def _atomics(adapter):
        """THE ABDUCTION->MOLECULE BRIDGE, which was the literal argument `atomics=[]`.

        `CoOption.propose` does:  base = [(h,d) for (h,d) in atomics if h['descriptor'] in names]

        It routed to CO-OPT 134 times and composed over an EMPTY LIST every one of them -- so the route was correct
        and there was nothing to recruit. That is Candidate 2 exactly: *the molecules exist but are not reachable
        from abduction; the gap is the bridge, not the inventory.* The bridge was a missing argument.

        The avatar regime never calls abduce(), so there is no classical hypothesis set. But it has TWO sources of
        induced structure, and both are grammar:
          - the causal map: trigger-type -> effect, learned live from probes
          - the object inducer: (colour_signature, size, action) -> translate/vanish/recolor/rotate

        Handing them over is a shape conversion, not an invention. Routing, not minting -- unchanged since July 8.
        """
        out = []
        try:
            import objective_validator as _OV
            cm = (_OV._GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("avatar_cmap", {}) or {}
            for k, at in cm.items():
                eff = at.get("effect")
                if not eff:
                    continue                      # an atom with no effect explains nothing; it cannot cast a shadow
                out.append(({"descriptor": "cmap:%s" % (eff,), "relation": "STEP_ON", "effect": eff,
                             "insts": at.get("insts") or ([at.get("inst")] if at.get("inst") else [])}, None))
        except Exception:
            pass
        try:
            oti = getattr(adapter, "_obj_inducer", None)
            if oti is not None:
                # report() returns COUNTS ("object_rules_confirmed: 15"), not rules. The rules live in `table`:
                # key = (colour_signature, size_bucket, action) -> effect counter. That key IS the factored model's
                # (kappa, tau, action) -- one rule per object TYPE, which is the whole point: a rule learned from one
                # door transfers to every door, and a wrong rule is repaired for one type without touching the rest.
                for key in list(oti.table.keys())[:16]:
                    eff = oti._rule(key)
                    if eff is None:
                        continue                          # unconfirmed: not yet a law, so not yet grammar
                    out.append(({"descriptor": "obj:%s->%s" % (str(key)[:34], str(eff)[:22]),
                                 "relation": "OBJECT_LAW", "key": key, "effect": eff}, None))
        except Exception:
            pass
        return out

    # Effect (measured, from the agent's OWN induced atomics) -> the grammar primes that describe it. Not a
    # per-game rule: it is the standing meaning of each effect class in the basis, so a residual can be named
    # in the WHOLE grammar. Every residual is also a caused change following an action -> BECOME + AFTER.
    _EFFECT_PRIMES = {
        "translate": {"BE_AT", "TOUCH"}, "vanish": {"NONE", "EXIST"}, "erase": {"NONE", "EXIST"},
        "recolor": {"BECOME", "SAME"}, "colour": {"BECOME", "SAME"}, "paint": {"BECOME", "SAME", "COVER"},
        "rotate": {"BECOME", "SAME", "TOUCH"}, "orientation": {"BECOME", "SAME"}, "shape": {"BECOME", "SAME"},
        "restate": {"BECOME"}, "budget": {"BECOME"}, "opens_route": {"CAN", "BE_AT"},
    }

    @staticmethod
    def _observed_primes(adapter, shadow):
        """The primes the agent ACTUALLY observed on this board: the effect-classes it has CONFIRMED from its
        own probes (the induced atomics -- cmap trigger->effect, object laws), mapped to the basis, plus
        BECOME/BECAUSE (a residual is a caused change). This grounds the residual in what the agent has learned
        the board DOES, so compose_or_invent reaches the whole grammar with the agent's real dynamics -- not a
        hardcoded list, and not the vacuous 'a change happened'. The shadow, when present, RANKS which effect is
        most implicated; absent, the board's whole confirmed vocabulary is used."""
        prs = {"BECOME", "BECAUSE"}                             # a residual is a CAUSED CHANGE
        try:
            atoms = ResidualRouter._atomics(adapter)
            names = {k[1] for k in (shadow or {}).keys() if isinstance(k, tuple) and k[0] == "primitive"}
            shadowed = [h for h, _d in atoms if h.get("descriptor") in names]
            use = shadowed if shadowed else [h for h, _d in atoms]   # shadow-casters if any; else all confirmed
            for h in use:
                prs |= ResidualRouter._EFFECT_PRIMES.get(str(h.get("effect")), set())
        except Exception:
            pass
        return prs

    @staticmethod
    def _residual_effect_primes(op, g_after):
        """CREDIT ASSIGNMENT: name the residual's EFFECT CLASS by reading what actually changed between the
        two frames the residual is about -- independent of whether any trigger effect is confirmed yet. A
        thing removed -> NONE/EXIST; vacated-here-and-filled-there -> translation (BE_AT/TOUCH); in-place
        recolour toward a target -> SAME; placed -> BE_AT. This is the direct causal read that lets the reach
        land on the right molecule even mid-characterisation, when the cmap is still empty."""
        prs = {"BECOME", "BECAUSE"}
        try:
            import numpy as _np
            buf = op.get("buf") or []
            if len(buf) >= 2:
                a, b = _np.asarray(buf[-2]), _np.asarray(buf[-1])
            else:
                a, b = _np.asarray(op["g0"]), _np.asarray(g_after)
            if a.shape != b.shape:
                return prs
            diff = _np.argwhere(a != b)
            if diff.size == 0:
                return prs
            bg = int(_np.bincount(a.ravel()).argmax())
            app = dis = rec = 0
            for r, c in diff:
                va, vb = int(a[r, c]), int(b[r, c])
                if va == bg and vb != bg:
                    app += 1
                elif va != bg and vb == bg:
                    dis += 1
                else:
                    rec += 1
            if dis and not app:
                prs |= {"NONE", "EXIST"}                      # removal
            elif app and dis:
                prs |= {"BE_AT", "TOUCH"}                     # translation (vacated here, filled there)
            elif rec:
                prs |= {"SAME"}                               # in-place recolour toward a target
            elif app:
                prs |= {"BE_AT"}                              # placement
        except Exception:
            pass
        return prs

    # THE LADDER, in-agent. The agent's own developmental self-assessment, ANCHORED to external outcome so it
    # is not dead reckoning: log-rung = the highest reasoning MOVE it emitted; corroborated-rung = the highest
    # one an EXTERNAL fact confirms (a gate opened, a level cleared, a named molecule carried across levels).
    # The gap tells the agent WHICH faculty is behind -- metacognition, the scaffold for L3->L4. And the
    # EARNED-CAPABILITY gate: corroborated-L4 AND an explicit need-rationale unlocks a forbidden tool (reset),
    # because the reasoning that reaches for it IS the readiness (the graduation bar, measured not guessed).
    _RUNG_SIG = [
        ("sensorimotor",        ("PROPRIOCEPT", "LAYERS", " MODEL ", "RECOGNISE")),
        ("representational",    ("HYPOTHESIS", "FALSIFY", "readout identity", "reads as")),
        ("concrete-operational",("COMPARE", "ENUMERATE", " PLAN ", "INDUCE", "BUDGET-MATH", "SUBGOAL")),
        ("formal-operational",  ("COMPOSED a new molecule", "MODEL-BREAK", "is ESTABLISHED from a prior level")),
    ]

    def _self_assess(self, adapter):
        try:
            import objective_validator as _OVs
            deriv = _OVs._game_mem(adapter).get("derivation", []) or []
        except Exception:
            return
        text = "\n".join(str(x) for x in deriv[-400:])
        log_rung = 0
        for i, (_name, keys) in enumerate(ResidualRouter._RUNG_SIG, start=1):
            if any(k in text for k in keys):
                log_rung = i
        cleared = self._levels(adapter) > 0
        gate = ("key MATCHES lock" in text) or ("GATE" in text and "SATISFIED" in text)
        real_compose = "is ESTABLISHED from a prior level" in text          # a NAMED molecule carried across a level
        reset_need = ("return to start" in text) or ("reset" in text.lower() and "need" in text.lower())
        corr = 0
        if ("confirmed object-laws" in text) or ("RECOGNISE" in text):
            corr = 1
        if gate or ("COMPARE" in text):
            corr = max(corr, 2)                                             # roles named well enough to compare
        if gate or cleared:
            corr = max(corr, 3)                                             # the plan converged in the world
        if real_compose:
            corr = max(corr, 4)                                            # self-authored structure that held
        names = {0: "reflex", 1: "sensorimotor", 2: "representational", 3: "concrete-operational", 4: "formal-operational"}
        weak = {1: "perception", 2: "role-naming", 3: "execution/navigation", 4: "composition"}
        if log_rung >= 2:
            tail = ("  -> the gap is %s, not my reasoning" % weak.get(corr + 1, "?")) if log_rung > corr else "  -> aligned"
            self.emit("SELF-ASSESS  I reason at L%d (%s) but corroborate at L%d (%s)%s"
                      % (log_rung, names[log_rung], corr, names[corr], tail))
        if corr >= 4 and reset_need:                                       # EARNED: reasoned to it AND it held
            try:
                import objective_validator as _OVe
                _gk = _OVe._GLOBAL_KNOWLEDGE.setdefault("patterns", {})
                if not _gk.get("reset_earned"):
                    _gk["reset_earned"] = True
                    self.emit("EARNED  reset UNLOCKED -- corroborated-L4 (a composed primitive that held across a "
                              "level) AND I reasoned my own way to needing reset. The reasoning is the unlock.")
            except Exception:
                pass

    @staticmethod
    def _levels(adapter):
        try:
            return int(getattr(getattr(adapter, "_obs", None), "levels_completed", 0) or 0)
        except Exception:
            return 0

    def report(self):
        eng = self.engine
        return {"objectives_opened": self.opened, "objectives_satisfied": self.closed,
                "residuals_routed": self.routed, "routes": dict(self.routes),
                "reproduced_residuals": self.reproduced_hits, "mints_licensed": self.licensed,
                "engine_fired": getattr(eng, "fired", 0) if eng else 0,
                "residual_kinds": (len(getattr(eng, "residual_counts", {}) or {}) if eng else 0),
                "reproduced_max": (max((getattr(eng, "residual_counts", {}) or {}).values())
                                   if eng and getattr(eng, "residual_counts", None) else 0)}
