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
