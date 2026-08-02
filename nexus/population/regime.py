"""nexus.population.regime -- a CUSUM change-point detector, mined (as an idea) from the retired
`main` line's evolvability_engine and micro_market (see FINDINGS_mining_the_main_line_for_nexus).

The population needs to know WHEN a regime has changed -- not from a single bad round (a flicker),
but from a PERSISTENT shift in the success stream. That is exactly what CUSUM is for: it accumulates
signed deviations from a reference and fires only when they pile up past a threshold, so one spike
never trips it but a sustained drop does. This is the signal the credibility layer uses to discount
incumbents earned on a regime that is gone -- the anti-incumbency trigger.

Rebuilt clean here; nothing ported. It reports a shift; it does not decide what to do about it.
"""
from __future__ import annotations


class Cusum:
    """Two-sided CUSUM over a scalar stream. Uses the running mean as the reference during a warmup,
    then holds it, so no target has to be hand-set. `fired()` is True only on a persistent shift."""

    def __init__(self, slack: float = 0.05, threshold: float = 0.9, warmup: int = 4):
        # threshold is set above the largest plausible SINGLE-step deviation so one spike can never
        # fire on its own -- only accumulated (persistent) deviation crosses it. That is the mine's
        # whole point: a flicker is not a regime change.
        self.slack = slack            # k: deviations smaller than this don't accumulate (noise band)
        self.threshold = threshold    # h: total accumulated deviation that counts as a real shift
        self.warmup = warmup
        self.n = 0
        self.ref = 0.0                # reference level (running mean until warmup ends, then frozen)
        self.s_hi = 0.0               # accumulates upward deviations
        self.s_lo = 0.0               # accumulates downward deviations
        self._fired = False

    def update(self, x: float) -> bool:
        """Feed one observation; return True iff a change-point fires THIS step (and reset on fire)."""
        self.n += 1
        if self.n <= self.warmup:
            self.ref += (x - self.ref) / self.n      # learn the baseline; never fire during warmup
            return False
        self.s_hi = max(0.0, self.s_hi + (x - self.ref - self.slack))
        self.s_lo = max(0.0, self.s_lo + (self.ref - x - self.slack))
        fire = self.s_hi > self.threshold or self.s_lo > self.threshold
        if fire:
            self.s_hi = self.s_lo = 0.0              # reset; the new level becomes the reference basis
            self.ref = x
            self._fired = True
        return fire

    @property
    def ever_fired(self) -> bool:
        return self._fired
