# EVIDENCE — arm S: the `live` column split by SIZE

Capture: `/tmp/armS_livesplit.txt`, 2026-08-01 07:36 UTC.
Scorecard: `https://arcprize.org/scorecards/17bf9042-f31a-488e-bf96-2bee1ba7aade`
Games: `su15-1944f8ab`, `tn36-ef4dde99` · budget `120 200` · warm bank · commit: the `live`-split commit.
Prereg: `docs/tether/PREREG_livesplit_the_live_column_split_by_size.md`, written and finished BEFORE launch.

## The receipt, pasted

```
=== BOARD RESPONSE PER GAME (charged once per observed frame, at the observe site) ===
  game               family        charged tail  resid  still   band    sub    live  live%   skip  banded frozen/esc
  su15-1944f8ab      click             117    1      0     31     60     20       6     5%      3      93 Y/1
  tn36-ef4dde99      click             118    1      0      0     31     57      30    25%      2      78 Y/0
  TOTAL                                235    2            31     91     77      36    15%      5

  --- the `live` column split by SIZE (redraw edge = 50% of the board; READOUT ONLY) ---
    game                  live   local  redraw  unsized    resid  maxfrac  >=25% >=50% >=75%
    su15-1944f8ab            6       6       0        0        0     0.5%      0     0     0
    tn36-ef4dde99           30      29       1        0        0    61.5%      1     1     0
    TOTAL                   36      35       1        0        0               1     1     0
```

## Scoring

| # | prediction | result |
|---|---|---|
| S-1 | `local + redraw + unsized == live`, no `★` residue | **CONFIRMED** — `resid 0` on both games and in total |
| S-2 | `live_unsized == 0` on both games | **CONFIRMED** — the area crossed the call site on every `live` step |
| S-3 | `tn36`: `live` 30 = local 29 + redraw 1 | **CONFIRMED, exactly** — and `maxfrac 61.5%` = 2518/4096, the number the derivation used |
| S-4 | `su15`: `live` 6 = local 6 + redraw 0, `maxfrac` well under 25% | **CONFIRMED** — `maxfrac 0.5%` (20/4096) |
| S-5 | the coarse rows reproduce arm R character-for-character | **CONFIRMED** — both `BOARD RESPONSE` rows and both `THE FLOOR, PRICED` rows are byte-identical to `/tmp/armR_classifier18.txt` |
| S-6 | the edge matters on `tn36` (`@25%` 1 vs `@75%` 0) and not on `su15` (all 0) | **CONFIRMED** — both halves |

S-3 is the one that carries weight. The point prediction `29 + 1` was derived arithmetically from arm R's floor
histogram and its `board_cells=4096` — an instrument written for a different question, published before this one
existed — and the new instrument, computed at a different site from a different quantity, returned that exact
partition. A split that had been mis-wired (charging the wrong denominator, double-counting, or reading `cells`
where it meant `area`) had no way to land on 29/1 by accident.

## What the reading says

**The pooling was real, and it is small on this pair.** Of 36 `live` steps across two games, exactly **one** was the
screen being replaced. `live` is not mostly redraws here. Anyone who expected the split to demolish `live%` should
record that it did not.

**And the sharper thing the split makes visible is not the redraw at all.** `tn36`'s `live%` of 25% looks like a
quarter of the agent's actions getting a real answer. The floor histogram says 26 of those 30 steps changed
**exactly 4 cells** — sitting precisely ON the smallness floor `MIN_CELLS = 4` — three more are small, and the
thirtieth is 2518 cells. So `tn36`'s `live` column is: a floor-edge population, plus one screen replacement. The
board that "answered a quarter of the time" answered at the minimum legal size almost every time.

**`su15` is the cleaner statement of the same thing.** Its largest board response across an entire 117-action
episode was **20 cells out of 4096 — half of one percent of the screen.** Whatever `live` is counting on `su15`, it
is not the screen changing state.

## What this does NOT license

- `live_redraw` is **not** a failure, not progress, and not a level advance. Nobody has shown a large answer IS a
  redraw; the claim is only that 61.5% of a screen is too large to be a puzzle responding to one action, and *"too
  large to be X"* is not *"is Y"*. Confirming it needs a rendered frame pair — NEXT item 5 (LAW-0 renders), not this arm.
- The 4-cell concentration on `tn36` is an observation about where its `live` steps sit, **not** a reason to move
  `MIN_CELLS`. CLASSIFIER 17 already exonerated the floor on the distribution as a whole and the freeze in HEARTBEAT
  ranking item 4 still holds: `CLEARED` is 0.
- Two games. Every number above is pooled over `su15` and `tn36` ONLY, on one budget, on a warm bank. The 23 other
  roster games have not been read through this instrument at all.

## Provenance limits, stated

1. **The bank was WARM but was NOT byte-identical to `/tmp/bank_snapshot` at launch** — `.residual_bank/su15.json`
   already differed before arm S started (arm R, 04:34, had run these same two games). So S-5 is a reproduction
   against arm R's *output* bank state, not against the snapshot. It is still a reproduction, and it extends the
   determinism receipt on the board columns to a FIFTH arm; it is not a claim about a cold bank.
2. **This arm re-renders TWO games through the CLASSIFIER-18-fixed printer. It does not discharge NEXT item `1★★`.**
   `sweep_chain.py` persists no result JSON — only rendered text survives — so re-rendering the other 23 games of
   arm O costs a live 25-game sweep. That debt stays open and must not be described as paid.
3. The chain is unchanged by this arm: `su15` REUSE_UNWIRED, `tn36` MINT_UNFIRED with one advance, **`CLEARED` 0**.
