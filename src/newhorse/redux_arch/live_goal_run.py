"""
live_goal_run.py -- redux-triality: run the v6 goal-directed stack against the LIVE dev API.

The live environment is the LIVE GROUND (spec v6 §1.5): it answers back, so BOTH the human (via the scorecard URL)
and the agent (via real `levels_completed`) get an external vantage a dead recording cannot give. Flow:

  WARMUP (random directional acts)  -> learn cursor colour (smallest mover), per-action vec (axis-snapped),
                                        passable set (colours the cursor's own trajectory stepped onto), and the
                                        salient landmark (static, distinct object -- the referent prior).
  POSE (reach-a-cell template)      -> φ_goal = ACTS_TOWARD(avatar, salient landmark). On a navigation game the
                                        design-prior template IS the pose; reward is too sparse to pose from live.
  EXPLOIT (pragmatic planner)       -> each step choose a PASSABLE action (INTENDED_FREE) that serves φ_goal.

`levels_completed` is the sole metric. RULE 0.7: one run is not a verdict; this run's job is to TEACH which chart
block breaks first on real frames. Reset is earned-only -- never reset in play.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
import time
import numpy as np
from .replay import learn_basis
from .bridge import _px_centroid
from .goal import static_salient_targets
from .planner import plan_action
from .dsl import Predicate, make_atom

ACTS_TOWARD = Predicate(frozenset({make_atom("ACTS_TOWARD")}))


def _learn_passable(frames: List[np.ndarray], cursor: Optional[int]) -> set:
    """Floor = the before-colour of cells the cursor ACTUALLY entered (leak-free trajectory read)."""
    passable = set()
    if cursor is None:
        return passable
    for i in range(1, len(frames)):
        cb, ca = _px_centroid(frames[i - 1], cursor), _px_centroid(frames[i], cursor)
        if cb is None or ca is None:
            continue
        rb, cbc = int(round(cb[0])), int(round(cb[1]))
        ra, ca_ = int(round(ca[0])), int(round(ca[1]))
        if (rb, cbc) != (ra, ca_):                        # the cursor moved -> it entered (ra,ca_)
            b = np.asarray(frames[i - 1]); h, w = b.shape
            if 0 <= ra < h and 0 <= ca_ < w:
                passable.add(int(b[ra, ca_]))
    return passable


def run_goal_live(game_id: str = "ls20-9607627b", warmup: int = 60, max_actions: int = 400,
                  wall_cap_s: float = 200.0, bg: int = 4, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Play one live game with the goal-directed stack. Returns a dict incl. levels_completed and the scorecard URL."""
    from ..arc3_env import Arc3Session
    session = Arc3Session(game_id, tags=tags or ["redux-triality", "goal-live", game_id])
    log: List[str] = []
    try:
        snap = session.open()
        avail = [v for v in snap["available"] if v != 6]   # directional values only (6 = click)
        if not avail:
            return dict(game=game_id, outcome="no_discrete_actions", levels_completed=snap["levels_completed"],
                        view_url=session.view_url, log=log)
        labels = ["A%d" % v for v in avail]
        val_of = {"A%d" % v: v for v in avail}

        # ---- WARMUP: gather (frame, action-label) to learn the perception basis -------------------------------
        frames = [np.asarray(snap["grid"])]
        acts = ["RESET"]
        t0 = time.time()
        best_levels = snap["levels_completed"]
        for i in range(warmup):
            lbl = labels[i % len(labels)]                  # cycle actions so every action's vec is observed
            snap = session.step(val_of[lbl])
            frames.append(np.asarray(snap["grid"])); acts.append(lbl)
            best_levels = max(best_levels, snap["levels_completed"])
            if snap["done"]:
                break
        cursor, vecs = learn_basis(frames, acts)
        passable = _learn_passable(frames, cursor)
        cands = static_salient_targets(frames, avatar_colour=(cursor if cursor is not None else -1), bg=bg, top=3)
        target_colour = cands[0] if cands else None
        log.append("LEARN cursor=%s vecs=%s passable=%s salient=%s (target=%s)"
                   % (cursor, vecs, sorted(passable), cands, target_colour))
        if cursor is None or not vecs or target_colour is None:
            return dict(game=game_id, outcome="warmup_underdetermined", levels_completed=best_levels,
                        view_url=session.view_url, cursor=cursor, vecs=vecs, passable=sorted(passable),
                        salient=cands, log=log)

        # ---- EXPLOIT: serve φ_goal = ACTS_TOWARD(avatar, salient landmark), passability-gated -----------------
        steps = warmup
        outcome = "action_cap"
        stuck = 0
        while steps < max_actions and (time.time() - t0) < wall_cap_s:
            grid = np.asarray(snap["grid"])
            cur = _px_centroid(grid, cursor)
            tgt = _px_centroid(grid, target_colour)
            if cur is None or tgt is None:                 # perception lost the cursor or the landmark
                lbl = labels[steps % len(labels)]
            else:
                avatar = (int(round(cur[0])), int(round(cur[1])))
                target = (int(round(tgt[0])), int(round(tgt[1])))
                h, w = grid.shape
                def passable_fn(dest, _g=grid, _h=h, _w=w):
                    r, c = dest
                    return 0 <= r < _h and 0 <= c < _w and int(_g[r, c]) in passable
                lbl = plan_action(avatar, target, vecs, ACTS_TOWARD, passable_fn) or labels[steps % len(labels)]
            prev = snap["levels_completed"]
            snap = session.step(val_of[lbl], reasoning={"why": "serve ACTS_TOWARD(avatar, salient=%s)" % target_colour})
            if snap["levels_completed"] > prev:
                log.append("LEVEL UP %d->%d at step %d" % (prev, snap["levels_completed"], steps))
            best_levels = max(best_levels, snap["levels_completed"])
            steps += 1
            if snap["done"]:
                outcome = snap["state"]
                break
        return dict(game=game_id, outcome=outcome, levels_completed=best_levels, steps=steps,
                    view_url=session.view_url, cursor=cursor, vecs=vecs, passable=sorted(passable),
                    salient=cands, target_colour=target_colour, log=log)
    finally:
        session.close()
