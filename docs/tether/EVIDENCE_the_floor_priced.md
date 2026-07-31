# EVIDENCE — THE FLOOR, PRICED

*Recorded 2026-07-31. Instrument added this beat (`ChainLedger.board_cells_hist` / `_board_cells_kind`,
`tools/sweep_chain.py: floor_section`); fired on arm O, a 25-game sweep at `120 200`, scorecard
`https://arcprize.org/scorecards/b126d739-6a3c-4580-b638-2801efe13bb6`. **The residual bank was WARM**
(`.residual_bank/` present on disk at launch). This is EVIDENCE. It records what the receipt printed and how
to overturn it. It does not conclude.*

## The question, and why it needed an instrument

`MIN_CELLS = 4` decides whether a board ANSWERED. Everything downstream reads it — `answered`, `is_null`,
`failed_trial`, `frozen`, `responsive_fraction` — and every one of those is a MAX over the masked
changed-cell count. The only number ever published about that count was `mean_masked_cells`: one mean pooled
over four populations (`still` at 0, `band_only` at 0, `sub_floor` below the floor, `live` at or above it).
A pooled number offered as evidence about a subset cannot say which members, and a mean cannot speak to a
predicate that reads a max. So the standing suspicion — *the agent looks inert because the floor is set too
high* — could not be tested; it could only be asserted.

## The distribution, 24 games, 2799 charged steps

| masked changed cells | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | ≥8 |
|---|---|---|---|---|---|---|---|---|---|
| charged steps | 1256 | 267 | 63 | 9 | 26 | 0 | 1 | 0 | 1177 |

**It is bimodal, and the floor sits in the empty part of it.** 87% of every charged step is either exactly
zero cells (45%) or eight-or-more (42%). The whole interval the floor could plausibly be moved through —
cells 1 through 7 — holds 366 steps, 13%.

Priced as an intervention, which is the only way this number is worth anything:

- floor 4 → 3 reclassifies **9 steps of 2799 (0.3%)**, on two games (`re86` 8, `sp80` 1);
- floor 4 → 2 reclassifies **72 (2.6%)**;
- floor 4 → 1 reclassifies **339 (12%)** — and 267 of those 339 are one-cell changes, which is the
  cursor-blink population the floor exists to exclude in the first place;
- floor 4 → 5 demotes **26 steps, every one of them on `tn36`**, which is a banked click win. The one place
  the floor is tightly binding is *underneath a win*, in the upward direction.

**So the smallness floor is not where the silence comes from.** No reachable setting of `MIN_CELLS` turns a
frozen game responsive, because the games that are silent are silent at exactly zero cells, not at three.

## The cross-check, which is why the table above may be cited

The histogram is written at the same site as the four literals but into a different structure, so they are
independent counters of the same steps. They close exactly:

```
hist[0]        == still + band_only ==  491 + 765 == 1256
hist[1..3]     == sub_floor         ==             339
hist[>=4]      == live              ==  27 + 1177 == 1204
sum(hist)      == charged           ==            2799
```

A charge that reached one site and not the other would show here as a number that fails. It did not.

## What this instrument does NOT resolve, and must not be read as resolving

1. **`hist[0]` pools `still` with `band_only`.** The histogram alone cannot tell a board that did nothing
   from a board where only the clock ticked; that split lives in `board_section` and is 491 / 765.
2. **`live` is now visibly a pooled population, and a wildly heterogeneous one.** The per-game `live` maxima
   include `lp85` 1409, `tn36` 2518 and `m0r0` 2708 on a 4096-cell board — a third to two-thirds of every
   cell changing in one step. That is not an avatar moving four cells; it is a scene replacement (a level
   redraw, a restart, a menu). `live` therefore pools "the puzzle answered" with "the screen was replaced",
   and every rate built on it inherits that. This is the same defect as `mean_masked_cells`, one level up
   again, and it is the FIRST thing this instrument found that nobody was looking for.
3. **Nothing here licenses moving the floor.** The detector taxonomy is frozen and this is a readout: it is
   written at one site, read only by `board_report` and the sweep printer, and
   `test_the_histogram_is_a_readout_and_no_decision_reads_it` fails if any decision module imports it.

## Coverage, stated rather than implied

24 games carried a row. **`sc25-635fd71a` carried none: its RESET returned HTTP 400 and it never played.**
It is absent from every number above, including the denominator. `total_levels: 3`, `advances: 3`,
`CLEARED: 0` — unchanged, and the chain still does not clear.

## How to overturn this

1. A sweep on a DIFFERENT game set whose 1–3 cell column is large. The claim is about this population of 24
   games; the bimodality is not a law.
2. A cold-bank run (`.residual_bank/` deleted) that shows a materially different distribution — this arm was
   warm and says so.
3. A game where `frozen` flips on a floor change: that is the direct refutation, and the table above says it
   would need the floor at 1, where the instrument is measuring cursor blinks.
