# BUILDER BRIEF — STANDING_HALF_LIFE AT THE ATOM GRAIN (dispatch AFTER W2c lands; shares planner.py / scheduler.py)

Reads first, in order: record/prereg/PREREG_STANDING_HALF_LIFE_ATOMS.md (ruled; the Seat 3
ruling + riders at its foot are binding: "silence never evicts" TAKEN; decay must BITE — a
falsifier asserts a decayed atom is REACHED LATER than an undecayed twin, not merely scored
lower), record/canon/THE_LADDER.md, engines/egocentric/planner.py (`_candidate_ids`), engines/egocentric/
scheduler.py (`plan_wrong`, `on_abort`, GATE B's change mark), engines/egocentric/mint.py
(`_refresh_sig_index` — the incremental-index pattern; the ep stamp on verdicts; the conflict
clause's superseding append), engines/egocentric/effects.py (Gamma: add/get last-wins),
engines/social/prestige_engine.py:214-235 (the decay exemplar the prereg derives FROM, not
borrows), tests/gate/test_fabric_seq_cache.py (counting, never wall-clock).

Constraints (standing): HOLD up — no commit, nothing under .runs/, do not remove HOLD. Forbidden
reads: docs/GAME_TRUTH, ouroboros_cpu/objective_grammar.py, the train-set-answers directory.
Never print .env. Never decode game frames; constructed fixtures only. No game id, colour or
object identity in code, tests or comments. Other builders' uncommitted work is in the tree —
leave it; on cognitive_loop.py use Edit for surgical hunks only, re-read before each edit.

Build exactly the prereg: one module engines/egocentric/standing.py — events E(a)/M(a) as
defined (e1 mint verdict, e2 rederivation, e3 HELD step recorded per step atom + composite
settle; m1 plan-wrong routed per step atom, persisted by stamping `steps`+`ep` on the PLAN
abort narration record; m2 ctx_conflict appends from the observation-time clause; the
`via: plan-wrong` marker makes the stage-4 path count ONCE); S(a,t) with the SAME decay on
both sides; d = 0.5^(1/g*) from the population's own median re-earn gap, d = 0.97 BORROWED
and stated below 30 qualifying atoms; computed incrementally in memory, re-derived from the
streams on restart (two processes over the same books compute identical S — F6). RANK:
`_candidate_ids` by S descending, ties lexical. EVICTION: τ = Q1 − 1.5·IQR of S over atoms
valid at (game, level), recomputed per engagement; evict iff S < τ AND M_d > 0 — a
superseding append `evicted: true, S, tau, ep`; `_candidate_ids` drops ids whose LAST record
carries evicted: true; the NOVELTY guard still sees the key. RE-ENTRY on rederivation when
S ≥ τ (`evicted: false`), reopening GATE B (third change-mark component). Narrated at the PLAN
point with fixed tokens `evicted` / `re-entered` + id.

THE RIDER AS A TEST: decay BITES — construct two atoms identical but for standing; under the
planner's node budget the decayed one is reached LATER (by expanded-count or visit index),
asserted as an ordering of reach, not a comparison of S.

Gates (tests/gate/test_standing.py): F1 demotion (rank + exclusion + the next search never
applies it), F2 recovery (re-entry append, GATE B reopens), F3 silence never evicts (3 and 10
half-lives), F4 the stream never loses a record, F5 the set reflects exclusion (ANCHOR_MISS,
not a plan), F6 replay identity, F7 one event one count, R4 (every atom wrong once → none
evicted; one atom wrong five times → exactly that one), the rider test. Plus test_plan_wire,
test_composer_stage3/45/notes, test_planner_retention (W2c's — a superseded/evicted atom's
content key misses by construction; assert it), test_consumers (ALLOWLIST byte-unchanged),
test_system_determinism, test_wiring_registry — all green.

Cross-grain counter: record per component (tick / rate / combine / negative side / threshold)
adjustment-needed y/n in the registry row's note, exactly as the prereg's §"CROSS-GRAIN CLAIM
#6" pre-names the verdict rule. KNOBS: d's fallback 0.97 is BORROWED (say so in the row); τ's
1.5·IQR is PINNED by the prereg; the 30-atom floor PINNED.

Discipline: module-bottom helpers; registry rows refreshed by grepping the symbol, never by
offset, drift stated; ruff zero new; one full `pytest tests -q` at the end, verbatim tail,
every red reported yours or not; non-pinned decisions numbered; terse structured report.

## THE LAWS THIS BUILD SATISFIES (figures/*.svg; a builder that cannot state them was not briefed)
- FIGURE 1 — the ground is the only metric; predicates minted and credibility accrued are
  frame-internal and do not count. Standing S RANKS RETRIEVAL; it is never a score, never a
  metric, never reported as progress. Your tests must include one asserting S feeds nothing
  that prices or reports (F5-style identity of sinks).
- FIGURE 2 — the anchor does not update. An atom's EARN events are ground-settled facts
  (held steps, settles, rederivations against the world), never another atom's or agent's
  opinion; M events are mispredictions against the LIVE frame. No mutual update between
  atoms: standing is each atom ranged against the ground separately.
- FIGURE 5 — "nothing new here: the machinery worked; the answer was already known" is a
  rederivation, and it STRENGTHENS (e2). Decay that makes a rederived atom sink would
  violate this; F2 recovery is the law's test.
- FIGURE 10 — provenance: every eviction/re-entry append carries S, tau, ep and the event
  that caused it, so a later reader can locate the error rather than feel it.
State in your report which of these your tests assert and which are assumed.
