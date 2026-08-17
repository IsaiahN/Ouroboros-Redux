# PREREG: THE CORPSE FIX (1a) + THE GUARD INVERSION (2) + the consumption record where it bites
DATE: 2026-08-17. AUTHORITY: Isaiah ruled yes on all four. Shipped as ONE change because
it is one causal story: STOP REPLAYING CORPSES. Fixes (1b) dead-cell dedup and (1c)
rotation ship SEPARATELY (different organs, separable verdicts).

## MEASURED HARM (ar25, receipts in FRONTIER_AUDIT)
13 of 13 salient replays end GAME_OVER on the FIRST cognitive action after playback;
[SALIENT] divergence fires ZERO times. Cause: the bank keeps the prefix "up to the last
EFFECTFUL action", and dying CHANGES THE FRAME, so the death step IS the terminal
banked step and the fidelity check matches the corpse's own hash. 318 of 450 actions
(71%) go to playback, leaving ONE cognitive action at the frontier.

## BUILD
A. NEVER BANK A TERMINAL STEP: if the final effectful step of an episode produced
   GAME_OVER (or the episode terminated at it), TRUNCATE BEFORE IT; if nothing remains,
   REFUSE to bank. Narrated.
B. THE GUARD INVERSION — OUTCOME, NOT FIDELITY: divergence detection answers "does this
   still apply"; the question is "DOES THIS STILL WIN". Record per-prefix REPLAY
   OUTCOME at replay end (reached_level / died / aborted) on the prefix row — which is
   also THE CONSUMPTION RECORD for this artifact (rule 3, scoped: any artifact subject
   to selection carries its consumption record or the selection runs on a constant).
   REFUSE to select a prefix whose last recorded outcome was DEATH.
   NOTE: this breaks the uses-DESC lock-in as a SIDE EFFECT (a locked corpse is refused,
   so the next alternative is reached). Pure round-robin rotation (1c) is NOT in scope.
C. Existing banked corpses: the refusal in (B) handles them without deleting evidence
   (archive law) — they stay on disk, unselected.

## FALSIFIERS (failing first)
1. An episode whose last effectful step is a GAME_OVER banks NOTHING (or a truncated
   prefix), never the death step.
2. A prefix with a recorded death outcome is NOT selected; the next alternative is.
3. A prefix replayed to a level records reached_level and remains selectable.
4. OFF-ARM (ablation clause, passing at ship): CORPSE_GUARD=0 reproduces current
   behaviour byte-identically (banking and selection), proving the toggle.

## REGISTERED VERDICT (2 beats)
[SALIENT] replays stop terminating in GAME_OVER on the first cognitive action; cognitive
actions available at the frontier rise above 1. LOSING CONDITION: if replays still end
in death with the guard on, the death is not coming from the banked prefix and the
diagnosis was wrong — revert, do not extend the guard.
