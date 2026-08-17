# PREREG: RANKED DRAIN (behavior) + ORIGIN MARKER (instrumentation)
DATE: 2026-08-17. AUTHORITY: Isaiah rulings 1 and 5. Ships together because the origin
marker is pure instrumentation (a field written at mint) and cannot confound the drain
verdict; the drain change is the only behavior change in this wave.

## A. RANKED DRAIN (Isaiah: "take the most performant, or ranked predicates")
Today: consume() drains OLDEST-FIRST, budget_n=8, through ~370k pre-characterization
records that can only produce frame-free sigmas -> 100% declined at the completeness
guard, while 82,301 characterized residuals sit unreachable behind them.
BUILD: rank the drain queue instead of FIFO. Ranking key (Register G, GUESSED, one row):
  (1) CHARACTERIZED FIRST (complete sigma: all 5 invariants present)
  (2) then LARGEST RESIDUAL (most unexplained first)
  (3) then RECENCY (newest first) as the tiebreak
Bounded: rank only a bounded window of candidates per pass (no full-queue sort).
OFF-ARM (ablation clause, ships as a PASSING TEST): DRAIN_RANKED=0 reproduces
oldest-first byte-identically (same records, same order, same outcomes).
FALSIFIER (failing first): a synthetic queue holding old sigma-less records + newer
characterized ones drains the CHARACTERIZED ones first under the ranked path and the
OLD ones first under the off-arm; declines on characterized records are zero.
REGISTERED VERDICT (2 beats post-deploy): the decline rate falls and candidates>0
appear; if declines stay at ~100% with characterized records reaching the guard, the
diagnosis was wrong and the ordering was not the blocker.
UNDO: one call site; git revert.

## B. ORIGIN MARKER (Isaiah: "this distinction should be marked")
Today: ZERO atoms carry imported/source_game; local-vs-imported is carried by ABSENCE
of fields, which collapses silently the moment anything writes them.
BUILD: every atom record gains, AT MINT/SEED TIME, a positive marker:
  origin = "local" | "imported"; mint_seq; source_game (imported only).
Additive; old books read unchanged (absent origin => UNKNOWN, never inferred as local).
FALSIFIER: a locally minted atom carries origin=local + mint_seq; a seeded import
carries origin=imported + source_game; a legacy record reads UNKNOWN and no consumer
infers local from absence.
PURPOSE (Isaiah): charts learning and growth across episodes — and it is the ONLY
discriminator between corroboration (convergent minting) and surplus (adopted import).
