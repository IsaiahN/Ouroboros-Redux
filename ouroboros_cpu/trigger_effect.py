"""TRIGGER-EFFECT molecule (OO-MDP / DOORMAX-style condition-effect) + regression planner (Schema-Networks-
style backward chaining).

The gap this closes: the composer's causal vocabulary was ACTION-indexed ("action A reproduces a colour
transition"), not OVERLAP-conditioned ("stepping on object T transforms the key's property C by delta"). This
module learns the latter from observed (trigger, key_before, key_after) events accumulated ACROSS rollouts
(the adapter resets each rollout, so a within-rollout model would be wiped), classifies each trigger's effect
per property component into a small canonical set {assign, increment, cycle}, and plans a trigger sequence by
regressing from the lock (target) vector back through those effects.

Property vector = molecule_prediction.object_property_vector(grid, cells, bg) = (colour, shape_mask, size).
Components: 0 = colour (categorical), 1 = shape/orientation (categorical), 2 = size (numeric).
"""

import numpy as np
from collections import defaultdict

CATEGORICAL = (0, 1)        # colour, shape: assign / cycle
NUMERIC = (2,)              # size: assign / increment


def _sig(vec):
    """Hashable trigger signature from a property vector (colour, shape_mask, size)."""
    try:
        return (vec[0], vec[1], int(vec[2]))
    except Exception:
        return None


class TriggerEffectModel:
    """Accumulates overlap(self,trigger) -> key-transition events and induces, per trigger, a typed effect for
    each property component. Persistent across rollouts and levels (never reset within a game)."""

    def __init__(self):
        # trigger_sig -> component -> list of (before_value, after_value)
        self._obs = defaultdict(lambda: defaultdict(list))
        # trigger_sig -> representative centroid (for navigation back to it)
        self.centroid = {}
        self.n_events = 0

    # ---------------- learning ----------------
    def observe(self, trigger_sig, before_vec, after_vec, trigger_centroid=None):
        """Record one event: while overlapping the trigger, the key's vector went before->after."""
        if trigger_sig is None or before_vec is None or after_vec is None:
            return
        if tuple(before_vec) == tuple(after_vec):
            return                                   # no change -> not an effect event
        for c in (0, 1, 2):
            if before_vec[c] != after_vec[c]:
                self._obs[trigger_sig][c].append((before_vec[c], after_vec[c]))
        if trigger_centroid is not None:
            self.centroid[trigger_sig] = tuple(trigger_centroid)
        self.n_events += 1

    def _classify(self, trigger_sig, c):
        """Induce the typed effect of `trigger_sig` on component `c` from accumulated pairs.
        Returns ('assign', v) | ('increment', d) | ('cycle', ring) | None (no/insufficient/inconsistent)."""
        pairs = self._obs.get(trigger_sig, {}).get(c, [])
        if not pairs:
            return None
        afters = [a for _, a in pairs]
        # ASSIGN: after is always the same constant regardless of before
        if len(set(afters)) == 1:
            return ("assign", afters[0])
        if c in NUMERIC:
            deltas = set()
            ok = True
            for b, a in pairs:
                try:
                    deltas.add(int(a) - int(b))
                except Exception:
                    ok = False; break
            if ok and len(deltas) == 1:
                return ("increment", next(iter(deltas)))
        # CYCLE: before->after is a consistent (deterministic) map; build the ring by chaining
        mapping = {}
        for b, a in pairs:
            if b in mapping and mapping[b] != a:
                return None                          # non-deterministic -> not a clean effect
            mapping[b] = a
        # chain into a ring starting from any node
        start = next(iter(mapping))
        ring = [start]; cur = mapping[start]
        seen = {start}
        while cur in mapping and cur not in seen:
            ring.append(cur); seen.add(cur); cur = mapping[cur]
        if len(ring) >= 2 and mapping.get(ring[-1]) == ring[0]:
            return ("cycle", ring)
        if len(ring) >= 2:
            return ("cycle", ring)                   # open chain still usable as ordered steps
        return None

    def effect_of(self, trigger_sig):
        """Full per-component effect model for a trigger."""
        return {c: self._classify(trigger_sig, c) for c in (0, 1, 2)}

    def known_triggers(self):
        return list(self._obs.keys())

    # ---------------- planning (regression / backward chaining) ----------------
    def _applications_to(self, eff, cur, target):
        """How many applications of effect `eff` take component value `cur` to `target` (None if it can't)."""
        if eff is None or cur == target:
            return 0 if cur == target else None
        kind = eff[0]
        if kind == "assign":
            return 1 if eff[1] == target else None
        if kind == "increment":
            d = eff[1]
            if d == 0:
                return None
            try:
                diff = int(target) - int(cur)
            except Exception:
                return None
            if diff == 0:
                return 0
            if diff % d != 0 or (diff // d) <= 0:
                return None
            return diff // d
        if kind == "cycle":
            ring = eff[1]
            if cur not in ring or target not in ring:
                return None
            i, j = ring.index(cur), ring.index(target)
            return (j - i) % len(ring)
        return None

    def plan(self, key_vec, lock_vec, max_triggers=8):
        """Regress from the lock: for each mismatched component, pick a trigger whose induced effect reaches the
        lock's value, and emit the ordered (trigger_sig, repeat_count, component) steps. Returns [] if any
        mismatched component has no satisfying trigger (caller falls back to greedy/explore)."""
        if key_vec is None or lock_vec is None:
            return []
        plan = []
        triggers = self.known_triggers()
        for c in (0, 1, 2):
            if key_vec[c] == lock_vec[c]:
                continue
            best = None
            for tsig in triggers:
                eff = self._classify(tsig, c)
                n = self._applications_to(eff, key_vec[c], lock_vec[c])
                if n is not None and n >= 1:
                    # prefer fewer applications; tie-break on having a known centroid
                    score = (n, 0 if tsig in self.centroid else 1)
                    if best is None or score < best[0]:
                        best = (score, tsig, n)
            if best is None:
                return []                            # unmodellable component -> no committed plan
            plan.append((best[1], best[2], c))
        plan.sort(key=lambda step: step[1])          # apply categorical assigns before long increments/cycles
        flat = []
        for tsig, n, c in plan:
            flat.extend([(tsig, c)] * min(n, max_triggers))
        return flat[:max_triggers]
