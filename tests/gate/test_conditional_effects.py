"""B9 falsifier: CONDITIONAL-EFFECT CONSTRUCTOR (arity-3) -- EFFECT_IF.

The button-door: the SAME action in the SAME local context yields DIVERGENT outcomes, and a
REMOTE state predicate (a cell elsewhere whose pre-value differs between the observation sets)
distinguishes them. A bounded ConditionalMiner buffers (pre, action, post) per action; on the
second, divergent observation it constructs EFFECT_IF {condition: {cells}, then, else}. apply
honors the condition both ways. The router feeds the miner from settled workspace bets that
carry their frames: a TRANSFERRED then a BROKEN_MECHANISM on the same action is exactly the
divergence signal, and the constructed conditional lands where the caller can read it.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _E():
    from engines.egocentric import effects as E
    if not hasattr(E, "ConditionalMiner"):
        pytest.fail("effects.ConditionalMiner missing -- B9 has not landed")
    return E


BUTTON = (1, 8)
DOOR = ((5, 5), (5, 6))


def _button_door():
    """pre_on: button lit (5) -> the door (colour 2) flips to 8. pre_off: button dark (0)
    -> the same action does nothing. Everything else identical."""
    pre_on = np.zeros((10, 10), dtype=int)
    pre_on[BUTTON] = 5
    for r, c in DOOR:
        pre_on[r, c] = 2
    post_on = pre_on.copy()
    for r, c in DOOR:
        post_on[r, c] = 8
    pre_off = pre_on.copy()
    pre_off[BUTTON] = 0
    post_off = pre_off.copy()
    return pre_on, post_on, pre_off, post_off


class TestTheMiner:

    def test_two_divergent_observations_emit_effect_if(self):
        E = _E()
        pre_on, post_on, pre_off, post_off = _button_door()
        m = E.ConditionalMiner()
        assert m.feed(pre_on, 6, post_on) is None, "one observation is no divergence"
        atom = m.feed(pre_off, 6, post_off)
        assert atom is not None, "the second, divergent outcome must construct the conditional"
        assert atom["kind"] == "EFFECT_IF" and atom["arity"] == 3
        assert atom["action"] == 6
        assert atom["condition"]["cells"] == [[1, 8, 5]], (
            "the condition is the remote predicate: the button cell at its THEN value")
        assert atom["then"] is not None and atom["then"]["kind"] == "EFFECT"
        assert atom.get("else") is None, "an inert other-branch is no else transform"

    def test_order_of_observations_does_not_matter(self):
        E = _E()
        pre_on, post_on, pre_off, post_off = _button_door()
        m = E.ConditionalMiner()
        assert m.feed(pre_off, 6, post_off) is None
        atom = m.feed(pre_on, 6, post_on)
        assert atom is not None and atom["kind"] == "EFFECT_IF"
        assert atom["condition"]["cells"] == [[1, 8, 5]], (
            "the THEN branch is the one that changed the frame, whichever arrived first")

    def test_apply_honors_the_condition_both_ways(self):
        E = _E()
        pre_on, post_on, pre_off, post_off = _button_door()
        m = E.ConditionalMiner()
        m.feed(pre_on, 6, post_on)
        atom = m.feed(pre_off, 6, post_off)
        out_on = E.apply_effect(atom, pre_on)
        assert out_on is not None and (out_on == post_on).all(), "condition holds -> then fires"
        out_off = E.apply_effect(atom, pre_off)
        assert out_off is not None and (out_off == post_off).all(), (
            "condition fails, no else -> the action does nothing")

    def test_same_outcome_twice_is_not_conditional(self):
        E = _E()
        pre_on, post_on, _, _ = _button_door()
        m = E.ConditionalMiner()
        assert m.feed(pre_on, 6, post_on) is None
        assert m.feed(pre_on, 6, post_on) is None, "no divergence, no conditional"

    def test_a_non_remote_difference_is_not_a_predicate(self):
        """If the two pre-frames differ INSIDE the changed region there is no remote
        predicate -- the miner must not invent one."""
        E = _E()
        pre_on, post_on, _, _ = _button_door()
        m = E.ConditionalMiner()
        m.feed(pre_on, 6, post_on)
        pre2 = pre_on.copy()
        pre2[5, 5] = 3                                # differs inside the door itself
        atom = m.feed(pre2, 6, pre2.copy())
        assert atom is None

    def test_the_buffer_is_bounded(self):
        E = _E()
        m = E.ConditionalMiner()
        base = np.zeros((6, 6), dtype=int)
        for i in range(20):
            f = base.copy()
            f[0, 0] = 0                                # inert everywhere: nothing to mine
            f[3, 3] = i % 2
            m.feed(f, 6, f.copy())
        assert m.history_len(6) <= m.per_key, "the per-key history must stay bounded"


class TestRouterWiring:

    def test_divergence_at_the_router_constructs_the_conditional(self, tmp_path):
        from engines.egocentric.bank import PredictorBank
        from engines.egocentric.fabric import KnowledgeFabric
        from engines.egocentric.router import ResidualRouter
        E = _E()
        pre_on, post_on, pre_off, post_off = _button_door()
        g = E.Gamma(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))
        g.add(E.learn_effect(pre_on, 6, post_on), game="g1", level=1)

        bank = PredictorBank(gamma=g, game="g1", level=1)
        miner = E.ConditionalMiner()
        router = ResidualRouter(miner=miner)

        bank.commit({"WORKSPACE": pre_on}, action=6)
        out = bank.settle({"WORKSPACE": post_on})
        assert router.route("WORKSPACE", out["WORKSPACE"]) == "TRANSFERRED"

        bank.commit({"WORKSPACE": pre_off}, action=6)
        out2 = bank.settle({"WORKSPACE": post_off})
        assert router.route("WORKSPACE", out2["WORKSPACE"]) == "BROKEN_MECHANISM", (
            "the known atom mispredicted: the button was dark")

        assert router.conditional_atoms, (
            "the router must feed the miner from frame-carrying settlements and expose "
            "the constructed conditional")
        atom = router.conditional_atoms[0]
        assert atom["kind"] == "EFFECT_IF"
        assert atom["condition"]["cells"] == [[1, 8, 5]]
