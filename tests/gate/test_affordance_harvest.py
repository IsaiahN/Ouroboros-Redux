"""CK-1b GATE: affordance harvest un-gating (record/prereg/PREREG_CK_WAVE1.md, section CK-1b).

WHY (measured). Frontier harvest banks only when an episode reached a frontier
(level >= 1): the accrual in cognitive_loop.record_result and the episode-end
write in cognitive_game_player are BOTH gated on level >= 1. Result: 18 of 25
games sit at level 0 with ZERO harvest records after 48-112 episodes each --
every episode's affordance experience (which cells do something, which do
nothing) evaporates and each new episode re-explores blind.

THE CONTRACT (CK-1b):
  * The episode's accumulated experience -- effect cells (click -> frame
    changed) and dead-cell reports -- is banked at EPISODE END even when the
    episode had ZERO level-ups and ZERO deaths (level 0 included).
  * Same record shape, same writer (FrontierBook.record_harvest), same
    conservative >=2-report dead rule, same consumers. ONLY the accrual gate
    changes.
  * No double-writing: the episode-end recorder stays the single
    record_harvest site, one write per episode.
  * A level-up step's click still belongs to the level below (skipped) --
    the credit convention is untouched.

Run pre-build: the un-gating tests FAILED (level-0 experience evaporated).
"""
from __future__ import annotations

import os
import sys
import textwrap

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.frontier import FrontierBook  # noqa: E402


def _src(f):
    return open(os.path.join(REPO, f), encoding="utf-8", errors="replace").read()


def _mk_loop(tmp_path, monkeypatch, game_id="gate_g0"):
    """A real CognitiveLoop, hermetic: its fabric roots in tmp cwd."""
    monkeypatch.chdir(tmp_path)
    from cognitive_loop import CognitiveLoop
    loop = CognitiveLoop()
    loop.start_game(game_id, [1, 2, 3, 4, 5, 6], max_actions=50)
    return loop


def _step(loop, x=None, y=None, action=6, changed=False, level_changed=False):
    """Drive one action result through the REAL record_result path."""
    from engines.cognition.cognitive_frame import CognitiveFrame
    loop._current_frame = CognitiveFrame()
    info = {'type': action}
    if x is not None:
        info['x'], info['y'] = x, y
    loop._last_action_info = info
    loop.record_result(
        post_frame=np.zeros((64, 64), dtype=int),
        frame_changed=changed,
        score_delta=0.0,
        level_changed=level_changed,
    )


def _run_episode_end(loop, game_id, current_levels=0):
    """Execute the ACTUAL episode-end harvest recorder block shipped in
    cognitive_game_player.py (extracted verbatim), for an episode that ends
    with no death (last_obs=None short-circuits the death check)."""
    src = _src("cognitive_game_player.py")
    start = src.index("3d-ii (EGO-FRONTIER): harvest the episode's exploration")
    start = src.rindex("\n", 0, start) + 1
    end = src.index("# End game and get replay", start)
    end = src.rindex("\n", 0, end)
    block = textwrap.dedent(src[start:end])

    class _GS:
        GAME_OVER = object()
        WIN = object()

    ns = {"loop": loop, "game_id": game_id, "current_levels": current_levels,
          "last_obs": None, "GameState": _GS}
    exec(compile(block, "<episode-end-recorder>", "exec"), ns)  # noqa: S102 -- deliberately executes the extracted loop block under test


class TestLevelZeroAccrual:
    """The loop must accrue affordance observations at level 0."""

    def test_level0_clicks_accrue_effect_and_dead_cells(self, tmp_path, monkeypatch):
        loop = _mk_loop(tmp_path, monkeypatch)
        _step(loop, x=10, y=12, changed=True)    # effect cell
        _step(loop, x=20, y=21, changed=False)   # dead report
        assert (10, 12) in list(getattr(loop, "_ego_frontier_effects", []) or []), (
            "a level-0 click that CHANGED the frame was not accrued as an effect "
            "cell -- the affordance harvest is still gated on level >= 1 and "
            "level-0 experience evaporates (CK-1b)")
        assert (20, 21) in list(getattr(loop, "_ego_frontier_dead", []) or []), (
            "a level-0 click with NO effect was not accrued as a dead report -- "
            "the affordance harvest is still gated on level >= 1 (CK-1b)")

    def test_levelup_step_click_is_still_skipped(self, tmp_path, monkeypatch):
        """The credit convention survives the un-gating: a level-up step's
        click belongs to the level below and is NOT accrued."""
        loop = _mk_loop(tmp_path, monkeypatch)
        _step(loop, x=30, y=31, changed=True, level_changed=True)
        assert (30, 31) not in list(getattr(loop, "_ego_frontier_effects", []) or [])
        assert (30, 31) not in list(getattr(loop, "_ego_frontier_dead", []) or [])

    def test_non_click_actions_accrue_nothing(self, tmp_path, monkeypatch):
        loop = _mk_loop(tmp_path, monkeypatch)
        _step(loop, action=1, changed=True)
        assert not list(getattr(loop, "_ego_frontier_effects", []) or [])
        assert not list(getattr(loop, "_ego_frontier_dead", []) or [])


class TestEpisodeEndBanking:
    """The prereg falsifier: an episode with ZERO level-ups and ZERO deaths
    still writes harvest records at episode end."""

    def test_no_levelup_no_death_episode_banks_its_experience(self, tmp_path, monkeypatch):
        loop = _mk_loop(tmp_path, monkeypatch, game_id="gate_g0")
        _step(loop, x=10, y=12, changed=True)
        _step(loop, x=20, y=21, changed=False)
        book = getattr(loop, "_ego_frontier_book", None)
        assert book is not None, "loop built no FrontierBook -- fabric init broke"
        _run_episode_end(loop, "gate_g0", current_levels=0)
        h = book.load_harvest("gate_g0", 0)
        assert (10, 12) in h["effects"], (
            "an episode with zero level-ups and zero deaths banked NOTHING -- "
            "the episode-end recorder is still gated on level/death and the 18 "
            "level-0 games keep re-exploring blind (CK-1b falsifier)")
        assert (10, 12) in h["tried"] and (20, 21) in h["tried"]

    def test_writer_gate_no_longer_requires_frontier_level(self):
        """The one-condition gate: the record_harvest write must not require
        _hlevel >= 1 (episode end banks regardless of level/death)."""
        src = _src("cognitive_game_player.py")
        i = src.index(".record_harvest(")
        window = src[max(0, i - 1500):i]
        assert "_hlevel >= 1" not in window, (
            "the episode-end harvest write is still gated on _hlevel >= 1 -- "
            "level-0 experience is never banked (CK-1b)")

    def test_single_write_site_no_double_banking(self):
        """Guard: exactly ONE record_harvest call site in the player -- the
        same episode's observations can never be banked twice."""
        src = _src("cognitive_game_player.py")
        assert src.count(".record_harvest(") == 1, (
            "more than one record_harvest site in cognitive_game_player.py -- "
            "an episode's observations risk being double-banked")

    def test_fatal_opening_recording_untouched(self):
        """The per-event (death) banking stays exactly as it was."""
        src = _src("cognitive_game_player.py")
        i = src.index("record_fatal_opening(")
        window = src[max(0, i - 800):i]
        assert "current_levels >= 1" in window, (
            "the fatal-opening death path changed -- CK-1b touches only the "
            "harvest accrual gate")


class TestConservativeDeadRuleAtLevelZero:
    """The >=2-report dead rule holds unchanged for level-0 records."""

    def _book(self, tmp_path):
        return FrontierBook(KnowledgeFabric(str(tmp_path / "f"),
                                            agent_id="a", kin_key="v4"))

    def test_one_report_does_not_mark_dead(self, tmp_path):
        b = self._book(tmp_path)
        b.record_harvest("g0", 0, dead=[(5, 5)], effects=[], fatal=None, deltas={})
        h = b.load_harvest("g0", 0)
        assert (5, 5) not in h["dead"], (
            "ONE dead report marked the cell dead -- the conservative >=2 rule "
            "broke in the un-gating")
        assert (5, 5) in h["tried"]

    def test_two_reports_mark_dead_and_an_effect_still_wins(self, tmp_path):
        b = self._book(tmp_path)
        b.record_harvest("g0", 0, dead=[(5, 5)], effects=[], fatal=None, deltas={})
        b.record_harvest("g0", 0, dead=[(5, 5)], effects=[], fatal=None, deltas={})
        assert (5, 5) in b.load_harvest("g0", 0)["dead"]
        b.record_harvest("g0", 0, dead=[], effects=[(5, 5)], fatal=None, deltas={})
        h = b.load_harvest("g0", 0)
        assert (5, 5) not in h["dead"] and (5, 5) in h["effects"]

    def test_level0_records_stay_scoped_to_level0(self, tmp_path):
        b = self._book(tmp_path)
        b.record_harvest("g0", 0, dead=[(1, 1)], effects=[(2, 2)], fatal=None, deltas={})
        assert (2, 2) not in b.load_harvest("g0", 1)["effects"]
        assert (2, 2) in b.load_harvest("g0", 0)["effects"]
