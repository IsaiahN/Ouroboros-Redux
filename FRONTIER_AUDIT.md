# FRONTIER AUDIT (2026-08-17, read-only; receipts in the task record)
HEADLINE: the frontier IS reached, IS banked, IS consumed. It is not blocked by
amnesia. It is blocked by budget eaten by playback, path-blindness, and an inflated
blacklist.

## F-1 THE CORPSE REPLAY (worst; 13/13, zero ambiguity)
ar25: EVERY ONE of 13 salient-prefix replays ends in GAME_OVER on the FIRST cognitive
action after playback; [SALIENT] divergence fires ZERO times in the entire log. The
detector is not broken — the replay is FAITHFUL, and what it faithfully reproduces is
the death. Cause: _bank_salient_prefix banks "up to the LAST effectful action", and a
DEATH CHANGES THE FRAME (changed=True), so the death step IS the terminal banked step;
the divergence check then matches the corpse's own post-hash. CLAIM.md's fail-closed
clause anticipated a stale sequence degrading; the actual failure is a sequence that
still applies perfectly and replays a corpse.
## F-2 BUDGET: 318 OF 450 ACTIONS (71%) ON PLAYBACK -> ONE COGNITIVE ACTION AT THE
FRONTIER. 121 actions winning-sequence replay to reach L2, then a 197-step salient
prefix ending in death. The frontier is never explored because nothing is left to
explore with.
## F-3 DEAD-CELL BLACKLIST INFLATED ~4x (INCONSISTENCY, docstring vs code)
frontier.py documents dead as ">=2 INDEPENDENT records"; the code increments per LIST
ENTRY and the caller never dedups, so ONE episode clicking a cell twice blacklists it.
Live ar25: L2 dead(as coded)=163 vs dead(as documented)=41 — 122 cells (75%)
blacklisted by within-episode repeats alone. Nothing decays it (no recency term; the
janitor is severed), so elimination is MONOTONE across all episodes and recycles.
## F-4 "DEAD" IS A PROPERTY OF A CELL, NOT A STATE (SEMANTIC-FALLACY): a cell inert in
board config A and load-bearing in config B is permanently vetoed after two clicks in A.
## F-5 LEVEL MIXING (INCONSISTENCY): _ego_frontier_dead/effects are never reset on
level change; an episode running 0->1->2 banks its L0 and L1 clicks as L2 frontier
experience. (Replayed clicks do NOT pollute — that path is clean.)
## F-6 ALTERNATIVES: PER-CELL YES, PER-PATH NO. frontier_harvest stores UNORDERED SETS
— no ordinal, no route, no "what I tried and where it failed". The system can vary
WHICH CELL it clicks; it can never vary THE ROUTE. And the one ordered per-level bank
(salient_prefixes) is selected ORDER BY uses DESC — a self-reinforcing argmax: the
first prefix used once wins forever, and ar25's SEVEN alternative L2 prefixes have
NEVER been tried.
## F-7 SIX FRONTIER DB TABLES: ZERO ROWS EACH (frontier_discoveries, _checkpoints,
_level_topology, _exploration_confidence, near_miss_patterns,
eliminated_click_coordinates) — severed by route or never written.
## F-8 ARCHAEOLOGY (dated): the wasted-action detector (ReplayLearningEngine, 2026-01-13)
lost its caller 2026-01-29 and became unrecoverable 2026-02-01. THE MAINTAINER'S OWN
SEGMENTATION PRACTICE WAS MECHANISED 2026-01-20 as MasterySystem's ablation
(replay with random indices SKIPPED, record whether the level still falls;
ablation_test_results carries skipped_indices/skip_rate) — it is still wired in
game_player.py but SEVERED BY ROUTE (evolution_runner delegates to CognitiveGamePlayer;
GamePlayer.play_game is the exception fallback only). 0 rows. MasteryLite kept only
replay_probability, dropping ablation and improvement.
## F-9 SEGMENTATION IS POSSIBLE FROM EXISTING DATA — MEASURED: action_traces carries
per-action frame_changed and joins to a banked sequence by the ordered (action,x,y)
window UNIQUELY (session_id is severed — 'cognitive_session' literal — and is not
needed). Result: ar25 L1 seq = 4 productive of 63 (94% INERT); L1 improved seq = 4 of
42; L2 seq = 6 of 58 (90% inert). Dead runs are LONG AND CONTIGUOUS (L2 positions 4-18,
23-34) — natural segment boundaries, not scattered noise. salient_prefixes needs no
join at all (changed stored inline per step: 145 changed / 52 unchanged of 197).
CAVEAT (load-bearing): frame_changed is INERTNESS, not NECESSITY — an inert action can
be a required state-machine step. Any cut must be VERIFIED BY PLAYBACK, which is
exactly what the dead ablation path was built to do. And replay_wasted_actions'
schema already carries `verified_removable` — the exact field, never written.
## CHEAPEST FIXES, PRICED (not proposed as work): (a) never bank a terminal step
(kills the corpse replay); (b) the per-entry dead count (4x over-blacklist); (c)
uses-DESC lock-in (7 banked alternatives unreachable). Each is alternatives-generating
on its own.
