# THE DEFINITION OF DONE (2026-08-18) — binding on every builder brief

## WHY THIS EXISTS

Three things compound, and together they are the whole problem:

1. **The task is scoped to what was asked, and the wire lives in another file nobody
   named.** A brief that says "build X" gets X, correctly, unwired.
2. **Local success criteria are fully satisfiable.** Tests green, ruff clean, diff clean —
   all true, all simultaneously true of a severed organ.
3. **Eleven organs can now be produced in the time it used to take to produce one.**

Same failure rate, much bigger denominator. **IT FEELS LIKE A NEW PROBLEM AND IT IS THE
OLD ONE AT SPEED.** The fix is not more care — the one thing that reliably fails at this
volume is anyone remembering. So it is enforced mechanically, at ship time.

## THIS IS THE AGENT'S PROBLEM, ONE LEVEL UP

The agent's defect is that its organs do not consume each other's output. This build's
defect is that its organs do not consume each other's output. **Same genus, two scales.**
And the instruments that catch it are the same shape at both: a convention that names the
expectation, and a check that can fire when it is violated. That is why this arrangement
has value independently of whether the agent ever clears a level — it is a working answer
to how to build reliably at LLM speed, and no counter grades that.

## THE THREE CLAUSES — every brief carries all three, no exceptions

**1 · A LIVE-PATH RECEIPT THAT SURVIVES REACHABILITY.**
   Not a symbol reference. Not an import. Not "the test calls it." A `file:line` on a path
   REACHABLE FROM THE LOOP ENTRY, demonstrated by the coverage diff in operator mode.
   THE CURRENT GATE ASSERTS REFERENCE, NOT REACHABILITY — that is the open gap, and until
   the operator-mode coverage read lands, every LIVE row in WIRING_REGISTRY.md is a claim
   about references rather than about execution.

**2 · A NAMED CONSUMER WHOSE BEHAVIOUR CHANGES.**
   Not merely a reader. **Not an abort path.** Rung 0d's clause: a stream read only to
   STOP the agent satisfies naive writer-reader pairing while exhibiting exactly the
   pathology. The brief must name what DECISION comes out different, and the builder must
   show it coming out different.

**3 · A CONTRACT OR PROPERTY TEST AT THE SEAM.**
   The value crossing the boundary is ASSERTED, not assumed. This is the only clause that
   catches the override class — a literal passed to a live function on a reachable path is
   legal, and every static tool, every coverage run, and every dead-code linter passes it.
   The sole defence is someone having stated what the value should be.

## WHAT THE TOOLS DO AND DO NOT REACH (stated so no one buys a linter and stops)

REACHED:
  - static call graph from the loop entry (pycg/pyan) -> never-called, cleanly
  - `coverage.py --branch` on a REAL episode -> constructed-but-never-executed branches,
    dead conditionals, organs whose only caller is itself dead
  - **run both and diff. REACHABLE-STATICALLY-BUT-NEVER-EXECUTED IS THE INTERESTING BIN.**
  - vulture configured to ignore re-exports (the blind spot that hid sequence_miner)
  - tools/consumption_sweep.py — the writer-reader AST pass (rung 0d)

NOT REACHED BY ANY OF THEM:
  - **THE OVERRIDE.** A constant passed to a live function on a reachable path is legal.
    Only a contract or property test catches it — clause 3, and it is not a tool question.
  - **DRIFT.** Correct when written, invalidated by a change elsewhere, still well-formed.
    `level_breakpoints` is the specimen: the machinery to prevent it was built in full,
    re-exported, and never called.

## THE INSTRUMENT RULE (earned 2026-08-18, and it is now standing)

**A NEW INSTRUMENT'S FIRST OUTPUT IS A CLAIM ABOUT THE INSTRUMENT, NOT ABOUT THE SYSTEM.**
The consumption sweep's first run reported 130 unpaired streams/tables. **101 of the 130
were regex artifacts** — `FROM`, `INTEGER`, `SET` counted as table names. Caught by
checking before publishing; 130 would have propagated for weeks and been cited as a
census. That is the fourth genus — a defect in the OBSERVER — nearly committed by the
tool built to catch defects in the subject.
COROLLARY: **a measurement nobody can distinguish from a null result must be reported as
NOT IMPLEMENTED, never as a number.** The sweep's abort/decide classifier returns 0 on a
system with two hand-identified abort-only consumers. It now prints NOT IMPLEMENTED,
because a printed `0` becomes a clean bill within a week.

## ORDER OF WORK (queued behind the control arm — none of this says whether the
## architecture beats what it replaced)

  R1 · COVERAGE DIFF IN OPERATOR MODE against a real episode.
       DETERMINES WHETHER THE LAST MONTH'S LIVE COUNTS MEAN ANYTHING. Everything waits on
       it. **HELD, WITH A REASON: it requires running a real episode, and the control arm
       is measuring LEVELS PER HOUR on a 4-core box where load was already measured to
       vary 20x. Adding an episode now would corrupt a pre-registered reading of the one
       experiment that outranks this work.** It runs the hour the arm finishes.
  B1 · icontract at THE FOUR SEAMS THAT HAVE ALREADY FAILED — not repo-wide:
       planner budget, consumer drain, replay scope, wheel verification.
  B2 · These three clauses into the brief template, applied without anyone remembering.
