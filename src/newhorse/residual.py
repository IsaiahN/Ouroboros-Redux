"""
residual.py -- THE MAP SS8 (residual = aim + sense organ + Stream A), SS11 (the brake invariant),
SS10 (minting is re-reading; the MDL test + the before-state guard).

(FMap was dull here -- prediction error is not a distinct framework in the social-theory kernel;
its top hit was the project's own qcycle, i.e. circular. So this brick is grounded directly in the
map, which is explicit. Honesty over a forced framework.)

  * THE SENSE ORGAN (SS8): the grammar says what SHOULD happen; the residual is what happened that
    the grammar did NOT predict -- measured at FULL RESOLUTION (a system never surprised has no HERE).
  * THE BRAKE INVARIANT (SS11 shell 4): NO DRIVE MAY EVER SUPPRESS THE TIME-INTEGRAL OF PREDICTION
    ERROR. The accumulated surprise is the record the priors do not have; a drive may READ it, never
    zero it. Enforced structurally: pe_integral() is monotone non-decreasing; there is no suppress().
  * MINTING IS RE-READING (SS10): a residual is "explained" by a predicate phi only if the MDL test
    passes -- ||phi|| + ||residual|phi|| < ||residual enumerated||. THE GUARD: phi must be evaluable
    on the BEFORE-state; a predicate that reads the AFTER-state compresses perfectly and predicts
    nothing (III.10 tautology) -> minting with reads_after=True is refused.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet, Tuple, List, Optional
import numpy as np
from .perception import check_no_downsampling


class TautologyError(ValueError):
    pass


@dataclass(frozen=True)
class Residual:
    """What the grammar failed to predict, at full resolution: the cells where actual != predicted."""
    unexplained: FrozenSet[Tuple[int, int]]      # (row,col) cells the prediction got wrong
    bits: float                                  # surprise magnitude (a cell = 1 bit here; a real coder refines)

    @property
    def is_empty(self) -> bool:
        return len(self.unexplained) == 0


def sense(predicted_after: np.ndarray, actual_after: np.ndarray) -> Residual:
    """The sense organ: the FULL-RESOLUTION set of cells where reality diverged from the prediction."""
    pa, aa = np.asarray(predicted_after), np.asarray(actual_after)
    check_no_downsampling(pa.shape, aa.shape)     # both must be full-res and same shape
    if pa.shape != aa.shape:
        raise ValueError("predicted and actual must share shape at full resolution")
    ys, xs = np.where(pa != aa)
    cells = frozenset((int(y), int(x)) for y, x in zip(ys, xs))
    return Residual(unexplained=cells, bits=float(len(cells)))


class ResidualBus:
    """Stream A: the accumulated record of having been surprised. The brake invariant lives here."""

    def __init__(self):
        self._integral = 0.0              # time-integral of prediction error -- MONOTONE, un-suppressible
        self._outstanding: float = 0.0    # currently-unexplained surprise (the marketplace currency / the AIM)
        self.log: List[str] = []          # nothing silent

    def observe(self, r: Residual) -> None:
        """Bank a residual. Increases both the integral (forever) and the outstanding aim."""
        self._integral += r.bits          # the record can only GROW (the brake invariant)
        self._outstanding += r.bits
        self.log.append("OBSERVE  +%.0f bits surprise (integral=%.0f, outstanding=%.0f)"
                        % (r.bits, self._integral, self._outstanding))

    def pe_integral(self) -> float:
        """The un-suppressible record of surprise. No drive may reduce this (SS11)."""
        return self._integral

    def outstanding(self) -> float:
        """The currently-unexplained surprise -- the AIM (what generation is pointed at) and the currency."""
        return self._outstanding

    def explain(self, explained_bits: float) -> None:
        """A minted predicate ACCOUNTED FOR some outstanding surprise. This reduces the OUTSTANDING aim
        (the surprise is now understood) but NEVER the integral (it still happened -- we were surprised)."""
        take = min(explained_bits, self._outstanding)
        self._outstanding -= take
        self.log.append("EXPLAIN  -%.0f bits now understood (outstanding=%.0f); integral UNCHANGED=%.0f"
                        % (take, self._outstanding, self._integral))


def mdl_mint(phi_cost_bits: float, residual_given_phi_bits: float, residual_enumerated_bits: float,
             *, phi_reads_after: bool) -> bool:
    """SS10 MDL test: MINT iff the predicate costs less than the exceptions it eliminates.
    GUARD: phi must be a BEFORE-state predicate; one that reads the AFTER-state is a tautology (refused)."""
    if phi_reads_after:
        raise TautologyError("phi reads the after-state -> compresses perfectly, predicts nothing (SS10/III.10)")
    return (phi_cost_bits + residual_given_phi_bits) < residual_enumerated_bits
