"""ITEM-2 GATE: THE EFFICIENCY READ -- distance-to-that-player, per game+level.

WHY (record/canon/THE_GOALS.md, SEAT 2 SEQUENCING #2 + ITEM-2 QUALIFICATION): the replay
reference counts sit on disk unused, so rung 0 (record/canon/THE_LADDER.md: levels_completed,
the only currency) reads a bare zero with NO RESOLUTION -- "closer without a
level" is currently unreadable. This instrument buys that resolution and NOTHING
else: it is REGISTERED READ, NEVER TARGET (no knob, no arm objective, until
levels move; RHAE is a ratio against a solution and is UNDEFINED AT ZERO
LEVELS -- optimizing it before solving optimizes a quantity that does not exist).

THE ONE-RUN LABEL (EXECUTION RIDER 2): the reference is a SINGLE win replay, not
an upper-median human distribution. The convention does the remembering, so the
label is carried BY THE INSTRUMENT on EVERY OUTPUT LINE -- asserted here, in
both the human and the JSON rendering. A close-looking number must not be
readable as "close to the bar".

FALSIFIERS: synthetic books with known reference/observed counts must produce
exactly the stated distances; a game with a reference and NO banked replay must
read NOT-MEASURABLE (never 0, never "unknown-as-good"); a game with a replay and
NO reference must read NOT-MEASURABLE from the other side; references must come
OFF DISK (a synthetic book with different numbers must move the read, which the
cited-constant path cannot do); the swarm's best is the MINIMUM over observations;
tail-scoping must actually drop pre-window rows; and the whole pass must leave
every byte of every book unmodified.

Run pre-build: every test here FAILED (tools/efficiency_read.py did not exist).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools import efficiency_read as eff  # noqa: E402
from tools.wiring_receipts import (  # noqa: E402
    build_index,
    parse_file,
    parse_site,
)

# ── synthetic books ──────────────────────────────────────────────────────────

def _meta(root, box, game, hexid, baseline):
    d = os.path.join(str(root), box, "environment_files", game, hexid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "metadata.json"), "w", encoding="utf-8") as fh:
        json.dump({"game_id": "%s-%s" % (game, hexid), "title": game.upper(),
                   "baseline_actions": list(baseline)}, fh)
    return "%s-%s" % (game, hexid)


def _db(root, box):
    d = os.path.join(str(root), box)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "core_data.db")
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE IF NOT EXISTS winning_sequences (
        sequence_id TEXT PRIMARY KEY, game_id TEXT, level_number INTEGER,
        total_actions INTEGER, is_active INTEGER DEFAULT 1,
        generation_discovered INTEGER DEFAULT 0, discovered_at TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS game_results (
        game_id TEXT, session_id TEXT, total_actions INTEGER,
        level_completions INTEGER DEFAULT 0, created_at TIMESTAMP)""")
    con.commit()
    return con, path


def _win(con, game, level, actions, active=1, gen=0, at="2026-08-17 00:00:00"):
    con.execute("INSERT INTO winning_sequences VALUES (?,?,?,?,?,?,?)",
                ("seq_%s_%d_%d" % (game, level, actions), game, level,
                 actions, active, gen, at))
    con.commit()


def _episode(con, game, sid, actions, levels, at="2026-08-17 00:00:00"):
    con.execute("INSERT INTO game_results VALUES (?,?,?,?,?)",
                (game, sid, actions, levels, at))
    con.commit()


@pytest.fixture()
def books(tmp_path):
    """Three boxes, three honest states:

      aa11 -- reference [10, 20, 30] and banked replays for levels 1 and 2
              (level 1 observed twice: 14 and 12, so best = 12).
      bb22 -- reference [5, 5] and NO banked replay at all (NOT-MEASURABLE).
      cc33 -- banked replay but NO reference metadata (NOT-MEASURABLE, other side).
    """
    root = tmp_path / "swarm"
    g_a = _meta(root, "aa11", "aa11", "aaaaaaaa", [10, 20, 30])
    g_b = _meta(root, "bb22", "bb22", "bbbbbbbb", [5, 5])
    g_c = "cc33-cccccccc"

    con_a, _ = _db(root, "aa11")
    _win(con_a, g_a, 1, 14)
    _win(con_a, g_a, 1, 12)      # the best observation for level 1
    _win(con_a, g_a, 2, 20)      # exactly the reference
    _episode(con_a, g_a, "s1", 90, 2)
    _episode(con_a, g_a, "s2", 40, 0)
    con_a.close()

    con_b, _ = _db(root, "bb22")
    _episode(con_b, g_b, "s1", 50, 0)
    con_b.close()

    con_c, _ = _db(root, "cc33")
    _win(con_c, g_c, 1, 7)
    con_c.close()
    return {"root": str(root), "a": g_a, "b": g_b, "c": g_c}


def _report(books, **kw):
    kw.setdefault("refs_roots", [books["root"]])
    return eff.efficiency_report(books["root"], **kw)


def _game(report, game_id):
    for g in report["games"]:
        if g["game"] == game_id:
            return g
    raise AssertionError("game %r absent from report: %r"
                         % (game_id, [g["game"] for g in report["games"]]))


# ── the distances ────────────────────────────────────────────────────────────

class TestDistances:

    def test_per_level_distance_to_that_player(self, books):
        levels = {r["level"]: r for r in _game(_report(books), books["a"])["levels"]}
        assert levels[1]["reference"] == 10
        assert levels[1]["observed_best"] == 12, (
            "the swarm's best is the MINIMUM over observations (12, not 14)")
        assert levels[1]["distance"] == 2, "distance = observed - reference"
        assert levels[1]["ratio"] == pytest.approx(1.2)
        assert levels[1]["measurable"] is True

    def test_zero_distance_is_reachable_and_reads_zero(self, books):
        """A number that could only have been positive would be guaranteed by
        construction (THE_LADDER Q8). Level 2 matches the reference exactly."""
        levels = {r["level"]: r for r in _game(_report(books), books["a"])["levels"]}
        assert levels[2]["distance"] == 0 and levels[2]["ratio"] == pytest.approx(1.0)

    def test_cumulative_actions_to_that_level(self, books):
        levels = {r["level"]: r for r in _game(_report(books), books["a"])["levels"]}
        assert levels[1]["reference_cum"] == 10 and levels[1]["observed_cum"] == 12
        assert levels[2]["reference_cum"] == 30, "10 + 20"
        assert levels[2]["observed_cum"] == 32, "12 + 20"
        assert levels[2]["distance_cum"] == 2

    def test_episode_total_bound_from_game_results(self, books):
        """game_results carries no per-level split, so the only honest thing it
        yields is an UPPER BOUND on actions-to-complete-level-L: the smallest
        episode total among episodes that completed at least L levels."""
        levels = {r["level"]: r for r in _game(_report(books), books["a"])["levels"]}
        assert levels[2]["episode_total_bound"] == 90
        assert levels[1]["episode_total_bound"] == 90, (
            "the 40-action episode completed 0 levels and bounds nothing")

    def test_unreached_reference_level_is_not_measurable_not_zero(self, books):
        levels = {r["level"]: r for r in _game(_report(books), books["a"])["levels"]}
        assert levels[3]["measurable"] is False
        assert levels[3]["observed_best"] is None
        assert levels[3]["distance"] is None
        assert "NOT-MEASURABLE" in levels[3]["reason"]


class TestNotMeasurable:

    def test_game_with_reference_and_no_replay(self, books):
        g = _game(_report(books), books["b"])
        assert g["measurable"] is False
        assert "NOT-MEASURABLE" in g["reason"] and "replay" in g["reason"]
        assert g["episodes"] == 1, "exposure is still reported beside the honest gap"

    def test_game_with_replay_and_no_reference(self, books):
        g = _game(_report(books), books["c"])
        assert g["measurable"] is False
        assert "NOT-MEASURABLE" in g["reason"] and "reference" in g["reason"]

    def test_not_measurable_never_collapses_to_a_number(self, books):
        rep = _report(books)
        for g in rep["games"]:
            if g["measurable"]:
                continue
            for row in g["levels"]:
                assert row["distance"] is None and row["ratio"] is None


# ── the label, on every line ─────────────────────────────────────────────────

class TestOneRunLabel:

    def test_label_constant_is_the_riders_exact_words(self):
        assert eff.LABEL == "one reference run, not a reference distribution"

    def test_every_rendered_line_carries_the_label(self, books):
        lines = eff.render(_report(books))
        assert lines, "the render must produce output"
        missing = [ln for ln in lines if eff.LABEL not in ln]
        assert not missing, (
            "EVERY output line must carry %r -- the convention does the "
            "remembering, not the reader. Unlabelled: %r"
            % (eff.LABEL, missing[:5]))

    def test_every_json_line_carries_the_label(self, books):
        lines = eff.render(_report(books), as_json=True)
        assert lines
        for ln in lines:
            assert eff.LABEL in ln
            assert json.loads(ln)["label"] == eff.LABEL

    def test_header_prints_the_prohibition(self, books):
        head = eff.render(_report(books))[0:6]
        blob = "\n".join(head)
        assert eff.PROHIBITION in blob and eff.PROHIBITION == "READ, NEVER TARGET"
        assert eff.LABEL in head[0]

    def test_main_stdout_is_fully_labelled(self, books, capsys):
        rc = eff.main(["--root", books["root"], "--refs", books["root"]])
        out = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
        assert rc == 0 and out
        assert all(eff.LABEL in ln for ln in out)
        assert any(eff.PROHIBITION in ln for ln in out)


# ── the reference comes off disk ─────────────────────────────────────────────

class TestReferenceProvenance:

    def test_references_are_read_from_the_books_not_hardcoded(self, tmp_path):
        """Same game id, a DIFFERENT on-disk baseline: the read must move.
        A hardcoded constant cannot do this."""
        root = tmp_path / "swarm"
        g = _meta(root, "ls20", "ls20", "9607627b", [99, 98, 97])
        con, _ = _db(root, "ls20")
        _win(con, g, 1, 100)
        con.close()
        rep = eff.efficiency_report(str(root), refs_roots=[str(root)])
        row = _game(rep, g)["levels"][0]
        assert row["reference"] == 99 and row["distance"] == 1

    def test_cited_ls20_counts_are_verified_against_disk_never_substituted(self):
        """THE_GOALS.md cites ls20's replay expert counts. The instrument
        VERIFIES that citation against the on-disk record and reports the
        comparison; it must never fall back to the cited numbers as data."""
        env = [os.path.join(REPO, "environment_files")]
        refs = eff.discover_references(env)
        chk = eff.verify_cited_ls20(refs, eff.reference_sources(env))
        assert chk["found"] is True, "ls20's on-disk reference must be discoverable"
        assert chk["cited"] == list(eff.CITED_LS20)
        assert chk["on_disk"], "the on-disk counts must be reported verbatim"
        assert chk["match"] == (chk["on_disk"] == chk["cited"]), (
            "the verdict must be the comparison, not a claim about it")
        assert chk["source"].endswith("metadata.json")
        # the citation is never a data source: it is absent from the read path
        for game, vals in refs.items():
            if "ls20" in game:
                assert vals != list(eff.CITED_LS20)

    def test_reference_source_path_is_recorded_per_game(self, books):
        g = _game(_report(books), books["a"])
        assert g["reference_source"].endswith("metadata.json")


# ── tail-scoping and read-only ───────────────────────────────────────────────

class TestScopeAndSafety:

    def test_since_drops_pre_window_rows(self, tmp_path):
        root = tmp_path / "swarm"
        g = _meta(root, "aa11", "aa11", "aaaaaaaa", [10])
        con, _ = _db(root, "aa11")
        _win(con, g, 1, 11, at="2026-08-01 00:00:00")   # pre-window, the better one
        _win(con, g, 1, 19, at="2026-08-17 00:00:00")
        con.close()
        wide = eff.efficiency_report(str(root), refs_roots=[str(root)])
        assert _game(wide, g)["levels"][0]["observed_best"] == 11
        tail = eff.efficiency_report(str(root), refs_roots=[str(root)],
                                     since="2026-08-10")
        assert _game(tail, g)["levels"][0]["observed_best"] == 19, (
            "tail-scoping must actually drop pre-window observations "
            "(THE_LADDER: every reading gets an AS-OF)")

    def test_as_of_is_reported(self, books):
        rep = _report(books, since="2026-08-10")
        assert rep["as_of"]["since"] == "2026-08-10"
        assert any("as-of" in ln.lower() for ln in eff.render(rep))

    def test_the_read_never_writes(self, books):
        root = books["root"]
        before = {}
        for base, _dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(base, f)
                st = os.stat(p)
                before[p] = (st.st_size, st.st_mtime_ns)
        eff.main(["--root", root, "--refs", root])
        after = {}
        for base, _dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(base, f)
                st = os.stat(p)
                after[p] = (st.st_size, st.st_mtime_ns)
        assert after == before, (
            "READ, NEVER TARGET starts with READ, NEVER WRITE: the instrument "
            "must not touch a byte of the books")

    def test_missing_root_degrades_loudly_not_silently(self, tmp_path, capsys):
        rc = eff.main(["--root", str(tmp_path / "nope"),
                       "--refs", str(tmp_path / "nope")])
        out = capsys.readouterr().out
        assert rc == 0 and eff.LABEL in out
        assert "NOT-MEASURABLE" in out or "no swarm boxes" in out


# ── it is an instrument, not a knob ──────────────────────────────────────────

class TestNeverATarget:

    def test_module_declares_the_prohibition(self):
        assert eff.PROHIBITION in (eff.__doc__ or "")
        assert "rung-0" in (eff.__doc__ or "").lower()

    def test_no_threshold_or_target_constants(self):
        """A read with a threshold is a knob wearing a read's clothes."""
        bad = [n for n in dir(eff)
               if n.isupper() and any(w in n for w in
                                      ("TARGET", "THRESHOLD", "GOAL", "BUDGET"))]
        assert not bad, "an instrument registered READ-NEVER-TARGET grew a knob: %r" % bad


# ── the registry row (rung 0c) ───────────────────────────────────────────────

def _registry_row(name):
    path = os.path.join(REPO, "record", "canon", "WIRING_REGISTRY.md")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip().startswith("| %s |" % name):
                return [c.strip() for c in line.strip().strip("|").split("|")]
    return None


class TestRegistryRow:

    def test_efficiency_read_row_exists_as_an_instrument(self):
        row = _registry_row("efficiency-read")
        assert row is not None, (
            "rung 0c: a new organ with no registry receipt is UNSHIPPABLE")
        _name, symbol, site, status, date, note = row
        assert symbol == "tools.efficiency_read:efficiency_report"
        assert site.startswith("tools/efficiency_read.py:")
        assert status in ("LIVE", "SEVERED", "DELETED-PENDING")
        assert date.startswith("2026-")
        assert "[instrument]" in note, (
            "the row must declare INSTRUMENT: it is invoked by the beat "
            "protocol, never by the live path")
        assert "beat protocol" in note and "THE_LADDER" in note
        assert "READ, NEVER TARGET" in note

    def test_registry_receipt_line_exists(self):
        """UPDATED 2026-08-21 (PREREG_SYMBOL_RECEIPTS.md §1): the site cell is a
        SYMBOL FINGERPRINT, not a line, so `rsplit(":", 1)` no longer yields a
        path and an integer. The old body read ±6 lines around the claimed line
        and looked for the substring 'efficiency_report' -- the region-substring proxy that
        let four rows in this registry assert nothing at all. The claim now IS
        the symbol: the cell must name efficiency_report and the node it names must exist
        where the cell says."""
        row = _registry_row("efficiency-read")
        site = parse_site(row[2])
        assert site.fingerprinted, "row still on the old position form: %r" % row[2]
        assert site.name == "efficiency_report", (
            "the receipt does not name efficiency_report: %r" % row[2])
        full = os.path.join(REPO, site.file)
        assert os.path.exists(full)
        index, _quals = build_index(parse_file(full))
        nodes = index.get((site.enclosing, site.kind, site.name)) or []
        assert len(nodes) > site.ordinal, (
            "the claimed %s #%d of efficiency_report inside %r does not exist in %s"
            % (site.kind, site.ordinal, site.enclosing, site.file))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
