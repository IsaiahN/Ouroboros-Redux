# PREREG — W2b: THE PLANNER AS LAST RESORT (2026-08-20) — NAMED, NOT YET BRIEFED

Seat 3: *"The planner should engage when the cheap routes have failed to produce a good
option, not on every cycle where atoms happen to exist. An index makes an expensive search
cheaper; it does not decide when the search is worth running."*

**THE BUILD (scheduling, separate from the index):** the planner runs only when (a) no rung
above a stated confidence produced an option this cycle, AND (b) the situation changed since
the last planner attempt on this board-state (state-key check — no re-searching an unchanged
world). Both conditions narrated (W1) so every planner engagement carries its reason.

**FALSIFIERS (to be pinned at briefing):** F1 planner call count per episode drops by a
measured factor with no depth regression on the split-half read; F2 known-negative — a cycle
where cheap routes fail MUST still reach the planner (starvation guard: the scheduler may
delay, never permanently deny); F3 the deferral is narrated, never silent.
**UNDO:** remove the two gate conditions; the planner reverts to engage-on-atoms.

**RIDER (2026-08-20, the shadow test's Interruption finding):** on a mid-plan abort the
scheduler must ROUTE the abort — *world moved* (state key changed under the plan: re-plan,
do not penalise the plan) vs *plan wrong* (state as predicted, step failed: penalise). The
rebinding conflation one layer up; one discriminator closes it. Falsifier at briefing:
constructed cases both directions.

**EVIDENCE UPGRADE (F1 window):** engage-on-atoms DOUBLED planner calls (5→10) in the
capacity the index freed — every speedup is reabsorbed by the search that returns nothing.
W2b is what stops that, not an optimisation.
