"""
goal.py -- redux-arch P5-GOAL: POSE THE PROBLEM by minting one level up.

Affordances are minted off the TRANSITION residual ("did the world change as Γ predicted?") and give the
vocabulary of what is DOABLE (INTENDED_FREE). The GOAL is minted off the REWARD/PROGRESS residual ("did success
show up where my current goal-guess predicted?"): a posed goal is a predicate `R(avatar, target)` whose truth
coincides with progress. Same two-part-MDL machinery, same before-state DSL, different surprise stream.

The non-trivial discovery is TARGET SELECTION -- WHICH object, among several salient candidates, the reward
actually tracks. A distractor object also has a geometry; the poser must find that progress coincides with
`ACTS_TOWARD` the RIGHT object, not a red herring. That selection is "what is this game asking?" for a navigation
game -- the sensorimotor analog of an LLM posing a well-formed problem from an underspecified prompt.

NOTE (design law): the NOVELTY TEST does NOT apply here. Selecting an existing atom (`ACTS_TOWARD`) as the GOAL is
the CORRECT outcome, not a re-derivation failure. Novelty is required only for VOCABULARY growth (Region III),
never for goal selection. So `LiveMintBridge`'s navigation-progress residual -- dismissed earlier as "re-derives
ACTS_TOWARD" -- IS the goal-poser, reframed; this module makes the posing explicit and multi-candidate.

SUPPORT is the hazard: real reward (a win / `levels_completed`) is sparse. `pose_goal` needs a DENSE-enough
progress label to clear the MDL bar; where the label is near-empty it correctly poses NOTHING (guard, not bug).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Hashable
import numpy as np
from scipy import ndimage
from .dsl import Context
from .minting import two_part_mdl, Mint


def approachable_component_centroid(frame, colour: int, passable) -> Optional[Tuple[float, float]]:
    """Resolve a referent COLOUR to a specific OBJECT: the connected component most ADJACENT to the discovered
    passable region -- the goal the avatar can actually navigate to (ls20's grey goal box touches the green stem;
    the grey legend inset is walled off in the field). Fixes the colour-UNION phantom centroid. Ranked by
    (passable-adjacent pixels, size); falls back to the largest component, then the union centroid. Uses only
    discovered structure (the passable set), never a baked choice."""
    F = np.asarray(frame)
    m = (F == colour)
    if not m.any():
        return None
    lab, k = ndimage.label(m)
    if k <= 1:
        ys, xs = np.where(m); return (float(ys.mean()), float(xs.mean()))
    pass_mask = np.isin(F, list(passable)) if passable else np.zeros(F.shape, bool)
    adj = ndimage.binary_dilation(pass_mask)              # cells touching the passable region
    best, best_key = None, None
    for i in range(1, k + 1):
        comp = (lab == i)
        key = (int((comp & adj).sum()), int(comp.sum()))  # touches-passable first, then size
        if best_key is None or key > best_key:
            best_key, best = key, comp
    ys, xs = np.where(best)
    return (float(ys.mean()), float(xs.mean()))

# one observed step: (avatar_cell, action_vec, {candidate_id: candidate_cell}, progressed?)
GoalStep = Tuple[Tuple[int, int], Tuple[int, int], Dict[Hashable, Tuple[int, int]], bool]


@dataclass
class PosedGoal:
    target: Hashable                                     # which candidate the reward tracks (the discovery)
    mint: Mint                                           # the winning predicate over (avatar, target)
    saved_bits: float
    def __str__(self) -> str:
        return "GOAL: %s over (avatar, target=%r)  [%.1f bits]" % (self.mint.predicate, self.target, self.saved_bits)


def pose_goal(steps: List[GoalStep], avatar_colour: int = 0, max_size: int = 1) -> Optional[PosedGoal]:
    """Pose the game's goal by MDL over the progress residual: for each candidate target, score the best
    before-state predicate `R(avatar, candidate)` that compresses the progress stream; return the candidate whose
    predicate compresses it most. None if no candidate's relation compresses progress (SUPPORT/orthogonality
    guard -- the reward has no structure a single relation captures)."""
    cands = set()
    for _, _, cmap, _ in steps:
        cands.update(cmap.keys())
    best: Optional[PosedGoal] = None
    for cid in sorted(cands, key=lambda x: str(x)):
        exc = []
        for avatar, avec, cmap, prog in steps:
            if cid not in cmap:
                continue
            exc.append((Context(focus_rc=avatar, focus_colour=int(avatar_colour),
                                 target_rc=cmap[cid], action_vec=avec), bool(prog)))
        if len(exc) < 2:
            continue
        m = two_part_mdl(exc, max_size=max_size)         # searches ACTS_TOWARD, NEAR, TOUCH, SAME_ROW/COL ...
        if m is None:
            continue
        if best is None or m.saved_bits > best.saved_bits:
            best = PosedGoal(target=cid, mint=m, saved_bits=m.saved_bits)
    return best


def salient_targets(frames, avatar_colour: int, exclude=(), min_px: int = 4, max_frac: float = 0.15,
                    motion_frac: float = 0.3, top: int = 3) -> List[int]:
    """Referent prior (v6 §3, design pragmatics: salience · uniqueness · framing). A goal REFERENT is a distinct,
    STATIC, moderately-sized COMPACT object -- not 1–2px noise, not the huge floor/field/background, and NOT the
    moving avatar (an actor is not its own goal). This fixes the first-live-run failure where a smallest-first
    ranking grabbed a 2px fleck instead of the real landmark.

    Filters (all general, never a specific game's answer): drop the avatar colour and any `exclude` colours (pass
    the passable/floor + background here); drop colours with footprint < `min_px` (noise) or > `max_frac`·frame
    (floor/field); drop colours whose centroid MOVES on more than `motion_frac` of steps (that is an actor, not a
    landmark). Rank the survivors by prominence (footprint) — a large compact static blob outranks a tiny one."""
    F = np.stack([np.asarray(f) for f in frames])
    n = len(F); hw = F[0].size
    ex = set(int(x) for x in exclude)
    scored = []
    for c in sorted(set(int(v) for v in np.unique(F))):
        if c == avatar_colour or c in ex:
            continue
        sizes = [int((F[i] == c).sum()) for i in range(n)]
        size = int(np.median(sizes))
        if size < min_px or size > max_frac * hw:
            continue                                     # noise, or the floor/field/background
        moved, last = 0, None                            # centroid motion across frames
        for i in range(n):
            m = (F[i] == c)
            if m.any():
                ys, xs = np.where(m); cen = (round(float(ys.mean()), 1), round(float(xs.mean()), 1))
                if last is not None and cen != last:
                    moved += 1
                last = cen
        if moved > motion_frac * n:
            continue                                     # too mobile -> an actor/avatar, not a landmark
        scored.append((c, size))
    scored.sort(key=lambda t: -t[1])                     # most prominent static landmark first
    return [c for c, _ in scored[:top]]


def static_salient_targets(frames, avatar_colour: int, bg: int, top: int = 3) -> List[int]:
    """Design-prior candidate targets from a run's frames: colours that are STATIC (never move -- landmarks) and
    are neither the avatar nor the background, ranked by DISTINCTNESS (smallest footprint first -- a unique little
    landmark is a stronger 'this is significant' cue than a big wash of colour). If nothing is perfectly static,
    fall back to all non-avatar/non-bg colours by size. LAW 0: confirm the chosen target by pixels before trusting
    a posed goal built on it."""
    F = np.stack([np.asarray(f) for f in frames])
    scored = []
    for c in sorted(set(int(v) for v in np.unique(F))):
        if c == avatar_colour or c == bg:
            continue
        mask = (F == c)
        if not mask.any():
            continue
        static = bool((mask == mask[0]).all())           # identical every frame -> a fixed landmark
        scored.append((c, int(mask[0].sum()), static))
    statics = [(c, s) for c, s, st in scored if st]
    ranked = sorted(statics or [(c, s) for c, s, _ in scored], key=lambda x: x[1])
    return [c for c, _ in ranked[:top]]
