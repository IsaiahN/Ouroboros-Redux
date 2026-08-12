"""W2a: the predictor bank -- one predictor per bound slot; every capable slot bets every action.

The board was one slot; now BODY, WORKSPACE, REFERENCE and RESOURCE each carry their own
predictor and their own residual. A slot that can't bet doesn't get read (bet=False).

  * BODY      -- per-action exact (dr, dc) delta evidence, established at >= min_evidence
                 consistent observations (the goal spine's note_move discipline).
  * WORKSPACE -- bets only through Gamma's stored EFFECT atoms for (game, level); a matching
                 atom's apply_effect IS the prediction (from_known_atom=True).
  * REFERENCE -- always bets "unchanged"; a mutated reference is a loud residual.
  * RESOURCE  -- per-action exact scalar delta evidence, same discipline as BODY.

Discipline: deterministic (no RNG, no wall-clock), every exception is swallowed to the
`errors` counter -- the bank must never crash the loop it advises. Works with gamma=None
(effects is imported lazily inside the workspace path only).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np

__all__ = ["PredictorBank"]


def _no_bet(observed: Any) -> Dict[str, Any]:
    return {"bet": False, "predicted": None, "observed": observed,
            "residual": 0.0, "from_known_atom": False}


class PredictorBank:
    """commit(slot_states, action) then settle(observed_states) -> per-slot verdicts."""

    def __init__(self, gamma=None, game=None, level=None, min_evidence: int = 3):
        self.gamma = gamma
        self.game = game
        self.level = level
        self.min_evidence = int(min_evidence)
        # action -> {exact (dr, dc) delta -> count}
        self._body_evidence: Dict[int, Dict[Tuple[int, int], int]] = {}
        # action -> {exact float delta -> count}
        self._resource_evidence: Dict[int, Dict[float, int]] = {}
        self._pending: Optional[Dict[str, Any]] = None
        self._pending_action: Optional[int] = None
        self.errors: int = 0

    # ── commit ────────────────────────────────────────────────────────────────

    def commit(self, slot_states: Dict[str, Any], action: int) -> None:
        try:
            self._pending = dict(slot_states)
            self._pending_action = int(action)
        except Exception:
            self.errors += 1
            self._pending = None
            self._pending_action = None

    # ── settle ────────────────────────────────────────────────────────────────

    def settle(self, observed_states: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        pending, action = self._pending, self._pending_action
        self._pending, self._pending_action = None, None
        if pending is None or action is None:
            return out
        for slot in pending:
            if slot not in observed_states:
                continue
            committed = pending[slot]
            observed = observed_states[slot]
            try:
                if slot == "BODY":
                    out[slot] = self._settle_body(committed, observed, action)
                elif slot == "WORKSPACE":
                    out[slot] = self._settle_workspace(committed, observed, action)
                elif slot == "REFERENCE":
                    out[slot] = self._settle_reference(committed, observed)
                elif slot == "RESOURCE":
                    out[slot] = self._settle_resource(committed, observed, action)
                else:
                    out[slot] = _no_bet(observed)
            except Exception:
                self.errors += 1
                out[slot] = _no_bet(observed)
        return out

    # ── BODY: per-action vector delta evidence ────────────────────────────────

    def _established(self, evidence: Dict[Any, int]) -> Optional[Any]:
        """Dominant exact delta seen >= min_evidence times (ties: smallest delta)."""
        if not evidence:
            return None
        best = min(sorted(evidence.items()), key=lambda kv: -kv[1])
        if best[1] >= self.min_evidence:
            return best[0]
        return None

    def _settle_body(self, committed: Tuple[int, int], observed: Tuple[int, int],
                     action: int) -> Dict[str, Any]:
        counts = self._body_evidence.setdefault(int(action), {})
        delta = self._established(counts)
        if delta is None:
            result = _no_bet(observed)
        else:
            predicted = (int(committed[0]) + delta[0], int(committed[1]) + delta[1])
            residual = float(abs(predicted[0] - int(observed[0])) +
                             abs(predicted[1] - int(observed[1])))
            result = {"bet": True, "predicted": predicted, "observed": observed,
                      "residual": residual, "from_known_atom": False}
        # ALWAYS learn from the observed transition, after settling.
        seen = (int(observed[0]) - int(committed[0]), int(observed[1]) - int(committed[1]))
        counts[seen] = counts.get(seen, 0) + 1
        return result

    # ── WORKSPACE: bets only through known EFFECT atoms ───────────────────────

    def _settle_workspace(self, committed: np.ndarray, observed: np.ndarray,
                          action: int) -> Dict[str, Any]:
        if self.gamma is None:
            return _no_bet(observed)
        from engines.egocentric.effects import Gamma, apply_effect  # lazy: gamma=None never pays
        records = self.gamma.fabric.query("collective", Gamma.TOPIC)
        for rec in records:
            if str(rec.get("game")) != str(self.game):
                continue
            if int(rec.get("level", -1)) != int(self.level):
                continue
            atom = rec.get("atom") or {}
            if atom.get("kind") != "EFFECT":
                continue
            if int(atom.get("action", -1)) != int(action):
                continue
            predicted = apply_effect(atom, np.asarray(committed))
            if predicted is None:
                continue                                    # context does not match here
            residual = self._grid_residual(predicted, observed)
            return {"bet": True, "predicted": predicted, "observed": observed,
                    "residual": residual, "from_known_atom": True}
        return _no_bet(observed)

    # ── REFERENCE: always bets "unchanged" ────────────────────────────────────

    def _settle_reference(self, committed: np.ndarray, observed: np.ndarray) -> Dict[str, Any]:
        predicted = np.asarray(committed)
        residual = self._grid_residual(predicted, observed)
        return {"bet": True, "predicted": predicted, "observed": observed,
                "residual": residual, "from_known_atom": False}

    # ── RESOURCE: per-action scalar delta evidence ────────────────────────────

    def _settle_resource(self, committed: float, observed: float,
                         action: int) -> Dict[str, Any]:
        counts = self._resource_evidence.setdefault(int(action), {})
        delta = self._established(counts)
        if delta is None:
            result = _no_bet(observed)
        else:
            predicted = float(committed) + float(delta)
            result = {"bet": True, "predicted": predicted, "observed": observed,
                      "residual": abs(predicted - float(observed)),
                      "from_known_atom": False}
        seen = float(observed) - float(committed)
        counts[seen] = counts.get(seen, 0) + 1
        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _grid_residual(predicted: np.ndarray, observed: np.ndarray) -> float:
        p = np.asarray(predicted)
        o = np.asarray(observed)
        if p.shape != o.shape:
            return float(max(p.size, o.size))               # a reshape is maximally loud
        return float((p != o).sum())
