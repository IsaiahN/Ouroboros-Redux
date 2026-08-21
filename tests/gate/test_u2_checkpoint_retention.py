"""U-2 gate (record/findings/RETENTION_POLICY.md): the frontier-checkpoint
retention path may never delete by score.

D-1 was the condemned key still in production: safe_cleanup kept the top 20
checkpoints per (game_type, level_number) ranked by survival_score DESC and
hard-DELETED the rest -- latent only because the table's writer was never
wired (record/findings/F8A_READ.md: "D-1 is LATENT, not INERT"). disk rulings
2026-08: score-keyed deletion removed; ground evidence protected.

Ruled shape, asserted here three ways:
  1. BEHAVIOURAL -- a constructed table with rows is archived IN FULL to
     frontier_checkpoints_archive and then truncated; the archive is readable
     and complete (count match AND value-identical rows).
  2. STRUCTURAL  -- no score comparison anywhere in the deletion path: the
     method source contains no survival_score, no ranking window, and its
     truncate statement carries no predicate (AST scan of the SQL literals).
  3. APPEND-ONLY -- a second sweep appends to the archive, never overwrites.
A regression that reintroduces score-keyed deletion turns 1 AND 2 red.
"""
from __future__ import annotations

import ast
import inspect
import os
import sqlite3
import sys
import textwrap

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from safe_cleanup import SafeDatabaseCleaner  # noqa: E402

# Original columns, in schema order (complete_database_schema.sql:2061-2075).
COLS = ("game_type", "level_number", "terminal_frame_hash", "action_sequence",
        "actions_count", "unique_frames_seen", "survival_score",
        "terminal_reason", "times_used", "times_extended")


def _rows(n, game="g1", level=1, tag=""):
    """n distinct rows; survival_score spread INCLUDES 0 -- the rows the
    pre-ruling top-20 ranking would have condemned."""
    return [(game, level, f"{tag}hash_{game}_{level}_{i}", f"[{i}]", i + 1,
             i, float(i % 7), "timeout", 0, i % 3) for i in range(n)]


def _db(tmp_path, rows):
    con = sqlite3.connect(os.path.join(str(tmp_path), "t.db"))
    con.execute("""CREATE TABLE frontier_checkpoints (
        game_type TEXT NOT NULL, level_number INTEGER NOT NULL,
        terminal_frame_hash TEXT NOT NULL, action_sequence TEXT NOT NULL,
        actions_count INTEGER NOT NULL, unique_frames_seen INTEGER DEFAULT 0,
        survival_score REAL DEFAULT 0, terminal_reason TEXT,
        times_used INTEGER DEFAULT 0, times_extended INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP,
        PRIMARY KEY (game_type, level_number, terminal_frame_hash))""")
    con.executemany(
        f"INSERT INTO frontier_checkpoints ({', '.join(COLS)}) "  # noqa: S608 - fixed identifiers
        f"VALUES ({', '.join('?' * len(COLS))})", rows)
    con.commit()
    return con


def _run(con, dry_run=False):
    obj = SafeDatabaseCleaner.__new__(SafeDatabaseCleaner)
    return obj._clean_frontier_checkpoints(con.cursor(), con, dry_run, False)


def _count(con, table):
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608 - fixed identifiers


class TestU2CheckpointRetention:

    def test_archives_all_rows_then_truncates(self, tmp_path):
        # 30 rows in one partition (the old code would have score-deleted 10
        # of these, rn > 20) plus 5 in a second partition.
        rows = _rows(30, "g1", 1) + _rows(5, "g2", 3)
        con = _db(tmp_path, rows)
        out = _run(con)

        assert _count(con, "frontier_checkpoints") == 0, \
            "live table not truncated -- rows were retained (or ranked)"
        assert _count(con, "frontier_checkpoints_archive") == 35, \
            "archive incomplete -- a row was lost on the way"
        # Complete AND readable: every original row survives value-identical.
        got = sorted(con.execute(
            f"SELECT {', '.join(COLS)} FROM frontier_checkpoints_archive"))  # noqa: S608 - fixed identifiers
        assert got == sorted(rows), "archive rows differ from originals"
        # Every archived row carries the archive stamp.
        assert con.execute(
            "SELECT COUNT(*) FROM frontier_checkpoints_archive "
            "WHERE archived_at IS NULL OR archived_at = ''").fetchone()[0] == 0
        assert out["found"] == 35 and out["archived"] == 35
        assert out["deleted"] == 0, \
            "archive-then-truncate must report deleted=0: nothing is deleted"

    def test_zero_score_rows_survive_in_archive(self, tmp_path):
        """The exact victims of the condemned key (survival_score = 0) are in
        the archive after the sweep -- ground evidence protected."""
        con = _db(tmp_path, _rows(28, "g1", 1))
        zero_before = con.execute(
            "SELECT COUNT(*) FROM frontier_checkpoints "
            "WHERE survival_score = 0").fetchone()[0]
        assert zero_before > 0
        _run(con)
        zero_archived = con.execute(
            "SELECT COUNT(*) FROM frontier_checkpoints_archive "
            "WHERE survival_score = 0").fetchone()[0]
        assert zero_archived == zero_before

    def test_dry_run_touches_nothing(self, tmp_path):
        con = _db(tmp_path, _rows(25))
        out = _run(con, dry_run=True)
        assert out["found"] == 25 and out["archived"] == 0
        assert out["deleted"] == 0
        assert _count(con, "frontier_checkpoints") == 25
        assert con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='frontier_checkpoints_archive'").fetchone() is None

    def test_archive_is_append_only_across_sweeps(self, tmp_path):
        con = _db(tmp_path, _rows(4, "g1", 1))
        _run(con)
        con.executemany(
            f"INSERT INTO frontier_checkpoints ({', '.join(COLS)}) "  # noqa: S608 - fixed identifiers
            f"VALUES ({', '.join('?' * len(COLS))})",
            _rows(3, "g1", 2, tag="w2_"))
        con.commit()
        out = _run(con)
        assert out["archived"] == 3
        assert _count(con, "frontier_checkpoints_archive") == 7, \
            "second sweep overwrote the archive -- it must append"
        assert _count(con, "frontier_checkpoints") == 0

    def test_structural_no_score_predicate_in_deletion_path(self):
        """AST/source scan: the deletion path contains no score comparison,
        no ranking window, and its DELETE carries no predicate at all."""
        src = textwrap.dedent(inspect.getsource(
            SafeDatabaseCleaner._clean_frontier_checkpoints))
        assert "survival_score" not in src, \
            "the condemned key is back in the deletion path (D-1)"
        assert "ROW_NUMBER" not in src.upper(), \
            "a ranking window is back in the deletion path"

        tree = ast.parse(src)
        sql_literals = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                sql_literals.append(node.value)
            elif isinstance(node, ast.JoinedStr):  # f-strings piecewise
                sql_literals.append("".join(
                    v.value for v in node.values
                    if isinstance(v, ast.Constant) and isinstance(v.value, str)))

        # SQL DELETE statements only ("delete from ..."), not prose mentions
        # of the word in the docstring or in loud prints.
        deletes = [" ".join(s.lower().split()) for s in sql_literals
                   if "delete from" in " ".join(s.lower().split())]
        assert deletes, "no DELETE literal found -- structural scan is vacuous"
        for stmt in deletes:
            assert "score" not in stmt, f"score inside a DELETE: {stmt!r}"
            assert "order by" not in stmt, f"ranking inside a DELETE: {stmt!r}"
            assert "where" not in stmt, \
                f"the truncate grew a predicate -- rows are being SELECTED " \
                f"for removal again: {stmt!r}"

        # No Python-side comparison against anything score-named either.
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for sub in ast.walk(node):
                    name = (sub.id if isinstance(sub, ast.Name)
                            else sub.attr if isinstance(sub, ast.Attribute)
                            else "")
                    assert "score" not in name.lower(), \
                        "python-side score comparison in the deletion path"
