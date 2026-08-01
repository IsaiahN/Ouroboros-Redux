# PREREG — the roster re-rendered through both fixed printers (arm T)

**Written BEFORE launch.** 2026-08-01 ~10:5x UTC. Commit at time of writing: `440dee0` plus an uncommitted
tools-only change (the result sidecar, below). Nothing in this file may be edited after the arm starts; the
EVIDENCE doc records what happened and cites this one.

## Why this arm exists at all — two debts, one arm, and no cheap path

Two printers were found wrong AFTER the roster had been measured through them.

**CLASSIFIER 18** (fixed at `25202dd`). The self-motion control grouped by EXIT LITERAL and then by action. But
the control's question — *did the agent move the board, or does the board move anyway?* — has the GAME as its
denominator, not the exit. A game whose actions were split across several exits therefore rendered a row per
exit, each with one action in it, each verdict reading `MUTE: one action only`. Every one of those verdicts is a
SUBSET reading. Arm O is the 25-game record the roster's claims rest on, and it was rendered by the broken
printer.

**CLASSIFIER 19** (shipped at `440dee0`). The `live` literal is defined by a LOWER bound only, so it pools a
four-cell answer with a full-screen repaint. It has now been split by size on TWO games (arm S). The roster's
`live` total — 1181 charged steps in arm O — has never been split at all.

**The cheap path does not exist and this was checked, not assumed.** `tools/sweep_chain.py` `main()` rendered
straight to stdout and persisted no result dict. Rendered text cannot be re-rendered. So the debt costs a live
sweep, and this is that sweep.

**On the way, the debt class is retired.** This arm carries a tools-only change: the sweep writes its result
dict as JSON beside the capture, and gains a `--render <file>` path that re-prints a banked sweep without an API
key. The sidecar is verified rather than assumed — the capture is rendered twice, once from the measured dict
and once from the reloaded file, and the two strings are compared, with the verdict printed either way. From
this arm forward, a printer fix is a re-render. `tests/test_sweep_dump.py` pins the round trip and, in its third
test, pins that the comparison CAN fail — an equality assertion between two renders is worth nothing unless the
renders could differ.

## Arm T — the run

- 25-game roster, `max_actions=120`, `wall_cap_s=200`, no `only` filter. A full roster, so no pooled number in
  the capture is pooled over a subset.
- **Bank state at launch: WARM.** `.residual_bank/` holds 15 game files, 744K, fingerprint
  `bd0744f64dbceae55996ed297d88b371` (md5-of-sorted-md5s). Fourteen were written by arm O_floor on 07-31
  ~22:3x; `su15.json` was rewritten by arm S at 08-01 07:37. It is NOT byte-identical to `/tmp/bank_snapshot`.
  Any firing count from this arm is a WARM-BANK count and must be cited as one.
- **No agent path is touched by this beat's change.** The only edited runtime file is `tools/sweep_chain.py`,
  which the agent never imports.

## The predictions

Six of the nine below are DERIVED POINT PREDICTIONS: they are what an already-published instrument FORCES the
new numbers to be, computed here at zero API cost. `armO_floor.txt` (07-31 22:40) published, per game, the
`live(mean/max)` masked-cell statistic. The boards are 64×64 = 4096 cells (`band_cells=64/4096` in the same
capture). So `live_max_frac` is FORCED to `max / 4096`, and the `@25 / @50 / @75` columns are forced with it.

The derivation is already validated on two instances: arm S measured `su15` at 0.5% and `tn36` at 61.5%, and
arm O's maxima of 20 and 2518 give 20/4096 = 0.49% and 2518/4096 = 61.5%. Two for two.

| game | armO live max | forced `maxfrac` | ≥25 | ≥50 | ≥75 |
|---|---|---|---|---|---|
| m0r0-492f87ba | 2708 | 66.1% | ✔ | ✔ | ✘ |
| tn36-ef4dde99 | 2518 | 61.5% | ✔ | ✔ | ✘ |
| lp85-305b61c3 | 1409 | 34.4% | ✔ | ✘ | ✘ |
| bp35-0a0ad940 | 461 | 11.3% | ✘ | ✘ | ✘ |
| cn04 279 · vc33 265 · cd82 201 · sp80 163 · ls20 146 · r11l 121 · ar25 109 · sk48 97 · g50t 71 · wa30 65 · re86 61 · lf52 57 · sb26 53 · ft09 38 · tr87 29 · su15 20 · tu93 20 · ka59 19 · s5i5 12 · dc22 9 | | ≤ 6.8% | ✘ | ✘ | ✘ |

**T-1 (derived, point).** `>=75%` is ZERO on every game and therefore zero on the roster. The largest masked
change arm O ever recorded on any game was 2708/4096 = 66.1%.

**T-2 (derived, point).** `>=50%` is nonzero on EXACTLY TWO games — `m0r0-492f87ba` and `tn36-ef4dde99` — and
zero on the other twenty-three. Equivalently: at the shipped 50% edge, `redraw` is confined to those two games.

**T-3 (derived, point).** `>=25%` is nonzero on EXACTLY THREE games: the two above plus `lp85-305b61c3`.
`lp85` is the head item's named case — 1409/4096 = 34% is `local` at the shipped edge and `redraw` at a 30% one.

**T-4 (derived, point).** `live_max_frac` per game lands within ±2 percentage points of the forced column
above on every game that runs to a comparable step count.

**T-5.** The roster's `redraw` count is under 2% of its `live` total. Arm S measured 1 redraw in 36 live steps
on the cheap pair; the table above says only two games can contribute any at all.

**T-6 (identity, must hold or the instrument is broken).** For every game, `local + redraw + unsized == live`,
`unsized == 0`, and `live_hist_n == live`. A partition that does not sum back is a defect, not a finding.

**T-7 (derived, point — CLASSIFIER 18).** Re-deriving arm O's own per-exit rows and regrouping them by game
gives: 24 games with priced rows, **17 crossing more than one exit**, and **8 WIDENED** — games whose two or
more actions never met inside a single exit, so every per-exit verdict on them was a subset. The eight are
`bp35`, `cd82`, `cn04`, `ka59`, `lf52`, `sb26`, `sc25`, `sp80`. Arm T's by-game block should flag WIDENED on
6–10 games and report `games that crossed >1 exit` in 14–19.

**T-8.** The regrouping residue printed by the by-game block (`regrouped priced steps` vs `pooled action split`)
is **0**. It was 0 on arm R's two games; a nonzero residue on 25 means a step is being counted in one grouping
and not the other.

**T-9 (the sidecar).** The capture ends with `RESULT SIDECAR: <path> -- reload renders BYTE-IDENTICAL`. If it
instead reports LOSSY, the sidecar may not be cited and the debt is NOT retired, whatever else the arm found.

## What would falsify the reading, and what would not

- A `>=50%` on a THIRD game falsifies T-2. That is the interesting outcome, not the boring one: it would mean
  the roster's redraw population is trajectory-dependent rather than a property of two games, and the whole
  derived-prediction method above would need re-pricing.
- Run-to-run variation is expected in the COUNTS (steps, deaths, firings) and is not a falsification of T-1..T-4,
  which are about the MAXIMUM a game's board can be made to change. A game that dies early and never reaches its
  large-change state renders a smaller max; that is a shorter trajectory, not a different board, and it is
  recorded as such rather than scored against the prediction.
- **Nothing here is a claim about the agent getting better.** This arm changes no agent path. `CLEARED` is
  expected to remain 0 and the detector taxonomy stays frozen.

## What this arm may NOT be used for

Re-interpreting any historical row by hand. The whole point is that the rows get RE-RENDERED. A hand-reinterpreted
verdict is a conclusion banked in place of a receipt, and this file exists so that temptation has a written answer.
