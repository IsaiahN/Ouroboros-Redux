# PREREG — W1: THE NARRATION SPINE + MEMORY AT THREE RANGES (2026-08-20)

**AUTHORITY:** the accepted refactor plan, W1; Seat 3: *"Start W-1, you are clear to proceed."*
**STATUS: PREREG + BUILDER BRIEF. Agent code — a firewalled builder writes it.** This document
is the brief: mechanics only, no game specifics, predicates named not answers.

## THE CORRECTION THAT CHANGES WHAT GETS BUILT (Seat 3, 2026-08-20)
> **Narration is not a log written after a decision. It IS the decision** — the loop's step 1
> is perceive, BET, act, observe: the bet comes before the action and the residual is the gap
> between them. **An action taken without a prediction attached produces no residual — not a
> small one, none. There was nothing to be wrong against.**

So the emitter fires **BEFORE the action**: the bet (per-slot prediction), the bin reasoning,
the candidate, the source tags — written at decision time, with the action taken *from* that
state. The post-action lines (ECHO, outcome) close the loop against the pre-action bet.
An agent that acts and then explains has skipped step 1 and started at step 2; the
explanation afterward is a reconstruction, and it may or may not be true.

**And this sharpens the falsifier rather than replacing it:** if narration were written after
the fact, the two arms would be indistinguishable **by construction** — you cannot consume
what did not exist when the decision was made. **The narrate-and-consume arm is only a real
arm if narration precedes the action.** F1 therefore gains a precedence check: every ACT
record must reference the id of a BET record with an earlier sequence number in the same step.

## WHAT IT IS
One build, two faces (Seat 3: *"one change, not two"*):
1. **The agent narrates its own loop, in the loop's vocabulary** — bet-side lines BEFORE the
   action, outcome-side lines after, at six points per cycle:
   - **PERCEIVE**: prediction vs outcome, per slot — never aggregated.
   - **ROUTE**: which of the four bins, **and why not the neighbour bin** (the discriminating
     fact, e.g. *residual > eps AND from_known_atom → BROKEN·mechanism, not NOVEL*).
   - **MINT**: the candidate offered; if none, **which guard was the zero** (route-specific
     per the resolved triple); did the bargain pay, with both sides of the inequality.
   - **ECHO**: what settled, or *candidate* stated as such.
   - **PLAN**: drove / shadowed / no-steps, with the g-gate that stopped it.
   - **ACT**: the chosen action and the rung that won the wheel.
2. **Every narration line names its memory range**: `[EP]` this episode · `[OWN]` this agent's
   history on this game · `[COL]` the collective (with provenance: inherited-library /
   role-pool / cross-role — the contact classes, since the single A/B dial is excluded).

**Grammar:** the loop's terms + NSM primes for the connective tissue. Fixed tokens, one line
per event, machine-parseable (`narration.jsonl`, personal stream, one record per step).

## WHY (the claim being tested)
The week's costliest work was reconstructing *why* from the outside. **Narration is retention**
— the `binding_stale` finding generalised: the system repeatedly knows things at the moment it
acts and has forgotten them by the time anyone asks. If the agent states bin, guard, and
source at act-time, diagnosis becomes a read.

## THE SHARED FALSIFIER — held, and it gates the rest of the plan
> **If the agent narrates its reasoning and names its sources and nothing about its behaviour
> changes, the narration is decoration and the framework describes rather than drives.**

Per Seat 4's caution, this is checked **before** W2–W6 are built on top: *six workstreams
resting on a narration layer that turns out to be decoration would be the elaboration trap at
architecture scale.*

**Operationalised, with the null PINNED BEFORE THE RUN** (Seat 4: *"stating it afterward is
how a null gets absorbed"* — same discipline as the seed-stability criterion, stated against
a shuffle rather than a number):

- **Arms**: C (narrate-and-consume: ROUTE/MINT read their own immediately-prior narration
  state, e.g. the retained stale-mark) vs W (narrate-only: write-but-never-read). Same game,
  same seeds regime, alternating episodes.
- **N, derived not asserted**: enough episodes per arm that the rarest ROUTE bin's expected
  count is ≥ 20 in each arm, computed from that game's observed bin rates before the run.
- **Three statistics, pre-named**: (1) total-variation distance between the arms' ROUTE-bin
  distributions; (2) TVD between mint-verdict distributions; (3) per-step action agreement
  rate against matched episode indices.
- **The null**: permutation — shuffle episode→arm labels 1,000 times, recompute all three
  statistics per shuffle. **The falsifier FIRES (narration is decoration) iff ALL THREE
  observed statistics fall inside their shuffled 95% bands.** Narration drives iff at least
  one pre-named statistic exceeds its band. No other statistic may be substituted after the
  run; a surprise elsewhere is a new finding, not a rescue.
- On firing: recorded as a finding, and W2+ redesigns around instruments rather than
  narration.

## FALSIFIERS FOR THE BUILD ITSELF
- **F1 · IT NARRATES**: every step emits exactly one record with bin + why-not-neighbour +
  memory-range tag. *Fails if:* any step is silent or any record lacks the range tag.
- **F2 · IT IS CHEAP**: per-step overhead ≤ 5% of current per-action time, measured against
  the D-5 baseline profile (this is why the baseline runs first). *Fails if:* narration
  worsens D-5.
- **F3 · KNOWN-NEGATIVE**: a replayed/observe-only step narrates as `[REPLAY]`, never as a
  fresh decision — narration must not launder playback into reasoning.
- **R4 on the stream**: a constructed episode with a known bin sequence must reproduce that
  sequence in narration (sensitivity); a no-op step must not fabricate a bin (specificity).

## UNDO
The stream is append-only JSONL with its own topic; the emitter is one call site per loop
point. Remove the call sites; records remain readable as history. Consumer entry in the
ALLOWLIST cites this prereg until the falsifier experiment consumes the stream.

## COST NOTE
Narration lands *before* the index (W2) by design: W2's provenance tags are written by the
same events narration reports, so the emitter sites are shared — build once, two consumers.


---

## ARM C's CONSUMPTION MUST BE REAL (Seat 3, 2026-08-20 — pre-briefing amendment)

> *"A consume arm that reads narration and makes the same decision anyway would produce a
> true null about a wire rather than about the framework."*

The pinned permutation null handles the statistics; THIS clause handles what the statistics
are about. **Arm C consumes narration at named decision points where the decision DIFFERS
by construction**, with narration as the only carrier of the consumed fact:

1. **ROUTE consumes the prior BET's discriminating fact.** When the current residual falls
   in the ambiguous band between neighbour bins (the discriminating fact's own threshold
   region), arm C resolves the tie using the prior bet's stated expectation; arm W applies
   the bare rule's default. *Decision point: borderline residuals route differently.*
2. **MINT consumes its own guard-zero history.** If the last narration for this signature
   named a guard as the zero, arm C does not re-offer the same candidate until the narrated
   zero's input has changed (support grew, route changed); arm W re-offers every cycle.
   *Decision point: mint attempts differ in count and timing.*
3. **ACT consumes the bet's confidence phrasing** only through 1 and 2 (no third wire
   invented for symmetry — two real wires beat three thin ones).

**THE WIRE CHECK, before the experiment may run:** a constructed episode in which
consumption provably FLIPS a decision — a borderline residual that routes one way with the
prior bet present and the other way with it absent, and a guard-zero repeat that arm C
skips and arm W re-offers. **Sensitivity for the wire itself.** Only after the wire check
passes does a null in the experiment speak about the framework rather than the wiring —
if the wire check cannot be made to pass, that is reported as "the consume arm is thin"
and the experiment does not run in disguise.
