# APPARATUS ITEMS I WOULD HAVE TAKEN — DECISION ANALYSIS FORM (2026-08-18, for Seat 3)

AUTHORITY: Isaiah — *"write up any apparatus item you'd have taken, with its Decision
Analysis form: options developed, musts separated from wants, and the PPA — what breaks if
this works."*

**NONE OF THESE WERE BUILT.** Each is a build I stopped short of because it is apparatus and
the seat was empty. Form is Kepner-Tregoe (1958): **musts eliminate, wants are weighted,
PPA asks what the success itself breaks.**

**THE HAZARD OF THIS FORM, CARRIED RATHER THAN HIDDEN:** the weights below are **declared,
not derived.** A weighted score **ranks** options; it does not settle them. Where a ranking
is close I say so instead of letting two decimal places pretend to decide.

---

# ITEM 1 — THE SHAPE→INSTANCE INDEX
### the instrument the SITE-SCOPED KNOWLEDGE genus implies

**THE PROBLEM, IN ONE LINE.** A defect is a fact about a **shape**; a fix is a fact about a
**line**; nothing maps a shape to its instance set, so the defect count grows by ordinary
authoring while the fix count stays at 1. Receipts today: the correct evidence-guard pattern
authored 2025-12-04 and **not used by D-1 written 54 days later, 561 lines below it in the
same file**; the 08-13 rule and its contradicting verifier **1,575 lines apart for five days**;
the discriminating test helper **168 lines above** the test that needed it.

**MUSTS** (fail any → eliminated)
- M1 Reports **instances-of-shape** and **instances-of-fix** as two numbers, not one verdict.
- M2 Satisfies **R4 both ways** — a pinned known-positive and a pinned known-negative.
- M3 Works **within a tree**, not only across two. The 1,575-line case has no fork in it.
- M4 **Reads only.** No edit, no rewrite, no auto-fix.

| option | M1 | M2 | M3 | M4 | verdict |
|---|---|---|---|---|---|
| **A · Extend `fork_divergence.py` to count within-tree instances** | ✓ | ✓ | ✓ | ✓ | **survives** |
| **B · Structural/AST shape matcher** (find every proxy-keyed DELETE by parse, not text) | ✓ | ✓ | ✓ | ✓ | **survives** |
| **C · A defect register — each defect gets an ID and a hand-maintained instance list** | ✓ | ✗ (a list has no self-check) | ✓ | ✓ | eliminated |
| **D · Require every fix commit to state "where else"** (process, not tooling) | ✗ (produces no count) | ✗ | ✓ | ✓ | eliminated |

**WANTS** (weight ×10 scale, declared)

| want | w | A | B |
|---|---|---|---|
| finds shapes text cannot express (`ORDER BY <proxy>` regardless of column name) | 9 | 3 | **9** |
| cost to build tonight | 8 | **9** | 3 |
| false-positive rate low enough to read by hand | 7 | 6 | **8** |
| extends an instrument already returning something (**INWARD**, not built-from-description) | 8 | **9** | 4 |
| **weighted** | | **211** | **190** |

**RECOMMENDATION: A, and the margin is 211 vs 190 — that is NOT a settled gap.** A wins on
cost and on being INWARD; B wins on the thing that actually matters long-term. **The honest
reading is "A first *because* it is cheap, and it is not an argument that A is better."**

**PPA — WHAT BREAKS IF THIS WORKS**
1. **It will find a lot, and every hit is an accusation.** A sweep that returns 40 instances
   of a proxy-keyed retention turns one ruling (D-1) into forty. **Risk: the board becomes
   unreadable and the genus stops being actionable at exactly the moment it is proven.**
   *Mitigation: report as SHAPE COUNT + one exemplar, never forty rows.*
2. **A count invites a batch fix, and a batch fix is the ledger genus at scale** — *a fix
   that destroys the record of the thing it fixed*, applied to forty sites at once.
   *Mitigation: M4. Read-only is not a nicety here, it is the containment.*
3. **It makes the sibling look worse than it is.** The sibling is frozen; instance counts
   there are exposure, not damage. *Mitigation: report lineage state beside every count.*
4. **The instrument becomes the authority on what a "shape" is.** Whatever it can express
   becomes the definition of the genus, and defects it cannot express become invisible —
   **which is how the frontier-checkpoint system stayed invisible for six months.**

---

# ITEM 2 — GIVE THE VERIFIER A VERDICT
### F-8c's owed build. Counting the right rows is not verifying.

**THE PROBLEM.** `verify_critical_data` prints `[OK]` **unconditionally** — no threshold, no
before/after. It would print `0 [OK]` on a destroyed corpus. The D-3 fix corrected *what* it
counts and did not give it a way to **fail**. Worse: **the automated janitor never calls it
at all**, so in production the deletions were never verified by anything.

**MUSTS**
- M1 It can **FAIL**, and the failure is a non-zero exit, not a printed word.
- M2 It compares **before vs after the same cleanup run** — a standalone count cannot detect loss.
- M3 It is **on the automated path**, or it is decoration.
- M4 It **cannot itself delete or repair** anything.
- M5 Degraded readings (legacy schema, missing columns) are **loud**, never silently partial.

| option | verdict |
|---|---|
| **A · Before/after snapshot inside `cleanup()`, abort-on-loss** | survives all five |
| **B · Post-hoc verifier run separately after cleanup** | ✗ M2 — the "before" is already gone |
| **C · Assert invariants on the DB only (evidence rows never decrease)** | survives; weaker, no per-run attribution |
| **D · Log before/after and let a human read it** | ✗ M1 — **this is precisely the rung-0e failure that produced zero records in 257 days** |

**WANTS**: catches partial loss not just total (9) · cheap (6) · works on legacy schemas (8)
· no false aborts on legitimate deletion (10 — *a verifier that cries wolf gets disabled, and
a disabled verifier is the state we are already in*).
**RECOMMENDATION: A, with C as the standing backstop.** A alone can be tuned into silence;
C survives A being switched off.

**PPA — WHAT BREAKS IF THIS WORKS**
1. **A cleanup that legitimately deletes evidence rows now ABORTS THE RUN.** The 30 GB
   ceiling depends on cleanup succeeding. **A correct verifier can therefore stop the disk
   from ever being reclaimed** — the two mechanisms are in direct tension and Seat 3 should
   see that before either ships. *This is the sharpest PPA on this page.*
2. **Before/after snapshots on a 3.6 GB DB cost time and space**, inside the janitor, every
   30 generations.
3. **It will fail immediately and loudly on legacy boxes** with partial schemas — correct
   behaviour that will read as a regression on day one.
4. **A verdict invites trust.** Once it returns PASS, people stop looking — and its scope
   (evidence rows in `game_results`) is far narrower than "the data is fine."

---

# ITEM 3 — `disk_space_monitor.py`, AN ORPHANED ORGAN
### found by the propagation read; **built, plumbed, never called** since 2026-08-10

**THE FACTS.** The module is present. Its call site in `evolution_runner.py` was removed on
2026-08-10. The sibling still calls it at every generation boundary **and has a gate test
for the wiring (`test_disk_monitor_wired.py`) that this repo does not have.** I built
`tools/disk_ceiling.py` from scratch eight days later without knowing any of this.

| option | note |
|---|---|
| **A · Delete the module** | honest, and destroys the only local record that the capability existed — **the ledger genus** |
| **B · Re-wire it as-is** | it is **report-only**, the exact failure Isaiah's ruling condemns (*"a ceiling that logs is a ceiling that scrolls past"*) |
| **C · Leave it, and register it as a known orphan** | costs nothing, keeps the record, keeps the lie that it is live |
| **D · Fold its per-table reporting into `disk_ceiling.py` and retire the module with a pointer** | keeps the capability, keeps the record, single gate |

**MUSTS**: must not resurrect a report-only ceiling (kills **B**) · must not destroy the
record of a removal (kills **A**) · must leave exactly one live disk mechanism (kills **C**).
**RECOMMENDATION: D.** It is the only option surviving the musts, which is worth saying
plainly — the elimination did the work here, not the weighting.

**PPA:** `disk_ceiling.py` grows a second job and becomes the single point of failure for
disk. Its per-table reporting reads the DB during a run, adding contention to the thing it
measures. And **retiring a module "with a pointer" is only as good as the pointer** — which
is the genus this whole page is about.

---

# THE REST OF THE HELD REGISTER — named, not worked up
*(each is apparatus, each waits; listed so the queue is visible rather than implied)*
1. **Put `verify_critical_data` on the janitor path** — inseparable from Item 2, same ruling.
2. **`fork_divergence.py` is one-directional.** It asks only "did OUR fix cross." The read
   that found the orphaned disk monitor asked the reverse. **My tooling defect.**
3. **Extend `comment_divergence.py`** to cross-file referents and single digits — its
   measured recall is **1 of 3** without them.
4. **The standing red `test_zero_score_games_deleted`**, which asserts the condemned
   behaviour as a requirement and has been red for five days. **SUBJECT/GROUND-GATED:**
   rewriting an assertion to match new behaviour is not a night-shift edit.
5. **The 21 sibling gate tests with zero filename overlap.** Porting guards is a build and a
   judgement about which lineage's guards are right.
6. **The frontier-checkpoint system: alive or not.** SUBJECT. If yes, a capability is being
   paid for and not received; if no, a rung registered at priority 4 and a cleanup routine
   are both lying.
7. **Gate coverage is 144 of 473 files.** Widening `include` is one line and a large amount
   of pre-existing lint. **A scope decision, not a cleanup.**
