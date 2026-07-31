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
    report(res)


# The per-action floor the self-motion classifier requires before a spread counts as a finding. Set here, printed
# in the section header, so a reader never has to guess whether a 0%-100% split came from two steps or two hundred.
_MIN_ACT_N = 5


def report(res: dict) -> None:
    """Render one sweep's result dict. SEPARATE FROM `main` on purpose: a printer bug in this file has twice been
    discovered only after a live sweep had already been spent on it, and a printer that can only be exercised by
    spending a sweep is a printer that gets debugged in production. Split out, it can be driven offline from real
    `summary()`/`echo_pool()` output, which is what `tests/test_sweep_report.py` does."""
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

    # ★★★ THE HEADLINE, AND WHICH OF THE TWO READINGS IT CAME FROM. THREE BEATS OWED. ★★★
    # `indicts` used to be `indicts(Stage[worst])` -- the deepest stall, alone. It printed "architecture" on sweeps
    # A/B and "drive" on C, flipping on nothing but residual-bank warmth, while the funnel below said those very
    # segments resolved at a `no_eligible` branch. The stage reading is KEPT, under `indicts_worst_stage`, so the
    # two can be compared instead of one quietly replacing the other; when they DISAGREE that is the finding, and
    # it is printed as one rather than left for a reader to notice.
    _tc = res.get("tether_chain") or {}
    print("\n=== WHAT THE SWEEP INDICTS (branch reading vs stage reading) ===")
    print("  indicts=%s   (source=%s, scope=%s, attempts=%s)"
          % (_tc.get("indicts"), _tc.get("indicts_source"), _tc.get("indicts_scope"), _tc.get("indicts_attempts")))
    print("  indicts_worst_stage=%s   (worst_stage=%s)"
          % (_tc.get("indicts_worst_stage"), _tc.get("worst_stage")))
    for _l, _n in sorted((_tc.get("indicts_layers") or {}).items()):
        print("    %-18s %6d attempts" % (_l, int(_n)))
    if _tc.get("indicts_unmapped"):
        print("  ★ UNMAPPED BRANCHES -- a literal was added without a layer, so NO verdict is claimed: %s"
              % dict(_tc["indicts_unmapped"]))
    if _tc.get("indicts_source") == "reuse_funnel" and _tc.get("indicts") != _tc.get("indicts_worst_stage"):
        print("  ★ THE TWO READINGS DISAGREE. The stage name covers more than one branch, so the BRANCH reading is"
              " the attribution and the stage reading is only the depth. Cite `indicts` with its scope, never the"
              " stage word on its own.")

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

    # ★★★ THE DECIDE FUNNEL -- WHICH `return` ANSWERED, AND ON HOW MANY GAMES. ★★★
    # This block exists because of last beat's finding: the Γ decision site was entered on ONE game out of
    # twenty-four, and for two beats its zero was read as a statement about Γ when it was a statement about the
    # agent's own control flow. `steps` is what each exit answered; `games` is how many DIFFERENT games it
    # answered on -- printed together because a pooled step count cannot say which. `dir_*` rows are the exits
    # inside `_act_directional`; everything else exits before the family dispatch is even reached.
    dfn = (res.get("tether_chain") or {}).get("echo", {}).get("decide_funnel") or {}
    dfx, dfg = (dfn.get("exits") or {}), (dfn.get("exit_games") or {})
    print("\n=== DECIDE FUNNEL (which return answered, counted at its own exit site) ===")
    _calls = int(dfn.get("calls", 0))
    if not dfx:
        print("  (no decisions recorded)")
    # ★ REACH IS NOT COMPETENCE. `answered` prices each exit's steps: of the ones whose RESULT FRAME was seen and
    # whose action the survival veto did not replace, on how many did the board actually change? MASKED is the
    # reading that matters (the monotone budget/timer band is removed first); RAW is printed beside it because a
    # raw-only column reads ~100% on any game with a ticking bar, and seeing the two apart is how you tell a
    # responsive board from a ticking one. `unpriced` steps are excluded from the denominator, not scored as null.
    dfa, dfm, dfr, dfv = ((dfn.get("attr") or {}), (dfn.get("moved") or {}),
                          (dfn.get("moved_raw") or {}), (dfn.get("veto") or {}))
    for k, n in sorted(dfx.items(), key=lambda kv: (-kv[1], kv[0])):
        _a = int(dfa.get(k, 0))
        _pr = ("answered %5.1f%% masked / %5.1f%% raw  of %5d priced"
               % (100.0 * int(dfm.get(k, 0)) / _a, 100.0 * int(dfr.get(k, 0)) / _a, _a)) if _a else \
              "answered      --  (NOTHING PRICED)          "
        print("    %-22s steps %7d (%5.1f%%)   games %3d   %s   veto %4d"
              % (k, n, 100.0 * n / max(1, _calls), int(dfg.get(k, 0)), _pr, int(dfv.get(k, 0))))
    _pa, _pv, _pu = sum(dfa.values()), sum(dfv.values()), int(dfn.get("unpriced", 0))
    print("  priced=%d | veto-replaced=%d | unpriced=%d | exits=%d | RESIDUE=%d"
          % (_pa, _pv, _pu, sum(dfx.values()), sum(dfx.values()) - _pa - _pv - _pu))
    if sum(dfx.values()) - _pa - _pv - _pu:
        print("  ★ THE OUTCOME COLUMN DOES NOT CLOSE against the exit counts. Do not read any `answered` number"
              " until the residue is named.")
    print("  decide() calls=%d | exits counted=%d | UNCOUNTED=%d" % (_calls, sum(dfx.values()),
                                                                     int(dfn.get("uncounted", 0))))
    if int(dfn.get("uncounted", 0)):
        print("  ★ IDENTITY BROKEN: a `return` in the decision path is not counted at its own site. Every number in"
              " this block is a floor, not a measurement, until that exit is named.")
    _below = int(dfn.get("gamma_site_reach_from_below", 0))
    _dis = int(dfn.get("gamma_site_reach_disagreement", 0))
    print("  Γ site reach measured FROM BELOW (dir_gamma+dir_explore)=%d | disagreement with `gamma_reached`=%d"
          % (_below, _dis))
    if _dis:
        print("  ★ TWO COUNTERS OF ONE EVENT DISAGREE by %d. One of them is wrong; neither may be cited until the"
              " difference is explained." % _dis)

    # ★★★ THE ESCALATION BRANCH -- WHERE `escalate`'s STEPS ACTUALLY COME FROM. ★★★
    # `escalate` + `escalate_click` hold ~1 decision in 7 and answer ~1 step in 20, uniform across every game they
    # touch. A rate that low and that flat is a statement about the ORGAN, not about seven boards -- but the exit
    # name cannot say which of `_modality_escalate`'s three returns produced the step, so the rate has been
    # unattributable. These counts come from those three returns, written there as string literals. Read them as:
    #   new           a genuine modality switch -- the lever firing, once per switch
    #   hold_untried  serving the SAME label again while its fair trial completes: the designed cost of a switch,
    #                 bounded by the engagement window
    #   hold_answered serving the same label again AFTER it has answered at least once. Now reachable ONLY by A6
    #                 on the step its click commit lands; every later A6 decision is caught by the natively-routed
    #                 click exit. A DIRECTIONAL label that answers is RELEASED instead (below).
    #   released_answered  the label answered, so it is not a null intervention and there is nothing left to
    #                 refuse: `_escalated` is cleared and the game handed back to its family organ. This return
    #                 produces NO escalate step, so it is OUTSIDE the identity, printed separately, and its size
    #                 is the direct read on how much of the old lock-in has been converted into a hand-back.
    esb = (dfn.get("esc_branch") or {})
    _NOSTEP = ("released_answered",)
    _esc_steps = int(dfx.get("escalate", 0)) + int(dfx.get("escalate_click", 0))
    print("\n=== THE ESCALATION BRANCH (which return of _modality_escalate produced the step) ===")
    if not esb:
        print("  (no escalation branch recorded -- the organ never returned an action this sweep)")
    for k in ("new", "hold_untried", "hold_answered"):
        _n = int(esb.get(k, 0))
        print("    %-14s steps %7d (%5.1f%% of escalate steps)"
              % (k, _n, 100.0 * _n / max(1, _esc_steps)))
    for k in _NOSTEP:
        print("    %-14s      %7d   (NO step: handed back to the family organ -- outside the identity below)"
              % (k, int(esb.get(k, 0))))
    for k, n in sorted(esb.items()):
        if k not in ("new", "hold_untried", "hold_answered") + _NOSTEP:
            print("    %-14s steps %7d   ★ UNNAMED BRANCH -- added without a reading" % (k, int(n)))
    _res = int(dfn.get("esc_branch_residue", 0))
    _step_sum = sum(v for k, v in esb.items() if k not in _NOSTEP)
    print("  escalate steps=%d | step-branch sum=%d | RESIDUE=%d" % (_esc_steps, _step_sum, _res))
    if _res:
        print("  ★ THE BRANCH SPLIT DOES NOT SUM TO THE ESCALATE EXITS. Do not read any row above until the"
              " residue is named.")
    else:
        _new, _hu, _ha = (int(esb.get("new", 0)), int(esb.get("hold_untried", 0)),
                          int(esb.get("hold_answered", 0)))
        if not _esc_steps:
            print("  VERDICT: MUTE -- the escalation organ produced no steps this sweep.")
        else:
            if _new:
                print("  mean steps per switch: %.1f held-untried + 1 new = %.1f (engagement window is the"
                      " intended bound on the untried part)" % (_hu / float(_new), _hu / float(_new) + 1.0))
            else:
                # ★ NOT a reason to mute the verdict. These counters are SEGMENT-scoped, so a hold that began in
                # an earlier segment arrives here with no switch beside it -- which is precisely the long tail a
                # lock-in produces. Muting on `new == 0` would suppress the reading exactly where it matters.
                print("  no switch counted in these segments -- the held label was escalated to earlier; the"
                      " steps-per-switch ratio is unavailable, the split below is not")
            _rel = int(esb.get("released_answered", 0))
            print("  released=%d hand-backs vs %d escalate steps -- %.2f hand-backs per escalate step. This is the"
                  " lock-in's replacement: every one of these was a `hold_answered` step before the release."
                  % (_rel, _esc_steps, _rel / float(max(1, _esc_steps))))
            if _ha >= 0.5 * _esc_steps:
                print("  VERDICT: LOCK-IN DOMINATES -- %.1f%% of escalate's steps re-serve a label that has"
                      " ALREADY answered, which `failed_trial` can never end. The organ built to refuse a null"
                      " intervention is itself the null intervention on those steps." % (100.0 * _ha / _esc_steps))
            elif _hu >= 0.5 * _esc_steps:
                print("  VERDICT: FAIR-TRIAL WAIT DOMINATES -- %.1f%% of escalate's steps are the bounded cost of"
                      " confirming a negative. The low answer rate is the PRICE OF THE TRIAL, not a lock-in."
                      % (100.0 * _hu / _esc_steps))
            else:
                print("  VERDICT: MIXED -- neither branch holds half the steps; both readings stay open.")

    # ★★★ THE CLICK BRANCH -- WHY THIS CLICK. THE LARGEST UN-ATTRIBUTED THING THE AGENT DOES. ★★★
    # `click_native` alone took 45.4% of every decision last sweep, and it is ONE exit name over FOUR different
    # `return`s inside `ClickProber.choose`. An exit name covering more than one return is not an attribution
    # (RANKING 5) -- the same defect the escalation branch had, one organ over, at three times the size. These
    # counts are string literals written at those four returns. Read them as:
    #   untried_perceptual        blind enumeration of a point PERCEPTION proposed (a `click_targets` centroid)
    #   untried_sweep             blind enumeration of a `grid_sweep` LATTICE point -- nobody proposed it
    #   untried_refresh           blind enumeration of a point `refresh()` folded in after the board changed
    #   exploit_scored            the learned choice -- a target whose `novel`/`changed` history out-ranks the rest
    #   nothing_moved_least_tried the fallback: NOTHING the prober ever clicked moved the board, so it round-robins
    #   no_targets                the degenerate corner click: perception offered no candidate at all
    # ★ MIGRATION, NAMED: the first six sweeps published `untried_first` as ONE row holding 96.3% of every click.
    # It was itself an exit name over more than one cause and it is GONE; the three `untried_*` rows replace it and
    # their sum is printed below so the old series stays comparable. Do not silently re-add the old name.
    # ★ PRE-REGISTERED PREDICTION (written 2026-07-30, BEFORE any sweep at this commit; evaluated below by the
    # script itself, never by the prose afterwards). The claim this REPLACES was "`refresh()` replenishes the
    # untried queue faster than it drains" -- an untested mechanism that no receipt ever supported. The offline
    # bound in docs/tether/EVIDENCE_the_click_pool_floor.md says the CONSTRUCTION POOL alone forces 61.4%-83.8%
    # of sweep G's 1393 click steps, before `refresh` can contribute anything, because `choose` drains
    # `self.targets` in admission order and refresh arrivals sit at the END of that list. So:
    #   A. `untried_perceptual` + `untried_sweep` >= 50% of click steps, and `untried_sweep` > `untried_perceptual`
    #      (perception offers <=24 points, the lattice adds 64).
    #   B. `untried_refresh` <= 40% of click steps.
    # OVERTURNED IF `untried_refresh` exceeds the construction pair -- that would reinstate the replenishment
    # reading and the offline bound would be wrong. Published either way.
    cbr = (dfn.get("click_branch") or {})
    cpl = (dfn.get("click_pool") or {})
    _CB_NAMED = ("untried_perceptual", "untried_sweep", "untried_refresh", "exploit_scored",
                 "nothing_moved_least_tried", "no_targets")
    _clk_steps = int(dfx.get("click_native", 0)) + int(dfx.get("escalate_click", 0))
    print("\n=== THE CLICK BRANCH (which return of ClickProber.choose produced the click) ===")
    if not cbr:
        print("  (no click branch recorded -- the prober never chose a target this sweep)")
    for k in _CB_NAMED:
        _n = int(cbr.get(k, 0))
        print("    %-26s steps %7d (%5.1f%% of click steps)"
              % (k, _n, 100.0 * _n / max(1, _clk_steps)))
    for k, n in sorted(cbr.items()):
        if k not in _CB_NAMED:
            print("    %-26s steps %7d   ★ UNNAMED BRANCH -- added without a reading" % (k, int(n)))
    _u_perc, _u_swp = int(cbr.get("untried_perceptual", 0)), int(cbr.get("untried_sweep", 0))
    _u_ref = int(cbr.get("untried_refresh", 0))
    _u_all = _u_perc + _u_swp + _u_ref
    print("    %-26s steps %7d (%5.1f%% of click steps)   [was one row: `untried_first`]"
          % ("untried_* TOTAL", _u_all, 100.0 * _u_all / max(1, _clk_steps)))
    _cres = int(dfn.get("click_branch_residue", 0))
    print("  click steps=%d | branch sum=%d | RESIDUE=%d" % (_clk_steps, sum(cbr.values()), _cres))
    # THE POOL, on its own denominator. These are ADMISSIONS, never steps, and they are printed under the branch
    # split only because they are what BOUNDS it -- a prober cannot leave the untried branch until every admitted
    # target has been tried once, so `ctor_targets` per prober is a hard floor on forced enumeration.
    if cpl:
        _ctp, _cts = int(cpl.get("ctor_perceptual", 0)), int(cpl.get("ctor_sweep", 0))
        _ctt, _cpr = int(cpl.get("ctor_targets", 0)), int(cpl.get("ctor_probers", 0))
        _rfa, _rfc = int(cpl.get("refresh_admitted", 0)), int(cpl.get("refresh_calls", 0))
        _pres = int(dfn.get("click_pool_ctor_residue", 0))
        print("  POOL (admissions, NOT steps): probers built=%d | at construction: perceptual=%d + sweep=%d ="
              " targets=%d (%.1f per prober) | de-dup RESIDUE=%d"
              % (_cpr, _ctp, _cts, _ctt, _ctt / float(max(1, _cpr)), _pres))
        print("       refresh: %d calls admitted %d further targets (%.2f per call). The construction pool is"
              " drained FIRST -- refresh arrivals sit at the end of `targets`." % (_rfc, _rfa, _rfa / float(max(1, _rfc))))
        # ★ THE DRAIN, on the ADMISSIONS denominator. The branch rows above are a rate over STEPS and a rate can be
        # right about the size of a cost while being silent about its CAUSE (PATTERN 07-30g). These two rates are
        # the ordering claim itself: if `choose` really drains `targets` in admission order, then the construction
        # admissions must be spent MUCH more completely than the refresh admissions, because the latter can only be
        # reached after the former is exhausted. Same sweep, different denominator, so it can disagree.
        _ctor_steps = _u_perc + _u_swp
        print("       DRAIN (steps taken per target ADMITTED): construction %d/%d = %.1f%% | refresh %d/%d = %.1f%%"
              % (_ctor_steps, _ctt, 100.0 * _ctor_steps / float(max(1, _ctt)),
                 _u_ref, _rfa, 100.0 * _u_ref / float(max(1, _rfa))))
        if _pres:
            print("  ★ THE POOL DOES NOT CLOSE: the two origins do not sum to the targets admitted. Do not read"
                  " the untried rows -- a target was admitted without an origin.")
    else:
        print("  POOL: (not recorded -- no prober was constructed this sweep)")
    # ★ WHICH MEMBERS. The branch split above is POOLED, and a pooled number offered as evidence about a subset is
    # the mis-labelled-receipt defect one level up (RANKING 5). The per-game carry already exists as a sibling of
    # `decide_funnel`; this reads it rather than adding a second traversal that could drift from the pooler.
    _fbg = (res.get("tether_chain") or {}).get("echo", {}).get("decide_funnel_by_game") or {}
    _PL_NAMED = ("ctor_probers", "ctor_perceptual", "ctor_sweep", "ctor_targets",
                 "refresh_calls", "refresh_admitted")
    _rows = []
    for _g, _xs in sorted(_fbg.items()):
        _r = {k: int((_xs.get(k) or {}).get("click_branch", 0)) for k in _CB_NAMED}
        _p = {k: int((_xs.get(k) or {}).get("click_pool", 0)) for k in _PL_NAMED}
        if sum(_r.values()) or sum(_p.values()):
            _rows.append((_g, _r, _p))
    if _rows:
        print("  PER GAME (%d of %d games took a click step):" % (len(_rows), len(_fbg)))
        for _g, _r, _p in _rows:
            _tot = sum(_r.values())
            print("    %-18s steps %5d | perc %4d  sweep %4d  refresh %4d  exploit %4d  nomove %4d  notgt %4d"
                  % (_g, _tot, _r["untried_perceptual"], _r["untried_sweep"], _r["untried_refresh"],
                     _r["exploit_scored"], _r["nothing_moved_least_tried"], _r["no_targets"]))
        # ★ WHICH MEMBERS, ON THE ADMISSIONS DENOMINATOR. The pooled drain above is exactly the pooled-number defect
        # if it is offered as evidence about the ORDERING, because one game that never spent its pool and one game
        # that spent it twice average to something that describes neither. A game at 100% construction drain is a
        # DIRECT observation that every admitted construction target was clicked before any refresh arrival was
        # reached; that is the ordering claim, per game, with nothing pooled.
        print("  PER GAME, THE POOL (admissions, NOT steps -- `full` = the construction pool was spent to the last"
              " target before any refresh arrival was reachable):")
        _full = 0
        for _g, _r, _p in _rows:
            _t, _pr = _p["ctor_targets"], _p["ctor_probers"]
            _cs = _r["untried_perceptual"] + _r["untried_sweep"]
            _dr = 100.0 * _cs / float(max(1, _t))
            if _t and _cs >= _t:
                _full += 1
            print("    %-18s probers %2d | ctor perc %4d + sweep %4d = %5d (%5.1f/prober) | refresh %4d calls"
                  " admitted %4d | DRAIN ctor %5.1f%% refresh %5.1f%%%s"
                  % (_g, _pr, _p["ctor_perceptual"], _p["ctor_sweep"], _t, _t / float(max(1, _pr)),
                     _p["refresh_calls"], _p["refresh_admitted"], _dr,
                     100.0 * _r["untried_refresh"] / float(max(1, _p["refresh_admitted"])),
                     "  full" if (_t and _cs >= _t) else ""))
        if _full:
            print("  ⇒ %d of %d games spent their ENTIRE construction pool. In each of those the lattice was"
                  " enumerated to exhaustion before a single refresh arrival could be chosen -- the ordering,"
                  " OBSERVED per game, not inferred from a pooled rate." % (_full, len(_rows)))
        else:
            print("  ⇒ NO game spent its entire construction pool, so this sweep cannot observe the ordering"
                  " directly: every game died with lattice points still untried. The branch rows above are a rate"
                  " over steps and remain untested at the mechanism (PATTERN 07-30g).")
    if _cres:
        print("  ★ THE CLICK BRANCH DOES NOT SUM TO THE CLICK EXITS. Do not read any row above until the residue"
              " is named. Every return of `choose` produces a click, so a non-zero residue means a return was"
              " added without a literal -- or a no-step path now exists and must be excluded BY NAME.")
    elif not _clk_steps:
        print("  VERDICT: MUTE -- no click steps this sweep, so the branch split rules nothing out.")
    else:
        _ex = int(cbr.get("exploit_scored", 0))
        _nm, _nt = int(cbr.get("nothing_moved_least_tried", 0)), int(cbr.get("no_targets", 0))
        _ctor = _u_perc + _u_swp
        _top = max((_ctor, "construction"), (_u_ref, "untried_refresh"), (_ex, "exploit_scored"),
                   (_nm, "nothing_moved_least_tried"), (_nt, "no_targets"))
        if _top[1] == "construction" and _ctor >= 0.5 * _clk_steps:
            print("  VERDICT: THE CONSTRUCTION POOL IS THE TAX -- %.1f%% of clicks (%.1f%% lattice, %.1f%%"
                  " perceptual) drain targets admitted at construction, BEFORE `refresh` can contribute anything."
                  " PREDICTION A HELD. `refresh` accounts for %.1f%% and the learned scores for %.1f%%, so the"
                  " thing to bound is the unconditional `grid_sweep`, not `refresh`."
                  % (100.0 * _ctor / _clk_steps, 100.0 * _u_swp / _clk_steps, 100.0 * _u_perc / _clk_steps,
                     100.0 * _u_ref / _clk_steps, 100.0 * _ex / _clk_steps))
        elif _top[1] == "untried_refresh" and _u_ref >= 0.5 * _clk_steps:
            print("  VERDICT: REFRESH REPLENISHMENT DOMINATES -- %.1f%% of clicks drain targets folded in AFTER"
                  " construction. PREDICTION OVERTURNED: the offline pool-floor bound was wrong and the"
                  " replenishment reading is reinstated." % (100.0 * _u_ref / _clk_steps))
        elif _top[1] == "exploit_scored" and _ex >= 0.5 * _clk_steps:
            print("  VERDICT: THE LEARNED SCORES ARE BEING USED -- %.1f%% of clicks are the exploit branch."
                  " PREDICTION WRONG: enumeration does finish, and the click policy's memory is live."
                  % (100.0 * _ex / _clk_steps))
        elif _top[1] == "nothing_moved_least_tried" and _nm >= 0.5 * _clk_steps:
            print("  VERDICT: NOTHING IT CLICKED EVER MOVED -- %.1f%% of clicks fall through to the round-robin,"
                  " which is reached only when EVERY candidate scores zero novel and zero changed. That is a"
                  " statement about perception's candidates, not about the choice among them."
                  % (100.0 * _nm / _clk_steps))
        elif _top[1] == "no_targets" and _nt >= 0.5 * _clk_steps:
            print("  VERDICT: PERCEPTION OFFERED NOTHING -- %.1f%% of clicks are the degenerate corner click with"
                  " no candidate at all. The prober is not choosing; `click_targets` is empty."
                  % (100.0 * _nt / _clk_steps))
        else:
            print("  VERDICT: MIXED -- no branch holds half the click steps (largest is %s at %.1f%%); the"
                  " prediction is neither held nor refuted." % (_top[1], 100.0 * _top[0] / _clk_steps))

    # ★★★ THE REUSE FUNNEL -- WHY A MINTED φ IS NEVER USED. THIRTEEN BEATS OWED. ★★★
    # MINTED_UNUSED is the ONE stage code that indicts the ARCHITECTURE, and every sweep so far has reported it as a
    # bare count under a sentence -- "reuse was attempted and the library did not explain" -- that names no branch.
    # An attempt can end four different ways at the offer site and four more at the directive site, and they
    # implicate four different layers. These counts are string literals written at those branches:
    #   explains_no_eligible_* Γ held nothing that even SPLITS these contexts. The library never competed. This is a
    #                          GRAIN/applicability verdict and it is NOT a verdict on the architecture. ★ AND IT IS
    #                          ITSELF AN EXIT NAME SPANNING MORE THAN ONE STATE, so it now resolves at four returns:
    #                          _empty (library empty; unreachable from the live site, named so nobody hides there),
    #                          _absent (every rejected φ held on NO fresh context -- the vocabulary does not describe
    #                          this board, so the repair is GRAIN at link 1), _universal (every rejected φ held on
    #                          EVERY fresh context -- true and vacuous, so the repair is UPSTREAM in the residual
    #                          builder), _mixed (both kinds present; no threshold picks between them, because a
    #                          threshold is a name somebody chose and that is the defect this funnel exists to undo).
    #   explains_no_compress   eligible φ existed and none paid its own cost + log2(eligible). Γ was tested and lost
    #                          -- the only reading MINTED_UNUSED has ever claimed to be.
    #   explains_already_pure  the residual had one outcome; nothing to explain (unreachable from the live site,
    #   explains_no_exceptions the residual was empty (likewise) -- both named so a future caller cannot hide there.
    #   dir_no_evaluable       Γ was consulted for an ACTION and no label had an evaluable context (seam failure)
    #   dir_no_endorsement     ...contexts evaluated, no candidate scored positive (the sign said nothing here)
    #   dir_tie                ...two candidates tied and Γ is refused the pick (refusal 4 -- a deliberate no)
    #   dir_acted              a directive actually chose the action -- a reuse, counted where it happened
    # ★ PRE-REGISTERED PREDICTION (written before the sweep that reads it, evaluated below by the script itself):
    #   `explains_no_eligible` DOMINATES, and the directive site contributes ZERO attempts. If that holds, then what
    #   has been reported as an ARCHITECTURE stall for thirteen beats is a stall in which Γ's promoted φ were never
    #   applicable to the fresh residual's contexts at all -- the library was never on trial. If instead
    #   `explains_no_compress` dominates, the architecture reading survives its first real test and the next beat is
    #   about the MDL bar, not about grain. Published either way; NOTHING is widened this beat.
    rfn = (res.get("tether_chain") or {}).get("echo", {}).get("reuse_funnel") or {}
    rbr = (rfn.get("branch") or {})
    _RB_NE = ("explains_no_eligible_empty", "explains_no_eligible_absent", "explains_no_eligible_universal",
              "explains_no_eligible_mixed")
    _RB_NAMED = _RB_NE + ("explains_no_compress", "explains_already_pure", "explains_no_exceptions",
                          "explains_transfer", "dir_no_evaluable", "dir_no_endorsement", "dir_tie", "dir_acted")
    _att = int(rfn.get("attempts", 0))
    # ★★★ THE OFFER GATE -- ONE LEVEL ABOVE THE FUNNEL, AND THE BOUND ON RUN-TO-RUN MOVEMENT. ★★★
    # Two cold-bank sweeps at the same commit, byte-identical in every per-game row and in every upstream counter,
    # disagreed by ONE segment: REUSE_UNWIRED 5/MINTED_UNUSED 3 against 4/4. Nothing the agent DID differed. The
    # swarm plays 8 games as concurrent threads in ONE process against ONE shared, APPEND-ONLY Γ, and the offer
    # site's guard was `if self.echo.library:` with no else -- so a non-empty residual that arrives before the
    # process's FIRST promotion makes no attempt and scores REUSE_UNWIRED, while the same residual arriving after
    # it scores MINTED_UNUSED. Which side of that line a segment lands on is decided by thread scheduling. The
    # counter below is the receipt for that: `skipped_gamma_empty` is the number of offer OPPORTUNITIES that found
    # an empty library, and therefore the UPPER BOUND ON ORDER-DEPENDENT SEGMENTS -- no more than this many stage
    # assignments can move between two runs whose agents behaved identically.
    _gate = (rfn.get("offer_gate") or {})
    _opp = int(rfn.get("offer_opportunities", 0))
    _gsum = sum(int(n) for n in _gate.values())
    _skip = int(_gate.get("skipped_gamma_empty", 0))
    _echo_tot = (res.get("tether_chain") or {}).get("echo") or {}
    _rne = int(_echo_tot.get("residual_nonempty", 0))
    _prom = int(_echo_tot.get("promoted", 0))
    print("\n=== THE OFFER GATE (was there anything in Γ to ask, at the moment we asked?) ===")
    if not _gate:
        print("  (no gate recorded -- either no residual was ever non-empty, or the guard is not writing a"
              " literal. A stage histogram alone CANNOT tell those two apart; do not read REUSE_UNWIRED below.)")
    for k in ("offered", "skipped_gamma_empty"):
        print("    %-24s %7d (%5.1f%% of opportunities)" % (k, int(_gate.get(k, 0)), 100.0 * int(_gate.get(k, 0)) / max(1, _gsum)))
    for k, n in sorted(_gate.items()):
        if k not in ("offered", "skipped_gamma_empty"):
            print("    %-24s %7d   ★ UNNAMED GATE BRANCH -- a third path was added without a reading" % (k, int(n)))
    print("  opportunities(from the diffs)=%d | gate sum=%d | RESIDUE=%d" % (_opp, _gsum, int(rfn.get("offer_residue", 0))))
    if int(rfn.get("offer_residue", 0)):
        print("  ★ THE GATE DOES NOT SUM TO THE OPPORTUNITIES. A non-empty residual reached the guard without"
              " being charged to a literal (or a literal was written where no residual was). Cite no row above.")
    # THE POOLING-BOUNDARY CHECK, taken here rather than in the producer for the same reason the branch cross-tab
    # residue is: inside `receipt._reuse_funnel` the opportunity count and the gate sum come from different fields,
    # but only AFTER `swarm._pool_block` has carried both across the process boundary can a dropped dict show.
    if _rne and _gsum != _rne:
        print("  ★ GATE SUM %d ≠ POOLED residual_nonempty %d -- the count and its denominator did not cross the"
              " pooling boundary together. The percentages above are unattributable." % (_gsum, _rne))
    print("  ⇒ UPPER BOUND ON ORDER-DEPENDENT SEGMENTS THIS SWEEP: %d of %d opportunities (%.1f%%) were offers made"
          " to an EMPTY Γ. Every one of those is a segment whose stage was decided by WHEN its thread asked, not by"
          " what the agent did. Two identical runs may differ by up to this many stage assignments."
          % (_skip, _gsum, 100.0 * _skip / max(1, _gsum)))
    # ★ PRE-REGISTERED PREDICTION (written into tests/test_offer_gate.py BEFORE this sweep ran): on any sweep with
    #   promoted>0, `gamma_at_offer` must contain BOTH a `0` key and a NON-ZERO key -- the direct receipt that
    #   offers inside ONE process saw DIFFERENT libraries, i.e. that ORDER, not behaviour, chose the outcome. If
    #   only `0` appears while promoted>0, the first promotion landed after every offer and the race window is the
    #   WHOLE RUN, which is a stronger version of the same finding, not a refutation of it.
    _gat = (rfn.get("gamma_at_offer") or {})
    print("  --- the SIZE Γ actually had at each offer (same denominator, own dict) ---")
    if not _gat:
        print("    (no sizes recorded)")
    for k, n in sorted(_gat.items(), key=lambda kv: int(kv[0])):
        print("    Γ had %-6s members at %7d offers" % (k, int(n)))
    _nz = sorted(int(k) for k in _gat if int(k) != 0)
    if _prom > 0 and _gat:
        if "0" in _gat and _nz:
            print("    ⇒ PREDICTION HELD: offers in ONE process saw Γ at 0 AND at %s. The stage a segment received"
                  " depended on which side of a promotion its thread ran." % (",".join(str(x) for x in _nz)))
        elif "0" in _gat and not _nz:
            print("    ⇒ EVERY offer saw an EMPTY Γ although %d φ were promoted -- the first promotion landed after"
                  " the last offer, so the race window is the WHOLE RUN, not a moment in it." % _prom)
        else:
            print("    ⇒ NO offer saw an empty Γ despite %d promotions: the library was already warm before the"
                  " first opportunity, and NONE of this sweep's REUSE_UNWIRED can be blamed on order." % _prom)
    elif not _prom:
        print("    ⇒ NOTHING WAS PROMOTED THIS SWEEP, so an all-zero column above is arithmetic, not a race: with"
              " an empty library there is no order for the outcome to depend on. Do not cite the bound.")
    _gbs = (rfn.get("offer_gate_by_stage") or {})
    if _gbs:
        print("  --- by the stage the SEGMENT was scored ---")
        for k, n in sorted(_gbs.items(), key=lambda kv: (-kv[1], kv[0])):
            print("    %-46s %7d%s" % (k, int(n),
                  "   ← THE ORDER-DEPENDENT ONES" if k == "REUSE_UNWIRED|skipped_gamma_empty" else ""))
        _gbres = _gsum - sum(int(n) for n in _gbs.values())
        if _gbres:
            print("    ★ GATE CROSS-TAB RESIDUE=%d -- one of the two dicts did not survive the pooling boundary."
                  % _gbres)

    print("\n=== THE REUSE FUNNEL (which branch resolved each offer of a fresh residual to Γ) ===")
    if not rbr:
        print("  (no reuse branch recorded -- Γ was never offered anything this sweep)")
    for k in _RB_NAMED:
        _n = int(rbr.get(k, 0))
        if _n or k in _RB_NE or k in ("explains_no_compress", "explains_transfer"):
            print("    %-32s attempts %7d (%5.1f%% of attempts)" % (k, _n, 100.0 * _n / max(1, _att)))
    for k, n in sorted(rbr.items()):
        if k not in _RB_NAMED:
            print("    %-32s attempts %7d   ★ UNNAMED BRANCH -- added without a reading" % (k, int(n)))
    _rres = int(rfn.get("residue", 0))
    print("  attempts=%d | branch sum=%d | RESIDUE=%d" % (_att, sum(rbr.values()), _rres))
    if _rres:
        print("  ★ THE REUSE FUNNEL DOES NOT SUM TO THE ATTEMPTS. Do not read any row above until the residue is"
              " named: an attempt that reached no branch means a `return` was added without a literal, and a branch"
              " without an attempt means a name is being written where no offer was made.")
    elif not _att:
        print("  VERDICT: MUTE -- Γ was never non-empty at an offer, so no attempt was made and MINTED_UNUSED"
              " cannot have been reached by this route. Nothing here is a verdict on the architecture.")
    else:
        # `_ne` is the SUM of the four no-eligible returns, so the dominance question below is asked of exactly
        # the quantity the first prediction was written about -- splitting a name must not silently change the
        # denominator of the prediction that motivated the split.
        _ne, _nc = sum(int(rbr.get(k, 0)) for k in _RB_NE), int(rbr.get("explains_no_compress", 0))
        _dir = sum(int(rbr.get(k, 0)) for k in ("dir_no_evaluable", "dir_no_endorsement", "dir_tie", "dir_acted"))
        if _ne >= 0.5 * _att:
            print("  VERDICT: Γ WAS NEVER APPLICABLE -- %.1f%% of offers found NO promoted φ that even splits the"
                  " fresh contexts. PREDICTION HELD. MINTED_UNUSED has been reporting a GRAIN failure under an"
                  " ARCHITECTURE name: the library was not tested and lost, it never took the field."
                  % (100.0 * _ne / _att))
        elif _nc >= 0.5 * _att:
            print("  VERDICT: Γ WAS TESTED AND LOST -- %.1f%% of offers had eligible φ and none of them paid its"
                  " cost. PREDICTION WRONG, and this is the first sweep in which MINTED_UNUSED means what it says."
                  % (100.0 * _nc / _att))
        else:
            print("  VERDICT: MIXED -- neither applicability nor compression holds half the attempts"
                  " (no_eligible %.1f%%, no_compress %.1f%%); both readings stay open."
                  % (100.0 * _ne / _att, 100.0 * _nc / _att))
        print("  directive-site attempts=%d (predicted 0)%s" % (_dir, "" if not _dir else "  ★ PREDICTION WRONG"))
        # ★ SECOND PRE-REGISTERED PREDICTION (written in tests/test_reuse_funnel.py BEFORE this sweep ran, and
        # evaluated here by the script rather than by prose afterwards): `_absent` DOMINATES the four, and
        # `phi_absent` dominates `phi_universal` in the per-φ tally. ABSENT means the promoted φ are simply not
        # PRESENT off their home board and the repair is grain, at link 1. UNIVERSAL means the fresh contexts do
        # not vary and the repair is UPSTREAM in the residual builder. They are different repairs, which is the
        # whole reason the count had to be split before either one was attempted.
        print("  --- WHICH KIND OF INAPPLICABILITY (the split of the %d no-eligible attempts) ---" % _ne)
        if not _ne:
            print("    (no attempt ended no-eligible this sweep -- the split says nothing and neither repair is"
                  " indicated by it)")
        else:
            for k in _RB_NE:
                print("    %-32s %7d (%5.1f%% of no-eligible)" % (k, int(rbr.get(k, 0)),
                                                                  100.0 * int(rbr.get(k, 0)) / _ne))
            _abs_n, _uni_n = int(rbr.get("explains_no_eligible_absent", 0)), \
                int(rbr.get("explains_no_eligible_universal", 0))
            _mix_n, _emp_n = int(rbr.get("explains_no_eligible_mixed", 0)), \
                int(rbr.get("explains_no_eligible_empty", 0))
            if _emp_n:
                print("    ★ %d attempts found Γ'S LIBRARY EMPTY. That branch is supposed to be unreachable from"
                      " the live site, which guards on Γ being non-empty. A reachable 'unreachable' branch is a"
                      " wiring finding and it outranks the rest of this section." % _emp_n)
            if _abs_n >= 0.5 * _ne:
                print("    VERDICT: ABSENT -- %.1f%% of no-eligible attempts rejected EVERY φ for holding on no"
                      " fresh context at all. PREDICTION HELD. The promoted vocabulary does not describe the board"
                      " it was carried to; the repair is GRAIN, at link 1, and nothing about the MDL bar or the"
                      " residual builder is implicated." % (100.0 * _abs_n / _ne))
            elif _uni_n >= 0.5 * _ne:
                print("    VERDICT: UNIVERSAL -- %.1f%% of no-eligible attempts rejected EVERY φ for holding on"
                      " EVERY fresh context. PREDICTION WRONG, and the finding points UPSTREAM: the contexts the"
                      " residual builder hands to Γ do not vary, so no predicate could split them and grain is not"
                      " the thing to repair." % (100.0 * _uni_n / _ne))
            elif _mix_n >= 0.5 * _ne:
                print("    VERDICT: MIXED -- %.1f%% of no-eligible attempts saw BOTH kinds in one library scan."
                      " Neither repair can be attempted first on the strength of this row; the per-φ tally below"
                      " carries the proportions, on its own denominator." % (100.0 * _mix_n / _ne))
            else:
                print("    VERDICT: NO KIND HOLDS HALF (absent %.1f%%, universal %.1f%%, mixed %.1f%%) -- both"
                      " repairs stay open and neither is indicated."
                      % (100.0 * _abs_n / _ne, 100.0 * _uni_n / _ne, 100.0 * _mix_n / _ne))
    # ★★★ THE PER-φ TALLY: A DIFFERENT DENOMINATOR, KEPT APART ON PURPOSE. ★★★
    # Every row above counts ATTEMPTS. These rows count LIBRARY φ SCANNED -- one write per rejected predicate, at
    # the eligibility loop. One attempt against a twelve-φ library writes one branch name and up to twelve φ names,
    # so the two must never be added or divided into one another. That is exactly why the producer publishes this
    # as a bare split and never as a rate against attempts: a per-φ count folded into a per-attempt sum would land
    # on a plausible total for the wrong reason, and would do it invisibly.
    _phi = (rfn.get("phi") or {})
    _phi_bys = (rfn.get("phi_by_stage") or {})
    _phi_tot = sum(int(n) for n in _phi.values())
    print("\n=== WHY EACH LIBRARY φ WAS REJECTED (per φ SCANNED -- NOT per attempt; do not divide by attempts) ===")
    if not _phi_tot:
        print("  (no φ rejection recorded -- either no attempt reached the eligibility loop, or every scanned φ"
              " was eligible. Those are different states and this row does not distinguish them.)")
    else:
        for k, n in sorted(_phi.items(), key=lambda kv: (-kv[1], kv[0])):
            print("    %-24s %7d (%5.1f%% of φ scanned-and-rejected)" % (k, int(n), 100.0 * int(n) / _phi_tot))
        _pa, _pu = int(_phi.get("phi_absent", 0)), int(_phi.get("phi_universal", 0))
        if _pa > _pu:
            print("  VERDICT: φ ARE ABSENT more often than vacuous (%d vs %d). PREDICTION HELD at the φ level:"
                  " the promoted literals do not fire on the boards they were carried to." % (_pa, _pu))
        elif _pu > _pa:
            print("  VERDICT: φ ARE VACUOUS more often than absent (%d vs %d). PREDICTION WRONG at the φ level:"
                  " the φ do fire, and it is the CONTEXTS that fail to vary -- an upstream finding." % (_pu, _pa))
        else:
            print("  VERDICT: TIED at %d each -- the φ-level split indicates neither repair." % _pa)
        print("  --- by the stage the SEGMENT was scored (same subset caveat as the branch cross-tab) ---")
        for k, n in sorted(_phi_bys.items(), key=lambda kv: (-kv[1], kv[0])):
            print("    %-46s %7d%s" % (k, int(n),
                                       "   ← THE ARCHITECTURE CLAIM" if k.startswith("MINTED_UNUSED|") else ""))
        _pres = _phi_tot - sum(int(n) for n in _phi_bys.values())
        if _pres:
            print("    ★ PER-φ CROSS-TAB RESIDUE=%d -- the pooled by-stage φ rows do not sum back to the pooled φ"
                  " totals, so one of the two dicts did not survive the pooling boundary intact. Cite neither."
                  % _pres)
    # ★★★ WHICH VOCABULARY WAS ABSENT -- THE SAME DENOMINATOR AS ABOVE, A DIFFERENT QUESTION. ★★★
    # `phi_absent` says the promoted φ did not fire on the board it was carried to. It does not say WHICH PART of
    # the vocabulary failed to travel, and those have different repairs: a dead COLOUR literal says the palette is
    # local to the board it was learned on, a dead RELATIONAL atom says the geometry is, and a φ whose every atom
    # is alive but which still holds nowhere says NEITHER vocabulary is missing -- the conjunction simply never
    # co-occurs, which is an arity question, not a grain one. These rows are charged at the same loop as
    # `phi_absent`, from each atom's OWN evaluation over the SAME contexts, into a SEPARATE dict; the identity
    # below is across the two dicts, which is where it can genuinely fail.
    _pk = (rfn.get("phi_kind") or {})
    _pk_bys = (rfn.get("phi_kind_by_stage") or {})
    print("\n=== WHICH VOCABULARY WAS ABSENT (per ABSENT φ -- a refinement of the row above, not an addition) ===")
    if not _pk:
        print("  (no vocabulary split recorded -- no φ was rejected, or the finer pen did not reach this run.)")
    else:
        _pa2 = int(_phi.get("phi_absent", 0))
        _pu2 = int(_phi.get("phi_universal", 0))
        _sum = lambda pre: sum(int(n) for k, n in _pk.items() if k.startswith(pre))
        _ak, _ac, _uk = _sum("absent_kind_"), _sum("absent_cause_"), _sum("universal_kind_")
        print("  --- COMPOSITION of the dead φ (what it was MADE OF) ---")
        for k, n in sorted(_pk.items(), key=lambda kv: (-kv[1], kv[0])):
            if k.startswith("absent_kind_"):
                print("    %-32s %7d (%5.1f%% of absent φ)" % (k, int(n), 100.0 * int(n) / max(1, _ak)))
        print("  --- CAUSE of its death (which family's ATOM was itself dead on these contexts) ---")
        for k, n in sorted(_pk.items(), key=lambda kv: (-kv[1], kv[0])):
            if k.startswith("absent_cause_"):
                print("    %-32s %7d (%5.1f%% of absent φ)" % (k, int(n), 100.0 * int(n) / max(1, _ac)))
        print("  --- BASE RATE: composition of the UNIVERSAL φ (the same vocabulary, rejected the other way) ---")
        for k, n in sorted(_pk.items(), key=lambda kv: (-kv[1], kv[0])):
            if k.startswith("universal_kind_"):
                print("    %-32s %7d (%5.1f%% of universal φ)" % (k, int(n), 100.0 * int(n) / max(1, _uk)))
        _stray = sorted(k for k in _pk
                        if not k.startswith(("absent_kind_", "absent_cause_", "universal_kind_")))
        if _stray:
            print("    ★ UNNAMED VOCABULARY ROWS %s -- a literal outside the three families is a branch added"
                  " without a reading; it is printed, not folded." % (_stray,))
        # ★ THE THREE IDENTITIES, ACROSS TWO DICTS AND ACROSS THE POOLING BOUNDARY -- each able to fail.
        _bad = []
        if _ak != _pa2:
            _bad.append("absent_kind_* sums to %d but phi_absent is %d" % (_ak, _pa2))
        if _ac != _pa2:
            _bad.append("absent_cause_* sums to %d but phi_absent is %d" % (_ac, _pa2))
        if _uk != _pu2:
            _bad.append("universal_kind_* sums to %d but phi_universal is %d" % (_uk, _pu2))
        if _bad:
            print("  ★ VOCABULARY IDENTITY BROKEN: %s. One of the two dicts did not cross the pooling boundary"
                  " intact, or a φ took a rejection branch without writing its family. CITE NOTHING FROM THIS"
                  " SECTION until it closes." % "; ".join(_bad))
        else:
            print("  identities CLOSE: absent_kind=%d absent_cause=%d both == phi_absent=%d;"
                  " universal_kind=%d == phi_universal=%d" % (_ak, _ac, _pa2, _uk, _pu2))
        # ★ THIRD PRE-REGISTERED PREDICTION (written into tests/test_reuse_funnel.py BEFORE this sweep ran):
        # ABSENCE CONCENTRATES IN THE COLOUR VOCABULARY. If it holds, the grain repair is about WHICH ATOMS GET
        # PROMOTED and not about widening any gate. The two ways to be wrong point elsewhere and are named here
        # so neither can be re-described afterwards as a partial success.
        _col = int(_pk.get("absent_cause_colour", 0)) + int(_pk.get("absent_cause_both", 0))
        _rel = int(_pk.get("absent_cause_relational", 0))
        _non = int(_pk.get("absent_cause_none", 0))
        if not _ac:
            print("  (no absent φ this sweep -- the third prediction is UNEVALUATED, which is not a pass.)")
        elif _col > _rel + _non:
            print("  VERDICT: COLOUR -- %d of %d absent φ died on a ground-colour literal (relational %d,"
                  " interaction-only %d). PREDICTION HELD. The promoted palette is local to the board it was"
                  " learned on; the grain repair is about WHICH ATOMS GET PROMOTED, and no gate is implicated."
                  % (_col, _ac, _rel, _non))
        elif _rel > _col + _non:
            print("  VERDICT: RELATIONAL -- %d of %d absent φ died on a relational atom (colour %d,"
                  " interaction-only %d). PREDICTION WRONG. The palette travels and the GEOMETRY does not, so the"
                  " repair is in the relational vocabulary, not in colour promotion." % (_rel, _ac, _col, _non))
        elif _non > _col + _rel:
            print("  VERDICT: INTERACTION -- %d of %d absent φ had EVERY atom alive and still held nowhere"
                  " (colour %d, relational %d). PREDICTION WRONG in a third way that was named in advance:"
                  " NEITHER vocabulary is missing. The conjunction never co-occurs, so the repair is the ARITY of"
                  " the predicate, not the atom registry." % (_non, _ac, _col, _rel))
        else:
            print("  VERDICT: NO CAUSE HOLDS A MAJORITY (colour %d, relational %d, interaction-only %d of %d) --"
                  " the third prediction is UNRESOLVED and no repair is indicated by this section."
                  % (_col, _rel, _non, _ac))
        if _pk_bys:
            print("  --- by the stage the SEGMENT was scored (same subset caveat as every cross-tab here) ---")
            for k, n in sorted(_pk_bys.items(), key=lambda kv: (-kv[1], kv[0])):
                print("    %-52s %7d%s" % (k, int(n),
                                           "   ← THE ARCHITECTURE CLAIM" if k.startswith("MINTED_UNUSED|") else ""))
            _kres = sum(int(n) for n in _pk.values()) - sum(int(n) for n in _pk_bys.values())
            if _kres:
                print("    ★ VOCABULARY CROSS-TAB RESIDUE=%d -- the by-stage rows do not sum back to the pooled"
                      " rows; one dict did not survive the pooling boundary. Cite neither." % _kres)
    # THE CROSS-TAB. The branch counts above are pooled over EVERY segment; the question owed is about the segments
    # scored MINTED_UNUSED specifically, and a pooled rate offered as evidence about a subset is a mis-labelled
    # receipt. These rows are read off each receipt's own stage and own branch tally -- one row, never a join.
    _bys = (rfn.get("by_stage") or {})
    print("  --- by the stage the SEGMENT was scored (the subset the architecture claim is about) ---")
    if not _bys:
        print("    (no cross-tab recorded -- the pooled rows above are UNSPLIT by stage; do not cite one about"
              " MINTED_UNUSED)")
    for k, n in sorted(_bys.items(), key=lambda kv: (-kv[1], kv[0])):
        print("    %-46s %7d%s" % (k, int(n), "   ← THE ARCHITECTURE CLAIM" if k.startswith("MINTED_UNUSED|") else ""))
    # THE CROSS-TAB RESIDUE IS COMPUTED **HERE**, NOT READ FROM THE PRODUCER, AND THAT IS THE WHOLE POINT. Inside
    # `receipt._reuse_funnel` every branch write also writes a by_stage row, so a residue over the two is zero BY
    # CONSTRUCTION -- an identity that cannot fail is decoration, and a producer field that can only ever be 0 is a
    # field never computed, printed as evidence. The place the two dicts can genuinely diverge is the POOLING
    # boundary: `swarm._pool_block` unions dict-valued sub-keys, and a pooler that carried one dict and dropped the
    # other would show up only in a subtraction taken AFTER the pool. So it is taken after the pool, from the two
    # pooled dicts, where it is able to be non-zero.
    _bres = sum(int(n) for n in rbr.values()) - sum(int(n) for n in _bys.values())
    if _bres:
        print("    ★ CROSS-TAB RESIDUE=%d -- the pooled by-stage rows do not sum back to the pooled branch totals,"
              " so one of the two dicts did not survive the pooling boundary intact. Do not cite either." % _bres)

    # ★★★ THE MEMBERS QUESTION: WHICH GAMES ARE BEHIND EACH POOLED RATE. ★★★
    # Every `answered` number in the block above is pooled across that exit's games. `dir_target_colour` answered
    # 89.0% masked over TWELVE games last sweep, and that one number cannot distinguish uniform competence from
    # three good games carrying nine bad ones -- which are not the same finding and do not have the same fix. A
    # pooled number offered as evidence about a SUBSET is the mis-labelled-receipt defect one level up, so the
    # rule is: ask WHICH MEMBERS before building anything on the rate. The SPREAD line is the actual finding here;
    # the per-game rows are its receipts. Nothing below is recomputed -- it is the same per-game funnel the pooler
    # summed, carried instead of discarded, and the RESIDUE line proves the two agree.
    fbg = (res.get("tether_chain") or {}).get("echo", {}).get("decide_funnel_by_game") or {}
    print("\n=== THE MEMBERS BEHIND EACH POOLED RATE (per-exit answer rate BY GAME) ===")
    if not fbg:
        print("  (no per-game funnel recorded -- every rate above is pooled and UNSPLIT; do not cite one about a"
              " subset of games)")
    for k, n in sorted(dfx.items(), key=lambda kv: (-kv[1], kv[0])):
        rows = []
        for g, xs in sorted(fbg.items()):
            sv = xs.get(k) or {}
            if not int(sv.get("exits", 0)):
                continue
            rows.append((int(sv["exits"]), g, int(sv.get("attr", 0)), int(sv.get("moved", 0)),
                         int(sv.get("moved_raw", 0)), int(sv.get("veto", 0))))
        if not rows:
            continue
        rows.sort(key=lambda t: (-t[0], t[1]))
        print("  %-22s pooled %5.1f%% masked of %d priced across %d games"
              % (k, (100.0 * int(dfm.get(k, 0)) / int(dfa[k])) if int(dfa.get(k, 0)) else float("nan"),
                 int(dfa.get(k, 0)), len(rows)))
        for st, g, a, mv, rw, vt in rows:
            if a:
                print("      %-18s steps %6d   priced %6d   masked %5.1f%%   raw %5.1f%%   veto %4d"
                      % (g, st, a, 100.0 * mv / a, 100.0 * rw / a, vt))
            else:
                print("      %-18s steps %6d   priced      0   (NOTHING PRICED -- contributes no rate)   veto %4d"
                      % (g, st, vt))
        _pg = [(100.0 * mv / a, g) for st, g, a, mv, rw, vt in rows if a]
        if _pg:
            _lo, _hi = min(_pg), max(_pg)
            print("      SPREAD: %d/%d games priced | masked min %5.1f%% (%s) max %5.1f%% (%s) | games ==0%%: %d |"
                  " games >=50%%: %d"
                  % (len(_pg), len(rows), _lo[0], _lo[1], _hi[0], _hi[1],
                     sum(1 for v, _ in _pg if v == 0.0), sum(1 for v, _ in _pg if v >= 50.0)))
        _rs, _ra = sum(t[0] for t in rows) - n, sum(t[2] for t in rows) - int(dfa.get(k, 0))
        if _rs or _ra:
            print("      ★ THE SPLIT DOES NOT SUM TO THE POOL: steps residue %d, priced residue %d. The per-game"
                  " rows and the pooled row are measuring different things -- cite NEITHER." % (_rs, _ra))

    # ★★★ THE SELF-MOTION CONTROL: "THE BOARD CHANGED" IS NOT "I CHANGED THE BOARD". ★★★
    # The members split found three games reading masked 100.0% AND raw 100.0% over 105-115 consecutive priced
    # steps on `dir_target_colour`. masked==raw kills the budget-bar explanation and nothing else: a board with an
    # animation, a patrolling hazard or a cycling display answers every step whatever the agent sends, and reads
    # 100/100 too. Those two findings have opposite fixes, so the perfect scores are a mis-labelled receipt until
    # re-measured (RANKING 5). This block conditions the SAME reading on the action ACTUALLY EMITTED, and reads the
    # steps the survival veto replaced -- an action the exit did not choose, same board, same segment.
    # ★ THE CLASSIFIER IS PRINTED, NOT THE VERDICT:
    #   * rates that DIFFER across actions => the motion is action-conditional => it IS the agent's.
    #   * rates ALIKE and high across every action, and the veto steps read high too => CONSISTENT WITH SELF-MOTION.
    #     That does not prove self-motion -- it is equally consistent with every action being effective -- but it
    #     does mean the rate may not be cited as competence on that game.
    #   * one action only, or no vetoed steps => the control is MUTE on that game. Muteness is printed, never
    #     rounded into either answer.
    print("\n=== THE SELF-MOTION CONTROL (did the AGENT move the board, or does the board move anyway?) ===")
    print("  (per-action floor for a verdict: %d priced steps; thinner actions are printed but carry no finding)"
          % _MIN_ACT_N)
    daa, dam, dar = ((dfn.get("act_attr") or {}), (dfn.get("act_moved") or {}), (dfn.get("act_moved_raw") or {}))
    dac, dacn = ((dfn.get("act_cells") or {}), (dfn.get("act_cells_n") or {}))
    dva, dvm = ((dfn.get("veto_attr") or {}), (dfn.get("veto_moved") or {}))
    if not daa:
        print("  (no action split recorded -- every `answered` rate above is UNCONTROLLED; do not cite one as"
              " competence)")

    def _acts_of(src, exit_name, bag):
        """The per-action rows for one exit, read off the flat "<exit>|<action>" keys of `bag`."""
        out = {}
        for kk, nn in bag.items():
            x, _sep, a = kk.partition("|")
            if _sep == "|" and x == exit_name:
                out[a] = int(nn)
        return out

    for k, n in sorted(dfx.items(), key=lambda kv: (-kv[1], kv[0])):
        pooled_a = _acts_of(None, k, daa)
        if not pooled_a:
            continue
        _a = int(dfa.get(k, 0))
        print("  %-22s pooled %5.1f%% masked of %d priced, over %d distinct actions"
              % (k, (100.0 * int(dfm.get(k, 0)) / _a) if _a else float("nan"), _a, len(pooled_a)))
        for g, xs in sorted(fbg.items()):
            ga = _acts_of(None, k, {kk: vv.get("act_attr", 0) for kk, vv in xs.items()})
            if not ga:
                continue
            gm = _acts_of(None, k, {kk: vv.get("act_moved", 0) for kk, vv in xs.items()})
            gc = _acts_of(None, k, {kk: vv.get("act_cells", 0) for kk, vv in xs.items()})
            gcn = _acts_of(None, k, {kk: vv.get("act_cells_n", 0) for kk, vv in xs.items()})
            rates = {a: 100.0 * gm.get(a, 0) / c for a, c in ga.items() if c}
            cells = {a: gc.get(a, 0) / gcn[a] for a in ga if gcn.get(a)}
            row = "  ".join("%s %5.1f%%(n=%d,cells%5.1f)" % (a, rates.get(a, float("nan")), ga[a],
                                                            cells.get(a, float("nan")))
                            for a in sorted(ga))
            print("      %-18s %s" % (g, row))
            sv = (xs.get(k) or {})
            _va, _vm = int(sv.get("veto_attr", 0)), int(sv.get("veto_moved", 0))
            _ea, _em = int(sv.get("attr", 0)), int(sv.get("moved", 0))
            _exit_rate = (100.0 * _em / _ea) if _ea else float("nan")
            # ★ A SPREAD OVER ONE-STEP SAMPLES IS NOT A SPREAD. The warmup exit sends each action exactly once, so
            # an ungated classifier reads "0.0%-100.0%, ACTION-CONDITIONAL" off four single steps and calls it a
            # finding. Actions below the floor are still PRINTED -- they are the evidence -- but they do not carry
            # a verdict, and a game with fewer than two actions above it is MUTE, published as mute.
            solid = {a: r for a, r in rates.items() if ga[a] >= _MIN_ACT_N}
            if len(rates) < 2:
                verdict = "MUTE: one action only -- the split cannot vary, so it rules nothing out"
            elif len(solid) < 2:
                verdict = ("MUTE: fewer than two actions reached %d priced steps (%s) -- too thin to support"
                           % (_MIN_ACT_N, ", ".join("%s n=%d" % (a, ga[a]) for a in sorted(ga))))
            else:
                rates = solid
                _lo, _hi = min(rates.values()), max(rates.values())
                if _hi - _lo >= 10.0:
                    verdict = ("ACTION-CONDITIONAL by %.1f pts (%.1f%%-%.1f%%) -- the change tracks WHICH action,"
                               " so it is the agent's" % (_hi - _lo, _lo, _hi))
                elif _hi >= 90.0:
                    verdict = ("UNIFORM and HIGH (%.1f%%-%.1f%%) -- CONSISTENT WITH SELF-MOTION; this game's rate"
                               " may not be cited as competence" % (_lo, _hi))
                else:
                    verdict = "UNIFORM (%.1f%%-%.1f%%) but not high -- no self-motion signature" % (_lo, _hi)
            if _va:
                verdict += " | VETO CONTROL: %5.1f%% masked over %d replaced steps vs %5.1f%% for the exit's own" \
                           % (100.0 * _vm / _va, _va, _exit_rate)
            else:
                verdict += " | VETO CONTROL MUTE (no replaced steps on this game)"
            print("          -> %s" % verdict)
        # the control is the SAME steps conditioned, so it must sum back to the column it controls, exactly
        _res = sum(pooled_a.values()) - _a
        if _res:
            print("      ★ THE ACTION SPLIT DOES NOT SUM TO THE PRICED COLUMN (residue %d): the control and its"
                  " subject are measuring different steps -- cite NEITHER." % _res)
    _vres = sum(dva.values())
    print("  veto steps READ by the control=%d of %d replaced (%d had no result frame) | pooled veto masked=%s"
          % (_vres, sum(dfv.values()), sum(dfv.values()) - _vres,
             ("%5.1f%%" % (100.0 * sum(dvm.values()) / _vres)) if _vres else "-- (no veto steps priced)"))

    # ★★★ THE CLICK REGION -- THE CONTROL THE SELF-MOTION SPLIT COULD NOT HAVE. ★★★
    # The block above conditions on the EMITTED LABEL, and every click carries the same label `A6`. So on click
    # games it has exactly ONE row, nothing to vary over, and prints MUTE on every one of them -- and those games
    # are 45.4% of the agent's decisions. A control that cannot fail is not a control. But the agent DOES vary its
    # click: it varies WHERE. This is the SAME priced steps, re-keyed by the coarse REGION (a thirds grid over the
    # board's own shape) of the coordinate ACTUALLY EMITTED. Same classifier as above, same sample floor:
    #   * rates that DIFFER across regions => the change tracks WHERE it clicked => it is the agent's.
    #   * rates ALIKE and high across every region => CONSISTENT WITH SELF-MOTION; the rate may not be cited as
    #     competence on that game. It is the board answering, not the click.
    #   * fewer than two regions above the floor => MUTE, published as mute.
    # The region is DESCRIPTIVE ONLY -- computed after the fact at the pricing site, and a test asserts no decision
    # function can read it. The moment an organ consults it, it stops being a reading and becomes a detector.
    cra, crm, crr = ((dfn.get("click_reg_attr") or {}), (dfn.get("click_reg_moved") or {}),
                     (dfn.get("click_reg_moved_raw") or {}))
    print("\n=== THE CLICK REGION (does the answer rate vary with WHERE the agent clicked?) ===")
    print("  (per-region floor for a verdict: %d priced steps; thinner regions are printed but carry no finding)"
          % _MIN_ACT_N)
    if not cra:
        print("  (no click region recorded -- either no clicks were priced this sweep, or the key never fired)")
    for k in sorted(set(kk.partition("|")[0] for kk in cra)):
        pooled_r = _acts_of(None, k, cra)
        _pn = sum(pooled_r.values())
        _pm = sum(_acts_of(None, k, crm).values())
        _pr = sum(_acts_of(None, k, crr).values())
        print("  %-22s pooled %5.1f%% masked / %5.1f%% raw of %d priced clicks, over %d distinct regions"
              % (k, 100.0 * _pm / max(1, _pn), 100.0 * _pr / max(1, _pn), _pn, len(pooled_r)))
        for g, xs in sorted(fbg.items()):
            # DROP THE ZEROS. The per-game bag carries every sub-key this game recorded under ANY funnel field, so
            # the action-split key `<exit>|A6` arrives here with a click_reg_attr of 0 and would print as a region
            # named `A6` with `nan%(n=0)` beside the real ones -- a row that was never computed, rendered as if it
            # had been. It is not a region and it is not evidence; it is the other instrument's key.
            ga = {a: n for a, n in _acts_of(None, k, {kk: vv.get("click_reg_attr", 0)
                                                      for kk, vv in xs.items()}).items() if n}
            if not ga:
                continue
            gm = _acts_of(None, k, {kk: vv.get("click_reg_moved", 0) for kk, vv in xs.items()})
            rates = {a: 100.0 * gm.get(a, 0) / c for a, c in ga.items() if c}
            print("      %-18s %s" % (g, "  ".join("%s %5.1f%%(n=%d)" % (a, rates.get(a, float("nan")), ga[a])
                                                   for a in sorted(ga))))
            solid = {a: r for a, r in rates.items() if ga[a] >= _MIN_ACT_N}
            if len(rates) < 2:
                verdict = "MUTE: one region only -- the agent clicked in a single third of the board"
            elif len(solid) < 2:
                verdict = ("MUTE: fewer than two regions reached %d priced clicks -- too thin to support"
                           % _MIN_ACT_N)
            else:
                _lo, _hi = min(solid.values()), max(solid.values())
                if _hi - _lo >= 10.0:
                    verdict = ("REGION-CONDITIONAL by %.1f pts (%.1f%%-%.1f%%) -- the change tracks WHERE the"
                               " click landed, so it is the agent's" % (_hi - _lo, _lo, _hi))
                elif _hi >= 90.0:
                    verdict = ("UNIFORM and HIGH (%.1f%%-%.1f%%) -- CONSISTENT WITH SELF-MOTION; this game's click"
                               " rate may not be cited as competence" % (_lo, _hi))
                else:
                    verdict = ("UNIFORM (%.1f%%-%.1f%%) but not high -- no self-motion signature" % (_lo, _hi))
            print("          -> %s" % verdict)
    _a6 = sum(v for k, v in daa.items() if k.endswith("|A6"))
    _crres = int(dfn.get("click_reg_residue", 0))
    print("  |A6 rows of the action split=%d | region sum=%d | RESIDUE=%d" % (_a6, sum(cra.values()), _crres))
    if _crres:
        print("  ★ THE REGION SPLIT DOES NOT SUM TO THE `|A6` ROWS IT RE-KEYS. These are meant to be the same"
              " steps read twice; a residue means a click was priced in one and dropped in the other -- cite"
              " NEITHER until it is named.")

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
    # ★ THE GAME COUNTS BEHIND THE POOLED LINES. Every `READS AS:` below used to be phrased over pooled STEPS, so
    # "entered 18 times ... the sign bar working as measured" was true and was about ONE GAME -- a reader who
    # skipped the table took it as a statement about the sweep. A pooled number offered as evidence about a subset
    # is the mis-labelled-receipt defect one level up, so every such sentence now carries its own denominator.
    _gm_reached = _gm_noseam = _gm_advice = 0
    for gid in sorted(res["results"]):
        g = ((res["results"][gid].get("echo") or {}).get("gamma_decision") or {})
        ent = int((g.get("sign_report_at_first_entry") or {}).get("signed_at_2_families", 0))
        clo = int((g.get("sign_report") or {}).get("signed_at_2_families", 0))
        _gm_reached += 1 if int(g.get("steps_reached", 0)) else 0
        _gm_noseam += 1 if int(g.get("steps_noseam", 0)) else 0
        _gm_advice += 1 if int(g.get("steps_consulted", 0)) else 0
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
    _ng = len(res["results"]) or 1
    print("  segments that entered the site=%d | of those, Γ ALREADY SIGNED at entry=%d" % (_entered, _ents))
    print("  GAMES BEHIND THESE POOLED NUMBERS: entered the site %d/%d | no seam %d/%d | Γ had advice %d/%d"
          % (_gm_reached, _ng, _gm_noseam, _ng, _gm_advice, _ng))
    if _contra:
        print("  ★ DEFECT: %d segments had a signed directive AT ENTRY and still took the empty branch. The guard"
              " and `sign_report` disagree. CHASE THIS BEFORE READING ANYTHING ELSE HERE." % _contra)
    elif _entered and not _ents:
        print("  READS AS (over %d of %d games): every entry happened while Γ was UNSIGNED for that game. Any"
              " signed directive visible in the end-of-run snapshot arrived AFTER the site stopped being entered"
              " -- a TIMING finding about how late Γ warms up, NOT a broken guard and NOT a wrong sign bar."
              % (_gm_reached, _ng))
    if _err:
        print("  ★ Γ RAISED on %d steps -- a BROKEN library, not an empty one. This is swallowed by design so a"
              " run never dies; it must never be read as 'Γ had nothing'." % _err)
    if _r == 0:
        print("  READS AS (over 0 of %d games): the decision site was NEVER ENTERED. Nothing here is a statement"
              " about Γ -- look at the caller (`_act_directional`), not at the library." % _ng)
    elif _n == _r:
        print("  READS AS (over %d of %d games): entered %d times, and EVERY TIME without a calibrated"
              " cursor/vectors. This is a CALIBRATION finding, not a Γ finding." % (_gm_reached, _ng, _r))
    elif _c == 0:
        print("  READS AS (over %d of %d games): entered %d times with a live seam on %d of them, and Γ offered a"
              " signed directive on NONE. This is the sign bar working as measured ON THOSE %d GAMES -- it is NOT"
              " a statement about the other %d." % (_gm_reached, _ng, _r, _r - _n, _gm_reached, _ng - _gm_reached))
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
