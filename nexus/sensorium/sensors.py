"""nexus.sensorium.sensors -- the minted, typed, OPEN sensorium (Stage 1 of the plan), now driven
by a NON-SIMULABLE family of self-hypotheses (DESIGN §7).

A sensor here is what the corpus's reduction demands: not a sensation but the INFORMATION a sense
provides, expressed as a typed function of the BEFORE-state + memory. This mirrors the kernel DSL's
discipline exactly (dsl.py `Context`): a sensor is evaluable before the outcome, so it cannot peek.
The registry is OPEN: sensors are constructors keyed by kind, mintable at runtime (mint.py).

The Sensorium's headline product is `signature(grid, available)` -- the SELF-RELATIVE danger
descriptor that replaces `local_signature`. The self-frame now comes from whichever member of the
self-hypothesis family best predicts THIS game's dynamics (translation / growth / value-latent /
toggle), ground-selected by residual. When the whole family fails together (`self_unmodeled`), the
signature falls back honestly and the failure is surfaced rather than papered over -- the paper's
completeness critic, not another correlated guess.
"""
from __future__ import annotations
from typing import Callable, Dict, List, Tuple
import numpy as np
from .forward import as_grid2d, background_colour
from .self_family import SelfModelFamily


class SensedState:
    """The before-state read the sensors see: the grid, the available actions, and the self-model
    family's current self-frame. Everything a sensor may use, nothing from after the outcome."""

    def __init__(self, grid, available, selfmodel: SelfModelFamily):
        self.g = as_grid2d(grid)
        self.available = tuple(sorted(int(v) for v in (available or [])))
        self.bg = background_colour(self.g)
        self.selfmodel = selfmodel

    def self_frame(self) -> Tuple:
        sel = self.selfmodel.selected()
        return sel.self_frame(self.g, self.available) if sel else ()

    def self_model_name(self) -> str:
        sel = self.selfmodel.selected()
        return sel.name if sel else "none"

    def global_colours(self) -> Tuple:
        if self.g.size == 0:
            return ()
        return tuple(sorted(int(c) for c in np.unique(self.g)))


_CHANNELS: Dict[str, Callable[[SensedState], object]] = {
    "AVAILABLE":  lambda s: s.available,            # the affordance set (which actions exist here)
    "SELF_FRAME": lambda s: s.self_frame(),         # the selected member's self-relative descriptor
    "SELF_MODEL": lambda s: s.self_model_name(),    # WHICH self-hypothesis the ground selected
    "GLOBAL_COL": lambda s: s.global_colours(),     # fallback whole-board colours
}


def channel(kind: str, read: SensedState):
    if kind not in _CHANNELS:
        raise KeyError("unknown sensor channel %r" % kind)
    return _CHANNELS[kind](read)


def register_channel(kind: str, fn: Callable[[SensedState], object]) -> None:
    """Mint a new sensor channel at runtime (the registry stays OPEN)."""
    _CHANNELS[kind] = fn


class Sensorium:
    """The persistent perceptual organ carried across a run. Wraps the self-hypothesis family, feeds
    the sensor mint with ground-labelled outcomes, and emits the self-relative danger signature the
    verdict circuit generalizes over."""

    def __init__(self, mint=None, unmodeled_threshold: float = 0.6):
        self.selfmodel = SelfModelFamily(unmodeled_threshold=unmodeled_threshold)
        self.mint = mint

    # ---- the headline product: the minted, self-relative signature --------------------------------
    def signature(self, grid, available) -> Tuple:
        """A hashable, self-relative danger descriptor for THIS board, keyed with the action by the
        circuit as (signature, action). Uses the ground-selected self member's frame; falls back to
        (available, global colours) when the family failed together (self_unmodeled)."""
        read = SensedState(grid, available, self.selfmodel)
        sig = self.selfmodel.signature(grid, available)
        if sig is None:                                   # completeness critic tripped -> honest fallback
            return ("nobody", read.available, read.global_colours())
        keys = self.mint.active_channels() if self.mint else None
        if not keys:
            return sig + (read.available,)                # full self-relative frame before minting sharpens
        return ("self",) + tuple(channel(k, read) for k in keys)

    def features(self, grid, available) -> Dict[str, object]:
        """The full candidate-feature dict the mint separates fatal from survived over."""
        read = SensedState(grid, available, self.selfmodel)
        return {k: _CHANNELS[k](read) for k in _CHANNELS}

    # ---- learning: fold each grounded step back into perception -----------------------------------
    def observe(self, before, action: str, after, fatal: bool, available) -> None:
        """Update the self-hypothesis family from the transition (the environment prices every member
        by prediction residual) and, if a mint is attached, teach it whether the before-state's
        self-relative features led to death. The ground prices perception; nothing self-verifies."""
        feats = self.features(before, available) if self.mint is not None else None
        self.selfmodel.observe(before, action, after)     # members fold the action into their own state
        if self.mint is not None:
            self.mint.observe(action, feats, fatal)

    def self_unmodeled(self) -> bool:
        return self.selfmodel.self_unmodeled()

    def report(self) -> Dict:
        return self.selfmodel.report()
