# BOARD AUDIT (2026-08-17) — the first time this project looked at the board
METHOD: instrumented replay of ar25's banked route + the 197-step L2 prefix, capturing
the frame after every step, using the AGENT'S OWN hash function. Box DB read-only, no
agent code modified. 318 frames captured.

## 0. THE FRAME CORPUS DOES NOT EXIST
levelup_frames: 1 record with real 64x64 arrays — THE ONLY GENUINE BOARD DATA ON DISK.
winning_sequences.initial_frame/final_frame: the 2-byte literal '[]' in ALL 85 rows.
action_traces.frame_before/after: str(list_of_ndarray) — numpy REPR, ellipsis-truncated;
  0 of 171,013 rows are reconstructable.
salient_prefixes: md5 hashes only. frame_embeddings / visual_analysis_cache /
  game_visual_analysis / visual_primitives / replay_index: 0 rows each.
=> 187k action records banked; the board retained for exactly ONE moment in history.
EVERYTHING DOWNSTREAM REASONS ON DIGESTS.

## 1. CORRECTION TO F-1
The death is STEP 197 OF THE PLAYBACK ITSELF, not "the first cognitive action after".
The game is already over when the replay returns; the logged [319] action is the loop
STEPPING A CORPSE. Fidelity was perfect: 197/197 hashes matched, 0 divergences.

## 2. THE CLOCK — the board publishes a countdown the model has no slot for
Column 63 is a 64-cell monotone clock: refills at level-ups, spends on effectful
actions, terminal when full. Verified strictly monotone across all 197 steps (128 ticks
over 144 changed steps). Both WINNING levels finished with spare left (16 and 18). The
prefix spent all 64, ran a SECOND full 64-tick pass, and died on the tick that completed
it. THE DEATH WAS VISIBLE, WITH AN EXACT COUNTDOWN, FOR THE FINAL 97 STEPS.
DIVERGENCE FROM A WINNING RUN: prefix step 4 (colour 12 appears — a symbol that NEVER
occurs in the 121-action winning portion); step 82 (spare drops below 16, the lowest
spare any level-up ever came from); step 100 (spare = 0, committed).

## 3. WHY NOTHING NOTICED — three reasons, deepest last
(a) The divergence detector is a WHOLE-FRAME md5: a FIDELITY test, and fidelity was
    perfect. A 64-cell monotone clock is invisible to a whole-frame digest — the digest
    changes on every tick and carries NO ORDERING, so "3 remaining" and "60 remaining"
    are equally just "some hash."
(b) changed=True IS WHAT KILLED IT: the clock ticks on effectful actions, so the death
    is the MOST effectful step in the ledger; banking truncates to "the last effectful
    action". THE SALIENCE RULE SELECTED THE CORPSE BECAUSE IT WAS THE CORPSE.
(c) THE ONE SIGNAL THAT EXISTED WAS ERASED (cognitive_game_player.py:337):
      prev_levels = getattr(_sobs, 'levels_completed', 0) or prev_levels
    A GAME_OVER observation reports levels_completed = 0; the `or` treats 0 AS MISSING
    and restores the stale 2. The call site never checks _sobs.state. So the loop
    returns from playback believing ALIVE, LEVEL 2, 132 ACTIONS LEFT. The board says
    DEAD, LEVEL 0. This is the ZERO-IS-NOT-ABSENT fallacy, live, on the critical path —
    and the corpse guard does NOT fix it.

## 4. THE ONTOLOGY IS WRONG FOR THIS BOARD (Divergence B)
ACROSS THE ENTIRE 318-ACTION EPISODE: 45 ACTION6 coordinate clicks, ZERO effective —
not one changed a single cell, not even the clock. 24 of the prefix's 26 clicks land on
background; 2 land inside a wall. Meanwhile the loop banks 155 individually-blacklisted
"dead cells" at this level (itself ~4x inflated per F-3). THE BOARD IS NOT SAYING
"THESE 155 CELLS ARE DEAD" — IT IS SAYING "ACTION6 DOES NOTHING HERE AT ALL", and it has
said so for 492 consecutive trials. The model's ontology is PER-COORDINATE; the fact on
the board is PER-ACTION.
AND THE REDIRECT MADE IT WORSE: the frontier steered a click (36,12)->(35,11) INTO A
STATIC WALL (row 11 cols 33-35 read BBB in every frame). It consulted a cell blacklist
and never the wall geometry visible in every single frame.

## 5. Divergence C: 19 of the 121 actions in the WINNING sequences are clicks that
change NOTHING on replay. frame_changed is not merely weaker than necessity — it is not
stable across replays of the same sequence on the same board.

## 6. THE VOCABULARY ALREADY EXISTS AND IS NOT WIRED TO THIS
goal_abduction.py defines colour_count_zero(colour) — literally "colour 11 count is
zero", the exact condition at prefix step 100 — and never evaluates it against this
board.

## THE EPISTEMIC LESSON (for the corpus)
Every instrument this project has built reads THE AGENT'S ACCOUNT OF THE WORLD — logs,
testimony, settlements, verdicts, books. NONE of them read THE WORLD. One instrumented
replay against the frames produced three defects that months of log-reading missed,
because the missing information was never in the logs to be read. THE GROUND HAS A
CHANNEL AND WE HAD NEVER OPENED IT.
