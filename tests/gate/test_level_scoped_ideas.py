"""Level-scoped ideas: a level-1 goal has no business at level 3.

Seeds loaded once at episode start are level-1 ideas; after a handoff the agent pursues them at
the frontier, fails, and burns budget falsifying them. Ideas now carry the level their reward
produced; seeding re-scopes on every level change.
"""
from __future__ import annotations
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import json
import pytest
from engines.egocentric.fabric import KnowledgeFabric


def _f(tmp_path, name="f", agent="a"):
    return KnowledgeFabric(str(tmp_path / name), agent_id=agent, kin_key="v4")


class TestLevelOnIdeas:

    def test_mint_stores_level(self, tmp_path):
        f = _f(tmp_path)
        i = f.mint({"kind": "CLICK_AT", "cell": [1, 1]}, game="g1",
                   signal={"type": "level_up"}, level=2)
        recs = f.query("personal", "ideas")
        assert recs and recs[-1].get("level") == 2

    def test_priors_filter_by_level(self, tmp_path):
        f = _f(tmp_path)
        i1 = f.mint({"kind": "CLICK_AT", "cell": [1, 1]}, game="g1",
                    signal={"type": "level_up"}, level=1)
        i2 = f.mint({"kind": "CLICK_AT", "cell": [2, 2]}, game="g1",
                    signal={"type": "level_up"}, level=2)
        ids_l2 = [p["id"] for p in f.priors("g1", level=2)]
        assert i2 in ids_l2 and i1 not in ids_l2

    def test_missing_level_defaults_to_one(self, tmp_path):
        """Historical records lack the field; every historical mint was a level-1 win."""
        f = _f(tmp_path)
        i = f.mint({"kind": "BE_AT", "cell": [3, 3]}, game="g1",
                   signal={"type": "level_up"})
        assert i in [p["id"] for p in f.priors("g1", level=1)]
        assert i not in [p["id"] for p in f.priors("g1", level=2)]

    def test_unfiltered_priors_unchanged(self, tmp_path):
        f = _f(tmp_path)
        a = f.mint({"kind": "BE_AT", "cell": [1, 1]}, game="g1",
                   signal={"type": "level_up"}, level=1)
        b = f.mint({"kind": "BE_AT", "cell": [2, 2]}, game="g1",
                   signal={"type": "level_up"}, level=3)
        ids = [p["id"] for p in f.priors("g1")]
        assert a in ids and b in ids


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_seeding_passes_the_level(self):
        src = self._src()
        assert "priors(" in src
        i = src.find(".priors(")
        window = src[i:i + 200]
        assert "level" in window, (
            "seeding still loads ALL levels' ideas — the frontier pollution stands")

    def test_reseed_on_level_change(self):
        src = self._src()
        assert "_ego_seed_level" in src or "reseed" in src.lower(), (
            "no re-seed on level change — the agent carries level-1 goals to the frontier")

    def test_mint_calls_pass_level(self):
        src = self._src()
        i = src.find(".mint(")
        assert i != -1
        window = src[i:i + 400]
        assert "level" in window, "mints are unscoped — new ideas pollute other levels forever"
