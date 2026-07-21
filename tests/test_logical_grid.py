"""
Tests for the logical-grid quantum lens (brick 11).

Verifies: a genuinely-tiled board is detected with the right pitch/origin and cell<->pixel round-trips;
a near-lossless FIDELITY GATE rejects frames that don't cleanly tile (so a mover like ls20 stays native
and gets its stride from motion, not tiling); and -- the map's hard bound -- the lens NEVER downsamples
the working frame (it is a coordinate service, not a replacement representation).
"""
import sys, os, glob, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse import logical_grid as LG
from newhorse.logical_grid import detect_grid, GridSpec, fidelity


def _clean_board(n=5, pitch=6, pad=2):
    """A genuinely-tiled board: n×n distinct solid cells upscaled by `pitch`, centred with `pad` background."""
    side = n * pitch + 2 * pad
    f = np.zeros((side, side), dtype=int)             # pad = colour 0 (distinct from all cells)
    for i in range(n):
        for j in range(n):
            colour = (i * n + j) % 9 + 1              # 1..9, never the pad colour
            r0, c0 = pad + i * pitch, pad + j * pitch
            f[r0:r0 + pitch, c0:c0 + pitch] = colour
    return f


def test_detects_a_clean_tiled_board():
    f = _clean_board(n=5, pitch=6, pad=2)
    spec = detect_grid(f)
    assert spec is not None
    assert spec.stride == (6, 6) and spec.logical_shape == (5, 5)
    assert fidelity(f, 6, 2, 5) == 1.0                # each cell one solid colour -> lossless


def test_cell_pixel_roundtrip_and_centre():
    f = _clean_board(n=5, pitch=6, pad=2)
    spec = detect_grid(f)
    # a located click lands dead-centre on the cell, and maps back to the same cell
    for (r, c) in [(0, 0), (2, 3), (4, 4)]:
        y, x = spec.cell_to_px(r, c)
        assert f[y, x] == (r * 5 + c) % 9 + 1          # centre pixel is that cell's colour
        assert spec.px_to_cell(y, x) == (r, c)         # round-trips
    # off-board pixels clamp into the board
    assert spec.px_to_cell(-100, -100) == (0, 0)
    assert spec.px_to_cell(9999, 9999) == (4, 4)


def test_logical_read_recovers_the_board_without_touching_raw():
    f = _clean_board(n=5, pitch=6, pad=2)
    before = f.copy()
    spec = detect_grid(f)
    view = spec.logical_read(f)
    assert view.shape == (5, 5)                        # the DERIVED reasoning view is cell-space
    for i in range(5):
        for j in range(5):
            assert view[i, j] == (i * 5 + j) % 9 + 1
    assert f.shape == before.shape and np.array_equal(f, before)   # raw frame untouched (no mutation)


def test_fidelity_gate_mechanism():
    # the gate is the non-gameable arbiter (FMap arrows_impossibility): a grid is committed only if the
    # tiling is near-lossless. On a perfect board (fidelity 1.0) the gate passes at any <=1.0 threshold and
    # fails the instant the bar is raised above the achievable fidelity.
    f = _clean_board(n=5, pitch=6, pad=2)
    assert fidelity(f, 6, 2, 5) == 1.0
    assert detect_grid(f, fidelity_min=1.0) is not None      # 1.0 >= 1.0 -> commits
    assert detect_grid(f, fidelity_min=1.01) is None         # bar above achievable -> native (gate really gates)


def test_pure_noise_is_native():
    # deterministic fine (1px) structure -> no clean tiling -> None (never force a grid onto a native frame)
    f = np.fromfunction(lambda i, j: ((i * 7 + j * 13) % 5), (30, 30), dtype=int).astype(int)
    assert detect_grid(f) is None


def test_lens_never_exposes_a_frame_downsampler():
    # the map's hard bound: this module must NOT provide a function that REPLACES the working frame with a
    # reduced one. logical_read is a derived VIEW (tested above); there is no `downsample` here (Redux had one).
    assert not hasattr(LG, "downsample")


def test_ls20_real_frame_is_native_at_the_default_gate():
    # LAW 0 regression, when a recording is present: the real ls20 frame must NOT yield the game grid at the
    # near-lossless default (its true 5px grid scores 0.818; only a spurious 2px tiling passes a 0.93 gate).
    hits = glob.glob(os.path.join(os.path.dirname(__file__), "..", "recordings", "*", "*.jsonl"))
    if not hits:
        return                                          # recording not present in this checkout -> skip silently
    recs = [json.loads(l)["data"] for l in open(hits[0]).read().splitlines()]
    frame = np.array(recs[0]["frame"])[-1]
    assert detect_grid(frame, fidelity_min=0.98) is None           # native at the near-lossless default
    spurious = detect_grid(frame, fidelity_min=0.93)
    if spurious is not None:
        assert spurious.stride != (5, 5)                # whatever a loose gate finds, it is NOT the 5px game grid
