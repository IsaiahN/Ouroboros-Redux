"""THE VERIFIED-HYDRATION GATE (record/canon/KNOBS.md AMENDMENT 3, A3-1 -- the grain audit's defect).

⭐ WHY. "Verified" had TWO stores and only one was consulted: settlements persist
atom_key + atom_bin ("TRANSFERRED", ...) on the fabric, but the planner's DRIVE
gate reads ONLY the in-memory _atom_verified dict, which is created EMPTY at the
W4c lazy-init of every episode. Consequence: every atom -- imported atoms
especially -- had to earn its 2x TRANSFERRED inside a single episode or never
drive; cross-episode verification evaporated, and the import verdict was
handicapped (the machine ships atoms across fabrics, then forgets it ever
verified them).

THE FIX under test: at the W4c lazy-init, _atom_verified is HYDRATED from the
settlements books (personal + collective, THIS game at full-id grain, the
PLAYING level = _ego_level + 1 per A3-2, bounded to the last N=500 records per
scope). The in-episode increment path is unchanged -- it adds to the hydrated
base. "Verified" becomes book-derived: one definition, persistent, auditable.

Run pre-fix: both tests fail (the lazy-init writes a bare {}).
"""
from __future__ import annotations

import io
import os
import sys
import time
import types
from contextlib import redirect_stdout

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer  # noqa: E402
from engines.egocentric.effects import Gamma, learn_effect  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402

GAME = "hyd25-4f00c0de"      # knowledge streams ride the FULL version id (A3-3)
AID = "eff-feedbeef:0"
CELL = (20, 20)              # the transforming cell: colour 3 -> 4


def _settlement(game=GAME, level=1, atom_key=AID, atom_bin="TRANSFERRED"):
    """One fabric settlements record in BetBook.settle's exact shape."""
    return {"agent": "agent", "game": game, "level": level, "action": 6,
            "members": 1, "best": 1.0, "nontrivial": True,
            "atom_key": atom_key, "atom_bin": atom_bin}


def _frames():
    before = np.zeros((64, 64), dtype=int)
    before[CELL] = 3
    after = before.copy()
    after[CELL] = 4
    return before, after


class TestBookDerivedVerification:

    def test_fresh_loop_hydrates_transferred_counts_from_the_books(
            self, tmp_path, monkeypatch):
        """Two TRANSFERRED settlements for an atom already ON the books; a FRESH
        loop's lazy-init must carry the count -- pre-fix the dict inits empty and
        the verification evaporates with the episode that earned it."""
        from cognitive_loop import CognitiveLoop
        from engines.cognition.cognitive_frame import CognitiveFrame
        monkeypatch.chdir(tmp_path)
        fab = KnowledgeFabric(str(tmp_path / "ego_fabric"), agent_id="agent",
                              kin_key="v4")
        for _ in range(2):
            fab.append("collective", "settlements", _settlement())
        # Noise that must NOT count toward this game's playing-level tally:
        fab.append("collective", "settlements", _settlement(game="other-game"))
        fab.append("collective", "settlements", _settlement(level=7))
        fab.append("collective", "settlements", _settlement(atom_bin="NOVEL"))
        fab.append("collective", "settlements", _settlement(atom_key=None))

        loop = CognitiveLoop()
        loop.start_game(GAME, [1, 2, 3, 4, 5, 6])
        loop._current_frame = CognitiveFrame(action_number=0,
                                             timestamp=time.time(), level=1)
        frame = [np.zeros((64, 64), dtype=np.uint8).tolist()]
        loop.record_result(frame, False, 0.0, False)

        av = getattr(loop, "_atom_verified", None) or {}
        assert av.get(AID, 0) >= 2, (
            "A3-1: a fresh loop's _atom_verified must be HYDRATED from the "
            "settlements books (2x TRANSFERRED on disk) -- got %r" % (av,))
        assert av.get(AID, 0) == 2, (
            "hydration over-counted: other-game / other-level / non-TRANSFERRED "
            "/ null-key records leaked into the tally -- got %r" % (av,))

    def test_book_verified_import_drives_the_plan_on_a_fresh_episode(
            self, tmp_path, monkeypatch):
        """The full A3-1 consequence: an atom imported from a sibling fabric and
        verified 2x TRANSFERRED ON THE BOOKS passes the planner's verified gate
        in a FRESH episode -- no re-earning inside the episode. Pre-fix the plan
        shadows with verified=False forever."""
        from cognitive_loop import CognitiveLoop
        monkeypatch.chdir(tmp_path)
        before, after = _frames()

        # 1. The SIBLING's fabric: the atom is minted elsewhere, sigma at birth.
        sib_root = os.path.join(str(tmp_path), "sibling_fabric")
        sib = KnowledgeFabric(sib_root, agent_id="sibling", kin_key="other_kin")
        atom = learn_effect(before, 6, after)
        assert atom is not None and atom["kind"] == "EFFECT"
        atom["sigma"] = consumer.sigma_of(before, after)
        Gamma(sib).add(atom, "someone_elses_game", 1)
        monkeypatch.setenv("OURO_FABRIC_SEEDS", sib_root)

        obs = types.SimpleNamespace(levels_completed=1)

        # 2. EPISODE N: the import lands in the home Gamma (the consumer dance).
        ep1 = CognitiveLoop()
        ep1.start_game(GAME, [6], max_actions=200)
        with redirect_stdout(io.StringIO()):
            ep1.cycle(before, obs)
            ep1.record_result(before, False, 0.0, False)
        fab = ep1._ego_fabric
        assert fab is not None and sib_root in fab.seeds
        fab.append("collective", "import_queue",
                   {"slot": "WORKSPACE", "residual": 1.0,
                    "before": before.tolist(), "after": after.tolist()})
        assert consumer.consume(fab, GAME, 2, 20)["candidates"] >= 1
        assert consumer.seed_imports(ep1._gamma, fab, GAME, 2) == 1
        recs = fab.query("collective", "atoms",
                         where=lambda r: r.get("game") == GAME)
        assert len(recs) == 1 and recs[0]["atom"].get("imported") is True
        aid = recs[0]["id"]

        # 3. The BOOKS say verified: 2x TRANSFERRED at the playing level (2).
        for _ in range(2):
            fab.append("collective", "settlements",
                       _settlement(level=2, atom_key=aid))

        # 4. EPISODE N+1: a FRESH loop. Its lazy-init must hydrate the counts.
        ep2 = CognitiveLoop()
        ep2.start_game(GAME, [6], max_actions=200)
        with redirect_stdout(io.StringIO()):
            ep2.cycle(before, obs)                       # obs: playing level 2
            ep2.record_result(before, False, 0.0, False)
        av = getattr(ep2, "_atom_verified", None) or {}
        assert av.get(aid, 0) >= 2, (
            "the fresh episode's _atom_verified is not book-derived: %r" % (av,))

        # 5. Plan-gate preconditions the loop earns live in a real episode:
        #    level >= 1, a REFERENCE-bound class, a reference snapshot.
        for _ in range(4):
            ep2._role_binder.observe_attributed(
                9, 6, False, True, {(40, 6), (40, 7)}, {(5, 5)}, 0)
        ep2._reference_snapshot = after.copy()

        buf = io.StringIO()
        with redirect_stdout(buf):
            action, data, _cf = ep2.cycle(before, obs)
        out = buf.getvalue()
        assert "[PLAN] DRIVE" in out, (
            "book-verified import still shadows on a fresh episode -- "
            "cross-episode verification evaporated (A3-1):\n%s" % out)
        assert action == 6 and data == {"x": CELL[1], "y": CELL[0]}, (
            "the drive click must land on the atom's context site %r -- got "
            "action=%r data=%r" % (CELL, action, data))
