"""Tests for the falsified ledger. Each test names the map principle it pins."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.falsified_ledger import FalsifiedLedger


def test_express_before_judge_non_trial_records_nothing():
    # SS9.4.1 + Effectiveness gate: a hypothesis that never actually ran is a NON-TRIAL, not a refutation.
    L = FalsifiedLedger()
    assert L.record("maze_exit", trial_ran=False, made_progress=False, now=0) == "non_trial"
    assert L.weight("maze_exit", now=0) == 0.0
    assert len(L) == 0


def test_registered_unrewarded_trial_is_refuted_and_accumulates():
    # SS9.4.4: a real, registered, unrewarded trial accumulates rejection weight.
    L = FalsifiedLedger(half_life=8.0)
    assert L.record("maze_exit", trial_ran=True, made_progress=False, now=0) == "refuted"
    w1 = L.weight("maze_exit", now=0)
    L.record("maze_exit", trial_ran=True, made_progress=False, now=0)
    w2 = L.weight("maze_exit", now=0)
    assert w2 > w1 > 0
    assert L.is_refuted("maze_exit", now=0)          # crosses the default threshold after repeats


def test_progress_clears_the_reject():
    # If the hypothesis actually did something (reward / residual drop), it is NOT a dead idea.
    L = FalsifiedLedger()
    L.record("cycle_match", trial_ran=True, made_progress=False, now=0)
    L.record("cycle_match", trial_ran=True, made_progress=False, now=1)
    assert L.weight("cycle_match", now=1) > 0
    assert L.record("cycle_match", trial_ran=True, made_progress=True, now=2) == "progress_cleared"
    assert L.weight("cycle_match", now=2) == 0.0


def test_decay_over_logical_clock_is_defeasible():
    # A rejection HALVES over one half_life of attempts -> the ledger never ossifies.
    L = FalsifiedLedger(half_life=4.0)
    L.record("k", trial_ran=True, made_progress=False, now=0, weight=2.0)
    w0 = L.weight("k", now=0)
    w_half = L.weight("k", now=4)                    # one half-life later
    assert math.isclose(w_half, w0 * 0.5, rel_tol=1e-6)
    w_two = L.weight("k", now=8)
    assert math.isclose(w_two, w0 * 0.25, rel_tol=1e-6)


def test_fitness_conditional_gate_drop_reopens():
    # SS9.4.5: decisive new surprise REOPENS a refuted hypothesis (high fitness overrides the gate).
    L = FalsifiedLedger(reopen_surprise=1.0)
    L.record("k", trial_ran=True, made_progress=False, now=0, weight=3.0)
    assert L.weight("k", now=0) == 3.0
    L.reconsider("k", surprise=0.5, now=0)           # partial forgiveness
    assert math.isclose(L.weight("k", now=0), 1.5, rel_tol=1e-6)
    L.reconsider("k", surprise=1.0, now=0)           # decisive -> fully reopened
    assert L.weight("k", now=0) == 0.0
    assert "k" not in L.keys()


def test_bias_is_bounded_soft_deprioritisation():
    # bias in [0,1): a ranker SUBTRACTS it -> de-prioritise, never a hard ban (defeasibility).
    L = FalsifiedLedger()
    assert L.bias("unknown", now=0) == 0.0
    for i in range(20):
        L.record("k", trial_ran=True, made_progress=False, now=0)
    b = L.bias("k", now=0)
    assert 0.9 < b < 1.0                              # strong but never reaches 1.0 (can still be retried)


def test_persistence_round_trip_survives_episodes():
    # The whole point: the reject-memory survives across episodes via an external store.
    store = {}
    L1 = FalsifiedLedger(store, half_life=8.0)
    L1.record("maze_exit", trial_ran=True, made_progress=False, now=0)
    L1.record("maze_exit", trial_ran=True, made_progress=False, now=0)
    # a fresh ledger (next episode) binding the SAME store remembers the refutation
    L2 = FalsifiedLedger(store, half_life=8.0)
    assert math.isclose(L2.weight("maze_exit", now=0), L1.weight("maze_exit", now=0), rel_tol=1e-9)
    assert L2.is_refuted("maze_exit", now=0)


def test_snapshot_load_equivalence():
    L = FalsifiedLedger()
    L.record("a", trial_ran=True, made_progress=False, now=1, weight=2.0)
    snap = L.snapshot()
    L2 = FalsifiedLedger().bind(snap)
    assert math.isclose(L2.weight("a", now=1), L.weight("a", now=1), rel_tol=1e-9)


def test_never_encodes_an_answer_only_agent_dead_ends():
    # The ledger can only ever say what the AGENT itself found unrewarded; there is no setter for a "right answer".
    L = FalsifiedLedger()
    assert not hasattr(L, "set_answer") and not hasattr(L, "correct")
    # unknown keys carry zero information (no injected priors)
    assert L.weight("anything", now=0) == 0.0 and L.bias("anything", now=0) == 0.0


def test_explain_narrates_nothing_silent():
    L = FalsifiedLedger()
    L.record("maze_exit", trial_ran=True, made_progress=False, now=3)
    msg = L.explain("maze_exit", now=3)
    assert "maze_exit" in msg and "DE-PRIORITISE" in msg and "reopens" in msg
    assert "no record" in L.explain("never_seen", now=3)
