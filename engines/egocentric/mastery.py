"""mastery.py -- mastery-lite: replay probability EARNED from replay reliability.

PREREG_MASTERY_LITE.md: the v2 mastery principle scoped to available evidence.
A bank that keeps reproducing its levels keeps its high replay rate; a bank that
starts failing decays back toward exploration automatically. Records live in the
fabric's collective "replay_outcomes" stream (seeds + local, insertion order),
so the earned rate survives reopen and compounds across boxes via seed overlays.

Pure stdlib, deterministic, never raises: any storage error falls back to the
static prior (0.8 banked / 0.2 not).
"""
from __future__ import annotations

from typing import Any


class MasteryLite:
    """Earned replay probability over the last-10 replay outcomes per game."""

    TOPIC = "replay_outcomes"
    WINDOW = 10

    def __init__(self, fabric: Any):
        self.fabric = fabric

    def record_replay_outcome(self, game: str, ok: bool) -> None:
        """Append one outcome (ok = the replay reproduced its banked levels)."""
        try:
            self.fabric.append("collective", self.TOPIC,
                               {"game": str(game), "ok": bool(ok)})
        except Exception:
            pass  # recording must never crash the player

    def replay_probability(self, game: str, has_bank: bool) -> float:
        """0.2 without a bank; 0.8 with a bank and no history (optimistic prior);
        else 0.2 + 0.6 * success_rate over the LAST 10 outcomes (seeds + local,
        stream order). Earned, and DECAYING: failing replays drop the game back
        toward exploration."""
        if not has_bank:
            return 0.2
        try:
            game = str(game)
            recs = self.fabric.query(
                "collective", self.TOPIC,
                where=lambda r: r.get("game") == game)
            recs = recs[-self.WINDOW:]
            if not recs:
                return 0.8
            successes = sum(1 for r in recs if bool(r.get("ok")))
            return 0.2 + 0.6 * (successes / float(len(recs)))
        except Exception:
            return 0.8  # bank exists: the optimistic prior is the safe fallback
