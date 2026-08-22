"""GATE: THE SEQ WATERMARK -- record/prereg/PREREG_SEQ_WATERMARK.md, F1-F5.

THE CLAIM UNDER TEST. The ego_fabric streams carry `seq` and no clock, so no
frame-internal rate the mandate's item 3 asks for can be windowed. The repair is
a SIDECAR the launcher writes and the agent never reads -- .runs/swarm/<box>/
watermarks.jsonl, {utc, poll, streams:{"collective/<topic>": head seq}} -- and
NOT a UTC field on fabric.append, which would break the byte-identity gate
(tests/gate/test_system_determinism.py). No record gains a clock.

ASSERTED -- these fail if the build changes behaviour:
  * F1 NO RECORD CHANGES: every fabric byte, and every fabric mtime, is identical
    with the watermark writer running and not running; and two identically-driven
    roots stay byte-identical THROUGH a watermark sweep -- the determinism gate's
    own property, restated at this build's grain;
  * F2 THE WINDOW IS EXACT: over a stream appended by the REAL KnowledgeFabric
    across four watermark ticks, `_window_seq` returns the bracketing head seqs
    and the records it selects are exactly the records appended in that interval,
    at every boundary, with (lo, hi] half-open -- the record whose seq equals lo
    belongs to the PREVIOUS window and the one equal to hi to this one;
  * F3 DEGRADATION IS STATED: with no sidecar the beat's report is what it was
    before this build, and a sidecar too short to bracket the window produces
    THE SAME BYTES (the fallback is the undo); a sidecar with a gap at a window
    boundary reads NOT READABLE and prints no rate for that stream, never an
    interpolation;
  * F4 THE AGENT NEVER READS IT: no module under engines/, no rung, no repo-root
    production module and not the loop imports tools.watermark or names the
    sidecar, its symbols or its filename (AST over strings, names, attributes and
    imports, plus a raw-byte check on the filename);
  * F5 CHEAP: one tail read per collective stream per tick, counted on a
    constructed box, and ZERO whole-stream parses -- the writer may never pay
    `_read_stream`;
  * the writer creates nothing on a box with no fabric; the sidecar is bounded by
    the janitor's OWN threshold, keeping the newest ticks and only whole records;
    both launchers reach the ONE assembly and neither transcribes its format.

ASSUMED -- read off the fixtures, not laws of the system:
  * KnowledgeFabric.append's record grammar (a "seq" field it assigns, monotone
    per stream, starting at 1) is the fabric as of this commit; a change there
    makes these fixtures wrong, not the watermark;
  * FabricJanitor.STREAM_MAX_BYTES is the bound the writer trims against --
    imported, so the value itself is never asserted here, only that the trim
    happens at it;
  * the beat's report text quoted in F3 is tools/beat_rates.py's own wording as
    of this commit (it is compared against ITSELF across two runs, so the test
    breaks on a behaviour change and not on a rewording).

NO .runs ANYWHERE, and NO REAL CLOCK ANYWHERE. Every timestamp in this file is
SET explicitly -- the tick utcs, the report's `now`, and the report's as-of line.
A test about time whose result depends on when it runs is not a test: that error
was made in this suite on 2026-08-21 (tests/gate/test_beat_rates.py's stream
mtime inherited the filesystem's real clock and went red when real time walked
into a frozen window), and this file is the one place it would be easiest to
repeat.
"""
from __future__ import annotations

import ast
import builtins
import datetime as dt
import glob
import importlib
import io
import json
import os
import sys
from unittest import mock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from tools import beat_rates as br  # noqa: E402
from tools import watermark as wmk  # noqa: E402

WM_SRC = os.path.join(REPO, "tools", "watermark.py")
SUP_SRC = os.path.join(REPO, "tools", "swarm_supervisor.py")
KEEPER_SRC = os.path.join(REPO, "tools", "sprint_keeper.py")

# THE FROZEN CLOCK. Ticks are one POLL apart; every window in this file is stated
# against these instants and never against `now`.
POLL = 60
T0 = dt.datetime(2026, 8, 22, 10, 0, 0)
T1 = T0 + dt.timedelta(seconds=POLL)
T2 = T0 + dt.timedelta(seconds=2 * POLL)
T3 = T0 + dt.timedelta(seconds=3 * POLL)
NOW = dt.datetime(2026, 8, 22, 12, 0, 0)


# ── fixture construction (tmp only) ──────────────────────────────────────────

def _iso(when: dt.datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%S")


def _box(tmp_path, name: str = "bx01") -> str:
    return os.path.join(str(tmp_path / "swarm"), name)


def _fabric(box_dir: str) -> KnowledgeFabric:
    """A REAL fabric over the box's ego_fabric root. Its appends assign the seqs
    this whole build windows on -- the test never invents one."""
    return KnowledgeFabric(os.path.join(box_dir, wmk.FABRIC_DIR))


def _seed_fabric(box_dir: str) -> None:
    """Bring the fabric into existence the way a worker does -- ONE personal
    narration record, before any collective topic exists. The launcher's first
    tick then lands on a real fabric with an empty collective scope, which is the
    floor the beat needs (every topic at head 0) and is exactly the order a live
    box goes through: the loop narrates long before it mints."""
    KnowledgeFabric(os.path.join(box_dir, wmk.FABRIC_DIR),
                    agent_id="ag0").append("personal", "narration",
                                           {"point": "PERCEIVE"})


def _tick(box_dir: str, when: dt.datetime, poll: float = POLL):
    """One watermark tick at an EXPLICIT utc, through the shipped writer."""
    return wmk.append_watermark(box_dir, poll, _iso(when))


def _snapshot(root: str):
    """{relpath: (bytes, mtime_ns)} for every file under a directory tree."""
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = (fh.read(), os.stat(p).st_mtime_ns)
    return out


def _mint(fab: KnowledgeFabric, n: int, topic: str = "atoms", first: int = 1):
    """`n` records on one collective topic, returning their assigned seqs. No
    game id, no colour, no object identity: the ids are ordinals."""
    return [fab.append("collective", topic,
                       {"id": "a%d" % i, "kind": "EFFECT"})["seq"]
            for i in range(first, first + n)]


def _run_report(root: str, hours: float = 1.0, since=None, now=NOW) -> str:
    """The beat's report over a constructed root, with BOTH clocks pinned: the
    window's `now` AND the as-of line's `utcnow` (which is a real-clock read and
    would otherwise make two runs of the same fixture differ by a second)."""
    out = io.StringIO()
    with mock.patch.object(br, "RUNS", root), \
            mock.patch.object(br, "utcnow", lambda: now):
        br.report(br.resolve_window(hours, since, now), None, out)
    return out.getvalue()


# ── F1 · NO RECORD CHANGES ───────────────────────────────────────────────────

def test_f1_the_fabric_is_byte_identical_with_the_writer_running(tmp_path):
    """ASSERTED. The whole point of a sidecar: the writer reads and never writes.
    Bytes AND mtimes of every fabric file are unchanged across three sweeps, and
    the only thing that appears on the box is the sidecar, OUTSIDE ego_fabric."""
    box = _box(tmp_path)
    fab = _fabric(box)
    _mint(fab, 5)
    _mint(fab, 3, topic="mint_verdicts")
    fabric_root = os.path.join(box, wmk.FABRIC_DIR)
    before = _snapshot(fabric_root)

    for i, when in enumerate((T0, T1, T2)):
        assert _tick(box, when) is not None, i

    assert _snapshot(fabric_root) == before, (
        "the watermark writer changed a fabric byte or a fabric mtime -- it must "
        "only READ (F1)")
    assert sorted(os.listdir(box)) == [wmk.FABRIC_DIR, wmk.WATERMARK_NAME]


def test_f1_two_identically_driven_roots_stay_identical_through_a_sweep(tmp_path):
    """ASSERTED -- the determinism gate's own property at this build's grain.
    Two roots driven with the SAME appends, one of them watermarked between every
    append, end byte-identical. If the sidecar could ever perturb a stream, this
    is where it would show."""
    plain, marked = _box(tmp_path, "plain"), _box(tmp_path, "marked")
    fa, fb = _fabric(plain), _fabric(marked)
    for i in range(4):
        _mint(fa, 2, first=1 + 2 * i)
        _mint(fb, 2, first=1 + 2 * i)
        _tick(marked, T0 + dt.timedelta(seconds=POLL * i))
    a = {k: v[0] for k, v in _snapshot(os.path.join(plain, wmk.FABRIC_DIR)).items()}
    b = {k: v[0] for k, v in _snapshot(os.path.join(marked, wmk.FABRIC_DIR)).items()}
    assert a == b, "a watermarked root diverged from an unwatermarked one"


def test_f1_no_record_carries_a_clock(tmp_path):
    """ASSERTED. The trap, made structural: not one record the fabric wrote
    carries a utc/time field, and the sidecar is not a stream -- it lives outside
    ego_fabric and no fabric scope can reach it."""
    box = _box(tmp_path)
    _mint(_fabric(box), 3)
    _tick(box, T0)
    for path in glob.glob(os.path.join(box, wmk.FABRIC_DIR, "**", "*.jsonl"),
                          recursive=True):
        for line in open(path, encoding="utf-8"):
            rec = json.loads(line)
            assert set(rec) == {"id", "kind", "seq"}, (path, rec)
    assert os.path.dirname(wmk.watermark_path(box)) == box


# ── F2 · THE WINDOW IS EXACT ─────────────────────────────────────────────────

@pytest.fixture
def three_ticks(tmp_path):
    """A stream appended ACROSS the ticks, by the real fabric, at explicit times:

        tick T0 (head 0) | +3 records | tick T1 (head 3) | +2 | tick T2 (head 5)
        | +4 | tick T3 (head 9)

    Returns (root, box name). Every seq here is the fabric's, not the test's."""
    box = _box(tmp_path)
    _seed_fabric(box)
    fab = _fabric(box)
    assert _tick(box, T0)[wmk.F_STREAMS] == {}, "the floor tick is missing"
    assert _mint(fab, 3, first=1) == [1, 2, 3]
    _tick(box, T1)
    assert _mint(fab, 2, first=4) == [4, 5]
    _tick(box, T2)
    assert _mint(fab, 4, first=6) == [6, 7, 8, 9]
    _tick(box, T3)
    return str(tmp_path / "swarm"), "bx01"


@pytest.mark.parametrize("t_a,t_b,pair,seqs", [
    (T0, T1, (0, 3), [1, 2, 3]),
    (T1, T2, (3, 5), [4, 5]),
    (T2, T3, (5, 9), [6, 7, 8, 9]),
    (T0, T2, (0, 5), [1, 2, 3, 4, 5]),
    (T1, T3, (3, 9), [4, 5, 6, 7, 8, 9]),
    (T0, T3, (0, 9), [1, 2, 3, 4, 5, 6, 7, 8, 9]),
])
def test_f2_the_window_is_exact_at_every_boundary(three_ticks, t_a, t_b, pair, seqs):
    """ASSERTED. The beat's count for a window equals the records actually
    appended in it, EXACTLY, at every boundary -- both edges included."""
    root, box = three_ticks
    with mock.patch.object(br, "RUNS", root):
        assert br._window_seq(box, "atoms", t_a, t_b) == pair
        sb = br.SeqBracket(box, "atoms", br.Window(t_a, t_b))
        assert sb.state == "exact", sb.reason
        recs = br.read_records(br.stream_path(box, "atoms"))
        assert [r["seq"] for r in sb.select(recs)] == seqs


def test_f2_the_boundary_is_half_open_so_two_beats_partition(three_ticks):
    """ASSERTED. (lo, hi] -- the same rule the DB clock's (start, end] uses. The
    record whose seq equals lo belongs to the PREVIOUS window; the one equal to
    hi to this one. Two consecutive beats therefore partition the stream instead
    of counting the boundary record twice."""
    root, box = three_ticks
    with mock.patch.object(br, "RUNS", root):
        recs = br.read_records(br.stream_path(box, "atoms"))
        first = br.SeqBracket(box, "atoms", br.Window(T0, T1))
        second = br.SeqBracket(box, "atoms", br.Window(T1, T2))
        a = [r["seq"] for r in first.select(recs)]
        b = [r["seq"] for r in second.select(recs)]
    assert 3 in a and 3 not in b, "the boundary record was counted in both windows"
    assert not set(a) & set(b)
    assert sorted(a + b) == [1, 2, 3, 4, 5], "a record fell out of both windows"


def test_f2_a_window_inside_one_tick_interval_is_bracketed_with_its_slack(
        three_ticks):
    """ASSERTED. A window whose boundaries do NOT land on ticks is readable but
    is NOT called exact: it is the bracketing ticks' range, and the slack between
    each boundary and its tick is carried on the object and PRINTED, never
    rounded away. Resolution equals the poll interval, which is the residue the
    prereg states."""
    root, box = three_ticks
    mid_a, mid_b = T0 + dt.timedelta(seconds=20), T1 + dt.timedelta(seconds=20)
    with mock.patch.object(br, "RUNS", root):
        sb = br.SeqBracket(box, "atoms", br.Window(mid_a, mid_b))
    assert sb.state == "bracketed" and sb.readable
    assert (sb.lo, sb.hi) == (0, 5)
    assert (sb.slack_lo, sb.slack_hi) == (20.0, 40.0)
    assert "+/-40s" in sb.cell(), sb.cell()


def test_f2_a_missing_key_is_seq_zero_and_a_null_head_is_not(tmp_path):
    """ASSERTED. A key ABSENT from a tick means the stream did not exist then --
    head 0, the floor below the first append there will ever be. A key present
    but NULL means the head could not be read: that tick is dropped for the
    topic rather than read as a zero, which would rewind the floor and
    over-count."""
    box = _box(tmp_path)
    _seed_fabric(box)
    fab = _fabric(box)
    _tick(box, T0)                                   # no collective topic yet
    _mint(fab, 2)
    _tick(box, T1)
    root = str(tmp_path / "swarm")
    with mock.patch.object(br, "RUNS", root):
        assert br._window_seq("bx01", "atoms", T0, T1) == (0, 2)
    # now poison the first tick's head for this topic and the window degrades
    ticks = wmk.read_watermarks(wmk.watermark_path(box))
    ticks[0][wmk.F_STREAMS]["collective/atoms"] = None
    with open(wmk.watermark_path(box), "w", encoding="utf-8") as fh:
        for t in ticks:
            fh.write(json.dumps(t) + "\n")
    with mock.patch.object(br, "RUNS", root):
        assert br._window_seq("bx01", "atoms", T0, T1) is None, (
            "the beat served a stale parse of a sidecar that changed under it")


# ── F3 · DEGRADATION IS STATED ───────────────────────────────────────────────

def _fill(box_dir: str) -> None:
    """The collective records the beat counts: four verdicts (three of them
    mints) and four atoms carrying four distinct keys, through the real fabric.
    Called BEFORE or BETWEEN ticks by each test, because WHEN a record lands
    relative to a tick is the whole subject here."""
    fab = _fabric(box_dir)
    for i in range(4):
        fab.append("collective", "mint_verdicts",
                   {"verdict": "mint" if i < 3 else "reject", "game": "gx"})
        fab.append("collective", "atoms",
                   {"id": "a%d" % i, "game": "gx", "atom": {"key": "k%d" % i}})


def _beat_box(tmp_path, box_name: str = "bx01"):
    """A box the beat can report on: a minimal core_data.db plus a fabric that
    exists and has NO collective topic yet (the state a live box is in before its
    first mint). The records are added by `_fill` where each test wants them."""
    import sqlite3
    box = _box(tmp_path, box_name)
    os.makedirs(box, exist_ok=True)
    con = sqlite3.connect(os.path.join(box, "core_data.db"))
    con.executescript(
        "CREATE TABLE game_results (game_id TEXT, session_id TEXT, status TEXT, "
        " win_detected INTEGER, level_completions INTEGER, created_at TEXT);"
        "CREATE TABLE action_traces (session_id TEXT, game_id TEXT, "
        " action_number INTEGER, timestamp TEXT, created_at TEXT, "
        " level_number INTEGER);"
        "CREATE TABLE agent_operating_modes (agent_id TEXT, game_id TEXT, "
        " operating_mode TEXT, score_achieved REAL, win_achieved INTEGER, "
        " progress_score REAL, created_at TEXT);"
        "CREATE TABLE agents (agent_id TEXT, is_active INTEGER, "
        " retirement_reason TEXT);"
        "CREATE TABLE primitive_status (primitive_name TEXT, status TEXT, "
        " unlocked_at TEXT, unlocked_by_agent TEXT);")
    con.commit()
    con.close()
    _seed_fabric(box)
    return box


def test_f3_no_sidecar_prints_todays_report_and_no_watermark_section(tmp_path):
    """ASSERTED. With no sidecar the beat is exactly the instrument it was: the
    mtime bracket, its stated sentences, and NO seq section anywhere."""
    _fill(_beat_box(tmp_path))
    text = _run_report(str(tmp_path / "swarm"))
    assert "A2." not in text and "seq (" not in text
    assert "SEQ WATERMARK: present" not in text
    assert "MTIME BRACKET" in text
    assert br.NOT_READABLE in text


def test_f3_a_sidecar_too_short_to_bracket_degrades_byte_for_byte(tmp_path):
    """ASSERTED -- THE UNDO. A sidecar that does not bracket the window produces
    THE SAME BYTES as no sidecar at all. Not 'similar output': the two reports
    are compared to each other, so a behaviour change breaks this and a rewording
    does not."""
    box = _beat_box(tmp_path)
    _fill(box)
    root = str(tmp_path / "swarm")
    without = _run_report(root)                       # window is (11:00, 12:00]
    _tick(box, T0)                                    # 10:00 -- before the window
    _tick(box, T1)                                    # 10:01 -- and nothing after
    with_short = _run_report(root)
    assert with_short == without, (
        "a sidecar that cannot bracket the window changed the report -- the "
        "fallback to the mtime bracket is the undo and must be byte-for-byte")
    with mock.patch.object(br, "RUNS", root):
        sb = br.SeqBracket("bx01", "atoms", br.resolve_window(1.0, None, NOW))
    assert sb.state == "absent" and "does not bracket" in sb.reason


def test_f3_a_gap_reads_not_readable_and_is_never_interpolated(tmp_path):
    """ASSERTED. The sidecar brackets the window, but a boundary sits further
    from its tick than the launcher's OWN declared poll interval -- a missed
    tick. The count over that bracket is not attributable to the window, so it is
    NOT READABLE and no rate is printed for that stream."""
    box = _beat_box(tmp_path)
    root = str(tmp_path / "swarm")
    # the window is (11:00, 12:00]; the only ticks are at 10:30 and 12:29 -- the
    # launcher was down across both boundaries, so neither is attributable.
    _tick(box, NOW - dt.timedelta(minutes=90))
    _fill(box)
    _tick(box, NOW + dt.timedelta(minutes=29))
    with mock.patch.object(br, "RUNS", root):
        w = br.resolve_window(1.0, None, NOW)
        sb = br.SeqBracket("bx01", "atoms", w)
        assert br._window_seq("bx01", "atoms", w.start, w.end) is None
    assert sb.state == "gap", sb.reason
    assert "missed a tick" in sb.reason
    assert sb.lo is None and sb.hi is None, "a gap handed back a seq range"

    text = _run_report(root)
    assert "A2." in text and "A GAP IS NOT INTERPOLATED" in text
    assert "mint/h" not in text, "a rate table was printed over a gap"
    gap_lines = [ln for ln in text.splitlines()
                 if br.NOT_READABLE in ln and "missed a tick" in ln]
    assert len(gap_lines) == 2, gap_lines          # mint_verdicts and atoms
    assert "bx01" in gap_lines[0] and "atoms" in " ".join(gap_lines)


def test_f3_a_bracketing_sidecar_prints_true_per_hour_rates(tmp_path):
    """ASSERTED -- what the whole build is for. With ticks on both sides of the
    window the beat prints minted/composed/retired PER HOUR, from a seq range,
    and says which range it used."""
    box = _beat_box(tmp_path)
    root = str(tmp_path / "swarm")
    _tick(box, NOW - dt.timedelta(hours=1))           # exactly on the boundary
    _fill(box)                                        # every record lands INSIDE
    _tick(box, NOW)
    text = _run_report(root)
    assert "A2. PER HOUR" in text and "NO RECORD GAINED A CLOCK" in text
    assert "SEQ WATERMARK: present on 1/1 boxes" in text
    assert "the clock is beside them, never inside them" in text
    lines = text.splitlines()
    a2 = lines[next(i for i, ln in enumerate(lines) if ln.startswith("A2.")):]
    row = [ln for ln in a2 if ln.strip().startswith("gx") and "seq (" in ln]
    assert row, text
    # four verdicts, three of them mints, all inside a one-hour window -> 3.00/h
    assert row[0].split()[2] == "3.00", row[0]
    assert "seq (0,4] EXACT" in row[0], row[0]
    # the all-time table above it carries the same window cell and its own rate
    a_row = [ln for ln in lines[:len(lines) - len(a2)]
             if ln.strip().startswith("gx")]
    assert a_row and "3/4 = 0.750" in a_row[-1], a_row
    # ... and NOVEL becomes a real count: four keys first appear in the window
    assert "NOVEL: 4/4" in text, text


def test_f3_the_windowed_tally_is_the_same_rule_as_the_all_time_tally(tmp_path):
    """ASSERTED. The windowed numbers come from `_tally` -- the same function the
    all-time table uses -- applied to the seq-selected records. One counting
    rule, two ranges: a windowed number and an all-time number can never be
    produced by two different definitions."""
    box = _beat_box(tmp_path)
    root = str(tmp_path / "swarm")
    _tick(box, NOW - dt.timedelta(hours=1))
    _fill(box)
    _tick(box, NOW)
    with mock.patch.object(br, "RUNS", root):
        L = br.learning("bx01", br.resolve_window(1.0, None, NOW))
    assert L["window_per_game"]["gx"] == L["per_game"]["gx"], (
        "every record was inside the window, so the two tallies must agree")
    src = ast.parse(open(os.path.join(REPO, "tools", "beat_rates.py"),
                         encoding="utf-8").read())
    fn = next(n for n in ast.walk(src)
              if isinstance(n, ast.FunctionDef) and n.name == "learning")
    tallies = [c for c in ast.walk(fn) if isinstance(c, ast.Call)
               and isinstance(c.func, ast.Name) and c.func.id == "_tally"]
    assert len(tallies) == 2, (
        "the windowed pass no longer goes through the all-time counting rule")


# ── F4 · THE AGENT NEVER READS IT ────────────────────────────────────────────

# The names that must not appear in production. `write_all` is deliberately NOT
# here: it is too generic a name to ban across a tree, and the launchers' alias
# (`write_watermarks`) plus the module path already pin the wire.
FORBIDDEN_NAMES = ("append_watermark", "watermark_record", "stream_heads",
                   "read_watermarks", "watermark_path", "WATERMARK_NAME",
                   "write_watermarks", "head_seq")
FORBIDDEN_TEXT = ("watermarks.jsonl", "tools.watermark", "tools/watermark")

PROD_GLOBS = ("*.py", "engines/**/*.py", "rungs/**/*.py")


def _production_files():
    out, seen = [], set()
    for pat in PROD_GLOBS:
        for path in glob.glob(os.path.join(REPO, pat), recursive=True):
            rel = os.path.relpath(path, REPO).replace("\\", "/")
            if rel in seen or "__pycache__" in rel:
                continue
            seen.add(rel)
            out.append(rel)
    return sorted(out)


def test_f4_no_production_module_references_the_watermark():
    """ASSERTED. The agent's determinism surface stays clean: nothing under
    engines/, nothing under rungs/, no repo-root production module and not the
    loop imports the writer or names the sidecar. If any of them did, a
    wall-clock file would be inside the frame the watermark exists to measure
    from OUTSIDE (FIGURE 2: the anchor does not update)."""
    hits = []
    for rel in _production_files():
        path = os.path.join(REPO, rel)
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                src = fh.read()
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        for bad in FORBIDDEN_TEXT:
            if bad in src:
                hits.append((rel, bad, "text"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                hits.append((rel, node.id, "name %d" % node.lineno))
            elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES:
                hits.append((rel, node.attr, "attribute %d" % node.lineno))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if "watermark" in a.name:
                        hits.append((rel, a.name, "import %d" % node.lineno))
            elif isinstance(node, ast.ImportFrom) \
                    and "watermark" in (node.module or ""):
                hits.append((rel, node.module, "import %d" % node.lineno))
    assert hits == [], hits


def test_f4_the_loop_itself_names_nothing_of_it():
    """ASSERTED, separately and by raw bytes: cognitive_loop.py must not mention
    the sidecar even in a comment -- a name in a comment is a lead a later editor
    follows."""
    src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8").read()
    for bad in FORBIDDEN_TEXT + FORBIDDEN_NAMES:
        assert bad not in src, bad


def test_f4_the_writer_only_ever_opens_a_stream_for_reading():
    """ASSERTED. AST over the shipped writer: every open() of a fabric stream is
    a read. The only writes it performs are to the sidecar and its own tmp file."""
    tree = ast.parse(open(WM_SRC, encoding="utf-8").read())
    for fn_name in ("stream_files", "head_seq", "stream_heads"):
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == fn_name)
        opens = [c for c in ast.walk(fn) if isinstance(c, ast.Call)
                 and isinstance(c.func, ast.Name) and c.func.id == "open"]
        assert opens == [], "%s opens a file itself: %r" % (fn_name, opens)


# ── F5 · CHEAP ───────────────────────────────────────────────────────────────

def test_f5_one_tail_read_per_stream_and_no_whole_file_parse(tmp_path, monkeypatch):
    """ASSERTED. The per-poll cost is bounded by ONE tail read per collective
    stream, counted on a constructed box -- and the oracle `_read_stream` (a
    whole-file parse, the thing PERF_AUDIT.md measured at 262 ms on a 40k-record
    stream) is never paid at all.

    The counting shape is tests/gate/test_fabric_next_seq_cache.py's own
    (`counting_tail`), named rather than re-derived."""
    box = _box(tmp_path)
    fab = _fabric(box)
    for topic in ("atoms", "mint_verdicts", "settlements"):
        _mint(fab, 40, topic=topic)

    tails, wholes = [], []
    real_tail = KnowledgeFabric._tail_records

    def counting_tail(path, n):
        tails.append((os.path.basename(path), n))
        return real_tail(path, n)

    def counting_whole(path):
        wholes.append(path)
        raise AssertionError("the watermark writer parsed a whole stream: %s" % path)

    monkeypatch.setattr(KnowledgeFabric, "_tail_records", staticmethod(counting_tail))
    monkeypatch.setattr(KnowledgeFabric, "_read_stream", staticmethod(counting_whole))

    rec = _tick(box, T0)
    assert rec is not None
    assert sorted(tails) == [("atoms.jsonl", 1), ("mint_verdicts.jsonl", 1),
                             ("settlements.jsonl", 1)], tails
    assert wholes == []
    assert rec[wmk.F_STREAMS] == {"collective/atoms": 40,
                                  "collective/mint_verdicts": 40,
                                  "collective/settlements": 40}


def test_f5_the_personal_scope_is_not_watermarked(tmp_path):
    """ASSERTED, and it is the bound that makes F5 hold on the real fleet: one
    box carries ~300 personal narration streams. The collective scope is what the
    beat windows; narration's rung is a bounded tail SAMPLE with its denominator
    printed, never a window."""
    box = _box(tmp_path)
    fab = KnowledgeFabric(os.path.join(box, wmk.FABRIC_DIR), agent_id="ag0")
    fab.append("personal", "narration", {"point": "PERCEIVE"})
    fab.append("collective", "atoms", {"id": "a1"})
    rec = _tick(box, T0)
    assert list(rec[wmk.F_STREAMS]) == ["collective/atoms"]


def test_f5_archives_and_backups_are_not_watermarked(tmp_path):
    """ASSERTED. The janitor's archive holds records already REMOVED from the
    stream: watermarking it would put a second seq series under one topic name.
    A topic carries no dot, which is the rule that excludes both."""
    box = _box(tmp_path)
    _mint(_fabric(box), 2)
    coll = wmk.scope_dir(box)
    open(os.path.join(coll, "atoms.archive.jsonl"), "w",
         encoding="utf-8").write('{"seq": 99}\n')
    open(os.path.join(coll, "atoms.jsonl.bak"), "w",
         encoding="utf-8").write('{"seq": 99}\n')
    open(os.path.join(coll, "action_book.json"), "w",
         encoding="utf-8").write("{}\n")
    rec = _tick(box, T0)
    assert rec[wmk.F_STREAMS] == {"collective/atoms": 2}


# ── the writer's own contract ────────────────────────────────────────────────

def test_the_record_carries_exactly_the_declared_fields(tmp_path):
    """ASSERTED. {utc, poll, streams} and nothing else: the prereg's two fields
    plus the writer's declaration of its own cadence, which is what makes the
    beat's gap rule DERIVED (a boundary further from its tick than the writer
    said it polls) instead of a threshold somebody chose."""
    box = _box(tmp_path)
    _mint(_fabric(box), 1)
    rec = _tick(box, T0, poll=45)
    assert set(rec) == {wmk.F_UTC, wmk.F_POLL, wmk.F_STREAMS}
    assert rec[wmk.F_UTC] == "2026-08-22T10:00:00"
    assert rec[wmk.F_POLL] == 45
    assert br.parse_utc(rec[wmk.F_UTC]) == T0
    line = open(wmk.watermark_path(box), encoding="utf-8").read()
    assert json.loads(line) == rec and line.endswith("\n")


def test_a_box_with_no_fabric_gains_no_file(tmp_path):
    """ASSERTED. A launcher may call the writer unconditionally: a box directory
    that exists because a worker was spawned into it, with no fabric yet, gains
    nothing. (The supervisor's own gate harness runs over exactly such boxes.)"""
    box = _box(tmp_path)
    os.makedirs(box)
    assert _tick(box, T0) is None
    assert os.listdir(box) == []
    assert wmk.write_all(str(tmp_path / "swarm"), ["bx01", "nope"], POLL) == []


def test_the_sidecar_is_bounded_by_the_janitors_own_threshold(tmp_path, monkeypatch):
    """ASSERTED. SIZE-triggered, never cadence-triggered -- the janitor's stated
    philosophy against the janitor's imported constant. The trim keeps the NEWEST
    ticks and only WHOLE records."""
    box = _box(tmp_path)
    _mint(_fabric(box), 1)
    monkeypatch.setattr(wmk, "max_bytes", lambda: 2048)
    for i in range(200):
        _tick(box, T0 + dt.timedelta(seconds=POLL * i))
    size = os.path.getsize(wmk.watermark_path(box))
    assert size <= 2048, size
    ticks = wmk.read_watermarks(wmk.watermark_path(box))
    raw = open(wmk.watermark_path(box), encoding="utf-8").read().splitlines()
    assert len(ticks) == len(raw), "the trim left a partial record"
    assert ticks[-1][wmk.F_UTC] == _iso(T0 + dt.timedelta(seconds=POLL * 199))
    assert ticks[0][wmk.F_UTC] > _iso(T0), "the trim kept the OLDEST ticks"


def test_the_bound_is_the_janitors_constant_not_a_new_knob():
    """ASSERTED. No new knob: the threshold IS FabricJanitor.STREAM_MAX_BYTES,
    imported. Change record/canon/KNOBS.md O2 and this moves with it."""
    from engines.egocentric.janitor import FabricJanitor
    assert wmk.max_bytes() == FabricJanitor.STREAM_MAX_BYTES
    src = open(WM_SRC, encoding="utf-8").read()
    assert "FabricJanitor.STREAM_MAX_BYTES" in src


def test_a_torn_tail_in_the_sidecar_is_skipped_not_fatal(tmp_path):
    """ASSERTED. A crash mid-append is normal on these boxes; the reader drops
    the torn line and keeps the rest, exactly as the fabric's own reader does."""
    box = _box(tmp_path)
    _mint(_fabric(box), 2)
    _tick(box, T0)
    with open(wmk.watermark_path(box), "a", encoding="utf-8") as fh:
        fh.write('{"utc": "2026-08-22T10:01:00", "poll": 60, "stre')
    _tick(box, T2)
    ticks = wmk.read_watermarks(wmk.watermark_path(box))
    assert [t[wmk.F_UTC] for t in ticks] == [_iso(T0), _iso(T2)]


def test_write_all_stamps_the_whole_sweep_with_one_utc(tmp_path):
    """ASSERTED. One utc per sweep, so a window resolves to the same pair of
    ticks on every box and a fleet line is not assembled from 25 clocks."""
    root = str(tmp_path / "swarm")
    for name in ("bx01", "bx02"):
        _mint(_fabric(_box(tmp_path, name)), 1)
    assert wmk.write_all(root, ["bx01", "bx02"], POLL, _iso(T0)) == ["bx01", "bx02"]
    stamps = [wmk.read_watermarks(wmk.watermark_path(_box(tmp_path, n)))[0][wmk.F_UTC]
              for n in ("bx01", "bx02")]
    assert stamps == [_iso(T0), _iso(T0)]


# ── one assembly, both launchers (the fleet_env precedent) ───────────────────

def test_both_launchers_call_the_one_assembly_and_neither_transcribes_it():
    """ASSERTED. The supervisor ticks at its poll and the keeper at its interval,
    both through tools/watermark.py -- the same discipline tools/fleet_env.py
    exists for. Neither launcher names the sidecar's filename or rebuilds its
    record: a transcription drifts.

    Asserted over the launchers' CODE, not their prose -- tests/gate/
    test_sprint_keeper.py's own `test_the_keeper_carries_no_transcription` idiom:
    `ast.unparse` drops comments and the docstring is stripped, so a paragraph
    explaining the sidecar is legal and a line rebuilding it is not."""
    for src_path, poll_arg in ((SUP_SRC, "POLL_SEC"), (KEEPER_SRC, "a.interval")):
        raw = open(src_path, encoding="utf-8").read()
        tree = ast.parse(raw)
        stripped = ast.parse(raw)
        for node in ast.walk(stripped):
            if isinstance(node, (ast.Module, ast.FunctionDef)) \
                    and ast.get_docstring(node):
                node.body = node.body[1:]
        text = ast.unparse(stripped)
        imported = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                    and n.module == "tools.watermark"]
        assert imported, "%s does not import the one assembly" % src_path
        main_fn = next(n for n in tree.body
                       if isinstance(n, ast.FunctionDef) and n.name == "main")
        body = ast.unparse(main_fn)
        assert "write_watermarks(" in body, "%s never ticks" % src_path
        assert poll_arg in body.split("write_watermarks(")[1][:60], (
            "%s does not hand the writer its OWN declared cadence" % src_path)
        assert "watermarks.jsonl" not in text, (
            "%s transcribes the sidecar's filename" % src_path)
        assert '"streams"' not in text and "'streams'" not in text, (
            "%s rebuilds the sidecar's record shape" % src_path)


def test_importing_the_writer_has_no_side_effects_and_no_engine_import():
    """ASSERTED (the D-6 lesson at tooling grain). Importing the writer opens no
    file and pulls in no engine module: both launchers hold a clean-import gate
    and the beat holds its own, so the fabric and the janitor are imported inside
    the functions that need them."""
    real_open = builtins.open

    def boom(*a, **k):
        raise AssertionError("import opened a file: %r" % (a[:1],))

    for mod in ("engines.egocentric.fabric", "engines.egocentric.janitor"):
        sys.modules.pop(mod, None)
    with mock.patch.object(builtins, "open", boom), \
            mock.patch.object(os, "makedirs", boom):
        sys.modules.pop("tools.watermark", None)
        mod = importlib.import_module("tools.watermark")
        importlib.reload(mod)
    builtins.open = real_open
    assert mod.WATERMARK_NAME == "watermarks.jsonl"
    tree = ast.parse(open(WM_SRC, encoding="utf-8").read())
    top_imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    named = [a.name for n in top_imports for a in n.names] + \
            [n.module for n in top_imports if isinstance(n, ast.ImportFrom)]
    assert not any("engines" in str(m) for m in named), named
