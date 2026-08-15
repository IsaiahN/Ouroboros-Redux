"""latents.py -- REGISTER L (KNOBS A2): measured latents, never constants.

L1: the planner's cost_per_action. Currently the callers hard-code 1.0; the
live books read non-monotonic per-level costs (A2's 1,2,2,1,2,1,2 across one
game's levels). A latent misfiled as a constant is invisible to the arm
mechanism, so it becomes a MEASURABLE here: the ESTIMATOR is the socket -- one
global mechanism for every game, no game id anywhere in this file -- and the
ESTIMATE is content, keyed by (game, level) at call time from the ledger.

EVIDENCE SOURCE (discovered): the fabric's collective "settlements" stream.
BetBook appends ONE record per settled action carrying (agent, game, PLAYING
level, nontrivial) -- the A3-2 PLAYING-level convention gives the per-level
grain, and the stream rides the planner's existing gamma.fabric handle. The
alternative book, game_results (SQLite), holds only per-episode totals
(total_actions, level_completions: game grain, no per-level split) and is not
reachable from the planner; it corroborates the estimate at game grain only.

THE DERIVATION (actions-per-level-completion -> cost per planned action):
a COMPLETION RUN is one agent's contiguous settled actions at playing level L
immediately followed by that agent's first record at L+1 (the level-up, in
append order -- an agent whose level never advances contributes nothing:
open-ended exploration is not completion evidence). The run's length is that
completion's actions-per-level; cost_per_action = total actions / total
NONTRIVIAL actions across the (game, L) completion runs. Unit-honest: a plan
step presumes one EFFECTIVE (frame-changing) click, and the ratio is the
ledgered number of budget actions one effective click cost during play that
actually completed the level (>= 1 whenever an effective click exists;
2-click-per-move games read ~2). No completion runs -> cost 1.0 with an
honest MISSING flag -- the fallback is the old constant, never a fabrication.

Write-contract (the affect law): PURE (a function of the ledger prefix and the
(game, level) key -- no RNG, no wall-clock, no instance state), BOUNDED (the
read is windowed to the last MAX_RECORDS settlement rows), a READ ONLY (never
appends), and the estimate travels as DATA (the planner reports it on the plan
dict; nothing here prices, gates, or verifies -- feasibility was already the
planner's answer to give).
"""
from __future__ import annotations

from typing import Any, Dict, List

__all__ = ["ActionCostEstimator", "ESTIMATOR", "FALLBACK", "MAX_RECORDS", "TOPIC"]

TOPIC = "settlements"
MAX_RECORDS = 4000     # bounded read: the janitor keeps ~100 raw + archive; 4000
                       # covers every survivor of a long-lived stream without an
                       # unbounded scan (same windowing idiom as lp_drive)
FALLBACK = 1.0         # the old constant -- returned ONLY with missing=True


class ActionCostEstimator:
    """The L1 socket: cost_per_action(fabric, game, level) from the books."""

    def cost_per_action(self, fabric: Any, game: Any, level: Any) -> Dict[str, Any]:
        """{"cost", "missing", "completions", "actions", "effective",
        "source": "settlements"} for (game, playing level) -- see the module
        docstring for the completion-run derivation. Pure bounded read; any
        failure degrades to the flagged fallback, never raises."""
        out: Dict[str, Any] = {"cost": FALLBACK, "missing": True, "completions": 0,
                               "actions": 0, "effective": 0, "source": TOPIC}
        try:
            g, lv = str(game), int(level)
            try:
                rows = fabric.query("collective", TOPIC)
            except Exception:
                rows = []
            # per-agent level walk, append order (the stream interleaves agents)
            runs: List[Dict[str, int]] = []          # closed completion runs at lv
            open_runs: Dict[str, Dict[str, int]] = {}    # agent -> the run at lv
            for rec in rows[-int(MAX_RECORDS):]:
                try:
                    if str(rec.get("game")) != g:
                        continue
                    a = str(rec.get("agent"))
                    rl = int(rec.get("level", -1))
                except Exception:
                    continue
                if rl == lv:
                    run = open_runs.setdefault(a, {"actions": 0, "effective": 0})
                    run["actions"] += 1
                    if rec.get("nontrivial"):
                        run["effective"] += 1
                elif a in open_runs:
                    if rl == lv + 1:                 # the level-up closes the run
                        runs.append(open_runs.pop(a))
                    else:                            # reset/jump: not a completion
                        open_runs.pop(a)
            if runs:                                 # open runs are not evidence
                actions = sum(r["actions"] for r in runs)
                effective = sum(r["effective"] for r in runs)
                out.update({
                    "cost": float(actions) / float(max(1, effective)),
                    "missing": False, "completions": len(runs),
                    "actions": int(actions), "effective": int(effective)})
        except Exception:
            pass                                     # the flagged fallback stands
        return out


# The GLOBAL estimator (Register L law: the socket is one mechanism for all
# games; estimates are per-(game, level) data read at call time). Stateless,
# so sharing it never couples callers.
ESTIMATOR = ActionCostEstimator()
