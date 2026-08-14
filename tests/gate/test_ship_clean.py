"""W4 B18 GATE: the ship-clean import lint (CK_LEDGER — THE SHIP-CLEAN LAW).

⭐ WHY. Instruments are scaffolding around the building, never parts of it: production
sources must run on Kaggle in a bare venv (stdlib + numpy, no dev deps, no network).
A pytest/hypothesis/ruff/vulture/pydantic/requests import inside production code means
absence of instruments CAN break the agent — the exact failure the law forbids. This
gate AST-walks every production source (engines/**, cognitive_loop.py,
cognitive_game_player.py) and checks every import, top-level and function-level.

ALLOWED: stdlib (sys.stdlib_module_names — the interpreter's own list, never hand-rolled),
numpy, relative imports, and local project modules (engines.* and repo-root modules like
database_interface/event_bus — they ship with the tree). An import whose enclosing
try/except catches ImportError (graceful degradation, e.g. PIL in visual_cortex) is
tolerated: the code is ship-clean BY CONSTRUCTION when the dep is absent.

THE DEBT REGISTER: pre-existing hard violations found when this gate first ran are
pinned below file-by-file — a RATCHET, not an allowlist. Any NEW violation is red; any
pinned entry that disappears (someone fixed it) is ALSO red until the entry is deleted
here (no stale allowlist — the consumer-gate rule applied to this gate itself).

Run pre-build (empty register): failed on scipy (engines/egocentric/agency.py:29,
engines/egocentric/perception.py:23) and arcengine (cognitive_game_player.py:32).
"""
from __future__ import annotations

import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# ── the debt register (ratchet): pre-existing hard violations, routed for fixes ──────
# (module, production file, why it is debt and not a waiver)
PREEXISTING_DEBT = {
    # 2026-08-14: the two scipy entries (agency.py, perception.py) cleared -- imports
    # are now guarded with a pure-numpy fallback (W4 QA F3); the ratchet tightened.
    ("arcengine", "cognitive_game_player.py"):
        "unguarded ARC client import -- the online entry point, absent from a bare venv",
}

PRODUCTION_FILES = ("cognitive_loop.py", "cognitive_game_player.py")
PRODUCTION_DIRS = ("engines",)


def _production_sources():
    files = [os.path.join(REPO, f) for f in PRODUCTION_FILES]
    for d in PRODUCTION_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, d)):
            dirnames[:] = [x for x in dirnames if x != "__pycache__"]
            files.extend(os.path.join(dirpath, f) for f in filenames if f.endswith(".py"))
    return sorted(files)


def _local_project_roots():
    """Top-level module names that ship with the tree: repo-root *.py files plus
    packages -- regular (__init__.py) or namespace (any top-level *.py inside,
    e.g. config/cognitive_parameters.py)."""
    roots = set()
    for name in os.listdir(REPO):
        full = os.path.join(REPO, name)
        if name.endswith(".py"):
            roots.add(name[:-3])
        elif os.path.isdir(full) and not name.startswith("."):
            try:
                entries = os.listdir(full)
            except OSError:
                continue
            if "__init__.py" in entries or any(e.endswith(".py") for e in entries):
                roots.add(name)
    return roots


def _guarded_import_lines(tree):
    """Line numbers of imports whose enclosing try/except catches ImportError-family
    (or broader): graceful-degradation guards -- ship-clean by construction."""
    guarded = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        catches = False
        for h in node.handlers:
            if h.type is None:                                   # bare except
                catches = True
                break
            names = []
            t = h.type
            for sub in ([t.elts] if isinstance(t, ast.Tuple) else [[t]])[0]:
                if isinstance(sub, ast.Name):
                    names.append(sub.id)
                elif isinstance(sub, ast.Attribute):
                    names.append(sub.attr)
            if {"ImportError", "ModuleNotFoundError", "Exception",
                    "BaseException"} & set(names):
                catches = True
        if not catches:
            continue
        for sub in node.body:
            for inner in [sub, *list(ast.walk(sub))]:
                if isinstance(inner, (ast.Import, ast.ImportFrom)):
                    guarded.add(inner.lineno)
    return guarded


def _violations():
    """[(module, relpath, lineno)] for every hard non-stdlib/non-numpy/non-local import."""
    allowed = set(sys.stdlib_module_names) | {"numpy"} | _local_project_roots()
    out = []
    for path in _production_sources():
        rel = os.path.relpath(path, REPO).replace(os.sep, "/")
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        tree = ast.parse(src, filename=rel)                      # a parse error IS a failure
        guarded = _guarded_import_lines(tree)
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:                                   # relative: local by definition
                    continue
                if node.module:
                    mods = [node.module.split(".")[0]]
            for m in mods:
                if m in allowed or node.lineno in guarded:
                    continue
                out.append((m, rel, node.lineno))
    return out


class TestShipClean:

    def test_production_imports_are_stdlib_numpy_or_pinned_debt(self):
        found = _violations()
        new = [(m, f, ln) for (m, f, ln) in found if (m, f) not in PREEXISTING_DEBT]
        assert not new, (
            "SHIP-CLEAN VIOLATION -- production imports beyond stdlib+numpy (the Kaggle "
            "venv will not have these):\n" +
            "\n".join("  %s:%d imports %r" % (f, ln, m) for m, f, ln in new))

    def test_the_debt_register_is_not_stale(self):
        """Every pinned entry must still exist -- a fixed violation must be deleted from
        the register (the no-stale-allowlist rule, applied to this gate itself)."""
        found = {(m, f) for (m, f, _ln) in _violations()}
        stale = sorted(set(PREEXISTING_DEBT) - found)
        assert not stale, (
            "STALE DEBT ENTRIES -- these violations no longer exist; delete them from "
            "PREEXISTING_DEBT so the ratchet tightens:\n" +
            "\n".join("  (%s, %s)" % e for e in stale))

    def test_the_debt_register_never_grows(self):
        """The ratchet's hard ceiling: exactly the three pre-existing violations of
        2026-08-14. Growing this register requires deleting this line consciously."""
        assert len(PREEXISTING_DEBT) <= 3
