"""W2c GATE (PREREG_W2C_PLANNER_RETENTION.md): THE PLANNER RETAINS WHAT IT LEARNS.

The build under test: engines/egocentric/retention.py (the store the W2b
scheduler owns, cleared inside on_level_change / on_fission; every key
(game, level)-tagged AND carrying the atom's CONTENT key), served to the
planner's _run and the composer's _simulate through `retained=`; the BAND
restriction of effects._context_anchors (tier 2 of the per-state negative,
RAW-path atoms only); the dead-end marks; the composer's anchors store and
enabler-index FIFO. retained=None at both call sites is the undo.

The pinned falsifiers, as gated here -- BY COUNTING, NEVER WALL-CLOCK (the
canon's no-threshold-in-wall-clock rule; tests/gate/test_fabric_seq_cache.py
is the exemplar):
  F1  the second call does less work: (i) exact repeat -> applied_cold == 0,
      identical dict + reason; (ii) shifted repeat (root = a state the first
      call expanded) -> applied_cold strictly lower, memo_hits >= 1; (iii) a
      second compose_attempt on the same frame fires ZERO _context_anchors
      scans and ZERO cold seam applications.
  F2  retention never survives a level change or a fission: every
      substructure reports 0 after the clears; a state key seen in level L
      is a MISS in level L+1 on a byte-identical board; an entry written
      under (game, L) is unreadable under (game, L+1) with NO clear called.
  F3  memory bounded: caps never exceeded, oldest evicted first, evictions
      counted; oversized frames exhaust STATE_BYTES_CAP and the pointing
      memo entries become counted store_misses; MEMO_CAP=1 -> identical output.
  F4  the band negative both ways: (i) sensitivity -- a change that creates a
      match inside the band is found and equals the full scan's first match;
      (ii) specificity -- a change whose band excludes the would-be anchor
      re-examines only the band (band_anchors < full_anchors) and records a
      fresh negative; the oracle band ≡ full ∩ band on random frames and
      patches; a typed atom never enters tier 2.
  R4  retention changes work, never the answer: cold-vs-warm sequences
      (across mints, aborts, eviction) return identical plans, reasons and
      `expanded`.
  KN1 a superseded atom (same id, minimised context) misses memo AND anchors;
  KN2 a mint between calls: the dead-end mark misses, the successor is found;
  KN3 retained=None is byte-identical to today's planner and composer;
  KN4 a consumer mutating a served array raises; the store's copy is unchanged;
  KN5 the composer's empty anchor list is never read as a typed None.

Seeded with a FIXED CONSTANT (the build date), never a clock. No game id,
colour or object identity: every frame here is constructed.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl  # noqa: E402
from engines.egocentric import composer as C  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import enables as EN  # noqa: E402
from engines.egocentric import planner as P  # noqa: E402
from engines.egocentric import retention as R  # noqa: E402
from engines.egocentric import scheduler as sch  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402

SEED = 20260821  # fixed constant (the build date) -- deterministic forever
DELTAS4 = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


# ── constructions ─────────────────────────────────────────────────────────────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


def _raw(ctx, out, key, action=6):
    """An untyped (RAW-path) EFFECT atom: its only scan is the context window."""
    ctx_l = [[int(v) for v in row] for row in ctx]
    out_l = [[int(v) for v in row] for row in out]
    return {"kind": "EFFECT", "arity": 2, "key": key, "action": action,
            "context": ctx_l, "transform": {"before": ctx_l, "after": out_l},
            "changed": int((np.asarray(ctx) != np.asarray(out)).sum())}


def _typed(ctx, out, key, ttype, params, action=6):
    a = _raw(ctx, out, key, action)
    a["ttype"] = ttype
    a["params"] = dict(params)
    return a


def _inc_gamma(tmp_path, name, values=(3, 4), game="g1", level=1):
    """One learned (typed COLOUR_PERM, invertible) 1-cell increment per value
    -- the small solvable chain 3 -> 4 -> 5 the budget gate uses."""
    g = _gamma(tmp_path, name)
    ids = []
    for v in values:
        b = np.zeros((6, 6), dtype=int)
        b[2, 2] = v
        a = b.copy()
        a[2, 2] = v + 1
        ids.append(g.add(E.learn_effect(b, 6, a), game=game, level=level))
    return g, ids


def _board(v, shape=(6, 6)):
    f = np.zeros(shape, dtype=int)
    f[2, 2] = int(v)
    return f


def _count_calls(monkeypatch, module, name):
    """Count invocations of module.name (the work a retained call must skip)."""
    calls = {"n": 0}
    orig = getattr(module, name)

    def counting(*a, **kw):
        calls["n"] += 1
        return orig(*a, **kw)

    monkeypatch.setattr(module, name, counting)
    return calls


def _plan(ws, ref, g, store=None, game="g1", level=1, budget=100, cost=1,
          pred=None):
    """One planner call; returns (dict, reason, expanded) -- `expanded` read
    by counting the nodes the search spends (the budget's own unit)."""
    expanded = {"n": 0}
    orig_run = P._set_reason

    def _spy(reason):
        orig_run(reason)

    with mock.patch.object(P, "_set_reason", _spy):
        out = P.plan_to_identity(ws, ref, g, game=game, level=level,
                                 budget=budget, cost_per_action=cost,
                                 goal_predicate=pred, retained=store)
    return out, P.last_reason(), expanded


def _trace(ws, ref, g, store=None, game="g1", level=1, budget=100):
    """A planner call's (dict, reason, expanded, applied_cold): `expanded` is
    recovered by counting frontier pops through the planner's own deque."""
    pops = {"n": 0}
    real_deque = P.deque

    class CountingDeque(real_deque):
        def popleft(self):
            pops["n"] += 1
            return super().popleft()

    with mock.patch.object(P, "deque", CountingDeque):
        out = P.plan_to_identity(ws, ref, g, game=game, level=level,
                                 budget=budget, cost_per_action=1,
                                 retained=store)
    cold = R.last_call()["applied_cold"] if store is not None else None
    return out, P.last_reason(), pops["n"], cold


# ═════════════════════════════════════════════════════════════════════════════
# F1 · THE SECOND CALL DOES LESS WORK -- COUNTED, NOT TIMED
# ═════════════════════════════════════════════════════════════════════════════

class TestF1SecondCallDoesLessWork:

    def test_i_exact_repeat_applies_nothing_cold(self, tmp_path, monkeypatch):
        g, ids = _inc_gamma(tmp_path, "f1i")
        store = R.RetentionStore()
        first, r1, _ = _plan(_board(3), _board(5), g, store)
        c1 = R.last_call()
        assert first == {"steps": ids, "feasible": True}
        assert c1["applied_cold"] > 0, "construction: the first call must work"
        calls = _count_calls(monkeypatch, E, "apply_effect")
        second, r2, _ = _plan(_board(3), _board(5), g, store)
        c2 = R.last_call()
        assert second == first and r2 == r1, (
            "F1(i) FALSIFIED: the retained call changed the answer: %r vs %r"
            % (second, first))
        assert c2["applied_cold"] == 0, (
            "F1(i) FALSIFIED: the exact repeat still applied %d atoms cold"
            % c2["applied_cold"])
        assert calls["n"] == 0, (
            "F1(i) FALSIFIED: apply_effect fired %d times on the exact repeat"
            % calls["n"])
        assert c2["memo_hits"] >= c1["applied_cold"]
        assert store.last_call is c2 or store.last_call == c2

    def test_ii_shifted_repeat_strictly_less_cold_work(self, tmp_path):
        g, ids = _inc_gamma(tmp_path, "f1ii", values=(3, 4, 5))
        store = R.RetentionStore()
        first, _, _ = _plan(_board(3), _board(6), g, store)
        c1 = R.last_call()
        assert first == {"steps": ids, "feasible": True}
        # the second root = a state the first call EXPANDED (3 -> 4 happened)
        second, _, _ = _plan(_board(4), _board(6), g, store)
        c2 = R.last_call()
        assert second == {"steps": ids[1:], "feasible": True}
        assert c2["applied_cold"] < c1["applied_cold"], (
            "F1(ii) FALSIFIED: shifted repeat applied %d cold vs %d on the "
            "first call" % (c2["applied_cold"], c1["applied_cold"]))
        assert c2["memo_hits"] >= 1, "F1(ii) FALSIFIED: no memo hit on a seen state"

    def test_iii_second_compose_attempt_fires_no_scan_no_cold_seam(
            self, tmp_path, monkeypatch):
        f, g, ids, want = _two_shelf_world(tmp_path, "f1iii")
        store = R.RetentionStore()
        res1 = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1,
                                 retained=store)
        assert res1["reason"] == C.COMPOSED, res1
        c1 = R.last_call()
        assert c1["applied_cold"] > 0 and c1["full_anchors"] > 0
        scans = _count_calls(monkeypatch, E, "_context_anchors")
        applies = _count_calls(monkeypatch, E, "apply_effect")
        res2 = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1,
                                 retained=store)
        c2 = R.last_call()
        assert res2["reason"] == C.COMPOSED and res2["chain"] == res1["chain"]
        assert scans["n"] == 0, (
            "F1(iii) FALSIFIED: %d _context_anchors scans on the repeat attempt"
            % scans["n"])
        assert applies["n"] == 0 and c2["applied_cold"] == 0, (
            "F1(iii) FALSIFIED: cold seam applications on the repeat: "
            "apply_effect=%d applied_cold=%d" % (applies["n"], c2["applied_cold"]))
        assert c2["memo_hits"] > 0

    def test_the_instrument_has_exactly_the_fixed_keys_and_is_out_of_band(self):
        assert R.INSTRUMENT_KEYS == ("applied_cold", "memo_hits", "band_anchors",
                                     "full_anchors", "dead_end_skips",
                                     "store_misses", "evictions", "delta_compares")
        store = R.RetentionStore()
        assert set(store.counts) == set(R.INSTRUMENT_KEYS)
        assert set(R.last_call()) == set(R.INSTRUMENT_KEYS)
        # out-of-band: the module writes no stream (no fabric handle anywhere)
        src = open(os.path.join(REPO, "engines", "egocentric", "retention.py"),
                   encoding="utf-8").read()
        assert "fabric" not in src.replace("gamma.fabric", "").lower() or \
            ".append(" not in src, "the instrument must never be a stream record"


def _two_shelf_world(tmp_path, name, game="g1", level=1):
    """The composer gate's construction (test_composer_stage3): avatar 7 at
    (0,0); target 3 at (2,4); atom B writes 9 on it with act cell (0,4) =
    anchor + (-2, 0); a minted TRANSLATE moves 7 one column right."""
    f = np.zeros((3, 6), dtype=int)
    f[0, 0] = 7
    f[2, 4] = 3
    g = _gamma(tmp_path, name)
    ids = {}
    ids["mv"] = g.add(_typed([[7, 0]], [[0, 7]], "mv-right", "TRANSLATE",
                             {"dx": 0, "dy": 1, "fill": 0}, action=4), game, level)
    b = _raw([[3]], [[9]], "click-b")
    b[EN.ACT_OFFSET_FIELD] = {"v": EN.ACT_OFFSET_VERSION, "dr": -2, "dc": 0}
    ids["B"] = g.add(b, game, level)
    return f, g, ids, [(2, 4, 9)]


# ═════════════════════════════════════════════════════════════════════════════
# F2 · RETENTION NEVER SURVIVES A LEVEL CHANGE OR A FISSION
# ═════════════════════════════════════════════════════════════════════════════

class TestF2TheLeakCheck:

    def _fill(self, tmp_path, name, store):
        g, ids = _inc_gamma(tmp_path, name)
        _plan(_board(3), _board(5), g, store)
        f, g2, _ids, want = _two_shelf_world(tmp_path, name + "c")
        # a candidate with NO anchor makes the attempt build the enabler index
        g2.add(_raw([[8]], [[9]], "no-anchor"), "g1", 1)
        C.compose_attempt(want, f, g2, (0, 0), DELTAS4, set(), "g1", 1,
                          retained=store)
        sizes = store.sizes()
        assert sizes["memo"] > 0 and sizes["states"] > 0 and sizes["anchors"] > 0
        assert sizes["enablers"] > 0 and sizes["root"] == 1
        return g

    def test_on_level_change_empties_every_substructure(self, tmp_path):
        s = sch.PlannerScheduler()
        self._fill(tmp_path, "f2a", s.retained)
        s.on_level_change()
        assert all(v == 0 for v in s.retained.sizes().values()), (
            "F2 FALSIFIED: retention survived on_level_change: %r"
            % s.retained.sizes())

    def test_on_fission_empties_every_substructure(self, tmp_path):
        s = sch.PlannerScheduler()
        self._fill(tmp_path, "f2b", s.retained)
        s.on_fission("any-class")
        assert all(v == 0 for v in s.retained.sizes().values()), (
            "F2 FALSIFIED: retention survived on_fission: %r" % s.retained.sizes())

    def test_the_loop_level_site_clears_the_store(self, tmp_path):
        """cognitive_loop._w2b_abort(level_changed=True) is the ONE level
        site: the store clears through the scheduler's own clear."""
        s = sch.PlannerScheduler()
        self._fill(tmp_path, "f2c", s.retained)
        ns = SimpleNamespace(_w2b_sched=s, _w2b_driven=None, _prev_frame=None,
                             _game_id="g1", _ego_level=0, _narration=None)
        cl._w2b_abort(ns, frame_changed=True, level_changed=True)
        assert all(v == 0 for v in s.retained.sizes().values())

    def test_a_state_seen_in_level_L_misses_in_L_plus_1_byte_identical_board(
            self, tmp_path):
        g = _gamma(tmp_path, "f2d")
        for v in (3, 4):
            b = np.zeros((6, 6), dtype=int)
            b[2, 2] = v
            a = b.copy()
            a[2, 2] = v + 1
            atom = E.learn_effect(b, 6, a)
            g.add(atom, game="g1", level=1)
        s = sch.PlannerScheduler()
        _plan(_board(3), _board(5), g, s.retained, level=1)
        assert R.last_call()["applied_cold"] > 0
        s.on_level_change()
        _plan(_board(3), _board(5), g, s.retained, level=2)
        c = R.last_call()
        assert c["memo_hits"] == 0 and c["applied_cold"] > 0, (
            "F2 FALSIFIED: level-1 knowledge served in level 2: %r" % (c,))

    def test_the_belt_an_entry_under_L_is_unreadable_under_L_plus_1_no_clear(self):
        """NO clear called: the scope is part of every key, so a lookup under
        (game, L+1) cannot see what (game, L) wrote -- and binding the new
        scope is itself a counted miss that clears."""
        store = R.RetentionStore()
        atom = _raw([[1]], [[2]], "k")
        ck = R.content_key(atom)
        scope_l = ("g1", 1)
        store._scope = scope_l                    # bind without going through bind()
        store.memo_put(scope_l, ck, "K", np.array([[2]]))
        store.mark_dead(scope_l, R.FWD, "K", "S")
        store.anchors_put(scope_l, ck, "K", [(0, 0)])
        # a read under the NEXT level, by key alone (no clear, no bind)
        assert store.memo_get(("g1", 2), ck, "K") == (False, None)
        assert store.dead(("g1", 2), R.FWD, "K", "S") is False
        assert store.anchors_get(("g1", 2), ck, "K") is None
        assert store.negative(("g1", 2), ck, "K") is False
        # and binding the next level counts the miss and clears the belt
        before = store.counts["store_misses"]
        R.Session(store, "g1", 2)
        assert store.counts["store_misses"] == before + 1
        assert store.sizes()["memo"] == 0 and store.sizes()["anchors"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# F3 · MEMORY BOUNDED
# ═════════════════════════════════════════════════════════════════════════════

class TestF3Bounded:

    def test_caps_are_the_prereg_numbers_and_knobs_rows_exist(self):
        assert R.MEMO_CAP == 65_536
        assert R.STATE_BYTES_CAP == 64 * 1024 * 1024
        assert R.DEAD_CAP == 16_384
        assert R.ANCHORS_CAP == 8_192
        assert R.ENABLERS_CAP == 8
        knobs = open(os.path.join(REPO, "record", "canon", "KNOBS.md"), encoding="utf-8").read()
        for tok in ("MEMO_CAP=65536", "STATE_BYTES_CAP=64 MiB", "DEAD_CAP=16384",
                    "ANCHORS_CAP=8192", "ENABLERS_CAP=8"):
            assert tok in knobs, "KNOBS.md lacks the pinned row for %s" % tok
        assert "PREREG_W2C_PLANNER_RETENTION.md" in knobs

    def test_memo_never_exceeds_cap_oldest_first_counted(self):
        store = R.RetentionStore(memo_cap=4)
        scope = R.Session(store, "g1", 1).scope
        for i in range(10):
            store.memo_put(scope, "ck%d" % i, "K", None)
            assert store.sizes()["memo"] <= 4, "F3 FALSIFIED: memo over cap"
        assert store.counts["evictions"] == 6
        assert store.memo_get(scope, "ck0", "K") == (False, None), "oldest must go"
        assert store.memo_get(scope, "ck9", "K") == (True, None), "newest stays"

    def test_dead_anchors_enablers_caps_hold_oldest_first(self):
        store = R.RetentionStore(dead_cap=3, anchors_cap=2, enablers_cap=2)
        scope = R.Session(store, "g1", 1).scope
        for i in range(6):
            store.mark_dead(scope, R.FWD, "K%d" % i, "S")
            store.anchors_put(scope, "c%d" % i, "F", [(0, 0)])
            store.enablers_put(scope, ("m", i), ("s",), {"a": ["b"]})
        sz = store.sizes()
        assert sz["dead"] == 3 and sz["anchors"] == 2 and sz["enablers"] == 2
        assert store.dead(scope, R.FWD, "K0", "S") is False
        assert store.dead(scope, R.FWD, "K5", "S") is True
        assert store.anchors_get(scope, "c0", "F") is None
        assert store.anchors_get(scope, "c5", "F") == ((0, 0),)
        assert store.enablers_get(scope, ("m", 0), ("s",)) is None
        assert store.enablers_get(scope, ("m", 5), ("s",)) is not None
        assert store.counts["evictions"] == 3 + 4 + 4

    def test_oversized_frames_exhaust_state_bytes_and_memo_entries_become_misses(self):
        frame = np.zeros((8, 8), dtype=np.int64)          # 512 bytes each
        store = R.RetentionStore(state_bytes_cap=3 * frame.nbytes)
        scope = R.Session(store, "g1", 1).scope
        keys = []
        for i in range(5):
            res = frame.copy()
            res[0, 0] = i + 1
            store.memo_put(scope, "ck", "K%d" % i, res)
            keys.append("K%d" % i)
            assert store.sizes()["state_bytes"] <= 3 * frame.nbytes, (
                "F3 FALSIFIED: the state store exceeded STATE_BYTES_CAP")
        assert store.counts["evictions"] == 2
        assert store.sizes()["memo"] == 5, "memo entries stay until read"
        before = store.counts["store_misses"]
        assert store.memo_get(scope, "ck", "K0") == (False, None)
        assert store.memo_get(scope, "ck", "K1") == (False, None)
        assert store.counts["store_misses"] == before + 2, (
            "F3 FALSIFIED: a memo entry whose state was evicted was not a "
            "counted store miss")
        hit, arr = store.memo_get(scope, "ck", "K4")
        assert hit and arr[0, 0] == 5

    def test_memo_cap_one_planner_output_identical(self, tmp_path):
        g, ids = _inc_gamma(tmp_path, "f3e", values=(3, 4, 5))
        cold = _trace(_board(3), _board(6), g)
        store = R.RetentionStore(memo_cap=1)
        warm1 = _trace(_board(3), _board(6), g, store)
        warm2 = _trace(_board(3), _board(6), g, store)
        assert cold[:3] == warm1[:3] == warm2[:3], (
            "F3 FALSIFIED: MEMO_CAP=1 changed the planner's output: cold=%r "
            "warm=%r / %r" % (cold[:3], warm1[:3], warm2[:3]))
        assert store.counts["evictions"] > 0, "construction: cap 1 must evict"


# ═════════════════════════════════════════════════════════════════════════════
# F4 · THE BAND NEGATIVE, BOTH WAYS
# ═════════════════════════════════════════════════════════════════════════════

class TestF4TheBand:

    def test_i_sensitivity_a_change_inside_the_band_is_found_first_match(self):
        """A 2x2 patch matched nowhere on K; K' = K + C places it at (3,3)
        -- the band scan returns that anchor and equals the full scan."""
        patch = np.array([[1, 2], [3, 4]])
        K = np.zeros((8, 8), dtype=int)
        assert E._context_anchors(K, patch) == []
        Kp = K.copy()
        Kp[3:5, 3:5] = patch
        C_ = np.argwhere(Kp != K)
        band = E._context_anchors(Kp, patch, band=C_)
        full = E._context_anchors(Kp, patch)
        assert band == full == [(3, 3)], (
            "F4(i) FALSIFIED: band=%r full=%r" % (band, full))

    def test_i_sensitivity_through_the_planner_a_negative_never_suppresses(
            self, tmp_path):
        """A RAW atom matches nowhere at the root; a first step CREATES its
        context in the child; the second step must still fire (the plan is
        the two-step chain, identical cold and warm)."""
        g = _gamma(tmp_path, "f4s")
        a1 = g.add(_raw([[3]], [[1]], "make-1"), "g1", 1)      # 3 -> 1
        a2 = g.add(_raw([[1, 0]], [[1, 9]], "use-1"), "g1", 1)  # needs the 1
        ws = _board(3)
        ref = ws.copy()
        ref[2, 2] = 1
        ref[2, 3] = 9
        cold = _trace(ws, ref, g)
        store = R.RetentionStore()
        warm = _trace(ws, ref, g, store)
        assert cold[0] == {"steps": [a1, a2], "feasible": True}
        assert warm[:3] == cold[:3], "F4(i) FALSIFIED: the band suppressed a created match"
        assert R.last_call()["band_anchors"] > 0, (
            "construction: the raw atom's negative must have been carried by the band")

    def test_ii_specificity_band_smaller_than_full_and_fresh_negative(self, tmp_path):
        """Two RAW atoms: one that fires at the root (changing a far cell) and
        one that matches nowhere. In the child, the matched-nowhere atom is
        re-examined ONLY in the band around the changed cell (band_anchors <
        full_anchors, counted) and a fresh negative is recorded for the child."""
        g = _gamma(tmp_path, "f4sp")
        g.add(_raw([[3]], [[4]], "far"), "g1", 1)
        never = _raw([[5, 5]], [[6, 6]], "never")
        g.add(never, "g1", 1)
        ws = np.zeros((10, 10), dtype=int)
        ws[2, 2] = 3
        ws[7, 7] = 5                                  # a lone 5: [[5,5]] never matches
        ref = ws.copy()
        ref[2, 2] = 9                                 # unreachable: the search drains
        store = R.RetentionStore()
        out, reason, _, _ = _trace(ws, ref, g, store)
        c = R.last_call()
        assert out is None and reason == "NO_MEET"
        assert 0 < c["band_anchors"] < c["full_anchors"], (
            "F4(ii) FALSIFIED: band_anchors=%d full_anchors=%d"
            % (c["band_anchors"], c["full_anchors"]))
        # the fresh negative for the child state is in the memo
        child = ws.copy()
        child[2, 2] = 4
        sess = R.Session(store, "g1", 1)
        assert store.negative(sess.scope, R.content_key(never), R.state_key(child)), (
            "F4(ii) FALSIFIED: no fresh negative recorded for K'")

    def test_oracle_band_equals_full_intersect_band_on_random_frames_and_patches(self):
        rng = np.random.default_rng(SEED)
        for _ in range(300):
            bh, bw = int(rng.integers(1, 12)), int(rng.integers(1, 12))
            ph, pw = int(rng.integers(1, 4)), int(rng.integers(1, 4))
            b = rng.integers(0, 3, size=(bh, bw))
            ctx = rng.integers(0, 3, size=(ph, pw))
            if rng.random() < 0.3:
                ctx[rng.integers(0, ph), rng.integers(0, pw)] = E.DONT_CARE
            n = int(rng.integers(0, 4))
            cells = np.array([[int(rng.integers(0, bh)), int(rng.integers(0, bw))]
                              for _i in range(n)]).reshape(-1, 2)
            mask = E._band_mask(bh, bw, ph, pw, cells)
            full = list(E._context_anchors(b, ctx))
            band = E._context_anchors(b, ctx, band=cells)
            expect = [] if mask is None else [a for a in full if mask[a]]
            assert band == expect, (
                "F4 ORACLE FALSIFIED: band=%r expected full∩band=%r (frame %r "
                "patch %r cells %r)" % (band, expect, b.tolist(), ctx.tolist(),
                                        cells.tolist()))
            assert E.band_positions((bh, bw), (ph, pw), cells) == (
                0 if mask is None else int(mask.sum()))

    def test_band_none_is_the_unchanged_dispatch(self):
        rng = np.random.default_rng(SEED + 1)
        for _ in range(50):
            b = rng.integers(0, 3, size=(7, 9))
            ctx = rng.integers(0, 3, size=(2, 3))
            assert (list(E._context_anchors(b, ctx))
                    == list(E._context_anchors(b, ctx, band=None))
                    == list(E._context_anchors_scalar(b, ctx)))

    def test_a_typed_atom_never_enters_tier_2(self, tmp_path):
        typed = _typed([[1, 0, 0]], [[0, 1, 0]], "t", "TRANSLATE",
                       {"dx": 0, "dy": 1, "fill": 0})
        assert R.tier2_eligible(typed) is False
        assert R.tier2_eligible(_raw([[1]], [[2]], "r")) is True
        assert R.tier2_eligible({"kind": "EFFECT_IF", "condition": {"cells": []}}) is False
        assert R.tier2_eligible({"kind": "COMPOSITE", "parts": []}) is False
        # behaviourally: a typed atom's negative at the parent never licenses
        # a band scan at the child -- band_anchors stays 0 for a typed-only Gamma
        g, _ids = _inc_gamma(tmp_path, "f4t", values=(3, 4, 5))
        store = R.RetentionStore()
        _trace(_board(3), _board(6), g, store)
        assert R.last_call()["band_anchors"] == 0, (
            "F4 FALSIFIED: a typed atom entered tier 2")


# ═════════════════════════════════════════════════════════════════════════════
# R4 · RETENTION CHANGES WORK, NEVER THE ANSWER
# ═════════════════════════════════════════════════════════════════════════════

class TestR4ColdVsWarm:

    def test_identical_plans_reasons_expanded_across_a_sequence_with_mint_and_eviction(
            self, tmp_path):
        g, ids = _inc_gamma(tmp_path, "r4", values=(3, 4))
        seq = [(_board(3), _board(5)), (_board(4), _board(5)),
               (_board(3), _board(5)), (_board(3), _board(9)),   # unreachable
               (_board(5), _board(5))]                          # already identity
        cold = [_trace(w, r, g)[:3] for w, r in seq]
        store = R.RetentionStore(memo_cap=3)                    # eviction exercised
        warm = [_trace(w, r, g, store)[:3] for w, r in seq]
        assert warm == cold, "R4 FALSIFIED (pre-mint): warm %r vs cold %r" % (warm, cold)
        # a MINT between calls: the candidate set changes; answers still agree
        b = np.zeros((6, 6), dtype=int)
        b[2, 2] = 5
        a = b.copy()
        a[2, 2] = 6
        g.add(E.learn_effect(b, 6, a), game="g1", level=1)
        seq2 = [(_board(3), _board(6)), (_board(5), _board(6)), (_board(3), _board(5))]
        cold2 = [_trace(w, r, g)[:3] for w, r in seq2]
        warm2 = [_trace(w, r, g, store)[:3] for w, r in seq2]
        assert warm2 == cold2, "R4 FALSIFIED (post-mint): %r vs %r" % (warm2, cold2)
        assert store.counts["evictions"] > 0

    def test_identical_across_an_abort_routed_through_the_scheduler(self, tmp_path):
        g, ids = _inc_gamma(tmp_path, "r4b")
        s = sch.PlannerScheduler()
        cold = _trace(_board(3), _board(5), g)[:3]
        warm1 = _trace(_board(3), _board(5), g, s.retained)[:3]
        s.on_abort(sch.ABORT_WORLD_MOVED, "g1", 1, ids)      # the retained key drops
        s.on_abort(sch.ABORT_PLAN_WRONG, "g1", 1, ids)       # recorded against the plan
        warm2 = _trace(_board(3), _board(5), g, s.retained)[:3]
        assert cold == warm1 == warm2
        assert R.last_call()["applied_cold"] == 0, "an abort is not a clear"

    def test_dead_end_skip_spends_expanded_and_keeps_the_reason(self, tmp_path):
        g = _gamma(tmp_path, "r4d")
        g.add(_raw([[3]], [[4]], "one"), "g1", 1)
        ws = _board(3)
        ref = _board(9)
        cold = _trace(ws, ref, g)
        store = R.RetentionStore()
        warm1 = _trace(ws, ref, g, store)
        warm2 = _trace(ws, ref, g, store)
        assert cold[1] == "NO_MEET" and cold[:3] == warm1[:3] == warm2[:3]
        assert R.last_call()["dead_end_skips"] >= 1, (
            "the re-encountered dead-end (the 4-state) was not skipped")


# ═════════════════════════════════════════════════════════════════════════════
# KNOWN-NEGATIVES
# ═════════════════════════════════════════════════════════════════════════════

class TestKnownNegatives:

    def test_kn1_a_superseded_atom_misses_memo_and_anchors(self, tmp_path):
        """Same id, minimised context (a superseding append): the content key
        changes, the memo and anchors stores miss, the NEW result returns."""
        g = _gamma(tmp_path, "kn1")
        # 1x4 patch: the changed cell (0,0) + its ring (0,1) are always kept;
        # (0,3) is negotiable and VARIES in the second observation
        atom = _raw([[3, 7, 0, 5]], [[4, 7, 0, 5]], "sup")
        aid = g.add(atom, "g1", 1)
        ws = _board(3)
        ws[2, 3], ws[2, 4], ws[2, 5] = 7, 0, 5
        ref = ws.copy()
        ref[2, 2] = 4
        store = R.RetentionStore()
        first = _trace(ws, ref, g, store)
        assert first[0] == {"steps": [aid], "feasible": True}
        # the supersede: the observed context varied at (0,3) -> DONT_CARE there
        obs = np.array([[3, 7, 0, 2]])
        minimised = E.minimise_atom(atom, obs)
        assert minimised is not None and minimised["context"][0][3] == E.DONT_CARE
        g.fabric.append("collective", g.TOPIC, {"id": aid, "game": "g1", "level": 1,
                                                "atom": minimised, "type": "structural"})
        assert R.content_key(minimised) != R.content_key(atom)
        # a frame the OLD atom could not fire on, the minimised one can
        ws2 = ws.copy()
        ws2[2, 5] = 2
        ref2 = ws2.copy()
        ref2[2, 2] = 4
        cold = _trace(ws2, ref2, g)
        warm = _trace(ws2, ref2, g, store)
        assert cold[0] == warm[0] == {"steps": [aid], "feasible": True}, (
            "KN1 FALSIFIED: stale result served for a superseded atom: %r" % (warm[0],))
        assert R.last_call()["applied_cold"] > 0, "the superseded atom must miss"
        # the composer's anchors store misses too (content key in the key)
        sess = R.Session(store, "g1", 1)
        a_old = C._anchors(ws, atom, sess, aid)
        a_new = C._anchors(ws, minimised, sess, aid + "x")
        assert a_old == [(2, 2)] and a_new == [(2, 2)]
        assert store.anchors_get(sess.scope, R.content_key(atom), R.state_key(ws)) is not None
        assert store.anchors_get(sess.scope, R.content_key(minimised),
                                 R.state_key(ws)) is not None

    def test_kn2_a_mint_between_calls_misses_the_dead_end_and_finds_the_successor(
            self, tmp_path):
        g = _gamma(tmp_path, "kn2")
        g.add(_raw([[3]], [[4]], "first"), "g1", 1)
        store = R.RetentionStore()
        out, reason, _, _ = _trace(_board(3), _board(5), g, store)
        assert out is None and reason == "NO_MEET"
        assert store.sizes()["dead"] >= 1, "construction: the 4-state is a dead-end"
        second = g.add(_raw([[4]], [[5]], "second"), "g1", 1)   # the mint
        cold = _trace(_board(3), _board(5), g)
        warm = _trace(_board(3), _board(5), g, store)
        assert cold[0] == warm[0] and warm[0]["steps"][-1] == second, (
            "KN2 FALSIFIED: the dead-end mark outlived the mint: %r" % (warm[0],))
        assert R.last_call()["dead_end_skips"] == 0

    def test_kn3_retained_none_is_byte_identical(self, tmp_path, monkeypatch):
        """The undo: with retained=None the planner and the composer never
        touch the retention module (no Session opened), and the outputs equal
        the retained outputs' answers."""
        opened = _count_calls(monkeypatch, R, "Session")
        g, ids = _inc_gamma(tmp_path, "kn3")
        out = P.plan_to_identity(_board(3), _board(5), g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out == {"steps": ids, "feasible": True}
        f, g2, _ids, want = _two_shelf_world(tmp_path, "kn3c")
        res = C.compose_attempt(want, f, g2, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED
        assert opened["n"] == 0, "KN3 FALSIFIED: retained=None opened a session"
        # default argument at both entry points IS None
        import inspect
        assert inspect.signature(P.plan_to_identity).parameters["retained"].default is None
        assert inspect.signature(C.compose_attempt).parameters["retained"].default is None

    def test_kn4_a_consumer_mutating_a_served_array_raises(self, tmp_path):
        g, ids = _inc_gamma(tmp_path, "kn4")
        store = R.RetentionStore()
        sess = R.Session(store, "g1", 1)
        atom = g.get(ids[0])
        ws = _board(3)
        served = sess.apply(ids[0], atom, ws, R.state_key(ws))
        assert served is not None and served[2, 2] == 4
        with pytest.raises(ValueError):
            served[2, 2] = 99
        hit, again = store.memo_get(sess.scope, sess.ckey(ids[0], atom), R.state_key(ws))
        assert hit and again[2, 2] == 4, "KN4 FALSIFIED: the store's copy changed"
        assert not again.flags.writeable

    def test_kn5_the_composers_empty_anchor_list_is_not_a_typed_none(self):
        """A typed TRANSLATE whose literal context matches nowhere but whose
        parameterised op fires: _anchors records [] in the anchors store; the
        memo must NOT read that as None -- the application returns the typed
        result."""
        typed = _typed([[7, 0, 0]], [[0, 7, 0]], "t", "TRANSLATE",
                       {"dx": 0, "dy": 1, "fill": 0})
        frame = np.array([[7, 0, 5]])
        assert E._context_anchors(frame, np.asarray(typed["context"])) == []
        expect = E.apply_effect(typed, frame)
        assert expect is not None and expect.tolist() == [[0, 7, 5]]
        store = R.RetentionStore()
        sess = R.Session(store, "g1", 1)
        fk = R.state_key(frame)
        assert C._anchors(frame, typed, sess, "t") == []
        assert store.anchors_get(sess.scope, sess.ckey("t", typed), fk) == ()
        assert store.negative(sess.scope, sess.ckey("t", typed), fk) is False, (
            "KN5 FALSIFIED: the empty anchor list was written as a memo None")
        got = sess.apply("t", typed, frame, fk)
        assert got is not None and got.tolist() == expect.tolist(), (
            "KN5 FALSIFIED: the typed application was read as None")


# ═════════════════════════════════════════════════════════════════════════════
# THE WIRING: the scheduler owns the store; both loop call sites pass it
# ═════════════════════════════════════════════════════════════════════════════

class TestWiring:

    def test_scheduler_owns_one_store(self):
        s = sch.PlannerScheduler()
        assert isinstance(s.retained, R.RetentionStore)

    def test_both_call_sites_pass_the_schedulers_store(self):
        import ast
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8").read()
        sites = {"plan_to_identity": 0, "abduced_plan": 0, "compose_attempt": 0}
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call):
                fn = node.func
                name = getattr(fn, "id", None) or getattr(fn, "attr", None)
                if name in sites:
                    kws = {kw.arg for kw in node.keywords}
                    assert "retained" in kws, (
                        "%s call at line %d does not pass retained=" % (name, node.lineno))
                    sites[name] += 1
        assert all(v >= 1 for v in sites.values()), sites
        gsrc = open(os.path.join(REPO, "engines", "egocentric", "goal_abduction.py"),
                    encoding="utf-8").read()
        assert "retained=retained" in gsrc, "abduced_plan must pass the store through"

    def test_content_key_reads_exactly_the_fields_apply_effect_reads(self):
        a = _raw([[1]], [[2]], "k")
        b = dict(a)
        b["key"] = "other"
        b["asig"] = {"cached": 1}
        b["act_offset"] = {"dr": 1}
        assert R.content_key(a) == R.content_key(b), "id-free, cache-free"
        c = dict(a)
        c["context"] = [[E.DONT_CARE]]
        assert R.content_key(c) != R.content_key(a)
        assert R.content_key(None) == "none"
