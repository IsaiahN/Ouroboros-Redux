# EVIDENCE — the lattice released (arms I and J)

Scores `PREREG_the_lattice_held.md`, which was committed in `1f9af2e` **before either arm ran**. Read that
file first; it states what was believed beforehand, which is the only thing that makes this one worth
anything. Read `EVIDENCE_the_pool_floor_measured.md` for the baseline (sweep H at `67e8d8a`).

## The two runs

    commit (both arms)   1f9af2e   -- one commit, two wirings, nothing else differs
    ARM I (control)      NEWHORSE_CLICK_LATTICE=eager   scorecard 03795bf4-3248-4f99-acd9-7709fc13ac3f
                         capture /tmp/armI_eager.txt (6262 lines, whole report, never truncated)
    ARM J (treatment)    default = reserve              scorecard 6d23b0fd-a1bc-49c2-8a52-b7ea6bbfb35b
                         capture /tmp/armJ_reserve.txt (6284 lines, whole report, never truncated)
    residual bank        WARM (14 files) at arm I launch; arm J ran after arm I deposited into it.
                         ⇒ NO chain-stage, `fired`, `mint` or `resid` count may be compared across the
                         two arms. This is a click-branch experiment; the chain columns are along for
                         the ride and are NOT evidence here. Pre-registered as such.

## Arm I reproduced sweep H to the digit — the switch is a clean control

    decide() calls               2943   (sweep H: 2943)   exits 2943, UNCOUNTED 0, RESIDUE 0
    click_native / escalate_click 1335 / 58              denominator 1393
    branch split         untried_perceptual 304 · untried_sweep 827 · untried_reserve 0 ·
                         untried_refresh 211 · exploit_scored 51 · nothing_moved 0 · no_targets 0
    pool                 ctor_probers 17 · ctor_targets 1402 (82.5/prober) · ctor_reserved 0 ·
                         refresh admitted 978 (r11l 561) · click_pool_ctor_residue 0
    region pair          15.9% masked / 65.2% raw of 1312 priced over 13 games
    per-game click       identical to sweep H, game for game

Every one of those equals sweep H. **PREDICTION I-1 HELD.** The `LATTICE_ADMISSION` switch changes nothing
when set to `eager`, so arm J's deltas are attributable to the wiring and not to the four counters added
alongside it. This is also the ELEVENTH sweep to reproduce `decide_calls=2943` and the per-game action
vector on the games that played — and it did so on a bank one sweep warmer than sweep H's, which is fresh
evidence that the click branch is bank-independent.

## ★ ONE GAME DID NOT PLAY IN ARM J, AND IT ACCOUNTS FOR ALMOST THE WHOLE `decide_calls` DELTA

`tn36-ef4dde99` returned `400 Bad Request` on `RESET` in **BOTH** arms. Arm I recovered after three
attempts and played it; arm J retried seven times and gave up, so arm J is a **24-game / 14-clicking-game**
sweep and tn36 is scored `error` with no receipt. This is infrastructure, not the intervention, and it is
the reason every pooled comparison below is recomputed on the **12-game / 14-game INTERSECTION** rather
than on the printed pooled rows. A pooled number offered as evidence about a subset is a mis-labelled
receipt one level up — so the printed `15.9% / 24.6%` headline pair is NOT the comparison, and the
intersection pair further down is.

    decide_calls   2943 (arm I)  ->  2820 (arm J)   delta -123
    attributed     tn36 not played          -119   (its only exit was click_native)
                   su15 click steps 118->115  -3
                   sc25 click steps  84-> 83  -1
                   every other exit           +0   dir_target_colour 626, dir_relation_drive 342,
                                                   family_effect 226, family_two_body 115,
                                                   dir_explore 99, warmup 76, escalate 66,
                                                   escalate_click 58 — identical in both arms

**PREDICTION J-7 IS VIOLATED, AND 119 OF THE 123 IS A MISSING GAME.** The residual is FOUR steps on two
games. `maxL` did not move on either (su15 0, sc25 0 in both arms), so it is not a level advance. Four
steps is small, but `decide_calls` has reproduced EXACTLY on eleven prior sweeps and has never moved by a
non-zero amount before, so this is banked as an open audit item and NOT waved through as noise. It is
listed in §Audit below.

## The branch split, on the 14-game intersection

Arm I recomputed with tn36 removed; arm J as printed. Denominators 1274 and 1270 click steps.

                              ARM I (eager)          ARM J (reserve)
    untried_perceptual         270  (21.2%)           277  (21.8%)
    untried_sweep              764  (60.0%)             0  ( 0.0%)   <- J-1 HELD, exactly
    untried_reserve              0  ( 0.0%)            63  ( 5.0%)
    untried_refresh            199  (15.6%)           498  (39.2%)
    exploit_scored              41  ( 3.2%)           432  (34.0%)
    nothing_moved_least_tried    0                      0
    no_targets                   0                      0
    untried_* TOTAL           1233  (96.8%)           838  (66.0%)
    games reaching exploit     5 of 14                10 of 14

    pool: ctor_probers 15 (both, on the intersection) | ctor_targets 1402->277 (82.5 -> 18.5 per prober)
          ctor_reserved 0 -> 950 | reserve_admitted 0 -> 63 | click_pool_ctor_residue 0 in BOTH arms
          refresh admitted 978 -> 815 (r11l 561 -> 381)

**`exploit_scored` went from 41 steps to 432 — a 10.5x rise, from 3.2% to 34.0% of click steps, and from
5 of 14 games to 10 of 14.** That is above the 400-step ceiling the pre-registration set as the point at
which an attribution is owed, so here it is: the mechanism is the queue length and nothing else. `choose()`
cannot leave the untried branch until every admitted target has `tries >= 1`; the construction pool fell
from 1402 admissions to 277 while the DRAIN stayed at 100.0% in both arms on every game that played. The
agent did not become better at clicking. It stopped being made to spend its whole action budget
enumerating points nobody proposed. Every remaining step went somewhere the receipt can name.

## THE PAIR — the prediction that could have sunk the beat

Recomputed on the 12 games priced in BOTH arms (tn36 removed from arm I):

                        masked        raw       priced
    ARM I (eager)       14.98%      61.84%       1195
    ARM J (reserve)     24.62%      72.94%       1190
                        +9.6 pts    +11.1 pts

**PREDICTION J-8 HELD, and with room.** The bar was masked >= 15.0% and raw >= 63.0%; both rose well past
it. The intervention did not trade answer quality for branch reach — it raised both. Per game, the masked
rate rose on lp85 (5.9 -> 30.3), sb26 (21.8 -> 90.8), sc25 (14.5 -> 58.0), cn04 (2.4 -> 4.7), r11l
(73.5 -> 74.4) and fell on cd82 (3.4 -> 1.1), lf52 (2.9 -> 1.9), s5i5 (6.1 -> 4.1), su15 (12.2 -> 5.4);
ft09, vc33 and bp35 are unchanged. Games at >= 50% masked went from 1 to 3.

## Every pre-registered prediction, scored

    I-1  arm I reproduces sweep H on every click row              HELD, to the digit
    J-1  untried_sweep -> 0 exactly                               HELD (0)
    J-2  ctor_targets leaves [64,88] per prober BY DESIGN;
         click_pool_ctor_residue stays 0                          HELD (18.5/prober; residue 0 both arms)
    J-3  reserve_admitted <= ctor_reserved                        HELD (63 <= 950; no IDENTITY BROKEN line)
    J-4  untried_* total stays > 60%; refresh >= 400 steps;
         perceptual roughly flat at 250-350                       HELD (66.0%; 498; 277)
    J-5  exploit_scored >= 120 steps AND >= 8 of 15 games         HELD (432 steps, 10 of 14 games) —
                                                                  above the 400 ceiling, attributed above
    J-6  reserve_promotions_empty >= 1 AND
         reserve_promotions_inert >= 1                            ★ HALF FAILED. inert = 1 (ft09, 63 points
                                                                  admitted, 63 steps taken on them).
                                                                  empty = 0 on all 15 probers.
    J-7  decide_calls stays 2943 and the per-game vector
         stays identical                                          ★ VIOLATED. -123, of which -119 is a game
                                                                  that never played. -4 is unexplained.
    J-8  masked >= 15.0% AND raw >= 63.0%  (THE PAIR)             HELD (24.62% / 72.94%)

### J-6 is the honest miss, and it is worth more than the hits

Condition (1) — "perception proposed NOTHING" — **never fired on any of the 15 probers built in arm J.**
Perception offered between 8 and 24 centroids on every single one. So the `empty` promotion is real,
synthetically tested, and load-bearing as a capability guard, but this sweep provides **no live evidence
that it is ever needed**. It must not be cited as part of why the intervention worked. The whole live
effect came from one thing: not admitting the lattice.

Condition (2) fired **once**, on ft09, and it fired correctly: every perceptual and refresh target had
been clicked at least once and none of them had moved the board, so the lattice was promoted and ft09
spent 63 steps on it — 5.0% of all click steps in the sweep. That is the 64-point fallback being paid at
the price it was designed to cost, on the one game that needed it, instead of on all fifteen.

## What did NOT improve, and why the beat does not claim it did

- **No game cleared a level that did not clear one before.** `total_levels` fell 3 -> 2, and that is tn36
  not playing. `CLEARED` is still 0. The detector-taxonomy freeze still holds.
- **bp35 and r11l still reach `exploit_scored` zero times.** Their tax simply moved from the lattice to
  the refresh queue: bp35 spent 66 of 90 steps on refresh arrivals (79 admitted), r11l 95 of 119 (381
  admitted). The blind lattice was never r11l's problem. **The next floor is the refresh queue, and it is
  a DIFFERENT mechanism** — `refresh()` folds newly-perceived points in with no cap and no score.
- **ka59 and sp80 still take 11 and 12 click steps.** As sweep H already said, the pool was never their
  problem; they stop clicking almost immediately.
- **The chain is not evidence here** and no chain row from either arm is cited anywhere in this document.

## Audit items this sweep opened

  a. **The 4-step `decide_calls` residual** (su15 -3, sc25 -1) with `maxL` unmoved in both arms. First
     non-zero move in `decide_calls` across twelve sweeps. Needs its own attribution before CLASSIFIER 7
     is cited again.
  b. **`tn36` `RESET` returns 400 on both arms** and recovered on only one. The retry behaviour differs
     run to run, so any two sweeps may silently compare different game sets. The sweep should refuse a
     pooled cross-run comparison when the game sets differ, in the printer, rather than in a doc.
  c. **`reserve_promotions_empty` has no live firing.** Either construct a game where perception proposes
     nothing, or record that the guard is untested live.
  d. **The refresh queue is the new floor** (39.2% of click steps, 815 admissions, 61.1% drain). It is an
     uncapped, unscored admission path. This is the natural successor question and it is a DIFFERENT
     mechanism from the one this beat closed — do not build it in the same beat as this measurement.

## How to overturn

`NEWHORSE_CLICK_LATTICE=eager` at any commit from `1f9af2e` forward restores the pre-07-31 wiring exactly.
A cold `.residual_bank/` fires the reuse chain zero times and makes the chain columns incomparable to
either arm here.
