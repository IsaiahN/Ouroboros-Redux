"""RUNG-4 GATE: THE FOURTH BRANCH — DECLINED is expressible (instrument only).

⭐ WHY (THE_LADDER.md, RUNG-4 READ PREP). The consumer's outcome enum was
{consumed, not_found, candidates}: MATCHED-AND-REJECTED DID NOT EXIST in the
vocabulary. Every guard between match and candidate-emission that refused a
comparison fell through to not_found, making "never-matched" the UNION of two
states — a genuinely empty (or fully-evaluated) search, and an offer that
arrived with atoms present but was declined without a verdict. This gate splits
them: the impoverished-description guard in match() (the base-rate skip,
previously silent) now persists an axis-tagged kind="declined" record whose
reason comes from a FIXED enum; not_found henceforth means STRICTLY
never-matched. Readers (pending / open_not_found) tolerate the new kind so the
Chaitin reopen machinery is unchanged; the report dict and the [IMPORT]
narration carry the count. A source-scan (AST) test pins the routing so no
future guard drifts declines back into not_found — the level-convention defect
class: one site updated, another still routing declines where they always went.

Run pre-build: the decline tests failed (kind="declined" absent from the enum).
"""
from __future__ import annotations

import ast
import inspect
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric.effects import learn_effect
from engines.egocentric.fabric import KnowledgeFabric

# ── fixtures (the triangulation gate's synthetic shapes, kept local) ──────────


def _recolour(n=5, cells=((2, 2),), src=2, dst=3):
    b = np.full((n, n), src, dtype=int)
    a = b.copy()
    for r, c in cells:
        a[r, c] = dst
    return b, a


def _home(tmp_path, name="home"):
    return KnowledgeFabric(str(tmp_path / name), agent_id="agentA", kin_key="kinA")


def _sigma_atom(fabric, key="eff-oth", src=2, dst=3, sigma=None, agent="agentB"):
    """One atom record carrying a FULL prediction signature (all invariants),
    unless an explicit (possibly impoverished) sigma is handed in."""
    b, a = _recolour(src=src, dst=dst)
    atom = learn_effect(b, 1, a)
    atom["key"] = key
    atom["sigma"] = consumer.sigma_of(b, a) if sigma is None else dict(sigma)
    return fabric.append("collective", "atoms",
                         {"id": key + ":0", "type": "structural", "game": "g_src",
                          "level": 1, "agent": agent, "atom": atom})


def _enqueue_rich(fabric, before, after, residual=1.0):
    return fabric.append("collective", "import_queue", {
        "slot": "WORKSPACE", "residual": float(residual),
        "before": [[int(v) for v in row] for row in np.asarray(before)],
        "after": [[int(v) for v in row] for row in np.asarray(after)]})


def _enqueue_impoverished(fabric, residual=4.0):
    """A patch-less residual: describe() degrades to slot + mag — the
    impoverished description whose match walk is refused atom by atom."""
    return fabric.append("collective", "import_queue",
                         {"slot": "WORKSPACE", "residual": float(residual)})


def _queue_rows(fabric):
    return KnowledgeFabric(fabric.root, agent_id="agentA",
                           kin_key="kinA").query("collective", "import_queue")


def _kinds(fabric, kind):
    return [r for r in _queue_rows(fabric) if r.get("kind") == kind]


# ── the FIXED enum ────────────────────────────────────────────────────────────


class TestTheFixedEnum:

    def test_the_decline_vocabulary_is_fixed_and_exported(self):
        assert consumer.KIND_DECLINED == "declined"
        assert consumer.DECLINED_IMPOVERISHED == "impoverished"
        assert isinstance(consumer.DECLINE_REASONS, tuple), "the enum must be FIXED"
        assert consumer.DECLINED_IMPOVERISHED in consumer.DECLINE_REASONS
        for name in ("KIND_DECLINED", "DECLINED_IMPOVERISHED", "DECLINE_REASONS"):
            assert name in consumer.__all__


# ── the fourth branch: DECLINED, not not_found ────────────────────────────────


class TestDeclinedBranch:

    def test_impoverished_drain_records_declined_not_not_found(self, tmp_path):
        """THE FINDING MADE EXPRESSIBLE: atoms present, every comparison refused
        by the base-rate guard — previously a silent fall-through to not_found."""
        home = _home(tmp_path)
        _sigma_atom(home)                              # a full-sigma atom IS present
        raw = _enqueue_impoverished(home)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["drained"] == 1
        assert rep["declined"] == 1, "the decline was not recorded as declined"
        assert rep["not_found"] == 0, (
            "an impoverished drain with atoms present fell through to not_found "
            "-- never-matched is still a union of two states")
        assert rep["candidates"] == 0
        dec = _kinds(home, "declined")
        assert len(dec) == 1
        assert dec[0]["reason"] == consumer.DECLINED_IMPOVERISHED
        assert dec[0]["reason"] in consumer.DECLINE_REASONS, "reason outside the FIXED enum"
        assert dec[0]["src_seq"] == raw["seq"]
        assert dec[0]["axis"] == "vocabulary"
        assert _kinds(home, "not_found") == [], "a shadow not_found was also written"

    def test_declined_record_carries_the_reopen_vocabulary(self, tmp_path):
        """Additive shape: a not_found superset (+ kind/reason/counts), so the
        Chaitin machinery reads it with no special case."""
        home = _home(tmp_path)
        _sigma_atom(home)
        _enqueue_impoverished(home)
        consumer.consume(home, "g_home", 1, 8)
        rec = _kinds(home, "declined")[0]
        for field in ("sigma", "axis", "atoms_seen", "priority_seq",
                      "near_misses", "game", "level", "src_seq"):
            assert field in rec, "declined record lost the %r reopen field" % field
        assert rec["declined_atoms"] == 1 and rec["evaluated_atoms"] == 0

    def test_all_atom_sigmas_impoverished_is_also_a_decline(self, tmp_path):
        """The guard trips on EITHER side: a full residual description against
        atoms whose sigmas lack the invariants is still a refusal, not a search."""
        home = _home(tmp_path)
        _sigma_atom(home, sigma={"arity": 2, "mag": "small"})   # invariants missing
        b, a = _recolour()
        _enqueue_rich(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["declined"] == 1 and rep["not_found"] == 0
        assert _kinds(home, "declined")[0]["axis"] == "any"


# ── not_found means STRICTLY never-matched ────────────────────────────────────


class TestNotFoundIsStrictlyNeverMatched:

    def test_genuine_no_match_still_not_found(self, tmp_path):
        """A fully-evaluated search that misses on >= 2 invariants is the real
        never-matched — it stays not_found and stays reopenable."""
        home = _home(tmp_path)
        _sigma_atom(home, dst=3)                       # 1 cell, 2 -> 3
        b, a = _recolour(cells=((1, 1), (3, 3)), dst=9)  # 2 cells, 2 -> 9
        _enqueue_rich(home, b, a, residual=2.0)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["not_found"] == 1 and rep["declined"] == 0
        assert _kinds(home, "declined") == []
        assert len(consumer.open_not_found(home)) == 1

    def test_empty_search_is_not_a_decline(self, tmp_path):
        """No atoms anywhere: silence is never a decline verdict (Chaitin) —
        the pre-fix compat behavior, byte-for-byte."""
        home = _home(tmp_path)
        _enqueue_impoverished(home)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["not_found"] == 1 and rep["declined"] == 0
        assert consumer.open_not_found(home)[0]["axis"] == "vocabulary"

    def test_unsigmad_atoms_are_an_empty_search(self, tmp_path):
        """An atom with NO sigma cannot be recognized (backfill) — nothing was
        offered, so nothing was declined."""
        home = _home(tmp_path)
        b, a = _recolour()
        atom = learn_effect(b, 1, a)
        atom["key"] = "eff-unsig"                      # deliberately sigma-less
        home.append("collective", "atoms",
                    {"id": "eff-unsig:0", "type": "structural", "game": "g_src",
                     "level": 1, "agent": "agentB", "atom": atom})
        _enqueue_rich(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["not_found"] == 1 and rep["declined"] == 0

    def test_near_miss_retry_path_unchanged(self, tmp_path):
        """One failing invariant -> ONE redescription retry -> axis-tagged
        not_found: evaluated comparisons happened, so this is never a decline."""
        home = _home(tmp_path)
        _sigma_atom(home, dst=3)
        b, a = _recolour(dst=7)                        # colour_delta alone fails
        _enqueue_rich(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["retried"] == 1 and rep["not_found"] == 1
        assert rep["declined"] == 0
        assert consumer.open_not_found(home)[0]["axis"] == "colour_delta"


# ── candidates unchanged ──────────────────────────────────────────────────────


class TestCandidatesUnchanged:

    def test_hit_path_emits_the_same_candidate(self, tmp_path):
        home = _home(tmp_path)
        _sigma_atom(home)
        b, a = _recolour()
        _enqueue_rich(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["candidates"] == 1 and rep["declined"] == 0
        cands = consumer.candidates(home, "g_home", 1)
        assert len(cands) == 1
        cand = cands[0]
        assert cand["atom"]["key"] == "eff-oth"
        tc = cand["three_conditions"]
        assert tc["priority_seq"] < tc["match_seq"]
        assert tc["atom_mint_seq"] < tc["match_seq"]
        assert _kinds(home, "declined") == [] and _kinds(home, "not_found") == []


# ── readers tolerate the new kind; the Chaitin reopen path is whole ───────────


class TestReadersTolerate:

    def test_declined_item_is_closed_not_redrained(self, tmp_path):
        home = _home(tmp_path)
        _sigma_atom(home)
        _enqueue_impoverished(home)
        consumer.consume(home, "g_home", 1, 8)
        assert consumer.pending(home) == [], "a declined item re-listed as pending"
        rep2 = consumer.consume(home, "g_home", 1, 8)
        assert rep2["drained"] == 0

    def test_declined_reopens_when_a_new_atom_touches_the_axis(self, tmp_path):
        """Zero behavior change on the reopen machinery: a declined item re-looks
        exactly as its not_found ancestor did, and — still impoverished — records
        declined again, never not_found."""
        home = _home(tmp_path)
        _sigma_atom(home, key="eff-one")
        _enqueue_impoverished(home)
        rep1 = consumer.consume(home, "g_home", 1, 8)
        assert rep1["declined"] == 1
        rep2 = consumer.consume(home, "g_home", 1, 8)
        assert rep2["reopened"] == 0, "reopened on the same silence"
        _sigma_atom(home, key="eff-two")               # the axis is touched
        rep3 = consumer.consume(home, "g_home", 1, 8)
        assert rep3["reopened"] == 1
        assert rep3["declined"] == 1 and rep3["not_found"] == 0
        standing = consumer.open_not_found(home)
        assert len(standing) == 1 and standing[0]["kind"] == "declined"

    def test_compat_old_not_found_records_still_close_and_reopen(self, tmp_path):
        """Books written by the pre-decline consumer read identically: the old
        not_found closes its raw, stands open, and reopens into a candidate."""
        home = _home(tmp_path)
        raw = _enqueue_impoverished(home)
        rep = consumer.consume(home, "g_home", 1, 8)   # old-world outcome: not_found
        assert rep["not_found"] == 1
        assert consumer.pending(home) == []
        nf = consumer.open_not_found(home)
        assert len(nf) == 1 and nf[0]["kind"] == "not_found"
        assert nf[0]["src_seq"] == raw["seq"]
        b, a = _recolour()
        raw2 = _enqueue_rich(home, b, a)
        _sigma_atom(home)                              # now a matching atom exists
        rep2 = consumer.consume(home, "g_home", 1, 8)
        assert rep2["drained"] == 1 and rep2["candidates"] == 1
        assert {c["src_seq"] for c in consumer.candidates(home, "g_home", 1)} == {raw2["seq"]}


# ── the report and the narration carry the count ──────────────────────────────


class TestReportAndNarration:

    def test_report_always_carries_declined(self, tmp_path):
        rep = consumer.consume(_home(tmp_path), "g_home", 1, 8)
        assert rep.get("declined") == 0, "the report dict lost the declined counter"

    def test_import_narration_carries_declined(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8").read()
        i = src.index("[IMPORT] consumed")
        block = src[i:i + 400]
        assert "declined=" in block, (
            "the [IMPORT] consumed narration does not carry the declined count")


# ── drift-proofing: no code path routes a match into not_found ────────────────


def _consumer_tree():
    return ast.parse(inspect.getsource(consumer))


def _parent_map(tree):
    par = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            par[child] = node
    return par


def _calls_to(tree, names):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id in names]


def _in_any(node, stmts):
    return any(node is walked for stmt in stmts for walked in ast.walk(stmt))


def _guarded_by_hits(call, par, want_no_hits):
    """True iff an ancestor `if hits:` has the call on its no-hits (orelse) arm
    — or its hits (body) arm when want_no_hits is False. `if not hits:` guards
    are honored symmetrically."""
    node = call
    while node in par:
        parent = par[node]
        if isinstance(parent, ast.If):
            test = parent.test
            plain = isinstance(test, ast.Name) and test.id == "hits"
            negated = (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
                       and isinstance(test.operand, ast.Name)
                       and test.operand.id == "hits")
            if plain and _in_any(call, parent.orelse if want_no_hits
                                 else parent.body):
                return True
            if negated and _in_any(call, parent.body if want_no_hits
                                   else parent.orelse):
                return True
        node = parent
    return False


class TestRoutingIsDriftProof:
    """The level-convention defect class, pre-empted at the source level: one
    site gets updated, another keeps routing declines to not_found because
    that is where they always went. These scans pin the routing law."""

    def test_no_give_up_writer_is_reachable_after_a_match(self):
        """EVERY call to _not_found / _declined sits on the no-hits arm of an
        `if hits:` — no code path records a give-up after a successful match."""
        tree = _consumer_tree()
        par = _parent_map(tree)
        calls = _calls_to(tree, {"_not_found", "_declined"})
        assert calls, "the give-up writers are never called — the branch is gone"
        for call in calls:
            assert _guarded_by_hits(call, par, want_no_hits=True), (
                "line %d: %s() is reachable with hits non-empty — a matched item "
                "can be recorded as a give-up" % (call.lineno, call.func.id))

    def test_the_hit_writer_only_fires_on_a_match(self):
        tree = _consumer_tree()
        par = _parent_map(tree)
        calls = _calls_to(tree, {"_close_hit"})
        assert calls, "_close_hit is never called — the hit branch is gone"
        for call in calls:
            assert _guarded_by_hits(call, par, want_no_hits=False), (
                "line %d: _close_hit() is reachable without hits" % call.lineno)

    def test_single_write_sites_per_kind(self):
        """The literal kind values are written by exactly one function each:
        not_found by _not_found, declined by _declined — so the routing law
        above covers every write of both kinds."""
        tree = _consumer_tree()
        par = _parent_map(tree)
        for kind, owner in (("not_found", "_not_found"), ("declined", "_declined")):
            writers = set()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Dict):
                    continue
                for k, v in zip(node.keys, node.values, strict=True):
                    if not (isinstance(k, ast.Constant) and k.value == "kind"):
                        continue
                    if isinstance(v, ast.Constant):
                        val = v.value
                    elif isinstance(v, ast.Name):        # e.g. KIND_DECLINED
                        val = getattr(consumer, v.id, None)
                    else:
                        continue
                    if val != kind:
                        continue
                    fn = node
                    while fn in par and not isinstance(fn, ast.FunctionDef):
                        fn = par[fn]
                    writers.add(getattr(fn, "name", "<module>"))
            assert writers <= {owner}, (
                "kind=%r is written outside %s(): %r" % (kind, owner, writers))
