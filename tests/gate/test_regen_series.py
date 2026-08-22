"""ITEM-3 GATE: THE REGENERATION SERIES -- within-fabric rho drift over time.

WHY (THE_LADDER.md, THE REPORT FORMAT rider 2): "THE RATIO HAS ONE TERM --
rho_readings gives crossing-spend; REGENERATION RATE (rho drift over time within
a fabric vs its own ground) needs a time series NOBODY COLLECTS, so the
roving-pool gate fires with one term missing unless the series starts." This is
the collector. It computes nothing about the gate; it makes the gate's second
term COMPUTABLE by putting successive self-comparisons in the books.

THE DESIGN CONSTRAINTS, each with a falsifier below:
  * SELF-rho, not cross-rho: fabric-now vs THE SAME FABRIC AT ITS LAST SNAPSHOT,
    at every rung of the identity ladder (rho.rho_at 0/1/2) -- so a drift that
    only key identity sees, or only the coarsened sigma sees, is not averaged away.
  * NO WALL CLOCK IN THE RECORD: a time series whose index is the sampler's
    clock is a latent (EVICTION SPEC RIDER 1, the same defect class). Any stamp
    is PASSED IN; absent one, the record's only ordinal is its own seq.
  * BOUNDED: capped atoms per fabric, capped digest per rung -- and truncation
    is FLAGGED in the record, never silent.
  * READ-ONLY ON FABRICS and IDEMPOTENT-SAFE: re-invocation appends a
    well-formed snapshot (drift 0.0 on an unchanged fabric), never rewrites,
    never loses a prior line, never raises on a torn tail.

Run pre-build: every test here FAILED (tools/regen_series.py did not exist).
"""
from __future__ import annotations

import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import rho  # noqa: E402
from tools import regen_series as rs  # noqa: E402
from tools.wiring_receipts import (  # noqa: E402
    build_index,
    parse_file,
    parse_site,
)

# ── synthetic fabrics (two epochs) ───────────────────────────────────────────

def _sig(i):
    return {"arity": 2, "bbox": "cell", "changed": "1",
            "colour_delta": [[int(i), int(i) + 1]], "conserved": False,
            "mag": "small"}


def _rec(game, key, i, ttype="TRANSLATE", params=None):
    return {"id": "%s:0" % key, "type": "structural", "game": game, "level": 1,
            "atom": {"kind": "EFFECT", "arity": 2, "key": str(key),
                     "sigma": _sig(i), "ttype": ttype,
                     "params": params if params is not None else {"dx": int(i)}}}


def _fabric(root, name, recs, game="gg11-deadbeef"):
    d = os.path.join(str(root), name, "ego_fabric", "collective")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "atoms.jsonl"), "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    return d


def _grow(dirpath, recs):
    """APPEND-ONLY growth: the evidence-only-added law -- an epoch adds atoms."""
    with open(os.path.join(dirpath, "atoms.jsonl"), "a", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


def _rewrite(dirpath, recs):
    """A COMPACTED epoch: the fabric is not append-only forever (the janitor
    rewrites it), and a refit can change an atom's params in place."""
    with open(os.path.join(dirpath, "atoms.jsonl"), "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


def _epoch1(root, game="gg11-deadbeef"):
    return _fabric(root, "gg11", [_rec(game, "k%d" % i, i) for i in range(4)], game)


def _lines(path):
    """The series' WELL-FORMED records: a torn tail is skipped on read, exactly
    as the collector skips it (and never rewrites it)."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            try:
                out.append(json.loads(raw))
            except ValueError:
                continue
    return out


@pytest.fixture()
def series(tmp_path):
    return str(tmp_path / "regen_series.jsonl")


# ── the append, and its monotonic seq ────────────────────────────────────────

class TestAppend:

    def test_one_snapshot_per_fabric_per_invocation(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        _fabric(root, "hh22", [_rec("hh22-feedface", "z0", 9)], "hh22-feedface")
        n = rs.regen_snapshot(str(root), series)
        assert n == 2, "one snapshot per fabric, per invocation"
        recs = _lines(series)
        assert {r["fabric"].split("/")[-3] for r in recs} == {"gg11", "hh22"}
        assert [r["seq"] for r in recs] == [1, 2]

    def test_seq_is_monotonic_across_invocations(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series)
        rs.regen_snapshot(str(root), series)
        rs.regen_snapshot(str(root), series)
        assert [r["seq"] for r in _lines(series)] == [1, 2, 3]

    def test_record_carries_game_and_atom_count(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series)
        rec = _lines(series)[0]
        assert rec["game"] == "gg11-deadbeef"
        assert rec["atoms"] == 4
        assert set(rec["classes"]) == {"r0", "r1", "r2"}

    def test_first_snapshot_has_no_drift_and_says_so(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series)
        rec = _lines(series)[0]
        assert rec["prev_seq"] is None
        assert rec["drift"] == {"r0": None, "r1": None, "r2": None}, (
            "no prior snapshot means no drift -- never 0.0, which would read "
            "as 'the fabric did not move'")


# ── the drift, between two synthetic epochs ──────────────────────────────────

class TestDrift:

    def test_drift_between_two_epochs_equals_one_minus_rho_at(self, tmp_path, series):
        """THE core assertion: the digest path the series stores must agree
        EXACTLY with rho.rho_at over the two epochs' atom records, at every
        rung. A cheaper approximation here would silently redefine the metric
        the roving-pool gate is supposed to price."""
        root = tmp_path / "swarm"
        game = "gg11-deadbeef"
        old = [_rec(game, "k%d" % i, i) for i in range(4)]
        d = _fabric(root, "gg11", old, game)
        rs.regen_snapshot(str(root), series)

        new = [_rec(game, "k%d" % i, i) for i in range(4, 7)]
        _grow(d, new)
        rs.regen_snapshot(str(root), series)

        rec = _lines(series)[1]
        assert rec["prev_seq"] == 1
        for rung in (0, 1, 2):
            expect = 1.0 - rho.rho_at(old + new, old, rung)
            assert rec["drift"]["r%d" % rung] == pytest.approx(expect), (
                "rung %d drift must be 1 - rho_at(now, last-snapshot)" % rung)
        assert rec["drift"]["r0"] > 0.0, "the fabric moved; the series must see it"

    def test_rung_split_survives_a_params_only_refit(self, tmp_path, series):
        """A refit that changes ONLY params moves rung 1 and nothing else:
        rung 0 (keys) and rung 2 (params dropped) must read 0.0 while rung 1
        reads the split. One averaged drift number would erase this -- the
        partition artifact the identity ladder exists to prevent, in time."""
        root = tmp_path / "swarm"
        game = "gg11-deadbeef"
        d = _fabric(root, "gg11", [_rec(game, "k0", 0, params={"dx": 1}),
                                   _rec(game, "k1", 0, params={"dx": 2})], game)
        rs.regen_snapshot(str(root), series)
        _rewrite(d, [_rec(game, "k0", 0, params={"dx": 1}),
                     _rec(game, "k1", 0, params={"dx": 1})])
        rs.regen_snapshot(str(root), series)
        drift = _lines(series)[1]["drift"]
        assert drift["r0"] == 0.0, "the same two keys: rung 0 sees no drift"
        assert drift["r2"] == 0.0, "params dropped: rung 2 sees no drift"
        assert drift["r1"] == pytest.approx(2.0 / 3.0), (
            "rung 1: {c(dx1):1, c(dx2):1} -> {c(dx1):2} is jaccard 1/3")

    def test_unchanged_fabric_drifts_zero(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series)
        rs.regen_snapshot(str(root), series)
        drift = _lines(series)[1]["drift"]
        assert drift == {"r0": 0.0, "r1": 0.0, "r2": 0.0}

    def test_drift_is_against_the_last_snapshot_not_the_first(self, tmp_path,
                                                              series):
        root = tmp_path / "swarm"
        game = "gg11-deadbeef"
        d = _fabric(root, "gg11", [_rec(game, "k0", 0)], game)
        rs.regen_snapshot(str(root), series)
        _grow(d, [_rec(game, "k1", 1)])
        rs.regen_snapshot(str(root), series)
        _grow(d, [_rec(game, "k2", 2)])
        rs.regen_snapshot(str(root), series)
        recs = _lines(series)
        assert recs[2]["prev_seq"] == 2
        # now={k0,k1,k2} vs last={k0,k1}: rung 0 weighted jaccard = 2/3
        assert recs[2]["drift"]["r0"] == pytest.approx(1.0 - 2.0 / 3.0)

    def test_sigma_less_atoms_degrade_never_raise(self, tmp_path, series):
        root = tmp_path / "swarm"
        d = _fabric(root, "gg11", [_rec("gg11-deadbeef", "k0", 0)])
        _grow(d, [{"id": "old:0", "game": "gg11-deadbeef",
                   "atom": {"kind": "EFFECT", "key": "legacy"}}])
        assert rs.regen_snapshot(str(root), series) == 1
        rec = _lines(series)[0]
        assert rec["atoms"] == 2 and rec["classes"]["r0"] == 2
        assert rec["classes"]["r1"] == 1, "the sigma-less atom takes no rung-1 vote"


# ── no wall clock ────────────────────────────────────────────────────────────

class TestNoWallClock:

    def test_record_has_no_timestamp_by_default(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series)
        rec = _lines(series)[0]
        assert rec["stamp"] is None
        blob = json.dumps(rec).lower()
        for word in ("time", "date", "clock", "utc", "epoch_ms"):
            assert word not in blob, (
                "a wall-clock index makes the series a latent (EVICTION SPEC "
                "RIDER 1); found %r in %r" % (word, rec))

    def test_stamp_is_passed_in_and_stored_verbatim(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series, stamp="beat-29")
        assert _lines(series)[0]["stamp"] == "beat-29"

    def test_module_never_reads_the_clock(self):
        src = open(os.path.join(REPO, "tools", "regen_series.py"),
                   encoding="utf-8").read()
        for banned in ("time.time(", "datetime.now", "utcnow", "time.monotonic",
                       "datetime('now')"):
            assert banned not in src, (
                "the collector must never read the clock: %r" % banned)


# ── bounded ──────────────────────────────────────────────────────────────────

class TestBounded:

    def test_atom_cap_is_honoured_and_flagged(self, tmp_path, series):
        root = tmp_path / "swarm"
        _fabric(root, "gg11", [_rec("gg11-deadbeef", "k%d" % i, i)
                               for i in range(20)])
        rs.regen_snapshot(str(root), series, max_atoms=5)
        rec = _lines(series)[0]
        assert rec["atoms"] == 5 and rec["atoms_truncated"] is True

    def test_digest_cap_is_honoured_and_flagged(self, tmp_path, series):
        root = tmp_path / "swarm"
        _fabric(root, "gg11", [_rec("gg11-deadbeef", "k%d" % i, i)
                               for i in range(10)])
        rs.regen_snapshot(str(root), series, max_digest=3)
        rec = _lines(series)[0]
        assert all(len(rec["digest"][r]) <= 3 for r in ("r0", "r1", "r2"))
        assert rec["digest_truncated"] is True

    def test_untruncated_snapshots_say_so(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series)
        rec = _lines(series)[0]
        assert rec["atoms_truncated"] is False and rec["digest_truncated"] is False

    def test_fabric_cap_is_honoured(self, tmp_path, series):
        root = tmp_path / "swarm"
        for i in range(5):
            _fabric(root, "g%d" % i, [_rec("g%d-x" % i, "k", i)], "g%d-x" % i)
        assert rs.regen_snapshot(str(root), series, max_fabrics=2) == 2


# ── read-only + idempotent-safe ──────────────────────────────────────────────

class TestSafety:

    def test_fabrics_are_never_written(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        before = {}
        for base, _d, files in os.walk(root):
            for f in files:
                p = os.path.join(base, f)
                st = os.stat(p)
                before[p] = (st.st_size, st.st_mtime_ns)
        rs.regen_snapshot(str(root), series)
        rs.regen_snapshot(str(root), series)
        after = {}
        for base, _d, files in os.walk(root):
            for f in files:
                p = os.path.join(base, f)
                st = os.stat(p)
                after[p] = (st.st_size, st.st_mtime_ns)
        assert after == before, "the collector must not touch a fabric byte"

    def test_torn_tail_is_tolerated_and_preserved(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series)
        with open(series, "a", encoding="utf-8") as fh:
            fh.write('{"seq": 2, "fabric": "trunc')      # torn write
        rs.regen_snapshot(str(root), series)
        with open(series, encoding="utf-8") as fh:
            raw = fh.read()
        assert '{"seq": 2, "fabric": "trunc' in raw, (
            "the collector must never rewrite the file: prior bytes survive")
        good = _lines(series)
        assert [r["seq"] for r in good] == [1, 2]

    def test_dry_run_appends_nothing(self, tmp_path, series):
        root = tmp_path / "swarm"
        _epoch1(root)
        rs.regen_snapshot(str(root), series, dry_run=True)
        assert not os.path.exists(series)

    def test_missing_root_is_a_no_op_not_a_raise(self, tmp_path, series):
        assert rs.regen_snapshot(str(tmp_path / "nope"), series) == 0
        assert not os.path.exists(series)

    def test_main_runs_and_narrates(self, tmp_path, series, capsys):
        root = tmp_path / "swarm"
        _epoch1(root)
        rc = rs.main(["--root", str(root), "--out", series, "--stamp", "beat-29"])
        out = capsys.readouterr().out
        assert rc == 0 and "[REGEN]" in out
        assert _lines(series)[0]["stamp"] == "beat-29"


# ── the documented consumer ──────────────────────────────────────────────────

class TestDocumentedConsumer:

    def test_docstring_names_the_consumer_and_the_missing_term(self):
        doc = (rs.__doc__ or "")
        assert "roving-pool" in doc, "a produced stream needs a NAMED consumer"
        assert "one term" in doc or "two terms" in doc
        assert "beat" in doc, "invocation site: the beat-read protocol"


# ── the registry row (rung 0c) ───────────────────────────────────────────────

def _registry_row(name):
    path = os.path.join(REPO, "WIRING_REGISTRY.md")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip().startswith("| %s |" % name):
                return [c.strip() for c in line.strip().strip("|").split("|")]
    return None


class TestRegistryRow:

    def test_regen_series_row_exists_as_an_instrument(self):
        row = _registry_row("regen-series")
        assert row is not None, (
            "rung 0c: a new organ with no registry receipt is UNSHIPPABLE")
        _name, symbol, site, status, date, note = row
        assert symbol == "tools.regen_series:regen_snapshot"
        assert site.startswith("tools/regen_series.py:")
        assert status in ("LIVE", "SEVERED", "DELETED-PENDING")
        assert date.startswith("2026-")
        assert "[instrument]" in note
        assert "beat protocol" in note and "THE_LADDER" in note
        assert "roving-pool" in note, "the consumer is named in the receipt"

    def test_registry_receipt_line_exists(self):
        """UPDATED 2026-08-21 (PREREG_SYMBOL_RECEIPTS.md §1): the site cell is a
        SYMBOL FINGERPRINT, not a line, so `rsplit(":", 1)` no longer yields a
        path and an integer. The old body read ±6 lines around the claimed line
        and looked for the substring 'regen_snapshot' -- the region-substring proxy that
        let four rows in this registry assert nothing at all. The claim now IS
        the symbol: the cell must name regen_snapshot and the node it names must exist
        where the cell says."""
        row = _registry_row("regen-series")
        site = parse_site(row[2])
        assert site.fingerprinted, "row still on the old position form: %r" % row[2]
        assert site.name == "regen_snapshot", (
            "the receipt does not name regen_snapshot: %r" % row[2])
        full = os.path.join(REPO, site.file)
        assert os.path.exists(full)
        index, _quals = build_index(parse_file(full))
        nodes = index.get((site.enclosing, site.kind, site.name)) or []
        assert len(nodes) > site.ordinal, (
            "the claimed %s #%d of regen_snapshot inside %r does not exist in %s"
            % (site.kind, site.ordinal, site.enclosing, site.file))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
