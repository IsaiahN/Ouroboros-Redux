"""nexus.membrane.promote -- UP through the membrane: ECHO promotion (Tether §11.1, §14).

A predicate promotes into shared Γ only when it is verified by MORE THAN ONE distinct role -- the
same φ arising from different frames on the same problem is ECHO (cross-role resonance), evidence
of generality rather than one role's bias. This is v4's resonance_detector logic, kept as the
selectionist filter the paper says a Lamarckian library needs (§11.2): inheritance without a test
grows the library faster than it is checked.

Guards, in order:
  1. the crossing rule (rules.may_cross): only policy crosses, never playback.
  2. the ground verified it (passed in -- promotion is on RECEIPTS, never on proposals).
  3. ECHO: >= `min_roles` distinct roles verified it this round.
"""
from __future__ import annotations
from typing import Dict, Set, List, Tuple
from .rules import may_cross


def echo_promote(verified_by: Dict[str, Set[str]], items: Dict[str, object],
                 min_roles: int = 2) -> List[str]:
    """`verified_by`: pred_key -> set of role names whose GROUND-VERIFIED receipt included it.
    `items`: pred_key -> the object (Predicate or otherwise). Returns the keys that promote.

    Cross-role recurrence is ECHO; same role twice is not (that is correlation within one bias,
    not evidence of generality). A single agent's self-recurrence must never promote -- §14."""
    promoted = []
    for key, roles in verified_by.items():
        if len(roles) < min_roles:
            continue                      # not enough distinct frames -> correlation, not echo
        item = items.get(key)
        if item is None or not may_cross(item):
            continue                      # playback / non-policy never crosses
        promoted.append(key)
    return promoted
