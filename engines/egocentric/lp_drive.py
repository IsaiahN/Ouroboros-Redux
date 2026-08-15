"""G-D: the LP drive -- C33's three-arm exploration control (PREREG_FINAL_GAPS.md).

The arm is selected per worker by the LP_DRIVE_ARM env variable (the swarm
supervisor assigns it deterministically, sha1(game) mod 3 -- assign_arm below):

  * "fixed"  (default, and the fallback for any unknown label) -- current
    behavior, byte-identical: steer() hands its candidates back unchanged,
    the same object. The floor.
  * "random" -- current behavior, byte-identical. The arm exists as a LABEL
    for the control harness (C33 §1: the presupposition retires against
    RANDOM, not fixed); the loop's existing RNG already supplies the
    randomness, so nothing is added here -- an RNG wearing an emotion label
    must not be able to pass.
  * "lp"     -- learning progress: exploration is REWEIGHTED toward candidate
    sites whose recent NOVEL-bin residuals were LARGE and COMPRESSIBLE.

THE SIGNAL (pure, bounded, replayable -- affect's replay law, lp(t) =
f(ledger[0:t])): signal() reads the last WINDOW records of the collective
"import_queue" stream (the router's NOVEL bin, persisted by W4c-4) and, for
each record carrying before/after evidence, scores its changed-cell bbox:

    weight = clamp(residual * margin * w_bar, 0, CEIL)

where `residual` is the router's ledgered magnitude (|R|), `margin` is the
headroom under the mint's OWN published MDL inequality -- cost = 1 + changed
(encoding_cost_atom's price) against R = RESIDUAL_CELL_COST * changed +
UNEXPLAINED_PREMIUM with the MDL_MARGIN and the MAX_BBOX_BOARD_FRACTION
pocket test, constants imported from mint.py (one source of truth; a record
that fails the inequality contributes NOTHING -- large |R| alone never
attracts the drive) -- and `w_bar` is the mean ledgered surprise-support "w"
over the last VERDICT_WINDOW mint_verdicts rows for the game (neutral 1.0
when absent). The mint's output AIMS exploration here; it is never a metric:
no price, no mint_bar, no support, no verification is touched.

WRITE-CONTRACT (house law, exposed to the loop via AffectGains.lp_steer):
derived from the ledger only (this module is a PURE READ -- it never appends),
bounded (weights clamped into [0, CEIL]; steering is a stable REORDER of the
candidates the loop already had, never an invented target), narrated ([LP]
emitted whenever the lp arm is consulted -- a steering signal that leaves no
trace is the failure), steers ONLY. No RNG, no wall-clock, no hidden state:
two instances over the same fabric prefix return identical outputs.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from engines.egocentric.mint import (
    MAX_BBOX_BOARD_FRACTION,
    MDL_MARGIN,
    RESIDUAL_CELL_COST,
    UNEXPLAINED_PREMIUM,
)

__all__ = ["ARM_ENV", "ARMS", "CEIL", "LPDrive", "arm", "assign_arm"]

ARM_ENV = "LP_DRIVE_ARM"
ARMS = ("fixed", "random", "lp")
# Bounded recent windows (the replay law needs a fixed prefix function, and the
# steering must stay cheap on a long-lived ledger).
WINDOW = 32            # NOVEL-bin (import_queue) records considered "recent"
VERDICT_WINDOW = 64    # mint_verdicts rows consulted for the ledgered w signal
# The boost is bounded: no residual, however monstrous, buys more than this.
CEIL = 4.0


def arm() -> str:
    """The worker's arm, read from the env at call time. Unknown labels and an
    absent variable are the FIXED arm -- current behavior, byte-identical."""
    v = os.environ.get(ARM_ENV, "fixed").strip().lower()
    return v if v in ARMS else "fixed"


def assign_arm(name: str, recycle_count: int = 0) -> str:
    """Deterministic per-worker assignment for the supervisor, ROTATING per
    recycle: ARMS[(sha1(name) + recycle_count) mod 3]. sha1 (content-addressing,
    not cryptography), never the salted builtin hash: the same (game, recycle)
    pair gets the same arm in every process, restart and reboot.

    The rotation kills the arm/game confound: a worker that carries one arm
    forever makes its game's verdict an arm verdict too. With the recycle
    counter added before the mod, every game visits EVERY arm across any 3
    consecutive recycles, and recycle_count=0 reproduces the original static
    assignment exactly (no history rewritten)."""
    h = hashlib.sha1(str(name).encode("utf-8"), usedforsecurity=False).hexdigest()
    return ARMS[(int(h, 16) + int(recycle_count)) % len(ARMS)]


class LPDrive:
    """The lp arm's signal + steer over a KnowledgeFabric. Pure read; errors
    are counted and survived (channels fall back to no-op), never raised."""

    def __init__(self, fabric):
        self.fabric = fabric
        self.errors = 0

    # ── the signal (pure function of the ledger prefix) ───────────────────────

    def signal(self, game) -> List[Dict[str, Any]]:
        """Scored NOVEL residual sites from the last WINDOW import_queue records,
        in ledger order: [{"slot", "bbox": [r0, c0, r1, c1], "residual",
        "weight"}]. Records without before/after evidence, with no changed
        cells, or failing the mint's MDL pocket inequality contribute nothing."""
        try:
            rows = self.fabric.query("collective", "import_queue")
        except Exception:
            self.errors += 1
            rows = []
        w_bar = self._w_bar(game)
        out: List[Dict[str, Any]] = []
        for q in rows[-WINDOW:]:
            s = self._score(q, w_bar)
            if s is not None:
                out.append(s)
        return out

    def _w_bar(self, game) -> float:
        """The mint's ledgered surprise-support: mean "w" over the game's recent
        verdict rows that carry one; neutral 1.0 when none exist."""
        try:
            rows = self.fabric.query("collective", "mint_verdicts")
        except Exception:
            self.errors += 1
            rows = []
        g = str(game)
        ws = [float(r["w"]) for r in rows[-VERDICT_WINDOW:]
              if r.get("game") == g and isinstance(r.get("w"), (int, float))]
        return (sum(ws) / len(ws)) if ws else 1.0

    def _score(self, q: Dict[str, Any], w_bar: float) -> Optional[Dict[str, Any]]:
        """One import_queue record -> a bounded site weight, or None. The
        compressibility test is the mint's own published inequality (imported
        constants): cost + 0 < R, cost < MDL_MARGIN * R, bbox a pocket."""
        try:
            if q.get("before") is None or q.get("after") is None:
                return None
            b = np.asarray(q["before"])
            a = np.asarray(q["after"])
            if b.ndim != 2 or b.shape != a.shape or b.size == 0:
                return None
            diff = b != a
            changed = int(diff.sum())
            if changed == 0:
                return None
            rr = np.flatnonzero(diff.any(axis=1))
            cc = np.flatnonzero(diff.any(axis=0))
            r0, r1 = int(rr[0]), int(rr[-1])
            c0, c1 = int(cc[0]), int(cc[-1])
            bbox_area = (r1 - r0 + 1) * (c1 - c0 + 1)
            cost = 1.0 + changed                     # encoding_cost_atom's price
            big_r = RESIDUAL_CELL_COST * changed + UNEXPLAINED_PREMIUM
            compresses = (cost < big_r
                          and cost < MDL_MARGIN * big_r
                          and bbox_area < MAX_BBOX_BOARD_FRACTION * b.size)
            if not compresses:
                return None
            margin = 1.0 - cost / (MDL_MARGIN * big_r)      # headroom in (0, 1]
            mag = float(q.get("residual", changed))
            weight = max(0.0, min(CEIL, mag * margin * w_bar))
            if weight <= 0.0:
                return None
            return {"slot": q.get("slot"), "bbox": [r0, c0, r1, c1],
                    "residual": mag, "weight": weight}
        except Exception:
            self.errors += 1
            return None

    # ── the steer (the one consumer-facing operation) ─────────────────────────

    @staticmethod
    def _site_of(cand) -> Optional[Tuple[int, int]]:
        """(x, y) of one explore candidate: ((x, y), rate) or a bare (x, y)."""
        try:
            p = cand[0] if isinstance(cand[0], (list, tuple)) else cand
            return int(p[0]), int(p[1])
        except Exception:
            return None

    def _candidate_score(self, cand, sig: List[Dict[str, Any]]) -> float:
        site = self._site_of(cand)
        if site is None:
            return 0.0
        x, y = site
        total = 0.0
        for s in sig:
            r0, c0, r1, c1 = s["bbox"]
            if r0 <= y <= r1 and c0 <= x <= c1:
                total += float(s["weight"])
        return min(CEIL, total)

    def steer(self, candidates: Sequence, game) -> Sequence:
        """The arm gate. fixed/random: `candidates` comes back unchanged -- the
        SAME object, byte-identical current behavior, no trace. lp: a stable
        descending reorder by site score ([LP] narrated; zero signal leaves the
        order untouched). Never raises; any failure returns the input."""
        if arm() != "lp":
            return candidates
        try:
            sig = self.signal(game)
            scores = [self._candidate_score(c, sig) for c in candidates]
            if not any(s > 0.0 for s in scores):
                print("[LP] arm=lp no-signal candidates=%d window=%d"
                      % (len(candidates), WINDOW))
                return candidates
            order = sorted(range(len(candidates)), key=lambda i: -scores[i])
            out = [candidates[i] for i in order]
            top = self._site_of(out[0])
            print("[LP] arm=lp sites=%d top=%s score=%.3f candidates=%d window=%d"
                  % (len(sig), top, max(scores), len(candidates), WINDOW))
            return out
        except Exception:
            self.errors += 1
            return candidates
