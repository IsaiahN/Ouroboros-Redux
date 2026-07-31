"""The BOARD-RESPONSE organ: does the board ANSWER what the agent does, and if not, change the intervention.

Why this exists (found by SIGHT, not by a proxy -- see claude/DESIGN_see_before_proxy.md). Rendering real runs on four
zero-win games showed the same pathology every time: after warmup the agent locks onto ONE action and presses it for the
whole budget, while the puzzle sits FROZEN. On one game the entire available action set was {A5, A6, A7} -- no cursor to
drive at all -- and the agent spent every step on A5 while the click modality sat untouched.

The Tether reading. R_τ is the transition residual |Γ(b,a) − o'|. An action that leaves the board unchanged is predicted
perfectly by "nothing happens": R_τ = 0. Zero residual is zero gradient -- nothing to correct, nothing to mint, nothing
to transfer. Repeating a null intervention is the dual of the residual duty in Fig 2: where the duty says *refuse the
proxy that talks when the real metric is mute*, its dual says **refuse the intervention that says nothing**. An agent
that keeps acting while the ground stays silent is not exploring; it is drifting coherently at the action layer.

Two pieces, both general (no game id, no per-game pixel calibration):
  * `monotone_band_mask` -- a budget/timer BAR is an edge-flush thin band whose filled extent only ever GROWS. It ticks
    every step no matter what the agent does, so any raw change signal counts it and reports a responsive board when the
    puzzle is frozen. It is the proxy that talks. Mask it before measuring anything.
  * `EngagementMeter` -- per-action board response on the masked board, a FROZEN test over a window, and an ESCALATION
    that hands back an available action the agent has never tried. Escalation fires only when nothing tried is
    answering, so it cannot preempt a working plan.
"""
from typing import Dict, List, Optional
import os
import numpy as np

# ★ THE CONTROL-ARM SWITCH, AND THE ONLY REASON IT EXISTS. "clear" is the shipped wiring (the frame history the band
# mask is computed from is DROPPED when the level restarts); "keep" is the pre-2026-07-31 wiring (history carried
# across the restart). Two arms at the SAME commit are what separate the intervention from the counters added to
# measure it -- without that, the beat would be two changes and one number. The agent never reads this; only
# `EngagementMeter.note_restart` does, once per restart.
#
# Why the default moved. `monotone_band_mask` requires the band's filled count to be NON-DECREASING across the whole
# retained history. A restart REFILLS the timer bar -- the count falls -- so for up to `keep` frames after every
# restart no band qualifies and the bar's own tick is charged as board response. That is the proxy that talks,
# admitted through the back door by a history that outlives the episode it described.
MASK_ON_RESTART = (os.environ.get("NEWHORSE_MASK_RESET") or "clear").strip().lower()

# A change smaller than this many cells is a cursor blink / heartbeat, not a state change. It is a general smallness
# floor applied identically to every board (a 64x64 board is ~4096 cells); it is NOT fit to any game's pixels.
#
# What the floor costs, stated plainly: a genuine state change of one to three cells reads as null, so a modality whose
# only effect is that small can be wrongly condemned. The alternative criterion -- count a change when the board reaches
# a state it has never been in -- catches those, but calls a small ticking counter anywhere on the board 'responsive'
# forever. Between the two errors, Fig 2 decides: a false READ of responsiveness is the proxy that talks while the
# ground is mute, and refusing it matters more than catching every faint answer. Magnitude, conservatively.
MIN_CELLS = 4


def monotone_band_mask(frames: List[np.ndarray], max_thick: int = 3, min_frames: int = 5,
                       min_fill: float = 0.25) -> np.ndarray:
    """Cells belonging to a MONOTONE EDGE BAND -- a budget/timer bar. Tested structurally: a band flush with one board
    edge, at most `max_thick` cells thick, whose count of cells differing from the first frame is NON-DECREASING across
    the run and ends covering at least `min_fill` of the band. A ratchet on the boundary is a budget readout, not the
    puzzle. The fill requirement is what stops a band from qualifying merely because it CLIPS a bar running along the
    perpendicular edge, and only the THINNEST qualifying band per edge is masked, so a real bar never eats puzzle rows.
    Returns an all-False mask when there is not enough history to tell -- it never masks on a guess."""
    if not frames:
        return np.zeros((1, 1), dtype=bool)
    base = frames[0]
    mask = np.zeros(base.shape, dtype=bool)
    if len(frames) < min_frames or any(f.shape != base.shape for f in frames):
        return mask
    H, W = base.shape
    stack = np.stack(frames)
    for edge in ("top", "bottom", "left", "right"):
        for t in range(1, max_thick + 1):
            if t >= min(H, W):
                break
            band = np.zeros((H, W), dtype=bool)
            if edge == "top":
                band[:t, :] = True
            elif edge == "bottom":
                band[H - t:, :] = True
            elif edge == "left":
                band[:, :t] = True
            else:
                band[:, W - t:] = True
            size = int(band.sum())
            filled = [(int(((f != base) & band).sum())) for f in stack]
            if filled[-1] < max(2, min_fill * size):
                continue
            if all(filled[i] <= filled[i + 1] for i in range(len(filled) - 1)):   # a ratchet: only ever grows
                mask |= band
                break                                     # thinnest qualifying band for this edge; do not thicken
    return mask


class _Resp:
    __slots__ = ("n", "total", "best")

    def __init__(self) -> None:
        self.n = 0
        self.total = 0.0
        self.best = 0.0


class EngagementMeter:
    """How much the board ANSWERS each action, with budget/timer bands masked out.

    `observe(grid, label)` is fed the freshly observed frame and the action that produced it. `frozen()` says the board
    has not meaningfully answered anything over the recent window. `escalate(labels)` returns an available action the
    agent has not yet tried -- the modality switch -- and only when frozen, so a plan that is working is never disturbed.
    """

    def __init__(self, window: int = 12, min_obs: int = 2, keep: int = 48, min_cells: int = MIN_CELLS) -> None:
        self.window = int(window)
        self.min_obs = int(min_obs)
        self.keep = int(keep)
        self.min_cells = int(min_cells)
        self._frames: List[np.ndarray] = []
        self._resp: Dict[str, _Resp] = {}
        self._recent: List[int] = []            # masked changed-cell count per recent step
        self._mask: Optional[np.ndarray] = None
        self.n_steps = 0

    # ---- observation ---------------------------------------------------------------------------------------------
    def observe(self, grid, label: Optional[str]) -> None:
        g = np.asarray(grid)
        prev = self._frames[-1] if self._frames else None
        self._frames.append(g)
        if len(self._frames) > self.keep:
            self._frames.pop(0)
        self._mask = None                        # history changed -> the band mask is stale
        if prev is None or prev.shape != g.shape or label in (None, "RESET", "?"):
            return
        m = self.mask()
        changed = int(((prev != g) & ~m).sum())
        e = self._resp.setdefault(str(label), _Resp())
        e.n += 1
        e.total += float(changed)
        e.best = max(e.best, float(changed))
        self._recent.append(changed)
        if len(self._recent) > self.window:
            self._recent.pop(0)
        self.n_steps += 1

    def note_restart(self) -> None:
        """The level restarted: DROP the frame history the band mask is computed from, and nothing else.

        What this fixes. The mask's qualifying test is a RATCHET -- the band's filled count must never fall across the
        retained history. A restart refills the timer bar, so the count falls, so no band qualifies for up to `keep`
        frames afterwards and every step in that stretch has the bar's own tick counted as the board ANSWERING the
        agent. The history describes an episode that has ended; carrying it into the next one is what blinds the mask.

        What this deliberately does NOT clear. `_resp` (per-action response) and `_recent` (the frozen-test window) are
        the agent's evidence about which modality is live, and a restart is not evidence that a dead modality woke up.
        Clearing them would delay `frozen()` by a full window after every death -- a SECOND change, and one nothing has
        measured. One change per arm.

        `NEWHORSE_MASK_RESET=keep` makes this a no-op, restoring the pre-2026-07-31 behaviour EXACTLY."""
        if MASK_ON_RESTART == "keep":
            return
        self._frames = []
        self._mask = None

    def mask(self) -> np.ndarray:
        if not self._frames:                     # only reachable between a restart and the first frame after it
            return np.zeros((1, 1), dtype=bool)
        if self._mask is None or self._mask.shape != self._frames[-1].shape:
            self._mask = monotone_band_mask(self._frames)
        return self._mask

    # ---- readings ------------------------------------------------------------------------------------------------
    def mean(self, label: str) -> float:
        e = self._resp.get(str(label))
        return 0.0 if e is None or e.n == 0 else e.total / e.n

    def observations(self, label: str) -> int:
        e = self._resp.get(str(label))
        return 0 if e is None else e.n

    def best(self, label: str) -> float:
        e = self._resp.get(str(label))
        return 0.0 if e is None else e.best

    def is_null(self, label: str) -> bool:
        """This action has been tried enough times and the board has NEVER meaningfully answered it (R_τ ≡ 0).

        Judged on the action's BEST response, not its mean. One real answer proves the modality is live even if most
        attempts miss -- a click that lands off the workspace tells us about the aim, not about the modality. Averaging
        would let a live modality be declared dead by its own misses and hand the game back to an inert one."""
        return self.observations(label) >= self.min_obs and self.best(label) < self.min_cells

    def failed_trial(self, label: str) -> bool:
        """A FAIR verdict on a modality the agent ESCALATED to: it has now had at least as many probes as the window
        that condemned the modality it replaced, and it never once moved the board. Equal evidence before a verdict.
        `is_null` is too impatient for this job -- a click carries a coordinate, so a couple of misses say something
        about the aim and nothing about the modality."""
        return self.observations(label) >= self.window and self.best(label) < self.min_cells

    def answered(self, label: str) -> bool:
        """This action has moved the board at least once -- the modality is live, whatever its hit rate."""
        return self.best(label) >= self.min_cells

    def frozen(self) -> bool:
        """Nothing the agent did across a full recent window moved the board (outside the budget band)."""
        return len(self._recent) >= self.window and max(self._recent) < self.min_cells

    def responsive_fraction(self) -> float:
        if not self._recent:
            return 0.0
        return sum(1 for c in self._recent if c >= self.min_cells) / float(len(self._recent))

    # ---- the readout ---------------------------------------------------------------------------------------------
    def report(self) -> Dict[str, object]:
        """Everything this organ ALREADY holds, printed. It held all of it from the day it shipped and no receipt
        ever showed a single field, so an organ built to detect a frozen board could be silent on a game the agent
        never moved and nothing would say so. This method computes NOTHING new -- it is a readout, not a measurement,
        which is why it can be added while the detector taxonomy is frozen.

        Two fields carry a caveat that must travel with them. `band_cells` is the mask AS OF THE LAST OBSERVED
        FRAME, recomputed from a sliding window of the most recent `keep` frames: it is not evidence about the mask
        that priced step 7, and a run whose restart REFILLS the timer bar breaks the non-decreasing ratchet the mask
        requires, so a game that plainly has a bar can report `band_cells=0` here. The per-step record of whether a
        band was masked lives in `ChainLedger.board_band`, charged at the step. `recent_window` is the tail only."""
        m = self.mask() if self._frames else None
        return {
            "n_steps": int(self.n_steps),
            "labels": {k: {"n": int(v.n), "mean": (v.total / v.n) if v.n else 0.0, "best": float(v.best)}
                       for k, v in sorted(self._resp.items())},
            "frozen": bool(self.frozen()),
            "responsive_fraction": float(self.responsive_fraction()),
            "recent_window": [int(c) for c in self._recent],
            "band_cells": int(m.sum()) if m is not None else None,
            "board_cells": int(m.size) if m is not None else None,
            "min_cells": int(self.min_cells),
            "window": int(self.window),
        }

    # ---- the lever -----------------------------------------------------------------------------------------------
    def escalate(self, labels: List[str]) -> Optional[str]:
        """When the board is FROZEN under everything tried, hand back the least-observed AVAILABLE action -- switch
        modality rather than keep issuing a null intervention. Returns None if the board is answering, or if every
        available action has already been tried and found null (there is no modality left to escalate to; that stall is
        real and must be reported, not papered over)."""
        if not self.frozen():
            return None
        untried = [l for l in labels if self.observations(l) < self.min_obs]
        if not untried:
            return None
        return min(untried, key=lambda l: (self.observations(l), l))
