# THE COGNITIVE STANDARD — the periodic table of human reasoning, as a diagnostic checklist for the agent `[Isaiah, 20 Jul 2026]`

**What this is.** A master catalogue of the formal frameworks, biases, developmental stages, and epistemic
heuristics a century of cognitive science has mapped — organised by layers of abstraction. **Its purpose is to
diagnose ANY reasoning failure in the agent as a CLASS, not an obstacle.** When the agent solves or stalls, its
trace is run through this stack; the first check it fails names the missing capability, built once and reused on
every game. This is Chollet's definition of intelligence made operational — *skill-acquisition efficiency over a
scope of tasks* — a class answered from few instances.

## THE GATEKEEPER (the operational core)

Every time the agent is about to emit a CLASSIFICATION ("this is a booster / wall / cycler / the goal"), that
output must pass the stack below. If it fails any check, it is forcibly downgraded to **"insufficient evidence —
hypothesis pending — further causal testing required,"** carrying a *distribution* over live hypotheses, not a
point label. Refusing to harden a label the evidence hasn't earned is what turns this catalogue into a
mechanism. Four checks are **preconditions/stop-conditions** the gate runs, not just table rows:

1. **Effectiveness — gate the DATUM.** Before an outcome counts as evidence, verify the intervention actually
   took effect (the do-operator registered). A move blocked by a wall, a contact that didn't satisfy the
   activation condition, a no-op action → a NON-TRIAL, not a null result. "I failed to do X" must never be coded
   as "X is inert." (Extends the agent's `REACH-FAIL: UNTESTED, not rejected` from reachability down to contact.)
2. **Syntax vs. Semantics — gate the LABEL (hard requirement).** A causal label passes ONLY if it is grounded in
   an *executable mechanism* in the world-model: a predictor that, run forward from the state, reproduces the
   observation (+N budget on contact). If the model cannot simulate it, the claim is linguistic, not causal —
   stays "hypothesis pending." This is the anti-Chinese-Room guard that makes "whitebox reasoning that can say
   how" true rather than narrated. (Lake: a model is a *process that produces* the observation, not a lookup.)
3. **Unidentifiability — gate the LOOP (stop-condition).** Distinct from underdetermination ("many theories
   fit"): can ANY test I can run separate the live hypotheses, or do they predict identical observations? If not,
   STOP testing — declare unidentifiable and act under irreducible uncertainty rather than spend a life proving
   nothing. This is the graceful terminus of the free→deliberate→**stop** escalation, and the principled bound on
   re-probing. (Formally Pearl's identifiability; the agent already has the seed at the model level:
   `NOT identifiable -> I will not plan over this`.)
4. **Mediation — decompose the EFFECT.** Direct vs indirect path: is the true proximal cause *on the path*
   (step → compress plate → sensor → budget)? Don't collapse the chain. Detection is nearly free (see Layer 2);
   chain-tracing with nested counterfactuals is staged.

The **In the agent** column is a conservative gap-analysis of the live composer: **HAS** (a named step fires),
**PARTIAL** (present but narrow), **MISSING** (no representation yet). MISSING items are the roadmap.

---

### LAYER 0 — Hardware constraints (System-1 heuristics / biases)

| Name | The error | In the agent |
| :-- | :-- | :-- |
| **Availability** | overweight recent/dramatic/easily-recalled data | MISSING |
| **Representativeness** | judge by resemblance, ignore base rates | PARTIAL — `canon_shape` grouping; no base-rate correction |
| **Anchoring** | over-fixate on the first datum | MISSING — a one-shot first label IS an anchor (the booster bug) |
| **Fluency** | the simpler story feels truer ("I stepped, budget rose") | MISSING — the exact leap the gatekeeper blocks |
| **Gaze** | assume what I look at is what I interact with | MISSING — attribute effect to the tested cell, not the salient one |
| **Syntax vs. Semantics** *(core-prior; gatekeeper #2)* | a claim that is linguistic probability, not an executable mechanism | PARTIAL/BUILDING — object-laws ARE executable; the trigger label is not yet tied to a runnable predictor |

### LAYER 1 — Statistical & probabilistic reasoning

| Name | The error | In the agent |
| :-- | :-- | :-- |
| **Bayesian inference** | fail to update; confuse P(H\|E) with P(E\|H) | PARTIAL — market/confidence; not explicit Bayes |
| **Base-rate neglect** | one rise ⇒ "steps cause rises" | PARTIAL — `_state_context` de-dups same-context; no true base rate |
| **Regression to the mean** | credit a rebound from a dip | MISSING |
| **Gambler's fallacy / Conjunction** | self-correcting independents; A∧B > A | MISSING |
| **Selection / survivorship** | only sample the promising panels | MISSING — no control-sampling of the ignored |

### LAYER 2 — Causal reasoning (Pearl's Ladder) — *the exact ladder the agent must climb*

| Rung / component | Definition | In the agent |
| :-- | :-- | :-- |
| **1 — Association (seeing)** | "X changed when I did Y" | HAS (where it currently STOPS and labels) |
| **2 — Intervention (doing)** | *do Y again* under control — does it replicate? | BUILDING — probe repeats; routed through the earned-confidence ladder |
| **2b — Effectiveness** *(gatekeeper #1)* | verify the do actually took effect before scoring | PARTIAL — `REACH-FAIL` at reachability; missing at contact |
| **3 — Counterfactual (imagining)** | would X change *without* my Y? | BUILDING — the passive-observation arm |
| **Confounding (back-door)** | hidden common cause of act & effect | PARTIAL — the booster/death/level confound guard |
| **d-separation / colliders** | a third var (time) makes X,Y correlate though unrelated | MISSING |
| **Mediation** *(gatekeeper #4)* | true cause is on the path (step→plate→sensor→budget) | PARTIAL — `_classify_change` detects self vs remote (direct/indirect); chain-tracing MISSING |

### LAYER 3 — Epistemic logic & belief management

| Name | The error | In the agent |
| :-- | :-- | :-- |
| **Doxastic logic** (Belief/Disbelief/**Suspension**) | only yes/no; no "suspend judgment" | BUILDING — `unknown`/`conjectured` = suspension; the gate's default |
| **Defeasible reasoning** | a label as absolute, not overturnable | BUILDING — status re-anchors / splits |
| **Gettier** | justified-true-belief true *by accident* | PARTIAL — rung 3 guards being right-for-wrong-reason |
| **Moore's paradox** | act as if P while holding no belief P | MISSING — couple action-confidence to belief-confidence (act at `supported`) |
| **Problem of induction** | "worked 3× ⇒ works 4th," no mechanism | PARTIAL — seeks the effect-kind, not just the streak |

### LAYER 4 — Scientific method & hypothesis testing

| Name | The error | In the agent |
| :-- | :-- | :-- |
| **Falsificationism** | claim without a disproof condition | HAS — refutation ledger / `FALSIFY` / anomaly-split |
| **Null-hypothesis** | assume effect before evidence | PARTIAL — `inert` should be the earned null, not one-shot |
| **A/B / control** | only step ON; never stand *beside* as control | BUILDING — passive/deliberate-observe = the control |
| **Operationalization** | define "booster" by effect, not mechanism | PARTIAL (tightened by gatekeeper #2) |
| **Replication awareness** | label after ONE trial | BUILDING — conjectured→supported→confirmed |

### LAYER 5 — Social cognition & theory of mind (designers / adversaries behind the game)

| Name | The error | In the agent |
| :-- | :-- | :-- |
| **Intentional stance** | never ask *why the designer put this here* | PARTIAL — the `SOLVABILITY AXIOM` is a thin designer-intent prior |
| **Strategic deception / adversarial** | take the display at face value; ignore honeypots/decoys | MISSING — a real branch (the `===` decoy) |
| **Common knowledge** | ignore that the game anticipates the agent's habits | MISSING |
| **Trust / source reliability** | treat a faulty sensor as infallible | PARTIAL — distrusts a noisy readout, not as Bayesian reliability |

### LAYER 6 — Metacognition & executive function (the debugger)

| Name | The error | In the agent |
| :-- | :-- | :-- |
| **Epistemic humility** | 100% certain on correlational evidence | BUILDING — confidence calibrated to n |
| **Metacognitive monitoring** | no "confusion" signal | PARTIAL — `SELF-ASSESS`, model "NOT identifiable" |
| **Unidentifiability** *(gatekeeper #3)* | keep testing a question no test can answer | PARTIAL — model-level only; lift to classification + make it the stop-condition |
| **Overfitting vs generalization** | hyper-specific rule for this panel | HAS (partial) — "the CLASS transfers, the ADDRESS does not" |
| **Frame problem / Salience** | which variables to ignore; everything equal ⇒ paralysis | HAS (partial) — self/HUD frame narrowing; `_candidates` salience |
| **Reflective equilibrium** | hold "corr≠cause" while acting as if it does | MISSING — the meta-consistency the gate enforces |

### LAYER 7 — Philosophical traps (black swans)

| Name | The error | In the agent |
| :-- | :-- | :-- |
| **Underdetermination** | infinite theories fit; pick one, ignore the rest | MISSING — carry a *distribution*, not a point label |
| **Goodhart's / Campbell's Law** | the measure becomes the target | HAS (as doctrine) — **LAW 0 is the anti-Goodhart**; extend into objective handling (`no_posthoc`) |
| **Map–territory** | confuse the label with the object | BUILDING — the booster bug IS this; fix keeps label ≠ earned-verdict |
| **Munchausen trilemma / Hume** | justification bottoms out; this sim ⇒ all sims | MISSING / PARTIAL (transfer claimed as mechanism) |

### LAYER 8 — Developmental & embodied cognition (core-knowledge priors — Chollet/Spelke)

| Name | In the agent |
| :-- | :-- |
| **Affordances** (Gibson) | HAS (partial) — `_affordances`: "what this descriptor DID" |
| **Object permanence** | HAS (partial) — persistence / tracker identity |
| **Naïve physics / mechanics** | PARTIAL — object-laws / MOTION induced; contact-causality assumed |
| **Naïve biology / essentialism** | PARTIAL — a stable per-type "effect essence" |
| **Sensorimotor contingencies** | HAS (partial) — two-frame proprioceptive reconciliation, self-model |
| **Interoception** | PARTIAL — budget as a felt depleting resource; caution when low |

---

## THE CROSS-LAYER AUDIT (run on every classification, and every solve/stall)

Walk the stack; the FIRST failed check names the class:
1. **Datum valid?** (Effectiveness) — did the intervention register, or is this a non-trial?
2. **Anchoring/fluency/gaze?** (Layer 0) — reset the anchor; attribute to the tested cell.
3. **Rung mismatch?** (Layer 2) — at association but acting like intervention? demand replication + a no-contact control.
4. **Judgment suspended?** (Layer 3) — hard label vs `hypothesis pending`? force suspension.
5. **Label grounded?** (Syntax/Semantics) — backed by an executable mechanism, or just words?
6. **Overfit / underdetermined?** (Layer 6/7) — generalise; output a *distribution*, not a point estimate.
7. **Resolvable at all?** (Unidentifiability) — can any test decide this? if not, stop and act under uncertainty.
8. **Proxy becoming target?** (Goodhart / LAW 0) — earn it, don't optimise the label.

Failing any check forcibly rewrites the output to **"insufficient evidence — hypothesis pending — further
causal testing required."** Passing the stack is the ONLY way an object earns a hardened effect label.

**Proctor usage.** On every solve OR stall: walk the trace, name the failed check as the class, build the
general capability (gated + A/B), confirm it fires as a NAMED step, regression-check the WHOLE stack (a
Layer-0/8 change ripples up), and record it here + in PROCTOR_STATE. A level is not "won" until its trace shows
no missing rung/prior/operation — a win with a hidden gap just relocates the failure to the next game.

---

## Sources
- Chollet, *On the Measure of Intelligence* (2019): https://arxiv.org/abs/1911.01547
- Pearl, ladder of causation + identifiability / d-separation / confounding / mediation: https://causalai.net/r60.pdf
- Lake, Ullman, Tenenbaum, Gershman, *Building Machines That Learn and Think Like People* (2017): https://arxiv.org/abs/1604.00289
- Spelke & Kinzler, *Core Knowledge*; Piaget (in-corpus as `THE_LADDER`); Popper; Dennett; Gibson; Korzybski; Goodhart/Campbell.
