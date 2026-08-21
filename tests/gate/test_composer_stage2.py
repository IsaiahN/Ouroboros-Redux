"""COMPOSER STAGE 2 -- THE ENABLES INDICES (PREREG_COMPOSER_STAGE2_ENABLES.md;
PROPOSAL_COMPOSER_DESIGN.md par.2-3).

The build under test (engines/egocentric/enables.py + the mint's stamp):
  (1) enables_edges -- the within-Gamma ENABLES edge: A -> B iff A's psig
      `written` colours intersect B's required palette AND B's requirement
      is not satisfiable in the current frame without A (missing_B =
      required_B - frame_palette; edge iff missing_B nonempty and it
      intersects written_A). Stored signatures only; pure python; doubt
      produces ABSENCE (NO-REQUIREMENT / NO-CLAIM), never a false edge.
  (2) act_offset -- stamped by mint.consider beside psig when the minting
      action carried coordinates (act=(row, col), passed from the loop's
      offer sites); the anchor origin is the changed-cell bbox origin
      (learn_effect's crop). NO content backfill exists -- the click cell
      is no function of the atom's patches -- so act_offset_of serves the
      stored stamp or None, and absence is permanent, stated, never
      approximated. The offset survives minimisation's supersede.
  (3) cross_shelf_reach -- cheapest BODY chain landing the act cell
      (anchor + act_offset) on a matching anchor: BFS shortest path over
      per-action (dr, dc) deltas, masked by the frontier book's fatal
      cells ((x, y) -> (row, col) via fatal_cells, the one conversion
      point). Returns chain + cost or None, every chain verified=False.

The falsifiers, as gated here:
  F1  translation exact: constructed atom + avatar + anchors -> the chain,
      applied as deltas, lands the act-cell EXACTLY on anchor+offset;
      off-by-one in either axis fails the equality.
  F2  mask honesty: an anchor whose only path crosses a frontier-book
      fatal cell yields None; clearing the mark yields the chain -- run
      through fatal_cells' own (x, y) -> (row, col) conversion.
  F3  the algebra proposes, simulation decides: the returned chain is
      marked verified=False; a constructed world where a wall (unknown to
      the mask) blocks the delta-sum path shows the proposal made and the
      simulation rejecting it -- the cheap shelf never returns a
      verified-looking wrong chain.
  F4  the within-Gamma edge prunes and never lies: a requirement A cannot
      manufacture is absent from A's edge list; one A does manufacture is
      present; an underivable pair produces NO EDGE (both directions).
  R4  constructed graphs reproduce expected edge sets and cheapest chains
      exactly (exact adjacency dicts; nearer-anchor tie broken by cost).
  KNOWN-NEGATIVE: an empty Gamma yields an empty graph, not an exception;
      an offset-less atom yields None from the reach, never a guess.

Seeded with a FIXED CONSTANT (the build date), never a clock.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import action_book as AB  # noqa: E402
from engines.egocentric import applicability as A  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import enables as EN  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402

SEED = 20260821  # fixed constant (the build date) -- deterministic forever

# Constructed test deltas (the reach is source-agnostic; the stated live
# sources are book_deltas -- primary -- and the bank's established BODY
# deltas as fallback): 1 up, 2 down, 3 left, 4 right, in (dr, dc).
DELTAS4 = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


# ── constructions ─────────────────────────────────────────────────────────────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


def _atom(ctx, out, key, action=6):
    ctx_l = [[int(v) for v in row] for row in ctx]
    out_l = [[int(v) for v in row] for row in out]
    return {"kind": "EFFECT", "arity": 2, "key": key, "action": action,
            "context": ctx_l,
            "transform": {"before": ctx_l, "after": out_l},
            "changed": int((np.asarray(ctx) != np.asarray(out)).sum())}


def _writer(colour, key, requires=1):
    """A 1-cell EFFECT requiring `requires` and writing `colour`."""
    return _atom([[requires]], [[colour]], key)


def _offset_atom(dr, dc, key="click"):
    """A minimal atom carrying a valid stored act_offset (dr, dc)."""
    atom = _writer(4, key)
    atom[EN.ACT_OFFSET_FIELD] = {"v": EN.ACT_OFFSET_VERSION,
                                 "dr": int(dr), "dc": int(dc)}
    return atom


def _fsig(colours):
    """A frame-signature dict as applicability.frame_signature returns it."""
    return {"h": 9, "w": 9, "pal": set(colours)}


def _apply_chain(start, chain, deltas):
    r, c = start
    for action in chain:
        dr, dc = deltas[action]
        r, c = r + dr, c + dc
    return (r, c)


# ── F4 + R4: the within-Gamma edge never lies ─────────────────────────────────

def test_f4_within_edge_present_absent_and_underivable_pairs():
    a_yes = _writer(5, "eff-writes5")           # manufactures B's missing 5
    a_no = _writer(3, "eff-writes3")            # writes 3: cannot manufacture 5
    b = _atom([[5]], [[7]], "eff-needs5")       # requires colour 5
    atoms = {"A": a_yes, "A2": a_no, "B": b}
    edges = EN.enables_edges(["A", "A2", "B"], atoms, _fsig({1}))
    assert "B" in edges.get("A", []), (
        "F4 FALSIFIED: A writes 5, the frame lacks 5, B requires 5 -- the "
        "edge A->B must exist")
    assert "B" not in edges.get("A2", []), (
        "F4 FALSIFIED: A2 cannot manufacture B's requirement -- the edge lies")
    # satisfiable WITHOUT A: the frame already holds 5 -> no edge at all
    assert EN.enables_edges(["A", "B"], atoms, _fsig({1, 5})) == {}, (
        "F4 FALSIFIED: B's requirement is satisfiable in the current frame "
        "without A -- an edge here is a false promise of necessity")
    # underivable pairs produce NO EDGE, never a false one (both directions)
    junk = {"kind": "MYSTERY", "blob": object()}
    edges = EN.enables_edges(["A", "J"], {"A": a_yes, "J": junk}, _fsig({1}))
    assert edges == {}, (
        "F4 FALSIFIED: an underivable atom reads NO-REQUIREMENT (nothing "
        "missing) and NO-CLAIM (writes nothing) -- it must join NO edge")
    edges = EN.enables_edges(["J", "B"], {"J": junk, "B": b}, _fsig({1}))
    assert edges == {}, (
        "F4 FALSIFIED: an atom whose postcondition is unreadable claims to "
        "write NOTHING -- no out-edge may be built on it")
    # no self-edges: an atom whose writes cover its own requirement (a swap
    # writes both colours it requires) still never "enables" itself
    cyc = _atom([[5, 1]], [[1, 5]], "eff-cyc")
    edges = EN.enables_edges(["C"], {"C": cyc}, _fsig(set()))
    assert edges == {}, "a lone atom must never hold a self-edge"


def test_r4_exact_edge_set_on_constructed_graph():
    """Four atoms, one frame, ONE exact expected adjacency dict."""
    a = _writer(5, "eff-a")                       # writes 5
    b = _atom([[5]], [[6]], "eff-b")              # requires 5, writes 6
    c = _atom([[6]], [[7]], "eff-c")              # requires 6, writes 7
    d = _atom([[1]], [[2]], "eff-d")              # requires 1 (frame has it)
    atoms = {"a": a, "b": b, "c": c, "d": d}
    edges = EN.enables_edges(["a", "b", "c", "d"], atoms, _fsig({1}))
    assert edges == {"a": ["b"], "b": ["c"]}, (
        "R4 FALSIFIED: expected exactly a->b (5 missing, a writes it) and "
        "b->c (6 missing, b writes it); d is frame-satisfied and c's 7 "
        "feeds nobody\ngot=%r" % (edges,))
    # fsig=None degrades to the empty frame palette: d's requirement (1) now
    # counts as missing and a->b, b->c stand unchanged; nobody writes 1.
    edges = EN.enables_edges(["a", "b", "c", "d"], atoms, None)
    assert edges == {"a": ["b"], "b": ["c"]}, (
        "R4 FALSIFIED: the fsig=None degrade (empty frame palette) moved "
        "edges it must not\ngot=%r" % (edges,))


def test_known_negative_empty_gamma_yields_empty_graph():
    assert EN.enables_edges([], {}, _fsig({1, 2})) == {}
    assert EN.enables_edges([], {}, None) == {}


def test_within_edge_path_is_pure_python_no_numpy():
    """The applicability F4 discipline carried over: the per-edge path is
    set/int arithmetic -- numpy appears NOWHERE in the module (the frame
    read stays in applicability.frame_signature)."""
    src = open(EN.__file__, encoding="utf-8").read()
    assert "import numpy" not in src and "np." not in src, (
        "enables.py grew a numpy dependency -- the per-edge path's "
        "pure-python claim is dead")


# ── act_offset: the mint stamp + the honest read side ─────────────────────────

def _recolour_frames(v0=3, v1=4):
    b = np.zeros((5, 5), dtype=int)
    b[2, 2] = v0
    a = b.copy()
    a[2, 2] = v1
    return b, a


def test_act_offset_stamped_at_the_mint_write_site(tmp_path):
    """consider(..., act=(row, col)) stamps act_offset = act - bbox origin
    beside psig; no act -> no field; a malformed act stamps nothing and
    never moves the verdict."""
    g = _gamma(tmp_path, "stamp")
    mint = MDLMint(g)
    b, a = _recolour_frames()                     # changed-cell bbox origin (2, 2)
    r1 = mint.consider(b, 6, a, game="g1", level=1, act=(1, 1))
    assert r1["verdict"] == "mint", "construction: the event must mint"
    atom = g.get(r1["id"])
    assert atom[EN.ACT_OFFSET_FIELD] == {"v": EN.ACT_OFFSET_VERSION,
                                         "dr": -1, "dc": -1}, (
        "STAMP FALSIFIED: act (1,1) minus bbox origin (2,2) is (-1,-1); "
        "stored %r" % (atom.get(EN.ACT_OFFSET_FIELD),))
    assert EN.act_offset_of(atom) == (-1, -1)
    assert atom[A.PSIG_FIELD] == A.postcondition_signature(atom), (
        "the offset stamp must ride BESIDE psig, not displace it")
    # no coordinates -> no field, and the read side states the absence
    g2 = _gamma(tmp_path, "nostamp")
    b2, a2 = _recolour_frames(2, 6)
    r2 = MDLMint(g2).consider(b2, 6, a2, game="g2", level=1)
    assert r2["verdict"] == "mint"
    atom2 = g2.get(r2["id"])
    assert EN.ACT_OFFSET_FIELD not in atom2, (
        "an actless mint must stamp NOTHING -- absent, not approximated")
    assert EN.act_offset_of(atom2) is None
    # malformed capture: verdict untouched, nothing stamped
    g3 = _gamma(tmp_path, "badact")
    b3, a3 = _recolour_frames(5, 7)
    r3 = MDLMint(g3).consider(b3, 6, a3, game="g3", level=1, act=("x", None))
    assert r3["verdict"] == "mint", "a malformed act must never move a verdict"
    assert EN.ACT_OFFSET_FIELD not in g3.get(r3["id"])


def test_act_offset_read_side_never_guesses():
    base = _writer(4, "eff-x")
    assert EN.act_offset_of(base) is None, "no field: stated absence"
    assert EN.act_offset_of(None) is None
    stale = dict(base)
    stale[EN.ACT_OFFSET_FIELD] = {"v": 999, "dr": 1, "dc": 1}
    assert EN.act_offset_of(stale) is None, (
        "a malformed stored offset must read ABSENT -- there is no content "
        "derivation to fall back on, and a guess would be a false geometry")
    bad = dict(base)
    bad[EN.ACT_OFFSET_FIELD] = {"v": EN.ACT_OFFSET_VERSION,
                                "dr": "1", "dc": 0}
    assert EN.act_offset_of(bad) is None
    good = dict(base)
    good[EN.ACT_OFFSET_FIELD] = {"v": EN.ACT_OFFSET_VERSION, "dr": -2, "dc": 3}
    assert EN.act_offset_of(good) == (-2, 3)


def test_act_offset_survives_the_minimisation_supersede(tmp_path):
    """The ctx_min superseding append carries the offset forward: both
    minimisation and reinstatement preserve the patch bbox, and the offset
    is anchor-relative -- so no restamp, no loss."""
    rng = np.random.default_rng(SEED)
    b1 = rng.integers(1, 8, size=(9, 9)).astype(int)
    b1[1, 1], b1[5, 5], b1[1, 5] = 2, 3, 8        # change sites + distant X
    a1 = b1.copy()
    a1[1, 1] = 0
    a1[5, 5] = 0
    g = _gamma(tmp_path, "minsurv")
    mint = MDLMint(g)
    r1 = mint.consider(b1, 6, a1, game="g1", level=1, act=(2, 3))
    assert r1["verdict"] == "mint", "construction: the event must mint"
    stamped = g.get(r1["id"])[EN.ACT_OFFSET_FIELD]
    assert stamped == {"v": EN.ACT_OFFSET_VERSION, "dr": 1, "dc": 2}, (
        "construction: bbox origin (1,1), act (2,3) -> offset (1,2)")
    b2 = b1.copy()
    b2[1, 5] = 7                                  # different debris at X
    a2 = b2.copy()
    a2[1, 1] = 0
    a2[5, 5] = 0
    mint.consider(b2, 6, a2, game="g1", level=1, act=(2, 3))
    rec = g.fabric.query("collective", g.TOPIC,
                         where=lambda r: r.get("id") == r1["id"])[-1]
    assert rec.get("ctx_min") is True, "construction: the merge must fire"
    assert rec["atom"].get(EN.ACT_OFFSET_FIELD) == stamped, (
        "SUPERSEDE FALSIFIED: minimisation dropped or moved act_offset -- "
        "the anchor-relative offset must survive the ctx_min append")


# ── F1: the translation is exact ──────────────────────────────────────────────

def test_f1_translation_exact():
    atom = _offset_atom(2, 1)                     # act cell = anchor + (2, 1)
    res = EN.cross_shelf_reach(atom, [(3, 3)], (0, 0), DELTAS4, (8, 8))
    assert res is not None, "F1 FALSIFIED: a free 8x8 grid must be reachable"
    landed = _apply_chain((0, 0), res["chain"], DELTAS4)
    assert landed == (3 + 2, 3 + 1) == res["target"], (
        "F1 FALSIFIED: the chain applied as deltas lands on %r, the act "
        "cell (anchor+offset) is %r -- off by %r"
        % (landed, (5, 4), (landed[0] - 5, landed[1] - 4)))
    assert res["anchor"] == (3, 3)
    assert res["cost"] == len(res["chain"]) == 9, (
        "F1 FALSIFIED: with unit 4-dir deltas the cheapest chain is the "
        "Manhattan distance |5|+|4| = 9, got %r" % (res["cost"],))
    # the identity case: already standing on the act cell -> empty chain
    res0 = EN.cross_shelf_reach(atom, [(3, 3)], (5, 4), DELTAS4, (8, 8))
    assert res0 is not None and res0["chain"] == [] and res0["cost"] == 0


# ── F2: the mask is honest ────────────────────────────────────────────────────

class _StubBook:
    """avoid_set in the frontier book's own click convention: (x, y)."""

    def __init__(self, cells):
        self._cells = set(cells)

    def avoid_set(self, game, level):
        return set(self._cells)


def test_f2_mask_honesty_fatal_blocks_cleared_passes():
    atom = _offset_atom(0, 0)
    corridor = (1, 5)                             # one row: only 3/4 move
    lr = {3: (0, -1), 4: (0, 1)}
    # the frontier book banks the fatal cell as (x, y) = (2, 0): column 2,
    # row 0 -- fatal_cells is the one conversion point to (row, col)
    fatal = EN.fatal_cells(_StubBook({(2, 0)}), "g1", 1)
    assert fatal == {(0, 2)}, (
        "the (x, y) -> (row, col) conversion is wrong -- every mask "
        "downstream would be transposed")
    blocked = EN.cross_shelf_reach(atom, [(0, 4)], (0, 0), lr, corridor,
                                   fatal=fatal)
    assert blocked is None, (
        "F2 FALSIFIED: the only path crosses a banked fatal cell and the "
        "reach returned a chain anyway -- the mask was not consulted")
    cleared = EN.cross_shelf_reach(atom, [(0, 4)], (0, 0), lr, corridor,
                                   fatal=set())
    assert cleared is not None and cleared["chain"] == [4, 4, 4, 4], (
        "F2 FALSIFIED (known-negative): clearing the mark must yield the "
        "chain, got %r" % (cleared,))
    # a fatal TARGET is unreachable too (the act cell itself is masked)
    assert EN.cross_shelf_reach(atom, [(0, 4)], (0, 0), lr, corridor,
                                fatal={(0, 4)}) is None
    # a fatal START is a contradiction, not a path
    assert EN.cross_shelf_reach(atom, [(0, 4)], (0, 0), lr, corridor,
                                fatal={(0, 0)}) is None


# ── F3: the algebra proposes, the simulation decides ──────────────────────────

def _world_step(cell, action, walls, shape):
    """The constructed world's OWN rule: a wall blocks -- the mover stays."""
    dr, dc = DELTAS4[action]
    nxt = (cell[0] + dr, cell[1] + dc)
    if nxt in walls or not (0 <= nxt[0] < shape[0] and 0 <= nxt[1] < shape[1]):
        return cell
    return nxt


def test_f3_chain_marked_unverified_and_simulation_rejects():
    atom = _offset_atom(0, 0)
    shape = (1, 4)
    lr = {3: (0, -1), 4: (0, 1)}
    walls = {(0, 1)}                              # the world knows; the mask does NOT
    res = EN.cross_shelf_reach(atom, [(0, 3)], (0, 0), lr, shape, fatal=set())
    assert res is not None and res["chain"] == [4, 4, 4], (
        "construction: the algebra must PROPOSE the straight chain -- the "
        "wall is not in the fatal mask (the agent has not died on it)")
    assert res["verified"] is False, (
        "F3 FALSIFIED: the returned chain claims verification -- the cheap "
        "shelf must never return a verified-looking chain; the flag IS the "
        "contract (the algebra proposes, simulation decides)")
    cell = (0, 0)
    for action in res["chain"]:
        cell = _world_step(cell, action, walls, shape)
    assert cell != res["target"], (
        "construction drifted: the wall must actually block the proposal")
    # and the flag is structural: nothing in the module can set it True
    src = open(EN.__file__, encoding="utf-8").read()
    assert '"verified": False' in src and '"verified": True' not in src, (
        "F3 FALSIFIED: enables.py holds a path that emits verified=True")


# ── R4 + known-negatives on the reach ─────────────────────────────────────────

def test_r4_cheapest_chain_exact_on_constructed_graphs():
    atom = _offset_atom(0, 0)
    # two anchors: (0, 4) costs 4, (2, 1) costs 3 -- the cheaper wins
    res = EN.cross_shelf_reach(atom, [(0, 4), (2, 1)], (0, 0), DELTAS4, (5, 5))
    assert res is not None and res["cost"] == 3 and res["anchor"] == (2, 1), (
        "R4 FALSIFIED: cheapest chain is 3 steps to anchor (2,1), got %r"
        % (res,))
    assert _apply_chain((0, 0), res["chain"], DELTAS4) == (2, 1)
    # a nonzero offset shifts the TARGET, not the anchor
    off = _offset_atom(-1, 0)
    res = EN.cross_shelf_reach(off, [(2, 1)], (0, 0), DELTAS4, (5, 5))
    assert res is not None and res["target"] == (1, 1) and res["cost"] == 2
    # cells trace: start + every visited cell, chain-consistent
    assert res["cells"][0] == (0, 0) and res["cells"][-1] == (1, 1)
    assert len(res["cells"]) == res["cost"] + 1


def test_known_negative_reach_never_guesses():
    plain = _writer(4, "eff-noff")                # NO act_offset field
    assert EN.cross_shelf_reach(plain, [(1, 1)], (0, 0), DELTAS4, (5, 5)) is None, (
        "an offset-less atom has no cross-shelf translation -- None, never "
        "an approximation (the prereg's blocked-not-guessed clause)")
    atom = _offset_atom(0, 0)
    # every target out of bounds -> None
    assert EN.cross_shelf_reach(atom, [(9, 9)], (0, 0), DELTAS4, (3, 3)) is None
    # no anchors -> None
    assert EN.cross_shelf_reach(atom, [], (0, 0), DELTAS4, (3, 3)) is None
    # avatar out of bounds -> None
    assert EN.cross_shelf_reach(atom, [(1, 1)], (7, 7), DELTAS4, (3, 3)) is None
    # no deltas -> unreachable (unless already standing on the act cell)
    assert EN.cross_shelf_reach(atom, [(1, 1)], (0, 0), {}, (3, 3)) is None


# ── the stated delta source: the action book ──────────────────────────────────

def test_book_deltas_reads_the_action_book_verbatim(tmp_path):
    """The reach's primary delta source, stated: each action's highest-
    evidence TRANSLATE entry, (dx, dy) taken as (dr, dc) VERBATIM (effects
    applies TRANSLATE as tr, tc = r + dx, c + dy). Absence stays absent --
    an action without translate evidence gets NO guessed delta."""
    game_dir = tmp_path / "box"
    book = {"artifact": AB.ARTIFACT, "v": AB.BOOK_VERSION, "box": "box",
            "game_ids": ["gd77"],
            "actions": {
                "1": {"atoms": {"n": 9,
                                "translate": [{"dx": -1, "dy": 0, "n": 7},
                                              {"dx": 1, "dy": 0, "n": 2}]}},
                "2": {"atoms": {"n": 3, "translate": None,
                                "translate_absent": "no translate atoms"}},
            }}
    path = AB.book_path(str(game_dir))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(book, fh)
    assert AB.load_action_book(str(game_dir)) is not None, "construction"
    got = EN.book_deltas("gd77")
    assert got == {1: (-1, 0)}, (
        "book_deltas must take action 1's dominant translate verbatim and "
        "leave action 2 ABSENT (no guessed delta); got %r" % (got,))
    assert EN.book_deltas("never-loaded-game") == {}, (
        "an unloaded book is not evidence of anything -- empty, not invented")
