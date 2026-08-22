"""W4a: affect -- the gains on the deliberation loop, computed from the ledger.

Emotion here is the endogenization of the hyperparameters: statistics over the
collective books, never a sensor, never a price. v1 exposes exactly TWO channels
because exactly two knobs are live:

  * seed_bias -- gain on the explore aim's seed. A lively world (recent
    settlements mostly nontrivial) biases the seed toward exploitation of
    residual-rich regions; a quiet one toward exploration.
  * mint_bar  -- the mint threshold. Rises with SILENCE: desperation makes the
    mint pickier, never looser.

THE REPLAY REQUIREMENT is the anti-proxy guard: gains(t) is a pure function of
the collective ledger prefix (streams "settlements" and "mint_verdicts").
No instance state that is not re-derived per call, no wall-clock, no RNG --
two instances over the same fabric directory (even with different agent_ids)
return identical gains() dicts.

Formulas (documented per the contract; WINDOW = last 20 settlements):

  nontrivial_rate = (# settlements in window with truthy "nontrivial") / (window size)
                    ... defaulting to 0.5 when there are zero settlements.

  seed_bias = nontrivial_rate                      -- monotone, bounded in [0, 1].

  mint_bar  = FLOOR + (CEIL - FLOOR) * (1 - nontrivial_rate)
                                                    -- bounded in [FLOOR, CEIL];
              zero settlements -> the midpoint; total silence -> CEIL (the bar
              at its highest); a fully lively window -> FLOOR.

mint_verdicts are consulted for the narration (mint acceptance rate is part of
the legible state) but do not move the two channels in v1 -- channels <= knobs.

THE THIRD CHANNEL (PREREG_PERSISTENCE_MONITOR.md, 2026-08-21):

  persist   = min(1, run/k)   -- the persistence monitor's live run over k
              (engines/egocentric/persistence.py); 0 with no live run or no
              attached monitor; bounded in [0, 1]. A pure function of the
              NARRATION stream prefix (the monitor is that fold), so it
              replays like its two siblings. A MODULATOR, never a price: it
              feeds exactly two sinks -- starvation_steer's explore_boost
              (the STARVE_STEP path: a full run counts as one more starved
              dimension) and goal.GoalManager.observe's stall clock -- and
              nothing that ranks, prices or selects (gate test F5).
"""
from __future__ import annotations

from typing import Any, Dict, List

from engines.egocentric import lp_drive as _lp_drive


class AffectGains:
    """Affect channels derived purely from the books: two from the collective
    ledger, the third (persist) from the agent's own narration stream."""

    MINT_BAR_FLOOR = 1.0
    MINT_BAR_CEIL = 3.0
    WINDOW = 20  # settlements considered "recent"

    def __init__(self, fabric):
        self.fabric = fabric
        self.errors = 0  # counter: fabric-read failures survived (channels fall back to neutral)
        # THE PERSISTENCE MONITOR (PREREG_PERSISTENCE_MONITOR.md): attached by
        # the loop (cognitive_loop._pm_attach) -- the in-memory fold over the
        # narration stream the spine feeds. None = no monitor: persist is 0.
        self.monitor = None

    # ── the third channel's source (read-only; never a stream read here) ──────

    def persist(self, game=None) -> float:
        """persist = min(1, run/k) from the attached monitor; 0.0 without one.
        Bounded in [0, 1]; contained (a monitor failure reads as 0)."""
        mon = self.monitor
        if mon is None:
            return 0.0
        try:
            return min(1.0, max(0.0, float(mon.persist(game))))
        except Exception:
            self.errors += 1
            return 0.0

    # ── internals (all re-derived per call; no cached state) ─────────────────

    def _recent_settlements(self) -> List[Dict[str, Any]]:
        """The last WINDOW settlements -- read as a TAIL, not as a whole stream.

        record/prereg/PERF_AUDIT.md Q4: this was `query(...)[-WINDOW:]`, a full-file parse answering a
        20-record question, and gains() calls it from cognitive_loop.py:1849 twice per
        step -- 0.314 ms over 20 records, 262.250 ms over 40,000, on boxes carrying
        28,772. `query_tail` returns the identical list (byte-identical by contract:
        tests/gate/test_tail_read.py), so nothing downstream of here changes except the
        cost. The fallback is not defensive padding: stand-in fabrics that implement only
        `query` are passed to this class in the live tests, and they must keep working.
        """
        try:
            tail = getattr(self.fabric, "query_tail", None)
            if tail is not None:
                return tail("collective", "settlements", self.WINDOW)
            rows = self.fabric.query("collective", "settlements")
        except Exception:
            self.errors += 1
            return []
        return rows[-self.WINDOW:]

    def _mint_verdicts(self) -> List[Dict[str, Any]]:
        try:
            return self.fabric.query("collective", "mint_verdicts")
        except Exception:
            self.errors += 1
            return []

    def _nontrivial_rate(self) -> float:
        """Fraction of the last WINDOW settlements that were nontrivial.

        Zero settlements -> 0.5 (neutral: seed unbiased, mint_bar at midpoint).
        """
        recent = self._recent_settlements()
        if not recent:
            return 0.5
        hits = sum(1 for r in recent if r.get("nontrivial"))
        return float(hits) / float(len(recent))

    # ── the contract ──────────────────────────────────────────────────────────

    def gains(self) -> Dict[str, float]:
        """The channels: seed_bias and mint_bar, each a pure function of the
        collective ledger; persist, a pure function of the narration prefix."""
        rate = self._nontrivial_rate()
        seed_bias = min(1.0, max(0.0, rate))
        span = self.MINT_BAR_CEIL - self.MINT_BAR_FLOOR
        mint_bar = self.MINT_BAR_FLOOR + span * (1.0 - rate)
        mint_bar = min(self.MINT_BAR_CEIL, max(self.MINT_BAR_FLOOR, mint_bar))
        return {"seed_bias": seed_bias, "mint_bar": mint_bar,
                "persist": self.persist()}

    def narrate(self) -> str:
        """The legibility law: no channel moves without the state being emitted."""
        g = self.gains()
        verdicts = self._mint_verdicts()
        mints = sum(1 for v in verdicts if v.get("verdict") == "mint")
        line = ("affect: seed_bias=%.4f mint_bar=%.4f persist=%.4f "
                "(nontrivial_rate over last %d settlements; mint_verdicts: %d mint / %d total; errors=%d)"
                % (g["seed_bias"], g["mint_bar"], g["persist"], self.WINDOW,
                   mints, len(verdicts), self.errors))
        return line

    # ── R1 CONSUMER (record/prereg/PREREG_READOUTS.md): starvation STEERS, never prices ─────

    STARVE_WINDOW = 6     # <= 1 record/socket/episode: the trailing episode's block
    STARVE_STEP = 0.25    # one starved socket -> +25% exploration effort
    STARVE_CEIL = 2.0     # the boost is bounded: at most double, never a takeover

    def starvation_steer(self, game) -> Dict[str, Any]:
        """The one-currency law: the agent's own starvation records (PERSONAL
        stream "starvation", written by StarvationBook at the episode boundary)
        may STEER exploration effort on the starved dimension -- a bounded
        multiplicative boost -- and nothing else. No mint_bar, no support, no
        pricing, no reputation: gains() is untouched by this stream.

        Pure function of the stream prefix (the replay requirement): the last
        STARVE_WINDOW records for `game`, distinct codes counted, boost =
        min(STARVE_CEIL, 1 + STARVE_STEP * (#codes + persist)). Empty stream,
        no live run -> neutral 1.0.

        THE PERSISTENCE SINK (PREREG_PERSISTENCE_MONITOR.md): the `persist`
        channel enters HERE and only here on the explore side -- a full run
        (persist = 1) widens effort by exactly one STARVE_STEP, as one more
        starved dimension would; no new constant. Everything downstream of
        explore_boost (seed_gain's widen, the loop's rotation window and
        probe budget) is this same path.
        """
        try:
            rows = self.fabric.query("personal", "starvation")
        except Exception:
            self.errors += 1
            rows = []
        g = str(game)
        recent = [r for r in rows if r.get("game") == g][-self.STARVE_WINDOW:]
        codes = tuple(sorted({str(r.get("code")) for r in recent
                              if r.get("code")}))
        boost = min(self.STARVE_CEIL,
                    1.0 + self.STARVE_STEP * (len(codes) + self.persist(g)))
        return {"explore_boost": boost, "codes": codes}

    # ── B5 (BUILD_PROGRAM_2 W1): the APPLIED seed bias at the loop's site ─────

    SWALLOW_STEP = 0.1   # each distinct swallowed block adds +10% widening (B4 consumer)

    def seed_gain(self, game) -> Dict[str, Any]:
        """The seed bias the loop actually APPLIES: gains()["seed_bias"]
        widened MULTIPLICATIVELY when the agent's own starvation codes exist,
        plus SWALLOW_STEP per distinct swallowed block (B4's consumer, the
        same one-currency read path) -- boost capped at STARVE_CEIL, applied
        capped into [0, 1]. A SEPARATE method by contract: gains() keys stay
        exactly {seed_bias, mint_bar} and are untouched by these streams.
        Pure function of the stream prefixes (the replay requirement)."""
        g = self.gains()
        st = self.starvation_steer(game)
        try:
            rows = self.fabric.query("personal", "swallow")
        except Exception:
            self.errors += 1
            rows = []
        blocks = {str(r.get("block")) for r in rows[-self.STARVE_WINDOW:]
                  if r.get("block")}
        boost = min(self.STARVE_CEIL,
                    float(st["explore_boost"]) + self.SWALLOW_STEP * len(blocks))
        return {"base": g["seed_bias"], "boost": boost,
                "applied": min(1.0, g["seed_bias"] * boost),
                "codes": st["codes"], "swallowed": tuple(sorted(blocks))}

    # ── G-D (PREREG_FINAL_GAPS): the LP-drive hook — steering only ────────────

    def lp_steer(self, candidates, game):
        """The LP drive's affect-style face (house write-contract): a signal
        DERIVED from the ledger (a pure read of collective import_queue +
        mint_verdicts — lp_drive never appends), BOUNDED (lp_drive.CEIL),
        NARRATED ([LP], emitted on the lp arm only), that STEERS exploration
        only — it reorders the explore candidates the loop already had and
        touches nothing else: no mint_bar, no support, no pricing, no
        verification; gains() keys stay exactly {seed_bias, mint_bar}. On the
        "fixed"/"random" arms (LP_DRIVE_ARM) the candidates come back
        unchanged — the same object, byte-identical current behavior. Pure
        function of the fabric prefix + the arm (the replay requirement);
        failures are swallowed into self.errors, never raised."""
        try:
            drive = _lp_drive.LPDrive(self.fabric)
            out = drive.steer(candidates, game)
            self.errors += drive.errors
            return out
        except Exception:
            self.errors += 1
            return candidates
