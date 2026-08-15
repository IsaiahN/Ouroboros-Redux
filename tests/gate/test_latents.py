"""L1 GATE (KNOBS A2, REGISTER L): planner cost_per_action is a MEASURED LATENT.

The ESTIMATOR is the socket (one global mechanism for all games -- never a
per-game knob); the ESTIMATE is content, read from the books per (game, level).

EVIDENCE SOURCE (discovered, documented in latents.py): the fabric's collective
"settlements" stream -- one record per settled action carrying (agent, game,
PLAYING level, nontrivial). game_results (SQLite) holds only per-episode totals
(game grain, no per-level split) and is unreachable from the planner; the
settlements ledger has both the per-level grain (A3-2 PLAYING-level convention)
and the planner's existing handle (gamma.fabric).

THE DERIVATION: a COMPLETION RUN is one agent's contiguous settled actions at
playing level L immediately followed by that agent's first record at L+1 (the
level-up, in append order). Actions-per-level-completion is the run's length;
cost_per_action = total actions / total NONTRIVIAL actions across the (game, L)
completion runs -- the ledgered price, in budget actions, of one EFFECTIVE
(frame-changing) click, which is what a plan step presumes. Unit-honest:
always >= 1 when effective clicks exist; ls20-style 2-click moves read ~2.

FALSIFIERS pinned here: no completion evidence -> cost 1.0 with an honest
MISSING flag (never invented); synthetic completion runs -> the exact ratio;
non-completing exploration contributes nothing; pure + bounded (replayable,
windowed read); the planner uses the estimator ONLY when the caller passes
cost_per_action=None -- explicit costs leave behavior and the returned plan
dict byte-identical to current.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import effects as E
from engines.egocentric.fabric import KnowledgeFabric

GAME = "g1"


def _L():
    try:
        from engines.egocentric.latents import (
            ESTIMATOR,  # noqa: F401
            ActionCostEstimator,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.latents missing (%s) -- L1 has not landed" % e)
    from engines.egocentric import latents
    return latents


def _settle(fab, agent, level, nontrivial=True, game=GAME, n=1):
    for _ in range(n):
        fab.append("collective", "settlements", {
            "agent": str(agent), "game": str(game), "level": int(level),
            "action": 6, "members": 1, "best": 0.0,
            "nontrivial": bool(nontrivial), "atom_key": None, "atom_bin": None})


def _completion_fabric(tmp_path, name="f"):
    """agent a1 completes playing level 1 in 4 actions (3 nontrivial); agent a2
    explores level 1 forever (10 actions) and never completes it."""
    fab = KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")
    _settle(fab, "a1", 1, nontrivial=True, n=3)
    _settle(fab, "a1", 1, nontrivial=False, n=1)
    _settle(fab, "a1", 2, nontrivial=True, n=1)     # the level-up: run closed
    _settle(fab, "a2", 1, nontrivial=True, n=10)    # never reaches level 2
    return fab


class TestTheEstimate:

    def test_no_evidence_is_fallback_with_missing_flag(self, tmp_path):
        """The honest fallback: an empty book estimates NOTHING -- 1.0, flagged."""
        lat = _L()
        fab = KnowledgeFabric(str(tmp_path / "empty"), agent_id="a", kin_key="v4")
        est = lat.ESTIMATOR.cost_per_action(fab, GAME, 1)
        assert est["cost"] == 1.0 and est["missing"] is True
        assert est["completions"] == 0

    def test_completion_run_yields_the_exact_ratio(self, tmp_path):
        """One completion run: 4 actions, 3 nontrivial -> cost 4/3, not missing."""
        lat = _L()
        fab = _completion_fabric(tmp_path)
        est = lat.ESTIMATOR.cost_per_action(fab, GAME, 1)
        assert est["missing"] is False and est["completions"] == 1
        assert est["actions"] == 4 and est["effective"] == 3
        assert abs(est["cost"] - 4.0 / 3.0) < 1e-12

    def test_non_completing_exploration_contributes_nothing(self, tmp_path):
        """a2's 10 open-ended actions are not completion evidence: the estimate
        equals the a1-only estimate exactly."""
        lat = _L()
        fab = _completion_fabric(tmp_path)
        solo = KnowledgeFabric(str(tmp_path / "solo"), agent_id="a", kin_key="v4")
        _settle(solo, "a1", 1, nontrivial=True, n=3)
        _settle(solo, "a1", 1, nontrivial=False, n=1)
        _settle(solo, "a1", 2, nontrivial=True, n=1)
        assert (lat.ESTIMATOR.cost_per_action(fab, GAME, 1)
                == lat.ESTIMATOR.cost_per_action(solo, GAME, 1))

    def test_scoped_per_game_and_level(self, tmp_path):
        """The estimate is (game, level)-scoped data: another game's completions
        and another level's runs answer MISSING, never bleed."""
        lat = _L()
        fab = _completion_fabric(tmp_path)
        assert lat.ESTIMATOR.cost_per_action(fab, "other", 1)["missing"] is True
        assert lat.ESTIMATOR.cost_per_action(fab, GAME, 3)["missing"] is True

    def test_the_measured_ground_truth_sequence_is_recovered(self, tmp_path):
        """A2/A6-3 VERIFICATION (pre-wiring condition): against a synthetic
        ledger reproducing the KNOWN measured ground truth -- completion runs
        costing 1,2,2,1,2,1,2 across seven levels (the A2 reading) -- the
        estimator recovers exactly that sequence, level by level. The live
        cost call sites still pass explicit costs; flipping them to the
        estimate is a SEPARATE decision, gated on this test."""
        lat = _L()
        fab = KnowledgeFabric(str(tmp_path / "gt"), agent_id="a", kin_key="v4")
        truth = [1, 2, 2, 1, 2, 1, 2]
        for lv, cost in enumerate(truth, start=1):
            # cost c == actions/effective: 2 effective clicks + 2*(c-1) misses
            _settle(fab, "a1", lv, nontrivial=True, n=2)
            if cost > 1:
                _settle(fab, "a1", lv, nontrivial=False, n=2 * (cost - 1))
        _settle(fab, "a1", len(truth) + 1, nontrivial=True, n=1)   # close L7's run
        got = [lat.ESTIMATOR.cost_per_action(fab, GAME, lv)
               for lv in range(1, len(truth) + 1)]
        assert all(e["missing"] is False and e["completions"] == 1 for e in got)
        assert [e["cost"] for e in got] == [float(c) for c in truth], (
            "the estimator must read back the non-monotonic measured sequence "
            "exactly -- a latent, never a constant")

    def test_pure_bounded_replayable(self, tmp_path):
        """Two estimator instances over the same ledger prefix agree, call after
        call (the replay law), and the read is windowed by MAX_RECORDS."""
        lat = _L()
        fab = _completion_fabric(tmp_path, name="shared")
        fb = KnowledgeFabric(str(tmp_path / "shared"), agent_id="b", kin_key="v4")
        e1 = lat.ESTIMATOR.cost_per_action(fab, GAME, 1)
        e2 = lat.ActionCostEstimator().cost_per_action(fb, GAME, 1)
        assert e1 == e2 == lat.ESTIMATOR.cost_per_action(fab, GAME, 1)
        assert int(lat.MAX_RECORDS) > 0, "the read must be bounded"

    def test_the_estimator_is_global_never_game_conditioned(self):
        """The OOD law at the estimator: one mechanism for all games -- no game
        id may appear in latents.py logic (estimates are data, keyed at call)."""
        lat = _L()
        with open(lat.__file__, encoding="utf-8") as f:
            src = f.read()
        for gid in ("ar25", "ls20", "vc33", "lp85", "cn04"):
            assert gid not in src, "latents.py names a game -- a latent became a knob"


class TestThePlannerHookup:

    def _gamma_with_increment(self, fab):
        g = E.Gamma(fab)
        ids = []
        for v in (3, 4):
            b = np.zeros((5, 5), dtype=int)
            b[2, 2] = v
            a = b.copy()
            a[2, 2] = v + 1
            ids.append(g.add(E.learn_effect(b, 6, a), game=GAME, level=1))
        return g

    def test_none_cost_uses_the_estimate(self, tmp_path):
        """cost_per_action=None -> the planner prices steps at the books' rate
        and reports the estimate ON the plan (estimates are data)."""
        _L()
        from engines.egocentric.planner import plan_to_identity
        fab = _completion_fabric(tmp_path)
        g = self._gamma_with_increment(fab)
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int)
        ref[2, 2] = 5
        out = plan_to_identity(ws, ref, g, game=GAME, level=1,
                               budget=100.0, cost_per_action=None)
        assert out is not None and len(out["steps"]) == 2
        assert abs(out["cost_per_action"] - 4.0 / 3.0) < 1e-12
        assert out["cost_missing"] is False and out["feasible"] is True
        tight = plan_to_identity(ws, ref, g, game=GAME, level=1,
                                 budget=2.0, cost_per_action=None)
        assert tight is not None and tight["feasible"] is False, (
            "2 steps at the ledgered 4/3 rate cost 8/3 > 2 -- the estimate must "
            "actually price feasibility, not decorate it")

    def test_none_cost_without_evidence_falls_back_flagged(self, tmp_path):
        _L()
        from engines.egocentric.planner import plan_to_identity
        fab = KnowledgeFabric(str(tmp_path / "noev"), agent_id="a", kin_key="v4")
        g = self._gamma_with_increment(fab)
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int)
        ref[2, 2] = 5
        out = plan_to_identity(ws, ref, g, game=GAME, level=1,
                               budget=100.0, cost_per_action=None)
        assert out is not None and out["cost_per_action"] == 1.0
        assert out["cost_missing"] is True, "the fallback must be FLAGGED, never silent"
        assert out["feasible"] is True

    def test_explicit_cost_is_byte_identical_to_current(self, tmp_path):
        """A caller-passed cost bypasses the estimator entirely: the returned
        dict keeps its exact current shape (no cost_* keys) and values."""
        _L()
        from engines.egocentric.planner import plan_to_identity
        fab = _completion_fabric(tmp_path)
        g = self._gamma_with_increment(fab)
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 3
        ref = np.zeros((5, 5), dtype=int)
        ref[2, 2] = 5
        out = plan_to_identity(ws, ref, g, game=GAME, level=1,
                               budget=100.0, cost_per_action=1.0)
        assert out is not None and set(out) == {"steps", "feasible"}, (
            "explicit-cost calls must return the unchanged current dict shape")
