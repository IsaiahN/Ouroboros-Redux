"""★★★ THE CLICK, ATTRIBUTED: 45.4% OF EVERY DECISION, UNDER ONE NAME AND ONE LABEL. ★★★

`click_native` took 1335 of the agent's 2943 decisions last sweep -- the single largest thing it does -- and
NOTHING about those steps could be attributed. Two separate reasons, and they need two separate instruments:

  WHY this click?    `click_native` is ONE exit name over FOUR different returns inside `ClickProber.choose`:
                     no candidates at all, the initial blind enumeration, the learned-target exploit, and the
                     nothing-ever-moved fallback. An exit name covering more than one `return` is not an
                     attribution (RANKING 5) -- this is the same defect the escalation branch had, one organ over.

  DID IT DO ANYTHING? The self-motion control conditions the outcome column on the EMITTED ACTION, and every
                     click carries the same label `A6`. So on click games the control has exactly one row, nothing
                     to vary over, and renders MUTE on every game -- a control that cannot fail is not a control.
                     But the agent does vary its click: it varies WHERE. Keying the same reading by the coarse
                     REGION of the coordinate actually emitted gives the control something to vary over.

★ SUPERSEDED 2026-07-30. The first prediction here was: "`untried_first` DOMINATES, because `refresh()` folds
freshly-perceived candidates in at every step and the untried queue is replenished faster than it drains." The
sweeps confirmed the RATE (96.3%) and the printer banked that as PREDICTION HELD -- but the RATE was never
evidence for the MECHANISM, and no receipt ever measured the mechanism at all. `untried_first` was itself one
name over more than one cause. It is now THREE returns keyed by the ADMISSION ORIGIN of the target being drained
(`untried_perceptual` / `untried_sweep` / `untried_refresh`), with a separate `click_pool` dict counting
admissions at `__init__` and `refresh`. The rival reading, and the new pre-registration, are in
docs/tether/EVIDENCE_the_click_pool_floor.md: the unconditional 64-point `grid_sweep` lattice forces most of that
96.3% at construction, before `refresh` can contribute anything.

Nothing here changes what the agent does. Both instruments are counted at the sites that already exist, and the
last test in this file is the one that proves it.
"""
import numpy as np

from newhorse.redux_arch.policy import ReduxPolicy, CLICK
from newhorse.redux_arch.receipt import summary


def _policy(gid="cl11-cccc"):
    p = ReduxPolicy(game_id=gid)
    p.frames = []
    return p


def _board(h=20, w=20):
    g = np.zeros((h, w), dtype=int)
    g[3, 3], g[3, 4] = 4, 5
    g[12, 15], g[16, 6] = 6, 7
    return g


def _drive(p, g, n, answer=False, avail=(6,)):
    """A click-only game: `avail == [6]` routes `family` to CLICK on the first decision, so every step goes through
    `click_native` -> `_act_click` -> `ClickProber.choose`. `answer=True` moves four interior cells every step
    whatever was clicked -- the board answering regardless, which is the state the region control exists to name."""
    tick = 0
    for _ in range(n):
        p.observe(g.copy(), list(avail), 0)
        p.choose()
        if answer:
            tick += 1
            g[9:11, 9:11] = tick % 5 + 1
    return p


def test_every_click_is_charged_to_the_return_that_produced_it():
    """The floor. Every decision on a click-only game passes through exactly one `return` of `ClickProber.choose`,
    so the branch counts must be non-empty and must name the enumeration the prober actually starts in."""
    p = _drive(_policy("cl11-first"), _board(), 30)
    assert p.family == CLICK, p.family
    assert sum(p._click_branch.values()) == 30, p._click_branch
    assert p._click_branch.get("untried_perceptual", 0) >= 1, p._click_branch
    assert "untried_first" not in p._click_branch, p._click_branch      # the migrated name must not come back


def test_the_click_branch_sums_to_the_click_exits_on_the_receipt():
    """The identity, checked where every other identity in this instrument is checked: on the pooled receipt. The
    branch counts are written inside `ClickProber.choose` and the exit counts at two `return`s inside `_decide`;
    they are independent counters of the same steps, so a non-zero residue means one is wrong and NEITHER may be
    cited. Every return of `choose` produces a click, so unlike the escalation branch nothing is excluded here --
    a no-step name appearing in this dict later must break this residue, which is the point of publishing it."""
    p = _drive(_policy("cl11-sums"), _board(), 40, answer=True)
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    clicks = int(dfn["exits"].get("click_native", 0)) + int(dfn["exits"].get("escalate_click", 0))
    assert clicks > 0, dfn["exits"]
    assert sum(dfn["click_branch"].values()) == clicks, dfn
    assert dfn["click_branch_residue"] == 0, dfn


def test_the_branch_survives_a_segment_boundary():
    """THE FAILURE THIS INSTRUMENT WAS ONE LINE FROM HAVING. The prober holds a REFERENCE to the branch dict and
    outlives the segment -- it is only rebuilt on a level change. If `_close_segment` REBOUND the dict instead of
    clearing it in place, the prober would keep writing into an orphan and every segment after the first would
    report zero clicks: a field never computed, printed as a zero, which is a mis-labelled receipt. Two segments,
    and the SECOND one must carry counts."""
    p = _drive(_policy("cl11-two"), _board(), 20)
    p._close_segment("death")
    assert p._click_branch == {}, p._click_branch
    _drive(p, _board(), 20)
    p._close_segment("death")
    assert len(p.receipts) >= 2, p.receipts
    assert sum(p.receipts[-1].decide_click_branch.values()) > 0, p.receipts[-1].decide_click_branch
    assert sum(p.receipts[-2].decide_click_branch.values()) > 0, p.receipts[-2].decide_click_branch


def test_the_region_split_gives_the_control_something_to_vary_over():
    """The whole reason the region key exists. The action split sees ONE row (`click_native|A6`) because every
    click carries the same label; the region split must see MORE THAN ONE, or it has bought nothing."""
    p = _drive(_policy("cl11-reg"), _board(), 40, answer=True)
    a6 = [k for k in p._dec_act_attr if k.endswith("|A6")]
    assert len(a6) == 1, a6                                # the blind spot, restated as a test
    assert len(p._dec_click_reg_attr) >= 2, p._dec_click_reg_attr


def test_the_region_split_sums_back_to_the_A6_rows_of_the_action_split():
    """It must be the SAME steps, re-keyed -- not a second reading of a different denominator. The residue is
    against the `|A6` rows of the action split rather than against the click exits, because a click decided at a
    segment boundary is unpriced in both and comparing to the exits would fold that residue into this one."""
    p = _drive(_policy("cl11-ident"), _board(), 40, answer=True)
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    a6 = sum(v for k, v in dfn["act_attr"].items() if k.endswith("|A6"))
    assert a6 > 0, dfn["act_attr"]
    assert sum(dfn["click_reg_attr"].values()) == a6, dfn
    assert dfn["click_reg_residue"] == 0, dfn


def test_a_click_with_no_recorded_coordinate_is_NAMED_not_dropped():
    """An `A6` can be emitted by an organ that hands back no coordinate (the cycle fallback). Dropping those steps
    would close the identity above by shrinking the numerator -- silence read as agreement. They get their own
    name instead, so they are visible AND inside the sum."""
    p = _policy("cl11-noxy")

    def _stub():
        p._dec_calls += 1
        return p._exit("stub_exit", ("A6", None))         # a label with no coordinate, as `_cycle` produces
    p._decide = _stub
    _drive(p, _board(), 20, answer=True)
    assert p._dec_click_reg_attr.get("stub_exit|A6@noxy", 0) >= 10, p._dec_click_reg_attr
    assert sum(p._dec_click_reg_attr.values()) == sum(v for k, v in p._dec_act_attr.items()
                                                      if k.endswith("|A6")), p._dec_click_reg_attr


def test_the_region_is_read_off_the_EMITTED_coordinate_and_the_board_it_was_clicked_on():
    """The key must be the agent's actual doing, on a real board's own shape -- a THIRDS grid, frame-relative, no
    threshold and no colour, which is what keeps a descriptive key from turning into a detector. Two clicks placed
    at opposite corners of a 30x30 board must land in opposite corner regions and not agree."""
    p = _policy("cl11-key")
    seq = [{"x": 1, "y": 1}, {"x": 28, "y": 28}]

    def _stub():
        p._dec_calls += 1
        return p._exit("stub_exit", ("A6", seq[min(len(seq) - 1, p.n_emitted)]))
    p._decide = _stub
    g = np.zeros((30, 30), dtype=int); g[3, 3] = 4
    _drive(p, g, 3, answer=True)
    assert p._dec_click_reg_attr.get("stub_exit|A6@r0c0", 0) == 1, p._dec_click_reg_attr
    assert p._dec_click_reg_attr.get("stub_exit|A6@r2c2", 0) >= 1, p._dec_click_reg_attr


def test_no_decision_path_can_READ_the_region_split():
    """A DESCRIPTIVE KEY THAT AN ORGAN READS IS A DETECTOR. The region is computed after the fact, at the pricing
    site, from a coordinate that has already been emitted; nothing on the decision path may consult it. Checked in
    the source of the decision functions themselves, so a future beat that wires it in fails here rather than
    quietly encoding a per-game answer about where to click."""
    import inspect
    from newhorse.redux_arch import policy as _pol
    for fn in (_pol.ReduxPolicy._decide, _pol.ReduxPolicy._act_click, _pol.ReduxPolicy._act_directional,
               _pol.ReduxPolicy._modality_escalate, _pol.ReduxPolicy.choose):
        src = inspect.getsource(fn)
        assert "_dec_click_reg" not in src, fn.__name__
        assert "click_reg" not in src, fn.__name__


def test_neither_instrument_changes_what_the_agent_CLICKS():
    """An instrument that alters the thing it measures is not an instrument. Two identical runs, one with both new
    dicts swapped for sinks that discard every write: the emitted coordinate sequences must be identical."""
    class _Sink(dict):
        def __setitem__(self, k, v):                      # accept and discard
            pass

    a = _drive(_policy("cl11-sink"), _board(), 60, answer=True)
    b = _policy("cl11-sink")
    b._click_branch = _Sink()
    b._click_pool = _Sink()
    b._dec_click_reg_attr = _Sink()
    b._dec_click_reg_moved = _Sink()
    b._dec_click_reg_moved_raw = _Sink()
    _drive(b, _board(), 60, answer=True)
    assert a.acts == b.acts, (a.acts, b.acts)
    assert a.click_rc == b.click_rc, (a.click_rc, b.click_rc)


def test_every_prober_ever_built_writes_into_the_POLICY_dict():
    """THE DEFECT THE FIRST SWEEP FOUND, PINNED. There were two places a `ClickProber` was constructed and only
    one passed the branch dict, so every click after a level re-parameterization went into a private dict nobody
    reads -- 126 of 1393 clicks counted at the exit and missing from the split. Constructed by SOURCE, not by
    driving a level change, because what failed was a call site rather than a code path: any future third site
    that forgets the dict fails here."""
    import inspect
    from newhorse.redux_arch import policy as _pol
    src = inspect.getsource(_pol)
    lines = src.splitlines()
    idx = [i for i, l in enumerate(lines) if "ClickProber(" in l and "class ClickProber" not in l]
    assert len(idx) == 1, idx                              # one constructor, so there is nothing to forget
    # the call may wrap; read it to its closing paren so a continuation line cannot hide a dropped carrier
    call = "\n".join(lines[idx[0]:idx[0] + 3])
    assert "branch=self._click_branch" in call, call
    assert "pool=self._click_pool" in call, call


def test_a_reparameterized_prober_keeps_writing_into_the_LIVE_dict():
    """The same defect from the behaviour side: rebuild the prober the way a level change does, then keep
    clicking. The counts must keep landing on the policy, not on the orphan."""
    p = _drive(_policy("cl11-repar"), _board(), 12)
    p._reparameterize(_board())
    before = sum(p._click_branch.values())
    _drive(p, _board(), 12)
    assert sum(p._click_branch.values()) == before + 12, (before, p._click_branch)


# ---------------------------------------------------------------------------------------------------------------
# ★★★ THE POOL FLOOR: WHICH POOL IS THE UNTRIED BRANCH DRAINING? ★★★
# `untried_first` carried 96.3% of every click the agent made and was ITSELF one name over more than one cause.
# The pre-registered reading attributed that dominance to `refresh()` replenishing the queue -- an untested
# mechanism. The rival is a CODE FACT: `_new_prober` passes `grid_sweep(grid, n=8)` -- 64 blind lattice points --
# UNCONDITIONALLY, so every prober starts with a 64-88 target pool that `choose` must enumerate in full before any
# learned score is consulted. These tests pin the instrument that tells the two apart on a live sweep.
# See docs/tether/EVIDENCE_the_click_pool_floor.md.
# ---------------------------------------------------------------------------------------------------------------

def test_the_untried_branch_names_WHICH_POOL_it_is_draining():
    """The decomposition, at the floor. A board with four coloured cells gives perception a handful of centroids
    and the lattice gives 64 more; the first clicks must be charged to `untried_perceptual` (perception's points
    are admitted FIRST) and the branch must then move to `untried_sweep` -- never to one undifferentiated row."""
    p = _drive(_policy("cl11-prov"), _board(), 40)
    b = p._click_branch
    assert sum(b.values()) == 40, b
    assert b.get("untried_perceptual", 0) >= 1, b
    assert b.get("untried_sweep", 0) >= 1, b               # 40 steps out-runs the handful of centroids
    assert b.get("untried_perceptual", 0) < 40, b          # ... and does not out-run the lattice


def test_the_pool_counts_ADMISSIONS_and_closes_on_its_own_denominator():
    """The pool is a different denominator from the branch split -- targets admitted, not steps taken -- so it is
    a separate dict and it has its own identity: the two construction origins must sum to the targets actually
    admitted after de-dup. A lattice point that collided with a perceptual centroid must show as a de-dup, never
    as a double count."""
    p = _drive(_policy("cl11-pool"), _board(), 30)
    p._close_segment("death")
    dfn = summary(p.receipts)["decide_funnel"]
    cpl = dfn["click_pool"]
    assert cpl["ctor_probers"] == 1, cpl
    assert cpl["ctor_sweep"] > 0 and cpl["ctor_perceptual"] > 0, cpl
    assert cpl["ctor_targets"] == cpl["ctor_perceptual"] + cpl["ctor_sweep"], cpl
    assert dfn["click_pool_ctor_residue"] == 0, dfn
    assert cpl["refresh_calls"] >= 1, cpl                  # `_act_click` refreshes on every step after the first
    # THE FLOOR ITSELF: the construction pool is >= 64 lattice points, so a 30-step run cannot possibly have
    # drained it -- which is exactly why `exploit_scored` is unreachable on short click games.
    assert cpl["ctor_targets"] >= 64, cpl
    assert p._click_branch.get("exploit_scored", 0) == 0, p._click_branch


def test_refresh_admissions_are_drained_LAST_which_is_what_makes_the_split_a_decomposition():
    """The code fact the whole reading rests on. `choose` picks `untried[0]` and `self.targets` is in ADMISSION
    order, so a refresh-admitted target cannot be reached until every construction target has been tried once.
    Built directly on the prober -- one perceptual point, one lattice point, then a refresh arrival."""
    from newhorse.redux_arch.click import ClickProber
    b = {}
    pr = ClickProber([(1, 1)], sweep=[(5, 5)], branch=b, pool={})
    pr.refresh([(9, 9)])
    g0, g1 = np.zeros((10, 10), dtype=int), np.ones((10, 10), dtype=int)
    picks = []
    for i in range(3):
        picks.append(pr.choose())
        pr.observe(g0 if i % 2 else g1, g1 if i % 2 else g0)
    assert picks == [(1, 1), (5, 5), (9, 9)], picks
    assert b == {"untried_perceptual": 1, "untried_sweep": 1, "untried_refresh": 1}, b


def test_the_pool_dict_survives_a_segment_boundary_like_the_branch_dict_does():
    """Same reference discipline, same failure mode. The prober outlives the segment and holds a reference to the
    pool dict; if `_close_segment` REBOUND it the refresh admissions of every segment after the first would be
    written into an orphan and printed as a zero."""
    p = _drive(_policy("cl11-poolseg"), _board(), 15)
    p._close_segment("death")
    assert p._click_pool == {}, p._click_pool
    _drive(p, _board(), 15)
    p._close_segment("death")
    assert p.receipts[-1].decide_click_pool.get("refresh_calls", 0) > 0, p.receipts[-1].decide_click_pool
    # no prober was REBUILT for the second segment, so the second receipt records refresh admissions and no
    # construction -- which is the point: `ctor_probers` counts constructions, not segments.
    assert p.receipts[-2].decide_click_pool.get("ctor_probers", 0) == 1, p.receipts[-2].decide_click_pool
