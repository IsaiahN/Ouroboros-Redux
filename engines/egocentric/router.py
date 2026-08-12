"""W2b: the residual router -- every settled residual lands in exactly one of four bins.

TRANSFERRED confirms; NOVEL extends perception (the import queue); BROKEN·rebinding re-fits
the binder; BROKEN·mechanism owes the mint one atom. The router is the loop's boundary diff:
where to look, decided by what kind of surprise arrived.

Deterministic, stdlib only.
"""
from __future__ import annotations

TRANSFERRED = "TRANSFERRED"
NOVEL = "NOVEL"
BROKEN_REBINDING = "BROKEN_REBINDING"
BROKEN_MECHANISM = "BROKEN_MECHANISM"

_BINS = (TRANSFERRED, NOVEL, BROKEN_REBINDING, BROKEN_MECHANISM)


class ResidualRouter:
    """Route a settled bet's residual into exactly one of four bins.

    Precedence (first match wins):
      1. no bet            -> None (nothing was staked; nothing to learn)
      2. residual <= eps   -> TRANSFERRED (the prediction held)
      3. binding stale     -> BROKEN_REBINDING (re-fit the binder)  [refit_queue]
      4. from a known atom -> BROKEN_MECHANISM (the mint owes an atom)  [mint_queue]
      5. otherwise         -> NOVEL (extend perception)  [import_queue]
    """

    def __init__(self, eps: float = 1e-9):
        self.eps = float(eps)
        self.import_queue: list[dict] = []   # NOVEL -- the endogenous build agenda
        self.refit_queue: list[dict] = []    # BROKEN_REBINDING -- binder re-fits owed
        self.mint_queue: list[dict] = []     # BROKEN_MECHANISM -- atoms owed to the mint
        self.routed: dict[str, int] = {b: 0 for b in _BINS}
        self.errors: int = 0

    def route(self, slot: str, settlement: dict) -> str | None:
        """Route one settlement; return its bin, or None when no bet was staked."""
        try:
            bet = bool(settlement.get("bet", False))
            if not bet:
                return None
            residual = float(settlement.get("residual", 0.0))
            binding_stale = bool(settlement.get("binding_stale", False))
            from_known_atom = bool(settlement.get("from_known_atom", False))
        except (TypeError, ValueError, AttributeError):
            self.errors += 1
            return None

        if residual <= self.eps:
            self.routed[TRANSFERRED] += 1
            return TRANSFERRED

        item = dict(settlement)
        item["slot"] = slot
        item["residual"] = residual

        if binding_stale:
            self.refit_queue.append(item)
            self.routed[BROKEN_REBINDING] += 1
            return BROKEN_REBINDING
        if from_known_atom:
            self.mint_queue.append(item)
            self.routed[BROKEN_MECHANISM] += 1
            return BROKEN_MECHANISM
        self.import_queue.append(item)
        self.routed[NOVEL] += 1
        return NOVEL

    def import_queue_ranked(self) -> list[dict]:
        """The import queue by unexplained residual, biggest debt first (stable)."""
        return sorted(self.import_queue, key=lambda i: -float(i.get("residual", 0.0)))
