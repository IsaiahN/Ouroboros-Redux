"""B7 GATE (BUILD_PROGRAM_2 W1): the salient-prefix bank — near-miss prefixes,
PLAYBACK CHANNEL ONLY.

⭐ WHY. An episode that ends WITHOUT a level-up but whose actions produced real
frame changes carries a near-miss: the prefix that did the work evaporates.
B7 banks it DB-side (the playback channel, exactly like winning_sequences) —
NEVER the fabric: the membrane law keeps replay material out of the knowledge
streams.

THE CONTRACT (K = 3, documented in cognitive_game_player.py):
  * bank: >= K nontrivial frame changes and no level-up -> the prefix up to the
    LAST effectful action lands in box-DB table salient_prefixes (game_id,
    level, prefix_json, outcome_hash, uses, created_at), DEDUPED by
    outcome-state hash (the frame hash after the last effectful action);
  * replay: a later episode at the same game+level replays a banked prefix with
    small probability (0.2, the mastery-lite mirror) BEFORE exploring; the draw
    happens only when a prefix exists (fresh boxes: no RNG-stream shift);
  * divergence: if the frame after step i differs from the banked expectation,
    STOP replaying and bank the divergence point (the observed fork, same
    salience rule, same dedup);
  * membrane law: nothing from salient_prefixes is ever written into any
    fabric stream.

Run pre-build: failed (methods and table absent).
"""
from __future__ import annotations

import ast
import os
import sqlite3
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

PLAYER = os.path.join(REPO, "cognitive_game_player.py")


class _DB:
    """Minimal box-DB stand-in speaking execute_query(sql, params)."""

    def __init__(self, path):
        self._c = sqlite3.connect(path)
        self._c.row_factory = sqlite3.Row

    def execute_query(self, sql, params=()):
        cur = self._c.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        self._c.commit()
        return rows


class _Obs:
    def __init__(self, frame, state="NOT_FINISHED", levels=0):
        self.frame = frame
        self.state = state
        self.levels_completed = levels


class _Env:
    """Scripted environment: pops the next observation per step."""

    def __init__(self, observations):
        self._obs = list(observations)
        self.steps = []

    def step(self, action, data=None):
        self.steps.append((getattr(action, "name", action), data))
        return self._obs.pop(0) if self._obs else None


def _player(tmp_path):
    from cognitive_game_player import CognitiveGamePlayer

    class _GP:
        pass
    gp = _GP()
    gp.db = _DB(str(tmp_path / "box.db"))
    p = CognitiveGamePlayer(gp, verbose=False)
    for name in ("_bank_salient_prefix", "_load_salient_prefix",
                 "_replay_salient_prefix"):
        if not hasattr(p, name):
            pytest.fail("CognitiveGamePlayer.%s missing — B7 has not landed"
                        % name)
    return p


def _steps(changes, tail_noops=2):
    """A step ledger with `changes` effectful steps then trailing no-ops."""
    out = []
    for i in range(changes):
        out.append({"action": 6, "data": {"x": i, "y": i},
                    "post_hash": "h%d" % i, "changed": True})
    for _ in range(tail_noops):
        out.append({"action": 1, "data": None,
                    "post_hash": "h%d" % (changes - 1), "changed": False})
    return out


class TestTheBank:

    def test_a_salient_no_levelup_episode_banks_its_prefix(self, tmp_path):
        p = _player(tmp_path)
        assert p._SALIENT_K == 3, "K is preregistered and documented"
        assert p._bank_salient_prefix("g1", 0, _steps(3)) is True
        rows = p._gp.db.execute_query(
            "SELECT * FROM salient_prefixes", ())
        assert len(rows) == 1
        r = rows[0]
        assert r["game_id"] == "g1" and r["level"] == 0 and r["uses"] == 0
        import json
        prefix = json.loads(r["prefix_json"])
        assert len(prefix) == 3, "the prefix stops at the LAST effectful action"
        assert r["outcome_hash"] == "h2"

    def test_below_k_changes_nothing_banks(self, tmp_path):
        p = _player(tmp_path)
        p._ensure_salient_table()
        assert p._bank_salient_prefix("g1", 0, _steps(2)) is False
        assert p._gp.db.execute_query(
            "SELECT * FROM salient_prefixes", ()) == []

    def test_dedup_by_outcome_state_hash(self, tmp_path):
        p = _player(tmp_path)
        p._bank_salient_prefix("g1", 0, _steps(3))
        p._bank_salient_prefix("g1", 0, _steps(3, tail_noops=5))
        rows = p._gp.db.execute_query("SELECT * FROM salient_prefixes", ())
        assert len(rows) == 1, "same outcome-state hash: one banked prefix"

    def test_load_is_game_and_level_scoped(self, tmp_path):
        p = _player(tmp_path)
        p._bank_salient_prefix("g1", 0, _steps(3))
        assert p._load_salient_prefix("g1", 0) is not None
        assert p._load_salient_prefix("g1", 1) is None
        assert p._load_salient_prefix("g2", 0) is None


class TestTheReplay:

    def _frame(self, k):
        return np.full((4, 4), k, dtype=np.uint8)

    def _hash(self, k):
        from cognitive_game_player import CognitiveGamePlayer
        return CognitiveGamePlayer._compute_frame_hash(_Obs(self._frame(k)))

    def _banked(self, p, n=3):
        steps = [{"action": 6, "data": {"x": i, "y": i},
                  "post_hash": self._hash(i + 1), "changed": True}
                 for i in range(n)]
        p._bank_salient_prefix("g1", 0, steps)
        return p._load_salient_prefix("g1", 0)

    def test_a_faithful_replay_runs_the_whole_prefix(self, tmp_path):
        p = _player(tmp_path)
        sal = self._banked(p)
        env = _Env([_Obs(self._frame(1)), _Obs(self._frame(2)),
                    _Obs(self._frame(3))])
        taken, obs = p._replay_salient_prefix(env, "g1", 0, sal, None)
        assert taken == 3 and len(env.steps) == 3
        rows = p._gp.db.execute_query(
            "SELECT uses FROM salient_prefixes", ())
        assert rows[0]["uses"] == 1, "a replay marks its use"

    def test_divergence_stops_the_replay_and_banks_the_fork(self, tmp_path):
        p = _player(tmp_path)
        sal = self._banked(p, n=4)
        # step 1, 2, 3 faithful; step 4 diverges (frame 9 != expected 4)
        env = _Env([_Obs(self._frame(1)), _Obs(self._frame(2)),
                    _Obs(self._frame(3)), _Obs(self._frame(9)),
                    _Obs(self._frame(5))])
        taken, obs = p._replay_salient_prefix(env, "g1", 0, sal, None)
        assert taken == 4, "the diverging step ends the replay"
        assert len(env.steps) == 4, "no steps after the divergence point"
        rows = p._gp.db.execute_query(
            "SELECT outcome_hash FROM salient_prefixes ORDER BY rowid", ())
        assert len(rows) == 2, "the divergence point is banked (same dedup)"
        assert rows[1]["outcome_hash"] == self._hash(9)


class TestTheMembraneLaw:
    """Nothing from salient_prefixes is ever written into any fabric stream."""

    def test_no_salient_function_touches_a_fabric_stream(self):
        src = open(PLAYER, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
        scopes = {"personal", "kin", "collective"}
        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            seg = ast.get_source_segment(src, node) or ""
            if "salient" not in seg.lower():
                continue
            for call in ast.walk(node):
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr in ("append", "mint")
                        and call.args
                        and isinstance(call.args[0], ast.Constant)
                        and call.args[0].value in scopes):
                    offenders.append(node.name)
        assert offenders == [], (
            "membrane law violated: salient-prefix code writes fabric "
            "streams %r" % offenders)

    def test_the_bank_is_wired_at_episode_end_and_replay_before_exploring(self):
        src = open(PLAYER, encoding="utf-8", errors="replace").read()
        assert "_bank_salient_prefix" in src and "_load_salient_prefix" in src
        assert "_SALIENT_REPLAY_P = 0.2" in src, (
            "the replay probability mirrors mastery-lite's 0.2 and is a "
            "named constant")
        i = src.find("_replay_salient_prefix(")
        j = src.find("COGNITIVE GAME LOOP")
        assert i != -1 and j != -1
        assert src.find("def play_game") < src.find(
            "_load_salient_prefix(game_id") < j, (
            "the banked prefix must be consulted BEFORE the explore loop")
