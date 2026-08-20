"""THE SPLIT-HALF IMPROVEMENT READ — the standing beat number.

Seat 3, 2026-08-19: *"The split-half improvement read goes in every beat, not just when
someone remembers. It's the only number that says whether the work is moving the counter…
Report it as: games improved, games regressed, games unchanged, with the as-of and the
window. IF THE WINDOW IS TOO SHORT TO SPLIT, SAY SO RATHER THAN REPORTING A NUMBER."*

WHAT IT MEASURES. `levels_completed` is a proxy for a WIN **only if it increases** (Seat 3's
rule). So the statistic is not the maximum, it is the DIRECTION: each game's best-ever
`level_completions` in the first half of the window against the second half.

WHY SPLIT BY EPISODE COUNT AND NOT BY TIME. A max over a half is sensitive to how many draws
that half had, and per-game episode rates differ by an order of magnitude. Splitting by count
gives both halves the same n **by construction**, so the comparison is not a sample-size
artefact wearing a trend's clothes.

THE INSUFFICIENCY RULE, WHICH IS THE POINT OF THE THIRD CATEGORY. A game with too few
episodes cannot be split into two halves that mean anything: whether its one good episode
landed left or right of the midpoint is a coin flip, and a coin flip reported as "improved"
or "regressed" is worse than no reading. Such games are counted as **TOO SHORT** and named,
never folded into "unchanged" — folding them there would report stability that was never
measured.

TIMESTAMPS ARE UTC IN THESE DATABASES (`MAX(timestamp)` reads ~5h ahead of local). `--since`
is therefore interpreted as UTC and says so on the output line, because comparing a local
wall-clock string against a UTC column silently matches most of the day.

USAGE
  python tools/split_half.py                      # whole history
  python tools/split_half.py --since "2026-08-19 21:00:00"   # a window, UTC
  python tools/split_half.py --min-per-half 8     # the sufficiency floor
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import sqlite3
import sys
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, ".runs", "swarm")


def series(db: str, since: Optional[str]) -> List[int]:
    """This game's level_completions in episode order, oldest first."""
    try:
        con = sqlite3.connect("file:" + db.replace(os.sep, "/") + "?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        if since:
            rows = con.execute(
                "SELECT level_completions FROM game_results WHERE created_at > ? "
                "ORDER BY created_at", (since,)).fetchall()
        else:
            rows = con.execute(
                "SELECT level_completions FROM game_results ORDER BY created_at").fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        con.close()
    return [int(r[0] or 0) for r in rows]


def required_per_half(all_vals: List[int], miss_tolerance: float = 0.05) -> Tuple[int, float]:
    """DERIVED, not asserted. Returns (episodes needed per half, the observed rate p).

    The statistic is `max(level_completions)` per half, so the failure mode is a half
    MISSING the game's best level by luck and the comparison reporting a direction that is
    really a sampling artefact. If p is the rate at which an episode reaches that best
    level, a half of size k misses it with probability (1-p)^k, so:

        k = ceil( ln(miss_tolerance) / ln(1-p) )      [5% by default]

    p is measured from the game's OWN history, because the rates differ by an order of
    magnitude across the roster -- ft09 reaches its best on ~15% of episodes and ar25 on
    far more, and one global floor would be far too loose for the first and wasteful for
    the second.

    A GAME THAT HAS NEVER SCORED IS A SEPARATE CASE and returns k=0: max is 0 in both
    halves, "unchanged" is then a true statement about what happened rather than an
    estimate that could have missed something, and no power is required to say it. What
    such a game CANNOT do is support a claim about direction, which is why it is reported
    as never-scored rather than folded in with the rest."""
    n = len(all_vals)
    if n == 0:
        return 0, 0.0
    best = max(all_vals)
    if best == 0:
        return 0, 0.0
    hits = sum(1 for v in all_vals if v >= best)
    p = hits / n
    if p >= 1.0:
        return 1, p
    k = math.ceil(math.log(miss_tolerance) / math.log(1.0 - p))
    return max(1, int(k)), p


def classify(vals: List[int], need: int, scored_ever: bool) -> Tuple[str, int, int, int]:
    """(verdict, n, best_first_half, best_second_half). One of
    improved / regressed / unchanged / never-scored / too-short."""
    n = len(vals)
    if not scored_ever:
        # max 0 vs max 0 is not a sampling artefact; it is the absence itself.
        return ("never-scored", n, 0, 0) if n >= 2 else ("too-short", n, 0, 0)
    if n < need * 2:
        return "too-short", n, 0, 0
    h = n // 2
    b1, b2 = max(vals[:h]), max(vals[h:])
    if b2 > b1:
        return "improved", n, b1, b2
    if b2 < b1:
        return "regressed", n, b1, b2
    return "unchanged", n, b1, b2


def _best_level(game: str) -> int:
    """This game's best level ever reached, over ALL history -- used only to warn about
    which games a short window is dropping, never as part of the split-half verdict."""
    db = os.path.join(RUNS, game, "core_data.db")
    try:
        con = sqlite3.connect("file:" + db.replace(os.sep, "/") + "?mode=ro", uri=True)
        n = con.execute("SELECT COALESCE(MAX(level_number),0) FROM action_traces").fetchone()[0]
        con.close()
        return int(n or 0)
    except sqlite3.Error:
        return 0


def wins(db: str) -> int:
    try:
        con = sqlite3.connect("file:" + db.replace(os.sep, "/") + "?mode=ro", uri=True)
        n = con.execute("SELECT COUNT(*) FROM game_results WHERE win_detected=1").fetchone()[0]
        con.close()
        return int(n or 0)
    except sqlite3.Error:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None,
                    help="UTC timestamp; window starts here. Omit for whole history.")
    a = ap.parse_args()

    buckets: Dict[str, List[str]] = {"improved": [], "regressed": [], "unchanged": [],
                                     "never-scored": [], "too-short": []}
    detail = []
    total_wins = 0
    for db in sorted(glob.glob(os.path.join(RUNS, "*", "core_data.db"))):
        g = os.path.basename(os.path.dirname(db))
        hist = series(db, None)                 # the rate comes from ALL history
        need, p = required_per_half(hist)
        vals = series(db, a.since)              # the verdict comes from the WINDOW
        verdict, n, b1, b2 = classify(vals, need, scored_ever=(need > 0))
        buckets.setdefault(verdict, []).append(g)
        total_wins += wins(db)
        detail.append((g, verdict, n, b1, b2, need, p))

    window = ("whole history" if not a.since else "since %s UTC" % a.since)
    import time
    won = sum(1 for d in detail
              if wins(os.path.join(RUNS, d[0], "core_data.db")) > 0)
    print("SPLIT-HALF IMPROVEMENT READ")
    print("  as-of : %s UTC" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    print("  window: %s" % window)
    print("  split : by EPISODE COUNT (equal n per half). NO WALL-CLOCK THRESHOLD --")
    print("          the requirement is sessions per game, and it is DERIVED per game")
    print("          from that game's own event rate: k = ceil(ln(0.05)/ln(1-p)).")
    print()
    print("  GAMES WON         : %d/25" % won)
    for name, key in (("IMPROVED", "improved"), ("REGRESSED", "regressed"),
                      ("UNCHANGED", "unchanged"), ("NEVER SCORED", "never-scored"),
                      ("NOT YET READABLE", "too-short")):
        print("  games %-17s: %d  %s" % (name, len(buckets[key]),
                                         " ".join(sorted(buckets[key])) or "--"))

    if buckets["too-short"]:
        print()
        print("  ** %d GAME(S) ARE NOT YET READABLE IN THIS WINDOW. That is a STATED ABSENCE,"
              % len(buckets["too-short"]))
        print("     not a zero: their direction is unknown, and they are NOT counted as")
        print("     unchanged. A coin flip labelled 'improved' is worse than no reading.")
    if len(buckets["too-short"]) == 25:
        print("  ** NO GAME IS READABLE YET. There is no number this beat.")

    deep_short = [g for g in buckets["too-short"] if _best_level(g) >= 1]
    if deep_short:
        print()
        print("  ** SKEW: %d of the not-yet-readable games are at L1+ (%s)."
              % (len(deep_short), " ".join(sorted(deep_short))))
        print("     A short window drops the games that produce FEW episodes, and those are")
        print("     the ones with banked routes to replay -- the games CLOSEST to a win.")
        print("     Any number above is therefore weighted toward fast, shallow games.")

    print()
    print("  PER GAME -- read each as it crosses, never wait for the slowest:")
    print("    %-6s %-16s %6s %6s  %s" % ("game", "verdict", "have", "need", "detail"))
    for g, verdict, n, b1, b2, need, p in sorted(detail, key=lambda d: (d[1], -d[2])):
        want = need * 2
        if verdict == "too-short":
            # need==0 means the game has never scored at all, so the requirement is not a
            # power threshold -- it is simply "produce something". Show the floor of 2
            # rather than 0, and say plainly when a game produced NOTHING in the window.
            want = want if want >= 2 else 2
            short = max(0, want - n)
            note = ("NO SESSIONS AT ALL in this window" if n == 0
                    else "%d more session(s)" % short)
            print("    %-6s %-16s %6d %6d  %s; p=%.2f"
                  % (g, "not-yet-readable", n, want, note, p))
        elif verdict == "never-scored":
            print("    %-6s %-16s %6d %6s  never completed a level in this window"
                  % (g, verdict, n, "n/a"))
        else:
            print("    %-6s %-16s %6d %6d  best %d -> %d  (p=%.2f)"
                  % (g, verdict, n, want, b1, b2, p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
