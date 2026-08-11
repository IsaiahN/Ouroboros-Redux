"""3d-ii GATE: the frontier exploration harvest — bank the experience, not the death spot.

⭐ WHY (Isaiah's correction). A frontier episode produces ~150 actions of experience: which
cells do nothing, which cells cause effects, which action moves the body where. All of it
evaporated at episode end (unrewarded => unminted). The harvest banks it as OBSERVATIONS —
never signal, nothing opens the wheel — and later agents explore the frontier as one
cumulative population-wide sweep instead of independent blind draws.

THE CONTRACT (PREREG_FRONTIER_HARVEST.md):
  * FrontierBook gains: record_harvest(game, level, dead=[cells], effects=[cells],
    fatal=cell|None, deltas={action: (dr, dc)}) — one collective "frontier_harvest" record;
  * load_harvest(game, level) -> dict with:
      - "dead": cells reported dead in >=2 INDEPENDENT records and NEVER in any effects list
        (state-dependent one-offs stay explorable; an effect report always wins);
      - "effects": union of all effects cells;
      - "fatal": union of fatal cells (3d-i's veto data rides along);
      - "tried": union of every dead+effects+fatal cell across records;
      - "deltas": first-seen delta per action (deterministic);
  * spine.remap_to_untried(cell, tried, avoid, shape) -> nearest cell NOT in tried|avoid
    (ring scan, (dy,dx) order); no such cell -> nearest not in avoid; none -> original;
  * loop wiring: harvest written on BOTH death and budget ends; consumers only in the
    pre-empt block; harvested deltas pre-establish the spine's move-map (means, not signal).

Run pre-build: these failed (methods absent).
"""
from __future__ import annotations
import os, sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric   # noqa: E402


def _book(tmp_path, name="f", agent="a"):
    from engines.egocentric.frontier import FrontierBook
    b = FrontierBook(KnowledgeFabric(str(tmp_path / name), agent_id=agent, kin_key="v4"))
    if not hasattr(b, "record_harvest"):
        pytest.fail("FrontierBook.record_harvest missing — 3d-ii has not landed")
    return b


class TestTheHarvest:

    def test_roundtrip_and_unions(self, tmp_path):
        b = _book(tmp_path)
        b.record_harvest("g1", 1, dead=[(1, 1)], effects=[(2, 2)], fatal=(9, 9),
                         deltas={"1": (0, 1)})
        b.record_harvest("g1", 1, dead=[(1, 1), (3, 3)], effects=[(4, 4)], fatal=None,
                         deltas={"2": (1, 0)})
        h = b.load_harvest("g1", 1)
        assert h["dead"] == {(1, 1)}, "dead needs >=2 independent reports"
        assert h["effects"] == {(2, 2), (4, 4)}
        assert h["fatal"] == {(9, 9)}
        assert (3, 3) in h["tried"] and (9, 9) in h["tried"]
        assert h["deltas"] == {"1": (0, 1), "2": (1, 0)}

    def test_an_effect_report_always_beats_dead_reports(self, tmp_path):
        """⭐ THE CONSERVATIVE RULE. A cell dead twice but effectful once stays EXPLORABLE —
        state-dependent effects exist and one positive observation outweighs silence."""
        b = _book(tmp_path)
        b.record_harvest("g1", 1, dead=[(5, 5)], effects=[], fatal=None, deltas={})
        b.record_harvest("g1", 1, dead=[(5, 5)], effects=[], fatal=None, deltas={})
        b.record_harvest("g1", 1, dead=[], effects=[(5, 5)], fatal=None, deltas={})
        h = b.load_harvest("g1", 1)
        assert (5, 5) not in h["dead"]
        assert (5, 5) in h["effects"]

    def test_level_scoping(self, tmp_path):
        b = _book(tmp_path)
        b.record_harvest("g1", 1, dead=[(1, 1)], effects=[], fatal=None, deltas={})
        b.record_harvest("g1", 2, dead=[(2, 2)], effects=[], fatal=None, deltas={})
        assert (2, 2) not in b.load_harvest("g1", 1)["tried"]

    def test_population_union_via_seeds(self, tmp_path):
        sb = _book(tmp_path, "seed", agent="origin")
        sb.record_harvest("g1", 1, dead=[], effects=[(6, 6)], fatal=None, deltas={})
        from engines.egocentric.frontier import FrontierBook
        live = FrontierBook(KnowledgeFabric(str(tmp_path / "live"),
                                            seeds=[str(tmp_path / "seed")],
                                            agent_id="b", kin_key="v4"))
        assert (6, 6) in live.load_harvest("g1", 1)["effects"]


class TestTheUntriedRemap:

    def _spine(self):
        from engines.egocentric.spine import GoalSpine
        s = GoalSpine()
        if not hasattr(s, "remap_to_untried"):
            pytest.fail("GoalSpine.remap_to_untried missing — 3d-ii has not landed")
        return s

    def test_prefers_untried_over_merely_non_avoided(self):
        s = self._spine()
        tried = {(2, 2), (1, 1), (3, 3)}
        out = s.remap_to_untried((2, 2), tried, set(), (8, 8))
        assert out not in tried and 0 <= out[0] < 8 and 0 <= out[1] < 8

    def test_all_tried_falls_back_to_non_avoided(self):
        s = self._spine()
        tried = {(x, y) for x in range(4) for y in range(4)}
        avoid = {(0, 0)}
        out = s.remap_to_untried((0, 0), tried, avoid, (4, 4))
        assert out != (0, 0), "fatal cells must still be escaped even on a fully-tried board"

    def test_determinism(self):
        s = self._spine()
        picks = {s.remap_to_untried((2, 2), {(2, 2)}, set(), (6, 6)) for _ in range(5)}
        assert len(picks) == 1


class TestTheWiring:

    def _src(self, f="cognitive_loop.py"):
        return open(os.path.join(REPO, f), encoding="utf-8", errors="replace").read()

    def test_harvest_written_on_both_end_kinds(self):
        src = self._src("cognitive_game_player.py")
        assert src.count("record_harvest") >= 1, "no harvest write — experience still evaporates"
        i = src.find("record_harvest")
        window = src[max(0, i - 3000):i + 3000]
        assert "GAME_OVER" in window or "budget" in window.lower() or "actions_taken" in window, (
            "the harvest must be written at episode end (death AND budget expiry)")

    def test_the_loop_accrues_the_harvest_material(self):
        src = self._src()
        assert "_ego_frontier_dead" in src or "_ego_harvest" in src, (
            "the loop tracks no per-episode frontier dead/effect cells — there is nothing to "
            "harvest (starvation)")

    def test_consumers_use_untried_remap(self):
        src = self._src()
        assert "remap_to_untried" in src, (
            "the pre-empt block never remaps toward untried cells — coverage stays "
            "non-cumulative and N episodes remain N independent blind draws")

    def test_harvested_deltas_pre_establish_the_move_map(self):
        src = self._src()
        assert "load_harvest" in src
        i = src.find("load_harvest")
        window = src[i:i + 2500]
        assert "note_move" in window or "deltas" in window, (
            "harvested deltas never reach the spine — every frontier visit re-pays the "
            "move-map learning tax")
