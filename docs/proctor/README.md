# Proctor operating layer

- **PROCTOR_MEMORY_law_0.md** — LAW 0 + Rule 0 of Evidence + the phantom-first debug guide. Load first.
  Outranked only by `../corpus/*` (the map).

The live running state and the two reference instruments live in the attached claude.ai project and are
mirrored into this folder as they stabilise:
- **PROCTOR_STATE.md** — the session-by-session running log / handoff (latest first). [project: `claude/PROCTOR_STATE.md`]
- **THE_LADDER.md** — the developmental metric (L0–L5), corroboration-anchored. [project: `claude/THE_LADDER.md`]
- **UNREACHABLE_INVENTORY.md** — what the agent has but cannot use (flags off / modules unwired). [project: `claude/UNREACHABLE_INVENTORY.md`]

A scheduled autonomous session should read the live PROCTOR_STATE from the project before starting, and
write its handoff back there (and mirror it here on a stable-checkpoint push).
