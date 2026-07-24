"""Brick 2 of the reasoning scaffold: a FRAME-NATIVE referent/legend detector -- it NAMES where the reference that
specifies the goal plausibly is (a bordered panel, an edge legend of distinct tokens, a matched endpoint pair), purely
from structure, so Brick 3 can hypothesise a win relation over it. Precision-first: a plain board yields nothing. Names
no game, encodes no answer, steers no action."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.referent import find_referents, Referent
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard


# ---- each detector kind on a synthetic board -------------------------------------------------------------------
def test_detects_bordered_panel():
    """A rectangular ring of colour 2 enclosing an interior with content -> a 'panel' referent naming the interior."""
    g = np.zeros((12, 12), dtype=int)
    g[2:8, 2:9] = 0
    g[2, 2:9] = g[7, 2:9] = 2                                  # top/bottom border
    g[2:8, 2] = g[2:8, 8] = 2                                 # left/right border
    g[4, 5] = 3; g[5, 6] = 4                                  # interior content
    refs = [r for r in find_referents(g) if r.kind == "panel"]
    assert len(refs) == 1
    r = refs[0]
    assert r.colour == 2
    assert r.bbox == (3, 3, 6, 7)                             # the interior, border stripped
    assert set(r.detail["interior_colours"]) == {3, 4}


def test_detects_block_panel_thick_frame():
    """A dense multi-colour rectangular block with a THICK/two-colour frame (colours that also recur elsewhere) is a
    reference panel even though no single-colour ring test would fire -- the real shape of edit-to-match references."""
    g = np.zeros((20, 20), dtype=int)
    blk = np.full((10, 10), 4, dtype=int)                     # a solid colour-4 field...
    blk[0, :] = blk[-1, :] = 2                                # ...top/bottom frame colour 2...
    blk[:, 0] = blk[:, -1] = 8                                # ...left/right frame colour 8 (a MIXED, thick frame)...
    blk[3:5, 3:5] = 9; blk[6:8, 6:8] = 2                     # ...with structured colour-9 / colour-2 content inside
    g[5:15, 5:15] = blk
    g[1, 1] = 4; g[18, 2] = 2                                # frame colours recur elsewhere (defeats global-bbox ring)
    panels = [r for r in find_referents(g) if r.kind == "panel"]
    assert len(panels) == 1
    p = panels[0]
    assert p.bbox == (5, 5, 14, 14)                           # the whole structured block
    assert p.detail["via"] == "block"
    assert set(p.detail["colours"]) == {2, 4, 8, 9}


def test_detects_legend_strip():
    """A thin top band of >=3 distinct tokens, separated from the interior by a bg gap row -> a 'legend' referent."""
    g = np.zeros((14, 10), dtype=int)
    g[0, 1] = 3; g[0, 3] = 4; g[0, 5] = 5; g[0, 7] = 6        # top row: four distinct tokens
    # row 1 is all-bg (the separator gap); interior below has unrelated content
    g[6, 4] = 7; g[9, 2] = 8
    refs = [r for r in find_referents(g) if r.kind == "legend"]
    assert len(refs) == 1
    assert set(refs[0].detail["tokens"]) == {3, 4, 5, 6}
    assert refs[0].bbox[0] == 0                               # anchored at the top edge


def test_detects_endpoint_pairs():
    """A colour present as exactly two small, similar-sized components -> a matched 'endpoints' referent."""
    g = np.zeros((14, 14), dtype=int)
    g[2, 2] = 5; g[2, 3] = 5                                  # endpoint A (2 cells)
    g[11, 11] = 5; g[11, 12] = 5                              # endpoint B (2 cells), same colour, far apart
    g[6, 6] = 1                                               # unrelated single cell of another colour
    refs = [r for r in find_referents(g) if r.kind == "endpoints"]
    assert len(refs) == 1
    assert refs[0].colour == 5
    assert refs[0].detail["sizes"] == [2, 2]


# ---- precision: no structure -> no referent --------------------------------------------------------------------
def test_plain_board_yields_no_referent():
    """A structureless board (a few scattered cells, no ring / no edge legend / no matched pair) yields nothing."""
    g = np.zeros((12, 12), dtype=int)
    g[5, 5] = 3                                              # a lone cell: not a panel, legend, or matched pair
    g[8, 2] = 4
    assert find_referents(g) == []


def test_solid_and_striped_boards_yield_no_panel():
    """A solid fill and a simple stripe pattern must not be mistaken for a bordered panel (no enclosed interior)."""
    assert find_referents(np.full((10, 10), 3, dtype=int)) == []
    striped = np.zeros((10, 10), dtype=int); striped[::2, :] = 6       # horizontal stripes: no ring
    assert not [r for r in find_referents(striped) if r.kind == "panel"]


def test_clustered_node_pair_detected():
    """A colour whose FRAGMENTS form two well-separated groups (a fragmented / unequal connect-node pair the exact-2
    detector misses) registers as an endpoints referent via clustering."""
    g = np.zeros((24, 24), dtype=int)
    g[2, 2] = 5; g[2, 3] = 5; g[3, 2] = 5                    # node A: a 3-cell blob (top-left)...
    g[4, 5] = 5; g[4, 6] = 5                                 # ...plus a 2-cell fragment nearby (same cluster)
    g[20, 20] = 5; g[20, 21] = 5; g[21, 20] = 5             # node B: a blob (bottom-right)...
    g[18, 18] = 5; g[18, 19] = 5                             # ...plus a fragment nearby
    refs = [r for r in find_referents(g) if r.kind == "endpoints"]
    assert len(refs) == 1
    assert refs[0].colour == 5 and refs[0].detail.get("clustered") is True
    (ar, ac), (br, bc) = refs[0].detail["centroids"]
    assert (ar < 12) != (br < 12)                            # the two group centroids are on opposite ends


def test_bunched_fragments_are_not_a_node_pair():
    """Several fragments bunched in ONE region do not separate into two distant nodes -> no clustered pair (precision)."""
    g = np.zeros((24, 24), dtype=int)
    g[2, 2] = 5; g[2, 3] = 5                                 # three small fragments, all within a tight top-left box
    g[2, 6] = 5; g[3, 6] = 5
    g[5, 3] = 5; g[5, 4] = 5
    assert not [r for r in find_referents(g) if r.kind == "endpoints"]


def test_exact_small_pair_not_double_emitted():
    """A colour that is an exact 2-small-component pair is emitted once (by the exact detector), not also re-clustered."""
    g = np.zeros((16, 16), dtype=int)
    g[2, 2] = 5; g[2, 3] = 5
    g[12, 12] = 5; g[12, 13] = 5
    eps = [r for r in find_referents(g) if r.kind == "endpoints"]
    assert len(eps) == 1


def test_three_components_is_not_endpoints():
    """Three components of one colour is not a matched PAIR -> no endpoints referent (precision)."""
    g = np.zeros((14, 14), dtype=int)
    g[2, 2] = 5; g[7, 7] = 5; g[11, 11] = 5                  # three separate markers, not a pair
    assert not [r for r in find_referents(g) if r.kind == "endpoints"]


# ---- policy integration: referents are stored + exposed, and steer nothing -------------------------------------
def test_policy_stores_and_exposes_referents():
    """The policy computes referents each observe and exposes them via referents(); on a panel board it finds one, on
    a plain board none. It must not crash and must not change the chosen-action contract (accessor only)."""
    pol = ReduxPolicy(game_id="ref-x", blackboard=Blackboard(), warmup_cap=2)
    g = np.zeros((12, 12), dtype=int)
    g[2, 2:9] = 2; g[7, 2:9] = 2; g[2:8, 2] = 2; g[2:8, 8] = 2
    g[4, 5] = 3; g[5, 6] = 4
    pol.observe(g, [1, 2, 3, 4, 5])
    kinds = {r.kind for r in pol.referents()}
    assert "panel" in kinds
    assert pol.n_referent_frames == 1
    lbl, _ = pol.choose()                                     # accessor must not break action selection
    assert isinstance(lbl, str)
    # a plain follow-up frame -> referents cleared (recomputed per frame)
    pol.observe(np.zeros((12, 12), dtype=int), [1, 2, 3, 4, 5])
    assert pol.referents() == []
