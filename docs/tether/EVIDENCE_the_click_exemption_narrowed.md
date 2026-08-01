# EVIDENCE — narrowing the click organ's exemption (arms P and Q at `26cce47`)

Scored against `PREREG_the_click_exemption_narrowed.md`, whose commit `26cce47` is the SAME commit that
carries both arms and was pushed to `redux-triality` before either arm opened a scorecard.

    ARM P  (CONTROL)    NEWHORSE_CLICK_EXEMPT=broad   https://arcprize.org/scorecards/621afdcb-046b-4592-b059-0e9aba104972
    ARM Q  (TREATMENT)  default = narrow              https://arcprize.org/scorecards/04db42d6-f6a9-4555-b6b3-b6c70346e4e3

Two games (`su15-1944f8ab`, `tn36-ef4dde99`), `120 200`, roster digest `a79e9bb17f83`, same commit.
**BOTH ARMS WARM.** `.residual_bank/` (15 files) was snapshotted before arm P and restored before arm Q;
`diff -r` reported the restored bank byte-identical to the snapshot. No chain count below is compared
across arms without that sentence.

---

## 1. The control reproduced the prior sweep BYTE-FOR-BYTE, and that is the most useful thing in this file

Arm P's board-response rows are character-identical to arm O's, taken eight days and one code change earlier:

    game               family        charged tail  resid  still   band    sub    live  live%   skip  banded frozen/esc
    su15-1944f8ab      click             115    0      0     19     70     20       6     5%      3      91 Y/0     <- arm O AND arm P
    tn36-ef4dde99      click             118    1      0      0     31     57      30    25%      2      78 Y/0     <- arm O AND arm P AND arm Q

Same for both meters (`su15` A6 n=115 mean=1.27 best=20.0; `tn36` A6 n=118 mean=24.72 best=2518.0) and both
funnels (`click_native` = 100% of decisions on both games, every other literal 0).

**This was not predicted and it changes what the arms are worth.** Every prior arm on this project has been
read with "the environment is stochastic" as a standing excuse for any difference under ~10%. On these two
games it is not: three independent sweeps on three different days returned identical step counts, identical
death boards, identical changed-cell histograms. So a difference between arm P and arm Q on these games is
**attributable to the switch**, and does not need a repeat to be believed. It also means the reverse: any
FUTURE difference on `tn36` is a regression and cannot be waved off as noise.

Caveat with teeth: this is a determinism receipt for THESE TWO GAMES at this budget, not for the roster. It
says nothing about the 23 games arm P and Q dropped.

## 2. The fork resolved: su15 advertises A7, tn36 is click-only

The prereg named both branches in advance because arm O's record could not tell "never offered" from
"offered and never selected". Arm Q answers it:

    su15-1944f8ab   escalate|A7  12 steps   -> its advertised set contains a non-click action
    tn36-ef4dde99   click_native 119 steps  -> its advertised set is click-only

## 3. Predictions, scored

**P-1 CONFIRMED.** Arm P: `click_native` 234 steps = 100.0% of 234 decisions across 2 games. `escalate`,
`escalate_click`, `family_click`, `family_fallback` all 0.

**P-2 CONFIRMED.** `frozen/esc` reads `Y/0` on both games; both appear in the ONE-action-label table with
`A6` alone.

**P-3 CONFIRMED.** `escalate steps=0 | step-branch sum=0 | RESIDUE=0`, verdict `MUTE`. `hold_answered`
rendered nowhere — the retired-branch tripwire did not fire.

**Q-1 CONFIRMED on su15, exactly as written.** `click_native` is **0** on `su15` — not reduced, zero, for
118 decisions. Every non-escalated click step landed on the new `family_click` literal (106 steps) and the
escalation took 12. `106 + 12 = 118 = decide_calls`, funnel RESIDUE 0. `n_modality_escalations` = 1
(`frozen/esc` = `Y/1`). The meter now carries two labels and `su15` consequently DROPPED OUT of the
one-action-label table. The escalation was BOUNDED and handed the game back: `new 1 + hold_untried 11 = 12`
steps, then `family_click` resumed.

**Q-3 / Q-4 CONFIRMED on tn36. THE KILL CONDITION DID NOT FIRE.** `tn36` is exit-for-exit identical between
arms: `click_native` 119, `family_click` 0, `escalate` 0, board-response row identical, meter identical,
`advances` 1 preserved, `maxL` 1 preserved. The narrowing did not leak past its own precondition.

**Chain identical across arms.** Both: `advances 1`, `{MINT_UNFIRED 1, RESIDUAL_EMPTY 3, REUSE_UNWIRED 1}`,
`break_events 6`, `minted 1`, `fired 0`, **`CLEARED 0`**.

## 4. THE PRE-REGISTERED +0 WAS WRONG, AND IT WAS WRONG IN THE CONTROL TOO

§6 of the prereg predicted `advances 0` and `total_levels 0` on both games on both arms. **Both arms
returned `advances 1` and `total_levels 1`**, from `tn36`, which reaches level 1.

This is not the intervention doing anything. Arm O's own banked row said `tn36 ... maxL 1 ... adv 1` and I
mis-read it while writing the prereg. The failure is a READING failure in a document whose entire purpose is
to be un-revisable afterwards, so it is recorded here rather than quietly corrected there. The rule it
earns: **a pre-registered baseline number must be pasted from the capture file, not typed from memory of
it.**

The +0 that DID hold, and the one that mattered: `CLEARED` is **0** on both arms. This change won nothing.

## 5. What the agent actually did with its new capacity: nothing, and the nothing is informative

`escalate|A7` on `su15`: **12 steps, 0.0% masked, 0.0% raw, 0.0 cells mean, 0 cells max.** A7 moved not one
cell, ever. The agent gained the ability to try an action it had been offered for the whole project and had
never once tried, tried it for the bounded 12 steps the fair-trial window allows, got literally nothing, and
handed the game back to the click organ. That is the organ working as designed.

**Do not report the death-count change as a benefit.** Arm P `su15`: 117 steps, 3 deaths, closed
`death_no_new_cause`. Arm Q `su15`: 120 steps, 2 deaths, closed `action_cap`. The death BOARDS are the same
two in both arms (`bea16f73e85c`, `215b73c40473`); arm P's third death was a REPEAT of the second, which is
what tripped the no-new-cause terminal. In arm Q the 12 inert A7 steps displaced 12 A6 steps and pushed that
third repeat past the 120-action budget. **That is a scheduling difference, not a learning difference**, and
`maxL` stayed 0 on `su15` in both arms.

The A6 behaviour itself was preserved, which is the check that says the displacement was clean: `su15`'s A6
answer rate held at 5.4% (6 of 112 priced) in arm P versus 5.8% (6 of 103 priced) in arm Q — the same six
answering steps, a smaller denominator.

## 6. CLASSIFIER 18 — the self-motion control splits by EXIT before it splits by ACTION, so it cannot see a contrast it was built to find

Before this change `su15` had exactly one action for its whole history, and the self-motion control said so
honestly: *"MUTE: one action only -- the split cannot vary, so it rules nothing out."* After this change
`su15` has **two** actions with sharply different answer rates — A6 at 5.8% (n=103) and A7 at 0.0% (n=12) —
which is precisely the contrast the control exists to detect. The control still prints MUTE **twice**:

    family_click  ... su15  A6   5.8%(n=103,cells 1.4)   -> MUTE: one action only
    escalate      ... su15  A7   0.0%(n=12, cells 0.0)   -> MUTE: one action only

It groups by EXIT LITERAL first and by ACTION second, so a game whose two actions arrive through two
different exits reads as two one-action games. The question the control asks is *"did the AGENT move the
board, or does the board move anyway?"* — that question's denominator is the GAME, not the exit.

This is the pooled/subset defect one level down: a SUBSET number standing where the per-game number is what
answers the question. **Not fixed this beat** — the rule is that a fix does not ship in the same beat as the
measurement that motivated it. It is the head of NEXT.

## 7. How to overturn each claim here

- **The determinism receipt (§1).** Run arm P again. If `su15`'s row is not `115 0 0 19 70 20 6 5% 3 91`,
  the environment is not deterministic on these games and every attribution in §5 needs a repeat.
- **Q-1.** Re-read arm Q's `DECIDE FUNNEL` per game. If `su15` charges any `click_native`, the exemption is
  being evaluated somewhere other than at every decision.
- **Q-4 / the kill condition.** Diff arm P's and arm Q's `tn36` rows. Any difference at all reverts the
  change; there is no version of this that is patched instead.
- **§5's "scheduling, not learning".** Read the death boards. If arm Q's deaths are on DIFFERENT boards than
  arm P's, the agent reached somewhere new and the framing here is too harsh.
- **CLASSIFIER 18.** Read the control's grouping in `tools/sweep_chain.py`. If it already pools by game
  before it splits by action, the MUTE verdicts above have some other cause and this classifier is wrong.
