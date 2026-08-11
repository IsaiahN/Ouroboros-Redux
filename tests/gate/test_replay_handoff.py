"""PHASE 3c GATE: the handoff at the frontier — replay episodes stop discarding their budget.

⭐ WHY. Found at play_game's replay branch: `return replay_result` — a replayed episode ENDS at
replay completion, throwing away every remaining action. Stock v4's only reliable route to
level 2's doorstep ends the episode on arrival; the 1800-episode zero-L2 baseline was not a
weak lottery at L2 — for replayed episodes there was NO lottery. v1 is the PURE handoff (no
synthetic credit): post-replay, cognitive play continues with the remaining budget; the wheel
opens only via fabric priors or a live level-up (the wheel rule untouched).

THE CONTRACT (PREREG_PHASE3C.md §2):
  * the unconditional `return replay_result` is replaced by a GUARDED handoff: return only on
    WIN, GAME_OVER, or exhausted budget; otherwise continue into ordinary cognitive play with
    the REMAINING budget (max_actions reduced by the replay's actions_taken);
  * a `[REPLAY-HANDOFF]` log line marks the transition (remaining budget stated);
  * the final GameResult reflects the WHOLE episode: levels_completed from the latest
    observation, actions from replay + continuation;
  * no replay (replay_result None) → the ordinary path, byte-untouched.

These are source-contract tests (the player's episode loop needs a live env; the LIVE half of
this gate is the pre-registered population falsifier: post-replay cognitive actions visible on
≥3 banked games). Run pre-build: they failed (the unconditional return was present).
"""
from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _src():
    return open(os.path.join(REPO, "cognitive_game_player.py"), encoding="utf-8",
                errors="replace").read()


class TestTheHandoffContract:

    def test_the_unconditional_return_is_gone(self):
        src = _src()
        i = src.find("replay_result = self._replay_winning_sequences(")
        assert i != -1, "the replay call site moved — update this gate deliberately"
        window = src[i:i + 2500]
        assert re.search(r"if replay_result is not None:\s*\n\s*return replay_result", window) is None, (
            "play_game still returns unconditionally at replay completion — the remaining "
            "budget is discarded and level 2 is never attempted (the 3c gap, unfixed).")

    def test_terminal_replays_still_return(self):
        """WIN and GAME_OVER (and exhausted budget) must end the episode as before."""
        src = _src()
        i = src.find("replay_result = self._replay_winning_sequences(")
        window = src[i:i + 2500]
        assert "is_win" in window and ("GAME_OVER" in window or "game_over" in window
                                       or "remaining" in window), (
            "the handoff guard must distinguish terminal replays (return) from non-terminal "
            "ones (continue)")
        assert "return replay_result" in window, (
            "terminal replays must still return the replay result")

    def test_the_handoff_is_logged_with_remaining_budget(self):
        src = _src()
        assert "[REPLAY-HANDOFF]" in src, "no handoff log — the live falsifier cannot be judged"
        i = src.find("[REPLAY-HANDOFF]")
        window = src[max(0, i - 300):i + 300]
        assert "remain" in window.lower(), "the handoff line must state the remaining budget"

    def test_the_continuation_budget_is_reduced_by_the_replay(self):
        src = _src()
        i = src.find("[REPLAY-HANDOFF]")
        window = src[max(0, i - 1500):i + 1500]
        assert "actions_taken" in window, (
            "the continuation must subtract the replay's actions from the episode budget — "
            "otherwise replayed episodes get a longer total budget than the baseline's, and "
            "the scored L2 number is contaminated")
