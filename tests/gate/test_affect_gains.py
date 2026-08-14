"""W4a: affect — the gains on the deliberation loop, computed from the ledger, replay-testable.

Emotion is the endogenization of the hyperparameters: statistics over the agent's own books,
never a sensor, never a price. v1 exposes exactly TWO channels because exactly two knobs are
live (seed-bias for the explore aim; mint-bar for the mint threshold) — channels <= knobs, and
width/depth arrive with rooms. THE REPLAY TEST is the anti-proxy guard: affect(t) is a pure
function of the ledger prefix; replaying the books offline reproduces the trace byte-exactly.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


def _A():
    try:
        from engines.egocentric.affect import (
            AffectGains,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.affect missing (%s) -- W4a has not landed" % e)
    from engines.egocentric.affect import AffectGains as A
    return A


def _fabric_with_history(tmp_path, name="f", settles=10, nontrivial=5, mints=2, rejects=1):
    f = KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")
    for i in range(settles):
        f.append("collective", "settlements",
                 {"agent": "a", "game": "g1", "level": 1, "action": 6,
                  "best": 0.5, "nontrivial": i < nontrivial})
    for _ in range(mints):
        f.append("collective", "mint_verdicts", {"verdict": "mint", "game": "g1"})
    for _ in range(rejects):
        f.append("collective", "mint_verdicts", {"verdict": "reject", "game": "g1"})
    return f


class TestTheContract:

    def test_two_channels_bounded(self, tmp_path):
        a = _A()(_fabric_with_history(tmp_path))
        g = a.gains()
        assert set(g.keys()) == {"seed_bias", "mint_bar"}, (
            "channels <= knobs: exactly the two live knobs, no free-floating moods")
        assert 0.0 <= g["seed_bias"] <= 1.0
        assert a.MINT_BAR_FLOOR <= g["mint_bar"] <= a.MINT_BAR_CEIL
        assert a.MINT_BAR_FLOOR >= 1.0, "the bar's floor never dips below the standing guards"

    def test_desperation_raises_the_bar(self, tmp_path):
        """Long silence (no nontrivial settlements) must RAISE the mint bar, not lower it —
        desperation makes the mint pickier, never looser."""
        A = _A()
        quiet = A(_fabric_with_history(tmp_path, "q", settles=20, nontrivial=0))
        lively = A(_fabric_with_history(tmp_path, "l", settles=20, nontrivial=15))
        assert quiet.gains()["mint_bar"] > lively.gains()["mint_bar"]

    def test_the_replay_test(self, tmp_path):
        """affect(t) = f(ledger[0:t]) — two instances over the same books produce the identical
        trace. Private state is a second brain; there is none."""
        f = _fabric_with_history(tmp_path, "r", settles=12, nontrivial=4)
        A = _A()
        t1 = A(f).gains()
        f2 = KnowledgeFabric(str(tmp_path / "r"), agent_id="b", kin_key="v4")
        t2 = A(f2).gains()
        assert t1 == t2, "the affect trace must replay byte-exactly from the books alone"

    def test_narration(self, tmp_path):
        """No channel moves without the state being emitted — the legibility law."""
        a = _A()(_fabric_with_history(tmp_path))
        line = a.narrate()
        assert "seed_bias" in line and "mint_bar" in line
