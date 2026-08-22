"""persistence.py -- THE PERSISTENCE MONITOR (PREREG_PERSISTENCE_MONITOR.md,
Seat 3 APPROVED 2026-08-21): the achievement gap GAP 2 of F1_VERDICT_AND_SHADOW_TEST
Part 2 -- "persisting in what isn't working is a TREND no single-event bin can
express -- a counter over narration, not a fifth bin."

A READ-ONLY CONSUMER of the narration stream (narration.py's record grammar). It
classifies no event. It COUNTS: the same residual recurring under an unchanged
strategy for k consecutive steps is ONE named finding -- a PERSISTENCE record --
and a bounded channel to the two book-computed risk modulators. Nothing here
prices, ranks or selects; nothing here writes a stream (the spine emits the
record through its own emitter; this module holds no fabric and never appends).

THE UNIT (fixed tokens from the stream; nothing inferred). Per step, from the
records that close against that step's BET:
  RESIDUAL rho  = (ROUTE.bin, ROUTE.why_not.fact), restricted to the FAILURE bins
                  BROKEN_REBINDING / BROKEN_MECHANISM -- a staked bet that missed.
                  NOVEL is not failure (nothing staked); TRANSFERRED is success;
                  bin=None (no bet: every [REPLAY] step, F3) is no rho at all.
  STRATEGY sigma = (ACT.rung, BET.bin, the sorted slot-key shape of BET.slots --
                  what last_bet already retains -- PLAN.mode, PLAN.gate).
A RUN is a maximal sequence of consecutive steps of one game with identical
(rho, sigma) and rho != None. It resets to 0 when rho changes or is None (a
TRANSFERRED settle included), sigma changes, or the level changes (the BET
record's additive `level` field; records without it cannot reset on level and
readout() says so). The monitor's own PERSISTENCE records never count.

k -- DERIVED, never a dial: k_g = the median number of steps between successive
level crossings in this agent's OWN history on game g (the `level` field on BET
records, per game; a level's step count is the number of BETs placed at that
level before the crossing). Fallbacks, in order: no crossing in OWN history ->
the population median of per-level step counts over games with >= 1 crossing
([COL]: the other games visible in the same stream prefix -- see THE PREFIX
LAW below); no crossing anywhere -> k undefined: the monitor counts, never
fires, readout `unarmed`. k_g >= K_FLOOR = 2 by the prereg's definition (one
failure is an event; repetition is the trend). k is recomputed at each level
crossing (and at each episode boundary) and FROZEN within a level -- the run
being measured never moves its own bar.

THE PREFIX LAW (the replay requirement): the monitor is a pure fold over the
narration record sequence -- no wall-clock, no RNG, no read of anything but the
records handed to it -- so replay() over the JSONL yields byte-identical
PERSISTENCE records to the online emission. That is WHY the [COL] fallback is
the other games in the same stream prefix and NOT a read of other agents'
streams at derivation time: a population read taken from disk is an as-of
snapshot, and a k that depends on when the stream was replayed is not a
function of the prefix. Stated, not hidden.

HOT PATH: observe() is O(1) per record (one dict lookup per point, no scans);
the one O(stream) read is from_fabric() -- the priming fold at spine
construction (once per game/spine), never per record and never per step.

THE CONSUMER (a modulator, never a price): affect.AffectGains.persist ==
min(1, run/k) (0 with no live run; bounded [0, 1]) feeds EXACTLY two sinks --
the explore-effort steer (AffectGains.starvation_steer's explore_boost, the
STARVE_STEP path) and the goal stuck/abandonment measure (goal.GoalManager.
observe's stall clock). Not the mint's MDL terms, not reputation, not breeding,
not any atom's standing: gate tests/gate/test_persistence.py F5 scans the price
modules for the channel and the token by identity.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from engines.egocentric import narration as _na

# The stream this consumer reads -- the spine's topic, mirrored as a module
# constant so the R3 consumer gate (tests/gate/test_consumers.py) resolves the
# reader by name. Asserted equal at import: a drift here is a broken reader.
TOPIC = "narration"
if TOPIC != _na.TOPIC:
    raise RuntimeError("persistence.TOPIC drifted from narration.TOPIC")

# rho exists only in the two FAILURE bins (a staked bet that missed). Mirrored
# as string-stable tokens, narration.py's own pattern: these are the STREAM's
# bin tokens, not the router's organ (the registry's severed-organ scan keys on
# the router symbol's bare name; a local definition says which one this is).
# Asserted equal to narration's table at import.
BROKEN_REBINDING = "BROKEN_REBINDING"
BROKEN_MECHANISM = "BROKEN_MECHANISM"
FAILURE_BINS = (BROKEN_REBINDING, BROKEN_MECHANISM)
if FAILURE_BINS != (_na.BROKEN_REBINDING, _na.BROKEN_MECHANISM):
    raise RuntimeError("persistence.FAILURE_BINS drifted from narration's bins")

# k's floor -- PINNED by PREREG_PERSISTENCE_MONITOR.md ("k_g >= 2 by
# definition: one failure is an event (a bin); repetition is the trend").
# Not a dial: KNOBS.md G30.
K_FLOOR = 2

# readout tokens (fixed)
UNARMED = "unarmed"
COUNTING = "counting"
PERSISTING = "persisting"
LEVEL_RESET_ON = "level field present: resets on level change"
LEVEL_RESET_OFF = "no level field on BET records: cannot reset on level"


# -- pure functions of single records / histories -----------------------------

def rho_of(route: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """The step's RESIDUAL from its ROUTE record: (bin, discriminating fact)
    in a FAILURE bin; None otherwise (TRANSFERRED, NOVEL, or no bet)."""
    b = route.get("bin")
    if b not in FAILURE_BINS:
        return None
    return (str(b), str((route.get("why_not") or {}).get("fact")))


def sigma_of(bet: Dict[str, Any], plan: Optional[Dict[str, Any]],
             act: Optional[Dict[str, Any]]) -> Tuple[Any, ...]:
    """The step's STRATEGY: (ACT.rung, BET.bin, sorted slot-key shape,
    PLAN.mode, PLAN.gate) -- fixed tokens only; a missing PLAN/ACT record
    contributes its absent tokens (None), never an inferred value."""
    slots = tuple(sorted(str(s) for s in (bet.get("slots") or {})))
    return (
        (act or {}).get("rung"),
        bet.get("bin"),
        slots,
        (plan or {}).get("mode"),
        (plan or {}).get("gate"),
    )


def upper_median(values: List[int]) -> int:
    """The upper median of a non-empty integer list: an element of the data
    (no rounding convention to guess at)."""
    s = sorted(int(v) for v in values)
    return s[len(s) // 2]


def derive_k(own: List[int], col: List[int]
             ) -> Tuple[Optional[int], Optional[str]]:
    """k from the per-level step counts: OWN history first, the [COL] pool
    second, undefined (None, None) when neither has a crossing. Floored at
    K_FLOOR. Returns (k, source-range tag)."""
    if own:
        return max(K_FLOOR, upper_median(own)), _na.OWN
    if col:
        return max(K_FLOOR, upper_median(col)), _na.COL
    return None, None


# -- the fold ------------------------------------------------------------------

class _GameState:
    """Per-game fold state: the live run, the frozen k, the level ledger and
    the open step buffer. An internal organ of the monitor."""

    __slots__ = ("run", "rho", "sigma", "first", "last_step", "fired",
                 "persisting", "k", "k_source", "k_derived", "level",
                 "level_steps", "level_counts", "level_field", "step",
                 "last_seen_step", "closed", "crossings")

    def __init__(self) -> None:
        self.run = 0
        self.rho: Optional[Tuple[str, str]] = None
        self.sigma: Optional[Tuple[Any, ...]] = None
        self.first: Optional[Dict[str, Any]] = None   # the run's first BET
        self.last_step: Optional[int] = None
        self.fired = False
        self.persisting = False
        self.k: Optional[int] = None
        self.k_source: Optional[str] = None
        self.k_derived = False
        self.level: Optional[int] = None
        self.level_steps = 0
        self.level_counts: List[int] = []     # OWN: completed levels' step counts
        self.level_field = False
        self.step: Optional[Dict[str, Any]] = None   # {"bet", "plan", "act"}
        self.last_seen_step: Optional[int] = None
        self.closed = 0
        self.crossings = 0

    def reset_run(self) -> None:
        self.run = 0
        self.rho = None
        self.sigma = None
        self.first = None
        self.last_step = None
        self.fired = False
        self.persisting = False


class PersistenceMonitor:
    """The read-only consumer: observe(record) -> [finding] (at most one),
    O(1) per record. A pure fold over the record sequence, per game."""

    def __init__(self) -> None:
        self.games: Dict[str, _GameState] = {}
        self.current: Optional[str] = None    # the game of the last record
        self.errors = 0
        self.fired = 0

    @classmethod
    def from_fabric(cls, fabric: Any) -> PersistenceMonitor:
        """THE priming read: fold the agent's own narration stream as written
        so far (one O(stream) read, at spine construction -- never per
        record). Findings already on the stream are records; none re-fire."""
        mon = cls()
        mon.prime(fabric.query("personal", TOPIC))
        return mon

    def prime(self, records: Any) -> None:
        """Fold a record prefix with firing suppressed (the prefix already
        carries its PERSISTENCE records, or they were never emitted)."""
        for rec in records:
            self.observe(rec)

    # -- the hook's target ----------------------------------------------------

    def observe(self, rec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """One record in; zero or one finding out. Never raises."""
        try:
            return self._observe(rec)
        except Exception:
            self.errors += 1
            return []

    def _observe(self, rec: Dict[str, Any]) -> List[Dict[str, Any]]:
        point = rec.get("point")
        game = str(rec.get("game"))
        self.current = game
        st = self.games.get(game)
        if st is None:
            st = self.games[game] = _GameState()
        if point == _na.PERSISTENCE:
            return []                         # the monitor's own records never count
        if point == _na.ARM:
            self._boundary(st)                # an episode's first record
            return []
        step = rec.get("step")
        if point == _na.ACT and rec.get("side") == _na.SIDE_REPLAY:
            st.step = None                    # [REPLAY]: no bet, bin None -> reset
            st.reset_run()
            self._seen(st, step)
            return []
        if point == _na.BET:
            if st.step is not None:
                st.reset_run()                # an unclosed step has no rho
            if (step is not None and st.last_seen_step is not None
                    and int(step) < st.last_seen_step):
                self._boundary(st)            # a loop with no ARM record
            self._level(st, rec)
            if not st.k_derived:
                self._rederive(st)
            st.step = {"bet": rec, "plan": None, "act": None}
            self._seen(st, step)
            return []
        buf = st.step
        if buf is None or rec.get("ref") != buf["bet"].get("id"):
            return []                         # not this step's closing records
        if point == _na.PLAN:
            if buf["plan"] is None:
                buf["plan"] = rec             # the bet-side verdict: first PLAN
            return []
        if point == _na.ACT:
            if buf["act"] is None:
                buf["act"] = rec
            return []
        if point != _na.ROUTE:
            return []
        # ROUTE closes the step: the unit is complete
        st.step = None
        st.closed += 1
        bet = buf["bet"]
        rho = rho_of(rec)
        if rho is None:
            st.reset_run()
            return []
        sigma = sigma_of(bet, buf["plan"], buf["act"])
        bstep = int(bet.get("step", 0) or 0)
        if st.run > 0 and rho == st.rho and sigma == st.sigma:
            st.run += 1
            st.last_step = bstep
        else:
            st.run = 1
            st.rho = rho
            st.sigma = sigma
            st.first = {"id": bet.get("id"), "range": bet.get("range"),
                        "col_class": bet.get("col_class"), "step": bstep}
            st.last_step = bstep
            st.fired = False
            st.persisting = False
        if st.k is None or st.fired or st.run != st.k:
            return []
        st.fired = True                       # exactly once per run
        st.persisting = True
        self.fired += 1
        return [self._finding(st, game, rec)]

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _seen(st: _GameState, step: Any) -> None:
        if step is not None:
            st.last_seen_step = int(step)

    def _boundary(self, st: _GameState) -> None:
        """An episode boundary: the in-progress level segment is incomplete
        (never crossed) and is discarded; the run resets; k re-derives (a
        level start, so still frozen within the level that follows)."""
        st.step = None
        st.reset_run()
        st.level = None
        st.level_steps = 0
        st.last_seen_step = None
        self._rederive(st)

    def _level(self, st: _GameState, bet: Dict[str, Any]) -> None:
        lv = bet.get("level")
        if lv is None:
            return                            # no field: cannot reset on level
        st.level_field = True
        lv = int(lv)
        if st.level is None:
            st.level = lv
        elif lv > st.level:                   # a level CROSSING
            st.level_counts = st.level_counts + [st.level_steps]
            st.crossings += 1
            st.level = lv
            st.level_steps = 0
            st.reset_run()
            self._rederive(st)
        elif lv < st.level:                   # a new episode without its ARM
            st.level = lv
            st.level_steps = 0
            st.reset_run()
            self._rederive(st)
        st.level_steps += 1

    def _rederive(self, st: _GameState) -> None:
        col = [c for g in self.games.values() if g is not st and g.level_counts
               for c in g.level_counts]
        st.k, st.k_source = derive_k(st.level_counts, col)
        st.k_derived = True

    @staticmethod
    def _finding(st: _GameState, game: str, route: Dict[str, Any]
                 ) -> Dict[str, Any]:
        first = st.first or {}
        rho = st.rho or ("", "")
        sigma = st.sigma or (None, None, (), None, None)
        return {
            "range": first.get("range") or _na.EP,
            "col_class": first.get("col_class"),
            "ref": first.get("id"),
            "step": int(route.get("step", 0) or 0),
            "sq": int(route.get("sq", 0) or 0),
            "payload": {
                "k": st.k, "run": st.run,
                "rho": {"bin": rho[0], "fact": rho[1]},
                "sigma": {"rung": sigma[0], "bin": sigma[1],
                          "slots": list(sigma[2]), "mode": sigma[3],
                          "gate": sigma[4]},
                "first_step": first.get("step"), "last_step": st.last_step,
                "game": game,
            },
        }

    # -- the channel + the readout --------------------------------------------

    def persist(self, game: Optional[str] = None) -> float:
        """persist = min(1, run/k): 0 with no live run or k undefined."""
        st = self.games.get(str(game) if game is not None else self.current)
        if st is None or st.k is None or st.run <= 0:
            return 0.0
        return min(1.0, float(st.run) / float(st.k))

    def readout(self, game: Optional[str] = None) -> Dict[str, Any]:
        """The legible state: k and its source, the run, the status
        (`unarmed` when k is undefined), and whether level resets can fire."""
        g = str(game) if game is not None else self.current
        st = self.games.get(g)
        if st is None:
            return {"game": g, "k": None, "k_source": None, "run": 0,
                    "persist": 0.0, "status": UNARMED,
                    "level_reset": LEVEL_RESET_OFF, "level_counts": [],
                    "crossings": 0, "closed": 0}
        status = (UNARMED if st.k is None
                  else (PERSISTING if st.persisting else COUNTING))
        return {"game": g, "k": st.k, "k_source": st.k_source, "run": st.run,
                "persist": self.persist(g), "status": status,
                "level_reset": (LEVEL_RESET_ON if st.level_field
                                else LEVEL_RESET_OFF),
                "level_counts": list(st.level_counts),
                "crossings": st.crossings, "closed": st.closed}


# -- the offline reader --------------------------------------------------------

def replay(fabric: Any, game: Optional[str] = None) -> List[Dict[str, Any]]:
    """THE STREAM READER (R3): replay the narration JSONL through a fresh
    monitor and rebuild every PERSISTENCE record it would have emitted, via
    narration.make_record -- byte-identical to the online records (minus
    the fabric's `seq`). The fold runs over the WHOLE stream (the [COL]
    fallback is a property of the prefix); `game` filters the output only."""
    mon = PersistenceMonitor()
    out: List[Dict[str, Any]] = []
    for rec in fabric.query("personal", TOPIC):
        for f in mon.observe(rec):
            g = str(rec.get("game"))
            if game is not None and g != str(game):
                continue
            out = out + [_na.make_record(
                g, f["step"], f["sq"] + 1, _na.PERSISTENCE, _na.SIDE_MONITOR,
                f["range"], f["payload"], f["ref"], f["col_class"])]
    return out
