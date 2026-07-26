"""★★★ THE PRINTER GETS A TEST, BECAUSE THE PRINTER IS WHERE THE LIES HAVE BEEN. ★★★

Twice now a defect has reached a live sweep through `tools/sweep_chain.py` rather than through the agent: a
counter re-added to close an identity, and a field labelled `empty` that silently carried the `raised` count
(PATTERN 07-26e). Both were printer bugs, both cost a sweep to find, and neither could be caught by the suite
because the rendering lived inside `main()` behind a live session and an API key.

So the rendering is now `report(res)`, and this file drives it offline from REAL `summary()` / `echo_pool()`
output -- never a hand-written dict, which would only test that the printer agrees with my idea of the shape.

What is pinned here is the SELF-MOTION CONTROL's rendering, because the control's whole job is to refuse a
conclusion, and a control that renders its refusal wrong is worse than no control at all.
"""
import io
import sys
import contextlib

import numpy as np

from newhorse.redux_arch.policy import ReduxPolicy
from newhorse.redux_arch.receipt import summary
from newhorse.redux_arch.swarm import echo_pool, tether_distribution

sys.path.insert(0, "tools")


# Long enough that all four cycled actions clear the printer's own per-action floor (`sweep_chain._MIN_ACT_N`).
# Read from the printer rather than hard-coded: if someone raises the floor, these tests must keep testing the
# CLASSIFIER, not silently degrade into a second test of the floor. +2 covers the unpriced first step and the
# remainder of the rotation.
def _min_n():
    import sweep_chain
    return sweep_chain._MIN_ACT_N * 4 + 2


_N = _min_n()


def _policy(game_id):
    p = ReduxPolicy(game_id=game_id)
    p.frames = []
    return p


def _run(gid, n, movers, cycle=True):
    """Drive a real policy on a board that answers ONLY when the emitted action is in `movers`. `movers=None`
    means the board answers EVERY step no matter what was sent -- the self-motion case this control exists for.

    `cycle` replaces the DECISION with a stub that rotates the four actions through one named exit. The real
    decision path is exercised by `tests/test_gamma_directive.py`; what is under test HERE is the classifier, and
    the real path settles on a single action within a few steps (`family_effect` picks the best-effect one), which
    is a MUTE row by design and cannot distinguish the two boards. Using it here would test the floor, not the
    classifier. The stub still counts itself at `_exit` and still increments the funnel denominator, so every
    identity the printer checks stays true."""
    p = _policy(gid)
    if cycle:
        labels = ["A1", "A2", "A3", "A4"]

        def _stub():
            p._dec_calls += 1
            return p._exit("stub_exit", (labels[p.n_emitted % len(labels)], None))
        p._decide = _stub
    g = np.zeros((20, 20), dtype=int)
    g[3, 3], g[3, 4] = 4, 5
    tick = 0
    for _ in range(n):
        p.observe(g.copy(), [1, 2, 3, 4], 0)
        lbl, _d = p.choose()
        if movers is None or lbl in movers:
            tick += 1
            g[9:11, 9:11] = tick % 5 + 1               # four interior cells, where a budget band cannot reach
    p._close_segment("death")
    return p


def _res(**games):
    results = {}
    for gid, p in games.items():
        results[gid] = {"game": gid, "echo": summary(p.receipts), "family": "DIRECTIONAL", "levels": 1,
                        "tether_stage": {"stalls": 1, "advances": 0, "furthest_stage": "MINT_UNFIRED",
                                         "counts": {"MINT_UNFIRED": 1}},
                        "firings": []}
    pooled = echo_pool(results)
    return dict(view_url=None, scorecard_id=None, results=results, families={},
                total_levels=len(results), tether_chain=dict(tether_distribution(results), **pooled))


def _render(res):
    import sweep_chain
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sweep_chain.report(res)
    return buf.getvalue()


def _section(out, title):
    lines = out.splitlines()
    i = next(k for k, l in enumerate(lines) if title in l)
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("===") or lines[k].startswith("\n===")),
             len(lines))
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("=== ")), len(lines))
    return "\n".join(lines[i:j])


def test_the_report_renders_at_all_without_a_live_session():
    """The floor: every block in the printer survives a result dict built from real receipts. This is the test
    that would have cost nothing and saved two sweeps."""
    out = _render(_res(aa11=_run("aa11-aaaa", 10, ("A1",))))
    for title in ("=== DECIDE FUNNEL", "=== THE MEMBERS BEHIND EACH POOLED RATE",
                  "=== THE SELF-MOTION CONTROL", "=== FIRING RECEIPTS"):
        assert title in out, (title, out)


def test_a_board_that_answers_only_ONE_action_renders_as_ACTION_CONDITIONAL():
    """The good case, and the one that lets a rate be cited: the change tracks WHICH action was sent, so it is the
    agent's doing. The printer must say that in the classifier line, not merely print the numbers and leave the
    reader to conclude it."""
    out = _section(_render(_res(aa11=_run("aa11-aaaa", _N, ("A1",)))), "=== THE SELF-MOTION CONTROL")
    assert "ACTION-CONDITIONAL" in out, out
    assert "CONSISTENT WITH SELF-MOTION" not in out, out


def test_a_board_that_answers_EVERY_action_renders_as_CONSISTENT_WITH_SELF_MOTION():
    """The case the three 100%/100% carriers are suspected of. The board here changes every step regardless of
    what was sent, so every action reads 100% -- exactly what a competent agent looks like through the outcome
    column alone. The classifier must refuse the competence reading, and must refuse it in words: `UNIFORM and
    HIGH ... may not be cited as competence`. A printer that rendered this as a good score is the whole failure
    this beat exists to prevent."""
    out = _section(_render(_res(bb22=_run("bb22-bbbb", _N, None))), "=== THE SELF-MOTION CONTROL")
    assert "CONSISTENT WITH SELF-MOTION" in out, out
    assert "may not be cited as competence" in out, out
    assert "ACTION-CONDITIONAL" not in out, out


def test_the_two_cases_are_told_APART_in_ONE_sweep():
    """Both games in one report. If the classifier were reading the pooled number, or the last game seen, the two
    rows would agree -- and a control that cannot separate these two boards in the same run could never have
    separated them across a real sweep either."""
    out = _section(_render(_res(aa11=_run("aa11-aaaa", _N, ("A1",)), bb22=_run("bb22-bbbb", _N, None))),
                   "=== THE SELF-MOTION CONTROL")
    rows = [l for l in out.splitlines() if "->" in l]
    assert any("ACTION-CONDITIONAL" in l for l in rows), out
    assert any("CONSISTENT WITH SELF-MOTION" in l for l in rows), out
    # and the two verdicts are on DIFFERENT game rows, never one row carrying both readings
    assert not any("ACTION-CONDITIONAL" in l and "CONSISTENT WITH SELF-MOTION" in l for l in rows), out


def test_a_single_action_game_renders_MUTE_rather_than_a_verdict():
    """The control's honest failure mode, published rather than rounded. With one action there is nothing for the
    split to vary over, so it rules nothing out -- and a printer that let that render as `UNIFORM and HIGH` would
    be manufacturing a self-motion finding out of an absence of evidence, which is the mirror image of the defect
    it is here to catch."""
    p = _policy("cc33-cccc")
    g = np.zeros((20, 20), dtype=int)
    g[3, 3], g[3, 4] = 4, 5
    for i in range(9):
        p.observe(g.copy(), [1], 0)                   # ONE available action: every step is A1
        p.choose()
        g[9:11, 9:11] = i % 5 + 1
    p._close_segment("death")
    out = _section(_render(_res(cc33=p)), "=== THE SELF-MOTION CONTROL")
    assert "MUTE: one action only" in out, out
    assert "CONSISTENT WITH SELF-MOTION" not in out, out


def _relabel_to_lockin(p):
    """THE CLASSIFIER OUTLIVES THE STATE IT WAS BUILT FOR. The release shipped this beat means no live policy can
    produce a `hold_answered`-dominated receipt any more -- the directional case is handed back on its first
    answer and A6 is caught by the click exit. That is exactly why the LOCK-IN verdict must STAY in the printer:
    it is the guard that would catch the state coming back by some other path, and a guard is worth nothing if
    nothing ever tests it.

    So the state is now built where it honestly belongs -- on the RECEIPT, by relabelling counted steps, not by
    inventing them. The step totals and the escalate exits are untouched, so the identity still closes; only the
    branch NAME moves. This is a synthetic receipt and is labelled as one; no number here may be cited about the
    agent."""
    for ev in p.receipts:
        b = ev.decide_esc_branch
        if b.get("hold_untried"):
            b["hold_answered"] = b.get("hold_answered", 0) + b.pop("hold_untried")
    return p


def _escalating(gid, n_frozen, n_answer, avail=(1, 2, 3, 4, 6), lockin=False):
    """A real policy driven into the escalation organ, for the printer's branch block. `lockin` constructs the
    directional held state (see tests/test_escalation_branch.py for why that state is constructed and not driven);
    since the release shipped it no longer HOLDS, so the printer's LOCK-IN verdict is fed by `_relabel_to_lockin`
    instead and this flag now drives the RELEASE path."""
    from newhorse.redux_arch.policy import EFFECT
    p = _policy(gid)
    if lockin:
        p.family, p._escalated = EFFECT, "A1"
        avail = (1, 2, 3, 4)
    g = np.zeros((20, 20), dtype=int)
    g[3, 3], g[3, 4] = 4, 5
    tick = 0
    for i in range(n_frozen + n_answer):
        p.observe(g.copy(), list(avail), 0)
        p.choose()
        if i >= n_frozen:
            tick += 1
            g[9:11, 9:11] = tick % 5 + 1
    p._close_segment("death")
    return p


def test_the_escalation_branch_block_renders_and_CLOSES():
    """The identity first: the branch counts are written at three returns inside `_modality_escalate` and the
    exit counts at two returns inside `_decide`. If those two independent counters of the same steps disagree,
    the printer must say so and every row above becomes uncitable. A block that renders a residue as silence is
    the printer defect this file exists to catch."""
    out = _section(_render(_res(aa11=_escalating("aa11-aaaa", 20, 0))), "=== THE ESCALATION BRANCH")
    assert "RESIDUE=0" in out, out
    assert "DOES NOT SUM" not in out, out
    for row in ("new", "hold_untried", "hold_answered"):
        assert row in out, out


def test_a_fair_trial_wait_and_a_LOCK_IN_render_as_DIFFERENT_verdicts():
    """The classifier's whole job. A frozen board pays the BOUNDED cost of confirming a negative -- that is the
    organ working, and the printer must not call it a defect. A held label that has already answered can never
    end its own trial (`best` is a max), and the printer must not let that read as the same thing."""
    wait = _section(_render(_res(aa11=_escalating("aa11-aaaa", 20, 0))), "=== THE ESCALATION BRANCH")
    assert "FAIR-TRIAL WAIT DOMINATES" in wait, wait
    assert "LOCK-IN DOMINATES" not in wait, wait
    lock = _section(_render(_res(bb22=_relabel_to_lockin(_escalating("bb22-bbbb", 20, 0)))),
                    "=== THE ESCALATION BRANCH")
    assert "LOCK-IN DOMINATES" in lock, lock
    assert "FAIR-TRIAL WAIT DOMINATES" not in lock, lock
    assert "RESIDUE=0" in lock, lock                   # the relabel moved a name, not a count


def test_the_printer_renders_the_hand_back_the_release_produces():
    """The release's own row. A branch that produces NO step would be invisible in a block whose every other row
    is priced as a share of escalate steps, and an organ change you cannot see in the report is one you cannot
    check next sweep. The row must appear, must be marked as producing no step, and must NOT be counted into the
    identity -- the residue is what makes every other row in the block citable."""
    out = _section(_render(_res(bb22=_escalating("bb22-bbbb", 0, 60, lockin=True))), "=== THE ESCALATION BRANCH")
    assert "released_answered" in out, out
    assert "NO step" in out, out
    assert "RESIDUE=0" in out, out
    assert "DOES NOT SUM" not in out, out
