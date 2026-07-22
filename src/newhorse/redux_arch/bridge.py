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
from dataclasses import dataclass, field, replace
from collections import Counter
from typing import Optional, Tuple, FrozenSet
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


def _smallest_mover(before: np.ndarray, after: np.ndarray) -> Optional[int]:
    """The SMALL colour that TRANSLATED between the two frames -- i.e. the cursor sprite, not a large scrolling
    region. A colour is a 'mover' if it both appeared and vanished somewhere (a shift, not a grow); among movers
    we take the one with the smallest TOTAL footprint. Ranking by footprint (not by moved-pixel count) is what
    breaks the cursor/floor symmetry: when the cursor steps off a cell, that cell flips back to floor, so the
    FLOOR colour also 'appears and vanishes' with the same moved-pixel count -- but the floor is a large region
    and the cursor is a few pixels. This also stops the tu93 misID where the largest component of a colour is the
    whole background rather than the little dot that actually moves."""
    b = np.asarray(before); a = np.asarray(after)
    best_c, best_sz = None, None
    for c in sorted(set(int(v) for v in np.unique(b)) | set(int(v) for v in np.unique(a))):
        appeared = int(((a == c) & ~(b == c)).sum())
        vanished = int(((b == c) & ~(a == c)).sum())
        if appeared == 0 or vanished == 0:
            continue                                     # static, or grew/shrank -- not a rigid translation
        footprint = int((b == c).sum())                  # total pixels of this colour (cursor << floor << bg)
        if best_sz is None or footprint < best_sz:
            best_sz, best_c = footprint, c
    return best_c


@dataclass
class CursorLocator:
    """Identify the cursor colour by MOTION over a warmup window (the smallest thing that keeps translating),
    then FREEZE it. Robust where the agency's largest-component heuristic locks onto a big static region."""
    warmup: int = 20
    _votes: Counter = field(default_factory=Counter)
    _steps: int = 0
    _frozen: Optional[int] = None

    def observe(self, before: np.ndarray, after: np.ndarray) -> None:
        self._steps += 1
        c = _smallest_mover(before, after)
        if c is not None:
            self._votes[c] += 1

    def cursor(self) -> Optional[int]:
        if self._frozen is None and self._steps >= self.warmup and self._votes:
            self._frozen = self._votes.most_common(1)[0][0]
        return self._frozen


@dataclass
class PassabilityCalibrator:
    """Leak-FREE passable-colour read: the floor colours are the ones the cursor's OWN trajectory stepped ONTO
    (the before-state colour of a cell it successfully entered), tallied over a warmup window and then FROZEN.
    This is a structural fact about the maze, learned from the agent's motion history -- NOT `core.bg` (which was
    wrong for tu93) and NOT the move/blocked label being predicted (calibration and minting run on DISJOINT
    steps: we freeze after warmup, then mint on held-out steps). A colour must be entered >= min_hits times to
    count (single-pixel noise guard). The minted φ still predicts a held-out step -> a regularity, not a peek."""
    warmup: int = 30
    min_hits: int = 2
    _hits: Counter = field(default_factory=Counter)
    _steps: int = 0
    _frozen: Optional[FrozenSet[int]] = None

    def observe(self, entered_colour: Optional[int], moved: bool) -> None:
        self._steps += 1
        if moved and entered_colour is not None and entered_colour >= 0:
            self._hits[int(entered_colour)] += 1         # a cell the cursor SUCCEEDED in entering -> floor

    @property
    def calibrating(self) -> bool:
        return self._steps < self.warmup

    def passable_set(self) -> FrozenSet[int]:
        if self._frozen is None and not self.calibrating:
            self._frozen = frozenset(c for c, n in self._hits.items() if n >= self.min_hits)
        return self._frozen if self._frozen is not None else frozenset()

    def is_free(self, colour: Optional[int]) -> Optional[bool]:
        ps = self.passable_set()
        if not ps or colour is None:
            return None                                  # unknown until calibrated / for off-board
        return int(colour) in ps


def affordance_step(before: np.ndarray, after: np.ndarray, cursor_colour: int, vec: Tuple[int, int],
                    stride: int = 1, passable: Optional[FrozenSet[int]] = None,
                    bg: Optional[int] = None) -> Optional[Tuple[Context, bool]]:
    """PURE: build one affordance exception (Context, moved) from a before/after pair. `intended_colour` is the
    before-state colour of the cell the cursor would ENTER (a before-state fact). `intended_free` is that cell
    being FLOOR: keyed off the calibrated `passable` set when given (leak-free), else legacy `bg`-equality. No
    dependence on the loop -- so the labeling logic is unit-testable in isolation."""
    cur = _px_centroid(before, cursor_colour)
    if cur is None or not vec or tuple(vec) == (0, 0):
        return None
    ir, ic = int(round(cur[0] + vec[0])), int(round(cur[1] + vec[1]))       # cell the cursor would ENTER (px)
    h, w = np.asarray(before).shape
    if 0 <= ir < h and 0 <= ic < w:
        icol = int(np.asarray(before)[ir, ic])
        if passable is not None:
            intended_free = icol in passable
        else:
            intended_free = (icol == bg) if bg is not None else False
    else:
        icol, intended_free = -1, False                  # off-board edge -> blocked
    s = max(1, stride)
    fb = (int(round(cur[0] / s)), int(round(cur[1] / s)))
    ca = _px_centroid(after, cursor_colour)
    if ca is None:
        return None
    fa = (int(round(ca[0] / s)), int(round(ca[1] / s)))
    avec = (int(round(vec[0] / s)), int(round(vec[1] / s)))
    ctx = Context(focus_rc=fb, focus_colour=int(cursor_colour), target_rc=fb, action_vec=avec,
                  intended_free=bool(intended_free), intended_colour=(icol if icol >= 0 else None))
    return ctx, (fa != fb)                               # moved iff the cursor cell actually changed


class AffordanceMintBridge:
    """P4 (novel-aim): label the residual by the GRAMMAR's own prediction error -- Γ predicts 'the cursor shifts
    by its action vector'; the residual is WHERE THAT FAILS (a blocked move). The predictor of that is NOT
    navigation (ACTS_TOWARD) but AFFORDANCE -- what occupies the cell the cursor would enter. The minter then
    invents an OCCUPANCY predicate the navigation kernel lacked, minted from the prediction-error residual.

    Two honest reads, both fixing the retracted tu93 mint (see docs/LAW0_ls20_tu93_passability.md):
    - `cursor_locator` (optional): identify the cursor by MOTION (the small mover), not the agency's
      largest-component heuristic -- the misID that made INTENDED_COLOUR==5 (grey surround) spurious.
    - `calibrator` (optional): set `intended_free` from a leak-free discovered passable set, not `core.bg`, so the
      colour-agnostic INTENDED_FREE is the clean predictor and can echo across differently-palettes mazes.
    With neither, it falls back to the legacy `core.bg` path (P4.2 behaviour)."""

    def __init__(self, engine: MintingEngine, calibrator: Optional[PassabilityCalibrator] = None,
                 cursor_locator: Optional[CursorLocator] = None):
        self.engine = engine
        self.calibrator = calibrator
        self.cursor_locator = cursor_locator

    def __call__(self, loop, before: np.ndarray, action: str, after: np.ndarray) -> None:
        core = loop.core
        if self.cursor_locator is not None:
            self.cursor_locator.observe(before, after)
            cc = self.cursor_locator.cursor()
            if cc is None:
                cc = core.agency.cursor_colour()         # still warming up the motion-based cursor id
        else:
            cc = core.agency.cursor_colour()
        if cc is None:
            return
        vec = core.agency.predict(action)
        if not vec or tuple(vec) == (0, 0):
            return                                       # Γ predicts no move -> nothing to be right/wrong about
        stride = core.agency.stride() or 1
        step = affordance_step(before, after, int(cc), tuple(vec), stride,
                               passable=None, bg=getattr(core, "bg", 0))   # provisional intended_free (legacy)
        if step is None:
            return
        ctx, moved = step
        if self.calibrator is not None:
            self.calibrator.observe(ctx.intended_colour, moved)
            if self.calibrator.calibrating:
                return                                   # warmup: freeze the passable read before minting
            free = self.calibrator.is_free(ctx.intended_colour)
            ctx = replace(ctx, intended_free=bool(free) if free is not None else False)
        self.engine.observe(ctx, moved)
        self.engine.maybe_mint()
