"""3d-i GATE: frontier pariah paths — each frontier death permanently removes an opening.

⭐ WHY. Three sealed eras, zero L2 in 5400 episodes. Post-handoff explorers die on landmine
openings in 15-60 actions and the next attempt repeats them: nothing compounds. v3's own
frontier-checkpoint blueprint, adapted: bank the FATAL OPENING (the first post-frontier click
of an episode that died there) in the fabric; veto its repetition population-wide. Exploration
ordering, not goal-claiming — the wheel rule is untouched.

THE CONTRACT (PREREG_FRONTIER_PARIAH.md):
  * `FrontierBook(fabric)` in engines/egocentric/frontier.py:
      - record_fatal_opening(game, level, cell) -> appends to collective "frontier_paths";
      - avoid_set(game, level) -> set of cells from seeds+local; deterministic;
      - errors counter; no RNG, no wall-clock.
  * spine: `remap_avoided(cell, avoid, shape) -> cell` — identity when not avoided; else the
    nearest non-avoided cell by Chebyshev ring scan (ties: (dy,dx) order), in-bounds; if every
    cell in range is avoided, the original stands. Deterministic.
  * loop wiring: the cycle pre-empt block vetoes a chosen CLICK on an avoided cell (current
    game+level) via remap, printing `[EGO-FRONTIER] avoid`; the result path records the fatal
    opening on a frontier death; `[EGO-FRONTIER]` log lines exist.

Run pre-build: these failed (module absent).
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402


def _book(tmp_path, name="f"):
    try:
        from engines.egocentric.frontier import (
            FrontierBook,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.frontier missing (%s) — 3d-i has not landed" % e)
    from engines.egocentric.frontier import FrontierBook as FB
    return FB(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


class TestTheBook:

    def test_roundtrip_and_scoping(self, tmp_path):
        b = _book(tmp_path)
        b.record_fatal_opening("g1", 1, (5, 5))
        b.record_fatal_opening("g1", 2, (7, 7))
        b.record_fatal_opening("g2", 1, (9, 9))
        assert b.avoid_set("g1", 1) == {(5, 5)}
        assert b.avoid_set("g1", 2) == {(7, 7)}
        assert b.avoid_set("g2", 1) == {(9, 9)}
        assert b.avoid_set("g3", 1) == set()

    def test_population_union_via_seed_overlay(self, tmp_path):
        seed = tmp_path / "seed"
        sb = _book(tmp_path, "seed")
        sb.record_fatal_opening("g1", 1, (3, 3))
        from engines.egocentric.frontier import FrontierBook
        live = FrontierBook(KnowledgeFabric(str(tmp_path / "live"), seeds=[str(seed)],
                                            agent_id="b", kin_key="v4"))
        live.record_fatal_opening("g1", 1, (4, 4))
        assert live.avoid_set("g1", 1) == {(3, 3), (4, 4)}, (
            "the avoid-set must union seeds+local — compounding is population-wide or it "
            "is not compounding")


class TestTheRemap:

    def _spine(self):
        from engines.egocentric.spine import GoalSpine
        s = GoalSpine()
        if not hasattr(s, "remap_avoided"):
            pytest.fail("GoalSpine.remap_avoided missing — 3d-i has not landed")
        return s

    def test_identity_when_not_avoided(self):
        assert self._spine().remap_avoided((3, 3), {(5, 5)}, (8, 8)) == (3, 3)

    def test_nearest_non_avoided_when_on_list(self):
        out = self._spine().remap_avoided((3, 3), {(3, 3)}, (8, 8))
        assert out != (3, 3) and 0 <= out[0] < 8 and 0 <= out[1] < 8

    def test_everything_avoided_keeps_original(self):
        avoid = {(x, y) for x in range(4) for y in range(4)}
        assert self._spine().remap_avoided((1, 1), avoid, (4, 4)) == (1, 1)

    def test_determinism(self):
        s = self._spine()
        picks = {s.remap_avoided((2, 2), {(2, 2), (1, 1)}, (6, 6)) for _ in range(5)}
        assert len(picks) == 1


class TestTheWiring:

    def _src(self, f="cognitive_loop.py"):
        return open(os.path.join(REPO, f), encoding="utf-8", errors="replace").read()

    def test_the_preempt_block_vetoes_avoided_clicks(self):
        src = self._src()
        assert "remap_avoided" in src, "no veto in the loop — fatal openings repeat (starvation)"
        assert "[EGO-FRONTIER]" in src

    def test_the_fatal_opening_is_recorded_on_frontier_death(self):
        src = self._src("cognitive_game_player.py") + self._src()
        assert "record_fatal_opening" in src, (
            "nothing records fatal openings — the book exists and every death still teaches "
            "nothing (the compounding this build exists for)")

    def test_the_level_convention_is_unified(self):
        """_ego_level must NEVER be derived from record_result's new_level param — new_level
        is levels_completed+1 while cycle()'s obs-based max uses levels_completed, so mixing
        them splits the avoid-set key across pathways (partial compounding). Bare increment
        only: one convention, one key."""
        src = self._src()
        i = src.find("def record_result")
        assert i != -1
        j = src.find("\n    def ", i + 1)
        body = src[i:j if j != -1 else len(src)]
        offenders = [ln.strip() for ln in body.splitlines()
                     if "_ego_level" in ln and "new_level" in ln]
        assert not offenders, (
            "record_result derives _ego_level from new_level (%r) — the frontier level must "
            "use the levels_completed convention (bare increment) so live and handoff "
            "pathways share one avoid-set key" % offenders)
