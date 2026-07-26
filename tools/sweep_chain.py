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

    # ★ THE OPEN DENOMINATOR, GIVEN A COLUMN. Last sweep R_τ filed 25 break events of which 19 had `diff_ran`, so
    # SIX receipts had a dead diff -- but only FOUR segments scored `DIED_PRE_DIFF`. Two counts of the same thing
    # that do not agree is not a mystery to narrate, it is a missing column. There are two different diffs: the
    # receipt's bit is whether the transition/click residual ran on THIS break event, the ledger's bit can also be
    # set by the §3.5 boundary diff at a level advance, which files NO receipt of its own and lands in the NEXT
    # segment. `boundary_diff=yes` is that case, on the record from the boundary's own call site. A row keyed
    # `...|boundary_diff=NO` is a dead-diff receipt on a segment the ledger scored past DIED_PRE_DIFF with NOTHING
    # accounting for it -- that remainder is a DIFFERENT, unexplained finding and must be published as one, not
    # absorbed into this explanation.
    dds = (res.get("tether_chain") or {}).get("echo", {}).get("dead_diff_stages") or {}
    print("\n=== DEAD-DIFF RECEIPTS BY LEDGER STAGE ===")
    if not dds:
        print("  (none: every break-event receipt had its own diff)")
    for k, n in sorted(dds.items()):
        print("    %-40s %d" % (k, n))
    _unex = sum(n for k, n in dds.items() if k.endswith("boundary_diff=NO"))
    if _unex:
        print("  ★ %d dead-diff receipt(s) on segments the ledger scored past DIED_PRE_DIFF with NO boundary diff"
              " to account for them. UNEXPLAINED -- do not fold this into the boundary story." % _unex)

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

    # THE DECISION SITE, AND ITS PREDICTION -- EVALUATED BY THE SCRIPT, BEFORE ANY HUMAN READS THE NUMBER.
    # Written down before this sweep ran (claude/FINDINGS_can_gamma_decide.md): an offline audit of the real Γ
    # found FOUR promoted φ, ZERO of them carrying a sign the live seam could act on, so a correctly-wired
    # decision site MUST take zero actions. A zero here is the wiring behaving as measured. A NON-zero is not a
    # success -- it means Γ signed something the audit says it cannot, and it must be explained before it is
    # celebrated. This is printed as a PASS/INVESTIGATE, never as a score.
    gd = ec.get("gamma_decision") or {}
    print("\n=== Γ -> ACTION (the decision site) ===")
    # ★ THE FUNNEL, NOT THE SINGLE ZERO. The previous sweep printed only `segments where Γ had advice=0` beside a
    # Γ snapshot showing six games ending with a signed directive available, and nothing on the record could say
    # whether the site was never reached, reached without a seam, or reached and offered nothing. Three different
    # findings, three different fixes. Each line below is counted at its own guard inside `_gamma_directive`.
    print("  FUNNEL: site reached=%d -> of those, no calibrated seam=%d | Γ had nothing for this game=%d |"
          " Γ RAISED=%d | Γ had advice=%d"
          % (int(gd.get("steps_reached", 0)), int(gd.get("steps_noseam", 0)), int(gd.get("steps_empty", 0)),
             int(gd.get("steps_error", 0)), int(gd.get("steps_consulted", 0))))
    print("  segments where Γ had advice=%d | steps DIRECTED BY Γ=%d | candidates the seam could not evaluate=%d"
          % (int(gd.get("segments_consulted", 0)), int(gd.get("steps_directed", 0)),
             int(gd.get("unevaluable", 0))))
    _r, _n, _e, _c = (int(gd.get(k, 0)) for k in ("steps_reached", "steps_noseam", "steps_empty", "steps_consulted"))
    _err = int(gd.get("steps_error", 0))
    # ★ NOT FOLDED INTO `_e`. The first draft of this block wrote `_e += _err` so the identity below would still
    # close -- and that made the warning line print a number labelled `empty` that silently contained the raised
    # count. A field that was never that thing, printed under that thing's name, IS a mis-labelled receipt: the
    # exact defect this whole beat exists to close, reappearing inside the printer for the fix. The identity is
    # widened to carry `raised` as its own term instead.

    # ★ THE POOLED FUNNEL IS ITSELF AN AMBIGUOUS NUMBER, AND THIS IS THE ROW THAT CLOSES IT. Last sweep printed
    # `Γ had nothing for this game=18` beside an end-of-run snapshot showing EIGHT games with one signed directive
    # available -- but the 18 was pooled over 25 games, so it could not say whether the entered games were the
    # signed ones at all. Three states, three fixes: the signed games never entered the site (pooling artefact);
    # they entered BEFORE the sign existed (Γ warms up too late -- a timing finding); or they entered with the
    # sign already there and the guard still refused (a DEFECT). One row per game, entry snapshot beside close
    # snapshot, says which. `signed@entry`/`signed@close` are `signed_at_2_families` -- the same bar the guard uses.
    print("\n  PER GAME -- who entered the site, and what Γ had for them WHEN (blank rows omitted):")
    print("    %-18s %7s %7s %6s %6s %7s   %11s %11s" % ("game", "reached", "noseam", "empty", "raised",
                                                         "advice", "signed@entry", "signed@close"))
    _rows = 0
    for gid in sorted(res["results"]):
        g = ((res["results"][gid].get("echo") or {}).get("gamma_decision") or {})
        ent = int((g.get("sign_report_at_first_entry") or {}).get("signed_at_2_families", 0))
        clo = int((g.get("sign_report") or {}).get("signed_at_2_families", 0))
        if not (int(g.get("steps_reached", 0)) or ent or clo):
            continue
        _rows += 1
        print("    %-18s %7d %7d %6d %6d %7d   %11d %11d"
              % (gid, int(g.get("steps_reached", 0)), int(g.get("steps_noseam", 0)), int(g.get("steps_empty", 0)),
                 int(g.get("steps_error", 0)), int(g.get("steps_consulted", 0)), ent, clo))
    if not _rows:
        print("    (no game entered the decision site and none ended with a signed directive)")
    _ents, _entered = int(gd.get("segments_entered_gamma_signed", 0)), int(gd.get("segments_entered", 0))
    _contra = int(gd.get("entry_close_contradiction", 0))
    print("  segments that entered the site=%d | of those, Γ ALREADY SIGNED at entry=%d" % (_entered, _ents))
    if _contra:
        print("  ★ DEFECT: %d segments had a signed directive AT ENTRY and still took the empty branch. The guard"
              " and `sign_report` disagree. CHASE THIS BEFORE READING ANYTHING ELSE HERE." % _contra)
    elif _entered and not _ents:
        print("  READS AS: every entry happened while Γ was UNSIGNED for that game. Any signed directive visible in"
              " the end-of-run snapshot arrived AFTER the site stopped being entered -- a TIMING finding about how"
              " late Γ warms up, NOT a broken guard and NOT a wrong sign bar.")
    if _err:
        print("  ★ Γ RAISED on %d steps -- a BROKEN library, not an empty one. This is swallowed by design so a"
              " run never dies; it must never be read as 'Γ had nothing'." % _err)
    if _r == 0:
        print("  READS AS: the decision site was NEVER ENTERED. Nothing here is a statement about Γ -- look at the"
              " caller (`_act_directional`), not at the library.")
    elif _n == _r:
        print("  READS AS: entered %d times, and EVERY TIME without a calibrated cursor/vectors. This is a"
              " CALIBRATION finding, not a Γ finding." % _r)
    elif _c == 0:
        print("  READS AS: entered %d times with a live seam on %d of them, and Γ offered a signed directive on"
              " NONE. This is the sign bar, working as measured." % (_r, _r - _n))
    if _r != _n + _e + _err + _c:
        print("  ARITHMETIC WARNING: reached(%d) != noseam(%d)+empty(%d)+raised(%d)+advice(%d). A guard is"
              " uncounted." % (_r, _n, _e, _err, _c))
    print("  reuse signal authored by: explains=%d | directive=%d   (never one number: both write the same ledger"
          " bit)" % (int(gd.get("reuse_by_explains", 0)), int(gd.get("reuse_by_directive", 0))))
    for g, sr in sorted((gd.get("sign_report_by_game") or {}).items()):
        print("    %-18s %s" % (g, json.dumps(sr, sort_keys=True)))
    directed = int(gd.get("steps_directed", 0))
    print("  PRE-REGISTERED PREDICTION: 0 steps directed by Γ (no promoted φ carries an agreed cross-family sign)")
    print("  RESULT: %s" % ("PASS -- the prediction held. Γ still cannot decide anything, and now says so with a"
                            " receipt instead of a silence." if directed == 0 else
                            "INVESTIGATE -- %d steps were directed. The offline audit says that should be"
                            " impossible; find out which φ signed and why BEFORE reporting this as progress."
                            % directed))


if __name__ == "__main__":
    main()
