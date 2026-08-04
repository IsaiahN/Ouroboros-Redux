"""
molecule.py -- redux-arch: GROUND a grammar MOLECULE over a SCOPE (the quantifier bridge, invention loop Half A.5).

A molecule (grammar.py) is a QUANTIFIED typed objective: quantifier(ALL/SOME/ONE/NONE) over an inner relation
(a PRED). The flat dsl composer only ever evaluated a relation over ONE (focus,target) pair, so it could never
say "for ALL adjacent pairs this-before-that" (ORDER) or "for NONE" (collect-all). This module supplies the
missing half: it evaluates the inner relation (grounded via the dsl extractor basis) across a SCOPE of objects
and applies the quantifier -- producing a verdict AND a continuous DEGREE so progress can be measured.

Preserves the molecule richness (MOLECULES_the_rich_objective_layer_preserve): the objective stays a typed,
quantified OBJ; the extractor basis is only the PRED-grounding beneath it, never a replacement. New good
molecules can be NAMED and kept (mint output) -- the library grows in rich typed units, not flat atoms.

Encodes NO game answer: the scope is the perceived objects, the relation is basis-composed, the quantifier is
generic, and the ground (progress) prices which molecule fits. Nothing here names a game.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Callable, Optional, Dict, Any
import math
from .dsl import Context, Atom
from .minting import _entropy_bits


# An "object" in a scope: its cell (row,col) and its colour attribute. (Extend with more attrs as extractors grow.)
Obj = Tuple[Tuple[int, int], int]                        # ((row, col), colour)

PAIRINGS = ("consecutive", "all_pairs", "unary")
QUANTIFIERS = ("ALL", "SOME", "ONE", "NONE")


def _contexts(objects: List[Obj], pairing: str) -> List[Context]:
    """Turn a scope of objects into the (focus,target) Contexts the inner relation is evaluated on.
      consecutive -> (obj[i], obj[i+1])   [ORDER / sequence relations]
      all_pairs   -> (obj[i], obj[j]) i<j [MATCH / 'some pair' relations]
      unary       -> (obj[i], obj[i])     [EXIST / per-object relations]"""
    ctxs: List[Context] = []
    n = len(objects)
    if pairing == "consecutive":
        for i in range(n - 1):
            (frc, fc), (trc, tc) = objects[i], objects[i + 1]
            ctxs.append(Context(focus_rc=frc, focus_colour=fc, target_rc=trc, action_vec=(0, 0), target_colour=tc))
    elif pairing == "all_pairs":
        for i in range(n):
            for j in range(i + 1, n):
                (frc, fc), (trc, tc) = objects[i], objects[j]
                ctxs.append(Context(focus_rc=frc, focus_colour=fc, target_rc=trc, action_vec=(0, 0), target_colour=tc))
    else:  # unary
        for (rc, c) in objects:
            ctxs.append(Context(focus_rc=rc, focus_colour=c, target_rc=rc, action_vec=(0, 0), target_colour=c))
    return ctxs


def _apply_quantifier(quant: str, results: List[bool]) -> Tuple[bool, float]:
    """(verdict, degree). degree in [0,1] is the graded 'how close to satisfied' signal the ground prices on."""
    n = len(results)
    if n == 0:
        return False, 0.0
    k = sum(1 for r in results if r)
    frac = k / n
    if quant == "ALL":
        return (k == n), frac                            # degree rises as more pairs satisfy
    if quant == "SOME":
        return (k >= 1), frac
    if quant == "ONE":
        return (k == 1), (1.0 - abs(k - 1) / n)          # peak at exactly one
    if quant == "NONE":
        return (k == 0), (1.0 - frac)                    # degree rises as satisfied count falls (collect/erase)
    raise ValueError("unknown quantifier %r" % quant)


@dataclass(frozen=True)
class Molecule:
    """A grounded, evaluable quantified objective: quantifier(relation) over a scope with a pairing mode."""
    quantifier: str                                      # ALL / SOME / ONE / NONE
    relation: Atom                                       # the inner grounded PRED (from the dsl extractor basis)
    pairing: str                                         # consecutive / all_pairs / unary

    def __str__(self) -> str:
        return "%s[%s](%s)" % (self.quantifier, self.pairing, self.relation.name)

    def evaluate(self, objects: List[Obj]) -> Tuple[bool, float]:
        """Evaluate this molecule over a scope: (verdict, degree)."""
        ctxs = _contexts(objects, self.pairing)
        results = [self.relation.holds(c) for c in ctxs]
        return _apply_quantifier(self.quantifier, results)

    def degree(self, objects: List[Obj]) -> float:
        return self.evaluate(objects)[1]


def enumerate_molecules(relations: List[Atom],
                        quantifiers: Tuple[str, ...] = QUANTIFIERS,
                        pairings: Tuple[str, ...] = PAIRINGS) -> List[Molecule]:
    """The molecule candidate space = quantifier x grounded-relation x pairing. This is the composer's search
    space AT the molecule level (typed, quantified) -- the ground prices which one fits the progress residual."""
    out: List[Molecule] = []
    for q in quantifiers:
        for rel in relations:
            for p in pairings:
                out.append(Molecule(quantifier=q, relation=rel, pairing=p))
    return out


def score_molecule(mol: Molecule, scope_stream: List[List[Obj]], progress: List[bool]) -> Optional[float]:
    """Price a molecule by the SAME two-part-MDL logic used for flat atoms, one level up: does the molecule's
    per-step DEGREE crossing a threshold partition the progress stream? Returns saved bits (>0 = a real fit) or
    None. The molecule's graded degree is thresholded at its own median so the split is data-driven, not tuned."""
    if len(scope_stream) != len(progress) or len(progress) < 4:
        return None
    degs = [mol.degree(s) for s in scope_stream]
    thr = sorted(degs)[len(degs) // 2]                   # median split (no free parameter)
    pred = [d >= thr for d in degs]
    n = len(progress)
    k = sum(1 for p in progress if p)
    base = _entropy_bits(n, k)
    if base <= 0.0:
        return None
    # split progress by the molecule's thresholded degree; L(R|phi) = entropy within each side
    hi = [p for p, x in zip(progress, pred) if x]
    lo = [p for p, x in zip(progress, pred) if not x]
    cond = _entropy_bits(len(hi), sum(1 for p in hi if p)) + _entropy_bits(len(lo), sum(1 for p in lo if p))
    saved = base - cond - 2.0                             # 2 bits for the molecule description (quant+rel)
    return saved if saved > 0 else None
