# PRE-REGISTRATION — the smart cleanup (Isaiah's file-storage retention system)

**Written 2026-08-12, at `584d80d`. Urgent at swarm scale: 25 worker DBs (~0.25 MB/episode of
telemetry each) + 25 fabrics growing in parallel. v4's SafeDatabaseCleaner philosophy (keep
knowledge forever, cap telemetry) improved: size-triggered not cadence-triggered, loud not
silent, compaction not deletion where data has summary value.**

## THE TOOL (proctor instrument: tools/verify/fabric_janitor.py — offline, paused boxes only)
> Per-stream policies, atomic rewrite (write-new -> os.replace), manifest printed ALWAYS:
> - ideas: confirmed/echoed kept forever; pariahs -> tombstones (id, cell, status).
> - idea_events: events older than the last 50 fold into per-idea cumulative counters
>   (a snapshot record); credibility recomputable exactly.
> - frontier_harvest: per (game,level) -> ONE merged snapshot record (dead cells EMITTED
>   TWICE across two snapshot records to preserve the >=2 dead rule, effects/fatal unioned,
>   deltas first-seen) + the last 10 raw records.
> - settlements: per (game,level) fold into counters (n, nontrivial_n, best-histogram) +
>   last 100 raw (affect's window is 20; margin 5x).
> - replay_outcomes: last 20 per game.
> - atoms / atom_narrowings / mint_verdicts / import_queue: KNOWLEDGE — never compacted in v1.
> Trigger: any stream > 2 MB or fabric total > 20 MB. Dry-run default; --delete to act.
> DB-side: the existing janitor discipline extends to swarm boxes (core_data.db trimmed only
> on STOPPED workers; fabrics/logs/controls always kept).

## THE GATE
1. Tests: per-policy round-trips — post-compaction, every consumer READS THE SAME ANSWERS
   (priors ranking, load_harvest merge incl. the >=2 dead rule, credibility, mastery rates,
   affect gains) — byte-equality of consumer outputs pre/post compaction on a synthetic fabric.
2. ⭐ FALSIFIER: any consumer answer changed by compaction -> the tool is WRONG, revert; loud
   manifest required on every run (the silent-failure fix).

## THE UNDO
Tool is offline + dry-run default; git revert for the tool itself.
