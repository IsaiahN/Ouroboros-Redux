"""AMENDMENT 2 GATE: multi-rung rho -- the identity ladder measured, not partitioned.

⭐ WHY (KNOBS AMENDMENT 2): rho_bar=0.000 x153-pairs was a PARTITION ARTIFACT --
n_eff under ONE grain where correlation is undetectable. VERIFIED live: cn04 holds
64 rederivation verdicts for ka59's atom key while atom-set rho reads 0. Two
sameness notions were in play; the ladder freezes all the rungs:

  rung 0  KEY        canonical content hash, position-free (the novelty guard)
  rung 1  SIG_CLASS  sigma + ttype + params (current consumer matching / atom rho)
  rung 2  COARSE     sigma invariants + ttype only -- params (and the frame-local
                     mag class) dropped: the redescription rung

plus the REDERIVATION-TRAFFIC channel: cross-recognitions counted from A's verdict
stream against B's atom keyset. rho_report(fabrics) returns per-pair
{r0, r1, r2, traffic} -- a DISTRIBUTION capable of nonzero, never a partition.

FALSIFIERS: rungs ordered (r2 >= r1 -- rung 2 is a strict coarsening of rung 1);
a fixture where r1 = 0 but r2 > 0 (the partition artifact made visible); rung 0
catches key identity that sigma classes miss; traffic catches a synthetic
cross-recognition; sigma-less/old-shape records degrade to 0 / are skipped,
never raise.

Run pre-build: FAILED (rho had no rho_at, no rederivation_traffic, no rho_report).
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import rho


def _sig(i, mag="small"):
    """A distinct one-cell recolour signature per integer i."""
    return {"arity": 2, "bbox": "cell", "changed": "1",
            "colour_delta": [[int(i), int(i) + 1]], "conserved": False, "mag": mag}


def _rec(key, sigma=None, ttype=None, params=None, game="gA"):
    atom = {"kind": "EFFECT", "arity": 2, "key": str(key)}
    if sigma is not None:
        atom["sigma"] = dict(sigma)
    if ttype is not None:
        atom["ttype"] = ttype
    if params is not None:
        atom["params"] = params
    return {"id": "%s:0" % key, "type": "structural", "game": str(game),
            "level": 1, "atom": atom}


def _reder(key, game="gX"):
    return {"verdict": "rederivation", "game": game, "level": 1, "key": str(key)}


# ── rho_at: the ladder's rungs ────────────────────────────────────────────────

class TestRhoAtRungs:

    def test_identical_fabrics_read_one_at_every_rung(self):
        a = [_rec("k%d" % i, _sig(i), ttype="TRANSLATE", params={"dx": 1})
             for i in range(4)]
        b = [dict(r) for r in a]
        for rung in (0, 1, 2):
            assert rho.rho_at(a, b, rung) == pytest.approx(1.0), "rung %d" % rung

    def test_disjoint_fabrics_read_zero_at_every_rung(self):
        a = [_rec("a%d" % i, _sig(i), ttype="TRANSLATE", params={"dx": 1})
             for i in range(4)]
        b = [_rec("b%d" % i, _sig(10 + i), ttype="ROTATE", params={"k": 1})
             for i in range(4)]
        for rung in (0, 1, 2):
            assert rho.rho_at(a, b, rung) == pytest.approx(0.0), "rung %d" % rung

    def test_rung0_is_key_identity_blind_to_sigma(self):
        """The cn04/ka59 shape: SAME canonical key, sigma classes that differ
        (or are absent) -- rung 1 reads 0, rung 0 must read the overlap."""
        a = [_rec("shared-key", _sig(1))]
        b = [_rec("shared-key", _sig(7))]
        assert rho.rho_at(a, b, 1) == pytest.approx(0.0)
        assert rho.rho_at(a, b, 0) == pytest.approx(1.0), (
            "key identity is patch-level identity -- rung 0 must catch it")

    def test_rung1_matches_the_frozen_estimator(self):
        a = [_rec("a%d" % i, _sig(i)) for i in range(4)]
        b = [_rec("b%d" % i, _sig(i)) for i in range(2)] + \
            [_rec("b%d" % i, _sig(20 + i)) for i in range(2)]
        assert rho.rho_at(a, b, 1) == pytest.approx(rho.rho(a, b))

    def test_partition_artifact_r1_zero_but_r2_positive(self):
        """THE amendment's case: same mechanism, different params -- rung 1
        partitions them apart (rho 0), rung 2 sees the shared redescription."""
        a = [_rec("a0", _sig(0), ttype="TRANSLATE", params={"dx": 1, "dy": 0})]
        b = [_rec("b0", _sig(0), ttype="TRANSLATE", params={"dx": 2, "dy": 0})]
        r1 = rho.rho_at(a, b, 1)
        r2 = rho.rho_at(a, b, 2)
        assert r1 == pytest.approx(0.0), "params split rung 1 classes"
        assert r2 > 0.0, "rung 2 drops params: the correlation becomes visible"

    def test_mag_is_dropped_at_rung2(self):
        """mag is a frame-local descriptor, not a sigma invariant: rung 2
        coarsens it away."""
        a = [_rec("a0", _sig(0, mag="small"))]
        b = [_rec("b0", _sig(0, mag="large"))]
        assert rho.rho_at(a, b, 1) == pytest.approx(0.0)
        assert rho.rho_at(a, b, 2) == pytest.approx(1.0)

    def test_rungs_are_ordered_r2_never_below_r1(self):
        a = [_rec("a%d" % i, _sig(i % 3), ttype="TRANSLATE",
                  params={"dx": i}) for i in range(6)]
        b = [_rec("b%d" % i, _sig(i % 4), ttype="TRANSLATE",
                  params={"dx": i + 1}) for i in range(6)]
        assert rho.rho_at(a, b, 2) >= rho.rho_at(a, b, 1), (
            "rung 2 is a coarsening of rung 1: Jaccard can only rise")

    def test_sigma_less_atoms_degrade_never_raise(self):
        bare = [{"id": "x", "game": "gB", "atom": {"kind": "EFFECT", "key": "x"}}]
        signed = [_rec("x", _sig(0))]
        assert rho.rho_at(signed, bare, 1) == pytest.approx(0.0)
        assert rho.rho_at(signed, bare, 2) == pytest.approx(0.0)
        assert rho.rho_at(signed, bare, 0) == pytest.approx(1.0), (
            "an unsigma'd atom still HAS a key -- rung 0 keeps measuring")
        assert rho.rho_at([], [], 0) == pytest.approx(0.0)

    def test_unknown_rung_is_a_loud_error(self):
        with pytest.raises(ValueError):
            rho.rho_at([], [], 3)


# ── the rederivation-traffic channel ─────────────────────────────────────────

class TestRederivationTraffic:

    def test_traffic_catches_a_synthetic_cross_recognition(self):
        atoms_b = [_rec("kb", _sig(0)), _rec("kb2", _sig(1))]
        verdicts_a = [
            _reder("kb"), _reder("kb"),            # 2 recognitions of B's atom
            _reder("elsewhere"),                   # not B's key
            {"verdict": "reject", "game": "gX", "level": 1, "key": "kb"},
            {"verdict": "mint", "game": "gX", "level": 1, "key": "kb2"},
        ]
        assert rho.rederivation_traffic(verdicts_a, atoms_b) == 2, (
            "rederivation verdicts naming B's atom keys, nothing else")

    def test_old_shape_and_malformed_verdicts_never_raise(self):
        atoms_b = [_rec("kb", _sig(0))]
        verdicts = [_reder("kb"),                       # counts
                    {"verdict": "rederivation"},        # keyless: skipped
                    {"verdict": "quarantine"},
                    "not-a-dict", None]                 # garbage: skipped
        assert rho.rederivation_traffic(verdicts, atoms_b) == 1
        assert rho.rederivation_traffic(None, atoms_b) == 0
        assert rho.rederivation_traffic([_reder("kb")], None) == 0


# ── rho_report: the per-pair distribution ────────────────────────────────────

class TestRhoReport:

    def _fabrics(self):
        """A/B replicate a key + share coarse structure; C is disjoint.
        A's verdict stream re-recognizes B's atom key: nonzero traffic."""
        shared = _rec("shared-key", _sig(0), ttype="TRANSLATE", params={"dx": 1})
        return {
            "A": {"atoms": [shared,
                            _rec("a1", _sig(1), ttype="TRANSLATE",
                                 params={"dx": 3})],
                  "verdicts": [_reder("b-only")]},
            "B": {"atoms": [dict(shared),
                            _rec("b-only", _sig(1), ttype="TRANSLATE",
                                 params={"dx": 4})],
                  "verdicts": []},
            "C": {"atoms": [_rec("c1", _sig(30), ttype="ROTATE",
                                 params={"k": 1})],
                  "verdicts": []},
        }

    def test_report_covers_every_pair_with_all_four_channels(self):
        rep = rho.rho_report(self._fabrics())
        assert set(rep) == {("A", "B"), ("A", "C"), ("B", "C")}
        for stats in rep.values():
            assert set(stats) == {"r0", "r1", "r2", "traffic"}

    def test_the_distribution_is_capable_of_nonzero(self):
        """The amendment's whole point: a measurement of independence must be
        able to read nonzero -- on every channel at once for a correlated pair."""
        rep = rho.rho_report(self._fabrics())
        ab = rep[("A", "B")]
        assert ab["r0"] > 0.0, "rung 0 must catch the shared canonical key"
        assert ab["r1"] > 0.0
        assert ab["r2"] >= ab["r1"]
        assert ab["traffic"] == 1, "A re-recognized B's atom: traffic channel fires"
        ac = rep[("A", "C")]
        assert ac["r0"] == ac["r1"] == pytest.approx(0.0)
        assert ac["traffic"] == 0

    def test_traffic_is_counted_in_both_directions(self):
        fabs = self._fabrics()
        fabs["B"]["verdicts"] = [_reder("a1"), _reder("a1")]
        rep = rho.rho_report(fabs)
        assert rep[("A", "B")]["traffic"] == 3, "A->B (1) plus B->A (2)"

    def test_missing_verdict_streams_degrade_to_zero_traffic(self):
        fabs = {"A": {"atoms": [_rec("a0", _sig(0))]},
                "B": {"atoms": [_rec("a0", _sig(0))]}}
        rep = rho.rho_report(fabs)
        assert rep[("A", "B")]["traffic"] == 0
        assert rep[("A", "B")]["r0"] == pytest.approx(1.0)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
