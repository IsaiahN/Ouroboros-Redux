# Injected by tools/verify/hermetic.py. Seeds every RNG the run path uses, at interpreter startup,
# BEFORE any agent module imports. No agent file is modified.
import os, random
_s = int(os.environ.get("OURO_SEED", "0"))
random.seed(_s)
try:
    import numpy as _np
    _np.random.seed(_s % (2 ** 32))
except Exception:
    pass
try:
    import torch as _t
    _t.manual_seed(_s)
except Exception:
    pass

# --- CUT-WIRE on has_goal (OURO_CUTWIRE = force | negate). Builder-only, never in a scored run. ---
# A PROPERTY is a DATA descriptor, so it wins over the instance __dict__ that the dataclass __init__
# writes to. That is what makes this a corruption of the SIGNAL rather than of the producer: the
# perceiver still computes and assigns exactly what it always did; only what downstream READS changes.
# CUT-WIRE ON LOADED KNOWLEDGE. Beat 20 gave the agent 106 remembered facts; that it EXISTS and that
# it is CONSUMED are different claims. Wiping the map right after the loader fills it isolates exactly
# the loaded portion -- the agent still learns normally from its own actions within the episode.
_WIPE = os.environ.get("OURO_WIPE_LOADED", "")
if _WIPE:
    # A RAISE HERE WOULD BE SILENT. Python reports a sitecustomize failure as a warning and carries on
    # UNSEEDED AND UNPROBED -- the exact failure mode that produced a fake 'hermetic' run in beat 4.
    # The compile check in _sandbox catches syntax errors; only this catches import-time ones.
    try:
        import cognitive_loop as _clw
        _olpk = _clw.CognitiveLoop._load_prior_knowledge
    except BaseException as _e:
        with open("WIPE_PROBE_FAILED.txt", "w", encoding="utf-8") as _fh:
            _fh.write("%s: %s" % (type(_e).__name__, _e))
        _clw = None

    def _wiped(self, game_id, *a, **k):   # noqa: E306
        r = _olpk(self, game_id, *a, **k)
        cm = getattr(self, "_causal_map", None)
        if cm is not None:
            try:
                # BEAT 21'S WIPE CLEARED TWO OF THE SIX STRUCTURES THE LOADER FILLS, so its
                # "isolation" was not one -- _explored, _all_positions, _walls and _rules survived,
                # and marking N positions as already-explored changes exploration by itself.
                # OURO_WIPE_LOADED=full clears all six; anything else keeps the partial behaviour so
                # the two arms stay comparable.
                names = (["_effects", "_color_cycles"] if _WIPE != "full" else
                         ["_effects", "_color_cycles", "_explored", "_all_positions",
                          "_walls", "_rules"])
                sizes = []
                for nm in names:
                    obj = getattr(cm, nm, None)
                    if obj is None:
                        sizes.append(nm + "=absent")
                        continue
                    sizes.append("%s=%d" % (nm, len(obj)))
                    try:
                        obj.clear()
                    except Exception:
                        sizes[-1] += "(UNCLEARABLE)"
                with open("wiped.txt", "a", encoding="utf-8") as fh:
                    fh.write("mode=%s " % _WIPE + " ".join(sizes) + chr(10))
            except Exception as _we:
                with open("wiped.txt", "a", encoding="utf-8") as fh:
                    fh.write("WIPE FAILED: %s" % _we + chr(10))
        return r

    if _clw is not None:
        _clw.CognitiveLoop._load_prior_knowledge = _wiped

# --- EGO-CONFIRM CUT-WIRE (OURO_CW_EGOCONFIRM=N). Consumption falsifier for the goal spine
# (PREREG_PHASE2.md): at the Nth drive() call, force-confirm the current top candidate through
# the REAL credit path, then let the shipped drive run. If the forced arm's action sequence is
# byte-identical to control, the drive is decorative. Instrument-side only; shipped code never
# reads this env var.
_ECW = os.environ.get("OURO_CW_EGOCONFIRM", "")
if _ECW:
    try:
        from engines.egocentric.spine import GoalSpine as _GS
        _eon = int(_ECW)
        _odrv = _GS.drive
        _ocred = _GS.credit
        _est = {"n": 0, "forced": False}

        def _fdrive(self, self_cell):
            _est["n"] += 1
            if not _est["forced"] and _est["n"] >= _eon and self.manager.price:
                top = max(self.manager.price, key=self.manager.price.get)
                cell = (top[1] if isinstance(top, tuple) and len(top) == 2
                        and isinstance(top[1], tuple) else top)
                try:
                    _ocred(self, cell)
                    _est["forced"] = True
                    print("[CW-EGOCONFIRM] forced credit at %s (call %d)" % (cell, _est["n"]))
                except Exception as _fe:
                    print("[CW-EGOCONFIRM] force failed: %s" % _fe)
            return _odrv(self, self_cell)

        _GS.drive = _fdrive
    except Exception as _e:
        print("[CW-EGOCONFIRM] attach failed: %s" % _e)

_CW = os.environ.get("OURO_CUTWIRE", "")
if _CW:
    import engines.perception.perceptual_field as _pfm
    _C = _pfm.PerceptualField

    def _hg_get(self):
        raw = bool(self.__dict__.get("_ouro_hg", False))
        return True if _CW == "force" else (not raw)

    def _hg_set(self, v):
        self.__dict__["_ouro_hg"] = bool(v)
        # PRE-REGISTERED CONFOUND: cognitive_loop:1915 reads `has_goal AND goal_cells`, so a forced
        # flag with an empty goal_cells short-circuits on the second conjunct and the arm would test
        # nothing. Seed one placeholder cell ONLY when forcing, and only if the perceiver left it
        # empty -- never overwrite a real detection.
        if _CW == "force" and not self.__dict__.get("goal_cells"):
            self.__dict__["goal_cells"] = {(0, 0): 1}

    _C.has_goal = property(_hg_get, _hg_set)

# --- GOAL-CHANNEL PROBE (OURO_GOALPROBE=1). Counts only; changes nothing. -------------------------
# _run_goal_channel is the ONLY place has_goal is set True, and its whole body sits inside
#   except Exception as e: logger.debug(...)
# so a channel that throws on every frame is INVISIBLE at default log level. This probe distinguishes
# the three ways the channel can produce nothing, which no amount of reading the source can settle:
#   NOT REACHED   -- perceive() never calls it
#   EARLY RETURN  -- visual_scene_dict or frame_array is None, so it returns before any detection
#   THREW         -- the swallowed exception path
#   NO MATCH      -- it ran to completion and found neither a reference panel nor a transformation
_GP = os.environ.get("OURO_GOALPROBE", "")
if _GP:
    import atexit, json as _json
    import engines.perception.perceiver as _pv
    _tally = {"calls": 0, "early_return": 0, "threw": 0, "ref_panel": 0, "transforms_only": 0,
              "no_match": 0, "set_true": 0, "exc_types": {},
              # 'early return' is two different bugs wearing one number: a spatial channel that
              # returned None, or a frame that never arrived. Separated, because the fixes differ.
              "early_no_scene": 0, "early_no_frame": 0}
    _orig = _pv.Perceiver._run_goal_channel

    def _probed(self, visual_scene_dict, frame_array, pf):
        _tally["calls"] += 1
        if visual_scene_dict is None or frame_array is None:
            _tally["early_return"] += 1
            if visual_scene_dict is None:
                _tally["early_no_scene"] += 1
            if frame_array is None:
                _tally["early_no_frame"] += 1
            return _orig(self, visual_scene_dict, frame_array, pf)
        try:
            rp = visual_scene_dict.get("reference_panel_id")
            tr = visual_scene_dict.get("transformations", [])
        except Exception:
            rp, tr = None, []
        if rp is not None:
            _tally["ref_panel"] += 1
        elif tr:
            _tally["transforms_only"] += 1
        else:
            _tally["no_match"] += 1
        # Call the ORIGINAL and observe what it did, rather than reimplementing its logic here --
        # a probe that re-derives the thing it measures is measuring the probe.
        try:
            r = _orig(self, visual_scene_dict, frame_array, pf)
        except BaseException as e:
            _tally["threw"] += 1
            k = type(e).__name__
            _tally["exc_types"][k] = _tally["exc_types"].get(k, 0) + 1
            raise
        try:
            if pf.has_goal:
                _tally["set_true"] += 1
        except Exception:
            pass
        return r

    _pv.Perceiver._run_goal_channel = _probed

    # --- SPATIAL-CHANNEL PROBE. _run_spatial_channel returning None is what starves the goal
    # channel on mode-B games (sk48 130/200, ft09 162/200). It has TWO None paths -- a guard, and a
    # SECOND swallowed `except Exception: logger.debug(...)`. Last beat the equivalent hypothesis was
    # refuted for the goal channel, so this one is measured rather than assumed in either direction.
    _tally["sp_calls"] = 0
    _tally["sp_guard_cortex"] = 0
    _tally["sp_guard_framelist"] = 0
    _tally["sp_threw"] = 0
    _tally["sp_ok"] = 0
    _tally["sp_exc"] = {}
    _origsp = _pv.Perceiver._run_spatial_channel

    def _probed_sp(self, frame_list, pf):
        _tally["sp_calls"] += 1
        if getattr(self, "_visual_cortex", None) is None:
            _tally["sp_guard_cortex"] += 1
        if frame_list is None:
            _tally["sp_guard_framelist"] += 1
        try:
            r = _origsp(self, frame_list, pf)
        except BaseException as e:
            _tally["sp_threw"] += 1
            raise
        if r is None:
            # The original swallows its own exception and returns None, so a None that is NOT
            # explained by a guard is the swallowed path -- inferred from the outcome, because
            # re-implementing the try block here would be measuring the probe.
            if getattr(self, "_visual_cortex", None) is not None and frame_list is not None:
                _tally["sp_threw"] += 1
        else:
            _tally["sp_ok"] += 1
        return r

    _pv.Perceiver._run_spatial_channel = _probed_sp

    # --- TEARDOWN PROBE. Beat 46: on some games the code after the play loop is never reached --
    # no "Game ended" line, no record append. The [GAME OVER] print happens BEFORE
    # _write_frame_snapshot and event_bus.publish, so a raise in either skips the break and
    # everything after the loop. This names which one, instead of guessing in a fix brief.
    _tally["teardown_exc"] = {}
    try:
        import cognitive_game_player as _cgp

        def _wrap(owner, name, label):
            fn = getattr(owner, name, None)
            if fn is None:
                _tally["teardown_exc"][label + ":ABSENT"] = 1
                return

            def _w(*a, **k):
                try:
                    return fn(*a, **k)
                except BaseException as e:
                    key = "%s RAISED %s: %s" % (label, type(e).__name__, str(e)[:120])
                    _tally["teardown_exc"][key] = _tally["teardown_exc"].get(key, 0) + 1
                    raise
            setattr(owner, name, _w)

        _wrap(_cgp.CognitiveGamePlayer, "_write_frame_snapshot", "snapshot")
        # Wrap the whole episode: does ANY exception escape play_game? Beat 47's first probe
        # wrapped only two named calls and found nothing, which does not mean nothing threw.
        _opg = _cgp.CognitiveGamePlayer.play_game

        def _pg(self, *a, **k):
            try:
                return _opg(self, *a, **k)
            except BaseException as e:
                import traceback as _tb
                site = "?"
                for fr in reversed(_tb.extract_tb(e.__traceback__)):
                    if "site-packages" not in fr.filename.lower():
                        site = "%s:%d in %s" % (os.path.basename(fr.filename), fr.lineno, fr.name)
                        break
                key = "play_game ESCAPED %s: %s @ %s" % (type(e).__name__, str(e)[:90], site)
                _tally["teardown_exc"][key] = _tally["teardown_exc"].get(key, 0) + 1
                raise
        _cgp.CognitiveGamePlayer.play_game = _pg
        try:
            import event_bus as _eb
            _obus = _eb.EventBus.publish

            def _pub(self, *a, **k):
                try:
                    return _obus(self, *a, **k)
                except BaseException as e:
                    key = "publish RAISED %s: %s" % (type(e).__name__, str(e)[:120])
                    _tally["teardown_exc"][key] = _tally["teardown_exc"].get(key, 0) + 1
                    raise
            _eb.EventBus.publish = _pub
        except Exception as _e2:
            _tally["teardown_exc"]["publish-probe-failed: %s" % _e2] = 1
    except Exception as _e:
        _tally["teardown_exc"]["PROBE-FAILED: %s" % str(_e)[:80]] = 1


    # TILE MAP + FRAME_CHANGED CUT-WIRE.
    # The codebase's own comment says pixel-level multi-cell counts are ARTEFACTS because one tile is
    # 16-38 pixels, and it uses _tile_map to work in tiles instead. So: is _tile_map ever populated?
    # And separately -- before enriching frame_changed with magnitude, does frame_changed reach an
    # action at all? OURO_CW_FC=invert flips it; if actions do not move, enriching it is pointless.
    _tally["tilemap_set"] = 0
    _tally["tilemap_none"] = 0
    _tally["fc_true"] = 0
    _tally["fc_false"] = 0
    # DEAD-CELL RE-CLICK TALLY (read-only; PREREG_pariah_recon.md). A cell whose click produced no
    # frame change is "dead once"; clicking it again is the waste an in-episode pariah consumer
    # would remove. Counted here because this wrapper already receives click_pos + frame_changed.
    _tally["clicks"] = 0
    _tally["reclick_dead1"] = 0
    _tally["reclick_dead2"] = 0
    _DEAD = {}
    try:
        import engines.cognition.causal_map as _cm2
        _oufa = _cm2.CausalMap.update_from_action
        _FC = os.environ.get("OURO_CW_FC", "")

        def _pufa(self, click_pos, pre_frame, post_frame, frame_changed, *a, **k):
            if getattr(self, "_tile_map", None) is not None:
                _tally["tilemap_set"] += 1
            else:
                _tally["tilemap_none"] += 1
            if frame_changed:
                _tally["fc_true"] += 1
            else:
                _tally["fc_false"] += 1
            if click_pos is not None:
                try:
                    _cp = (int(click_pos[0]), int(click_pos[1]))
                    _tally["clicks"] += 1
                    _n = _DEAD.get(_cp, 0)
                    if _n >= 1:
                        _tally["reclick_dead1"] += 1
                    if _n >= 2:
                        _tally["reclick_dead2"] += 1
                    if not frame_changed:
                        _DEAD[_cp] = _n + 1
                    else:
                        _DEAD[_cp] = 0
                except Exception:
                    _tally["reclick_tally_failed"] = True
            if _FC == "invert":
                frame_changed = not frame_changed
            elif _FC == "false":
                frame_changed = False
            return _oufa(self, click_pos, pre_frame, post_frame, frame_changed, *a, **k)

        _cm2.CausalMap.update_from_action = _pufa
    except Exception as _e:
        _tally["tilemap_probe_failed"] = str(_e)[:80]


    # --- PARIAH WIRE TALLY + CUT (OURO_CW_PARIAH=empty). Isaiah's question: do agents actually
    # USE pariahs? The decisive runtime facts: (1) how many DB queries touch pariah tables during a
    # real run, split read/write; (2) if reads exist, does emptying them change the actions?
    _tally["pariah_q"] = {"reads": 0, "writes": 0}
    try:
        from database_interface import DatabaseInterface as _DBI
        _oexq = _DBI.execute_query
        _PCW = os.environ.get("OURO_CW_PARIAH", "")

        def _pexq(self, query, *a, **k):
            q = " ".join(str(query).lower().split())
            if "pariah" in q:
                if q.startswith("select"):
                    _tally["pariah_q"]["reads"] += 1
                    if _PCW == "empty":
                        return []
                else:
                    _tally["pariah_q"]["writes"] += 1
            return _oexq(self, query, *a, **k)

        _DBI.execute_query = _pexq
    except Exception as _e:
        _tally["pariah_probe_failed"] = str(_e)[:80]


    # --- MARKET SCORE TALLY (always on, read-only). Records every salience the market prices, so
    # abstention can be MEASURED: if the max score on a game is <= 0, the mean is <= 0 and the
    # selection rule abstains after bootstrap -- everything market-gated becomes unreachable there.
    _tally["mkt_scores"] = {"n": 0, "min": None, "max": None, "sum": 0.0}
    try:
        import engines.economy.marketplace as _mm
        _ores2 = _mm.Marketplace.resolve

        def _tally_resolve(self, before, actual_after, hypotheses):
            r = _ores2(self, before, actual_after, hypotheses)
            for v in r.scores.values():
                t = _tally["mkt_scores"]
                t["n"] += 1; t["sum"] += float(v)
                t["min"] = v if t["min"] is None else min(t["min"], v)
                t["max"] = v if t["max"] is None else max(t["max"], v)
            # SURPRISE TALLY: would the residual be non-empty for the scored prediction? The band
            # law needs both halves measured -- drive (scores) and surprise (this).
            try:
                import numpy as _np2
                for h_ in hypotheses:
                    _pred = h_.predict(before)
                    t = _tally["mkt_scores"]
                    t["surprised"] = t.get("surprised", 0) + (1 if bool((_pred != _np2.asarray(actual_after)).any()) else 0)
            except Exception:
                _tally["mkt_scores"]["surprise_tally_failed"] = True
            # DECOMP TALLY (OURO_TALLY_DECOMP=1, read-only). Per-settle decomposition of the
            # currency -- n_changed / pred_dev / correct_changed / hallucinated -- so an
            # exactly-0.00 game's mechanism is READ, not inferred. A static frame scores the match
            # fraction (1.0 for a no-change predictor), so exact-0 requires n_changed>0 with
            # correct==hall every settle; pred_dev separates "prediction collapsed to no-change"
            # from "replayed delta lands in the changed region with stale values".
            # See docs/carryover/PREREG_zero_score_mechanism.md.
            if os.environ.get("OURO_TALLY_DECOMP"):
                try:
                    import numpy as _np3
                    _b3, _a3 = _np3.asarray(before), _np3.asarray(actual_after)
                    _ch3 = (_a3 != _b3)
                    for h_ in hypotheses:
                        _p3 = _np3.asarray(h_.predict(before))
                        _tally.setdefault("decomp", [])
                        if len(_tally["decomp"]) < 400:
                            _tally["decomp"].append({
                                "n_changed": int(_ch3.sum()),
                                "pred_dev": int((_p3 != _b3).sum()),
                                "correct": int(((_p3 == _a3) & _ch3).sum()),
                                "hall": int(((_p3 != _b3) & ~_ch3).sum())})
                except Exception as _de:
                    _tally["decomp_failed"] = str(_de)[:80]
            return r

        _mm.Marketplace.resolve = _tally_resolve
    except Exception as _e:
        _tally["mkt_scores_failed"] = str(_e)[:80]


    # --- RESIDUAL-AIM CUT-WIRE (OURO_CW_RESID=random). The consumption falsifier for transplant 5:
    # replace the deterministic aim with a seeded random cell FROM THE SAME MASK. If the click
    # coordinates do not change, the aim is decorative -- revert. Seeded, so the corrupted arm is
    # itself hermetic.
    if os.environ.get("OURO_CW_RESID") == "random":
        try:
            import cognitive_loop as _cl6
            import random as _rr
            _rng = _rr.Random(int(os.environ.get("OURO_SEED", "0")) + 4242)

            def _rand_aim(mask):
                import numpy as _np
                if mask is None:
                    return None
                hits = _np.argwhere(mask)
                if hits.size == 0:
                    return None
                y, x = hits[_rng.randrange(len(hits))]
                return int(x), int(y)

            _cl6._residual_aim = _rand_aim
            _tally["cw_resid"] = "random"
        except Exception as _e:
            _tally["cw_resid_failed"] = str(_e)[:80]


    # --- PROGRESS-SIGNAL CUT-WIRE (OURO_CW_PROGRESS=score|level). Beat 82 measured that survival
    # does not convert into levels. The directest aim signal already flows through record_result:
    # score_delta and level_changed, the game's OWN progress ground truth. This forces them and
    # diffs the sequence: if nothing moves, progress is produced and steers nothing -- a dead wire,
    # and "the market prices progress" becomes the transplant shape.
    try:
        import cognitive_loop as _cl5
        _orr = _cl5.CognitiveLoop.record_result
        _PW = os.environ.get("OURO_CW_PROGRESS", "")

        def _prr(self, post_frame, frame_changed, score_delta, level_changed, *a, **k):
            if _PW == "score":
                score_delta = 0.5
            elif _PW == "level":
                level_changed = True
            return _orr(self, post_frame, frame_changed, score_delta, level_changed, *a, **k)

        if _PW:
            _cl5.CognitiveLoop.record_result = _prr
    except Exception as _e:
        _tally["progress_cw_failed"] = str(_e)[:80]


    # --- TIMER-URGENCY PROBE + CUT-WIRE (OURO_CW_TIMER=critical|safe). Two questions at once:
    # (1) what does the producer actually emit? (tallied per run) and (2) is the CONSUMER live --
    # does forcing urgency change the action sequence? A consumer that ignores corruption is dead,
    # and a dead consumer means the budget-model transplant has no wire to feed.
    _tally["timer_urgency"] = {}
    try:
        import cognitive_loop as _cl4
        _ochs = _cl4.CognitiveLoop._check_hud_state
        _TF = os.environ.get("OURO_CW_TIMER", "")

        def _pchs(self, cf, frame_array):
            out = _ochs(self, cf, frame_array)
            u = getattr(cf, "timer_urgency", None)
            _tally["timer_urgency"][str(u)] = _tally["timer_urgency"].get(str(u), 0) + 1
            if _TF in ("critical", "safe", "moderate"):
                cf.timer_urgency = _TF
                cf.timer_fraction = {"critical": 0.1, "moderate": 0.4, "safe": 0.9}[_TF]
            return out

        _cl4.CognitiveLoop._check_hud_state = _pchs
    except Exception as _e:
        _tally["timer_probe_failed"] = str(_e)[:80]


    # --- MARKETPLACE CURRENCY CUT-WIRE (OURO_CW_MKT=flat). The transplant's falsifier: if
    # flattening every price to the same constant changes NOTHING about the action sequence, the
    # market is decorative -- its scores are produced but not consumed. Patch Marketplace.resolve
    # rather than informative_salience: the default currency binds at class-creation time, so
    # patching the module name would miss silently.
    if os.environ.get("OURO_CW_MKT") == "flat":
        try:
            import engines.economy.marketplace as _mkt
            _ores = _mkt.Marketplace.resolve

            def _flat_resolve(self, before, actual_after, hypotheses):
                r = _ores(self, before, actual_after, hypotheses)
                flat = {name: 0.5 for name in r.scores}
                win = sorted(flat)[0] if flat else None
                self.log.append("CW_MKT flat: scores flattened to 0.5")
                return _mkt.Resolution(win, flat, bool(flat))

            _mkt.Marketplace.resolve = _flat_resolve
            _tally["cw_mkt"] = "flat"
        except Exception as _e:
            _tally["cw_mkt_failed"] = str(_e)[:80]

    # --- ACTION-AVAILABILITY CUT-WIRE. Does the agent read what the game OFFERS?
    # Measured at beat 65: a game that offers [1,2,3,4,5,6] got 150 clicks and no movement at all,
    # while eleven other games offering movement clicked only 5-22%. So the agent CAN pick movement
    # and did not. This records what it was offered against what it chose, and can corrupt the offer.
    #   OURO_CW_ACTIONS=noclick   remove 6 from the list the loop is told about
    #   OURO_CW_ACTIONS=clickonly remove 1,2,3,4 from it
    # If stripping 6 does not change the emitted actions, the list is not being read.
    _tally["offered"] = {}
    _tally["chosen"] = {}
    try:
        import cognitive_loop as _cl3
        _ocyc = _cl3.CognitiveLoop.cycle
        _CWA = os.environ.get("OURO_CW_ACTIONS", "")

        def _pcyc(self, frame, obs, *a, **k):
            # Record the two sources SEPARATELY. Conflating them once produced a contradiction with a
            # direct probe of the same game and cost a beat to unpick.
            _kw = k.get("available_actions")
            _ob = getattr(obs, "available_actions", None)
            for _lbl, _v in (("kwarg", _kw), ("obs", _ob)):
                _key = _lbl + ":" + (",".join(str(x) for x in sorted(_v)) if _v else "None")
                _tally["offered"][_key] = _tally["offered"].get(_key, 0) + 1
            av = _kw if _kw is not None else _ob
            if av:
                if _CWA == "noclick":
                    k["available_actions"] = [x for x in av if x != 6] or list(av)
                elif _CWA == "clickonly":
                    k["available_actions"] = [x for x in av if x not in (1, 2, 3, 4)] or list(av)
                elif _CWA.startswith("drop:"):
                    # Remove named actions. If the agent's near-monopoly on one action is a CHOICE,
                    # removing it should produce a varied distribution. If it is the argmax of a flat
                    # signal, the monopoly simply moves to whatever is next in order.
                    _drop = set(int(x) for x in _CWA[5:].split(",") if x.strip().isdigit())
                    k["available_actions"] = [x for x in av if x not in _drop] or list(av)
            out = _ocyc(self, frame, obs, *a, **k)
            try:
                num = out[0] if isinstance(out, tuple) else out
                _tally["chosen"][str(num)] = _tally["chosen"].get(str(num), 0) + 1
            except Exception:
                pass
            return out

        _cl3.CognitiveLoop.cycle = _pcyc
    except Exception as _e:
        _tally["actions_probe_failed"] = str(_e)[:80]


    # --- CONSUMPTION-CHAIN PROBE. The goal signal's only consumer is causal_map.set_goal(), which
    # enables plan_to_goal() -- and plan_to_goal() is itself gated on `strategy == "execute"`. So a
    # goal can be produced, forwarded, and STILL never planned on. Each link is counted separately
    # because they fail differently and only separate counts can tell them apart.
    _tally["cells_nonempty"] = 0
    _tally["cells_empty"] = 0
    _tally["set_goal"] = 0
    _tally["plan_to_goal_calls"] = 0
    _tally["plan_to_goal_nonempty"] = 0
    _tally["strategies"] = {}
    try:
        import engines.cognition.causal_map as _cm
        _optg_raw = _cm.CausalMap.plan_to_goal      # captured BEFORE wrapping, so the shadow call
        #                                            does not inflate the plan_to_goal_calls counter
        _osg = _cm.CausalMap.set_goal

        def _psg(self, goal_cells, *a, **k):
            _tally["set_goal"] += 1
            r = _osg(self, goal_cells, *a, **k)
            # SHADOW PLAN. The deadlock keeps plan_to_goal() from ever being called. Before anyone
            # builds a repair to open that gate, ask what is behind it: would the planner return a
            # plan if it ran? Call it here, out of band, and THROW THE RESULT AWAY.
            #
            # plan_to_goal() mutates _plan/_plan_valid/_plan_step at its end, and _plan_valid is what
            # has_plan reads -- so an unrestored shadow call would OPEN THE DEADLOCK ITSELF and the
            # probe would be measuring its own side effect. Snapshot and restore all three, in a
            # finally, so the run is bit-for-bit what it would have been.
            _snap = (getattr(self, "_plan", None), getattr(self, "_plan_valid", None),
                     getattr(self, "_plan_step", None))
            try:
                _tally["shadow_attempts"] = _tally.get("shadow_attempts", 0) + 1
                if not getattr(self, "_current_cells", None):
                    _tally["shadow_no_current_cells"] = _tally.get("shadow_no_current_cells", 0) + 1
                # WHY the plan is empty is two different bugs. plan_to_goal returns [] when the
                # goal/current delta is EMPTY (the agent believes it is already at the goal -- a
                # degenerate GOAL) and also when no rule can produce any needed transition (an empty
                # CAUSAL MODEL). Separate them here, from the same state the planner will read.
                _gc = getattr(self, "_goal_cells", None) or {}
                _cc = getattr(self, "_current_cells", None) or {}
                _d = sum(1 for _pz, _g in _gc.items()
                         if _cc.get(_pz) is not None and _cc.get(_pz) != _g)
                _tally["delta_zero"] = _tally.get("delta_zero", 0) + (1 if _d == 0 else 0)
                _tally["delta_nonzero"] = _tally.get("delta_nonzero", 0) + (1 if _d else 0)
                _tally["delta_max"] = max(_tally.get("delta_max", 0), _d)
                _tally["goal_cells_n"] = max(_tally.get("goal_cells_n", 0), len(_gc))
                _tally["curr_cells_n"] = max(_tally.get("curr_cells_n", 0), len(_cc))
                _tally["effects_n"] = max(_tally.get("effects_n", 0),
                                          len(getattr(self, "_effects", {}) or {}))
                # PERSISTENCE TEST. The max over a run says how much was learned; only the value at
                # the FIRST observation says how much was ALREADY THERE when the episode began.
                if "first_effects" not in _tally:
                    _tally["first_effects"] = len(getattr(self, "_effects", {}) or {})
                    _tally["first_cycles"] = len(getattr(self, "_color_cycles", {}) or {})
                _tally["cycles_n"] = max(_tally.get("cycles_n", 0),
                                         len(getattr(self, "_color_cycles", {}) or {}))
                # DO THE MODEL AND THE GOAL EVEN SHARE A COORDINATE SPACE? plan_to_goal's first
                # strategy looks up _color_cycles[target_pos] and its second scans _effects, both
                # keyed by POSITION. If those keys live in a different space from goal_cells keys --
                # tile vs pixel, (row,col) vs (x,y) -- every lookup misses and no amount of learning
                # can help. Record the KEY RANGES and the INTERSECTION, which settles it either way.
                _cy = getattr(self, "_color_cycles", {}) or {}
                _ef = getattr(self, "_effects", {}) or {}
                def _rng(keys):
                    ks = [k for k in keys if isinstance(k, tuple) and len(k) == 2]
                    if not ks:
                        return None
                    return (min(k[0] for k in ks), max(k[0] for k in ks),
                            min(k[1] for k in ks), max(k[1] for k in ks))
                _tally["rng_goal"] = _rng(_gc.keys()) or _tally.get("rng_goal")
                _tally["rng_cycles"] = _rng(_cy.keys()) or _tally.get("rng_cycles")
                _tally["rng_effects"] = _rng(_ef.keys()) or _tally.get("rng_effects")
                _tally["rng_current"] = _rng(_cc.keys()) or _tally.get("rng_current")
                _gk = set(_gc.keys())
                _tally["isect_goal_cycles"] = max(_tally.get("isect_goal_cycles", 0),
                                                  len(_gk & set(_cy.keys())))
                _tally["isect_goal_effects"] = max(_tally.get("isect_goal_effects", 0),
                                                   len(_gk & set(_ef.keys())))
                # And the intersection that actually matters: the DELTA cells, not all goal cells.
                _dk = {pz for pz, g in _gc.items()
                       if _cc.get(pz) is not None and _cc.get(pz) != g}
                _tally["isect_delta_cycles"] = max(_tally.get("isect_delta_cycles", 0),
                                                   len(_dk & set(_cy.keys())))
                _tally["isect_delta_effects"] = max(_tally.get("isect_delta_effects", 0),
                                                    len(_dk & set(_ef.keys())))
                _sp = _optg_raw(self)
                n = len(_sp) if _sp else 0
                if n:
                    _tally["shadow_plan_nonempty"] = _tally.get("shadow_plan_nonempty", 0) + 1
                    _tally["shadow_plan_maxlen"] = max(_tally.get("shadow_plan_maxlen", 0), n)
                else:
                    _tally["shadow_plan_empty"] = _tally.get("shadow_plan_empty", 0) + 1
            except BaseException as e:
                _tally["shadow_threw"] = _tally.get("shadow_threw", 0) + 1
                _tally.setdefault("shadow_exc", {})
                k2 = type(e).__name__
                _tally["shadow_exc"][k2] = _tally["shadow_exc"].get(k2, 0) + 1
            finally:
                try:
                    self._plan, self._plan_valid, self._plan_step = _snap
                except Exception:
                    pass
            return r
        _cm.CausalMap.set_goal = _psg

        _optg = _cm.CausalMap.plan_to_goal

        def _pptg(self, *a, **k):
            _tally["plan_to_goal_calls"] += 1
            r = _optg(self, *a, **k)
            if r:
                _tally["plan_to_goal_nonempty"] += 1
            return r
        _cm.CausalMap.plan_to_goal = _pptg
    except Exception as _e:
        _tally["strategies"]["CAUSALMAP-PROBE-FAILED: %s" % _e] = 1

    try:
        import cognitive_loop as _cl
        _oth = _cl.CognitiveLoop._think

        def _pth(self, percept, cf, *a, **k):
            # INSTRUMENT FIX (beat 21). first_effects used to be sampled at set_goal, and set_goal
            # never fires on the clock games -- so lf52 and dc22 held stored knowledge that could not
            # be seen at all. _think runs every step on every game, so sampling here is universal.
            try:
                _cm2 = getattr(self, "_causal_map", None)
                if _cm2 is not None and "step1_effects" not in _tally:
                    _tally["step1_effects"] = len(getattr(_cm2, "_effects", {}) or {})
                    _tally["step1_cycles"] = len(getattr(_cm2, "_color_cycles", {}) or {})
            except Exception:
                pass
            try:
                gc = getattr(percept, "goal_cells", None)
                if gc:
                    _tally["cells_nonempty"] += 1
                else:
                    _tally["cells_empty"] += 1
            except Exception:
                pass
            # THE DEADLOCK CANDIDATE. Three of the four "execute" paths require percept.has_plan,
            # and a plan can only be produced by plan_to_goal(), which only runs when the strategy is
            # already "execute". The one escape needs map_completeness > 0.5 AND fraction_done > 0.3.
            # Record the escape's two inputs, and has_plan, so the deadlock is measured not inferred.
            try:
                mc = float(getattr(percept, "map_completeness", -1) or 0)
                _tally["mc_max"] = max(_tally.get("mc_max", 0.0), mc)
                if mc > 0.5:
                    _tally["mc_over_half"] = _tally.get("mc_over_half", 0) + 1
                if getattr(percept, "has_plan", False):
                    _tally["has_plan_true"] = _tally.get("has_plan_true", 0) + 1
                ct = getattr(percept, "cells_total", 0) or 0
                if ct > 0:
                    fd = (getattr(percept, "cells_matching_goal", 0) or 0) / max(ct, 1)
                    _tally["fd_max"] = max(_tally.get("fd_max", 0.0), fd)
                    if fd > 0.3:
                        _tally["fd_over_third"] = _tally.get("fd_over_third", 0) + 1
                    if mc > 0.5 and fd > 0.3:
                        _tally["escape_open"] = _tally.get("escape_open", 0) + 1
            except Exception:
                pass
            r = _oth(self, percept, cf, *a, **k)
            try:
                st = r[0] if isinstance(r, tuple) else r
                _tally["strategies"][str(st)] = _tally["strategies"].get(str(st), 0) + 1
            except Exception:
                pass
            return r
        _cl.CognitiveLoop._think = _pth
    except Exception as _e:
        _tally["strategies"]["THINK-PROBE-FAILED: %s" % _e] = 1


    # The swallowed exception is caught INSIDE _run_spatial_channel, so wrapping that method can only
    # infer that one happened. To learn WHAT it is, wrap the call it makes: VisualCortex.analyze.
    _tally["vc_exc"] = {}
    _tally["vc_calls"] = 0
    try:
        _vc_cls = type(_pv.Perceiver(None)._visual_cortex) if False else None
    except Exception:
        _vc_cls = None
    try:
        import engines.perception.visual_cortex as _vcm
        for _nm in dir(_vcm):
            _o = getattr(_vcm, _nm)
            if isinstance(_o, type) and hasattr(_o, "analyze"):
                _oa = _o.analyze

                def _mk(_oa):
                    def _wrapped(self, *a, **k):
                        _tally["vc_calls"] += 1
                        # Record the SHAPE of what actually arrives. analyze() documents its input as
                        # "2D list of color integers (typically 64x64)" and unpacks grid.shape into
                        # exactly two names; if the shapes below are not all 2-D, the docstring is the
                        # bug report.
                        try:
                            import numpy as _n
                            _sh = str(_n.array(a[0]).shape) if a else "no-arg"
                        except Exception:
                            _sh = "unarrayable"
                        _tally.setdefault("vc_shapes", {})
                        _tally["vc_shapes"][_sh] = _tally["vc_shapes"].get(_sh, 0) + 1
                        try:
                            return _oa(self, *a, **k)
                        except BaseException as e:
                            # The message alone does not locate the bug. Record the DEEPEST frame
                            # inside the repo -- that is the line that actually raised.
                            import traceback as _tb
                            site = "?"
                            for fr in reversed(_tb.extract_tb(e.__traceback__)):
                                if "site-packages" not in fr.filename.lower():
                                    site = "%s:%d in %s | %s" % (
                                        os.path.basename(fr.filename), fr.lineno, fr.name,
                                        (fr.line or "")[:90])
                                    break
                            key = "%s: %s  @ %s" % (type(e).__name__, str(e)[:60], site)
                            _tally["vc_exc"][key] = _tally["vc_exc"].get(key, 0) + 1
                            raise
                    return _wrapped

                _o.analyze = _mk(_oa)
    except Exception as _e:
        _tally["vc_exc"]["PROBE-FAILED-TO-ATTACH: %s" % _e] = 1


    def _dump():
        try:
            with open("goal_probe.json", "w", encoding="utf-8") as fh:
                _json.dump(_tally, fh, indent=2)
        except Exception:
            pass
    atexit.register(_dump)
