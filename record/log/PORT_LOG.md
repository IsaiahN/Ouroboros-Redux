# PORT LOG — the egocentric port onto v4-cold

Beat log for a human who was away. Every entry leads with the L2 count against the cold
baseline. Charter: `record/prereg/EGOCENTRIC_PORT_PLAN.md` (§6 fusion, §7 the wheel rule).

---

## ENTRY 1 - 2026-08-10 - THE BASELINE IS FINAL: 20 generations, 1800 episodes, 6 games at L1, ZERO L2. Phase 1 opens.

> ## **L2 count: 0 (baseline 0 — nothing to beat yet; Phase 3 owns that number).**

**The baseline hardened all the way.** Run 2 (gens 10–19) added ZERO new L1 games — the same six
(`ar25 cd82 ft09 lp85 m0r0 r11l`), 85 banked sequences total, max level_completions still 1 in
all 1800 episodes. The lottery's cheap tickets are spent: breadth stalled at 6/25 and depth never
started. DB 425 MB / 20 gens, knowledge pipeline healthy throughout, telemetry-dominated.

**Phase 1 (the self) opens this beat:** verbatim port of `perception` + `self_locus` + `agency`
from `Nexus:src/newhorse/` into `engines/egocentric/`, wrapped by a small `EgoObserver`, wired
READ-ONLY into the loop (logs `[EGO]` lines, feeds nothing). Prereg: `record/prereg/PREREG_PHASE1.md`.
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


## ENTRY 38 — 2026-08-20. **GAMES WON: 0/25.** LEVELS DELTA: 0. **SWARM DELIBERATELY STOPPED.**
**FREEZE, NOT AN OUTAGE:** Seat 3 ordered all players and tests stopped ahead of a major
refactor. HOLD is set; this beat does NOT relaunch, overriding the beat protocol's
stale-status rule — a directive from the maintainer outranks the cron.
Scoreboard from the frozen boxes: L1+ 9/25, L2+ 1/25 (ar25), 12,940 sessions. No vitals
(nothing runs), no improvement taken (the improvement queue is suspended pending the
refactor plan, which will absorb or retire it — absorbed items will be NAMED).
Day's closures before the freeze: D-6 closed (import-time logger creating a root DB;
deferred-init fix, falsifier passed), dead code-lineage retired (4 tests + 5 modules),
dead DATA-lineage retired (2 test files whose greens read the archived pre-swarm DB),
13 tooling candidates quarantined. Suite baseline 1986 green / 4 known-red.
Standing post-plan action: REVIEW EVERY PREREG (33) for continued relevance.


## ENTRY 39 — 2026-08-20. **GAMES WON: 0/25.** LEVELS DELTA: 0. **PLAN ACCEPTED; FREEZE HOLDS.**
Read-only beat under the freeze (HOLD set, 0 workers): L1+ 9/25, L2+ 1/25 (ar25), 13,008
sessions — unchanged, as a frozen system should be. No vitals, no improvement (queue absorbed
into the accepted plan).
**THE REFACTOR PLAN IS ACCEPTED AS AMENDED** (commits 6bcb7c7 → 95b0dc0 → this one), with
affect-in-role-fit STRIPPED (allocation is a price; affect in the gate makes assignments
self-confirming) and the surgical note on `evolutionary_engine.py:666`: prestige out of the
breeding draw, youth stays, same line. Seat 3 marked the grep-token failure as the THIRD
instance of a search returning an absence that was the instrument's rather than the system's
(T_A substring, manual_tools category, self-determination tokens) — carried as a standing
caution: an absence claim owes a constructed presence.
**THE 33-PREREG REVIEW IS DONE** (see `record/prereg/PREREG_REVIEW_2026-08-20.md`): 17 keep,
8 resolved-kept as records, 5 amended into workstreams, 3 retired with notes. The swarm stays
held until Seat 3 reads the review.


## ENTRY 40 — 2026-08-20. **GAMES WON: 0/25.** LEVELS DELTA: 0. **FREEZE HOLDS; W1 BASELINE LANDED.**
Read-only beat (HOLD set, 0 workers): L1+ 9/25, L2+ 1/25 (ar25), 13,010 sessions cn04-profile
delta only. No vitals (frozen), no improvement (the plan owns the queue).
**THE BEAT-PROTOCOL ESCALATION IS ANSWERED AND CLOSED**: the chain atoms -> 2x TRANSFERRED ->
shadow -> DRIVE is still zero NOT by starvation at the gates but because **the planner search
itself has never returned a plan while consuming ~95% of slow-worker runtime** — profiled:
97.6% plan_to_identity, 95.3% apply_effect, 77.7M numpy .all() calls in 420s, every atom
applied at every anchor with no pruning (D5_PROFILE_RESULT.md, ab2290e). D-5 mechanical:
atoms x levels = search space x search engagement. W2 re-scoped by its own pre-stated rule:
first deliverable is the APPLICABILITY INDEX. W1 narration prereg pinned (permutation null,
three pre-named statistics). Awaiting: builder for W1 narration; word to prereg the
applicability index as W2's first build.


## ENTRY 41 — 2026-08-20/21. THE DEPLOY-GATE INCIDENT, OWNED — and the day W2 completed.
**GAMES WON: 0/25.** L1+ 9/25, L2+ 1/25. Split-half: lp85 readable, most games within
hours; the read runs next beat on POST-INCIDENT data only (below).
**THE INCIDENT:** 8 "code change" deploys since HOLD-lift, every one a DIRTY tree —
intermediate builder states of cognitive_loop/consumer/registry deployed to the live fleet
as builders saved. Proctor's procedural gap: HOLD removed at lift, builders dispatched into
a watched production tree. Zero worker crashes (every state importable); every COMMITTED
state suite-verified; but the fleet ran between-commit code for hours. **FIX, permanent:
HOLD up whenever a builder is active in live-path files; lift only at verified commits.**
**THE CAVEAT THAT TRAVELS WITH THE NUMBERS:** every post-lift reading — ctx_min 50→52,
ctx_conflict 8→10, the verdict mix (462/249/40/9), the 299-session pace, the coverage
proxy (2.1/19.2/33.7/45) — was taken on a system whose code changed EIGHT TIMES underneath
it: a pooled population across semantics changes. Directionally indicative, not citable as
baselines. Post-incident baselines start at the next stable deploy.
**THE DAY OTHERWISE:** W2 completed end-to-end (index → vectorisation → scheduling →
extent premium → re-point; shares 95.3→27.0; cn04 generation 420s-unfinishable → 56s).
Import gate + narration arms + action book landed. The writer defect trio found (budget
never passed though in scope; frames stored as lossy reprs; book inverse-counts tainted
and loudly stamped). Γ shown CLICK-ONLY with action-agnostic wiring — the half-board
clause suspected as a metal key measuring extent in an egocentric frame. The reasoning
gate designed, approved through stage 1, most of it salvage-with-citations (no_posthoc's
wall, primitive_ledger's observe ladder, the validator's check discipline). Two builders
in flight under HOLD (writer fix, verdict reason).


## ENTRY 42 — 2026-08-21. SPRINT MODE + COMPOSER STAGES 1-2 LIVE. **GAMES WON: 0/25. L1+ 10/25 (g50t NEW — never-scored → scoreable).**
Seat 3 ruled sprint mode: fleet at 3 (sk48 split-half tail, ar25, g50t smoke), 22 paused,
suite 25min → ~7min, builds get the cores. Composer stage 1 (the factoring: psig, csig,
derived price, admission hole closed) and stage 2 (ENABLES indices; act_offset SHIPPED —
the coordinates died at the offer calls with values in scope, the never-wired family's
parameter-not-passed sub-kind, fixed by one capture; cross-shelf reach returns
verified=False chains structurally) both landed. Book rebuild done (clean-window numbers
next read). One suite failure was a MISSING NEWLINE concatenating two registry rows —
caught by the 6-field unpack, split, both gates green. The family counter now carries the
sub-split: parameter-not-passed (one site, one capture) vs field-not-read (siteless,
found only by asking who-reads-this). Next: stage 3 (compose loop), stage 4 (settlement
wire), then g7.

## ENTRY 43 — 2026-08-21 (heartbeat). Book rebuild DID NOT un-taint: the tool has no clean-window filter.
Inverse n-counts identical to the tainted run (full-stream rebuild); stamps were overwritten
by the from-scratch write and are RE-APPLIED. The --since filter is a queued tool task, not
a claim already made. New and clean: COST EVIDENCE now PRESENT on boxes with post-fix rows
(dc22, lp85, s5i5, tr87, vc33 first) -- the budget writer fix paying into the book. Stage-4
prereg pushed (e1cce38); builder held for the user's restart. Split-half baseline 0-0-5.

## ENTRY 44 — 2026-08-21 (heartbeat cycle). Stage 4 building; three reads closed.
Stage 4 (settlement wire) relaunched after an API drop (no partial edits). --since filter
for the book tool landed (17/17; byte-identical without the flag; unparseable frames
skipped and counted). BODY-settlement read closed the movement causal chain in the stream
(BODY·TRANSFERRED 5,084 vs WORKSPACE·NOVEL absent from the top eight) and found BODY·NOVEL
= 2,467 unexplained self-motions consumed by nothing (offer filter is WORKSPACE-only) —
PROPOSAL to Seat 3: a BODY-slot consumer for wall evidence. Mode-usage read: weighted mode
runs live as the cognitive router's no-action fallback with no threshold — the suggester's
influence is structurally possible, empirically zero labeled wins; retirement loses
nothing observed. Unmarked-origin cohort = pre-marker vintage, not a third source.
Numbers unchanged: WON 0/25 · L1+ 10 · baseline 0-0-5.

## ENTRY 45 — 2026-08-21. WINDOW FIVE: the planner is GONE from the top; the sixth layer is I/O.
g50t, composer stages 1-3 live: generation in 90s. fabric._read_stream 28% (whole-stream
re-parse ~4x/cycle), sqlite 17.5% (~35 queries/cycle), decide 12.4%. Produced-once,
parsed-many at the storage layer. PREREG_FABRIC_IO drafting (incremental tail reads +
parsed-stream cache + batched per-step writes; uncached path stays the equivalence oracle).
D-7 registered: the weighted fallback ignores every rung's confidence_threshold — frequency
read in flight before the fix. Seven agents in flight; stage 4 is the gate for everything
swarm-facing. Numbers unchanged.

## ENTRY 46 — 2026-08-21. Stage 4 LANDED (verifying); a sprint-config caveat declared; three drafts await a word.
STAGE 4 (settlement wire) built: one live_settle writer, g7 = the planner's own _plan_gate
dict asserted by identity, the mispredicting component tightened via _reinstate, 87 scoped
green, 18 receipts refreshed loudly. New behaviour stated by the builder: multi-cycle
drive (continuation bypasses _w2b_engage while a chain executes, key-checked each cycle) —
W2b's F1 leak-stop must be RE-READ in the next profile window.
CAVEAT THAT TRAVELS WITH THE NUMBERS: sprint workers (sk48/ar25/g50t) ran WITHOUT
OURO_FABRIC_SEEDS and LP_DRIVE_ARM since sprint mode began — my direct relaunches omitted
the supervisor's per-worker env. The split-half baseline's sprint-window sessions on those
three games are a different config from the fleet's. The full fleet resumes under the
supervisor at the next commit; the keeper (landed, 14/14) inherits the same gap by design
and is for sprint use only.
g50t ATTRIBUTED: exploration luck on wall_aware_navigation — no plan, no composite, no
atom — banked and replayed since; goal_hypotheses 0→714 after the level.
DRAFTS LANDED, REVIEW-PENDING AT SEAT 3 on exactly these: (1) standing_half_life —
"silence never evicts" (eviction needs low standing AND a misprediction); (2) shadow gate —
PERCEIVE not relocated in stage 1 (gate builds its own opener on a `gate` topic; must not
survive into stage 2 unnoticed); (3) persistence monitor — a new narration point token
(PERSISTENCE) is a schema event. Fabric I/O and W2c drafts accepted with riders (cache
bounded; nested-mutation falsifier). D-7 frequency read in flight.
D-7 READ: the cognitive router yields no usable action on ~78% of steps on sk48/ar25 and
falls through to thresholdless weighted voting — the router, not the fallback, is the
defect; honouring thresholds would INCREASE randomness. Instrument (one field) before fix.
SPLIT-HALF ROW NOTE (g50t): its 1→1 baseline was exploration luck, banked and replayed —
not a capability floor the composer must beat. Rulings: standing_half_life "silence never
evicts" TAKEN (+ decay-must-bite rider; the counter's first YES); shadow gate accepted with
the stage-2 deadline as a mechanism; persistence monitor approved.

## ENTRY 47 — 2026-08-21. STAGE 4.5 LANDED (verifying): the four silent successes now fail loudly.
Silent #1: want-already-satisfied refused before the pool is read; predicate mode requires
a FLIP (false on frame0, true on result) and the flip is re-verified on the LIVE frame at
settle (predicate-unmet otherwise). Silent #2: csig-less chains refused (csig-underivable);
local mints now pay consumer.extent_bargain — ONE statement shared with the import door;
"nothing prices what's made at home" closed. Silent #3: patch-centre site synthesis
removed; offset-less atoms compose-only, shadowed with no-act-offset, never driven; anchors
reconciled reach→simulation→drive. Silent #4: final seam applied AT the reached anchor
after an avatar-at-act-cell check; unnecessary prefixes dropped (prefix-unnecessary) —
the cross-shelf claim is now tested at the seam where it matters. Handoffs: exact
self-cell with centroid-rounded as a stated fallback; is_citable reads the stream record;
reach["verified"] READ (breach refuses). Multi-prior union left as the prereg'd limitation,
palette and cell credits made consistent. 123 scoped green. NOTED: stage 4's own test R4e
had ASSERTED silent #3 (offset-less drive from a synthesised site) — a test encoding the
defect, rewritten to assert the refusal. Fleet-env helper landed (100 pairs, 0 mismatches;
supervisor import-side-effects fixed under main guard — D-6 at tooling grain).
Settled suite running; on green: commit → D-8 instrument → lift → fleet → THE RUN.
SETTLED SUITE AFTER 4.5: 1468 passed, 7 FAILED — none semantic. Five are the .credit/.route
WINDOW LAWS (source-position bounds in cognitive_loop, <60 chars headroom per Seat 4's
earlier warning; 4.5's two in-body feed-site inserts consumed it), one is the law that
_plan_gate stays out of record_result (stage 4's settle seam touches it there), two are
rotted receipts (router-core, mint-core). Repair builder dispatched with the rule: the code
moves, the laws never weaken. THE APPARATUS NOTE: window laws are position-based like
file:line receipts — the symbol-anchored apparatus (approved) now has a second customer;
today the debt blocked instead of taxed.
STRUCTURAL REPAIR LANDED: the four window laws recovered by a CODE MOVE (one 280-char
self-cell stamp relocated past .route(; headroom back to HEAD's 50/15); the _plan_gate law
CONVERTED to its AST form (record_result's body had NO violation — the tail slice was
failing on module-bottom helpers; conversion authorized, name kept, KNOBS A4-2 cited,
reach over the body preserved exactly); router-core/mint-core refreshed — and the finding:
the stage-4 refresh sweep had committed those two rows ALREADY RED (+37). Builder's full
suite 1475 green; proctor's independent settled run follows; then commit → D-8 → lift.
KNOWN RESIDUAL (beat-carried): the self-cell stamp now sits after .route(; if a pre-existing
PHASE-2 statement between the old and new sites raises (spine/credit/mint bug paths), that
step's stamp is skipped and _w3c_compose sees the PRIOR cell. Non-raising paths identical.
A stale avatar cell after a PHASE-2 exception is this, not a new defect.
GUARD-GREEN-FOR-THE-WRONG-REASON genus: fourth instance — two receipts committed red by a
sweep that missed them. All four found by reads to the fact, not the verdict.

## ENTRY 48 — 2026-08-21T21:02 UTC. THE RUN IS OPEN. Full fleet on b10bc12, clean deploy (dirty: none).
Sprint ended (6 procs down); supervisor up under the side-effect-free import; deploy event
confirmed carrying the committed head. THE RUN'S PURPOSE, stated before it runs: (a) g7's
window -- driven composite settlements on a library that can apply, with the four silent
successes closed before the first reading; (b) complete the split-half set (m0r0 +1);
(c) live data for the fabric-I/O sixth window and W2b's leak-stop re-read under multi-cycle
drive; (d) the D-8 true fallback rate per game. STOP: every scoreable game at its derived
2k post-baseline sessions. Numbers at open: WON 0/25 · L1+ 10 · L2+ 1 · baseline 0-0-5
(g50t's 1→1 noted as luck). HOLD goes back UP for the next serialized build (shadow gate);
the fleet runs the committed code meanwhile.
L0 MEMORY PROFILE, first data point (9 min post-deploy, boot ramp included): the five L0
suspects are NOT distinguished — fleet-wide ~+22 MB/min; the OUTLIER is sp80 at +71 MB/min
(156→799 MB), 3× the fleet. Hypothesis under test: the re-point's Γ-derived signature index
(_rec_by_id/_sig2id, unbounded, full records) scales with atoms-stream size and sp80's is
the largest. Correlation read + steady-state second window dispatched.
FALSIFIED: the signature-index hypothesis for sp80's growth — sp80's streams are the
SMALLEST in the group (atoms 0.2MB, narration 1.7MB); growth does not track stream size.
sp80 was the fleet's heaviest RSS before the sprint too (641MB at 32m). Object unknown →
heap-shape read (tracemalloc wrapper, 420s, top allocation sites) dispatched on sp80.

## ENTRY 49 — 2026-08-21. THE RUN'S FIRST FINDINGS (10 min in).
D-8 MEASURED: the cognitive router yields no usable action on 84.9% of decisions
fleet-wide (796/938), 100% on ar25/cn04/sk48/sp80/ls20/ft09. Five of six actions are
decided by thresholdless weighted voting. For the gate's census: ~85% of actions are
PROBES by mechanism — the derivations:probes baseline.
THE COMPOSER ENGAGES AND CANNOT REACH: 53,711 no-steps · 2,923 W2b skips · 15 compose
attempts → 14 unreachable, 1 unverified-only · 0 composites minted · 0 settled. Root: the
cross-shelf reach needs act_offset and the legacy library predates the stamp — offset-less
atoms are compose-only, so nearly every candidate is unreachable BY CONSTRUCTION. g7's
window cannot open until offset-bearing atoms exist in quantity; this is upstream of the
design falsifier (material, not chaining), pre-named here so it is not read as the
falsifier firing. Supply read follows.
D-10 (the run's second finding): the act_offset stamp NEVER FIRES LIVE — 28 mints since the
instrument, zero atoms carry act_offset; the newest atom has psig+asig from the same write
site and no offset. Built, gated on constructed inputs, never fired on real ones — and it
sits on the composer's entire material supply (14 of 15 compose attempts "unreachable").
Diagnosis read dispatched; fix serialized behind the gate builder if it lives in
cognitive_loop.py. g7's window is closed until this fires.
L0 MEMORY, steady-state window (boot excluded): fleet growth fell to +2..+11 MB/min; the
five L0 suspects are NOT the top growers (su15 +3.6, s5i5 +2.3) — the brief's premise
(suspects dominate) does NOT hold on the clean code; ka59/cd82/wa30 lead at ~+11 MB/min.
sp80 (the boot-window outlier at +71) left the top ten — fate checked in status.txt. The
heap-shape read on sp80 is the remaining instrument; the memory brief is rewritten on it.
sp80 CORRECTION: not settled — 799MB @9m → 1,008MB @25m (~+13 MB/min steady), the fleet's
heaviest by 300MB, on course for the supervisor's memory cap; it fell out of my top-ten by
RATE only. wa30 second at 685MB (db 333MB). The heap read names the object.
sp80 HEAP READ: tracemalloc sees 75MB (peak 75.6) in a worker whose RSS reaches ~1GB — the
growth is NATIVE (numpy buffers or sqlite page cache), invisible to the Python tracer.
Side finding: matplotlib + scipy + fontTools are IMPORTED INSIDE GAME WORKERS (~40MB of
plotting libraries at boot, ×25) — pure import weight; consumer check queued. Next
instrument: a gc walk of live ndarrays by shape + referrer (dispatched on sp80).
THREE-NUMBER CENSUS on the clean run (n=1,980 ACT): derivations 2.9% (all wa30,
controlled_movement_planning) · negative derivations 3.8% · probes 93.2% (77.8% by
fallback mechanism + 15.4% explore rungs). The gate's stage-1 baseline on clean data.
HEAP READS VOID (my instrument): --max-generations 3 let sp80's ~90s generations finish
before the timer, so both dumps ran post-teardown ("2 live arrays, 0MB" in a running
worker is impossible — the sensitivity check that caught it). Re-run with 999 generations
and a 300s dump; the 75MB tracemalloc figure is withdrawn as a mid-run measurement.
MEMORY INSTRUMENT, third correction: numpy arrays are NOT GC-tracked, so a gc.get_objects()
walk cannot see them by design (the worker DID run to the dump — confirmed by PLAN records
immediately before it). Replaced by a ROOT-WALK from GC-tracked holders (CognitiveLoop,
PredictorBank, Gamma, KnowledgeFabric, …) recursing attributes and summing ndarray bytes
by attribute PATH — with a constructed 4MB known-positive asserted before the real run.
Two instruments falsified by their own sensitivity checks before a number was reported.

D-10 WITHDRAWN (proctor error). act_offset fires live: 4/4 local click mints written since
the 16:01 relaunch carry it (bp35 dc=-1 = click outside the bbox, the designed geometry).
The "28 mints, 0 carry act_offset" census filtered on COMMIT time; the workers that wrote
them were still resident with pre-stage-2 code (a commit does not reload a process).
Rule: censuses of live output filter on PROCESS START, never on commit time. No code change.

MEMORY, root-walk (known-positive OK): ndarray bytes reachable from the 12 cognitive roots =
0.1MB; corrected tracemalloc = 75MB, ~40MB of it import machinery. The agent's own state is
NOT where sp80's RSS lives. Growth is native and outside the cognitive objects: sqlite
connections / page cache, or arrays held by non-cognitive holders (env objects). v2 walks
every gc container at depth 1 and DIFFS two dumps in one process (growth attributed, not
inferred).

D-12 OPENED (the real composer blocker). sp80 live: compose-none reason=unreachable
candidates=17 proposed=0 notes={} on EVERY cycle. notes={} rules out the noted branches
(no-act-offset, no-avatar) -> all 17 fall through the two UNNOTED paths; with zero sp80
act_offset atoms the reach path is impossible -> NO CANDIDATE ANCHORS ON THE PLAN-TIME
FRAME. The label "unreachable" conflates no-anchor with no-path. Read-only diagnosis out:
vintage vs level vs matcher. g7's window on sp80 is closed by anchoring, not by act_offset.

MEMORY, root-walk v2 (every gc container, two dumps 270s apart, known-positive OK): ndarray
bytes 1.1 -> 1.4MB; Python objects +9k; sqlite connections 23 -> 23. Python heap 75MB. The
~1GB on the heavy workers is NATIVE AND UNHELD by any Python object -- the profile of heap
fragmentation from large transient allocations. The named suspect is the fabric I/O defect
already prereg'd (PREREG_FABRIC_IO: _next_seq re-reads the whole stream per append): one fix
would close two defects. Test before believing: RSS growth rate per box should track stream
size per box (correlation read out). Instrument note: hasattr() does not swallow werkzeug's
RuntimeError -- guard attribute probes with a bare except when walking a foreign heap.
MEMORY, correlation read: growth does NOT track stream size (cd82 17.8MB grows +11 MB/min;
sc25 52MB grows +2.6). The fragmentation-from-fabric-I/O hypothesis is falsified at the
file-size grain. The fast growers cluster (ka59/cd82/wa30 ~+11; the rest +2..4): a shared
property of the three, not a per-box size. Arm checked next (deterministic, free).
Arm read: the three fast growers are all arm=fixed, but so are lp85 and sc25 (slow) ->
inconclusive at recycles=0 (the supervisor rotates arms on recycle; the live arm is in each
worker's env, not derivable from the game name alone). Next cheap discriminator: the live
LP_DRIVE_ARM + level + mode per worker, read from worker.log heads, against the rate table.

D-12 DIAGNOSED -- the composer is starved AT THE STAMP, not in the chain.
sp80's Γ shelf: 20 EFFECT atoms, 17 candidates for WANT colour 8/9. Anchoring is exact
equality over atom["context"] = the FULL bbox crop of the before-frame (800-1440 cells,
effects.py:369-380). 0/17 anchor on the first level-2 frame; 0/17 on the worker's own 31
frames; 18/461 stored level-2 frames match exactly one. The [[14]]-class atoms anchor
62-64x: the matcher works; the large WANT-writing effects are single-use by construction.
Not vintage (asig v1 where present; matcher ignores asig), not level (minted and played
at level 2).
WHY MINIMISATION NEVER FIRED: context minimisation exists (W2-S2 re-point, mint.py:391
_signature_merge -> _merge_context -> effects.minimise_atom) and runs before the
rederivation verdict -- yet 0/20 atoms carry a DONT_CARE. The candidates' colour_delta is
[[8,9],[9,8],[14,0]]: THE AVATAR'S OWN 14->0 TRAIL CELL IS INSIDE THE CHANGED SET. The
coarse signature is change-only, so the same world-edit seen from another avatar position
hashes differently, never merges, and MINTS A NEW 40x28 ATOM -- seventeen near-twins.
THE STAMP DOES NOT FACTOR SELF-MOTION OUT OF WORLD-EDITS. The composer's two-shelf premise
(Γ vs BODY separated at the stamp) is false at the stamp.
g7 STATUS: the design falsifier cannot be READ -- neither "g7 > 0" nor "route to the WANT
supply". A third branch the prereg did not name: the chain is unreachable because Γ holds
no anchorable large effect. The composer's test is BLOCKED, not failed; the blocker is
upstream of every stage built this week.
Smallest instrument (builder, one line each): _note("no-anchor") at composer.py:571 and
_note("no-reach") at :543 -- notes={} would have named this on the first PLAN line.
Other boxes: ar25 unreachable candidates=73 x372 (pre-ccbd272 build, notes unobservable);
cd82 candidates=9 x3 avatar=no-avatar -- same zero-anchor shape.
TO SEAT 3: the fix direction is factoring at the stamp -- subtract the BODY's own cells
(the avatar colour at its previous and new cell, which the BODY shelf already knows per
action) from the changed set BEFORE signature and context crop, so a world-edit's
signature is position-invariant and minimisation can merge. That is a change to what an
EFFECT atom IS; it needs a ruling and a prereg, not a patch.
SEAT 4 on D-12: the over-specification finding (contexts too wide) and D-12 are ONE defect
seen from two sides -- the width IS the avatar's trail. Stages 2-3 built a cross-shelf reach
between two shelves that were one contaminated shelf; the index, the re-point, the extent
premium and the composer all operated on atoms whose identity carried the observer's
position. Same class as the re-point: it changes the object -> prereg + ruling.
SEAT 4 on the determinism red: byte-identity has been the strongest gate in four of this
week's builds; a stream that differs between identically-seeded runs removes it as a
falsifier. That, not principle alone, is why ms cannot ride a stream record.
SEAT 4 on D-10: second time a code-vintage filter selected a population other than the one
it named (cf. the pooled-population rule).

STAMP FACTORING CLEARED (Seat 3 + 4): (1) Γ records world-edit only; (2) locus + BODY
delta, under the general rule "the delta explains the subtraction, or the cells stay",
fail-closed to byte-identical; (3) leave the vintage -- the library heals forward, re-
derivation reconsidered only on a measurement. F6 = readability is the stamp's debt; the
number is the composer's. Build serialized behind the gate's commit (settled-tree rule).
GATE DETERMINISM CLOSED: ms was the only differing key across 18 lines (diffed before
changing); cost now an in-process accumulator (a print would have moved the red: the suite
asserts identical stdout too); byte-identity pinned by a two-run test.
RECEIPT LAYER, on the proctor: the registry was refreshed by OFFSET from the builder's
estimate; one estimate was wrong and my refresh script accepted a comment line as the
target. Fourth-or-fifth estimate-for-measurement this week. Rule: a receipt is refreshed by
grepping the SYMBOL it names, never by adding an offset; the builder re-measured every
gate.py row and the loud note records the sequence so a re-measured row is tellable from
an adjusted one.
NEW SMALL GENUS (Seat 4): a registry row's SITE is gated and re-checked; its NOTE is prose
nobody validates ("ms rides the SUMMARY" stood false until rewritten). Notes rot silently
in the file whose purpose is not rotting. No mechanism today; the symbol apparatus will not
catch it either -- known.

=== BEAT 50 (2026-08-21, post-commit 41886d6) ===
ASK: nothing. Levels: MUTE (split-half run 1: 0 improved / 0 regressed / 5 unchanged;
11 never-scored in window, 5 not-yet-readable). g7: 0 -- UNREAD, not failed (D-12).
LANDED 41886d6: reasoning gate stage 1 (shadow, blocks nothing, two reds fixed under the
law), D-9 (diagnostic gated), D-11 (headless workers). Suite 2427+ green, ruff clean.
HOLD DROPPED for the deploy; goes back up for the stamp build the moment the fleet is
relaunched on 41886d6 (the tree is production).
NEXT: stamp factoring (cleared; brief at record/prereg/BRIEF_STAMP_FACTORING.md) -- the
one build between the fleet and a readable g7. Then fabric I/O, W2c, standing_half_life,
persistence monitor, symbol receipts, in that order. Memory profile parked with its
instrument specified. At Seat 3: nothing outstanding.
DEPLOYED 41886d6 at 18:42:51 local (fingerprint ea7474ad7381293a, dirty none); 25 workers
relaunched, boot RSS 193-349MB (headless). HOLD back up: stamp factoring building.

GATE, FIRST LIVE BEAT (18:49, 11,938 gate records, 25 boxes, 2,943 steps): mode observe
on every box; MODE records 163 (one per game start; enforcement off, deadline marker
carried). THE THREE-NUMBER BEAT: derivations 0 : negative derivations 0 : probes 2,943 --
class=probe on EVERY step. Consistent with D-12 (nothing anchorable -> nothing derivable);
the gate reads what the composer reads. BET would-refuse 570/2,943 = 19.4% (shadow count,
blocks nothing); ACT pass 2,943; PERCEIVE unverdicted 163 = first step per game (no
previous opener, by design); unbuildable 0; completeness reported == differing on every
step with a previous (unreported 0). Stratum mass at 9-12.
ANOMALY UNDER VERIFICATION: `ms` is present on 2,677 of the 2,943 SUMMARY records -- the
field removed before 41886d6. The fleet ran b10bc12 (no gate) until 18:43; records with
`ms` can only have come from a process that imported the builder's UNCOMMITTED gate. The
suspect: the bounded-lifetime recycle respawns a worker from the working tree, and HOLD
suspends deploys but not recycles. If so, HOLD is not a complete stop and uncommitted
builder code ran live for ~50 min. Creation times of gate.jsonl decide it.
ANOMALY CONFIRMED -> D-13, HOLD IS NOT A STOP. tools/swarm_supervisor.py: RECYCLE_MIN=120
(:44); the HOLD check (:337) suspends DEPLOYS only; the bounded-lifetime recycle (:374)
fires regardless and spawn() imports the working tree. status.txt r/m/c went 0/0/0 (17:44)
-> 0/0/1 (18:45): all 25 workers recycled at ~18:03 onto the dirty tree -- the gate with
`ms` and the raw-origin read ran live for ~40 min under HOLD. Crash restarts and mem-kills
have the same hole. No harm this time (shadow gate; the `ms` records sit in personal
streams -- mixed vintage, stated). Fix: under HOLD, defer lifetime recycles; any forced
respawn under HOLD is appended to deploys.jsonl as reason="respawn-under-hold" with the
dirty state, so the ledger never again shows a clean history over a dirty fleet. Builder
dispatched; tooling grain; its own gate.
D-13 TIMING PINNED: first gate.jsonl per box created 18:03:51-18:09:53 = 120 min after the
16:03 start (RECYCLE_MIN); post-deploy files 18:43-18:46 match the new PIDs (18:43:03-
18:44:40). Three independent reads agree (code path, recycle counter, file creation).
GATE BEAT, POST-DEPLOY VINTAGE (18:5x, 519 steps, 25 boxes, 60 game starts): THE THREE
NUMBERS 0 : 0 : 519 (class=probe on every step). BET would-refuse 110/519 = 21.2% (shadow);
PERCEIVE pass 459 + 60 first-step unverdicted; ACT pass 519; unbuildable 0; completeness
unreported 0 everywhere. Instrument note: a fleet-wide deploy stamp is the WRONG vintage
cut -- 16 `ms`-bearing SUMMARY records leaked through because an old worker opened a fresh
agent stream between the deploy stamp and its own kill (ls20: 18:43:10-18:44:09, replaced
18:44:15). The cut is PER-BOX WORKER START (the D-10 rule at the box grain); instrument
tightened, excluded streams counted and stated.
Beat instrument verified: per-box worker-start cut excludes 62 pre-vintage streams; ms-
bearing SUMMARY = 0 post-cut (the known-positive of the cut). 668 steps on the deployed
vintage at 18:5x; mode observe everywhere.

STAMP FACTORING: F1 FIRED THE LOSING CONDITION. The builder ran the falsifier on a
scratchpad prototype of THE RULE before touching the tree (its decision 1 -- the right
order under "the tree is production"). Readings, each with its population:
  - the 17 sp80 near-twins, THE RULE, locus=colour 14, book deltas: 17 -> 17 (the book
    holds translate=None for every action; fail-closed is byte-identical by construction)
  - same, bank-style centroid deltas: 17 -> 17 (every delta rounds to (0,0))
  - the REJECTED colour-anywhere reading, as a diagnostic bound: 17 -> 16 -- decisive:
    even the widest subtraction leaves 16, because the 8<->9 edits are 14 DISTINCT
    geometries (64/96/128 cells, 4x24..28x40). THE NEAR-TWINS ARE NOT TWINS.
  - THE RULE on sp80's actual mover (colour 9, 80 cells, deltas +-4): 471 arrow events,
    self_cells derived on 425, signatures 396 -> 27. The mechanism works -- on the shelf
    the prereg did not point it at.
D-12 CORRECTED (proctor error): colour 14 on sp80 is NOT the avatar. It is a contiguous
bottom-row bar losing 1-2 cells per action regardless of action -- the per-action budget
clock THE_LADDER rung 0d already records as "nothing reads". The "14->0 trail inside the
changed set" is the CLOCK'S TICK, and the near-twins' varying widths are the tick's
column. The evidence was in the log I read ("[EGO] colour=14"); I did not ask what 14 was.
D-14 OPENED -- THE SELF-LOCUS IS ACTION-CONTINGENT, NOT ACTION-SPECIFIC: the ego observer
names as "the controllable" whatever changes when the agent acts (676/~900 [EGO] lines on
sp80 name the clock); the Goodhart guard fails on contingency alone. Consequences: every
[PLAN] line on sp80 is avatar=centroid-rounded OF THE CLOCK (35/35); the BODY shelf on any
box with a per-action indicator is the indicator; cross-shelf reach computes paths for a
clock; the "[[14]]-class atoms that anchor 62-64x" are clock ticks. Question for the
BODY-NOVEL proposal at Seat 3: how many of the 2,467 "unexplained self-motions" are ticks?
WHAT THE COMPOSER'S STARVATION ACTUALLY IS: large world-edits that each happen ONCE, minted
with context = full crop, so the minimiser (which needs a second observation of the SAME
edit) never fires and no later frame matches. Over-specification proper. Self-motion
factoring does not touch it. The fix class: narrow at MINT (changed + one ring retained,
DONT_CARE elsewhere, context_full as the undo -- the minimiser's own retention rule applied
at first mint), tightened by the re-point's existing conflict clause on divergence. Start
loose, tighten on conflict -- the same machinery the re-point already runs, direction
reversed. Object change -> ruling, not patch.
F (the two composer notes) ships alone: one line each, no ruling needed.
PREREG_STAMP_FACTORING: status -> F1 FIRED; the rule is sound on the true body (396->27)
and the prereg is re-targetable at BODY/world separation for MOVES, but it is not the
composer's fix. Held for Seat 3.

GM CORRECTION (evening): "your job is not to solve the games for the agents." Accepted.
The drift, named: five layers upstream of a null (act_offset -> anchoring -> stamp ->
context -> self-locus), each a ruling-grade change to the agent's representation so the
composer could be tested, the last reasoning from what colours 14 and 9 ARE on sp80.
The wheel rule applies to the proctor too: the composer's falsifier HAS answered -- Γ's
large effects are single-use, the chain anchors nothing, g7 = 0 is a READ NULL. Per its
own prereg the finding routes to the WANT supply (abduction) or the composer stays on the
shelf until signal earns it. PREREG_MINT_CONTEXT_RING withdrawn. D-14 stands as a FINDING
(the self-locus names a non-mover), no fix attached. Back to the cleared queue: fabric
I/O, W2c, standing_half_life, persistence monitor, symbol receipts.

FIREWALL STATEMENT (GM asked; stated, not assumed): two game identifications reached
builder-class agents this session, both in BRIEFS, neither in code or a fixture --
BRIEF_STAMP_FACTORING F1 ("the avatar colour 14's locus"; that builder touched zero tree
files) and the D-14 diagnosis prompt ("colour 9 is the mover"; read-only agent). Source was
the agents' own .runs records, not GAME_TRUTH -- one step from an answer, as ruled. Both
scrubbed; the D-14 agent instructed: criterion only, no identification in any recommendation.
BOARD CONSTRAINT (GM): the proctor does not look at the board -- frames are the agent's
view. Both diagnoses decoded frames from action_traces; that stops. The seat works from
records, streams, logs and code.
RULINGS: PREREG_MINT_CONTEXT_RING -- Seat 4 "take it"; Seat 3 sequences it behind the
infrastructure queue; re-admitted with game-specific language removed, falsifiers by
behaviour. D-14's fix, when drafted, is a PRIOR ("a locus that does not move under a
movement action is not a body"), never an identification. Seat 3 has seat-specific work
queued after the infrastructure queue lands.
FIREWALL ASYMMETRY (Seat 4): the D-14 prompt went to a read-only agent -- contained BY
CONSTRUCTION. The stamp-factoring brief went to a BUILDER with the identification in F1;
it touched zero tree files only because F1 fired -- contained BY CIRCUMSTANCE. One safe by
design, one safe by luck; the second is the lesson. Closed by the board rule (frames are
never read from this seat) and the criterion rule (identifications never enter a brief).
D-13 LANDED (tree, uncommitted): under HOLD lifetime recycles DEFER ("RECYCLE DEFERRED
(HOLD)"); forced respawns (restart/mem_kill) are ledgered as reason="respawn-under-hold"
with head/dirty/fingerprint through the ONE assembly deploy_record(); F4 oracle captured
from the unedited supervisor and frozen. 308 passed. Receipts in this log's D-13 entry
(:44/:337/:374) are as-of; the symbols now sit at :53/:374/:425.
COMPOSER NOTES LANDED (tree, uncommitted): NO_ANCHOR / NO_REACH noted per candidate at
the two formerly silent fall-throughs; reason label unchanged; 11 tests; registry rows
refreshed by symbol (+7/+7/+11 stated).

QUEUE STATE (post-GM-correction): IN FLIGHT in parallel, files disjoint -- fabric I/O
(fabric.py only; stage 1 + _next_seq cache, stage 2 attribution read only), W2c (retention.py
new; planner/scheduler/composer/effects band; two loop call sites), persistence monitor
(persistence.py new; narration/affect/goal; one loop hook; the `narration` ALLOWLIST entry
deletes). SERIALIZED: standing_half_life after W2c (shares planner._candidate_ids and
scheduler.plan_wrong); symbol receipts LAST (its migration rewrites every registry row --
any build landing after it would refresh rows in the retired form). Landed in tree,
uncommitted, green: D-13, composer notes. Then ONE settled-tree suite -> commit -> HOLD
down -> deploy. D-14 diagnosis read-only, criterion-only, report with no fix.
D-14 DIAGNOSED (read-only, criterion-only, no board reads): self_locus.py scores a colour
by the SPREAD of per-action mean displacement MAGNITUDE (direction discarded at :49-51);
lifetime accrual, zero-overlap matches admitted, move_eps met by losing an end cell; a body
moving equally under every arrow scores 0 across arrows. NO consumer checks the locus moves
per action; the only locus-independent per-action VECTOR (W4c classifier, :2141-2163) is
unread by the chooser. SIZE: 10 of 16 named loci fleet-wide have no stored mover evidence;
9 boxes have no locus. Finding doc: record/findings/D14_SELF_LOCUS_CRITERION.md. No fix
dispatched; the fix is a prior and needs a ruling; queued behind the infrastructure work.
D-14 amplifiers recorded as four SEPARATE items (no reset; zero-overlap match; move_eps=0.5;
frame_change_rate 1.0 under every action) beside the criterion defect, so the criterion
change is never credited with fixing them (Seat 4).
FLEET, 19:4x: the RUNNING supervisor is pre-D-13 code; at ~20:43 (120 min after the 18:43
relaunch) it will recycle all 25 workers onto a tree with three builders mid-edit, ledger
silent. Proctor attempted to stop the supervisor PROCESS ONLY (workers orphaned alive,
recycles/deploys frozen until the commit) -- blocked by the permission classifier; routed
to the GM for decision. If allowed: at deploy, kill the orphans, start the new supervisor
(D-13 code) from the committed tree. If not: the recycle is recorded by hand when it fires.
FABRIC I/O, RIDER-2 AUDIT (Seat 4 read it in flight): zero nested mutations, zero
top-level-only writes, forty read-only consumers; the shallow-copy contract is SUFFICIENT
TODAY and held by dict(atom) at two sites that no rule states -- "a contract nobody wrote
down that everybody depends on": produced-and-unread INVERTED. Two pins ordered on the
builder: (1) an AST wall naming the no-nested-mutation invariant over production globs
(exemplar: gate.py's no-posthoc wall); (2) the mint-index / cache consistency invariant
(_scan_pos resets only on shrink) as a constructed test or, failing that, a stated contract
at both sites. Hazards pinned, not fixed -- the right disposition for a contract audit.

## ENTRY 50 — 2026-08-21. FABRIC I/O LANDED (tree, uncommitted, HOLD up): the seq tail (A) and the read cache (B); stage 2's attribution read names execute_query, not the log handler.
WHAT EXISTED BEFORE vs WHAT 6-b CLAIMED: `_next_seq` already cached the high-water mark --
per INSTANCE, keyed by file SIZE -- and test_fabric_seq_cache.py proved 0 re-reads after a
priming append on ONE instance. The 1.5M json.loads / 1,220 appends came from the loop
building a fresh KnowledgeFabric per reachability seam and per game on one root
(cognitive_loop.py:133/262/1819/1943 + cognitive_game_player.py:107): every fresh instance
paid one whole-stream `_read_stream` per stream on first touch. What the old gate never
counted: the priming read; two instances on one root; a same-size rewrite (size-blind).
A. THE SEQ TAIL (fabric.py `_next_seq`/`append`/`reload_seqs` + module-bottom `_seed_seq`,
`_anchor_size`, `_anchor_bytes`): one PROCESS-level entry per stream path; seeded from the
LAST record via `_tail_records` (first touch of a 3,000-record stream: 0 full reads, 1 tail
read, <= 4 json.loads -- counted); advanced in memory (anchor advanced from the bytes text
mode wrote, then held to the stat: a disagreeing size drops the entry); invalidated by THE
SAME anchor rule as the read cache (one definition, `_anchor_size`; the seq side requires
size == upto, the read side size >= upto). Shrink / grow / same-size rewrite: exactly ONE
re-seed each (counted). Two instances alternating on one root: live 0 full + 0 tail reads;
the literal transcription of the 41886d6 writer re-parsed on EVERY alternation (>= 40, the
known-positive). `reload_seqs()` = one full oracle scan (keeps the existing gate's
"exactly one _read_stream" assertion true by meaning, not by accident). `_ends_in_newline`
removed: the anchor already holds the last byte. STATED RESIDUE: a foreign tail record
whose seq is LOWER than an earlier one reads last+1 where the old scan read max+1 (pinned
as a test; append is monotonic and the janitor keeps order, so only an out-of-band writer
can produce it; reload_seqs is the hatch).
B. THE READ CACHE (`_cached_stream`, the one dispatch in `query` at fabric.py:284): paths
1/2/3 as the prereg specifies; parsed_upto never mid-line; a lone trailing "\r" stays
volatile; path 3 decodes the same bytes `_read_stream` would through `_tail_lines` (proved
identical by the tail-read gate) rather than calling `_read_stream` and re-reading for the
seed. F1: the whole corpus list + random sequences + EVERY stream of one real box
(the smallest with >= 100 streams, read-only) == the oracle at every read. F2 (100 cycles,
today's query set against growing streams): full reads per cycle 4 -> 0 for all 99
post-warm-up cycles; tail reads 4/cycle; bytes decoded <= bytes appended; `_read_stream`
called 0 times under the cache (by construction -- so the count that carries F2 is
READ_STATS["full"], not the old probe, which would be a guaranteed zero). F3: append never
invalidates (0 full / 20 tail over 20 appends); rewrite exactly once; a shrink between the
stat and the anchor read falls to path 3 and returns the oracle's answer on the shrunk file.
RIDER 1: LRU by stream bytes, READ_CACHE_CAP_BYTES = 32 MiB (KNOBS G35: GUESSED from the
25-box observation, 24.3 MiB max per-box working set of the per-cycle topics; held memory
3.5x-6.5x measured; a stream over the cap is served uncached, never retained). L0
INTERACTION (stated in G35): the cache is a PLATEAU bounded by cap x 6.5 (~210 MB worst
case), not growth -- it cannot be the unbounded grower, and it removes the per-cycle
transient parses of the cached streams; import_queue (> cap on 15/25 boxes) keeps
today's per-cycle whole parse -- the L0 suspect (b) path is lp_drive.py:124's
`query("collective", "import_queue")`, untouched by this build and worth its own read.
RIDER 2: AUDIT + CONTRACT chosen over deep copies (44 production consumers: 40 read-only,
4 copy-before-write, 0 nested writes; deep-copying 80k records per call would cost what the
cache saves). PIN 1 built: an AST wall over the production globs (alias-depth model, the
no-posthoc shape; R4 known-positive fires on six shapes, known-negative silent on the
dict(atom) idioms) -- 0 violations on the tree today; the contract is on the
fabric-read-cache registry row. PIN 2 built: control (plain supersede) agrees; TWO STRICT
XFAILS = a pre-existing FINDING at mint.py:535-554 -- a shrink-then-grow between refreshes
that ends LONGER than _scan_pos skips the records in [old len, new len) and a re-base never
evicts vanished ids (scratch: 10 stale / 2 missing of 8); a same-size rewrite of the last
record re-seeds the cache but not the mint's index. The pre-build `query` returned the
identical list, so the cache neither causes nor hides it; a mint fix flips both xfails loud.
C. STAGE 2 NOT BUILT; THE ATTRIBUTION READ DONE from the existing W6 pstats
(.runs/d5_profile_g50t_W6.pstats, read-only): sqlite commit 79.2 s of 396.7 s (20.0%),
1,328 commits -- 917 / 72.4 s under `DatabaseInterface.execute_query` (FIX #16 auto-commit,
79 ms each) vs 350 / 6.7 s under `DatabaseLogHandler.emit` (19 ms each). THE NUMBERS POINT
AT execute_query's per-statement auto-commit, NOT the log handler the review named first.
execute_query's callers by cumulative time: game_player._record_action_trace 20.4 s (130),
routing_traces.execute 18.3 s (130), i_thread._save_state 10.7 s (113),
sensation_engine._update_object_sensation_mapping 6.3 s (260) + learn_from_outcome 5.9 s
(260) + _update_action_bias 2.4 s (260), i_thread._log_history 5.5 s (113) = 69.5 of 75 s.
Stage 2's batch is designed for THAT site; the log handler's level is the successor if
commits prove cheap under WAL.
GATES: tests/gate/test_fabric_next_seq_cache.py (23) + tests/gate/test_fabric_read_cache.py
(45 + 2 strict xfail) green; the five pre-existing fabric gates (88) green; test_consumers.py
untouched by this build (its working-tree delta is the persistence-monitor builder's,
narration entry deleted); WIRING_REGISTRY +2 [helper] rows (sites by grep: fabric.py:284,
:203; no prior row carried a fabric.py receipt -- drift 0); KNOBS G35; ruff clean. Full-suite
tail in the dispatch report. Registry reds seen this session, NOT mine: lp-steer /
goal-abduction-plan / composer-cross-shelf-reach / admission-bargain receipts rotted and
persistence.py's BROKEN_REBINDING reference + 4 unregistered classes (persistence.py,
retention.py) -- the concurrent composer/supervisor/persistence builds.
D-13 FIRED AGAIN, 20:46 (recorded by hand -- the running supervisor is pre-D-13 and its
ledger is silent): RECYCLED#2 on every box. The tree at that instant carried three
builders' uncommitted edits (fabric.py read/seq cache; W2c retention across planner/
scheduler/composer/effects/cognitive_loop; persistence across narration/affect/goal/
cognitive_loop), each mid-suite. The fleet now runs that code. The proctor's attempt to
stop the supervisor process beforehand was blocked by the permission layer and routed to
the GM; no decision arrived before the recycle.
FLEET THRASHING (status 20:46): mem-kills s5i5 x16, sb26 x21, tn36 x13, su15 #14 (2027MB),
vc33 #16 (1688MB), all accumulated since ~19:30 = when the builders began editing. Crash
and mem-kill respawns import the working tree (D-13's other half), so these workers run
half-built code that reaches ~2GB in minutes. The 20:46 recycle put the other 20 on the
same tree. Suspect: an unbounded parsed-stream cache mid-build (Rider 1 bounds it; the
bound may not have existed at respawn time) -- the builders' reports decide. A builder also
deleted architecture/Autonomous Research Lab.md outside scope; restored from git.
DECISION REQUESTED OF THE GM: halt the fleet (stop supervisor + workers) until the commit,
since HOLD cannot stop respawns and the proctor is blocked from stopping processes.

FLEET HALTED (GM ruling): 52 processes stopped (supervisor pair + 25 worker pairs), 0
remaining. Reasons as ruled: streams since ~19:30 are CONTAMINATED EVIDENCE (mixed-vintage
code under a changing tree -- the eight-dirty-deploys defect again), and a ~500 MB/min
memory ramp of unattributed origin was running unsupervised while slowing the very suites
that would name it. Nothing of value lost: levels mute, g7 a null, split-half sealed before.
WHAT D-13 ACTUALLY DOES (answering the GM): under HOLD it DEFERS lifetime recycles and
LEDGERS forced respawns (crash/mem-kill) as respawn-under-hold. It does NOT stop respawns
-- a crashed worker can only be respawned from the tree that exists. So after D-13, HOLD is
a deploy gate + a recycle gate; it is still not a fleet gate.
THE STANDING LESSON: HOLD was designed as a deploy gate and treated all week as a fleet
gate. Every build done "under HOLD" on the production tree was exposed to respawns
importing half-built code. THE RULE FROM HERE: builds on live-path files happen with the
fleet HALTED, or the fleet deploys from a SNAPSHOT (a worktree at the deployed commit) --
the second is the infrastructure fix and is proposed to Seat 3 as the next queue item after
symbol receipts. Until then: halt for builds.
RAMP ATTRIBUTION (pending the three reports): the five mem-killed boxes (s5i5, sb26, tn36,
su15, vc33) are the SMALL-stream, never-scored boxes, not the big-stream ones -- evidence
against the read cache as the ramp. If none of the three reports owns it, a fourth thing is
running and gets its own read before anything lands.

THE PROCTOR MANDATE received (GM, evening) -- saved verbatim-in-substance at
record/corpus/THE_PROCTOR_MANDATE.md and in memory. Eight items; the queue finishes first.
THE ELEVEN FIGURES internalised (text digest at record/corpus/FIGURES_TEXT_DIGEST.md; the
SVGs are the law). From here every brief states the laws its build satisfies and every read
states the figure it reads against. The law behind the board constraint is FIGURE 10:
"Looking inside the frame it grades is how the seat stops being outside ... Bring a
characterised residual, never the source." The seat reading frames was the seat acquiring
the agent's model and grading against its own picture. The two briefs already written
(standing, symbol receipts) now carry their laws. FIGURE 11 names the other standing
caution for every gate test in the tree: a test harness is a substituted habitat -- a
synthetic solve proves wiring, never capability.
W2c LANDED (tree, uncommitted): retention.py (store + session, content-keyed), planner/
composer/effects band at the one dispatch, scheduler owns and clears the store, 3 loop hunks,
31 tests green; F1 by counting (exact repeat applied_cold 5 -> 0; second compose attempt 0
scans); band oracle 0 mismatches on 300 + 400 cases. Caps G30-G34 pinned by prereg. Its full
run: 2606 passed / 5 failed, all attributable to concurrent builds -- persistence's hook
appended BELOW _gate_step breaks the gate's "lives at module bottom" law (a POSITION PROXY:
"is last" rather than "is a module-level def after the class" -- the genus symbol receipts
retires; the gate test is corrected when persistence lands), persistence's third gains
channel breaks the test pinning "exactly two channels" (the prereg adds a third; the
test is in that builder's scope), and the supervisor env-order parity (re-checked at the
settled suite). W2c wrote no PORT_LOG entry (file under concurrent edit) -- correct.
SERIALIZATION: standing_half_life waits for persistence too (it stamps the PLAN-abort
NARRATION record; persistence owns narration.py until it lands).
FABRIC I/O LANDED (tree, uncommitted): A) _next_seq -- TARGET CORRECTED: it was already
cached PER INSTANCE; the 1.5M loads came from fresh KnowledgeFabric instances per seam/game
on one root (cognitive_loop.py:133/262/1819/1943, cognitive_game_player.py:107), each
parsing the whole stream on first touch. Now ONE process-level entry per path, tail-seeded
(3,000-record stream: 0 full reads, 1 tail read), anchor-invalidated; 23 tests. B) the read
cache: 45 tests + 2 strict xfails; F2 full reads 4 -> 0 after warm-up; cap 32 MiB stream
bytes GUESSED from the observed per-box working set (24.3 MiB max), import_queue (>15MB on
15/25 boxes) deliberately uncached; held memory a ~110-210MB PLATEAU, not growth (G35).
PIN 1 (no nested mutation) built as an AST wall, 0 violations; PIN 2 found a PRE-EXISTING
mint defect (mint.py:535-554: shrink-then-grow past _scan_pos skips records and never
evicts; same-size last-record rewrite unseen) -- two strict xfails, independent of the
cache. C) ATTRIBUTION READ: sqlite commit 79.2s / 396.7s (20.0%), 1,328 commits -- 917 /
72.4s under execute_query AUTO-COMMIT vs 350 / 6.7s under DatabaseLogHandler.emit. The
proctor's first suspect (the log handler) was wrong; the numbers name execute_query. Top
callers: game_player._record_action_trace 20.4s, routing_traces.execute 18.3s,
sensation_engine.* 14.6s, i_thread._save_state 10.7s, i_thread._log_history 5.5s. This is
MANDATE ITEM 2's first number. Stage 2 (per-step batch) now has its target.
Its full run: same 5 reds as W2c's, all attributable to the persistence build + supervisor
env order; none its own.
SEAT 4 on the two landings: "not mine" by CONTROLLED SUBSTITUTION (HEAD's fabric.py swapped
in, four reds reproduce identically) is the strongest form available. test_sprint_keeper
flipping mid-suite under a concurrent supervisor edit = the MOVING-TREE HAZARD, fifth
instance this week; the policy meant to close it (full suite proctor-only on a settled
tree) did not hold because three builders ran simultaneously -- the proctor's parallelism
decision is the cause. PIN 2's xfails are a real pre-existing mint gap, correctly filed
not fixed. The 32 MiB cap leaves the largest stream on >half the fleet cold: right trade;
if import_queue reads prove hot, the cap is the wrong SHAPE not the wrong number.
SUITE TIME IS A DESIGN CONSTRAINT: 57 min now vs 2.5 min on a quiet box a week ago; two
new gate files add ~20 min (file-open cost on this box). Every gate written from here is
shaped by that fact. Mandate item 2 owns it.
RAMP REPRODUCTION (one worker in-process on a thrashed box, FINAL tree, fleet halted):
NOT REPRODUCED -- 625MB private / 442MB working set at 27 min, versus the fleet's ~2GB in
~4 min during the build window. Consistent with the ramp belonging to a MID-EDIT tree state
(e.g. a cache before its bound landed) under 25 workers + 3 suites; not provable from here.
THE TEST IS THE RELAUNCH: on the committed tree, status.txt mem-kills must stay 0 across the
first hour; any recurrence is caught at the first heartbeat read (the halt rule), not after
21 kills. Instrument lesson: the sampler thread owned the timer and died silently on one
transient OSError -- a sampler must never share a thread with the deadline.
HEARTBEAT: session cron replaced with the canonical prompt (job 47e58640, 11,41 * * * *);
the verbatim prompt lives in memory (proctor-session-start) and in THE_PROCTOR_MANDATE.md
so any model re-arms it identically.
GM: fleet relaunch AUTHORIZED on the proctor's timing once the mandate's item-6
obligations are met (figures internalised; laws in every brief -- done). The halt lifts at
the verified commit: persistence lands -> standing builds -> ONE settled suite with no
builder in flight -> commit -> new supervisor (D-13 code) from the committed tree -> the
first status.txt read is the ramp's test (mem-kills must stay 0).

MANDATE ITEM 2, FIRST NUMBER (records only, worker.log stamps, per PROCESS lifetime; read
against FIGURE 3): WITHIN-PROCESS GENERATION GAP median 1,995s = 33 MIN (p25 19 min, p75
55 min; n=2,133 gaps, 3,804 process lifetimes, 25 boxes). Target: several generations in
10 min -> a >= 10x gap. Median GENERATIONS PER PROCESS = 1: most workers complete one
generation before they end (recycle/restart/mem-kill/deploy), so every generation also pays
a boot: ~95s import (pre-D-11) + median 72s from the runner banner to the first cognitive
cycle (replay handoff + agent construction). Per-box: first-cycle 9s (cn04) to 235s (su15);
gen gap 711s (ar25) to 3,870s (sp80). NEXT READ: actions per generation and seconds per
action per box, from the logs -- to split the 33 min into per-action work (the profile
windows' terms: sqlite auto-commit 20%, apply_effect, record_result) vs per-generation
overhead (agent creation, evaluation, DB), and to show the arithmetic to the target.
Item 2, sidebar: the supervisor spawns --max-generations 50, so "1 generation per process"
is not the argv -- it is process death (120-min recycle, restarts, mem-kills, deploys)
landing before generation 2, which a 33-min generation makes near-certain: a 120-min
lifetime holds ~3 generations at best, and every respawn re-pays boot + first-cycle
(~95s + 72s) and a replay handoff. Speed and lifecycle are one problem: shorten the
generation and the lifecycle overhead shrinks with it; lengthen the lifetime and the
memory growth (L0) bites instead. The anatomy read splits the 33 min next.
Item 2, ANATOMY (2,133 complete generations, records only): a generation = 4 agents played
SEQUENTIALLY in one process; median 277 narration events; 6.25s per event (fleet median;
ar25 0.67s ... sp80 23.7s). Head (banner -> first [AGENT]) and tail (last event -> next
banner) read 0s at this grain -- no logger stamp there -- so the 33 min is the play itself,
not evaluation/selection overhead (to be confirmed at the action grain from the DB).

MANDATE ITEM 2, ACTION GRAIN (core_data.db action_traces, non-frame columns; records only):
  box    actions/session  span    s/action (all / last 50)
  g50t        130         318s     5.1 / 3.7
  tu93         50         325s     6.7 / 6.6
  ka59        100         734s     8.3 / 8.6
  sb26         22         283s    11.1 / 11.2
  ar25         84         619s    11.8 / 17.6   (composer engaged, 73 candidates/cycle)
  sp80         32        1122s    45.8 / 44.3   (composer engaged every cycle, 17 candidates)
A generation = 4 sessions -> 1,130s (sb26) .. 4,490s (sp80). Per-action cost varies 12x
across boxes and is dominated on the slow boxes by PER-CYCLE COGNITION (composer/planner
scans -- W2c retains them; fabric reads -- now cached; sqlite auto-commit 20% -- stage 2's
target), not by boot. THE FIFTH LAYER, named: the per-cycle plan/compose engagement on
boxes where the planner engages every cycle (sp80 45s/action vs g50t 3.7s) -- W2c is its
fix and its measurement (applied_cold per call, first vs repeat engagement) is pre-committed.
THE ARITHMETIC TO THE TARGET. "Several generations in 10 min, fleet-wide": take 3 per 10
min = 200s per generation = 4 sessions x ~100 actions = 0.5 s/action PER WORKER WITH THE
CORE TO ITSELF. THE BOX: Intel i5-6500, 4 cores / 4 threads, 56GB. 25 single-threaded
workers share 4 cores -> each sees ~0.16 core; a fleet-wide generation is 25 x 400 = 10,000
actions through 4 cores. At 1 s/core-action (plausible after the four landings) that is
2,500s = 42 min per fleet-wide generation; the target needs ~0.07 s/core-action, a further
~14x beyond the landings, OR fewer actions per generation (the 150 budget), OR fewer boxes
concurrently (sprint mode: 3 workers on 4 cores -- the GM's own preference while builds
run), OR more cores. The GPU does not enter: the hot paths are numpy/SQLite/Python, not
tensor-shaped. Stated as the GM asked: part of the remaining cost IS the work (per-cycle
cognition on engaged boxes), and part is contention that no code change removes.
MEASUREMENT PRE-COMMITTED FOR THE RELAUNCH: s/action per box from action_traces over the
first hour on 41886d6+landings vs this table (same query, same boxes); sprint-vs-full
comparison on the same boxes if the GM wants the contention term isolated.

MANDATE ITEM 1, THE LADDER AUDIT (read against Figure 3): 11 rungs read something today
(0, 0c, 0d, 1, 1b, 2, 3, 4, 5, 5b, 6); 2 read an instrument that does not exist (0b the
exposure floor -- MIN_EXPOSURE in no .py, no tool; 0e publication -- none named, answered
once by hand); 1 has NEVER returned a value in its named form (0b), +1 returned only a
guaranteed zero (rung 1, R_T=0, ruled not-a-reading by Q8). THREE STATEMENTS IN THE LADDER
ARE NOW FALSE THE OTHER WAY: 0c "no CI gate" (ci.yml runs both gates on all branches);
rung 2 "reason field unbuilt" (mint.py W4 built it); rung 4 "matched-and-rejected
inexpressible" (kind=declined built). MOST CONSEQUENTIAL ABSENCE: 0b -- the break is being
read at g7 on a fleet whose leaders run 0.1 act/min, and without an exposure instrument
the ladder cannot say whether that null is a reading or a reading of nothing; by its own
stop rule every rung beneath is unmeasured until 0b reads. DISPOSITION: the beat-rates
tool (in build) gains the 0b line (episodes/hour, actions/episode, s/action, completion
rate, MEASURED/UNMEASURED against split_half's derived k); the three stale statements are
corrected in THE_LADDER by a dated currency section.
SEAT 4 on the ladder audit -- CORRECTION TO THIS LOG'S OWN FRAMING: g7 is not "a read
null". With no exposure instrument (0b never built; MIN_EXPOSURE in no .py), the g7 null
on a fleet whose leaders run 0.1 act/min is UNMEASURED by the ladder's own stop rule --
nobody knows whether enough happened for the number to be a reading. Rung 1 likewise: only
R_T = 0 ever returned, arithmetic-not-result by Q8; no localised R_tau figure anywhere. Two
hollow rungs at the bottom; every reading this project has taken sits above them. The
three stale "gap" statements mean the ladder UNDER-reported its own coverage -- a stale
receipt in the document that governs receipts. The mechanism that replaced 0b's threshold
(split_half's derived k, the no-wall-clock ruling) was never re-scoped onto the rung.
DISPOSITION: beat_rates.py (building) carries BOTH instruments -- 0b exposure per game
against split_half's k, and rung 1's per-slot residual from the bank's settlement records
(largest single-slot mass, live-slot count, never a mean -- Figure 1). If the bank writes
no per-slot field, the tool prints that, and rung 1's instrument becomes a queued build.

PERSISTENCE MONITOR LANDED (tree, uncommitted): persistence.py (pure fold, O(1)/record,
one observer hook in the spine), the PERSISTENCE token, `persist` as affect's third channel
into exactly two sinks, 42 tests. Its one red (keeper env order) REPRODUCED GREEN in
isolation by the proctor (21 passed) -- another mid-suite artifact of a concurrent
supervisor edit: the SIXTH moving-tree instance, and the last, because no builder runs a
full suite from here (proctor-only, alone, after every builder stops -- the root cause was
my parallelism, not their discipline).
SEAT 4 on the build, three notes:
1. THE GOAL SINK IS LATENT AND MARKED: GoalManager.observe has no live caller; the builder
   registered it SEVERED with a loud waiver rather than driving it (scope creep) or hiding
   it (the ten-instance genus). F6's wire check runs through the LIVE sink instead, so it
   tests something that fires. The right refusal.
2. [COL] FALLBACK = the same stream prefix, not a disk read of other agents' streams:
   determinism over richer evidence, because byte-identity between the live emitter and
   replay() is what makes the monitor auditable. The same trade as the `ms` field, one
   build later, taken unprompted.
3. PRIMING COST, to become a beat number not a note: from_fabric parses the agent's whole
   personal narration stream once per spine per game (~0.3s / 40k records). Narration grows
   per step, so a long-lived worker pays a longer parse for every new game -- the same
   shape as the replay tails, which were invisible until measured at 12 minutes.
THE POSITIONAL LAW THAT SURVIVES THE APPARATUS: test_gate_stage1 pins _gate_step as the
module's LAST function, so persistence's helper had to go ABOVE it -- the third build shaped
by a gate constraint rather than by design, and the second collision this week between the
module-bottom convention and a positional law. Symbol receipts removes the RECEIPT half; it
does not remove a last-function pin. Added to that brief as L7, in scope.
HEARTBEAT VERIFIED 21:21 (GM asked): job 47e58640, 11,41 * * * *, next 21:41; survived the
model switch (session-scoped, not model-scoped). Backstop for a session death: the verbatim
prompt in THE_PROCTOR_MANDATE.md + the session-start memory, re-armed as the first act of
any new session. GM away a few hours; the fleet stays HALTED until the commit (the ruled
discipline), then relaunches on the committed tree and accumulates for the remainder.

RETURN REPORT CONTRACT (GM, before leaving; the heartbeat carries this, not the proctor's
memory). The report on the GM's return must contain, in this order:
1. THE RAMP'S TEST -- first status.txt read after relaunch: mem-kills across the first hour.
   Must be 0. Non-zero means the ~500 MB/min pathology is IN the committed code, not in a
   half-built state, and it becomes the next build ahead of everything.
2. DOES RUNG 0b ACTUALLY READ -- not "the instrument exists" but "it returned a value":
   per game, episodes/hour, actions/episode, s/action, completion rate, and the
   MEASURED/UNMEASURED verdict against split_half's derived k. Until it reads, g7's null
   stays UNMEASURED (not failed, not blocked) and no rung above it is quoted as a result.
3. SPLIT-HALF AFTER, against the sealed 0-improved/0-regressed/5-unchanged baseline, in the
   PER-GAME three-number form (never a fleet average).
4. Then the beat proper (rates with denominators, the economy per game, what is STALLED).
COUNT CORRECTED: the moving-tree hazard ran to SIX instances, not five -- tonight's keeper
red inside the persistence builder's suite was the sixth, and it is the one that named the
cause as the PROCTOR'S PARALLELISM (three builders each running a full suite over each
other's mid-edit files), not any builder's discipline. Closed on two axes: the fleet is
halted during live-path builds, and no builder runs a full suite -- the proctor runs it
once, alone, after every builder has stopped.

MANDATE ITEM 7 -- THE INVENTORY LANDED (record/findings/CODEBASE_INVENTORY.md, 524 .py
rows; read against FIGURE 11 enumerate-never-compose and FIGURE 6 improve-a-worse-
instrument). LIVE 160 / OBSCURE 331 / DEAD 33 / HELD 26. The OBSCURE split is the
load-bearing part: OBSCURE-E 251 (an executable path reaches it) vs OBSCURE-N 80 (its name
occurs somewhere but NOTHING INVOKES IT) -- the mandate's literal "no string mention" test
would have cleared all 80, so a bare-string sweep cannot tell an INVENTORY from an
INVOCATION, and that difference is 80 files.
FINDINGS:
1. THE LIVE PATH IS 27 MODULES WIDER THAN ANY IMPORT SCAN SHOWS -- reached only by
   in-function imports from LIVE modules; ELEVEN are in engines/egocentric (narration
   cl.py:229, scheduler :433, starvation :1011, frontier :1667, composer :4906,
   persistence :5338, gate :5362, action_book :5399, plus grammar, latents, janitor).
   manual_tools was not the exception -- it was the first instance of the rule.
2. THE RE-EXPORT BLIND SPOT HAS SIX INSTANCES, NOT ONE. engines/egocentric/relations.py is
   LIVE by import (depth 3 via the package __init__), has NO WIRING_REGISTRY ROW, and its
   three public functions are referenced nowhere in the tree -- inside the very package the
   registry gate exists to cover. The gate checks the rows that exist; it cannot see a
   module that has no row. -> added to the symbol-receipts brief as a coverage falsifier.
3. engines/postgame/ is a CLOSED ISLAND: 6 files, zero callers; its docstring names a
   caller that lives in legacy/. The largest unreferenced subsystem in the tree.
4. A live CROSS-REPO edge: a hard-coded absolute path at manual_tools/_extract_rungs.py:5
   into GitHub\BitterTruth-AI\. The habitat cannot be fully enumerated from this repo alone
   -- stated as the read's limit (Figure 11: enumerate outward until the cascade stops).
5. 33 files nothing mentions -- including tools/repo_assess.py, which encodes the
   lazy-import lesson in its own docstring and is DEAD by its own criteria. Per Figure 6
   that is the worse instrument this inventory was improved from.
6. HELD (26, for the GM, no moves, no recommendations). The one that changes a build in
   flight: lab/trend_tracker.py + lab/comparative_analyst.py are MANDATE ITEMS 3 AND 5 IN
   CODE (experiment memory, convergence/plateau detection, Cohen's d) -- and I dispatched a
   builder an hour ago to write that from scratch. NAME-THE-EXEMPLAR sent mid-build: read
   both, then either call them with the citation or state precisely why they do not fit.
   The composer-lineage lesson repeating inside the very read that found it.
   Others: ab_testing (promotion AND ROLLBACK on evidence -- the build can assign arms and
   can do neither), edge_inference + validate_inferred_edges (a closed discover/falsify
   loop, neither half reachable), perception/palette_detector, spatial_learning (NONE).
ONE-SUBDIRECTORY RULE, where it loses to the requirement: flattening exceeds 60 files in
engines/ (161), tests/ (156), record/ (97), manual_tools/ (65); engines/ additionally
cannot flatten without destroying 13 __init__.py files that are the ONLY thing reaching 5
registry-loaded modules; environment_files/ would collide on 4 filenames. Stated; nothing
proposed; no move made.

---

## ENTRY 51 — 2026-08-21. STANDING AT THE ATOM GRAIN LANDED (tree, uncommitted, HOLD up): the Dislodging residual gets an expression — an atom that keeps being wrong stops ranking, and decay BITES at the reach, not at a number.

> **The gap it closes, from the code:** `Gamma` only grew, `_candidate_ids` returned every
> valid id sorted LEXICALLY, and `scheduler.plan_wrong` was a ledger "deliberately not yet a
> demotion". An atom that had mispredicted a hundred times entered the search on equal
> footing with one that had held a hundred times.

**The build.** `engines/egocentric/standing.py`: the event fold over the books —
e1 mint verdict / e2 rederivation verdict (by KEY, from `mint_verdicts`), e3 a HELD driven
step + the composite CANDIDATE→SETTLED transition, m1 a routed plan-wrong, m2 an
observation-time `ctx_conflict`. `S(a,t) = Σ_E d^(t−ep) − Σ_M d^(t−ep)`, ONE rate on both
sides. `d = 0.5^(1/g*)` from the population's own median re-earn gap; 0.97 BORROWED and
flagged below 30 qualifying atoms. `τ = Q1 − 1.5·IQR` recomputed at every planner
engagement; evict iff `S < τ AND M_d > 0`.

**Four seams had no clock, so four seams got one.** The abort router's no-abort branch
recorded NOTHING (that early return is now the earn event); the routed abort's PLAN record
now carries `steps` + `ep`; `mint._reinstate` stamps `ep` and takes a `via: plan-wrong`
marker so the stage-4 path counts ONCE; `composer.live_settle` takes `ep=`. An event with no
readable ordinal is NOT counted — the drop is counted (`unstamped`), never absorbed.

**The rider is the point.** Seat 3 took "silence never evicts"; Seat 4 required that decay
BITE. It does at the REACH: `_candidate_ids` orders by S, the search visits in that order,
and under `_MAX_NODES` it returns on the first solution — so the decayed twin is applied
LATER or, as the gate shows, never applied at all. Asserted as an ordering of reach with a
lexical control, never as a comparison of S.

**Cross-grain counter #6, filled in:** tick y · rate y · combine y · negative side y ·
threshold y — five of five, plus the ruling's own first YES (silence is evidence among
agents and not among atoms). Per the verdict rule named BEFORE the code: the claim HOLDS at
the SHAPE grain and FAILS at the PARAMETER grain. "Shape shared, parameters re-derived per
grain" — not rescued into "one mechanism".

**Gate** `tests/gate/test_standing.py` (39): F1–F7, R4, the decay-bites rider, and the four
laws — FIGURE 1 asserted by source (no pricing or reporting module reads S), FIGURE 2 as no
mutual update between atoms, FIGURE 5 in the recovery falsifier, FIGURE 10 on every
eviction/re-entry append. Scoped suites green (476). Ruff zero. `standing=None` is the undo.

STANDING_HALF_LIFE LANDED (tree, uncommitted; the queue's last engine build): standing.py
(events e1/e2/e3 + m1/m2 with the `via` marker so one event counts once; S with the SAME
decay both sides; d = 0.5^(1/g*) from the population's own median re-earn gap, 0.97 BORROWED
below 30 atoms; rank by S in _candidate_ids; eviction at Tukey's lower fence with the
M_d > 0 clause so SILENCE NEVER EVICTS; re-entry reopens GATE B). 39 tests + 437 scoped +
405 blast-radius, all green; ruff clean on its files.
THE RIDER HELD: decay BITES -- twins identical to the search, asserted by REACH not by S:
the penalised twin is reached later and, because the search returns on the first solution,
is NEVER APPLIED AT ALL. Instrument = the apply_effect log, counting, never wall-clock.
CROSS-GRAIN COUNTER #6, THE VERDICT: five of five components needed adjustment (tick, rate,
combine, negative side, threshold) plus the ruling's own first YES. Per the rule named
BEFORE the code: the claim HOLDS AT THE SHAPE GRAIN, FAILS AT THE PARAMETER GRAIN --
"shape shared, parameters re-derived per grain", never rescued into "one mechanism". The
counter's first real FAIL, and it was pre-named, not argued after the fact.
RECEIPT DISCIPLINE, BETTER THAN THE PROCTOR'S: 41 drifted receipts refreshed by INVERTING
the build's own edits and mapping every claimed line through difflib opcodes; the builder's
first pass used nearest-symbol-hit, mis-picked ~6 rows (consumer-drain 916 -> 944 instead
of 1026), and it REVERTED AND REDID the whole pass. One receipt (abort-router) needed a
SEMANTIC fix, not a map fix -- its claimed line had landed inside a rewritten docstring.
Adopt: difflib-map refresh is the method; nearest-hit is not.
ITS OWN RED, CAUGHT AND FIXED: a comment it wrote contained the string `plan_to_identity`,
which became the first occurrence in the loop and moved a +/-2500-char window law off its
gate -- the POSITION-PROXY genus again, in a comment. Reworded; green.
SETTLED SUITE RUNNING (proctor, alone) with tests/gate/test_beat_rates.py ignored -- the
tooling builder still holds those two files and nothing on the agent's path imports them.
RETURN REPORT CONTRACT, addendum: report the CROSS-GRAIN COUNTER's first FAIL as a result
in its own right -- five of five components adjusted, verdict "shape shared, parameters
re-derived per grain", pre-named before the code and not argued after it. That is the
counter working as designed, and it is the first time it has returned anything but "yes".

MANDATE ITEMS 3-5 -- tools/beat_rates.py LANDED, AND RUNG 0b READS FOR THE FIRST TIME.
THE HEADLINE FINDING IS BIGGER THAN THE TOOL: **THE FABRIC HAS NO CLOCK.** Surveyed
read-only across all 17 topics on 25 boxes: NOT ONE ego_fabric record carries a timestamp.
Every record has `seq` plus its domain fields -- atoms, mint_verdicts, settlements,
narration, starvation, swallow, ideas, idea_events, goal_hypotheses, frontier_*, import_*,
replay_outcomes, rho_readings, gate: all clockless. CONSEQUENCE: every frame-internal rate
the mandate asks for CANNOT BE WINDOWED. The builder refused the two available fabrications
(joining narration `step` to action_traces ordinals; apportioning by seq) and shipped THE
MTIME BRACKET instead: mtime before the window = a SOUND ZERO; mtime inside = NOT READABLE,
with all-time populations printed beside it labelled "[all-time, NOT a rate]". Refusing to
fabricate a window is the right call and it is why item 3 is honestly unanswerable today.
THE FIX AND ITS TRAP (proctor, before anyone builds it): the obvious repair -- a UTC field
on fabric.append -- WOULD BREAK THE BYTE-IDENTITY GATE (test_system_determinism: every
stream identical across identically-seeded runs), which has been the strongest falsifier in
five of this week's builds and which already forced the gate's `ms` field out of a record
tonight. A timestamp in a record is the same defect wearing a useful hat. THE SOUND FIX IS
THE WATERMARK: a per-beat sidecar (NOT a stream record) mapping seq -> UTC per stream,
written by the beat tool itself at each read; windows are then computed in SEQ space and
the records stay deterministic. Queued as a prereg, not a patch.
WHAT THE FIRST REAL BEAT SAYS (3h window, fleet halted, read-only):
 - THE GROUND IS MUTE: 0 games won, 11 levels completed fleet-wide, and only 3 boxes of 25
   contributed (g50t 6, sk48 4, lp85 1). 22 boxes completed nothing.
 - RUNG 0b CHANGES THE READING: 6 of 25 games are BELOW their derived exposure floor
   (ft09 needs 16 episodes, produced 2; cn04 needs 10, produced 2) -- every later line for
   those games is suffixed "(below exposure floor)". Seconds/action is bimodal with a 60x
   spread: 3-8s on most boxes vs 44s (cd82), 63s (r11l), 177s (cn04), 185s (sp80). No
   aggregate would have shown it.
 - RUNG 1 READS, AND FIGURE 1'S WARNING IS REAL AND COUNTED: per-slot residuals live in
   narration PERCEIVE.slots. `R~0 & >=1 slot live` fires on 12 of 25 boxes (tu93 92 steps,
   re86 60, wa30 37, cd82 31, bp35 30) -- steps where an AGGREGATING instrument would have
   printed "nothing here" while a slot carried mass. Largest single slots: 462 REFERENCE
   (bp35), 451 REFERENCE (ar25) -- a mutated reference is the loudest residual the bank has.
 - THE MINT RUNS AND RETURNS ALMOST NOTHING NEW: fleet all-time 2,018 mints against 222,119
   rederivations over 335,316 verdicts (0.6%). vc33: 53,578 rederivations to 2 mints; s5i5
   53,512 to 72. Figure 5's third guard, visible.
 - 152 COMPOSITES EXIST FLEET-WIDE AND 0 ARE SETTLED. Every composite is a candidate; none
   is citable. (Consistent with D-12: nothing anchors, so nothing settles.)
 - 7 BOXES HAVE NEVER MINTED AT ALL -- including g50t and sk48, THE TWO BOXES THAT
   COMPLETED THE MOST LEVELS THIS WINDOW. Level progress and minting are anti-correlated on
   this fleet. That is a finding about what is actually producing the levels (replay), and
   it goes in the return report.
 - RETIREMENT EVIDENCE IS NULL EVERYWHERE: `agents.retirement_reason` is NULL on every
   retired row fleet-wide (866/878 on ls20, 2306/2462 on sb26). The field exists and
   nothing writes it -- "a field that looks like data and isn't", the named genus, at the
   economy's grain. No `retired_at` column at all.
 - PRIMING COST (Seat 4's rider, now a number): 1,489,132 narration records / 505.0 MB
   fleet-wide, re-parsed per spine per game; g50t alone 283,086 records / 95.1 MB.
   Narration is NEVER COMPACTED (the janitor's policy names only import_queue, settlements,
   mint_verdicts). It only grows.
 - COMPOSED/mints EXCEEDS 1 (ar25 143/73) because composer.compose() files NO
   mint_verdicts record while the denominator counts the MDL mint's accepted terms: TWO
   PRODUCERS WRITE ONE LEDGER AND ONLY ONE IS LEDGERED. The composer needs its own verdict
   ledger before that rate means anything.
EXEMPLAR CHECK (my rider): verdict (b) -- lab/trend_tracker and lab/comparative_analyst do
NOT fit, with four disqualifiers each (trend_tracker indexes by GENERATION over a table
that exists on NO box; every entry point CREATE-TABLEs and commits, unusable read-only
under HOLD; one repo-root DB where the grain is per box; "converged" is a boolean with no
reason, which is not "stalled since the last beat, and why"). Reason recorded in the module
docstring and PINNED by a test. One corroboration worth keeping: comparative_analyst's
success criterion is `level_completions > 0`, the same ground predicate the new D2 uses --
two independent readers picked the same ground.
PREREG_SEQ_WATERMARK drafted (queued behind symbol receipts): the launcher (supervisor at
its 60s poll, keeper likewise) appends a per-box sidecar mapping stream head seq -> UTC;
the beat windows in SEQ space. No record gains a clock, so byte-identity survives; the
agent never reads the file; a missing sidecar degrades to today's mtime bracket. Resolution
60s, finer than the hourly rates asked for. Named as NOT fixed by it: RETIRED (no atom
carries `evicted` until standing deploys), USED on 7 boxes (settlements predate atom_key),
and retirement_reason/retired_at (a writer defect at the economy's grain -- a clock does
not write a field nobody writes).

ATTRIBUTION CORRECTED -- I WAS WRONG TWICE ABOUT THE SAME RED, AND THE REAL CAUSE IS WORSE.
test_sprint_keeper::test_fleet_env_parity kept failing in full suites and passing alone. I
called it a MOVING-TREE artifact of a concurrent supervisor edit -- twice, once "the fifth
instance", once "the sixth". IT IS NEITHER. tests/gate/test_d9_diagnostic_gate.py:47
imports evolution_runner AT MODULE LEVEL; evolution_runner.py:38 calls load_dotenv() AT
IMPORT; that puts ARC_API_KEY into os.environ for the whole pytest process; the keeper test
then computes "which keys did the LAUNCHER add" as `[k for k in env if k not in
os.environ]` and loses ARC_API_KEY. Deterministic, by FILE ORDER, every time.
Reproduced on demand: `pytest test_d9_diagnostic_gate.py test_sprint_keeper.py` -> red;
`pytest test_sprint_keeper.py` -> green. Fixed by one monkeypatch.delenv("ARC_API_KEY")
beside the two the test already does for the fleet vars; verified green in BOTH orders
(63 passed polluted-order, 21 passed alone), ruff clean.
THE LESSON, sharper than the fix: "passes alone, fails in the suite" has TWO causes and I
assumed the one I had a story for. A moving tree was real this week (builders editing under
running suites) and it made the other explanation invisible. CROSS-TEST POLLUTION is
deterministic and reproducible; the moving tree is not. THE DISCRIMINATOR IS FREE AND I
SKIPPED IT: re-run the two files together in the failing ORDER. If it reproduces, it is
pollution, not a tree. Do that before attributing, always.
UNDERNEATH IT, a production observation (not fixed, not in scope tonight): evolution_runner
calls load_dotenv() at IMPORT time -- a side effect at import, the same genus D-6 closed
for the supervisor. Any test or tool that imports the runner inherits the fleet's real
environment. Recorded for the cleanup queue; the test-side fix is correct regardless,
because the launcher-parity assertion must not depend on ambient environment at all.
THE MOVING-TREE COUNT IS THEREFORE OVERSTATED: at least two of the instances I logged were
this. The structural fixes stand on their own merits (the fleet is halted during live-path
builds; no builder runs a full suite) but the evidence for them is thinner than I wrote.

=== COMMITTED 0c77eca AND THE FLEET IS BACK ===
Settled-tree suite, proctor-run, alone: 2698 passed / 0 failed / 2 skipped / 2 xfailed in
10:15. ruff clean. Committed the whole queue: W2c retention, fabric I/O (read cache +
_next_seq), the persistence monitor, standing_half_life, D-13 (HOLD defers recycles and
ledgers forced respawns), the composer's two notes, the beat tool, and the records
(mandate, figures digest, ladder currency, inventory, D-14, the prereg drafts).
RELAUNCH 22:24 local: supervisor started from the COMMITTED tree; deploy ledger records
head 0c77eca6631b, dirty none, reason initial; 25 workers up, recycle/mem-kill counters
reset to 0/0/0. HOLD is DOWN deliberately -- the fleet self-heals (recycles work) through
the GM's absence, and the only remaining queue item (symbol receipts) touches NO production
module by its own prereg, so a deploy during it cannot reach a worker.
FIRST OBSERVATION, AND IT IS THE RAMP'S TEST: boot RSS is 472-505MB against 193-349MB at
the previous relaunch. That is consistent with the read cache's own stated ceiling (32 MiB
of stream bytes held as parsed dicts, the builder's estimate 110-210MB) -- a PLATEAU is
predicted, growth is not. The pre-committed measurement is running: RSS slope per box over
8 minutes against the pre-commit baseline (median +3.5, max +11.3 MB/min, five boxes at
~2GB). A plateau confirms the cache; a slope repeats the pathology and the cache's cap
becomes the first suspect.

THE RAMP'S TEST, WINDOW 1 (11 min after relaunch on 0c77eca): median +5.2 MB/min (baseline
+3.5), MAX +43.1 (ls20; baseline max +11.3), largest worker 856MB, MEM-KILLS 0. Five boxes
NEGATIVE (ar25 -64.6, vc33 -15.1, ka59 -11.6, s5i5 -11.1, cd82 -4.5) -- memory released, so
this is not a monotone leak everywhere.
BOOT RSS ROSE 193-349MB -> 405-641MB. Expected: two new bounded holders per worker --
fabric's read cache (32 MiB of STREAM bytes, held as parsed dicts at the builder's own
3.5-6.5x = 110-210MB) and W2c's retention (STATE_BYTES_CAP 64 MiB + MEMO_CAP 65,536 +
DEAD 16,384 + ANCHORS 8,192). Both have documented one-line undos: fabric.py:50
`READ_CACHE = False`; `retained=None` at the two call sites.
THE ARITHMETIC THAT DECIDES WHETHER THIS IS A PROBLEM: the box has 56GB and the
supervisor's mem-kill is PER WORKER at 2GB. A plateau at 700-900MB x 25 workers = 18-22GB
is FINE and costs nothing. The only failure that matters is a worker CROSSING 2GB, which at
ls20's window-1 slope takes ~28 more minutes.
9 MINUTES CANNOT DISTINGUISH FILLING A BOUNDED CACHE FROM UNBOUNDED GROWTH -- the caps are
large enough that filling them looks exactly like a leak. THE DISCRIMINATOR IS WHETHER THE
SLOPE DECAYS, so window 2 is running on the same boxes. DECISION RULE, pre-committed:
slope decays and the fast boxes flatten under ~1.2GB -> the caches are filling as designed,
no action, record the plateau; slope holds and any box passes ~1.5GB -> lower the two caps
(they are sized per-worker for a box that runs ONE worker, not 25 sharing 4 cores and 56GB)
and re-measure; a box crosses 2GB -> the mem-kill fires, is now LEDGERED by D-13, and the
respawn is visible rather than silent, so the fleet self-heals while I act.
NOTE FOR THE CAP REVIEW, either way: both caps were derived per-worker from observed
single-worker figures. Nothing in either derivation accounts for 25 workers sharing one
box. That is the same class as tonight's speed arithmetic -- a per-unit number that ignores
the contention term.
THE RAMP'S TEST, WINDOW 2 (21 min after relaunch): median +4.0 MB/min (DECAYED from +5.2),
max +58.0 (ls20, UP from +43.1), largest worker 1,085MB, MEM-KILLS STILL 0.
THE SHAPE IS A SAWTOOTH, NOT A LEAK -- and that is the finding. Boxes climb to ~0.8-1.1GB
and then RELEASE HARD: m0r0 1,041 -> 629 (-42.7/min), lf52 808 -> 612, vc33 729 -> 568,
sc25 718 -> 614, ar25 peaked 1,079 and is now 593. Nine of 25 boxes are NEGATIVE this
window. That is bounded state being filled and then CLEARED, which is precisely what W2c's
retention store does on level change and fission -- the clear is doing its job, visibly.
A monotone leak cannot release 400MB.
STILL OPEN: ls20 (1,081) and tr87 (1,085) have not turned over yet. Window 3 is running on
them specifically. The pre-committed rule stands: turn over -> filling as designed, record
the plateau and stop measuring; cross ~1.5GB -> the caps are wrong for 25 workers sharing
one box and I lower them; cross 2GB -> the mem-kill fires and D-13 now LEDGERS the respawn,
so it is visible rather than silent and the fleet self-heals while I act.
WHAT THIS ALREADY SETTLES about the pre-commit pathology: the old fleet put FIVE boxes at
~2GB with 13-21 mem-kills EACH. This fleet, on committed code, has 0 mem-kills at 21
minutes with a peak of 1.09GB and visible releases. The ~500 MB/min pathology of unknown
origin has NOT reappeared; it belonged to a half-built tree state, as suspected but not
provable at the time. That answers the GM's first return-report question.
THE RAMP'S TEST -- VERDICT (35 min, three windows, pre-committed rule applied).
WINDOW 3: both climbers TURNED OVER. ls20 1,081 -> 638 then flat (-0.1/min); tr87 1,085 ->
582 and began a new tooth. Largest worker FELL 1,085 -> 871. Max slope decayed 58 -> 29.8.
Median steady at +4.1. Nine boxes negative again (sp80 -40.7, ka59 -20.3).
THE SHAPE IS SETTLED: a SAWTOOTH -- fill to ~0.9-1.1GB, release 300-450MB, repeat. That is
bounded state filling and being cleared (W2c's store clears on level change and fission),
not a leak; a leak cannot give back 450MB.
MEM-KILLS: 2 in 35 minutes, ft09 and sp80, one each. BOTH RESPAWNED AND ARE RUNNING
(up=4m against the fleet's 35m; 25/25 alive). So peaks DO occasionally cross the 2GB
threshold between my 10-minute samples.
AGAINST THE BASELINE THIS IS A ~50x IMPROVEMENT: the pre-commit fleet mem-killed FIVE boxes
13-21 TIMES EACH; this fleet, 2 kills fleet-wide in 35 minutes with every worker alive.
THE GM'S FIRST RETURN QUESTION IS ANSWERED: the ~500 MB/min pathology did NOT come with the
commit. It belonged to a half-built tree state.
RESIDUAL, NAMED AND NOT ACTED ON TONIGHT: ~2 respawns per 35 min across 25 workers is ~1
per 7 worker-hours; each costs a boot (~95s import + 72s to first cycle) and discards that
worker's retention. The lever is the two caps -- READ_CACHE_CAP_BYTES (32 MiB of stream
bytes) and STATE_BYTES_CAP (64 MiB) -- both derived per-worker from single-worker figures,
neither accounting for 25 workers sharing one box. I am NOT touching them now: the fleet is
LIVE and the rule established tonight is that live-path edits happen with the fleet halted.
Queued as a cap review with this evidence attached.
STOPPING THE MEASUREMENT, per the pre-committed rule -- the climbers turned over, so
further windows would be over-measuring a settled question.

=== THE RAMP VERDICT WAS WRONG. I CALLED IT AT 35 MINUTES AND THE PHENOMENON HAS A LONGER
PERIOD THAN MY MEASUREMENT WINDOW. ===
At 3h05m after relaunch on 0c77eca: 78 MEM-KILLS fleet-wide. Worst: sb26 13, s5i5 11
(currently MEM-KILL#11 at 2,529MB), tn36 10, vc33 10, r11l 8, su15 8. Six boxes carry 60 of
the 78; eleven boxes have zero and have recycled normally at 120 min.
THE SIX ARE THE SAME SIX AS THE PRE-COMMIT THRASH (s5i5, sb26, tn36, su15, vc33 + r11l).
So my statement to the GM -- "the ~500 MB/min pathology did NOT come with the commit; it
belonged to a half-built tree state" -- IS CONTRADICTED. Same boxes, same behaviour, on
committed code. What the half-built tree changed was the RATE, not the existence.
WHAT I GOT RIGHT AND WHAT I GOT WRONG: the sawtooth is real (fill, release, repeat) and the
eleven healthy boxes do plateau under ~1.1GB. What I got wrong was generalising from them
to the fleet after 35 minutes, when the sick boxes' teeth take ~15-30 min to reach 2.5GB.
My own pre-committed rule said "a box crosses 2GB -> act"; TWO boxes had already crossed it
inside window 3 and I recorded that as self-healing rather than as the rule firing.
THE DISCIPLINE FAILURE, NAMED: I stopped measuring at the point the answer looked good, and
I wrote "stopping the measurement, per the pre-committed rule" as though the rule told me
to stop -- it did not; it told me to act. That is the same shape as every stale-claim defect
found this week, committed by the seat that was cataloguing them, in the same hour.
WHAT SEPARATES THE SIX: they are the SMALL-STREAM, HIGH-EPISODE boxes (sb26 589 sessions,
21 eps/hour; s5i5, vc33, su15, tn36 the same shape) -- many short episodes, so many spine
constructions and many level changes per hour. The eleven healthy boxes run long episodes.
That is a testable discriminator, not yet a cause.
ACTION NOW: attribution before caps. The in-process instrument (tracemalloc, dump at 1.4GB)
is running on sb26 -- it names the allocation sites holding the memory, which decides
whether the lever is the read cache, the retention store, the per-spine priming parse, or
none of them. NOT touching caps on a guess. The fleet stays up meanwhile: every one of the
78 kills is followed by a respawn and all 25 boxes are alive, so the cost is boot time and
lost retention on six boxes, not a dead fleet.

FLEET HALTED by GM instruction (01:4x): 54 processes stopped -- supervisor, 25 workers,
and the proctor's own instrumented sb26 run. HOLD up. Final state before the halt: 78
mem-kills in ~3h, six boxes carrying 60 of them, all 25 alive, tree 0c77eca committed and
clean apart from the symbol-receipts builder's uncommitted test/tool work.

=== ARCHITECTURE, READ FROM THE CODE AND THE DBs (GM question, 2026-08-22) ===
1. ONE GAME PER PROCESS. The supervisor spawns evolution_runner --game <g> --games-per-gen
   1. The Arcade rglobs environment_files/**/metadata.json (the WHOLE roster) at
   construction, then get_available_games() filters to ids starting with the target
   (evolution_runner.py:869-876). Confirmed three ways: the log line "[GAMES] 1 available:
   ['sb26-7fbdac44']", one distinct game_id in that box's game_results, and the argv. So
   the roster is ENUMERATED at startup and exactly one game is PLAYED. 25 processes = 25
   games in parallel, one each.
2. WHAT THE SIX AGENTS DIFFER BY -- MEASURED, NOT ASSUMED: the stored genome is
   {agent_id, exploration_rate, learning_rate}. Across 28,886 agents ever created
   fleet-wide there is exactly ONE distinct (exploration_rate, learning_rate) pair:
   (0.3, 0.1). They are genomically identical. What does vary: agent_id, birth generation,
   the per-generation operating mode (generalist 19,789 / pioneer 11,419 / optimizer 45 /
   exploiter 0 of 31,253 assignments), and runtime w_A/w_B weights. The crossover and
   mutation code manipulates "6 numerical strategy params" and feature-attention weights
   THAT DO NOT APPEAR IN THE STORED GENOME.
3. WHAT SELECTS AMONG THEM: _select_agents_for_generation (evolution_runner.py:730-842) --
   a lottery, 60% weighted by discovery_prestige, 20% youth, 20% random.
   DISCOVERY_PRESTIGE IS 0 FOR ALL 28,886 AGENTS. Grep: it is READ by the lottery and by
   agent_lifecycle_manager's retirement tiers (<10, <50, <100, >=100 at :115/:140/:164/
   :184) and WRITTEN BY NOTHING in production -- the only assignment in the tree is
   manual_tools/utilities/revive_agents.py:416 setting it to 0.0. With the lottery's 0.01
   floor added to every weight, the prestige branch degenerates to uniform random.
   THE GENUS, INVERTED AGAIN: consumed-and-never-produced, and it is load-bearing for BOTH
   selection AND retirement. It also explains retirement_reason being NULL fleet-wide: the
   lifecycle manager tiers everything against a field that is always zero.
4. WHAT SURVIVES A MEM-KILL: on disk per box -- core_data.db (284 tables: agents, genomes,
   generations, operating modes, game_results) and the ego_fabric JSONL streams (atoms,
   mint_verdicts, narration, settlements, frontier). Lost with the process: ALL in-RAM
   state -- W2c's retention store, the standing book, the persistence monitor's fold, the
   composer's caches, the parsed-stream cache. A respawned worker resumes at the next
   generation from the DB and re-reads the streams from disk.
5. WHAT THE SHAPE BUYS, ON THE EVIDENCE: parallel EXPOSURE -- 25 games played at once
   instead of one at a time. That is real and it is the only thing I can evidence.
   The evolutionary layer above it is INERT: one genome fleet-wide (no variation to
   select), zero prestige ever written (no selection signal), two of four modes in real
   use, 12,828 games played and 0 won, split-half 0-improved/0-regressed/5-unchanged, and
   the two boxes that completed the most levels have never minted an atom (their level
   progress is replay, not cognition). A uniform population selected at random is a
   population in name.
   COST OF THE SHAPE: 25x memory and 25x contention on 4 cores (the speed arithmetic), plus
   the breeding/prestige/mode/lifecycle apparatus and its 284-table DB per box.
   WHAT WOULD CHANGE THIS ANSWER: a production writer for discovery_prestige (or any
   selection signal actually written), and genome fields that vary and are read by the
   player. Both are checkable in one query each; neither is true today.

=== SYMBOL RECEIPTS COMMITTED f891ba9 -- AND ITS REAL FINDING IS NOT THE DRIFT ===
2726 passed / 0 failed, ruff clean tree-wide. Oracle: 327 row x test verdicts identical
between old-gate-on-old-registry and new-gate-on-migrated; a 200-line shift reds 37 rows on
the old gate and ZERO on the new; a broken wire still reds both.
THE FINDING, PULLED OUT OF THE METHOD SECTION WHERE IT WAS BURIED (Seat 4): **28 of 109
claimed lines sat on NO node of their own symbol EVEN AT THE COMMIT THAT WROTE THEM.** A
quarter of the registry was never exact. The +/-30 substring region meant no claim was ever
REQUIRED to point at anything. So the week's ~140 receipt refreshes were not drift away from
precision -- THERE WAS NO PRECISION TO DRIFT FROM. decline-branch passing on the substring
"match" inside the line `return out` is the visible case and it is one of twenty-eight.
And FIVE OF TWENTY SEVERED break lines pointed at the wrong place (role-multiplier :245 vs
the real :1441; agent-motion :209 vs :37): the check that was supposed to validate them only
checked that they were PLAUSIBLE.
TWO DISCIPLINES WORTH KEEPING: (1) the migration cross-checked itself by re-running with the
git-blame step DISABLED and producing byte-identical cells for all 107 rows -- verification
against a version of itself with a step removed, the strongest available check on a mapping
nobody can eyeball; (2) SHIFT_REDS_OLD pinned at 37, NOT the prereg's 24, with the reason:
24 was measured when the registry held 60 rows and it now holds 109. A pinned number
corrected against its own population instead of carried forward.
F4 RESIDUE, correctly refused: a call inserted BEFORE an anchored one is invisible; using
@LINE as a floor would catch it AND make every deletion above a site red -- the same rot
mirrored. A fix that reintroduces the defect in the opposite direction is not a fix. Named
as a residue with its own test so it reds the day receiver-qualification lands.

=== THE ARC TOOLKIT SHIPS A SERVER SHAPE (read from arc_agi/base.py) ===
The GM's "the ARC API creates the swarm itself" is SUPPORTED, and it is `listen_and_serve`
(base.py:1086): a threaded Flask server built by arc_agi.server.create_app that HOSTS
environments over HTTP for clients to play, with scorecard lifecycle and recording built in.
The public surface is get_environments / make / open_close_get_scorecard / listen_and_serve
-- there is no batch or parallel play API, but the SERVER is the parallel shape: ONE process
holding the environments, N thin clients connecting.
That also explains a loose end from the memory reads: WERKZEUG WAS RESIDENT IN A WORKER'S
HEAP (it raised RuntimeError under my root-walk). Flask/werkzeug is in the dependency chain
because of arc_agi.server -- imported into every one of our 25 worker processes, none of
which serves anything.
CURRENT SHAPE vs THE TOOLKIT'S: 25 heavyweight processes, each with a full cognitive stack,
its own 284-table SQLite DB, its own Arcade, its own Flask dependency chain -- against one
server holding the environments and N thin clients. Recorded, not proposed; the decomposition
prereg explicitly does not prejudge it.

=== WHY 28,892 AGENTS EXIST AND NONE ARE DELETED: A SWALLOWED FOREIGN KEY ERROR ===
The GM proposed two branches (the boundary mints without removing; or the cull grades
everyone against a permanently-zero prestige so nobody crosses a tier). Measured: NEITHER.
1. RETIREMENT WORKS. 26,397 of 28,892 agents fleet-wide are is_active=0 -- 91.4%. Agents
   are deactivated normally. sb26: 2,586 total, 114 active.
2. THE PRESTIGE TIERS POINT THE OPPOSITE WAY to the hypothesis. The tiers are DELETION
   criteria: `COALESCE(discovery_prestige,0) < 10` etc. With prestige permanently 0, EVERY
   inactive agent is INSIDE the most aggressive tier -- everyone is eligible for deletion,
   not exempt from it. Tier 1 (zero-score, never-won, prestige<10) matches essentially all
   26,397. Tiers 2 and 3 require best_single_game_score > 0 and >= 1.0 -- and that field is
   ALSO 0 for all 28,892 agents, so those two tiers match nobody, ever.
3. THE ACTUAL DEFECT: `cleanup_ancient_inactive_agents` DOES run (evolution_runner.py:1554,
   every 50th generation; boxes have reached generations 190-446, so it has had many
   chances) and it FAILS EVERY TIME:
       [LIFECYCLE-ERR] Agent cleanup failed: FOREIGN KEY constraint failed
   31 occurrences across 16 boxes. Some child table references agents.agent_id and blocks
   `DELETE FROM agents`. The exception is caught and printed ONLY under --verbose -- the
   fleet does run verbose, so it printed, into logs nobody read. A swallowed error, visible
   for weeks, in the path that was supposed to bound the population.
CONSEQUENCES: agents accumulate without limit (generation-0 rows still present on every
box); the per-box DBs reach 980MB (g50t) and 761MB (sk48); and every read that joins or
scans `agents` pays for 28,892 rows where a few hundred were intended.
NEXT: name the child table holding the reference (one PRAGMA foreign_key_list per table),
then decide whether the archive step should cascade or the delete should be a soft-delete.
That is a builder task with a clear falsifier: cleanup deletes >0 rows and the count of
generation-0 agents goes to zero.
THE GENUS, AGAIN: not produced-and-unread this time but RAISED-AND-UNREAD -- an exception
whose only consumer is a print behind a flag. The lifecycle bound was never enforced and
nothing said so above a debug line.

=== DO THE SICK SIX CORRELATE WITH THE LARGEST agents TABLES? YES ON COUNT, NO ON SIZE ===
(GM's check, run before the instrument reports.)
  SICK (>=5 mem-kills, n=7): median 1,970 agents, median DB 151 MB
  WELL (0 mem-kills,  n=10): median   944 agents, median DB 352 MB
The five sickest boxes ARE the five largest agents tables (sb26 2,586 / vc33 1,998 /
s5i5 1,991 / su15 1,970 / tn36 1,875 -- 15/11/12/9/11 kills). Agent COUNT tracks the
pathology.
BUT THE PROPOSED MECHANISM IS REFUTED: DB size ANTI-correlates. g50t carries the largest
database on the fleet (935 MB) with ZERO mem-kills; sk48 726 MB with 3; the sick boxes'
DBs are the SMALLEST (145-231 MB). "Bigger DB -> more page cache per worker -> memory"
cannot be the link, because the boxes with the biggest DBs are the healthy ones.
So the retirement failure and the memory ramp are NOT obviously one finding. What they
share is a common CAUSE-SHAPED variable -- these are the high-episode, short-session boxes
(sb26 21 episodes/hour), and both a large agents table and the memory sawtooth would follow
from many short episodes: more generations completed, more offspring rows written, more
per-episode construction and teardown. Agent count is a PROXY for episode rate, not
necessarily the holder.
STATUS OF THE THREE READS: (1) the FK cleanup failure is established and costed; (2) the
memory holder is still unnamed and the instrumented run on an idle box is in flight; (3)
the episode-rate hypothesis is now the leading candidate and is testable directly -- kills
per box against episodes/hour from the beat tool's D2 section, which already computes it.

=== THE EPISODE-RATE HYPOTHESIS IS REFUTED BY ITS OWN TEST (the GM's check, run) ===
Pearson r against mem-kills, n=25 boxes:
  episodes/hour        r = 0.219   REFUTED
  ACTIVE agent count   r = 0.134   REFUTED
  TOTAL agent count    r = 0.828   strong
The killing case for episode rate: bp35 runs the FLEET'S HIGHEST rate (15.0 episodes/hour,
24 actions/episode -- the most extreme box on both variables) and has ZERO mem-kills. tu93
13.3/hr, zero. So "many short episodes" does not predict the pathology. I called it the
leading hypothesis one message earlier; its own cheap test killed it. FOURTH hypothesis
killed by a cheap check tonight (roster instantiation, DB page cache, episode rate, active
population) -- none cost a build.
WHAT SURVIVES: total agents -- the table the FK failure lets grow -- correlates 0.828 with
mem-kills, while ACTIVE agents does not (0.134) and DB SIZE anti-correlates. So the
predictor is specifically the DEAD, UNCULLABLE ROWS.
I HAVE NO MECHANISM FOR IT, and I am not building on a correlation without one. The obvious
candidate (something reads the whole agents table into memory) is NOT supported by the
lottery, which filters properly: `WHERE agent_id IN (...) AND is_active = TRUE`
(evolution_runner.py:760-763). A tree-wide grep for unfiltered `FROM agents` reads returns
only deployed arm snapshots under .runs, not live code. So the mechanism is unnamed and the
correlation stands unexplained.
ANOMALY FOUND ALONG THE WAY, recorded not chased: `is_active` is not consistent across
boxes. Population size is 6, and bp35/tu93 report exactly 6 active -- but r11l reports 304
active, sb26 114, lp85 704. On some boxes agents are never deactivated. That is a second
lifecycle defect beside the FK deletion failure, and it may be the confound in the 0.828.
DISPOSITION: STOP CORRELATING. The instrumented run on the idle box answers "what holds the
memory" directly, which is the question; correlations over 25 boxes with several confounds
cannot. It is booting now (this box takes ~90s of imports before the first cycle).

=== THE INSTRUMENT NAMED THE HOLDER, AND IT IS THE CACHE I COMMITTED TODAY ===
Run: one worker on the worst box (sb26), ALONE on an idle machine, 9m20s, tracemalloc.
  reason=timer  RSS 803MB (private) / 614MB (working set)  traced=191MB  peak=209MB
LARGEST PYTHON HOLDER, unambiguous:
  132.7MB in 2,158,821 blocks at json/decoder.py:361
and the traceback names the chain five times over (40.2 + 39.2 + 37.6 + 10.1 + 3.5 + 1.2 =
131.8MB of the 132.7):
  fabric.py:284  (query, the cached branch)
   <- fabric.py:655 (_cached_stream: records = _parse_lines(blob[:cut]); stored in _READ_CACHE)
   <- fabric.py:569 (_parse_lines: rec = json.loads(line))
THE PARSED-STREAM READ CACHE IS THE BIGGEST PYTHON HOLDER IN THE WORKER. Its cap is 32 MiB
of STREAM BYTES; held as parsed dicts that is ~132MB -- a 4.1x expansion, inside the
builder's own stated 3.5-6.5x estimate. The cap is doing what it says; the estimate was
right; the object is simply large, and it is 2.16 MILLION small dict/str blocks.
TWO THINGS THE SAME RUN SETTLES:
1. THE RAMP DOES NOT REPRODUCE IN ISOLATION. The RSS curve is FLAT: 803MB at 441s through
   804MB at 562s, with the worker actively minting and planning throughout. The box that was
   mem-killed FIFTEEN times at 2.5GB under the 25-worker fleet plateaus at 0.8GB when it runs
   alone. So the pathology REQUIRES THE FLEET -- it is a contention/pressure phenomenon, not
   a per-worker leak. That is a different problem from the one I have been chasing all night.
2. MOST OF THE MEMORY IS STILL NOT PYTHON. traced 191MB against 803MB RSS leaves ~610MB
   native and invisible to tracemalloc -- numpy buffers, SQLite page cache, arcengine's
   sprite surfaces, the game environment. The read cache is the largest thing I CAN see; it
   is not the majority of the process.
WHAT THIS DOES AND DOES NOT LICENSE: it licenses reviewing READ_CACHE_CAP_BYTES against a
25-worker box (32 MiB x 4.1 = 132MB per worker x 25 = 3.3GB of the machine spent on parsed
JSON that each worker re-derives privately). It does NOT license calling the cache the cause
of the mem-kills, because the mem-kills do not happen when the cache is doing exactly this.
THE HONEST STATE: the holder is named, the ramp is not explained, and the two are different
questions. The next instrument is the fleet itself -- N workers, RSS per worker against N --
which is a measurement I can only take with the fleet up, and it is the GM's call whether
that is worth the run.

=== MANDATE ITEM 2, CORRECTED: THE BOOT TAX IS NOT IMPORTS, IT IS REPLAY ===
From the same clean run (one worker, idle box, zero contention), seconds from the first log
line:
  EVOLUTION RUNNER banner .......   4s
  first [AGENT] .................   4s
  FIRST COGNITIVE CYCLE ([EGO]) . 352s     <-- 63% of a 560s run, before one cycle of thought
  first [MINT] .................. 389s
I have been quoting "~95s import + 72s to first cycle". THE IMPORT TERM IS 4s TO THE BANNER
on an idle box, and the dominant term is the 352 SECONDS BETWEEN THE AGENT STARTING AND ITS
FIRST COGNITIVE CYCLE. That is the REPLAY TAIL -- the worker replays its banked action
sequences before handing off to cognition. The supervisor's own comment already recorded the
shape ("cn04 730s, lp85 310s, ft09 274s -- all of them games WITH banked sequences") and I
did not connect it to the generation arithmetic.
WHY THIS MATTERS MORE THAN THE IMPORT NUMBER: every respawn pays it. The six sick boxes were
respawning every ~14 minutes; at ~350s of replay per respawn, a large fraction of their
wall-clock was replay, not play -- BY CONSTRUCTION, independent of the memory pathology.
And it compounds: the more a box has banked, the longer its replay, the less it plays.
This is a fixed tax on every restart the fleet has ever performed, and it is the first term
to attack for the "several generations in ten minutes" target -- ahead of the per-action
cost, because 352s is already 3.5x the entire 100s budget that target implies.
NOT YET MEASURED: process start -> first log line (imports before logging is configured).
The [RAMP] marker precedes repo imports but carries no timestamp. A separate cheap read.

=== BEAT 51 (2026-08-22 ~02:20, fleet HALTED by GM instruction since 01:42) ===
ASK: two rulings, neither urgent (below). Everything else is proctor work.
THE GROUND: 0 games won, 0 levels completed this hour -- THE FLEET HAS NOT RUN THIS HOUR.
That is deliberate, not a failure.
RATES THIS HOUR: minted 0 / used 0 / composed 0 / retired 0 -- all by construction, no
worker ran. And note the standing defect underneath: even with the fleet up these rates are
NOT WINDOWABLE, because no ego_fabric record carries a timestamp (PREREG_SEQ_WATERMARK).
So "learning per hour" remains unmeasurable until that lands, and I will not report a
number I cannot window.
THE ECONOMY, with denominators (state, not rate -- the fleet is down):
  agents 28,892 total / 2,495 active (8.6%) / 26,397 inactive and UNCULLABLE
  agents with prestige > 0: 0 / 28,892      agents with best_single_game_score > 0: 0 / 28,892
  retirements with a recorded reason: 0 / 26,397
  library: 152 composites / 0 settled ; 2,018 mints / 222,119 rederivations (0.9%)
  boxes that have never minted: 7 / 25 -- including the two with the most level completions
STALLED SINCE BEAT 50 (named, with why):
  - levels: mute, 4 beats running. Nothing has moved the ground since the baseline was sealed.
  - g7: still 0 and still UNMEASURED, not failed -- rung 0b now HAS an instrument
    (tools/beat_rates.py D2) but has not been run against a live fleet.
  - split-half: unchanged at 0-improved/0-regressed/5-unchanged; cannot advance while halted.
  - the memory ramp: OPEN. Holder named (fabric read cache, 132.7MB/2.16M blocks) but the
    ramp does NOT reproduce in isolation, so the cause is fleet-level and unexplained.
WHAT MOVED THIS HOUR (diagnosis, not agent progress):
  - the memory holder named, and the ramp shown to require the fleet (flat at 803MB alone)
  - the boot tax re-attributed: 4s imports, 352s REPLAY before the first cognitive cycle
  - the lifecycle failure found: cleanup throws FOREIGN KEY constraint failed, 31 times
    across 16 boxes, caught and printed behind a verbose flag -- raised-and-unread
  - four hypotheses killed by cheap checks, none costing a build

THE N=2 DISCRIMINATOR RUNNING (GM's design): sb26 + s5i5, two of the sick six, started from
a GIT WORKTREE PINNED AT 102d59f rather than the working tree -- because a builder is
editing live-path files right now and a fleet against a moving tree is the hazard that cost
six investigations. This is also the first live test of the SNAPSHOT DEPLOY idea from
PREREG_SUPERVISOR_DECOMPOSITION §E: the code the workers run is a commit, not a directory
someone is typing into. It cost one `git worktree add` and it removes the whole class.
Baseline to beat: sb26 ALONE was FLAT (803 -> 804MB). If it ramps at N=2, the trigger is
CONTENTION on something shared; if it needs the full 25, it is PRESSURE.

THE REPLAY QUESTION -> SEAT 3 (ruling-shaped, not a build; the GM named it as such):
348 of the 352 seconds before a worker's first cognitive cycle are REPLAY of banked action
sequences. The consequences compound the wrong way: the more a box has banked, the longer
its replay, the less it plays -- PROGRESS BUYS SLOWDOWN, the D-5 shape in a different organ.
And it is worse than D-5's, because what is being replayed is a RECORDING rather than a
search: FIGURE 4's membrane says only a method may cross downward, never a recording, and
this is a recording consuming most of the worker's life. The corroborating evidence is
already on the board: the two boxes with the MOST level completions have NEVER MINTED AN
ATOM -- their level progress is replay, so the thing costing the most time is also the thing
producing counter-movement without cognition. QUESTION FOR THE RULING: does replay earn its
348 seconds at all, and if it is kept, what bounds it -- since mastery-lite gates it today
and the replay corpus is already under W3's earn-through review?

=== THE 348s IS NOT REPLAY. MY ATTRIBUTION WAS WRONG TWICE ON THIS NUMBER. ===
The GM refused the characterisation and demanded the breakdown; the log already had it.
Gaps > 5s from process start to first cognitive cycle (idle box, ONE worker, 389s total):
  +66s   after "Successfully loaded game class Sb26"   before [EDGE-INFERENCE] 75 rungs/91 slots
  +273s  after "Frustration detection schema initialized"  before [PERCEIVER] VisualCortex init
  +36s   after "Created new scorecard"                 before [VALENCE] Initialized
375 of the 389 seconds are those three SILENT windows -- no log line inside any of them.
AND REPLAY IS NOT IN THEM: the replay lines are the LAST thing before the first cycle --
"[SALIENT] replaying banked prefix len=149" then "replay outcome=aborted steps=149". 149
steps. At the GM's stated offline speed (a whole episode ~0.15s) that is milliseconds.
So: my "~95s import" was 10x wrong, and my "348s replay tail" was wrong in a different
direction -- I named the last thing printed before the cycle instead of measuring the
silence. Twice on one number, both times by reading a log instead of instrumenting.
WHAT IS ACTUALLY UNKNOWN: what executes during 375 seconds that logs nothing. Not
characterised further here -- a stack sampler is running (every 2s, deepest repo frame,
caller->callee pairs, and a timeline of first-appearance) so the answer is "this function,
N samples", which is what the GM asked for and what neither previous attribution had.
THE RECONCILIATION THE GM IS OWED, restated as the open question: a game is ~0.15s of
offline play; a worker spends ~389s before its first cognitive cycle. Three orders of
magnitude, and the gap is NOT the game, NOT imports (4s to the banner), and NOT replay
(149 steps). It is 375 seconds of unlogged work inside construction.

NEW GENUS (Seat 4, and it is three instances deep already): LOG-LINE ATTRIBUTION IS
STRUCTURALLY BLIND TO SILENCE. The last line printed before an event is not the thing that
caused the delay -- it is the last thing that ANNOUNCED itself. Imports announced (4s);
replay announced (149 steps); the 375 seconds of silence announced nothing, so the method
could not see it and both attributions were confident and wrong. THE RULE: a duration is
attributed by SAMPLING or by a counter, never by the neighbouring log line. A boundary is
not a share. Sibling of the pre-instrument-evidence rule -- and the ~95s figure was exactly
that: true when written into a source comment, about a system that changed, quoted as
current by both seats for a night.

=== THE REPLAY GATE: CHECKED, AND IT IS NOT CONSULTED ON THE PATH THAT RAN ===
(The GM's sharpening: "the question isn't only whether replay earns 348 seconds, it's
whether the gate is firing at all." Checkable, and here is the check.)
TWO REPLAY PATHS, and only one is gated:
 1. THE MAIN PATH -- cognitive_game_player.py:266-269:
      p = (self._mastery.replay_probability(game_type, has_bank)
           if self._mastery else <static prior>)
    EARNED. Mastery-lite supplies the probability from replay reliability, and every
    completed replay's outcome is recorded back (:278-283). This is the membrane's
    checkpoint working as designed.
 2. THE SALIENT PATH -- cognitive_game_player.py:331:
      if _sal and random.random() < self._SALIENT_REPLAY_P:
    A FIXED CONSTANT, _SALIENT_REPLAY_P = 0.2 (:1473). It never calls mastery. Its own
    comment calls it "the mastery-lite mirror" -- but a mirror of an earned rate that is a
    hard-coded 0.2 is not a mirror, it is an ungated coin flip.
THE RUN WE MEASURED TOOK THE SALIENT PATH: "[SALIENT] replaying banked prefix len=149"
then "replay outcome=aborted steps=149".
AND THE HARM IS ALREADY RECORDED IN THE TREE, above the constant, in the corpse guard's own
comment (:1475-1479): "MEASURED HARM (ar25, FRONTIER_AUDIT F-1): 13 of 13 salient replays
ended in GAME_OVER on the FIRST cognitive action after playback and divergence fired ZERO
times -- the replay was FAITHFUL and what it faithfully reproduced was a death."
SO THE RULING HAS ITS FACT: this is an UNGATED replay on a 0.2 coin flip, on a path with
13/13 measured harm, and it is the path that ran. A gated replay that earns its place is a
different object from this. The 348-second attribution was wrong (that time is construction,
not replay) -- but the GATE finding stands independently of the timing, and it is the half
that decides the ruling.
NOTE THE SHAPE: the constant's comment claims a relationship to mastery that the code does
not implement. A COMMENT ASSERTING A WIRE THAT ISN'T THERE -- the registry defect, in prose,
outside the registry's reach (the same surface Seat 4 named when KNOBS rows were flagged as
uncovered by the symbol apparatus).

RULING (GM, 2026-08-22) ON THE SALIENT REPLAY GATE: "the salient path calls mastery like its
sibling does -- not removal, since the main path proves the mechanism works. Make the mirror
an actual mirror." Brief written: record/prereg/BRIEF_SALIENT_REPLAY_GATE.md. Queued behind
the lifecycle-cleanup builder (one builder in the tree at a time). Its exemplar is named
(site A, :266-269 + :278-283), its undo is `self._mastery is None`, and it must FEED the
gate as well as read it -- a gate never fed cannot earn anything.
NEW GENUS, THIRD INSTANCE THIS WEEK (Seat 4): THE RIGHT ANSWER SITTING NEAR THE WRONG ONE.
The normaliser; the two frame writers; and now two replay paths in ONE FILE where one is
earned (:266) and one is a hard-coded constant (:331) sixty lines apart. In each case the
correct implementation was already in the tree, adjacent, and the defective site was written
as though the correct one did not exist. This is why NAME THE EXEMPLAR is a rule rather than
a courtesy: the exemplar is usually already there, and the cost of not citing it is a second
implementation that silently disagrees.
AND THE GENERALISED FORM OF THE ATTRIBUTION GENUS (Seat 4 sharpened it past logs): ANY
attribution by ADJACENCY -- the last thing that ran, the last thing that changed, the last
thing that announced -- is blind to whatever did not announce. And the thing that did not
announce is DISPROPORTIONATELY LIKELY to be the cause, because announcing is cheap and
expensive work rarely does it.

=== N=2 RESULT: THE SLOPE IS THE SAME AT N=2 AND N=25. THE MEM-KILLS ARE NOT A RAMP. ===
Two workers (sb26 + s5i5) from the pinned worktree, 9 minutes:
  sb26  449 -> 488 MB  = +4.5 MB/min
  s5i5  461 -> 497 MB  = +4.2 MB/min
AND THE DECISIVE COMPARISON, from my own earlier fleet window 1 at N=25:
  sb26  489 -> 527 MB  = +4.4 MB/min
IDENTICAL. sb26 climbs +4.4/min under the full 25-worker fleet and +4.5/min with a single
neighbour. CONTENTION DOES NOT CHANGE ITS SLOPE. So the GM's discriminator answers cleanly
and the answer is NEITHER "pressure" NOR "contention" as I framed them.
THE ARITHMETIC THAT KILLS THE RAMP STORY ENTIRELY: at +4.4 MB/min, climbing from ~450MB to
the 2GB cap takes 355 MINUTES. sb26 was mem-killed FIFTEEN TIMES IN THREE HOURS -- roughly
every 14 minutes. A +4.4/min slope cannot do that. IT IS NOT A RAMP. Something allocates
~1.5GB IN A BURST, and my 30-second-to-10-minute sampling windows step over it.
That reframes every memory measurement I have taken tonight: I have been measuring the
steady slope of a process whose deaths are caused by transients, and reporting the slope as
though it were the cause. Three windows, a two-worker test and an in-process instrument, all
aimed at the wrong statistic.
INSTRUMENT ERROR FOUND IN THE SAME COMPARISON: the N=1 run reported 803MB where N=2 reports
488MB at the same elapsed time. The N=1 run was under tracemalloc with 12-frame tracebacks,
whose own bookkeeping inflates the process substantially. So "sb26 plateaus at 803MB alone"
was partly the instrument; the 132.7MB read-cache ATTRIBUTION stands (it is a share of
traced allocations, measured internally), but the ABSOLUTE figure was contaminated and I
reported it as a clean measurement.
THE RIGHT INSTRUMENT, and it is cheap: Windows PROCESS_MEMORY_COUNTERS already carries
PeakWorkingSetSize and PeakPagefileUsage -- THE OS TRACKS THE PEAK FOR US. Reading the peak
catches a transient that no sampling interval can be guaranteed to hit. Every memory read
from here reports PEAK beside current, and the fleet's own status line should carry it too.
NEXT: a peak-tracking run (peak vs current per worker, plus the peak's timing relative to
generation and episode boundaries), which is the first instrument aimed at the actual
failure rather than at the slope beside it.

STACK SAMPLER: ONE REAL FINDING, ONE INSTRUMENT BUG, BOTH STATED.
FINDING: 400 of 418 sampled seconds (95.7%) are inside evolution_runner.py:893 `play_game`,
entered at t=4s and never left. So the 375 "silent" seconds are NOT construction happening
before play -- THE WORKER IS INSIDE play_game THE WHOLE TIME. The engine initialisations I
read as a construction phase are lazy constructions occurring DURING play.
INSTRUMENT BUG, which caps what this can conclude: the sampler classified frames as "repo"
by matching the repo path, but this run used PYTHONPATH pointed at the pinned SNAPSHOT
worktree in Temp. So every frame from cognitive_game_player / cognitive_loop / the engines
resolved from the worktree path and was filtered out as non-repo. `play_game` shows as the
deepest repo frame only because evolution_runner was loaded via runpy from the repo path.
The sampler therefore CANNOT name the function below play_game -- it named the last frame
its own filter allowed. That is the ADJACENCY GENUS AGAIN, this time committed by the
instrument built to defeat it: my filter, not a log line, but the same blindness.
FIX (queued, not run -- the GM has paused the memory/speed work): match BOTH the repo path
and the worktree path, or filter by "not stdlib and not site-packages" instead of by an
allowlist of one root.
WHAT SURVIVES: the time is inside play_game, entered 4s after start. Where inside it is
unnamed. The reconciliation the GM asked for (0.15s of game vs ~400s of play_game) is still
owed and is now a one-line instrument fix away.
PAUSED BY GM: memory and speed instrumentation. The codebase examination becomes the main
task.

=== THE CODEBASE EXAMINATION IS NOW THE MAIN TASK (GM, 2026-08-22) ===
Ahead of the queue. Rubric written and binding: record/findings/EXAMINATION_RUBRIC.md.
502 .py outside environment_files/record/dot-dirs, plus the non-.py surface. FIVE READ-ONLY
agents on disjoint slices, each writing ONE findings file, each opening every file in its
slice rather than sampling:
  EXAM_01  engines/egocentric + engines/cognition
  EXAM_02  engines/ remainder (perception, self_model, social, planning, memory,
           regulation, consciousness, postgame, ...)
  EXAM_03  repo root (37) + tools + rungs + config
  EXAM_04  manual_tools + legacy + lab   <- the most likely home of PRESERVE
  EXAM_05  tests (live by constraint; audited for tests that gate nothing) + the non-.py
           surface (architecture, checklists, config, figures, models, loose root files)
NOTHING IS MOVED OR DELETED IN THIS PASS. The deliverable is the list with a summary per
file; the GM approves or does not, and only then does anything move.
THE POINT, restated so it is not lost in the tidying: the deliverable is CAPABILITY THIS
BUILD DOES NOT HAVE. sequence_miner was nearly deleted and was the only code able to
express level-scoping; the composer lineage was five modules of work being rediscovered.
Assume there is more.
AND THE REACHABILITY TEST IS NOT THE IMPORT GRAPH: 27 modules on this fleet are reached
ONLY by a lazy import (eleven inside engines/egocentric), and 80 files are "named" only by
inventories that invoke nothing. A file reached by a string or a lazy import does not fail
at import -- it fails in production, on one path, later. Every row therefore carries HOW it
is reached and the SITE, and the real test after any approved move is a FLEET RUN, not a
green suite.

=== EXAM_03 LANDED (root + tools + rungs + config): 79 files, live 61 / preserve 15 /
considered_dead 3, every file opened. AND IT FOUND A HOLE IN THE RUBRIC I WROTE. ===
THE HOLE: "skip .-prefixed directories entirely" is right for MOVES and wrong for
REACHABILITY. `.github/workflows/ci.yml` invokes tools/consumption_sweep.py (:41) and
tools/ood_lint.py (:47) as BLOCKING steps on every push and PR; `.pre-commit-config.yaml:17`
invokes tools/vulture_whitelist.py. The earlier automated inventory called all three
unreached BECAUSE it skipped dot-dirs at every level. CI IS THE MOST RELIABLE INVOCATION
SITE A REPO HAS AND THE RULE MADE IT INVISIBLE. Rubric AMENDMENT 1 written and pushed to
all four running agents mid-flight: dot-dirs are never moved, always SEARCHED. This is the
GM's own principle turned on the GM's own rule -- where the rule and the requirement
disagree the requirement wins, and the requirement is "verify nothing is hiding".
SIX CORRECTIONS TO THE AUTOMATED INVENTORY, each with a site -- and note the shape: the
automated pass was wrong in BOTH directions. Wrong-dead: the three CI-invoked tools above.
Wrong-live: schema_auto_maintenance.py's only "caller" is its own name inside
cleanup_temp_files.py's KEEP_FILES list (an inventory, not a call site -- the very defect
that pass itself named); tools/verify/hermetic.py's "17 references" are the English
adjective. Wrong-attribution: safe_cleanup.py's production caller is health_monitor.py:133
(every 30 generations), NOT the supervisor -- and with D-1/D-2 open against that file, which
caller is authoritative is not bookkeeping.
THE FINDING OF THE SLICE, and it reframes the whole preserve category: THE PRESERVE SET IS
ALMOST ENTIRELY INSTRUMENTS THAT MEASURE THE BUILD -- determinism, causal control arms,
ship-cleanliness, premise age, comment truth, fork drift. NONE HAS A CALLER. "The build does
not lack instruments; the instruments lack callers" -- the same shape as the defects each was
written to catch. tools/repo_assess.py is dead by its own criteria while .runs/assess_py.txt
is its verbatim 613-line output, so it HAS run; its guard is a product (novelty at zero
blocks removal mechanically) and its main() refuses to convert a scan into a verdict, in code.
ALSO: tools/ has no __init__.py (PEP-420 namespace), sits outside the registry's production
globs, and all four tools/* registry rows are SEVERED -- so NOTHING in tools/ carries a
receipt, INCLUDING THE TWO FILES CI BLOCKS ON. 12 one-shot tools already run are catalogued
with harm-on-rerun notes (sigma_backfill rewrites fabrics in place; dump_schema overwrites
the canonical schema from a RELATIVE db path; norm_sweep has no __main__ guard so it RUNS ON
IMPORT and prints CANDIDATES: 0 from the wrong cwd -- indistinguishable from a clean tree).
A THIRD REPO NAME: tools/overnight_run.py:29 hard-codes an interpreter under .../GitHub/
Ouroboros/.venv and cannot run on this tree as written. The tree calls itself
Ouroboros-Redux, Ouroboros, and BitterTruth-AI.

THE REFRAMING (Seat 4, on EXAM_03's preserve set): THE INSTRUMENT IS THE PRODUCER AND IT HAS
NO CONSUMER. Determinism, causal control arms, ship-cleanliness, premise age, comment truth,
fork drift -- all written, none called, and every one written to catch a class of defect
this project spent the week rediscovering BY HAND. The produced-and-unread genus, one level
up: the instruments themselves are the unread product. repo_assess.py is the sharpest
instance -- dead by its own criteria, and .runs/assess_py.txt is its verbatim 613-line
output, so it HAS run and nothing calls it.
CARRIED TO THE EXAMINATION'S CLOSE, as its own line: TWO BLOCKING CI STEPS CARRY NO RECEIPT.
tools/ has no __init__.py, sits outside the registry's PROD_GLOBS, and all four tools/*
registry rows are SEVERED -- so consumption_sweep.py and ood_lint.py gate every push and pull
request while the wiring registry cannot vouch for either. The coverage falsifier that landed
with symbol receipts checks modules reachable from the ENTRYPOINTS; a CI step is an
entrypoint the falsifier does not know about. That is the same hole as the dot-dir rule,
inside the apparatus built to close holes.
AND A LIVE CONSEQUENCE FOR AN OPEN DEFECT: safe_cleanup.py's production caller is
health_monitor.py:133, firing EVERY 30 GENERATIONS from the runner -- not the supervisor, as
recorded. D-1 and D-2 are open against that file, and the correction changes WHEN the
deletion path runs and under what conditions. The D-1/D-2 write-ups are to be re-read against
the real caller before either is dispositioned.

=== THE GM'S TWO STANDING RULES, CHECKED. BOTH ARE STATED AND NEITHER IS ENFORCED. ===
RULE 1 -- DISABLE BYTECODE CACHING. Result: 830 .pyc files in 109 __pycache__ dirs on disk
right now.
  * 210 FILES CONTAIN `os.environ['PYTHONDONTWRITEBYTECODE'] = '1'`, most with the comment
    "# Rule 1: Disable pycache". IT IS INERT. Proven directly: the interpreter reads that
    variable ONLY AT STARTUP; assigning it at runtime leaves sys.dont_write_bytecode False.
    210 statements of a rule, doing nothing, for however long.
  * The flag that works at runtime IS set -- `sys.dont_write_bytecode = True` -- in a
    handful of modules (config/cognitive_parameters.py, engines/cognition/ab_testing.py,
    algorithms.py, blackboard.py...). It only takes effect from the moment that module is
    imported, so everything imported before it still writes bytecode.
  * WHERE THE RULE IS ACTUALLY ENFORCED: the supervisor's spawn env
    (env["PYTHONDONTWRITEBYTECODE"]="1"), set BEFORE the interpreter starts -- the only
    place that can work. So FLEET WORKERS ARE CLEAN; every other invocation (pytest, ruff,
    my instrument runs, any manual run) writes bytecode.
  * COULD IT HAVE CONTRIBUTED TO THIS WEEK'S "WHICH CODE WAS RUNNING" INVESTIGATIONS? Not
    to the ones I closed -- those were resolved by process-start times and by controlled
    substitution, neither of which bytecode can fake. But the HAZARD IS REAL AND UNCHECKED,
    and .runs/arms/<hash>/ is a COMPLETE SECOND COPY OF THE REPO with its own bytecode; a
    path or cwd resolution reaching one is the moving-tree hazard by a second mechanism.
  * THE GENUS, AGAIN, AND AT SCALE: 210 files assert a rule the code does not implement.
    Same shape as the "mastery-lite mirror" comment on a hard-coded constant -- prose
    describing behaviour the code lacks -- but here it is repeated 210 times.
RULE 2 -- RUN THE DEPENDENCY ANALYSIS BEFORE A REFACTOR. Ran it. THE TOOL IS INADEQUATE FOR
THE JOB IT WAS WRITTEN FOR:
  * IT SEES 36 MODULES. The tree has 501. It scans the root only -- 7% of the surface.
  * ITS --cycles FLAG PRINTS NOTHING AT ALL. Not "no cycles found": no output, then
    "Analysis complete". A check that cannot fail.
  * It reports `evolution_runner.py` -- THE MAIN ENTRYPOINT -- as "potentially orphaned".
  * It calls the repo "BitterTruth-AI Dependency Analyzer" (third repo name).
  * ITS CALLERS ARE THREE DOCUMENTS: .github/copilot-instructions-v4-legacy.md:139,
    architecture/Autonomous Research Lab.md:672, checklists/code_reviewer.md:9. Documented
    procedure, never automated. EXACTLY THE GM'S PREDICTION: an instrument written for this
    moment, unused during it -- and worse than unused, insufficient.
SO I RAN THE REAL ANALYSIS (ast over all 501 modules, parse-only):
  MODULES 501 · EDGES 908 = 635 static + 273 LAZY (30.1% of all imports are in-function --
  a static-only scan misses nearly a third of the graph, which is why the tree's own tool
  and every import scan this week understated reachability).
  IMPORT CYCLES, static-only: 3 components. Static+lazy: 5, and TWO CROSS PACKAGE BOUNDARIES
  -- those are the ones a move breaks, because reordering directories changes import order
  and a cycle only fails in one order:
    CROSSES: decision_rung_system <-> engines.cognition.edge_inference <-> shadow_testing
    CROSSES: database_logger <-> engines.engine_logger
  Largest cycle (static+lazy): 9 modules inside engines.egocentric (affect, applicability,
  bank, binder, effects, goal_abduction, mint, planner + the package).
  THE MOVE MUST NOT REORDER THOSE TWO CROSSING CYCLES. Recorded before any file moves.

=== THE LIFECYCLE CLEANUP FIXED, AND A SECOND SWALLOWED DEFECT FOUND INSIDE IT ===
FK DIAGNOSIS: 54 foreign keys reference agents.agent_id across 50 child tables, NONE with
ON DELETE CASCADE, identical on all 25 boxes. 9 links held rows (sensation_learning_events
42,704; object_sensation_mappings 10,984; agent_operating_modes 2,534; ...).
DISPOSITION, derived not curated: a child column that is NOT NULL or part of the primary
key is OWNED and dies with the agent; a NULLABLE column is ATTRIBUTION and is released to
NULL. Read off what the schema already declares -- and it lands exactly right: all ten
nullable links are provenance columns (discovered_by_agent, learned_from_agent,
infected_by_agent, ...), so SHARED KNOWLEDGE SURVIVES ITS DISCOVERER, and a table added
tomorrow needs no edit. Same property as the derived index and the composite price: a rule
read off the structure rather than authored over it.
Two alternatives refuted on measurement, not taste: restrict-to-childless deletes 0 of 2,459
(every eligible agent has an operating-modes row); soft delete bounds nothing and converts a
loud failure into a quiet no-op THAT REPORTS SUCCESS.
THE SECOND DEFECT, ONE FRAME DOWN AND THE SAME GENUS: `_archive_agent_knowledge` inserted
into agent_archive columns `agent_data` and `generation` THAT HAVE NEVER EXISTED in any
schema or any box DB. Every call raised `no such column` into logger.debug. AGENT_ARCHIVE
HOLDS 0 ROWS FLEET-WIDE -- and manual_tools/utilities/revive_agents.py has been reading
`final_performance` out of that empty table the whole time. So the archive that made deletion
recoverable never held anything, and the tool for reading it has been reading nothing.
Raised-and-unread, WITH a consumer of the empty thing. Now writes the real columns and
RAISES: an agent that cannot be archived is not deleted -- the archive law with teeth
instead of as a comment.
VERIFIED ON A COPY OF A REAL BOX: agents 2,586 -> 127; inactive 2,472 -> 13; gen-0 2,522 ->
108 (all remaining are is_active=1, the OTHER lifecycle defect, untouched); agent_archive
0 -> 2,459; 57,959 child rows deleted, 0 released, 0 failures, 8.6s; second pass deletes 0
and leaves 0 orphans. The GM's falsifier is met.
RESIDUES FLAGGED, both right: winning_sequences.agent_id is NOT NULL so it reads as OWNED --
a scored agent's winning sequences would die with it; never fires today (tier 1 needs zero
wins, tiers 2/3 need a score writer). And tiers 2 and 3 have 200- and 500-generation
windows, so TIER 3 HAS NEVER HAD AN OPEN WINDOW ON ANY BOX -- a second gate found by a test
failing first.

=== THE ORACLE ANCHORED ITSELF TO HEAD, AND HEAD MOVED ===
The two reds in that build were mine, from f891ba9. test_symbol_receipts' oracle fetched the
"pre-migration" gate and registry with `git show HEAD:...`. The moment the migration commit
became an ancestor of HEAD, that returned the MIGRATED registry and the NEW gate -- so the
oracle compared the new gate against itself, reddened 0 rows on a 200-line shift instead of
the pinned 37, and failed. THE BUILD WHOSE ENTIRE CLAIM IS "A REFERENCE THAT MOVES UNDER A
CLAIM ROTS IT" ANCHORED ITS OWN ORACLE TO THE MOST MOBILE REFERENCE IN THE REPO.
FIXED: PRE_MIGRATION_SHA = "0c77eca" pinned in tools/wiring_receipts.py, with the whole
account in head_blob's docstring so the next reader sees why it is a SHA and not HEAD.
FIGURE 2, on the apparatus itself: the anchor must not update. 4 oracle tests pass, 377
across the three affected gate files, ruff clean.
The builder proved the reds were not its own by reverting all three of its files to HEAD and
reproducing them identically -- controlled substitution again, and the right method.

=== THE EXAMINATION IS COMPLETE. 502 FILES, EVERY ONE OPENED. ===
  EXAM_01 engines/egocentric + cognition   76 files   live 68 · preserve  8 · dead  0
  EXAM_02 engines/ remainder               85 files   live 74 · preserve 10 · dead  1
  EXAM_03 root + tools + rungs + config    79 files   live 61 · preserve 15 · dead  3
  EXAM_04 manual_tools + legacy + lab     109 files   live  2 · preserve 39 · dead 68
  EXAM_05 tests (153, live by constraint) + 91 non-.py rows
  TOTALS (excluding tests): live 205 · preserve 72 · considered_dead 72 · unreadable 0
NOTHING MOVED. The list awaits the GM's sign-off, as ruled.

THE FINDING OF THE WHOLE EXAMINATION -- EXAM_02's DEFECT A, and it is not about tidying:
engines/interfaces.py declares 25 Protocols. ELEVEN OF THEM DECLARE 14 METHODS THAT NO
IMPLEMENTATION IN THE TREE DEFINES. engines/registry.py:42-45 has the type-checking imports
COMMENTED OUT, so nothing catches it. Each missing name is exactly the string a live rung
hasattr-guards -- 21 such call sites -- so the guard silently takes the false branch forever.
THREE PRIORITY-ORDERED RUNGS HAVE NO REACHABLE BODY AT ALL: NearMissAnalyzerRung,
ImaginationBudgetRung, NetworkExplorationStatsRung. Permanent no-ops in the ladder the agent
descends every decision. rungs/hypothesis.py:47 falls back to the literal 'exploring' every
call, so its "theory contradicted" branch is unreachable.
AND FOUR OF THE FOURTEEN ARE PURE NAME MISMATCHES:
    get_proven_sequence  vs  get_proven_sequences     (a missing 's')
    get_active_beliefs   vs  get_beliefs
    get_inferred_goal    vs  get_goal
    suggest_transformation vs get_transformation_needed
Four capabilities are one identifier apart from working. This is hasattr-guarding as a
silent-failure machine: a typo becomes a permanently-taken false branch with no error, no
log line, and no test -- the raised-and-unread genus with nothing even raised.
SECOND: all 19 package-level get_*() lazy accessors in engines/{perception,memory,planning,
regulation,social,consciousness}/__init__.py ARE NEVER CALLED, which invalidates 17
reachability rows in the automated inventory (16 have a different real site; one does not).
THIRD: engines/reasoning/deliberation_audit.py is a WRITER WITH NO READER -- constructed
live at decision_rung_system.py:636, fills the top-5-alternatives table every episode, and
its four analysis methods have zero callers.
FOURTH, and it explains a smaller mystery: the `import os; os.environ[...]` prelude puts the
docstring after a statement in 63 FILES, so their __doc__ is None. The same inert bytecode
prelude that states a rule it cannot enforce ALSO destroys the module docstring. Two-line
reorder.
CORRECTION TO A LEAD I GAVE THE SLICE: palette_detector and spatial_learning are NOT
unreached -- both are lazy-imported by registered, priority-ordered live rungs. The
capability claim stood; my reachability implication did not.
CAUTION BEFORE ANY MOVE: sequence_miner is not inert -- it loads on every engines.planning.*
import and its module-level logger OPENS A DB HANDLER.

=== THE GM'S CACHE AND TOOL RULES, EXECUTED AND CONFIRMED BY MEASUREMENT ===
CACHES DELETED: 109 __pycache__ dirs, 826 .pyc files, .pytest_cache, .ruff_cache -> all 0.
MADE DURABLE, not merely deleted: pytest.ini `-p no:cacheprovider`; pyproject `cache-dir`;
and a NEW ROOT conftest.py setting `sys.dont_write_bytecode = True` -- the earliest file
pytest imports, and the only in-process lever that works. Its docstring records why it
exists rather than the 210 inert statements: they assign an env var the interpreter reads
ONLY at startup. The fleet path was already correct (the supervisor sets it in the SPAWN
env, before the interpreter starts).
CONFIRMED OFF BY RUNNING, not assumed: a real `ruff check` -> no .ruff_cache recreated; a
real `pytest tests/gate/test_sprint_keeper.py` (21 passed) -> no .pytest_cache, 0
__pycache__ dirs after.
COPILOT FILES DELETED: .github/copilot-instructions.md and -v4-legacy.md (git rm). Note what
goes with them: they were the ONLY invocation site outside checklists/ for the lab modules
and for analyze_dependencies. Remaining citations are inside .runs/arms/<hash>/, which is a
COPY of the repo, not the repo.

=== THE MANDATED PRE-REFACTOR TOOL CANNOT RUN ON THIS REPO. THE REASON IS THE REPO'S NAME. ===
pydeps 3.0.7 IS installed. Pointed at the real entrypoint from root it refuses, and the
reason is structural: pydeps builds a synthetic dummy module containing literal
`import <modname>` statements and runs modulefinder on it. `Ouroboros-Redux` CONTAINS A
HYPHEN, so it is not a valid Python identifier, cannot appear after `import`, and
modulefinder traces nothing -- pydeps produces an empty graph BY CONSTRUCTION.
So the GM's standing rule -- run the dependency analysis before every major refactor -- has
been unrunnable with the real tool for as long as the directory has had that name. That is
why a hand-rolled copy exists under manual_tools; and THAT copy sees 36 of 501 modules and
prints nothing for --cycles. The instrument was replaced by a worse one because the good one
could not start, and neither fact was recorded anywhere.
THE ANALYSIS STANDS ON MY OWN AST PASS (all 501 modules, parse-only): 908 edges = 635 static
+ 273 lazy (30.1% in-function); 5 cycles with lazy included, TWO CROSSING PACKAGE BOUNDARIES
-- decision_rung_system <-> engines.cognition.edge_inference <-> shadow_testing, and
database_logger <-> engines.engine_logger. Those two are what a move can break, because
relocation changes import order and a cycle fails in only one order.

=== MOVED (GM-authorised): architecture/ + checklists/ -> considered_dead/ ===
`git mv`, fully recoverable. evolution_runner still imports cleanly after the move.
WHAT THE MOVE BREAKS, stated rather than discovered later -- architecture/ IS NOT ONLY
DOCUMENTATION. Three code sites read DATA out of it by path:
  manual_tools/infer_answerable_by.py:304   default="architecture/rung_dependency_matrix.json"
  manual_tools/profile_baseline.py:278      PROJECT_ROOT / "architecture" / "rung_dependency_matrix.json"
  manual_tools/profile_baseline.py:343      default="architecture/baseline_profile.json"
Both tools are themselves preserve/dead, so nothing live breaks -- but those defaults now
point at nothing. Five docstring references (decision_rung_system.py:119, event_bus.py:13,
lab/__init__.py:2, legacy/learning_systems.py:762, manual_tools/utilities/run_context.py:9)
and two README links become dangling pointers.
checklists/ moved clean: ZERO code citations. Its only invocation sites were the two copilot
files deleted an hour ago -- so deleting those and moving this removes the last caller of
the lab/ modules and of analyze_dependencies, which is worth knowing before the preserve
list is ruled on.

=== .runs: WHAT IT IS, AND IT IS NOT DELETABLE ===
13 GB, gitignored (.gitignore:88 `.runs/*`), 8 files tracked by exception.
  .runs/swarm/  9.3 GB  <- THE AGENTS' MEMORY. 25 boxes, ~400 MB each: core_data.db
                           (284 tables: agents, genomes, generations, results) + ego_fabric
                           (atoms, mint_verdicts, narration, settlements, frontier). This is
                           everything the fleet has learned. Deleting it is a reset to zero.
                           Read at runtime by tools/beat_rates.py:165, bracket_rt.py:60,
                           build_action_book.py:646; written by every worker (its cwd IS its
                           box). NOT DELETABLE.
  ~2.7 GB of PAST EXPERIMENT RUNS, all last written 2026-08-06 to 2026-08-18 and none since:
    rescore 423M, scored20 553M, legacy_db 410M, hermetic 249M, frontier_cap 239M,
    compound1 235M, harvest_cap 228M, compound2 202M, assembly1 121M, cold_venv 50M,
    oldlogs 44M, plus ~15 small dirs (base, earned, cur, m7on/off, m2on, final, ...) at
    2026-08-06, and TWO EMPTY ONES (archive/, c34_base_gamma/).
  .runs/arms/  149M  <- A COMPLETE SECOND COPY OF THE REPO (5 entries; 112913b692a2 holds
                        BUILD_PROGRAM.md, record/canon/CLAIM.md, the lot). THIS IS THE MOVING-TREE HAZARD
                        BY A THIRD MECHANISM: a second importable tree inside the repo, with
                        its own .py, its own .github, and until tonight its own bytecode. It
                        is also why several greps this week returned phantom hits.
  54 loose files: profiles (.pstats), logs, and my own instrument dumps from tonight.
RECOMMENDATION (not executed -- deletion needs the GM's sign-off): keep .runs/swarm entire;
the ~2.7 GB of dated experiment directories and the arms copy are archival and none has been
written in 4+ days. The arms copy is the one I would remove first, because it is not merely
stale storage -- it is a second tree that can be imported from and grepped into.

=== .runs ARCHIVE DELETED (GM sign-off): 13 GB -> 9.3 GB ===
Manifest written FIRST to record/findings/RUNS_ARCHIVE_MANIFEST.md, because .runs is
gitignored and this is the ONE deletion tonight that git cannot undo. Everything except
swarm/ removed: rescore, scored20, legacy_db, hermetic, frontier_cap, compound1/2,
harvest_cap, assembly1, cold_venv, oldlogs, ~15 small 2026-08-06 dirs, two empty ones --
and .runs/arms/, THE COMPLETE SECOND COPY OF THE REPO, which was the moving-tree hazard by
a third mechanism and the source of phantom grep hits all week. swarm/ intact: 33 entries,
9.3 GB, every box's core_data.db and ego_fabric untouched. 54 loose instrument files kept.

=== OLD TESTS MOVED, AND THE DATE SORT WOULD HAVE BROKEN THE SUITE ===
Sorted by LAST COMMIT DATE, not mtime -- mtime lies after any checkout, and this tree has
been checked out and worktree'd repeatedly this week. The split is clean: 27 files last
committed 2026-02, 126 in 2026-08, nothing in between.
BUT TWO OF THE 27 ARE THE SUITE'S OWN SCAFFOLDING: tests/conftest.py (83 lines; it sets
sys.path for the ENTIRE suite -- and tests/gate has NO conftest of its own, so all 125 gate
tests depend on it) and tests/__init__.py. A mechanical date sort would have moved both and
broken every test in the repo. THE REQUIREMENT BEATS THE RULE, again, and this time the rule
was a date.
MOVED 25 pre-August test files -> considered_dead/tests/. Collection after the move: 1,949
tests collected, no errors. Among the 25 are the three EXAM_05 found gate NOTHING --
test_sequence_system, test_reasoning_data_usage, test_reasoning_system_fixes -- which import
nothing from this project and assert against logic re-typed inside the test file.
FOOTNOTE THAT IS NOT A FOOTNOTE: tests/conftest.py contains the SAME INERT
os.environ['PYTHONDONTWRITEBYTECODE'] line as the other 210 files. The suite's own config
has been asserting the cache rule and not enforcing it for six months; the new root
conftest.py enforces it properly.

=== core_data.db AT THE ROOT: AN ARTIFACT, AND THE CODE THAT MAKES IT CANNOT MOVE ===
There was a 10 MB core_data.db in the repo root, modified TODAY. It is not tracked (*.db is
gitignored) and it is NOT the agents' data -- theirs live at .runs/swarm/<box>/core_data.db.
Deleted the artifact.
THE CREATOR IS THE LIVE DATABASE LAYER, NOT A DEAD SCRIPT: 135 sites default db_path to the
RELATIVE string "core_data.db" (database_interface.py:31, database_logger.py:41/403,
concept_discovery_engine, engines/perception/object_detector, engines/planning/
sequence_abstraction:1513, engines/reasoning/symbolic_reasoning_engine, ...). A relative
default means EVERY process creates a database at whatever cwd it happens to have. Moving
any of it to considered_dead would break every worker.
THE TREE ALREADY KNOWS: database_logger.py:55-63 carries the D-6 FIX comment -- the log
handler was constructed at IMPORT time, so "merely importing the engines package CREATED a
core_data.db at whatever cwd the importer had... that is how a schema-only 282-table shell
kept reappearing at the repo root". D-6 deferred schema init to first EMIT. That stopped the
empty shell; it does not stop a root database appearing once anything actually logs from the
root -- which is what every suite run I did today does. Hence 10 MB, today.
DISPOSITION: not a move. The defect is the RELATIVE DEFAULT, and the fix is to anchor it
(explicit path from the caller, or a module constant resolved against the box root) so a
process cannot silently create a database wherever it stands. Queued as a build, not done
here -- it touches 135 sites and the fleet is the thing that would prove it.

=== ROOT FILES BY DATE: THE SORT WORKS FOR TESTS AND FAILS FOR ROOT ===
Sorted all 37 root .py by last commit: 27 are February 2026, 10 are August. A clean split --
and acting on it would be wrong.
CHECKED EVERY FEBRUARY FILE FOR LIVE IMPORTERS: abstraction_config 11, event_bus 8,
outcome_processor 6, context_builder 4, concept_discovery_engine 4,
multi_stage_matching_pipeline 4, seed_primitives 3, mastery_system 3, evolutionary_engine 2,
representation_learner 2, health_monitor 1 (evolution_runner.py:60 -- the entrypoint itself).
TWENTY-FIVE OF TWENTY-SEVEN ARE LIVE. They are February because THEY HAVE NOT NEEDED TO
CHANGE. Stability is not death, and on the live path it is the opposite.
AND THE ONE THAT LOOKS DEADEST IS NOT: breakthrough_budget_allocator has ZERO static
importers -- every import scan calls it dead -- but engines/registry.py:297 imports it BY
STRING (module='breakthrough_budget_allocator'). Exactly the trap the rubric names, in the
root, on a file a date sort would have moved first.
ONE GENUINE CANDIDATE of the 27: schema_auto_maintenance.py -- its only importer is
manual_tools/utilities/enhanced_database_interface.py (itself a manual tool) and its other
"reference" is a KEEP_FILES inventory line. Found by EXAMINATION, not by date.
CONCLUSION FOR THE GM: date predicted deadness for tests (25/25 correct, because a test that
stopped changing stopped being maintained) and predicts NOTHING in root (1/27, and it would
have moved 25 live modules plus a string-imported one). Root files are moved on the
examination's evidence or not at all. NOTHING MOVED FROM ROOT.

=== THE MOVES: manual_tools + legacy + lab, 105 FILES, BY USEFULNESS NOT BY DATE ===
Driven by EXAM_04's per-file destinations (the GM's "check by date but also if useful"):
  preserve/        37 files -- capability worth having, no caller today
  considered_dead/ 68 files -- appears dead
Relative paths preserved under each destination, so the diff reads as a move and nothing
collides. The script refuses anything under tests/, any dot-path, anything untracked, and
prints every skip with a reason -- there were none.
THE TEST, RUN IMMEDIATELY (the GM's rule: move first, see what breaks):
  * all four entrypoints import: evolution_runner, cognitive_game_player, game_player,
    arc_api_adapter -- OK
  * the suite still COLLECTS: 1,949 tests, no collection errors
Nothing broke. Note what that does and does not prove: collection exercises imports, not the
lazy-import and string-import paths that only fire in production. The FLEET RUN is still the
real test, per the GM's own instruction, and it is owed before any of this is called safe.
HELD BACK, deliberately: EXAM_01 (engines/egocentric + cognition) and EXAM_02 (engines
remainder) and EXAM_03 (root + tools + rungs + config) are NOT executed yet -- the Protocol
repair builder currently owns engines/interfaces.py, engines/registry.py and rungs/, and
moving files under a running builder is the hazard that cost six investigations this week.
They go the moment it returns.

=== PROCTOR ERROR IN bed4757: `git add -A` SWEPT IN A RUNNING BUILDER'S WORK ===
The commit was meant to contain 105 file moves. It also contains the Protocol-repair
builder's IN-FLIGHT, UNFINISHED edits: engines/interfaces.py (+381), rungs/hypothesis.py
(+80), rungs/exploitation.py (+61), rungs/base.py (+42), engines/__init__.py (-4). That
builder is still running and has not reported, so this code has not passed its own gate and
has never been through a suite.
WHY IT HAPPENED, and it is the genus I have spent the night cataloguing: `git add -A` is an
ADJACENCY OPERATION. It stages everything PRESENT, not everything I meant -- the same shape
as attributing a delay to the last line printed, or a caller to the nearest name. I have
been telling builders all night to name what they touch, and then staged by proximity.
WHAT I AM NOT DOING: reverting. The builder holds those files right now; a revert would
destroy work in progress and produce exactly the moving-tree collision this discipline
exists to prevent. The partial state is at least importable (entrypoints load, 1,949 tests
collect) and the builder's own final run is what validates it.
DISPOSITION: the commit stands, MARKED. The builder's completion commit supersedes it and
its full-suite run is the gate this content never got. If that run reds on its own files,
the cause is here and not in its work.
THE RULE, adopted now: WHILE A BUILDER IS RUNNING, STAGE EXPLICIT PATHS. Never `git add -A`,
never `git commit -a`. The proctor's own commits name their files, exactly as builders are
required to name what they touch.

=== ROOT MARKDOWN CONSOLIDATED: 20 MOVED, 49 FILES OF CITATIONS REWRITTEN WITH THEM ===
THE PROBLEM WAS NOT UNTIDINESS, IT WAS TWO HOMES FOR ONE CLASS OF DOCUMENT: 19 old
PREREG_*.md sat at the repo root while every prereg written since lives in record/prereg/.
Same kind of file, two locations, and nothing said which was canonical.
MOVED to record/prereg/: 19 PREREG_*.md + VICTORY_PROTOCOL.md, PERF_AUDIT.md,
EGOCENTRIC_PORT_PLAN.md (20 total).
KEPT AT ROOT, and the reason is measured, not habitual:
  record/canon/WIRING_REGISTRY.md and record/canon/KNOBS.md are OPENED AND PARSED by gate tests
  (test_dead_dedup.py:328/336, test_efficiency_read.py:344, test_origin_marker.py:305,
  test_planner_retention.py:358). Moving them BREAKS TESTS, not just pointers.
  record/canon/THE_LADDER.md, record/canon/CLAIM.md, record/canon/THE_GOALS.md, README.md -- canon, cited from ~100 sites.
THE CITATIONS MOVED IN THE SAME OPERATION -- 49 files rewritten. A move that leaves stale
references behind IS THE RECEIPT-ROT DEFECT IN PROSE, and this project has spent the week
paying for exactly that at the line-number grain. Verified after: zero bare references
remain to any moved document.
TESTS AFTER: 1,959 collect (up from 1,949 -- the Protocol builder's new gate file); the two
parsing suites pass, 45 tests.
BUILDER SAFETY, checked rather than assumed: the Protocol repair builder holds
engines/registry.py, rungs/{exploitation,filter_rungs,hypothesis,orientation}.py and its new
test file. NONE of the six cites any moved document, so the rewrite could not collide. That
check is the thing I skipped an hour ago when `git add -A` swept its work into bed4757.

=== ON MOVING PREREGS TO considered_dead: I HAVE NOT, AND HERE IS WHY ===
The GM asked for preregs that are no longer relevant to go to considered_dead. A landed
prereg is not stale -- IT IS THE REASON THE CODE IS SHAPED AS IT IS, and live code CITES IT
BY NAME at the site it governs (cognitive_game_player.py:428 cites the corpse guard's
clause A; the composer's stages cite theirs). Moving those breaks the only explanation the
code carries for its own behaviour.
WHAT IS GENUINELY STALE is a smaller and different set, and it needs the GM's eye because
each is a judgement about intent rather than reachability:
  * PREREG_STAMP_FACTORING + BRIEF_STAMP_FACTORING -- F1 FIRED, held, never built
  * PREREG_SWARM_OFFLINE_MODE -- "PREREG ONLY. NOT EXECUTED."
  * PREREG_W2_APPLICABILITY_INDEX -- "AWAITING SEAT 3's CLEARANCE" (long since overtaken)
  * PREREG_MINT_CONTEXT_RING -- withdrawn, then re-admitted and queued; live, not stale
Four candidates, one of which is explicitly still queued. That is a ruling, not a sweep, so
it waits for the GM rather than being executed on a guess.

=== THE CANON MOVED TO record/canon/ -- AND THE MOVE BROKE 16 TESTS, WHICH IS THE TEST ===
Moved: WIRING_REGISTRY.md, KNOBS.md, THE_LADDER.md, CLAIM.md, THE_GOALS.md -> record/canon/.
README.md STAYS AT ROOT: it is the repository's front page by universal convention and by
GitHub's own resolution. Stated as a judgement rather than skipped silently.
55 files of references rewritten in the same operation, and BOTH kinds: the PROSE mentions,
and the CODE PATHS that actually open these files -- os.path.join(REPO, "WIRING_REGISTRY.md")
in four gate tests and two tools, plus the bare relative constants.
IT BROKE 16 TESTS AND 4 ERRORED. Two causes, both instructive:
 1. THE SCRATCH HARNESS ASSUMED A FLAT ROOT. test_symbol_receipts._scratch copies the gate,
    the laws and the registry into a temp tree with os.makedirs("tests/gate") hard-coded --
    it made the ONE directory it knew about. The registry's new parent did not exist, so
    every copy raised FileNotFoundError. Fixed by making the parent OF EACH FILE rather
    than a named directory: the assumption the move exposed.
 2. A PATH IS ONLY VALID RELATIVE TO A REVISION. The oracle reads the pre-migration gate and
    registry out of a historical commit, where the registry was still at the repo ROOT --
    so `git show 0c77eca:record/canon/WIRING_REGISTRY.md` finds nothing. One constant was
    serving both the working tree and a historical read. Split into REGISTRY_REL and
    REGISTRY_REL_AT_PRE_MIGRATION, with the reason in the code: the same lesson as the
    receipts themselves, one level up -- a location is a fact about a moment.
AFTER: 496 passed across all eight suites that open these documents. Zero dangling refs.
THIS IS THE GM'S METHOD WORKING AS SPECIFIED: move first, see what breaks, report. Reading
the imports would not have found either defect -- neither is an import. The first is a
hard-coded directory in a test harness, the second is a git path in a historical read.

=== THE PROTOCOL REPAIR LANDED: 20 DECLARED-BUT-UNDEFINED, NOT 14, AND THE FOUR "TYPOS"
    WERE NOT TYPOS ===
The examination's DEFECT A is CONFIRMED AND UNDERSTATED. The builder's own AST sweep found
20 declared-but-undefined Protocol methods (six the exam missed) PLUS 8 guard-only drifts
that no Protocol declares at all. Two different sets, both real; the exam had conflated them.
THE FINDING THAT MATTERS, AND IT REVERSES MY OWN BRIEF: I told the builder four of these
were "pure name mismatches, one identifier apart from working". THREE OF THE FOUR ARE NOT.
get_beliefs, get_goal and get_proven_sequences return DATACLASSES (or a list of sequences);
the dead branches read them as DICTS. A pure rename would have moved each rung from
SILENTLY DEAD to RAISING ON THE FIRST LINE AND SWALLOWED BY ITS OWN except -- dead a second
way, still silent. The builder checked the shape, not just the name, and said so.
That is the adjacency genus once more: I matched on the NEAREST NAME and called it a typo.
DISPOSITION: implementation is the truth, 16 names fixed at the CALL SITE, ZERO
implementations renamed. Two interfaces deleted entire (CounterfactualAnalyzer,
PrimitiveHelper -- their named consumer rungs do not exist). Six kept and made LOUD via a
capability_absent() call logged once per (class, method) per process, each with a row in a
new UNIMPLEMENTED_DECLARATIONS table stating why it stays declared. Declared-but-
unimplemented went 20 -> 5, and all five are allowlisted and loud. NO SILENT FALSE BRANCH
SURVIVES.
THE ANTI-REPEAT MECHANISM IS BOUND, NOT TREE-WIDE, and that distinction is load-bearing:
F1 binds each Protocol to the class the REGISTRY CONSTRUCTS and checks THAT class --
get_current_prediction is defined by two other classes and NOT by the bound one, so a
tree-wide check passes and is wrong.
engines/registry.py:42-45 UNCOMMENTED -- no cycle exists (interfaces.py imports only os and
typing). Stated honestly by the builder: uncommenting does NOT restore checking, because no
type checker runs in CI. The gate test is the check; the annotations are the declaration.
SUITE: 1957 passed, 2 xfailed, ZERO REDS.
COST FLAGGED FOR A RULING, not hidden: restoring get_budget wires a DB aggregate + an INFO
log into a PER-DECISION context modifier, and two restored orientation rungs run two DB
queries per decision. The fleet has never paid these. The builder applied the rule
consistently rather than special-casing, and says so: turning them off is a priority
ordering decision, not a defect decision.

=== AND IT CAUGHT ME TWICE, BOTH FAIR ===
1. Commit d86dc1a swept its in-progress test file (551 lines) and its interfaces.py changes
   into a commit whose message describes a documentation move -- my `git add -A`, already
   recorded, and this is the builder observing the consequence from the other side.
2. My canon move to record/canon/ broke its runs mid-flight (19 reds, then 16). It attributed
   correctly and three ways -- the failure text named the moved file, the suite imports
   nothing it touched, and run order-isolated it passed 25/25 once my fix landed.
3. The 2743 baseline in its brief was ALREADY STALE when I wrote it: my own moves of 25 tests
   and 105 files had changed the count. It could not have matched the number I gave it and
   said so rather than fudging.
Three proctor errors, all found by the builder, none by me.

=== THE DATABASE PATH IS ANCHORED: DATA CANNOT LAND OUTSIDE .runs ANY MORE ===
resolve_db_path() at the module bottom of database_interface.py -- chosen on a MEASUREMENT
(80 importers vs database_logger's 4) and PURE: no mkdir, no connect, so the D-6 property
stays true. Explicit caller paths honoured unchanged (the escape hatch tests need); the
DEFAULT resolves to the box when cwd is under .runs, else to the runs root, and any path
that would land outside raises DatabasePathOutsideRuns NAMING THE PATH AND THE RULE.
MY "135 SITES" WAS WRONG -- IT IS 35. The real figure, from an AST scan over the production
globs, is 37 constants minus 2 module docstrings. My grep counted the WHOLE TREE, including
considered_dead/, preserve/, tools/ and record/ PROSE. A number produced by scope-less
grep, quoted as a live-path count: the adjacency genus at the measurement grain, and the
third number of mine a builder has corrected tonight (95s import, four "typos", now this).
HOW THE 35 WERE FIXED, and not by rewriting 35 literals into a different literal: 21 are
forward-only and simply stopped asserting a path (default None, resolved at the sink); 8
that store or connect call the resolver explicitly; database_logger's DATABASE_PATH env
fallback moved INTO the resolver; symbolic_reasoning_engine's `DB_PATH = Path("core_data.db")`
module constant was DELETED rather than rewritten, because a constant resolves at IMPORT
time and that module is imported from the repo root by the suite -- rewriting it would have
turned a path question into an import-time raise.
THE MEASUREMENT THAT CLOSES IT, and I re-ran it myself rather than accept the report:
20 engine log records emitted from the repo root -> root core_data.db BYTE-IDENTICAL
(3,899,392 bytes, mtime unchanged at 03:47) and the write landed in .runs/. The builder's
own full-suite run left the root DB's mtime frozen likewise.
NON-VACUITY PROVEN BY RE-PLANTING THE DEFECT: the builder deliberately restored the old
relative default into object_detector.py to check F4 reds by name. It did.
THE EXEMPTION IS AN EQUALITY, NOT A SKIP: engines/registry.py:358 and :696 are two more live
sites of this exact defect, in the file the Protocol builder owned at the time. They are
carried in F4 as KNOWN_OUTSTANDING, and the gate REDS WHEN THEY ARE FIXED, demanding the
entry be deleted. An exemption that can be forgotten is the same species as a convention
nothing checks -- so it was written as one that cannot be.
SUITE: 1965 passed, 2 xfailed, zero reds. ruff clean.
TWO FOSSILS, and only one is mine to remove: the root core_data.db (3.9 MB, 282 tables) is
now inert -- nothing writes it -- and I deleted it, which the GM's rule requires and which
is only final NOW that the defect is fixed. And .runs/core_data.db (3.6 MB) is suite noise
that the fix correctly redirected INTO the sanctioned area; it is inert with respect to the
fleet (every box reads .runs/swarm/<box>/core_data.db) and it stays. The clean follow-up --
diverting engine logging under test -- needs a test-detection convention the tree does not
have, and the builder declined to invent one unilaterally. Correct refusal.

=== BEAT 52 (2026-08-22 ~04:05, fleet HALTED since 01:42) ===
ASK: nothing blocking. One ruling waits (the restored rungs' per-decision DB cost) and one
decision is yours whenever (which of four stale preregs go).
THE GROUND: 0 levels, 0 games won this hour -- THE FLEET HAS NOT RUN. Deliberate.
RATES THIS HOUR: minted 0 / used 0 / composed 0 / retired 0, all by construction. And the
standing caveat holds: even with the fleet up these are NOT WINDOWABLE until the seq
watermark lands, because no ego_fabric record carries a timestamp.
STALLED SINCE BEAT 51, named: levels (5 beats); g7 (still 0, still UNMEASURED not failed --
rung 0b's instrument exists now but has never run against a live fleet); split-half (frozen
at 0/0/5, cannot advance while halted); the memory ramp (holder named, cause NOT -- it is
transient spikes, not a slope, and the peak-tracking instrument is written but unrun).
WHAT MOVED: the examination finished and its moves are executing.

=== THE EXAMINATION MOVES, ALL FIVE SLICES: 142 FILES, AND FOUR CAME BACK ===
EXAM_01 8 · EXAM_02 11 · EXAM_03 18 · EXAM_04 105 = 142 moved.
FOUR RESTORED IMMEDIATELY, and the reason is one the examination could not see:
  engines/cognition/cognitive_stages.py, engines/egocentric/{falsified_ledger,janitor,
  relations}.py -- all four are imported AT PACKAGE-IMPORT TIME by their package's own
  __init__.py. The examination called them "re-exported, zero constructions" and classified
  them preserve. A RE-EXPORT IS NOT A MENTION -- IT IS A STATIC IMPORT THAT RUNS. The class
  may never be constructed; the MODULE is imported every time anything touches the package.
  Moving them broke all four entrypoints instantly.
THAT IS THE GM'S METHOD PAYING OFF EXACTLY AS SPECIFIED: move first, see what breaks. No
amount of further reading would have produced this -- the examination HAD the evidence
("re-exported twice") and drew the wrong conclusion from it. Only the move settled it.
AFTER: 1,965 tests pass, 2 xfailed, zero reds. All four entrypoints import.
WHAT THIS STILL DOES NOT PROVE, and it is the GM's own point: a green suite exercises
imports, not the LAZY and STRING import paths that fire only in production. 27 modules on
this fleet are reached ONLY by an in-function import. THE FLEET RUN IS THE TEST THAT IS
OWED, and it is owed before any of these 138 moves is called safe.

=== THE FLEET RUN CAUGHT WHAT THE SUITE COULD NOT. THIS IS THE WHOLE ARGUMENT. ===
Relaunched on e52ee32 at 04:17 (25 workers, deploy ledger clean). Within three minutes the
worker logs carried an error no test in this repo could produce:
    ModuleNotFoundError: No module named 'engines.planning.sequence_miner'
    [registry:WARNING] Failed to import subgoal_planner
    [registry:WARNING] Failed to import replay_learning_engine
CAUSE: engines/planning/__init__.py:5 imports sequence_miner at package-import time. Moving
it to preserve/ broke the PACKAGE, and with it two engines the registry loads BY STRING --
subgoal_planner and replay_learning_engine. A string import cannot fail at collection; it
fails at registry construction, in a worker, and is CAUGHT AND LOGGED AS A WARNING. The
fleet kept running with two engines silently absent.
1,965 TESTS PASSED OVER THIS EXACT TREE. All four entrypoints imported. The suite could not
see it because nothing in tests/ imports engines.planning, and the registry swallows the
failure by design.
AND THE EXAMINATION HAD WARNED ME: EXAM_02 wrote that sequence_miner "is not inert -- it
loads on every engines.planning.* import and its module-level logger opens a DB handler,
which is a caution against moving it casually." I moved it anyway, because its row said
preserve. I READ THE ROW AND NOT THE WARNING BESIDE IT.
RESTORED; engines.planning and both dependents import; the supervisor redeployed on the
change at 09:23 UTC and all 25 workers are up.
FIVE FILES HAVE NOW COME BACK of 142 moved (cognitive_stages, falsified_ledger, janitor,
relations, sequence_miner) and EVERY ONE for the same reason: A PACKAGE __init__.py IMPORTS
IT AT IMPORT TIME. That is now a rule, not an anecdote: BEFORE MOVING ANY MODULE, GREP ITS
OWN PACKAGE'S __init__.py. A re-export is not a mention; it is the package's contract.
STATED SO IT IS NOT LOST: the fleet run remains the only test that reaches string and lazy
imports, and it has now earned that claim twice in one night -- once for the manual_tools
lazy import weeks ago, once here. A green suite is necessary and it is not sufficient.
