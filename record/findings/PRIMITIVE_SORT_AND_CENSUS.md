# THE PRIMITIVE SORT + THE CENSUS + THE WANT SUPPLY (2026-08-21, agent read, proctor-verified structure)

## Q1 · THE SORT: 315 unique primitives — PRIOR 85 · MECHANIC 78 · CAPABILITY 152

Rule applied: MECHANIC = interpreter-grade algebra/bookkeeping (handing it is legitimate —
apply_effect's class). PRIOR = output is a gap/expectation/drive (question-producers).
CAPABILITY = output is a named world-conclusion (answer-only; must be earned).

- **MECHANIC (78)**: raw frame access, math/comparison/data/iteration/aggregation algebra,
  interpreter bookkeeping (action history, rand, hash), colour-substitution/pattern-
  replication transforms, click hit-testing, chain_primitives (the composition operator
  itself), pure grid measures (area, angle, connected components), relation-ledger queries.
- **PRIOR (85)**: detect_change/motion/contingency + surprise/information-gain (the
  question factory); segmentation & similarity registration; raw contact/adjacency events;
  the violable biases (solidity, continuity, gravity, persistence, contact-causality —
  their JOB is to be violated); social attention biases; drive substrate (novelty, boredom,
  exploration coverage); metacognitive residuals (detect_stuck, confidence); numerosity
  substrate; appearance/disappearance events; raw temporal deltas; regularity registration
  (symmetry/texture/alignment detectors); remote contingency.
- **CAPABILITY (152)**: affordances (is_movable/is_container/is_tool...); causal-functional
  attributions (detect_blocking/pushing/gating/causation...); containment-as-concept
  (detect_hole/enclosure/nesting...); physical-process naming (support, momentum, flow
  suite incl. predict_flow_path); agency readings (chasing, fleeing); structure/hierarchy
  conclusions (part-whole, path-between, fitting); occlusion world-models;
  track_object_identity; ARC semantics (template/rule/role/analogy — the crown jewels);
  goal & resource semantics; UI parsing; packaged policies.

### Boundary cases FOR SEAT 3's RULING (reasoning, then placement)
1. **Subitizing cluster** — placed PRIOR; but `count_objects` is implemented EXACT (not
   approximate despite its docstring), and an exact count fed to a rule is an answer.
   Suggested split: detect_one_vs_many/compare_quantities PRIOR; count_objects MECHANIC.
2. **detect_motion** — PRIOR by output (a residual); but its implementation matches objects
   by colour across frames — it quietly presupposes identity persistence (a CAPABILITY).
   Placement stands; the implementation is dirtier than the concept.
3. **persistence_bias vs track_object_identity** — the permanence pair: the violable
   expectation (returns a surprise signal) is PRIOR; the identity-maintenance service is
   CAPABILITY. The split is what saves the prior.
4. **detect_contingency vs detect_causation** — same math, different subject: "did MY
   action do this" is birth-grade agency substrate (PRIOR); "A caused B in the world" is
   earned (CAPABILITY).
5. **euler_characteristic / genus** — placed MECHANIC (computable invariants), but genus IS
   hole-count and detect_hole is CAPABILITY. The inconsistency is real and flagged, not
   hidden: if hole-hood is uniformly earned, both move.
6. **Symmetry/texture cluster (17)** — PRIOR as regularity-registration (the broken-
   symmetry cell is the puzzle); the counter is that in ARC "it is symmetric" is often the
   answer. Answer-emitters (predict_symmetric_position, scale_invariance_check,
   detect_facing_direction) moved to CAPABILITY.
7. **teaching_detection** — shakiest social PRIOR ("this hint is intentional" is mind-
   reading); strict line moves it to CAPABILITY.
8. **The attention/action line**: directing attention (select_unexplored_target) = PRIOR;
   emitting the action (get_strategic_exploration_action) = CAPABILITY.

## Q2 · THE CENSUS: why a wired rung never wins — and why zero-wins means NOTHING yet

**Mechanism (a) with an (e) rider: a hard arithmetic ceiling below its own gate, made
permanent by an unwired feedback loop — and the registry has never actually run.**
- Candidate confidence hardcoded 0.25–0.5 × relevance boost (default 0.5) → best 0.30;
  the rung multiplies by 0.8 (`rungs/exploitation.py:3791`) → **max 0.24 against its own
  0.35 threshold** (`:3762`) — **in ladder mode it can NEVER pass, at any priority.**
- Permanent because the RLVR loop (`record_outcome`/`record_game_result`) is **called by
  nothing** (docstring-only); `primitive_action_effectiveness` and
  `primitive_game_relevance`: **0 rows in both DBs.**
- **The (e) rider: five of the six primitives the suggester applies DON'T EXIST in the
  registry** (raise Unknown primitive, `seed_primitives.py:16553-16557`) and the sixth
  (detect_motion) is called with the wrong arity. Every suggestion ever made came from
  crude in-file fallbacks — **the 315-primitive registry has never been exercised at all.**
- **Implication**: zero wins is NOT evidence the wheel would discard these capabilities;
  the wheel never received a valid confident proposal. Whether the catalogue's
  capabilities would help is STILL OPEN — the census cleared the question, not the answer.

## Q3 · THE WANT SUPPLY: LIVE — thin in breadth, not in flow
- **~13,030 goal_hypotheses records and GROWING during the audit** (+23 in 20 min),
  collective streams only, **9 of 25 games** (sp80 2,326 · cn04 1,865 · ar25 1,575 ·
  m0r0 1,483 · lp85 1,458 · r11l 1,382 · sk48 1,250 · ft09 856 · cd82 830).
- Volume is repeated evidence accrual on **~151 distinct hypotheses over 5 predicate
  kinds** (region_contains_colour dominant; ev: 9,997 co / 3,051 miss).
- Reference WANTs: in-memory, per-episode, **gated L1+** (g3) — essentially ar25 today.
  Abduced WANTs fire exactly when the refsnap is absent — complementary by construction.
- **Composer amendment 1 verdict: the producer is alive for the 9 scoreable games; the
  compose loop needs constructed WANTs only for the 16 games with no hypothesis stream.**

## Downstream consequences (proctor)
- Destination-2 curriculum proceeds: the catalogue gets the 152 capabilities as aims; the
  never-exercised finding means their VALUE is untested, and the first agents to earn one
  will be the first evidence either way.
- The suggester itself: after the sort empties the registry into its three destinations,
  the rung's fate is Seat 3's — repair (wire the feedback, fix the six names, rederive the
  ceiling) or retire (the catalogue + gate replace its role). The census gives the repair
  bill precisely.


---

# SEAT 3 RULINGS (2026-08-21) — the sort is settled

1. **count_objects → MECHANIC** (the split taken): the docstring claims subitizing, the
   code is len(); **the implementation decides, not the name.** Approximate numerosity
   stays PRIOR.
2. **detect_motion → PRIOR stands, with a REPAIR NOTE**: the colour-matching
   identity-persistence smuggle is fixed, not inherited.
3. **The permanence pair split → confirmed as THE MODEL for the whole sort**: *a violable
   expectation returning a surprise signal is a prior; the same knowledge as a maintained
   service is a capability. If both were one primitive it would be CAPABILITY.*
4. **euler_characteristic + genus → CAPABILITY**: hole-hood is a world-conclusion; a clean
   invariant does not make it less of one. The rule over the implementation's tidiness.
5. **teaching_detection → CAPABILITY**: "this hint is intentional" concludes about another
   mind; the other three social primitives direct trials and stay PRIOR.
6. All other placements stand.

**FINAL TALLY: PRIOR 83 · MECHANIC 77 · CAPABILITY 155 = 315.**

## THE SUGGESTER: RETIRED into catalogue + gate (Seat 3)
Repair would mean fixing four independent defects to restore an organ whose replacement is
already designed. **Seat 3's condition — did the fallbacks ever produce anything useful? —
is answerable from the census itself**: the fallbacks were the only path that ever ran, AND
the rung has zero labeled wheel wins — so nothing the suggester ever emitted, registry or
fallback, drove a single action (caveat: the 45% unlabeled cohort could in principle hide
occurrences; no labeled evidence exists). The only thing that ever ran also never won.
Retirement loses nothing that was ever used.

## Destinations now execute per the settled sort
- 83 PRIORS → perceptual substrate + PERCEIVE/grammar leaf suppliers (W3 build, with the
  detect_motion repair in its brief).
- 77 MECHANICS → interpreter layer (legitimate to hand; no earn-through).
- 155 CAPABILITIES → the catalogue as curriculum, value honestly unknown until the first
  earns settle.


## THE FALLBACK-USEFULNESS QUESTION (Seat 3's retirement condition) — the honest bound
Both selection modes exist in decision_rung_system (ladder: has_suggestion vs threshold at
:881/:1163/:1263; weighted: vote = confidence x (100-priority)/100 at :944). The answer by
mode:
- **Ladder orderings: the fallbacks produced NOTHING downstream, provably** — 0.24 < 0.35
  means no suggestion ever passed the rung's own gate, so no output reached the wheel.
- **Weighted mode: influence possible in principle, never credited, bounded ≤ ~0.16** —
  the vote joined the blend but a win credits the highest contributor, and the suggester
  was never it. Whether its marginal vote ever FLIPPED a blended choice is unmeasured.
**QUEUED (heartbeat): the bounding read** — which mode each role/strategy actually runs
live, and the suggester's vote share vs typical winner scores in any weighted path. If
weighted never runs live, the answer hardens to "the fallbacks never influenced a single
action, in any mode" and the retirement loses provably nothing.

## THE MODE-USAGE READ (2026-08-21) — the fallback bound, finalised
Live strategy is 'cognitive' or 'ladder', never 'weighted' — BUT inside _decide_cognitive
(decision_rung_system.py:1436-1437) weighted voting runs LIVE as the fallback whenever the
router's selected action is unavailable, and that path (:1210-1226) has NO threshold check:
the suggester's 0.24 confidence scores ≈0.22 > the 0.15 floor and could win. So the bound
does NOT harden to "never in any mode": STRUCTURALLY POSSIBLE in the no-action fallback;
EMPIRICALLY zero labeled wins in 20,952 ACT records (a weighted win is credited to the
highest contributor, which would label it) — the residual uncertainty is the 45% unlabeled
cohort only. Retirement still loses nothing OBSERVED. Recorded as the honest bound.

## TWO CONSEQUENCES (Seat 4, 2026-08-21)
1. **The retirement's basis is corrected: "never arrived" was wrong.** The suggester never
   arrived through the LADDER path; it could have arrived — and won — through the cognitive
   router's no-action FALLBACK. The bound is now the residue, not the conclusion: whether it
   ever actually won there is UNMEASURED, and the fallback's frequency is unknown (rare or
   common decides whether the retirement is clean). **QUEUED READ: how often
   _decide_cognitive falls through to _decide_weighted_non_emergency in live play, and the
   winning-rung distribution on that path.**
2. **D-7 — a WIDER DEFECT than the suggester: the weighted fallback ignores every rung's
   confidence_threshold** (decision_rung_system.py:1210 gates on `if result.action:` only).
   A rung's threshold is honoured on the ladder path and ignored on the fallback — every
   rung with a threshold is unguarded there, not just the retired one. Own line in the
   defect register; fix shape = apply has_suggestion(threshold) on the fallback path, with
   the fallback's own frequency read first so the fix's blast radius is known.

## THE D-7 FREQUENCY READ (2026-08-21) — the fallback is not the defect; the router is
The fallback leaks a label: `rung == "weighted_random"` on an ACT record PROVES the D-7
path fired (lower bound — a fallback vote ≥0.15 takes the real winner's name). Share of
labeled ACTs: **sk48 78.7% · ar25 78.4%** · bp35 32.6% · g50t 4.7% · tn36 0%. **On the two
deepest games the cognitive router produces no usable action on ~4 of 5 steps and falls
through to thresholdless weighted voting.** That is the real finding: D-7's missing check
sits on a path that IS the main path for L1+ play. The suggester never appears as a winner
in any box — the retirement's residue closes to "never won, on any path" (lower-bound
caveat stated). BLAST RADIUS of honouring thresholds on the fallback: 3 rungs silenced
outright (belief_system, state_matching, valence_goals), 6 partial, 27 safe, 30 undecidable
statically — and the NET EFFECT is fewer votes → MORE weighted_random. **So the fix is not
the threshold check alone; it is why the router yields nothing 78% of the time on the games
closest to winning.** Instrument first: `last_decision_metadata['weighted_fallback']=True`
at the branch (:1437), emitted on the ACT record — one field, exact count. For the gate's
coverage census this reclassifies most of sk48/ar25's actions as PROBES by mechanism.

## D-7 → D-8, and the instrument (Seat 4 + Seat 3, 2026-08-21)
- **D-8 registered — the defect under D-7**: the cognitive router's selected rung produces
  no usable action on ~4 of 5 cycles on sk48/ar25 (lower bound 78.7/78.4%). Not that the
  fallback is unguarded, but that it is needed at all. The primary path on the deepest
  games has been unlabelled.
- **THE INSTRUMENT, taken (one line, queued as the first build after the stage-4 commit):**
  `last_decision_metadata['weighted_fallback'] = True` at decision_rung_system.py:1437
  before the call overwrites it, emitted on the ACT narration record. Converts a lower
  bound into a measurement; no behaviour change.
- **PINNED BEFORE THE FIX: honouring thresholds on the fallback will READ AS A REGRESSION.**
  Fewer sub-threshold votes → the fallback finds nothing → more weighted_random. The random
  share rising is the MEASUREMENT of how many actions were decided by votes their own rungs
  declared unreliable — not damage from the fix. Stated now so it cannot be argued later.
- The suggester's residue closes mostly clean: it could have won on a path taken ~78% of
  the time and never appears as a winner in any box.

## D-9 (2026-08-21): the per-generation SystemDiagnostic pass — produced, PRINTED, unread
evolution_runner.py:1494-1506: `SystemDiagnostic.run()` (~23s, window 6-a) runs EVERY
GENERATION in every worker and its result reaches three print() lines only — no table, no
stream, no reader. Against 90s generations (window 5) that is ~25% of generation time
producing a health score nobody consumes; ×25 workers. The genus at the telemetry grain.
Fix shape: env-gated (OURO_DIAGNOSTIC, default off for swarm workers; the supervisor and
keeper set nothing), print path kept for operators who opt in. Builder dispatched.

## D-11 (2026-08-21): arc_agi.rendering imports matplotlib into every headless worker
`-X importtime`: matplotlib 5.14s cumulative per worker boot (+fontTools via dviread), first
imported by `arc_agi.rendering` — the toolkit's visualiser, which no worker calls. ×25
workers ≈ 2 CPU-minutes per fleet restart and ~40MB × 25 ≈ 1GB of RSS baseline. Same
family as D-9 (a boot term nobody named). Fix shape: import the toolkit's needed
submodules (base/client) rather than the package, or lazy-load rendering; measured by
-X importtime before/after. Serialized behind the D-9 builder (shared files).
scipy: imported by engines/egocentric/perception.py (0.4s) — usage check alongside.
scipy resolved: perception.py imports ndimage as an OPTIONAL dev-box convenience with a
pure-numpy fallback (the venv has it, so it loads; 0.4s). Not a defect; not in D-11's fix.
D-9 CORRECTED by its builder: the diagnostic fires at generation 0 and every 10th
(`current_generation % 10 == 0`), not every generation — "~25% of every 90s generation"
overstated it; a boot lands on gen 0, which is what window 6-a measured. Cost per fire
(~23s) and the print-only consumer stand. Gated behind OURO_DIAGNOSTIC (off by default),
construction-side, byte-identical when on. 22/22.
D-9 DISPOSITION NOTE (Seat 4): produced-and-unread, ~tenth instance — and the first whose
fix is GATE THE PRODUCER rather than wire a consumer, because nothing wants the product.
F5 asserts no-reader by AST identity on attribute nodes, so prose cannot shift it.
D-11 ADJACENT (proctor, memory instrument side-read): a werkzeug LocalProxy is resident in a
game worker's heap (it raised RuntimeError under the root-walk's attribute probe). Flask or
its proxy is imported on the worker path. Same genus as D-11 (matplotlib via rendering):
import-time weight with no worker-side consumer. Not yet located; census on import graph due.
