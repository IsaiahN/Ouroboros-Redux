"""W4b: the mute verdict -- quarantine + the empowerment probe.

Confirm -> mint + seed. Refute -> veto. MUTE -- the ground said nothing -- quarantines
the item and answers with a DISCRIMINATING PROBE: the least-observed candidate cell,
the observation that would make the ground speak. Deterministic, stdlib only.
"""
from __future__ import annotations


class MuteHandler:
    """Quarantine for items the ground could not settle, plus the empowerment probe."""

    def __init__(self) -> None:
        self.quarantine: list = []
        self.errors: int = 0

    def mute(self, item, candidates, observed_counts):
        """Quarantine ``item``; return {"probe": cell|None}.

        The probe is the LEAST-observed candidate (missing counts = 0), ties broken
        by sorted order so the choice is deterministic. Empty candidates -> None.
        """
        self.quarantine.append(item)
        probe = None
        try:
            if candidates:
                counts = observed_counts or {}
                probe = min(sorted(candidates), key=lambda c: counts.get(c, 0))
        except Exception:
            self.errors += 1
            probe = None
        return {"probe": probe}

    def release(self, item_id):
        """Remove and return the quarantined item whose .get("id") == item_id, else None."""
        try:
            for i, item in enumerate(self.quarantine):
                if isinstance(item, dict) and item.get("id") == item_id:
                    return self.quarantine.pop(i)
        except Exception:
            self.errors += 1
        return None
