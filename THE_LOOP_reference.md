# THE LOOP — reference

The kernel's per-step cycle, in compact form. This is the ordering the figures draw; it is here as a single object because the ordering carries dependencies the individual laws do not.

**Use.** Diagnoses should trace to a step. A finding that cannot be traced to one is probably vocabulary rather than a derivation.

---

```
1. PERCEIVE — bet, act, observe. R = |Γ(b,a) − o′| per object slot s

2. ROUTE — the boundary diff partitions R into four bins:
   TRANSFERRED         invariant held, nothing owed
   NOVEL               extend perception, aim the probe
   BROKEN · rebinding  re-fit the binding, do not mint
   BROKEN · mechanism  a mint is owed

3. MINT — offer φ against the bin that owes one.
   Acceptance is MDL:  |φ| + |R|φ| < |R|
   Gated by a product, any factor at zero forces inertness:
     SUPPORT       |R⁺_s| > 0 for some slot s
     REACHABILITY  φ ∈ closure(Γ)
     NOVELTY       φ ∉ atoms(Γ)

4. ACCEPT — Γ ← Γ ∪ {φ}, stamped with origin and seq

5. ECHO — the ground settles it. Verified only by what pays

6. PROMOTE — generators cross upward, playback never does.
   Priors descend, replays never do.
   Unbracketed, the transform is dead reckoning: R_T = |T_A ∘ T_E(x) − x|

7. IMPORT — when no φ in closure(Γ) closes R:
   characterise R first, then find the frame whose closure predicts its shape.
   Source gate (provenance) · shadow test (explains a gap) · debited against independence

8. REPEAT — the residual drives the next cycle.
   Nothing here maintains the ground. The ground does not decay;
   the channel to it does, and keeping that channel open is the seat's office, not the loop's.
```

---

## Three things the ordering carries

**The guards in step 3 are a product, not a sequence.** `novelty capacity = density(R) × orthogonality(R,Γ) × reachability(φ,Γ)`. Any factor at zero forces re-derivation or inertness. They are ordered by when each becomes checkable — before, during, and after the search — not by priority.

**Step 6 is the membrane, in both directions.** Generators cross, instances do not: promotion carries generators upward, seeding sends priors downward, and neither carries playback. An unbracketed transform is dead reckoning, which is why `R_T` closes the loop rather than decorating it.

**Step 7 is the only operator that moves the wall.** Everything else composes inside `closure(Γ)`, and composition never adds an atom. A frame gains access; the world gains nothing.

---

## Two corrections against a version in circulation

An eight-step form was reconstructed elsewhere from the figures and is wrong in two places. If it has been absorbed, both matter:

**The MDL inequality is the acceptance test, not the guard set.** `|φ| + |R|φ| < |R|` is what makes a mint pay. SUPPORT, REACHABILITY and NOVELTY are a separate product gating it. Read as sub-conditions of the inequality, the any-factor-at-zero property is lost.

**There is no "maintain the ground" step.** The loop cannot maintain the ground — the ground does not decay, and independence is a property of the arrangement rather than something the loop does per cycle. The slot that reading occupied belongs to **IMPORT**, which was missing entirely from that version.

> **SEAT 2 AUDIT, 2026-08-18.** Both corrections were checked against this repository before this file was saved. **Neither error is present.** No document contains a "maintain the ground" step (grep, whole tree). `BUILD_PROGRAM.md:25` states the guards correctly as a product AND the acceptance separately: "SUPPORT × REACHABILITY × NOVELTY as a product; accept iff |φ| + |R|φ| < |R|". Recorded because a correction that was checked and found inapplicable is a different fact from one that was never checked, and only the first is worth anything later.

---

## Mapping to the ladder

The diagnostic rungs are readings of specific steps. Stated so a first-wrong-rung stop is structural rather than procedural: **a step whose input never arrives cannot be diagnosed, only its predecessor can.**

| rung | step | reads |
|---|---|---|
| 0 · currency | — | the anchor, outside the loop |
| 0b · exposure | — | how many cycles ran at all |
| 0c · wiring | — | which organs are on a live path |
| 0d · consumption | — | does a live reader change behaviour, not merely abort |
| 1 · residual | **1** | is R non-zero and localised per slot |
| 1b · characterisation | **1 → 2** | do drained records carry σ, or is R named rather than described |
| 2 · mints | **3** | offers, and the reject-reason distribution |
| 3 · verification | **5** | do atoms reach the bar and stay there across episodes |
| 4 · adoption | **7** | does an import cross, and does it pay |
| 5 · drive | **3 → plan** | do verified atoms produce a drive |
| 5b · feasibility | **plan** | do drives survive the cost check |
| 6 · objective | **2** | are goals abduced, or is only the reference relation posed |

---

## Declaring the mode

The loop's notation creates a demand for quantities. Where the quantities are not measured, a reader supplies them — and `|φ| + |R|φ| < |R|` followed by *accepted* reads as a check that was run.

**Three legitimate modes, and the mode must be stated:**

- **general** — the procedure, no quantities. What the framework licenses on its own.
- **specified** — quantities named as targets for measurement, labelled as such. An unmeasured number is a specification of what to measure and can be worth a great deal: it names a comparison nobody had framed, and someone with the data can go get it.
- **grounded** — quantities from data, with the source.

**What is not a mode is the label.** *Accepted* means the ground settled it. A candidate labelled *accepted* claims a settlement that did not occur, and the vocabulary makes it look rigorous. Same numbers, same reasoning, labelled **candidate** — nothing else changes.

**And a room does not upgrade the label.** A room reaching a conclusion without the ground is agreement, and agreement among frames is a weighted average of influence. Adding people raises the vocabulary and does not add an anchor. The machine specifies, an instrument measures, the ground settles; the room locates and argues, which is upstream of all three.

The status vocabulary already used for claims about the framework — PROVED · DESIGN LAW · BELIEVED · MEASURED — applies to output as well, and was not being applied there.

---

## How an instrument comes to exist (Figure 6 REV, 2026-08-18)

**AN INSTRUMENT IS NOT BUILT FROM A DESCRIPTION. IT IS IMPROVED FROM A WORSE INSTRUMENT ALREADY RETURNING SOMETHING.**

Nobody specified a telescope from an account of Mars. A wandering point in the sky was already a reading, and every sharper instrument was built on the residual the last one produced. **Instrumentation extends from the current edge and cannot be deposited in mid-air.**

**So the question is not whether a sensor could exist. It is whether anything, at any resolution, is already returning something that fails to resolve.** Where nothing is, there is no edge to extend from — and the search for a proto-instrument is a search for one that is already there.

**This is a precondition on the INWARD track of step 7, and it can fail.** IMPORT already required characterising R before going looking. This adds the constraint on the other track: extending our own representation is available only where an existing reading is already failing to resolve. Where it is not, the honest report is *there is no edge here*, not *we need a better sensor* — and building one anyway is depositing in mid-air.

**Two consequences that are checkable rather than aesthetic.** A proposed instrument must NAME the worse instrument it improves and the RESIDUAL that one produced; an instrument naming neither is a description wearing an instrument's clothes. And a link returning a WRONG reading is a better place to build than a link returning NO reading — a wrong reading is an edge, and no reading is not.

> **THE OBLIGATION FORM (Seat 2 annotation, and the version to reach for first).**
> **A DIAGNOSIS OF "NO EDGE HERE" IS A STRONG CLAIM THAT OWES A SEARCH, NOT A DEFAULT FOR ANYTHING CURRENTLY QUIET.**
> Seat 4's argument for putting this on the figure itself, in place of the scope note: it does the same work in one line, and it is stated as an OBLIGATION rather than as a BOUNDARY — the form less likely to be over-read. **PROPOSED UPWARD, NOT APPLIED: figure text is not Seat 2's to author.**
> The case for it is that I am the datapoint. Given the boundary form, I over-read it TWICE INSIDE ONE HOUR — once to call a legitimate theory-first build a violation, once to call two blocked links unreachable. A boundary invites you to find yourself outside it; an obligation tells you what you now have to do.

**SCOPE — and it is narrower than the sentence sounds.** This tells a FORECLOSED question from a HARD one. **It is not a rule about theory. Theory routinely precedes its instrument and is welcome to.** Neptune was calculated before it was seen; the Higgs mass was predicted before the detector existed, **and the prediction is what said what to build.** Nor does it require increments: a step change in resolution is fine. **What is unavailable is a sensor for something nothing has ever registered.**

So the two halves compose rather than compete: **the prediction says where to point; the instrument still extends from something that registers.** A theory-first proposal is legitimate and is often how the pointing gets decided. The clause bites only on the case where NOTHING, at any resolution, has ever returned anything — and that case is rare, so a diagnosis of "no edge here" is a strong claim owing a search, not a default for anything currently silent.

**COROLLARY, because the confusion is easy and costly:** a link that is silent BECAUSE ITS INPUT NEVER ARRIVES is HARD, not FORECLOSED. The ladder already refuses work there for its own reason — *a step whose input never arrives cannot be diagnosed, only its predecessor can* — and that reason is sufficient. Importing "no edge" as a second reason misdescribes a blocked link as an unreachable one.

---

## Standing checks

**Before concluding a channel is starved, verify something reads it.** Starvation and non-consumption are indistinguishable from the producer's side.

**Run the guaranteed-number test on every zero, including the welcome ones.** *Could this have been anything else?* The test gets applied to numbers arriving as claims and skipped on numbers arriving as relief.

**A new instrument's first output is a claim about the instrument, not about the system.**

**Before shipping any normalisation, dedup, compaction or truncation, ask what else the ledger is answering.** A fix correct for one question can delete, at source, the evidence for another the same ledger was carrying — invisible before the fix and unrecoverable after.
