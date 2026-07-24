"""Brick 3 of the reasoning scaffold: the RELATIONAL goal-hypothesis + TESTER. It enumerates the authors' relation set
{MATCH, CONNECT, ORDER, ARRANGE, REACH} as frame-native discrepancies and SELECTS the one whose discrepancy is
confidently shrinking under play -- the hypothesis the environment is rewarding, discovered not encoded. Tests: each
measurable relation is detected + selected as its gap closes; the tester prefers the shrinking relation over a static
one; a board with no referent forces no relation; and the policy steers a directional move toward the relation target.
Names no game."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.relation import RelationBank, RelationCtx
from newhorse.redux_arch.referent import Referent
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard, DIRECTIONAL


# ---- each relation is measured + selected as its discrepancy closes -------------------------------------------
def test_reach_selected_when_cursor_approaches_goal():
    bank = RelationBank(min_obs=5, min_range=1.0)
    ctx = RelationCtx(cursor=7, passable=frozenset(), bg=0)
    goal = Referent("panel", (2, 2, 4, 4), 5, {})            # goal bbox centre = (3,3)
    for r in range(10, 4, -1):                                # cursor (r,r) walks toward the goal, stopping outside it
        g = np.zeros((14, 14), dtype=int); g[r, r] = 7
        bank.observe(g, [goal], ctx)
    assert bank.selected() == "REACH"
    assert bank.drive_target() == (3, 3)                      # the goal cell, exposed for the policy to pursue


def test_connect_selected_as_gap_fills():
    bank = RelationBank(min_obs=4, min_range=1.0)
    ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
    ep = Referent("endpoints", (5, 2, 5, 12), 4, {"centroids": [(5.0, 2.0), (5.0, 12.0)], "sizes": [1, 1]})
    for k in range(0, 9):                                     # a connecting path fills the gap between the two ends
        g = np.zeros((10, 14), dtype=int); g[5, 2] = 4; g[5, 12] = 4
        for c in range(3, 3 + k):
            g[5, c] = 4
        bank.observe(g, [ep], ctx)
    assert bank.selected() == "CONNECT"


def test_match_measures_panel_hamming_to_zero():
    bank = RelationBank(min_obs=4, min_range=0.1)
    ctx = RelationCtx(cursor=None, passable=frozenset(), bg=0)
    ref = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    p1 = Referent("panel", (1, 0, 3, 2), None, {})
    p2 = Referent("panel", (1, 6, 3, 8), None, {})
    for k in range(0, 6):                                     # a workspace panel is edited toward the reference panel
        g = np.zeros((5, 12), dtype=int); g[1:4, 0:3] = ref
        w = np.zeros(9, dtype=int); w[:min(9, 2 * k)] = ref.ravel()[:min(9, 2 * k)]
        g[1:4, 6:9] = w.reshape(3, 3)
        bank.observe(g, [p1, p2], ctx)
    assert bank.discrepancies()["MATCH"] == 0.0              # final workspace equals the reference
    assert bank.selected() == "MATCH"


# ---- Brick 4: REACH goal-identity LOCK keeps the discrepancy monotone (so selection is reliable live) ----------
def test_reach_goal_lock_holds_goal_under_a_nearer_distractor():
    """The bank PINS the goal across frames: a smaller, nearer distractor referent appearing mid-approach must NOT
    hijack REACH's goal (which would make the discrepancy jump and defeat selection). It stays locked on the original
    goal, so the sequence is monotone and REACH is selected -- the fix for Brick 3's live-selection limitation."""
    bank = RelationBank(min_obs=5, min_range=1.0)
    ctx = RelationCtx(cursor=7, passable=frozenset(), bg=0)
    A = Referent("panel", (2, 2, 6, 6), 5, {})               # the real goal: centre (4,4), area 25
    for i, r in enumerate(range(14, 7, -1)):                  # cursor walks toward A
        g = np.zeros((20, 20), dtype=int); g[r, r] = 7
        refs = [A]
        if i >= 3:                                            # a SMALLER (area 9), NEARER distractor appears
            refs.append(Referent("panel", (r - 1, r + 2, r + 1, r + 4), 6, {}))
        bank.observe(g, refs, ctx)
    assert bank.selected() == "REACH"
    assert bank.drive_target() == (4, 4)                      # locked on A, not the smaller nearer distractor


def test_reach_goal_relocks_when_goal_disappears():
    bank = RelationBank(min_obs=3, min_range=1.0)
    ctx = RelationCtx(cursor=7, passable=frozenset(), bg=0)
    for _ in range(3):
        g = np.zeros((16, 16), dtype=int); g[10, 10] = 7
        bank.observe(g, [Referent("panel", (2, 2, 4, 4), 5, {})], ctx)
    assert bank._reach_goal == (2, 2, 4, 4)
    for _ in range(3):
        g = np.zeros((16, 16), dtype=int); g[7, 7] = 7
        bank.observe(g, [Referent("panel", (12, 12, 14, 14), 6, {})], ctx)   # old goal gone -> re-pin
    assert bank._reach_goal == (12, 12, 14, 14)


# ---- the tester prefers the shrinking relation over a static one ----------------------------------------------
def test_tester_prefers_the_shrinking_relation():
    bank = RelationBank(min_obs=5, min_range=1.0)
    ctx = RelationCtx(cursor=7, passable=frozenset(), bg=0)
    goal = Referent("panel", (2, 2, 4, 4), 5, {})
    ep = Referent("endpoints", (8, 2, 8, 12), 4, {"centroids": [(8.0, 2.0), (8.0, 12.0)], "sizes": [1, 1]})
    for r in range(10, 4, -1):                                # REACH shrinks; CONNECT gap is never filled (static)
        g = np.zeros((14, 14), dtype=int); g[r, r] = 7; g[8, 2] = 4; g[8, 12] = 4
        bank.observe(g, [goal, ep], ctx)
    assert bank.selected() == "REACH"
    assert bank._decreasing(bank.hist["CONNECT"])[2] == 0.0   # CONNECT net decrease is 0 -> not rewarded, not selected


# ---- precision: no referent forces no relation ----------------------------------------------------------------
def test_no_referent_no_relation_selected():
    bank = RelationBank()
    ctx = RelationCtx(cursor=7, passable=frozenset(), bg=0)
    for _ in range(8):
        g = np.zeros((10, 10), dtype=int); g[5, 5] = 7
        bank.observe(g, [], ctx)
    assert bank.selected() is None
    assert bank.drive_target() is None


# ---- policy integration: a directional move is steered toward the relation target -----------------------------
def _ring(g, colour, r0, c0, r1, c1):
    g[r0, c0:c1 + 1] = colour; g[r1, c0:c1 + 1] = colour; g[r0:r1 + 1, c0] = colour; g[r0:r1 + 1, c1] = colour


def test_policy_steers_directional_only_after_relation_selected():
    """The relation drive is EARNED: as the cursor approaches a detectable goal panel, REACH's discrepancy shrinks, the
    tester SELECTS it, and only then does the directional policy steer toward the relation target. (Before selection,
    curiosity is left untouched so the affordance/effect organs are not starved by an unconfirmed hypothesis.)"""
    pol = ReduxPolicy(game_id="rel-x", blackboard=Blackboard(), warmup_cap=0)
    pol.family = DIRECTIONAL
    pol.cursor = 7
    pol.vecs = {"A1": (-1, 0), "A2": (1, 0), "A3": (0, -1), "A4": (0, 1)}
    pol.passable = {0}
    pol.stride = 1
    pol.target_colour = None
    for step in range(13, 6, -1):                            # cursor (step,step) walks toward the goal panel at (3,3)
        g = np.zeros((16, 16), dtype=int)
        _ring(g, 2, 1, 1, 5, 5); g[3, 3] = 8                 # a bordered goal panel top-left (with interior content)
        g[step, step] = 7                                    # the cursor, approaching the goal
        pol.observe(g, [1, 2, 3, 4])
        lbl, _ = pol.choose()
        assert lbl in ("A1", "A2", "A3", "A4")
    assert pol.relation()[0] == "REACH"                      # the shrinking discrepancy was confidently selected
    assert pol.n_relation_drive >= 1                          # and the directional move was steered toward its target
