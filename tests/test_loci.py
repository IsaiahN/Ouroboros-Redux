"""
Persistent-identity loci (`_track`) -- the Tether §3.5 structural precondition for a real boundary diff. An object
must keep its id through translation, recolour, reshape and level redraw; genuinely new objects get fresh ids and
vanished ones decay. These pin each of those, plus a real m0r0 recording (the two bodies keep ids through motion).
"""
import sys, os, glob, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.loci import LociTracker, Locus


def _blank(h=20, w=20):
    return np.zeros((h, w), dtype=int)


def test_identity_survives_translation():
    tr = LociTracker()
    ids = []
    for c in range(3, 10):
        f = _blank(); f[5:7, c:c + 2] = 7          # a 2x2 block sliding right
        loci = tr.observe(f)
        ids.append(loci[0].id)
    assert len(set(ids)) == 1                       # one identity throughout the slide


def test_identity_survives_recolour():
    tr = LociTracker()
    f1 = _blank(); f1[5:7, 5:7] = 7
    f2 = _blank(); f2[5:7, 5:7] = 3                 # same mask, different colour
    id1 = tr.observe(f1)[0].id
    l2 = tr.observe(f2)[0]
    assert l2.id == id1 and l2.colour == 3          # identity kept, colour updated (colourless shape signature)


def test_identity_survives_reshape():
    tr = LociTracker()
    f1 = _blank(); f1[5:7, 5:7] = 7                 # 2x2 (size 4)
    f2 = _blank(); f2[5:7, 5:8] = 7                 # 2x3 (size 6) -- grew
    id1 = tr.observe(f1)[0].id
    assert tr.observe(f2)[0].id == id1              # fuzzy size-tolerant match keeps identity


def test_two_identical_objects_do_not_swap_ids():
    tr = LociTracker()
    seen = []
    for step in range(4):
        f = _blank()
        f[5:7, 4 + step:6 + step] = 7               # left block sliding right
        f[5:7, 15 + step:17 + step] = 7             # right block sliding right
        loci = sorted(tr.observe(f), key=lambda l: l.centroid[1])
        seen.append((loci[0].id, loci[1].id))
    assert len(set(seen)) == 1                       # (left_id, right_id) constant -> no swap
    assert seen[0][0] != seen[0][1]


def test_redraw_persists_survivors_and_fresh_ids_for_new_objects():
    tr = LociTracker()
    f1 = _blank(); f1[2:4, 2:4] = 7; f1[10:13, 10] = 4        # object A (2x2) + object C (3x1)
    tr.observe(f1)
    A_id = [l.id for l in tr.loci() if l.colour == 7][0]
    C_id = [l.id for l in tr.loci() if l.colour == 4][0]
    f2 = _blank(); f2[10:13, 10] = 4; f2[2:6, 2:6] = 5        # C persists; A gone; NEW big 4x4 object B
    tr.observe(f2)
    ids_now = tr.ids()
    assert C_id in ids_now                                    # survivor kept its id (TRANSFERRED)
    assert A_id not in ids_now                                # vanished object not "present"
    B = [l for l in tr.loci() if l.colour == 5][0]
    assert B.id not in (A_id, C_id)                          # the new object is a fresh identity (NOVEL)


def test_vanished_object_decays_after_grace():
    tr = LociTracker(grace=3)
    f = _blank(); f[5:7, 5:7] = 7
    lid = tr.observe(f)[0].id
    for _ in range(3):
        tr.observe(_blank())                                 # absent for 3 frames
    assert lid not in tr.ids()                                # not present immediately
    tr.observe(_blank())                                      # missing now exceeds grace
    assert tr.get(lid) is None                                # fully dropped


def test_real_m0r0_bodies_keep_stable_ids_through_motion():
    hits = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "recordings", "*", "m0r0-*.jsonl")))
    if not hits:
        import pytest; pytest.skip("no m0r0 recording")
    recs = [json.loads(l)["data"] for l in open(hits[0]).read().splitlines()]
    frames = [np.asarray(np.array(r["frame"])[-1]) for r in recs][:15]
    tr = LociTracker()
    body_ids = []
    for f in frames:
        loci = tr.observe(f)
        b = tuple(sorted(l.id for l in loci if l.colour == 10))
        if len(b) == 2:
            body_ids.append(b)
    assert body_ids, "never saw two navy bodies"
    # the two body identities are stable across the motion frames (no churn)
    assert len(set(body_ids)) == 1, "body ids churned: %s" % set(body_ids)


def test_policy_runs_the_tracker_passively():
    from newhorse.redux_arch.policy import ReduxPolicy, Blackboard
    p = ReduxPolicy(game_id="t-1", blackboard=Blackboard())
    f = _blank(); f[5:7, 5:7] = 7
    for c in range(5):
        f = _blank(); f[5:7, 5 + c:7 + c] = 7
        p.observe(f, [1, 2, 3, 4, 5])
        p.choose()
    assert hasattr(p, "tracker") and len(p.tracker.loci()) >= 1   # identity substrate is live for the boundary diff
