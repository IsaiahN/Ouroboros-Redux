"""★★★ MINTED_UNUSED, ATTRIBUTED: THE ONE CODE THAT INDICTS THE ARCHITECTURE HAS NEVER NAMED A BRANCH. ★★★

`MINTED_UNUSED` means "a residual was computed, a φ was minted, reuse was attempted, and the library did not
explain". That sentence has carried the whole architecture claim for thirteen beats and it names no branch. An
offer to Γ can come out four different ways, and they are not the same finding:

  explains_no_exceptions  the residual was empty -- unreachable from the live site, named so nobody can hide there
  explains_already_pure   the residual had one outcome; nothing for any predicate to split -- likewise
  explains_no_eligible    NO promoted φ even non-trivially SPLITS these contexts. Γ never took the field. This is a
                          GRAIN/applicability verdict and it is NOT a verdict on the architecture.
  explains_no_compress    eligible φ existed and none paid its own cost + log2(eligible). Γ was tested and LOST --
                          the only reading MINTED_UNUSED has ever claimed to be.
  explains_transfer       a φ compressed the fresh residual: reuse.

and at the second attempt site, `policy._gamma_directive`, four more: `dir_no_evaluable` (no label had an
evaluable context -- a seam failure), `dir_no_endorsement` (Γ scored nothing positive -- the sign said nothing),
`dir_tie` (two candidates tied; Γ is refused the pick), `dir_acted`.

★ PRE-REGISTERED PREDICTION (written before the sweep that reads it, and evaluated by `tools/sweep_chain.py`
itself, not by prose afterwards): `explains_no_eligible` DOMINATES and the directive site contributes ZERO
attempts. If that holds, thirteen beats of ARCHITECTURE reporting have been a GRAIN stall wearing an architecture
name. If `explains_no_compress` dominates instead, the architecture reading survives its first real test and the
next beat is about the MDL bar. NOTHING is widened this beat either way -- this file pins an instrument, and the
last three tests are the ones that prove it is only an instrument.

WHAT THESE TESTS DELIBERATELY DO NOT ASSERT: any live count, rate or dominance. That is a measurement and it
belongs to the sweep. A unit test that pinned which branch wins would be an answer key, and it would make the
prediction unfalsifiable by construction.
"""
from __future__ import annotations

import os
import re

import numpy as np

from newhorse.redux_arch.abort_code import ChainLedger, Stage
from newhorse.redux_arch.consolidate import Consolidator
from newhorse.redux_arch.dsl import Context, Predicate, make_atom
from newhorse.redux_arch.minting import Mint
from newhorse.redux_arch.policy import ReduxPolicy
from newhorse.redux_arch.receipt import ResidualEvent, _reuse_funnel, summary

SRC = os.path.join(os.path.dirname(__file__), "..", "src", "newhorse", "redux_arch")

FREE = Predicate(frozenset({make_atom("INTENDED_FREE")}))
ROW = Predicate(frozenset({make_atom("SAME_ROW")}))
NEAR = Predicate(frozenset({make_atom("NEAR")}))

# The nine literals, in one place. A branch that is not on this list is a `return` that was added without a
# reading, and the sweep printer flags it as UNNAMED for exactly that reason.
NAMED = ("explains_no_exceptions", "explains_already_pure", "explains_no_eligible", "explains_no_compress",
         "explains_transfer", "dir_no_evaluable", "dir_no_endorsement", "dir_tie", "dir_acted")


def _ctx(free: bool, colour: int = 4, same_row: bool = False, near: bool = False) -> Context:
    fr, fc = 2, 2
    tr = fr if same_row else fr + 4
    tc = fc + 4
    if near:
        tr, tc = fr, fc + 1
    return Context(focus_rc=(fr, fc), focus_colour=colour, target_rc=(tr, tc), action_vec=(0, 1),
                   intended_free=free, intended_colour=(None if free else colour))


def _evidence(n: int = 8):
    """n exceptions whose OUTCOME is exactly INTENDED_FREE, so FREE explains them perfectly. `same_row` cycles on
    a different period, so ROW is ELIGIBLE (it splits the contexts) without being any good at the outcome."""
    return [(_ctx(free=(i % 2 == 0), same_row=(i % 3 == 0)), i % 2 == 0) for i in range(n)]


class _Pen:
    """A recording stand-in for `ChainLedger.note_reuse_exit`, used ONLY where the ledger itself is not the
    subject. Where the ledger IS the subject the real bound method is passed, because the thing being pinned is
    that the count lands in the ledger and not in some second carrier."""

    def __init__(self):
        self.names = []

    def __call__(self, name):
        self.names.append(name)


# --------------------------------------------------------------------------------------------------------------
# 1. EVERY WAY OUT OF THE OFFER SITE WRITES ITS OWN LITERAL AT ITS OWN BRANCH.
# --------------------------------------------------------------------------------------------------------------
def test_an_empty_residual_and_a_pure_one_are_named_apart_even_though_the_live_site_reaches_neither():
    """Both return None with nothing to explain, and both are unreachable from `_residual_pass` (which returns
    early unless `n >= 2 and base > 0`). They are named anyway: an unreachable branch with no literal is a place a
    future caller can land silently, and the residue would then close by accident."""
    p1, p2 = _Pen(), _Pen()
    Consolidator(echo_threshold=2).explains_scored([], branch=p1)
    con = Consolidator(echo_threshold=2)
    con.library.append(FREE)
    con.explains_scored([(_ctx(True), True), (_ctx(False), True)], branch=p2)   # one outcome -> base == 0
    assert p1.names == ["explains_no_exceptions"]
    assert p2.names == ["explains_already_pure"]


def test_no_eligible_and_no_compress_are_the_two_readings_the_bare_count_conflated():
    """THE WHOLE POINT OF THE FUNNEL. An EMPTY library and a library holding a φ that splits the contexts but
    cannot pay for itself both returned None and both were counted as MINTED_UNUSED. One says Γ was never
    applicable (grain); the other says Γ competed and lost (architecture). Different names, different fixes."""
    ev = _evidence(8)
    empty, useless = _Pen(), _Pen()
    Consolidator(echo_threshold=2).explains_scored(ev, branch=empty)
    con = Consolidator(echo_threshold=2)
    con.library.append(ROW)                              # splits the CONTEXTS, is worthless on the OUTCOME
    con.explains_scored(ev, branch=useless)
    assert empty.names == ["explains_no_eligible"]
    assert useless.names == ["explains_no_compress"]


def test_a_library_predicate_that_does_not_split_these_contexts_is_no_eligible_not_no_compress():
    """A NON-EMPTY library can still be inapplicable. `NEAR` is false in every context here, so it never enters
    `eligible` and Γ is not on trial -- and the funnel must say so, or a non-empty library would make every stall
    read as an architecture failure merely by existing."""
    pen = _Pen()
    con = Consolidator(echo_threshold=2)
    con.library.append(NEAR)
    assert con.explains_scored(_evidence(8), branch=pen) is None
    assert pen.names == ["explains_no_eligible"]


def test_a_transfer_is_named_at_its_own_return_too():
    pen = _Pen()
    con = Consolidator(echo_threshold=2)
    con.library.append(FREE)
    assert con.explains_scored(_evidence(8), branch=pen) is not None
    assert pen.names == ["explains_transfer"]


def test_exactly_one_literal_is_written_per_call_on_every_path():
    """The identity `sum(branch) == attempts` is only meaningful if each attempt writes ONE name. A path writing
    two would close the residue while double-counting, which is the worse failure: it looks correct."""
    cases = [(Consolidator(echo_threshold=2), []),
             (Consolidator(echo_threshold=2), _evidence(8)),
             (_lib(FREE), _evidence(8)),
             (_lib(ROW), _evidence(8)),
             (_lib(NEAR), _evidence(8))]
    for con, ev in cases:
        pen = _Pen()
        con.explains_scored(ev, branch=pen)
        assert len(pen.names) == 1, pen.names
        assert pen.names[0] in NAMED


def _lib(*preds) -> Consolidator:
    c = Consolidator(echo_threshold=2)
    c.library.extend(preds)
    return c


# --------------------------------------------------------------------------------------------------------------
# 2. THE PEN IS THE LEDGER'S OWN BOUND METHOD, AND THE COUNT LANDS IN THE LEDGER.
# --------------------------------------------------------------------------------------------------------------
def test_the_count_lands_in_the_ledger_because_the_ledger_wrote_it_itself():
    """RANKING 1: a chain signal must be emitted into `ChainLedger` FROM ITS REAL CALL SITE, never derived from
    another organ. Passing the bound method means there is no second carrier at all -- the defect that made the
    click branch read RESIDUE=126 for a beat was a carrier with two construction sites, one of them orphaned."""
    led = ChainLedger()
    con = _lib(ROW)
    led.note_reuse_attempt()
    con.explains_scored(_evidence(8), branch=led.note_reuse_exit)
    assert led.reuse_attempts == 1
    assert dict(led.reuse_branch) == {"explains_no_compress": 1}
    assert led.reuse_attempts_in_segment == 1
    assert led.reuse_branch_in_segment == {"explains_no_compress": 1}


def test_every_explains_scored_call_site_in_policy_passes_the_pen():
    """THE ORPHAN-HAZARD TEST. A second offer site added without `branch=` would be an attempt with no branch: the
    residue would go non-zero and the sweep printer would refuse to read the rows -- but only after a 20-minute
    sweep. This catches it at import time instead."""
    src = open(os.path.join(SRC, "policy.py")).read()
    sites = re.findall(r"explains_scored\((?:[^()]|\([^()]*\))*\)", src)
    assert sites, "the offer site vanished -- the funnel is measuring nothing"
    for s in sites:
        assert "branch=" in s, "an offer site with no pen: %s" % s


def test_the_run_total_never_resets_but_the_segment_tally_does():
    """Scoping is load-bearing in both directions. The SEGMENT tally must reset or one segment's failures get
    charged to the next segment's stage -- the exact defect `_sig` is scoped to avoid. The RUN total must not, or
    the sweep-level denominator would count only the last segment."""
    led = ChainLedger()
    led.note_step()
    led.note_reuse_attempt()
    led.note_reuse_exit("explains_no_eligible")
    led.end_segment("death")
    assert led.reuse_attempts == 1                       # run-level survives
    assert dict(led.reuse_branch) == {"explains_no_eligible": 1}
    assert led.reuse_attempts_in_segment == 0            # segment-level does not
    assert led.reuse_branch_in_segment == {}
    led.note_step()
    led.note_reuse_attempt()
    led.note_reuse_exit("explains_no_compress")
    assert led.reuse_attempts == 2
    assert led.reuse_branch_in_segment == {"explains_no_compress": 1}


def test_the_report_publishes_the_residue_rather_than_assuming_it():
    led = ChainLedger()
    led.note_reuse_attempt()
    led.note_reuse_attempt()
    led.note_reuse_exit("explains_no_eligible")
    rep = led.report()
    assert rep["reuse_attempts"] == 2
    assert rep["reuse_residue"] == 1                     # an attempt that reached no branch -- and it SAYS so
    led.note_reuse_exit("explains_no_eligible")
    assert led.report()["reuse_residue"] == 0


# --------------------------------------------------------------------------------------------------------------
# 3. THE SEGMENT CARRY IS READ BEFORE THE CLOSE, AND LANDS ON THE SAME ROW AS THE STAGE.
# --------------------------------------------------------------------------------------------------------------
def _board(h=7, w=7):
    g = np.zeros((h, w), dtype=int)
    g[3, 3] = 4
    g[3, 4] = 5
    return g


def test_the_receipt_carries_the_segment_tally_and_the_stage_on_one_row():
    """READ-BEFORE-CLOSE. `end_segment` zeroes the tally; reading after it would stamp a measured zero on every
    receipt -- a field never computed, printed as evidence (RANKING 5). This drives the real `_close_segment`."""
    p = ReduxPolicy(game_id="rf01-aaaa")
    p.frames = [_board()]
    p.chain.note_step()
    p.chain.note_reuse_attempt()
    p.chain.note_reuse_exit("explains_no_eligible")
    p.chain.note_reuse_exit("explains_no_compress")      # two branches, one segment
    p._close_segment("death")
    ev = p.receipts[-1]
    assert ev.reuse_attempts == 1
    assert ev.reuse_branch == {"explains_no_compress": 1, "explains_no_eligible": 1}
    assert ev.stage is not None                          # the stage and its branches are on the SAME receipt
    assert p.chain.reuse_attempts_in_segment == 0        # ...and the ledger moved on


def test_a_second_segment_is_not_charged_the_first_segments_branches():
    p = ReduxPolicy(game_id="rf02-aaaa")
    p.frames = [_board()]
    p.chain.note_step()
    p.chain.note_reuse_attempt()
    p.chain.note_reuse_exit("explains_no_eligible")
    p._close_segment("death")
    p.chain.note_step()
    p._close_segment("death")
    assert p.receipts[-2].reuse_branch == {"explains_no_eligible": 1}
    assert p.receipts[-1].reuse_attempts == 0
    assert p.receipts[-1].reuse_branch == {}


# --------------------------------------------------------------------------------------------------------------
# 4. THE CROSS-TAB IS A READING OF ONE ROW, NEVER A JOIN BETWEEN TWO ORGANS.
# --------------------------------------------------------------------------------------------------------------
def _ev(stage, branch, game="g1"):
    e = ResidualEvent(game=game, level=0, segment=0, reason="death")
    e.stage = stage
    e.reuse_branch = dict(branch)
    e.reuse_attempts = sum(branch.values())
    return e


def test_by_stage_takes_the_stage_and_the_branch_off_the_same_receipt():
    """A pooled branch count says how the sweep's offers came out; it says NOTHING about the segments scored
    MINTED_UNUSED, and a pooled number offered as evidence about a subset is a mis-labelled receipt one level up.
    The cross-tab answers WHICH MEMBERS -- and it can only do that if no segment's branches can be charged to
    another segment's stage, which is what keying off each receipt's own two fields guarantees."""
    evs = [_ev("MINTED_UNUSED", {"explains_no_eligible": 3}),
           _ev("USED_NOCLEAR", {"explains_transfer": 1, "explains_no_eligible": 1}),
           _ev("MINT_UNFIRED", {"explains_no_compress": 2})]
    f = _reuse_funnel(evs)
    assert f["attempts"] == 7
    assert f["branch"] == {"explains_no_compress": 2, "explains_no_eligible": 4, "explains_transfer": 1}
    assert f["residue"] == 0
    assert f["by_stage"]["MINTED_UNUSED|explains_no_eligible"] == 3
    assert f["by_stage"]["USED_NOCLEAR|explains_no_eligible"] == 1
    assert "MINTED_UNUSED|explains_no_compress" not in f["by_stage"]
    assert sum(f["by_stage"].values()) == sum(f["branch"].values())


def test_an_unscored_segment_is_named_not_dropped():
    """A segment that ended in an ADVANCE is deliberately unscored, and a receipt filed before the ledger returned
    a stage has no stage either. Dropping those rows would be a residue that closes itself -- the cross-tab would
    balance because the missing rows were never counted on either side."""
    f = _reuse_funnel([_ev(None, {"explains_no_eligible": 2})])
    assert f["by_stage"] == {"UNSCORED|explains_no_eligible": 2}
    assert f["residue"] == 0


def test_the_residue_goes_nonzero_when_an_attempt_reached_no_branch():
    e = _ev("MINTED_UNUSED", {"explains_no_eligible": 1})
    e.reuse_attempts = 3                                 # two attempts that never named a branch
    f = _reuse_funnel([e])
    assert f["residue"] == 2


def test_no_by_stage_residue_is_published_because_it_could_never_fail_here():
    """An identity that cannot fail is decoration, not a check: inside `_reuse_funnel` every branch write also
    writes a by_stage row, so the two sums are equal BY CONSTRUCTION. The residue worth printing crosses the
    POOLING boundary and `tools/sweep_chain.py` computes it there, from the two pooled dicts. A producer field
    that can only ever read 0 is precisely 'a field never COMPUTED, printed as a zero'."""
    assert "by_stage_residue" not in _reuse_funnel([_ev("MINTED_UNUSED", {"explains_no_eligible": 1})])
    printer = open(os.path.join(os.path.dirname(__file__), "..", "tools", "sweep_chain.py")).read()
    assert "by_stage_residue" not in printer, "the printer is reading a field the producer no longer emits"


def test_summary_publishes_the_funnel_as_a_sibling_of_the_decide_funnel():
    s = summary([_ev("MINTED_UNUSED", {"explains_no_eligible": 2})])
    assert s["reuse_funnel"]["attempts"] == 2
    assert s["reuse_funnel"]["branch"] == {"explains_no_eligible": 2}


# --------------------------------------------------------------------------------------------------------------
# 5. IT IS AN INSTRUMENT: NOTHING READS IT, AND NOTHING ABOUT THE AGENT CHANGED.
# --------------------------------------------------------------------------------------------------------------
def test_the_pen_does_not_change_what_the_scorer_returns():
    """THE SINK TEST. If writing a name could change a verdict, the funnel would be part of the mechanism and
    every number it reports would be about itself."""
    for lib in ([], [FREE], [ROW], [NEAR], [FREE, ROW, NEAR]):
        ev = _evidence(8)
        a = _lib(*lib).explains_scored(ev)
        b = _lib(*lib).explains_scored(ev, branch=_Pen())
        assert (a is None) == (b is None)
        if a is not None:
            assert a[0] == b[0] and abs(a[1] - b[1]) < 1e-12


def test_the_directive_site_returns_the_same_thing_it_did_before_the_split():
    """`_gamma_directive`'s three-clause `or` became four named branches in the ORIGINAL short-circuit order, so
    what the agent DOES is bit-identical. With an empty Γ the honest answer is still None, and -- because an empty
    library is not an offer -- no attempt and no branch may be recorded either."""
    p = ReduxPolicy(game_id="rf03-aaaa")
    p.frames = [_board()]
    p.cursor = 4
    p.vecs = {"A1": (-1, 0), "A2": (1, 0), "A3": (0, -1), "A4": (0, 1)}
    p.passable = {0}
    p.stride = 1
    assert p._gamma_directive(["A1", "A2", "A3", "A4"]) is None
    assert p.chain.reuse_attempts == 0
    assert dict(p.chain.reuse_branch) == {}


def test_no_decision_path_reads_the_funnel():
    """BANK EVIDENCE, NEVER CONCLUSIONS. The moment an organ branches on `reuse_branch`, the agent is being
    steered by its own instrument and the sweep is measuring a feedback loop. Only the ledger that owns the
    counters, the receipt that files them and the policy line that copies them onto the receipt may name them."""
    allowed = {"abort_code.py", "receipt.py"}
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".py") or fn in allowed:
            continue
        src = open(os.path.join(SRC, fn)).read()
        for i, line in enumerate(src.splitlines(), 1):
            if "reuse_branch" not in line and "reuse_attempts" not in line:
                continue
            code = line.split("#")[0]
            if "reuse_branch" not in code and "reuse_attempts" not in code:
                continue                                 # a comment may discuss it; only code is the hazard
            assert fn == "policy.py" and ("ev.reuse_" in code or "seg_att" in code or "seg_reuse" in code), \
                "%s:%d reads the reuse funnel outside the carry: %s" % (fn, i, line.strip())


def test_every_literal_written_anywhere_in_the_source_is_on_the_named_list():
    """An UNNAMED branch is a `return` added without a reading. The sweep printer flags it, but only after a
    sweep; this catches it at import time, and it is the reason the printer's legend and this list are the same
    nine strings."""
    for fn in ("policy.py", "consolidate.py"):
        src = open(os.path.join(SRC, fn)).read()
        for name in re.findall(r'_b\("([a-z_]+)"\)|note_reuse_exit\("([a-z_]+)"\)', src):
            got = name[0] or name[1]
            assert got in NAMED, "%s writes an unnamed branch %r" % (fn, got)
