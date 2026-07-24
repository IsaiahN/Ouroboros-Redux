"""Family B (ORDER): the reference is an ORDERED token sequence (a legend strip) and the agent brings a WORKSPACE
sequence to match its ORDER (tr87/su15/sb26). Two general pieces: (1) the legend detector now reads tokens in READING
ORDER (detail['sequence']), and (2) the ORDER relation measures the EDIT DISTANCE between two ordered sequences -- a
permutation is a few edits, distinct from MATCH's 2-D content compare. Built + tested on synthetic frames; names no game."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.referent import find_referents, _ordered_tokens
from newhorse.redux_arch.relation import RelationBank, RelationCtx, _levenshtein


def test_ordered_tokens_reads_in_order_with_gaps():
    band = np.array([[0, 3, 3, 0, 4, 0, 5, 5, 0]])            # r r . b . g g  (bg=0)
    assert _ordered_tokens(band, horizontal=True, bg=0) == [3, 4, 5]
    band2 = np.array([[0, 5, 0, 4, 0, 3, 0]])
    assert _ordered_tokens(band2, horizontal=True, bg=0) == [5, 4, 3]
    assert _ordered_tokens(np.array([[3, 3, 0, 3, 3]]), horizontal=True, bg=0) == [3, 3]   # a gap makes a new token


def _frame_two_legends(top_seq, bot_seq, H=14, W=16):
    g = np.zeros((H, W), dtype=int)
    for k, c in enumerate(top_seq):
        g[0, 1 + 2 * k] = c                                   # top strip: tokens spaced along row 0
    for k, c in enumerate(bot_seq):
        g[H - 1, 1 + 2 * k] = c                               # bottom strip along the last row
    return g                                                  # rows 1 and H-2 stay all-bg = the separator gaps


def test_legend_exposes_reading_order_sequence():
    g = _frame_two_legends([3, 4, 5, 6], [6, 5, 4, 3])
    legs = [r for r in find_referents(g) if r.kind == "legend"]
    seqs = sorted(tuple(r.detail["sequence"]) for r in legs)
    assert (3, 4, 5, 6) in seqs and (6, 5, 4, 3) in seqs      # both strips, each in its own reading order
    assert len(legs) == 2                                     # the reversed strip is NOT merged with the forward one


def test_order_discrepancy_is_edit_distance_between_sequences():
    bank = RelationBank(min_obs=4, min_range=1.0)
    ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
    bank.observe(_frame_two_legends([3, 4, 5, 6], [6, 5, 4, 3]), find_referents(_frame_two_legends([3, 4, 5, 6], [6, 5, 4, 3])), ctx)
    # [3,4,5,6] vs [6,5,4,3] is a full reversal (LCS 1) -> 4 substitutions -> edit distance 4
    assert bank.discrepancies()["ORDER"] == float(_levenshtein([3, 4, 5, 6], [6, 5, 4, 3]))
    assert bank.discrepancies()["ORDER"] == 4.0


def test_single_sequence_gives_no_order_discrepancy():
    g = np.zeros((14, 16), dtype=int)
    for k, c in enumerate([3, 4, 5]):
        g[0, 1 + 2 * k] = c                                   # only ONE legend strip -> nothing to order against
    bank = RelationBank()
    ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
    bank.observe(g, find_referents(g), ctx)
    assert bank.discrepancies()["ORDER"] is None


def test_order_selected_as_a_workspace_sequence_is_reordered_to_the_reference():
    """The reference strip is fixed; the workspace strip is permuted toward it over the stream -> edit distance shrinks
    -> ORDER is selected (the tester recognises the closing order)."""
    bank = RelationBank(min_obs=4, min_range=1.0)
    ref = [3, 4, 5, 6]
    seq = [[6, 5, 4, 3], [6, 5, 4, 3], [3, 5, 4, 6], [3, 5, 4, 6], [3, 4, 5, 6], [3, 4, 5, 6]]   # dist 2,2,1,1,0,0
    for ws in seq:
        g = _frame_two_legends(ref, ws)
        bank.observe(g, find_referents(g), RelationCtx(cursor=None, passable=frozenset(), bg=0))
    assert bank.discrepancies()["ORDER"] == 0.0
    assert bank.selected() == "ORDER"
