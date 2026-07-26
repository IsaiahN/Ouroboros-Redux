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
from newhorse.redux_arch.receipt import ResidualEvent, render_one, firings


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
    # `maxL` is the CARRIER-REACH column: a within-run-across-levels echo needs a run that crosses TWO boundaries
    # (mint at 0->1, then REACH 1->2 to offer it). If no game shows maxL>=2, that carrier has zero live instances
    # and wiring it would ship a correct, inert mechanism. Printed per game so the claim is checkable, not asserted.
    print("\n%-18s %-14s %5s %6s %6s %6s %6s %6s  %s"
          % ("game", "family", "maxL", "stalls", "adv", "resid", "mint", "fired", "furthest stage"))
    for gid in sorted(res["results"]):
        r = res["results"][gid]
        ts = r.get("tether_stage") or {}
        ec = r.get("echo") or {}
        print("%-18s %-14s %5s %6s %6s %6s %6s %6s  %s"
              % (gid, r.get("family"), r.get("levels"), ts.get("stalls"), ts.get("advances"),
                 ec.get("residual_nonempty"), ec.get("minted"), ec.get("fired"), ts.get("furthest_stage")))
    print("\n=== POOLED TETHER-STAGE DISTRIBUTION ===")
    print(json.dumps(res.get("tether_chain"), indent=2, sort_keys=True))

    # DIRECTIVE 5: a firing is a RECEIPT, not a claim. Every transfer is rendered in full, with its echo KIND and
    # the caveat that a within-game echo is a weaker claim than a cross-game one. No receipt => it did not fire.
    print("\n=== FIRING RECEIPTS ===")
    evs = []
    for gid in sorted(res["results"]):
        for d in (res["results"][gid].get("firings") or []):
            evs.append(ResidualEvent(**{k: v for k, v in d.items() if k != "fired"}))
    for e in firings(evs):
        print(render_one(e))
    # THE DENOMINATOR MUST BE THE SWEEP'S, NOT THE SHIPPED FIRINGS'. Only FIRING receipts cross the process
    # boundary (a full per-event dump would be megabytes), so `summary_line(evs)` here would count only firings and
    # print "break events=0" on a sweep that had nineteen of them -- a silence rendered as a zero. The pooled echo
    # block is computed inside each policy over EVERY break event, so it is the honest count of what did not fire.
    ec = (res.get("tether_chain") or {}).get("echo") or {}
    if not evs:
        print("NO FIRING. Not a claim about the architecture -- a count over EVERY break event in this sweep:")
    print("  break events=%d | residual computed=%d | non-empty=%d | minted=%d | promoted into Γ=%d | "
          "offered to Γ=%d | FIRED=%d | cleared=%d"
          % (ec.get("break_events", 0), ec.get("diff_ran", 0), ec.get("residual_nonempty", 0),
             ec.get("minted", 0), ec.get("promoted", 0), ec.get("reuse_attempted", 0),
             ec.get("fired", 0), ec.get("cleared", 0)))

    # THE SHARED-Γ UNDO, PRE-REGISTERED BEFORE THIS SWEEP AND EVALUATED BY THE SCRIPT, NOT BY THE READER.
    # Written down before the run: "a cross-game Γ is worth keeping only if reuse_attempted > 0 AND a promoted φ is
    # offered on a game it was not minted on. If Γ fills but reuse_attempted stays 0, the wiring is decorative and
    # reverts." Printing the verdict here is the point -- a criterion a human evaluates after seeing the numbers is
    # a criterion that gets met.
    att, foreign = int(ec.get("reuse_attempted", 0)), int(ec.get("reuse_attempted_foreign", 0))
    keep = att > 0 and foreign > 0
    print("\n=== SHARED-Γ PRE-REGISTERED UNDO ===")
    print("  offered to Γ=%d | of those, offered a φ minted on ANOTHER GAME=%d" % (att, foreign))
    print("  VERDICT: %s" % ("KEEP -- Γ crossed a game boundary at the offer site." if keep else
                             ("REVERT -- Γ filled but nothing was ever offered: decorative wiring."
                              if att == 0 else
                              "REVERT -- every offer was same-game: the SHARING bought nothing, only the library did.")))
    print("  This says nothing about whether φ EXPLAINED anything (fired=%d) -- an offer is an opportunity, not a"
          " transfer." % int(ec.get("fired", 0)))


if __name__ == "__main__":
    main()
