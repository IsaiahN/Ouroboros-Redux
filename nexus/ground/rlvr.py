"""nexus.ground.rlvr -- the GROUND: externally verifiable, unpersuadable, non-negotiable.

Per the Tether paper (§3, §12): a ground is a slice of observable reality the frames can only
RANGE against, never move. Here, offline, it is a hidden target predicate that LABELS a fixed
dataset of before-states; a candidate is scored by its predictive agreement with those labels.

Two properties this enforces, and a test asserts:
  * VERIFIABLE  -- the score is computed from data (balanced accuracy on the labelled sample),
                   not asserted by any frame.
  * UNPERSUADABLE -- the score is a pure function of (candidate, dataset). It does NOT depend on
                   who proposed the candidate, its credibility, or the population's opinion. A
                   frame cannot argue a wrong predicate into a right score.

This is a SYNTHETIC ground: the dataset is generated from a known target, so the whole loop can
run offline with a real, checkable metric. The LIVE ground (the ARC-AGI environment) is the same
interface with a different backend -- see live_arc.py. Level-completion on the live gate is the
only metric that ultimately counts (paper §16.7); this synthetic ground is scaffolding for it.
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Tuple
from ..kernel import Context, Predicate

_ACTIONS = [(0, 0), (0, 1), (1, 0), (0, -1), (-1, 0)]

def sample_contexts(palette: List[int], n: int, grid: int = 8, seed: int = 0) -> List[Context]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        out.append(Context(
            focus_rc=(rng.randrange(grid), rng.randrange(grid)),
            focus_colour=rng.choice(palette),
            target_rc=(rng.randrange(grid), rng.randrange(grid)),
            action_vec=rng.choice(_ACTIONS),
            intended_free=rng.random() < 0.6,
            intended_colour=rng.choice(palette + [None]),
        ))
    return out


@dataclass
class Level:
    name: str
    target: Predicate            # the hidden truth for this level
    palette: List[int]


class SyntheticGround:
    """One level's ground: a hidden target predicate labelling a fixed before-state sample."""
    def __init__(self, level: Level, n: int = 400, seed: int = 0, solved_at: float = 0.999):
        self.level = level
        self.palette = level.palette
        self.solved_at = solved_at
        self._ctxs = sample_contexts(level.palette, n, seed=seed)
        self._labels = [level.target.holds(c) for c in self._ctxs]
        self._pos = sum(self._labels)

    def score(self, pred: Predicate) -> float:
        """Balanced accuracy on the labelled sample. Balanced so a constant predicate cannot win
        on an imbalanced level (the Goodhart guard: predicting the majority label earns 0.5, not a
        free high score). Pure function of (pred, dataset) -- unpersuadable by construction."""
        tp = tn = fp = fn = 0
        for c, y in zip(self._ctxs, self._labels):
            p = pred.holds(c)
            if y and p: tp += 1
            elif y and not p: fn += 1
            elif (not y) and p: fp += 1
            else: tn += 1
        pos, neg = tp + fn, tn + fp
        tpr = tp / pos if pos else 1.0
        tnr = tn / neg if neg else 1.0
        return 0.5 * (tpr + tnr)

    def solved(self, pred: Predicate) -> bool:
        return self.score(pred) >= self.solved_at

    def __repr__(self):
        return f"<SyntheticGround {self.level.name} target='{self.level.target}' pos={self._pos}/{len(self._labels)}>"


def make_curriculum(palette: List[int], seed: int = 0) -> List[Level]:
    """A graduated curriculum (the ARC-3 shape the 'library vs composers' essay is about): two chains
    that REFINE upward, each adding a mechanic. Built from the KERNEL's own atoms so every target is
    a real, evaluable Γ predicate.

    The load-bearing design: the blind proposer enumerates conjunctions only up to size 2 (a real
    bound -- the size-3 space is ~C(atoms,3), which blind search cannot cover). So the size-3 targets
    (L3, and L5 is size-2) are reachable ONLY by composing on top of a verified predicate that the
    shared Γ carries forward -- refinement of a promoted level. That is exactly §16.7's question:
    without the database, an agent's bounded blind search cannot get there; with it, composition can.
    """
    from ..kernel import make_atom
    A = make_atom
    c0, c1 = palette[0], palette[1]
    L = []
    # chain 1: TOUCH -> TOUCH∧colour -> TOUCH∧colour∧free   (size 1 -> 2 -> 3)
    L.append(Level("L1_touch", Predicate(frozenset({A("TOUCH")})), palette))
    L.append(Level("L2_touch_colour", Predicate(frozenset({A("TOUCH"), A("HAS_COLOUR", c0)})), palette))
    L.append(Level("L3_touch_colour_free",
                   Predicate(frozenset({A("TOUCH"), A("HAS_COLOUR", c0), A("INTENDED_FREE")})), palette))
    # chain 2: ACTS_TOWARD -> ACTS_TOWARD∧same_row∧colour   (size 1 -> 3)
    L.append(Level("L4_acts", Predicate(frozenset({A("ACTS_TOWARD")})), palette))
    L.append(Level("L5_acts_row_colour",
                   Predicate(frozenset({A("ACTS_TOWARD"), A("SAME_ROW"), A("HAS_COLOUR", c1)})), palette))
    return L
