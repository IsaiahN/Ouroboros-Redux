"""Family-A referent fix: a framed SYMBOL DISPLAY -- a single-colour BORDER RING enclosing a small symbol -- is a
`panel` (a reference the agent reads a target configuration from: key & lock, a target symbol), NOT scattered endpoint
markers. The dense-block panel test misses it because the frame encloses mostly background, so a large sparse box used
to read as endpoints. General principle: a genuine closed border ring (all four sides, mostly hollow) enclosing content.
Built + tested on synthetic frames; names no game. Precision: a bare marker pair with NO ring stays endpoints."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.referent import find_referents, _find_ring_panels
from newhorse.redux_arch.relation import RelationBank, RelationCtx


def _ring(g, colour, r0, c0, r1, c1):
    g[r0, c0:c1 + 1] = colour; g[r1, c0:c1 + 1] = colour; g[r0:r1 + 1, c0] = colour; g[r0:r1 + 1, c1] = colour


def test_large_sparse_framed_symbol_is_a_panel_not_endpoints():
    """A 9x9 ring (fill < 0.5, so `_find_panels` skips it) enclosing a small symbol -> a panel via the ring detector."""
    g = np.zeros((14, 14), dtype=int)
    _ring(g, 2, 2, 2, 10, 10)                                 # 9x9 hollow frame in a big background sea
    g[6, 6] = 7                                               # a single-cell symbol inside
    refs = find_referents(g)
    panels = [r for r in refs if r.kind == "panel"]
    assert any(r.detail.get("via") == "ring" and r.colour == 2 for r in panels)   # emitted as a framed panel
    assert not [r for r in refs if r.kind == "endpoints"]     # the sparse box is not read as scattered markers


def test_two_framed_symbols_same_shape_are_a_matchable_panel_pair():
    """Key & lock: two identical-shape framed displays -> two panels, so role-by-mutation + MATCH can compare them."""
    g = np.zeros((14, 20), dtype=int)
    _ring(g, 2, 2, 2, 8, 8); g[5, 5] = 7                      # display A (the 'key'), interior symbol colour 7
    _ring(g, 2, 2, 12, 8, 18); g[5, 15] = 8                  # display B (the 'lock'), interior symbol colour 8
    panels = [r for r in find_referents(g) if r.kind == "panel"]
    assert len(panels) == 2
    assert all(r.detail.get("via") == "ring" for r in panels)
    a, b = sorted(panels, key=lambda r: r.bbox[1])
    ha, wa = a.bbox[2] - a.bbox[0], a.bbox[3] - a.bbox[1]
    hb, wb = b.bbox[2] - b.bbox[0], b.bbox[3] - b.bbox[1]
    assert (ha, wa) == (hb, wb)                               # same interior shape -> a comparable MATCH pair


def test_role_by_mutation_over_a_framed_pair_feeds_directed_match():
    """One framed display mutates (workspace/key), the other is invariant (reference/lock). Roles resolve, and MATCH
    measures a directed discrepancy that goes to 0 as the key is brought to the lock's symbol -- end to end from
    detection through relation, no game id."""
    def frame(key_sym):
        g = np.zeros((12, 20), dtype=int)
        _ring(g, 2, 2, 2, 6, 6); g[4, 4] = key_sym            # workspace display (mutates)
        _ring(g, 2, 2, 12, 6, 16); g[4, 14] = 9              # reference display (invariant symbol 9)
        return g
    bank = RelationBank(min_obs=4, min_range=1.0)
    seq = [5, 5, 7, 7, 9, 9]                                  # key symbol converges to the lock's (9)
    for k in seq:
        g = frame(k)
        bank.observe(g, find_referents(g), RelationCtx(cursor=None, passable=frozenset(), bg=0))
    assert bank.role_bboxes() is not None                     # workspace vs reference resolved by mutation
    assert bank.discrepancies()["MATCH"] == 0.0               # directed MATCH nulled once key == lock


def test_bare_marker_pair_with_no_ring_stays_endpoints():
    """Precision: two small same-colour blobs with NO enclosing frame are still endpoints, not a spurious panel."""
    g = np.zeros((12, 12), dtype=int)
    g[3, 3] = 4; g[8, 9] = 4                                  # a matched pair, no border ring anywhere
    refs = find_referents(g)
    assert [r for r in refs if r.kind == "endpoints"]
    assert not [r for r in refs if r.kind == "panel"]


def test_two_facing_bars_are_not_a_framed_panel():
    """Precision: two parallel bars (an open channel, not a closed enclosure) must not be mistaken for a border ring."""
    g = np.zeros((12, 12), dtype=int)
    g[3, 2:10] = 2; g[9, 2:10] = 2                            # top and bottom bars only -- left/right open
    g[6, 6] = 7
    assert not _find_ring_panels(g, 0)


def test_plain_board_yields_no_ring_panel():
    g = np.zeros((12, 12), dtype=int); g[5, 5] = 3
    assert not _find_ring_panels(g, 0)
