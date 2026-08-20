# D-5 NAMED: THE PLANNER THAT HAS NEVER DRIVEN AN ACTION CONSUMES 95% OF THE COMPUTE (2026-08-20)

**The W1 baseline read.** cn04 (0.1 actions/min live), 420-second cProfile window, dump-on-
timer. **Proportions only** — cProfile inflates absolutes; no threshold is set against these
numbers (F2's cap measures un-profiled wall-clock: cn04's live rate is already known).

## THE PROFILE, AND IT IS NOT CLOSE

| share | site |
|---|---|
| **97.6%** | `planner.py:146 plan_to_identity` — **5 calls** in the window |
| **95.3%** | `effects.py:523 apply_effect` — **47,418 calls**, 188s own time |
| 34.2% | `numpy.ndarray.all` — **77.7 MILLION calls** |
| 23.7% | `effects.py:480 _apply_typed` |
| 19.7% | `numpy.ufunc.reduce` |

**Ten loop cycles in the window. Five entered the planner. Each planner call ran ~9,500
`apply_effect` evaluations, each doing full-array `.all()` comparisons — ~1,600 numpy
scans per application, 77.7M in total.** The planner brute-forces **every atom × every
anchor position** against the frame, with no pruning of which atoms could possibly apply.

## THE SENTENCE THAT MATTERS
> **The planner has never produced a plan with steps (g7 = 0, ever) — and it consumes ~95%
> of a slow worker's runtime searching for them.**

The agent spends nearly everything it has on a search that has never once returned, and the
80 seconds per attempt is un-indexed atom application. **D-5's 2×2 is now mechanically
explained**: the planner path engages only when atoms exist (g6) AND a reference snapshot
binds (g4/g5) — which is precisely `atoms + L1`, the slow cell. `sk48` (L1, 0 atoms) skips
at g6 → fast. The L0-with-atoms games pay a partial term. **Atoms × levels = search space ×
search engagement. Progress buys slowdown because progress switches this search on.**

**The fourth layer, as Seat 4 predicted**: API cap → fabric read → commit batching →
**the planner's brute-force atom application.** Each earlier fix was real and relocated the
bottleneck; this one is currently the work itself — done ~1,600× less efficiently than an
indexed lookup would allow.

## THE W2 DECISION, PER THE RULE STATED BEFORE THE PROFILE
*"The index attacks the term the profile names, or W2 is re-scoped."* **Verdict: re-scoped —
the profile names retrieval, but not the retrieval W2 led with.**
- **W2's FIRST deliverable becomes the APPLICABILITY INDEX**: for each atom, an anchor
  signature (context patch hash / dimensions / palette) so `plan_to_identity` prunes the
  candidate set *before* `apply_effect`, instead of applying everything everywhere. This
  attacks the named term directly — the 77.7M `.all()` calls are the cost of not knowing
  which atoms can apply where.
- **Provenance tags and the catalogue remain W2 deliverables two and three** — they share
  the same write-sites — but they are the layer above the named term and no longer claim
  its number.
- **Measured against this baseline**: success = the planner's share collapses on the same
  window, or the same search completes in seconds. The falsifier: if pruning the candidate
  set does NOT collapse the share, the cost is in `apply_effect`'s per-application work, not
  in candidate count, and the fix is vectorisation rather than indexing — a different build.

## STANDING NOTE FOR W1's F2
The narration overhead cap (≤5%) is measured against **live un-profiled wall-clock**
(cn04 ≈ one action per 10 minutes at last live measurement), never against profiled numbers.
