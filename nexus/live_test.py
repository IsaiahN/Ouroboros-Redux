"""nexus.live_test -- play ARC-AGI-3 LIVE public-set games with the GENERATIONAL runner.

Each game gets its OWN independent run (own scorecard) and lives across many lifetimes: play until
GAME_OVER, RESET into the next generation, carrying the ledger's refuted set so nothing dead is
re-spent. This is the fusion (economy of thought within a lifetime + economy of agents across
lifetimes) over a run-local JSON ledger -- the offline stand-in for v4's generations/database.

Swarm here means PARALLELISM across games (one dedicated agent per game), NOT cross-game transfer.

Usage (online -- requires ARC_API_KEY in env):
    python3.12 -m nexus.live_test GAME_ID [GAME_ID ...] [--generations N] [--actions M] [--wall S]
Usage (OFFLINE -- no key, local game pack, ~25x faster/step):
    python3.12 -m nexus.live_test GAME_ID [...] --offline   (uses OURO_ENV_DIR, default /tmp/environment_files)

Reports only what the ground returns (best_level per game) + the ledger path per game.
"""
from __future__ import annotations
import os, sys
from .generational import GenerationalRunner


def main(argv):
    # A game id is a positional token that is NOT a flag AND NOT the value that follows a value-taking flag
    # (--generations 2 etc). The old `[a for a in argv if not a.startswith("--")]` swept those values in as
    # bogus game ids ("2", "40"), which then failed the offline lookup -- fixed here.
    _VALUE_FLAGS = {"--generations", "--cap", "--stall", "--wall", "--actions"}
    games = [a for i, a in enumerate(argv)
             if not a.startswith("--") and not (i > 0 and argv[i - 1] in _VALUE_FLAGS)]
    def opt(name, default):
        if name in argv:
            return type(default)(argv[argv.index(name) + 1])
        return default
    if not games:
        print("usage: python3.12 -m nexus.live_test GAME_ID [...] [--offline] [--generations N] [--actions M] [--wall S]")
        return 2
    # --offline: play the SAME nexus engine (generational + sensorium + kernel over the real Γ) against the LOCAL
    # game pack via Arc3Session's offline branch -- no ARC_API_KEY, no network, ~25x faster/step. run_online builds
    # the Arc3Session, which reads OURO_OFFLINE, so the only change needed is to set the env and skip the key guard.
    offline = "--offline" in argv
    if offline:
        os.environ["OURO_OFFLINE"] = "1"
        os.environ.setdefault("OURO_ENV_DIR", "/tmp/environment_files")
    elif not os.environ.get("ARC_API_KEY"):
        print("ARC_API_KEY not set -- export it (env-only) and retry, or pass --offline for the local game pack.")
        return 1

    gens = opt("--generations", 20)
    cap = opt("--cap", 500)            # hard ceiling per lifetime (infinite games); death/stall reset earlier
    stall = opt("--stall", 60)         # reset after this many steps with no new board state and no level
    wall = opt("--wall", 3600.0)
    runner = GenerationalRunner()
    total = 0
    for gid in games:
        r = runner.run_online(gid, max_generations=gens, hard_cap=cap, stall_patience=stall, wall_cap_s=wall)
        total += r.get("best_level", 0) or 0
        print(f"{gid:16s} best_level={r.get('best_level')} gens={r.get('generations')} "
              f"steps={r.get('steps')} outcome={r.get('outcome')} scorecard={r.get('view_url')}")
        print(f"                 ledger={r.get('ledger')}  refuted={len(r.get('summary',{}).get('refuted',[]))}")
    print(f"\nTOTAL best_level across {len(games)} game(s) = {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
