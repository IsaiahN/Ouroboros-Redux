# PREREG: DEAD-CELL DEDUP (fix 1b)
DATE: 2026-08-17. AUTHORITY: Isaiah ruled yes.
MEASURED HARM: frontier.py documents dead as ">=2 INDEPENDENT RECORDS"; the code
increments per LIST ENTRY and the caller never dedups, so ONE episode clicking a cell
twice blacklists it. Live ar25 L2: dead(as coded)=163 vs dead(as documented)=41 —
122 cells (75%) blacklisted by within-episode repeats. Nothing decays it (no recency
term; the janitor never ran), so the elimination is MONOTONE forever.
BUILD: count DISTINCT RECORDS, not list entries — at BOTH ends:
  (a) WRITE: dedup the per-episode dead list before banking (one episode = one report);
  (b) READ: load_harvest counts distinct records per cell, so ALREADY-BANKED history is
      corrected WITHOUT deleting or rewriting evidence (archive law).
OFF-ARM (passing at ship): DEAD_DEDUP=0 reproduces the current per-entry counting
byte-identically.
FALSIFIER (failing first): a synthetic episode clicking one cell 5x contributes ONE
report; a cell needs reports from >=2 DISTINCT records to be banked dead; the effects
set still outranks dead; the >=2 rule itself is unchanged.
REGISTERED VERDICT (next beat): ar25 L2 dead count falls from 163 toward the documented
41. IF IT DOES NOT REACH ~41, THE RESIDUAL IS LEVEL-MIXING (audit F-5: the per-episode
dead/effect lists are never reset on level change, so an episode running 0->1->2 banks
its L0 and L1 clicks as L2 experience) — that is INFORMATIVE, not confounding, and it
is the next single. LOSING CONDITION: if the count does not move at all, the counting
was not the inflation source — revert.
