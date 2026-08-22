"""LINK 3 GATE (LINK3_AUDIT.md) — the abduction hook and the grown vocabulary.

⭐ WHY. Measured, read-only, against every level-up frame this project has on disk:
`extract_predicates` returned **0 predicates on every record**, while the boards
visibly differed. Two defects, and the audit's ordering is binding — (a) is prior
to (b), because a perfect vocabulary shipped alone would still only ever see the
level-1 transitions the cognitive cycle happens to observe.

  (a) THE HOOK. `_goal_abd` had exactly ONE call site — inside the cognitive
      cycle. `_replay_salient_prefix` steps the environment directly and never
      enters that cycle, so a level-up REACHED BY REPLAY never reached the
      abduction bank. Every banked record is level 1 for that reason: level 1 is
      reached by exploration (banked), level 2 only by replay (not banked).
      SUCCESS SUPPRESSES THE EVIDENCE CHANNEL.
      PRE-COMMITTED FALSIFIER: after the hook, a replayed level-up must produce a
      `levelup_frames` record AT A LEVEL > 1. That count was 0 project-wide.

  (b) THE VOCABULARY, GROWN FROM THE MEASURED RESIDUAL — not designed from a
      description. The worse instrument's residual IS the specification:
        * colours APPEAR and never vanish   -> `colour_present`
        * the dominant colour flips while every colour's count moves
                                            -> `colour_majority`
        * no region is EVER uniform (0/5), regions hold 2..11 colours, and some
          region palettes SHRINK             -> `region_colour_count_atmost`
          (`region_uniform` is exactly the k=1 rung of this ladder)
        * a colour enters a region it was not in (local, not global, appearance)
                                            -> `region_contains_colour`
      The three original classes are KEPT — they are correct and merely never
      satisfied on this domain. This is an extension, not a replacement.
      PRE-COMMITTED FALSIFIER, failable in BOTH directions:
        1. > 0 predicates on the appearance/majority/palette-shrink shapes;
        2. STILL EXACTLY ZERO for `region_uniform` and `regions_equal` on those
           same boards — a vocabulary that starts firing the two classes shown
           unsatisfiable has REPLACED the edge rather than extended it;
        3. a class that fires on EVERY record is not evidence: the per-class fire
           rate is reported and asserted to be discriminating, not universal.

The fixtures here are 64x64 (the real board size) and reproduce the SHAPES measured
on the live records; `tools/link3_live_check.py` runs the same extractor against the
live `.runs/swarm/**/levelup_frames.jsonl` records read-only, which a hermetic test
must not depend on.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _laws():
    """The shared law bodies (tests/gate/_ast_laws.py). tests/gate is not a
    package, so it is loaded by path and cached in sys.modules for the
    session -- one body per law, one place to argue with it."""
    mod = sys.modules.get("_ouro_ast_laws")
    if mod is None:
        spec = importlib.util.spec_from_file_location(
            "_ouro_ast_laws",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ast_laws.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_ouro_ast_laws"] = mod
        spec.loader.exec_module(mod)
    return mod

from engines.egocentric import goal_abduction as GA  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402

PLAYER = os.path.join(REPO, "cognitive_game_player.py")
LOOP = os.path.join(REPO, "cognitive_loop.py")

H = W = 64          # the real board size on every live record


def _src(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


# ── FIXTURES DERIVED FROM THE REAL SHAPES ────────────────────────────────────────
# Every fixture is built from derived geometry (H, W and fractions of them), never
# from a memorized coordinate, and each reproduces one measured residual.

def _mottled(background, scattered):
    """A 64x64 board shaped like the live ones: ONE dominant background colour
    (measured: ar25 colour 9 held 3663/4096 cells, cd82 colour 5 held 3259)
    with the rest scattered densely enough that no region is ever uniform and no
    two quadrants are ever equal."""
    a = np.full((H, W), background, dtype=int)
    n = len(scattered)
    for r in range(H):
        for c in range(W):
            if (r * 5 + c * 3 + (r * c) % 7) % 9 == 0:
                a[r, c] = scattered[(r + c + (r * c) % 3) % n]
    return a


def appearance_pair():
    """cd82-shaped, ISOLATING APPEARANCE: a colour ABSENT in pre is PRESENT in
    post (measured: colour 12 went 0 -> 64 cells), nothing vanishes, and the
    dominant colour does NOT change (measured: 5 held the plurality either
    side)."""
    pre = _mottled(5, [0, 2, 3, 4, 15])
    post = pre.copy()
    blk = H // 8
    post[blk:blk * 2, blk:blk * 2] = 12          # exactly 64 cells, as measured
    return pre, post


def majority_flip_pair():
    """lp85-shaped, ISOLATING COUNT CHANGE: no colour appears and none vanishes,
    but the DOMINANT colour flips (measured: 4 held 1978 cells and 3 held 1606
    in pre; in post 3 holds 2319 and 4 holds 1445)."""
    pre = _mottled(4, [3, 1, 2, 5])
    post = pre.copy()
    rows = np.arange(H)[:, None]
    cols = np.arange(W)[None, :]
    post[(pre == 4) & (((rows + cols) % 3) != 0)] = 3     # 3 takes the plurality
    return pre, post


def palette_shrink_pair():
    """ar25-shaped, ISOLATING LOCAL STRUCTURE: one quadrant's DISTINCT-COLOUR
    COUNT drops (measured: q2 went 4 -> 3) while the board stays far from
    uniform and the colours survive elsewhere on the board."""
    pre = _mottled(9, [5, 10, 11, 4, 0])
    post = pre.copy()
    h2, w2 = H // 2, W // 2
    q2 = post[H - h2:, :w2].copy()
    q2[q2 == 11] = 10                                     # two colours leave q2
    q2[q2 == 4] = 10
    post[H - h2:, :w2] = q2
    return pre, post


ALL_PAIRS = {"appearance": appearance_pair(),
             "majority_flip": majority_flip_pair(),
             "palette_shrink": palette_shrink_pair()}


class TestTheFixturesReproduceTheMeasuredResidual:
    """The fixtures are only evidence if they carry the live boards' properties."""

    @pytest.mark.parametrize("name", sorted(ALL_PAIRS))
    def test_no_region_is_uniform_and_no_quadrants_are_equal(self, name):
        pre, post = ALL_PAIRS[name]
        for frame in (pre, post):
            for rname in ("full", "q0", "q1", "q2", "q3"):
                assert not GA.satisfies(
                    {"kind": "region_uniform", "region": rname}, frame), (
                    "fixture %s is not shaped like a live board: %s is uniform"
                    % (name, rname))
            for a, b in (("q0", "q1"), ("q0", "q2"), ("q0", "q3"),
                         ("q1", "q2"), ("q1", "q3"), ("q2", "q3")):
                assert not GA.satisfies(
                    {"kind": "regions_equal", "a": a, "b": b}, frame)

    @pytest.mark.parametrize("name", sorted(ALL_PAIRS))
    def test_nothing_ever_vanishes(self, name):
        pre, post = ALL_PAIRS[name]
        vanished = set(np.unique(pre).tolist()) - set(np.unique(post).tolist())
        assert vanished == set(), (
            "the live corpus has NEVER lost a colour at a level-up; fixture %s "
            "must not either" % name)

    @pytest.mark.parametrize("name", sorted(ALL_PAIRS))
    def test_the_boards_visibly_differ(self, name):
        pre, post = ALL_PAIRS[name]
        assert not bool((pre == post).all())


class TestTheVocabularyNowResolves:
    """FALSIFIER (b).1 — > 0 on the shapes the residual named."""

    def test_a_colour_that_appears_is_extracted(self):
        pre, post = appearance_pair()
        sigs = {GA.signature(p) for p in GA.extract_predicates(pre, post)}
        assert "colour_present:12" in sigs, (
            "a colour ABSENT in pre and PRESENT in post is the one thing this "
            "domain actually does at a level-up — it must extract")

    def test_a_flipped_dominant_colour_is_extracted(self):
        pre, post = majority_flip_pair()
        sigs = {GA.signature(p) for p in GA.extract_predicates(pre, post)}
        assert "colour_majority:3" in sigs, (
            "count change expressed RELATIVELY (which colour dominates), never "
            "as an absolute cell count — the mechanic, not the answer")
        assert "colour_majority:4" not in sigs, (
            "4 dominated in PRE — a predicate that already held is not the delta")

    def test_a_shrinking_region_palette_is_extracted(self):
        pre, post = palette_shrink_pair()
        sigs = {GA.signature(p) for p in GA.extract_predicates(pre, post)}
        assert any(s.startswith("region_colour_count_atmost:q2:") for s in sigs), (
            "region_uniform is the k=1 rung of a ladder the domain lives at "
            "k=2..11; the ladder must be walkable")

    def test_a_colour_entering_a_region_is_extracted(self):
        pre, post = appearance_pair()
        sigs = {GA.signature(p) for p in GA.extract_predicates(pre, post)}
        assert any(s.startswith("region_contains_colour:") and s.endswith(":12")
                   for s in sigs), (
            "LOCAL appearance — a colour entering a region — is invisible to the "
            "global class when the colour already exists elsewhere on the board")

    @pytest.mark.parametrize("name", sorted(ALL_PAIRS))
    def test_every_measured_shape_now_yields_something(self, name):
        pre, post = ALL_PAIRS[name]
        assert len(GA.extract_predicates(pre, post)) > 0, (
            "the whole finding was 0 predicates on boards that visibly differ; "
            "shape %s must no longer return 0" % name)


class TestTheOldClassesAreExtendedNotReplaced:
    """FALSIFIER (b).2 — the two classes shown UNSATISFIABLE on this domain must
    still yield exactly ZERO. A vocabulary that starts firing them has replaced
    the edge rather than extended it."""

    @pytest.mark.parametrize("name", sorted(ALL_PAIRS))
    def test_region_uniform_and_regions_equal_still_yield_zero(self, name):
        pre, post = ALL_PAIRS[name]
        kinds = [p.get("kind") for p in GA.extract_predicates(pre, post)]
        assert kinds.count("region_uniform") == 0, (
            "region_uniform was measured 0/5 on every live board; firing it on a "
            "live-shaped board means the class changed meaning")
        assert kinds.count("regions_equal") == 0

    def test_the_original_three_classes_still_behave_exactly_as_before(self):
        """The kept classes are correct — they are merely never satisfied HERE."""
        pre = np.zeros((8, 8), dtype=int)
        pre[2, 2] = 3
        pre[5, 6] = 3
        post = np.zeros((8, 8), dtype=int)
        post[1, 1] = 7
        sigs = {GA.signature(p) for p in GA.extract_predicates(pre, post)}
        assert "colour_count_zero:3" in sigs, "elimination must still extract"
        pre2 = np.zeros((8, 8), dtype=int)
        pre2[1, 1] = 4
        post2 = np.zeros((8, 8), dtype=int)
        post2[6, 6] = 5
        sigs2 = {GA.signature(p) for p in GA.extract_predicates(pre2, post2)}
        assert "region_uniform:q0" in sigs2
        assert "region_uniform:full" not in sigs2
        pre3 = np.zeros((8, 8), dtype=int)
        pre3[1, 1] = 4
        post3 = np.zeros((8, 8), dtype=int)
        post3[1, 1] = 4
        post3[1, 5] = 4
        sigs3 = {GA.signature(p) for p in GA.extract_predicates(pre3, post3)}
        assert "regions_equal:q0:q1" in sigs3


class TestNoClassFiresEverywhere:
    """FALSIFIER (b).3 — an instrument that fires on every record has not
    extended anything. The per-class fire rate is measured, not assumed."""

    def _rates(self):
        rates = {}
        for name, (pre, post) in sorted(ALL_PAIRS.items()):
            for k in {p.get("kind") for p in GA.extract_predicates(pre, post)}:
                rates.setdefault(k, set()).add(name)
        return rates

    def test_no_class_fires_on_every_shape(self):
        rates = self._rates()
        n = len(ALL_PAIRS)
        universal = sorted(k for k, s in rates.items() if len(s) == n)
        assert universal == [], (
            "%r fired on EVERY shape — a detector that always fires is a "
            "constant, not evidence. Fire map: %r"
            % (universal, {k: sorted(v) for k, v in rates.items()}))

    def test_each_grown_class_is_carried_by_the_residual_it_was_grown_from(self):
        """The fire map IS the claim: each new class answers ONE measured
        residual and stays silent on the other two."""
        rates = {k: sorted(v) for k, v in self._rates().items()}
        assert rates.get("colour_present") == ["appearance"], rates
        assert rates.get("colour_majority") == ["majority_flip"], rates
        assert rates.get("region_colour_count_atmost") == ["palette_shrink"], rates
        assert "region_contains_colour" in rates, (
            "the coarse LOCAL rung must exist — it is the one that sees a colour "
            "entering a region while the global class cannot. Fire map: %r" % rates)

    def test_an_unchanged_board_extracts_nothing_at_all(self):
        for _name, (pre, _post) in sorted(ALL_PAIRS.items()):
            assert GA.extract_predicates(pre, pre.copy()) == [], (
                "a predicate that already held is not the level-up's delta")


class TestTheDisciplineSurvives:
    """Determinism, signature(), MIN_CO, and the never-invent rule."""

    def test_extraction_is_deterministic(self):
        pre, post = appearance_pair()
        first = [GA.signature(p) for p in GA.extract_predicates(pre, post)]
        for _ in range(3):
            assert [GA.signature(p) for p in GA.extract_predicates(pre, post)] == first

    def test_signature_is_total_and_stable(self):
        assert GA.signature(None) == "unknown"
        assert GA.signature({"kind": "nonsense"}) == "unknown"
        assert GA.signature({"kind": "colour_present", "colour": 12}) == "colour_present:12"
        assert GA.signature({"kind": "colour_majority", "colour": 3}) == "colour_majority:3"
        assert GA.signature({"kind": "region_colour_count_atmost", "region": "q2",
                             "k": 3}) == "region_colour_count_atmost:q2:3"
        assert GA.signature({"kind": "region_contains_colour", "region": "q0",
                             "colour": 12}) == "region_contains_colour:q0:12"

    def test_every_extracted_predicate_round_trips_through_signature(self):
        for _name, (pre, post) in sorted(ALL_PAIRS.items()):
            for p in GA.extract_predicates(pre, post):
                assert GA.signature(p) != "unknown", (
                    "an extracted predicate with no signature cannot be banked: %r" % p)

    def test_satisfies_is_the_single_frame_stopping_test_for_every_class(self):
        """The planner's predicate mode tests `satisfies(pred, state)` on ONE
        frame — a delta-shaped predicate would be undecidable there."""
        pre, post = appearance_pair()
        for p in GA.extract_predicates(pre, post):
            assert GA.satisfies(p, post) is True, "%r must hold in post" % p
            assert GA.satisfies(p, pre) is False, "%r must not hold in pre" % p

    def test_garbage_never_raises_and_never_invents(self):
        assert GA.extract_predicates(None, None) == []
        assert GA.extract_predicates("nonsense", 7) == []
        assert GA.extract_predicates(np.zeros(3), np.zeros(3)) == []
        assert GA.satisfies({"kind": "colour_present"}, None) is False
        assert GA.satisfies({"kind": "colour_majority", "colour": "x"}, None) is False
        assert GA.satisfies({"kind": "region_colour_count_atmost"}, None) is False
        assert GA.satisfies({"kind": "region_contains_colour"}, None) is False

    def test_min_co_is_unchanged(self):
        assert GA.MIN_CO == 2


# ═════════════════════════════════════════════════════════════════════════════════
# PART (a) — THE HOOK
# ═════════════════════════════════════════════════════════════════════════════════

class _Obs:
    def __init__(self, frame, state="NOT_FINISHED", levels=0):
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


class _DB:
    def __init__(self, path):
        import sqlite3
        self._c = sqlite3.connect(path)
        self._c.row_factory = sqlite3.Row

    def execute_query(self, sql, params=()):
        cur = self._c.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        self._c.commit()
        return rows


class _RecordingLoop:
    """A stand-in loop that records exactly what crosses the seam."""

    def __init__(self):
        self.fed = []
        self.banked = []

    def _ego_feed(self, frame, action):
        self.fed.append((np.asarray(frame).copy(), action))

    def bank_replay_levelup(self, game, level, pre, post):
        self.banked.append((str(game), int(level),
                            np.asarray(pre).copy(), np.asarray(post).copy()))
        return 0


def _frame(k):
    return np.full((8, 8), k, dtype=np.uint8)


def _player(tmp_path):
    from cognitive_game_player import CognitiveGamePlayer

    class _GP:
        pass
    gp = _GP()
    gp.db = _DB(str(tmp_path / "box.db"))
    return CognitiveGamePlayer(gp, verbose=False)


def _banked_prefix(p, game, level, frames):
    """Bank a prefix whose expected post-frames are exactly `frames`."""
    from cognitive_game_player import CognitiveGamePlayer
    steps = [{"action": 6, "data": {"x": i, "y": i},
              "post_hash": CognitiveGamePlayer._compute_frame_hash(_Obs(f)),
              "changed": True}
             for i, f in enumerate(frames)]
    assert p._bank_salient_prefix(game, level, steps) is True
    return p._load_salient_prefix(game, level)


class TestTheReplayHook:
    """PRE-COMMITTED FALSIFIER (a): a replayed level-up must produce a
    `levelup_frames` record AT A LEVEL > 1. Project-wide that count was 0."""

    def _replay_crossing_level_2(self, tmp_path, loop):
        """A replay that starts at levels_completed=1 and crosses into 2 on the
        SECOND step — the exact bootstrap trap: L2 is only ever reached by replay."""
        p = _player(tmp_path)
        frames = [_frame(1), _frame(2), _frame(3)]
        sal = _banked_prefix(p, "g1", 1, frames)
        env = _Env([_Obs(frames[0], levels=1),
                    _Obs(frames[1], levels=2),      # <-- the level boundary
                    _Obs(frames[2], levels=2)])
        taken, obs = p._replay_salient_prefix(env, "g1", 1, sal, loop,
                                              pre_obs=_Obs(_frame(0), levels=1))
        assert taken == 3, "the replay must run to completion (taken=%r)" % taken
        return p, frames

    def test_a_replayed_level_up_reaches_the_abduction_bank_above_level_1(
            self, tmp_path):
        """THE FALSIFIER. Not 'the function was called' — the RECORD must appear,
        in a real fabric, at a level greater than 1."""
        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop()
        loop._game_id = "g1"
        loop._ego_fabric = KnowledgeFabric(str(tmp_path / "fab"),
                                           agent_id="a", kin_key="v4")
        self._replay_crossing_level_2(tmp_path, loop)
        recs = loop._ego_fabric.query("personal", GA.FRAMES_TOPIC)
        assert len(recs) == 1, (
            "a replay that crossed a level boundary banked %d levelup_frames "
            "records — the abduction bank is not on the replay path" % len(recs))
        assert int(recs[0]["level"]) > 1, (
            "banked at level %r; the whole point is that level 2 is reached ONLY "
            "by replay and has never been banked" % recs[0]["level"])
        assert int(recs[0]["level"]) == 2

    def test_a_fresh_loop_with_no_fabric_yet_still_banks(self, tmp_path,
                                                         monkeypatch):
        """REACHABILITY, and this is the one that nearly shipped inert. A real
        episode builds a NEW CognitiveLoop per play_game and the fabric is lazily
        created inside the cognitive cycle — which the salient replay runs BEFORE.
        A hook that requires `_ego_fabric` to already exist is reachable and does
        nothing, every time, in production."""
        from cognitive_loop import CognitiveLoop
        monkeypatch.chdir(tmp_path)                  # the fabric root is relative
        loop = CognitiveLoop()                       # exactly as play_game builds it
        loop._game_id = "g1"
        loop._ego_agent_id = "agentA"
        assert getattr(loop, "_ego_fabric", None) is None, (
            "this test is only meaningful while the fresh loop has no fabric")
        self._replay_crossing_level_2(tmp_path, loop)
        recs = loop._ego_fabric.query("personal", GA.FRAMES_TOPIC)
        assert len(recs) == 1 and int(recs[0]["level"]) == 2, (
            "a replayed level-up on a FRESH loop banked nothing — the hook is "
            "wired but inert on the only path production actually takes")
        assert loop._goal_book is not None
        assert loop._goal_book.fabric.agent_id == "agentA", (
            "the personal record must be filed under the real agent")

    def test_the_seam_carries_the_transition_frames_not_the_replay_edges(
            self, tmp_path):
        """CLAUSE 3 — the value crossing the boundary is ASSERTED. pre must be
        the frame BEFORE the crossing step and post the frame AFTER it; a hook
        that hands over the first/last frames of the whole replay is wrong."""
        loop = _RecordingLoop()
        _p, frames = self._replay_crossing_level_2(tmp_path, loop)
        assert len(loop.banked) == 1, (
            "exactly one level boundary was crossed; got %d bank calls"
            % len(loop.banked))
        game, level, pre, post = loop.banked[0]
        assert game == "g1"
        assert level == 2, "the banked level is the NEW levels_completed"
        assert np.array_equal(pre, frames[0]), (
            "pre must be the frame observed immediately BEFORE the crossing step")
        assert np.array_equal(post, frames[1]), (
            "post must be the frame observed immediately AFTER it")

    def test_a_replay_with_no_level_change_banks_nothing(self, tmp_path):
        p = _player(tmp_path)
        frames = [_frame(1), _frame(2), _frame(3)]
        sal = _banked_prefix(p, "g1", 1, frames)
        loop = _RecordingLoop()
        env = _Env([_Obs(f, levels=1) for f in frames])
        p._replay_salient_prefix(env, "g1", 1, sal, loop,
                                 pre_obs=_Obs(_frame(0), levels=1))
        assert loop.banked == [], "no level-up -> no record (never invented)"

    def test_a_crossing_on_the_first_step_still_has_a_pre_frame(self, tmp_path):
        """The pre frame for step 1 comes from the observation the replay starts
        from — without it, a one-step crossing would bank nothing."""
        p = _player(tmp_path)
        frames = [_frame(1), _frame(2), _frame(3)]
        sal = _banked_prefix(p, "g1", 1, frames)
        loop = _RecordingLoop()
        env = _Env([_Obs(frames[0], levels=2),      # crossing on step 1
                    _Obs(frames[1], levels=2), _Obs(frames[2], levels=2)])
        p._replay_salient_prefix(env, "g1", 1, sal, loop,
                                 pre_obs=_Obs(_frame(0), levels=1))
        assert len(loop.banked) == 1
        _g, level, pre, post = loop.banked[0]
        assert level == 2
        assert np.array_equal(pre, _frame(0))
        assert np.array_equal(post, frames[0])

    def test_the_hook_never_raises_into_the_replay_path(self, tmp_path):
        """CONTAINMENT — exactly as the existing site never raises."""
        class _Exploding(_RecordingLoop):
            def bank_replay_levelup(self, game, level, pre, post):
                raise RuntimeError("bank exploded")

        p = _player(tmp_path)
        frames = [_frame(1), _frame(2), _frame(3)]
        sal = _banked_prefix(p, "g1", 1, frames)
        env = _Env([_Obs(frames[0], levels=1), _Obs(frames[1], levels=2),
                    _Obs(frames[2], levels=2)])
        taken, obs = p._replay_salient_prefix(env, "g1", 1, sal, _Exploding(),
                                              pre_obs=_Obs(_frame(0), levels=1))
        assert taken == 3, "a raising bank must not truncate the replay"
        assert obs is not None

    def test_a_loop_without_the_hook_is_tolerated(self, tmp_path):
        """Old loops (and loop=None) must keep working — no AttributeError."""
        p = _player(tmp_path)
        frames = [_frame(1), _frame(2), _frame(3)]
        sal = _banked_prefix(p, "g1", 1, frames)
        env = _Env([_Obs(frames[0], levels=1), _Obs(frames[1], levels=2),
                    _Obs(frames[2], levels=2)])
        taken, _obs = p._replay_salient_prefix(env, "g1", 1, sal, None,
                                               pre_obs=_Obs(_frame(0), levels=1))
        assert taken == 3

    def test_the_bank_never_writes_the_replayed_ACTIONS_anywhere(self, tmp_path):
        """The membrane law, kept: what crosses is the OBSERVED level-up frame
        delta (the same channel `_ego_feed` already teaches on), never the banked
        prefix's actions."""
        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop()
        loop._game_id = "g1"
        loop._ego_fabric = KnowledgeFabric(str(tmp_path / "fab2"),
                                           agent_id="a", kin_key="v4")
        self._replay_crossing_level_2(tmp_path, loop)
        rec = loop._ego_fabric.query("personal", GA.FRAMES_TOPIC)[0]
        assert set(rec) >= {"game", "level", "pre", "post"}
        for banned in ("steps", "prefix", "prefix_json", "action", "actions",
                       "outcome_hash"):
            assert banned not in rec, (
                "replay material leaked into a fabric stream: %r" % banned)


class TestTheCrossingDetector:
    """The shared seam both replay paths call. Asserted directly so the
    winning-sequence path is covered by behaviour, not only by source scan."""

    def test_it_banks_once_per_crossing_and_carries_the_frames(self, tmp_path):
        p = _player(tmp_path)
        loop = _RecordingLoop()
        lv, pre = 1, _frame(0)
        lv, pre = p._bank_replay_crossing(loop, "g1", _Obs(_frame(1), levels=1),
                                          pre, lv)
        assert loop.banked == [] and lv == 1
        assert np.array_equal(pre, _frame(1)), "the pre frame must roll forward"
        lv, pre = p._bank_replay_crossing(loop, "g1", _Obs(_frame(2), levels=2),
                                          pre, lv)
        assert lv == 2 and len(loop.banked) == 1
        _g, level, bpre, bpost = loop.banked[0]
        assert level == 2
        assert np.array_equal(bpre, _frame(1)) and np.array_equal(bpost, _frame(2))
        # a later step at the SAME level must not re-bank
        lv, pre = p._bank_replay_crossing(loop, "g1", _Obs(_frame(3), levels=2),
                                          pre, lv)
        assert len(loop.banked) == 1, "one record per crossing, not per step"

    def test_it_survives_garbage_and_a_hookless_loop(self, tmp_path):
        p = _player(tmp_path)
        assert p._bank_replay_crossing(None, "g1", None, None, 0) == (0, None)
        assert p._bank_replay_crossing(object(), "g1",
                                       _Obs(_frame(1), levels=9), _frame(0),
                                       0)[0] == 9, (
            "a loop with no hook must not break the replay")


class TestTheLivePathReceipt:
    """CLAUSE 1 — a `file:line` reachable from the loop entry, not a reference."""

    def test_the_replay_path_calls_the_bank_and_the_replay_path_is_entered(self):
        src = _src(PLAYER)
        i = src.find("def _replay_salient_prefix")
        assert i != -1
        body = src[i:src.find("\n    def ", i + 10)]
        assert "_bank_replay_crossing(" in body, (
            "_replay_salient_prefix never reaches the abduction bank — the "
            "replay bypass is still open")
        # ...and _replay_salient_prefix is itself called from play_game, before
        # the explore loop (the same reachability the B7 gate pins).
        j = src.find("_replay_salient_prefix(", src.find("def play_game"))
        assert 0 < j < src.find("COGNITIVE GAME LOOP")

    def test_both_replay_paths_use_the_one_crossing_detector(self):
        """BOTH replay routes bypass the cognitive cycle. Hooking only the one
        the audit happened to name would leave the same defect open next door —
        and winning-sequence replay is the route that most often reaches L2."""
        src = _src(PLAYER)
        det = src[src.find("def _bank_replay_crossing"):]
        det = det[:det.find("\n    def ", 10)]
        assert "bank_replay_levelup(" in det, (
            "the crossing detector must actually call the bank")
        for fn in ("def _replay_salient_prefix", "def _replay_winning_sequences"):
            i = src.find(fn)
            assert i != -1, fn
            body = src[i:src.find("\n    def ", i + 10)]
            assert "_bank_replay_crossing(" in body, (
                "%s still bypasses the abduction bank" % fn)
        assert src.count("_bank_replay_crossing(") == 3, (
            "one definition + exactly two call sites; a third copy means the "
            "detector was duplicated instead of shared")

    def test_both_level_up_routes_share_one_banking_core(self):
        """No duplicated cognitive cycle: the cycle's `_goal_abd` and the replay
        seam must enter the bank through the SAME function."""
        src = _src(LOOP)
        assert "def _goal_bank(" in src, (
            "the two routes must share one banking core, not two copies")
        assert src.count("observe_levelup(") == 1, (
            "observe_levelup is called from more than one place — the cycle was "
            "duplicated instead of shared")
        assert "def bank_replay_levelup(" in src

    def test_the_window_laws_still_hold(self):
        """L1, L2, L3 (PREREG_SYMBOL_RECEIPTS.md section 2): credit and route
        live inside record_result, and the level-up is banked only AFTER the
        step is settled and routed. The name is kept; the character offsets
        are gone."""
        L = _laws()
        L.l1_credit_inside_record_result()
        L.l2_route_inside_record_result()
        L.l3_settle_before_bank()


class TestTheConsumerBehaviourChanges:
    """CLAUSE 2 — a NAMED consumer whose DECISION comes out different, and not an
    abort path. The chain is hypotheses() -> top() -> abduced_plan -> the loop's
    EGO-PLAN block, where `action_num`/`action_data` (and `_nav_goal_px`) are set
    from the abduced goal's site. Before: no hypothesis at level 2 -> abduced_plan
    returns None -> no goal-driven action. After: the replay-banked level-2
    hypotheses make abduced_plan return a plan with a site, and the agent CLICKS
    THERE. The decision that changes is WHICH ACTION IS TAKEN."""

    def _gamma_that_can_paint_the_appearing_colour(self, tmp_path):
        from engines.egocentric import effects as E
        fab = KnowledgeFabric(str(tmp_path / "cons"), agent_id="a", kin_key="v4")
        g = E.Gamma(fab)
        before = np.zeros((5, 5), dtype=int)
        before[2, 2] = 3
        after = before.copy()
        after[2, 2] = 12                       # the atom makes colour 12 appear
        aid = g.add(E.learn_effect(before, 6, after), game="g1", level=2)
        return fab, g, aid

    def test_before_the_hook_there_is_no_level_2_goal_and_no_plan(self, tmp_path):
        fab, g, _aid = self._gamma_that_can_paint_the_appearing_colour(tmp_path)
        book = GA.GoalBook(fab)
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 3
        assert book.hypotheses("g1", 2) == []
        assert GA.abduced_plan(g, book, ws, game="g1", level=2, budget=10,
                               verified_counts={}) is None, (
            "with nothing banked at level 2 the consumer produces NO decision — "
            "this is the state the whole project has been in")

    def test_after_the_hook_the_same_consumer_produces_a_different_decision(
            self, tmp_path):
        """Two replay-achieved level-2s go through the REAL banking core; the
        same abduced_plan call now returns a driveable plan with a site."""
        from cognitive_loop import _goal_bank

        fab, g, aid = self._gamma_that_can_paint_the_appearing_colour(tmp_path)

        class _Loop:
            pass
        loop = _Loop()
        loop._ego_fabric = fab
        pre, post = appearance_pair()
        for _ in range(GA.MIN_CO):
            assert _goal_bank(loop, "g1", 2, pre, post) > 0, (
                "the banking core extracted nothing from a live-shaped level-up")

        book = loop._goal_book
        hyps = book.hypotheses("g1", 2)
        assert hyps, "the replay-banked level-2 hypotheses must exist"
        ws = np.zeros((5, 5), dtype=int)
        ws[2, 2] = 3
        ap = GA.abduced_plan(g, book, ws, game="g1", level=2, budget=10,
                             verified_counts={aid: 2})
        assert ap is not None, (
            "the consumer still produces no decision — the chain "
            "hypotheses() -> top() -> abduced_plan is not actually consuming "
            "what the hook banks")
        assert ap["steps"], "a plan with no steps drives nothing"
        assert ap["site"] is not None, (
            "the site IS the changed decision: it becomes action_data {x, y}")
        assert ap["verified"] is True and ap["veto"] is False, (
            "the UNCHANGED drive gates must be able to pass, or the 'consumer' "
            "is an abort path wearing a plan's clothes")

    def test_the_loop_turns_that_plan_into_a_different_action(self):
        """L5: the named consumer's site is what becomes the action — stated as
        containment and order inside CognitiveLoop.cycle, not as the next 2000
        characters after the string "abduced_plan(" ."""
        _laws().l5_abduced_plan_becomes_the_action()
