"""★★★ MINTED_UNUSED, ATTRIBUTED: THE ONE CODE THAT INDICTS THE ARCHITECTURE HAS NEVER NAMED A BRANCH. ★★★

`MINTED_UNUSED` means "a residual was computed, a φ was minted, reuse was attempted, and the library did not
explain". That sentence has carried the whole architecture claim for thirteen beats and it names no branch. An
offer to Γ can come out four different ways, and they are not the same finding:

  explains_no_exceptions  the residual was empty -- unreachable from the live site, named so nobody can hide there
  explains_already_pure   the residual had one outcome; nothing for any predicate to split -- likewise
  explains_no_eligible_*  NO promoted φ even non-trivially SPLITS these contexts. Γ never took the field. This is a
                          GRAIN/applicability verdict and it is NOT a verdict on the architecture. ★ AND IT IS
                          ITSELF AN EXIT NAME SPANNING MORE THAN ONE STATE, which is why it now resolves at four
                          separate returns: `_empty` (Γ's library is empty -- unreachable from the live site, which
                          guards on Γ, and named so nobody can hide there), `_absent` (every rejected φ held on NO
                          fresh context: the vocabulary does not describe this board, so the fix is GRAIN, at link
                          1), `_universal` (every rejected φ held on EVERY fresh context: true but vacuous, so the
                          fix is UPSTREAM in whatever built contexts that do not vary), `_mixed` (both kinds were
                          present). Exhaustive and exclusive because `any(h) and not all(h)` is false exactly when
                          `not any(h)` or `all(h)` -- no threshold decides which, because a threshold is a name
                          somebody chose and that is the defect this funnel exists to undo.
  explains_no_compress    eligible φ existed and none paid its own cost + log2(eligible). Γ was tested and LOST --
                          the only reading MINTED_UNUSED has ever claimed to be.
  explains_transfer       a φ compressed the fresh residual: reuse.

A SECOND, FINER COUNTER rides alongside: `note_no_eligible_phi` tallies `phi_absent` / `phi_universal` ONCE PER φ
SCANNED, at the eligibility loop. Its denominator is the library scan, not the attempt, so it is published as a
bare split and is deliberately NOT part of the `sum(branch) == attempts` identity -- adding a per-φ count to a
per-attempt count would close the residue on the right total for the wrong reason, invisibly.

and at the second attempt site, `policy._gamma_directive`, four more: `dir_no_evaluable` (no label had an
evaluable context -- a seam failure), `dir_no_endorsement` (Γ scored nothing positive -- the sign said nothing),
`dir_tie` (two candidates tied; Γ is refused the pick), `dir_acted`.

★ PRE-REGISTERED PREDICTION (written before the sweep that reads it, and evaluated by `tools/sweep_chain.py`
itself, not by prose afterwards): `explains_no_eligible` DOMINATES and the directive site contributes ZERO
attempts. If that holds, thirteen beats of ARCHITECTURE reporting have been a GRAIN stall wearing an architecture
name. If `explains_no_compress` dominates instead, the architecture reading survives its first real test and the
next beat is about the MDL bar. NOTHING is widened this beat either way -- this file pins an instrument, and the
last three tests are the ones that prove it is only an instrument.

★ SECOND PRE-REGISTERED PREDICTION (written before the sweep that splits it, evaluated by the sweep printer):
`explains_no_eligible_absent` DOMINATES the four, and `phi_absent` dominates `phi_universal` in the per-φ tally.
That would say the promoted φ are simply NOT PRESENT off their home board -- the colour literals do not survive
the trip -- and the fix is grain, at link 1. `_universal` dominating instead would say the fresh contexts do not
vary, which points UPSTREAM into the residual builder and is a different repair entirely. `_mixed` dominating
says both are happening and neither repair can be attempted first without splitting further. Published whichever
way it lands, and nothing is widened on the strength of it.

★ THIRD PRE-REGISTERED PREDICTION (written before the sweep that reads it, evaluated by the sweep printer):
ABSENCE CONCENTRATES IN THE COLOUR VOCABULARY. `phi_absent` says a promoted φ did not fire on the board it was
carried to; it does not say WHICH PART of the vocabulary failed to travel, and the parts have different repairs.
A THIRD counter, `note_phi_kind`, rides on the SAME denominator as `note_no_eligible_phi` (one write per φ
rejected) in its OWN dict, and writes two orthogonal splits over the absent φ -- the COMPOSITION of the dead
predicate (`absent_kind_colour|relational|both|empty`) and the CAUSE of its death (`absent_cause_colour|
relational|both|none`, charged from each ATOM's own evaluation over the same contexts) -- plus `universal_kind_*`
as the base rate the absent split must be read against. Composition and cause are NOT the same claim: a
conjunction made of a colour literal and a relational atom can be absent because the RELATION never held, so the
composition row alone would name the wrong repair. The prediction is that
`absent_cause_colour + absent_cause_both` exceeds `absent_cause_relational + absent_cause_none`. If it holds, the
promoted palette is local to the board it was learned on and the grain repair is about WHICH ATOMS GET PROMOTED,
not about widening any gate. If `absent_cause_relational` dominates, the palette travels and the GEOMETRY does
not, and the repair is elsewhere. If `absent_cause_none` dominates, NEITHER vocabulary is missing: every atom is
alive and only the conjunction fails, so the repair is the ARITY of the predicate and not the atom registry at
all. All three are named in advance so none can be re-described afterwards as a partial success. Nothing is
widened on the strength of any of them: no atom, gate, threshold or detector is added, and nothing in the search
or the MDL score reads any of these rows.

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
# `_ctx` builds every context with focus_colour=4, so COL4 holds in ALL of them: TRUE and vacuous, the UNIVERSAL
# half of the old `explains_no_eligible`. NEAR is false in all of them (the focus is 4+ cells from the target
# unless `near=True`, which `_evidence` never sets): the ABSENT half. One library, two opposite diagnoses.
COL4 = Predicate(frozenset({make_atom("HAS_COLOUR", 4)}))

# The twelve literals, in one place. A branch that is not on this list is a `return` that was added without a
# reading, and the sweep printer flags it as UNNAMED for exactly that reason.
NAMED = ("explains_no_exceptions", "explains_already_pure", "explains_no_eligible_empty",
         "explains_no_eligible_absent", "explains_no_eligible_universal", "explains_no_eligible_mixed",
         "explains_no_compress", "explains_transfer", "dir_no_evaluable", "dir_no_endorsement", "dir_tie",
         "dir_acted")
# The four ways an attempt can end in "nothing in Γ was applicable". The sweep sums them where the old single
# `explains_no_eligible` used to be read, so the dominance question is asked of the same quantity as before.
NO_ELIGIBLE = tuple(n for n in NAMED if n.startswith("explains_no_eligible"))
# The per-φ literals. Different denominator (one write per library φ scanned, not per attempt) -- never summed
# into the branch tally, and every test below that touches both keeps them apart on purpose.
PHI_NAMED = ("phi_absent", "phi_universal")
# The vocabulary literals. SAME denominator as PHI_NAMED (one write per φ rejected), OWN dict -- because the sweep
# closes the φ dict by summing every key in it, and a refinement dropped into that bag would inflate the coarse
# total invisibly. Three families, each closing on its own subset: `absent_kind_*` and `absent_cause_*` each sum
# to the `phi_absent` count, `universal_kind_*` sums to the `phi_universal` count.
KIND_NAMED = ("absent_kind_colour", "absent_kind_relational", "absent_kind_both", "absent_kind_empty",
              "absent_kind_unregistered",
              "absent_cause_colour", "absent_cause_relational", "absent_cause_both", "absent_cause_none",
              "absent_cause_unregistered",
              "universal_kind_colour", "universal_kind_relational", "universal_kind_both",
              "universal_kind_empty", "universal_kind_unregistered")
# A colour the evidence never shows (every `_ctx` is colour 4), so this literal holds NOWHERE: the ABSENT half,
# and unlike NEAR it is absent because a GROUND-COLOUR atom is dead rather than a relational one.
COL7 = Predicate(frozenset({make_atom("HAS_COLOUR", 7)}))
# Composition `both`, cause RELATIONAL: colour 4 holds in every context, NEAR in none, so the conjunction is
# absent and the atom that killed it is the relational one. This pair is the whole reason cause is counted
# separately from composition -- reading the composition row alone would name the colour vocabulary here.
COL4_NEAR = Predicate(frozenset({make_atom("HAS_COLOUR", 4), make_atom("NEAR")}))
# Composition `both`, cause BOTH: neither atom holds anywhere.
COL7_NEAR = Predicate(frozenset({make_atom("HAS_COLOUR", 7), make_atom("NEAR")}))
# Composition `relational`, cause NONE: each atom is alive somewhere and they never co-occur (see `_split_ev`).
FREE_ROW = Predicate(frozenset({make_atom("INTENDED_FREE"), make_atom("SAME_ROW")}))


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


def _split_ev(n: int = 6):
    """Evidence in which INTENDED_FREE and SAME_ROW are alive but NEVER TOGETHER: the odd rows are free and not
    row-aligned, the even rows are row-aligned and not free. So `FREE ∧ ROW` holds on no context even though every
    one of its atoms holds on some context -- the INTERACTION absence, which is an arity fault, not a grain one.
    The outcome tracks `free`, so the residual is never pure."""
    return [(_ctx(free=(i % 2 == 1), same_row=(i % 2 == 0)), i % 2 == 1) for i in range(n)]


def _row_ev(n: int = 6):
    """Every context is row-aligned, so SAME_ROW holds EVERYWHERE: a relational atom on the UNIVERSAL side. The
    base rate has to be measurable on both families or 'absence concentrates in colour' is unreadable."""
    return [(_ctx(free=(i % 2 == 0), same_row=True), i % 2 == 0) for i in range(n)]


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
    assert empty.names == ["explains_no_eligible_empty"]
    assert useless.names == ["explains_no_compress"]


def test_a_library_predicate_that_does_not_split_these_contexts_is_no_eligible_not_no_compress():
    """A NON-EMPTY library can still be inapplicable. `NEAR` is false in every context here, so it never enters
    `eligible` and Γ is not on trial -- and the funnel must say so, or a non-empty library would make every stall
    read as an architecture failure merely by existing."""
    pen = _Pen()
    con = Consolidator(echo_threshold=2)
    con.library.append(NEAR)
    assert con.explains_scored(_evidence(8), branch=pen) is None
    assert pen.names == ["explains_no_eligible_absent"]


# --------------------------------------------------------------------------------------------------------------
# 1b. ...AND `explains_no_eligible` IS ITSELF SPLIT, BECAUSE ITS TWO HALVES HAVE OPPOSITE FIXES.
# --------------------------------------------------------------------------------------------------------------
def test_absent_and_universal_are_named_apart_because_one_fix_is_grain_and_the_other_is_upstream():
    """Both mean "no φ was eligible" and both used to write the same name. `NEAR` holds in NO context here -- the
    vocabulary does not describe this board, so the repair is at link 1, in perception's grain. `HAS_COLOUR 4`
    holds in EVERY context here -- it is true and vacuous, and what is broken is the contexts, upstream in the
    residual builder. Reporting one number over both would recommend the wrong repair half the time."""
    absent, universal = _Pen(), _Pen()
    assert _lib(NEAR).explains_scored(_evidence(8), branch=absent) is None
    assert _lib(COL4).explains_scored(_evidence(8), branch=universal) is None
    assert absent.names == ["explains_no_eligible_absent"]
    assert universal.names == ["explains_no_eligible_universal"]


def test_a_library_holding_both_kinds_is_mixed_and_no_threshold_decides_which():
    """When the library contains an absent φ AND a universal one, there is no fact of the matter about which
    "dominates" that is not a threshold somebody chose -- and a name somebody chose is the defect this whole
    funnel exists to undo (PATTERN 07-30). So the attempt-level branch says MIXED and refuses to pick, and the
    per-φ tally underneath carries the actual proportions on its own denominator."""
    pen = _Pen()
    assert _lib(NEAR, COL4).explains_scored(_evidence(8), branch=pen) is None
    assert pen.names == ["explains_no_eligible_mixed"]


def test_the_four_no_eligible_branches_are_exhaustive_and_exclusive_by_the_algebra_not_by_luck():
    """`any(h) and not all(h)` is false exactly when `not any(h)` or `all(h)`, and for a non-empty context list
    those two are mutually exclusive. So every library that yields no eligible φ lands in exactly one of empty /
    absent / universal / mixed -- there is no fifth state to add later and no attempt that can reach none."""
    ev = _evidence(8)
    for lib in ([], [NEAR], [COL4], [NEAR, COL4], [COL4, NEAR], [NEAR, NEAR], [COL4, COL4]):
        pen = _Pen()
        assert _lib(*lib).explains_scored(ev, branch=pen) is None
        assert len(pen.names) == 1 and pen.names[0] in NO_ELIGIBLE, pen.names


def test_the_per_phi_tally_counts_once_per_library_predicate_not_once_per_attempt():
    """DIFFERENT DENOMINATOR, ON PURPOSE. The branch pen writes ONE name per attempt; the φ pen writes one per φ
    scanned. Three ineligible φ in the library is one attempt and three φ writes, and the two counts must never be
    added together -- a per-φ count folded into a per-attempt sum would land on a plausible total for the wrong
    reason and would do it invisibly."""
    pen, phi = _Pen(), _Pen()
    assert _lib(NEAR, NEAR, COL4).explains_scored(_evidence(8), branch=pen, phi_branch=phi) is None
    assert pen.names == ["explains_no_eligible_mixed"]
    assert sorted(phi.names) == ["phi_absent", "phi_absent", "phi_universal"]


def test_an_eligible_predicate_writes_no_phi_literal_at_all():
    """The φ pen is charged at the REJECTION, so a φ that passes the eligibility test writes nothing. If it wrote
    anything the tally would stop being a reason-for-rejection and become a library census wearing that name."""
    pen, phi = _Pen(), _Pen()
    assert _lib(ROW).explains_scored(_evidence(8), branch=pen, phi_branch=phi) is None
    assert pen.names == ["explains_no_compress"]         # ROW split the contexts: eligible, and then it lost
    assert phi.names == []


def test_the_report_dict_carries_the_same_two_counts_the_phi_pen_wrote():
    """The offline attributor (`tools/replay_mint.py` pattern) reads `report`, the live chain reads the pen. If
    those two ever disagree the offline attribution is about a different run than the sweep is."""
    rep, phi = {}, _Pen()
    _lib(NEAR, COL4).explains_scored(_evidence(8), report=rep, phi_branch=phi)
    assert rep["n_eligible"] == 0 and rep["library_size"] == 2
    assert rep["n_phi_absent"] == phi.names.count("phi_absent") == 1
    assert rep["n_phi_universal"] == phi.names.count("phi_universal") == 1


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
    led.note_reuse_exit("explains_no_eligible_absent")
    led.note_no_eligible_phi("phi_absent")
    led.end_segment("death")
    assert led.reuse_attempts == 1                       # run-level survives
    assert dict(led.reuse_branch) == {"explains_no_eligible_absent": 1}
    assert dict(led.no_eligible_phi) == {"phi_absent": 1}
    assert led.reuse_attempts_in_segment == 0            # segment-level does not
    assert led.reuse_branch_in_segment == {}
    assert led.no_eligible_phi_in_segment == {}          # ...and the per-φ tally is scoped the same way
    led.note_step()
    led.note_reuse_attempt()
    led.note_reuse_exit("explains_no_compress")
    assert led.reuse_attempts == 2
    assert led.reuse_branch_in_segment == {"explains_no_compress": 1}


def test_the_phi_tally_lands_in_the_ledger_because_the_ledger_wrote_it_itself():
    """RANKING 1 again, for the second pen. `note_no_eligible_phi` is passed as a BOUND METHOD for the same reason
    `note_reuse_exit` is: a second carrier is a second construction site, and one of them gets orphaned."""
    led = ChainLedger()
    led.note_reuse_attempt()
    _lib(NEAR, COL4).explains_scored(_evidence(8), branch=led.note_reuse_exit,
                                     phi_branch=led.note_no_eligible_phi)
    assert dict(led.reuse_branch) == {"explains_no_eligible_mixed": 1}
    assert dict(led.no_eligible_phi) == {"phi_absent": 1, "phi_universal": 1}
    assert led.no_eligible_phi_in_segment == {"phi_absent": 1, "phi_universal": 1}
    assert led.report()["no_eligible_phi"] == {"phi_absent": 1, "phi_universal": 1}


def test_every_explains_scored_call_site_in_policy_passes_the_phi_pen_too():
    """The orphan hazard, once per pen. An offer site wired for `branch=` but not `phi_branch=` would report a
    confident zero for whichever half of the split it stopped counting -- a field never COMPUTED, printed as a
    zero, which is the mis-labelled receipt this whole beat is undoing."""
    src = open(os.path.join(SRC, "policy.py")).read()
    sites = re.findall(r"explains_scored\((?:[^()]|\([^()]*\))*\)", src, re.S)
    assert sites, "the offer site vanished -- the funnel is measuring nothing"
    for s in sites:
        assert "phi_branch=" in s, "an offer site with no φ pen: %s" % s


def test_the_report_publishes_the_residue_rather_than_assuming_it():
    led = ChainLedger()
    led.note_reuse_attempt()
    led.note_reuse_attempt()
    led.note_reuse_exit("explains_no_eligible_absent")
    rep = led.report()
    assert rep["reuse_attempts"] == 2
    assert rep["reuse_residue"] == 1                     # an attempt that reached no branch -- and it SAYS so
    led.note_reuse_exit("explains_no_eligible_absent")
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
    p.chain.note_reuse_exit("explains_no_eligible_absent")
    p.chain.note_reuse_exit("explains_no_compress")      # two branches, one segment
    p._close_segment("death")
    ev = p.receipts[-1]
    assert ev.reuse_attempts == 1
    assert ev.reuse_branch == {"explains_no_compress": 1, "explains_no_eligible_absent": 1}
    assert ev.stage is not None                          # the stage and its branches are on the SAME receipt
    assert p.chain.reuse_attempts_in_segment == 0        # ...and the ledger moved on


def test_a_second_segment_is_not_charged_the_first_segments_branches():
    p = ReduxPolicy(game_id="rf02-aaaa")
    p.frames = [_board()]
    p.chain.note_step()
    p.chain.note_reuse_attempt()
    p.chain.note_reuse_exit("explains_no_eligible_absent")
    p._close_segment("death")
    p.chain.note_step()
    p._close_segment("death")
    assert p.receipts[-2].reuse_branch == {"explains_no_eligible_absent": 1}
    assert p.receipts[-1].reuse_attempts == 0
    assert p.receipts[-1].reuse_branch == {}


def test_the_receipt_carries_the_per_phi_tally_and_it_is_read_before_the_close_too():
    """The φ tally is a SECOND field that `end_segment` zeroes, so it needs its own read-before-close. Wiring the
    branch read and forgetting this one would stamp a measured zero for the φ split on every receipt in the run
    and the sweep would print a confident, empty answer to the question the whole beat is about."""
    p = ReduxPolicy(game_id="rf03-aaaa")
    p.frames = [_board()]
    p.chain.note_step()
    p.chain.note_reuse_attempt()
    p.chain.note_reuse_exit("explains_no_eligible_mixed")
    p.chain.note_no_eligible_phi("phi_absent")
    p.chain.note_no_eligible_phi("phi_absent")
    p.chain.note_no_eligible_phi("phi_universal")        # three φ scanned, ONE attempt -- different denominators
    p._close_segment("death")
    ev = p.receipts[-1]
    assert ev.reuse_attempts == 1
    assert ev.no_eligible_phi == {"phi_absent": 2, "phi_universal": 1}
    assert sum(ev.no_eligible_phi.values()) != ev.reuse_attempts    # ...and they are NOT expected to agree
    assert p.chain.no_eligible_phi_in_segment == {}
    p.chain.note_step()
    p._close_segment("death")
    assert p.receipts[-1].no_eligible_phi == {}          # the next segment is not charged the first one's φ


# --------------------------------------------------------------------------------------------------------------
# 4. THE CROSS-TAB IS A READING OF ONE ROW, NEVER A JOIN BETWEEN TWO ORGANS.
# --------------------------------------------------------------------------------------------------------------
def _ev(stage, branch, game="g1", phi=None):
    e = ResidualEvent(game=game, level=0, segment=0, reason="death")
    e.stage = stage
    e.reuse_branch = dict(branch)
    e.reuse_attempts = sum(branch.values())
    e.no_eligible_phi = dict(phi or {})
    return e


def test_by_stage_takes_the_stage_and_the_branch_off_the_same_receipt():
    """A pooled branch count says how the sweep's offers came out; it says NOTHING about the segments scored
    MINTED_UNUSED, and a pooled number offered as evidence about a subset is a mis-labelled receipt one level up.
    The cross-tab answers WHICH MEMBERS -- and it can only do that if no segment's branches can be charged to
    another segment's stage, which is what keying off each receipt's own two fields guarantees."""
    evs = [_ev("MINTED_UNUSED", {"explains_no_eligible_absent": 3}),
           _ev("USED_NOCLEAR", {"explains_transfer": 1, "explains_no_eligible_absent": 1}),
           _ev("MINT_UNFIRED", {"explains_no_compress": 2})]
    f = _reuse_funnel(evs)
    assert f["attempts"] == 7
    assert f["branch"] == {"explains_no_compress": 2, "explains_no_eligible_absent": 4, "explains_transfer": 1}
    assert f["residue"] == 0
    assert f["by_stage"]["MINTED_UNUSED|explains_no_eligible_absent"] == 3
    assert f["by_stage"]["USED_NOCLEAR|explains_no_eligible_absent"] == 1
    assert "MINTED_UNUSED|explains_no_compress" not in f["by_stage"]
    assert sum(f["by_stage"].values()) == sum(f["branch"].values())


def test_an_unscored_segment_is_named_not_dropped():
    """A segment that ended in an ADVANCE is deliberately unscored, and a receipt filed before the ledger returned
    a stage has no stage either. Dropping those rows would be a residue that closes itself -- the cross-tab would
    balance because the missing rows were never counted on either side."""
    f = _reuse_funnel([_ev(None, {"explains_no_eligible_absent": 2})])
    assert f["by_stage"] == {"UNSCORED|explains_no_eligible_absent": 2}
    assert f["residue"] == 0


def test_the_residue_goes_nonzero_when_an_attempt_reached_no_branch():
    e = _ev("MINTED_UNUSED", {"explains_no_eligible_absent": 1})
    e.reuse_attempts = 3                                 # two attempts that never named a branch
    f = _reuse_funnel([e])
    assert f["residue"] == 2


def test_no_by_stage_residue_is_published_because_it_could_never_fail_here():
    """An identity that cannot fail is decoration, not a check: inside `_reuse_funnel` every branch write also
    writes a by_stage row, so the two sums are equal BY CONSTRUCTION. The residue worth printing crosses the
    POOLING boundary and `tools/sweep_chain.py` computes it there, from the two pooled dicts. A producer field
    that can only ever read 0 is precisely 'a field never COMPUTED, printed as a zero'."""
    assert "by_stage_residue" not in _reuse_funnel([_ev("MINTED_UNUSED", {"explains_no_eligible_absent": 1})])
    printer = open(os.path.join(os.path.dirname(__file__), "..", "tools", "sweep_chain.py")).read()
    assert "by_stage_residue" not in printer, "the printer is reading a field the producer no longer emits"


def test_the_per_phi_tally_pools_on_its_own_denominator_and_is_never_added_to_the_branch_sum():
    """THE POOLED φ SPLIT. It rides in the same block as `branch` and must stay separable from it: the residue
    identity `sum(branch) == attempts` closes on ATTEMPTS, and folding a per-φ count into it would make the sum
    land on the right total for the wrong reason -- invisibly, because nothing would go red."""
    evs = [_ev("MINTED_UNUSED", {"explains_no_eligible_absent": 2}, phi={"phi_absent": 5}),
           _ev("MINTED_UNUSED", {"explains_no_eligible_mixed": 1}, phi={"phi_absent": 3, "phi_universal": 1}),
           _ev("USED_NOCLEAR", {"explains_transfer": 1})]
    f = _reuse_funnel(evs)
    assert f["attempts"] == 4 and f["residue"] == 0      # the attempt identity is untouched by the φ rows
    assert f["phi"] == {"phi_absent": 8, "phi_universal": 1}
    assert sum(f["phi"].values()) != f["attempts"]       # different denominator, and the test says so out loud
    assert sum(f["branch"].values()) == f["attempts"]


def test_the_per_phi_cross_tab_is_read_off_the_same_receipt_as_the_stage():
    """Same rule as the branch cross-tab: a pooled φ split says nothing about the segments scored MINTED_UNUSED
    specifically, and a pooled number offered as evidence about a subset is a mis-labelled receipt one level up."""
    f = _reuse_funnel([_ev("MINTED_UNUSED", {"explains_no_eligible_absent": 1}, phi={"phi_absent": 4}),
                       _ev("MINT_UNFIRED", {"explains_no_eligible_universal": 1}, phi={"phi_universal": 2}),
                       _ev(None, {"explains_no_eligible_absent": 1}, phi={"phi_absent": 1})])
    assert f["phi_by_stage"] == {"MINTED_UNUSED|phi_absent": 4, "MINT_UNFIRED|phi_universal": 2,
                                 "UNSCORED|phi_absent": 1}
    assert sum(f["phi_by_stage"].values()) == sum(f["phi"].values())


def test_a_receipt_with_no_phi_rows_contributes_nothing_rather_than_a_zero():
    """An attempt that never reached the eligibility loop has no φ verdict, which is not the same as a φ verdict
    of zero. Emitting a 0 row would be a field never COMPUTED, printed as a zero -- the exact defect."""
    f = _reuse_funnel([_ev("MINTED_UNUSED", {"explains_no_compress": 1})])
    assert f["phi"] == {} and f["phi_by_stage"] == {}


def test_summary_publishes_the_funnel_as_a_sibling_of_the_decide_funnel():
    s = summary([_ev("MINTED_UNUSED", {"explains_no_eligible_absent": 2})])
    assert s["reuse_funnel"]["attempts"] == 2
    assert s["reuse_funnel"]["branch"] == {"explains_no_eligible_absent": 2}


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


# --------------------------------------------------------------------------------------------------------------
# 6. WHICH VOCABULARY WAS ABSENT -- THE SAME DENOMINATOR, A DIFFERENT QUESTION, ITS OWN DICT.
# --------------------------------------------------------------------------------------------------------------
def test_every_registry_kind_stamps_itself_onto_the_atom_it_builds():
    """The family split is read off `Atom.kind`, which the BUILDER writes. The alternative was to recover the kind
    by parsing `name` afterwards, and a name parsed after the fact is a guess about what a branch did rather than
    a record of it -- the same defect as an exit name spanning two returns, one layer down."""
    from newhorse.redux_arch.dsl import _ATOM_TYPES, make_atom
    for kind, (argt, _) in _ATOM_TYPES.items():
        atom = make_atom(kind, *(4 for _ in argt))
        assert atom.kind == kind, "%s built an atom stamped %r" % (kind, atom.kind)


def test_the_two_families_partition_the_registry_exhaustively_and_exclusively():
    """No third family and no atom in both. If a new atom kind is ever registered without being placed, the module
    assert fires at import -- an unplaced atom silently counted as 'relational' would be a mis-labelled receipt
    manufactured at the point the vocabulary grew."""
    from newhorse.redux_arch.dsl import COLOUR_ATOM_KINDS, RELATIONAL_ATOM_KINDS, _ATOM_TYPES, atom_family, make_atom
    assert COLOUR_ATOM_KINDS | RELATIONAL_ATOM_KINDS == frozenset(_ATOM_TYPES)
    assert not (COLOUR_ATOM_KINDS & RELATIONAL_ATOM_KINDS)
    for kind, (argt, _) in _ATOM_TYPES.items():
        assert atom_family(make_atom(kind, *(4 for _ in argt))) in ("colour", "relational")


def test_predicate_composition_is_exhaustive_over_conjunctions_and_names_the_empty_case():
    from newhorse.redux_arch.dsl import predicate_family
    assert predicate_family(COL7) == "colour"
    assert predicate_family(NEAR) == "relational"
    assert predicate_family(COL4_NEAR) == "both"
    assert predicate_family(Predicate(frozenset())) == "empty"     # named, not folded into either side


def test_composition_and_cause_are_different_claims_and_the_test_case_proves_it():
    """★ THE REASON THERE ARE TWO SPLITS. `colour==4 ∧ NEAR` is absent on this evidence because NEAR never holds;
    colour 4 holds in every single context. Reading the COMPOSITION row alone would charge this to the colour
    vocabulary and send the repair to atom promotion, which would fix nothing. The CAUSE row is charged from each
    atom's OWN evaluation over the same contexts -- the only place that fact exists."""
    kind = _Pen()
    assert _lib(COL4_NEAR).explains_scored(_evidence(8), phi_branch=_Pen(), kind_branch=kind) is None
    assert sorted(kind.names) == ["absent_cause_relational", "absent_kind_both"]


def test_the_cause_split_names_an_interaction_absence_rather_than_blaming_a_vocabulary():
    """`FREE ∧ ROW` holds nowhere on `_split_ev` and yet BOTH of its atoms are alive there. Charging that to
    either vocabulary would be an invented finding; `absent_cause_none` says the conjunction never co-occurs, and
    its repair is the ARITY of the predicate, not the atom registry."""
    kind = _Pen()
    assert _lib(FREE_ROW).explains_scored(_split_ev(6), phi_branch=_Pen(), kind_branch=kind) is None
    assert sorted(kind.names) == ["absent_cause_none", "absent_kind_relational"]


def test_the_cause_split_names_both_when_both_families_are_dead():
    kind = _Pen()
    assert _lib(COL7_NEAR).explains_scored(_evidence(8), phi_branch=_Pen(), kind_branch=kind) is None
    assert sorted(kind.names) == ["absent_cause_both", "absent_kind_both"]


def test_a_dead_colour_literal_is_charged_to_the_colour_vocabulary_at_both_splits():
    kind = _Pen()
    assert _lib(COL7).explains_scored(_evidence(8), phi_branch=_Pen(), kind_branch=kind) is None
    assert sorted(kind.names) == ["absent_cause_colour", "absent_kind_colour"]


def test_the_base_rate_is_measurable_on_both_families_or_the_absent_split_is_unreadable():
    """`universal_kind_*` exists so 'absence concentrates in colour' can be read against what the library is MADE
    of rather than asserted. A library that is 90% colour would produce a colour-heavy absent split by base rate
    alone, and that is not a finding about travel."""
    k1, k2 = _Pen(), _Pen()
    assert _lib(COL4).explains_scored(_evidence(8), phi_branch=_Pen(), kind_branch=k1) is None
    assert k1.names == ["universal_kind_colour"]
    assert _lib(ROW).explains_scored(_row_ev(6), phi_branch=_Pen(), kind_branch=k2) is None
    assert k2.names == ["universal_kind_relational"]


def test_an_eligible_predicate_writes_no_vocabulary_literal_either():
    """The vocabulary pen is charged at the REJECTION, exactly like the φ pen. If it wrote on eligible φ too it
    would become a library census wearing the name of a rejection reason."""
    kind = _Pen()
    assert _lib(ROW).explains_scored(_evidence(8), phi_branch=_Pen(), kind_branch=kind) is None
    assert kind.names == []                              # ROW is ELIGIBLE here; it lost at compression, not here


def test_the_three_vocabulary_identities_close_against_the_coarse_phi_counts():
    """★ THE IDENTITY THAT CAN FAIL. `absent_kind_*` and `absent_cause_*` each sum to `phi_absent`;
    `universal_kind_*` sums to `phi_universal`. They live in a DIFFERENT dict from `phi_absent`/`phi_universal`
    precisely so this is a cross-dict check rather than a tautology -- a refinement pooled into the same bag would
    close on the right total for the wrong reason."""
    phi, kind = _Pen(), _Pen()
    lib = (COL7, NEAR, COL4_NEAR, COL7_NEAR, COL4)       # four absent, one universal
    assert _lib(*lib).explains_scored(_evidence(8), phi_branch=phi, kind_branch=kind) is None
    n_abs = phi.names.count("phi_absent")
    n_uni = phi.names.count("phi_universal")
    assert (n_abs, n_uni) == (4, 1)
    assert sum(1 for n in kind.names if n.startswith("absent_kind_")) == n_abs
    assert sum(1 for n in kind.names if n.startswith("absent_cause_")) == n_abs
    assert sum(1 for n in kind.names if n.startswith("universal_kind_")) == n_uni
    for n in kind.names:
        assert n in KIND_NAMED, "an unnamed vocabulary literal %r" % n


def test_the_vocabulary_tally_is_never_added_to_the_phi_tally_or_the_branch_tally():
    """THREE denominators now, and only two of them are the same. The branch pen writes once per ATTEMPT; the φ
    pen and the vocabulary pen both write once per φ REJECTED but answer different questions and close on
    different subsets. None of the three may be summed into another."""
    led = ChainLedger()
    led.note_reuse_attempt()
    _lib(COL7, NEAR, COL4).explains_scored(_evidence(8), branch=led.note_reuse_exit,
                                           phi_branch=led.note_no_eligible_phi,
                                           kind_branch=led.note_phi_kind)
    rep = led.report()
    assert rep["reuse_attempts"] == 1 and rep["reuse_residue"] == 0
    assert rep["reuse_branch"] == {"explains_no_eligible_mixed": 1}
    assert rep["no_eligible_phi"] == {"phi_absent": 2, "phi_universal": 1}
    assert set(rep["phi_kind"]) <= set(KIND_NAMED)
    assert sum(rep["phi_kind"].values()) == 2 * 2 + 1    # two splits over 2 absent φ, one over 1 universal φ
    assert sum(rep["phi_kind"].values()) != sum(rep["no_eligible_phi"].values())


def test_the_vocabulary_count_lands_in_the_ledger_because_the_ledger_wrote_it_itself():
    """RANKING 1, for the third pen. Bound method, one construction site, nothing to orphan."""
    led = ChainLedger()
    led.note_reuse_attempt()
    _lib(COL7).explains_scored(_evidence(8), branch=led.note_reuse_exit,
                               phi_branch=led.note_no_eligible_phi, kind_branch=led.note_phi_kind)
    assert dict(led.phi_kind) == {"absent_kind_colour": 1, "absent_cause_colour": 1}
    assert led.phi_kind_in_segment == {"absent_cause_colour": 1, "absent_kind_colour": 1}
    assert led.report()["phi_kind"] == {"absent_cause_colour": 1, "absent_kind_colour": 1}


def test_the_segment_vocabulary_tally_resets_but_the_run_total_does_not():
    led = ChainLedger()
    led.note_step()
    led.note_phi_kind("absent_kind_colour")
    led.end_segment("death")
    assert led.phi_kind_in_segment == {}                 # the next segment is not charged this one's vocabulary
    assert dict(led.phi_kind) == {"absent_kind_colour": 1}


def test_every_explains_scored_call_site_in_policy_passes_the_vocabulary_pen_too():
    """The orphan hazard, once per pen. A site wired for `phi_branch=` but not `kind_branch=` would print a
    confident zero for the vocabulary split -- a field never COMPUTED, rendered as evidence."""
    src = open(os.path.join(SRC, "policy.py")).read()
    sites = re.findall(r"explains_scored\((?:[^()]|\([^()]*\))*\)", src, re.S)
    assert sites, "the offer site vanished -- the funnel is measuring nothing"
    for s in sites:
        assert "kind_branch=" in s, "an offer site with no vocabulary pen: %s" % s


def test_the_receipt_carries_the_vocabulary_tally_and_it_is_read_before_the_close():
    """A THIRD field that `end_segment` zeroes, so a third read-before-close. Wiring two of the three and
    forgetting this one would stamp a measured zero on every receipt in the run."""
    p = ReduxPolicy(game_id="rf06-aaaa")
    p.frames = [_board()]
    p.chain.note_step()
    p.chain.note_reuse_attempt()
    p.chain.note_reuse_exit("explains_no_eligible_absent")
    p.chain.note_no_eligible_phi("phi_absent")
    p.chain.note_phi_kind("absent_kind_colour")
    p.chain.note_phi_kind("absent_cause_relational")
    p._close_segment("death")
    ev = p.receipts[-1]
    assert ev.phi_kind == {"absent_cause_relational": 1, "absent_kind_colour": 1}
    assert p.chain.phi_kind_in_segment == {}
    p.chain.note_step()
    p._close_segment("death")
    assert p.receipts[-1].phi_kind == {}


def test_the_vocabulary_split_pools_on_its_own_axis_and_cross_tabs_off_the_same_row():
    """Pooled into its OWN dict and cross-tabbed against the stage on the receipt that carries both, exactly like
    the φ split. The cross-tab is a reading of one row, never a join between two organs."""
    a = ResidualEvent(game="g1", level=0, segment=0, reason="death")
    a.stage, a.reuse_branch, a.reuse_attempts = "MINTED_UNUSED", {"explains_no_eligible_absent": 1}, 1
    a.no_eligible_phi = {"phi_absent": 2}
    a.phi_kind = {"absent_kind_colour": 2, "absent_cause_colour": 1, "absent_cause_relational": 1}
    b = ResidualEvent(game="g1", level=0, segment=1, reason="death")
    b.stage, b.reuse_branch, b.reuse_attempts = "USED_NOCLEAR", {"explains_transfer": 1}, 1
    out = _reuse_funnel([a, b])
    assert out["phi_kind"] == {"absent_cause_colour": 1, "absent_cause_relational": 1, "absent_kind_colour": 2}
    assert out["phi_kind_by_stage"] == {"MINTED_UNUSED|absent_cause_colour": 1,
                                        "MINTED_UNUSED|absent_cause_relational": 1,
                                        "MINTED_UNUSED|absent_kind_colour": 2}
    assert out["residue"] == 0                           # ...and none of it touched the per-ATTEMPT identity
    assert sum(out["phi_kind"].values()) != out["attempts"]


def test_a_receipt_with_no_vocabulary_rows_contributes_nothing_rather_than_a_zero():
    e = ResidualEvent(game="g1", level=0, segment=0, reason="death")
    e.stage, e.reuse_branch, e.reuse_attempts = "MINT_UNFIRED", {}, 0
    assert _reuse_funnel([e])["phi_kind"] == {}          # absent, not a manufactured zero


def test_the_vocabulary_pen_does_not_change_what_the_scorer_returns():
    """INSTRUMENT ONLY. Same library, same evidence, with and without the third pen -- identical verdict and
    identical bits. If passing a pen could move the answer the instrument would be part of the mechanism."""
    for lib, ev in ((( COL7, NEAR), _evidence(8)), ((FREE,), _evidence(8)), ((ROW,), _evidence(8))):
        bare = _lib(*lib).explains_scored(ev)
        penned = _lib(*lib).explains_scored(ev, branch=_Pen(), phi_branch=_Pen(), kind_branch=_Pen())
        assert (bare is None) == (penned is None)
        if bare is not None:
            assert str(bare[0]) == str(penned[0]) and abs(bare[1] - penned[1]) < 1e-9


def test_no_decision_path_reads_the_vocabulary_split():
    """THE FREEZE HOLDS. `phi_kind` is written by the scorer and read by the receipt carry and the sweep printer.
    Any other reader would be an organ steering on its own instrument, which is how the old proxy lied."""
    for fn in ("policy.py", "consolidate.py", "swarm.py", "receipt.py", "abort_code.py"):
        for i, line in enumerate(open(os.path.join(SRC, fn)), 1):
            code = line.split("#")[0]
            if "phi_kind" not in code:
                continue
            ok = (fn in ("abort_code.py", "receipt.py")
                  or (fn == "consolidate.py" and "phi_kind" not in code.split("=")[0])
                  or (fn == "policy.py" and ("ev.phi_kind" in code or "seg_phi_kind" in code
                                             or "kind_branch=" in code)))
            assert ok, "%s:%d reads the vocabulary split outside the carry: %s" % (fn, i, line.strip())


# --------------------------------------------------------------------------------------------------------------
# 7. THE HEADLINE READS THE BRANCH, NOT THE DEEPEST STALL.
#
# `tether_distribution` published `indicts = indicts(Stage[worst])` -- computed from the WORST STAGE ALONE. It
# printed "architecture" on sweeps A/B and "drive" on C, flipping on nothing but how warm the residual bank was,
# while the reuse funnel three lines below it said all nineteen MINTED_UNUSED segments across five sweeps resolved
# at a `no_eligible` branch and ZERO at `explains_no_compress`. MINTED_UNUSED is an EXIT NAME COVERING MORE THAN
# ONE `return`, and an exit name is not an attribution. These tests pin the branch reading, the scope it was taken
# on, the survival of the old reading under its own name, and the refusal to guess a layer for an unread literal.
# --------------------------------------------------------------------------------------------------------------

def _dist(games):
    from newhorse.redux_arch.swarm import tether_distribution
    return tether_distribution(games)


def _game(stage, rank, branch_by_stage=None, branch=None, gid="g"):
    """One game's contribution, shaped exactly as `_play_policy` returns it."""
    r = dict(game=gid, tether_stage=dict(counts={stage: 1}, stalls=1, advances=0,
                                         furthest_stage=stage, furthest_rank=rank))
    if branch_by_stage is not None or branch is not None:
        r["echo"] = dict(reuse_funnel=dict(attempts=sum((branch or {}).values()),
                                           branch=dict(branch or {}),
                                           by_stage=dict(branch_by_stage or {})))
    return r


def test_the_branch_map_covers_exactly_the_literals_the_source_actually_writes():
    """The map is checked against the SOURCE, not against a hand-copied tuple. A `return` added with a literal but
    no layer would otherwise reach the headline and be folded into a neighbouring layer silently."""
    from newhorse.redux_arch.abort_code import REUSE_BRANCHES, _BRANCH_INDICTS
    written = set()
    for fn in ("policy.py", "consolidate.py"):
        src = open(os.path.join(SRC, fn)).read()
        for a, b in re.findall(r'_b\("([a-z_]+)"\)|note_reuse_exit\("([a-z_]+)"\)', src):
            written.add(a or b)
    assert written <= set(REUSE_BRANCHES), "a literal is written with no entry in REUSE_BRANCHES: %s" % (
        written - set(REUSE_BRANCHES))
    assert set(REUSE_BRANCHES) == set(NAMED) == set(_BRANCH_INDICTS)


def test_absent_and_universal_get_opposite_layers_even_though_they_share_a_prefix():
    """THE MAP IS A LOOKUP ON THE WHOLE LITERAL, NEVER A PREFIX PARSE. `explains_no_eligible_absent` and
    `..._universal` share a stem and implicate OPPOSITE links; a `startswith` reading would merge them and the
    merge would be invisible."""
    from newhorse.redux_arch.abort_code import branch_indicts
    assert branch_indicts("explains_no_eligible_absent") == "grain"
    assert branch_indicts("explains_no_eligible_universal") == "upstream"
    assert branch_indicts("explains_no_eligible_mixed") == "grain+upstream"
    assert branch_indicts("explains_no_compress") == "architecture"     # the ONLY architecture branch
    arch = [k for k in NAMED if branch_indicts(k) == "architecture"]
    assert arch == ["explains_no_compress"]


def test_an_unread_literal_is_published_as_unmapped_rather_than_given_a_layer():
    """Guessing a layer for a name nobody has read is the defect this map exists to close, so an unmapped branch
    suppresses the verdict entirely instead of losing to a majority computed without it."""
    from newhorse.redux_arch.abort_code import branch_indicts, indicts_from_branches
    assert branch_indicts("explains_brand_new_thing") is None
    got = indicts_from_branches({"explains_no_eligible_absent": 9, "explains_brand_new_thing": 1})
    assert got["verdict"] == "unattributed"
    assert got["unmapped"] == {"explains_brand_new_thing": 1} and got["attempts"] == 10


def test_a_layer_is_claimed_only_on_a_strict_majority_and_the_split_is_always_published():
    """No threshold was chosen and no tie is broken: below a majority the answer is `mixed`, with the per-layer
    split beside it so the reader sees what was charged rather than a word."""
    from newhorse.redux_arch.abort_code import indicts_from_branches
    tie = indicts_from_branches({"explains_no_eligible_absent": 5, "explains_no_compress": 5})
    assert tie["verdict"] == "mixed" and tie["layers"] == {"architecture": 5, "grain": 5}
    win = indicts_from_branches({"explains_no_eligible_absent": 6, "explains_no_compress": 5})
    assert win["verdict"] == "grain" and win["attempts"] == 11
    assert indicts_from_branches({})["verdict"] == "none"


def test_the_headline_reads_the_minted_unused_rows_not_the_pooled_branch_tally():
    """★ WHICH MEMBERS. A pooled branch tally answers "how did the sweep's offers come out", not "how did the
    MINTED_UNUSED segments come out". Here the pooled tally is dominated by TRANSFERS and the MINTED_UNUSED rows
    are all `no_eligible`: the pooled reading would say the chain is fine, the subset reading says grain."""
    d = _dist({"g": _game("MINTED_UNUSED", 4,
                          branch_by_stage={"MINTED_UNUSED|explains_no_eligible_absent": 4,
                                           "CLEARED|explains_transfer": 20},
                          branch={"explains_no_eligible_absent": 4, "explains_transfer": 20})})
    assert d["indicts"] == "grain" and d["indicts_scope"] == "MINTED_UNUSED"
    assert d["indicts_attempts"] == 4                        # the SUBSET's denominator, not the sweep's 24
    assert d["indicts_layers"] == {"grain": 4}


def test_the_old_stage_reading_survives_under_its_own_name_and_is_not_silently_redefined():
    """The stage reading is the honest depth and a mis-labelled attribution. It is kept so the two can be compared;
    replacing it in place would have changed what an old number meant without renaming it."""
    d = _dist({"g": _game("MINTED_UNUSED", 4,
                          branch_by_stage={"MINTED_UNUSED|explains_no_eligible_absent": 4},
                          branch={"explains_no_eligible_absent": 4})})
    assert d["indicts_worst_stage"] == "architecture"        # what the sweep printed for thirteen beats
    assert d["indicts"] == "grain" and d["indicts_source"] == "reuse_funnel"
    assert d["worst_stage"] == "MINTED_UNUSED"               # the DEPTH is unchanged and still published


def test_the_headline_falls_back_to_the_stage_and_says_so_when_the_funnel_has_nothing():
    """A funnel with no rows is not evidence of anything. Below the reuse stage there is no branch to read, so the
    stage reading stands -- and `indicts_source` states which of the two produced the word."""
    d = _dist({"g": _game("MINT_UNFIRED", 2)})
    assert d["indicts"] == "gate/implementation" and d["indicts_source"] == "worst_stage"
    assert d["indicts_scope"] is None and d["indicts_attempts"] == 0


def test_all_attempts_scope_is_used_only_when_the_cross_tab_is_missing_and_it_names_itself():
    """An older producer emits `branch` but no `by_stage`. Reading the pooled tally is still better than the stage
    word, but it is a different denominator, so the scope travels with the verdict."""
    d = _dist({"g": _game("MINTED_UNUSED", 4, branch={"explains_no_compress": 3})})
    assert d["indicts"] == "architecture" and d["indicts_scope"] == "all_attempts"
    d2 = _dist({"g": _game("USED_NOCLEAR", 5, branch={"explains_transfer": 3})})
    assert d2["indicts_source"] == "worst_stage" and d2["indicts"] == "drive"


def test_the_headline_stops_flipping_on_bank_warmth_when_the_branches_do_not_change():
    """THE DEFECT ITSELF. Sweeps A/B/C differed only in how warm the residual bank was: the deepest stall moved
    MINTED_UNUSED -> USED_NOCLEAR and the headline flipped architecture -> drive, though every MINTED_UNUSED
    segment resolved at the same grain branch in both. The branch reading holds; the stage reading still flips."""
    cold = _dist({"g": _game("MINTED_UNUSED", 4,
                             branch_by_stage={"MINTED_UNUSED|explains_no_eligible_absent": 4},
                             branch={"explains_no_eligible_absent": 4})})
    warm = _dist({"g": _game("USED_NOCLEAR", 5,
                             branch_by_stage={"MINTED_UNUSED|explains_no_eligible_absent": 4,
                                              "USED_NOCLEAR|explains_transfer": 7},
                             branch={"explains_no_eligible_absent": 4, "explains_transfer": 7})})
    assert cold["indicts"] == warm["indicts"] == "grain"
    assert cold["indicts_worst_stage"] != warm["indicts_worst_stage"]   # the old headline, still flipping


def test_the_cross_tab_key_is_split_by_the_same_convention_that_built_it():
    """A composite key is a classification carried on a receipt, and a class recovered by parsing a name rots when
    the convention drifts. It cannot be stamped at construction (the stage and the branch are joined at pooling
    time), so join and split live in ONE place and this pins the round trip -- including a branch name that
    someday contains the separator."""
    from newhorse.redux_arch.receipt import stage_key, split_stage_key
    for st, nm in (("MINTED_UNUSED", "explains_no_compress"), ("UNSCORED", "dir_tie"), ("CLEARED", "a|b")):
        assert split_stage_key(stage_key(st, nm)) == (st, nm)
    assert split_stage_key("bare_name_with_no_stage") == ("UNSCORED", "bare_name_with_no_stage")


def test_no_decision_path_reads_the_headline_attribution():
    """THE FREEZE HOLDS ONE LEVEL UP TOO. The branch->layer map is written by the sweep reporter and read by the
    printer. An organ steering on it would be steering on its own instrument."""
    for fn in ("policy.py", "consolidate.py", "receipt.py"):
        for i, line in enumerate(open(os.path.join(SRC, fn)), 1):
            code = line.split("#")[0]
            assert "branch_indicts" not in code and "indicts_from_branches" not in code, \
                "%s:%d reads the headline attribution: %s" % (fn, i, line.strip())
