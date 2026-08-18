"""LINK 3 LIVE CHECK — run the abduction vocabulary against every level-up frame
this project has on disk. READ-ONLY: opens files for reading, writes nothing.

This is the operator half of the LINK3_AUDIT falsifier. The gate test
(`tests/gate/test_link3_hook_and_vocabulary.py`) pins the same claims on fixtures
derived from these boards' measured shapes, because a hermetic test must not
depend on `.runs/**` — the janitor compacts those streams and the corpus size
moves. This script reads the real records so the claim can be re-measured against
whatever is actually there.

THE THREE PRE-COMMITTED CLAUSES, all printed:
  1. > 0 predicates on records where the residual said something happens
     (the shipped-before number was 0 on every record);
  2. STILL EXACTLY ZERO for `region_uniform` and `regions_equal` — those two were
     measured unsatisfiable on this domain, and a vocabulary that starts firing
     them has REPLACED the edge rather than extended it;
  3. the PER-CLASS FIRE RATE, over records AND over distinct transitions (the
     corpus contains duplicate records of the same event). A class that fires on
     every record is a constant, not evidence, and is flagged as such.

Exit 1 if clause 1 or clause 2 fails. Clause 3 is reported, never gated — the
right response to a universal detector is judgement, not an automatic red.

  usage:  python tools/link3_live_check.py [--root .runs/swarm]

Stdlib + numpy; dev-time tool, never imported by an agent.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from engines.egocentric import goal_abduction as GA  # noqa: E402

UNSATISFIABLE_HERE = ("region_uniform", "regions_equal")
KNOWN_CLASSES = ("region_uniform", "colour_count_zero", "regions_equal",
                 "colour_present", "colour_majority",
                 "region_colour_count_atmost", "region_contains_colour")


def _load(root: str):
    """Every levelup_frames record under `root`, read-only."""
    out = []
    pattern = os.path.join(root, "**", "levelup_frames.jsonl")
    for path in sorted(glob.glob(pattern, recursive=True)):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for ln, raw in enumerate(fh):
                text = raw.strip()
                if not text:
                    continue
                try:
                    rec = json.loads(text)
                except Exception as exc:
                    print("  UNPARSEABLE %s:%d (%s)" % (path, ln, exc))
                    continue
                out.append((os.path.relpath(path, REPO), ln,
                            rec.get("data", rec)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=os.path.join(REPO, ".runs", "swarm"),
                    help="directory tree to scan (read-only)")
    args = ap.parse_args(argv)

    recs = _load(args.root)
    print("LINK 3 LIVE CHECK — %d record(s) under %s" % (len(recs), args.root))
    if not recs:
        print("NO RECORDS. Nothing measured — this is NOT a pass.")
        return 1
    print()

    per_class_records = Counter()
    per_class_transitions = {}
    transitions = {}
    total = 0
    zero_records = []

    for path, ln, d in recs:
        pre = np.asarray(d.get("pre"))
        post = np.asarray(d.get("post"))
        game, level = d.get("game"), d.get("level")
        key = hashlib.md5(
            ("%s|%s|%s" % (game, pre.tobytes(), post.tobytes())).encode(
                "utf-8", "replace")).hexdigest()[:8]
        transitions.setdefault(key, 0)
        transitions[key] += 1

        preds = GA.extract_predicates(pre, post)
        total += len(preds)
        kinds = {p.get("kind") for p in preds}
        for k in kinds:
            per_class_records[k] += 1
            per_class_transitions.setdefault(k, set()).add(key)
        if not preds:
            zero_records.append((path, ln))

        pre_cols = sorted(int(v) for v in np.unique(pre))
        post_cols = sorted(int(v) for v in np.unique(post))
        print("%-46s L%-3s game=%-16s txn=%s" % (
            os.path.basename(os.path.dirname(path)), level, game, key))
        print("    colours pre=%s post=%s appeared=%s vanished=%s" % (
            pre_cols, post_cols,
            [c for c in post_cols if c not in pre_cols],
            [c for c in pre_cols if c not in post_cols]))
        print("    predicates=%d  %s" % (
            len(preds), sorted(GA.signature(p) for p in preds)))

    n_rec, n_txn = len(recs), len(transitions)
    print()
    print("TOTAL PREDICATES OVER %d RECORD(S) / %d DISTINCT TRANSITION(S): %d"
          % (n_rec, n_txn, total))
    print()
    print("PER-CLASS FIRE RATE (clause 3 — reported, never gated):")
    all_classes = sorted(set(per_class_records) | set(KNOWN_CLASSES))
    for k in all_classes:
        r, t = per_class_records[k], len(per_class_transitions.get(k, ()))
        flag = ""
        if r == n_rec and n_rec > 1:
            flag = "   <== FIRES ON EVERY RECORD: a constant, not evidence"
        elif r == 0:
            flag = "   (silent)"
        print("    %-30s %d/%d records   %d/%d transitions%s"
              % (k, r, n_rec, t, n_txn, flag))

    print()
    ok = True
    if total <= 0:
        print("CLAUSE 1: FAIL — 0 predicates over the whole corpus. This is the "
              "shipped-before reading; nothing was fixed.")
        ok = False
    else:
        print("CLAUSE 1: PASS — %d predicate(s) extracted (was 0)." % total)
    if zero_records:
        print("          note: %d record(s) still yield 0: %s"
              % (len(zero_records), [p for p, _ in zero_records]))

    fired_dead = [k for k in UNSATISFIABLE_HERE if per_class_records[k]]
    if fired_dead:
        print("CLAUSE 2: FAIL — %r fired on this domain. Those classes were "
              "measured unsatisfiable here; firing them means the class changed "
              "meaning and the edge was replaced, not extended." % fired_dead)
        ok = False
    else:
        print("CLAUSE 2: PASS — region_uniform and regions_equal still yield "
              "exactly zero, as measured.")

    universal = [k for k in per_class_records
                 if per_class_records[k] == n_rec and n_rec > 1]
    print("CLAUSE 3: %s" % (
        "reported — %r fire on every record and must not be read as evidence"
        % sorted(universal) if universal
        else "reported — no class fires on every record"))

    print()
    print("VERDICT: %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
