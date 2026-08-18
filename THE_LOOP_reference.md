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

## Standing checks

**Before concluding a channel is starved, verify something reads it.** Starvation and non-consumption are indistinguishable from the producer's side.

**Run the guaranteed-number test on every zero, including the welcome ones.** *Could this have been anything else?* The test gets applied to numbers arriving as claims and skipped on numbers arriving as relief.

**A new instrument's first output is a claim about the instrument, not about the system.**

**Before shipping any normalisation, dedup, compaction or truncation, ask what else the ledger is answering.** A fix correct for one question can delete, at source, the evidence for another the same ledger was carrying — invisible before the fix and unrecoverable after.
