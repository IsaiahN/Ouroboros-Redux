"""
conftest.py -- test isolation for the PERSISTENT residual bank.

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
