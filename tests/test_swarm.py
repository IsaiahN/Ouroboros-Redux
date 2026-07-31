"""
redux-triality: the SWARM runner -- one ReduxPolicy per game across many games, shared scorecard + rate limiter +
blackboard (the eval harness's execution model, plus the cross-game transfer the official swarm lacks). Tested
fully OFFLINE via injected FakeSessions + a timing test on the global rate limiter.
"""
import sys, os, time, threading
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.swarm import RateLimiter, run_swarm, _play_policy
from newhorse.redux_arch.policy import Blackboard, CLICK, TWO_BODY, DIRECTIONAL


# ---- rate limiter -------------------------------------------------------------------------------------------
def test_rate_limiter_spaces_serial_calls():
    rl = RateLimiter(rpm=600)                       # interval 0.1s
    t0 = time.monotonic()
    for _ in range(5):
        rl.acquire()
    assert time.monotonic() - t0 >= 0.35            # >=4 gaps of 0.1s (loose for scheduling slack)


def test_rate_limiter_caps_aggregate_across_threads():
    rl = RateLimiter(rpm=1200)                      # interval 0.05s
    t0 = time.monotonic()
    def worker():
        for _ in range(4):
            rl.acquire()
    ts = [threading.Thread(target=worker) for _ in range(3)]   # 12 acquires total
    for t in ts: t.start()
    for t in ts: t.join()
    assert time.monotonic() - t0 >= 0.45            # global spacing: ~11 gaps of 0.05s regardless of threads


# ---- fake worlds/sessions (offline) -------------------------------------------------------------------------
class _TwoBody:
    def __init__(self):
        self.L = [10, 4]; self.R = [10, 15]
        self.mv = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
    def frame(self):
        g = np.zeros((20, 20), dtype=int); g[tuple(self.L)] = 7; g[tuple(self.R)] = 7; return g
    def step_val(self, v, data=None):
        d = self.mv.get(v, (0, 0))
        if v in (1, 2):
            self.L = [self.L[0] + d[0], self.L[1] + d[1]]; self.R = [self.R[0] + d[0], self.R[1] + d[1]]
        else:
            self.L = [self.L[0], self.L[1] + d[1]]; self.R = [self.R[0], self.R[1] - d[1]]


class _Dir:
    def __init__(self):
        self.p = [10, 10]; self.mv = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
    def frame(self):
        g = np.zeros((20, 20), dtype=int); g[2:4, 2:4] = 3; g[tuple(self.p)] = 9; return g
    def step_val(self, v, data=None):
        d = self.mv.get(v, (0, 0)); nb = [self.p[0] + d[0], self.p[1] + d[1]]
        if 0 <= nb[0] < 20 and 0 <= nb[1] < 20 and not (2 <= nb[0] < 4 and 2 <= nb[1] < 4):
            self.p = nb


class _Click:
    def frame(self):
        g = np.full((24, 24), 5, dtype=int); g[3:5, 3:5] = 2; g[18:20, 18:20] = 3; return g
    def step_val(self, v, data=None):
        pass


class FakeSession:
    def __init__(self, world, avail, win_after=None):
        self.world = world; self.avail = avail; self.win_after = win_after; self.steps = 0
        self.view_url = "fake://scorecard"
    def open(self):
        return self._snap()
    def step(self, val, data=None):
        self.world.step_val(val, data); self.steps += 1; return self._snap()
    def _snap(self):
        won = self.win_after is not None and self.steps >= self.win_after
        return dict(grid=self.world.frame(), available=self.avail,
                    levels_completed=(1 if won else 0), state=("WIN" if won else "NOT_FINISHED"), done=won)
    def close(self):
        pass


def test_play_policy_routes_and_reports_via_fake_session():
    bb = Blackboard()
    r = _play_policy(FakeSession(_TwoBody(), [1, 2, 3, 4, 5]), bb, "m0r0-x", max_actions=15, wall_cap_s=5)
    assert r["family"] == TWO_BODY and r["game"] == "m0r0-x"


class _FlakyOpenSession(FakeSession):
    """open() raises `fail_n` times (a transient reset 500 under concurrency) then succeeds -- the exact failure
    that dropped m0r0 from the swarm-L scorecard. The retry loop must recover instead of returning an error."""
    def __init__(self, world, avail, fail_n):
        super().__init__(world, avail)
        self._fail_n = fail_n; self.open_calls = 0
    def open(self):
        self.open_calls += 1
        if self.open_calls <= self._fail_n:
            raise RuntimeError("online reset returned None (rate limit / server 500)")
        return self._snap()


def test_play_policy_recovers_from_transient_open_failures():
    bb = Blackboard()
    s = _FlakyOpenSession(_TwoBody(), [1, 2, 3, 4, 5], fail_n=3)   # fails 3x then opens -- within the 6 retries
    r = _play_policy(s, bb, "m0r0-x", max_actions=12, wall_cap_s=5, open_backoff=0.0)
    assert r["family"] == TWO_BODY                                  # recovered and played, not an open_error
    assert s.open_calls == 4                                        # 3 failures + 1 success


def test_play_policy_reports_open_error_only_after_exhausting_retries():
    bb = Blackboard()
    s = _FlakyOpenSession(_TwoBody(), [1, 2, 3, 4, 5], fail_n=99)  # never opens
    r = _play_policy(s, bb, "x-1", max_actions=5, wall_cap_s=5, open_retries=4, open_backoff=0.0)
    assert r["family"] == "error" and r["outcome"].startswith("open_error")
    assert s.open_calls == 4                                        # tried exactly open_retries times


def test_swarm_runs_all_families_concurrently_and_shares_blackboard():
    worlds = {"m0r0-a": (_TwoBody(), [1, 2, 3, 4, 5], None),
              "s5i5-a": (_Click(), [6], None),
              "ls20-a": (_Dir(), [1, 2, 3, 4, 5], None)}
    def factory(gid, scorecard_id=None, limiter=None):
        w, avail, win = worlds[gid]
        return FakeSession(w, avail, win_after=win)
    bb = Blackboard()
    res = run_swarm(list(worlds), max_actions=16, wall_cap_s=8, rpm=6000,
                    blackboard=bb, session_factory=factory, start_stagger_s=0.0, open_backoff=0.0)
    assert set(res["results"]) == set(worlds)                         # every game ran to a result
    assert res["families"]["m0r0-a"] == TWO_BODY
    assert res["families"]["s5i5-a"] == CLICK
    assert res["families"]["ls20-a"] == DIRECTIONAL
    # the shared blackboard accumulated each game's recognised family (cross-game transfer substrate)
    assert bb.get("m0r0").get("family") == TWO_BODY
    assert bb.get("s5i5").get("family") == CLICK


def test_swarm_records_a_win():
    def factory(gid, scorecard_id=None, limiter=None):
        return FakeSession(_TwoBody(), [1, 2, 3, 4, 5], win_after=6)
    res = run_swarm(["m0r0-w"], max_actions=30, wall_cap_s=5, session_factory=factory, start_stagger_s=0.0, open_backoff=0.0)
    assert res["results"]["m0r0-w"]["levels"] == 1 and res["total_levels"] == 1


def test_swarm_one_game_error_does_not_sink_the_rest():
    class Boom:
        def open(self): raise RuntimeError("boom")
        def close(self): pass
    def factory(gid, scorecard_id=None, limiter=None):
        return Boom() if gid == "bad-1" else FakeSession(_Dir(), [1, 2, 3, 4, 5])
    res = run_swarm(["bad-1", "ls20-b"], max_actions=12, wall_cap_s=5, session_factory=factory, start_stagger_s=0.0, open_backoff=0.0)
    assert res["results"]["bad-1"]["family"] == "error"              # isolated failure
    assert res["families"]["ls20-b"] == DIRECTIONAL                  # the healthy game still ran


# ---- TETHER-STAGE distribution ------------------------------------------------------------------------------
# The swarm is where most play happens and it reported no stage code at all, so the measured stall distribution was
# blind to nearly every stall the build has ever produced. These pin that every game now reports, that the pooled
# distribution adds up, and that the pooling can never over-credit.

def test_every_swarm_result_carries_a_measured_tether_stage():
    worlds = {"m0r0-a": (_TwoBody(), [1, 2, 3, 4, 5], None),
              "ls20-a": (_Dir(), [1, 2, 3, 4, 5], None)}
    def factory(gid, scorecard_id=None, limiter=None):
        w, avail, win = worlds[gid]
        return FakeSession(w, avail, win_after=win)
    res = run_swarm(list(worlds), max_actions=14, wall_cap_s=8, rpm=6000,
                    session_factory=factory, start_stagger_s=0.0, open_backoff=0.0)
    for gid in worlds:
        ts = res["results"][gid]["tether_stage"]
        assert ts["stalls"] >= 1                                      # the action cap is a stall and is scored
        assert ts["furthest_stage"] is not None
    d = res["tether_chain"]
    assert d["games_reporting"] == len(worlds)
    assert d["stalls"] == sum(res["results"][g]["tether_stage"]["stalls"] for g in worlds)
    assert sum(d["counts"].values()) == d["stalls"]                   # every stall lands in exactly one bucket
    assert d["indicts"] != "architecture"                             # reuse is not wired; it may never say this


def test_pooled_distribution_takes_the_deepest_stall_not_the_average():
    from newhorse.redux_arch.swarm import tether_distribution
    fake = {"a": dict(tether_stage=dict(counts={"DIED_PRE_DIFF": 3}, stalls=3, advances=0,
                                        furthest_stage="DIED_PRE_DIFF", furthest_rank=0)),
            "b": dict(tether_stage=dict(counts={"MINT_UNFIRED": 1}, stalls=1, advances=2,
                                        furthest_stage="MINT_UNFIRED", furthest_rank=2)),
            "c": dict(outcome="open_error:X")}                        # a game that never ran contributes nothing
    d = tether_distribution(fake)
    assert d["worst_stage"] == "MINT_UNFIRED" and d["indicts"] == "gate/implementation"
    assert d["stalls"] == 4 and d["advances"] == 2 and d["games_reporting"] == 2
    assert d["counts"] == {"DIED_PRE_DIFF": 3, "MINT_UNFIRED": 1}


# ---- ★ THE ACTION BUDGET IDENTITY ---------------------------------------------------------------------------
# `decide_calls` reproduced at 2943 on eleven consecutive sweeps and was read as "the ACTION budget binds". It is
# not the budget. `_play_policy` increments `steps` at TWO sites -- after a `pol.choose()` (which produces exactly
# one `decide()` exit) and at the EARNED RESET (which produces none) -- so, exactly and always:
#
#       decide_exits(game) == steps(game) - retries(game)
#
# These tests pin that identity against a REAL `_play_policy` run, and pin the two fall-through exits to their own
# literals. Before this beat a single literal, pre-set BEFORE the loop, named the action cap for BOTH of them.
class _Maze:
    """A directional world whose marker moves every step, so no two boards repeat. That matters: a reset is EARNED
    only when the death taught a NEW (board, action) cause, so a static world would die repeatedly on one cause and
    never exercise the reset site this identity is about."""
    def __init__(self):
        self.t = 0
    def frame(self):
        g = np.zeros((20, 20), dtype=int); g[2:4, 2:4] = 3
        g[self.t % 20, (self.t * 7) % 20] = 9
        return g
    def step_val(self, v, data=None):
        self.t += 1


class _DyingSession(FakeSession):
    """Reports GAME_OVER every `die_every` steps and can be restarted. The restart is the ONE site in
    `_play_policy` that spends an action WITHOUT a `decide()` call, which is the whole point of the identity.

    `step_calls` counts calls to `session.step`, and every such call follows exactly one `pol.choose()` -- so
    `step_calls` IS the decide-exit count, measured at the collaborator rather than inferred from the policy."""
    def __init__(self, world, avail, die_every):
        super().__init__(world, avail)
        self.die_every = die_every; self.resets = 0; self.step_calls = 0; self._dead = False
    def step(self, val, data=None):
        self.step_calls += 1
        self.world.step_val(val, data); self.steps += 1
        self._dead = (self.steps % self.die_every == 0)
        return self._snap()
    def reset_after_death(self, reasoning=None):
        self.resets += 1; self._dead = False; self.world.t += 3
        return self._snap()
    def _snap(self):
        return dict(grid=self.world.frame(), available=self.avail, levels_completed=0,
                    state=("GAME_OVER" if self._dead else "NOT_FINISHED"), done=self._dead)


def test_the_action_budget_identity_decide_exits_equals_steps_minus_retries():
    """The identity, measured -- not asserted from the source. `step_calls` is counted inside the session, on the
    other side of the call boundary from the counter under test."""
    s = _DyingSession(_Maze(), [1, 2, 3, 4, 5], die_every=9)
    r = _play_policy(s, Blackboard(), "m0r0-x", max_actions=40, wall_cap_s=30)
    assert r["retries"] >= 1, r                             # the reset site actually ran; without it this is vacuous
    assert s.step_calls == r["steps"] - r["retries"], (s.step_calls, r["steps"], r["retries"])
    assert s.resets == r["retries"], (s.resets, r["retries"])


def test_a_run_with_no_deaths_spends_every_step_on_a_decision():
    """The control for the test above: with no reset site firing, `retries` is 0 and `steps` IS the decide count.
    A version of the identity that only held when retries were nonzero would not be an identity."""
    s = _DyingSession(_Maze(), [1, 2, 3, 4, 5], die_every=10 ** 6)
    r = _play_policy(s, Blackboard(), "m0r0-x", max_actions=12, wall_cap_s=30)
    assert r["retries"] == 0 and s.step_calls == r["steps"] == 12


def test_the_wall_clock_exit_no_longer_reports_the_action_cap():
    """★ THE MIS-NAMED EXIT. `outcome` was pre-set to `"action_cap"` before a loop with TWO fall-through exit
    conditions, so a wall-clock stop printed the action cap's name. Every "no sweep was wall-clock bound" reading
    ever taken off this field came from a name nobody chose at the exit that produced it."""
    r = _play_policy(FakeSession(_Dir(), [1, 2, 3, 4, 5]), Blackboard(), "m0r0-x",
                     max_actions=10 ** 6, wall_cap_s=0.5)
    assert r["outcome"] == "wall_cap", r["outcome"]
    assert r["steps"] < 10 ** 6


def test_the_action_cap_exit_names_the_action_cap():
    r = _play_policy(FakeSession(_Dir(), [1, 2, 3, 4, 5]), Blackboard(), "m0r0-x",
                     max_actions=12, wall_cap_s=60)
    assert r["outcome"] == "action_cap" and r["steps"] == 12


def test_no_exit_is_left_unattributed():
    """`loop_exit_unattributed` is the literal that fires when the post-loop re-test finds NEITHER condition true,
    which cannot happen. It exists so that if the guard is ever wrong it says so by name instead of borrowing a
    neighbour's label -- and no ordinary run may produce it."""
    for kw in (dict(max_actions=8, wall_cap_s=60), dict(max_actions=10 ** 6, wall_cap_s=0.4)):
        r = _play_policy(FakeSession(_Dir(), [1, 2, 3, 4, 5]), Blackboard(), "m0r0-x", **kw)
        assert r["outcome"] != "loop_exit_unattributed", (kw, r["outcome"])


def test_the_swarm_carries_the_denominator_across_the_process_boundary():
    """A count that crosses a boundary without its denominator cannot be read. `steps` crossed alone until this
    beat, so a printer could not tell an action-capped game from one that stopped twenty short."""
    def factory(gid, scorecard_id=None, limiter=None):
        return FakeSession(_Dir(), [1, 2, 3, 4, 5])
    res = run_swarm(["ls20-a"], max_actions=9, wall_cap_s=8, rpm=6000,
                    session_factory=factory, start_stagger_s=0.0, open_backoff=0.0)
    assert res["max_actions"] == 9 and res["wall_cap_s"] == 8.0
    assert res["results"]["ls20-a"]["steps"] == 9
    assert res["results"]["ls20-a"]["outcome"] == "action_cap"


# ---- ★ THE DEATH EXIT, SPLIT INTO THE THREE CONDITIONS IT COVERED -------------------------------------------
# `GAME_OVER` was ONE literal at ONE `break` guarded by `not can_retry or not earned or retries >= retry_cap`.
# Those are three different findings about the agent -- the harness cannot restart, the death memory ALREADY held
# this cause, or the harness cut the run off -- and arm K's three short games all reported the single name.
class _Still:
    """A board that never changes, so every death repeats the same (board, action) cause once the action does."""
    def __init__(self):
        self.t = 0
    def frame(self):
        g = np.zeros((20, 20), dtype=int); g[2:4, 2:4] = 3; g[10, 10] = 9
        return g
    def step_val(self, v, data=None):
        self.t += 1


class _DyingNoResetSession(FakeSession):
    """Dies and offers NO `reset_after_death`, which is how `_play_policy` learns a session cannot restart. It is a
    separate class rather than a flag because `can_retry` is `hasattr`, and a flag would still have the method."""
    def __init__(self, world, avail, die_every):
        super().__init__(world, avail)
        self.die_every = die_every; self._dead = False
    def step(self, val, data=None):
        self.world.step_val(val, data); self.steps += 1
        self._dead = (self.steps % self.die_every == 0)
        return self._snap()
    def _snap(self):
        return dict(grid=self.world.frame(), available=self.avail, levels_completed=0,
                    state=("GAME_OVER" if self._dead else "NOT_FINISHED"), done=self._dead)


def test_a_death_that_teaches_nothing_new_names_itself():
    """The condition arm K's three short games were almost certainly in -- s5i5, vc33 and su15 each carried one
    more death than retry -- and which the old single literal could not distinguish from the retry cap."""
    s = _DyingSession(_Still(), [1], die_every=1)
    r = _play_policy(s, Blackboard(), "m0r0-x", max_actions=40, wall_cap_s=30)
    assert r["outcome"] == "death_no_new_cause", r["outcome"]
    assert r["retries"] < 6                                     # not the cap; the cause repeated


def test_an_exhausted_retry_cap_names_the_CAP_and_not_the_agent():
    """The opposite finding on the same exit: the board keeps teaching new causes and the HARNESS stops the run.
    Reading this as `death_no_new_cause` would credit the agent's memory for a limit the builder chose."""
    s = _DyingSession(_Maze(), [1, 2, 3, 4, 5], die_every=1)
    r = _play_policy(s, Blackboard(), "m0r0-x", max_actions=60, wall_cap_s=30)
    assert r["outcome"] == "death_retry_cap", r["outcome"]
    assert r["retries"] == 6


def test_a_session_that_cannot_restart_says_so_rather_than_blaming_the_death():
    s = _DyingNoResetSession(_Maze(), [1, 2, 3, 4, 5], die_every=4)
    r = _play_policy(s, Blackboard(), "m0r0-x", max_actions=40, wall_cap_s=30)
    assert r["outcome"] == "death_no_reset_support", r["outcome"]
    assert r["retries"] == 0


def test_the_death_identity_one_unearned_death_on_a_death_exit_and_none_otherwise():
    """★ THE SECOND IDENTITY, FREE ON THE SAME RECEIPT. `deaths` counts observed GAME_OVERs, `retries` counts the
    ones that earned a restart, so a run ending on a death carries exactly ONE unearned death -- the terminal
    one -- and a run ending any other way carries NONE."""
    died = _play_policy(_DyingSession(_Still(), [1], die_every=1), Blackboard(), "m0r0-x",
                        max_actions=40, wall_cap_s=30)
    assert died["outcome"].startswith("death_") and died["deaths"] - died["retries"] == 1, died
    lived = _play_policy(_DyingSession(_Maze(), [1, 2, 3, 4, 5], die_every=9), Blackboard(), "m0r0-x",
                         max_actions=40, wall_cap_s=30)
    assert not lived["outcome"].startswith("death_") and lived["deaths"] - lived["retries"] == 0, lived


def test_the_retired_GAME_OVER_literal_is_gone_from_the_exit():
    """No path may still produce the pooled name. If one does, the split is incomplete and the receipt is back to
    summarising three conditions under one word."""
    for s in (_DyingSession(_Still(), [1], die_every=1),
              _DyingSession(_Maze(), [1, 2, 3, 4, 5], die_every=1),
              _DyingNoResetSession(_Maze(), [1, 2, 3, 4, 5], die_every=4)):
        r = _play_policy(s, Blackboard(), "m0r0-x", max_actions=60, wall_cap_s=30)
        assert r["outcome"] != "GAME_OVER", r["outcome"]


def test_the_TERMINAL_death_carries_the_reason_it_refused_the_restart():
    """★ THE `why` STRING WAS PRODUCED AND THROWN AWAY. `reset_earned()` has returned `(earned, why)` since §XIX
    shipped and `_play_policy` has written it into `log` all along; nothing ever read it. The exit literal names the
    BRANCH -- this names the EVIDENCE the branch stood on, which is the only place the WHICH-cause question has ever
    been answered. Assert on the log the policy WROTE, not on a reconstruction of it."""
    r = _play_policy(_DyingSession(_Still(), [1], die_every=1), Blackboard(), "m0r0-x",
                     max_actions=40, wall_cap_s=30)
    assert r["outcome"] == "death_no_new_cause", r["outcome"]
    terminal = [l for l in r["log"] if l.startswith("no RESET")]
    assert len(terminal) == 1, r["log"]                       # the branch `break`s, so exactly one can exist
    assert "death_no_new_cause" in terminal[0] and "earned=False" in terminal[0]
    assert "repeats a cause already in game-memory" in terminal[0], terminal[0]


def test_an_EARNED_restart_records_the_new_cause_it_was_granted_for():
    """The other half: a restart that WAS granted writes its own line, so a reader can tell a run that learned four
    new causes and then stopped from one that learned nothing and stopped immediately."""
    r = _play_policy(_DyingSession(_Maze(), [1, 2, 3, 4, 5], die_every=5), Blackboard(), "m0r0-x",
                     max_actions=40, wall_cap_s=30)
    earned = [l for l in r["log"] if l.startswith("EARNED RESET")]
    assert earned and len(earned) == r["retries"], (earned, r["retries"])
    assert "NEW avoidable cause" in earned[0], earned[0]


def test_the_size_of_the_death_MEMORY_crosses_the_process_boundary():
    """`death_no_new_cause` says the terminal death repeated something already held. How MUCH was held is a
    different number and it lived only inside the policy. A run that stops with one cause stopped on its second
    death; a run that stops with several spent the run learning first. Same literal, two different agents."""
    lots = _play_policy(_DyingSession(_Maze(), [1, 2, 3, 4, 5], die_every=5), Blackboard(), "m0r0-x",
                        max_actions=40, wall_cap_s=30)
    assert lots["causes"] >= 1 and lots["causes"] >= lots["retries"], lots
    none = _play_policy(FakeSession(_Maze(), [1, 2, 3, 4, 5]), Blackboard(), "m0r0-x",
                        max_actions=10, wall_cap_s=30)
    assert none["deaths"] == 0 and none["causes"] == 0, none    # nothing died, so nothing was learned this way


def test_a_game_that_never_opens_reports_the_EXCEPTION_TEXT_and_not_just_its_class():
    """★ `open_error:RuntimeError` NAMES THE CLASS AND NOTHING ELSE -- and one class covered a 400, a 500 and a
    None reset across three games and three arms. The literal is UNCHANGED (every comparison against it still
    holds); the text rides beside it."""
    s = _FlakyOpenSession(_TwoBody(), [1, 2, 3, 4, 5], fail_n=99)
    r = _play_policy(s, Blackboard(), "x-1", max_actions=5, wall_cap_s=5, open_retries=2, open_backoff=0.0)
    assert r["outcome"] == "open_error:RuntimeError"
    assert "rate limit / server 500" in r["error_text"], r.get("error_text")


def test_the_key_can_never_ride_out_on_an_exception_string():
    """ENV-ONLY has to hold in the FAILURE path too: the receipt is captured to a file and read back. A key value
    present in the environment is redacted out of any text this module emits."""
    from newhorse.redux_arch.swarm import _scrub
    old = os.environ.get("ARC_API_KEY")
    os.environ["ARC_API_KEY"] = "sk-live-abcdef0123456789"
    try:
        out = _scrub(RuntimeError("GET /api?key=sk-live-abcdef0123456789 failed"))
        assert "sk-live-abcdef0123456789" not in out and "***KEY-REDACTED***" in out, out
        assert len(_scrub("x" * 5000)) < 400                    # one traceback cannot bury the receipt
    finally:
        if old is None:
            os.environ.pop("ARC_API_KEY", None)
        else:
            os.environ["ARC_API_KEY"] = old
