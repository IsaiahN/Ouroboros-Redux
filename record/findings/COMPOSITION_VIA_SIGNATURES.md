# COMPOSITION VIA SIGNATURES — the seven questions, answered from code (2026-08-21)

Seat 3's claim checked: *the applicability index is a partial type system; if postconditions
derive the same way, composition becomes a signature match.* Per-question, with sites.

## 1 · Does `anchor_signature` give a usable precondition? YES for pruning; composition
needs nothing more IF two-stage
`applicability.py:155-184`: `{min h, min w, intersected palette, content key}` — the
weakest requirement over every application path. It is deliberately coarse (no object
count, no topology). **Composition should use it exactly as retrieval does: signature
prunes, the matcher verifies** — prune-then-verify, not type-match-decides. Extending the
signature (object count, region properties) would sharpen pruning but is an optimisation,
not a prerequisite.

## 2 · The postcondition derives at mint time, and most of it ALREADY EXISTS in sigma
From what `learn_effect` already crops: resulting dims (= input dims, grid-to-grid),
colours WRITTEN (`sigma.colour_delta` — stored on 100% of atoms since forever), changed
count + changed-mask key (the mint's `_signature` hashes exactly this), palette-after
(before − consumed ∪ written). **Same function shape as `anchor_signature`, same write
site, no new computation** — a `postcondition_signature(atom)` is an afternoon of factoring,
not a design.

## 3 · Where it fails — THE HONEST ANSWER, and the recovery
**Naive signature-match composition DOES mostly swallow everything**: grid-to-grid,
palettes usually unchanged → dims/palette postconditions give almost no pruning. The
claim as stated fails. **But two recoveries, both already in the machinery:**
- **The ENABLES edge prunes genuinely**: A *writes* colour/cells that B *requires* and the
  current frame lacks. Derivable purely from `colour_delta` + palettes — a sparse directed
  graph over Γ, computable at mint, no execution. This is means-ends analysis falling out
  of the signature algebra: the edge exists exactly where A manufactures B's precondition.
- **The decisive check is now cheap enough to BE the type check**: post-vectorisation, one
  application is ~0.37ms. "Does A's after-state satisfy B's context" is a concrete
  matcher call on the predicted state — and `planner._run` ALREADY chains this way,
  memoised. Signature prunes candidates; simulation decides; 29× made simulation
  affordable as the judge.
**Verdict: signature-ONLY composition fails here; signature-pruned, simulation-decided
composition is already how the planner works, and the ENABLES edge is the new pruning
composition adds.**

## 4 · Chains stay checkable — algebra where disjoint, simulation where entangled
Exactly compositional without running: palette deltas (written/consumed sets compose
associatively) and disjoint-bbox changed regions (union). NOT signature-carriable: B's
dependence on frame content outside A's patch. The boundary is clean: **disjoint steps
compose by algebra; entangled steps compose by simulation on stored patches** (~0.4ms/step)
— and `planner._finish` already verifies whole chains by forward replay before returning
one. Chains longer than two are reachable today: `_run`'s memoised recursion is
depth-general.

## 5 · `effects.compose()` IS the registry half, already as specified
`effects.py:1033-1050`: memoises the id list into a COMPOSITE atom record on the same
stream, origin-marked, **identity = sha1 of the parts list — the composed-from tags ARE
the name**, exactly as Seat 3 settled the handle question. **What it lacks: any signature.**
`applicability.py:198` — COMPOSITE = NO-REQUIREMENT, never pruned, index-invisible. The
gap and the pricing converge beautifully: **the composite's precondition derivation
(step 1's context + unguaranteed residues) IS the composite's price derivation — one
computation, two consumers** (three, counting the admission gate's known hole).

## 6 · COMPOSITEs nest today
`compose()` filters components only by `self.get(i) is not None` — no kind check, so a
COMPOSITE id is a legal part. And `planner._run` recurses through COMPOSITE parts, so
nested composites execute. **No one-level cap.** (Untested in the gate suite — noted as
unblocked-but-ungated; the composer brief adds the nesting gate.)

## 7 · Earn-through: ONCE is right, and "once" means a LIVE frame
`compose()` today writes the record with no verification the chain runs. Rule 1 makes a
composite compression — but its applicability (the unguaranteed residue actually occurring
in the world) is a fact about the world, not about the parts. **Proposed: mint-time
composite = CANDIDATE; first correct prediction on a live frame = citable.** Simulation on
stored patches does not count as the settle — stored patches are the components' own
claims, and a chain settling against its own premises is agreement, not evidence. This is
the mint's existing candidate→settled discipline at the composite grain (one rule, many
grains, candidate #5), and it slots into the gate naturally: an unsettled composite may
appear in a BET (a claim) but not as GROUND.

## Carried into the composer brief as known holes (per Seat 3)
1. **The unpriced-composite admission hole**: composites have no extent; `admission_price`
   passes unpriceable shapes ungated (stated by that builder). Fix shape: the derived
   composite price (= its derived precondition) becomes its admission price — the same
   derivation a third time.
2. **Missing-component import**: admit-as-catalogue-aim per the standing answer; the
   composer design formalises it.
3. **The COMPOSITE nesting gate** (works, ungated).
4. **The ENABLES-edge index** as composition's genuine new pruning structure.

## Queue position (Seat 3's directive, recorded)
Composer DESIGN work queued now — after the movement read and book rebuild, ahead of
standing items — **sized on the branch**: metal-key branch → the composer waits for
ego-shift compensation (its material roughly doubles); elsewhere-branch → it proceeds on
the click vocabulary and the census becomes a separate read. Written against a known
library, never a hypothetical one.

## And at the queue's end: THE SWARM RUN, with its purpose stated before it starts
Per Seat 3: not diagnostics — play. Clean baseline, six builds deployed, gate in shadow.
**Stated purpose: feed the split-half read on post-incident data.** Stated stop: every
scoreable game reaches its derived 2k sessions (lp85 already there; sk48 the tail at 26),
then the read runs and reports improved/regressed/unchanged per game. A fleet running
because it is up is what produced eight dirty deploys — this run has a number it is for
and a condition that ends it.
