# Self-running loop (unattended)

The clean way to keep the agent playing without a human launching it each time — and **without the ARC
key ever leaving GitHub**.

## The shape of it

The instinct "expose the key so the proctor can grab it" is backwards: every path that carries a live
credential out to the proctor (a build log, an artifact, a commit) leaves it somewhere broader and more
permanent than a secret should ever sit. So we invert it. **The agent runs where the key already is; the
proctor consumes only what the agent commits back.**

- `ARC_API_KEY` lives as a **repository secret** (Settings → Secrets and variables → Actions → *Secrets*).
  A secret, not a variable — GitHub masks it in logs and never lets it into the tree.
- `.github/workflows/agent-loop.yml` runs on a schedule (and on manual dispatch). GitHub injects the
  secret into the runner as `$ARC_API_KEY`, env-only. `bootstrap.sh` installs the SDK; `ci_run.py` plays
  the game(s) live.
- The job commits **only `results/<run_number>/`** back to the repo — `summary.json` plus the agent's own
  DSL narration (`<game>.stream.log`). The key is never printed, so it never appears there.
- The proctor (in a Cowork session, attended or scheduled) clones the repo, reads `results/`, diagnoses
  under LAW 0 (render the frame, check for phantoms first), edits the pipeline, and pushes code changes to
  `main`. The next scheduled run picks them up. That is the whole loop.

## Turning it on

1. On `IsaiahN/Ouroboros-Redux`, add the repo secret **`ARC_API_KEY`** = the online key.
2. That's it. The schedule (`cron: "0 */6 * * *"`, every 6h UTC) starts firing. To run one now:
   Actions → **agent-loop** → *Run workflow* (optionally set `games`, `mode`, `cap`, `wall`).

## Knobs (workflow inputs / env)

| var          | default | meaning                                              |
|--------------|---------|------------------------------------------------------|
| `OURO_GAMES` | `ls20`  | comma-separated game ids                             |
| `OURO_MODE`  | `free`  | `free` = one agent across deaths (depth) · `sweep` = one pass per game (breadth) |
| `OURO_CAP`   | `1500`  | actions cap per game                                 |
| `OURO_WALL`  | `1200`  | wall-seconds cap per game                            |

`free` is the mode that matters for getting a single game's reasoning up: cross-life memory (cmap,
refutation ledger, persistent model, self-assessment) persists across restarts in `GLOBAL_KNOWLEDGE`, so
the agent evolves across generations within one run. `sweep` is for breadth once several games are in play.

## The rule this loop must never break

`ci_run.py` and the workflow only ever **run** the agent and **record** what it did. Every change to how
the agent *reasons* is a pipeline edit made by the proctor under LAW 0 — never an answer encoded into the
runner, never a game mechanic baked into CI. The loop is plumbing; the reasoning stays the agent's.
