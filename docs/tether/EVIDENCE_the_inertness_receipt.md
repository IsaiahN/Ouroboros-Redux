# EVIDENCE — the inertness receipt (arms N and O)

**Read `PREREG_the_inertness_receipt.md` FIRST, including its AMENDMENT. That is what was believed before each
run; this is what the runs said.**

Arm N — scorecard `fb68f38d-f5fc-4287-a073-3288c77c284a`, roster digest `5d845a4bd1ab`, 24 reporting / 1 errored
(`su15` never opened), `TOTAL steps=2842 decide=2824 retries=18 | BUDGET RESIDUE=0`, bank WARM (15 files, 748K).

Arm O — scorecard `9b783773-04cb-4693-9f9e-3d20d9953028`, roster digest `29e058945c46`, 24 reporting / 1 errored
(`wa30` never opened), `TOTAL steps=2839 decide=2819 retries=20 | BUDGET RESIDUE=0`, bank WARM. Same agent code as
arm N: the only changes between them are in `tools/sweep_chain.py` and `tests/`.

**The two rosters differ, so no pooled number crosses them.** The intersection is 23 games, and on it the board
table reproduces **cell for cell** — every column of every shared row identical, checked mechanically, not by eye.
Two live runs of one build over one roster; that is a reproduction, not a second sample.

## S2′ — the corrected identity, tested out of sample: PASSED

`board.steps == steps − retries − tail`, `tail` assigned by the exit literal BEFORE the residue was looked at.
Arm O: **residue 0 on all 24 reporting games**; `tail = 1` on the 21 cap-exit games and `0` on the three
`death_no_new_cause` games (`s5i5`, `su15`, `vc33`), with no exceptions in either direction. The rule fitted to
arm N's failure survived the arm it did not see. `observed_tail` names the fall-through literals explicitly, so a
new fall-through `return` added later prints `?` and forfeits its residue rather than borrowing a `1`.

## What the receipt says about the agent (arm O, per game, roster-scoped)

`TOTAL charged 2798 | still 518 | band_only 448 | sub_floor 651 | live 1181 (42%) | skip 44`.

Four games answer on essentially every action (`dc22`, `ls20`, `sk48`, `tr87` at 100%); four are near-mute
(`tu93` 3%, `lf52` 3%, `s5i5` 4%, `su15` 5%, `vc33` 2%). **`live%` is not competence** — the four 100% games win
nothing — and it is not being offered as such. What it is good for is the opposite direction: a game at 2–5% is a
game where almost no action the agent took produced anything a residual could be built from, and `R_τ = 0` has no
gradient. That is the same set of games the tether stage table scores `RESIDUAL_EMPTY`.

## P1 FAILED AS STATED, and the failure is a statement about the MASK

`sp80` was predicted inert: `live` 0 or single figures. It came back **45 live of 116 charged (39%)**. Taken
alone that would overturn last beat's inertness reading of `sp80` and with it the clearest leg of CLASSIFIER 13.
It cannot be taken alone, because P3 failed in the same row: **the monotone band was masked on only 23 of those
116 steps.** On the other bar games the same shortfall appears — `tu93` 42/117, `s5i5` 42/100, `vc33` 42/100,
`bp35` 30/117. The band mask needs a non-decreasing ratchet across a window; a restart REFILLS the bar and breaks
it for up to `keep = 48` frames. So on the majority of steps the bar's own tick is charged as board response.
**Neither reading is established: `sp80` is not shown inert and it is not shown responsive.** What is shown is
that this instrument cannot answer that question until the mask survives a restart, and that fix may not ship in
the beat that measured the need for it.

## THE ONE-LABEL GAMES: MY OWN EARLIER READING THIS BEAT IS WITHDRAWN

Seven games spent their whole budget on `A6`. Mid-beat I read that as the escalation organ being switched off by
the native-click guard exactly where it was needed, and started writing it up as a classifier. **That reading was
a code reading, not a receipt, and the receipt refuted most of it.** The recordings carry each game's
`available_actions`:

    ft09 (6,)   lp85 (6,)   r11l (6,)   s5i5 (6,)   tn36 (6,)   vc33 (6,)   su15 (6,7)   sp80 (1,2,3,4,5,6)

**On six of the seven, action 6 is the entire action set.** One label for the whole budget is not a pathology
there and no organ could have done otherwise; there is nothing to escalate TO, and `EngagementMeter.escalate`
correctly returns `None`. Any inertness claim about those six is a claim about the game's action set.

## CLASSIFIER 14 — A NATIVELY CLICK-ROUTED GAME NEVER REACHES THE ESCALATION ORGAN

`su15` is the one game where an alternative exists, and it is the receipt. It advertises `A6` and `A7`. Arm O:
family `click`, `frozen = True`, `responsive_fraction = 0.00`, **115 charged steps, one action label, `A7` never
emitted once, `escalations = 0`**, board response 5% live. It then died three times — every death on `A6`, and
deaths #2 and #3 from the **pixel-identical board `215b73c40473`** (`@85` and `@117`).

The mechanism is one branch, and it is not the guard inside the organ. `_decide` returns at the `click_native`
exit **before `_modality_escalate` is ever called**, so on a game whose action set carries no directional actions
the organ built to refuse a null intervention is never consulted at all — however frozen the board, however many
untried actions are available. `tests/test_board_response.py` pins both arms synthetically: an identical frozen
board with `{A6, A7}` available, natively routed, emits `A6` forever with `escalations == 0` while the meter,
asked directly, hands back `A7`; the same board routed to another organ escalates and emits both labels.

**Live instance count: ONE (`su15`).** Six games cannot speak to it because their action set has no alternative,
and the games that escalated INTO click (`bp35`, `cd82`, `cn04`, `lf52`, `sc25`, `sb26`) reach the organ by
construction. A single live instance plus a synthetic is enough to say the branch does what it says; it is not
enough to price it. **HOW TO OVERTURN:** find a game that advertises a non-`A6` action, routes natively to click,
freezes, and DOES escalate — that would mean the `click_native` return is not the bypass. Or show that `A7` on
`su15` is inert too, which would make the bypass free on the one instance we have.

**No fix ships in this beat.** Removing or scoping the guard is the change this measurement motivates, and the
discipline forbids building it in the beat that measured it.
