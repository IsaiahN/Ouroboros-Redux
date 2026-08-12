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

---

## ENTRY 14 - 2026-08-11 - 3d-i LANDS: frontier deaths now COMPOUND. Capability run launches.

> ## **L2 count: 0 (three sealed eras, 5400 eps). The first subtractive-search lever is live: every frontier death permanently bans its fatal opening, population-wide via the fabric.**

Gate 62/62 (8 shown failing first); containment 6/6 byte-identical - sixth consecutive clean
containment across the whole port. The builder's own caveat (two level conventions splitting the
avoid-sets between live and handoff pathways) was fixed same-hour with a gate test PROVEN to
catch the old code. Capability falsifier runs next on a population box: fatal-opening records
AND avoid vetoes must both appear, on >=2 games - records without vetoes or vetoes without
records means the loop is open -> fix or revert.

---

## ENTRY 15 - 2026-08-11 - 3d-ii LANDS ON ISAIAH'S CORRECTION: bank the EXPERIENCE, not the death spot. Frontier exploration is now a cumulative population-wide sweep.

> ## **L2 count: 0 (three sealed eras). The compounding is no longer one bit per death - it is the whole episode's experience.**

Isaiah: "where the agent died isn't as important as what it learned about what it explored."
Implemented: every frontier episode (death OR budget end) harvests dead cells, effect cells,
the fatal click, and its established move-map into collective memory. Later agents: dead
(conservatively merged: >=2 reports, never effectful - one positive observation outweighs
silence) and fatal cells remap to the NEAREST UNTRIED cell; harvested deltas pre-establish the
move-map. N frontier attempts stop being N blind draws and become one sweep. Observations,
never signal - the wheel rule untouched. Gate 73/73; containment 6/6 (seventh consecutive).
The 3d-i capability run (in flight, pre-3d-ii code) judges the fatal-veto loop; the NEXT
population run judges the harvest loop (records with non-empty dead/effects; untried remaps;
monotonic coverage growth re-derived from the fabric).

---

## ENTRY 16 - 2026-08-11 - 3d-i CAPABILITY PASSES: 25 fatal openings banked, 435 vetoes fired, and r11l's L2 minefield is being MAPPED death by death. Harvest judge launches.

> ## **L2 count: 0 (still; 900 more episodes). The subtractive loop is proven live: records AND vetoes on 3 games (threshold 2).**

The fabric now holds a charted danger zone for r11l level 1's frontier (19 distinct fatal cells,
clustered rows 51-53 x cols 11-15) plus cd82 (5) and ar25 (1) - exactly the death-by-death
population mapping 3d-i promised. 435 [EGO-FRONTIER] avoid vetoes across 42 handoffs consumed
it. Next box runs the post-3d-ii code: the harvest loop's falsifier (non-empty dead/effects
harvests, untried remaps, monotonic coverage growth) plus the standing L2 watch.

---

## ENTRY 17 - 2026-08-11 - THE ARCHAEOLOGY VERDICT: the full-game wins EXIST, committed on `competition/notebook-v2` (post-v4). Isaiah was right; my "never existed" is RETRACTED. And the winning configuration is the one we have been independently rebuilding.

> ## **L2 count: 0 on v4-cold. On the competition branch: ft09 6/6, tr87 6/6, tu93 7/7, g50t 7/7 - full games, with banked artifacts (9 games of per-level winning sequences in committed JSON).**

**The winning configuration (commit-cited by the archaeology agent):** PTMA + Win Condition
Classifier & Analytical Solver + solver-seeded causal knowledge (H34 - bank effects once, reuse
as priors: their version of our fabric/harvest) + **replay-to-cognitive handoff (H25) tuned to
replay rate 50%** - their version of our 3c + rate lever. We have been re-deriving their winning
stack from first principles without knowing it existed. Convergence is strong evidence both
times; their tuning data (50% vs our 0.8) is a free calibration point for our capability run.

**Also this beat:** the handoff-rate lever landed (057e3d3; gate 75/75; containment 8th
consecutive). Harvest judge interim: 25 harvests, 26 loads - live.

**Next (preregs to follow):** (1) SEED THE BANK from the competition artifacts - 9 games of
banked sequences means handoff+harvest at DEEP frontiers (L2-L6) immediately; runtime knowledge,
not code-encoded answers; the wheel rule governs as always. (2) Port the Win Condition
Classifier - their answer to "nothing knows what winning looks like", which is our conversion
gap by its historical name.

---

## ENTRY 18 - 2026-08-11 - ISAIAH'S RULING: MECHANICS ONLY, NEVER ANSWERS. The seed-bank prereg is dead; the classifier inspection launches under an answer-firewall.

> ## **L2 count: 0. Ruling recorded: banked sequences are answers; answers are garbage OOD; the FUNCTIONALITY is what transfers.**

Killed: seeding the bank from competition artifacts (answers); the per-game puzzle solvers
(answer-encoding in code form). Under inspection with a firewall brief (mechanisms reported,
constants never): the Win Condition Classifier (portable ONLY if it classifies win-condition
TYPE from observation generically), mastery-gated replay (earn the right to replay), and the
proactive level-reset lifeline. The 50% replay-rate precedent stands as a calibration point
(a hyperparameter, not an answer). Harvest judge still running.

---

## ENTRY 19 - 2026-08-11 - THE INSPECTION VERDICTS: the "classifier" was a lookup table in disguise (Isaiah's filter was exactly right); mastery-gating and proactive reset are pure mechanics and PORT.

> ## **L2 count: 0 (harvest judge still running). Three verdicts, answer-firewall held.**

1. **Win Condition Classifier: ANSWER-ENCODED at its core** - it "classifies" by recognising
   memorised per-game identifiers; a never-seen game falls to `unknown`. OOD-worthless, exactly
   as Isaiah predicted. Portable remnant (~150 lines re-grounded): the win-type TAXONOMY, the
   feasibility gate, and the probe-prune-enumerate pattern (probe cells, prune no-ops, enumerate
   small subsets smallest-first) - re-groundable on observations. PORT-PARTIALLY, later (needs
   design work: white-box probing must become real-env probing).
2. **Mastery-gated replay: GENERIC THROUGHOUT (~400-line core). PORT NEXT.** Scores each
   game-level 0-100 from evidence (strategy diversity by edit-distance, ablation robustness,
   cross-agent consistency, efficiency trend); the score sets replay probability (0-95%), with
   tier decay on failing ablations. This SUPERSEDES the 0.8 constant we just shipped: replay
   rate becomes EARNED per game-level - the wheel-rule philosophy applied to replay itself.
3. **Proactive reset: GENERIC. PORT** (after mastery) - the four-cascade decision (learned HUD
   meaning; learned budget stats; stuck detection; coverage-without-progress) that resets BEFORE
   imminent death so the harvest survives. Synergy with 3d-ii is direct: every rescued frontier
   attempt is a bigger harvest.

Queue: mastery-gating prereg next beat; proactive reset behind it; probe-prune-enumerate behind
the classifier re-grounding design. Level-scoped ideas, RESONANCE-ERR, su15 remain.

---

## ENTRY 20 - 2026-08-11 - 3d-ii CAPABILITY PASSES ON ALL THREE CONDITIONS: the population sweep is real (lp85 frontier: 362 cells charted, 22/22 later records adding new ground). One structural gap surfaced: fabrics do not yet carry across RUNS.

> ## **L2 count: 0 (900 more eps). Within-run compounding PROVEN: 54 harvests, 929 untried remaps, monotonic coverage on 4 games re-derived from the fabric raw.**

The gap the numbers surface: each run box starts a FRESH fabric, so the 362-cell lp85 chart dies
with the run. The seed-overlay machinery (built for Kaggle from day one) is the fix and needs no
new code - carry each run's ego_fabric forward as the next run's read-only seed. Self-generated
knowledge, not answers; the compounding becomes cross-run. Queued as run-harness practice (a
driver-script change, not agent code).

Port queue stands: mastery-gated replay next (earned replay probability supersedes the 0.8
constant), proactive reset behind it.

---

## ENTRY 21 - 2026-08-11 - MASTERY-LITE LANDS (the earned replay rate) + THE COMPOUNDING ERA OPENS (fabric carried across runs).

> ## **L2 count: 0. Two moves: replay probability is now EARNED per game (v2's principle, fabric-backed, decaying on failure); and compound1 runs with harvest_cap's fabric carried forward - the first run in this codebase's history that STARTS with charted frontiers (lp85 362 cells, ft09 148, r11l 102).**

Falsifier for the carry-forward: the seeded run's coverage union must strictly contain the
prior run's per game+level. Mastery capability judged on the compounding runs (outcomes
accumulate; failing banks visibly decay). Gate 82/82; ninth consecutive clean containment.

---

## ENTRY 22 - 2026-08-12 - THE CARRY-FORWARD HOLDS ON PARTIAL DATA: lp85's chart grew 362 -> 583 cells ACROSS RUNS. compound1 resumed in place after a session restart.

> ## **L2 count: 0 (compound1 mid-flight, resumed with DB+fabric intact). Cross-run compounding is REAL: strict containment on all four charted frontiers, with growth on two (+221 cells on lp85, +8 on r11l).**

The session restart stopped compound1 mid-episode (37k log lines in). Because everything is
accumulation by design, the resume is a plain relaunch in the same box - the DB keeps its bank,
the fabric keeps its charts, generations continue. The interrupted run had already proven the
point: lp85's frontier chart carried at 362 cells and grew to 583 - a second run's agents
extending a map the first run's agents drew. Also: run boxes unignored by git until now
(add -A sweep); fixed - boxes ignored, falsifier-control JSONs kept tracked. Gate 82/82 on
resume. Mastery capability (replay_outcomes accumulating) judged when compound1 completes.

---

## ENTRY 23 - 2026-08-12 - LEVEL-SCOPED IDEAS LAND; the proactive-reset port KILLED by consumer analysis; compound1 mid-flight with mastery outcomes accumulating.

> ## **L2 count: 0 (compound1 at 231 episodes, 5 replay-outcomes banked -- mastery's live precondition met). Tenth consecutive clean containment.**

Two queue decisions this beat, both evidence-driven: (1) proactive reset NOT ported -- its v2
rationale (knowledge dies at game-over) is obsolete under the fabric (3d-ii harvests at every
episode end), and a mid-episode reset strands the agent at L1 without replay assistance:
strictly worse than dying into the next handoff. Consumer-first law applied. (2) Level-scoped
ideas landed: mints tagged with the level their reward produced; seeds re-scope on every level
change; L1 goals no longer burn frontier budget being falsified at LN. Capability judged on the
compounding runs ([EGO-SEED] level tags; frontier falsify-counts drop).

---

## ENTRY 24 - 2026-08-12 - COMPOUND1 COMPLETE: mastery capability PASSED (130 outcomes, all banks earning their 0.80); coverage compounding hard (lp85 362->949, ft09 809). compound2 launches - the fabric's third hop, all mechanisms live.

> ## **L2 count: 0 (1038 episodes on compound1). The sweep curve: lp85 362 -> 583 -> 949 cells across the run chain; ft09 at 809 (~20% of board). Level-scope capability rolls to compound2 (the resumed process predated that commit).**

The economy self-regulates correctly: every bank at 100% recent reliability keeps its earned
0.80; the decay path stands proven in gates, untriggered because nothing deserved it. compound2
carries the grown fabric forward with level-scoped seeding live for the first time - its judges:
[EGO-SEED] level tags at handoffs, frontier falsify-counts dropping, continued strict coverage
containment, and the standing L2 watch on the deepest charts this system has ever had.

---

## ENTRY 25 - 2026-08-12 - THE BUDGET RESTORATION: replayed levels fund like live levels; the stranded role economy is wired. And the third archive grep found a LIVING organ: alpha.

> ## **L2 count: 0 (compound2 still running on the OLD budgets). From the next run, L2s report on the BUDGET-RESTORED line - the sealed baselines were frontier-starved by design conservatism (3c remainder-only) and role-flat purses.**

Isaiah's two-part directive executed: (a) a replayed level is a completed level for funding -
handoff budget = allowance x (1+levels_replayed) - replay_cost; (b) ROLE_BASE_ATP wired from
his committed table (adaptive_action_limits was built and never called - the stranded-organ
census grows). Gate 92/92; the containment BREAK is expected, documented, and new controls
will be stored post-land (crash-fix precedent).

**The alpha archive verdict (the mirror of the frustration grep): OUTCOME (1) - ALIVE.**
`i_thread.learn_from_outcome` recomputes w_A/w_B at runtime from action outcomes (bounded
0.1-0.9, persisted, 4847 history rows in our baseline). First living organ in three greps.
Caveats -> C33: it is a fixed-step bandit (no EWMA, no precision - exactly the lifetime-drift
disease the alpha design names), and "positive outcome" needs the regulation-style input
trace before its trajectories qualify for the bracket. Alpha is INHERITANCE-WITH-AUDIT: the
build is an upgrade (bandit -> recency-weighted precision ratio), bracketed against
i_thread_history's real trajectories.
