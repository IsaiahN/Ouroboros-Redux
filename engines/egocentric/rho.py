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

THE IDENTITY LADDER (KNOBS AMENDMENT 2): one grain is a partition, not a
measurement -- rho_bar=0.000 x153 pairs was an ARTIFACT of measuring at rung 1
only (VERIFIED live: cn04 held 64 rederivation verdicts for ka59's atom key
while atom-set rho read 0). rho is therefore reported at every rung:

  * rho_at(atoms_a, atoms_b, rung): rung 0 = canonical KEY identity (the novelty
    guard's grain, position-free content hash); rung 1 = sig_class (the frozen
    estimator above, unchanged); rung 2 = COARSENED sigma -- params dropped,
    the frame-local mag class dropped, sigma INVARIANTS + ttype kept only.
    Rung 2 is a strict coarsening of rung 1 over the same classified atoms, so
    r2 >= r1 always; rung 0 measures a different axis (keys survive sigma-less
    atoms) and is not ordered against the others.

  * rederivation_traffic(verdicts_a, atoms_b): the CROSS-RECOGNITION channel --
    how many of A's "rederivation" verdicts name a key in B's atom keyset.
    This is the channel the partition could not see.

  * rho_report(fabrics): per-pair {r0, r1, r2, traffic} over a {name: {"atoms":
    [...], "verdicts": [...]}} mapping -- a DISTRIBUTION capable of nonzero,
    never a single-grain partition. traffic is counted in BOTH directions and
    summed (A recognizing B's atoms plus B recognizing A's).

Pure functions, stdlib only, deterministic; failures degrade, never raise.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = ["RHO_COLLAPSE", "sig_class", "class_counts", "rho", "n_eff", "collapse",
           "atom_key", "coarse_class", "rho_at", "rederivation_traffic", "rho_report"]

# The collapse-4 guard threshold (rationale in the module docstring).
RHO_COLLAPSE = 0.9

# The frame-free sigma axes (consumer.INVARIANTS + the magnitude class);
# "slot" is frame-local and deliberately absent.
SIGMA_AXES = ("arity", "bbox", "changed", "colour_delta", "conserved", "mag")

# Rung 2's axes: the sigma INVARIANTS only -- "mag" (a frame-local magnitude
# class, not an invariant) is coarsened away along with the params.
COARSE_AXES = ("arity", "bbox", "changed", "colour_delta", "conserved")


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


def coarse_class(rec: Dict[str, Any]) -> Optional[str]:
    """Rung 2: the COARSENED signature class -- sigma invariants + ttype only
    (params and the frame-local mag class dropped). Same sigma sourcing and
    ttype convention as sig_class, so rung 2 strictly coarsens rung 1: every
    atom that classifies at rung 1 classifies at rung 2, into a class that is
    a projection of its rung-1 class."""
    try:
        atom = rec.get("atom")
        atom = atom if isinstance(atom, dict) else {}
        sig = atom.get("sigma")
        if not isinstance(sig, dict):
            sig = rec.get("sigma")
        if not isinstance(sig, dict):
            return None
        proj = {k: sig.get(k) for k in COARSE_AXES if k in sig}
        ttype = atom.get("ttype") or atom.get("kind")
        return json.dumps([proj, str(ttype)], sort_keys=True, default=str)
    except Exception:
        return None


def atom_key(rec: Dict[str, Any]) -> Optional[str]:
    """Rung 0: the canonical content key of one atom record (atom.key, with
    rec.key as fallback), or None -- keyless records take no vote."""
    try:
        atom = rec.get("atom")
        atom = atom if isinstance(atom, dict) else {}
        k = atom.get("key", rec.get("key"))
        return str(k) if k else None
    except Exception:
        return None


def class_counts(atoms: Optional[Iterable[Dict[str, Any]]],
                 classifier: Callable[[Dict[str, Any]], Optional[str]] = sig_class,
                 ) -> Dict[str, int]:
    """Multiset of classes over one fabric's atom records, under `classifier`
    (default: the rung-1 sig_class)."""
    counts: Dict[str, int] = {}
    for rec in atoms or ():
        c = classifier(rec) if isinstance(rec, dict) else None
        if c is not None:
            counts[c] = counts.get(c, 0) + 1
    return counts


def _weighted_jaccard(ca: Dict[str, int], cb: Dict[str, int]) -> float:
    """sum(min)/sum(max) over the union of classes; either side empty -> 0.0
    (silence is never evidence of correlation)."""
    if not ca or not cb:
        return 0.0
    keys = set(ca) | set(cb)
    inter = sum(min(ca.get(k, 0), cb.get(k, 0)) for k in keys)
    union = sum(max(ca.get(k, 0), cb.get(k, 0)) for k in keys)
    return float(inter) / float(union) if union else 0.0


def rho(atoms_a: Optional[Iterable[Dict[str, Any]]],
        atoms_b: Optional[Iterable[Dict[str, Any]]]) -> float:
    """Weighted Jaccard over signature classes, in [0, 1]. Symmetric, pure.
    Either side empty (or entirely unsigma'd) -> 0.0: silence is never
    evidence of correlation. (This IS rung 1 of the identity ladder.)"""
    return _weighted_jaccard(class_counts(atoms_a), class_counts(atoms_b))


# The ladder's rungs, by classifier (AMENDMENT 2).
_RUNG_CLASSIFIERS: Dict[int, Callable[[Dict[str, Any]], Optional[str]]] = {
    0: atom_key,
    1: sig_class,
    2: coarse_class,
}


def rho_at(atoms_a: Optional[Iterable[Dict[str, Any]]],
           atoms_b: Optional[Iterable[Dict[str, Any]]],
           rung: int) -> float:
    """rho measured at one rung of the identity ladder: 0 = canonical KEY,
    1 = sig_class (== rho()), 2 = coarsened sigma. Weighted Jaccard at every
    rung; unknown rungs are a LOUD ValueError (a silent 0.0 would be exactly
    the partition artifact this function exists to kill)."""
    try:
        classifier = _RUNG_CLASSIFIERS[int(rung)]
    except (KeyError, TypeError, ValueError):
        raise ValueError("unknown identity-ladder rung: %r (have %s)"
                         % (rung, sorted(_RUNG_CLASSIFIERS))) from None
    return _weighted_jaccard(class_counts(atoms_a, classifier),
                             class_counts(atoms_b, classifier))


def rederivation_traffic(verdicts_a: Optional[Iterable[Any]],
                         atoms_b: Optional[Iterable[Dict[str, Any]]]) -> int:
    """The CROSS-RECOGNITION channel: how many of A's "rederivation" verdicts
    name a canonical key in B's atom keyset. Old-shape (ep/sigma-less) and
    malformed verdict records are read or skipped, never raised on."""
    keys_b = {atom_key(rec) for rec in (atoms_b or ())
              if isinstance(rec, dict)} - {None}
    if not keys_b:
        return 0
    n = 0
    for v in verdicts_a or ():
        if not isinstance(v, dict) or v.get("verdict") != "rederivation":
            continue
        k = v.get("key")
        if k is not None and str(k) in keys_b:
            n += 1
    return n


def rho_report(fabrics: Optional[Dict[str, Dict[str, Any]]]
               ) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """The per-pair distribution over {name: {"atoms": [...], "verdicts":
    [...]}}: for every unordered pair (a < b), {"r0", "r1", "r2", "traffic"}
    with traffic = A-recognizes-B plus B-recognizes-A. A measurement of
    independence must be CAPABLE of reading nonzero -- four channels, no
    single-grain partition. Deterministic; missing streams degrade to 0."""
    fabs = fabrics or {}
    names = sorted(str(n) for n in fabs)
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            fa, fb = fabs.get(a) or {}, fabs.get(b) or {}
            atoms_a, atoms_b = fa.get("atoms"), fb.get("atoms")
            out[(a, b)] = {
                "r0": rho_at(atoms_a, atoms_b, 0),
                "r1": rho_at(atoms_a, atoms_b, 1),
                "r2": rho_at(atoms_a, atoms_b, 2),
                "traffic": (rederivation_traffic(fa.get("verdicts"), atoms_b)
                            + rederivation_traffic(fb.get("verdicts"), atoms_a)),
            }
    return out


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
