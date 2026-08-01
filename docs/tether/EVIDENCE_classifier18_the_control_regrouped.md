# EVIDENCE — CLASSIFIER 18 fixed, scored against its own prereg at the same commit

**Arm R: `tools/sweep_chain.py 120 200 su15,tn36`, default (narrow) exemption, bank restored byte-identical to
`/tmp/bank_snapshot` so it is bank-identical to arm Q. Scorecard `6e14903b-152c-4be9-bfb7-b3a151ff1f38`.
Capture `/tmp/armR_classifier18.txt`, 675 lines.**

Read `PREREG_classifier18_the_control_regrouped.md` first, including its §1 provenance note: that document was
written while arm R was in flight but before any of its output was read, and it says so in its own header rather
than borrowing the credibility of a real pre-registration.

---

## 1. R-1, R-2, R-3 — the fix, on the instance that motivated it

Pasted from `/tmp/armR_classifier18.txt` lines 633–640:

      --- THE SAME CONTROL, GROUPED BY GAME FIRST (CLASSIFIER 18 -- the question's own denominator) ---
          su15-1944f8ab      A6   5.8%(n=103,cells  1.4)  A7   0.0%(n=12,cells  0.0)
              over 2 exit(s): escalate{A7}, family_click{A6}  ★ WIDENED -- this game's 2 actions never met
              inside ONE exit, so EVERY per-exit row above is a subset and the verdict here is the only one
              that answers the control's question
              -> UNIFORM (0.0%-5.8%) but not high -- no self-motion signature | VETO CONTROL MUTE
          tn36-ef4dde99      A6  25.6%(n=117,cells 24.9)
              over 1 exit(s): click_native{A6}
              -> MUTE: one action only -- the split cannot vary, so it rules nothing out | VETO CONTROL MUTE
          regrouped priced steps=232 | pooled action split=232 | RESIDUE=0 | games that crossed >1 exit=1 |
          games WIDENED by the regrouping=1

**R-1 CONFIRMED.** `su15` appears ONCE, with both actions, marked `★ WIDENED`, exits rendered exactly as
predicted. Where the control previously printed `MUTE: one action only` twice, it now compares A6 against A7 on
the board they were both sent to.

**R-2 CONFIRMED, and it is the unflattering reading published in advance.** `UNIFORM (0.0%-5.8%) but not high --
no self-motion signature`. Not ACTION-CONDITIONAL: 5.8 points is below the 10.0-point bar and 5.8% is below the
90% bar. The bar was NOT moved to let this row read better. **What the fix bought is that the control now speaks
on this game instead of going mute, and what it says is that the agent's two actions are not distinguishable on
this board.** A7's twelve steps moved nothing and A6's hundred-and-three moved something 5.8% of the time; against
a control that can now see both at once, that is a game the agent is not steering.

**R-3 CONFIRMED.** `tn36` has one action on one exit, stays `MUTE: one action only`, is NOT marked WIDENED. The
fix did not manufacture a finding on a game that has none to give.

**R-4 CONFIRMED.** `RESIDUE=0` — the regrouping is the same 232 steps the pooled split counted. `games WIDENED by
the regrouping=1`, and the coarser `games that crossed >1 exit=1` is printed beside it under its own name.

## 2. The coarse reading was KEPT, and this is checkable

Lines 622–630 of the same capture still carry the three per-exit rows with their two `su15` MUTEs, byte-identical
to arm Q's lines 619–623. Nothing was deleted to make the new reading look better. The per-exit rows answer a
different question — does one code path answer better than another on the same game? — and on a two-exit game they
remain the only place those paths can be told apart.

## 3. R-5 — the +0, and it held

`CLEARED` is **0** (line 654: `break events=6 | residual computed=6 | non-empty=1 | minted=1 | promoted into Γ=0 |
offered to Γ=0 | FIRED=0 | cleared=0`). `advances` is 1 and `total_levels` is 1, both from `tn36`, exactly as
pasted in advance from arm Q's capture. **This change won nothing on any game and is not reported as if it had.**
It is an instrument repair: the control that exists to stop a rate being cited as competence can now be read on a
game where it previously refused to speak.

## 4. R-6 — the kill condition did not fire, and the determinism receipt is now THREE-armed

All **six** rows compared — the two tether-stage rows, the two budget rows, and the two board rows — are
CHARACTER-IDENTICAL between arm Q (2026-08-01 ~01:46) and arm R (2026-08-01 ~04:34):

    su15-1944f8ab      click              0      3      0      1      1      0  REUSE_UNWIRED
    tn36-ef4dde99      click              1      2      1      0      0      0  MINT_UNFIRED
    su15-1944f8ab         120     118        2       2       0  action_cap
    tn36-ef4dde99         120     119        1       1       0  action_cap
    su15-1944f8ab      click             117    1      0     31     60     20       6     5%      3      93 Y/1
    tn36-ef4dde99      click             118    1      0      0     31     57      30    25%      2      78 Y/0

The prereg asked for four rows and got six; the two tether-stage rows were not predicted and reproduced anyway.
That is a fourth independent sweep agreeing on `tn36` and a second on narrow-`su15`. **The 08-01 determinism
receipt survives its first adversarial test.** Its bound is unchanged and must keep travelling with it: these two
games, this budget, a WARM bank restored to a named snapshot. It is not a claim about the roster.

The kill condition mattered here for a specific reason. A readout change cannot move these numbers — nothing in
the agent reads the printer — so a difference would have been evidence about the ENVIRONMENT or about an
unnoticed non-readout change in the diff, and either would have had to be named before anything else in these
documents could be read. It came back clean, which is also a receipt that the diff really is readout-only.

## 5. The readout-only claim, checked rather than asserted

`grep -rn "_action_spread_verdict\|GROUPED BY GAME FIRST\|WIDENED by the regrouping" src/` returns nothing. No
symbol introduced by this change is reachable from the agent. No counter was added and no emit site moved: the new
block sums the same per-game `act_*` bag the old loop filtered.

## 6. What this does NOT license

- It is not evidence about the roster. Two games, one budget, one bank state.
- `su15`'s UNIFORM verdict is a statement about A6 vs A7 **on `su15` at 120 actions**, not about A7 as an action
  and not about the escalation organ. Twelve steps is above the printer's floor and nowhere near enough to
  characterise an action.
- The 25-game arm has NOT been re-rendered through the fixed printer. Every historical MUTE verdict on a
  multi-exit game in every prior capture is still a subset reading, and the correct move is to re-render, not to
  reinterpret them by hand.

## 7. How to overturn

- **The regrouping.** A sweep where a game visibly takes two exits with different actions but
  `games WIDENED by the regrouping=0` refutes the widening detector, and the summary line may not be cited.
- **The kept coarse reading.** If the per-exit MUTE rows are ever absent, the fix removed evidence instead of
  adding a reading.
- **The determinism receipt.** Run arm R again. If any of the six rows above differs, the receipt is REVOKED — not
  narrowed — and every attribution made against it needs a repeat.
- **`UNIFORM` on `su15`.** Give A7 a larger window. If its answer rate rises above ~15.8% the verdict flips to
  ACTION-CONDITIONAL, and the reading in §1 was an artefact of a twelve-step trial rather than a fact about the
  game.

## 8. Gates

`764 passed, 12 skipped` · audit `VERDICT: clean (1 warn)`, `test_count: tests=776` · `answer_lint clean`.
Four new tests in `tests/test_sweep_report.py`, mutation-checked: restricting the per-game accumulation to one
exit fails two of them, and removing the zero-drop fails a third.
