"""
redux-triality: trail-aware / multi-mover cursor detection -- unlocks games that routed UNDRIVABLE because a
growing trail (g50t) or a second mover (sc25) defeats the footprint-only detector. LAW-0 confirmed g50t's real
cursor is colour 9 (constant-size translator) while colour 1 is the trail (grows).
"""
import sys, os, glob, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.replay import translating_cursor, learn_basis_trailaware, learn_basis
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard, DIRECTIONAL


class TrailWorld:
    """Cursor colour 9 (1px) moves by action and leaves a colour-1 TRAIL at every prior cell (the trail GROWS)."""
    def __init__(self):
        self.p = [10, 10]; self.trail = set(); self.mv = {"A1": (-1, 0), "A2": (1, 0), "A3": (0, -1), "A4": (0, 1)}
    def frame(self):
        g = np.full((20, 20), 5, dtype=int)
        for (r, c) in self.trail:
            g[r, c] = 1
        g[tuple(self.p)] = 9
        return g
    def step(self, a):
        self.trail.add(tuple(self.p))
        d = self.mv.get(a, (0, 0)); nb = [self.p[0] + d[0], self.p[1] + d[1]]
        if 0 <= nb[0] < 20 and 0 <= nb[1] < 20:
            self.p = nb
        return self.frame()


def _stream(world, seq):
    frames = [world.frame()]; acts = ["RESET"]
    for a in seq:
        frames.append(world.step(a)); acts.append(a)
    return frames, acts


def test_translating_cursor_prefers_constant_size_translator_over_trail():
    frames, acts = _stream(TrailWorld(), ["A1", "A2", "A3", "A4"] * 3)
    assert translating_cursor(frames, acts) == 9          # the rigid mover, NOT the growing colour-1 trail


def test_learn_basis_trailaware_recovers_cursor_and_vecs():
    frames, acts = _stream(TrailWorld(), ["A1", "A2", "A3", "A4"] * 3)
    cursor, vecs = learn_basis_trailaware(frames, acts)
    assert cursor == 9 and set(vecs) >= {"A1", "A2", "A3", "A4"}
    assert vecs["A1"][0] < 0 and vecs["A2"][0] > 0        # up / down axis-snapped


class TwoMover:
    """Two independent constant-size movers of DIFFERENT colours (9 and 10) -- sc25's shape. The detector should
    lock ONE of them as the cursor (single-mover control), where learn_basis is ambiguous."""
    def __init__(self):
        self.a = [5, 5]; self.b = [15, 15]; self.mv = {"A1": (-1, 0), "A2": (1, 0), "A3": (0, -1), "A4": (0, 1)}
    def frame(self):
        g = np.zeros((20, 20), dtype=int); g[tuple(self.a)] = 9; g[tuple(self.b)] = 10; return g
    def step(self, act):
        d = self.mv.get(act, (0, 0))
        self.a = [min(19, max(0, self.a[0] + d[0])), min(19, max(0, self.a[1] + d[1]))]
        self.b = [min(19, max(0, self.b[0] - d[0])), min(19, max(0, self.b[1] - d[1]))]
        return self.frame()


def test_translating_cursor_picks_one_of_two_movers():
    frames, acts = _stream(TwoMover(), ["A1", "A2", "A3", "A4"] * 3)
    assert translating_cursor(frames, acts) in (9, 10)    # locks a mover instead of failing


def test_policy_routes_directional_on_trail_world_via_fallback():
    p = ReduxPolicy(game_id="g50t-x", blackboard=Blackboard(), warmup_cap=8)
    w = TrailWorld()
    grid = w.frame()
    for _ in range(14):
        p.observe(grid, [1, 2, 3, 4, 5])
        lbl, _ = p.choose()
        grid = w.step(lbl)
    assert p.family == DIRECTIONAL and p.cursor == 9      # no longer UNDRIVABLE


def _real_stream(gid, n=40):
    hits = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "recordings", "*", "%s-*.jsonl" % gid)))
    if not hits:
        return None, None
    recs = [json.loads(l)["data"] for l in open(hits[0]).read().splitlines()]
    frames = [np.asarray(np.array(r["frame"])[-1]) for r in recs][:n]
    acts = [r.get("action_input", {}).get("id", "?") for r in recs][:n]
    return frames, acts


def test_trailaware_unlocks_sc25_and_re86_real_recordings():
    # LAW-0 verified: these two really DO have a constant-size translating mover that the footprint detector missed.
    for gid in ("sc25", "re86"):
        frames, acts = _real_stream(gid)
        if frames is None:
            import pytest; pytest.skip("no %s recording" % gid)
        cursor, vecs = learn_basis_trailaware(frames, acts)
        assert cursor is not None and len(vecs) >= 1, gid   # now drivable (was UNDRIVABLE)
        assert cursor != 0, gid                             # a real mover, not the background


def test_trailaware_honestly_does_not_fake_g50t():
    # HONEST: g50t's colour-9 region is CONSUMED into the trail (it shrinks), not a rigid mover -- no cursor exists,
    # and the detector must NOT invent one. g50t/tr87/su15/sb26/lf52 need paint/toggle/select models, not this.
    frames, acts = _real_stream("g50t")
    if frames is None:
        import pytest; pytest.skip("no g50t recording")
    assert learn_basis_trailaware(frames, acts)[0] is None
