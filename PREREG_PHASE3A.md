# PRE-REGISTRATION — PHASE 3a: the fabric, the mint, and the seed channel

**Written 2026-08-10 BEFORE the build, on `v4-cold` at `671771b`. Baseline: 6 games L1, ZERO
L2. Phases 1–2 passed all falsifiers. Design: `PHASE3_DESIGN.md`.**

## 1. THE CHANGE THAT IS AUTHORISED

> `engines/egocentric/fabric.py` (pure stdlib; scoped JSONL streams; seed-overlay; the idea
> economy: mint/echo/falsify/credibility/priors/reputation per the design doc). Verbatim port of
> `falsified_ledger.py` (present/importable; full consumption is 3a-lite: the falsify path).
> Wiring, all inside the existing EGO blocks: (a) **MINT on signal only** — when `credit()`
> fires (real level-up), mint the confirmed goal + the established delta map to personal AND
> collective scopes (`[EGO-MINT]` logged); (b) **SEED at first observation** — load
> `priors(game)` and feed candidate goals into the spine at inherited (reduced) price; an
> inherited confirmation MAY open the drive gate (flagged-for-veto rule, design §4);
> (c) **ECHO** — a level-up while pursuing a seeded idea echoes it (origin reputation up);
> (d) **FALSIFY** — a seeded-confirmed goal reached without reward is falsified to pariah and
> loses its inherited confirmation immediately (drive gate closes back).

**HARD CONSTRAINTS:** stdlib-only fabric; deterministic (sequence numbers, injectable clock,
no wall-time in defaults); every fabric/economy failure swallowed to counters; the fabric root
for live runs is `ego_fabric/` under the working directory (hermetic boxes get their own —
isolation preserved); EMPTY fabric ⇒ byte-inert (the containment property).

## 2. THE GATE — binding

1. **TESTS FIRST, SHOWN TO FAIL:** fabric CRUD + scopes + overlay read-only + corrupt-tail
   tolerance + determinism; economy semantics (mint requires signal context; echo raises
   credibility AND origin reputation; falsify pariah-ranks; priors order: credibility desc,
   personal>kin>collective on ties, pariahs last); wiring scans (mint only inside the credit
   path; seed at init; falsify on reached-without-reward; `[EGO-MINT]`/`[EGO-SEED]` logs).
2. **⭐ FALSIFIER (containment):** with an EMPTY fabric, the four stored control shas reproduce
   byte-identically. Any drift → memory acted without signal → revert.
3. **⭐ FALSIFIER (consumption):** instrument-side pre-seeded fabric (a confirmed-goal idea per
   game, cells taken from control-run logs, proctor-chosen) — the seeded arm must differ from
   control on ≥2 of 4 movement games AND the run logs must show `[EGO-SEED]` + drive or
   falsify activity. Identical everywhere → the seed channel is decorative → revert.
4. **⭐ FALSIFIER (the pariah loop closes):** in the seeded arm, at least one seeded idea that
   led nowhere must appear falsified in the session fabric (the consumer-first requirement —
   v4's pariah storage had readers=0 forever; this one must WRITE BACK from live play).

## 3. THE UNDO

`git revert` of the Phase-3a commit(s); baseline `671771b`.

## 4. WHAT THIS DOES NOT CLAIM

No L2 claim (that is 3c, after 3b promote/seed runs population-scale). No claim that inherited
ideas are TRUE — only that they are priced, defeasible, and falsifiable by one contrary fact.
