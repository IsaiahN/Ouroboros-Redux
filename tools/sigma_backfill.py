"""sigma_backfill.py -- B13: sigma for the legacy atoms, offline, atomically.

Every atom minted since B13 carries its prediction-signature ("sigma") at mint time;
the legacy atoms (the pre-B13 books, Kaggle seed-mounts included) predate it and can
never be recognized by the triangulation consumer. This tool derives sigma FROM THE
STORED before/after patches (no re-observation: cells outside the changed-region bbox
are unchanged by construction, so conservation, bbox class, changed class and
colour-delta computed over the patch equal the full-frame values the mint would have
written) and rewrites each atoms.jsonl in place.

════════════════════════ THE OPERATOR CONTRACT (LOUD) ════════════════════════
Fabrics are APPEND-ONLY in live operation. This tool REWRITES files. It therefore
runs ONLY with the swarm STOPPED. main() enforces a simple, deliberately paranoid
process check -- it REFUSES to run while any OTHER python process is alive on this
machine (worker, supervisor, or anything it cannot tell apart from one). --force
overrides the check; the operator who forces owns the outcome. Every rewrite is
atomic and leaves a .bak of the original beside the file.
══════════════════════════════════════════════════════════════════════════════

Unparseable lines (a crash mid-write) and records already carrying sigma are
preserved BYTE-VERBATIM; only records gaining sigma are re-serialized. Idempotent.

Usage: python tools/sigma_backfill.py FABRIC_ROOT [FABRIC_ROOT ...] [--force]

Stdlib + numpy only (via engines.egocentric.consumer.sigma_of).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import List, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.consumer import sigma_of

# ── the process check (the swarm-stopped guard) ───────────────────────────────

def _other_python_pids() -> List[int]:
    """Pids of OTHER live python processes, self excluded. Windows: tasklist CSV;
    POSIX: ps. An unavailable check returns [] -- the loud contract above then
    carries the full weight."""
    me = os.getpid()
    pids: List[int] = []
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True, timeout=30,
                                 check=False).stdout or ""
            for ln in out.splitlines():
                parts = [p.strip('"') for p in ln.split('","')]
                if len(parts) >= 2 and "python" in parts[0].lower():
                    try:
                        pid = int(parts[1])
                    except ValueError:
                        continue
                    if pid != me:
                        pids.append(pid)
        else:
            out = subprocess.run(["ps", "-eo", "pid=,comm="],
                                 capture_output=True, text=True, timeout=30,
                                 check=False).stdout or ""
            for ln in out.splitlines():
                bits = ln.split(None, 1)
                if len(bits) == 2 and "python" in bits[1].lower():
                    try:
                        pid = int(bits[0])
                    except ValueError:
                        continue
                    if pid != me:
                        pids.append(pid)
    except Exception:
        return []
    return pids


# ── the backfill ──────────────────────────────────────────────────────────────

def _atomic_rewrite(path: str, lines: List[str]) -> None:
    """tmp -> original becomes .bak -> tmp replaces original."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")
    bak = path + ".bak"
    if os.path.isfile(bak):
        os.remove(bak)
    os.replace(path, bak)
    os.replace(tmp, path)


def backfill_file(path: str) -> Tuple[int, int]:
    """Add sigma to every atom record in one atoms.jsonl that lacks it and stores
    a before/after transform pair. Returns (records seen, records updated); rewrites
    (atomically, with .bak) only when something changed."""
    if not os.path.isfile(path):
        return (0, 0)
    out: List[str] = []
    total = updated = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                out.append(line)                    # a crash mid-write is evidence
                continue
            if not isinstance(rec, dict):
                out.append(line)
                continue
            total += 1
            atom = rec.get("atom")
            if isinstance(atom, dict) and "sigma" not in atom:
                t = atom.get("transform") or {}
                b, a = t.get("before"), t.get("after")
                sig = sigma_of(b, a) if b is not None and a is not None else None
                if sig is not None and "bbox" in sig:       # a real patch description
                    atom["sigma"] = sig
                    updated += 1
                    out.append(json.dumps(rec, ensure_ascii=False))
                    continue
            out.append(line)                        # untouched records stay byte-verbatim
    if updated:
        _atomic_rewrite(path, out)
    return (total, updated)


def atoms_files(root: str) -> List[str]:
    """Every atoms.jsonl under a fabric root (collective + all personal/kin scopes)."""
    found: List[str] = []
    for dirpath, _dirs, files in os.walk(str(root)):
        for name in files:
            if name == "atoms.jsonl":
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def backfill_root(root: str) -> dict:
    """Backfill every atoms stream under one fabric root; per-file loud report."""
    files = total = updated = 0
    for path in atoms_files(root):
        t, u = backfill_file(path)
        files += 1
        total += t
        updated += u
        print("[SIGMA-BACKFILL] %s: %d records, %d gained sigma" % (path, t, u))
    return {"files": files, "total": total, "updated": updated}


# ── the CLI ───────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Backfill mint-time sigma onto legacy atoms (SWARM STOPPED ONLY).")
    ap.add_argument("roots", nargs="+", help="fabric root directories to rewrite")
    ap.add_argument("--force", action="store_true",
                    help="override the workers-alive refusal; the operator owns it")
    args = ap.parse_args(argv)
    others = _other_python_pids()
    if others and not args.force:
        print("[SIGMA-BACKFILL] REFUSING TO RUN: %d other python process(es) alive "
              "(pids %s%s). Fabrics are append-only in live operation -- STOP THE "
              "SWARM first, then rerun. (--force overrides; the operator who forces "
              "owns the outcome.)"
              % (len(others), ", ".join(str(p) for p in others[:5]),
                 ", ..." if len(others) > 5 else ""))
        return 2
    grand = {"files": 0, "total": 0, "updated": 0}
    for root in args.roots:
        rep = backfill_root(root)
        for k in grand:
            grand[k] += rep[k]
    print("[SIGMA-BACKFILL] DONE: %(files)d files, %(total)d records, "
          "%(updated)d gained sigma" % grand)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
