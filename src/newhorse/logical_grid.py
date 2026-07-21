"""
logical_grid.py -- brick 11: the LOGICAL-GRID QUANTUM LENS (harvested from Redux grid_perception,
re-expressed through the map's lens). Many ARC-3 boards are a small logical N×N grid RENDERED (scaled)
into the 64×64 frame -- so a click must land on a cell CENTRE, and a "move" is one logical cell, not one
pixel. This detects that hidden lattice from a single frame and exposes it as a COORDINATE LENS.

CRITICAL DIFFERENCE FROM REDUX (the map's hard bound): this NEVER downsamples the working frame. Redux's
grid_perception.downsample() replaces the 64×64 with an N×N array; the new horse BANS that (a glyph is
exact; averaging destroys it). Here the lens only provides (a) the pitch/quantum, (b) cell<->pixel
coordinate mapping, and (c) non-destructive per-cell colour READS. Raw full-resolution perception is
untouched; the logical grid is an ADDED service (Dijkstra separation-of-concerns), not a replacement.

FMap: arrows_impossibility (d=0.115) -- no rank-order vote among competing axis/pitch candidates cleanly
picks the true grid, so the arbiter is NOT a vote but a non-gameable FIDELITY GATE: commit a logical grid
only if downsampling to it would be NEAR-LOSSLESS (>= fidelity_min). This is also brake-safe: a wrong grid
makes located clicks MISS (abort), never a false win.

LAW-0 CALIBRATION (verified on rendered ls20 frames): ls20's true game grid is 5-px (the piece moves
exactly 5 px/action), but its whole-frame fidelity at 5-px is only 0.818, and the only tiling that passes
a 0.93 gate is a SPURIOUS 2-px/24×24 one (0.946) -- not the game grid. Losing ~5% of pixels means real
structure (the cross, glyph edges) is destroyed, which the map forbids. So the gate is set NEAR-LOSSLESS
(default 0.98): ls20 is correctly rejected as NATIVE (no clean logical board), and a mover's stride is
recovered from MOTION (brick 12), not from tiling. The lens fires only for genuinely-tiled (click) boards.
Nothing silent.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List
from collections import Counter
import numpy as np


@dataclass(frozen=True)
class GridSpec:
    """A detected logical lattice over a raw frame. Pitch = pixels per logical cell (the QUANTUM/stride)."""
    pitch_r: int
    pitch_c: int
    origin_r: int
    origin_c: int
    n_r: int
    n_c: int
    H: int
    W: int

    @property
    def stride(self) -> Tuple[int, int]:
        """Pixels per one logical-cell move -- e.g. a board upscaled 5× gives stride (5,5)."""
        return (self.pitch_r, self.pitch_c)

    @property
    def logical_shape(self) -> Tuple[int, int]:
        return (self.n_r, self.n_c)

    def cell_to_px(self, r: int, c: int) -> Tuple[int, int]:
        """Logical cell (r,c) -> raw pixel CENTRE (row_px, col_px). Matches engine rendering
        origin + idx*pitch + pitch//2, so a located click lands dead-centre on the cell."""
        fr = self.origin_r + int(r) * self.pitch_r + self.pitch_r // 2
        fc = self.origin_c + int(c) * self.pitch_c + self.pitch_c // 2
        return int(fr), int(fc)

    def px_to_cell(self, y: int, x: int) -> Tuple[int, int]:
        """Raw pixel (y,x) -> logical cell (r,c), clamped into the board."""
        r = (int(y) - self.origin_r) // self.pitch_r
        c = (int(x) - self.origin_c) // self.pitch_c
        return (max(0, min(self.n_r - 1, r)), max(0, min(self.n_c - 1, c)))

    def cell_colour(self, frame: np.ndarray, r: int, c: int) -> int:
        """NON-DESTRUCTIVE read: the modal colour of cell (r,c) taken from the RAW frame (the frame is not
        reduced or mutated -- this just looks). Modal is robust to sparse click-animation overlays."""
        r0, r1 = self.origin_r + r * self.pitch_r, self.origin_r + (r + 1) * self.pitch_r
        c0, c1 = self.origin_c + c * self.pitch_c, self.origin_c + (c + 1) * self.pitch_c
        block = np.asarray(frame)[max(0, r0):min(self.H, r1), max(0, c0):min(self.W, c1)]
        if block.size == 0:
            return 0
        vals, counts = np.unique(block, return_counts=True)
        return int(vals[counts.argmax()])

    def logical_read(self, frame: np.ndarray) -> np.ndarray:
        """A DERIVED reasoning VIEW: the modal colour per cell as an n_r×n_c array. This is for THINK-stage
        coordinate reasoning ONLY -- it is NOT the working frame and must NEVER be fed to perception or the
        ResolutionBound (raw full-res perception is untouched; the hard no-downsample bound is on the loop's
        perceive path, not on this deliberate, discarded read)."""
        out = np.zeros((self.n_r, self.n_c), dtype=np.asarray(frame).dtype)
        for i in range(self.n_r):
            for j in range(self.n_c):
                out[i, j] = self.cell_colour(frame, i, j)
        return out


def _axis_geom(frame: np.ndarray, axis: int) -> Optional[Tuple[int, int, int]]:
    """Per-axis (scale, pad0, N): scale = modal boundary gap (cell pitch); pad0 = first boundary."""
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


def fidelity(frame: np.ndarray, pitch: int, pad: int, N: int) -> float:
    """Fraction of pixels equal to their cell's modal colour: ~1.0 for a genuine scaled board (each cell one
    solid colour), lower for a native frame whose fine structure downsampling would destroy."""
    f = np.asarray(frame)
    H, W = f.shape
    match = 0
    for i in range(N):
        r0, r1 = pad + i * pitch, min(H, pad + (i + 1) * pitch)
        if r1 <= r0:
            continue
        for j in range(N):
            c0, c1 = pad + j * pitch, min(W, pad + (j + 1) * pitch)
            if c1 <= c0:
                continue
            block = f[r0:r1, c0:c1]
            _, counts = np.unique(block, return_counts=True)
            match += int(counts.max())
    span = N * pitch
    denom = float(min(H, span) * min(W, span))
    return match / denom if denom else 0.0


def detect_grid(frame: np.ndarray, fidelity_min: float = 0.98) -> Optional[GridSpec]:
    """Detect the logical lattice of a genuinely-tiled board, else None (native/mover). Recovers the finest
    reliable pitch (ties -> larger pad), re-derives the CENTRED origin (engine mapping), and commits ONLY if
    the tiling is NEAR-LOSSLESS (>= fidelity_min). Default 0.98 is calibrated so a mover like ls20 (best
    spurious tiling 0.946) is rejected as native and a truly solid-celled click board (~1.0) passes."""
    f = np.asarray(frame)
    if f.ndim != 2:
        return None
    H, W = f.shape
    cands = [g for g in (_axis_geom(f, 0), _axis_geom(f, 1)) if g is not None]
    if not cands:
        return None
    pitch, _, N = min(cands, key=lambda g: (g[0], -g[1]))     # finest pitch, then larger pad
    if pitch <= 1 or N < 3 or N > 40:
        return None
    pad = (H - N * pitch) // 2                                # centred pad (matches engine rendering)
    if pad < 0:
        return None
    if fidelity(f, pitch, pad, N) < fidelity_min:            # not near-lossless -> native, stay full-res
        return None
    return GridSpec(pitch_r=pitch, pitch_c=pitch, origin_r=pad, origin_c=pad,
                    n_r=N, n_c=N, H=int(H), W=int(W))
