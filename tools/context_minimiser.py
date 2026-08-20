"""context_minimiser.py -- W2 STAGE 2 part 3: the RETRO context-minimisation pass.

PREREG_W2_STAGE2_CONTEXT_MIN.md: where an atoms stream holds MULTIPLE observations
of one key, minimise the stored atom by the same intersection the mint now applies
at re-observation (effects.minimise_atom): cells that varied across observations
become DONT_CARE, the changed cells plus one 8-neighbourhood ring are ALWAYS
retained, and the original full context is preserved in `context_full` (the undo).
Where a key holds ONE observation the atom is emitted UNCHANGED and marked
"singleton": true -- no invented minimisation, the read can see the split.

A TOOL, NOT AUTO-RUN. Read-only on the source stream; the minimised stream is
written to a NEW output file given on the command line (refused if it names the
input). Nothing is modified in place; the source remains the holder of record.

F1 IS ENFORCED INSIDE THE PASS: every minimised atom must still match and
correctly predict EVERY one of its own recorded same-shape observations
(effects.apply_effect over the observed context patch reproduces the observed
after-patch). One failure reverts THAT key to its unminimised atom, emitted with
"reverted": true -- stated, never silent. (Gate: tests/gate/test_context_min.py.)

THE EVIDENCE LIMIT, stated up front (measured 2026-08-20 over the 2,009 records
in .runs/swarm/*/ego_fabric/collective/atoms.jsonl): 1,967 distinct keys; 42 keys
hold 2+ same-shape observations; ALL 42 pairs carry BYTE-IDENTICAL contexts
(41/42 are import-echoes of a single mint, 1/42 a local+import pair). The atom
key hashes the full context patch, so same-key observations are identical by
construction and the intersection shrinks NOTHING on today's streams. This pass
ships the MECHANISM ahead of the evidence it needs (streams whose keys ever
loosen, or already-minimised atoms accruing further observations); it is not a
claim that the evidence exists today.

Usage: python tools/context_minimiser.py ATOMS_JSONL OUT_JSONL

Output record = the key's LAST record envelope (Gamma.get reads last-wins) with:
  "atom"          the minimised atom (or the stored atom, unchanged)
  "singleton"     true iff the key held exactly one observation
  "observations"  how many records the key held
  "ctx_min"       true iff the intersection actually shrank the context
  "reverted"      true iff a minimisation failed F1 and was reverted (rare, loud)

Deterministic; stdlib + numpy + engines.egocentric only. Exit 0 on success.
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import applicability, effects


def _read_stream(path: str) -> List[Dict[str, Any]]:
    """Parseable records, in stream order. Torn tails (a crash mid-write) are
    skipped, counted by the caller via len() difference if it cares."""
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def _observation(rec: Dict[str, Any]) -> Optional[Tuple[List, List]]:
    """(context, after) of one recorded observation, or None if unreadable."""
    atom = rec.get("atom") or {}
    ctx = atom.get("context")
    out = (atom.get("transform") or {}).get("after")
    if not isinstance(ctx, list) or not ctx or not isinstance(ctx[0], list):
        return None
    if not isinstance(out, list) or not out or not isinstance(out[0], list):
        return None
    return ctx, out


def _predicts(atom: Dict[str, Any], ctx: List, out: List) -> bool:
    """F1's unit check: applied to the observed context patch itself, the atom
    must fire and reproduce the observed after-patch exactly."""
    try:
        res = effects.apply_effect(atom, np.asarray(ctx))
        return res is not None and np.array_equal(res, np.asarray(out))
    except Exception:
        return False


def minimise_stream(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]],
                                                            Dict[str, int]]:
    """The pass, pure: records in, ONE output record per key (first-seen key
    order) + counters. Never mutates its input."""
    by_key: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()
    passthrough: List[Dict[str, Any]] = []
    for rec in records:
        key = (rec.get("atom") or {}).get("key") or rec.get("key")
        if key:
            by_key.setdefault(str(key), []).append(rec)
        else:
            passthrough.append(rec)      # composites etc: emitted verbatim below
    stats = {"records": len(records), "keys": len(by_key),
             "singletons": 0, "multi": 0, "minimised": 0, "reverted": 0,
             "keyless": len(passthrough)}
    out_records: List[Dict[str, Any]] = []
    for _key, recs in by_key.items():
        base = dict(recs[-1])                       # last-wins envelope
        base["observations"] = len(recs)
        if len(recs) == 1:
            stats["singletons"] += 1
            base["singleton"] = True                # no invented minimisation
            out_records.append(base)
            continue
        stats["multi"] += 1
        base["singleton"] = False
        obs = [o for o in (_observation(r) for r in recs) if o is not None]
        current: Optional[Dict[str, Any]] = dict(recs[0].get("atom") or {})
        shrank = False
        for ctx, _after in obs[1:]:                 # fold the intersection forward
            m = effects.minimise_atom(current, ctx)
            if m is not None:
                current, shrank = m, True
        if not shrank:
            out_records.append(base)                # identical contexts: nothing to do
            continue
        # F1, enforced here: one failed observation reverts THIS minimisation.
        same_shape = [(c, a) for c, a in obs
                      if len(c) == len(current["context"])
                      and len(c[0]) == len(current["context"][0])]
        if all(_predicts(current, c, a) for c, a in same_shape):
            current[applicability.ASIG_FIELD] = (
                applicability.anchor_signature(current))    # restamp the cache
            base["atom"] = current
            base["ctx_min"] = True
            stats["minimised"] += 1
        else:
            base["reverted"] = True                 # loud, per the falsifier
            stats["reverted"] += 1
        out_records.append(base)
    out_records.extend(dict(r) for r in passthrough)
    return out_records, stats


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__.split("Usage:")[1].split("\n")[0].strip()
              if "Usage:" in (__doc__ or "") else
              "usage: context_minimiser.py ATOMS_JSONL OUT_JSONL")
        return 2
    src, dst = argv
    if not os.path.isfile(src):
        print("ERROR: source stream not found: %s" % src)
        return 2
    if os.path.exists(dst) and os.path.samefile(src, dst):
        print("ERROR: output must be a NEW file -- this pass never modifies "
              "the source stream in place (%s)" % src)
        return 2
    records = _read_stream(src)
    out_records, stats = minimise_stream(records)
    with open(dst, "w", encoding="utf-8") as fh:
        for rec in out_records:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
    print("context_minimiser: %(records)d records -> %(keys)d keys "
          "(%(singletons)d singleton, %(multi)d multi; %(minimised)d minimised, "
          "%(reverted)d reverted, %(keyless)d keyless passthrough)" % stats)
    if stats["multi"] and not stats["minimised"] and not stats["reverted"]:
        print("context_minimiser: NOTE -- every multi-observation key carried "
              "identical contexts (the key hashes the full context patch), so "
              "the intersection shrank nothing. The limit is stated in the "
              "module docstring; it is not papered over.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
