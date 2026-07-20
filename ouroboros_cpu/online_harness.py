"""online_harness.py -- ONLINE-API DEV harness, CORRECTED to drive the EVOLVABILITY-ENGINE trunk.

Difference from the original artifact: the original drove ouroboros_integrated.OuroborosIntegrated().run(),
which uses the Kernel path and NEVER calls objective_validator.validate_multilevel -- so the evolvability
engine (residual reporter / forward-model / co-option / mint / 3-state gate / narration) never fired. This
version adds brain="submission" (the DEFAULT) drives the ACTUAL submission agent (integrated_agent.MyAgent) so dev == submission;
submission) uses -- so DEV online testing exercises the SAME brain you will submit. brain="reasonfirst" keeps
the original OuroborosIntegrated path available.

Also fixed for the RF1 work: OnlineArcAdapter now initialises the objective-keyed transition_buffer +
reasoning fields (the original __init__ skipped super().__init__), and step() appends frames to the buffer so
the forward-model residual has data. The engine's grammar `why` (set via adapter.set_reasoning) rides each
action into the replay metadata, so the scorecard shows the engine's reasoning in the composer's own grammar.

API key is read from ARC_API_KEY (or passed explicitly) and is NEVER written to disk by this module.
View a session at:  https://arcprize.org/scorecards/<scorecard_id>

Usage:
    ARC_API_KEY=... python3 online_harness.py ls20 ka59 cn04              # engine brain (default)
    ARC_API_KEY=... python3 online_harness.py --reasonfirst ls20          # old brain
or:
    import online_harness as OH; OH.run_online(["ls20"], wall_cap_s=180, brain="engine")
"""
import os, sys, time, logging
from collections import deque

import arc_agi
try:
    from arc_agi.base import OperationMode
except Exception:
    try:
        from arc_agi import OperationMode
    except Exception:
        OperationMode = None
from arcengine import GameAction, GameState
from self_model import SelfLocusModel
import grid_perception as GP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arc_modules as _AM_MOD
import ouroboros_integrated as OI

_AM = {i: getattr(GameAction, f"ACTION{i}") for i in range(1, 8)}
_AM[0] = GameAction.RESET

import time as _time
_LAST = [0.0]
_MIN_INTERVAL = float(os.environ.get("ARC_MIN_INTERVAL", "0.13"))   # ~460/min, safely under the 600/min cap


def _throttle():
    dt = _time.time() - _LAST[0]
    if dt < _MIN_INTERVAL:
        _time.sleep(_MIN_INTERVAL - dt)
    _LAST[0] = _time.time()


def _retry_none(fn, tries=4, base=0.8):
    o = None
    for i in range(tries):
        _throttle()
        try:
            o = fn()
        except Exception:
            o = None
        if o is not None:
            return o
        _time.sleep(base * (2 ** i))
    return o


class OnlineArcAdapter(_AM_MOD.ArcAdapter):
    """ArcAdapter contract over a remote (ONLINE) environment. Reuses _grid/actions/discrete_actions/step_at/
    pointer_actions from the parent; overrides construction/reset/step so the env is created online (scorecard
    + recording) and each action carries a reasoning dict into the replay. RF1: maintains an objective-keyed
    transition buffer + the reasoning side-channel the engine sets via set_reasoning()."""

    def __init__(self, game_id, arc, scorecard_id=None, save_recording=True, reasoning_fn=None):
        os.environ.setdefault("ONLY_RESET_LEVELS", "true")
        self.arc = arc
        self.game_id = game_id
        self.scorecard_id = scorecard_id
        self.save_recording = bool(save_recording)
        self._reasoning_fn = reasoning_fn
        self.env = None
        self._obs = None
        self.slm = SelfLocusModel()
        self._spec = None
        self.level_local = True
        self._api_failed = False
        self._resets_used = 0
        # RF1 + reasoning side-channel (the original __init__ omitted these):
        self.transition_buffer = deque(maxlen=8)
        self.reasoning = None
        self._fresh = False
        self._last_meta = None
        self._n_reset = 0; self._n_action = 0        # instrument reset-vs-action flow (diagnose reset storms)
        self.deadline = None                          # hard wall-clock deadline (enforced INSIDE step/reset)
        self.online = True                            # signals validate() to bound reset-and-replay passes

    def _past_deadline(self):
        return self.deadline is not None and _time.time() > self.deadline

    def _make_env(self):
        _throttle()
        return self.arc.make(self.game_id, scorecard_id=self.scorecard_id, save_recording=self.save_recording)

    def reset(self):
        import numpy as np
        if self._past_deadline():                     # wall cap hit -> do NOT hit the API; unwind the composer
            self._api_failed = True
            return self._grid(self._obs) if self._obs is not None else np.zeros((64, 64), dtype=int)
        # ONE online session per game. make() ONLY when no env yet; every subsequent reset() the composer issues
        # (abduce probes, descend restarts, interaction probe) is a LEVEL-LOCAL restart on the SAME session --
        # never a fresh make(). Offline the composer resets very frequently (free); online a make()-per-reset
        # spawns a new remote session each time (the reset storm). Reusing the one session is the fix.
        if self.env is None:
            self.env = self._make_env()
            o = _retry_none(lambda: self.env.reset(), tries=5, base=1.2)
        else:
            # RESETS DISABLED across the board (user directive): the system does not yet know when a restart is
            # rational, and mid-game resets ruin the play process. A reset() on an EXISTING session is now a NO-OP --
            # the game plays ONE continuous life per session (WIN or GAME_OVER ends it; no restart). The initial
            # make() above is unaffected. Re-enable per-adapter via `adapter.resets_enabled = True` once the composer
            # can decide resets rationally.
            if not getattr(self, "resets_enabled", False):
                return self._grid(self._obs) if self._obs is not None else np.zeros((64, 64), dtype=int)
            o = _retry_none(lambda: self.env.step(GameAction.RESET), tries=5, base=1.2)
        self._n_reset += 1
        if o is None:
            self._api_failed = True
            raise RuntimeError("online reset returned None after retries (rate limit / server)")
        self._obs = o
        self._lvl0 = getattr(o, "levels_completed", 0) or 0
        self._reward = False
        self.slm.locus = None
        f = np.array(o.frame); raw = (f[-1] if f.ndim == 3 else f) if f.size else np.zeros((64, 64), dtype=int)
        acts = [_AM[int(a)] for a in (o.available_actions or [])]
        pure_click = (GameAction.ACTION6 in acts) and not any(a != GameAction.ACTION6 for a in acts)
        self._spec = None   # reason at NATIVE 64x64; logical-grid spec is unused (removed to prevent coord regressions)
        g = self._grid(o)
        try:
            self.transition_buffer.append(g.copy())      # seed the buffer for this objective
        except Exception:
            pass
        return g

    def _reasoning_for(self, action):
        # ENGINE path (the ONLINE brain): unify the grammar `why` (set via set_reasoning) into the SAME
        # decision_reasoning payload shape as every other path, and stamp the re-evaluated dynamics REGIME (from the
        # self-locus model: 'is one of these objects ME?'), so ALL 25 games narrate identically online -- no silent
        # actions, no per-path format drift. Fallback to the raw meta if anything fails -> never lose reasoning.
        base = None
        if getattr(self, "reasoning", None):
            base = dict(self.reasoning, decision_point=bool(getattr(self, "_fresh", False)))
            self._fresh = False
        elif self._reasoning_fn is not None:
            try:
                base = self._reasoning_fn(action, self)
            except Exception:
                base = None
        try:
            import regime_factory as _RF
            slm = getattr(self, "slm", None)
            coh = slm.coherent_actions() if slm is not None else {}
            has_self = slm is not None and slm.locus is not None and len(coh) > 0
            avail = None
            try:
                aa = getattr(self._obs, "available_actions", None)
                avail = set(int(getattr(a, "value", a)) for a in aa) if aa else None
            except Exception:
                avail = None
            clicks_only = bool(avail) and avail.issubset({6, 7})
            steps = int(getattr(self, "_n_action", 0))
            n_arg = (1 if has_self else (0 if (clicks_only or steps >= 50) else None))
            regime = (base or {}).get("regime") or _RF.SHARED.control_regime.classify(n_arg, clicks_only, steps)
            m = base or {}
            payload = _RF.SHARED.decision_reasoning.build(
                regime, action,
                frame_read=(("controllable at %s (co-moves with %d action(s))" % (slm.agent_cell(), len(coh))) if has_self
                            else (("target := %s" % m.get("target")) if m.get("target")
                            else ("click/actuator dynamics -- no controllable after %d steps" % steps
                                  if regime == "actuator" else "probing for the controllable (co-movement not established)"))),
                rule_hypothesis=(m.get("objective") or m.get("grammar_gloss") or m.get("relation")
                                 or "(provisional objective -- a bet tested by acting, confirmed only by a win)"),
                expect="advances the provisional objective; forward-model residual falls if the read is right",
                disproof="residual stays high, or the controllable/roles behave unlike this read -> RE-DERIVE mechanics",
                step=steps,
                extra={k: m.get(k) for k in ("grammar_steps", "grammar", "decision", "pass", "source", "relation",
                                             "decision_point") if m.get(k) is not None})
            return payload
        except Exception:
            return base                                        # fallback: keep whatever reasoning existed (no regression)

    def _click_xy(self, r, c):
        """Map an agent-grid (row, col) click to the raw ACTION6 payload. The agent reasons on a DOWNSCALED logical
        grid (vc33 is 12x12); ACTION6 takes 0-63 coords on the raw 64x64 frame, x=horizontal(col), y=vertical(row).
        So scale up by raw/agent AND transpose, clicking the CENTRE of the agent cell. This is the fix for clicks that
        were landing bunched in the top-left (unscaled) instead of on the objects."""
        import numpy as np
        try:
            ag = self._grid(self._obs); aH, aW = ag.shape
            raw = np.array(self._obs.frame); raw = raw[-1] if raw.ndim == 3 else raw; rH, rW = raw.shape
        except Exception:
            rH = rW = 64; aH = aW = 64
        x = int((c + 0.5) * rW / max(1, aW)); y = int((r + 0.5) * rH / max(1, aH))
        return {"x": min(max(x, 0), rW - 1), "y": min(max(y, 0), rH - 1)}

    def step(self, action):
        import numpy as np
        if self._past_deadline():                              # ONLY the wall-clock deadline ends the session. A single
            g = self._grid(self._obs) if self._obs is not None else np.zeros((64, 64), dtype=int)   # 400/send error must
            return g, 0.0, True, {"state": "DEADLINE"}          # NOT latch the whole session dead.
        # CONFIRMED GAME_OVER: sending ANY action to a game-over session returns 400. That is the ONE sanctioned reason
        # to RESET (start a fresh session) -- the exception to reset-is-deliberate. Do that instead of 400-hammering a
        # dead session (which is what made btn6/btn7 'fail' -- they were sent AFTER the level had already ended).
        try:
            _go = getattr(self._obs, "state", None) == GameState.GAME_OVER
        except Exception:
            _go = False
        if _go:
            g0 = self._grid(self._obs) if self._obs is not None else np.zeros((64, 64), dtype=int)
            try:
                o = _retry_none(lambda: self.env.step(GameAction.RESET), tries=3, base=0.8)   # allowed: game-over confirmed
                if o is not None:
                    self._obs = o; self._lvl0 = getattr(o, "levels_completed", 0) or 0; self._n_reset += 1
                    return self._grid(o), 0.0, True, {"state": "GAME_OVER_RESET"}   # done: fresh session began
            except Exception:
                pass
            return g0, 0.0, True, {"state": "GAME_OVER"}        # couldn't reset -> report game-over, stop acting
        reasoning = self._reasoning_for(action)                # transient 400 on one button into a session-wide DEADLINE
        self._n_action += 1                                    # cascade, starving every action after it).
        prev = self._grid(self._obs) if self._obs is not None else None
        if isinstance(action, tuple) and action[0] == "click":
            _xy = self._click_xy(int(action[1]), int(action[2]))    # scale downscaled(r,c) -> raw 64x64, x=col,y=row
            o = _retry_none(lambda: self.env.step(GameAction.ACTION6, data=_xy,
                                                  reasoning=reasoning), tries=1, base=0.6)
        else:
            o = _retry_none(lambda: self.env.step(action, reasoning=reasoning), tries=3, base=0.6)
        if o is None and self._resets_used < 3 and not getattr(self, "_recovering", False) and getattr(self, "resets_enabled", False):
            self._recovering = True
            try:
                self._resets_used += 1
                _retry_none(lambda: self.env.step(GameAction.RESET), tries=2, base=0.8)
                if isinstance(action, tuple) and action[0] == "click":
                    o = _retry_none(lambda: self.env.step(GameAction.ACTION6, data=self._click_xy(int(action[1]), int(action[2])), reasoning=reasoning), tries=2, base=0.6)
                else:
                    o = _retry_none(lambda: self.env.step(action, reasoning=reasoning), tries=2, base=0.6)
            except Exception:
                o = None
            finally:
                self._recovering = False
        if o is None:                                          # transient send failure (e.g. 400) -- report it for THIS
            g = self._grid(self._obs) if self._obs is not None else np.zeros((64, 64), dtype=int)   # action only; do NOT
            return g, 0.0, False, {"state": "API_NONE"}         # latch _api_failed -> the NEXT action retries the server fresh
        self._obs = o
        cur = self._grid(o)
        try:
            self.transition_buffer.append(cur.copy())    # RF1: record the frame for the forward-model residual
        except Exception:
            pass
        if prev is not None and not isinstance(action, tuple) and prev.shape == cur.shape:
            self.slm.update(prev, action, cur)
        lvl = getattr(o, "levels_completed", 0) or 0
        rew = 1.0 if lvl > self._lvl0 else 0.0
        if lvl > self._lvl0:
            self._reward = True; self._lvl0 = lvl
        if o.state == GameState.WIN:
            self._reward = True
        # A LEVEL-win keeps state NOT_FINISHED and the game AUTO-ADVANCES to the next level -- it must NOT be treated
        # as episode-end, or the pursuit resets on the winning action and undoes the win (the "keeps resetting" loop).
        # Only a full-game WIN or a GAME_OVER (death / max actions) ends the episode. The level-win rides as `rew`.
        done = o.state in (GameState.WIN, GameState.GAME_OVER)
        return self._grid(o), rew, done, {"state": o.state.name}


# ---------------- reasonfirst reasoning provider (unchanged path) ----------------
def _reasoning_snapshot(oi, action, ad):
    grid = None
    try:
        grid = OI._read(ad)
    except Exception:
        grid = None
    return OI.reasoning_snapshot(oi, action, grid=grid)


def _make_reasoning_fn(oi, logger=None):
    def fn(action, ad):
        r = _reasoning_snapshot(oi, action, ad)
        if logger is not None:
            d = r.get("decision") or {}
            logger.info("act=%s phase=%s engine=%s rationale=%s",
                        r.get("action"), r.get("phase"), d.get("engine"), d.get("rationale"))
        return r
    return fn


def _build_logger(verbose=True):
    logger = logging.getLogger("ouroboros_online")
    logger.setLevel(logging.INFO if verbose else logging.WARNING)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s [ouro] %(message)s", "%H:%M:%S"))
        logger.addHandler(h)
    logger.propagate = False
    return logger


# ===================================================================================================
def _ensure_agents_stub():
    """integrated_agent / v18 / my_agent do `from agents.agent import Agent`, which the COMPETITION FRAMEWORK provides at
    Kaggle rerun but is ABSENT in the online dev environment. Without this the submission brain cannot even be imported
    here (ModuleNotFoundError: 'agents'), which is why driving it online silently produced nothing. Inject the same
    minimal stub the offline closure tests use so the submission brain is importable + drivable in dev; the REAL base is
    used at actual submission (this only fires when 'agents' is missing)."""
    import sys as _sys, types as _types
    try:
        import agents.agent  # noqa: F401  -- present at Kaggle rerun; use the real base
        return
    except Exception:
        pass
    _ag = _types.ModuleType("agents"); _ag.__path__ = []
    _aa = _types.ModuleType("agents.agent")

    class Agent:
        def __init__(self, *a, **kw):
            self.game_id = kw.get("game_id", "stub"); self.frames = []
    class Playback:
        pass
    _aa.Agent = Agent; _aa.Playback = Playback; _ag.agent = _aa
    _sys.modules["agents"] = _ag; _sys.modules["agents.agent"] = _aa


# SUBMISSION brain (the ONLY online path) -- drive the ACTUAL submission agent so dev == submission.
# ===================================================================================================
def play_game_submission(arc, game_id, scorecard_id, logger, wall_cap_s=300, save_recording=True):
    """Drive the ACTUAL submission agent (integrated_agent.MyAgent) against the online game via the standard
    choose_action / is_done loop. This makes ONLINE DEV TESTING IDENTICAL to what gets submitted: the same regime
    ROUTING (v18 for movers, composer for click/actuator), the same unified reasoning on every action, the same composer
    bridge. It REPLACES the bare-engine path (validate_multilevel directly), which diverged from submission on every
    mover game (it ran validate_multilevel for movers where submission runs v18)."""
    _ensure_agents_stub()                                      # dev has no 'agents' framework -> stub before importing
    import integrated_agent as IA
    from arcengine import GameAction
    env = arc.make(game_id, scorecard_id=scorecard_id, save_recording=save_recording)
    try:
        agent = IA.MyAgent(game_id=game_id, card=scorecard_id)
    except Exception:
        agent = IA.MyAgent(game_id=game_id)
    t0 = time.time(); deadline = t0 + wall_cap_s
    logger.info("=== %s: SUBMISSION brain (integrated_agent.MyAgent) online session ===", game_id)
    o = _retry_none(lambda: env.reset(), tries=5, base=1.2)
    frames = [o] if o is not None else []
    max_level = 0; outcome = "submission-complete"; guard = 0
    cap = int(getattr(agent, "MAX_ACTIONS", 10000))            # 10k per-game cap so a stuck game can't run unbounded
    try:
        while o is not None and time.time() < deadline and guard < cap:
            guard += 1
            try:
                max_level = max(max_level, int(getattr(o, "levels_completed", 0) or 0))
            except Exception:
                pass
            try:
                if agent.is_done(frames, o):
                    outcome = "done"; break
            except Exception:
                pass
            action = agent.choose_action(frames, o)            # the REAL brain: routes + attaches unified reasoning
            if action is None:
                break
            reasoning = getattr(action, "reasoning", None)     # rides to the recording (HELM #6: never silent)
            # CLICK CONTRACT: env.step reads click x,y from the `data` param, NOT from the enum. For ACTION6 pull the
            # coords off the returned action's action_data and pass them through, else the server 500s on a coord-less click.
            step_data = None
            if getattr(action, "value", None) == 6:
                _ad = getattr(action, "action_data", None)
                if _ad is not None:
                    step_data = {"x": int(getattr(_ad, "x", 0) or 0), "y": int(getattr(_ad, "y", 0) or 0)}
            o = _retry_none(lambda: env.step(action, data=step_data, reasoning=reasoning), tries=3, base=0.6)
            if o is not None:
                frames.append(o); frames = frames[-16:]        # bound memory; agent keeps its own history
        if o is not None:
            try:
                max_level = max(max_level, int(getattr(o, "levels_completed", 0) or 0))
            except Exception:
                pass
    except Exception as e:
        logger.warning("%s: submission run error %s: %s", game_id, type(e).__name__, str(e)[:120])
        outcome = "error"
    dt = round(time.time() - t0)
    logger.info("=== %s: done outcome=%s levels=%s steps=%s %ss ===", game_id, outcome, max_level, guard, dt)
    return dict(game=game_id, max_level=max_level, outcome=outcome, steps=guard, seconds=dt)


# BARE-ENGINE path -- DISABLED. Driving validate_multilevel directly diverged from the submission brain (it ran
# validate_multilevel for mover games where the submission runs v18), so online dev results did not reflect submission.
# It is now unreachable: run_online drives play_game_submission. Kept only to fail LOUDLY if something calls it.
def play_game_engine(*a, **k):
    raise RuntimeError("play_game_engine (bare validate_multilevel) is DISABLED: the online path MUST drive the "
                       "submission agent (integrated_agent.MyAgent) so dev == submission. Use play_game_submission.")


def _play_game_engine_legacy(arc, game_id, scorecard_id, logger, wall_cap_s=300, save_recording=True):
    import objective_validator as OV
    ad = OnlineArcAdapter(game_id, arc, scorecard_id=scorecard_id, save_recording=save_recording,
                          reasoning_fn=None)                      # engine sets reasoning via set_reasoning()
    ad.deadline = time.time() + wall_cap_s                        # HARD cap enforced inside step/reset
    t0 = time.time()
    logger.info("=== %s: ENGINE brain (validate_multilevel) online session ===", game_id)
    outcome = "engine-complete"; levels = 0; evo = {}; best_levels = 0; attempts = 0
    MAX_ATTEMPTS = 10
    try:
        while attempts < MAX_ATTEMPTS and time.time() < ad.deadline - 2:
            attempts += 1
            _tb = max(5, int(ad.deadline - time.time()))
            res = OV.validate_multilevel(ad, budget=3000, max_hyps=4, max_levels=40, time_budget=_tb)
            levels = res.get("levels_completed", 0)
            evo = res.get("evolvability") or {}
            if levels <= best_levels:
                break                                         # attempt made NO new progress -> stuck, stop re-attempting
            best_levels = levels
            logger.info("[re-attempt] %s: reached level %d on attempt %d; resetting to push the frontier",
                        game_id, levels, attempts)
            if time.time() >= ad.deadline - 2:
                break
            # RE-ATTEMPT (component 3): the game ended with PROGRESS. Reset -- re-enabled ONLY for this progress-seeking
            # re-attempt (this is 'get deeper into the game', NOT the banned retry-the-same-level reset) -- and re-play.
            # The per-game solution cache fast-replays the already-beaten levels, so this attempt reaches one deeper
            # with budget to spare for the new frontier level.
            ad.resets_enabled = True
            g = ad.reset()
            ad.resets_enabled = False
            if g is None:
                break
        levels = best_levels
    except Exception as e:
        logger.warning("%s: engine run error %s: %s", game_id, type(e).__name__, str(e)[:120])
        outcome = "error"; levels = best_levels
    dt = round(time.time() - t0)
    # surface the engine's grammar narration (the WHY) + escalations/promotions to the proctor
    for line in (evo.get("narration") or [])[-24:]:
        logger.info("[engine] %s", line)
    esc = evo.get("escalations") or []; promoted = evo.get("promoted") or {}
    if esc:
        logger.info("[engine] escalations (perception-gap reports, NOT minted): %d", len(esc))
    if promoted:
        logger.info("[engine] promoted molecules (co-option library growth): %s", list(
            (v.get("name") if isinstance(v, dict) else v) for v in promoted.values()))
    logger.info("=== %s: done outcome=%s levels=%s %ss ===", game_id, outcome, levels, dt)
    return dict(game=game_id, max_level=levels, outcome=outcome, seconds=dt,
                n_reset=getattr(ad, "_n_reset", 0), n_action=getattr(ad, "_n_action", 0),
                fired=int(evo.get("fired") or 0), min_disc=getattr(ad, "_min_disc", None),
                dynamics=getattr(ad, "_dynamics", None),
                sim_trusted=bool((getattr(ad, "_sim_rank", None) or {}).get("trustworthy")),
                explore_term=getattr(ad, "_explore_term", None),
                narration=(evo.get("narration") or [])[-24:], escalations=len(esc),
                promoted=list((v.get("name") if isinstance(v, dict) else v) for v in promoted.values()),
                radius=evo.get("radius"))


# ===================================================================================================
# REASONFIRST brain (original path) -- OuroborosIntegrated; kept for comparison.
# ===================================================================================================
def play_game_reasonfirst(arc, game_id, scorecard_id, logger, wall_cap_s=180, max_cycles=256, max_steps=120,
                          save_recording=True):
    oi = OI.OuroborosIntegrated()
    ad = OnlineArcAdapter(game_id, arc, scorecard_id=scorecard_id, save_recording=save_recording,
                          reasoning_fn=_make_reasoning_fn(oi, logger))
    t0 = time.time(); guard = 0; stall = 0; last_hist = -1; max_level = 0; outcome = None
    logger.info("=== %s: REASONFIRST brain online session ===", game_id)
    while guard < max_cycles:
        if (time.time() - t0) > wall_cap_s:
            outcome = "wall-cap"; break
        guard += 1
        try:
            out = oi.run(ad, max_steps=max_steps)
        except Exception as e:
            logger.warning("%s: run error %s: %s", game_id, type(e).__name__, str(e)[:80]); outcome = "error"; break
        oc = out.get("outcome") if isinstance(out, dict) else None
        hl = out.get("history_len", 0) if isinstance(out, dict) else 0
        try:
            max_level = max(max_level, ad._lvl0 if isinstance(ad._lvl0, int) else 0)
        except Exception:
            pass
        if oc in ("deduction-exhausted", "inert"):
            outcome = oc; break
        if (not (isinstance(out, dict) and out.get("objective_committed"))) and hl == last_hist:
            stall += 1
        else:
            stall = 0
        last_hist = hl
        if stall >= 8:
            outcome = "stall"; break
    else:
        outcome = "max-cycles"
    dt = round(time.time() - t0)
    logger.info("=== %s: done outcome=%s levels=%s cycles=%s %ss ===", game_id, outcome, max_level, guard, dt)
    return dict(game=game_id, max_level=max_level, outcome=outcome, cycles=guard, seconds=dt)


def run_online(game_ids, api_key=None, tags=None, wall_cap_s=300, max_steps=120, save_recording=True,
               verbose=True, brain="submission"):
    """Open one scorecard, play each game online, close and report. brain='engine' (default) drives
    validate_multilevel (the submission trunk + evolvability engine); brain='reasonfirst' drives the old
    OuroborosIntegrated path. Returns (scorecard_id, view_url, results)."""
    key = api_key or os.environ.get("ARC_API_KEY", "")
    if not key:
        raise RuntimeError("No API key: set ARC_API_KEY or pass api_key=...")
    logger = _build_logger(verbose)
    # LAYER-2 WIRING (orchestrator direction): register the Layer-1 controllers into the flow's hook registry once,
    # before any game runs. This is the only place the two layers connect; the flow reaches a controller via
    # OV.controller_hook(name) and never imports autonomy_controllers, keeping the dependency graph acyclic.
    try:
        import autonomy_controllers as _AC
        _AC.wire()
    except Exception as _e:
        logger.info("controller wiring skipped: %s", _e)
    arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE, arc_api_key=key, logger=logger)
    scorecard_id = arc.open_scorecard(tags=tags or ["ouroboros", "online-test", brain])
    view_url = f"https://arcprize.org/scorecards/{scorecard_id}"
    logger.info("opened scorecard %s  (brain=%s)", scorecard_id, brain)
    results = []
    try:
        for gm in game_ids:
            if brain == "reasonfirst":
                results.append(play_game_reasonfirst(arc, gm, scorecard_id, logger, wall_cap_s=wall_cap_s,
                                                     max_steps=max_steps, save_recording=save_recording))
            else:
                # ALL non-reasonfirst brains (incl. legacy "engine") drive the ACTUAL submission agent -> dev ==
                # submission. The bare-engine path (validate_multilevel directly) is never taken.
                results.append(play_game_submission(arc, gm, scorecard_id, logger, wall_cap_s=wall_cap_s,
                                                    save_recording=save_recording))
    finally:
        try:
            final = arc.close_scorecard(scorecard_id)
            logger.info("closed scorecard %s  score=%s", scorecard_id, getattr(final, "score", None))
        except Exception as e:
            logger.warning("close_scorecard failed: %s", e)
    print("\n==== ONLINE SESSION (brain=%s) ====" % brain)
    for r in results:
        print(f"  {r['game']:14} level={r['max_level']} outcome={r['outcome']} {r['seconds']}s"
              + (f" promoted={r.get('promoted')}" if r.get('promoted') else ""))
    print(f"  view: {view_url}")
    return scorecard_id, view_url, results


if __name__ == "__main__":
    args = sys.argv[1:]
    brain = "engine"
    if args and args[0] == "--reasonfirst":
        brain = "reasonfirst"; args = args[1:]
    games = args or ["ls20"]
    run_online(games, brain=brain)
