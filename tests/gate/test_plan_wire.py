"""PREREG_PLAN_WIRE: the [PLAN-GATE] wire — which of the seven gates starves the planner?

Atoms exist but [PLAN] narration is 0 across all workers: a starvation bug. The EGO-PLAN
block has seven conjunctive gates that all fail silently; this build adds counters only
(zero behavior change) so the [PLAN-GATE] line names the first gate whose count collapses.
This test pins the counter block to the EGO-PLAN region (cycle path, BEFORE record_result)
so the 8000-char record_result->.credit window is never touched.
"""
from __future__ import annotations

import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOOP = os.path.join(REPO, "cognitive_loop.py")


def _src():
    with open(LOOP, encoding="utf-8") as f:
        return f.read()


def test_plan_gate_counters_in_ego_plan_region():
    """[PLAN-GATE] narration + _plan_gate counters live INSIDE the EGO-PLAN block."""
    src = _src()
    a = src.index("W4c (EGO-PLAN)")
    b = src.index("C33 STEP 1", a)
    region = src[a:b]
    assert "[PLAN-GATE]" in region, "no [PLAN-GATE] narration in the EGO-PLAN block"
    assert "_plan_gate" in region, "no _plan_gate counter dict in the EGO-PLAN block"
    for k in ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "shadow", "drive", "cycles"):
        assert '"%s"' % k in region, "gate counter key %r missing" % k


def test_plan_gate_stays_out_of_record_result():
    """The counter block must NOT appear at/after record_result (8000-char .credit window)."""
    src = _src()
    tail = src[src.index("def record_result"):]
    assert "_plan_gate" not in tail, "_plan_gate leaked into/after record_result"
    assert "[PLAN-GATE]" not in tail, "[PLAN-GATE] leaked into/after record_result"
