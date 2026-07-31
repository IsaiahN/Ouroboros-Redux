# EVIDENCE — what the death BOARDS said (arm M, read against the pre-registration)

Pre-registration: `docs/tether/PREREG_the_death_board.md`, written and pushed at commit `658f04d` **before** this
run opened. Instrument commit and run commit: `658f04d`.

Scorecard: `https://arcprize.org/scorecards/64fbbbe0-fe6a-45ba-af7a-7066fc96424f`
Capture: `/tmp/armM_deaths.txt` (6321 lines). Attribution: `/tmp/armM_depth.txt`.
Roster digest `793049198616`, 25 games reporting, 0 errored — **the same digest arm L printed**, so pooled
comparison to arm L is licensed for the first time in this series.
Bank: **WARM** — `.residual_bank/` held 15 family files (740K) and was not deleted. Arm L ran on 14 files (728K).
No chain/mint/residual count here may be compared to a cold arm.

## The run reproduced arm L exactly, which is itself the instrument's control

`TOTAL steps=2959 decide=2939 retries=20 | BUDGET RESIDUE=0` — **identical to arm L, digit for digit**, as are
the per-game death marks (`bp35` 17/82, `s5i5` 51, `sp80` 31/62/93, `su15` 52/85, `tu93` 51/102, `vc33` 51),
23 deaths across 15 games, 20 earned and 3 refused. The instrument added three log fields and changed no
behaviour, and the receipt says so rather than the commit message.

## The four instrument self-checks: all held

| # | check | result |
|---|---|---|
| 1 | printed terminal `@N` equals the derived depth | **held** — 101 / 117 / 101, no disagreement printed. The derived table published in `EVIDENCE_the_death_rationale.md` was correct and stands. |
| 2 | a `death_no_new_cause` terminal's digest appears among that game's earlier death digests, same action | **held** — `s5i5` 472b23=life1 (A6/A6), `vc33` 98056c=life1 (A6/A6), `su15` 215b73=life2 (A6/A6) |
| 3 | every earned and terminal death line carries `board=`/`act=`/`pstep=` | **held** — 23 clauses for 23 deaths, 0 games verdicted `unknown` |
| 4 | the tautology is labelled, never counted | **held** — all three `death_no_new_cause` terminals verdict `by-defn`, not `replay` |

## The measurement, and the prediction it broke

```
  game               outcome              death @steps      actions/life   fatal actions   death boards
  bp35-0a0ad940      action_cap           17, 82            16, 64         A4 A6           ff1a25 22efe2
  s5i5-18d95033      death_no_new_cause   51, 101           50, 50         A6 A6*          472b23 472b23=life1[by defn]
  sp80-589a99af      action_cap           31, 62, 93        30, 30, 30     A6 A2 A5        78c0bb 78c0bb=life1★REPEAT 78c0bb=life1★REPEAT
  su15-1944f8ab      death_no_new_cause   52, 85, 117       51, 32, 32     A6 A6 A6*       bea16f 215b73 215b73=life2[by defn]
  tu93-0768757b      action_cap           51, 102           50, 50         A3 A4           d0fdbf fb0e3b
  vc33-5430563c      death_no_new_cause   51, 101           50, 50         A6 A6*          98056c 98056c=life1[by defn]
```

Prediction 5 said the two flat games whose deaths ALL registered as new causes — `sp80` and `tu93` — would show
pairwise distinct boards, which would let H1 (clock) survive and kill H2 (replay). **It split.** `tu93` held
distinct. **`sp80` did not: all three of its deaths happened on the pixel-identical board `78c0bbef166e`, at
policy frames 29, 60 and 91, under three DIFFERENT actions — A6, then A2, then A5.** Each was credited by §XIX
as a NEW avoidable cause, because the key is `(board, action)` and the action differed each time.

## Then I rendered the two games, and the digest reading collapsed

`tools/see_game.py sp80-589a99af 95` — **the agent's thirty actions changed nothing on the screen.** The
change-map is zero everywhere except the top bar and the vertical corridor swept by a descending block; the
avatar-coloured cells never change at all. `cells_ever_changed=832` is entirely the falling block and the bar.
A monotonically depleting bar runs across the top of the frame and is empty at the death.

So on `sp80` the board is a function of the STEP INDEX and not of the agent. Two deaths at the same depth are
then pixel-identical **necessarily**, and the `★REPEAT` is not a second observation about a route — it is the
flat life count re-encoded as a digest. **The `replay` verdict there is a statement that the agent was inert, not
that it navigated back.** The tool's printed gloss has been amended to carry that defeater, because a mis-labelled
receipt produced by the very instrument built to catch them is the worst kind.

`tools/see_game.py tu93-0768757b 55` — a maze. The avatar DOES move (`cells_ever_changed=91`, a wander trail
around the start corner), it never approaches the goal cell, and a depleting bar runs along the bottom and is
empty at the death. Its two death boards differ because the avatar was somewhere different; the depth was 50
both times regardless.

## CLASSIFIER 13 — the death the memory is recording is not the death that happened

**On the games where the agent dies twice or more, the receipt and the pixels agree that the run is ending on a
depleting bar reaching zero, and §XIX is recording the pending ACTION as the cause.**

The single strongest line of evidence needs no rendering at all: on `sp80`, **three different actions were each
recorded as fatal from one pixel-identical board.** If an action were the cause, three different actions could
not all be fatal at the same instant on the same screen. The invariant across the three is the step count.

That is why the memory grows and survival does not. `DeathMemory` learns "A6 from board X ends the run", the
retry dutifully avoids A6 there and takes A2, and the run ends at the same instant anyway — after which A2 is
recorded as a second cause, then A5 as a third. The veto works exactly as designed and is aimed at the wrong
object. The §XIX gate then reads three genuinely-new `(board, action)` pairs and grants three restarts, each of
which it describes as having "a reasoned basis for a different outcome."

**This supersedes the H1/H2 framing rather than resolving it.** H2 (replayed route) is dead as stated: the one
game that produced a pixel-exact repeat produced it by not moving. H1 (per-game death clock) is the right shape
but the wrong altitude — it is not a mysterious clock, it is a visible resource the agent neither perceives nor
spends deliberately.

## What may NOT be read off this

* **`bp35` contradicts a universal budget reading and is named, not smoothed.** Its lives were 16 then 64, on two
  distinct boards. `su15` also fails a fixed-budget story: 51, then 32, then 32. Whatever the bar is, it is not
  the same length on every life of every game, and this document does not claim it is.
* **"A depleting bar" is what I saw, not a mechanic I verified.** I have not shown the bar CAUSES the death, only
  that it is monotone in the step index and empty at the death in the two games rendered. Two games are not the
  roster.
* **The nine single-death games carry boards now but no comparison.** One death cannot repeat or fail to repeat.
* **Pooled comparison to arm K (digest `b93d1c615657`) is still refused.** Arm L and arm M share a digest; arm K
  does not.
* **No claim about the other 19 games' death mechanism.** They died once or not at all.
* **The digest can only say identical or not.** The "near-identical under a weaker key" form of replay remains
  untestable from this capture, because the boards themselves are not logged.

## How to overturn, and what it licenses

The claim to attack is CLASSIFIER 13: that the deaths being recorded as action-caused are resource-exhaustion
deaths. Three ways to break it, in order of cheapness:

1. **Render the other multi-death games** (`bp35`, `s5i5`, `su15`, `vc33`). If any of them dies on a hazard
   collision with the bar still full, the classifier is over-general and must be scoped to `sp80`/`tu93` by name.
2. **Measure inertness directly.** The `sp80` reading rests on a change-map I looked at. A receipt that counts,
   per game, how many of the agent's actions changed ANY cell would make "the agent is inert here" a printed
   number instead of an image I described. That is the cheapest instrument this document motivates, and the fact
   that `replay` cannot currently be read without it is the argument for building it.
3. **Check whether the bar is in the frame the policy sees.** If the depleting row is present in the observation
   and simply never becomes a referent, that is a perception finding. If it is not in the frame at all, no amount
   of reasoning could have used it, and the whole death-memory design is answering a question the agent cannot
   see.

**Nothing here licenses a behaviour change in the beat that measured it**, and the temptation is specific and
must be named so the next beat can refuse it: DO NOT special-case "timeout deaths" out of `note_death`, and do
not add a hazard/timeout distinction to the death literals, on the strength of two rendered games. Get (1) and
(2) first. Changing the §XIX key or the death memory remains the FIX and did not ship here.
