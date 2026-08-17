# PIPELINE AUDIT (2026-08-16, read-only trace, receipts in task record)
CAUSAL STORY (found, not assumed): goals are rarely POSED (upstream break) AND the
selector's exploit branches predate the goal object (correct 2026-02-13/14, condition
died 2026-02-15, ran 6 months) — the two compose. Exploit-waste is downstream symptom.
FINDINGS: 1a no goal lifecycle (rebuilt from pixels each frame; no create/retire).
1b has_goal=True on panel detection alone -> goal:0/0 phantom (conflates "display
exists" with "goal known"; perceiver.py:260-262). 1c 0/0 BLOCKS its own recovery
(Gap-1 gated on `not has_goal`, loop:3092) — live in the log, dead in the decision.
1d goal:n/n is EXPLORATION COVERAGE mislabeled as goal (workspace delta written into
goal fields, loop:3099-3107; docstring admits it). 1e completion FORCES exploit
(cells_remaining<=3 includes 0; loop:3270-3276); no retirement anywhere. 1f exploit
branches goal-blind: `_prior_loaded + map>0.1 or cert>0.2 -> exploit` (loop:3292-3297).
1g dated: convention outlived condition 2026-02-15. 1h INSTRUMENT DEFECT: P: summary
frozen pre-enrichment (loop:3078 vs 3092) — no-goal counts inflated. 2a T:exploit vs
experiment downstream-indistinguishable (same decide(), strategy not in context).
2b goal-less exploit rung FABRICATES a majority-colour objective (exploitation.py:
3319-3331) — the literal mechanism of exploiting nothing. 4a budget strategy-blind.
4b THREE dead throttles: exploitation budget modifier (0 call sites), imagination rung
gated on nonexistent method, frustration escape reads never-written table.
ROLE COLLAPSE (separate trace): incidental w_A/w_B writer/reader inversion noted
(agent_factory writes w_B; operating_mode_system reads it as wA).
FIX PROGRAM NAMED (F1-F8): F1 exploit requires live non-vacuous non-completed goal;
F2 split has_goal (panel-detected vs goal-known; 0/0 never live, never blocks Gap-1);
F3 coverage never written into goal fields; F4 n/n retires -> explore; F5 no fabricated
objectives (no goal_state -> no constraint-solve; fall through); F6 fix P: timing;
F7 dead throttles removed or wired (decide per soundness); F8 w_A/w_B (awaits role
trace). Behavior changes -> prereg + falsifiers + control-arm verdicts per framework.

## WAVE GOVERNANCE (reviewer, 2026-08-16 — binding):
(1) VALUE-VS-EFFECT SWEEP runs BEFORE the wave: for every gate test, does it assert a
VALUE or an EFFECT? The role test asserted a table while the organ was orphaned —
same genus as R_T=0.000 (checks the record, passes either way). Sweep dispatched.
(2) CONFOUND AS-OF: every measurement since f673b9a (2026-08-13) was on a swarm with
zero optimizers/exploiters and NO live budget differentiation — LP arms, rho readings,
rung-4 traffic (86->123) all carry this date as a standing caveat.
(3) ORDERING LAW: F6 FIRST (the instrument timing defect — everything is measured
through it); then the pure inconsistency repairs, no arms needed (F7-single-target-
table, F3 wire-or-delete, F5 orphan, RF6 knowledge/telemetry split) — those remove
things that lie; THEN behavioral changes SINGLY, one change then re-run. Fifteen in a
wave is fifteen confounded arms.
(4) THE CAUSAL STORY IS A HYPOTHESIS WITH A FALSIFIER, registered now: fixing the goal
lifecycle predicts budget goes somewhere useful and levels move. If levels do NOT move
after F1-F8, that is INFORMATIVE, not disappointing: the wasted budget was not the
binding constraint and TARGET-SELECTION is. Named before the wave so the outcome is
readable either way.

## SWEEP CHUNK A (2026-08-16): two more SEVERED organs — the genus grows
S1 ClassFissionSocket (B10, the hidden-type detector): unit-effect-tested green,
   ZERO production callers of note_outcome/resolve; RoleBinder.on_fission never
   called live. Built, tested, dead.
S2 ConditionalMiner/EFFECT_IF (B9, the arity-3 button-door constructor): live router
   constructed WITHOUT miner= (cognitive_loop.py:1612) -> router early-returns;
   conditional_atoms never populated in production. Built, tested, dead.
Chunk A otherwise: wiring/source-scan families all live; bet-spine, click-economy,
efference, decline, cost-flip wires confirmed receiving real inputs. Chunks B/C pending.

## THE FULL SWEEP (2026-08-16): ELEVEN severed organs behind green tests
S-list (worst first): 1 role multiplier fed None forever (known, unfixed). 2 R_T=0.000
is a PRINTED CONSTANT (bracket_rt.py:484-490 hardcodes the string on a key-to-itself
join) — not arithmetic, a literal. 3 AGENT_MOTION family: never fed (animacy never
runs live). 4 ConditionalMiner: live router built minerless (loop:1612). 5 Class-
FissionSocket: zero production callers. 6 MUTE PROBE (W4b, old): observed_counts
hardcoded all-zeros, probe only PRINTED — steers nothing, release never called.
7 FABRICJANITOR: NEVER CONSTRUCTED IN PRODUCTION — compaction has never run (explains
268k-line queues); supervisor docstring defers to a janitor nothing runs. 8 rho
Amendment-2 ladder (rho_at/traffic/report): zero callers — the partition-artifact fix
is unmeasured live. 9 BROKEN_REBINDING bin unreachable (binding_stale never produced,
refit_queue never drained). 10 SymbolicGameplayIntegration never constructed.
11 FalsifiedLedger never constructed (the __init__ re-export hid it from vulture).
Minor: mint ep kwarg uncalled. LISTS 2/3: recent wiring-scan + effect families all
verified LIVE (the AST-wiring discipline works; the severed set predates or bypassed
it). CONSEQUENCE FOR THE WAVE: before behavioral singles, each severed organ gets a
RECONNECT-OR-REMOVE ruling (a wire that was never alive is not a regression to
restore by default — it is an unproven organ entering as a fresh arm), and the
soundness law applies: tests that green on dead organs get effect-upgrades.

## SEAT CORRECTION + TOOLING PROGRAM (2026-08-16)
OWNED: beat reports systematically over-reported capability — the verification standard
was "does the test pass," not "DOES THE WIRE CARRY." Four inert organs were reported as
capability landings (EFFECT_IF, fission, agent-motion, rho ladder); the multi-rung
r0/r1/r2 readings were a tool run BY HAND in a report, never a measurement the system
takes. Same class as the testimony stream: the instrument existed and measured the
wrong thing. NEW STANDARD: a capability is reported landed only with its wire-carry
receipt (a live call site + an effect observed in the books).
TRIAGE (reviewer): DELETE SymbolicGameplayIntegration + FalsifiedLedger (dead weight).
WIRE FIRST the rho ladder (measurement — before anyone reasons about grain again).
NEAR FRONT: ConditionalMiner + ClassFission (absence explains measured failures).
Every reconnection is a FIRST ACTIVATION, not a fix — enters as a fresh arm, singly.
TOOLING (framework-consistent): (1) SEAM CONTRACTS as plain asserts (stdlib — icontract
/pydantic violate ship-clean; the DETECTOR matters, not the library): goal validity,
role-reaches-purse, budget. Converts silent semantic death into a loud crash. (2)
HYPOTHESIS EFFECT-PROPERTIES replacing value assertions ("for any agent, purse ==
multiplier(assigned role)" — fails the day role/specialization diverge). (3) THE R3
AST PASS, mechanized: every field written has a read; every stream a named consumer
(catches specialization/role, sensation rows, frustration table, testimony). (4)
VULTURE RE-EXPORT BLIND SPOT: __init__ re-exports count as uses — the no-orphans
signal was never trustworthy; configure or replace with the AST pass. (5) COVERAGE
--branch on a live episode (never-taken branches = unreachable-by-construction, e.g.
int(6*0.15)=0). (6) MUTMUT UNSTRUCK, scoped to gate suite only: do these tests fail
when the thing they test breaks. CEILING (stated): tools catch inertness; only
conventions catch drift — a frozen instrument owes a violation detector; these are
six-months-to-six-minutes trades, the only trade available.

## TRIAGE RULINGS (Isaiah, 2026-08-16):
WIRE: AGENT_MOTION (yes); BROKEN_REBINDING/refit queue (yes); rho ladder FIRST
(measurement before grain reasoning); ConditionalMiner + ClassFission near front
(first activations, singly). FIX+INCLUDE: role_multiplier. LIARS (remove, F6 group):
R_T printed constant (bracket_rt.py:484 + the test pinning it); mute probe (degenerate
input + unconsumed output — feed real counts + consume, or delete the call). DELETE:
SymbolicGameplayIntegration, FalsifiedLedger (+_Entry dies with its parent). ICE,
DECIDE LATER: FabricJanitor (build trust too low to delete or activate — registered
ICED). LEAVE ICED: Marketplace pair (by design). REVIEWER FLAGS ADOPTED: severed
count=5 is a DRIVE-PATTERN ARTIFACT, not a reading — beat line states it so until the
operator --coverage-file real-game run exists and runs first; UNMEASURED becomes an
explicit registry state (scope gap is not a status).
FOUR UNKNOWNS IDENTIFIED (git-dated): _Entry = FalsifiedLedger's internal decay record
(2026-08-10) — dies with parent. CursorAgency (2026-08-10, Phase 1 port) = own-avatar
displacement-map learner; GridNav (2026-08-10, Phase 2 port) = BFS board navigator —
TOGETHER THE UNWIRED MOVEMENT-GAME STACK (their use case = the six click-less L0
games); nothing currently calls either; surfaced as a pair-decision, not dead weight.
bump_episode (2026-08-12) = explicit ep advance for same-level retries the (game,level)
ordinal cannot see — one cheap call at the episode boundary makes R_T ep stamps
retry-precise; recommend wire-with-stamps.
