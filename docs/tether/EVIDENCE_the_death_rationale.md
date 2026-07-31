# EVIDENCE — what the death rationale actually said (arm L, read against the pre-registration)

Pre-registration: `docs/tether/PREREG_the_death_rationale.md`, written and pushed at commit `2651230` **before**
this run opened. Instrument commit: `7e37f83`. Run commit: `2651230`.

Scorecard: `https://arcprize.org/scorecards/77af39ab-4ee5-4b0b-9bfb-458d00ac4df8`
Capture: `/tmp/armL_deaths.txt` (6263 lines). Roster digest `793049198616`, 25 games reporting, 0 errored.
Bank: **WARM** — `.residual_bank/` held 14 family files (728K) and was not deleted. No chain/mint/residual count
below or in that capture may be compared to a cold arm.

Offline attribution: `tools/death_depth.py` (pinned by `tests/test_death_depth.py`), run over the capture. It
re-derives nothing from the agent; every number it prints was printed by `tools/sweep_chain.py` off a string the
policy itself wrote at the moment it decided.

## Verdict: the pre-registration is CONFIRMED on all four predictions

| # | prediction | result |
|---|---|---|
| 1 | `s5i5`, `vc33`, `su15` each exit `death_no_new_cause` | **held** — all three, and no other game did |
| 2 | each carries exactly one TERMINAL rationale containing `repeats a cause already in game-memory` | **held** — 3 terminal rationales, 0 ★ MISSING, 0 doubled |
| 3 | `retries` strictly below `retry_cap = 6` | **held** — 1, 1, 2; the largest anywhere in the sweep is 3 (`sp80`) |
| 4 | `deaths − retries == 1` on each | **held** — 2−1, 2−1, 3−2 |

None of the three falsifiers fired. **CLASSIFIER 11's §XIX paragraph stands and does not need rewriting.** The
attribution it made from code plus a pooled `GAME_OVER` literal is now a printed receipt.

The budget identity closed again live and independently: `TOTAL steps=2959 decide=2939 retries=20 | BUDGET
RESIDUE=0` across all 25 games.

## What the newly-printed lines then showed (this is the new finding)

23 deaths across 15 games. **20 earned a restart, 3 were refused.** Per game, `causes == retries` on every single
game in the sweep — the death-memory grew by one at every death except the three terminal ones.

```
  game               outcome              death @steps               actions/life     fatal actions
  bp35-0a0ad940      action_cap           17, 82                     16, 64           A4 A6
  s5i5-18d95033      death_no_new_cause   51, [101 derived]          50, 50           A6 A6*
  sp80-589a99af      action_cap           31, 62, 93                 30, 30, 30       A6 A2 A5
  su15-1944f8ab      death_no_new_cause   52, 85, [117 derived]      51, 32, 32       A6 A6 A6*
  tu93-0768757b      action_cap           51, 102                    50, 50           A3 A4
  vc33-5430563c      death_no_new_cause   51, [101 derived]          50, 50           A6 A6*
```

(`actions/life` subtracts the reset's own step increment once per restart; `*` marks a terminal death, whose depth
is DERIVED from final `steps` because the terminal branch logs and breaks without a `@N`. Nine further games died
exactly once and have no lives to compare.)

**Four of the six multi-life games reproduce their per-life action count EXACTLY** — `s5i5` 50/50, `vc33` 50/50,
`tu93` 50/50, `sp80` 30/30/30. `su15` shortened once and then repeated (51/32/32). **`bp35` is the sole
counter-example in the sweep: 16 actions, then 64.** It is named rather than averaged away.

The fatal action was **A6 in 15 of the 23 deaths**; A4, A3 and A2 twice each, A1 and A5 once.

## The two things this licenses, and the one it does not

**(a) The §XIX gate reads as a reasoning gate and behaves as a novelty test.** `board_fingerprint`
(`survival.py:23`) is `hash((a.shape, a.tobytes()))` — two boards share a fingerprint iff they are
pixel-identical. So "did this death teach a NEW avoidable cause?" is executed as "is this exact screen novel?",
and it answered NEW 20 times out of 23. `AvatarHazard`'s own docstring already conceded the consequence: the
agent must die ONCE AT EACH NEW FATAL BOARD. The receipt now shows what that costs in practice.

**(b) The restarts bought no depth on four of six games.** The memory grows 1 → 2 → 3 while post-reset survival
does not move.

**(c) NOT licensed: why.** Two readings survive this capture and it cannot separate them.
* **H1 — a per-game death clock.** Something kills the agent at a fixed depth regardless of what it does, and the
  "new causes" are cosmetic noise about a board that happens to differ.
* **H2 — a replayed route.** The agent re-walks a near-identical path and dies in the same situation on a board
  that is not pixel-identical.

Evidence bearing on both, in both directions: every intermediate death registered as NEW, so the death board was
*not* pixel-identical, which argues against an exact replay. But `tu93` (50/50) and `sp80` (30/30/30) reproduced
their life length exactly *and* registered NEW at every death, so a flat life length does **not** imply a repeated
board — the coupling runs one way at most. Conversely all three pixel-exact repeats (`s5i5`, `vc33`, `su15`)
happened on games whose life lengths also matched to the action.

## What may NOT be read off this

* **No pooled comparison to arm K** (digest `b93d1c615657`, 23 reporting). The digests differ. That `s5i5`,
  `vc33` and `su15` reproduce 101/101/117 steps across the two arms is a PER-GAME observation and is offered as
  nothing more.
* **`death_retry_cap` and `death_no_reset_support` still have no live firing.** The cap never bound and every
  live session carried `reset_after_death`. Their coverage is synthetic only; that is an absence, not a result.
* **`error_text` got no live exercise.** All 25 games opened this sweep (`cn04`, `r11l` and `tn36`, which had
  failed to open in arms I/J/K, all recovered). The field is synthetic-only so far.
* **The terminal death's depth is derived, not printed.** It is sound — the run ends at that death — but it is
  not a receipt, and it is the first thing to fix if these life lengths ever become load-bearing.
* **A6's 15-of-23 share is not "A6 is dangerous."** The action mix the agent emits is not flat, and this section
  carries no denominator for how often each action was emitted at all.

## How to overturn

The separating measurement is **the death BOARD**, which no receipt currently carries. Put the death-board
fingerprint, the pending action, and the step index on the terminal rationale line as well as the earned ones,
then re-run this same roster warm:

* If the fingerprints of a game's successive deaths are **pairwise distinct while the life lengths are equal**,
  H1 (clock) survives and H2 (replay) is in trouble.
* If successive death boards are **near-identical under any weaker key** — same avatar cell, same fatal cell,
  differing only in a counter or a cosmetic tile — H2 survives, and the finding becomes "the memory's key is too
  strict," which is an argument for changing the key, not for changing the gate.
* If life lengths **stop being flat** once the boards are logged, this table was an artefact of the roster and
  must be withdrawn.

Nothing here licenses a behaviour change in the beat that measured it. Changing the §XIX key or the death memory
is a FIX, and it does not belong in the same beat as its own motivation.
