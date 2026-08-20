"""THE APPLICABILITY INDEX MUST NEVER COST A LEGAL CANDIDATE.
PREREG_W2_APPLICABILITY_INDEX.md -- STAGE 1 (the index + the planner pre-filter).

D5 (D5_PROFILE_RESULT.md): 95.3% of a slow worker's runtime inside apply_effect
-- every atom applied at every anchor, 77.7M numpy .all() scans in one 420s
window. The build: a per-atom ANCHOR SIGNATURE (context dims, palette set, cheap
content key) stamped at mint time and DERIVED ON READ for older atoms, consulted
once per planner call to prune candidates BEFORE any apply_effect.

The falsifiers, as gated here:
  F2 (ABSOLUTE)  the pruned candidate set is a superset-or-equal of the atoms
                 apply_effect would have applied -- an atom that CAN apply is
                 NEVER pruned; and the impossible constructions ARE pruned
                 (strictness -- without it F2 passes on a filter that keeps all)
  F3             known-negative BOTH directions: wrong-palette pruned,
                 hand-placed matching atom retained
  F4             the per-atom check is O(1) set/dim comparisons -- structural:
                 the pre-filter path contains no apply_effect call, no numpy,
                 no elementwise/array comparison
  R4             a mixed population of 10 constructed atoms partitions EXACTLY
                 as expected
Plus: the mint stamps the signature at write time; the signature is DERIVED
STATE (recomputed on read, byte-equal to the stored copy); the planner's plans
are unchanged by the filter (the scope guard made executable).
"""
from __future__ import annotations

import ast
import inspect
import os
import sys
import textwrap

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import applicability as A  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import planner as P  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402

# ── constructions ─────────────────────────────────────────────────────────────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


def _recolour(v0, v1):
    """A 1-cell recolour EFFECT learned from real frames (ctx [[v0]] -> [[v1]])."""
    b = np.zeros((5, 5), dtype=int)
    b[2, 2] = v0
    a = b.copy()
    a[2, 2] = v1
    return E.learn_effect(b, 6, a)


def _recolour2(v0, v1):
    """A 2-cell recolour EFFECT (ctx [[v0, v0]] -> [[v1, v1]])."""
    b = np.zeros((5, 5), dtype=int)
    b[2, 2] = b[2, 3] = v0
    a = b.copy()
    a[2, 2] = a[2, 3] = v1
    return E.learn_effect(b, 6, a)


def _oversized():
    """An EFFECT whose context patch (9x9) exceeds a 5x5 frame in BOTH dims."""
    b = np.zeros((9, 9), dtype=int)
    a = np.full((9, 9), 3, dtype=int)
    return E.learn_effect(b, 6, a)


def _board(v):
    ws = np.zeros((5, 5), dtype=int)
    ws[2, 2] = v
    return ws


def _prune(atoms_by_id, ws, ref, gamma=None, bidirectional=True):
    """The exact call the planner makes: frame signature ONCE, then the filter."""
    fsig = A.frame_signature([ws] if ref is None else [ws, ref])
    resolver = gamma.get if gamma is not None else None
    return A.prune_candidates(sorted(atoms_by_id), atoms_by_id, fsig,
                              resolver=resolver, bidirectional=bidirectional)


# ── F2: THE ABSOLUTE ONE -- nothing that can apply is ever pruned ─────────────

def test_f2_pruned_set_is_superset_of_actual_appliers_and_strictly_prunes(tmp_path):
    """Both constructions the brief demands: an atom that matches the frame
    (MUST be retained) and atoms whose palette/dims cannot occur (MUST be
    pruned). The superset check is against apply_effect ITSELF -- the
    authority the filter must never contradict."""
    g = _gamma(tmp_path, "f2")
    ws, ref = _board(3), _board(5)
    atoms = {}
    atoms[g.add(_recolour(3, 4), "g1", 1)] = _recolour(3, 4)      # matches ws
    atoms[g.add(_recolour(7, 8), "g1", 1)] = _recolour(7, 8)      # palette impossible
    atoms[g.add(_oversized(), "g1", 1)] = _oversized()            # dims impossible

    kept = _prune(atoms, ws, ref, gamma=g)

    appliers = {aid for aid, atom in atoms.items()
                if E.apply_effect(atom, ws) is not None
                or E.apply_effect(atom, ref) is not None}
    assert appliers, "the construction must contain at least one real applier"
    assert appliers <= set(kept), (
        "F2 FALSIFIED: an atom apply_effect can apply was pruned: %r"
        % sorted(appliers - set(kept)))
    assert set(kept) < set(atoms), (
        "strictness: the impossible constructions were NOT pruned -- the "
        "filter is a no-op and F2 passed vacuously")


def test_f2_multi_step_closure_keeps_the_second_hop(tmp_path):
    """Colours are not invariant: 3->4 introduces the 4 that 4->5 needs. A
    naive frame-palette filter would prune the second hop and lose the only
    legal 2-step plan; the closure must keep it -- proven END TO END: the
    planner still returns the exact 2-step plan through the filter."""
    g = _gamma(tmp_path, "f2chain")
    id34 = g.add(_recolour(3, 4), "g1", 1)
    id45 = g.add(_recolour(4, 5), "g1", 1)
    g.add(_recolour(7, 8), "g1", 1)                       # pruned distractor rides along
    out = P.plan_to_identity(_board(3), _board(5), g, game="g1", level=1,
                             budget=100, cost_per_action=1)
    assert out is not None and out["feasible"] is True
    assert out["steps"] == [id34, id45], (
        "the filter changed WHICH plan is found -- scope guard violated")
    assert set(out) == {"steps", "feasible"}, "no filter data leaks into the dict"


# ── F3: known-negative, both directions ───────────────────────────────────────

def test_f3_wrong_palette_pruned_and_matching_retained(tmp_path):
    g = _gamma(tmp_path, "f3")
    ws, ref = _board(3), _board(9)
    good = g.add(_recolour(3, 4), "g1", 1)                # hand-placed to match ws
    bad = g.add(_recolour(7, 8), "g1", 1)                 # 7 occurs in NO frame
    atoms = {good: _recolour(3, 4), bad: _recolour(7, 8)}
    kept = _prune(atoms, ws, ref, gamma=g)
    assert good in kept, "F3 FALSIFIED: the matching atom was pruned"
    assert bad not in kept, "F3 FALSIFIED: the impossible atom was retained"


def test_f3_planner_names_the_empty_result_anchor_miss(tmp_path):
    """All candidates pruned == zero applications would have fired: the
    planner returns None with the SAME reason the exhaustive search reaches."""
    g = _gamma(tmp_path, "f3miss")
    g.add(_recolour(7, 8), "g1", 1)
    out = P.plan_to_identity(_board(3), _board(9), g, game="g1", level=1,
                             budget=100, cost_per_action=1)
    assert out is None
    assert P.last_reason() == "ANCHOR_MISS"


# ── F4: the check is O(1) per atom -- no arrays anywhere in the filter path ───

def _called_names(fn):
    """(name, lineno) of every call in fn's CODE -- AST walk, so docstrings and
    comments (which may legitimately SAY 'apply_effect') never count."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            # builtin-style calls report bare names; METHOD calls report
            # ".name" -- so ndarray .all()/.any() scans are distinguishable
            # from python's builtin any() over a generator.
            name = f.id if isinstance(f, ast.Name) else (
                "." + f.attr if isinstance(f, ast.Attribute) else None)
            if name is not None:
                out.append((name, node.lineno))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in ("np", "numpy"):
                out.append(("numpy." + node.attr, node.lineno))
    return out


def test_f4_prefilter_path_is_structurally_array_free():
    """Structural, as the prereg allows: the per-atom filter path CALLS no
    apply_effect, no numpy, no elementwise/array comparison (.all/.any),
    no asarray. (frame_signature -- the ONCE-per-call frame read -- is the
    sole numpy site and is deliberately not in this list.)"""
    per_atom_path = (A.prune_candidates, A.signature_of, A.anchor_signature,
                     A._derive, A._typed_requirement, A.inverse_signature,
                     A.colour_universe, A._patch_dims, A._patch_palette,
                     A._content_key, A._valid)
    banned = {"apply_effect", ".apply_effect", ".all", ".any",
              "asarray", ".asarray"}
    for fn in per_atom_path:
        for name, line in _called_names(fn):
            assert name not in banned and not name.startswith("numpy."), (
                "F4 FALSIFIED: %s calls %r (line %d) -- the signature check "
                "must be set/dim comparisons only" % (fn.__name__, name, line))


def test_f4_planner_consults_the_filter_before_any_application():
    calls = _called_names(P.plan_to_identity)
    prune = [ln for name, ln in calls if name == "prune_candidates"]
    fsig = [ln for name, ln in calls if name == "frame_signature"]
    applies = [ln for name, ln in calls
               if name in ("apply_effect", ".apply_effect",
                           "apply_inverse", ".apply_inverse")]
    assert prune, "the planner does not consult the index"
    assert fsig, "the frame signature is not read per call"
    assert applies and min(prune) < min(applies), (
        "the filter must run before the application machinery, not after")


# ── R4: a mixed population of 10 partitions exactly as expected ───────────────

def test_r4_mixed_population_partitions_exactly(tmp_path):
    g = _gamma(tmp_path, "r4")
    ws, ref = _board(3), _board(5)                        # base palette {0, 3, 5}
    expected_kept, expected_pruned, atoms = [], [], {}

    def add(atom, kept):
        aid = g.add(atom, "g1", 1)
        atoms[aid] = atom
        (expected_kept if kept else expected_pruned).append(aid)
        return aid

    add(_recolour(3, 4), kept=True)                       # matches ws directly
    add(_recolour(4, 5), kept=True)                       # closure: 3->4 writes the 4
    add(_recolour(0, 3), kept=True)                       # matches the ground
    add(_recolour(6, 3), kept=True)                       # inverse path: 3 in ref side
    add(_recolour2(3, 4), kept=True)                      # 2-cell, matches ws
    add(_recolour(7, 8), kept=False)                      # 7/8 occur nowhere, ever
    add(_recolour(9, 7), kept=False)                      # 9/7 occur nowhere, ever
    add(_oversized(), kept=False)                         # 9x9 context on 5x5 frames
    add(_recolour2(7, 1), kept=False)                     # neither 7 nor 1 reachable
    add(_recolour(8, 9), kept=False)                      # 8/9 occur nowhere, ever
    assert len(atoms) == 10

    kept = _prune(atoms, ws, ref, gamma=g)
    assert set(kept) == set(expected_kept), (
        "R4 FALSIFIED: partition mismatch -- wrongly pruned %r, wrongly kept %r"
        % (sorted(set(expected_kept) - set(kept)),
           sorted(set(kept) - set(expected_kept))))
    assert kept == [aid for aid in sorted(atoms) if aid in set(expected_kept)], (
        "the filter must preserve candidate order")


def test_r4_forward_only_mode_drops_the_inverse_path(tmp_path):
    """In goal mode there is no reference to walk backward from: 6->3 (kept
    above ONLY through its inverse) must now be pruned -- and that is sound,
    because no forward-reachable state ever contains a 6."""
    g = _gamma(tmp_path, "r4fwd")
    a34 = g.add(_recolour(3, 4), "g1", 1)
    a63 = g.add(_recolour(6, 3), "g1", 1)
    atoms = {a34: _recolour(3, 4), a63: _recolour(6, 3)}
    kept = _prune(atoms, _board(3), None, gamma=g, bidirectional=False)
    assert a34 in kept
    assert a63 not in kept


# ── conservatism: what the filter cannot bound, it must keep ──────────────────

def test_unknown_ttype_and_composite_are_never_pruned(tmp_path):
    """A mechanism this module cannot reason about must not be filtered --
    even when its palette looks impossible."""
    g = _gamma(tmp_path, "unk")
    weird = {"kind": "EFFECT", "arity": 2, "key": "eff-weird", "action": 6,
             "context": [[7]], "transform": {"before": [[7]], "after": [[8]]},
             "changed": 1, "ttype": "WARP_DRIVE", "params": {}}
    wid = g.add(weird, "g1", 1)
    a34 = g.add(_recolour(3, 4), "g1", 1)
    cid = g.compose([a34], "g1", 1)
    atoms = {wid: weird, a34: _recolour(3, 4), cid: g.get(cid)}
    kept = _prune(atoms, _board(3), _board(5), gamma=g)
    assert wid in kept, "unknown ttype was pruned -- conservatism violated"
    assert cid in kept, "a composite was pruned -- conservatism violated"


def test_effect_if_prunes_on_condition_dims_only(tmp_path):
    """An EFFECT_IF whose condition cells lie off the frame can NEVER return;
    one whose cells fit must be kept (a false condition still yields a frame)."""
    then_atom = _recolour(3, 4)
    off = {"kind": "EFFECT_IF", "arity": 3, "key": "effif-off", "action": 6,
           "condition": {"cells": [[6, 6, 1]]}, "then": then_atom, "else": None,
           "changed": 1}
    on = {"kind": "EFFECT_IF", "arity": 3, "key": "effif-on", "action": 6,
          "condition": {"cells": [[1, 1, 9]]}, "then": then_atom, "else": None,
          "changed": 1}
    ws = _board(3)
    assert E.apply_effect(off, ws) is None, "construction error: off-frame fires"
    assert E.apply_effect(on, ws) is not None, "construction error: on-frame inert"
    atoms = {"off:0": off, "on:1": on}
    fsig = A.frame_signature([ws])
    kept = A.prune_candidates(sorted(atoms), atoms, fsig)
    assert "on:1" in kept
    assert "off:0" not in kept


# ── the index is derived state, written at the mint site ──────────────────────

def test_mint_stamps_the_signature_and_read_rederives_it_identically(tmp_path):
    g = _gamma(tmp_path, "mint")
    mint = MDLMint(g)
    b = np.zeros((5, 5), dtype=int)
    b[2, 2] = 1
    a = b.copy()
    a[2, 2] = 2
    out = mint.consider(b, 6, a, game="g1", level=1)
    assert out["verdict"] == "mint", "construction error: the recolour must mint"
    rec = g.fabric.query("collective", g.TOPIC)[-1]
    atom = rec["atom"]
    assert A.ASIG_FIELD in atom, "the mint site did not stamp the signature"
    stored = atom[A.ASIG_FIELD]
    assert stored["v"] == A.ASIG_VERSION
    assert (stored["h"], stored["w"]) == (1, 1) and stored["pal"] == [1]
    # DERIVED STATE: strip the field; the read side rebuilds the identical
    # signature from the atom content alone -- the store is never the sole holder.
    stripped = {k: v for k, v in atom.items() if k != A.ASIG_FIELD}
    assert A.signature_of(stripped) == stored, (
        "backfill-on-read does not reproduce the mint-time signature -- the "
        "index would fork into two truths")
    assert A.signature_of(atom) == stored, "a valid stored signature must be used"


def test_pre_field_atoms_backfill_on_read(tmp_path):
    """Atoms written before this build (Gamma.add without the mint stamp) carry
    no asig -- the read side must derive one, never demand a migration."""
    g = _gamma(tmp_path, "old")
    aid = g.add(_recolour(3, 4), "g1", 1)
    atom = g.get(aid)
    assert A.ASIG_FIELD not in atom, "construction error: g.add must not stamp"
    sig = A.signature_of(atom)
    assert sig["v"] == A.ASIG_VERSION
    assert (sig["h"], sig["w"]) == (1, 1) and sig["pal"] == [3]
    assert sig["ck"], "the content key must derive too"


# ── the scope guard, executable: existing planner outcomes are unchanged ──────

def test_planner_reasons_unchanged_by_the_filter(tmp_path):
    """The reason vocabulary and the outcomes of the test_none_reasons
    constructions survive the filter verbatim."""
    g = _gamma(tmp_path, "reasons")
    g.add(_recolour(3, 4), "g1", 1)
    out = P.plan_to_identity(_board(3), _board(9), g, game="g1", level=1,
                             budget=100, cost_per_action=1)
    assert out is None and P.last_reason() == "NO_MEET"   # fired, drained, no meet
