"""THE SELF, FAMILY-GENERALLY (cycle 21) -- the objective composer must not presuppose a translating avatar.

Before this, `_pose_goal_step` returned at its FIRST line unless `cursor`+`vecs` existed, and those are assigned
in exactly one place: the DIRECTIONAL branch of the router. Measured across all 25 public games at equal budget
(cycle 20), 12 never accumulated a single GoalStep -- including all three games we win -- so Fig-1's
objective-composition organ did not merely underperform outside that one family, it did not EXIST there. These
tests pin the removal of that smuggled presupposition ("the self is a colour-blob that translates"):

  * the self is the SPATIAL SUPPORT OF MY OWN EFFECT -- where the residual lands -- not a colour blob;
  * a whole-board redraw is NOT my effect (bounded), so no centre-of-board self is invented;
  * where the action CARRIED a coordinate, contingency is known by construction and outranks prominence
    (the Goodhart guard from self_locus.py: an autonomous mover must not be mis-claimed as self);
  * the last legible locus persists through a no-op step;
  * DIRECTIONAL is PRESERVED -- a learned cursor still outranks the effect locus, and the minted sensorium
    self outranks both;
  * end-to-end, a policy with NO cursor now accumulates goal-steps and POSES an objective, where it posed none.

Nothing here names a game. These pin the composer's ENTRY, not a guaranteed answer: what gets posed is still
priced by the ground, and pose_goal returning None when nothing compresses stays the honest outcome.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.policy import ReduxPolicy, LOCUS_MAX_FRAC


def _pol(**kw):
    p = ReduxPolicy(game_id="test")
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _board(h=24, w=24):
    return np.zeros((h, w), dtype=int)


def test_effect_locus_is_the_support_of_the_change():
    """A click game's 'self' is where the action LANDED -- the region that changed, wherever it is."""
    a = _board(); b = _board()
    b[3:6, 17:20] = 5                                    # a compact 9px change in the top-right
    p = _pol(frames=[a, b])
    assert p._effect_locus() == (4, 18)


def test_a_whole_board_redraw_is_not_my_effect():
    """Above LOCUS_MAX_FRAC the change is the WORLD's (redraw / animated field / scroll). Averaging it would
    invent a self at the centre of the board -- the exact kind of smuggled percept this build removes."""
    a = _board(); b = _board() + 7                        # every cell changed
    assert (b != a).sum() > LOCUS_MAX_FRAC * b.size       # (guard the test's own premise)
    p = _pol(frames=[a, b])
    assert p._effect_locus() is None


def test_the_carried_coordinate_beats_a_bigger_autonomous_mover():
    """THE GOODHART GUARD. A large region changes on its own; a small one changes where I clicked. Contingency
    is known by construction for the cell I named, so the small one is the self -- not the prominent drifter."""
    a = _board(); b = _board()
    b[0:4, 0:8] = 6                                       # 32px of autonomous animation
    b[19, 20] = 2                                         # 1px -- exactly where I clicked
    p = _pol(frames=[a, b], click_rc=[(19, 20)])
    assert p._effect_locus() == (19, 20)
    q = _pol(frames=[a, b])                               # same frames, no coordinate carried -> prominence only
    assert q._effect_locus() == (2, 4)                    # the centroid of the big drifting block


def test_the_last_legible_locus_persists_through_a_noop():
    """An actor that did nothing this step still exists; a no-op must not blank the self."""
    a = _board(); b = _board(); b[10:12, 4:6] = 3
    p = _pol(frames=[a, b])
    first = p._effect_locus()
    assert first is not None
    p.frames = [b, b.copy()]                              # nothing changed
    assert p._effect_locus() == first


def test_a_learned_cursor_still_outranks_the_effect_locus():
    """DIRECTIONAL is PRESERVED: where a translator was learned, that is still the self (no behaviour change)."""
    g = _board(); g[8, 9] = 4
    p = _pol(frames=[_board(), g], cursor=4)
    assert p._self_locus(g) == ((8, 9), 4, "cursor")


def test_the_minted_sensorium_self_outranks_everything():
    g = _board(); g[8, 9] = 4; g[2, 2] = 6
    p = _pol(frames=[_board(), g], cursor=4, _self_focus=(2, 2))
    assert p._self_locus(g) == ((2, 2), 6, "minted")


def test_no_cursor_and_no_effect_yet_poses_nothing():
    """Honest silence, not a fabricated self: with no legible effect there is no locus and no goal-step."""
    p = _pol(frames=[_board(), _board()])
    assert p._self_locus(_board()) is None
    p._pose_goal_step(True)
    assert p._goal_steps == []


def test_a_non_directional_game_now_poses_an_objective():
    """END-TO-END, the headline. NO cursor and NO learned action->displacement basis: the pre-cycle-21 composer
    accumulated ZERO goal-steps in this situation. Here the agent's own effect walks toward a static landmark (7)
    while a distractor (8) sits in the far corner, and progress is flagged on the steps that closed distance to 7.
    The composer must now both RUN and select the reward-linked target out of the two candidates."""
    p = _pol()
    tgt = (3, 20)
    prev = None
    for k in range(60):
        r, c = 20 - (k % 18), 3 + (k % 18)               # the changed region walks toward the landmark
        g = _board()
        g[2:5, 19:22] = 7                                # a compact static landmark
        g[20:23, 2:5] = 8                                # a compact static distractor
        g[r, c] = 3                                      # this step's change (the agent's own effect)
        p.frames = [p.frames[-1] if p.frames else _board(), g]
        p.acts.append("A1")
        p.click_rc.append((r, c))
        d_now = abs(r - tgt[0]) + abs(c - tgt[1])
        progressed = prev is not None and d_now < prev
        prev = d_now
        p._pose_goal_step(bool(progressed))
    assert p.cursor is None and not p.vecs               # (premise: this is NOT the directional path)
    assert len(p._goal_steps) > 0, "the composer still never ran outside DIRECTIONAL"
    assert p._locus_kind == "effect"
    assert p.n_posed > 0, "accumulated a progress stream but never posed an objective"
    assert p._posed_goal is not None and p._posed_goal.target == 7, p._posed_goal
    assert p.abduced[-1]["locus"] == "effect"            # the agent can SAY which self it reasoned from


def test_the_old_entry_gate_is_restorable_for_an_ab(monkeypatch):
    monkeypatch.setenv("OURO_POSE_ANYFAM", "0")
    p = ReduxPolicy(game_id="test")
    g = _board(); g[5, 5] = 3
    p.frames = [_board(), g]
    p.click_rc = [(5, 5)]
    p._pose_goal_step(True)
    assert p._goal_steps == []                           # DIRECTIONAL-only, exactly as before


def test_the_stream_resets_when_the_self_changes_hypothesis():
    """One objective cannot be composed across two different selves. When the router learns a translator mid-run,
    the effect-locus steps accumulated during warmup must NOT stay in the window scoring R(avatar, target)."""
    p = _pol()
    for k in range(8):
        g = _board(); g[2:5, 19:22] = 7; g[10, 3 + k] = 3
        p.frames = [p.frames[-1] if p.frames else _board(), g]
        p.acts.append("A1"); p.click_rc.append(None)
        p._pose_goal_step(k % 2 == 0)
    assert p._locus_kind == "effect" and len(p._goal_steps) > 1
    p.cursor = 3                                          # the router settles DIRECTIONAL partway through
    g = _board(); g[2:5, 19:22] = 7; g[10, 12] = 3
    p.frames = [p.frames[-1], g]; p.acts.append("A1"); p.click_rc.append(None)
    p._pose_goal_step(True)
    assert p._locus_kind == "cursor"
    assert len(p._goal_steps) == 1                        # only the step taken under the NEW self survives
