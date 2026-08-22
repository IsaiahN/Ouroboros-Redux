# PREREG — THE SUPERVISOR STOPS JUDGING; THE BOUND BECOMES A SHARE (2026-08-22)

Status: DRAFT for Seat 3, from the GM's ruling that a centralised controller deciding which
workers live is not permitted. Two separable changes; the second does not depend on the first.

## A · WHAT THE SUPERVISOR DOES TODAY (read from tools/swarm_supervisor.py)
| function | line | is it judging? |
|---|---|---|
| spawn the roster at start | :352-355 | no — nothing exists yet |
| restart a crashed/exited worker | the restart branch | no — a dead process cannot restart itself |
| deploy on code change (kill + respawn all) | :382 | yes, on timing it chose |
| MEM-KILL above a fixed cap | :410-414 | YES — decides which workers live |
| bounded-lifetime recycle at RECYCLE_MIN=120 | :419-425 | YES — an arbitrary clock |
| status.txt | the poll tail | no — observation |
| deploys.jsonl | :143-160 | no — a ledger |

## B · THE ANSWER TO "WHAT BREAKS IF IT ONLY SPAWNS AND NEVER JUDGES"
ONE thing, and it is real: **nothing restarts a worker that has died.** A dead process
cannot restart itself. This is not hypothetical — it is already recorded on this project:
sprint mode without the supervisor let workers exit at the end of their run and the fleet
went to zero SILENTLY (proctor-session-start memory, the sprint-keeper gap).
Everything else moves, and each move is an improvement rather than a loss:
- MEM-KILL -> a SELF-LIMIT inside the worker. Strictly better: a killed worker loses its
  in-RAM retention (the memo, the standing book, the persistence fold); a worker that stops
  ITSELF can flush first and stop at a generation boundary rather than mid-episode.
- LIFETIME RECYCLE -> deleted, or a self-decision at a generation boundary. The 120-minute
  clock was never derived from anything.
- DEPLOY -> the worker reads a version marker at its own generation boundary and exits
  cleanly for respawn. Removes the mid-episode kill entirely.
- STATUS + LEDGER -> keep. That is the GM's "verification that the plumbing works": reasoning
  logs written, action traces landing, the DB receiving what it should. A check, not a
  controller.
SO THE RESIDUAL SUPERVISOR IS: spawn, restart-the-dead, observe, ledger. It never decides
which worker deserves to live; selection returns to the ground (RLVR, the cull at a
generation boundary) where the existing mechanisms already sit.

## C · THE BOUND AS A SHARE, PORTABLE (the GM's rule)
`cap_per_worker = min(0.80 * TOTAL_RAM, TOTAL_RAM - RESERVE) / N_workers`, read at launch
from the machine (`psutil.virtual_memory().total` or the ctypes equivalent) and from the
roster length; recorded in KNOBS with the derivation, the machine it was derived on, and
the worker count it assumed, so it RE-DERIVES when either changes instead of being tuned.
Floor: a worker below some absolute minimum cannot run at all; state it and refuse to start
rather than thrash.

### THE ARITHMETIC ON THIS MACHINE, AND WHY IT DOES NOT DO WHAT WE HOPED
56 GB total, 10 GB reserved, 80% ceiling -> 44.8 GB usable.
| N workers | fair share | today's fixed cap |
|---|---|---|
| 25 | **1.79 GB** | 2.00 GB |
| 12 | 3.73 GB | 2.00 GB |
| 6 | 7.47 GB | 2.00 GB |
| 3 | **14.93 GB** | 2.00 GB |
| 1 | 44.80 GB | 2.00 GB |
**At 25 workers the derived share is TIGHTER than today's cap, not looser.** So this change
does NOT stop the 78 restarts; it would produce slightly more. Where it pays enormously is
at low worker counts -- in sprint mode (3 workers) the current fixed 2 GB is 7.5x too tight
and is throttling for no reason.
AND THE MACHINE IS NOT IDLE BECAUSE THE CAP IS LOW: typical workers use 0.5-1.1 GB, so 25 of
them peak near 27 GB of 56. The machine is idle because workers do not use their share --
except six that exceed it. THAT IS A DEFECT IN THOSE SIX, NOT IN THE CAP. The cap re-
derivation is right on its own merits (portability, honesty, re-derivation) and it is NOT
the fix for the ramp. The fix for the ramp is the cause, still unnamed.

## D · FALSIFIERS
- F1 · a worker crossing its own share stops ITSELF at a generation boundary, having flushed
  its retention; the supervisor observes the exit and respawns. Asserted by construction on
  a fake worker; no kill path is taken.
- F2 · the supervisor contains NO decision about worker fitness: an AST assertion that
  `stop_and_gc` is reachable only from the spawn/restart/deploy paths, never from a
  memory or lifetime comparison.
- F3 · the cap re-derives: same code on a machine with different total RAM, or a different
  roster length, yields a different number, and the KNOBS row records both inputs.
- F4 · portability: the derivation never exceeds 80% of the device, asserted at N=1.
- F5 · the fleet cannot silently go to zero: a worker that exits for any reason is respawned,
  and a respawn that fails is stated in status.txt rather than dropped.

## E · WHAT THIS DOES NOT DECIDE
Whether 25 processes is the right shape at all (see the ARC server note in PORT_LOG: the
toolkit ships `listen_and_serve`, a Flask server hosting environments for clients to play
over HTTP — one process holding the environments, N thin clients, which is a different
architecture from 25 full stacks). That is a larger question and this prereg does not
prejudge it.
