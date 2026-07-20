# Ouroboros — run on a dispatch

## What loads
Submission entrypoint: `integrated_agent.MyAgent(game_id, card=<scorecard_id>)`.
Live path: `online_harness.run_online -> play_game_submission -> integrated_agent.MyAgent ->
my_agent.MyAgent (_QueueAdapter) -> objective_validator.validate_multilevel`.

## Environment
- Python 3.12+ (dev used 3.13). SDK: `pip install arc-agi arcengine arc-agi-3 --break-system-packages`
- scipy required: `pip install scipy --break-system-packages`
- ARC key: env var ONLY -> `export ARC_API_KEY=<key>`   (never in a file)

## Quick run (free run, keeps one agent alive across deaths for N actions, tees the DSL stream)
    export ARC_API_KEY=<key>
    python _proctor_free.py <cap_actions> <wall_seconds> <stream_out.log>
    # e.g. python _proctor_free.py 1000 800 /tmp/free.log
Runners: `_proctor_free.py` (cross-death free run), `_proctor_run.py` (single+tee),
`_proctor_batch.py` (A/B). Score a run: `python ladder_score.py <stream.log>`.

## Flags (env; all default to the verified-good value — leave unset for normal play)
- OURO_WALL_AXIOM=1        wall-pound guard ON (exempts planned pathfinder moves)
- OURO_NAV_ESCALATE=1      "press to the frontier, don't conclude unreachable"
- OURO_FLOOR_INCLUSION=1   plan on perceived floor
- OURO_JOINT_PLAN=1        joint (pos x phase) predicate search, try-first w/ fallback
- OURO_DRIVER_BATON=0      leave OFF: walk/run is agent-chosen from its own stall signal
- OURO_KL_DEBUG=0          diagnostic loci dump -> /tmp/nb/kl_loci.log (OFF for real runs)
- OURO_JOINT_DEBUG=0       joint-plan gate trace (OFF)

## Verified state (20 Jul 2026)
ls20 L0 clears reliably (every generation). L1: pairs with the real box now (phantom fixed),
runs the full match+nav chain; not yet cleared (long maze within budget). No known regressions.
