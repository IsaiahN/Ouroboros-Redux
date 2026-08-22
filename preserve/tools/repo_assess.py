"""REPOSITORY ASSESSMENT — a read, at every level, with the framework applied to itself.

Seat 3, 2026-08-20: *"apply the framework recursively, to everything… including when the
system in question is you."* So the cleanup uses the loop's own step 2:

    LIVE        = TRANSFERRED       something imports/references it. Nothing owed.
    CAPABILITY  = NOVEL             holds something the architecture lacks. Extend, aim the
                                    probe -- report it, never build it here.
    MISFILED    = BROKEN.rebinding  live and in the wrong place. RE-FIT (move). Do not delete.
    SUPERSEDED  = BROKEN.mechanism  overtaken or retracted. A removal is owed, WITH A NOTE
                                    saying what replaced it.

THE GUARDS ARE A PRODUCT, and any factor at zero forbids a removal:
    SUPPORT      no importer, no reference, no bare-string hit anywhere
    REACHABILITY the deadness is checkable -- dynamic/lazy imports were searched as STRINGS,
                 not only as `import` statements
    NOVELTY      it holds nothing the live tree already has

THE LAZY-IMPORT LESSON IS BUILT IN. `manual_tools` looked like proctor tooling and is reached
only by `evolutionary_engine.py:464`'s function-local import. A module name is therefore
searched three ways: as an import, as a dotted path, and as a bare quoted string.

SKIPS every directory with a `.` prefix, at EVERY level, plus .venv and .runs.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from typing import Dict, List, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_NAMES = {"__pycache__", "node_modules", "venv"}


def walk(exts: Tuple[str, ...]) -> List[str]:
    out = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if not d.startswith(".") and d not in SKIP_NAMES]
        for f in fns:
            if f.endswith(exts):
                out.append(os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/"))
    return sorted(out)


def corpus() -> Dict[str, str]:
    """Every text file's contents, keyed by relpath. One read, many queries."""
    blob = {}
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if not d.startswith(".") and d not in SKIP_NAMES]
        for f in fns:
            if not f.endswith((".py", ".md", ".yml", ".yaml", ".toml", ".cfg", ".txt",
                               ".json", ".ini")):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    blob[os.path.relpath(p, ROOT).replace("\\", "/")] = fh.read()
            except OSError:
                pass
    return blob


def references(target: str, blob: Dict[str, str]) -> Set[str]:
    """Who mentions this file? Module name as import, as dotted path, AND as a bare
    string -- the third is what catches a dynamic import."""
    base = os.path.basename(target)
    stem = base[:-3] if base.endswith(".py") else base[:-3] if base.endswith(".md") else base
    dotted = target[:-3].replace("/", ".") if target.endswith(".py") else None
    pats = [re.compile(r"\b(?:import|from)\s+%s\b" % re.escape(stem)),
            re.compile(r"[\"']%s[\"']" % re.escape(stem)),
            re.compile(re.escape(base))]
    if dotted:
        pats.append(re.compile(re.escape(dotted)))
    hits = set()
    for path, text in blob.items():
        if path == target:
            continue
        for pat in pats:
            if pat.search(text):
                hits.add(path)
                break
    return hits


def created(path: str) -> str:
    try:
        r = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ad",
                            "--date=short", "--", path], cwd=ROOT,
                           capture_output=True, text=True, timeout=20, check=False)
        lines = [x for x in r.stdout.strip().splitlines() if x.strip()]
        return lines[-1] if lines else "?"
    except Exception:
        return "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["py", "md", "both"], default="both")
    ap.add_argument("--dates", action="store_true", help="git creation date (slow)")
    a = ap.parse_args()

    blob = corpus()
    exts = {"py": (".py",), "md": (".md",), "both": (".py", ".md")}[a.kind]
    files = walk(exts)
    print("REPOSITORY ASSESSMENT  (skips every .-prefixed dir at every level)")
    print("  files scanned: %d   corpus files searched for references: %d\n" % (
        len(files), len(blob)))

    unref = []
    for f in files:
        refs = references(f, blob)
        live_refs = {r for r in refs if not r.startswith("docs/") or True}
        if not live_refs:
            unref.append(f)
        print("%-62s refs=%-3d %s" % (f, len(live_refs),
                                      created(f) if a.dates else ""))

    print("\nZERO-REFERENCE FILES (removal CANDIDATES -- support guard satisfied only):")
    for f in unref:
        print("   %s" % f)
    print("\n%d of %d have no reference anywhere." % (len(unref), len(files)))
    print("A zero here is NOT a verdict: NOVELTY is unchecked (does it hold capability the")
    print("live tree lacks?) and that guard is read by a human, not by this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
