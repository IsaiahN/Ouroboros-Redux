"""
bounds.py -- THE MAP §VIII / the Constitution: the HARD BOUNDS, enforced at IMPORT.

These are not tunable dials. They are constitutional: the moment this module loads, the bounds hold,
and there is NO parameter, flag, or setter anywhere that turns them off. A dial can be turned; a bound
cannot. The two hard bounds the whole project turns on:

  * RESET is BANNED in active play -- a reset credit is EARNED only by genuine progress (a level
    completed), never by a mere failed attempt. (This is the exact rule the Redux harness once
    violated by force-RESETting on GAME_OVER to farm ~18 unearned attempts.)
  * NEVER DOWNSAMPLE the grid -- a symbolic glyph is exact; once the canonical full-resolution shape
    is admitted, no smaller frame may enter. (perception.check_no_downsampling is the primitive; here
    it becomes a standing bound on the loop's mandatory perceive path.)

FMap grounding: lambda_calculus (d=0.171, nearest of the 46). Its lesson for unbypassable enforcement:
in the pure calculus an illegal state is not rejected at runtime -- it is simply NOT CONSTRUCTIBLE in
the grammar. So we enforce by construction: the forbidden operation cannot be EXPRESSED against these
objects (no `allow_reset=True`, no `disable` argument -- such a parameter would be a free variable the
caller could bind to escape the bound). Its classic FAILURE MODE is variable capture / unhygienic
substitution -- a bound name silently rebound. The analog bypass is a guard stored as a mutable public
flag that the agent's own code monkeypatches or shadows. GUARDS: (1) no public disable path exists;
(2) the check lives on the MANDATORY path (perceive / the reset call), not on an optional toggle;
(3) the module runs a CONSTITUTIONAL SELF-CHECK at import and refuses to load (ImportError) if either
bound fails to hold -- you cannot even import a broken constitution.

Nothing silent: every earn, every ban, every admitted canonical shape is logged.
"""
from __future__ import annotations
from typing import List, Optional, Tuple
import numpy as np
from .perception import check_no_downsampling, DownsampleError  # the no-downsample primitive


class ResetForbidden(RuntimeError):
    """Raised when a RESET is requested in active play without an earned credit. The ban, made loud."""


class ResetGate:
    """RESET is banned in active play; a credit is EARNED only by a genuinely completed level.

    Deliberately takes NO constructor arguments: there is no `allow`, `bypass`, or `disable` to bind.
    The only way to permit a reset is to have earned it -- the bound cannot be dialed down."""

    def __init__(self):
        self._credits = 0                 # earned, unspent reset credits (starts at ZERO -- nothing is owed)
        self.log: List[str] = []

    def earn(self, *, level_completed: bool, reason: str = "") -> bool:
        """Mint a reset credit -- ONLY on genuine progress. A failed attempt earns nothing (that was the
        Redux bug). Returns True iff a credit was minted."""
        if not level_completed:
            self.log.append("EARN-DENIED  no level completed -> zero credit (%s)" % reason)
            return False
        self._credits += 1
        self.log.append("EARN  +1 reset credit (now %d): %s" % (self._credits, reason))
        return True

    def permitted(self) -> bool:
        """Is a reset currently allowed? Only if a credit has been earned and not yet spent."""
        return self._credits > 0

    def request_reset(self, *, reason: str = "") -> None:
        """Consume one earned credit to permit ONE reset. If none earned -> RESET IS BANNED: raise."""
        if self._credits <= 0:
            self.log.append("RESET-BANNED  no earned credit -> refused (%s)" % reason)
            raise ResetForbidden("RESET banned in active play; none earned (%s)" % reason)
        self._credits -= 1
        self.log.append("RESET-PERMITTED  spent 1 credit (now %d): %s" % (self._credits, reason))

    @property
    def credits(self) -> int:
        return self._credits


class ResolutionBound:
    """The full-resolution grid is inviolable. Once the first frame sets the canonical shape, no admitted
    frame may have fewer rows or columns. No downsampling, ever. Takes NO argument that relaxes it."""

    def __init__(self):
        self._canonical: Optional[Tuple[int, int]] = None
        self.log: List[str] = []

    def admit(self, grid: np.ndarray) -> np.ndarray:
        """Pass a frame through the bound (returns it unchanged so it sits inline on the perceive path).
        Raises DownsampleError if the frame is smaller than the canonical full-resolution shape."""
        shape = np.asarray(grid).shape
        if len(shape) != 2:
            raise ValueError("a frame must be a 2-D full-resolution grid; got shape %s" % (shape,))
        if self._canonical is None:
            self._canonical = (int(shape[0]), int(shape[1]))
            self.log.append("BOUND  canonical full-resolution set = %s" % (self._canonical,))
        else:
            check_no_downsampling(self._canonical, shape)   # raises DownsampleError if shrunk
            self.log.append("ADMIT  %s ok (canonical %s -- not downsampled)" % (tuple(shape), self._canonical))
        return grid

    @property
    def canonical(self) -> Optional[Tuple[int, int]]:
        return self._canonical


# --- HARD BOUNDS, named (documentation is not enforcement, but silence is worse) ---------------------
HARD_BOUNDS = (
    "RESET is banned in active play; a reset credit is earned only by a completed level.",
    "The grid is never downsampled; a symbolic glyph is exact and admitted at full resolution.",
)


def verify_constitution() -> bool:
    """The import-time SELF-CHECK: prove both bounds actually hold on a fresh instance. Used by the
    module load below to REFUSE to import a broken constitution. Also callable in tests."""
    # (1) a fresh reset gate must BAN reset (nothing is owed at birth)
    g = ResetGate()
    if g.permitted():
        return False
    try:
        g.request_reset(reason="constitution self-check")
        return False                      # it permitted an unearned reset -> constitution broken
    except ResetForbidden:
        pass
    # a failed attempt must earn NOTHING; a completed level must earn exactly the right to ONE reset
    if g.earn(level_completed=False, reason="self-check attempt") or g.permitted():
        return False
    if not g.earn(level_completed=True, reason="self-check completion") or not g.permitted():
        return False
    g.request_reset(reason="self-check spend")
    if g.permitted():                     # one credit must buy exactly one reset
        return False
    # (2) a fresh resolution bound must REJECT a downsample
    rb = ResolutionBound()
    rb.admit(np.zeros((4, 4), dtype=int))
    try:
        rb.admit(np.zeros((2, 2), dtype=int))
        return False                      # it admitted a shrunk frame -> constitution broken
    except DownsampleError:
        pass
    return True


# ENFORCED AT IMPORT: you cannot even load a broken constitution.
CONSTITUTION_VERIFIED = verify_constitution()
if not CONSTITUTION_VERIFIED:
    raise ImportError("HARD BOUNDS failed their constitutional self-check -- refusing to load bounds.py")
