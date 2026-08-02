"""nexus.membrane.seed -- DOWN through the membrane: the α / w_i seed-down (Tether §11.1, §7.1).

What descends is a PRIOR, not a replay: shared Γ lowers the starting kernel of an individual and
never dictates its actions. Operationally this biases which predicates a role proposes -- it mixes
the population's promoted Γ with fresh proposals by the role's weight w_i (the α-gate). A role with
high w_i (Pioneer, Exploiter) leans on its own exploration; low w_i (Optimizer) trusts Γ more.

Forward-projection lives here (design note, 2026-08-02): the seed set is not just Γ's members but
their TYPE-ADMISSIBLE GENERALIZATIONS -- a verified conjunction with one atom dropped subsumes more
cases, so proposing it early covers a FUTURE level's partial structure before that level arrives.
The generalizations are weighted proposals only; nothing here promotes them -- RLVR still must kill
or confirm each one (proposer proposes, never scores, never promotes).
"""
from __future__ import annotations
from typing import Dict, List
from ..kernel import Predicate


def generalizations(pred: Predicate) -> List[Predicate]:
    """Type-admissible generalizations: drop one atom from the conjunction (subsumes -> covers more).
    The worst-predictable-case envelope, grounded in a verified predicate rather than invented."""
    atoms = list(pred.atoms)
    if len(atoms) <= 1:
        return []
    return [Predicate(frozenset(atoms[:i] + atoms[i + 1:])) for i in range(len(atoms))]


def seed_down(gamma_shared: Dict[str, Predicate], w_i: float, project: bool = True) -> Dict[Predicate, float]:
    """Return {predicate: prior_weight} descended from shared Γ for a role with weight w_i.

    weight = (1 - w_i): the LESS a role trusts its own exploration, the MORE the promoted Γ seeds
    it. Generalizations (forward-projection) descend at a discounted weight -- they are speculative
    extrapolations, so they must never outweigh a directly verified member.
    """
    trust_gamma = 1.0 - w_i
    seeds: Dict[Predicate, float] = {}
    for pred in gamma_shared.values():
        seeds[pred] = seeds.get(pred, 0.0) + trust_gamma
        if project:
            for g in generalizations(pred):
                seeds[g] = seeds.get(g, 0.0) + 0.5 * trust_gamma      # discounted: speculative
    return seeds
