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
