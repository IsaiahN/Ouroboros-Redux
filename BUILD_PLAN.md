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
- Brick 6 **two streams + pose + α** (§9.2/§3/I2a) — 7 tests. FMap → arrows_impossibility (no perfect aggregation → α must be LEARNED). alpha = learnable weight on private residual instinct vs social grammar; decaying LR (primacy → path-dependent). **The map's own I2a falsifier PASSES**: identical architecture + divergent encounter ORDER ⇒ divergent α (pose mechanism holds), with a same-order determinism control.
- Brick 7 **loop closure** (§9.6) — 9 tests. FMap → kauffman_nk_landscapes (tight coupling ⇒ untunable rugged landscape → the six modules stay LOOSELY coupled through clean interfaces, each swappable). One small COMPLETE loop wires all six bricks: PERCEIVE (segment+track the controllable) → THINK (generic transforms filtered by the falsified ledger) → MAP (price each by the residual it leaves) → ACT (commit the most-believed, pose-blended) → FEEDBACK (residual bus banks surprise, ledger records express-before-judge, pose.learn moves α, belief updates). **The loop LEARNS, measured**: on a toy world whose action→effect map is the WORLD'S SECRET (never passed to the agent), the agent discovers which action causes which transform purely from prediction error — argmax belief converges to the true mapping, committed residual falls, α moves, PE-integral grows monotone, refuted transforms aren't re-committed, no downsampling, two actions discriminated, and the secret is structurally never encoded (built with generic unit moves + empty belief).
- Brick 8 **hard-bound enforcers at import** (§VIII / the Constitution) — 11 tests. FMap → lambda_calculus (d=0.171): enforce by CONSTRUCTION, not by check — the forbidden op must be UNEXPRESSIBLE against the objects; its failure mode is variable capture (a mutable guard-flag silently rebound), guarded by exposing NO disable/bypass parameter anywhere (a free variable the caller could bind to escape) and putting the check on the MANDATORY path. `bounds.py`: `ResetGate` (RESET banned in active play; a credit is earned ONLY by a completed level — the exact Redux force-RESET bug, now unbypassable), `ResolutionBound` (once the canonical full-res shape is admitted, no smaller frame enters — no downsampling ever). Both take no arguments that relax them. The module runs a **constitutional self-check at import and raises ImportError if either bound fails** — you cannot even load a broken constitution. Wired into `AgentLoop` on the mandatory paths: `perceive()` admits every frame through the bound; `reset()` routes through the gate (raises `ResetForbidden` unless earned) and, when permitted, clears only the board — NEVER the learned lineage (belief/pose/ledger) and NEVER the brake's PE-integral (tested: an earned reset does not zero the record of surprise).
- Brick 9 **live-run wiring + first run through the gate** (§9.6 vs the real world) — 6 smoke tests (offline FakeSession, no network). `arc3_env.Arc3Session` (thin API session: open→step→close, native full-res frames, key env-only, holds NO game knowledge) + `live_run.run_live` (pure over the session interface: actions = the game's available non-click discrete actions as generic labels; earned-only reset via earn_progress + never reset in play; no-downsample on perceive; returns `levels_completed` + what it LEARNED). FMap not re-queried — this brick is integration of built parts, grounded in §9.6 directly.
  - **FIRST LIVE RUN (ls20, scorecard 002fc26f-52f7-41a4-9a68-620878a9c512):** `levels_completed = 0` over 262 real actions in 90s; outcome=action_cap; pe_integral 312; **only A1 ever exercised, A1→STAY belief 1.0**, α stayed 0.5, 4 refuted. RULE 0.7: the first run TEACHES, and it taught two concrete mechanism gaps → (a) **exploration collapse** — `choose()` greedily commits the single best (action,transform) across ALL actions, so once one converges the other actions are never tried (this is the documented ls20 explore-collapse pathology); (b) **STAY dominating** means unit-translation of the *smallest object* is the wrong controllable model for ls20 — either the smallest-object heuristic isn't grabbing the real controllable, or ls20's dynamics aren't single-object unit shifts. The loop correctly preferred the honest null (STAY) over a bad model, then couldn't escape it. NO answer encoded — this is a capability gap, not a solution.
- **Suite: 75/75.** Next: brick 10 — **exploration + controllable identification** (the two gaps the live run exposed). FMap-ground an exploration drive (uninformative belief must pull toward UNTRIED actions, not collapse to the first convergent one — the marketplace/pose should price novelty) and a self-locus / co-movement controllable-ID (which object actually co-moves with the agent's actions), then re-run ls20 through the gate. Metric stays `levels_completed` only.
