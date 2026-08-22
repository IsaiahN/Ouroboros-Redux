# PREREG: THE THREE READOUTS — starvation codes, socket/filler grade, consumer gate

DATE: 2026-08-13. AUTHORITY: Isaiah ("can we employ this?"). THE LINE: the agent may read
its own RESIDUAL; it may never read its own GRADE.

## R1: SOCKET STARVATION CODES (agent + maintainer)
Fixed ENUM of game-agnostic codes (machinery facts only): e.g. NO_STABLE_REFERENCE (g2),
NO_REFERENCE_BINDING (g4), EMPTY_PLAN (g7), NO_NEGATIVE_INSTANCES, MINT_STARVED,
BANK_NO_FAMILY. When a socket starves persistently within an episode (thresholded), ONE
record {socket, code, level, budget_spent, seq} appends to the agent's PERSONAL fabric
stream "starvation". Write-contract (affect law): derived from the ledger, replayable
(pure function of episode events), bounded (<= 1 per socket per episode), narrated
([STARVE] line). CONSUMER (same build, one-currency law): the affect/seed-bias path may
read the latest starvation records to STEER exploration effort; it never prices (no bar,
no support, no reputation effects). Codes contain no game content by construction (enum).
FALSIFIER (failing first): an episode engineered to starve a socket emits exactly one
enum-coded record + [STARVE] narration; a healthy episode emits none; the record replays
as a pure function of the episode's ledger prefix.

## R2: SOCKET-VS-FILLER CLASSIFICATION (maintainer ONLY — the grade)
Proctor seat, outside agent-readable space (repo/PORT_LOG — agents read fabrics only).
(a) Every build commit's PORT_LOG line carries SOCKET or CONTENT. (b) tools/
socket_or_filler_lint.py: heuristic flags on agent-code diffs — literal grid arrays,
absolute coordinates, game-id string literals, hardcoded colour mappings. A CONTENT flag
on a builder diff = firewall alarm, proctor review. Never wired into agent code or tests
the agent's behaviour depends on.
FALSIFIER: lint flags a synthetic diff containing a hardcoded grid + game id; passes the
CK-1/CK-2 diffs (which were sockets).

## R3: PRODUCED-BUT-NEVER-CONSUMED (build gate, CI)
tests/gate/test_consumers.py: static inventory — every fabric topic WRITTEN somewhere in
the codebase must be READ somewhere outside its writer, OR appear in an ALLOWLIST where
each entry cites a prereg (an open socket is a named promise, not silence). KNOWN OPEN
TODAY: import_queue (consumer specced C33 §14-16, queued CK-3+) — allowlisted with that
citation; starvation (consumed by R1's seed-bias reader, so NOT allowlisted). When a
consumer lands, its allowlist entry is DELETED (the gate tightens monotonically; test
asserts allowlist entries still lack consumers — a stale entry fails the gate too).
FALSIFIER: a synthetic writer with no reader and no allowlist entry fails; import_queue
passes only via its cited entry; deleting a real consumer turns the gate red.

## CONTAINMENT
Gate suite (222) green; failing-first; R1 narration bounded; wheel rule untouched; the
8000-char .credit window untouched (starvation write sites live outside record_result or
within slack). Separate commits: R1+R3 (builder), R2 (proctor tooling).
