# THE PLANNER ALGORITHM READ (2026-08-20) — Seat 3's third question, answered from code

**The question:** *is try-every-atom-at-every-position the right algorithm at all, or the most
expensive possible route to whatever the planner is actually computing?*

## What `plan_to_identity` actually computes
A **forward state-space search**: from the workspace frame, apply atoms (learned EFFECT
patches) as operators, seeking a state where `compute_d(state, reference).differing == 0`
(or, in goal mode, `satisfies(goal_predicate, state)`). Memoised per `(atom, state_key)`;
COMPOSITE atoms recurse through their parts; a stitched plan is verified by forward replay
before being returned.

## THE FINDING: THE SEARCH IS GOAL-BLIND, AND THE GOAL SIGNAL IS ALREADY COMPUTED
`_candidate_ids(gamma, game, level)` selects candidates by **game and level validity only** —
it does not take the diff. Yet the planner **has** the diff: `compute_d(ws, ref)` names
exactly which cells differ, it is evaluated in the stopping test, and the cognitive loop
narrates `d.differing` right next to the plan call.

> **The planner computes precisely which cells need to change and then searches as if it
> didn't know** — every atom, every anchor, in the whole frame, including regions the diff
> says are already correct. *Produced-and-not-consumed, inside the algorithm itself.*

## What this means for the three builds
1. **The applicability index (W2a, cleared)** is still right and still first — feasibility
   pruning helps any search shape and its write-sites are shared with provenance tags.
2. **But the fundamentally faster route exists and is a REFACTOR, as Seat 3 suspected:
   goal-directed candidate selection.** Only atoms whose effect patch **intersects the
   differing region** can be on any minimal path. On typical boards the diff is a few cells
   to a few regions; the candidate set collapses from |Γ| × anchors to atoms-touching-the-diff
   × anchors-in-the-diff. This is means-ends analysis — match operators to the *remaining
   difference*, the classical repair for exactly this cost shape.
3. **Ordering ruling needed (small):** index first as cleared, with diff-directed selection
   as W2a-2 behind its own falsifier — or fold both into one builder brief since they touch
   the same `_candidate_ids` seam. **Recommendation: one brief, two gated stages** — the
   index's F1 window read stays clean (stage 1 measured alone), and the diff-directed stage
   carries its own falsifier: *on the same window, candidates-per-call drops by ≥10× vs
   index-only, with F2's superset check re-proven against the diff-restricted set* (an atom
   whose patch does not intersect the diff can still be needed for a multi-step path through
   an intermediate state — so the superset check for stage 2 must be against RECORDED
   multi-step solutions, not single applications; if none exist yet, stage 2 waits for the
   first recorded plan).

**The honest caveat, stated before anyone builds:** goal-directed pruning is only provably
lossless for single-step reachability; multi-step paths can pass through states that
temporarily *increase* the diff. Stage 2's falsifier above exists because of exactly this —
the refactor is a claim to be gated, not an optimisation to be assumed.
