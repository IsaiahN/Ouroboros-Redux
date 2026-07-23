# Honesty tripwires — how to audit this build without trusting the LLM's word

The build loop runs unattended (hourly heartbeats). The agent's *progress* is tethered to a real external ground
you cannot fake — the live ARC eval (`levels_completed` on the scorecards). But the axis the LLM (the model
building this) cannot honestly police about **itself** is: *am I feeding the agent answers / drifting the
architecture?* — because it is both the builder and the self-reporter there (Tether §1.5: a frame cannot grade its
own exam). These two tripwires externalise that check into rules the LLM cannot argue with, so you can step back and
**audit on return** instead of trusting the ledger narration.

## 1. Answer-encoding linter (`redux_arch/answer_lint.py`, enforced by `tests/test_answer_lint.py`)
A mechanical rule, no judgement: the agent-logic modules (policy, coupled, replay, click, goal, planner, bridge,
explore, dsl, minting, consolidate) may **not** contain a game-id literal, a known dev game-code used in logic, or
behaviour that branches on `game_id`. If a future beat special-cases a game, the suite goes **RED** and it shows up
in the git diff you read. Runners/adapters are exempt (they name games as default args only). Run it yourself:
`PYTHONPATH=src python -m newhorse.redux_arch.answer_lint`.

## 2. Novelty-claim parking (`redux_arch/novelty_ledger.py`, enforced by `tests/test_novelty_ledger.py`)
A **NOVEL** predicate mint is the one verdict the build must never self-certify. Every promotion goes through
`guarded_promote()`: a RE-DERIVATION passes (it invents nothing); a NOVEL is appended to `docs/NOVELTY_CLAIMS.jsonl`
flagged UNCONFIRMED and the build is **not allowed to act on it**. You confirm a claim only after reviewing it, by
writing its key into `docs/NOVELTY_CONFIRMED.txt` (human-only). Until then it is parked.

## What to check when you come back
- **Scorecards** (external, unfakeable): the `view_url`s in the ledger / commit messages — open them.
- **git diffs** (append-only, pushed): every beat is a readable commit; the linter would have caught encoded answers.
- **recordings/** (raw frames): the ground truth of what actually happened on the board.
- **`docs/NOVELTY_CLAIMS.jsonl`**: any frontier claim the build wants to make is here, UNCONFIRMED, awaiting you.
- Trust these over `claude/HEARTBEAT.md`, which is the LLM's own narration.

## What these do NOT do (honest)
They make the loop **auditable and bounded**, not **self-correcting**. If the LLM drifts subtly in a way no rule
catches, nothing in the loop stops it while you are away — but the grounds above let you catch it on return, and the
blast radius is bounded to the `redux-triality` branch (reversible). Real independence (a *different* checker, not
this same model auditing itself 4-hourly) is the remaining gap.
