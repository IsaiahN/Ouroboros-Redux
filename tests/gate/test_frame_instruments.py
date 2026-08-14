"""GATE: the deterministic code-quality instruments stay clean on OUR code.

Scope (pyproject.toml [tool.ruff] include): engines/egocentric/, tools/, tests/gate/.
The legacy v4 codebase is deliberately OUT of scope. House law is encoded in
pyproject per-file-ignores: blanket try/except containment in engine/tool code
(EGO code must never crash the host loop), asserts + non-crypto randomness in tests.

Both tests run the instrument as a subprocess with the interpreter running this
suite (the venv python), from the repo root, and put the full instrument output
in the assertion message -- a future violation names itself.
"""
from __future__ import annotations

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RUFF_SCOPE = ["engines/egocentric", "tools", "tests/gate"]


def _run(module_args):
    return subprocess.run(
        [sys.executable, "-m", *module_args],
        cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300, check=False)


def test_ruff_is_clean_on_the_scoped_paths():
    p = _run(["ruff", "check", *RUFF_SCOPE])
    assert p.returncode == 0, (
        "ruff check %s failed (exit %d) -- fix the named violations or, for a "
        "deliberate house-law pattern, extend pyproject.toml per-file-ignores "
        "WITH a comment saying why:\n%s\n%s"
        % (" ".join(RUFF_SCOPE), p.returncode, p.stdout, p.stderr))


def test_vulture_finds_no_dead_code_in_the_engine():
    p = _run(["vulture", "engines/egocentric", "--min-confidence", "80"])
    assert p.returncode == 0, (
        "vulture engines/egocentric --min-confidence 80 failed (exit %d) -- "
        "remove the dead code, or whitelist a legitimate dynamic use:\n%s\n%s"
        % (p.returncode, p.stdout, p.stderr))
