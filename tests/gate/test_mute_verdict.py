"""W4b: the mute verdict — quarantine + the empowerment probe.

Confirm -> mint + seed (live). Refute -> veto (live, measured). MUTE — the ground said
nothing — was the open link: a bet that cannot settle, an objective with no evidence either
way. Mute quarantines the item and answers with a DISCRIMINATING PROBE: the observation that
would make the ground speak. Every verdict is a force on the generator.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _V():
    try:
        from engines.egocentric.verdicts import (
            MuteHandler,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.verdicts missing (%s) -- W4b has not landed" % e)
    from engines.egocentric.verdicts import MuteHandler as V
    return V


class TestMute:

    def test_mute_quarantines_and_probes(self):
        v = _V()()
        out = v.mute(item={"kind": "objective", "cell": [3, 3]},
                     candidates=[(1, 1), (3, 3), (5, 5)],
                     observed_counts={(1, 1): 4, (3, 3): 2, (5, 5): 0})
        assert len(v.quarantine) == 1
        assert out["probe"] == (5, 5), (
            "the empowerment probe aims at the LEAST-observed candidate -- the observation "
            "that would make the ground speak")

    def test_quarantined_items_can_return(self):
        v = _V()()
        v.mute(item={"kind": "objective", "id": "x"}, candidates=[(1, 1)],
               observed_counts={(1, 1): 0})
        back = v.release("x")
        assert back is not None and len(v.quarantine) == 0, (
            "quarantine is a waiting room, not a grave -- defeasibility everywhere")

    def test_no_candidates_is_pure_quarantine(self):
        v = _V()()
        out = v.mute(item={"kind": "objective", "id": "y"}, candidates=[],
                     observed_counts={})
        assert out["probe"] is None and len(v.quarantine) == 1

    def test_deterministic_probe_choice(self):
        v = _V()()
        out1 = v.mute(item={"id": "a"}, candidates=[(2, 2), (1, 1)],
                      observed_counts={(2, 2): 0, (1, 1): 0})
        assert out1["probe"] == (1, 1), "ties break deterministically (sorted order)"
