# PROPOSAL — THE COMPOSER (2026-08-21). Design, not build. Sized on the branch: proceeds now.

Inherits, settled elsewhere and cited: two-shelf vocabulary (`PREREG_MOVEMENT_MINT_READ`
result), the seven composition answers (`COMPOSITION_VIA_SIGNATURES`), pricing = precondition
= admission (one derivation, three consumers), catalogue-aim degradation, context-match as
the recording discriminator, nesting, live-frame settlement, the cross-shelf ENABLES edge.

## 1 · What the composer IS
Not a new organ: **a promotion of the planner's existing chaining into a citable, priced,
gated capability.** `planner._run` already chains memoised applications; `effects.compose()`
already registers id-lists as COMPOSITEs. The composer adds exactly four things:
1. **The postcondition signature** (factored from sigma at mint — Q2's afternoon).
2. **The ENABLES-edge index**, both within-Γ (A writes what B requires) and **cross-shelf**
   (a BODY delta puts the avatar where a Γ atom's context anchors — position facts meeting
   patch facts; the design's one genuinely new algorithm).
3. **The composite signature/price derivation** (start_extent + Σ unguaranteed residue +
   length) written at compose-time, consumed by index, admission, and the gate's PAY.
4. **The settlement wire**: composite minted = CANDIDATE; first correct live-frame
   prediction = citable (proposable-not-standable until then).

## 2 · The two shelves and their edge
- **Γ shelf**: world-edit rules, context-keyed, applied by the vectorised matcher.
- **BODY shelf**: per-action (dr,dc) deltas with evidence counts (the bank), plus the
  action book's inverse pairs and costs. Locomotion composes by VECTOR ALGEBRA (sum of
  deltas — exact, no simulation needed) — the cheap shelf.
- **The cross-shelf edge**: `reach(p) ∘ click_atom(anchored at p)`. Derivable at query
  time: for a Γ atom with anchor cell set A and the avatar at v, the enabling BODY chain is
  any delta-sum from v into A — a shortest-path query over the BODY algebra with the
  frontier book as obstacle mask. **This is means-ends across shelves and it is the
  composer's core loop: pick a WANT (diff cells), find Γ atoms whose effect intersects it
  (means-ends within Γ), then find BODY chains that reach their anchors.**

## 3 · The compose loop (all existing machinery, one new ordering)
```
WANT (diff/predicate) → Γ candidates by effect∩diff (ENABLES toward the goal)
  → per candidate: anchor reachable? (BODY shortest-path, frontier-masked)
  → chain = [BODY deltas..., Γ atom] → simulate entangled seams (~0.4ms/step)
  → cheapest chain by the derived price → COMPOSITE minted as CANDIDATE
  → driven via the planner's existing drive path → settles on the live frame
  → citable (or conflict-tightened on failure, ctx machinery unchanged)
```
Chains that edit-then-move-then-edit alternate shelves; nesting handles depth.

## 4 · Falsifiers (pinned now, refined at prereg)
- **F1 · the chain settles**: a constructed two-shelf chain (move, then click) predicts its
  live outcome exactly once before citation; an unsettled composite refused as GROUND.
- **F2 · the price is derived**: EXTENT-style dial test — composite admission at the
  derived price rejects a bundle-of-unrelated-steps whose parts pass individually; a
  well-chained twin passes (the discount is real).
- **F3 · the recording discriminator**: a coordinate-keyed step-list (a disguised
  winning_sequence) is refused composition; the identical chain expressed context-keyed
  composes. Both constructed.
- **F4 · cross-shelf reachability is honest**: an anchor behind a frontier-book fatal cell
  yields no chain (the mask consulted); clearing the mask yields one.
- **R4**: constructed two-shelf worlds reproduce expected cheapest chains exactly.
- **The falsifier of the whole design**: if, with the composer live, driven composite
  settlements do not raise g7 above zero on any L1+ game within the swarm-run window, the
  promotion failed and the finding is about the WANT supply (abduction), not chaining.

## 5 · What it does NOT do
No new search (the planner's, scheduled by W2b, is the driver) · no authored action
semantics (the book + bank are the sources) · no bulk import (components pass admission
individually; missing components degrade to catalogue aims) · no self-settlement
(simulation never counts as the settle).

## 6 · Build order when cleared (each stage its own prereg + falsifiers)
1. Postcondition signature + composite signature/price (the factoring; unblocks admission
   hole + index visibility + nesting gate).
2. The ENABLES indices (within-Γ, then cross-shelf reach).
3. The compose loop behind the W2b scheduler (the planner drives; g7 is the counter).
4. The settlement wire into the gate's BET/GROUND discipline.
Stage-1 shadow gate proceeds in parallel — the composer's utterances are exactly the
composition requests the gate was designed to check.
