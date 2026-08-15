"""FIG-9 GATE: a residual must be CHARACTERIZED, not named (the import-queue fix).

Live import_queue records used to carry only {slot, residual, game, level} -- a
NAME (a magnitude with an address), not a description. The consumer then had
nothing to match (base-rate "vocabulary" not-founds) and the LP drive nothing
to score (no evidence, no signal). THE FIX, pinned here:

  * at the W4c-4 persist site, when before/after evidence is in hand, the
    record additionally carries "sigma" (consumer.sigma_of at ENQUEUE time --
    the description step, the priority condition) and compact bbox-cropped
    "pre"/"post" patches + the absolute "bbox" (BOUNDED: patches are skipped
    when the changed-region bbox exceeds PATCH_BOARD_FRACTION of the board;
    sigma is kept ALWAYS);
  * consumer.describe USES the persisted sigma when present (no recompute --
    the enqueue-time description is the one whose seq precedes the match);
  * lp_drive.signal scores ONLY sigma-carrying records -- pre-fix records are
    STRUCTURALLY INERT, so the LP arm's evidence clock restarts automatically
    at the fix boundary (no migration, no flag day);
  * old records stay READABLE everywhere (compat): pending/consume still walk
    them, the frame-carrying synthetic shape still recomputes its sigma.

Run pre-build: the characterization tests failed (consumer.characterize absent;
describe recomputed; sigma-less frame records scored).
"""
from __future__ import annotations

import io
import os
import sys
import types
from contextlib import redirect_stdout

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric.effects import Gamma
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.mint import MDLMint

GAME = "qch2-0c556536"      # FULL version id -- the A3-3 knowledge grain


def _characterize():
    try:
        from engines.egocentric.consumer import (
            PATCH_BOARD_FRACTION,  # noqa: F401
            characterize,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("consumer.characterize missing (%s) -- Fig 9 has not landed" % e)
    return consumer


# ── synthetic frames ──────────────────────────────────────────────────────────

def _pocket_pair():
    """A 2x2 recolour on 8x8: bbox [1,1,2,2], area 4 <= 0.25*64 -- patches kept."""
    b = np.zeros((8, 8), dtype=int)
    b[1:3, 1:3] = 3
    a = np.zeros((8, 8), dtype=int)
    a[1:3, 1:3] = 5
    return b, a


def _oversized_pair():
    """Two far corners changed on 8x8: bbox area 64 > 0.25*64 -- patches skipped."""
    b = np.zeros((8, 8), dtype=int)
    a = np.zeros((8, 8), dtype=int)
    a[0, 0] = 1
    a[7, 7] = 2
    return b, a


def _recolour(n=5, cells=((2, 2),), src=2, dst=3):
    b = np.full((n, n), src, dtype=int)
    a = b.copy()
    for r, c in cells:
        a[r, c] = dst
    return b, a


def _mint_into(root, game):
    """Mint one atom into a fresh sibling fabric via the REAL mint."""
    f = KnowledgeFabric(str(root), agent_id="agentB", kin_key="kinB")
    b, a = _recolour()
    v = MDLMint(Gamma(f)).consider(b, 1, a, game, 1)
    assert v["verdict"] == "mint", "fixture mint failed: %r" % (v,)
    return f


def _home(tmp_path, seeds, name="home"):
    return KnowledgeFabric(str(tmp_path / name), seeds=[str(s) for s in seeds],
                           agent_id="agentA", kin_key="kinA")


def _new_format(before, after, residual=1.0):
    """A record in the POST-FIX live shape: characterized, NO raw frames."""
    rec = {"slot": "WORKSPACE", "residual": float(residual)}
    rec.update(_characterize().characterize(before, after, slot="WORKSPACE",
                                            residual=residual))
    return rec


# ── the characterization helper ───────────────────────────────────────────────

class TestTheCharacterization:

    def test_pocket_residual_carries_sigma_and_patches(self):
        con = _characterize()
        b, a = _pocket_pair()
        out = con.characterize(b, a, slot="WORKSPACE", residual=9.0)
        assert set(out) == {"sigma", "pre", "post", "bbox"}
        assert out["sigma"] == con.sigma_of(b, a, slot="WORKSPACE", residual=9.0), (
            "the persisted sigma must BE the enqueue-time description")
        assert all(k in out["sigma"] for k in con.INVARIANTS)
        assert out["bbox"] == [1, 1, 2, 2], "the bbox must be absolute board coords"
        assert out["pre"] == [[3, 3], [3, 3]] and out["post"] == [[5, 5], [5, 5]], (
            "patches must be the bbox CROP, compact, JSON-native")

    def test_oversized_bbox_skips_patches_but_keeps_sigma(self):
        con = _characterize()
        b, a = _oversized_pair()
        out = con.characterize(b, a, slot="WORKSPACE", residual=2.0)
        assert set(out) == {"sigma"}, (
            "an oversized changed region is BOUNDED out of the patch store")
        assert all(k in out["sigma"] for k in con.INVARIANTS), (
            "sigma is kept ALWAYS -- the description is never size-gated")
        assert con.PATCH_BOARD_FRACTION * b.size < 8 * 8, (
            "fixture must actually exceed the patch bound it exercises")

    def test_degrades_to_sigma_only_never_raises(self):
        con = _characterize()
        out = con.characterize(None, None, slot="BODY", residual=1.0)
        assert set(out) == {"sigma"} and out["sigma"]["slot"] == "BODY"


# ── the W4c-4 persist site, driven through the REAL loop ──────────────────────

@pytest.fixture(scope="module")
def episode(tmp_path_factory):
    """A hermetic run through cycle+record_result (the test_level_conventions
    staging): once the binder binds REFERENCE, its identity bet's residual
    routes NOVEL and W4c-4 persists it -- now CHARACTERIZED."""
    root = tmp_path_factory.mktemp("qchar_run")
    cwd = os.getcwd()
    os.chdir(root)
    try:
        from cognitive_loop import CognitiveLoop
        loop = CognitiveLoop()
        loop.start_game(GAME, [1, 2, 3, 4, 5, 6], max_actions=64)
        obs = types.SimpleNamespace(levels_completed=0, score=0)
        prev = np.zeros((64, 64), dtype=np.uint8)
        prev[::2, :] = 9
        buf = io.StringIO()
        with redirect_stdout(buf):
            for step in range(6):
                loop.cycle([prev.tolist()], obs)
                post = prev.copy()
                post[step, 0] = 1 + (step % 7)
                loop.record_result([post.tolist()], True, 0.0, False)
                if step == 1:
                    for _ in range(4):
                        loop._role_binder.observe_attributed(
                            9, 6, False, True, {(40, 6), (40, 7)}, {(5, 5)}, 0)
                prev = post
        fab = loop._ego_fabric
        assert fab is not None
        yield {"fabric": fab,
               "raws": [r for r in fab.query("collective", "import_queue")
                        if "kind" not in r]}
    finally:
        os.chdir(cwd)


class TestThePersistSite:

    def test_live_records_carry_sigma_and_patches(self, episode):
        con = _characterize()
        raws = episode["raws"]
        assert raws, ("no NOVEL residual was persisted -- the REFERENCE "
                      "identity bet never routed (understaged binder?)")
        charac = [r for r in raws if isinstance(r.get("sigma"), dict)]
        assert charac, "W4c-4 persisted no characterized record (Fig 9 not wired)"
        full = [r for r in charac
                if all(k in r["sigma"] for k in con.INVARIANTS)]
        assert full, "no persisted sigma carries the full invariant set"
        patched = [r for r in full
                   if "pre" in r and "post" in r and len(r.get("bbox") or []) == 4]
        assert patched, "a pocket-sized changed region must persist its patches"
        for r in raws:                       # A3-2 convention rides unchanged
            assert r.get("game") == GAME and int(r.get("level", -1)) == 1

    def test_live_records_feed_the_lp_signal(self, episode):
        from engines.egocentric.lp_drive import CEIL, LPDrive
        sig = LPDrive(episode["fabric"]).signal(GAME)
        assert sig, "characterized live records must be scoreable by the LP drive"
        assert all(len(s["bbox"]) == 4 and 0.0 < s["weight"] <= CEIL for s in sig)


# ── the consumer on the new shape (describe -> match -> candidate) ────────────

class TestTheConsumerReads:

    def test_describe_uses_the_persisted_sigma_no_recompute(self):
        con = _characterize()
        b, a = _pocket_pair()
        rec = _new_format(b, a, residual=9.0)
        ob, oa = _oversized_pair()
        rec["before"] = ob.tolist()          # poison: a CONTRADICTORY frame pair
        rec["after"] = oa.tolist()
        got = con.describe(rec)
        assert got == rec["sigma"], (
            "describe must return the PERSISTED enqueue-time sigma verbatim -- "
            "recomputing breaks the priority condition (the seq that precedes "
            "the match is the persisted description's)")

    def test_persisted_sigma_record_matches_end_to_end(self, tmp_path):
        """The full path on the post-fix shape (no raw frames anywhere):
        describe -> match -> candidate against a synthetic sibling atom."""
        con = _characterize()
        src = _mint_into(tmp_path / "src", "g_src")
        home = _home(tmp_path, [src.root])
        b, a = _recolour()
        rec = _new_format(b, a, residual=1.0)
        assert "before" not in rec and "after" not in rec
        home.append("collective", "import_queue", rec)
        rep = con.consume(home, "g_home", 1, 8)
        assert rep["drained"] == 1 and rep["candidates"] == 1, (
            "a characterized record must recognize its sibling atom: %r" % (rep,))
        cand = con.candidates(home, "g_home", 1)[0]
        assert cand["sigma"] == rec["sigma"], "the candidate must cite the persisted sigma"
        assert cand["source_game"] == "g_src"

    def test_old_frame_records_still_recompute_and_match(self, tmp_path):
        """COMPAT: the legacy synthetic shape (raw frames, no sigma) still
        earns its candidate through the recompute path."""
        con = _characterize()
        src = _mint_into(tmp_path / "src", "g_src")
        home = _home(tmp_path, [src.root])
        b, a = _recolour()
        home.append("collective", "import_queue",
                    {"slot": "WORKSPACE", "residual": 1.0,
                     "before": b.tolist(), "after": a.tolist()})
        rep = con.consume(home, "g_home", 1, 8)
        assert rep["candidates"] == 1

    def test_pre_fix_live_records_still_walk_the_queue(self, tmp_path):
        """COMPAT: a pre-fix live record ({slot, residual, game, level}) is
        still listed, drained, and closed as the impoverished-description
        not-found it always was -- readable, never a crash."""
        con = _characterize()
        home = _home(tmp_path, [])
        home.append("collective", "import_queue",
                    {"slot": "WORKSPACE", "residual": 4.0,
                     "game": "g_old", "level": 1})
        assert len(con.pending(home)) == 1
        rep = con.consume(home, "g_old", 1, 8)
        assert rep["drained"] == 1 and rep["not_found"] == 1
        assert con.open_not_found(home)[0]["axis"] == "vocabulary"


# ── the LP cutoff (the arm clock restarts at the fix boundary) ────────────────

class TestTheLpCutoff:

    def test_signal_ignores_sigma_less_records(self, tmp_path):
        """Pre-fix records are STRUCTURALLY INERT to the LP drive: no sigma,
        no score -- even when a frame pair is present and compressible."""
        _characterize()
        from engines.egocentric.lp_drive import LPDrive
        fab = KnowledgeFabric(str(tmp_path / "old"), agent_id="a", kin_key="v4")
        fab.append("collective", "import_queue",     # pre-fix live shape
                   {"slot": "WORKSPACE", "residual": 9.0, "game": "g1", "level": 1})
        b, a = _pocket_pair()
        fab.append("collective", "import_queue",     # frame pair, still no sigma
                   {"slot": "WORKSPACE", "residual": 9.0,
                    "before": b.tolist(), "after": a.tolist()})
        assert LPDrive(fab).signal("g1") == [], (
            "sigma-less records must contribute NOTHING -- the LP arm's clock "
            "restart at the characterization boundary is this inertness")

    def test_signal_scores_the_characterized_record(self, tmp_path):
        from engines.egocentric.lp_drive import LPDrive
        fab = KnowledgeFabric(str(tmp_path / "new"), agent_id="a", kin_key="v4")
        b, a = _pocket_pair()
        fab.append("collective", "import_queue", _new_format(b, a, residual=9.0))
        sig = LPDrive(fab).signal("g1")
        assert len(sig) == 1 and sig[0]["bbox"] == [1, 1, 2, 2], (
            "a characterized pocket residual must be scoreable from its patches")
        assert sig[0]["weight"] > 0.0

    def test_sigma_only_record_is_inert_but_never_crashes(self, tmp_path):
        """An oversized residual persists sigma WITHOUT patches: readable by
        the consumer, silently unscoreable by the LP drive (no evidence)."""
        con = _characterize()
        from engines.egocentric.lp_drive import LPDrive
        fab = KnowledgeFabric(str(tmp_path / "big"), agent_id="a", kin_key="v4")
        b, a = _oversized_pair()
        rec = {"slot": "WORKSPACE", "residual": 2.0}
        rec.update(con.characterize(b, a, slot="WORKSPACE", residual=2.0))
        fab.append("collective", "import_queue", rec)
        drv = LPDrive(fab)
        assert drv.signal("g1") == [] and drv.errors == 0
