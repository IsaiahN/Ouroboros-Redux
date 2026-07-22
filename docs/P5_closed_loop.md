# P5-GOAL step 2: the whole chain closes (synthetic), and why real grounding needs live

## LAW-0 finding (why offline grounding of target-selection is a dead end on these recordings)
Inspected the tu93 recording that actually wins (a9e77dad, `levels_completed` 0→1 at step 42). The win is a
**762-cell whole-maze REDRAW** (a level transition), not a within-level progress gradient. No colour shows a
monotone component-count drop (no "collection" signal); the games are **navigation-to-sparse-win**. Across all
tu93 recordings there is exactly **one** win; ls20 has none. So the passive dev recordings contain no dense,
positive, non-circular signal to ground TARGET SELECTION against — confirming (with pixels) last beat's timer
finding. Grounding target-selection on real reward therefore requires the agent to **generate its own wins**
(go live and probe), not more replay.

## What was built instead — the unbuilt chain link (`src/newhorse/redux_arch/planner.py`, 3 tests)
The chart flags PLAN→leading-goal + ACT(pragmatic) as a separate, unbuilt link (Amdahl: a posed goal is
necessary, not sufficient). Built the minimal version and closed the WHOLE chain on a synthetic known-answer
maze:
- `plan_action(...)` — a pragmatic one-step planner: among PASSABLE destinations (the minted **INTENDED_FREE**
  affordance), pick an action whose before-state Context satisfies **φ_goal**. This is where the two BUILT tiers
  finally compose: Tier-1 affordance says what's DOABLE, Tier-2 posed goal says what's WANTED.
- `GoalDirectedAgent` — perceive → POSE (once, from a warmup) → PLAN/ACT to serve the posed goal.
- End-to-end result: the agent poses `ACTS_TOWARD(avatar, target=7)` (the reward-linked object, NOT the
  distractor 8), then clears **59 levels in 400 steps**; a random agent clears **0**. A wall-band variant shows
  the planner never chooses a wall cell (INTENDED_FREE gating) and still reaches the target through the gap.

## Honest status (RULE 0.7)
This moves a **synthetic** `levels_completed`; the real metric is still 0. But it proves the full architecture
composes end-to-end (perceive → pose → plan → act → complete) **when a dense signal exists**, which isolates the
sole remaining real-ARC gap precisely: not the mechanism, not the planner — the **dense reward signal**. Next:
go LIVE so the agent generates its own reward events (wins), pose the goal by probing which salient candidate
moves the true reward, and run this exact loop on real frames.
