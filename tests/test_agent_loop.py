"""
Tests for loop closure (THE MAP §9.6): PERCEIVE -> THINK -> MAP -> ACT with BOTH feedback arrows.

The claim under test is not "the code runs" but "the loop LEARNS": on a toy world whose action->effect
mapping is the WORLD'S SECRET (never told to the agent), the agent discovers WHICH action causes WHICH
generic transform purely from prediction error. That is loop closure -- perception feeds thinking, the
market prices by residual, the act is committed, and the residual feeds back to move belief + pose + ledger.

NEVER ENCODE THE ANSWER: the agent is constructed with only (actions, generic transforms, background).
The secret mapping lives ONLY inside the ToyWorld; the agent never reads it. If the agent ends up knowing
the mapping, it learned it -- there is no path by which it was handed it.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.agent_loop import AgentLoop, unit_transforms


class ToyWorld:
    """A tiny controllable-dot world. ONE colored cell on a background board. Each action moves the dot
    by a SECRET delta (bounded to the grid). The agent is never told this mapping -- it is the world's law."""

    def __init__(self, shape=(6, 6), start=(2, 2), colour=3, secret=None):
        self.h, self.w = shape
        self.pos = start
        self.colour = colour
        # THE SECRET: action -> true (dr, dc). The agent does NOT receive this.
        self.secret = secret or {"A": (1, 0), "B": (0, 1)}   # A moves DOWN, B moves RIGHT

    def frame(self) -> np.ndarray:
        g = np.zeros((self.h, self.w), dtype=int)
        g[self.pos] = self.colour
        return g

    def step(self, action: str) -> np.ndarray:
        dr, dc = self.secret.get(action, (0, 0))
        nr = min(self.h - 1, max(0, self.pos[0] + dr))
        nc = min(self.w - 1, max(0, self.pos[1] + dc))
        self.pos = (nr, nc)
        return self.frame()


def _run(world, steps, actions=None):
    agent = AgentLoop(actions=actions or ["A"])
    committed_residual = []
    integral_trace = []
    shapes = set()
    for _ in range(steps):
        frame = world.frame()
        shapes.add(frame.shape)
        before_integral = agent.residuals.pe_integral()
        agent.step(frame, world.step)
        committed_residual.append(agent.residuals.pe_integral() - before_integral)
        integral_trace.append(agent.residuals.pe_integral())
        shapes.add(world.frame().shape)
    return agent, committed_residual, integral_trace, shapes


def test_loop_runs_end_to_end():
    world = ToyWorld(secret={"A": (1, 0)})
    agent, _, _, _ = _run(world, steps=8, actions=["A"])
    assert agent.clock == 8                    # eight closed cycles happened
    assert len(agent.log) > 0                   # nothing silent


def test_agent_learns_which_transform_the_action_causes():
    # THE CORE CLAIM: action A secretly moves the dot DOWN. The agent is told only the generic transforms.
    # After experience, its most-believed transform for A must BE "DOWN" -- discovered via prediction error.
    world = ToyWorld(secret={"A": (1, 0)})     # DOWN is (+1, 0)
    agent, _, _, _ = _run(world, steps=12, actions=["A"])
    beliefs = {t: agent.belief.get(("A", t), 0.0) for t in unit_transforms()}
    best = max(beliefs, key=beliefs.get)
    assert best == "DOWN", "learned mapping wrong: %r" % beliefs
    # and it is decisively above the alternatives (not a coin-flip)
    assert beliefs["DOWN"] > beliefs["STAY"]
    assert beliefs["DOWN"] > beliefs["UP"]


def test_committed_prediction_error_drops_as_it_learns():
    # loop closure means the FEEDBACK actually improves the ACT: the committed prediction's residual
    # (the surprise the agent's OWN chosen move left) should fall as belief converges.
    world = ToyWorld(secret={"A": (1, 0)})
    _, committed_res, _, _ = _run(world, steps=14, actions=["A"])
    early = sum(committed_res[:4]) / 4.0
    late = sum(committed_res[-4:]) / 4.0
    assert late < early, "committed residual did not fall: early=%.2f late=%.2f" % (early, late)


def test_pe_integral_is_monotone_and_grows():
    # the brake invariant surfaced through the loop: the record of surprise only ever grows.
    world = ToyWorld(secret={"A": (1, 0)})
    _, _, integral, _ = _run(world, steps=10, actions=["A"])
    assert all(integral[i] <= integral[i + 1] for i in range(len(integral) - 1))  # monotone
    assert integral[-1] > 0.0                   # it WAS surprised (an unsurprised system has no HERE)


def test_pose_alpha_moves_off_its_prior():
    # the pose learns through the loop -- alpha is not frozen at 0.5.
    world = ToyWorld(secret={"A": (1, 0)})
    agent, _, _, _ = _run(world, steps=12, actions=["A"])
    assert agent.pose.alpha != 0.5
    assert len(agent.pose.history) == 12        # every step fed the pose an encounter


def test_refuted_transforms_are_not_committed():
    # a consistently-wrong transform accrues rejection weight; once refuted it must not be the committed act.
    world = ToyWorld(secret={"A": (1, 0)})
    agent, _, _, _ = _run(world, steps=16, actions=["A"])
    # at least one clearly-wrong transform (the opposite, UP) should be refuted by now
    refuted = [t for t in unit_transforms() if agent.ledger.is_refuted("A->%s" % t, agent.clock)]
    assert refuted, "nothing was ever refuted -- the ledger arm of the loop is dead"
    # and the agent's final committed choice is never a refuted signature
    frame = world.frame()
    ctrl = agent.perceive(frame)
    action, tname, _ = agent.choose(frame, ctrl)
    assert not agent.ledger.is_refuted(agent._sig(action, tname), agent.clock)


def test_no_downsampling_through_the_loop():
    # the hard bound holds across every frame the loop touched: shape never shrank.
    world = ToyWorld(shape=(6, 6), secret={"A": (1, 0)})
    _, _, _, shapes = _run(world, steps=10, actions=["A"])
    assert shapes == {(6, 6)}                    # every frame stayed full-resolution


def test_two_actions_are_discriminated():
    # with two actions the agent should not confuse them: whichever action it learns, it maps to the
    # transform THAT action truly causes (never the other action's effect).
    world = ToyWorld(secret={"A": (1, 0), "B": (0, 1)})   # A->DOWN, B->RIGHT
    agent, _, _, _ = _run(world, steps=24, actions=["A", "B"])
    # for whichever actions it actually exercised (has belief for), the argmax transform must be the true one
    truth = {"A": "DOWN", "B": "RIGHT"}
    exercised = {a for (a, _t) in agent.belief}
    assert exercised, "no action was ever exercised"
    for a in exercised:
        bel = {t: agent.belief.get((a, t), 0.0) for t in unit_transforms()}
        if max(bel.values()) > 0:               # only judge actions it actually learned something about
            assert max(bel, key=bel.get) == truth[a], "action %s mislearned: %r" % (a, bel)


def test_answer_is_not_encoded_in_construction():
    # STRUCTURAL guarantee: the agent is built with generic transforms only; the secret is never passed in.
    agent = AgentLoop(actions=["A", "B"])
    # the transforms are the five generic unit moves -- nothing game-specific
    assert set(agent.transforms) == {"STAY", "UP", "DOWN", "LEFT", "RIGHT"}
    # belief starts EMPTY: it knows no mapping at birth
    assert agent.belief == {}
