"""nexus.population.roles -- the ALLOCENTRIC half's role specialization (Tether Table 6).

Roles preserve the population's non-identity (§12.2): each occupies a different region of the
reasoning space with a different weight w_i over private exploration vs shared network wisdom, and
a different proposal STYLE. The population cannot collapse into one weighted average because the
roles do not all propose the same way. w_i values are Table 6's.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Role:
    name: str
    w_i: float          # weight on PRIVATE exploration vs network Γ (high = trusts self)
    budget: int         # action/proposal budget per generation
    style: str          # how this role generates proposals: explore | refine | generalize | exploit


ROLES: List[Role] = [
    Role("Pioneer",    0.7, 1000, "explore"),      # broad novel search from scratch
    Role("Optimizer",  0.3,  200, "refine"),       # local refinement, trusts Γ most
    Role("Generalist", 0.5,  300, "generalize"),   # abstraction / forward-projection
    Role("Exploiter",  0.8,  200, "exploit"),      # low network trust, mines its own hits
]
