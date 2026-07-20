"""grid_perception.py — platform-agnostic LOGICAL-GRID perception.

Many ARC-AGI-3 boards are a small logical NxN grid rendered (scaled) into the 64x64 frame, often with a
NON-INTEGER pitch (11 cells over 64px ~= 5.8). A composer that reasons + clicks in raw pixels misses the
logical cells (§11.275). This detects the logical grid from the frame and downsamples to it, so the composer
reasons in the board's native cell space; located clicks map back to frame-pixel cell centres.

No game identity, no cross-game state: the grid is read from THIS frame only. Brake-safe by construction —
reward fires on the real board, so a wrong detection makes clicks miss (abort), never a false win.
"""
import numpy as np
from collections import Counter


def _detect_axis_n(frame, axis, pmin=3, pmax=14, f1_min=0.6):
    """Detect the logical cell geometry along `axis` as (pitch, origin): cell boundaries sit at
    origin + k*pitch. This matches how boards are rendered (px = gx*scale + scale//2 + pad), so cell
    centres line up with the engine's own mapping -- clicks land dead-centre. Robust to non-integer
    effective pitch and to HUD/border overlays. Returns (pitch, origin, N) or None."""
    lines = frame if axis == 0 else frame.T
    L = lines.shape[0]
    diff = np.any(lines[1:] != lines[:-1], axis=1)
    actual = sorted(int(i) + 1 for i in np.where(diff)[0])
    if len(actual) < 2:
        return None
    best = (0.0, None, None)
    for pitch in range(pmin, pmax + 1):
        for origin in range(0, pitch):
            pred = [origin + k * pitch for k in range(L // pitch + 2) if 0 < origin + k * pitch < L]
            if len(pred) < 3:
                continue
            mp = sum(1 for p in pred if any(abs(p - a) <= 1 for a in actual))
            ma = sum(1 for a in actual if any(abs(p - a) <= 1 for p in pred))
            prec = ma / len(actual); rec = mp / len(pred)
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
            if f1 > best[0]:
                best = (f1, pitch, origin)
    if best[1] is None or best[0] < f1_min:
        return None
    pitch, origin = best[1], best[2]
    N = (L - origin + pitch - 1) // pitch
    return pitch, origin, int(N)
    """Given per-boundary edge strength along one axis (len L-1), find N (logical cells) whose predicted
    boundaries round(i*L/N) capture most edge mass. Handles non-integer pitch. Returns N or None."""
    total = float(edges.sum())
    if total <= 0:
        return None
    best = (0.0, None)
    for N in range(nmin, nmax + 1):
        hit = 0.0
        for i in range(1, N):
            b = int(round(i * L / N)) - 1
            w = [bb for bb in (b - 1, b, b + 1) if 0 <= bb < len(edges)]
            if w:
                hit += max(float(edges[bb]) for bb in w)
        frac = hit / total
        if frac >= frac_min:
            score = frac - 0.015 * N          # mild Occam: prefer the smallest sufficient N
            if score > best[0]:
                best = (score, N)
    return best[1]


def _axis_geom(frame, axis):
    """Per-axis (scale, pad0, N): scale = modal boundary gap (cell pitch); pad0 = first boundary; N from span."""
    lines = frame if axis == 0 else frame.T
    L = lines.shape[0]
    diff = np.any(lines[1:] != lines[:-1], axis=1)
    bnd = sorted(int(i) + 1 for i in np.where(diff)[0])
    if len(bnd) < 3:
        return None
    gaps = [bnd[i + 1] - bnd[i] for i in range(len(bnd) - 1) if bnd[i + 1] - bnd[i] >= 2]
    if not gaps:
        return None
    scale = Counter(gaps).most_common(1)[0][0]
    pad0 = bnd[0]
    N = int(round((L - 2 * pad0) / scale))
    return scale, pad0, N


def _fidelity(frame, scale, pad, N):
    """Fraction of pixels equal to their cell's modal colour. ~1.0 for a genuine scaled board (each cell is
    one solid colour); low for a native game whose fine structure would be destroyed by downsampling."""
    H, W = frame.shape
    match = 0
    for i in range(N):
        r0, r1 = pad + i * scale, min(H, pad + (i + 1) * scale)
        if r1 <= r0:
            continue
        for j in range(N):
            c0, c1 = pad + j * scale, min(W, pad + (j + 1) * scale)
            if c1 <= c0:
                continue
            block = frame[r0:r1, c0:c1]
            vals, counts = np.unique(block, return_counts=True)
            match += int(counts.max())
    span = N * scale
    return match / float(min(H, span) * min(W, span)) if span else 0.0


def detect_grid(frame, fidelity_min=0.93):
    """Detect logical cell geometry for a scaled/tiled board, else None (native). Boards render CENTRED with
    a deterministic mapping (scale=int(64/N), pad=(64-N*scale)//2), so we recover the reliable axis (finest
    scale; ties -> larger pad) and re-derive the CENTRED pad -- reproducing the engine mapping so clicks land
    dead-centre. CONFIDENCE GATE: only commit if downsampling preserves the frame (reconstruction fidelity),
    so native games with incidental fine structure stay native. Returns {pr,pc,or_,oc,nr,nc,H,W} or None."""
    H, W = frame.shape
    cands = [g for g in (_axis_geom(frame, 0), _axis_geom(frame, 1)) if g is not None]
    if not cands:
        return None
    scale, _, N = min(cands, key=lambda g: (g[0], -g[1]))     # finest pitch, then larger pad
    if scale <= 1 or N < 3 or N > 40:
        return None
    pad = (H - N * scale) // 2                                # centred pad (matches engine)
    if pad < 0:
        return None
    if _fidelity(frame, scale, pad, N) < fidelity_min:        # not a clean tiling -> treat as native
        return None
    return {"pr": scale, "pc": scale, "or_": pad, "oc": pad, "nr": N, "nc": N, "H": int(H), "W": int(W)}


def downsample(frame, spec):
    """Modal colour per logical cell. Modal is robust to sparse click-animation pixels overlaying a cell."""
    pr, pc, or_, oc, nr, nc = spec["pr"], spec["pc"], spec["or_"], spec["oc"], spec["nr"], spec["nc"]
    out = np.zeros((nr, nc), dtype=frame.dtype)
    for i in range(nr):
        r0, r1 = or_ + i * pr, min(spec["H"], or_ + (i + 1) * pr)
        for j in range(nc):
            c0, c1 = oc + j * pc, min(spec["W"], oc + (j + 1) * pc)
            block = frame[r0:r1, c0:c1]
            if block.size == 0:
                continue
            vals, counts = np.unique(block, return_counts=True)
            out[i, j] = vals[counts.argmax()]
    return out


def cell_to_frame(r, c, spec):
    """Logical cell (r,c) -> frame pixel centre (row_px, col_px), matching engine rendering origin+idx*pitch+pitch//2."""
    fr = spec["or_"] + int(r) * spec["pr"] + spec["pr"] // 2
    fc = spec["oc"] + int(c) * spec["pc"] + spec["pc"] // 2
    return int(fr), int(fc)
