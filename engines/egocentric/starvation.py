"""starvation.py -- R1 (PREREG_READOUTS.md): socket starvation codes.

THE LINE: the agent may read its own RESIDUAL; it may never read its own GRADE.
This module is the residual readout: a fixed ENUM of game-agnostic machinery
codes, and a book that -- fed one episode's socket counters at the episode
boundary -- decides which sockets STARVED (exercised persistently, zero passes)
and appends AT MOST one record per socket to the agent's PERSONAL fabric
stream "starvation".

Write-contract (the affect law, as AffectGains):
  * PURE: `starved(counters)` is a pure function of the counters handed in --
    no wall-clock, no RNG, no instance state; identical counters replay to
    identical records;
  * BOUNDED: <= 1 record per socket per episode by construction (one pass over
    the fixed SOCKETS spec, each socket emits at most once);
  * ENUM-CODED: codes come only from CODES -- machinery facts, no game content;
  * NARRATED: every record prints its [STARVE] line ("[STARVE] socket=CODE").

CONSUMER (one-currency law): AffectGains.starvation_steer reads the stream
back and STEERS exploration effort only -- never a bar, a support, a price,
or a reputation.

Thresholds (documented choices):
  * PLAN_N = 50 -- the plan-gate sockets (g1..g7) are exercised once per cycle;
    50 exercised cycles with zero passes is persistent starvation, not noise.
  * BOOK_N = 10 -- the mint/bank sockets are fed by rarer events (queue drains,
    settlements); 10 exercised offers with zero passes already names the fact.
"""
from __future__ import annotations

from typing import Any, Dict, List

# The fixed enum -- game-agnostic machinery facts only (PREREG_READOUTS.md R1).
CODES = (
    "NO_STABLE_REFERENCE",    # g2 never passed: no reference snapshot materialised
    "NO_REFERENCE_BINDING",   # g4 never passed: no class ever bound to REFERENCE
    "EMPTY_PLAN",             # g7 never passed: the planner never produced steps
    "NO_NEGATIVE_INSTANCES",  # no falsifying evidence ever accrued (feeder queued)
    "MINT_STARVED",           # the mint was offered evidence and never minted
    "BANK_NO_FAMILY",         # the bank settled and no learned family ever bet
)

PLAN_N = 50   # plan-gate sockets: exercised every cycle -- cheap, so the bar is high
BOOK_N = 10   # mint/bank sockets: fed by rarer events -- 10 dry offers name the fact

# socket -> (exercised counter key, passed counter key, code, threshold N).
# A socket starves iff exercised >= N and passed == 0. Downstream sockets of a
# starved gate go UNEXERCISED (their tried-count stays low), so only the FIRST
# collapsed socket in a chain emits -- the machinery fact, not its echo.
SOCKETS = (
    ("plan_reference", "g1", "g2", "NO_STABLE_REFERENCE", PLAN_N),
    ("plan_binding", "g3", "g4", "NO_REFERENCE_BINDING", PLAN_N),
    ("plan_steps", "g6", "g7", "EMPTY_PLAN", PLAN_N),
    ("negatives", "neg_tried", "neg_passed", "NO_NEGATIVE_INSTANCES", PLAN_N),
    ("mint", "mint_tried", "mint_passed", "MINT_STARVED", BOOK_N),
    ("bank", "bank_tried", "bank_passed", "BANK_NO_FAMILY", BOOK_N),
)


class StarvationBook:
    """Episode-boundary starvation readout over a fixed socket spec."""

    TOPIC = "starvation"

    def __init__(self, fabric: Any):
        self.fabric = fabric
        self.errors = 0  # fabric-write failures survived (the book never crashes the loop)

    @staticmethod
    def starved(counters: Dict[str, Any]) -> List[Dict[str, str]]:
        """PURE decision: which sockets starved, in fixed SOCKETS order.
        A socket starved iff it was exercised >= N times with ZERO passes."""
        out: List[Dict[str, str]] = []
        for socket, tried_key, pass_key, code, n in SOCKETS:
            try:
                tried = int(counters.get(tried_key, 0) or 0)
                passed = int(counters.get(pass_key, 0) or 0)
            except Exception:
                continue
            if tried >= n and passed == 0:
                out.append({"socket": socket, "code": code})
        return out

    def settle_episode(self, counters: Dict[str, Any], game: str, level: int,
                       budget_spent: int) -> List[Dict[str, Any]]:
        """Emit the episode's starvation records: at most one per socket, each
        appended to the PERSONAL "starvation" stream and narrated. The record
        is a pure function of the arguments (the fabric only adds "seq")."""
        recs: List[Dict[str, Any]] = []
        for s in self.starved(counters):
            rec: Dict[str, Any] = {
                "socket": s["socket"], "code": s["code"], "game": str(game),
                "level": int(level), "budget_spent": int(budget_spent),
            }
            try:
                stored = self.fabric.append("personal", "starvation", rec)
            except Exception:
                self.errors += 1
                stored = rec
            print("[STARVE] %s=%s level=%d budget_spent=%d"
                  % (rec["socket"], rec["code"], rec["level"],
                     rec["budget_spent"]))
            recs.append(dict(stored))
        return recs
