"""CK-2a: EFFERENCE-COPY SUBTRACTION (von Holst; Wolpert) -- attacks g4=0.

The binder attributed world-vs-self change by click proximity: any mutation within
radius 1 of the click read as "my contact", anything further as "the world". An
independent mover passing next to the click was minted a WORKSPACE; a reference
pane blinking on its own was branded by whichever side of the radius it fell on.
REFERENCE never bound (g4=0 in [PLAN-GATE]).

The cure: predict the sensory consequence of MY OWN action (the bank/gamma
committed prediction; floor: the old click neighbourhood), SUBTRACT it from the
observed change. Change inside the predicted mask is reafference (my contact,
feeds mutated_on_contact); change outside it is exafference (the world, feeds
changed_without_agent). REFERENCE tolerates exafference: the world changing on
its own does not disqualify the world frame -- only MY influence does.

FALSIFIER (this file, failing first): a synthetic episode where the agent's click
changes cells at the click site AND an independent mover changes other cells in
the same step. The old proximity path misattributes the near mover as contact-
mutation (WORKSPACE). The new path: the mover accrues changed_without_agent and
reaches REFERENCE; the click-site object accrues contact-mutation and cannot.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _B():
    try:
        from engines.egocentric.binder import (
            RoleBinder,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.binder missing (%s) -- W1b has not landed" % e)
    from engines.egocentric.binder import RoleBinder as B
    return B


def _binder(min_evidence=3):
    b = _B()(min_evidence=min_evidence)
    if not hasattr(b, "observe_attributed"):
        pytest.fail("RoleBinder.observe_attributed missing -- CK-2a has not landed")
    return b


# The synthetic episode, shared by every test below.
# Click at (5, 5); the click changes the cell UNDER the click (class 3).
# An independent mover (class 9) changes cells at (4, 6)/(4, 7) in the SAME
# step -- (4, 6) is within radius 1 of the click, so the OLD heuristic reads
# the mover as "my contact". The efference copy predicts exactly {(5, 5)}.
CLICK = (5, 5)
MASK = {(5, 5)}                    # predicted self-caused change (sharp)
SITE_CHANGED = {(5, 5)}            # the click-site object's changed cells
MOVER_CHANGED = {(4, 6), (4, 7)}   # the mover's changed cells (one near, one far)


class TestTheOldPathMisattributes:

    def test_proximity_mints_the_independent_mover_a_workspace(self):
        """DOCUMENTATION of the measured failure: under the old call-site
        heuristic (any prior cell within radius 1 of the click => contact),
        the mover's mutation reads as mutated_on_contact and the mover binds
        WORKSPACE -- an independent object minted as my workspace. This is
        exactly what the old cognitive_loop W4c-1 flags computed."""
        b = _B()(min_evidence=3)
        for _ in range(4):
            near = any(abs(r - CLICK[0]) <= 1 and abs(c - CLICK[1]) <= 1
                       for (r, c) in MOVER_CHANGED)
            assert near, "the episode must place the mover inside the old radius"
            b.observe(object_class=9, action=6, moved_with_action=False,
                      mutated_on_contact=near, changed_without_agent=not near,
                      scalar_delta=0)
        bind = b.binding(9)
        assert bind is not None and bind["slot"] == "WORKSPACE", (
            "the misattribution this prereg targets: proximity minted the "
            "independent mover a WORKSPACE")


class TestEfferenceCopySubtraction:

    def test_the_mover_accrues_world_evidence_and_reaches_reference(self):
        """Mover cells fall OUTSIDE the predicted mask => changed_without_agent;
        exafference does not disqualify the world frame => REFERENCE binds."""
        b = _binder()
        for _ in range(4):
            b.observe_attributed(9, 6, False, True, MOVER_CHANGED, MASK, 0)
        bind = b.binding(9)
        assert bind is not None and bind["slot"] == "REFERENCE", (
            "world-caused change must feed changed_without_agent and still "
            "permit REFERENCE -- got %r" % (bind,))

    def test_the_click_site_object_accrues_contact_and_cannot_be_reference(self):
        """Click-site cells fall INSIDE the predicted mask => mutated_on_contact
        => WORKSPACE, never REFERENCE."""
        b = _binder()
        for _ in range(4):
            b.observe_attributed(3, 6, False, True, SITE_CHANGED, MASK, 0)
        bind = b.binding(3)
        assert bind is not None and bind["slot"] == "WORKSPACE", (
            "self-caused change must feed mutated_on_contact -- got %r" % (bind,))

    def test_the_full_episode_separates_the_two(self):
        """The falsifier proper: both objects change in the SAME steps; the
        subtraction separates them where proximity could not."""
        b = _binder()
        for _ in range(4):
            b.observe_attributed(3, 6, False, True, SITE_CHANGED, MASK, 0)
            b.observe_attributed(9, 6, False, True, MOVER_CHANGED, MASK, 0)
        assert b.binding(3)["slot"] == "WORKSPACE"
        assert b.binding(9)["slot"] == "REFERENCE"

    def test_no_mutation_accrues_no_attribution_either_way(self):
        b = _binder()
        for _ in range(4):
            b.observe_attributed(7, 6, False, False, set(), MASK, 0)
        bind = b.binding(7)
        assert bind is not None and bind["slot"] == "REFERENCE"

    def test_malformed_input_is_swallowed_to_the_counter(self):
        b = _binder()
        b.observe_attributed(1, 6, False, True, 123, 456, 0)   # not iterables
        assert b.errors >= 1, "a malformed observation must never raise"


class TestThePredictedChangeMask:

    def test_the_floor_is_the_old_click_neighbourhood(self):
        """With no gamma/bank knowledge the mask degrades to the old heuristic:
        the clicked cell and its radius-1 neighbourhood."""
        B = _B()
        if not hasattr(B, "predicted_change_mask"):
            pytest.fail("RoleBinder.predicted_change_mask missing -- CK-2a has not landed")
        mask = B.predicted_change_mask(None, 6, CLICK)
        want = {(CLICK[0] + dr, CLICK[1] + dc)
                for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
        assert mask == want

    def test_no_click_and_no_knowledge_is_an_empty_mask(self):
        B = _B()
        assert B.predicted_change_mask(None, 1, None) == set()

    def test_a_matching_effect_atom_sharpens_the_mask(self):
        """A stored EFFECT atom for this (game, level, action) IS the committed
        prediction: the mask is exactly its predicted diff -- NOT the radius-1
        blur, so the adjacent mover falls outside it."""
        B = _B()

        class _Fab:
            def __init__(self, recs):
                self._recs = recs

            def query(self, scope, topic, where=None):
                return [r for r in self._recs if where is None or where(r)]

        class _Gamma:
            def __init__(self, recs):
                self.fabric = _Fab(recs)

        atom = {"kind": "EFFECT", "action": 6, "context": [[3]],
                "transform": {"after": [[5]]}}
        gm = _Gamma([{"id": "a1", "game": "g", "level": 1, "atom": atom}])
        pre = np.zeros((9, 9), dtype=int)
        pre[5, 5] = 3
        mask = B.predicted_change_mask(pre, 6, CLICK, gamma=gm, game="g", level=1)
        assert mask == {(5, 5)}, "the atom's diff, not the blur -- got %r" % (mask,)
        assert not (mask & MOVER_CHANGED), "the adjacent mover must fall outside"

    def test_a_wrong_action_atom_is_ignored_and_the_floor_returns(self):
        B = _B()

        class _Fab:
            def __init__(self, recs):
                self._recs = recs

            def query(self, scope, topic, where=None):
                return [r for r in self._recs if where is None or where(r)]

        class _Gamma:
            def __init__(self, recs):
                self.fabric = _Fab(recs)

        atom = {"kind": "EFFECT", "action": 2, "context": [[3]],
                "transform": {"after": [[5]]}}
        gm = _Gamma([{"id": "a1", "game": "g", "level": 1, "atom": atom}])
        pre = np.zeros((9, 9), dtype=int)
        pre[5, 5] = 3
        mask = B.predicted_change_mask(pre, 6, CLICK, gamma=gm, game="g", level=1)
        want = {(CLICK[0] + dr, CLICK[1] + dc)
                for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
        assert mask == want


class TestTheWireIsLive:

    def test_record_result_feeds_the_sharpened_attribution(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        i = src.find("def record_result")
        body = src[i:i + 20000]
        assert "observe_attributed" in body, (
            "W4c-1 still feeds the binder through raw proximity flags -- the "
            "efference copy is unwired (starvation)")
        assert "predicted_change_mask" in body, (
            "W4c-1 never computes the predicted-change mask before feeding")
