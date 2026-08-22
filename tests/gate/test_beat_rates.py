"""GATE: tools/beat_rates.py -- the hourly beat instrument.

WHAT THIS GATE ASSERTS (a law it can break) vs WHAT IT ASSUMES (a fact it reads
off the tool's own inputs) is stated per test, because a gate that cannot tell
the two apart is a survey.

ASSERTED -- these fail if the tool changes behaviour:
  * every rate prints as numerator/denominator, never as a bare count
    (MANDATE item 3: "a count that only goes up is not a learning curve");
  * the window boundary is (start, end] on the DB clock -- a row exactly at the
    start belongs to the PREVIOUS window and a row exactly at the end belongs to
    this one, so two consecutive beats partition rather than double-count;
  * STALLED fires across two identical windows and names the reason the records
    give, rather than printing a flat number twice (MANDATE item 5);
  * a missing topic prints NOT READABLE and names what is missing -- never a
    zero standing in for an absence;
  * the EXPOSURE verdict resolves BOTH ways against a floor derived per game
    from tools/split_half.py, and a game below its floor SUFFIXES every later
    line for that game (FIGURE 3: a reading taken below the break is a reading
    of nothing);
  * the residual line reports ONE LIVE SLOT with its slot id and the largest
    single-slot value, and the MEAN VALUE IS NEVER PRINTED, in exactly the case
    Figure 1 calls legal: the across-slot aggregate near zero with a slot live
    ("aggregating across slots is how a live signal disappears into an average");
  * no function in the tool reads the frame blob columns or the per-level frame
    stream (AST over the tool's source: the proctor's standing constraint made
    structural rather than promised);
  * importing the tool has no side effects -- no file opened, no directory made,
    no subprocess -- the D-6 lesson at tooling grain, the same property
    tests/gate/test_sprint_keeper.py holds the supervisor to.

ASSUMED -- read off the fixtures, not laws of the system:
  * the sqlite schema fragments used here (game_results, action_traces,
    agent_operating_modes, agents, primitive_status) are the live column sets as
    of this commit; a schema change makes these fixtures wrong, not the tool;
  * the narration PERCEIVE payload shape slots{SLOT:{bet,residual,bin}} is
    engines/egocentric/narration.py's record grammar as the loop writes it.

NO .runs ANYWHERE. Every fixture is built into pytest's tmp_path and the tool's
RUNS constant is repointed at it; nothing here reads or writes the live fleet.
"""
from __future__ import annotations

import ast
import builtins
import datetime as dt
import importlib
import io
import json
import os
import sqlite3
import sys
from unittest import mock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools import beat_rates as br  # noqa: E402

TOOL_SRC = os.path.join(REPO, "tools", "beat_rates.py")

# The names the proctor may never read. They live HERE, in the gate, and must
# not appear in the tool at all -- which is the whole point of the AST test.
FORBIDDEN = ("frame_before", "frame_after", "levelup_frames")

NOW = dt.datetime(2026, 8, 22, 12, 0, 0)


# ── fixture construction (tmp only) ──────────────────────────────────────────

def _mkdb(path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(
        "CREATE TABLE game_results (game_id TEXT, session_id TEXT, "
        " start_time TEXT, end_time TEXT, status TEXT, win_detected INTEGER, "
        " level_completions INTEGER, created_at TEXT);"
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
    return con


def _episode(con, game, sid, created, actions=4, levels=(0,), completions=0,
             win=0, gap_s=3):
    """One session: its result row and `actions` trace rows `gap_s` apart."""
    con.execute("INSERT INTO game_results (game_id, session_id, status, "
                "win_detected, level_completions, created_at) VALUES (?,?,?,?,?,?)",
                (game, sid, "completed", win, completions, created))
    t0 = br.parse_utc(created)
    for i in range(actions):
        t = br.stamp(t0 + dt.timedelta(seconds=gap_s * i))
        con.execute("INSERT INTO action_traces (session_id, game_id, "
                    "action_number, timestamp, created_at, level_number) "
                    "VALUES (?,?,?,?,?,?)",
                    (sid, game, 1, t, t, levels[i % len(levels)]))


def _write(path: str, records, mtime: str = None) -> None:
    """A constructed stream. `mtime` sets the file's modification time, which is
    THE ONLY CLOCK a fabric stream has and therefore the only thing the tool's
    MTIME BRACKET can read -- so a test that wants a particular bracket state
    must set it rather than inherit whatever the filesystem stamped."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        for i, r in enumerate(records, 1):
            rec = dict(r)
            rec.setdefault("seq", i)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if mtime is not None:
        epoch = (br.parse_utc(mtime)
                 - dt.datetime(1970, 1, 1)).total_seconds()
        os.utime(path, (epoch, epoch))


def _run(root, hours=1.0, since=None, box=None, now=NOW) -> str:
    """Run the report against a constructed root and return its text."""
    out = io.StringIO()
    with mock.patch.object(br, "RUNS", root):
        w = br.resolve_window(hours, since, now)
        br.report(w, box, out)
    return out.getvalue()


def _game_line(text: str, game: str, section_marker: str) -> str:
    """The first line after `section_marker` that names `game`."""
    seen = False
    for line in text.splitlines():
        if line.startswith(section_marker):
            seen = True
            continue
        if seen and game in line:
            return line
    return ""


@pytest.fixture
def root(tmp_path):
    """One box, one game, with the window straddling its episodes.

    Window under NOW/--hours 1 is (11:00, 12:00]. Two episodes land inside it,
    two in the previous window, and one exactly ON the boundary -- that one has
    every trace stamped at 11:00:00 exactly (gap_s=0), so it tests the boundary
    rather than straddling it.
    """
    base = str(tmp_path / "swarm")
    con = _mkdb(os.path.join(base, "bx01", "core_data.db"))
    game = "bx01-deadbeef"
    _episode(con, game, "s_prev_a", "2026-08-22 10:10:00")
    _episode(con, game, "s_prev_b", "2026-08-22 10:40:00")
    _episode(con, game, "s_edge", "2026-08-22 11:00:00", gap_s=0)   # == start
    _episode(con, game, "s_in_a", "2026-08-22 11:20:00", actions=6)
    _episode(con, game, "s_in_b", "2026-08-22 11:50:00", actions=2)
    for mode, n in (("pioneer", 3), ("generalist", 2)):
        for i in range(n):
            con.execute("INSERT INTO agent_operating_modes (agent_id, game_id, "
                        "operating_mode, score_achieved, win_achieved, "
                        "progress_score, created_at) VALUES (?,?,?,?,?,?,?)",
                        ("a%d" % i, game, mode, 0.0, 0, 0.5,
                         "2026-08-22 11:30:00"))
    con.execute("INSERT INTO agents VALUES ('a0', 0, NULL)")
    con.execute("INSERT INTO agents VALUES ('a1', 1, NULL)")
    con.commit()
    con.close()

    fab = os.path.join(base, "bx01", "ego_fabric")
    # MTIME PINNED, and it must be. This stream inherited the filesystem's real
    # timestamp, so the fixture's meaning depended on WHEN THE SUITE RAN: the
    # window under NOW is (11:00, 12:00] on 2026-08-22, and at 11:00 UTC that day
    # real time walked into the frozen window. The stream's mtime went from
    # "before the window" to "inside it", the tool correctly switched from a
    # sound zero to NOT COMPARABLE, and the test went red having tested nothing
    # but the clock. `_write`'s own docstring already said a test wanting a
    # particular bracket state must SET it -- this one call had not.
    _write(os.path.join(fab, "collective", "mint_verdicts.jsonl"), [
        {"verdict": "mint", "game": game, "level": 0},
        {"verdict": "mint", "game": game, "level": 0},
        {"verdict": "rederivation", "game": game, "level": 0},
        {"verdict": "reject", "game": game, "level": 0},
        {"verdict": "quarantine", "game": game, "level": 0},
    ], mtime="2026-08-22 09:30:00")
    _write(os.path.join(fab, "collective", "atoms.jsonl"), [
        {"id": "at1", "type": "EFFECT", "game": game, "level": 0,
         "origin": "local", "atom": {"kind": "EFFECT", "key": "k1"}},
        {"id": "at2", "type": "EFFECT", "game": game, "level": 0,
         "origin": "local", "atom": {"kind": "EFFECT", "key": "k2"}},
        # a superseding append on at1 -- same id, so it is ONE atom, not two
        {"id": "at1", "type": "EFFECT", "game": game, "level": 0,
         "ctx_min": True, "atom": {"kind": "EFFECT", "key": "k1"}},
    ])
    _write(os.path.join(fab, "collective", "settlements.jsonl"), [
        {"agent": "a0", "game": game, "level": 0, "action": 1, "members": 1,
         "best": 0.0, "nontrivial": True},
    ])
    # THE RESIDUAL FIXTURE -- Figure 1's legal state, built on purpose:
    # three slots bet, exactly ONE carries mass, and the across-slot mean is
    # 1.0/3 = 0.333, which is below the smallest possible positive residual.
    _write(os.path.join(fab, "personal", "ag0", "narration.jsonl"), [
        {"id": "n:%s:1:1" % game, "step": 1, "sq": 1, "point": "BET",
         "side": "bet", "range": "EP", "game": game},
        {"id": "n:%s:1:4" % game, "step": 1, "sq": 4, "point": "PERCEIVE",
         "side": "outcome", "range": "EP", "game": game,
         "slots": {"WORKSPACE": {"bet": True, "residual": 1.0, "bin": None},
                   "BODY": {"bet": True, "residual": 0.0, "bin": None},
                   "REFERENCE": {"bet": True, "residual": 0.0, "bin": None}}},
    ])
    return base


# ── 1 · every rate carries its denominator ───────────────────────────────────

def test_every_rate_prints_its_denominator(root):
    """ASSERTED (mandate item 3). Not one series may print a bare count."""
    text = _run(root)
    assert "MINTED" in text and "REDERIVED" in text
    # the learning rates come through as n/d with their quotient
    assert "2/5 = 0.400" in text          # mints / all verdicts
    assert "1/5 = 0.200" in text          # rederivations / all verdicts
    # the economy's categories, with the window's own denominator
    assert "3/5 = 0.600" in text          # pioneers / assignments in window
    assert "2/5 = 0.400" in text          # generalists / assignments in window
    # the exposure completion rate carries its denominator too
    assert "EXPOSURE" in text
    # and the atoms denominator counts DISTINCT IDS, not stream records: the
    # fixture has three atom records over two ids (one superseding append).
    assert "library 3 recs / 2 keys" in text


def test_no_series_prints_a_bare_count_as_a_rate(root):
    """ASSERTED. Every line labelled with a series name carries a '/'."""
    text = _run(root)
    for line in text.splitlines():
        stripped = line.strip()
        for label in ("MINTED", "REDERIVED", "COMPOSED"):
            if stripped.startswith(label) or (" %s " % label) in stripped:
                assert "/" in stripped, line


# ── 2 · the window boundary ──────────────────────────────────────────────────

def test_window_boundary_is_start_exclusive_end_inclusive(root):
    """ASSERTED. The 11:00:00 episode sits exactly on the window start and
    belongs to the PREVIOUS window, so two consecutive beats partition the
    history instead of counting that episode twice."""
    text = _run(root)                                  # (11:00, 12:00]
    line = _game_line(text, "bx01-deadbeef", "D2.")
    assert line.split()[2] == "2", line                # the edge episode is OUT
    # widen by ONE SECOND and the boundary episode joins this window, and only it
    wider = _run(root, since="2026-08-22 10:59:59")    # (10:59:59, 12:00]
    wide_line = _game_line(wider, "bx01-deadbeef", "D2.")
    assert wide_line.split()[2] == "3", wide_line


def test_previous_window_is_the_same_length_and_abuts(root):
    """ASSERTED. Section C's comparison window is exactly the span before."""
    w = br.resolve_window(1.0, None, NOW)
    assert w.prev_end == w.start
    assert w.end - w.start == w.start - w.prev_start


# ── 3 · STALLED across two identical windows ─────────────────────────────────

def test_stalled_fires_across_two_identical_windows(tmp_path):
    """ASSERTED (mandate item 5). Two windows with the same content must be
    named as stalled WITH THE REASON, not printed as the same number twice."""
    base = str(tmp_path / "swarm")
    con = _mkdb(os.path.join(base, "bx02", "core_data.db"))
    game = "bx02-cafef00d"
    for created in ("2026-08-22 10:20:00", "2026-08-22 11:20:00"):
        _episode(con, game, "s" + created, created, actions=4)
    con.commit()
    con.close()
    text = _run(base)
    assert "C. STALLED" in text
    stalled = [ln for ln in text.splitlines() if ln.strip().startswith(
        ("GROUND", "EXPOSURE", "LEARNING", "ECONOMY"))]
    assert stalled, text
    assert any("GROUND" in ln and "unchanged" in ln for ln in stalled)
    assert any("EXPOSURE" in ln and "1 episodes both windows" in ln
               for ln in stalled)
    # the REASON is the point: a bare "unchanged" would be the flat number
    assert any("0 levels completed in either" in ln for ln in stalled)


def test_stalled_says_no_records_in_window_when_the_bracket_is_a_sound_zero(root):
    """ASSERTED. Mandate item 5 asks for 'no verdict records in window' vs
    'verdicts present, 0 mints'. The fixture's verdict stream was last written
    before the window opened, so the MTIME BRACKET can soundly say the first --
    and it says exactly that, with the mtime as its evidence."""
    text = _run(root)
    assert "LEARNING" in text
    assert "no verdict record in either window" in text
    assert "stream mtime precedes both" in text


def test_stalled_refuses_to_call_a_clockless_active_stream_stalled(root):
    """ASSERTED. When the verdict stream was written INSIDE the window, the
    bracket cannot separate stall from motion, and the tool must say so rather
    than pick one. A flat number reported as stalled would be the mandate's
    'measuring nothing' dressed as a finding."""
    _write(os.path.join(root, "bx01", "ego_fabric", "collective",
                        "mint_verdicts.jsonl"),
           [{"verdict": "mint", "game": "bx01-deadbeef", "level": 0}],
           mtime="2026-08-22 11:30:00")            # inside (11:00, 12:00]
    text = _run(root)
    assert "NOT COMPARABLE" in text
    assert "stall cannot be distinguished from motion" in text


# ── 4 · NOT READABLE on a missing topic ──────────────────────────────────────

def test_missing_topic_prints_not_readable_and_names_it(tmp_path):
    """ASSERTED. An absence is named; a zero never stands in for one."""
    base = str(tmp_path / "swarm")
    con = _mkdb(os.path.join(base, "bx03", "core_data.db"))
    _episode(con, "bx03-01", "s1", "2026-08-22 11:30:00")
    con.commit()
    con.close()
    text = _run(base)
    assert br.NOT_READABLE in text
    assert "the stream does not exist on this box" in text
    assert "mint_verdicts.jsonl" in text
    # the residual rung says the absence rather than printing 0 slots
    assert "no PERCEIVE record in the sampled tail" in text


def test_absent_series_are_never_reported_as_zero_rates(tmp_path):
    """ASSERTED. RETIRED and USED have no writer in the live build; the tool
    must name the record that would close each, not print 0/N."""
    base = str(tmp_path / "swarm")
    con = _mkdb(os.path.join(base, "bx04", "core_data.db"))
    _episode(con, "bx04-01", "s1", "2026-08-22 11:30:00")
    con.commit()
    con.close()
    fab = os.path.join(base, "bx04", "ego_fabric", "collective")
    _write(os.path.join(fab, "mint_verdicts.jsonl"),
           [{"verdict": "mint", "game": "bx04-01", "level": 0}])
    _write(os.path.join(fab, "atoms.jsonl"),
           [{"id": "a1", "game": "bx04-01", "level": 0,
             "atom": {"kind": "EFFECT", "key": "k"}}])
    _write(os.path.join(fab, "settlements.jsonl"),
           [{"agent": "a", "game": "bx04-01", "level": 0, "action": 1,
             "members": 1, "best": 0.0, "nontrivial": True}])
    text = _run(base)
    assert "RETIRED" in text and "eviction append" in text
    assert "USED" in text and "settlements.atom_key written non-null" in text


# ── 5 · the exposure verdict, both ways ──────────────────────────────────────

def test_exposure_measured_when_the_window_clears_the_derived_floor(root):
    """ASSERTED. A never-scored game's floor is split_half's stated minimum of
    two sessions; two episodes in the window clears it."""
    text = _run(root)
    assert "EXPOSURE 2/2: MEASURED" in text
    assert br.BELOW_FLOOR.strip() not in text


def test_exposure_unmeasured_below_the_floor_and_suffixes_later_lines(tmp_path):
    """ASSERTED (FIGURE 3). A game that HAS scored gets a floor derived from
    its own event rate; a window below it reads UNMEASURED, and every later
    line for that game is suffixed."""
    base = str(tmp_path / "swarm")
    game = "bx05-99887766"
    con = _mkdb(os.path.join(base, "bx05", "core_data.db"))
    # FOUR episodes of history, ONE of which completed a level, so split_half
    # measures p = 1/4 and k = ceil(ln 0.05 / ln 0.75) = 11 -- the window floor
    # is 2k = 22 episodes. The number is DERIVED from the fixture's own history,
    # which is the property under test: change the history and the floor moves.
    _episode(con, game, "h1", "2026-08-20 09:00:00")
    _episode(con, game, "h2", "2026-08-20 09:30:00")
    _episode(con, game, "h3", "2026-08-20 10:00:00", completions=1)
    _episode(con, game, "w1", "2026-08-22 11:30:00")
    con.execute("INSERT INTO agent_operating_modes (agent_id, game_id, "
                "operating_mode, score_achieved, win_achieved, progress_score, "
                "created_at) VALUES (?,?,?,?,?,?,?)",
                ("a0", game, "pioneer", 0.0, 0, 0.5, "2026-08-22 11:30:00"))
    con.commit()
    con.close()
    fab = os.path.join(base, "bx05", "ego_fabric")
    _write(os.path.join(fab, "collective", "mint_verdicts.jsonl"),
           [{"verdict": "mint", "game": game, "level": 0},
            {"verdict": "reject", "game": game, "level": 0}])
    _write(os.path.join(fab, "collective", "atoms.jsonl"),
           [{"id": "a1", "game": game, "level": 0,
             "atom": {"kind": "EFFECT", "key": "k"}}])
    _write(os.path.join(fab, "personal", "ag0", "narration.jsonl"),
           [{"id": "n:%s:1:4" % game, "step": 1, "sq": 4, "point": "PERCEIVE",
             "side": "outcome", "range": "EP", "game": game,
             "slots": {"WORKSPACE": {"bet": True, "residual": 4.0}}}])

    with mock.patch.object(br, "RUNS", base):
        k, p, note = br.exposure_floor("bx05")
    assert (k, round(p, 3)) == (22, 0.25), (k, p, note)
    assert "ln(0.05)" in note

    text = _run(base)
    assert "UNMEASURED -- exposure 1/22" in text
    # ... and the suffix rides every later line for that game
    d3 = _game_line(text, game, "D3.")
    assert br.BELOW_FLOOR.strip() in d3, d3
    learn = _game_line(text, game, "A. LEARNING")
    assert learn and br.BELOW_FLOOR.strip() in learn, learn
    perf = _game_line(text, game, "B. THE ECONOMY")
    assert perf and br.BELOW_FLOOR.strip() in perf, perf


# ── 6 · the residual: one live slot, and never a mean ────────────────────────

def test_residual_reports_one_live_slot_and_prints_no_mean(root):
    """ASSERTED (FIGURE 1). The fixture is the legal state: three slots bet,
    one carries mass 1.0, the across-slot mean is 0.333. The tool must report
    1/3 with the slot named, must count the step as the legal state, and must
    NEVER put the mean on the page -- that number is exactly the average a live
    signal disappears into."""
    text = _run(root)
    line = _game_line(text, "bx01-deadbeef", "D3.")
    assert "1/3" in line, line                     # positive mass / slots bet
    assert "WORKSPACE" in line, line               # the slot id, named
    assert "1.0" in line, line                     # the largest SINGLE slot
    # the legal-state counter fired once
    res = None
    with mock.patch.object(br, "RUNS", root):
        res = br.residual("bx01")
    d = res["per_game"]["bx01-deadbeef"]
    assert d == {"steps": 1, "bet": 3, "positive": 1, "largest": 1.0,
                 "largest_slot": "WORKSPACE",
                 "largest_step": "n:bx01-deadbeef:1:4", "legal_state": 1}
    # THE MEAN IS NOWHERE ON THE PAGE
    for forbidden in ("0.33", "0.333"):
        assert forbidden not in text, forbidden


def test_residual_aggregation_epsilon_is_derived_not_a_dial():
    """ASSERTED. Every residual the bank writes is an integer count or an
    integer position delta, so the smallest positive residual is 1.0 and the
    epsilon is that value -- not a tolerance somebody chose."""
    assert br.AGG_EPS == 1.0


def test_residual_absence_prints_the_stated_sentence(tmp_path):
    """ASSERTED. If no per-slot residual reaches disk anywhere, the tool says
    so in one fixed sentence rather than reporting an empty rate."""
    base = str(tmp_path / "swarm")
    con = _mkdb(os.path.join(base, "bx06", "core_data.db"))
    _episode(con, "bx06-01", "s1", "2026-08-22 11:30:00")
    con.commit()
    con.close()
    text = _run(base)
    assert ("the bank writes no per-slot residual -- rung 1 has no instrument"
            in text)


# ── 7 · E · CARRIED COST (Seat 4's rider) ────────────────────────────────────

def test_carried_cost_counts_records_from_a_constructed_stream(root):
    """ASSERTED. records x games is the priming parse a worker pays per new
    game; the record count comes off the constructed stream, not a guess."""
    text = _run(root)
    assert "E. CARRIED COST" in text
    assert "implied parses" in text
    with mock.patch.object(br, "RUNS", root):
        con = br._connect(br.db_path("bx01"))
        c = br.carried_cost("bx01", con)
        con.close()
    assert c["records"] == 2                    # the two narration lines written
    assert c["games"] == 1
    assert c["implied_parses"] == 2
    assert c["streams"] == 1
    assert c["biggest_records"] == 2
    line = [ln for ln in text.splitlines() if ln.strip().startswith("bx01")]
    assert line, text


# ── 8 · the standing constraint, made structural ─────────────────────────────

def test_no_function_reads_the_frame_blobs_or_the_frame_stream():
    """ASSERTED. AST over the tool: not one string constant, attribute or name
    anywhere in it mentions the frame blob columns or the per-level frame
    stream. The proctor diagnoses the machinery and never the board, and this
    is that rule enforced rather than promised."""
    with open(TOOL_SRC, encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for bad in FORBIDDEN:
                if bad in node.value:
                    hits.append((bad, "string", getattr(node, "lineno", 0)))
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN:
            hits.append((node.attr, "attribute", node.lineno))
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN:
            hits.append((node.id, "name", node.lineno))
    assert hits == [], hits
    # and nowhere in the raw bytes either -- a comment naming one is a lead a
    # later editor follows.
    for bad in FORBIDDEN:
        assert bad not in src, bad


def test_every_select_names_its_columns():
    """ASSERTED. `SELECT *` would pull the frame blobs in by accident; the tool
    must name every column it reads."""
    with open(TOOL_SRC, encoding="utf-8") as fh:
        src = fh.read()
    assert "SELECT *" not in src


def test_the_exemplar_decision_is_recorded_in_the_docstring():
    """ASSERTED (house rule: NAME THE EXEMPLAR). Two modules of this genus exist
    in the tree, unreachable -- lab/trend_tracker.py's convergence detection and
    lab/comparative_analyst.py's cohort effect sizes. This tool does not call
    either, and an unstated re-derivation is the thing the rule forbids, so the
    reason must be in the module docstring where a later reader will find it.
    This test fails if the citation is ever dropped."""
    doc = br.__doc__ or ""
    assert "lab/trend_tracker.py" in doc
    assert "lab/comparative_analyst.py" in doc
    assert "NAME THE EXEMPLAR" in doc
    # and the reason, not just the name
    assert "ensure_schema" in doc                 # it writes; the beat is read-only
    assert "GENERATION" in doc                    # wrong unit for a wall-clock beat
    # neither module is imported by the tool
    with open(TOOL_SRC, encoding="utf-8") as fh:
        src = fh.read()
    body = src.split('"""', 2)[2]                 # everything after the docstring
    assert "trend_tracker" not in body
    assert "comparative_analyst" not in body


def test_the_db_is_opened_read_only():
    """ASSERTED. The fleet is a live artefact; the beat may never write to it."""
    with open(TOOL_SRC, encoding="utf-8") as fh:
        src = fh.read()
    assert "mode=ro" in src
    assert src.count("sqlite3.connect(") == 1


# ── 9 · import is side-effect free ───────────────────────────────────────────

def test_import_has_no_side_effects():
    """ASSERTED (the D-6 lesson at tooling grain, the exemplar's CLEAN IMPORT).
    Importing the tool opens no file, makes no directory and spawns nothing --
    so a gate may import it without touching the fleet."""
    real_open = builtins.open

    def boom(*a, **k):
        raise AssertionError("import opened a file: %r" % (a[:1],))

    with mock.patch.object(builtins, "open", boom), \
            mock.patch.object(os, "makedirs", boom), \
            mock.patch.object(sqlite3, "connect", boom):
        sys.modules.pop("tools.beat_rates", None)
        mod = importlib.import_module("tools.beat_rates")
        importlib.reload(mod)
    builtins.open = real_open
    assert mod.RUNS.endswith(os.path.join(".runs", "swarm"))
