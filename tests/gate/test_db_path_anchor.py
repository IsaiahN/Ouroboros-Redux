"""THE DATABASE PATH IS AN ANCHOR, AND AN ANCHOR DOES NOT MOVE WITH THE CALLER.

THE DEFECT (measured 2026-08-21). The GM's rule is that agent data lives ONLY under
.runs/. Thirty-five production sites defaulted ``db_path`` to the RELATIVE string
"core_data.db". A relative default means every process opens or creates a database at
whatever cwd it happens to have. Fleet workers were correct BY ACCIDENT -- the supervisor
spawns them with ``cwd=<their box>`` (swarm_supervisor.py:258) -- while the suite, the
tools, and any manual run from the repo root silently created a SECOND database there and
read and wrote it believing it was the agent's. A 3.9 MB, 282-table core_data.db kept
reappearing at the repo root; deleting it did not stop it coming back, because the cause
was a default, not a file.

D-6 (database_logger.py:56-63) had already found half of this: the log handler was built
at IMPORT time, so merely importing the engines package created a database at the
importer's cwd. D-6 deferred schema init to the first EMIT. That stopped the empty shell.
It did not stop a real database appearing the moment anything actually logged from the
root -- which every suite run does. D-6 removed the cheapest symptom; D-7 removes the
cause, and F5 below turns D-6's deferral into an enforced property rather than a comment.

THE LAWS.

  FIGURE 10, "install what can be violated" -- **ASSERTED**, by F2 and F4 together.
      A relative default is a convention that nothing can check: the rule lived in prose
      and was enforced by nobody. F2 asserts the resolver REFUSES, loudly and by name,
      rather than falling back or redirecting. F4 asserts the tree cannot quietly grow a
      thirty-sixth site. Neither is an appeal to reviewer attention -- both are mechanism.

  FIGURE 2, "the anchor must not update" -- **ASSERTED**, by F1.
      A path whose meaning changes with the caller's cwd is an anchor that moves. F1 does
      not merely check that three cwds each land somewhere under .runs/; it asserts that
      the repo root and a tmp dir resolve to the SAME ABSOLUTE PATH. That equality is the
      figure. A test that only checked "it's under .runs/" would pass on a resolver that
      still moved, so long as it moved within the sanctioned directory.

  **ASSUMED**, and named so it is not mistaken for proven: that .runs/ is the correct
      home at all. That is the GM's rule, taken as given here. This file enforces the
      rule; it does not justify it. Also assumed: that the fleet's per-box separation is
      worth preserving. It is not re-derived -- it was established on 2026-08-20 and is
      recorded at symbolic_reasoning_engine.py:48-62, where anchoring to the repo root
      instead had put all 25 workers on ONE file, "a single evidence pool wearing 25
      boxes' clothes". F1's box case pins that behaviour so this fix cannot undo it.

THE KNOWN-NEGATIVE is F5, and it is the one that matters. F1 and F3 would both pass on a
resolver that returned correct-looking strings while something else, elsewhere, still
created a database at the root -- which is exactly the failure D-6 left standing. F5
tests the FILESYSTEM, not the return value.
"""
from __future__ import annotations

import ast
import glob
import os
import subprocess
import sys
import tempfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from database_interface import (  # noqa: E402
    DEFAULT_DB_NAME,
    RUNS_ROOT,
    DatabaseInterface,
    DatabasePathOutsideRuns,
    resolve_db_path,
)

# ─────────────────────────────────────────────────────────────────────────────
# F1 · the default resolves under .runs/ and nowhere else, from three cwds
# ─────────────────────────────────────────────────────────────────────────────

def test_f1_default_resolves_under_runs_from_three_cwds(monkeypatch):
    """The RESOLVED PATH is asserted, not the fact that resolution succeeded.

    ``cwd`` is injected rather than os.chdir'd: chdir is process-global and would
    make this test's outcome depend on execution order under -p xdist.
    """
    monkeypatch.delenv("DATABASE_PATH", raising=False)

    box = os.path.join(str(RUNS_ROOT), "swarm", "ar25")
    tmp = tempfile.gettempdir()

    from_root = resolve_db_path(cwd=REPO)
    from_box = resolve_db_path(cwd=box)
    from_tmp = resolve_db_path(cwd=tmp)

    # The exact paths, spelled out.
    assert from_root == os.path.join(str(RUNS_ROOT), DEFAULT_DB_NAME), from_root
    assert from_box == os.path.join(box, DEFAULT_DB_NAME), from_box
    assert from_tmp == os.path.join(str(RUNS_ROOT), DEFAULT_DB_NAME), from_tmp

    # FIGURE 2, stated as an equality: two unrelated cwds, neither of them a box,
    # give the SAME absolute path. This is what "the anchor does not update" means,
    # and it is strictly stronger than "both are under .runs/".
    assert from_root == from_tmp

    # Every branch absolute, and every branch inside the sanctioned directory.
    for p in (from_root, from_box, from_tmp):
        assert os.path.isabs(p), p
        assert p.startswith(str(RUNS_ROOT) + os.sep), p

    # The box branch is NOT the anchor branch -- the fleet's per-box separation
    # survives. If this ever collapses, 25 workers share one evidence pool again.
    assert from_box != from_root


# ─────────────────────────────────────────────────────────────────────────────
# F2 · a default landing outside .runs/ RAISES, naming the path.  CONSTRUCTED.
# ─────────────────────────────────────────────────────────────────────────────

def test_f2_default_outside_runs_raises_naming_the_path(monkeypatch, tmp_path):
    """Constructed: an ABSOLUTE DATABASE_PATH pointing outside .runs/.

    This is the operator's default, not a caller's explicit argument, so the rule
    applies to it -- and the refusal must be a raise, not a warning and not a
    silent redirect into .runs/. A redirect would be the same class of bug as the
    original: the process would carry on believing it had the database it asked for.
    """
    outside = tmp_path / "evil.db"
    monkeypatch.setenv("DATABASE_PATH", str(outside))

    with pytest.raises(DatabasePathOutsideRuns) as exc:
        resolve_db_path()

    msg = str(exc.value)
    assert str(outside) in msg, "the refusal must NAME the offending path: %s" % msg
    assert ".runs" in msg, "the refusal must state the RULE: %s" % msg

    # Not a fallback: nothing was created at the refused location, and nothing was
    # quietly substituted for it.
    assert not outside.exists()


def test_f2b_the_refusal_is_reachable_only_by_the_default(monkeypatch, tmp_path):
    """The same path that RAISES as a default is ACCEPTED as an explicit argument.

    Without this pair, F2 could be satisfied by a resolver that simply refused every
    path outside .runs/ including the ones tests must be able to use -- which would
    make the suite untestable and invite the escape hatch to be reopened badly.
    """
    outside = tmp_path / "evil.db"
    monkeypatch.setenv("DATABASE_PATH", str(outside))

    with pytest.raises(DatabasePathOutsideRuns):
        resolve_db_path()

    assert resolve_db_path(str(outside)) == str(outside)


# ─────────────────────────────────────────────────────────────────────────────
# F3 · an explicit caller-supplied path is honoured UNCHANGED
# ─────────────────────────────────────────────────────────────────────────────

def test_f3_explicit_path_is_honoured_unchanged(tmp_path, monkeypatch):
    """The escape hatch tests need -- asserted end to end, through DatabaseInterface.

    Resolving the string correctly is not enough: the value must survive into the
    object and be the file that is actually opened. A resolver that returned the
    right string while the constructor ignored it would pass a weaker test.
    """
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    explicit = tmp_path / "core_data.db"

    assert resolve_db_path(str(explicit)) == str(explicit)

    db = DatabaseInterface(str(explicit))
    try:
        assert db.db_path == str(explicit)
        assert explicit.exists(), "the explicit path is the file actually opened"
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# F4 · AST: no bare relative "core_data.db" literal in the production globs
# ─────────────────────────────────────────────────────────────────────────────

# The same production scope the wiring gate and _ast_laws use: the live path.
PROD_GLOBS = ("*.py", "engines/**/*.py", "rungs/**/*.py", "src/**/*.py")
PROD_EXCLUDE_NAMES = ("_temp_check.py", "vulture_whitelist.py")

# The resolver's own module DEFINES the name. Exempting the file wholesale would be
# too coarse -- it is exempted for the single assignment `DEFAULT_DB_NAME = ...`,
# checked by name below, so a stray literal elsewhere in it still reds.
RESOLVER_MODULE = "database_interface.py"
RESOLVER_CONSTANT = "DEFAULT_DB_NAME"

# ── KNOWN-OUTSTANDING, and deliberately SELF-LIQUIDATING.
# engines/registry.py:358 and :696 are two live default sites of exactly this defect.
# They were NOT fixed here because that file was owned by a concurrently running builder
# at the time of writing (2026-08-22) and editing it would have collided. The exemption
# is an equality, not a skip: when those sites are fixed, this test REDS and demands the
# entry be deleted. An exemption that can be forgotten is the same species of defect as a
# convention that nothing checks.
KNOWN_OUTSTANDING = {"engines/registry.py": 2}


def _prod_files():
    out = []
    for pat in PROD_GLOBS:
        for p in glob.glob(os.path.join(REPO, pat), recursive=True):
            base = os.path.basename(p)
            if base.startswith("_investigate") or base in PROD_EXCLUDE_NAMES:
                continue
            out.append(p)
    return sorted(set(out))


def _docstring_nodes(tree):
    """Constant nodes that are docstrings -- prose, not paths."""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def _offending_literals(path):
    """Lines in ``path`` holding a bare relative 'core_data.db' string literal.

    Docstrings and comments are excluded: they are prose. The resolver's own
    DEFAULT_DB_NAME assignment is excluded by name. Everything else counts --
    including an absolute-looking literal that merely ENDS in core_data.db, which
    would be a second hard-coded anchor and just as wrong.
    """
    src = open(path, encoding="utf-8", errors="replace").read()
    if DEFAULT_DB_NAME not in src:
        return []
    tree = ast.parse(src)
    docstrings = _docstring_nodes(tree)

    exempt = set()
    if os.path.basename(path) == RESOLVER_MODULE:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == RESOLVER_CONSTANT:
                        exempt.add(id(node.value))

    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if DEFAULT_DB_NAME not in node.value:
            continue
        if id(node) in docstrings or id(node) in exempt:
            continue
        hits.append(node.lineno)
    return hits


def test_f4_no_bare_core_data_db_literal_in_production():
    """THE ANTI-REPEAT MECHANISM. One resolver, called -- not 35 literals rewritten.

    The instruction that produced this fix was explicitly *not* "change the string";
    a second literal is the same defect wearing a different value. This law is what
    stops the tree drifting back, and it is why the fix is a function rather than a
    better constant.
    """
    found = {}
    for path in _prod_files():
        lines = _offending_literals(path)
        if lines:
            found[os.path.relpath(path, REPO).replace("\\", "/")] = len(lines)

    unexpected = {k: v for k, v in found.items() if k not in KNOWN_OUTSTANDING}
    assert not unexpected, (
        "bare relative %r literal(s) in production -- route them through "
        "database_interface.resolve_db_path instead of naming a path:\n  %s"
        % (DEFAULT_DB_NAME, unexpected)
    )

    # The exemption liquidates itself: fixing registry.py reds this line.
    assert found == KNOWN_OUTSTANDING, (
        "the KNOWN_OUTSTANDING set is stale. If engines/registry.py has been fixed, "
        "DELETE its entry from KNOWN_OUTSTANDING in this file -- the exemption exists "
        "only because a concurrent builder owned that file on 2026-08-22.\n"
        "  expected: %s\n  actual:   %s" % (KNOWN_OUTSTANDING, found)
    )


def test_f4_falsifier_a_constructed_violation_reds(tmp_path):
    """R4: the law must FAIL on a violation, or it is decoration.

    A constructed module with a bare default is written to a scratch file and run
    through the same detector the law uses. If this returns nothing, F4 is asleep.
    """
    bad = tmp_path / "fake_engine.py"
    bad.write_text(
        '"""A docstring mentioning core_data.db must NOT count."""\n'
        "class Thing:\n"
        '    def __init__(self, db_path: str = "core_data.db"):\n'
        "        self.db_path = db_path\n",
        encoding="utf-8",
    )
    hits = _offending_literals(str(bad))
    assert hits == [3], (
        "F4's detector missed a constructed bare default (or counted the docstring): %s" % hits
    )

    clean = tmp_path / "good_engine.py"
    clean.write_text(
        '"""core_data.db in prose only."""\n'
        "from database_interface import resolve_db_path\n"
        "class Thing:\n"
        "    def __init__(self, db_path=None):\n"
        "        self.db_path = resolve_db_path(db_path)\n",
        encoding="utf-8",
    )
    assert _offending_literals(str(clean)) == []


# ─────────────────────────────────────────────────────────────────────────────
# F5 · KNOWN-NEGATIVE: importing engines from the repo root creates NO database
# ─────────────────────────────────────────────────────────────────────────────

_IMPORT_PROBE = (
    "import os, sys; sys.path.insert(0, %r); "
    "import engines; "
    "print('IMPORTED')"
)


def _db_snapshot(directory):
    """{path: (size, mtime)} for every *.db directly in ``directory``."""
    snap = {}
    for p in glob.glob(os.path.join(directory, "*.db")):
        try:
            st = os.stat(p)
        except OSError:
            continue
        snap[p] = (st.st_size, st.st_mtime)
    return snap


def test_f5_importing_engines_from_repo_root_creates_no_database():
    """D-6's property, ENFORCED rather than deferred -- and tested on disk.

    Run in a SUBPROCESS with cwd=REPO, because the property is about what a fresh
    interpreter does at the repo root; this pytest process has already imported half
    the tree and could not observe it.

    Note the baseline is a snapshot, not an emptiness check: a stray core_data.db
    already exists at the repo root (3.9 MB, 282 tables, ~716 rows -- the fossil of
    this very defect). The test asserts the import does not CREATE or GROW a
    database, which is the property that matters and is checkable with the fossil
    still present. Deleting it is the GM's call, not this test's.
    """
    before_root = _db_snapshot(REPO)
    anchored = RUNS_ROOT / DEFAULT_DB_NAME
    anchored_before = anchored.exists()

    proc = subprocess.run(  # noqa: S603 -- fixed argv, our interpreter, our probe
        [sys.executable, "-c", _IMPORT_PROBE % REPO],
        cwd=REPO, capture_output=True, text=True, timeout=300,
        check=False,  # a failed import is asserted below, with stderr in the message
    )
    assert "IMPORTED" in proc.stdout, (
        "the engines package failed to import, so this test proves nothing:\n"
        "STDOUT:\n%s\nSTDERR:\n%s" % (proc.stdout, proc.stderr[-4000:])
    )

    after_root = _db_snapshot(REPO)

    created = sorted(set(after_root) - set(before_root))
    assert not created, "importing engines CREATED a database at the repo root: %s" % created

    grew = sorted(p for p in before_root if p in after_root and after_root[p] != before_root[p])
    assert not grew, "importing engines WROTE to a database at the repo root: %s" % grew

    # And it did not create the anchored default either -- import must not touch the
    # filesystem at all, wherever the anchor happens to point.
    if not anchored_before:
        assert not anchored.exists(), (
            "importing engines created the anchored database %s -- resolution must be "
            "PURE; only an actual connect may create a file" % anchored
        )


def test_f5b_resolving_is_pure(monkeypatch, tmp_path):
    """Resolution creates nothing -- the property F5 depends on, tested directly.

    If resolve_db_path ever mkdir'd or touched its result, F5 would start failing
    for a reason that has nothing to do with the engines import, and the D-6
    property would quietly stop being enforced.
    """
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    target = tmp_path / "nested" / "deep" / "core_data.db"

    assert resolve_db_path(str(target)) == str(target)
    assert not target.exists()
    assert not target.parent.exists(), "resolution must not create directories"

    for cwd in (REPO, tempfile.gettempdir(), str(RUNS_ROOT / "swarm" / "zz99")):
        resolve_db_path(cwd=cwd)
    assert not (RUNS_ROOT / "swarm" / "zz99").exists()
