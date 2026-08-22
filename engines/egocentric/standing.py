"""standing.py -- R3/R4: STANDING AT THE ATOM GRAIN (PREREG_STANDING_HALF_LIFE_ATOMS.md).

THE GAP, from the code: `effects.Gamma` only grows -- `add` appends, `get` is
last-wins, every update is a superseding append. `planner._candidate_ids`
returned EVERY id valid at (game, level), sorted lexically, so an atom that had
mispredicted a hundred times entered the search on equal footing with one that
had held a hundred times. `scheduler.plan_wrong` was a ledger "deliberately not
yet a demotion". This module is the demotion.

WHAT STANDING IS, AND IS NOT (FIGURE 1: the ground is the only metric).
S RANKS RETRIEVAL and nothing else. It is never a score, never a metric, never
reported as progress, never priced. Its only two consumers are
`planner._candidate_ids` (the visit order + the evicted filter) and this
module's own eviction writer. Nothing that prices (pricing / bank / mastery /
lp_drive / rho / consumer.admission_price) reads it, and the gate asserts that
by source (tests/gate/test_standing.py, the FIGURE 1 sink identity).

ONE CLOCK: the A3-4 episode ordinal `ep`. The mint stamps it on every verdict;
this build extends the stamp to the two atoms-stream event writers (the
conflict clause's reinstate, the composite settle) and to the two PLAN-point
narration writers (a HELD driven step, a routed plan-wrong abort). AN EVENT
WITH NO READABLE ep IS NOT COUNTED -- no clock, no event; the drop is counted
(`unstamped`), never silently absorbed.

EARN EVENTS E(a)  (FIGURE 2: each is the GROUND settling, never another atom's
or another agent's opinion -- there is no mutual update between atoms; every
atom is ranged against the world separately):
  e1  the mint verdict on a's key            (mint_verdicts, verdict=mint)
  e2  each rederivation verdict on a's key   (mint_verdicts, verdict=rederivation)
      -- FIGURE 5's "nothing new here: the machinery worked; the answer was
      already known" is a rederivation, and it STRENGTHENS.
  e3  each HELD step: a driven plan step that landed (the abort router's
      no-abort branch), recorded per step atom at the PLAN point; and, for
      composites, stage 4's `settled: true` superseding append -- counted at
      the CANDIDATE -> SETTLED transition, so a later superseding append that
      carries the flag forward is not a second event.

MISPREDICTION EVENTS M(a)  (against the LIVE frame, never a simulation):
  m1  each plan-wrong routed against a as a step atom, persisted by `steps` +
      `ep` on the PLAN abort narration record that already fires.
  m2  each `ctx_conflict` superseding append on a from the OBSERVATION-time
      conflict clause.
DISJOINTNESS: the stage-4 plan-wrong path writes a ctx_conflict AND a ledger
increment for ONE event. Its append carries the additive envelope marker
`via: plan-wrong`, and this reader counts it under m1 only -- one event, one
count. Composites are ids like any other.

THE NUMBER:  S(a, t) = sum_{e in E(a)} d^(t - ep_e) - sum_{m in M(a)} d^(t - ep_m)
Both sides decay at the SAME rate: an old misprediction fades exactly as an old
confirmation does (R4 binds failures too -- pariah decay's symmetry). t is the
highest episode ordinal in the books, DERIVED, never a clock.

THE DECAY RULE -- derived, not borrowed. Prestige (engines/social/
prestige_engine.py:214-235) decays 3% per GENERATION because that is the unit
at which a contribution can be re-earned. An atom's re-earn unit is the
EPISODE, so the tick is `ep`. The RATE comes from the population's own cadence:
g(a) = the median gap in episodes between successive earn events of a, over
atoms with >= 2 earn events in DISTINCT episodes; g* = the population median of
g(a) for this game; d = 0.5^(1/g*) -- the half-life is one typical re-earn
interval. Below MIN_QUALIFYING atoms a median is not a distribution: d = 0.97,
prestige's own rate, reported BORROWED until the population supplies its own.

RANK / EVICTION / RE-ENTRY:
  RANK      `_candidate_ids` orders by S descending, ties keeping today's
            lexical order. The search visits stronger atoms first; under the
            node budget this decides which plans are found AT ALL -- decay
            BITES (the Seat 3 rider).
  EVICTION  tau = Q1 - 1.5*IQR of S over the atoms valid at this (game, level)
            (Tukey's lower fence), recomputed at each planner engagement. An
            atom is evicted iff S < tau AND M_d > 0. The fence IS the
            Dislodging-vs-Assumption discriminator: when the world remaps and
            every atom goes wrong together the population's S drops together,
            the fence moves with it, and nothing is evicted. The M_d > 0 clause
            is Seat 3's ruling TAKEN: silence is not an outcome -- decay ranks
            an untouched atom down, it never evicts it.
  WRITE     a superseding append on the atoms stream, same id, envelope
            `evicted / S / tau / ep / cause` (FIGURE 10: every append carries
            the numbers AND the event kind that caused it, so a later reader
            can locate the error rather than feel it). NOTHING is deleted; the
            mint's NOVELTY guard still reads the whole stream, so an evicted
            atom's key stays known and no duplicate is ever re-minted.
  RE-ENTRY  re-observation fires a rederivation (e2) regardless of eviction;
            at the next engagement S >= tau appends the atom back
            `evicted: false`, and the re-entry count is GATE B's third
            change-mark component (a re-entry grew the set; an eviction shrank
            it and need not reopen the gate).

REPLAY (F6): every number here is a fold over the books. The in-memory state is
incremental (the `mint._refresh_sig_index` pattern: each record processed once
per process, a shrunk stream forcing a full reset), and a fresh process over
the same books computes identical S for every atom.

UNDO: `standing=None` at `plan_to_identity` (and `abduced_plan`) restores
today's `_candidate_ids` exactly; drop the engage() call site and the GATE B
component. The `evicted`/`S`/`tau` envelope fields, the `steps`/`ep` on PLAN
records, the HELD records and the `via` marker remain readable history.

Containment (house law): pure reads + one append per transition; nothing here
raises into the host loop -- failures bump `errors` and the caller proceeds.
Stdlib + numpy only.
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

__all__ = ["StandingBook", "valid_ids", "fence", "episode_of",
           "EVENTS", "EARN", "MISPREDICT"]

# ── THE EVENT VOCABULARY (FIXED; consumers may switch on these values) ───────
E_MINT = "e1"                 # the mint verdict on the atom's key
E_REDERIVATION = "e2"         # a rederivation verdict on the atom's key
E_HELD = "e3"                 # a driven step that landed / a composite settle
M_PLAN_WRONG = "m1"           # a plan-wrong routed against the atom as a step
M_CTX_CONFLICT = "m2"         # an observation-time ctx_conflict append
EARN = frozenset({E_MINT, E_REDERIVATION, E_HELD})
MISPREDICT = frozenset({M_PLAN_WRONG, M_CTX_CONFLICT})
EVENTS = (E_MINT, E_REDERIVATION, E_HELD, M_PLAN_WRONG, M_CTX_CONFLICT)

# ── THE ENVELOPE FIELDS the eviction/re-entry append carries ─────────────────
EVICTED_FIELD = "evicted"     # bool, last-wins (Gamma.get's rule)
S_FIELD = "S"                 # the standing that decided it
TAU_FIELD = "tau"             # the fence it was decided against
EP_FIELD = "ep"               # the episode ordinal it was decided at
CAUSE_FIELD = "cause"         # the EVENT KIND that last moved this atom
VIA_FIELD = "via"             # the additive disjointness marker
VIA_PLAN_WRONG = "plan-wrong"  # string-stable mirror of scheduler.ABORT_PLAN_WRONG

# ── THE PLAN-POINT TOKENS (fixed; narrated verbatim, never free prose) ───────
PLAN_EVICTED = "evicted"
PLAN_REENTERED = "re-entered"
PLAN_HELD = "held"
HELD_GATE = "step-landed"     # the HELD record's gate slot
ABORT_MODE = "abort"          # the abort router's own PLAN mode
PLAN_POINT = "PLAN"           # string-stable mirror of narration.PLAN
NARRATION_TOPIC = "narration"  # string-stable mirror of narration.TOPIC
VERDICT_TOPIC = "mint_verdicts"  # string-stable mirror of mint.VERDICT_TOPIC
ATOMS_TOPIC = "atoms"         # string-stable mirror of effects.Gamma.TOPIC
V_MINT = "mint"
V_REDERIVATION = "rederivation"

# ── THE KNOBS (KNOBS G35/G36) ────────────────────────────────────────────────
# BORROWED: prestige's own 3%-per-generation rate, used only until the
# population supplies >= MIN_QUALIFYING atoms with a re-earn cadence of their
# own. Reported as BORROWED by decay(); never silently the answer.
BORROWED_DECAY = 0.97
# PINNED by the prereg: "a median over fewer is not a distribution".
MIN_QUALIFYING = 30
# PINNED by the prereg: Tukey's lower fence.
IQR_FENCE = 1.5
HALF_LIFE = 0.5


class StandingBook:
    """The per-loop standing state: the event books folded out of the streams,
    the decay rate derived from the population's own cadence, the rank the
    planner visits in, and the ONE eviction/re-entry writer.

    OWNED by `scheduler.PlannerScheduler` beside the W2c retention store, and
    handed to the planner as `standing=` at the loop's call sites. Unlike the
    retention store it is NOT cleared on a level change: standing is the atom's
    history against the ground, and the board redrawing does not unmake it
    (the level scope lives in tau, which is recomputed per (game, level))."""

    def __init__(self) -> None:
        # atom id -> [(ep, event kind)] for the id-addressed events (e3/m1/m2)
        self._id_events: Dict[str, List[Tuple[int, str]]] = {}
        # atom KEY -> [(ep, event kind)] for the verdict-addressed events
        # (e1/e2 -- mint_verdicts name the key, never the id)
        self._key_events: Dict[str, List[Tuple[int, str]]] = {}
        self._id_key: Dict[str, str] = {}
        self._key_ids: Dict[str, List[str]] = {}
        self._id_game: Dict[str, str] = {}
        self._evicted: Dict[str, bool] = {}      # last-wins over the stream
        self._settled: Dict[str, None] = {}      # ids whose settle transition fired
        self._pos: Dict[str, int] = {"atoms": 0, "verdicts": 0, "narration": 0}
        self._len: Dict[str, int] = {"atoms": 0, "verdicts": 0, "narration": 0}
        self._t = 0                              # the highest ep in the books
        self._d: Dict[str, Tuple[float, bool]] = {}   # game -> (d, borrowed)
        # instruments (out-of-band; never a stream record, never a metric)
        self.evictions = 0
        self.reentries = 0
        self.unstamped = 0        # events dropped for want of a readable ep
        self.errors = 0

    # -- the fold over the books ---------------------------------------------

    def refresh(self, gamma) -> None:
        """Fold every stream record appended since the last call into the event
        books. Incremental per process (`_pos`, the `_refresh_sig_index`
        pattern); a SHRUNK stream (the janitor rewrote it) resets every derived
        map and re-folds from zero, so the books always describe the stream as
        it is now -- which is what makes two processes agree (F6)."""
        try:
            fab = gamma.fabric
            topic = getattr(gamma, "TOPIC", ATOMS_TOPIC)
            atoms = fab.query("collective", topic)
            verdicts = fab.query("collective", VERDICT_TOPIC)
            narr = fab.query("personal", NARRATION_TOPIC)
            if (len(atoms) < self._len["atoms"]
                    or len(verdicts) < self._len["verdicts"]
                    or len(narr) < self._len["narration"]):
                self._reset()
            grew = (len(atoms) > self._pos["atoms"]
                    or len(verdicts) > self._pos["verdicts"]
                    or len(narr) > self._pos["narration"])
            self._scan_atoms(atoms)
            self._scan_verdicts(verdicts)
            self._scan_narration(narr)
            self._len = {"atoms": len(atoms), "verdicts": len(verdicts),
                         "narration": len(narr)}
            if grew:
                self._d.clear()          # the cadence moved: re-derive d
        except Exception:
            self.errors += 1

    def _reset(self) -> None:
        """A re-based stream: every derived map is re-folded from zero (an
        event list appended to twice would double-count -- so nothing is)."""
        self._id_events.clear()
        self._key_events.clear()
        self._id_key.clear()
        self._key_ids.clear()
        self._id_game.clear()
        self._evicted.clear()
        self._settled.clear()
        self._d.clear()
        self._pos = {"atoms": 0, "verdicts": 0, "narration": 0}
        self._t = 0

    def _scan_atoms(self, recs: List[Dict[str, Any]]) -> None:
        """The atoms stream: identity (id -> key, id -> game), the eviction
        state (last-wins), m2 and the composite half of e3."""
        for rec in recs[self._pos["atoms"]:]:
            try:
                aid = rec.get("id")
                if not aid:
                    continue
                aid = str(aid)
                atom = rec.get("atom") or {}
                k = atom.get("key") or rec.get("key")
                if k and aid not in self._id_key:
                    self._id_key[aid] = str(k)
                    self._key_ids.setdefault(str(k), []).append(aid)
                if rec.get("game") is not None:
                    self._id_game[aid] = str(rec["game"])
                self._evicted[aid] = bool(rec.get(EVICTED_FIELD, False))
                # m2: the OBSERVATION-time conflict clause only. The stage-4
                # plan-wrong path's append carries `via: plan-wrong` and is
                # counted under m1 -- one event, one count.
                if (rec.get("ctx_conflict") is True
                        and rec.get(VIA_FIELD) != VIA_PLAN_WRONG):
                    self._add_id(aid, rec.get(EP_FIELD), M_CTX_CONFLICT)
                # e3 (composite): the CANDIDATE -> SETTLED transition. Later
                # superseding appends carry the flag forward; only the first
                # record that shows it is the event.
                if rec.get("settled") is True and aid not in self._settled:
                    self._settled[aid] = None
                    self._add_id(aid, rec.get(EP_FIELD), E_HELD)
            except Exception:
                self.errors += 1
        self._pos["atoms"] = len(recs)

    def _scan_verdicts(self, recs: List[Dict[str, Any]]) -> None:
        """The mint's verdict stream: e1 and e2, addressed by KEY."""
        for rec in recs[self._pos["verdicts"]:]:
            try:
                v = rec.get("verdict")
                kind = (E_MINT if v == V_MINT
                        else (E_REDERIVATION if v == V_REDERIVATION else None))
                if kind is None:
                    continue
                self._add_key(rec.get("key"), rec.get(EP_FIELD), kind)
            except Exception:
                self.errors += 1
        self._pos["verdicts"] = len(recs)

    def _scan_narration(self, recs: List[Dict[str, Any]]) -> None:
        """The PLAN point: the HELD half of e3 and all of m1, each addressed by
        the STEP ATOM ids the record carries. A world-moved abort carries a
        different gate and is never a misprediction (the plan's atoms were
        never given the state they bet on)."""
        for rec in recs[self._pos["narration"]:]:
            try:
                if rec.get("point") != PLAN_POINT:
                    continue
                mode, gate = rec.get("mode"), rec.get("gate")
                if mode == PLAN_HELD:
                    kind = E_HELD
                elif mode == ABORT_MODE and gate == VIA_PLAN_WRONG:
                    kind = M_PLAN_WRONG
                else:
                    continue
                steps = rec.get("steps")
                if not isinstance(steps, (list, tuple)):
                    continue
                for sid in steps:
                    self._add_id(str(sid), rec.get(EP_FIELD), kind)
            except Exception:
                self.errors += 1
        self._pos["narration"] = len(recs)

    def _add_id(self, aid: str, ep: Any, kind: str) -> None:
        e = _ep(ep)
        if e is None:
            self.unstamped += 1          # no clock, no event -- counted, never absorbed
            return
        self._id_events.setdefault(aid, []).append((e, kind))
        self._t = max(self._t, e)

    def _add_key(self, key: Any, ep: Any, kind: str) -> None:
        e = _ep(ep)
        if not key:
            return
        if e is None:
            self.unstamped += 1
            return
        self._key_events.setdefault(str(key), []).append((e, kind))
        self._t = max(self._t, e)

    # -- the number ----------------------------------------------------------

    def now(self) -> int:
        """t: the highest episode ordinal in the books. DERIVED (F6), never a
        clock -- two processes over the same books read the same t."""
        return int(self._t)

    def events(self, aid: str) -> List[Tuple[int, str]]:
        """Every standing event on this atom: its own, plus the verdict events
        addressed to its key. FIGURE 2: only this atom's own contacts with the
        ground appear here -- no other atom's outcome ever enters."""
        out = list(self._id_events.get(str(aid), ()))
        k = self._id_key.get(str(aid))
        if k:
            out.extend(self._key_events.get(k, ()))
        return out

    def decay(self, game: Optional[str] = None) -> Tuple[float, bool]:
        """(d, borrowed) for this game's population. d = 0.5^(1/g*) from the
        population's own median re-earn gap; BORROWED_DECAY below
        MIN_QUALIFYING qualifying atoms, flagged as borrowed."""
        key = str(game)
        hit = self._d.get(key)
        if hit is not None:
            return hit
        try:
            gaps: List[float] = []
            for aid in self._population(game):
                eps = sorted({e for e, kind in self.events(aid) if kind in EARN})
                if len(eps) < 2:
                    continue        # one earn event is not a cadence
                gaps.append(float(statistics.median(
                    [eps[i + 1] - eps[i] for i in range(len(eps) - 1)])))
            if len(gaps) < MIN_QUALIFYING:
                out = (BORROWED_DECAY, True)
            else:
                g_star = float(statistics.median(gaps))
                out = ((HALF_LIFE ** (1.0 / g_star), False) if g_star > 0.0
                       else (BORROWED_DECAY, True))
        except Exception:
            self.errors += 1
            out = (BORROWED_DECAY, True)
        self._d[key] = out
        return out

    def standing(self, aid: str, game: Optional[str] = None,
                 t: Optional[int] = None) -> float:
        """S(a, t): decayed earns minus decayed mispredictions, ONE rate on
        both sides. An event stamped ahead of t contributes undecayed (the
        exponent floors at 0) -- never amplified."""
        d = self.decay(game if game is not None
                       else self._id_game.get(str(aid)))[0]
        tt = self.now() if t is None else int(t)
        total = 0.0
        for ep, kind in self.events(aid):
            w = d ** max(0, tt - ep)
            total += w if kind in EARN else -w
        return float(total)

    def mis_decayed(self, aid: str, game: Optional[str] = None,
                    t: Optional[int] = None) -> float:
        """M_d(a): the decayed misprediction mass alone. > 0 iff this atom has
        a misprediction in its books at all -- the clause that makes silence
        un-evictable (Seat 3's ruling TAKEN)."""
        d = self.decay(game if game is not None
                       else self._id_game.get(str(aid)))[0]
        tt = self.now() if t is None else int(t)
        return float(sum(d ** max(0, tt - ep)
                         for ep, kind in self.events(aid) if kind in MISPREDICT))

    def is_evicted(self, aid: str) -> bool:
        """The LAST record's `evicted` flag (Gamma.get's last-wins rule)."""
        return bool(self._evicted.get(str(aid), False))

    def cause(self, aid: str) -> Optional[str]:
        """FIGURE 10's provenance: the EVENT KIND that last moved this atom --
        the thing a later reader locates the error by."""
        evs = self.events(aid)
        if not evs:
            return None
        return sorted(evs, key=lambda e: e[0])[-1][1]

    # -- RANK: the planner's visit order -------------------------------------

    def rank(self, gamma, ids: List[str], game: str) -> List[str]:
        """S descending, ties keeping today's lexical order, evicted ids
        dropped. THE ONLY consumer of S besides this module's own writer:
        it decides WHICH ATOM THE SEARCH REACHES FIRST, never a price and
        never a report (FIGURE 1)."""
        try:
            self.refresh(gamma)
            t = self.now()
            live = [a for a in ids if not self._evicted.get(str(a), False)]
            return sorted(live, key=lambda a: (-self.standing(a, game, t), str(a)))
        except Exception:
            self.errors += 1
            return list(ids)         # containment: never starve the search

    # -- EVICTION / RE-ENTRY: the one writer ---------------------------------

    def engage(self, gamma, game: str, level: int) -> Dict[str, Any]:
        """THE ENGAGEMENT SWEEP, called once per planner engagement (never
        inside plan_to_identity -- the search keeps treating Gamma as
        read-only). Recomputes tau over the atoms valid at (game, level) and
        writes the transitions it finds. Returns
        {"tau", "evicted": [...], "re_entered": [...], "n", "d", "borrowed"}
        -- the loop narrates it at the PLAN point."""
        out: Dict[str, Any] = {"tau": None, "evicted": [], "re_entered": [],
                               "n": 0, "d": BORROWED_DECAY, "borrowed": True}
        try:
            self.refresh(gamma)
            ids = valid_ids(gamma, game, level)
            out["n"] = len(ids)
            d, borrowed = self.decay(game)
            out["d"], out["borrowed"] = float(d), bool(borrowed)
            if not ids:
                return out
            t = self.now()
            scores = {aid: self.standing(aid, game, t) for aid in ids}
            tau = fence(list(scores.values()))
            out["tau"] = tau
            if tau is None:
                return out
            for aid in ids:
                s = scores[aid]
                was = bool(self._evicted.get(aid, False))
                if (not was and s < tau
                        and self.mis_decayed(aid, game, t) > 0.0):
                    # DISLODGING: wrong while its peers held. (When the world
                    # remaps and everything goes wrong together the fence moves
                    # with the population and this branch never fires -- that
                    # residual belongs to the rebinding discriminator.)
                    if self._write(gamma, aid, True, s, tau, t):
                        self.evictions += 1
                        out["evicted"].append(aid)
                elif (was and s >= tau
                        and self._write(gamma, aid, False, s, tau, t)):
                    self.reentries += 1
                    out["re_entered"].append(aid)
        except Exception:
            self.errors += 1
        return out

    def _write(self, gamma, aid: str, evicted: bool, s: float, tau: float,
               t: int) -> bool:
        """The superseding append (the archive law; Gamma.get last-wins): same
        id, same atom, the envelope carrying S / tau / ep / cause. NOTHING is
        deleted -- the mint's NOVELTY guard reads the whole stream, so an
        evicted atom's key stays known and no duplicate is ever re-minted."""
        try:
            topic = getattr(gamma, "TOPIC", ATOMS_TOPIC)
            recs = gamma.fabric.query("collective", topic,
                                      where=lambda r: r.get("id") == str(aid))
            if not recs:
                return False
            sup = dict(recs[-1])
            sup[EVICTED_FIELD] = bool(evicted)
            sup[S_FIELD] = float(s)
            sup[TAU_FIELD] = float(tau)
            sup[EP_FIELD] = int(t)
            sup[CAUSE_FIELD] = self.cause(aid)
            sup.pop("ctx_min", None)         # markers are event-scoped (the
            sup.pop("ctx_conflict", None)    # mint's own idiom): this is not
            sup.pop("settle", None)          # a mint event, so it claims none
            gamma.fabric.append("collective", topic, sup)
            self._evicted[str(aid)] = bool(evicted)
            return True
        except Exception:
            self.errors += 1
            return False

    # -- readouts (out-of-band; never a stream record, never a metric) -------

    def counters(self) -> Dict[str, int]:
        return {"evictions": int(self.evictions), "reentries": int(self.reentries),
                "unstamped": int(self.unstamped), "errors": int(self.errors),
                "atoms": len(self._id_key), "t": int(self._t)}

    def _population(self, game: Optional[str]) -> List[str]:
        """The atoms of one game, by the game their record was written under.
        game=None reads the whole book (the tests' constructed single-game
        case and the no-game caller)."""
        if game is None:
            return sorted(self._id_key)
        g = str(game)
        return sorted(a for a in self._id_key if self._id_game.get(a) == g)


# ── module-bottom helpers (the placement law: helpers below their organ) ─────

def valid_ids(gamma, game: str, level: int) -> List[str]:
    """Gamma's stored entries for the game, still valid at (game, level),
    sorted lexically. THE ONE DEFINITION of the candidate population: the
    planner's `_candidate_ids` and this module's eviction sweep read the same
    set, so the fence is computed over exactly the atoms the search would
    otherwise have visited. Byte-identical to the pre-build `_candidate_ids`."""
    topic = getattr(gamma, "TOPIC", ATOMS_TOPIC)
    recs = gamma.fabric.query("collective", topic,
                              where=lambda r: r.get("game") == str(game))
    ids = sorted({r["id"] for r in recs if r.get("id") is not None})
    return [aid for aid in ids if gamma.valid_in(aid, game, level)]


def fence(values: List[float]) -> Optional[float]:
    """Tukey's LOWER fence over the population's own S: Q1 - 1.5*IQR. PURE.
    None on an empty population. A population whose middle 50% is identical
    has IQR 0 and therefore tau = Q1 -- which is exactly the R4 Assumption
    case: every atom equally wrong sits AT the fence, never below it."""
    vals = [float(v) for v in values]
    if not vals:
        return None
    q1 = float(np.percentile(vals, 25))
    q3 = float(np.percentile(vals, 75))
    return q1 - IQR_FENCE * (q3 - q1)


def episode_of(mint: Any) -> Optional[int]:
    """The A3-4 episode ordinal in force, read from the mint that stamps it --
    the ONE clock, never a second counter. None when there is no mint to read
    (the event is then unstamped and, by the law above, not counted)."""
    try:
        ep = getattr(mint, "_ep", None)
        return None if ep is None else int(ep)
    except Exception:
        return None


def _ep(ep: Any) -> Optional[int]:
    """A readable episode ordinal, or None. Total; never raises."""
    if ep is None or isinstance(ep, bool):
        return None
    try:
        return int(ep)
    except (TypeError, ValueError):
        return None
