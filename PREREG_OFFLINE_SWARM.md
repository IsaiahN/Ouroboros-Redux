# PREREG — THE OFFLINE SWARM SESSION (2026-08-18)

AUTHORITY: Isaiah — *"use swarm from the api the way the api uses it and use the offline
mode"*, and *"1 session (25 unique games paired with unique agents) should be the basic
set."* Seat 4 ruling: development, testing, arms and diagnostics run offline; online is
reserved for scorecard runs and replays.

## WHAT CHANGES, AND IT IS SMALLER THAN IT LOOKS
`evolution_runner.py:1634` ALREADY has `--mode {online,offline,normal}` and constructs
`Arcade(operation_mode=op_mode)` at `:270`. **`tools/swarm_supervisor.py:122-124` NEVER
PASSES IT**, so all 25 workers defaulted to `normal` and reached the API. The mode was a
supported, plumbed, one-flag decision that nobody made.

## THE TWO CHANGES
**1. OFFLINE.** Every development / testing / diagnostic run passes `--mode offline`.
**2. ARC'S SWARM DEFINITION.** ARC: *one agent instance per game, run concurrently, once.*
Ours: 25 pinned workers x `--max-generations 50`, i.e. hundreds of episodes. **THE BASIC
SET BECOMES ONE SESSION = 25 UNIQUE GAMES x 25 UNIQUE AGENTS x ONE PASS.** Depth beyond
that is a separate allocation decision, not the default.

## PRE-COMMITTED FALSIFIERS — all three must pass or this reverts
**F1 · SPEED.** A full 25-game session completes in **UNDER 10 MINUTES** wall-clock. The
online path could not finish one game in 15 hours. *Fails if:* >= 10 min.
**F2 · IT ACTUALLY PLAYED.** All 25 games produce **new `action_traces` rows** in their
worker DBs, and the per-game session count rises. *Fails if:* any game produces zero.
**F3 · NO KEY, NO NETWORK.** The session runs with `ARC_API_KEY` absent from the
environment. *Fails if:* it errors, or any scorecard/metadata HTTP call appears in a log.

**AND A FOURTH THAT IS NOT A FALSIFIER BUT A WATCH:** offline has no scorecards, so
`win_detected` must still be derivable from local game state. **If a full-game win becomes
UNDETECTABLE offline, that is an APPARATUS change and it goes to Seat 3 before it is
adopted as the default** — the mission is counted in wins.

## UNDO — one line, no state
Stop passing `--mode offline` (and/or unset `OPERATION_MODE`). **No data is migrated, no
schema changes, no records rewritten.** The existing `.runs/swarm/<game>/` boxes are
untouched by the flag. Reverting costs one edit and loses nothing.

## POTENTIAL PROBLEM ANALYSIS (the KT import, first use)
*Not "did it work" but "what breaks if it does".*
**PP1 — offline environments could be a different version from online.** The loader logs
`Found latest version of ls20: ls20-9607627b (downloaded 2026-08-10)`. **PREVENTIVE: record
the resolved version per game in the session output**, so a result can never be compared
across two different game builds without it being visible.
**PP2 — every banked atom, sequence and dead-cell map was earned ONLINE.** If offline
differs at all, the bank is now cross-regime evidence and the population/as-of rule applies.
**PREVENTIVE: stamp session records with the mode**, and never pool online and offline
counts in one figure.
**PP3 — 25 concurrent heavy processes are what caused the contention I misdiagnosed.**
Offline is ~11,782 steps/sec single-threaded, so 25 games is seconds of compute.
**PREVENTIVE: run ONE process with a small thread pool, not 25 processes.** The box has 4
cores and the previous design oversubscribed it 13x.
**PP4 — losing scorecards means losing the replay/leaderboard record.** PREVENTIVE: online
stays available and is reserved for exactly that, per the standing ruling.
