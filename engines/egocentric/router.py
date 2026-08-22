"""W2b: the residual router -- every settled residual lands in exactly one of four bins.

TRANSFERRED confirms; NOVEL extends perception (the import queue); BROKEN·rebinding re-fits
the binder; BROKEN·mechanism owes the mint one atom. The router is the loop's boundary diff:
where to look, decided by what kind of surprise arrived.

B9: the router is also where DIVERGENCE becomes visible -- the same action settling
TRANSFERRED in one episode and BROKEN·mechanism in another. A settlement that carries its
frames ("committed", "observed", "action" -- the workspace predictor supplies them) feeds an
attached effects.ConditionalMiner; a constructed EFFECT_IF lands in ``conditional_atoms``
for the caller to read.

Deterministic, stdlib only (the optional miner is caller-supplied, never imported here).
"""
from __future__ import annotations

TRANSFERRED = "TRANSFERRED"
NOVEL = "NOVEL"
BROKEN_REBINDING = "BROKEN_REBINDING"
BROKEN_MECHANISM = "BROKEN_MECHANISM"

_BINS = (TRANSFERRED, NOVEL, BROKEN_REBINDING, BROKEN_MECHANISM)

# W1 FALSIFIER, ARM C (PREREG_W1_NARRATION.md "ARM C's CONSUMPTION MUST BE
# REAL" wire 1): THE AMBIGUOUS BAND around the router's own threshold. The
# discriminating fact between TRANSFERRED and every neighbour bin is
# ``residual <= eps`` (the precedence rule below; eps defaults to 1e-9, a
# float-noise zero). A residual within AMBIGUOUS_BAND of eps sits BELOW the
# board's own resolution: every grid/centroid residual the bank can produce
# is a whole count (changed cells; Manhattan centroid steps -- bank.py), so
# the smallest residual the substrate can testify to is 1.0, and anything in
# (eps, 0.5] is float noise or sub-unit scalar drift the bare rule can only
# coin-toss on. Inside that band -- and ONLY there, and ONLY when the caller
# passes the prior bet's stated expectation (arm C) -- the bet resolves the
# tie. GUESSED (half the substrate's smallest testifiable residual);
# record/canon/KNOBS.md G27, Register G.
AMBIGUOUS_BAND = 0.5


class ResidualRouter:
    """Route a settled bet's residual into exactly one of four bins.

    Precedence (first match wins):
      1. no bet            -> None (nothing was staked; nothing to learn)
      2. residual <= eps   -> TRANSFERRED (the prediction held)
      3. binding stale     -> BROKEN_REBINDING (re-fit the binder)  [refit_queue]
      4. from a known atom -> BROKEN_MECHANISM (the mint owes an atom)  [mint_queue]
      5. otherwise         -> NOVEL (extend perception)  [import_queue]
    """

    def __init__(self, eps: float = 1e-9, miner=None):
        self.eps = float(eps)
        self.miner = miner                   # B9: optional effects.ConditionalMiner
        self.import_queue: list[dict] = []   # NOVEL -- the endogenous build agenda
        self.refit_queue: list[dict] = []    # BROKEN_REBINDING -- binder re-fits owed
        self.mint_queue: list[dict] = []     # BROKEN_MECHANISM -- atoms owed to the mint
        self.conditional_atoms: list[dict] = []   # B9: constructed EFFECT_IF atoms
        self.routed: dict[str, int] = dict.fromkeys(_BINS, 0)
        self.errors: int = 0
        # W1 falsifier arm C: consumption ledger -- times the prior bet's
        # expectation resolved an in-band tie (total + last-call flag). Arm W
        # (expected_bin never passed) leaves both at their zero forever; the
        # gate asserts exactly that.
        self.consumed: int = 0
        self.last_consumed: bool = False

    def route(self, slot: str, settlement: dict,
              expected_bin: str | None = None) -> str | None:
        """Route one settlement; return its bin, or None when no bet was staked.

        ``expected_bin`` (W1 falsifier, ARM C ONLY -- the arm-W caller passes
        nothing and the consumption branch is never entered): the immediately
        prior BET narration record's stated expected bin for this slot. It is
        consulted ONLY when the residual falls inside AMBIGUOUS_BAND of the
        eps threshold -- the discriminating fact's own tie region -- where it
        resolves the TRANSFERRED-vs-neighbour tie the bare rule would decide
        on float noise. Outside the band the bare rule holds regardless."""
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

        self._mine(settlement)               # B9: every frame-carrying bet is divergence food

        self.last_consumed = False
        if (expected_bin is not None
                and abs(residual - self.eps) <= AMBIGUOUS_BAND):
            # ARM C's WIRE 1 decision point: in-band, the consumed bet decides.
            held = expected_bin == TRANSFERRED
            self.consumed += 1
            self.last_consumed = True
        else:
            held = residual <= self.eps      # the bare rule (arm W always)
        if held:
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

    def _mine(self, settlement: dict) -> None:
        """B9: feed the attached miner from a settlement carrying its (pre, action, post)
        frames; a constructed EFFECT_IF lands in ``conditional_atoms``. Never raises --
        mining is a bonus, never a tax on routing."""
        if self.miner is None:
            return
        try:
            pre = settlement.get("committed")
            post = settlement.get("observed")
            action = settlement.get("action")
            if pre is None or post is None or action is None:
                return
            atom = self.miner.feed(pre, action, post)
            if atom is not None:
                self.conditional_atoms.append(atom)
        except Exception:
            self.errors += 1

    def import_queue_ranked(self) -> list[dict]:
        """The import queue by unexplained residual, biggest debt first (stable)."""
        return sorted(self.import_queue, key=lambda i: -float(i.get("residual", 0.0)))
