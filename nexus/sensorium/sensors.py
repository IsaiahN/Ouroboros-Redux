"""nexus.sensorium.sensors -- the minted, typed, OPEN sensorium (Stage 1 of the plan).

A sensor here is what the corpus's reduction demands: not a sensation but the INFORMATION a sense
provides, expressed as a typed function of the BEFORE-state + memory. This mirrors the kernel DSL's
discipline exactly (dsl.py `Context`): a sensor is evaluable before the outcome, so it cannot peek
-- the tautology guard is a type property, not a rule to remember. The registry is OPEN: sensors are
constructors keyed by kind, and new ones can be minted (mint.py) without editing a closed list, or we
re-smuggle the presupposition one door down (the zero-trust scrutiny).

The Sensorium's headline product is `signature(grid, available)` -- the SELF-RELATIVE, local danger
descriptor that replaces `local_signature`. The earlier ground finding
(FINDINGS_the_generalization_the_ground_refused) showed whole-board colours+available were too coarse:
survivors shared them, so the ground kept relaxing the generalization. A self-relative descriptor
fixes that at the root -- it describes the situation AROUND THE AGENT (what the self is surrounded by),
so "when surrounded like THIS, going that direction kills" generalizes across globally-different boards
while open-space boards simply do not match. It is kernel-perceived and mintable, exactly what the
finding asked for.
"""
from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np
from .forward import ForwardModel, as_grid2d, background_colour

# ---- typed sensor channels (before-state functions; open registry) --------------------------------
# Each channel: kind -> callable(read) -> hashable feature value. `read` is the SensedState below.
# Adding a channel is adding a constructor here or minting one at runtime -- never gating on a fixed set.


class SensedState:
    """The before-state read the sensors see: the grid, the available actions, and the self-model's
    current estimate of the controllable self. Everything a sensor may use, and nothing from after
    the outcome -- so no sensor built on it can cheat."""

    def __init__(self, grid, available, fwd: ForwardModel, window: int = 2):
        self.g = as_grid2d(grid)
        self.available = tuple(sorted(int(v) for v in (available or [])))
        self.bg = background_colour(self.g)
        self.fwd = fwd
        self.window = window
        self.centroid = fwd.self_centroid()

    def self_local(self) -> Tuple:
        """The multiset of colours in a small window AROUND THE SELF (self-relative vision). This is
        the sensor that makes danger perceivable as a local configuration rather than a global one."""
        if self.centroid is None or self.g.size == 0:
            return ()
        r0, c0 = self.centroid; w = self.window; h, wd = self.g.shape
        patch = []
        for r in range(r0 - w, r0 + w + 1):
            for c in range(c0 - w, c0 + w + 1):
                patch.append(int(self.g[r, c]) if (0 <= r < h and 0 <= c < wd) else -1)  # -1 = wall/edge
        return tuple(patch)

    def self_shape(self) -> Tuple:
        cells = self.fwd.self_mask()
        if not cells:
            return ()
        rs = [r for r, _ in cells]; cs = [c for _, c in cells]
        r0, c0 = min(rs), min(cs)
        return tuple(sorted((r - r0, c - c0) for r, c in cells))

    def global_colours(self) -> Tuple:
        if self.g.size == 0:
            return ()
        return tuple(sorted(int(c) for c in np.unique(self.g)))


_CHANNELS: Dict[str, Callable[[SensedState], object]] = {
    "AVAILABLE":   lambda s: s.available,            # the affordance set (which actions exist here)
    "SELF_LOCAL":  lambda s: s.self_local(),         # self-relative vision (the danger-bearing channel)
    "SELF_SHAPE":  lambda s: s.self_shape(),         # proprioceptive body shape
    "GLOBAL_COL":  lambda s: s.global_colours(),     # fallback whole-board colours (used only w/o a self)
}


def channel(kind: str, read: SensedState):
    if kind not in _CHANNELS:
        raise KeyError("unknown sensor channel %r" % kind)
    return _CHANNELS[kind](read)


def register_channel(kind: str, fn: Callable[[SensedState], object]) -> None:
    """Mint a new sensor channel at runtime (the registry stays OPEN). Used by mint.py; also the seam
    for kernel-perceived channels to migrate in once ground-validated."""
    _CHANNELS[kind] = fn


class Sensorium:
    """The persistent perceptual organ carried across a run. Wraps the forward model, feeds the sensor
    mint with ground-labelled outcomes, and emits the self-relative danger signature the verdict
    circuit generalizes over. Stateful ON PURPOSE: perceiving danger needs memory of what moved."""

    def __init__(self, window: int = 2, mint=None):
        self.fwd = ForwardModel()
        self.window = window
        self.mint = mint                                   # a SensorMint or None (set by the runner)
        self._last_before = None

    # ---- the headline product: the minted, self-relative signature --------------------------------
    def signature(self, grid, available) -> Tuple:
        """A hashable, self-relative danger descriptor for THIS board, keyed with the action by the
        circuit as (signature, action). With a self, it is the minted projection of self-relative
        features; with no self yet, it falls back to (available, global colours) -- honest, because
        without a body there is no self-relative frame to perceive danger in."""
        read = SensedState(grid, available, self.fwd, self.window)
        if not self.fwd.has_self():
            return ("nobody", read.available, read.global_colours())
        keys = self.mint.active_channels() if self.mint else None
        if not keys:
            keys = ("AVAILABLE", "SELF_LOCAL", "SELF_SHAPE")     # full self-relative read before minting sharpens it
        return ("self",) + tuple(channel(k, read) for k in keys)

    def features(self, grid, available) -> Dict[str, object]:
        """The full candidate-feature dict the mint separates fatal from survived over."""
        read = SensedState(grid, available, self.fwd, self.window)
        return {k: _CHANNELS[k](read) for k in _CHANNELS}

    # ---- learning: fold each grounded step back into perception -----------------------------------
    def observe(self, before, action: str, after, fatal: bool, available) -> None:
        """Update the self-model from the transition and, if a mint is attached, teach it whether the
        before-state's self-relative features led to death. This is the ground pricing perception:
        the danger sensor is minted from confirmed fatal/survived outcomes, never asserted."""
        self.fwd.observe(before, action, after)
        if self.mint is not None:
            feats = self.features(before, available)
            self.mint.observe(action, feats, fatal)

    def surprise(self, grid, action: str, after) -> int:
        """Active-inference signal: how badly the efference copy failed here (for empowerment)."""
        return self.fwd.surprise(grid, action, after)
