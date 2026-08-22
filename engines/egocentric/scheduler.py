"""scheduler.py -- W2b: THE PLANNER AS LAST RESORT (PREREG_W2B_PLANNER_SCHEDULING.md).

Seat 3: "The planner should engage when the cheap routes have failed to produce
a good option, not on every cycle where atoms happen to exist. An index makes
an expensive search cheaper; it does not decide when the search is worth
running." The F2 addendum measured the leak three times: engagement scaled
with freed capacity (5 -> 10 -> 17 calls across three profiling windows) and
reabsorbed every per-call speedup. This module is the decision of WHEN, kept
separate from the index (which is the decision of HOW CHEAPLY).

TWO GATES, ONE GUARD, ONE ROUTER:

  GATE A (cheap routes first): the planner engages only when no CANDIDATE-
      PRODUCING cheap route (mapped = a causal-map plan step, reasoned = a
      rung's decision) produced a candidate at or above CHEAP_ROUTE_CONF_BAR
      this cycle. Explore/random speeds ARE the cheap routes having failed --
      the loop seam passes conf=None for them, and None never closes the
      gate. The bar mirrors the loop's existing 0.5 exploit/certainty bar
      (_derive_strategy's "felt.certainty > 0.5" and the lesson-confidence
      cut) -- named here as a module constant because no prior named constant
      existed for it.
  GATE B (no re-search of an unchanged world): the (state key, change mark) of
      the last planner attempt is retained per (game, level). The change mark
      is (mints passed, imports seeded, RE-ENTRIES); an identical key with an
      identical mark means nothing was minted, imported or re-admitted since
      -- the search would return the same nothing, so it is SKIPPED, and the
      skip is NARRATED at the PLAN point with its reason (falsifier F3), never
      silent. The third component is R3/R4's (PREREG_STANDING_HALF_LIFE_
      ATOMS.md): a RE-ENTRY grew the candidate set, so the world changed for
      the search's purposes. An EVICTION shrank it and needs no reopening --
      the same nothing would come back with one fewer atom asked.
  STARVATION GUARD (absolute, falsifier F2): a cycle where every cheap route
      failed MUST reach the planner in that same cycle. Provable by
      construction in decide(): with conf below the bar, the ONLY remaining
      skip is a retained identical attempt -- and a fresh (game, level, key)
      has none, so both gates are OPEN. Deferral within a cycle may never
      become denial across cycles: any key change, mint, import, level change
      or fission reopens GATE B.
  THE ABORT ROUTER (the shadow test's Interruption rider, falsifier F4): a
      driven plan that aborts mid-execution is ROUTED, never conflated --
      WORLD-MOVED (the state key changed under the plan: re-plan, no penalty
      to the plan's atoms; the retained key is dropped so GATE B cannot block
      the re-plan) vs PLAN-WRONG (state as predicted, the step failed:
      recorded against the plan's atoms in plan_wrong). Both narrated with
      their discriminator.

The state key is the planner's own (planner._state_key) so the scheduler and
the search agree byte-for-byte on what "the same state" means.

UNDO: remove the two gate conditions at the loop seams; the planner reverts to
engage-on-atoms.

Falsifiers: tests/gate/test_planner_scheduling.py (F2 / F3 / F4 / R4). F1 (the
leak stops in a live window) is the proctor's profile read, not asserted here.

Containment (house law): pure state + dict returns; nothing here raises into
the host loop -- the loop-side seam additionally fails OPEN (engage) so a
scheduler error can never starve the planner.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from engines.egocentric import retention as _ret
from engines.egocentric import standing as _standing
from engines.egocentric.planner import _state_key

# GATE A's bar (KNOBS G25, Register G, provenance GUESSED -- mirrors the
# loop's existing 0.5 exploit-certainty bar; no named constant existed).
# A cheap-route candidate AT or ABOVE the bar holds the wheel: no search.
CHEAP_ROUTE_CONF_BAR = 0.5

# fixed reason tokens (narrated verbatim -- never free prose)
SKIP_CHEAP_ROUTE = "cheap-route-held"      # GATE A: a confident cheap candidate exists
SKIP_UNCHANGED = "unchanged-world"         # GATE B: same key, nothing minted/imported
ENGAGE_FIRST = "first-attempt-on-state"    # no retained attempt for (game, level)
ENGAGE_CHANGED = "world-changed"           # key moved, or a mint/import landed

# the abort router's two destinations (the discriminator's fixed tokens)
ABORT_WORLD_MOVED = "world-moved"
ABORT_PLAN_WRONG = "plan-wrong"


def state_key(state: Any) -> str:
    """The planner's OWN state key over a workspace frame -- one hash function
    for scheduler and search, so GATE B's "unchanged" is exactly the state the
    planner would re-search."""
    return _state_key(np.asarray(state))


def route_abort(planned_key: Optional[str], observed_key: Optional[str]
                ) -> Dict[str, str]:
    """THE DISCRIMINATOR (pure): route a driven plan's mid-execution abort.

    WORLD-MOVED: the observed state key differs from the key the plan was made
    against -- the world changed under the plan. Re-plan; the plan's atoms are
    NOT penalised (they were never given the state they bet on).
    PLAN-WRONG: the state is exactly as predicted and the step still failed --
    the plan itself is wrong, and that is recorded against it."""
    if str(observed_key) != str(planned_key):
        return {"route": ABORT_WORLD_MOVED,
                "fact": "state key changed under the plan; re-plan, no penalty"}
    return {"route": ABORT_PLAN_WRONG,
            "fact": "state as predicted and the step failed; recorded against the plan"}


class PlannerScheduler:
    """W2b: per-loop scheduling state. Retains the last planner attempt's
    (state key, change mark) per (game, level) for GATE B, counts engagements
    and skips (readout only), and holds the plan-wrong ledger the abort router
    records against. Level change or fission clears the retained keys
    (binder.on_level_change's pattern: the board redraws, the key re-earns).
    W2c (PREREG_W2C_PLANNER_RETENTION.md): OWNS the retention store
    (`retained`, a retention.RetentionStore) the planner and the composer
    receive at the loop's call sites; it is cleared INSIDE the same two
    clears -- one clear site per event, none to forget."""

    def __init__(self) -> None:
        # (game, level) -> (state_key, change_mark) of the LAST planner attempt
        self._last: Dict[Tuple[str, int], Tuple[str, Tuple[int, ...]]] = {}
        self.engages = 0
        self.skips = 0
        # the abort router's record against the plan: atom id -> failed-step count
        self.plan_wrong: Dict[str, int] = {}
        self.aborts_routed = 0
        self.errors = 0
        # W2c: the level-scoped store of what the planner/composer learned
        self.retained = _ret.RetentionStore()
        # R3/R4 (PREREG_STANDING_HALF_LIFE_ATOMS.md): the standing book the
        # planner ranks by and the eviction sweep writes through. DELIBERATELY
        # NOT cleared by on_level_change: retention describes a board that
        # redrew, standing describes an atom's history against the ground, and
        # the board redrawing does not unmake it. The level scope lives in tau,
        # recomputed per (game, level) at every engagement.
        self.standing = _standing.StandingBook()

    # -- the two gates + the starvation guard ---------------------------------

    def decide(self, game: str, level: int, key: str,
               conf: Optional[float],
               change_mark: Tuple[int, ...]) -> Dict[str, Any]:
        """The ONE engagement decision. Returns {"engage": bool, "reason": str}.

        STARVATION GUARD, provable by construction: when conf is below the bar
        (every cheap route failed) the only remaining condition is GATE B, and
        GATE B can only close on a RETAINED identical attempt -- a fresh
        (game, level, key) or any mint/import since always engages, in that
        same cycle. The gates defer within a cycle, never deny across cycles."""
        # GATE A -- cheap routes first: a confident candidate holds the wheel.
        if conf is not None and float(conf) >= CHEAP_ROUTE_CONF_BAR:
            self.skips += 1
            return {"engage": False, "reason": SKIP_CHEAP_ROUTE}
        # GATE B -- no re-search of an unchanged world.
        prev = self._last.get((str(game), int(level)))
        if prev is not None and prev == (str(key), tuple(change_mark)):
            self.skips += 1
            return {"engage": False, "reason": SKIP_UNCHANGED}
        self.engages += 1
        return {"engage": True,
                "reason": ENGAGE_FIRST if prev is None else ENGAGE_CHANGED}

    def note_attempt(self, game: str, level: int, key: str,
                     change_mark: Tuple[int, ...]) -> None:
        """Retain THIS attempt's (key, mark) -- recorded at engagement, so an
        identical world with nothing minted/imported since is not re-searched."""
        try:
            self._last[(str(game), int(level))] = (str(key), tuple(change_mark))
        except Exception:
            self.errors += 1

    # -- the abort router's state side ----------------------------------------

    def on_abort(self, route: str, game: str, level: int,
                 steps: Optional[List[str]] = None) -> None:
        """Apply a routed abort. WORLD-MOVED drops the retained key so GATE B
        cannot block the re-plan (and penalises nothing). PLAN-WRONG records
        the failure against every step atom of the plan (the eviction gap's
        future evidence -- a ledger, deliberately not yet a demotion)."""
        try:
            self.aborts_routed += 1
            if route == ABORT_WORLD_MOVED:
                self._last.pop((str(game), int(level)), None)
                return
            for sid in steps or []:
                self.plan_wrong[str(sid)] = self.plan_wrong.get(str(sid), 0) + 1
        except Exception:
            self.errors += 1

    # -- clears (binder.on_level_change's pattern) ----------------------------

    def on_level_change(self) -> None:
        """The board redraws; every retained attempt key must re-earn itself.
        W2c: the retention store clears HERE too -- the mark cannot outlive
        the world it describes (F2)."""
        try:
            self._last.clear()
        except Exception:
            self.errors += 1
        try:
            self.retained.clear()
        except Exception:
            self.errors += 1

    def on_fission(self, object_class: Optional[str] = None) -> None:
        """A class fissioned (bank.ClassFissionSocket): the world model under
        the retained keys is stale -- same clear as a level change."""
        self.on_level_change()
