"""nexus.live_test -- play ARC-AGI-3 LIVE public-set games with the GENERATIONAL runner.

Each game gets its OWN independent run (own scorecard) and lives across many lifetimes: play until
GAME_OVER, RESET into the next generation, carrying the ledger's refuted set so nothing dead is
re-spent. This is the fusion (economy of thought within a lifetime + economy of agents across
lifetimes) over a run-local JSON ledger -- the offline stand-in for v4's generations/database.

Swarm here means PARALLELISM across games (one dedicated agent per game), NOT cross-game transfer.

Usage (requires ARC_API_KEY in env):
    python3.12 -m nexus.live_test GAME_ID [GAME_ID ...] [--generations N] [--actions M] [--wall S]

Reports only what the ground returns (best_level per game) + the ledger path per game.
"""
from __future__ import annotations
import os, sys
from .generational import GenerationalRunner


def main(argv):
    games = [a for a in argv if not a.startswith("--")]
    def opt(name, default):
        if name in argv:
            return type(default)(argv[argv.index(name) + 1])
        return default
    if not games:
        print("usage: python3.12 -m nexus.live_test GAME_ID [...] [--generations N] [--actions M] [--wall S]")
        return 2
    if not os.environ.get("ARC_API_KEY"):
        print("ARC_API_KEY not set -- export it (env-only) and retry.")
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
