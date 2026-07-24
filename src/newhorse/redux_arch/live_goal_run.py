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
from .goal import salient_targets, approachable_component_centroid
from .planner import plan_action, bfs_path_action
from .explore import CuriosityExplorer
from .coupled import learn_two_body, two_body_drive_action, two_body_search_action
from scipy import ndimage as _ndi
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
                  wall_cap_s: float = 200.0, bg: int = 4, explore: bool = False,
                  tags: Optional[List[str]] = None) -> Dict[str, Any]:
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
        # referent prior: exclude the avatar, the passable floor, and the background/field -> a static landmark
        cands = salient_targets(frames, avatar_colour=(cursor if cursor is not None else -1),
                                exclude=set(passable) | {bg}, top=3)
        target_colour = cands[0] if cands else None
        log.append("LEARN cursor=%s vecs=%s passable=%s salient=%s (target=%s)"
                   % (cursor, vecs, sorted(passable), cands, target_colour))
        if cursor is None or not vecs or target_colour is None:
            return dict(game=game_id, outcome="warmup_underdetermined", levels_completed=best_levels,
                        view_url=session.view_url, cursor=cursor, vecs=vecs, passable=sorted(passable),
                        salient=cands, log=log)

        # ---- ACT: EXPLORE (curiosity/coverage, to manufacture a first win) or EXPLOIT (pathfind to landmark) ---
        stride = max((max(abs(v[0]), abs(v[1])) for v in vecs.values()), default=1) or 1
        explorer = CuriosityExplorer() if explore else None
        steps = warmup
        outcome = "action_cap"
        min_target_dist = None                             # closest the cursor ever gets to the landmark (px)
        while steps < max_actions and (time.time() - t0) < wall_cap_s:
            grid = np.asarray(snap["grid"])
            cur = _px_centroid(grid, cursor)
            h, w = grid.shape
            def passable_px(dest, _g=grid, _h=h, _w=w):
                r, c = dest
                return 0 <= r < _h and 0 <= c < _w and int(_g[r, c]) in passable
            if cur is None:
                lbl = labels[steps % len(labels)]
            elif explorer is not None:                     # EXPLORE: sweep the board by cell-novelty
                avatar = (int(round(cur[0])), int(round(cur[1])))
                pick = explorer.choose(avatar, vecs, passable_px, stride)
                if pick is None:
                    lbl = labels[steps % len(labels)]
                else:
                    lbl, cell = pick
                    explorer.visit(lbl, cell)
            else:                                          # EXPLOIT: pathfind to the posed landmark
                tgt = approachable_component_centroid(grid, target_colour, passable)
                if tgt is None:
                    lbl = labels[steps % len(labels)]
                else:
                    avatar = (int(round(cur[0])), int(round(cur[1])))
                    target = (int(round(tgt[0])), int(round(tgt[1])))
                    d = abs(avatar[0] - target[0]) + abs(avatar[1] - target[1])
                    min_target_dist = d if min_target_dist is None else min(min_target_dist, d)
                    lbl = (bfs_path_action(grid, avatar, target, vecs, passable, stride)
                           or plan_action(avatar, target, vecs, ACTS_TOWARD, passable_px)
                           or labels[steps % len(labels)])
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
                    salient=cands, target_colour=target_colour, min_target_dist=min_target_dist,
                    mode=("explore" if explore else "exploit"),
                    coverage=(explorer.coverage() if explorer is not None else None), log=log)
    finally:
        session.close()


def run_policy_live(game_id: str, max_actions: int = 80, wall_cap_s: float = 200.0,
                    tags: Optional[List[str]] = None, blackboard=None, retry_cap: int = 6) -> Dict[str, Any]:
    """Drive the CONTROL-INVERSION ReduxPolicy against ONE live game, per-step -- the single-game shape of what the
    swarm runs per thread. Proves the refactored policy preserves each organ's competence live. The policy routes
    the family itself (click / two-body / directional) from the warmup stream; no per-game wiring here.

    DON'T-DIE: on GAME_OVER (not a WIN), the policy has recorded what killed it; the runner issues the legitimate
    post-death RESET (bounded by retry_cap and the action budget) so the retry can avoid the fatal action instead of
    ending the run at the first death. A real WIN still stops immediately."""
    from .sdk_guard import assert_online_sdk
    assert_online_sdk()                                   # fail loud on wrong interpreter/SDK before touching the wire
    from ..arc3_env import Arc3Session
    from .policy import ReduxPolicy
    session = Arc3Session(game_id, tags=tags or ["redux-triality", "policy-live", game_id])
    log: List[str] = []
    try:
        snap = session.open()
        pol = ReduxPolicy(game_id=game_id, blackboard=blackboard, warmup_cap=8)
        best_levels = snap["levels_completed"]; t0 = time.time(); steps = 0; outcome = "action_cap"; retries = 0
        while steps < max_actions and (time.time() - t0) < wall_cap_s:
            pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap["state"])
            if snap["done"]:
                if snap["state"] == "WIN":
                    outcome = "WIN"; break
                # GAME_OVER: death recorded in observe(). §XIX -- a retry is issued ONLY if the reset is EARNED
                # (the death taught a NEW avoidable cause); an unearned death ends the session.
                earned, why = pol.reset_earned()
                if not earned or retries >= retry_cap:
                    outcome = "GAME_OVER"; log.append("no RESET (earned=%s cap=%d): %s" % (earned, retry_cap, why)); break
                retries += 1; steps += 1
                log.append("EARNED RESET #%d at step %d: %s" % (retries, steps, why))
                snap = session.reset_after_death(reasoning={"why": why, "reset_earned": True})
                pol.note_reset()
                continue
            lbl, data = pol.choose()
            val = int(lbl[1:])
            prev = snap["levels_completed"]
            snap = session.step(val, data=data, reasoning={"why": "ReduxPolicy family=%s" % pol.family})
            if snap["levels_completed"] > prev:
                log.append("LEVEL UP %d->%d at step %d (family=%s)" % (prev, snap["levels_completed"], steps, pol.family))
            best_levels = max(best_levels, snap["levels_completed"]); steps += 1
        probe = None
        if pol._probe is not None:
            probe = dict(hypotheses=pol._probe.hypotheses, current=pol._probe.current(),
                         idx=pol._probe.idx, locked=pol._probe.locked)
        return dict(game=game_id, outcome=outcome, levels_completed=best_levels, steps=steps,
                    family=pol.family, view_url=session.view_url, log=log,
                    level_deltas=pol.level_deltas, probe=probe, abduced=pol.abduced,
                    directed_active=(pol._directed is not None),
                    effective=pol.effect_aff.effective(), effect_visits=dict(pol._effect_visits),
                    undo=pol.effect_aff.undo(),
                    deaths=pol.n_deaths, distinct_death_causes=pol.deaths.distinct_causes,
                    retries=retries, vetoes=pol.n_vetoes)
    finally:
        session.close()


def run_click_live(game_id: str = "s5i5-18d95033", max_actions: int = 120, wall_cap_s: float = 200.0,
                   tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """CLICK modality live: for a coordinate-only game (available == [6]), perceive candidate click points and probe
    them by curiosity/empowerment. Unlocks the 6 click-only dev games the directional stack cannot even act on.
    ACTION6 carries data={"x": col, "y": row}. Returns levels_completed + the scorecard URL."""
    from ..arc3_env import Arc3Session
    from .click import click_targets, grid_sweep, ClickProber
    session = Arc3Session(game_id, tags=tags or ["redux-triality", "click-live", game_id])
    log: List[str] = []
    try:
        snap = session.open()
        avail = snap["available"]
        if 6 not in avail:
            return dict(game=game_id, outcome="not_a_click_game", available=avail,
                        levels_completed=snap["levels_completed"], view_url=session.view_url, log=log)
        grid = np.asarray(snap["grid"])
        prober = ClickProber(click_targets(grid), grid_sweep(grid, n=8))
        log.append("CLICK avail=%s candidates=%d (perceptual=%d)"
                   % (avail, len(prober.targets), len(click_targets(grid))))
        best_levels = snap["levels_completed"]; t0 = time.time(); steps = 0; outcome = "action_cap"; changes = 0
        while steps < max_actions and (time.time() - t0) < wall_cap_s:
            tgt = prober.choose()
            if tgt is None:
                break
            r, c = tgt
            prev_grid = np.asarray(snap["grid"]); prev = snap["levels_completed"]
            snap = session.step(6, data={"x": int(c), "y": int(r)},
                                reasoning={"why": "epistemic click-probe at (row=%d,col=%d)" % (r, c)})
            new_grid = np.asarray(snap["grid"])
            if prober.observe(prev_grid, new_grid):
                changes += 1
                prober.refresh(click_targets(new_grid))       # new tokens may have appeared -> fold them in
            if snap["levels_completed"] > prev:
                log.append("LEVEL UP %d->%d at step %d via click (%d,%d)" % (prev, snap["levels_completed"], steps, r, c))
            best_levels = max(best_levels, snap["levels_completed"]); steps += 1
            if snap["done"]:
                outcome = snap["state"]; break
        return dict(game=game_id, outcome=outcome, levels_completed=best_levels, steps=steps,
                    view_url=session.view_url, board_changes=changes,
                    productive_clicks=len(prober.productive()), log=log)
    finally:
        session.close()


def _two_bodies(frame, colour, max_body_cells=400):
    """The two body centroids. `colour` is an int (two same-colour components, sorted left-to-right) OR a
    (c0, c1) pair (one component per colour, body i = colour[i]) -- the different-coloured two-body case."""
    f = np.asarray(frame)
    if isinstance(colour, (tuple, list)):                    # two-colour: one small component per colour, in order
        out = []
        for c in colour:
            m = f == int(c)
            if not m.any():
                return []
            lab, k = _ndi.label(m)
            small = [(int(round(np.where(lab == i)[0].mean())), int(round(np.where(lab == i)[1].mean())))
                     for i in range(1, k + 1) if np.where(lab == i)[0].size <= max_body_cells]
            if len(small) != 1:
                return []
            out.append(small[0])
        return out
    m = f == colour
    if not m.any():
        return []
    lab, k = _ndi.label(m); out = []
    for i in range(1, k + 1):
        ys, xs = np.where(lab == i)
        if ys.size <= max_body_cells:
            out.append((int(round(ys.mean())), int(round(xs.mean()))))
    return sorted(out, key=lambda p: p[1])


def run_coupled_live(game_id="m0r0-492f87ba", warmup=40, max_actions=300, wall_cap_s=200.0,
                     tags=None):
    """TWO-BODY driver live: learn the coupling, then drive both bodies toward MEET (become one component -- the
    m0r0 win relation). Passability per body = colours that body's own trajectory stepped onto (leak-free)."""
    from ..arc3_env import Arc3Session
    session = Arc3Session(game_id, tags=tags or ["redux-triality", "coupled-live", game_id])
    log = []
    try:
        snap = session.open()
        avail = [v for v in snap["available"] if v != 6]
        if not avail:
            return dict(game=game_id, outcome="no_discrete_actions", levels_completed=snap["levels_completed"],
                        view_url=session.view_url, log=log)
        labels = ["A%d" % v for v in avail]; val_of = {"A%d" % v: v for v in avail}
        frames = [np.asarray(snap["grid"])]; acts = ["RESET"]
        best_levels = snap["levels_completed"]; t0 = time.time()
        for i in range(warmup):
            snap = session.step(val_of[labels[i % len(labels)]])
            frames.append(np.asarray(snap["grid"])); acts.append(labels[i % len(labels)])
            best_levels = max(best_levels, snap["levels_completed"])
            if snap["done"]:
                break
        colour, ag = learn_two_body(frames, acts)
        if colour is None or ag is None or not ag.ready():
            return dict(game=game_id, outcome="coupling_underdetermined", levels_completed=best_levels,
                        view_url=session.view_url, colour=colour,
                        nbodies=(ag.n_controllable() if ag else 0), log=log)
        # per-body passable = before-colour of cells each body entered during warmup
        passable = [set(), set()]
        for i in range(1, len(frames)):
            b0, b1 = _two_bodies(frames[i - 1], colour), _two_bodies(frames[i], colour)
            if len(b0) == 2 and len(b1) == 2:
                for j in range(2):
                    if b0[j] != b1[j]:
                        r, c = b1[j]; h, w = frames[i - 1].shape
                        if 0 <= r < h and 0 <= c < w:
                            passable[j].add(int(frames[i - 1][r, c]))
        stride = max((max(abs(v[0]), abs(v[1])) for m in (ag.body_map(0), ag.body_map(1)) for v in m.values()),
                     default=1) or 1
        log.append("LEARN colour=%s stride=%s bodymaps=%s passable=%s" %
                   (colour, stride, [ag.body_map(0), ag.body_map(1)], [sorted(passable[0]), sorted(passable[1])]))
        steps = warmup; outcome = "action_cap"; min_dist = None
        while steps < max_actions and (time.time() - t0) < wall_cap_s:
            grid = np.asarray(snap["grid"]); h, w = grid.shape
            bodies = _two_bodies(grid, colour)
            if len(bodies) < 2:
                min_dist = 0
                lbl = labels[steps % len(labels)]           # merged (or lost) -> nudge
            else:
                d = abs(bodies[0][0] - bodies[1][0]) + abs(bodies[0][1] - bodies[1][1])
                min_dist = d if min_dist is None else min(min_dist, d)
                def passfn(i, dest, _g=grid, _h=h, _w=w):    # px-space passability (greedy fallback)
                    r, c = dest
                    return 0 <= r < _h and 0 <= c < _w and (not passable[i] or int(_g[r, c]) in passable[i])
                def passcell(i, cell, _g=grid, _h=h, _w=w, _s=stride):   # cell-space passability (joint search)
                    r, c = cell[0] * _s, cell[1] * _s
                    return 0 <= r < _h and 0 <= c < _w and (not passable[i] or int(_g[r, c]) in passable[i])
                lbl = (two_body_search_action(bodies, ag, passcell, stride)   # JOINT SEARCH to MEET
                       or two_body_drive_action(bodies, ag, passfn)           # greedy fallback
                       or labels[steps % len(labels)])
            prev = snap["levels_completed"]
            snap = session.step(val_of[lbl], reasoning={"why": "drive two bodies to MEET"})
            if snap["levels_completed"] > prev:
                log.append("LEVEL UP %d->%d at step %d" % (prev, snap["levels_completed"], steps))
            best_levels = max(best_levels, snap["levels_completed"]); steps += 1
            if snap["done"]:
                outcome = snap["state"]; break
        return dict(game=game_id, outcome=outcome, levels_completed=best_levels, steps=steps,
                    view_url=session.view_url, colour=colour, min_body_dist=min_dist, log=log)
    finally:
        session.close()
