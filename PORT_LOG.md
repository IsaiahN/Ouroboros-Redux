# PORT LOG — the egocentric port onto v4-cold

Beat log for a human who was away. Every entry leads with the L2 count against the cold
baseline. Charter: `EGOCENTRIC_PORT_PLAN.md` (§6 fusion, §7 the wheel rule).

---

## ENTRY 1 - 2026-08-10 - THE BASELINE IS FINAL: 20 generations, 1800 episodes, 6 games at L1, ZERO L2. Phase 1 opens.

> ## **L2 count: 0 (baseline 0 — nothing to beat yet; Phase 3 owns that number).**

**The baseline hardened all the way.** Run 2 (gens 10–19) added ZERO new L1 games — the same six
(`ar25 cd82 ft09 lp85 m0r0 r11l`), 85 banked sequences total, max level_completions still 1 in
all 1800 episodes. The lottery's cheap tickets are spent: breadth stalled at 6/25 and depth never
started. DB 425 MB / 20 gens, knowledge pipeline healthy throughout, telemetry-dominated.

**Phase 1 (the self) opens this beat:** verbatim port of `perception` + `self_locus` + `agency`
from `Nexus:src/newhorse/` into `engines/egocentric/`, wrapped by a small `EgoObserver`, wired
READ-ONLY into the loop (logs `[EGO]` lines, feeds nothing). Prereg: `PREREG_PHASE1.md`.
Pre-wire control shas capturing now (4 games, seed 5) → `.runs/p1_controls.json`.

---

## ENTRY 2 - 2026-08-10 - PHASE 1 LANDS READ-ONLY (containment 4/4 byte-identical). Capability OPEN at 2 named / 1 vacuous / 1 under diagnosis - and the vacuous case exposed a stock-v4 crash.

> ## **L2 count: 0 (baseline 0). Phase 1 committed at `493f96c`; Phase 2 CLOSED until capability clears.**

**The build:** verbatim ports (sha1-verified byte-identical to `Nexus:src/newhorse/`) of
`perception` / `self_locus` / `agency` + the `EgoObserver` wrapper; ONE 13-line read-only block
in `record_result`; gate 10/10 re-derived; tests were shown failing first (9F/1P).

**Containment PASSED perfectly:** all four pre-wire shas reproduced exactly - the observer is
provably inert on behaviour.

**Capability NOT yet passed (prereg: fix-or-revert before Phase 2):** `ka59` and `dc22` name a
stable controllable colour; `su15` errors/flaps (diagnosis pending - background assumption or
None frames); `ls20` is VACUOUS - and that vacuity is the beat's discovery:

> ### **STOCK v4'S COGNITIVE LOOP CRASHES ON SOME GAMES AND SILENTLY FALLS BACK TO THE OLD STACK.** `[PTMA-ERR] CognitiveLoop failed: cannot access local variable 'random'` - a shadowed-variable bug. It fired 109 times across the 20-generation baseline (45+64 in the run logs), so a slice of the 1800 baseline episodes never ran the cognitive path at all. `ls20` hits it every episode in hermetic runs. Pre-existing, not Phase-1 damage; the fallback is silent at default log level - the silent-failure class, again, in the loop itself.

**Next:** capability extension on 4 more movement-capable games (seed 6, running); su15
diagnosis; the `[OPEN]` question for Isaiah - whether to fix the stock `random`-shadow bug on
v4-cold (it changes stock behaviour, which the baseline was measured on) or leave it and score
capability only on non-vacuous games.

---

## ENTRY 3 - 2026-08-10 - PHASE 1 COMPLETE: capability CLEARS at 4 non-vacuous games. The crash census grows to 3 of 25.

> ## **L2 count: 0 (baseline 0). Phase 1 fully passed; PHASE 2 (the goal spine) MAY OPEN.**

**Capability, final:** `ka59` `dc22` `cd82` `m0r0` all name a stable controllable colour by the
final third under pure action-contingency - the >=4 threshold is met. `su15` remains the one
genuine non-namer (error-flapping; diagnosis queued, non-blocking). `ls20` `tu93` `tr87` are
vacuous: **all three crash stock v4's cognitive loop every hermetic episode** (the PTMA
`random`-shadow bug) and play on the fallback stack. The [OPEN] question for Isaiah stands and
now matters more: Phase 2 cannot reach those three games until the one-line bug is fixed (as its
own pre-registered, gated change) or they are excluded from the port's scope.

**Phase 1 verdict: both falsifiers resolved.** Containment 4/4 byte-identical; capability 4
named of 5 non-vacuous. The loop now has eyes for its own body on every game where the loop
itself survives.

---

## ENTRY 4 - 2026-08-10 - PHASE 2 v1 PASSES BOTH FALSIFIERS: the wheel exists, it is closed by default, and it steers when signal opens it.

> ## **L2 count: 0 (baseline 0). Phases 1-2 complete; PHASE 3 (ledger + mint, then the L2 attack) is next.**

**Containment 4/4:** every control sha byte-identical - without a confirmed reward the whole
egocentric stack is provably inert (the wheel rule as a measured property, not a promise).

**Consumption 3/4 (threshold >=2):** with the instrument-side forced confirm, `dc22` drove 23
actions toward the market's winner, `m0r0` 15, `cd82` 3; `ka59` accepted the credit and refused
to drive - no established action strictly helped, and the unhelpful-map rule held. The refusal
is as load-bearing as the drives.

**What exists now on v4-cold:** stock v4 (untouched behaviour, byte-verified twice) + an
egocentric layer that knows WHICH body is its own (contingency, not correlation), learns WHICH
action moves it WHERE (live, answer-free), proposes candidate goals from appearance
(cue-proposes), and will steer toward one ONLY once a real level-up confirms it
(reward-disposes). Next: Phase 3a - the falsified ledger + mint (hypotheses die by prediction
error; knowledge compounds only under the MDL guard), then 3b promote/seed, then the L2 attack
scored against the baseline of zero.

---

## ENTRY 5 - 2026-08-10 - PHASE 3a PASSES ALL THREE FALSIFIERS: the fabric is live, the mint is gated, and the pariah loop closed from real play.

> ## **L2 count: 0 (baseline 0). Phases 1-3a complete. Next: 3b (population-scale promote/seed), then 3c - the L2 attack.**

**What the falsifiers measured (re-derived from raw logs and session fabrics):**

| | result |
|---|---|
| containment: empty fabric, 4 control shas | **byte-identical 4/4** - memory does nothing without signal |
| consumption: pre-seeded corroborated ideas | **2/4 diverged** (dc22 drove 12 actions, cd82 3) - threshold met exactly |
| the pariah loop closes from live play | **2 falsifications written back** (ka59, m0r0 reached seeded cells rewardless) |

The refusals matter as much as the drives: ka59 loaded its seed, had no established action that
helped, and refused the wheel (Phase-2 rule holding through Phase 3). The economy now runs
end-to-end in real episodes: seed -> pursue-or-refuse -> confirm(echo)/refute(falsify) ->
write back -> the next agent inherits a corrected market.

**The stack, in Isaiah's terms:** allocentric evolution (stock v4, untouched) underneath;
egocentric self + goal + memory above it; ideas now have authors, prices, reputations and
graveyards. What is NOT yet real: population-scale circulation (3b) and any L2 (3c's number).

---

## ENTRY 6 - 2026-08-10 - 3b'S FALSIFIER FIRED, MECHANISM READ: the credit wire requires a self-centroid, and click games never have one. A real level-up was dropped. The click-side economy is the fix.

> ## **L2 count: 0 (baseline 0). 3b verdict: circulation BROKEN at the mint - not in the fabric, in the credit gate.**

The trial (12 agents, 3 gens, 5346 actions): the observer ran everywhere (514 [EGO] lines), a
REAL level-up occurred on the cognitive path (click-only game, action 84) - and zero CONFIRM,
zero MINT, no fabric dir (lazy: nothing ever appended). The credit branch is gated on the
controllable's centroid; on click games the contingency test can never name a controllable
(nothing moves WITH the choice), so the centroid is None forever and rewards are discarded.
Movement-side economy: proven live in 3a. Click-side: does not exist. Most banked L1s are click
games. Fix prereg'd: PREREG_PHASE3B2.md - credit at the ACTED-ON cell (the clicked cell when
the rewarded action was a click), CLICK_AT ideas, click-drive under the identical wheel rule.

Also measured from source this beat (PREREG_PHASE3C.md): replay episodes RETURN at replay
completion - the remaining budget is discarded; stock v4's only reliable route to L2's doorstep
ends the episode on arrival. The 3c handoff fixes that after 3b2 lands.

---

## ENTRY 7 - 2026-08-10 - CREDIT MADE NON-DROPPABLE AFTER TWO LIVE FIRINGS READ TWO REAL MECHANISMS. THE SCORED RUN LAUNCHES.

> ## **L2 count: 0 (baseline 0). Every phase landed (1, 2, 3a, 3b2, 3b3, 3c). THE SCORED RUN IS IN FLIGHT.**

The live-wire falsifier fired twice and each firing read a real mechanism from logs, never
inferred: (1) click games have no self-centroid -> click rewards dropped -> 3b2 credits the
ACTED-ON cell; (2) the level-up step carries the NEW level's first frame and the controllable
pick breaks exactly then (colour named 4 lines earlier!) -> movement rewards dropped -> 3b3
completes the attribution: click coords -> centroid -> LAST-KNOWN centroid -> bare LEVEL mint.
A real level-up can no longer leave zero trace. Gate 48/48; containment 4/4 after every change
(five consecutive byte-identity verdicts across the whole port).

**THE SCORED RUN (part 1 of 2) is running:** production shape, exact baseline mirror (stock
defaults, fresh box, 10+10 generations). ONE sealed number: any `level_completions >= 2`
against the baseline's ZERO in 1800 episodes. The same run judges the 3b live-wire (a level-up
must mint) and the 3c handoff (post-replay cognitive actions on banked games).

---

## ENTRY 8 - 2026-08-11 - PART 1 OF THE SCORED RUN: ALL THREE LIVE FALSIFIERS PASS. The economy runs in production. No L2 yet (900 eps; the sealed 20-gen window is half open).

> ## **L2 count: 0 of part 1 (baseline 0). Part 2 (gens 10-19) launched on the same box.**

**The live-wire, third firing: PASSED.** 35 level-ups -> 35 CONFIRM -> 35 [EGO-MINT] (zero
dropped rewards after 3b3's non-droppable chain). The fabric materialised: 35 collective ideas
by 18 distinct agents, 46 echo/falsify events, 72 [EGO-SEED] loads by later agents - the
circulation Isaiah asked for, measured live.

**The handoff: PASSED.** 23 [REPLAY-HANDOFF] lines - budget spent standing at level 2's
doorstep for the first time in v4's history ("93 actions replayed - continuing cognitively, 57
remaining"). 51 drive actions steered on confirmed/inherited goals.

**Standing decisions executed:** inheritance = steer-defeasibly (charter, veto cleared); the
crash fix is Isaiah-approved and pre-registered (PREREG_CRASHFIX.md), build held until the
sealed 20 completes; the three healed games will be scored on their own line.

---

## ENTRY 9 - 2026-08-11 - THE SEALED VERDICT: ZERO L2 IN 20 GENERATIONS (baseline equalled, not beaten). The mechanism is read: the agent arrives at the frontier blind and the wheel shut. Two fixes named.

> ## **L2 count: 0 of 1800 (baseline 0 of 1800). The scored number DID NOT MOVE. Said plainly.**

What DID change vs baseline: L2 attempts now EXIST (39 handoffs in part 2 alone spent budget at
the frontier; the baseline spent zero), the economy ran throughout (77 collective ideas, 102
events, 108 seed-loads in part 2), and six games hold L1 (sp80 in, ar25 out vs baseline's set -
the lottery's usual churn).

**Why the door stayed shut, read from post-handoff logs (never inferred):** every handoff shows
`confirmed=False` + `established=[]` - (1) the 93 replayed actions BYPASS the loop, so the
observer/delta-map arrive at L2 empty: the agent has amnesia about its own body at the exact
moment it matters; (2) seeded L1 ideas carry credibility <1 -> sub-threshold price -> the wheel
stays shut (correct per the rule - but it means frontier play is pure blind explore); (3) some
L2 boards kill blind explorers fast (GAME_OVER at 15-60 post-handoff actions).

**Next build (PREREG_REPLAY_FEED.md): the replay is an observation stream.** Frames and actions
during replay are fully known; feeding them through the observer/spine (observe-only, no
decisions) delivers the agent to the frontier with a named body and an established delta map,
for free. Level-scoped ideas queued behind it.

**The crash fix (Isaiah-approved) lands NOW** - the sealed window it waited for is closed.

---

## ENTRY 10 - 2026-08-11 - THE CRASH FIX HEALS THREE GAMES (falsifiers 3/3 + 3/3). Next: the replay observation feed.

> ## **L2 count: 0 of the sealed 1800 (baseline 0). Side-scoreboard opened for the healed trio (ls20 tu93 tr87) per Isaiah's condition.**

One deleted line; three games join the cognitive loop for the first time in v4's history (zero
crashes, full reasoning). Controls updated. The frontier-amnesia fix (PREREG_REPLAY_FEED.md)
builds next: replay frames/actions feed the ego machinery observe-only, so handoff episodes
arrive at level 2 with a named body and an established move-map instead of amnesia.

---

## ENTRY 11 - 2026-08-11 - THE REPLAY FEED LANDS (gate 53/53, containment 6/6). THE RESCORE RUN LAUNCHES: feed live, crash fix live, healed trio side-scored.

> ## **L2 count: 0 (sealed baseline 0 of 1800, sealed port run 0 of 1800). The post-fix era gets its own line.**

Replayed actions now teach the exact loop instance that plays the continuation - the agent
arrives at the frontier with a named body and an established move-map instead of amnesia, and
not one unit of synthetic credit (scanned by gate). The rescore run judges: (1) the feed's
capability falsifier - post-handoff `established` non-empty on >=3 handoff episodes; (2) the
first L2 anywhere, reported on the post-fix line; (3) the healed trio's side-scoreboard.

---

## ENTRY 12 - 2026-08-11 - THE FEED'S CAPABILITY FALSIFIER PASSES: 17 post-handoff episodes with established move-maps (sealed run: zero). Rescore part 2 launched.

> ## **L2 count (post-fix line): 0 of 900 so far. Feed capability: PASSED (threshold >=3, measured 17 of 29 handoffs).**

Agents now demonstrably arrive at the frontier knowing their bodies and controls - the exact
deficit the sealed run's logs named is gone from the logs. Economy healthy (37 mints, 87
seed-loads, 40 drives in part 1). The healed trio plays the cognitive loop (30-42 episodes
each) but holds no L1 yet - empty banks, as every game once had. Part 2 runs; level-scoped
ideas queued behind its verdict to keep one code state per run pair.

---

## ENTRY 13 - 2026-08-11 - RESCORE COMPLETE: ZERO L2 in the post-fix era too (0 of 1800). The remaining obstacle is ARITHMETIC, and v3 already drew the blueprint.

> ## **L2 count: 0 (sealed baseline 0/1800; sealed port 0/1800; post-fix 0/1800). Three swings, every named obstacle removed, door still shut. Said plainly.**

What the fixes bought (measured): L2 attempts went 0 -> 38 per run; agents arrive with
established move-maps; 34 mints; 214 drives. What remains is TICKET ARITHMETIC: level 1 falls
at ~6 games per 1800 blind episodes because EVERY episode buys an L1 ticket. Level 2 gets ~38
short-budget tickets per run (replay fires at p=0.2), each starting its frontier exploration
FROM SCRATCH - nothing L2-side ever accumulates, because under the wheel rule nothing confirms
until the first L2 win. The bootstrap problem evolution solved for L1 with mass parallelism is
unsolved at L2 by orders of magnitude.

**The three levers, all preregable, in cost order:**
1. **Handoff rate** - replay probability 0.2 means banked games spend 80% of episodes blindly
   rediscovering L1 instead of standing at L2. Raising it for banked games is a pure ticket
   multiplier (needs care: replays also serve validation/prestige).
2. **Frontier checkpoints on the live path** - v3's own blueprint (recovered doc, FULLY WIRED
   on the abandoned stack): bank the prefix that reached L2 when the episode dies there; replay
   it; divergence-detect staleness; explore from the doorstep. With the fabric as the store,
   L2 attempts finally COMPOUND across episodes and agents.
3. **Level-scoped ideas** - stop L1 goals polluting L2 priors (smaller effect; the falsify loop
   already prunes them, at the cost of wasted clicks).

Also noted: `[RESONANCE-ERR]` signature drift crashes resonance detection in population runs -
the silent-failure class again; queued.
