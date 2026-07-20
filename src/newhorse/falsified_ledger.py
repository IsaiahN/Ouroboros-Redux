"""
falsified_ledger.py -- THE MAP SS9.4 item 4: "Falsified ledger = CRISPR spacers -- a weighted
memory of what to REJECT, so trials aren't re-spent on dead ideas."

This is the component Redux structurally cannot hold: its hypothesis ledger has only
{provisional, confirmed} and promotes ONLY by a win, so a falsified hypothesis is re-tried cold
every episode. Here the reject-memory is first-class.

Design principles, each traceable to the map / the cognitive standard:

  * EXPRESS-BEFORE-JUDGE (SS9.4.1; CRISPR-Cas transcribes foreign DNA before interference acts):
    a refutation is recorded ONLY after the hypothesis actually RAN a trial and the do-operator
    registered. A blocked / no-op / never-reached attempt is a NON-TRIAL, not a refutation --
    THE GATEKEEPER's Effectiveness gate: "I failed to do X" must never be coded as "X is inert."

  * WEIGHTED, not binary (SS9.4.4): repeated failures accumulate weight; the ledger holds a
    strength-of-rejection, so the consumer can DE-PRIORITISE (soft), never hard-ban.

  * DEFEASIBLE (cognitive standard -- a refutation is retractable, never absolute), two ways:
      - DECAY over a logical clock (attempts/generations, "the man dies, the lineage learns"):
        old rejections fade so the ledger never ossifies.
      - FITNESS-CONDITIONAL GATE-DROP (SS9.4.5: "under decisive selection pressure CRISPR is LOST
        to permit beneficial HGT"): decisive new surprise REOPENS a refuted hypothesis.

  * NEVER ENCODE THE ANSWER (hard bound): the ledger only ever records what the AGENT ITSELF
    tried and found unrewarded. It contains no "right answer", only the agent's own dead ends.

  * NOTHING HAPPENS SILENTLY (hard bound): explain() narrates every rejection with its reason.

The clock is LOGICAL (an integer attempt/generation index the caller advances), not wall-clock:
deterministic, testable, and faithful to the map's generational accounting. No wall-clock is read.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
import math


@dataclass
class _Entry:
    weight: float          # accumulated rejection strength at `last`
    last: int              # logical time (attempt index) of the most recent refutation
    first: int             # when it was first refuted
    trials: int            # how many recorded failed trials


class FalsifiedLedger:
    """A weighted, defeasible memory of hypotheses the agent tried and found unrewarded.

    `store` may be an external dict (e.g. a persistent knowledge blob) so the ledger survives
    across episodes -- the whole point. Pass the SAME dict back to persist; omit for a fresh one.
    """

    def __init__(self, store: Optional[dict] = None, *, half_life: float = 8.0,
                 reopen_surprise: float = 1.0, refuted_threshold: float = 1.0):
        if half_life <= 0:
            raise ValueError("half_life must be > 0")
        self.half_life = float(half_life)          # attempts over which a rejection halves
        self.reopen_surprise = float(reopen_surprise)  # surprise that fully reopens a dead idea
        self.refuted_threshold = float(refuted_threshold)  # decayed weight above which is_refuted() is True
        self._store: Dict[str, _Entry] = {}
        if store is not None:
            self.bind(store)

    # ---- persistence -------------------------------------------------------------------
    def bind(self, store: dict) -> "FalsifiedLedger":
        """Adopt an external dict as backing store (load its contents). Survives across episodes."""
        self._store = {}
        for k, v in (store.get("entries", {}) or {}).items():
            self._store[k] = _Entry(**v)
        self._ext = store
        store.setdefault("entries", {})
        return self

    def _flush(self):
        ext = getattr(self, "_ext", None)
        if ext is not None:
            ext["entries"] = {k: vars(e).copy() for k, e in self._store.items()}

    def snapshot(self) -> dict:
        return {"entries": {k: vars(e).copy() for k, e in self._store.items()}}

    # ---- the decayed weight (defeasible: rejections fade over the logical clock) --------
    def weight(self, key: str, now: int) -> float:
        """Current rejection strength for `key`, decayed to logical time `now`. 0.0 if unknown."""
        e = self._store.get(key)
        if e is None:
            return 0.0
        dt = max(0, now - e.last)
        return e.weight * (0.5 ** (dt / self.half_life))

    def is_refuted(self, key: str, now: int) -> bool:
        return self.weight(key, now) >= self.refuted_threshold

    def bias(self, key: str, now: int) -> float:
        """A bounded de-prioritisation in [0, 1) for a ranker to SUBTRACT -- soft, never a ban.
        0 = untouched; ->1 = strongly, but not infinitely, deprioritised. The agent can still
        re-try it if everything else is exhausted (defeasibility; never encode the answer)."""
        w = self.weight(key, now)
        return 1.0 - math.exp(-w)

    # ---- recording (express-before-judge + effectiveness gate) -------------------------
    def record(self, key: str, *, trial_ran: bool, made_progress: bool,
               now: int, weight: float = 1.0) -> str:
        """Record the OUTCOME of a hypothesis the agent committed to this attempt.

        trial_ran      : did the do-operator actually REGISTER (moved / contacted / executed)?
                         If False -> NON-TRIAL (blocked/no-op/never-reached): recorded as nothing.
        made_progress  : did it register reward / reduce the objective residual?
                         If True -> the idea is NOT dead: its rejection is CLEARED (it did something).
        Returns one of: 'non_trial', 'progress_cleared', 'refuted'.
        """
        if not trial_ran:
            return "non_trial"                     # Effectiveness gate: a failure to act is not evidence of inertness
        if made_progress:
            if key in self._store:                 # it worked -> it is not a dead idea; drop the reject
                del self._store[key]; self._flush()
            return "progress_cleared"
        # a real, registered, unrewarded trial -> accumulate rejection weight (on top of the decayed prior)
        prior = self.weight(key, now)
        e = self._store.get(key)
        if e is None:
            self._store[key] = _Entry(weight=weight, last=now, first=now, trials=1)
        else:
            e.weight = prior + weight; e.last = now; e.trials += 1
        self._flush()
        return "refuted"

    # ---- defeasibility: decisive new evidence reopens a dead idea (fitness-conditional gate-drop)
    def reconsider(self, key: str, *, surprise: float, now: int) -> bool:
        """Decisive new surprise/fitness REOPENS a refuted hypothesis (SS9.4.5). Returns True if it
        was reopened (weight reduced/cleared). surprise>=reopen_surprise clears it fully; partial
        surprise partially forgives it."""
        e = self._store.get(key)
        if e is None or surprise <= 0:
            return False
        frac = min(1.0, surprise / self.reopen_surprise)
        cur = self.weight(key, now)
        neww = cur * (1.0 - frac)
        if neww < 1e-9:
            del self._store[key]
        else:
            e.weight = neww; e.last = now
        self._flush()
        return True

    # ---- narration (nothing happens silently) ------------------------------------------
    def explain(self, key: str, now: int) -> str:
        e = self._store.get(key)
        if e is None:
            return "FALSIFIED-LEDGER  '%s' -- no record; not a known dead idea." % key
        return ("FALSIFIED-LEDGER  '%s' committed-and-unrewarded %d time(s) (first@%d, last@%d) -> "
                "reject weight %.2f now (bias %.2f); DE-PRIORITISE, not banned -- decisive new "
                "surprise reopens it." % (key, e.trials, e.first, e.last, self.weight(key, now),
                                          self.bias(key, now)))

    def keys(self):
        return list(self._store.keys())

    def __len__(self):
        return len(self._store)
