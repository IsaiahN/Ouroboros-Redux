"""
transition_induction.py -- the ENVIRONMENT-side state-transition inducer.

Sibling to the agent-side evolvability engine, but a DIFFERENT epistemic act. The evolvability engine mints/
co-opts AGENT objectives under sparse reward (variation-under-selection -- the elaboration-trap risk lives there).
This module reverse-engineers the ENVIRONMENT's hidden transition rule T(s, a) -> s' from before/after snapshots
via grey-box LOCAL-RULE induction (LFIT / cellular-automaton rule-induction style). Three properties, by design,
matching the environment-simulator research doc:

  1. UNCONDITIONAL. Fed EVERY exploration transition, whether or not any objective was satisfied. It is the
     perception layer that builds the world model -- NOT a repair triggered by the ResidualReporter (that gating
     inherits the dead "satisfied-but-unrewarded" trigger the live scan showed never fires).

  2. FALSIFICATION-GATED. A rule that mispredicts the very next frame is dead on arrival -- dense, cheap, and
     immediately falsifiable against ground truth. No reward signal needed. This is the one property the agent
     side lacks, and it is why induction is tractable where mint/co-opt is speculative.

  3. IDENTIFIABILITY-AWARE. When the SAME local precondition maps to DIFFERENT effects, the dynamics are not
     identifiable from this representation (hidden state / observational equivalence -- the provable-limits case).
     The engine REPORTS this rather than inventing a rule to paper over it. This is the built-in bp35 diagnostic:
     it distinguishes a missing-rule gap (build a bigger inducer) from an identifiability WALL ([PROVEN] limit).

Rule form (v1, grey-box, pixel-local): precondition = (center_before, action, Moore-8 neighbour colours);
effect = center_after. Out-of-bounds neighbours use a sentinel. Generalisation over which neighbours matter is
[BUILDABLE] and deferred; exact-positional match is falsifiable and correct, just less general.

NOTE: pixel-local rules on a scale>1 game are noisier at block interiors; logical-resolution induction (downscale
by the effect_classifier cell scale) is a [BUILDABLE] refinement. v1 runs at pixel resolution and lets the
falsification gate report whether pixel rules are consistent.
"""

import numpy as np
from collections import Counter, defaultdict

_OOB = -1                    # sentinel colour for out-of-bounds neighbours
_MOORE = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _akey(action):
    """Stable hashable key for an action (GameAction, 'click', tuple, int)."""
    try:
        if isinstance(action, tuple):
            return ("click",) if action and action[0] == "click" else tuple(action)
        return str(action)
    except Exception:
        return str(action)


def _neigh(g, r, c):
    H, W = g.shape
    out = []
    for dr, dc in _MOORE:
        rr, cc = r + dr, c + dc
        out.append(int(g[rr, cc]) if 0 <= rr < H and 0 <= cc < W else _OOB)
    return tuple(out)


class TransitionInductionEngine:
    """Induce and simulate the environment's transition rule from observed (before, action, after) transitions."""

    def __init__(self, confirm_support=2, neg_sample=48, max_rules=200000):
        # precondition -> Counter(effect_value -> support). effect includes "no change" as the same-value effect.
        self._table = defaultdict(Counter)
        self.confirm_support = confirm_support        # a rule is CONFIRMED at >= this support with no live conflict
        self.neg_sample = neg_sample                  # unchanged cells sampled per transition (stability evidence)
        self.max_rules = max_rules
        self._n_obs = 0                               # transitions ingested
        self._changed_seen = 0                        # changed cells seen (denominator for coverage)
        self._changed_explained = 0                   # changed cells whose pattern is a CONFIRMED change-rule
        self._pred_cells = 0                          # cells predicted (falsification denominator)
        self._pred_wrong = 0                          # cells mispredicted (falsification numerator)
        self._rng = np.random.default_rng(0)

    # ---- (1) INDUCTION: ingest one real transition, unconditionally ------------------------------------
    def observe(self, before, action, after):
        """Ingest ONE (before, action, after) transition: extract local-rule evidence from changed cells (and a
        sample of UNCHANGED cells, for stability/negative evidence so contradictions surface). Falsification-scores
        the current rules against this transition BEFORE updating. Returns a per-transition status dict."""
        b = np.asarray(before); a = np.asarray(after)
        if b.shape != a.shape or b.ndim != 2:
            return dict(ok=False, reason="shape")
        ak = _akey(action)
        # -- falsify current rules against this ground-truth transition (the dense, reward-free signal) --
        pred = self._simulate_grid(b, ak)
        chmask = (b != a)
        predmask = (pred != b)
        wrong = int(np.count_nonzero((pred != a) & (chmask | predmask)))
        cells = int(np.count_nonzero(chmask | predmask))
        self._pred_wrong += wrong; self._pred_cells += cells
        # -- update rule table from changed cells --
        ch = np.argwhere(chmask)
        for (r, c) in ch:
            key = (int(b[r, c]), ak, _neigh(b, r, c))
            self._table[key][int(a[r, c])] += 1
            self._changed_seen += 1
        # -- negative/stability evidence: sample UNCHANGED cells so a pattern that SOMETIMES changes and
        #    SOMETIMES doesn't surfaces as a CONTRADICTION (non-identifiable), not a silent bias --
        H, W = b.shape
        if len(ch) and len(self._table) < self.max_rules:
            for _ in range(self.neg_sample):
                r = int(self._rng.integers(0, H)); c = int(self._rng.integers(0, W))
                if chmask[r, c]:
                    continue
                key = (int(b[r, c]), ak, _neigh(b, r, c))
                self._table[key][int(b[r, c])] += 1        # effect == same value (stable)
        self._n_obs += 1
        return dict(ok=True, wrong=wrong, cells=cells,
                    predict_error=round(wrong / cells, 3) if cells else 0.0)

    # ---- rule readout -------------------------------------------------------------------------------
    def _rule_for(self, key):
        """Return (effect, status) for a precondition. status in {confirmed, tentative, contradictory}."""
        ctr = self._table.get(key)
        if not ctr:
            return None, "unseen"
        top, top_n = ctr.most_common(1)[0]
        rest = sum(v for e, v in ctr.items() if e != top)
        if rest >= 2 and rest >= 0.34 * top_n:                # genuine conflict, not one-off noise
            return top, "contradictory"                        # same precondition -> different effects
        if top_n >= self.confirm_support and rest == 0:
            return top, "confirmed"
        return top, "tentative"

    def rules(self, status="confirmed"):
        """All induced rules at a given status, as (center, action, neighbours) -> effect."""
        out = []
        for key, ctr in self._table.items():
            eff, st = self._rule_for(key)
            if st == status and eff is not None:
                out.append((key, eff, sum(ctr.values())))
        return out

    # ---- (2) SIMULATION: roll the induced rules forward ---------------------------------------------
    def _simulate_grid(self, g, ak):
        """Apply CONFIRMED change-rules to every cell to produce the predicted next grid (generative T(s,a)).
        Cells with no confirmed change-rule (or contradictory/unseen) default to UNCHANGED -- conservative."""
        g = np.asarray(g); out = g.copy()
        H, W = g.shape
        # only cells whose (center,action,neigh) is a confirmed rule with effect != center get changed
        for r in range(H):
            for c in range(W):
                key = (int(g[r, c]), ak, _neigh(g, r, c))
                eff, st = self._rule_for(key)
                if st == "confirmed" and eff != int(g[r, c]):
                    out[r, c] = eff
        return out

    def simulate(self, state, action, steps=1):
        """Predict the next state(s) by rolling induced rules forward `steps` times. The GENERATIVE counterpart
        to effect_signature's descriptive read. Returns the final predicted grid (or list if steps>1)."""
        ak = _akey(action)
        g = np.asarray(state).copy()
        traj = []
        for _ in range(max(1, steps)):
            g = self._simulate_grid(g, ak)
            traj.append(g.copy())
        return traj[-1] if steps == 1 else traj

    def predict_error(self, before, action, after):
        """Falsification score for one transition: fraction of active cells mispredicted. A high value is the
        DEMOTED ResidualReporter signal -- 're-induce the world rule', NOT 'mint an agent objective'."""
        b = np.asarray(before); a = np.asarray(after)
        pred = self._simulate_grid(b, _akey(action))
        active = (b != a) | (pred != b)
        n = int(np.count_nonzero(active))
        return round(int(np.count_nonzero((pred != a) & active)) / n, 3) if n else 0.0

    # ---- (3) IDENTIFIABILITY + COVERAGE (the provable-limits readout) --------------------------------
    def report(self):
        """Epistemic readout of the induced world model:
          - coverage: fraction of observed CHANGED cells explained by a confirmed change-rule.
          - contradiction_rate: fraction of change-preconditions that are CONTRADICTORY (same precondition ->
            different effects) => NOT identifiable from this representation (hidden state / obs-equivalence).
          - fidelity: 1 - running falsification error (how well the current rules predict real transitions).
          - identifiable: whether the observed dynamics ARE explained by a consistent local rule set. If False,
            a bigger inducer will NOT help -- it is a [PROVEN] identifiability wall (the bp35-style verdict)."""
        change_keys = [k for k in self._table if any(e != k[0] for e in self._table[k])]
        contradictory = 0; confirmed_change = 0; support_confirmed = 0
        for k in change_keys:
            eff, st = self._rule_for(k)
            if st == "contradictory":
                contradictory += 1
            elif st == "confirmed" and eff != k[0]:
                confirmed_change += 1
                support_confirmed += sum(v for e, v in self._table[k].items() if e == eff)
        n_change_keys = max(1, len(change_keys))
        coverage = round(support_confirmed / max(1, self._changed_seen), 3)
        contradiction_rate = round(contradictory / n_change_keys, 3)
        fidelity = round(1.0 - (self._pred_wrong / self._pred_cells), 3) if self._pred_cells else None
        # identifiable if most change-preconditions are non-contradictory AND fidelity is decent
        identifiable = (contradiction_rate <= 0.15) and (fidelity is None or fidelity >= 0.6)
        return dict(transitions=self._n_obs,
                    change_rules_confirmed=confirmed_change,
                    change_preconditions=len(change_keys),
                    coverage=coverage,
                    contradiction_rate=contradiction_rate,
                    fidelity=fidelity,
                    identifiable=bool(identifiable),
                    verdict=("identifiable-dynamics" if identifiable else
                             "NON-identifiable (hidden-state / obs-equivalent -- a limits wall, not a missing module)"))


# ===================================================================================================
# §15 OBJECT / LOGICAL-RESOLUTION LIFT -- the precondition for believing any non-identifiability verdict.
# Pixel-local rules are noisy at scale>1 (block interiors all-same-colour). Two lifts:
#   (a) LOGICAL resolution: downscale by the effect-classifier cell scale, then induce local rules on the
#       logical grid (a scale-3 block collapses to one cell -> the law becomes visible and low-noise).
#   (b) OBJECT level: induce per-object relational rules (translate / vanish / recolor / spawn), which express
#       "this whole object slides until contact" -- a law pixels cannot represent.
# ===================================================================================================

def _logical_dims(frame):
    try:
        from effect_classifier import detect_grid_dims
        nr, nc = detect_grid_dims(frame)
        H, W = np.asarray(frame).shape
        # only treat as scaled if it genuinely reduces resolution and divides cleanly-ish
        if nr >= 2 and nc >= 2 and nr < H and nc < W:
            return (nr, nc)
    except Exception:
        pass
    return None


def _down(frame, dims):
    from effect_classifier import to_logical
    return to_logical(frame, dims)


def _up(logical, shape):
    """Nearest-neighbour upscale a logical grid back to pixel shape (for pixel-resolution discrepancy fns)."""
    lg = np.asarray(logical); nr, nc = lg.shape; H, W = shape
    out = np.zeros((H, W), dtype=int)
    for i in range(nr):
        for j in range(nc):
            out[round(i * H / nr):round((i + 1) * H / nr), round(j * W / nc):round((j + 1) * W / nc)] = lg[i, j]
    return out


class LogicalTransitionInducer:
    """§15(a): the pixel local-rule inducer run at LOGICAL resolution. Downscales every transition to the
    inferred logical grid, induces there, and upscales predictions back to pixel resolution. Dims are locked
    from the first informative frame (a scaled grid has stable dims)."""

    def __init__(self, **kw):
        self.core = TransitionInductionEngine(**kw)
        self.dims = None

    def _dims(self, frame):
        if self.dims is None:
            self.dims = _logical_dims(frame)
        return self.dims

    def observe(self, before, action, after):
        d = self._dims(before)
        if d is None:
            return dict(ok=False, reason="no-logical-grid")
        return self.core.observe(_down(before, d), action, _down(after, d))

    def simulate(self, state, action, steps=1):
        st = np.asarray(state); d = self._dims(st)
        if d is None:
            return st.copy()
        pred = self.core.simulate(_down(st, d), action, steps=steps)
        return _up(pred, st.shape)

    def predict_error(self, before, action, after):
        d = self._dims(before)
        if d is None:
            return 1.0
        return self.core.predict_error(_down(before, d), action, _down(after, d))

    def report(self):
        r = self.core.report(); r["resolution"] = "logical"; r["dims"] = self.dims
        return r


def _cellset(cells):
    """An object's arrangement, normalised to its own origin -- so "did it change shape?" is asked independently of
    "did it move?". Position is already answered by the centroid; this answers only the other question."""
    cs = [(int(y), int(x)) for y, x in cells]
    if not cs:
        return frozenset()
    y0 = min(y for y, _ in cs); x0 = min(x for _, x in cs)
    return frozenset((y - y0, x - x0) for y, x in cs)


def new_table():
    """A fresh evidence table. Module-level so a caller can own one that outlives any single episode."""
    return defaultdict(Counter)


class ObjectTransitionInducer:
    """§15(b): per-OBJECT relational transition rules. Segments before/after, matches objects by colour-signature
    + nearest centroid, and induces effects keyed by (colour_sig, size-bucket, action):
        translate(dr,dc) | vanish | recolor(new_sig) | (spawn handled as unmatched-after).
    simulate() applies the confirmed per-object rule to each object and renders back to a grid. This expresses
    object-level laws (an object sliding as a whole) that pixel rules cannot. Falsification/identifiability are
    scored at object granularity."""

    def __init__(self, confirm_support=2):
        self.terrain = set()          # colours that are the BOARD, not objects on it. Injected by whoever knows.
        self._tracks = {}             # object permanence: tid -> {ident, cells}. Survives recolour and reshape.
        self._next_tid = 0
        self._track_changed = set()   # (legacy) tids my play has altered
        self._changed_regions = set() # (identity, cy//8, cx//8) my play has RESTATED -- survives re-segmentation,
        #                               and separates the readout-region from the lock-region of a shared identity.
        self.table = defaultdict(Counter)          # (colour_sig, size_bucket, action) -> Counter(effect)
        self.confirm_support = confirm_support
        self._n = 0; self._pred = 0; self._wrong = 0
        self._ssig_cache = None; self._ssig_at = -1     # who I am, recomputed once per transition, not once per object
        self._ewma = None                 # recency-weighted fidelity, half-life ~8 transitions

    def bind_table(self, shared):
        """Accumulate the EVIDENCE across episodes instead of burning it and keeping only the verdict.

        THE ASYMMETRY THIS FIXES
        ------------------------
        `avatar_cmap` is marked "TRANSFERS across levels/games" and carries conclusions forward forever. This table --
        the transitions those conclusions were drawn FROM -- was attached to the adapter and destroyed with it. So the
        memory kept the verdict and burned the transcript. A conclusion with no evidence behind it cannot be
        re-examined, only obeyed: that is how "colour-9 box => +32 budget" survived to send the agent walking to a
        cell on a board that no longer existed.

        It also made `confirmed` mean less than it looks. `_rule` demands `rest == 0` at `confirm_support=2`, which
        reads as strict; it is not. Two is simply all the support that ever existed, because the count restarted every
        episode. "47 times out of 48" was unreachable by construction. Share the table and a law can actually be
        REPLICATED -- or killed by the 49th run, which is the half that matters.

        Scoped BY GAME on purpose. The key holds raw colours, and colour 9 is a readout here and something else
        elsewhere; pooling across games would launder one board's coincidences into another's priors. Whether laws
        generalise across games is a real question and a separate one -- it should be asked, not assumed by a
        dictionary key.
        """
        if shared is not None:
            self.table = shared
        return self

    @staticmethod
    def _bg(g):
        return int(np.bincount(np.asarray(g).ravel()).argmax())

    def _segs(self, g):
        """Objects, with the TERRAIN treated as background.

        `_bg` returns ONE colour -- the single most common, which on a maze is the floor. The walls are therefore
        FOREGROUND, and a maze's walls are one connected structure, so every segmentation returned a single
        1451-pixel object carrying `frozenset({0,1,3,5,9,12})` -- every colour on the board, as one thing. Nothing
        moves, so the only law inducible was ('stay',), and the object marked itself `contradicted`.

        The background of a board is not a colour. It is the TERRAIN: floor AND walls. `segment_objects` has always
        taken `ignore_colors` -- *"large static structure colors to treat as background too"* -- and nobody passed it.
        The agent has narrated `terrain := floor(colour 3), walls(colours [4,5])` on every single run. The knowledge
        was in the system and not in the carving.
        """
        try:
            from object_seg import segment_objects
            ign = set(int(c) for c in (self.terrain or ()))
            return segment_objects(np.asarray(g), bg=self._bg(g), ignore_colors=ign or None)
        except Exception:
            return []

    @staticmethod
    def _bucket(sz):
        return 0 if sz <= 2 else (1 if sz <= 9 else (2 if sz <= 50 else 3))

    def _delta_for(self, action):
        """The action->delta map, LEARNED from the model's own confirmed translate rules.

        Not supplied. The inducer watches the board, induces `translate(dr,dc)` for some object under some action,
        and that IS the steer map -- so the model bootstraps the feature it needs from the rules it already has.
        Before any translate is confirmed this returns None, and the key stays context-free: the model does not
        pretend to a feature it has not earned.
        """
        best, bn = None, 0
        for _k, ctr in self.table.items():
            if _k[2] != _akey(action):        # the key is (sig, size_bucket, action, context) -- 4 wide now
                continue
            for eff, n in ctr.items():
                if eff and eff[0] == "translate" and n > bn:
                    best, bn = (eff[1], eff[2]), n
        return best

    def _track(self, objs):
        """OBJECT PERMANENCE. An object keeps its identity through a recolour or a reshape, because it is still there.

        The table generalises on colour_sig + size_bucket -- appearance. The readout's whole function is to CHANGE its
        appearance, so each time it does its job it becomes, to the table, a different object: the law that it changes
        fragments across signatures and buckets and accumulates support nowhere. Level 2's readout is blue; level 6's
        is red and a different shape. Nothing keyed on how it looks can hold it across the thing it exists to do.

        What survives being repainted is that it is still THERE. Identity is founded at first sight and carried by
        overlap: it shares cells with what was there, and more of them than any other candidate does. Objects do not
        teleport, so best-overlap-wins needs no threshold.

        There WAS a threshold here -- `iou >= 0.5`, defended in this docstring as "a definition, not a tuned dial".
        Measured on the readout's rotation: 20 cells before, 20 after, 12 shared, 28 union. IoU 0.429. It fell under
        the bar and the readout was handed a NEW identity at the exact instant it did the only thing it exists to do,
        so its change history never accumulated and the tracker disagreed with the table about what had ever moved.
        A number that fails on the one case it was written for was never a definition.
        """
        prev = self._tracks; used = set(); out = {}
        for o in objs:
            cells = frozenset((int(y), int(x)) for y, x in o["cells"])
            best, bo = None, 0.0
            for tid, t in prev.items():
                if tid in used:
                    continue
                inter = len(cells & t["cells"])
                if not inter:
                    continue
                iou = inter / float(len(cells | t["cells"]))
                if iou > bo:
                    bo, best = iou, tid
            if best is not None:
                used.add(best); tid = best; ident = prev[best]["ident"]
            else:
                tid = self._next_tid; self._next_tid += 1
                ident = frozenset(o["color_sig"])
            o["tid"] = tid; o["ident"] = ident
            _prev_near = prev.get(tid, {}).get("near", 1e9) if best is not None else 1e9
            out[tid] = {"ident": ident, "cells": cells, "unseen": 0, "near": _prev_near}
        # PERMANENCE MEANS IT IS STILL THERE WHEN I CANNOT SEE IT. Keeping only what was segmented THIS frame is the
        # opposite: one frame where the readout is occluded (the ring flash) or missed, and its identity is gone --
        # measured live, the pair formed at action 27 and was dead by 71 with no level change. Carry unmatched tracks
        # forward so a reappearing object is recognised rather than re-founded as a stranger.
        # Carry unmatched tracks forward -- an occluded object still exists -- but a track is GONE, not merely unseen,
        # once its cells are demonstrably occupied by other objects now. That is evidence, not a timer: I am not
        # guessing it left after N frames, I can SEE something else in its place. Without this, ghosts accumulate
        # (measured: 46 of 59 tracks stale by action 377, unseen up to 519 frames) and the greedy matcher revives a
        # corpse for any object drifting over its old cells -- which is how "30 of 30 objects changed" emptied the
        # never-changed set and dissolved the target.
        _live_cells = set()
        for o2 in objs:
            _live_cells |= frozenset((int(y), int(x)) for y, x in o2["cells"])
        for tid, t in prev.items():
            if tid in out:
                continue
            gone = len(t["cells"] & _live_cells) / float(len(t["cells"]) or 1)
            if gone >= 0.5:
                continue                                      # its place is taken -> it is gone, drop it
            t = dict(t); t["unseen"] = t.get("unseen", 0) + 1
            out[tid] = t
        self._tracks = out
        return objs

    def loci(self):
        """Every object I am currently tracking: (cy, cx, ident, ever_changed).

        `ever_changed` is per-instance and that is the point. On this board the key and the lock are the same colour
        and the same shape family; no signature can separate them. What separates them is that my play changes one of
        them and has never changed the other.
        """
        out = []
        for tid, t in self._tracks.items():
            cells = t["cells"]
            if not cells:
                continue
            cy = sum(y for y, _ in cells) / float(len(cells))
            cx = sum(x for _, x in cells) / float(len(cells))
            rg = (t["ident"], int(cy // 8), int(cx // 8))
            out.append((cy, cx, t["ident"], rg in self._changed_regions, len(cells), t.get("near", 1e9)))
        return out

    def _self_sig(self):
        """WHICH OBJECT IS ME -- from this table, by the same test `footprint.self_signature()` uses: the thing whose
        confirmed law is TRANSLATE under my directional actions is the thing my action choice steers. Nothing handed in."""
        if self._ssig_at == self._n and self._ssig_cache is not None:
            return self._ssig_cache
        best, sup = None, 0
        for k, ctr in self.table.items():
            try:
                eff, st = self._rule(k)
            except Exception:
                continue
            if st != "confirmed" or not eff or eff[0] != "translate":
                continue
            n = sum(ctr.values())
            if n > sup:
                best, sup = k[0], n
        self._ssig_cache, self._ssig_at = best, self._n
        return best

    def _self_contact(self, action, grid, objs):
        """WHAT I TOUCHED this step: the cell I am moving into. This is the antecedent for everything that is not me."""
        d = self._delta_for(action)
        ssig = self._self_sig()
        if d is None or grid is None or ssig is None or not objs:
            return None
        me = next((o for o in objs if frozenset(o["color_sig"]) == ssig), None)
        if me is None:
            return None
        try:
            g = np.asarray(grid)
            ty = int(round(me["centroid"][0] + d[0])); tx = int(round(me["centroid"][1] + d[1]))
            if 0 <= ty < g.shape[0] and 0 <= tx < g.shape[1]:
                return int(g[ty, tx])
            return -1
        except Exception:
            return None

    def _ctx(self, o, action, grid, objs=None):
        """THE ANTECEDENT. Which question this asks depends on WHOSE law is being built:

            for ME          -> what is in the way            (unchanged; this is what _ctx was written for)
            for anything else -> WHAT I TOUCHED               (new)

        The old version asked the first question about everything, which is ego-local and meaningless for an object
        that never moves: for the readout panel it asked what colour sits five rows above a static box and got noise.
        So the panel's row read `stay x98, restate x2` -- MIXED -- and this function's own docstring already says what
        a mixed row means: not a stochastic world, an UNDER-SPECIFIED PRECONDITION. Name the feature, do not widen the
        tolerance. The feature that was missing is not in front of the panel. It is under my feet.

        With it, `contact(X) -> restate(Y)` is an ordinary row, `period` is just how many contacts before it comes
        back around, and "ambient" needs no definition: the fuel bar's row stays mixed under every antecedent because
        nothing predicts it, so it never confirms. A clock is not a kind of object. It is a law with no cause, seen
        from the inside.
        """
        _ssig = self._self_sig()
        if _ssig is not None and frozenset(o["color_sig"]) != _ssig:
            return self._self_contact(action, grid, objs)
        return self._ctx_ego(o, action, grid)

    def _ctx_ego(self, o, action, grid):
        """WHAT IS IN THE WAY -- the missing feature.

        `_key` was (colour_sig, size, action) with no context, so the avatar under ACTION1 produced BOTH
        translate(-5,0) and stay -- the same precondition with different effects. That is `contradictory`, so the
        rule never confirms, so motion_rules < 2, so `degenerate`, so fidelity 0.353 and the model is unusable.

        The row was never noisy. It was MISSING A FEATURE. A mixed row is not evidence that the world is stochastic;
        it is evidence that the precondition is under-specified -- and the fix is to name the feature, not to widen
        the tolerance. Here the feature is the cell the object is about to enter.

        Read at full resolution off the frame the agent actually saw. Game-agnostic: it asks "what is there", not
        "is it a wall".
        """
        d = self._delta_for(action)
        if d is None or grid is None:
            return None
        try:
            import numpy as _np
            g = _np.asarray(grid)
            cy, cx = o["centroid"]
            ty, tx = int(round(cy + d[0])), int(round(cx + d[1]))
            if 0 <= ty < g.shape[0] and 0 <= tx < g.shape[1]:
                return int(g[ty, tx])
            return -1                      # off-board is a context, and a very informative one
        except Exception:
            return None

    def _key(self, o, action, grid=None, objs=None):
        ident = o.get("ident") or frozenset(o["color_sig"])
        return (ident, self._bucket(o["size"]), _akey(action), self._ctx(o, action, grid, objs))

    @staticmethod
    def _match(a_objs, b_objs):
        """Greedy match a->b. TWO passes, and the second one is the whole point.

        Pass 1 -- same colour_sig, nearest centroid -- is the strongest evidence there is, and it stays first.

        Pass 2 exists because pass 1 ALONE made `recolor` UNREACHABLE. `_effect` asks
        `if ob["color_sig"] != oa["color_sig"]: return ("recolor", ...)` -- a condition pass 1 guarantees is false,
        because it refuses to pair objects whose colours differ. So the branch was dead code, and `recolor` scored 0
        across 4277 observations: not because nothing ever recoloured, but because an object that recolours cannot be
        TRACKED through the recolour, so it is filed as a death and a stranger's birth.

        Measured on ls20 frame 13: the readout's signature goes [5,9] -> [0,5,9] when its highlight flashes on, and
        its rotation lands in the table as `vanish` with the right antecedent (contact=0) and the wrong verb. The law
        was found. It was wearing someone else's name.

        This is identity keyed to colour for the third time -- the avatar carved APART by colour, the readout fused
        TOGETHER across colour, and here an object that CHANGES colour treated as two objects. So pass 2 keys on the
        one thing a recolour cannot touch: where the object is. An object that changes colour in place still occupies
        its own cells. Overlap is the evidence; colour is only a property.
        """
        used = set(); pairs = []; leftovers = []
        for oa in a_objs:
            best, bd = None, 1e18
            for j, ob in enumerate(b_objs):
                if j in used or ob["color_sig"] != oa["color_sig"]:
                    continue
                d = abs(oa["centroid"][0] - ob["centroid"][0]) + abs(oa["centroid"][1] - ob["centroid"][1])
                if d < bd:
                    bd, best = d, j
            if best is not None:
                used.add(best); pairs.append((oa, b_objs[best]))
            else:
                leftovers.append(oa)
        # PASS 2: no same-colour partner -> it may have RECOLOURED. Track it by position instead.
        # Majority overlap required. A weak positional match would quietly pair two unrelated leftovers and invent a
        # law out of a coincidence, which is worse than an honest `vanish` -- so the bar is "more shared than not".
        for oa in leftovers:
            ca = set(map(tuple, oa["cells"])); best, bo = None, 0.0
            for j, ob in enumerate(b_objs):
                if j in used:
                    continue
                cb = set(map(tuple, ob["cells"]))
                inter = len(ca & cb)
                if not inter:
                    continue
                iou = inter / float(len(ca | cb))
                if iou > bo:
                    bo, best = iou, j
            if best is not None and bo >= 0.5:
                used.add(best); pairs.append((oa, b_objs[best]))
            else:
                pairs.append((oa, None))
        return pairs

    @staticmethod
    def _normshape(cells):
        ys = [p[0] for p in cells]; xs = [p[1] for p in cells]
        r0, c0 = min(ys), min(xs)
        return frozenset((int(r - r0), int(c - c0)) for (r, c) in cells)

    @staticmethod
    def _rot90(shape):
        # 90 deg CW in image coords: (r,c) -> (c, -r), then re-normalise to non-negative
        rot = [(c, -r) for (r, c) in shape]
        ys = [p[0] for p in rot]; xs = [p[1] for p in rot]
        r0, c0 = min(ys), min(xs)
        return frozenset((r - r0, c - c0) for (r, c) in rot)

    def _rotation_of(self, cells_a, cells_b):
        """Return 90/180/270 if shape B is that CW rotation of shape A, else None."""
        a = self._normshape(cells_a); b = self._normshape(cells_b)
        if len(a) != len(b) or a == b:
            return None
        rot = a
        for deg in (90, 180, 270):
            rot = self._rot90(rot)
            if rot == b:
                return deg
        return None

    @staticmethod
    def _rotate_cell(r, c, cy, cx, deg):
        dr, dc = r - cy, c - cx
        if deg == 90:                       # CW
            return cy + dc, cx - dr
        if deg == 180:
            return cy - dr, cx - dc
        return cy - dc, cx + dr             # 270

    def _effect(self, oa, ob):
        """What happened to this object. One verb for "it became different", not a list of ways to be different.

        A TRANSLATION PRESERVES THE OBJECT. If what arrived is not the same thing in a new place, it did not move --
        it changed, and `restate` says only that, deliberately. Which axis it changed on (turned, recoloured,
        reshaped, resized, several at once) is a HYPOTHESIS for the agent to form from the evidence, not a branch for
        this function to enumerate. Enumerating it builds a list, and the next level has a change that is not on it.

        Ordering matters and used to be wrong: centroid drift was tested before shape, so a glyph whose arm swings
        left-to-right -- 20 cells, same box, mass moved 2 columns -- was recorded as `translate` 36 times. The
        readout was doing its job in plain sight and the table wrote down "it moved sideways".
        """
        if ob is None:
            return ("vanish",)
        same_shape = _cellset(oa["cells"]) == _cellset(ob["cells"])
        same_colour = frozenset(ob["color_sig"]) == frozenset(oa["color_sig"])
        if same_shape and same_colour:
            dr = int(round(ob["centroid"][0] - oa["centroid"][0]))
            dc = int(round(ob["centroid"][1] - oa["centroid"][1]))
            return ("translate", dr, dc) if (dr, dc) != (0, 0) else ("stay",)
        return ("restate",)

    def observe(self, before, action, after):
        a_objs = self._track(self._segs(before)); b_objs = self._segs(after)
        if not a_objs:
            return dict(ok=False, reason="no-objects")
        # SIGNAL C: how close has my body ever gotten to each glyph? A measured floor on approach distance -- not
        # "never visited" (absence, rests on a complete map) but "tried across the whole run, closest ever = D".
        # The target is a changed-identity glyph my body has reached (near ~0); the HUD readout is one it never
        # approached below a large floor (measured 28-42 vs 2 on-board). No threshold picked: the gap is an order
        # of magnitude.
        _self = self._self_sig()
        if _self is not None:
            _bc = None
            for o2 in a_objs:
                if frozenset(o2.get("ident") or o2["color_sig"]) == _self or frozenset(o2["color_sig"]) == _self:
                    _bc = o2["centroid"]; break
            if _bc is not None:
                for tid, t in self._tracks.items():
                    if not t["cells"]:
                        continue
                    cy = sum(y for y, _ in t["cells"]) / float(len(t["cells"]))
                    cx = sum(x for _, x in t["cells"]) / float(len(t["cells"]))
                    d = abs(_bc[0] - cy) + abs(_bc[1] - cx)
                    if d < t.get("near", 1e9):
                        t["near"] = d
        # falsify current model first
        pe = self.predict_error(before, action, after)
        self._pred += 1; self._wrong += pe
        # RECENT fidelity -- the one the licence reads. See report() for why the cumulative cannot be it.
        self._ewma = (1.0 - pe) if self._ewma is None else (0.12 * (1.0 - pe) + 0.88 * self._ewma)
        for oa, ob in self._match(a_objs, b_objs):
            _e = self._effect(oa, ob)
            # "changed" means RESTATED -- became a different thing in place. Moving is not changing (the target may
            # translate). Keyed on (identity, coarse region) NOT tid: re-segmentation (a ring flash splitting the
            # panel) mints a fresh tid, and a tid-keyed history is lost exactly when the readout does its job. The
            # two same-identity instances live in regions that persist, so (ident, region) survives the split while
            # still telling the readout-region from the lock-region apart.
            if _e[0] in ("restate", "recolor", "rotate"):
                cy = sum(y for y, _ in oa["cells"]) / float(len(oa["cells"]) or 1)
                cx = sum(x for _, x in oa["cells"]) / float(len(oa["cells"]) or 1)
                self._changed_regions.add((frozenset(oa.get("ident") or oa["color_sig"]),
                                           int(cy // 8), int(cx // 8)))
            self.table[self._key(oa, action, before, a_objs)][_e] += 1
        self._n += 1
        return dict(ok=True, predict_error=pe)

    def _rule(self, key):
        ctr = self.table.get(key)
        if not ctr:
            return None, "unseen"
        top, n = ctr.most_common(1)[0]
        rest = sum(v for e, v in ctr.items() if e != top)
        if rest >= 2 and rest >= 0.34 * n:
            return top, "contradictory"
        if n >= self.confirm_support and rest == 0:
            return top, "confirmed"
        return top, "tentative"

    def simulate(self, state, action, steps=1):
        g = np.asarray(state).copy()
        for _ in range(max(1, steps)):
            objs = self._segs(g); bg = self._bg(g); nxt = g.copy()
            for o in objs:
                # PASS THE GRID. The key now carries context (what the object is about to enter); a lookup built
                # without it is a different key and matches nothing the model learned -- the forward model would
                # silently predict "stay" for everything and score a degenerate fidelity of ~1.0.
                eff, st = self._rule(self._key(o, action, g, objs))
                if st != "confirmed" or eff is None or eff[0] == "stay":
                    continue
                cells = list(o["cells"])
                if eff[0] == "vanish":
                    for (r, c) in cells:
                        nxt[r, c] = bg
                elif eff[0] == "translate":
                    dr, dc = eff[1], eff[2]
                    for (r, c) in cells:
                        nxt[r, c] = bg
                    for (r, c) in cells:
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < g.shape[0] and 0 <= cc < g.shape[1]:
                            nxt[rr, cc] = g[r, c]
                elif eff[0] == "rotate":                    # generative 'mental rotation': spin cells about centre
                    deg = eff[1]
                    ys = [p[0] for p in cells]; xs = [p[1] for p in cells]
                    cy = (min(ys) + max(ys)) / 2.0; cx = (min(xs) + max(xs)) / 2.0
                    vals = {(r, c): g[r, c] for (r, c) in cells}
                    for (r, c) in cells:
                        nxt[r, c] = bg
                    for (r, c) in cells:
                        rr, cc = self._rotate_cell(r, c, cy, cx, deg)
                        rr, cc = int(round(rr)), int(round(cc))
                        if 0 <= rr < g.shape[0] and 0 <= cc < g.shape[1]:
                            nxt[rr, cc] = vals[(r, c)]
            g = nxt
        return g

    def predict_error(self, before, action, after):
        """Error over the ACTIVE cells: those that changed, or that we predicted would change.

        Not whole-board cell error, and the difference is the whole honesty of the measure. Whole-board error
        would let "nothing ever moves" score ~0.99 on a mostly-static board -- the model's most flattering lie.
        Scoring only the active cells inverts that: predicting nothing means pred == before, so `active` is
        exactly the cells that DID change, and every one of them is wrong -> error 1.0 -> fidelity 0.0.

        A model that says nothing scores ZERO here, not nearly-perfect. The trap was already thought about.
        """
        pred = self.simulate(before, action)
        a = np.asarray(after)
        active = (np.asarray(before) != a) | (pred != np.asarray(before))
        n = int(np.count_nonzero(active))
        return round(int(np.count_nonzero((pred != a) & active)) / n, 3) if n else 0.0

    def report(self):
        keys = list(self.table.keys())
        contra = sum(1 for k in keys if self._rule(k)[1] == "contradictory")
        conf = sum(1 for k in keys if self._rule(k)[1] == "confirmed")
        # count CONFIRMED rules that predict real MOTION (not "stay") -- a model that only ever learned "stay" has a
        # degenerate fidelity of ~1.0 (it predicts nothing changes) and must NOT be trusted for ranking.
        motion = 0
        for k in keys:
            eff, stt = self._rule(k)
            if stt == "confirmed" and eff is not None and eff[0] != "stay":
                motion += 1
        # THE LICENCE READS THE RECENT FIDELITY, NOT THE LIFETIME ONE.
        #
        # `1 - wrong/pred` is cumulative over every transition since birth. A model NECESSARILY starts wrong -- it
        # has no rules yet -- so the lifetime figure permanently carries the errors of its own learning period:
        #
        #     wrong for the first 200, then PERFECT for 100  ->  lifetime 0.333  -> REFUSED
        #     wrong for the first 200, then PERFECT for 300  ->  lifetime 0.600  -> licensed at last
        #
        # A model that becomes perfect at transition 200 must then be perfect for 300 more just to reach the gate --
        # and the agent dies every 42 actions. **The carve could be fixed and the licence would still refuse, for
        # reasons entirely about the past.** That is the same defect as pricing a carving on its lifetime hit-rate,
        # in the one number that gates everything downstream.
        #
        # The licence asks "can I plan over this NOW". The lifetime figure answers "how has this done since birth".
        # Those are different questions and only one of them is the licence's.
        #
        # Lifetime is KEPT and reported. It is a fact about the past. It must never be the gate.
        fidelity_lifetime = round(1.0 - self._wrong / self._pred, 3) if self._pred else None
        fidelity = round(self._ewma, 3) if self._ewma is not None else fidelity_lifetime
        crate = round(contra / max(1, len(keys)), 3)
        degenerate = (motion < 2)                          # learned <2 motion rules => no real dynamics captured
        ident = (crate <= 0.15) and (fidelity is None or fidelity >= 0.6) and not degenerate
        return dict(resolution="object", transitions=self._n, object_rules_confirmed=conf,
                    motion_rules=motion, degenerate=bool(degenerate), object_keys=len(keys),
                    contradiction_rate=crate, fidelity=fidelity,
                    fidelity_lifetime=fidelity_lifetime, identifiable=bool(ident))


class WorldModel:
    """Orchestrates the three inducers (pixel / logical / object), fed the SAME transitions unconditionally.
    simulate() delegates to whichever sub-model is currently the MOST FAITHFUL (the model earns trust by its
    running falsification score). report() exposes per-model readouts AND a single best-model verdict, read
    representation-relative per the doc §14 (a non-identifiable verdict is believed only once the object/logical
    lift has had its say)."""

    def __init__(self):
        self.pixel = TransitionInductionEngine()
        self.logical = LogicalTransitionInducer()
        self.object = ObjectTransitionInducer()

    def observe(self, before, action, after):
        for m in (self.pixel, self.logical, self.object):
            try:
                m.observe(before, action, after)
            except Exception:
                pass

    def _fid(self, rep):
        if (rep or {}).get("degenerate"):      # degenerate high-fidelity (learned no motion) -> never trusted
            return -1.0
        f = (rep or {}).get("fidelity")
        return f if f is not None else -1.0

    def _reports(self):
        return {"pixel": self.pixel.report(), "logical": self.logical.report(), "object": self.object.report()}

    def best(self):
        reps = self._reports()
        name = max(reps, key=lambda k: self._fid(reps[k]))
        return name, {"pixel": self.pixel, "logical": self.logical, "object": self.object}[name], reps

    def simulate(self, state, action, steps=1):
        _, model, _ = self.best()
        return model.simulate(state, action, steps=steps)

    def fidelity(self):
        _, _, reps = self.best()
        name = max(reps, key=lambda k: self._fid(reps[k]))
        return self._fid(reps[name])

    def report(self):
        name, _, reps = self.best()
        best = reps[name]
        ident = bool(best.get("identifiable"))
        return dict(best_model=name, fidelity=best.get("fidelity"), identifiable=ident,
                    per_model={k: {kk: reps[k].get(kk) for kk in ("fidelity", "contradiction_rate", "identifiable")}
                               for k in reps},
                    verdict=("identifiable-dynamics@%s" % name if ident else
                             "NON-identifiable across pixel/logical/object -- a limits wall, not a missing module"))


# ===================================================================================================
# §11 MPC / ROLLOUT SCORER -- the dense-feedback payoff. Score an abduced objective by a short GREEDY
# lookahead in the induced WorldModel: does the objective's discrepancy SHRINK under simulated action chains,
# without spending real actions? Gated by model fidelity (trust the score only when the model earns it).
# ===================================================================================================

def _ctrl_centroid(g, ctrl):
    g = np.asarray(g); cells = np.argwhere(g == ctrl)
    return (float(cells[:, 0].mean()), float(cells[:, 1].mean())) if len(cells) else None


def _gradient_probe(world, state, disc, actions, steps=4):
    """GATE #2 primitive. On-distribution, per-candidate: does disc.measure RESPOND to any simulated action along
    a short greedy path? A measure that is invariant to every action (flat where it matters) gives the scorer no
    steering signal no matter how faithful the model is. Distinguishes flat-loss from genuinely-stuck (a stuck
    measure still MOVES under actions, it just can't improve)."""
    cur = np.asarray(state).copy(); moved_any = False; probed = 0
    for _ in range(steps):
        m0 = float(disc.measure(cur)); best = m0; nxt = None
        for a in actions:
            try:
                ng = world.simulate(cur, a)
            except Exception:
                continue
            probed += 1; m1 = float(disc.measure(ng))
            if abs(m1 - m0) > 1e-9:
                moved_any = True
            if m1 < best:
                best, nxt = m1, ng
        if nxt is None:                      # nothing improved here; step forward to probe a fresh state
            if not actions:
                break
            try:
                cur = world.simulate(cur, actions[0])
            except Exception:
                break
        else:
            cur = nxt
    return dict(informative=bool(moved_any), probed=probed)


def _potential_surrogate(disc, ctrl):
    """Potential-based shaping surrogate for a FLAT measure (Ng-Harada-Russell): distance from the controllable
    to the nearest active (discrepancy-driving) cell. Gives a rankable gradient toward the region that needs
    action WITHOUT changing the true objective -- disc.measure stays the satisfaction gate; this only ranks.
    Caveat: a mis-specified active() steers wrong, so this is a heuristic, flagged shaped=True at the call site."""
    def s(g):
        g = np.asarray(g)
        try:
            act = list(disc.active(g))
        except Exception:
            act = []
        if not act:
            return 0.0
        p = _ctrl_centroid(g, ctrl) if ctrl is not None else None
        if p is None:
            return float(len(act))                 # no controllable -> fall back to count of active cells
        pr, pc = int(p[0]), int(p[1])
        return float(min(abs(pr - int(r)) + abs(pc - int(c)) for (r, c) in act))
    return s


class RolloutScorer:
    """§11 MPC scorer with TWO gates. Score an objective by simulated discrepancy-reduction ONLY when:
       gate #1 -- the world model has EARNED trust (running fidelity >= min_fidelity), AND
       gate #2 -- the discrepancy provides a usable GRADIENT (it responds to actions). If the true measure is
                  flat but a potential surrogate is available, rank on the SURROGATE (shaped) rather than fall
                  back to blind. If flat with no surrogate, emit gradient_flat and do not rank.
    A flat loss with a faithful model still yields no steering signal -- gate #2 is why fidelity alone is not
    sufficient to trust the ranking."""

    def __init__(self, min_fidelity=0.6, depth=8):
        self.min_fidelity = min_fidelity
        self.depth = depth

    def score(self, world, state, disc, actions, ctrl=None):
        fid = world.fidelity() if hasattr(world, "fidelity") else None
        init = float(disc.measure(np.asarray(state)))
        if fid is None or fid < self.min_fidelity:
            return dict(trusted=False, gate="fidelity", init=round(init, 2), best=None, reduction=None,
                        gradient_informative=None, shaped=False, path=[],
                        note="gate#1 FAIL: model fidelity %.2f < %.2f -- do NOT rank on simulation" % (fid or 0, self.min_fidelity))
        # -- gate #2: gradient informativeness --
        gp = _gradient_probe(world, state, disc, actions)
        objective = disc.measure; shaped = False
        if not gp["informative"]:
            surro = _potential_surrogate(disc, ctrl)
            # is the SURROGATE informative? (does it respond to actions?)
            class _S:                                    # lightweight disc-like wrapper for the probe
                def measure(self, g): return surro(g)
                def active(self, g):
                    try: return list(disc.active(g))
                    except Exception: return []
            if _gradient_probe(world, state, _S(), actions)["informative"]:
                objective = surro; shaped = True
            else:
                return dict(trusted=False, gate="gradient", init=round(init, 2), best=None, reduction=None,
                            gradient_informative=False, shaped=False, path=[],
                            note="gate#2 FAIL: discrepancy is FLAT and no informative surrogate -- gradient_flat, "
                                 "ranking would be noise; fall back to blind pursuit for this candidate")
        # -- greedy MPC on the chosen objective (true measure, or shaped surrogate for ranking only) --
        g = np.asarray(state).copy(); best = float(objective(g)); path = []
        for _ in range(self.depth):
            cur = float(objective(g)); cand = []
            for a in actions:
                try:
                    ng = world.simulate(g, a); cand.append((float(objective(ng)), a, ng))
                except Exception:
                    continue
            if not cand:
                break
            cand.sort(key=lambda t: t[0]); h, a, ng = cand[0]
            if h >= cur:
                break
            g = ng; path.append(a); best = min(best, h)
            if best <= 0:
                break
        true_best = float(disc.measure(g))              # report progress in the TRUE measure regardless of shaping
        return dict(trusted=True, gate="ok", init=round(init, 2), best=round(true_best, 2),
                    reduction=round(init - true_best, 2), gradient_informative=True, shaped=shaped,
                    path=[str(a) for a in path],
                    note=("simulated-satisfiable" if true_best <= 0 else
                          ("shaped-ranked (true measure flat; ranked via potential surrogate)@%.2f" % true_best if shaped
                           else "simulated-plateau@%.2f (prune before pursuing)" % true_best)))


def rank_objectives(world, state, cand_discs, actions, scorer=None, ctrl=None):
    """§11 + §5-6: score each abduced objective by simulated discrepancy-reduction (gate #1 fidelity + gate #2
    gradient), return them ranked most-promising-first, twins flagged. cand_discs: list of (descriptor, Disc).
    Meaningful only when the model is trusted AND at least one candidate has a usable (or shaped) gradient."""
    scorer = scorer or RolloutScorer()
    scored = []
    for descr, disc in cand_discs:
        s = scorer.score(world, state, disc, actions, ctrl=ctrl)
        scored.append((descr, s))

    def _sig(s):
        return (s.get("init"), tuple(s.get("path") or []), s.get("best"))
    seen = {}
    for descr, s in scored:
        seen.setdefault(_sig(s), []).append(descr)
    twins = [grp for grp in seen.values() if len(grp) > 1]
    trusted = [x for x in scored if x[1].get("trusted")]
    trusted.sort(key=lambda x: (x[1].get("best") if x[1].get("best") is not None else 1e9))
    flat = [d for d, s in scored if s.get("gate") == "gradient"]
    return dict(ranked=trusted, all=scored, twins=twins,
                trustworthy=bool(trusted),
                n_flat=len(flat), n_shaped=sum(1 for _, s in scored if s.get("shaped")),
                note=("ranked by simulated discrepancy (gates: fidelity + gradient)" if trusted else
                      "no candidate cleared both gates -> preserve blind order, pursue as before"))


def separating_probe(world, state, disc_a, disc_b, actions, depth=10):
    """§5-6 twin-separator: two objectives simulate identically; find a simulated state where their
    discrepancies DISAGREE (the state to actually drive to, to tell them apart). Returns the action path to a
    separating state, or None if none found within depth (genuinely observationally-equivalent here)."""
    from collections import deque
    g0 = np.asarray(state)
    if disc_a.measure(g0) != disc_b.measure(g0):
        return dict(separated=True, path=[], where="initial")
    q = deque([(g0, [])]); seen = {g0.tobytes()}
    while q and depth > 0:
        depth -= 0  # depth bounds path length below, not BFS breadth
        g, path = q.popleft()
        if len(path) >= 10:
            continue
        for a in actions:
            try:
                ng = world.simulate(g, a)
            except Exception:
                continue
            key = ng.tobytes()
            if key in seen:
                continue
            seen.add(key)
            if disc_a.measure(ng) != disc_b.measure(ng):
                return dict(separated=True, path=[str(x) for x in path + [a]], where="simulated")
            q.append((ng, path + [a]))
    return dict(separated=False, path=None, note="observationally-equivalent within horizon (a §5 twin wall)")


# ===================================================================================================
# §13 STATIC-PAIR SIBLING INDUCER -- classic ARC input->output transformation pairs. SEPARATE regime with a
# STRICTLY LOWER identifiability ceiling: passive (Pearl's association rung, no interventions), few-shot (below
# the sample-complexity floor without a DSL prior). Shares the local-rule language, NOT the guarantees.
# ===================================================================================================

class StaticPairInducer:
    """Induce a transformation from a few (input, output) grid pairs, then re-run on a test input. Passive,
    few-shot -- reports how UNDER-DETERMINED the induced rule is (many hidden programs may fit 2-3 pairs)."""

    def __init__(self):
        self.core = TransitionInductionEngine(neg_sample=0)   # no action; T(s)->s'
        self.n_pairs = 0

    def fit(self, pairs):
        for (inp, out) in pairs:
            self.core.observe(inp, "static", out)
            self.n_pairs += 1
        return self.report()

    def apply(self, test_input):
        return self.core.simulate(test_input, "static")

    def report(self):
        r = self.core.report(); r["regime"] = "static-passive-fewshot"; r["n_pairs"] = self.n_pairs
        r["identifiability_ceiling"] = ("LOW: passive/association-rung (Pearl), %d pairs -- likely under-"
                                        "determined; interventions unavailable" % self.n_pairs)
        return r
