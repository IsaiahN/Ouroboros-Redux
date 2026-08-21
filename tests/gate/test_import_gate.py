"""THE IMPORT ADMISSION GATE: ADMISSION PAYS THE SAME BARGAIN THE MINT PAYS.

The defect (Seat 3, 2026-08-20): the extent premium (mint.EXTENT_RATE,
PREREG_W2_STAGE2_CONTEXT_MIN.md) prices every LOCALLY minted atom's context
extent -- but an atom arriving over the network (origin "imported", the
consumer.seed_imports path) entered local Gamma WITHOUT meeting the bargain.
The premium was a door with a wall beside it: pre-premium wide atoms
(PI_REPLAY_RESULT.md's median 976-cell contexts licensing 26-cell changes,
structurally unable to apply anywhere) kept circulating between boxes.

The build under test: consumer.admission_price applies the mint's OWN
inequality at the Gamma write in seed_imports -- constants imported from
mint/effects, never duplicated:

    cost = effects.encoding_cost_atom(atom)
           + mint.EXTENT_RATE * effects.context_retained_cells(atom)
    R    = mint.RESIDUAL_CELL_COST * changed + mint.UNEXPLAINED_PREMIUM
    admit iff cost < R and cost < mint.MDL_MARGIN * R

A failing atom is NOT admitted; the refusal is a kind="import_reject" record
on the import_queue stream (the stream that already logs import outcomes),
carrying the price and the bar. A ctx_min-minimised atom is priced on its
RETAINED cells only -- context_full never counts against it.

The falsifiers, as gated here:
  F1 (BOTH WAYS)  a constructed wide legacy atom (990-cell context, 26
                  changed -- the pi-replay median shape) is REFUSED admission
                  with its price recorded; its tight twin (changed + ring)
                  is admitted with context/transform byte-unchanged.
  F2              a ctx_min-minimised wide atom whose RETAINED cells are
                  tight is ADMITTED (the re-qualification path, SAME key as
                  its refused wide ancestor) -- priced on retained, never on
                  context_full; the re-inflated control refuses.
  F3 (THE DIAL)   EXTENT_RATE = 0 -> admission byte-identical to the
                  pre-gate door on a constructed batch (oracle reimplemented
                  here from the frozen pre-gate loop): every candidate
                  admits, zero refusal records.
  R4              constructed admission sequences reproduce the expected
                  admit/refuse decisions EXACTLY, in order.
  NO-SILENT-DROP  count(refusals) == count(import_reject records) on a
                  constructed batch; a re-run neither re-admits nor
                  re-appends (idempotent per candidate record, never per
                  key -- the key must stay free to re-qualify).

Seeded with a FIXED CONSTANT (the build date), never a clock.
"""
from __future__ import annotations

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer as C  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import mint as M  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402

SEED = 20260820  # fixed constant (the build date) -- deterministic forever
DC = E.DONT_CARE


# ── constructions ─────────────────────────────────────────────────────────────

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


def _wide_atom(key="eff-wide", seed=SEED):
    """The pi-replay median shape as a stored atom: a 30x33 = 990-cell context
    licensing 26 scattered changed cells (bbox pinned to the full patch by the
    corner cells). retained = 964; at the shipped rate cost = 27 + 0.05*964 =
    75.2, far over the 47.7 bar."""
    rng = np.random.default_rng(seed)
    h, w = 30, 33
    ctx = rng.integers(1, 9, size=(h, w)).astype(int)
    cells = [(0, 0), (h - 1, w - 1)]                  # pin the bbox to the patch
    while len(cells) < 26:
        r, c = int(rng.integers(0, h)), int(rng.integers(0, w))
        if (r, c) not in cells:
            cells.append((r, c))
    out = ctx.copy()
    for r, c in cells:
        out[r, c] = 0                                 # ctx is 1..8: always a change
    return _atom(ctx, out, key), cells


def _tight_atom(key="eff-tight", seed=SEED + 1):
    """The same 26-cell change, compact: a 2x13 changed block plus its one-cell
    ring -- a 4x15 context, retained 34; cost = 27 + 0.05*34 = 28.7 < 47.7."""
    rng = np.random.default_rng(seed)
    ctx = rng.integers(1, 9, size=(4, 15)).astype(int)
    out = ctx.copy()
    out[1:3, 1:14] = 0                                # 2 x 13 = 26 changed
    a = _atom(ctx, out, key)
    assert a["changed"] == 26, "construction: the twin must change 26 cells"
    return a


def _minimised_wide(key="eff-wide"):
    """The wide atom put through the REAL intersection machinery: one
    observation differing at every negotiable cell -> everything outside
    changed + ring becomes DONT_CARE; context_full preserves the 990-cell
    original (the undo)."""
    wide, cells = _wide_atom(key=key)
    ctx = np.asarray(wide["context"])
    changed = ctx != np.asarray(wide["transform"]["after"])
    keep = E._ring_of(changed)
    obs = ctx.copy()
    obs[~keep] = 0                                    # ctx is 1..8: differs everywhere
    m = E.minimise_atom(wide, obs)
    assert m is not None and (np.asarray(m["context"]) == DC).any(), (
        "construction: minimisation must have dropped cells")
    assert m["context_full"] == wide["context"], "the undo must hold the original"
    return m, wide


def _cand(fabric, atom, src_seq, game="g1", level=1, source_game="srcA"):
    """One import_candidates record, the shape _close_hit emits (the fields
    seed_imports reads: atom / source_game / source_seq / src_seq)."""
    return fabric.append("collective", C.CAND_TOPIC, {
        "game": str(game), "level": int(level), "src_seq": int(src_seq),
        "atom": dict(atom), "sigma": {}, "source_game": source_game,
        "source_seq": 7})


def _rejects(fabric):
    return [r for r in fabric.query("collective", C.QUEUE_TOPIC)
            if r.get("kind") == C.KIND_IMPORT_REJECT]


def _admitted_keys(fabric):
    return [r["atom"].get("key")
            for r in fabric.query("collective", C.ATOMS_TOPIC)]


def _price_by_hand(atom):
    """The inequality, recomputed here from the SAME constants the gate
    imports -- the arithmetic witness for the recorded price and bar."""
    changed = int((np.asarray(atom["context"])
                   != np.asarray(atom["transform"]["after"])).sum())
    cost = (E.encoding_cost_atom(atom)
            + M.EXTENT_RATE * E.context_retained_cells(atom))
    r_cost = M.RESIDUAL_CELL_COST * changed + M.UNEXPLAINED_PREMIUM
    return cost, M.MDL_MARGIN * r_cost, changed


# ── F1: both ways -- the wide legacy atom refused, the tight twin admitted ────

def test_f1_wide_refused_with_price_recorded_tight_twin_admitted(tmp_path):
    g, f = _box(tmp_path, "f1")
    wide, _cells = _wide_atom()
    tight = _tight_atom()
    _cand(f, wide, 1)
    _cand(f, tight, 2)
    n = C.seed_imports(g, f, "g1", 1)
    assert n == 1, "F1 FALSIFIED: exactly the tight twin should have entered"
    keys = _admitted_keys(f)
    assert tight["key"] in keys, "F1 FALSIFIED: the tight twin was refused"
    assert wide["key"] not in keys, (
        "F1 FALSIFIED: the 990-cell legacy atom entered local Gamma without "
        "meeting the bargain -- the door is still beside the wall")
    # the refusal is ON RECORD, with the price and the bar
    rej = _rejects(f)
    assert len(rej) == 1, "F1 FALSIFIED: the refusal left no import_reject record"
    rec = rej[0]
    cost, bar, changed = _price_by_hand(wide)
    assert rec["key"] == wide["key"] and rec["src_seq"] == 1
    assert rec["cost"] == cost and rec["bar"] == bar, (
        "F1 FALSIFIED: the recorded price/bar are not the mint's own arithmetic"
        " (got cost=%r bar=%r, expected %r/%r)"
        % (rec["cost"], rec["bar"], cost, bar))
    assert rec["changed"] == changed == 26
    assert rec["retained"] == E.context_retained_cells(wide) == 964
    assert rec["rate"] == M.EXTENT_RATE, "the rate must be the mint's, imported"
    assert rec["cost"] >= rec["bar"], "a refusal must show cost over the bar"
    # the admitted twin is UNCHANGED: context and transform byte-equal
    (adm,) = [r for r in f.query("collective", C.ATOMS_TOPIC)
              if r["atom"].get("key") == tight["key"]]
    assert adm["origin"] == E.ORIGIN_IMPORTED
    assert adm["atom"]["context"] == tight["context"], (
        "F1 FALSIFIED: admission modified the admitted atom's context")
    assert adm["atom"]["transform"] == tight["transform"]


# ── F2: the re-qualification path -- minimised, priced on RETAINED only ───────

def test_f2_minimised_wide_atom_requalifies_on_retained_cells(tmp_path):
    g, f = _box(tmp_path, "f2")
    minimised, wide = _minimised_wide()
    # the wide ancestor arrives first and is REFUSED (its record stands) ...
    _cand(f, wide, 1)
    assert C.seed_imports(g, f, "g1", 1) == 0
    assert len(_rejects(f)) == 1
    # ... then the SAME KEY arrives minimised (ctx_min shape: DONT_CARE cells,
    # context_full carrying the 990-cell original) as a NEW candidate
    _cand(f, minimised, 2)
    n = C.seed_imports(g, f, "g1", 1)
    assert n == 1, (
        "F2 FALSIFIED: the minimised atom was refused -- either the refusal "
        "poisoned the key or context_full was counted against it")
    assert minimised["key"] in _admitted_keys(f)
    assert len(_rejects(f)) == 1, "the ancestor's refusal is the only one"
    # priced on RETAINED, demonstrably: retained excludes every DONT_CARE cell
    price = C.admission_price(minimised)
    assert price is not None and price["admit"] is True
    assert price["retained"] == E.context_retained_cells(minimised) < 250, (
        "F2 FALSIFIED: retained must count only the cells the minimised "
        "context still insists on")
    # the CONTROL: the same atom re-inflated to its context_full REFUSES --
    # so it was the minimisation, not luck, that re-qualified it
    inflated = dict(minimised)
    full = [row[:] for row in minimised["context_full"]]
    inflated["context"] = full
    inflated["transform"] = {"before": full,
                             "after": wide["transform"]["after"]}
    control = C.admission_price(inflated)
    assert control is not None and control["admit"] is False, (
        "F2 FALSIFIED: the re-inflated control was admitted -- the gate is "
        "not pricing extent at all")


def test_f2_context_full_never_enters_the_price(tmp_path):
    minimised, _wide = _minimised_wide(key="eff-cfull")
    with_full = C.admission_price(minimised)
    shorn = dict(minimised)
    shorn.pop("context_full")
    without_full = C.admission_price(shorn)
    assert with_full == without_full, (
        "F2 FALSIFIED: the price moved when context_full was removed -- the "
        "undo is being billed")


# ── F3: the dial -- EXTENT_RATE = 0 is byte-identical to the pre-gate door ────

def _oracle_seed(gamma, fabric, game, level):
    """The PRE-GATE door, frozen: the exact seed_imports loop before the
    admission gate existed (already-have scan + enter everything else)."""
    have = set()
    for rec in C._local(gamma.fabric).query("collective", C.ATOMS_TOPIC):
        atom = rec.get("atom") or {}
        key = atom.get("key")
        if not key:
            continue
        if (atom.get("imported")
                or E.origin_of(rec) == E.ORIGIN_IMPORTED):
            have.add(key)
    count = 0
    entered = []
    for cand in C.candidates(fabric, game, level):
        atom = dict(cand.get("atom") or {})
        key = atom.get("key")
        if not atom or (key and key in have):
            continue
        atom["imported"] = True
        src_game = cand.get("source_game")
        if src_game is not None and "source_game" not in atom:
            atom["source_game"] = src_game
        entered.append(atom)
        if key:
            have.add(key)
        count += 1
    return count, entered


def _f3_batch(fabric):
    """A batch spanning the shapes: wide (the premium's target), tight,
    1-cell, minimised, and an extent-less lexical atom."""
    wide, _ = _wide_atom(key="eff-f3-wide")
    tight = _tight_atom(key="eff-f3-tight")
    one = _atom([[2]], [[5]], "eff-f3-one")
    minimised, _ = _minimised_wide(key="eff-f3-min")
    lexical = {"kind": "INERT", "arity": 2, "key": "lex-f3", "action": 6,
               "changed": 0}
    batch = [wide, tight, one, minimised, lexical]
    for i, atom in enumerate(batch):
        _cand(fabric, atom, i + 1)
    return batch


def test_f3_rate_zero_admission_is_byte_identical_to_the_pre_gate_door(
        tmp_path, monkeypatch):
    monkeypatch.setattr(M, "EXTENT_RATE", 0.0)
    g, f = _box(tmp_path, "f3z")
    batch = _f3_batch(f)
    go, fo = _box(tmp_path, "f3oracle")
    for i, atom in enumerate(batch):
        _cand(fo, atom, i + 1)
    n_oracle, entered = _oracle_seed(go, fo, "g1", 1)
    n = C.seed_imports(g, f, "g1", 1)
    assert n == n_oracle == len(batch), (
        "F3 FALSIFIED: at EXTENT_RATE=0 a currently-admitted atom no longer "
        "admits (%d vs oracle %d)" % (n, n_oracle))
    assert _rejects(f) == [], (
        "F3 FALSIFIED: refusal records appeared with the dial at zero")
    got = [r["atom"] for r in f.query("collective", C.ATOMS_TOPIC)]
    assert got == entered, (
        "F3 FALSIFIED: the entered atom payloads diverged from the pre-gate "
        "door's -- admission at rate 0 must be byte-identical")


def test_f3_the_shipped_rate_is_on(tmp_path):
    assert M.EXTENT_RATE > 0.0, "the dial ships OFF -- the door is open again"
    wide, _ = _wide_atom()
    price = C.admission_price(wide)
    assert price is not None and price["admit"] is False
    assert C.admission_price(_tight_atom())["admit"] is True


# ── R4: constructed sequences reproduce the decisions EXACTLY ─────────────────

def _retained_exactly(k, key, seed=SEED + 4):
    """A 30x33 atom with changed pinned to the bbox corners plus 24 scattered
    cells, and EXACTLY k retained unchanged cells (everything else DONT_CARE
    in context AND after together -- the ctx_min shape)."""
    wide, cells = _wide_atom(key=key, seed=seed)
    ctx = np.asarray(wide["context"])
    out = np.asarray(wide["transform"]["after"])
    changed = ctx != out
    unchanged = np.argwhere(~changed)
    assert len(unchanged) >= k, "construction: not enough unchanged cells"
    drop = unchanged[k:]                              # keep the first k retained
    for r, c in drop:
        ctx[r, c] = DC
        out[r, c] = DC
    a = _atom(ctx, out, key)
    assert E.context_retained_cells(a) == k, "construction: retained != k"
    assert a["changed"] == 26
    return a


def test_r4_admission_sequences_reproduce_expected_decisions_exactly(tmp_path):
    g, f = _box(tmp_path, "r4")
    # rejection onset at changed=26: cost = 27 + 0.05*k vs bar 47.7 -- clear
    # of the float boundary on both sides (k=400 -> 47.0; k=440 -> 49.0)
    seq = [
        (_wide_atom(key="r4-wide")[0], False),
        (_tight_atom(key="r4-tight"), True),
        (_atom([[2]], [[5]], "r4-one"), True),        # 1-cell recolour: 2 < 2.7
        (_retained_exactly(400, "r4-under"), True),   # just under the onset
        (_retained_exactly(440, "r4-over"), False),   # just over the onset
        (_minimised_wide(key="r4-min")[0], True),     # the re-qualified shape
    ]
    for i, (atom, _want) in enumerate(seq):
        _cand(f, atom, i + 1)
    n = C.seed_imports(g, f, "g1", 1)
    admitted = set(_admitted_keys(f))
    refused = {r["key"] for r in _rejects(f)}
    for atom, want in seq:
        if want:
            assert atom["key"] in admitted and atom["key"] not in refused, (
                "R4 FALSIFIED: %s expected ADMIT, got refuse" % atom["key"])
        else:
            assert atom["key"] in refused and atom["key"] not in admitted, (
                "R4 FALSIFIED: %s expected REFUSE, got admit" % atom["key"])
    assert n == sum(1 for _, want in seq if want)
    # and every decision matches the hand arithmetic, not just the labels
    for atom, want in seq:
        cost, bar, _ = _price_by_hand(atom)
        assert (cost < bar) is want, (
            "R4 FALSIFIED: the hand inequality disagrees with the expected "
            "decision for %s (cost=%r bar=%r)" % (atom["key"], cost, bar))


# ── NO-SILENT-DROP: every refusal has its record; re-runs stay idempotent ─────

def test_no_silent_drop_refusal_count_equals_record_count(tmp_path):
    g, f = _box(tmp_path, "drop")
    wides = [_wide_atom(key="drop-w%d" % i, seed=SEED + 10 + i)[0]
             for i in range(5)]
    tights = [_tight_atom(key="drop-t%d" % i, seed=SEED + 20 + i)
              for i in range(3)]
    for i, atom in enumerate(wides + tights):
        _cand(f, atom, i + 1)
    n = C.seed_imports(g, f, "g1", 1)
    assert n == 3
    rej = _rejects(f)
    assert len(rej) == 5, (
        "NO-SILENT-DROP FALSIFIED: %d refusals but %d import_reject records"
        % (5, len(rej)))
    assert {r["key"] for r in rej} == {w["key"] for w in wides}
    for r in rej:
        for field in ("cost", "bar", "changed", "retained", "rate",
                      "src_seq", "cand_seq", "game", "level"):
            assert field in r, "a refusal record without its %r is silence" % field
    # the RE-RUN: nothing re-admits, nothing re-appends -- but nothing was
    # dropped either (the standing records ARE the refusals)
    n2 = C.seed_imports(g, f, "g1", 1)
    assert n2 == 0
    assert len(_rejects(f)) == 5, (
        "a re-run re-priced already-refused candidate records (spam) or "
        "erased standing refusals")
    assert len(f.query("collective", C.ATOMS_TOPIC)) == 3


# ── the gate's edges: unpriceable atoms pass the door exactly as before ───────

def test_unpriceable_atoms_are_not_this_gates_business(tmp_path):
    assert C.admission_price(None) is None
    assert C.admission_price({}) is None
    assert C.admission_price({"kind": "INERT", "key": "x", "changed": 0}) is None
    same = [[1, 2], [3, 4]]
    assert C.admission_price(
        {"key": "nc", "context": same,
         "transform": {"before": same, "after": same}}) is None, (
        "a changed-free atom carries no residual for the bargain to price")
    g, f = _box(tmp_path, "edges")
    lexical = {"kind": "INERT", "arity": 2, "key": "lex-1", "action": 6,
               "changed": 0}
    _cand(f, lexical, 1)
    assert C.seed_imports(g, f, "g1", 1) == 1, (
        "an extent-less atom must pass the door exactly as it always did")
    assert _rejects(f) == []
