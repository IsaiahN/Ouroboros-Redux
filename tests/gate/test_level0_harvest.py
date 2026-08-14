"""B1 GATE (BUILD_PROGRAM_2 W1): level-0 harvest CONSUMPTION.

⭐ WHY. CK-1b un-gated the harvest WRITE from the frontier (level-0 episodes bank
their dead/effect cells), but the READ side stayed gated `level >= 1`: eighteen
level-0 games bank experience nobody ever loads. B1 admits level 0 at BOTH read
sites — the once-per-level `load_harvest` consumption and the pre-empt remap
veto — under the SAME conservative rules (dead needs >=2 independent reports and
never an effects report; an effect report always wins).

Run pre-build: the wiring tests failed (both sites gated `_ego_level >= 1`).
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


def _book(tmp_path, name="f", agent="a"):
    from engines.egocentric.frontier import FrontierBook
    return FrontierBook(KnowledgeFabric(str(tmp_path / name), agent_id=agent,
                                        kin_key="v4"))


def _src():
    return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                errors="replace").read()


class TestLevelZeroRecordsLoad:

    def test_level0_roundtrip_with_the_conservative_dead_rule(self, tmp_path):
        """Level-0 records load under the SAME rules as any frontier level."""
        b = _book(tmp_path)
        b.record_harvest("g1", 0, dead=[(1, 1)], effects=[(2, 2)], fatal=None,
                         deltas={"1": (0, 1)})
        b.record_harvest("g1", 0, dead=[(1, 1), (3, 3)], effects=[], fatal=None,
                         deltas={})
        h = b.load_harvest("g1", 0)
        assert h["dead"] == {(1, 1)}, "dead still needs >=2 independent reports"
        assert (2, 2) in h["effects"] and (3, 3) in h["tried"]
        assert h["deltas"] == {"1": (0, 1)}

    def test_level0_harvest_influences_the_remap_path(self, tmp_path):
        """A merged level-0 dead cell remaps to an untried cell — the exact
        consumption the loop's pre-empt veto performs."""
        from engines.egocentric.spine import GoalSpine
        b = _book(tmp_path)
        b.record_harvest("g1", 0, dead=[(4, 4)], effects=[], fatal=None, deltas={})
        b.record_harvest("g1", 0, dead=[(4, 4)], effects=[], fatal=None, deltas={})
        h = b.load_harvest("g1", 0)
        assert (4, 4) in h["dead"]
        out = GoalSpine().remap_to_untried((4, 4), h["tried"], h["fatal"], (8, 8))
        assert out != (4, 4) and out not in h["tried"]


class TestTheWiring:
    """The loop's TWO read sites must admit level 0 (the write already does)."""

    def test_the_load_site_admits_level_zero(self):
        src = _src()
        i = src.find("load_harvest")
        assert i != -1, "the harvest load site vanished"
        window = src[max(0, i - 700):i]
        assert "_ego_level >= 0" in window, (
            "the harvest LOAD is still gated level >= 1 — level-0 records are "
            "written but never consumed (B1 unlanded)")
        assert "_ego_level >= 1" not in window

    def test_the_remap_veto_site_admits_level_zero(self):
        src = _src()
        i = src.find(".remap_to_untried(")
        assert i != -1, "the harvest remap veto site vanished"
        window = src[max(0, i - 2500):i]
        assert "self._ego_level >= 0" in window, (
            "the pre-empt harvest veto is still gated level >= 1 — a level-0 "
            "click can never be remapped off banked dead cells (B1 unlanded)")
        assert "self._ego_level >= 1" not in window
