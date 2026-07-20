# BUILD PLAN — The New Horse (autonomous build)

## Charter
Isaiah handed full control on 2026-07-20. The mission: **build the agent `docs/THE_MAP.md`
describes — one that solves ARC-AGI-3 by its OWN reasoning.** The corpus documents are the
doctrine (they substitute for Isaiah's judgment); THE_MAP is the spec; the FMap grounds each
design decision. Final submission deadline: **2 November 2026**.

## Operating discipline — non-negotiable (LAW 0 + THE MAP §VIII)
- **Never encode the answer.** The agent reasons its own way to it; I build the capability, never the solution.
- **Never ship half a mechanism.** A record without a consumer, an enumerate without a use, is worth nothing.
- **Nothing happens silently** — no isolated code, no silent code, no code without reason.
- **RESET earned-only; never downsample the grid** — enforced at import (hard bounds, not dials).
- **The brake:** a claim's strength never exceeds its gate. Every brick is unit-tested; the live game is the real gate.
- **RULE 0.7 — don't spiral, don't force a solve.** When stuck: abstract up, re-read the docs, query the FMap. A single run is never a verdict.
- **Rule 0 of Evidence** — render ground truth (frames AND code/AST), never reason from the narration.
- **Monolith-then-carve** — build a small COMPLETE loop, then refine. Do not gold-plate isolated parts or gate the design.
- **FMap-ground every design decision** — reason the problem's F* coords, rank the 46 frameworks, research the top one's blueprint + FAILURE MODES, build the guards in. (`/tmp/nb/fmap_query.py`.)
- **Don't build a decorated copy** — the map's one warning. Coherence is not correctness; only measurement is.

## Build sequence (adaptive — reorder as the build teaches)
Each brick: FMap-grounded, unit-tested, committed, nothing silent.
1. **[DONE]** Falsified ledger (§9.4) — the reject-memory Redux can't hold. Immune-system failure-mode audited. 10/10 tests.
2. **Full-resolution perception** (§9.2) — object permanence (identity by overlap, survives recolour/reshape), segmentation-as-revisable-belief, tracking through occlusion, `check_no_downsampling()` at import. Foundational: everything reads from it.
3. **Typed grammar** (§9.1) — primes (Kant/NSM), molecules, predicates × quantifiers. Adapt Redux's `objective_grammar.py` (already sound), cleaned and TYPED (typing beats size).
4. **The residual** (§8) — prediction error as the aim, the sense organ, and the currency. Full-resolution, un-suppressible (the brake invariant: no drive may suppress the time-integral of prediction error).
5. **The marketplace** (§9.3) — propose → vote → resolve, priced by prediction error. *FMap says: predictive_processing (hypotheses ranked by prediction error) + goodharts_law GUARD (the price must not become a gameable target).*
6. **Two streams + pose + α** (§9.2, I2a) — Stream A private residual history, Stream B the grammar, α the learnable weighting. Falsifier: divergent encounter order ⇒ divergent α.
7. **Loop closure** (§9.6) — PERCEIVE → THINK → MAP → ACT with both feedback arrows.
8. **Hard-bound enforcers at import** — reset-earned-only, no-downsampling.
9. **Run vs one clean ARC-3 game through the live gate.** Metric: `levels_completed` only (no fractional goose chase).

## Foundation status
The map's central bet — aim variation with a spec — has a **measured floor**: the reverse-map
falsifier on the real 46-framework F* kernel gave edge **1.29×**, p<0.001 vs a shuffled null.
E.1 does not fail. We build on ground that held its own test. (Fuller problem→primitive D.1
accrues for free as the FMap dogfooding loop runs on real build problems.)

## Log
- **2026-07-20** — branch created (orphan). Full control handed over.
- Brick 1 **falsified ledger** (§9.4) — 10 tests. FMap → adaptive_immune_system #1 (map's own choice); failure-mode audited.
- Brick 2 **full-res perception** (§9.2) — 9 tests. FMap → Simon near-decomposability (segmentation principle). Object permanence.
- Brick 3 **typed grammar** (§9.1) — 7 tests. FMap → small_world_network. "Typing beats size" measured (64×–1024× < flat bag).
- Brick 4 **the residual** (§8/§10/§11) — 9 tests. FMap dull (grounded in the map directly). Sense organ + un-suppressible PE-integral (brake invariant) + MDL mint test with the before-state tautology guard.
- Brick 5 **the marketplace** (§9.3/§7) — 7 tests. FMap → predictive_processing + goodharts_law GUARD. propose→vote→resolve; currency = the residual (informative accuracy); a trivial "nothing changes" hypothesis earns ZERO salience on a change frame (can't game the price); hallucinated change penalised.
- **Suite: 42/42.** Next: brick 6 two-streams + pose + α (§9.2 — Stream A private residual history vs Stream B grammar, learnable α; falsifier: divergent encounter order ⇒ divergent α).
