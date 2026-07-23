# Live game survey (redux-triality) — is the current loop winnable anywhere?

Goal: validate the reunified-so-far agent against a real OBSERVED win before building the reward market. LAW-0
rendered each recording; ran the current `run_goal_live` on the drivable ones.

| game | drivable? (single translating mover) | live result | note |
|------|--------------------------------------|-------------|------|
| ls20 | ✓ cursor 12, vecs ±5, floor 3 | 14px from target, **levels 0**, GAME_OVER | timer; BE_AT the box ≠ win |
| tu93 | ✓ (keyboard_click) | — | wins are observable (1 win in recordings) but needs click |
| wa30 | ✓ cursor 0, vecs ±6/7, bg 1 | 10px from target 9, **levels 0**, GAME_OVER (scorecard c44a61e7) | multi-object puzzle |
| g50t | ✗ **undrivable** | — | light-blue cursor leaves a SAME-COLOUR TRAIL → translate-based detector mis-IDs it (picks the maroon target), `vecs={}` → agent cannot act |
| tr87 | ✗ **undrivable** | — | `vecs={}` (no clean per-action displacement) |

## Findings (honest)
1. **No surveyed game wins with the current loop.** Where the agent CAN drive (ls20, wa30) it navigates to within
   ~10–14px of the salient target and still scores 0 — reaching a salient object is not the win (the relations.py
   lesson, now confirmed on TWO games).
2. **The perception is narrow.** It only handles a single clean *translating* mover on a static field. A
   trail-drawing cursor (g50t) or a game with no clean per-action displacement (tr87) yields `vecs={}` and the
   agent can't act at all. This is a separate perception-breadth gap (defer).
3. **Reward is universally starved** across the surveyed set (0 wins live and in the recordings). A reward-priced
   market has no currency to arbitrate with.

## Conclusion → next reclaim
The metric will NOT move by finding a game where "reach the salient target" happens to win — it doesn't in this
set. The chart's prescription is the path: reclaim **exploration.py** (empowerment / curiosity bootstrap) so the
agent explores broadly enough to STUMBLE INTO wins and thereby MANUFACTURE reward when `|R⁺_ρ|=0` — then the
reward-priced typed-relation market (**relations.py + marketplace.py**) can learn the actual win relation from
those wins. Exploration first (make reward non-zero), market second (learn what the reward tracks). The current
goal-fixation (navigate to one salient object) is actually *worse* than broad exploration for stumbling into a
first win, which is further reason to put exploration next.

## Exploration sweep + tu93 win analysis (curiosity reclaim beat)
Reclaimed `explore.py` (CuriosityExplorer: cell-coverage novelty, decays, Goodhart-guarded; tests pass) and ran
it LIVE:
- ls20 EXPLORE (21373b3e): coverage 35 cells (~all of the green region), levels 0, GAME_OVER (timer).
- wa30 EXPLORE (0000fb9b): coverage 60 cells, levels 0, GAME_OVER.
- tu93 EXPLOIT (17d1cb04) / EXPLORE (6ff2ac37): levels 0, GAME_OVER at the ~50-step timer; explore coverage only
  3 (narrow black corridors); referent prior mis-picked colour 2 (the RED WALLS) as the target.

**tu93 win-recording analysis (a9e77dad, the ONE observed win, L1 at step 42):** the cursor (colour 4) was
MID-MAZE at (33,13) at the win — NOT at any salient object. Magenta (colour 6) is the depleting TIMER bar at
row 63 (size 19→13 then resets to 64 on the level redraw), NOT a goal. So even our single win does not correspond
to "reach the obvious object"; the win mechanic is opaque from centroids.

## Hard honest conclusion (5 live runs, 3 games, both modes → 0 reward)
Navigation + cell-coverage exploration is INSUFFICIENT to move the metric on ls20/wa30/tu93: covering the passable
space doesn't win, timers end first, and no perceptual referent picks the goal. There is NO reward on any
drivable game, so the exploration→reward→market bootstrap cannot start (it never reaches a win to learn from).
The win conditions are specific discoverable mechanics beyond navigation. This is a strategic fork worth Isaiah's
input: (a) reclaim relations.py + marketplace and explore over (object × RELATION) HYPOTHESES not cells; (b) mine
more win recordings for a navigation-tractable game; (c) expand the action model (click/coordinate, multi-step);
(d) accept the current instantiation may need substantially more machinery to score on the dev set.
