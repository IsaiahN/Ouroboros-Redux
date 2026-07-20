"""
two_streams.py -- THE MAP SS9.2 / SS3 / I2a: the two-stream architecture and the POSE.

  * Stream A = PRIVATE encounter history (the accumulated residuals -- what happened that the grammar
    did not predict). Path-dependent, non-transferable.
  * Stream B = NETWORK WISDOM: the grammar / priors -- what SHOULD happen.
  * alpha = the LEARNABLE weighting between them.  decision = alpha*private + (1-alpha)*social.
  * THE POSE (SS3, SS5): alpha + an encounter history IS the pose -- a vantage that is its OWN for a
    stateable reason. Two shells of identical architecture diverge for two reasons: divergent
    encounter history, and the learnable alpha.

FMap framing: arrows_impossibility -- there is NO axiomatically-perfect way to aggregate private vs
social preference, so alpha cannot be a fixed optimal rule; it must be LEARNED from the outcomes of
past weightings (the map's own claim). alpha is updated with a DECAYING learning rate, so EARLY
encounters imprint more (primacy) -- which makes the update ORDER-SENSITIVE (path-dependent). That
path-dependence is exactly what the I2a falsifier (Appendix E.3) requires: identical architecture +
divergent encounter ORDER must produce divergent alpha, or the pose mechanism is false and non-
identity is just noise. (Test test_i2a_falsifier pins it.)

Nothing silent: every weighting update is logged.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple


class Pose:
    """A vantage: a learnable alpha over (private residual instinct) vs (social grammar), plus the
    encounter history that shaped it. Identical Poses fed different encounter ORDER diverge in alpha."""

    def __init__(self, alpha: float = 0.5, lr0: float = 0.5):
        if not (0.0 <= alpha <= 1.0):
            raise ValueError("alpha must be in [0,1]")
        self.alpha = float(alpha)          # weight on the PRIVATE stream (Stream A)
        self.lr0 = float(lr0)
        self.history: List[Tuple[float, float]] = []   # (private_error, social_error) encounters -- Stream A record
        self.log: List[str] = []

    def decide(self, private: float, social: float) -> float:
        """The convex blend: trust private instinct by alpha, social pressure by (1-alpha)."""
        return self.alpha * private + (1.0 - self.alpha) * social

    def learn(self, private_error: float, social_error: float) -> None:
        """alpha LEARNS from the outcome of the last weighting: if the PRIVATE stream predicted better
        (lower error) than the social one, trust private more (alpha up); else trust social more (down).
        The learning rate DECAYS with experience, so early encounters imprint more -> order-sensitive."""
        t = len(self.history)
        lr = self.lr0 / (1.0 + t)                      # primacy: early experience moves alpha more
        # signed, magnitude-scaled by how decisively one stream beat the other
        gap = social_error - private_error             # >0 -> private was better -> raise alpha
        denom = abs(social_error) + abs(private_error) + 1e-9
        step = lr * (gap / denom)
        self.alpha = min(1.0, max(0.0, self.alpha + step))
        self.history.append((float(private_error), float(social_error)))
        self.log.append("WEIGHT  t=%d lr=%.3f private_err=%.2f social_err=%.2f -> alpha=%.3f"
                        % (t, lr, private_error, social_error, self.alpha))

    def clone_fresh(self) -> "Pose":
        """A shell with IDENTICAL architecture + init, no history yet (for the I2a divergence test)."""
        return Pose(alpha=0.5, lr0=self.lr0)
