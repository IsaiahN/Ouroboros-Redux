"""GATE: THE DEAD-CELL DEDUP + ITS OFF-ARM (PREREG_DEAD_DEDUP.md, audit F-3).

⭐ WHY: frontier.py documents the dead set as ">=2 INDEPENDENT records" and the code
increments ONCE PER LIST ENTRY, while the caller banks the per-episode dead list
VERBATIM. So ONE episode clicking a cell twice blacklists it forever. MEASURED on the
live ar25 books: level-2 dead(as coded)=163 vs dead(as documented)=41 -- 122 cells
(75%) blacklisted by within-episode repeats alone. Nothing decays it (no recency term,
the janitor never ran), so the elimination is MONOTONE across every future episode.

THE BUILD -- count DISTINCT RECORDS, not list entries, at BOTH ends:
  (a) WRITE: record_harvest dedups the per-episode dead list before banking, so one
      episode contributes AT MOST ONE report per cell (first-seen order preserved);
  (b) READ: load_harvest counts DISTINCT RECORDS per cell, so the ~370k of
      already-banked history is corrected AT READ TIME -- no stored evidence is
      deleted or rewritten (the archive law: evidence is added, never replaced).
The >=2 THRESHOLD ITSELF IS UNCHANGED (KNOBS F8: evidence semantics, not a dial), and
the effects-set-outranks-dead rule is UNCHANGED.

THE OFF-ARM IS THE POINT (CLAIM.md's ablation constraint: "a toggle is not a toggle
until something has run with it off"). DEAD_DEDUP=0 reproduces the per-entry counting
BYTE-IDENTICALLY at BOTH ends -- the same bytes on disk from the write side, the same
returned sets from the read side -- asserted HERE, at ship.

FALSIFIERS (all failing before the build):
  * an episode clicking ONE cell 5x contributes ONE report, not 5;
  * a cell needs >=2 DISTINCT RECORDS to be banked dead (5x in one episode is not
    two independent reports);
  * an effect report still outranks any number of dead reports;
  * REAL-SHAPED LEGACY records (already on disk, dead list carrying duplicates) read
    back at the DOCUMENTED count, not the inflated one -- without touching the file;
  * an ar25-L2-shaped legacy fixture's corrected count is MATERIALLY LOWER;
  * the off-arm reproduces the inflated counting byte-identically at both ends;
  * the registry row carries the receipt.

Run pre-build: FAILED (frontier had no DEAD_DEDUP / _dead_dedup_enabled;
record_harvest banked the list verbatim and load_harvest counted per entry).
"""
from __future__ import annotations

import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import frontier  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402

HARVEST_TOPIC = "frontier_harvest"
GAME, LEVEL = "g_dead", 2


# ── fixtures ─────────────────────────────────────────────────────────────────

def _book(root, agent="agentD", kin="kinD"):
    return frontier.FrontierBook(
        KnowledgeFabric(str(root), seeds=[], agent_id=agent, kin_key=kin))


def _stream_path(root, topic=HARVEST_TOPIC):
    return os.path.join(str(root), "collective", "%s.jsonl" % topic)


def _stream_bytes(root, topic=HARVEST_TOPIC):
    path = _stream_path(root, topic)
    if not os.path.isfile(path):
        return b""
    with open(path, "rb") as fh:
        return fh.read()


def _banked_dead(root):
    """The dead lists AS STORED, in record order (the write-side observable)."""
    out = []
    for line in _stream_bytes(root).decode("utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line).get("dead"))
    return out


def _legacy_append(book, game, level, dead, effects=(), fatal=None):
    """A record written the PRE-FIX way: the dead list VERBATIM, duplicates and
    all -- i.e. exactly the ~370k records already on disk. Bypasses the write
    side on purpose, so the READ side is tested against real legacy shapes."""
    book.fabric.append("collective", HARVEST_TOPIC, {
        "game": str(game), "level": int(level),
        "dead": [[int(c[0]), int(c[1])] for c in dead],
        "effects": [[int(c[0]), int(c[1])] for c in effects],
        "fatal": ([int(fatal[0]), int(fatal[1])] if fatal is not None else None),
        "deltas": {},
    })


# ── (1) the write side: one episode = one report per cell ────────────────────

class TestTheWriteSide:

    def test_one_episode_clicking_one_cell_five_times_banks_one_report(
            self, tmp_path):
        """⭐ FALSIFIER 1. Five clicks in ONE episode are ONE observation of one
        cell -- not five independent reports."""
        root = tmp_path / "w1"
        b = _book(root)
        b.record_harvest(GAME, LEVEL, dead=[(3, 3)] * 5, effects=[], fatal=None)
        assert _banked_dead(root) == [[[3, 3]]], (
            "the per-episode dead list was banked verbatim -- one episode still "
            "counts as five independent records")

    def test_dedup_preserves_first_seen_order_and_distinct_cells(self, tmp_path):
        root = tmp_path / "w2"
        b = _book(root)
        b.record_harvest(GAME, LEVEL,
                         dead=[(9, 9), (1, 1), (9, 9), (2, 2), (1, 1)],
                         effects=[], fatal=None)
        assert _banked_dead(root) == [[[9, 9], [1, 1], [2, 2]]], (
            "dedup must be first-seen order-preserving (deterministic), not a set")

    def test_two_episodes_still_make_a_cell_dead(self, tmp_path):
        """The threshold is UNCHANGED: dedup must not make cells un-blacklistable."""
        b = _book(tmp_path / "w3")
        b.record_harvest(GAME, LEVEL, dead=[(4, 4), (4, 4)], effects=[], fatal=None)
        b.record_harvest(GAME, LEVEL, dead=[(4, 4)], effects=[], fatal=None)
        assert (4, 4) in b.load_harvest(GAME, LEVEL)["dead"]

    def test_effects_and_fatal_are_untouched_by_the_dedup(self, tmp_path):
        """SCOPE: the build changes the DEAD list only. Effects/fatal/deltas keep
        their existing semantics and their existing bytes."""
        root = tmp_path / "w4"
        b = _book(root)
        b.record_harvest(GAME, LEVEL, dead=[(1, 1)], effects=[(2, 2), (2, 2)],
                         fatal=(7, 7), deltas={"1": (0, 1)})
        rec = json.loads(_stream_bytes(root).decode("utf-8").splitlines()[0])
        assert rec["effects"] == [[2, 2], [2, 2]], (
            "effects must be banked verbatim -- this build touches dead only")
        assert rec["fatal"] == [7, 7] and rec["deltas"] == {"1": [0, 1]}


# ── (2) the read side: distinct RECORDS, on history already banked ───────────

class TestTheReadSide:

    def test_a_cell_needs_two_distinct_records(self, tmp_path):
        """⭐ FALSIFIER 2. Five entries inside ONE legacy record are ONE report."""
        b = _book(tmp_path / "r1")
        _legacy_append(b, GAME, LEVEL, [(5, 5)] * 5)
        assert b.load_harvest(GAME, LEVEL)["dead"] == set(), (
            "one record blacklisted a cell -- '>=2 INDEPENDENT records' is still "
            "counting list entries")
        _legacy_append(b, GAME, LEVEL, [(5, 5)])
        assert b.load_harvest(GAME, LEVEL)["dead"] == {(5, 5)}, (
            "the >=2 threshold itself must be UNCHANGED (KNOBS F8)")

    def test_legacy_records_are_corrected_without_being_rewritten(self, tmp_path):
        """⭐ FALSIFIER 4 + THE ARCHIVE LAW. A real-shaped legacy record (dead
        list carrying duplicates) reads back at the DOCUMENTED count -- and the
        bytes on disk are IDENTICAL before and after the read."""
        root = tmp_path / "r2"
        b = _book(root)
        _legacy_append(b, GAME, LEVEL, [(1, 1), (1, 1), (2, 2), (1, 1), (2, 2)])
        _legacy_append(b, GAME, LEVEL, [(2, 2), (2, 2)])
        before = _stream_bytes(root)
        h = b.load_harvest(GAME, LEVEL)
        assert h["dead"] == {(2, 2)}, (
            "(1,1) appears 3x in ONE record and (2,2) in TWO records: only (2,2) "
            "has two independent reports")
        assert (1, 1) in h["tried"], "tried is still the union of every reported cell"
        assert _stream_bytes(root) == before, (
            "the read side rewrote stored evidence -- the archive law says evidence "
            "is ADDED, never replaced")

    def test_an_effect_report_still_outranks_dead(self, tmp_path):
        """⭐ FALSIFIER 3. The conservative rule is UNCHANGED by this build."""
        b = _book(tmp_path / "r3")
        _legacy_append(b, GAME, LEVEL, [(6, 6)] * 9)
        _legacy_append(b, GAME, LEVEL, [(6, 6)] * 9)
        assert (6, 6) in b.load_harvest(GAME, LEVEL)["dead"]
        _legacy_append(b, GAME, LEVEL, [], effects=[(6, 6)])
        h = b.load_harvest(GAME, LEVEL)
        assert (6, 6) not in h["dead"] and (6, 6) in h["effects"]

    def test_ar25_l2_shaped_books_read_materially_lower(self, tmp_path):
        """⭐ THE LIVE SHAPE, reproduced. The ar25 level-2 books: 32 legacy
        records over a 64x64 board, 553 distinct cells reported dead, 163 of them
        blacklisted by PER-ENTRY counting and 41 by the DOCUMENTED per-record
        rule. This fixture is built to that census -- a shared core every episode
        touches, a per-episode set clicked REPEATEDLY BY ONE EPISODE ONLY (the
        inflation), and single-click cells that are dead by neither rule.

        FIXTURE NOTE (this test failed once and the FIXTURE was the bug): an
        earlier version let consecutive episodes overlap, so nearly every cell
        genuinely appeared in >=2 records and both rules returned 16 -- a fixture
        that could not have shown the correction at all.
        """
        def cell(i):                                # distinct cells, 64x64 board
            return (i // 64, i % 64)

        b = _book(tmp_path / "r4")
        core = [cell(i) for i in range(41)]         # every episode touches these
        for ep in range(32):
            clicks = list(core)                     # once each: 32 records deep
            for j in range(4):                      # THIS episode's own cells,
                clicks.extend([cell(100 + ep * 4 + j)] * 3)   # clicked 3x
            clicks.extend(cell(1000 + ep * 12 + j) for j in range(12))  # once
            _legacy_append(b, GAME, LEVEL, clicks)

        per_entry = _dead_per_entry(b, GAME, LEVEL)
        h = b.load_harvest(GAME, LEVEL)
        assert len(h["tried"]) == 553, "the fixture must match the live census"
        assert len(per_entry) == 169, (
            "per-entry counting must reproduce the ~163 measured live")
        assert h["dead"] == set(core), (
            "only the cells reported by >=2 DISTINCT records are dead")
        assert len(h["dead"]) == 41, (
            "the documented count on the live-shaped books is 41 (measured: the "
            "real ar25 L2 books read 163 per-entry and 41 per-record)")
        assert len(h["dead"]) < len(per_entry) / 2, (
            "corrected dead=%d vs per-entry dead=%d -- the correction must be "
            "MATERIAL on live-shaped books" % (len(h["dead"]), len(per_entry)))


def _dead_per_entry(book, game, level):
    """The PRE-FIX reference computation, written out literally: increment once
    per LIST ENTRY, then apply the (unchanged) >=2 + not-in-effects rule."""
    counts, effects = {}, set()
    for rec in book.fabric.query(
            "collective", HARVEST_TOPIC,
            where=lambda r: (r.get("game") == str(game)
                             and r.get("level") == int(level)
                             and r.get("kind") != frontier.MOVE_KIND)):
        for c in rec.get("dead") or []:
            if len(c) == 2:
                cell = (int(c[0]), int(c[1]))
                counts[cell] = counts.get(cell, 0) + 1
        for c in rec.get("effects") or []:
            if len(c) == 2:
                effects.add((int(c[0]), int(c[1])))
    return {c for c, n in counts.items() if n >= 2 and c not in effects}


# ── (3) the off-arm: per-entry counting, byte-identical, BOTH ends ───────────

class TestTheOffArm:

    def test_off_arm_write_is_byte_identical_to_the_pre_fix_bank(
            self, tmp_path, monkeypatch):
        """⭐ FALSIFIER 5 (write end). Two identical books: one banked with
        DEAD_DEDUP=0, the other by the LITERAL pre-change expression. The
        frontier_harvest stream must match byte for byte."""
        off_root, ref_root = tmp_path / "arm_off", tmp_path / "arm_ref"
        off, ref = _book(off_root), _book(ref_root)
        dead = [(1, 1), (1, 1), (2, 2), (1, 1)]

        monkeypatch.setenv("DEAD_DEDUP", "0")
        off.record_harvest(GAME, LEVEL, dead=dead, effects=[(3, 3)], fatal=(4, 4),
                           deltas={"1": (0, 1)})
        monkeypatch.delenv("DEAD_DEDUP", raising=False)
        ref.fabric.append("collective", HARVEST_TOPIC, {
            "game": str(GAME), "level": int(LEVEL),
            "dead": [[int(c[0]), int(c[1])] for c in dead],
            "effects": [[3, 3]], "fatal": [4, 4], "deltas": {"1": [0, 1]},
        })
        assert _stream_bytes(off_root) == _stream_bytes(ref_root), (
            "DEAD_DEDUP=0 did not reproduce the pre-fix bank byte-identically -- "
            "the ablation clause is unmet")

    def test_off_arm_read_reproduces_the_inflated_count(
            self, tmp_path, monkeypatch):
        """⭐ FALSIFIER 5 (read end). With the toggle off, ONE record's repeats
        blacklist a cell again -- exactly the measured harm, reproducible."""
        b = _book(tmp_path / "arm_read")
        _legacy_append(b, GAME, LEVEL, [(8, 8)] * 5)
        assert b.load_harvest(GAME, LEVEL)["dead"] == set()
        monkeypatch.setenv("DEAD_DEDUP", "0")
        assert b.load_harvest(GAME, LEVEL)["dead"] == {(8, 8)}, (
            "the off-arm must restore per-entry counting exactly")

    def test_off_arm_read_equals_the_literal_pre_fix_computation(
            self, tmp_path, monkeypatch):
        """Not merely 'inflated' -- IDENTICAL to the pre-change code path on
        live-shaped books, cell for cell."""
        b = _book(tmp_path / "arm_ref_read")
        for ep in range(6):
            _legacy_append(b, GAME, LEVEL,
                           [(ep, ep)] * 3 + [(1, 1), (1, 1)] + [(2, 2)],
                           effects=[(3, 3)] if ep == 0 else [])
        monkeypatch.setenv("DEAD_DEDUP", "0")
        assert (b.load_harvest(GAME, LEVEL)["dead"]
                == _dead_per_entry(b, GAME, LEVEL))

    @pytest.mark.parametrize("value", ["0", "false", "off", "no", ""])
    def test_every_off_word_disables(self, tmp_path, monkeypatch, value):
        b = _book(tmp_path / ("off_" + (value or "empty")))
        _legacy_append(b, GAME, LEVEL, [(8, 8), (8, 8)])
        monkeypatch.setenv("DEAD_DEDUP", value)
        assert b.load_harvest(GAME, LEVEL)["dead"] == {(8, 8)}

    def test_env_outranks_the_module_flag(self, tmp_path, monkeypatch):
        """The same precedence as DRAIN_RANKED/CORPSE_GUARD: env wins when set."""
        b = _book(tmp_path / "prec")
        _legacy_append(b, GAME, LEVEL, [(8, 8), (8, 8)])
        monkeypatch.setattr(frontier, "DEAD_DEDUP", False)
        assert b.load_harvest(GAME, LEVEL)["dead"] == {(8, 8)}
        monkeypatch.setenv("DEAD_DEDUP", "1")
        assert b.load_harvest(GAME, LEVEL)["dead"] == set()

    def test_the_on_arm_is_the_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DEAD_DEDUP", raising=False)
        assert frontier.DEAD_DEDUP is True
        assert frontier._dead_dedup_enabled() is True


# ── (4) containment + the receipt ────────────────────────────────────────────

class TestContainmentAndReceipt:

    def test_garbage_never_raises(self, tmp_path):
        """House law: the book must never crash the loop it advises."""
        b = _book(tmp_path / "junk")
        b.record_harvest(GAME, LEVEL, dead=[(1,), None, "x", (2, 2)])
        assert isinstance(b.load_harvest(GAME, LEVEL), dict)
        assert b.errors >= 0

    def test_registry_row_carries_the_receipt(self):
        reg = open(os.path.join(REPO, "WIRING_REGISTRY.md"),
                   encoding="utf-8", errors="replace").read()
        row = [ln for ln in reg.splitlines() if ln.startswith("| harvest |")]
        assert row, "the harvest row vanished from the wiring registry"
        assert "DEAD_DEDUP" in row[0], (
            "the harvest row must carry the dedup toggle receipt (CLAIM.md)")

    def test_knobs_registers_the_toggle(self):
        knobs = open(os.path.join(REPO, "KNOBS.md"),
                     encoding="utf-8", errors="replace").read()
        assert "DEAD_DEDUP" in knobs, "the toggle is unregistered (KNOBS Register G)"
        assert ">= 2 independent reports" in knobs, (
            "F8 (the >=2 rule) must remain frozen and stated")
