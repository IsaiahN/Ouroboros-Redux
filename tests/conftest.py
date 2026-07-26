"""
conftest.py -- test isolation for the two PROCESS-WIDE singletons: the persistent residual bank and the shared Γ.

The bank is a process-wide singleton that writes to disk on purpose, which makes it the one piece of state in
this build that a test run can silently carry into a LIVE run. A synthetic residual banked by a unit test and
later pooled by a real episode would be evidence the agent never saw, minting a rule about a game it never
played -- the exact failure the "bank evidence, never conclusions" rule is meant to make impossible, arriving by
the back door instead. So: every test session redirects the bank to a throwaway directory, and every test starts
with it empty.
"""
import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolate_residual_bank():
    from newhorse.redux_arch import policy
    tmp = tempfile.mkdtemp(prefix="newhorse-bank-test-")
    os.environ["NEWHORSE_BANK_DIR"] = tmp
    policy.RESIDUAL_BANK.root = tmp
    policy.RESIDUAL_BANK.clear()
    yield
    policy.RESIDUAL_BANK.clear()


@pytest.fixture(autouse=True)
def _empty_residual_bank(_isolate_residual_bank):
    """Per-test reset: pooling is cross-episode BY DESIGN, so without this one test's residual becomes another
    test's evidence and a pooled mint would pass for a fresh one."""
    from newhorse.redux_arch import policy
    policy.RESIDUAL_BANK.clear()
    yield


@pytest.fixture(autouse=True)
def _empty_shared_gamma():
    """Per-test reset of Γ. The promoted library is now a process-wide singleton shared by every policy, which makes
    it the SECOND piece of state a test can carry into another test -- and a worse one than the bank, because the
    bank holds evidence that must still pass the mint gate while Γ holds CONCLUSIONS that `explains()` will apply
    directly. Without this, a test that synthesises two mints leaves a φ in Γ, and the next test's policy reports
    `reuse_attempted=True` against a library its game never saw: a manufactured transfer opportunity, and the one
    route by which MINTED_UNUSED -- the only code that indicts the architecture -- becomes reachable by bookkeeping.
    Γ is NOT redirected anywhere (unlike the bank it never touches disk), so clearing is the whole isolation."""
    from newhorse.redux_arch import policy
    policy.SHARED_ECHO.reset()
    yield
    policy.SHARED_ECHO.reset()
