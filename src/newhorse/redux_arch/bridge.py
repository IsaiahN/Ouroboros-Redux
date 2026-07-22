"""
bridge.py -- redux-arch P4 (step 1): the PERCEPTION -> CONTEXT bridge that wires the minter to LIVE frames.

The minter (P2) eats `(Context, outcome)` exceptions; the loop produces frames. This bridge builds a before-state
`Context` each step from the agency's perception -- focus = the cursor cell, target = a salient landmark cell,
action_vec = the cursor's learned per-action displacement (a before-state fact) -- and labels the step by whether
it made PROGRESS toward the target (the residual the base grammar, which has no rule for this game, mispredicts).
It plugs into `ArchLoop.mint_seam`, so the offline core now runs on real perception.

Faithful to the docs' worked example: on a game whose win is "move toward the target", the predicate that
compresses the progress-residual is ACTS_TOWARD -- i.e. the loop re-derives MOVE_TOWARD from its own residual.
(On a game whose win needs a relation NOT in the DSL, this same bridge surfaces the incompressible residual that
triggers a genuinely NEW mint -- the P4 curriculum-break experiment. That step needs LAW-0 game selection first.)
"""
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np
from scipy import ndimage
from .dsl import Context
from .minting import MintingEngine


def _largest_cell(frame: np.ndarray, colour: int, stride: int) -> Optional[Tuple[int, int]]:
    """Logical cell of the largest connected component of `colour` (None if absent)."""
    m = np.asarray(frame) == colour
    if not m.any():
        return None
    lab, k = ndimage.label(m)
    if k == 0:
        return None
    sizes = ndimage.sum(m, lab, range(1, k + 1))
    i = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lab == i)
    s = max(1, stride)
    return (int(round(ys.mean() / s)), int(round(xs.mean() / s)))


class LiveMintBridge:
    """A callable for `ArchLoop.mint_seam`: turns each live (before, action, after) into a minter exception."""

    def __init__(self, engine: MintingEngine, target_colour: Optional[int] = None):
        self.engine = engine
        self.target_colour = target_colour               # None -> pick a salient STATIC landmark from the loop

    def _target(self, loop, before: np.ndarray, stride: int) -> Optional[Tuple[int, int]]:
        col = self.target_colour
        if col is None:                                  # prefer a fixed distinct landmark (brick-23 salience)
            stat = loop.core._static_colours()
            cc = loop.core.agency.cursor_colour()
            cands = [c for c in stat if c != cc and c != loop.bg] if hasattr(loop, "bg") else list(stat)
            col = next(iter(sorted(cands)), None)
        if col is None:
            return None
        return _largest_cell(before, col, stride)

    def __call__(self, loop, before: np.ndarray, action: str, after: np.ndarray) -> None:
        core = loop.core
        cc = core.agency.cursor_colour()
        if cc is None:
            return
        stride = core.agency.stride() or 1
        focus_b = core._cursor_cell_in(before, stride)
        focus_a = core._cursor_cell_in(after, stride)
        target = self._target(loop, before, stride)
        if focus_b is None or focus_a is None or target is None:
            return
        vec = core.agency.predict(action) or (0, 0)
        avec = (int(round(vec[0] / stride)), int(round(vec[1] / stride)))   # action displacement in CELL units
        ctx = Context(focus_rc=focus_b, focus_colour=int(cc), target_rc=target, action_vec=avec)
        d_before = abs(focus_b[0] - target[0]) + abs(focus_b[1] - target[1])
        d_after = abs(focus_a[0] - target[0]) + abs(focus_a[1] - target[1])
        outcome = d_after < d_before                     # PROGRESS toward the target -> the label the grammar missed
        self.engine.observe(ctx, outcome)
        self.engine.maybe_mint()


def _px_centroid(frame: np.ndarray, colour: int):
    m = np.asarray(frame) == colour
    if not m.any():
        return None
    lab, k = ndimage.label(m)
    if k == 0:
        return None
    sizes = ndimage.sum(m, lab, range(1, k + 1))
    i = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lab == i)
    return (float(ys.mean()), float(xs.mean()))


class AffordanceMintBridge:
    """P4 (novel-aim): label the residual by the GRAMMAR's own prediction error -- Γ predicts 'the cursor shifts
    by its action vector'; the residual is WHERE THAT FAILS (a blocked move). The predictor of that is NOT
    navigation (ACTS_TOWARD) but AFFORDANCE -- what occupies the cell the cursor would enter. This bridge fills
    `intended_free`/`intended_colour` (before-state facts) and labels each step by whether the cursor actually
    MOVED as predicted. The minter then invents an OCCUPANCY predicate -- a kind the navigation kernel lacked,
    minted from the prediction-error residual, not re-derived."""

    def __init__(self, engine: MintingEngine):
        self.engine = engine

    def __call__(self, loop, before: np.ndarray, action: str, after: np.ndarray) -> None:
        core = loop.core
        cc = core.agency.cursor_colour()
        if cc is None:
            return
        vec = core.agency.predict(action)
        if not vec or vec == (0, 0):
            return                                       # Γ predicts no move -> nothing to be right/wrong about
        stride = core.agency.stride() or 1
        cur = _px_centroid(before, cc)
        if cur is None:
            return
        ir, ic = int(round(cur[0] + vec[0])), int(round(cur[1] + vec[1]))   # the cell the cursor would ENTER (px)
        h, w = np.asarray(before).shape
        if 0 <= ir < h and 0 <= ic < w:
            icol = int(np.asarray(before)[ir, ic])
            intended_free = (icol == core.bg)
        else:
            icol, intended_free = -1, False              # off-board edge -> blocked
        fb = core._cursor_cell_in(before, stride)
        fa = core._cursor_cell_in(after, stride)
        tgt = fb                                          # target unused for the affordance label; keep a valid cell
        if fb is None or fa is None:
            return
        avec = (int(round(vec[0] / stride)), int(round(vec[1] / stride)))
        ctx = Context(focus_rc=fb, focus_colour=int(cc), target_rc=tgt, action_vec=avec,
                      intended_free=bool(intended_free), intended_colour=(icol if icol >= 0 else None))
        moved = fa != fb                                 # did the predicted move actually happen? (else: blocked)
        self.engine.observe(ctx, moved)
        self.engine.maybe_mint()
