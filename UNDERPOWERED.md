# UNDER-POWERED REGISTER — every architecture verdict, with its n
2026-08-18. Isaiah's ruling: *nothing gets thrown out; what changes is the label, not the
status.* A verdict recorded at n=1 **is not wrong; it is unsupported**, and those are
different and both worth keeping.

## THE RULE APPLIED, AND THE ASYMMETRY IS THE USABLE PART
**ELIMINATIONS SURVIVE n=1.** Same depth at a thousandfold throughput kills every
more-time hypothesis, and no amount of repetition resurrects them. A capability shown
ABSENT once is strong.
**EVERYTHING ELSE NEEDS n.** A capability shown PRESENT once is weak. Anything expressed as
a RATE, a MARGIN, or a DISTRIBUTION needs n by construction.
**AND THE SEEDING ECONOMY MAKES THE VARIANCE WORSE THAN ORDINARY NOISE.** An agent with a
lucky early sequence banks it, seeds from it, and is funded to continue; a random advantage
becomes structural within a generation and has a track record by the third. **THE MECHANISM
MEANT TO SELECT FOR CAPABILITY WILL FAITHFULLY SELECT FOR WHATEVER HAPPENED FIRST, AND
NOTHING DISTINGUISHES THE TWO FROM INSIDE.**

---

## THE LIST

### RANK 1 — THE CONTROL ARM: "THE STACK PAYS"
**CLAIM:** the full egocentric stack beats stripped v4 on capability. ar25 19v11, r11l
34v25, sp80 31v0.
**n = 3 GAMES x 12 EPISODES x 2 ARMS** (48 sessions per arm per game).
**POPULATION:** ONLINE, rate-limited, **and contended by my own load** (Amendment 3).
**AS-OF:** 2026-08-18.
**LABEL: UNDER-POWERED FOR THE MARGIN, RE-RUN PENDING.** The 19v11 and 34v25 figures are
MARGINS and need n. **BUT sp80 (31 vs 0) IS NEAR-ELIMINATION SHAPE** — the stripped
comparator completed nothing, which is a capability shown ABSENT and survives thin n far
better than the other two.
**HIGHEST CONSEQUENCE ON THE BOARD:** it is the verdict that resumed the queue.

### RANK 2 — LINK-3 VOCABULARY: "50 PREDICATES WHERE THERE WERE 0"
**n = 6 RECORDS / 3 DISTINCT TRANSITIONS.** Population: swarm boxes, online-earned.
**LABEL: UNDER-POWERED, AND SEPARATELY BLOCKED** by the `post (3,64,64)` normalisation
defect. Two reasons it is unsettled and only one is sample size.
**NOTE the halves differ:** the 0-predicate finding is an ELIMINATION (the vocabulary
cannot express these transitions) and survives n=3. **The 50 is a RATE and does not.**

### RANK 3 — "SELECTIVITY, NOT ACTIVITY"
**CLAIM:** the stripped arm changes MORE frames while completing FEWER levels.
**n = 3 GAMES.** Population: online, contended. **LABEL: UNDER-POWERED, RE-RUN PENDING.**
A margin on three points, and it is the only *mechanism* story the arm produced.

### RANK 4 — OFFLINE THROUGHPUT: 11,782 STEPS/SEC
**n = 2 MEASUREMENTS, 1 GAME (ls20), 1 BOX.** As-of 2026-08-18.
**LABEL: THIN BUT ROBUST** — effect size is ~1,000x against a documented 10 actions/sec cap.
A re-run is cheap and should widen to several games, but no plausible variance closes that
gap.

### SURVIVES AS AN ELIMINATION — NO n REQUIRED
- **DEPTH IS NOT THROUGHPUT-BOUND.** 25 fresh sessions, ~1,000x throughput, depth delta 0.
- **THE ABDUCTION VOCABULARY COULD NOT EXPRESS A LEVEL-UP.** 0 predicates on every record.
- **`region_uniform` / `regions_equal` ARE UNSATISFIABLE ON THIS DOMAIN.** 0/5 and 0/6.
- **DENSITY IS FLAT; DETECTION CHANGED.** Baseline verified by `--diff-filter=A`.
- **REPLAY BYPASSED THE ABDUCTION BANK.** Single-call-site receipt, structural.

### n UNRECOVERABLE FROM THE RECORD — STATED, NOT ESTIMATED
- **G23 dead-dedup (743 -> 454).** A full recount, not a sample — but **THE HARVEST RECORD
  CARRIES NO TIME FIELD**, so its AS-OF cannot be supplied and the population may straddle
  the 2026-08-14 level-convention change. Already recorded; repeated here because it is
  exactly this register's subject.
- **Every wave-1 item** (movement stack, rho ladder, ranked drain, origin marker, corpse
  guard, efficiency read, regen series): gate-passed, **ground n = 0**. Already relabelled
  CANDIDATE under CLAIM.md's gate-passed-vs-ground-settled status.

### ALREADY RETRACTED — kept, not deleted
rho = 0.000 (partition artifact, twice) · the throughput ratios >=74x and ~163x
(contaminated) · "45 clicks, 0 effective" as a level-wide claim (29 cells are historically
live) · the HORIZON 15-of-28 claim (budget extends per level).

---

## n = 0 — ASSUMED SINCE THE BEGINNING, NEVER MEASURED
**SEED-STABILITY OF THE WINNER SET.** Repeat an epoch with different seeds: **if the same
agents win, selection is tracking something; if the winners change every time, the economy
is amplifying noise and the ranking means nothing.** This is **a direct test of one of the
architecture's central claims**, it has never been run, and until this morning it cost
fifteen hours per arm. **IT IS NOT A RE-RUN. IT IS A FIRST RUN**, and it belongs above
every re-run on this list because a null there would reprice every ranking the economy has
ever produced — including the arm's.

## THE TWO DISCRIMINATORS TO BUILD IN
**TREND, NOT TOTAL.** A real winner IMPROVES ACROSS GENERATIONS; a lucky one is FLAT AND
HIGH. Same data, much stronger signal than the final count, **and it separates precisely
the two cases the seeding economy conflates.**
**SEED-STABILITY.** As above. Both are cheap now and neither was affordable this morning.

## THE STANDING CAUTION, ADOPTED
The old sample sizes were **budget artifacts** — fifteen hours per arm is why n was what it
was. At seconds per session **n is CHOSEN rather than AFFORDED, so the honest standard goes
UP rather than staying where it was.**
And cheap repetition invites reading many runs casually. Prereg, as-of, population label
and the guaranteed-number check were affordable at fifteen hours per arm **because the run
itself forced a pause. NOTHING FORCES ONE NOW.**
**MORE RUNS, SAME DISCIPLINE PER RUN.**

---

# RE-DERIVING n FROM WHAT THE CLAIM NEEDS (2026-08-18, Isaiah's question)
*"is there any reason a re-run is 3 games rather than 25 — or 25 games rather than
25 x several seeds? If there's a constraint I'm not seeing, name it."*

## THE ONE CONSTRAINT, MEASURED — AND IT IS NEITHER THE CLOCK NOR THE API
```
  ONE offline session, FRESH empty box .............. 11.7 s
  ONE offline session, EXISTING 55 MB box (ls20) .... 71.3 s      6.1x PENALTY
  box sizes today: ls20 73MB/55MB db · ar25 55MB/43MB · bp35 155MB/131MB
```
**PER-SESSION COST SCALES WITH ACCUMULATED BOX SIZE.** Gameplay is ~0.15 s of the 71 s;
the rest is the local DB layer — the schema rebuild from `object_detector.py:37`'s relative
`db_path`, and commits without WAL (313 ms vs 0.03 ms, PERF_AUDIT). **THAT IS THE WHOLE
CONSTRAINT, IT IS 6x, AND IT IS ALREADY ON THE RULE-FIRED QUEUE AS R3.**

## SO: 3 GAMES -> 25. NO REASON NOT TO, AND A BETTER REASON THAN COST
**THE 25 GAMES ARE NOT A SAMPLE. THEY ARE THE POPULATION.** Running 3 was SAMPLING a
population we can ENUMERATE. **25 games is a CENSUS, not a bigger sample**, and there is no
statistical argument for sampling what you can enumerate. Cost: 25 x 71 s / pool 4 ~= **7.5
minutes**.

## 25 GAMES -> 25 x SEEDS: SEEDS ARE THE ONLY REAL SOURCE OF ADDITIONAL n
Once the games are a census, **every further n must come from REPETITION** — and repetition
is exactly what the seeding economy's variance requires.
```
  25 games x  5 seeds x 2 arms = 250 sessions ~= 74 min at today's DB cost
  25 games x 10 seeds x 2 arms = 500 sessions ~= 2.5 h
  the same after the R3 DB fix (11.7 s/session):  ~= 12 min and ~= 24 min
```
**SEEDS ARE AFFORDABLE NOW AND CHEAP AFTER R3.** The constraint bites somewhere past
25 x 50, not at 25 x 5.

## RE-DERIVED SAMPLE SIZES, BY WHAT EACH CLAIM NEEDS
| claim | needs | proposed |
|---|---|---|
| "the stack pays" (a MARGIN, under seeding-economy variance) | separation from seed noise | **25 games x >=5 seeds x 2 arms** |
| seed-stability of the winner set | enough seeds to see churn | **>=5 seeds, 10 preferred** |
| "selectivity not activity" | rides the same runs | **free** |
| offline throughput | several games | **~free** |
| any ELIMINATION | n=1 | **unchanged** |

## THE SEED-STABILITY LOSING CONDITION, PINNED BEFORE IT RUNS
Seat 4: *partial overlap is the likely outcome and it is the one that is arguable
afterward.* Correct, so it is fixed now.
**AND A GUARANTEED-NUMBER TRAP IN THE OBVIOUS METRIC:** with `--population 6`, the top-5
winner set is **5 of 6 by construction**, so pairwise Jaccard is high NO MATTER WHAT and
would "prove" stability from pure noise. **THE CRITERION MUST BE STATED AGAINST THE NULL,
NOT AGAINST AN ABSOLUTE THRESHOLD.**
**PRE-COMMITTED:** compare the observed cross-seed winner overlap against **the overlap
expected from RANDOM winner assignment at the same population size**, computed by shuffle.
  - observed overlap **significantly ABOVE** the null -> **selection tracks something**
  - observed overlap **indistinguishable from** the null -> **the economy amplifies noise
    and every ranking it has produced, including the arm's, is unsupported**
  - **anything between -> UNRESOLVED, more seeds. NOT a partial win.**
**AND RAISE THE POPULATION** so the statistic has room: population 6 cannot express this.

## TWO LABELS ADOPTED FROM SEAT 4
**(i) THE SORT IS PER-CLAIM, NOT PER-VERDICT.** The arm contains both kinds — 19v11 is a
margin, sp80's 31v0 is an elimination. Link 3 contains both — the 0 survives, the 50 does
not. **Stated as the rule rather than the instance, because the next verdict will too.**
**(ii) RANK 4's ELIMINATION IS LICENSED BY MAGNITUDE, NOT BY n.** "No plausible variance
closes ~1,000x" is a judgement about effect size against noise, **stated rather than
measured**, and it now carries that label. It is the same reasoning as *this is a
categorical absence*, and it is the honest account of why thin n is acceptable there and
nowhere else on this list.

## AND THE GUARD, BECAUSE NOTHING FORCES A PAUSE NOW
Seat 4: the signature of the coming failure is **verdicts arriving without their population,
as-of, or n**. Four such omissions in ten days when runs took hours; at seconds, the same
omission rate produces far more unlabelled numbers.
**PROPOSED (SUBJECT / GROUND-GATED): a report carrying a number and no n has not cleared
the standard** — checkable mechanically against the report's own format, in the same shape
as the consumption sweep, and it does not depend on anyone remembering.
