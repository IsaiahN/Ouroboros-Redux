# Full dev-set survey (25 games) — where can the current agent even act, and what's the best first-win target?

Short explore-mode probes (warmup 25, ~55 actions) of the current redux-triality agent across all 25 dev
environments, plus prior-beat runs for wa30/tr87/tu93/g50t. Signal per game: can it act (learned action-vecs)?
did it win? how much did it cover?

## Categories (25 games)
- **CLICK-ONLY — agent cannot act at all (6):** s5i5, lp85, tn36, vc33, r11l, ft09. `no_discrete_actions`: their
  only action is a coordinate CLICK (ACTION6), which the agent filters out. ~24% of the dev set is entirely
  locked out without a click modality.
- **UNDRIVABLE by perception (7):** su15, sb26, lf52, sc25, re86, tr87, g50t. Directional actions exist but the
  translate-based detector can't lock a cursor/vecs — trail-drawing cursors (g50t), non-mover/state puzzles
  (sc25), or no clean single mover.
- **DRIVABLE single-body, but 0 wins (10):** cn04, cd82, ls20, dc22, sp80, bp35, sk48, ar25, wa30, tu93. The
  agent navigates/covers (ar25 covered 30 cells, ls20 22) but never wins — reaching a salient target is not the
  win on any of them.
- **TWO-BODY (2):** m0r0, ka59. Coverage ~0 under single-body control (steering one body displaces the other).
  **m0r0 is the ONLY game with winning recordings (5).** ka59 is the same family (charter: m0r0 + ka59 two-body).

## Wins observed in the survey: **ZERO** (live). Only m0r0 (5) and tu93 (1) have wins in any RECORDING (better play).

## Effort-to-win ranking (the survey's answer)
1. **m0r0 — best first-win target.** PROVEN winnable (5 winning recordings), two-body PERCEPTION already reclaimed
   + validated live; only the two-body DRIVER remains. Shortest path to the first `levels_completed>0` and the
   first reward signal. (ka59 is a free second two-body game once the driver exists.)
2. **Clicks — biggest GENERALIZATION gap, not the fastest win.** 6/25 games are click-only and untouchable; the
   click modality is the highest-leverage reclaim for coverage, but it is new machinery and the goal-ID problem
   persists on top, so it doesn't yield a fast first win.
3. Drivable single-body games: navigate fine, but win needs the reward-relation market with NO reward to
   bootstrap — poor effort-to-win until a win exists elsewhere.

## Recommendation (reconciles the fork)
**Finish m0r0 first** (two-body driver → first win + first reward), because the survey confirms it is the only
proven-winnable, already-half-built target. **Then reclaim clicks** as the top generalization move (unlocks ~6
locked-out games). The two are sequential, not competing: m0r0 gets the metric off zero fastest; clicks widen the
board next. The reward-relation market (fork option b) is correctly LAST — it needs a reward source to arbitrate,
which m0r0's win provides.
