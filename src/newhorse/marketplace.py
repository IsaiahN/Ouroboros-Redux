"""
marketplace.py -- THE MAP SS9.3 / SS7: the router is a PRICE, not a decider.

The invariant (SS7): propose -> vote -> resolve. Only the actor / currency / arena bindings change.
Whichever vantage has the most salient prediction on the CURRENT frame drives the next action.

Grounded via the FMap on predictive_processing (a multi-layered hypothesis-testing system where the
best predictor wins) + goodharts_law GUARD (when the price becomes a target it stops measuring).

  * CURRENCY = prediction error (the residual, SS8), measured EXTERNALLY against ground truth -- a
    hypothesis cannot self-report its own salience.
  * GOODHART GUARD (the FMap's warning, built in): reward INFORMATIVE accuracy -- correctly predicting
    the cells that ACTUALLY changed -- NOT trivially matching the unchanged background. A hypothesis
    that games the measure by predicting "nothing changes" earns ZERO salience on a frame that changed,
    so it can never win by saying nothing. Hallucinated change (predicting change where none occurred)
    is penalised, so over-claiming is not a free win either.
  * NOTHING SILENT: every proposal, score, and resolution is logged.

Only the currency function is pluggable (SS7 "only actor/currency/arena bindings change"); the
propose->vote->resolve invariant is fixed.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
import numpy as np


class Hypothesis:
    """An actor/vantage: given the BEFORE frame it commits a prediction of the AFTER frame.
    (Prediction is committed BEFORE the outcome -- it cannot read the result: the SS10/III.10 guard.)"""
    def __init__(self, name: str, predict: Callable[[np.ndarray], np.ndarray]):
        self.name = name
        self._predict = predict

    def predict(self, before: np.ndarray) -> np.ndarray:
        return np.asarray(self._predict(np.asarray(before)))


def informative_salience(before: np.ndarray, predicted: np.ndarray, actual: np.ndarray) -> float:
    """The Goodhart-guarded currency: credit for correctly predicting REAL change, minus hallucinated change."""
    before, predicted, actual = np.asarray(before), np.asarray(predicted), np.asarray(actual)
    changed = (actual != before)
    n_changed = int(changed.sum())
    if n_changed == 0:
        # a no-change frame teaches little; score = fraction correct, low stakes, no Goodhart exposure
        return float((predicted == actual).mean())
    correct_changed = int(((predicted == actual) & changed).sum())         # got the REAL change right
    hallucinated = int(((predicted != before) & ~changed).sum())           # claimed change where none occurred
    # normalise by the amount of real change; a trivial no-change predictor scores 0 here (correct_changed=0)
    return (correct_changed - hallucinated) / n_changed


@dataclass
class Resolution:
    winner: Optional[str]
    scores: dict            # name -> salience
    drove: bool             # did anyone earn positive salience? (else no confident driver this turn)


class Marketplace:
    """propose -> vote -> resolve. The most salient predictor on the current frame drives next."""

    def __init__(self, currency: Callable[[np.ndarray, np.ndarray, np.ndarray], float] = informative_salience):
        self.currency = currency           # pluggable (SS7); default is the Goodhart-guarded residual price
        self.log: List[str] = []

    def resolve(self, before: np.ndarray, actual_after: np.ndarray,
                hypotheses: List[Hypothesis]) -> Resolution:
        before, actual_after = np.asarray(before), np.asarray(actual_after)
        if before.shape != actual_after.shape:
            raise ValueError("before/after must share shape at full resolution (no downsampling)")
        scores: dict = {}
        # PROPOSE + VOTE: each vantage predicts (committed pre-outcome); the currency prices it vs ground truth
        for h in hypotheses:
            pred = h.predict(before)
            if pred.shape != actual_after.shape:
                raise ValueError("hypothesis '%s' predicted a wrong-shaped frame" % h.name)
            s = float(self.currency(before, pred, actual_after))
            scores[h.name] = s
            self.log.append("VOTE  %s salience=%.3f" % (h.name, s))
        # RESOLVE: highest salience drives; deterministic tie-break by name; require positive salience to drive
        if not scores:
            return Resolution(None, {}, False)
        top = max(scores.values())
        best_name = sorted(n for n, s in scores.items() if s == top)[0]     # tie-break by name -> no chatter
        drove = scores[best_name] > 0
        self.log.append("RESOLVE  %s drives (salience=%.3f)%s"
                        % (best_name, scores[best_name], "" if drove else "  [no confident driver -> explore]"))
        return Resolution(best_name if drove else None, scores, drove)
