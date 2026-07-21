"""
live_run.py -- brick 9: drive the AgentLoop against a live ARC-AGI-3 session (THE MAP §9.6, closed
against the real world). This is the consumer that turns the six-brick loop + the hard bounds into an
actual play run. THE GATE metric is `levels_completed` ONLY -- no fractional goose chase (RULE 0.7:
a single run is never a verdict; the first run's job is to TEACH).

`run_live(session, ...)` is PURE over the session interface (open/step/close returning snapshot dicts),
so it runs offline against a FakeSession with no network or key. `run_online_game(...)` is the thin
entry that constructs the real Arc3Session (lazy import, so tests need no SDK/key).

Discipline held here:
  * NEVER ENCODE THE ANSWER -- actions are the game's own available action VALUES, wrapped as generic
    labels; WHICH action causes WHICH transform is discovered by the loop's prediction error, never given.
  * RESET is EARNED-ONLY -- on a level-up we mint a credit via earn_progress(); we NEVER reset in active
    play. A GAME_OVER without an earned+spent reset simply ENDS the session (no free re-attempt).
  * NO DOWNSAMPLING -- perceive() admits every native frame through the ResolutionBound (brick 8).
  * NOTHING SILENT -- every step is on the loop's log; the run returns what it LEARNED, not just a score.
"""
from __future__ import annotations
import time
from typing import Dict, Any, List, Optional
import numpy as np
from .agent_loop import AgentLoop, unit_transforms


def _learned_summary(loop: AgentLoop) -> Dict[str, Any]:
    """What the run TAUGHT: per action, the transform it came to believe, plus the pose + brake state."""
    per_action: Dict[str, Any] = {}
    seen = sorted({a for (a, _t) in loop.belief})
    for a in seen:
        bel = {t: loop.belief.get((a, t), 0.0) for t in unit_transforms()}
        best = max(bel, key=bel.get)
        per_action[a] = {"best_transform": best, "belief": round(bel[best], 3)}
    return dict(per_action=per_action,
                pose_alpha=round(loop.pose.alpha, 3),
                pe_integral=loop.residuals.pe_integral(),
                refuted=len(loop.ledger),
                reset_credits=loop.reset_gate.credits,
                # brick 12: did the agency separate the cursor from the environment and learn its move map?
                cursor_colour=loop.agency.cursor_colour(),
                cursor_stride=loop.agency.stride(),
                action_map={a: list(v) for a, v in loop.agency.action_map().items()},
                # brick 13/14: navigation + goal market
                walls_learned=sum(1 for v in loop.nav.edge.values() if v is False),
                goal_candidates=len(loop.goals.price),
                top_goals=sorted(loop.goals.price.items(), key=lambda kv: -kv[1])[:3])


def run_live(session, *, wall_cap_s: float = 120.0, max_actions: int = 600,
             background: int = 0) -> Dict[str, Any]:
    """Play one game through the loop. Returns {levels_completed, steps, outcome, view_url, learned}."""
    snap = session.open()
    # the action set = the game's available NON-CLICK discrete actions (value 6 = click needs coordinates
    # the unit-transform loop cannot yet produce -- that is a later brick; this first slice drives movers).
    avail = [v for v in snap["available"] if v != 6]   # value 6 = click; the unit-transform loop can't drive it yet
    if not avail:
        return dict(levels_completed=snap["levels_completed"], steps=0, outcome="no_discrete_actions",
                    view_url=getattr(session, "view_url", None), learned=None)
    actions = ["A%d" % v for v in avail]
    val_of = {"A%d" % v: v for v in avail}
    loop = AgentLoop(actions=actions, background=background)

    grid = snap["grid"]
    best_levels = snap["levels_completed"]
    t0 = time.time()
    steps = 0
    outcome = "action_cap"
    while steps < max_actions and (time.time() - t0) < wall_cap_s:
        ctrl = loop.perceive(grid)                       # brick-8 no-downsample bound admits the native frame
        if ctrl is None:                                 # nothing controllable segmented -> probe to change the world
            action_label = actions[steps % len(actions)]
        else:
            action_label, _tname, _pred = loop.choose(grid, ctrl)
        reasoning = {"why": "committed %s; discovering its effect by prediction error" % action_label}
        snap = session.step(val_of[action_label], reasoning=reasoning)
        after = snap["grid"]
        leveled = snap["levels_completed"] > best_levels
        if leveled:
            loop.signal_reward()                         # brick 14: attribute the reward to the goal pursued THIS step
        # score the committed action against reality -- only when the resolution is stable (it should be)
        if ctrl is not None and after.shape == grid.shape:
            loop.observe(grid, ctrl, action_label, _tname, after)
        else:
            loop.clock += 1                              # advance the logical clock even when we couldn't score
        if leveled:                                      # EARNED progress -> mint a reset credit (never used in play)
            loop.earn_progress(level_completed=True,
                               reason="levels %d->%d" % (best_levels, snap["levels_completed"]))
            best_levels = snap["levels_completed"]
        grid = after
        steps += 1
        if snap["done"]:                                 # WIN or GAME_OVER. RESET is earned-only: we do NOT reset in play.
            outcome = snap["state"]
            break

    return dict(levels_completed=best_levels, steps=steps, outcome=outcome,
                view_url=getattr(session, "view_url", None), learned=_learned_summary(loop))


def run_online_game(game_id: str, *, wall_cap_s: float = 90.0, max_actions: int = 400,
                    tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Thin online entry: construct the real Arc3Session, play, close the scorecard, return the result.
    Lazy-imports the SDK so offline tests need neither the SDK nor a key."""
    from .arc3_env import Arc3Session
    session = Arc3Session(game_id, tags=tags)
    try:
        result = run_live(session, wall_cap_s=wall_cap_s, max_actions=max_actions)
    finally:
        session.close()
    result["game"] = game_id
    return result
