# HISTORY TRACE (2026-08-17) — the three genera across Tabula Rasa + Ouroboros v1-v4

METHOD: two era-blind instruments applied identically to every era tip, so RATES are
comparable (absolute counts carry constant false positives). Storage: CREATE TABLE names
vs writers/readers in the same tree — no writer = G1, writer-no-reader = G3. Organs:
top-level production classes referenced zero times as a token in any other production
file = G2. Trees extracted read-only via git archive.

## 1. THE RATE DID NOT MOVE

                        G2 (no prod caller)   G1 tables   G3 storage
  TR      2025-09-13         84/184  46%          n/a         n/a
  O-v1    2025-12-30         52/144  36%         35  19%     29  15%
  O-v2    2026-01-29         85/206  41%         51  20%     36  14%
  O-v3    2026-02-16        254/580  44%        113  39%     30  10%
  O-v4    2026-08-10        253/583  43%        113  38%     31  11%
  NEW-HORSE (fresh root)     30/114  26%          n/a         n/a
  R-port  2026-08-16        478/834  57%        113  38%     30  10%
  R-instr 2026-08-17        479/836  57%        113  38%     30  10%

G1 HAS BEEN 113 TABLES SINCE 2026-02-16 — identical through the v4 split, the competition
branch, the port, and the registry install. ~500 commits, 183 days, ZERO new instances and
ZERO repairs. G3-storage identical at 30-31 the whole way. THE INSTRUMENT ERA MOVED
NEITHER NUMBER BY ONE. G2 is 57% on BOTH SIDES of the registry install, and
built-and-tested-but-uncalled went 72 -> 74 ACROSS THE INSTRUMENT COMMITS THEMSELVES.

THE ONLY LEVER THAT EVER MOVED THE RATE: NEW-HORSE at 26% — a fresh root with more test
files (112) than production files (98) — abandoned 2026-08-04 for outcome reasons
unrelated to defect rate.

## 2. THE LARGEST DEFECT-CREATION EVENT IN THE RECORD

a29cb28, 2026-02-01, "Provenance Tracking & Resonance Detection Implementation":
-250 INSERT INTO statements, +36, while the schema HELD AT 253 TABLES. 55 tables lost
their only writer in ONE COMMIT and the schema was left standing. Still G1 today (197 d).
G1 MASS-MANUFACTURED BY REFACTOR.

## 3. TIME-TO-DETECTION IS BIMODAL BY GENUS, NOT BY ERA

G2 inside the instrument's scope: 14 of 15 finds were organs BORN INSIDE THE INSTRUMENT'S
OWN 6-DAY WINDOW (0-6 d latency). EXACTLY ONE pre-existing organ was ever caught:
symbolic-gameplay, introduced 2025-12-02, detected 2026-08-16 — 257 DAYS. The tight
cluster is a property of the DENOMINATOR, not of detection power.

G1/G3 storage — ALL STILL UNDETECTED AT HEAD:

  claude_memory         declared 2025-10-19, NO INSERT HAS EVER EXISTED IN THE BRANCH  303 d
  visual_primitives     2025-10-29, writer never written                               293 d
  knowledge_graph_edges 2025-11-01, writer never written                               290 d
  causal_chains / action_effects / object_tracks, writer removed 2025-12-06            254 d
  the 55 severed by a29cb28                                                            197 d
  33 tables G1 at the v1 tip and still G1                                            >=231 d

## 4. THE INSTRUMENT FOR CODE-NEVER-CALLED IS ITSELF CODE-NEVER-CALLED

manual_tools/audit_orphaned_systems.py — a G2 detector built 2026-02-03 (a06bb61, "Wire
11 orphaned engines"), 15.7 KB, TOUCHED EXACTLY ONCE IN ITS LIFE: the commit that created
it. Present at HEAD, referenced by nothing but itself. Its report
architecture/ORPHANED_SYSTEMS_AUDIT.md last touched 2026-02-17, never consulted again.
G2 for 195 days; its output G3 for 195 days.

AND "WIRE THE ORPHANS" HAS BEEN SOLVED TWICE, SIX MONTHS APART, WITH THE SAME COUNT:
2026-02-03 "Wire 11 orphaned engines" -> 2026-08-16 "11 severed organs behind green
tests". ELEVEN, TWICE. The second sweep did not know the first auditor existed.

## 5. VERIFIED BY SEAT 2 DIRECTLY — THE CI GATE IS NOT A CI GATE

.github/workflows/ci.yml, read at HEAD:

  - header says "CI workflow for BitterTruth-AI" — INHERITED BOILERPLATE, WRONG PROJECT
  - on: push/pull_request branches: [main, master] — ALL WORK HAS BEEN ON v4-cold
  - line 59: pytest tests/ ... || echo "Some tests failed (non-blocking for now)"
  - lines 60, 65: continue-on-error: true
  - line 54: --exclude "deprecated/,tests/,manual_tools/" — EXCLUDES THE ORPHAN AUDITOR
  - invokes tests/gate/test_wiring_registry.py: NEVER. tools/live_coverage_diff.py: NEVER
  - LAST TOUCHED 2026-02-01 BY a29cb28 — THE SAME COMMIT THAT MANUFACTURED THE 55 G1
    TABLES. 197 days untouched.

SO: on a branch nobody works on, with every check non-blocking, excluding the directory
that holds the dead-code auditor, never invoking either instrument this project built.

## 6. SEAT 2 RETRACTION (owed, and the genus is mine)

THE_LADDER rung 0c has said "registry + CI GATE + coverage diff" since I wrote it.
THERE IS NO CI GATE. tests/gate/test_wiring_registry.py is a LOCAL pytest file that no
automation runs. I named GREEN-AND-INERT as a genus and then shipped an instance of it as
my own rung: a gate that passes locally, is never enforced, and whose passing I have been
citing as evidence of wiring health. Rung 0c is downgraded to "registry + LOCAL gate +
coverage diff (MANUAL)" until enforcement exists.

## 7. THE NUMBER TO WATCH IS THE SCOPE RATIO, NOT THE CENSUS

Verified at HEAD by Seat 2: WIRING_REGISTRY.md carries 74 status rows (48 LIVE,
24 SEVERED, 1 DELETED-PENDING, 1 INSTRUMENT). Production classes in the core tree
(engines/ + cognitive_loop.py + cognitive_game_player.py + tools/): 416.

  ORGAN COVERAGE:   74 / 416 = 17.8%   (read C's repo-wide denominator 836 => 8.9%)
  STORAGE COVERAGE:  0 / 281 tables = 0.0%

A 27% severed rate measured inside a ~9-18% window CANNOT move a 57% repo-wide rate, and
it did not. THE INSTRUMENTS ARE NOT COSMETIC — THEY ARE CORRECTLY BUILT AND UNDER-SCOPED,
WHICH PRODUCES THE SAME OBSERVABLE AS COSMETIC: A FLAT RATE.

## 8. A FOURTH GENUS THE THREE DO NOT COVER

Measurement-layer defects are at least as frequent as organ-layer defects: "THE SHADOW
TOOL WAS BROKEN A THIRD TIME" (2026-08-06), "I KILLED A BUILDER ON A BROKEN MEASUREMENT"
(2026-08-07), "the rule was right, MY INSTRUMENT WAS WRONG" (2026-08-09), "marked failed
ON THE WRONG INSTRUMENT" (2026-08-07), "THE REPO SHADOWS THE API: a repo-root probe
measures a different game" (2026-08-09). ~14 explicit retractions in Aug 2026, and in most
THE INSTRUMENT WAS THE DEFECT, NOT THE CLAIM. G1/G2/G3 are all defects in the SUBJECT;
this genus is a defect in the OBSERVER, and nothing in the ladder tests for it.

## 9. THE PERENNIAL: COMPACTION/GC, TEN ATTEMPTS, FOUR ERAS, NINE MONTHS

2025-11-01 -> 2025-11-13 -> 2026-01-21 -> 2026-02-06 -> 2026-02-24 -> 2026-08-09 ->
2026-08-12 -> 2026-08-13 (x3) -> and the verdict on 2026-08-16 AND AGAIN 2026-08-17 is
STILL "janitor never ran", now with a 370k-record backlog as the consequence.

## 10. RULED OUT — DO NOT RE-PROPOSE (each killed with a stated reason)

sequence recombination (2026-01-03 "dead code") | CODS (2026-01-31) | startup DB cleanup
(2026-01-21, still off) | safe_cleanup zero-score deletion (2026-02-24, "score is the
wrong deletion key") | grid-scan (2026-03-25, "invalid coords") | untried_first
(2026-07-30) | THE ENTIRE FROM-SCRATCH REWRITE (2026-08-04, "the composer never once
minted a word"; sealed 2026-08-07 "RANDOM CLEARS 7, THE AGENT CLEARS 3") | survival veto
(2026-08-06, "it costs a level") | transplant 4 / memory (2026-08-09, "MEMORY UNSEATED AN
EARN") | the widening (2026-08-09, "FAILED ITS OWN FALSIFIER") | richest-is-best
(2026-08-09) | the death book (2026-08-10, "clock deaths assign false blame") |
proactive-reset port (2026-08-12) | Marketplace (2026-08-12, iced BY DESIGN, "bets drive
nothing") | mkboard silent-delete (2026-08-07).

NOTE FOR THE BOARD AUDIT: "the death book — clock deaths assign false blame" was
retracted 2026-08-10, BEFORE the clock in column 63 was ever seen. That lever was killed
on a mechanism this project had not yet observed.
