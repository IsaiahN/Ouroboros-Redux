"""B5 GATE (BUILD_PROGRAM_2 W1): starvation -> seed_bias full wiring (not just
the probe cap).

THE CONTRACT: AffectGains.seed_gain(game) — a SEPARATE method (gains() keys stay
exactly {seed_bias, mint_bar}, gate-asserted elsewhere) returning the APPLIED
seed bias at the loop's consumption site:
  * base   = gains()["seed_bias"] (untouched);
  * boost  = starvation_steer's bounded multiplicative widening, PLUS a
    SWALLOW_STEP per distinct swallowed block (B4's consumer), capped at
    STARVE_CEIL;
  * applied = min(1.0, base * boost) — multiplicative, capped;
  * pure over the streams (replayable), neutral on empty streams.
Wiring: the loop's [AFFECT] site consumes seed_gain, stores the widening, and
the explore rotation in _act widens by it (bounded).

Run pre-build: failed (method absent; loop consumed nothing).
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


def _gains(fab):
    from engines.egocentric.affect import AffectGains
    a = AffectGains(fab)
    if not hasattr(a, "seed_gain"):
        pytest.fail("AffectGains.seed_gain missing — B5 has not landed")
    return a


def _starve(fab, game="g1"):
    from engines.egocentric.starvation import StarvationBook
    StarvationBook(fab).settle_episode(
        {"g1": 200, "g2": 0, "g3": 0, "g4": 0, "g5": 0, "g6": 0, "g7": 0,
         "mint_tried": 0, "mint_passed": 0, "bank_tried": 0, "bank_passed": 0},
        game=game, level=1, budget_spent=100)


class TestTheWidening:

    def _fab(self, tmp_path, name="f"):
        return KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")

    def test_neutral_on_empty_streams(self, tmp_path):
        a = _gains(self._fab(tmp_path))
        sg = a.seed_gain("g1")
        assert sg["boost"] == 1.0
        assert sg["applied"] == sg["base"] == a.gains()["seed_bias"]

    def test_starvation_widens_multiplicatively_within_the_cap(self, tmp_path):
        f = self._fab(tmp_path)
        _starve(f)
        a = _gains(f)
        sg = a.seed_gain("g1")
        assert 1.0 < sg["boost"] <= a.STARVE_CEIL, "bounded, multiplicative"
        assert sg["applied"] == min(1.0, sg["base"] * sg["boost"])
        assert sg["applied"] > sg["base"], "the applied bias must WIDEN"
        assert "NO_STABLE_REFERENCE" in sg["codes"]

    def test_swallow_records_widen_further_but_never_past_the_cap(self, tmp_path):
        """B4's consumer: swallowed blocks add effort widening — same read
        path, same ceiling, never a price."""
        from engines.egocentric.swallow import SwallowBook
        f = self._fab(tmp_path)
        _starve(f)
        base_boost = _gains(f).seed_gain("g1")["boost"]
        SwallowBook(f).settle_episode(
            {"OBSERVER": 2, "PLANNER": 1, "MINT_DRAIN": 3, "FABRIC": 1,
             "AFFECT": 1, "SPINE": 2, "FRONTIER": 1, "BINDER_FEED": 1},
            game="g1", level=1)
        a = _gains(f)
        sg = a.seed_gain("g1")
        assert sg["boost"] > base_boost, "swallowed blocks add widening"
        assert sg["boost"] <= a.STARVE_CEIL, "the cap holds"
        assert sg["swallowed"], "the consumed blocks are legible"

    def test_pure_over_the_streams(self, tmp_path):
        f = self._fab(tmp_path)
        _starve(f)
        f2 = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        assert _gains(f).seed_gain("g1") == _gains(f2).seed_gain("g1")

    def test_gains_keys_stay_exactly_the_two_channels(self, tmp_path):
        f = self._fab(tmp_path)
        _starve(f)
        assert set(_gains(f).gains().keys()) == {"seed_bias", "mint_bar",
                                                 "persist"}, (
            "seed_gain is a SEPARATE method — gains() is the priced contract "
            "(+ the persistence modulator, PREREG_PERSISTENCE_MONITOR.md; it "
            "is not widened by starvation either)")
        assert _gains(f).gains()["persist"] == 0.0


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_the_affect_site_consumes_seed_gain_and_narrates(self):
        src = self._src()
        assert "seed_gain" in src, (
            "the loop never consumes the applied seed bias (B5 unlanded)")
        i = src.find("seed_gain")
        window = src[max(0, i - 1200):i + 1200]
        assert "[AFFECT]" in window, "the widening must ride the [AFFECT] line"

    def test_the_explore_rotation_applies_the_widening(self):
        src = self._src()
        assert "_ego_explore_widen" in src
        i = src.find("% top_n")
        assert i != -1, "the explore rotation vanished"
        window = src[max(0, i - 1500):i]
        assert "_ego_explore_widen" in window, (
            "the widening never reaches the explore rotation — starvation "
            "still steers only the probe cap")
