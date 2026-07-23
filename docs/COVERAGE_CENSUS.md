# Coverage census — measured routing of the redux-triality policy across all 25 dev games

Measured live (`run_policy_live`, max_actions=22): what family the ONE router assigns each game, and whether it
scored. This REPLACES the estimates in DEV_SET_SURVEY.md with real routing.

| game | family | levels | outcome |
|------|--------|--------|---------|
| ar25 | directional | 0 | action_cap |
| bp35 | directional | 0 | GAME_OVER |
| cd82 | directional | 0 | action_cap |
| cn04 | directional | 0 | action_cap |
| dc22 | directional | 0 | action_cap |
| ft09 | click | 0 | action_cap |
| g50t | effect | 0 | action_cap |
| ka59 | directional | 0 | action_cap |
| lf52 | effect | 0 | action_cap |
| lp85 | click | 0 | action_cap |
| ls20 | directional | 0 | action_cap |
| m0r0 | two_body | 1 | action_cap |
| r11l | click | 0 | action_cap |
| re86 | directional | 0 | action_cap |
| s5i5 | click | 0 | action_cap |
| sb26 | effect | 0 | action_cap |
| sc25 | directional | 0 | action_cap |
| sk48 | directional | 0 | action_cap |
| sp80 | directional | 0 | action_cap |
| su15 | click | 0 | action_cap |
| tn36 | click | 1 | action_cap |
| tr87 | effect | 0 | action_cap |
| tu93 | directional | 0 | action_cap |
| vc33 | click | 0 | action_cap |
| wa30 | directional | 0 | action_cap |

## Summary
- **Actionable: 25/25** — every dev game routes to a driving family; **ZERO undrivable** (was 18/25 before beats D/E).
- By family: directional 13, click 7, effect 4, two_body 1.
- **Wins (levels>0): 2** — m0r0 L1 (two_body), tn36 L1 (click).

## Honest notes
- **tn36 WON L1 via CLICK** — a new win beyond m0r0: the ClickProber's curiosity stumbled into a winning click.
- **ka59 routes DIRECTIONAL**, though the charter calls it a two-body game. Under the tightened is_coupled (>=3
  co-moving actions + conserved invariant) ka59 does not meet the two-body bar in a 22-action probe — either its
  coupling needs a longer warmup to show, or it is not a clean mirror. A real finding to revisit, not a mis-fix.
- Wins are under a SHORT 22-action probe; games needing more actions to win are undercounted here. The census
  measures ROUTING (actionability), not the win ceiling.
- levels-0 on a routed game = acts but the win mechanic is unlearned (expected; winning is the hard part).
