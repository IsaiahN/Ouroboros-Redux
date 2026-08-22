# PREREG — SHORT BATCHES AS A MEASUREMENT OF ACCUMULATION (2026-08-19)

**AUTHORITY: Seat 3 —** *"Run in batches of roughly five minutes rather than two-hour worker
lives… Register it as a measurement rather than as a deployment change with a safety check
attached."*

**REGISTERED AS A MEASUREMENT. The deployment benefit is real and it is not what is being
tested.** What is being tested is whether **accumulation within a worker's life does anything**,
which the architecture claims and nothing has ever measured.

---

## THE CLAIM UNDER TEST
The architecture says an agent **learns, banks, seeds and improves across episodes within a
worker's life** — compounding. **A 5-minute life is ~24× shorter than the current 2-hour one.**
If compounding is real, shortening the life should cost something measurable.

## THE BASELINE, PINNED NOW (PORT_LOG 37, this beat)
**Split-half improvement: 0 of 25 games improved their best-ever `level_completions`;
`cn04` regressed 1→0; `r11l` has completed nothing in its last 20 episodes.**
Last-20 means: `ar25` 1.20 · `sk48` 0.95 · `lp85` 0.80 · `cd82` 0.65 · `sp80` 0.65 ·
`ft09` 0.15 · everything else 0.00. **GAMES WON 0/25.**

## THE THREE OUTCOMES, ALL WORTH HAVING
- **WORSE** → accumulation was doing something and **batch length is a real constraint.**
  That is a finding, and **it argues against the change** — batching would be reverted and the
  constraint would become a target.
- **UNCHANGED (still zero)** → **batch length was never the constraint and nothing was lost.**
  The deployment benefit is then free.
- **BETTER** → the **known-negative**, and it is not a win. It would mean long lives were
  *costing* something — memory growth, state rot, the five mem-killed workers — and **the
  accumulation claim is inverted.** *Either direction of movement is a result; only "unchanged"
  is neutral.*

**READ AT: 24 h and 72 h after the switch, split-half within the post-switch window** — never
against the pre-switch history, which has a different worker-life regime and would confound
the comparison with the mode flip that landed the same day.

---

## PRECONDITION (a) — **CLEANUP IS LIVE, BUT IT IS NOT `disk_ceiling`, AND ITS CADENCE ASSUMPTION BREAKS**

**`disk_ceiling.py` IS NOT IN THE SWARM PATH.** Its only callers are `tools/overnight_run.py`
(a finished run) and its own gate test. **The 30 GB ceiling has never been checked by the live
swarm** — Seat 3's *"exists and has never fired"* is exactly right.

**What IS live: `swarm_supervisor.db_gc()` (:59), called from `stop_and_gc()` (:205) at every
recycle and every kill.** What it does when it fires:
1. `PRAGMA wal_checkpoint(TRUNCATE)`
2. **if box DB > `DB_HARD_CAP_MB` (600): `DELETE FROM` every `TELEMETRY_TABLES` entry —
   which includes `action_traces`.** *This is D-4. No archive, no undo.*
3. if box DB > `VACUUM_AT_MB` (200): `VACUUM`

**THE CADENCE ASSUMPTION IS THE PROBLEM, AND IT IS NOT A SAFETY CHECK BOLTED ON — IT CHANGES
THE COST OF THE EXPERIMENT.** Both thresholds were chosen for a **2-hour** boundary. At
5 minutes the boundary fires **~24× more often**:
- **VACUUM rewrites the entire DB file.** Current boxes: `bp35` **153 MB**, several above
  100 MB, threshold **200 MB**. **Once a box crosses 200 MB, every batch boundary triggers a
  full VACUUM** — 25 boxes × ~12/hour = **~300 VACUUMs/hour**, each rewriting a 200 MB file.
  That is a disk-throughput cost that did not exist at a 2-hour cadence.
- **D-4 stops being a 23-day risk and becomes a per-boundary one.** It is size-triggered, so
  batching does not make it fire *sooner in bytes* — **but it moves the check from twice a day
  to ~300 times a day**, and the thing it does when it fires deletes the level evidence.

**REQUIRED BEFORE BATCHING LANDS, and this is the part Seat 3 asked to be confirmed rather
than assumed:** the two thresholds must be **re-derived for the new cadence**, or `db_gc` must
be made **boundary-count-aware** (e.g. VACUUM at most every Nth boundary). **Batches that clean
up on a 2-hour schedule at a 5-minute rate convert a slow disk problem into a fast one** —
which is precisely Seat 3's warning, and it is confirmed rather than hypothetical.

---

## PRECONDITION (b) — **THE NEW HOLD MECHANISM**

**The old model was: commit = the boundary between "not running" and "running." That was
false** (`record/canon/THE_LADDER.md`, *the working tree is production*): a change is live at the recycle.
**At ~12 boundaries an hour it is live within five minutes, so "hold the commit" protects the
repository and nothing else.**

**THE HOLD IS NOW A FILE THE LAUNCHER READS, NOT A DISCIPLINE SOMEONE REMEMBERS:**

| | mechanism |
|---|---|
| **HOLD** | `.runs/swarm/HOLD` exists → **the launcher finishes the current batch and starts no new one.** Deleting the file resumes. *The stop is a file, so it survives the operator forgetting.* |
| **DEPLOY** | happens at the **next batch boundary**, automatically, from the working tree. There is no other deploy step and pretending otherwise is what produced this morning's error. |
| **RECORD** | every batch logs `git rev-parse HEAD` **and** `git status --porcelain` for live-path files. **This is rung 0e applied to deployment: what actually ran this batch is answerable afterwards**, including when the tree was dirty. |

**AND THE CHARACTER OF THE GATE CHANGES, which is worth stating plainly:** at a 5-minute
boundary a bad change costs **one batch**. So the hold is no longer a *safety* device — it is
for **deliberate staging**, holding something back on purpose. **Safety now comes from the
batch being short, not from the gate being closed.** That is the arm mechanism applied to
deployment, exactly as Seat 3 put it: variation inside, selection between, at a rate that makes
selection affordable.

---

## FALSIFIERS FOR THE BATCHING ITSELF (distinct from the measurement)
- **F1 · IT STILL PLAYS.** Every one of 25 games produces sessions within two batch boundaries.
- **F2 · CLEANUP RUNS AND IS BOUNDED.** `db_gc` fires at boundaries **and** total VACUUM time
  per hour stays under a stated budget. *Fails if:* disk throughput becomes the limit.
- **F3 · THE HOLD HOLDS.** With `.runs/swarm/HOLD` present, **no new batch starts** and a
  deliberate live-path edit does **not** reach any worker. *Fails if:* a change lands anyway —
  which would mean the new gate is as fictional as the old one.

## UNDO
Restore `RECYCLE_MIN` to 120 and remove the batch loop. **No data touched.** The measurement
window's records stay and remain readable.
