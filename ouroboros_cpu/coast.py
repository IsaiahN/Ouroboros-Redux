"""coast.py -- Step 5: the score-proof exploit/recompose economy, wrapping the kernel's per-level loop.

Replaces the action-space router AND the budget-ceiling give-up with a moon-landing gate keyed on the
only honest signal: did the score move (a level win).

  COAST   -- re-use the cached winning composition on the next level, WITHOUT re-deriving, while it keeps
             winning within an ADAPTIVE budget. Earned only by score proof (>=1 win on the family).
  OVERRUN -- hit the adaptive budget without a win. The carried composition is INCOMPLETE, not WRONG
             (every level layers a new mechanic on the old) -> INCREMENTAL recomposition: keep the cached
             composition and abduce ADDITIONAL structure. Re-deriving from scratch would discard proven
             rules -- the elaboration trap in reverse.
  MODEL-BREAK -- the current model cannot DESCRIBE the new frame in its existing vocabulary (explanation
             quality collapses). This is "a different game", not "a harder version" -> from-scratch.
  GIVE UP -- only when recomposition itself keeps failing.

Adaptive budget (NOT a fixed 1.5x: the premise "a correct composition solves the next level in ~the same
steps" is FALSE here because levels ADD mechanics). Anchor to the steps-to-win TREND (extrapolated growth,
clamped) with a generous skepticism band (~2x). This stops a tight cutoff from forcing from-scratch on
nearly every level and incinerating the accumulated rules.

Injected functions (compose_fresh / compose_incremental / explanation_quality / run_level) keep this
platform-free and SYNTHETICALLY verifiable (constructed from the principles, not from real games).
"""
from kernel import Outcome


class CoastController:
    def __init__(self, skepticism=2.0, growth_clamp=(1.0, 3.0), model_break_thresh=0.5, base_budget=400):
        self.win_steps = []          # steps-to-win per cleared level (the trend; the score proof)
        self.cached = None           # the winning composition to coast on
        self.skepticism = skepticism
        self.growth_clamp = growth_clamp
        self.model_break_thresh = model_break_thresh
        self.base_budget = base_budget
        self.log = []

    # ---- adaptive budget from the steps-to-win trend ----
    def adaptive_budget(self):
        ws = self.win_steps
        if not ws:
            return int(self.base_budget * self.skepticism)     # no proof yet: generous initial reasoning budget
        if len(ws) == 1:
            expected = ws[-1]
        else:
            growth = ws[-1] / max(1, ws[-2])
            lo, hi = self.growth_clamp
            growth = max(lo, min(growth, hi))                  # levels get harder; clamp a single spike
            expected = ws[-1] * growth
        return int(expected * self.skepticism)

    # ---- per-level strategy ----
    def strategy(self, explanation_quality):
        """coast (score proof + describable) | from-scratch (model-break) | compose (no proof yet)."""
        if explanation_quality < self.model_break_thresh:
            return "from-scratch"                              # different game -> discard cache
        if self.cached is None:
            return "compose"                                   # no win yet -> full reasoning
        return "coast"                                         # earned the shortcut

    # ---- drive one game (sequence of levels) ----
    def run_game(self, levels, compose_fresh, compose_incremental, explanation_quality, run_level,
                 max_levels=64):
        """levels: iterable of level handles. The injected callables:
            compose_fresh(level) -> composition
            compose_incremental(level, cached) -> cached + ADDITIONAL structure
            explanation_quality(level, cached) -> float in [0,1]
            run_level(level, composition, budget) -> (Outcome, steps_used)
        Returns dict(levels_completed, log)."""
        completed = 0
        for i, level in enumerate(levels):
            if i >= max_levels:
                break
            eq = explanation_quality(level, self.cached)
            strat = self.strategy(eq)
            budget = self.adaptive_budget()
            if strat == "coast":
                comp = self.cached
            elif strat == "from-scratch":
                comp = compose_fresh(level)                    # model-break: ignore the (wrong-game) cache
            else:
                comp = compose_fresh(level)                    # no proof yet
            outcome, steps = run_level(level, comp, budget)
            entry = dict(level=i, strategy=strat, eq=round(eq, 2), budget=budget,
                         outcome=outcome, steps=steps)

            if outcome == Outcome.SUCCESS:
                self.cached = comp; self.win_steps.append(steps)
                entry["result"] = "win"
                self.log.append(entry); completed += 1
                continue

            # not a win this attempt. OVERRUN or OBJECTIVE_INVALID with a cache -> INCREMENTAL recompose
            # (keep the proven rules, add structure) BEFORE ever going from-scratch.
            if self.cached is not None and strat != "from-scratch":
                comp2 = compose_incremental(level, self.cached)
                outcome2, steps2 = run_level(level, comp2, budget)
                entry["incremental"] = dict(outcome=outcome2, steps=steps2)
                if outcome2 == Outcome.SUCCESS:
                    self.cached = comp2; self.win_steps.append(steps2)
                    entry["result"] = "win-incremental"
                    self.log.append(entry); completed += 1
                    continue

            # incremental also failed (or we were from-scratch) -> from-scratch once, then give up
            comp3 = compose_fresh(level)
            outcome3, steps3 = run_level(level, comp3, budget)
            entry["from_scratch"] = dict(outcome=outcome3, steps=steps3)
            if outcome3 == Outcome.SUCCESS:
                self.cached = comp3; self.win_steps.append(steps3)
                entry["result"] = "win-from-scratch"
                self.log.append(entry); completed += 1
                continue

            entry["result"] = "give-up"
            self.log.append(entry)
            break                                              # recomposition kept failing -> stop the game

        return dict(levels_completed=completed, log=self.log)
