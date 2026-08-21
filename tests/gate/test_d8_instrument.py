"""D-8 GATE (PREREG_D8_FALLBACK_INSTRUMENT.md): the fallback instrument.

ONE FIELD, NO BEHAVIOUR CHANGE. The cognitive router's selected rung produces no
usable action on ~4 of 5 cycles on the deepest games and falls through to the
thresholdless weighted vote (_decide_weighted_non_emergency). The only evidence
so far was a LABEL LEAK (rung == "weighted_random" -- a lower bound: a fallback
vote >= 0.15 takes the real winner's name). The instrument converts the lower
bound into a measurement: ``last_decision_metadata['weighted_fallback']`` is set
True immediately before the fallback call and False on the other branch, and
the ACT narration record carries ``fallback`` read the same way ``rung`` is.

The build falsifiers under test:
  F1 · BOTH WAYS       -- a constructed decide() whose router yields an available
                          action -> ACT fallback=False; one whose router yields
                          nothing (or an unavailable action) -> fallback=True with
                          the winner label left EXACTLY as the leak produces it.
  F2 · NEVER ABSENT    -- the field is on every ACT record: the emitter writes it
                          unconditionally, the loop's one emission site passes it,
                          a cf without the attribute still reads False.
  F3 · BYTE-IDENTICAL  -- the flag is WRITE-ONLY in the decider (AST: never read),
                          and a seeded corpus decides the same actions with the
                          instrument and with it STRIPPED from the tree's own
                          source by AST (the counterfactual derived from the tree).
  R4 · THE BITMAP      -- a constructed 10-cycle sequence reproduces its exact
                          fallback bitmap on the ACT stream (sensitivity), and an
                          all-available sequence never fabricates a True.
  KNOWN-NEGATIVE       -- the ladder strategy (never reaches the router) records
                          False, never True -- including its OWN 'weighted_fallback'
                          rung LABEL, which is not the flag.
"""
from __future__ import annotations

import ast
import os
import random
import sys
import types
from types import SimpleNamespace

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl  # noqa: E402
import decision_rung_system as drs  # noqa: E402
from engines.cognition.cognitive_frame import CognitiveFrame  # noqa: E402
from engines.egocentric import narration as na  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from rungs.base import RungResult  # noqa: E402

KEY = "weighted_fallback"
ROUTER_RUNG = "scripted_rung"


# ---------------------------------------------------------------------------
# constructed parts: a scripted router, legacy rungs, the loop seam
# ---------------------------------------------------------------------------

class _Rung:
    """A constructed legacy rung: votes ``action`` at ``confidence`` (None = abstains)."""
    category = "hypothesis"

    def __init__(self, name, action=None, confidence=0.0, priority=10):
        self.name = name
        self.enabled = True
        self.confidence_threshold = 0.3
        self.priority_override = None
        self._action, self._conf, self._prio = action, confidence, priority

    def evaluate(self, game_state, context):
        return RungResult(action=self._action, confidence=self._conf, reason="constructed")

    def get_priority(self):
        return self._prio

    def record_outcome(self, was_accepted, outcome_score=0.0):
        pass


class _Router:
    """A scripted cognitive router: each decide() yields the next scripted value as
    the selected rung's action -- an action string, or None (the rung yielded
    nothing). The rung_executor bridge is exercised on every call."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def initialize(self, nodes, edges, game_id):
        pass

    def get_statistics(self):
        return {"total_decisions": self.calls, "total_fallbacks": 0, "fallback_rate": 0.0}

    def decide(self, game_state, rung_executor):
        self.calls += 1
        rung_executor(ROUTER_RUNG, game_state)
        return SimpleNamespace(action_value=self.script.pop(0), action=ROUTER_RUNG,
                               confidence=0.5, reasoning="scripted", path=[],
                               final_quadrant="Q1", iterations=1, time_elapsed=0.0)


class _NoTemporal:
    def get_rung_modulation(self, **kw):
        return {}

    def get_exploration_appetite(self, **kw):
        return 0.5


def _fresh(ds, router, rungs):
    """Reset a constructed system to a known state with the given router + rungs."""
    ds.rungs = list(rungs)
    ds._cognitive_router = router
    ds._cognitive_router_initialized = True
    ds.last_decision_metadata = {}
    ds.total_decisions = 0
    ds.rung_wins = {}
    ds._last_winning_rung = None
    if hasattr(ds, "_cognitive_game_id"):
        del ds._cognitive_game_id
    ds._engine_registry = None          # ACTION6 coordinates: the random strategy only
    ds._routing_trace_store = None
    ds._temporal_integrator = _NoTemporal()
    return ds


@pytest.fixture(scope="module")
def cog():
    return drs.DecisionRungSystem(strategy="cognitive", cognitive_router=_Router([]))


@pytest.fixture(scope="module")
def lad():
    return drs.DecisionRungSystem(strategy="ladder")


def _ctx(available=(1, 2, 3), **extra):
    c = {"available_actions": list(available), "game_id": "g1", "agent_id": "a",
         "game_type": "t", "level": 1}
    c.update(extra)
    return c


def _gs():
    return SimpleNamespace(frame=None)


def _fab(tmp_path, name="f"):
    return KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")


def _loop(tmp_path, name="f"):
    """A constructed loop namespace at the narration seam (the arms-test pattern):
    enough real state for _narr_bet to run the LOOP'S OWN emission path."""
    return SimpleNamespace(
        _ego_fabric=_fab(tmp_path, name), _game_id="g1", _actions_taken=0,
        _ego_agent_id="a", _ego_level=0,
        _w2b_sched=None, _w2b_narr=None, _w2b_driven=None, _w2b_key=None,
        _w4c_counters={"mint_passed": 0}, _narr_import_n=0,
        _narration=None, _narr_slots=None, _atom_verified={},
        _residual_router=None, _plan_gate={"cycles": 1},
        _narr_settle=None, _narr_mint=None, _prev_frame=None,
        _ego_seeded={}, _ego_seeded_clicks={},
        _narr_route_consumed=None, _narr_mint_sig=None)


def _cf(md):
    """The loop's REASONED stamp, mirrored: rung_name and fallback ride together
    (_act()'s pair is pinned structurally in TestTheWiring)."""
    return SimpleNamespace(action_speed="reasoned", action_confidence=0.0,
                           rung_name=md.get("rung_name", md.get("rung", "")),
                           fallback=cl._d8_fallback(md))


def _acts(loop):
    return [r for r in loop._ego_fabric.query("personal", na.TOPIC)
            if r["point"] == na.ACT]


def _decide_and_act(ds, loop, step, ctx=None):
    """One cycle at the seam: decide() -> cf (the loop's read) -> the ACT record."""
    loop._actions_taken = step
    action, reason = ds.decide(_gs(), ctx or _ctx())
    cl._narr_bet(loop, int(action.replace("ACTION", "")), _cf(ds.last_decision_metadata), {})
    return action, reason


# ---------------------------------------------------------------------------
# F1 -- both directions
# ---------------------------------------------------------------------------

class TestF1BothDirections:

    def test_router_yields_an_available_action_records_false(self, cog, tmp_path):
        ds = _fresh(cog, _Router(["ACTION1"]), [_Rung("voter", "ACTION2", 0.9)])
        s = _loop(tmp_path)
        action, _ = _decide_and_act(ds, s, 0)
        assert action == "ACTION1", "the router's action is taken as-is"
        md = ds.last_decision_metadata
        assert md[KEY] is False and md["rung_name"] == ROUTER_RUNG
        act = _acts(s)[0]
        assert act["fallback"] is False and act["rung"] == ROUTER_RUNG

    def test_router_yields_nothing_records_true_and_keeps_the_leaked_label(
            self, cog, tmp_path):
        """The fallback's best score >= 0.15: the LABEL becomes the winner's name
        (the leak) -- the field is additive, the leak is NOT removed."""
        ds = _fresh(cog, _Router([None]), [_Rung("voter", "ACTION2", 0.9)])
        s = _loop(tmp_path)
        action, reason = _decide_and_act(ds, s, 0)
        assert action == "ACTION2" and "Weighted fallback" in reason
        md = ds.last_decision_metadata
        assert md[KEY] is True
        assert md["rung_name"] == "voter", (
            "the winner label must be left exactly as the leak produces it")
        act = _acts(s)[0]
        assert act["fallback"] is True and act["rung"] == "voter"

    def test_router_yields_an_unavailable_action_is_the_fallback_too(self, cog, tmp_path):
        ds = _fresh(cog, _Router(["ACTION5"]), [_Rung("voter", "ACTION2", 0.9)])
        s = _loop(tmp_path)
        action, _ = _decide_and_act(ds, s, 0, _ctx([1, 2, 3]))
        assert action == "ACTION2"
        assert ds.last_decision_metadata[KEY] is True
        assert _acts(s)[0]["fallback"] is True

    def test_the_weighted_random_label_leak_is_left_as_it_is(self, cog, tmp_path):
        """Best score < 0.15: today's lower-bound label survives beside the flag."""
        ds = _fresh(cog, _Router([None]), [_Rung("whisper", "ACTION2", 0.01)])
        s = _loop(tmp_path)
        random.seed(3)
        action, _ = _decide_and_act(ds, s, 0)
        assert action in ("ACTION1", "ACTION2", "ACTION3")
        md = ds.last_decision_metadata
        assert md["rung_name"] == "weighted_random" and md[KEY] is True
        assert _acts(s)[0]["rung"] == "weighted_random"
        assert _acts(s)[0]["fallback"] is True

    def test_an_action6_fallback_keeps_the_flag_through_both_coordinate_stamps(
            self, cog):
        """The ACTION6 stamps REPLACE the metadata dict (the fallback's own at
        weighted_random/winner, then the cognitive path's) -- the flag must
        survive both, or the deepest games' clicks would read as absent."""
        random.seed(5)
        ds = _fresh(cog, _Router([None]), [_Rung("clicker", "ACTION6", 0.9)])
        action, _ = ds.decide(_gs(), _ctx([1, 6]))
        assert action == "ACTION6"
        md = ds.last_decision_metadata
        assert "x" in md and "y" in md, "the coordinate stamp happened"
        assert md[KEY] is True, "the flag was lost in the dict replacement"
        # and the weighted_random ACTION6 stamp (the one that drops every key)
        ds = _fresh(cog, _Router([None]), [_Rung("whisper", "ACTION6", 0.01)])
        action, _ = ds.decide(_gs(), _ctx([6]))
        assert action == "ACTION6"
        assert ds.last_decision_metadata[KEY] is True


# ---------------------------------------------------------------------------
# F2 -- never absent on ACT
# ---------------------------------------------------------------------------

class TestF2NeverAbsent:

    def test_the_emitter_writes_the_field_unconditionally(self, tmp_path):
        sp = na.NarrationSpine(_fab(tmp_path), game="g1")
        for step, fb in enumerate((None, False, True)):
            sp.start_step(step)
            b, w = na.predict_bin(True, False)
            sp.bet({}, b, w, None, na.GUARD_SUPPORT, rng=na.EP)
            if fb is None:
                sp.act(6, "explore", rng=na.EP)          # the pre-D8 call shape
            else:
                sp.act(6, "explore", rng=na.EP, fallback=fb)
        acts = [r for r in sp.fabric.query("personal", na.TOPIC) if r["point"] == na.ACT]
        assert [a["fallback"] for a in acts] == [False, False, True]
        for a in acts:
            assert isinstance(a["fallback"], bool), "a strict bool, never unknown"

    def test_the_loop_emission_carries_it_even_when_cf_lacks_the_attribute(
            self, tmp_path):
        s = _loop(tmp_path)
        pre_d8_cf = SimpleNamespace(rung_name="", action_speed="explore",
                                    action_confidence=0.0)
        cl._narr_bet(s, 6, pre_d8_cf, {})
        s._actions_taken = 1
        cl._narr_bet(s, 6, SimpleNamespace(rung_name="r", action_speed="reasoned",
                                           action_confidence=0.0, fallback=True), {})
        acts = _acts(s)
        assert len(acts) == 2
        assert acts[0]["fallback"] is False, "absence on cf reads False, never unknown"
        assert acts[1]["fallback"] is True

    def test_the_frame_default_and_the_loop_read_are_false_when_absent(self):
        assert CognitiveFrame().fallback is False
        assert cl._d8_fallback({}) is False and cl._d8_fallback(None) is False
        assert cl._d8_fallback({"rung_name": "x"}) is False
        assert cl._d8_fallback({KEY: True}) is True
        assert cl._d8_fallback({KEY: 1}) is True and cl._d8_fallback({KEY: 0}) is False

    def test_every_act_emission_path_passes_it_structural(self):
        src = _src("cognitive_loop.py")
        calls = [i for i in range(len(src)) if src.startswith(".act(", i)]
        assert len(calls) == 1, "exactly ONE ACT emission path in the loop"
        body = _body(src, "_narr_bet")
        assert ".act(" in body, "the emission lives in _narr_bet"
        call = body[body.index(".act("):body.index(".act(") + 160]
        assert "fallback=" in call, "the loop's ACT emission does not pass the field"
        nsrc = _src(os.path.join("engines", "egocentric", "narration.py"))
        act_def = _body(nsrc, "act(")
        assert '"fallback": bool(fallback)' in act_def, (
            "the emitter must write the field on every ACT record")


# ---------------------------------------------------------------------------
# F3 -- decisions byte-identical with and without the instrument
# ---------------------------------------------------------------------------

CORPUS = [
    ("ACTION1", "strong"), (None, "strong"), ("ACTION5", "strong"), (None, "whisper"),
    ("ACTION2", "whisper"), (None, "strong"), (None, "whisper"), ("ACTION3", "strong"),
    (None, "a6"), ("ACTION1", "whisper"), (None, "whisper"), (None, "strong"),
    ("ACTION6", "a6"), (None, "a6"),
]
RUNGS = {
    "strong": lambda: [_Rung("voter", "ACTION2", 0.9)],
    "whisper": lambda: [_Rung("whisper", "ACTION2", 0.01)],
    "a6": lambda: [_Rung("clicker", "ACTION6", 0.9)],
}


def _run_corpus(mod, seed):
    ds = _fresh(mod.DecisionRungSystem(strategy="cognitive", cognitive_router=_Router([])),
                _Router([v for v, _ in CORPUS]), [])
    random.seed(seed)
    out = []
    for _v, spec in CORPUS:
        ds.rungs = RUNGS[spec]()
        action, _ = ds.decide(_gs(), _ctx([1, 2, 3, 6]))
        out.append((action, ds.last_decision_metadata.get("rung_name")))
    return out


class _StripInstrument(ast.NodeTransformer):
    """Remove the instrument from the tree's own source: every store to the
    ``weighted_fallback`` key (subscript assignment or dict-display key). The
    'rung_name' LABEL 'weighted_fallback' is a value, not a key -- untouched."""

    def __init__(self):
        self.removed = 0

    @staticmethod
    def _is_key(n):
        return isinstance(n, ast.Constant) and n.value == KEY

    def visit_Assign(self, node):
        self.generic_visit(node)
        t = node.targets[0]
        if len(node.targets) == 1 and isinstance(t, ast.Subscript) and self._is_key(t.slice):
            self.removed += 1
            return None
        return node

    def visit_Dict(self, node):
        self.generic_visit(node)
        keep = [(k, v) for k, v in zip(node.keys, node.values, strict=True)
                if not (k is not None and self._is_key(k))]
        if len(keep) != len(node.keys):
            self.removed += 1
            node.keys, node.values = [k for k, _ in keep], [v for _, v in keep]
        return node


def _stripped_module():
    path = os.path.join(REPO, "decision_rung_system.py")
    tree = ast.parse(_src("decision_rung_system.py"), filename=path)
    stripper = _StripInstrument()
    tree = stripper.visit(tree)
    for n in ast.walk(tree):                   # a branch emptied by the strip
        for attr in ("body", "orelse", "finalbody"):
            seq = getattr(n, attr, None)
            if isinstance(seq, list) and not seq and attr == "body":
                seq.append(ast.Pass())
    ast.fix_missing_locations(tree)
    text = ast.unparse(tree)
    assert "['weighted_fallback'] =" not in text and "'weighted_fallback':" not in text, (
        "the strip left an instrument store behind")
    assert "'rung_name': 'weighted_fallback'" in text, "the ladder LABEL is not the flag"
    mod = types.ModuleType("drs_stripped")
    mod.__file__ = path
    exec(compile(tree, path, "exec"), mod.__dict__)  # noqa: S102 -- the counterfactual
    return mod, stripper.removed


class TestF3ByteIdentity:

    def test_the_flag_is_write_only_in_the_decider(self):
        """The decider never READS the key: no Load subscript, no .get/.pop/
        .setdefault, no comparison -- so no decision can depend on it."""
        tree = ast.parse(_src("decision_rung_system.py"))
        stores, reads = 0, []
        for n in ast.walk(tree):
            if isinstance(n, ast.Subscript) and _StripInstrument._is_key(n.slice):
                if isinstance(n.ctx, ast.Store):
                    stores += 1
                else:
                    reads.append(ast.dump(n))
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("get", "pop", "setdefault") and n.args
                    and _StripInstrument._is_key(n.args[0])):
                reads.append(ast.dump(n))
            if isinstance(n, ast.Compare) and any(
                    _StripInstrument._is_key(c) for c in [n.left, *n.comparators]):
                reads.append(ast.dump(n))
        assert stores >= 2, "the two assignment sites are missing"
        assert reads == [], "the instrument is READ in the decider: %r" % (reads,)

    def test_a_seeded_corpus_decides_identically_with_and_without_the_instrument(self):
        stripped, removed = _stripped_module()
        assert removed >= 5, "the strip removed nothing -- the counterfactual is hollow"
        with_it = _run_corpus(drs, 11)
        without = _run_corpus(stripped, 11)
        assert [a for a, _ in with_it] == [a for a, _ in without], (
            "the chosen actions differ with the instrument present -- NOT a "
            "no-behaviour-change build")
        assert [r for _, r in with_it] == [r for _, r in without], (
            "the rung labels differ -- the leak was altered")
        assert _run_corpus(drs, 11) == with_it, "the corpus is not deterministic"
        assert any(a == "ACTION6" for a, _ in with_it), "the corpus must exercise ACTION6"
        assert any(r == "weighted_random" for _, r in with_it), "and the random leak"


# ---------------------------------------------------------------------------
# R4 -- the bitmap
# ---------------------------------------------------------------------------

class TestR4Bitmap:
    BITMAP = [True, False, True, True, False, False, True, False, True, True]

    def test_a_constructed_10_cycle_sequence_reproduces_the_exact_bitmap(
            self, cog, tmp_path):
        script = [None if b else "ACTION1" for b in self.BITMAP]
        ds = _fresh(cog, _Router(script), [_Rung("voter", "ACTION2", 0.9)])
        s = _loop(tmp_path)
        for i in range(10):
            _decide_and_act(ds, s, i)
        acts = _acts(s)
        assert len(acts) == 10, "one ACT record per cycle"
        assert [a["fallback"] for a in acts] == self.BITMAP, (
            "the constructed fallback bitmap was not reproduced on the ACT stream "
            "(R4 sensitivity): %r" % [a["fallback"] for a in acts])
        assert [a["rung"] for a in acts] == [
            "voter" if b else ROUTER_RUNG for b in self.BITMAP], (
            "the leaked winner label on fallback steps, the router's rung otherwise")
        assert [a["action"] for a in acts] == [2 if b else 1 for b in self.BITMAP]

    def test_specificity_an_all_available_sequence_never_fabricates_a_true(
            self, cog, tmp_path):
        ds = _fresh(cog, _Router(["ACTION1"] * 6), [_Rung("voter", "ACTION2", 0.9)])
        s = _loop(tmp_path)
        for i in range(6):
            _decide_and_act(ds, s, i)
        assert [a["fallback"] for a in _acts(s)] == [False] * 6


# ---------------------------------------------------------------------------
# KNOWN-NEGATIVE -- the ladder never records True
# ---------------------------------------------------------------------------

class TestKnownNegativeLadder:

    def test_a_ladder_win_records_false(self, lad, tmp_path):
        ds = _fresh(lad, None, [_Rung("climber", "ACTION1", 0.9)])
        s = _loop(tmp_path)
        action, _ = _decide_and_act(ds, s, 0)
        assert action == "ACTION1"
        md = ds.last_decision_metadata
        assert md["rung_name"] == "climber" and md[KEY] is False
        assert _acts(s)[0]["fallback"] is False

    def test_the_ladders_own_weighted_fallback_label_is_not_the_flag(self, lad, tmp_path):
        """The ladder's post-ladder random choice is LABELLED 'weighted_fallback'
        -- a rung_name string, not the D-8 flag. It must read False."""
        ds = _fresh(lad, None, [_Rung("mute", None, 0.0)])
        s = _loop(tmp_path)
        random.seed(2)
        for i in range(4):
            _decide_and_act(ds, s, i, _ctx([1, 2, 3, 6]))
            md = ds.last_decision_metadata
            assert md["rung_name"] == "weighted_fallback"
            assert md[KEY] is False, "the ladder recorded the cognitive fallback"
        assert [a["fallback"] for a in _acts(s)] == [False] * 4

    def test_the_replay_fast_path_never_carries_a_stale_true(self, cog):
        """The cognitive path's metadata dict persists across cycles: after a
        fallback cycle, a replay fast-path cycle (which returns before the
        branch) must read False, not the previous cycle's True."""
        ds = _fresh(cog, _Router([None, "ACTION1"]), [_Rung("voter", "ACTION2", 0.9)])
        ds.decide(_gs(), _ctx())
        assert ds.last_decision_metadata[KEY] is True
        action, reason = ds.decide(_gs(), _ctx(is_replay=True, active_sequence=["ACTION3"],
                                               sequence_position=0))
        assert action == "ACTION3" and "Replay fast-path" in reason
        md = ds.last_decision_metadata
        assert md["rung_name"] == "three_try_sequence"
        assert md[KEY] is False, "a stale True rode the replay fast-path"


# ---------------------------------------------------------------------------
# THE WIRING -- the sites, in the ruled shape (source law)
# ---------------------------------------------------------------------------

def _src(rel):
    return open(os.path.join(REPO, rel), encoding="utf-8", errors="replace").read()


def _body(src, name):
    i = src.find("def %s" % name)
    assert i != -1, "%s missing" % name
    j = src.find("\n    def ", i + 10)
    return src[i:j if j != -1 else len(src)]


class TestTheWiring:

    def test_the_true_site_is_the_statement_immediately_before_the_fallback_call(self):
        body = _body(_src("decision_rung_system.py"), "_decide_cognitive")
        call = "self._decide_weighted_non_emergency(game_state, context)"
        t, c = body.index("['weighted_fallback'] = True"), body.index(call)
        assert t < c, "True must be set BEFORE the call overwrites the label"
        between = body[t:c].split("\n")[1:-1]
        assert all(ln.strip().startswith("#") or not ln.strip() for ln in between), (
            "a statement sits between the True assignment and the fallback call")
        f = body.index("['weighted_fallback'] = False", t)
        assert f > c, "the False site is the other branch at the same level"

    def test_the_ladder_stamps_false_wherever_rung_name_is_and_never_true(self):
        body = _body(_src("decision_rung_system.py"), "_decide_ladder(")
        assert body.count("'weighted_fallback'] = False") == 2
        assert body.count("'weighted_fallback': False") == 1
        assert "'weighted_fallback'] = True" not in body
        assert "'weighted_fallback': True" not in body

    def test_act_stamps_cf_fallback_beside_rung_name(self):
        """The REASONED block of _act (SPEED 2) is where rung_name is read off
        last_decision_metadata onto cf; the flag is read in the same breath."""
        body = _body(_src("cognitive_loop.py"), "_act(")
        assert "cf.fallback = _d8_fallback(md)" in body, (
            "the loop never reads the flag onto cf -- the ACT record would be blind")
        assert body.index("cf.rung_name = md.get(") < body.index("cf.fallback = _d8_fallback(md)")
        assert body.index("cf.fallback = _d8_fallback(md)") < body.index("cf.action_confidence = md.get(")

    def test_the_emitter_is_still_one_append_no_queries(self):
        nsrc = _src(os.path.join("engines", "egocentric", "narration.py"))
        assert nsrc.count(".append(") == 1
        assert ".query" not in nsrc and "query_tail" not in nsrc
