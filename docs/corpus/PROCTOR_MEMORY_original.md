# PROCTOR MEMORY — Claude's own. Load first, every session.

**Why this exists.** `[Isaiah, 17 July]` *"you keep compacting over time so you forget the rules and how the game
works and our guidelines... there are some genuine hangups for claude like the frame-1 issue with 6 grids that you
need to hold in a separate memory space persistent just for you to keep coherence as a proctor/assistant/coder."*

Not doctrine — that is `THE_ALIGNMENT.md`, under the five documents. **This is the set of facts and habits Claude
must not re-derive.** Every entry cost real hours at least once.

---

# I. THE METHOD THAT WORKS

## Instrument the seam. Do not read and infer.

**The case that proved it.** `COMPOSER DIED: too many values to unpack (expected 4)` — intermittent, ~1 in 9 runs,
invisible for a whole session. Claude read `_QueueAdapter.step` five times and it was innocent every time: four
returns, all 4-tuples, no base class, no `__getattr__`. Reading was **structurally incapable** of finding it, because
`adapter.step` was **monkeypatched** by `_install_grammar_ride._step_with_grammar` and the real function was never on
screen.

The procedure that killed it in one run:

1. **Make the failure name itself.** Put a guard at the seam that reports what actually arrived, not what was
   expected: adapter type, the real `step` object, the action, `repr` of the value, and the last 4 stack frames.
2. **Loop the run for an intermittent.** One run proves nothing about a bug that fires on a cadence.
3. **Read the dump, not the code.** It said `step=<_install_grammar_ride.<locals>._step_with_grammar>` and
   `value={'resolution': 'object', 'transitions': 190, ...}` — a 10-key dict, unpacking to its keys as 10 strings.
4. **Then** narrow inside the named function: every `return` (one), every assignment to the returned name (two).
5. Root cause: line 2320 `_r = _orig_step(...)`, line 2406 `_r = _oti.report()` — **a MODEL narration line reused the
   variable name**, 86 lines apart, and the wrapper returned whichever ran last. Fired only on the report cadence.

**The generalisation:** when a read of the code says a bug is impossible, the code being read is not the code being
run. Wrappers, monkeypatches, and two-adapters-with-the-same-name make reading a fiction. Instrument and let it talk.

**This is the same rule as Isaiah's CORE DEBUGGING RULE, one level down:** the debugging surface is what the thing
*emits*, never Claude's model of it. For the agent that means its DSL narration. For the code it means a dump at the
seam.

## ALTITUDE IS A PROPERTY OF THE OBSERVER, NOT THE SYSTEM `[Isaiah, verbatim]`

**Altitude is the level of abstraction at which you observe a system. It is a property of the OBSERVER, not the
system. Altitude is not the primary axis. The bill -- the cost, the exponent, the currency -- is the same at every
altitude. Altitude is just where you happen to be standing.** `[CONSTITUTION §1.3a: "the altitudes are not the
interesting axis -- the bill is, and it is the same bill at every altitude."]`

Why this is load-bearing for Claude, from tonight's own error: Claude imposed a correct affordability invariant at
the align stage, it regressed, and Claude logged the cause as "wrong altitude." That was itself the mistake. There is
no altitude to get right -- the bill (budget) comes due identically during navigation, align, and the walk to the
lock. Applying the rule at one stage does not move it to a "higher" or "lower" altitude; it just leaves the other
stages uncharged. So:

- Do NOT reason as if raising/lowering abstraction changes the problem. It changes only where YOU stand to look at it.
- When a rule "should work" but doesn't, do not hunt for the right altitude to place it. Ask WHERE THE BILL IS PAID,
  and charge every place it is paid. The invariant applies wherever the cost is incurred, not at a chosen level.
- The abstraction method (lift when stuck, niche back down) is about the OBSERVER moving to see structure -- it never
  implies the structure or its cost lives at that altitude. Lift to SEE; the bill is paid at every rung regardless.

## The rest of the method, in order

- **Measure before and after every change.** Claude thrashed the pairing twice in consecutive turns by editing, then
  editing again, without measuring between. Both halves were right; the wiring was wrong twice.
- **Verify against the agent's own values, never hand-set ones.** See §II.3 — this is the single most repeated error.
- **Parse + import + bounds + fidelity after every splice.** They are cheap. They are also **not sufficient** — see
  §II.5.
- **Cut a downloadable revert copy before every bulk pass.** It has already saved the tree once (recovering a deleted
  `observe`). `[Isaiah #11]`: any number of changes is fine *provided* the copy exists.
- **Run tests in a SEPARATE turn** `[Isaiah #23]` — API-bound, can crash the turn.

---

# II. THE HANGUPS — what Claude gets wrong, every time

## 1. Claude's magic numbers do not stay Claude's. The agent inherits them as reasoning.

**This is the most important entry in this file.**

Claude ranked the readout hypotheses by observation count. The agent then said, in its own voice, on the record:

> `HYPOTHESIS readout := colours [9] ... support 681` — while the fuel bar sat at 505.

`681 > 505` **is not a reason.** Both candidates had passed the identical test; the count broke the tie. The agent
got the right answer for a reason it could not defend, and printed *"changes only under some of what I touch → my
CHOICE moved it"* **next to a fuel bar that drains on every action.** The justification was false of its own
candidate.

An invented metric does not stay in Claude's head. It becomes a sentence in the agent's log that Isaiah reads as the
agent's reasoning. **Claude's noise becomes the agent's argument.**

The fix was structural, not a better number: **credibility is SELECTIVITY.** A cause is specific — a thing that
changes under 2 of 7 things you touch and ignores the other 5 is being moved by what you touched; a thing that
changes no matter what you touch is running on something you are not holding. `[Isaiah confirmed: "the bar changes
under every antecedent; the glyph changes under one."]`

## 2. Five for five: Claude labels the load-bearing thing as noise.

In one day: the multi-grid records (`frame[-1]`, 4 sites) · the HUD panel (**it is the key**) · the colour-0 ring
(**it is the win signal**) · the `[2:56]` slice (`# play area: the HUD is not the world` — the key lives in the HUD) ·
and Claude's own "chrome by extent" fix repeating the identical error six hours after the first.

**Nothing is chrome until measured.** Observe the entire frame. `[Isaiah #6, #7]`

## 3. Claude validates against a fiction — a better-sighted agent than the one that exists.

Claude hand-set `terrain={3,4}` in a replay harness. The agent derives `[3,4,5]`. Every offline "verification" for
hours was of an agent that segments the board differently from the real one. The `contact=0 → recolor({5,9})` law
Claude rendered and built a whole mechanism around **existed only in scratch**.

**Rule: the replay harness takes its parameters from the agent, or the result is worthless.**

## 4. Claude invents vocabulary and then reasons inside it.

"Chrome". "Carve". Isaiah on both: *"I have no idea what you mean... and thats probably a bad sign, since i dont need
[it] to solve these games."* They are **object segmentation** and **classification**. Invented words hide bad
reasoning because there is nothing to check them against.

## 5. Parse and import passing does not mean the code is intact.

Claude's `_effect` splice ran `def _effect` → `def _rule` and **deleted `ObjectTransitionInducer.observe`**, which
sat between them. Parse passed. Every import passed. A missing method is not a syntax error. Recovered from the
snapshot. **After any splice, assert the methods still exist**, not just that the file compiles.

## 6. A record is not a frame. `frame` is MULTI-LAYER.

```
one ls20 run: 106 records, 119 grids.
  99 records carry 1 grid · 1 carries 2 · 3 carry 6 (animations) · 3 carry ZERO
```
`frame[-1]` is the settled state; **the event is in the EARLY layers**. Already written in the tree at
`objective_validator:2555`: *"It is MULTI-LAYER: the aligned WIN-STATE is an EARLY layer, not frame[-1]."*
When Isaiah says "frame 13" he means the **global grid index** across the flattened sequence, not the record index.

## 7. Claude reads a flat `levels_completed` as failure.

A level bump is **30–40 things right at once**. 20/30 solved shows no bump and is not failure. `[Isaiah #14]`

## 8. Claude jumps to the story already in hand.

Retracted in one session: *"the agent is minting boosters out of itself"* (the mint was correct; the addresses were
stale) and *"fuel==0 ⟺ GAME_OVER"* (widget conflation; `lives==0` is the exact one). Both had the same shape.

## 9. Claude reaches for a cleaner sentence than the evidence supports.

Three consecutive rewrites of one `why` string: "does the effect vary" (separated nothing) → counting
`(action, contact)` pairs (hid the answer) → an `_only` branch that declared **the fuel bar** explained by contact.
The ranking was right every time; the justification kept overreaching. Same reflex as everything else, aimed at prose.

---

# III. HOW ISAIAH WANTS TO BE TALKED TO

**Always: a visual, and the question in plain words.** Asked for repeatedly, in these words:

> *"show me what you are talking about make me a render"*
> *"explain that to me plainly and visually"*
> *"show me what you are talking about or speak more plainly or both"*
> *"can you show me that picture with some colors too?"*
> *"ask me your question plainly"*

He is not reading the code `[#25]` — he built the theory instead, because code is cheap now. **A render plus one
plain sentence is how he checks Claude's reasoning.** Long prose and long code comments are waste.

**Frame-mismatch protocol:** when Isaiah and Claude disagree about what is on screen — **render the exact frame from
the data immediately**. Do not reconcile in words. Origin: a level-numbering off-by-one burned multiple turns.

**When confused about the game: ASK.** `[#9]` *"claude should never find itself trying to figure out the puzzle.
always ask me, its the easiest, or i will supply you with the gif replay or the json replays."* And: **ponder it
visually — the animations of the frames — as Isaiah would.**

**Do not ask him for the answer to encode.** Claude asked *"is the identity you'd expect the agent to land on
positional?"* — that is asking for the answer to put in the code. Unforgivable one `[#3]`.

---

# IV. ls20 — how the game works `[Isaiah, verbatim + measured]`

**Do not re-derive. Do not encode.** This exists so Claude can read the agent's log and tell sound reasoning from
unsound — nothing else. `[#17: only a Claude who understands the game can tell a fluke from real transfer.]`

- **KEY** = the glyph in the HUD, bottom-left. **Unreachable.** The triggers change it.
- **LOCK** = the matching glyph on the board. **Reachable, unchanging, position differs every game.** Reach it to
  exit. **The key and the lock are the SAME COLOUR (9) on ls20** — no appearance test can separate them; only what
  the agent's own play has done to each.
- **Scale-invariant pair**: key 20px, lock 5px, 4× ratio, same `canon_shape` S1. A size-similarity test fights the
  match it is looking for.
- **Triggers** (e.g. the small white cross, colour 0) each cycle ONE attribute — colour, shape, rotation, *or
  something else*. **Never enumerate the axis.** Different periods. The avatar's **centroid** landing on one fires it.
- **White ring flash = matching / win condition met.** Transient: ~5 grids, gone by `frame[-1]`.
- **Level 6 proves the mechanic**: the readout is RED there (blue on level 2), the bar is YELLOW (grey on level 2),
  and the glyph is **a different shape entirely** — not a rotation. **Every colour-keyed rule is one level from
  silently wrong, and being wrong looks exactly like `stay`.**
- **Budget:** bar rows 61–62, cols 13–54 = 42 columns. **L1: 1 col/action (42 actions). L2: 2 cols/action (21).**
  The price CHANGES at the level boundary.
- **Lives:** colour-8 blocks, cols 55–63. `lives == 0 ⟺ GAME_OVER` (exact, 456/456 frames).
- **Refills have THREE causes:** booster, death-respawn, new level.
- **Avatar:** 5×5 composite — 2 rows colour 12 over 3 rows colour 9. Colour 9 is **not** unique to it.
- **RESET — the graduation bar `[Isaiah]`.** The ban is not permanent; it is a scaffold that comes off when the agent
  EARNS the capability. The bar: the agent solves almost every game unaided, hits one that genuinely requires reset,
  and **pontificates in its own rationale that it needs the ability** -- derives from its own play that it is stuck in
  a way no available action escapes, recognises return-to-start as the missing primitive, and explains why. The
  reasoning is the unlock, not the score and not us deciding. This is the residue rule (`the agent builds the
  primitive it lacks`) applied to a forbidden tool: reset is a primitive it may not use until it can demonstrate it
  understands the tool well enough to have invented the need for it. Until that rationale appears, the GAME_OVER-only
  gate stands. Do NOT lift it because a level looks unsolvable -- that is Claude solving the game.

- **RESET is shadow-banned during active play `[Isaiah, ruled]`.** Legitimate ONLY at game-start (no frame yet) and
  after GAME_OVER. Using it skillfully mid-level requires autonomy the agent does not have; mid-play it just throws
  the level away. THE BUG (Claude's, earlier session): the adapter gate read `_obs is None or GAME_OVER or _lvl==0`,
  and `_lvl==0` fires on the FIRST level -- where ls20 spends the whole game -- so 27 destructive resets landed at
  state=NOT_FINISHED. Fixed: gate is now `_obs is None or GAME_OVER` only. Verified: 0 mid-play resets after boot.
  Note the direct `RESET` GameAction and `adapter.reset()` both funnel through the adapter, so the single gate covers
  both. **Do not re-introduce a level-based reset clause.**
- **RESET:** measured — after GAME_OVER it restores the level's board and `levels_completed` holds. Still banned
  during active play.

**vc33:** buttons double per level (2→4→8).

**Frame-reading:** a level's true board is the **RELOAD frame** (~15% of cells change at once) — *not* the first
frame at a new `levels_completed`, which is the win-state of the level just cleared.

---

# V. THE LIVE PATH

```
online_harness.run_online(brain != reasonfirst)
  -> play_game_submission -> integrated_agent.MyAgent      <- the class Kaggle's submission_agent.py loads
    -> _should_route_composer() == True for ALL games
      -> my_agent.MyAgent (_QueueAdapter) -> validate_multilevel -> validate -> explore_and_map -> WorldModel
```

- `play_game_engine` is disabled and raises. `reasonfirst` (`ouroboros_integrated`) is retired.
- **`adapter.step` is MONKEYPATCHED** by `_install_grammar_ride` (`objective_validator:2264`, installed at 4154 and
  7486). **Reading `_QueueAdapter.step` tells you nothing about what runs.**
- **Two silent doors to a v18 fallback** (composer import fail, construction fail). v18 has no reasoning services →
  fingerprint is `reasoning: null` on every action. Alarmed; `OURO_STRICT_BRIDGE=1` refuses.
- **`spatial_map.py`** (237 lines: `ego`, `reachable`, `nearest_reachable_to`, `frontier_step`, `coverage`,
  `blocked_edges`, `decay`, `distance`, its own `_say` narration) is imported **only by `ouroboros_integrated`** — the
  retired branch. The live path uses `objective_validator._spatial_mem`: **38 lines, one function, none of those
  methods.** Orphaned by the routing change, reimplemented at 16%.
- **`explore_and_map`**: 540 lines, was **0 emits** — violated `§1.4 NOTHING MAY HAPPEN SILENTLY`. Now narrates
  `MAP` and `WORLD-MODEL`. First thing it said: `explored 0 cells`, `action-map all zeros`, `fidelity 0.24`.

---

# VI. ENV

- Temp key: **env var only, never in any file, notebook, or artifact.**
- SDK: `pip install arc-agi arcengine arc-agi-3 --break-system-packages` (fresh container has none).
- `arcengine.GameAction` vs `arc_agi_3._structs.GameAction` — **different classes, both install** → the `.reasoning`
  AttributeError. Guarded at `integrated_agent.py:352`.
- Working dir `/tmp/nb`, flat, 65 modules. ls20 mechanics/grids/objectives: **scratch only, never a persistent file.**
- Hard bounds: `regime_factory.check_no_downsampling()` (not `kernel`) · `no_posthoc` import-time ·
  `test_marketplace_fidelity.py`.

---

# VII. STATE, 17 July 2026

**Fixed and live-confirmed:**
- Whole frame + every layer to the learner. `LAYERS this action produced 6 frames, not 1` fires live.
- `_effect`: one general verb (`restate` = became different in place), shape tested **before** position. Was filing
  36 rotations as `translate` because the arm swing moved the centroid 2 columns.
- Object permanence (`_track`): identity founded at first sight, carried by overlap, survives recolour/reshape.
  Table keys on persistent identity, not current paint.
- Shared per-game evidence table (`bind_table`) — 769 → 4277 support across 2 episodes. Re-segmentation no longer
  **clears it** (Claude's own bug: `_oti.table.clear()` was wiping the shared table).
- Segmentation narrates as a revisable **belief**, not a fact.
- **Composer crash dead**: 3 runs, 0 deaths, steps 130/178/197 → **502/529/521** (it now runs its full budget).
- The agent **names the readout itself**: `HYPOTHESIS readout identity := [9]` with selectivity reasoning. First time
  in the project's history, with no HUD concept, no colour hint, no screenshot.

**Fixed in the autonomous session (17 July, cont.) — all live-confirmed:**
- **A hypothesis need not be confirmed to be a hypothesis.** `readout_hypotheses` required `status=="confirmed"`;
  confirmation needs REPETITION, and the readout's law is rare BY DESIGN (3 changes in 522 live actions) while the
  bar's is constant (469). The common thing confirmed instantly, the informative thing never surfaced. Removed the
  gate → ranking flips to `[9]` on the run's own evidence. `[Isaiah #19: an unearned guess is a hypothesis.]`
- **Target no longer required to share the readout's colour** — an ls20 accident Claude had written in.
- **One object system**: `_keylock` reads candidates from the tracker that holds the change evidence (`loci()`),
  not from `by_col` matched by proximity. Two segmentations disagreeing was why 0 glyphs paired.
- **`iou >= 0.5` removed** from `_track`. Claude defended it as "a definition, not a dial"; measured on the readout's
  rotation it was **0.429** and failed on the exact event it existed for. Best-overlap-wins, no threshold.
- **Tracks persist through non-observation** (occlusion) but **die on evidence** — when their cells are ≥50% occupied
  by live objects now, they are gone, not merely unseen. Without the death test, ghosts hit 46/59 by action 377.
- **"Changed" means RESTATED, not moved.** `_track_changed` was flagging `translate`/`vanish`, which painted the
  avatar's whole breadcrumb trail as "changed" and emptied the never-changed pool the target lives in. Now only
  restate/recolor/rotate count → pool holds at 52, only `[9]` and `[11]` flagged.

**Result:** the agent now, from COLD, at action 27: names `readout identity := [9]` by selectivity, locates the
instance, pairs it against a never-changed glyph, runs COMPARE, and cycles the key from differing on
`[shape,orientation,colour]` down to `[orientation]` alone. Best reasoning in the project's history. `max_level` 1 on
most runs, 0 deaths across ~15 runs.

**Open — the live edge:**
- **The pairing is RESOLVED (17 July, late).** The instance problem — both HUD panel and lock are `[9]` and both
  restate — is settled by **Signal C as a measured approach floor**: per-track minimum body-approach distance
  (`near`), accumulated. On-board glyphs reach min-distance ~2; the HUD panel never gets below 28-42, over 200+
  samples. A 10x gap, no threshold tuned. READOUT = ranked identity, changed, `near > 8` (driven at a distance);
  TARGET = a glyph the body reached (`near <= 8`). Live-confirmed: `readout := (59,7)` the panel, `target := (27,31)`
  on-board, roles correct, `COMPARE ... differ on ['shape']`. This was the 4x-thrashed junction; the ABSTRACTION
  METHOD resolved it (lift to "which did my body ever get near", let the 2-vs-28 gap decide).
  - **Required a second fix underneath:** `_track_changed` was keyed on `tid`, so a ring-flash re-segmenting the panel
    minted a fresh tid and LOST the restate history exactly when the readout did its job. Re-keyed on
    `(identity, cy//8, cx//8)` — survives re-segmentation, still separates readout-region from lock-region of a
    shared identity. Same disease (identity keyed to shifting segmentation) at its FOURTH layer.

- **The align read-miss is FIXED.** `_differ` returned `['?']` on a single-frame read miss mid-cycle (glyph caught
  between states), and the align loop cannot act on `['?']`. Fix: cache the last good key/lock reading in game_mem
  and HOLD it through a transient miss, re-reading next frame, instead of collapsing to unknown. Ground truth (from
  the full 7-level replay): cycling is modular and the readout passes through unreadable intermediate states between
  steps, so missing one is expected. Verified: `['?']` appearances 0 across runs; nothing else regressed.
- **Reset gate widened correctly:** the API needs a real RESET to START/RESTART (game-start, GAME_OVER, and the
  NOT_STARTED/NOT_PLAYED state after a death) -- gating on "GAME_OVER" alone was too narrow. Mid-play (NOT_FINISHED,
  live board) reset stays banned. The `GAME_NOT_STARTED` errors in logs are a harmless startup retry race (reset
  succeeds, first action probes before it settles), present in good runs too -- NOT a regression.
- **FIXED: inert triggers were stored as untested, causing endless re-probing.** A trigger probed and found to do
  nothing was recorded `cmap[ttype] = {"effect": None}`. The reuse gate checks `cmap[ttype].get("effect")` and None
  is falsy -> "characterised as inert" was indistinguishable from "never tested" -> the agent re-navigated to and
  re-probed the same inert trigger every pass (measured: type (9,..) 4x in one life, RECOGNISE never fired). Fix:
  inert is now a POSITIVE verdict `{"effect": "inert", ...}`. Verified: RECOGNISE now fires, and it CORRELATES with
  clearing level 1 (runs that reuse verdicts reach lc=1; runs that don't stay lc=0). `"inert"` threads correctly
  through every effect-consumer (align gate at 5370 checks `in props`; booster check at 4938 checks `in (None,
  "budget")` -- inert is excluded from both). This is the SAME disease as the object-table fix: a result that dies /
  reads as absent instead of accumulating as knowledge. It was the "re-runs the experiment every life" symptom.

- **NEXT: re-navigation DURING characterization (a second layer).** Even with the verdict fix, the agent
  re-navigates to a trigger multiple times WITHIN one characterization (the `for _visit in range(4)` probe loop plus
  the navigate-to-probe fire repeatedly before `cmap[ttype]` is written). Re-probe repeats did NOT drop (still 3-6/
  run). This is a within-characterization inefficiency, SEPARATE from verdict-reuse. It is likely why lives are still
  spent expensively even when reuse works. Diagnose the probe loop's navigation next -- fresh problem, not a
  continuation.

- **[EARLIER FRAMING, PARTLY SUPERSEDED] BUDGET OVERSPEND DURING NAVIGATION -- upstream of align.** Tried imposing the
  affordability invariant (THE BILL, §1.3a -- "no spend that leaves the whole objective unpayable on some schedule,
  priced in the agent's own currency") at the ALIGN/DETOUR stage. It REGRESSED (0/5 vs 2/5) and the `BILL` narration
  never fired -- because the agent dies at ~150 steps BEFORE reaching align. The debt is run up during
  navigation/exploration: the winner walks a ~41-action path on a ~42-action meter; ours WANDERS and bleeds the meter
  before it ever pairs+aligns. A prior session wrote this in the comments and Claude half-passed it. REVERTED to the
  READHOLD checkpoint. **The invariant is RIGHT; I applied it at ONE stage while the bill comes due at EVERY stage.** It must price
  EVERY action during navigation/exploration against the remaining bill -- not just the detour. NOTE the framing
  correction below: "wrong altitude" was itself a wrong diagnosis. The bill is the same at every altitude; my error
  was applying the rule to one stage (align) while the agent pays the identical bill during navigation. Not an
  altitude I mis-set -- a stage I failed to charge. That is structural (touches how nav
  decides to move), not a bolt-on. Do it fresh, with Isaiah, not tired. FMap framing (Isaiah): impose "every step
  must leave the whole bill payable" as the invariant at the abstract/allocentric altitude; the agent transforms it
  through its own Pose (its rate, its meter, its path) into concrete moves -- keeps agency, reasons to the answer in
  its own frame. The booster overspend is a SYMPTOM of the wander, not the disease.
  - META-LESSON (Isaiah's, made concrete): Claude imposed a correct higher-frame rule at the WRONG frame boundary --
    guarded the align door while the agent died in the hallway. Same "fix the stage I'm looking at, not the stage
    where the problem lives" = producer-before-consumer, again. Only measurement caught it (the BILL emit never fired).

- **[SUPERSEDED] BUDGET-DETOUR OVERSPEND.** On level 1 the budget is short (~21 actions). The
  agent reasons the whole way (MODEL/RESIDUAL/PROGRESS all firing) but collects boosters / detours and runs the meter
  to zero before it aligns and reaches the lock -> GAME_OVER at ~150 steps, lc=0. 2 of 5 runs reach level 1; the rest
  die of budget here. The booster-detour must check it can afford the detour AND the align AND the walk-to-lock, not
  just the detour. This is the live ceiling now -- align reasoning itself is sound (ground-truth confirmed).

- **GROUND TRUTH (proctor-only, NEVER encode):** full 7-level replay confirms — matching key==lock only UNLOCKS; the
  avatar must then walk onto the lock to complete (verified: avatar closes on lock at every level-up). The readout
  MUTATES across levels: base colour 9->9->12->8, shape changes too (level 6 genuinely different shape). Cycling is
  modular/forward-only (overshoot = loop again). A level may require aligning MORE THAN ONE attribute (colour+size
  move together as the ring transient; shape/orient is the rarer real cycle). The agent's PLAN ("pair, enumerate
  differing attrs, cycle each via triggers, walk to lock") is the CORRECT decomposition — preserve it; fix only
  execution.

- **[SUPERSEDED] the align does not converge — DIAGNOSED, not yet fixed.** After correct pairing + `COMPARE differ on
  ['shape']`, the agent navigates to triggers and cycles the key one step at a time (this logic WORKS — SUBGOAL/
  NAVIGATE/PLAN all sound). It stalls because the sub-goal degrades to `['?']` around action 189. Traced precisely:
  the pair is NOT lost (`_keylock` keeps succeeding, no "no pair" emit after 85) and the key IS readable (a 4px [9]
  blob sits 1.0px from the key-pos at the stall frames — measured). So `['?']` is `_differ` hitting
  `gk is None or gl is None` on a SINGLE frame mid-cycle, when a glyph is transiently between states. The fix is a
  RETRY, not a re-plumb: a one-frame read miss during cycling should be re-read, not resolved to `['?']` (which the
  align loop then can't act on). **Do NOT re-plumb `_read_at`'s object source — that was a wrong hunch, disproven by
  measurement (the blob is right there).**
  - Secondary: at budget ~2 the agent commits a 5-action booster detour (`costs 5 of ~2`), overspending and dying
    ~300 steps. Budget-gated detour needs to check it can afford the detour AND the exit. Downstream of the align.

- **THE ABSTRACTION METHOD `[Isaiah, core]`:** when stuck, LIFT the problem to where its structure shows — name the
  candidates and the signals that could decide — let the answer shake out at that altitude, then niche back down to
  specifics. For Claude: render options plainly + visually, decide on the shape not the coordinates. The agent must
  do the same when its play thrashes. This is now in `THE_ALIGNMENT.md` §6.
- **Trust-and-commit `[Isaiah, ruled]`:** when the agent reads a match it should TRUST it and commit (walk out). If
  the read is wrong, fix the underlying pipe — do not teach the agent to doubt itself. `_differ` read a match at
  action 168 then differed again at 193; that is a pipe to fix, not a reason to add re-verification.
- Evidence-starvation is RESOLVED within a run by the fixes above (cold-start reasoning works by action 27). The
  cross-process question stands: `#30` says always cold, but the 25-game OOD run is one process so the shared table
  accumulates across games. Not yet an issue at ls20 scale.
- Terrain/segmentation still a **set**, not a probability gradient. A wall is a **bound** (causal: I could not pass),
  already derived as `contact=3→translate, contact=4→stay`; `terrain={3,4,5}` overrides it with a colour list.
- `explore_and_map` action-map all zeros / `controllable := 12` (composite bug) while `self_signature()` derives
  `[9,12]`. Two systems answering "what do I control"; wrong one feeds the planner.
- Strip Claude's long comments from 17 July `[#25]`.

**Revert ladder (each a downloadable zip in outputs, latest last):** PRE_PERCEPTION → PERCEPTION → IDENTITY →
SELECTIVITY → COMPOSER_ALIVE → HYPOTHESIS → PERMANENCE → **POOLS (current)**.
