"""
exploration.py -- brick 10a: the exploration drive that stops the loop collapsing onto the first
convergent action (the gap the first live ls20 run exposed: only A1 was ever tried).

MAP §8: generation is pointed at OUTSTANDING surprise -- an action never tried carries the most
unresolved prediction-information, so it must earn the highest pull. FMap: federated_learning (d=0.117,
nearest of the 46). Its lesson for this failure: do NOT let one client (action) dominate the aggregate
before the others have participated -- guarantee COVERAGE. Its failure mode is premature convergence to
a biased aggregate when early/loud clients crowd out the rest; that is exactly the collapse we saw.

Goodhart guard: the novelty bonus is predictive-information-STILL-AVAILABLE and DECAYS with visits, so
it cannot be farmed by thrashing -- a learned action stops being novel. Once every action has been
sampled enough, the bonus fades and exploitation (learned belief) takes over. Nothing silent.
"""
from __future__ import annotations
from typing import Dict, List


class Explorer:
    """Count-based novelty: an untried action gets the full bonus; the bonus decays as it is visited, so
    exploration is guaranteed early (coverage) and vanishes late (convergence)."""

    def __init__(self, novelty_weight: float = 1.0):
        if novelty_weight < 0:
            raise ValueError("novelty_weight must be >= 0")
        self.novelty_weight = float(novelty_weight)
        self.visits: Dict[str, int] = {}
        self.log: List[str] = []

    def bonus(self, action: str) -> float:
        """Predictive information still available for this action: full when untried, ->0 as it is learned."""
        v = self.visits.get(action, 0)
        return self.novelty_weight / (1.0 + v)

    def visit(self, action: str) -> None:
        """Record that the action was actually committed this step (its novelty is now partly spent)."""
        self.visits[action] = self.visits.get(action, 0) + 1
        self.log.append("VISIT  %s -> n=%d (bonus now %.3f)" % (action, self.visits[action], self.bonus(action)))

    def coverage(self, actions: List[str]) -> float:
        """Fraction of the action set that has been tried at least once (the anti-collapse metric)."""
        if not actions:
            return 1.0
        return sum(1 for a in actions if self.visits.get(a, 0) > 0) / len(actions)
