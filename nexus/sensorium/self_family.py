"""nexus.sensorium.self_family -- a NON-SIMULABLE family of self-hypotheses (the correction from
"Structural Limits of Intra-Family Self-Verification", folded into DESIGN §7).

The first live ls20 test refuted the keystone's single instantiation: `has_self: false` for 904
steps, because the forward model looked for ONE thing -- a rigid object that translates -- and
ls20's self does not translate (it is a growing/advancing trail; a colour depletes monotonically).
A family of four TRANSLATION-flavoured detectors would not have helped: their failure modes are
correlated, so they fail together on the same games (the paper's "manufacturing diversity within
the same organization" -- nominal diversity, one shared blind spot).

So the members here span DELIBERATELY DIFFERENT primitives, admitted by whether they fail where
the others succeed (error-decorrelation = the paper's operational non-simulability), NOT by
variety for its own sake:

  TranslationSelf  -- a rigid object that moves (mover/sprite games).      fails on: non-rigid change
  GrowthEdgeSelf   -- a region that extends at a frontier (trails, paths). fails on: non-monotone area
  ValueLatentSelf  -- a NON-SPATIAL scalar: a colour whose count changes    fails on: non-monotone count
                      monotonically (ls20's retracting colour-11 bar).
  RegionToggleSelf -- a bounded region whose cells churn/alternate.         fails on: non-periodic change

Each member predicts and is scored by RESIDUAL (prediction error) -- the environment's own
dynamics price it, never the family judging itself. The family SELECTS the best-predicting member
that has a self. THE COMPLETENESS CRITIC (the paper's §5.3 applied to perception): when EVERY
member predicts badly at once, that agreement-in-failure is the diagnostic that the family shares
a smuggled presupposition -- surface it as `self_unmodeled`, do NOT mint another correlated guess.
The ground (ARC) remains the sole verifier throughout.
"""
from __future__ import annotations
from collections import defaultdict, deque
from typing import Optional, Tuple
import numpy as np
from .forward import ForwardModel, as_grid2d, background_colour


def _counts(a: np.ndarray, ncol: int = 16) -> np.ndarray:
    if a.size == 0:
        return np.zeros(ncol, dtype=int)
    return np.bincount(a.ravel().clip(0, ncol - 1), minlength=ncol)


def _local_patch(g: np.ndarray, centroid: Tuple[int, int], w: int = 2) -> Tuple:
    if centroid is None or g.size == 0:
        return ()
    r0, c0 = centroid; h, wd = g.shape
    return tuple(int(g[r, c]) if (0 <= r < h and 0 <= c < wd) else -1
                 for r in range(r0 - w, r0 + w + 1) for c in range(c0 - w, c0 + w + 1))


class SelfHypothesis:
    """A candidate answer to 'what do I control here?'. observe() returns a residual in [0,1]
    (0 = perfectly predicted this step, 1 = explained nothing). Members are compared ONLY by this
    ground-facing residual, never by judging each other."""
    name = "base"
    def observe(self, before, action, after) -> float: return 1.0
    def has_self(self) -> bool: return False
    def self_frame(self, grid, available) -> Tuple: return ()


class TranslationSelf(SelfHypothesis):
    name = "translation"
    def __init__(self, window: int = 2):
        self.fwd = ForwardModel(); self.window = window
    def observe(self, before, action, after) -> float:
        a = as_grid2d(before); b = as_grid2d(after)
        if a.size == 0 or a.shape != b.shape:
            return 1.0
        changed = int((a != b).sum())
        self.fwd.observe(before, action, after)
        if changed == 0:
            return 1.0
        explained = 2 * len(self.fwd.self_mask())         # vacated + arrived
        return max(0.0, 1.0 - min(1.0, explained / changed))
    def has_self(self) -> bool:
        return self.fwd.has_self()
    def self_frame(self, grid, available) -> Tuple:
        g = as_grid2d(grid)
        return ("tr", _local_patch(g, self.fwd.self_centroid(), self.window))


class GrowthEdgeSelf(SelfHypothesis):
    name = "growth"
    def __init__(self, window: int = 2):
        self.window = window; self._streak = 0; self.colour = None; self.frontier = set()
    def observe(self, before, action, after) -> float:
        a = as_grid2d(before); b = as_grid2d(after)
        if a.size == 0 or a.shape != b.shape:
            self._streak = 0; return 1.0
        changed = int((a != b).sum())
        if changed == 0:
            self._streak = 0; return 1.0
        db = _counts(b) - _counts(a)
        bg = background_colour(a)
        db[bg] = -10**9                                    # background growth is not a self
        c = int(np.argmax(db))
        if db[c] <= 0:
            self._streak = 0; return 1.0
        new_cells = {(int(r), int(c2)) for r, c2 in zip(*np.where((b == c) & (a != c)))}
        res = max(0.0, 1.0 - min(1.0, len(new_cells) / changed))
        if res < 0.5:
            self._streak += 1; self.colour = c; self.frontier = new_cells
        else:
            self._streak = 0
        return res
    def has_self(self) -> bool:
        return self._streak >= 2 and bool(self.frontier)
    def self_frame(self, grid, available) -> Tuple:
        if not self.frontier:
            return ("gr", ())
        rs = [r for r, _ in self.frontier]; cs = [c for _, c in self.frontier]
        cen = (round(sum(rs) / len(rs)), round(sum(cs) / len(cs)))
        return ("gr", self.colour, _local_patch(as_grid2d(grid), cen, self.window))


class ValueLatentSelf(SelfHypothesis):
    """A NON-SPATIAL self: the controllable thing is a scalar (a colour's total count) that moves
    monotonically. This is the member ls20 needs -- colour 11 (the retracting bar) depletes each
    step. There is no self-cell to point at; the self IS the value."""
    name = "value"
    def __init__(self, K: int = 8, bucket: int = 8, alpha: float = 0.3):
        self.K = K; self.bucket = bucket; self.alpha = alpha
        self.hist = defaultdict(lambda: deque(maxlen=K))
        self.colour = None; self._n = 0
        self.act_delta = {}                               # action -> EWMA change in the tracked resource
    def observe(self, before, action, after) -> float:
        b = as_grid2d(after)
        if b.size == 0:
            return 1.0
        self._n += 1
        prev = dict(self.hist[self.colour]) if False else None
        prev_col_count = self.hist[self.colour][-1] if (self.colour is not None and self.hist[self.colour]) else None
        cts = _counts(b)
        bg = background_colour(b)                          # the background is the frame, not the self
        for col in range(len(cts)):
            self.hist[col].append(int(cts[col]))
        # attribute the resource change under THIS action, so "preserve the resource" is actionable
        if self.colour is not None and prev_col_count is not None:
            delta = float(cts[self.colour]) - float(prev_col_count)
            self.act_delta[action] = (1 - self.alpha) * self.act_delta.get(action, 0.0) + self.alpha * delta
        best_col, best_mono = None, 0.0
        for col, series in self.hist.items():
            if col == bg or len(series) < 3:
                continue
            diffs = [series[i + 1] - series[i] for i in range(len(series) - 1)]
            nz = [d for d in diffs if d != 0]
            if not nz:
                continue
            mono = abs(sum(np.sign(nz))) / len(nz)          # 1.0 = strictly monotone
            if mono > best_mono:
                best_mono, best_col = mono, col
        if best_col is not None:
            self.colour = best_col
        return max(0.0, 1.0 - best_mono)
    def has_self(self) -> bool:
        if self.colour is None or self._n < 4:
            return False
        series = self.hist[self.colour]
        if len(series) < 4:
            return False
        diffs = [series[i + 1] - series[i] for i in range(len(series) - 1)]
        nz = [d for d in diffs if d != 0]
        # a real latent value moves consistently (>=80% one direction) AND meaningfully (net travel
        # of at least one unit per nonzero step), which random count jitter does not sustain.
        if len(nz) < 3 or abs(sum(np.sign(nz))) / len(nz) < 0.8:
            return False
        return abs(series[-1] - series[0]) >= len(nz)
    def self_frame(self, grid, available) -> Tuple:
        cur = self.hist[self.colour][-1] if self.colour is not None and self.hist[self.colour] else 0
        return ("val", self.colour, cur // self.bucket)

    # ---- the resource, made actionable (for the self-composed objective) --------------------------
    def level(self) -> Optional[int]:
        return self.hist[self.colour][-1] if (self.colour is not None and self.hist[self.colour]) else None

    def trend(self) -> int:
        """+1 growing, -1 depleting, 0 flat -- the sign of the resource's recent motion."""
        if self.colour is None:
            return 0
        s = self.hist[self.colour]
        diffs = [s[i + 1] - s[i] for i in range(len(s) - 1)]
        nz = [d for d in diffs if d != 0]
        return int(np.sign(sum(nz))) if nz else 0

    def action_delta(self, action: str) -> float:
        """The learned change in the resource under an action (>0 refills, <0 depletes)."""
        return self.act_delta.get(action, 0.0)

    def action_deltas(self) -> dict:
        return {a: round(v, 3) for a, v in self.act_delta.items()}


class RegionToggleSelf(SelfHypothesis):
    """A bounded region that ALTERNATES between values -- true toggling, not mere repeated change.
    A cell toggles iff its value returns to what it was two steps ago (g[t]==g[t-2] != g[t-1]); this
    rejects random repaint, where cells change every step but never come back."""
    name = "toggle"
    def __init__(self):
        self._g1 = None; self._g2 = None; self._streak = 0; self.region = set()
    def observe(self, before, action, after) -> float:
        b = as_grid2d(after)
        if b.size == 0:
            self._streak = 0; return 1.0
        changed = None
        if self._g1 is not None and self._g1.shape == b.shape:
            changed = {(int(r), int(c)) for r, c in zip(*np.where(self._g1 != b))}
        res = 1.0
        if self._g2 is not None and self._g1 is not None and self._g2.shape == b.shape and changed:
            alt = {(r, c) for (r, c) in changed
                   if b[r, c] == self._g2[r, c] and b[r, c] != self._g1[r, c]}   # came back after one step
            res = max(0.0, 1.0 - min(1.0, len(alt) / len(changed)))
            if res < 0.5 and alt:
                self._streak += 1; self.region = alt
            else:
                self._streak = 0
        self._g2, self._g1 = self._g1, b
        return res
    def has_self(self) -> bool:
        return self._streak >= 2 and bool(self.region)
    def self_frame(self, grid, available) -> Tuple:
        if not self.region:
            return ("tg", ())
        rs = [r for r, _ in self.region]; cs = [c for _, c in self.region]
        return ("tg", (min(rs), max(rs), min(cs), max(cs)))


class SelfModelFamily:
    """Holds the non-simulable members, prices each by its ground-facing residual (EWMA), selects
    the best-predicting one that has a self, and runs the completeness critic."""
    def __init__(self, alpha: float = 0.3, unmodeled_threshold: float = 0.6):
        self.members = [TranslationSelf(), GrowthEdgeSelf(), ValueLatentSelf(), RegionToggleSelf()]
        self.alpha = alpha; self.thr = unmodeled_threshold
        self.ewma = {m.name: 1.0 for m in self.members}
        self._n = 0

    def observe(self, before, action, after) -> None:
        self._n += 1
        for m in self.members:
            r = m.observe(before, action, after)
            self.ewma[m.name] = (1 - self.alpha) * self.ewma[m.name] + self.alpha * float(r)

    def selected(self) -> Optional[SelfHypothesis]:
        cands = [m for m in self.members if m.has_self()]
        if not cands:
            return None
        return min(cands, key=lambda m: self.ewma[m.name])

    def self_unmodeled(self) -> bool:
        """The completeness critic: no member has a self, OR the best residual is still high -- the
        whole family failed together, which flags a shared smuggled presupposition to surface."""
        m = self.selected()
        if m is None:
            return True
        return self.ewma[m.name] > self.thr

    def signature(self, grid, available) -> Optional[Tuple]:
        m = self.selected()
        if m is None or self.self_unmodeled():
            return None
        return ("self", m.name) + m.self_frame(grid, available)

    def report(self) -> dict:
        m = self.selected()
        rep = {"selected": m.name if m else None,
               "self_unmodeled": self.self_unmodeled(),
               "residuals": {k: round(v, 3) for k, v in self.ewma.items()}}
        if m is not None and m.name == "value":            # surface the resource mechanics the ground taught
            rep["resource"] = {"colour": m.colour, "level": m.level(), "trend": m.trend(),
                               "action_deltas": m.action_deltas()}
        return rep
