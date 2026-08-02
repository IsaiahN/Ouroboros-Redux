"""nexus.live_test -- the actual validation: play ARC-AGI-3 LIVE public-set games.

This is the "then we test against the ARC live public set" step. It requires ARC_API_KEY in the
environment (env-only, never written to disk) and network access, so it is NOT run by the offline
test suite. It reaches the live gate through the kernel's own harness via LiveArcGround.

Usage:
    export ARC_API_KEY="..."         # env-only
    python3.12 -m nexus.live_test GAME_ID [GAME_ID ...]

The gate metric is levels_completed per game (paper §16.7). A single run is never a verdict -- its
job is to teach (kernel RULE 0.7). No result is fabricated; whatever the environment returns is what
is reported, including the scorecard view_url.
"""
from __future__ import annotations
import sys
from .ground.live_arc import LiveArcGround


def main(argv):
    if not argv:
        print("usage: python3.12 -m nexus.live_test GAME_ID [GAME_ID ...]")
        print("       (requires ARC_API_KEY in env)")
        return 2
    g = LiveArcGround()
    if not g.has_key():
        print("ARC_API_KEY not set -- export it (env-only) and retry.")
        return 1
    total = 0
    for gid in argv:
        r = g.play(gid)
        lv = r.get("levels_completed", 0)
        total += lv
        print(f"{gid:16s} levels_completed={lv}  outcome={r.get('outcome')}  scorecard={r.get('view_url')}")
    print(f"\nTOTAL levels_completed across {len(argv)} game(s): {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
