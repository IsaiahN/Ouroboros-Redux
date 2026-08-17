"""GATE: THE RANKED DRAIN + ITS OFF-ARM (PREREG_DRAIN_ORIGIN.md §A).

⭐ WHY: THE_LADDER.md's "CORRECTION TO THE TALLY READING" located rung 4's zero in
QUEUE ORDER, not in description: 388,184 queue records, 82,301 carrying a COMPLETE
sigma -- and consume() drained OLDEST-FIRST at budget_n=8 through a ~370k
PRE-CHARACTERIZATION backlog whose {slot,residual,seq} records can only produce a
frame-free sigma, so 100% of declines were residual-side-incomplete BY CONSTRUCTION
and the complete descriptions sat ~46,000 episodes away at the back.

THE BUILD: consume()'s PHASE-2 agenda is a bounded RANKED selection instead of FIFO --
  (1) CHARACTERIZED FIRST (a complete sigma: all 5 INVARIANTS present)
  (2) then LARGEST RESIDUAL (most unexplained first)
  (3) then RECENCY (newest first) as the tiebreak
ranked over a BOUNDED WINDOW of the newest DRAIN_WINDOW pending records (KNOBS G21,
Register G, GUESSED) -- never a sort of the whole 370k queue.

THE OFF-ARM IS THE POINT (CLAIM.md's ablation constraint: "a toggle is not a toggle
until something has run with it off"). DRAIN_RANKED=0 reproduces oldest-first
BYTE-IDENTICALLY -- the same records, in the same order, with the same outcomes, on
disk -- and that is asserted HERE, at ship, against a literal FIFO reference path.

FALSIFIERS (all failing before the build):
  * an old sigma-less + newer characterized queue drains CHARACTERIZED FIRST ranked,
    OLDEST FIRST under DRAIN_RANKED=0;
  * declines on characterized records are ZERO;
  * the off-arm's on-disk streams are byte-identical to the FIFO reference's;
  * the window BOUND holds: a characterized record older than the window is NOT
    preferred (a whole-queue sort would find it -- that is the bound's falsifier);
  * the registry row carries the receipt.

Run pre-build: FAILED (module had no DRAIN_RANKED / DRAIN_WINDOW / _drain_order;
consume() drained `pending(fabric)` verbatim).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric.fabric import KnowledgeFabric

QUEUE_TOPIC = "import_queue"
GAME, LEVEL = "g_home", 2


# ── fixtures ─────────────────────────────────────────────────────────────────

def _recolour(n=5, cell=(2, 2), src=2, dst=3):
    b = np.full((n, n), src, dtype=int)
    a = b.copy()
    a[cell] = dst
    return b, a


def _fab(root, agent="agentH", kin="kinH"):
    return KnowledgeFabric(str(root), seeds=[], agent_id=agent, kin_key=kin)


def _put_atom(fabric, game, key, sigma):
    """A source atom carrying a COMPLETE sigma -- so a decline can only ever be
    caused by the RESIDUAL side (the live 5,632/5,632 pattern)."""
    return fabric.append("collective", "atoms", {
        "id": "%s:0" % key, "type": "structural", "game": str(game), "level": 1,
        "atom": {"kind": "EFFECT", "arity": 2, "key": str(key),
                 "sigma": dict(sigma)}})


def _enqueue_legacy(fabric, slot, residual):
    """THE PRE-FIX RAW RECORD, verbatim shape: {slot, residual} + game/level and
    NO frames -- describe() can only recompute the frame-free subset."""
    return fabric.append("collective", QUEUE_TOPIC, {
        "slot": str(slot), "residual": float(residual),
        "game": GAME, "level": LEVEL})


def _enqueue_characterized(fabric, slot, residual, cell=(2, 2)):
    """A Fig-9 CHARACTERIZED record: the W4c-4 persist site's shape (sigma at
    enqueue time + bounded patches)."""
    b, a = _recolour(cell=cell)
    rec = {"slot": str(slot), "residual": float(residual),
           "game": GAME, "level": LEVEL}
    rec.update(consumer.characterize(b, a, slot=slot, residual=residual))
    return fabric.append("collective", QUEUE_TOPIC, rec)


def _books(root, n_old=6, n_new=3):
    """OLD sigma-less records first (the backlog), NEWER characterized ones at the
    BACK -- the live geometry in miniature. Residuals ascend on the old ones so a
    residual-only ranking cannot pass this test by accident."""
    fab = _fab(root)
    b, a = _recolour()
    _put_atom(fab, "gSRC", "k-match", consumer.sigma_of(b, a))
    old = [_enqueue_legacy(fab, "OLD%d" % i, 10.0 + i) for i in range(n_old)]
    new = [_enqueue_characterized(fab, "NEW%d" % i, 1.0 + i) for i in range(n_new)]
    return fab, [int(r["seq"]) for r in old], [int(r["seq"]) for r in new]


def _drained_seqs(fabric):
    """The src_seq of every record the pass actually drained, IN DRAIN ORDER (the
    "sigma" processing entries are written one per drained raw, in order)."""
    return [int(r.get("src_seq", -1))
            for r in fabric.query("collective", QUEUE_TOPIC)
            if r.get("kind") == "sigma"]


def _stream_bytes(root, topic):
    path = os.path.join(str(root), "collective", "%s.jsonl" % topic)
    if not os.path.isfile(path):
        return b""
    with open(path, "rb") as fh:
        return fh.read()


# ── (1) the ranked arm: characterized first ──────────────────────────────────

class TestRankedArm:

    def test_characterized_records_drain_first(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        fab, old, new = _books(tmp_path / "ranked")
        rep = consumer.consume(fab, GAME, LEVEL, 3)
        assert rep["drained"] == 3
        assert _drained_seqs(fab) == sorted(new, reverse=True), (
            "the ranked drain must take the CHARACTERIZED records first "
            "(newest-first inside the tier), not the oldest raws")

    def test_characterized_records_reach_a_verdict_and_are_never_declined(
            self, tmp_path, monkeypatch):
        """The prereg's second falsifier: declines on characterized records are
        ZERO. A complete residual sigma against complete atom sigmas can hit or
        miss -- it can never be refused by the completeness guard."""
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        fab, old, new = _books(tmp_path / "verdict")
        rep = consumer.consume(fab, GAME, LEVEL, 3)
        assert rep["declined"] == 0, (
            "a characterized record cannot be declined at the completeness "
            "guard -- got %d declines" % rep["declined"])
        assert rep["candidates"] == 3, "each characterized record matched an atom"
        for row in fab.query("collective", QUEUE_TOPIC):
            if row.get("kind") == consumer.KIND_DECLINED:
                sig = row.get("sigma") or {}
                assert not all(k in sig for k in consumer.INVARIANTS), (
                    "a DECLINE was recorded against a COMPLETE sigma: %r" % sig)

    def test_largest_residual_then_recency_inside_the_tier(self, tmp_path,
                                                           monkeypatch):
        """Key (2) then (3): among characterized records the LARGEST RESIDUAL
        goes first; equal residuals fall back to NEWEST."""
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        fab = _fab(tmp_path / "tier")
        b, a = _recolour()
        _put_atom(fab, "gSRC", "k-match", consumer.sigma_of(b, a))
        small = int(_enqueue_characterized(fab, "SMALL", 1.0)["seq"])
        big = int(_enqueue_characterized(fab, "BIG", 9.0)["seq"])
        tie_a = int(_enqueue_characterized(fab, "TIE_A", 5.0)["seq"])
        tie_b = int(_enqueue_characterized(fab, "TIE_B", 5.0)["seq"])
        consumer.consume(fab, GAME, LEVEL, 4)
        assert _drained_seqs(fab) == [big, tie_b, tie_a, small], (
            "rank = largest residual, then newest on ties")


# ── (2) the off-arm: oldest-first, byte-identical ────────────────────────────

class TestOffArm:

    def test_off_arm_drains_oldest_first(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DRAIN_RANKED", "0")
        fab, old, new = _books(tmp_path / "off")
        rep = consumer.consume(fab, GAME, LEVEL, 3)
        assert _drained_seqs(fab) == old[:3], (
            "DRAIN_RANKED=0 must reproduce the FIFO agenda exactly")
        assert rep["declined"] == 3, (
            "the off-arm reproduces the BASELINE PATHOLOGY: frame-free legacy "
            "records refused at the completeness guard")
        assert rep["candidates"] == 0

    def test_off_arm_order_is_pending_verbatim(self, tmp_path, monkeypatch):
        """The off-arm does not merely agree with FIFO -- it IS pending(),
        element for element (nothing is reordered, dropped, or re-wrapped)."""
        monkeypatch.setenv("DRAIN_RANKED", "0")
        fab, old, new = _books(tmp_path / "verbatim")
        assert consumer._drain_order(fab) == consumer.pending(fab)
        assert [int(r["seq"]) for r in consumer._drain_order(fab)] == old + new

    def test_off_arm_streams_are_byte_identical_to_a_fifo_reference(
            self, tmp_path, monkeypatch):
        """THE TOGGLE RECEIPT (CLAIM.md): two identical books; one drained with
        DRAIN_RANKED=0, the other drained by the LITERAL pre-change expression
        (`for raw in pending(fabric)`). Every on-disk stream must match byte for
        byte -- same records, same order, same outcomes."""
        off_root = tmp_path / "arm_off"
        ref_root = tmp_path / "arm_ref"
        off_fab, _, _ = _books(off_root)
        ref_fab, _, _ = _books(ref_root)
        assert _stream_bytes(off_root, QUEUE_TOPIC) == _stream_bytes(
            ref_root, QUEUE_TOPIC), "the two fixtures must start identical"

        monkeypatch.setenv("DRAIN_RANKED", "0")
        off_rep = consumer.consume(off_fab, GAME, LEVEL, 4)
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        monkeypatch.setattr(consumer, "_drain_order", consumer.pending)
        ref_rep = consumer.consume(ref_fab, GAME, LEVEL, 4)

        assert off_rep == ref_rep, "same outcomes: %r vs %r" % (off_rep, ref_rep)
        for topic in (QUEUE_TOPIC, "import_candidates", "rho_readings", "atoms"):
            assert _stream_bytes(off_root, topic) == _stream_bytes(
                ref_root, topic), (
                "off-arm stream %r is NOT byte-identical to the FIFO "
                "reference -- the ablation clause is unmet" % topic)

    @pytest.mark.parametrize("value", ["0", "false", "off", "no"])
    def test_off_arm_words(self, tmp_path, monkeypatch, value):
        monkeypatch.setenv("DRAIN_RANKED", value)
        fab, old, _ = _books(tmp_path / ("w" + value))
        consumer.consume(fab, GAME, LEVEL, 2)
        assert _drained_seqs(fab) == old[:2]

    def test_module_flag_is_the_second_lever(self, tmp_path, monkeypatch):
        """`or module flag`: with the env unset the module constant decides."""
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        monkeypatch.setattr(consumer, "DRAIN_RANKED", False)
        fab, old, _ = _books(tmp_path / "flag")
        consumer.consume(fab, GAME, LEVEL, 2)
        assert _drained_seqs(fab) == old[:2]

    def test_env_outranks_the_module_flag(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DRAIN_RANKED", "1")
        monkeypatch.setattr(consumer, "DRAIN_RANKED", False)
        fab, old, new = _books(tmp_path / "envwins")
        consumer.consume(fab, GAME, LEVEL, 1)
        assert _drained_seqs(fab) == [max(new)]


# ── (3) the bound: a window, never a whole-queue sort ────────────────────────

class TestWindowBound:

    def test_window_is_bounded(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        fab = _fab(tmp_path / "bound")
        b, a = _recolour()
        _put_atom(fab, "gSRC", "k-match", consumer.sigma_of(b, a))
        for i in range(consumer.DRAIN_WINDOW + 20):
            _enqueue_legacy(fab, "OLD%d" % i, 1.0)
        assert len(consumer._drain_order(fab)) == consumer.DRAIN_WINDOW, (
            "the ranked agenda must be bounded by DRAIN_WINDOW -- a whole-queue "
            "sort is exactly what this build refuses")

    def test_a_characterized_record_older_than_the_window_is_not_reached(
            self, tmp_path, monkeypatch):
        """THE BOUND'S FALSIFIER: one characterized record sits at the very
        FRONT, outside the newest-DRAIN_WINDOW window. A whole-queue sort would
        promote it; a bounded scan must not see it at all."""
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        fab = _fab(tmp_path / "outside")
        b, a = _recolour()
        _put_atom(fab, "gSRC", "k-match", consumer.sigma_of(b, a))
        buried = int(_enqueue_characterized(fab, "BURIED", 99.0)["seq"])
        for i in range(consumer.DRAIN_WINDOW + 20):
            _enqueue_legacy(fab, "OLD%d" % i, 1.0)
        rep = consumer.consume(fab, GAME, LEVEL, 4)
        assert buried not in _drained_seqs(fab), (
            "a record OUTSIDE the window was ranked -- the scan is unbounded")
        assert rep["candidates"] == 0 and rep["declined"] == 4


# ── (4) old books still load ─────────────────────────────────────────────────

class TestCompat:

    def test_seqless_and_malformed_records_degrade_never_raise(self, tmp_path,
                                                               monkeypatch):
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        fab = _fab(tmp_path / "compat")
        fab.append("collective", QUEUE_TOPIC, {"slot": "S"})          # no residual
        fab.append("collective", QUEUE_TOPIC, {"residual": "not-a-number"})
        fab.append("collective", QUEUE_TOPIC, {"slot": "T", "residual": None})
        rep = consumer.consume(fab, GAME, LEVEL, 8)
        assert rep["drained"] == 3


# ── (5) the registry receipt ─────────────────────────────────────────────────

class TestRegistryReceipt:

    def _row(self, name):
        path = os.path.join(REPO, "WIRING_REGISTRY.md")
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith("| %s |" % name):
                    return [c.strip() for c in line.strip().strip("|").split("|")]
        return None

    def test_drain_ranked_row_is_live_with_a_consume_receipt(self):
        row = self._row("drain-ranked")
        assert row is not None, "no drain-ranked row in WIRING_REGISTRY.md"
        assert row[3] == "LIVE", "the ranked drain ships LIVE (got %r)" % row[3]
        assert "consumer:_drain_order" in row[1]
        assert "consumer.py" in row[2]

    def test_knobs_registers_the_window_as_guessed(self):
        with open(os.path.join(REPO, "KNOBS.md"), encoding="utf-8") as fh:
            text = fh.read()
        assert "DRAIN_WINDOW" in text and "DRAIN_RANKED" in text, (
            "the ranked drain's knob row is missing from KNOBS.md")
        row = [ln for ln in text.splitlines() if "DRAIN_WINDOW" in ln]
        assert any("GUESSED" in ln for ln in row), (
            "the window size must carry its GUESSED provenance (A5)")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
