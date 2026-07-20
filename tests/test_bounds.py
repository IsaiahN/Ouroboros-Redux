"""
Tests for the HARD BOUNDS (THE MAP §VIII / the Constitution), brick 8.

The bounds are constitutional, not dials: RESET is banned in active play unless earned, the grid is
never downsampled, and there is NO parameter or flag anywhere that turns either off. These tests pin
the FALSIFIABLE properties -- an unearned reset RAISES, a shrunk frame RAISES, no disable path exists,
a broken constitution won't import, and (integration) the loop's mandatory paths carry the bounds.
"""
import sys, os, inspect
import numpy as np
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.bounds import (ResetGate, ResolutionBound, ResetForbidden, verify_constitution,
                             CONSTITUTION_VERIFIED, HARD_BOUNDS)
from newhorse.perception import DownsampleError
from newhorse.agent_loop import AgentLoop


# ---- RESET is banned in active play, earned only ---------------------------------------
def test_fresh_reset_is_banned():
    g = ResetGate()
    assert not g.permitted()                 # nothing is owed at birth
    with pytest.raises(ResetForbidden):
        g.request_reset(reason="unearned")


def test_a_failed_attempt_earns_no_credit():
    g = ResetGate()
    assert g.earn(level_completed=False, reason="attempt that failed") is False
    assert not g.permitted()                 # the exact Redux bug: an attempt must NOT mint a reset
    with pytest.raises(ResetForbidden):
        g.request_reset()


def test_a_completed_level_earns_exactly_one_reset():
    g = ResetGate()
    assert g.earn(level_completed=True, reason="level 1 done") is True
    assert g.permitted()
    g.request_reset(reason="spend the earned credit")   # permitted -- does not raise
    assert not g.permitted()                 # one credit buys exactly ONE reset
    with pytest.raises(ResetForbidden):
        g.request_reset()                    # the second is banned again


# ---- the grid is never downsampled -----------------------------------------------------
def test_downsample_is_rejected():
    rb = ResolutionBound()
    rb.admit(np.zeros((6, 6), dtype=int))    # sets the canonical full resolution
    rb.admit(np.zeros((6, 6), dtype=int))    # same size ok
    with pytest.raises(DownsampleError):
        rb.admit(np.zeros((3, 3), dtype=int))  # smaller -> banned


def test_admit_returns_the_frame_for_inline_use():
    rb = ResolutionBound()
    g = np.arange(16).reshape(4, 4)
    out = rb.admit(g)
    assert out is g and rb.canonical == (4, 4)


# ---- unbypassable: no dial, no disable path --------------------------------------------
def test_no_disable_parameter_on_the_bounds():
    # a `disable`/`allow`/`bypass` constructor arg would be a free variable the caller could bind to
    # escape the bound (the lambda-calculus capture failure mode). There must be none.
    for cls in (ResetGate, ResolutionBound):
        params = set(inspect.signature(cls.__init__).parameters) - {"self"}
        assert params == set(), "%s exposes bypassable params: %r" % (cls.__name__, params)
    # and there is no public method whose name suggests granting a free reset
    forbidden = {"disable", "allow", "bypass", "force_reset", "grant"}
    assert forbidden.isdisjoint(dir(ResetGate))


def test_constitution_is_enforced_at_import():
    # the module ran its self-check at load and refused to import if a bound failed.
    assert CONSTITUTION_VERIFIED is True
    assert verify_constitution() is True
    assert len(HARD_BOUNDS) == 2 and all(isinstance(s, str) for s in HARD_BOUNDS)


def test_nothing_silent():
    g = ResetGate(); g.earn(level_completed=True, reason="x"); g.request_reset(reason="y")
    assert any(e.startswith("EARN") for e in g.log) and any("RESET-PERMITTED" in e for e in g.log)
    rb = ResolutionBound(); rb.admit(np.zeros((4, 4), dtype=int))
    assert any(e.startswith("BOUND") for e in rb.log)


# ---- integration: the loop carries the bounds on its mandatory paths --------------------
def _world_frame(pos=(2, 2), shape=(6, 6), colour=3):
    g = np.zeros(shape, dtype=int); g[pos] = colour; return g


def test_loop_reset_is_banned_until_earned():
    agent = AgentLoop(actions=["A"])
    with pytest.raises(ResetForbidden):
        agent.reset(reason="unearned in active play")     # routes through the gate -> banned
    assert agent.earn_progress(level_completed=True, reason="completed a level") is True
    agent.reset(reason="now earned")                       # permitted -- no raise
    with pytest.raises(ResetForbidden):
        agent.reset()                                      # credit spent -> banned again


def test_loop_perceive_admits_full_res_and_rejects_downsample():
    agent = AgentLoop(actions=["A"])
    agent.perceive(_world_frame(shape=(6, 6)))             # sets canonical (6,6)
    with pytest.raises(DownsampleError):
        agent.perceive(_world_frame(shape=(3, 3)))         # a shrunk frame is refused on the perceive path


def test_earned_reset_preserves_the_brake_integral():
    # THE BRAKE INVARIANT survives a reset: a permitted reset clears the board, NEVER the PE-integral.
    agent = AgentLoop(actions=["A"])
    pos = [2, 2]
    def env(_a):                                            # a tiny moving world so the loop banks surprise
        pos[0] = min(5, pos[0] + 1); return _world_frame(tuple(pos))
    for _ in range(5):
        agent.step(_world_frame(tuple(pos)), env)
    banked = agent.residuals.pe_integral()
    assert banked > 0
    agent.earn_progress(level_completed=True, reason="level done")
    agent.reset(reason="earned")
    assert agent.residuals.pe_integral() == banked         # reset did NOT zero the record of surprise
    assert agent.belief != {}                              # learned lineage preserved across the reset
