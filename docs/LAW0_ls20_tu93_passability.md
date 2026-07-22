# LAW-0 findings: passability basis for ls20 & tu93 (P4.3 game selection)

**Rule invoked:** LAW 0 — SEE BEFORE YOU SAY. Rendered both recordings with `tools/render_run.py`, READ the
pixels, then verified numerically (cursor = the small high-motion connected component; passable colour = the
colour its own new cells held *before* it stepped in — a before-state trajectory fact, not the move/blocked
label). Recordings used:
- ls20: `recordings/50d29d18-.../ls20-9607627b-f0831ace-....jsonl`
- tu93: `recordings/a9e77dad-.../tu93-0768757b-9f18534d-....jsonl`

## What the pixels + numbers say

| game | true cursor colour | passable floor (steps ONTO) | walls | outer background |
|------|-------------------|-----------------------------|-------|------------------|
| ls20 | 12 (small teal marker of the maroon 9/11/12 sprite) | **3 (green)**, 1280 step-ons | 4 (yellow) | 4 (yellow) |
| tu93 | 4 (yellow dot) | **0 (black corridors)**, 26/27 step-ons | 2 (red) | 5 (grey) |

Both are clean "move iff the cell ahead is passable" mazes with **different palettes** (passable 3 vs 0) — the
intended setup for an INTENDED_FREE cross-game echo (colour-specific INTENDED_COLOUR would NOT echo; the P4.3
mechanism gate already proved that).

## The correction LAW-0 forced (do not skip)

The prior beat's **live tu93 mint `INTENDED_COLOUR==5` (grey) was a perception-basis error.** Grey (colour 5,
~3465 px) is the *outer background the cursor never enters* — not the corridor. The true passable colour is
**0 (black)**. Likely cause: `AffordanceMintBridge` took a pixel centroid over a mis-identified (large) cursor
object, so "the cell the cursor would enter" landed in the grey surround. This is charter guard #4 exactly — a
residual computed in the wrong ontology is *consistent-but-lying*. The 5.1-bit mint was real compression of a
**spurious** basis. (ls20's `INTENDED_COLOUR==3` is, by contrast, pixel-confirmed CORRECT.)

RULE 0.7: one run ≠ a verdict — but a pixel+numeric disagreement with a prior claim is enough to retract it.

## Consequence for the code (next beat, unblocked by this)

`AffordanceMintBridge` must derive `intended_free` from a **discovered passable set**, computed leak-free as the
colours the cursor historically stepped onto (its own trajectory), NOT from a hardcoded `core.bg` and NOT from
the move outcome it is trying to predict. Then:
- ls20 passable → {3}, tu93 passable → {0};
- `intended_free := intended_colour ∈ passable_set` makes **INTENDED_FREE** (colour-agnostic) the clean predictor
  in *both* games, so it can echo across them and PROMOTE — the live join of fail→mint→ECHO→PROMOTE.

This keeps the abstraction honest: passability is learned from the agent's own motion history (structure), the
minted φ still predicts a *held-out* step's move/blocked outcome, so it is a regularity, not a tautology.
