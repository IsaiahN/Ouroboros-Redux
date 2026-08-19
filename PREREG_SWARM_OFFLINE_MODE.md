# PREREG — RUN THE SWARM IN THE MODE THE OBJECTIVE IS DEFINED IN (2026-08-19)

**AUTHORITY: Seat 3, this beat —** *"the main metric is to reach 25/25 games completed locally
**OFFLINE** in the **WON** status. That is the goal/primary objective that RLVR is based on."*

**STATUS: PREREG ONLY. NOT EXECUTED.** It restarts all 25 workers, which is a visible cost and
therefore Seat 3's to spend.

## THE MISMATCH
`tools/swarm_supervisor.py:122` launches every worker with **no `--mode`**, and
`evolution_runner.py:1634` defaults it to **`normal`** — `OperationMode.NORMAL`, *"use both
local environments and API."* **The objective is defined in OFFLINE. The swarm is not running
in it.**

Consequences today, none catastrophic and all unnecessary:
- **API calls on a locally-defined objective.** Worker logs show `Successfully fetched metadata
  for game <id>` per episode — a network dependency, and a rate-limit surface, on work whose
  success condition is local.
- **A mode nobody chose.** `normal` is an argparse default, not a decision. *The switch was
  never set; it was never even considered.*

## THE CHANGE
Add `"--mode", "offline"` to the worker argv at `swarm_supervisor.py:122`. **One token.**

## WHY IT IS LOW-RISK, MEASURED RATHER THAN ASSERTED
**The twelve-hour run already did this.** `tools/overnight_run.py` drove all 25 games with
`--mode offline` for 47 cycles and **every cycle produced 25 sessions** — so **all 25 games are
present locally** and OFFLINE's *"use only locally available environments"* is satisfied for
the whole roster. That was the risk, and it is already retired by evidence.

The LP-drive arm rotation is environment-based (`LP_DRIVE_ARM`) and untouched by mode.

## FALSIFIERS
- **F1 · IT STILL PLAYS.** Within one poll after the switch, **all 25 workers produce sessions**
  and the per-game session count advances. *Fails if:* any game stops producing — which would
  mean it is not locally available and the roster assumption is wrong.
- **F2 · THE PROXY DOES NOT REGRESS.** `levels_completed` last-20 mean per game must not fall
  below its pre-switch value. **Baseline pinned now:** ar25 1.20 · sk48 0.95 · lp85 0.80 ·
  cd82 0.65 · sp80 0.65 · ft09 0.15 · r11l 0.00 · cn04 0.00 · all others 0.00.
  *Fails if:* any non-zero game drops to zero.
- **F3 · KNOWN-NEGATIVE — IT MUST NOT INVENT DEPTH EITHER.** A mode change is a channel change,
  not a capability change (Seat 3's own ruling). **If `levels_completed` IMPROVES on the switch,
  that is not a win — it is evidence the two modes are not the same game**, and the depth
  elimination would need re-deriving. *Either direction of movement is a finding.*

## UNDO
Remove the two argv tokens. Workers pick it up at the next recycle or restart. **No state, no
schema, no data touched.**

## WHAT THIS DOES NOT CLAIM
It will not win a game. **It aligns the run mode with the mode the objective is written in, and
removes a network dependency from a local success condition.** Nothing more.
