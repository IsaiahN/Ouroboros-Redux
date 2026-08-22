"""
Pytest configuration for the Ouroboros test suite.

This conftest properly sets up sys.path to import modules directly
without triggering the root __init__.py which uses relative imports.
"""

import os
import sys
from pathlib import Path

import pytest

# Disable pycache - per project rules
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

# Add the project root to sys.path BEFORE pytest collects tests
# This allows tests to import modules directly (e.g., from trigger_controller import ...)
# without going through the package's __init__.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ── D-7 (2026-08-22): the `db_path` and `db_connection` fixtures were REMOVED.
# They read `MAIN_DB_PATH = Path(project_root) / "core_data.db"` -- the suite's own
# copy of the defect being fixed, aimed straight at the repo root, and `db_connection`
# did not merely read it: sqlite3.connect CREATES, so any test taking that fixture
# would mint the stray root database the GM keeps deleting. Both had ZERO consumers
# across tests/ (verified by grep for the fixture names before removal), so nothing
# relied on them and no test needed rewriting.
#
# A test that needs a database takes an EXPLICIT path -- `tmp_path / "core_data.db"`
# handed to DatabaseInterface, which honours explicit paths unchanged. Tests must never
# take the anchored default: that default lives under .runs/, which is the agent's
# data, and a test writing there would corrupt a live fleet box.


def _find_pycache(root: str):
    for dirpath, dirnames, _ in os.walk(root):
        parts = set(dirpath.split(os.sep))
        if '.venv' in parts or '.git' in parts:
            continue
        for d in list(dirnames):
            if d == "__pycache__":
                yield os.path.join(dirpath, d)


def pytest_sessionfinish(session, exitstatus):
    """Fail the session if any __pycache__ directories remain after tests."""
    pycaches = list(_find_pycache(project_root))
    if not pycaches:
        return

    # Attempt cleanup first
    for path in pycaches:
        try:
            import shutil
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass

    remaining = [p for p in pycaches if Path(p).exists()]
    if remaining:
        import pytest as _pytest
        _pytest.exit(
            f"Detected __pycache__ inside repo (enforce PYTHONDONTWRITEBYTECODE=1):\n{os.linesep.join(sorted(remaining))}\nRemove them and rerun."
        )
    else:
        print(f"Removed __pycache__ directories:{os.linesep}{os.linesep.join(sorted(pycaches))}")
