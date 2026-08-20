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

---

## ENTRY 26 - 2026-08-12 - C33 STEP 1 LANDS: every action carries a bet. The iced spine returns, byte-verbatim, consumer-less, on the fabric.

> ## **L2 count: 0 (compound2 still grinding, old budgets; the census run just launched with bets live). Gate 92 -> 101; containment 6/6 - TWELFTH consecutive.**

The 89-line pricing core that survived nine lifecycles on the iced branch is back, sha-verified
byte-identical, now writing lineage-bearing settlement records to the fabric (the ledger the
affect replay-test and the rooms' admission rule both need). The three paid-for laws are in
from commit one: counterfactuals void, family-best floor, executed-action discipline. The
debasement field (nontrivial) rides every record. NO CONSUMER by prereg - a gate test fails if
any decision path ever reads a bet score; the wheel rule will decide consumers in the rooms
step. Capability judge launched: a fresh production box whose settlement ledger IS the band
census re-run + debasement report.

Also this beat: the §12 correction recorded (temporal-not-spatial, the single-atom constructor
requirement, operator_effect.py as harvest v2's reference implementation) - the spatial
two-place null (30 mints, zero levels) is v2's standing warning.

---

## ENTRY 27 - 2026-08-12 - THE ASSEMBLY IS COMPLETE. Ten components, five waves, one loop -- built in one day from contracts argued to consensus. THE RESTART LAUNCHES.

> ## **L2 count: 0 (the pre-assembly lines are closed; the assembly line opens now). Gate 101 -> 162. Containment: thirteen consecutive byte-identity verdicts across the entire port.**

What now runs in one loop, none of it hand-tuned, all of it narrated: a self that knows its
body by contingency; roles bound by invariance and re-earned at boundaries; every action a
bet across every bound slot; every settlement binned; atoms minted only where compression
pays, priced so causal transforms beat routes at n=1; composites keyed as atoms (the letters
wall structurally closed); a computed, FALSIFIABLE objective; a planner that spends verified
operators against it under the wheel rule; affect as two ledger-computed gains with the
replay test; mute closed with the empowerment probe; and underneath it all the fabric --
collective, personal, kin -- carrying charts, ideas, outcomes, verdicts and the import agenda
across episodes, runs, deaths and process crashes.

**THE RESTART: assembly1 launches with compound2's fabric carried forward.** Riding it: the
census + debasement judges, binder-binding visibility, mint-split watchdog, [PLAN] shadow/
drive counts, and the only number that was ever the point -- level 2, on the budget-restored
line, attempted for the first time by an agent that can read what a level wants and plan
what to spend on it.

---

## ENTRY 28 - 2026-08-12 - THE SWARM IS LIVE: 25 workers, one per game, one shared economy. Plus the restart's first finding fixed same-hour (the starving mint).

> ## **L2 count: 0 (assembly1 mid-run; the swarm's clock starts now). Gate 164/164.**

assembly1's interim logs delivered the restart's first live finding within the hour: [MINT] 0
- the mint only ate BROKEN-mechanism, which requires a known atom to be wrong, and a fresh
Gamma knows nothing. Fixed (5ea2a46): NOVEL workspace evidence is the mint's first meal,
through the same affect bar, filtered by the mint's own guards. The fabric-seeds env landed
in the same commit (unset = byte-identical; thirteen containment verdicts still stand).

**THE SWARM (Isaiah's items 1-4, executed):** 25 workers spawned, one per game, breadth-equal
per his ruling, each cross-mounting every sibling's fabric read-only (re-evaluated per episode,
so late-appearing siblings join automatically) plus the compound2 inheritance. Supervisor
restarts dead workers and writes status every minute. Every worker carries the FULL assembled
loop: binder, bank, router, bootstrapped mint, planner (wheel-gated), affect, mute, frontier
harvest, mastery, budget restoration. Many bodies, one economy - the v4 vision at n=1 grain.

Queued behind the swarm's first verdicts: assembly1's full judges (item 3, on completion);
the SMART CLEANUP prereg (item 4 - now urgent at swarm scale); alpha precision upgrade;
probe-prune-enumerate.

---

## ENTRY 29 - 2026-08-13 - ⭐⭐⭐ THE FIRST LEVEL 2 IN THE PROJECT'S HISTORY: ar25, banked at 00:36, replicated EIGHT TIMES by three generations. GAMES WON: 0/25 -- but the depth wall is BROKEN.

> ## **GAMES WON: 0/25. Levels: ar25 = 2 (FIRST EVER, x8 reps, banked 58-action L2 sequence seq_4f21a9fc59e3); L1 now held by 7 games (cn04 and sp80 joined). 1,643 episodes overnight across the swarm.**

**The verification (raw, per the discipline):** eight L2-completing episodes in ar25's DB
(gens 9-11, 00:47 through 11:10); the L2 sequence banked at 00:36 and replayed since -- the
ratchet operating at a NEW level for the first time: discover once, bank, routine. Mechanism
read from the worker log: the breakthrough episode reached L2 via the reasoned path on a
FUNDED post-handoff budget (302-450-action episodes -- the budget restoration paying exactly
as Isaiah diagnosed); planner still silent ([PLAN] 0 -- verified atoms only now accumulating).
Attribution line: BUDGET-RESTORED ERA, assembled-machine swarm. Three sealed eras produced 0
L2 in 5,400 episodes; the swarm produced L2 in ~500.

**THE MINT ECONOMY IS ALIVE (post-primal-path):** 79,694 verdicts considered, 493 atoms
accepted -- ALL STRUCTURAL (the letters-wall watchdog reads clean: zero lexical). The guards
filter at 160:1. assembly1 (completed, pre-fix code): 347 eps, its settlement census profiles
all 25 games -- the debasement watch flags lp85 (0% nontrivial of 5,580 settles) and ft09 (9%)
as inertia-pricing candidates exactly as the beat-104-era receipts predicted.

**HERD FIXED:** the first launch's 27 orphans had double-ridden boxes all night (52 procs);
all killed; ONE clean 25-worker herd relaunched on current code. Heartbeat: the cron fired
this beat; the overnight silence (REPL not pumping) is a session-only-cron fragility --
mitigation: the supervisor grinds regardless; a cloud schedule is the durable option if
Isaiah wants one.

**Next beats:** [PLAN] shadow/DRIVE watch (atoms exist; verification chain should light);
fabric_janitor build (cleanup prereg af70593); alpha precision; the lp85/ft09 debasement
follow-up.

## Entry 30 — SWARM BEAT: the venv-launcher trap defused 29 minutes before it fired; the [PLAN] wire goes in

GAMES WON: 0/25. High-water HOLDS: ar25 = L2 (banked, replicating). Levels delta: none —
the same 7 games hold depth (ar25 L2; cd82/cn04/ft09/lp85/r11l/sp80 L1).

SCOREBOARD (raw from 25 worker DBs): episodes 48-111 per game; generations 11-92.

VITALS:
- Mint economy: 88,160 verdicts -> 504 accepted atoms, 100% structural (175:1 filter;
  letters wall clean). Atoms span 22 game/level pairs; census: m0r0 136, tn36 62, lp85 60,
  s5i5 58, ft09 41 (mostly L1-play mints; the L2+ tail is thin).
- [PLAN] = 0 in all logs with 504 atoms banked, two+ beats running -> STARVATION CONFIRMED
  as a condition. Mechanism read: seven conjunctive silent gates (refsnap, level>=1,
  REFERENCE binding, shape, per-game atoms, non-empty plan). Per C33 §15 silence is not a
  verdict on WHICH gate -> PREREG_PLAN_WIRE registered, builder added per-gate counters
  ([PLAN-GATE] line every 200 cycles, narration only, record_result untouched). Gate
  167/167 green, failing-first shown. Verdict next beat: the first gate that collapses
  to ~0 is the starvation site; the fix gets its own prereg.
- Import queue: 165,956 records across 25 fabrics — fabric_janitor urgency rising.

HERD — THE VENV-LAUNCHER TRAP (the beat's find): Windows venv python.exe is a LAUNCHER
that spawns the real interpreter as a child. Supervisor v2 tracked launcher pids, so
(a) the memory cap watched a 3MB stub (rss=0 all beat — blind), and (b) p.kill() at the
2h recycle would have killed only launchers and ORPHANED all 25 real workers into
double-riding their boxes. First recycle was ~29 minutes away when caught. v3/v3.1
(37914e3, 0fd2c89): taskkill /T tree kills, tree_rss() sums launcher+child, wmic replaces
the powershell poll (cold-start >45s under load, timed out), empty polls announced loudly.
rss now reads real workers (204-288MB). Swarm restarted instrumented: 25/25 verified as
process pairs, all post-dating the wire build. Fabrics, banks, and the ar25 L2 bank
persisted through all three restarts, as designed.

C33: §16 committed (670e903) — signature-first recognition corrects §14's candidate-first
consumer spec; seq-provable conditions; expiring eliminations; the silent-failure caution.
(§17 provenance-sort draft was REJECTED at commit by Isaiah — held uncommitted pending
his direction.)

## Entry 31 — THE WIRE SPEAKS + THE CK DIRECTIVE: Core Knowledge wiring begins

[PLAN-GATE] first data (lp85, two episodes): (A) g1..g6=194, g7=0 — every gate passes,
atoms present, slots bound, and the planner returns an EMPTY plan 194/194 times: raw
pixel-patch atoms cannot compose to unseen states (the variable-binding wall). (B) g4=0 —
REFERENCE never binds (the slot-binding wall). Both walls real; g7 is the deeper one.

ISAIAH'S DIRECTIVE: wire the Core Knowledge ledger into the closure (CK_LEDGER.md
committed; four-year-old test = standing legitimacy gate). Wave CK-1 preregistered
(PREREG_CK_WAVE1) and dispatched to two firewalled builders:
- CK-1a typed parameterized transforms (TRANSLATE/ROTATE/REFLECT/SCALE/COLOUR_PERM) —
  attacks g7=0 via Marcus variable binding + core geometry; raw path kept as fallback.
- CK-1b affordance harvest un-gating — episode-end banking regardless of level/death;
  attacks the 18-game harvest=0 blind-re-exploration finding (Gibson affordances).
Verdict rules registered: g7 moves off zero where g6>0; harvest moves off zero for
level-0 games within one beat.

## Entry 32 — CK WAVE 1 LANDS: the closure gains variable binding and affordances

Both builds verified independently (188/188 gate, failing-first shown) and committed
separately: CK-1a ec773c3 (typed parameterized transforms — TRANSLATE/ROTATE/REFLECT/
SCALE/COLOUR_PERM as open-variable ops; apply_effect fires in never-seen contexts; raw
path intact as fallback) and CK-1b 78d818a (affordance harvest un-gated — level-0
episodes bank dead/effect cells at episode end; read gate kept at level>=1 pending its
own prereg). Swarm restarted on the new closure — all 25 workers uniform, verdict clocks
clean. REGISTERED VERDICTS: g7 off zero where g6>0 (CK-1a); harvest off zero for
level-0 games within one beat (CK-1b). Follow-ups queued: level-0 harvest CONSUMPTION
prereg; g4=0 REFERENCE-binding wall after CK-1a's verdict; CK-2 (Gestalt, physics
predictor families, same/different sigma).

## Entry 33 — THE CLEANER ATE THE CENSUS: evidence-preserving cleanup shipped (725d0f5)

Isaiah caught it from the scoreboard: re86 112->8, tu93 97->12 episode rows. Root cause:
SafeDatabaseCleaner._clean_zero_score_games ran DELETE FROM game_results WHERE
final_score=0 at every recycle — score-based, not value-based. Fixed: rows carrying
EVIDENCE (win_detected, level_completions>0, or score>0) are kept FOREVER; zero-evidence
rows keep the latest 10 generations (stuck-game census); NULL-generation kept. 3
regression tests; gate 191 green. Deployed via supervisor restart; 2 recycles since ran
the new rule (db sizes stable, ar25's L2 rows intact: 21 rows, maxL=2). CASUALTY: the old
rule's final pass (fired at the 120-min recycle ~1 min before the fixed supervisor took
over) zeroed re86 and tu93 game_results entirely — their episode census restarts from
this afternoon; historical counts live only in PORT_LOG entries 29-32. Fabrics, banked
sequences, and all knowledge stores were never touched (separate files/tables).
WATCH: re86 + tu93 wrote ZERO new episode rows in ~2h since — the same two games that
had anomalously few episodes all day. Next beat: read their worker logs (slow-episode or
stuck-loop diagnosis), now visible precisely because the census survives.

## Entry 34 — CK WAVE 2 LANDS: efference copy, inverse closure, surprise pricing

Three builds, three separate commits (4786759, 3840e20, 9e51b86), all failing-first, suite
222/222 verified independently, swarm restarted on the new closure.
- CK-2a EFFERENCE COPY (von Holst): binder attribution = predicted-change-mask subtraction
  (reafference vs exafference). SEMANTIC CHANGE per prereg: REFERENCE = invariant-under-ME
  (a single autonomous event no longer blocks the slot forever — defeasibility); BODY
  guard untouched. Attacks g4=0.
- CK-2b INVERSE CLOSURE + BACKWARD CHAINING (Klein/Newell-Simon): invert_transform per
  ttype; planner meet-in-the-middle, inversion proposes / forward replay proves; stitched
  plans replayed end-to-end. Falsifier: 16-step goal invisible forward-only, found+
  verified bidirectionally. Attacks g7.
- CK-2c SURPRISE WEIGHTING (Rescorla-Wagner): mint support weighted 1/(1+seen) per
  transition signature (coarser than atom key — closes the lp85 same-transition-novel-key
  grind loophole); N repetitions sum ~ln N. Attacks debasement.
REGISTERED VERDICTS OPEN: g4 rises where g3 passes (2 beats); g7 moves on typed-atom
games; lp85/ft09 trivial-mint acceptance falls, structural share holds. CK-3 queue:
conditional-effect constructor (arity-3, the button-door relation), class-fission socket
(hidden types), agent-motion predictor family (cat 14, flagged). Laws on the books:
capacity/content (= the firewall line), composability (one currency, four modes,
transient-then-durable). Builder-detach lesson: two builders backgrounded their suite
runs and stopped early — resumed via SendMessage; future briefs say FOREGROUND.

## Entry 35 — THE THREE READOUTS LIVE: every episode a measurement regardless of outcome

R1 (ecd0a56, SOCKET): starvation codes — fixed six-code enum, StarvationBook pure over
episode counters, <=1 record/socket/episode to the PERSONAL fabric, [STARVE] narration;
consumer = affect.starvation_steer widening the mute-probe cap (steers effort, never
prices; gains() unchanged, gate-asserted). The agent now reads its own residual.
R2 (9b2e62b, proctor-only): socket-vs-filler lint over builder diffs (grids/game-ids/
mappings); CK-1a, CK-2, and R1 diffs all verified socket-clean; PORT_LOG entries carry
SOCKET/CONTENT per build. The agent never reads its grade.
R3 (3dd1631, SOCKET): produced-but-never-consumed is a GATE — AST inventory, 11 fabric
topics, every writer needs a reader or a prereg-cited allowlist entry; stale entries
fail too (monotone tightening). import_queue = the one named orphan (C33 §14-16, CK-3+).
Suite 244/244 verified independently; failing-first shown for R1 and R3; swarm restarted
with readouts live. THE LINE, now plumbing: residual in, grade out.

## Entry 36 — BUILD_PROGRAM_2 EXECUTED: full stop, full build-out, instrument-gated restart

Isaiah's directive: stop everything, build EVERYTHING, QA against instruments only, then
restart. Done in one day: 4 firewalled waves (B1-B21) + a fix wave, all tests-first.
THE TREE GAINED: level-0 harvest consumption; movement affordances; DRIVE frontier veto;
swallow counters (G1); starvation->seed-bias; negative feeder; salient-prefix bank;
OBJECT-LEVEL transform classifier; EFFECT_IF (arity-3); class-fission; agent-motion
family; THE TRIANGULATION CONSUMER (sigma-first, kin-echo law, seq-provable conditions);
sigma at mint + 585-atom backfill; fabric_janitor; OOD lint; compat fixtures; ship-clean
gate; cold-ship smoke; control-arm driver; n=1 metric; settlements carry atom identity.
QA FOUND AND FIXED REAL ROT: lp85 hardcoded across 4 sites in a stock reasoning engine
(the exact id-based nonsense the directive named), a (32,32) literal, unguarded scipy
(the one blocker to true Kaggle parity — cold-ship now passes BARE with zero debt).
FINAL QA (independent): gate 416/416; ruff clean; vulture clean; OOD CLEAN; consumer
gate zero orphans; cold-ship PASS. Commit: single build-out commit post-e0f9c14.
Backfill note: sigma_backfill's process guard fired twice — once correctly (my own
sequencing race), once on the venv-launcher pair (known trap); forced with justification.
SWARM RESTARTED on the complete closure. Registered verdicts (2 beats): g7 > 0 somewhere;
import_candidates > 0 with >=1 TRANSFERRED imported atom; [SWALLOW] baseline; movement
bias visible in the six click-less games.

## Entry 37 — THE HARDENED RESTART: 500/500, every live-audit finding closed

Post-buildout hardening committed (6924448): consumer driver wired (consume at end_game,
seed at init — the queue drains at last), VOID settles, THE BLIND OBSERVER CURED (3D
animation stacks unwrap to the settled grid at one choke point — the ego pipeline had
been blind on animated frames all along), planner node budget (runaway -> 4s shadow),
fabric seq cache (x85-x398), 5 behavioral suites (e2e, cross-wave composition, byte-
identical determinism, soak, torn-writes). FINAL QA independent: 500/500 gate, ruff
clean, OOD CLEAN. Swarm restarted on the complete hardened closure. Registered verdicts
(2 beats): g7 > 0; first cross-game import earns TRANSFERRED; [SWALLOW] ~0 baseline;
movement bias visible. Every bug this build-out found was found by an instrument built
this week.

## Entry 38 — FULLY BUILT: the final gaps closed; the swarm runs the three-arm control

G-A rho (84e27d2): independence numeric — Jaccard over sigma classes, n_eff, collapse-4
guard at 0.9; consumer ranks kin-echo then low-rho. G-B bracket (cdf2cdb): R_T round trip
measured, membrane enforced as code; LIVE FINDING: cn04 re-derived ka59's atom x61 with
R_T=0 — Fig 8's union surplus observed in the wild. G-C goal abduction (bd6a775):
structural predicates from level-up deltas, defeasible credibility, planner predicate
mode for no-reference episodes. G-D LP drive (6a2a1c9): three arms live (fixed 10 /
random 8 / lp 7 by sha1(game)); fixed/random byte-identical proven; lp merges default-on
only if it beats random. QA: 561/561, ruff clean, OOD CLEAN. By the figures' checklist
the system is FULLY BUILT — every mechanism, every metric, drives under controlled test.
Swarm restarted. Open: live verdicts (g7, import TRANSFERRED, swallow baseline, movement
bias, now + LP arm comparison + R_T live once verdicts carry episode ids); push to origin
awaiting Isaiah's word.

## Entry 39 — THE GRAIN FIXES LIVE: verified is book-derived; rho is a distribution

Isaiah's class-of-error audit (KNOBS amendments 2-3) closed in full (fdd37f1, 9e05be3):
verdict stamps (ep + sigma, all four kinds); multi-rung rho r0/r1/r2 + rederivation
traffic — live: cn04-ka59 r*=0.0 on atom sets, traffic=65 (the correlation channel
found); VERIFIED IS BOOK-DERIVED (hydrated from settlements at loop init, cross-episode;
an imported atom verified on the books DRIVES on a fresh episode, test-proven). BONUS
DEFECT caught by the registered level convention DURING the fix: settlements were
written at bare level while consumers read playing level — hydration would have been
unreadable. The registry paid for itself in hours. QA: 602/602, ruff clean, OOD CLEAN.
Swarm restarted with the grain fixes live; the import verdict loses its asterisk.

## Entry 40 — THE DESCRIPTION STEP: residuals characterized at enqueue (Fig 9 closed)

Isaiah's call on the sweep's Finding 1: import_queue records carried {slot,residual,seq}
— named, never characterized (collapse-5 literal). Fixed: sigma computed AT ENQUEUE
(the priority condition where it belongs) + bounded bbox patches (0.25 board fraction,
stricter than the mint's 0.5). Consumer uses persisted sigma verbatim (seq = priority
proof). LP ARM CLOCK RESTARTED automatically: signal scores only sigma-carrying records
— all pre-fix data structurally inert; CUTOFF = this deploy. L1 verified against ls20's
known ground truth (recovers 1,2,2,1,2,1,2 untold) — live cost wiring remains a separate
decision. QA independent: 641/641, ruff clean. POST-DEPLOY READS QUEUED: re-read rungs
r1/r2 once sigma-carrying records accrue (before any rung-3 design); cn04 adoption watch
continues with the pre-staged reject-reason read.

## Entry 41 — THE COST FLIP (beat boundary: readings after this are post-flip populations)

L1 wired live per Isaiah's three conditions (fail-closed MIN_OBS=3; [COST] logs estimate
AND the replaced 1.0 per site; this entry IS the as-of boundary). Feasibility is now
priced by measured cost — in the games where 1.0 was fiction (measured 33-225), plans
that could never finish stop being approved. Next g7/feasibility reads are two
populations: pre/post this deploy. QA independent: 651/651, ruff clean.

## Entry 42 — BEAT (monitor-only): no depth delta; reason counters not yet surfaced

GAMES WON: 0/25. Depth holds (ar25 L2; cd82/cn04/ft09/lp85/r11l/sp80 L1). Herd clean:
25/25, 5 recycles, zero kills. The None-instrument read returned EMPTY at 60KB tails
across 5 workers — either the 200-cycle cadence hasn't fired within the tail window or
verbose logs swamp it; next beat greps deploy-scoped full logs (the as-of rule applies
to log depth too). No changes made — monitor-only. Named reads still pending: reason
distributions, rung re-read, metamer read, cn04 adoption.

## Entry 43 — FIRST ACTIVATIONS DEPLOYED: the movement stack lives; rho measures itself

Movement stack (fb8a7ba): CursorAgency + GridNav LIVE for the first time ever — fed
real move outcomes, [NAV] steering as a capped narrated bias (wheel rule pinned byte-
identical incl. RNG stream at no-confidence); comparative verdict registered (WORSE is
reportable). bump_episode + [RESET] counter shipped instrumentation-only per the split
(guard enters singly only if the counter reports spam). Rho ladder LIVE: multi-rung
readings persisted per drain — grain measurement the system takes itself. Registry gate
caught 17 rotted receipts mid-build and forced refresh (the machinery working). QA
independent: 881/881, ruff clean, OOD CLEAN. Swarm restarted. SEQUENCE NEXT: the liars
(R_T printed constant + pinning test removed; mute probe fed-or-deleted), role
multiplier fix, refit queue + AGENT_MOTION activations, then goal-lifecycle singles.

## ENTRY 30 — 2026-08-18. GAMES WON: 0/25. LEVELS DELTA: 0. THE ARM REPORTED.

**SCOREBOARD, re-derived raw from all 25 worker DBs.** GAMES WON: **0/25** (win counters
summed across the swarm: 0). Levels-completed high-water: **ar25 = L2, UNCHANGED. NO NEW
DEPTH RECORD.** 8 games at L>=1 (ar25 2; cd82, cn04, ft09, lp85, m0r0, r11l, sp80 at 1);
**17 games at L0.** LEVELS DELTA THIS BEAT: **ZERO — the swarm was down for the whole
interval.**

**THE HEADLINE IS NOT THE SCOREBOARD, IT IS THE ARM.** The control arm completed all three
games (full prereg, n = 3 x 12 x 2) and **THE FULL STACK WINS ON CAPABILITY ON ALL THREE**:
ar25 19 vs 11, r11l 34 vs 25, sp80 31 vs 0. The pre-committed branch that fired was
"FULL WINS ON EITHER -> the stack pays; the queue resumes as sequenced", written before the
numbers existed. `win_detected = 0` and `best_level_completions = 1` on every arm — **the
stack beats its comparator and both are at zero against the anchor.**
**AND MY THROUGHPUT NUMBER WAS WRONG THREE TIMES OVER**: sp80 ran both arms in 23m42s where
r11l took 15h22m on identical settings — the difference was MY OWN LOAD, not the stack. The
throughput branch does not fire.

**INSTRUMENT NOTE, and it is the day's third.** My scoreboard's FIRST TWO runs were both
broken — a path split that returned "core_data.db" as the game name, then a query against a
`game_sessions` table that does not exist. **THE FIRST RUN PRINTED "GAMES WON: 0/25" WHICH
IS THE RIGHT ANSWER FOR THE WRONG REASON: it had read nothing.** A new instrument's first
output is a claim about the instrument, and this one would have been cited.
**AND A CONVENTION, NOT A DEFECT:** `action_traces.level_number` and
`i_thread_history.level_number` disagree by **exactly +1 on 25 of 25 games** — completed
depth vs PLAYING level (KNOBS A3-2). Uniform offset, so the two agree; my instrument flagged
25 disagreements because it did not know the convention.

**VITALS.** Not read this beat and stated rather than skipped: mints, [PLAN] shadow vs DRIVE,
seed-loads, import-queue depth, affect sanity and the lp85/ft09 debasement watch **all
require a live swarm** and the swarm was dead for the entire interval. First read with
signal will be next beat.

**HERD.** Supervisor DEAD — `status.txt` 978 minutes stale (16.3 h), zero processes, down
since the arm began. **RELAUNCHED**: exactly one supervisor verified before and after,
52 python processes (25 games x 2 + the supervisor pair), all 25 spawned. Disk `.runs` =
**4.5 GB, under the ~8 GB trim threshold — no trim.**

**ONE IMPROVEMENT: NONE DISPATCHED.** The arm's verdict landing and the swarm coming back
after 16 hours down is the beat. **AND THE RESTART IS ITSELF THE LINK-3 LIVE CHECK** — the
falsifier baseline is locked at **0 `levelup_frames` records above level 1** across the
swarm, and the link-3 hook (shipped as a CANDIDATE, gate-passed, ground-unsettled) must
produce one. That is now running as a consequence of the restart rather than as a separate
build.

### ENTRY 30a — WHAT SWARM MODE ACTUALLY IS, MEASURED (2026-08-18, Isaiah's question)
*"a game takes seconds to complete offline, and 25 games could be done in less than 3
minutes most likely so im curious whats actually being done"*

**IT IS NOT OFFLINE. EVERY ACTION IS A LIVE ARC API ROUND-TRIP.** The arm log carries
`Created new scorecard: ...` and `Successfully fetched metadata for game r11l`; the client
is `arc_api_client.py` over aiohttp, and `arc_api_adapter.py:277 step(action)` returns one
Observation per action. So the loop is network-bound per action, not compute-bound offline.

**AND IT IS NOT PLAYING 25 GAMES. IT IS RUNNING 25 CONCURRENT SEARCHES.** Each worker is
pinned to ONE game and plays it repeatedly: **ar25's worker.log carries 256 episode
boundaries**, and **533,717 ACTION lines are banked across the 25 workers**. Right now ar25
is live at **`levels=2/8`, action 122, budget `G:365/1788`.** The unit of work is not "a
game", it is "an episode", and the point of the swarm is accumulation across hundreds of
them.

**AND THE MEASUREMENT THAT MATTERS: THE BOX IS 13x OVERSUBSCRIBED.**
```
  52 python processes (25 games x 2 + supervisor pair) on 4 LOGICAL CORES
  workers writing within  30 seconds:  0 of 25
                           2 minutes:  1 of 25
                           5 minutes:  4 of 25
                          15 minutes: 17 of 25
```
**A WORKER PRODUCES OUTPUT ROUGHLY ONCE EVERY TEN TO FIFTEEN MINUTES.** My own 25-file
`stat` loop TIMED OUT AT FIVE MINUTES against this load, which is a second reading of the
same fact.

**SO THE ANSWER TO "WHY NOT 3 MINUTES" IS FOUR THINGS, IN ORDER OF SIZE:** (1) the agent
does not know the solution and is searching, not replaying; (2) each action is a network
round-trip; (3) an episode is up to ~1788 actions on ar25, not a handful; (4) **25 workers
share 4 cores, so each runs at roughly 1/13 speed.**

**AND THE QUESTION THAT FALLS OUT, WHICH IS SEAT 3's (TAG: APPARATUS).** Total throughput
is capped at 4 cores either way, so 25-way parallelism does not buy more actions per
second — **it buys 25 shallow searches instead of 4 deep ones, and it makes every worker's
learn->bank->seed->improve cycle ~13x slower.** Learning is SEQUENTIAL inside a worker.
**WHETHER 25 PINNED WORKERS BEATS A SMALLER POOL ON THIS BOX HAS NEVER BEEN MEASURED**, and
it is the same shape as the control arm question one level up. Named, not started.

## ENTRY 31 — 2026-08-18. GAMES WON: 0/25. DEPTH RECORD UNMOVED — AT 1,000x THE SPEED.

**SCOREBOARD.** GAMES WON **0/25**. ar25 **L2**, 7 games at L1, 17 at L0. **NO NEW DEPTH
RECORD.** Same shape as the previous beat.
**AND THAT IS THE BEAT'S REAL FINDING: THROUGHPUT WAS NEVER THE CONSTRAINT ON DEPTH.** The
agent is not reaching L2 and stopping because it runs out of time — it stops for a reason
speed does not touch. **This points AT link 3, and it is a cleaner argument for the queue
order than any timing number was.**

**LINK-3 FALSIFIER FIRED — AND ONLY HALF THE CLAIM CLEARED.**
**MECHANISM: GROUND-SETTLED.** The first `levelup_frames` record above level 1 in this
project's history — ar25, level 2, from the live run. Baseline was 0. The replay hook works.
**VOCABULARY RESULT: NOT SETTLED, AND THE NUMBERS CURRENTLY MEAN NOTHING.** The record
carries `pre (64,64)` against `post (3,64,64)`. Extraction yields **5 predicates from the
malformed input, 0 from `post[0]`, 6 from `post[-1]`.**
**CAUSE LOCATED:** `cognitive_game_player.py:1688` normalises PRE through
`_get_frame_array(pre_obs)`; **POST DOES NOT GO THROUGH IT.** The helper exists precisely
for this — its docstring at `:1946-1974` says *"obs.frame can be ... a list wrapping"* a
grid. **Asymmetric normalisation at one seam.** `post[-1]` is almost certainly the real
post-state and 6 the real reading. **QUEUED, NOT FIXED — and nothing is built on the 5
until it is.** Two claims, and only the first cleared the ground.

**THE OFFLINE SWITCH — AND F1 FAILED, RECORDED AS A FAIL.**
Measured: **11,782 offline steps/sec** against ARC's documented online cap of 600 req/min
= 10 actions/sec. One game, one agent, one pass, **no API key: 5 seconds.**
**F1 (25-game basic set under 10 minutes): FAILED.** 22 of 25 complete past the ten-minute
mark. **THE TIMEOUT WAS MY HARNESS; THE SLOWNESS WAS REAL, AND BOTH ARE TRUE.**
**CAUSE — AND IT IS A CASE THE CORPUS SHOULD CARRY.** A fresh empty box runs a game in
5 s; the same work against a 45 MB (ar25) or 137 MB (bp35) worker box takes minutes.
**REMOVING THE 600/min CEILING MOVED THE BOTTLENECK RATHER THAN REMOVING IT** — the local
DB layer was always costing this and nothing measured it because the API dwarfed it.
**SAME SHAPE AS THE UNBUNDLING LAW: a constant term invisible under a dominant one becomes
dominant when the dominant one is removed, and what remains was always there.**

**SCORECARDS — THE ONE READ ISAIAH ASKED FOR. CREATED AND NEVER CLOSED.**
`close_scorecard` is DEFINED at three levels (`arc_api_adapter.py:614`,
`arc_api_client.py:484`, `core_gameplay.py:465`) and **each definition only calls the layer
beneath it. NOTHING IN `evolution_runner.py`, `game_player.py` OR `cognitive_game_player.py`
EVER CALLS IT.** Not orphaned-per-episode, not a log line printing on attempt: the open half
runs, the close half is never invoked, **and an unclosed scorecard never publishes.** That
is why the public record shows nothing for agents since Aug 3 while our logs report
scorecards being created. **TWO WEEKS, NOTHING NOTICED.**

**THE GENUS, NOW THE PROJECT'S CHARACTERISTIC FAILURE — FOUR INSTANCES THIS WEEK.**
`OPERATION_MODE` (built, plumbed, defaulted to NORMAL, never set) · `close_scorecard`
(defined three deep, never called) · the eleven severed organs · `sequence_miner`.
**THE SWITCH EXISTING AND NEVER BEING THROWN.** Both of this week's cost weeks of silence.

**VITALS.** Not read — the online swarm was stopped for the mode switch and the offline
basic set was still running. Stated rather than skipped.
**HERD.** Online swarm stopped deliberately (0 procs at the switch). Basic set: 24/25 logs,
22/25 complete. Disk 4.5 GB, no trim.
**ONE IMPROVEMENT: the offline switch**, prereg'd at `PREREG_OFFLINE_SWARM.md` with three
falsifiers and a one-line undo. F2/F3 pass, **F1 fails**, and the fix is the DB layer rather
than the mode.

**PROPOSED UPWARD (APPARATUS) — A SCORECARD-LANDED CHECK IN THE BEAT READ.** *Did the run
that was supposed to publish, publish?* **EVERY INSTRUMENT THIS ARRANGEMENT OWNS POINTS
INWARD** — the registry checks wiring, the sweep checks consumption, the rungs read the
agent's own machinery. **NOTHING READS THE PUBLIC RECORD.** Same class as the
operation-mode default, one level further out. To be built to ARC's documented lifecycle
rather than to ours.

**TWO LABELS TAKEN BEFORE ANY OFFLINE NUMBER IS READ.** (i) **The first offline reading is a
claim about the instrument** — if levels-completed moves, the first hypothesis is that the
offline path differs in an unchecked way (same game IDs, same resolved version, same action
budget), not that the agent changed. (ii) **The offline population carries its own label
from the start.** An unlimited-throughput run and a rate-limited scorecard run will diverge,
and pooling them later would be **the same omission a fifth time.**

## ENTRY 32 — 2026-08-18. GAMES WON: 0/25. LEVELS DELTA: 0 ACROSS +25 SESSIONS.

**SCOREBOARD.** GAMES WON **0/25**. ar25 **L2**, 7 at L1, 17 at L0. **NO NEW DEPTH RECORD.**
Sessions 8,495 -> **8,520 (+25, exactly the offline basic set)**. **TWENTY-FIVE FRESH
SESSIONS MOVED DEPTH BY ZERO** — which is the same elimination as the last beat, now with a
clean one-pass population behind it rather than an inference from speed.

**BASIC SET (offline, 25 games x 1 agent x 1 pass): 23 of 25 COMPLETED.** Two did not —
**cn04** (stopped inside near-miss analysis) and **m0r0** (stopped mid-stream) — both at the
600 s per-game cap I set, not on an error. Recorded as incomplete rather than rounded to 25.

**LINK-3 MECHANISM: REPRODUCIBLE.** `levelup_frames` records above level 1: **1 -> 2**. The
replay hook fired again on a fresh session. **THE MECHANISM IS SETTLED; THE VOCABULARY
CLAIM STILL IS NOT** — the `post (3,64,64)` normalisation defect is unfixed and nothing is
built on those predicate counts.

**THE OWED BASELINE CHECK, RUN, AND IT HOLDS.** Seat 4 flagged that my
density-versus-detection elimination rests on "14 of 15 finds were organs born inside the
instrument's own window" — a claim about CREATION dates. Verified with
`git log --diff-filter=A`: `agency.py` **493f96c 2026-08-10**, `navigation.py` **d1e3d5a
08-10**, `falsified_ledger.py` **36d8785 08-10**, `janitor.py` **3a11c15 08-14** — **all
four cited commits are genuine file CREATIONS matching the cited dates**, detected 08-16.
**THE ELIMINATION SURVIVES ITS OWN CHECK:** flat population, changed find-rate.

**VITALS.**
```
  atoms 1,584   mint_verdicts 225,590   settlements 529,154
  import_queue 407,142   rho_readings 14   frontier_harvest 4,449
```
**THE IMPORT QUEUE IS THE VITAL THAT MOVED, AND THE WRONG WAY: ~370k -> 407,142.** It is
GROWING, not draining, and the ranked-drain fix shipped weeks ago.
**225,590 VERDICTS FOR 1,584 ATOMS** — a ~0.7% acceptance rate, unchanged in character.
`rho_readings` at **14** and still read by nothing (rung 0d, unpaired).
**MINT STRUCTURAL/LEXICAL SPLIT: NOT IMPLEMENTED.** My reader guessed `ttype`/`kind` and got
`{'?': 1584}` for every atom — **the instrument does not know the field name, so it reports
NOT IMPLEMENTED rather than a split.** [PLAN] shadow vs DRIVE, seed-loads, affect sanity and
the lp85/ft09 debasement watch: not read this beat.

**HERD.** No supervisor running (0 procs) — the online swarm remains deliberately stopped
pending the offline switch, and the basic set ran as a bounded one-pass session instead.
Disk **4.5 GB**, under the ~8 GB trim threshold, no trim.

**ONE IMPROVEMENT: NONE DISPATCHED.** This beat's work was the owed verification and the
instrument correction, and the rule is one MAXIMUM, not one minimum.
**NEXT, IN ORDER:** (1) the `post` normalisation fix — one seam, unblocks the link-3
vocabulary claim from CANDIDATE to settled; (2) the scorecard lifecycle rebuilt to ARC's
documented pattern, plus the scorecard-landed check proposed upward as APPARATUS; (3) the
import-queue backlog, which is now the loudest vital on the board.

## ENTRY 33 — R3 LANDED: 320x ON THE READ, ~2x ON THE SESSION, AND IT DOES NOT RECOVER THE 6.1x

**F1 · BYTE-IDENTITY: PASS.** Oracle transcribed from the pre-fix code, sharing no code with
the subject, compared by `json.dumps` per record so **key order counts**. 44 tests. Two real
traps caught in the build: `str.splitlines()` **breaks on `\v \f \x85 \u2028`** and would
have split records; and counting LINES instead of RECORDS returns short windows on exactly
the crash-torn streams the live boxes carry. **Both would have shipped green.**
**F2 · THE COST MOVES: 320x** (threshold 10x). `gains()` 115.056 ms -> **0.360 ms** on a copy
of the real 28,772-record stream.
**F3 · THE SESSION: ~69.7 s -> ~33.9 s on live episodes.** Read share of session time
**44.6-45.5% -> 3.7%**; all remaining `fabric.query` time is 0.80 s of 34.2 s.

**AND THE PART I ASKED FOR WHETHER OR NOT IT FLATTERED THE FIX: IT DOES NOT RECOVER THE
6.1x.** Post-fix ls20 is **33.9 s, not 11.7 s**. The read was the leading term and roughly
**half** the gap.
**AND THE BUILDER CHALLENGED MY BASELINE, CORRECTLY.** Sessions take one of two paths — a
**replay-death (~11-14 s)** or a **live episode (~70 s)**. **AN 11-14 s ls20 SESSION SITS
RIGHT ON MY 11.7 s "FRESH BOX" NUMBER**, so my fresh-vs-existing A/B may have compared **two
different EPISODE PATHS rather than two box sizes.** **THAT IS MY FIFTH TIMING ERROR**, same
class as the previous four: a measurement taken under uncontrolled conditions is a
measurement of the conditions — and the uncontrolled condition here was which path the RNG
drew. **THE 6.1x FIGURE IS WITHDRAWN AS A BOX-SIZE MEASUREMENT.** What survives is measured
inside the session: 30 s of read removed, attributed by instrumentation rather than by
subtraction of two whole-session timings.

**ISAIAH'S n=1 RULING ARRIVED INSIDE A BUILD, HOURS AFTER IT WAS MADE.** The builder's FIRST
A/B pair drew different episode paths and **REPORTED THE FIX AS A SLOWDOWN.** It caught this
by running five per arm and then attributing inside the session instead. **One run per arm
was not interpretable, exactly as ruled, and the demonstration was live rather than
argued.**

**MY OWN BREAKAGE, AND IT IS THE SHARPER FINDING.** `ruff` has been failing at HEAD since
`7681ac3` — **10 errors, all in `tools/norm_sweep.py`, MY file** — and
`test_frame_instruments.py::test_ruff_is_clean_on_the_scoped_paths` has been RED for **6
commits, all pushed.** The builder found it, correctly refused to fix it (another seat's
instrument, and folding a formatting diff into an R3 perf change is the scope mixing the
standard warns against), and proved it was not its own with scoped runs. **NOW FIXED; ruff
clean repo-wide; the sweep still returns its known-positive after the edit.**
**AND RUNG 0e FIRES ON MY OWN INSTRUMENT ON THE DAY IT WAS INSTALLED.** `ci.yml` declares
`ruff` a **BLOCKING** check. **SIX COMMITS WERE PUSHED WHILE IT WAS FAILING AND NOTHING
STOPPED THEM.** So either CI never ran, or it ran red and nothing surfaced it. **I INSTALLED
A BLOCKING GATE TWO DAYS AGO AND NEVER VERIFIED IT FIRES** — *did the check that was supposed
to block, block?* is rung 0e pointed one level in, and the answer is no. `gh` is not
installed here, so **I cannot confirm from this box whether the workflow has ever executed,
and that is itself the finding rather than an excuse.**

## ENTRY 34 — 2026-08-18. GAMES WON: 0/25. LEVELS DELTA: 0. SWARM DOWN 193 MIN.

**SCOREBOARD.** **0/25.** ar25 **L2**, 7 at L1, 17 at L0. **NO NEW DEPTH RECORD.** Sessions
8,520 -> **8,521 (+1)**, and that one is **MINE** — the F3 baseline run I took directly
against the real ls20 box. **THE SWARM CONTRIBUTED NOTHING BECAUSE IT WAS DOWN.**

**VITALS.** atoms **1,584** (flat) · mint_verdicts **225,590** (flat) · settlements
**529,287** (+133) · **import_queue 407,283 (+141) — STILL GROWING, STILL NOT DRAINING** ·
rho_readings **14** (flat, still unpaired) · frontier_harvest 4,450.
**MINT STRUCTURAL/LEXICAL SPLIT: NOT IMPLEMENTED** — my reader still does not know the field
name and returns `{'?': 1584}`, so it prints no split rather than a wrong one. [PLAN] shadow
vs DRIVE, seed-loads, affect sanity, lp85/ft09 debasement: **not read — they need a live
swarm.**

**HERD.** 0 supervisors, 0 procs, `status.txt` **193 min stale**. Disk **4.5 GB**, no trim.
Swarm remains deliberately down pending the offline switch.

## THE ONE IMPROVEMENT: THE DURABILITY TEST. **BOTH PREMISES SETTLED, IN OPPOSITE
## DIRECTIONS.**
`tools/durability_test.py` — a child commits 500 rows under production pragmas then dies by
`os._exit(9)`: no close, no atexit, no forced checkpoint. Parent reopens and counts.
```
  autocheckpoint=100     hard-killed  WAL left   412,032 B   rows 500/500  ALL SURVIVED
  autocheckpoint=1000    hard-killed  WAL left 2,220,712 B   rows 500/500  ALL SURVIVED
  autocheckpoint=10000   hard-killed  WAL left 2,220,712 B   rows 500/500  ALL SURVIVED
```
**CHECKPOINT FREQUENCY DOES NOT DECIDE SURVIVAL OF COMMITTED DATA. IT DECIDES WAL SIZE —
412 KB against 2.2 MB, a 5.4x difference — AND THEREFORE REPLAY TIME ON REOPEN.** Measured
here rather than cited from documentation.

**THE TWO MECHANISMS SEPARATE CLEANLY, WHICH IS WHAT THE TEST WAS FOR:**
  **`wal_autocheckpoint=100` — ITS STATED RATIONALE IS RETIRED.** *"Prevent data loss on
  force-close"* is not what the setting does. What it buys is a 5.4x smaller WAL and a
  shorter replay, **at a measured 277x write cost.** That is now a legitimate change
  candidate on an honest trade rather than a safety requirement.
  **`FIX #16` (commit per write statement) — ITS RATIONALE STANDS.** An UNCOMMITTED write is
  lost either way, so committing often genuinely does buy durability. **The transaction
  boundary at the decision remains a real trade — lose up to one decision's writes on a
  kill, for 8.8x fewer flush triggers — and is NOT retired by this result.**

**NEITHER IS CHANGED THIS BEAT.** The rule is one improvement maximum and the test was it.
The pragma change goes next beat with its own falsifier: **the same data written, verified
byte-identically, not merely a faster clock.**

### ENTRY 34a — THE IMPORT QUEUE: ARITHMETIC, NOT A BACKLOG (Seat 4's flag, run)
Seat 4: *a queue that grows monotonically is either an unconsumed channel or a producer
outpacing a drain, and both have been findings here.* **IT IS THE SECOND, AND THE MARGIN IS
NOT CLOSE.**
```
  queue 407,283 over 8,521 sessions   ->  +47.8 records ADDED per session
  drain: consume(..., budget_n=8)     ->   -8   consumed per episode
  NET  +39.8 PER EPISODE, MONOTONIC, FOREVER
  episodes to clear the backlog at 8/ep IF PRODUCTION STOPPED: 50,910
```
`import_queue` is NOT on the rung-0d unpaired list — **it has a real consumer at
`cognitive_loop.py:639`. The channel is wired. THE RATE IS WRONG.** 8 out against 47.8 in
is not a backlog that clears; it is a queue that cannot converge at any runtime.

**AND A SECOND, SEPARABLE DEFECT — REACH.** `consumer.py:402`:
`window = raws[-DRAIN_WINDOW:]`, `DRAIN_WINDOW = 512`. **Only the NEWEST 512 pending records
are ever ranked. 406,771 RECORDS ARE OUTSIDE THE WINDOW AND ARE NEVER EXAMINED AT ALL.**

**THE DESIGN NAMED THIS IN ITS OWN DOCSTRING**, and I shipped it: *"bounded by
construction, never a whole-queue sort, so a characterized record older than the window is
NOT promoted (that is the bound's falsifier)."* **THE BOUND'S OWN STATED FALSIFIER IS NOW
FIRING AT 406,771 RECORDS.** It was an accepted trade — avoid an O(N) whole-queue sort — and
the accepted cost has grown by three orders of magnitude since it was accepted.

**THE TWO DEFECTS RANK, AND THE ORDER MATTERS.** **RATE IS PRIMARY**: at 8 < 47.8 the queue
grows regardless of window size. **REACH IS SECONDARY AND SELF-RESOLVING**: once the drain
outpaces production the queue shrinks, and when it falls below 512 the old records re-enter
the window on their own. **So budget_n is the lever and DRAIN_WINDOW is not** — which is the
opposite of where I would have looked, since the window is the parameter I shipped.

**A READ, NOT A BUILD. NOTHING CHANGED.** `budget_n=8` goes to the premise register as
**PREMISE MOVED** — it was chosen when the queue was small and the drain ran on a
rate-limited online box. **TAG: SUBJECT / GROUND-GATED**, and it needs a falsifier that the
CONSUMED RECORDS ARE HANDLED CORRECTLY at a higher rate, not merely that the queue shrinks.

## ENTRY 35 — 2026-08-18. GAMES WON: 0/25. LEVELS DELTA: 0. SWARM DOWN 306 MIN.

**SCOREBOARD.** **0/25.** ar25 **L2**, 7 at L1, 17 at L0. **NO NEW DEPTH RECORD.** Sessions
**8,521, unchanged.** Swarm down the whole interval; **zero contribution, said plainly.**

**VITALS — every one flat.** atoms 1,584 · mint_verdicts 225,590 · settlements 529,287 ·
**import_queue 407,283** · rho_readings 14 · frontier_harvest 4,450. Mint structural/lexical
split: **NOT IMPLEMENTED** (the reader still does not know the field). [PLAN]/DRIVE,
seed-loads, affect, debasement: **need a live swarm, not read.**

**HERD.** 0 supervisors, 0 procs, status **306 min** stale. **Disk 4.474 GB of the new
30 GB ceiling (14.9%)** — the gate reports UNDER and a run may proceed.
**THE SWARM STAYS DOWN DELIBERATELY.** The basic set has run; **allocation is Seat 3's next
specification** and relaunching 25 pinned continuous workers would revert the design he is
moving away from. Not a stall — a held decision with an owner.

## THE ONE IMPROVEMENT: D-3, THE BLIND VERIFIER. FIXED, GATED, AND IT BROKE A TEST FIRST.
`verify_critical_data()` counted `game_results WHERE final_score > 0` — **the exact key
condemned 2026-02-24 after zero-score deletion destroyed ~80% of the metrics corpus.**
**AND THE SHARPER FACT: `_clean_zero_score_games():683` IN THE SAME FILE ALREADY CARRIES THE
CORRECT EVIDENCE RULE.** The 2026-08-13 correction was applied to the DELETER and not to its
CHECKER. **The fix failed to cross 1,500 lines of the same file**, which is the same shape as
its failing to cross the fork four months earlier.

**FALSIFIERS, both directions, on a fixture with a WIN AT ZERO SCORE and LEVELS AT ZERO
SCORE:**
```
  before:  OLD=1  NEW=3        (1 scored, 2 zero-score-with-evidence, 1 worthless)
  KNOWN-NEGATIVE: the worthless row is counted by NEITHER      PASS
  F2 NO-OP STABLE                                              PASS
  after deleting every zero-score row:  OLD=1   NEW=1
  F1 OLD IS BLIND — ITS COUNT DOES NOT MOVE AT ALL             PASS
  F1 NEW DETECTS THE LOSS, 3 -> 1                              PASS
```
**THE OLD VERIFIER'S COUNT IS UNCHANGED BY THE CATASTROPHE. IT CERTIFIES.**

**AND IT BROKE A TEST, WHICH I CHECKED RATHER THAN ASSUMED.** 4 failures before, **5 after**
— `test_verify_critical_data` was MINE. **NOT the test encoding the defect** (which is what
a wrong fix would have claimed): `no such column: win_detected` on a legacy 3-column fixture.
**I TOOK `_clean_zero_score_games`'s RULE WITHOUT TAKING ITS LEGACY-SCHEMA DEFENCE**, which
that function has at `:686-691` — the normaliser-applied-to-one-side shape, mine this time.
Fixed by building the predicate from the columns that EXIST, and **surfacing
`good_games_evidence_partial` in the stats, because silently reverting to the score-only key
on an old schema would be the blind verifier returning by the back door.**
**Back to the pre-existing 4 failures** (verified by stashing and re-running, not asserted).
ruff clean · OOD clean · sweep `--strict` exit 0.

## ENTRY 36 — 2026-08-19. **GAMES WON: 0/25.** LEVELS DELTA: **L1+ 8 → 9 (sk48, new).**
## L2+ unchanged at 1 (ar25). SWARM WAS DOWN; RELAUNCHED, 25/25 UP.

**SCOREBOARD, re-derived raw from the 25 worker DBs** (MAX `level_completions` + WIN states):
**GAMES WON 0/25. WIN rows: 0.** `maxL` 2, held only by **ar25**. Games at L1+: **9/25** —
`ar25 cd82 cn04 ft09 lp85 m0r0 r11l sk48 sp80`.

**THE HEADLINE IS A DEPTH RECORD AND IT IS SMALL: `sk48` crossed level 1 for the first time
at 05:49:52 today** (2,626 level≥1 traces since). Every other L1+ game first crossed on
08-12/13. **First new game to reach L1 in six days**, and it happened during the twelve-hour
offline run. One crossing in 1,194 sessions is a rate, not a breakthrough.

**AND THE DENOMINATOR IS NOW ON THE RECORD:** worker logs read `levels=2/8`. **A full game
win is 8 levels. The high-water is 2.** The mission distance is larger than the scoreboard's
"L2" has been making it look.

**INSTRUMENT DISAGREEMENT, FLAGGED NOT RESOLVED:** `m0r0` reports `MAX(level_completions)=0`
in `game_results` but `MAX(level_number)=1` in `action_traces`. Two sources, one game, and
they disagree about whether it has ever completed a level. Counted as L1+ on the trace
evidence; **the discrepancy is not chased this beat.**

**HERD.** Supervisor was **DEAD** — no process, no `status.txt`, no log. Relaunched with the
Ouroboros venv python; **25/25 spawned, up 15m, `r/m/c = 0/0/0` on every worker**, no RSS
above 800 MB (cap 1200). Disk **4.88 GB** — under the ~8 GB trim line and 16.3% of the 30 GB
ceiling. **No trim needed, nothing deleted.**
*Noted, not acted on:* the supervisor's `DB_HARD_CAP_MB=600` path empties `TELEMETRY_TABLES`,
**which includes `action_traces` — the table this scoreboard's level evidence comes from.**
Largest box is 145 MB so it cannot fire this beat, but a cap that empties the level record is
D-1's cousin and belongs in the ledger.

**VITALS.** Atoms **1,727 — structural 1,727 / lexical 0**, up from 493 at entry 29.
Mint verdicts **257,863**: `rederivation` 166,071 · `reject` 57,991 · `quarantine` 32,116 ·
**`mint` 1,685 (0.65%)**. Import queue **231 MB / 25 boxes**; settlements **101 MB**.
Starvation book: `MINT_STARVED` 1,409 · `BANK_NO_FAMILY` 254 · `NO_STABLE_REFERENCE` 91 ·
`EMPTY_PLAN` 68 · `NO_REFERENCE_BINDING` 10.

**DEBASEMENT WATCH — the flagged pair is not where the concentration is.** Of **5,644
TRANSFERRED settlements across 59 distinct atoms, TWO atoms hold 77.4%**: `bp35`
`eff-1a405e7e…` at **2,782** and `lf52` `eff-7ee8a672…` at **1,584**. An atom at 2,782 is not
1,391× more verified than one at 2 — **at that point it is a constant, not evidence**, the
same shape as `region_contains_colour` firing on every link-3 record. `lp85` (65) and `ft09`
(56) are unremarkable beside it. **Raised, not repriced.**

## THE ONE IMPROVEMENT: **PREREG ONLY, NOT BUILT — `PREREG_EMPTY_PLAN_ATTRIBUTION.md`.**
The `[PLAN] shadow vs DRIVE` chain is the beat's standing escalation, and it fired: **atoms
exist and shadow/DRIVE are still zero.** The project's own instrument names the step —
`g1=198 g2=194 g3=194 g4=194 g5=194 g6=194` **`g7=0`** `shadow=0 drive=0`. **g7 is
`plan_to_identity` returning a plan WITH STEPS**, and both `drive` and `shadow` increment
inside that branch.

**SO THE 2× TRANSFERRED GATE IS NOT THE BLOCKER — IT IS NEVER REACHED.** 5,644 TRANSFERRED
settlements exist and **32 atoms clear the ≥2 bar**; all 32 are idle because no plan with
steps ever arrives to be checked against them. *Ladder stop rule: diagnose the predecessor.*

**AND I NEARLY REPORTED THIS ON STALE EVIDENCE.** Those `[PLAN-GATE]` lines are from
**08-13/14** and predate `ad441c0` (08-15), which added `gate_summary()` to that very line —
**27 such lines exist in total, ever, from 2 of 25 boxes, none since 08-14.** The instrument
built to answer this question **has never once reported.** The live confirmation is separate
evidence: since the relaunch, across 25 workers, **`[COST]` fired 521 times and `[PLAN]`
fired 0** — `[COST]` prints inside g6 after the planner returns, `[PLAN]` only at g7. **The
planner is returning a plan that carries a cost and no steps, every time, on current code.**

**THE GAP IS ONE FIELD WIDE.** `starvation.jsonl` records *which socket* starved
(`EMPTY_PLAN`, 68 records, no reason); `planner._REASON_COUNTS` records *why*
(`NO_APPLICABLE_ATOMS`/`BUDGET_EXHAUSTED`/`NO_MEET`/`ANCHOR_MISS`/`INFEASIBLE_COST`) but is a
**module global that dies with the worker.** Nothing joins them. The build carries the reason
onto the record — **narration to disk, no decision changed** — with F1 attributes, F2 changes
nothing else (gate counts and actions identical), F3 known-negative (other sockets must NOT
gain the field), and a one-line undo on an append-only stream.

**NOT BUILT, DELIBERATELY: it is agent code, and agent code is a builder's to write.**

**HOUSEKEEPING, mine:** two leftovers from the pre-commit hook verification finally
committed — an uncommitted import-sort fix in `tools/_durability_writer.py` and the deletion
of `tools/_hooktest.py`, the deliberate "should be blocked" fixture. Neither is an
improvement; both were my own uncommitted working-tree state.

## ENTRY 37 — 2026-08-19. **GAMES WON: 0/25.** LEVELS DELTA: **0.** L1+ 9/25, L2+ 1/25.
## AND THE NEW READ THAT MATTERS: **0 OF 25 GAMES ARE TRENDING UP.**

**SCOREBOARD, raw from the 25 worker DBs.** `GAMES WON 0/25` — **`win_detected` rows: 0,
everywhere, ever.** L1+ **9/25** (`ar25 cd82 cn04 ft09 lp85 m0r0 r11l sk48 sp80`), L2+ **1/25**
(`ar25`), maxL **2**, **10,624 sessions**.

**SEAT 3 RULED THE METRIC THIS BEAT: 25/25 completed LOCALLY OFFLINE in WON status, and
`levels_completed` is a decent proxy ONLY IF IT INCREASES toward a full win.** So the trend is
the instrument, not the maximum. Built it — best-ever `level_completions` in each game's first
half of history against its second half:

| game | rows | best ever | best 1st half | best 2nd half | last-20 mean | trend |
|---|---|---|---|---|---|---|
| ar25 | 82 | 2 | 2 | 2 | **1.20** | flat |
| sk48 | 46 | 1 | 1 | 1 | 0.95 | flat |
| lp85 | 81 | 1 | 1 | 1 | 0.80 | flat |
| cd82 | 88 | 1 | 1 | 1 | 0.65 | flat |
| sp80 | 146 | 1 | 1 | 1 | 0.65 | flat |
| ft09 | 30 | 1 | 1 | 1 | 0.15 | flat |
| **cn04** | 50 | 1 | **1** | **0** | 0.00 | **DOWN** |
| **r11l** | 190 | 1 | 1 | 1 | **0.00** | flat, but its last 20 all completed nothing |
| the other 17 | — | 0 | 0 | 0 | 0.00 | flat |

> **GAMES WHOSE BEST-EVER `level_completions` IMPROVED IN THE SECOND HALF: 0 OF 25.**
> **ONE HAS REGRESSED** (`cn04`, 1 → 0), and **`r11l` has completed nothing in its last 20
> episodes despite reaching L1 earlier in its history.**

**THE PROXY, ANSWERED ON ITS OWN TERMS: IT IS NOT INCREASING. ANYWHERE.** Under the rule Seat 3
just set, that makes it a proxy that is currently reporting no progress toward a win rather
than one reporting slow progress. **And it is a better statement than "0/25 won", because it
distinguishes *stalled* from *early*.** *(ar25's last-20 mean of 1.20 also says it does not
reliably reach L2 — it usually completes 1.)*

**VITALS.** Atoms **1,829 structural / 0 lexical**. Mint verdicts **270,126**: `rederivation`
**175,644 (65%)** · `reject` 60,579 · `quarantine` 32,116 · **`mint` 1,787 (0.66%)**.
Starvation: `MINT_STARVED` 1,513 · `BANK_NO_FAMILY` 258 · `NO_STABLE_REFERENCE` 91 ·
`EMPTY_PLAN` 68 · `NO_REFERENCE_BINDING` 10. Import queue **529,101**.
**The three plan-socket codes are UNCHANGED since this morning** (91 / 68 / 10) while
`MINT_STARVED` grew by 104 — **the planner sockets are not starving again; they are not being
reached.** Consistent with g7 and with the ROUTE bin that cannot fire.

**HERD — THE LIVE PROBLEM. 144 MEM-KILLS, AND IT IS ACCELERATING: 8 → 34 → 140 → 144.**
Six workers now, five of them holding 137 of the 144:
`sb26` **35** · `vc33` **27** · `s5i5` **26** · `su15` **25** · `tn36` **24** · `lp85` 7.
`tn36` is sitting at **1,172 MB against the 1,200 MB cap as this is written** — about to go
again. **AND ALL FIVE OF THE HEAVY ONES ARE L0 GAMES.** Falsified as a cause: graph size is
identical across sick and healthy (3,609 edges, 75 nodes both groups), the healthy boxes are
*larger* on disk, and traces-per-session does not separate them. **Nothing measurable from
outside distinguishes them, so the growth is inside the episode and needs a builder-side
memory profile.** Measured cost: the five added +97 sessions against +166 from four healthy
peers — **roughly half throughput, on 20% of the roster, all of it at L0.**
Disk **5.052 GB of 30** (16.8%), under the ~8 GB trim line. Nothing trimmed.

## THE ONE IMPROVEMENT: **PREREG ONLY — `PREREG_SWARM_OFFLINE_MODE.md`.**
**The objective is defined in OFFLINE and the swarm is not running in it.**
`swarm_supervisor.py:122` passes no `--mode`; `evolution_runner.py:1634` defaults to `normal`
(*"both local environments and API"*). **`normal` is an argparse default, not a decision — the
switch was never set and never considered.** Cost today: per-episode `fetched metadata` API
calls, a network dependency and a rate-limit surface on work whose success condition is local.

**The change is one token.** The risk that mattered — *are all 25 games available locally* — is
**already retired by evidence**: the twelve-hour run drove all 25 with `--mode offline` for 47
cycles and every cycle produced 25 sessions. F1 it still plays · F2 the proxy does not regress,
with the last-20 means pinned above as the baseline · **F3 known-negative: it must not IMPROVE
either — a mode change is a channel change, and depth moving in either direction means the two
modes are not the same game.** Undo is deleting two tokens.

**NOT EXECUTED: it restarts all 25 workers, which is a visible cost and Seat 3's to spend.**
One command on the word.

### ADDENDUM TO ENTRY 37 — **THE WIN METRIC IS SOUND, AND THE TOOLKIT IS CURRENT**
Seat 3 pointed at the API's win definition and asked for the toolkit to be checked. Both done,
and the first one is the guaranteed-number test applied to the **primary metric** — the one
number this project is judged by, which had never been shown to be capable of moving.

**THE API'S DEFINITION** (`docs.arcprize.org/api-reference/scorecards/retrieve-scorecard-one-game`):
`state` takes `NOT_FINISHED` · `NOT_STARTED` · **`WIN`** · `GAME_OVER`, and `completed` is a
boolean meaning *terminal* — **`WIN` OR `GAME_OVER`. So `completed: true` is NOT a win**, and
anything reading it as one would count every death as a finish.

**THE CHAIN, VERIFIED END TO END:**
```
arcengine.GameState.WIN.value == 'WIN'          <- matches the API doc exactly
game_player.py:1407   is_win = last_obs.state == GameState.WIN
engines/postgame/orchestrator.py:88   'win_detected': self.is_win or self.is_full_win
database_interface.py:914 / result_recorder.py:95   -> game_results.win_detected
```
**`GAMES WON: 0/25` IS A READING, NOT A BLIND COLUMN.** The comparison is against the correct
enum, the enum carries the correct string, and the writer reaches the table. *This needed
checking precisely because an unwritten column reports zero wins whether or not any occurred —
and it is the number the whole mission is scored on.*

**TOOLKIT — CURRENT IN BOTH VENVS, checked against PyPI directly (neither venv has pip):**
| package | installed | latest | |
|---|---|---|---|
| `arcengine` | 0.9.3 | 0.9.3 | up to date (its only release) |
| `arc-agi` | 0.9.9 | 0.9.9 | up to date |
Identical in `Ouroboros-Redux/.venv` and `Ouroboros/.venv` — **and the second is the one that
matters, since the supervisor launches workers with the Ouroboros venv python.**

**ONE DIVERGENCE, FLAGGED AND LOW PRIORITY:** the API doc lists `NOT_STARTED`; `arcengine`
0.9.3 ships `NOT_PLAYED`. Four members either way, and **`WIN` and `GAME_OVER` are identical**,
so win detection is unaffected. Recorded because a doc/engine name divergence is the shape that
bites whoever next writes a state comparison from the documentation rather than the enum.

**METHOD NOTE — the same error class, caught by one line.** I first checked `arc_agi` and its
`GameState`, and it does not have one. **The live player imports `from arcengine import
GameAction, GameState` (`game_player.py:25`).** Two toolkits are installed and only one is on
the live path. *Reading the import line is what separated them — the same "which thing is
actually live" check that the log-line-as-channel error needed this afternoon.*
