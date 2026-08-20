"""CONTEXT MINIMISATION MUST ONLY EVER DROP WHAT THE EVIDENCE ALREADY DISPROVED.
PREREG_W2_STAGE2_CONTEXT_MIN.md -- W2 STAGE 2 (the pi-replay null's repair:
PI_REPLAY_RESULT.md measured a median context of 976 cells licensing a 26-cell
change -- a dense snapshot of a sparse rule that can match nothing but its own
source frame -- with the MDL inequality extent-blind and the half-board clause
a binary cap atoms crowd against).

The build under test: (1) intersection at re-observation of a known key
(mint._intersect_context -> effects.minimise_atom): cells that varied become
effects.DONT_CARE, changed cells + one 8-ring are ALWAYS retained, the stored
context only ever shrinks, `context_full` preserves the original (the undo);
(2) the EXTENT PREMIUM: cost = 1.0 + changed + mint.EXTENT_RATE *
retained_unchanged_cells, the half-board clause staying as the outer wall;
(3) the retro pass tools/context_minimiser.py (a tool, never auto-run;
read-only on its source stream).

The falsifiers, as gated here:
  F1 (ABSOLUTE)  every minimised constructed atom still matches and correctly
                 predicts EVERY one of its own recorded observations; one
                 failure = that minimisation reverted (the retro pass enforces
                 the revert itself, loudly).
  F2             known-negative BOTH ways: a rule with a distant CONSTANT cell
                 RETAINS it (and stops matching when it is violated); a rule
                 observed with a VARYING distant cell DROPS it and still
                 predicts on all observations.
  F3 (THE DIAL)  EXTENT_RATE = 0 -> byte-identical mint decisions to the
                 pre-premium code on a constructed corpus (oracle reimplemented
                 here from the frozen inequality); at the shipped value the
                 wide historical-median-shaped candidate (976-cell context,
                 26 changed) REJECTS while its tight twin MINTS -- and the
                 oracle proves the old rule would have minted both.
  R4             constructed multi-observation sets reproduce the expected
                 intersections EXACTLY, always-retained ring included.
  DC-EQUIV       the vectorised and scalar match paths agree byte-for-byte on
                 don't-care-bearing atoms (the scalar oracle defines the
                 semantics; corpus extension also in test_vectorised_scan.py).

Seeded with a FIXED CONSTANT (the prereg date), never a clock.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import applicability as A  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import mint as M  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402
from tools import context_minimiser as CM  # noqa: E402

SEED = 20260820  # fixed constant (the prereg date) -- deterministic forever
DC = E.DONT_CARE


# ── constructions ─────────────────────────────────────────────────────────────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


def _rule_observations(n_obs, vary_cells, constant_cells=(), size=7,
                       changed=((3, 3),), base=1, seed=SEED):
    """n_obs (ctx, out) observation pairs of ONE rule on a size x size patch:
    `changed` cells flip base -> 9; `vary_cells` take a different value in every
    observation; `constant_cells` hold one fixed value throughout; everything
    else is the base colour."""
    rng = np.random.default_rng(seed)
    obs = []
    for i in range(n_obs):
        ctx = np.full((size, size), base, dtype=int)
        for r, c in constant_cells:
            ctx[r, c] = 5
        for j, (r, c) in enumerate(vary_cells):
            ctx[r, c] = (2 + ((i + j + int(rng.integers(0, 2))) % 3))  # varies
        # force actual variation on every vary cell across the first two obs
        if i == 1:
            for r, c in vary_cells:
                ctx[r, c] = 8
        out = ctx.copy()
        for r, c in changed:
            out[r, c] = 9
        obs.append((ctx, out))
    return obs


def _fold(obs):
    """The retro pass's fold: first observation's atom, intersected with the rest."""
    ctx0, out0 = obs[0]
    atom = {"kind": "EFFECT", "arity": 2, "key": "eff-fold", "action": 6,
            "context": [[int(v) for v in row] for row in ctx0],
            "transform": {"before": [[int(v) for v in row] for row in ctx0],
                          "after": [[int(v) for v in row] for row in out0]},
            "changed": int((ctx0 != out0).sum())}
    for ctx, _out in obs[1:]:
        m = E.minimise_atom(atom, ctx)
        if m is not None:
            atom = m
    return atom


def _ring(cells, size):
    """The changed cells + one 8-neighbourhood ring, clipped -- the never-
    negotiable region, computed independently of the implementation."""
    keep = set()
    for r, c in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < size and 0 <= cc < size:
                    keep.add((rr, cc))
    return keep


# ── F1: ABSOLUTE -- every minimised atom predicts every recorded observation ──

def test_f1_minimised_atoms_predict_every_recorded_observation():
    rng = np.random.default_rng(SEED)
    checked = 0
    for case in range(20):
        size = int(rng.integers(5, 10))
        changed = ((int(rng.integers(2, size - 2)), int(rng.integers(2, size - 2))),)
        ring = _ring(changed, size)
        candidates = [(r, c) for r in range(size) for c in range(size)
                      if (r, c) not in ring]
        rng.shuffle(candidates)
        vary = tuple(candidates[:int(rng.integers(1, 4))])
        const = tuple(candidates[4:5])
        obs = _rule_observations(int(rng.integers(2, 5)), vary, const,
                                 size=size, changed=changed, seed=SEED + case)
        atom = _fold(obs)
        for k, (ctx, out) in enumerate(obs):
            res = E.apply_effect(atom, ctx)
            assert res is not None, (
                "F1 FALSIFIED (case %d, obs %d): minimised atom no longer "
                "matches its own recorded observation" % (case, k))
            assert np.array_equal(res, out), (
                "F1 FALSIFIED (case %d, obs %d): minimised atom mispredicts "
                "its own recorded observation" % (case, k))
            checked += 1
    assert checked >= 40, "construction collapsed -- not a sweep (%d)" % checked


def test_f1_the_retro_pass_reverts_a_failing_minimisation_loudly():
    """A ring cell that VARIES across observations is retained with the stored
    value, so the minimised atom cannot match the divergent observation --
    exactly F1's 'one failure': the pass must emit the atom UNMINIMISED,
    marked reverted, never silently. (0,6) varies too, so the intersection
    DOES shrink -- and the shrunken atom still cannot satisfy F1."""
    size = 7
    obs = _rule_observations(2, vary_cells=((3, 4), (0, 6)), size=size,
                             changed=((3, 3),))     # (3,4) is IN the ring
    recs = []
    for i, (ctx, out) in enumerate(obs):
        recs.append({"id": "eff-ring:%d" % i, "type": "structural",
                     "game": "g1", "level": 1,
                     "atom": {"kind": "EFFECT", "arity": 2, "key": "eff-ring",
                              "action": 6,
                              "context": ctx.tolist(),
                              "transform": {"before": ctx.tolist(),
                                            "after": out.tolist()},
                              "changed": 1}})
    out_records, stats = CM.minimise_stream(recs)
    assert stats["reverted"] == 1 and stats["minimised"] == 0
    (rec,) = out_records
    assert rec.get("reverted") is True
    assert rec["atom"]["context"] == recs[-1]["atom"]["context"], (
        "F1 FALSIFIED: a reverted key must keep its stored context verbatim")


# ── F2: known-negative BOTH ways ──────────────────────────────────────────────

def test_f2_distant_constant_retained_and_varying_dropped():
    size = 9
    changed = ((4, 4),)
    obs = _rule_observations(3, vary_cells=((0, 8),), constant_cells=((8, 0),),
                             size=size, changed=changed)
    atom = _fold(obs)
    ctx = np.asarray(atom["context"])
    assert ctx[8, 0] == 5, (
        "F2 FALSIFIED: the distant CONSTANT cell was dropped -- the "
        "intersection must keep constants")
    assert ctx[4, 4] != DC and atom["context_full"], "changed cell must survive"
    assert ctx[0, 8] == DC, (
        "F2 FALSIFIED: the distant VARYING cell was retained -- it "
        "demonstrably cannot be a precondition")
    # dropped-and-still-predicts, on every observation (F1's property, F2's rule)
    for k, (octx, oout) in enumerate(obs):
        res = E.apply_effect(atom, octx)
        assert res is not None and np.array_equal(res, oout), (
            "F2 FALSIFIED: after dropping the varying cell the rule no "
            "longer predicts observation %d" % k)
    # the retained constant is a REAL precondition: violate it and the atom
    # must refuse to fire on an otherwise-perfect frame
    bad = obs[0][0].copy()
    bad[8, 0] = 7
    assert E.apply_effect(atom, bad) is None, (
        "F2 FALSIFIED: the atom fired with its retained constant violated")
    # and a NOVEL value at the dropped cell is accepted AND left in place
    novel = obs[0][0].copy()
    novel[0, 8] = 6                                   # never observed there
    res = E.apply_effect(atom, novel)
    assert res is not None and res[0, 8] == 6, (
        "the masked stamp must leave the frame's own value at DONT_CARE cells")


# ── F3: THE DIAL ──────────────────────────────────────────────────────────────

def _oracle_verdict(before, action, after):
    """Today's (pre-premium) mint decision, frozen: the exact inequality of
    mint.py before EXTENT_RATE existed, for a FIRST event on a FRESH store
    (novelty and surprise vacuous by construction)."""
    b = np.asarray(before)
    a = np.asarray(after)
    if b.shape != a.shape or b.ndim != 2 or b.size == 0:
        return "quarantine"
    changed = int((b != a).sum())
    if changed == 0:
        return "reject"
    phi = E.learn_effect(b, action, a)
    if phi is None or phi.get("kind") != "EFFECT":
        return "reject"
    cost = 1.0 + changed
    R = M.RESIDUAL_CELL_COST * float(changed) + M.UNEXPLAINED_PREMIUM
    ctx = phi.get("context") or [[]]
    bbox = len(ctx) * (len(ctx[0]) if ctx else 0)
    ok = (cost < R and cost < M.MDL_MARGIN * R
          and bbox < M.MAX_BBOX_BOARD_FRACTION * b.size)
    return "mint" if ok else "reject"


def _f3_corpus():
    """Deterministic first-events spanning mint / MDL-reject / bbox-reject /
    no-change / wide-sparse (the premium's target shape)."""
    rng = np.random.default_rng(SEED + 3)
    corpus = []
    for i in range(24):
        h, w = int(rng.integers(5, 30)), int(rng.integers(5, 30))
        before = rng.integers(0, 6, size=(h, w)).astype(int)
        after = before.copy()
        mode = i % 4
        if mode == 0:                                     # 1-cell recolour: mints
            after[h // 2, w // 2] = (after[h // 2, w // 2] + 1) % 10
        elif mode == 1:                                   # big scramble: bbox wall
            after[:, :] = (after + 1) % 10
        elif mode == 2:                                   # no change: reject
            pass
        else:                                             # sparse wide: the target
            r0, c0 = 1, 1
            r1, c1 = h - 2, w - 2
            after[r0, c0] = (after[r0, c0] + 1) % 10
            after[r1, c1] = (after[r1, c1] + 1) % 10
        corpus.append((before, 6, after))
    return corpus


def _consider_fresh(tmp_path, name, before, action, after):
    g = _gamma(tmp_path, name)
    return MDLMint(g).consider(before, action, after, game="g1", level=1)["verdict"]


def test_f3_rate_zero_is_byte_identical_to_the_pre_premium_decision(tmp_path,
                                                                    monkeypatch):
    monkeypatch.setattr(M, "EXTENT_RATE", 0.0)
    got, expected = [], []
    for i, (b, act, a) in enumerate(_f3_corpus()):
        got.append(_consider_fresh(tmp_path, "z%d" % i, b, act, a))
        expected.append(_oracle_verdict(b, act, a))
    assert got == expected, (
        "F3 FALSIFIED: EXTENT_RATE=0 diverged from the pre-premium decision\n"
        "got=%r\nexp=%r" % (got, expected))
    assert "mint" in expected and "reject" in expected, "corpus spans nothing"


def _median_shaped_event():
    """The historical median atom's shape (PI_REPLAY_RESULT.md): a ~976-cell
    context licensing a 26-cell change, INSIDE the half-board wall."""
    board = np.zeros((46, 46), dtype=int)                 # area 2116; wall at 1058
    after = board.copy()
    cells = [(5, 5), (34, 37)]                            # pin bbox to 30 x 33 = 990
    rng = np.random.default_rng(SEED + 9)
    while len(cells) < 26:
        r, c = int(rng.integers(5, 35)), int(rng.integers(5, 38))
        if (r, c) not in cells:
            cells.append((r, c))
    for r, c in cells:
        after[r, c] = 3
    return board, 6, after


def _tight_twin_event():
    """The same 26-cell change, compact: bbox == changed, zero retained extent."""
    board = np.zeros((46, 46), dtype=int)
    after = board.copy()
    after[20:22, 5:18] = 3                                # 2 x 13 = 26 changed
    return board, 6, after


def test_f3_shipped_rate_rejects_the_wide_median_and_mints_the_tight_twin(tmp_path):
    assert M.EXTENT_RATE > 0.0, "the dial ships OFF -- the premium is not on"
    wide = _median_shaped_event()
    tight = _tight_twin_event()
    # the old rule would have minted BOTH -- so the premium, not the wall, decides
    assert _oracle_verdict(*wide) == "mint"
    assert _oracle_verdict(*tight) == "mint"
    assert _consider_fresh(tmp_path, "wide", *wide) == "reject", (
        "F3 FALSIFIED: the historical-median-shaped candidate still mints")
    assert _consider_fresh(tmp_path, "tight", *tight) == "mint", (
        "F3 FALSIFIED: the tight twin no longer mints -- the premium overshot")


def test_f3_the_rate_sits_inside_the_derived_window():
    """The constant's own docstring arithmetic, executable: reject the median
    shape (retained 950), keep a fully scattered tight atom (retained <= 208)."""
    changed = 26
    base = 1.0 + changed
    bar = M.MDL_MARGIN * (M.RESIDUAL_CELL_COST * changed + M.UNEXPLAINED_PREMIUM)
    assert base + M.EXTENT_RATE * (976 - changed) >= bar, (
        "the median-shaped atom would still mint at EXTENT_RATE=%r"
        % M.EXTENT_RATE)
    assert base + M.EXTENT_RATE * (8 * changed) < bar, (
        "a changed+ring tight atom would be rejected at EXTENT_RATE=%r"
        % M.EXTENT_RATE)


# ── R4: constructed intersections reproduce EXACTLY, ring included ────────────

def test_r4_exact_intersection_with_always_retained_ring():
    base = np.full((5, 5), 1, dtype=int)
    ctx1 = base.copy()
    ctx1[0, 0] = 4                                        # will vary -> DC
    ctx1[0, 4] = 5                                        # constant -> retained
    ctx1[3, 3] = 7                                        # ring cell, varies -> RETAINED
    out1 = ctx1.copy()
    out1[2, 2] = 9                                        # the changed cell
    atom = {"kind": "EFFECT", "arity": 2, "key": "eff-r4", "action": 6,
            "context": ctx1.tolist(),
            "transform": {"before": ctx1.tolist(), "after": out1.tolist()},
            "changed": 1}
    ctx2 = ctx1.copy()
    ctx2[0, 0] = 8                                        # varies
    ctx2[3, 3] = 2                                        # varies INSIDE the ring
    m = E.minimise_atom(atom, ctx2)
    assert m is not None
    expected = ctx1.copy()
    expected[0, 0] = DC                                   # varied, outside ring
    assert m["context"] == expected.tolist(), (
        "R4 FALSIFIED: intersection mismatch\ngot=%r\nexpected=%r"
        % (m["context"], expected.tolist()))
    exp_out = out1.copy()
    exp_out[0, 0] = DC
    assert m["transform"]["after"] == exp_out.tolist()
    assert m["transform"]["before"] == m["context"]
    assert m["context_full"] == ctx1.tolist(), "the undo must hold the original"
    # ring membership, checked against an independent ring computation
    for (r, c) in _ring(((2, 2),), 5):
        assert m["context"][r][c] != DC, (
            "R4 FALSIFIED: ring cell (%d,%d) was dropped" % (r, c))


def test_r4_monotone_shrink_and_first_touch_undo():
    obs = _rule_observations(2, vary_cells=((0, 6),), size=7, changed=((3, 3),))
    atom = _fold(obs)
    assert np.asarray(atom["context"])[0, 6] == DC
    full = atom["context_full"]
    # a THIRD observation varying a second distant cell shrinks further
    ctx3 = obs[0][0].copy()
    ctx3[6, 0] = 6
    m2 = E.minimise_atom(atom, ctx3)
    assert m2 is not None
    c2 = np.asarray(m2["context"])
    assert c2[0, 6] == DC and c2[6, 0] == DC, "shrink must be monotone"
    assert m2["context_full"] == full, (
        "context_full must be preserved from the FIRST touch, not overwritten")
    # and an observation matching the stored context exactly shrinks nothing
    assert E.minimise_atom(m2, np.asarray(m2["context"])) is None


# ── DON'T-CARE EQUIVALENCE: vectorised == scalar on sentinel-bearing atoms ────

def test_dontcare_vectorised_and_scalar_paths_agree_byte_identically():
    rng = np.random.default_rng(SEED + 5)
    obs = _rule_observations(3, vary_cells=((0, 6), (6, 6)),
                             constant_cells=((6, 0),), size=7, changed=((3, 3),))
    atom = _fold(obs)
    assert (np.asarray(atom["context"]) == DC).any(), "construction: no sentinel"
    frames = [octx for octx, _ in obs]
    for _i in range(12):
        fh, fw = int(rng.integers(7, 24)), int(rng.integers(7, 24))
        frames.append(rng.integers(0, 10, size=(fh, fw)).astype(int))
        g = frames[-1].copy()
        er = int(rng.integers(0, fh - 6))
        ec = int(rng.integers(0, fw - 6))
        actx = np.asarray(atom["context"])
        keepm = actx != DC
        g[er:er + 7, ec:ec + 7][keepm] = actx[keepm]
        frames.append(g)                                  # placed match, wild cells random
    prev = E._ANCHOR_SCAN_VECTORISED
    try:
        for k, f in enumerate(frames):
            E._ANCHOR_SCAN_VECTORISED = True
            vec = E.apply_effect(atom, f)
            E._ANCHOR_SCAN_VECTORISED = False
            sca = E.apply_effect(atom, f)
            if vec is None or sca is None:
                assert vec is None and sca is None, (
                    "DC-EQUIV FALSIFIED (frame %d): one path matched, the "
                    "other did not" % k)
            else:
                assert (vec.dtype == sca.dtype and vec.shape == sca.shape
                        and vec.tobytes() == sca.tobytes()), (
                    "DC-EQUIV FALSIFIED (frame %d): bytes diverged" % k)
                assert not (vec == DC).any(), (
                    "the sentinel leaked into a frame -- DONT_CARE is a match "
                    "convention, never content")
    finally:
        E._ANCHOR_SCAN_VECTORISED = prev


# ── the mint-side wire: intersection at re-observation ────────────────────────

def _distant_event():
    """An event whose atom has a 5x5 bbox with a distant unchanged cell (patch
    (0,4)) outside both changed cells' rings, on a fixed-seed textured board
    (unique anchor by construction) -- and SMALL enough extent that the shipped
    premium still mints it (retained 23 < 30-cell rejection onset at changed=2)."""
    rng = np.random.default_rng(SEED + 7)
    before = rng.integers(1, 9, size=(9, 9)).astype(int)
    after = before.copy()
    after[1, 1] = 0                                       # changed (bbox 0,0)
    after[5, 5] = 0                                       # changed (bbox 4,4)
    return before, 6, after


def test_mint_reobservation_intersects_supersedes_and_keeps_the_verdict(tmp_path):
    b, act, a = _distant_event()
    phi = E.learn_effect(b, act, a)
    doctored = dict(phi)
    ctx = [row[:] for row in phi["context"]]
    out_patch = [row[:] for row in phi["transform"]["after"]]
    ctx[0][4] = 0                                         # stored context differs
    out_patch[0][4] = 0                                   # at the distant cell
    doctored["context"] = ctx
    doctored["transform"] = {"before": ctx, "after": out_patch}
    g = _gamma(tmp_path, "reobs")
    aid = g.add(doctored, "g1", 1)
    mint = MDLMint(g)
    n0 = len(g.fabric.query("collective", g.TOPIC))
    verdict = mint.consider(b, act, a, game="g1", level=1)
    assert verdict["verdict"] == "rederivation", "the verdict itself must not change"
    recs = g.fabric.query("collective", g.TOPIC)
    assert len(recs) == n0 + 1, "re-observation must SUPERSEDE, append-only"
    sup = recs[-1]
    assert sup["id"] == aid and sup.get("ctx_min") is True
    atom = sup["atom"]
    assert atom["context"][0][4] == DC, (
        "the varying distant cell must be DONT_CARE after the intersection")
    assert atom["context_full"] == ctx, "the undo must hold the stored original"
    assert atom["key"] == phi["key"], "the key never changes under minimisation"
    # Gamma.get reads last-wins: the store now serves the minimised atom,
    # and it still fires on the live frame (F1 through the mint path)
    served = g.get(aid)
    assert served["context"][0][4] == DC
    res = E.apply_effect(served, b)
    assert res is not None and np.array_equal(res, a)
    # the restamped signature carries no sentinel in its palette
    sig = A.signature_of(served)
    assert DC not in sig["pal"], "DONT_CARE leaked into the anchor signature"
    assert A.anchor_signature(served) == atom[A.ASIG_FIELD], (
        "the stamped cache must equal the derived signature -- never stale")


def test_mint_reobservation_of_identical_context_is_a_structural_noop(tmp_path):
    """Stated, not papered over: the key hashes the full context, so a genuine
    same-key re-observation carries an identical context and shrinks nothing --
    no superseding record, verdict unchanged."""
    g = _gamma(tmp_path, "noop")
    mint = MDLMint(g)
    b, act, a = _distant_event()
    assert mint.consider(b, act, a, game="g1", level=1)["verdict"] == "mint"
    n0 = len(g.fabric.query("collective", g.TOPIC))
    out = mint.consider(b, act, a, game="g1", level=1)
    assert out["verdict"] == "rederivation"
    assert len(g.fabric.query("collective", g.TOPIC)) == n0, (
        "an identical re-observation must not append a superseding record")


def test_minimised_atom_survives_the_applicability_prefilter(tmp_path):
    """The index interplay: a minimised atom that CAN apply is never pruned
    (F2 of the W2a stage-1 gate, extended to sentinel-bearing atoms)."""
    obs = _rule_observations(2, vary_cells=((0, 6),), size=7, changed=((3, 3),))
    atom = _fold(obs)
    frame = obs[1][0]
    assert E.apply_effect(atom, frame) is not None, "construction: must apply"
    fsig = A.frame_signature([frame])
    kept = A.prune_candidates(["m:0"], {"m:0": atom}, fsig)
    assert kept == ["m:0"], (
        "a minimised atom apply_effect can fire was pruned -- the sentinel "
        "must never become a palette requirement")


# ── the retro pass: the tool itself ───────────────────────────────────────────

def _stream_record(i, atom, game="g1"):
    return {"id": "%s:%d" % (atom["key"], i), "type": "structural",
            "game": game, "level": 1, "atom": atom,
            "origin": "local", "mint_seq": i}


def _tool_stream(tmp_path):
    """A constructed atoms stream: one singleton, one identical-contexts pair
    (today's real shape), one differing-contexts pair (the evidence the
    mechanism needs)."""
    b0 = np.zeros((5, 5), dtype=int)
    a0 = b0.copy()
    a0[2, 2] = 3
    single = E.learn_effect(b0, 6, a0)
    obs = _rule_observations(2, vary_cells=((0, 6),), size=7, changed=((3, 3),))
    diff_recs = []
    for k, (ctx, out) in enumerate(obs):
        diff_recs.append(_stream_record(10 + k, {
            "kind": "EFFECT", "arity": 2, "key": "eff-vary", "action": 6,
            "context": ctx.tolist(),
            "transform": {"before": ctx.tolist(), "after": out.tolist()},
            "changed": 1}))
    ident = _stream_record(20, dict(diff_recs[0]["atom"], key="eff-echo"))
    records = ([_stream_record(0, single)] + diff_recs
               + [ident, dict(ident, origin="imported", mint_seq=21)])
    src = tmp_path / "atoms.jsonl"
    with open(src, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return src, records, obs


def test_retro_pass_singleton_multi_and_source_untouched(tmp_path):
    src, _records, obs = _tool_stream(tmp_path)
    dst = tmp_path / "atoms.min.jsonl"
    before_bytes = src.read_bytes()
    rc = CM.main([str(src), str(dst)])
    assert rc == 0
    assert src.read_bytes() == before_bytes, (
        "the retro pass MODIFIED its source stream -- forbidden")
    out = [json.loads(ln) for ln in dst.read_text(encoding="utf-8").splitlines()]
    by_key = {r["atom"]["key"]: r for r in out}
    assert len(out) == 3, "one output record per key"
    singleton = next(r for r in out if r.get("singleton"))
    assert singleton["observations"] == 1
    assert singleton["atom"]["context"] == [[0]], "singleton emitted unchanged"
    echo = by_key["eff-echo"]                             # identical contexts
    assert echo["singleton"] is False and "ctx_min" not in echo, (
        "identical-context observations must NOT invent a minimisation")
    vary = by_key["eff-vary"]
    assert vary["ctx_min"] is True and vary["observations"] == 2
    assert vary["atom"]["context"][0][6] == DC
    assert vary["atom"]["context_full"] == obs[0][0].tolist()
    for octx, oout in obs:                                # F1 inside the pass held
        res = E.apply_effect(vary["atom"], octx)
        assert res is not None and np.array_equal(res, oout)


def test_retro_pass_refuses_to_write_onto_its_source(tmp_path):
    src, _records, _obs = _tool_stream(tmp_path)
    assert CM.main([str(src), str(src)]) == 2, (
        "the pass must refuse in-place operation -- the source is the holder "
        "of record")
