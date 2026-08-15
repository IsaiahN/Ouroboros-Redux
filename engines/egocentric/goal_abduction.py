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
    except Exception:
        pass
    return "unknown"


def extract_predicates(pre_levelup_frame: Any,
                       post_levelup_frame: Any) -> List[Dict[str, Any]]:
    """The LEVEL-UP FRAME DELTA as predicates: every vocabulary candidate that
    holds in the post frame and did NOT hold in the pre frame (what CHANGED at
    the moment of level-up). A predicate that already held is not evidence.
    Deterministic order; garbage -> [] (never invented, never raises)."""
    out: List[Dict[str, Any]] = []
    try:
        pre = np.asarray(pre_levelup_frame)
        post = np.asarray(post_levelup_frame)
        if pre.ndim < 2 or post.ndim < 2:
            return out
        cands: List[Dict[str, Any]] = [
            {"kind": "region_uniform", "region": r} for r in _REGIONS]
        cands.extend({"kind": "colour_count_zero", "colour": int(c)}
                     for c in sorted(int(v) for v in np.unique(pre)))
        cands.extend({"kind": "regions_equal", "a": _QUADS[i], "b": _QUADS[j]}
                     for i in range(len(_QUADS))
                     for j in range(i + 1, len(_QUADS)))
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
                 min_co: int = MIN_CO) -> Optional[Dict[str, Any]]:
    """The planner's SECOND target mode, one call (the loop's compact fallback).

    With no reference snapshot, plan toward the top abduced goal predicate via
    plan_to_identity's predicate mode. None when there is no credible
    hypothesis, no plan, or nothing left to do (never invented). Otherwise
    {"pred", "sig", "credibility", "steps", "feasible", "verified", "site",
    "veto"} with the DRIVE gates UNCHANGED: verified = every step atom carries
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
                                budget=float(budget), cost_per_action=1.0,
                                goal_predicate=top["pred"])
        if plan is None or not plan.get("steps"):
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
                "veto": bool(plan_veto(site, harvest, avoid=avoid))}
    except Exception:
        return None
