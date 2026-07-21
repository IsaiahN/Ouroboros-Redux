"""
Tests for goal-by-reward-disposes (brick 14).

GoalManager: a market of candidate goals priced by reward -- confirm what rewards, demote (defeasibly) what
doesn't, rotate. Loop integration: a world with a DECOY landmark and a REAL target (reaching it grants a
level). The agent tries candidates, demotes the decoy (reaching it does nothing), and locks the real target
once reaching it advances the level.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.goal import GoalManager, candidate_targets
from newhorse.perception import Object
from newhorse.agent_loop import AgentLoop


def test_reward_confirms_the_active_goal():
    gm = GoalManager()
    gm.propose([((5, 5), 0), ((1, 1), 1)])
    g = gm.active_goal()                                   # highest price = rank 0 = (5,5)
    assert g == (5, 5)
    gm.observe(reached=False, reward=True)                 # a reward while pursuing (5,5) -> confirm
    assert gm.price[(5, 5)] > gm.price[(1, 1)]
    assert gm.active_goal() == (5, 5)                      # stays the pursued goal


def test_reaching_without_reward_demotes_and_rotates():
    gm = GoalManager()
    gm.propose([((5, 5), 0), ((1, 1), 1)])
    assert gm.active_goal() == (5, 5)
    before = gm.price[(5, 5)]
    gm.observe(reached=True, reward=False)                 # reached it, no reward -> a dead target
    assert gm.price[(5, 5)] < before                       # demoted
    assert gm.active_goal() == (1, 1)                      # rotated to the next candidate


def test_stall_demotes_even_without_reaching():
    gm = GoalManager(stall_steps=3)
    gm.propose([((9, 9), 0), ((1, 1), 1)])
    gm.active_goal()
    for _ in range(3):
        gm.observe(reached=False, reward=False)            # never reaches (9,9)
    assert gm.active_goal() == (1, 1)                       # stalled -> rotated


def test_demotion_is_defeasible_not_a_hard_drop():
    gm = GoalManager()
    gm.propose([((5, 5), 0)])
    gm.active_goal()
    gm.observe(reached=True, reward=False)
    assert gm.price[(5, 5)] >= gm.min_price                # kept a residual price -> reconsiderable
    assert gm.active_goal() == (5, 5)                       # only candidate -> tried again


def test_nothing_silent():
    gm = GoalManager()
    gm.propose([((5, 5), 0)]); gm.active_goal()
    gm.observe(reached=False, reward=True)
    assert any(s.startswith("GOAL") for s in gm.log)


def _obj(cells, colour):
    return Object(cells=frozenset(cells), colours=frozenset({colour}))


def test_candidate_targets_ranks_marker_like_first():
    objs = [_obj([(0, 0)], 4),                              # cursor
            _obj([(10, 10)], 7),                            # tiny landmark
            _obj([(r, c) for r in range(5) for c in range(5)], 3)]  # big blob
    cands = candidate_targets(objs, cursor_colour=4, stride=1)
    assert cands[0][0] == (10, 10)                          # the small one ranks first (marker-like)


# ---------------- loop integration: demote the decoy, lock the real target ----------------
class RewardMazeWorld:
    """A cursor (colour 4); a DECOY landmark (colour 6) and a REAL target (colour 7). Reaching the REAL target
    grants a level (and respawns the cursor); reaching the decoy does nothing. Small board -> stride 1."""

    def __init__(self):
        self.h, self.w = 9, 9
        self.pos = [4, 4]
        self.decoy = (0, 0)
        self.real = (8, 8)
        self.levels = 0
        self.secret = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

    def _frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        g[self.decoy] = 6
        g[self.real] = 7
        g[tuple(self.pos)] = 4
        return g

    def frame(self):
        return self._frame()

    def step(self, action):
        dr, dc = self.secret.get(action, (0, 0))
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if 0 <= nr < self.h and 0 <= nc < self.w:
            self.pos = [nr, nc]
        if tuple(self.pos) == self.real:                   # reached the REAL target -> level up, respawn
            self.levels += 1
            self.pos = [4, 4]
        return self._frame()


def test_loop_demotes_decoy_and_locks_rewarding_target():
    world = RewardMazeWorld()
    agent = AgentLoop(actions=["U", "D", "L", "R"], background=0)
    levels_seen = 0
    for _ in range(400):
        # drive one step, signalling reward to the goal market when a level was granted
        frame = world.frame()
        ctrl = agent.perceive(frame)
        if ctrl is None:
            action = agent.actions[0]; world.step(action); continue
        action, t, _ = agent.choose(frame, ctrl)
        before_levels = world.levels
        after = world.step(action)
        if world.levels > before_levels:
            agent.signal_reward()
        agent.observe(frame, ctrl, action, t, after)
        levels_seen = world.levels
        if levels_seen >= 2:
            break
    assert agent.agency.ready()
    assert levels_seen >= 2, "never learned to reach the rewarding target (levels=%d)" % levels_seen
    # the REAL target (relation keyed on cell (8,8)) is priced above the decoy (relation on (0,0))
    real_price = max((p for k, p in agent.goals.price.items() if k[1] == (8, 8)), default=0.0)
    decoy_price = max((p for k, p in agent.goals.price.items() if k[1] == (0, 0)), default=0.0)
    assert real_price > decoy_price, agent.goals.price
