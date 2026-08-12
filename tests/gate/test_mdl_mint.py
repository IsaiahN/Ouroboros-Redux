"""W3a: the MDL mint — one operator, guards as a product, accept iff the compression pays.

SUPPORT (evidence exists, before search) x REACHABILITY (constructible from Gamma/event,
during) x NOVELTY (not already an atom, after). Accept iff |phi| + |R given phi| < |R|.
Any factor at zero -> re-derivation or quarantine, never a mint. The mint compounds nothing
on silence -- the wheel rule extended to memory, now with the compression test attached.
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


def _M():
    try:
        from engines.egocentric.mint import MDLMint
    except Exception as e:
        pytest.fail("engines.egocentric.mint missing (%s) -- W3a has not landed" % e)
    from engines.egocentric.mint import MDLMint as M
    return M


def _g(tmp_path):
    return E.Gamma(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))


def _event():
    before = np.zeros((5, 5), dtype=int); before[2, 2] = 3
    after = before.copy(); after[2, 2] = 4
    return before, after


class TestTheGuards:

    def test_support_zero_is_quarantine_or_rejection(self, tmp_path):
        m = _M()(self._gamma(tmp_path) if hasattr(self, "_gamma") else _g(tmp_path))
        before, _ = _event()
        out = m.consider(before=before, action=6, after=before.copy(), game="g1", level=1)
        assert out["verdict"] in ("quarantine", "reject"), (
            "no residual, no mint -- SUPPORT is the before-search guard")

    def test_a_supported_novel_compressible_event_mints(self, tmp_path):
        m = _M()(_g(tmp_path))
        before, after = _event()
        out = m.consider(before=before, action=6, after=after, game="g1", level=1)
        assert out["verdict"] == "mint" and out.get("id"), "the pocket is compressible -- cash it"

    def test_novelty_zero_is_rederivation_not_a_second_atom(self, tmp_path):
        g = _g(tmp_path)
        m = _M()(g)
        before, after = _event()
        first = m.consider(before=before, action=6, after=after, game="g1", level=1)
        again = m.consider(before=before, action=6, after=after, game="g1", level=1)
        assert again["verdict"] == "rederivation"
        atoms = [r for r in g.fabric.query("collective", "atoms")
                 if r.get("atom", {}).get("kind") == "EFFECT"]
        assert len(atoms) == 1, "re-deriving a known atom must not add a duplicate"

    def test_the_compression_test_can_refuse(self, tmp_path):
        """An 'atom' that explains less than it costs is refused even when novel: a full-board
        scramble has no compressible pocket at n=1."""
        m = _M()(_g(tmp_path))
        rng_free = np.arange(36, dtype=int).reshape(6, 6) % 7
        scramble = (rng_free + np.arange(36).reshape(6, 6) * 3) % 9
        out = m.consider(before=rng_free, action=6, after=scramble, game="g1", level=1)
        assert out["verdict"] in ("reject", "quarantine"), (
            "a transform as big as the change it explains compresses nothing")


class TestTheLedger:

    def test_every_verdict_is_recorded(self, tmp_path):
        g = _g(tmp_path)
        m = _M()(g)
        before, after = _event()
        m.consider(before=before, action=6, after=after, game="g1", level=1)
        recs = g.fabric.query("collective", "mint_verdicts")
        assert recs and recs[-1]["verdict"] == "mint", "nothing silent -- verdicts are book entries"

    def test_the_mint_split_is_reported(self, tmp_path):
        """The letters-wall watchdog: accepted mints report lexical vs structural."""
        g = _g(tmp_path)
        m = _M()(g)
        before, after = _event()
        m.consider(before=before, action=6, after=after, game="g1", level=1)
        split = m.split()
        assert split.get("structural", 0) >= 1
        assert "lexical" in split
