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
