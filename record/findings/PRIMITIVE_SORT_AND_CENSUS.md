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
