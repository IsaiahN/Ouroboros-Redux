"""validation.py -- the causal-history validation engine. Turns "articulate + course-correct" into a
mechanism, and "unfalsifiable = uncommitted" into an enforced rule.

The design (from the §11.33x discussion):
  * Causal history validates OUTCOMES, not reasoning. It is the agent's INTERNAL GAME GATE: did the
    predicted consequence happen. It must be PAIRED with descriptive alignment (the internal PROCTOR GATE)
    so a hypothesis that is right-for-the-wrong-reason, or a black-box win, is not mistaken for understanding.
  * DETECTION vs VERDICT: a prediction mismatch DETECTS; whether it is structural (re-type) or quantitative
    (observer correction) is the VERDICT (lives in persistent_model). This module does detection + the
    understanding gate.
  * PHASE-GATED: a violated prediction during EXPLORE is expected (provisional); during EXPLOIT it is a real
    falsification of a committed belief -> recalibrate. No oscillation while probing.
  * unfalsifiable = uncommitted: a component with no checkable prediction cannot be validated, so it cannot
    be committed -- committed() filters them out.

Predictions are STRUCTURED (dict with 'kind') so they are machine-checkable, not prose. A causal-history
entry is dict(action=..., clicked=(r,c)|None, before=grid, after=grid, won=bool, phase='explore'|'exploit').
"""
import numpy as np


def _changed(a, b):
    return set(map(tuple, np.argwhere(np.asarray(a) != np.asarray(b))))


def committed(components):
    """unfalsifiable = uncommitted: only components carrying a checkable prediction may be committed."""
    return [c for c in components if getattr(c, "prediction", None)]


def check_prediction(component, entry):
    """One causal-history entry vs a component's prediction. True=held, False=violated, None=not applicable."""
    p = getattr(component, "prediction", None)
    if not p:
        return None
    bf = np.asarray(entry["before"]); af = np.asarray(entry["after"]); ch = _changed(bf, af)
    kind = p.get("kind")
    if kind == "command":
        clicked = entry.get("clicked")
        if clicked is None:
            return None
        r, c = clicked
        if not (0 <= r < bf.shape[0] and 0 <= c < bf.shape[1]) or int(bf[r, c]) != p["color"]:
            return None                                   # not this command -> not applicable
        if not ch:
            return False                                  # predicted a transform, nothing happened
        return abs(len(ch) - p["size"]) <= max(2, int(0.5 * p["size"]))
    if kind == "constraint":
        if entry.get("action") != p.get("action"):
            return None
        return len(ch) == 0                               # predicted: no change
    if kind == "autonomous":
        cells = p.get("cells") or set()
        return (len(ch & cells) > 0) if cells else (len(ch) > 0)
    if kind in ("self_translate", "self_located"):
        if entry.get("action") is None and entry.get("clicked") is None:
            return None
        return len(ch) > 0                                # predicted: the controllable changes state
    if kind == "relation":
        # MOLECULE-layer causal check. Judges only transitions that CHANGED the world (a no-op transition
        # is not evidence for or against a relation -> None). The signature discriminates a wrong relation
        # from the right one, so the ledger can refute the specific molecule whose prediction broke.
        if not ch:
            return None
        rel = p.get("relation")
        if rel == "BECOME":
            col = p.get("color")
            return any(int(af[r, c]) == col for (r, c) in ch)         # held: a changed cell took target colour
        if rel == "COVER":
            cells = p.get("cells") or set()
            bg = p.get("bg", 0)
            tgt = ch & cells
            if not tgt:
                return None                                            # this transition touched no target cell
            return any(int(af[r, c]) != bg for (r, c) in tgt)         # held: a target cell became non-bg
        if rel == "NONE.EXIST":
            col = p.get("color")
            if not bool((bf == col).any()):
                return None                                            # colour absent -> nothing to disappear
            return any(int(bf[r, c]) == col and int(af[r, c]) != col for (r, c) in ch)  # target colour vanished
        if rel == "BE_AT":
            col = p.get("ctrl_color"); locus = p.get("locus")
            if col is None or locus is None:
                return None
            b = np.argwhere(bf == col); a = np.argwhere(af == col)
            if len(b) == 0 or len(a) == 0:
                return None
            db = float(np.hypot(*(b.mean(0) - np.asarray(locus, float))))
            da = float(np.hypot(*(a.mean(0) - np.asarray(locus, float))))
            return da < db - 1e-9                                      # held: controllable moved toward locus
        return None
    if kind == "action_effect":
        # ACTION-INDEXED CAUSAL effect -- the ARC-3 ontology the global relations (BECOME/BE_AT/NONE.EXIST/
        # COVER) cannot express. Applicable ONLY to the action this molecule is about; held if that action
        # reproduced at least one of its characteristic colour-transitions (before_colour -> after_colour).
        # Observation-grounded (the signature was read off probe transitions) and falsifiable (if the action
        # produces only off-signature transitions under exploit, it refutes). A no-op (blocked move) is not
        # evidence -> None, matching the relation-kind convention above.
        if entry.get("action") != p.get("action"):
            return None
        if not ch:
            return None
        sig = p.get("signature") or set()
        if not sig:
            return None
        obs = {(int(bf[r, c]), int(af[r, c])) for (r, c) in ch}
        return len(obs & sig) > 0
    if kind == "measure_progress":
        # generic molecule check: the molecule's OWN discrepancy measure must decrease on transitions that
        # changed the world. Causal: it is this molecule's measure, not a shared outcome.
        m = p.get("measure")
        if m is None or not ch:
            return None
        try:
            return float(m(af)) < float(m(bf)) - 1e-9
        except Exception:
            return None
    return None                                            # world_law etc. -> not generically checkable


def validate(component, history, phase="exploit"):
    """Aggregate a component's prediction over causal history. The verdict is driven by EXPLOIT-phase
    transitions -- those produced while ACTING ON a committed objective, where a violation is load-bearing
    (a real refutation). EXPLORE-phase transitions (undirected probing) are expected to be noisy and never
    force a verdict, so a correct hypothesis is not falsified by random exploration. Per-entry phase
    (entry['phase']) takes precedence; the `phase` arg is the fallback for entries that carry none."""
    pairs = [(check_prediction(component, e), e.get("phase", phase)) for e in history]
    applic = [(x, ph) for (x, ph) in pairs if x is not None]
    if not applic:
        return dict(verdict="untested", recalibrate=False, hold_rate=None, n=0)
    exploit = [x for (x, ph) in applic if ph == "exploit"]
    if not exploit:                                       # only undirected (explore) evidence so far
        rate = sum(1 for (x, ph) in applic if x) / len(applic)
        return dict(verdict="provisional", recalibrate=False, hold_rate=round(rate, 2), n=len(applic))
    rate = sum(1 for x in exploit if x) / len(exploit)
    if rate >= 0.8:
        return dict(verdict="confirmed", recalibrate=False, hold_rate=round(rate, 2), n=len(exploit))
    return dict(verdict="falsified", recalibrate=True, hold_rate=round(rate, 2), n=len(exploit),
                note="committed prediction violated under EXPLOIT -> revise the hypothesis (detection; "
                     "verdict structural-vs-quantitative resolved by persistent_model.classify_error)")


def is_understanding(components, history):
    """The internal PROCTOR gate. A win counts as UNDERSTANDING only if a committed component's checkable
    prediction was actually TESTED and HELD on the path to it. A win with no satisfied committed prediction
    is a BLACK-BOX reward stumble -- exactly the lp85 trap, caught from the inside this time."""
    if not any(e.get("won") for e in history):
        return dict(win=False, explained=False, note="no win in this history")
    tested = held = False
    for c in committed(components):
        for e in history:
            r = check_prediction(c, e)
            if r is not None:
                tested = True
                if r:
                    held = True
    explained = bool(tested and held)
    return dict(win=True, explained=explained,
                note=("a committed, falsifiable prediction was tested and held on the path to the win "
                      "-> UNDERSTANDING" if explained else
                      "win with no satisfied committed prediction -> BLACK-BOX (uncommitted; do not trust)"))
