# PREREG — W1: THE NARRATION SPINE + MEMORY AT THREE RANGES (2026-08-20)

**AUTHORITY:** the accepted refactor plan, W1; Seat 3: *"Start W-1, you are clear to proceed."*
**STATUS: PREREG + BUILDER BRIEF. Agent code — a firewalled builder writes it.** This document
is the brief: mechanics only, no game specifics, predicates named not answers.

## WHAT IT IS
One build, two faces (Seat 3: *"one change, not two"*):
1. **The agent narrates its own loop, in the loop's vocabulary** — at six points per cycle:
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

**Operationalised:** run N episodes narrating-and-consuming (the ROUTE/MINT decisions read
their own immediately-prior narration state, e.g. the retained stale-mark) vs N narrating-only
(write-but-never-read). **If the consuming arm's bin distribution, mint verdicts, and action
choices are statistically indistinguishable from write-only, the falsifier FIRES** — recorded
as a finding, and W2+ redesigns around instruments rather than narration.

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
