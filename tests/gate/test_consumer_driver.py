"""THE CONSUMER DRIVER GATE (live-audit finding + the BANK_SETTLE storm).

⭐ WHY. Two live findings, one file:

1. engines/egocentric/consumer.py's consume() had NO call site in production —
   the import_queue never drained at runtime, so import_candidates never
   materialised and seed_imports had nothing to seed (B12 built the machine;
   nobody turned the key). The driver: end_game (the SAME episode boundary
   where starvation and swallow settle) calls consumer.consume(fabric, game,
   level, budget_n=8) once per episode; the NEXT episode's gamma init calls
   seed_imports so candidates written at episode N's end enter Gamma at N+1,
   flagged imported=True (the wheel rule untouched: an imported atom still
   earns its 2x TRANSFERRED before the planner trusts it).

2. [SWALLOW] block=BANK_SETTLE count=33 in one live episode: the API frame is
   a list of GRIDS (3D after _to_numpy, (k, 64, 64) with k varying on
   animation steps), and the W4c settle path threw on every effectful click —
   swallowed 33x by house containment. The regression test drives the REAL
   cycle+record_result path with API-shaped multi-grid frames and asserts the
   episode ends with ZERO BANK_SETTLE swallows.

Run pre-build: the wiring tests fail (no call site).
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric.fabric import KnowledgeFabric


def _src():
    return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                errors="replace").read()


def _fab(tmp_path, agent="a"):
    return KnowledgeFabric(str(tmp_path / "ego_fabric"), agent_id=agent,
                           kin_key="v4")


def _queue_residual(fab, before, after):
    """One raw import-queue record carrying its patches (the full sigma diet)."""
    return fab.append("collective", "import_queue", {
        "slot": "WORKSPACE", "residual": 4.0,
        "before": [[int(v) for v in row] for row in np.asarray(before)],
        "after": [[int(v) for v in row] for row in np.asarray(after)],
    })


def _sibling_atom(fab, before, after, game="other-game"):
    """A sibling's minted atom carrying its prediction signature (B13)."""
    sig = consumer.sigma_of(before, after)
    return fab.append("collective", "atoms", {
        "id": "eff-sib:0", "type": "structural", "game": game, "level": 1,
        "atom": {"kind": "EFFECT", "key": "eff-sib", "action": 6,
                 "sigma": sig,
                 "context": [[int(v) for v in row] for row in np.asarray(before)],
                 "transform": {
                     "before": [[int(v) for v in row] for row in np.asarray(before)],
                     "after": [[int(v) for v in row] for row in np.asarray(after)]}},
    })


def _patches():
    before = np.zeros((3, 3), dtype=np.uint8)
    after = before.copy()
    after[1, 1] = 5
    return before, after


class TestTheWiringExists:

    def test_consume_is_called_at_the_episode_boundary(self):
        """end_game — where starvation/swallow settle — drives the consumer."""
        src = _src()
        i = src.find("def end_game")
        j = src.find("def record_result")
        boundary = src[i:j]
        assert "consume(" in boundary, (
            "consumer.consume has no call site at the episode boundary — the "
            "import queue never drains at runtime (the live-audit finding)")
        assert "budget_n" in boundary, "the drain must be budgeted"

    def test_seed_imports_is_wired(self):
        """Candidates written at episode N end get seeded into Gamma at N+1."""
        src = _src()
        assert "seed_imports" in src, (
            "seed_imports is never called — import_candidates never reach "
            "Gamma (W1's exact-signature interface is an open socket)")


class TestTheEpisodeBoundaryDrive:

    def test_consume_runs_and_a_candidate_lands(self, tmp_path, capsys):
        """A queued residual + a sibling atom -> end_game drains the queue and
        an import_candidates record lands with the three conditions."""
        from cognitive_loop import CognitiveLoop
        before, after = _patches()
        fab = _fab(tmp_path)
        _sibling_atom(fab, before, after)
        _queue_residual(fab, before, after)

        loop = CognitiveLoop()
        loop._ego_fabric = fab
        loop._game_id = "g1"
        loop._ego_level = 0
        loop.end_game()

        cands = consumer.candidates(fab, "g1", 1)  # playing level = _ego_level + 1
        assert len(cands) == 1, "consume ran but no candidate landed"
        cand = cands[0]
        assert cand["atom"].get("key") == "eff-sib"
        assert "three_conditions" in cand, "the seq-provable conditions must travel"
        marks = [r for r in fab.query("collective", "import_queue")
                 if r.get("kind") == "consumed"]
        assert marks, "no consumed marker — the queue item was not closed"
        assert consumer.pending(fab) == [], "the queue did not drain"

        loop.end_game()  # once per episode: the settled flag holds
        assert len(consumer.candidates(fab, "g1", 1)) == 1

    def test_next_episode_init_seeds_the_candidate_imported(
            self, tmp_path, monkeypatch, capsys):
        """Episode N ends with a candidate; episode N+1's gamma init seeds it
        into Gamma flagged imported=True."""
        from cognitive_loop import CognitiveLoop
        from engines.cognition.cognitive_frame import CognitiveFrame
        before, after = _patches()
        fab = _fab(tmp_path)
        _sibling_atom(fab, before, after)
        _queue_residual(fab, before, after)

        ep1 = CognitiveLoop()
        ep1._ego_fabric = fab
        ep1._game_id = "g1"
        ep1._ego_level = 0
        ep1.end_game()
        assert consumer.candidates(fab, "g1", 1), "episode N left no candidate"

        # Episode N+1: a fresh loop instance; record_result's lazy fabric+gamma
        # init roots at tmp_path because the loop is TOLD to (the de-cwd build,
        # 2026-08-22: the root is threaded in, never inherited from the cwd).
        monkeypatch.chdir(tmp_path)
        ep2 = CognitiveLoop(data_root=str(tmp_path))
        ep2.start_game("g1", [1, 2, 3, 4, 5, 6])
        ep2._current_frame = CognitiveFrame(action_number=0,
                                            timestamp=time.time(), level=1)
        frame = [np.zeros((64, 64), dtype=np.uint8).tolist()]
        ep2.record_result(frame, False, 0.0, False)

        imported = [r for r in fab.query("collective", "atoms")
                    if (r.get("atom") or {}).get("imported")]
        assert imported, (
            "the N+1 init never seeded the candidate — seed_imports unwired")
        assert imported[0]["atom"]["key"] == "eff-sib"
        assert int(imported[0]["level"]) == 1, "seeded at the playing level"

        # Idempotent per atom key: a second init-cycle seeds nothing new.
        ep3 = CognitiveLoop(data_root=str(tmp_path))
        ep3.start_game("g1", [1, 2, 3, 4, 5, 6])
        ep3._current_frame = CognitiveFrame(action_number=0,
                                            timestamp=time.time(), level=1)
        ep3.record_result(frame, False, 0.0, False)
        again = [r for r in fab.query("collective", "atoms")
                 if (r.get("atom") or {}).get("imported")]
        assert len(again) == len(imported), "seeding is not idempotent"


class TestTheBankSettleStorm:

    # The live frame shape: the API returns a LIST of animation grids per
    # step; _to_numpy turns it into a (k, 64, 64) stack and k VARIES with the
    # animation phase. k=2 then k=3 between commit and settle is the storm.
    K_PATTERN = (2, 2, 3, 2, 3, 2, 3, 2)

    def _drive(self, tmp_path, monkeypatch):
        """The REAL cycle+record_result path under API-shaped frames."""
        from cognitive_loop import CognitiveLoop
        monkeypatch.chdir(tmp_path)

        class _Obs:
            levels_completed = 0
            score = 0

        base = np.zeros((64, 64), dtype=np.uint8)
        base[::2, :] = 9
        loop = CognitiveLoop(data_root=str(tmp_path))
        loop.start_game("g1", [1, 2, 3, 4, 5, 6],
                        max_actions=len(self.K_PATTERN))
        prev = base
        prev_raw = [prev.tolist()] * self.K_PATTERN[0]
        for step, k in enumerate(self.K_PATTERN):
            action, data, cf = loop.cycle(prev_raw, _Obs())
            post = prev.copy()
            post[step % 64, 0] = 1 + (step % 7)      # every step is effectful
            post_raw = [prev.tolist()] * (k - 1) + [post.tolist()]
            loop.record_result(post_raw, True, 0.0, False)
            prev, prev_raw = post, post_raw
        loop.end_game()
        return loop

    def test_the_settle_path_swallows_nothing(self, tmp_path, monkeypatch):
        """Pre-fix: pricing.informative_salience raised
        `ValueError: operands could not be broadcast together` on every
        (k=2 -> k=3) animation step inside BetBook.settle, swallowed as
        BANK_SETTLE (33x in one live bp35 episode). Post-fix: the same drive
        settles cleanly — zero BANK_SETTLE swallows, and the equal-shape step
        still PRICES (the fix voids the unpriceable, it never mutes the book)."""
        loop = self._drive(tmp_path, monkeypatch)
        counts = getattr(loop, "_swallow_counts", None) or {}
        assert counts.get("BANK_SETTLE", 0) == 0, (
            "the settle path still swallows under API-shaped multi-grid "
            "frames: %r" % (counts,))
        bb = getattr(loop, "_bet_book", None)
        assert bb is not None and bb.settled > 0, "no bet ever settled"
        assert bb.records, (
            "no settle ever priced — the fix must void ONLY the unpriceable "
            "(mismatched stacks), never the equal-shape settles")
