"""THE CORPSE GUARD GATE (record/prereg/PREREG_CORPSE_GUARD.md; FRONTIER_AUDIT.md F-1).

⭐ WHY. MEASURED (ar25, 13 of 13, zero ambiguity): every salient-prefix replay
ended in GAME_OVER on the FIRST cognitive action after playback, and [SALIENT]
divergence fired ZERO times. The detector was not broken — the replay was
FAITHFUL, and what it faithfully reproduced was the death: _bank_salient_prefix
banks "up to the LAST effectful action", and DYING CHANGES THE FRAME, so the
death step IS the terminal banked step and the fidelity check matches the
corpse's own post-hash.

THE BUILD (three parts, one causal story: STOP REPLAYING CORPSES):
  A. NEVER BANK A TERMINAL STEP — a step whose observation was GAME_OVER is
     truncated away before banking; if nothing salient remains, banking is
     REFUSED. Narrated ([SALIENT] truncated / refused).
  B. OUTCOME, NOT FIDELITY — divergence detection answers "does this still
     APPLY"; the question is "does this still WIN". Every replay writes its
     outcome (reached_level / died / aborted) plus its consumption ordinal
     (last_used_seq) onto the prefix row — which IS this artifact's CONSUMPTION
     RECORD (the scoped rule: any artifact subject to selection carries its
     consumption record, or the selection runs on a constant). Selection
     REFUSES a prefix whose last recorded outcome was DEATH and takes the next
     alternative.
  C. ARCHIVE LAW — banked corpses are NEVER deleted. They stay on disk,
     unselected.

THE OFF-ARM (CLAIM.md's binding ablation clause, shipped as a PASSING test):
CORPSE_GUARD=0 in the environment (or CognitiveGamePlayer.CORPSE_GUARD = False)
reproduces the pre-guard behaviour BYTE-IDENTICALLY for BOTH banking (the death
step is banked, same prefix_json bytes) and selection (the dead prefix is
chosen, the original ORDER BY uses DESC query verbatim).

NOT IN SCOPE (a separate item, deliberately absent): pure round-robin rotation
over the uses-DESC lock-in. The death refusal breaks the lock-in only as a SIDE
EFFECT (a locked corpse is refused, so the next alternative is reached).

Run pre-build: FAILED — 16 failed, 2 passed (no terminal truncation, no outcome
column, no consumption record, no CORPSE_GUARD toggle; the two greens are the
source-scans that already held: no DELETE path, and the original argmax query
still present).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

import numpy as np
import pytest
from arcengine import GameState

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
    def __init__(self, frame, state=GameState.NOT_FINISHED, levels=0):
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


def _player(tmp_path, name="box.db"):
    from cognitive_game_player import CognitiveGamePlayer

    class _GP:
        pass
    gp = _GP()
    gp.db = _DB(str(tmp_path / name))
    p = CognitiveGamePlayer(gp, verbose=False)
    for attr in ("_bank_salient_prefix", "_load_salient_prefix",
                 "_replay_salient_prefix", "_corpse_guard_enabled",
                 "CORPSE_GUARD"):
        if not hasattr(p, attr):
            pytest.fail("CognitiveGamePlayer.%s missing — the corpse guard "
                        "has not landed" % attr)
    return p


def _steps(changes, tail_noops=0):
    """A step ledger with `changes` effectful steps then trailing no-ops."""
    out = []
    for i in range(changes):
        out.append({"action": 6, "data": {"x": i, "y": i},
                    "post_hash": "h%d" % i, "changed": True})
    for _ in range(tail_noops):
        out.append({"action": 1, "data": None,
                    "post_hash": "h%d" % (changes - 1), "changed": False})
    return out


def _steps_ending_in_death(changes, tail_noops=0):
    """The MEASURED shape: the final effectful step is the death — it changed
    the frame (dying redraws the board), so it is the terminal banked step."""
    out = _steps(changes, tail_noops=tail_noops)
    out[-1]["terminal"] = True
    return out


def _rows(p, sql="SELECT * FROM salient_prefixes ORDER BY rowid"):
    return p._gp.db.execute_query(sql, ())


# ─────────────────────────────────────────────────────────────────────────────
# FALSIFIER 1 — an episode whose last effectful step is a GAME_OVER banks
# NOTHING (or a truncated prefix), never the death step
# ─────────────────────────────────────────────────────────────────────────────

class TestNeverBankATerminalStep:

    def test_the_death_step_is_truncated_away(self, tmp_path, monkeypatch,
                                              capsys):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        assert p._bank_salient_prefix("g1", 0, _steps_ending_in_death(4)) is True
        rows = _rows(p)
        assert len(rows) == 1
        prefix = json.loads(rows[0]["prefix_json"])
        assert len(prefix) == 3, (
            "the banked prefix stops BEFORE the terminal step (4 effectful "
            "steps, the last one fatal -> 3 banked)")
        assert rows[0]["outcome_hash"] == "h2", (
            "the outcome hash is the last SURVIVED state, not the corpse's")
        assert not any(s.get("terminal") for s in prefix)
        out = capsys.readouterr().out
        assert "[SALIENT]" in out and "truncat" in out.lower(), (
            "the truncation is NARRATED, not silent")

    def test_nothing_salient_left_after_truncation_refuses_to_bank(
            self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        p._ensure_salient_table()
        # 3 effectful steps, the last fatal -> 2 survive, below K=3
        assert p._bank_salient_prefix("g1", 0, _steps_ending_in_death(3)) is False
        assert _rows(p) == []
        out = capsys.readouterr().out
        assert "[SALIENT]" in out and "refus" in out.lower(), (
            "the refusal is NARRATED, not silent")

    def test_a_lone_terminal_step_banks_nothing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        p._ensure_salient_table()
        assert p._bank_salient_prefix("g1", 0, _steps_ending_in_death(1)) is False
        assert _rows(p) == []

    def test_a_clean_episode_is_unaffected(self, tmp_path, monkeypatch):
        """The guard fires ONLY on terminal steps: a non-fatal episode banks
        exactly what it banked before (no-op guarantee on the healthy path)."""
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        assert p._bank_salient_prefix("g1", 0, _steps(3, tail_noops=2)) is True
        rows = _rows(p)
        assert len(json.loads(rows[0]["prefix_json"])) == 3
        assert rows[0]["outcome_hash"] == "h2"

    def test_the_live_step_ledger_marks_the_terminal_step(self):
        """The wire: the episode loop stamps `terminal` on the step whose
        observation was GAME_OVER — without it the guard has nothing to read."""
        src = open(PLAYER, encoding="utf-8", errors="replace").read()
        i = src.find("_sal_steps.append(")
        assert i != -1
        window = src[i:i + 400]
        assert "'terminal'" in window or '"terminal"' in window, (
            "the salient step ledger must record terminality at the step that "
            "produced it — the bank cannot reconstruct it afterwards")


# ─────────────────────────────────────────────────────────────────────────────
# FALSIFIER 2 — a prefix with a recorded death outcome is NOT selected; the
# next alternative is.  FALSIFIER 3 — reached_level is recorded and stays
# selectable.  (THE CONSUMPTION RECORD, scoped rule.)
# ─────────────────────────────────────────────────────────────────────────────

def _frame(k):
    return np.full((4, 4), k, dtype=np.uint8)


def _hash(k):
    from cognitive_game_player import CognitiveGamePlayer
    return CognitiveGamePlayer._compute_frame_hash(_Obs(_frame(k)))


def _bank_run(p, first, n=3, level=0):
    """Bank a prefix whose expected frames are `first`..`first+n-1`."""
    steps = [{"action": 6, "data": {"x": i, "y": i},
              "post_hash": _hash(first + i), "changed": True}
             for i in range(n)]
    assert p._bank_salient_prefix("g1", level, steps) is True
    return _hash(first + n - 1)


class TestOutcomeNotFidelity:

    def test_a_replay_that_dies_records_died(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        oh = _bank_run(p, 1)
        sal = p._load_salient_prefix("g1", 0)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)),
                    _Obs(_frame(3), state=GameState.GAME_OVER)])
        p._replay_salient_prefix(env, "g1", 0, sal, None)
        row = [r for r in _rows(p) if r["outcome_hash"] == oh][0]
        assert row["outcome"] == "died", (
            "a replay that ends in GAME_OVER records DIED — outcome, not "
            "fidelity: this replay was perfectly faithful")

    def test_a_dead_prefix_is_not_selected_and_the_next_alternative_is(
            self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        corpse = _bank_run(p, 1)
        alt = _bank_run(p, 11)
        # the corpse wins the uses-DESC argmax AND is a recorded corpse
        p._gp.db.execute_query(
            "UPDATE salient_prefixes SET uses = 9, outcome = 'died' "
            "WHERE outcome_hash = ?", (corpse,))
        capsys.readouterr()  # drop the banking narration
        sal = p._load_salient_prefix("g1", 0)
        assert sal is not None, "the guard REFUSES corpses, it does not refuse "\
                                "replay altogether while alternatives exist"
        assert sal["outcome_hash"] == alt, (
            "the recorded corpse is refused and the NEXT alternative is "
            "selected (uses-DESC lock-in broken as a side effect)")
        out = capsys.readouterr().out
        assert "[SALIENT]" in out and "refus" in out.lower(), (
            "the refusal at SELECTION is narrated too")

    def test_every_alternative_dead_selects_nothing(self, tmp_path,
                                                    monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1)
        _bank_run(p, 11)
        p._gp.db.execute_query(
            "UPDATE salient_prefixes SET outcome = 'died'", ())
        assert p._load_salient_prefix("g1", 0) is None, (
            "with every banked alternative a recorded corpse, replay is "
            "refused entirely — the budget goes to the frontier instead")

    def test_a_replay_that_reaches_a_level_records_it_and_stays_selectable(
            self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        oh = _bank_run(p, 1)
        sal = p._load_salient_prefix("g1", 0)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)),
                    _Obs(_frame(3), levels=1)])
        p._replay_salient_prefix(env, "g1", 0, sal, None)
        row = _rows(p)[0]
        assert row["outcome"] == "reached_level"
        assert row["outcome_hash"] == oh
        assert p._load_salient_prefix("g1", 0) is not None, (
            "a winning prefix stays selectable")

    def test_an_incomplete_replay_records_aborted(self, tmp_path, monkeypatch):
        """The catch-all: a divergence/API break that neither died nor levelled
        is ABORTED — and aborted stays SELECTABLE (only death refuses)."""
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1, n=4)
        sal = p._load_salient_prefix("g1", 0)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)), _Obs(_frame(99))])
        p._replay_salient_prefix(env, "g1", 0, sal, None)
        rows = _rows(p)
        assert rows[0]["outcome"] == "aborted"
        assert p._load_salient_prefix("g1", 0) is not None

    def test_the_consumption_record_is_written_on_the_artifact(
            self, tmp_path, monkeypatch):
        """THE SCOPED RULE: an artifact subject to selection carries its
        consumption record, or the selection runs on a constant."""
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1)
        sal = p._load_salient_prefix("g1", 0)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)), _Obs(_frame(3))])
        p._replay_salient_prefix(env, "g1", 0, sal, None)
        row = _rows(p)[0]
        assert row["uses"] == 1
        assert row["last_used_seq"] == 1, (
            "the consumption ordinal is recorded ON the artifact")
        assert row["outcome"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# ARCHIVE LAW — corpses are unselected, never deleted
# ─────────────────────────────────────────────────────────────────────────────

class TestArchiveLaw:

    def test_a_refused_corpse_stays_on_disk(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        corpse = _bank_run(p, 1)
        _bank_run(p, 11)
        p._gp.db.execute_query(
            "UPDATE salient_prefixes SET uses = 9, outcome = 'died' "
            "WHERE outcome_hash = ?", (corpse,))
        for _ in range(3):
            p._load_salient_prefix("g1", 0)
        rows = _rows(p)
        assert len(rows) == 2, "evidence is only ever ADDED (archive law)"
        assert any(r["outcome_hash"] == corpse and r["outcome"] == "died"
                   for r in rows), "the corpse keeps its receipts"

    def test_no_salient_path_deletes_a_prefix(self):
        src = open(PLAYER, encoding="utf-8", errors="replace").read()
        i = src.find("_ensure_salient_table")
        assert i != -1
        region = src[i:]
        assert "DELETE FROM salient_prefixes" not in region
        assert "DROP TABLE salient_prefixes" not in region


# ─────────────────────────────────────────────────────────────────────────────
# FALSIFIER 4 — THE OFF-ARM (passing at ship): CORPSE_GUARD=0 reproduces the
# pre-guard behaviour byte-identically, for banking AND selection
# ─────────────────────────────────────────────────────────────────────────────

class TestTheOffArm:

    def test_off_arm_banks_the_death_step_byte_identically(self, tmp_path,
                                                           monkeypatch):
        monkeypatch.setenv("CORPSE_GUARD", "0")
        p = _player(tmp_path)
        steps = _steps_ending_in_death(4)
        assert p._bank_salient_prefix("g1", 0, steps) is True
        row = _rows(p)[0]
        pre_guard = json.dumps(
            [{k: v for k, v in s.items() if k != "terminal"} for s in steps])
        assert row["prefix_json"] == pre_guard, (
            "the off-arm must reproduce the PRE-GUARD bytes exactly — the "
            "corpse and all")
        assert row["outcome_hash"] == "h3"
        assert len(json.loads(row["prefix_json"])) == 4

    def test_off_arm_selects_the_dead_prefix(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CORPSE_GUARD", "0")
        p = _player(tmp_path)
        corpse = _bank_run(p, 1)
        _bank_run(p, 11)
        p._gp.db.execute_query(
            "UPDATE salient_prefixes SET uses = 9, outcome = 'died' "
            "WHERE outcome_hash = ?", (corpse,))
        sal = p._load_salient_prefix("g1", 0)
        assert sal["outcome_hash"] == corpse, (
            "off-arm selection is the original uses-DESC argmax, outcome "
            "column ignored")

    def test_off_arm_replay_writes_no_outcome(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CORPSE_GUARD", "0")
        p = _player(tmp_path)
        _bank_run(p, 1)
        sal = p._load_salient_prefix("g1", 0)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)),
                    _Obs(_frame(3), state=GameState.GAME_OVER)])
        p._replay_salient_prefix(env, "g1", 0, sal, None)
        row = _rows(p)[0]
        assert row["uses"] == 1, "the original use-count still increments"
        assert row["outcome"] is None and row["last_used_seq"] is None, (
            "the off-arm records nothing new — the schema columns exist "
            "(migration is not behaviour) and stay NULL")

    def test_the_environment_variable_outranks_the_module_flag(self, tmp_path,
                                                              monkeypatch):
        from cognitive_game_player import CognitiveGamePlayer
        assert CognitiveGamePlayer.CORPSE_GUARD is True, (
            "the guard ships ON; the off-arm is the ablation, not the default")
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        assert CognitiveGamePlayer._corpse_guard_enabled() is True
        for word in ("0", "false", "no", "off", ""):
            monkeypatch.setenv("CORPSE_GUARD", word)
            assert CognitiveGamePlayer._corpse_guard_enabled() is False, word
        monkeypatch.setenv("CORPSE_GUARD", "1")
        monkeypatch.setattr(CognitiveGamePlayer, "CORPSE_GUARD", False)
        assert CognitiveGamePlayer._corpse_guard_enabled() is True, (
            "the environment variable outranks the module flag")

    def test_the_off_arm_selection_query_is_the_original_verbatim(self):
        """Byte-identity of SELECTION is a property of the SQL, not of one
        fixture: the off branch runs the pre-guard query unchanged."""
        src = open(PLAYER, encoding="utf-8", errors="replace").read()
        i = src.find("def _load_salient_prefix")
        assert i != -1
        body = src[i:src.find("def _replay_salient_prefix")]
        assert "ORDER BY uses DESC, created_at ASC LIMIT 1" in body, (
            "the original argmax query must survive verbatim as the off-arm")
