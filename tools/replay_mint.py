#!/usr/bin/env python3.12
"""
replay_mint.py -- OFFLINE BENCH: re-score banked residuals under the OLD and NEW acceptance codes, on the FRESH
segment and on the POOL, without spending a live sweep on each combination.

WHY THIS EXISTS. Two changes landed together and each of them makes minting easier:
  (A) the selection cost is charged over ELIGIBLE candidates (plus a parametric-complexity term per fitted
      sub-stream, which pulls the other way), and
  (B) residuals PERSIST, so a mint can be attempted on pooled evidence rather than on one segment's ~5 items.
Two changes and one number is not a measurement -- if the stall distribution moves, nothing in a live sweep says
which change moved it. This tool replays the SAME banked evidence through all four combinations, so the
attribution is arithmetic instead of narrative.

WHAT IT CANNOT TELL YOU. It reads the bank, which only contains residuals that were computed at all. It says
nothing about DIED_PRE_DIFF (the diff never ran -- there is no evidence to replay) and nothing about whether a
minted φ ever gets USED. It reports mints and echoes, which is the gate under test, and stops there.

THE UNDO IS PRE-REGISTERED. `keys_on_2plus_tasks` is the criterion, agreed before the run: if mints appear but no
key ever recurs on a second distinct task, this is inventing noise and both changes get reverted.

    python3.12 tools/replay_mint.py [--bank DIR] [--max-size 2]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from newhorse.redux_arch.dsl import Predicate, enumerate_predicates          # noqa: E402
from newhorse.redux_arch.minting import (_entropy_bits, _parametric_bits,    # noqa: E402
                                         two_part_mdl)
from newhorse.redux_arch.residual_bank import DEFAULT_BANK_DIR, Deposit      # noqa: E402


def _key(pred: Predicate) -> str:
    return "+".join(sorted(a.name for a in pred.atoms))


def score_old(exceptions, max_size: int = 2) -> Optional[Predicate]:
    """The PRE-CHANGE code, kept here verbatim in behaviour so the comparison is against what actually ran:
    plug-in entropy with no parametric term, and a selection cost over every CONSTRUCTED candidate."""
    n = len(exceptions)
    if n < 2:
        return None
    k = sum(1 for _, o in exceptions if o)
    baseline = _entropy_bits(n, k)
    if baseline == 0.0:
        return None
    colours = set()
    for ctx, _ in exceptions:
        colours.add(ctx.focus_colour)
        if ctx.intended_colour is not None:
            colours.add(ctx.intended_colour)
    preds = enumerate_predicates(colours, max_size=max_size)
    sel = math.log2(len(preds)) if preds else 0.0
    best, best_total = None, baseline
    for pred in preds:
        pos = [o for ctx, o in exceptions if pred.holds(ctx)]
        neg = [o for ctx, o in exceptions if not pred.holds(ctx)]
        if not pos or not neg:
            continue
        total = pred.cost() + sel + _entropy_bits(len(pos), sum(pos)) + _entropy_bits(len(neg), sum(neg))
        if total < best_total - 1e-9:
            best_total, best = total, pred
    return best


def score_new(exceptions, max_size: int = 2) -> Optional[Predicate]:
    m = two_part_mdl(exceptions, max_size=max_size)
    return None if m is None else m.predicate


def load_bank(root: str) -> Dict[str, List[Deposit]]:
    out: Dict[str, List[Deposit]] = {}
    if not os.path.isdir(root):
        return out
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".json"):
            continue
        try:
            blob = json.load(open(os.path.join(root, fn), encoding="utf-8"))
        except Exception:
            continue
        deps = sorted((Deposit.from_json(d) for d in blob.get("deposits", [])), key=lambda d: d.serial)
        if deps:
            out[blob.get("key", fn[:-5])] = deps
    return out


def replay(bank: Dict[str, List[Deposit]], max_size: int = 2) -> Dict[str, dict]:
    """Four cells: {old,new} × {fresh,pool}. A mint is credited to the CURRENT task in every cell -- the same
    one-mint-one-task rule the live wiring uses, so the echo counts here mean what they mean there."""
    cells = {name: dict(mints=0, attempts=0, tasks_by_key=defaultdict(set), pool_sizes=[])
             for name in ("old_fresh", "new_fresh", "old_pool", "new_pool")}
    for family, deps in bank.items():
        pool: List = []
        for d in deps:
            pool.extend(d.exceptions)
            for name, scorer, ev in (("old_fresh", score_old, d.exceptions), ("new_fresh", score_new, d.exceptions),
                                     ("old_pool", score_old, pool), ("new_pool", score_new, pool)):
                c = cells[name]
                c["attempts"] += 1
                c["pool_sizes"].append(len(ev))
                p = scorer(list(ev), max_size=max_size)
                if p is not None:
                    c["mints"] += 1
                    c["tasks_by_key"][_key(p)].add("%s|%s" % (family, d.task_id))
    out = {}
    for name, c in cells.items():
        by_key = {k: sorted(v) for k, v in c["tasks_by_key"].items()}
        two_plus = {k: v for k, v in by_key.items() if len(v) >= 2}
        sizes = sorted(c["pool_sizes"])
        out[name] = dict(attempts=c["attempts"], mints=c["mints"],
                         mint_rate=(c["mints"] / c["attempts"] if c["attempts"] else 0.0),
                         median_evidence=(sizes[len(sizes) // 2] if sizes else 0),
                         distinct_keys=len(by_key),
                         keys_on_2plus_tasks=len(two_plus),
                         echoing_keys={k: v for k, v in sorted(two_plus.items())})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default=DEFAULT_BANK_DIR)
    ap.add_argument("--max-size", type=int, default=2)
    a = ap.parse_args()

    bank = load_bank(a.bank)
    if not bank:
        print("NO BANKED RESIDUALS at %s -- nothing to replay. Run a sweep first; an empty bench is not a zero."
              % a.bank)
        return 1
    print("BANK  %s" % a.bank)
    for fam, deps in sorted(bank.items()):
        print("  %-10s %3d deposits  %5d exceptions  %3d tasks"
              % (fam, len(deps), sum(len(d.exceptions) for d in deps), len({d.task_id for d in deps})))
    res = replay(bank, max_size=a.max_size)
    print("\n%-11s %9s %7s %9s %9s %7s %s" % ("CELL", "attempts", "mints", "rate", "median_n", "keys", "keys@2+tasks"))
    for name in ("old_fresh", "new_fresh", "old_pool", "new_pool"):
        c = res[name]
        print("%-11s %9d %7d %8.1f%% %9d %7d %d"
              % (name, c["attempts"], c["mints"], 100 * c["mint_rate"], c["median_evidence"],
                 c["distinct_keys"], c["keys_on_2plus_tasks"]))
    print("\nATTRIBUTION  code change alone: %+d mints | pooling alone: %+d | both: %+d"
          % (res["new_fresh"]["mints"] - res["old_fresh"]["mints"],
             res["old_pool"]["mints"] - res["old_fresh"]["mints"],
             res["new_pool"]["mints"] - res["old_fresh"]["mints"]))
    print("PRE-REGISTERED UNDO  mints>0 with keys@2+tasks==0 in new_pool => manufacturing noise => REVERT BOTH.")
    ech = res["new_pool"]["echoing_keys"]
    print("ECHOING KEYS (new_pool): %s" % (json.dumps(ech, indent=2) if ech else "(none)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
