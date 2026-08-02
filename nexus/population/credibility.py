"""nexus.population.credibility -- the shared credibility-weighted database Γ + market arbiter M.

The market arbiter (Tether §4.2): propose -> vote -> resolve, a PRICE not a controller. Credibility
evolves by usage-weighted success and is DISCOUNTED BY COVARIANCE WITH THE POPULATION (§7.3): a
proposal that predicts what the population already predicts is priced lower (negative-correlation
learning), so redundant co-firing is not rewarded and diversity is not silently competed away.

`gamma` is the promoted, ECHO-verified shared library -- the only thing that crosses the membrane
upward. It is what seed-down descends to the individuals. Nothing enters `gamma` except through
membrane.promote (this class never self-promotes on a proposal).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict
from ..kernel import Predicate


def _clip01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


class CredibilityDB:
    def __init__(self, lam: float = 0.3, lr: float = 0.3):
        self.lam = lam                       # covariance-discount strength
        self.lr = lr                         # credibility learning rate
        self.cred: Dict[str, float] = {}     # pred_key -> credibility in [0,1]
        self.gamma: Dict[str, Predicate] = {}  # promoted shared library (ECHO-verified only)

    def market_value(self, ground_score: float, redundancy: int, n_roles: int) -> float:
        """bid = reward_prediction - λ·covariance_with_population. `redundancy` = how many roles
        proposed this same predicate this round; correlated proposals are priced down."""
        corr = max(0, redundancy - 1) / max(1, n_roles)
        return ground_score - self.lam * corr

    def vote(self, key: str, ground_score: float, redundancy: int, n_roles: int) -> float:
        """Update credibility toward the covariance-discounted market value. Returns the value."""
        v = self.market_value(ground_score, redundancy, n_roles)
        self.cred[key] = _clip01(self.cred.get(key, 0.0) + self.lr * (v - self.cred.get(key, 0.0)))
        return v

    def promote(self, key: str, pred: Predicate) -> None:
        """Enter a predicate into shared Γ. Called ONLY by the membrane after ECHO + ground verify."""
        self.gamma[key] = pred

    def shared_gamma(self) -> Dict[str, Predicate]:
        return dict(self.gamma)
