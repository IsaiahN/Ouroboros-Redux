"""frontier.py -- 3d-i: frontier pariah paths (PREREG_FRONTIER_PARIAH.md).

Each frontier death permanently removes an opening: when an episode that stood
at frontier level N dies, its FIRST post-frontier click is banked in the fabric
(collective scope, topic "frontier_paths") as a fatal opening. `avoid_set`
reads the union back from seeds+local, so the compounding is population-wide.
Exploration ORDERING, not goal-claiming -- the wheel rule is untouched.

Discipline (as the spine): deterministic (no RNG, no wall-clock), and EVERY
exception is swallowed to the `errors` counter -- the book must never crash
the loop it advises.
"""
from __future__ import annotations

from typing import Any, Set, Tuple

TOPIC = "frontier_paths"


class FrontierBook:
    """Fabric-backed ledger of fatal openings, keyed by (game, level)."""

    def __init__(self, fabric: Any):
        self.fabric = fabric
        self.errors: int = 0

    def record_fatal_opening(self, game: str, level: int,
                             cell: Tuple[int, int]) -> None:
        """Bank one fatal opening: the first post-frontier click of an episode
        that died at frontier `level` of `game`."""
        try:
            self.fabric.append("collective", TOPIC, {
                "game": str(game),
                "level": int(level),
                "cell": [int(cell[0]), int(cell[1])],
                "fatal": True,
            })
        except Exception:
            self.errors += 1

    def avoid_set(self, game: str, level: int) -> Set[Tuple[int, int]]:
        """Union of banked fatal openings for game+level, seeds+local
        (population-wide compounding). Deterministic; empty set on error."""
        try:
            g, lv = str(game), int(level)
            out: Set[Tuple[int, int]] = set()
            for rec in self.fabric.query(
                    "collective", TOPIC,
                    where=lambda r: (r.get("game") == g
                                     and r.get("level") == lv
                                     and r.get("fatal"))):
                c = rec.get("cell") or []
                if len(c) == 2:
                    out.add((int(c[0]), int(c[1])))
            return out
        except Exception:
            self.errors += 1
            return set()
