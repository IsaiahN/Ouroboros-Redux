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
