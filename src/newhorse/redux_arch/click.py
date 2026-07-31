"""
click.py -- redux-triality: the CLICK modality (ACTION6 coordinate clicks) + a where-to-click perception.

Coverage gap this closes (docs/DEV_SET_SURVEY.md): 6/25 dev games (s5i5, lp85, tn36, vc33, r11l, ft09) offer
ONLY a coordinate click (ACTION6). The directional stack filters `v == 6`, so the agent literally cannot act on
~24% of the dev set. This module gives it a coordinate to click and an epistemic policy for choosing which.

Two pure pieces (unit-tested without the wire):
  click_targets(frame)   -- the referent prior generalised from COLOUR to COORDINATE space: rank the centroids of
                            distinct non-background components (the interactive tokens) as candidate click points.
  ClickProber            -- curiosity/empowerment over click TARGETS: cycle unvisited candidates first, then prefer
                            the ones observed to CHANGE the board (epistemic action), with a coarse grid sweep as a
                            fallback when the frame has too few components. It manufactures its own gradient on games
                            with no reward and no gameplay recordings to imitate.

★ THE DISAGREEMENT, AND ITS RESOLUTION (2026-07-31). FOR EIGHT SWEEPS THE DOCSTRING ABOVE AND THE CALL SITE
DISAGREED AND THE CALL SITE WON. The old text is preserved verbatim in docs/tether/EVIDENCE_the_click_pool_floor.md
and reads: "a coarse grid sweep as a FALLBACK when the frame has too few components" is the DESIGN;
`ReduxPolicy._new_prober` passes `grid_sweep(grid, n=8)` -- 64 blind lattice points -- UNCONDITIONALLY, on every
prober ever built, alongside up to 24 perceptual centroids. So the documented fallback is in fact a mandatory
64-point enumeration tax paid before any learned score can be consulted (`choose` cannot leave the untried branch
until EVERY target has been tried once).

Sweep H at `67e8d8a` turned that offline bound into a receipt: 1131 of 1393 click steps (81.2%) drained the
construction pool blind, ELEVEN of fifteen clicking games spent that pool to the last target, and 978 refresh
arrivals yielded 211 chosen steps (21.6%) against 80.7% for construction admissions. `exploit_scored` -- the only
branch that consults anything the click policy LEARNED -- took 51 steps, 3.7%. The receipt indicted the word
UNCONDITIONAL at a named call site. It did NOT indict the constant 8, and this change does not touch it.

★ WHAT CHANGED. The lattice is no longer ADMITTED at construction; it is HELD IN RESERVE and promoted into the
target pool on exactly the two conditions the docstrings above already name, and on no others:
  (1) perception proposed NOTHING            -> "when the frame has too few components" (promoted in `__init__`)
  (2) nothing perceptual ever moved the board -> "falling back to a coarse grid sweep if nothing perceptual ever
                                                 moved" (promoted at the inert exit of `choose`)
This is the DESIGN being wired for the first time, not a new policy. It removes no capability: every lattice point
is still reachable, and on a frame where perception is useless it is reached on the very first choose(). What it
removes is the ORDERING -- the lattice no longer sits in front of the learned scores and the refresh arrivals.

★ HOW TO OVERTURN / RUN THE CONTROL. `NEWHORSE_CLICK_LATTICE=eager` restores the pre-07-31 wiring EXACTLY, at the
same commit. That switch exists so the intervention can be isolated from the counters that measure it (two changes
and one number is not a measurement); it is not a tuning knob and nothing in the agent reads it.

We reclaim the MECHANISM (choose-a-click-that-informs), never a per-game answer. LAW 0: the prober SEES the frame
change before it "says" a target is productive.
"""
from __future__ import annotations
import os
from typing import List, Optional, Tuple, Dict, Set
from .survival import board_fingerprint
import numpy as np
from scipy import ndimage as _ndi

# ★ THE CONTROL-ARM SWITCH, AND THE ONLY REASON IT EXISTS. "reserve" is the shipped wiring (the lattice is a
# fallback, as designed); "eager" is the pre-2026-07-31 wiring (the lattice is admitted at construction). Two arms
# at the SAME commit are what separate the intervention from the counters added to measure it -- without that, the
# beat would be two changes and one number. The agent never reads this; only `ClickProber.__init__` does, once.
LATTICE_ADMISSION = (os.environ.get("NEWHORSE_CLICK_LATTICE") or "reserve").strip().lower()


def _background(frame: np.ndarray) -> int:
    """The most common colour is the field/background (the non-interactive substrate)."""
    vals, cnts = np.unique(np.asarray(frame), return_counts=True)
    return int(vals[int(np.argmax(cnts))])


def click_targets(frame: np.ndarray, bg: Optional[int] = None, min_px: int = 1,
                  max_frac: float = 0.20, top: int = 24) -> List[Tuple[int, int]]:
    """Candidate click points = centroids of distinct non-background components, ranked by salience.

    Salience prefers RARER colours (a colour used for few pixels is likelier an interactive token than a bulk fill)
    and MODERATE-sized components (drop single-pixel noise ties by keeping them last, drop giant fills over
    max_frac of the board). Returns (row, col) centroids, de-duplicated, best-first, capped at `top`.
    """
    f = np.asarray(frame)
    if f.ndim != 2:
        return []
    h, w = f.shape
    area = h * w
    if bg is None:
        bg = _background(f)
    colour_total = {int(c): int(n) for c, n in zip(*np.unique(f, return_counts=True))}
    scored: List[Tuple[float, Tuple[int, int]]] = []
    for colour in sorted(colour_total):
        if colour == bg:
            continue
        lab, k = _ndi.label(f == colour)
        for i in range(1, k + 1):
            ys, xs = np.where(lab == i)
            size = ys.size
            if size < min_px or size > max_frac * area:
                continue
            r, c = int(round(ys.mean())), int(round(xs.mean()))
            # rarer colour -> smaller score (ranks first); tiny (1px) noise pushed later via a size floor
            rarity = colour_total[colour] / area
            noise_penalty = 2.0 if size == 1 else 0.0
            scored.append((rarity + noise_penalty, (r, c)))
    scored.sort(key=lambda t: t[0])
    out: List[Tuple[int, int]] = []
    seen = set()
    for _, rc in scored:
        if rc in seen:
            continue
        seen.add(rc)
        out.append(rc)
        if len(out) >= top:
            break
    return out


def grid_sweep(frame: np.ndarray, n: int = 8) -> List[Tuple[int, int]]:
    """Fallback candidate points: an n x n lattice over the board (used when components are too few to probe)."""
    f = np.asarray(frame)
    h, w = f.shape
    rs = [int((i + 0.5) * h / n) for i in range(n)]
    cs = [int((j + 0.5) * w / n) for j in range(n)]
    return [(r, c) for r in rs for c in cs]


class ClickProber:
    """Curiosity/empowerment over click TARGETS -- the epistemic-action policy for a coordinate-click game.

    Bootstraps with the perceptual candidates (component centroids). Each beat it returns the least-tried target;
    once every candidate has been tried at least once it prefers targets that were OBSERVED to change the board
    (productive), falling back to a coarse grid sweep if nothing perceptual ever moved. This mirrors the directional
    CuriosityExplorer, but over WHERE-TO-CLICK instead of where-to-step.
    """

    def __init__(self, candidates: List[Tuple[int, int]], sweep: Optional[List[Tuple[int, int]]] = None,
                 branch: Optional[Dict[str, int]] = None, pool: Optional[Dict[str, int]] = None,
                 lattice: Optional[str] = None):
        # de-dup while preserving perceptual order, then EITHER append the sweep points (eager, the pre-07-31
        # wiring) OR hold them in a reserve that is promoted only on the two documented fallback conditions.
        # ★ PROVENANCE IS RECORDED AT ADMISSION, which is the only place it is knowable. `origin` says WHERE a
        # target came from -- perception, the blind lattice at construction, the blind lattice on PROMOTION, or a
        # later `refresh` -- and it is what lets the untried branch name WHICH POOL it is draining instead of
        # reporting one undifferentiated `untried_first`. `sweep` and `reserve` are DELIBERATELY separate names:
        # `untried_sweep` keeps meaning exactly what it meant on sweeps A-H (a lattice point admitted at
        # CONSTRUCTION) so the eight-sweep series stays readable, and the new mechanism gets its own literal at
        # its own return rather than being folded into an existing name (RANKING 5).
        self._lattice_mode: str = (lattice or LATTICE_ADMISSION)
        _eager = (self._lattice_mode == "eager")
        self.targets: List[Tuple[int, int]] = []
        self.origin: Dict[Tuple[int, int], str] = {}
        self._reserve: List[Tuple[int, int]] = []
        seen: Set[Tuple[int, int]] = set()
        _n_perc = _n_sweep = 0
        for rc in list(candidates):
            if rc not in seen:
                seen.add(rc)
                self.targets.append(rc)
                self.origin[rc] = "perceptual"
                _n_perc += 1
        for rc in list(sweep or []):
            if rc in seen:
                continue
            seen.add(rc)
            if _eager:
                self.targets.append(rc)
                self.origin[rc] = "sweep"
                _n_sweep += 1
            else:
                self._reserve.append(rc)
        self.tries: Dict[Tuple[int, int], int] = {t: 0 for t in self.targets}
        self.changed: Dict[Tuple[int, int], int] = {t: 0 for t in self.targets}
        self.novel: Dict[Tuple[int, int], int] = {t: 0 for t in self.targets}   # clicks that reached an UNSEEN board
        self._seen: Set[int] = set()                        # board-state fingerprints ever observed
        self._last: Optional[Tuple[int, int]] = None
        # ★ THE CLICK BRANCH. `click_native` is 45.4% of every decision the agent makes and it is a SINGLE exit
        # name covering FOUR different reasons to click, because every click carries the same label `A6`. An exit
        # name that covers more than one `return` is not an attribution (RANKING 5). This dict is that attribution
        # and nothing else: a STRING LITERAL at each `return` of `choose`, which is the real call site. It is
        # OWNED BY THE POLICY and passed in, so it is segment-scoped there and cleared IN PLACE -- a prober that
        # outlives a segment must keep writing into the live dict, not a rebound one it can no longer see.
        self.branch: Dict[str, int] = {} if branch is None else branch
        # ★ THE POOL, MEASURED AT ITS OWN CALL SITES. Separate dict, separate denominator: these are ADMISSIONS,
        # not steps, so they must never join `branch` (whose sum is an identity against the click exits). It is
        # written here in `__init__` and in `refresh` -- the two places a target can enter the pool -- and never
        # derived from anything else. Keys: `ctor_probers` (constructions), `ctor_perceptual` / `ctor_sweep`
        # (targets admitted at construction, by origin), `ctor_targets` (their sum, published so the de-dup
        # between the two sources is visible rather than assumed), `refresh_calls`, `refresh_admitted`, and for the
        # reserve: `ctor_reserved` (lattice points HELD, not admitted), `reserve_promotions_empty` /
        # `reserve_promotions_inert` (promotion events, one literal per cause), `reserve_admitted` (points that
        # actually entered `targets` on promotion). `ctor_reserved` is written AFTER `ctor_targets` and is not part
        # of the construction identity, because a held point is not an admission.
        self.pool: Dict[str, int] = {} if pool is None else pool
        self._p("ctor_probers", 1)
        self._p("ctor_perceptual", _n_perc)
        self._p("ctor_sweep", _n_sweep)
        self._p("ctor_targets", len(self.targets))
        # ★ THE RESERVE IS COUNTED SEPARATELY AND *AFTER* `ctor_targets`, so the construction identity
        # `ctor_targets - ctor_perceptual - ctor_sweep == 0` is untouched in both modes. A held point is not an
        # admission; it becomes one only when a promotion writes `reserve_admitted` at its own call site.
        self._p("ctor_reserved", len(self._reserve))
        # CONDITION (1), the module docstring's "too few components", in its only unambiguous form: NONE. Without
        # this the prober would return `no_targets` on a frame perception cannot read, which is the one case the
        # blind lattice was actually written for.
        if not self.targets and self._reserve:
            self._promote_reserve("empty")

    def _b(self, name: str) -> None:
        self.branch[name] = self.branch.get(name, 0) + 1

    def _p(self, name: str, n: int) -> None:
        self.pool[name] = self.pool.get(name, 0) + int(n)

    def _promote_reserve(self, cause: str) -> int:
        """Move the held lattice into the live target pool. THE ONLY PLACE A RESERVE POINT IS ADMITTED, and the
        cause is a string literal chosen at the call site -- an abort code is a name somebody chose, so the branch
        that produced a promotion writes its own literal rather than letting one name cover two reasons."""
        if not self._reserve:
            return 0
        added = 0
        for rc in self._reserve:
            if rc not in self.tries:
                self.targets.append(rc)
                self.origin[rc] = "reserve"
                self.tries[rc] = 0
                self.changed[rc] = 0
                self.novel[rc] = 0
                added += 1
        self._reserve = []
        self._p("reserve_promotions_" + cause, 1)
        self._p("reserve_admitted", added)
        return added

    def choose(self) -> Optional[Tuple[int, int]]:
        """Pick the next (row, col) to click. None only if there are no candidates at all."""
        if not self.targets:
            self._b("no_targets")                               # the degenerate corner click, named
            return None
        untried = [t for t in self.targets if self.tries[t] == 0]
        if untried:
            pick = untried[0]                                   # sweep every candidate at least once first
            self._last = pick
            # ★ `untried_first` WAS ITSELF AN EXIT NAME OVER MORE THAN ONE CAUSE, and it carried 96.3% of every
            # click the agent made. It resolves here into THREE returns by the ADMISSION ORIGIN of the target
            # being drained, because the two mechanisms that can produce a blind click are different organs:
            #   untried_perceptual  perception proposed this point (`click_targets` centroids)
            #   untried_sweep       nobody proposed it -- it is a `grid_sweep` lattice point admitted at
            #                       CONSTRUCTION. That is the pre-07-31 wiring and it is what sweeps A-H measured;
            #                       under the shipped `reserve` wiring this row is 0 by construction.
            #   untried_reserve     a `grid_sweep` lattice point admitted by PROMOTION -- i.e. the fallback fired
            #                       because perception proposed nothing, or because nothing perceptual ever moved
            #   untried_refresh     the board changed and `refresh()` folded a newly-perceived point in
            # `self.targets` is drained IN ADMISSION ORDER (perceptual, then sweep, then refresh arrivals), so a
            # prober cannot reach a refresh-admitted target until the whole construction pool is spent. That is
            # a CODE FACT and it is what makes these three counts a decomposition rather than three labels.
            _o = self.origin.get(pick)
            if _o == "sweep":
                self._b("untried_sweep")
                return pick
            if _o == "reserve":
                self._b("untried_reserve")
                return pick
            if _o == "refresh":
                self._b("untried_refresh")
                return pick
            self._b("untried_perceptual")
            return pick
        # exploit: prefer targets that reach NOVEL board states -- a cell that merely TOGGLES (reverts to an
        # already-seen state) scores changed>0 forever but adds no new territory, so it must not out-rank a
        # target still discovering unseen configurations. Novelty first, then raw change, then least-tried.
        pick = max(self.targets, key=lambda t: (self.novel[t], self.changed[t], -self.tries[t]))
        if self.novel[pick] == 0 and self.changed[pick] == 0:   # nothing ever moved
            # CONDITION (2), and it is the class docstring's own sentence: "falling back to a coarse grid sweep if
            # nothing perceptual ever moved". Every perceptual (and refresh-perceived) target has now been clicked
            # at least once and NONE of them changed the board, so perception has been given its turn and failed.
            # THIS is where the blind lattice earns its keep -- after the evidence, not in front of it.
            if self._promote_reserve("inert"):
                pick = next((t for t in self.targets if self.tries[t] == 0), pick)
                self._b("untried_reserve")
                self._last = pick
                return pick
            pick = min(self.targets, key=lambda t: self.tries[t])
            self._b("nothing_moved_least_tried")
            self._last = pick
            return pick
        self._b("exploit_scored")
        self._last = pick
        return pick

    def observe(self, prev_frame: np.ndarray, new_frame: np.ndarray) -> bool:
        """Record whether the last click changed the board (the empowerment signal). Returns did-change."""
        if self._last is None:
            return False
        self.tries[self._last] += 1
        p, n = np.asarray(prev_frame), np.asarray(new_frame)
        did = not np.array_equal(p, n)
        fp_new = board_fingerprint(n)
        novel = did and (fp_new not in self._seen)          # changed AND reached a state never seen before
        self._seen.add(board_fingerprint(p)); self._seen.add(fp_new)
        if did:
            self.changed[self._last] += 1
        if novel:
            self.novel[self._last] += 1
        return did

    def refresh(self, new_candidates: List[Tuple[int, int]]) -> int:
        """Fold freshly-perceived candidate points into the pool (the board changed -> new tokens may exist).
        Existing targets keep their tries/changed history. Returns how many NEW targets were added."""
        added = 0
        for rc in new_candidates:
            if rc not in self.tries:
                self.targets.append(rc)
                self.origin[rc] = "refresh"
                self.tries[rc] = 0
                self.changed[rc] = 0
                self.novel[rc] = 0
                added += 1
        self._p("refresh_calls", 1)
        self._p("refresh_admitted", added)
        return added

    def productive(self) -> List[Tuple[int, int]]:
        """Targets that have been observed to change the board (the learned interactive points)."""
        return [t for t in self.targets if self.changed[t] > 0]
