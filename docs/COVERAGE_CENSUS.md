# Coverage census — measured routing + WIN CEILING of the redux-triality policy across all 25 dev games

Measured live via `run_policy_live`. Two probes: **routing** (max_actions=22, "does it act?") and the **win ceiling**
(max_actions=80, "does it win with the current organs, or die, or stall?"). Numbers are live, not estimated.

| game | family | levels@80 | outcome@80 | died@step | class |
|------|--------|-----------|------------|-----------|-------|
| ar25 | directional | 0 | GAME_OVER | 64 | death |
| bp35 | directional | 0 | GAME_OVER | 16 | death (fastest) |
| cd82 | directional | 0 | action_cap | — | stall |
| cn04 | directional | 0 | GAME_OVER | 75 | death |
| dc22 | directional | 0 | action_cap | — | stall |
| ft09 | click | 0 | action_cap | — | stall |
| g50t | effect | 0 | action_cap | — | stall |
| ka59 | directional | 0 | action_cap | — | stall |
| lf52 | effect | 0 | GAME_OVER | 64 | death |
| lp85 | click | 0 | action_cap | — | stall |
| ls20 | directional | 0 | action_cap | — | stall |
| m0r0 | two_body | **1** | action_cap | — | **WIN L1** (survives) |
| r11l | click | 0 | GAME_OVER | 60 | death |
| re86 | directional | 0 | action_cap | — | stall |
| s5i5 | click | 0 | GAME_OVER | 50 | death |
| sb26 | effect | 0 | GAME_OVER | 65 | death |
| sc25 | directional | 0 | GAME_OVER | 52 | death |
| sk48 | directional | 0 | action_cap | — | stall |
| sp80 | directional | 0 | GAME_OVER | 30 | death |
| su15 | click | 0 | GAME_OVER | 43 | death |
| tn36 | click | **1** | GAME_OVER | 71 | **WIN L1 then dies L2** |
| tr87 | effect | 0 | action_cap | — | stall |
| tu93 | directional | 0 | GAME_OVER | 50 | death |
| vc33 | click | 0 | GAME_OVER | 50 | death |
| wa30 | directional | 0 | action_cap | — | stall |

## Win ceiling — the headline
- **Wins @80 actions: 2/25** (m0r0 L1, tn36 L1). **IDENTICAL to the 22-action probe.** Quadrupling the action
  budget (22 → 80) unlocked **zero** new wins. **The bottleneck is NOT the action budget — it is the win predicate.**
- **Actionable: still 25/25** — every game routes to a driving family and learns which actions have an effect
  (`eff=...` populated on nearly all). The agent acts purposefully everywhere; it just doesn't convert to reward.

## Two honest failure classes (the real frontier)
The 23 non-winning games split cleanly into two mechanically distinct classes:

**DEATH — 13 games hit GAME_OVER (the agent gets killed).** bp35 dies at step 16, sp80 at 30, su15 at 43. The
agent walks into a game-over transition it never learns to avoid. This is a **general, non-fabricated lever**: the
reward residual R_ρ carries a strong *negative* signal (the run ending) that the current stack does not use to steer
*away*. A survival / hazard-avoidance organ — "the last action before GAME_OVER is to be avoided in that state" —
is a domain-general win-adjacent improvement that needs no per-game code and no minted novelty. tn36 shows this
sharply: it WINS L1, then dies on L2 — death, not stall, is what caps it.

**STALL — 12 games survive to the 80-cap with no win and no death.** reach-target / curiosity / effect-press all
exhaust without ever triggering reward. For these the win predicate is genuinely unlearned — this is **mint_gate /
human-confirmation territory** (a novel win-predicate per game). NOT fabricated here.

## Honest notes
- The census measures live behavior, not a claim of competence. levels-0 on a routed game = acts but the win
  mechanic is unlearned (expected; winning is the hard part).
- ka59 routes DIRECTIONAL though the charter calls it two-body; under the tightened `is_coupled` bar it doesn't
  present as a clean mirror in this probe. A finding to revisit, not a mis-fix.
- **Next lever (highest general value): the DON'T-DIE organ** for the 13 death games — avoid the GAME_OVER
  transition from R_ρ's negative signal. Then win-predicate mining for the 12 stalls (mint-gate territory).

## Beat H — the DON'T-DIE organ closed the DEATH class (live, 80 actions each)
`survival.DeathMemory` + the post-death RESET retry loop, run on all 13 death games:
- **beat G: 13/13 ended in GAME_OVER. beat H: 13/13 now SURVIVE to the action cap** (0 end on GAME_OVER).
- **distinct_death_causes == deaths on EVERY game** — no death cause ever repeated (the exact-board veto works as
  designed). Most die once, record the cause, never die that way again; bp35 (fastest death @16) died 4× with 6
  vetoes then threaded a survivable maze path. Rendered bp35 = a real avatar navigating corridors across resets.
- **HONEST: survival ≠ win.** Only tn36 still reaches a win (L1, unchanged). The 13 DEATH games became STALL games
  — full budget to explore now, but the win predicate stays unlearned (mint-gate territory). Removing death as a
  confound is real, general progress on the right axis, NOT a new win count. Win tally still 2/25 (m0r0, tn36).

## Provenance / integrity note
Run under `python3.12` (the interpreter carrying the online ARC-AGI-3 SDK, `arc_agi.Arcade` +
`OperationMode.ONLINE`). On the container this beat ran in, the default `python3` had silently become 3.11 carrying
the WRONG package (the static `arc-agi==0.0.7` dataset lib, no `Arcade`) — a first probe under it errored on every
game (ImportError) and those poisoned rows were discarded, not recorded. The live stack fails LOUD on the wrong SDK
(no fake wins possible); a guard + the interpreter requirement are now pinned so a future run cannot silently drift.

## Beat N — DEFINITIVE OFFICIAL-HARNESS run, all 25 games, one scorecard
Ran every dev game end-to-end through the ACTUAL official ARC-AGI-3 `Agent.main()` loop (ReduxAgent), one shared
scorecard: **https://arcprize.org/scorecards/8a41d995-fdaa-4e77-85b6-946d1cb4c20a** (25 games / 72s).
- **25/25 ran with ZERO errors** through the official contract; families directional 13 · click 7 · effect 4 · two_body 1 (0 undrivable).
- **ALL 25 ended NOT_FINISHED at the action cap — ZERO GAME_OVER terminations.** 18 deaths occurred across the set
  and were ALL recovered via the harness RESET path (bp35 died 4×, sp80/su15 2×, and 8 others once) — concrete
  proof the beat-M shim death-retry works at scale (without it, each of those games would have terminated on the
  first death). The don't-die organ is live on the official contract.
- **Wins: 2/25 — m0r0 L1 (two_body) + tn36 L1 (click)** — the honest ledger, now proven through the OFFICIAL harness
  across the full dev set. Remaining 23 need novel win-predicates (mint_gate/human); not fabricated.
The agent is EVAL-SUBMITTABLE and validated at full submission shape.

## §XIX-compliant OFFICIAL-HARNESS run, all 25 (reset_earned gate in force)
After Isaiah's §XIX ruling (option B: a post-GAME_OVER RESET must be EARNED by the agent's own reasoning backed by
evidence from play/game-memory — implemented as "the death taught a NEW avoidable cause"), re-ran all 25 through the
real `Agent.main()` loop with the gate active. One card: **https://arcprize.org/scorecards/ddc1f033-3436-436c-936f-2bbf89d031ae**
(25 games / 62s).
- **25/25 actionable, 0 undrivable, 0 errors; wins 2/25 (m0r0 L1, tn36 L1)** — unchanged, honest ledger.
- **18 deaths, 18 EARNED resets** — every death this run taught a NEW avoidable cause (the dev death-games keep
  hitting fresh fatal boards = genuine learning), so the gate permitted every retry and **0 games ended early**. The
  gate is NOT a no-op: it DENIES a repeat-death with no new learning (unit-tested `test_first_death_earns_reset_repeat_does_not`)
  and ends the session at GAME_OVER per §XIX — this dev set just never repeated a death this run. Each earned reset
  carries the agent's evidence-cited rationale, recorded in the reset reasoning (nothing silent).
The agent is eval-submittable AND §XIX-compliant on the submission path.

---

## SCAFFOLD COVERAGE CENSUS (2026-07-24, post-Brick-5) — where the reasoning scaffold fires

Probed 13 games across every archetype with `run_policy_live(max_actions=50)`, recording family + referents +
relation selected (post-4c target-stability gate) + drive/reinforce counts + deaths + levels. Purpose: measure where
Bricks 1–5 actually HELP vs are inert/mis-fire, before building more (contamination-risky) drivers.

| game | archetype | family | referents | relation | rel_drive | multi_drive | levels |
|------|-----------|--------|-----------|----------|-----------|-------------|--------|
| ft09 | edit-to-match | click | panel | — | 0 | 0 | 0 |
| cd82 | edit-to-match | directional | endpoints,panel | REACH | 39 | 0 | 0 |
| g50t | colour-swap (NOT connect) | effect | endpoints,panel | CONNECT* | 0 | 0 | 0 |
| lf52 | connect click-draw | effect | endpoints,panel | — | 0 | 0 | 0 |
| tr87 | legend-select | effect† | endpoints,panel | — | 0 | 0† | 0 |
| su15 | legend-order | click | endpoints,panel | CONNECT* | 0 | 0 | 0 |
| ls20 | maze-reach | directional | endpoints,panel | REACH | 10 | 0 | 0 |
| ar25 | directional | directional | endpoints,legend,panel | REACH | 40 | 0 | 0 |
| wa30 | directional | directional | endpoints,panel | REACH | 40 | 0 | 0 |
| sc25 | directional | directional | endpoints,legend,panel | — | 0 | 0 | 0 |
| ka59 | multi-avatar (turn-based) | directional | endpoints,panel | REACH | 0 | 0 | 0 |
| bp35 | block-arrange | directional | legend,panel | — | 0 | 0 | 0 |
| m0r0 | coupled two-body | two_body | endpoints | — | 0 | 0 | **1 WIN** |
| tn36 | click | click | endpoints,panel | CONNECT* | 0 | 0 | **1 WIN** |

`*` = harmless CONNECT false-positive (effect/click family → no drive/reinforce; wins untouched).
`†` = tr87 initially MIS-ROUTED to `multi_avatar` (drive 46) — a Brick-5 precision REGRESSION found by this census and
FIXED same beat (see below); re-probe shows `effect`, multi_drive 0.

### What the scaffold does WELL
- **Referent detection (Brick 2) fires broadly** — panel + endpoints on nearly every game; legend on ar25/sc25/bp35.
- **REACH actively NAVIGATES the directional/maze family** — cd82 39, ar25 40, wa30 40, ls20 10 drives/50 steps. The
  agent pilots toward a reference goal, the clearest working value of the scaffold (post-4a goal-lock).
- **The 2 wins are preserved and correctly routed** — m0r0 two_body, tn36 click; the relation/multi-avatar layers never
  touch their committed plans.

### What MIS-FIRES or is INERT (the honest gaps)
1. **Brick-5 MULTI_AVATAR was too loose** — activated on tr87 (legend-select, not multi-avatar) and drove 46 actions.
   ROOT CAUSE: `independent_multi` required only "2 mapped uncoupled bodies", which two co-toggling legend tiles satisfy.
   FIX (this beat): require a SOLO control per body (an action that moves one avatar while the other stays) = evidence of
   genuine separate steering. tr87 re-probes as `effect`; the synthetic 2-avatar routing test still passes; a new test
   asserts co-moving-without-solo is rejected. Wins preserved.
2. **REACH mis-applies on non-maze directional games** — cd82 (edit-to-match) is driven as reach-the-referent (39
   drives) though its win is a tile MATCH, not a reach. REACH treats any directional+referent game as reach; harmless
   exploration, but not solving. (A relation-disambiguation step — try MATCH/ARRANGE too, keep the reward-positive — is
   the general remedy, but their DRIVES are click-tier, which we hold off to protect the tn36 win.)
3. **Edit-to-match click games (ft09) are under-served** — click family, only a panel referent, progress NOT confident,
   no relation engaged. MATCH is measured but not drivable at the click tier (by design, to protect tn36).
4. **CONNECT false-positives** (g50t colour-swap, su15, tn36) — harmless (no action), but noisy telemetry.

### The honest CEILING (surfaced for Isaiah — he holds the general-vs-game-specific fork)
The general scaffold NAVIGATES (REACH drives 4–5 directional games) and REASONS (referents + relation tester fire), but
converts to **0 new wins**. The gap to each next win is game-specific GOAL/GATE identification: WHICH referent is the
true goal (vs a legend/decoy), collect-then-reach key/gate logic, the per-game control model (ka59 turn-based, g50t
colour-swap). These cannot be solved by a purely-general organ without risking the contamination boundary (encoding a
per-game answer). **Recommendation: the general scaffold is at its natural completion; the next wins likely require
either (a) a general GATE/KEY-aware routing + relation-disambiguation layer that still tests against the env's own
reward, or (b) explicit authorization for carefully-bounded game-specific drivers.** Awaiting Isaiah's fork.
