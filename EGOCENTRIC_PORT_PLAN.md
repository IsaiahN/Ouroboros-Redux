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
