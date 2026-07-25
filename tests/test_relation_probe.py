"""The DRIVE bootstrap (family-B ORDER and any measured relation): a relation can only be SELECTED once some action is
seen to shrink its discrepancy, but before selection the effect tier credited nothing -- so a measured-but-unselected
gap (e.g. ORDER on an effect game like sb26, which measures ~15 live but never selects) sat flat and was never driven.
The fix is an EPISTEMIC PROBE: credit actions by the drop they produce in the LARGEST MEASURED gap even before selection,
and let the effect reinforce engage on that probed relation, so its drivability gets tested (spec §3.5 probe-to-isolate).
General: names no game, privileges no relation, credits only real drops. Built + tested on synthetic frames."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.relation import RelationBank, RelationCtx
from newhorse.redux_arch.referent import find_referents
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard


def _two_legends(top_seq, bot_seq, H=14, W=16):
    g = np.zeros((H, W), dtype=int)
    for k, c in enumerate(top_seq):
        g[0, 1 + 2 * k] = c
    for k, c in enumerate(bot_seq):
        g[H - 1, 1 + 2 * k] = c
    return g


def test_delta_tracks_an_order_gap_and_max_measured_returns_a_measured_relation():
    # NOTE (targeting caveat): max_measured() ranks by RAW discrepancy across relations, whose scales differ (ORDER =
    # edit distance, CONNECT = pixel distance). The probe target is therefore heuristic and validated LIVE, not asserted
    # here. What IS pinned: delta computes a relation's OWN drop, and a probe target exists whenever anything measures.
    # (Until the same-context filter in referent.py, the shared tokens of these two legends ALSO minted a straddling
    # endpoint pair per colour, so CONNECT co-measured a pixel distance between a reference token and its workspace
    # twin. That measurement was on a false object and is now gone -- the loss is a correction, not a regression.)
    bank = RelationBank(min_obs=5, min_range=1.0)
    ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
    g = _two_legends([3, 4, 5, 6], [6, 5, 4, 3])                 # a full reversal -> ORDER edit distance 4
    bank.observe(g, find_referents(g), ctx)
    assert bank.discrepancies()["ORDER"] == 4.0
    g2 = _two_legends([3, 4, 5, 6], [3, 5, 4, 6])                # closer -> ORDER edit distance 2
    bank.observe(g2, find_referents(g2), ctx)
    assert bank.delta("ORDER") == 2.0                            # prev(4) - cur(2) = a real drop of 2 for ORDER itself
    mm = bank.max_measured()
    assert mm is not None and bank.discrepancies()[mm] is not None   # a probe target exists and is actually measuring
    assert bank.discrepancies()[mm] == max(v for v in bank.discrepancies().values() if v is not None)


def test_max_measured_is_none_when_nothing_measures():
    bank = RelationBank()
    ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
    g = np.zeros((12, 12), dtype=int); g[5, 5] = 3               # a plain board -> no relation measures
    bank.observe(g, find_referents(g), ctx)
    assert bank.max_measured() is None
    assert bank.delta("ORDER") == 0.0                            # no measured points -> no drop


def _min_policy():
    p = ReduxPolicy(game_id="probe-x", blackboard=Blackboard(), warmup_cap=2)
    p.frames = [np.zeros((4, 4), dtype=int), np.zeros((4, 4), dtype=int)]   # >=2 frames so credit can accrue
    p.acts = ["RESET", "A1"]
    return p


def test_reinforce_engages_on_a_probed_relation_before_any_selection():
    """The core bootstrap: with NOTHING selected but a probed relation carrying positive action-credit, the effect
    reinforce biases the exploratory pick toward the gap-closing action -- so the agent intervenes to test drivability
    instead of waiting for undirected exploration to happen upon a reduction."""
    p = _min_policy()
    p._relation_selected = None                                  # nothing confidently selected yet
    p._probe_rel = "ORDER"                                       # ORDER is the largest measured gap being probed
    p._rel_credit = {"A1": 0.7, "A2": 0.0}                       # A1 has historically closed the gap
    assert p._relation_reinforce("A2", ["A1", "A2"]) == "A1"     # swap the exploratory pick toward the gap-closer
    assert p.n_rel_reinforce == 1


def test_reinforce_is_a_noop_without_a_probe_or_without_positive_credit():
    p = _min_policy()
    p._probe_rel = None                                          # nothing measured or selected -> no drive
    p._rel_credit = {"A1": 0.7}
    assert p._relation_reinforce("A2", ["A1", "A2"]) == "A2"     # unchanged
    p._probe_rel = "ORDER"
    p._rel_credit = {"A1": 0.0, "A2": 0.0}                       # no gap-closing evidence yet
    assert p._relation_reinforce("A2", ["A1", "A2"]) == "A2"     # a probe with no evidence changes nothing (precision)
    p._rel_credit = {"A6": 0.9}                                  # click coords are never a per-label credit
    assert p._relation_reinforce("A2", ["A2", "A6"]) == "A2"     # A6 left untouched (click win safe)


def test_probe_bootstraps_order_selection_over_a_closing_stream():
    """End-to-end on synthetic frames: a fixed reference + a workspace sequence permuted toward it -> the probe credits
    the reduction, ORDER is the max measured gap throughout, and once the gap confidently shrinks the tester SELECTS it
    -- the measure->probe->select chain the effect drive then reinforces (no live game, no game id)."""
    bank = RelationBank(min_obs=4, min_range=1.0)
    ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
    ref = [3, 4, 5, 6]
    stream = [[6, 5, 4, 3], [6, 5, 4, 3], [3, 5, 4, 6], [3, 5, 4, 6], [3, 4, 5, 6], [3, 4, 5, 6]]  # dist 4,4,2,2,0,0
    for ws in stream:
        g = _two_legends(ref, ws)
        bank.observe(g, find_referents(g), ctx)
        if bank.discrepancies().get("ORDER"):                    # while a gap is OPEN there must be a probe target...
            assert bank.max_measured() == "ORDER"
    assert bank.max_measured() is None                           # ...and once it closes there is nothing left to probe

    assert bank.discrepancies()["ORDER"] == 0.0
    assert bank.selected() == "ORDER"                            # the confidently-closing ORDER gap gets selected
