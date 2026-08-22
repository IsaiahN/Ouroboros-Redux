# THE EXAMINATION — shared rubric (GM, 2026-08-22). Every file examined, not sampled.

## Why (the GM's case, verbatim in substance)
An ungated replay whose comment claims it is gated; a normaliser applied to one side of a
pair; two frame writers where one is lossy; a rung with four defects that never fired; 315
primitives never exercised; five modules nobody remembered; a grammar that existed twice.
None of these were found by looking — they were found by tripping over them. The whole
surface gets examined once.

## The three destinations
- **live** — stays where it is. One line: what it does.
- **preserve/** — not called today, and holds capability worth having. One line on what the
  capability is and why it might matter. (`sequence_miner` was nearly deleted and was the
  only code able to express level-scoping; the composer lineage was five modules of work we
  were rediscovering. ASSUME THERE IS MORE.)
- **considered_dead/** — appears dead. Moved, never deleted.

## The reachability test (this week proved imports are not sufficient)
For every file record HOW it is reached, with the site:
1. STATIC — imported (transitively) from an entrypoint: `evolution_runner.py`,
   `tools/swarm_supervisor.py`, `tools/sprint_keeper.py`, `cognitive_game_player.py`,
   `game_player.py`, `arc_api_adapter.py`.
2. LAZY — reached only by an in-function import. Name the file:line. (27 modules on this
   fleet are reached ONLY this way, eleven inside `engines/egocentric` — a static import
   scan understates the live path by that much.)
3. STRING — reached by `importlib`, `__import__`, a subprocess command line, or a config/
   JSON/registry string. Name the site. THIS IS HOW `manual_tools` SURVIVED being called
   proctor tooling by everyone.
4. TEST-ONLY — referenced only from `tests/`.
5. NAMED-ONLY — its name appears somewhere (a README, a KEEP list, an inventory) but
   NOTHING INVOKES IT. 80 files are in this state; a bare-string sweep cannot tell an
   inventory from an invocation, and that difference is 80 files.
6. NONE — no import, no string, no test.
Search the module's bare name as a STRING across `.py/.json/.md/.txt/.toml/.yaml` as well as
parsing imports. A file reached only by a lazy import or a string will not fail at import —
it fails in production, on one path, later.

## Constraints (binding)
- Nothing in the current agent architecture, nothing under `tests/`, nothing with a `.`
  prefix is proposed for a move. Examine them; mark them **live** by constraint.
- Skip `.`-prefixed directories entirely. `environment_files/` (game data) and `record/`
  (the archive) are out of scope for moves.
- **NOTHING IS MOVED OR DELETED IN THIS PASS.** Produce the list. The GM approves or does not.
- Recoverability: when moves are later approved, git is the record, with commit messages
  saying what moved and why.

## Structure
One subdirectory level, except `.`-prefixed directories. WHERE THAT RULE AND LEGIBILITY
DISAGREE, LEGIBILITY WINS: if flattening a package would put two hundred files in one
directory, say so and propose the alternative rather than executing a rule that defeats its
own purpose. The point is that the GM can verify nothing is hiding.
(Known: flattening exceeds 60 files in `engines/` (161), `tests/` (154), `manual_tools/`
(63); `engines/` additionally cannot flatten without destroying 13 `__init__.py` files that
are the only thing reaching 5 registry-loaded modules.)

## The output format — one row per file, no exceptions
```
| path | dest | reached-by (with site) | one-line: what it does | if preserve: the capability and why it may matter |
```

## What the GM wants out of it
The inventory, not the tidiness. And above all the **preserve** category — capability this
build does not have, sitting in the tree unreached. That is what this is being done for.

## AMENDMENT 1 (2026-08-22, forced by EXAM_03's first finding) — THE DOT-DIR RULE HAS A HOLE
"Skip `.`-prefixed directories entirely" is correct FOR MOVES and WRONG FOR REACHABILITY.
`.github/workflows/ci.yml` invokes `tools/consumption_sweep.py` (:41) and `tools/ood_lint.py`
(:47) as BLOCKING steps on every push and PR; `.pre-commit-config.yaml:17` invokes
`tools/vulture_whitelist.py`. The earlier automated inventory called all three unreached
BECAUSE IT SKIPPED DOT-DIRS AT EVERY LEVEL. CI is the most reliable invocation site a repo
has, and the skip rule made it invisible.
BINDING FROM NOW ON: dot-prefixed directories are still NEVER MOVED and never restructured,
but they MUST BE SEARCHED as invocation sites. Before calling anything dead, grep the module
name across `.github/**`, `.pre-commit-config.yaml`, and any other dot-file that can invoke
(`.gitlab-ci.yml`, `.vscode/tasks.json`, `.claude/**` command definitions, Makefiles, shell
scripts). A CI step is a caller. This is the GM's own principle applied to the GM's own rule:
where the rule and the requirement disagree, the requirement wins — the requirement is
"verify nothing is hiding", and a rule that hides callers defeats it.
