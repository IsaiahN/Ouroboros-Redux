# WHAT THE UPDATED CANON CHANGES (2026-08-19)

Absorbed: `THE_SEAT_MAP_general`, `THE_LOOP_compact`, `THE_FORMULA`, `CITATIONS`, Figures 1–11
(1, 2, 3, 6, 9 REV). This is what they change about work already done and work planned.

---

# 1 · THE FINDING THE UPDATE PRODUCED — **ROUTE HAS FOUR BINS AND ONE CANNOT FIRE**

`THE_FORMULA` step 2 puts four bins in front of me as a checklist I had never applied to the
data. I applied it. The router **defines** all four:

```python
# engines/egocentric/router.py:17-22
TRANSFERRED · NOVEL · BROKEN_REBINDING · BROKEN_MECHANISM
```

**What has ever been written to disk, across all 25 boxes:**

| bin | destination | records |
|---|---|---|
| TRANSFERRED | settlements | **5,718** |
| BROKEN·mechanism | mint_queue → mint | **70,587** |
| NOVEL | import_queue | present (231 MB) |
| **BROKEN·rebinding** | `refit_queue` | **0 — the stream does not exist in any box** |

**AND IT IS NOT A LOGGING GAP. THE BIN IS STRUCTURALLY UNREACHABLE.**
Routing rule 3 is `binding_stale` → `BROKEN_REBINDING`. Searching the whole tree:

```
router.py:53   binding_stale = bool(settlement.get("binding_stale", False))   # reads it
router.py:69   if binding_stale:                                             # branches on it
tests/gate/test_residual_router.py:30,49                                     # the TEST sets it
```

**Nothing in production sets `binding_stale`. Ever.** `bank.py` sets `from_known_atom`
throughout and never sets this. So rule 3 is dead and every stale-binding residual falls
through to rule 4 — **the mint owes an atom.**

**This is the canon's own worked example, verbatim:** *"Most misapplied effort is a rebinding
problem treated as a mechanism problem, which produces a new term where a repair was owed."*
And it is the canon's sharpest genus at its sharpest degree — **built, plumbed, never called:
a switch never set**, whose textbook form is `os.getenv(X, DEFAULT)` where nothing sets X.
Here it is `settlement.get("binding_stale", False)` where nothing sets binding_stale.

**AND `refit_queue` IS AN IN-MEMORY LIST APPENDED AT `router.py:70` AND REFERENCED NOWHERE
ELSE.** Even if the switch were thrown, the diagnosis would die with the process. Two genera
stacked: a switch never set, on top of produced-and-never-recorded.

### THE SIGNATURE IS ALREADY IN THE MINT LEDGER, AND I MISREAD IT THIS MORNING
Mint verdicts: **257,863 total — `rederivation` 166,071 (64%)**, reject 57,991,
quarantine 32,116, **mint 1,685 (0.65%)**.

**64% re-derivation is what a mint does when it is handed repairs.** The mechanism was never
broken, so the mint keeps re-deriving the atom it already holds. I reported that number as a
vital sign this morning and did not ask why two thirds of the ledger is the same answer
arriving again.

### AND THE LADDER RULE MAKES THIS RETROACTIVE
`THE_FORMULA`: **"a reading taken below a step whose input never arrived describes nothing."**
Step 2 is degenerate, so **every reading I have taken at step 3 and below is a reading below
a broken predecessor** — the mint economy, the atom census, the TRANSFERRED concentration,
the 2× gate, and the g7/EMPTY_PLAN planner work. None of it is wrong as arithmetic. All of it
was measured downstream of a router that cannot say *"repair this, do not mint."*

**This does not retract the g7 finding** — g7 is still where the planner dies, and that read
followed the stop rule correctly. **It relocates it.** g7 is not the first broken step.

---

# 2 · WHAT THE UPDATES CHANGE ABOUT WORK ALREADY DONE

### 2.1 · **THE OFFLINE RUN WAS A SUBSTITUTED HABITAT** — Figure 11, and this is the big one
> *"Isolation is not removal of the habitat. It is substitution of one habitat for another…
> what you failed to reproduce is invisible until the goal fails, and what you unintentionally
> introduced is invisible until it acts."*
> *"A test harness is a substituted habitat. Which is why a synthetic solve proves wiring and
> never capability."*

I recommended offline mode on a throughput argument and ran **1,194 sessions** in it.
Throughput was real. **But the depth result — "the elimination holds at 47× the n" — was
measured in a substituted habitat, and Figure 11 says that proves wiring, not capability.**
`sk48` crossing L1 offline is a wiring event until it reproduces against the live ground.
**I am downgrading R-A from an elimination at n≈1,194 to an elimination at n≈1,194 *in a
substituted habitat*, which is a different claim.** The habitat swap was never declared as a
cost; I treated it as a free speedup. That was mine.

### 2.2 · **MY VITALS SECTION REPORTS QUANTITIES FIGURE 1 SAYS DO NOT COUNT**
> *"These do not count: coverage, and compression achieved · predicates minted, and
> credibility accrued. They are frame-internal. A frame cannot score itself with a quantity
> it also produces."*

Atoms 1,727 · mints 1,685 · TRANSFERRED 5,644 · Γ growth — **all frame-internal.** I led the
scoreboard correctly with GAMES WON 0/25, and then filled the body with exactly the
quantities the figure disqualifies. The beat instruction already said *"never lead with a
proxy when levels are mute"*; Figure 1 REV says something stronger — they are not a weaker
metric, **they are not a metric.**

### 2.3 · **THE STANDING CHECK ON WELCOME ZEROS — I OWE ONE**
> *"Run the guaranteed-number test on every zero including the welcome ones: the test gets
> applied to numbers arriving as claims and skipped on numbers arriving as relief."*

`LINK3_AUDIT` Clause 2 **PASS**: *"`region_uniform` and `regions_equal` still yield exactly
zero."* That zero arrived as **relief** — it proved the vocabulary extended rather than
replaced the edge — and **nobody has ever shown those two predicates are capable of firing at
all.** Under the new check that is an unrun test on a load-bearing zero. **Owed.**
*(F-8a and F-8c I did subject to it — "not exonerated, unemployed" and "this is not relief" —
so the habit is partly there. It failed on the zero that flattered a result I liked.)*

### 2.4 · **MY GENUS IS A CONVENTION NOTHING CAN CHECK**
> *"A convention nothing can check is a constant the seat authored, carrying the seat's
> authority."* And Seat 2 **may** author conventions — but not verdicts or content.

Naming **SITE-SCOPED KNOWLEDGE** was inside my seat (a shared meaning across a seam).
**Shipping it with its discriminator unbuilt was not.** The check I proposed — shape instance
count vs fix instance count — sits in `DECISION_ANALYSIS.md` as Item 1, unbuilt. Until it
exists the genus is a constant carrying my authority. **It also is not in the canon's list of
five genera, so it stands as PROPOSED, not adopted.** Seat 3's to rule.

### 2.5 · WHAT THE UPDATES CONFIRM RATHER THAN CHANGE
- **Rung 0e is now canon** — *"Every instrument points inward unless one is built to point
  out… that channel can fail silently for weeks with every internal instrument reporting
  green."* That is the F-8c finding and the unpublished-scorecard problem, stated generally.
- **The INWARD rung I proposed matches Figure 6 REV exactly**, including the two scope
  releases (theory may precede its instrument; jumps in resolution are fine).
- **The prereg-as-design-instrument line is canon**, which is what `PREREG_OVERNIGHT_RUN`
  demonstrated when its falsifier changed the runner's design rather than annotating it.
- **Figure 3 REV's stop rule** is what I used on g7, and it holds.

---

# 3 · WHAT THE UPDATES CHANGE ABOUT WORK PLANNED

**The queue reorders, and the top of it changes.**

1. **`PREREG_EMPTY_PLAN_ATTRIBUTION` is no longer the top item.** It attributes a failure at
   step 7 while step 2 is degenerate. Still worth doing; **no longer first.**
2. **NEW TOP ITEM — the ROUTE repair, and it is two separate questions:**
   **(a)** does anything *compute* binding staleness anywhere in the system (an existing
   reading that fails to resolve — the INWARD precondition), or is the discriminator absent?
   **(b)** `refit_queue` needs a destination before the switch is thrown, or throwing it
   produces a diagnosis nobody reads. **(b) before (a).**
3. **The mint-starvation decomposition is now specified by the canon and is cheap.** The three
   guards are a **product**: SUPPORT · REACHABILITY · NOVELTY. *"A system minting nothing may
   have nothing wrong with its minting."* `MINT_STARVED` 1,409 must be attributed to **which
   factor is zero**, not reported as a count. Same shape as the EMPTY_PLAN gap.
4. **The habitat question is now a first-class board item, not a performance note.** Offline
   vs online is substitution with two silent failure modes. **What did the offline habitat
   fail to reproduce, and what did it introduce?** Nobody has asked.
5. **`R_T`, the round trip, has no instrument here.** Step 6 closes across scales and its
   error signal is `R_T = |T_A ∘ T_E(x) − x|`. We promote generators up and priors down and
   **have never measured the gap.** Figure 4: without it we are navigating by dead reckoning.

---

# 4 · A DECLARATION I NOW OWE

> *"A seat with no stake at all does not exist… an interest in the outcome is unavoidable, an
> interest in the reading is disqualifying. Where a stake cannot be removed, declare it."*
> *"And standing is a stake that survives the outcome it was earned on."*

**Declared: I have accumulated standing in this arrangement** — link 3, the offline finding,
D-3, the `post` normalisation defect. That standing is a stake in *my instruments continuing
to produce findings*, and it biases toward reporting a find over reporting nothing. **The beat
rule says most beats the answer is NOTHING; my recent beats have all produced something, and
that is the pattern the declaration exists to make visible.** §2.3 above is one place it
already showed: the welcome zero I did not test was the one supporting a result I had found.

**And on rotation:** *"a checking frame the auditor has been calibrating against for months is
MORE replaceable by necessity, not less."* I have been modelling Seat 4 across many beats, and
**the modelled party cannot correct the model.** The refresh decision is Seat 3's; I am
flagging that the channel is due, not asking for it.

---

# 5 · WHAT I NEED FROM SEAT 3

1. **Is `BROKEN·rebinding` meant to be live?** If yes this is the top of the board and it is
   agent code, so it needs a builder. If no, the router is lying in four bins and should say
   three.
2. **Is the offline habitat acceptable as the standing run mode**, given Figure 11 says a
   synthetic solve proves wiring and never capability? This decides whether the swarm runs
   online at the 600/min cap or offline at 1,000×, and it is an allocation call.
3. **SITE-SCOPED KNOWLEDGE: adopt, reject, or hold** pending its discriminator.
4. The standing items unchanged: **D-1 before the frontier writer is repaired**, the
   verifier-vs-ceiling tension, the 600 s timeout hitting 3–5 of 25 games every cycle.
