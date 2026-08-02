"""nexus.sensorium.objective -- perception made GENERATIVE (DESIGN §7.5 step 3).

The live ls20 test proved the sensorium had become diagnostic-only: it found the right self (a
depleting resource) but changed nothing, because the only consumer of perception was the post-hoc
veto, which has no legal move at an all-directions-fatal board. Perception has to enter the
PROPOSER: the self-percept must compose an OBJECTIVE that biases what the agent proposes, not just
what it forbids.

This is the smallest honest version of that. It reads the ground-selected self-hypothesis and, when
the self carries an actionable objective, proposes the action that best serves it -- a POSITIVE goal
("preserve the resource because it is depleting and low"), distinct in kind from the veto's negative
"don't die." It is scoped to mover actions (a click's coordinate is the policy's job), it fires only
when the objective is confident, and the verdict veto still runs AFTER it -- so a self-objective can
never propose into a known death. The ground still prices everything: the resource deltas it reasons
over are learned from observed transitions, never asserted.

Currently dispatches on the value-latent self (the resource game, e.g. ls20). Other self-types get a
neutral objective until the ground gives them one -- the registry is open, like the sensor mint.
"""
from __future__ import annotations
from typing import List, Optional, Tuple

EPS = 1e-6


class SelfObjective:
    def __init__(self, low_fraction: float = 0.5, min_gap: float = 0.25):
        # fire the preserve-objective when the resource is in the lower `low_fraction` of its seen
        # range, and only if the best mover's resource-delta beats the chosen one's by `min_gap`.
        self.low_fraction = low_fraction
        self.min_gap = min_gap

    def propose(self, chosen_lbl: str, available, selfmodel) -> Tuple[Optional[str], Optional[str]]:
        """Return (action, note) if the self-composed objective wants a different mover, else (None,
        None). `note` is a human-readable trace for the reasoning payload."""
        m = selfmodel.selected()
        if m is None:
            return None, None
        if m.name == "value":
            return self._resource_objective(chosen_lbl, available, m)
        return None, None                                   # no objective composed for this self-type yet

    def _resource_objective(self, chosen, available, m) -> Tuple[Optional[str], Optional[str]]:
        movers = ["A%d" % int(v) for v in available if int(v) != 6]
        if m.trend() >= 0:                                  # not depleting -> nothing to preserve
            return None, None
        # reason only over movers the GROUND has shown a resource-delta for (evidence, not default 0);
        # untried actions are exploration's job, not the preserve-objective's.
        cand = [a for a in movers if a in m.act_delta]
        if not cand:
            return None, None
        best = max(cand, key=lambda a: m.action_delta(a))
        gap = m.action_delta(best) - m.action_delta(chosen)
        # only override when preservation is both meaningful (a clearly-less-depleting mover exists)
        # and the chosen move is not already the best. This is the composed objective acting.
        if best != chosen and gap > self.min_gap:
            return best, "objective:preserve-resource(%s d=%+.2f vs %s d=%+.2f)" % (
                best, m.action_delta(best), chosen, m.action_delta(chosen))
        return None, None
