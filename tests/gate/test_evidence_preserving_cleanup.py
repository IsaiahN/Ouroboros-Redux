"""The cleaner must never eat evidence: wins, level completions, and positive
scores are kept forever regardless of score; zero-evidence episode rows keep a
recent generation window (census for stuck-game diagnosis); NULL-generation
rows are kept (conservative). Regression for the re86/tu93 census wipe
(112->8, 97->12) caused by DELETE ... WHERE final_score = 0.
"""
from __future__ import annotations

import os
import sqlite3
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _db(tmp_path):
    con = sqlite3.connect(os.path.join(str(tmp_path), "t.db"))
    con.execute("""CREATE TABLE game_results (
        game_id TEXT, session_id TEXT, start_time TIMESTAMP, status TEXT,
        final_score REAL DEFAULT 0, win_detected BOOLEAN DEFAULT 0,
        level_completions INTEGER DEFAULT 0, generation INTEGER)""")
    rows = [
        ("g", "win_score0",   0.0, 1, 0, 1),    # win recorded with zero score
        ("g", "level_score0", 0.0, 0, 2, 1),    # level completion, zero score
        ("g", "scored_old",   3.0, 0, 0, 1),    # positive score, ancient
        ("g", "zero_recent",  0.0, 0, 0, 48),   # zero-evidence, recent gen
        ("g", "zero_old",     0.0, 0, 0, 5),    # zero-evidence, old gen
        ("g", "zero_nullgen", 0.0, 0, 0, None), # zero-evidence, no generation
        ("g", "head",         0.0, 0, 0, 50),   # establishes max generation
    ]
    con.executemany(
        "INSERT INTO game_results (game_id, session_id, final_score, "
        "win_detected, level_completions, generation) VALUES (?,?,?,?,?,?)",
        rows)
    con.commit()
    return con


def _run(con, dry_run=False):
    from safe_cleanup import SafeDatabaseCleaner
    obj = SafeDatabaseCleaner.__new__(SafeDatabaseCleaner)
    obj.raw_data_generation_retention = 10
    return obj._clean_zero_score_games(con.cursor(), con, dry_run, False)


def _survivors(con):
    return {r[0] for r in con.execute("SELECT session_id FROM game_results")}


class TestEvidenceIsForever:

    def test_only_old_zero_evidence_rows_die(self, tmp_path):
        con = _db(tmp_path)
        out = _run(con)
        kept = _survivors(con)
        assert "win_score0" in kept, "a WIN row was deleted -- the scoreboard's ground truth"
        assert "level_score0" in kept, "a LEVEL row was deleted -- depth evidence destroyed"
        assert "scored_old" in kept
        assert "zero_recent" in kept, "recent census deleted -- stuck-game diagnosis blinded"
        assert "zero_nullgen" in kept, "NULL-generation row deleted -- not conservative"
        assert "zero_old" not in kept, "old zero-evidence row survived -- cleanup does nothing"
        assert out["deleted"] == 1

    def test_short_history_keeps_everything(self, tmp_path):
        con = _db(tmp_path)
        con.execute("UPDATE game_results SET generation = 3 WHERE generation IS NOT NULL")
        con.commit()
        out = _run(con)
        assert out["deleted"] == 0 and len(_survivors(con)) == 7

    def test_dry_run_deletes_nothing(self, tmp_path):
        con = _db(tmp_path)
        _run(con, dry_run=True)
        assert len(_survivors(con)) == 7
