"""regen_series.py -- ITEM 3: THE REGENERATION SERIES (within-fabric rho drift).

WHY (record/canon/THE_LADDER.md, THE REPORT FORMAT rider 2, reviewer 2026-08-17):

    "THE RATIO HAS ONE TERM: rho_readings gives crossing-spend; REGENERATION
     RATE (rho drift over time within a fabric vs its own ground) needs a time
     series nobody collects -- the roving-pool gate fires with one term missing
     unless the series starts."

This is the collector that starts it. THE CONSUMER, NAMED (the law that every
produced stream has one): THE ROVING-POOL GATE'S PRICING, whose two terms are
(1) crossing-spend, already supplied by the live rho_readings stream, and
(2) REGENERATION RATE -- how fast a fabric moves away from its own last state,
which is exactly `drift / snapshots elapsed` over this series. Adoption of that
gate is still zero, so this ships as a BEAT-READ COMPONENT: the beat protocol
invokes it, one snapshot per fabric per invocation, and the series accumulates
until the gate can be priced with both terms instead of one.

THE RECORD (one JSON line per fabric per invocation, appended to
.runs/regen_series.jsonl):

    {seq, fabric, game, atoms, classes{r0,r1,r2}, drift{r0,r1,r2},
     prev_seq, digest{r0,r1,r2}, atoms_truncated, digest_truncated, stamp}

  * drift[rN] = 1 - rho.rho_at(fabric-now, fabric-at-its-last-snapshot, N),
    computed from the stored class-count digests -- AT EVERY RUNG of the
    identity ladder, never averaged. A refit that moves only params shows at
    rung 1 and nowhere else; a compaction that drops atoms shows at rung 0.
    One collapsed number would reproduce the partition artifact in time.
  * prev_seq/drift are NULL on a fabric's first snapshot: no prior state means
    no drift, and 0.0 would read as "the fabric did not move".
  * NO WALL CLOCK. A series indexed by the sampler's clock is a latent (the
    EVICTION SPEC RIDER-1 defect class: the unit must be the system's own
    events, not the observer's). The record's ordinal is its own `seq`; any
    campaign label is PASSED IN via `stamp` and stored verbatim.
  * BOUNDED: `max_fabrics`, `max_atoms` per fabric, `max_digest` classes per
    rung -- and truncation is FLAGGED in the record, never silent.
  * READ-ONLY on fabrics; append-only on the series (a torn tail is skipped on
    read and preserved on disk, never rewritten). Re-invoking is safe: an
    unchanged fabric simply records drift 0.0.

INVOCATION: the beat protocol (a beat-read component), operator-run:
    python tools/regen_series.py --root .runs/swarm [--stamp beat-29]
Pure stdlib + engines.egocentric.rho; deterministic.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from engines.egocentric import rho  # noqa: E402

__all__ = ["DEFAULT_ROOT", "DEFAULT_OUT", "RUNGS", "MAX_FABRICS", "MAX_ATOMS",
           "MAX_DIGEST", "regen_snapshot", "main"]

DEFAULT_ROOT = os.path.join(".runs", "swarm")
DEFAULT_OUT = os.path.join(".runs", "regen_series.jsonl")

# The identity ladder's rungs, by rho's own public classifiers -- so the digest
# path this module stores is the SAME classification rho_at measures with
# (asserted equal, rung by rung, in tests/gate/test_regen_series.py).
RUNGS = {"r0": (0, rho.atom_key), "r1": (1, rho.sig_class),
         "r2": (2, rho.coarse_class)}

MAX_FABRICS = 256      # bounded sweep
MAX_ATOMS = 50000      # bounded read per fabric
MAX_DIGEST = 4096      # bounded record per rung


def _digest_key(cls: str) -> str:
    """Content address of a class string: the digest is keyed by hash so the
    record stays bounded and the (weighted-Jaccard) arithmetic is unchanged."""
    return hashlib.sha1(cls.encode("utf-8")).hexdigest()[:16]  # noqa: S324


def _weighted_jaccard(a: Dict[str, int], b: Dict[str, int]) -> float:
    """rho's multiset form, over digests instead of raw class strings:
    sum(min)/sum(max); either side empty -> 0.0 (silence is never evidence)."""
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    inter = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    union = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return float(inter) / float(union) if union else 0.0


def _read_atoms(path: str, max_atoms: int):
    """Bounded, read-only, torn-line tolerant read of one atoms.jsonl."""
    recs: List[Dict[str, Any]] = []
    truncated = False
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for raw in fh:
                if len(recs) >= max_atoms:
                    truncated = True
                    break
                line = raw.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if isinstance(rec, dict):
                    recs.append(rec)
    except Exception:
        return [], False
    return recs, truncated


def _digests(recs, max_digest: int):
    """{rung: {digest: count}} plus the class totals and a truncation flag."""
    out: Dict[str, Dict[str, int]] = {}
    classes: Dict[str, int] = {}
    truncated = False
    for name, (_rung, classifier) in RUNGS.items():
        counts = rho.class_counts(recs, classifier)
        classes[name] = sum(counts.values())
        hashed: Dict[str, int] = {}
        for cls, n in counts.items():
            hashed[_digest_key(cls)] = hashed.get(_digest_key(cls), 0) + n
        if len(hashed) > max_digest:
            truncated = True
            keep = sorted(hashed.items(), key=lambda kv: (-kv[1], kv[0]))
            hashed = dict(keep[:max_digest])
        out[name] = hashed
    return out, classes, truncated


def _read_series(out_path: str):
    """Prior state: (next_seq, {fabric: last record}). A torn/partial tail line
    is SKIPPED, never repaired and never rewritten -- the file is append-only."""
    last: Dict[str, Dict[str, Any]] = {}
    max_seq = 0
    if not os.path.exists(out_path):
        return 1, last
    try:
        with open(out_path, encoding="utf-8", errors="ignore") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not isinstance(rec, dict) or "fabric" not in rec:
                    continue
                try:
                    seq = int(rec.get("seq") or 0)
                except Exception:
                    continue
                max_seq = max(max_seq, seq)
                prev = last.get(str(rec["fabric"]))
                if prev is None or seq >= int(prev.get("seq") or 0):
                    last[str(rec["fabric"])] = rec
    except Exception:
        return max_seq + 1, last
    return max_seq + 1, last


def _find_fabrics(root: str, include_personal: bool, max_fabrics: int):
    """Fabric directories under `root` holding an atoms.jsonl, deterministic
    order, bounded count."""
    if not os.path.isdir(str(root)):
        return []
    pats = [os.path.join(str(root), "*", "ego_fabric", "collective")]
    if include_personal:
        pats.append(os.path.join(str(root), "*", "ego_fabric", "personal", "*"))
    found: List[str] = []
    for pat in pats:
        for d in sorted(glob.glob(pat)):
            if os.path.isfile(os.path.join(d, "atoms.jsonl")) and d not in found:
                found.append(d)
    return found[:max_fabrics]


def _game_of(recs, fallback: str) -> str:
    """The fabric's game, by majority over its atom records (deterministic tie
    break), falling back to the box directory name."""
    tally: Dict[str, int] = {}
    for rec in recs:
        g = rec.get("game")
        if g:
            tally[str(g)] = tally.get(str(g), 0) + 1
    if not tally:
        return fallback
    return sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _append(out_path: str, line: str) -> None:
    """Append ONE line. If a prior torn write left the file without a trailing
    newline, this record starts on a fresh line -- the damaged bytes stay
    exactly where they are (evidence is only ever added)."""
    parent = os.path.dirname(os.path.abspath(out_path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    prefix = ""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        with open(out_path, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                prefix = "\n"
    with open(out_path, "a", encoding="utf-8") as fh:
        fh.write(prefix + line + "\n")
        fh.flush()


def regen_snapshot(root: str = DEFAULT_ROOT, out_path: str = DEFAULT_OUT,
                   stamp: Optional[str] = None, max_fabrics: int = MAX_FABRICS,
                   max_atoms: int = MAX_ATOMS, max_digest: int = MAX_DIGEST,
                   include_personal: bool = False,
                   dry_run: bool = False) -> int:
    """Append ONE self-rho snapshot per fabric under `root`; return how many.

    Each snapshot compares the fabric NOW against THE SAME FABRIC at its own
    last snapshot, at every rung of the identity ladder. Read-only on fabrics,
    append-only on the series, no wall clock in the record."""
    fabrics = _find_fabrics(root, include_personal, max_fabrics)
    if not fabrics:
        return 0
    seq, last = _read_series(out_path)
    written = 0
    for d in fabrics:
        rel = os.path.relpath(d, str(root)).replace("\\", "/")
        recs, atoms_trunc = _read_atoms(os.path.join(d, "atoms.jsonl"),
                                        max_atoms)
        digest, classes, dig_trunc = _digests(recs, max_digest)
        prev = last.get(rel)
        drift: Dict[str, Optional[float]] = {}
        for name in RUNGS:
            pd = (prev or {}).get("digest", {}).get(name) if prev else None
            drift[name] = (None if prev is None
                           else 1.0 - _weighted_jaccard(digest[name], pd or {}))
        rec = {
            "seq": seq,
            "fabric": rel,
            "game": _game_of(recs, rel.split("/")[0]),
            "atoms": len(recs),
            "classes": classes,
            "drift": drift,
            "prev_seq": (int(prev["seq"]) if prev else None),
            "digest": digest,
            "atoms_truncated": bool(atoms_trunc),
            "digest_truncated": bool(dig_trunc),
            "stamp": stamp,
        }
        line = json.dumps(rec, sort_keys=True)
        print("[REGEN] seq=%d %s game=%s atoms=%d drift r0=%s r1=%s r2=%s%s"
              % (seq, rel, rec["game"], rec["atoms"],
                 _f(drift["r0"]), _f(drift["r1"]), _f(drift["r2"]),
                 " (dry-run)" if dry_run else ""))
        if not dry_run:
            _append(out_path, line)
        written += 1
        seq += 1
    return written


def _f(v) -> str:
    return "n/a" if v is None else "%.4f" % v


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="ITEM 3: the regeneration series -- within-fabric rho "
                    "drift over time; consumer = the roving-pool gate pricing")
    ap.add_argument("--root", default=DEFAULT_ROOT,
                    help="swarm root holding the per-game boxes")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="append-only series file")
    ap.add_argument("--stamp", default=None,
                    help="campaign label stored verbatim (the record carries "
                         "NO wall clock; pass any index in)")
    ap.add_argument("--max-fabrics", type=int, default=MAX_FABRICS)
    ap.add_argument("--max-atoms", type=int, default=MAX_ATOMS)
    ap.add_argument("--max-digest", type=int, default=MAX_DIGEST)
    ap.add_argument("--include-personal", action="store_true",
                    help="also snapshot per-agent personal fabrics")
    ap.add_argument("--dry-run", action="store_true",
                    help="narrate without appending")
    args = ap.parse_args(list(argv) if argv is not None else None)

    n = regen_snapshot(args.root, args.out, stamp=args.stamp,
                       max_fabrics=args.max_fabrics, max_atoms=args.max_atoms,
                       max_digest=args.max_digest,
                       include_personal=args.include_personal,
                       dry_run=args.dry_run)
    print("[REGEN] snapshots=%d root=%s out=%s" % (n, args.root, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
