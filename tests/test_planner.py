"""
redux-arch P5-GOAL step 2: the WHOLE chain closes on a synthetic known-answer world -- perceive → pose-goal →
plan-to-goal → act → COMPLETE LEVELS. The agent poses its goal from a dense reward (distance-reduction to the
reward-linked target, with a distractor present), then serves it with a passability-gated pragmatic planner
(INTENDED_FREE). It moves a synthetic `levels_completed`; a random agent does not. This is the honest precursor
to live: the loop works when a dense signal exists; only the signal is missing on the passive recordings.
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.planner import GoalDirectedAgent, plan_action
from newhorse.redux_arch.goal import pose_goal
from newhorse.redux_arch.dsl import Context, Predicate, make_atom

VECS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


class MazeEnv:
    """Open 13x13 board. Avatar navigates to a TRUE target; reaching it => levels_completed++ and the target
    relocates. A DISTRACTOR object sits elsewhere (never rewarded). A one-cell wall band tests passability."""
    def __init__(self, walls=False, seed=0):
        self.h = self.w = 13
        self.rng = random.Random(seed)
        self.avatar = [6, 1]
        self.true = (6, 11)
        self.dist = (0, 0)
        self.levels = 0
        self.walls = set()
        if walls:
            self.walls = {(r, 6) for r in range(0, 13) if r not in (6,)}   # a wall with a gap at row 6

    def passable(self, cell):
        r, c = cell
        return 0 <= r < self.h and 0 <= c < self.w and (r, c) not in self.walls

    def candidates(self):
        return {7: self.true, 8: self.dist}

    def step(self, action):
        v = VECS[action]
        nr, nc = self.avatar[0] + v[0], self.avatar[1] + v[1]
        if self.passable((nr, nc)):
            self.avatar = [nr, nc]
        reached = tuple(self.avatar) == self.true
        if reached:
            self.levels += 1
            self.true = (self.rng.randint(0, 12), self.rng.randint(0, 12))   # relocate the goal
        return reached


def _warmup(env, n=250, seed=1):
    """Random exploration -> dense progress steps (progressed == got closer to the TRUE target)."""
    rng = random.Random(seed)
    steps = []
    for _ in range(n):
        a = rng.choice(list(VECS))
        before = tuple(env.avatar)
        d_b = abs(before[0] - env.true[0]) + abs(before[1] - env.true[1])
        env.step(a)
        d_a = abs(env.avatar[0] - env.true[0]) + abs(env.avatar[1] - env.true[1])
        steps.append((before, VECS[a], env.candidates(), d_a < d_b))
    return steps


def test_agent_poses_reach_goal_then_clears_levels():
    env = MazeEnv(seed=2)
    agent = GoalDirectedAgent(action_vecs=VECS)
    goal = agent.pose(_warmup(env), avatar_colour=4)
    assert goal is not None and goal.target == 7                      # posed: reach the reward-linked target
    assert "ACTS_TOWARD(focus,target)" in {a.name for a in goal.mint.predicate.atoms}
    # now EXPLOIT: serve the posed goal; count level completions in a budget
    env2 = MazeEnv(seed=2)
    completed = 0
    for _ in range(400):
        a = agent.act(tuple(env2.avatar), env2.true, passable=env2.passable)
        if a is None:
            break
        if env2.step(a):
            completed += 1
    assert completed >= 8, completed                                  # the posed goal drives real completions


def test_random_agent_barely_clears_levels():
    env = MazeEnv(seed=2)
    rng = random.Random(9)
    completed = 0
    for _ in range(400):
        if env.step(rng.choice(list(VECS))):
            completed += 1
    assert completed <= 3, completed                                  # baseline: goal-direction is doing the work


def test_planner_respects_passability_no_wall_bump():
    # with a wall band (gap at row 6) the planner must route through passable cells only; INTENDED_FREE gates it.
    env = MazeEnv(walls=True, seed=3)
    agent = GoalDirectedAgent(action_vecs=VECS)
    assert agent.pose(_warmup(MazeEnv(seed=3)), avatar_colour=4) is not None
    for _ in range(400):
        avatar = tuple(env.avatar)
        a = agent.act(avatar, env.true, passable=env.passable)
        if a is None:
            break
        v = VECS[a]
        assert env.passable((avatar[0] + v[0], avatar[1] + v[1]))     # never chooses a wall cell
        env.step(a)
        if env.levels >= 1:
            break
    assert env.levels >= 1                                            # reached the target through the gap
