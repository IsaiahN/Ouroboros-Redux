#!/usr/bin/env python3.12
"""
audit_gamma.py -- OFFLINE BENCH: is anything in Γ ACTIONABLE?

WHY THIS EXISTS. Γ (`policy.SHARED_ECHO`) is the only thing in this agent that crosses a game boundary. A grep of
every use of `self.echo` puts all of them inside `_residual_pass`, `_close_segment`, and reporting: nothing in
`_decide`, `_survival_veto`, or any `_act_*` reads it. So the agent has a library of transferred knowledge and no
hand on the wheel. The obvious next build is to connect Γ to action selection -- and the obvious next build is
exactly the kind of change that moves internal counters without making the agent better.

So this runs FIRST, offline, on banked evidence, and it is allowed to return NO. A promoted φ can change what the
agent DOES only if all four of these hold, and each is measured here rather than asserted:

  (1) ACTION-COUPLED. Holding the board fixed at a decision point, φ's truth value must vary with WHICH action is
      considered. A φ that reads only focus_colour is constant across every candidate action at a step, so it can
      gate WHEN to trust something but can never rank WHAT to do. Measured by mutating one Context field at a time
      over values actually observed in the bank -- never by matching atom names, because a name is a claim.
  (2) CONSTRUCTIBLE AT THE LIVE SEAM. The seam already exists: `planner.plan_action` builds one Context per
      candidate action and tests a Predicate against it. But it builds that Context with `focus_colour=0` hard-coded
      and leaves `intended_free`/`intended_colour` at their defaults. A φ that reads a field the seam does not
      supply would be evaluated against a FABRICATED before-state -- it would answer, and its answer would be about
      a board that does not exist. That is worse than not firing.
  (3) SIGNED. Γ stores `List[Predicate]` and nothing else. A promoted φ says "these two groups of steps differ";
      it does not say which group is the good one. An unsigned predicate cannot yield a preference, only a
      partition. This is a structural fact about `Consolidator`, checked here, not inferred.
  (4) SIGN AGREEMENT ACROSS THE GAMES THAT ECHOED IT. Even a signed, action-coupled, constructible φ is only worth
      TRANSFERRING if the sign is the same on the games it echoed on. If φ predicts progress on re86 and predicts
      the opposite on wa30, wiring it in transfers a rule that is right in one place and actively wrong in another,
      and the pooled average would hide that. Per-task rates are printed with their denominators.

WHAT IT CANNOT TELL YOU. It reads the bank, which contains only residuals that were computed at all -- it is silent
on DIED_PRE_DIFF. It measures whether a φ COULD change a decision; it cannot say the changed decision clears a
level. That is what a live sweep is for, and nothing here may be cited as evidence of a clear.

    python3.12 tools/audit_gamma.py [--bank DIR] [--max-size 2] [--json OUT]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from newhorse.redux_arch.consolidate import Consolidator                     # noqa: E402
from newhorse.redux_arch.dsl import Context, Predicate                       # noqa: E402
from newhorse.redux_arch.minting import two_part_mdl                         # noqa: E402
from newhorse.redux_arch.receipt import game_of                              # noqa: E402
from newhorse.redux_arch.residual_bank import (DEFAULT_BANK_DIR, Deposit,     # noqa: E402
                                                 family_key)

# The fields of a decision-point Context, split by whether they can differ BETWEEN candidate actions at one step.
BOARD_FIELDS = ("focus_rc", "focus_colour", "target_rc")
ACTION_FIELDS = ("action_vec", "intended_free", "intended_colour")
# What `planner.plan_action` actually supplies today (focus_colour is hard-coded 0; the other two take defaults).
SEAM_SUPPLIES = ("focus_rc", "target_rc", "action_vec")


def _key(pred: Predicate) -> str:
    return " ∧ ".join(sorted(a.name for a in pred.atoms))


def load_bank(root: str) -> Dict[str, List[Deposit]]:
    out: Dict[str, List[Deposit]] = {}
    if not os.path.isdir(root):
        return out
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".json"):
            continue
        try:
            blob = json.load(open(os.path.join(root, fn), encoding="utf-8"))
        except Exception:
            continue
        deps = sorted((Deposit.from_json(d) for d in blob.get("deposits", [])), key=lambda d: d.serial)
        if deps:
            out[blob.get("key", fn[:-5])] = deps
    return out


# What the OUTCOME bit means, per evidence stream. It is NOT the same bit in both, and pooling them would compare
# "the focus moved" against "the board changed" -- one number over two questions (bridge.affordance_step vs
# bridge.click_residual). The stream is carried in the task id's suffix.
STREAM_OUTCOME = {
    "tau":   "the focus ACTUALLY MOVED under the action (bridge.affordance_step)",
    "click": "the BOARD CHANGED after the click (bridge.click_residual)",
}


def stream_of(task_id: str) -> str:
    return task_id.rsplit(".", 1)[-1] if "." in task_id else "unlabelled"


def promote(bank: Dict[str, List[Deposit]], max_size: int = 2) -> Tuple[Consolidator, Dict[str, List[Tuple[Context, bool]]]]:
    """Reproduce the LIVE promotion path offline: pool per family under the shipped code, mint, credit the mint to
    the CURRENT task, and let the real `Consolidator` decide what reaches Γ. Using the real class matters -- an
    audit that re-implements the promotion rule is auditing its own re-implementation."""
    echo = Consolidator(echo_threshold=2)
    by_task: Dict[str, List[Tuple[Context, bool]]] = defaultdict(list)
    for family, deps in sorted(bank.items()):
        pool: List[Tuple[Context, bool]] = []
        for d in deps:
            pool.extend(d.exceptions)
            by_task[d.task_id].extend(d.exceptions)
            m = two_part_mdl(list(pool), max_size=max_size)
            if m is not None:
                echo.observe_mint(d.task_id, m)
    return echo, by_task


def _realizable(contexts: List[Context]) -> Dict[str, list]:
    """The value sets a mutation test is allowed to draw from: what the world actually produced. Mutating a field
    to a value the bank never contains would let a φ be called action-coupled on a board that cannot occur."""
    vals: Dict[str, set] = {f: set() for f in BOARD_FIELDS + ACTION_FIELDS}
    for c in contexts:
        for f in vals:
            vals[f].add(getattr(c, f))
    return {f: sorted(v, key=lambda x: (x is None, str(x))) for f, v in vals.items()}


def field_dependence(pred: Predicate, contexts: List[Context]) -> List[str]:
    """Which Context fields this φ actually reads, established by PERTURBATION, not by parsing atom names.
    A field is a dependence iff changing ONLY that field, on some observed context, to some observed value,
    changes φ's verdict."""
    if not contexts:
        return []
    vals = _realizable(contexts)
    deps = []
    for f in BOARD_FIELDS + ACTION_FIELDS:
        changed = False
        for c in contexts:
            base = pred.holds(c)
            for v in vals[f]:
                if v == getattr(c, f):
                    continue
                if pred.holds(dataclasses.replace(c, **{f: v})) != base:
                    changed = True
                    break
            if changed:
                break
        if changed:
            deps.append(f)
    return deps


def sign_by_task(pred: Predicate, by_task: Dict[str, List[Tuple[Context, bool]]],
                 tasks: List[str]) -> List[dict]:
    """Per echoing task: the OUTCOME rate on each side of φ's split (see STREAM_OUTCOME for what the bit means), with denominators. The DELTA's sign is the
    thing a decision would use; the point of splitting by task is that a pooled delta can be positive while the
    per-game deltas point in opposite directions."""
    rows = []
    for t in tasks:
        exc = by_task.get(t, [])
        pos = [o for ctx, o in exc if pred.holds(ctx)]
        neg = [o for ctx, o in exc if not pred.holds(ctx)]
        p_pos = (sum(pos) / len(pos)) if pos else None
        p_neg = (sum(neg) / len(neg)) if neg else None
        delta = None if (p_pos is None or p_neg is None) else p_pos - p_neg
        rows.append(dict(task=t, game=game_of(t), family=family_key(game_of(t)), n_pos=len(pos), n_neg=len(neg),
                         p_pos=p_pos, p_neg=p_neg, delta=delta))
    return rows


def gamma_is_signed() -> bool:
    """Does a promotion carry ANY outcome-derived quantity into Γ? Tested by EXPERIMENT, not by reading field
    names: promote the same predicate through two Mints that differ ONLY in their outcome-derived numbers
    (`saved_bits`, `support`), and compare everything Γ retains. If the two Γs are indistinguishable, then nothing a
    decision could read about WHICH SIDE OF φ IS BETTER survived promotion -- Γ holds a partition, not a preference.
    A name-based check would pass the day someone adds a field called `sign` that nothing writes."""
    from newhorse.redux_arch.dsl import make_atom
    from newhorse.redux_arch.minting import Mint
    p = Predicate(frozenset({make_atom("INTENDED_FREE")}))
    def snapshot(saved: float, support: int) -> str:
        c = Consolidator(echo_threshold=1)
        c.observe_mint("zz00-aaaa", Mint(predicate=p, saved_bits=saved, support=support))
        return repr((c.library, c._tasks_by_key, c._pred_by_key, c.log))
    return snapshot(1.0, 1) != snapshot(999.0, 99)


def audit(bank: Dict[str, List[Deposit]], max_size: int = 2) -> dict:
    echo, by_task = promote(bank, max_size=max_size)
    all_ctx = [ctx for exc in by_task.values() for ctx, _ in exc]
    signed_in_gamma = gamma_is_signed()
    rows = []
    for pred in echo.library:
        tasks = echo.echo_tasks(pred)
        games = echo.echo_games(pred)
        deps = field_dependence(pred, all_ctx)
        action_coupled = [f for f in deps if f in ACTION_FIELDS]
        unsupplied = [f for f in deps if f not in SEAM_SUPPLIES]
        by = sign_by_task(pred, by_task, tasks)
        # SIGN AGREEMENT IS A CROSS-GAME QUESTION AND MUST BE COUNTED PER GAME. Four tasks that are four segments of
        # ONE game agreeing with each other is within-run consistency, and calling that "the sign transfers" is the
        # source-amnesia error the echo-kind ranking already refuses to make. Tasks are pooled within their game
        # first; only games with a measurable delta vote.
        # AND THE UNIT IS THE FAMILY, NOT THE INSTANCE. `ls20-016295f7` and `ls20-9c1e...` are two instances of one
        # game and are declared to share colour semantics (residual_bank's pooling key is exactly this); two
        # instances agreeing is not a cross-game claim, and counting them as two would let within-family
        # consistency be reported as transfer.
        per_game: Dict[str, Tuple[int, int, int, int]] = {}
        for row in by:
            g = family_key(row["game"])
            np_, kp, nn, kn = per_game.get(g, (0, 0, 0, 0))
            exc = by_task.get(row["task"], [])
            pos = [o for ctx, o in exc if pred.holds(ctx)]
            neg = [o for ctx, o in exc if not pred.holds(ctx)]
            per_game[g] = (np_ + len(pos), kp + sum(pos), nn + len(neg), kn + sum(neg))
        game_rows = []
        for g, (np_, kp, nn, kn) in sorted(per_game.items()):
            d = None if (np_ == 0 or nn == 0) else (kp / np_) - (kn / nn)
            game_rows.append(dict(game=g, n_pos=np_, n_neg=nn, delta=d))
        gdeltas = [r["delta"] for r in game_rows if r["delta"] is not None]
        signs = {(1 if d > 0 else (-1 if d < 0 else 0)) for d in gdeltas}
        agree = (len(signs) == 1 and 0 not in signs) if len(gdeltas) >= 2 else None
        rows.append(dict(phi=_key(pred), tasks=tasks, games=games,
                         depends_on=deps, action_coupled=action_coupled,
                         seam_missing_fields=unsupplied,
                         rankable=bool(action_coupled),
                         families=sorted({family_key(g) for g in games}),
                         constructible_at_seam=not unsupplied,
                         per_task=by, per_game=game_rows,
                         n_games_measurable=len(gdeltas), sign_agreement=agree))
    return dict(library_size=len(echo.library), signed_in_gamma=signed_in_gamma, predicates=rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default=DEFAULT_BANK_DIR)
    ap.add_argument("--max-size", type=int, default=2)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    bank = load_bank(a.bank)
    if not bank:
        print("NO BANKED RESIDUALS at %s -- an empty bench is not a zero. Run a sweep first." % a.bank)
        return 1
    streams = sorted({stream_of(d.task_id) for deps in bank.values() for d in deps})
    if len(streams) > 1:
        print("REFUSING TO POOL: the bank holds %d streams %s. The outcome bit does not mean the same thing in\n"
              "each of them, so one split rate over all of them would be one number over two questions. Re-run\n"
              "with a bank filtered to one stream." % (len(streams), streams))
        return 2
    res = audit(bank, max_size=a.max_size)
    print("BANK  %s   families=%d" % (a.bank, len(bank)))
    print("STREAM  %s   -- outcome=True means: %s"
          % (streams[0], STREAM_OUTCOME.get(streams[0], "UNKNOWN -- the task id carries no stream tag")))
    print("Γ  promoted=%d" % res["library_size"])
    print("SIGNED IN Γ: %s   -- `Consolidator.library` is List[Predicate]; no outcome statistic is stored with a\n"
          "             promotion, so Γ can say WHICH DISTINCTION MATTERS and cannot say WHICH SIDE IS BETTER."
          % ("yes" if res["signed_in_gamma"] else "NO"))
    print("\n%-24s %5s %5s %-18s %-6s %-6s %s"
          % ("φ", "tasks", "games", "depends on", "rank?", "seam?", "sign agrees ACROSS FAMILIES?"))
    for r in res["predicates"]:
        print("%-24s %5d %5d %-18s %-6s %-6s %s"
              % (r["phi"][:24], len(r["tasks"]), len(r["games"]), ",".join(r["depends_on"])[:18],
                 "YES" if r["rankable"] else "no",
                 "YES" if r["constructible_at_seam"] else "NO",
                 {True: "YES", False: "NO -- IT REVERSES",
                  None: "n/a (only %d family measurable)" % r["n_games_measurable"]}[r["sign_agreement"]]))
    print("\nPER-GAME SPLIT RATES (delta = P(outcome|φ) - P(outcome|¬φ); a transferred decision uses its SIGN)")
    for r in res["predicates"]:
        print("  φ = %s" % r["phi"])
        for row in r["per_game"]:
            print("      FAMILY %-8s n+=%-5d n-=%-5d delta=%s"
                  % (row["game"], row["n_pos"], row["n_neg"],
                     " n/a" if row["delta"] is None else "%+5.2f" % row["delta"]))
    print("\nPER-TASK SPLIT RATES (the segments the per-game rows pool; shown so the pooling is checkable)")
    for r in res["predicates"]:
        print("  φ = %s" % r["phi"])
        if r["seam_missing_fields"]:
            print("      seam cannot supply: %s  -- evaluating it in `plan_action` today would test a FABRICATED"
                  " before-state" % ",".join(r["seam_missing_fields"]))
        for row in r["per_task"]:
            d = row["delta"]
            print("      %-24s n+=%-4d n-=%-4d  P+=%s  P-=%s  delta=%s"
                  % (row["task"], row["n_pos"], row["n_neg"],
                     "  n/a" if row["p_pos"] is None else "%5.2f" % row["p_pos"],
                     "  n/a" if row["p_neg"] is None else "%5.2f" % row["p_neg"],
                     " n/a" if d is None else "%+5.2f" % d))
    rankable = [r for r in res["predicates"] if r["rankable"]]
    usable = [r for r in rankable if r["constructible_at_seam"]]
    cross = [r for r in res["predicates"] if r["n_games_measurable"] >= 2]
    agreeing = [r for r in cross if r["sign_agreement"] is True]
    print("\nVERDICT  %d promoted / %d rank actions / %d of those the live seam can evaluate honestly."
          % (res["library_size"], len(rankable), len(usable)))
    print("         %d echoed on 2+ FAMILIES with a measurable delta on each -- the only ones whose sign is a"
          " CROSS-GAME\n         claim at all; %d of those agree, %d reverse."
          % (len(cross), len(agreeing), len(cross) - len(agreeing)))
    ready = [r for r in cross if r["sign_agreement"] is True and r["rankable"] and r["constructible_at_seam"]]
    print("         WIRABLE TODAY (ranks actions AND the seam can build its context AND the sign holds across"
          " games): %d" % len(ready))
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=2, default=str)
        print("\nwrote %s" % a.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
