"""nexus.proposer.enumerate -- the PROPOSE leg of the market, type-directed enumeration form.

The proposer proposes candidate Γ predicates; it never scores and never promotes (that is the
elaboration-trap guard). This enumeration proposer is the deterministic, no-training form; the
fluent LM form (fluent.py) is the drop-in that AIMS this same distribution with a tiny model.

Role STYLE differentiates the population (Table 6): explore broadly (Pioneer), refine seeds by
adding an atom (Optimizer, the mechanism that turns a promoted L1 predicate into an L2 one), emit
generalizations for forward-cover (Generalist), or mine one's own hits (Exploiter). Seeds arrive
from the membrane's seed-down; a role's w_i already set their weight, so a high-w_i role sees weak
seeds and leans on its own search.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List
from ..kernel import Predicate, enumerate_predicates, atom_universe
from ..membrane.seed import generalizations


class EnumerationProposer:
    def __init__(self, palette, max_size: int = 2):
        self.universe = enumerate_predicates(palette, max_size)
        self.singletons = [p for p in self.universe if len(p.atoms) == 1]
        self.atoms = atom_universe(palette)
        self.memory: Dict[str, List[Predicate]] = defaultdict(list)

    def remember(self, role_name: str, pred: Predicate) -> None:
        if str(pred) not in {str(p) for p in self.memory[role_name]}:
            self.memory[role_name].append(pred)

    def _refine(self, pred: Predicate) -> List[Predicate]:
        out = [pred]
        present = set(pred.atoms)
        for a in self.atoms:
            if a not in present:
                out.append(Predicate(frozenset(present | {a})))
        return out

    @staticmethod
    def _dedup(preds: List[Predicate]) -> List[Predicate]:
        uniq, seen = [], set()
        for p in preds:
            key = str(p)
            if key not in seen:
                seen.add(key); uniq.append(p)
        return uniq

    def propose(self, seeds: Dict[Predicate, float], role, k: int, rng) -> List[Predicate]:
        """The α-gate as an ADDITIVE mix: Γ-derived candidates + blind exploration, never one
        replacing the other. A role's w_i sets how many of k slots go to Γ vs exploration, so
        seed-down can only ADD reach, never remove it (that was the bug: replacing exploration let
        the shared DB do worse than none). Refinements of the FRONTIER (largest verified predicate)
        come first and are shuffled per round, so composing past the blind search's size bound is
        stochastic across rounds rather than a fixed truncation that never advances."""
        seedcands: List[Predicate] = []
        if seeds:
            frontier = sorted(seeds, key=lambda p: (-len(p.atoms), -seeds[p]))  # extend the most specific first
            for sp in frontier:
                if role.style in ("refine", "exploit"):
                    ext = self._refine(sp); rng.shuffle(ext); seedcands += ext
                elif role.style == "generalize":
                    seedcands += [sp] + generalizations(sp)          # forward-cover
                elif role.style == "explore":
                    seedcands += [sp]                                 # Pioneer barely leans on Γ
        if role.style == "exploit":
            seedcands = list(self.memory[role.name]) + seedcands
        seedcands = self._dedup(seedcands)
        n_seed = min(len(seedcands), round((1.0 - role.w_i) * k)) if seeds else 0
        chosen = seedcands[:n_seed]
        n_expl = k - len(chosen)
        explore = rng.sample(self.universe, min(n_expl, len(self.universe)))  # always ranges the ground
        return self._dedup(chosen + explore)[:k]
