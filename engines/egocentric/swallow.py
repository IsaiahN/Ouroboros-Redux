"""swallow.py -- B4 (BUILD_PROGRAM_2 W1, G1): SWALLOW counters.

HOUSE LAW: EGO code never crashes the host loop -- every guarded block swallows
its exceptions. But a swallowed exception is invisible: a broken block can
starve silently for generations. This module gives the containment pattern a
ledger: a fixed ENUM of guarded-block names, a tiny `swallow_note` helper the
instrumented except-branches call (one compact line each), and a SwallowBook
that -- fed the episode's counts at the SAME episode boundary as starvation --
appends AT MOST one enum-coded record per block to the agent's PERSONAL fabric
stream "swallow".

Write-contract (the affect law, as StarvationBook):
  * PURE: `swallowed(counts)` is a pure function of the counts handed in --
    no wall-clock, no RNG, no instance state; identical counts replay to
    identical records;
  * BOUNDED: <= 1 record per block per episode by construction (one pass over
    the fixed BLOCKS enum, each block emits at most once);
  * ENUM-CODED: block names come only from BLOCKS -- machinery facts, no game
    content; unknown names collapse to OTHER at the counting site;
  * NARRATED: every record prints its [SWALLOW] line.

CONSUMER (one-currency law): AffectGains.seed_gain reads the stream back on the
same starvation_steer path and STEERS exploration effort only -- never a bar,
a support, a price, or a reputation.
"""
from __future__ import annotations

from typing import Any, Dict, List

# The fixed enum -- the loop's guarded EGO blocks (machinery names only).
BLOCKS = (
    "OBSERVER",     # PHASE 1 egocentric observation feed
    "SPINE",        # PHASE 2 goal-spine accrual/credit path
    "FABRIC",       # knowledge-fabric init / seeding / re-seeding
    "BINDER_FEED",  # W4c-1 per-class invariance evidence
    "BANK_SETTLE",  # W4c bank commit/settle (and the bet book's settle)
    "MINT_DRAIN",   # W4c-3/4 mint offers + import-queue persistence
    "PLANNER",      # W4c EGO-PLAN drive/shadow block
    "FRONTIER",     # 3d frontier book init / harvest paths
    "AFFECT",       # W4c-6 affect narration / seed-gain consumption
    "STARVATION",   # the episode-boundary starvation settle itself
    "OTHER",        # any guarded block without a named seat
)

TOPIC = "swallow"


def swallow_note(host, block) -> None:
    """The one-line call an instrumented except-branch makes: count the
    swallow on the host loop. Unknown block names collapse to OTHER; a
    hostile host is itself swallowed (the counter never raises)."""
    try:
        _c = getattr(host, "_swallow_counts", None)
        if _c is None:
            _c = {}
            host._swallow_counts = _c
        _b = block if block in BLOCKS else "OTHER"
        _c[_b] = int(_c.get(_b, 0) or 0) + 1
    except Exception:
        pass


class SwallowBook:
    """Episode-boundary swallow readout over the fixed block enum."""

    TOPIC = "swallow"

    def __init__(self, fabric: Any):
        self.fabric = fabric
        self.errors = 0  # fabric-write failures survived (the book never crashes the loop)

    @staticmethod
    def swallowed(counts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """PURE decision: which blocks swallowed, in fixed BLOCKS order."""
        out: List[Dict[str, Any]] = []
        for b in BLOCKS:
            try:
                n = int((counts or {}).get(b, 0) or 0)
            except Exception:
                continue
            if n > 0:
                out.append({"block": b, "count": n})
        return out

    def settle_episode(self, counts: Dict[str, Any], game: str,
                       level: int) -> List[Dict[str, Any]]:
        """Emit the episode's swallow records: at most one per block, each
        appended to the PERSONAL "swallow" stream and narrated. The record is
        a pure function of the arguments (the fabric only adds "seq")."""
        recs: List[Dict[str, Any]] = []
        for s in self.swallowed(counts):
            rec: Dict[str, Any] = {
                "block": s["block"], "count": s["count"], "game": str(game),
                "level": int(level),
            }
            try:
                stored = self.fabric.append("personal", TOPIC, rec)
            except Exception:
                self.errors += 1
                stored = rec
            print("[SWALLOW] block=%s count=%d level=%d"
                  % (rec["block"], rec["count"], rec["level"]))
            recs.append(dict(stored))
        return recs
