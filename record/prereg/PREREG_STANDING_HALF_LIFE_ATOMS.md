# PREREG — STANDING_HALF_LIFE AT THE ATOM GRAIN: THE DISLODGING GAP (2026-08-21)

**AUTHORITY:** `record/findings/F1_VERDICT_AND_SHADOW_TEST.md` Part 2, GAP 1 (proposal approved by
Seat 3 → this prereg); `REFACTOR_PLAN_AND_READ.md` R3 (`standing_half_life`: standing expires unless
re-earned) and R4 (the second root: a past outcome priced as a present one). **STATUS: PREREG, no
code.** Mechanics only, predicates named, no game specifics.

## THE GAP, restated from the code
- `effects.Gamma` only grows: `add` appends, `get` is last-wins, every update is a superseding append
  (`ctx_min`, `ctx_conflict`, `settled`). Nothing ranks, nothing retires.
- `planner._candidate_ids` returns EVERY id valid at (game, level), sorted lexically: an atom that has
  mispredicted a hundred times enters the search on equal footing with one that held a hundred times.
- `scheduler.PlannerScheduler.plan_wrong` is a ledger "deliberately not yet a demotion": in-memory, per
  process, unpersisted, consumed by nothing. `mint._conflict_clause` tightens a diverging atom's context
  (never loosens) — it makes the atom MORE specific, never LESS ranked.
So the Dislodging residual — *this atom keeps being wrong and still ranks* — has no expression today.

## STANDING, concretely
**One clock:** the A3-4 episode ordinal `ep` (advances on (game, level) change; the mint stamps it on every
verdict). Every standing event carries it, or is joined to a record that does.
**EARN events E(a)** for atom a: (e1) its mint verdict (`mint_verdicts`, verdict=mint, key=a.key, ep);
(e2) each rederivation verdict on its key — the NOVELTY hit, W2's "rederivation strengthens the entry",
now literally; (e3) each HELD step: a driven plan step that landed (the abort router's no-abort branch,
today an early return that records nothing), recorded per step atom; for composites, stage 4's
`settled: true` append.
**MISPREDICTION events M(a):** (m1) each plan-wrong routed against a as a step atom (`on_abort(PLAN_WRONG)`,
today the ledger increment), persisted by stamping `steps` + `ep` on the PLAN abort narration record that
already fires; (m2) each `ctx_conflict` superseding append on a from the OBSERVATION-time conflict clause.
**Disjointness:** the stage-4 plan-wrong path writes a ctx_conflict AND a ledger increment for one event;
its append carries an additive `via: plan-wrong` envelope marker and counts under m1 only. One event, one
count. Composites are ids like any other: their settles and their routed plan-wrongs are their events.
**The number:** `S(a, t) = Σ_{e∈E(a)} d^(t − ep_e) − Σ_{m∈M(a)} d^(t − ep_m)`. Both sides decay at the SAME
rate: an old misprediction fades exactly as an old confirmation does (R4 binds failures too — pariah
decay's symmetry, per W5). Computed per game from the books, incrementally in memory (the
`mint._refresh_sig_index` pattern), re-derived from the streams on restart — the affect REPLAY
requirement transplanted: two processes over the same books compute identical S for every atom.

## THE DECAY RULE — derived, not borrowed
Prestige (`engines/social/prestige_engine.py:214-235`): geometric, 3% per generation, `max(raw, decayed)`.
Its tick is the GENERATION because that is the unit at which a contribution can be re-earned. An atom's
re-earn unit is the EPISODE: within one episode CK-2c's surprise weight already discounts repetition;
across episodes an atom either re-appears or does not. So the tick is `ep`.
**Rate, from the population's own cadence:** let g(a) = the median gap in episodes between successive earn
events of a, over atoms with ≥ 2 earn events in distinct episodes; g* = the population median of g(a) for
this game. **d = 0.5^(1/g*)** — the half-life is one typical re-earn interval. Meaning: an atom re-earned
at the typical cadence holds level standing; one that falls silent halves per typical interval —
standing outlives its evidence by exactly one interval, never accumulating past it (R4). Prestige's 3%
would give a half-life of 22.8 ticks; the beat records g* beside that figure (§cross-grain). Fewer than
30 qualifying atoms (a median over fewer is not a distribution): d = 0.97, prestige's own rate, recorded
as BORROWED until the population supplies its own.

## RANK, EVICTION, RE-ENTRY
- **RANK:** `_candidate_ids` orders by S descending (ties keep today's lexical order). The search visits
  stronger atoms first; under the budget this decides which plans are found at all.
- **EVICTION threshold τ, from the population, not a number:** over the atoms valid at this (game, level),
  τ = Q1 − 1.5·IQR of S (Tukey's lower fence), recomputed at each planner engagement. An atom is EVICTED
  iff **S(a) < τ AND M_d(a) > 0** (a decayed misprediction still in its books). The fence IS the
  Dislodging-vs-Assumption discriminator: when the world remaps and every atom goes wrong
  (BROKEN·rebinding), the population's S drops together, the fence moves with it, nothing is evicted —
  that residual belongs to the rebinding discriminator, not to eviction. Only an atom wrong while its
  peers hold falls below the fence. The M_d > 0 clause: silence is not an outcome; decay RANKS an
  untouched atom down, it never evicts it.
- **Eviction = a superseding append** on the atoms stream, same id, envelope `evicted: true, S, tau, ep`
  (the archive law; `Gamma.get` last-wins). `_candidate_ids` drops ids whose last record carries
  `evicted: true`. NOTHING is deleted; the mint's NOVELTY guard still reads the whole stream, so an
  evicted atom's key stays known — no duplicate is ever re-minted.
- **RE-ENTRY:** re-observation fires a rederivation verdict (e2) regardless of eviction; when S ≥ τ the
  atom is appended back `evicted: false`. A re-entry reopens W2b's GATE B (the change mark gains a third
  component, re-entries; an eviction shrinks the set and need not). Both narrated at the PLAN point with
  fixed tokens `evicted` / `re-entered` and the atom id.

## CROSS-GRAIN CLAIM #6 — what this tests
Claim: decay written for social standing applies to Γ itself — "one mechanism, two grains." The beat
records, per component, adjustment-needed y/n: **tick** (generation → episode): y, stated above ·
**rate** (3% → d from g*): y/n, read from the first beat · **combine** (`max(raw, decayed)` → additive
decayed sums): y — an atom earns discrete events, not a per-tick score · **negative side** (prestige has
none → M): y, supplied by pariah decay's shape · **threshold** (prestige has none → τ): y.
Verdict rule, pre-named: the claim HOLDS at the SHAPE grain (geometric decay per re-earn unit; re-earning
restores; no score outlives its evidence) — the shape above is unchanged. It FAILS at the PARAMETER
grain, since three components already need adjustment. Recorded as "shape shared, parameters re-derived
per grain", never rescued into "one mechanism".

## FALSIFIERS (tests/gate/test_standing.py, house style)
- **F1 · DEMOTION:** a constructed atom that mispredicts on successive driven steps (plan-wrong routed each
  time) ranks below every held atom after the first, and leaves `_candidate_ids` once S < τ. Rank and
  exclusion both asserted; the planner's next search never applies it.
- **F2 · RECOVERY:** the same atom, re-observed (rederivation verdicts) until S ≥ τ, re-enters; the append
  carries `evicted: false`; GATE B reopens on that cycle.
- **F3 · SILENCE NEVER EVICTS:** an atom with one mint and no further event sinks in rank over 3 half-lives
  and is never evicted (M_d = 0) — the window is unbounded by construction; asserted at 3 and at 10.
- **F4 · THE STREAM NEVER LOSES A RECORD:** the atoms-stream record count is monotone across eviction and
  re-entry; `Gamma.get` of an evicted id still returns the atom.
- **F5 · THE SET REFLECTS EXCLUSION:** `plan_to_identity` on a frame where ONLY the evicted atom could anchor
  returns ANCHOR_MISS, not a plan — exclusion is real, not cosmetic.
- **F6 · REPLAY:** two fresh processes over the same books compute identical S for every atom.
- **F7 · ONE EVENT, ONE COUNT:** a stage-4 plan-wrong (ctx_conflict + ledger) raises M by exactly 1.
- **R4:** a constructed population where EVERY atom mispredicts once evicts none (the Assumption case); the
  same population with one atom mispredicting five times evicts exactly that one.

## UNDO
Remove the ordering and the `evicted` filter in `_candidate_ids`, the eviction/re-entry writer, and the
GATE B component. The `evicted`/`S`/`tau` envelope fields, the `steps`/`ep` on PLAN records, the HELD
records and the `via` marker remain readable history; the plan-wrong ledger returns to a ledger. Nothing
stored is destroyed.

## SEAT 3 RULING (2026-08-21, with Seat 4's riders): "silence never evicts" TAKEN
An atom nobody invoked has not failed; it has had no opportunity — the second root inverted.
RIDER: decay must BITE — sinking in rank must have a real consequence (retrieval priority
lost, tried later, must re-earn by being useful when reached); a falsifier asserts a decayed
atom is reached LATER than an undecayed twin, not merely scored lower. RECORDED AS THE
CROSS-GRAIN COUNTER'S FIRST "YES": the network rule needed modification at the atom grain
(silence is evidence among agents, not among atoms) — the finding the counter exists to
catch, logged as such, not as a design choice.
