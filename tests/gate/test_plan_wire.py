"""PREREG_PLAN_WIRE: the [PLAN-GATE] wire — which of the seven gates starves the planner?

Atoms exist but [PLAN] narration is 0 across all workers: a starvation bug. The EGO-PLAN
block has seven conjunctive gates that all fail silently; this build adds counters only
(zero behavior change) so the [PLAN-GATE] line names the first gate whose count collapses.
This test pins the counter block to the EGO-PLAN region (cycle path, BEFORE record_result)
so the 8000-char record_result->.credit window is never touched.
"""
from __future__ import annotations

import ast
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
    """AST wiring assertion (KNOBS A4-2; record/prereg/PREREG_SYMBOL_RECEIPTS.md
    section 2, law L4): the counter block never touches record_result -- NO
    `_plan_gate` Name/Attribute (nor its getattr string form) and NO
    "[PLAN-GATE]" narration anywhere inside def record_result's SUBTREE, and
    the same two tokens absent from record_result's exact source span
    (comments included).

    CONVERTED 2026-08-21 by the COMPOSER STAGE 4.5 structural repair, under the
    proctor's authorization, from the tail-slice proxy
    `"_plan_gate" not in src[src.index("def record_result"):]`. That slice
    swept every module-bottom helper BELOW the method (lines 4832-4975 at the
    time, all after record_result's end) as if it were inside record_result --
    so the module-bottom convention that protects registry receipts was the
    very thing the proxy forbade (stage 4's g7 rule increments the planner's
    dict from a module-bottom helper BY DESIGN, asserted by identity in
    tests/gate/test_composer_stage4.py F4). The structural fact is kept whole:
    the slice's reach over record_result's body is preserved EXACTLY (reads,
    writes, string forms, comments -- not only writes); only its reach over
    unrelated code after the body is dropped. Exemplar of the form:
    tests/gate/test_goal_spine.py::test_reward_wires_to_credit."""
    src = _src()
    fns = [n for n in ast.walk(ast.parse(src))
           if isinstance(n, ast.FunctionDef) and n.name == "record_result"]
    assert fns, "def record_result is missing from cognitive_loop"
    leaks = []
    for fn in fns:
        for n in ast.walk(fn):
            if isinstance(n, ast.Attribute) and n.attr == "_plan_gate":
                leaks.append(("attribute", n.lineno))
            elif isinstance(n, ast.Name) and n.id == "_plan_gate":
                leaks.append(("name", n.lineno))
            elif (isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and ("_plan_gate" in n.value or "[PLAN-GATE]" in n.value)):
                leaks.append(("string", n.lineno))
    assert not leaks, "_plan_gate / [PLAN-GATE] leaked into record_result: %r" % leaks
    lines = src.splitlines()
    for fn in fns:
        span = "\n".join(lines[fn.lineno - 1:fn.end_lineno])
        assert "_plan_gate" not in span, "_plan_gate leaked into record_result's span"
        assert "[PLAN-GATE]" not in span, "[PLAN-GATE] leaked into record_result's span"
