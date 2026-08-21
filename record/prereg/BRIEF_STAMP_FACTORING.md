# BUILDER BRIEF — STAMP FACTORING (reads PREREG_STAMP_FACTORING.md first; the ruling is in it)

Repo: c:\Users\Admin\Documents\GitHub\Ouroboros-Redux, branch v4-cold. HOLD is up
(.runs/swarm/HOLD) — do not remove it, do not commit, do not write under .runs/. Never read
docs/GAME_TRUTH, ouroboros_cpu/objective_grammar.py, or anything under
"C:\Users\Admin\Documents\GitHub\train set answers". Never print .env.

## What you build (the prereg's Mechanism 1-5, under the ruling)
A. `effects.learn_effect(before, action, after, self_cells=None)`. With `self_cells`
   (a set of (row, col)), clear those cells from the diff mask BEFORE bbox/ctx/out/key/
   changed. Inside the remaining bbox, self cells are DONT_CARE in context and in
   transform.before/after. All-self diff -> INERT. `self_cells=None` -> byte-identical
   output to today (F3 asserts this on a recorded corpus; build that corpus from the test
   fixtures already in tests/gate/test_effects*.py / test_mint*.py, not from .runs).
B. THE RULE, as code: the self cells are EXACTLY the avatar's cells in `before` (from the
   locus) plus those cells displaced by the action's KNOWN BODY delta. If any of those
   cells' before->after values are NOT what the delta predicts (vacated cell not taking
   the background/under-colour the delta implies; destination cell not taking the avatar
   colour), that cell is NOT subtracted — "the delta explains the subtraction, or the cells
   stay." Put the cell-set derivation in ONE pure helper (name it; exemplar for purity:
   `enables.act_offset`) so the mint and the stamp call the same one.
C. The mint's coarse signature: `MDLMint._signature(b, a, action)` and `_atom_signature`
   must apply the SAME subtraction (via the same helper) or the re-point never matches
   factored atoms. State in the registry row that this is one helper, two callers.
D. Callers: the ego layer already holds the locus and the per-action BODY deltas (the
   composer receives `avatar` and `deltas` — find where cognitive_loop passes them into
   compose and reuse THOSE values at the stamp site; do not add perception). If either is
   absent for this action -> `self_cells=None`.
E. Marker: new mints carry `factored: True` on the RECORD envelope (not the atom). Read it
   only through one total reader (exemplar: `effects.origin_of`); absence is the
   pre-factoring vintage, never inferred. Vintage atoms are NOT rewritten.
F. The two notes D-12 lacked: `_note("no-anchor")` at composer.py:571 (the else branch
   when no candidate/enabler anchors) and `_note("no-reach")` at :543 (reach None).

## Gates (tests/gate/test_stamp_factoring.py; F-numbers are the prereg's)
F1 OFFLINE: from sp80's stored level-2 frame pairs — read `core_data.db` table
   `action_traces` for game sp80-589a99af (frame_before/frame_after/action; the diagnosis
   found 461 decodable pairs at level_number=1) — re-stamp with self_cells derived from
   the avatar colour 14's locus in each before-frame and the BODY delta for the action
   (take deltas from the box's frontier/BODY records; if you cannot derive a delta for a
   pair, that pair is self_cells=None and is reported as such, not skipped silently).
   Assert the distinct coarse signatures among the WANT-colour-8/9 effects collapse from
   17 to <= 3. If they do not, STOP and report the signature census — do not tune.
   (This test reads the live DB read-only; mark it with the existing live-data marker the
   suite uses for such reads, or skip-with-reason when the DB is absent.)
F2: factored atoms anchor on > 0 of those stored frames; the `[[14]]`-class atoms' anchor
   counts are unchanged.
F3: self_cells=None -> byte-identical learn_effect output on >= 200 recorded events.
F4: tests/gate/test_system_determinism.py stays green (self_cells come from loop state).
F5: the two composer notes appear in the PLAN record's notes on a constructed
   no-anchor case and a constructed no-reach case.
Known-negatives as tests: avatar dies (cell -> a colour the delta did not predict) stays
   in the diff; a tile under the avatar changing stays minted; colour-14 recurring
   elsewhere in the bbox is NOT subtracted (the colour-anywhere failure, asserted absent).

## Discipline
- Module-bottom helpers; zero receipt rot — refresh every WIRING_REGISTRY.md row you move
  and state the drift. KNOBS.md: no new numeric constant without a row; the marker and
  the rule are PINNED by this prereg, not GUESSED.
- ruff: zero new findings. Run the full `pytest tests -q` once at the end; report the
  verbatim tail and every red, yours or not.
- Non-pinned decisions: list them; do not bury them in prose.
- Another builder's uncommitted work may be in the tree; touch only effects.py, mint.py,
  composer.py (the two notes), the ONE stamp call site in cognitive_loop.py, your test
  file, WIRING_REGISTRY.md, KNOBS.md. Name anything else you needed and did not touch.
