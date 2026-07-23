"""
redux-triality: the CONTROL-INVERSION policy. The eval harness owns the loop and calls choose_action per step (and
runs a SWARM across games). ReduxPolicy re-expresses the reclaimed organs as a stateful per-step brain: it routes a
game into its family within a TIGHT warmup budget (RHAE squares action efficiency; warmup is pure cost) and
dispatches the right organ. These tests pin: correct family routing, the warmup budget, click-action shape, and the
cross-game blackboard transfer the official swarm lacks.
"""
import sys, os, glob, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.policy import (ReduxPolicy, Blackboard, _prefix, level_delta, GoalProbe,
                                        _nearest_colour_centroid, CLICK, TWO_BODY, DIRECTIONAL, PENDING)
from newhorse.redux_arch.coupled import two_body_goal_action, learn_two_body


class AMirror:
    """MirrorWorld keyed by A-labels: A1=up, A2=down (both bodies same); A3/A4 mirror horizontally. == m0r0 coupling."""
    def __init__(self):
        self.L = [10, 4]; self.R = [10, 15]
        self.mv = {"A1": (-1, 0), "A2": (1, 0), "A3": (0, -1), "A4": (0, 1)}

    def frame(self):
        g = np.zeros((20, 20), dtype=int); g[tuple(self.L)] = 7; g[tuple(self.R)] = 7; return g

    def step(self, a):
        d = self.mv.get(a, (0, 0))
        if a in ("A1", "A2"):
            self.L = [self.L[0] + d[0], self.L[1] + d[1]]; self.R = [self.R[0] + d[0], self.R[1] + d[1]]
        else:
            self.L = [self.L[0], self.L[1] + d[1]]; self.R = [self.R[0], self.R[1] - d[1]]
        return self.frame()


class ADrive:
    """Single-body drive world keyed by A-labels: one cursor (colour 9) on floor 0 + a static block (colour 3)."""
    def __init__(self):
        self.p = [10, 10]
        self.mv = {"A1": (-1, 0), "A2": (1, 0), "A3": (0, -1), "A4": (0, 1)}

    def frame(self):
        g = np.zeros((20, 20), dtype=int); g[2:4, 2:4] = 3; g[tuple(self.p)] = 9; return g

    def step(self, a):
        d = self.mv.get(a, (0, 0))
        nb = [self.p[0] + d[0], self.p[1] + d[1]]
        if 0 <= nb[0] < 20 and 0 <= nb[1] < 20 and not (2 <= nb[0] < 4 and 2 <= nb[1] < 4):
            self.p = nb
        return self.frame()


def _run_closed_loop(world, avail, n):
    """Drive ReduxPolicy against a synthetic world for n steps; return the policy."""
    p = ReduxPolicy(game_id="test-abc", blackboard=Blackboard(), warmup_cap=8)
    grid = world.frame()
    for _ in range(n):
        p.observe(grid, avail)
        lbl, data = p.choose()
        grid = world.step(lbl)
    return p


def test_router_dispatches_two_body_within_warmup_budget():
    p = _run_closed_loop(AMirror(), avail=[1, 2, 3, 4, 5], n=12)
    assert p.family == TWO_BODY
    assert p.tb_colour == 7 and p.ag is not None and p.ag.ready()
    # RHAE discipline: routed to the organ well inside the warmup cap (not a 40-action warmup)
    assert p.warmup_cap <= 8


def test_router_dispatches_single_body_directional():
    p = _run_closed_loop(ADrive(), avail=[1, 2, 3, 4, 5], n=12)
    assert p.family == DIRECTIONAL
    assert p.cursor == 9 and p.vecs                      # learned the cursor + its per-action vecs


def test_click_only_routes_click_and_emits_xy_action():
    board = np.full((32, 32), 5, dtype=int); board[4:6, 4:6] = 2; board[20:22, 25:27] = 3
    p = ReduxPolicy(game_id="s5i5-x", blackboard=Blackboard())
    p.observe(board, [6])                                # click-only: no directional actions
    lbl, data = p.choose()
    assert p.family == CLICK
    assert lbl == "A6" and set(data) == {"x", "y"}       # ACTION6 carries explicit coordinates
    assert 0 <= data["x"] < 32 and 0 <= data["y"] < 32   # click lands on-frame


def test_click_prober_advances_and_credits_change():
    board = np.full((16, 16), 5, dtype=int); board[3:5, 3:5] = 2
    p = ReduxPolicy(game_id="c-1", blackboard=Blackboard())
    coords = []
    grid = board
    for i in range(6):
        p.observe(grid, [6])
        lbl, data = p.choose()
        coords.append((data["x"], data["y"]))
        grid = board.copy(); grid[0, 0] = (i % 7)         # every click "changes" the board
    assert lbl == "A6"
    assert len(set(coords)) > 1                            # it probes DIFFERENT coordinates, not one point


def test_blackboard_transfers_family_across_games_of_a_prefix():
    bb = Blackboard()
    p1 = _run_closed_loop_bb(AMirror(), [1, 2, 3, 4, 5], 12, bb, "m0r0-aaaa")
    assert p1.family == TWO_BODY
    # a fresh game of the SAME prefix finds the reclaimed mechanism already on the board
    assert bb.get(_prefix("m0r0-bbbb")).get("family") == TWO_BODY
    assert bb.get("m0r0").get("colour") == 7


def _run_closed_loop_bb(world, avail, n, bb, game_id):
    p = ReduxPolicy(game_id=game_id, blackboard=bb, warmup_cap=8)
    grid = world.frame()
    for _ in range(n):
        p.observe(grid, avail); lbl, data = p.choose(); grid = world.step(lbl)
    return p


def test_level_delta_reports_new_colours_and_actions():
    prev = np.full((8, 8), 5, dtype=int); prev[0, 0] = 2
    new = np.full((8, 8), 5, dtype=int); new[0, 0] = 2; new[1, 1] = 7   # colour 7 is NEW this level
    d = level_delta(prev, new, prev_avail=[1, 2, 3], new_avail=[1, 2, 3, 4])
    assert d["new_colours"] == [7] and d["new_actions"] == [4]          # a new actor + a newly-unlocked action
    assert d["gone_colours"] == [] and d["gone_actions"] == []


def test_level_change_keeps_family_when_referent_survives():
    # DIRECTIONAL policy; on the graduated level the cursor colour still exists -> KEEP (motion model transfers)
    p = _run_closed_loop(ADrive(), avail=[1, 2, 3, 4, 5], n=12)
    assert p.family == DIRECTIONAL and p.cursor == 9
    new_level_frame = np.zeros((20, 20), dtype=int); new_level_frame[5:7, 5:7] = 3; new_level_frame[8, 8] = 9
    p.observe(new_level_frame, [1, 2, 3, 4, 5], levels_completed=1)
    assert p.family == DIRECTIONAL                                      # kept
    assert p.level_model["decision"] == "keep" and p.level == 1
    assert p.prior is not None and p.prior["from_level"] == 0           # transfer frozen


def test_level_change_rederives_when_referent_gone():
    # TWO_BODY policy; graduated level has NO two bodies of the coupled colour -> RE-DERIVE (mechanic changed)
    p = _run_closed_loop(AMirror(), avail=[1, 2, 3, 4, 5], n=12)
    assert p.family == TWO_BODY and p.tb_colour == 7
    n_before = p.n_emitted
    blank = np.zeros((20, 20), dtype=int)                              # the navy bodies are gone
    p.observe(blank, [1, 2, 3, 4, 5], levels_completed=1)
    assert p.family == PENDING                                         # re-routing on the new level
    assert p.level_model["decision"] == "rederive"
    assert p._warm_start == n_before                                   # warmup counter reset -> re-warms
    assert p.prior is not None and p.prior["tb_colour"] == 7           # prior retained (transfer, not discard)


def test_goal_probe_rotates_meet_deliver_then_new_actors_and_locks():
    p = GoalProbe(referent_colours=[6, 8], meet_first=True, budget=3)
    assert p.current() == ("meet", None)                   # try the transferred goal first (cheap)
    for _ in range(3):
        p.tick()
    assert p.current() == ("deliver", None)                # then the PAIRED two-zone goal
    for _ in range(3):
        p.tick()
    assert p.current() == ("near", 6)                      # then single new actors
    for _ in range(3):
        p.tick()
    assert p.current() == ("near", 8)
    p.lock()                                               # a hypothesis paid off
    before = p.current()
    for _ in range(10):
        p.tick()
    assert p.locked and p.current() == before              # locked: no more rotation


def test_largest_zones_and_assignment():
    from newhorse.redux_arch.policy import _largest_zones, _assign_zones
    g = np.full((40, 40), 5, dtype=int)
    g[30:38, 4:12] = 6                                      # zone A (bottom-left), 8x8
    g[30:38, 28:36] = 15                                   # zone B (bottom-right), 8x8
    g[10, 20] = 8                                           # a tiny distractor
    zones = _largest_zones(g, [6, 8, 15], exclude=10, k=2)
    assert {z[3] for z in zones} == {6, 15}                # the two big zones, not the 1px colour-8
    bodies = [(15, 6), (15, 30)]                            # body0 left, body1 right
    (c0, r0), (c1, r1) = _assign_zones(bodies, zones, stride=1)
    assert c0[1] < c1[1]                                    # body0 -> left zone, body1 -> right zone (min distance)


def test_two_body_deliver_drives_bodies_to_distinct_zones():
    from newhorse.redux_arch.coupled import two_body_deliver_action
    w = AMirror()
    frames = [w.frame()]; acts = ["RESET"]
    for a in (["A1", "A2", "A3", "A4"] * 5):
        frames.append(w.step(a)); acts.append(a)
    colour, ag = learn_two_body(frames, acts)
    passable = lambda i, cell: 0 <= cell[0] < 20 and 0 <= cell[1] < 20
    bodies = [(10, 4), (10, 15)]
    a = two_body_deliver_action(bodies, ag, passable, target0=(2, 4), target1=(2, 15), stride=1, reach0=1, reach1=1)
    assert a in ("A1", "A2", "A3", "A4")                    # returns a first action toward the paired goal
    # driving both bodies UP (A1) reduces both bodies' distance to their (row-2) targets
    m0 = ag.body_map(0)["A1"]; m1 = ag.body_map(1)["A1"]
    assert m0[0] == -1 and m1[0] == -1


def test_nearest_colour_centroid_picks_and_excludes_self():
    g = np.zeros((20, 20), dtype=int); g[2, 2] = 6; g[15, 15] = 6; g[10, 10] = 7
    # nearest colour-6 blob to a body near (3,3) is the (2,2) one
    assert _nearest_colour_centroid(g, 6, (3, 3), exclude=7) == (2, 2)
    assert _nearest_colour_centroid(g, 7, (0, 0), exclude=7) is None   # never target the bodies' own colour


def test_two_body_goal_action_drives_a_body_toward_a_target():
    w = AMirror()
    frames = [w.frame()]; acts = ["RESET"]
    for a in (["A1", "A2", "A3", "A4"] * 5):
        frames.append(w.step(a)); acts.append(a)
    colour, ag = learn_two_body(frames, acts)
    assert ag is not None and ag.ready()
    passable = lambda i, dest: 0 <= dest[0] < 20 and 0 <= dest[1] < 20
    bodies = [[3, 4], [3, 15]]                               # body0 at (3,4)
    target = (0, 4)                                          # straight up from body0
    a = two_body_goal_action(bodies, ag, passable, target, which=0)
    # the chosen action should reduce body0's distance to the target
    d0 = abs(bodies[0][0] - target[0]) + abs(bodies[0][1] - target[1])
    mp = ag.body_map(0)[a]
    nd = abs(bodies[0][0] + mp[0] - target[0]) + abs(bodies[0][1] + mp[1] - target[1])
    assert nd < d0


def test_keep_on_two_body_arms_the_goal_probe_with_new_actors():
    p = _run_closed_loop(AMirror(), avail=[1, 2, 3, 4, 5], n=12)
    assert p.family == TWO_BODY
    # graduate to a level that still has the two bodies (KEEP) PLUS a new actor colour 6
    nf = np.zeros((20, 20), dtype=int); nf[10, 4] = 7; nf[10, 15] = 7; nf[5, 9] = 6
    p.observe(nf, [1, 2, 3, 4, 5], levels_completed=1)
    assert p.level_model["decision"] == "keep"
    assert p._probe is not None and ("near", 6) in p._probe.hypotheses   # probe armed with the new actor


def test_router_two_body_on_real_m0r0_recording():
    hits = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "recordings", "*", "m0r0-*.jsonl")))
    if not hits:
        import pytest; pytest.skip("no m0r0 recording")
    recs = [json.loads(l)["data"] for l in open(hits[0]).read().splitlines()]
    frames = [np.array(r["frame"])[-1] for r in recs][:40]
    acts = [r.get("action_input", {}).get("id", "?") for r in recs][:40]
    p = ReduxPolicy(game_id="m0r0-492f87ba", blackboard=Blackboard())
    p.frames = [np.asarray(f) for f in frames]; p.acts = acts        # inject the real stream, then route
    p._route([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert p.family == TWO_BODY and p.tb_colour == 10                # the navy two bodies (real m0r0)
