"""
test_residual_bank.py -- the two changes aimed at MINT_UNFIRED=16, tested SEPARATELY.

The measured stall distribution says 16 segments computed a MIXED residual and the MDL code still declined. Two
things could be wrong there and they need different fixes, so they are tested apart:

  (1) THE PRICE. The selection cost charged log2(CONSTRUCTED) -- including candidates that were constant across
      the residual's own contexts and therefore could never have been selected. That is paying to name a
      hypothesis that was not in the class we searched.
  (2) THE SAMPLE. A segment's residual is ~5 exceptions. No split of five items can pay a ~6-bit naming cost no
      matter how real the rule is; the evidence was being DISCARDED at segment close, so every episode re-met the
      same wall. The bank makes it accumulate.

Each change makes minting EASIER, which is exactly the direction in which an instrument lies to its builder. So
the load-bearing tests here are the ones that must still FAIL to mint: noise, and outcome-blindness of the
eligibility filter. The pre-registered undo stands: if rules start appearing but no key ever reaches two distinct
tasks, this is manufacturing noise and gets reverted.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pytest

from newhorse.redux_arch.dsl import Context, Predicate, make_atom
from newhorse.redux_arch.minting import Mint, two_part_mdl
from newhorse.redux_arch.residual_bank import ResidualBank, family_key
from newhorse.redux_arch import policy as policy_mod
from newhorse.redux_arch.policy import ReduxPolicy

BG, WALL, CUR = 0, 3, 7
H = W = 9
VECS = {"RIGHT": (0, 1), "DOWN": (1, 0), "LEFT": (0, -1), "UP": (-1, 0)}


# ---- generators -------------------------------------------------------------------------------------------------

def _ctx(free: bool, colour: int = 4, rc=(2, 2), trc=(5, 5), vec=(0, 1)) -> Context:
    return Context(focus_rc=rc, focus_colour=colour, target_rc=trc, action_vec=vec,
                   intended_free=free, intended_colour=(None if free else colour))


def _lawful(n: int, seed: int = 0):
    """A residual with ONE real rule in it: the move happens iff the cell entered is free. Structurally the same
    thing the live transition residual produces on a walled room."""
    rng = np.random.RandomState(seed)
    out = []
    for _ in range(n):
        free = bool(rng.rand() < 0.5)
        out.append((_ctx(free, colour=int(rng.randint(1, 6))), free))
    return out


def _noise(n: int, seed: int = 0):
    """Same context distribution, outcomes severed from it. Nothing here is worth a name."""
    rng = np.random.RandomState(seed)
    return [(_ctx(bool(rng.rand() < 0.5), colour=int(rng.randint(1, 6))), bool(rng.rand() < 0.5))
            for _ in range(n)]


# ---- 1. the price: eligibility is counted, and it is counted from the CONTEXTS -----------------------------------

def test_selection_cost_is_charged_over_eligible_candidates_not_constructed_ones():
    rep = {}
    two_part_mdl(_lawful(30, seed=1), max_size=2, report=rep)
    assert rep["n_constructed"] > rep["n_eligible"] > 0, "some constructed candidates must be constant here"
    assert rep["selection_cost_bits"] == pytest.approx(math.log2(rep["n_eligible"]))
    assert rep["selection_cost_bits"] < math.log2(rep["n_constructed"]), "the fix must reduce the price, not raise it"


def test_eligibility_is_blind_to_the_outcomes():
    """THE GUARD THAT MATTERS. The tautology guard is a TYPE property -- φ sees only the before-state -- and a
    filter that consulted the outcomes would quietly break it, letting the price depend on the answer. Invert every
    outcome and the candidate accounting must not move by one."""
    exc = _lawful(30, seed=2)
    a, b = {}, {}
    two_part_mdl(exc, max_size=2, report=a)
    two_part_mdl([(c, not o) for c, o in exc], max_size=2, report=b)
    assert (a["n_constructed"], a["n_eligible"], a["selection_cost_bits"]) == \
           (b["n_constructed"], b["n_eligible"], b["selection_cost_bits"])


def test_the_noise_mint_rate_is_small_AND_DOES_NOT_CLIMB_WITH_SAMPLE_SIZE():
    """The change makes minting easier; this is the test that says how much easier is too much -- and it asserts a
    measured RATE, not a lucky zero, because at these sizes the honest rate is small but not nil.

    The second clause is the load-bearing one. Cheapening the selection cost alone produced 0.75% false mints at
    n=30 and 2.25% at n=80 -- a rate that CLIMBS WITH n. The bank exists to raise n, so a gate whose error grows
    with n would have converted the fix into a machine for manufacturing mints. The parametric-complexity term is
    what flattens it: each sub-stream now pays for the parameter it fitted, and a split pays twice where the
    baseline pays once."""
    def rate(n):
        return sum(1 for s in range(300) if two_part_mdl(_noise(n, seed=1000 + s), max_size=2) is not None) / 300.0
    small, large = rate(30), rate(120)
    assert small <= 0.02 and large <= 0.02, "noise mints at %.3f / %.3f" % (small, large)
    assert large <= max(0.01, 3 * small), "the false-mint rate must not scale up with the pooled sample size"


def test_a_real_rule_still_mints_and_names_the_before_state_fact():
    m = two_part_mdl(_lawful(30, seed=3), max_size=2)
    assert m is not None and m.saved_bits > 0
    assert "INTENDED_FREE" in str(m.predicate)


def test_a_split_pays_for_two_fitted_parameters_where_the_baseline_pays_for_one():
    """The parametric term must be IN the code, not a comment about it: the baseline of a mixed residual has to
    exceed its plug-in entropy, or nothing is being charged for the fit."""
    from newhorse.redux_arch.minting import _entropy_bits, _parametric_bits
    exc = _lawful(30, seed=11)
    rep = {}
    two_part_mdl(exc, max_size=2, report=rep)
    k = sum(1 for _, o in exc if o)
    assert rep["baseline_bits"] == pytest.approx(_entropy_bits(30, k) + _parametric_bits(30))
    assert _parametric_bits(30) > 0 and _parametric_bits(0) == 0.0


def test_five_exceptions_cannot_pay_for_a_name_but_thirty_can():
    """The arithmetic the BANK exists for, stated as a test: the SAME generator, the same rule, the same code --
    only the sample size differs. This is why MINT_UNFIRED is not by itself a verdict on the acceptance rule."""
    assert two_part_mdl(_lawful(5, seed=4), max_size=2) is None
    assert two_part_mdl(_lawful(30, seed=4), max_size=2) is not None


# ---- 2. the bank: evidence, per family, under a decay bound ------------------------------------------------------

def test_family_key_pools_instances_of_one_game_and_nothing_wider():
    assert family_key("ls20-016295f7") == family_key("ls20-9c1e0000") == "ls20"
    assert family_key("tn36-ef4dde99") != family_key("ls20-016295f7")


def test_two_families_never_pool(tmp_path):
    """Colour 4 means different things in different games. Pooling across families would mint a rule about an
    integer -- a perception failure wearing a mint's clothes."""
    b = ResidualBank(root=str(tmp_path), persist=True)
    b.deposit("ls20-aaaa", "ls20#L0#s0.tau", _lawful(6, seed=5))
    b.deposit("tn36-bbbb", "tn36#L0#s0.tau", _lawful(6, seed=6))
    assert len(b.pool("ls20-aaaa")[0]) == 6
    assert len(b.pool("tn36-cccc")[0]) == 6, "a sibling INSTANCE shares the family pool"
    assert b.pool("ls20-aaaa")[1] == ["ls20#L0#s0.tau"]


def test_the_pool_survives_the_process(tmp_path):
    """The whole point. A bank that dies with the episode re-creates the discard it was built to remove."""
    b1 = ResidualBank(root=str(tmp_path))
    for s in range(4):
        b1.deposit("ls20-aaaa", "ls20#L0#s%d.tau" % s, _lawful(5, seed=s))
    b2 = ResidualBank(root=str(tmp_path))                     # a fresh object == a fresh process
    pool, tasks = b2.pool("ls20-aaaa")
    assert len(pool) == 20 and len(tasks) == 4


def test_the_bank_holds_evidence_and_never_a_conclusion(tmp_path):
    b = ResidualBank(root=str(tmp_path))
    b.deposit("ls20-aaaa", "t0", _lawful(6, seed=7))
    blob = json.load(open(os.path.join(str(tmp_path), "ls20.json"), encoding="utf-8"))
    text = json.dumps(blob)
    for forbidden in ("predicate", "phi", "minted", "verdict", "saved_bits", "answer"):
        assert forbidden not in text, "a banked conclusion could skip the acceptance rule; only evidence may persist"
    assert set(blob["deposits"][0]["exceptions"][0][0]) == {
        "focus_rc", "focus_colour", "target_rc", "action_vec", "intended_free", "intended_colour"}


def test_age_decay_forgets_a_regime_that_stopped_recurring(tmp_path):
    b = ResidualBank(root=str(tmp_path), max_age=3, capacity=10_000)
    for s in range(10):
        b.deposit("ls20-aaaa", "t%d" % s, _lawful(2, seed=s))
    tasks = b.pool("ls20-aaaa")[1]
    assert tasks == ["t6", "t7", "t8", "t9"], "serial 10 keeps only deposits within max_age=3"


def test_capacity_evicts_oldest_first(tmp_path):
    b = ResidualBank(root=str(tmp_path), max_age=10_000, capacity=9)
    for s in range(5):
        b.deposit("ls20-aaaa", "t%d" % s, _lawful(4, seed=s))
    pool, tasks = b.pool("ls20-aaaa")
    assert len(pool) <= 9 and tasks[-1] == "t4" and "t0" not in tasks


def test_an_empty_residual_is_not_banked(tmp_path):
    b = ResidualBank(root=str(tmp_path))
    assert b.deposit("ls20-aaaa", "t0", []) == -1
    assert b.stats("ls20-aaaa")["deposits"] == 0


def test_exclude_task_separates_what_the_past_said_from_what_this_segment_said(tmp_path):
    b = ResidualBank(root=str(tmp_path))
    b.deposit("ls20-aaaa", "past", _lawful(4, seed=8))
    b.deposit("ls20-aaaa", "now", _lawful(4, seed=9))
    assert b.pool("ls20-aaaa", exclude_task="now")[1] == ["past"]


# ---- 3. the wiring: what the receipt is allowed to claim ---------------------------------------------------------

def _board(rc, walls=()):
    g = np.zeros((H, W), dtype=int)
    for w in walls:
        g[w] = WALL
    g[rc] = CUR
    return g


def _room(seed=0, n=44, wall_frac=0.30):
    rng = np.random.RandomState(seed)
    walls = {(r, c) for r in range(H) for c in range(W) if rng.rand() < wall_frac}
    start = (H // 2, W // 2)
    walls.discard(start)
    labels = ["RIGHT", "DOWN", "LEFT", "UP"]
    rc, frames, acts = start, [_board(start, walls)], ["RESET"]
    for lbl in [labels[i] for i in rng.randint(0, 4, size=n)]:
        dr, dc = VECS[lbl]
        nr, nc = rc[0] + dr, rc[1] + dc
        if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in walls:
            rc = (nr, nc)
        frames.append(_board(rc, walls))
        acts.append(lbl)
    return frames, acts


def _armed(gid="synthetic-0000"):
    pol = ReduxPolicy(game_id=gid)
    pol.cursor, pol.vecs, pol.passable, pol.stride = CUR, dict(VECS), {BG}, 1
    return pol


def _feed(pol, frames, acts):
    for f, a in zip(frames, acts):
        pol.frames.append(np.asarray(f))
        pol.acts.append(a)
        pol.chain.note_step()


def test_the_first_segment_has_no_past_to_pool_and_says_so(tmp_path):
    pol = _armed()
    pol.bank = ResidualBank(root=str(tmp_path))
    _feed(pol, *_room(seed=1))
    pol._close_segment("death")
    ev = pol.receipts[0]
    assert ev.pool_attempted is False, "a pool that IS this segment adds nothing and must not be reported as a retry"
    assert ev.n_eligible > 0 and ev.selection_cost_bits > 0, "the gate must be on the record next to the verdict"


def test_the_residual_is_banked_even_when_the_fresh_mint_succeeded(tmp_path):
    """The discard this change removes is unconditional. Banking only failures would make the pool a record of
    where the agent was weakest rather than of what it saw."""
    pol = _armed()
    pol.bank = ResidualBank(root=str(tmp_path))
    _feed(pol, *_room(seed=1))
    pol._close_segment("death")
    assert pol.receipts[0].minted
    assert pol.bank.stats(pol.game_id)["deposits"] == 1


def test_a_pooled_mint_is_credited_to_exactly_one_task(monkeypatch, tmp_path):
    """THE LOAD-BEARING WIRING TEST. A pooled mint uses evidence from many tasks. Crediting it to all of them
    would clear echo_threshold=2 in one call, auto-fill Γ, and make MINTED_UNUSED -- the single code that indicts
    the architecture -- reachable by bookkeeping instead of by play. It must count as ONE task: the current one."""
    pol = _armed()
    pol.bank = ResidualBank(root=str(tmp_path))
    for s in range(3):                                        # fill the pool from earlier tasks
        pol.bank.deposit(pol.game_id, "past#%d" % s, _lawful(6, seed=s))
    phi = Predicate(frozenset({make_atom("INTENDED_FREE")}))
    calls = {"n": 0}

    def fake_mdl(exc, max_size=2, report=None):
        calls["n"] += 1
        if report is not None:
            report.update(n_constructed=10, n_eligible=4, selection_cost_bits=2.0)
        return None if calls["n"] == 1 else Mint(predicate=phi, saved_bits=9.0, support=len(exc))

    monkeypatch.setattr(policy_mod, "two_part_mdl", fake_mdl)
    _feed(pol, *_room(seed=1))
    pol._close_segment("death")

    ev = pol.receipts[0]
    assert ev.minted_from_pool and ev.minted and ev.pool_attempted
    assert len(ev.pool_tasks) >= 3, "the pool really did span several tasks"
    assert pol.echo.echo_tasks(phi) == [ev.task_id], "one mint, one task -- never one per contributing task"
    assert ev.echo_count == 1 and ev.promoted is False, "a single pooled mint cannot promote itself into Γ"


def test_the_pooled_retry_only_runs_when_the_fresh_residual_failed(monkeypatch, tmp_path):
    """The fresh attempt is left untouched so the pre-change measurement stays comparable. If a successful fresh
    mint also triggered a pooled one, `minted` would stop meaning what it meant in the baseline sweep."""
    pol = _armed()
    pol.bank = ResidualBank(root=str(tmp_path))
    for s in range(3):
        pol.bank.deposit(pol.game_id, "past#%d" % s, _lawful(6, seed=s))
    seen = {"n": 0}
    real = policy_mod.two_part_mdl

    def counting(exc, max_size=2, report=None):
        seen["n"] += 1
        return real(exc, max_size=max_size, report=report)

    monkeypatch.setattr(policy_mod, "two_part_mdl", counting)
    _feed(pol, *_room(seed=1))
    pol._close_segment("death")
    assert pol.receipts[0].minted and seen["n"] == 1, "a fresh mint must not be followed by a pooled attempt"
