"""THE TWELVE-HOUR OFFLINE RUN. PREREG_OVERNIGHT_RUN.md.

One CYCLE = 25 unique games x 1 agent x 1 pass, OFFLINE, concurrency 4.
Cycles run back to back until the clock, the disk gate, or the run's own falsifier stops it.

STOPS ON (never "logs and continues"):
  * the disk gate reporting a breach
  * a cycle producing ZERO new sessions across all 25 games (the run's falsifier)
  * the wall-clock budget

NOTHING IRREVERSIBLE: no sweep, no deletion, no compaction, no pragma change. Every box is
append-only for the duration.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, ".runs", "swarm")
PY = r"C:\Users\Admin\Documents\GitHub\Ouroboros\.venv\Scripts\python.exe"
RUNNER = os.path.join(ROOT, "evolution_runner.py")
LOG = os.path.join(ROOT, ".runs", "overnight_run.jsonl")


def games() -> list:
    return sorted(os.path.basename(d.rstrip(os.sep))
                  for d in glob.glob(os.path.join(RUNS, "*" + os.sep)))


def _q(db: str, sql: str) -> int:
    try:
        c = sqlite3.connect("file:" + db.replace(os.sep, "/") + "?mode=ro", uri=True)
        v = c.execute(sql).fetchone()[0] or 0
        c.close()
        return int(v)
    except Exception:
        return 0


def scoreboard() -> Tuple[int, Dict[str, int], int]:
    """(total distinct sessions, per-game max level, games at level >= 1)."""
    sessions, levels = 0, {}
    for g in games():
        db = os.path.join(RUNS, g, "core_data.db")
        sessions += _q(db, "SELECT COUNT(DISTINCT session_id) FROM action_traces")
        levels[g] = _q(db, "SELECT COALESCE(MAX(level_number),0) FROM action_traces")
    return sessions, levels, sum(1 for v in levels.values() if v >= 1)


def queue_depth() -> int:
    n = 0
    for f in glob.glob(os.path.join(RUNS, "*", "ego_fabric", "collective",
                                    "import_queue.jsonl")):
        try:
            with open(f, "rb") as fh:
                n += sum(1 for ln in fh if ln.strip())
        except OSError:
            pass
    return n


def levelup_above_1() -> int:
    n = 0
    for f in glob.glob(os.path.join(RUNS, "**", "levelup_frames.jsonl"), recursive=True):
        try:
            for raw in open(f, encoding="utf-8", errors="replace"):
                line = raw.strip()
                if not line:
                    continue
                try:
                    if int(json.loads(line).get("level", 0)) > 1:
                        n += 1
                except Exception:
                    pass
        except OSError:
            pass
    return n


def gate_ok() -> bool:
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "disk_ceiling.py"),
                        "--guard"], cwd=ROOT, capture_output=True, text=True, check=False)
    return r.returncode == 0


def play(game: str, timeout_s: int) -> str:
    box = os.path.join(RUNS, game)
    env = dict(os.environ)
    env["OPERATION_MODE"] = "OFFLINE"
    env.pop("ARC_API_KEY", None)
    env.pop("ARC_KEY", None)
    log = open(os.path.join(box, "overnight.log"), "a", encoding="utf-8", errors="replace")
    try:
        subprocess.run([PY, RUNNER, "--mode", "offline", "--game", game,
                        "--population", "1", "--agents-per-gen", "1",
                        "--games-per-gen", "1", "--max-generations", "1"],
                       cwd=box, env=env, stdout=log, stderr=subprocess.STDOUT,
                       timeout=timeout_s, check=False)
        return "ok"
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        return f"err:{type(e).__name__}"
    finally:
        log.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=12.0)
    ap.add_argument("--pool", type=int, default=4)
    ap.add_argument("--per-game-timeout", type=int, default=600)
    a = ap.parse_args()

    deadline = time.time() + a.hours * 3600
    gs = games()
    print(f"OVERNIGHT RUN: {len(gs)} games, pool={a.pool}, {a.hours}h, OFFLINE", flush=True)

    cycle = 0
    while time.time() < deadline:
        if not gate_ok():
            print("DISK GATE BREACHED — STOPPING (no sweep; cleanup is Seat 3's)", flush=True)
            break
        cycle += 1
        s0, _, _ = scoreboard()
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=a.pool) as ex:
            outcomes = list(ex.map(lambda g: play(g, a.per_game_timeout), gs))
        dt = time.time() - t0
        s1, levels, at1 = scoreboard()
        rec = {
            "cycle": cycle,
            "utc": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "seconds": round(dt, 1),
            "sessions_before": s0, "sessions_after": s1, "sessions_added": s1 - s0,
            "max_level": max(levels.values()) if levels else 0,
            "games_at_L1_plus": at1,
            "games_at_L2_plus": sum(1 for v in levels.values() if v >= 2),
            "queue_depth": queue_depth(),
            "levelup_above_L1": levelup_above_1(),
            "ok": outcomes.count("ok"), "timeout": outcomes.count("timeout"),
        }
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"cycle {cycle}: {dt:.0f}s  +{s1-s0} sessions  maxL={rec['max_level']}  "
              f"L1+={at1}  L2+={rec['games_at_L2_plus']}  queue={rec['queue_depth']}  "
              f"lvlup>1={rec['levelup_above_L1']}  ok={rec['ok']} to={rec['timeout']}",
              flush=True)

        # THE RUN'S OWN FALSIFIER: a cycle that adds nothing is a broken run, not a slow one.
        if s1 - s0 == 0:
            print("FALSIFIER FIRED: a full cycle produced ZERO new sessions. STOPPING.",
                  flush=True)
            break

    print(f"done after {cycle} cycle(s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
