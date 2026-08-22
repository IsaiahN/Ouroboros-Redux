"""data_root.py -- THE ONE RESOLVER FOR WHERE AGENT DATA LIVES.

THE DEFECT THIS CLOSES (record/prereg/PLAN_SWARM_SHAPE.md section 3, items 1-2).
Agent data paths resolved against the CURRENT WORKING DIRECTORY. That was correct
only by the accident that each retired fleet worker was spawned with ``cwd=<its own
box>``: ``KnowledgeFabric("ego_fabric", ...)`` is a RELATIVE root, and the database
default was resolved against ``Path.cwd()``. Put two games in ONE process -- which is
what the ARC swarm harness does, and what the Kaggle notebook must do -- and they
share one cwd, so both fabrics and both databases FUSE. Nothing raises. Nothing looks
wrong. One game's atoms simply appear in another game's library, which is precisely
the contamination the firewall exists to prevent, arriving by a path nobody watches.

THE RULE (ruled by the GM; this module is its only implementation)::

    OURO_DATA_ROOT              env var, explicit           -- wins if set
    else /kaggle/working/ouro   if /kaggle/working IS A DIRECTORY
    else <repo>/.runs           if the repo marker is present
    else RAISE, naming all three branches and what it looked for

* KAGGLE IS DETECTED BY DIRECTORY EXISTENCE, not by an env var Kaggle might rename.
  The deliverable ships as a notebook and ``/kaggle/working`` is the only writable
  place there. (WINDOWS NUANCE, NAMED RATHER THAN HIDDEN: a POSIX-absolute probe is
  DRIVE-relative on Windows, so ``/kaggle/working`` there means ``<current
  drive>\\kaggle\\working``. The branch is not expected to fire off-Kaggle; local
  development takes the repo branch. This is the one residue of process state in the
  rule and it is the GM's spelling of it, kept verbatim rather than "improved".)

* NO CWD FALLBACK, EVER. If nothing resolves, this RAISES. A fallback would reinstate
  the defect wearing a nicer name.

* THE PER-GAME ROOT is ``root / "games" / <game_id>`` (``game_data_root``), and it is
  PASSED EXPLICITLY into ``KnowledgeFabric`` and ``resolve_db_path`` from the entry
  point. Leaf modules never re-derive it: a second derivation is a second rule, and
  two rules are how the first one stops being an anchor.

THE LAWS THIS SERVES.
  FIGURE 2, "the anchor must not update" -- a path whose meaning changes with the
    caller's directory is an anchor that moves. That is exactly what a relative
    fabric root and a cwd-derived database default were.
  FIGURE 10, "install what can be violated" -- a relative default is a convention
    nothing can check; a raise is one that can. Hence the fourth branch is a RAISE
    and not a best-effort guess.
  FIGURE 6 / the firewall -- cross-game fabric fusion would put one game's atoms in
    another's library. ``tests/gate/test_data_root.py`` F1 is the instrument for that.

RESOLUTION IS PURE: nothing here creates a directory or touches a file. Only an
actual open/append may create anything. (``database_interface.resolve_db_path``
depends on that property; ``tests/gate/test_db_path_anchor.py`` F5b asserts it.)

Stdlib only, no side effects at import.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Mapping, Optional

__all__ = [
    "DataRootUnresolved",
    "ENV_VAR",
    "GAMES_DIRNAME",
    "KAGGLE_SUBDIR",
    "KAGGLE_WORKING",
    "LOCAL_SUBDIR",
    "REPO_MARKER",
    "ensure_data_root",
    "game_data_root",
    "resolve_data_root",
]

# The env var the operator sets to say it outright. Absolute paths only.
ENV_VAR = "OURO_DATA_ROOT"

# The Kaggle branch: the directory whose EXISTENCE selects it, and the subdirectory
# we own inside it. /kaggle/working is the only writable location in a notebook.
KAGGLE_WORKING = "/kaggle/working"
KAGGLE_SUBDIR = "ouro"

# The local branch: the marker that says "this is the repo", and the directory the
# GM's rule puts agent data in.
REPO_MARKER = "pyproject.toml"
LOCAL_SUBDIR = ".runs"

# The per-game level, between the root and the game id.
GAMES_DIRNAME = "games"

# A game id is a DIRECTORY NAME, so it is checked as one. Whitelist, not blacklist:
# a separator, a drive letter or a ".." in a game id would let one game's root
# escape into another's, which is the very fusion this module exists to stop.
_GAME_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class DataRootUnresolved(RuntimeError):
    """No branch of the root rule resolved -- and there is no fallback by design."""


def resolve_data_root(
    *,
    env: Optional[Mapping[str, str]] = None,
    kaggle_working: Optional[Any] = None,
    repo_dir: Optional[Any] = None,
) -> Path:
    """THE ROOT. Absolute, cwd-independent, or a raise naming all three branches.

    Args:
        env: the environment mapping to read ``OURO_DATA_ROOT`` from. Injected so a
            test can construct an environment rather than mutate the process's.
        kaggle_working: the directory whose existence selects the Kaggle branch.
            Injected so the branch can be exercised on a constructed directory.
        repo_dir: the directory searched for the repo marker. Defaults to THIS
            MODULE'S OWN directory -- the repo is where this file is, never where
            the caller is standing. Injected so the branch can be exercised on a
            constructed repo.

    Returns:
        An absolute, normalised ``Path``. Nothing is created.

    Raises:
        DataRootUnresolved: no branch resolved, or ``OURO_DATA_ROOT`` was relative.
    """
    environ: Mapping[str, str] = os.environ if env is None else env
    declared = str(environ.get(ENV_VAR) or "").strip()
    if declared:
        if not os.path.isabs(declared):
            raise DataRootUnresolved(_relative_env_message(declared))
        return _norm(Path(declared))

    kaggle = str(KAGGLE_WORKING if kaggle_working is None else kaggle_working)
    if os.path.isdir(kaggle):
        return _norm(Path(kaggle) / KAGGLE_SUBDIR)

    repo = Path(_MODULE_DIR if repo_dir is None else repo_dir)
    if (repo / REPO_MARKER).is_file():
        return _norm(repo / LOCAL_SUBDIR)

    raise DataRootUnresolved(_unresolved_message(kaggle, repo))


def game_data_root(game_id: str, *, root: Optional[Any] = None) -> Path:
    """The per-game root: ``<root>/games/<game_id>``, absolute, created by nothing.

    This is the value the entry point THREADS -- into ``KnowledgeFabric`` and into
    ``resolve_db_path(root=...)``. It is not re-derived downstream.

    Args:
        game_id: the game's id, used as a directory NAME and validated as one.
        root: the data root; resolved by ``resolve_data_root()`` when omitted.

    Raises:
        ValueError: the game id could not be a directory name (empty, or carrying a
            separator, a drive letter or a traversal).
        DataRootUnresolved: ``root`` omitted and no branch resolved.
    """
    gid = str(game_id).strip()
    if not _GAME_ID_RE.match(gid):
        raise ValueError(
            "%r is not usable as a per-game directory name. A game id must match "
            "%s -- a separator, a drive letter or a traversal in it would let one "
            "game's root escape into another's, which is the fusion the per-game "
            "root exists to prevent." % (game_id, _GAME_ID_RE.pattern))
    base = resolve_data_root() if root is None else Path(root)
    return _norm(base / GAMES_DIRNAME / gid)


def ensure_data_root(path: Any) -> Path:
    """CREATE the directory ``path`` names, and return it. THE ONLY IMPURE FUNCTION
    HERE, and it is separate from the resolver ON PURPOSE.

    ``resolve_data_root``/``game_data_root`` must create nothing: resolution runs at
    import time all over the tree, and a resolver with a side effect is how a
    database appeared at the repo root every time anything was imported (D-6/D-7).
    So the making of the directory is a SEPARATE, NAMED act, performed once by the
    entry point that has decided the game.

    It matters on Kaggle: ``/kaggle/working/ouro/games/<id>`` does not exist when
    the notebook starts, and ``sqlite3.connect`` on a path whose directory is
    missing fails with "unable to open database file" -- a degradation that would
    read as a broken database rather than as a missing directory.
    """
    out = Path(path)
    os.makedirs(str(out), exist_ok=True)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# module-bottom helpers
# ─────────────────────────────────────────────────────────────────────────────

# The repo is where THIS FILE is. Not where the process is standing -- that is the
# whole defect, and reading __file__ is the one derivation that cannot move with a
# caller. ``.resolve()`` follows symlinks so a linked checkout still finds its marker.
_MODULE_DIR = Path(__file__).resolve().parent


def _norm(path: Path) -> Path:
    """Normalised, and asserted absolute. ``abspath`` is deliberately NOT used: it
    joins a relative path to the cwd, which is the branch this module forbids."""
    out = Path(os.path.normpath(str(path)))
    if not out.is_absolute():
        raise DataRootUnresolved(
            "the data root resolved to the relative path %s. Every branch of the "
            "rule must yield an absolute location; a relative one would be read "
            "against whatever directory the process happens to be standing in, "
            "which is the defect this resolver removes." % out)
    return out


def _relative_env_message(declared: str) -> str:
    return (
        "%s=%r is RELATIVE, and a relative root is not a root: it names a different "
        "directory for every process depending on where it was started. Set %s to an "
        "ABSOLUTE path, or unset it and let the rule resolve:\n"
        "  1. %s                (env var, absolute)\n"
        "  2. %s/%s   (if %s is a directory)\n"
        "  3. <repo>/%s              (if <repo>/%s is present)"
        % (ENV_VAR, declared, ENV_VAR, ENV_VAR, KAGGLE_WORKING, KAGGLE_SUBDIR,
           KAGGLE_WORKING, LOCAL_SUBDIR, REPO_MARKER))


def _unresolved_message(kaggle: str, repo: Path) -> str:
    """The refusal NAMES ALL THREE BRANCHES AND WHAT IT LOOKED FOR.

    A raise that says only "unresolved" tells the reader nothing they could not
    already see; this one tells them which of the three to fix and where it looked.
    """
    return (
        "cannot resolve the agent data root -- and there is NO CWD FALLBACK by "
        "design, because a fallback is the defect wearing a nicer name.\n"
        "  the rule, in order:\n"
        "    1. %s                 (env var, absolute)\n"
        "    2. %s/%s   (selected by %s being a DIRECTORY)\n"
        "    3. <repo>/%s               (selected by <repo>/%s being present)\n"
        "  what it found:\n"
        "    1. %s is unset (or empty)\n"
        "    2. %s is not a directory, so %s/%s was not taken\n"
        "    3. no marker %r in %s, so %s/%s was not taken\n"
        "Set %s to an absolute path, run inside the repo, or run on Kaggle."
        % (ENV_VAR, KAGGLE_WORKING, KAGGLE_SUBDIR, KAGGLE_WORKING, LOCAL_SUBDIR,
           REPO_MARKER, ENV_VAR, kaggle, kaggle, KAGGLE_SUBDIR, REPO_MARKER, repo,
           repo, LOCAL_SUBDIR, ENV_VAR))
