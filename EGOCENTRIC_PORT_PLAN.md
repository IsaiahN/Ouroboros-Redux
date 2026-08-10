# THE EGOCENTRIC PORT — plan for v4-cold

**Written 2026-08-10, on `v4-cold` (stock v4 at `5800f9c`), while the cold run's second 10
generations execute. Status: PLAN ONLY — no agent code has been written. Awaiting Isaiah's
scope confirmation; recon proceeds meanwhile.**

---

## 1. WHAT THE COLD RUN ESTABLISHED (the hole this port fills)

900 episodes, 10 generations: **6 games solved level 1; ZERO reached level 2.** v4 is a
discovery-and-banking machine — population-scale search finds L1s, `winning_sequences` replays
them forever — but each next level is a fresh blind search from a replayed prefix. Breadth
compounds; depth never does. The missing mechanism is *directed* play: knowing what the game
wants and acting toward it. That is precisely the new horse's egocentric loop.

## 2. WHAT THE EGOCENTRIC LAYER ACTUALLY IS (read from `Nexus:src/newhorse/`, ~2k lines total)

`AgentLoop` (392 lines) composes small, swappable bricks — the load-bearing ones for depth:

| brick | module | what it gives v4 |
|---|---|---|
| belief state | `perception.segment` + `ObjectTracker` | objects held steady through change |
| **self-locus** | `SelfLocus` + `CursorAgency` | WHICH object is *me* — identified by action contingency, never assumed |
| goal market | `GoalManager` + `relations` | candidate win-relations (typed + ALL-quantified), **priced by actual reward** — confirmed on level-up via `signal_reward()` |
| directed act | `GridNav` (directed-edge walls) | navigate the self to the priced goal |
| honesty rails | `FalsifiedLedger`, `ResidualBus`, `Pose` | hypotheses die by prediction error; surprise banks; private-vs-social weighting learned |
| discipline | `bounds.py` ResetGate/ResolutionBound | constitutional bounds with no off-switch |

Principle stamped through the code: transforms are GENERIC (identity + unit shifts); which action
causes which transform is discovered by prediction error, never given. No answers encoded.

## 3. PORT SHAPE — three phases, each independently gated, each reversible

**Phase 1 — the self (perception substrate).** Port `perception`/`ObjectTracker` +
`SelfLocus`/`CursorAgency` as a v4 engine (`engines/egocentric/`). Wire read-only first: the
cognitive loop LOGS the identified controllable + its move map every step, changes nothing.
Gate: on ≥4 movement-capable games the identified self-locus tracks the avatar (verified from
per-move logs); zero behaviour diff (seq identity) while read-only.

**Phase 2 — the goal spine.** Port `GoalManager` + `relations` + `GridNav`. Consumer: a new
decision path in the loop — when a goal has POSITIVE confirmed price (a level-up happened while
pursuing it), navigation toward it pre-empts the ordinary choice; otherwise everything is
unchanged (mirror of the market's abstain-by-default). `signal_reward()` wires to v4's
`level_completions` event. Gate: consumption cut-wire (corrupt the nav target → sequence must
change on goal-priced games); containment (byte-identical when the path never fires).

**Phase 3 — depth from replayed prefixes.** The L2 attack: after a banked L1 replay completes,
the egocentric loop takes over the remaining budget with its goal market live. This is where
"breadth machine" becomes "depth machine". Gate: the ONLY scored number — does any game post a
level_completions=2 episode within N generations, judged against the cold baseline of zero in 20.

**Explicitly NOT ported:** the marketplace/economies pricing spine (lives on the iced branch;
re-merge later if wanted), `two_streams` alpha beyond what Pose needs, `budget.py` (v4 has its
own), the redux_arch chart shell (Phase-0 naming only).

## 4. DISCIPLINE CARRIED OVER FROM THE ICED BRANCH

Prereg + falsifier + undo before each phase; tests-fail-first; firewalled builders (predicates,
never games/cells); the hermetic harness gets copied to this branch as proctor tooling when
Phase-1 gating needs it; every number re-derived from raw logs. The iced branch's laws that
transfer: additive-only changes survive trials; evidence-replacing changes died twice; consumers
before producers — build nothing until its consumer's case is measured.

## 5. OPEN QUESTION FOR ISAIAH

Scope: full spine (Phases 1–3) or belief-state/self-locus first and reassess? Phase 1 starts
either way (everything sits on it) — say the word to start, or redirect.

---

## 6. THE TWO-TIMESCALE FUSION (Isaiah's frame, 2026-08-10 — supersedes §3's Phase 3 shape)

v4 = allocentric evolution: variation by random allocation, selection by level-fitness, retention
by banking. The egocentric layer runs THE SAME TRIAD inside one agent at action timescale:
variation = hypothesis proposal from local Γ; selection = the residual settles every action
(dense gradient, not per-life); retention = MDL-guarded MINT into local Γ. One agent's episode
is itself a thousand generations of idea-evolution.

The bank splits into two channels with different transfer laws:
  * `winning_sequences` (playback) — stays; bootstraps every episode to the frontier. Playback
    DOES NOT CROSS levels (the measured L2 wall) and never crosses upward.
  * Γ-promote (generators) — minted φ that were VERIFIED + ECHOED (re-derived on a second
    context) + COMPRESSED cross into the shared library; next generation SEEDS local Γ from it
    as PRIORS (bias proposal order), never as replays.
Bracket residual R_T gates the round trip both ways. Variation inside a generation, selection
between: agents never copy each other's Γ mid-flight — sharing only through the promote gate.
Ground stays pinned: hypotheses are priced against the WORLD's next frame only, never against
each other (the anchor must not update).

Build order follows the dependency chain's measured status (perception/persistent identity
first; the mint fires last and is gated like everything else): Phase 1 self → Phase 2 goal
spine → Phase 3a local ledger+mint → Phase 3b promote/seed channels through v4's existing
transfer machinery → the L2 number against the cold baseline of zero.
