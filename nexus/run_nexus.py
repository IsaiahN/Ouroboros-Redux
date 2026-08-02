"""run_nexus.py -- the two halves + the proposer, wired end-to-end and run OFFLINE.

EGOCENTRIC (kernel): the real in-repo typed predicate DSL Γ (src/newhorse) supplies the candidate
space, the type-check, and the truth of a predicate on a before-state.
ALLOCENTRIC (population): roles with distinct w_i propose into a credibility-weighted market;
ECHO-verified predicates promote into shared Γ; Γ seeds the next round (the membrane).
GROUND: a synthetic, verifiable, unpersuadable RLVR stand-in (a hidden target predicate labelling a
before-state sample). The LIVE ARC gate is the documented seam in ground/live_arc.py and is NOT
exercised here -- no live-gate result is claimed.
PROPOSER: the propose leg. Default = type-directed enumeration; the fluent LM form (nexus.proposer
.fluent, esp32-ai's TinyLM over Γ) is a drop-in with the same interface.

The headline experiment is the paper's §16.7 question, run as a controlled comparison: does the
shared database earn its keep? Same RNG, same curriculum, DB on vs DB off.
"""
from __future__ import annotations
from .population.loop import run_curriculum
from .population.roles import ROLES
from .proposer.enumerate import EnumerationProposer
from .ground.rlvr import make_curriculum


def main():
    palette = list(range(1, 11))         # 10 colours -> 26 atoms; blind search is bounded at conj-size 2
    curriculum = make_curriculum(palette)
    K, ROUNDS = 20, 10
    print("NEXUS -- two-scale loop, offline synthetic ground\n")
    print("roles:", ", ".join(f"{r.name}(w={r.w_i})" for r in ROLES))
    print("curriculum:", ", ".join(f"{lv.name}[{lv.target}]" for lv in curriculum), "\n")

    on = run_curriculum(curriculum, EnumerationProposer(palette), use_db=True, k=K, max_rounds=ROUNDS)
    off = run_curriculum(curriculum, EnumerationProposer(palette), use_db=False, k=K, max_rounds=ROUNDS)

    print("=== §16.7  DOES THE SHARED DATABASE EARN ITS KEEP? (same RNG, DB on vs off) ===")
    print(f"{'level':16s} {'DB-on round':>12s} {'DB-off round':>13s}")
    for a, b in zip(on["results"], off["results"]):
        ra = "solved@%s" % a["solved_round"] if a["solved_round"] is not None else "unsolved"
        rb = "solved@%s" % b["solved_round"] if b["solved_round"] is not None else "unsolved"
        star = "  <- first-exposure via Γ" if (a["first_exposure"] and not b["first_exposure"]) else ""
        print(f"{a['level']:16s} {ra:>12s} {rb:>13s}{star}")

    print(f"\nlevels solved     : DB-on {on['solved']}/{len(curriculum)}   DB-off {off['solved']}/{len(curriculum)}")
    print(f"first-exposure    : DB-on {on['first_exposure']}          DB-off {off['first_exposure']}")
    print(f"proposals spent   : DB-on {on['total_proposals']}         DB-off {off['total_proposals']}")
    print(f"shared Γ (promoted): {on['gamma']}")
    print("\nNOTE: synthetic ground. The only metric that ultimately counts is live level-completion")
    print("      (ground/live_arc.py) -- that seam is intentionally not exercised in this branch.")


if __name__ == "__main__":
    main()
