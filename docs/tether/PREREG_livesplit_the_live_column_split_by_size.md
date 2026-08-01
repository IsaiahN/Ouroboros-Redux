# PREREG — arm S: the `live` column split by SIZE

**Provenance, stated first because last beat's prereg could not.** This document was written BEFORE arm S was
launched. Nothing below is read off arm S output. The point predictions in §3 are derived from an *already published*
and *independent* instrument — the floor histogram printed by arm R (`/tmp/armR_classifier18.txt`, capture
2026-08-01 ~04:34) — and that derivation is shown in full so it can be checked rather than trusted.

## 1. What is being measured, and what is NOT

`live` is one of four literals that partition every frame the agent's own action produced: `still` / `band_only` /
`sub_floor` / `live`. It means *the board answered outside the monotone budget band, at or above the smallness floor
`MIN_CELLS = 4`.*

On a 4096-cell board, arm O and arm R record `live` **maxima** of 1409 (`lp85`), 2518 (`tn36`) and 2708 (`m0r0`) —
between a third and two thirds of every cell on the screen. A puzzle answering one action does not repaint two
thirds of the screen. A level redraw does; so does a restart, and so does a menu. So `live` pools two populations,
and every rate built on it — including `live%`, which HEARTBEAT already forbids reading as competence — is a POOLED
number offered as evidence about a SUBSET, which is the defect this project's discipline names one level up.

**This arm changes nothing about what counts as answered.** `MIN_CELLS` is untouched, the four literals are
untouched, no detector is added, no referent kind is added, and the freeze in HEARTBEAT ranking item 4 is not
crossed. The coarse `live` column is KEPT under its own name and is still the number to cite when citing `live`.
The split is printed BESIDE it as a partition, with the residue published, so the two readings must sum back or star.

**The edge is an author's choice and is treated as one.** `LIVE_REDRAW_FRAC = 0.5` is one number somebody picked. A
bucket edge picked by the author is a second floor smuggled in beside the one under test, so the ledger banks the
EXACT `(cells, area)` joint distribution of every `live` step (`live_hist`, keyed `"<cells>/<area>"`, never a
bucket): any threshold anybody later prefers is recomputable from the record without spending another sweep. The
printer additionally counts the same steps at 25% / 50% / 75% — COUNTED, NOT APPLIED, exactly as `floor_section`
counts the cells just below the smallness floor without proposing to move it.

## 2. The arm

- Games: `su15` and `tn36` — the CHEAPEST instance, not the important one, and specifically the pair the four-armed
  determinism receipt is bound to, so the control in §3 (`the coarse reading did not move`) is a character-for-character
  comparison rather than a judgement call.
- Budget: `120 200`, warm `.residual_bank/` (15 files, `diff -r` identical to `/tmp/bank_snapshot`).
- Commit: the `live`-split commit, on `redux-triality`.
- Comparison arm: **arm R**, `/tmp/armR_classifier18.txt`, same two games, same budget, same warm bank.

This arm also RE-RENDERS these two games through the CLASSIFIER-18-fixed printer. It does **not** discharge NEXT item
`1★★` — the 25-game re-render — which stays owed, because no arm-O result JSON was persisted (`sweep_chain.py` has no
JSON dump; only rendered text survives) and re-rendering the other 23 games therefore costs a live 25-game sweep.

## 3. The predictions, with their derivation

### S-1 — the identity holds. `local + redraw + unsized == live`, per game and in total, no `★` residue.

### S-2 — `live_unsized == 0` on both games.
Every frame that reaches the `live` branch has a shape, so an unsized `live` step would mean the area failed to
cross the call site — the field-never-computed defect in a brand-new column.

### S-3 — **`tn36`: `live` 30 = `local` 29 + `redraw` 1.** Point prediction, derived, falsifiable.
Arm R's floor row for `tn36`: `n=118`, histogram `0→31, 1→57, 4→26, 8+→4`, `max 2518`, `live(mean/max) 95.33/2518`,
and its one-label row gives `board_cells=4096`. So the 30 `live` steps sum to `95.33 × 30 = 2860`; 26 of them sit at
exactly 4 cells (104 cells), leaving **4** steps in the `8+` tail summing to 2756, of which one is 2518 — so the
other three sum to 238 and none of them can individually reach the 2048-cell edge. Exactly one `live` step is at or
above 50% of that board.

### S-4 — **`su15`: `live` 6 = `local` 6 + `redraw` 0.** Its `live` max is **20 cells**; no plausible board makes 20
cells half the screen. `maxfrac` for `su15` is predicted well under 25%, and all three `@` marks are 0.

### S-5 — **the coarse reading did not move.** The `su15` and `tn36` rows of `BOARD RESPONSE PER GAME` and of `THE
FLOOR, PRICED` must reproduce arm R character-for-character:
```
  su15-1944f8ab      click             117    1      0     31     60     20       6     5%      3      93 Y/1
  tn36-ef4dde99      click             118    1      0      0     31     57      30    25%      2      78 Y/0
```
This is the control on the whole change: a readout that perturbs the reading it is a readout OF is not a readout.
A differing row does not "narrow" this arm — it REVOKES both this claim and the four-armed determinism receipt, and
the split may not be cited until the difference is explained.

### S-6 — the edge demonstrably matters somewhere, or it demonstrably does not.
On these two games the `@25%` and `@75%` counts are predicted to be **1 and 0** (`tn36`) and **0 and 0** (`su15`) —
i.e. the 2518-cell step is caught by every edge below ~61% and by none above it. If `@25%` and `@75%` come back
EQUAL on both games, that is a real result and must be published as such: on this pair the split's verdict is
insensitive to the author's edge, which is a stronger statement than the split itself.

## 4. What a confirmed arm licenses, and what it does not

**Licensed:** saying, per game, how much of what `live` counted was the screen being replaced; and citing the split
in place of a bare `live` count when the distinction matters.

**NOT licensed:** treating `live_redraw` as a failure, as progress, or as a level advance — nobody has shown that a
large answer IS a redraw; the reading is that it is too large to be a puzzle answering one action, and *"too large to
be X"* is not *"is Y"*. Confirming that would need a rendered frame pair, which is item 5 of the NEXT list (LAW-0
renders) and is not this arm. Nor does a confirmed arm license moving `MIN_CELLS`, adding a detector, or changing any
decision — the split is read by `board_report` and the sweep printer and by nothing else, and
`test_the_histogram_is_a_readout_and_no_decision_reads_it` was EXTENDED (not duplicated) to make that a test failure
rather than a promise.
