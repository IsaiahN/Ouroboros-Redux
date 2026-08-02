"""nexus.population.credibility -- the shared credibility-weighted database Γ + market arbiter M,
now with RECENCY-DECAY and a CUSUM regime trigger (mined from the retired `main` line's
micro_market + evolvability_engine; see FINDINGS_mining_the_main_line_for_nexus).

The market arbiter (Tether §4.2): propose -> vote -> resolve, a PRICE not a controller. Credibility
evolves by usage-weighted success, DISCOUNTED BY COVARIANCE WITH THE POPULATION (§7.3) so redundant
co-firing is not rewarded.

The mine that hardens it: credibility must decay ON THE CLOCK, not only when re-voted. The plain
vote-EMA froze a stale incumbent's standing (a role right on an early regime stayed trusted through a
regime change it no longer fit -- the "incumbency" pathology). So:
  * `tick()` decays every credibility toward zero by a HALF-LIFE each round -- standing is earned by
    recent prediction and forgotten if not renewed.
  * `note_round(mean_success)` feeds a CUSUM; on a PERSISTENT drop (a regime change, not a flicker)
    incumbents are discounted at once -- they earned their standing on a regime that is gone.

`gamma` (promoted, ECHO-verified shared library) is unchanged and still enters only via the membrane.
"""
from __future__ import annotations
from typing import Dict
from ..kernel import Predicate
from .regime import Cusum


def _clip01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


class CredibilityDB:
    def __init__(self, lam: float = 0.3, lr: float = 0.3, half_life_rounds: float = 6.0,
                 regime_discount: float = 0.5):
        self.lam = lam                                   # covariance-discount strength
        self.lr = lr                                     # per-vote EMA rate
        self.decay = 0.5 ** (1.0 / max(1e-6, half_life_rounds))  # per-round clock decay (anti-incumbency)
        self.regime_discount = regime_discount           # extra one-shot discount on a detected regime change
        self.cred: Dict[str, float] = {}
        self.gamma: Dict[str, Predicate] = {}
        self._cusum = Cusum()
        self.regime_changes = 0                          # how many change-points fired this run

    # ---- market pricing ---------------------------------------------------------------------------
    def market_value(self, ground_score: float, redundancy: int, n_roles: int) -> float:
        corr = max(0, redundancy - 1) / max(1, n_roles)
        return ground_score - self.lam * corr

    def vote(self, key: str, ground_score: float, redundancy: int, n_roles: int) -> float:
        v = self.market_value(ground_score, redundancy, n_roles)
        self.cred[key] = _clip01(self.cred.get(key, 0.0) + self.lr * (v - self.cred.get(key, 0.0)))
        return v

    # ---- the mined hardening ----------------------------------------------------------------------
    def tick(self) -> None:
        """Advance the clock one round: decay all standing toward zero by the half-life. A role that
        stops predicting well stops being trusted, even if it is never voted down explicitly."""
        for k in list(self.cred):
            self.cred[k] *= self.decay

    def note_round(self, mean_success: float) -> bool:
        """Feed the round's aggregate success to the CUSUM. On a persistent shift (regime change),
        discount every incumbent at once and return True."""
        if self._cusum.update(mean_success):
            self.regime_changes += 1
            for k in list(self.cred):
                self.cred[k] *= self.regime_discount
            return True
        return False

    # ---- shared library (membrane-only entry) -----------------------------------------------------
    def promote(self, key: str, pred: Predicate) -> None:
        self.gamma[key] = pred

    def shared_gamma(self) -> Dict[str, Predicate]:
        return dict(self.gamma)
