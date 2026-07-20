"""
prediction_error_bus.py -- Phase 1 of the self-reasoning spine.

ONE in-process bus that every binding layer (segmentation -> roles -> causal ->
objective -> component) PUBLISHES a (predicted, observed) pair into, and that
returns a LOCALIZED, CONFIDENCE-WEIGHTED attribution: which layer, which object,
how big the residual, and how much to trust the attribution.

Why it exists: it is the mechanism that turns "the human tells it WHICH binding is
wrong" into "it localizes which binding is wrong." It does that only as far as the
forward model and the confidence weighting allow -- and the confidence weighting is
the SAFEGUARD. A layer whose predictor is historically unreliable produces
LOW-confidence attributions, so a wrong prediction cannot masquerade as a sharp
localization. That is the offline-over-optimism failure mode (a real number moving
the right way on a fragment, mistaken for truth) kept from being rebuilt INSIDE the
agent. Precision-weighting is not polish; it is the brake.

SCOPE HONESTY: publishing an attribution is a SOUNDNESS event (a prediction was made
and compared). Whether the localization is CORRECT on a live game is a game-gate
claim -- Isaiah's, from watching the run -- exactly like every other correctness
claim in this project. This module manufactures the signal; it does not certify it.

Stdlib only. No I/O, no network, no persistent state, no external calls. Kaggle-safe
in-process. Callers wrap every entry point in try/except so the bus can never crash a
solve; internally it is defensive too.
"""

import math

# The binding hierarchy, coarse->fine cause order. "component" = a validation-verdict
# carrier (a molecule/percept judged by validation.validate).
LAYERS = ("segmentation", "roles", "causal", "objective", "component")

_EPS = 1e-9


# --------------------------------------------------------------------------- store
def _bus(mem):
    """The per-game bus lives inside the same _game_mem dict as causal/derivation."""
    b = mem.setdefault("pe_bus", None)
    if b is None:
        b = mem["pe_bus"] = {"log": [], "precision": {}, "t": 0}
    b.setdefault("log", [])
    b.setdefault("precision", {})
    b.setdefault("t", 0)
    return b


def _precision(mem, layer):
    """Running reliability of `layer`'s predictor in [0,1], Laplace-smoothed, start 0.5.
    High = this layer's predictions have historically held; its errors are trustworthy.
    Low  = this layer mispredicts a lot; discount its attributions."""
    p = _bus(mem)["precision"].get(layer)
    if not p:
        return 0.5
    h, m = p.get("hits", 0), p.get("misses", 0)
    return (h + 1.0) / (h + m + 2.0)


def _bump(mem, layer, hit):
    p = _bus(mem)["precision"].setdefault(layer, {"hits": 0, "misses": 0})
    p["hits" if hit else "misses"] += 1


# ----------------------------------------------------------------------- attribution
def _residual(predicted, observed):
    """Structured residual + a magnitude in [0,1]. Handles the shapes the layers speak:
    labels ('active'/'inert', 'reduce'/'change'), numbers (objective distance), and
    tuples/regions (centroids). Unknown shapes fall back to equality."""
    kind = "match"
    mag = 0.0
    try:
        if isinstance(predicted, (int, float)) and isinstance(observed, (int, float)):
            kind = "scalar"
            denom = max(abs(predicted), abs(observed), 1.0)
            mag = min(1.0, abs(float(predicted) - float(observed)) / denom)
        elif (isinstance(predicted, (tuple, list)) and isinstance(observed, (tuple, list))
              and len(predicted) == len(observed) == 2):
            kind = "region"
            d = abs(predicted[0] - observed[0]) + abs(predicted[1] - observed[1])
            mag = min(1.0, d / 16.0)               # 16 cells ~ full-grid divergence
        else:
            kind = "label"
            mag = 0.0 if predicted == observed else 1.0
    except Exception:
        mag = 0.0 if predicted == observed else 1.0
    return {"predicted": predicted, "observed": observed, "kind": kind, "magnitude": round(mag, 3)}


def _find_open(mem, layer, obj_key):
    for a in _bus(mem)["log"]:
        if not a.get("resolved") and a["layer"] == layer and a["obj"] == obj_key:
            return a
    return None


def publish(mem, layer, obj, predicted, observed, sharpness=1.0, note="", emit=None):
    """Publish one (predicted, observed) at `layer` for `obj`. Returns the attribution
    dict if it is a real, UNRESOLVED error, else None.

    DEDUP + RESOLVE (the Phase-1 completion): a re-observed error with the same
    (layer, obj) is REFRESHED in place (seen++), NOT re-appended -- so a plateau that
    recurs every re-attempt does not flood the log or tank precision. Precision updates
    only on DISTINCT evidence (a first miss, or a hit), never on a re-log -- so the
    confidence weighting reflects the predictor's real reliability, not how many times
    the same unresolved error was re-emitted. A HIT (prediction now holds) RESOLVES any
    open error for that key -- e.g. a conditionally-gated control that reduces after the
    state advanced clears its own coverage error.

    sharpness in [0,1]: strength of the prediction. confidence = precision(layer, BEFORE
    this sample) * sharpness."""
    try:
        b = _bus(mem)
        b["t"] += 1
        ok = _obj_key(obj)
        res = _residual(predicted, observed)
        hit = res["magnitude"] <= _EPS
        open_attr = _find_open(mem, layer, ok)
        if hit:
            _bump(mem, layer, True)                            # distinct evidence: prediction held
            if open_attr is not None:                          # a HIT clears the open error for this key
                open_attr["resolved"] = True
                if emit is not None:
                    try: emit("RESOLVE  %s:%s  prediction now holds" % (layer, ok))
                    except Exception: pass
            return None
        if open_attr is not None:                              # RE-LOG of an existing open error -> refresh in place
            open_attr["seen"] = open_attr.get("seen", 1) + 1
            open_attr["t"] = b["t"]
            open_attr["residual"] = res; open_attr["magnitude"] = res["magnitude"]
            if note: open_attr["note"] = note
            return open_attr                                   # NO precision bump (not new evidence), NO re-emit
        _bump(mem, layer, False)                               # distinct evidence: a NEW miss
        conf = round(max(0.0, min(1.0, _precision(mem, layer) * float(sharpness))), 3)
        attr = {"t": b["t"], "layer": layer, "obj": ok, "seen": 1,
                "residual": res, "magnitude": res["magnitude"], "confidence": conf,
                "note": note, "resolved": False}
        b["log"].append(attr)
        if emit is not None:
            try:
                emit("ATTRIBUTE  %s:%s  predicted=%s observed=%s  [residual=%.2f conf=%.2f]%s"
                     % (layer, ok, _short(predicted), _short(observed),
                        attr["magnitude"], attr["confidence"], ("  " + note) if note else ""))
            except Exception:
                pass
        return attr
    except Exception:
        return None


def ingest_verdict(mem, component, verdict, emit=None):
    """Map a validation.validate() result into a component-layer attribution. A
    'falsified' verdict (recalibrate=True) is a committed prediction that broke ->
    a real, localizable error. 'provisional'/'confirmed'/'untested' are not errors."""
    try:
        if not isinstance(verdict, dict):
            return None
        if verdict.get("verdict") != "falsified":
            # still feed precision: a confirmed/provisional hold is evidence the
            # component predictor is reliable.
            if verdict.get("verdict") in ("confirmed", "provisional"):
                _bump(mem, "component", True)
            return None
        hold = verdict.get("hold_rate")
        sharp = 1.0 if (isinstance(hold, (int, float)) and hold < 0.5) else 0.6
        return publish(mem, "component", component, predicted="holds",
                       observed="falsified", sharpness=sharp,
                       note="recalibrate (hold_rate=%s, n=%s)" % (hold, verdict.get("n")),
                       emit=emit)
    except Exception:
        return None


# --------------------------------------------------------------------------- readers
def top_error(mem, layer=None, min_conf=0.0):
    """Highest (magnitude * confidence) UNRESOLVED attribution -- what to revise next.
    Consumed by later phases (anomaly-refine, probe-selection, System-2 gate)."""
    try:
        cand = [a for a in _bus(mem)["log"]
                if not a.get("resolved")
                and (layer is None or a["layer"] == layer)
                and a["confidence"] >= min_conf]
        if not cand:
            return None
        return max(cand, key=lambda a: a["magnitude"] * a["confidence"])
    except Exception:
        return None


def localized_errors(mem, k=6, min_conf=0.0):
    """Ranked unresolved attributions -- the agent's answer to 'which binding is wrong'."""
    try:
        cand = [a for a in _bus(mem)["log"]
                if not a.get("resolved") and a["confidence"] >= min_conf]
        cand.sort(key=lambda a: a["magnitude"] * a["confidence"], reverse=True)
        return cand[:k]
    except Exception:
        return []


# --------------------------------------------------- Phase-2 readers (reflex + effort gate)
def persistent_errors(mem, min_seen=2, min_conf=0.0):
    """Unresolved errors seen >= min_seen times -- the HYSTERESIS filter for the anomaly
    reflex. A single cold-probe anomaly is NOT acted on; only an error that RECURS (the
    prediction kept failing) earns a refine. Ranked by magnitude*confidence."""
    try:
        cand = [a for a in _bus(mem)["log"]
                if not a.get("resolved") and a.get("seen", 1) >= min_seen
                and a["confidence"] >= min_conf]
        cand.sort(key=lambda a: a["magnitude"] * a["confidence"], reverse=True)
        return cand
    except Exception:
        return []


def surprise(mem):
    """A scalar in [0,1]: the strongest current UNRESOLVED prediction error
    (max magnitude*confidence). Low => the model's predictions are holding, coast on the
    cached policy; high => something the agent believed just broke, deliberate. This is the
    System-2 trigger -- effort follows surprise, not the clock."""
    try:
        cand = [a["magnitude"] * a["confidence"] for a in _bus(mem)["log"] if not a.get("resolved")]
        return round(max(cand), 3) if cand else 0.0
    except Exception:
        return 0.0


def should_deliberate(mem, threshold=0.25):
    """Gate deep composition on surprise. True => invoke the composer/refine; False =>
    surprise is low, coast. Advisory: callers keep their own floors."""
    try:
        return surprise(mem) >= float(threshold)
    except Exception:
        return True                                           # fail OPEN: never suppress deliberation on a bus error


def resolve(mem, attr):
    """Mark an attribution handled (a layer revised in response)."""
    try:
        if isinstance(attr, dict):
            attr["resolved"] = True
    except Exception:
        pass


def summary(mem, k=6):
    """Compact human/grammar-readable 'which binding is wrong', confidence-ranked.
    This is the Phase-1 exit surface: the agent NAMING the failing binding."""
    out = []
    for a in localized_errors(mem, k=k):
        out.append("%s:%s  %s->%s  (mag=%.2f, conf=%.2f)%s"
                   % (a["layer"], a["obj"], _short(a["residual"]["predicted"]),
                      _short(a["residual"]["observed"]), a["magnitude"], a["confidence"],
                      ("  " + a["note"]) if a["note"] else ""))
    return out


def precision_report(mem):
    """Per-layer reliability -- how much to trust each layer's attributions."""
    return {L: round(_precision(mem, L), 3) for L in LAYERS if L in _bus(mem)["precision"]}


# ----------------------------------------------------------------------------- utils
def _obj_key(obj):
    try:
        if isinstance(obj, (tuple, list)):
            return "@" + ",".join(str(x) for x in obj)
        return str(obj)
    except Exception:
        return "?"


def _short(v):
    try:
        if isinstance(v, float):
            return ("%.1f" % v)
        if isinstance(v, (tuple, list)):
            return "(" + ",".join(_short(x) for x in v) + ")"
        s = str(v)
        return s if len(s) <= 18 else s[:17] + "\u2026"
    except Exception:
        return "?"
