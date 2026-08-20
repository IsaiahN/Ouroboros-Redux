# PREREG — W2c: THE PLANNER RETAINS WHAT IT LEARNS (2026-08-20) — NAMED, NOT YET BRIEFED

Seat 3: *"Every call discovers things about the environment, the objects, and what applies
where — and discards all of it on return. That is the spent-discriminator shape again...
Retention means the next call starts from what the last one found rather than from nothing."*

**THE BUILD:** the planner's per-call discoveries persist across calls within a level:
(a) the (atom, state_key) memo survives the call (already computed, currently discarded);
(b) applicability outcomes feed the W2a index (an atom that matched nowhere on this board is
recorded as such until the level changes — the binder's on_level_change clears it, which is
the retention window the binding_stale work already defines); (c) dead-end states are marked.
**The genus this closes:** produced-and-destroyed-at-production — binder/staleness,
planner/everything-it-touches, same shape, same fix (retention with a level-scoped clear).

**FALSIFIERS (to be pinned at briefing):** F1 second planner call on the same board does
measurably less apply_effect work than the first (the memo pays); F2 retention NEVER
survives a level change (leak check — the mark cannot outlive the world it describes);
F3 memory bounded (the retained set is capped and evictable; caps stated, not discovered).
**UNDO:** drop the persistence; per-call behavior returns exactly.
