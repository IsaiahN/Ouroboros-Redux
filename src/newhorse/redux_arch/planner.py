"""
planner.py -- redux-arch P5-GOAL step 2: CLOSE THE LOOP  (perceive → pose-goal → PLAN-to-goal → act).

A posed goal (goal.py) is *necessary but not sufficient* -- the chart flags PLAN→leading-goal and ACT(pragmatic)
as a separate, unbuilt link (Amdahl: filling pose-goal doesn't move the metric while plan-to-goal is empty). This
module builds the minimal version of that link: a PRAGMATIC one-step planner that SERVES the posed goal by
choosing an action whose before-state Context satisfies `φ_goal`, restricted to PASSABLE destinations (the minted
`INTENDED_FREE` affordance is the means). So the two built tiers finally compose -- Tier-1 affordance says what's
DOABLE, Tier-2 posed goal says what's WANTED, and the planner picks the doable action that serves the want.

Demonstrated end-to-end on a synthetic known-answer maze where it MOVES a (synthetic) `levels_completed`, while a
random agent does not. This isolates the SOLE remaining real-ARC gap as the DENSE REWARD SIGNAL: the passive dev
recordings have at most one win per game (navigation-to-sparse-win; the one dense-looking signal was a timer), so
grounding target-selection on real reward needs the agent to GENERATE its own wins -- i.e. go live and probe. The
loop itself is proven here; only its fuel (a dense signal) is missing on replay.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List, Callable
from .dsl import Context, Predicate
from .goal import PosedGoal, pose_goal, GoalStep

Vec = Tuple[int, int]
Cell = Tuple[int, int]


def plan_action(avatar: Cell, target: Cell, action_vecs: Dict[str, Vec], goal_pred: Predicate,
                passable: Optional[Callable[[Cell], bool]] = None) -> Optional[str]:
    """Pragmatic one-step plan: among PASSABLE actions (INTENDED_FREE destinations), pick one whose before-state
    Context satisfies the posed goal predicate (e.g. ACTS_TOWARD(avatar, target)). Falls back to any passable
    action if none satisfies φ_goal (keep moving / don't wall-bump), or None if boxed in."""
    passable_actions = []
    for a, v in action_vecs.items():
        dest = (avatar[0] + v[0], avatar[1] + v[1])
        if passable is None or passable(dest):
            passable_actions.append((a, v))
    for a, v in passable_actions:
        ctx = Context(focus_rc=avatar, focus_colour=0, target_rc=target, action_vec=v)
        if goal_pred.holds(ctx):                          # this action serves the posed goal
            return a
    return passable_actions[0][0] if passable_actions else None


def bfs_path_action(frame, cur_px: Cell, tgt_px: Cell, action_vecs: Dict[str, Vec],
                    passable: set, stride: int) -> Optional[str]:
    """PATHFINDER (reclaimed from new-horse navigation.py, re-pointed at DISCOVERED structure): breadth-first
    search over the passable-cell graph to the cell nearest the posed target, returning the FIRST action of the
    shortest route. Fixes the greedy planner's wall-stick: greedy picks a locally-toward move and dead-ends behind
    walls; BFS routes around them. Walls are discovered (a cell is passable iff its colour is in the learned
    `passable` set) -- never a baked map. The target object itself is usually NOT floor (e.g. ls20's grey box), so
    we head for the reachable passable cell CLOSEST to it (approach, not necessarily step onto -- the BE_AT vs
    TOUCH question is the goal-relation block, not the planner's).

    Cells are pixel/stride units so one action = one cell step. Returns None if boxed in / already closest."""
    import numpy as _np
    from collections import deque
    F = _np.asarray(frame); h, w = F.shape
    s = max(1, int(stride))
    def _cell(px):
        return (int(round(px[0] / s)), int(round(px[1] / s)))
    def _passable_cell(cell):
        r, c = cell[0] * s, cell[1] * s
        return 0 <= r < h and 0 <= c < w and int(F[r, c]) in passable
    moves = {lbl: (int(round(v[0] / s)), int(round(v[1] / s))) for lbl, v in action_vecs.items()}
    moves = {lbl: m for lbl, m in moves.items() if m != (0, 0)}
    start, goal = _cell(cur_px), _cell(tgt_px)
    seen = {start: None}
    q = deque([start])
    best, best_d = start, abs(start[0] - goal[0]) + abs(start[1] - goal[1])
    while q:
        cell = q.popleft()
        d = abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])
        if d < best_d:
            best_d, best = d, cell
        for lbl, m in moves.items():
            nb = (cell[0] + m[0], cell[1] + m[1])
            if nb not in seen and _passable_cell(nb):
                seen[nb] = (cell, lbl)
                q.append(nb)
    if best == start:
        return None                                       # already the closest reachable cell (or boxed in)
    cur, first = best, None
    while seen[cur] is not None:                           # backtrack to the first action of the route
        prev, lbl = seen[cur]; first = lbl; cur = prev
    return first


@dataclass
class GoalDirectedAgent:
    """perceive → POSE (once, from a warmup) → PLAN/ACT to serve the posed goal, using INTENDED_FREE for passability."""
    action_vecs: Dict[str, Vec]
    goal: Optional[PosedGoal] = None

    def pose(self, warmup: List[GoalStep], avatar_colour: int = 0) -> Optional[PosedGoal]:
        self.goal = pose_goal(warmup, avatar_colour=avatar_colour, max_size=1)
        return self.goal

    def act(self, avatar: Cell, target: Cell, passable: Optional[Callable[[Cell], bool]] = None) -> Optional[str]:
        if self.goal is None:
            return None
        return plan_action(avatar, target, self.action_vecs, self.goal.mint.predicate, passable)
