"""★★★ THE OFFER GATE: `REUSE_UNWIRED` IS AN EXIT NAME COVERING A STATE NOBODY WROTE DOWN. ★★★

TWO COLD SWEEPS AT ONE COMMIT DISAGREED BY ONE SEGMENT. `/tmp/sweepA.txt` and `/tmp/sweepB.txt` were run at
`9c00271` with the residual bank deleted. Their per-game tables are BYTE-IDENTICAL across all 25 games -- same
family, same levels, same stalls, same advances, same residuals, same mints, same furthest stage -- and every
upstream stream counter matches exactly (break_events, diff_ran, minted, promoted, residual_nonempty). The only
difference in either file is one segment moving between two stage names:

    A: REUSE_UNWIRED 5, MINTED_UNUSED 3        B: REUSE_UNWIRED 4, MINTED_UNUSED 4

Nothing the agent DID differed. So the ±1 is not a fact about reasoning, and until it is bounded, every stage
histogram this project prints carries an unbounded error bar on the one code that indicts the architecture.

WHAT ACTUALLY MOVES IT. `swarm.run_swarm` plays 8 games as concurrent `threading.Thread`s in ONE process.
`policy.SHARED_ECHO` is a process-wide `Consolidator` singleton, so all 8 threads offer their residuals to ONE
library. `Consolidator.observe_mint` only ever APPENDS to `self.library` -- nothing removes -- so the library is
MONOTONE NON-DECREASING and has exactly one empty→non-empty transition per process: the FIRST promotion. The
offer site's guard was `if self.echo.library:` with NO else. Therefore a non-empty residual arriving before that
first promotion makes no attempt at all and its segment tops out at REUSE_UNWIRED, while the SAME residual
arriving after it makes an attempt and its segment scores MINTED_UNUSED. Which side of the line a segment lands
on is chosen by the thread scheduler.

THIS IS THE SAME DEFECT ALREADY CLOSED THREE TIMES: an exit name that covers more than one state is not an
attribution (`_decide`'s exits, `explains_no_eligible`, the sweep headline). `REUSE_UNWIRED` says "the reuse path
is not wired". What it MEANT, for some unknown fraction of its count, was "Γ was still empty when we asked".

THE INSTRUMENT. `ChainLedger.note_offer_gate` is written at BOTH branches of the guard, on the denominator of
OFFER OPPORTUNITIES (one row per non-empty-residual diff) rather than attempts -- the whole point being the
opportunities that never became attempts. Two literals, exhaustive and exclusive at a single `if`:

    offered              Γ had members; an attempt follows and the funnel takes over from here
    skipped_gamma_empty  Γ was empty AT ASK TIME; no attempt is made and the segment's ceiling stays REUSE_UNWIRED

and `gamma_at_offer` records the library SIZE seen at the same guard, from the SAME read, in its OWN dict on the
SAME denominator -- for the reason `phi_kind` is kept out of `no_eligible_phi`: it refines the gate rather than
partitioning it differently, and merging them would close the coarse total on the right number for the wrong
reason.

★ PRE-REGISTERED PREDICTION (written here BEFORE the sweep that reads it, evaluated by `tools/sweep_chain.py`
itself and not by prose afterwards): on any sweep with `promoted > 0`, `gamma_at_offer` will contain BOTH a `0`
key AND a non-zero key. That is the direct receipt that offers inside ONE process saw DIFFERENT libraries -- i.e.
that ORDER, not behaviour, chose which stage some segments received. If instead only `0` appears while
`promoted > 0`, the first promotion landed after the last offer and the race window is the WHOLE RUN, which is a
stronger form of the same finding rather than a refutation. If NO offer saw an empty Γ, the bank was warm before
the first opportunity and none of that sweep's REUSE_UNWIRED can be blamed on order -- published either way.

WHAT `skipped_gamma_empty` IS, EXACTLY: the UPPER BOUND on how many stage assignments can move between two runs
whose agents behaved identically. It is a bound, not an estimate -- no claim is made here about how many actually
move, because that would need many runs, and the bound is what the histograms need in order to be readable.

WHAT THESE TESTS DELIBERATELY DO NOT ASSERT: any live count, rate, or that the ±1 was CAUSED by this and nothing
else. Two runs is one sample, and a verdict computed from one sample is a verdict about one sample. What is
pinned here is that the state is now RECORDED at the site where it happens, that it cannot be silently dropped
crossing the pooling boundary, and that nothing in the agent reads it back.
"""
from __future__ import annotations

import os
import re

from newhorse.redux_arch.abort_code import ChainLedger, Stage
from newhorse.redux_arch.consolidate import Consolidator
from newhorse.redux_arch.dsl import Predicate, make_atom
from newhorse.redux_arch.minting import Mint
from newhorse.redux_arch.receipt import ResidualEvent, _reuse_funnel

SRC = os.path.join(os.path.dirname(__file__), "..", "src", "newhorse", "redux_arch")

# The two literals, in one place. A third path added at the guard without a reading is caught by the source scan
# below and flagged as UNNAMED by the sweep printer for the same reason the reuse branches are.
GATE_NAMED = ("offered", "skipped_gamma_empty")

FREE = Predicate(frozenset({make_atom("INTENDED_FREE")}))
ROW = Predicate(frozenset({make_atom("SAME_ROW")}))


# --------------------------------------------------------------------------------------------------------------
# 1. THE PEN WRITES BOTH DICTS, AT THE SITE, FROM ONE READ.
# --------------------------------------------------------------------------------------------------------------
def test_both_branches_of_the_guard_write_a_literal_and_the_two_are_the_whole_gate():
    led = ChainLedger()
    led.note_offer_gate("offered", 3)
    led.note_offer_gate("skipped_gamma_empty", 0)
    assert dict(led.offer_gate) == {"offered": 1, "skipped_gamma_empty": 1}
    assert set(led.offer_gate) <= set(GATE_NAMED)


def test_the_size_lands_in_its_own_dict_on_the_same_denominator_and_is_never_added_to_the_gate():
    """`phi_kind`'s rule, one level up: same denominator, different question, separate total. Summing the two
    would double the opportunities and land on a plausible number for the wrong reason."""
    led = ChainLedger()
    for n in (0, 0, 2, 2, 5):
        led.note_offer_gate("offered" if n else "skipped_gamma_empty", n)
    assert dict(led.gamma_at_offer) == {"0": 2, "2": 2, "5": 1}
    assert sum(led.gamma_at_offer.values()) == sum(led.offer_gate.values()) == 5
    assert set(led.gamma_at_offer) & set(led.offer_gate) == set()


def test_one_call_writes_exactly_one_row_in_each_dict_so_the_two_can_never_disagree():
    """The branch and the size come from ONE read of a library that other threads are mutating. A second read
    could return a different number than the one that chose the branch -- and the disagreement would appear
    exactly in the runs this counter exists to explain. One call, one pair."""
    led = ChainLedger()
    for i in range(7):
        led.note_offer_gate("offered", i + 1)
    assert sum(led.offer_gate.values()) == sum(led.gamma_at_offer.values()) == 7


def test_a_zero_size_is_recorded_as_a_key_not_as_an_absence():
    """An empty Γ is the state the whole counter is about. If `0` were skipped as falsy it would be exactly the
    silence-printed-as-nothing this instrument was built to end."""
    led = ChainLedger()
    led.note_offer_gate("skipped_gamma_empty", 0)
    assert led.gamma_at_offer["0"] == 1


# --------------------------------------------------------------------------------------------------------------
# 2. SCOPING: THE SEGMENT MIRROR RESETS, THE RUN TOTAL DOES NOT.
# --------------------------------------------------------------------------------------------------------------
def test_the_segment_tally_resets_at_the_close_but_the_run_total_does_not():
    led = ChainLedger()
    led.note_step()
    led.note_offer_gate("skipped_gamma_empty", 0)
    assert led.offer_gate_in_segment == {"skipped_gamma_empty": 1}
    assert led.gamma_at_offer_in_segment == {"0": 1}
    led.end_segment("death")
    assert led.offer_gate_in_segment == {} and led.gamma_at_offer_in_segment == {}
    assert dict(led.offer_gate) == {"skipped_gamma_empty": 1}      # the RUN total survives
    led.note_step()
    led.note_offer_gate("offered", 2)
    assert led.offer_gate_in_segment == {"offered": 1}             # ...and the next segment is not charged the last
    assert dict(led.offer_gate) == {"offered": 1, "skipped_gamma_empty": 1}


def test_the_report_carries_both_dicts_as_the_ledger_wrote_them():
    led = ChainLedger()
    led.note_offer_gate("offered", 4)
    led.note_offer_gate("skipped_gamma_empty", 0)
    r = led.report()
    assert r["offer_gate"] == {"offered": 1, "skipped_gamma_empty": 1}
    assert r["gamma_at_offer"] == {"0": 1, "4": 1}


def test_the_gate_writes_no_chain_signal_so_no_stage_moves_because_it_was_added():
    """A NEW INSTRUMENT MUST NOT MOVE THE THING IT MEASURES. If `note_offer_gate` touched `_sig`, this beat's
    sweep could not be compared with any previous one -- two changes and one number is not a measurement."""
    a, b = ChainLedger(), ChainLedger()
    for led in (a, b):
        led.note_step()
        led.note_diff(residual_nonempty=True)
        led.note_mint()
    b.note_offer_gate("skipped_gamma_empty", 0)
    b.note_offer_gate("offered", 1)
    assert a.end_segment("death") == b.end_segment("death") == Stage.REUSE_UNWIRED


# --------------------------------------------------------------------------------------------------------------
# 3. THE RACE, SYNTHESISED. A MONOTONE SHARED LIBRARY MEANS THE ANSWER DEPENDS ON WHEN YOU ASK.
# --------------------------------------------------------------------------------------------------------------
def _promote(con: Consolidator, pred: Predicate, tasks=("t1", "t2")) -> None:
    for t in tasks:
        con.observe_mint(t, Mint(predicate=pred, saved_bits=4.0, support=8))


def test_the_shared_library_is_append_only_so_it_has_exactly_one_empty_to_nonempty_transition():
    """The claim the whole diagnosis rests on. If anything ever REMOVED a promoted φ, the library could go empty
    again, `skipped_gamma_empty` would stop being an upper bound on an ordering effect and would start being a
    measurement of something else, and this test is what would say so."""
    con = Consolidator(echo_threshold=2)
    assert not con.library
    _promote(con, FREE)
    assert len(con.library) == 1
    sizes = [len(con.library)]
    _promote(con, ROW, tasks=("t3", "t4"))
    sizes.append(len(con.library))
    _promote(con, FREE, tasks=("t5", "t6"))               # a re-promotion of a φ already held
    sizes.append(len(con.library))
    assert sizes == sorted(sizes), "the library went DOWN: it is no longer monotone"


def test_two_identical_offers_get_opposite_gate_literals_purely_because_of_when_they_asked():
    """THE ±1, IN MINIATURE AND WITHOUT ANY NETWORK. Same residual, same library object, same code path -- the
    only difference is that one offer happens before the process's first promotion and one after. This is the
    receipt that the stage a segment receives is not, on its own, a statement about the agent's reasoning."""
    con = Consolidator(echo_threshold=2)
    early, late = ChainLedger(), ChainLedger()
    n = len(con.library)
    early.note_offer_gate("offered" if n else "skipped_gamma_empty", n)
    _promote(con, FREE)                                   # ...another thread's game promotes, between the two asks
    n = len(con.library)
    late.note_offer_gate("offered" if n else "skipped_gamma_empty", n)
    assert dict(early.offer_gate) == {"skipped_gamma_empty": 1}
    assert dict(late.offer_gate) == {"offered": 1}
    assert dict(early.gamma_at_offer) == {"0": 1} and dict(late.gamma_at_offer) == {"1": 1}


def test_the_prediction_is_falsifiable_a_run_whose_offers_all_come_after_the_promotion_shows_no_zero_key():
    """The prediction says a run with promotions shows BOTH a 0 key and a non-zero key. Here is the world in
    which it fails: every offer made after the library was already warm. The prediction can therefore lose."""
    con = Consolidator(echo_threshold=2)
    _promote(con, FREE)
    led = ChainLedger()
    for _ in range(3):
        led.note_offer_gate("offered", len(con.library))
    assert "0" not in led.gamma_at_offer


# --------------------------------------------------------------------------------------------------------------
# 4. THE CALL SITE. ONE GUARD, ONE READ, BOTH BRANCHES CHARGED.
# --------------------------------------------------------------------------------------------------------------
def test_the_offer_guard_reads_the_library_once_and_branches_on_that_read():
    """A guard that re-reads `self.echo.library` after deciding could record a size that disagrees with its own
    branch, under exactly the concurrency this counter measures."""
    src = open(os.path.join(SRC, "policy.py")).read()
    assert "gamma_n = len(self.echo.library)" in src
    assert re.search(r"\n\s+if gamma_n:\n", src), "the guard no longer branches on the single read"
    body = src.split("gamma_n = len(self.echo.library)", 1)[1].split("note-transfer-CLEAR")[0]
    assert "if self.echo.library" not in body, "the guard re-reads the shared library after the single read"


def test_both_branches_of_the_live_guard_write_a_gate_literal():
    """THE ORPHAN-HAZARD TEST, in the direction that actually bit: the `else` did not exist for fourteen beats,
    and its absence was invisible because a branch that writes nothing produces no row to be missing."""
    src = open(os.path.join(SRC, "policy.py")).read()
    assert 'note_offer_gate("offered", gamma_n)' in src
    assert 'note_offer_gate("skipped_gamma_empty", 0)' in src


def test_every_gate_literal_written_anywhere_in_the_source_is_on_the_named_list():
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".py"):
            continue
        src = open(os.path.join(SRC, fn)).read()
        for got in re.findall(r'note_offer_gate\(\s*"([a-z_]+)"', src):
            assert got in GATE_NAMED, "%s writes an unnamed gate literal %r" % (fn, got)


def test_the_gate_is_charged_only_where_a_residual_was_actually_non_empty():
    """The denominator is OPPORTUNITIES, and an opportunity requires a residual worth offering. The guard sits
    strictly after the `if not nonempty: return ev` line, so an empty residual can never reach it -- otherwise
    the bound would be inflated by segments that had nothing to ask about in the first place."""
    src = open(os.path.join(SRC, "policy.py")).read()
    assert src.index("if not nonempty:") < src.index("gamma_n = len(self.echo.library)")


# --------------------------------------------------------------------------------------------------------------
# 5. THE CARRY: ONE ROW HOLDS THE STAGE AND THE GATE THAT PRODUCED IT.
# --------------------------------------------------------------------------------------------------------------
def test_the_receipt_carries_the_gate_and_the_policy_reads_it_before_the_close():
    """`end_segment` zeroes the mirror. A read taken after the close would put a measured zero on every receipt --
    a field never computed, rendered as evidence, which is the defect this whole ledger is scoped against."""
    src = open(os.path.join(SRC, "policy.py")).read()
    i_read = src.index("seg_offer = dict(self.chain.offer_gate_in_segment)")
    i_close = src.index("st = self.chain.end_segment(reason)")
    assert i_read < i_close
    assert src.index("seg_gamma = dict(self.chain.gamma_at_offer_in_segment)") < i_close
    assert "ev.offer_gate = seg_offer" in src and "ev.gamma_at_offer = seg_gamma" in src


def test_the_pooled_gate_cross_tabs_against_the_stage_off_one_receipt():
    evs = [ResidualEvent(game="g", level=0, segment=0, reason="death", steps=3, task_id="g:0",
                         diff_ran=True, residual_nonempty=True, stage="REUSE_UNWIRED",
                         offer_gate={"skipped_gamma_empty": 1}, gamma_at_offer={"0": 1}),
           ResidualEvent(game="g", level=0, segment=1, reason="death", steps=3, task_id="g:1",
                         diff_ran=True, residual_nonempty=True, stage="MINTED_UNUSED",
                         offer_gate={"offered": 1}, gamma_at_offer={"2": 1})]
    f = _reuse_funnel(evs)
    assert f["offer_gate"] == {"offered": 1, "skipped_gamma_empty": 1}
    assert f["offer_gate_by_stage"] == {"MINTED_UNUSED|offered": 1, "REUSE_UNWIRED|skipped_gamma_empty": 1}
    assert f["gamma_at_offer"] == {"0": 1, "2": 1}
    assert f["offer_opportunities"] == 2 and f["offer_residue"] == 0


def test_the_size_is_not_cross_tabbed_by_stage_because_it_is_a_property_of_the_process_not_the_segment():
    """Keying a library size by the stage that observed it invites reading "this stage sees small libraries" when
    the causation runs the other way round."""
    f = _reuse_funnel([ResidualEvent(game="g", level=0, segment=0, reason="death", steps=1, task_id="t",
                                     diff_ran=True, residual_nonempty=True, stage="REUSE_UNWIRED",
                                     offer_gate={"skipped_gamma_empty": 1}, gamma_at_offer={"0": 1})])
    assert "gamma_at_offer_by_stage" not in f


def test_the_gate_residue_goes_nonzero_when_an_opportunity_reached_no_literal():
    """UNLIKE the branch cross-tab residue, this one is computed from two DIFFERENT fields written at two
    DIFFERENT moments -- the diff (per receipt) and the guard (per segment, landed at the close) -- so it is able
    to fail, and a guard that someday grows a third silent path shows up here as a number rather than a silence."""
    f = _reuse_funnel([ResidualEvent(game="g", level=0, segment=0, reason="death", steps=1, task_id="t",
                                     diff_ran=True, residual_nonempty=True, stage="REUSE_UNWIRED")])
    assert f["offer_opportunities"] == 1 and f["offer_residue"] == 1


def test_an_empty_residual_is_not_counted_as_an_opportunity():
    f = _reuse_funnel([ResidualEvent(game="g", level=0, segment=0, reason="death", steps=1, task_id="t",
                                     diff_ran=True, residual_nonempty=False)])
    assert f["offer_opportunities"] == 0 and f["offer_residue"] == 0


def test_a_receipt_with_no_gate_rows_contributes_nothing_rather_than_a_zero():
    """A game that never reached the guard must not add a `skipped_gamma_empty: 0` row -- a key printed as a
    confident zero is how a field nobody computed gets cited."""
    f = _reuse_funnel([ResidualEvent(game="g", level=0, segment=0, reason="advance", steps=1, task_id="t",
                                     diff_ran=False)])
    assert f["offer_gate"] == {} and f["gamma_at_offer"] == {}


# --------------------------------------------------------------------------------------------------------------
# 6. BANK EVIDENCE, NEVER CONCLUSIONS.
# --------------------------------------------------------------------------------------------------------------
def test_no_decision_path_reads_the_gate():
    """The instant an organ branches on `offer_gate`, the agent is being steered by its own instrument. Only the
    ledger that owns the counters, the receipt that files them, and the policy lines that write and carry them
    may name them at all."""
    allowed = {"abort_code.py", "receipt.py"}
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".py") or fn in allowed:
            continue
        src = open(os.path.join(SRC, fn)).read()
        for i, line in enumerate(src.splitlines(), 1):
            code = line.split("#")[0]
            if "offer_gate" not in code and "gamma_at_offer" not in code:
                continue
            ok = fn == "policy.py" and ("note_offer_gate(" in code or "seg_offer" in code or "seg_gamma" in code
                                        or "ev.offer_gate" in code or "ev.gamma_at_offer" in code)
            assert ok, "%s:%d reads the offer gate outside the write-and-carry: %s" % (fn, i, line.strip())
