# THE COLOUR INVARIANT READ (2026-08-20) — Seat 3's three questions, answered from our own data

**The question:** is colour identity the right invariant, or a naming convention treated as
physical law? **A read, not a build** — upstream of W2 stage 2, as ordered.

## Q1 · How are the atoms keyed? (census: 2,009 atoms, every box)

- **100% colour-IDENTITY keyed.** Every atom is a raw EFFECT with literal colour patches;
  zero wildcards. An atom that learned *3→4* learned it about colours 3 and 4, verbatim.
- **66% are π-transportable** (result colours ⊆ context colours: a colour permutation
  inferred from the context match determines the result). **34% introduce colours absent
  from context** — those need a colour anchor.
- **THE FINDING UNDER THE QUESTION: the relation is ALREADY RECORDED.** `sigma.colour_delta`
  — the from→to colour mapping — is computed at mint and stored on **100% of atoms**. It is
  consumed by **nothing**. The produced-not-consumed genus, at exactly the point Seat 3
  aimed at: **the mint already knows the transformation fact; the matcher only ever uses
  the palette fact.** And for the 34% that introduce colours, `colour_delta` IS the missing
  anchor.

## Q2 · Do palettes shift in the public set? YES — in our own frames, three ways

Census of all 676 level-up pre/post snapshots (`levelup_frames`, kept for exactly this):

| game | level-ups | palette unchanged | **REMAPPED** (colours simultaneously gone AND new) | pattern |
|---|---|---|---|---|
| **cn04** | 61 | 0 | **56** | 10 vanishes; 9, 11, 12 appear — **the board relabels at level-up** |
| **m0r0** | 56 | 0 | **51** | 0, 11, 12 → 8, 6, 15 |
| **sp80** | 72 | 0 | **67** | 0 → 8, 13 |
| ar25 | 139 | 73 | 0 | colour 4 consumed (objects, not labels) |
| ft09 | 57 | 4 | 0 | colours consumed |
| cd82 / sk48 / r11l | 193 | 0 | 0 | new colours appear (new object kinds) |
| lp85 | 98 | 98 | 0 | perfectly stable |

**Three of nine L1+ games RECOLOUR the board at essentially every level-up** — and one of
them is cn04, the slowest worker in the fleet. **Seat 3's suspicion confirmed from our own
frames: we have been routing a relabeling as a mechanism change.** An identity-keyed atom
from level N cannot apply at level N+1 in these games — not because the mechanism changed
but because the label did. This is plausibly a large slice of the 65% rederivation bill:
**in recolouring games, knowledge dies at every level-up because its key is a label the
level-up rotates.** It is BROKEN·rebinding (world remapped, knowledge intact) being paid
for as BROKEN·mechanism — the exact conflation the rebinding bin exists to prevent, one
axis over (colour instead of position).

## Q3 · The cost of colour-relation keying

- **As a SECOND signature with fallback (cheap, stage-2-sized):** canonical form = relabel
  each patch's colours in first-occurrence order; two atoms equal up to permutation share a
  canonical key. The write-site work is already half-done (`colour_delta` at mint; the
  applicability index writes signatures at the same site). Application under permutation:
  infer π from the context match, transport the result through π; for the introduces-34%,
  `colour_delta` supplies the anchor. All gateable by the W2a-2 pattern — scalar/identity
  path as the oracle, equivalence absolute where π = identity.
- **As PRIMARY keying (expensive):** a matcher refactor touching effects, mint, and the
  index — not justified before the fallback proves value.
- **THE FALSIFIER ALREADY EXISTS IN OUR DATA:** replay cn04's level-N atoms against its
  recorded level-N+1 frames under inferred π. If transported atoms apply and predict, the
  rederivation tax was a naming-convention tax, and the read's claim is proven on recorded
  frames before anything ships. If they do not, colour identity was load-bearing and the
  index's current pruning stands as-is.

## Verdict
**Colour identity is the wrong sole invariant.** The game authors' own levels rotate labels
mid-game (Q2), the mint already computes the invariant fact and discards it unread (Q1),
and the cheap path to repair is a fallback signature plus π-transport gated by a replay
falsifier that costs one script (Q3). Recommended order: the replay falsifier FIRST (a
read), then the fallback signature as stage 2's opening move if it fires — displacing, not
joining, the diff-directed selection as stage 2's lead, since a transported atom changes
WHICH candidates exist before any question of how to order them.
