# =====================================================================================================
# evolvability_engine.py  —  THE MONOLITH
# Built to spec of  composer_as_evolvability_engine.md.  One system, all organs live, no flags-off.
#
# WHERE EACH SECTION OF THE DOCUMENT LIVES (carve against this map):
#   §Part I  closed/co-option/open tiers ....... _route_three_way()  + CoOption / DirectedMint / (open=escalate)
#   §Part V  MODEL_INCOMPLETE kernel outcome .... EvolvabilityEngine.on_residual()  (fired by validate on `refuted`)
#   §14  residual reporter + active triangulate . ResidualReporter, triangulate()
#   §15  co-option = library growth .............. CoOption.propose()/promote()  (composite -> named Molecule)
#   §11  facilitated / directed mint ............. DirectedMint.propose()  (residual-parametrized instances)
#   §2,§12  cadence / EDA proposal prior ......... CadencePrior  (ranks proposals from the per-game genome + lineage)
#   §Part IV.3  blind dose-response ladder ....... DoseResponseLadder  (+ segmented-knee)
#   §7   1/5 rule radius controller .............. OneFifthController
#   §8   CUSUM speciation trigger ................ CUSUM  (== the MODEL_INCOMPLETE firing condition)
#   §13  posterior contraction + the alarm ....... PosteriorTracker  (confidence-up / generalization-down)
#   §Part V  three-gate anti-apophenia filter .... ThreeGateFilter  (falsifiability / held-out / refutation-probation)
#   §12  quality-diversity ....................... EvolvabilityEngine._qd_key()  (reward solving DIFFERENTLY)
#   §16  provable ceiling (open-atom) ............ _route_three_way() case (iii) -> escalate, NEVER mint
#
# DISCIPLINE (per the user's warning that generation >> validation here):
#   - Nothing in this file logs a WIN on a synthetic/dev run.  Internal measurements are tagged
#     "unverified-awaiting-live".  The ONLY win gate remains validate_multilevel's real levels_completed++.
#   - MINT is never a new measure-function authored at runtime (that is the open-atom apophenia the doc forbids).
#     MINT = new *instance* of an existing, tested discrepancy kind, parametrised to the residual.
#     CO-OPTION = *composite* (AND/OR/SEQ) of existing atomics, promoted to a named Molecule on generalisation.
#   - Composer primitives (compile_*, descend, pursue) are INJECTED (dependency injection) to avoid the
#     circular import with objective_validator and to mirror the kernel's compose_fn/pursue_fn philosophy.
# =====================================================================================================
import math
import numpy as np
from collections import Counter, defaultdict, deque

try:
    from effect_classifier import effect_signature            # §14 residual feature vocabulary
except Exception:
    def effect_signature(a, b):
        a = np.asarray(a); b = np.asarray(b)
        ch = np.argwhere(a != b)
        return dict(type=("noop" if ch.size == 0 else "change"), n=int(len(ch)),
                    centroid=(tuple(ch.mean(0)) if ch.size else None),
                    added=(), removed=(), bbox=None)

try:
    from object_seg import segment_objects
except Exception:
    segment_objects = None

# THE BOARD IS NOT AN OBJECT.
# forward_predict segmented with a single background colour -- the modal one, which on a maze is the FLOOR. The walls
# stayed foreground, a maze's walls are one connected structure, and so every residual's correlates were computed
# against a single 1451-pixel blob spanning 42% of the board. A blob that size correlates with everything above the
# 0.15 shadow threshold, so triangulate() ALWAYS returned a shadow, so _route_three_way ALWAYS chose co-opt -- and
# the MINT branch was structurally unreachable. 84 routings, 0 mints, all session.
#
# The mint route was never blocked because minting is hard. It was blocked because the carve was wrong.
# Injected rather than guessed: the composer knows the terrain and narrates it on every run.
TERRAIN = set()


def _bg(g):
    g = np.asarray(g)
    return int(np.bincount(g.ravel()).argmax()) if g.size else 0


# =====================================================================================================
# GRAMMAR VOCABULARY BRIDGE  —  the engine speaks the composer's advanced grammar (words + deep_form),
# never raw tuples, so every creation is legible in the same language as the rest of the system.
# =====================================================================================================
def _rel_words(rel):
    """Plain-language gloss for a relation/predicate, from the grammar's own PREDICATES table."""
    try:
        import objective_grammar as G
        p = G.PREDICATES.get(rel)
        if p is not None:
            return p.gloss
        e = G.explain(rel)
        if e.get("words") and "unknown" not in e["words"]:
            return e["words"]
    except Exception:
        pass
    return {"MATCH": "make sameness", "COLLECT": "remove every item of a kind",
            "BE_AT": "be located at a target position", "SAME": "match the target"}.get(rel, rel)


def _spec_grammar(spec):
    """Render a spec in the QUANTIFIER/RELATION deep-form language the composer uses to explain itself."""
    if isinstance(spec, tuple) and spec and isinstance(spec[0], str) and spec[0] in ("AND", "OR", "SEQ"):
        joiner = {"AND": " AND ", "OR": " OR ", "SEQ": " THEN "}[spec[0]]
        return joiner.join(_spec_grammar(s) for s in spec[1:])
    if isinstance(spec, tuple) and spec:
        rel = spec[0]
        tgt = spec[1] if len(spec) > 1 else ""
        return f"{rel}(o, {tgt})"
    return str(spec)


def _spec_words(spec):
    """Plain-language reading of a spec, composing the constituent relation glosses."""
    if isinstance(spec, tuple) and spec and isinstance(spec[0], str) and spec[0] in ("AND", "OR", "SEQ"):
        joiner = {"AND": " and also ", "OR": " or ", "SEQ": ", then "}[spec[0]]
        return joiner.join(_spec_words(s) for s in spec[1:])
    if isinstance(spec, tuple) and spec:
        return f"\u27e8{_rel_words(spec[0])}\u27e9"
    return str(spec)


# =====================================================================================================
# FORWARD MODEL (RF1 fix)  —  the residual is PREDICTION ERROR across an objective-keyed buffer, not a
# single-frame diff. Establish per-object motion from the earlier transitions, extrapolate to predict the
# last frame, and the residual is where reality deviated from that prediction (the "vanished on push 3" event).
# Robust centroid-velocity model on the object_seg substrate; TAGGED so the proctor sees which mode fired.
# =====================================================================================================
def _match_objs(a_objs, b_objs, max_d=6.0):
    """Greedy nearest-centroid match between two object lists (same-ish colour/size preferred)."""
    pairs = []
    used = set()
    for oa in a_objs:
        best, bd = None, max_d
        for j, ob in enumerate(b_objs):
            if j in used:
                continue
            d = ((oa["centroid"][0] - ob["centroid"][0]) ** 2 + (oa["centroid"][1] - ob["centroid"][1]) ** 2) ** 0.5
            if d < bd:
                best, bd = j, d
        if best is not None:
            used.add(best); pairs.append((oa, b_objs[best]))
    return pairs


def forward_predict(buffer):
    """buffer = list of grids [g_{t-N} ... g_t]. Predict g_t from the motion established over g_{t-N..t-1}
    (constant-velocity extrapolation per object). Returns (predicted_grid, model_tag). Falls back to a
    persistence model ('no change') when no motion can be established -> tag records which."""
    if segment_objects is None or len(buffer) < 3:
        return (np.asarray(buffer[-2]) if len(buffer) >= 2 else np.asarray(buffer[-1])), "diff-fallback"
    frames = [np.asarray(g) for g in buffer]
    g_prev, g_last = frames[-2], frames[-1]
    if g_prev.shape != g_last.shape:
        return g_prev, "diff-fallback"
    bg = _bg(g_last)
    # establish per-object velocity from the two transitions before the last
    try:
        _ign = set(int(c) for c in TERRAIN) or None
        o_a = [o for o in segment_objects(frames[-3], bg=bg, ignore_colors=_ign) if o["size"] >= 1]
        o_b = [o for o in segment_objects(g_prev, bg=bg, ignore_colors=(set(int(c) for c in TERRAIN) or None)) if o["size"] >= 1]
    except Exception:
        return g_prev, "diff-fallback"
    vel = {}
    for oa, ob in _match_objs(o_a, o_b):
        dv = (ob["centroid"][0] - oa["centroid"][0], ob["centroid"][1] - oa["centroid"][1])
        vel[id(ob)] = (int(round(dv[0])), int(round(dv[1])), ob)
    if not any((abs(v[0]) + abs(v[1])) > 0 for v in vel.values()):
        return g_prev, "persistence"                    # nothing was moving -> predict no change
    # extrapolate: MOVE each moving object (erase its old cells, stamp at old+velocity); non-movers persist.
    pred = np.asarray(g_prev).copy()
    moved_any = False
    for (dr, dc, ob) in vel.values():
        if not (dr or dc):
            continue
        moved_any = True
        for (r, c) in ob["cells"]:
            pred[r, c] = bg                             # erase old position
    for (dr, dc, ob) in vel.values():
        if not (dr or dc):
            continue
        for (r, c) in ob["cells"]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < pred.shape[0] and 0 <= nc < pred.shape[1]:
                pred[nr, nc] = g_prev[r, c]             # stamp at extrapolated position
    return pred, ("forward-model" if moved_any else "persistence")


# =====================================================================================================
# §14  RESIDUAL REPORTER  —  the unexplained-prediction-error signal as a first-class object.
# =====================================================================================================
class Residual:
    """A characterised anomaly: what changed that no active primitive predicted, in effect_classifier's
    vocabulary, plus the correlates that let §15 route it (mint / co-opt / escalate)."""
    __slots__ = ("cells", "colors", "centroid", "bbox", "effect_type", "correlates",
                 "reproduced", "representable", "raw")

    def __init__(self, cells=(), colors=(), centroid=None, bbox=None, effect_type="unknown",
                 correlates=None, reproduced=1, representable=True, raw=None):
        self.cells = tuple(cells); self.colors = tuple(colors); self.centroid = centroid
        self.bbox = bbox; self.effect_type = effect_type
        self.correlates = correlates or {}          # primitive/feature -> correlation strength (the "shadow")
        self.reproduced = int(reproduced)           # how many times this same residual has recurred (CUSUM feeds this)
        self.representable = bool(representable)     # False -> §16 case (iii), the true ceiling
        self.raw = raw

    def key(self):
        return (self.effect_type, self.colors, self.bbox)


class ResidualReporter:
    """§14. From the composer's satisfied-but-unrewarded evidence + before/after frames, characterise the
    residual and log the correlates it (a) resists explanation by, (b) co-occurs with, (c) follows."""

    def __init__(self):
        self.log = []                               # append-only anomaly log (observe-only, for the proctor)

    def report(self, g_before, g_after, satisfied_atomics, active_primitive_traces, buffer=None):
        """RF1: residual = PREDICTION ERROR of the active dynamics across an objective-keyed buffer, not a
        single-frame diff. buffer = list of grids for the CURRENT objective (reset at each decision point).
        Falls back to the g_before/g_after diff only when no buffer is available; the mode is tagged."""
        buffer = list(buffer) if buffer else []
        if len(buffer) >= 3:
            predicted, mode = forward_predict(buffer)
            actual = np.asarray(buffer[-1])
            if predicted.shape != actual.shape:
                predicted, mode = np.asarray(buffer[-2]), "diff-fallback"
            ch = np.argwhere(actual != predicted)
            base_before, base_after = np.asarray(buffer[-2]), actual
        else:
            mode = "diff-fallback"
            base_before, base_after = np.asarray(g_before), np.asarray(g_after)
            ch = np.argwhere(base_before != base_after)
        if ch.size == 0:
            # the world matched the forward model exactly -> the reward tracks something UNPERCEIVED.
            res = Residual(effect_type="invisible", representable=False, raw=dict(mode=mode))
        else:
            cells = tuple(map(tuple, ch.tolist()))
            colors = tuple(sorted(set(int(base_after[r, c]) for r, c in ch) |
                                  set(int(base_before[r, c]) for r, c in ch)))
            r0, c0 = ch.min(0); r1, c1 = ch.max(0)
            res = Residual(cells=cells, colors=colors,
                           centroid=(float(ch[:, 0].mean()), float(ch[:, 1].mean())),
                           bbox=(int(r0), int(r1), int(c0), int(c1)),
                           effect_type="prediction-error" if mode == "forward-model" else "change",
                           raw=dict(mode=mode))
        res.correlates = self._correlates(res, base_before, active_primitive_traces)
        self.log.append(dict(kind="residual", key=res.key(), mode=mode, correlates=res.correlates,
                             representable=res.representable, status="unverified-awaiting-live"))
        return res

    def _correlates(self, res, g_before, traces):
        """Triangulation input: features whose signal co-locates with the residual, read on the BEFORE-state.

        This used to take `g_after` and segment it. Changing the body to read `g_before` was not enough and the
        import-time bound said so: a function that is HANDED the outcome can read the outcome, and the next edit
        will. The parameter is gone. The predicate builder is now structurally unable to see what happened -- which
        is the only version of this constraint that survives contact with a future change.

        Don't look becomes can't look. That is the difference between a convention and a bound.
        """
        cor = {}
        if not res.cells:
            return cor
        rc = set(res.cells)
        # feature 1: does any active primitive's trace touch the residual cells? (co-occurrence)
        for name, cells in (traces or {}).items():
            if not cells:
                continue
            overlap = len(rc & set(map(tuple, cells)))
            if overlap:
                cor[("primitive", name)] = overlap / max(1, len(rc))
        # feature 2: object-structure the residual sits in -- READ ON THE BEFORE-STATE.
        #
        # This segmented `g_after`. The residual IS the change, so asking which after-state object contains the
        # changed cells asks the outcome to explain itself: the object is partly CONSTITUTED by the residual it is
        # being credited with. That is "the block moved because the block moved" with a segmentation in front of it.
        #
        # Measured, not argued. An MDL sweep over a predicate family on a synthetic residual:
        #     [TAUTOLOGY] "did it move"          |phi|=36   R|phi=0.0    gain +189.7   <- WINS
        #     ctx: colour at centroid+delta      |phi|=52   R|phi=0.0    gain +173.7   <- the truth
        #     step parity / step mod 3 / row / col / n-walls              all NEGATIVE  <- correctly rejected
        # A predicate that reads the outcome compresses the residual to ZERO bits, so it beats every real regularity,
        # systematically, forever. MDL alone does not save you. The before-state constraint does.
        #
        # A shadow must be cast by something that was ALREADY THERE.
        if segment_objects is not None:
            try:
                bg = _bg(g_before)
                for o in segment_objects(g_before, bg=bg, ignore_colors=(set(int(c) for c in TERRAIN) or None)):
                    ov = len(rc & set(map(tuple, o["cells"])))
                    if ov:
                        cor[("object", o.get("color", "?"), o["size"])] = ov / max(1, len(rc))
            except Exception:
                pass
        return cor


# =====================================================================================================
# §14  ACTIVE TRIANGULATION  +  §15/§Part-I  THREE-WAY ROUTER
# =====================================================================================================
def triangulate(residual, min_shadow=0.15):
    """§14. Bound where the hidden dynamic lives by the shadow it casts across measurable features.
    Returns the shadow-casting handles (correlates above threshold). Empty -> no shadow -> §16 case (iii)."""
    return {k: v for k, v in residual.correlates.items() if v >= min_shadow}


def _route_three_way(residual, shadow):
    """§Part-I / §15.  (i) representable residual -> MINT ; (ii) shadow across existing primitives -> CO-OPT ;
    (iii) no shadow / not representable -> ESCALATE (true ceiling, §16; NEVER mint — that is apophenia)."""
    if shadow:
        return "co-opt", shadow                      # (ii) reachable: recompose the shadow-casters
    if residual.representable and residual.cells:
        return "mint", None                          # (i) representable residual -> parametrised new instance
    return "escalate", None                          # (iii) B1 ceiling: report for perceptual enrichment


# =====================================================================================================
# §11  DIRECTED MINT  —  residual-parametrised new INSTANCE of an existing (tested) kind. Facilitated,
#                        not open-atom: the residual structures where the proposal lands.
# =====================================================================================================
class DirectedMint:
    def propose(self, residual, ctrl, g0, compile_objective, compile_discrepancy):
        """Return candidate discs aimed at the residual, built ONLY from existing kinds with new params."""
        out = []
        if residual.centroid is not None:
            r, c = int(round(residual.centroid[0])), int(round(residual.centroid[1]))
            # BE_AT the residual locus (drive the controllable onto where reward-linked change happened)
            for spec in (("BE_AT", ("cell", r, c)),):
                d = self._try(compile_objective, spec, ctrl, g0)
                if d is not None:
                    out.append((f"MINT.BE_AT@{(r,c)}", spec, d))
        for col in residual.colors:
            # MATCH / target the residual colour (the reward may track a colour the satisfied rule ignored)
            for rel in ("MATCH", "COLLECT"):
                d = self._disc(compile_discrepancy, rel, ctrl, (col,), g0)
                if d is not None:
                    out.append((f"MINT.{rel}(col={col})", (rel, (col,)), d))
        return out

    def _try(self, compile_objective, spec, ctrl, g0):
        try:
            d = compile_objective(spec, ctrl, g0)
            return d if d.measure(g0) > 0 else None
        except Exception:
            return None

    def _disc(self, compile_discrepancy, rel, ctrl, tc, g0):
        try:
            d = compile_discrepancy(rel, ctrl, tc, g0)
            return d if d.measure(g0) > 0 else None
        except Exception:
            return None


# =====================================================================================================
# §15  CO-OPTION  —  compose shadow-casting atomics into a composite; promote the winner to a named
#                    Molecule (DreamCoder-style library growth). This is the reachable, high-value organ.
# =====================================================================================================
class CoOption:
    def __init__(self):
        self.promoted = {}                          # composite-signature -> Molecule name (per-game library growth)

    def propose(self, shadow, atomics, residual, ctrl, g0, compile_objective):
        """Build composite objectives (AND/OR/SEQ) over the atomics implicated by the shadow + the residual."""
        # atomics implicated by the shadow (co-option recruits signals ALREADY present, §15 floor)
        names = {n for (t, n, *_) in [k if isinstance(k, tuple) else (k,) for k in shadow]
                 if t == "primitive"} if shadow else set()
        base = [(h, d) for (h, d) in atomics if h.get("descriptor") in names]
        # co-option recruits the shadow-caster AND composes it with other available atomics (needs >=2 to compose)
        if len(base) < 2:
            extra = [x for x in atomics if x not in base]
            base = base + extra[:max(0, 2 - len(base)) + 1]
        base = base[:4]
        out = []
        for i in range(len(base)):
            for j in range(len(base)):
                if i == j:
                    continue
                a, b = base[i][0], base[j][0]
                if a.get("target_color") is None or b.get("target_color") is None:
                    continue
                for op in ("AND", "SEQ"):            # AND = both hold ; SEQ = order matters (a then b)
                    spec = (op, (a["relation"], a["target_color"]), (b["relation"], b["target_color"]))
                    try:
                        d = compile_objective(spec, ctrl, g0)
                    except Exception:
                        continue
                    if d.measure(g0) > 0:
                        out.append((f"COOPT.{op}({a['relation']},{b['relation']})", spec, d))
        return out

    def promote(self, sig, spec):
        """§15 library growth: a composite that GENERALISED under refutation becomes a first-class Molecule,
        spoken in the grammar's own vocabulary (gloss + deep_form composed from its constituent relations)."""
        try:
            import objective_grammar as G
            name = f"COOPT_{len(self.promoted)+1}"
            primes = tuple(x for x in _spec_primes(spec) if x in getattr(G, "ALL_PRIMES", set()))
            gloss = _spec_words(spec)                                   # plain words, composed
            deep = f"ALL(o in OBJECT: {_spec_grammar(spec)})"          # deep-form in the composer's language
            if hasattr(G, "_addmol"):
                G._addmol(name, gloss, primes or ("REACH",), deep)     # the grammar's own library-growth call
            else:
                G.MOLECULES[name] = G.Molecule(name, gloss, primes or ("REACH",), deep)
            self.promoted[sig] = dict(name=name, words=gloss, deep_form=deep, spec=spec)
            return dict(name=name, words=gloss, deep_form=deep)
        except Exception:
            return None


def _spec_primes(spec):
    out = []
    def walk(s):
        if isinstance(s, tuple) and s and isinstance(s[0], str) and s[0] in ("AND", "OR", "SEQ"):
            for sub in s[1:]:
                walk(sub)
        elif isinstance(s, tuple) and s:
            out.append(s[0])
    walk(spec)
    return out


# =====================================================================================================
# §2,§12  CADENCE / EDA PROPOSAL PRIOR  —  rank proposals by the per-game genome + version lineage.
#          (Perfect-memory EDA: fit an EXACT distribution over what has confirmed vs refuted, §12.)
# =====================================================================================================
class CadencePrior:
    def __init__(self):
        self.confirmed = Counter()                  # relation/op -> times it generalised (per game)
        self.refuted = Counter()                    # relation/op -> times it was evicted
        self.axis_history = []                       # ordered log of which axis was tried (cadence)

    def observe(self, tag, ok):
        (self.confirmed if ok else self.refuted)[tag] += 1
        self.axis_history.append((tag, ok))

    def rank(self, proposals):
        """Higher score first. EDA: proposals resembling confirmed lineage rank up; refuted rank down."""
        def score(p):
            tag = _proposal_tag(p)
            return (self.confirmed[tag] - self.refuted[tag], -len(str(p[0])))
        return sorted(proposals, key=score, reverse=True)


def _proposal_tag(p):
    label = p[0]
    return label.split("(")[0].split("@")[0].split(".")[-1]


# =====================================================================================================
# §Part IV.3  BLIND DOSE-RESPONSE LADDER  +  segmented-knee  (pre-committed, single-axis, uncontaminated)
# =====================================================================================================
class DoseResponseLadder:
    """Emit a pre-committed spread of increasing mutation-distance (1 atomic, 2, 3, ...). Generated BEFORE
    any result is seen (§Part IV.3): the FAILURES are the instrument that locates the diminishing-returns knee."""

    def build(self, ranked_proposals, max_rungs=5):
        return list(ranked_proposals[:max_rungs])    # each rung = one further step along the ranked axis

    @staticmethod
    def knee(survival):
        """survival: list of bools per rung (in order). Return the rung index just past the last survivor."""
        last_ok = -1
        for i, ok in enumerate(survival):
            if ok:
                last_ok = i
        return last_ok + 1                           # radius cap for the NEXT round


# =====================================================================================================
# §7  RECHENBERG 1/5 RULE  —  survival rate self-tunes the mutation radius.
# =====================================================================================================
class OneFifthController:
    def __init__(self, radius=3, c=1.3, lo=1, hi=8):
        self.radius = radius; self.c = c; self.lo = lo; self.hi = hi

    def update(self, n_survived, n_tested):
        if n_tested <= 0:
            return self.radius
        rate = n_survived / n_tested
        if rate > 0.2:
            self.radius = min(self.hi, self.radius * self.c)     # too timid -> widen
        elif rate < 0.2:
            self.radius = max(self.lo, self.radius / self.c)     # overshooting -> shrink
        return int(round(self.radius))


# =====================================================================================================
# §8  CUSUM CHANGE-POINT  ==  the MODEL_INCOMPLETE / speciation trigger (stable, reproduced residual;
#      NOT a one-off flicker -> that would be pareidolia).
# =====================================================================================================
class CUSUM:
    def __init__(self, K=0.5, h=2.0):
        self.K = K; self.h = h; self.S = 0.0

    def push(self, surprise):
        self.S = max(0.0, self.S + (surprise - self.K))
        return self.S > self.h                       # True -> speciation: the regime changed, MINT is licensed

    def reset(self):
        self.S = 0.0


# =====================================================================================================
# §13  POSTERIOR CONTRACTION TRACKER  +  the one alarm: confidence-up / generalisation-down.
# =====================================================================================================
class PosteriorTracker:
    def __init__(self):
        self.live = set()                           # live hypothesis handles (the version space)
        self.history = []                           # (n_live, held_out_accuracy)

    def note(self, n_live, held_out_accuracy):
        self.history.append((int(n_live), float(held_out_accuracy)))

    def alarm(self):
        """§13: contraction (n_live falling) WITH held-out accuracy also falling = overfitting in the costume
        of convergence. Returns True when the confidence-up/generalisation-down divergence is detected."""
        if len(self.history) < 3:
            return False
        (n0, a0), (n1, a1) = self.history[-3], self.history[-1]
        contracting = n1 < n0
        generalisation_dropping = a1 < a0 - 1e-6
        return bool(contracting and generalisation_dropping)


# =====================================================================================================
# §Part V  THREE-GATE ANTI-APOPHENIA FILTER  —  falsifiability / held-out / refutation-on-probation.
# =====================================================================================================
class ThreeGateFilter:
    def falsifiable(self, disc, g0):
        """Gate 1: must make a RISKY prediction — not trivially satisfied, not vacuously true."""
        try:
            m = disc.measure(g0)
            return (m is not None) and (m > 0) and (m != float("inf"))
        except Exception:
            return False

    def held_out(self, disc, held_levels):
        """Gate 2 (RF2, corrected): LEVEL-SPLIT held-out, three-state — the private set varies by LEVEL, not by
        frame, so a temporal frame-split would measure the wrong thing. held_levels = archived frame-sequences
        from previously-solved levels. Returns 'pass' (predicts a held-out level), 'fail' (contradicts one), or
        'unproven' (no held-out level yet -> refutation-on-probation carries it; NOT a pass)."""
        if not held_levels:
            return "unproven"
        seen = 0; held = 0
        for frames in held_levels:
            for g in frames:
                try:
                    m = disc.measure(g)
                except Exception:
                    continue
                if m is None:
                    continue
                seen += 1
                if m > 0:                                 # the discrepancy still applies on the held-out level
                    held += 1
        if seen == 0:
            return "unproven"
        return "pass" if held >= max(1, seen // 2) else "fail"

    # Gate 3 (refutation-on-probation) is the ledger + GROWTH_CANDIDATES: enforced by the engine on promotion.


# =====================================================================================================
# NARRATOR  —  explains, in the composer's advanced grammar, WHY the engine creates what it creates, so
# the proctor (you and I) can process each change as it happens during the game. Legibility is the thesis.
# =====================================================================================================
class Narrator:
    def residual(self, res, satisfied_rel=None):
        sat = f"objective \u27e8{_rel_words(satisfied_rel)}\u27e9 was SATISFIED but produced NO reward; " if satisfied_rel else ""
        where = f" over {res.bbox}" if res.bbox else ""
        cols = f" in colours {list(res.colors)}" if res.colors else ""
        return (f"MODEL_INCOMPLETE: {sat}residual = a '{res.effect_type}' change{where}{cols} that no active "
                f"prime predicts (seen \u00d7{res.reproduced}).")

    def speciation(self, res):
        return (f"SPECIATION (\u00a78 CUSUM): this residual is stable and reproduced (\u00d7{res.reproduced}) \u2014 the "
                f"regime changed, so minting is licensed; this is not a one-off flicker (not pareidolia).")

    def route(self, route, res, shadow):
        if route == "co-opt":
            handles = ", ".join(self._handle(h) for h in list(shadow)[:4])
            return (f"ROUTE \u2192 CO-OPT (\u00a715): the residual casts a shadow on [{handles}] \u2014 signals ALREADY in the "
                    f"grammar. Recomposing them into a new composite 'organ'; the reward tracks a combination the "
                    f"grammar holds only as separate atoms. Not a new atom \u2014 a new arrangement of existing ones.")
        if route == "mint":
            loc = f" at {tuple(int(x) for x in res.centroid)}" if res.centroid else ""
            return (f"ROUTE \u2192 MINT (\u00a711 facilitated): the residual is representable{loc} but casts no composite "
                    f"shadow. Proposing a residual-parametrised INSTANCE of an existing predicate \u2014 a new instance, "
                    f"not a new kind.")
        return ("ROUTE \u2192 ESCALATE (\u00a716 ceiling): the residual casts NO shadow on any prime and is not "
                "representable \u2014 a perception gap. Reporting it for richer perception; NOT minting, because minting "
                "into a dimension we cannot perceive would be apophenia (a hallucinated atom).")

    def proposal(self, label, spec):
        kind = "co-opt" if label.startswith("COOPT") else "mint"
        if kind == "co-opt":
            return f"  \u2022 {label}: require {_spec_words(spec)} \u2014 formally {_spec_grammar(spec)}."
        return f"  \u2022 {label}: {_spec_words(spec)} aimed at the residual \u2014 drive the controllable onto where the reward-linked change occurred."

    def drive(self, label, ok):
        return f"  \u2192 tried {label}: {'HELD (unverified-awaiting-live)' if ok else 'refuted'}."

    def promote(self, info):
        return (f"PROMOTE {info['name']} \u2192 library (\u00a715 growth): the composite generalised under refutation. "
                f"Added as a first-class Molecule \u2014 \u27e8{info['words']}\u27e9, formally {info['deep_form']}. "
                f"The grammar is now richer by one organ.")

    def alarm(self):
        return ("\u26a0 ALARM (\u00a713): the version-space is contracting WHILE held-out accuracy falls \u2014 confidence up, "
                "generalisation down. Narrowing is overfitting in the costume of convergence; recheck before trusting these survivors.")

    def escalate(self, res):
        cor = ", ".join(self._handle(h) for h in list(res.correlates)[:4]) or "none"
        return (f"ESCALATION logged (\u00a716 case iii): unexplained '{res.effect_type}' residual, correlates=[{cor}]. "
                f"This is a request to enrich perception, not a failure \u2014 the ceiling is real and it is HERE.")

    def _handle(self, h):
        if isinstance(h, tuple) and h and h[0] == "primitive":
            return f"prime {h[1]}"
        if isinstance(h, tuple) and h and h[0] == "object":
            return f"object(colour {h[1]}, size {h[2]})"
        return str(h)



class EvolvabilityEngine:
    def __init__(self):
        self.reporter = ResidualReporter()          # §14
        self.mint = DirectedMint()                  # §11
        self.coopt = CoOption()                     # §15
        self.prior = CadencePrior()                 # §2,§12
        self.ladder = DoseResponseLadder()          # §IV.3
        self.radius = OneFifthController()          # §7
        self.cusum = CUSUM()                        # §8
        self.posterior = PosteriorTracker()         # §13
        self.gate = ThreeGateFilter()               # §Part V
        self.narrator = Narrator()                  # grammar-legible self-explanation
        self.narration = []                          # human-readable running account (for you and me, live)
        self.residual_counts = Counter()            # reproduction counter (feeds CUSUM stability)
        self.escalations = []                        # §16 case (iii): gaps to report, NEVER minted
        self.behavior_archive = {}                   # §12 quality-diversity: descriptor -> best handle
        self.held_out_levels = []                    # RF2: archived frame-sequences from solved levels (level-split)
        self.events = []                             # observe-only trace (all "unverified-awaiting-live")

    def archive_level(self, frames):
        """RF2: bank a solved level's frames as a held-out generalisation set for Gate 2 (level-split)."""
        frames = [np.asarray(g) for g in (frames or []) if g is not None]
        if len(frames) >= 2:
            self.held_out_levels.append(frames[-8:])         # a sample suffices for a predictive test
            self.held_out_levels = self.held_out_levels[-6:] # bound memory

    def _qd_key(self, residual):
        # §12 MAP-Elites descriptor: solve DIFFERENTLY -> spread across effect-type x locus, not just score
        cx = None if residual.centroid is None else (int(residual.centroid[0]) // 8, int(residual.centroid[1]) // 8)
        return (residual.effect_type, cx)

    def on_residual(self, ctx):
        """FIRED by validate() when the grammar is satisfied-but-unrewarded (== MODEL_INCOMPLETE, §Part V).
        ctx (injected, no circular import) must provide:
          g0, ctrl, refuted (list of (h,disc)), atomics (list of (h,disc)),
          g_before, g_after, active_traces (name->cells),
          compile_objective, compile_discrepancy, descend, pursue, adapter, budget, held_grids (optional)
        RETURNS a winning result dict (drives the scored path) or None. NEVER logs a synthetic win."""
        self.fired = getattr(self, "fired", 0) + 1                 # unambiguous: engine was TRIGGERED (refuted seen)
        self.events.append(dict(phase="engine-fired", n=self.fired, refuted=len(ctx.get("refuted") or []),
                                status="unverified-awaiting-live"))
        try:
            return self._on_residual(ctx)
        except Exception as e:
            self.events.append(dict(phase="engine-error", err=str(e)[:160], status="unverified-awaiting-live"))
            return None

    def _on_residual(self, ctx):
        g0 = ctx["g0"]; ctrl = ctx["ctrl"]
        def _say(line):
            self.narration.append(line)
        # ---- §14 report the residual (RF1: forward-model prediction error over the objective-keyed buffer) --
        res = self.reporter.report(ctx.get("g_before", g0), ctx.get("g_after", g0),
                                   ctx.get("refuted", []), ctx.get("active_traces", {}),
                                   buffer=ctx.get("buffer"))
        self.residual_counts[res.key()] += 1
        res.reproduced = self.residual_counts[res.key()]
        sat_rel = None
        _rf = ctx.get("refuted", [])
        if _rf:
            try: sat_rel = _rf[0][0].get("relation")
            except Exception: sat_rel = None
        _say(self.narrator.residual(res, sat_rel))
        # ---- §8 CUSUM: only a STABLE, reproduced residual licenses minting (else it is noise/pareidolia) --
        speciate = self.cusum.push(1.0 if res.reproduced >= 1 else 0.0)
        if speciate:
            _say(self.narrator.speciation(res))
        # ---- §14 triangulate -> §15 three-way route ------------------------------------------------
        shadow = triangulate(res)
        route, handle = _route_three_way(res, shadow)
        _say(self.narrator.route(route, res, shadow))
        self.events.append(dict(phase="route", route=route, residual=res.key(), reproduced=res.reproduced,
                               speciate=bool(speciate), why=self.narration[-1], status="unverified-awaiting-live"))
        if route == "escalate":
            # §16 case (iii): no shadow, not representable -> REPORT for perceptual enrichment; DO NOT mint.
            _say(self.narrator.escalate(res))
            self.escalations.append(dict(residual=res.key(), correlates=res.correlates,
                                        why=self.narration[-1],
                                        note="representation gap — enrich perception; minting here would be apophenia"))
            return None

        # ---- assemble proposals. §15: co-option is PREFERRED when the residual casts a shadow (recomposable);
        #      §11 directed mint is the representable-residual fallback. -----------------------------------
        compile_objective = ctx["compile_objective"]; compile_discrepancy = ctx["compile_discrepancy"]
        coopt_props = self.coopt.propose(shadow, ctx.get("atomics", []), res, ctrl, g0, compile_objective) if route == "co-opt" else []
        mint_props = self.mint.propose(res, ctrl, g0, compile_objective, compile_discrepancy)
        if not (coopt_props or mint_props):
            return None
        # §2,§12 EDA prior ranks WITHIN each group; co-option composites lead, mint instances follow.
        ranked = self.prior.rank(coopt_props) + self.prior.rank(mint_props)
        rungs = self.ladder.build(ranked, max_rungs=max(1, int(self.radius.radius)))  # §IV.3 blind pre-committed ladder
        for label, spec, _ in rungs:
            _say(self.narrator.proposal(label, spec))

        # ---- DRIVE (scored): test the whole pre-committed ladder; failures are the instrument (§IV.3) ----
        descend = ctx["descend"]; pursue = ctx["pursue"]; adapter = ctx["adapter"]; budget = ctx.get("budget", 1500)
        held = ctx.get("held_grids", []) or self.held_out_levels     # RF2: level-split held-out sets
        survival = []
        gate2_seen = 0; gate2_pass = 0                                # RF2: real generalisation ground truth
        winner = None
        for label, spec, disc in rungs:
            # §Part-V gate 1 (falsifiability) before spending actions
            if not self.gate.falsifiable(disc, g0):
                survival.append(False); self.prior.observe(_proposal_tag((label,)), False); continue
            gate2 = self.gate.held_out(disc, held)                    # 'pass' | 'fail' | 'unproven'
            if gate2 in ("pass", "fail"):
                gate2_seen += 1; gate2_pass += (gate2 == "pass")
            # RIDE THE GRAMMAR WHY ON THE REAL ACTIONS (free lane): set the adapter's reasoning to THIS rung's
            # rationale; the first action descend/pursue emits is flagged decision_point, the rest carry the same
            # why. Rides GameAction.reasoning — no ghost action, no environment effect, no residual contamination.
            if hasattr(adapter, "set_reasoning"):
                try:
                    adapter.set_reasoning(dict(engine="evolvability", route=route, label=label,
                                               grammar=_spec_grammar(spec), residual=list(res.key()),
                                               gate2=gate2, why=self.narrator.proposal(label, spec).strip()))
                except Exception:
                    pass
            r = descend(adapter, disc, ctrl, budget=min(budget, 300), patience=120,
                        reset_first=not getattr(adapter, "level_local", False))
            if not r.get("validated"):
                r = pursue(adapter, disc, budget=min(budget, 1200))
            ok = bool(r.get("validated"))
            survival.append(ok and gate2 != "fail")                  # held-out FAIL disqualifies a survivor
            self.prior.observe(_proposal_tag((label,)), ok)                       # §2 cadence update
            _say(self.narrator.drive(label, ok))
            self.events.append(dict(phase="drive", label=label, validated=ok, gate2=gate2, why=self.narration[-1],
                                    status="unverified-awaiting-live"))            # NEVER a 'win' on dev
            if ok:
                # §15 promote a CO-OPTion composite ONLY on a real held-out PASS (RF2). 'unproven' -> probation
                # (the ledger carries it across levels); 'fail' is never promoted.
                if label.startswith("COOPT") and gate2 == "pass":
                    info = self.coopt.promote(label, spec)
                    if info:
                        _say(self.narrator.promote(info))
                        self.events.append(dict(phase="promote", molecule=info, gate2=gate2, why=self.narration[-1],
                                                status="unverified-awaiting-live"))
                elif label.startswith("COOPT"):
                    self.events.append(dict(phase="probation", label=label, gate2=gate2,
                                            note="won but held-out=" + gate2 + " -> GROWTH_CANDIDATES probation, not promoted",
                                            status="unverified-awaiting-live"))
                # §12 quality-diversity archive: keep the winner that solves THIS behavior-cell
                self.behavior_archive[self._qd_key(res)] = label
                winner = dict(validated=label, won_relation=(spec[0] if isinstance(spec, tuple) else "COMPOSED"),
                              engine="evolvability", detail=r, source="+evolvability", spec=spec,
                              why=" | ".join(self.narration[-4:]))
                break

        # ---- §7 retune radius from the survival curve; §IV.3 knee bounds next round --------------------
        self.radius.update(sum(1 for s in survival if s), len(survival))
        self._knee = self.ladder.knee(survival)
        # ---- §13 posterior: held-out accuracy is the Gate-2 PASS RATE (real generalisation ground truth, RF2),
        #      NOT raw survival/score. Only with real ground truth does the confidence/generalisation alarm mean
        #      anything; on level 1 (no held-out yet) gate2 is 'unproven' -> we record nothing and defer. ------
        held_acc = (gate2_pass / gate2_seen) if gate2_seen else None
        if held_acc is not None:
            self.posterior.note(len(rungs), held_acc)
            if self.posterior.alarm():
                _say(self.narrator.alarm())
                self.events.append(dict(phase="ALARM", why=self.narration[-1],
                                        note="confidence-up/generalisation-down — narrowing is overfitting",
                                        status="unverified-awaiting-live"))
        return winner


# convenience: a fresh engine per game (called by validate_multilevel)
def new_engine():
    return EvolvabilityEngine()
