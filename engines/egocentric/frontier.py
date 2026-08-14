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

from typing import Any, Dict, Optional, Set, Tuple

TOPIC = "frontier_paths"
HARVEST_TOPIC = "frontier_harvest"

# ── B2 (BUILD_PROGRAM_2 W1): movement-affordance bias constants ──────────────
MOVE_KIND = "move"    # the discriminator riding the SAME harvest stream
MOVE_NOOP_MIN = 3     # observations before an action is judged at all
MOVE_NOOP_RATE = 0.8  # no-op fraction that marks an action deprioritized
MOVE_BIAS = 3         # bounded bias: preferred actions weighted 3x -- never a veto


def bias_moves(candidates, moves) -> list:
    """B2 consumer: a WEIGHTED candidate list for the blind 1-5 chooser.

    An action with >= MOVE_NOOP_MIN banked outcomes and a no-op rate >=
    MOVE_NOOP_RATE keeps weight 1; every other candidate appears MOVE_BIAS
    times. Every candidate stays present (a bounded bias, not a veto);
    no data -> uniform; garbage -> the candidates unchanged.
    """
    try:
        out = []
        for a in candidates:
            ch, un = ((moves or {}).get(str(a)) or (0, 0))[:2]
            n = int(ch) + int(un)
            noop = n >= MOVE_NOOP_MIN and int(un) >= MOVE_NOOP_RATE * n
            out.extend([a] * (1 if noop else MOVE_BIAS))
        return out or list(candidates)
    except Exception:
        return list(candidates)


def plan_veto(site, harvest, avoid=None) -> bool:
    """B3: PURE frontier veto for the planner's DRIVE click -- True iff the
    planned target sits in the loaded harvest's fatal/dead sets or the banked
    avoid-set. None/empty inputs never veto; garbage never raises (the book
    must never crash the loop it advises)."""
    try:
        if site is None:
            return False
        _c = (int(site[0]), int(site[1]))
        _h = harvest if isinstance(harvest, dict) else {}
        return bool(_c in (_h.get("fatal") or set())
                    or _c in (_h.get("dead") or set())
                    or _c in (avoid or set()))
    except Exception:
        return False


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

    # ── 3d-ii: the exploration harvest — bank the experience, not the death spot ──

    def record_harvest(self, game: str, level: int, dead=None, effects=None,
                       fatal: Optional[Tuple[int, int]] = None,
                       deltas: Optional[Dict[str, Tuple[int, int]]] = None) -> None:
        """Bank one episode's frontier experience (PREREG_FRONTIER_HARVEST.md):
        dead cells (clicked, no effect), effect cells (clicked, frame changed),
        the fatal cell if the episode died, and the established action->delta
        map. Observations, never signal -- nothing here opens the wheel."""
        try:
            self.fabric.append("collective", HARVEST_TOPIC, {
                "game": str(game),
                "level": int(level),
                "dead": [[int(c[0]), int(c[1])] for c in (dead or [])],
                "effects": [[int(c[0]), int(c[1])] for c in (effects or [])],
                "fatal": ([int(fatal[0]), int(fatal[1])]
                          if fatal is not None else None),
                "deltas": {str(a): [int(d[0]), int(d[1])]
                           for a, d in (deltas or {}).items()},
            })
        except Exception:
            self.errors += 1

    # ── B2 (BUILD_PROGRAM_2 W1): movement affordances -- record_moves/load_moves
    # mirror record_harvest/load_harvest on the SAME stream, "kind"-discriminated.

    def record_moves(self, game: str, level: int, moves) -> None:
        """Bank one episode's movement outcomes: per-action (1-5) counts of
        frame-changed vs unchanged results, {action: (changed, unchanged)}.
        Observations, never signal -- nothing here opens the wheel."""
        try:
            self.fabric.append("collective", HARVEST_TOPIC, {
                "game": str(game),
                "level": int(level),
                "kind": MOVE_KIND,
                "moves": {str(a): [int(c[0]), int(c[1])]
                          for a, c in (moves or {}).items()},
            })
        except Exception:
            self.errors += 1

    def load_moves(self, game: str, level: int) -> Dict[str, Tuple[int, int]]:
        """Sum banked movement outcomes for game+level across ALL move records
        (seeds+local): {action: (changed_total, unchanged_total)}. Non-move
        records are ignored; deterministic; empty dict on error."""
        try:
            g, lv = str(game), int(level)
            out: Dict[str, Tuple[int, int]] = {}
            for rec in self.fabric.query(
                    "collective", HARVEST_TOPIC,
                    where=lambda r: (r.get("game") == g and r.get("level") == lv
                                     and r.get("kind") == MOVE_KIND)):
                for a, c in (rec.get("moves") or {}).items():
                    if len(c) == 2:
                        prev = out.get(str(a), (0, 0))
                        out[str(a)] = (prev[0] + int(c[0]), prev[1] + int(c[1]))
            return out
        except Exception:
            self.errors += 1
            return {}

    def load_harvest(self, game: str, level: int) -> Dict[str, Any]:
        """Merge ALL harvest records for game+level (seeds+local): effects and
        fatal are unions; dead is CONSERVATIVE (reported dead in >=2 independent
        records AND never in any effects list -- an effect report always wins);
        tried is the union of every reported cell; deltas keep the first-seen
        value per action in record order (deterministic)."""
        empty: Dict[str, Any] = {"dead": set(), "effects": set(), "fatal": set(),
                                 "tried": set(), "deltas": {}}
        try:
            g, lv = str(game), int(level)
            dead_counts: Dict[Tuple[int, int], int] = {}
            effects: Set[Tuple[int, int]] = set()
            fatal: Set[Tuple[int, int]] = set()
            deltas: Dict[str, Tuple[int, int]] = {}
            for rec in self.fabric.query(
                    "collective", HARVEST_TOPIC,
                    where=lambda r: (r.get("game") == g and r.get("level") == lv
                                     and r.get("kind") != MOVE_KIND)):
                for c in rec.get("dead") or []:
                    if len(c) == 2:
                        cell = (int(c[0]), int(c[1]))
                        dead_counts[cell] = dead_counts.get(cell, 0) + 1
                for c in rec.get("effects") or []:
                    if len(c) == 2:
                        effects.add((int(c[0]), int(c[1])))
                fc = rec.get("fatal")
                if fc is not None and len(fc) == 2:
                    fatal.add((int(fc[0]), int(fc[1])))
                for a, d in (rec.get("deltas") or {}).items():
                    if str(a) not in deltas and len(d) == 2:
                        deltas[str(a)] = (int(d[0]), int(d[1]))
            dead = {c for c, n in dead_counts.items()
                    if n >= 2 and c not in effects}
            tried = set(dead_counts) | effects | fatal
            return {"dead": dead, "effects": effects, "fatal": fatal,
                    "tried": tried, "deltas": deltas}
        except Exception:
            self.errors += 1
            return empty
