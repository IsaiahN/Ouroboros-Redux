"""PROCTOR-ONLY (R2, PREREG_READOUTS.md): socket-vs-filler lint on builder diffs.

The grade the agent must never read: did a diff wire a CAPACITY (socket) or write
CONTENT (filler)? Content markers in AGENT code (engines/, cognitive_*.py; tests
excluded -- synthetic grids belong there) are firewall alarms:
  * nested numeric list literals (hardcoded grids/patterns)
  * game-id-shaped string literals (two letters + two digits)
  * numeric dict literals of size >= 3 (hardcoded mappings)
Usage:  python tools/socket_or_filler_lint.py [<rev-range>]   (default HEAD~1..HEAD)
Exit 1 iff flags found. Never wired into agent code or agent-visible tests.
"""
import re
import subprocess
import sys

AGENT_PATHS = ("engines/", "cognitive_loop.py", "cognitive_game_player.py")
EXCLUDE = ("tests/", "tools/")

GRID = re.compile(r"\[\s*\[\s*\d+\s*,\s*\d+\s*,\s*\d+")          # [[n, n, n...
GAME_ID = re.compile(r"['\"][a-z]{2}\d{2}['\"]")                   # 'ar25'
NUM_MAP = re.compile(r"\{\s*\d+\s*:\s*\d+\s*,\s*\d+\s*:\s*\d+\s*,\s*\d+\s*:")


def lint(rev_range="HEAD~1..HEAD"):
    out = subprocess.run(["git", "diff", rev_range, "--unified=0"],
                         capture_output=True, text=True).stdout
    flags, current = [], None
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            p = line[6:]
            current = p if (p.startswith(AGENT_PATHS)
                            and not p.startswith(EXCLUDE)) else None
        elif current and line.startswith("+") and not line.startswith("+++"):
            body = line[1:]
            for name, rx in (("GRID", GRID), ("GAME_ID", GAME_ID),
                             ("NUM_MAP", NUM_MAP)):
                if rx.search(body):
                    flags.append((current, name, body.strip()[:100]))
    return flags


if __name__ == "__main__":
    rng = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1..HEAD"
    fl = lint(rng)
    for f, kind, snip in fl:
        print("CONTENT FLAG [%s] %s: %s" % (kind, f, snip))
    print("%d flag(s) in %s -- %s" % (len(fl), rng,
          "FILLER SUSPECT: proctor review" if fl else "socket-clean"))
    sys.exit(1 if fl else 0)
