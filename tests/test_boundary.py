"""
The loci-based BOUNDARY DIFF (Tether §3.5) -- partition a level graduation by TRACKED IDENTITY (TRANSFERRED /
NOVEL / GONE), detect broken-by-REBINDING from the action-set delta, PARK unresolved residual under decay, and
route every mint through the human-confirmation gate. Synthetic + a real m0r0 L1->L2 boundary.
"""
import sys, os, glob, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.boundary import BoundaryDiff, diff_identities, Quarantine
from newhorse.redux_arch.loci import LociTracker
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard


class _L:                                    # a stand-in locus with an id (diff_identities only reads .id)
    def __init__(self, i): self.id = i


def test_diff_identities_partitions_by_persistence():
    transferred, novel, gone = diff_identities({1, 2, 3}, [_L(2), _L(3), _L(4)])
    assert transferred == [2, 3] and novel == [4] and gone == [1]


def test_rebinding_is_the_action_set_change():
    bd = BoundaryDiff(1, [1], [2], [], new_colours=[], gone_colours=[], new_actions=[6], gone_actions=[])
    assert bd.rebinding is True
    bd2 = BoundaryDiff(1, [1], [2], [], new_colours=[9], gone_colours=[], new_actions=[], gone_actions=[])
    assert bd2.rebinding is False           # new COLOURS alone are novel actors, not a control-set rebinding


def test_quarantine_parks_wakes_and_decays():
    q = Quarantine()
    q.park("a", {"x": 1}, budget=2)
    assert q.wake("a") == {"x": 1} and q.wake("a") is None    # wake retrieves once
    q.park("b", {"y": 2}, budget=2)
    assert q.tick() == [] and "b" in q.live()                 # budget 2->1, still parked
    assert q.tick() == ["b"] and q.live() == {}               # budget ->0, decayed out


def _blank(h=20, w=20):
    return np.zeros((h, w), dtype=int)


def test_policy_boundary_diff_marks_transferred_and_novel():
    p = ReduxPolicy(game_id="t-1", blackboard=Blackboard())
    for _ in range(2):
        f = _blank(); f[2:4, 2:4] = 7                          # object A, static
        p.observe(f, [1, 2, 3, 4, 5], 0); p.choose()
    f = _blank(); f[2:4, 2:4] = 7; f[10:12, 10:12] = 5         # A persists + NEW object B, level up
    p.observe(f, [1, 2, 3, 4, 5], 1); p.choose()
    assert p.boundary is not None
    assert len(p.boundary.transferred) >= 1                    # A carried its identity across the boundary
    assert len(p.boundary.novel) >= 1 and p.novel_loci == p.boundary.novel   # B is a novel actor, surfaced for beat C


def test_policy_action_set_growth_is_rebinding():
    p = ReduxPolicy(game_id="t-2", blackboard=Blackboard())
    for _ in range(2):
        f = _blank(); f[2:4, 2:4] = 7
        p.observe(f, [1, 2, 3, 4, 5], 0); p.choose()
    f = _blank(); f[2:4, 2:4] = 7
    p.observe(f, [1, 2, 3, 4, 5, 6], 1); p.choose()            # control set grew (ACTION6 unlocked)
    assert p.boundary.rebinding is True
    assert p.level_model["decision"].startswith("rederive")    # re-fit, not treated as a fresh mechanism


def test_mint_gate_parks_novel_and_passes_rederivation(tmp_path):
    p = ReduxPolicy(game_id="g9", blackboard=Blackboard())
    cp = str(tmp_path / "claims.jsonl"); fp = str(tmp_path / "confirmed.txt")
    assert p.mint_gate("RE-DERIVATION", "NEAR", 47.0, claims_path=cp, confirmed_path=fp) is True   # nothing to certify
    assert p.mint_gate("NOVEL", "COUNT(k)", 61.0, claims_path=cp, confirmed_path=fp) is False       # parked for human
    assert os.path.exists(cp)                                  # the claim was recorded UNCONFIRMED


def test_real_m0r0_boundary_produces_a_coherent_partition():
    # Honest: on m0r0 the win IS the two bodies MERGING, then L2 respawns them -> at the win-boundary the bodies do
    # NOT transfer identity (the diff correctly reports them as NOVEL). So we validate the DIFF MECHANISM on real
    # data: a coherent partition of the current identities, transferred were genuinely present before, and the
    # redraw changed the object set.
    hits = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "recordings", "*", "m0r0-*.jsonl")))
    cross = None
    for p_ in hits:
        recs = [json.loads(l)["data"] for l in open(p_).read().splitlines()]
        lv = [r.get("levels_completed", 0) for r in recs]
        b = next((i for i in range(1, len(lv)) if lv[i] > lv[i - 1]), None)
        if b is not None:
            cross = (recs, b); break
    if cross is None:
        import pytest; pytest.skip("no m0r0 recording crosses a level boundary")
    recs, b = cross
    frames = [np.asarray(np.array(r["frame"])[-1]) for r in recs]
    tr = LociTracker()
    for f in frames[:b]:
        tr.observe(f)
    prev_ids = set(tr.ids())
    tr.observe(frames[b])                                      # the boundary/redraw frame
    transferred, novel, gone = diff_identities(prev_ids, tr.loci())
    now = {l.id for l in tr.loci()}
    assert set(transferred) | set(novel) == now               # the partition covers every current identity
    assert set(transferred) <= prev_ids                       # transferred ids were genuinely present before
    assert novel or gone                                      # the redraw changed the object set (a real boundary)
