"""THE TRACE WRITER MUST RECORD WHAT HAPPENED -- BUDGETS FILLED, FRAMES EXACT.

THE APPROVED FIX (Seat 3, 2026-08-20): ONE writer, telemetry-only, no
behaviour change. GamePlayer._record_action_trace (game_player.py) had three
defects: (1) budget_total/budget_spend NULL in all ~800k rows -- the live
caller (cognitive_game_player.py, the trace-write site in the cognitive loop)
never passed them although the per-level budget state (action_budget /
actions_taken) is in scope at the call; (2) frame_before/frame_after stored as
LOSSY numpy repr strings (str(array) with `...` ellipsis truncation) --
unparseable and unreconstructable; (3) every downstream trace-frame consumer
inherited the loss.

The falsifiers, as gated here (constructed player/DB fixtures; no .runs):

  F1   a recorded trace row round-trips: json.loads(frame_before)
       reconstructs the EXACT array (np.array_equal, byte-exact against the
       levelup_frames format json.dumps(arr.tolist())); budget_total /
       budget_spend are non-null and correct against a constructed budget
       state. 64x64 frames deliberately -- big enough that the OLD str()
       path would have produced `...` truncation. Multi-frame payloads store
       the loop's normalised form (THE LAST frame), list-of-arrays and
       3-D stack alike.
  F2   forward-only: rows already written in the OLD format (lossy repr,
       NULL budgets) are byte-for-byte untouched by the new writer -- no
       migration, ever.
  F3   budget arithmetic: total and spend reflect the constructed level's
       funding and consumption AT THE MOMENT OF THE WRITE -- the write
       precedes the level-up extension for the step that levels up, and the
       NEXT row carries the extended total (mirrors the caller's
       `action_budget += actions_per_level` after the trace write); the
       replay-handoff funded total (allowance x (1 + levels_replayed)) is the
       same arithmetic at episode start. And the WIRING is asserted
       structurally: the live call site passes budget_total=action_budget and
       budget_spend=actions_taken (AST, not grep).
  R4   a constructed 3-step episode produces exactly 3 rows with the
       expected budgets and byte-exact frame JSON per step.
"""
from __future__ import annotations

import ast
import json
import os
import sqlite3
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from game_player import GamePlayer  # noqa: E402

# ── constructed fixtures (no .runs, no live DB) ───────────────────────────────

class _DB:
    """The action_traces table with the live schema's inserted columns,
    behind DatabaseInterface's execute_query contract (dict rows,
    auto-commit on writes). One in-memory connection per fixture."""

    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            "CREATE TABLE action_traces ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " session_id TEXT, game_id TEXT, action_number INTEGER,"
            " coordinates TEXT, timestamp TEXT,"
            " frame_before TEXT, frame_after TEXT, frame_changed INTEGER,"
            " score_before REAL, score_after REAL, score_change REAL,"
            " level_number INTEGER, resulted_in_game_over INTEGER,"
            " frame_hash TEXT, budget_total REAL, budget_spend REAL,"
            " created_at TEXT)")
        self._conn.commit()

    def execute_query(self, query, params=()):
        cur = self._conn.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        if query.strip().upper().startswith(
                ("INSERT", "UPDATE", "DELETE", "REPLACE")):
            self._conn.commit()
        return rows


class _Obs:
    def __init__(self, frame):
        self.frame = frame


def _player(db):
    gp = GamePlayer.__new__(GamePlayer)
    gp.db = db
    gp._current_session_id = "sess-gate"
    gp.verbose = False
    return gp


def _grid(fill, n=64):
    return np.full((n, n), fill, dtype=np.uint8)


def _rows(db):
    return db.execute_query(
        "SELECT * FROM action_traces ORDER BY id", ())


# ── F1: round-trip -- exact frames, non-null correct budgets ──────────────────

def test_f1_recorded_row_round_trips_exactly():
    db = _DB()
    gp = _player(db)
    before = _grid(3)
    before[10][20] = 7            # structure the old repr would have elided
    after = _grid(5)
    gp._record_action_trace(
        game_id="gx-1", action_num=6,
        obs_before=_Obs(before), obs_after=_Obs(after),
        score_before=0.0, score_after=0.25,
        level_before=0, level_after=1, is_game_over=False,
        coordinates={"x": 20, "y": 10},
        budget_total=150, budget_spend=7,
    )
    (row,) = _rows(db)
    # the EXACT array back -- the defect was `...` ellipsis truncation
    assert np.array_equal(np.array(json.loads(row["frame_before"])), before), (
        "F1 FALSIFIED: json.loads(frame_before) does not reconstruct the "
        "exact array")
    assert np.array_equal(np.array(json.loads(row["frame_after"])), after)
    # byte-exact against the levelup_frames format: json.dumps(tolist())
    assert row["frame_before"] == json.dumps(before.tolist())
    assert row["frame_after"] == json.dumps(after.tolist())
    assert "..." not in row["frame_before"], (
        "F1 FALSIFIED: the lossy numpy repr survived the fix")
    # budgets: non-null, correct against the constructed state
    assert row["budget_total"] == 150.0
    assert row["budget_spend"] == 7.0


def test_f1_multi_frame_payload_stores_the_loops_normalised_form():
    """A stack is ordered oldest -> newest; the loop's normaliser keeps THE
    LAST frame, so the stored JSON is the last frame -- list of ndarrays and
    3-D stack alike."""
    db = _DB()
    gp = _player(db)
    stack_list = [_grid(1), _grid(2), _grid(3)]
    stack_arr = np.stack([_grid(4), _grid(5), _grid(6)])
    gp._record_action_trace(
        game_id="gx-1", action_num=1,
        obs_before=_Obs(stack_list), obs_after=_Obs(stack_arr),
        score_before=0.0, score_after=0.0,
        level_before=0, level_after=0, is_game_over=False,
        budget_total=150, budget_spend=1,
    )
    (row,) = _rows(db)
    assert row["frame_before"] == json.dumps(_grid(3).tolist()), (
        "F1 FALSIFIED: a 3-frame list did not normalise to the LAST frame")
    assert row["frame_after"] == json.dumps(_grid(6).tolist()), (
        "F1 FALSIFIED: a 3-D stack did not normalise to the LAST frame")
    # single-frame wrap keeps its exact previous meaning: the one frame
    db2 = _DB()
    gp2 = _player(db2)
    gp2._record_action_trace(
        game_id="gx-1", action_num=1,
        obs_before=_Obs([_grid(9)]), obs_after=_Obs(None),
        score_before=0.0, score_after=0.0,
        level_before=0, level_after=0, is_game_over=False)
    (row2,) = _rows(db2)
    assert row2["frame_before"] == json.dumps(_grid(9).tolist())
    # absent frame is NULL, never the string "None"
    assert row2["frame_after"] is None


# ── F2: forward-only -- old rows stay exactly as they are ─────────────────────

_OLD_REPR = ("[[0 0 0 ... 0 0 0]\n [0 0 0 ... 0 0 0]\n ...\n"
             " [0 0 0 ... 0 0 0]]")


def test_f2_old_format_rows_are_untouched():
    db = _DB()
    # rows written by the OLD writer: lossy repr frames, NULL budgets
    for i in range(3):
        db.execute_query(
            "INSERT INTO action_traces ("
            " session_id, game_id, action_number, timestamp,"
            " frame_before, frame_after, frame_changed,"
            " score_before, score_after, score_change,"
            " level_number, resulted_in_game_over, frame_hash, created_at"
            ") VALUES (?, ?, ?, 'old', ?, ?, 1, 0, 0, 0, 1, 0, 'h', 'old')",
            ("old-sess", "gx-1", i + 1, _OLD_REPR, _OLD_REPR))
    snapshot = _rows(db)
    assert len(snapshot) == 3 and all(
        r["budget_total"] is None and "..." in r["frame_before"]
        for r in snapshot)
    # the new writer appends; nothing in this build rewrites history
    gp = _player(db)
    gp._record_action_trace(
        game_id="gx-1", action_num=4,
        obs_before=_Obs(_grid(1)), obs_after=_Obs(_grid(2)),
        score_before=0.0, score_after=0.0,
        level_before=0, level_after=0, is_game_over=False,
        budget_total=150, budget_spend=1)
    rows = _rows(db)
    assert len(rows) == 4
    assert rows[:3] == snapshot, (
        "F2 FALSIFIED: an old-format row was modified -- the fix is "
        "forward-only, migration is forbidden")


# ── F3: budget arithmetic + the wiring, structurally ──────────────────────────

def _mirror_episode(db, gp, steps, actions_per_level=150,
                    start_budget=None, start_taken=0):
    """The caller's exact arithmetic (cognitive_game_player.play_game):
    actions_taken increments BEFORE the write; the write happens; THEN a
    level-up extends action_budget by actions_per_level. `steps` is a list of
    (frame_fill_before, frame_fill_after, level_up)."""
    action_budget = (start_budget if start_budget is not None
                     else actions_per_level)
    actions_taken = start_taken
    level = 0
    for fill_b, fill_a, level_up in steps:
        actions_taken += 1
        new_level = level + (1 if level_up else 0)
        gp._record_action_trace(
            game_id="gx-1", action_num=1,
            obs_before=_Obs(_grid(fill_b, n=4)), obs_after=_Obs(_grid(fill_a, n=4)),
            score_before=0.0, score_after=0.0,
            level_before=level, level_after=new_level, is_game_over=False,
            budget_total=action_budget, budget_spend=actions_taken)
        if level_up:
            action_budget += actions_per_level
        level = new_level
    return action_budget, actions_taken


def test_f3_budget_totals_and_spend_at_the_moment_of_the_write():
    db = _DB()
    gp = _player(db)
    # step 2 levels up: its OWN row carries the pre-extension total (the
    # write precedes the extension); step 3 carries the extended total
    _mirror_episode(db, gp, [(0, 1, False), (1, 2, True), (2, 3, False)])
    rows = _rows(db)
    assert [(r["budget_total"], r["budget_spend"]) for r in rows] == [
        (150.0, 1.0), (150.0, 2.0), (300.0, 3.0)], (
        "F3 FALSIFIED: budgets do not reflect the level's funding and "
        "consumption at the moment of each write (level-up extension "
        "included)")


def test_f3_replay_handoff_funding_is_the_same_arithmetic():
    """The replay handoff funds like live levels: allowance x (1 + levels
    replayed), spend continuing from the replay's actions_taken."""
    db = _DB()
    gp = _player(db)
    _mirror_episode(db, gp, [(0, 1, False)],
                    start_budget=150 * (1 + 1), start_taken=40)
    (row,) = _rows(db)
    assert (row["budget_total"], row["budget_spend"]) == (300.0, 41.0)


def test_f3_the_live_call_site_passes_the_budget_state():
    """Structurally (AST, not grep): the ONE trace-write call in
    cognitive_game_player.py passes budget_total=action_budget and
    budget_spend=actions_taken -- the in-scope per-level budget state."""
    with open(os.path.join(REPO, "cognitive_game_player.py"),
              encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    calls = [node for node in ast.walk(tree)
             if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute)
             and node.func.attr == "_record_action_trace"]
    assert len(calls) == 1, (
        "expected exactly ONE trace-write call site in "
        "cognitive_game_player.py, found %d" % len(calls))
    kw = {k.arg: k.value for k in calls[0].keywords}
    assert isinstance(kw.get("budget_total"), ast.Name) and \
        kw["budget_total"].id == "action_budget", (
        "F3 FALSIFIED: the call site does not pass "
        "budget_total=action_budget")
    assert isinstance(kw.get("budget_spend"), ast.Name) and \
        kw["budget_spend"].id == "actions_taken", (
        "F3 FALSIFIED: the call site does not pass "
        "budget_spend=actions_taken")


# ── R4: a 3-step episode -> 3 rows, expected budgets, byte-exact frames ───────

def test_r4_three_step_episode_produces_three_exact_rows():
    db = _DB()
    gp = _player(db)
    _mirror_episode(db, gp, [(0, 1, False), (1, 2, False), (2, 3, False)])
    rows = _rows(db)
    assert len(rows) == 3, (
        "R4 FALSIFIED: 3 recorded steps produced %d rows" % len(rows))
    for i, r in enumerate(rows):
        assert r["frame_before"] == json.dumps(_grid(i, n=4).tolist())
        assert r["frame_after"] == json.dumps(_grid(i + 1, n=4).tolist())
        assert (r["budget_total"], r["budget_spend"]) == (150.0, float(i + 1))
        assert r["session_id"] == "sess-gate" and r["game_id"] == "gx-1"
