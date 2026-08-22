# record/ — WHERE THINGS LIVE, AND WHY THE ROOT STILL HAS 36 MARKDOWN FILES

## THE FINDING THAT SHAPED THIS REORGANISATION
The root looked like accumulated clutter. **It is a citation graph.** Measured before moving
anything: **36 of 80 root markdown files are cited BY NAME inside `.py`, at 102 sites**,
including live agent code — `cognitive_loop.py`, `cognitive_game_player.py`,
`engines/egocentric/consumer.py`. `record/canon/THE_LADDER.md` alone is cited 8 times; `record/canon/WIRING_REGISTRY.md`
8; `record/canon/CLAIM.md` 7.

**So the lazy-import lesson generalises: a file that live code cites by name is referenced by
a live path.** Moving those 36 would stale 102 citations *and* require editing agent code,
which is out of scope by Seat 3's constraint. **They stay at the root. Only uncited files
moved.**

| directory | what is in it |
|---|---|
| **root** (36 `.md`) | **cited by live `.py`.** Not clutter — a referenced corpus. Moving one means updating its citations in agent code. |
| `record/corpus/` | the framework deliverables: the seat map, the loop reference, figure notes, diagrams |
| `record/prereg/` | preregistrations no longer cited from code (resolved or superseded) |
| `record/findings/` | audits, reads, sweeps, decision analyses, the autonomy proposal |
| `record/log/` | `PORT_LOG.md`, the beat record |
| `record/retired/` | **superseded documents, with a note naming what replaced each.** Never deleted. |

## RELOAD POINTS — read these first after a compaction or a fresh session
**Canon, in dependency order:**
1. `record/canon/THE_LADDER.md` *(root — cited by 8 files, does not move)* — the diagnostic read order,
   the failure genera, and every rule adopted this week.
2. `record/corpus/THE_SEAT_MAP_general.md` — the seats, the laws, the loop appendix.
3. `record/corpus/THE_LOOP_reference.md` — the eight steps in compact form.
4. `record/canon/CLAIM.md` *(root)* — what is claimed and at what status.
5. `record/canon/WIRING_REGISTRY.md` *(root)* — live organs and their receipts.

**State, when picking the board back up:**
- `record/log/PORT_LOG.md` — the last beat, scoreboard-first.
- `record/findings/AUTONOMY_PROPOSAL.md` — what may be taken unsupervised, the stopping
  condition, the re-ranking rule.
- `python tools/split_half.py` — the standing beat number; `--since <UTC>` for a window.
- `.runs/swarm/status.txt` and `.runs/swarm/deploys.jsonl` — herd health and what code is
  actually deployed.

## HYGIENE IS ONGOING, NOT A PASS
Retiring a superseded document is **part of a beat**. A finding that supersedes a finding, or
a prereg that resolves, moves to `record/retired/` **with its replacement named** — because a
superseded document that stays live reads as current and nothing marks that it isn't, and
deleting it destroys the record of the correction.
