# BUILDER BRIEF — MAKE THE MIRROR AN ACTUAL MIRROR (salient replay calls mastery)

RULED (GM, 2026-08-22): "The obvious disposition is that the salient path calls mastery like
its sibling does — not removal, since the main path proves the mechanism works. Make the
mirror an actual mirror." NOT removal. The mechanism is sound; one of its two call sites
never uses it.

## The defect, with both sites
`cognitive_game_player.py`
- **Site A, GATED, the exemplar — do not change it, copy it**: `:266-269`
  `p = (self._mastery.replay_probability(game_type, has_bank) if self._mastery else <static prior>)`
  and every completed replay's outcome is fed back at `:278-283`
  (`self._mastery.record_replay_outcome(game_type, ok)`).
- **Site B, UNGATED, the defect**: `:331`
  `if _sal and random.random() < self._SALIENT_REPLAY_P:` with `_SALIENT_REPLAY_P = 0.2`
  at `:1473`, whose comment reads "the mastery-lite mirror: fresh-rate replay draw".
  It never calls mastery, never records an outcome, and the constant is hard-coded.
- **The harm is already recorded four lines below the constant**, in the corpse guard's own
  comment (`:1475-1479`): "MEASURED HARM (ar25, FRONTIER_AUDIT F-1): 13 of 13 salient
  replays ended in GAME_OVER on the FIRST cognitive action after playback and divergence
  fired ZERO times — the replay was FAITHFUL and what it faithfully reproduced was a death."

## What you build
1. Site B draws its probability from mastery exactly as site A does — same call, same
   fallback when `self._mastery` is None, so behaviour with no mastery instance is
   byte-identical to today (that absence IS the undo).
2. Site B records the outcome of every completed salient replay back into mastery, exactly
   as site A does. A gate that is never fed cannot earn anything; feeding it is the half
   that makes the gate real over time.
3. `_SALIENT_REPLAY_P` remains ONLY as the no-mastery fallback prior. Its comment is
   corrected: it is a fallback constant, not a mirror. Read `record/prereg/PREREG_MASTERY_LITE.md`
   first and follow its vocabulary.
4. Do NOT change the corpse guard, the divergence detection, `_SALIENT_K`, or the main path.
   Do not remove salient replay.

## Falsifiers (tests/gate/test_salient_replay_gate.py)
- F1 · with a mastery instance whose `replay_probability` returns 0.0, the salient path
  NEVER replays over many draws; at 1.0 it always does. Asserted by counting, with the RNG
  seeded — never by wall-clock, never by a single draw.
- F2 · every completed salient replay calls `record_replay_outcome` exactly once, with the
  outcome the replay actually had (success and abort both constructed).
- F3 · `self._mastery is None` → byte-identical behaviour to today, including that the
  static prior is used and no outcome is recorded (the undo).
- F4 · the two sites now resolve their probability through the SAME function — asserted by
  identity (both call `replay_probability`), not by name-alike.
- F5 · known-negative: the corpse guard and divergence detection still fire on their own
  constructed cases; this build does not weaken them.

## The laws this build satisfies (figures/*.svg; digest at record/corpus/FIGURES_TEXT_DIGEST.md)
- **FIGURE 4, the membrane**: "downward: something that makes the next search cheaper. Never
  a replay of what worked once." Replay is playback crossing downward; mastery-lite IS the
  membrane's checkpoint, and a path that skips it is an unchecked crossing.
- **FIGURE 10, install what can be violated**: a hard-coded 0.2 calling itself a mirror is a
  convention nothing can check. Routing through the earned rate makes it checkable.
- **FIGURE 1**: replay produces counter-movement without cognition — levels completed by
  playback are not the ground being met by the agent. Do not report replay counts as progress.
State in your report which of these your tests ASSERT and which they ASSUME.

## Discipline
Fleet is halted and HOLD is up — this is the window for a live-path edit. No commit, nothing
under `.runs/`. The registry is symbol-anchored now: refresh any row you move by GREPPING THE
SYMBOL and read `tools/wiring_receipts.py` + `tests/gate/_ast_laws.py` before touching a cell.
KNOBS: `_SALIENT_REPLAY_P` changes meaning (mirror → fallback prior), so its row is updated
with the ruling cited. ruff zero new. Full suite once at the end; the number to match is
2726 passed / 0 failed / 2 skipped / 2 xfailed, plus your new tests.
