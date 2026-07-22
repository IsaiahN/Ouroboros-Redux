"""
replay.py -- redux-arch P4.3: drive the AffordanceMintBridge over a RECORDED run (offline, no SDK).

Why a bespoke harness and not `ArchLoop.step`: the loop chooses its OWN action and derives the after-frame from
it, so it cannot faithfully replay a FIXED recorded transition -- the action handed to the mint-seam would not
match the recorded after-frame, corrupting the affordance label. So we replay the exact recorded
`(before, recorded_action, after)` triples through the bridge directly.

Two passes (both offline, both leak-safe):
  1. PRE-PASS learns the perception basis from the recording's own motion: the cursor colour (the smallest thing
     that rigidly translates -- `_smallest_mover`) and, per action, the cursor's characteristic displacement
     `vec` (the mode of its non-zero shifts). This is exactly what `agency.predict` would learn online; doing it
     up front just removes the online chicken-and-egg (the bridge needs a vec on step 1).
  2. MAIN PASS drives `AffordanceMintBridge(engine, calibrator)` over the triples via a minimal `ReplayLoop`
     shim (supplies `core.agency.{cursor_colour,predict,stride}` and `core.bg`). The calibrator warms up on the
     first `warmup` steps (freezing the passable set) and mints on the held-out remainder.

Nothing silent: `replay_affordance` returns the engine, the learned basis, and the moved/blocked tally.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter
from statistics import median
from typing import Dict, List, Optional, Tuple
import json
import numpy as np
from .bridge import AffordanceMintBridge, PassabilityCalibrator, _smallest_mover, _px_centroid
from .minting import MintingEngine


def load_recording(path: str) -> Tuple[List[np.ndarray], List[str]]:
    """(frames, actions) from an ARC-3 recording .jsonl -- frame = the last grid of each record."""
    recs = [json.loads(l)["data"] for l in open(path).read().splitlines()]
    frames = [np.array(r["frame"])[-1] for r in recs]
    acts = [r.get("action_input", {}).get("id", "?") for r in recs]
    return frames, acts


def learn_basis(frames: List[np.ndarray], acts: List[str]) -> Tuple[Optional[int], Dict[str, Tuple[int, int]]]:
    """Cursor colour (smallest consistent mover) and per-action characteristic pixel displacement of that cursor.
    `vec` per action = the mode of the cursor's NON-ZERO centroid shifts (its 'what this action does' -- Γ's
    prediction; blocked steps contribute nothing to the mode)."""
    votes: Counter = Counter()
    for b, a in zip(frames, frames[1:]):
        c = _smallest_mover(b, a)
        if c is not None:
            votes[c] += 1
    cursor = votes.most_common(1)[0][0] if votes else None
    deltas: Dict[str, List[Tuple[int, int]]] = {}
    if cursor is not None:
        for i in range(1, len(frames)):
            cb = _px_centroid(frames[i - 1], cursor)
            ca = _px_centroid(frames[i], cursor)
            if cb is None or ca is None:
                continue
            d = (int(round(ca[0] - cb[0])), int(round(ca[1] - cb[1])))
            if d != (0, 0):
                deltas.setdefault(acts[i], []).append(d)
    vec_table = {a: v for a, v in ((a, _dominant_axis_vec(ds)) for a, ds in deltas.items()) if v is not None}
    return cursor, vec_table


def _dominant_axis_vec(deltas: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """Snap a cloud of observed cursor displacements for ONE action to a single clean axial stride. A grid move
    is purely horizontal or vertical; raw pixel-centroid deltas pick up cross-axis jitter (tu93's `(7,-1)`),
    which then lands the projected 'cell ahead' in the wrong colour. We choose the axis carrying the most total
    motion, take the SIGN of its net displacement, and the MEDIAN magnitude along it (robust to outliers) -- a
    clean `(±stride, 0)` or `(0, ±stride)`. Zero cross-axis component by construction."""
    if not deltas:
        return None
    sr = sum(abs(dr) for dr, _ in deltas)
    sc = sum(abs(dc) for _, dc in deltas)
    if sr >= sc:
        vals = [dr for dr, _ in deltas if dr != 0]
        if not vals:
            return None
        mag = int(round(median(sorted(abs(v) for v in vals))))
        return ((1 if sum(vals) >= 0 else -1) * mag, 0)
    vals = [dc for _, dc in deltas if dc != 0]
    if not vals:
        return None
    mag = int(round(median(sorted(abs(v) for v in vals))))
    return (0, (1 if sum(vals) >= 0 else -1) * mag)


@dataclass
class _ReplayAgency:
    cursor: Optional[int]
    vec_table: Dict[str, Tuple[int, int]]
    def cursor_colour(self) -> Optional[int]:
        return self.cursor
    def predict(self, action: str) -> Tuple[int, int]:
        return self.vec_table.get(action, (0, 0))
    def stride(self) -> int:
        return 1                                          # vecs are in full pixels -> cell == pixel, stride 1


@dataclass
class _ReplayCore:
    agency: _ReplayAgency
    bg: int = 0


@dataclass
class _ReplayLoop:
    core: _ReplayCore


@dataclass
class ReplayResult:
    cursor: Optional[int]
    vec_table: Dict[str, Tuple[int, int]]
    passable: frozenset
    moved: int
    blocked: int
    engine: MintingEngine
    minted_names: List[frozenset] = field(default_factory=list)


def replay_affordance(path: str, warmup: int = 30, min_exceptions: int = 20, min_hits: int = 2,
                      max_size: int = 1) -> ReplayResult:
    """Replay one recording through the calibrated AffordanceMintBridge and report what it mints. `max_size=1`
    keeps the mint to a single atom (we want the atomic affordance predicate, not a conjunction)."""
    frames, acts = load_recording(path)
    cursor, vec_table = learn_basis(frames, acts)
    engine = MintingEngine(min_exceptions=min_exceptions, max_size=max_size)
    cal = PassabilityCalibrator(warmup=warmup, min_hits=min_hits)
    bridge = AffordanceMintBridge(engine, calibrator=cal)
    loop = _ReplayLoop(_ReplayCore(_ReplayAgency(cursor, vec_table)))
    moved = blocked = 0
    for i in range(1, len(frames)):
        before, after, action = frames[i - 1], frames[i], acts[i]
        pre = len(engine.buffer)
        bridge(loop, before, action, after)
        if len(engine.buffer) > pre:                      # a post-warmup exception was banked -> tally its label
            _, o = engine.buffer[-1]
            moved += int(bool(o)); blocked += int(not o)
    names = [frozenset(a.name for a in m.predicate.atoms) for m in engine.minted]
    return ReplayResult(cursor=cursor, vec_table=vec_table, passable=cal.passable_set(),
                        moved=moved, blocked=blocked, engine=engine, minted_names=names)
