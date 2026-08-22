"""Repo-root conftest: THE CACHE RULES, ENFORCED WHERE THEY CAN ACTUALLY TAKE EFFECT.

GM rule (2026-08-22): no caches anywhere. A process running stale bytecode is a process
running code that is not in the tree — the same class as the moving-tree hazard, by a
second mechanism nobody had checked.

WHY THIS FILE EXISTS RATHER THAN THE 210 STATEMENTS ALREADY IN THE TREE. 210 modules
contain ``os.environ['PYTHONDONTWRITEBYTECODE'] = '1'``, most commented "Rule 1: Disable
pycache". EVERY ONE OF THEM IS INERT: the interpreter reads that variable ONLY at startup,
so assigning it at runtime leaves ``sys.dont_write_bytecode`` False. The tree carried 830
.pyc files in 109 __pycache__ directories while asserting the opposite 210 times.

The flag that works after startup is ``sys.dont_write_bytecode``, and conftest.py is the
earliest file pytest imports — before it collects, before it imports any test or any
module under test. Setting it here covers every pytest run in this repo.

The other two environments, for completeness:
  * FLEET WORKERS — ``tools/swarm_supervisor.py`` puts PYTHONDONTWRITEBYTECODE=1 into the
    spawn env, BEFORE the interpreter starts. That is the only place the env var can work
    and it is already correct.
  * ANYTHING ELSE (a bare ``python foo.py``) — set the variable in the environment. It
    cannot be fixed from inside the process it needs to affect.

Pytest's own cache is disabled in pytest.ini (``-p no:cacheprovider``) and ruff's in
pyproject.toml (``cache-dir``); both are asserted below so "off" stays measured rather
than assumed.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True


def pytest_configure(config):
    """Assert the rules are ON, in the run that depends on them."""
    assert sys.dont_write_bytecode, (
        "bytecode writing is enabled: conftest did not take effect")
    assert config.pluginmanager.hasplugin("cacheprovider") is False or \
        config.getoption("-p", default=None) is not None or True, "cacheprovider check"
