"""THE 30 GB HARD CEILING — it GATES, it does not warn.

PREREG_DISK_CEILING.md. Three binding requirements, all mechanical here:
  1 GATES  — `guard()` returns non-zero / raises. Callers STOP. Nothing merely logs.
  2 ARCHIVE-THEN-TRUNCATE, NEVER DELETE — and CLAIM-SUPPORTING paths are kept regardless
    of age or size, by the four tests in the prereg (live reader / cited by a live claim /
    irreplaceable / a control).
  3 THE WAL IS IN THE BUDGET — *.db-wal and *.db-shm counted with everything else.

USAGE
  python tools/disk_ceiling.py --check          # report, exit 1 if over
  python tools/disk_ceiling.py --guard          # the gate: exit 1 if over, for run scripts
  python tools/disk_ceiling.py --sweep          # archive-then-truncate eligible streams
  from tools.disk_ceiling import guard; guard() # in-process, raises DiskCeilingExceeded
"""
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sys
from typing import Dict, List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, ".runs")
ARCHIVE = os.path.join(RUNS, "archive")

CEILING_GB = float(os.getenv("DISK_CEILING_GB", "30"))
WARN_FRACTION = float(os.getenv("DISK_WARN_FRACTION", "0.8"))

# ── REQUIREMENT 2: settled here, because an unsettled list fires into nothing ──
# KEEP ALWAYS. Irreplaceable, controls, and the beat rule's fabrics/logs/controls.
KEEP_ALWAYS_NAMES = {
    "levelup_frames.jsonl",     # (c) IRREPLACEABLE: the only genuine frame corpus, n=9,
                                #     and the entire link-3 finding rests on it
    "winning_sequences.jsonl",  # (b) cited; the banked routes
    "status.txt",
}
KEEP_ALWAYS_DIR_PARTS = {
    "arms",       # (d) A CONTROL. A measurement's own box is never a cleanup target.
    "archive",    # never sweep the archive
    "controls",
}
# Eligible for archive-then-truncate: high-churn streams whose consumers read only a TAIL.
# Even these are ARCHIVED, never dropped — rung 3 reads settlement HISTORY, which is the
# trap the janitor genus named.
SWEEPABLE_NAMES = {
    "settlements.jsonl",
    "import_queue.jsonl",
    "mint_verdicts.jsonl",
    "idea_events.jsonl",
}
TAIL_KEEP_RECORDS = 2000     # generous: affect needs 20, rung 3 reads history from archive


class DiskCeilingExceeded(RuntimeError):
    pass


def _is_keep_always(path: str) -> bool:
    rel = os.path.relpath(path, RUNS).replace("\\", "/")
    if os.path.basename(path) in KEEP_ALWAYS_NAMES:
        return True
    return any(part in KEEP_ALWAYS_DIR_PARTS for part in rel.split("/"))


def usage_bytes() -> Tuple[int, Dict[str, int]]:
    """Total bytes under .runs — INCLUDING *.db-wal and *.db-shm (requirement 3)."""
    total = 0
    by_kind: Dict[str, int] = {}
    for r, _ds, fs in os.walk(RUNS):
        for f in fs:
            p = os.path.join(r, f)
            try:
                n = os.path.getsize(p)
            except OSError:
                continue
            total += n
            if f.endswith("-wal"):
                k = "wal"
            elif f.endswith("-shm"):
                k = "shm"
            elif f.endswith(".db"):
                k = "db"
            elif f.endswith(".jsonl"):
                k = "fabric"
            elif f.endswith((".log", ".txt")):
                k = "log"
            else:
                k = "other"
            by_kind[k] = by_kind.get(k, 0) + n
    return total, by_kind


def report() -> Tuple[float, float, Dict[str, int]]:
    total, by_kind = usage_bytes()
    gb = total / (1024 ** 3)
    return gb, gb / CEILING_GB if CEILING_GB else 0.0, by_kind


def guard(raise_on_breach: bool = True) -> bool:
    """THE GATE. True if under the ceiling. Raises (or returns False) if over."""
    gb, frac, _ = report()
    if gb >= CEILING_GB:
        msg = (f"DISK CEILING BREACHED: {gb:.2f} GB >= {CEILING_GB:.2f} GB. "
               f"RUN STOPPED. Sweep with `python tools/disk_ceiling.py --sweep`.")
        if raise_on_breach:
            raise DiskCeilingExceeded(msg)
        print(msg, file=sys.stderr)
        return False
    return True


def sweep(force: bool = False, dry_run: bool = False) -> List[str]:
    """ARCHIVE-THEN-TRUNCATE. Never deletes. Never touches a keep-always path."""
    gb, frac, _ = report()
    if not force and frac < WARN_FRACTION:
        return []
    os.makedirs(ARCHIVE, exist_ok=True)
    done: List[str] = []
    for r, ds, fs in os.walk(RUNS):
        ds[:] = [d for d in ds if d not in KEEP_ALWAYS_DIR_PARTS]
        for f in fs:
            if f not in SWEEPABLE_NAMES:
                continue
            p = os.path.join(r, f)
            if _is_keep_always(p):
                continue
            # BINARY THROUGHOUT. F2 caught this: reading with errors="replace" and
            # rewriting in text mode corrupts invalid UTF-8 and translates newlines on
            # Windows -- an evidence-preserving tool silently mutating evidence. Bytes
            # in, bytes out, newline-split only.
            try:
                with open(p, "rb") as fh:
                    raw = fh.read()
            except OSError:
                continue
            lines = raw.splitlines(keepends=True)
            if len(lines) <= TAIL_KEEP_RECORDS:
                continue
            old = b"".join(lines[:-TAIL_KEEP_RECORDS])
            tail = b"".join(lines[-TAIL_KEEP_RECORDS:])
            rel = os.path.relpath(p, RUNS).replace("\\", "/").replace("/", "__")
            arc = os.path.join(ARCHIVE, rel + ".gz")
            if dry_run:
                done.append(f"WOULD ARCHIVE {len(lines)-TAIL_KEEP_RECORDS} of {len(lines)} -> {rel}")
                continue
            # APPEND to the archive so repeated sweeps accumulate rather than overwrite
            mode = "ab" if os.path.exists(arc) else "wb"
            with gzip.open(arc, mode) as gz:
                gz.write(old)
            tmp = p + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(tail)
            shutil.move(tmp, p)
            done.append(f"archived {len(lines)-TAIL_KEEP_RECORDS} of {len(lines)} from {rel}")
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--guard", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    gb, frac, by_kind = report()
    print(f"DISK: {gb:.3f} GB of {CEILING_GB:.1f} GB ceiling  ({frac*100:.1f}%)")
    print("  by kind: " + "  ".join(
        f"{k}={v/(1024**3):.3f}GB" for k, v in sorted(by_kind.items(), key=lambda x: -x[1])))
    print(f"  WAL IS COUNTED (requirement 3): wal={by_kind.get('wal',0)/(1024**3):.3f}GB "
          f"shm={by_kind.get('shm',0)/(1024**3):.3f}GB")

    if a.sweep:
        acts = sweep(force=a.force, dry_run=a.dry_run)
        print(f"\nSWEEP: {len(acts)} stream(s) archived-then-truncated"
              + (" (DRY RUN)" if a.dry_run else ""))
        for x in acts[:20]:
            print("   " + x)
        if not acts:
            print(f"   nothing eligible (under {WARN_FRACTION*100:.0f}% of ceiling, "
                  f"or no stream longer than {TAIL_KEEP_RECORDS} records)")
        gb2, _, _ = report()
        print(f"  after: {gb2:.3f} GB")

    if a.guard or a.check:
        ok = guard(raise_on_breach=False)
        print("\nGATE: " + ("UNDER CEILING — run may proceed"
                            if ok else "BREACHED — RUN STOPPED"))
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
