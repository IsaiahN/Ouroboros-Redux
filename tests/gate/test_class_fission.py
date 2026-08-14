"""B10 falsifier: the CLASS-FISSION SOCKET -- hidden types split a bimodal class.

One object class, one predicted transform: it VERIFIES on some instances and FAILS on others,
consistently (the essentialism signal; Xu-Carey). The socket tracks per-instance settlement
outcomes; bimodal beyond threshold -> FISSION: two subclass identities (class__a / class__b),
distinguished by a discriminating feature when one is findable, else by instance bucket. The
fission event is a readable record (the probe target); resolve() keys predictions on the
subclass so they track separately. Unimodal classes NEVER fission; a noisy instance below the
purity threshold is no evidence. The binder drops the parent's stale evidence on fission so the
subclasses re-earn their own bindings.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _socket():
    try:
        from engines.egocentric.bank import (
            ClassFissionSocket,  # noqa: F401 -- the import IS the availability probe
        )
    except ImportError:
        pytest.fail("bank.ClassFissionSocket missing -- B10 has not landed")
    from engines.egocentric.bank import ClassFissionSocket as S
    return S


class TestFissionTrigger:

    def test_bimodal_outcomes_trigger_fission(self):
        s = _socket()()
        for _ in range(3):
            s.note_outcome("blob", "i1", verified=True)
        assert not s.fission_events, "one pure mode is not bimodality"
        for _ in range(3):
            s.note_outcome("blob", "i2", verified=False)
        assert len(s.fission_events) == 1, "a consistent split must fission the class"
        ev = s.fission_events[0]
        assert ev["class"] == "blob"
        assert ev["subclasses"] == ["blob__a", "blob__b"]
        assert s.resolve("blob", "i1") == "blob__a"
        assert s.resolve("blob", "i2") == "blob__b"

    def test_unimodal_never_fissions(self):
        s = _socket()()
        for inst in ("i1", "i2", "i3"):
            for _ in range(5):
                s.note_outcome("blob", inst, verified=True)
        assert not s.fission_events
        assert s.resolve("blob", "i1") == "blob", "an unfissioned class keeps its identity"

    def test_a_noisy_instance_below_purity_is_no_evidence(self):
        s = _socket()()
        for _ in range(4):
            s.note_outcome("blob", "i1", verified=True)
        s.note_outcome("blob", "i2", verified=False)
        s.note_outcome("blob", "i2", verified=True)
        s.note_outcome("blob", "i2", verified=False)     # 1/3 verified: purity < threshold
        assert not s.fission_events, "an inconsistent instance is noise, not a hidden type"

    def test_fission_happens_once(self):
        s = _socket()()
        for _ in range(3):
            s.note_outcome("blob", "i1", verified=True)
            s.note_outcome("blob", "i2", verified=False)
        for _ in range(3):
            s.note_outcome("blob", "i3", verified=False)
        assert len(s.fission_events) == 1, "a fissioned class does not fission again"


class TestDiscriminatingFeature:

    def test_feature_split_is_named_when_findable(self):
        s = _socket()()
        for _ in range(3):
            s.note_outcome("blob", "i1", verified=True, features={"colour": 4})
            s.note_outcome("blob", "i2", verified=False, features={"colour": 7})
        ev = s.fission_events[0]
        assert ev["feature"] == {"name": "colour", "a": 4, "b": 7}, (
            "the discriminating feature is the probe target -- name it when findable")
        assert s.resolve("blob", "never-seen", features={"colour": 7}) == "blob__b", (
            "a new instance wearing the b-feature joins the b-subclass")
        assert s.resolve("blob", "never-seen-2", features={"colour": 4}) == "blob__a"

    def test_no_feature_means_instance_bucket(self):
        s = _socket()()
        for _ in range(3):
            s.note_outcome("blob", "i1", verified=True)
            s.note_outcome("blob", "i2", verified=False)
        assert s.fission_events[0]["feature"] is None
        assert s.fission_events[0]["assignment"] == {"i1": "blob__a", "i2": "blob__b"}


class TestPredictionsSeparateAfterFission:

    def test_subclass_identities_key_separate_evidence(self):
        """After fission, evidence accrued under the resolved identities diverges: the
        a-instances bind WORKSPACE, the b-instances bind REFERENCE -- one pre-fission class
        could never hold both verdicts at once."""
        from engines.egocentric.binder import RoleBinder
        s = _socket()()
        for _ in range(3):
            s.note_outcome("blob", "i1", verified=True)
            s.note_outcome("blob", "i2", verified=False)
        binder = RoleBinder(min_evidence=3)
        for _ in range(3):
            binder.observe(s.resolve("blob", "i1"), action=6, moved_with_action=False,
                           mutated_on_contact=True, changed_without_agent=False,
                           scalar_delta=0)
            binder.observe(s.resolve("blob", "i2"), action=6, moved_with_action=False,
                           mutated_on_contact=False, changed_without_agent=False,
                           scalar_delta=0)
        a = binder.binding("blob__a")
        b = binder.binding("blob__b")
        assert a is not None and a["slot"] == "WORKSPACE"
        assert b is not None and b["slot"] == "REFERENCE"

    def test_binder_drops_the_parent_evidence_on_fission(self):
        from engines.egocentric.binder import RoleBinder
        binder = RoleBinder(min_evidence=3)
        if not hasattr(binder, "on_fission"):
            pytest.fail("RoleBinder.on_fission missing -- B10 has not landed")
        for _ in range(3):
            binder.observe("blob", action=6, moved_with_action=False,
                           mutated_on_contact=True, changed_without_agent=False,
                           scalar_delta=0)
        assert binder.binding("blob") is not None
        binder.on_fission("blob")
        assert binder.binding("blob") is None, (
            "the parent's evidence is stale after fission; the subclasses re-earn")
