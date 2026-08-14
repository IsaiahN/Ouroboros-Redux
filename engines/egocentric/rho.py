"""rho.py -- G-A THE RHO ESTIMATOR (PREREG_FINAL_GAPS.md §G-A; the anchor figure's metric).

Cross-mounted fabrics are not independent witnesses: the swarm banks and replicates
fabrics verbatim, so k agreeing sources can be one source photocopied k times.
This module prices that redundancy.

  * rho(atoms_a, atoms_b) -> [0, 1]: WEIGHTED JACCARD over atom SIGNATURE CLASSES.
    A signature class is the frame-free half of an atom's identity: its sigma
    invariants (arity/bbox/changed/colour_delta/conserved + the mag class) joined
    with its transform's ttype/params class. The weighting is the multiset form --
    sum(min(count_a, count_b)) / sum(max(count_a, count_b)) -- so a class minted
    five times in one fabric and once in the other contributes 1/5, not 1/1.
    Identical fabrics -> 1.0; disjoint vocabularies -> 0.0. Frame-local descriptors
    (slot) are excluded: they never compare across fabrics (consumer.INVARIANTS law).

  * n_eff(k, rho_bar) = k / (1 + (k-1) * rho_bar): the effective number of
    INDEPENDENT sources among k correlated ones (the standard correlated-witness
    shrinkage: rho_bar=0 -> k, rho_bar=1 -> 1).

  * collapse(names, pair_rho, threshold) -> clusters: the COLLAPSE-4 GUARD's
    partition -- transitive closure of "rho >= threshold" pairs, so a bank
    replicated x8 folds into ONE witness cluster whose agreement counts once.

THE THRESHOLD (RHO_COLLAPSE = 0.9, documented choice): the guard is for REPLICAS,
not for overlap. Verbatim-banked copies measure rho ~ 1.0; a fabric that merely
shares half of another's vocabulary tops out around 0.5-0.67 on this estimator and
must NOT be hard-merged -- partial correlation is already priced continuously by
the n_eff debit. 0.9 operationalizes the prereg's "rho ~ 1" with headroom for a
replica that drifted by a few freshly minted atoms.

Empty or unsigma'd fabrics: rho = 0.0 -- silence is never evidence of correlation
(and never triggers the guard); an atom without sigma has no signature class.

Pure functions, stdlib only, deterministic; failures degrade, never raise.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

__all__ = ["RHO_COLLAPSE", "sig_class", "class_counts", "rho", "n_eff", "collapse"]

# The collapse-4 guard threshold (rationale in the module docstring).
RHO_COLLAPSE = 0.9

# The frame-free sigma axes (consumer.INVARIANTS + the magnitude class);
# "slot" is frame-local and deliberately absent.
SIGMA_AXES = ("arity", "bbox", "changed", "colour_delta", "conserved", "mag")


def sig_class(rec: Dict[str, Any]) -> Optional[str]:
    """The canonical signature class of one atom RECORD, or None for an atom
    that carries no sigma (no signature -> no vote in rho, either way).

    The class is a canonical JSON string of [projected sigma, ttype class,
    params], read from atom.sigma (mint-time, B13) with rec.sigma as fallback;
    ttype falls back to the atom kind so untyped EFFECT atoms still classify."""
    try:
        atom = rec.get("atom")
        atom = atom if isinstance(atom, dict) else {}
        sig = atom.get("sigma")
        if not isinstance(sig, dict):
            sig = rec.get("sigma")
        if not isinstance(sig, dict):
            return None
        proj = {k: sig.get(k) for k in SIGMA_AXES if k in sig}
        ttype = atom.get("ttype") or atom.get("kind")
        return json.dumps([proj, str(ttype), atom.get("params")],
                          sort_keys=True, default=str)
    except Exception:
        return None


def class_counts(atoms: Optional[Iterable[Dict[str, Any]]]) -> Dict[str, int]:
    """Multiset of signature classes over one fabric's atom records."""
    counts: Dict[str, int] = {}
    for rec in atoms or ():
        c = sig_class(rec) if isinstance(rec, dict) else None
        if c is not None:
            counts[c] = counts.get(c, 0) + 1
    return counts


def rho(atoms_a: Optional[Iterable[Dict[str, Any]]],
        atoms_b: Optional[Iterable[Dict[str, Any]]]) -> float:
    """Weighted Jaccard over signature classes, in [0, 1]. Symmetric, pure.
    Either side empty (or entirely unsigma'd) -> 0.0: silence is never
    evidence of correlation."""
    ca, cb = class_counts(atoms_a), class_counts(atoms_b)
    if not ca or not cb:
        return 0.0
    keys = set(ca) | set(cb)
    inter = sum(min(ca.get(k, 0), cb.get(k, 0)) for k in keys)
    union = sum(max(ca.get(k, 0), cb.get(k, 0)) for k in keys)
    return float(inter) / float(union) if union else 0.0


def n_eff(k, rho_bar) -> float:
    """Effective independent-source count among k sources with mean pairwise
    correlation rho_bar: k / (1 + (k-1) * rho_bar). rho_bar clamps into [0, 1];
    k <= 0 -> 0.0."""
    try:
        k = int(k)
    except Exception:
        return 0.0
    if k <= 0:
        return 0.0
    try:
        rb = float(rho_bar)
    except Exception:
        rb = 0.0
    rb = min(1.0, max(0.0, rb))
    return float(k) / (1.0 + (k - 1) * rb)


def collapse(names: Sequence[str], pair_rho: Callable[[str, str], float],
             threshold: float = RHO_COLLAPSE) -> List[List[str]]:
    """The collapse-4 guard's partition: union-find over "pair_rho(a, b) >=
    threshold" edges. Returns sorted clusters of sorted names; sources in one
    cluster are ONE witness (their agreement counts once). Deterministic."""
    order = sorted(dict.fromkeys(str(n) for n in names))
    parent = {n: n for n in order}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(order):
        for b in order[i + 1:]:
            try:
                close = float(pair_rho(a, b)) >= float(threshold)
            except Exception:
                close = False
            if close:
                parent[find(b)] = find(a)
    clusters: Dict[str, List[str]] = {}
    for n in order:
        clusters.setdefault(find(n), []).append(n)
    return sorted(sorted(c) for c in clusters.values())
