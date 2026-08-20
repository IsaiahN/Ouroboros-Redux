# THE TWELVE-HOUR OFFLINE RUN — RESULT (2026-08-18 → 08-19)

Against `PREREG_OVERNIGHT_RUN.md`, written before the run. **47 cycles + the smoke cycle =
48 records, 1,194 sessions, OFFLINE, pool 4.** Stopped by the **wall clock** — not the disk
gate, not the run's own falsifier. Exit 0.

**SAFETY HELD.** Disk 4.474 → **4.875 GB of 30** (16.3%). The gate ran before all 47 cycles
and never breached. **`.runs/archive` does not exist: no sweep fired, nothing was deleted,
truncated, compacted, and the pragma was not touched.** Every box append-only throughout.

---

## THE SCOREBOARD

| read | prediction | result | verdict |
|---|---|---|---|
| **R-A depth** | (elimination test) | maxL **2→2**, L2+ **1→1**, L1+ **8→9** | **ELIMINATION HOLDS at 47× the n** |
| **R-B link-3 hook** | reproducible? n was 2 | **3 → 37** | **SETTLED** |
| **R-C queue rate** | ~**+40**/session | **+63.0**/session | ❌ **FALSIFIED (1.58×)** |
| **R-D DB-cost curve** | cycle time rises with box size | corr **+0.194**; timeouts corr **+0.797** | ❌ **FALSIFIED** |

**TWO OF MY FOUR PRE-REGISTERED READS FAILED AGAINST ME. That is the point of registering
them, and both are reported before the one that flattered me.**

### R-C · THE QUEUE PREDICTION — FALSIFIED
Queue **408,649 → 482,301 = +73,652 over 1,169 sessions = +63.0 per session.**
I predicted **+39.8** from a measured +47.8 in and 8 out per episode. **I am wrong by 1.58×,
and the rate finding needs re-deriving** — the in/out measurement was taken on a small
sample and does not survive contact with 1,169 sessions. What survives: the queue is
**monotonic and unbounded**, growing ~1.5 records per session faster than I claimed.

### R-D · THE DB-COST CURVE — FALSIFIED, AND THE REPLACEMENT IS BETTER
I claimed per-cycle wall-clock rises as boxes grow. It does not, in any dominant sense:

| | correlation with cycle seconds |
|---|---|
| cycle index (i.e. accumulated box size) | **+0.194** |
| **number of games hitting the 600 s per-game timeout** | **+0.797** |

| timeouts in cycle | n | mean cycle | range |
|---|---|---|---|
| 1 | 2 | 674 s | 641–707 |
| 2 | 4 | 747 s | 706–792 |
| 3 | 13 | 749 s | 383–882 |
| 4 | 17 | 890 s | 767–1200 |
| **5** | **12** | **1200 s** | **1200–1200 — zero variance** |

**Cycle time is set by how many games hit the timeout ceiling, not by box size.** At pool 4,
five timeouts serialise into exactly two 600 s rounds = 1200 s, twelve times, with *no
variance at all* — that is a saturation artefact, not a growth curve. A mild upward drift
does exist (first-5 mean 786 s → last-5 mean 893 s) but **it is not separable from timeout
incidence in this design**, so I claim nothing from it. **The box-size cost claim in
`PERF_AUDIT.md` is not supported at this scale and should carry this result beside it.**

### R-A · DEPTH — THE ELIMINATION HOLDS, AND ONE GAME MOVED
**1,194 sessions produced no new depth.** `maxL` stayed 2; only `ar25` is at L2+, exactly as
before. The elimination — ***depth is not throughput-bound*** — was established at n=25.
**It now stands at n≈1,194, a 47-fold increase in evidence, unchanged.** Throughput was
never the binding constraint and this closes the question at a population that cannot be
called underpowered.

**BUT ONE GAME DID MOVE, AND IT IS NOT NOTHING.** `L1+` went **8 → 9** at cycle 22:

```
sk48   first level>=1 trace: 2026-08-19 05:49:52   (2,626 such traces since)
```
**Every other L1+ game first crossed on 2026-08-12 or 08-13. `sk48` is the first new game to
reach level 1 in six days, and it did it in this run.** One crossing in 1,194 sessions is a
rate, not a breakthrough — but it is a real crossing on a game that had never crossed.

### R-B · THE LINK-3 HOOK — SETTLED
**`levelup_frames` records at level > 1: 3 → 37.** Before today the count was **2, and the
hook's falsifier was proven in simulation only.** It is now ground-settled with 34 further
firings across the run. **Reproducibility is no longer the open question.**

---

## WHAT THE RUN ALSO BOUGHT, OUTSIDE THE PREREG
The `post`-normalisation defect (see `LINK3_AUDIT.md` Addendum 4) was **found in this run's
banked evidence and its fix was confirmed by this run's later records** — three crossings
banked `post=[3,64,64]`, and every crossing after the fix banked `post=[64,64]`. **The run
was both the instrument that exposed the defect and the witness that the fix took.**

## THE STANDING COST THIS EXPOSES — for Seat 3, not decided here
**3 to 5 of 25 games hit the 600 s per-game ceiling in every single cycle**, and they are the
dominant term in wall-clock. That is between 12% and 20% of every cycle's work being cut off
mid-episode, every cycle, for twelve hours. **Whether the ceiling should rise, or those games
should be diagnosed as slow, is an allocation question and therefore APPARATUS.** The
long-episode games by traces/session are `lp85` (144), `sk48` (122), `sb26` (119),
`wa30` (119) — and `sk48`, the one that crossed, is among them.
