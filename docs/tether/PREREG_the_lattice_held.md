# PRE-REGISTRATION — holding the blind lattice in reserve (arms I and J)

**This file is written and COMMITTED BEFORE EITHER ARM RUNS.** That is its entire purpose. Git history
is what makes it evidence rather than a story told afterwards; if this file's commit is not an ancestor
of the commit that carries the arm receipts, throw it away and re-run.

Companion to `EVIDENCE_the_click_pool_floor.md` (CLASSIFIER 8, the offline bound) and
`EVIDENCE_the_pool_floor_measured.md` (CLASSIFIER 9, the live receipt at `67e8d8a`). Read both first.
Everything below is scored against **sweep H at `67e8d8a`**, never against sweep G — sweep G has no
pool rows.

---

## 1. The old docstring text, carried forward verbatim

The intervention edits `click.py`'s module docstring, so the text it replaces is preserved here. This is
the paragraph that stood for eight sweeps:

> ★ THE DOCSTRING ABOVE AND THE CALL SITE DISAGREE, AND THE CALL SITE WINS. The text above describes
> "a coarse grid sweep as a FALLBACK when the frame has too few components"; `ReduxPolicy._new_prober`
> passes `grid_sweep(grid, n=8)` — 64 blind lattice points — UNCONDITIONALLY, on every prober ever
> built, alongside up to 24 perceptual centroids. `choose()` cannot leave its untried branch until every
> admitted target has `tries >= 1`, and it drains `self.targets` in ADMISSION ORDER. The design says
> fallback; the wiring says floor.

`EVIDENCE_the_click_pool_floor.md` carries the same text and stays the authority for the offline bound.

## 2. What changed, in one paragraph

`ClickProber.__init__` no longer admits the lattice into `self.targets`. It holds those points in
`self._reserve` and promotes them into the pool on exactly the two conditions the code's own docstrings
already name, and on no others: **(1) perception proposed nothing at construction** (`too few
components`, promoted in `__init__` with cause `empty`), and **(2) nothing perceptual ever moved the
board** (`falling back to a coarse grid sweep if nothing perceptual ever moved`, promoted at the inert
exit of `choose` with cause `inert`). `grid_sweep(grid, n=8)` is unchanged and still constructed and
still passed: sweep H indicted the word UNCONDITIONAL at a named call site, not the constant 8. No
capability is removed — every point that could have been clicked before can still be clicked. What is
removed is the ORDERING, i.e. the lattice no longer enumerates in front of the learned scores and the
refresh arrivals.

`NEWHORSE_CLICK_LATTICE=eager` restores the pre-07-31 wiring exactly, at the same commit. It exists so
the intervention can be isolated from the counters added to measure it; it is not a tuning knob and
nothing in the agent reads it.

## 3. The two arms

    ARM I  (CONTROL)    NEWHORSE_CLICK_LATTICE=eager   PYTHONPATH=src python3.12 tools/sweep_chain.py 120 200
    ARM J  (TREATMENT)  (default = reserve)            PYTHONPATH=src python3.12 tools/sweep_chain.py 120 200

Same commit, same 25 games, same budget, both captured whole to a file. The residual bank is **WARM (14
files) at launch of arm I**; arm J runs after it, on a bank arm I has deposited into, and **no `fired`
or chain-stage count may be compared across the two arms** for that reason. This is a click-branch
experiment; the chain columns are along for the ride and are not evidence here.

## 4. Predictions — arm I (the control)

**I-1. Arm I reproduces sweep H on every click row.** `decide_calls` 2943; `click_native` 1335;
`escalate_click` 58; denominator 1393; `untried_perceptual` 304, `untried_sweep` 827,
`untried_refresh` 211, `exploit_scored` 51; `ctor_probers` 17, `ctor_targets` 1402,
`click_pool_ctor_residue` 0; `ctor_reserved` **0** (nothing is held in eager mode);
`reserve_admitted` 0; `untried_reserve` 0; region pair 15.9% masked / 65.2% raw over 13 games; the
per-game click vector identical game-for-game.

If arm I does not reproduce sweep H, **the beat stops here and the rest of this file is void** — the
switch is not a clean control and arm J measures nothing.

## 5. Predictions — arm J (the treatment), against sweep H, denominator 1393

**J-1. `untried_sweep` → 0, exactly.** No construction-admitted lattice point can exist in reserve mode.
Any nonzero value is a wiring bug, not a result.

**J-2. `ctor_targets` falls out of the pre-registered [64, 88] per-prober band, ON PURPOSE.** Expect
per-prober `ctor_targets` ≈ 8–24 (perceptual only) and `ctor_reserved` ≈ 60–64. The printer's
prediction-C line will read VIOLATED and that is the intended reading, not a failure. `ctor_reserved` is
written AFTER `ctor_targets` precisely so `click_pool_ctor_residue` stays **0** in both arms; if it is
nonzero in arm J the counter placement is wrong.

**J-3. `reserve_admitted <= ctor_reserved`, always.** A held point becomes an admission only through
`_promote_reserve`. Violation ⇒ the printer prints `★ RESERVE IDENTITY BROKEN` and the arm is void.

**J-4. The honest expectation on the untried total: it stays high.** The naive reading of "81.2% of
click steps drained the pool blind" says `exploit_scored` should rise toward 80%. **It will not.** The
reason is composition: r11l alone admitted **561** refresh targets on sweep H against 211 refresh steps
chosen across all fifteen games, and eleven of fifteen clicking games spent their construction pool to
the last target. Removing 64 lattice points per prober does not remove the untried queue; it lets the
refresh arrivals — which were sitting behind the lattice — take those steps instead. **Predicted:
`untried_*` total stays above 60% of click steps, with `untried_refresh` rising to at least 400 steps
(from 211) and `untried_perceptual` roughly flat at 250–350.**

**J-5. `exploit_scored` rises, and the bar is deliberately modest.** Baseline 51 steps = 3.7%, reached
in only 6 of 15 clicking games. **Predicted: `exploit_scored` >= 120 steps (8.6%) and reached in >= 8
of 15 clicking games.** Anything at or below 51 means the reserve did not free the branch and the
intervention is a null. Anything above 400 (28.7%) means something other than the ordering changed and
must be attributed before it is claimed.

**J-6. Promotions actually happen, and the causes are separable.** Predicted `reserve_promotions_empty`
>= 1 (some frame gives perception nothing) and `reserve_promotions_inert` >= 1 (some game moves nothing).
The specific failure this prediction guards against is **the lattice being built and never promoted on
any prober**, which the printer calls out by name; that would mean the 64-point fallback is paid zero
times, which is a real result but a different one from the one predicted here.

**J-7. `decide_calls` stays 2943 and the per-game click vector stays identical.** CLASSIFIER 7 says the
ACTION budget binds. This intervention changes WHICH cell is clicked, never HOW MANY actions are spent,
so both must hold. **If `decide_calls` moves, that is the finding of the beat** and everything else in
arm J is confounded by it.

**J-8. THE PAIR — and this is the prediction that can sink the beat.** The click-region answer rate is
**15.9% masked / 65.2% raw over 13 games** at baseline. *Raising `exploit_scored` while the region rate
falls is a LOSS, and only the pair says so.* **Predicted: masked >= 15.0% AND raw >= 63.0%.** If the
region pair drops below that while `exploit_scored` rises, the correct report is that the intervention
traded answer quality for branch reach, and the shipped default must revert to `eager` pending a
better fix.

## 6. What would overturn this

Ship `NEWHORSE_CLICK_LATTICE=eager` as the default again. That is the whole of the rollback: one
environment variable, same commit, no code motion. Anyone re-running should note that a COLD
`.residual_bank/` fires the reuse chain zero times and makes the chain columns incomparable to either
arm here.
