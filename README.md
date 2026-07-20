# Ouroboros — Redux (v5)

The **Redux composer agent** — a whitebox reasoning agent that solves ARC-AGI-3 games *by its own
reasoning*, not by an encoded answer. The merge of the allocentric and egocentric views
(`docs/corpus/THE_MARBLE §VII`). Distinct lineage from the v1–v4 multi-agent "smart network, dumb
agents" blackbox (`docs/corpus/THE_ALIGNMENT §0`).

> **The goal is the agent, not the score.** An agent that beats the 25 dev games on its own, in one
> generation, and can *say how*. A blackbox that wins teaches nothing.

## Layout

- **`ouroboros_cpu/`** — the live agent (69 modules). Entry: `integrated_agent.MyAgent`. Live path:
  `online_harness.run_online → play_game_submission → integrated_agent.MyAgent → my_agent → objective_validator`.
- **`ouroboros_cpu/RUN_ON_DISPATCH.md`** — how to run it (env, SDK, flags, run command). **Read first.**
- **`docs/corpus/`** — the map (the five map docs + THE_ALIGNMENT + PROCTOR_MEMORY_original). These are
  the values; they outrank everything. `PROCTOR_MEMORY_original §IV` = the measured ls20 facts.
- **`docs/proctor/`** — the operating layer: **LAW 0** (`PROCTOR_MEMORY_law_0.md`) + Rule 0 of Evidence
  + the phantom-first debug guide. The live running state (`PROCTOR_STATE`), the developmental gauge
  (`THE_LADDER`), and the off/unreachable inventory live in the attached claude.ai project and are
  mirrored here as they stabilise.

## Quick run

    export ARC_API_KEY=<key>          # env ONLY — never commit a key
    cd ouroboros_cpu
    pip install arc-agi arcengine arc-agi-3 scipy --break-system-packages
    python _proctor_free.py 1000 800 /tmp/free.log     # cap_actions wall_secs stream_out
    python ladder_score.py /tmp/free.log               # score log-rung vs corroborated-rung

## The one rule that keeps it honest

Every fix repairs the **pipeline / perception / tools** so the agent reasons for itself — never the
answer, never "how to think." `levels_completed` is the only real metric; a proctor reading its own
narration is dead reckoning (`THE_DIALOGUES §III-b`), so every verdict anchors to an external landmark
— the metric, the rendered frame, or Isaiah — never the log alone.

## Status (20 Jul 2026)

ls20 **L0 clears reliably**. L1: perception fixed (pairs with the real box), full match+nav chain runs,
not yet cleared (long maze within budget). The other 24 dev games are unstarted. No secrets in the tree
— the ARC key and any GitHub token are env-only, never committed.
