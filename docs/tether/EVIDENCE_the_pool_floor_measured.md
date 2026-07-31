# EVIDENCE — the click pool floor, MEASURED (sweep H)

Companion to `EVIDENCE_the_click_pool_floor.md`, which bounded this OFFLINE and pre-registered four
predictions. This file banks the LIVE receipt that scores them. Read that file first; it states what was
believed before this sweep ran, which is the only thing that makes this one worth anything.

## The run

    commit at launch   67e8d8a  (the printer extension in this beat landed AFTER the sweep; the agent
                                 code that produced every number below is exactly 67e8d8a)
    invocation         PYTHONPATH=src python3.12 tools/sweep_chain.py 120 200
    games              25 launched, 25 completed, family=error 0
    residual bank      WARM — 14 files present at launch (cd82 cn04 ft09 ka59 lp85 ls20 re86 sb26 sc25
                       sk48 sp80 su15 tu93 wa30). Every `fired` count below is a WARM count.
    capture            /tmp/sweepH_0731.txt (6050 lines, whole report, never truncated)

## The control first, because it is what licenses the rest

The instrument added in `67e8d8a` writes three literals at admission and six pool counters. If it also
changed what the agent DID, none of the rows below would be about the agent. It did not:

    decide() calls                    2943    (sweep G: 2943)
    exits counted                     2943    RESIDUE 0, UNCOUNTED 0
    click_native steps                1335    (sweep G: 1335)
    escalate_click steps                58    (sweep G: 58)
    click_native answer rate     15.9% masked / 65.2% raw of 1312 priced, 13 games   (sweep G: identical)
    per-game click vector        ft09 120 · lp85 120 · r11l 119 · tn36 119 · su15 118 · lf52 107 ·
                                 s5i5 100 · vc33 100 · sb26 96 · sc25 96 · cd82 95 · bp35 90 ·
                                 cn04 90 · sp80 12 · ka59 11     (sweep G: identical, game for game)

This is the +0 and it is published as such. The instrument is a pure observer on every row for which a
sweep-G number exists. It is also the tenth sweep to reproduce the same per-game action vector, which is
CLASSIFIER 7 holding again: the ACTION budget binds, the wall clock does not.

## The four pre-registered predictions, scored

    A.  untried_perceptual + untried_sweep >= 50% of click steps,
        and untried_sweep > untried_perceptual
        ⇒ HELD.  304 (21.8%) + 827 (59.4%) = 1131 of 1393 = 81.2%; 827 > 304.
        The offline band was [855, 1167] steps. The live figure 1131 is INSIDE it.

    B.  untried_refresh <= 40% of click steps
        ⇒ HELD.  211 steps = 15.1%.

    C.  ctor_targets / ctor_probers in [64, 88]
        ⇒ HELD.  1402 / 17 = 82.5 pooled, and EVERY per-game per-prober value is in [72.0, 88.0].
        click_pool_ctor_residue = 0: the two origins sum to the targets admitted, so the origin tags
        on the untried rows are readable.

    D.  ka59 and sp80 show exploit_scored == 0
        ⇒ HELD, but not for the reason the prediction gave. Both are 0. The prediction reasoned that
        those games "cannot reach exploit_scored even in principle" because their click budget is
        smaller than the pool. The receipt says something narrower and better: ka59 spent 11 of 74
        admitted construction targets (14.9%) and sp80 spent 12 of 72 (16.7%). They do not fail to
        reach the exploit branch because the pool is large; they fail because they stop clicking
        almost immediately. The pool is not their problem and this beat should not claim it is.

    CONTROL.  the region-answer pair must not move  ⇒ HELD, to the digit (see above).

The full branch split, on the STEP denominator (click steps = click_native + escalate_click = 1393):

    untried_perceptual          304   21.8%
    untried_sweep               827   59.4%
    untried_refresh             211   15.1%
    exploit_scored               51    3.7%
    nothing_moved_least_tried      0    0.0%
    no_targets                     0    0.0%
    untried_* TOTAL             1342   96.3%      branch sum 1393, RESIDUE 0

## The mechanism, on the ADMISSIONS denominator

This is the part the offline bound could not supply and the part PATTERN 07-30g demanded. A rate over
STEPS can be right about the SIZE of a cost and say nothing about its CAUSE. The ordering claim — that
`choose` drains `self.targets` in admission order, so refresh arrivals are unreachable until the
construction pool is spent — lives on a different denominator entirely: targets ADMITTED.

Computed offline from the sweep's own `decide_funnel_by_game` JSON by brace-depth walk + `json.loads`
(PATTERN 07-30f(c)); the printer emits these rows natively from the next sweep on.

    game        probers  ctor perc + sweep = targets  per-prober | refresh calls / admitted | ctor drain  refresh drain
    bp35              1     24     64       88         88.0      |    89 /  79              100.0%          2.5%   full
    cd82              1     12     63       75         75.0      |    94 /  35              100.0%         57.1%   full
    cn04              1      8     64       72         72.0      |    89 /  33              100.0%         54.5%   full
    ft09              1     24     63       87         87.0      |   119 /  20              100.0%        100.0%   full
    ka59              1     10     64       74         74.0      |    10 /   6               14.9%          0.0%
    lf52              1     24     62       86         86.0      |   106 /  40              100.0%         52.5%   full
    lp85              2     48    124      172         86.0      |   119 /  14               59.3%        100.0%
    r11l              1     24     64       88         88.0      |   118 / 561              100.0%          5.5%   full
    s5i5              1     21     64       85         85.0      |    99 /  58              100.0%         25.9%   full
    sb26              1     20     62       82         82.0      |    95 /   4              100.0%        100.0%   full
    sc25              1     21     64       85         85.0      |    95 /  10              100.0%        100.0%   full
    sp80              1      8     64       72         72.0      |    11 /  17               16.7%          0.0%
    su15              1     24     64       88         88.0      |   117 /  17              100.0%        100.0%   full
    tn36              2     48    127      175         87.5      |   118 /  26               55.4%         46.2%
    vc33              1      9     64       73         73.0      |    99 /  58              100.0%         46.6%   full
    TOTAL            17          1402                  82.5      |  1378 / 978               80.7%         21.6%

ELEVEN OF FIFTEEN GAMES SPENT THEIR ENTIRE CONSTRUCTION POOL. In each of those eleven, every target
admitted at construction was clicked exactly once before any refresh arrival was choosable. That is not
a rate that is consistent with the ordering; it is the ordering, observed, per game, on a denominator
the branch split does not share.

The four that did not: ka59 (14.9%) and sp80 (16.7%) stopped clicking long before the pool ran out, and
lp85 (59.3%) and tn36 (55.4%) each built TWO probers — the grid changed under them and construction ran
again, refilling the pool with a second lattice. This is why the offline point estimate at pool 82.5 was
1095.5 forced steps and the live figure is 1131: rebuilds only ever raise the floor, exactly as the
bound said they would.

The starvation, stated plainly: 978 refresh targets were admitted across the sweep and 211 were ever
chosen — 21.6%, against 80.7% for construction admissions. r11l is the extreme: `refresh` admitted 561
further targets and 31 of them were reached (5.5%). bp35 admitted 79 and reached 2 (2.5%). The arrivals
are there. They are simply behind a queue that the lattice fills first.

## What this establishes

1. The queued intervention was aimed at the wrong thing. Bounding `refresh()` addresses 15.1% of click
   steps. The unconditional `grid_sweep(grid, n=8)` at the single construction site accounts for 59.4%
   directly and gates the rest by sitting ahead of them in `targets`.
2. `exploit_scored` — the only branch that uses anything the click policy LEARNED — took 51 of 1393
   steps, 3.7%, and reached it in only 6 of 15 games. The learned scores are not wrong; they are
   starved of turns.
3. The mechanism claim is now measured, not inferred. Prediction A was already confirmed at the rate on
   seven prior sweeps under the old `untried_first` name; what was missing was any receipt on the
   admissions denominator. It exists now, per game.

## What this does NOT establish

- That bounding the lattice would raise the ANSWER rate. Nothing here says a click chosen by a learned
  score answers more often than a lattice point. The region control is flat and stays flat.
- That 64 is the wrong `n`. The receipt indicts the word UNCONDITIONAL in `click.py`'s call site, not
  the size of the lattice. A conditional 64-point fallback and an unconditional one are different
  mechanisms with the same constant.
- Anything about the 10 games that took no click step at all.
- Anything about CLEARED, which is still 0 on this sweep as on the nine before it. The detector
  taxonomy freeze holds.

## What is NOT authorised by this document

The fix. DISCIPLINE forbids building it in the beat that measured it. When it is built it must, BEFORE
running, predict both the branch split and the region-answer pair, and it must be measured against THIS
sweep — sweep H at `67e8d8a` — not against sweep G, which has no pool rows. Do not repair the
`click.py` docstring or the call site before then: the disagreement between them is the finding.

## How to overturn this

- A sweep where `untried_refresh` exceeds `untried_perceptual + untried_sweep` reinstates the
  replenishment reading and this document is wrong.
- A non-zero `click_pool_ctor_residue`, or a per-prober `ctor_targets` outside [64, 88], means a target
  was admitted without an origin and no untried row may be read.
- A sweep in which NO game spends its construction pool has not observed the ordering at all; the
  printer now says so in those words rather than letting the pooled split stand in for the mechanism.
