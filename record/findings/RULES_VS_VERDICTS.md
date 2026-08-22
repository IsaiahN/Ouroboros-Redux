# RULES vs VERDICTS (2026-08-18) — converting the board so Seat 3 is not the rate limit

ISAIAH'S FRAMING, ADOPTED VERBATIM AS THE TEST:
  A VERDICT is one where the outcome depends on THE GROUND, THE REGISTER, or WHAT IS AT
  STAKE. Those stay with Seat 3.
  A DECISION THAT FOLLOWS FROM A CRITERION THAT COULD BE WRITTEN DOWN ONCE should become
  a criterion.
Every proposed rule below carries a VIOLATION DETECTOR, same standard as any convention.
A rule without a detector is a preference, and preferences are how this drifts back.

TALLY: 12 held items. **7 CONVERT TO RULES. 5 STAY VERDICTS.** The 7 cover ~57 individual
dispositions (the 29 unpaired + 24 severed rows + 4 singles), because most of the board's
BULK was one criterion applied 53 times.

---

## R1 · ORPHAN DISPOSITION — the big one (covers 53 items)
ISAIAH PROPOSED THE SHAPE; ADOPTED WITH ONE ADDITION.

  RULE: For any organ or stream currently SEVERED or UNPAIRED:
    - live-path receipt (reachability, not reference) AND a consumer whose BEHAVIOUR
      CHANGES (not an abort path)          -> WIRE. No ruling.
    - NEITHER                              -> DELETE. No ruling.
    - EXACTLY ONE OF THE TWO               -> RULING. Goes to Seat 3.
  THE ADDITION: a fourth case the three miss. If the organ is the ONLY IMPLEMENTATION OF A
  DISTINCTION NOTHING ELSE EXPRESSES -> RULING regardless of receipts. sequence_miner is
  the specimen: no receipt, no consumer, so the rule says DELETE — and deleting it would
  destroy the only code in the repository that can express level-scoping, which is the
  defect it was built to prevent. Deletion must not be able to consume the cure.

  VIOLATION DETECTOR: tools/consumption_sweep.py --strict (now CI-blocking). Any new
  unpaired stream/table fails the build. Any item removed from the baseline without a
  corresponding WIRE or DELETE in the registry fails the ratchet's stale check.

## R2 · GROUND-TRUTH CORRECTIONS — ships under the standard gate
  RULE: A change whose sole effect is to make a recorded value AGREE WITH AN OBSERVATION
  THE SYSTEM ALREADY RECEIVED — where the current value is DEMONSTRABLY FALSE against
  that observation — is a CORRECTION and needs no ruling.
  COVERS: cognitive_game_player.py:337 (`levels_completed = getattr(...) or prev_levels`
  restores a stale 2 when GAME_OVER honestly reports 0; the board says dead, the loop says
  alive on level 2 with 132 actions left).
  VIOLATION DETECTOR: the fix MUST ship with a test that asserts against THE OBSERVATION
  (`_sobs.state`), not against our model of it, and that FAILS BEFORE / PASSES AFTER. A
  correction whose test asserts our own expected number is not a correction; it is a
  re-statement, and it fails this rule.
  BOUNDARY (this is what keeps R2 from swallowing R6): if the change can make a previously
  INFEASIBLE option FEASIBLE, or vice versa, it is NOT a correction. It is a behaviour
  change and it goes to R6/verdict.

## R3 · BEHAVIOUR-PRESERVING PERFORMANCE — ships as an optimization
  RULE: A change that produces BYTE-IDENTICAL OUTPUT to the code it replaces ships without
  a ruling, however large the speedup.
  COVERS: affect.py:54-58 (full-file read -> tail read; the returned last-20 records are
  the same records), object_detector.py:37 (a relative db_path default that relocates a
  file, touching no decision).
  VIOLATION DETECTOR: the ablation clause already in record/canon/CLAIM.md — an OFF-ARM test, PASSING
  AT SHIP, asserting the new path equals a LITERAL pre-fix computation on live-shaped
  data. This is the exact pattern G23 shipped under; it is proven and costs one test.
  NOTE: this rule covers the READ. It does NOT cover the janitor (see V2) — the coupling
  Isaiah identified is real, but it is a coupling of ECONOMICS, not of correctness, and
  economics is allocation.

## R4 · INSTRUMENT HONESTY — no ruling, and it is mandatory rather than permitted
  RULE: An instrument that CANNOT DISTINGUISH ITS RESULT FROM A NULL RESULT must report
  NOT IMPLEMENTED, never a number. A new instrument's FIRST OUTPUT IS A CLAIM ABOUT THE
  INSTRUMENT, not about the system, and must be checked as such before publication.
  EARNED: 101 of the sweep's first 130 findings were regex artifacts; the abort/decide
  classifier returns 0 on a system with two hand-identified abort-only consumers.
  VIOLATION DETECTOR: any instrument printing a COUNT must have a KNOWN-POSITIVE FIXTURE
  that makes that count nonzero. No fixture -> the count is not printed. Mechanically:
  a gate test per instrument asserting `detector(known_positive) > 0`.

## R5 · CONTRACTS AT NAMED SEAMS — ships in observe-mode without a ruling
  RULE: icontract at a seam WITH A DOCUMENTED PRIOR FAILURE ships in OBSERVE MODE (log the
  violation, do not raise) with no ruling. PROMOTION TO RAISE requires one clean swarm
  cycle with zero observed violations — and that promotion is automatic on the evidence,
  not a ruling.
  COVERS the four named seams: planner budget, consumer drain, replay scope, wheel
  verification. NOT repo-wide — a contract at a seam with no prior failure is speculation.
  WHY OBSERVE-FIRST: a contract that raises on a live worker kills the worker. Shipping
  straight to raise converts an unknown-frequency violation into an unknown-frequency
  outage, which is a new failure mode introduced by the safety measure.
  VIOLATION DETECTOR: the observe-mode log is itself a stream — and it goes on the rung-0d
  sweep like everything else. A contract whose observations nothing reads is the genus.

## R6 · SELF-RESOLVING HOLDS — no ruling needed, only a stated trigger
  RULE: An item held ONLY on resource contention is not a decision; it is a schedule. It
  states its trigger and executes when the trigger fires.
  COVERS: R1 operator-mode coverage diff — held solely because it needs a real episode and
  the control arm is measuring levels-per-hour on a 4-core box. TRIGGER: the arm's third
  delta lands. Executes then, without asking.
  VIOLATION DETECTOR: any item on the held list with no stated trigger and no ruling
  request is mis-filed and must be re-triaged. "Held" with neither is how a board grows.

## R7 · THE STARVATION CHECK — a standing precondition, not a rule about builds
  RULE: BEFORE CONCLUDING A CHANNEL IS STARVED, VERIFY SOMETHING READS IT. From the
  producer's side an empty downstream and an unread stream are IDENTICAL. This project has
  mistaken the second for the first TWICE (salient-bank suppression; the levelup_frames
  corpus "staying at one record").
  VIOLATION DETECTOR: any claim of "starved" about a stream on the sweep's unpaired list is
  automatically rejected. Mechanically checkable — the unpaired list is a file.

---

# WHAT STAYS WITH SEAT 3 — and why each is genuinely a verdict

## V1 · THE CONTROL ARM: duration, and the replay respec
WHY IT CANNOT BE A RULE: it AMENDS A PRE-REGISTRATION MID-FLIGHT. The prereg exists
precisely to stop the person holding the numbers from changing the design once they see
them, and a rule authored by the seat watching the run is that same act with extra steps.
Also genuinely at-stake: whether 2 games is enough to settle three weeks of work.
STANDING NOTE: salient-prefix replay is FULL-ARM-ONLY, so "remove from both sides" is not
an available move; removing it removes part of the treatment.

## V2 · THE JANITOR: offline-only -> online
WHY: it is a DESTRUCTIVE compactor, and promoting it means running deletion against live
books carrying a 370k-record backlog while workers write. R3 covers the read that made
the streams expensive; it does not cover deciding when it is safe to delete. AT STAKE, and
the ground (backlog size, writer liveness) decides it.

## V3 · FRAME RETENTION
WHY: it is a COMPOSITION AND RESOURCE COMMITMENT — what this project keeps forever, at
what storage cost, on a box already measured at 22-32 ms/write. No criterion I can write
decides how much history is worth keeping; that is a judgement about what the work is for.

## V4 · THE PRECONDITION ONTOLOGY
WHY: REGISTER F. It changes the agent's representational commitments — whether the model
can express "this action works only when <gate>". Anything touching Register F stays,
by the seat map's own law.

## V5 · THE BUDGET REGIME (L-1) AND ITS OVERRIDE RIDER
WHY: it CHANGES FEASIBILITY ON EVERY GAME WITH A REAL LIMIT, which SILENTLY MOVES THE
BASELINE THE CONTROL ARM MEASURES AGAINST. Seat 4 flagged it needs its own falsifier
rather than shipping as a correction, and that is right: it fails R2's boundary clause
explicitly, because it can make previously-infeasible options feasible. Additionally it is
the first Register L estimator and sets the pattern for the other six.

---

## THE RESIDUAL RISK, NAMED
These rules move ~57 dispositions off Seat 3's board. THE FAILURE MODE THEY INTRODUCE is
that a rule fires on an item it was not written for — R1's DELETE case nearly consuming
sequence_miner is the live example, caught only because the fourth case was added.
MITIGATION, and it is the same standard as everything else: every rule-fired disposition
is RECORDED WITH THE RULE THAT FIRED IT, so a bad rule is auditable in one grep rather
than being invisible in a pile of individually-plausible decisions.

## AMENDMENT — R1's DELETE ARM RETURNS TO SEAT 3 (2026-08-18, Isaiah's ruling)
*"Correct, and I'd take it — it's the one rule-fired action that destroys something, and
the near-miss is the receipt."*
**R1 IS NOW SPLIT.** The WIRE arm stays rule-fired: receipt + consumer whose behaviour
changes -> wire, no ruling, both conditions mechanical. **THE DELETE ARM IS SEAT 3's.**
Neither receipt nor consumer no longer fires a deletion; it produces a RULING REQUEST
carrying both null findings.
**THE RECEIPT FOR THE SPLIT:** R1 as first written would have deleted `sequence_miner` —
the only code in this repository able to express level-scoping, which is the distinction
whose absence caused the replay defect. A rule needing a fourth case on first contact with
a real item is a rule that should not fire irreversibly on its own.
