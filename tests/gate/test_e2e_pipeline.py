"""E2E PIPELINE GATE: one synthetic episode through the REAL CognitiveLoop,
every producer's output verified in the fabric afterward.

The existing 416 gate tests are unit/falsifier/static; this file is COMPOSITION:
the full chain -- cycle() -> record_result() -> episode-end recorders ->
end_game() -- driven hermetically (tmp cwd, synthetic 64x64 frames, seeded RNG)
against a deterministic toy world:

  * a clickable board: a click on a pair of 0-cells paints a 2-cell colour-5
    object (the deterministic transform the mint learns);
  * an independent mover: a colour-7 cell advancing one column every even step
    (world-caused change, no click involved);
  * a forced movement action every 7th step (banks move affordances);
  * one level-up on the final step (the reward that mints ideas).

Afterward the books are audited: EFFECT atoms minted WITH sigma, settlements
carrying atom_key/atom_bin, starvation+swallow settled at end_game (<= 1 per
socket/block, idempotent on a second end_game), harvest + move records banked
through the SHIPPED episode-end recorder blocks (extracted verbatim from
cognitive_game_player.py), and the [PLAN-GATE]/[AFFECT]/[MINT]/[EGO-MINT]
narration present in the captured stream.

NOTE on pace: the [PLAN-GATE] line prints every 200 cycles; the episode is 36
cycles with the cadence counter fast-forwarded to 199 before the final cycle,
so the 200th-cycle print site executes without paying 200 real cycles (this
box's antivirus makes fabric read-after-append pathologically slow).
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

from engines.egocentric.consumer import INVARIANTS  # noqa: E402
from engines.egocentric.starvation import StarvationBook  # noqa: E402
from engines.egocentric.swallow import SwallowBook, swallow_note  # noqa: E402

N_STEPS = 36          # full real cycles (kept small: fabric I/O is AV-taxed here)
LEVEL_UP_STEP = 35    # the final step's click is the level-up
MOVE_EVERY = 7        # every 7th step executes a movement action (1..5)
GAME_ID = "e2e_gate_g1"


class SynthEnv:
    """Deterministic toy world on a 64x64 board.

    Click on (x, y): if cells (y, x) and (y, x+1) are both 0 they become 5
    (the deterministic 2-cell transform); anything else is a dead click.
    Independent mover: colour 7 at row 40 advances one column every even step.
    Movement actions never change the board.
    """

    def __init__(self):
        self.board = np.zeros((64, 64), dtype=int)
        self.step = 0
        self.mover = [40, 5]
        self.board[40, 5] = 7

    def apply(self, action, data):
        pre = self.board.copy()
        if self.step % 2 == 0:                      # the mover owes nobody a click
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


def _extract_episode_end_block():
    """The SHIPPED episode-end recorder region of cognitive_game_player.py,
    verbatim: the 3d-ii harvest write AND the B2 moves write (the B7 block in
    between is guarded by its own try/except and no-ops without a player)."""
    src = _src("cognitive_game_player.py")
    start = src.index("3d-ii (EGO-FRONTIER): harvest the episode's exploration")
    start = src.rindex("\n", 0, start) + 1
    end = src.index("# End game and get replay", start)
    end = src.rindex("\n", 0, end)
    return textwrap.dedent(src[start:end])


def _run_episode_end(loop, game_id, current_levels, ep_moves):
    block = _extract_episode_end_block()

    class _GS:
        GAME_OVER = object()
        WIN = object()

    ns = {"loop": loop, "game_id": game_id, "current_levels": current_levels,
          "prev_levels": current_levels, "_ep_moves": dict(ep_moves),
          "last_obs": None, "GameState": _GS}
    exec(compile(block, "<episode-end-recorder>", "exec"), ns)  # noqa: S102 -- executes the extracted shipped block under test


@pytest.fixture(scope="module")
def episode(tmp_path_factory):
    """Run the synthetic episode ONCE; every test below audits its books."""
    run_dir = tmp_path_factory.mktemp("e2e_run")
    cwd = os.getcwd()
    os.chdir(run_dir)
    try:
        random.seed(20260814)
        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop(data_root=str(run_dir))
        loop.start_game(GAME_ID, [1, 2, 3, 4, 5, 6], max_actions=500)
        env = SynthEnv()
        obs = types.SimpleNamespace(levels_completed=0)
        frame = env.board.copy()
        ep_moves = {}
        clicks, forced_moves = [], []
        buf = io.StringIO()
        with redirect_stdout(buf):
            for i in range(N_STEPS):
                if i == N_STEPS - 1 and hasattr(loop, "_plan_gate"):
                    # cadence fast-forward: the 200th-cycle narration site fires
                    loop._plan_gate["cycles"] = 199
                action, data, _cf = loop.cycle(frame, obs)
                if i % MOVE_EVERY == 3:
                    # the game player would execute a movement action here;
                    # committed != executed is the bet book's own VOID law
                    action, data = 1 + (i // MOVE_EVERY) % 5, None
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
                    forced_moves.append(action)
                    prev = ep_moves.get(str(action), (0, 0))
                    ep_moves[str(action)] = (prev[0] + (1 if changed else 0),
                                             prev[1] + (0 if changed else 1))
                elif action == 6 and data:
                    clicks.append((i, int(data["x"]), int(data["y"]), changed,
                                   level_changed))
                loop.record_result(post_frame=post, frame_changed=changed,
                                   score_delta=0.0, level_changed=level_changed,
                                   new_level=2 if level_changed else 0)
                frame = post
            # loop-side accrual snapshot BEFORE the recorders run
            accrued_effects = list(getattr(loop, "_ego_frontier_effects", []))
            accrued_dead = list(getattr(loop, "_ego_frontier_dead", []))
            real_swallows = dict(getattr(loop, "_swallow_counts", None) or {})
            counters = dict(getattr(loop, "_plan_gate", None) or {})
            counters.update(getattr(loop, "_w4c_counters", None) or {})
            _run_episode_end(loop, GAME_ID, current_levels=1, ep_moves=ep_moves)
            # exercise the swallow settle deterministically: two notes, one block
            swallow_note(loop, "OTHER")
            swallow_note(loop, "OTHER")
            expected_swallow = SwallowBook.swallowed(
                dict(getattr(loop, "_swallow_counts", None) or {}))
            loop.end_game()
            loop.end_game()   # the <=1-per-episode rule: a second settle is inert
        yield {
            "loop": loop, "fabric": loop._ego_fabric, "out": buf.getvalue(),
            "ep_moves": ep_moves, "clicks": clicks,
            "accrued_effects": accrued_effects, "accrued_dead": accrued_dead,
            "real_swallows": real_swallows, "counters": counters,
            "expected_swallow": expected_swallow,
        }
    finally:
        os.chdir(cwd)


class TestAtomsMinted:

    def test_effect_atoms_minted_with_sigma(self, episode):
        atoms = episode["fabric"].query("collective", "atoms")
        assert atoms, ("an episode of deterministic 2-cell click transforms "
                       "minted NO atoms -- the mint chain is dead")
        effects = [r for r in atoms if (r.get("atom") or {}).get("kind") == "EFFECT"]
        assert effects, "no EFFECT atom in the atoms stream"
        for rec in effects:
            atom = rec["atom"]
            sig = atom.get("sigma")
            assert isinstance(sig, dict), (
                "minted atom %r carries no sigma -- B13 signature-at-mint broke "
                "in composition" % (atom.get("key"),))
            missing = [k for k in INVARIANTS if k not in sig]
            assert not missing, (
                "atom %r sigma lacks invariants %r -- the consumer can never "
                "recognize it" % (atom.get("key"), missing))
            assert rec.get("game") == GAME_ID
            assert atom.get("key", "").startswith("eff-")

    def test_mint_ledger_accounts_for_every_atom(self, episode):
        fab = episode["fabric"]
        verdicts = fab.query("collective", "mint_verdicts")
        assert verdicts, "the mint never ledgered a verdict"
        allowed = {"mint", "reject", "rederivation", "quarantine"}
        assert {v.get("verdict") for v in verdicts} <= allowed
        mints = sum(1 for v in verdicts if v.get("verdict") == "mint")
        atoms = fab.query("collective", "atoms")
        assert mints == len(atoms), (
            "mint verdicts say %d mints but the atoms stream holds %d records "
            "-- a write site is bypassing the ledger" % (mints, len(atoms)))

    def test_mint_narration_present(self, episode):
        assert "[MINT] verdict=mint" in episode["out"], (
            "an accepted mint printed no [MINT] line -- nothing silent")


class TestSettlements:

    def test_settlements_written_with_atom_identity_fields(self, episode):
        setts = episode["fabric"].query("collective", "settlements")
        assert len(setts) >= 10, (
            "only %d settlements for a %d-step episode -- the bet spine is not "
            "settling" % (len(setts), N_STEPS))
        for s in setts:
            assert "atom_key" in s and "atom_bin" in s, (
                "settlement %r lacks the atom identity pair -- the n=1 linkage "
                "is off the record" % (s,))
            assert s.get("game") == GAME_ID
            assert "nontrivial" in s and "action" in s and "level" in s

    def test_some_settlement_names_the_atom_that_bet(self, episode):
        fab = episode["fabric"]
        setts = fab.query("collective", "settlements")
        keyed = [s for s in setts if s.get("atom_key")]
        assert keyed, (
            "no settlement ever carried a non-null atom_key -- known-atom bets "
            "never reached the settlement record (F4 linkage broken)")
        atom_ids = {r.get("id") for r in fab.query("collective", "atoms")}
        for s in keyed:
            assert s["atom_key"] in atom_ids, (
                "settlement names atom %r which the atoms stream does not hold"
                % (s["atom_key"],))


class TestEpisodeBoundaryBooks:

    def test_starvation_settled_consistent_and_bounded(self, episode):
        fab = episode["fabric"]
        recs = [r for r in fab.query("personal", "starvation")
                if r.get("game") == GAME_ID]
        expected = {s["socket"]: s["code"]
                    for s in StarvationBook.starved(episode["counters"])}
        got = {}
        for r in recs:
            assert r["socket"] not in got, (
                "socket %r settled twice in one episode -- the <=1 rule broke"
                % (r["socket"],))
            got[r["socket"]] = r["code"]
        assert got == expected, (
            "starvation records %r do not match the pure decision %r over the "
            "loop's own counters" % (got, expected))

    def test_swallow_settled_consistent_and_bounded(self, episode):
        fab = episode["fabric"]
        recs = fab.query("personal", "swallow")
        expected = {(s["block"], s["count"]) for s in episode["expected_swallow"]}
        got = [(r["block"], r["count"]) for r in recs]
        assert len(got) == len({r["block"] for r in recs}), (
            "a block settled twice in one episode -- the <=1 rule broke: %r"
            % (got,))
        assert set(got) == expected, (
            "swallow records %r do not match the pure decision %r" % (got, expected))
        assert ("OTHER", 2) in set(got), (
            "the two injected OTHER swallows never reached the personal stream")

    def test_second_end_game_is_inert(self, episode):
        # the fixture already called end_game twice; had the second call
        # re-settled, the per-socket/per-block uniqueness above would fail.
        # Here: the guard flags themselves.
        loop = episode["loop"]
        assert getattr(loop, "_starve_settled", False) is True
        assert getattr(loop, "_swallow_settled", False) is True

    def test_no_exception_storm_in_the_healthy_episode(self, episode):
        assert episode["real_swallows"] == {}, (
            "the episode swallowed exceptions %r -- a guarded EGO block is "
            "broken and starving silently" % (episode["real_swallows"],))


class TestHarvestAndMoves:

    def test_click_experience_banked_through_the_shipped_recorder(self, episode):
        loop = episode["loop"]
        book = loop._ego_frontier_book
        assert book is not None
        h = book.load_harvest(GAME_ID, 1)
        assert episode["accrued_effects"], "the episode accrued no effect clicks"
        for cell in episode["accrued_effects"]:
            assert tuple(cell) in h["effects"], (
                "accrued effect cell %r missing from the banked harvest" % (cell,))
        for cell in episode["accrued_dead"]:
            assert tuple(cell) in h["tried"], (
                "accrued dead report %r missing from the harvest's tried set"
                % (cell,))

    def test_move_affordances_banked_through_the_shipped_recorder(self, episode):
        loop = episode["loop"]
        moves = loop._ego_frontier_book.load_moves(GAME_ID, 1)
        assert moves == {a: tuple(c) for a, c in episode["ep_moves"].items()}, (
            "banked move affordances %r do not match the episode's executed "
            "movement outcomes %r" % (moves, episode["ep_moves"]))


class TestRewardMintsIdeas:

    def test_level_up_minted_click_idea_in_both_scopes(self, episode):
        fab = episode["fabric"]
        for scope in ("personal", "collective"):
            ideas = [r for r in fab.query(scope, "ideas")
                     if r.get("game") == GAME_ID]
            kinds = {(r.get("idea") or {}).get("kind") for r in ideas}
            assert "CLICK_AT" in kinds, (
                "the level-up click minted no CLICK_AT idea in the %s scope"
                % scope)
            for r in ideas:
                assert r.get("level") == 1, (
                    "idea %r minted without the reward's level" % (r.get("id"),))
        assert "[EGO-MINT]" in episode["out"]


class TestNarration:

    def test_plan_gate_line_emitted(self, episode):
        assert "[PLAN-GATE]" in episode["out"], (
            "the 200th-cycle [PLAN-GATE] narration never printed")

    def test_affect_line_emitted(self, episode):
        assert "[AFFECT]" in episode["out"], (
            "the affect state never narrated -- no channel may move silently")

    def test_ego_frontier_harvest_loaded_narration(self, episode):
        assert "[EGO-FRONTIER] harvest loaded" in episode["out"]
