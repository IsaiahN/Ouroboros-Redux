"""PREMISE PASS — every constant, threshold, cap, window and default, with its date and
the premise it was chosen against.

**THIS IS A READ, NOT A RE-TUNING. NOTHING CHANGES ON THE STRENGTH OF BEING OLD.**

The date is HOW YOU FIND THEM, NOT HOW YOU JUDGE THEM. A value set three days ago against
the online rate limit is stale; one from 2025 whose conditions are unchanged is fine.

THREE BUCKETS:
  PREMISE MOVED   — the conditions it was set against no longer obtain. Does NOT mean the
                    value is wrong; means nobody has checked it since the world changed.
  PREMISE UNKNOWN — no comment, no commit message. GUESSED whether labelled or not.
  STILL HOLDS     — only where a premise is stated AND is unaffected by the four moves.

FOUR PREMISES THAT MOVED, each with a grep-able signature (Seat 3):
  1 ONLINE->OFFLINE     sized against 600 req/min, network latency, rate-limit sharing
  2 BOX GROWTH          assumes a small local DB: windows, batching, checkpoints, retention
  3 POPULATION/WORKERS  computed from 25 workers, or int(6 * fraction) truncation
  4 ACTION-BUDGET       the L1 estimator showed it is per-game and per-level, not constant

R4: **KNOWN-POSITIVE that must fire** = `wal_autocheckpoint` (box growth).
    **KNOWN-NEGATIVE that must not** = `min_evidence` (an epistemic threshold — how much
    evidence convinces us — which none of the four moves touches).
Candidates, never a census.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROD = ["engines", "cognitive_loop.py", "cognitive_game_player.py",
        "database_interface.py", "database_logger.py", "evolution_runner.py",
        "game_player.py", "arc_api_adapter.py", "core_gameplay.py"]
SKIP = {".venv", ".runs", ".git", "tests", "deprecated", "archive",
        "environment_files", "__pycache__"}

# Signatures. Matched against the constant's NAME and the comment/context around it.
SIGS: List[Tuple[str, re.Pattern]] = [
    ("1 ONLINE->OFFLINE", re.compile(
        r"rate|ratelimit|request|throttl|api|network|latenc|timeout|retry|backoff|"
        r"poll|600|per_minute|rpm|concurren", re.I)),
    ("2 BOX GROWTH", re.compile(
        r"window|cap\b|keep|retention|checkpoint|batch|max_bytes|trim|prune|stream_max|"
        r"autocheckpoint|cleanup_threshold|wal|commit|flush|page", re.I)),
    ("3 POPULATION/WORKERS", re.compile(
        r"population|worker|agents_per|roster|pool|kin|per_gen|generation|offspring", re.I)),
    ("4 ACTION-BUDGET", re.compile(
        r"max_actions|budget|actions_per|allowance|atp|action_limit|per_level", re.I)),
]
# Epistemic thresholds: about how much evidence convinces us, not about the world.
# None of the four moves touches these. This is the known-negative class.
EPISTEMIC = re.compile(r"min_evidence|min_obs|purity|eps\b|half_life|confidence|"
                       r"significance|alpha\b", re.I)


def prod_files() -> List[str]:
    out = []
    for spec in PROD:
        p = os.path.join(ROOT, spec)
        if os.path.isfile(p):
            out.append(p)
        elif os.path.isdir(p):
            for r, ds, fs in os.walk(p):
                ds[:] = [d for d in ds if d not in SKIP]
                out += [os.path.join(r, f) for f in fs if f.endswith(".py")]
    return sorted(set(out))


def blame_dates(path: str) -> Dict[int, str]:
    """line -> YYYY-MM-DD, one git call per file."""
    try:
        out = subprocess.run(["git", "blame", "--line-porcelain", "--", path],
                             cwd=ROOT, capture_output=True, text=True,
                             errors="replace", timeout=120, check=False).stdout
    except Exception:
        return {}
    dates: Dict[int, str] = {}
    line_no: Optional[int] = None
    import datetime
    for ln in out.splitlines():
        m = re.match(r"^[0-9a-f]{7,40} \d+ (\d+)", ln)
        if m:
            line_no = int(m.group(1))
        elif ln.startswith("author-time ") and line_no is not None:
            try:
                ts = int(ln.split()[1])
                dates[line_no] = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            except Exception:
                pass
    return dates


def context(src_lines: List[str], lineno: int) -> str:
    lo = max(0, lineno - 4)
    return " ".join(src_lines[lo:lineno + 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    rows = []
    for path in prod_files():
        try:
            src = open(path, encoding="utf-8", errors="replace").read()
            tree = ast.parse(src)
        except Exception:
            continue
        lines = src.splitlines()
        dates = blame_dates(path)
        # A constant with a premise PARAMETERISES behaviour. `self.count = 0` inside a
        # method INITIALISES state and has no premise to move. Only module- and
        # class-level assignments qualify.
        top_level_assigns = set()
        for _n in ast.walk(tree):
            if isinstance(_n, (ast.Module, ast.ClassDef)):
                for _st in _n.body:
                    if isinstance(_st, ast.Assign):
                        top_level_assigns.add(id(_st))
        rel = os.path.relpath(path, ROOT).replace("\\", "/")

        def add(name: str, val, lineno: int, kind: str,
                lines=lines, rel=rel, dates=dates) -> None:
            ctx = context(lines, lineno - 1)
            blob = f"{name} {ctx}"
            has_comment = "#" in ctx
            buckets = [tag for tag, pat in SIGS if pat.search(blob)]
            epistemic = bool(EPISTEMIC.search(name))
            rows.append({"file": rel, "line": lineno, "name": name, "val": val,
                         "kind": kind, "date": dates.get(lineno, "?"),
                         "buckets": buckets, "comment": has_comment,
                         "epistemic": epistemic})

        # DEFECT-1 FIX: constants embedded in STRING LITERALS (PRAGMA x=N, LIMIT N).
        # The known-positive lives in execute("PRAGMA wal_autocheckpoint=100") and the
        # AST walk below cannot see it -- which is why R4 caught this instrument.
        for i, ln in enumerate(lines, 1):
            for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)", ln):
                if (('"' in ln or "'" in ln)
                        and re.search(r"PRAGMA|LIMIT|pragma|limit", ln)):
                    add(m.group(1), int(m.group(2)), i, "in-string")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                a = node.args
                pairs = (list(zip(a.args[len(a.args) - len(a.defaults):], a.defaults,
                                  strict=False)) if a.defaults else [])
                pairs += list(zip(a.kwonlyargs, a.kw_defaults or [], strict=False))
                for arg, d in pairs:
                    if (isinstance(d, ast.Constant)
                            and isinstance(d.value, (int, float))
                            and not isinstance(d.value, bool)):
                        add(arg.arg, d.value, d.lineno, "default-arg")
            elif isinstance(node, ast.Assign) and id(node) in top_level_assigns:
                if (isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, (int, float))
                        and not isinstance(node.value.value, bool)):
                    for t in node.targets:
                        nm = (t.id if isinstance(t, ast.Name)
                              else (t.attr if isinstance(t, ast.Attribute) else None))
                        if nm:
                            add(nm, node.value.value, node.lineno, "assign")
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == "get" and len(node.args) == 2):
                k, d = node.args
                if (isinstance(k, ast.Constant) and isinstance(k.value, str)
                        and isinstance(d, ast.Constant)
                        and isinstance(d.value, (int, float))
                        and not isinstance(d.value, bool)):
                    add(k.value, d.value, node.lineno, "get-default")

    moved = [r for r in rows if r["buckets"] and not r["epistemic"]]
    unknown = [r for r in rows if not r["buckets"] and not r["comment"]
               and not r["epistemic"]]
    holds = [r for r in rows if r["epistemic"]]

    print("=" * 78)
    print("PREMISE PASS — A READ. NOTHING CHANGES ON THE STRENGTH OF BEING OLD.")
    print("=" * 78)
    print(f"\nconstants examined: {len(rows)}")
    print(f"  PREMISE MOVED (candidates): {len(moved)}")
    print(f"  PREMISE UNKNOWN (no comment, GUESSED): {len(unknown)}")
    print(f"  epistemic / known-negative class: {len(holds)}")

    print("\n--- PREMISE MOVED — candidates, sorted by signature then date ---")
    for r in sorted(moved, key=lambda x: (x["buckets"][0], x["date"]))[:args.limit]:
        tag = ",".join(b.split()[0] for b in r["buckets"])
        print(f"  [{tag}] {r['date']}  {r['file']}:{r['line']}  "
              f"{r['name']} = {r['val']}{'' if r['comment'] else '   (no comment)'}")
    if len(moved) > args.limit:
        print(f"  ... and {len(moved) - args.limit} more")

    print("\n--- PREMISE UNKNOWN — no comment anywhere near; GUESSED by definition ---")
    for r in sorted(unknown, key=lambda x: x["date"])[:12]:
        print(f"  {r['date']}  {r['file']}:{r['line']}  {r['name']} = {r['val']}")
    if len(unknown) > 12:
        print(f"  ... and {len(unknown) - 12} more")

    # ── R4: the instrument checks itself before it is read ──────────────────
    print("\n" + "-" * 78)
    pos = [r for r in moved if "autocheckpoint" in r["name"].lower()]
    neg = [r for r in moved if EPISTEMIC.search(r["name"])]
    print(f"R4 KNOWN-POSITIVE (wal_autocheckpoint must appear as MOVED): "
          f"{'FIRED' if pos else '** DID NOT FIRE — INSTRUMENT SUSPECT **'}")
    print(f"R4 KNOWN-NEGATIVE (min_evidence-class must NOT appear as MOVED): "
          f"{'CLEAN' if not neg else '** OVER-FIRED — ' + str(len(neg)) + ' **'}")
    print("CANDIDATES, NOT A CENSUS. The date locates; the premise judges.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
