"""SYSTEM DETERMINISM GATE: the same synthetic episode, driven twice from an
identical initial state (seeded RNG), must leave BYTE-IDENTICAL fabric writes.

The whole EGO substrate claims determinism (no wall-clock, no RNG in the
modules; the loop's only RNG is the seeded `random` explorer). This suite runs
one full episode -- real CognitiveLoop cycles, record_result, the shipped
episode-end recorder blocks, end_game -- twice in two fresh roots and
byte-compares every JSONL stream under ego_fabric/, plus the captured
narration. Any diverging byte is a FINDING: the first differing file and line
pair is named in the assertion message.

No exclusion list is applied: as of this writing NO wall-clock field exists in
any fabric record (fabric.append adds only "seq"). If one is ever added, this
test will name it.
"""
from __future__ import annotations

import io
import os
import random
import sys
import textwrap
import types
from contextlib import redirect_stdout

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

N_STEPS = 18
LEVEL_UP_STEP = 17
SEED = 777
GAME_ID = "det_gate_g1"


class SynthEnv:
    """Same toy world as the E2E gate: deterministic 2-cell click transform +
    an independent mover advancing every even step."""

    def __init__(self):
        self.board = np.zeros((64, 64), dtype=int)
        self.step = 0
        self.mover = [40, 5]
        self.board[40, 5] = 7

    def apply(self, action, data):
        pre = self.board.copy()
        if self.step % 2 == 0:
            r, c = self.mover
            self.board[r, c] = 0
            c2 = (c + 1) % 60
            self.mover = [r, c2]
            self.board[r, c2] = 7
        if action == 6 and data:
            x, y = int(data["x"]), int(data["y"])
            if (0 <= y < 64 and 0 <= x < 63
                    and self.board[y, x] == 0 and self.board[y, x + 1] == 0):
                self.board[y, x] = 5
                self.board[y, x + 1] = 5
        self.step += 1
        changed = bool((self.board != pre).any())
        return self.board.copy(), changed


def _src(f):
    return open(os.path.join(REPO, f), encoding="utf-8", errors="replace").read()


def _run_episode_end(loop, game_id, current_levels, ep_moves):
    src = _src("cognitive_game_player.py")
    start = src.index("3d-ii (EGO-FRONTIER): harvest the episode's exploration")
    start = src.rindex("\n", 0, start) + 1
    end = src.index("# End game and get replay", start)
    end = src.rindex("\n", 0, end)
    block = textwrap.dedent(src[start:end])

    class _GS:
        GAME_OVER = object()
        WIN = object()

    ns = {"loop": loop, "game_id": game_id, "current_levels": current_levels,
          "prev_levels": current_levels, "_ep_moves": dict(ep_moves),
          "last_obs": None, "GameState": _GS}
    exec(compile(block, "<episode-end-recorder>", "exec"), ns)  # noqa: S102 -- executes the extracted shipped block under test


def run_episode(run_root):
    """One full episode in `run_root`; returns (stream bytes by relpath, out)."""
    cwd = os.getcwd()
    os.chdir(run_root)
    try:
        random.seed(SEED)
        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop()
        loop.start_game(GAME_ID, [1, 2, 3, 4, 5, 6], max_actions=200)
        env = SynthEnv()
        obs = types.SimpleNamespace(levels_completed=0)
        frame = env.board.copy()
        ep_moves = {}
        buf = io.StringIO()
        with redirect_stdout(buf):
            for i in range(N_STEPS):
                action, data, _cf = loop.cycle(frame, obs)
                if i % 6 == 2:
                    action, data = 1 + (i // 6) % 5, None
                    loop._last_action_info = {
                        "type": action, "x": None, "y": None,
                        "frame_changed": False, "score_delta": 0.0,
                        "level_changed": False,
                        "consecutive_no_change": loop._consecutive_no_change,
                        "consecutive_same_action": 0,
                    }
                post, changed = env.apply(action, data)
                level_changed = (i == LEVEL_UP_STEP)
                if level_changed:
                    obs.levels_completed = 1
                if action in (1, 2, 3, 4, 5):
                    prev = ep_moves.get(str(action), (0, 0))
                    ep_moves[str(action)] = (prev[0] + (1 if changed else 0),
                                             prev[1] + (0 if changed else 1))
                loop.record_result(post_frame=post, frame_changed=changed,
                                   score_delta=0.0, level_changed=level_changed,
                                   new_level=2 if level_changed else 0)
                frame = post
            _run_episode_end(loop, GAME_ID, current_levels=1, ep_moves=ep_moves)
            loop.end_game()
        streams = {}
        for root, _dirs, files in os.walk("ego_fabric"):
            for f in sorted(files):
                p = os.path.join(root, f)
                rel = os.path.relpath(p, "ego_fabric").replace(os.sep, "/")
                with open(p, "rb") as fh:
                    streams[rel] = fh.read()
        return streams, buf.getvalue()
    finally:
        os.chdir(cwd)


@pytest.fixture(scope="module")
def two_runs(tmp_path_factory):
    r1 = tmp_path_factory.mktemp("det_run1")
    r2 = tmp_path_factory.mktemp("det_run2")
    s1, out1 = run_episode(r1)
    s2, out2 = run_episode(r2)
    return {"s1": s1, "s2": s2, "out1": out1, "out2": out2}


def _first_diff(a: bytes, b: bytes):
    la, lb = a.split(b"\n"), b.split(b"\n")
    for i, (x, y) in enumerate(zip(la, lb, strict=False)):
        if x != y:
            return i + 1, x[:300], y[:300]
    return (min(len(la), len(lb)) + 1,
            la[len(lb):len(lb) + 1], lb[len(la):len(la) + 1])


class TestIdenticalFabricWrites:

    def test_same_stream_files_exist(self, two_runs):
        k1, k2 = set(two_runs["s1"]), set(two_runs["s2"])
        assert k1 == k2, (
            "the two runs wrote different stream sets -- only in run1: %r, "
            "only in run2: %r (FINDING: nondeterministic stream creation)"
            % (sorted(k1 - k2), sorted(k2 - k1)))

    def test_every_stream_is_byte_identical(self, two_runs):
        s1, s2 = two_runs["s1"], two_runs["s2"]
        for rel in sorted(s1):
            if s1[rel] == s2.get(rel):
                continue
            line, x, y = _first_diff(s1[rel], s2[rel])
            raise AssertionError(
                "FINDING -- nondeterministic fabric write: stream %r differs "
                "between two identically-seeded runs, first at line %d:\n"
                "  run1: %r\n  run2: %r" % (rel, line, x, y))

    def test_narration_is_identical(self, two_runs):
        o1, o2 = two_runs["out1"], two_runs["out2"]
        if o1 != o2:
            for i, (a, b) in enumerate(zip(o1.splitlines(), o2.splitlines(),
                                           strict=False)):
                if a != b:
                    raise AssertionError(
                        "FINDING -- nondeterministic narration at line %d:\n"
                        "  run1: %r\n  run2: %r" % (i + 1, a, b))
            raise AssertionError(
                "FINDING -- narration lengths differ: %d vs %d lines"
                % (len(o1.splitlines()), len(o2.splitlines())))


class TestTheComparisonIsNotVacuous:

    def test_the_episode_actually_wrote_the_books(self, two_runs):
        s1 = two_runs["s1"]
        for needle in ("collective/atoms.jsonl", "collective/settlements.jsonl",
                       "collective/mint_verdicts.jsonl",
                       "collective/frontier_harvest.jsonl"):
            assert needle in s1 and s1[needle].strip(), (
                "stream %r missing/empty -- the determinism comparison would "
                "be vacuous" % (needle,))
        assert any(k.endswith("ideas.jsonl") for k in s1), (
            "no ideas stream -- the level-up mint never happened")

    def test_no_wall_clock_shaped_fields_in_any_record(self, two_runs):
        import json
        suspicious = ("time", "timestamp", "ts", "wall", "date", "now")
        for rel, blob in two_runs["s1"].items():
            for raw in blob.splitlines():
                if not raw.strip():
                    continue
                rec = json.loads(raw)
                bad = [k for k in rec
                       if any(s == k.lower() or k.lower().endswith("_" + s)
                              for s in suspicious)]
                assert not bad, (
                    "stream %r record carries wall-clock-shaped field(s) %r "
                    "(FINDING: name it and exclude it explicitly)" % (rel, bad))
