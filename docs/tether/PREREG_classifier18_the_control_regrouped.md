# PREREG — CLASSIFIER 18: the self-motion control regrouped by GAME before ACTION

**2026-08-01 ~05:10 UTC. This is a READOUT change. Nothing in the agent reads it, no counter was added, no emit
site moved.**

**★ THE HONEST PROVENANCE OF THIS DOCUMENT, stated because the alternative is a lie of omission.** Arm R was
LAUNCHED before this was written. It was not pushed before the scorecard opened, and the standard header claiming
otherwise has been removed rather than left to be read charitably. What IS true, and is the whole reason it is
still worth having: every prediction below was written before a single line of arm R's output was read. R-1
through R-4 are derivable from the diff by inspection and could have been written without any arm at all; R-6 is
PASTED from arm Q's capture file at named line numbers. Nothing here can have been back-fitted to a result I had
not seen. Judge it as a pre-reading, not a pre-registration, and hold the next intervention to the stricter bar.

---

## 1. The defect

`tools/sweep_chain.py`'s self-motion control loops `for k, n in sorted(dfx.items(), ...)` — the EXIT LITERAL —
and only inside that loop splits each game's steps by ACTION, via `_acts_of(None, k, ...)`, which filters the
per-game bag down to the one exit. So a game whose actions arrive through two different exits is rendered as two
separate one-action games.

On 2026-08-01 arm Q this destroyed the sharpest action contrast the roster has produced. `su15-1944f8ab` sent A6
through `family_click` (n=103, 5.8% masked) and A7 through `escalate` (n=12, 0.0% masked) — and the control
printed, twice, verbatim from `/tmp/armQ_treatment.txt` lines 619–623:

    family_click           pooled   5.8% masked of 103 priced, over 1 distinct actions
        su15-1944f8ab      A6   5.8%(n=103,cells  1.4)  ...
            -> MUTE: one action only -- the split cannot vary, so it rules nothing out
    escalate               pooled   0.0% masked of 12 priced, over 1 distinct actions
        su15-1944f8ab      A7   0.0%(n=12,cells  0.0)
            -> MUTE: one action only -- the split cannot vary, so it rules nothing out

The control's question is *"did the AGENT move the board, or does the board move anyway?"* That question's
denominator is the **GAME**: one board, one episode, the actions compared against each other on it. An exit is a
fact about which code path chose the action, not about which board it was sent to. A per-exit number standing
where the per-game number is what answers the question is RANKING 5's pooled/subset defect one level down — and
it fails in the worse direction. It does not overstate a finding; it DELETES one.

## 2. What changed

1. `_action_spread_verdict(rates, ga)` lifted to module level — the classifier now exists in ONE place and is
   called from both readings, so the two groupings can never disagree about the same steps.
2. A new sub-block, `--- THE SAME CONTROL, GROUPED BY GAME FIRST ---`, which sums the SAME per-game `act_*` bag
   over every exit instead of filtering to one, and applies the identical classifier.
3. The per-exit rows are **kept, unaltered, under their own name**. They answer a different question — does one
   code path answer better than another on the same game? — and are the only place a two-exit game's paths can be
   told apart. When a coarse reading is replaced by a finer one, both are printed and each is labelled.
4. Zero-`act_attr` sub-keys are DROPPED in the new block (the region keys `<exit>|A6@r2c0` carry `click_reg_attr`,
   not `act_attr`, and would otherwise render as actions at `nan%(n=0)` — a field never COMPUTED, printed as a
   zero, which is a mis-labelled receipt). The region block below already does exactly this drop; the per-exit
   block above does not, and is left alone.
5. Two counters, because they are not the same number and conflating them would overstate this fix's reach:
   `games that crossed >1 exit` (nearly the whole roster — every game crosses `warmup` → its steady exit, so this
   number says almost nothing) and `games WIDENED by the regrouping` (the game's action set is wider than any
   single exit's — the only case where a comparison was actually destroyed). Cite the second.
6. A RESIDUE line: the regrouping is the same steps read a second way, so it must close against the pooled action
   split exactly.

## 3. The tests (offline, real receipts through `report()`, mutation-checked)

`tests/test_sweep_report.py` gains four. `_run_two_exits` drives a real `ReduxPolicy` on a board that answers only
A1, with a stub decision that routes A1 through `exit_alpha` and A2 through `exit_beta` — `su15` in miniature.

- the per-exit rows are STILL two MUTEs, and the per-game row is ACTION-CONDITIONAL by 100 points
- the regrouping sums back to the pooled split, RESIDUE=0
- a region key never renders as an action
- a game that really does have one action is STILL MUTE after regrouping — the fix changes the denominator, never
  the classifier

Mutations run and caught: restricting the per-game accumulation to one exit fails tests 1 and 2; removing the
zero-drop fails test 3.

## 4. THE PRE-REGISTERED PREDICTIONS — arm R (`tools/sweep_chain.py 120 200 su15,tn36`, default narrow, bank
restored to `/tmp/bank_snapshot` so it is bank-identical to arm Q)

**R-1 (the fix, on the instance that motivated it).** `su15-1944f8ab` appears ONCE in the new block with TWO
actions, A6 and A7, and is marked `★ WIDENED`. Its exits render as `escalate{A7}, family_click{A6}`.

**R-2 (the verdict, published in advance because it is NOT the flattering one).** A6 ≈ 5.8%, A7 = 0.0%. The spread
is ≈5.8 points, below the 10.0-point ACTION-CONDITIONAL bar and below the 90% self-motion bar, so the control will
read **`UNIFORM (0.0%-5.8%) but not high -- no self-motion signature`**. It will NOT read ACTION-CONDITIONAL. The
threshold is FROZEN and will not be tuned to make this row read better; a control retuned until it agrees with the
builder is not a control. What the fix buys is that the control now SPEAKS on this game instead of going mute —
and what it says is that the agent's two actions are not distinguishable on this board.

**R-3 (the fix does not manufacture findings).** `tn36-ef4dde99` has one action on one exit and stays
`MUTE: one action only`. It is NOT marked WIDENED.

**R-4 (the identity).** `RESIDUE=0`, and `games WIDENED by the regrouping=1`.

**R-5 (the +0, published in advance).** `CLEARED` is 0. `advances` is 1 and `total_levels` is 1, both entirely
from `tn36` — **pasted from `/tmp/armQ_treatment.txt` line 58, not typed from memory**, per the rule earned on
2026-08-01 when a pre-registered baseline was wrong in the control too. This change wins nothing on any game. It
is an instrument repair and is reported as one.

**R-6 (determinism, the third independent test of the 08-01 receipt).** Arm R is the same commit's agent as arm Q
on the same two games at the same budget from a byte-identical bank, so if the environment is deterministic on
these games these rows must reproduce CHARACTER-FOR-CHARACTER. Pasted from `/tmp/armQ_treatment.txt`:

    line 57   su15-1944f8ab         120     118        2       2       0  action_cap
    line 58   tn36-ef4dde99         120     119        1       1       0  action_cap
    line 77   su15-1944f8ab      click             117    1      0     31     60     20       6     5%      3      93 Y/1
    line 78   tn36-ef4dde99      click             118    1      0      0     31     57      30    25%      2      78 Y/0

**KILL CONDITION.** If any of those four rows differs, the 08-01 determinism receipt is REVOKED — not narrowed,
revoked — and every attribution made against it (including "scheduling, not learning") needs a repeat before it
may be cited again. A readout change cannot move these numbers; nothing in the agent reads the printer. So a
difference here is evidence about the ENVIRONMENT or about an unnoticed non-readout change, and it must be named
before anything else in this document is read.

## 5. How to overturn this

- **The regrouping.** If `games WIDENED by the regrouping=0` on a sweep where a game visibly took two exits with
  different actions, the widening detector is wrong and the summary line may not be cited.
- **"Nothing in the agent reads it."** Grep `src/` for `_action_spread_verdict` and for the new block's strings.
  Any hit means this stopped being a readout change and the whole thing needs re-scoping.
- **The kept coarse reading.** If the per-exit MUTE rows disappear, the fix removed evidence instead of adding a
  reading, and the claim in §2.3 is false.
