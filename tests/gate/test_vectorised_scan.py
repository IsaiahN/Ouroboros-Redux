"""THE VECTORISED ANCHOR SCAN MUST BE INVISIBLE EXCEPT IN TIME.
PREREG_W2A2_VECTORISE_ANCHOR_SCAN.md -- W2a-2 (the pre-committed successor of
F1's losing condition, F1_VERDICT_AND_SHADOW_TEST.md).

F1 held at 92.5%: the cost is INSIDE apply_effect -- ~4ms and ~1,450 numpy
.all() calls per application, the anchor scan slicing the frame at every
candidate position in a Python loop. The build: ONE numpy pass (sliding-window
view + a single equality reduction) behind ONE dispatch
(effects._ANCHOR_SCAN_VECTORISED); the scalar path stays in the file verbatim
as the undo and the equivalence oracle.

The falsifiers, as gated here:
  F1 (ABSOLUTE)  on a deterministically generated corpus of (atom, frame)
                 pairs spanning dims, palettes, shape masks, edge anchors,
                 no-match cases and multi-match tie-breaks, the vectorised
                 path returns BYTE-IDENTICAL results to the scalar path --
                 including None-cases. Any divergence fails the build.
  F3             known-negative BOTH directions: a patch that matches nowhere
                 returns the scalar path's no-match (None); a multi-match
                 frame picks the scalar path's anchor (first in row-major).
  R4             constructed frames with KNOWN anchor sets reproduce those
                 sets exactly, in scan order, in both scan modes.
  STRUCTURAL     the per-atom hot path contains no Python-level per-anchor
                 loop: no nested For, no For over range() candidate
                 enumeration (AST), and the scalar oracle is NEVER invoked
                 on the vectorised path (call count == 0).

Seeded with a FIXED CONSTANT (the prereg's date), never a clock.
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

from engines.egocentric import effects as E  # noqa: E402

SEED = 20260820  # fixed constant (the prereg date) -- deterministic forever


# ── the two scan modes, byte-level comparison ─────────────────────────────────

def _in_mode(vectorised: bool, atom, frame):
    """Run apply_effect with the dispatch pinned; always restore the flag.
    A raised exception is an OUTCOME too -- captured, compared across modes."""
    prev = E._ANCHOR_SCAN_VECTORISED
    E._ANCHOR_SCAN_VECTORISED = bool(vectorised)
    try:
        return E.apply_effect(atom, frame)
    except Exception as exc:                              # noqa: BLE001
        return ("RAISED", type(exc).__name__)
    finally:
        E._ANCHOR_SCAN_VECTORISED = prev


def _identical(x, y) -> bool:
    """Byte-identical: both None, same raise, or same dtype + shape + bytes."""
    if x is None or y is None:
        return x is None and y is None
    if isinstance(x, tuple) or isinstance(y, tuple):
        return x == y                                     # ("RAISED", type)
    return (x.dtype == y.dtype and x.shape == y.shape
            and x.tobytes() == y.tobytes())


def _assert_equivalent(atom, frame, label):
    vec = _in_mode(True, atom, frame)
    sca = _in_mode(False, atom, frame)
    assert _identical(vec, sca), (
        "F1 FALSIFIED (%s): vectorised != scalar\natom=%r\nframe=\n%r\n"
        "vec=%r\nsca=%r" % (label, atom, frame, vec, sca))
    return vec, sca


# ── corpus construction: deterministic, spanning the prereg's axes ────────────

def _raw(ctx_rows, out_rows, action=6):
    """A raw EFFECT atom (no ttype): the exact-context scan path."""
    return {"kind": "EFFECT", "arity": 2, "key": "eff-test", "action": action,
            "context": ctx_rows,
            "transform": {"before": ctx_rows, "after": out_rows},
            "changed": 1}


def _typed(ttype, params, ctx_rows, out_rows, action=2):
    """A typed EFFECT atom: the parameterized path (raw scan is the fallback)."""
    atom = _raw(ctx_rows, out_rows, action)
    atom["ttype"] = ttype
    atom["params"] = params
    return atom


def _learned_pairs(rng):
    """Atoms learned from real frame pairs (the constructor's own output),
    replayed on fresh frames: random, guaranteed-match, and edge-anchored."""
    pairs = []
    for i in range(30):
        h, w = int(rng.integers(3, 24)), int(rng.integers(3, 24))
        before = rng.integers(0, 9, size=(h, w)).astype(int)
        after = before.copy()
        ph = int(rng.integers(1, min(4, h) + 1))
        pw = int(rng.integers(1, min(4, w) + 1))
        r = int(rng.integers(0, h - ph + 1))
        c = int(rng.integers(0, w - pw + 1))
        after[r:r + ph, c:c + pw] = (after[r:r + ph, c:c + pw]
                                     + 1 + rng.integers(0, 4)) % 10
        atom = E.learn_effect(before, int(rng.integers(0, 7)), after)
        if atom is None or atom.get("kind") != "EFFECT":
            continue
        ctx = np.asarray(atom["context"])
        pairs.append((atom, rng.integers(0, 9, size=(
            int(rng.integers(2, 40)), int(rng.integers(2, 40)))).astype(int),
            "learned/random-%d" % i))
        pairs.append((atom, before.copy(), "learned/source-%d" % i))
        # edge anchors: the context patch stamped at every corner
        fh = ctx.shape[0] + int(rng.integers(0, 9))
        fw = ctx.shape[1] + int(rng.integers(0, 9))
        base = rng.integers(0, 10, size=(fh, fw)).astype(int)
        for j, (er, ec) in enumerate([(0, 0), (0, fw - ctx.shape[1]),
                                      (fh - ctx.shape[0], 0),
                                      (fh - ctx.shape[0], fw - ctx.shape[1])]):
            f = base.copy()
            f[er:er + ctx.shape[0], ec:ec + ctx.shape[1]] = ctx
            pairs.append((atom, f, "learned/edge-%d-%d" % (i, j)))
        # multi-match: the context tiled -- the tie-break axis
        pairs.append((atom, np.tile(ctx, (2, 2)).astype(int),
                      "learned/tiled-%d" % i))
        # no-match: a palette the atom has never seen
        pairs.append((atom, np.full((fh, fw), 12, dtype=int),
                      "learned/nomatch-%d" % i))
    return pairs


def _typed_battery(rng):
    """Hand-built typed atoms crossing every parameterized op with frames that
    match at edges, match repeatedly, or match nowhere."""
    sq = [[1, 2], [3, 4]]
    battery = [
        _typed("ROTATE", {"k": 1}, sq, [[3, 1], [4, 2]]),
        _typed("REFLECT", {"axis": "h"}, sq, [[3, 4], [1, 2]]),
        _typed("REFLECT", {"axis": "v"}, sq, [[2, 1], [4, 3]]),
        _typed("SCALE", {"fx": 2, "fy": 2, "mode": "up"}, sq, [[9, 9], [9, 9]]),
        _typed("COLOUR_PERM", {"mapping": [[1, 5], [2, 6]]}, sq, [[5, 6], [3, 4]]),
        _typed("TRANSLATE", {"dx": 1, "dy": 0, "fill": 0},
               [[7, 0], [0, 0]], [[0, 0], [7, 0]]),
        # B8 shape-bound ops: the masked (sparse) anchor scan
        _typed("TRANSLATE", {"dx": 0, "dy": 2, "fill": 0,
                             "shape": [[0, 0, 5], [1, 1, 5]]},
               [[5, 0], [0, 5]], [[0, 5], [5, 0]]),
        _typed("OBJ_APPEAR", {"shape": [[0, 0, 8], [0, 1, 8]], "fill": 0},
               [[0, 0]], [[8, 8]]),
        _typed("OBJ_VANISH", {"shape": [[0, 0, 8], [0, 1, 8]], "fill": 0},
               [[8, 8]], [[0, 0]]),
        _typed("COLOUR_PERM", {"mapping": [[5, 9]],
                               "shape": [[0, 0, 5], [1, 1, 5]]},
               [[5, 0], [0, 5]], [[9, 0], [0, 9]]),
    ]
    pairs = []
    for i, atom in enumerate(battery):
        ctx = np.asarray(atom["context"])
        ph, pw = ctx.shape
        for j in range(6):
            fh, fw = ph + int(rng.integers(0, 12)), pw + int(rng.integers(0, 12))
            f = rng.integers(0, 10, size=(fh, fw)).astype(int)
            pairs.append((atom, f, "typed-%d/random-%d" % (i, j)))
            g = np.zeros((fh, fw), dtype=int)
            er = int(rng.integers(0, fh - ph + 1))
            ec = int(rng.integers(0, fw - pw + 1))
            g[er:er + ph, ec:ec + pw] = ctx
            pairs.append((atom, g, "typed-%d/placed-%d" % (i, j)))
        pairs.append((atom, np.full((6, 6), 12, dtype=int), "typed-%d/nomatch" % i))
        pairs.append((atom, np.tile(ctx, (2, 3)).astype(int), "typed-%d/tiled" % i))
    return pairs


def _dontcare_battery(rng):
    """W2-S2 (PREREG_W2_STAGE2_CONTEXT_MIN.md): DON'T-CARE-bearing atoms. The
    SCALAR path is the semantics oracle for the sentinel too: a DONT_CARE
    context cell matches any frame value, a DONT_CARE after-patch cell leaves
    the frame's value in place, and both scan modes must agree byte-for-byte
    across match / no-match / multi-match / edge anchors."""
    dc = E.DONT_CARE
    # a 3x3 minimised patch: centre changed, corners DON'T-CARE, edges retained
    ctx = [[dc, 1, dc], [1, 2, 1], [dc, 1, dc]]
    out = [[dc, 1, dc], [1, 7, 1], [dc, 1, dc]]
    wild = _raw(ctx, out)
    # a fully retained twin (no sentinel) for contrast on the same frames
    lit = _raw([[3, 1, 3], [1, 2, 1], [3, 1, 3]],
               [[3, 1, 3], [1, 7, 1], [3, 1, 3]])
    # a minimised TYPED atom: the typed path must bail to the raw scan,
    # never stamp the sentinel into a frame
    typed_wild = _typed("COLOUR_PERM", {"mapping": [[2, 7]]}, ctx, out)
    row = _raw([[dc, 5, dc]], [[dc, 6, dc]])              # 1x3, sparse retained
    alldc = _raw([[dc, dc]], [[dc, dc]])                  # degenerate: all wildcard
    pairs = []
    for i, atom in enumerate((wild, lit, typed_wild, row)):
        actx = np.asarray(atom["context"])
        ph, pw = actx.shape
        for j in range(6):
            fh = ph + int(rng.integers(0, 10))
            fw = pw + int(rng.integers(0, 10))
            f = rng.integers(0, 10, size=(fh, fw)).astype(int)
            pairs.append((atom, f, "dc-%d/random-%d" % (i, j)))
            g = f.copy()
            er = int(rng.integers(0, fh - ph + 1))
            ec = int(rng.integers(0, fw - pw + 1))
            reg = g[er:er + ph, ec:ec + pw]
            m = actx != dc
            reg[m] = actx[m]                              # retained cells placed,
            pairs.append((atom, g, "dc-%d/placed-%d" % (i, j)))  # wildcards left random
        pairs.append((atom, np.full((5, 5), 9, dtype=int), "dc-%d/nomatch" % i))
    # multi-match tie-break with wildcards: retained column repeated
    tie = np.zeros((4, 6), dtype=int)
    tie[1, 1] = tie[1, 4] = tie[2, 2] = 5
    pairs.append((row, tie, "dc/multi-match"))
    pairs.append((alldc, np.arange(12).reshape(3, 4), "dc/all-wild"))
    pairs.append((alldc, np.array([[8]]), "dc/all-wild-too-small"))
    return pairs


def _oddities():
    """Dims/dtypes/degenerates the prereg's 'spanning' clause demands."""
    one = _raw([[3]], [[4]])
    eff_if = {"kind": "EFFECT_IF", "arity": 3, "key": "effif-test", "action": 6,
              "condition": {"cells": [[0, 0, 9]]}, "then": _raw([[3]], [[4]]),
              "else": _raw([[3]], [[5]]), "changed": 1}
    hot = np.zeros((4, 4), dtype=int)
    hot[0, 0] = 9
    hot[2, 2] = 3
    cold = np.zeros((4, 4), dtype=int)
    cold[2, 2] = 3
    return [
        (one, np.array([[3]]), "odd/1x1-match"),
        (one, np.array([[7]]), "odd/1x1-nomatch"),
        (one, np.full((64, 64), 3, dtype=int), "odd/64x64-all-match"),
        (one, np.zeros((64, 64), dtype=int), "odd/64x64-nomatch"),
        (_raw([[1, 2, 3]], [[4, 5, 6]]), np.arange(64).reshape(8, 8) % 8,
         "odd/wide-ctx"),
        (_raw([[1], [2], [3]], [[4], [5], [6]]),
         (np.arange(64).reshape(8, 8) // 8).astype(int), "odd/tall-ctx"),
        (one, np.full((3, 3), 3, dtype=np.uint8), "odd/uint8-frame"),
        (_typed("COLOUR_PERM", {"mapping": [[5, 9]],
                                "shape": [[0, 0, 5]]}, [[5]], [[9]]),
         np.full((3, 3), 5.0), "odd/float-frame-shape-op"),
        (_raw([[9, 9], [9, 9]], [[1, 1], [1, 1]]), np.full((2, 2), 9, dtype=int),
         "odd/ctx-equals-frame"),
        (_raw([[9, 9], [9, 9]], [[1, 1], [1, 1]]), np.array([[9]]),
         "odd/ctx-bigger-than-frame"),
        (eff_if, hot, "odd/effect-if-then"),
        (eff_if, cold, "odd/effect-if-else"),
    ]


def _corpus():
    rng = np.random.default_rng(SEED)
    return (_learned_pairs(rng) + _typed_battery(rng) + _dontcare_battery(rng)
            + _oddities())


# ── F1: EQUIVALENCE, absolute -- byte-identical including None ────────────────

def test_f1_generated_corpus_byte_identical_including_none():
    corpus = _corpus()
    assert len(corpus) > 200, "corpus construction collapsed -- not a sweep"
    nones = matches = 0
    for atom, frame, label in corpus:
        vec, _sca = _assert_equivalent(atom, frame, label)
        if vec is None:
            nones += 1
        elif not isinstance(vec, tuple):                  # a returned frame
            matches += 1
    # the corpus must actually SPAN the axes, or F1 passed on thin air
    assert nones >= 10, "corpus has too few None-cases (%d)" % nones
    assert matches >= 50, "corpus has too few match-cases (%d)" % matches


def test_f1_multi_match_anchor_lists_are_identical_not_just_first():
    """Stronger than the returned array: on multi-match frames the FULL anchor
    sequence (order included) agrees between the scan modes -- the tie-break
    is 'first in existing scan order' at every rank, not only rank one."""
    rng = np.random.default_rng(SEED + 1)
    prev = E._ANCHOR_SCAN_VECTORISED
    try:
        for i in range(20):
            ph, pw = int(rng.integers(1, 4)), int(rng.integers(1, 4))
            ctx = rng.integers(0, 3, size=(ph, pw)).astype(int)
            frame = rng.integers(0, 3, size=(int(rng.integers(4, 20)),
                                             int(rng.integers(4, 20)))).astype(int)
            E._ANCHOR_SCAN_VECTORISED = True
            vec = list(E._context_anchors(frame, ctx))
            E._ANCHOR_SCAN_VECTORISED = False
            sca = list(E._context_anchors(frame, ctx))
            assert [(int(r), int(c)) for r, c in vec] == sca, (
                "anchor sequence diverged (case %d): vec=%r sca=%r"
                % (i, vec, sca))
    finally:
        E._ANCHOR_SCAN_VECTORISED = prev


def test_f1_chunked_reduction_equals_unchunked():
    """The memory guard must not change the answer: force a tiny chunk budget
    so a 64x64 scan takes MANY chunks and assert the same result bytes."""
    atom = _raw([[3, 3], [3, 3]], [[4, 4], [4, 4]])
    frame = np.zeros((64, 64), dtype=int)
    frame[50:52, 60:62] = 3
    full = _in_mode(True, atom, frame)
    prev = E._SCAN_CHUNK_BYTES
    E._SCAN_CHUNK_BYTES = 64                              # a few rows per chunk
    try:
        tiny = _in_mode(True, atom, frame)
    finally:
        E._SCAN_CHUNK_BYTES = prev
    assert _identical(full, tiny), "chunking changed the scan result"
    assert _identical(full, _in_mode(False, atom, frame))


# ── F3: known-negative, both directions ───────────────────────────────────────

def test_f3_no_match_returns_the_scalar_no_match():
    atom = _raw([[7, 7]], [[8, 8]])                       # 7 occurs nowhere
    frame = np.zeros((9, 9), dtype=int)
    vec, sca = _assert_equivalent(atom, frame, "f3/no-match")
    assert vec is None and sca is None, "F3 FALSIFIED: no-match must be None"


def test_f3_multi_match_picks_the_scalar_anchor():
    """Three placed matches; the winner must be the scalar order's first
    (row-major), proven on the WRITTEN CELLS, not just byte equality."""
    atom = _raw([[5]], [[8]])
    frame = np.zeros((6, 6), dtype=int)
    for r, c in [(1, 1), (1, 4), (3, 2)]:
        frame[r, c] = 5
    vec, sca = _assert_equivalent(atom, frame, "f3/multi-match")
    assert vec is not None
    assert vec[1, 1] == 8, "F3 FALSIFIED: the first row-major anchor lost"
    assert vec[1, 4] == 5 and vec[3, 2] == 5, (
        "F3 FALSIFIED: a later anchor was written -- wrong tie-break")


def test_f3_shape_scan_multi_match_picks_the_scalar_anchor():
    atom = _typed("OBJ_VANISH", {"shape": [[0, 0, 8], [1, 1, 8]], "fill": 0},
                  [[8, 0], [0, 8]], [[0, 0], [0, 0]])
    frame = np.zeros((7, 7), dtype=int)
    for r, c in [(0, 3), (2, 1), (4, 4)]:                 # three diagonal pairs
        frame[r, c] = frame[r + 1, c + 1] = 8
    vec, _sca = _assert_equivalent(atom, frame, "f3/shape-multi")
    assert vec is not None
    assert vec[0, 3] == 0 and vec[1, 4] == 0, "first shape anchor must win"
    assert vec[2, 1] == 8 and vec[5, 5] == 8, "later shape anchors must survive"


# ── R4: constructed frames with KNOWN anchor sets, reproduced exactly ─────────

def test_r4_known_context_anchor_sets_exact():
    frame = np.zeros((5, 7), dtype=int)
    placed = [(0, 0), (2, 3), (4, 6)]
    for r, c in placed:
        frame[r, c] = 9
    for mode in (True, False):
        prev = E._ANCHOR_SCAN_VECTORISED
        E._ANCHOR_SCAN_VECTORISED = mode
        try:
            got = [(int(r), int(c))
                   for r, c in E._context_anchors(frame, np.array([[9]]))]
        finally:
            E._ANCHOR_SCAN_VECTORISED = prev
        assert got == placed, (
            "R4 FALSIFIED (mode=%s): %r != %r" % (mode, got, placed))


def test_r4_overlapping_matches_enumerate_completely_in_order():
    frame = np.full((3, 4), 3, dtype=int)
    expected = [(r, c) for r in range(3) for c in range(3)]  # 1x2 ctx overlaps
    for mode in (True, False):
        prev = E._ANCHOR_SCAN_VECTORISED
        E._ANCHOR_SCAN_VECTORISED = mode
        try:
            got = [(int(r), int(c))
                   for r, c in E._context_anchors(frame, np.array([[3, 3]]))]
        finally:
            E._ANCHOR_SCAN_VECTORISED = prev
        assert got == expected, "R4 FALSIFIED (mode=%s): %r" % (mode, got)


def test_r4_known_shape_anchor_sets_exact():
    shape = [[0, 0, 5], [1, 1, 5]]                        # a diagonal pair
    frame = np.zeros((6, 6), dtype=int)
    placed = [(0, 0), (2, 3), (4, 1)]
    for r, c in placed:
        frame[r, c] = frame[r + 1, c + 1] = 5
    for mode in (True, False):
        prev = E._ANCHOR_SCAN_VECTORISED
        E._ANCHOR_SCAN_VECTORISED = mode
        try:
            got = [(int(r), int(c))
                   for r, c in E._iter_shape_anchors(frame, shape)]
        finally:
            E._ANCHOR_SCAN_VECTORISED = prev
        assert got == placed, (
            "R4 FALSIFIED (mode=%s): %r != %r" % (mode, got, placed))


# ── STRUCTURAL: no Python-level per-anchor loop on the hot path ───────────────

def _for_nodes(fn):
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return [n for n in ast.walk(tree) if isinstance(n, ast.For)]


def test_structural_dispatch_defaults_to_vectorised():
    assert E._ANCHOR_SCAN_VECTORISED is True, (
        "the dispatch ships scalar -- the build is not on")


def test_structural_hot_path_has_no_per_anchor_loop():
    """AST: the appliers may loop over MATCHES (_context_anchors) but never
    enumerate candidate positions themselves -- no nested For, no For over
    range() (the old per-anchor scan's exact shape)."""
    for fn in (E.apply_effect, E._apply_typed, E._apply_translate):
        for node in _for_nodes(fn):
            inner = [n for n in ast.walk(node)
                     if isinstance(n, ast.For) and n is not node]
            assert not inner, (
                "STRUCTURAL FALSIFIED: nested For in %s (line %d) -- the "
                "per-anchor double loop is back" % (fn.__name__, node.lineno))
            it = node.iter
            assert not (isinstance(it, ast.Call)
                        and isinstance(it.func, ast.Name)
                        and it.func.id == "range"), (
                "STRUCTURAL FALSIFIED: %s loops over range() (line %d) -- "
                "candidate enumeration is back in Python"
                % (fn.__name__, node.lineno))


def test_structural_vector_pass_is_numpy_not_python():
    """The vectorised scan itself: built on sliding_window_view, and its only
    For loop is the row-chunk memory guard -- never nested, never per-anchor."""
    src = inspect.getsource(E._context_anchors_vector)
    assert "sliding_window_view" in src, (
        "the vector pass no longer uses the windowed view")
    fors = _for_nodes(E._context_anchors_vector)
    assert len(fors) <= 1, "more than the one chunk loop in the vector pass"
    for node in fors:
        inner = [n for n in ast.walk(node)
                 if isinstance(n, ast.For) and n is not node]
        assert not inner, "nested For inside the vector pass"


def test_structural_scalar_oracle_never_called_on_the_vectorised_path(monkeypatch):
    """Call-count check, as the brief allows: with the dispatch ON, a raw
    atom, a typed atom and a shape-bound atom applied to a 64x64 frame must
    reach the scalar generators ZERO times."""
    calls = []
    real_ctx = E._context_anchors_scalar
    real_shp = E._shape_anchors_scalar

    def spy_ctx(b, ctx):
        calls.append("ctx")
        return real_ctx(b, ctx)

    def spy_shp(b, shape):
        calls.append("shape")
        return real_shp(b, shape)

    monkeypatch.setattr(E, "_context_anchors_scalar", spy_ctx)
    monkeypatch.setattr(E, "_shape_anchors_scalar", spy_shp)

    frame = np.zeros((64, 64), dtype=int)
    frame[40, 41] = 3
    assert E.apply_effect(_raw([[3]], [[4]]), frame) is not None
    assert E.apply_effect(_typed("COLOUR_PERM", {"mapping": [[3, 5]]},
                                 [[3]], [[5]]), frame) is not None
    assert E.apply_effect(
        _typed("OBJ_VANISH", {"shape": [[0, 0, 3]], "fill": 0},
               [[3]], [[0]]), frame) is not None
    assert E.apply_effect(_raw([[7]], [[8]]), frame) is None  # full no-match scan
    assert calls == [], (
        "STRUCTURAL FALSIFIED: the scalar oracle ran on the vectorised "
        "path: %r" % calls)
