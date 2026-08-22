"""test_rho.py -- G-A THE RHO ESTIMATOR (record/prereg/PREREG_FINAL_GAPS.md §G-A).

⭐ WHY: the anchor figure's missing metric. Cross-mounted fabrics are NOT independent
witnesses -- the swarm replicates banks verbatim, so k agreeing sources can be one
source photocopied k times. rho(fabric_a_atoms, fabric_b_atoms) is a weighted Jaccard
over atom signature classes (sigma + ttype/params class); n_eff(k, rho_bar) =
k / (1 + (k-1)*rho_bar) is the effective independent-source count. One-currency
consumers, ranking only: (1) the triangulation consumer prefers the LOW-rho source
when several sources match (independence is the gate -- Fig 8's debit); (2) the
COLLAPSE-4 GUARD: two source fabrics with rho >= the collapse threshold have their
agreement counted ONCE (n_eff-weighted, never duplicated); one [RHO] line per pass.

FALSIFIER (prereg): identical fabrics -> rho ~ 1 and n_eff -> 1; disjoint synthetic
fabrics -> rho ~ 0 and n_eff ~ k; the consumer prefers the low-rho source when two
sources match; the guard collapses replicated agreement to a single count.

Run pre-build: these failed (engines.egocentric.rho absent; consume() emitted no
rho block and no [RHO] line).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer, rho
from engines.egocentric.fabric import KnowledgeFabric

# ── fixtures: synthetic sigma classes and fabric roots ────────────────────────

def _recolour(n=5, cells=((2, 2),), src=2, dst=3):
    b = np.full((n, n), src, dtype=int)
    a = b.copy()
    for r, c in cells:
        a[r, c] = dst
    return b, a


def _class_sig(i):
    """A distinct one-cell recolour signature class per integer i."""
    return {"arity": 2, "bbox": "cell", "changed": "1",
            "colour_delta": [[int(i), int(i) + 1]], "conserved": False, "mag": "small"}


def _rec(game, key, sigma, ttype=None, params=None):
    """One atom RECORD in the collective/atoms shape (see .runs/swarm/*/ego_fabric)."""
    atom = {"kind": "EFFECT", "arity": 2, "key": str(key), "sigma": dict(sigma)}
    if ttype is not None:
        atom["ttype"] = ttype
    if params is not None:
        atom["params"] = params
    return {"id": "%s:0" % key, "type": "structural", "game": str(game), "level": 1,
            "atom": atom}


def _fab(root, agent="agentX", kin="kinX", seeds=()):
    return KnowledgeFabric(str(root), seeds=[str(s) for s in seeds],
                           agent_id=agent, kin_key=kin)


def _put_atom(fabric, game, key, sigma):
    return fabric.append("collective", "atoms", _rec(game, key, sigma))


def _enqueue(fabric, before, after, slot="WORKSPACE", residual=1.0):
    return fabric.append("collective", "import_queue", {
        "slot": slot, "residual": float(residual),
        "before": [[int(v) for v in row] for row in np.asarray(before)],
        "after": [[int(v) for v in row] for row in np.asarray(after)],
    })


def _match_sigma():
    """The signature the enqueued residual will carry (1-cell 2->3 on 5x5)."""
    b, a = _recolour()
    return consumer.sigma_of(b, a)


# ── the prereg falsifier, pure half: rho / n_eff ─────────────────────────────

class TestRhoPure:

    def test_identical_fabrics_rho_is_one_n_eff_is_one(self):
        atoms = [_rec("gA", "k%d" % i, _class_sig(i)) for i in range(4)]
        clone = [_rec("gB", "c%d" % i, _class_sig(i)) for i in range(4)]
        r = rho.rho(atoms, clone)
        assert r == pytest.approx(1.0)
        assert rho.n_eff(2, r) == pytest.approx(1.0)
        assert rho.n_eff(8, 1.0) == pytest.approx(1.0), "x8 replicas are ONE witness"

    def test_disjoint_fabrics_rho_is_zero_n_eff_is_k(self):
        a = [_rec("gA", "a%d" % i, _class_sig(i)) for i in range(4)]
        b = [_rec("gB", "b%d" % i, _class_sig(10 + i)) for i in range(4)]
        r = rho.rho(a, b)
        assert r == pytest.approx(0.0)
        assert rho.n_eff(5, r) == pytest.approx(5.0)

    def test_partial_overlap_is_strictly_between_and_symmetric(self):
        a = [_rec("gA", "a%d" % i, _class_sig(i)) for i in range(4)]
        b = [_rec("gB", "b%d" % i, _class_sig(i)) for i in range(2)] + \
            [_rec("gB", "b%d" % i, _class_sig(20 + i)) for i in range(2)]
        r = rho.rho(a, b)
        assert 0.0 < r < 1.0
        assert r == pytest.approx(rho.rho(b, a)), "rho must be symmetric"
        # multiset weighting: 2 shared of 6 distinct-by-max -> 2/6
        assert r == pytest.approx(2.0 / 6.0)

    def test_ttype_params_split_signature_classes(self):
        sig = _class_sig(0)
        a = [_rec("gA", "a0", sig, ttype="COLOUR_PERM", params={"mapping": [[0, 15]]})]
        b = [_rec("gB", "b0", sig, ttype="TRANSLATE", params={"dx": 1})]
        assert rho.rho(a, b) == pytest.approx(0.0), "ttype/params class must separate"
        assert rho.rho(a, list(a)) == pytest.approx(1.0)

    def test_empty_or_unsigmad_fabrics_never_correlate(self):
        atoms = [_rec("gA", "a0", _class_sig(0))]
        bare = [{"id": "x", "game": "gB", "atom": {"kind": "EFFECT", "key": "x"}}]
        assert rho.rho([], []) == pytest.approx(0.0)
        assert rho.rho(atoms, []) == pytest.approx(0.0)
        assert rho.rho(atoms, bare) == pytest.approx(0.0)
        assert rho.sig_class(bare[0]) is None, "an unsigma'd atom has no signature class"

    def test_n_eff_formula_and_clamps(self):
        assert rho.n_eff(4, 0.5) == pytest.approx(4.0 / 2.5)
        assert rho.n_eff(1, 0.9) == pytest.approx(1.0)
        assert rho.n_eff(0, 0.5) == pytest.approx(0.0)
        assert rho.n_eff(3, -0.5) == pytest.approx(3.0), "rho_bar clamps into [0,1]"
        assert rho.n_eff(3, 7.0) == pytest.approx(1.0)

    def test_collapse_clusters_only_above_threshold(self):
        pair = {("A", "B"): 0.95, ("A", "C"): 0.1, ("B", "C"): 0.2}

        def pr(x, y):
            return pair.get((x, y), pair.get((y, x), 0.0))

        clusters = rho.collapse(["A", "B", "C"], pr)
        assert sorted(sorted(c) for c in clusters) == [["A", "B"], ["C"]]
        assert rho.collapse(["A", "B", "C"], pr, threshold=0.05) == [["A", "B", "C"]]


# ── the consumer ranking hook: LOW rho preferred ─────────────────────────────

class TestLowRhoPreferred:

    def test_consumer_prefers_the_low_rho_source(self, tmp_path):
        """Two sources match. gA replicates the home fabric's own vocabulary (high
        rho -- a photocopy adds nothing); gB is disjoint from home (independent).
        The OLD ranking (mint seq) would pick gA's earlier atom; the rho ranking
        must pick gB's."""
        msig = _match_sigma()
        A = _fab(tmp_path / "A", agent="agentB", kin="kinB")
        _put_atom(A, "gA", "eff-A", msig)                    # earliest seq of the two hits
        _put_atom(A, "gA", "padA1", _class_sig(4))
        _put_atom(A, "gA", "padA2", _class_sig(6))
        B = _fab(tmp_path / "B", agent="agentC", kin="kinC")
        _put_atom(B, "gB", "padB1", _class_sig(8))
        _put_atom(B, "gB", "padB2", _class_sig(11))
        _put_atom(B, "gB", "eff-B", msig)                    # latest seq -- seq must NOT win
        home = _fab(tmp_path / "home", agent="agentA", kin="kinA",
                    seeds=[tmp_path / "A", tmp_path / "B"])
        _put_atom(home, "g_hist", "padH1", _class_sig(4))    # home already holds gA's classes
        _put_atom(home, "g_hist", "padH2", _class_sig(6))
        b, a = _recolour()
        _enqueue(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["candidates"] == 1
        cand = consumer.candidates(home, "g_home", 1)[0]
        assert cand["source_game"] == "gB", "the low-rho (independent) source must win"
        assert cand["atom"]["key"] == "eff-B"
        blk = cand["rho"]
        assert blk["source_rho"] == pytest.approx(0.0)
        assert blk["k"] == 2 and blk["clusters"] == 2 and blk["collapsed"] is False

    def test_kin_echo_law_still_outranks_rho(self, tmp_path):
        """The rho preference is SECONDARY: a stranger's atom still outranks kin's
        even when kin is the lower-rho source (the CK_LEDGER ground criterion)."""
        msig = _match_sigma()
        home = _fab(tmp_path / "home", agent="agentA", kin="kinA")
        rec = _rec("g_kin", "eff-kin", msig)
        rec["agent"] = "agentA"
        home.append("collective", "atoms", rec)
        rec2 = _rec("g_oth", "eff-oth", msig)
        rec2["agent"] = "agentB"
        home.append("collective", "atoms", rec2)
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        cand = consumer.candidates(home, "g_home", 1)[0]
        assert cand["atom"]["key"] == "eff-oth" and cand["kin_echo"] is False


# ── the COLLAPSE-4 GUARD: replicated agreement counts once ───────────────────

class TestCollapseGuard:

    def test_replicated_sources_agreement_counts_once(self, tmp_path):
        """gA and gB are verbatim replicas (rho = 1 >= threshold): the candidate's
        support collapses to ONE independent witness -- the anchor figure's debit."""
        msig = _match_sigma()
        for name, game in (("A", "gA"), ("B", "gB")):
            f = _fab(tmp_path / name, agent="agent" + name, kin="kin" + name)
            _put_atom(f, game, "eff-" + name, msig)
            _put_atom(f, game, "pad1-" + name, _class_sig(4))
            _put_atom(f, game, "pad2-" + name, _class_sig(6))
        home = _fab(tmp_path / "home", agent="agentA", kin="kinA",
                    seeds=[tmp_path / "A", tmp_path / "B"])
        b, a = _recolour()
        _enqueue(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["candidates"] == 1
        blk = consumer.candidates(home, "g_home", 1)[0]["rho"]
        assert blk["k"] == 2
        assert blk["rho_bar"] == pytest.approx(1.0)
        assert blk["n_eff"] == pytest.approx(1.0)
        assert blk["clusters"] == 1, "the guard must merge rho~1 sources"
        assert blk["support"] == pytest.approx(1.0), "agreement counted ONCE"
        assert blk["collapsed"] is True

    def test_disjoint_sources_keep_near_full_support(self, tmp_path):
        msig = _match_sigma()
        for name, game, base in (("A", "gA", 4), ("B", "gB", 14)):
            f = _fab(tmp_path / name, agent="agent" + name, kin="kin" + name)
            _put_atom(f, game, "eff-" + name, msig)
            for j in range(4):
                _put_atom(f, game, "pad%d-%s" % (j, name), _class_sig(base + 2 * j))
        home = _fab(tmp_path / "home", agent="agentA", kin="kinA",
                    seeds=[tmp_path / "A", tmp_path / "B"])
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        blk = consumer.candidates(home, "g_home", 1)[0]["rho"]
        assert blk["k"] == 2 and blk["clusters"] == 2 and blk["collapsed"] is False
        assert blk["rho_bar"] < rho.RHO_COLLAPSE
        assert blk["support"] > 1.7, "independent agreement keeps ~k witnesses"


# ── the [RHO] narration: one line per consume pass ───────────────────────────

class TestRhoLine:

    def test_one_rho_line_per_pass(self, tmp_path, capsys):
        home = _fab(tmp_path / "home", agent="agentA", kin="kinA")
        _put_atom(home, "g_hist", "eff-h", _match_sigma())
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        lines = [ln for ln in capsys.readouterr().out.splitlines()
                 if ln.startswith("[RHO]")]
        assert len(lines) == 1, "exactly one [RHO] line per consume pass"
        consumer.consume(home, "g_home", 1, 8)          # an empty pass still narrates
        lines2 = [ln for ln in capsys.readouterr().out.splitlines()
                  if ln.startswith("[RHO]")]
        assert len(lines2) == 1
