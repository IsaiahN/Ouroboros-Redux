"""SPRINT KEEPER -- relaunch-only watchdog for the sprint-mode workers.

THE GAP THIS CLOSES (2026-08-21): in "sprint mode" the proctor runs a handful of
workers DIRECTLY, with no supervisor above them. evolution_runner EXITS when its run
ends (--max-generations reached, crash, whatever) and nothing relaunches it -- so the
sprint fleet silently went to zero today and nobody was told. This keeper's entire
job is: every --interval seconds, for each named game, if no live python process is
running `evolution_runner ... --game <game>`, start one, and write a line saying so.

WHAT THIS IS NOT. tools/swarm_supervisor.py is the FULL-FLEET tool: it owns its
workers as children, enforces the memory cap and the bounded lifetime, runs trash
collection at every stop, fingerprints the live path and deploys on change, honours
HOLD. None of that is replicated here, on purpose:
  * no deploys, no fingerprinting, no HOLD -- the keeper never decides a worker is
    stale; it only notices one is ABSENT;
  * no kills, no memory cap, no recycle -- the keeper never stops a worker;
  * workers are spawned DETACHED (not children): Ctrl-C on the keeper exits the
    keeper and leaves every worker exactly as it was.

FLEET-ENV PARITY (2026-08-21, the second gap). The supervisor does not just launch a
worker: it assembles a per-worker environment the worker's behaviour depends on --
OURO_FABRIC_SEEDS (the ego_fabric dirs of every OTHER box, ';'-joined, so fabrics are
cross-mounted) and LP_DRIVE_ARM (assign_arm(game, recycles)). A keeper that relaunched
with a bare inherited env ran the sprint under a DIFFERENT, UNDECLARED config than the
fleet, and that contaminated a read. So the keeper now sets both, BY DEFAULT, the way
the supervisor would for that game -- and not by transcribing the supervisor's lines
(a transcription drifts) but by calling the SAME function the supervisor calls:
tools/fleet_env.py holds the roster (GAMES) and the assembly (fleet_env_for), with no
import-time side effects, and both launchers import it. The keeper passes recycles=0:
it keeps no recycle stats (it never recycles), so the arm is the static assignment,
stated in worker.log.
`--no-fleet-env` opts out (the W3 no-seeds direction needs an explicit flag, never an
accident) and every spawn's log line says which mode it used: `spawn <pid> fleet-env`
or `spawn <pid> bare-env`.

INPUT: .runs/sprint_argv.txt -- the worker command line the proctor used, saved
verbatim (one line). The keeper replaces the value after its `--game` token per game
and strips a stray trailing PID if the line was copied from a process listing.
OUTPUT: .runs/swarm/sprint_keeper.log -- one line per event: `utc game action pid`,
plus the env mode on spawn lines: `utc game spawn pid fleet-env|bare-env`.
Worker stdout/stderr is appended to .runs/swarm/<game>/worker.log, the same file the
supervisor uses, so the evidence trail does not fork.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import time

REDUX = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REDUX not in sys.path:
    sys.path.insert(0, REDUX)
# The roster + the per-worker env assembly, shared with swarm_supervisor -- never a
# transcription of it. tools/fleet_env.py has no import-time side effects.
from tools.fleet_env import GAMES, SEED_SEP, fleet_env_for  # noqa: E402

# THE SEQ WATERMARK (record/prereg/PREREG_SEQ_WATERMARK.md), the keeper's half of it:
# the supervisor ticks at its 60s poll, the keeper at its --interval pass, and both call
# THE SAME assembly -- tools/watermark.py -- for the same reason fleet_env exists. A
# sprint whose boxes carry no ticks is a sprint the beat cannot window.
from tools.watermark import write_all as write_watermarks  # noqa: E402

ROOT = os.path.join(REDUX, ".runs", "swarm")
ARGV_FILE = os.path.join(REDUX, ".runs", "sprint_argv.txt")
LOG_FILE = os.path.join(ROOT, "sprint_keeper.log")
DEFAULT_GAMES = ["sk48", "ar25", "g50t"]
DEFAULT_INTERVAL = 60.0
RUNNER_MARK = "evolution_runner"   # the liveness predicate keys on this + --game <g>
MODE_FLEET, MODE_BARE = "fleet-env", "bare-env"

# Windows-only; absent elsewhere (tests mock Popen, so the constant just has to exist).
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0)


# ── argv templating ──────────────────────────────────────────────────────────

def tokenize(line):
    """Split the saved command line into argv tokens. Windows paths keep their
    backslashes (posix=False); surrounding quotes on a token are stripped."""
    toks = shlex.split(line.strip(), posix=False)
    return [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'" else t
            for t in toks]


def strip_trailing_pid(tokens):
    """Defensive: a template copied from a process listing can end in the PID.
    A trailing all-digit token is dropped when the token before it is NOT an
    option name -- so `--max-generations 50` survives (50 is the option's value)
    while `--max-generations 50 18324` loses the 18324. The residue: a template
    ending `--flag PID` where --flag takes no value is indistinguishable from
    `--flag VALUE` and is left alone."""
    toks = list(tokens)
    if len(toks) >= 2 and toks[-1].isdigit() and not toks[-2].startswith("-"):
        toks.pop()
    return toks


def render_argv(tokens, game):
    """Return a fresh argv with the `--game X` (or `--game=X`) token set to `game`.
    Raises ValueError, loudly, if the template carries no --game at all: a keeper
    that spawned three workers on the template's own game would be worse than
    none."""
    toks = list(tokens)
    for i, t in enumerate(toks):
        if t == "--game":
            if i + 1 >= len(toks):
                raise ValueError("sprint argv template ends with a bare --game (no value)")
            toks[i + 1] = game
            return toks
        if t.startswith("--game="):
            toks[i] = "--game=" + game
            return toks
    raise ValueError("sprint argv template has no --game token: %r" % (" ".join(toks),))


def load_template(path=ARGV_FILE):
    """First non-empty line of the saved argv file -> cleaned token list."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            "no sprint argv template at %s -- save the proctor's worker command line "
            "there (one line, containing `--game X`)" % path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                toks = strip_trailing_pid(tokenize(line))
                render_argv(toks, "probe")  # validate now, not at the first relaunch
                return toks
    raise ValueError("sprint argv template %s is empty" % path)


# ── liveness ─────────────────────────────────────────────────────────────────

_GAME_RE = re.compile(r"(?:^|\s)--game(?:\s+|=)(\S+)")


def is_worker_for(cmdline, game):
    """THE LIVENESS PREDICATE. A command line is the worker for `game` iff it
    mentions evolution_runner AND carries `--game <game>` as a whole token
    (`--game sk48` never matches sk4 or sk48x; `--game=sk48` also counts)."""
    if RUNNER_MARK not in cmdline:
        return False
    m = _GAME_RE.search(cmdline)
    return bool(m) and m.group(1).strip("\"'") == game


def live_pids(game, procs):
    """PIDs among procs=[(pid, cmdline), ...] that are workers for `game`.
    The venv launcher and the real interpreter both appear -- both count."""
    return [pid for pid, cmd in procs if is_worker_for(cmd or "", game)]


def list_python_processes():
    """[(pid, cmdline)] for every python.exe. Same route as the supervisor:
    one wmic call (fast under load), PowerShell CIM as the fallback. wmic's CSV
    is unquoted and a command line may contain commas, so the row is parsed as
    Node,<everything in between>,ProcessId."""
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'",
             "get", "ProcessId,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=50, check=False)
        procs = []
        for line in out.stdout.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 3 and parts[-1].isdigit():
                procs.append((int(parts[-1]), ",".join(parts[1:-1])))
        if procs:
            return procs
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "ForEach-Object { \"$($_.ProcessId) $($_.CommandLine)\" }"],
            capture_output=True, text=True, timeout=50, check=False)
        procs = []
        for line in out.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if parts and parts[0].isdigit():
                procs.append((int(parts[0]), parts[1] if len(parts) > 1 else ""))
        return procs
    except Exception:
        return []


# ── spawning + logging ───────────────────────────────────────────────────────

def _worker_env(game=None, root=ROOT, fleet_env=True):
    """Inherit the keeper's environment (the proctor's shell) plus the two settings
    the supervisor always applies. ARC_API_KEY is filled from .env only when the
    shell did not already provide one. With fleet_env (the default) the fleet
    policy -- OURO_FABRIC_SEEDS and LP_DRIVE_ARM -- is set by fleet_env_for, the
    supervisor's own assembly, at recycles=0; with fleet_env=False NEITHER is set
    (and neither is removed: the shell's own value, if any, passes through
    untouched, as it always did)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = REDUX
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if not env.get("ARC_API_KEY"):
        try:
            txt = open(os.path.join(REDUX, ".env"), encoding="utf-8").read()
            m = re.search(r"^\s*ARC_KEY\s*=\s*(.+?)\s*$", txt, re.M)
            if m:
                env["ARC_API_KEY"] = m.group(1).strip().strip('"').strip("'")
        except Exception:
            pass
    if fleet_env:
        env.update(fleet_env_for(game, root, GAMES, recycles=0))
    return env


def env_mode(fleet_env):
    return MODE_FLEET if fleet_env else MODE_BARE


def spawn(game, argv, root=ROOT, fleet_env=True):
    """Start one detached worker; cwd = its box; output appended to worker.log.
    Returns the launcher PID. The Popen handle is deliberately dropped: the
    keeper never waits on, polls, or kills what it starts."""
    box = os.path.join(root, game)
    os.makedirs(box, exist_ok=True)
    env = _worker_env(game, root, fleet_env)
    logf = open(os.path.join(box, "worker.log"), "a", encoding="utf-8", errors="replace")
    if fleet_env:
        nseeds = len([s for s in env["OURO_FABRIC_SEEDS"].split(SEED_SEP) if s])
        logf.write("[KEEPER] relaunch %s %s LP_DRIVE_ARM=%s recycles=0 seeds=%d\n"
                   % (utc_now(), MODE_FLEET, env["LP_DRIVE_ARM"], nseeds))
    else:
        logf.write("[KEEPER] relaunch %s %s (OURO_FABRIC_SEEDS / LP_DRIVE_ARM not set)\n"
                   % (utc_now(), MODE_BARE))
    logf.flush()
    p = subprocess.Popen(argv, cwd=box, env=env, stdout=logf,
                         stderr=subprocess.STDOUT, creationflags=DETACHED_PROCESS)
    logf.close()  # the child holds its own handle now
    return p.pid


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def format_log_line(utc, game, action, pid, mode=""):
    """`utc game action pid`, space-separated, one event per line; spawn lines
    carry a fifth field, the env mode (`fleet-env` / `bare-env`)."""
    line = "%s %s %s %s" % (utc, game, action, pid)
    return line + " " + mode if mode else line


def log_event(game, action, pid, log_path=LOG_FILE, mode=""):
    line = format_log_line(utc_now(), game, action, pid, mode)
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    print(line, flush=True)


# ── the loop ─────────────────────────────────────────────────────────────────

def run_once(games, template, procs, root=ROOT, log_path=LOG_FILE, spawn_fn=spawn,
             fleet_env=True):
    """One pass: relaunch every game with no live worker in `procs`. Returns
    [(game, action, pid)] for what happened. Pure except through spawn_fn and
    the log, so a test can drive it with a constructed process list. The env
    mode (fleet-env / bare-env) is passed to spawn_fn and written on the log line."""
    events = []
    mode = env_mode(fleet_env)
    for g in games:
        if live_pids(g, procs):
            continue
        try:
            pid = spawn_fn(g, render_argv(template, g), root, fleet_env=fleet_env)
            action = "spawn"
        except Exception as e:
            pid, action = "-", "spawn_failed:%s" % type(e).__name__
        log_event(g, action, pid, log_path, mode)
        events.append((g, action, pid))
    return events


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("games", nargs="*", default=DEFAULT_GAMES,
                    help="games to keep alive (default: %s)" % " ".join(DEFAULT_GAMES))
    ap.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                    help="seconds between liveness passes (default %.0f)" % DEFAULT_INTERVAL)
    ap.add_argument("--once", action="store_true",
                    help="one pass, then exit (operator sanity check)")
    ap.add_argument("--no-fleet-env", dest="fleet_env", action="store_false",
                    help="do NOT set OURO_FABRIC_SEEDS / LP_DRIVE_ARM (bare inherited env; "
                         "the W3 no-seeds direction -- an explicit choice, never the default)")
    a = ap.parse_args(argv)

    template = load_template()
    log_event("-", "keeper_start:%s" % ",".join(a.games), os.getpid(), mode=env_mode(a.fleet_env))
    try:
        while True:
            run_once(a.games, template, list_python_processes(), fleet_env=a.fleet_env)
            # ONE TICK PER PASS, at the keeper's own declared cadence. It lives here and
            # not inside run_once because run_once is the RELAUNCH decision and a pass
            # that relaunches nothing must stay a no-op that writes nothing (its gate
            # says so); a watermark is taken every pass, relaunch or not.
            write_watermarks(ROOT, a.games, a.interval)
            if a.once:
                break
            time.sleep(a.interval)
    except KeyboardInterrupt:
        pass  # workers are detached: they are left exactly as they were
    log_event("-", "keeper_stop", os.getpid())
    return 0


if __name__ == "__main__":
    sys.exit(main())
