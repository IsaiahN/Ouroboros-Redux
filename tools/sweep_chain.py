"""sweep_chain.py -- run the whole environment set and print the MEASURED TETHER-STAGE distribution.

"You currently have no idea which link breaks -- 'detection is inert' is a guess about stage 1." This is the script
that replaces the guess with a count. It plays every environment the API offers, pools every per-stall stage code
from every game, and prints where the chain actually dies and how often.

It hardcodes NO game id -- the set comes from the API -- and it tunes nothing. It is a MEASUREMENT: read what it
says, however low, and do not build the chain to make it read higher.

    export ARC_API_KEY=...            # env-only, never written to a file
    PYTHONPATH=src python3.12 tools/sweep_chain.py [max_actions] [wall_cap_s]
"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from newhorse.redux_arch.sdk_guard import assert_online_sdk
from newhorse.redux_arch.swarm import run_swarm


def environment_ids():
    import arc_agi
    from arc_agi.base import OperationMode
    arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE, arc_api_key=os.environ["ARC_API_KEY"])
    out = []
    for e in arc.available_environments:
        gid = getattr(e, "game_id", None) or getattr(e, "name", None) or str(e)
        out.append(str(gid))
    return sorted(set(out))


def main() -> None:
    assert_online_sdk()
    if not os.environ.get("ARC_API_KEY"):
        raise SystemExit("ARC_API_KEY not set -- env-only")
    max_actions = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    wall_cap_s = float(sys.argv[2]) if len(sys.argv) > 2 else 200.0
    gids = environment_ids()
    print("sweeping %d environments (max_actions=%d wall_cap=%.0fs)" % (len(gids), max_actions, wall_cap_s))

    res = run_swarm(gids, max_actions=max_actions, wall_cap_s=wall_cap_s, rpm=540, max_workers=8,
                    tags=["redux-triality", "chain-sweep"])

    print("\nscorecard: %s" % res.get("view_url"))
    print("total_levels: %s" % res.get("total_levels"))
    print("\n%-18s %-14s %6s %6s %6s  %s" % ("game", "family", "levels", "stalls", "adv", "furthest stage"))
    for gid in sorted(res["results"]):
        r = res["results"][gid]
        ts = r.get("tether_stage") or {}
        print("%-18s %-14s %6s %6s %6s  %s" % (gid, r.get("family"), r.get("levels"),
                                               ts.get("stalls"), ts.get("advances"), ts.get("furthest_stage")))
    print("\n=== POOLED TETHER-STAGE DISTRIBUTION ===")
    print(json.dumps(res.get("tether_chain"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
