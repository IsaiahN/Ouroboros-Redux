"""COMPOSER STAGE 1 -- THE FACTORING: postcondition signatures, composite
signature + price (PROPOSAL_COMPOSER_DESIGN.md §6.1 + amendments;
COMPOSITION_VIA_SIGNATURES.md Q2/Q5 and the pricing convergence).

The build under test:
  (1) applicability.postcondition_signature -- the atom's POSTCONDITION,
      factored from what the atom already stores (Q2: sigma had most of it):
      after-patch dims, colours WRITTEN, changed count + the changed-mask
      content key (the mint's _signature hashing shape), palette-after.
      Stamped by the mint BESIDE the anchor signature at all three asig write
      sites (consider / _merge_context / _reinstate); psig_of backfills on
      read; NO-CLAIM degrade, total, DONT_CARE never leaks.
  (2) Gamma.compose derives-and-stores the composite's precondition signature
      AND price at compose time (applicability.composite_signature -- ONE
      derivation, Q5's convergence): precondition = step 1's minimised
      context requirement + each later step's UNGUARANTEED RESIDUE (context
      cells no prior step's stored after-patch establishes);
      price = start_extent + Σ unguaranteed_residue + length.
  (3) applicability's COMPOSITE branch returns the stored derived
      precondition (composites become index-visible and pruneable); any
      doubt degrades to NO-REQUIREMENT (kept, never pruned).
  (4) consumer.admission_price prices composites by the stored derived price
      with the mint's own inequality (constants imported, never duplicated)
      -- the unpriced-composite admission hole closes.

The falsifiers, as gated here (known-negative BOTH directions on each):
  R4  constructed atoms produce EXACTLY the expected postcondition
      signatures, minimised DONT_CARE-bearing atoms included (the sentinel
      never leaks into any psig field); unreadable degrades to NO-CLAIM.
  F1  chain discount, DERIVED-EXECUTABLE (amendment 3): a well-chained pair
      (A writes exactly what B requires) prices start_extent + 0 + 2; an
      unrelated pair prices start_extent + B's full requirement + 2 -- both
      numbers computed HERE from the same stored patches the code reads.
  F2  composite index visibility: wrong-dims and wrong-palette composites
      are PRUNED by prune_candidates; a matching one is retained; an
      underivable composite degrades to NO-REQUIREMENT and is never pruned.
  F3  the admission hole closes: a constructed wide composite is REFUSED at
      the derived price with the price recorded on the import_reject record;
      its well-chained twin admits; EXTENT_RATE = 0 is byte-identical to the
      pre-build door for composites (zero refusals -- the dial proves the
      axis); an underivable composite still passes unpriced, stated.
  F4  nesting: a composite-of-composites derives signature and price THROUGH
      the recursion (nested == flat, the order Gamma.apply executes); an
      underivable nest degrades everywhere at once.

Seeded with a FIXED CONSTANT (the build date), never a clock.
"""
from __future__ import annotations

import hashlib
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import applicability as A  # noqa: E402
from engines.egocentric import consumer as C  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import mint as M  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402

SEED = 20260821  # fixed constant (the build date) -- deterministic forever
DC = E.DONT_CARE


# ── constructions ─────────────────────────────────────────────────────────────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


def _box(tmp_path, name):
    """One agent's home fabric + Gamma (the seed_imports call signature)."""
    f = KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")
    return E.Gamma(f), f


def _atom(ctx, out, key, action=6):
    ctx_l = [[int(v) for v in row] for row in ctx]
    out_l = [[int(v) for v in row] for row in out]
    return {"kind": "EFFECT", "arity": 2, "key": key, "action": action,
            "context": ctx_l,
            "transform": {"before": ctx_l, "after": out_l},
            "changed": int((np.asarray(ctx) != np.asarray(out)).sum())}


def _recolour(v0, v1, action=6):
    """A 1-cell recolour EFFECT learned from real frames (ctx [[v0]] -> [[v1]])."""
    b = np.zeros((5, 5), dtype=int)
    b[2, 2] = v0
    a = b.copy()
    a[2, 2] = v1
    return E.learn_effect(b, action, a)


def _cand(fabric, atom, src_seq, game="g1", level=1, source_game="srcA"):
    """One import_candidates record (the fields seed_imports reads)."""
    return fabric.append("collective", C.CAND_TOPIC, {
        "game": str(game), "level": int(level), "src_seq": int(src_seq),
        "atom": dict(atom), "sigma": {}, "source_game": source_game,
        "source_seq": 7})


def _rejects(fabric):
    return [r for r in fabric.query("collective", C.QUEUE_TOPIC)
            if r.get("kind") == C.KIND_IMPORT_REJECT]


# ── the test-side oracles (independent reimplementations, patches in hand) ────

def _retained(atom):
    """start_extent's definition: retained-but-unchanged context cells."""
    ctx = np.asarray(atom["context"])
    out = np.asarray(atom["transform"]["after"])
    return int(((ctx != DC) & (ctx == out)).sum())


def _required(atom):
    """A step's full requirement: every non-DONT_CARE context cell."""
    return int((np.asarray(atom["context"]) != DC).sum())


def _changed(atom):
    ctx = np.asarray(atom["context"])
    return int((ctx != np.asarray(atom["transform"]["after"])).sum())


def _established_oracle(step, priors):
    """Best single-prior full-containment agreement for `step`'s required
    context cells -- reimplemented here from the design statement, never
    from the code under test."""
    ctx = np.asarray(step["context"])
    ch, cw = ctx.shape
    req = ctx != DC
    best = 0
    for prior in priors:
        after = np.asarray(prior["transform"]["after"])
        ah, aw = after.shape
        for r0 in range(ah - ch + 1):
            for c0 in range(aw - cw + 1):
                win = after[r0:r0 + ch, c0:c0 + cw]
                best = max(best, int((req & (win != DC) & (win == ctx)).sum()))
    return best


def _price_oracle(leaves):
    """price = start_extent + Σ unguaranteed_residue + length, from the SAME
    stored patches the code reads -- the F1 amendment-3 arithmetic witness."""
    residue = sum(_required(step) - _established_oracle(step, leaves[:i])
                  for i, step in enumerate(leaves) if i > 0)
    return _retained(leaves[0]) + residue + len(leaves), residue


def _psig_oracle(atom):
    """The expected postcondition signature, reimplemented: after-patch dims,
    written colours at changed cells, changed-mask key (the mint's _signature
    hashing shape in the psig's pure-python encoding), palette-after."""
    ctx = np.asarray(atom["context"])
    out = np.asarray(atom["transform"]["after"])
    h, w = out.shape
    bits, bvals, avals, written = [], [], [], set()
    for r in range(h):
        for c in range(w):
            b_, a_ = int(ctx[r, c]), int(out[r, c])
            if b_ != a_:
                bits.append("1")
                bvals.append(b_)
                avals.append(a_)
                if a_ != DC:
                    written.add(a_)
            else:
                bits.append("0")
    blob = "%d|%d,%d|%s|%s|%s" % (
        int(atom.get("action", 0)), h, w, "".join(bits),
        ",".join(str(v) for v in bvals), ",".join(str(v) for v in avals))
    return {"v": A.PSIG_VERSION, "h": int(h), "w": int(w),
            "written": sorted(written), "changed": len(bvals),
            "ck": hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16],  # noqa: S324 -- content-addressing, not cryptography (the house sha1 rule)
            "pal_after": sorted(int(v) for v in set(out.ravel().tolist())
                                if int(v) != DC)}


# ── R4: exact postcondition signatures, sentinel never leaks ──────────────────

def test_r4_postcondition_signature_exact_on_constructed_atoms():
    rec = _recolour(3, 4)
    assert A.postcondition_signature(rec) == _psig_oracle(rec), (
        "R4 FALSIFIED: the recolour atom's psig diverged from the oracle")
    multi = _atom([[1, 2], [3, 4]], [[5, 6], [7, 4]], "eff-multi")
    got = A.postcondition_signature(multi)
    assert got == _psig_oracle(multi), (
        "R4 FALSIFIED: multi-cell psig diverged\ngot=%r\nexp=%r"
        % (got, _psig_oracle(multi)))
    assert got["written"] == [5, 6, 7] and got["changed"] == 3, (
        "R4 FALSIFIED: written must be the after values AT CHANGED CELLS "
        "only -- the unchanged 4 is not written")
    assert got["pal_after"] == [4, 5, 6, 7], (
        "R4 FALSIFIED: palette-after must be the after-patch palette "
        "(before - consumed, union written)")
    # known-negative: a different action or a different change moves the key
    other_action = A.postcondition_signature(dict(multi, action=1))
    assert other_action["ck"] != got["ck"], "the mask key must hash the action"
    other_change = A.postcondition_signature(
        _atom([[1, 2], [3, 4]], [[5, 6], [7, 9]], "eff-multi2"))
    assert other_change["ck"] != got["ck"], "the mask key must hash the change"


def test_r4_unreadable_degrades_to_no_claim_and_psig_of_backfills():
    for junk in (None, {}, {"kind": "INERT", "changed": 0},
                 {"kind": "EFFECT", "context": "nope",
                  "transform": {"after": "nope"}}):
        sig = A.postcondition_signature(junk)
        assert sig == {"v": A.PSIG_VERSION, "h": 0, "w": 0, "written": [],
                       "changed": 0, "ck": "", "pal_after": []}, (
            "unreadable input must degrade to NO-CLAIM, never raise: %r" % (junk,))
    rec = _recolour(3, 4)
    assert A.psig_of(rec) == A.postcondition_signature(rec), (
        "psig_of must DERIVE for an atom that predates the field (backfill)")
    stale = dict(rec)
    stale[A.PSIG_FIELD] = {"v": 999, "garbage": True}
    assert A.psig_of(stale) == A.postcondition_signature(rec), (
        "a malformed stored psig must be re-derived, never served")
    stamped = dict(rec)
    stamped[A.PSIG_FIELD] = A.postcondition_signature(rec)
    assert A.psig_of(stamped) is stamped[A.PSIG_FIELD], (
        "a valid stored psig is the cache -- served, not re-derived")


def test_r4_minimised_atom_sentinel_never_leaks_into_psig():
    """A DONT_CARE-bearing minimised atom: the sentinel is a match convention,
    never content -- it must appear in NO psig field, and the changed
    count/key must be untouched by minimisation (DC lands in ctx and after
    together, never at a changed cell)."""
    base = np.full((5, 5), 1, dtype=int)
    ctx = base.copy()
    ctx[0, 0] = 4                                     # will vary -> DC
    ctx[0, 4] = 5                                     # constant, retained
    out = ctx.copy()
    out[2, 2] = 9                                     # the changed cell
    atom = _atom(ctx, out, "eff-min")
    before_psig = A.postcondition_signature(atom)
    obs = ctx.copy()
    obs[0, 0] = 8                                     # varies -> dropped
    m = E.minimise_atom(atom, obs)
    assert m is not None and m["context"][0][0] == DC, "construction: must shrink"
    assert A.PSIG_FIELD not in m, (
        "minimise_atom must DROP the stale psig cache exactly as it drops asig")
    sig = A.postcondition_signature(m)
    assert sig == _psig_oracle(m), "R4 FALSIFIED on the minimised atom"
    assert DC not in sig["written"] and DC not in sig["pal_after"], (
        "R4 FALSIFIED: the sentinel leaked into the postcondition signature")
    assert sig["changed"] == before_psig["changed"] == 1, (
        "minimisation must never move the changed count")
    assert sig["ck"] == before_psig["ck"], (
        "the changed-mask key hashes the CHANGE; dropping unchanged debris "
        "cells must not move it")
    assert 4 in before_psig["pal_after"] and 4 not in sig["pal_after"], (
        "the dropped cell's colour must leave palette-after (and only that)")


def test_psig_stamped_beside_asig_at_all_three_mint_write_sites(tmp_path):
    """The mint stamp (consider), the minimisation restamp (_merge_context)
    and the conflict restamp (_reinstate) each leave a stored psig equal to
    the derived one -- the cache never outlives its patches."""
    rng = np.random.default_rng(SEED)
    b1 = rng.integers(1, 8, size=(9, 9)).astype(int)  # colours 1..7 only
    b1[1, 1], b1[5, 5], b1[1, 5] = 2, 3, 8            # change sites + distant X;
    # X's colour (8) is UNIQUE in the patch, so dropping X moves palette-after
    a1 = b1.copy()
    a1[1, 1] = 0
    a1[5, 5] = 0
    g = _gamma(tmp_path, "stamps")
    mint = MDLMint(g)
    r1 = mint.consider(b1, 6, a1, game="g1", level=1)
    assert r1["verdict"] == "mint", "construction: the event must mint"
    served = g.get(r1["id"])
    assert served[A.PSIG_FIELD] == A.postcondition_signature(served), (
        "SITE 1 (consider) FALSIFIED: stored psig != derived")
    # site 2: a same-signature different-debris re-observation shrinks (ctx_min)
    b2 = b1.copy()
    b2[1, 5] = 7                                      # different debris at X
    a2 = b2.copy()
    a2[1, 1] = 0
    a2[5, 5] = 0
    mint.consider(b2, 6, a2, game="g1", level=1)
    rec = g.fabric.query("collective", g.TOPIC,
                         where=lambda r: r.get("id") == r1["id"])[-1]
    assert rec.get("ctx_min") is True, "construction: the merge must fire"
    atom2 = rec["atom"]
    assert atom2["context"][0][4] == DC, "construction: X must be dropped"
    assert atom2[A.PSIG_FIELD] == A.postcondition_signature(atom2), (
        "SITE 2 (_merge_context) FALSIFIED: stale psig survived minimisation")
    assert atom2[A.PSIG_FIELD] != served[A.PSIG_FIELD], (
        "construction: minimisation moved palette-after, the restamp must show it")
    # site 3: a different-outcome frame matching the loosened context reinstates
    b3 = b1.copy()
    b3[1, 5] = 5                                      # a third X value
    a3 = b3.copy()
    a3[1, 1] = 7                                      # a DIFFERENT change
    a3[5, 5] = 7
    assert E.apply_effect(atom2, b3) is not None, (
        "construction: loosened atom must match the conflict frame first")
    mint.consider(b3, 6, a3, game="g1", level=1)
    rec3 = g.fabric.query("collective", g.TOPIC,
                          where=lambda r: r.get("id") == r1["id"])[-1]
    assert rec3.get("ctx_conflict") is True, "construction: the clause must fire"
    atom3 = rec3["atom"]
    assert atom3[A.PSIG_FIELD] == A.postcondition_signature(atom3), (
        "SITE 3 (_reinstate) FALSIFIED: stale psig survived reinstatement")


# ── F1: the chain discount, derived and executable (amendment 3) ──────────────

def _chain_atoms():
    """A writes EXACTLY what B requires (B.context == A.after); Cu is
    unrelated (no colour of its context appears in A's after-patch)."""
    a = _atom([[1, 2], [3, 4]], [[5, 6], [7, 8]], "eff-A")
    b = _atom([[5, 6], [7, 8]], [[9, 9], [9, 9]], "eff-B")
    cu = _atom([[2, 2], [2, 2]], [[9, 9], [9, 9]], "eff-C")
    assert a["transform"]["after"] == b["context"], "construction: well-chained"
    a_after = {v for row in a["transform"]["after"] for v in row}
    assert not ({v for row in cu["context"] for v in row} & a_after), (
        "construction: the unrelated pair must share no establishable colour")
    return a, b, cu


def test_f1_chain_discount_derived_executable(tmp_path):
    g = _gamma(tmp_path, "f1")
    a, b, cu = _chain_atoms()
    ida, idb, idc = (g.add(x, "g1", 1) for x in (a, b, cu))
    chained = g.get(g.compose([ida, idb], "g1", 1))
    unrelated = g.get(g.compose([ida, idc], "g1", 1))
    # the numbers, computed here from the SAME stored patches the code reads
    exp_chained, res_chained = _price_oracle([a, b])
    exp_unrelated, res_unrelated = _price_oracle([a, cu])
    assert res_chained == 0, (
        "F1 FALSIFIED: A writes exactly what B requires -- residue must be 0")
    assert res_unrelated == _required(cu), (
        "F1 FALSIFIED: nothing establishes the unrelated step -- residue "
        "must be its FULL requirement")
    assert exp_chained == _retained(a) + 0 + 2
    assert exp_unrelated == _retained(a) + _required(cu) + 2
    assert chained["csig"]["price"] == exp_chained, (
        "F1 FALSIFIED: chained price %r != derived %r"
        % (chained["csig"]["price"], exp_chained))
    assert unrelated["csig"]["price"] == exp_unrelated, (
        "F1 FALSIFIED: unrelated price %r != derived %r"
        % (unrelated["csig"]["price"], exp_unrelated))
    assert chained["csig"]["price"] < unrelated["csig"]["price"], (
        "F1 FALSIFIED: the chain discount is not real")
    # EXECUTABLE, not just priced: the chained composite actually runs
    frame = np.zeros((4, 4), dtype=int)
    frame[1:3, 1:3] = np.asarray(a["context"])
    out = g.apply(g.compose([ida, idb], "g1", 1), frame)
    assert out is not None and (np.asarray(out)[1:3, 1:3] == 9).all(), (
        "construction: the well-chained composite must execute end to end")


def test_f1_start_extent_is_paid(tmp_path):
    """The first step's retained extent enters the price (the wide-start
    axis F3 refuses on) -- and only the FIRST step's: a wide step buried
    later is priced through its residue instead."""
    g = _gamma(tmp_path, "f1se")
    wide_first = _atom([[1, 1, 1], [1, 2, 1], [1, 1, 1]],
                       [[1, 1, 1], [1, 3, 1], [1, 1, 1]], "eff-wf")
    follow = _atom([[1, 1, 1], [1, 3, 1], [1, 1, 1]],
                   [[1, 1, 1], [1, 4, 1], [1, 1, 1]], "eff-fl")
    idw, idf = g.add(wide_first, "g1", 1), g.add(follow, "g1", 1)
    csig = g.get(g.compose([idw, idf], "g1", 1))["csig"]
    exp, res = _price_oracle([wide_first, follow])
    assert _retained(wide_first) == 8 and res == 0, "construction drifted"
    assert csig["price"] == exp == 8 + 0 + 2, (
        "F1 FALSIFIED: start_extent (8) must be paid exactly once")
    assert csig["start_extent"] == 8 and csig["length"] == 2


# ── F2: composite index visibility ────────────────────────────────────────────

def test_f2_composite_pruned_on_dims_kept_on_match(tmp_path):
    g = _gamma(tmp_path, "f2dims")
    b = np.zeros((3, 7), dtype=int)
    b[1, 1:6] = [1, 2, 3, 4, 5]
    a = b.copy()
    a[1, 1:6] = [5, 4, 3, 2, 1]
    row = E.learn_effect(b, 6, a)                     # 1x5 context requirement
    rid = g.add(row, "g1", 1)
    cid = g.compose([rid], "g1", 1)
    comp = g.get(cid)
    assert comp.get(A.CSIG_FIELD), "construction: the composite must derive"
    small = A.frame_signature([np.zeros((3, 3), dtype=int)])
    kept = A.prune_candidates([cid], {cid: comp}, small, resolver=g.get)
    assert kept == [], (
        "F2 FALSIFIED: a composite whose derived requirement can never fit "
        "the frame was NOT pruned -- composites are still index-invisible")
    fits = A.frame_signature([b])
    kept = A.prune_candidates([cid], {cid: comp}, fits, resolver=g.get)
    assert kept == [cid], (
        "F2 FALSIFIED (known-negative): a composite that CAN apply was pruned")


def test_f2_composite_pruned_on_palette_kept_on_match(tmp_path):
    g = _gamma(tmp_path, "f2pal")
    a34 = g.add(_recolour(3, 4), "g1", 1)
    a45 = g.add(_recolour(4, 5), "g1", 1)
    cid = g.compose([a34, a45], "g1", 1)
    comp = g.get(cid)
    assert comp["csig"]["pre"]["pal"] == [3], (
        "the LATER step's requirement (4) is established by the first step's "
        "write -- only the start colour is demanded of the frame")
    hostile = A.frame_signature([np.full((5, 5), 7)])
    kept = A.prune_candidates([cid], {cid: comp}, hostile, resolver=g.get)
    assert kept == [], (
        "F2 FALSIFIED: no reachable palette covers the derived requirement "
        "and the composite was NOT pruned")
    friendly = A.frame_signature([np.full((5, 5), 3)])
    kept = A.prune_candidates([cid], {cid: comp}, friendly, resolver=g.get)
    assert kept == [cid], (
        "F2 FALSIFIED (known-negative): the applicable composite was pruned")


def test_f2_underivable_composite_degrades_to_no_requirement(tmp_path):
    g = _gamma(tmp_path, "f2und")
    a34 = g.add(_recolour(3, 4), "g1", 1)
    effif = {"kind": "EFFECT_IF", "arity": 3, "key": "effif-x", "action": 6,
             "condition": {"cells": [[1, 1, 9]]}, "then": _recolour(3, 4),
             "else": None, "changed": 1}
    fid = g.add(effif, "g1", 1)
    cid = g.compose([a34, fid], "g1", 1)
    comp = g.get(cid)
    assert A.CSIG_FIELD not in comp, (
        "an EFFECT_IF part's branch is world-selected -- the derivation must "
        "DECLINE, never guess")
    assert A.signature_of(comp) == {"v": A.ASIG_VERSION, "h": 0, "w": 0,
                                    "pal": [], "ck": ""}, (
        "F2 FALSIFIED: an underivable composite must read NO-REQUIREMENT")
    hostile = A.frame_signature([np.full((3, 3), 7)])
    kept = A.prune_candidates([cid], {cid: comp}, hostile, resolver=g.get)
    assert kept == [cid], (
        "F2 FALSIFIED: an underivable composite was pruned -- conservatism "
        "violated (any doubt keeps the candidate)")
    # and a legacy composite (minted before this build: no csig field) too
    legacy = {"kind": "COMPOSITE", "key": "cmp-old", "parts": [a34]}
    kept = A.prune_candidates(["old:0"], {"old:0": legacy}, hostile,
                              resolver=g.get)
    assert kept == ["old:0"], "a pre-build composite must never be pruned"


# ── F3: the admission hole closes ─────────────────────────────────────────────

def _wide_leaf(key="eff-w", seed=SEED):
    """The pi-replay median shape: 30x33 context, 26 scattered changed cells
    (corners pinned so the bbox is the whole patch), retained 964."""
    rng = np.random.default_rng(seed)
    h, w = 30, 33
    ctx = rng.integers(1, 9, size=(h, w)).astype(int)
    cells = [(0, 0), (h - 1, w - 1)]
    while len(cells) < 26:
        r, c = int(rng.integers(0, h)), int(rng.integers(0, w))
        if (r, c) not in cells:
            cells.append((r, c))
    out = ctx.copy()
    for r, c in cells:
        out[r, c] = 0
    atom = _atom(ctx, out, key)
    assert _retained(atom) == 964 and atom["changed"] == 26, "construction drifted"
    return atom


def _f3_composites(tmp_path):
    """(wide_composite, twin_composite, source_gamma): the wide one starts on
    a 964-cell extent and chains into an unestablished step; the twin is a
    tight well-chained pair with the same total changed (52)."""
    gs = _gamma(tmp_path, "src")
    rng = np.random.default_rng(SEED + 1)
    wide = _wide_leaf()
    nines = np.full((2, 13), 9, dtype=int)
    unrel = _atom(nines, np.zeros((2, 13), dtype=int), "eff-u")   # 9s: not in wide's after
    t1c = rng.integers(1, 9, size=(2, 13)).astype(int)
    t1 = _atom(t1c, nines, "eff-t1")
    t2 = _atom(nines, np.full((2, 13), 4, dtype=int), "eff-t2")   # ctx == t1.after
    ids = {a["key"]: gs.add(a, "g1", 1) for a in (wide, unrel, t1, t2)}
    wide_cid = gs.compose([ids["eff-w"], ids["eff-u"]], "g1", 1)
    twin_cid = gs.compose([ids["eff-t1"], ids["eff-t2"]], "g1", 1)
    return gs.get(wide_cid), gs.get(twin_cid), (wide, unrel, t1, t2)


def test_f3_wide_composite_refused_at_derived_price_twin_admits(tmp_path):
    wide_c, twin_c, (wide, unrel, t1, t2) = _f3_composites(tmp_path)
    exp_wide, _ = _price_oracle([wide, unrel])
    exp_twin, res_twin = _price_oracle([t1, t2])
    assert res_twin == 0 and exp_twin == 2, "construction: the twin must chain"
    assert wide_c["csig"]["price"] == exp_wide == 964 + 26 + 2
    changed = wide_c["csig"]["changed"]
    cost = (1.0 + changed) + M.EXTENT_RATE * exp_wide
    bar = M.MDL_MARGIN * (M.RESIDUAL_CELL_COST * changed + M.UNEXPLAINED_PREMIUM)
    assert cost >= bar, "construction: the wide composite must fail the bargain"
    g, f = _box(tmp_path, "door")
    _cand(f, wide_c, 1)
    _cand(f, twin_c, 2)
    assert C.seed_imports(g, f, "g1", 1) == 1, (
        "F3 FALSIFIED: the door did not split the pair -- either the wide "
        "composite passed unpriced (the hole) or the twin was overcharged")
    keys = [r["atom"].get("key") for r in g.fabric.query("collective", C.ATOMS_TOPIC)]
    assert twin_c["key"] in keys and wide_c["key"] not in keys, (
        "F3 FALSIFIED (both directions): twin in, wide out -- not the reverse")
    (rej,) = _rejects(f)
    assert rej["key"] == wide_c["key"]
    assert rej["retained"] == exp_wide, (
        "F3 FALSIFIED: the refusal must record the DERIVED PRICE (it "
        "recorded %r, derived %r)" % (rej["retained"], exp_wide))
    assert rej["cost"] == cost and rej["bar"] == bar and rej["changed"] == changed, (
        "the recorded numbers must be the inequality's own terms")


def test_f3_rate_zero_is_byte_identical_to_the_pre_build_door(tmp_path,
                                                              monkeypatch):
    """THE DIAL: at EXTENT_RATE = 0 every derivable composite admits and zero
    refusal records exist -- exactly the pre-build door, where composites
    passed unpriced. The axis, not the constant, is what the build adds."""
    monkeypatch.setattr(M, "EXTENT_RATE", 0.0)
    wide_c, twin_c, _leaves = _f3_composites(tmp_path)
    price = C.admission_price(wide_c)
    assert price is not None and price["admit"], (
        "F3 FALSIFIED: at rate 0 the wide composite must admit -- the "
        "refusal is the PRICED extent axis, nothing else")
    g, f = _box(tmp_path, "door0")
    _cand(f, wide_c, 1)
    _cand(f, twin_c, 2)
    assert C.seed_imports(g, f, "g1", 1) == 2, "rate 0 must admit both"
    assert _rejects(f) == [], (
        "rate 0 must leave ZERO refusal records -- byte-identical streams")


def test_f3_underivable_composite_still_passes_unpriced_stated(tmp_path):
    """The hole persists EXACTLY where nothing derivable exists to price --
    stated, not silent: csig-less composites return None and pass the door
    as they always did (the conservative degrade, F2's twin at admission)."""
    legacy = {"kind": "COMPOSITE", "key": "cmp-legacy", "parts": ["x:0"]}
    assert C.admission_price(legacy) is None
    g, f = _box(tmp_path, "legacy")
    _cand(f, legacy, 1)
    assert C.seed_imports(g, f, "g1", 1) == 1 and _rejects(f) == [], (
        "an unpriceable composite must pass the door exactly as before")


# ── F4: nesting -- the ungated nesting gains its gate ─────────────────────────

def test_f4_nested_composite_derives_through_the_recursion(tmp_path):
    g = _gamma(tmp_path, "f4")
    a, b, cu = _chain_atoms()
    ida, idb, idc = (g.add(x, "g1", 1) for x in (a, b, cu))
    inner = g.compose([ida, idb], "g1", 1)
    nested = g.get(g.compose([inner, idc], "g1", 1))
    flat = g.get(g.compose([ida, idb, idc], "g1", 1))
    assert nested.get(A.CSIG_FIELD), (
        "F4 FALSIFIED: a composite-of-composites derived NO signature -- "
        "nesting is still ungated")
    assert nested["csig"] == flat["csig"], (
        "F4 FALSIFIED: the nested derivation must equal the flat one -- the "
        "recursion IS Gamma.apply's execution order\nnested=%r\nflat=%r"
        % (nested["csig"], flat["csig"]))
    assert nested["csig"]["length"] == 3, "one price unit per LEAF step"
    exp, _res = _price_oracle([a, b, cu])
    assert nested["csig"]["price"] == exp, (
        "F4 FALSIFIED: the nested price diverged from the patch-derived one")
    assert C.admission_price(nested) is not None, (
        "F4 FALSIFIED: the nested composite must be PRICEABLE at the door")
    # known-negative: an underivable inner poisons the whole nest -- no
    # signature, no price, never pruned (degrade everywhere at once)
    effif = {"kind": "EFFECT_IF", "arity": 3, "key": "effif-n", "action": 6,
             "condition": {"cells": [[0, 0, 1]]}, "then": _recolour(1, 2),
             "else": None, "changed": 1}
    fid = g.add(effif, "g1", 1)
    bad_inner = g.compose([ida, fid], "g1", 1)
    bad = g.get(g.compose([bad_inner, idc], "g1", 1))
    assert A.CSIG_FIELD not in bad and C.admission_price(bad) is None
    hostile = A.frame_signature([np.full((3, 3), 7)])
    assert A.prune_candidates(["bad:0"], {"bad:0": bad}, hostile,
                              resolver=g.get) == ["bad:0"], (
        "an underivable nest must degrade to NO-REQUIREMENT, never be pruned")
