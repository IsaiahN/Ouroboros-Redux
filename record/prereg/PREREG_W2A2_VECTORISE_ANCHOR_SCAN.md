# PREREG — W2a-2: VECTORISE THE ANCHOR SCAN (2026-08-20)

**AUTHORITY:** the pre-committed successor of F1's losing condition
(`PREREG_W2_APPLICABILITY_INDEX.md`: *"if the share holds, the cost is per-application work,
not candidate count, and the fix is vectorisation"*). F1 held: 92.5% vs 95.3% on the
identical window, with per-call applications already halved by the index. The cost is
INSIDE `apply_effect`: ~4ms and ~1,450 numpy `.all()` calls per application — the anchor
scan comparing the atom's context patch at every position by per-anchor slicing.

## THE BUILD
Replace the per-anchor Python loop in the raw-context scan path of
`effects.py` (`apply_effect`/`_apply_typed` seam) with a **whole-frame vectorised match**:
compute all candidate anchor positions in one numpy pass (e.g. sliding-window view via
`numpy.lib.stride_tricks.sliding_window_view` + a single equality reduction, masked by the
patch's nonzero mask), then apply at the matched anchor(s) exactly as today.

**SEMANTICS FROZEN:** same matches, same tie-breaking order (first anchor in the existing
scan order wins), same returned arrays byte-for-byte. This is a speed change with zero
behavioural degrees of freedom — which is what makes it preregisterable.

## FALSIFIERS
- **F1 · EQUIVALENCE (absolute):** on a generated corpus of (atom, frame) pairs spanning
  dims/palettes/masks/edge-anchors — plus every atom in a real box replayed against recorded
  frames — the vectorised path returns **byte-identical** results to the scalar path,
  including None-cases and tie-breaks. Any divergence fails the build.
- **F2 · THE SHARE COLLAPSES (the point):** same 420s window, same worker: `apply_effect`
  cumulative share drops to a minority share. *Fails if it holds again* — and the
  pre-committed successor of THAT failure is named now: the cost would then be search
  breadth (states explored), and the fix is W2b scheduling + the stage-2 diff-directed
  selection, not further micro-optimisation.
- **F3 · KNOWN-NEGATIVE:** a patch that matches nowhere returns exactly what the scalar
  path returns for no-match; a multi-match frame picks the same anchor as the scalar order.
- **R4:** constructed frames with known anchor sets reproduce those sets exactly.

## UNDO
The scalar path remains in the file behind the same function signature (one internal
dispatch); reverting is deleting the dispatch to the vectorised branch.

## SCOPE GUARD
No changes to signatures, mint, planner, or the index. `effects.py` only, plus its gate
test. The memoisation and COMPOSITE recursion in `planner._run` are untouched.
