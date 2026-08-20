# BUILD PROGRAM 2 — THE FULL BUILD-OUT (swarm stopped until QA passes)

DATE: 2026-08-14. AUTHORITY: Isaiah — "stop it all... build everything out... checked
against the instrumentation QA... only then do we restart." Acceptance: (1) everything
built; (2) everything wired (consumer gate: no orphans, no stale allowlist); (3) NO
ID-BASED NONSENSE — OOD sweep proves no hardcoded game ids/absolute-coordinate magic in
production code (game ids as RUNTIME KEYS for per-game learning are legitimate — the
mechanics transfer, the keys are data); (4) QA = ruff+vulture+hypothesis+full gate suite
100% green + OOD lint clean + ship-clean import lint + cold-ship smoke. THEN restart.

## WAVE OWNERSHIP (disjoint files; interfaces fixed here)
W1 THE LOOP WAVE — owns cognitive_loop.py, cognitive_game_player.py,
   engines/egocentric/frontier.py, engines/egocentric/swallow.py (new):
   B1 level-0 harvest CONSUMPTION (read gate level>=1 -> level>=0; same conservative rules)
   B2 movement affordances: actions 1-5 banked per-episode as {action -> displacement/
      frame-change outcome} records (the six click-less games stop re-exploring blind)
   B3 planner-DRIVE consults the frontier veto before clicking (audit-note fix)
   B4 SWALLOW COUNTERS (G1): per-guarded-block exception counts, enum-coded block names,
      <=1 record/block/episode to personal "swallow" stream + [SWALLOW] narration;
      consumer = same starvation_steer read path (effort only)
   B5 starvation -> seed_bias full wiring (not just probe cap)
   B6 NO_NEGATIVE_INSTANCES feeder (binder negative-evidence counters)
   B7 salient-prefix bank: near-miss action prefixes deduped by outcome-state hash,
      PLAYBACK CHANNEL ONLY (DB-side, never the fabric — membrane law), replay with
      divergence detection
   INTERFACE: calls engines.egocentric.consumer.seed_imports(gamma, fabric, game, level)
   -> int at the fabric-load site (one compact call; W3 provides it).
W2 THE VOCABULARY WAVE — owns engines/egocentric/effects.py, binder.py, bank.py, router.py:
   B8 OBJECT-LEVEL transform classifier: per-changed-connected-component classify
      (mover TRANSLATE within cluttered context etc.) -> typed atoms fire on real
      transitions (fixes typed=3/585 -> the g7 precondition)
   B9 conditional-effect constructor (arity-3): EFFECT_IF — same action+context,
      divergent outcomes correlated with remote state predicate -> conditional atom
   B10 class-fission socket: bimodal settlement outcomes for one class -> split identity
       (hidden types; essentialism + Xu-Carey), probe aimed at the split
   B11 agent-motion predictor family (flagged AGENT_MOTION=on): animacy -> approach-vector
       goal inference -> efficiency next-step bets; settlements decide policy-vs-mechanism
W3 THE IMPORT ECONOMY WAVE — owns engines/egocentric/consumer.py (new), janitor.py (new),
   mint.py (sigma field only), tools/sigma_backfill.py:
   B12 TRIANGULATION CONSUMER: drains import_queue; sigma-first lookup over ALL mounted
       fabrics' atoms (ttype/params + invariants: arity, bbox shape class, changed count,
       colour-delta set, conservation); THREE CONDITIONS seq-provable; near-miss logging
       (all-but-one invariant); redescription loop (sharpen the named invariant, retry);
       KIN-ECHO LAW: reputation effects exclude/down-weight same-lineage echoes; output =
       "import_candidates" records; seed_imports() enters them into Gamma flagged
       imported=True — planner still requires 2x TRANSFERRED (wheel rule untouched)
   B13 sigma AT MINT TIME for all new atoms (raw included) + tools/sigma_backfill.py for
       the 582 legacy atoms (from stored before/after; no re-observation)
   B14 FABRIC_JANITOR (per PREREG_SMART_CLEANUP): size-triggered compaction; FALSIFIER =
       byte-equality of every consumer-visible query result pre/post compaction; loud
   B15 R3 allowlist: DELETE import_queue entry (it now has its consumer)
W4 THE SHIP/QA WAVE — owns tools/ood_lint.py, tools/cold_ship.py, tools/control_arm.py,
   tools/n1_metric.py, tests/gate/test_ship_clean.py, test_compat_old_books.py, fixtures/:
   B16 OOD LINT (Isaiah point 3): full-scan of production code for hardcoded game-id
       string literals, absolute-coordinate magic constants, level-number specials;
       runtime keying by game/level VARIABLES is legitimate and not flagged
   B17 compat fixture pack: frozen old-era record shapes (atoms sans ttype/sigma,
       settlements, harvest, verdicts sans w) + gate test: every consumer reads old books
   B18 ship-clean import lint (gate): production imports = stdlib + numpy ONLY
   B19 cold-ship smoke: bare-venv (stdlib+numpy) module-import + synthetic-cycle dry run,
       no network — the Kaggle parity check
   B20 control-arm driver (G2): paired boxes, two shas (git worktree), same game, N
       episodes each, delta report — future verdicts read as arm deltas
   B21 n=1 discontinuity metric: per-atom time-to-first-mint vs time-to-first-TRANSFERRED
       from fabric seq (refit-vs-remint audit, incl. ar25 L1->L2)
PROCTOR: G5 pinning (requirements-dev.txt), coordination, independent QA, restart.

## DEFERRED WITH REASONS (honesty over completeness theater)
- mutmut nightly: hours-long; add after restart as cron, not a build artifact.
- pyright strict ratchet: typing refactor across untyped legacy = regression risk for
  marginal gain now; module-by-module after depth returns.
- alpha/EWMA precision: lives in the ICED marketplace path (sha-frozen); upgrade only
  if/when the marketplace is un-iced.

## VERDICTS (registered now, checked before restart)
Every wave: failing-first tests; suite 100% green (target >251 tests); ruff/vulture
clean; socket/filler lint clean per commit; OOD lint clean; consumer gate: zero orphans,
zero stale allowlist entries; cold-ship smoke passes. Post-restart (first two beats):
g7 > 0 somewhere (B8's typed vocabulary is the registered unlock); import_candidates > 0
with >=1 TRANSFERRED verification of an imported atom (B12); [SWALLOW] baseline recorded.
UNDO: every wave a separate commit; revert per commit.
