"""THE ACTION BOOK MUST BE DERIVED, EVIDENCE-COUNTED, AND REBUILDABLE -- NEVER AUTHORED.

STAGE 0 of PROPOSAL_REASONING_GATE.md §3: per (game, action) semantics the
agent can CITE, derived entirely from its own recorded history (the Γ atoms
stream + the action_traces DB, budget columns included). Authored action
semantics would be checking-against-us; derived ones are the agent's history
made citable.

The falsifiers, as gated here (constructed fixtures throughout; no .runs
dependency):

  R4   constructed atom streams + trace rows produce EXACTLY the expected
       book: effect distributions (changed-cell stats, ttypes, colour deltas,
       TRANSLATE dx/dy), inverse pairs with correct evidence n from BOTH
       sources (trace frame-restoration pairs f0-a->f1-b->f0 with f1 != f0;
       typed atom deltas composed to identity through effects.invert_transform),
       and cost evidence from the budget columns.
  F1   known-negative: an action with no evidence yields EXPLICIT nulls with
       the NAMED reason (verbatim strings asserted); an inverse claim with
       n=1 is reported with n=1 and never promoted; all-null budget columns
       yield cost null with "no traces with non-null budget".
  F2   derived-not-authored: structurally, neither module contains an
       int-keyed dict literal (no hardcoded action->meaning map); and the
       whole derivation is PERMUTATION-EQUIVARIANT -- relabel the action ints
       in the inputs and the book relabels with them, byte-for-byte after the
       same relabelling. Nothing can be keyed to what an action "is".
  F3   rebuild identity: running the builder twice over the same box is
       byte-identical output, the header carries the source stream positions,
       and the sources are untouched (read-only, asserted on bytes).

Seeded with a FIXED CONSTANT (the prereg date), never a clock.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sqlite3
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import action_book as AB  # noqa: E402
from tools import build_action_book as BAB  # noqa: E402

SEED = 20260820  # fixed constant (the prereg date) -- deterministic forever

F0 = [[0, 0], [0, 0]]
F1_ = [[1, 0], [0, 0]]
F2_ = [[2, 0], [0, 0]]


# ── constructions ─────────────────────────────────────────────────────────────

def _atom_rec(i, action, changed=1, ttype=None, params=None, colour_delta=None,
              game="gx-1", rid=None):
    atom = {"kind": "EFFECT", "arity": 2, "key": "eff-%d" % i,
            "action": action, "changed": changed,
            "context": [[1]], "transform": {"before": [[1]], "after": [[2]]}}
    if ttype is not None:
        atom["ttype"] = ttype
        atom["params"] = params or {}
    sigma = {"arity": 2, "bbox": "rect", "conserved": False}
    if colour_delta is not None:
        sigma["colour_delta"] = colour_delta
    atom["sigma"] = sigma
    return {"id": rid or ("eff-%d:%d" % (i, i)), "type": "structural",
            "game": game, "level": 1, "seq": i, "atom": atom}


def _trace(i, sess, action, fb, fa, score=0.0, bt=None, bs=None, game="gx-1"):
    return {"id": i, "session_id": sess, "game_id": game,
            "action_number": action, "score_change": score,
            "budget_total": bt, "budget_spend": bs,
            "frame_before": json.dumps(fb), "frame_after": json.dumps(fa)}


def _corpus():
    """The constructed history: TRANSLATE inverses across actions 2/3 (atoms),
    a COLOUR_PERM inverse pair 4/5 (atoms), frame-restoration pairs 3/4
    (traces, n=2 one way and n=1 the other), one untyped atom on 6, budget
    evidence on 6 only, and action 7 seen ONLY in traces."""
    atoms = []
    for k in range(3):
        atoms.append(_atom_rec(10 + k, 2, changed=2, ttype="TRANSLATE",
                               params={"dx": 1, "dy": 0, "fill": 0}))
    for k in range(2):
        atoms.append(_atom_rec(20 + k, 3, changed=4, ttype="TRANSLATE",
                               params={"dx": -1, "dy": 0, "fill": 0}))
    atoms.append(_atom_rec(30, 4, changed=1, ttype="COLOUR_PERM",
                           params={"mapping": [[1, 2]]}, colour_delta=[[1, 2]]))
    atoms.append(_atom_rec(31, 5, changed=1, ttype="COLOUR_PERM",
                           params={"mapping": [[2, 1]]}, colour_delta=[[2, 1]]))
    atoms.append(_atom_rec(40, 6, changed=17, colour_delta=[[0, 9], [9, 0]]))
    # a SUPERSEDING append (same id, e.g. ctx_min): an update, never a new
    # observation -- the fold must dedupe by id last-wins
    atoms.append(_atom_rec(10, 2, changed=2, ttype="TRANSLATE",
                           params={"dx": 1, "dy": 0, "fill": 0},
                           rid="eff-10:10"))
    traces = [
        _trace(1, "s1", 3, F0, F1_),
        _trace(2, "s1", 4, F1_, F0),
        _trace(3, "s1", 3, F0, F1_),
        _trace(4, "s1", 4, F1_, F0),
        _trace(5, "s2", 6, F0, F2_, score=1.0, bt=10.0, bs=0.5),
        _trace(6, "s2", 6, F2_, F2_, score=0.0, bt=10.0, bs=0.25),
        _trace(7, "s2", 7, F2_, F2_),
    ]
    return atoms, traces


def _book():
    atoms, traces = _corpus()
    return BAB.build_book("boxa", atoms, traces, trace_games=["gx-1"])


# ── R4: the constructed history produces EXACTLY the expected book ────────────

def test_r4_effect_distributions_exact():
    book = _book()
    assert book["coverage"]["actions_seen"] == [2, 3, 4, 5, 6, 7]
    a2 = book["actions"]["2"]
    # superseding append deduped: 3 observations, not 4
    assert a2["atoms"]["n"] == 3, (
        "R4 FALSIFIED: a superseding same-id append was counted as a new "
        "observation (got n=%r)" % a2["atoms"]["n"])
    assert a2["atoms"]["changed_cells"] == {"n": 3, "min": 2.0, "max": 2.0,
                                            "mean": 2.0}
    assert a2["atoms"]["ttypes"] == {"TRANSLATE": 3}
    assert a2["atoms"]["translate"] == [{"dx": 1, "dy": 0, "n": 3}]
    assert a2["atoms"]["colour_deltas"] is None
    assert a2["atoms"]["colour_deltas_absent"] == BAB.R_NO_COLOUR_DELTA
    a6 = book["actions"]["6"]
    assert a6["atoms"]["ttypes"] == {"NONE": 1}
    assert a6["atoms"]["colour_deltas"] == [{"delta": [[0, 9], [9, 0]], "n": 1}]
    assert a6["atoms"]["translate"] is None
    assert a6["atoms"]["translate_absent"] == BAB.R_NO_TRANSLATE


def test_r4_trace_distributions_and_cost_exact():
    book = _book()
    a3 = book["actions"]["3"]
    assert a3["traces"] == {"n": 2, "frame_changed_n": 2,
                            "frame_change_rate": 1.0,
                            "score": {"n": 2, "zero_n": 2, "pos_n": 0,
                                      "neg_n": 0, "min": 0.0, "max": 0.0,
                                      "sum": 0.0}}
    a6 = book["actions"]["6"]
    assert a6["traces"]["n"] == 2 and a6["traces"]["frame_changed_n"] == 1
    assert a6["traces"]["frame_change_rate"] == 0.5
    assert a6["traces"]["score"]["pos_n"] == 1 and a6["traces"]["score"]["sum"] == 1.0
    # COST: the budget columns, read at last (produced-and-unread until now)
    assert a6["cost"] == {"n": 2,
                          "budget_spend": {"n": 2, "min": 0.25, "max": 0.5,
                                           "mean": 0.375},
                          "budget_total": {"n": 2, "min": 10.0, "max": 10.0,
                                           "mean": 10.0}}
    # action 2 never traced: explicit nulls, named reason
    a2 = book["actions"]["2"]
    assert a2["traces"] is None and a2["traces_absent"] == BAB.R_NO_TRACES_ACTION
    assert a2["cost"] is None and a2["cost_absent"] == BAB.R_NO_TRACES_ACTION


def test_r4_inverse_pairs_with_correct_evidence_n():
    book = _book()
    inv = book["inverses"]
    # traces: f0 -3-> f1 -4-> f0 twice => (3,4) n=2; the middle restoration
    # f1 -4-> f0 -3-> f1 => (4,3) n=1
    assert inv["3"]["pairs"]["4"] == {"n_traces": 2, "n_atoms": 0}
    # atoms: 3 TRANSLATE(+1,0) on action 2 x 2 TRANSLATE(-1,0) on action 3
    # => 6 ordered pairs each way (composed through effects.invert_transform)
    assert inv["2"]["pairs"] == {"3": {"n_traces": 0, "n_atoms": 6}}
    assert inv["3"]["pairs"]["2"] == {"n_traces": 0, "n_atoms": 6}
    assert inv["4"]["pairs"] == {"3": {"n_traces": 1, "n_atoms": 0},
                                 "5": {"n_traces": 0, "n_atoms": 1}}
    assert inv["5"]["pairs"] == {"4": {"n_traces": 0, "n_atoms": 1}}
    cov = book["coverage"]
    assert sorted(cov["inverse_pairs_n2"]) == sorted(
        ["3<-2 n=6", "2<-3 n=6", "4<-3 n=2"])
    assert sorted(cov["inverse_pairs_n1"]) == sorted(["3<-4", "5<-4", "4<-5"])
    assert cov["cost_evidence"] is True


def test_r4_two_noops_never_fake_an_inverse_pair():
    """f2 == f0 trivially when a changed nothing: two no-ops must not count
    as 'b undoes a' -- the pair requires a REAL change restored."""
    traces = [_trace(1, "s", 1, F0, F0), _trace(2, "s", 2, F0, F0)]
    book = BAB.build_book("b", None, traces)
    assert book["inverses"]["1"]["pairs"] is None
    assert BAB.R_NO_FRAME_PAIRS in book["inverses"]["1"]["reason"]


def test_r4_a_broken_chain_never_pairs():
    """A replay seam (frame_before of step 2 != frame_after of step 1) is not
    consecutive play: no pair, whatever the frames claim."""
    traces = [_trace(1, "s", 1, F0, F1_), _trace(2, "s", 2, F2_, F0)]
    book = BAB.build_book("b", None, traces)
    assert book["inverses"]["1"]["pairs"] is None


# ── F1: known-negative -- explicit nulls, named reasons, n=1 stays n=1 ────────

def test_f1_no_evidence_is_an_explicit_null_with_the_named_reason():
    book = _book()
    a7 = book["actions"]["7"]                 # seen ONLY in traces
    assert a7["atoms"] is None
    assert a7["atoms_absent"] == BAB.R_NO_ATOMS_ACTION == \
        "no atoms recorded for this action"
    assert a7["cost"] is None
    assert a7["cost_absent"] == BAB.R_NO_BUDGET == \
        "no traces with non-null budget"
    inv7 = book["inverses"]["7"]
    assert inv7["pairs"] is None
    assert BAB.R_NO_FRAME_PAIRS in inv7["reason"]
    assert BAB.R_NO_TYPED_ATOMS in inv7["reason"]
    # an ABSENT source is a DIFFERENT named reason than a silent one
    no_src = BAB.build_book("b", None, [_trace(1, "s", 1, F0, F1_)])
    a1 = no_src["actions"]["1"]
    assert a1["atoms"] is None
    assert a1["atoms_absent"] == BAB.R_NO_ATOM_STREAM
    db_less = BAB.build_book("b", [_atom_rec(1, 1)], None)
    b1 = db_less["actions"]["1"]
    assert b1["traces"] is None and b1["traces_absent"] == BAB.R_NO_TRACE_DB
    assert b1["cost"] is None and b1["cost_absent"] == BAB.R_NO_TRACE_DB


def test_f1_an_n1_inverse_is_reported_as_n1_never_promoted():
    book = _book()
    assert book["inverses"]["5"]["pairs"]["4"] == {"n_traces": 0, "n_atoms": 1}
    assert "4<-5" in book["coverage"]["inverse_pairs_n1"]
    assert not any(s.startswith("4<-5 ")
                   for s in book["coverage"]["inverse_pairs_n2"]), (
        "F1 FALSIFIED: an n=1 inverse claim was promoted into the n>=2 report")


# ── F2: derived, never authored ───────────────────────────────────────────────

def _int_keyed_dict_literals(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if (isinstance(key, ast.Constant)
                        and isinstance(key.value, int)
                        and not isinstance(key.value, bool)):
                    hits.append(node.lineno)
    return hits


def test_f2_no_hardcoded_action_semantics_structurally():
    """No int-keyed dict literal exists in either module -- there is nowhere
    an authored action->meaning table could live. Everything is keyed by what
    the RECORDS said."""
    for rel in ("engines/egocentric/action_book.py",
                "tools/build_action_book.py"):
        hits = _int_keyed_dict_literals(os.path.join(REPO, rel))
        assert not hits, (
            "F2 FALSIFIED: %s carries an int-keyed dict literal at lines %r "
            "-- a hardcoded action mapping is authored semantics" % (rel, hits))


_PAIR2 = re.compile(r"^(\d+)<-(\d+) n=(\d+)$")
_PAIR1 = re.compile(r"^(\d+)<-(\d+)$")


def _relabel(book, perm):
    """The book with every action int relabelled through `perm` -- what a
    derived-only artifact MUST equal when the inputs are relabelled."""
    out = json.loads(json.dumps(book))
    out["actions"] = {str(perm[int(k)]): v for k, v in book["actions"].items()}
    inv = {}
    for k, v in book["inverses"].items():
        v2 = dict(v)
        if v.get("pairs"):
            v2["pairs"] = {str(perm[int(b)]): ev
                           for b, ev in v["pairs"].items()}
        inv[str(perm[int(k)])] = v2
    out["inverses"] = inv
    cov = dict(book["coverage"])
    cov["actions_seen"] = sorted(perm[a] for a in book["coverage"]["actions_seen"])
    cov["inverse_pairs_n2"] = sorted(
        "%d<-%d n=%s" % (perm[int(m.group(1))], perm[int(m.group(2))], m.group(3))
        for m in map(_PAIR2.match, book["coverage"]["inverse_pairs_n2"]))
    cov["inverse_pairs_n1"] = sorted(
        "%d<-%d" % (perm[int(m.group(1))], perm[int(m.group(2))])
        for m in map(_PAIR1.match, book["coverage"]["inverse_pairs_n1"]))
    out["coverage"] = cov
    return out


def test_f2_permutation_equivariance_nothing_keys_on_what_an_action_is():
    perm = {2: 11, 3: 5, 4: 2, 5: 9, 6: 3, 7: 8}
    atoms, traces = _corpus()
    atoms_p = json.loads(json.dumps(atoms))
    for rec in atoms_p:
        rec["atom"]["action"] = perm[rec["atom"]["action"]]
    traces_p = [dict(t, action_number=perm[t["action_number"]]) for t in traces]
    book = BAB.build_book("boxa", atoms, traces, trace_games=["gx-1"])
    book_p = BAB.build_book("boxa", atoms_p, traces_p, trace_games=["gx-1"])
    assert book_p == _relabel(book, perm), (
        "F2 FALSIFIED: relabelling the action ints in the INPUTS did not "
        "relabel the book identically -- something in the derivation is "
        "keyed to specific action numbers (authored semantics)")


# ── F3: rebuild identity, end to end, sources untouched ───────────────────────

def _make_box(tmp_path):
    box = tmp_path / "boxa"
    coll = box / "ego_fabric" / "collective"
    coll.mkdir(parents=True)
    atoms, traces = _corpus()
    with open(coll / "atoms.jsonl", "w", encoding="utf-8") as fh:
        for rec in atoms:
            fh.write(json.dumps(rec) + "\n")
    conn = sqlite3.connect(str(box / "core_data.db"))
    conn.execute(
        "CREATE TABLE action_traces (id INTEGER PRIMARY KEY, session_id TEXT,"
        " game_id TEXT, action_number INTEGER, score_change REAL,"
        " budget_total REAL, budget_spend REAL, frame_before TEXT,"
        " frame_after TEXT)")
    for t in traces:
        conn.execute(
            "INSERT INTO action_traces VALUES (?,?,?,?,?,?,?,?,?)",
            (t["id"], t["session_id"], t["game_id"], t["action_number"],
             t["score_change"], t["budget_total"], t["budget_spend"],
             t["frame_before"], t["frame_after"]))
    conn.commit()
    conn.close()
    return box


def test_f3_rebuild_is_byte_identical_and_sources_untouched(tmp_path):
    box = _make_box(tmp_path)
    atoms_path = box / "ego_fabric" / "collective" / "atoms.jsonl"
    db_path = box / "core_data.db"
    src_atoms = atoms_path.read_bytes()
    src_db = db_path.read_bytes()
    assert BAB.main([str(box)]) == 0
    out = box / "ego_fabric" / "collective" / "action_book.json"
    first = out.read_bytes()
    assert BAB.main([str(box)]) == 0
    assert out.read_bytes() == first, (
        "F3 FALSIFIED: two builder runs over the SAME inputs diverged -- the "
        "artifact is not a pure derivation")
    assert atoms_path.read_bytes() == src_atoms, (
        "the builder MODIFIED its atoms source stream -- forbidden")
    assert db_path.read_bytes() == src_db, (
        "the builder MODIFIED its traces DB source -- forbidden")
    book = json.loads(first.decode("utf-8"))
    # the header says it rebuilds from scratch and carries source positions
    assert "REBUILT FROM SCRATCH" in book["derived"]
    assert book["sources"]["atoms_stream"]["records_read"] == 9
    assert book["sources"]["atoms_stream"]["last_seq"] == 40
    assert book["sources"]["traces_db"]["rows_read"] == 7
    assert book["sources"]["traces_db"]["max_trace_id"] == 7
    assert book["game_ids"] == ["gx-1"]


def test_f3_the_artifact_never_holds_anything_the_sources_do_not(tmp_path):
    """Delete the artifact, rebuild: identical. The book may never be the
    sole holder of anything (derived state, like the applicability index)."""
    box = _make_box(tmp_path)
    assert BAB.main([str(box)]) == 0
    out = box / "ego_fabric" / "collective" / "action_book.json"
    first = out.read_bytes()
    out.unlink()
    assert BAB.main([str(box)]) == 0
    assert out.read_bytes() == first


# ── the read side: load + query helpers ───────────────────────────────────────

def test_load_and_query_helpers(tmp_path):
    box = _make_box(tmp_path)
    assert BAB.main([str(box)]) == 0
    book = AB.load_action_book(str(box))
    assert book is not None and book["box"] == "boxa"
    # registered under BOTH the box name and the recorded game id
    assert AB.effect_summary("boxa", 6) == AB.effect_summary("gx-1", 6)
    e6 = AB.effect_summary("boxa", 6)
    assert e6["atoms"]["ttypes"] == {"NONE": 1}
    assert e6["cost"]["n"] == 2
    # an action the book never saw: the explicit-null shape, named reason
    e99 = AB.effect_summary("boxa", 99)
    assert e99["atoms"] is None and e99["atoms_absent"] == AB.NO_EVIDENCE
    assert e99["cost"] is None and e99["cost_absent"] == AB.NO_EVIDENCE
    # an unloaded game is None -- absence of a book is not evidence
    assert AB.effect_summary("no-such-game", 1) is None
    # inverse_of: most evidence wins (action 3: b=2 n=6 beats b=4 n=2)
    assert AB.inverse_of("boxa", 3) == (2, 6)
    assert AB.inverse_of("boxa", 4) == (3, 1), (
        "n=1 must be REPORTED as n=1 (tie on n breaks to smallest b), never "
        "promoted and never hidden")
    assert AB.inverse_of("boxa", 7) is None
    assert AB.inverse_of("no-such-game", 3) is None
    # cost_of: evidence or None, never a default price
    assert AB.cost_of("boxa", 6) == {"n": 2,
                                     "budget_spend": {"n": 2, "min": 0.25,
                                                      "max": 0.5, "mean": 0.375},
                                     "budget_total": {"n": 2, "min": 10.0,
                                                      "max": 10.0, "mean": 10.0}}
    assert AB.cost_of("boxa", 3) is None
    assert AB.cost_of("boxa", 99) is None


def test_load_absent_or_malformed_book_is_none(tmp_path):
    assert AB.load_action_book(str(tmp_path / "nowhere")) is None
    box = tmp_path / "boxbad"
    coll = box / "ego_fabric" / "collective"
    coll.mkdir(parents=True)
    (coll / "action_book.json").write_text("{not json", encoding="utf-8")
    assert AB.load_action_book(str(box)) is None
    (coll / "action_book.json").write_text('{"artifact": "other"}',
                                           encoding="utf-8")
    assert AB.load_action_book(str(box)) is None
