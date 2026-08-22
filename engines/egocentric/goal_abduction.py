"""goal_abduction.py -- G-C: goal abduction (PREREG_FINAL_GAPS.md).

The thin link past d->0-to-reference: at the moment of a level-up, the frame
delta is mined for STRUCTURAL predicates that BECAME true across the transition
(they hold in the post frame and did not hold in the pre frame) -- mechanics,
never answers. The vocabulary is relative/derived only (no game ids, no absolute
board coordinates):

  * region_uniform(region):    the region holds exactly one colour;
  * colour_count_zero(colour): count(colour) == 0 -- the colour was eliminated;
  * regions_equal(a, b):       two same-shape regions are cell-identical
                               (pattern A matches B).

Regions are frame-shape-DERIVED: "full" plus the four floor-halved quadrants
"q0".."q3" (rows/cols taken h//2 and w//2 from each end, so paired quadrants
always share a shape whatever the board size).

THE GROWN CLASSES (LINK3_AUDIT + addendum 2 -- an instrument is improved from a
worse instrument already returning something, and the RESIDUAL is the spec).
Measured read-only against every level-up frame the project holds: the three
classes above extracted ZERO predicates on every record while the boards
visibly differed. The residual that measurement produced -- not a description of
the domain, the residual itself -- named four extensions:

  * colour_present(colour)     -- count(colour) > 0. `colour_count_zero`'s
      SIGN-FLIPPED TWIN. Nothing has ever vanished at a level-up in this
      project's history; colours APPEAR. The old class looked only for
      disappearance and was therefore anti-correlated with the event it exists
      to describe.
  * colour_majority(colour)    -- colour holds strictly more cells than every
      other colour. The residual showed EVERY colour's count moving while the
      colour SET often did not change at all; this states that change
      RELATIVELY (which colour dominates), never as an absolute cell count --
      a raw count is a memorized answer, not a mechanic.
  * region_colour_count_atmost(region, k) -- the region holds at most k distinct
      colours. `region_uniform` is exactly the k=1 rung of this ladder and was
      measured unsatisfiable (0/5 on every board, pre AND post); the live boards
      live at k=2..11 and some region palettes SHRINK across the transition.
  * region_contains_colour(region, colour) -- the region holds at least one cell
      of that colour. LOCAL appearance: a colour entering a region it was not
      in, which the global class cannot see when the colour already exists
      elsewhere on the board. This is deliberately the COARSEST rung and it
      fires very widely; MIN_CO and the miss ledger, never its own fire rate,
      are what must carry it.

The original three are KEPT UNCHANGED -- they are correct and merely never
satisfied on this domain. This is an extension, not a replacement: a vocabulary
that started firing `region_uniform` or `regions_equal` on these boards would
have replaced the edge rather than extended it.

EVERY class is a SINGLE-FRAME property, which is not a stylistic choice: the
planner's predicate mode stops on `satisfies(pred, state)` against one state, so
a delta-shaped predicate ("count increased") would be undecidable there.

GoalBook banks each level-up's extracted predicates as GOAL HYPOTHESES on the
COLLECTIVE fabric stream "goal_hypotheses", scoped by (game, level) like every
prior. Credibility = co-occurrence count across episodes minus misses: a
level-up that occurs WITHOUT a known hypothesis's predicate (not satisfied by
the post frame) appends a miss -- falsified defeasibly, never deleted. No
level-up evidence -> no hypotheses (never invented).

`abduced_plan` is the planner's SECOND target mode in one call (the loop's
compact fallback for the g4=0 episodes): with no reference snapshot, plan
toward the top credible abduced goal (>= MIN_CO co-occurrences) via
plan_to_identity's predicate mode, under the UNCHANGED drive gates.

Discipline (as spine/frontier): deterministic -- no RNG, no wall-clock; the
book swallows every exception to `errors` (it must never crash the loop it
advises). Stdlib + numpy only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

__all__ = ["GoalBook", "extract_predicates", "satisfies", "signature",
           "abduced_plan", "TOPIC", "FRAMES_TOPIC", "MIN_CO"]

TOPIC = "goal_hypotheses"
FRAMES_TOPIC = "levelup_frames"   # VICTORY_PROTOCOL: the raw pre/post record
MIN_CO = 2                    # co-occurrences before a hypothesis may become a target

_QUADS = ("q0", "q1", "q2", "q3")
_REGIONS = ("full",) + _QUADS


def _region(frame: np.ndarray, name: str) -> Optional[np.ndarray]:
    """A named RELATIVE region of the frame; None when it does not exist."""
    a = np.asarray(frame)
    if a.ndim < 2:
        return None
    if name == "full":
        return a
    h2, w2 = a.shape[0] // 2, a.shape[1] // 2
    if h2 == 0 or w2 == 0:
        return None
    if name == "q0":
        return a[:h2, :w2]
    if name == "q1":
        return a[:h2, a.shape[1] - w2:]
    if name == "q2":
        return a[a.shape[0] - h2:, :w2]
    if name == "q3":
        return a[a.shape[0] - h2:, a.shape[1] - w2:]
    return None


def _uniform(region: Optional[np.ndarray]) -> bool:
    return region is not None and region.size > 0 and len(np.unique(region)) == 1


def _majority(frame: np.ndarray, colour: int) -> bool:
    """True iff `colour` holds STRICTLY more cells than every other colour --
    the plurality, stated relatively (no absolute cell count ever appears)."""
    vals, counts = np.unique(frame, return_counts=True)
    if vals.size == 0:
        return False
    top = int(counts.max())
    if int(counts[counts == top].sum()) != top:
        return False                        # tied plurality: nobody dominates
    return bool(int(vals[int(np.argmax(counts))]) == int(colour))


def satisfies(pred: Optional[Dict[str, Any]], frame: Any) -> bool:
    """True iff the structural predicate holds in `frame` -- the planner's
    predicate-mode stopping test. Garbage -> False, never raises."""
    try:
        a = np.asarray(frame)
        k = (pred or {}).get("kind")
        if k == "region_uniform":
            return _uniform(_region(a, str(pred.get("region"))))
        if k == "colour_count_zero":
            return bool(int((a == int(pred.get("colour"))).sum()) == 0)
        if k == "regions_equal":
            ra = _region(a, str(pred.get("a")))
            rb = _region(a, str(pred.get("b")))
            return (ra is not None and rb is not None and ra.size > 0
                    and ra.shape == rb.shape and bool((ra == rb).all()))
        if k == "colour_present":
            return bool(int((a == int(pred.get("colour"))).sum()) > 0)
        if k == "colour_majority":
            return a.size > 0 and _majority(a, int(pred.get("colour")))
        if k == "region_colour_count_atmost":
            r = _region(a, str(pred.get("region")))
            return (r is not None and r.size > 0
                    and int(len(np.unique(r))) <= int(pred.get("k")))
        if k == "region_contains_colour":
            r = _region(a, str(pred.get("region")))
            return (r is not None and r.size > 0
                    and bool(int((r == int(pred.get("colour"))).sum()) > 0))
        return False
    except Exception:
        return False


def signature(pred: Optional[Dict[str, Any]]) -> str:
    """Canonical stream key for a predicate -- shape + params, nothing else."""
    try:
        k = (pred or {}).get("kind")
        if k == "region_uniform":
            return "region_uniform:%s" % pred.get("region")
        if k == "colour_count_zero":
            return "colour_count_zero:%d" % int(pred.get("colour"))
        if k == "regions_equal":
            return "regions_equal:%s:%s" % (pred.get("a"), pred.get("b"))
        if k == "colour_present":
            return "colour_present:%d" % int(pred.get("colour"))
        if k == "colour_majority":
            return "colour_majority:%d" % int(pred.get("colour"))
        if k == "region_colour_count_atmost":
            return "region_colour_count_atmost:%s:%d" % (
                pred.get("region"), int(pred.get("k")))
        if k == "region_contains_colour":
            return "region_contains_colour:%s:%d" % (
                pred.get("region"), int(pred.get("colour")))
    except Exception:
        pass
    return "unknown"


def extract_predicates(pre_levelup_frame: Any,
                       post_levelup_frame: Any) -> List[Dict[str, Any]]:
    """The LEVEL-UP FRAME DELTA as predicates: every vocabulary candidate that
    holds in the post frame and did NOT hold in the pre frame (what CHANGED at
    the moment of level-up). A predicate that already held is not evidence.
    Deterministic order; garbage -> [] (never invented, never raises).

    Every candidate's parameters are DRAWN FROM THE FRAMES THEMSELVES (colours
    present, measured region palette sizes) -- nothing is invented and no
    magnitude is memorized. The single filter below is what keeps the extension
    honest: a class whose candidates all already held in pre contributes
    nothing, which is exactly why `region_uniform` and `regions_equal` still
    yield zero on this domain."""
    out: List[Dict[str, Any]] = []
    try:
        pre = np.asarray(pre_levelup_frame)
        post = np.asarray(post_levelup_frame)
        if pre.ndim < 2 or post.ndim < 2:
            return out
        post_cols = sorted(int(v) for v in np.unique(post))
        cands: List[Dict[str, Any]] = [
            {"kind": "region_uniform", "region": r} for r in _REGIONS]
        cands.extend({"kind": "colour_count_zero", "colour": int(c)}
                     for c in sorted(int(v) for v in np.unique(pre)))
        cands.extend({"kind": "regions_equal", "a": _QUADS[i], "b": _QUADS[j]}
                     for i in range(len(_QUADS))
                     for j in range(i + 1, len(_QUADS)))
        # ── the grown classes (LINK3_AUDIT residual) ──────────────────────────
        cands.extend({"kind": "colour_present", "colour": int(c)}
                     for c in post_cols)
        cands.extend({"kind": "colour_majority", "colour": int(c)}
                     for c in post_cols)
        for r in _REGIONS:
            reg = _region(post, r)
            if reg is None or reg.size == 0:
                continue
            # k is the region's OWN measured palette size in post, so the
            # candidate holds there by construction and survives the filter
            # only when the pre-frame's palette for that region was LARGER.
            cands.append({"kind": "region_colour_count_atmost", "region": r,
                          "k": int(len(np.unique(reg)))})
            cands.extend({"kind": "region_contains_colour", "region": r,
                          "colour": int(c)}
                         for c in sorted(int(v) for v in np.unique(reg)))
        out = [p for p in cands
               if satisfies(p, post) and not satisfies(p, pre)]
    except Exception:
        return []
    return out


class GoalBook:
    """Fabric-backed ledger of abduced goal hypotheses, keyed by (game, level)."""

    def __init__(self, fabric: Any):
        self.fabric = fabric
        self.errors: int = 0

    def observe_levelup(self, game: str, level: int, pre: Any,
                        post: Any) -> List[Dict[str, Any]]:
        """Bank one level-up's frame delta: every extracted predicate appends a
        co-occurrence record; every KNOWN hypothesis at (game, level) whose
        predicate does NOT hold in the post frame appends a miss (a level-up
        occurred WITHOUT it -- falsified, credibility drops). Returns the
        banked [{"pred", "sig"}]; [] on error or no delta (never invented).

        RECORD-KEEPING (VICTORY_PROTOCOL): the pre/post frames themselves are
        persisted to the PERSONAL "levelup_frames" stream, exactly ONE record
        per level-up, BEFORE predicate extraction -- the frames are
        unrecoverable later, the predicates merely derivable from them. A
        level-up whose delta yields no hypothesis still keeps its snapshot;
        absent frames keep nothing (never invented)."""
        try:
            g, lv = str(game), int(level)
            if pre is not None and post is not None:
                try:
                    self.fabric.append("personal", FRAMES_TOPIC, {
                        "game": g, "level": lv,
                        "pre": np.asarray(pre).tolist(),
                        "post": np.asarray(post).tolist()})
                except Exception:
                    self.errors += 1        # the frame record must never block banking
            preds = extract_predicates(pre, post)
            known: Dict[str, Dict[str, Any]] = {}
            for rec in self.fabric.query(
                    "collective", TOPIC,
                    where=lambda r: r.get("game") == g and r.get("level") == lv):
                s = rec.get("sig")
                if s and s not in known and rec.get("pred") is not None:
                    known[s] = rec["pred"]
            got = set()
            out: List[Dict[str, Any]] = []
            for p in preds:
                s = signature(p)
                got.add(s)
                self.fabric.append("collective", TOPIC,
                                   {"game": g, "level": lv, "sig": s,
                                    "pred": p, "ev": "co"})
                out.append({"pred": p, "sig": s})
            for s in sorted(known):
                if s not in got and not satisfies(known[s], post):
                    self.fabric.append("collective", TOPIC,
                                       {"game": g, "level": lv, "sig": s,
                                        "pred": known[s], "ev": "miss"})
            return out
        except Exception:
            self.errors += 1
            return []

    def hypotheses(self, game: str, level: int) -> List[Dict[str, Any]]:
        """Every hypothesis for (game, level), aggregated across seeds+local:
        [{"pred", "sig", "co", "miss", "credibility"}], ranked credibility desc
        then sig asc (deterministic, as priors). [] on error."""
        try:
            g, lv = str(game), int(level)
            agg: Dict[str, Dict[str, Any]] = {}
            for rec in self.fabric.query(
                    "collective", TOPIC,
                    where=lambda r: r.get("game") == g and r.get("level") == lv):
                s = rec.get("sig")
                if not s:
                    continue
                e = agg.setdefault(s, {"pred": None, "sig": s, "co": 0, "miss": 0})
                if e["pred"] is None and rec.get("pred") is not None:
                    e["pred"] = rec["pred"]
                if rec.get("ev") == "co":
                    e["co"] += 1
                elif rec.get("ev") == "miss":
                    e["miss"] += 1
            out = list(agg.values())
            for e in out:
                e["credibility"] = int(e["co"]) - int(e["miss"])
            out.sort(key=lambda h: (-int(h["credibility"]), str(h["sig"])))
            return out
        except Exception:
            self.errors += 1
            return []

    def top(self, game: str, level: int,
            min_co: int = MIN_CO) -> Optional[Dict[str, Any]]:
        """The top CREDIBLE hypothesis: highest credibility with >= min_co
        co-occurrences, positive credibility, and a usable predicate. None
        otherwise -- no evidence is no target (abduced=[] dies)."""
        for h in self.hypotheses(game, level):
            if (int(h.get("co", 0)) >= int(min_co)
                    and int(h.get("credibility", 0)) > 0
                    and h.get("pred") is not None):
                return h
        return None


def abduced_plan(gamma: Any, book: GoalBook, frame: Any, game: str, level: int,
                 budget: float, verified_counts: Optional[Dict[str, int]],
                 harvest: Any = None, avoid: Any = None,
                 min_co: int = MIN_CO, retained: Any = None,
                 standing: Any = None) -> Optional[Dict[str, Any]]:
    """The planner's SECOND target mode, one call (the loop's compact fallback).
    W2c: `retained` is passed through to plan_to_identity untouched (the
    scheduler's retention store, or None -- the undo). R3/R4: `standing` is
    passed through the same way (the scheduler's standing book, or None) --
    the abduced path is the SAME candidate set, so it is ranked and filtered
    by the same rule; nothing here reads S.

    With no reference snapshot, plan toward the top abduced goal predicate via
    plan_to_identity's predicate mode. None when there is no credible
    hypothesis, no plan, or nothing left to do (never invented). Otherwise
    {"pred", "sig", "credibility", "steps", "feasible", "verified", "site",
    "veto", "cost_per_action", "cost_missing"} -- the plan is priced by the
    L1 measured latent (cost_per_action=None: the planner consumes the global
    latents.ESTIMATOR; below MIN_OBS completion runs it fails closed to the
    flagged 1.0) and this site narrates the [COST] line, both values (the
    estimate and the 1.0 it replaced) -- with the DRIVE gates UNCHANGED:
    verified = every step atom carries
    >= 2 TRANSFERRED settlements; site = the first atom's context anchor in
    `frame` (derived, never memorized); veto = the frontier fatal/dead/avoid
    check. WHETHER to drive stays the loop's decision -- this function only
    reports the gates. Never raises."""
    try:
        top = book.top(game, level, min_co)
        if top is None:
            return None
        from engines.egocentric.planner import plan_to_identity  # late: no import cycle
        f = np.asarray(frame)
        plan = plan_to_identity(f, None, gamma, game=str(game), level=int(level),
                                budget=float(budget), cost_per_action=None,
                                goal_predicate=top["pred"], retained=retained,
                                standing=standing)
        if plan is None:
            return None
        # L1 narration -- BOTH values on the line: the estimate AND the 1.0
        # constant it replaced ([COST] per call site; fallback never silent).
        if plan.get("cost_missing"):
            print("[COST] fallback=1.0")
        else:
            print("[COST] est=%.2f (was 1.0)" % float(plan["cost_per_action"]))
        if not plan.get("steps"):
            return None
        av = verified_counts or {}
        verified = all(int(av.get(sid, 0)) >= 2 for sid in plan["steps"])
        site: Optional[Tuple[int, int]] = None
        atom = gamma.get(plan["steps"][0])
        if atom is not None and atom.get("kind") == "EFFECT":
            ctx = np.asarray(atom["context"])
            ph, pw = ctx.shape
            bh, bw = f.shape[:2]
            for r in range(bh - ph + 1):
                for c in range(bw - pw + 1):
                    if (f[r:r + ph, c:c + pw] == ctx).all():
                        site = (c + pw // 2, r + ph // 2)
                        break
                if site is not None:
                    break
        from engines.egocentric.frontier import plan_veto
        return {"pred": top["pred"], "sig": str(top["sig"]),
                "credibility": int(top["credibility"]),
                "steps": list(plan["steps"]), "feasible": bool(plan["feasible"]),
                "verified": bool(verified), "site": site,
                "veto": bool(plan_veto(site, harvest, avoid=avoid)),
                "cost_per_action": float(plan.get("cost_per_action", 1.0)),
                "cost_missing": bool(plan.get("cost_missing", True))}
    except Exception:
        return None
