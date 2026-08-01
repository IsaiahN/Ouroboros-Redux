"""★★★ THE SELECTOR BRANCH: WHICH LAYER ACTUALLY CHOSE THE LABEL THE AGENT EMITTED. ★★★

Seven games in the last full sweep spent their whole budget on ONE action label. Six of them
(`ft09`, `lp85`, `r11l`, `s5i5`, `tn36`, `vc33`) are answered by the action set the environment
OFFERS -- 100% of their priced steps exit `click_native` and no label but A6 appears anywhere in
their records. `tr87` is a different animal: A1-A4 were all available and it spent 114 of 119
priced steps on A3, every one of which moved the board.

Reading the code says the shape of `tr87` is a SELECTOR problem, not an offer problem. An
exploratory pick passes through three layers -- the organ's own choice (`AffordanceModel.choose`,
which is curiosity-ordered and therefore CANNOT stick), then `_progress_reinforce`, then
`_relation_reinforce`. Both reinforcers are unguarded `argmax`es over a credit dict, and the
credited action is then the one the organ is charged a visit for, so the curiosity counter is
written by the thing that overrode curiosity. While one label leads, the argmax returns it at
every single call and the organ's ordering never reaches the wire -- an absorbing selector of the
same shape CLASSIFIER 16 was about.

BUT THAT READING HAD NO RECEIPT. `n_prog_reinforce` / `n_rel_reinforce` are posted only by
`live_goal_run.py`, a path `run_swarm` never takes, so nothing in the sweep's own record could
tell an organ that keeps re-picking apart from a reinforcer that overrides every pick. The
counters under test here are what close that gap, and they are worth nothing until something
pins them. So:

    prog_inactive / rel_inactive   the layer returned before looking
    prog_hold     / rel_hold       the layer was ACTIVE and let the organ's pick stand
    prog_swap     / rel_swap       the layer OVERRODE the organ's pick

The tests below prove the counter can distinguish those three, that it reads DIFFERENTLY on two
boards that differ only in whether a colour count rises, and that it does not change what the
agent emits. What `tr87` actually does is a question for the next sweep, not for this file --
a synthetic lock-in is a demonstration that the mechanism EXISTS, never evidence that any
particular game is in it.

THE SYNTHETIC FINDING, which is a finding about the MECHANISM and not about any game: on a board
that answers with a monotone colour, the progress reinforcer reaches an absorbing state WITH NO
CONSTRUCTION AT ALL -- no seeded credit, no forced state, just sixty steps -- and from then on it
overrides the organ at every call and the agent emits one label forever. See
`test_the_progress_reinforcer_absorbs_with_no_construction_at_all`.
"""
import numpy as np

from newhorse.redux_arch.policy import ReduxPolicy, EFFECT
from newhorse.redux_arch.receipt import summary


def _policy(gid="ee55-eeee"):
    p = ReduxPolicy(game_id=gid)
    p.frames = []
    return p


def _board():
    g = np.zeros((20, 20), dtype=int)
    g[3, 3], g[3, 4] = 4, 5
    return g


def _drive(p, g, n, board="rising", avail=(1, 2, 3, 4), rel=None, rel_credit=None):
    """Two boards, differing in ONE property, which is the whole point of having both.

    `board="rising"` recolours the same four interior cells every step. The board ANSWERS (so the
    escalation organ never arms) and some colour's count rises monotonically, so `ProgressProbe`
    becomes CONFIDENT and the progress reinforcer switches on.

    `board="shuttle"` moves a 2x2 block around a cleared band. The board answers just as much --
    the same order of cells change per step -- but every colour's count is CONSTANT, so no
    monotone signal exists. This is the control: same organ, same family, same budget, and the
    only thing that differs is whether the layer under test has anything to act on.

    `rel` / `rel_credit` CONSTRUCT the relation drive after each observe, the way
    `test_escalation_branch` constructs `_escalated` directly: `_probe_rel` is recomputed from the
    frame every step, and whether a real board reaches that state often is the sweep's job, not a
    unit test's. What is under test is the CONSEQUENCE of being in it.
    """
    labels, tick = [], 0
    for _ in range(n):
        p.observe(g.copy(), list(avail), 0)
        if rel is not None:
            p._probe_rel = rel
            p._rel_credit = dict(rel_credit or {})
        lbl, _d = p.choose()
        labels.append(lbl)
        tick += 1
        if board == "rising":
            g[9:11, 9:11] = tick % 5 + 1
        else:
            g[8:14, 4:16] = 0
            r, c = 8 + (tick % 4), 4 + (tick * 3) % 10
            g[r:r + 2, c:c + 2] = 3
    return labels


def test_the_progress_reinforcer_absorbs_with_no_construction_at_all():
    """THE FINDING. Nothing is constructed here -- no seeded credit, no forced state, no injected
    relation. An EFFECT game is driven for sixty steps on a board that answers, and the progress
    reinforcer overrides the organ on 98% of its calls and pins the agent to a single label for
    the rest of the episode.

    The mechanism is the EMA at `observe`: only the EMITTED action is ever credited, so once any
    action leads the argmax it keeps being emitted, keeps being the only action credited, and
    keeps leading. Curiosity is still choosing underneath -- `prog_swap` firing at nearly every
    call is precisely the evidence that its choice never reached the wire.

    This is a statement about the MECHANISM. It is not evidence that any live game is in this
    state; that is what the counter was wired to find out."""
    p = _policy("aa11-absorb")
    p.family = EFFECT
    labels = _drive(p, _board(), 60, board="rising")
    b = p._sel_branch
    fx = int(p._dec_exits.get("family_effect", 0))
    assert fx >= 50, p._dec_exits
    assert b.get("prog_swap", 0) >= 0.9 * fx, (b, fx)
    assert len(set(labels[-30:])) == 1, labels[-30:]


def test_the_swap_counter_names_the_credited_label_not_the_organs_pick():
    """The same drive with the credit SEEDED elsewhere. If the counter were measuring the organ,
    seeding a different action would change nothing; because it is measuring the override, the
    emitted label follows the seed. Same board, same budget, different answer."""
    p = _policy("aa11-seeded")
    p.family = EFFECT
    p._prog_credit = {"A3": 5.0}
    labels = _drive(p, _board(), 60, board="rising")
    assert set(labels[-30:]) == {"A3"}, labels[-30:]
    assert p._sel_branch.get("prog_swap", 0) >= 50, p._sel_branch


def test_the_control_the_layer_is_ACTIVE_and_the_organs_ordering_reaches_the_wire():
    """THE VACUITY CONTROL, and the reason the shuttle board exists. A counter that only ever
    reads `swap` is measuring its own call site, not the agent. Here the reinforcer is entered
    exactly as often -- same family, same exits -- but no colour count rises, so it has no
    positive credit to prefer and every call ends in `hold`. The organ's curiosity ordering then
    reaches the wire and the emitted labels CYCLE, which is the behaviour the swap-heavy run does
    not have. `prog_swap` must be ZERO: this is the reading that proves the other one is not an
    artefact of the instrument."""
    p = _policy("bb22-hold")
    p.family = EFFECT
    labels = _drive(p, _board(), 60, board="shuttle")
    b = p._sel_branch
    assert b.get("prog_swap", 0) == 0, b
    assert b.get("prog_hold", 0) >= 50, b
    assert len(set(labels[-12:])) >= 3, labels[-12:]


def test_a_constructed_relation_drive_locks_the_SECOND_layer_the_same_way():
    """The relation reinforcer is the same argmax one layer further down, and it gets the last
    word -- whatever `_progress_reinforce` returned, this can still override it. The state is
    CONSTRUCTED (a driven relation with credit on A2) because reaching it depends on referents a
    20x20 synthetic board does not have; the consequence is what is under test. The board is the
    shuttle, on which the progress layer provably HOLDS, so a lock-in here can only have come from
    the relation layer."""
    p = _policy("cc33-rel")
    p.family = EFFECT
    labels = _drive(p, _board(), 60, board="shuttle", rel="ORDER", rel_credit={"A2": 5.0})
    b = p._sel_branch
    assert b.get("rel_swap", 0) >= 20, b
    assert set(labels[-20:]) == {"A2"}, labels[-20:]
    assert b.get("prog_swap", 0) == 0, b          # the layer above still held; this is the one that swapped


def test_both_splits_sum_to_their_call_sites_exits_on_the_receipt():
    """The two identities, checked on the pooled receipt where every other identity in this
    instrument is checked. The branch counts are written at the returns inside the reinforcers and
    the exit counts at returns inside `_decide`; they are independent counters of the same steps,
    so a non-zero residue means one of them is wrong and neither may be cited.

    `_progress_reinforce` has TWO call sites (`_act_effect` and both of `_explore`'s returns) and
    `_relation_reinforce` has one, which is why the two identities are different sums and why they
    are published separately rather than pooled into one number that could not say which side
    broke."""
    p = _policy("dd44-sums")
    p.family = EFFECT
    _drive(p, _board(), 60, board="rising")
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    slb, ex = dfn["sel_branch"], dfn["exits"]
    assert int(ex.get("family_effect", 0)) > 0, ex
    assert sum(v for k, v in slb.items() if k.startswith("prog_")) == \
        int(ex.get("family_effect", 0)) + int(ex.get("dir_explore", 0)), dfn
    assert sum(v for k, v in slb.items() if k.startswith("rel_")) == int(ex.get("family_effect", 0)), dfn
    assert dfn["sel_branch_prog_residue"] == 0, dfn
    assert dfn["sel_branch_rel_residue"] == 0, dfn


def test_the_prog_identity_holds_on_the_OTHER_call_site_too():
    """A DIRECTIONAL game routes its exploratory picks through `_explore` -> `dir_explore`, never
    through `_act_effect`. That exercises the second term of the prog identity and, at the same
    time, pins the rel identity at ZERO on both sides -- the relation layer is not on this path at
    all, so a `rel_*` count appearing here would mean a call site had moved."""
    p = _policy("dd44-dir")
    _drive(p, _board(), 80, board="shuttle")
    assert p.family == "directional", p.family
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    slb, ex = dfn["sel_branch"], dfn["exits"]
    assert int(ex.get("dir_explore", 0)) > 0, ex
    assert sum(v for k, v in slb.items() if k.startswith("prog_")) == int(ex.get("dir_explore", 0)), dfn
    assert sum(v for k, v in slb.items() if k.startswith("rel_")) == 0, dfn
    assert dfn["sel_branch_prog_residue"] == 0 and dfn["sel_branch_rel_residue"] == 0, dfn


def test_an_unliteralled_return_breaks_the_residue_of_ITS_OWN_layer_only():
    """The residue is worth publishing only if something added without a reading breaks it, and
    the two residues are worth publishing SEPARATELY only if each is blind to the other's keys.
    Inject into one prefix and exactly one number must move."""
    p = _policy("ee55-guard")
    p.family = EFFECT
    _drive(p, _board(), 60, board="rising")
    p._sel_branch["prog_some_new_return"] = 7
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    assert dfn["sel_branch_prog_residue"] == -7, dfn
    assert dfn["sel_branch_rel_residue"] == 0, dfn

    q = _policy("ee55-guard2")
    q.family = EFFECT
    _drive(q, _board(), 60, board="rising")
    q._sel_branch["rel_some_new_return"] = 3
    q._close_segment("death")
    dfn2 = summary(q.receipts)["decide_funnel"]
    assert dfn2["sel_branch_rel_residue"] == -3, dfn2
    assert dfn2["sel_branch_prog_residue"] == 0, dfn2


def test_the_branch_counter_does_not_change_what_the_agent_emits():
    """An instrument that alters the thing it measures is not an instrument. Two identical runs,
    one with the branch dict swapped for a sink that discards every write: the emitted action
    sequences must be identical. This matters more here than it did for the escalation counter,
    because these writes sit on the hot path of the selector itself."""
    class _Sink(dict):
        def __setitem__(self, k, v):                   # accept and discard
            pass

    a_p = _policy("ff66-a")
    a_p.family = EFFECT
    a = _drive(a_p, _board(), 80, board="rising")

    b_p = _policy("ff66-a")
    b_p.family = EFFECT
    b_p._sel_branch = _Sink()
    b = _drive(b_p, _board(), 80, board="rising")

    assert a == b, (a, b)
