"""nexus.membrane.rules -- the membrane crossing rule (Tether §7.2).

"A stored action sequence is playback and must not be promoted; a package that is a predicate
mapping state -> action/bool is policy and may be." This is what keeps the macro scale from
becoming a lookup table: only GENERALISING structure crosses upward into shared Γ, never a
remembered replay of what happened once.

Enforced by TYPE, not by a reviewer's judgement: a Predicate (Context -> bool) is policy; an
ActionReplay (a recorded sequence) is playback. The check is `may_cross`.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
from ..kernel import Predicate


@dataclass(frozen=True)
class ActionReplay:
    """A recorded action sequence -- the FORBIDDEN kind of crossing. Represented explicitly so the
    rule has something to refuse; a replay is playback (biodegrades at the boundary), not policy."""
    actions: Tuple[int, ...]


def is_policy(item) -> bool:
    return isinstance(item, Predicate)

def may_cross(item) -> bool:
    """True iff `item` may promote upward through the membrane. Policy crosses; playback does not."""
    if isinstance(item, ActionReplay):
        return False
    return is_policy(item)
