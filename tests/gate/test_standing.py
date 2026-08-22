"""R3/R4 GATE (PREREG_STANDING_HALF_LIFE_ATOMS.md): STANDING AT THE ATOM GRAIN.

The build under test: engines/egocentric/standing.py (the event fold, the decay
derived from the population's own re-earn cadence, the Tukey fence, the ONE
eviction/re-entry writer), planner._candidate_ids ranking by S and dropping
evicted ids, scheduler.PlannerScheduler owning the book, GATE B's third
change-mark component, and the four event-write seams: the mint's reinstate
(ep + the `via` disjointness marker), the composite settle's ep, and the two
PLAN-point narration records (`held`, and `steps`+`ep` on the routed abort).

THE PINNED FALSIFIERS, as gated here -- BY COUNTING EPISODES, NEVER WALL-CLOCK
(the canon's no-threshold-in-wall-clock rule; tests/gate/
test_fabric_next_seq_cache.py is the exemplar; the clock here is the A3-4
episode ordinal and nothing else):
  F1  DEMOTION: an atom that mispredicts on successive driven steps ranks below
      every held atom, leaves _candidate_ids once S < tau, and the planner's
      next search NEVER APPLIES IT (counted at apply_effect, not inferred).
  F2  RECOVERY: rederivation verdicts (FIGURE 5 -- "the answer was already
      known" STRENGTHENS) carry the same atom back over the fence; the append
      carries evicted: false; GATE B reopens through the loop's own mark.
  F3  SILENCE NEVER EVICTS: an atom with one mint and no further event sinks in
      rank over 3 AND 10 half-lives and is never evicted -- asserted WITH its
      known-positive (it is BELOW the fence the whole time; only M_d = 0 saves
      it), so the clause is doing the work and not the construction.
  F4  THE STREAM NEVER LOSES A RECORD: the atoms-stream count is monotone
      across eviction and re-entry, Gamma.get of an evicted id still returns
      the atom, and the mint's NOVELTY guard still knows its key.
  F5  THE SET REFLECTS EXCLUSION: plan_to_identity on a frame where ONLY the
      evicted atom could anchor returns ANCHOR_MISS -- with the known-positive
      that the same call with standing=None returns a plan.
  F6  REPLAY: an incrementally-folded book and a cold book over the same books
      compute identical S, identical d and identical tau for every atom.
  F7  ONE EVENT, ONE COUNT: the stage-4 plan-wrong writes a ctx_conflict AND a
      ledger increment for one event and raises M by exactly 1; the
      observation-time clause (no `via`) is the known-positive that counts m2.
  R4  a population where EVERY atom mispredicts once evicts none (the
      Assumption case); the same population with one atom mispredicting five
      times evicts exactly that one.
  RIDER (Seat 3 + Seat 4, binding): DECAY BITES -- a decayed atom is REACHED
      LATER than an undecayed twin. Asserted as an ORDERING OF REACH (the
      application index at apply_effect, and which plan the search returns
      under the budget), never as a comparison of S; with the lexical-order
      control that pins standing, not the construction, as the cause.

THE LAWS (figures/*.svg via record/corpus/FIGURES_TEXT_DIGEST.md):
  FIGURE 1  S ranks retrieval and prices nothing: asserted BY SOURCE (the sink
            identity below -- no pricing/reporting module reads it).
  FIGURE 2  the anchor does not update: asserted as no mutual update between
            atoms (one atom's events never move another's S).
  FIGURE 5  rederivation strengthens: asserted in F2.
  FIGURE 10 provenance: every eviction/re-entry append carries S, tau, ep and
            the event kind that caused it.

Seeded with a FIXED CONSTANT (the build date), never a clock. No game id,
colour or object identity: every frame here is constructed.
"""
from __future__ import annotations

import ast
import glob
import os
import sys
from types import SimpleNamespace

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl  # noqa: E402
from engines.egocentric import composer as C  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import mint as M  # noqa: E402
from engines.egocentric import narration as NA  # noqa: E402
from engines.egocentric import planner as P  # noqa: E402
from engines.egocentric import scheduler as SCH  # noqa: E402
from engines.egocentric import standing as S  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402

SEED = 20260821          # fixed constant (the build date) -- deterministic forever
GAME, LEVEL = "g1", 1


# ── constructions ─────────────────────────────────────────────────────────────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a",
                                   kin_key="v4"))


def _atom(ctx, out, key, action=6):
    """An untyped EFFECT atom: context patch in, after patch out."""
    ctx_l = [[int(v) for v in row] for row in ctx]
    out_l = [[int(v) for v in row] for row in out]
    return {"kind": "EFFECT", "arity": 2, "key": key, "action": action,
            "context": ctx_l, "transform": {"before": ctx_l, "after": out_l},
            "changed": int((np.asarray(ctx) != np.asarray(out)).sum())}


def _verdict(g, verdict, key, ep, game=GAME, level=LEVEL):
    """One mint-verdict record in the mint's own shape (the e1/e2 source)."""
    g.fabric.append("collective", M.VERDICT_TOPIC,
                    {"verdict": str(verdict), "game": str(game),
                     "level": int(level), "key": str(key), "ep": int(ep),
                     "reason": str(verdict)})


def _spine(g, game=GAME):
    return NA.NarrationSpine(g.fabric, game=game)


def _held(spine, steps, ep):
    """The PLAN-point HELD record, written with the loop's own call."""
    return spine.plan(S.PLAN_HELD, S.HELD_GATE, rng=NA.EP,
                      extra={"steps": [str(s) for s in steps], "ep": int(ep)})


def _wrong(spine, steps, ep, route=SCH.ABORT_PLAN_WRONG):
    """The PLAN-point routed-abort record, written with the loop's own call."""
    return spine.plan("abort", route, rng=NA.EP,
                      extra={"steps": [str(s) for s in steps], "ep": int(ep)})


def _book(g):
    b = S.StandingBook()
    b.refresh(g)
    return b


def _records(g, aid=None):
    rows = g.fabric.query("collective", g.TOPIC)
    return rows if aid is None else [r for r in rows if r.get("id") == aid]


def _population(tmp_path, name, n=5, ep=0):
    """`n` atoms, each minted once at episode `ep` -- identical standing by
    construction, which is the only way a later difference is attributable."""
    g = _gamma(tmp_path, name)
    ids = []
    for i in range(n):
        key = "eff-%02d" % i
        ids.append(g.add(_atom([[i + 1]], [[9]], key), GAME, LEVEL))
        _verdict(g, "mint", key, ep)
    return g, ids


def _apply_log(monkeypatch):
    """THE REACH INSTRUMENT: the ordered list of atom keys the search actually
    applied. Counting, never timing; the planner's own apply seam."""
    log = []
    orig = P.apply_effect

    def counting(atom, state):
        log.append(str((atom or {}).get("key")))
        return orig(atom, state)

    monkeypatch.setattr(P, "apply_effect", counting)
    return log


def _ns(tmp_path, name, g):
    """The loop namespace at the standing seams -- enough real state for
    _w2b_engage / _w2b_abort / _std_held / _std_sweep / _w2b_mark to run the
    LOOP'S OWN code paths."""
    return SimpleNamespace(
        _ego_fabric=g.fabric, _game_id=GAME, _actions_taken=0,
        _ego_agent_id="a", _ego_level=LEVEL,
        _w2b_sched=SCH.PlannerScheduler(), _w2b_narr=None, _w2b_driven=None,
        _w2b_key=None, _w3d_chain=None,
        _w4c_counters={"mint_passed": 0}, _narr_import_n=0,
        _narration=_spine(g), _narr_slots=None,
        _atom_verified={}, _residual_router=None,
        _plan_gate=None, _narr_settle=None, _narr_mint=None, _prev_frame=None,
        _gamma=g, _mdl_mint=MDLMint(g),
        _ego_frontier_book=None, _ego_harvest_cache=None,
        _perceiver=SimpleNamespace(_to_numpy=np.asarray))


def _plan_records(g):
    return [r for r in g.fabric.query("personal", NA.TOPIC)
            if r.get("point") == NA.PLAN]


# ═════════════════════════════════════════════════════════════════════════════
# F1 · DEMOTION -- rank, exclusion, and the search that never applies it
# ═════════════════════════════════════════════════════════════════════════════

class TestF1Demotion:

    def _wrong_atom(self, tmp_path, name, misses=5):
        g, ids = _population(tmp_path, name, n=5, ep=0)
        sp = _spine(g)
        bad = ids[0]
        for k in range(misses):
            _wrong(sp, [bad], ep=1 + k)
        return g, ids, bad

    def test_the_mispredicting_atom_ranks_below_every_held_atom(self, tmp_path):
        g, ids, bad = self._wrong_atom(tmp_path, "f1rank")
        b = _book(g)
        ranked = b.rank(g, ids, GAME)
        assert ranked[-1] == bad, (
            "F1 FALSIFIED: the mispredicting atom did not rank last -- %r"
            % (ranked,))
        assert sorted(ranked) == sorted(ids), "rank dropped an un-evicted atom"
        assert ranked[:-1] == sorted(ids[1:]), (
            "ties must keep today's lexical order -- %r" % (ranked,))

    def test_it_leaves_the_candidate_set_once_S_is_below_the_fence(self, tmp_path):
        g, ids, bad = self._wrong_atom(tmp_path, "f1evict")
        b = _book(g)
        assert sorted(P._candidate_ids(g, GAME, LEVEL, b)) == sorted(ids), (
            "construction: nothing is excluded before the sweep")
        out = b.engage(g, GAME, LEVEL)
        assert out["evicted"] == [bad], (
            "F1 FALSIFIED: the sweep evicted %r (tau=%r)"
            % (out["evicted"], out["tau"]))
        assert bad not in P._candidate_ids(g, GAME, LEVEL, b), (
            "F1 FALSIFIED: an evicted id is still a candidate")
        assert bad in P._candidate_ids(g, GAME, LEVEL, None), (
            "the UNDO: standing=None must still return every valid id")

    def test_the_next_search_never_applies_the_evicted_atom(
            self, tmp_path, monkeypatch):
        """Exclusion is real work not done, counted at the apply seam."""
        g, ids, bad = self._wrong_atom(tmp_path, "f1apply")
        b = _book(g)
        b.engage(g, GAME, LEVEL)
        ws = np.zeros((5, 5), dtype=int)
        for i in range(5):
            ws[0, i] = i + 1                       # every atom's context is present
        ref = ws.copy()
        ref[0, 4] = 9
        log = _apply_log(monkeypatch)
        P.plan_to_identity(ws, ref, g, game=GAME, level=LEVEL, budget=100,
                           cost_per_action=1, standing=b)
        assert "eff-00" not in log, (
            "F1 FALSIFIED: the evicted atom was applied %d time(s)"
            % log.count("eff-00"))
        assert log, "construction: the search must have applied something"


# ═════════════════════════════════════════════════════════════════════════════
# F2 · RECOVERY -- rederivation strengthens (FIGURE 5), and GATE B reopens
# ═════════════════════════════════════════════════════════════════════════════

class TestF2Recovery:

    def _evicted(self, tmp_path, name):
        g, ids = _population(tmp_path, name, n=5, ep=0)
        sp = _spine(g)
        for k in range(5):
            _wrong(sp, [ids[0]], ep=1 + k)
        b = _book(g)
        assert b.engage(g, GAME, LEVEL)["evicted"] == [ids[0]]
        return g, ids, b

    def test_rederivations_carry_it_back_and_the_append_says_so(self, tmp_path):
        g, ids, b = self._evicted(tmp_path, "f2back")
        before = b.standing(ids[0], GAME)
        for k in range(8):                          # FIGURE 5: e2 STRENGTHENS
            _verdict(g, "rederivation", "eff-00", ep=6 + k)
        b.refresh(g)
        assert b.standing(ids[0], GAME) > before, (
            "FIGURE 5 FALSIFIED: rederivation did not strengthen the entry")
        out = b.engage(g, GAME, LEVEL)
        assert out["re_entered"] == [ids[0]], (
            "F2 FALSIFIED: re-entry did not fire (tau=%r, S=%r)"
            % (out["tau"], b.standing(ids[0], GAME)))
        last = _records(g, ids[0])[-1]
        assert last[S.EVICTED_FIELD] is False, (
            "F2 FALSIFIED: the re-entry append must carry evicted: false")
        assert ids[0] in P._candidate_ids(g, GAME, LEVEL, b)

    def test_the_reentry_append_carries_its_provenance(self, tmp_path):
        """FIGURE 10: S, tau, ep and the event kind that caused it -- a later
        reader locates the error rather than feels it."""
        g, ids, b = self._evicted(tmp_path, "f2prov")
        ev = _records(g, ids[0])[-1]
        for f in (S.EVICTED_FIELD, S.S_FIELD, S.TAU_FIELD, S.EP_FIELD,
                  S.CAUSE_FIELD):
            assert f in ev, "FIGURE 10 FALSIFIED: %s missing from the append" % f
        assert ev[S.CAUSE_FIELD] == S.M_PLAN_WRONG, (
            "the cause must name the EVENT KIND that last moved the atom")
        assert ev[S.S_FIELD] < ev[S.TAU_FIELD]
        assert ev["atom"]["key"] == "eff-00", (
            "the append must carry the atom forward, not replace it")

    def test_a_reentry_reopens_gate_b_through_the_loops_own_mark(self, tmp_path):
        """The third change-mark component, read through cognitive_loop's own
        _w2b_mark -- never a mirror of it."""
        g, ids = _population(tmp_path, "f2gateb", n=5, ep=0)
        ns = _ns(tmp_path, "f2gateb", g)
        sched = ns._w2b_sched
        mark0 = cl._w2b_mark(ns)
        assert len(mark0) == 3 and mark0[2] == 0
        assert sched.decide(GAME, LEVEL, "k", 0.0, mark0)["engage"] is True
        sched.note_attempt(GAME, LEVEL, "k", mark0)
        assert sched.decide(GAME, LEVEL, "k", 0.0, cl._w2b_mark(ns))["engage"] is False, (
            "construction: an unchanged world must close GATE B")
        sched.standing.reentries += 1                # the sweep's own counter
        mark1 = cl._w2b_mark(ns)
        assert mark1[2] == 1, "the mark did not carry the re-entry"
        assert sched.decide(GAME, LEVEL, "k", 0.0, mark1)["engage"] is True, (
            "F2 FALSIFIED: a re-entry did not reopen GATE B")

    def test_an_eviction_alone_does_not_reopen_the_gate(self, tmp_path):
        """The stated asymmetry: a strictly smaller set returns the same
        nothing, so eviction is not a world change for the search."""
        g, ids = _population(tmp_path, "f2asym", n=5, ep=0)
        ns = _ns(tmp_path, "f2asym", g)
        sched = ns._w2b_sched
        sched.note_attempt(GAME, LEVEL, "k", cl._w2b_mark(ns))
        sched.standing.evictions += 3
        assert sched.decide(GAME, LEVEL, "k", 0.0,
                            cl._w2b_mark(ns))["engage"] is False


# ═════════════════════════════════════════════════════════════════════════════
# F3 · SILENCE NEVER EVICTS -- Seat 3's ruling, TAKEN
# ═════════════════════════════════════════════════════════════════════════════

class TestF3SilenceNeverEvicts:

    def _silent(self, tmp_path, name, horizon):
        """One atom minted at ep 0 and never touched again; four peers that go
        on earning right up to the horizon."""
        g, ids = _population(tmp_path, name, n=5, ep=0)
        sp = _spine(g)
        for aid, key in zip(ids[1:], ["eff-01", "eff-02", "eff-03", "eff-04"],
                            strict=True):
            _verdict(g, "rederivation", key, ep=horizon)
            _held(sp, [aid], ep=horizon)
        return g, ids[0], _book(g)

    def _half_lives(self, n):
        """n half-lives of the BORROWED rate, in episodes -- counted from the
        rate itself, never a literal."""
        import math
        return int(math.ceil(n * math.log(0.5) / math.log(S.BORROWED_DECAY)))

    def test_three_half_lives(self, tmp_path):
        h = self._half_lives(3)
        g, silent, b = self._silent(tmp_path, "f3a", h)
        out = b.engage(g, GAME, LEVEL)
        assert b.rank(g, P._candidate_ids(g, GAME, LEVEL, None), GAME)[-1] == silent, (
            "the silent atom must SINK in rank")
        assert b.standing(silent, GAME) < out["tau"], (
            "KNOWN-POSITIVE FAILED: the silent atom is not below the fence, so "
            "this test is not testing the M_d clause")
        assert b.mis_decayed(silent, GAME) == 0.0
        assert out["evicted"] == [], (
            "F3 FALSIFIED: silence evicted %r" % (out["evicted"],))
        assert silent in P._candidate_ids(g, GAME, LEVEL, b)

    def test_ten_half_lives(self, tmp_path):
        h = self._half_lives(10)
        g, silent, b = self._silent(tmp_path, "f3b", h)
        out = b.engage(g, GAME, LEVEL)
        assert b.standing(silent, GAME) < out["tau"]
        assert out["evicted"] == [], (
            "F3 FALSIFIED at 10 half-lives: %r" % (out["evicted"],))
        assert not b.is_evicted(silent)
        assert len(_records(g, silent)) == 1, (
            "silence must write NOTHING -- the window is unbounded")


# ═════════════════════════════════════════════════════════════════════════════
# F4 · THE STREAM NEVER LOSES A RECORD
# ═════════════════════════════════════════════════════════════════════════════

class TestF4TheStreamNeverLosesARecord:

    def test_monotone_across_eviction_and_reentry(self, tmp_path):
        g, ids = _population(tmp_path, "f4", n=5, ep=0)
        sp = _spine(g)
        for k in range(5):
            _wrong(sp, [ids[0]], ep=1 + k)
        counts = [len(_records(g))]
        b = _book(g)
        b.engage(g, GAME, LEVEL)
        counts.append(len(_records(g)))
        for k in range(8):
            _verdict(g, "rederivation", "eff-00", ep=6 + k)
        b.engage(g, GAME, LEVEL)
        counts.append(len(_records(g)))
        assert counts == sorted(counts) and counts[0] < counts[-1], (
            "F4 FALSIFIED: the atoms stream is not monotone -- %r" % (counts,))
        assert len(_records(g, ids[0])) == 3, (
            "mint + eviction + re-entry: three records, none replaced")

    def test_gamma_get_still_returns_an_evicted_atom(self, tmp_path):
        g, ids = _population(tmp_path, "f4get", n=5, ep=0)
        sp = _spine(g)
        for k in range(5):
            _wrong(sp, [ids[0]], ep=1 + k)
        b = _book(g)
        b.engage(g, GAME, LEVEL)
        atom = g.get(ids[0])
        assert atom is not None and atom.get("key") == "eff-00", (
            "F4 FALSIFIED: Gamma.get lost an evicted atom")

    def test_the_novelty_guard_still_knows_the_key(self, tmp_path):
        """Nothing is deleted, so no duplicate can ever be re-minted."""
        g, ids = _population(tmp_path, "f4key", n=5, ep=0)
        sp = _spine(g)
        for k in range(5):
            _wrong(sp, [ids[0]], ep=1 + k)
        b = _book(g)
        b.engage(g, GAME, LEVEL)
        assert "eff-00" in MDLMint(g)._known_keys(), (
            "F4 FALSIFIED: eviction hid a key from the NOVELTY guard")


# ═════════════════════════════════════════════════════════════════════════════
# F5 · THE SET REFLECTS EXCLUSION -- ANCHOR_MISS, not a plan
# ═════════════════════════════════════════════════════════════════════════════

class TestF5TheSetReflectsExclusion:

    def _world(self, tmp_path, name):
        """One atom that CAN anchor here (it is the one that will be evicted)
        and two whose colour is not on this frame at all."""
        g = _gamma(tmp_path, name)
        only = g.add(_atom([[3]], [[9]], "eff-only"), GAME, LEVEL)
        others = [g.add(_atom([[7]] * (i + 1), [[8]] * (i + 1),
                              "eff-x%d" % i), GAME, LEVEL)
                  for i in range(5)]
        _verdict(g, "mint", "eff-only", 0)
        for k in ["eff-x%d" % i for i in range(5)]:
            _verdict(g, "mint", k, 0)
            for e in range(1, 6):
                _verdict(g, "rederivation", k, e)
        sp = _spine(g)
        for k in range(6):
            _wrong(sp, [only], ep=1 + k)
        ws = np.zeros((4, 4), dtype=int)
        ws[1, 1] = 3
        ref = ws.copy()
        ref[1, 1] = 9
        return g, only, others, ws, ref

    def test_the_evicted_atoms_frame_returns_anchor_miss(self, tmp_path):
        g, only, others, ws, ref = self._world(tmp_path, "f5")
        plan = P.plan_to_identity(ws, ref, g, game=GAME, level=LEVEL,
                                  budget=100, cost_per_action=1, standing=None)
        assert plan == {"steps": [only], "feasible": True}, (
            "KNOWN-POSITIVE FAILED: without standing this frame must plan")
        b = _book(g)
        assert b.engage(g, GAME, LEVEL)["evicted"] == [only]
        out = P.plan_to_identity(ws, ref, g, game=GAME, level=LEVEL,
                                 budget=100, cost_per_action=1, standing=b)
        assert out is None and P.last_reason() == "ANCHOR_MISS", (
            "F5 FALSIFIED: exclusion was cosmetic -- got %r / %r"
            % (out, P.last_reason()))


# ═════════════════════════════════════════════════════════════════════════════
# F6 · REPLAY -- two processes over the same books agree
# ═════════════════════════════════════════════════════════════════════════════

class TestF6Replay:

    def _books(self, tmp_path, name):
        """`warm` is folded incrementally as the streams grow (a live worker);
        `cold` is a fresh instance over the finished books (a restart)."""
        g, ids = _population(tmp_path, name, n=6, ep=0)
        warm = S.StandingBook()
        sp = _spine(g)
        for step in range(6):
            _verdict(g, "rederivation", "eff-0%d" % (step % 6), ep=step + 1)
            _wrong(sp, [ids[(step + 1) % 6]], ep=step + 1)
            _held(sp, [ids[(step + 2) % 6]], ep=step + 2)
            warm.refresh(g)
        cold = _book(g)
        return g, ids, warm, cold

    def test_identical_S_for_every_atom(self, tmp_path):
        g, ids, warm, cold = self._books(tmp_path, "f6")
        assert warm.now() == cold.now()
        for aid in ids:
            assert warm.standing(aid, GAME) == cold.standing(aid, GAME), (
                "F6 FALSIFIED: %s warm=%r cold=%r"
                % (aid, warm.standing(aid, GAME), cold.standing(aid, GAME)))
            assert warm.events(aid) == cold.events(aid)

    def test_identical_decay_and_fence(self, tmp_path):
        g, ids, warm, cold = self._books(tmp_path, "f6b")
        assert warm.decay(GAME) == cold.decay(GAME)
        f_w = S.fence([warm.standing(a, GAME) for a in ids])
        f_c = S.fence([cold.standing(a, GAME) for a in ids])
        assert f_w == f_c
        assert warm.rank(g, ids, GAME) == cold.rank(g, ids, GAME)

    def test_a_rebased_stream_refolds_rather_than_double_counting(self, tmp_path):
        """The janitor rewrote the stream: the incremental fold must reset,
        never append a second copy of every event."""
        g, ids, warm, cold = self._books(tmp_path, "f6c")
        before = warm.events(ids[0])
        path = os.path.join(str(tmp_path / "f6c"), "collective",
                            M.VERDICT_TOPIC + ".jsonl")
        with open(path, "rb") as fh:
            lines = fh.read().splitlines(keepends=True)
        with open(path, "wb") as fh:
            fh.writelines(lines[:2])
        g.fabric.reload_seqs()
        warm.refresh(g)
        assert len(warm.events(ids[0])) <= len(before), (
            "F6 FALSIFIED: a re-based stream double-counted events")
        assert warm.events(ids[0]) == _book(g).events(ids[0])


# ═════════════════════════════════════════════════════════════════════════════
# F7 · ONE EVENT, ONE COUNT -- the stage-4 disjointness marker
# ═════════════════════════════════════════════════════════════════════════════

class TestF7OneEventOneCount:

    def _conflictable(self, tmp_path, name):
        """An atom whose context was loosened (context_full preserved), so the
        conflict clause has something to reinstate."""
        g = _gamma(tmp_path, name)
        atom = _atom([[3, 0], [0, 0]], [[9, 0], [0, 0]], "eff-c")
        atom["context_full"] = [[3, 5], [0, 0]]
        atom["context"] = [[3, E.DONT_CARE], [0, 0]]
        atom["transform"]["before"] = atom["context"]
        aid = g.add(atom, GAME, LEVEL)
        _verdict(g, "mint", "eff-c", 0)
        frame = np.zeros((4, 4), dtype=int)
        frame[0, 0] = 3
        frame[0, 1] = 7                       # differs from context_full: a discriminator
        return g, aid, frame

    def test_a_stage4_plan_wrong_raises_M_by_exactly_one(self, tmp_path):
        g, aid, frame = self._conflictable(tmp_path, "f7")
        mint = MDLMint(g)
        mint._ep = 4
        base = _book(g).mis_decayed(aid, GAME)
        assert base == 0.0, "construction: no misprediction yet"
        # the loop's stage-4 pair, written exactly as _w3d_abort writes it
        out = C.conflict_component(mint, g, aid, frame)
        assert out["conflicted"] is True, "construction: %r" % (out,)
        _wrong(_spine(g), [aid], ep=4)
        b = _book(g)
        kinds = [k for _ep, k in b.events(aid) if k in S.MISPREDICT]
        assert kinds == [S.M_PLAN_WRONG], (
            "F7 FALSIFIED: one event counted as %r" % (kinds,))
        rec = _records(g, aid)[-1]
        assert rec.get(S.VIA_FIELD) == S.VIA_PLAN_WRONG
        assert rec.get("ctx_conflict") is True and rec.get(S.EP_FIELD) == 4

    def test_the_observation_time_clause_is_the_known_positive(self, tmp_path):
        """No `via`: the SAME write counts as m2, so the marker is what
        separates the paths -- not the absence of a write."""
        g, aid, frame = self._conflictable(tmp_path, "f7kp")
        mint = MDLMint(g)
        mint._ep = 4
        rec = _records(g, aid)[-1]
        atom = rec["atom"]
        full = np.asarray(atom["context_full"])
        dist = np.asarray(atom["context"]) == E.DONT_CARE
        mint._reinstate(aid, rec, atom, full, dist)          # via=None
        b = _book(g)
        kinds = [k for _ep, k in b.events(aid) if k in S.MISPREDICT]
        assert kinds == [S.M_CTX_CONFLICT], (
            "KNOWN-POSITIVE FAILED: the unmarked clause must count as m2 -- %r"
            % (kinds,))
        assert _records(g, aid)[-1].get(S.VIA_FIELD) is None


# ═════════════════════════════════════════════════════════════════════════════
# R4 · THE ASSUMPTION CASE vs THE DISLODGING CASE
# ═════════════════════════════════════════════════════════════════════════════

class TestR4TheFenceIsTheDiscriminator:

    def test_every_atom_wrong_once_evicts_none(self, tmp_path):
        """BROKEN-rebinding: the world remapped, the population's S dropped
        together, the fence moved with it. That residual belongs to the
        rebinding discriminator, not to eviction."""
        g, ids = _population(tmp_path, "r4a", n=6, ep=0)
        sp = _spine(g)
        for aid in ids:
            _wrong(sp, [aid], ep=1)
        b = _book(g)
        out = b.engage(g, GAME, LEVEL)
        assert out["evicted"] == [], (
            "R4 FALSIFIED: the Assumption case evicted %r" % (out["evicted"],))
        assert all(b.mis_decayed(a, GAME) > 0 for a in ids), (
            "KNOWN-POSITIVE FAILED: every atom must carry a misprediction, or "
            "the M_d clause and not the fence is doing the work")

    def test_one_atom_wrong_five_times_evicts_exactly_that_one(self, tmp_path):
        g, ids = _population(tmp_path, "r4b", n=6, ep=0)
        sp = _spine(g)
        for aid in ids:
            _wrong(sp, [aid], ep=1)
        for k in range(4):
            _wrong(sp, [ids[2]], ep=2 + k)
        b = _book(g)
        out = b.engage(g, GAME, LEVEL)
        assert out["evicted"] == [ids[2]], (
            "R4 FALSIFIED: expected exactly %r, got %r" % (ids[2], out["evicted"]))


# ═════════════════════════════════════════════════════════════════════════════
# THE RIDER · DECAY BITES -- the decayed atom is REACHED LATER
# ═════════════════════════════════════════════════════════════════════════════

class TestTheRiderDecayBites:

    def _twins(self, tmp_path, name):
        """Two atoms that are INDISTINGUISHABLE to the search: both anchor at
        the same cell, both reach the reference in one step. Only standing can
        separate them, and the lexical control below proves it does."""
        g = _gamma(tmp_path, name)
        a = g.add(_atom([[3]], [[9]], "eff-a"), GAME, LEVEL)
        b = g.add(_atom([[3, 0]], [[9, 0]], "eff-b"), GAME, LEVEL)
        for k in ("eff-a", "eff-b"):
            _verdict(g, "mint", k, 0)
        ws = np.zeros((4, 4), dtype=int)
        ws[1, 1] = 3
        ref = ws.copy()
        ref[1, 1] = 9
        return g, a, b, ws, ref

    def _reach(self, g, ws, ref, book, monkeypatch):
        log = _apply_log(monkeypatch)
        plan = P.plan_to_identity(ws, ref, g, game=GAME, level=LEVEL,
                                  budget=100, cost_per_action=1, standing=book)
        return plan, log

    def test_the_lexical_control(self, tmp_path, monkeypatch):
        """standing=None: the search reaches the lexically-first twin. This is
        the control -- if it ever changes, the flip below proves nothing."""
        g, a, b, ws, ref = self._twins(tmp_path, "riderctl")
        plan, log = self._reach(g, ws, ref, None, monkeypatch)
        assert plan == {"steps": [a], "feasible": True}
        assert log[0] == "eff-a"

    def test_the_decayed_twin_is_reached_later(self, tmp_path, monkeypatch):
        g, a, b, ws, ref = self._twins(tmp_path, "riderlate")
        _wrong(_spine(g), [a], ep=1)               # a decays; b does not
        book = _book(g)
        plan, log = self._reach(g, ws, ref, book, monkeypatch)
        assert log.index("eff-b") < (log.index("eff-a") if "eff-a" in log
                                     else len(log)), (
            "RIDER FALSIFIED: the decayed twin was not reached later -- %r"
            % (log,))
        assert plan == {"steps": [b], "feasible": True}, (
            "RIDER FALSIFIED: sinking in rank had no consequence -- the search "
            "still returned the decayed atom's plan (%r)" % (plan,))

    def test_the_ordering_follows_standing_and_not_the_construction(
            self, tmp_path, monkeypatch):
        """The mirror: penalise the OTHER twin and the reach order flips back.
        Asserted as reach, never as a comparison of S."""
        g, a, b, ws, ref = self._twins(tmp_path, "riderflip")
        _wrong(_spine(g), [b], ep=1)
        book = _book(g)
        plan, log = self._reach(g, ws, ref, book, monkeypatch)
        assert log[0] == "eff-a"
        assert plan == {"steps": [a], "feasible": True}

    def test_the_weaker_twins_application_never_happens_under_the_budget(
            self, tmp_path, monkeypatch):
        """The budget is what turns 'later' into 'not at all': the search
        returns on the first solution, so the decayed twin is never applied."""
        g, a, b, ws, ref = self._twins(tmp_path, "riderbudget")
        _wrong(_spine(g), [a], ep=1)
        book = _book(g)
        _plan, log = self._reach(g, ws, ref, book, monkeypatch)
        assert "eff-a" not in log, (
            "RIDER FALSIFIED: the decayed twin was still applied -- %r" % (log,))


# ═════════════════════════════════════════════════════════════════════════════
# THE DECAY RULE -- derived from the population, borrowed only when it must be
# ═════════════════════════════════════════════════════════════════════════════

class TestTheDecayRule:

    def test_below_the_floor_the_rate_is_reported_borrowed(self, tmp_path):
        g, ids = _population(tmp_path, "dk1", n=5, ep=0)
        d, borrowed = _book(g).decay(GAME)
        assert (d, borrowed) == (S.BORROWED_DECAY, True), (
            "a median over fewer than %d atoms is not a distribution"
            % S.MIN_QUALIFYING)

    def test_the_population_supplies_its_own_rate(self, tmp_path):
        """MIN_QUALIFYING atoms, each re-earned every 4 episodes: the half-life
        is one typical re-earn interval, so d = 0.5^(1/4)."""
        g = _gamma(tmp_path, "dk2")
        for i in range(S.MIN_QUALIFYING):
            key = "eff-%03d" % i
            g.add(_atom([[(i % 8) + 1]], [[9]], key), GAME, LEVEL)
            for step in range(3):
                _verdict(g, "mint" if step == 0 else "rederivation", key,
                         ep=step * 4)
        d, borrowed = _book(g).decay(GAME)
        assert borrowed is False, "the population's own cadence was not used"
        assert abs(d - 0.5 ** (1.0 / 4.0)) < 1e-12, (
            "d must be 0.5^(1/g*) with g* = 4 -- got %r" % (d,))

    def test_the_pinned_knobs(self):
        assert S.MIN_QUALIFYING == 30          # PINNED by the prereg
        assert S.IQR_FENCE == 1.5              # PINNED by the prereg
        assert S.BORROWED_DECAY == 0.97        # BORROWED (prestige's own rate)

    def test_both_sides_decay_at_the_same_rate(self, tmp_path):
        """R4 binds failures too: an old misprediction fades exactly as an old
        confirmation does. Asserted as an exact cancellation."""
        g = _gamma(tmp_path, "dk3")
        aid = g.add(_atom([[3]], [[9]], "eff-s"), GAME, LEVEL)
        _verdict(g, "mint", "eff-s", 0)
        _wrong(_spine(g), [aid], ep=0)
        b = _book(g)
        assert abs(b.standing(aid, GAME)) < 1e-12, (
            "an earn and a misprediction at the same episode must cancel")
        _verdict(g, "rederivation", "eff-s", 50)
        _wrong(_spine(g), [aid], ep=50)
        b = _book(g)
        assert abs(b.standing(aid, GAME)) < 1e-12, (
            "the same pair 50 episodes later must still cancel -- one rate")


# ═════════════════════════════════════════════════════════════════════════════
# THE LOOP SEAMS -- the events are written by the loop, not only constructible
# ═════════════════════════════════════════════════════════════════════════════

class TestTheLoopSeams:

    def test_a_landed_step_is_recorded_as_an_earn_event(self, tmp_path):
        """The abort router's no-abort branch recorded NOTHING until this
        build. Driven through cognitive_loop._w2b_abort itself."""
        g, ids = _population(tmp_path, "seam1", n=3, ep=0)
        ns = _ns(tmp_path, "seam1", g)
        ns._mdl_mint._ep = 7
        ns._w2b_driven = {"key": "k", "steps": [ids[0]]}
        cl._w2b_abort(ns, frame_changed=True, level_changed=False)
        recs = [r for r in _plan_records(g) if r.get("mode") == S.PLAN_HELD]
        assert len(recs) == 1 and recs[0]["steps"] == [ids[0]], (
            "the HELD record did not fire -- %r" % (recs,))
        assert recs[0]["ep"] == 7 and recs[0]["gate"] == S.HELD_GATE
        b = _book(g)
        assert (7, S.E_HELD) in b.events(ids[0])

    def test_a_routed_plan_wrong_persists_steps_and_ep(self, tmp_path):
        g, ids = _population(tmp_path, "seam2", n=3, ep=0)
        ns = _ns(tmp_path, "seam2", g)
        ns._mdl_mint._ep = 9
        ns._prev_frame = np.zeros((3, 3), dtype=int)
        ns._w2b_driven = {"key": SCH.state_key(ns._prev_frame),
                          "steps": [ids[1]]}
        cl._w2b_abort(ns, frame_changed=False, level_changed=False)
        rec = [r for r in _plan_records(g)
               if r.get("mode") == "abort"][-1]
        assert rec["gate"] == SCH.ABORT_PLAN_WRONG
        assert rec["steps"] == [ids[1]] and rec["ep"] == 9
        assert (9, S.M_PLAN_WRONG) in _book(g).events(ids[1])

    def test_a_world_moved_abort_is_never_a_misprediction(self, tmp_path):
        """FIGURE 2: those atoms were never given the state they bet on, so no
        contact with the ground happened and nothing is recorded against them."""
        g, ids = _population(tmp_path, "seam3", n=3, ep=0)
        ns = _ns(tmp_path, "seam3", g)
        ns._mdl_mint._ep = 3
        ns._prev_frame = np.ones((3, 3), dtype=int)
        ns._w2b_driven = {"key": "a-different-key", "steps": [ids[2]]}
        cl._w2b_abort(ns, frame_changed=False, level_changed=False)
        rec = [r for r in _plan_records(g) if r.get("mode") == "abort"][-1]
        assert rec["gate"] == SCH.ABORT_WORLD_MOVED
        assert [k for _e, k in _book(g).events(ids[2])
                if k in S.MISPREDICT] == [], (
            "a world-moved abort must record no misprediction event")

    def test_the_engagement_sweep_runs_at_the_loops_own_gate(self, tmp_path):
        """_w2b_engage owns the sweep: the eviction is written when the
        planner engages, and narrated at the PLAN point with fixed tokens."""
        g, ids = _population(tmp_path, "seam4", n=5, ep=0)
        ns = _ns(tmp_path, "seam4", g)
        sp = _spine(g)
        for k in range(5):
            _wrong(sp, [ids[0]], ep=1 + k)
        ns._narration = sp
        assert cl._w2b_engage(ns, np.zeros((3, 3), dtype=int),
                              SimpleNamespace(action_confidence=0.0,
                                              action_speed="explore")) is True
        assert ns._w2b_sched.standing.evictions == 1
        toks = [r for r in _plan_records(g)
                if r.get("mode") == S.PLAN_EVICTED]
        assert len(toks) == 1 and toks[0]["gate"] == ids[0], (
            "the eviction must be narrated at the PLAN point with the id")
        assert _records(g, ids[0])[-1][S.EVICTED_FIELD] is True

    def test_a_composite_settle_carries_the_episode_ordinal(self, tmp_path):
        """The settle append is the composite's earn event, so it needs the
        clock: composer.live_settle(ep=) is the ONE place it is stamped."""
        g = _gamma(tmp_path, "seam5")
        a = g.add(_atom([[3]], [[9]], "eff-p"), GAME, LEVEL)
        cid = g.compose([a], GAME, LEVEL)
        pre = np.zeros((3, 3), dtype=int)
        pre[1, 1] = 3
        post = pre.copy()
        post[1, 1] = 9
        drive = {"composite": cid, "chain": [a], "frame0": pre,
                 "frames": [post], "want_cells": [(1, 1)], "anchors": [None]}
        out = C.live_settle(g, drive, post, ep=11)
        assert out["settled"] is True and out["written"] is True, out
        rec = _records(g, cid)[-1]
        assert rec.get("ep") == 11 and rec.get(C.SETTLED_FIELD) is True
        b = _book(g)
        assert (11, S.E_HELD) in b.events(cid), (
            "the settle transition is the composite's earn event")

    def test_the_settle_transition_counts_once(self, tmp_path):
        """A later superseding append carries `settled` forward; only the
        transition is the event (one event, one count)."""
        g = _gamma(tmp_path, "seam6")
        a = g.add(_atom([[3]], [[9]], "eff-q"), GAME, LEVEL)
        cid = g.compose([a], GAME, LEVEL)
        rec = _records(g, cid)[-1]
        for _ in range(3):
            sup = dict(rec)
            sup["settled"] = True
            sup["ep"] = 2
            g.fabric.append("collective", g.TOPIC, sup)
        b = _book(g)
        assert [k for _e, k in b.events(cid)] == [S.E_HELD], (
            "F7 FALSIFIED: the carried-forward flag was counted again")


# ═════════════════════════════════════════════════════════════════════════════
# THE LAWS (figures/*.svg via record/corpus/FIGURES_TEXT_DIGEST.md)
# ═════════════════════════════════════════════════════════════════════════════

_PRICING_MODULES = ("pricing", "bank", "mastery", "lp_drive", "rho",
                    "consumer", "affect", "betting", "starvation")


def _prod_sources():
    out = {}
    for pat in ("*.py", "engines/**/*.py", "rungs/**/*.py"):
        for p in glob.glob(os.path.join(REPO, pat), recursive=True):
            rel = os.path.relpath(p, REPO).replace("\\", "/")
            if rel.startswith(("tests/", "tools/", ".runs/", ".venv/")):
                continue
            with open(p, encoding="utf-8", errors="replace") as fh:
                out[rel] = fh.read()
    return out


class TestFigure1SIsNotAMetric:
    """FIGURE 1: the ground is the only metric. Predicates minted and
    credibility accrued are frame-internal and do not count. S RANKS
    RETRIEVAL -- it is never a score, never reported as progress, never
    priced. Asserted by SOURCE: the sink identity."""

    def test_no_pricing_or_reporting_module_reads_standing(self):
        src = _prod_sources()
        offenders = []
        for rel, text in src.items():
            base = os.path.basename(rel)[:-3]
            if base not in _PRICING_MODULES:
                continue
            if any(t in text for t in ("import standing", "standing.",
                                       "StandingBook", "_standing")):
                offenders.append(rel)
        assert offenders == [], (
            "FIGURE 1 FALSIFIED: a pricing/reporting module reads standing -- %r"
            % (offenders,))

    def test_the_only_importers_are_the_retrieval_path(self):
        src = _prod_sources()
        importers = set()
        for rel, text in src.items():
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    names = [a.name for a in node.names]
                    if "standing" in names and "egocentric" in (node.module or ""):
                        importers.add(rel)
                elif isinstance(node, ast.Import):
                    if any(a.name.endswith(".standing") for a in node.names):
                        importers.add(rel)
        assert importers <= {"cognitive_loop.py",
                             "engines/egocentric/planner.py",
                             "engines/egocentric/scheduler.py",
                             "engines/egocentric/composer.py"}, (
            "FIGURE 1 FALSIFIED: standing reached beyond the retrieval path -- %r"
            % (sorted(importers),))
        assert "engines/egocentric/planner.py" in importers, (
            "the rank consumer must exist, or this assertion is vacuous")

    def test_S_never_reaches_a_stream_record_as_a_score(self, tmp_path):
        """S appears on exactly one kind of record -- the eviction/re-entry
        append, where it is PROVENANCE for a retrieval decision (FIGURE 10),
        beside the fence it was judged against. Never on a verdict, never on
        a narration outcome record, never as progress."""
        g, ids = _population(tmp_path, "fig1", n=5, ep=0)
        sp = _spine(g)
        for k in range(5):
            _wrong(sp, [ids[0]], ep=1 + k)
        b = _book(g)
        b.engage(g, GAME, LEVEL)
        carriers = [r for r in _records(g) if S.S_FIELD in r]
        assert len(carriers) == 1 and S.TAU_FIELD in carriers[0]
        assert all(S.S_FIELD not in r
                   for r in g.fabric.query("collective", M.VERDICT_TOPIC))
        assert all(S.S_FIELD not in r
                   for r in g.fabric.query("personal", NA.TOPIC))


class TestFigure2NoMutualUpdate:
    """FIGURE 2: the anchor does not update. Standing is each atom ranged
    against the ground SEPARATELY -- no atom's outcome ever moves another's."""

    def test_one_atoms_events_never_move_another_atoms_standing(self, tmp_path):
        g, ids = _population(tmp_path, "fig2", n=4, ep=0)
        b = _book(g)
        before = {a: b.standing(a, GAME) for a in ids}
        sp = _spine(g)
        for _k in range(6):
            _wrong(sp, [ids[0]], ep=1)
            _held(sp, [ids[1]], ep=1)
        b.refresh(g)
        for a in ids[2:]:
            assert b.standing(a, GAME, t=0) == before[a], (
                "FIGURE 2 FALSIFIED: %s moved on another atom's outcome" % a)
        assert b.standing(ids[0], GAME) < before[ids[0]]
        assert b.standing(ids[1], GAME) > before[ids[1]]

    def test_the_event_book_of_an_atom_holds_only_its_own_events(self, tmp_path):
        g, ids = _population(tmp_path, "fig2b", n=3, ep=0)
        sp = _spine(g)
        _wrong(sp, [ids[0]], ep=2)
        b = _book(g)
        assert [k for _e, k in b.events(ids[1])] == [S.E_MINT]
        assert sorted(k for _e, k in b.events(ids[0])) == [S.E_MINT,
                                                           S.M_PLAN_WRONG]
