# PREREG RELEVANCE REVIEW (2026-08-20) — all 33, against the accepted refactor plan

Fired as the queued action on plan acceptance. Verdicts: **KEEP** (still governs a live
mechanism) · **RESOLVED** (executed; stands as record, its gate tests are the living guard) ·
**AMEND** (absorbed into a workstream; the workstream supersedes its open items) · **RETIRE**
(superseded; moved to `record/retired/` with its replacement named). Root files stay in place
regardless of verdict — they are cited by live code — with supersession recorded HERE rather
than by moving them.

| prereg | verdict | note |
|---|---|---|
| PREREG_DISK_CEILING | **KEEP** | ceiling + F2/F3 gates live (`test_disk_ceiling_preserves`) |
| PREREG_SMART_CLEANUP | **KEEP** | fabric_janitor governs live fabric compaction |
| PREREG_CORPSE_GUARD | **KEEP** | corpse guard live in `cognitive_game_player` |
| PREREG_DEAD_DEDUP | **KEEP** | gate test live |
| PREREG_BUDGET_RESTORATION | **KEEP** | gate test live |
| PREREG_READOUTS | **KEEP** | the R3 produced-vs-consumed gate (`test_consumers`) is a standing guard |
| PREREG_FINAL_GAPS | **KEEP** | G-C abduced plans + G-D LP-arm rotation live |
| PREREG_HANDOFF_RATE | **KEEP** | gate test live |
| PREREG_FRONTIER_HARVEST | **KEEP** | harvest streams live |
| PREREG_FRONTIER_PARIAH | **KEEP** | pariah decay preserved by the plan (W5); rename lands with `standing_half_life` work |
| PREREG_CK_WAVE1 / CK_WAVE2 | **RESOLVED** | landed; records |
| PREREG_D3_VERIFIER | **RESOLVED** | D-3 fixed + gated |
| PREREG_CONTROL_ARM | **RESOLVED** | verdict recorded |
| PREREG_CRASHFIX | **RESOLVED** | landed |
| PREREG_OVERNIGHT_RUN | **RESOLVED** | executed; results in RUN_RESULT_OVERNIGHT |
| PREREG_SWARM_OFFLINE_MODE | **RESOLVED** | executed; mode live; baseline still cited |
| PREREG_PHASE1 / PHASE2 / PHASE3A / PHASE3B / PHASE3B2 / PHASE3C | **RESOLVED / superseded** | the phase roadmap's landed items stand as records; **every unexecuted phase item is superseded by the accepted plan** — the workstreams are the roadmap now |
| PREREG_DRAIN_ORIGIN | **AMEND → W2** | origin stamps live; W2 widens the stamp into full provenance tags |
| PREREG_MASTERY_LITE | **AMEND → W3/W5** | mastery-lite live; the plan elevates the mastery pattern to the template for every crossing and every earn-through |
| PREREG_PLAN_WIRE | **AMEND → W1** | the g1–g7 gate counters live; W1's narration is their successor and superset |
| PREREG_REPLAY_FEED | **AMEND → W5** | observe-only feed live; the replay corpus itself goes under earn-through review (recordings crossing) |
| PREREG_LEVEL_SCOPED_IDEAS | **AMEND → W2** | level-scoping is an index axis; absorbed |
| PREREG_REFIT_DESTINATION | **KEEP, amended** | destination landed; the switch build is W4's `binding_stale` retention; the ALLOWLIST consumer promise stands until then |
| PREREG_BATCH_DEPLOYMENT | **RETIRE** | superseded by deploy-on-change (the polling design); guard = `test_deploy_on_change` |
| PREREG_EMPTY_PLAN_ATTRIBUTION | **RETIRE** | deprioritised when step 2 proved degenerate; W1 narration + W4 supersede its whole purpose |
| PREREG_OFFLINE_SWARM | **RETIRE** | superseded by PREREG_SWARM_OFFLINE_MODE (executed) |
| PREREG_MARKETPLACE_MERGE | **SUPERSEDED in place** | root, live-cited, so not moved; W5 is its successor and the three exclusions bind it |

**Tally: 10 KEEP · 12 RESOLVED · 5 AMEND · 3 RETIRE · 1 SUPERSEDED-in-place** (phase series
counted as 6 files under one verdict). Retirements moved to `record/retired/` with notes.
