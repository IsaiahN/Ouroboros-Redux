# The New Horse — a clean implementation of THE MAP

This branch is a fresh start. It is **not** a patch of Ouroboros-Redux (the "clunky horse"),
it is the implementation **THE MAP** describes, built from the spec. Redux stays on `main`.

## Why a new branch
Three cycles of trying to retrofit ONE map-specified component (the falsified ledger, MAP §9.4)
into Redux kept confirming the map's own verdict: Redux is *"a machine that was never fully switched
on,"* and bolting parts on is slow and hard to verify. The components the map requires are cheap to
build first-class here and a nightmare to retrofit there. So we build the right one.

## The thesis (MAP §I)
Intelligence is **aiming variation with a spec** — lowering the *exponent* of the search, not escaping
its cost. **Foundation check: PASSED.** The F\* problem-shape coordinates carry real, measurable
structure — the reverse-map falsifier on the 46-framework kernel gave a search-reduction edge of
**1.29×**, top-5 recall 17% vs 11% chance, against a shuffled-F\* null of 1.01× (**p < 0.001**). We are
building on a foundation that held under its own test (MAP falsifier E.1 does not fail).

## What to build — the required properties (MAP §VII)
1. **Typed grammar** — not a flat bag; typing beats size.
2. **Full-resolution perception** — never downsample the grid; a 5-pixel glyph is an exact symbol.
3. **Two streams** — environment shapes within a rung; actors select between rungs; **actors must be priced**.
4. **A pose** — each shell has a vantage + a learnable weighting α over private history vs network wisdom.
5. **Allocentric + egocentric** — `(EgoMap, Pose) → Map`; the allocentric map is the integral of egocentric deltas.
6. **The marketplace** — propose → vote → resolve; the currency is **prediction error at full resolution**.
7. **The residual** as aim and sense organ — what the grammar failed to predict, moved upstream of generation.
8. **Shadow-first, echo-second** — shadow decides whether to mint; echo decides promotion.
9. **The brake** — a claim's strength never exceeds its gate.
10. **Monolith-then-carve** — gate the wiring, never the design; the real gate is the live environment.
11. **The falsified ledger** (CRISPR spacers, §9.4) — a weighted, persistent memory of what to **REJECT**,
    so trials aren't re-spent on dead ideas. The exact thing Redux structurally cannot do.

## Hard bounds — constitutional, enforced at import (MAP §VIII, §9.3)
- RESET banned during active play (earned only).
- No downsampling, anywhere, for any reason.
- Never encode the answer — the agent reasons its own way to it.
- Never ship half a mechanism.
- Nothing may happen silently — no isolated code, no silent code, no code without reason.

## First slice (to be scoped with Isaiah)
A minimal but COMPLETE loop on ONE clean-perception game, against an uncontaminated baseline through the
live gate: **typed grammar + full-resolution perception + the falsified ledger**, wired
`PERCEIVE → THINK → MAP → ACT` with both feedback arrows. Monolith-then-carve: build the whole small loop,
let the live environment be the gate.

*The map is finished. This branch is where it gets built.*
