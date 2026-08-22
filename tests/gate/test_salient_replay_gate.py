"""THE SALIENT REPLAY GATE — the mirror made an actual mirror.

RULED (GM, 2026-08-22; record/prereg/BRIEF_SALIENT_REPLAY_GATE.md): "the salient path calls
mastery like its sibling does". NOT removal — the main path proves the
mechanism works; one of its two call sites never used it.

THE DEFECT. `cognitive_game_player.py` has two replay draws. Site A (the
winning-sequence path) asks `MasteryLite.replay_probability` and feeds every
completed replay back through `record_replay_outcome`. Site B (the
salient-prefix path) drew against a hard-coded `_SALIENT_REPLAY_P = 0.2` whose
own comment called it "the mastery-lite mirror" — a convention nothing could
check (FIGURE 10), on the one crossing FIGURE 4 says must be checked (playback
going downward). MEASURED HARM (ar25, FRONTIER_AUDIT F-1): 13 of 13 salient
replays ended in GAME_OVER on the first cognitive action after playback and
divergence fired ZERO times — the replay was FAITHFUL and what it faithfully
reproduced was a death. An unfed gate cannot learn that.

WHAT IS ASSERTED HERE, and HOW (the honest limit): site B lives inside
`play_game`, a method no unit test in this tree can run. The DECISION and the
OUTCOME BIT are therefore asserted at RUNTIME on the helpers that carry them
(`_salient_replay_draw`, `_salient_replay_p`, `_salient_replay_ok`), and their
PRESENCE AT THE LIVE SITE is asserted STRUCTURALLY over the AST of `play_game`
(containment, order, count, receiver) — never by string window, never by line.
"""
from __future__ import annotations

import ast
import os
import random
import sqlite3
import sys

import numpy as np
import pytest
from arcengine import GameState

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

PLAYER = os.path.join(REPO, "cognitive_game_player.py")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures (the corpse-guard gate's constructions, so the known-negative in F5
# is run on the same shapes the guard was built against)
# ─────────────────────────────────────────────────────────────────────────────

class _DB:
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
    def __init__(self, observations):
        self._obs = list(observations)
        self.steps = []

    def step(self, action, data=None):
        self.steps.append((getattr(action, "name", action), data))
        return self._obs.pop(0) if self._obs else None


class _Mastery:
    """A recording double: what was asked, on which instance, and what was fed
    back. It is deliberately NOT a MasteryLite subclass — a name-alike would
    pass a name test, and F4 is about identity."""

    def __init__(self, p=1.0):
        self.p = p
        self.asked = []
        self.recorded = []
        self.receivers = []

    def replay_probability(self, game, has_bank):
        self.asked.append((game, has_bank))
        self.receivers.append(self)
        return self.p

    def record_replay_outcome(self, game, ok):
        self.recorded.append((game, ok))


def _player(tmp_path, name="box.db"):
    from cognitive_game_player import CognitiveGamePlayer

    class _GP:
        pass
    gp = _GP()
    gp.db = _DB(str(tmp_path / name))
    p = CognitiveGamePlayer(gp, verbose=False)
    for attr in ("_salient_replay_p", "_salient_replay_draw",
                 "_salient_replay_ok", "_SALIENT_REPLAY_P"):
        if not hasattr(p, attr):
            pytest.fail("CognitiveGamePlayer.%s missing — the salient replay "
                        "gate has not landed" % attr)
    return p


def _frame(k):
    return np.full((4, 4), k, dtype=np.uint8)


def _hash(k):
    from cognitive_game_player import CognitiveGamePlayer
    return CognitiveGamePlayer._compute_frame_hash(_Obs(_frame(k)))


def _bank_run(p, first, n=3, level=0):
    steps = [{"action": 6, "data": {"x": i, "y": i},
              "post_hash": _hash(first + i), "changed": True}
             for i in range(n)]
    assert p._bank_salient_prefix("g1", level, steps) is True
    return _hash(first + n - 1)


def _rows(p, sql="SELECT * FROM salient_prefixes ORDER BY rowid"):
    return p._gp.db.execute_query(sql, ())


# ─────────────────────────────────────────────────────────────────────────────
# The AST instrument: containment, order, count, receiver. No line numbers.
# ─────────────────────────────────────────────────────────────────────────────

def _tree():
    with open(PLAYER, encoding="utf-8", errors="replace") as fh:
        return ast.parse(fh.read())


def _scope(node, qualname):
    cur = node
    for part in qualname.split("."):
        found = None
        for child in (ast.walk(cur) if cur is node else ast.iter_child_nodes(cur)):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)) and child.name == part:
                found = child
                break
        assert found is not None, "%r does not exist in the player" % qualname
        cur = found
    return cur


def _calls(node, name):
    out = [n for n in ast.walk(node) if isinstance(n, ast.Call)
           and ((isinstance(n.func, ast.Name) and n.func.id == name)
                or (isinstance(n.func, ast.Attribute) and n.func.attr == name))]
    out.sort(key=lambda n: (n.lineno, n.col_offset))
    return out


def _on_self_mastery(call):
    """True when the callee is written `self._mastery.<attr>` — the RECEIVER,
    not just the method name."""
    f = call.func
    return (isinstance(f, ast.Attribute)
            and isinstance(f.value, ast.Attribute)
            and f.value.attr == "_mastery"
            and isinstance(f.value.value, ast.Name)
            and f.value.value.id == "self")


def _salient_branch():
    """The If in play_game whose body performs the salient replay."""
    pg = _scope(_tree(), "CognitiveGamePlayer.play_game")
    ifs = [n for n in ast.walk(pg) if isinstance(n, ast.If)
           and _calls_in_body(n, "_replay_salient_prefix")]
    assert len(ifs) == 1, (
        "expected exactly ONE branch in play_game that replays a salient "
        "prefix, found %d" % len(ifs))
    return pg, ifs[0]


def _calls_in_body(if_node, name):
    body = [n for stmt in if_node.body for n in ast.walk(stmt)]
    return [n for n in body if isinstance(n, ast.Call)
            and ((isinstance(n.func, ast.Name) and n.func.id == name)
                 or (isinstance(n.func, ast.Attribute) and n.func.attr == name))]


# ─────────────────────────────────────────────────────────────────────────────
# F1 — the gate is drawn against the EARNED rate: 0.0 never replays, 1.0
# always, over many SEEDED draws. Counting, never a single draw, never a clock.
# ─────────────────────────────────────────────────────────────────────────────

N = 2000


class TestF1TheRateIsTheDial:

    def _count(self, p, prob, seed=1234):
        p._mastery = _Mastery(prob)
        random.seed(seed)
        return sum(1 for _ in range(N) if p._salient_replay_draw("gt", True))

    def test_zero_never_replays_and_one_always_does(self, tmp_path):
        p = _player(tmp_path)
        assert self._count(p, 0.0) == 0, (
            "a mastery that has earned nothing must CLOSE the salient path — "
            "the gate is not a gate if 0.0 still replays")
        assert self._count(p, 1.0) == N, (
            "a fully earned rate must open it every time")

    def test_the_dial_is_continuous_between_them(self, tmp_path):
        p = _player(tmp_path)
        n = self._count(p, 0.5)
        assert 0 < n < N and abs(n - N // 2) < N // 10, (
            "0.5 drew %d of %d — the rate must be the dial, not a step" % (n, N))

    def test_exactly_one_random_draw_per_decision(self, tmp_path, monkeypatch):
        """The RNG-stream law the site depends on: the caller has already
        established that a prefix exists, so ONE draw happens there and only
        there."""
        p = _player(tmp_path)
        p._mastery = _Mastery(0.75)
        seen = []
        real = random.random
        monkeypatch.setattr(random, "random",
                            lambda: (seen.append(1), real())[1])
        p._salient_replay_draw("gt", True)
        assert len(seen) == 1, "the draw consumed %d values, not 1" % len(seen)
        assert p._mastery.asked == [("gt", True)], (
            "the rate must be asked once per draw, with the prefix's presence")

    def test_the_live_site_draws_through_it(self):
        """STRUCTURAL: the salient branch's own test is the draw — the site no
        longer compares a bare constant."""
        pg, br = _salient_branch()
        drawn = [n for n in ast.walk(br.test) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "_salient_replay_draw"]
        assert len(drawn) == 1, (
            "the salient branch does not decide through _salient_replay_draw "
            "(%d calls in its test)" % len(drawn))
        leaked = [n for n in ast.walk(pg)
                  if (isinstance(n, ast.Attribute) and n.attr == "_SALIENT_REPLAY_P")
                  or (isinstance(n, ast.Name) and n.id == "_SALIENT_REPLAY_P")]
        assert leaked == [], (
            "play_game still reads _SALIENT_REPLAY_P directly — the constant "
            "is the FALLBACK PRIOR now, reachable only when mastery is absent")


# ─────────────────────────────────────────────────────────────────────────────
# F2 — every completed salient replay feeds the gate exactly once, with the
# outcome the replay ACTUALLY had (success and abort both constructed).
# ─────────────────────────────────────────────────────────────────────────────

class TestF2TheGateIsFed:

    def test_the_record_is_in_the_branch_once_and_after_the_replay(self):
        pg, br = _salient_branch()
        rep = _calls_in_body(br, "_replay_salient_prefix")
        rec = _calls_in_body(br, "record_replay_outcome")
        assert len(rep) == 1 and len(rec) == 1, (
            "the salient branch holds %d replays and %d outcome records — "
            "exactly one of each" % (len(rep), len(rec)))
        assert (rec[0].lineno, rec[0].col_offset) > (rep[0].lineno,
                                                     rep[0].col_offset), (
            "the outcome is recorded BEFORE the replay runs — it cannot be the "
            "outcome the replay had")
        assert _on_self_mastery(rec[0]), (
            "the salient outcome is fed to something other than self._mastery")

    def test_it_is_keyed_the_way_site_a_keys_it(self):
        """Both records name the same key expression — a second key would be a
        second, quietly separate, ledger."""
        pg = _scope(_tree(), "CognitiveGamePlayer.play_game")
        recs = [c for c in _calls(pg, "record_replay_outcome")
                if _on_self_mastery(c)]
        assert len(recs) == 2, (
            "play_game records %d replay outcomes — site A and site B, no "
            "more, no fewer" % len(recs))
        keys = {ast.dump(c.args[0]) for c in recs}
        assert len(keys) == 1, (
            "the two sites feed DIFFERENT keys into the same ledger: %r" % keys)

    def _replay(self, p, env, level=0, n=3):
        sal = p._load_salient_prefix("g1", level)
        taken, obs = p._replay_salient_prefix(env, "g1", level, sal, None)
        return p._salient_replay_ok(obs, taken, len(sal.get("steps") or []),
                                    level)

    def test_a_faithful_surviving_replay_is_ok(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)), _Obs(_frame(3))])
        assert self._replay(p, env) is True, (
            "a replay that reproduced every banked step and lived is the "
            "success this bank is FOR (it is a near-miss prefix: levelling is "
            "not its job)")

    def test_a_replay_that_reaches_a_level_is_ok(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)), _Obs(_frame(3), levels=1)])
        assert self._replay(p, env) is True

    def test_the_measured_harm_is_a_failure(self, tmp_path, monkeypatch):
        """THE 13-of-13 CASE: perfectly faithful, and what it reproduced was a
        death. Faithful-but-fatal MUST decay the rate, or the gate learns the
        opposite of the measurement."""
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)),
                    _Obs(_frame(3), state=GameState.GAME_OVER)])
        assert self._replay(p, env) is False

    def test_a_diverged_replay_is_a_failure(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1, n=4)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)), _Obs(_frame(99))])
        assert self._replay(p, env) is False, (
            "the board moved under the prefix — that is exactly the staleness "
            "the earned rate exists to decay")

    def test_an_api_break_is_a_failure(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1)
        assert self._replay(p, _Env([])) is False, (
            "no observation at all is not a success")

    def test_a_win_is_ok(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1, n=4)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2), state=GameState.WIN)])
        assert self._replay(p, env) is True, (
            "a replay that WON stopped early by winning — not by diverging")


# ─────────────────────────────────────────────────────────────────────────────
# F3 — `self._mastery is None` is the UNDO: the static prior, no record.
# ─────────────────────────────────────────────────────────────────────────────

class TestF3TheUndoIsTheAbsence:

    def test_no_mastery_gives_the_static_prior(self, tmp_path):
        p = _player(tmp_path)
        assert not hasattr(p, "_mastery"), (
            "the player must not construct mastery eagerly — the absence is "
            "the undo")
        assert p._salient_replay_p("gt", True) == p._SALIENT_REPLAY_P == 0.2
        p._mastery = None
        assert p._salient_replay_p("gt", True) == 0.2, (
            "an explicit None must take the same arm as a missing attribute")

    def test_the_draw_sequence_is_byte_identical_to_the_old_constant(
            self, tmp_path):
        """Containment: with no mastery the site makes the SAME decisions from
        the SAME stream it made before the ruling."""
        p = _player(tmp_path)
        random.seed(99)
        new = [p._salient_replay_draw("gt", True) for _ in range(N)]
        random.seed(99)
        old = [random.random() < 0.2 for _ in range(N)]
        assert new == old, "the no-mastery arm shifted the RNG stream"

    def test_a_broken_mastery_falls_back_rather_than_closing_the_path(
            self, tmp_path):
        class _Broken:
            def replay_probability(self, game, has_bank):
                raise RuntimeError("storage")
        p = _player(tmp_path)
        p._mastery = _Broken()
        assert p._salient_replay_p("gt", True) == 0.2

    def test_the_record_is_guarded_by_the_same_absence(self):
        """STRUCTURAL: the outcome feed sits inside a test of _mastery, so the
        no-mastery arm records nothing at all."""
        pg, br = _salient_branch()
        recs = _calls_in_body(br, "record_replay_outcome")
        assert recs, ("the salient branch records no outcome at all — there is "
                      "nothing for the absence to guard")
        rec = recs[0]
        guards = [n for n in ast.walk(br) if isinstance(n, ast.If)
                  and any(m is rec for m in ast.walk(n))
                  and [r for r in ast.walk(n.test)
                       if (isinstance(r, ast.Attribute) and r.attr == "_mastery")
                       or (isinstance(r, ast.Constant) and r.value == "_mastery")]]
        assert guards, (
            "the salient outcome record is not guarded by a _mastery test — "
            "the no-mastery arm would raise instead of doing nothing")


# ─────────────────────────────────────────────────────────────────────────────
# F4 — both sites resolve their probability through the SAME function, on the
# SAME instance. Asserted by identity, not by name-alike.
# ─────────────────────────────────────────────────────────────────────────────

class TestF4OneFunctionTwoSites:

    def test_exactly_two_call_sites_both_on_self_mastery(self):
        t = _tree()
        cls = _scope(t, "CognitiveGamePlayer")
        every = _calls(cls, "replay_probability")
        assert len(every) == 2, (
            "the player calls replay_probability %d times — site A and site B, "
            "no more" % len(every))
        assert all(_on_self_mastery(c) for c in every), (
            "a replay_probability call whose receiver is NOT self._mastery is "
            "a name-alike, not the same gate")
        pg = _scope(t, "CognitiveGamePlayer.play_game")
        sb = _scope(t, "CognitiveGamePlayer._salient_replay_p")
        in_pg = [c for c in every if any(n is c for n in ast.walk(pg))]
        in_sb = [c for c in every if any(n is c for n in ast.walk(sb))]
        assert len(in_pg) == 1 and len(in_sb) == 1, (
            "the two calls are not one at site A (play_game) and one at site B "
            "(_salient_replay_p)")

    def test_site_b_is_reached_from_the_live_site(self):
        """A helper nothing calls is not a wire: play_game's salient branch
        reaches _salient_replay_p through _salient_replay_draw."""
        pg, br = _salient_branch()
        assert [n for n in ast.walk(br.test) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "_salient_replay_draw"]
        draw = _scope(_tree(), "CognitiveGamePlayer._salient_replay_draw")
        assert _calls(draw, "_salient_replay_p"), (
            "_salient_replay_draw does not consult _salient_replay_p")

    def test_the_receiver_is_the_one_instance(self, tmp_path):
        """RUNTIME IDENTITY: the object site B calls IS self._mastery — the
        same attribute site A reads, not a second instance built for it."""
        p = _player(tmp_path)
        m = _Mastery(0.42)
        p._mastery = m
        assert p._salient_replay_p("gt", True) == 0.42
        assert m.receivers and all(r is m for r in m.receivers)
        assert m.receivers[-1] is p._mastery

    def test_the_function_is_masterylite_s_own(self, tmp_path):
        """And the real instance resolves that attribute to ONE function
        object — the same one site A binds."""
        from engines.egocentric.fabric import KnowledgeFabric
        from engines.egocentric.mastery import MasteryLite
        m = MasteryLite(KnowledgeFabric(str(tmp_path / "f"), agent_id="a",
                                        kin_key="v4"))
        p = _player(tmp_path)
        p._mastery = m
        assert type(p._mastery).replay_probability is MasteryLite.replay_probability
        assert p._salient_replay_p("gt", False) == 0.2
        assert p._salient_replay_p("gt", True) == 0.8, (
            "with a prefix in hand and no history, site B gets mastery's "
            "optimistic prior — that is the earned mechanism, not the constant")


# ─────────────────────────────────────────────────────────────────────────────
# THE SHAPE CHECK (proctor's addition: three of four "name mismatch" repairs
# elsewhere were SHAPE mismatches — a renamed call returned a dataclass where
# the caller read a dict).
# ─────────────────────────────────────────────────────────────────────────────

class TestTheShapeTheCallSiteConsumes:

    def test_replay_probability_returns_a_bare_float(self, tmp_path):
        from engines.egocentric.fabric import KnowledgeFabric
        from engines.egocentric.mastery import MasteryLite
        m = MasteryLite(KnowledgeFabric(str(tmp_path / "f"), agent_id="a",
                                        kin_key="v4"))
        for has_bank in (True, False):
            v = m.replay_probability("gt", has_bank)
            assert type(v) is float, (
                "replay_probability returned %r (%s) — the call site compares "
                "it with `<`; a record would compare as a type error"
                % (v, type(v).__name__))
            assert 0.0 <= v <= 1.0
        m.record_replay_outcome("gt", True)
        assert type(m.replay_probability("gt", True)) is float

    def test_record_replay_outcome_consumes_a_bool_and_returns_nothing(
            self, tmp_path):
        from engines.egocentric.fabric import KnowledgeFabric
        from engines.egocentric.mastery import MasteryLite
        m = MasteryLite(KnowledgeFabric(str(tmp_path / "f"), agent_id="a",
                                        kin_key="v4"))
        assert m.record_replay_outcome("gt", True) is None
        assert type(m.replay_probability("gt", True)) is float

    def test_the_site_consumes_it_as_a_scalar(self, tmp_path):
        """STRUCTURAL: the returned value is compared, never indexed and never
        attribute-read — the exact defect the proctor's note names."""
        draw = _scope(_tree(), "CognitiveGamePlayer._salient_replay_draw")
        cmps = [n for n in ast.walk(draw) if isinstance(n, ast.Compare)]
        assert len(cmps) == 1 and isinstance(cmps[0].ops[0], ast.Lt)
        rhs = cmps[0].comparators[0]
        assert isinstance(rhs, ast.Call) and rhs.func.attr == "_salient_replay_p"
        sb = _scope(_tree(), "CognitiveGamePlayer._salient_replay_p")
        bad = [n for n in ast.walk(sb)
               if isinstance(n, (ast.Subscript,))
               or (isinstance(n, ast.Attribute) and n.attr in ("probability",
                                                               "value", "p"))]
        assert bad == [], (
            "site B reads a field off the probability — it is a float")

    def test_the_ok_bit_is_a_bool(self, tmp_path):
        p = _player(tmp_path)
        v = p._salient_replay_ok(_Obs(_frame(1)), 3, 3, 0)
        assert type(v) is bool, "the outcome fed to mastery must be a bool"
        assert type(p._salient_replay_ok(None, 0, 3, 0)) is bool


# ─────────────────────────────────────────────────────────────────────────────
# F5 — KNOWN-NEGATIVE: this build does not weaken the corpse guard or
# divergence detection. Both still fire on their own constructed cases.
# ─────────────────────────────────────────────────────────────────────────────

class TestF5TheGuardsStillFire:

    def test_a_fatal_replay_still_records_died_and_is_refused_next_time(
            self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        oh = _bank_run(p, 1)
        sal = p._load_salient_prefix("g1", 0)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)),
                    _Obs(_frame(3), state=GameState.GAME_OVER)])
        taken, obs = p._replay_salient_prefix(env, "g1", 0, sal, None)
        row = [r for r in _rows(p) if r["outcome_hash"] == oh][0]
        assert row["outcome"] == "died" and row["last_used_seq"] == 1
        assert p._load_salient_prefix("g1", 0) is None, (
            "the recorded corpse must still be refused at selection")
        assert p._salient_replay_ok(obs, taken, 3, 0) is False, (
            "and the same death must reach mastery as a failure")

    def test_divergence_still_stops_the_replay_and_is_narrated(
            self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("CORPSE_GUARD", raising=False)
        p = _player(tmp_path)
        _bank_run(p, 1, n=4)
        sal = p._load_salient_prefix("g1", 0)
        capsys.readouterr()
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)), _Obs(_frame(99)),
                    _Obs(_frame(4))])
        taken, obs = p._replay_salient_prefix(env, "g1", 0, sal, None)
        out = capsys.readouterr().out
        assert "diverg" in out.lower(), "divergence is no longer narrated"
        assert taken == 3, (
            "the replay must STOP at the fork, not run the remaining steps "
            "(took %d of 4)" % taken)
        assert len(env.steps) == 3
        assert p._salient_replay_ok(obs, taken, 4, 0) is False

    def test_the_off_arm_of_the_guard_is_untouched(self, tmp_path, monkeypatch):
        """The ablation clause: CORPSE_GUARD=0 still reproduces the pre-guard
        consumption record (no outcome written), and the earned rate does not
        depend on the guard's arm."""
        monkeypatch.setenv("CORPSE_GUARD", "0")
        p = _player(tmp_path)
        _bank_run(p, 1)
        sal = p._load_salient_prefix("g1", 0)
        env = _Env([_Obs(_frame(1)), _Obs(_frame(2)),
                    _Obs(_frame(3), state=GameState.GAME_OVER)])
        taken, obs = p._replay_salient_prefix(env, "g1", 0, sal, None)
        row = _rows(p)[0]
        assert row["uses"] == 1 and row["outcome"] is None
        assert p._salient_replay_ok(obs, taken, 3, 0) is False, (
            "the bit mastery is fed is a property of the replay, not of the "
            "guard's arm")


# ─────────────────────────────────────────────────────────────────────────────
# The corrected constant (the ruling's third clause)
# ─────────────────────────────────────────────────────────────────────────────

def test_the_constant_is_documented_as_the_fallback_prior():
    with open(PLAYER, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    i = src.find("_SALIENT_REPLAY_P = 0.2")
    assert i != -1, "the fallback prior must stay a named constant at 0.2"
    window = src[max(0, i - 500):i + 120].lower()
    assert "fallback" in window, (
        "the constant's comment must say what it now is: the fallback prior")
    assert "mirror" not in src[i:i + 120].lower(), (
        "it is not 'the mastery-lite mirror' any more — the mirror is the "
        "call, and the call is real")
