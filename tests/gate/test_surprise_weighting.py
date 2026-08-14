"""CK-2c: PREDICTION-ERROR (SURPRISE) WEIGHTING in the mint (Rescorla-Wagner shape).

Mint evidence currently counts; it should SURPRISE. Per (game, level, action,
transition-signature) -- the signature a cheap stable hash of the changed-cell pattern
(bbox delta bytes) -- repetition decays the effective support a piece of evidence
contributes: weight = 1/(1+seen). N identical repetitions asymptote (harmonic) below the
support that N distinct transitions clear. A single novel surprising transition is
UNCHANGED versus baseline; a transition already reproduced by an atom in Gamma is still a
rederivation. The seen-map is memory-bounded (LRU) so long grinds cannot grow it forever.

Measured motivation: lp85 grinds 270-action episodes of near-identical evidence (5,580
settlements, 0% nontrivial) -- repetition accumulates support linearly, debasing the mint.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric import effects as E
from engines.egocentric.mint import MDLMint


def _g(tmp_path, name="f"):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


def _repeat_item(i):
    """The SAME transition (same changed cells, same before/after values at them), with
    varying unchanged debris inside the bbox -- so the canonical atom KEY differs each
    time (NOVELTY passes; baseline mints every one) but the transition-signature is
    identical. This is the lp85 grind in miniature."""
    before = np.zeros((6, 6), dtype=int)
    before[1, 1] = 3
    before[2, 2] = 5
    before[1, 2] = 20 + i          # debris inside the bbox: unchanged, but varies per item
    after = before.copy()
    after[1, 1] = 4
    after[2, 2] = 6
    return before, after


def _distinct_item(i):
    """A genuinely distinct transition each time (different values at the changed cell)."""
    before = np.zeros((6, 6), dtype=int)
    before[2, 2] = 100 + i
    after = before.copy()
    after[2, 2] = 1000 + i
    return before, after


class TestTheFalsifier:

    def test_n_identical_repetitions_fall_below_n_distinct(self, tmp_path):
        """(a) N repeats of one transition must NOT reach the support N distinct ones
        reach: the distinct stream mints N atoms; the identical stream asymptotes at 1."""
        N = 6
        g_rep = _g(tmp_path, "rep")
        m_rep = MDLMint(g_rep)
        rep_verdicts = []
        for i in range(N):
            b, a = _repeat_item(i)
            rep_verdicts.append(
                m_rep.consider(before=b, action=6, after=a, game="lp85", level=1)["verdict"])

        g_dis = _g(tmp_path, "dis")
        m_dis = MDLMint(g_dis)
        dis_verdicts = []
        for i in range(N):
            b, a = _distinct_item(i)
            dis_verdicts.append(
                m_dis.consider(before=b, action=6, after=a, game="lp85", level=1)["verdict"])

        assert dis_verdicts.count("mint") == N, (
            "N distinct transitions must each contribute full support and mint")
        assert rep_verdicts.count("mint") < dis_verdicts.count("mint"), (
            "repetition still counts linearly -- the mint is not weighting by surprise")
        assert rep_verdicts[0] == "mint", "the FIRST occurrence is fully surprising"
        assert all(v == "reject" for v in rep_verdicts[1:]), (
            "repeats of a known transition-signature must contribute diminishing support "
            "(below the full-support bar), not mint near-duplicate atoms")

    def test_repetition_weight_decays_and_is_ledgered(self, tmp_path):
        """The Rescorla-Wagner shape: w = 1/(1+seen), recorded on the verdict ledger.
        Cumulative effective support over N repeats is the harmonic sum -- asymptotically
        below the N that N distinct transitions accumulate."""
        N = 5
        g = _g(tmp_path)
        m = MDLMint(g)
        for i in range(N):
            b, a = _repeat_item(i)
            m.consider(before=b, action=6, after=a, game="lp85", level=1)
        recs = g.fabric.query("collective", "mint_verdicts")
        ws = [r["w"] for r in recs if "w" in r]
        assert len(ws) == N, "every weighted consideration ledgers its weight"
        assert ws[0] == pytest.approx(1.0), "first occurrence: full support"
        for k in range(1, N):
            assert ws[k] == pytest.approx(1.0 / (1.0 + k)), "weight must decay 1/(1+seen)"
        assert sum(ws) < N - 1, "N identical repetitions must asymptote well below N"

    def test_single_novel_transition_unchanged_versus_baseline(self, tmp_path):
        """(b) A single surprising transition's treatment is EXACTLY the baseline's:
        mint with an id, key on the record; an identical re-offer is a rederivation
        (already reproduced by an atom in Gamma), never a reject; silence still rejects."""
        g = _g(tmp_path)
        m = MDLMint(g)
        before = np.zeros((5, 5), dtype=int)
        before[2, 2] = 3
        after = before.copy()
        after[2, 2] = 4
        out = m.consider(before=before, action=6, after=after, game="g1", level=1)
        assert out["verdict"] == "mint" and out.get("id"), "novel evidence: unchanged"
        rec = g.fabric.query("collective", "mint_verdicts")[-1]
        assert rec["verdict"] == "mint" and rec.get("key"), "record shape unchanged"
        again = m.consider(before=before, action=6, after=after, game="g1", level=1)
        assert again["verdict"] == "rederivation", (
            "a transition already reproduced by an existing atom stays a rederivation")
        silent = m.consider(before=before, action=6, after=before.copy(),
                            game="g1", level=1)
        assert silent["verdict"] in ("reject", "quarantine"), "SUPPORT guard unchanged"

    def test_the_seen_map_stays_bounded(self, tmp_path):
        """(c) Long runs cannot grow the seen-count map without bound (LRU cap)."""
        cap = 8
        g = _g(tmp_path)
        m = MDLMint(g, seen_cap=cap)
        for i in range(5 * cap):
            b, a = _distinct_item(i)
            m.consider(before=b, action=6, after=a, game="lp85", level=1)
        assert len(m._seen) <= cap, "the seen-count map must be memory-bounded"
