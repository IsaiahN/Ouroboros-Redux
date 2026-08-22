"""REASONING GATE STAGE 1 -- SHADOW MODE (PREREG_GATE_STAGE1_SHADOW.md).

The build under test: engines/egocentric/grammar.py (the salvaged typed
primes + compose() + the speech-act layer: RECORD / PRICE, nine heads with
the check-kind riding the head, three RECORD-producing terminals) and
engines/egocentric/gate.py (the shadow gate: the utterance-builder reading
ONLY agent state, the three checks -- ledger / executable / completeness --
the probe with its ignorance check, the off/observe/active ladder, the
no_posthoc wall, the three-number report) plus the ONE hook beside act() in
cognitive_loop._narr_bet (_gate_step, module bottom).

The falsifiers, as gated here (constructed fixtures throughout; no .runs):
  F1  WIRE CHECKS, PER HEAD: for each of the nine heads a constructed TRUE
      clause passes and a constructed FALSE clause refuses with THAT head
      named and a fixed token -- no head exempt (a head with no false case
      would fail the stage).
  F2  PRECEDENCE TYPE-CHECKS: GROUND citing a non-RECORD is ill-typed (parse,
      not ledger); a BET citing a later-sequence / other-step PERCEIVE
      refuses not-earlier / wrong-step; NEED citing a PERCEIVE (right type,
      wrong kind) is a LEDGER refusal at NEED.
  F3  COMPLETENESS: k differing cells with k-1 reported -> unreported-change
      (CHANGED named); all k pass; an extra unchanged cell -> false-change.
  F4  PROBE-IGNORANCE: a probe for an action with a held, applicable atom
      -> false-ignorance; the same probe with the atom absent passes; no
      book -> book-absent, a NON-verdict counted apart, never a pass.
  F5  SHADOW-NO-BLOCK (structural): the hook's return is unbound, action_num
      is never assigned after it, _gate_step returns nothing; a constructed
      episode's action sequence is byte-identical under off and observe;
      refuse == 0 by identity across the suite.
  F6  THE THREE-NUMBER REPORT: a constructed stream with known class counts
      reproduces them exactly, stratified, never folded (R4 both ways).
  THE DEADLINE MECHANISM (Seat 3's ruling): enforcement on + PERCEIVE on the
      gate topic -> deadline_violation names it; the shipped pair is clean
      (this is the test that goes red if stage 2 flips the flag first).
  THE WALL: a constructed builder variant reading post_array fails the
      import-time check; the shipped builders pass; a settle-builder reading
      the opener passes (labels are exempt); announce() speaks; audit() names
      not_guarded.
  SEAMS (each new code): wall x builder; ladder x verdicts (one false clause
      under all three values); Discrepancy x compute_d (misaligned / vacuous
      / pass); tropism x probe-validity (rank never confers validity);
      composer-utterances x gate-requests (a composed drive renders and
      passes with the predicted cells == frames[-1]; an unsatisfiable WANT
      is a NAMED refusal, never a silent drop); is_citable x GROUND (an
      unsettled composite refused at GROUND, accepted as the bet; settled
      flips exactly the former).
  KNOWN-NEGATIVES: no spine BET -> unbuildable: no-bet, not a refusal; the
      downgrade record exactly once; the ALLOWLIST carries `gate` citing
      this prereg.

Seeded with a FIXED CONSTANT (the prereg date), never a clock.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _laws():
    """The shared law bodies (tests/gate/_ast_laws.py). tests/gate is not a
    package, so it is loaded by path and cached in sys.modules for the
    session -- one body per law, one place to argue with it."""
    mod = sys.modules.get("_ouro_ast_laws")
    if mod is None:
        spec = importlib.util.spec_from_file_location(
            "_ouro_ast_laws",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ast_laws.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_ouro_ast_laws"] = mod
        spec.loader.exec_module(mod)
    return mod

import cognitive_loop as cl  # noqa: E402
from engines.egocentric import action_book as AB  # noqa: E402
from engines.egocentric import composer as C  # noqa: E402
from engines.egocentric import gate as GT  # noqa: E402
from engines.egocentric import grammar as G  # noqa: E402
from engines.egocentric import narration as na  # noqa: E402
from engines.egocentric.effects import Gamma, learn_effect  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.grammar import Leaf, T, compose, ref  # noqa: E402

SEED = 20260821  # fixed constant (the prereg date) -- deterministic forever

GAME = "g1"
NOBOOK = "g-nobook"


@pytest.fixture(autouse=True)
def _fresh_books(monkeypatch):
    """action_book's one in-memory dict is module-global: every test starts
    with NO book loaded (absence is absence; a leak would read as evidence)."""
    monkeypatch.setattr(AB, "_BOOKS", {})


# ── constructions ─────────────────────────────────────────────────────────────

def _fab(tmp_path, name="f"):
    return KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")


def _frames():
    """opener: a 4x4 board with colour 1 at (1,1); prev: the same with (0,0)
    = 5 -- so compute_d(prev, opener) differs on EXACTLY {(0,0)}."""
    opener = np.zeros((4, 4), dtype=int)
    opener[1, 1] = 1
    prev = opener.copy()
    prev[0, 0] = 5
    return opener, prev


def _atom(action=2, a=1, b=2):
    """A canonical EFFECT atom (effects.learn_effect): context [[a]] -> after [[b]]."""
    return learn_effect(np.array([[a]]), action, np.array([[b]]))


def _gamma(tmp_path, name="gm"):
    fab = _fab(tmp_path, name)
    gm = Gamma(fab)
    aid = gm.add(_atom(2, 1, 2), GAME, 1)          # action 2: 1 -> 2
    bid = gm.add(_atom(3, 2, 1), GAME, 1)          # action 3: 2 -> 1 (the inverse)
    return fab, gm, aid, bid


def _book_dir(tmp_path):
    """A constructed action book artifact for GAME: action 2 rich (atoms +
    traces + cost), action 3 atoms only (cost explicit null), action 7 the
    explicit-null shape; inverses 2 <-> 3 with n = 1 + 1."""
    book = {
        "artifact": AB.ARTIFACT, "version": AB.BOOK_VERSION, "box": "boxa",
        "game_ids": [GAME],
        "actions": {
            "2": {"atoms": {"n": 3, "ttypes": {"RECOLOR": 3}},
                  "traces": {"n": 4, "frame_changed_n": 3, "frame_change_rate": 0.75,
                             "score": {"n": 4, "pos_n": 1}},
                  "cost": {"n": 4, "budget_spend": {"n": 4, "min": 0.25, "max": 0.5,
                                                    "mean": 0.375},
                           "budget_total": {"n": 4, "min": 10.0, "max": 10.0,
                                            "mean": 10.0}}},
            "3": {"atoms": {"n": 1, "ttypes": {"RECOLOR": 1}}, "traces": None,
                  "traces_absent": "no traces", "cost": None, "cost_absent": "no traces"},
            "7": {"atoms": None, "atoms_absent": AB.NO_EVIDENCE, "traces": None,
                  "traces_absent": AB.NO_EVIDENCE, "cost": None, "cost_absent": AB.NO_EVIDENCE},
        },
        "inverses": {"2": {"pairs": {"3": {"n_traces": 1, "n_atoms": 1}}}},
    }
    d = tmp_path / "box"
    os.makedirs(os.path.dirname(AB.book_path(str(d))), exist_ok=True)
    with open(AB.book_path(str(d)), "w", encoding="utf-8") as fh:
        json.dump(book, fh)
    return str(d)


def _state(opener, prev, **kw):
    s = {"step": 1, "action": 2, "rung": "explore", "anchor": None, "spine_bet": "n:g1:1:1",
         "opener": opener, "prev": prev, "plan_steps": [], "composite": None, "drive": None,
         "chain_cursor": 0, "composite_price": None, "atom_of": None, "fatal": set(),
         "avatar": None, "settled_atom": (None, None), "want_cells": None,
         "game": GAME, "level": 1, "book_loaded": False, "cost": None}
    s.update(kw)
    return s


def _ledger(**kw):
    led = {"gamma": None, "game": GAME, "level": 1, "fatal": set(), "avatar": None,
           "settled_atom": (None, None), "book_loaded": False, "composite_price": None,
           "held_for_action": lambda a: [], "deltas": {}}
    led.update(kw)
    return led


def _see(cell, colour):
    return compose(G.SEE, Leaf(T.OBJECT, GT.SLOT), Leaf(T.REGION, cell), Leaf(T.ATTR, colour))


def _changed(cell, a, b):
    return compose(G.CHANGED, Leaf(T.REGION, cell), Leaf(T.ATTR, a), Leaf(T.ATTR, b))


def _become(cells):
    return compose("BECOME", Leaf(T.OBJECT, GT.SLOT), Leaf(T.ATTR, tuple(cells)))


def _want(cells):
    return compose(G.WANT, compose("ALL", _become(cells)))


def _two_steps(st):
    """A CONSISTENT two-step episode for a state built on (opener, prev):
    step 0 perceives `prev` with nothing before it; step 1 perceives `opener`
    having tracked `prev` -- so the agent's tracked previous frame IS the
    gate's retained previous opener (the builder/gate split holds by data,
    and an inconsistent fixture is a false-change, as it should be)."""
    return [dict(st, step=0, opener=st["prev"], prev=None), dict(st, step=1)]


def _records(pid="g:g1:1:1", bid="g:g1:1:2"):
    return {pid: {"terminal": G.PERCEIVE, "step": 1, "sq": 1},
            bid: {"terminal": G.BET, "step": 1, "sq": 2, "action": 2}}


def _gate_recs(fab):
    return fab.query("personal", GT.TOPIC)


def _summaries(fab):
    return [r for r in _gate_recs(fab) if r["terminal"] == "SUMMARY"]


# ── the grammar: nine heads, one check-kind each, compose raises with reason ──

class TestTheGrammar:

    def test_the_thirteen_primes_salvaged_with_signatures(self):
        assert len(G.PRIMES) == 13
        assert G.PRIMES["BE_AT"].in_types == (T.OBJECT, T.REGION)
        assert G.PRIMES["ALL"].out_type is T.OBJ
        assert G.KANT_CATEGORIES == ["Modality", "Quality", "Quantity", "Relation"]

    def test_nine_heads_each_with_one_check_kind_riding_the_head(self):
        assert len(G.HEADS) == 9
        for name, p in G.HEADS.items():
            assert p.check in G.CHECK_KINDS, "%s carries no check-kind" % name
            assert G.head_check(name) == p.check
        assert G.head_check(G.SEE) == G.CHECK_EXECUTABLE
        assert G.head_check(G.CHANGED) == G.CHECK_COMPLETENESS
        assert G.head_check(G.GROUND) == G.CHECK_LEDGER
        assert G.head_check(G.SETTLE) == G.CHECK_LEDGER_EXECUTABLE

    def test_terminals_produce_records(self):
        for t in (G.PERCEIVE, G.BET, G.ACT):
            assert G.TERMINALS[t].out_type is T.RECORD

    def test_compose_raises_with_its_reason_never_silently(self):
        with pytest.raises(G.TypeError_, match="ill-typed: BE_AT expects"):
            compose("BE_AT", Leaf(T.ATTR, 1), Leaf(T.REGION, (0, 0)))
        with pytest.raises(G.TypeError_, match="unknown head"):
            compose("NOPE")
        with pytest.raises(G.TypeError_, match="not a typed value"):
            compose("NOT", 42)

    def test_typed_holes_compose_as_templates(self):
        t = compose("SOME", compose("BE_AT", T.OBJECT, T.REGION))
        assert G.is_objective(t)
        assert G.is_hole(T.ATTR) and not G.is_hole(t)

    def test_molecules_and_counters_are_not_carried(self):
        assert not hasattr(G, "MOLECULES")
        assert not hasattr(G, "count_typed_objectives")


# ── F1: wire checks, per head (true passes, false refuses with THAT head) ─────

class TestF1WireChecks:

    def test_see(self):
        opener, _ = _frames()
        assert GT.check_see(_see((1, 1), 1), opener)["verdict"] == GT.PASS
        v = GT.check_see(_see((1, 1), 7), opener)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.MISMATCH)
        assert GT.check_see(_see((9, 9), 0), opener)["token"] == GT.MISMATCH

    def test_changed(self):
        opener, prev = _frames()
        v, counts = GT.check_changed_set([_changed((0, 0), 5, 0)], prev, opener)
        assert v["verdict"] == GT.PASS and counts == {"differing": 1, "reported": 1,
                                                       "unreported": 0}
        v, _ = GT.check_changed_set([_changed((2, 2), 0, 0)], prev, opener)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.FALSE_CHANGE)
        v, _ = GT.check_changed_set([_changed((0, 0), 4, 0)], prev, opener)
        assert v["token"] == GT.FALSE_CHANGE, "the right cell with the wrong a -> b is false"

    def test_settle(self):
        opener, _ = _frames()
        pb = {"id": "g:g1:0:2", "step": 0, "settled": False, "predicted": {(1, 1): 1},
              "atoms": []}
        held = compose("SAME", Leaf(T.ATTR, ("residual", 0.0)), Leaf(T.ATTR, ("residual", 0.0)))
        broke = compose("OTHER", Leaf(T.ATTR, ("residual", 1.0)), Leaf(T.ATTR, ("residual", 0.0)))
        assert GT.check_settle(compose(G.SETTLE, ref(pb["id"], "bet"), held),
                               opener, 1, pb)["verdict"] == GT.PASS
        v = GT.check_settle(compose(G.SETTLE, ref(pb["id"], "bet"), broke), opener, 1, pb)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.MISMATCH)
        # the prediction broke (predicted 9, the world shows 1): OTHER d=1 holds, SAME refuses
        pb9 = dict(pb, predicted={(1, 1): 9})
        assert GT.check_settle(compose(G.SETTLE, ref(pb["id"], "bet"), broke),
                               opener, 1, pb9)["verdict"] == GT.PASS
        assert GT.check_settle(compose(G.SETTLE, ref(pb["id"], "bet"), held),
                               opener, 1, pb9)["token"] == GT.MISMATCH
        # ledger half: wrong step, already settled, unknown id, wrong kind
        assert GT.check_settle(compose(G.SETTLE, ref(pb["id"], "bet"), held),
                               opener, 2, pb)["token"] == GT.WRONG_STEP
        assert GT.check_settle(compose(G.SETTLE, ref(pb["id"], "bet"), held), opener, 1,
                               dict(pb, settled=True))["token"] == GT.ALREADY_SETTLED
        assert GT.check_settle(compose(G.SETTLE, ref("g:g1:0:9", "bet"), held),
                               opener, 1, pb)["token"] == GT.NOT_HELD
        assert GT.check_settle(compose(G.SETTLE, ref(pb["id"], "perceive"), held),
                               opener, 1, pb)["token"] == GT.WRONG_KIND
        # the residual and its threshold are the bank's / router's own, by identity
        from engines.egocentric.bank import PredictorBank
        from engines.egocentric.router import ResidualRouter
        assert GT.RESIDUAL is PredictorBank._grid_residual
        assert ResidualRouter().eps == GT.SETTLE_EPS

    def test_stand(self):
        sa = ("k:1", na.TRANSFERRED)
        strong = compose(G.STAND, ref("k:1", "atom"), Leaf(T.ATTR, GT.STRENGTHENED))
        weak = compose(G.STAND, ref("k:1", "atom"), Leaf(T.ATTR, GT.WEAKENED))
        assert GT.check_stand(strong, sa, False, set())["verdict"] == GT.PASS
        v = GT.check_stand(weak, sa, False, set())
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.STANDING_MISMATCH)
        assert GT.check_stand(weak, ("k:1", na.BROKEN_MECHANISM), False,
                              set())["verdict"] == GT.PASS
        # an id cited in a bet that broke cannot strengthen in the same PERCEIVE
        v = GT.check_stand(strong, sa, True, {"k:1"})
        assert v["token"] == GT.STANDING_MISMATCH and v["note"] == "cited-in-broken-bet"
        died = compose(G.STAND, ref("k:1", "atom"), Leaf(T.ATTR, GT.DIED))
        assert GT.check_stand(died, sa, False, set())["token"] == GT.STANDING_MISMATCH

    def test_want(self):
        opener, _ = _frames()
        assert GT.check_want(_want([(1, 1, 2)]), opener)["verdict"] == GT.PASS
        v = GT.check_want(_want([(1, 1, 1)]), opener)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.VACUOUS)
        assert GT.check_want(_want([(9, 9, 1)]), opener)["token"] == GT.MISALIGNED
        assert GT.check_want(compose(G.WANT, T.OBJ), opener)["note"] == "template"
        v = GT.check_want(compose(G.WANT, compose("SOME", compose("EXIST", T.OBJECT))), opener)
        assert (v["verdict"], v["token"]) == (GT.UNVERDICTED, GT.UNCOMPILABLE)

    def test_ground(self, tmp_path):
        _fab_, gm, aid, _bid = _gamma(tmp_path)
        opener, _ = _frames()
        pid = "g:g1:1:1"
        pterms = {pid: compose(G.PERCEIVE, _see((1, 1), 1))}
        derive = compose(G.DERIVE, compose(G.GROUND, ref(pid, "perceive")),
                         ref(aid, "atom"), _become([(1, 1, 2)]))
        led = _ledger(gamma=gm)
        ok = compose(G.GROUND, ref(pid, "perceive"), ref(aid, "atom", tag=na.OWN))
        assert GT.check_ground(ok, derive, _records(), 1, 2, pterms, led)["verdict"] == GT.PASS
        bad = compose(G.GROUND, ref(pid, "perceive"), ref("nope:9", "atom", tag=na.OWN))
        v = GT.check_ground(bad, derive, _records(), 1, 2, pterms, led)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.NOT_HELD)
        wrong_tag = compose(G.GROUND, ref(pid, "perceive"), ref(aid, "atom", tag=na.COL))
        assert GT.check_ground(wrong_tag, derive, _records(), 1, 2, pterms,
                               led)["token"] == GT.NOT_HELD
        # a cell DERIVE uses that the perceive never reported
        d22 = compose(G.DERIVE, compose(G.GROUND, ref(pid, "perceive")), ref(aid, "atom"),
                      _become([(2, 2, 0)]))
        assert GT.check_ground(ok, d22, _records(), 1, 2, pterms,
                               led)["token"] == GT.NOT_IN_PERCEIVE
        fr = compose(G.GROUND, ref(pid, "perceive"), ref("frontier:g1:1:2,2", "frontier"))
        assert GT.check_ground(fr, derive, _records(), 1, 2, pterms,
                               _ledger(fatal={(2, 2)}))["verdict"] == GT.PASS
        assert GT.check_ground(fr, derive, _records(), 1, 2, pterms,
                               _ledger(fatal=set()))["token"] == GT.NOT_HELD

    def test_derive_positive(self, tmp_path):
        _fab_, gm, aid, _bid = _gamma(tmp_path)
        opener, _ = _frames()
        ground = compose(G.GROUND, ref("g:g1:1:1", "perceive"), ref(aid, "atom"))
        led = _ledger(gamma=gm)
        ok = compose(G.DERIVE, ground, ref(aid, "atom"), _become([(1, 1, 2)]))
        assert GT.check_derive(ok, opener, 2, led)["verdict"] == GT.PASS
        bad = compose(G.DERIVE, ground, ref(aid, "atom"), _become([(1, 1, 3)]))
        v = GT.check_derive(bad, opener, 2, led)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.MISMATCH)
        # an atom whose context does not match here cannot derive anything
        blank = np.zeros((4, 4), dtype=int)
        assert GT.check_derive(ok, blank, 2, led)["note"] == "inapplicable"

    def test_derive_inverse(self, tmp_path):
        _fab_, gm, aid, bid = _gamma(tmp_path)
        AB.load_action_book(_book_dir(tmp_path))
        opener, _ = _frames()
        ground = compose(G.GROUND, ref("g:g1:1:1", "perceive"), ref(aid, "atom"),
                         ref(bid, "atom"))
        led = _ledger(gamma=gm, book_loaded=True)

        def _inv(n):
            return compose("SAME", Leaf(T.ATTR, ("inverse", 2, 3, n)), Leaf(T.ATTR, "identity"))

        ok = compose(G.DERIVE, ground, ref(aid, "atom"), ref(bid, "atom"), _inv(2))
        assert GT.check_derive(ok, opener, 2, led)["verdict"] == GT.PASS
        v = GT.check_derive(compose(G.DERIVE, ground, ref(aid, "atom"), ref(bid, "atom"),
                                    _inv(5)), opener, 2, led)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.MISMATCH), "n stated verbatim"
        v = GT.check_derive(ok, opener, 2, _ledger(gamma=gm, book_loaded=False))
        assert (v["verdict"], v["token"]) == (GT.UNVERDICTED, GT.BOOK_ABSENT)
        # the deltas must compose to identity: a -> a is no inverse
        v = GT.check_derive(compose(G.DERIVE, ground, ref(aid, "atom"), ref(aid, "atom"),
                                    _inv(2)), opener, 2, led)
        assert v["token"] == GT.MISMATCH

    def test_derive_negative(self):
        opener, _ = _frames()
        ground = compose(G.GROUND, ref("g:g1:1:1", "perceive"),
                         ref("frontier:g1:1:2,2", "frontier"))
        neg = compose(G.DERIVE, ground, ref("frontier:g1:1:2,2", "frontier"),
                      compose("NOT", compose("BE_AT", Leaf(T.OBJECT, GT.SELF),
                                             Leaf(T.REGION, (2, 2)))))
        led = _ledger(fatal={(2, 2)}, avatar=(1, 2), deltas={1: (-1, 0), 2: (1, 0)})
        assert GT.check_derive(neg, opener, 1, led)["verdict"] == GT.PASS
        v = GT.check_derive(neg, opener, 2, led)      # action 2 walks INTO the fatal cell
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.MISMATCH)
        assert v["note"] == "enters-fatal"
        assert GT.check_derive(neg, opener, 1, _ledger(fatal=set(), avatar=(1, 2),
                                                       deltas={1: (-1, 0)}))["note"] == "not-fatal"
        v = GT.check_derive(neg, opener, 1, _ledger(fatal={(2, 2)}, avatar=(1, 2), deltas={}))
        assert (v["verdict"], v["token"]) == (GT.UNVERDICTED, GT.BOOK_ABSENT)

    def test_pay(self, tmp_path):
        AB.load_action_book(_book_dir(tmp_path))
        led = _ledger(book_loaded=True)
        assert GT.check_pay(compose(G.PAY, G.price(0.375, 4)), 2, led)["verdict"] == GT.PASS
        v = GT.check_pay(compose(G.PAY, G.price(0.5, 4)), 2, led)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.PRICE_MISMATCH)
        assert GT.check_pay(compose(G.PAY, G.price(0.375, None)), 2,
                            led)["token"] == GT.PRICE_INVENTED
        # the book's cost is an explicit null: the null must be STATED
        assert GT.check_pay(compose(G.PAY, G.price(None)), 3, led)["verdict"] == GT.PASS
        assert GT.check_pay(compose(G.PAY, G.price(1.0, 1)), 3,
                            led)["token"] == GT.PRICE_INVENTED
        v = GT.check_pay(compose(G.PAY, G.price(None)), 2, _ledger(game=NOBOOK))
        assert (v["verdict"], v["token"]) == (GT.UNVERDICTED, GT.BOOK_ABSENT)
        # a composite pays its DERIVED price; None -> the explicit null, never a number
        cl_ = _ledger(composite_price=3.0)
        assert GT.check_pay(compose(G.PAY, G.price(3.0)), 6, cl_, "c")["verdict"] == GT.PASS
        assert GT.check_pay(compose(G.PAY, G.price(2.0)), 6, cl_, "c")["token"] == GT.PRICE_MISMATCH
        assert GT.check_pay(compose(G.PAY, G.price(1.0)), 6, _ledger(),
                            "c")["token"] == GT.PRICE_INVENTED

    def test_need(self):
        ok = compose(G.NEED, ref("g:g1:1:2", "bet"), Leaf(T.ATTR, 2))
        assert GT.check_need(ok, 1, 3, _records())["verdict"] == GT.PASS
        v = GT.check_need(compose(G.NEED, ref("g:g1:1:2", "bet"), Leaf(T.ATTR, 3)), 1, 3,
                          _records())
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.MISMATCH)
        assert GT.check_need(ok, 1, 2, _records())["token"] == GT.NOT_EARLIER
        assert GT.check_need(ok, 2, 3, _records())["token"] == GT.WRONG_STEP

    def test_no_head_is_exempt(self):
        """Every head above has a false case; the stage fails if one cannot."""
        covered = {G.SEE, G.CHANGED, G.SETTLE, G.STAND, G.WANT, G.GROUND, G.DERIVE, G.PAY,
                   G.NEED}
        assert covered == set(G.HEADS), "a head with no wire check: %r" % (
            set(G.HEADS) - covered)


# ── F2: precedence type-checks ───────────────────────────────────────────────

class TestF2Precedence:

    def test_ground_citing_a_non_record_is_ill_typed_at_parse(self):
        with pytest.raises(G.TypeError_, match="ill-typed: GROUND"):
            compose(G.GROUND, Leaf(T.ATTR, "not a record"))
        with pytest.raises(G.TypeError_, match="ill-typed: DERIVE"):
            compose(G.DERIVE, compose(G.GROUND, ref("p", "perceive")), Leaf(T.ATTR, 1), T.PRED)
        with pytest.raises(G.TypeError_, match="ill-typed: NEED"):
            compose(G.NEED, Leaf(T.ATTR, 2), Leaf(T.ATTR, 2))

    def test_a_holed_want_composes_with_a_probe_only(self):
        ground = compose(G.GROUND, ref("p", "perceive"))
        pay = compose(G.PAY, G.price(None))
        probe = compose(G.DERIVE, ground, T.PRED)
        assert compose(G.BET, compose(G.WANT, T.OBJ), ground, probe, pay).type is T.RECORD
        concrete = compose(G.DERIVE, ground, ref("a", "atom"), _become([(1, 1, 2)]))
        with pytest.raises(G.TypeError_, match="holed WANT"):
            compose(G.BET, compose(G.WANT, T.OBJ), ground, concrete, pay)
        with pytest.raises(G.TypeError_, match="cites no record"):
            compose(G.BET, _want([(1, 1, 2)]), ground,
                    compose(G.DERIVE, ground, _become([(1, 1, 2)])), pay)
        with pytest.raises(G.TypeError_, match="in order"):
            compose(G.BET, ground, _want([(1, 1, 2)]), probe, pay)

    def test_bet_citing_a_later_or_other_step_perceive_refuses_at_ground(self, tmp_path):
        _fab_, gm, aid, _bid = _gamma(tmp_path)
        opener, _ = _frames()
        pid = "g:g1:1:1"
        pterms = {pid: compose(G.PERCEIVE, _see((1, 1), 1))}
        ground = compose(G.GROUND, ref(pid, "perceive"), ref(aid, "atom"))
        derive = compose(G.DERIVE, ground, ref(aid, "atom"), _become([(1, 1, 2)]))
        led = _ledger(gamma=gm)
        later = {pid: {"terminal": G.PERCEIVE, "step": 1, "sq": 5}}
        assert GT.check_ground(ground, derive, later, 1, 2, pterms, led)["token"] == GT.NOT_EARLIER
        other = {pid: {"terminal": G.PERCEIVE, "step": 0, "sq": 1}}
        assert GT.check_ground(ground, derive, other, 1, 2, pterms, led)["token"] == GT.WRONG_STEP

    def test_need_citing_a_perceive_is_a_ledger_refusal_at_need(self):
        v = GT.check_need(compose(G.NEED, ref("g:g1:1:1", "perceive"), Leaf(T.ATTR, 2)),
                          1, 3, _records())
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.WRONG_KIND)
        v = GT.check_ground(compose(G.GROUND, ref("g:g1:1:2", "bet")),
                            compose(G.DERIVE, compose(G.GROUND, ref("p", "perceive")), T.PRED),
                            _records(), 1, 3, {}, _ledger())
        assert v["token"] == GT.WRONG_KIND


# ── F3: completeness, never economised ───────────────────────────────────────

class TestF3Completeness:

    def test_k_minus_one_reported_is_unreported_change_with_changed_named(self):
        opener, prev = _frames()
        prev[3, 3] = 7                                   # k = 2 differing cells
        v, counts = GT.check_changed_set([_changed((0, 0), 5, 0)], prev, opener)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.UNREPORTED_CHANGE)
        assert counts == {"differing": 2, "reported": 1, "unreported": 1}
        v, counts = GT.check_changed_set([_changed((0, 0), 5, 0), _changed((3, 3), 7, 0)],
                                         prev, opener)
        assert v["verdict"] == GT.PASS and counts["unreported"] == 0
        v, _ = GT.check_changed_set([_changed((0, 0), 5, 0), _changed((3, 3), 7, 0),
                                     _changed((2, 2), 0, 0)], prev, opener)
        assert v["token"] == GT.FALSE_CHANGE

    def test_the_terminal_names_changed_on_an_unreported_cell(self):
        opener, prev = _frames()
        term = compose(G.PERCEIVE, _see((1, 1), 1))       # reports nothing changed
        pv = GT.check_perceive(term, opener, prev, 1, None, (None, None))
        assert (pv["verdict"], pv["head"], pv["token"]) == (GT.REFUSE, G.CHANGED,
                                                            GT.UNREPORTED_CHANGE)
        assert pv["completeness"] == {"differing": 1, "reported": 0, "unreported": 1}

    def test_shape_mismatch_is_a_non_answer_never_satisfied(self):
        opener, _ = _frames()
        v, _ = GT.check_changed_set([], np.zeros((3, 3), dtype=int), opener)
        assert (v["verdict"], v["token"]) == (GT.UNVERDICTED, GT.MISALIGNED)
        v, _ = GT.check_changed_set([], None, opener)
        assert (v["verdict"], v["token"]) == (GT.UNVERDICTED, GT.NO_PREVIOUS)


# ── F4: probe-ignorance, and book-absent as a named non-verdict ──────────────

class TestF4ProbeIgnorance:

    def _run(self, fab, states, ledger, mode="observe"):
        g = GT.ReasoningGate(fab, game=states[0]["game"], mode=mode)
        for st in states:
            g.step(st["step"], st, ledger)
        return g

    def test_a_false_i_dont_know_refuses_false_ignorance(self, tmp_path):
        fab, gm, _aid, _bid = _gamma(tmp_path)
        AB.load_action_book(_book_dir(tmp_path))
        opener, prev = _frames()
        held = [_atom(2, 1, 2)]
        st = _state(opener, prev, book_loaded=True, cost=AB.cost_of(GAME, 2))
        g = self._run(fab, _two_steps(st),
                      _ledger(gamma=gm, book_loaded=True, held_for_action=lambda a: held))
        bets = [r for r in _gate_recs(fab) if r["terminal"] == G.BET]
        assert len(bets) == 2
        assert (bets[1]["verdict"], bets[1]["head"], bets[1]["token"]) == (
            GT.REFUSE, G.DERIVE, GT.FALSE_IGNORANCE)
        assert g.counters["would_refuse"] >= 1 and g.counters["refuse"] == 0

    def test_the_same_probe_with_the_atom_absent_passes(self, tmp_path):
        fab, gm, _aid, _bid = _gamma(tmp_path)
        AB.load_action_book(_book_dir(tmp_path))
        opener, prev = _frames()
        st = _state(opener, prev, book_loaded=True, cost=AB.cost_of(GAME, 2))
        g = self._run(fab, _two_steps(st),
                      _ledger(gamma=gm, book_loaded=True, held_for_action=lambda a: []))
        sums = _summaries(fab)
        assert sums[1]["class"] == GT.PROBE
        assert sums[1]["verdicts"] == {G.PERCEIVE: GT.PASS, G.BET: GT.PASS, G.ACT: GT.PASS}
        assert g.counters["pass"] == 1 and g.counters["refuse"] == 0
        assert sums[1]["stratum"] == 3, "n = 3 atoms + 4 traces -> floor(log2(8)) = 3"
        assert sums[1]["score"] is not None, "a probe carries its discrimination score"

    def test_no_book_is_book_absent_a_non_verdict_counted_apart(self, tmp_path):
        fab, gm, _aid, _bid = _gamma(tmp_path)
        opener, prev = _frames()
        st = _state(opener, prev, game=NOBOOK)
        g = self._run(fab, _two_steps(st),
                      _ledger(gamma=gm, game=NOBOOK, book_loaded=False))
        bets = [r for r in _gate_recs(fab) if r["terminal"] == G.BET]
        by_head = {c["head"]: c for c in bets[1]["clauses"]}
        assert (by_head[G.DERIVE]["verdict"], by_head[G.DERIVE]["token"]) == (
            GT.UNVERDICTED, GT.BOOK_ABSENT)
        assert (by_head[G.PAY]["verdict"], by_head[G.PAY]["token"]) == (
            GT.UNVERDICTED, GT.BOOK_ABSENT)
        assert bets[1]["verdict"] == GT.UNVERDICTED
        assert g.counters["pass"] == 0, "an unverdicted probe is never counted valid"
        assert g.counters["unverdicted"] == 2 and g.counters["would_refuse"] == 0
        assert _summaries(fab)[1]["stratum"] is None


# ── F5: shadow-no-block (structural + a constructed episode) ─────────────────

class TestF5ShadowNoBlock:

    def _tree(self):
        with open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                  errors="replace") as fh:
            return ast.parse(fh.read())

    def _fn(self, tree, name):
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name == name:
                return n
        raise AssertionError("%s missing from cognitive_loop.py" % name)

    def test_the_hook_is_a_void_call_and_action_num_is_never_assigned_after_it(self):
        fn = self._fn(self._tree(), "_narr_bet")
        body = list(ast.walk(fn))
        calls = [n for n in body if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "_gate_step"]
        assert len(calls) == 1, "exactly ONE hook site"
        exprs = [n for n in body if isinstance(n, ast.Expr) and n.value is calls[0]]
        assert exprs, "the hook's return must be UNBOUND (an expression statement)"
        after = [n for n in body if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign))
                 and n.lineno > calls[0].lineno]
        for n in after:
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in targets:
                assert not (isinstance(t, ast.Name) and t.id == "action_num"), (
                    "action_num assigned after the hook -- a verdict could reach the action")
        assert "action_num" not in {
            t.id for n in body if isinstance(n, ast.Assign)
            for t in n.targets if isinstance(t, ast.Name)}

    def test_gate_step_returns_nothing_and_lives_at_module_bottom(self):
        """LAW L7 (record/prereg/PREREG_SYMBOL_RECEIPTS.md, added 2026-08-21).

        THE FACT: the hook is a MODULE-LEVEL def -- not nested in a function,
        not a method on CognitiveLoop -- so that inserting it rots no receipt
        and the loop's own body is untouched. It returns nothing, and it is
        reached from exactly ONE call site.

        WAS: `tree.body[-1] is fn` -- "the module's LAST function". That is a
        POSITIONAL law of exactly the genus this build retires, and it had
        already shaped a build: the persistence builder had to place its own
        helper ABOVE the hook because bottom-append was forbidden here, the
        second such collision this week (the first was the _plan_gate tail
        slice). Appending a new module-level helper after the hook is now
        GREEN, which is what it should always have been; moving the hook into
        the class, or deleting it, is still red."""
        _laws().l7_gate_hook_is_module_level()

    def test_no_code_path_in_the_gate_returns_a_blocking_verdict(self):
        src = open(os.path.join(REPO, "engines", "egocentric", "gate.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        step = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                    and n.name == "step")
        for n in ast.walk(step):
            if isinstance(n, ast.Return):
                assert n.value is None
        assert '["refuse"] +=' not in src and "['refuse'] +=" not in src, (
            "refuse is structurally zero: nothing increments it in stage 1")

    def _loop(self, tmp_path, name):
        return SimpleNamespace(
            _ego_fabric=_fab(tmp_path, name), _game_id=GAME, _actions_taken=0,
            _ego_agent_id="a", _ego_level=0, _w2b_sched=None, _w2b_narr=None,
            _w2b_driven=None, _w2b_key=None, _w4c_counters={"mint_passed": 0},
            _narr_import_n=0, _narration=None, _narr_slots=None, _atom_verified={},
            _residual_router=None, _plan_gate={"cycles": 1}, _narr_settle=None,
            _narr_mint=None, _prev_frame=None, _ego_seeded={}, _ego_seeded_clicks={},
            _narr_route_consumed=None, _narr_mint_sig=None)

    def test_a_constructed_episode_is_byte_identical_under_off_and_observe(
            self, tmp_path, monkeypatch):
        seq = [1, 3, 6, 2, 4]
        acts = {}
        gates = {}
        for mode in (GT.MODE_OFF, GT.MODE_OBSERVE):
            monkeypatch.setenv(GT.MODE_ENV, mode)
            s = self._loop(tmp_path, "ep-" + mode)
            for i, a in enumerate(seq):
                s._actions_taken = i
                cl._narr_bet(s, a, SimpleNamespace(rung_name="explore"), {}, None)
            acts[mode] = [r["action"] for r in s._ego_fabric.query("personal", na.TOPIC)
                          if r["point"] == na.ACT]
            gates[mode] = (s._ego_fabric.query("personal", GT.TOPIC), s._reasoning_gate)
        assert acts[GT.MODE_OFF] == acts[GT.MODE_OBSERVE] == seq
        assert gates[GT.MODE_OFF][0] == [], "off: no evaluation, no records"
        assert gates[GT.MODE_OBSERVE][0], "observe: evaluated and logged"
        assert gates[GT.MODE_OBSERVE][1].counters["refuse"] == 0


# ── the deadline mechanism (Seat 3's ruling) + the ladder ────────────────────

class TestTheDeadlineMechanism:

    def test_the_mechanism_fires_on_the_constructed_config(self):
        assert GT.deadline_violation(True, GT.TOPIC) == GT.DEADLINE_REASON
        assert GT.deadline_violation(True, GT.SPINE_TOPIC) is None
        assert GT.deadline_violation(False, GT.TOPIC) is None

    def test_the_shipped_tree_is_on_the_right_side_of_the_deadline(self):
        """THE TEST THAT GOES RED AT STAGE 2 if the enforcement flag flips
        while the opener-side PERCEIVE still lives on the gate topic."""
        assert GT.deadline_violation(GT.ENFORCEMENT_ENABLED, GT.PERCEIVE_HOME) is None, (
            "stage 2 enabled enforcement without relocating PERCEIVE into the spine")
        assert GT.PERCEIVE_HOME == GT.TOPIC and GT.ENFORCEMENT_ENABLED is False

    def test_active_downgrades_to_observe_and_the_default_is_observe(self, monkeypatch):
        assert GT.resolve_mode("active") == (GT.MODE_OBSERVE, True)
        assert GT.resolve_mode("observe") == (GT.MODE_OBSERVE, False)
        assert GT.resolve_mode("off") == (GT.MODE_OFF, False)
        assert GT.resolve_mode("nonsense") == (GT.MODE_OBSERVE, False)
        monkeypatch.delenv(GT.MODE_ENV, raising=False)
        assert GT.resolve_mode() == (GT.MODE_OBSERVE, False)

    def test_ladder_x_verdicts_one_false_clause_under_all_three_values(self, tmp_path):
        opener, prev = _frames()
        # the builder STANDs "k:1 strengthened" from its own state; the ledger
        # holds no such settlement -> standing-mismatch (one false clause)
        st = _state(opener, prev, settled_atom=("k:1", na.TRANSFERRED))
        led = _ledger(settled_atom=(None, None))
        out = {}
        for mode in GT.MODES:
            fab = _fab(tmp_path, "ladder-" + mode)
            g = GT.ReasoningGate(fab, game=GAME, mode=mode)
            g.step(1, st, led)
            g.step(2, dict(st, step=2), led)
            out[mode] = (g, _gate_recs(fab))
        g, recs = out[GT.MODE_OFF]
        assert recs == [] and g.counters["evaluated"] == 0
        g, recs = out[GT.MODE_OBSERVE]
        assert g.counters["would_refuse"] == 2 and g.counters["refuse"] == 0
        assert [r["terminal"] for r in recs if r["terminal"] in ("MODE", "DOWNGRADE")] == ["MODE"]
        pv = [r for r in recs if r["terminal"] == G.PERCEIVE][0]
        assert (pv["head"], pv["token"]) == (G.STAND, GT.STANDING_MISMATCH)
        g, recs = out[GT.MODE_ACTIVE]
        assert g.mode == GT.MODE_OBSERVE and g.downgraded
        assert g.counters["would_refuse"] == 2 and g.counters["refuse"] == 0
        downs = [r for r in recs if r["terminal"] == "DOWNGRADE"]
        assert len(downs) == 1 and g.counters["downgrades"] == 1, "exactly one downgrade record"
        assert downs[0]["from"] == GT.MODE_ACTIVE and downs[0]["to"] == GT.MODE_OBSERVE
        mode_rec = [r for r in recs if r["terminal"] == "MODE"][0]
        assert mode_rec["deadline"] is None and mode_rec["bound"].startswith("BOUND")


# ── the wall (no_posthoc x utterance-builder) ────────────────────────────────

class TestTheWall:

    def test_a_builder_variant_reading_post_array_fails_the_import_check(self):
        variant = ("def _build_derive(state, ground, cls, predicted, fatal_cell):\n"
                   "    return post_array\n")
        with pytest.raises(GT.PostHocRead, match="_build_derive reads the after-state"):
            GT.check_no_posthoc(source=variant, guarded=[("gate.py", "_build_derive")])
        variant2 = "def _build_want(state, observed):\n    return observed\n"
        with pytest.raises(GT.PostHocRead):
            GT.check_no_posthoc(source=variant2, guarded=[("gate.py", "_build_want")])

    def test_the_shipped_builders_pass_and_the_settle_builder_may_read_the_opener(self):
        assert GT.check_no_posthoc() is True
        settle = "def _build_settle(state):\n    opener = state['opener']\n    return opener\n"
        assert GT.check_no_posthoc(source=settle, guarded=[("gate.py", "_build_settle")])
        assert "_narr_settle" in GT.AFTER_NAMES and "post_array" in GT.AFTER_NAMES

    def test_announce_speaks_and_audit_names_not_guarded(self):
        said = []
        GT.announce(said.append)
        assert len(said) == 1 and said[0].startswith("BOUND")
        a = GT.audit()
        assert a["not_guarded"] and any("_build_settle" in x for x in a["not_guarded"])
        assert "gate.py::_build_derive" in a["guarded"] and "gate.py::_bet_cells" in a["guarded"]


# ── the seams (each new code, each a constructed case) ───────────────────────

class TestTheSeams:

    def test_discrepancy_x_compute_d(self):
        opener, _ = _frames()
        d = GT.want_discrepancy(compose("ALL", _become([(1, 1, 2), (0, 0, 0)])))
        assert d.measure(opener) == 1.0 and d.active(opener) == [(1, 1)]
        assert d.measure(np.zeros((1, 1), dtype=int)) == -1.0, "a non-answer, passed through"
        assert d.active(np.zeros((1, 1), dtype=int)) == []
        assert GT.want_discrepancy(compose("ALL", _become([(1, 1, 1)]))).measure(opener) == 0.0

    def test_tropism_x_probe_validity_rank_never_confers_validity(self, tmp_path):
        fab, gm, _aid, _bid = _gamma(tmp_path)
        AB.load_action_book(_book_dir(tmp_path))
        rich = AB.effect_summary(GAME, 2)
        assert GT.probe_score(rich) == 1.0, "the dominant effect tracks frame change exactly"
        assert GT.probe_score(AB.effect_summary(GAME, 7)) is None, "null shape: no score"
        opener, prev = _frames()
        led = _ledger(gamma=gm, book_loaded=True, held_for_action=lambda a: [_atom(2, 1, 2)])
        v = GT.check_derive(compose(G.DERIVE, compose(G.GROUND, ref("p", "perceive")), T.PRED),
                            opener, 2, led)
        assert v["token"] == GT.FALSE_IGNORANCE, "a high-score probe on a rich action refuses"
        v = GT.check_derive(compose(G.DERIVE, compose(G.GROUND, ref("p", "perceive")), T.PRED),
                            opener, 7, led)
        assert v["verdict"] == GT.PASS, "a score-less probe on the null-shape action passes"
        zero = GT.discrimination([{"q": (1, 1)}, {"q": (1, 1)}, {"q": (0, 1)}, {"q": (0, 1)}],
                                 [True, False, True, False])
        assert zero["q"] == 0.0

    def _composed(self, tmp_path):
        fab, gm, aid, _bid = _gamma(tmp_path)
        opener, prev = _frames()
        pred = opener.copy()
        pred[1, 1] = 2
        cid = gm.compose([aid], GAME, 1)
        drive = {"composite": cid, "chain": [aid], "frame0": opener.copy(), "frames": [pred],
                 "anchors": [(1, 1)], "actions": [2]}
        st = _state(opener, prev, plan_steps=[aid], composite=cid, drive=drive,
                    chain_cursor=0, atom_of=lambda a: GT.record_of(gm, a),
                    want_cells=[(1, 1, 2)])
        return fab, gm, aid, cid, st, pred

    def test_composer_utterances_x_gate_requests(self, tmp_path):
        fab, gm, aid, cid, st, pred = self._composed(tmp_path)
        g = GT.ReasoningGate(fab, game=GAME)
        for s in _two_steps(st):
            g.step(s["step"], s, _ledger(gamma=gm))
        sums = _summaries(fab)
        assert sums[1]["class"] == GT.DERIVATION
        assert sums[1]["verdicts"] == {G.PERCEIVE: GT.PASS, G.BET: GT.PASS, G.ACT: GT.PASS}
        bet = [r for r in _gate_recs(fab) if r["terminal"] == G.BET][1]
        derive = bet["utterance"]["args"][2]
        cells = {(r, c): v for r, c, v in derive["args"][-1]["args"][1]["v"]}
        expect = {(int(r), int(c)): int(pred[r, c])
                  for r, c in np.argwhere(st["opener"] != pred)}
        assert cells == expect, "the gate's predicted cells == frames[-1]"
        kinds = [a["k"] for a in derive["args"][1:-1]]
        assert kinds == [GT.K_ATOM, GT.K_COMPOSITE], "parts execute; the composite IS the bet"
        assert bet["utterance"]["args"][3]["args"][0]["v"][0] is None, "None -> the null price"

    def test_an_unsatisfiable_want_is_a_named_refusal_not_a_silent_drop(self, tmp_path):
        fab, gm, aid, cid, st, _pred = self._composed(tmp_path)
        st = dict(st, want_cells=[(1, 1, 1)])               # already holds: vacuous
        g = GT.ReasoningGate(fab, game=GAME)
        g.step(1, st, _ledger(gamma=gm))
        bet = [r for r in _gate_recs(fab) if r["terminal"] == G.BET][0]
        assert (bet["verdict"], bet["head"], bet["token"]) == (GT.REFUSE, G.WANT, GT.VACUOUS)
        assert _summaries(fab), "never a silent drop: the SUMMARY is written"

    def test_is_citable_x_ground(self, tmp_path):
        fab, gm, aid, cid, st, _pred = self._composed(tmp_path)
        opener = st["opener"]
        pid = "g:g1:1:1"
        pterms = {pid: compose(G.PERCEIVE, _see((1, 1), 1))}
        derive = compose(G.DERIVE, compose(G.GROUND, ref(pid, "perceive")), ref(aid, "atom"),
                         ref(cid, "composite"), _become([(1, 1, 2)]))
        ground = compose(G.GROUND, ref(pid, "perceive"), ref(aid, "atom", tag=na.OWN),
                         ref(cid, "composite"))
        led = _ledger(gamma=gm)
        v = GT.check_ground(ground, derive, _records(), 1, 2, pterms, led)
        assert (v["verdict"], v["token"]) == (GT.REFUSE, GT.UNSETTLED_COMPOSITE)
        assert GT.check_derive(derive, opener, 2, led)["verdict"] == GT.PASS, (
            "the same record in the bet position is accepted: the driven chain IS the bet")
        # settle it (the supersede idiom: same id, settled True) -> GROUND flips, DERIVE unchanged
        rec = dict(C.composite_record(gm, cid))
        rec[C.SETTLED_FIELD] = True
        fab.append("collective", Gamma.TOPIC, rec)
        assert C.citation_allowed(cid, C.ROLE_GROUND, gm)
        assert GT.check_ground(ground, derive, _records(), 1, 2, pterms, led)["verdict"] == GT.PASS
        assert GT.check_derive(derive, opener, 2, led)["verdict"] == GT.PASS


# ── F6: the three-number report, and R4 on the gate stream ───────────────────

class TestF6ThreeNumberReport:

    def _summary(self, cls, stratum, verdicts=None, game=GAME):
        return {"terminal": "SUMMARY", "game": game, "class": cls, "stratum": stratum,
                "verdicts": verdicts or {G.PERCEIVE: GT.PASS, G.BET: GT.PASS, G.ACT: GT.PASS}}

    def test_a_constructed_stream_reproduces_its_class_counts_exactly(self):
        recs = ([self._summary(GT.DERIVATION, 2)] * 3 + [self._summary(GT.NEGATIVE, 2)]
                + [self._summary(GT.PROBE, 2)] * 2 + [self._summary(GT.UNBUILDABLE, 2)]
                + [self._summary(GT.PROBE, None)]
                + [self._summary(GT.PROBE, 0, {G.PERCEIVE: GT.UNVERDICTED, G.BET: GT.PASS,
                                              G.ACT: GT.PASS})]
                + [{"terminal": G.BET, "game": GAME, "verdict": GT.REFUSE,
                    "clauses": [{"head": G.DERIVE, "verdict": GT.REFUSE,
                                 "token": GT.FALSE_IGNORANCE}]}])
        narr = [{"game": GAME, "side": na.SIDE_REPLAY}] * 2 + [{"game": GAME, "side": "bet"}]
        rep = GT.coverage_report(recs, narr)
        assert rep[GAME]["strata"]["2"] == {GT.DERIVATION: 3, GT.NEGATIVE: 1, GT.PROBE: 2,
                                            GT.UNBUILDABLE: 1, "unverdicted": 0}
        assert rep[GAME]["strata"]["book-absent"][GT.PROBE] == 1
        assert rep[GAME]["strata"]["0"] == {GT.DERIVATION: 0, GT.NEGATIVE: 0, GT.PROBE: 1,
                                            GT.UNBUILDABLE: 0, "unverdicted": 1}
        assert rep[GAME]["replay"] == 2
        assert rep[GAME]["would_refuse"] == {"DERIVE:false-ignorance": 1}

    def test_r4_specificity_no_probes_reports_zero_probes_never_folded(self):
        rep = GT.coverage_report([self._summary(GT.DERIVATION, 1), self._summary(GT.NEGATIVE, 1)])
        assert rep[GAME]["strata"]["1"][GT.PROBE] == 0
        assert rep[GAME]["strata"]["1"][GT.DERIVATION] == 1
        assert rep[GAME]["strata"]["1"][GT.NEGATIVE] == 1, "never folded into derivations"
        assert GT.coverage_report([]) == {}

    def test_the_live_gate_stream_feeds_the_report(self, tmp_path):
        fab, gm, _aid, _bid = _gamma(tmp_path)
        AB.load_action_book(_book_dir(tmp_path))
        opener, prev = _frames()
        st = _state(opener, prev, book_loaded=True, cost=AB.cost_of(GAME, 2))
        g = GT.ReasoningGate(fab, game=GAME)
        for s in _two_steps(st) + [dict(st, step=2, prev=opener)]:
            g.step(s["step"], s, _ledger(gamma=gm, book_loaded=True))
        rep = GT.coverage_report(_gate_recs(fab), cost={GAME: g.cost})
        assert rep[GAME]["strata"]["3"][GT.PROBE] == 3
        assert sum(rep[GAME]["strata"]["3"].values()) == 3 + 1, "3 probes; step 0 unverdicted"
        assert g.counters["evaluated"] == 3
        # the F3 cost data: in process, read into the report, never on the stream
        assert rep[GAME]["cost"]["n"] == 3 and rep[GAME]["cost"]["total_ms"] > 0
        assert rep[GAME]["cost"]["max_ms"] >= rep[GAME]["cost"]["last_ms"]
        assert all("ms" not in r for r in _gate_recs(fab))

    def test_the_gate_stream_is_byte_identical_across_two_identical_runs(self, tmp_path):
        """The determinism law, pinned at the gate's own grain: two gates fed
        the same states write byte-identical records (json.dumps, sort_keys)."""
        outs = []
        for name in ("det-a", "det-b"):
            fab, gm, _aid, _bid = _gamma(tmp_path, name)
            opener, prev = _frames()
            st = _state(opener, prev, settled_atom=("k:1", na.TRANSFERRED))
            g = GT.ReasoningGate(fab, game=GAME, mode="active")
            for s in _two_steps(st) + [dict(st, step=2, prev=opener)]:
                g.step(s["step"], s, _ledger(gamma=gm, settled_atom=(None, None)))
            outs.append("\n".join(json.dumps(r, sort_keys=True) for r in _gate_recs(fab)))
        assert outs[0] == outs[1], "a nondeterministic field reached the gate stream"


# ── the loop hook: live assembly through _narr_bet, and known-negatives ──────

class TestTheHookAndKnownNegatives:

    def _loop(self, tmp_path, name="hook"):
        s = TestF5ShadowNoBlock()._loop(tmp_path, name)
        s._perceiver = SimpleNamespace(_to_numpy=np.asarray)
        return s

    def test_a_step_with_no_spine_bet_records_unbuildable_no_bet_not_a_refusal(self, tmp_path):
        fab = _fab(tmp_path)
        g = GT.ReasoningGate(fab, game=GAME)
        opener, prev = _frames()
        g.step(1, _state(opener, prev, spine_bet=None), _ledger())
        s = _summaries(fab)
        assert len(s) == 1 and s[0]["class"] == GT.UNBUILDABLE and s[0]["unbuildable"] == "no-bet"
        assert g.counters == dict(g.counters, unbuildable=1, would_refuse=0, refuse=0)

    def test_the_hook_assembles_agent_state_and_the_gate_ref_joins_the_spine_bet(
            self, tmp_path, monkeypatch):
        monkeypatch.setenv(GT.MODE_ENV, "observe")
        s = self._loop(tmp_path)
        opener, prev = _frames()
        s._prev_frame = prev
        cl._narr_bet(s, 2, SimpleNamespace(rung_name="explore"), {}, opener.tolist())
        recs = _gate_recs(s._ego_fabric)
        terms = [r["terminal"] for r in recs]
        assert terms == ["MODE", G.PERCEIVE, G.BET, G.ACT, "SUMMARY"]
        spine_bet = [r for r in s._ego_fabric.query("personal", na.TOPIC)
                     if r["point"] == na.BET][0]["id"]
        assert all(r["ref"] == spine_bet for r in recs if r["terminal"] != "MODE"), (
            "the streams join by data: the gate's records carry the spine BET id")
        summ = recs[-1]
        assert summ["class"] == GT.PROBE and summ["action"] == 2
        assert "ms" not in summ, "no wall-clock on a fabric stream (the determinism law)"
        assert s._reasoning_gate.cost["n"] == 1 and s._reasoning_gate.cost["last_ms"] > 0
        assert summ["stratum"] is None, "no book on this box: absent, never stratum 0"
        # the first step has no previous opener: CHANGED is unverdicted, named
        pv = recs[1]
        assert (pv["verdict"], pv["head"], pv["token"]) == (GT.UNVERDICTED, G.CHANGED,
                                                            GT.NO_PREVIOUS)

    def test_the_second_step_settles_the_first_and_changed_is_checked(self, tmp_path,
                                                                      monkeypatch):
        monkeypatch.setenv(GT.MODE_ENV, "observe")
        s = self._loop(tmp_path)
        opener, prev = _frames()
        s._prev_frame = None
        cl._narr_bet(s, 2, SimpleNamespace(rung_name="explore"), {}, prev.tolist())
        s._actions_taken = 1
        s._prev_frame = prev
        cl._narr_bet(s, 2, SimpleNamespace(rung_name="explore"), {}, opener.tolist())
        sums = _summaries(s._ego_fabric)
        assert sums[1]["verdicts"][G.PERCEIVE] == GT.PASS
        assert sums[1]["completeness"] == {"differing": 1, "reported": 1, "unreported": 0}

    def test_the_allowlist_carries_gate_citing_this_prereg(self):
        src = open(os.path.join(REPO, "tests", "gate", "test_consumers.py"),
                   encoding="utf-8").read()
        assert '"gate": (' in src and "PREREG_GATE_STAGE1_SHADOW.md" in src

    def test_untouched_by_this_stage(self):
        """narration, action_book, composer, discrepancy, effects: no gate import."""
        for name in ("narration", "action_book", "composer", "discrepancy", "effects"):
            src = open(os.path.join(REPO, "engines", "egocentric", name + ".py"),
                       encoding="utf-8").read()
            assert "egocentric import gate" not in src and "egocentric.gate" not in src
