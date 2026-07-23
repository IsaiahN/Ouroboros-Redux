"""
affordance.py -- Tier-1 AFFORDANCE from the transition residual (Tether §4.4 Lane A). Games whose actions are
non-translation (paint / toggle / place / undo) route UNDRIVABLE because no cursor moves -- yet their actions DO
things. The transition residual R_τ is exactly where the (translation-)model mispredicts, i.e. where an action had
an EFFECT. The minimal general affordance read from it: which actions are EFFECTIVE (change the board), which are
NO-OPs, and which is an UNDO (reverts the previous change). With that, the agent acts PURPOSEFULLY -- press effective
buttons, avoid the no-ops and the undo -- instead of cycling blindly.

Domain-general: it names no game; "effective" is just "this action changed the board", learned live. This unlocks
sb26 (ACTION5 toggles), g50t (2/4/5 effective), tr87/lf52 (all effective) without any per-game code.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class EffectAffordance:
    """Running per-action effect model, updated live from each transition (before, action, after)."""
    _mag: Dict[str, List[int]] = field(default_factory=dict)     # action -> cells-changed per observation
    _undo: Dict[str, int] = field(default_factory=dict)          # action -> times it reverted the previous change
    n_obs: int = 0

    def update(self, prev, action: str, new, two_ago=None, prev_action=None) -> None:
        if action in ("RESET", "?", None):
            return
        p, n = np.asarray(prev), np.asarray(new)
        if p.shape != n.shape:
            return
        ch = int((p != n).sum())
        self._mag.setdefault(action, []).append(ch)
        self.n_obs += 1
        # UNDO = an action that reverts a DIFFERENT action's change (new == two-ago). Same-action reversion is a
        # TOGGLE/oscillation (a 2-cycle), NOT undo -- excluding it wrongly would blind us to the effective button.
        if two_ago is not None and prev_action is not None and prev_action != action:
            t = np.asarray(two_ago)
            if t.shape == n.shape and ch > 0 and np.array_equal(t, n):
                self._undo[action] = self._undo.get(action, 0) + 1

    def effect(self, action: str) -> float:
        v = self._mag.get(action, [])
        return float(np.mean(v)) if v else 0.0

    def effective(self, min_frac: float = 0.5, min_mean: float = 1.0) -> List[str]:
        """Actions that changed the board in >= min_frac of observations with mean effect >= min_mean cells."""
        out = []
        for a, v in self._mag.items():
            if not v:
                continue
            frac = sum(1 for x in v if x > 0) / len(v)
            if frac >= min_frac and float(np.mean(v)) >= min_mean:
                out.append(a)
        return sorted(out, key=lambda a: -self.effect(a))       # strongest effect first

    def undo(self) -> Optional[str]:
        return max(self._undo, key=self._undo.get) if self._undo else None

    def choose(self, labels: List[str], visits: Dict[str, int]) -> str:
        """Pick an action: prefer EFFECTIVE ones (excluding the undo and click A6), least-visited first (curiosity
        within the effective set). Cold start (no effective actions learned yet) -> explore the least-visited
        non-click action to gather effect evidence."""
        undo = self.undo()
        eff = [a for a in self.effective() if a in labels and a != undo and a != "A6"]
        pool = eff if eff else [a for a in labels if a != "A6"] or list(labels)
        if not pool:
            return labels[0] if labels else "A5"
        return min(pool, key=lambda x: visits.get(x, 0))
