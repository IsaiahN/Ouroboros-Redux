# EVIDENCE — the mask after a restart (offline contrast + arms P-control and P-treatment)

**Companion to `PREREG_the_mask_after_restart.md`, which was pushed — with its amendment — before the arm it grades.
Every verdict below is against a prediction that was on the record first. Read the prereg first; this file only
grades it.**

| | |
|---|---|
| commit both arms ran at | `b44190f` (identical; the only difference is `NEWHORSE_MASK_RESET`) |
| roster digest | `793049198616` (both arms) |
| control arm (`keep` = pre-2026-07-31 wiring) | scorecard `62011900-836d-4d4e-9762-e5c764ec3f63` |
| treatment arm (`clear` = shipped default) | scorecard `f4fbbb9b-ea73-4940-8f7e-240928811d3e` |
| budget, both arms | `TOTAL steps=2959 decide=2939 retries=20 | BUDGET RESIDUE=0`, 25 reporting |

---

## The self-checks. All three hold, in both arms.

**S1 — the switch is inert where it cannot fire. PASSED.** Ten games took ZERO retries in both arms — `dc22`, `ft09`,
`g50t`, `lp85`, `ls20`, `m0r0`, `sb26`, `sk48`, `tr87`, `wa30`. `note_restart` is never called on them, so the two
arms execute the same code on the same frames, and every board column reproduces **cell for cell**. Not one
zero-retry game moved, which is the arm's own control against drift.

Three games that DID take a retry also did not move (`cd82`, `ka59`, `re86`, one retry each). That is not a failure —
a restart only blinds the mask if a band was qualifying before it — but it does mean "has a retry" is not sufficient,
and any future claim of the form "every restart blinds the mask" is already contradicted by these three rows.

**S2 — the budget closes. PASSED.** `decide_exits == steps − retries`, residue 0 on every reporting game, both arms,
and the two TOTAL lines are byte-identical.

**S3 — the denominators close. PASSED.** `board.frames == board.steps + board.skipped` and
`skip_split == {no_predecessor: 1, label_reset: retries}` on every game in both arms.

---

## P0 — the offline contrast. **PASSED**, and it is the only leg with no confound in it.

`tools/replay_mask.py` feeds ONE recorded frame sequence to two `EngagementMeter`s, `keep` and `clear`, with no agent
in the loop. Same frames, same order, same restarts, one difference. Six games from the CONTROL arm's own recordings:

| game | frames | charged | `banded` keep | `banded` clear | `live` keep | `live` clear | `band_only` keep | `band_only` clear |
|---|---|---|---|---|---|---|---|---|
| `bp35` | 121 | 118 | 30 | 81 | 23 | 23 | 18 | 65 |
| `s5i5` | 102 | 100 | 42 | 76 | 4 | 4 | 42 | 76 |
| `sp80` | 121 | 117 | 23 | 89 | 45 | 45 | 16 | 64 |
| `su15` | 118 | 115 | 41 | 91 | 6 | 6 | 20 | 70 |
| `tu93` | 121 | 118 | 42 | 82 | 3 | 3 | 41 | 81 |
| `vc33` | 102 | 100 | 42 | 76 | 2 | 2 | 42 | 76 |
| **TOTAL** | | | **220** | **495** | | | | |

**+275 masked steps on frames that did not change.** The `keep` column reproduces the live control arm's own `banded`
column exactly on all six — that agreement is what licenses reading anything off this replay at all, and it is the
check that would have caught a replay drifting from what the policy actually saw.

**The defect is real, it is large, and it is an INSTRUMENT defect.** The ratchet in `monotone_band_mask` is broken by
a restart's refill; dropping the frame history restores it.

---

## P1 — `banded` rises on all five named bar games. **PASSED.**

HEARTBEAT's own falsifier, named in advance: *if `banded` does not rise on `sp80`/`tu93`/`s5i5`/`vc33`/`bp35`, the
ratchet is not what is blinding the mask and this diagnosis is wrong.* The bar was ≥ +15 on each.

| game | `banded` control | `banded` treatment | delta |
|---|---|---|---|
| `sp80-589a99af` | 23 | 88 | **+65** |
| `su15-1944f8ab` | 41 | 91 | +50 |
| `tu93-0768757b` | 42 | 81 | +39 |
| `s5i5-18d95033` | 42 | 76 | +34 |
| `vc33-5430563c` | 42 | 76 | +34 |
| `bp35-0a0ad940` | 30 | 80 | +50 |

Seven further games moved that were not named in advance (`ar25` 57→87, `cn04` 39→46, `lf52` 57→88, `r11l` 58→90,
`sc25` 71→85, `tn36` 63→78). Twelve of twenty-five games moved; thirteen board rows are byte-identical.

## P2 — the zero-retry games do not move. **PASSED.** See S1.

## P3 — `live` falls and `band_only` rises. **FAILED — and the failure was published BEFORE the treatment arm ran.**

`live` did not move by a single step, on any game, in either the offline replay or the live arms. Roster-wide `live`
is **1263 (43%) in both arms**, and every per-game `live` and `live%` cell is identical.

The reason, found in the offline replay and recorded in the prereg amendment: **the bar's tick is 1–3 cells, below
`MIN_CELLS = 4`.** A blinded mask was never turning a bar tick into a `live` step. What it was doing was shuffling
steps between `band_only` and `sub_floor` — two literals that are *both already under the floor*. Roster-wide:

```
band_only  448 -> 765     (+317)
sub_floor  663 -> 346     (-317)
still      543 -> 543     live 1263 -> 1263     charged 2917     skip 45
```

The `+317` and the `−317` are the same steps, and they never crossed the floor in either direction.

## P4 — superseded by P6 before the arm ran.

## P5 — no level and no win moves. **PASSED, +0 published in advance.** `levels_completed` unchanged on all 25.

## P6 — the treatment arm reproduces the control arm cell for cell in the budget table, and `live` / `live%` / `frozen` / `escalations` are unchanged. **PASSED, exactly.**

```
=== BUDGET: rows that DIFFER ===   NONE — all 25 rows identical (steps, decide, retries, deaths, resid, outcome)
=== maxL rows that DIFFER ===      NONE
=== BOARD: columns that DIFFER === only `band`, `sub`, `banded`, on 12 of 25 games
    escalate steps=124 in BOTH arms; released=10 in BOTH arms; frozen/esc column identical on all 25
```

---

## The classifier this earns

> **CLASSIFIER 15 — the band mask is blinded by a restart's refill, and mending it changes nothing the agent does,
> because the bar ticks below the same floor the decision reads.**
>
> The blindness is real and large (+275 masked steps on identical frames). But `frozen()` tests
> `max(_recent) < MIN_CELLS` and `is_null`/`answered` test `best(label) < MIN_CELLS` — **maxima**, not means. The
> steps the mask was failing to mask were 1–3-cell bar ticks, already under that floor. Un-masking them moved the
> mean and could never move the max. A fix to a mean is invisible to a predicate that reads a max.

The per-action table shows the mean moving and the max standing still, on the same run:

| game | `mean` control | `mean` treatment | `best` control | `best` treatment | `frozen` |
|---|---|---|---|---|---|
| `s5i5` A6 | 1.14 | 0.70 | 12.0 | 12.0 | True → True |
| `su15` A6 | 2.14 | 1.27 | 20.0 | 20.0 | True → True |
| `vc33` A6 | 6.02 | 5.58 | 265.0 | 265.0 | True → True |
| `tn36` A6 | 24.85 | 24.72 | 2518.0 | 2518.0 | True → True |
| `r11l` A6 | 52.40 | 52.11 | 121.0 | 121.0 | False → False |

**HOW TO OVERTURN.** Either (a) exhibit a game whose edge bar ticks **≥ 4 cells per step**, where the mask's blindness
would cross the floor and reach a decision, or (b) exhibit any single game where the two arms differ in `live`,
`frozen`, `escalations`, `steps`, `deaths` or `outcome`. Neither exists in this roster. A third route: change any
predicate that currently reads a MAX to read a mean or a fraction — `responsive_fraction()` already exists and reads
means, and nothing in `_decide` consults it. If it ever does, this classifier expires and the fix acquires teeth.

## What NEXT-1c answered, from these receipts, with no new code

**The depleting row IS in the frame the policy sees.** From the control arm's recordings: one full-width row at row 0
(`sp80`, `vc33`) or row 63 (`tu93`, `bp35`, `s5i5`, `su15`), 64 of 4096 cells, filling 0→64 across the first segment,
1–3 cells per step. `bp35`'s mask additionally grabs two full columns (190/4096) — that is a plausible OVER-mask, a
border frame rather than a bar, and it is recorded here as a caveat, not measured.

## What these arms may NOT be used for

- Not evidence the band mask is now **correct**. One known cause of blindness is removed. `sb26` and `sk48` report
  `banded = 0` with zero retries, so at least one other cause exists and is untouched.
- Not evidence about **competence**. `live%` is not competence: four games answer on 100% of actions and win nothing.
- Not evidence that the fix is **worthless**. It removes a false statement from an instrument that other work will
  read. It is worthless *to the current decision path*, which is a narrower and reversible claim.
- The unnamed seven games that moved in P1 were **not predicted**; they are consistent with the mechanism but they
  are not a test of it, and they must not be cited as one.
