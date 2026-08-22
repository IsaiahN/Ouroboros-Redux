"""BEAT RATES -- the hourly beat, as RATES WITH DENOMINATORS, per GAME, never averaged.

THE TWO LAWS THIS TOOL IS BUILT AGAINST, stated because a build that cannot name
its law was not briefed:

  FIGURE 1 (The Agent). "The ground enters as the only metric. Everything else
  either produces a residual or consumes the library. These do not count:
  coverage, and compression achieved; predicates minted, and credibility
  accrued. They are FRAME-INTERNAL. A frame cannot score itself with a quantity
  it also produces." So THE GROUND is printed FIRST and alone, and every other
  section carries the literal tag [frame-internal]. Figure 1 again, on the
  residual: "The residual is indexed by object slot, not aggregated. Support is
  satisfied when some slot carries positive mass, so a global residual near zero
  with one live slot is a legal state and not an inert one. AGGREGATING ACROSS
  SLOTS IS HOW A LIVE SIGNAL DISAPPEARS INTO AN AVERAGE." So section D3 reports
  per-slot counts and the LARGEST SINGLE SLOT -- never a mean -- and counts the
  steps where the aggregate would have said "nothing here" while a slot was live.

  FIGURE 5 (The Mint Pipeline). "MACHINERY FIRING IS NOT THE MILESTONE. A running
  system can mint and still return nothing new, which is exactly what the third
  guard exists to record." So section A's mint rate is never reported as progress,
  and section B's NOVEL line -- keys that appear in no stream before the window --
  is marked as the only line that speaks to novelty.

Read also against FIGURE 3 (The Dependency Chain): "a reading taken below the
break is not a weak reading, it is a reading of nothing", and "a link with no
instrument is not a link that works, it is a link nobody has looked at". Section
D2 (EXPOSURE) exists because that rung had no instrument: before any frame-
internal rate means anything, the agent must have been in contact with the world
often enough for the reading to exist at all. A game below its exposure floor has
every later line SUFFIXED "(below exposure floor)".

MANDATE ITEMS 3, 4, 5 (record/corpus/THE_PROCTOR_MANDATE.md):
  3. "The beat needs a RATE, not a state ... a count that only goes up is not a
     learning curve." Every series here prints numerator/denominator.
  4. Per beat, each with its denominator: agents by category and the shift;
     performance by category AND BY GAME, per-game, never averaged; retirements
     with the evidence; the library; and what was minted that did not exist.
  5. "Every beat, name what has not moved since the last one and why." Section C
     compares this window against the immediately preceding window of equal
     length and prints the reason the streams themselves give.

═══════════════════════════════════════════════════════════════════════════════
THE CLOCK, WHICH IS THE CENTRAL FINDING OF BUILDING THIS INSTRUMENT
═══════════════════════════════════════════════════════════════════════════════

There are TWO record families under .runs/swarm/<box>/ and only ONE of them has
a clock.

  * core_data.db -- REAL UTC TIMESTAMPS (game_results.created_at,
    action_traces.created_at/timestamp, agent_operating_modes.created_at).
    Sections D, D2, the economy's categories/performance, and E's game count
    window on this and are true windowed rates.

  * the ego_fabric JSONL streams -- NO TIMESTAMP ANYWHERE. Surveyed read-only
    over every topic present on the 25 live boxes (atoms, mint_verdicts,
    settlements, narration, starvation, swallow, ideas, idea_events,
    goal_hypotheses, frontier_harvest, frontier_paths, import_queue,
    import_candidates, replay_outcomes, rho_readings, gate): every record
    carries `seq` (fabric.append's monotonic per-stream counter) plus its own
    domain fields, and NOT ONE carries a wall-clock stamp. The only clock any
    stream has is its FILE MTIME.

THE MTIME BRACKET is therefore the only sound window over a fabric stream, and
this tool applies it literally:

    mtime(stream) <  window start  ->  0 records landed in the window. This is a
                                       SOUND ZERO, printed as a rate.
    mtime(stream) >= window start  ->  an unknown SUFFIX of the stream landed in
                                       the window. The in-window count is
                                       NOT READABLE. The all-time totals are
                                       printed beside it, labelled
                                       [all-time, NOT a rate], so the
                                       denominators are visible and nobody
                                       mistakes a monotone count for a rate.

Nothing is interpolated, apportioned, or joined across the two families. A
narration record cannot be dated by matching it against an action_traces row:
the loop's `step` resets, several agents share a box, and any such mapping would
be a fabrication wearing a measurement's clothes. The record that would close
this is named at every NOT READABLE line: a per-record UTC field on
fabric.append, or a persisted per-beat seq watermark.

═══════════════════════════════════════════════════════════════════════════════
NAME THE EXEMPLAR: WHAT THIS TOOL DOES NOT REUSE, AND WHY
═══════════════════════════════════════════════════════════════════════════════

The codebase inventory flagged two unreachable modules of the same genus, and the
house rule is to cite a correct implementation rather than re-derive it. Both
were READ before this tool was finished. Neither is called, for reasons that are
about grain and discipline rather than quality:

  lab/trend_tracker.py -- experiment memory + `detect_convergence`. Closest to
  section C (STALLED), and it does not fit on four counts.
    1. WRONG UNIT AND WRONG CLOCK. Its convergence is indexed by GENERATION over
       `lab_metric_snapshots`; the beat is indexed by a wall-clock WINDOW. That
       table does not exist on any fleet box (checked read-only, 25 boxes), so
       the unit it compares has no rows in the records this beat reads.
    2. IT WRITES. Every public entry point calls `ensure_schema()`, which
       CREATE-TABLEs and commits into core_data.db. This tool opens the fleet
       READ-ONLY, under HOLD; calling it would write to 25 live databases.
    3. WRONG DATABASE. `DB_PATH` defaults to the repo-root core_data.db -- ONE
       database. The beat's grain is per box, because the mandate's rule is
       per-GAME and never averaged.
    4. IT AVERAGES, AND IT ANSWERS A DIFFERENT QUESTION. `detect_convergence`
       compares mean(last 5 snapshots) with mean(previous 5) and calls a gap
       below 0.001 "converged". CONVERGED and STALLED are different claims:
       mandate item 5 asks what has not moved since the LAST BEAT and WHY, with
       the reason the records give. A boolean over a smoothed average carries no
       reason, and the smoothing is the very move Figure 1 warns about.

  lab/comparative_analyst.py -- cohort split + Cohen's d feature ranking. It
  answers "which feature separates successful sessions from failed ones in this
  GENERATION": a cohort effect size, not a rate with a denominator, with no
  window, no previous window and no way to say NOT READABLE (it returns
  {"error": ...} or a zero where a record is absent, which is the failure this
  beat exists to avoid). Its `game_type = game_id.split("-")[0]` also collapses
  the game key to the box prefix, and Cohen's d is a difference of MEANS over a
  pooled SD -- an aggregate where the mandate wants the per-game number.
  ONE THING IT CORROBORATES, and it is worth saying: its success criterion is
  `level_completions > 0`, the same ground predicate section D2 uses to decide
  that an episode crossed a level. Two independent readers picked the same
  ground, which is evidence for the predicate rather than for reuse.

  engines/cognition/edge_inference.py + manual_tools/validate_inferred_edges.py
  were also read: they infer and validate edges of the COGNITIVE RUNG GRAPH
  (dependency / implication / fallback / coactivation between rungs). A
  different rung of the ladder entirely -- nothing there produces a windowed
  rate, an exposure count or a per-slot residual.

So the implementation below is from scratch, deliberately, and this paragraph is
the record of that decision. None of those modules were repaired or re-wired;
they are HELD for the GM.

═══════════════════════════════════════════════════════════════════════════════

USAGE
  python tools/beat_rates.py --hours 1
  python tools/beat_rates.py --since "2026-08-22 01:00:00"    # UTC, per split_half
  python tools/beat_rates.py --hours 6 --box ls20

TIMESTAMPS ARE UTC IN THESE DATABASES -- the same rule tools/split_half.py states
and for the same reason: comparing a local wall-clock string against a UTC column
silently matches most of the day.

THE PROCTOR'S STANDING CONSTRAINT IS STRUCTURAL HERE, not a promise. This tool
opens core_data.db read-only and names every column it selects; it never selects
the frame blob columns of action_traces and never opens the per-level frame
stream. It reads records, streams and logs -- the machinery -- and never the
board. tests/gate/test_beat_rates.py asserts that by AST over this file.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, ".runs", "swarm")

if ROOT not in sys.path:                      # importable as `tools.beat_rates`
    sys.path.insert(0, ROOT)

# ── the constants, each with its derivation (KNOBS.md REGISTER O, row O5) ─────

# THE AGGREGATION EPSILON, DERIVED -- NOT GUESSED. Figure 1's legal state is "a
# global residual near zero with one live slot". Every residual the bank writes
# is INTEGER-VALUED: PredictorBank._grid_residual returns float((p != o).sum()),
# a count of differing cells; BODY and RESOURCE return a Manhattan / absolute
# delta over integer positions. The smallest POSITIVE residual is therefore
# exactly 1.0, so an aggregate strictly below 1.0 is precisely an aggregate that
# has rounded a live slot away. No dial, no tolerance to tune.
AGG_EPS = 1.0

# THE RESIDUAL SAMPLE BOUND. The fleet's personal narration streams total ~505 MB
# over ~2500 files; a full parse is minutes and this is an HOURLY beat. The
# residual read therefore tail-reads the N most-recently-written agent streams
# per box. mtime-ordering is used because IT IS THE ONLY CLOCK THE FABRIC HAS
# (see THE CLOCK above), and the sample's size is printed as the denominator on
# every line it produces -- a bounded sample stated as one, never as the window.
RESIDUAL_STREAMS_PER_BOX = 8
# One tail block per stream, matching KnowledgeFabric._TAIL_BLOCK exactly: the
# fabric measured 155 bytes/record on the live boxes, so 64 KiB is several
# hundred records of PERCEIVE history per stream.
RESIDUAL_TAIL_BYTES = 65536

# Streams read by exact name. The tool never enumerates *.jsonl and so can never
# wander into a stream it has no business reading.
T_ATOMS = "atoms"
T_VERDICTS = "mint_verdicts"
T_SETTLEMENTS = "settlements"
T_NARRATION = "narration"

NOT_READABLE = "NOT READABLE"
BELOW_FLOOR = "  (below exposure floor)"


# ── window ────────────────────────────────────────────────────────────────────

def utcnow() -> _dt.datetime:
    """NAIVE UTC, which is what these records hold. `datetime.utcnow()` is
    deprecated on 3.12+, so the aware clock is read and the offset dropped --
    the value is identical and the warning does not land in the report."""
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)


def utc_from_timestamp(epoch: float) -> _dt.datetime:
    return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).replace(tzinfo=None)


def parse_utc(text: str) -> _dt.datetime:
    """A UTC timestamp in either of the two shapes these records use."""
    s = str(text).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError("unreadable UTC timestamp: %r" % (text,))


def stamp(when: _dt.datetime) -> str:
    return when.strftime("%Y-%m-%d %H:%M:%S")


class Window:
    """This window and the one immediately before it, of equal length. The
    previous window is not decoration: mandate item 5 is the whole reason the
    tool computes two of everything."""

    def __init__(self, start: _dt.datetime, end: _dt.datetime):
        self.start = start
        self.end = end
        self.span = end - start
        self.prev_start = start - self.span
        self.prev_end = start

    @property
    def hours(self) -> float:
        return max(1e-9, self.span.total_seconds() / 3600.0)

    def s(self) -> str:
        return stamp(self.start)

    def e(self) -> str:
        return stamp(self.end)


def resolve_window(hours: float, since: Optional[str],
                   now: _dt.datetime) -> Window:
    end = now
    start = parse_utc(since) if since else (now - _dt.timedelta(hours=hours))
    if start >= end:
        end = start + _dt.timedelta(hours=max(hours, 1e-6))
    return Window(start, end)


# ── boxes and the DB clock ────────────────────────────────────────────────────

def boxes(only: Optional[str] = None) -> List[str]:
    """Every box directory that carries a core_data.db, sorted."""
    out = []
    for db in sorted(glob.glob(os.path.join(RUNS, "*", "core_data.db"))):
        name = os.path.basename(os.path.dirname(db))
        if only and name != only:
            continue
        out.append(name)
    return out


def db_path(box: str) -> str:
    return os.path.join(RUNS, box, "core_data.db")


def _connect(path: str) -> Optional[sqlite3.Connection]:
    """READ-ONLY, always. A failure returns None and the caller prints an
    absence -- never a zero standing in for one."""
    if not os.path.isfile(path):
        return None
    try:
        return sqlite3.connect("file:" + path.replace(os.sep, "/") + "?mode=ro",
                               uri=True)
    except sqlite3.Error:
        return None


def _rows(con: sqlite3.Connection, sql: str, args: Tuple = ()) -> List[Tuple]:
    try:
        return list(con.execute(sql, args))
    except sqlite3.Error:
        return []


def _one(con: sqlite3.Connection, sql: str, args: Tuple = ()) -> Optional[Tuple]:
    r = _rows(con, sql, args)
    return r[0] if r else None


def game_keys(con: sqlite3.Connection) -> List[str]:
    """The game keys as the RECORDS carry them -- read off game_results, never
    written into this file. A box with no result rows yet reports none."""
    return [str(r[0]) for r in _rows(
        con, "SELECT DISTINCT game_id FROM game_results "
             "WHERE game_id IS NOT NULL ORDER BY game_id")]


# ── D · THE GROUND ────────────────────────────────────────────────────────────

def ground(con: sqlite3.Connection, w: Window) -> Dict[str, Dict[str, Any]]:
    """Per game: levels completed and games WON in the window. The only
    non-frame-internal section, and it is printed first."""
    out: Dict[str, Dict[str, Any]] = {}
    for row in _rows(con,
                     "SELECT game_id, COUNT(*), "
                     "COALESCE(SUM(level_completions),0), "
                     "COALESCE(SUM(CASE WHEN win_detected=1 THEN 1 ELSE 0 END),0) "
                     "FROM game_results WHERE created_at > ? AND created_at <= ? "
                     "GROUP BY game_id", (w.s(), w.e())):
        out[str(row[0])] = {"episodes": int(row[1]), "levels": int(row[2]),
                            "wins": int(row[3])}
    # The best LEVEL NUMBER touched in the window -- a non-frame column of
    # action_traces, and the one number that moves before level_completions does.
    for row in _rows(con,
                     "SELECT game_id, COALESCE(MAX(level_number),0) "
                     "FROM action_traces WHERE created_at > ? AND created_at <= ? "
                     "GROUP BY game_id", (w.s(), w.e())):
        out.setdefault(str(row[0]), {"episodes": 0, "levels": 0, "wins": 0})
        out[str(row[0])]["best_level"] = int(row[1])
    return out


# ── D2 · EXPOSURE (RUNG 0b) ───────────────────────────────────────────────────

def _median(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def exposure(con: sqlite3.Connection, w: Window) -> Dict[str, Dict[str, Any]]:
    """Per game, for the window: episodes and episodes/hour, actions per episode
    (MEDIAN -- a mean over episodes of wildly different length says nothing),
    seconds per action (median), and the completion rate.

    An EPISODE here is a session that actually acted -- a distinct session_id in
    action_traces inside the window. game_results rows are counted alongside it
    because the two disagree when a session is still open, and a reading that
    hides the disagreement is a reading of nothing (Figure 3)."""
    per: Dict[str, Dict[str, Any]] = {}
    sess: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in _rows(con,
                     "SELECT game_id, session_id, COUNT(*), "
                     "COUNT(DISTINCT level_number), MIN(timestamp), MAX(timestamp) "
                     "FROM action_traces WHERE created_at > ? AND created_at <= ? "
                     "GROUP BY game_id, session_id", (w.s(), w.e())):
        g = str(row[0])
        sess.setdefault(g, {})[str(row[1])] = {
            "actions": int(row[2]), "levels_touched": int(row[3]),
            "first": row[4], "last": row[5]}
    # completion by the results ledger too: a session whose result row recorded a
    # level completion crossed one even if its traces never showed two levels.
    crossed_by_result: Dict[str, set] = {}
    for row in _rows(con,
                     "SELECT game_id, session_id FROM game_results "
                     "WHERE created_at > ? AND created_at <= ? "
                     "AND COALESCE(level_completions,0) >= 1", (w.s(), w.e())):
        crossed_by_result.setdefault(str(row[0]), set()).add(str(row[1]))
    results_n: Dict[str, int] = {}
    for row in _rows(con,
                     "SELECT game_id, COUNT(*) FROM game_results "
                     "WHERE created_at > ? AND created_at <= ? GROUP BY game_id",
                     (w.s(), w.e())):
        results_n[str(row[0])] = int(row[1])

    for g in sorted(set(list(sess) + list(results_n))):
        s = sess.get(g, {})
        acts = [float(v["actions"]) for v in s.values()]
        crossed = sum(1 for sid, v in s.items()
                      if v["levels_touched"] > 1
                      or sid in crossed_by_result.get(g, set()))
        secs = _seconds_per_action(con, g, w)
        per[g] = {
            "episodes": len(s),
            "episodes_per_hour": len(s) / w.hours,
            "result_rows": results_n.get(g, 0),
            "actions_median": _median(acts),
            "seconds_per_action_median": secs,
            "crossed": crossed,
            "actions_total": int(sum(acts)),
        }
    return per


def _seconds_per_action(con: sqlite3.Connection, game: str,
                        w: Window) -> Optional[float]:
    """Median gap between consecutive actions INSIDE one session, over every
    session of this game in the window. Gaps are never taken across a session
    boundary: the pause between episodes is spawn cost, not action cost, and
    folding it in is exactly the average that hides the number."""
    gaps: List[float] = []
    prev_sid: Optional[str] = None
    prev_t: Optional[_dt.datetime] = None
    for sid, ts in _rows(con,
                         "SELECT session_id, timestamp FROM action_traces "
                         "WHERE game_id = ? AND created_at > ? AND created_at <= ? "
                         "ORDER BY session_id, timestamp", (game, w.s(), w.e())):
        try:
            t = parse_utc(str(ts))
        except ValueError:
            prev_sid, prev_t = None, None
            continue
        if prev_sid == str(sid) and prev_t is not None:
            d = (t - prev_t).total_seconds()
            if d >= 0:
                gaps.append(d)
        prev_sid, prev_t = str(sid), t
    return _median(gaps)


def exposure_floor(box: str) -> Tuple[int, float, str]:
    """k_g, the per-game exposure floor, DERIVED -- never a fixed constant.

    It is tools/split_half.py's own derivation, imported so that no
    transcription can drift: `required_per_half` measures p, the rate at which an
    episode reaches that game's best-ever level, from the game's OWN history and
    returns k = ceil(ln(0.05)/ln(1-p)) -- the episodes per half needed for a half
    to miss that best level with probability <= 5%. A split needs BOTH halves, so
    the window floor is 2k; and for a game that has NEVER SCORED, `required_per_half`
    returns k = 0 and split_half falls back to its stated minimum of two sessions
    (tools/split_half.py, `want = want if want >= 2 else 2`) -- because such a
    game's requirement is not a power threshold, it is "produce something".

    Returns (k_g, p, source-note)."""
    try:
        from tools import split_half as sh
    except Exception:                                   # pragma: no cover
        return 2, 0.0, "split_half unavailable; floor defaulted to its stated minimum 2"
    hist = sh.series(db_path(box), None)                # the rate from ALL history
    need, p = sh.required_per_half(hist)
    k = need * 2
    if k < 2:
        return 2, float(p), "never-scored: split_half's stated minimum of 2 sessions"
    return int(k), float(p), "2 x ceil(ln(0.05)/ln(1-p)), p=%.3f from %d episodes" % (
        p, len(hist))


# ── the fabric side: streams with no clock ────────────────────────────────────

def stream_path(box: str, topic: str, scope: str = "collective",
                agent: Optional[str] = None) -> str:
    base = os.path.join(RUNS, box, "ego_fabric")
    if scope == "personal":
        return os.path.join(base, "personal", str(agent), topic + ".jsonl")
    return os.path.join(base, scope, topic + ".jsonl")


def mtime_utc(path: str) -> Optional[_dt.datetime]:
    try:
        return utc_from_timestamp(os.path.getmtime(path))
    except OSError:
        return None


class Bracket:
    """THE MTIME BRACKET -- the only sound window over a stream with no clock.

    `state` is one of:
      "absent"  the stream does not exist;
      "zero"    mtime precedes the window: NOTHING landed in it. A sound zero.
      "opaque"  mtime falls inside the window: an unknown suffix landed in it,
                and the in-window count is NOT READABLE.
    """

    def __init__(self, path: str, w: Window):
        self.path = path
        self.mtime = mtime_utc(path)
        if self.mtime is None:
            self.state = "absent"
        elif self.mtime < w.start:
            self.state = "zero"
        else:
            self.state = "opaque"

    @property
    def readable_zero(self) -> bool:
        return self.state == "zero"

    def note(self, what: str) -> str:
        if self.state == "absent":
            return "%s: %s -- the stream does not exist on this box" % (
                NOT_READABLE, os.path.relpath(self.path, ROOT).replace(os.sep, "/"))
        if self.state == "zero":
            return "0 in window (stream last written %s UTC, before the window)" % (
                stamp(self.mtime))
        return ("%s: %s carries no per-record timestamp, and its file mtime "
                "(%s UTC) falls inside the window -- an unknown suffix landed "
                "here. Needed to close: a UTC field written by fabric.append, "
                "or a persisted per-beat seq watermark." % (
                    NOT_READABLE, what, stamp(self.mtime)))


def read_records(path: str) -> List[Dict[str, Any]]:
    """Every well-formed record of one stream. `_read_stream`'s own rules --
    strip, skip blank, skip corrupt, skip non-dict -- because a crash-torn tail
    is normal on these boxes and must never be fatal to a read."""
    out: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def read_tail_records(path: str, nbytes: int) -> List[Dict[str, Any]]:
    """The records inside the last `nbytes` of a stream, first partial line
    dropped. A BOUNDED SAMPLE, and every line it feeds prints its own size."""
    if not os.path.isfile(path):
        return []
    start = 0
    try:
        size = os.path.getsize(path)
        start = max(0, size - nbytes)
        with open(path, "rb") as fh:
            fh.seek(start)
            blob = fh.read(size - start)
    except OSError:
        return []
    if start > 0:
        cut = blob.find(b"\n")
        blob = blob[cut + 1:] if cut >= 0 else b""
    out: List[Dict[str, Any]] = []
    for raw in blob.decode("utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def agent_streams(box: str) -> List[str]:
    """Every personal narration stream on a box, by exact filename."""
    return sorted(glob.glob(os.path.join(
        RUNS, box, "ego_fabric", "personal", "*", T_NARRATION + ".jsonl")))


# ── D3 · THE RESIDUAL (RUNG 1) ────────────────────────────────────────────────

def residual(box: str) -> Dict[str, Any]:
    """The PER-SLOT residual, read from the agent's own settlement narration.

    WHERE IT LIVES, found by reading rather than guessing. PredictorBank.settle
    computes one residual PER SLOT (BODY / WORKSPACE / REFERENCE / RESOURCE) via
    `_grid_residual` and the delta predictors, and returns them as a per-slot
    verdict map. That map never reaches the collective `settlements` stream --
    betting.BetBook.settle writes only (agent, game, level, action, members,
    best, nontrivial) there, a FAMILY-BEST scalar with no slot in it. The per-slot
    residual reaches disk in exactly one place: the PERCEIVE point of the
    personal narration stream, whose payload is
        "slots": {SLOT: {"bet": bool, "residual": float, "bin": str|None}}
    written by cognitive_loop._narr_close, which is the loop point Figure 1's
    "one bet per object slot, every action" actually names.

    Reported per game: slots carrying positive mass / slots that bet, the
    LARGEST SINGLE-SLOT residual with its slot id -- never a mean -- and the
    count of steps in Figure 1's legal state: the aggregate below AGG_EPS while
    at least one slot is live."""
    streams = agent_streams(box)
    streams.sort(key=lambda p: (mtime_utc(p) or _dt.datetime.min), reverse=True)
    sample = streams[:RESIDUAL_STREAMS_PER_BOX]
    per: Dict[str, Dict[str, Any]] = {}
    for path in sample:
        for rec in read_tail_records(path, RESIDUAL_TAIL_BYTES):
            if rec.get("point") != "PERCEIVE":
                continue
            slots = rec.get("slots")
            if not isinstance(slots, dict):
                continue
            g = str(rec.get("game") or "")
            d = per.setdefault(g, {"steps": 0, "bet": 0, "positive": 0,
                                   "largest": 0.0, "largest_slot": None,
                                   "largest_step": None, "legal_state": 0})
            d["steps"] += 1
            live = 0
            mass: List[float] = []
            for name, v in sorted(slots.items()):
                if not isinstance(v, dict) or not v.get("bet"):
                    continue
                try:
                    r = float(v.get("residual", 0.0) or 0.0)
                except (TypeError, ValueError):
                    continue
                d["bet"] += 1
                mass.append(r)
                if r > 0.0:
                    d["positive"] += 1
                    live += 1
                if r > d["largest"]:
                    d["largest"] = r
                    d["largest_slot"] = str(name)
                    d["largest_step"] = rec.get("id")
            # FIGURE 1's legal state, counted rather than averaged away: the
            # aggregate an aggregating instrument would have printed, against the
            # slots that are actually live underneath it.
            if mass and live >= 1 and (sum(mass) / float(len(mass))) < AGG_EPS:
                d["legal_state"] += 1
    return {"per_game": per, "streams_sampled": len(sample),
            "streams_total": len(streams)}


# ── A · LEARNING RATES [frame-internal] ───────────────────────────────────────

def learning(box: str, w: Window) -> Dict[str, Any]:
    """Per game, over the atoms and mint_verdicts streams, under the bracket.

    minted    verdict=="mint"            / all verdicts
    used      atoms cited in a driven plan or a settled chain / atoms existing
    composed  atom records carrying `parts`/`kind`  / mints
    retired   atom records marked evicted           / atoms existing
    rederived verdict=="rederivation"    / all verdicts

    Every one of these is FRAME-INTERNAL by Figure 1 and is labelled so. The
    presence of each FIELD is PROBED on the live stream rather than assumed --
    a series whose field no writer emits is an absence to be named, not a zero
    to be printed."""
    vpath = stream_path(box, T_VERDICTS)
    apath = stream_path(box, T_ATOMS)
    spath = stream_path(box, T_SETTLEMENTS)
    out: Dict[str, Any] = {
        "verdict_bracket": Bracket(vpath, w),
        "atom_bracket": Bracket(apath, w),
        "settle_bracket": Bracket(spath, w),
        "per_game": {},
        "used_field": None,
        "evicted_field": False,
    }
    verdicts = read_records(vpath)
    atoms = read_records(apath)
    settles = read_records(spath)

    # PROBE: is there any record anywhere that says an atom was USED?
    if any(r.get("atom_key") for r in settles):
        out["used_field"] = "settlements.atom_key"
    elif any(r.get("composite") or r.get("settled") is not None
             for r in _plan_probe(box)):
        out["used_field"] = "narration.PLAN.composite/settled"
    # PROBE: is there any eviction append at all?
    out["evicted_field"] = any(bool(r.get("evicted")) for r in atoms)

    per: Dict[str, Dict[str, int]] = {}
    for r in verdicts:
        g = str(r.get("game") or "")
        d = per.setdefault(g, {"verdicts": 0, "mint": 0, "rederivation": 0,
                               "atoms": 0, "composed": 0, "retired": 0,
                               "used": 0})
        d["verdicts"] += 1
        v = r.get("verdict")
        if v == "mint":
            d["mint"] += 1
        elif v == "rederivation":
            d["rederivation"] += 1
    # DISTINCT ATOM IDS, not records: the atoms stream carries SUPERSEDING
    # APPENDS (ctx_min / ctx_conflict rewrite the same id), so counting records
    # would inflate the denominator by however often a context was minimised.
    ids: Dict[str, set] = {}
    comp: Dict[str, set] = {}
    cited: Dict[str, set] = {}
    for r in atoms:
        g = str(r.get("game") or "")
        d = per.setdefault(g, {"verdicts": 0, "mint": 0, "rederivation": 0,
                               "atoms": 0, "composed": 0, "retired": 0,
                               "used": 0})
        aid = r.get("id")
        if aid is not None:
            ids.setdefault(g, set()).add(str(aid))
        atom = r.get("atom") if isinstance(r.get("atom"), dict) else {}
        if (r.get("parts") or atom.get("parts")) and aid is not None:
            comp.setdefault(g, set()).add(str(aid))
        if r.get("evicted"):
            d["retired"] += 1
    for g, s in ids.items():
        per[g]["atoms"] = len(s)
    for g, s in comp.items():
        per[g]["composed"] = len(s)
    if out["used_field"] == "settlements.atom_key":
        # USED is "atoms cited", not "citations": one atom ridden ten thousand
        # times is one atom used, and counting the rides would print a ratio
        # above 1 and call it a rate.
        for r in settles:
            k = r.get("atom_key")
            if k:
                g = str(r.get("game") or "")
                per.setdefault(g, {"verdicts": 0, "mint": 0, "rederivation": 0,
                                   "atoms": 0, "composed": 0, "retired": 0,
                                   "used": 0})
                cited.setdefault(g, set()).add(str(k))
        for g, s in cited.items():
            per[g]["used"] = len(s)
    out["per_game"] = per
    # THE LIBRARY's settled/candidate split: composer.SETTLED_FIELD is absent
    # until a live settle, so a composite without it is a CANDIDATE, and saying
    # "composed" without saying "settled" would report machinery firing as a
    # milestone -- exactly what Figure 5 forbids.
    out["composites_settled"] = len({str(r.get("id")) for r in atoms
                                     if r.get("settled") and r.get("id")})
    out["composites_total"] = len(set().union(*comp.values()) if comp else set())
    return out


def _plan_probe(box: str) -> List[Dict[str, Any]]:
    """A bounded look at the PLAN point, to answer one question only: does any
    record on this box carry a composite citation at all?"""
    out: List[Dict[str, Any]] = []
    for path in agent_streams(box)[:RESIDUAL_STREAMS_PER_BOX]:
        for rec in read_tail_records(path, RESIDUAL_TAIL_BYTES):
            if rec.get("point") == "PLAN":
                out.append(rec)
    return out


def novel_keys(box: str) -> Dict[str, Any]:
    """NOVEL -- atoms whose key appears in no stream before the window. The only
    line that speaks to novelty (mandate item 4; Figure 5's third guard). It
    needs a window over the fabric, which the fabric cannot give; what IS
    computable and stated here is the key population and how many keys are held
    by exactly one atom record."""
    atoms = read_records(stream_path(box, T_ATOMS))
    seen: Dict[str, int] = {}
    for r in atoms:
        atom = r.get("atom") if isinstance(r.get("atom"), dict) else {}
        k = atom.get("key") or r.get("key")
        if k:
            seen[str(k)] = seen.get(str(k), 0) + 1
    return {"keys": len(seen), "records": len(atoms),
            "single_record_keys": sum(1 for v in seen.values() if v == 1)}


# ── B · THE ECONOMY ───────────────────────────────────────────────────────────

def economy(con: sqlite3.Connection, w: Window) -> Dict[str, Any]:
    """Categories and their shift, performance BY (game, category), retirements
    with the evidence field the system recorded, and the catalogue."""
    out: Dict[str, Any] = {}

    def cats(a: str, b: str) -> Dict[str, int]:
        return {str(r[0]): int(r[1]) for r in _rows(
            con, "SELECT operating_mode, COUNT(*) FROM agent_operating_modes "
                 "WHERE created_at > ? AND created_at <= ? GROUP BY operating_mode",
            (a, b))}

    out["categories"] = cats(w.s(), w.e())
    out["categories_prev"] = cats(stamp(w.prev_start), stamp(w.prev_end))
    out["assignments_total"] = (_one(
        con, "SELECT COUNT(*) FROM agent_operating_modes") or (0,))[0]

    # PERFORMANCE BY (GAME, CATEGORY) -- never averaged across games. The table
    # carries score_achieved / win_achieved / progress_score per assignment; it
    # carries NO level column, and game_results carries no agent_id, so
    # LEVELS per category has no join and is named as an absence below.
    out["perf"] = [
        (str(r[0]), str(r[1]), int(r[2]), float(r[3] or 0.0), int(r[4] or 0),
         float(r[5] or 0.0))
        for r in _rows(
            con,
            "SELECT game_id, operating_mode, COUNT(*), MAX(score_achieved), "
            "SUM(win_achieved), MAX(progress_score) FROM agent_operating_modes "
            "WHERE created_at > ? AND created_at <= ? "
            "GROUP BY game_id, operating_mode ORDER BY game_id, operating_mode",
            (w.s(), w.e()))]

    # RETIREMENTS -- who, when, on what evidence. `agents.is_active` is the
    # state and `agents.retirement_reason` is the evidence field the system
    # reserved for it; there is NO retirement timestamp column, so the "when"
    # is an absence, named.
    out["retired"] = (_one(
        con, "SELECT COUNT(*) FROM agents WHERE is_active = 0") or (0,))[0]
    out["active"] = (_one(
        con, "SELECT COUNT(*) FROM agents WHERE is_active = 1") or (0,))[0]
    out["retire_reasons"] = [
        (r[0], int(r[1])) for r in _rows(
            con, "SELECT retirement_reason, COUNT(*) FROM agents "
                 "WHERE is_active = 0 GROUP BY retirement_reason "
                 "ORDER BY COUNT(*) DESC")]
    out["retire_reason_recorded"] = sum(
        n for reason, n in out["retire_reasons"] if reason)

    # THE CATALOGUE: primitive_status holds the roster and its unlock columns.
    out["catalogue_rows"] = (_one(
        con, "SELECT COUNT(*) FROM primitive_status") or (0,))[0]
    out["catalogue_unlocked_by_nobody"] = (_one(
        con, "SELECT COUNT(*) FROM primitive_status "
             "WHERE unlocked_by_agent IS NULL") or (0,))[0]
    return out


# ── E · CARRIED COST [frame-internal] ─────────────────────────────────────────

_GAME_TOKEN = re.compile(rb'"game": "([^"]{1,64})"')


def carried_cost(box: str, con: Optional[sqlite3.Connection]) -> Dict[str, Any]:
    """THE PARSE A LONG-LIVED WORKER PAYS FOR EVERY NEW GAME (Seat 4's rider).

    persistence.PersistenceMonitor.from_fabric primes itself with
    `fabric.query("personal", "narration")` -- ONE WHOLE-STREAM read, per spine,
    per game. The narration stream grows every step and is never compacted (the
    janitor's policy table names import_queue, settlements and mint_verdicts and
    nothing else), so a worker that has been up for days pays a longer priming
    parse every time a new game starts. Same shape as the replay tails, which
    were invisible until they were measured at twelve minutes.

    Records are counted by NEWLINE over the raw bytes -- no JSON parse -- because
    the count is the number wanted and a full parse of the fleet's ~505 MB of
    narration is minutes. `implied_parses` = records x games: the record-reads a
    box has already paid, or will pay, for its priming folds."""
    records = 0
    nbytes = 0
    biggest = ("", 0, 0)
    for path in agent_streams(box):
        n = 0
        b = 0
        try:
            with open(path, "rb") as fh:
                while True:
                    chunk = fh.read(1 << 20)
                    if not chunk:
                        break
                    b += len(chunk)
                    n += chunk.count(b"\n")
        except OSError:
            continue
        records += n
        nbytes += b
        if n > biggest[1]:
            biggest = (os.path.basename(os.path.dirname(path)), n, b)
    games = len(game_keys(con)) if con is not None else 0
    return {"records": records, "bytes": nbytes, "games": games,
            "streams": len(agent_streams(box)),
            "implied_parses": records * games,
            "biggest_agent": biggest[0], "biggest_records": biggest[1],
            "biggest_bytes": biggest[2]}


# ── the report ────────────────────────────────────────────────────────────────

def _rate(num: int, den: int) -> str:
    if den <= 0:
        return "%d/%d (no denominator)" % (num, den)
    return "%d/%d = %.3f" % (num, den, num / float(den))


def _window_cell(br: Bracket) -> str:
    """What the MTIME BRACKET can soundly say about the window, in one cell."""
    if br.state == "zero":
        return "0/0 SOUND ZERO"
    if br.state == "absent":
        return "no such stream"
    return NOT_READABLE


def report(w: Window, only: Optional[str], out) -> int:
    names = boxes(only)
    p = lambda s="": print(s, file=out)                          # noqa: E731

    p("BEAT RATES -- rates with denominators, per GAME, never averaged")
    p("  as-of : %s UTC" % stamp(utcnow()))
    p("  window: %s -> %s UTC   (%.2f h)" % (w.s(), w.e(), w.hours))
    p("  prev  : %s -> %s UTC   (the STALLED comparison)"
      % (stamp(w.prev_start), stamp(w.prev_end)))
    p("  boxes : %d%s" % (len(names), "" if not only else "  (--box %s)" % only))
    p()
    p("  LAW (FIGURE 1): the ground is the only metric; coverage, compression,")
    p("       predicates minted and credibility accrued are FRAME-INTERNAL and do")
    p("       not count. The residual is indexed by object slot, not aggregated --")
    p("       aggregating across slots is how a live signal disappears into an")
    p("       average.")
    p("  LAW (FIGURE 5): machinery firing is not the milestone.")
    p()
    p("  CLOCK: core_data.db carries UTC timestamps -- sections D, D2, B and E's")
    p("       game count are true windowed rates. THE EGO_FABRIC STREAMS CARRY NO")
    p("       TIMESTAMP: every record has `seq` and its domain fields and nothing")
    p("       else, on every topic present on these boxes. The only clock a stream")
    p("       has is its file mtime, so the MTIME BRACKET is the only sound window")
    p("       over it: mtime before the window start = a SOUND ZERO; mtime inside")
    p("       the window = an unknown suffix landed here and the count is NOT")
    p("       READABLE. Nothing is joined across the two clocks.")

    ground_rows: List[Tuple] = []
    floors: Dict[str, Tuple[int, float, str]] = {}
    exposures: Dict[str, Dict[str, Any]] = {}
    below: Dict[str, bool] = {}
    stalls: List[str] = []

    # ── D ────────────────────────────────────────────────────────────────────
    p()
    p("D. THE GROUND -- levels completed and games WON in the window, per game.")
    p("   The only section here that is not frame-internal.")
    p("   %-22s %-6s %8s %8s %8s %10s" % ("game", "box", "results", "levels",
                                          "WON", "best-lvl"))
    total_levels = total_wins = 0
    for box in names:
        con = _connect(db_path(box))
        if con is None:
            p("   %-22s %-6s  %s: core_data.db unreadable" % ("--", box, NOT_READABLE))
            continue
        g = ground(con, w)
        if not g:
            p("   %-22s %-6s %8d %8d %8d %10s"
              % ("(no rows in window)", box, 0, 0, 0, "--"))
        for game in sorted(g):
            d = g[game]
            total_levels += d["levels"]
            total_wins += d["wins"]
            ground_rows.append((game, box, d))
            p("   %-22s %-6s %8d %8d %8d %10s"
              % (game, box, d["episodes"], d["levels"], d["wins"],
                 d.get("best_level", "--")))
        con.close()
    p("   FLEET: levels completed %d ; GAMES WON %d/%d boxes"
      % (total_levels, total_wins, len(names)))
    if total_wins == 0:
        p("   NO GAME WAS WON THIS WINDOW%s. Every number below is"
          % ("" if total_levels else " AND NO LEVEL WAS COMPLETED"))
        p("   FRAME-INTERNAL and none of it is progress (Figure 5): machinery")
        p("   firing is not the milestone.")

    # ── D2 ───────────────────────────────────────────────────────────────────
    p()
    p("D2. EXPOSURE -- RUNG 0b. Read against FIGURE 3: a reading taken below the")
    p("    break is a reading of nothing. This rung has never had an instrument.")
    p("    k_g is DERIVED per game, never a constant: 2 x ceil(ln(0.05)/ln(1-p))")
    p("    with p measured from that game's OWN history (tools/split_half.py")
    p("    required_per_half), or split_half's stated minimum of 2 for a game that")
    p("    has never scored.")
    p("    %-22s %-6s %6s %8s %9s %9s %9s  %s"
      % ("game", "box", "eps", "eps/h", "act/ep~", "s/act~", "cross", "verdict"))
    for box in names:
        con = _connect(db_path(box))
        if con is None:
            continue
        ex = exposure(con, w)
        k, pp, note = exposure_floor(box)
        floors[box] = (k, pp, note)
        keys = sorted(set(list(ex) + game_keys(con)))
        for game in keys:
            d = ex.get(game, {"episodes": 0, "episodes_per_hour": 0.0,
                              "actions_median": None,
                              "seconds_per_action_median": None,
                              "crossed": 0, "result_rows": 0})
            exposures[game] = dict(d, box=box, k=k)
            n = d["episodes"]
            measured = n >= k
            below[game] = not measured
            p("    %-22s %-6s %6d %8.2f %9s %9s %9s  %-28s %s"
              % (game, box, n, d["episodes_per_hour"],
                 ("%.1f" % d["actions_median"]) if d["actions_median"] is not None else "--",
                 ("%.2f" % d["seconds_per_action_median"])
                 if d["seconds_per_action_median"] is not None else "--",
                 "%d/%d" % (d["crossed"], n) if n else "0/0",
                 ("EXPOSURE %d/%d: MEASURED" % (n, k)) if measured
                 else ("UNMEASURED -- exposure %d/%d" % (n, k)),
                 "k_g from " + note))
        con.close()
    p("    completion rate = episodes that crossed a level / episodes; an episode")
    p("    is a session that ACTED (a distinct session_id in action_traces inside")
    p("    the window). act/ep~ and s/act~ are MEDIANS -- a mean over episodes of")
    p("    different length is the average Figure 1 warns about.")

    # ── D3 ───────────────────────────────────────────────────────────────────
    p()
    p("D3. RESIDUAL -- RUNG 1. Read against FIGURE 1: the residual is indexed by")
    p("    object slot, not aggregated. Source: the PERCEIVE point of the personal")
    p("    narration stream -- slots{SLOT:{bet,residual,bin}} -- which is the ONLY")
    p("    place a per-slot residual reaches disk. The collective `settlements`")
    p("    stream writes a family-best SCALAR (agent, game, level, action, members,")
    p("    best, nontrivial) with no slot in it, so it cannot answer this rung.")
    p("    %-22s %-6s %14s %10s %-12s %10s  %s"
      % ("game", "box", "pos/settled", "largest", "slot", "R~0&live", "note"))
    any_residual = False
    for box in names:
        res = residual(box)
        if not res["per_game"]:
            p("    %-22s %-6s  %s: no PERCEIVE record in the sampled tail of %d/%d"
              " agent narration streams" % ("--", box, NOT_READABLE,
                                            res["streams_sampled"],
                                            res["streams_total"]))
            continue
        for game in sorted(res["per_game"]):
            d = res["per_game"][game]
            any_residual = True
            p("    %-22s %-6s %14s %10.1f %-12s %10s  tail sample: %d steps over"
              " %d/%d streams"
              % (game, box, "%d/%d" % (d["positive"], d["bet"]), d["largest"],
                 d["largest_slot"] or "--", d["legal_state"], d["steps"],
                 res["streams_sampled"], res["streams_total"])
              + (BELOW_FLOOR if below.get(game) else ""))
    if not any_residual:
        p("    %s: the bank writes no per-slot residual -- rung 1 has no instrument"
          % NOT_READABLE)
    p("    largest is the LARGEST SINGLE-SLOT residual, never a mean. R~0&live")
    p("    counts FIGURE 1's legal state: the across-slot aggregate below %.1f while"
      % AGG_EPS)
    p("    at least one slot carries positive mass -- the steps at which an")
    p("    aggregating instrument would have reported nothing. %.1f is DERIVED, not"
      % AGG_EPS)
    p("    guessed: every residual the bank writes is an integer cell count or an")
    p("    integer position delta, so the smallest positive residual is exactly 1.")
    p("    THE WINDOW IS NOT APPLIED HERE -- narration carries no timestamp; this is")
    p("    a bounded tail sample and its denominator is printed on every line.")

    # ── A ─────────────────────────────────────────────────────────────────────
    p()
    p("A. LEARNING RATES [frame-internal] -- per window, per game, then a fleet")
    p("   line. Figure 1: none of this counts as ground. Figure 5: a system can")
    p("   mint enthusiastically and return nothing new.")
    fleet = {"verdicts": 0, "mint": 0, "rederivation": 0, "atoms": 0,
             "composed": 0, "retired": 0}
    learn_all: Dict[str, Dict[str, Any]] = {}
    p("   window cell = what the MTIME BRACKET can soundly say; the columns beside")
    p("   it are ALL-TIME populations with their denominators, NEVER rates.")
    p("   %-22s %-6s %-14s %-18s %-18s %-14s %-14s %s"
      % ("game", "box", "window", "MINTED/verdicts", "REDERIV/verdicts",
         "COMPOSED/mints", "USED/atoms", "composites (settled)"))
    no_evict: List[str] = []
    no_used: List[str] = []
    for box in names:
        L = learning(box, w)
        learn_all[box] = L
        vb, ab = L["verdict_bracket"], L["atom_bracket"]
        if not L["evicted_field"]:
            no_evict.append(box)
        if not L["used_field"]:
            no_used.append(box)
        if not L["per_game"]:
            p("   %-22s %-6s %s" % ("--", box, vb.note("mint_verdicts")))
            continue
        for game in sorted(L["per_game"]):
            d = L["per_game"][game]
            for k in fleet:
                fleet[k] += d.get(k, 0)
            p("   %-22s %-6s %-14s %-18s %-18s %-14s %-14s %d (%d)%s"
              % (game, box, _window_cell(vb),
                 _rate(d["mint"], d["verdicts"]),
                 _rate(d["rederivation"], d["verdicts"]),
                 _rate(d["composed"], d["mint"]),
                 (_rate(d["used"], d["atoms"]) if L["used_field"]
                  else NOT_READABLE),
                 L["composites_total"], L["composites_settled"],
                 BELOW_FLOOR if below.get(game) else ""))
    p("   FLEET [all-time, NOT a rate]: MINTED %s ; REDERIVED %s ; COMPOSED %s"
      % (_rate(fleet["mint"], fleet["verdicts"]),
         _rate(fleet["rederivation"], fleet["verdicts"]),
         _rate(fleet["composed"], fleet["mint"])))
    p("   composites (settled): a composite without composer's `settled` field is a")
    p("   CANDIDATE. Reporting composition without it would report machinery firing")
    p("   as a milestone, which is what Figure 5 forbids.")
    p("   COMPOSED/mints ABOVE 1 IS NOT AN ERROR, it is the denominator mismatch")
    p("   showing: a composite is written to the atoms stream by composer.compose(),")
    p("   which files NO mint_verdicts record, while the denominator counts the MDL")
    p("   mint's accepted terms. The two producers write the same stream and only")
    p("   one of them is ledgered in verdicts. Read as stated -- composites per")
    p("   MDL-mint -- and note that the composer has no verdict ledger of its own.")
    p("   Atom and composite counts are DISTINCT IDS, not stream records: the atoms")
    p("   stream carries superseding appends (ctx_min / ctx_conflict rewrite the")
    p("   same id), and counting records would inflate every denominator here.")
    if no_evict:
        p("   RETIRED -- %s on %d/%d boxes: no atoms record carries `evicted`, and"
          % (NOT_READABLE, len(no_evict), len(names)))
        p("   the janitor's policy table names import_queue, settlements and")
        p("   mint_verdicts only, so nothing evicts an atom anywhere in this build.")
        p("   Needed to close: an eviction append on the atoms stream.")
    if no_used:
        p("   USED -- %s on %d/%d boxes (%s): no record links an atom to a driven"
          % (NOT_READABLE, len(no_used), len(names), " ".join(no_used[:8])
             + (" ..." if len(no_used) > 8 else "")))
        p("   plan or a settled chain -- settlements there carry no atom_key and no")
        p("   PLAN record carries a composite citation. Needed to close:")
        p("   settlements.atom_key written non-null, or the PLAN point's")
        p("   composite/settled fields reaching disk.")

    # ── B ─────────────────────────────────────────────────────────────────────
    p()
    p("B. THE ECONOMY, with denominators [frame-internal except where the ground")
    p("   is named].")
    novel_absent: List[str] = []
    for box in names:
        con = _connect(db_path(box))
        if con is None:
            continue
        E = economy(con, w)
        cur, prv = E["categories"], E["categories_prev"]
        allcats = sorted(set(list(cur) + list(prv)))
        tot = sum(cur.values())
        cats_txt = " ".join(
            ("%s %s (%+d)" % (c, _rate(cur.get(c, 0), tot),
                              cur.get(c, 0) - prv.get(c, 0)) if tot
             else "%s 0 in window (%+d vs prev %d)"
                  % (c, -prv.get(c, 0), prv.get(c, 0)))
            for c in allcats) or "no assignment row in this window or the previous"
        p("   [%s] categories, n=%d in window (%d all-time): %s"
          % (box, tot, E["assignments_total"], cats_txt))
        perf_txt = " | ".join(
            "%s/%s n=%d best %.2f wins %d prog %.2f%s"
            % (game, cat, n, score, wins, prog,
               BELOW_FLOOR.strip() if below.get(game) else "")
            for game, cat, n, score, wins, prog in E["perf"]) or "none in window"
        p("   [%s] perf per (GAME, category), never averaged: %s" % (box, perf_txt))
        nk = novel_keys(box)
        ab = learn_all.get(box, {}).get("atom_bracket")
        p("   [%s] retire %d/%d (%d active), evidence on %d | library %d recs /"
          " %d keys / %d singles | catalogue %d rows, %d unlocked by nobody%s"
          % (box, E["retired"], E["retired"] + E["active"], E["active"],
             E["retire_reason_recorded"], nk["records"], nk["keys"],
             nk["single_record_keys"], E["catalogue_rows"],
             E["catalogue_unlocked_by_nobody"],
             " -- NONE, the table is empty" if E["catalogue_rows"] == 0 else ""))
        if ab is not None and ab.readable_zero:
            p("   [%s] NOVEL: 0 keys minted in window -- atoms last written %s"
              " UTC, before it opened. A SOUND ZERO, and Figure 5's reading:"
              " the machinery may be firing and it returned nothing new here."
              % (box, stamp(ab.mtime)))
        elif ab is not None and ab.state == "absent":
            p("   [%s] NOVEL: 0 keys, ever -- this box has NO atoms stream. The"
              " mint has never accepted a term here, so there is nothing for a"
              " novelty read to be about." % box)
        else:
            novel_absent.append(box)
        con.close()
    p("   %s: LEVELS per (game, category) on every box -- agent_operating_modes"
      % NOT_READABLE)
    p("   has no level column and game_results has no agent_id, so no join exists.")
    p("   Needed to close: a level column on the mode row, or an agent_id on the")
    p("   result row.")
    p("   %s: WHEN each retirement happened, on every box -- the agents table"
      % NOT_READABLE)
    p("   carries is_active and retirement_reason but NO retirement timestamp, so")
    p("   retirements cannot be windowed at all. Needed to close: a retired_at")
    p("   column. (Where 'evidence on 0' is printed above, retirement_reason is")
    p("   NULL on every retired row: the field exists and nothing writes it.)")
    if novel_absent:
        p("   NOVEL: %s on %d/%d boxes (%s). Atoms carry no timestamp, so 'a key"
          % (NOT_READABLE, len(novel_absent), len(names),
             " ".join(novel_absent[:8])
             + (" ..." if len(novel_absent) > 8 else "")))
        p("   that appears in no stream BEFORE the window' has no before. This is")
        p("   the only line that speaks to novelty and it is the line the missing")
        p("   clock costs. Needed to close: a UTC field on the atoms record.")

    # ── C ─────────────────────────────────────────────────────────────────────
    p()
    p("C. STALLED -- every series unchanged vs the previous window, with the")
    p("   reason the streams themselves give (mandate item 5).")
    for box in names:
        con = _connect(db_path(box))
        if con is None:
            continue
        prev = Window(w.prev_start, w.prev_end)
        gnow, gprev = ground(con, w), ground(con, prev)
        enow, eprev = exposure(con, w), exposure(con, prev)
        for game in sorted(set(list(gnow) + list(gprev) + list(enow) + list(eprev))):
            a = gnow.get(game, {"levels": 0, "wins": 0})
            b = gprev.get(game, {"levels": 0, "wins": 0})
            ea = enow.get(game, {"episodes": 0, "actions_total": 0})
            eb = eprev.get(game, {"episodes": 0, "actions_total": 0})
            if a["levels"] == b["levels"] and a["wins"] == b["wins"]:
                why = ("no session acted in either window"
                       if ea["episodes"] == 0 and eb["episodes"] == 0
                       else "sessions present (%d now, %d prev), 0 levels completed"
                            " in either" % (ea["episodes"], eb["episodes"]))
                stalls.append("   GROUND    %-22s [%s] unchanged: levels %d, wins"
                              " %d -- %s" % (game, box, a["levels"], a["wins"], why))
            if ea["episodes"] == eb["episodes"]:
                stalls.append("   EXPOSURE  %-22s [%s] unchanged: %d episodes both"
                              " windows" % (game, box, ea["episodes"]))
        vb = learn_all.get(box, {}).get("verdict_bracket")
        pv = Bracket(stream_path(box, T_VERDICTS), prev)
        if vb is not None and vb.state == "absent":
            stalls.append("   LEARNING  %-22s [%s] unchanged: this box has no"
                          " mint_verdicts stream at all -- no verdict has ever"
                          " been written here" % ("(all games)", box))
        elif vb is not None and vb.readable_zero and pv.readable_zero:
            stalls.append("   LEARNING  %-22s [%s] unchanged: no verdict record in"
                          " either window (stream mtime precedes both)"
                          % ("(all games)", box))
        elif vb is not None and not vb.readable_zero:
            stalls.append("   LEARNING  %-22s [%s] NOT COMPARABLE: mint_verdicts has"
                          " no timestamp and its mtime is inside the window --"
                          " stall cannot be distinguished from motion"
                          % ("(all games)", box))
        E = economy(con, w)
        if E["categories"] == E["categories_prev"]:
            stalls.append("   ECONOMY   %-22s [%s] unchanged: category counts"
                          " identical (%s)" % ("(agents)", box,
                                               E["categories"] or "no rows"))
        con.close()
    if stalls:
        for line in stalls:
            p(line)
    else:
        p("   nothing stalled: every series moved against the previous window.")

    # ── E ─────────────────────────────────────────────────────────────────────
    p()
    p("E. CARRIED COST [frame-internal] -- the priming parse a long-lived worker")
    p("   pays for every new game. PersistenceMonitor.from_fabric reads the WHOLE")
    p("   personal narration stream once per spine per game; narration grows every")
    p("   step and the janitor never compacts it.")
    p("   %-6s %10s %9s %6s %14s  %s"
      % ("box", "records", "MB", "games", "implied parses", "largest agent stream"))
    fr = fnb = fp = 0
    for box in names:
        con = _connect(db_path(box))
        C = carried_cost(box, con)
        if con is not None:
            con.close()
        fr += C["records"]
        fnb += C["bytes"]
        fp += C["implied_parses"]
        p("   %-6s %10d %9.1f %6d %14d  %s: %d rec / %.1f MB (%d streams)"
          % (box, C["records"], C["bytes"] / 1048576.0, C["games"],
             C["implied_parses"], C["biggest_agent"] or "--",
             C["biggest_records"], C["biggest_bytes"] / 1048576.0,
             C["streams"]))
    p("   FLEET: %d narration records, %.1f MB, %d implied record-reads"
      % (fr, fnb / 1048576.0, fp))
    p("   This is RATE-ADJACENT, not a state: it is what the NEXT game start")
    p("   costs, and it grows with every step already taken.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="The hourly beat as rates with denominators, per game.")
    ap.add_argument("--hours", type=float, default=1.0,
                    help="window length in hours, ending now (UTC). Default 1.")
    ap.add_argument("--since", default=None,
                    help="UTC timestamp; window starts here instead of now-hours.")
    ap.add_argument("--box", default=None, help="restrict to one box directory.")
    a = ap.parse_args(argv)
    w = resolve_window(a.hours, a.since, utcnow())
    return report(w, a.box, sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
