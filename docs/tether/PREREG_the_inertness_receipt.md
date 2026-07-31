# PRE-REGISTRATION — the inertness receipt (arm N)

**Written and pushed BEFORE arm N opens, at the commit that adds the instrument. Branch `redux-triality`. The
predecessor of this file is `PREREG_the_death_board.md`, pushed at `658f04d` before arm M, and it is the pattern this
one follows: the predictions are on the record before the run can move them.**

## What was added, and why it is not a new organ

`ChainLedger.note_board(kind, cells, banded)` / `note_board_skip(kind)`, called once per observed frame from
`ReduxPolicy._note_board_response`, which is called from `observe` immediately after `engage.observe`. The reading is
`_change_reading` — the SAME implementation the priced decide column already uses, not a second one that could drift
from it. `EngagementMeter.report()` prints state the organ has held since the day it shipped and has never surfaced.

No detector, no `_find_*`, no new referent kind, no new relation: **the taxonomy freeze holds.** Nothing about the
agent's behaviour changed, and the §XIX key and the death memory were not touched.

Why the charge is taken at the frame and not read off the existing per-exit column: `_price_pending_exit` answers
"did the board answer THIS EXIT", drops the frames no exit chose, and is pooled across games in the printer. The
question CLASSIFIER 13 leaves open is about the AGENT over a whole episode on ONE game. Summing exit buckets to
answer it would be a pooled number offered as evidence about a subset — the defect the discipline names by name.

## The literals, and what each one means

Every observed frame lands in exactly one of these, charged at the site that read the two boards:

`still` (the new frame is pixel-identical to its predecessor) · `band_only` (something changed and ALL of it was
inside the monotone budget/timer band — the clock ticked, the puzzle did not) · `sub_floor` (change outside the band,
below the smallness floor) · `live` (the board answered outside the band, at or above the floor) · `reshape` (the
board changed shape; an answer with no comparable cell count, so it enters no mean). Frames that are not the agent's
doing are charged to `board_skip` under `no_predecessor` / `label_reset` / `label_none` / `label_unknown` — excluded
from the rates BY NAME, never dropped.

## Self-checks. If any of these fails, nothing downstream may be cited.

**S1 — the instrument reads only.** Arm N runs the same roster, WARM bank, and must reproduce arm M digit for digit:
`TOTAL steps=2959 decide=2939 retries=20 | BUDGET RESIDUE=0`, 23 deaths / 15 games / 20 earned / 3 refused, roster
digest `793049198616`. A different total means this instrument perturbed the run and every reading below is void.

**S2 — the charge equals the action budget.** Per game, `board.steps == steps − retries` (CLASSIFIER 11's identity),
residue 0 on all 25. A non-zero residue means a frame arrived with no action behind it or an action produced no
frame; the printer stars it, and no rate in the table may be cited until it is explained.

**S3 — the two denominators close.** `board.frames == board.steps + board.skipped`, and `skip_split` is exactly
`{no_predecessor: 1, label_reset: retries}` on every game.

## Predictions about the agent, on the record before the run

**P1 — `sp80-589a99af` is INERT.** `live` is 0, or a single-figure count out of ~90 charged steps. This is the game
whose change-map showed the agent's own cells never moving while a bar depleted across the top, and it is the
strongest leg CLASSIFIER 13 stands on. **If `sp80` comes back with a substantial live fraction, the inertness reading
is wrong, `tools/death_depth.py`'s `replay` verdict on it must be re-read as a genuine return to the same board, and
CLASSIFIER 13 loses its clearest instance.**

**P2 — `su15-1944f8ab`, `vc33-5430563c`, `s5i5-18d95033` were each played with ONE action label.** The meter's
per-action table shows exactly one key on each. Rendering showed A6 on every frame of all three. If two or more
labels appear, the render was not representative of the sweep and the one-action reading goes with it.

**P3 — a monotone band is masked on the bar games.** `band_at_step.banded > 0` on `sp80`, `tu93`, `su15`, `vc33`,
`s5i5`. All five were rendered with an edge bar that fills or depletes monotonically. **The interesting outcome is
the failure**: a game that plainly has a bar reporting `banded = 0` is a statement about the MASK, not about the
game, and the leading candidate is that `EngagementMeter._frames` is never cleared on a restart — a restart REFILLS
the bar, which breaks the non-decreasing ratchet the mask requires for up to `keep = 48` frames. That would mean an
organ built to detect a frozen board has been counting a timer as board response on exactly the games it exists for.

**P4 — `bp35-0a0ad940` is the ONE game with real live steps.** Its change-map showed a hot two-cell alcove: the
agent moves, but never leaves two cells. If `bp35` reads `live == 0`, my reading of that change-map was wrong and
must be withdrawn.

**P5 — the escalation never fired on the one-label games.** `escalations == 0` on `su15` / `vc33` / `s5i5`. If it
did fire and the label held anyway, something downstream of the organ pinned the action and the escalation is not
the lever it is documented to be.

## What this run may NOT be used for

* **`live%` is not competence.** A board that moves is not a puzzle being solved, and a `still` step is not
  necessarily a wasted one — a game may accept a press whose effect lands later.
* **No pooled inertness number about a subset.** The table is per game; the TOTAL row is the roster and nothing else.
* **No behaviour change lands in this beat.** Not the §XIX key, not the death memory, not a hazard/timeout
  distinction in the death literals, and not a reset-clear on `EngagementMeter._frames` — P3 failing is the
  measurement that would motivate that fix, which is exactly why the fix may not ship in the beat that measures it.
* **`band_cells` in the meter report is the mask AS OF THE LAST FRAME**, recomputed from a sliding window. Only
  `board_band`, charged per step, may be cited about what was masked during play.

---

## AMENDMENT — written after arm N, before arm O opens, at the commit that changes the printer

**S2 FAILED AS WRITTEN.** Arm N reported residue `−1` on 22 of the 24 games that reported, and `0` on exactly two:
`s5i5-18d95033` and `vc33-5430563c`. Those two are the only games in the run whose exit literal was a `death_*`.
Every other reporting game exited on a cap. Zero exceptions in either direction.

The cause is in `_play_policy` and is one line of control flow, not a defect in the charge: the policy observes at
the **top** of the loop. A run that leaves the loop by `break` — `WIN`, or any of the three `death_*` literals — has
already observed the frame it is breaking on, so every one of its actions is charged. A run that leaves by falling
out of the `while` **condition** never observes the frame its last action produced, so exactly one action is
uncharged. The corrected identity is therefore

> `board.steps == steps − retries − tail`, where `tail = 1` if the exit literal is `action_cap` / `wall_cap` /
> `action_and_wall_cap` / `loop_exit_unattributed`, `0` if it is `WIN` or `death_*`, and **undefined** for an
> `open_error:*` / `error:*` game, which reached no exit and is given no number at all.

**This rule is FITTED, not predicted.** It was derived from the arm N failure it explains and is therefore not
evidence about itself. It is printed as its own `tail` column rather than folded into `resid`, because a correction
absorbed silently is how a receipt stops being able to fail, and `tools/sweep_chain.py::observed_tail` names the
fall-through literals explicitly so that a fall-through `return` added later and not registered here reads `?` and
forfeits its residue instead of quietly borrowing a `1`.

**S2′ — THE OUT-OF-SAMPLE TEST, on the record before arm O opens.** On arm O, every reporting game shows
`resid = 0` under the corrected identity, and the `tail` column equals `1` on every cap-exit game and `0` on every
`death_*`/`WIN` game — **with the branch assignment made by the literal alone, before the residue is looked at.**
A single game where a `death_*` exit needs a tail of 1, or a cap exit needs 0, falsifies the control-flow
explanation above and sends the whole board table back to unreadable. `tests/test_board_response.py` pins both
branches synthetically; arm O is where the rule meets data it was not fitted to.

**What arm O may NOT be used for.** It is a re-run of the same roster with the same agent code — the ONLY changes
since arm N are in the printer and in tests. It is therefore a reproduction check on the arm N readings and a test
of S2′, and it is **not** a second sample about the agent: two runs of one build on one roster do not average into
a stronger claim about behaviour. Nothing about `_modality_escalate`, the native-click escalation guard, the §XIX
key, the death memory, or `EngagementMeter._frames` changes in this arm.
