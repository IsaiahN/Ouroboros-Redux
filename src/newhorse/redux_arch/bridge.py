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


def decision_context(before: np.ndarray, cursor_colour: int, vec: Tuple[int, int],
                     stride: int = 1, passable: Optional[FrozenSet[int]] = None,
                     bg: Optional[int] = None) -> Optional[Context]:
    """THE BEFORE-STATE CONTEXT FOR ONE CANDIDATE ACTION -- the whole of `affordance_step` except the outcome.

    ★ THIS EXISTS SO THERE IS EXACTLY ONE CONSTRUCTION. A promoted φ was fitted to contexts built by THIS rule:
    `target_rc` is the focus itself (so NEAR / TOUCH / SAME_ROW / SAME_COL are constant and inert), `intended_*`
    describe the cell the cursor would ENTER under `vec`, and `intended_free` is keyed off the CALIBRATED passable
    set rather than a background guess. If a decision site built its own context with different conventions --
    a real landmark in `target_rc`, `intended_free` defaulted True -- then φ would still evaluate and would be
    answering a DIFFERENT QUESTION than the one it was minted on, silently. A predicate asked the wrong question
    still returns a bool; that is precisely why this must not be duplicated. Both the residual site
    (`affordance_step`) and the action-selection site (`policy._gamma_directive`) call this one function.

    Returns None when the focus is not locatable or the action has no learned displacement -- the same refusals
    `affordance_step` makes, for the same reasons."""
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
    avec = (int(round(vec[0] / s)), int(round(vec[1] / s)))
    return Context(focus_rc=fb, focus_colour=int(cursor_colour), target_rc=fb, action_vec=avec,
                   intended_free=bool(intended_free), intended_colour=(icol if icol >= 0 else None))


def affordance_step(before: np.ndarray, after: np.ndarray, cursor_colour: int, vec: Tuple[int, int],
                    stride: int = 1, passable: Optional[FrozenSet[int]] = None,
                    bg: Optional[int] = None) -> Optional[Tuple[Context, bool]]:
    """PURE: build one affordance exception (Context, moved) from a before/after pair. The Context is built by
    `decision_context` -- the SAME function the action-selection site uses -- and this adds only the outcome.
    No dependence on the loop -- so the labeling logic is unit-testable in isolation."""
    ctx = decision_context(before, cursor_colour, vec, stride=stride, passable=passable, bg=bg)
    if ctx is None:
        return None
    cur = _px_centroid(before, cursor_colour)
    ca = _px_centroid(after, cursor_colour)
    if cur is None or ca is None:
        return None
    s = max(1, stride)
    fb = (int(round(cur[0] / s)), int(round(cur[1] / s)))
    fa = (int(round(ca[0] / s)), int(round(ca[1] / s)))
    return ctx, (fa != fb)                               # moved iff the cursor cell actually changed


def _entered_colour(before: np.ndarray, after: np.ndarray, cursor_colour: int) -> Optional[int]:
    """The before-state colour of the cell the cursor ACTUALLY moved into (its after-position). This is the true
    floor it stepped onto -- used to calibrate passability leak-free, unlike the projected cell-ahead which can
    overshoot into the surround near a boundary."""
    ca = _px_centroid(after, cursor_colour)
    if ca is None:
        return None
    b = np.asarray(before); h, w = b.shape
    r, c = int(round(ca[0])), int(round(ca[1]))
    return int(b[r, c]) if (0 <= r < h and 0 <= c < w) else None


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
            # CALIBRATE from the cursor's ACTUAL trajectory -- the before-state colour of the cell it truly
            # entered -- NOT the projected `intended_colour`. The projection overshoots into the surround near
            # boundaries (tu93: 4/31 moved steps projected into grey), leaking a non-floor colour into the
            # passable set; the actual-entered colour is the true floor. Prediction still uses the projection.
            entered = _entered_colour(before, after, int(cc)) if moved else None
            self.calibrator.observe(entered, moved)
            if self.calibrator.calibrating:
                return                                   # warmup: freeze the passable read before minting
            free = self.calibrator.is_free(ctx.intended_colour)
            ctx = replace(ctx, intended_free=bool(free) if free is not None else False)
        self.engine.observe(ctx, moved)
        self.engine.maybe_mint()


def transition_residual(frames, acts, focus_colour: Optional[int], vecs: Optional[dict],
                        passable=None, stride: int = 1, bg: Optional[int] = None,
                        report: Optional[dict] = None):
    """R_τ OVER A WHOLE SEGMENT: the transition residual the base grammar mispredicts, as an exception list.

    Γ's base rule is "the action displaces the focus by its learned vector". The exception list is every step where
    that rule was TESTABLE -- a learned vec exists for the action and the focus is on the board -- paired with
    whether it actually held. This is the SAME per-step labelling `affordance_step` already does; the only new thing
    is that it runs over a segment instead of one step, so a residual exists at every break event and not only at a
    level advance.

    Spec grounding (§4.3 SUPPORT): R_τ answers on EVERY step and is near-ideal; R_ρ speaks only on success and is
    near-mute. The build minted only off R_ρ, which is why the residual organ was gated behind the very outcome it
    exists to produce. This function is the R_τ stream, nothing more -- no new referent kind, no new atom, no
    detector (directive 4 stands).

    Returns None iff the residual COULD NOT BE COMPUTED (no learned focus colour, no learned vecs, no testable step)
    -- the honest DIED_PRE_DIFF. Returns a possibly-uniform list iff it RAN; a uniform list is RESIDUAL_EMPTY. The
    two must never be collapsed: "the organ never ran" and "the organ ran and found nothing" indict different layers.

    WHY THERE IS A `report` OUT-PARAM. DIED_PRE_DIFF is the largest pile on the board and this function is the ONLY
    place that knows which of four different things produced it. Returning a bare None collapses "the agent never
    learned a focus colour", "it learned no action vectors", "the segment was one frame long" and "it played a
    hundred steps and could not locate its own cursor on any of them" into a single silence -- four different
    layers wearing one code. Those are not the same failure and they do not have the same fix, so the classifier
    is recorded here, at the site that knows it, and the verdict is left to a later reader (§5.1).

    `report` is the same out-param shape `two_part_mdl(..., report=rep)` already uses. It is filled on EVERY path,
    including success, and it is REPORTING ONLY: nothing here reads it back, so this cannot change what the chain
    does. The scan counters are cumulative over the segment, so `scan_pairs == scan_no_vec + scan_unlocatable +
    len(exc)` is an identity a test can hold the instrument to.
    """
    rep = report if report is not None else {}
    rep.update(reason=None, scan_pairs=0, scan_no_vec=0, scan_unlocatable=0, n_frames=len(frames))
    if focus_colour is None:
        rep["reason"] = "no_focus_colour"                 # the agent never learned WHICH pixel is its cursor
        return None
    if not vecs:
        rep["reason"] = "no_learned_vecs"                 # it learned no action -> displacement map to be wrong about
        return None
    if len(frames) < 2:
        rep["reason"] = "segment_too_short"               # fewer than two frames: no transition exists to diff
        return None
    ps = frozenset(int(c) for c in passable) if passable else None
    exc = []
    n = min(len(frames), len(acts))
    for i in range(1, n):
        rep["scan_pairs"] += 1
        vec = vecs.get(acts[i])
        if not vec or tuple(vec) == (0, 0):
            rep["scan_no_vec"] += 1
            continue                                     # Γ predicts no displacement -> nothing to be wrong about
        step = affordance_step(frames[i - 1], frames[i], int(focus_colour), tuple(vec), stride,
                               passable=ps, bg=bg)
        if step is None:
            rep["scan_unlocatable"] += 1
            continue                                     # focus not locatable on this pair
        exc.append(step)
    if not exc:
        # It RAN and every pair was untestable. `scan_no_vec` vs `scan_unlocatable` separates "the agent kept
        # pressing actions it has no model for" from "the agent has a model but lost sight of the thing it moves",
        # which are a planner problem and a perception problem respectively.
        rep["reason"] = "no_testable_step"
        return None
    return exc


def click_residual(frames, acts, click_rc, bg: Optional[int] = None, report: Optional[dict] = None):
    """R_κ OVER A WHOLE SEGMENT: the CLICK residual. THE SECOND EVIDENCE STREAM (§5.3).

    WHY A SECOND STREAM AND NOT A WIDER R_τ. R_τ is DIRECTIONAL-ONLY by identity, not by accident: the only site in
    `policy._route` that learns a focus colour and a displacement map is the same site that commits `family =
    DIRECTIONAL`, and it is reached only AFTER both basis learners have already failed. "Widening the precondition"
    therefore means one of two things, and both are refused: lowering the bar inside `learn_basis` so a game with no
    drivable cursor reports one anyway (that is calibrating the instrument to make it read higher), or writing a new
    detector (directive 4's freeze). On a click-only game there are no directional actions AT ALL, so there is no
    action -> displacement map to be wrong about; the residual R_τ wants does not exist there in principle. §5.3 is
    explicit that a stream is a ground and grounds are assessed PER STREAM, so the honest move is a second stream.

    WHAT THE BASE RULE IS. Γ's rule for a click game is "clicking a cell does something to the board". The exception
    list is every step where that was TESTABLE -- the agent recorded WHICH cell it clicked and that cell is on the
    board -- paired with whether the board actually changed. Mixed outcomes (some clicks act, some are inert) are
    exactly what `two_part_mdl` needs to split, and the splitting predicate a click game wants -- "clicking colour c
    does something" -- is ALREADY in the DSL as HAS_COLOUR / INTENDED_COLOUR / INTENDED_FREE. That is the check that
    made this the cheap option rather than the ambitious one: NO new atom, NO new referent kind, NO new detector,
    no change to `Context`. The vocabulary already contained the right predicate.

    WHAT IS DEGENERATE AND SAID OUT LOUD. There is no displacement, so `action_vec` is (0,0) and ACTS_TOWARD is
    False on every context; there is no landmark, so `target_rc` is the clicked cell itself and NEAR / SAME_ROW /
    SAME_COL are constant. A constant atom cannot split a residual, so the MDL gate will simply never select one --
    they are inert, not forged. `intended_free` uses the MODAL colour of the before-frame as the background
    estimate; it is an estimate, it names no game, and it is only ever the input to a predicate the MDL gate still
    has to pay for.

    Returns None iff the residual COULD NOT BE COMPUTED -- the honest DIED_PRE_DIFF, with a reason in `report`,
    exactly as `transition_residual` does. `scan_pairs == scan_no_coord + scan_off_board + len(exc)` is an identity
    a test can hold the instrument to.
    """
    rep = report if report is not None else {}
    rep.update(reason=None, scan_pairs=0, scan_no_coord=0, scan_off_board=0, n_frames=len(frames))
    if not click_rc or not any(rc is not None for rc in click_rc):
        rep["reason"] = "no_click_coords"                 # nothing in this segment was a coordinate action
        return None
    if len(frames) < 2:
        rep["reason"] = "segment_too_short"
        return None
    exc = []
    n = min(len(frames), len(acts), len(click_rc))
    for i in range(1, n):
        rep["scan_pairs"] += 1
        rc = click_rc[i]
        if rc is None:
            rep["scan_no_coord"] += 1
            continue                                     # not a coordinate action -> no cell to be right about
        b = np.asarray(frames[i - 1])
        h, w = b.shape
        r, c = int(rc[0]), int(rc[1])
        if not (0 <= r < h and 0 <= c < w):
            rep["scan_off_board"] += 1
            continue
        col = int(b[r, c])
        bgc = int(bg) if bg is not None else int(np.bincount(b.ravel().astype(int)).argmax())
        ctx = Context(focus_rc=(r, c), focus_colour=col, target_rc=(r, c), action_vec=(0, 0),
                      intended_free=bool(col == bgc), intended_colour=col)
        exc.append((ctx, not np.array_equal(b, np.asarray(frames[i]))))
    if not exc:
        rep["reason"] = "no_testable_step"
        return None
    return exc
