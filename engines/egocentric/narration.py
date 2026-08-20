"""narration.py -- W1: the narration spine + memory at three ranges (PREREG_W1_NARRATION.md).

NARRATION IS NOT A LOG WRITTEN AFTER A DECISION -- IT IS THE DECISION (Seat 3,
2026-08-20): the loop's step 1 is perceive, BET, act, observe. The bet-side
record (per-slot prediction, ROUTE bin AND why-not-the-neighbour-bin, mint
candidate or which-guard-was-zero, memory-range tag) is emitted BEFORE the
action executes; the outcome-side records (PERCEIVE / ROUTE / MINT / ECHO)
close against the pre-action bet by referencing its record id. Every ACT
record references a BET record with an earlier per-step sequence number --
falsifier F1's precedence check, enforced here by construction: `act()`
refuses to emit when no bet was placed this step.

Six loop points per cycle, plus the BET record that binds them:
  PERCEIVE  prediction vs outcome, PER SLOT -- never aggregated
  ROUTE     which of the four bins, and why not the neighbour bin
  MINT      the candidate offered; if none, which guard was the zero;
            both sides of the MDL bargain
  ECHO      what settled, or *candidate* stated as such
  PLAN      drove / shadowed / no-steps, with the g-gate that stopped it
  ACT       the chosen action and the rung that won the wheel

Stream: one JSONL record per event on the PERSONAL "narration" topic (the same
append mechanism as the other personal streams -- starvation, swallow). Fixed
machine-parseable keys; the loop's terms as values; NSM primes ONLY as fixed
connective tokens in the "gloss" field, never free prose.

MEMORY AT THREE RANGES -- every record carries one:
  [EP]   this episode
  [OWN]  this agent's history on this game
  [COL]  the collective, with contact-class provenance (inherited-library /
         role-pool / cross-role -- the single A/B dial is excluded by prereg)
  [REPLAY] a replayed/observe-only step: playback narrated as playback,
         never a fresh decision (falsifier F3).

OVERHEAD LAW (F2's build-side half): every emit is O(1) -- one dict build plus
one fabric append; no scans, no queries, at emit time or anywhere in here.

CONSUMER (R3 gate): allowlisted in tests/gate/test_consumers.py citing
PREREG_W1_NARRATION.md -- the consumer lands with the falsifier experiment
(arm C, narrate-and-consume), and the entry is deleted then.

Containment (house law): the spine never raises into the host loop; failures
bump `errors` and drop the record.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

TOPIC = "narration"

# -- the record grammar: fixed tokens only ------------------------------------

# the six loop points + the pre-action bet that binds them
BET = "BET"
PERCEIVE = "PERCEIVE"
ROUTE = "ROUTE"
MINT = "MINT"
ECHO = "ECHO"
PLAN = "PLAN"
ACT = "ACT"
POINTS = (BET, PERCEIVE, ROUTE, MINT, ECHO, PLAN, ACT)

# record sides: bet-side lines land BEFORE the action, outcome-side after;
# replay is playback narrated as playback (F3), never either of the others.
SIDE_BET = "bet"
SIDE_OUTCOME = "outcome"
SIDE_REPLAY = "replay"

# memory ranges
EP = "EP"
OWN = "OWN"
COL = "COL"
REPLAY = "REPLAY"
RANGES = (EP, OWN, COL, REPLAY)

# [COL] contact-class provenance (the contact classes; the A/B dial excluded)
INHERITED_LIBRARY = "inherited-library"
ROLE_POOL = "role-pool"
CROSS_ROLE = "cross-role"
COL_CLASSES = (INHERITED_LIBRARY, ROLE_POOL, CROSS_ROLE)

# the four ROUTE bins (string-stable mirror of router.py; no import cycle)
TRANSFERRED = "TRANSFERRED"
NOVEL = "NOVEL"
BROKEN_REBINDING = "BROKEN_REBINDING"
BROKEN_MECHANISM = "BROKEN_MECHANISM"
BINS = (TRANSFERRED, NOVEL, BROKEN_REBINDING, BROKEN_MECHANISM)

# neighbour bin per bin + the discriminating fact separating them, in the
# router's own precedence terms (fixed tokens, the prereg's ROUTE example)
NEIGHBOUR = {
    TRANSFERRED: (BROKEN_MECHANISM, "residual<=eps"),
    BROKEN_REBINDING: (BROKEN_MECHANISM, "residual>eps AND binding_stale"),
    BROKEN_MECHANISM: (NOVEL, "residual>eps AND from_known_atom"),
    NOVEL: (TRANSFERRED, "residual>eps AND NOT from_known_atom"),
}

# the mint's resolved guard triple (mint.py: SUPPORT x NOVELTY x MDL)
GUARD_SUPPORT = "SUPPORT"
GUARD_NOVELTY = "NOVELTY"
GUARD_MDL = "MDL"

# NSM primes as CONNECTIVE tokens only -- one fixed gloss per (point, side).
GLOSS = {
    (BET, SIDE_BET): "I THINK THIS HAPPENS AFTER I DO THIS",
    (PLAN, SIDE_BET): "I WANT THIS; MAYBE I CAN DO SOMETHING",
    (ACT, SIDE_BET): "I DO THIS NOW BECAUSE I THINK THIS",
    (ACT, SIDE_REPLAY): "I DO THE SAME AS BEFORE; I DO NOT THINK NOW",
    (PERCEIVE, SIDE_OUTCOME): "I SEE THIS NOW; BEFORE I THOUGHT SOMETHING",
    (ROUTE, SIDE_OUTCOME): "THIS IS LIKE THIS; THIS IS NOT LIKE THE OTHER",
    (MINT, SIDE_OUTCOME): "MAYBE NOW I KNOW SOMETHING I DID NOT KNOW BEFORE",
    (ECHO, SIDE_OUTCOME): "THIS HAPPENED; I SAY IT HAPPENED",
}


# -- pure resolution functions (deterministic; the gate tests drive these) -----

def memory_range(replay: bool = False, inherited_n: int = 0, kin_n: int = 0,
                 collective_n: int = 0, own_n: int = 0
                 ) -> Tuple[str, Optional[str]]:
    """Resolve the memory-range tag from counts of what backs the decision.

    Furthest source wins: playback is [REPLAY] unconditionally; any collective
    contact tags [COL] with its contact class (inherited-library = read-only
    seed mounts, role-pool = kin scope, cross-role = imported cross-agent
    candidates); own cross-episode history tags [OWN]; else [EP].
    """
    if replay:
        return REPLAY, None
    if int(inherited_n or 0) > 0:
        return COL, INHERITED_LIBRARY
    if int(kin_n or 0) > 0:
        return COL, ROLE_POOL
    if int(collective_n or 0) > 0:
        return COL, CROSS_ROLE
    if int(own_n or 0) > 0:
        return OWN, None
    return EP, None


def predict_bin(staked: bool, known_atoms: bool
                ) -> Tuple[str, Dict[str, Optional[str]]]:
    """The bet-side ROUTE prediction: expected bin + why-not-the-neighbour.

    A staked bet predicts it HOLDS (TRANSFERRED); the discriminating fact names
    the neighbour a miss would land in. Nothing staked predicts NOVEL -- an
    unstaked residual cannot settle TRANSFERRED.
    """
    if not staked:
        return NOVEL, {"not": TRANSFERRED,
                       "fact": "no bet staked; nothing can settle TRANSFERRED"}
    if known_atoms:
        return TRANSFERRED, {
            "not": BROKEN_MECHANISM,
            "fact": "bet staked with known atoms in play; predicted residual<=eps"}
    return TRANSFERRED, {
        "not": NOVEL,
        "fact": "bet staked without a known atom; a miss lands NOVEL"}


def route_why_not(settled_bin: Optional[str]) -> Dict[str, Optional[str]]:
    """The outcome-side neighbour discrimination for a settled bin (fixed map).
    A step with no staked bet resolves no bin and fabricates none (R4)."""
    pair = NEIGHBOUR.get(settled_bin) if settled_bin else None
    if pair is None:
        return {"not": None, "fact": "no bet staked; no bin resolved"}
    return {"not": pair[0], "fact": pair[1]}


def plan_verdict(gates_before: Optional[Dict[str, Any]],
                 gates_after: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """PURE: drove / shadowed / no-steps + which g-gate stopped it, from the
    plan-gate pass counters either side of the cycle's plan block. The gates
    pass in order g1..g7; the first gate whose count did not advance is the
    one that stopped the plan."""
    b = gates_before or {}
    a = gates_after or {}

    def moved(k: str) -> bool:
        try:
            return int(a.get(k, 0) or 0) > int(b.get(k, 0) or 0)
        except Exception:
            return False

    if moved("drive"):
        return {"mode": "drove", "gate": None}
    if moved("shadow"):
        return {"mode": "shadowed", "gate": None}
    for g in ("g1", "g2", "g3", "g4", "g5", "g6", "g7"):
        if not moved(g):
            return {"mode": "no-steps", "gate": g}
    return {"mode": "no-steps", "gate": "g7"}


def mint_close(verdict: Optional[Dict[str, Any]],
               changed: Optional[int]) -> Dict[str, Any]:
    """PURE: the outcome-side MINT payload -- the candidate offered, or which
    guard of the resolved triple (SUPPORT x NOVELTY x MDL) was the zero, plus
    both sides of the MDL bargain (atom cost 1+changed vs residual cost
    2*changed+1, mint.py's own constants) and whether it paid."""
    v = (verdict or {}).get("verdict")
    out: Dict[str, Any] = {"candidate": (verdict or {}).get("id"),
                           "verdict": v, "guard_zero": None, "bargain": None}
    if changed is not None and int(changed) >= 0:
        c = float(int(changed))
        out["bargain"] = {"atom_cost": 1.0 + c, "residual_cost": 2.0 * c + 1.0,
                          "paid": v == "mint"}
    if v == "mint":
        return out
    if v == "rederivation":
        out["guard_zero"] = GUARD_NOVELTY
    elif v == "quarantine":
        out["guard_zero"] = GUARD_SUPPORT
    elif v == "reject":
        # a "w"-carrying reject is the surprise-weighted SUPPORT zero; a
        # zero-changed reject is SUPPORT too; anything else fell to MDL.
        if "w" in (verdict or {}) or not changed:
            out["guard_zero"] = GUARD_SUPPORT
        else:
            out["guard_zero"] = GUARD_MDL
    else:                         # no offer reached the mint at all this step
        out["guard_zero"] = GUARD_SUPPORT
    return out


# -- the spine ----------------------------------------------------------------

class NarrationSpine:
    """The per-step emitter: BET -> PLAN -> ACT before the action executes;
    PERCEIVE -> ROUTE -> MINT -> ECHO after, each closing against the bet by
    reference. One fabric append per event (O(1)); never raises."""

    TOPIC = TOPIC

    def __init__(self, fabric: Any, game: str = "game"):
        self.fabric = fabric
        self.game = str(game)
        # instance-monotonic event sequence -- NEVER resets, so within any one
        # step the bet's sequence number is strictly earlier than the act's
        # (F1's precedence check compares them).
        self._sq = 0
        self._step = -1
        self._bet_id: Optional[str] = None
        self._bet_step: Optional[int] = None
        self.emitted = 0
        self.dup_bets = 0     # a second bet on one step: refused, counted
        self.errors = 0

    @property
    def bet_id(self) -> Optional[str]:
        return self._bet_id

    def start_step(self, step: int) -> None:
        """Open a step: the bet slate is clean (exactly one bet per step)."""
        self._step = int(step)
        self._bet_id = None

    def _emit(self, point: str, side: str, rng: str,
              payload: Optional[Dict[str, Any]], ref: Optional[str] = None,
              col_class: Optional[str] = None) -> Optional[str]:
        """One record, fixed keys, one append. O(1); contained."""
        try:
            self._sq += 1
            rid = "n:%s:%d:%d" % (self.game, int(self._step), self._sq)
            rec: Dict[str, Any] = {
                "id": rid, "step": int(self._step), "sq": self._sq,
                "point": point, "side": side, "range": rng,
                "col_class": col_class, "ref": ref,
                "gloss": GLOSS.get((point, side), ""), "game": self.game,
            }
            for k, v in (payload or {}).items():
                if k not in rec:
                    rec[k] = v
            self.fabric.append("personal", TOPIC, rec)
            self.emitted += 1
            return rid
        except Exception:
            self.errors += 1
            return None

    # -- bet side (BEFORE the action executes) --------------------------------

    def bet(self, slots: Optional[Dict[str, Any]], route_bin: str,
            why_not: Optional[Dict[str, Any]], mint_candidate: Optional[str],
            guard_zero: Optional[str], rng: str,
            col_class: Optional[str] = None) -> Optional[str]:
        """THE one bet-side record per step (F1: exactly one, with bin +
        why-not-neighbour + range tag). A second bet on the same step is
        refused and counted -- never a duplicate record."""
        if self._bet_id is not None and self._bet_step == self._step:
            self.dup_bets += 1
            return self._bet_id
        rid = self._emit(BET, SIDE_BET, rng, {
            "slots": dict(slots or {}),
            "bin": route_bin,
            "why_not": dict(why_not or {}),
            "mint_candidate": mint_candidate,
            "guard_zero": guard_zero,
        }, col_class=col_class)
        if rid is not None:
            self._bet_id = rid
            self._bet_step = self._step
        return rid

    def plan(self, mode: str, gate: Optional[str], rng: str,
             col_class: Optional[str] = None) -> Optional[str]:
        """PLAN: drove / shadowed / no-steps, with the g-gate that stopped it."""
        return self._emit(PLAN, SIDE_BET, rng,
                          {"mode": str(mode), "gate": gate},
                          ref=self._bet_id, col_class=col_class)

    def act(self, action: int, rung: str, rng: str,
            col_class: Optional[str] = None) -> Optional[str]:
        """ACT: the chosen action + the rung that won the wheel. PRECEDENCE BY
        CONSTRUCTION (F1): refuses to emit when no bet was placed this step --
        an act without a bet has skipped step 1, and an explanation written
        afterward would be a reconstruction, not a decision."""
        if self._bet_id is None or self._bet_step != self._step:
            self.errors += 1
            return None
        return self._emit(ACT, SIDE_BET, rng,
                          {"action": int(action), "rung": str(rung or "")},
                          ref=self._bet_id, col_class=col_class)

    # -- outcome side (AFTER the action; closes against the bet) --------------

    def perceive(self, slots: Optional[Dict[str, Any]], rng: str,
                 col_class: Optional[str] = None) -> Optional[str]:
        """PERCEIVE: prediction vs outcome, PER SLOT -- never aggregated."""
        return self._emit(PERCEIVE, SIDE_OUTCOME, rng,
                          {"slots": dict(slots or {})},
                          ref=self._bet_id, col_class=col_class)

    def route(self, settled_bin: Optional[str],
              why_not: Optional[Dict[str, Any]],
              bins: Optional[Dict[str, Any]], rng: str,
              col_class: Optional[str] = None) -> Optional[str]:
        """ROUTE: the settled bin + the discriminating fact vs the neighbour
        (per-slot bins ride along; a no-bet step carries bin=None -- R4)."""
        return self._emit(ROUTE, SIDE_OUTCOME, rng,
                          {"bin": settled_bin, "why_not": dict(why_not or {}),
                           "bins": dict(bins or {})},
                          ref=self._bet_id, col_class=col_class)

    def mint_point(self, candidate: Optional[str], verdict: Optional[str],
                   guard_zero: Optional[str], bargain: Optional[Dict[str, Any]],
                   rng: str, col_class: Optional[str] = None) -> Optional[str]:
        """MINT: the candidate offered, or which guard was the zero; both
        sides of the MDL bargain. (Named mint_point, not mint: the source laws
        in tests/gate key on the FIRST `.mint(` in cognitive_loop.py being the
        fabric's idea mint on the credit path -- narrating the MINT point must
        not shadow the mint itself.)"""
        return self._emit(MINT, SIDE_OUTCOME, rng,
                          {"candidate": candidate, "verdict": verdict,
                           "guard_zero": guard_zero, "bargain": bargain},
                          ref=self._bet_id, col_class=col_class)

    def echo(self, status: str, detail: Optional[Dict[str, Any]], rng: str,
             col_class: Optional[str] = None) -> Optional[str]:
        """ECHO: what settled, or *candidate* stated as such."""
        return self._emit(ECHO, SIDE_OUTCOME, rng,
                          {"status": str(status), "detail": dict(detail or {})},
                          ref=self._bet_id, col_class=col_class)

    # -- replay (F3) ----------------------------------------------------------

    def replay(self, action: int, step: Optional[int] = None) -> Optional[str]:
        """F3: a replayed/observe-only step narrates as [REPLAY] -- playback
        marked as playback: side="replay", range=REPLAY, NO bet, NO reference.
        Narration must not launder playback into reasoning."""
        if step is not None:
            self._step = int(step)
        return self._emit(ACT, SIDE_REPLAY, REPLAY,
                          {"action": int(action)}, ref=None)
