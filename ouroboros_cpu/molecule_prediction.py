"""molecule_prediction.py -- lift CHECKABLE, CAUSAL predictions onto the abductor's molecules.

The gap this closes (Q1 of the §11.34x ledger discussion): validation.py refutes the PERCEPT typings
causally and per-component, but the abductor's relational molecules (BE_AT / BECOME / SAME / COVER /
NONE.EXIST) and the DELAY molecules carry NO checkable prediction, so the composed-objective layer has no
causal refutation -- the kernel only ever sees the coarse OBJECTIVE_INVALID / PURSUIT_FAILED. A refutation
ledger that closes composition branches cannot be causal until a molecule's failure is attributable to THAT
molecule's broken prediction.

This module derives a STRUCTURED prediction dict from an abduced hypothesis (+ its compiled Discrepancy when
available). The prediction routes through the SAME validation.check_prediction / validate path as the percept
predictions -- so refutation inherits the existing causal, phase-gated, hold_rate machinery. Nothing here
re-implements judging; it only produces the prediction that the existing engine judges.

DISCIPLINE:
  * A molecule whose claim is not generically checkable from (before, after) returns None -> it carries no
    prediction -> validation.committed() excludes it. unfalsifiable = uncommitted, held at the molecule layer
    exactly as at the percept layer.
  * Predictions are DERIVED from the abduced relation + observed targets, never from a game identity.
  * The per-transition signatures DISCRIMINATE a wrong relation from the right one (the property the ledger
    needs): acting in a world governed by BECOME(red) FALSIFIES BECOME(blue), because the changed cells
    became red, not blue.

Checkable relations (others -> None, honestly):
  BECOME(color)      changed cells take the target colour
  COVER(cells)       target (background) cells become non-background
  NONE.EXIST(color)  cells of the target colour disappear
  BE_AT(color,locus) the controllable's colour-centroid moves toward the locus
Generic fallback for any relation with a compiled measure:
  measure_progress   the molecule's own discrepancy measure decreases on transitions that changed the world
"""
import numpy as np


class MoleculeHyp:
    """A thin carrier so an abduced molecule is judged by validation.validate exactly like a percept
    component: it exposes `.prediction`. `.identity` is for the ledger's human-readable branch label."""
    __slots__ = ("identity", "relation", "prediction", "evidence", "confidence", "source")

    def __init__(self, identity, relation, prediction, source="abduction"):
        self.identity = identity
        self.relation = relation
        self.prediction = prediction          # dict|None ; None => uncommitted (validation.committed drops it)
        self.evidence = []
        self.confidence = 0.5
        self.source = source

    def __repr__(self):
        kind = (self.prediction or {}).get("kind", "uncommitted")
        return f"MoleculeHyp({self.identity}, {kind})"


def _as_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def predict(hyp, disc=None, grid0=None, bg=0):
    """Derive a checkable prediction dict for an abduced hypothesis. Returns None if the molecule's claim is
    not generically checkable (-> the molecule stays uncommitted).

    hyp: the abductor's dict (relation, target_color, controllable, locus/target_locus, ...).
    disc: the compiled Discrepancy (optional) -- supplies target cells (active) and the generic measure.
    grid0: a reference grid (optional) -- needed to read disc.active().
    """
    rel = (hyp.get("relation") if isinstance(hyp, dict) else None)
    col = _as_int(hyp.get("target_color")) if isinstance(hyp, dict) else None

    if rel == "BECOME" and col is not None:
        return dict(kind="relation", relation="BECOME", color=col)

    if rel in ("COVER",):
        cells = None
        if disc is not None and grid0 is not None and hasattr(disc, "active"):
            try:
                cells = set(map(tuple, disc.active(np.asarray(grid0))))
            except Exception:
                cells = None
        if not cells:
            cells = set(hyp.get("target_cells") or []) if isinstance(hyp, dict) else set()
        return dict(kind="relation", relation="COVER", cells=set(cells), bg=int(bg)) if cells else \
            _measure_fallback(disc)

    if rel in ("NONE.EXIST",) and col is not None:
        return dict(kind="relation", relation="NONE.EXIST", color=col)

    if rel in ("BE_AT", "TOUCH"):
        ctrl_color = _as_int(hyp.get("ctrl_color"))
        if ctrl_color is None:
            ctrl = hyp.get("controllable")
            ctrl_color = _as_int(ctrl) if not isinstance(ctrl, dict) else _as_int(ctrl.get("color"))
        locus = hyp.get("locus") or hyp.get("target_locus")
        if ctrl_color is not None and locus is not None and len(locus) == 2:
            return dict(kind="relation", relation="BE_AT", ctrl_color=ctrl_color,
                        locus=(float(locus[0]), float(locus[1])))
        return _measure_fallback(disc)

    # SAME (needs a template to be per-transition checkable) and any other relation: fall back to the
    # generic measure-progress check if a compiled measure exists, else uncommitted.
    return _measure_fallback(disc)


def _measure_fallback(disc):
    if disc is not None and hasattr(disc, "measure") and callable(getattr(disc, "measure")):
        return dict(kind="measure_progress", measure=disc.measure)
    return None


def molecule_from_hypothesis(hyp, disc=None, grid0=None, bg=0):
    """Wrap an abduced hypothesis as a MoleculeHyp carrying its checkable prediction (or None)."""
    p = predict(hyp, disc=disc, grid0=grid0, bg=bg)
    rel = hyp.get("relation") if isinstance(hyp, dict) else None
    col = hyp.get("target_color") if isinstance(hyp, dict) else None
    ident = f"{rel}({col})" if col is not None else f"{rel}"
    return MoleculeHyp(identity=ident, relation=rel, prediction=p)


def action_effect_molecules(per_action_signatures):
    """Lift ACTION-INDEXED CAUSAL-EFFECT molecules from observed per-action colour-transition signatures.

    per_action_signatures: dict  action -> set of (before_colour, after_colour) pairs that the action
    characteristically produced during probing. The molecule asserts the action reproduces (part of) its
    signature -- a LOCAL, CAUSAL, action-indexed claim, complementary to the abductor's global relations and
    matching ARC-3's action-indexed effects. Observation-grounded (signature read off probe transitions),
    so it is not a per-game rule: the SAME procedure runs on every game; the signature is measured."""
    mols = []
    for a, sig in (per_action_signatures or {}).items():
        sig = {tuple(p) for p in sig}
        if not sig:
            continue
        mols.append(MoleculeHyp(identity=f"ACT_EFFECT({a})", relation="ACTION_EFFECT",
                                prediction=dict(kind="action_effect", action=a, signature=sig),
                                source="observation"))
    return mols
