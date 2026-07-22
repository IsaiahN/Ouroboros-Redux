"""
consolidate.py -- redux-arch P3: ECHO -> PROMOTE (the slow, cross-episode clock).

A local mint (P2) is provisional: a predicate that compresses ONE task's residual might be an overfit hack. The
guard is ECHO-before-PROMOTE -- a minted φ is admitted into the grammar Γ only after it recurs on a DIFFERENT
task (it echoes). Then Γ ← Γ ∪ φ, and on the next task Γ already predicts the regularity, so the residual is
zero and no search is needed -- the self-modifying loop closes and transfer is realized.

This in-house consolidation (key predicates by their atom set; promote at echo_threshold distinct tasks) is the
minimal version of DreamCoder/Stitch library learning [Ellis 2021; Bowers 2023]. Stitch is the production backend
for the harder job -- refactoring a LARGE set of minted predicates to find shared sub-structure and abstract it;
for the echo-before-promote guard and small libraries, reuse-count promotion suffices. Nothing silent: every
promotion is logged with the tasks that echoed it.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, FrozenSet
from .dsl import Predicate, Context
from .minting import Mint, two_part_mdl, Exception_


def _key(pred: Predicate) -> FrozenSet[str]:
    """Canonical identity of a predicate: its set of atom names (equal predicates share it)."""
    return frozenset(a.name for a in pred.atoms)


@dataclass
class Consolidator:
    """The grammar's growth gate: promote a minted predicate into Γ only once it ECHOes on a different task."""
    echo_threshold: int = 2
    library: List[Predicate] = field(default_factory=list)      # Γ's promoted predicates (the grown vocabulary)
    _tasks_by_key: Dict[FrozenSet[str], Set[str]] = field(default_factory=dict)
    _pred_by_key: Dict[FrozenSet[str], Predicate] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)

    def observe_mint(self, task_id: str, mint: Mint) -> bool:
        """Register that `task_id` minted this predicate. Promote it into Γ once it has echoed on
        `echo_threshold` distinct tasks. Returns True iff this call caused a promotion."""
        key = _key(mint.predicate)
        self._pred_by_key[key] = mint.predicate
        seen = self._tasks_by_key.setdefault(key, set())
        seen.add(str(task_id))
        already = any(_key(p) == key for p in self.library)
        if len(seen) >= self.echo_threshold and not already:
            self.library.append(mint.predicate)
            self.log.append("PROMOTE  φ=(%s) into Γ -- echoed on tasks %s"
                            % (mint.predicate, sorted(seen)))
            return True
        self.log.append("HOLD  φ=(%s) minted on %s (%d/%d tasks -- not yet echoed)"
                        % (mint.predicate, task_id, len(seen), self.echo_threshold))
        return False

    def explains(self, exceptions: List[Exception_]) -> Optional[Predicate]:
        """Does Γ (a promoted predicate) already account for these exceptions? If so, the new task is solved
        WITHOUT re-minting -- the transfer payoff. Returns the explaining predicate or None."""
        for pred in self.library:
            pos = [o for ctx, o in exceptions if pred.holds(ctx)]
            neg = [o for ctx, o in exceptions if not pred.holds(ctx)]
            if pos and neg and _pure(pos) and _pure(neg):    # a promoted φ that cleanly splits this residual
                return pred
        return None


def _pure(outcomes: List[bool]) -> bool:
    return len(set(outcomes)) <= 1
