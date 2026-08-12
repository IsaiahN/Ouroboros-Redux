"""W1b: the role binder — one invariance classifier, four verdicts. Self-locus generalised.

Roles by INVARIANCE, never appearance: BODY moves contingently on my action; WORKSPACE mutates
under my contact; REFERENCE is invariant under me; RESOURCE is monotone under my actions.
Publishes bindings (class -> slot + confidence), re-binds on level change, unbound = None.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _B():
    try:
        from engines.egocentric.binder import RoleBinder
    except Exception as e:
        pytest.fail("engines.egocentric.binder missing (%s) -- W1b has not landed" % e)
    from engines.egocentric.binder import RoleBinder as B
    return B


def _feed(b, cls, action, moved, mutated, autonomous, delta):
    b.observe(object_class=cls, action=action, moved_with_action=moved,
              mutated_on_contact=mutated, changed_without_agent=autonomous,
              scalar_delta=delta)


class TestTheFourVerdicts:

    def test_contingent_mover_binds_body(self):
        b = _B()(min_evidence=3)
        for i in range(6):
            _feed(b, cls=7, action=(i % 2) + 1, moved=(i % 2 == 0), mutated=False,
                  autonomous=False, delta=0)
        bind = b.binding(7)
        assert bind is not None and bind["slot"] == "BODY"

    def test_contact_mutation_binds_workspace(self):
        b = _B()(min_evidence=3)
        for _ in range(4):
            _feed(b, cls=3, action=6, moved=False, mutated=True, autonomous=False, delta=0)
        assert b.binding(3)["slot"] == "WORKSPACE"

    def test_invariance_binds_reference(self):
        b = _B()(min_evidence=3)
        for i in range(6):
            _feed(b, cls=9, action=(i % 3) + 1, moved=False, mutated=False,
                  autonomous=False, delta=0)
        assert b.binding(9)["slot"] == "REFERENCE"

    def test_monotone_scalar_binds_resource(self):
        b = _B()(min_evidence=3)
        for i in range(5):
            _feed(b, cls=5, action=(i % 2) + 1, moved=False, mutated=False,
                  autonomous=False, delta=-1)
        assert b.binding(5)["slot"] == "RESOURCE"

    def test_autonomy_defeats_body(self):
        """An object that changes WITHOUT the agent is never BODY -- the Goodhart guard,
        inherited from the self-locus."""
        b = _B()(min_evidence=3)
        for i in range(6):
            _feed(b, cls=2, action=(i % 2) + 1, moved=True, mutated=False,
                  autonomous=True, delta=0)
        bind = b.binding(2)
        assert bind is None or bind["slot"] != "BODY"

    def test_insufficient_evidence_is_unbound(self):
        b = _B()(min_evidence=3)
        _feed(b, cls=4, action=1, moved=True, mutated=False, autonomous=False, delta=0)
        assert b.binding(4) is None, "one observation binds nothing -- unbound is honest"

    def test_level_change_rebinds(self):
        b = _B()(min_evidence=3)
        for _ in range(6):
            _feed(b, cls=7, action=1, moved=True, mutated=False, autonomous=False, delta=0)
        assert b.binding(7) is not None
        b.on_level_change()
        assert b.binding(7) is None, "the maze redraws; bindings must re-earn themselves"

    def test_bindings_publish_confidence(self):
        b = _B()(min_evidence=3)
        for _ in range(4):
            _feed(b, cls=3, action=6, moved=False, mutated=True, autonomous=False, delta=0)
        bind = b.binding(3)
        assert "confidence" in bind and 0.0 < bind["confidence"] <= 1.0
