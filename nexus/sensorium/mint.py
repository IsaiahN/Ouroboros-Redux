"""nexus.sensorium.mint -- the proposer mints SENSORS, not just actions (Stage 3 of the plan).

The economy of ideas, one level down: sensors compete in the same market as hypotheses, currency
still prediction-error. When the agent is surprised in a way its existing senses cannot describe --
here, when the current signature fails to separate boards that KILL from boards that SURVIVE -- it
mints a new sensor: it chooses which of its candidate perceptual channels actually carry the danger,
and drops the rest. A channel that never reduces the confusion between fatal and survived biodegrades
(the membrane rule); the ones that separate are kept. Nothing is asserted; the GROUND (via the
fatal/survived labels the circuit already produces) prices every channel.

This is what closes FINDINGS_the_generalization_the_ground_refused for real: `local_signature` was a
FIXED colours+available guess. Here the signature's channels are SELECTED by how well they separate
death from survival on this game -- minted, typed, open, ground-priced. Over-inclusion is safe (extra
channels only make the signature finer, and the circuit's counterexample relaxes an over-fine fatal);
the mint's job is to make it GENERAL by keeping only the channels that matter, so a fatal learned on
one board vetoes a globally-different board that shares the danger-bearing features.
"""
from __future__ import annotations
import math
from collections import defaultdict
from typing import Dict, List, Tuple


def _entropy(pos: int, neg: int) -> float:
    n = pos + neg
    if n == 0:
        return 0.0
    p = pos / n
    if p in (0.0, 1.0):
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


class SensorMint:
    """Accumulates (channel-value -> fatal?/survived?) evidence per channel and reports which channels
    separate the two -- the minted sensor. Parameter-light: a channel is 'active' once it has seen
    enough labelled outcomes AND its values are informative about death (positive information gain)."""

    def __init__(self, min_evidence: int = 6, min_gain: float = 0.02, all_channels: Tuple[str, ...] =
                 ("AVAILABLE", "SELF_LOCAL", "SELF_SHAPE", "GLOBAL_COL")):
        self.min_evidence = min_evidence
        self.min_gain = min_gain
        self.all_channels = all_channels
        # channel -> value -> [n_fatal, n_survived]
        self._tab: Dict[str, Dict[object, List[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        self._n = 0

    def observe(self, action: str, features: Dict[str, object], fatal: bool) -> None:
        """One grounded outcome: the before-state's channel values, labelled by whether it ended fatally.
        Action is folded into the value so a channel separates PER the action that was taken."""
        self._n += 1
        idx = 0 if fatal else 1
        for ch, val in features.items():
            self._tab[ch][(action, _hashable(val))][idx] += 1

    def information_gain(self, channel: str) -> float:
        """How much knowing this channel's value reduces uncertainty about death (mutual information,
        in bits). The ground's verdict on whether this sensor is worth having."""
        table = self._tab.get(channel)
        if not table:
            return 0.0
        tot_pos = sum(v[0] for v in table.values()); tot_neg = sum(v[1] for v in table.values())
        n = tot_pos + tot_neg
        if n < self.min_evidence:
            return 0.0
        h_prior = _entropy(tot_pos, tot_neg)
        h_cond = 0.0
        for (pos, neg) in table.values():
            w = (pos + neg) / n
            h_cond += w * _entropy(pos, neg)
        return max(0.0, h_prior - h_cond)

    def active_channels(self) -> Tuple[str, ...]:
        """The minted sensor: the channels whose information gain about death clears the bar, ordered
        by gain. Empty until enough grounded evidence accrues -- the Sensorium then uses its full
        self-relative read, and this SHARPENS it as the ground speaks. AVAILABLE is always kept (the
        affordance set is the cheapest, most invariant channel)."""
        scored = [(ch, self.information_gain(ch)) for ch in self.all_channels]
        keep = [ch for ch, g in sorted(scored, key=lambda kv: -kv[1]) if g >= self.min_gain]
        if "AVAILABLE" not in keep:
            keep = ["AVAILABLE"] + keep
        return tuple(keep) if len(keep) > 1 else ()      # <2 informative channels -> not yet minted

    def report(self) -> Dict[str, float]:
        return {ch: round(self.information_gain(ch), 4) for ch in self.all_channels}


def _hashable(val):
    try:
        hash(val); return val
    except Exception:
        return str(val)
