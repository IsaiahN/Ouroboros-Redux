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
| fabric-core | engines.egocentric.fabric:KnowledgeFabric | cognitive_loop.py:1492 | LIVE | 2026-08-16 | lazy init + seed once per game; also cognitive_game_player.py:107 |
| observer-core | engines.egocentric.observer:EgoObserver | cognitive_loop.py:1464 | LIVE | 2026-08-16 | replay-path twin at cognitive_loop.py:1388 |
| tracker-core | engines.egocentric.perception:ObjectTracker | engines/egocentric/observer.py:27 | LIVE | 2026-08-16 | also engines/perception/event_detector.py:104 |
| perception-object | engines.egocentric.perception:Object | engines/egocentric/goal.py:131 | LIVE | 2026-08-16 | the typed percept unit; used across goal/observer |
| downsample-ban | engines.egocentric.perception:DownsampleError | engines/egocentric/perception.py:125 | LIVE | 2026-08-16 | [helper] raised in own module; perception is live via tracker-core |
| self-locus | engines.egocentric.self_locus:SelfLocus | engines/egocentric/observer.py:28 | LIVE | 2026-08-16 | contingency self-detection inside the observer |
| goal-manager | engines.egocentric.goal:GoalManager | engines/egocentric/spine.py:32 | LIVE | 2026-08-16 | verbatim port wrapped by GoalSpine |
| goal-spine | engines.egocentric.spine:GoalSpine | cognitive_loop.py:1479 | LIVE | 2026-08-16 | replay twin cognitive_loop.py:1391; drive() pre-empt at cognitive_loop.py:1066 (the ONE wheel site) |
| click-economy | engines.egocentric.spine:GoalSpine.credit_click | cognitive_loop.py:1618 | LIVE | 2026-08-16 | drive_click cognitive_loop.py:1074; falsify write-back cognitive_loop.py:1922; credit the ACTED-ON cell |
| bet-spine | engines.egocentric.betting:BetBook | cognitive_loop.py:1290 | LIVE | 2026-08-16 | commit cognitive_loop.py:1311; settle cognitive_loop.py:2110; committed≠executed → VOID |
| pricing-salience | engines.egocentric.pricing:informative_salience | engines/egocentric/betting.py:98 | LIVE | 2026-08-16 | the live half of pricing.py; Marketplace stays iced (see marketplace-iced) |
| efference-copy | engines.egocentric.binder:RoleBinder.predicted_change_mask | cognitive_loop.py:1684 | LIVE | 2026-08-16 | CK-2a; subtraction consumed at cognitive_loop.py:1709 (observe_attributed) |
| binder-core | engines.egocentric.binder:RoleBinder | cognitive_loop.py:1652 | LIVE | 2026-08-16 | W4c lazy-init block; fed per step at cognitive_loop.py:1709 |
| binder-evidence | engines.egocentric.binder:_ClassEvidence | engines/egocentric/binder.py:80 | LIVE | 2026-08-16 | [helper] internal accumulator of the live binder |
| gamma-store | engines.egocentric.effects:Gamma | cognitive_loop.py:1651 | LIVE | 2026-08-16 | typed EFFECT store over the fabric |
| bank-core | engines.egocentric.bank:PredictorBank | cognitive_loop.py:1653 | LIVE | 2026-08-16 | settle at cognitive_loop.py:1733; every settlement routes |
| router-core | engines.egocentric.router:ResidualRouter | cognitive_loop.py:1657 | LIVE | 2026-08-16 | constructed MINERLESS — the miner wire is the conditional-miner SEVERED row |
| mint-core | engines.egocentric.mint:MDLMint | cognitive_loop.py:1658 | LIVE | 2026-08-16 | consider() at the credit/primal sites; ledger every verdict |
| affect-seed-steer | engines.egocentric.affect:AffectGains.seed_gain | cognitive_loop.py:1889 | LIVE | 2026-08-16 | B5 applied-bias site; AffectGains constructed cognitive_loop.py:1659; starvation+swallow widened, bounded |
| affect-starvation-steer | engines.egocentric.affect:AffectGains.starvation_steer | cognitive_loop.py:1959 | LIVE | 2026-08-16 | R1 explore_boost inside the mute-probe block; synthetic coverage floor may not reach it |
| lp-steer | engines.egocentric.lp_drive:LPDrive | engines/egocentric/affect.py:173 | LIVE | 2026-08-16 | consumed via AffectGains.lp_steer at cognitive_loop.py:3730; bounded, narrated, lp arm only |
| starvation-settle | engines.egocentric.starvation:StarvationBook | cognitive_loop.py:577 | LIVE | 2026-08-16 | settle_episode at end_game; ≤1 per socket |
| swallow-settle | engines.egocentric.swallow:SwallowBook | cognitive_loop.py:614 | LIVE | 2026-08-16 | settle_episode at end_game; ≤1 per block |
| consumer-drain | engines.egocentric.consumer:consume | cognitive_loop.py:594 | LIVE | 2026-08-16 | W1 once-per-episode budgeted drain (budget_n=8) |
| consumer-seed | engines.egocentric.consumer:seed_imports | cognitive_loop.py:93 | LIVE | 2026-08-16 | W1 seed side; called from _seed_imp at cognitive_loop.py:1668 |
| decline-branch | engines.egocentric.consumer:match | engines/egocentric/consumer.py:553 | LIVE | 2026-08-16 | [helper] kind=declined routed at consumer.py:258 (DECLINE_REASONS enum); reached via consumer-drain |
| hydration | cognitive_loop:_hyd_ver | cognitive_loop.py:1661 | LIVE | 2026-08-16 | [helper] A3-1 book-derived verified base; defined cognitive_loop.py:129 |
| goal-abduction-book | engines.egocentric.goal_abduction:GoalBook | cognitive_loop.py:1244 | LIVE | 2026-08-16 | boundary settle via _goal_abd at cognitive_loop.py:120 |
| goal-abduction-plan | engines.egocentric.goal_abduction:abduced_plan | cognitive_loop.py:1247 | LIVE | 2026-08-16 | verified-atom + site + veto gated; deep plan path |
| plan-veto | engines.egocentric.frontier:plan_veto | cognitive_loop.py:1209 | LIVE | 2026-08-16 | B3 frontier veto on the plan site; deep plan path — synthetic coverage floor may not reach it |
| harvest | engines.egocentric.frontier:FrontierBook.load_harvest | cognitive_loop.py:2076 | LIVE | 2026-08-16 | FrontierBook constructed cognitive_loop.py:1991; record_harvest cognitive_game_player.py:759 |
| movement-bias | engines.egocentric.frontier:bias_moves | cognitive_loop.py:3486 | LIVE | 2026-08-16 | B2 bounded bias, never a veto; load_moves cognitive_loop.py:3483; record_moves cognitive_game_player.py:776 |
| salient-prefix | cognitive_game_player:CognitiveGamePlayer._bank_salient_prefix | cognitive_game_player.py:790 | LIVE | 2026-08-16 | [helper] B7 playback channel only; replay via _load_salient_prefix cognitive_game_player.py:325 |
| cost-flip | engines.egocentric.latents:ActionCostEstimator | engines/egocentric/planner.py:166 | LIVE | 2026-08-16 | [alias=ESTIMATOR] KNOBS A2: both live plan sites pass cost_per_action=None and consume the estimate; fail-closed under MIN_OBS |
| mastery-lite | engines.egocentric.mastery:MasteryLite | cognitive_game_player.py:107 | LIVE | 2026-08-16 | replay-probability spine in the player |
| cursor-agency | engines.egocentric.agency:CursorAgency | cognitive_loop.py:2148 | LIVE | 2026-08-16 | FIRST ACTIVATION (the movement-stack pair): fed in record_result from pre/post frames + executed action (1-5); consumed by the [NAV] steer via _nav_step_action at cognitive_loop.py:3794; gate tests/gate/test_movement_stack.py |
| grid-nav | engines.egocentric.navigation:GridNav | cognitive_loop.py:2149 | LIVE | 2026-08-16 | FIRST ACTIVATION (with cursor-agency): traversability from the agency's map + observed frames in record_result; BFS next-step steers the blind 1-4 draw as a capped bias (NAV_BIAS_P<=0.5, Register G GUESSED), narrated [NAV], never a veto |
| rho-ladder | engines.egocentric.rho:rho_report | engines/egocentric/consumer.py:480 | LIVE | 2026-08-16 | S8 FLIPPED (was WIRE FIRST): consume() persists per-pass {r0,r1,r2,traffic} per matched source to collective "rho_readings" (consumer._persist_rho_readings, called consumer.py:700) via rho_report — which drives the whole trio, rho_at (rho.py:174) at rungs 0/1/2 + rederivation_traffic (rho.py:190) both ways, on live books; [RHO] line narrates r0/r2/traffic; stream consumer = the beat protocol (THE_LADDER rung 4); gate tests/gate/test_rho_ladder_live.py |

## INSTRUMENTS (rung-0 reads; invoked by the BEAT PROTOCOL, never by the live path)

An instrument's receipt is not a live-path call site — it is a NAMED CONSUMER in
the read protocol (THE_LADDER.md: "every produced stream needs a named consumer
INCLUDING THE SEAT'S OWN SOURCES — the beat protocol is the stream's consumer, by
name"). The gate's status vocabulary has three words and none of them is
INSTRUMENT, so these rows carry the status the gate can CHECK — SEVERED, i.e. no
production module references the symbol — with `[instrument]` naming the reason
(the same idiom as `marketplace-iced`: severed BY DESIGN, stated not hidden).
That is not a workaround, it is the right guard here: for the efficiency read a
production reference would BE the prohibited state (a rung-0 read becoming a
knob inside the loop), so the inverse-reference assert going red is exactly the
alarm the ITEM-2 QUALIFICATION asks for. Registry vocabulary gap recorded under
THE_LADDER's INEXPRESSIBLE-STATE GENUS; expressing it is the maintainer's call,
not this build's.

| name | symbol | site | status | date | note |
|------|--------|------|--------|------|------|
| efficiency-read | tools.efficiency_read:efficiency_report | tools/efficiency_read.py:310 | SEVERED | 2026-08-17 | [instrument] ITEM 2 (THE_GOALS.md ITEM-2 QUALIFICATION): rung-0 RESOLUTION read — distance-to-that-player per game+level, reference read off disk from replay metadata baseline_actions, observed = MIN over banked winning_sequences/archived_sequences, tail-scoped. Registered READ, NEVER TARGET: no knob, no arm objective, until levels move — a production reference to this symbol IS the prohibited state and this row's inverse-reference assert is the alarm. Every output line carries "one reference run, not a reference distribution" (EXECUTION RIDER 2). Invocation site = the beat protocol (THE_LADDER.md rung 0, levels_completed); output feeds beat reports only. Read-only on every book. Gate tests/gate/test_efficiency_read.py |
| regen-series | tools.regen_series:regen_snapshot | tools/regen_series.py:218 | SEVERED | 2026-08-17 | [instrument] ITEM 3 (THE_LADDER.md THE REPORT FORMAT rider 2, "THE RATIO HAS ONE TERM"): appends one per-fabric SELF-rho snapshot per invocation to .runs/regen_series.jsonl — drift of fabric-now vs fabric-at-its-last-snapshot at rho.rho_at rungs 0/1/2, never averaged. Named consumer = the roving-pool gate pricing, whose second term (regeneration rate) is uncollectable without this series; adoption of that gate is still zero, so it ships as a BEAT-READ COMPONENT and the series accumulates meanwhile. Bounded (max_fabrics/max_atoms/max_digest, truncation flagged), read-only on fabrics, append-only + torn-tail-safe on the series, NO wall clock in the record (stamp passed in — a clock index would be a latent, EVICTION SPEC RIDER 1). Invocation site = the beat protocol (THE_LADDER.md rung 0b/beat read). Gate tests/gate/test_regen_series.py |

## SEVERED ORGANS (the sweep's eleven, + minor, + build-scan finds)

| name | symbol | site | status | date | note |
|------|--------|------|--------|------|------|
| role-multiplier | cognitive_game_player:CognitiveGamePlayer._role_allowance_multiplier | cognitive_game_player.py:240 | SEVERED | 2026-08-16 | S1 [referenced-but-dead] fed None forever — no agent role reaches the call; every purse ×1.0 (known, unfixed) |
| bracket-rt-print | tools.bracket_rt:live_report | tools/bracket_rt.py:484 | SEVERED | 2026-08-16 | S2 R_T=0.000 is a PRINTED CONSTANT on a key-to-itself join (tools/bracket_rt.py:484-490), not arithmetic |
| agent-motion | engines.egocentric.bank:AGENT_MOTION_ENABLED | engines/egocentric/bank.py:209 | SEVERED | 2026-08-16 | S3 family never fed — animacy never runs live; flag True, branch dead (bank.py:209-264) |
| conditional-miner | engines.egocentric.effects:ConditionalMiner | cognitive_loop.py:1657 | SEVERED | 2026-08-16 | S4 live router constructed WITHOUT miner= → early-returns; conditional_atoms never populated; triage NEAR FRONT |
| class-fission | engines.egocentric.bank:ClassFissionSocket | engines/egocentric/bank.py:285 | SEVERED | 2026-08-16 | S5 zero production callers of note_outcome/resolve; RoleBinder.on_fission never called live; triage NEAR FRONT |
| mute-probe | engines.egocentric.verdicts:MuteHandler.mute | cognitive_loop.py:1973 | SEVERED | 2026-08-16 | S6 [referenced-but-dead] observed_counts hardcoded all-zeros at the call; probe only PRINTED; release() never called — steers nothing |
| fabric-janitor | engines.egocentric.janitor:FabricJanitor | engines/egocentric/janitor.py:60 | SEVERED | 2026-08-16 | S7 NEVER CONSTRUCTED in production — compaction has never run (explains 268k-line queues) |
| broken-rebinding | engines.egocentric.router:BROKEN_REBINDING | engines/egocentric/router.py:71 | SEVERED | 2026-08-16 | S9 bin unreachable — binding_stale never produced, refit_queue never drained |
| symbolic-gameplay | engines.reasoning.symbolic_reasoning_engine:SymbolicGameplayIntegration | engines/reasoning/symbolic_reasoning_engine.py:2274 | SEVERED | 2026-08-16 | S10 never constructed in production; triage DELETE (dead weight) |
| falsified-ledger | engines.egocentric.falsified_ledger:FalsifiedLedger | engines/egocentric/falsified_ledger.py:63 | SEVERED | 2026-08-16 | S11 never constructed; the __init__ re-export hid it from vulture; triage DELETE (dead weight) |
| falsified-ledger-entry | engines.egocentric.falsified_ledger:_Entry | engines/egocentric/falsified_ledger.py:56 | SEVERED | 2026-08-16 | helper of S11 — dies with its ledger |
| mint-ep-kwarg | engines.egocentric.mint:MDLMint.consider | engines/egocentric/mint.py:191 | SEVERED | 2026-08-16 | minor [referenced-but-dead] the ep= kwarg is never passed by any caller (internal counter used everywhere); consider() itself is the LIVE mint-core wire. 2026-08-16: bump_episode() now fires once per boundary at the end_game settle (cognitive_loop.py:640) so the INTERNAL ordinal is retry-precise — the kwarg stays unpassed |
| marketplace-iced | engines.egocentric.pricing:Marketplace | engines/egocentric/pricing.py:65 | SEVERED | 2026-08-16 | iced BY DESIGN (C33 step 1: bets drive nothing); informative_salience is the live half (pricing-salience row) |
| pricing-hypothesis | engines.egocentric.pricing:Hypothesis | engines/egocentric/pricing.py:33 | SEVERED | 2026-08-16 | helper of the iced marketplace |
| pricing-resolution | engines.egocentric.pricing:Resolution | engines/egocentric/pricing.py:59 | SEVERED | 2026-08-16 | helper of the iced marketplace |
