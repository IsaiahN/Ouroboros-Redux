# MyAgent — wraps the Ouroboros composer (objective_validator.validate) in the ARC-AGI-3-Agents
# framework contract. The composer is PULL-model (it calls adapter.reset/step); the framework is
# PUSH-model (it calls choose_action and applies the result). We invert control with a daemon thread
# behind a queue-backed adapter, so the VALIDATED composer code runs unchanged.
import os, sys, queue, threading
from collections import deque
for _p in ((os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()), "/kaggle/working"):
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import numpy as np
from arcengine import GameAction
try:
    from arcengine import ActionInput
except Exception:
    ActionInput = None
try:
    from agents.agent import Agent           # provided by the competition framework at rerun
    _HARNESS = True
except Exception:                            # local / offline: minimal stub
    _HARNESS = False
    class Agent:
        def __init__(self, *a, **kw):
            self.game_id = kw.get("game_id", "stub"); self.frames = []; self.arc_env = None

from objective_validator import validate, validate_multilevel    # composer entry-points (single + multi-level)


def _delta_payload(agent, payload):
    """PER-FRAME delta compression for the reasoning that rides on EVERY action into the frame data. Between two
    decisions the composer re-stamps the SAME payload onto ~50 frames, and constant fields (expect/disproof) repeat on
    every frame of the whole game -- so the recording is mostly duplicated old data. This collapses that: any field
    UNCHANGED from the previous frame becomes an em-dash '\u2014', and a frame whose payload is entirely unchanged becomes
    {'repeat':'\u2014','same_as_prev_x':N}. A spammed/duplicate action therefore reads as a run of bare dashes, and only
    genuine changes carry data. Compares by repr (robust to in-place mutation). Gated by OURO_FRAME_DELTA."""
    if os.environ.get("OURO_FRAME_DELTA", "1") != "1" or not isinstance(payload, dict):
        return payload
    prev = getattr(agent, "_prev_payload_reprs", None)
    cur = {k: repr(v) for k, v in payload.items()}
    if prev is not None and cur == prev:                       # nothing changed at all -> one dash + running count
        n = getattr(agent, "_payload_repeat", 0) + 1
        agent._payload_repeat = n; agent._prev_payload_reprs = cur
        return {"repeat": "\u2014", "same_as_prev_x": n}
    agent._payload_repeat = 0
    out = {}
    for k, v in payload.items():
        out[k] = "\u2014" if (prev is not None and prev.get(k) == cur[k]) else v   # unchanged field -> em-dash
    agent._prev_payload_reprs = cur
    return out

import grid_perception as GP                  # logical-grid perception (adapter transform)

_TIMEOUT = 30.0                              # per-step handshake timeout (turn-based; generous)
_ID2GA = {0: GameAction.RESET, 1: GameAction.ACTION1, 2: GameAction.ACTION2, 3: GameAction.ACTION3,
          4: GameAction.ACTION4, 5: GameAction.ACTION5, 6: GameAction.ACTION6}


def _state_name(fd):
    s = getattr(fd, "state", "")
    return getattr(s, "name", str(s)).upper()


def _grid_of(fd):
    try:
        f = np.array(fd.frame)
        if f.size == 0:
            return None
        return f[-1] if f.ndim == 3 else f
    except Exception:
        return None


class _QueueAdapter:
    """The EnvAdapter contract our composer expects, bridged to the framework over two queues.
    Runs in the composer thread: each reset()/step() puts the desired action on action_q and blocks
    on frame_q for the resulting frame (supplied by MyAgent.choose_action on the main thread)."""
    def __init__(self, action_q, frame_q):
        self.action_q = action_q; self.frame_q = frame_q
        self._obs = None; self._reward = False; self._lvl0 = 0
        self._last_grid = np.zeros((64, 64), dtype=int); self._spec = None
        # REASONING SIDE-CHANNEL (free lane): the composer/engine sets a grammar-legible `why` here; each
        # emitted action carries it on GameAction.reasoning (the sanctioned metadata lane the sample agents use),
        # so the event grammar rides the real action frame WITHOUT spending a ghost action. decision_point marks
        # the FIRST action of each objective (the commit); follow-through actions carry the same why, flag False.
        self.reasoning = None            # dict|None: the current objective's rationale
        self._fresh = False              # True until the first action of a new objective is emitted
        self._last_meta = None           # the meta paired with the action just put on the queue
        self.transition_buffer = deque(maxlen=8)   # RF1: objective-keyed frame buffer for prediction-error residual

    def set_reasoning(self, meta):
        """Called by the engine (or any pass) at a DECISION POINT: attach this rationale to the actions that
        follow, marking the first as the decision point. A FRESH objective also resets the transition buffer
        (RF1): the residual is prediction-error within ONE objective's pursuit, never across an objective switch."""
        self.reasoning = dict(meta) if isinstance(meta, dict) else {"why": str(meta)}
        self._fresh = True
        self.transition_buffer = deque([self._last_grid.copy()], maxlen=8)   # objective-keyed buffer restart

    def _ingest(self, fd):
        self._obs = fd
        g = _grid_of(fd)
        if g is not None:
            if self._spec is not None:
                g = GP.downsample(g, self._spec)             # present the board's NATIVE logical grid
            self._last_grid = g
        lvl = getattr(fd, "levels_completed", 0) or 0
        st = _state_name(fd)
        rew = 1.0 if lvl > self._lvl0 else 0.0
        if lvl > self._lvl0:
            self._reward = True; self._lvl0 = lvl
        if "WIN" in st:
            self._reward = True
        done = ("WIN" in st or "GAME_OVER" in st) or self._reward
        try:
            self.transition_buffer.append(self._last_grid.copy())     # RF1: record the frame for the buffer
        except Exception:
            pass
        return self._last_grid, rew, done

    def _exchange(self, action):
        # pair the current rationale with THIS action; first action of an objective is the decision point
        if self.reasoning is not None:
            self._last_meta = dict(self.reasoning, decision_point=bool(self._fresh))
            self._fresh = False
        else:
            self._last_meta = None
        self.action_q.put(action)
        fd = self.frame_q.get(timeout=_TIMEOUT)      # raises queue.Empty on desync -> ends composer
        return self._ingest(fd)

    def reset(self):
        self._reward = False; self._spec = None
        # RESET wipes the game and discards progress. It is legitimate ONLY at true game-start (no frame yet) or after
        # GAME_OVER. Mid-play it is a NO-OP that keeps the board -- the composer continues from where it is.
        #
        # RULED [Isaiah]: reset is shadow-banned during active play. Using it skillfully mid-level -- as a deliberate
        # return to a known state -- requires an autonomy the agent does not yet have; right now a mid-play reset just
        # throws the level away. Measured: 27 destructive resets in 303 actions, every one at state=NOT_FINISHED,
        # because an earlier gate let it fire whenever `_lvl == 0` (i.e. on the FIRST level -- where the whole game is
        # spent). That clause is the bug. The only safe conditions are game-start and GAME_OVER.
        _st = _state_name(self._obs) if self._obs is not None else ""
        # RESET BAN [Isaiah, extended]: a RESET is legitimate ONLY to START the game the first time (no frame yet /
        # NOT_STARTED / NOT_PLAYED, before any level has been played) or once reset has been EARNED. The RESTART-after-
        # GAME_OVER path is now BANNED too: reaching level 1 and then resetting back to level 0 DISCARDS the earned
        # progress -- "nothing to lose" was wrong once the agent has cleared a level. So GAME_OVER no longer auto-resets;
        # the session ends at GAME_OVER (one earned life -- see is_done) unless reset_earned. The MID-PLAY reset
        # (NOT_FINISHED with a live board) stays banned as before.
        # EARNED-CAPABILITY gate: the ban lifts ONLY when the ladder gauge has set `reset_earned` -- which requires
        # corroborated-L4 (a composed primitive that held across a level) AND the agent reasoning its own way to needing
        # reset. False until genuinely earned. This is the graduation bar wired to the measured signal, never hardcoded.
        _earned = False
        try:
            import objective_validator as _OVr
            _earned = bool((_OVr._GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("reset_earned"))
        except Exception:
            _earned = False
        _boundary = (self._obs is None or "NOT_STARTED" in _st or "NOT_PLAYED" in _st or _earned)
        if _boundary:
            g, _, _ = self._exchange(("__reset__",))         # start / restart only -- never mid-play (unless earned)
        # else active play -> NO-OP: keep the board and every cleared level, re-perceive from the current frame
        acts = self.actions()                                # pure click-to-place family only
        if (GameAction.ACTION6 in acts) and not any(a != GameAction.ACTION6 for a in acts):
            raw = _grid_of(self._obs)
            if raw is not None:
                self._spec = GP.detect_grid(raw)
        self._lvl0 = getattr(self._obs, "levels_completed", 0) or 0
        self._reward = False
        return self._grid(self._obs)

    def step(self, action):
        g, r, d = self._exchange(action)
        return g, r, d, {"state": _state_name(self._obs)}

    def satisfied(self):
        return self._reward

    def actions(self):
        av = getattr(self._obs, "available_actions", None) or []
        out = []
        for a in np.array(av).ravel().tolist():
            ga = _ID2GA.get(int(a))
            if ga is not None:
                out.append(ga)
        return out

    def discrete_actions(self):
        return [a for a in self.actions() if a != GameAction.ACTION6]

    def pointer_actions(self):
        return ["click"] if GameAction.ACTION6 in self.actions() else []

    def step_at(self, kind, r, c):
        if kind == "click":
            if self._spec is not None:                       # logical cell -> frame-pixel centre
                fr, fc = GP.cell_to_frame(int(r), int(c), self._spec)
                return self.step(("click", int(fc), int(fr)))
            return self.step(("click", int(c), int(r)))      # ARC convention x=col, y=row
        raise ValueError(kind)

    def _grid(self, o):
        g = _grid_of(o) if o is not None else None
        if g is not None and self._spec is not None:
            g = GP.downsample(g, self._spec)
        return g if g is not None else self._last_grid


class MyAgent(Agent):
    # Scaled for the REAL ARC harness (8h RTX 5090, offline). The sandbox's small caps (max_hyps 4,
    # ~1500 budget, 30s) were platform limits, not these. NOTE on RHAE scoring: per-level score is
    # (human_actions / AI_actions)^2 capped at 1.0, with a per-level action cutoff -- so a larger ACTION
    # budget buys coverage but NOT efficiency; the real harness's action cutoff bounds it regardless.
    MAX_ACTIONS = 10000                                  # safety cap only; the harness action-cutoff + time govern
    BUDGET = 15000                                       # per-candidate Go-Explore floor (adaptive: extends while improving)
    MAX_HYPS = 40                                        # objective hypotheses to try (coverage); early winners still resolve first
    PER_GAME_SECONDS = 480                               # WALL-CLOCK guard per game (kept: total must fit 8h across all games)
    PER_LEVEL_ACTIONS = 500                             # DIAGNOSTIC per-level action cap: most levels fall in a few hundred
                                                         # moves, so >1000 on one level means the agent is stuck/spamming ->
                                                         # stop and surface it rather than burn the whole run. Resets each level.

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.action_q = queue.Queue(); self.frame_q = queue.Queue()
        self.adapter = _QueueAdapter(self.action_q, self.frame_q)
        self._thread = None; self._started = False; self._done = False; self._acts = 0; self._t0 = None

    def _run_composer(self):
        try:
            # Pursue FULL game completion across levels (RHAE weights later levels more); bounded by wall-clock.
            validate_multilevel(self.adapter, budget=self.BUDGET, max_hyps=self.MAX_HYPS,
                                time_budget=self.PER_GAME_SECONDS * 0.9)
        except Exception as _e:
            # DO NOT SWALLOW. This `except: pass` made every composer crash look like a quiet, early finish: the run
            # reports `actions=49, epochs=0` and nothing anywhere says a traceback happened. Two whole diagnoses were
            # spent theorising about CPU cost for a run that had simply DIED. A silent failure is worse than a loud
            # one by exactly the amount of time it takes to find it.
            import os as _os, traceback as _tb
            self._composer_error = _tb.format_exc()
            if _os.environ.get("OURO_LOUD", "1") == "1":
                import sys as _sys
                print("COMPOSER DIED: %s" % _e, file=_sys.stderr)
                _tb.print_exc(file=_sys.stderr)
        finally:
            self._done = True
            self.action_q.put(("__end__",))


    def _complex(self, x, y):
        ga = GameAction.ACTION6
        if hasattr(ga, "set_data"):
            try:
                ga.set_data({"x": int(x), "y": int(y)})   # mutate the enum in place; env.step reads action_data
                return ga                                  # return the ENUM (.value/.name); ComplexAction crashes step
            except Exception:
                pass
        if ActionInput is not None:
            return ActionInput(id=GameAction.ACTION6, x=int(x), y=int(y))
        return ga

    def _to_framework(self, a):
        if isinstance(a, tuple) and a:
            if a[0] == "click":
                return self._complex(int(a[1]), int(a[2]))
            if a[0] == "__reset__":
                return GameAction.RESET
        return a                                          # already a GameAction

    def _next(self, default):
        try:
            a = self.action_q.get(timeout=_TIMEOUT)
        except queue.Empty:
            return default
        if isinstance(a, tuple) and a and a[0] == "__end__":
            self._done = True
            return default
        ga = self._to_framework(a)
        # ride the grammar `why` on the real action via the sanctioned metadata lane (sample agent: action.reasoning=...).
        # UNIFIED with the mover path: route through SHARED.decision_reasoning so the payload shape is IDENTICAL across
        # all 25 games (consistent reasoning communication), while folding in the composer's rich grammar so nothing is
        # lost. Fallback to the raw meta if anything fails -> never regress the path that already narrates.
        meta = getattr(self.adapter, "_last_meta", None)
        if hasattr(ga, "reasoning"):
            try:
                import regime_factory as _RF
                m = dict(meta) if isinstance(meta, dict) else ({"why": str(meta)} if meta is not None else {})
                payload = _RF.SHARED.decision_reasoning.build(
                    regime=m.get("regime", "unknown"), action=ga,
                    frame_read=(m.get("target") and ("target := %s" % m.get("target")))
                               or "(exact objects/roles from the descriptor; chrome excluded)",
                    rule_hypothesis=m.get("objective") or m.get("grammar_gloss") or m.get("relation")
                               or "(provisional actuator objective -- a bet tested by acting, confirmed only by a win)",
                    expect="the operated object changes as the forward-model predicts; residual falls if the read is right",
                    disproof="forward-model residual stays high, or roles behave unlike the read -> RE-DERIVE mechanics",
                    step=m.get("step"),
                    extra={"grammar_steps": m.get("grammar_steps"), "decision": m.get("decision"),
                           "pass": m.get("pass"), "source": m.get("source", "composer")})
                ga.reasoning = _delta_payload(self, payload)   # PER-FRAME delta: dash every field unchanged since the
            except Exception:
                try:
                    if meta is not None:
                        ga.reasoning = dict(meta)
                except Exception:
                    pass
        return ga

    def _safe_default(self, fd):
        """A NON-destructive, AVAILABLE action -- never RESET, never click. RESET wipes the board and is legitimate ONLY
        at game-start or after GAME_OVER; using it as a mid-game default (slow composer / spent budget) resets the state
        so no level-2 logic can ever shake out. This returns a real move from the frame's available_actions instead."""
        try:
            avs = set(getattr(fd, "available_actions", None) or [])
        except Exception:
            avs = set()
        try:
            from arcengine import GameAction as GA
        except Exception:
            return None
        _moves = [ga for aid, ga in ((1, GA.ACTION1), (2, GA.ACTION2), (3, GA.ACTION3), (4, GA.ACTION4), (5, GA.ACTION5))
                  if aid in avs]
        if _moves:
            # NO-FRAME-CHANGE ROTATION (Isaiah's rule): this filler runs while the composer computes perception. Returning
            # a FIXED action pounds one wall for many frames (the ACTION2 xN no-op run). Instead, watch the board: if it
            # did NOT change since the last filler, the current direction is a no-op -> ROTATE to the next available move.
            # No colour guess -- the unchanged frame is the signal. Any move that actually changes the board resets it.
            try:
                import numpy as _np
                _fr = getattr(fd, "frame", None)
                _pa = None
                if _fr is not None:
                    _gg = _np.asarray(_fr); _gg = _gg[0] if _gg.ndim == 3 else _gg
                    _pa = _gg[2:56] if _gg.shape[0] >= 56 else _gg
                _prev = getattr(self, "_sd_pa", None)
                if _pa is not None and _prev is not None and _np.array_equal(_pa, _prev):
                    self._sd_i = (getattr(self, "_sd_i", 0) + 1) % len(_moves)   # board stuck -> try the next direction
                self._sd_pa = _pa
            except Exception:
                pass
            return _moves[getattr(self, "_sd_i", 0) % len(_moves)]
        if 6 in avs:                                      # click-only game: a no-op-ish click beats a state wipe
            try:
                g = GA.ACTION6; g.set_data({"x": 0, "y": 0}); return g
            except Exception:
                pass
        return GA.ACTION1                                 # last resort -- still non-destructive vs RESET

    def choose_action(self, frames, lf=None):
        fd = lf if lf is not None else (frames[-1] if frames else None)
        import time as _time
        if self._t0 is None:
            self._t0 = _time.time()
        self._acts += 1
        _safe = self._safe_default(fd)                    # non-destructive move; NEVER RESET mid-game
        # PER-LEVEL DIAGNOSTIC CAP: count actions spent on the CURRENT level; reset the counter whenever the level
        # advances. If any single level exceeds PER_LEVEL_ACTIONS the agent is stuck/spamming on it (a few hundred moves
        # should clear a level) -> stop cleanly and surface it, instead of oscillating for thousands of frames.
        _cur_lvl = (getattr(fd, "levels_completed", 0) or 0) if fd is not None else 0
        if _cur_lvl != getattr(self, "_cap_lvl", None):
            self._cap_lvl = _cur_lvl; self._cap_acts = 0
        self._cap_acts = getattr(self, "_cap_acts", 0) + 1
        if self._cap_acts > self.PER_LEVEL_ACTIONS:
            self._done = True
            self._done_reason = "per-level action cap (%d) hit on level %d -- stuck/spamming, stopped for diagnostics" % (
                self.PER_LEVEL_ACTIONS, _cur_lvl)
            return _safe if _safe is not None else GameAction.ACTION1
        if self._acts > self.MAX_ACTIONS or (_time.time() - self._t0) > self.PER_GAME_SECONDS:
            self._done = True                            # budget spent -> signal done; do NOT RESET (that wipes progress)
            return _safe if _safe is not None else GameAction.ACTION1
        if not self._started:
            self._started = True
            self._thread = threading.Thread(target=self._run_composer, daemon=True)
            self._thread.start()
            return self._next(GameAction.RESET)           # FIRST action = game-start RESET (a legitimate boundary)
        if fd is not None:
            self.frame_q.put(fd)                          # feed back the previous action's frame
        return self._next(_safe if _safe is not None else GameAction.ACTION1)  # composer thinking -> safe move, NOT RESET

    def is_done(self, frames, lf=None):
        fd = lf if lf is not None else (frames[-1] if frames else None)
        if fd is not None and "WIN" in _state_name(fd):
            return True
        # RESET BAN [Isaiah]: END the session at GAME_OVER (one earned life) rather than auto-restarting back to level 0.
        # A restart is an EARNED privilege (reset_earned: corroborated-L4 AND reasoned its own way to needing it); until
        # then GAME_OVER is terminal for the session, so the agent cannot farm free attempts by resetting the game to zero.
        if fd is not None and "GAME_OVER" in _state_name(fd):
            try:
                import objective_validator as _OVr
                if not bool((_OVr._GLOBAL_KNOWLEDGE.get("patterns", {}) or {}).get("reset_earned")):
                    return True
            except Exception:
                return True
        return self._done                                 # composer exhausted -> advance cleanly
