# PRE-REGISTRATION — the mask after a restart (arms P-control and P-treatment)

**Written and pushed BEFORE either arm opens, at the commit that carries the change. Branch `redux-triality`. The
predecessor is `PREREG_the_inertness_receipt.md`, pushed before arm N, and this one follows the same rule: the
predictions are on the record before a run can move them. The control-arm switch follows the
`PREREG_the_lattice_held.md` / `NEWHORSE_CLICK_LATTICE` pattern exactly.**

## The defect this is a fix for, stated as it was measured

`monotone_band_mask` qualifies an edge band only if the count of its cells differing from the FIRST retained frame is
NON-DECREASING across the whole retained history — a ratchet, because a budget readout only ever runs one way. A
restart REFILLS the timer bar. The count falls. No band qualifies. For up to `keep = 48` frames after every earned
reset the mask is empty, and in that stretch the bar's own tick is charged as the board ANSWERING the agent.

Arm O's board table is what put this on the record, and the shape of it is hard to read any other way. On five games
with an edge bar, `banded` stops almost exactly where the first earned reset lands:

| game | charged | first EARNED RESET | `banded` (arm O) | retries |
|---|---|---|---|---|
| `sp80-589a99af` | 116 | @31 | 23 | 3 |
| `bp35-0a0ad940` | 117 | @17 | 30 | 2 |
| `tu93-0768757b` | 117 | @51 | 42 | 2 |
| `s5i5-18d95033` | 100 | @51 | 42 | 1 |
| `vc33-5430563c` | 100 | @51 | 42 | 1 |
| `su15-1944f8ab` | 115 | @52 | 41 | 2 |

That is the correlation the fix predicts and it is why the fix is worth running. It is NOT itself proof: `banded`
and the reset step could both be downstream of something else about these games, which is what the arms are for.

## The change, in one sentence, and what it deliberately does not touch

`EngagementMeter.note_restart()` drops `_frames` and `_mask`; `ReduxPolicy.note_reset` calls it. `_resp` (per-action
response) and `_recent` (the frozen-test window) are **not** cleared — a restart is not evidence that a dead modality
woke up, and re-arming `frozen()` after every death would be a second change nothing has measured. One change per arm.

**This is an AGENT-BEHAVIOUR change, not an instrument.** The mask feeds `frozen()`, `escalate()`, `is_null()` and the
two `engage.mask()` reads inside `_act_directional`. Every reading below must be read as a reading about a run, not
about a frame.

## How to run the control

`NEWHORSE_MASK_RESET=keep` restores the pre-2026-07-31 behaviour EXACTLY — `note_restart` returns immediately and the
call site is the only line that differs. `clear` is the shipped default. Nothing in the agent reads the switch; only
`EngagementMeter.note_restart` does, once per restart. Both arms run at the SAME commit, same roster, WARM bank.

## Self-checks. If any of these fails, nothing downstream may be cited.

**S1 — the switch is inert where it cannot fire.** Nine games took ZERO retries in arm O (`dc22`, `ft09`, `g50t`,
`lp85`, `ls20`, `m0r0`, `sb26`, `sk48`, `tr87`). `note_restart` is never called on them, so the two arms execute the
same code on the same frames. Their board rows must reproduce **cell for cell** across the two arms. A difference on
a zero-retry game means the arms differ by something other than this change and the whole comparison is void.

**S2 — the budget still closes.** `decide_exits == steps − retries`, residue 0 on every reporting game, in BOTH arms.

**S3 — the denominators still close.** `board.frames == board.steps + board.skipped`, and `skip_split` is exactly
`{no_predecessor: 1, label_reset: retries}` on every game, in BOTH arms.

## The offline contrast — the leg with no confound in it, and the one that decides the diagnosis

The live arms cannot give a clean per-frame contrast: once the mask changes, the agent's choices change, so the two
arms are not looking at the same boards. So the CONTROL arm's own recordings are replayed through both meters
offline, frame for frame, with no agent in the loop:

> For each of the five bar games, feed the control arm's recorded frame sequence (including its restart frames) into
> two `EngagementMeter`s, one at `keep` and one at `clear`, and count the steps at which `mask().any()` is True.

**P0 — on IDENTICAL frames, `clear` masks a band on strictly more steps than `keep`, on every one of the five.** This
is the prediction that carries the diagnosis, because nothing else varies between the two counts. **If P0 fails, the
ratchet break is not what is blinding the mask, the diagnosis in CLASSIFIER-13's neighbourhood is wrong, and the live
arms may not be cited for anything.** This test is registered here as the primary one; the live arms are secondary.

## Predictions about the agent, on the record before either arm opens

**P1 — `banded` RISES on all five bar games.** `banded(treatment) > banded(control)` on `sp80`, `tu93`, `s5i5`,
`vc33`, `bp35`, and by at least **+15 steps** on each. This is HEARTBEAT's named falsifier: *if `banded` does not rise
on those five, the ratchet is not what is blinding the mask and the diagnosis is wrong.*

**P2 — the zero-retry games do not move at all.** Restated from S1 as a prediction because the +0 is the point: nine
games change by nothing, and that is the arm's own control against drift.

**P3 — `live` FALLS and `band_only` RISES on the five, roughly trading one for the other.** `live%` on `sp80` falls
from 39% to below 30%. The bar's tick stops being counted as an answer, which is the entire mechanism.

**P4 — the agent's read of itself gets MORE pessimistic, not less.** Games reporting `frozen=True` at end of run does
not fall, and `escalations` on the five does not fall. **The direction is predicted deliberately: this fix should
make the agent look WORSE off, because it removes a false signal of progress.** A treatment arm that reports a
cheerier board than the control is evidence the change did the opposite of what it was built to do.

**P5 — no level and no win moves, on any game.** `levels_completed` is unchanged on all 25. **Published in advance as
a +0.** This fix removes a lie from an instrument the agent reads; it does not teach the agent anything. If a level
appears, it is a single sample from a diverged trajectory and it is NOT evidence that the mask fix caused it.

## What this run may NOT be used for

- It may **not** be used to claim the band mask is now correct. It removes ONE known cause of blindness. `sb26` and
  `sk48` report `banded = 0` with zero retries, so at least one other cause of `banded = 0` exists and is untouched.
- It may **not** be used as evidence about competence. `live%` is not competence — four games answer on 100% of
  actions and win nothing — and neither is `banded`.
- It may **not** be used to attribute any change in `steps`, `deaths`, `outcome` or level to the mask on a game whose
  trajectory diverged, without the offline contrast to separate the frame reading from the run.
- A rise in `banded` on a game with ZERO retries in the treatment arm would mean the two arms differ by something
  other than this change; it must be reported as a failed S1, not as a bigger effect.

## The named alternative, if P0 holds and P1 fails

Then the ratchet break IS blinding the mask on identical frames, but the restart is not where the live agent loses it
— for example the bar's refill is slow enough that the band never re-reaches `min_fill` before the run ends. That is
a statement about `min_fill` and `keep`, not about the reset, and it would be the next thing measured. Recording it
here so the fallback is not invented after the numbers arrive.

---

## AMENDMENT — written after the OFFLINE CONTRAST and the CONTROL arm, BEFORE the treatment arm opens

The control arm (`NEWHORSE_MASK_RESET=keep`, scorecard `62011900-836d-4d4e-9762-e5c764ec3f63`, roster digest
`793049198616`, `TOTAL steps=2959 decide=2939 retries=20 | BUDGET RESIDUE=0`) reproduced arm O cell for cell on all
24 games arm O reported, and `wa30-ee6fef47` opened this time, so all 25 report. S1/S2/S3 hold.

**P0 PASSED, and by a wide margin.** On identical frames, with no agent in the loop:

| game | frames | charged | `banded` keep | `banded` clear | `live` keep | `live` clear | `band_only` keep | `band_only` clear |
|---|---|---|---|---|---|---|---|---|
| `bp35` | 121 | 118 | 30 | 81 | 23 | 23 | 18 | 65 |
| `s5i5` | 102 | 100 | 42 | 76 | 4 | 4 | 42 | 76 |
| `sp80` | 121 | 117 | 23 | 89 | 45 | 45 | 16 | 64 |
| `su15` | 118 | 115 | 41 | 91 | 6 | 6 | 20 | 70 |
| `tu93` | 121 | 118 | 42 | 82 | 3 | 3 | 41 | 81 |
| `vc33` | 102 | 100 | 42 | 76 | 2 | 2 | 42 | 76 |

The `keep` column reproduces the live control arm's own `banded` column exactly on all six, which is what licenses
reading anything off this replay at all.

**And P3 is ALREADY FALSIFIED, before the treatment arm opens.** `live` does not move by a single step on any of the
six. The bar's tick is 1–3 cells — BELOW `MIN_CELLS = 4` — so a blinded mask was never turning a bar tick into an
`live`. What it was doing was moving steps between `band_only` and `sub_floor`, two literals that are both below the
floor. **The defect is real and it is large as an instrument defect; its consequence for anything the agent READS is
not established and now looks likely to be nil**, because `frozen()` tests `max(_recent) < MIN_CELLS` against the
same floor these steps were already under.

So the treatment arm is now a test of a NARROWER and more falsifiable claim, registered here before it runs:

**P6 — the treatment arm reproduces the control arm CELL FOR CELL in the budget table** (`steps`, `decide`,
`retries`, `deaths`, `outcome`) on all 25 games, and `live` / `live%` / `frozen` / `escalations` are unchanged on all
25. Only `banded`, `band_only` and `sub` move, and they move as the offline table above says. **This is the +0 being
published in advance: the honest expectation is now that this fix changes what the receipt SAYS and changes nothing
the agent DOES.** If instead any game's `steps`, `deaths` or `outcome` moves, the mask does reach a decision by a
route I have not found, and that route must be located and named before anything else is claimed.

P1 stands as written and is expected to pass. P4 is superseded by P6. P5 stands.
