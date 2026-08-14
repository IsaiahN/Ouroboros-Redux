"""W4 B20: the control-arm driver — verdicts become CAUSAL (CK_LEDGER G2).

Registered verdicts read off the live swarm are confounded with time, budget, and luck.
This driver runs the C33 three-arm discipline generalized: PAIRED BOXES, one git worktree
per sha (the code under test, frozen), the SAME game and the SAME shared fabric-seed
mount for every arm, SEPARATE boxes (each arm's DB + ego_fabric are its own), N episodes
per arm, then a delta report read from the box DBs — the future shape of every wave
verdict: an arm delta, not a wall-clock coincidence.

Episode mapping: one episode = one generation with --games-per-gen 1 (the swarm
supervisor's own convention), so --episodes N drives --max-generations N.

  python tools/control_arm.py --game ar25 --shas <A>,<B> --episodes 20
  python tools/control_arm.py --game ar25 --shas <A>,<B> --episodes 20 --dry-run

--dry-run validates the full setup path — sha resolution, worktree creation, runner
presence, command + env construction — prints everything, runs NOTHING, and removes any
worktree it created (a validation, not a residue). Real runs need ARC_KEY in .env and
network; the driver refuses to start without the key. Stdlib only; dev-time tool.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
ARMS_ROOT = os.path.join(REPO, ".runs", "arms")
DEFAULT_SEED = os.path.join(REPO, ".runs", "compound2", "ego_fabric")

RUNNER_ARGS = ["--verbose", "--population", "6", "--agents-per-gen", "4",
               "--games-per-gen", "1"]


def _git(*args, check=True):
    out = subprocess.run(["git", "-C", REPO, *args], capture_output=True,
                         text=True, timeout=300, check=False)
    if check and out.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), out.stderr.strip()))
    return out.stdout.strip()


def _arc_key():
    try:
        txt = open(os.path.join(REPO, ".env"), encoding="utf-8").read()
        m = re.search(r"^\s*ARC_KEY\s*=\s*(.+?)\s*$", txt, re.M)
        return m.group(1).strip().strip('"').strip("'") if m else None
    except OSError:
        return None


def _resolve(sha):
    full = _git("rev-parse", "--verify", sha + "^{commit}")
    return full, full[:12]


def _ensure_worktree(full_sha, short):
    """Worktree for the sha under .runs/arms/<short>. Returns (path, created_now)."""
    path = os.path.join(ARMS_ROOT, short)
    if os.path.isdir(os.path.join(path, ".git")) or os.path.isfile(os.path.join(path, ".git")):
        return path, False
    os.makedirs(ARMS_ROOT, exist_ok=True)
    _git("worktree", "add", "--detach", path, full_sha)
    return path, True


def _remove_worktree(path):
    _git("worktree", "remove", "--force", path, check=False)
    _git("worktree", "prune", check=False)


def _arm_command(worktree, game, episodes):
    runner = os.path.join(worktree, "evolution_runner.py")
    return [PY, runner, *RUNNER_ARGS, "--game", game,
            "--max-generations", str(int(episodes))]


def _arm_env(worktree, box, seed_dirs, key):
    env = dict(os.environ)
    env["PYTHONPATH"] = worktree                     # the arm runs ITS OWN sha's code
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OURO_FABRIC_SEEDS"] = ";".join(seed_dirs)   # SHARED seed mount: same books
    if key:
        env["ARC_API_KEY"] = key
    _ = box                                          # box separation = cwd, not env
    return env


def _box_stats(box):
    """level_completions / frame-change stats from one arm's box DB (read-only)."""
    db = os.path.join(box, "core_data.db")
    stats = {"db": db, "sessions": 0, "level_completions": 0, "frame_changes": 0,
             "best_level_completions": 0, "win_detected": 0}
    if not os.path.isfile(db):
        stats["missing"] = True
        return stats
    con = sqlite3.connect("file:%s?mode=ro" % db.replace(os.sep, "/"), uri=True)
    try:
        row = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(level_completions),0), "
            "COALESCE(SUM(frame_changes),0), COALESCE(MAX(level_completions),0), "
            "COALESCE(SUM(win_detected),0) FROM game_results").fetchone()
        (stats["sessions"], stats["level_completions"], stats["frame_changes"],
         stats["best_level_completions"], stats["win_detected"]) = [int(v) for v in row]
    finally:
        con.close()
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="paired-box control arms over two shas")
    ap.add_argument("--game", required=True, help="game id (runtime key, e.g. ar25)")
    ap.add_argument("--shas", required=True, help="two shas, comma-separated: A,B")
    ap.add_argument("--episodes", type=int, required=True, help="episodes per arm")
    ap.add_argument("--seed-fabric", default=DEFAULT_SEED,
                    help="shared read-only fabric seed dir mounted into BOTH arms")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate worktrees + commands; run nothing; clean up")
    args = ap.parse_args(argv)

    shas = [s.strip() for s in args.shas.split(",") if s.strip()]
    if len(shas) != 2:
        print("--shas needs exactly two (A,B); got %r" % (args.shas,))
        return 2
    seed_dirs = [args.seed_fabric] if os.path.isdir(args.seed_fabric) else []
    if not seed_dirs:
        print("NOTE: seed fabric %s absent -- arms run seedless (still paired)"
              % args.seed_fabric)

    key = _arc_key()
    if not args.dry_run and not key:
        print("ARC_KEY missing from .env -- a live paired run cannot start")
        return 2

    arms = []
    created = []
    try:
        for sha in shas:
            full, short = _resolve(sha)
            wt, was_created = _ensure_worktree(full, short)
            if was_created:
                created.append(wt)
            runner_ok = os.path.isfile(os.path.join(wt, "evolution_runner.py"))
            box = os.path.join(ARMS_ROOT, short, "box_%s" % args.game)
            cmd = _arm_command(wt, args.game, args.episodes)
            arms.append({"sha": full, "short": short, "worktree": wt, "box": box,
                         "cmd": cmd, "runner_ok": runner_ok})

        print("control-arm plan: game=%s episodes=%d shared_seeds=%s"
              % (args.game, args.episodes, seed_dirs or "NONE"))
        ok = True
        for a in arms:
            print("  arm %s" % a["short"])
            print("    worktree: %s (evolution_runner.py %s)"
                  % (a["worktree"], "present" if a["runner_ok"] else "MISSING"))
            print("    box:      %s" % a["box"])
            print("    cmd:      %s" % " ".join(a["cmd"]))
            print("    env:      PYTHONPATH=<worktree>  OURO_FABRIC_SEEDS=%d dir(s)  "
                  "ARC_API_KEY=%s" % (len(seed_dirs), "set" if key else "UNSET"))
            ok = ok and a["runner_ok"]

        if args.dry_run:
            print("dry-run: worktree creation %s; commands constructed; nothing ran"
                  % ("VALIDATED" if ok else "FAILED (runner missing)"))
            return 0 if ok else 1
        if not ok:
            print("refusing to run: a worktree lacks evolution_runner.py")
            return 1

        procs = []
        for a in arms:
            os.makedirs(a["box"], exist_ok=True)
            logf = open(os.path.join(a["box"], "arm.log"), "a", encoding="utf-8",
                        errors="replace")
            p = subprocess.Popen(a["cmd"], cwd=a["box"],
                                 env=_arm_env(a["worktree"], a["box"], seed_dirs, key),
                                 stdout=logf, stderr=subprocess.STDOUT)
            procs.append((a, p, logf))
            print("arm %s started (pid %d)" % (a["short"], p.pid))
        for a, p, logf in procs:
            rc = p.wait()
            logf.close()
            print("arm %s finished rc=%s" % (a["short"], rc))

        # ── the delta report: the verdict is B minus A ────────────────────────
        report = {"game": args.game, "episodes": args.episodes,
                  "when": time.strftime("%Y-%m-%d %H:%M:%S"), "arms": {}}
        for a in arms:
            report["arms"][a["short"]] = _box_stats(a["box"])
        sa, sb = (report["arms"][a["short"]] for a in arms)
        print("\nDELTA REPORT (%s -> %s), game=%s, %d episodes/arm"
              % (arms[0]["short"], arms[1]["short"], args.game, args.episodes))
        for k in ("sessions", "level_completions", "frame_changes",
                  "best_level_completions", "win_detected"):
            print("  %-24s A=%-8d B=%-8d delta=%+d" % (k, sa[k], sb[k], sb[k] - sa[k]))
        out = os.path.join(ARMS_ROOT, "delta_%s_%s_vs_%s.json"
                           % (args.game, arms[0]["short"], arms[1]["short"]))
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print("report written: %s" % out)
        return 0
    finally:
        if args.dry_run:
            for wt in created:
                _remove_worktree(wt)
            if created:
                print("dry-run cleanup: removed %d worktree(s) it created" % len(created))


if __name__ == "__main__":
    sys.exit(main())
