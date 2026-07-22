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
