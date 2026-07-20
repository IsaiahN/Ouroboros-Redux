# budget_ladder.py (11.309) — PER-LEVEL ESCALATING ACTION BUDGET tied to a difficulty TYPE judged
# from perception signals already on disk. This is a RESOURCE the agent manages, NOT the RHAE scoring
# cutoff (5x human median, external/unknown). The budget is walked UP while the level keeps YIELDING
# (a per-arm progress signal), capped by the judged type. Absolute ladder (EASY/MED/HARD); the HARD
# ceiling ~7k is an eyeballed ARC heuristic (per Isaiah's observation), exposed for tuning.
#
# Design (decisions 11.309): per-ARM progress signal (composer: discrepancy-falling; v18: novelty
# unsaturated OR belief rising); ABSOLUTE ladder anchor (type -> baseline magnitude, not relative to
# the previous level); re-judged DURING the level because hardness reveals through struggle
# (persistent no_self_yet -> reclassify upward -> more rope). The same cap is consumed by the composer
# arm and surfaced in its introspection for debugging.

# Absolute per-level action ceilings. RHAE-GROUNDED (11.320): the scoring cutoff is ~5x the human median
# ACTION count; for these OOD puzzle games the human median is small (tens-to-hundreds), so a solve past
# ~3k actions almost certainly exceeds 5x human and earns NO credit anyway. Spending beyond that horizon
# is therefore pure wall-clock waste that cannot raise the score. Ceilings are set at the creditable
# horizon, still ABOVE every known clean-slate win (m0r0 ~1491, lp85 ~1400) with margin, so no creditable
# solve is cut. (~2.2x wall-clock cut on the ~90% hopeless levels vs the old 7000 HARD ceiling.)
import os

CEILING = {"EASY": 1800, "MED": 2500, "HARD": 3200}
FLOOR   = {"EASY": 700,  "MED": 1200, "HARD": 1600}
STEP_FRAC = 0.25   # the working budget grows by this fraction of the ceiling per progress-extension


def classify(action_regime, has_controllable, family,
             grid_cells=None, multicolor_self=False) -> str:
    """Judge level difficulty from on-disk signals. RE-CALLABLE mid-level: callers should re-judge as
    state evolves, because a level that looks easy but stays no_self_yet should be reclassified upward.
      action_regime : 'click' | 'mover' | 'mixed'
      has_controllable : bool (v18 SelfModel found a self / composer isolated an agent)
      family : v18 family() string ('no_self_yet','force_object','model_complete', ...) or None
    """
    # hardest tells first (struggle / perception defeat dominate)
    if family == "no_self_yet" or multicolor_self:
        return "HARD"
    if action_regime == "mixed" and not has_controllable:
        return "HARD"
    if grid_cells is not None and grid_cells > int(0.55 * 64 * 64):
        return "HARD"
    # easiest tells (clean perception + a known self)
    if has_controllable and family in ("model_complete", "force_object") \
            and (grid_cells is None or grid_cells <= 32 * 32):
        return "EASY"
    return "MED"


def ceiling(t: str) -> int:
    # ARC3_BUDGET_CEILING_SCALE scales all ceilings (the 7k HARD is an eyeballed ARC heuristic; tunable).
    try:
        s = float(os.environ.get("ARC3_BUDGET_CEILING_SCALE", "1") or "1")
    except Exception:
        s = 1.0
    return max(1, int(CEILING.get(t, CEILING["MED"]) * s))


def floor(t: str) -> int:
    return FLOOR.get(t, FLOOR["MED"])


def next_budget(cur: int, t: str, progressing: bool) -> int:
    """Walk the working budget up toward the type ceiling while the level is yielding; otherwise hold."""
    cap = ceiling(t)
    if cur <= 0:
        cur = floor(t)
    if progressing and cur < cap:
        return min(cap, int(cur + STEP_FRAC * cap))
    return min(cur, cap)


def verdict(spent: int, t: str, progressing: bool) -> str:
    """'continue' | 'stalled' | 'ceiling'. The v18 arm uses this to stop spending expensive compute on
    a level that has exhausted its type allowance (ceiling) or is past the floor with no yield (stalled).
    Never trips before the type floor, so a slow-but-yielding solve (e.g. m0r0 at ~1491 < HARD floor
    2000) is never cut."""
    cap, flr = ceiling(t), floor(t)
    if spent >= cap:
        return "ceiling"
    if spent >= flr and not progressing:
        return "stalled"
    return "continue"
