"""THE DATA ROOT IS DECIDED BY A RULE, NOT BY WHERE THE PROCESS IS STANDING.

THE DEFECT (record/prereg/PLAN_SWARM_SHAPE.md section 3, items 1-2). Agent data paths
resolved against the CURRENT WORKING DIRECTORY, and were correct only by the accident
that each retired fleet worker's cwd WAS its own game box. Four sites in
``cognitive_loop.py`` and one in ``cognitive_game_player.py`` built
``KnowledgeFabric("ego_fabric", ...)`` -- a RELATIVE root -- and
``database_interface.resolve_db_path`` resolved its default against ``Path.cwd()``.
Put two games in ONE process, which is what the ARC swarm harness does and what the
Kaggle notebook must do, and they share one cwd: both fabrics and both databases FUSE.
Nothing raises. One game's atoms simply appear in another game's library, which is the
contamination the firewall exists to prevent, arriving by a path nobody watches.

THE RULE (implemented once, in ``data_root.py``)::

    OURO_DATA_ROOT              env var, explicit     -- wins if set
    else /kaggle/working/ouro   if /kaggle/working IS A DIRECTORY
    else <repo>/.runs           if the repo marker is present
    else RAISE, naming all three

THE LAWS.

  FIGURE 2, "the anchor must not update" -- **ASSERTED**, by F1 and F3.
      A path whose meaning changes with the caller's directory is an anchor that
      moves. F3 is the figure stated as an equality: the SAME CODE, WITH NO CWD
      CHANGE BETWEEN THE TWO CALLS, selects the Kaggle branch or the local branch
      purely from what exists on disk. The point of holding the cwd fixed across
      both calls is that a resolver which still consulted it could not produce two
      different correct answers -- so the cwd is demonstrated to be IRRELEVANT to
      the answer, not merely unused in one path.

  FIGURE 10, "install what can be violated" -- **ASSERTED**, by F2 and F4.
      A relative default is a convention nothing can check. F2 asserts the fourth
      branch is a RAISE naming all three routes and what it looked for -- not a
      fallback, because a fallback is the defect wearing a nicer name. F4 asserts
      the tree cannot quietly grow a new cwd-derived data path, and its own
      falsifier proves the detector fires.

  FIGURE 6 / THE FIREWALL -- **ASSERTED**, by F1.
      Cross-game fabric fusion would put one game's atoms in another's library. F1
      is the instrument: two games driven through the REAL loop in ONE process,
      both fabrics read back, and the disjointness asserted on the BYTES, not on
      the paths -- a path comparison would pass on a resolver that returned two
      correct-looking strings while something downstream still merged the streams.

  **ASSUMED**, and named so it is not mistaken for proven:
      * that the three branches are the RIGHT three, and that ``/kaggle/working`` is
        where the notebook may write. That is the GM's rule and the competition's
        constraint; this file enforces them and does not justify them.
      * that ``pyproject.toml`` identifies the repo. Any marker would do; this one is
        asserted to exist so the assumption cannot rot silently.
      * that a per-game root is the right GRAIN. Two games separated is asserted;
        that a game is the correct unit of separation is taken from the plan.

THE KNOWN-NEGATIVE is ``test_known_negative_explicit_path_is_honoured_unchanged``:
an explicit caller-supplied path still comes back verbatim. Without it F2 could be
satisfied by a resolver that refused everything, which would make the suite untestable
and invite the escape hatch to be reopened badly.

NO GAME IDENTITY APPEARS HERE. The two games in F1 are called "alpha" and "beta".
"""
from __future__ import annotations

import ast
import glob
import json
import os
import sqlite3
import sys
import types

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from data_root import (  # noqa: E402
    ENV_VAR,
    GAMES_DIRNAME,
    KAGGLE_SUBDIR,
    KAGGLE_WORKING,
    LOCAL_SUBDIR,
    REPO_MARKER,
    DataRootUnresolved,
    game_data_root,
    resolve_data_root,
)
from database_interface import resolve_db_path  # noqa: E402

GAME_A = "alpha"
GAME_B = "beta"


# ─────────────────────────────────────────────────────────────────────────────
# F1 · TWO GAMES IN ONE PROCESS -- THE FALSIFIER FOR THE ACTUAL DEFECT
# ─────────────────────────────────────────────────────────────────────────────

def _drive(loop, game_id, steps=6):
    """A few real cycles: cycle() -> record_result(), the path that lazily builds
    the fabric in production (cognitive_loop.py, the PHASE 3a init). Nothing is
    stubbed -- a fabric written by a mock would prove nothing about the loop."""
    import io
    from contextlib import redirect_stdout

    loop.start_game(game_id, [1, 2, 3, 4, 5, 6], max_actions=64)
    obs = types.SimpleNamespace(levels_completed=0)
    rng = np.random.RandomState(20260822)
    frame = rng.randint(0, 4, size=(8, 8)).astype(int)
    buf = io.StringIO()
    with redirect_stdout(buf):
        for i in range(steps):
            loop.cycle(frame, obs)
            post = frame.copy()
            post[i % 8, (i * 3) % 8] = (int(post[i % 8, (i * 3) % 8]) + 1) % 4
            loop.record_result(post_frame=post, frame_changed=True,
                               score_delta=0.0, level_changed=False, new_level=0)
            frame = post
        loop.end_game()
    return buf.getvalue()


def _stream_files(root):
    out = {}
    for base, _dirs, files in os.walk(root):
        for f in sorted(files):
            p = os.path.join(base, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root).replace(os.sep, "/")] = fh.read()
    return out


def test_f1_two_games_in_one_process_write_disjoint_fabrics(tmp_path, monkeypatch):
    """THE DEFECT, CONSTRUCTED AND FALSIFIED. Two loops, two per-game roots, ONE
    process, ONE cwd -- and two fabrics with nothing of each other in them.

    Before the fix both loops passed the relative root "ego_fabric" and this test
    could not have been written: there was one directory and one set of streams.
    """
    from cognitive_loop import EGO_FABRIC_DIRNAME, CognitiveLoop

    monkeypatch.setenv(ENV_VAR, str(tmp_path))
    root_a = game_data_root(GAME_A)
    root_b = game_data_root(GAME_B)
    assert root_a != root_b

    loop_a = CognitiveLoop(data_root=str(root_a))
    loop_b = CognitiveLoop(data_root=str(root_b))
    loop_a._ego_agent_id = "agent_a"
    loop_b._ego_agent_id = "agent_b"

    # ONE cwd for both, and it is neither of their roots. That is the whole point.
    cwd_before = os.getcwd()
    _drive(loop_a, GAME_A)
    _drive(loop_b, GAME_B)
    assert os.getcwd() == cwd_before, "the test itself must not move the process"

    fab_a = os.path.join(str(root_a), EGO_FABRIC_DIRNAME)
    fab_b = os.path.join(str(root_b), EGO_FABRIC_DIRNAME)
    assert loop_a._ego_fabric is not None and loop_b._ego_fabric is not None, (
        "a loop failed to build its fabric at all -- F1 would then pass vacuously")
    assert os.path.normcase(loop_a._ego_fabric.root) == os.path.normcase(fab_a)
    assert os.path.normcase(loop_b._ego_fabric.root) == os.path.normcase(fab_b)

    streams_a = _stream_files(fab_a)
    streams_b = _stream_files(fab_b)
    assert streams_a, "game %s wrote no fabric stream: nothing to compare" % GAME_A
    assert streams_b, "game %s wrote no fabric stream: nothing to compare" % GAME_B

    # THE DISJOINTNESS, ASSERTED ON THE BYTES. A path comparison would pass on a
    # resolver that returned two correct strings while the writes still merged.
    for rel, blob in streams_a.items():
        assert GAME_B.encode() not in blob, (
            "game %s appears inside game %s's fabric stream %r -- the fabrics fused"
            % (GAME_B, GAME_A, rel))
    for rel, blob in streams_b.items():
        assert GAME_A.encode() not in blob, (
            "game %s appears inside game %s's fabric stream %r -- the fabrics fused"
            % (GAME_A, GAME_B, rel))

    # ...and PARSED, not just scanned: every record that names a game names its
    # OWN game. The byte check above would miss a record whose game arrived
    # base64'd or split; this one reads the field the streams actually carry.
    for fab, mine, theirs in ((fab_a, GAME_A, GAME_B), (fab_b, GAME_B, GAME_A)):
        games, n = set(), 0
        for rel, blob in _stream_files(fab).items():
            for raw in blob.decode("utf-8", "replace").splitlines():
                if not raw.strip():
                    continue
                n += 1
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(rec, dict) and "game" in rec:
                    games.add(str(rec["game"]))
            assert rel  # every stream accounted for by name
        assert n, "no records at all under %s" % fab
        assert games == {mine}, (
            "%s holds records for %r; expected only %r. %s is in there: %s"
            % (fab, sorted(games), mine, theirs, theirs in games))

    # The per-game root is a LEAF of the shared root, not a root of its own tree:
    # a games/ directory nested inside a game's root would mean the level was
    # applied twice and the two would eventually meet.
    assert not os.path.exists(os.path.join(str(root_a), GAMES_DIRNAME))


def test_f1b_two_games_in_one_process_resolve_disjoint_databases(tmp_path, monkeypatch):
    """The database half of the same defect: ONE cwd, two per-game roots, two
    databases that are read back and compared. sqlite is used directly so the
    subject is the RESOLVER; that DatabaseInterface honours the resolved path end
    to end is asserted by tests/gate/test_db_path_anchor.py F3."""
    monkeypatch.setenv(ENV_VAR, str(tmp_path))
    monkeypatch.delenv("DATABASE_PATH", raising=False)

    db_a = resolve_db_path(root=game_data_root(GAME_A))
    db_b = resolve_db_path(root=game_data_root(GAME_B))
    assert db_a != db_b, "two games resolved to ONE database: %s" % db_a
    assert os.path.isabs(db_a) and os.path.isabs(db_b)

    for path, marker in ((db_a, GAME_A), (db_b, GAME_B)):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        try:
            conn.execute("CREATE TABLE atoms (who TEXT)")
            conn.execute("INSERT INTO atoms VALUES (?)", (marker,))
            conn.commit()
        finally:
            conn.close()

    for path, mine, theirs in ((db_a, GAME_A, GAME_B), (db_b, GAME_B, GAME_A)):
        conn = sqlite3.connect(path)
        try:
            rows = [r[0] for r in conn.execute("SELECT who FROM atoms")]
        finally:
            conn.close()
        assert rows == [mine], (
            "%s holds %r -- the two games' databases fused" % (path, rows))
        assert theirs not in rows


# ─────────────────────────────────────────────────────────────────────────────
# F2 · AN UNRESOLVABLE ROOT RAISES, NAMING ALL THREE BRANCHES.  CONSTRUCTED.
# ─────────────────────────────────────────────────────────────────────────────

def test_f2_unresolvable_root_raises_naming_all_three_branches(tmp_path):
    """Env unset, no /kaggle/working, no repo marker -- all three constructed.

    THE RAISE IS THE MECHANISM, not a diagnostic nicety: the only fallback
    available is the cwd, and a cwd fallback is the defect this build removes. A
    resolver that returned SOMETHING here would be the same bug with a better name.
    """
    no_kaggle = tmp_path / "no_kaggle_here"          # deliberately never created
    bare = tmp_path / "not_a_repo"
    bare.mkdir()
    assert not (bare / REPO_MARKER).exists()

    with pytest.raises(DataRootUnresolved) as exc:
        resolve_data_root(env={}, kaggle_working=str(no_kaggle), repo_dir=str(bare))

    msg = str(exc.value)
    for needle in (ENV_VAR, KAGGLE_WORKING.rstrip("/"), REPO_MARKER, LOCAL_SUBDIR):
        assert needle in msg, "the refusal must name %r:\n%s" % (needle, msg)
    assert str(no_kaggle) in msg, "the refusal must say WHERE it looked:\n%s" % msg
    assert str(bare) in msg, "the refusal must say WHERE it looked:\n%s" % msg

    # Nothing was created on the way to refusing: resolution is pure.
    assert not no_kaggle.exists()
    assert not (bare / LOCAL_SUBDIR).exists()


def test_f2b_a_relative_env_root_raises_rather_than_being_joined_to_the_cwd(tmp_path):
    """The one route by which the cwd could sneak back in, closed by name.

    ``OURO_DATA_ROOT=data`` looks explicit and is not: os.path.abspath would join
    it to the cwd, which is exactly the defect arriving through the environment.
    """
    with pytest.raises(DataRootUnresolved) as exc:
        resolve_data_root(env={ENV_VAR: "relative/data"})
    assert "RELATIVE" in str(exc.value).upper()
    assert ENV_VAR in str(exc.value)


def test_f2c_a_game_id_cannot_escape_its_root(tmp_path):
    """A traversal or a separator in a game id would let one game's root land
    inside another's -- the fusion defect through the id rather than the cwd."""
    for bad in ("..", "../beta", "a/b", "a\\b", "", "   ", ".hidden"):
        with pytest.raises(ValueError):
            game_data_root(bad, root=tmp_path)
    good = game_data_root(GAME_A, root=tmp_path)
    assert good == tmp_path / GAMES_DIRNAME / GAME_A


# ─────────────────────────────────────────────────────────────────────────────
# F3 · THE BRANCHES ARE SELECTED BY WHAT EXISTS, WITH NO CWD CHANGE BETWEEN THEM
# ─────────────────────────────────────────────────────────────────────────────

def test_f3_kaggle_and_local_branches_selected_with_the_cwd_held_fixed(tmp_path):
    """FIGURE 2 AS AN EQUALITY. Same code, same cwd, two answers -- so the answer
    cannot be a function of the cwd.

    Both branches are CONSTRUCTED: a directory standing in for /kaggle/working,
    and a directory carrying the repo marker. Neither call chdirs, and the cwd is
    asserted unchanged across both.
    """
    kaggle = tmp_path / "kaggle_working"
    kaggle.mkdir()
    repo = tmp_path / "a_repo"
    repo.mkdir()
    (repo / REPO_MARKER).write_text("[tool.ruff]\n", encoding="utf-8")

    before = os.getcwd()
    from_kaggle = resolve_data_root(env={}, kaggle_working=str(kaggle), repo_dir=str(repo))
    from_local = resolve_data_root(env={}, kaggle_working=str(tmp_path / "absent"),
                                   repo_dir=str(repo))
    after = os.getcwd()

    assert before == after, "the cwd moved between the two calls -- F3 proves nothing"
    assert from_kaggle == kaggle / KAGGLE_SUBDIR, from_kaggle
    assert from_local == repo / LOCAL_SUBDIR, from_local
    assert from_kaggle != from_local

    # The Kaggle branch OUTRANKS the local one: on Kaggle the repo is also present
    # (the notebook ships the tree) and the repo is not writable there.
    assert from_kaggle == resolve_data_root(
        env={}, kaggle_working=str(kaggle), repo_dir=str(repo))

    # And the env var outranks both, from the same fixed cwd.
    declared = tmp_path / "declared"
    assert resolve_data_root(env={ENV_VAR: str(declared)},
                             kaggle_working=str(kaggle), repo_dir=str(repo)) == declared
    assert os.getcwd() == before


def test_f3b_the_local_branch_marker_actually_marks_this_repo():
    """The ASSUMPTION, made checkable. If the marker ever leaves the tree, the
    local branch stops resolving and this says so in one line instead of in a
    confusing raise from somewhere else."""
    assert os.path.isfile(os.path.join(REPO, REPO_MARKER)), (
        "the repo marker %r is gone from %s -- data_root's local branch is now "
        "unreachable and every local run raises" % (REPO_MARKER, REPO))
    assert str(resolve_data_root(env={},
                                 kaggle_working=os.path.join(REPO, "no_kaggle"))) \
        == os.path.join(REPO, LOCAL_SUBDIR)


# ─────────────────────────────────────────────────────────────────────────────
# F4 · AST: NO PRODUCTION MODULE RESOLVES A DATA PATH FROM THE CWD
# ─────────────────────────────────────────────────────────────────────────────

# The production scope the wiring gate and _ast_laws use, plus tools/: the tool
# that measures the live path used to chdir so the loop's relative fabric root
# landed in scratch, which is the same defect one layer out. It was fixed rather
# than exempted, so the exemption table below is EMPTY -- and an empty table that
# an entry can be added to is still a mechanism; a table with no entries and no
# way to add one would just be a stricter rule pretending to be a policy.
PROD_GLOBS = ("*.py", "engines/**/*.py", "rungs/**/*.py", "src/**/*.py",
              "tools/**/*.py")
PROD_EXCLUDE_NAMES = ("_temp_check.py", "vulture_whitelist.py")

# rel path -> reason. A cwd use here must be for a NON-DATA purpose and must say so.
CWD_EXEMPTIONS: dict = {}


def _prod_files():
    out = []
    for pat in PROD_GLOBS:
        for p in glob.glob(os.path.join(REPO, pat), recursive=True):
            base = os.path.basename(p)
            if base.startswith("_investigate") or base in PROD_EXCLUDE_NAMES:
                continue
            out.append(p)
    return sorted(set(out))


def _cwd_calls(path):
    """Lines calling ``os.getcwd()``, a bare ``getcwd()``, or ``Path.cwd()``.

    AST, not text: a docstring or a comment naming ``Path.cwd()`` is prose and must
    not count -- database_interface.py's own docstring explains the defect by name.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    if "getcwd" not in src and "cwd" not in src:
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        bare = isinstance(f, ast.Name) and f.id == "getcwd"
        dotted = isinstance(f, ast.Attribute) and f.attr in ("getcwd", "cwd")
        if bare or dotted:
            hits.append(node.lineno)
    return sorted(set(hits))


def test_f4_no_production_module_resolves_a_data_path_from_the_cwd():
    """THE ANTI-REPEAT MECHANISM. One resolver, called -- not N relative defaults.

    The instruction was explicitly not "fix the five sites": a sixth site is the
    same defect at a different line. This law is what stops the tree drifting back.
    """
    found = {}
    for path in _prod_files():
        lines = _cwd_calls(path)
        if lines:
            found[os.path.relpath(path, REPO).replace("\\", "/")] = lines

    unexpected = {k: v for k, v in found.items() if k not in CWD_EXEMPTIONS}
    assert not unexpected, (
        "production module(s) resolving a path from the current working directory: "
        "%s\nA cwd-derived data path is shared by every game in the process. Take "
        "the root from data_root.resolve_data_root()/game_data_root(), or add an "
        "entry to CWD_EXEMPTIONS in this file WITH A REASON if the use is genuinely "
        "not a data path." % unexpected)

    stale = sorted(k for k in CWD_EXEMPTIONS if k not in found)
    assert not stale, (
        "CWD_EXEMPTIONS names %r, which no longer uses the cwd -- delete the entry. "
        "An exemption that can be forgotten is the same species of defect as a "
        "convention nothing checks." % stale)
    thin = [k for k, v in CWD_EXEMPTIONS.items() if len(str(v).strip()) < 20]
    assert not thin, "unreasoned exemption(s): %r" % thin


def test_f4_falsifier_a_constructed_violation_reds(tmp_path):
    """R4: the law must FAIL on a violation, or it is decoration."""
    bad = tmp_path / "fake_organ.py"
    bad.write_text(
        '"""A docstring naming Path.cwd() and os.getcwd() must NOT count."""\n'
        "import os\n"
        "from pathlib import Path\n"
        "def where():\n"
        "    return os.getcwd()\n"
        "def where2():\n"
        "    return Path.cwd() / 'ego_fabric'\n",
        encoding="utf-8",
    )
    assert _cwd_calls(str(bad)) == [5, 7], (
        "F4's detector missed a constructed cwd use (or counted the docstring): %s"
        % _cwd_calls(str(bad)))

    clean = tmp_path / "good_organ.py"
    clean.write_text(
        '"""os.getcwd() in prose only -- and a comment: Path.cwd()."""\n'
        "from data_root import game_data_root\n"
        "def where(game_id):\n"
        "    return game_data_root(game_id)  # os.getcwd() in a comment\n",
        encoding="utf-8",
    )
    assert _cwd_calls(str(clean)) == []


def test_f4b_the_loop_no_longer_names_a_relative_fabric_root():
    """The five sites named in the plan, asserted GONE by structure.

    F4 catches ``os.getcwd()``. A bare relative literal is the same defect without
    the call, and it is what the loop actually had -- so it gets its own law.
    """
    from cognitive_loop import EGO_FABRIC_DIRNAME

    for rel in ("cognitive_loop.py", "cognitive_game_player.py"):
        path = os.path.join(REPO, rel)
        with open(path, encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read())
        bad = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = (f.id if isinstance(f, ast.Name)
                    else f.attr if isinstance(f, ast.Attribute) else "")
            if name != "KnowledgeFabric":
                continue
            first = node.args[0] if node.args else None
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                bad.append((node.lineno, first.value))
        assert not bad, (
            "%s builds a KnowledgeFabric on a STRING LITERAL root %r. A literal root "
            "is relative to wherever the process is standing, which every game in "
            "the process shares. Pass the threaded per-game root." % (rel, bad))

    assert EGO_FABRIC_DIRNAME == "ego_fabric", (
        "the fabric directory name moved; existing boxes are laid out under the old "
        "one and would read as empty")


# ─────────────────────────────────────────────────────────────────────────────
# KNOWN-NEGATIVE · the escape hatch still opens
# ─────────────────────────────────────────────────────────────────────────────

def test_known_negative_explicit_path_is_honoured_unchanged(tmp_path, monkeypatch):
    """An explicit caller-supplied path comes back VERBATIM, root or no root.

    R4: a known-positive proves the instrument can fire and says nothing about
    over-firing. This is the known-negative for the whole build -- a resolver that
    refused everything would satisfy F2 and make the suite untestable.
    """
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    monkeypatch.delenv(ENV_VAR, raising=False)
    explicit = tmp_path / "somewhere" / "else.db"

    assert resolve_db_path(str(explicit)) == str(explicit)
    assert resolve_db_path(str(explicit), root=tmp_path / "unrelated") == str(explicit)
    assert not explicit.exists(), "resolution must create nothing"

    # And an explicit ROOT is honoured without consulting the rule at all: this
    # call would raise if the default branch were being taken.
    assert resolve_db_path(root=tmp_path).startswith(str(tmp_path))


def test_known_negative_a_loop_without_a_root_refuses_rather_than_guessing():
    """The loop's helper raises instead of falling back to the cwd.

    Asserted directly rather than through an episode: the four call sites are
    inside the loop's containment try/except, so a fallback there would present as
    a working fabric in the wrong directory -- silent, which is the failure mode.
    """
    from cognitive_loop import CognitiveLoop, _ego_fabric_root

    bare = CognitiveLoop()
    with pytest.raises(DataRootUnresolved) as exc:
        _ego_fabric_root(bare)
    assert "data_root" in str(exc.value)

    told = CognitiveLoop(data_root=os.path.join(os.sep, "tmp", "x"))
    assert _ego_fabric_root(told).endswith("ego_fabric")
