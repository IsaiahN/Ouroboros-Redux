"""nexus.reasoning -- the rich per-action reasoning payload, restored.

Mined (idea, not code) from the retired main line's DecisionReasoning (FINDINGS_mining...): every
action carries a structured, falsifiable narration into the API + the ledger, so the agent's thinking
is visible in the scorecard replay -- the thing that got lost when the clean kernel collapsed reasoning
to a one-line `why`. It is pure serialization: everything here is read off the ReduxPolicy object,
which already computes it; nothing new is reasoned.

Schema: regime / action / frame_read / rule_hypothesis / expect / disproof / status / step, plus a
`proposer` sub-block (what the proposer proposed this step -- the live hypotheses, the current pick,
the abduced objectives) so proposals are inspectable OVER TIME.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _frame_read(pol) -> str:
    fam = getattr(pol, "family", None)
    kinds = _safe(lambda: sorted(getattr(pol, "_referent_kinds_seen", []) or []), [])
    prog = _safe(lambda: pol.progress.best_colour(), None)
    bits = []
    if fam:
        bits.append("family=%s" % fam)
    if kinds:
        bits.append("referents=%s" % ",".join(map(str, kinds)))
    if prog is not None:
        bits.append("progress_colour=%s" % prog)
    return "; ".join(bits) or "(probing: controllable/roles not yet established)"


def proposer_section(pol) -> Dict[str, Any]:
    """What the proposer is putting forward this step -- the live hypothesis set + current pick."""
    probe = getattr(pol, "_probe", None)
    hyps = _safe(lambda: [str(h) for h in (getattr(probe, "hypotheses", []) or [])][:8], [])
    current = _safe(lambda: probe.current() if probe is not None else None, None)
    abduced = _safe(lambda: [str(a) for a in (getattr(pol, "abduced", []) or [])][:6], [])
    return {
        "candidates": hyps,
        "current": str(current) if current is not None else None,
        "idx": _safe(lambda: getattr(probe, "idx", None)),
        "locked": _safe(lambda: getattr(probe, "locked", None)),
        "abduced_objectives": abduced,
        "relation_selected": getattr(pol, "_relation_selected", None),
        "probe_rel": getattr(pol, "_probe_rel", None),
    }


def decision_reasoning(pol, action_label: str, data: Optional[dict], step: int, generation: int) -> Dict[str, Any]:
    prop = proposer_section(pol)
    rule = prop["current"] or (prop["abduced_objectives"][0] if prop["abduced_objectives"] else None) \
        or prop["relation_selected"]
    return {
        "regime": getattr(pol, "family", None) or "(detecting)",
        "action": action_label,
        "data": data,                                    # click coords etc., when present
        "frame_read": _frame_read(pol),
        "rule_hypothesis": str(rule) if rule else "(provisional objective -- a bet tested by acting)",
        "expect": "advances the objective; prediction-error residual falls if the read is right",
        "disproof": "residual stays high, or controllable/roles behave unlike this read -> RE-DERIVE mechanics",
        "status": "provisional -- only a level win confirms",
        "step": step,
        "generation": generation,
        "proposer": prop,                                # the proposer section, over time
    }


def compact_why(payload: Dict[str, Any]) -> str:
    """A one-line human summary kept alongside the structured payload (for logs/quick scan)."""
    return "g%s.s%s %s | reg=%s | hyp=%s" % (
        payload.get("generation"), payload.get("step"), payload.get("action"),
        payload.get("regime"), payload.get("rule_hypothesis"))
