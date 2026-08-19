# PREREG — THE TWELVE-HOUR OFFLINE RUN (2026-08-18)

AUTHORITY: Isaiah — *"Run the swarm for the twelve hours — that's the item with a visible
cost and it's yours to spec."*

## WHAT IT IS
**OFFLINE** (`--mode offline`, no API key, no 600/min cap). **Repeated BASIC SETS**: one
cycle = **25 unique games x 1 agent x 1 pass**, cycles run back to back until the clock or
the ceiling stops it. **CONCURRENCY 4, NOT 25** — the box has 4 logical cores and the old
25-pinned design oversubscribed it ~13x, which is the measured reason workers emitted once
per 10-15 minutes.

**WHY REPEATED BASIC SETS RATHER THAN 25 PINNED CONTINUOUS WORKERS:** the basic set is Seat
3's stated unit, it gives every game equal exposure per cycle, and **it makes the scoreboard
delta per cycle readable** instead of smearing 25 unsynchronised lifetimes together.

## THE FOUR PRE-REGISTERED READS — stated before the run, not chosen after
**R-A · DEPTH.** GAMES WON n/25 and per-game max level. **The current elimination —
*depth is not throughput-bound* — was established at n=25 sessions. This run takes n into
the thousands on the same question.** A new depth record is the headline if it appears.
**R-B · THE LINK-3 HOOK.** `levelup_frames` records at level > 1: **currently 2.** The hook
is ground-settled but its reproducibility is n=2. This gives it hundreds of chances.
**R-C · THE QUEUE PREDICTION, WHICH CAN FAIL.** I measured +47.8 records in and 8 out per
episode, i.e. **+39.8 net, monotonic**. **PREDICTION: import_queue grows by ~40 x (sessions
added).** *If it does not, my arithmetic is wrong and the rate finding needs re-deriving.*
**R-D · THE DB-COST CURVE, ALSO FALSIFIABLE.** I claimed per-session cost scales with
accumulated box size (11.7 s fresh vs 71.3 s at 55 MB, then ~33.9 s after R3). **PREDICTION:
cycle wall-clock rises monotonically as boxes grow.** *If cycle time is flat over 12 hours
while boxes grow, the box-size claim is dead and the residual is elsewhere.*

## SAFETY — nothing irreversible, per the standing instruction
**THE DISK GATE RUNS BEFORE EVERY CYCLE.** `disk_ceiling.py --guard`; on breach the run
**STOPS** and does not sweep. **NO ARCHIVE-THEN-TRUNCATE FIRES DURING THIS RUN** — cleanup
is Seat 3's and stays parked. **No deletion, no compaction, no pragma change.**
Budget headroom: 4.456 GB of 30. At ~0.5 KB/record and ~48 records/session the run cannot
plausibly approach the ceiling; the gate is there because a ceiling that is never checked is
a ceiling that scrolls past.

## FALSIFIER FOR THE RUN ITSELF
**If a cycle produces ZERO new sessions across all 25 games, the run is broken and must
stop rather than continue burning hours.** Checked per cycle against the session count.

## UNDO
Kill the process. Nothing is deleted, nothing is migrated, and every box is append-only for
the duration.
