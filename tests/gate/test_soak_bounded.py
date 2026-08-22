"""SOAK GATE: bounded growth under sustained drive.

320 steps through the REAL loop's EGO result path (record_result is where every
EGO block lives), plus direct module soaks where the full cycle() would only
pay this box's antivirus I/O tax without adding coverage:

  * no exception storm: the loop's swallow counters after 320 steps must be
    a tiny fraction of the step count (a broken guarded block swallows every
    step);
  * episode-boundary books: starvation/swallow settle <= 1 record per
    socket/block, and the starvation decision over the loop's OWN counters
    matches the stream exactly (the soak drive starves the bank socket by
    construction -- no commits ever happen -- proving the pipe flows);
  * ConditionalMiner: history keys and per-key buffers stay <= their caps
    under 240 mixed feeds;
  * MDL mint: the surprise seen-map stays <= seen_cap under a stream of
    distinct transitions, and every consider() lands one ledger line;
  * fabric streams: append cost is one record -- file size grows linearly
    (equal increments per equal batch), seq stays monotonic +1.
"""
from __future__ import annotations

import os
import random
import sys
import types
from contextlib import redirect_stdout

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.effects import ConditionalMiner, Gamma  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402
from engines.egocentric.starvation import StarvationBook  # noqa: E402
from engines.egocentric.swallow import BLOCKS, SwallowBook, swallow_note  # noqa: E402

N_STEPS = 320
GAME_ID = "soak_gate_g1"


@pytest.fixture(scope="module")
def soaked_loop(tmp_path_factory):
    """320 record_result steps through the real loop, hermetic in a tmp cwd."""
    run_dir = tmp_path_factory.mktemp("soak_run")
    cwd = os.getcwd()
    os.chdir(run_dir)
    try:
        import io
        random.seed(4242)
        from cognitive_loop import CognitiveLoop
        from engines.cognition.cognitive_frame import CognitiveFrame
        loop = CognitiveLoop(data_root=str(run_dir))
        loop.start_game(GAME_ID, [1, 2, 3, 4, 5, 6], max_actions=1000)
        base = np.zeros((64, 64), dtype=int)
        base[10:13, 10:13] = 2                       # a static block (negatives food)
        prev = base.copy()
        prev[50, 30] = 7
        buf = io.StringIO()
        with redirect_stdout(buf):
            for k in range(N_STEPS):
                cur = base.copy()
                cur[50, 30 + (k % 2)] = 7            # an ever-moving world cell
                changed = not np.array_equal(prev, cur)
                loop._current_frame = CognitiveFrame()
                loop._last_action_info = {
                    "type": 6,
                    "x": 5 + (k * 3) % 50, "y": 5 + (k * 5) % 50,
                    "frame_changed": False, "score_delta": 0.0,
                    "level_changed": False,
                    "consecutive_no_change": 0, "consecutive_same_action": 0,
                }
                loop.record_result(post_frame=cur, frame_changed=changed,
                                   score_delta=0.0, level_changed=False)
                prev = cur
            counters = dict(getattr(loop, "_plan_gate", None) or {})
            counters.update(getattr(loop, "_w4c_counters", None) or {})
            swallow_counts = dict(getattr(loop, "_swallow_counts", None) or {})
            loop.end_game()
        yield {"loop": loop, "fabric": loop._ego_fabric, "counters": counters,
               "swallow_counts": swallow_counts, "out": buf.getvalue()}
    finally:
        os.chdir(cwd)


class TestNoExceptionStorm:

    def test_swallow_counters_are_a_tiny_fraction_of_steps(self, soaked_loop):
        total = sum(int(v) for v in soaked_loop["swallow_counts"].values())
        assert total * 20 < N_STEPS, (
            "the loop swallowed %d exceptions over %d steps (%r) -- a guarded "
            "EGO block is broken and starving silently"
            % (total, N_STEPS, soaked_loop["swallow_counts"]))

    def test_module_error_counters_stayed_silent(self, soaked_loop):
        loop = soaked_loop["loop"]
        for name in ("_goal_spine", "_role_binder", "_predictor_bank",
                     "_residual_router", "_mdl_mint", "_affect",
                     "_ego_frontier_book"):
            mod = getattr(loop, name, None)
            if mod is None:
                continue
            errs = int(getattr(mod, "errors", 0) or 0)
            assert errs * 20 < N_STEPS, (
                "%s.errors == %d after %d steps -- an error storm inside the "
                "containment" % (name, errs, N_STEPS))


class TestEpisodeBoundaryBooksBounded:

    def test_starvation_stream_matches_the_pure_decision(self, soaked_loop):
        fab = soaked_loop["fabric"]
        recs = [r for r in fab.query("personal", "starvation")
                if r.get("game") == GAME_ID]
        expected = {s["socket"]: s["code"]
                    for s in StarvationBook.starved(soaked_loop["counters"])}
        got = {}
        for r in recs:
            assert r["socket"] not in got, (
                "socket %r settled twice -- the <=1-per-episode rule broke"
                % (r["socket"],))
            got[r["socket"]] = r["code"]
        assert got == expected

    def test_the_soak_starves_the_bank_socket_by_construction(self, soaked_loop):
        """No commit ever happened, so 320 settles = 320 dry bank exercises:
        the starvation pipe must actually flow (not just stay empty)."""
        assert soaked_loop["counters"].get("bank_tried", 0) >= N_STEPS
        assert soaked_loop["counters"].get("bank_passed", 0) == 0
        recs = [r for r in soaked_loop["fabric"].query("personal", "starvation")
                if r.get("game") == GAME_ID]
        assert any(r["code"] == "BANK_NO_FAMILY" for r in recs), (
            "320 dry bank exercises settled NO BANK_NO_FAMILY record -- the "
            "starvation readout is dead")
        assert "[STARVE]" in soaked_loop["out"]

    def test_swallow_stream_matches_the_pure_decision(self, soaked_loop):
        fab = soaked_loop["fabric"]
        recs = fab.query("personal", "swallow")
        expected = {(s["block"], s["count"])
                    for s in SwallowBook.swallowed(soaked_loop["swallow_counts"])}
        assert {(r["block"], r["count"]) for r in recs} == expected
        assert len(recs) == len({r["block"] for r in recs}), (
            "a block settled twice -- the <=1-per-episode rule broke")

    def test_loop_internal_buffers_stay_bounded(self, soaked_loop):
        loop = soaked_loop["loop"]
        assert len(loop._frame_history) <= 15
        accrued = (len(getattr(loop, "_ego_frontier_effects", []))
                   + len(getattr(loop, "_ego_frontier_dead", [])))
        assert accrued <= N_STEPS, (
            "frontier accrual exceeded one observation per step")


class TestConditionalMinerBounded:

    def test_history_keys_and_buffers_respect_their_caps(self):
        miner = ConditionalMiner(per_key=4, max_keys=6)
        rng = np.arange(64).reshape(8, 8)
        for k in range(240):
            action = k % 12                          # twice as many keys as fit
            pre = (rng + k) % 7
            post = pre.copy()
            post[k % 8, (k * 3) % 8] = (k + 1) % 7
            miner.feed(pre, action, post)
            assert len(miner._history) <= 6, (
                "miner grew %d action keys past max_keys=6 at feed %d"
                % (len(miner._history), k))
            assert all(len(h) <= 4 for h in miner._history.values()), (
                "a per-key buffer grew past per_key=4 at feed %d" % k)
        assert miner.errors == 0


class TestMintSeenMapBounded:

    def test_seen_map_respects_seen_cap_and_every_call_is_ledgered(self, tmp_path):
        fab = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        mint = MDLMint(Gamma(fab), seen_cap=24)
        n = 40
        for k in range(n):
            before = np.zeros((12, 12), dtype=int)
            before[0, 0] = 1
            after = before.copy()
            after[0, 0] = 2
            after[1 + k % 10, 1 + (k // 10) % 10] = 3   # a distinct transition each time
            mint.consider(before, 6, after, "soak_m", 1)
            assert len(mint._seen) <= 24, (
                "the surprise seen-map grew to %d past seen_cap=24 at call %d"
                % (len(mint._seen), k))
        verdicts = fab.query("collective", "mint_verdicts")
        assert len(verdicts) == n, (
            "%d consider() calls left %d ledger lines -- nothing silent"
            % (n, len(verdicts)))
        assert mint.errors == 0


class TestSwallowNoteBounded:

    def test_unknown_blocks_collapse_to_other_and_the_map_stays_enum_sized(self):
        host = types.SimpleNamespace()
        for k in range(500):
            swallow_note(host, "block_%d" % k)       # hostile: 500 distinct names
            swallow_note(host, BLOCKS[k % len(BLOCKS)])
        counts = host._swallow_counts
        assert set(counts) <= set(BLOCKS), (
            "swallow counters leaked non-enum keys: %r" % (sorted(counts),))
        assert len(counts) <= len(BLOCKS)
        assert counts["OTHER"] >= 500


class TestFabricGrowthLinear:

    def test_stream_bytes_grow_linearly_and_seq_monotonic(self, tmp_path):
        fab = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        path = os.path.join(str(tmp_path / "f"), "collective", "soak_topic.jsonl")
        sizes = [0]
        seqs = []
        for k in range(60):
            rec = fab.append("collective", "soak_topic",
                             {"payload": "x" * 40, "k": k})
            seqs.append(int(rec["seq"]))
            if (k + 1) % 20 == 0:
                sizes.append(os.path.getsize(path))
        assert seqs == list(range(1, 61)), (
            "seq is not monotonic +1 over a pure append run")
        d1 = sizes[1] - sizes[0]
        d2 = sizes[2] - sizes[1]
        d3 = sizes[3] - sizes[2]
        assert d1 > 0
        for later in (d2, d3):
            assert later <= 1.5 * d1, (
                "stream growth accelerated (batch deltas %r) -- appends are "
                "rewriting history, not appending" % ([d1, d2, d3],))
