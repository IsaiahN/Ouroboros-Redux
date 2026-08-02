# Nexus — the two halves + the proposer, wired

Nexus brings together, on one branch, the two halves of Ouroboros the synthesis paper describes as
"one architecture viewed from opposite ends of the telescope," plus the grammar-fluent proposer:

- **Egocentric half (the kernel)** — already in this repo at `src/newhorse/` (the branch is cut from
  `redux-triality`). The typed predicate DSL Γ, the mint/guards, and the **live ARC-AGI-3 harness**
  (`live_run.py`, `arc3_env.py`). Nexus does not reimplement it; it *uses* it.
- **Allocentric half (the population)** — `nexus/population/`: role specialization
  (Pioneer/Optimizer/Generalist/Exploiter with Table-6 `w_i`), a credibility-weighted shared database,
  and a market arbiter (propose→vote→resolve, covariance-discounted). A clean reimplementation of
  Ouroboros-v4's *design*, not a port of its internals (per `claude/FINDINGS_syncing_the_two_halves...`).
- **The membrane** — `nexus/membrane/`: the only coupling. Promote-up (ECHO / cross-role recurrence
  into shared Γ), seed-down (α/`w_i` prior descended to individuals, with forward-projection
  generalizations), and the policy-vs-playback crossing rule.
- **The proposer** — `nexus/proposer/`: the propose leg. Type-directed enumeration
  (`enumerate.py`) and the fluent tiny-LM form (`fluent.py`, esp32-ai's TinyLM over Γ) — the built,
  measured proposer from `claude/FINDINGS_stage1_grammar_fluent_proposer_built.md`.
- **The ground** — `nexus/ground/`: `SyntheticGround` (offline, verifiable, unpersuadable — scaffolding
  so the loop runs and is testable) and `LiveArcGround` (**the real gate**, delegating to the kernel's
  live harness).

## What RUNS today (offline, no key)

    python3.12 -m nexus.run_nexus       # the two-scale loop over a synthetic curriculum (a SMOKE TEST)
    python3.12 -m pytest nexus/tests -q # membrane / ground / market / kernel-bridge / live-reach

`run_nexus` is a **smoke test**: it proves the four layers are wired and the loop executes
end-to-end (propose → kernel type-check → ground score → market → membrane promote/seed). The
synthetic ground is scaffolding; its numbers are **not** a result and are deliberately not tuned to
look good — that would be the elaboration trap the whole project warns against.

`test_live_reach` drives the kernel's real `run_live` loop against a FakeSession, proving the
Nexus → kernel → live-gate path works with **no key and no network**.

## The real test (next step): ARC-AGI-3 live public set

    export ARC_API_KEY="..."                 # env-only, never written to disk/commit
    python3.12 -m nexus.live_test GAME_ID [GAME_ID ...]

The only metric that counts is `levels_completed` on the live public set (paper §16.7). That run is
the validation step, done next. **No live result is claimed in this branch** — a firing is a receipt,
not a claim.

## Honest status

Wired and running offline: kernel bridge, proposer (enumeration + fluent), membrane, population,
market, synthetic ground, and a tested reach into the live harness. **Not yet done, on purpose:**
(1) a live public-set run (needs key + sweep); (2) feeding the proposer's Γ candidates into the live
`AgentLoop`'s policy (the loop currently drives movers via the kernel's own selection — the proposer
is integrated into the offline market loop, and its hand-off to the live policy is the next wire);
(3) the stage-2 usefulness fine-tune of the proposer from verified mints. The design and provenance
live in the project docs `FINDINGS_syncing_the_two_halves_into_ouroboros_tether`,
`DESIGN_the_grammar_fluent_proposer`, and `FINDINGS_stage1_grammar_fluent_proposer_built`.
