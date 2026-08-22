"""betting.py -- C33 STEP 1: every action carries a bet (record/prereg/PREREG_MARKETPLACE_MERGE.md).

The iced pricing spine's settle machinery, adapted to the fabric. Per action the loop
COMMITS a prediction family (paste + temporal-transform members) at choice time and
SETTLES it against the EXECUTED action's next frame in the result path.

LAWS baked in from commit one (the three paid-for laws of the iced branch):
  * committed != executed -> VOID: nothing is priced (settle attribution -- a
    counterfactual is never scored against a frame it did not produce; the executed
    transition itself is the LOOP's job to record, not this class's);
  * family-best recording: the best member's salience is appended (evidence added,
    never replaced) -- the paste's score is a floor a hallucinating sibling cannot sink;
  * executed-action discipline: one pending bet at a time; a new commit replaces an
    unsettled one.

Settlements land on the fabric's collective "settlements" topic with LINEAGE fields
(agent, game, level, action, members, best + the fabric's own seq, plus the additive
atom-identity pair atom_key/atom_bin naming WHICH known atom bet and how it settled;
null when no atom rode the step) -- rho_deriv needs lineage from birth -- and the
DEBASEMENT field `nontrivial` (n_changed > 0): high
settlement volume with a near-zero non-trivial rate is pricing the board's inertia
(the beat-104 receipt).

IN THIS STEP THE BETS DRIVE NOTHING -- no decision path reads `records` (containment).
Deterministic, no RNG; fabric failures count on `errors`, never raise.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from engines.egocentric import pricing


class BetBook:
    """Per-action bet ledger: commit a prediction family, settle against the executed frame."""

    def __init__(self, fabric: Any, agent_id: str, game: str):
        self.fabric = fabric
        self.agent_id = str(agent_id)
        self.game = str(game)
        self.level = 0                       # settable by the loop (mints carry the level)
        self.records: Dict[int, List[float]] = {}   # action -> family-best scores (in-memory)
        self.pending: Optional[Dict[str, Any]] = None
        self.settled = 0                     # settle() calls that produced an outcome
        self.voided = 0
        self.errors = 0                      # fabric-write failures (counted, never raised)

    # ── commit: one pending bet at a time; a new commit replaces an unsettled one ──

    def commit(self, action: int, before: np.ndarray,
               paste: Optional[np.ndarray], transform: Optional[np.ndarray]) -> None:
        """Stash the pending prediction family for `action` (committed pre-outcome)."""
        self.pending = {
            "action": int(action),
            "before": np.asarray(before).copy(),
            "paste": None if paste is None else np.asarray(paste).copy(),
            "transform": None if transform is None else np.asarray(transform).copy(),
        }

    # ── settle: price the family against the EXECUTED action's next frame ──

    def settle(self, post: Optional[np.ndarray], executed_action: int,
               atom_key: Optional[str] = None,
               atom_bin: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Pop the pending bet and settle it; None if there is no pending or no frame.

        atom_key/atom_bin (additive, null when absent): when this step's bank
        settlement stemmed from a KNOWN atom bet, the caller threads the atom's
        id and the router bin it landed in ("TRANSFERRED", ...) so the fabric
        settlement record carries atom identity — the n=1 metric's linkage.
        """
        pending, self.pending = self.pending, None
        if pending is None or post is None:
            return None
        post = np.asarray(post)
        action = int(pending["action"])
        executed = int(executed_action)
        # LAW: committed != executed -> VOID. Nothing is priced, nothing recorded here
        # (the executed transition is the loop's to record, not this class's job).
        if action != executed:
            self.voided += 1
            self.settled += 1
            return {"void": True, "action": action, "executed": executed}
        before = pending["before"]
        members = [m for m in (pending["paste"], pending["transform"]) if m is not None]
        if not members:
            self.settled += 1
            return {"void": True, "action": action, "executed": executed}
        # Family-best: max member salience -- the paste's score is the floor.
        # The API frame is a stack of animation grids ((k, 64, 64) after
        # _to_numpy) and k VARIES between commit and settle; a post frame the
        # family cannot even be compared against (broadcast failure) prices
        # nothing: VOID -- the settle-attribution law, never a raise (this
        # escaped as the live [SWALLOW] BANK_SETTLE storm, 33x/episode).
        try:
            scores = [float(pricing.informative_salience(before, m, post))
                      for m in members]
        except ValueError:
            self.voided += 1
            self.settled += 1
            return {"void": True, "action": action, "executed": executed}
        best = max(scores)
        self.records.setdefault(action, []).append(best)
        # DEBASEMENT field: did the executed action change anything at all?
        nontrivial = bool((post != before).any())
        self.settled += 1
        out = {
            "void": False,
            "action": action,
            "members": len(members),
            "best": best,
            "nontrivial": nontrivial,
            "atom_key": atom_key,
        }
        # One compact fabric line per settle (the ledger the replay test needs).
        try:
            self.fabric.append("collective", "settlements", {
                "agent": self.agent_id,
                "game": self.game,
                "level": int(self.level),
                "action": action,
                "members": len(members),
                "best": best,
                "nontrivial": nontrivial,
                "atom_key": atom_key,     # WHICH atom the bank's bet rode (null: none)
                "atom_bin": atom_bin,     # how that atom bet settled (e.g. TRANSFERRED)
            })
        except Exception:
            self.errors += 1
        return out
