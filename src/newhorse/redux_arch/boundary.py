"""
boundary.py -- the loci-based BOUNDARY DIFF (Tether §3.5). At a level boundary the environment is partitioned by
TRACKED IDENTITY (from LociTracker), not by colour histogram:

  * TRANSFERRED -- a locus id that PERSISTED across the redraw ⇒ the part of the map that survived the transform.
  * NOVEL       -- a FRESH id with no prior referent ⇒ extend perception / direct empowerment HERE first (§4.4).
  * GONE        -- an id present before, absent after.

The action-set delta rides along because a GROWN control set (2→4→8) is the canonical broken-by-REBINDING case
(re-fit the bindings, do NOT mint) -- distinguishable from broken-by-MECHANISM, which owes a mint. Unresolved
residual goes to QUARANTINE under a DECAY bound: "PARK must decay, or quarantine becomes an unpurged store."

Domain-general by construction: it names no game, only "what identity persisted / what is new".
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class BoundaryDiff:
    level: int
    transferred: List[int]
    novel: List[int]
    gone: List[int]
    new_colours: List[int]
    gone_colours: List[int]
    new_actions: List[int]
    gone_actions: List[int]

    @property
    def rebinding(self) -> bool:
        """A changed/grown control set is the canonical broken-by-rebinding signal: re-fit params, do not mint."""
        return bool(self.new_actions or self.gone_actions)

    def summary(self) -> Dict[str, Any]:
        return dict(level=self.level, transferred=self.transferred, novel=self.novel, gone=self.gone,
                    new_colours=self.new_colours, gone_colours=self.gone_colours,
                    new_actions=self.new_actions, gone_actions=self.gone_actions, rebinding=self.rebinding)


def diff_identities(prev_ids, after_loci) -> Tuple[List[int], List[int], List[int]]:
    """Partition ids by persistence across a boundary. `after_loci` = tracker.loci() on the redraw frame."""
    after_ids = [l.id for l in after_loci]
    aset = set(after_ids)
    prev = set(prev_ids)
    transferred = [i for i in after_ids if i in prev]
    novel = [i for i in after_ids if i not in prev]
    gone = sorted(i for i in prev if i not in aset)
    return transferred, novel, gone


class Quarantine:
    """PARK unresolved boundary residuals under a decay bound. Each item carries a wake BUDGET decremented every
    boundary (`tick`); what fails to become explicable within it is discarded -- dormancy is not free. `wake(key)`
    retrieves + removes (it became explicable); `park` (re-)banks with a fresh budget (ACCUMULATE)."""

    def __init__(self) -> None:
        self._parked: Dict[str, Dict[str, Any]] = {}

    def park(self, key: str, payload: Any, budget: int = 3) -> None:
        self._parked[key] = dict(payload=payload, budget=int(budget))

    def tick(self) -> List[str]:
        """Decay every parked item by one boundary; drop and return the keys that expired."""
        expired = []
        for k in list(self._parked):
            self._parked[k]["budget"] -= 1
            if self._parked[k]["budget"] <= 0:
                del self._parked[k]
                expired.append(k)
        return expired

    def wake(self, key: str) -> Optional[Any]:
        item = self._parked.pop(key, None)
        return item["payload"] if item else None

    def live(self) -> Dict[str, Any]:
        return {k: v["payload"] for k, v in self._parked.items()}
