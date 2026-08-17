"""RESET-DISCIPLINE + A3-4 bump_episode GATE (maintainer's order).

THE WORRY (verbatim): an agent spamming RESET undoes progress -- moves 1-59
solid, 60 reset, ad infinitum. THE CONTRACT:

  * bump_episode PURPOSEFULLY: MDLMint.bump_episode() is called EXACTLY ONCE
    per episode boundary (the end_game settle site) so ep stamps are
    retry-precise -- monotonic across same-level retries the (game, level)
    context cannot see; a second end_game never double-bumps;
  * a bounded per-episode RESET counter rides the testimony
    (INSTRUMENTATION PAIR -- scope amendment: the counter REPORTS; no
    selection guard ships until it has, so a guard can enter singly later):
    a detected reset (the board reverting to the episode/level anchor frame
    after a solid run of >= RESET_MIN_RUN frame-changing steps) increments
    it, attributes the executed action, and narrates [RESET]; the episode
    settle line carries the count;
  * the reset-loop pattern (solid-run-then-reset repeated, the maintainer's
    moves-1-59-solid-60-reset worry) is RECORDED in full by the counter --
    every occurrence, with per-action attribution.

Run pre-build: failed (no bump site, no counter).
"""
from __future__ import annotations

import io
import os
import random
import sys
from contextlib import redirect_stdout

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

GAME_ID = "resetdisc_g1"


# ── frames: an anchor board and a progressive run away from it ──────────────

def _board(k):
    """k=0 is the anchor; k>0 are distinct 'solid progress' frames."""
    f = np.zeros((64, 64), dtype=int)
    f[10:13, 10:13] = 2
    if k > 0:
        f[40, 5 + k] = 7
    return f


def _drive(loop, before, act, after, level_changed=False):
    from engines.cognition.cognitive_frame import CognitiveFrame
    loop._current_frame = CognitiveFrame()
    loop._prev_frame = np.asarray(before)
    loop._last_action_info = {
        "type": int(act), "x": None, "y": None,
        "frame_changed": False, "score_delta": 0.0,
        "level_changed": False,
        "consecutive_no_change": 0, "consecutive_same_action": 0,
    }
    loop.record_result(
        post_frame=after,
        frame_changed=not np.array_equal(np.asarray(before), np.asarray(after)),
        score_delta=0.0, level_changed=level_changed)


def _reset_pattern(loop, rounds, reset_act=4):
    """The maintainer's pattern: a solid run (moves 1..3 change the frame),
    then `reset_act` reverts the board to the anchor. Repeated."""
    out = io.StringIO()
    with redirect_stdout(out):
        for _ in range(rounds):
            _drive(loop, _board(0), 1, _board(1))
            _drive(loop, _board(1), 2, _board(2))
            _drive(loop, _board(2), 3, _board(3))
            _drive(loop, _board(3), reset_act, _board(0))   # the reset
    return out.getvalue()


def _loop(game=GAME_ID, actions=(1, 2, 3, 4)):
    from cognitive_loop import CognitiveLoop
    loop = CognitiveLoop(verbose=False)
    loop.start_game(game, list(actions), max_actions=500)
    return loop


@pytest.fixture()
def run_dir(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(cwd)


# ── bump_episode: exactly once per boundary, retry-precise stamps ───────────

class TestBumpEpisodeOncePerBoundary:

    def test_ep_monotonic_across_same_level_retries(self, run_dir):
        loop = _loop()
        with redirect_stdout(io.StringIO()):
            _drive(loop, _board(0), 1, _board(1))    # lazy-inits fabric + mint
        mint = getattr(loop, "_mdl_mint", None)
        assert mint is not None
        fab = loop._ego_fabric
        with redirect_stdout(io.StringIO()):
            mint.consider(_board(0), 1, _board(1), "retry_game", 1)
        ep_before = fab.query("collective", "mint_verdicts")[-1]["ep"]
        with redirect_stdout(io.StringIO()):
            loop.end_game()                          # the episode boundary
            mint.consider(_board(0), 1, _board(1), "retry_game", 1)
        ep_after = fab.query("collective", "mint_verdicts")[-1]["ep"]
        assert ep_after == ep_before + 1, (
            "a same-level retry after the episode boundary must stamp a NEW "
            "ep ordinal (bump_episode not called at the end_game settle site)")

    def test_a_second_end_game_never_double_bumps(self, run_dir):
        loop = _loop()
        with redirect_stdout(io.StringIO()):
            _drive(loop, _board(0), 1, _board(1))
        mint = loop._mdl_mint
        with redirect_stdout(io.StringIO()):
            loop.end_game()
        ep1 = mint._ep
        with redirect_stdout(io.StringIO()):
            loop.end_game()
        assert mint._ep == ep1, (
            "bump_episode must fire EXACTLY once per episode boundary")


# ── (a) the counter + narration ─────────────────────────────────────────────

class TestTheResetCounter:

    def test_the_pattern_is_counted_and_narrated(self, run_dir):
        loop = _loop()
        out = _reset_pattern(loop, rounds=1)
        assert getattr(loop, "_reset_ep_count", 0) == 1, (
            "a solid-run-then-revert-to-anchor was not counted as a RESET")
        assert "[RESET]" in out, "a detected reset must narrate [RESET]"

    def test_every_occurrence_is_recorded(self, run_dir):
        loop = _loop()
        _reset_pattern(loop, rounds=4)
        assert loop._reset_ep_count == 4

    def test_the_episode_settle_line_carries_the_count(self, run_dir):
        loop = _loop()
        _reset_pattern(loop, rounds=2)
        buf = io.StringIO()
        with redirect_stdout(buf):
            loop.end_game()
        assert "[RESET] episode resets=2" in buf.getvalue(), (
            "the end_game settle line must testify the episode's reset count")

    def test_an_oscillating_world_is_not_a_reset(self, run_dir):
        """Returning to the anchor WITHOUT a solid run (< RESET_MIN_RUN
        frame-changing steps) is ordinary back-and-forth, not a reset."""
        loop = _loop()
        with redirect_stdout(io.StringIO()):
            for _ in range(6):
                _drive(loop, _board(0), 1, _board(1))
                _drive(loop, _board(1), 2, _board(0))
        assert getattr(loop, "_reset_ep_count", 0) == 0


# ── the reset-spam pattern is fully RECORDED (counter only; no guard yet) ───

class TestTheSpamPatternIsRecorded:

    def test_repeated_solid_run_then_reset_is_counted_in_full(self, run_dir):
        """The maintainer's ad-infinitum worry, recorded: every round of the
        solid-run-then-reset loop lands in the counter with the executed
        action attributed. (Scope amendment: the counter REPORTS -- no
        selection guard ships with this pair, so none is asserted here.)"""
        loop = _loop()
        out = _reset_pattern(loop, rounds=5)
        assert loop._reset_ep_count == 5, (
            "the reset-loop pattern must be recorded in full, one count per "
            "revert")
        assert loop._reset_actions == {4: 5}, (
            "each detected reset must attribute the executed action")
        assert out.count("[RESET]") == 5, "every occurrence narrates"

    def test_selection_is_untouched_by_the_counter(self, run_dir, monkeypatch):
        """No guard ships in this pair: after heavy reset spam the blind draw
        still sees every candidate at the incumbent (B2) weights."""
        from types import SimpleNamespace

        import cognitive_loop as cl
        from engines.cognition.cognitive_frame import CognitiveFrame
        loop = _loop()
        with redirect_stdout(io.StringIO()):
            _reset_pattern(loop, rounds=5)
        seen = {}

        real_choice = random.choice

        def spy_choice(seq):
            seen["cands"] = list(seq)
            return real_choice(seq)

        monkeypatch.setattr(cl.random, "choice", spy_choice)
        with redirect_stdout(io.StringIO()):
            loop._act(SimpleNamespace(), "explore", 0.2, None, None,
                      "agent", "pioneer", 0.5, 0.5, CognitiveFrame())
        cands = seen.get("cands")
        assert cands, "the blind movement draw never ran"
        counts = {cands.count(a) for a in set(cands)}
        assert len(counts) == 1, (
            "the counter is instrumentation ONLY -- candidate weights must "
            "stay at the incumbent draw's uniform (per-B2) shape until a "
            "guard enters singly, after the counter has reported")
