"""PREREG_PLAN_WIRE: the [PLAN-GATE] wire — which of the seven gates starves the planner?

Atoms exist but [PLAN] narration is 0 across all workers: a starvation bug. The EGO-PLAN
block has seven conjunctive gates that all fail silently; this build adds counters only
(zero behavior change) so the [PLAN-GATE] line names the first gate whose count collapses.

BOTH TESTS HERE ARE LAW L4 (record/prereg/PREREG_SYMBOL_RECEIPTS.md §2). The fact is
one fact and it is stated once, in tests/gate/_ast_laws.py: the gate counters are
initialised and narrated on the CYCLE path, before the bet commit, and never on the
result path. The names are kept so the history is followable.

WHAT THE OLD FORMS WERE, AND WHY THEY WENT:
  * the region form (`src.index("W4c (EGO-PLAN)") … src.index("C33 STEP 1")`) checked
    that the counter keys appeared as literal text between two comment banners;
  * the tail form (`"_plan_gate" not in src[src.index("def record_result"):]`) swept
    every MODULE-BOTTOM HELPER below the class — lines 4832-4975 at the time, all of
    them after record_result ends — as though they sat inside the method. Module-bottom
    appending is the convention that keeps registry receipts from rotting, and stage 4's
    g7 rule increments this very dict from a module-bottom helper BY DESIGN
    (tests/gate/test_composer_stage4.py F4 asserts it by identity). One position-based
    discipline forbidding another; containment has no such conflict.
The tail form's REACH OVER RECORD_RESULT'S BODY is preserved exactly — reads, writes and
string forms, not only writes — by L4's subtree check. Only its reach over unrelated code
after the body is dropped.
"""
from __future__ import annotations

import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOOP = os.path.join(REPO, "cognitive_loop.py")


def _laws():
    """The shared law bodies (tests/gate/_ast_laws.py). tests/gate is not a
    package, so it is loaded by path and cached in sys.modules for the
    session -- one body per law, one place to argue with it."""
    mod = sys.modules.get("_ouro_ast_laws")
    if mod is None:
        spec = importlib.util.spec_from_file_location(
            "_ouro_ast_laws",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ast_laws.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_ouro_ast_laws"] = mod
        spec.loader.exec_module(mod)
    return mod


def test_plan_gate_counters_in_ego_plan_region():
    """L4, the positive half: [PLAN-GATE] narration + the ten-key _plan_gate counter
    dict are initialised inside CognitiveLoop.cycle, before the bet is committed."""
    _laws().l4_plan_gate_on_the_cycle_path()


def test_plan_gate_stays_out_of_record_result():
    """L4, the negative half: NO `_plan_gate` Name/Attribute and NO `_plan_gate` /
    "[PLAN-GATE]" string constant anywhere inside record_result's SUBTREE."""
    _laws().l4_plan_gate_on_the_cycle_path()
