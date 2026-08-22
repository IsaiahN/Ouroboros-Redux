# RETIRED DOCUMENTS — moved, not deleted, with what replaced them

Seat 3, 2026-08-20: *"a document whose claim has been retracted or overtaken gets marked,
moved, or removed with a note saying what replaced it. **Not silently deleted, because the
record of a correction is the correction.**"*

Nothing here is deleted. Each entry says **what it was, why it stopped being true, and what
carries its content now.** All four predate 2026-04-01 and none is referenced by any live
path — verified as an import, a dotted path, **and a bare quoted string**, which is the check
`manual_tools` taught us on 2026-08-19.

| file | created | what it was | why retired | what carries it now |
|---|---|---|---|---|
| `progress.md` | 2025-12-03 | a running progress narrative from the v3 era | superseded by a structured beat record with scoreboard-first ordering | **`record/log/PORT_LOG.md`**, which carries GAMES WON, the levels delta and the split-half read every beat |
| `assesment.md` | 2025-12-25 | a one-off system assessment; its only inbound reference was to `progress.md`, itself retired | overtaken by the audits, each of which reads one link with receipts rather than surveying | **`record/findings/`** — `BOARD_AUDIT`, `HISTORY_TRACE`, `PERF_AUDIT`, `LINK3_AUDIT` |
| `loop_state.md` | 2026-02-11 | a snapshot of loop state during the February refactor | a snapshot of a build two eras back; `core_gameplay.py`/`learning_systems.py` have not been on the live path since 2026-02-10 | **`record/canon/THE_LADDER.md`** for the diagnostic ordering; `F8A_READ.md` for why that lineage is dead |
| `SUBAGENTS_PLAN.md` | 2026-02-10 | a plan for subagent orchestration | the arrangement it planned for was replaced by the seat map, which is a different structure and not a revision of this one | **`record/corpus/THE_SEAT_MAP_general.md`** |

## THE RULE THIS FOLDER EXISTS TO ENFORCE
**A superseded document that stays live is the same failure as a stale receipt** — it reads
as current and nothing marks that it isn't. Retiring is therefore part of a beat, not a
one-time pass: when a finding supersedes a finding, or a prereg resolves, **the overtaken
document moves here with its replacement named.**

**AND THE INVERSE IS THE TRAP:** deleting it destroys the record of the correction, which is
the ledger genus — *a fix that destroys the record of the thing it fixed*. Git holds the
content either way; this folder holds the **reason**, which git does not.

| `PREREG_BATCH_DEPLOYMENT.md` | 2026-08-19 | 5-minute batch deployment prereg | superseded before build by the polling design | deploy-on-change (`tools/swarm_supervisor.py` + `tests/gate/test_deploy_on_change.py`) |
| `PREREG_EMPTY_PLAN_ATTRIBUTION.md` | 2026-08-19 | reason field on EMPTY_PLAN starvation | step 2 proved degenerate, then the refactor absorbed attribution wholesale | REFACTOR_PLAN W1 (narration) + W4 |
| `PREREG_OFFLINE_SWARM.md` | 2026-08 | early offline-swarm prereg | superseded by the executed mode flip | `PREREG_SWARM_OFFLINE_MODE.md` (RESOLVED) |
