"""SWARM SUPERVISOR v2 — with smart trash collection and memory-leak protection.

Proctor tooling (driver-level, no agent code). One worker per game, cross-mounted fabrics.

THE PROTECTION LAYER (why each piece exists):
  * MEMORY CAP — a worker whose working set exceeds MEM_CAP_MB is killed and restarted
    (leaks cannot accumulate past the cap). Polled once per cycle via a single CIM query.
  * BOUNDED LIFETIME — every worker is recycled after RECYCLE_MIN minutes regardless of
    health (the gunicorn max-requests principle: a bounded process cannot leak unboundedly).
    Recycles are staggered by construction since spawn times differ.
  * TRASH COLLECTION ON EVERY RECYCLE — at each worker stop, its box's SQLite gets:
    v4's own SafeDatabaseCleaner (keeps knowledge, trims telemetry — Isaiah's tiering),
    a WAL checkpoint (TRUNCATE), and VACUUM when the file exceeds VACUUM_AT_MB. Fabrics are
    knowledge (tiny) and are never touched here — the fabric_janitor handles their
    compaction separately per PREREG_SMART_CLEANUP.
  * DISK GUARD — if the box DB still exceeds DB_HARD_CAP_MB after cleaning, telemetry tables
    are emptied outright (knowledge tables never touched) before VACUUM.
  * LOUD STATUS — .runs/swarm/status.txt every cycle: per-worker RSS, uptime, restarts,
    recycle/mem-kill counts, db size. Nothing silent.
Kill this process to stop the swarm; workers die with it (they are child processes).
"""
import os
import re
import subprocess
import sys
import time

REDUX = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REDUX)
from engines.egocentric.lp_drive import assign_arm  # G-D: three-arm LP-drive control

PY = sys.executable
ROOT = os.path.join(REDUX, ".runs", "swarm")
GAMES = ["ar25", "bp35", "cd82", "cn04", "dc22", "ft09", "g50t", "ka59", "lf52", "lp85",
         "ls20", "m0r0", "r11l", "re86", "s5i5", "sb26", "sc25", "sk48", "sp80", "su15",
         "tn36", "tr87", "tu93", "vc33", "wa30"]

MEM_CAP_MB = 1200          # kill + restart a worker above this working set
RECYCLE_MIN = 120          # bounded lifetime: recycle every 2 hours
VACUUM_AT_MB = 200         # vacuum a box DB above this size at recycle
DB_HARD_CAP_MB = 600       # after cleaning, still above this -> empty telemetry outright
POLL_SEC = 60

TELEMETRY_TABLES = ["system_logs", "action_traces", "sensation_learning_events",
                    "cognitive_routing_traces", "i_thread_history", "player_state_history",
                    "navigation_state_history", "agent_operating_modes"]

txt = open(os.path.join(REDUX, ".env"), encoding="utf-8").read()
KEY = re.search(r"^\s*ARC_KEY\s*=\s*(.+?)\s*$", txt, re.M).group(1).strip().strip('"').strip("'")

os.makedirs(ROOT, exist_ok=True)
seed_dirs = [os.path.join(REDUX, ".runs", "compound2", "ego_fabric")] + \
            [os.path.join(ROOT, g, "ego_fabric") for g in GAMES]

procs = {}     # game -> (Popen, logfile, t0)
stats = {g: {"restarts": 0, "mem_kills": 0, "recycles": 0} for g in GAMES}


def db_gc(box, log):
    """Smart trash collection for one box's SQLite. Loud, bounded, knowledge-preserving."""
    db = os.path.join(box, "core_data.db")
    if not os.path.exists(db):
        return
    size0 = os.path.getsize(db) / 1e6
    try:
        sys.path.insert(0, REDUX)
        import sqlite3
        # 1) v4's own tiered cleaner (keeps winners/knowledge, trims telemetry)
        try:
            from safe_cleanup import SafeDatabaseCleaner
            SafeDatabaseCleaner(db_path=db).cleanup(dry_run=False, verbose=False)
        except Exception as e:
            log.write("[GC] SafeDatabaseCleaner failed: %s\n" % e)
        con = sqlite3.connect(db)
        # 2) hard cap: telemetry emptied outright if still huge (knowledge never touched)
        if os.path.getsize(db) / 1e6 > DB_HARD_CAP_MB:
            for t in TELEMETRY_TABLES:
                try:
                    con.execute("DELETE FROM [%s]" % t)  # noqa: S608 -- t from the fixed TELEMETRY_TABLES list, not input
                except Exception:
                    pass
            con.commit()
            log.write("[GC] hard cap hit: telemetry emptied\n")
        # 3) WAL checkpoint + conditional vacuum
        try:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        if os.path.getsize(db) / 1e6 > VACUUM_AT_MB:
            try:
                con.execute("VACUUM")
            except Exception as e:
                log.write("[GC] vacuum failed: %s\n" % e)
        con.close()
        log.write("[GC] db %.0fMB -> %.0fMB\n" % (size0, os.path.getsize(db) / 1e6))
        log.flush()
    except Exception as e:
        log.write("[GC] failed entirely: %s\n" % e)
        log.flush()


def spawn(g):
    box = os.path.join(ROOT, g)
    os.makedirs(box, exist_ok=True)
    env = dict(os.environ)
    env["ARC_API_KEY"] = KEY
    env["PYTHONPATH"] = REDUX
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OURO_FABRIC_SEEDS"] = ";".join(d for d in seed_dirs
                                        if d != os.path.join(box, "ego_fabric"))
    # G-D (PREREG_FINAL_GAPS) + ROTATION: the three-arm LP-drive control runs
    # LIVE, and the arm ROTATES per recycle -- assign_arm(game, recycles) =
    # ARMS[(sha1(game) + recycles) mod 3] -- so every game visits every arm
    # across 3 recycles (the arm/game confound dies) while assignment stays
    # deterministic across restarts, recycles and supervisor reboots. Crash
    # restarts and mem-kills keep the arm (only the bounded-lifetime recycle
    # counter rotates it); recycles=0 is the original static assignment.
    env["LP_DRIVE_ARM"] = assign_arm(g, stats[g]["recycles"])
    logf = open(os.path.join(box, "worker.log"), "a", encoding="utf-8", errors="replace")
    logf.write("[SUPERVISOR] LP_DRIVE_ARM=%s recycles=%d\n"
               % (env["LP_DRIVE_ARM"], stats[g]["recycles"]))
    # --mode offline (PREREG_SWARM_OFFLINE_MODE.md, Seat 3 authorised 2026-08-19):
    # the objective is "25/25 completed LOCALLY OFFLINE in WON status", and the
    # runner's --mode defaulted to "normal" (local + API) because nothing ever set
    # it -- an argparse default, not a decision. OFFLINE removes a network
    # dependency and a rate-limit surface from work whose success condition is
    # local. Roster risk already retired: the 12-hour run drove all 25 games with
    # --mode offline for 47 cycles and every cycle produced 25 sessions.
    p = subprocess.Popen([PY, os.path.join(REDUX, "evolution_runner.py"), "--verbose",
                          "--mode", "offline",
                          "--game", g, "--population", "6", "--agents-per-gen", "4",
                          "--games-per-gen", "1", "--max-generations", "50"],
                         cwd=box, env=env, stdout=logf, stderr=subprocess.STDOUT)
    procs[g] = (p, logf, time.time())


def working_sets():
    """One CIM call for all python processes: {pid: (ppid, MB)}.

    VENV LAUNCHER TRAP: on Windows the venv python.exe is a small launcher that
    spawns the REAL interpreter as a child. Popen's pid is the launcher's, so a
    worker's true memory lives on the launcher's child. tree_rss() sums the tree.
    """
    # wmic: ~12s under swarm load; powershell cold-starts >45s and times out.
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'",
             "get", "ProcessId,ParentProcessId,WorkingSetSize", "/format:csv"],
            capture_output=True, text=True, timeout=50, check=False)
        m = {}
        for line in out.stdout.splitlines():
            parts = line.strip().split(",")
            # CSV columns (alphabetical): Node,ParentProcessId,ProcessId,WorkingSetSize
            if len(parts) == 4 and parts[1].isdigit() and parts[2].isdigit() \
                    and parts[3].isdigit():
                m[int(parts[2])] = (int(parts[1]), int(parts[3]) / 1e6)
        if m:
            return m
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "ForEach-Object { \"$($_.ProcessId) $($_.ParentProcessId) "
             "$($_.WorkingSetSize)\" }"],
            capture_output=True, text=True, timeout=50, check=False)
        m = {}
        for line in out.stdout.splitlines():
            parts = line.split()
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                m[int(parts[0])] = (int(parts[1]), int(parts[2]) / 1e6)
        return m
    except Exception:
        return {}


def tree_rss(root_pid, ws):
    """Total working set of root_pid + all descendants found in ws."""
    total = 0.0
    frontier = [root_pid]
    seen = set()
    while frontier:
        pid = frontier.pop()
        if pid in seen:
            continue
        seen.add(pid)
        if pid in ws:
            total += ws[pid][1]
        frontier.extend(cp for cp, (pp, _r) in ws.items() if pp == pid)
    return total


def kill_tree(pid):
    """Kill the whole process tree (launcher + real interpreter + children).
    p.kill() alone terminates only the venv launcher and ORPHANS the real
    worker -- the double-riding catastrophe. taskkill /T takes the tree."""
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True, timeout=30, check=False)
    except Exception:
        pass


def stop_and_gc(g, reason):
    p, logf, _t0 = procs[g]
    kill_tree(p.pid)
    try:
        p.wait(timeout=15)
    except Exception:
        pass
    logf.write("\n[SUPERVISOR] stopped (%s)\n" % reason)
    db_gc(os.path.join(ROOT, g), logf)
    logf.close()


for g in GAMES:
    spawn(g)
    print("spawned", g, flush=True)
    time.sleep(2.0)

while True:
    time.sleep(POLL_SEC)
    ws = working_sets()
    lines = []
    if not ws:
        lines.append("!! working_sets EMPTY -- memory cap blind this cycle")
    for g in GAMES:
        p, logf, t0 = procs[g]
        up_min = (time.time() - t0) / 60.0
        rss = tree_rss(p.pid, ws)
        if p.poll() is not None:
            stats[g]["restarts"] += 1
            logf.write("\n[SUPERVISOR] exited rc=%s; restart #%d\n" % (p.returncode, stats[g]["restarts"]))
            db_gc(os.path.join(ROOT, g), logf)
            logf.close()
            spawn(g)
            lines.append("%s RESTART#%d" % (g, stats[g]["restarts"]))
        elif rss > MEM_CAP_MB:
            stats[g]["mem_kills"] += 1
            stop_and_gc(g, "memory cap: %.0fMB > %dMB" % (rss, MEM_CAP_MB))
            spawn(g)
            lines.append("%s MEM-KILL#%d(%.0fMB)" % (g, stats[g]["mem_kills"], rss))
        elif up_min > RECYCLE_MIN:
            stats[g]["recycles"] += 1
            stop_and_gc(g, "bounded lifetime: %.0f min" % up_min)
            spawn(g)
            lines.append("%s RECYCLED#%d" % (g, stats[g]["recycles"]))
        else:
            db = os.path.join(ROOT, g, "core_data.db")
            dbmb = os.path.getsize(db) / 1e6 if os.path.exists(db) else 0
            lines.append("%s up=%dm rss=%.0fMB db=%.0fMB r/m/c=%d/%d/%d"
                         % (g, int(up_min), rss, dbmb,
                            stats[g]["restarts"], stats[g]["mem_kills"], stats[g]["recycles"]))
    with open(os.path.join(ROOT, "status.txt"), "w", encoding="utf-8") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + "\n".join(lines) + "\n")
