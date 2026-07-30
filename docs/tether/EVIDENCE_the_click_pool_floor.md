# EVIDENCE — the click pool floor

**Banked 2026-07-30. Evidence, not a conclusion. Nothing in the agent was changed by the work in this document;
the only code that landed with it is instrumentation.**

## The question this replaces

`tools/sweep_chain.py` has carried a pre-registered prediction since the click branch was first instrumented:

> `untried_first` DOMINATES. `refresh()` folds freshly-perceived candidates in at every step, so on a board that
> changes the untried queue can be replenished faster than it drains — the agent would enumerate forever and its
> learned scores would never be consulted.

Seven sweeps returned the same shape and the printer banked `PREDICTION HELD`. On sweep G:

```
untried_first              steps    1342 ( 96.3% of click steps)
exploit_scored             steps      51 (  3.7% of click steps)
nothing_moved_least_tried  steps       0 (  0.0% of click steps)
no_targets                 steps       0 (  0.0% of click steps)
  click steps=1393 | branch sum=1393 | RESIDUE=0
```

**What the sweep confirmed is the RATE. It never touched the MECHANISM.** The rate 96.3% is consistent with
`refresh()` replenishing the queue and equally consistent with several other causes; the receipt cannot tell them
apart, so under RANKING 5 (*no receipt ⇒ no diagnosis*) the mechanism clause was never evidence. It was prose
bridging a gap. `PREDICTION HELD` was a mis-labelled receipt: the printer evaluated a claim about a rate and
printed a verdict about a cause.

**Denominator correction, carried into this document.** `claude/HEARTBEAT.md` cites the click branch against
1335 steps. 1335 is `click_native` ALONE. The branch denominator is `click_native + escalate_click` = **1393**;
`_act_click` is reached from both exits and calls `ClickProber.choose` exactly once per call. Every percentage
below is against 1393.

## The rival reading — a code fact crossed with a receipt

`ReduxPolicy._new_prober` is the only place a prober is built:

```python
return ClickProber(click_targets(grid), grid_sweep(grid, n=8), branch=..., pool=...)
```

`grid_sweep(grid, n=8)` is a **64-point lattice**, passed **unconditionally**, on every prober ever constructed.
`click.py`'s own module docstring describes that lattice as *"a coarse grid sweep as a **fallback** when the frame
has too few components."* **The documented design and the wired design disagree, and the wired design is what
runs.** A documented fallback is being paid as a mandatory enumeration tax on every click game.

The tax binds because of a second code fact in `ClickProber.choose`:

```python
untried = [t for t in self.targets if self.tries[t] == 0]
if untried:
    pick = untried[0]          # ← admission order
```

`choose` cannot leave the untried branch until **every** target has `tries >= 1`, and it drains `self.targets` in
**admission order** — perceptual centroids first, then lattice points, then anything `refresh()` appends. So:

1. The construction pool size is a **hard floor** on how many click steps must be spent enumerating.
2. `refresh()`-admitted targets sit at the END of the list and **cannot be reached at all** until the entire
   construction pool has been drained. Refresh can only ever explain the *residual headroom*, never the floor.

Pool size per prober is between **64** (every perceptual centroid collides with a lattice point) and **88**
(24 centroids + 64 lattice, no collisions).

## The bound

Per-game click steps, parsed from `decide_funnel_by_game` in the saved sweep-G capture with a brace-depth walk
plus `json.loads` (PATTERN 07-30f(c): parse the structure, never regex the rendering of the structure) —
15 games, 1393 steps:

```
ft09 120 · lp85 120 · r11l 119 · tn36 119 · su15 118 · lf52 107 · s5i5 100 · vc33 100
sb26  96 · sc25  96 · cd82  95 · bp35  90 · cn04  90 · sp80  12 · ka59  11
```

Forced-untried floor = `sum over games of min(click_steps, pool)`:

| pool | forced floor | % of 1393 | ceiling for `exploit_scored` | steps NOT forced | of those, still untried |
|------|--------------|-----------|------------------------------|------------------|-------------------------|
| 64   | 855          | 61.4%     | 38.6%                        | 538              | 487 (90.5%)             |
| 88   | 1167         | 83.8%     | 16.2%                        | 226              | 175 (77.4%)             |

Games that cannot reach `exploit_scored` **even in principle** (click_steps ≤ pool): **ka59 and sp80**, at both
pool sizes — 2 of 15.

**This is a floor on the floor.** `_reparameterize` rebuilds the prober on a level advance, and each rebuild
re-imposes a fresh construction pool. The table computes the bound per *game*; per *prober* it can only be
larger. Rebuilds cannot lower these numbers.

## What this establishes, and what it does not

**Establishes:** between 61.4% and 83.8% of every click step the agent takes is forced into the untried branch by
the CONSTRUCTION POOL alone. No change to `refresh()` can touch those steps. The queued intervention ("bound
`refresh()` so the untried queue can drain") therefore has a hard, pre-computable ceiling: at best it moves
`untried_*` from 96.3% down to 61.4–83.8% and `exploit_scored` up to 16.2–38.6%. In the residual headroom that
`refresh` could in principle explain, 77–90% of steps still went untried.

**Does not establish:** which of the two pool sizes is actual, how many probers were built, how many targets
`refresh` admitted, or how the untried steps actually split between the lattice and perception. Those are the
inferred quantities this beat converts into direct receipts — see below.

**Does not establish** anything about whether bounding the lattice would be an IMPROVEMENT. `exploit_scored` is
not a good in itself; the agent's answer rate is. The region-answer pair (sweep G: 15.9% masked / 65.2% raw over
13 games; sweep F: 17.0% / 62.3% over 12) is the control that must not fall, and raising `exploit_scored` while
that pair drops is a loss.

## The instrument shipped with this document

Counted at the real call sites (RANKING 1), changing nothing about which target is chosen:

- **`ClickProber.origin`** records each target's provenance **at admission** — `perceptual` and `sweep` in
  `__init__`, `refresh` in `refresh()`. Admission is the only place provenance is knowable.
- **`untried_first` is retired** and resolves into three returns with three literals: `untried_perceptual`,
  `untried_sweep`, `untried_refresh`. The migration is named in the printer, which also prints their sum as
  `untried_* TOTAL` so the old series stays comparable. The identity
  `click_native + escalate_click == sum(click_branch)` is unchanged and `click_branch_residue` still publishes it.
- **`click_pool`** is a NEW dict on its own denominator — ADMISSIONS, not steps, which is why it is separate from
  the branch split rather than folded into a sum that is an identity against the click exits. Keys:
  `ctor_probers`, `ctor_perceptual`, `ctor_sweep`, `ctor_targets`, `refresh_calls`, `refresh_admitted`. Its own
  identity `ctor_targets == ctor_perceptual + ctor_sweep` is published as `click_pool_ctor_residue`, so a lattice
  point that collided with a centroid shows as a de-dup instead of a double count.
- **Per-game click-branch rows** are now printed. The split was POOLED-only, and a pooled number offered as
  evidence about a subset is the mis-labelled-receipt defect one level up. The per-game carry already existed as
  a sibling of `decide_funnel` (`decide_funnel_by_game`); the printer reads it rather than adding a second
  traversal that could drift from the pooler.

## Pre-registration for the next sweep at this commit

Written **before** any sweep has run against this instrument. The printer evaluates it; the prose does not.

- **A.** `untried_perceptual + untried_sweep` ≥ 50% of click steps, and `untried_sweep` > `untried_perceptual`.
  Point estimate from the bound: the construction pair lands in **855–1167 of ~1393** (61.4%–83.8%).
- **B.** `untried_refresh` ≤ 40% of click steps.
- **C.** `click_pool.ctor_targets / ctor_probers` lands in **[64, 88]**. Outside that range, the pool model in
  this document is wrong and everything above must be re-derived before it is cited.
- **D.** `ka59` and `sp80` show `exploit_scored == 0` in the per-game rows.
- **Control:** the region-answer pair does not move. It is not touched by an instrument.

## Overturn conditions

- **The bound is overturned** if `untried_refresh` exceeds `untried_perceptual + untried_sweep`. That would
  reinstate the replenishment reading and this document's arithmetic would be wrong.
- **The pool model is overturned** if `click_pool_ctor_residue` is non-zero, or if targets-per-prober falls
  outside [64, 88].
- **The diagnosis is overturned** — the docstring/call-site disagreement stops being the story — if
  `untried_sweep` is small relative to `untried_perceptual`. Then perception is offering enough points to fill
  the enumeration on its own and the lattice is not the tax.

## What is NOT authorised by this document

The fix. `grid_sweep` is still passed unconditionally, and it stays that way until a beat that is not this one.
DISCIPLINE: *do not build a fix in the same beat as the measurement that motivated it.* The fix, when it comes,
must predict **both** the branch split and the region-answer pair in advance, and must be measured against a
sweep taken at this commit with this instrument — not against sweep G, which does not have these rows.
