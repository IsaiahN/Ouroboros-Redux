# PRE-REGISTRATION — PHASE 3b: circulation at population scale (measurement first)

**Written 2026-08-10, on `v4-cold` at `e29ba00`. A MEASUREMENT beat — no agent code changes
authorised until its verdict.**

## THE HYPOTHESIS

> In a real multi-agent production run (v4's own generation machinery, fabric live), the idea
> economy circulates end-to-end WITHOUT further wiring: (a) level-ups mint; (b) a later agent
> loads a different agent's idea ([EGO-SEED] with the prior's author ≠ loader); (c) at least
> one echo or falsify crosses agents.

**FALSIFIER:** ≥1 level-up occurs in the trial but no cross-agent seed/echo/falsify ever does →
circulation is broken; mechanism read from logs/fabric before any fix is briefed.

## THE TRIAL

Fresh sandbox working dir (`.runs/pop3b/` — baseline DB untouched), stock runner:
population 12, 8 agents/gen, 3 games/agent, 3 generations (~72 episodes). Numbers re-derived
from the session fabric (JSONL) and run log by the proctor.

## ALSO MEASURED (the 3c question, from source + logs)

Whether REPLAY-MODE episodes route level-ups through the cognitive loop's `record_result`
(if not, 3c needs a signal wire from the replay executor to the spine/fabric — that becomes
3c's prereg).
