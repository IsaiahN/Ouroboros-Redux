"""
replay_explain.py -- OFFLINE ATTRIBUTION for the offer-site selection cost.

WHY THIS EXISTS INSTEAD OF ANOTHER LIVE SWEEP. The sweep that first fired the tether fired it THREE times. A live
re-run after a scoring change would differ in the API's stochasticity, in which levels were reached, in thread
interleaving and therefore in what Γ held when -- and a delta of one firing out of three is far smaller than that
noise. "Two changes and one number is not a measurement": here the trick is to hold the EVIDENCE fixed instead.
The persistent residual bank already stores exactly what the scorer consumes -- (before-state Context, outcome)
pairs -- so both arms can be run over byte-identical evidence in byte-identical order, and the only difference
between them is the line under test.

WHAT IT REPLAYS, AND HOW FAITHFULLY. For each banked deposit, in a deterministic order, it repeats `_residual_pass`'s
order of operations: OFFER the residual to Γ first (so a fresh mint can never answer its own question), then mint
from the fresh residual, then the pooled retry if the fresh mint declined, then feed the mint to the echo clock.
The two arms share every one of those steps. They differ in ONE function: the arm labelled `uncharged` scores the
library offer with the pre-change code (frozen below, and never imported by the build), and `charged` calls the
shipped `Consolidator.explains_scored`.

THREE CAVEATS THAT MUST BE READ WITH THE NUMBERS.
  1. THE ABSOLUTE COUNTS HERE ARE NOT THE SWEEP'S. The bank keeps residuals, not runs; Γ therefore fills in bank
     order, not in the live threaded order. The measurement this tool makes is the DIFFERENCE BETWEEN THE ARMS,
     and only that. Anyone quoting `fired` from this file as the chain's firing count is quoting the wrong number.
  2. THE DENOMINATOR IS BREAK EVENTS THAT PRODUCED EVIDENCE. An empty residual is never banked, so DIED_PRE_DIFF
     and RESIDUAL_EMPTY are structurally invisible here. This bench says nothing about them.
  3. IT CANNOT SHOW A FIRING THAT THE CHARGE CREATES, because the charge is strictly subtractive. A delta of zero
     means the charge changed no verdict on this evidence -- which is a real result and must be published as one,
     not as a reason to go looking for a different measurement.

    PYTHONPATH=src python3.12 tools/replay_explain.py [bank_dir]
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from newhorse.redux_arch.consolidate import Consolidator
from newhorse.redux_arch.minting import _entropy_bits, two_part_mdl
from newhorse.redux_arch.residual_bank import DEFAULT_BANK_DIR, Deposit


def uncharged_explains_scored(con: Consolidator, exceptions):
    """THE PRE-CHANGE OFFER-SITE SCORER, FROZEN. A verbatim copy of `Consolidator.explains_scored` as it stood at
    a531e21, minus the `selection_cost` term that is the change under test. It lives here, in a tool, and not
    behind a flag in `consolidate.py`, on purpose: a production switch that turns the multiple-hypothesis charge
    off is a switch that can be turned off to make the instrument read higher. This copy has exactly one consumer
    -- this bench -- and no import path into the agent."""
    n = len(exceptions)
    if n == 0:
        return None
    k = sum(1 for _, o in exceptions if o)
    base = _entropy_bits(n, k)
    if base == 0.0:
        return None
    best, best_gain = None, 1e-9
    for pred in list(con.library):
        holds = [pred.holds(ctx) for ctx, _ in exceptions]
        if not any(holds) or all(holds):
            continue
        pos = [o for (_, o), h in zip(exceptions, holds) if h]
        neg = [o for (_, o), h in zip(exceptions, holds) if not h]
        l_given = _entropy_bits(len(pos), sum(pos)) + _entropy_bits(len(neg), sum(neg))
        gain = base - (l_given + pred.cost())
        if gain > best_gain:
            best, best_gain = pred, gain
    return None if best is None else (best, float(best_gain))


LAST_REPORT = {}


def charged_explains_scored(con: Consolidator, exceptions):
    """The shipped scorer, called through its real name so this arm cannot drift from the build.

    The report block is captured because a delta of ZERO has two very different explanations and the reader must
    be able to tell them apart: either the charge was levied and every firing survived it, or the charge was
    ZERO because the contest had one entrant. Reporting `n_eligible` and `selection_cost_bits` per firing turns
    "no change" from an assertion into something checkable."""
    LAST_REPORT.clear()
    return con.explains_scored(exceptions, LAST_REPORT)


def load_bank(root: str):
    """Every banked deposit, ordered deterministically by (family, serial). Both arms walk this exact list."""
    out = []
    if not os.path.isdir(root):
        raise SystemExit("no bank at %s -- run a live sweep first; this bench replays evidence, it cannot invent it"
                         % root)
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".json"):
            continue
        fam = fn[:-5]
        with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
            blob = json.load(f)
        for d in blob.get("deposits", []):
            out.append((fam, Deposit.from_json(d)))
    out.sort(key=lambda t: (t[0], t[1].serial))
    return out


def run_arm(deposits, scorer):
    """One pass over the whole bank with one offer-site scorer. Returns the counts and every firing it produced."""
    con = Consolidator(echo_threshold=2)
    seen_by_family = {}                                   # family -> list of (serial, exceptions) already banked
    stats = dict(deposits=0, scorable=0, offers=0, fired=0, minted=0, promoted=0, gain_bits=0.0)
    fired = []
    for fam, dep in deposits:
        stats["deposits"] += 1
        exc = dep.exceptions
        n = len(exc)
        k = sum(1 for _, o in exc if o)
        base = _entropy_bits(n, k)
        prior = seen_by_family.setdefault(fam, [])
        if not (n >= 2 and base > 0.0):
            prior.append(exc)                             # still evidence for the pool, just not scorable alone
            continue
        stats["scorable"] += 1
        if con.library:
            stats["offers"] += 1
            hit = scorer(con, exc)
            if hit is not None:
                pred, gain = hit
                stats["fired"] += 1
                stats["gain_bits"] += gain
                fired.append(dict(task_id=dep.task_id, family=fam, phi=str(pred), gain_bits=round(gain, 3),
                                  library=[str(p) for p in con.library],
                                  n_eligible=int(LAST_REPORT.get("n_eligible", -1)),
                                  charge_bits=float(LAST_REPORT.get("selection_cost_bits", 0.0)),
                                  minted_on=con.echo_tasks(pred),
                                  minted_games=con.echo_games(pred)))
        mint = two_part_mdl(exc, max_size=2)
        prior.append(exc)                                 # deposit happens BEFORE the pooled retry reads the pool
        if mint is None:
            pool = [e for seg in prior for e in seg]
            if len(pool) > n:
                mint = two_part_mdl(pool, max_size=2)
        if mint is not None:
            stats["minted"] += 1
            if con.observe_mint(dep.task_id, mint):
                stats["promoted"] += 1
    stats["library"] = [str(p) for p in con.library]
    return stats, fired


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BANK_DIR
    deposits = load_bank(root)
    print("replaying %d banked deposits from %s (%d exceptions total)"
          % (len(deposits), root, sum(len(d.exceptions) for _, d in deposits)))

    arms = {}
    for label, scorer in (("uncharged", uncharged_explains_scored), ("charged", charged_explains_scored)):
        arms[label] = run_arm(deposits, scorer)

    print("\n%-12s %9s %8s %7s %7s %8s %9s" % ("arm", "scorable", "offers", "FIRED", "minted", "promoted", "Σ bits"))
    for label in ("uncharged", "charged"):
        s, _ = arms[label]
        print("%-12s %9d %8d %7d %7d %8d %9.2f"
              % (label, s["scorable"], s["offers"], s["fired"], s["minted"], s["promoted"], s["gain_bits"]))

    u, c = arms["uncharged"][0], arms["charged"][0]
    d_fired = c["fired"] - u["fired"]
    print("\n=== ATTRIBUTION: ONE CHANGE, IDENTICAL EVIDENCE ===")
    print("  firings %d -> %d  (delta %+d)" % (u["fired"], c["fired"], d_fired))
    print("  total claimed compression %.2f -> %.2f bits (delta %+.2f)"
          % (u["gain_bits"], c["gain_bits"], c["gain_bits"] - u["gain_bits"]))
    if u["offers"] != c["offers"] or u["minted"] != c["minted"] or u["promoted"] != c["promoted"]:
        print("  ⚠ THE ARMS DIVERGED UPSTREAM OF THE OFFER (offers/mints/promotions differ). The delta above is"
              " NOT attributable to the charge alone -- do not quote it.")
    else:
        print("  offers, mints and promotions are IDENTICAL across arms, so the delta is the charge and nothing"
              " else.")

    lost = [f for f in arms["uncharged"][1]
            if (f["task_id"], f["phi"]) not in {(g["task_id"], g["phi"]) for g in arms["charged"][1]}]
    print("\n=== FIRINGS THE CHARGE WITHDREW (%d) ===" % len(lost))
    for f in lost:
        cost = math.log2(len(f["library"])) if f["library"] else 0.0
        print("  %s  φ=%s  claimed %.2f bits, library of %d (a %.2f-bit contest at most) -- withdrawn"
              % (f["task_id"], f["phi"], f["gain_bits"], len(f["library"]), cost))
    print("\n=== FIRINGS THAT SURVIVED (%d) ===" % len(arms["charged"][1]))
    for f in arms["charged"][1]:
        print("  %s  φ=%s  %.2f bits | Γ held %d, ELIGIBLE %d, charged %.2f bits | minted on games %s"
              % (f["task_id"], f["phi"], f["gain_bits"], len(f["library"]), f["n_eligible"],
                 f["charge_bits"], f["minted_games"]))
    # WHY A ZERO CAME OUT. If every firing was charged nothing, the change is CORRECT AND INERT on this evidence,
    # and saying so plainly is the point -- a correction that survives only because it never bit is not evidence
    # that the hole was imaginary, it is evidence that Γ is still too small for the hole to show.
    charges = [f["charge_bits"] for f in arms["charged"][1]]
    if charges and max(charges) == 0.0:
        elig = sorted({f["n_eligible"] for f in arms["charged"][1]})
        print("\n  NOTE: every surviving firing was charged 0.00 bits, because the ELIGIBLE contest size was %s --"
              " log2(1)=0." % elig)
        print("  The library was larger than that (up to %d), but a φ that holds on every context, or on none,"
              " is not in the contest." % max(len(f["library"]) for f in arms["charged"][1]))
        print("  So this change altered NO verdict on the banked evidence. It closes a hole that opens as Γ grows;"
              " it has not yet been paid for by a result.")
    print("\nREAD THE CAVEATS IN THIS FILE'S DOCSTRING BEFORE QUOTING ANY ABSOLUTE NUMBER ABOVE.")


if __name__ == "__main__":
    main()
