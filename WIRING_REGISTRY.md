# WIRING REGISTRY (rung 0c, THE_LADDER.md) — one row per organ

THE DONE STANDARD: a build is DONE when something in the live path calls it
with real inputs. This file is the declaration layer; it states reality, it
does not hide it. It is CHECKED, not trusted:

* deterministic gate: `tests/gate/test_wiring_registry.py` — every LIVE row's
  receipt region (±30 lines) still references the symbol AND the symbol is
  referenced from a production module (non-import AST scan; `__init__`
  re-exports do NOT count — the vulture blind spot). Every SEVERED row asserts
  the INVERSE, so a silent reconnection goes red until this file is updated.
  Every class in `engines/egocentric/*.py` must have a row; a new organ with
  no receipt is UNSHIPPABLE.
* empirical gate: `tools/live_coverage_diff.py` — branch coverage from a
  bounded synthetic episode diffed against the LIVE rows; a receipt whose line
  never executes is reported SEVERED-EMPIRICAL (`severed count=N` is the
  rung-0c line). A real-game operator-invoked run is the stronger mode; the
  synthetic run is the CI-safe floor.

Row format (machine-parseable; the gate parses exactly this):
`| name | symbol (module:qualname) | site (file:line) | status | date | note |`
Status ∈ LIVE / SEVERED / DELETED-PENDING. For LIVE rows the site is the
claimed live-path call site; for SEVERED rows it is the WIRE-BREAK line.
Note markers the gate honors: `[helper]` (own-module reference counts),
`[alias=NAME]` (consumed under another name), `[referenced-but-dead]`
(deterministically referenced, semantically dead — inverse check waived
loudly; the coverage diff owns it).

Seeded 2026-08-16 from PIPELINE_AUDIT.md (the full sweep: eleven severed
organs behind green tests + verified-LIVE lists 2/3), receipts re-derived by
build-scan the same day.

## LIVE WIRES

| name | symbol | site | status | date | note |
|------|--------|------|--------|------|------|
| fabric-core | engines.egocentric.fabric:KnowledgeFabric | cognitive_loop.py:1447 | LIVE | 2026-08-16 | lazy init + seed once per game; also cognitive_game_player.py:107 |
| observer-core | engines.egocentric.observer:EgoObserver | cognitive_loop.py:1419 | LIVE | 2026-08-16 | replay-path twin at cognitive_loop.py:1343 |
| tracker-core | engines.egocentric.perception:ObjectTracker | engines/egocentric/observer.py:27 | LIVE | 2026-08-16 | also engines/perception/event_detector.py:104 |
| perception-object | engines.egocentric.perception:Object | engines/egocentric/goal.py:131 | LIVE | 2026-08-16 | the typed percept unit; used across goal/observer |
| downsample-ban | engines.egocentric.perception:DownsampleError | engines/egocentric/perception.py:125 | LIVE | 2026-08-16 | [helper] raised in own module; perception is live via tracker-core |
| self-locus | engines.egocentric.self_locus:SelfLocus | engines/egocentric/observer.py:28 | LIVE | 2026-08-16 | contingency self-detection inside the observer |
| goal-manager | engines.egocentric.goal:GoalManager | engines/egocentric/spine.py:32 | LIVE | 2026-08-16 | verbatim port wrapped by GoalSpine |
| goal-spine | engines.egocentric.spine:GoalSpine | cognitive_loop.py:1434 | LIVE | 2026-08-16 | replay twin cognitive_loop.py:1346; drive() pre-empt at cognitive_loop.py:1024 (the ONE wheel site) |
| click-economy | engines.egocentric.spine:GoalSpine.credit_click | cognitive_loop.py:1573 | LIVE | 2026-08-16 | drive_click cognitive_loop.py:1032; falsify write-back cognitive_loop.py:1877; credit the ACTED-ON cell |
| bet-spine | engines.egocentric.betting:BetBook | cognitive_loop.py:1245 | LIVE | 2026-08-16 | commit cognitive_loop.py:1266; settle cognitive_loop.py:2065; committed≠executed → VOID |
| pricing-salience | engines.egocentric.pricing:informative_salience | engines/egocentric/betting.py:98 | LIVE | 2026-08-16 | the live half of pricing.py; Marketplace stays iced (see marketplace-iced) |
| efference-copy | engines.egocentric.binder:RoleBinder.predicted_change_mask | cognitive_loop.py:1639 | LIVE | 2026-08-16 | CK-2a; subtraction consumed at cognitive_loop.py:1664 (observe_attributed) |
| binder-core | engines.egocentric.binder:RoleBinder | cognitive_loop.py:1607 | LIVE | 2026-08-16 | W4c lazy-init block; fed per step at cognitive_loop.py:1664 |
| binder-evidence | engines.egocentric.binder:_ClassEvidence | engines/egocentric/binder.py:80 | LIVE | 2026-08-16 | [helper] internal accumulator of the live binder |
| gamma-store | engines.egocentric.effects:Gamma | cognitive_loop.py:1606 | LIVE | 2026-08-16 | typed EFFECT store over the fabric |
| bank-core | engines.egocentric.bank:PredictorBank | cognitive_loop.py:1608 | LIVE | 2026-08-16 | settle at cognitive_loop.py:1688; every settlement routes |
| router-core | engines.egocentric.router:ResidualRouter | cognitive_loop.py:1612 | LIVE | 2026-08-16 | constructed MINERLESS — the miner wire is the conditional-miner SEVERED row |
| mint-core | engines.egocentric.mint:MDLMint | cognitive_loop.py:1613 | LIVE | 2026-08-16 | consider() at the credit/primal sites; ledger every verdict |
| affect-seed-steer | engines.egocentric.affect:AffectGains.seed_gain | cognitive_loop.py:1844 | LIVE | 2026-08-16 | B5 applied-bias site; AffectGains constructed cognitive_loop.py:1614; starvation+swallow widened, bounded |
| affect-starvation-steer | engines.egocentric.affect:AffectGains.starvation_steer | cognitive_loop.py:1913 | LIVE | 2026-08-16 | R1 explore_boost inside the mute-probe block; synthetic coverage floor may not reach it |
| lp-steer | engines.egocentric.lp_drive:LPDrive | engines/egocentric/affect.py:173 | LIVE | 2026-08-16 | consumed via AffectGains.lp_steer at cognitive_loop.py:3518; bounded, narrated, lp arm only |
| starvation-settle | engines.egocentric.starvation:StarvationBook | cognitive_loop.py:557 | LIVE | 2026-08-16 | settle_episode at end_game; ≤1 per socket |
| swallow-settle | engines.egocentric.swallow:SwallowBook | cognitive_loop.py:594 | LIVE | 2026-08-16 | settle_episode at end_game; ≤1 per block |
| consumer-drain | engines.egocentric.consumer:consume | cognitive_loop.py:574 | LIVE | 2026-08-16 | W1 once-per-episode budgeted drain (budget_n=8) |
| consumer-seed | engines.egocentric.consumer:seed_imports | cognitive_loop.py:85 | LIVE | 2026-08-16 | W1 seed side; called from _seed_imp at cognitive_loop.py:1623 |
| decline-branch | engines.egocentric.consumer:match | engines/egocentric/consumer.py:553 | LIVE | 2026-08-16 | [helper] kind=declined routed at consumer.py:258 (DECLINE_REASONS enum); reached via consumer-drain |
| hydration | cognitive_loop:_hyd_ver | cognitive_loop.py:1616 | LIVE | 2026-08-16 | [helper] A3-1 book-derived verified base; defined cognitive_loop.py:121 |
| goal-abduction-book | engines.egocentric.goal_abduction:GoalBook | cognitive_loop.py:1202 | LIVE | 2026-08-16 | boundary settle via _goal_abd at cognitive_loop.py:111 |
| goal-abduction-plan | engines.egocentric.goal_abduction:abduced_plan | cognitive_loop.py:1205 | LIVE | 2026-08-16 | verified-atom + site + veto gated; deep plan path |
| plan-veto | engines.egocentric.frontier:plan_veto | cognitive_loop.py:1167 | LIVE | 2026-08-16 | B3 frontier veto on the plan site; deep plan path — synthetic coverage floor may not reach it |
| harvest | engines.egocentric.frontier:FrontierBook.load_harvest | cognitive_loop.py:2031 | LIVE | 2026-08-16 | FrontierBook constructed cognitive_loop.py:1946; record_harvest cognitive_game_player.py:759 |
| movement-bias | engines.egocentric.frontier:bias_moves | cognitive_loop.py:3362 | LIVE | 2026-08-16 | B2 bounded bias, never a veto; load_moves cognitive_loop.py:3359; record_moves cognitive_game_player.py:776 |
| salient-prefix | cognitive_game_player:CognitiveGamePlayer._bank_salient_prefix | cognitive_game_player.py:790 | LIVE | 2026-08-16 | [helper] B7 playback channel only; replay via _load_salient_prefix cognitive_game_player.py:325 |
| cost-flip | engines.egocentric.latents:ActionCostEstimator | engines/egocentric/planner.py:166 | LIVE | 2026-08-16 | [alias=ESTIMATOR] KNOBS A2: both live plan sites pass cost_per_action=None and consume the estimate; fail-closed under MIN_OBS |
| mastery-lite | engines.egocentric.mastery:MasteryLite | cognitive_game_player.py:107 | LIVE | 2026-08-16 | replay-probability spine in the player |

## SEVERED ORGANS (the sweep's eleven, + minor, + build-scan finds)

| name | symbol | site | status | date | note |
|------|--------|------|--------|------|------|
| role-multiplier | cognitive_game_player:CognitiveGamePlayer._role_allowance_multiplier | cognitive_game_player.py:240 | SEVERED | 2026-08-16 | S1 [referenced-but-dead] fed None forever — no agent role reaches the call; every purse ×1.0 (known, unfixed) |
| bracket-rt-print | tools.bracket_rt:live_report | tools/bracket_rt.py:484 | SEVERED | 2026-08-16 | S2 R_T=0.000 is a PRINTED CONSTANT on a key-to-itself join (tools/bracket_rt.py:484-490), not arithmetic |
| agent-motion | engines.egocentric.bank:AGENT_MOTION_ENABLED | engines/egocentric/bank.py:209 | SEVERED | 2026-08-16 | S3 family never fed — animacy never runs live; flag True, branch dead (bank.py:209-264) |
| conditional-miner | engines.egocentric.effects:ConditionalMiner | cognitive_loop.py:1612 | SEVERED | 2026-08-16 | S4 live router constructed WITHOUT miner= → early-returns; conditional_atoms never populated; triage NEAR FRONT |
| class-fission | engines.egocentric.bank:ClassFissionSocket | engines/egocentric/bank.py:285 | SEVERED | 2026-08-16 | S5 zero production callers of note_outcome/resolve; RoleBinder.on_fission never called live; triage NEAR FRONT |
| mute-probe | engines.egocentric.verdicts:MuteHandler.mute | cognitive_loop.py:1931 | SEVERED | 2026-08-16 | S6 [referenced-but-dead] observed_counts hardcoded all-zeros at the call; probe only PRINTED; release() never called — steers nothing |
| fabric-janitor | engines.egocentric.janitor:FabricJanitor | engines/egocentric/janitor.py:60 | SEVERED | 2026-08-16 | S7 NEVER CONSTRUCTED in production — compaction has never run (explains 268k-line queues) |
| rho-ladder | engines.egocentric.rho:rho_at | engines/egocentric/rho.py:174 | SEVERED | 2026-08-16 | S8 Amendment-2 trio rho_at / rederivation_traffic (rho.py:190) / rho_report (rho.py:209): zero callers; partition-artifact fix unmeasured live; triage WIRE FIRST |
| broken-rebinding | engines.egocentric.router:BROKEN_REBINDING | engines/egocentric/router.py:71 | SEVERED | 2026-08-16 | S9 bin unreachable — binding_stale never produced, refit_queue never drained |
| symbolic-gameplay | engines.reasoning.symbolic_reasoning_engine:SymbolicGameplayIntegration | engines/reasoning/symbolic_reasoning_engine.py:2274 | SEVERED | 2026-08-16 | S10 never constructed in production; triage DELETE (dead weight) |
| falsified-ledger | engines.egocentric.falsified_ledger:FalsifiedLedger | engines/egocentric/falsified_ledger.py:63 | SEVERED | 2026-08-16 | S11 never constructed; the __init__ re-export hid it from vulture; triage DELETE (dead weight) |
| falsified-ledger-entry | engines.egocentric.falsified_ledger:_Entry | engines/egocentric/falsified_ledger.py:56 | SEVERED | 2026-08-16 | helper of S11 — dies with its ledger |
| mint-ep-kwarg | engines.egocentric.mint:MDLMint.consider | engines/egocentric/mint.py:191 | SEVERED | 2026-08-16 | minor [referenced-but-dead] the ep= kwarg is never passed by any caller (internal counter used everywhere); consider() itself is the LIVE mint-core wire |
| cursor-agency | engines.egocentric.agency:CursorAgency | engines/egocentric/agency.py:36 | SEVERED | 2026-08-16 | build-scan 2026-08-16: no production caller found — same genus as the eleven, surfaced by this registry's completeness rule |
| grid-nav | engines.egocentric.navigation:GridNav | engines/egocentric/navigation.py:30 | SEVERED | 2026-08-16 | build-scan 2026-08-16: no production caller found |
| marketplace-iced | engines.egocentric.pricing:Marketplace | engines/egocentric/pricing.py:65 | SEVERED | 2026-08-16 | iced BY DESIGN (C33 step 1: bets drive nothing); informative_salience is the live half (pricing-salience row) |
| pricing-hypothesis | engines.egocentric.pricing:Hypothesis | engines/egocentric/pricing.py:33 | SEVERED | 2026-08-16 | helper of the iced marketplace |
| pricing-resolution | engines.egocentric.pricing:Resolution | engines/egocentric/pricing.py:59 | SEVERED | 2026-08-16 | helper of the iced marketplace |
