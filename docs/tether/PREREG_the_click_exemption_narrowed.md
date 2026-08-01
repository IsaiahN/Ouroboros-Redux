# PRE-REGISTRATION — narrowing the click organ's exemption from modality escalation (arms P and Q)

**This file is written and COMMITTED BEFORE EITHER ARM RUNS.** That is its entire purpose. Git history is
what makes it evidence rather than a story told afterwards; if this file's commit is not an ancestor of the
commit that carries the arm receipts, throw it away and re-run.

Companion to `EVIDENCE_the_guard_behind_the_guard.md` (CLASSIFIER 16, the refuted reachability arm) and
`EVIDENCE_the_floor_priced.md` (CLASSIFIER 17, the bimodal changed-cell distribution). Everything below is
scored against **arm O at `37ed9d2`**, the 25-game warm-bank sweep on scorecard
`b126d739-6a3c-4580-b638-2801efe13bb6`.

---

## 1. The defect, in one paragraph

On a natively-routed click game the agent is **structurally incapable of ever trying anything but a click**,
however long the board has been dead and however many actions the game advertises that it has never once
tried. `_decide`'s second statement was `if self.family == CLICK and self._pre_esc_family is None: return
self._exit("click_native", self._act_click())`, and `_modality_escalate`'s first guard was a byte-for-byte
copy of the same expression. CLASSIFIER 16 established that the state is ABSORBING — the only non-`None`
assignment to `_pre_esc_family` lives downstream of the second guard — so the game can never leave. In arm O
this was not a corner case. `su15-1944f8ab` took **115 of 115** decisions at `click_native` and
`tn36-ef4dde99` took **119 of 119**: not one other exit literal was charged on either game for the whole
episode, while both meters read `frozen=True` and `resp_frac=0.00`.

This is a statement about AFFORDANCES, not about any game. A board that has been frozen for a full window
while an action the game itself offers has never been tried is not a board any organ can be said to own.

## 2. What changed, exactly

Four edits in `src/newhorse/redux_arch/policy.py` and one retirement:

1. `CLICK_EXEMPT = (os.environ.get("NEWHORSE_CLICK_EXEMPT") or "narrow").strip().lower()` — read ONCE at
   module import, never by a decision function. Same pattern as `click.py`'s `LATTICE_ADMISSION` and
   `engagement.py`'s `MASK_ON_RESTART`. Nothing in the agent reads it; it is not a tuning knob.
2. `_click_organ_exempt()` — THE ONE definition, called from BOTH former guard sites. Under `broad` it is
   the old expression verbatim. Under `narrow` it additionally requires `not [a for a in self._avail if
   int(a) != 6]` — the exemption holds only while the game's advertised action set offers no non-click
   alternative.
3. A new `family_click` dispatch arm in `_decide`, ahead of `family_fallback`. **This is not cosmetic.** The
   `click_native` early return was the CLICK family's ONLY dispatch; narrowing the guard without this arm
   would have dropped non-exempt click games into `_act_fallback`, a far larger behaviour change that would
   then have been read as the exemption's doing. Its own literal at its own return, so the funnel can say
   which of the two paths answered.
4. `_modality_escalate`'s A6 `hold_answered` exception RETIRED, replaced by `released_answered`. This was
   forced by the change and the forcing is worth recording: the A6 hold was only ever defensible because a
   committed click game was caught by `click_native` before reaching the organ, so it could be charged at
   most once. With the exemption narrowed the game DOES come back, and holding would pin `_escalated` at
   `"A6"` for the rest of the episode — a second absorbing state of exactly the kind CLASSIFIER 16 was
   about. Verified equivalent at the ACTION level: the held return produced `escalate_click` →
   `self._act_click()`; the release returns `None`, `_decide` falls through to the CLICK dispatch and calls
   **the same `_act_click()`**. Same call, same action; only the literal that counts the step differs.

**A design that was considered and REFUTED before it was written**, recorded here because the refutation is
the reusable part: the second arm of the exemption was nearly `self.engage.answered("A6")`. That is
CLASSIFIER 15 walking back in. `answered()` reads the ALL-TIME `best`; `frozen()` reads a MAX over the
RECENT window. `su15`'s `best("A6")` is 20.0 — comfortably over `MIN_CELLS = 4` — while its meter reads
`frozen=True`. The exemption would have held on the one game it was written for and the intervention would
have shipped as a silent no-op. **Measure the defect at the site of the read.**

## 3. The two arms

    ARM P  (CONTROL)    NEWHORSE_CLICK_EXEMPT=broad    PYTHONPATH=src python3.12 tools/sweep_chain.py 120 200 su15,tn36
    ARM Q  (TREATMENT)  (default = narrow)             PYTHONPATH=src python3.12 tools/sweep_chain.py 120 200 su15,tn36

Same commit, same two games, same budget, both captured whole to a file. **Two games, not twenty-five**,
because the ranking says AIM THE FIRST FIRING AT THE CHEAPEST INSTANCE: these are the only two click-family
games in arm O whose every decision was `click_native`, so they are where the guard binds and everything
else on the roster is wall clock spent to learn nothing. `tools/sweep_chain.py` gained an optional third
positional argument for this; it is a ROSTER filter read in the launcher, never inside the agent, and a
subset sweep prints `★ SUBSET SWEEP` and names every id it kept and the count it dropped.

**BANK STATE.** `.residual_bank/` is snapshotted before arm P and RESTORED before arm Q, so both arms open
on byte-identical persistent state. Say it in every citation: **both arms WARM, restored to the same
snapshot.** No `fired` or chain-stage count may be compared across the arms without that sentence.

**THE CONTROL IS ACTION-IDENTICAL, NOT LABEL-IDENTICAL, TO ARM O.** Edit 4 changes one exit literal on the
step where an escalation to A6 commits: arm O would charge `escalate_click`, arm P charges the CLICK
dispatch. On THIS roster the difference is provably nil — both games had `escalate_click == 0` in arm O —
but the claim "the control restores the old code EXACTLY" is false in general and is not made here.

## 4. Predictions — arm P (the control)

**P-1. Both games stay 100% `click_native`.** `click_native` equals `decide_calls` on `su15` and on `tn36`;
`escalate`, `escalate_click`, `family_click`, `family_fallback` are all **0** on both. Step counts will not
match arm O exactly — the environment is stochastic and arm O's `su15` RESET took an HTTP 400 retry — so the
prediction is on the exit SHAPE, not on 115 and 119.

**P-2. `n_modality_escalations == 0` on both games**, and each meter carries exactly one label, `A6`.

**P-3. `_esc_branch` is empty on both games.** `hold_answered` must be 0 — it is a retired branch and the
printer now renders it as `★ RETIRED BRANCH CHARGED` rather than as a statistic.

If P-1 fails the control is not the old code and nothing downstream may be cited.

## 5. Predictions — arm Q (the treatment)

Arm Q is also the ONLY evidence for which action set each game advertises. Arm O's banked record cannot
answer it: `A7` appears in arm O for `sb26` alone, and a label absent from a meter is equally consistent
with "never offered" and "offered and never selected". So the two games are pre-registered as a **fork with
both branches named in advance**, and whichever branch fires, it fires as a prediction and not as a
post-hoc reading.

**Q-1 (su15, IF its advertised set contains a non-click action).** `click_native == 0` for the entire
episode — not reduced, ZERO, because the exemption is evaluated fresh at every decision and the untried
action never leaves the advertised set. Every non-escalated click step lands on `family_click`.
`n_modality_escalations >= 1`. The meter carries at least two labels. The escalation is BOUNDED and hands
the game back: `family_click > 0` after the trial, and the emitted sequence ends on `A6`.

**Q-2 (su15, IF its advertised set is click-only).** Bit-identical to arm P. The intervention is a no-op on
this game and the finding is that it binds on neither of the two cheapest instances — which is a real
result and gets published as one, not quietly dropped in favour of a third game.

**Q-3 (tn36).** Same fork, same two branches, scored independently. Arm O's `tn36` row is the banked-win
neighbourhood this change must not disturb.

**Q-4. THE KILL CONDITION.** On any game whose advertised set is click-only, arm Q must be **exit-for-exit
identical** to arm P. A single `family_click` or `escalate` charge on a click-only game means the
narrowing leaks past its own precondition and the change is reverted, not patched.

## 6. The +0, published in advance

**This change is NOT predicted to win anything.** `CLEARED` is predicted to remain **0** on both arms.
`advances` is predicted to remain **0** on both games on both arms (in arm O `su15` closed
`death_no_new_cause` and `tn36` closed `action_cap`; neither advanced a level). `total_levels` is predicted
to be **0** on both arms.

That is the honest expectation and it is written down before the measurement so it cannot be revised
afterwards. What this change buys is not a level. It is that the agent stops being **structurally unable**
to try an action it has been offered and has never used, on a board that has been dead for a full window.
Whether that capacity is ever worth a level is a later question and a different arm; a capacity is not a
result, and the arms below will not be reported as one.

## 7. How to overturn each claim

- **The defect.** Re-read `policy.py` at `37ed9d2`. If `_decide`'s guard and `_modality_escalate`'s guard
  are not the same expression, or if `_pre_esc_family` has a non-`None` assignment reachable without
  passing the second guard, CLASSIFIER 16 is wrong and so is this.
- **"It binds on su15 and tn36."** Read `decide_funnel_by_game` in arm O's capture. If either game charges
  any literal other than `click_native`, the guard was not the only thing holding it and the cheapest
  instance was chosen wrong.
- **The refuted `answered("A6")` design.** Read arm O's one-label meter table. If `su15`'s `best` is below
  `MIN_CELLS` while `frozen` is True, `answered()` would have worked and the CLASSIFIER-15 objection does
  not apply.
- **The action-level equivalence of edit 4.** Read the two returns. If `hold_answered`'s label ever routed
  to anything other than `_act_click()`, the release changes actions and not only literals, and the control
  arm is not a control.
- **The +0.** If either arm returns `CLEARED > 0` or `advances > 0`, this section was wrong. Say so in the
  EVIDENCE doc in its own sentence rather than reporting the win as the intended outcome.
