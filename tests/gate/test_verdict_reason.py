"""EVERY VERDICT NAMES ITS DECIDING CLAUSE -- THE VERDICT REASON FIELD (W4).

The live customer: are movement transitions (whole-view changes in egocentric
frames) being rejected by the half-board bbox clause specifically? Before this
build a REJECT said nothing about WHICH clause killed it; the verdict stream
could not answer. Now every record mint.consider() ledgers carries "reason"
from the FIXED vocabulary mint.REASONS, rejects/quarantines carry "failed"
(every independently failing clause, reason = first in the code's own
evaluation order, mint.MDL_CLAUSE_ORDER), and MDL-decided records carry the
audit numerics under "mdl" -- all additive, old readers untouched.

The falsifiers, as gated here:
  R4  constructed candidates hitting EACH terminal produce EXACTLY the
      expected reason -- one test per value in the vocabulary, including a
      wide-context candidate whose reason is "bbox_half_board" (the
      movement-transition shape: the whole view changes, bbox == board) and
      one whose reason is "extent_premium" -- proven to PASS at EXTENT_RATE=0
      (the same event MINTS on a fresh store with the dial at 0) and fail at
      the shipped rate.
  F1  the "failed" list is COMPLETE on a candidate failing multiple clauses,
      and "reason" is the FIRST of them in evaluation order.
  F2  no terminal escapes: constructed inputs cover every return path in
      consider(); every emitted record carries a reason from the closed
      vocabulary, and the sweep observes the WHOLE vocabulary.
  F3  the numerics on the record equal independently recomputed values
      (cost, R, bbox_area, board_area, retained, changed, w) -- and the FLAT
      "w" field keeps its exact prior emission sites (lp_drive._w_bar means
      flat "w" over rows carrying one; an MDL reject's w lives inside "mdl").

Seeded with a FIXED CONSTANT (the prereg date), never a clock.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import mint as M  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402

SEED = 20260820  # fixed constant (the prereg date) -- deterministic forever


# ── constructions ─────────────────────────────────────────────────────────────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


def _consider_fresh(tmp_path, name, before, action, after):
    """One consider() on a fresh store; returns (result, last verdict record)."""
    g = _gamma(tmp_path, name)
    out = MDLMint(g).consider(before, action, after, game="g1", level=1)
    recs = g.fabric.query("collective", "mint_verdicts")
    assert recs, "nothing silent -- every consider() ledgers a record"
    return out, recs[-1]


def _one_cell_event():
    """1-cell recolour on 5x5: the docstring's own mint example."""
    before = np.zeros((5, 5), dtype=int)
    before[2, 2] = 3
    after = before.copy()
    after[2, 2] = 4
    return before, 6, after


def _distant_pair():
    """Two events with the SAME coarse signature (identical changed cells)
    but DIFFERENT full keys (a debris cell inside the bbox differs): the
    second is novel by key yet seen by signature -- the support terminal."""
    rng = np.random.default_rng(SEED)
    b1 = rng.integers(1, 9, size=(9, 9)).astype(int)
    a1 = b1.copy()
    a1[1, 1] = 0
    a1[5, 5] = 0
    b2 = b1.copy()
    b2[3, 3] = 0                                      # debris differs, patch (2,2)
    a2 = b2.copy()
    a2[1, 1] = 0
    a2[5, 5] = 0
    return (b1, 6, a1), (b2, 6, a2)


def _scramble_event():
    """The whole view changes -- the movement-transition shape. Every cell
    flips, so bbox == board: the cost clauses PASS (retained 0) and ONLY the
    half-board wall fails."""
    rng = np.random.default_rng(SEED + 1)
    before = rng.integers(0, 6, size=(6, 6)).astype(int)
    after = (before + 1) % 10
    return before, 6, after


def _scatter(board_shape, pins, n, r_range, c_range, seed):
    """`n` changed cells (0 -> 3) on a zeros board: `pins` fix the bbox, the
    rest land strictly inside it (fixed seed)."""
    board = np.zeros(board_shape, dtype=int)
    after = board.copy()
    cells = list(pins)
    rng = np.random.default_rng(seed)
    while len(cells) < n:
        r = int(rng.integers(*r_range))
        c = int(rng.integers(*c_range))
        if (r, c) not in cells:
            cells.append((r, c))
    for r, c in cells:
        after[r, c] = 3
    return board, 6, after


def _extent_premium_event():
    """The historical median shape (PI_REPLAY_RESULT.md): bbox 30x33 = 990 on
    a 46x46 board (wall at 1058 -- INSIDE it), 26 changed, retained 964.
    Rate 0: cost 27 clears R=53 and the 47.7 margin bar clean. Shipped rate:
    27 + 0.05*964 = 75.2 -- the premium alone kills it."""
    return _scatter((46, 46), [(5, 5), (34, 37)], 26, (6, 34), (6, 37), SEED + 9)


def _mdl_cost_event():
    """changed 26, bbox 20x28 = 560 on 20x50 (board 1000, wall 500), retained
    534: cost 27 + 26.7 = 53.7 >= R = 53 -- ALL THREE clauses fail, and bbox
    fails at rate 0 too, so the reason is the FIRST in evaluation order."""
    return _scatter((20, 50), [(0, 0), (19, 27)], 26, (1, 19), (1, 27), SEED + 2)


def _mdl_margin_event():
    """changed 26, bbox 19x24 = 456 on 20x40 (board 800, wall 400), retained
    430: cost 27 + 21.5 = 48.5 -- under R = 53 (mdl_cost passes) but over the
    47.7 margin bar; bbox fails too, at rate 0 as well, so the reason is
    mdl_margin (first failing clause), never extent_premium."""
    return _scatter((20, 40), [(0, 0), (18, 23)], 26, (1, 18), (1, 23), SEED + 3)


class _Boom:
    """np.asarray on this raises -- the quarantine EXCEPTION terminal."""

    def __array__(self, dtype=None, copy=None):
        raise RuntimeError("boom")


# ── R4: each terminal produces EXACTLY the expected reason ────────────────────

def test_r4_minted(tmp_path):
    out, rec = _consider_fresh(tmp_path, "mint", *_one_cell_event())
    assert out["verdict"] == "mint"
    assert rec["reason"] == M.REASON_MINTED, (
        "R4 FALSIFIED: an accepted mint must say 'minted', got %r" % rec["reason"])
    assert "failed" not in rec, "nothing failed on an accept"


def test_r4_rederivation(tmp_path):
    g = _gamma(tmp_path, "reder")
    m = MDLMint(g)
    b, act, a = _one_cell_event()
    assert m.consider(b, act, a, game="g1", level=1)["verdict"] == "mint"
    out = m.consider(b, act, a, game="g1", level=1)
    assert out["verdict"] == "rederivation"
    rec = g.fabric.query("collective", "mint_verdicts")[-1]
    assert rec["reason"] == M.REASON_REDERIVATION, (
        "R4 FALSIFIED: a known key must say 'rederivation'")


def test_r4_malformed_input_both_quarantine_paths(tmp_path):
    # the shape-mismatch branch
    out, rec = _consider_fresh(tmp_path, "qshape",
                               np.zeros((3, 3), dtype=int), 6,
                               np.zeros((4, 4), dtype=int))
    assert out["verdict"] == "quarantine"
    assert rec["reason"] == M.REASON_MALFORMED
    assert rec["failed"] == [M.REASON_MALFORMED]
    # the exception branch (np.asarray raises)
    out2, rec2 = _consider_fresh(tmp_path, "qboom", _Boom(), 6, _Boom())
    assert out2["verdict"] == "quarantine"
    assert rec2["reason"] == M.REASON_MALFORMED, (
        "R4 FALSIFIED: the exception quarantine escaped the reason field")


def test_r4_no_change(tmp_path):
    b = np.full((5, 5), 2, dtype=int)
    out, rec = _consider_fresh(tmp_path, "nochange", b, 6, b.copy())
    assert out["verdict"] == "reject"
    assert rec["reason"] == M.REASON_NO_CHANGE
    assert rec["failed"] == [M.REASON_NO_CHANGE] and rec["changed"] == 0


def test_r4_no_effect(tmp_path, monkeypatch):
    """learn_effect never fails on a well-formed changed 2D event today, so
    the terminal is reached the only honest way: the constructor is made to
    return no EFFECT atom."""
    monkeypatch.setattr(E, "learn_effect", lambda b, act, a: None)
    out, rec = _consider_fresh(tmp_path, "noeffect", *_one_cell_event())
    assert out["verdict"] == "reject"
    assert rec["reason"] == M.REASON_NO_EFFECT
    assert rec["failed"] == [M.REASON_NO_EFFECT] and rec["changed"] == 1


def test_r4_support(tmp_path):
    (b1, act, a1), (b2, _, a2) = _distant_pair()
    assert E.learn_effect(b1, act, a1)["key"] != E.learn_effect(b2, act, a2)["key"], (
        "construction: the full keys must differ (novel by key)")
    assert MDLMint._signature(b1, a1, act) == MDLMint._signature(b2, a2, act), (
        "construction: the coarse signatures must be identical (seen by sig)")
    g = _gamma(tmp_path, "support")
    m = MDLMint(g)
    assert m.consider(b1, act, a1, game="g1", level=1)["verdict"] == "mint"
    out = m.consider(b2, act, a2, game="g1", level=1)
    assert out["verdict"] == "reject"
    rec = g.fabric.query("collective", "mint_verdicts")[-1]
    assert rec["reason"] == M.REASON_SUPPORT, (
        "R4 FALSIFIED: a repeat-signature novel key must say 'support'")
    assert rec["failed"] == [M.REASON_SUPPORT]
    assert rec["w"] == pytest.approx(0.5), "the decayed support weight, flat as before"


def test_r4_bbox_half_board_the_movement_transition_shape(tmp_path):
    """THE LIVE QUESTION: a whole-view change (bbox == board) must be
    attributed to the half-board wall SPECIFICALLY -- the cost clauses pass."""
    out, rec = _consider_fresh(tmp_path, "moveshape", *_scramble_event())
    assert out["verdict"] == "reject"
    assert rec["reason"] == M.REASON_BBOX, (
        "R4 FALSIFIED: the whole-view change was not attributed to the bbox "
        "wall -- got %r" % rec["reason"])
    assert rec["failed"] == [M.REASON_BBOX], (
        "the cost clauses pass here; ONLY the wall fails")
    assert rec["mdl"]["bbox_area"] == rec["mdl"]["board_area"] == 36


def test_r4_mdl_cost(tmp_path):
    out, rec = _consider_fresh(tmp_path, "mdlcost", *_mdl_cost_event())
    assert out["verdict"] == "reject"
    assert rec["reason"] == M.REASON_MDL_COST, (
        "R4 FALSIFIED: cost >= R must say 'mdl_cost' when bbox fails at rate "
        "0 too -- got %r" % rec["reason"])


def test_r4_mdl_margin(tmp_path):
    out, rec = _consider_fresh(tmp_path, "mdlmargin", *_mdl_margin_event())
    assert out["verdict"] == "reject"
    assert rec["reason"] == M.REASON_MDL_MARGIN, (
        "R4 FALSIFIED: the margin clause decided (mdl_cost passes, bbox "
        "fails at rate 0 so not extent_premium) -- got %r" % rec["reason"])
    assert M.REASON_MDL_COST not in rec["failed"], (
        "construction broke: cost was meant to clear R")


def test_r4_extent_premium_passes_at_rate_zero_fails_shipped(tmp_path,
                                                             monkeypatch):
    assert M.EXTENT_RATE > 0.0, "the dial ships ON -- else the reason is dead"
    wide = _extent_premium_event()
    # proven to pass at rate 0: the SAME event mints with the dial at 0
    monkeypatch.setattr(M, "EXTENT_RATE", 0.0)
    out0, _ = _consider_fresh(tmp_path, "rate0", *wide)
    assert out0["verdict"] == "mint", "construction: must pass clean at rate 0"
    monkeypatch.undo()
    out, rec = _consider_fresh(tmp_path, "shipped", *wide)
    assert out["verdict"] == "reject"
    assert rec["reason"] == M.REASON_EXTENT_PREMIUM, (
        "R4 FALSIFIED: killed by the premium alone yet not attributed to it "
        "-- got %r" % rec["reason"])
    assert rec["failed"] == [M.REASON_MDL_COST, M.REASON_MDL_MARGIN], (
        "the raw failing clauses stay named; the reason disambiguates")


# ── F1: the failed list is complete; reason is first in evaluation order ──────

def test_f1_failed_list_complete_and_reason_first_in_order(tmp_path):
    out, rec = _consider_fresh(tmp_path, "multi", *_mdl_cost_event())
    assert out["verdict"] == "reject"
    assert rec["failed"] == [M.REASON_MDL_COST, M.REASON_MDL_MARGIN,
                            M.REASON_BBOX], (
        "F1 FALSIFIED: every independently failing clause must be listed, in "
        "evaluation order -- got %r" % rec["failed"])
    assert rec["reason"] == rec["failed"][0], (
        "F1 FALSIFIED: the reason must be the FIRST failing clause")
    assert tuple(rec["failed"]) == M.MDL_CLAUSE_ORDER, (
        "the listed order IS the code's evaluation order, published as "
        "MDL_CLAUSE_ORDER")


# ── F2: no terminal escapes -- the whole vocabulary, every return path ────────

def test_f2_every_terminal_ledgers_a_vocabulary_reason(tmp_path, monkeypatch):
    b1c = _one_cell_event()
    (bp1, act, ap1), (bp2, _, ap2) = _distant_pair()
    flat = np.full((5, 5), 2, dtype=int)
    seen = {}
    # fresh-store single-event terminals
    for name, ev in (("mint", b1c),
                     ("q_shape", (np.zeros((3, 3), dtype=int), 6,
                                  np.zeros((4, 4), dtype=int))),
                     ("q_boom", (_Boom(), 6, _Boom())),
                     ("no_change", (flat, 6, flat.copy())),
                     ("bbox", _scramble_event()),
                     ("mdl_cost", _mdl_cost_event()),
                     ("mdl_margin", _mdl_margin_event()),
                     ("extent", _extent_premium_event())):
        out, rec = _consider_fresh(tmp_path, "f2_%s" % name, *ev)
        assert rec["reason"] in M.REASONS, (
            "F2 FALSIFIED (%s): reason %r escapes the closed vocabulary"
            % (name, rec.get("reason")))
        seen[rec["reason"]] = out["verdict"]
    # two-event terminals on one store: rederivation, then support
    g = _gamma(tmp_path, "f2_pair")
    m = MDLMint(g)
    m.consider(bp1, act, ap1, game="g1", level=1)                 # mint
    m.consider(bp1, act, ap1, game="g1", level=1)                 # rederivation
    m.consider(bp2, act, ap2, game="g1", level=1)                 # support
    recs = g.fabric.query("collective", "mint_verdicts")
    assert len(recs) == 3, "one record per consider(), nothing silent"
    for rec in recs:
        assert rec["reason"] in M.REASONS
        seen[rec["reason"]] = rec["verdict"]
    # the no_effect terminal (constructor made to fail -- see R4)
    monkeypatch.setattr(E, "learn_effect", lambda b, a_, c: None)
    _, rec = _consider_fresh(tmp_path, "f2_noeffect", *b1c)
    seen[rec["reason"]] = rec["verdict"]
    monkeypatch.undo()
    assert set(seen) == set(M.REASONS), (
        "F2 FALSIFIED: the sweep must observe the WHOLE vocabulary; missing "
        "%r, extra %r" % (set(M.REASONS) - set(seen), set(seen) - set(M.REASONS)))


# ── F3: the numerics equal independently recomputed values ────────────────────

def _recompute(before, after):
    """The audit terms, re-derived here from the frames alone (a fresh atom
    retains bbox_area - changed cells; the mint's own arithmetic order)."""
    b = np.asarray(before)
    a = np.asarray(after)
    diff = b != a
    changed = int(diff.sum())
    rows = np.flatnonzero(diff.any(axis=1))
    cols = np.flatnonzero(diff.any(axis=0))
    bbox_area = int((rows[-1] - rows[0] + 1) * (cols[-1] - cols[0] + 1))
    retained = bbox_area - changed
    return {"cost": (1.0 + float(changed)) + M.EXTENT_RATE * retained,
            "R": M.RESIDUAL_CELL_COST * float(changed) + M.UNEXPLAINED_PREMIUM,
            "bbox_area": bbox_area, "board_area": int(b.size),
            "retained": retained, "w": 1.0,
            "extent_rate": float(M.EXTENT_RATE)}, changed


def test_f3_record_numerics_equal_recomputed_values(tmp_path):
    for name, ev in (("mint", _one_cell_event()),
                     ("extent", _extent_premium_event()),
                     ("bbox", _scramble_event())):
        b, act, a = ev
        _, rec = _consider_fresh(tmp_path, "f3_%s" % name, b, act, a)
        expected, changed = _recompute(b, a)
        assert rec["changed"] == changed, "F3 FALSIFIED (%s): changed" % name
        assert rec["mdl"] == expected, (
            "F3 FALSIFIED (%s): numerics diverge from the recomputation\n"
            "got=%r\nexpected=%r" % (name, rec["mdl"], expected))


def test_f3_flat_w_emission_sites_unchanged(tmp_path):
    """The compat guard, stated: lp_drive._w_bar means FLAT "w" over verdict
    rows carrying one. Mint and support-reject carry it exactly as before;
    an MDL reject does NOT grow a flat "w" -- its w lives inside "mdl"."""
    _, mint_rec = _consider_fresh(tmp_path, "wflat_mint", *_one_cell_event())
    assert mint_rec["w"] == 1.0 and mint_rec["mdl"]["w"] == 1.0
    _, rej = _consider_fresh(tmp_path, "wflat_rej", *_scramble_event())
    assert rej["verdict"] == "reject" and "w" not in rej, (
        "F3 FALSIFIED: a flat 'w' appeared on an MDL reject -- lp_drive's "
        "w_bar signal would silently shift")
    assert rej["mdl"]["w"] == 1.0, "the audit copy: full support reached MDL"
    # and the A3-4 stamps still ride on every record (additive, untouched)
    assert "ep" in mint_rec and "sigma" in mint_rec and "key" in mint_rec


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
