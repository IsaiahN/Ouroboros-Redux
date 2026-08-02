"""nexus.population.loop -- one run of the two-scale loop over a curriculum.

Per round, every role proposes (proposer + membrane seed-down), the GROUND scores every proposal
(unpersuadable), the market updates credibility with the covariance discount, and any predicate
verified by >= 2 distinct roles promotes into shared Γ through the membrane. Γ persists across
levels, so a predicate verified on an early level seeds refinement/generalization on later ones.

The RNG seed for each (level, round, role) is identical whether or not the shared DB is used, so a
DB-on vs DB-off comparison isolates exactly the database's contribution -- the §16.7 test, run as a
controlled one-variable experiment rather than asserted.
"""
from __future__ import annotations
import random
from collections import defaultdict, Counter
from typing import List
from .roles import ROLES
from .credibility import CredibilityDB
from ..membrane.seed import seed_down
from ..membrane.promote import echo_promote
from ..ground.rlvr import SyntheticGround, Level


def run_curriculum(curriculum: List[Level], proposer, use_db: bool = True,
                   max_rounds: int = 6, k: int = 12, seed: int = 0) -> dict:
    db = CredibilityDB()
    results, total_proposals = [], 0
    for level in curriculum:
        ground = SyntheticGround(level)
        solved_round = None
        cum_verified = defaultdict(set)   # key -> set of roles that ground-verified it (ACROSS rounds)
        seen_items = {}                   # key -> Predicate (all proposals seen this level)
        for rnd in range(max_rounds):
            proposals, proposers_of, redundancy = {}, defaultdict(set), Counter()
            for role in ROLES:
                rng = random.Random(f"{seed}-{level.name}-{rnd}-{role.name}")
                seeds = seed_down(db.shared_gamma(), role.w_i) if use_db else {}
                for p in proposer.propose(seeds, role, k, rng):
                    key = str(p)
                    proposals[key] = p; seen_items[key] = p
                    proposers_of[key].add(role.name); redundancy[key] += 1
            total_proposals += len(proposals)
            solved_here = False
            scores = []
            for key, p in proposals.items():
                s = ground.score(p); scores.append(s)
                if use_db:
                    db.vote(key, s, redundancy[key], len(ROLES))
                if ground.solved(p):
                    solved_here = True
                    cum_verified[key] |= proposers_of[key]      # accumulate cross-role echo over rounds
                    for rn in proposers_of[key]:
                        proposer.remember(rn, p)
            if use_db:
                db.tick()                                        # clock decay: standing fades if not renewed
                db.note_round(max(scores) if scores else 0.0)    # CUSUM regime trigger on the success stream
                for key in echo_promote(cum_verified, seen_items):  # promote whatever now has >=2-role echo
                    db.promote(key, seen_items[key])
            if solved_here and solved_round is None:
                solved_round = rnd
            # keep working a couple rounds past first solve so cross-role echo can promote the winner
            if solved_round is not None and rnd >= solved_round + 2:
                break
        results.append({"level": level.name, "solved_round": solved_round,
                        "first_exposure": solved_round == 0})
    return {"results": results, "gamma": sorted(db.shared_gamma().keys()),
            "total_proposals": total_proposals,
            "solved": sum(1 for r in results if r["solved_round"] is not None),
            "first_exposure": sum(1 for r in results if r["first_exposure"]),
            "regime_changes": db.regime_changes}   # CUSUM change-points detected from the success stream
