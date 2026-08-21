# F1 VERDICT (2026-08-20): THE SHARE HELD — VECTORISATION IS THE SUCCESSOR, PER THE PRE-COMMITMENT
# + THE METACOGNITIVE SHADOW TEST (Seat 3's check on the routing)

## Part 1 · F1, decided by the rule stated before either run

Same worker (cn04), same 420s dump-on-timer window, before (`d5_profile_cn04.pstats`) vs
after (`d5_profile_cn04_AFTER.pstats`):

| term | before | after |
|---|---|---|
| `apply_effect` cumulative share | 95.3% | **92.5% — HELD** |
| applications per planner call | ~9,483 | ~5,017 (halved — the filter prunes ~47%) |
| loop cycles in the window | 10 | **15 (+50% throughput)** |
| planner calls in the window | 5 | **10 (engagement DOUBLED)** |
| numpy `.all()` calls | 77.7M | 73.7M |
| filter cost (`prune_candidates`+`frame_signature`) | — | **0.2% (F4: the index is honest about its cost)** |

**VERDICT: F1 fails by its letter — the share did not collapse.** The pre-committed losing
condition fires exactly as written: *the cost is per-application work* — ~4ms and ~1,450
numpy `.all()` calls **inside each** `apply_effect` (the anchor scan), so halving the
candidate count halves per-call time without touching the share. **The successor is
VECTORISATION of the anchor scan**, named before the run so this result cannot be rescued
into a success. The index stays (real: throughput +50%, per-call cost halved, superset-safe)
— it is necessary and insufficient.

**The reabsorption finding, unlooked-for:** the freed time was immediately consumed by MORE
planner calls (5→10). Under engage-on-atoms, any capacity the index frees is spent
re-running the search that still returns nothing. **W2b (planner-as-last-resort) is not an
optimisation — it is the only thing that stops every future speedup from being eaten by the
same consumer.** Empirical, from the window.

**Row 3 settled by the same window** (Seat 4's check): `to_dict` — 225 calls, 0.0s
cumulative. The context dict's ~free is now a **measurement**, not a guess wearing one's
clothes. The unmeasured cluster (rows 2, 4, 13, 14) remains the map's to-do.

## Part 2 · The shadow test — does each category predict a residual the bins cannot express?

Per Seat 3: a check on the routing, not an install.

| category | current expression | shadow verdict |
|---|---|---|
| **Forming** (wrong model, right problem) | BROKEN·mechanism (residual from a known atom) | expressible |
| **Assumption** (right model, wrong problem) | BROKEN·rebinding (world remapped, knowledge intact) | expressible — the discriminator retention is W4 |
| **Dislodging** | **NOT EXPRESSIBLE.** The bins route new evidence; **no route DEMOTES standing knowledge.** Γ only grows; nothing retires an atom whose predictions keep failing. The predicted residual — *this atom keeps being wrong and still ranks* — has no bin because bins classify events, and this is a standing. | **GAP 1: eviction. And it is `standing_half_life` AT THE ATOM GRAIN** — Seat 3's network decay ruling applied to Γ itself. One mechanism, two grains. |
| **Location** (lost in the process) | the ordering rule + W1 narration (PLAN g-gates name where the agent stopped; bet-before-act IS knowing where you are) | expressible post-W1 |
| **Achievement** (persisting in what isn't working) | **NOT EXPRESSIBLE.** A bin classifies ONE residual; this is a TREND — the same failure repeated with no route change. The replay corpse and L1 hardening are both instances. | **GAP 2: a persistence monitor** — repeated-identical-residual with unchanged strategy is a fact no single-event bin can state. Needs a counter over narration (which now exists to count over), not a fifth bin. |
| **Progression** (behind but confident) | the frame-internal-metrics rule + the mastery gate (confidence priced by regeneration, not self-report) | expressible at the membrane |
| **Interruption** → plan disruption | **HALF-EXPRESSIBLE.** W2b's state-key condition detects THAT the world changed, but on a mid-plan abort nothing routes the abort: *world moved* (state changed under the plan → re-plan, do not penalise the plan) vs *plan wrong* (state as predicted, step failed → penalise). The rebinding conflation one layer up, as both seats said. | **W2b RIDER: route the abort.** One discriminator, same shape as the rebinding fix. Added to PREREG_W2B. |
| **Mislead** (led down the wrong path by a tool) | [COL] provenance tags + narration make a wrong import traceable to its source; the debit prices it | expressible post-W1/W2 |

**Net: two gaps and one rider, all about REMOVAL rather than addition** — eviction
(standing_half_life at atom grain), persistence (a monitor over narration), and abort
routing (a discriminator in W2b). Nothing needs a new bin; the four bins survive the shadow
test. The gaps go to Seat 3 as proposals, not installs.

## Map amendment (Seat 4's column, stated compactly)
Cost alone does not rank the rows — **cost × contribution** does. Three rows currently have
measured cost and **no known contribution**: row 9 (was 95%, returns nothing — the extreme),
row 5 (startup tail, forbidden by the ladder), row 3's 55 unread keys (build cost now
measured ~0; their *maintenance* cost is in code, not cycles). Row 7 is the inverse anchor:
cheap and load-bearing. The absent-column reading goes row by row as each unmeasured cell
gets its number.


---

# F2 ADDENDUM (2026-08-20, the third window): THE SHARE HELD AGAIN — SEARCH BREADTH IS THE COST

| | window 1 (baseline) | window 2 (index) | window 3 (vectorised) |
|---|---|---|---|
| `apply_effect` share | 95.3% | 92.5% | **87.7% — HELD** |
| `apply_effect` calls | 47,418 | 50,721 | **141,330 (2.8×)** |
| loop cycles | 10 | 15 | **22** |
| planner calls | 5 | 10 | **17** |
| total function calls | 240M | 231M | **21M** (the `.all()` storm gone) |

**The reabsorption law, now measured three times:** every per-call speedup is spent on more
calls and more breadth. Applications per planner call went 9.5k → 5.0k → **8.3k** — the
search widened back into the freed budget. The share is a ratio, and a consumer that
expands to fill capacity holds its ratio at any per-call speed. Meanwhile the absolute
numbers ARE better: cycles per window more than doubled across the three windows (10→22),
which the swarm inherits at HOLD-lift.

**Per the double pre-commitment (named before window 2 ran): no further micro-optimisation.
The fix is W2b (the planner engages as last resort) + stage-2 candidate selection** — for
which the colour read now proposes the relational signature as lead, pending the π-replay
falsifier. W2b's brief is pinned and dispatched; stage-2 waits on the π-replay read per
Seat 3's "answer before stage 2".


---

# WINDOW FOUR (2026-08-20, post-W2b): THE SHARE COLLAPSED — AND THE GENERATION FINISHED

| | w1 (base) | w2 (index) | w3 (vector) | **w4 (scheduled)** |
|---|---|---|---|---|
| `apply_effect` share | 95.3% | 92.5% | 87.7% | **27.0%** |
| planner calls | 5 | 10 | 17 | **4** |
| loop cycles | 10 | 15 | 22 | **75** |
| window used | 420s (killed) | 420s (killed) | 420s (killed) | **56s — RAN OUT OF GENERATION** |

**W2b's F1 PASSES.** Engagement fell from 77% of cycles (17/22) to **5% (4/75)** — the gates
bound the planner instead of the planner absorbing the budget. The reabsorption law did not
hold this window **because W2b is the thing built to break it**, and it did.

**The milestone under the numbers: cn04 — the slowest worker in the fleet, 0.1 actions/min
at the baseline — completed a FULL GENERATION in 56 seconds.** Windows one through three
could not finish inside 420s at all; the measurement that was obstructed by the thing it
measured now has 6.5× headroom. Cycle throughput vs window three: ~25×.

**And the map's prediction fired on schedule:** with row 9 shrunk, the unmeasured cluster
surfaced — `decision_rung_system.decide` is now visible at 19.7% (75 calls), the next
largest term after the (now bounded) planner. The 32-engine/rung decomposition read is no
longer a blind spot on a map; it is the next number in the profile.

Composition note: four builds each did their stated job — index pruned safely, vectorisation
cut per-application cost ~29×, scheduling bounded engagement — and the fifth (extent premium)
now gates what enters Γ going forward. The remaining planner cost per call (~5.9s cum) is
still the search-that-returns-nothing; it is now RARE instead of constant, and the re-point
build (coarse-signature intersection) is what makes it fertile instead of empty.

---

# WINDOW FIVE (2026-08-21, g50t, composer stages 1-3 live): THE SIXTH LAYER IS I/O
Generation finished in 90s. The planner is absent from the top. record_result 29.9% ←
fabric._read_stream 28.0% (556 calls / 130 cycles — whole-stream re-parse ~4× per cycle via
fabric.query) + sqlite execute 17.5% (4,601 calls ≈ 35/cycle); seed_imports 13.6% (one-time);
decide 12.4% (was 19.7%). **Produced-once, parsed-many — the week's genus at the storage
layer.** Fix shape (a prereg, no semantics): incremental tail reads with a parsed-stream
cache keyed by file position; batched per-step DB writes. The 32-engine decomposition read
is answered by elimination: the engines are not the next term; the fabric reads are.

## WINDOW SIX-a (ar25, b10bc12): INCONCLUSIVE — 2 cycles in 108s; startup-dominated
Not a steady-state read: imports 21.8%, `system_diagnostic._bottleneck_systems` 21.5% (a
~23s diagnostics pass at EVERY worker boot — ×25 workers ≈ 10 CPU-minutes per fleet
restart; a startup term nobody had named; is its output read? queued as a consumer check),
sqlite 24.4%. W2b's _w2b_engage fired once in two cycles — unjudgeable. Rerun on g50t
(window 6-b) for comparability with window five.

## WINDOW SIX-b (g50t, b10bc12, full fleet, 130 cycles / 397s): TWO VERDICTS
**W2b's leak-stop HOLDS under multi-cycle drive**: _w2b_engage 4 calls in 130 cycles (3%);
stage 4's continuation did not reopen the leak. F1 re-confirmed on the run's own code.
**The I/O layer, precisely**: record_result 36.9% ← fabric._read_stream 32.3% (572 calls)
AND fabric.append 30.7% → **_next_seq 28.3%: every append re-reads and re-parses the whole
stream to compute the next sequence number** — 1,220 appends → 1.5M json.loads. Plus
sqlite commit 20.0% (1,328 commits, one per write). The write path's most basic operation
re-parses the file it is about to extend. THIS IS THE FABRIC-I/O BUILD'S BEFORE-NUMBER:
reads 32.3 + _next_seq 28.3 + commits 20.0.
