"""
dynamics.py  --  multi-frame OBJECT-PHYSICS tracker (makes the dynamics molecules load-bearing)
================================================================================================
Perceiving visual dynamics / frame animation. Tracks objects across a frame sequence and reads their
physics, BINDING the perceptual molecules from the grammar (SLIDE, FALL, APPEAR, DISAPPEAR, BREAK/SEPARATE,
JOIN, SPIN, GROW=EXTEND, CHANGE, STAY) and the scene-level concept molecules (GRAVITY, CONVEYOR). Each bound
event carries its grammar primes (via objective_grammar.explain_molecule), so dynamics are grammar-grounded.

Two-stage correspondence per consecutive frame pair:
  Stage 1 (overlap): shared cells -> in-place events (STAY/CHANGE/GROW/SHRINK/SPIN, SPLIT, MERGE)
  Stage 2 (motion):  remaining objects matched by colour+shape+proximity -> SLIDE/FALL/ROTATE
  Stage 3 (residual): leftover -> APPEAR / DISAPPEAR
Then aggregate across the sequence -> scene physics (GRAVITY, CONVEYOR, SETTLE).

Observe-only; reuses visual_projection's perception. Wiring into the projection is a separate, gated step.
"""
from __future__ import annotations
import os, sys as _sys
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field

_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.join(_here, "latest_008")):
    if os.path.isdir(_p) and _p not in _sys.path:
        _sys.path.insert(0, _p)
import visual_projection as VP
try:
    import objective_grammar as G
except Exception:
    G = None

# molecule each dynamics kind binds (all exist in the grammar; SHRINK has no molecule -> CHANGE)
_KIND2MOL = {"SLIDE": "SLIDE", "FALL": "FALL", "STAY": "STAY", "CHANGE": "CHANGE", "GROW": "EXTEND",
             "SHRINK": "CHANGE", "SPIN": "SPIN", "SPLIT": "BREAK", "MERGE": "JOIN",
             "APPEAR": "APPEAR", "DISAPPEAR": "DISAPPEAR", "GRAVITY": "GRAVITY", "CONVEYOR": "CONVEYOR"}


def _norm(sig):
    ys = [y for y, x in sig]; xs = [x for y, x in sig]
    y0, x0 = min(ys), min(xs)
    return frozenset((y - y0, x - x0) for y, x in sig)


def _rotations(sig):
    cur = sig
    out = []
    for _ in range(4):
        out.append(_norm(cur))
        cur = frozenset((x, -y) for y, x in cur)   # rotate 90 deg
    return out


@dataclass
class Event:
    kind: str
    molecule: str
    a: int = -1
    b: int = -1
    vector: tuple = (0, 0)
    detail: str = ""


def _to_grid(fr):
    a = np.asarray(fr)
    while a.ndim > 2:
        a = a[-1]
    if a.ndim == 1:
        s = int(round(a.size ** 0.5))
        if s * s == a.size:
            a = a.reshape(s, s)
    return a


def pair_dynamics(g_a, g_b):
    """Events between two consecutive frames."""
    A, _ = VP.extract_objects(g_a)
    B, _ = VP.extract_objects(g_b)
    events = []
    a_used, b_used = set(), set()

    # --- Stage 1: cell-overlap -> in-place events, split, merge ---
    a_to_b = defaultdict(list); b_to_a = defaultdict(list)
    for a in A:
        for b in B:
            if a.cells & b.cells:
                a_to_b[a.id].append(b.id); b_to_a[b.id].append(a.id)
    Aby = {a.id: a for a in A}; Bby = {b.id: b for b in B}
    for a in A:
        bs = a_to_b.get(a.id, [])
        if len(bs) >= 2 and all(len(b_to_a[bi]) == 1 for bi in bs):       # one a -> many b
            events.append(Event("SPLIT", _KIND2MOL["SPLIT"], a.id, -1, detail=f"into {len(bs)}"))
            a_used.add(a.id); b_used.update(bs)
    for b in B:
        as_ = b_to_a.get(b.id, [])
        if len(as_) >= 2 and all(len(a_to_b[ai]) == 1 for ai in as_):     # many a -> one b
            events.append(Event("MERGE", _KIND2MOL["MERGE"], -1, b.id, detail=f"from {len(as_)}"))
            b_used.add(b.id); a_used.update(as_)
    for a in A:                                                            # 1<->1 overlap: in-place
        if a.id in a_used:
            continue
        bs = [bi for bi in a_to_b.get(a.id, []) if bi not in b_used]
        if len(bs) == 1 and len(b_to_a[bs[0]]) == 1:
            b = Bby[bs[0]]
            if a.cells == b.cells:
                kind = "STAY" if a.color == b.color else "CHANGE"
            elif b.size > a.size:
                kind = "GROW"
            elif b.size < a.size:
                kind = "SHRINK"
            elif _norm(b.shape_sig) in _rotations(a.shape_sig)[1:]:
                kind = "SPIN"
            else:
                kind = "CHANGE"
            events.append(Event(kind, _KIND2MOL[kind], a.id, b.id))
            a_used.add(a.id); b_used.add(b.id)

    # --- Stage 2: motion match (no overlap) by colour+shape+proximity ---
    rem_a = [a for a in A if a.id not in a_used]
    rem_b = [b for b in B if b.id not in b_used]
    cand = []
    for a in rem_a:
        for b in rem_b:
            if a.color != b.color:
                continue
            d = abs(a.centroid[0] - b.centroid[0]) + abs(a.centroid[1] - b.centroid[1])
            if d > 24:
                continue
            same = _norm(a.shape_sig) == _norm(b.shape_sig)
            rot = (not same) and (_norm(b.shape_sig) in _rotations(a.shape_sig))
            if same or rot:
                cand.append((d, a.id, b.id, "rot" if rot else "same"))
    cand.sort()
    for d, ai, bi, how in cand:
        if ai in a_used or bi in b_used:
            continue
        a, b = Aby[ai], Bby[bi]
        dv = (round(b.centroid[0] - a.centroid[0]), round(b.centroid[1] - a.centroid[1]))
        if how == "rot":
            kind = "SPIN"
        elif dv == (0, 0):
            kind = "STAY"
        elif dv[0] > 0 and abs(dv[1]) <= abs(dv[0]):
            kind = "FALL"
        else:
            kind = "SLIDE"
        events.append(Event(kind, _KIND2MOL[kind], ai, bi, vector=dv))
        a_used.add(ai); b_used.add(bi)

    # --- Stage 3: residual ---
    for a in A:
        if a.id not in a_used:
            events.append(Event("DISAPPEAR", _KIND2MOL["DISAPPEAR"], a=a.id))
    for b in B:
        if b.id not in b_used:
            events.append(Event("APPEAR", _KIND2MOL["APPEAR"], b=b.id))
    return events


@dataclass
class DynamicsRead:
    n_frames: int
    events_per_step: list
    scene: dict
    molecules: list       # bound molecules (deduped, scene-level), grammar-grounded

    def explain(self):
        if G is None:
            return ", ".join(self.molecules)
        out = []
        for m in self.molecules:
            e = G.explain_molecule(m)
            out.append(f"- {m}: {e.get('words','?')}  primes={e.get('primes',())}")
        return "\n".join(out)


def track(frames):
    grids = [_to_grid(f) for f in frames]
    per_step = [pair_dynamics(grids[i], grids[i + 1]) for i in range(len(grids) - 1)]

    # aggregate scene physics
    fall_dirs = defaultdict(int); slide_vecs = defaultdict(int)
    counts = defaultdict(int)
    for evs in per_step:
        for e in evs:
            counts[e.kind] += 1
            if e.kind == "FALL":
                fall_dirs[e.vector] += 1
            if e.kind == "SLIDE":
                slide_vecs[e.vector] += 1
    scene = {}
    bound = set()
    total_nonstay = sum(c for k, c in counts.items() if k != "STAY")
    sig = max(3, int(0.10 * total_nonstay))     # coincidence gate: a molecule needs significant support
    # GRAVITY: >=2 fall events sharing a downward direction (across the sequence)
    if sum(fall_dirs.values()) >= max(2, sig):
        scene["gravity"] = max(fall_dirs, key=fall_dirs.get)
        bound.add("GRAVITY")
    # CONVEYOR: a dominant shared SLIDE vector among multiple objects (a belt)
    if slide_vecs:
        v, n = max(slide_vecs.items(), key=lambda kv: kv[1])
        if n >= max(2, sig):
            scene["conveyor"] = v; bound.add("CONVEYOR")
    # SETTLE: motion present then STAY dominates later -> settling
    if counts.get("FALL", 0) + counts.get("SLIDE", 0) >= sig and counts.get("STAY", 0) > 0:
        scene["settle"] = True
    # surface event-kind molecules only if their support is SIGNIFICANT (kills singleton noise like 1 SPLIT)
    for k, c in counts.items():
        if k == "STAY":
            continue
        if k in _KIND2MOL and c >= sig:
            bound.add(_KIND2MOL[k])
    scene["counts"] = dict(counts)
    scene["significance_gate"] = sig
    return DynamicsRead(n_frames=len(grids), events_per_step=per_step, scene=scene,
                        molecules=sorted(bound))


if __name__ == "__main__":
    # synthetic: a 2-cell block falling, and a block sliding right
    g0 = np.zeros((10, 10), int); g0[1, 1] = 2; g0[1, 2] = 2; g0[5, 5] = 3
    g1 = np.zeros((10, 10), int); g1[2, 1] = 2; g1[2, 2] = 2; g1[5, 6] = 3
    g2 = np.zeros((10, 10), int); g2[3, 1] = 2; g2[3, 2] = 2; g2[5, 7] = 3
    dr = track([g0, g1, g2])
    print("scene:", dr.scene)
    print("molecules:", dr.molecules)
