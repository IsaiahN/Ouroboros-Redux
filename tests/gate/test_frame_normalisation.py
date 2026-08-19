"""THE NORMALISER MUST RETURN A GRID, WHATEVER THE PAYLOAD CARRIED.

FOUND IN THE BANKED EVIDENCE, NOT IN THE CODE (2026-08-18). Every `levelup_frames`
record at level > 1 -- the three records the whole link-3 finding rests on -- has
`pre` as a 64x64 grid and `post` as a **3x64x64 stack**. The crossing's
pre-observation carried one frame; its post-observation carried three.

THE MECHANISM: `_get_frame_array` unwrapped `[ndarray] -> ndarray` **only when
`len(data) == 1`**. A multi-frame step fell through to `np.array(data)` and produced
(3, 64, 64) where every caller expects (64, 64).

WHY NO SWEEP CAUGHT IT: `tools/norm_sweep.py` is a CALL-SITE instrument, and both
sides of the crossing call the SAME helper -- so it correctly reported all three
candidates clean. **The asymmetry is inside the normaliser and conditional on the
payload.** A call-site sweep is structurally blind to that, which is worth keeping
in view whenever norm_sweep is cited.

R4, BOTH WAYS:
  KNOWN-POSITIVE  a 3-frame payload must come back 2-D (this is the defect).
  KNOWN-NEGATIVE  a 1-frame payload must be BYTE-FOR-BYTE what it always was --
                  the fix must not disturb the case that already worked, since
                  every other caller of this helper depends on it.
"""
from __future__ import annotations

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from cognitive_game_player import CognitiveGamePlayer  # noqa: E402

_norm = CognitiveGamePlayer._get_frame_array


class _Obs:
    def __init__(self, frame):
        self.frame = frame


def _grid(fill):
    return np.full((64, 64), fill, dtype=np.uint8)


def test_known_positive_multi_frame_payload_normalises_to_a_grid():
    """THE DEFECT. A 3-frame stack must not reach a caller as (3, 64, 64)."""
    stack = [_grid(1), _grid(2), _grid(3)]
    out = _norm(_Obs(stack))
    assert out is not None
    assert out.ndim == 2, f"multi-frame payload came back {out.shape}, not a grid"
    assert out.shape == (64, 64)
    # THE LAST frame is the current state: a stack is ordered oldest -> newest.
    assert int(out[0][0]) == 3, "took the wrong frame from the stack"


def test_known_negative_single_frame_payload_is_unchanged():
    """The case that already worked must be untouched -- every other caller of this
    helper depends on it, so a fix that perturbs it is worse than the defect."""
    one = _grid(7)
    assert np.array_equal(_norm(_Obs([one])), one)
    assert _norm(_Obs([one])).shape == (64, 64)
    # a bare ndarray, not wrapped
    assert np.array_equal(_norm(_Obs(one)), one)
    # and the empty/None contracts
    assert _norm(None) is None
    assert _norm(_Obs([])) is not None or True  # empty list must not raise


def test_nested_list_payloads_follow_the_same_rule():
    """Raw JSON-ish payloads (lists, not ndarrays) must normalise identically, or the
    two paths drift and the defect returns through the other door."""
    stack = [[[1] * 64 for _ in range(64)] for _ in range(3)]
    out = _norm(_Obs(stack))
    assert out.ndim == 2 and out.shape == (64, 64)

    single = [[5] * 64 for _ in range(64)]
    out1 = _norm(_Obs(single))
    assert out1.ndim == 2 and out1.shape == (64, 64)
    assert int(out1[0][0]) == 5


def test_the_banked_evidence_shape_contract():
    """What the defect actually cost: pre and post must be COMMENSURABLE. A predicate
    comparing a 64x64 grid to a 3x64x64 stack is comparing incommensurable things,
    which is the mechanical reason a region vocabulary can yield exactly zero."""
    pre = _norm(_Obs([_grid(1)]))                          # 1-frame observation
    post = _norm(_Obs([_grid(1), _grid(2), _grid(3)]))     # 3-frame observation
    assert pre.shape == post.shape, (
        f"pre {pre.shape} and post {post.shape} are not comparable")
