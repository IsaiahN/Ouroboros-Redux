"""GATE: hypothesis property tests for the pure functions.

Three pure surfaces, each tested against its documented contract:

  * effects.classify_transform / invert_transform (engines/egocentric/effects.py):
    applying a typed transform to a suitable grid and classifying the pair recovers
    the ttype+params; the inverse transform applied after the transform is the
    identity; invert is an involution. Grids are generated all-distinct-valued so
    recovery is well-defined (classify's "first exact match wins" makes symmetric
    grids legitimately ambiguous -- that is documented behaviour, not a bug).
  * StarvationBook.starved (engines/egocentric/starvation.py): a PURE function of
    the counters dict -- identical counters (and any insertion order) replay to
    identical records; codes come only from CODES; at most one record per socket.
  * KnowledgeFabric append/query (engines/egocentric/fabric.py): what was appended
    is queried back, in insertion order, with a monotonic per-stream "seq".

Examples stay modest (max_examples=50, deadline=None) for CI stability.
"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np
from hypothesis import assume, given, settings
from hypothesis import strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import effects as E
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.starvation import CODES, SOCKETS, StarvationBook

MODEST = settings(max_examples=50, deadline=None)


# ── grid strategies ───────────────────────────────────────────────────────────

@st.composite
def distinct_grids(draw, min_side=2, max_side=5):
    """All cell values distinct: rotations/reflections cannot collide with each
    other or with a translate explanation, so classification is unambiguous."""
    h = draw(st.integers(min_side, max_side))
    w = draw(st.integers(min_side, max_side))
    vals = draw(st.permutations(list(range(h * w))))
    return np.array(vals, dtype=int).reshape(h, w)


@st.composite
def translate_cases(draw):
    """A uniform-fill grid with one all-distinct object, shifted in bounds."""
    h = draw(st.integers(2, 5))
    w = draw(st.integers(2, 5))
    oh = draw(st.integers(1, h - 1))
    ow = draw(st.integers(1, w - 1))
    fill = 0
    vals = draw(st.permutations(list(range(1, oh * ow + 1))))
    obj = np.array(vals, dtype=int).reshape(oh, ow)
    r0 = draw(st.integers(0, h - oh))
    c0 = draw(st.integers(0, w - ow))
    dx = draw(st.integers(-r0, h - oh - r0))
    dy = draw(st.integers(-c0, w - ow - c0))
    assume((dx, dy) != (0, 0))
    before = np.full((h, w), fill, dtype=int)
    before[r0:r0 + oh, c0:c0 + ow] = obj
    after = np.full((h, w), fill, dtype=int)
    after[r0 + dx:r0 + dx + oh, c0 + dy:c0 + dy + ow] = obj
    return before, after, dx, dy, fill


def _apply_typed(ttype, params, grid):
    """Pure re-application of a typed transform, mirroring classify's semantics."""
    g = np.asarray(grid)
    if ttype == "ROTATE":
        return np.rot90(g, params["k"])
    if ttype == "REFLECT":
        return np.flipud(g) if params["axis"] == "h" else np.fliplr(g)
    if ttype == "TRANSLATE":
        dx, dy, fill = params["dx"], params["dy"], params["fill"]
        out = np.full_like(g, fill)
        h, w = g.shape
        for r in range(h):
            for c in range(w):
                if g[r, c] != fill:
                    out[r + dx, c + dy] = g[r, c]
        return out
    raise AssertionError("unexpected ttype %r" % ttype)


# ── classify / invert round-trips ─────────────────────────────────────────────

@MODEST
@given(g=distinct_grids(), k=st.integers(1, 3))
def test_rotate_classify_and_invert_roundtrip(g, k):
    after = np.rot90(g, k)
    t = E.classify_transform(g, after)
    assert t == {"ttype": "ROTATE", "params": {"k": k}}, (t, k, g.tolist())
    inv = E.invert_transform(t["ttype"], t["params"])
    assert inv is not None
    ti, pi = inv
    back = _apply_typed(ti, pi, after)
    assert np.array_equal(back, g), (ti, pi, g.tolist())
    assert E.invert_transform(ti, pi) == (t["ttype"], {"k": k % 4}), "invert is an involution"


@MODEST
@given(g=distinct_grids(), axis=st.sampled_from(["h", "v"]))
def test_reflect_classify_and_invert_roundtrip(g, axis):
    after = np.flipud(g) if axis == "h" else np.fliplr(g)
    t = E.classify_transform(g, after)
    assert t == {"ttype": "REFLECT", "params": {"axis": axis}}, (t, axis, g.tolist())
    inv = E.invert_transform(t["ttype"], t["params"])
    assert inv == ("REFLECT", {"axis": axis}), "REFLECT is self-inverse"
    back = _apply_typed(inv[0], inv[1], after)
    assert np.array_equal(back, g)


@MODEST
@given(case=translate_cases())
def test_translate_classify_and_invert_roundtrip(case):
    before, after, dx, dy, fill = case
    t = E.classify_transform(before, after)
    assert t == {"ttype": "TRANSLATE",
                 "params": {"dx": dx, "dy": dy, "fill": fill}}, (t, dx, dy,
                                                                 before.tolist())
    inv = E.invert_transform(t["ttype"], t["params"])
    assert inv is not None
    ti, pi = inv
    assert (ti, pi) == ("TRANSLATE", {"dx": -dx, "dy": -dy, "fill": fill})
    back = _apply_typed(ti, pi, after)
    assert np.array_equal(back, before)
    assert E.invert_transform(ti, pi) == (t["ttype"], t["params"]), "invert is an involution"


# ── StarvationBook purity ─────────────────────────────────────────────────────

_COUNTER_KEYS = sorted({k for _s, tried, passed, _c, _n in SOCKETS
                        for k in (tried, passed)} | {"junk", "other"})

counters_st = st.dictionaries(
    keys=st.sampled_from(_COUNTER_KEYS),
    values=st.one_of(st.integers(-5, 200), st.none(),
                     st.sampled_from(["0", "12", "x"])),
    max_size=len(_COUNTER_KEYS))


@MODEST
@given(counters=counters_st)
def test_starved_is_pure_and_order_independent(counters):
    first = StarvationBook.starved(counters)
    second = StarvationBook.starved(dict(counters))
    assert first == second, "same counters twice must replay to identical records"
    reordered = dict(reversed(list(counters.items())))
    assert StarvationBook.starved(reordered) == first, (
        "dict insertion order must not matter")
    sockets = [r["socket"] for r in first]
    assert len(sockets) == len(set(sockets)), "at most one record per socket"
    assert all(r["code"] in CODES for r in first), "codes come only from CODES"


# ── fabric append/query round-trip ────────────────────────────────────────────

records_st = st.lists(
    st.dictionaries(
        keys=st.text(alphabet="abcxyz_", min_size=1, max_size=6),
        values=st.one_of(st.integers(-1000, 1000), st.booleans(), st.none(),
                         st.text(max_size=12)),
        max_size=4),
    min_size=1, max_size=8)


@MODEST
@given(records=records_st,
       scope=st.sampled_from(["collective", "personal", "kin"]),
       topic=st.text(alphabet="abcdfgh_", min_size=1, max_size=8))
def test_fabric_append_then_query_returns_what_was_written_in_order(records, scope, topic):
    with tempfile.TemporaryDirectory() as root:
        fab = KnowledgeFabric(os.path.join(root, "fab"), agent_id="a", kin_key="v4")
        for rec in records:
            fab.append(scope, topic, rec)
        got = fab.query(scope, topic)
        assert len(got) == len(records)
        for i, (written, read) in enumerate(zip(records, got, strict=True)):
            assert read["seq"] == i + 1, "seq must be monotonic from 1"
            for k, v in written.items():
                if k == "seq":
                    continue          # append() owns "seq"; payload key shadowed by design
                assert read.get(k) == v, (i, k, written, read)
