# LINK 3 — THE OBJECTIVE. Located, 2026-08-18. MODE: **GROUNDED**.

METHOD: ran the SHIPPED abduction vocabulary (`extract_predicates`) against **every
level-up frame this project has ever recorded** — the 9 records in `levelup_frames`.
Read-only, offline, no episode, no contention with the control arm. The one genuine frame
corpus I have been calling impoverished is exactly what this experiment needed.

## THE NUMBER

**TOTAL PREDICATES EXTRACTED FROM EVERY LEVEL-UP THIS PROJECT HAS EVER RECORDED: 0.**

*Could it have been anything else:* yes — any single predicate firing on any one of the 9
would have produced a `goal_hypotheses` record and a non-empty `abduced`. **There is
nothing this beats. It is the first grounded reading ever taken at link 3.**

## THE CORRECTION TO FIGURE 3

Figure 3 reads link 3 as *"abduced = [] — the space is never searched."*
**THE SPACE IS SEARCHED, EXHAUSTIVELY, EVERY TIME.** `observe_levelup` ran on all 9,
banked all 9 frame snapshots (the append at `goal_abduction.py:162` is unconditional and
precedes extraction), and evaluated 5 + |colours| + 6 candidates on each.
**THE SPACE IS EMPTY BY CONSTRUCTION.** That is a different defect with a different fix:
not plumbing, VOCABULARY.

## WHY EACH PREDICATE CLASS CANNOT FIRE — measured per class, all 9 records

  `region_uniform`  (5 candidates: full + 4 quadrants)
      **satisfied 0/5 in post AND 0/5 in pre, on every board.** A 64x64 ARC board is
      never uniform over a quadrant. THE PREDICATE IS UNSATISFIABLE ON THIS DOMAIN.

  `regions_equal`   (6 candidates: quadrant pairs)
      **satisfied 0/6 in post on every board.** Quadrants are never identical.
      ALSO UNSATISFIABLE ON THIS DOMAIN.

  `colour_count_zero` (one candidate per colour present in PRE)
      Requires a colour present in pre to be ABSENT in post. **VANISHED = [] on all 9.**
      NO COLOUR HAS EVER DISAPPEARED AT A LEVEL-UP IN THIS PROJECT'S HISTORY.
      AND THE SIGN IS BACKWARDS: at level-ups colours are **ADDED** —
        r11l L1: pre [0,1,2,3,5,6,15] -> post [0,1,2,3,5,6,**10,12**,15]
        cd82 L1: pre [0,2,3,4,5,15]   -> post [0,2,3,4,5,**12**,15]
      **THE VOCABULARY LOOKS ONLY FOR DISAPPEARANCE AND THE DOMAIN ONLY DOES
      APPEARANCE.** It is not merely too coarse; it is ANTI-CORRELATED with the event it
      exists to describe.

## THE CONNECTION TO THE BOARD AUDIT

`colour_count_zero` is the one predicate that could express the column-63 clock reaching
exhaustion (BOARD_AUDIT s2). It cannot fire here for a reason that is structural rather
than accidental: **at a level-up the clock REFILLS.** So the single predicate with any
purchase on the real terminal condition is evaluated at exactly the moment it is
guaranteed false. The vocabulary has no "count equals N", no "count increased", no "count
decreased" — only "count is zero".

## AND THE TRANSITION THAT MATTERS MOST WAS NEVER CAPTURED

**ALL 9 RECORDS ARE LEVEL 1.** ar25 reached level 2 and there is NO L2 level-up frame
anywhere. The 9 files hold roughly 4 distinct events (ar25 L1 x3, lp85 L1 x4, r11l L1,
cd82 L1). So the abduction bank has never seen the transition it would need to learn
level 2 — the one the banked prefix reaches by replay and has never re-derived (F-1).

## WHAT THIS MEANS FOR THE QUEUE

Figure 1's completeness test — *everything either produces R or consumes Γ* — and Figure
3's caption — *optimising a link that already works cannot rescue one that does not* —
now have a receipt. **EVERY ITEM ON THE CURRENT QUEUE IS AT LINKS 1-2**: dead-cell dedup,
corpse guard, drain order, the affect tail-read, the schema rebuild, the janitor, the
`:337` fix. Link 3 has been returning 0 for the entire life of the project and no item on
the board addresses it.

Seat 4's framing is the right account and is worth keeping verbatim: **this is not a
failure of judgement. Links 1-2 are where the instruments could see. Link 3 had
`abduced = []` — no records, no failures, no residual — so there was nothing to
instrument. The work went where the work was visible, and the visible work was the wrong
work.** That is the wrong-target state one level up: everything green, counter flat, and
the green measured on the links that were not the problem.

**THE BUILD THIS IMPLIES IS NAMED AND NOT STARTED** (allocation is Seat 3's, and the
control arm still outranks): a predicate vocabulary whose candidates are drawn from what
the frames DO — appearance, count change, local structure — rather than from three global
forms that the domain never exhibits. The falsifier is now cheap and pre-committed:
**re-run this exact experiment against the same 9 records; a vocabulary that still yields
0 has not fixed anything.** This is the first link-3 item with a losing condition.

## ADDENDUM — THE REPLAY BYPASS, CONFIRMED (2026-08-18). MODE: **GROUNDED** (static, exact).

Seat 4 inferred that replay-achieved level-ups never reach the abduction bank. **CHECKED,
AND IT IS TRUE, WITH A SINGLE-SITE RECEIPT:**

  `_goal_abd` HAS EXACTLY ONE CALL SITE: `cognitive_loop.py:1776`, inside the cognitive
  cycle, guarded on `level_changed`.
  `_replay_salient_prefix` (`cognitive_game_player.py:1626-1700`) NEVER ENTERS THAT CYCLE.
  It steps the environment directly and reads `levels_completed` itself at `:1687` — and
  uses it ONLY to classify the outcome (died > reached_level > aborted). **IT BANKS NO
  DELTA. THE ABDUCTION BANK IS NOT ON THE REPLAY PATH AT ALL.**

### THIS EXPLAINS "ALL 9 ARE L1" EXACTLY, AND IT IS A BOOTSTRAP TRAP
L1 is reached by the COGNITIVE LOOP (exploration) -> passes `:1776` -> banked.
L2 is reached ONLY BY REPLAY (F-1: never re-derived) -> bypasses `:1776` -> never banked.
So: **THE AGENT CAN ONLY LEARN GOALS FROM LEVEL-UPS IT ACHIEVED WITHOUT GOALS. THE ONE
RELIABLE SUCCESS PATH IT HAS TEACHES IT NOTHING.**

Seat 4's name for the shape is right and general: **SUCCESS SUPPRESSES THE EVIDENCE
CHANNEL.** Same coupling as the salient-bank suppression, and this time the channel it
suppresses is the one link 3 runs on. Note it is NOT the ledger genus (a fix destroying
its own record) — nothing here was deleted. The observation was never taken, because the
route that succeeds is not the route that observes.

### WHICH SPLITS THE NAMED BUILD IN TWO, AND REVERSES THE OBVIOUS ORDER
  **(a) THE HOOK** — replay-achieved level-ups must reach the abduction bank.
  **(b) THE VOCABULARY** — candidates drawn from what the frames DO (appearance, count
       change, local structure) rather than three global forms the domain never exhibits.
**(a) IS PRIOR TO (b).** A perfect vocabulary shipped alone would still only ever see L1
transitions, because L2 never reaches the bank. Shipping (b) first would produce a fix
that passes its own falsifier on the 9 L1 records AND STILL CANNOT SEE LEVEL 2 — a
gate-passed candidate that changes nothing, which is the exact class this project has been
relabelling all day.
FALSIFIER FOR (a), pre-committed and cheap: after the hook, a replayed level-up must
produce a new `levelup_frames` record AT A LEVEL > 1. Today that count is **0**.
STILL NAMED AND NOT STARTED — allocation is Seat 3's and the control arm outranks.

## ADDENDUM 2 — THE FIGURE 6 CLAUSE CHANGES HOW THIS BUILD IS MADE (2026-08-18)

"An instrument is not built from a description. It is improved from a worse instrument
already returning something." **THE BUILD I NAMED VIOLATES THIS AS WRITTEN.** I proposed
"a predicate vocabulary whose candidates are drawn from what the frames DO" — that is
SPECIFYING AN INSTRUMENT FROM A DESCRIPTION, which the figure says is not how one comes
to exist.

**THE CORRECT CONSTRUCTION, and the edge already exists:**
  THE WORSE INSTRUMENT: `extract_predicates`. It returns 0.
  IS 0 "NO READING" OR "A READING THAT FAILS TO RESOLVE"? **THE SECOND** — it returns 0
  while the boards VISIBLY DIFFER (`identical=False` on all 9). A detector reporting
  nothing where something plainly happened is a wandering point in the sky.
  THE RESIDUAL IT PRODUCED, measured, not imagined: colours are ADDED, never removed
  (r11l +10 +12; cd82 +12); no region is ever uniform (0/5); no quadrants ever equal
  (0/6). **THAT RESIDUAL NAMES THE NEXT PREDICATE CLASS. The vocabulary is GROWN FROM IT
  RATHER THAN DESIGNED AGAINST A DESCRIPTION OF THE DOMAIN.**

**AND THE FALSIFIER GETS STRONGER FOR THE SAME COST.** Not merely "yields > 0" — that
could be met by any noisy predicate. **THE NEW VOCABULARY MUST EXPLAIN THE SPECIFIC
RESIDUAL THE OLD ONE PRODUCED**: it must fire on the colour-appearance events already
measured in these 9 records, and it must still return 0 on the two classes shown
unsatisfiable. An instrument that fires everywhere has not extended the edge, it has
replaced it.

## AND A CORRECTION I OWE ON V3 (FRAME RETENTION)

I sent frame retention up as a VERDICT and argued "no frame-level work is possible
without a corpus". **THAT WAS WRONG, AND FIGURE 6 NAMES THE ERROR EXACTLY: the search for
a proto-instrument is a search for one that is already there.** NINE RECORDS WAS A
CORPUS. It was enough to produce the finding of the beat. I declared an ABSENCE where
there was an EDGE, and in doing so I put a prerequisite on Isaiah's board that was never
a prerequisite. **V3 IS DOWNGRADED: frame retention is worth doing and it BLOCKS
NOTHING.** The link-3 work can proceed on what is already on disk.

## ADDENDUM 3 — THE SCOPE CLAUSE CORRECTS TWO THINGS I SAID (2026-08-18)

Figure 6 REV(4) scopes the instrument rule: *it tells a FORECLOSED question from a HARD
one. It is not a rule about theory. Theory routinely precedes its instrument and is
welcome to* — Neptune calculated before it was seen, the Higgs mass predicted before the
detector, **and the prediction is what said what to build**. No increment requirement
either: a step change in resolution is fine. **What is unavailable is a sensor for
something NOTHING HAS EVER REGISTERED.**

**CORRECTION 1 — I was too hard on the build, and on myself.** I wrote that proposing "a
vocabulary drawn from what the frames do" **VIOLATES** the clause. IT DOES NOT. That is
theory preceding its instrument, which is explicitly welcome and is often how the pointing
gets decided. The residual-grown construction is still BETTER — it is anchored to a
reading that already exists — but the description-first version was never illegitimate.
THE TWO HALVES COMPOSE: **the prediction says where to point; the instrument still extends
from something that registers.** A Higgs detector was built on accelerators that already
registered particles; the prediction chose the target.

**CORRECTION 2 — and this one mattered more.** I wrote: *"links 4 and 5 are unreached,
returning nothing at all, so there is no edge there and building would be mid-air."*
**THAT MISDESCRIBES A BLOCKED LINK AS AN UNREACHABLE ONE.** Links 4 and 5 are silent
BECAUSE THEIR INPUT NEVER ARRIVES — link 3 returns 0, so planning has no goal and
mint->echo->promote never fires. That is **HARD**, not **FORECLOSED**. The ladder already
refuses work there for its own and sufficient reason: *a step whose input never arrives
cannot be diagnosed, only its predecessor can.* I imported "no edge" as a second reason
and it was the wrong one. The ordering conclusion survives; ONE OF ITS TWO ARGUMENTS DOES
NOT.

### AND THE USEFUL APPLICATION, RUN ACROSS THE WHOLE BOARD
*Foreclosed* means nothing has ever registered anything. Applied honestly:
  link 3 abduction      — 9 records registered, extractor returns 0 -> **HARD**, has an edge
  link 4 planning       — silent because link 3 is 0                -> **HARD**, blocked
  mint -> echo -> promote — never fired end to end, same cause      -> **HARD**, blocked
  L2 level-up frames    — 0 ever registered, BUT the cause is the replay bypass, and the
                          hook makes it register                    -> **HARD**, not foreclosed
  frame-level work      — 9 records; I already retracted this one   -> **HARD**, has an edge
**NOTHING ON THIS BOARD IS FORECLOSED.** Every silence traces to a broken predecessor
rather than to an absence in the world. That is a materially more encouraging reading than
the one I gave last turn, and it is the reading the scope clause exists to produce:
**a diagnosis of "no edge here" is a STRONG CLAIM OWING A SEARCH, not a default for
anything currently quiet.**

## ADDENDUM 4 — TWO CORRECTIONS TO THIS AUDIT, BOTH MINE (2026-08-18)

**1 · THE CORPUS DID NOT SHRINK. NOTHING WAS DELETED.** The builder measured 6 records
where this audit said 9 and reasonably inferred compaction — and flagged it as urgent data
loss. **It is intact: 9 records, 6 under `.runs/swarm/` and 3 under `.runs/arms/`.** The
builder was forbidden from reading `.runs/arms/` (correctly — a measurement is running
there), so it saw 6. NO JANITOR ACTION, NO LOSS, NOTHING TO CHASE.

**2 · AND THE REASON IT LOOKED LIKE LOSS IS A DEFECT IN THIS AUDIT: I POOLED TWO
POPULATIONS WITHOUT LABELLING THEM.** "Every level-up frame this project has ever
recorded" counted the SWARM boxes and the CONTROL-ARM WORKTREES as one corpus.
**The r11l `+10 +12` residual this audit headlines is from `.runs/arms/112913b692a2/
box_r11l/` — a control-arm box, not the swarm.** The observation is genuine (the arm runs
real episodes against real games) but the provenance was mislabelled, and pooling an
experiment's own output with the baseline population is the "populations pooled across a
change" defect from the seat map's channel-decay list. **THIRD TIME A NUMBER OF MINE HAS
ARRIVED WITHOUT ITS POPULATION PROPERLY STATED**, after the as-of on the dead-cell count
and the as-of on G23. That is the pattern, not the instance.

**THE HEADLINE SURVIVES BOTH.** 0 predicates on all 9, and independently 0 on the swarm's
6 — the finding does not depend on the pooling. **AND THE BUILDER'S RESIDUAL IS BETTER
FOUNDED THAN MINE:** measured on the clean swarm population it found that colour
APPEARANCE occurs in only 1 of 3 transitions, while **EVERY COLOUR'S COUNT MOVES ON EVERY
TRANSITION** and the DOMINANT colour flips on lp85. Count-change is the thing every
transition does and the shipped vocabulary had no predicate for it at all. That is a
sharper statement of the gap than "colours are added", and it came from re-measuring
rather than from re-reading.

## THE BUILD, VERIFIED BY SEAT 2 — STATUS: **CANDIDATE**, NOT SHIPPED

Independently re-run, not accepted on report:
  `tools/link3_live_check.py` -> **TOTAL PREDICATES 50 OVER 6 RECORDS / 3 TRANSITIONS
  (WAS 0)**. Clause 1 PASS. **Clause 2 PASS — `region_uniform` and `regions_equal` still
  yield EXACTLY ZERO**, so the vocabulary extended the edge rather than replacing it.
  Clause 3 reported honestly: `region_contains_colour` fires 6/6 and 3/3 — **A CONSTANT,
  NOT EVIDENCE**, kept but never gated on, and flagged in the tool's own output.
  `tests/gate/test_link3_hook_and_vocabulary.py` -> **46 passed**. ruff clean. OOD clean.
  consumption sweep --strict exit 0, ratchet unmoved at 32.

**WHY CANDIDATE AND NOT SHIPPED, stated per record/canon/CLAIM.md's own status rule:** the hook's
falsifier is proven **IN SIMULATION ONLY**. **THE PROJECT-WIDE COUNT OF `levelup_frames`
RECORDS AT A LEVEL ABOVE 1 IS STILL ZERO ON DISK** and stays zero until an episode runs.
The gate passed; the ground has not settled it. FIRST CHECK AFTER THE ARM RELEASES: does a
live episode produce a `levelup_frames` record with `level > 1`.

**TWO THINGS THE BUILDER FOUND THAT THE BRIEF DID NOT ASK FOR, AND BOTH WOULD HAVE SHIPPED
IT INERT.** (i) `play_game` builds a fresh `CognitiveLoop` per episode and `_ego_fabric`
is created lazily inside `record_result`, which the salient replay runs BEFORE — so the
hook would have been perfectly reachable and banked into `None`, every episode, forever.
(ii) `_replay_winning_sequences` carries the IDENTICAL bypass and is the route that most
often reaches L2; hooking only the named function would have left the same defect open
next door. **Neither was in the brief. This is a builder deriving rather than complying —
the second such instance in the record, and the strongest.**

**AND IT CAUGHT ITS OWN OBSERVER DEFECT BEFORE PUBLISHING.** It measured the wiring
registry against `HEAD`, reported "15 receipts were already rotted", then re-measured
against `ad26e69` and found **0 rotted — its own line shifts had caused all 15**, and it
corrected itself in the same report. That is BRIEF_STANDARD's instrument rule held, by a
builder, unprompted.

---

## ADDENDUM 4 (2026-08-18, overnight) — THE `post` SIDE WAS NEVER NORMALISED, AND THE EVIDENCE SAID SO BEFORE THE CODE DID

**HOW IT WAS FOUND: by reading the banked records, not by reading the code.** Verifying that
a live episode had produced a `levelup_frames` record at level > 1 — the exact condition this
audit set for moving off CANDIDATE — I checked the values rather than the keys:

```
pre  dims [64, 64]        <- a grid
post dims [3, 64, 64]     <- A STACK OF THREE FRAMES
```

**THE MECHANISM.** `_get_frame_array` unwrapped `[ndarray] -> ndarray` **only when
`len(data) == 1`**. A step returning three frames fell through to `np.array(data)` and
produced `(3, 64, 64)` where every caller expects `(64, 64)`. The crossing's
pre-observation happened to carry one frame; its post-observation carried three.

**WHY NO INSTRUMENT CAUGHT IT, AND THIS IS THE PART WORTH KEEPING.** `tools/norm_sweep.py`
reported all three of its candidates **clean, and was right to** — both sides of the crossing
call the *same* helper. **The asymmetry is inside the normaliser and conditional on the
payload.** A call-site sweep is structurally blind to that. *Whenever `norm_sweep` is cited
as evidence of symmetry, this limitation goes with it.*

**WHAT IT COST.** All three pre-fix L2 records report `appeared=[] vanished=[]` — pre and
post carry identical colour sets, because a 3-frame stack's colours union to the pre state.
**The malformed post was washing the transition out.** A vocabulary asked to describe a
change it cannot see returns nothing, which is a mechanical contribution to the zero-yield
result this audit has been circling.

**THE FIX, GATED.** `_get_frame_array` now takes the **last** frame of a stack (ordered
oldest → newest, so the last is "the frame now"), by the same rule on the ndarray path and
the list path so the two cannot drift. `tests/gate/test_frame_normalisation.py` — 4 tests,
R4 both ways: the known-positive is a 3-frame payload returning 2-D; **the known-negative is
that a 1-frame payload is byte-for-byte unchanged**, because ten other callers depend on the
case that already worked. **Blast radius measured, not assumed: the full gate suite is
1121 passed, 0 failed.**

**AND CONFIRMED BY THE GROUND, 47 MINUTES LATER.** The overnight run banked a new crossing:
```
11:58  agent_c5258d947f61   pre=[64,64]  post=[3,64,64]   <- pre-fix
13:34  agent_b99641ec6818   pre=[64,64]  post=[3,64,64]   <- pre-fix
19:27  agent_844a7d726e88   pre=[64,64]  post=[3,64,64]   <- pre-fix
20:14  agent_6a7985f9f58c   pre=[64,64]  post=[64,64]     <- POST-FIX, a grid
```
**The post-fix record is also the only one of the four showing a real transition**
(`vanished=[4]`, yielding `colour_count_zero:4`), exactly as the mechanism predicts.

### STATUS, SPLIT — because one half moved and the other did not
- **THE HOOK: SETTLED ON GROUND.** The condition this audit named — *"does a live episode
  produce a `levelup_frames` record with `level > 1`"* — is **met, four times, by four
  distinct agents across two distinct transitions.** No longer simulation-only.
- **THE VOCABULARY: STILL CANDIDATE, AND NOW WITH A NAMED CONTAMINATION.** The corpus has
  grown to **54 records / 16 transitions / 589 predicates** (was 6/3/50), but **three of the
  four L2 records were banked against a malformed `post`**, so every predicate derived from
  them describes a comparison that could not have worked. **The vocabulary reading must be
  re-taken on post-fix records only.**

### THE THREE LEGACY RECORDS ARE NOT LOST, AND I HAVE NOT TOUCHED THEM
`post[-1]` **is** the frame that should have been stored — the record is over-complete, not
corrupt, and is repairable at read time. **I did not rewrite them.** Rewriting stored
evidence to match a corrected reader is the ledger genus exactly (*a fix that destroys the
record of the thing it fixed*), and whether to add a read-time shim or leave them annotated
is **APPARATUS → Seat 3**.

---

## ADDENDUM 5 (2026-08-19) — THE GUARANTEED-NUMBER TEST ON CLAUSE 2'S ZERO. **IT PASSES.**

The updated canon adds a standing check: *"run the guaranteed-number test on every zero
including the welcome ones — the test gets applied to numbers arriving as claims and skipped
on numbers arriving as relief."* **Clause 2 is exactly such a zero.** It reads *"`region_uniform`
and `regions_equal` still yield EXACTLY ZERO, so the vocabulary extended the edge rather than
replacing it"* — a zero that arrived as relief and was never shown to be a reading.

**IT IS A READING. Both predicates fire when the boards demand it:**
```
pre : q0 mixed (3 and 0), q0 != q1        post: q0 uniform 5, q0 == q1
extract_predicates -> {'region_uniform': 1, 'regions_equal': 1, 'colour_count_zero': 2,
                       'colour_present': 1, 'region_colour_count_atmost': 2,
                       'region_contains_colour': 3}   n=10
```
Both survive the filter. So the zero on the live corpus is **evidence about the boards, not a
producer gap** — which is what `tools/link3_live_check.py:46` already names
`UNSATISFIABLE_HERE`, and the "here" is now earned rather than assumed. **Clause 2 PASS
stands, with a check behind it.**

### AND THE OBSERVER'S DEFECT, TWICE IN ONE READING, ON ME
> *"A new instrument's first output is a claim about the instrument, not about the system."*

**Probe 1** string-matched `str(p).startswith("region_uniform")` against records that are
**dicts** — it reported both predicates absent, which was a fact about my matcher.
**Probe 2** used an **all-zero pre-frame**, on which *every* region is uniform and *all*
quadrants are equal — so both predicates held in `pre`, were correctly filtered as non-changes,
and again reported absent. **Two wrong instruments in a row, both of which would have produced
a confident false finding** ("the producer cannot emit these") had I stopped at either.

**The catch was structural, not clever:** the first result contradicted `satisfies()` returning
`True` on the same board, and a producer that cannot make what its own consumer accepts is a
claim strong enough to demand a third look. **The rule earned here: when a probe reports an
absence, construct the case that forces presence before reporting it.**
