"""THE STRUCTURAL LAWS OF THE LOOP -- AST order, never character distance.

Not a test module (no ``test_`` names, nothing collected here). Seven laws
live here; seven tests across six gate files keep their own names and delegate
their bodies to them, so a law has ONE body and one place to be argued with.

WHY THIS FILE EXISTS (PREREG_SYMBOL_RECEIPTS.md section 2; KNOBS A4-2, queued
2026-08-14). Six of these laws were written as CHARACTER WINDOWS -- ``the
.credit( call appears within 8000 characters of "def record_result"`` -- and a
seventh as a POSITION (``_gate_step`` is the module's last function). A window
is a proxy for a structural fact, and a proxy has a budget: on 2026-08-21 the
budget ran out at 50 characters of headroom on ``.credit`` and 15 on
``.route``, and the two disciplines collided head-on --

  * the ``_plan_gate`` law took the file TAIL after ``def record_result`` and
    forbade the tokens in it, which swept every MODULE-BOTTOM HELPER (lines
    4832-4975, all of them AFTER record_result ends at 3005) as though they
    were inside the method;
  * module-bottom appending is the convention that protects registry receipts
    from rotting, and stage 4's g7 rule increments the planner's counter dict
    from a module-bottom helper BY DESIGN.

So one position-based discipline forbade the other. The AST form dissolves the
conflict rather than trading one off: every law below states the fact it was
always a proxy for, and states it as containment and order in the tree.

WHAT A LAW MAY ASSERT: containment (``X is inside Y``), order (``X precedes Y``
in statement order within one scope), count (``exactly one X``), and shape (a
dict's keys, a constant's text). Never a line number, never a character offset,
never a position among siblings.

Each law raises ``AssertionError`` with the fact it protects named in the
message, or returns None.
"""
from __future__ import annotations

import ast
import functools
import glob
import os
from typing import Iterable, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOOP = os.path.join(REPO, "cognitive_loop.py")

# The same production scope the wiring gate uses: the live path. Tests and
# tools are instruments, never the live path.
PROD_GLOBS = ("*.py", "engines/**/*.py", "rungs/**/*.py", "src/**/*.py")
PROD_EXCLUDE_NAMES = ("_temp_check.py", "vulture_whitelist.py")

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


# ─────────────────────────────────────────────────────────────────────────────
# Primitives: inside / precedes / nth-call
# ─────────────────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=8)
def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


@functools.lru_cache(maxsize=8)
def _parse(path: str) -> ast.Module:
    return ast.parse(_read(path))


def source(path: Optional[str] = None) -> str:
    # LOOP is read at CALL time, not bound as a default, so a falsifier can
    # point the laws at a scratch copy of the loop and re-run them.
    return _read(path or LOOP)


def tree(path: Optional[str] = None) -> ast.Module:
    return _parse(path or LOOP)


def reload_source() -> None:
    """Drop the cached parse -- for falsifiers that rewrite the loop."""
    _read.cache_clear()
    _parse.cache_clear()


def scope(node: ast.AST, qualname: str) -> ast.AST:
    """The def/class node named by ``qualname`` (dotted), searched from
    ``node``. Raises AssertionError if it does not exist -- a law about a
    function that is gone is a red, not a skip."""
    cur: ast.AST = node
    for part in qualname.split("."):
        found = None
        for child in ast.walk(cur) if cur is node else ast.iter_child_nodes(cur):
            if isinstance(child, _SCOPES) and child.name == part:
                found = child
                break
        assert found is not None, (
            "%r does not exist -- the law cannot be checked because the scope "
            "it is about is gone" % qualname)
        cur = found
    return cur


def calls(node: ast.AST, name: str) -> List[ast.Call]:
    """Every ``ast.Call`` inside ``node`` whose callee is written ``name``
    (a bare Name or the final attribute of a dotted path), in (line, col)
    order. Callee-only by design: the receiver is not encoded (prereg PROCTOR
    decision 3 -- receiver-qualified matching is QUEUED, not built, and the
    false positive it leaves open is a ``.credit`` on the wrong object)."""
    out = [n for n in ast.walk(node) if isinstance(n, ast.Call)
           and ((isinstance(n.func, ast.Name) and n.func.id == name)
                or (isinstance(n.func, ast.Attribute) and n.func.attr == name))]
    out.sort(key=lambda n: (n.lineno, n.col_offset))
    return out


def refs(node: ast.AST, name: str) -> List[ast.AST]:
    """Every Name/Attribute of ``name`` inside ``node``, call-callees
    included -- the reach a "must not appear here" law needs."""
    out = [n for n in ast.walk(node)
           if (isinstance(n, ast.Name) and n.id == name)
           or (isinstance(n, ast.Attribute) and n.attr == name)]
    out.sort(key=lambda n: (n.lineno, n.col_offset))
    return out


def strings(node: ast.AST, needle: str) -> List[ast.Constant]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Constant)
            and isinstance(n.value, str) and needle in n.value]


def pos(node: ast.AST) -> Tuple[int, int]:
    return (node.lineno, node.col_offset)


def precedes(a: ast.AST, b: ast.AST) -> bool:
    """Statement order inside one tree: a's position is before b's."""
    return pos(a) < pos(b)


def inside(container: ast.AST, node: ast.AST) -> bool:
    return any(n is node for n in ast.walk(container))


def _prod_files() -> List[str]:
    out, seen = [], set()
    for pat in PROD_GLOBS:
        for path in glob.glob(os.path.join(REPO, pat), recursive=True):
            rel = os.path.relpath(path, REPO).replace("\\", "/")
            if rel in seen or "__pycache__" in rel:
                continue
            base = os.path.basename(rel)
            if base.startswith("_investigate") or base in PROD_EXCLUDE_NAMES:
                continue
            seen.add(rel)
            out.append(rel)
    return sorted(out)


def production_calls(name: str) -> List[str]:
    """``file:line`` of every CALL of ``name`` across the production globs."""
    out: List[str] = []
    for rel in _prod_files():
        try:
            with open(os.path.join(REPO, rel), encoding="utf-8",
                      errors="ignore") as fh:
                t = ast.parse(fh.read())
        except (OSError, SyntaxError):
            continue
        out += ["%s:%d" % (rel, c.lineno) for c in calls(t, name)]
    return sorted(out)


def _where(nodes: Iterable[ast.AST]) -> str:
    return ", ".join("line %d" % n.lineno for n in nodes) or "nowhere"


# ─────────────────────────────────────────────────────────────────────────────
# L1 -- the spine is credited inside record_result
# ─────────────────────────────────────────────────────────────────────────────

def l1_credit_inside_record_result() -> None:
    """FACT: reward-disposes. A level-up CONFIRMS a candidate goal, and the
    confirmation happens on the OUTCOME path -- inside
    ``CognitiveLoop.record_result``, where the outcome is known. Nothing else
    may confirm a goal.

    WAS: ``0 <= src[src.find("def record_result"):].find(".credit(") < 8000``
    -- a proxy for exactly this containment (KNOBS A4-2 says so in as many
    words), with 50 characters of headroom left at HEAD."""
    rr = scope(tree(), "CognitiveLoop.record_result")
    assert calls(rr, "credit"), (
        "record_result never credits the spine on a level-up -- "
        "reward-disposes is the ONLY confirmation path and it is unwired "
        "(starvation).")


# ─────────────────────────────────────────────────────────────────────────────
# L2 -- every settlement routes through the residual router in record_result
# ─────────────────────────────────────────────────────────────────────────────

def l2_route_inside_record_result() -> None:
    """FACT: every settlement is routed by the residual router, on the outcome
    path, inside ``record_result``. A settlement that reaches the books
    without routing is an unattributed residual.

    WAS: the 20000-character ``.route(`` window, 15 characters of headroom."""
    rr = scope(tree(), "CognitiveLoop.record_result")
    assert calls(rr, "route"), (
        "record_result never routes a settlement through the residual router "
        "-- every settlement must be attributed (bank-core's note).")


# ─────────────────────────────────────────────────────────────────────────────
# L3 -- settle before bank
# ─────────────────────────────────────────────────────────────────────────────

def l3_settle_before_bank() -> None:
    """FACT (its OWN justification, per Seat 4's rider -- NOT "it protects
    L2's window", which is the thing being retired):

        A LEVEL-UP MAY ONLY BE BANKED AS A GOAL HYPOTHESIS AFTER THE STEP THAT
        PRODUCED IT HAS BEEN SETTLED AND ROUTED.

    ``_goal_abd`` banks the level-up frame delta as a hypothesis about WHAT
    CAUSED the advance. The residual router is what decides how much of the
    change is attributable to the agent's own action at all. Bank first and the
    hypothesis is formed from an unattributed delta -- the goal book learns
    from a frame the loop has not yet decided the agent caused. The order is
    therefore semantic, not economic: SETTLE, THEN BANK.

    The old form asserted ``body.find("_goal_abd(") > body.find(".route(")``
    -- character offsets from a string search, which is the same order claim
    made in the one currency that also moves when anything above it moves."""
    rr = scope(tree(), "CognitiveLoop.record_result")
    abd = calls(rr, "_goal_abd")
    rte = calls(rr, "route")
    assert abd, (
        "record_result never banks the level-up frame delta -- goal abduction "
        "is unwired (starvation)")
    assert rte, "record_result never routes -- L2 is broken, so L3 is unstatable"
    assert precedes(rte[0], abd[0]), (
        "SETTLE-BEFORE-BANK violated: the first route() is at line %d and "
        "_goal_abd( is at line %d. A level-up banked before the step is routed "
        "forms a goal hypothesis out of a delta the loop has not yet decided "
        "the agent caused." % (rte[0].lineno, abd[0].lineno))


# ─────────────────────────────────────────────────────────────────────────────
# L4 -- the plan-gate counters live on the cycle path, never the result path
# ─────────────────────────────────────────────────────────────────────────────

def l4_plan_gate_on_the_cycle_path() -> None:
    """FACT: the seven plan gates are counted and narrated where the decision
    is MADE -- on the cycle path, before the bet is committed -- and never on
    the result path. A counter incremented in ``record_result`` would be
    counting after the outcome is known, which is how a gate diagnostic turns
    into a post-hoc story about why the plan was right.

    Module-bottom helpers that increment the same dict are LEGAL BY DESIGN
    (stage 4's g7 rule, asserted by identity in test_composer_stage4.py F4).
    The retired tail-slice form forbade them, because a slice of the file
    after ``def record_result`` contains every helper appended below the
    class -- and module-bottom appending is the convention that keeps registry
    receipts from rotting. Two position-based disciplines, in direct conflict;
    containment has no such conflict."""
    cy = scope(tree(), "CognitiveLoop.cycle")
    rr = scope(tree(), "CognitiveLoop.record_result")

    assigns = [n for n in ast.walk(cy) if isinstance(n, ast.Assign)
               for t in n.targets
               if isinstance(t, ast.Attribute) and t.attr == "_plan_gate"]
    assert assigns, (
        "no `self._plan_gate = {...}` inside CognitiveLoop.cycle -- the gate "
        "counters are not initialised on the decision path")
    dicts = [n.value for n in assigns if isinstance(n.value, ast.Dict)]
    assert dicts, "_plan_gate is assigned in cycle but not from a dict literal"
    keys = {k.value for d in dicts for k in d.keys
            if isinstance(k, ast.Constant)}
    want = {"g1", "g2", "g3", "g4", "g5", "g6", "g7", "shadow", "drive", "cycles"}
    assert want <= keys, (
        "the plan-gate counter dict is missing %r -- a gate with no counter "
        "cannot be the one named as starving the planner" % sorted(want - keys))

    narration = strings(cy, "[PLAN-GATE]")
    assert narration, "no [PLAN-GATE] narration on the cycle path"

    commits = calls(cy, "commit")
    assert commits, "cycle never commits a bet -- the ordering claim is unstatable"
    first_commit = commits[0]
    assert precedes(assigns[0], first_commit), (
        "the plan-gate counters are initialised AFTER the bet is committed "
        "(init line %d, commit line %d) -- the gates must be counted while "
        "the decision is still being made"
        % (assigns[0].lineno, first_commit.lineno))

    leaks = ([("attribute/name", n.lineno) for n in refs(rr, "_plan_gate")]
             + [("string", n.lineno) for n in strings(rr, "_plan_gate")]
             + [("string", n.lineno) for n in strings(rr, "[PLAN-GATE]")])
    assert not leaks, (
        "_plan_gate / [PLAN-GATE] leaked into record_result's SUBTREE at %r -- "
        "the result path must not touch the decision-path counters" % (leaks,))

    # The tail slice's reach OVER RECORD_RESULT'S OWN BODY is preserved exactly
    # -- comments included, not only the tokens the AST can see. This is the
    # method's own span, not a slice of the file after it: the difference is
    # the whole finding.
    span = "\n".join(source().splitlines()[rr.lineno - 1:rr.end_lineno])
    for tok in ("_plan_gate", "[PLAN-GATE]"):
        assert tok not in span, (
            "%r appears in record_result's source span (a comment or a "
            "fragment the AST does not carry) -- the result path must not "
            "mention the decision-path counters at all" % tok)


# ─────────────────────────────────────────────────────────────────────────────
# L5 -- the abduced plan's site becomes the action
# ─────────────────────────────────────────────────────────────────────────────

def l5_abduced_plan_becomes_the_action() -> None:
    """FACT: the abduced plan is a DECIDER, not a reader. Its ``site`` becomes
    the action the agent takes, on the same path, before the bet is committed
    -- otherwise the whole hypotheses -> top -> abduced_plan chain is an abort
    path wearing a plan's clothes.

    WAS: ``region[i:i+2000]`` after the string ``abduced_plan(`` inside a
    comment-delimited slice of the source."""
    cy = scope(tree(), "CognitiveLoop.cycle")
    ap = calls(cy, "abduced_plan")
    assert ap, (
        "cycle never calls abduced_plan -- the EGO-PLAN block never tries the "
        "abduced target")
    commits = calls(cy, "commit")
    assert commits and precedes(ap[0], commits[0]), (
        "abduced_plan is consulted at or after the bet commit (%s vs %s) -- a "
        "plan that arrives after the bet cannot change the action"
        % (_where(ap[:1]), _where(commits[:1])))

    after = [n for n in ast.walk(cy)
             if getattr(n, "lineno", None) is not None and precedes(ap[0], n)]
    six = [n for n in after if isinstance(n, ast.Assign)
           for t in n.targets if isinstance(t, ast.Name) and t.id == "action_num"
           and isinstance(n.value, ast.Constant) and n.value.value == 6]
    assert six, (
        "no `action_num = 6` after the abduced_plan call inside cycle -- the "
        "abduced plan's site never becomes an action")
    data = [n for n in after if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "action_data"
                    for t in n.targets)
            and _reads_ap_site(n.value)]
    assert data, (
        "`action_data` is never built from _ap[\"site\"] after the abduced_plan "
        "call -- the consumer is a reader, not a decider")
    assert strings(cy, "[PLAN]"), "no [PLAN] narration on the cycle path"


def _reads_ap_site(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Subscript)
               and isinstance(n.value, ast.Name) and n.value.id == "_ap"
               and isinstance(n.slice, ast.Constant) and n.slice.value == "site"
               for n in ast.walk(node))


# ─────────────────────────────────────────────────────────────────────────────
# L6 -- lp_steer is consumed at exactly one site, in the action path
# ─────────────────────────────────────────────────────────────────────────────

def l6_lp_steer_is_the_one_consumption_site() -> None:
    """FACT: the LP drive is an ARM of a live control experiment. It has ONE
    consumption point, in the loop's action selection (``CognitiveLoop._act``),
    so the arm contrast is a contrast of one decision and not of a diffuse set
    of nudges. A second call site anywhere in production would make the arm
    unmeasurable.

    WAS: the string ``lp_steer`` appearing between two comment banners, plus
    the 8000/20000 windows carried along for the ride. Uniqueness -- the part
    that actually makes the experiment readable -- was never checked at all."""
    sites = production_calls("lp_steer")
    assert len(sites) == 1, (
        "lp_steer is called from %d production sites (%r) -- the LP arm is "
        "readable only if there is exactly ONE consumption point"
        % (len(sites), sites))
    act = scope(tree(), "CognitiveLoop._act")
    assert calls(act, "lp_steer"), (
        "the one lp_steer call is not inside CognitiveLoop._act (%r) -- the "
        "consumption belongs at the explore-widen site in action selection"
        % sites)


# ─────────────────────────────────────────────────────────────────────────────
# L7 -- the gate hook is a MODULE-LEVEL def (added 2026-08-21)
# ─────────────────────────────────────────────────────────────────────────────

def l7_gate_hook_is_module_level() -> None:
    """FACT (read out of test_gate_stage1.py, which stated it as "the module's
    LAST function"): the shadow gate's hook is a MODULE-LEVEL ``def`` -- not
    nested inside a function, not a method on ``CognitiveLoop`` -- so that
    adding it moved no line inside the class, rotted no receipt, and left the
    loop's body untouched. The gate observes and blocks nothing; its hook must
    weigh nothing structurally.

    "LAST in the file" was a PROXY for that, and a proxy of the exact genus
    this build retires: it made every LATER module-bottom helper illegal, so
    the persistence builder had to place its own helper ABOVE the hook -- a
    build shaped by a gate rather than by design, the second such collision
    this week (the first was the _plan_gate tail slice).

    FALSIFIERS, as pre-registered: (i) move the hook inside the class -> red;
    (ii) append a new module-level helper after it -> GREEN (it was red);
    (iii) delete the hook -> red here and on its registry row."""
    t = tree()
    at_module = [n for n in t.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == "_gate_step"]
    assert at_module, (
        "_gate_step is not a MODULE-LEVEL def in cognitive_loop.py -- either "
        "it is gone, or it was nested inside a function or class, which puts "
        "the shadow gate's hook inside the loop's own body")

    hook = at_module[0]
    cls = scope(t, "CognitiveLoop")
    in_class = refs(cls, "_gate_step")
    assert not in_class, (
        "CognitiveLoop's class body references _gate_step at %s -- the hook is "
        "reached from the module-level narration helper, and only from there; "
        "a reference inside the class puts the shadow gate on the loop's own "
        "surface" % _where(in_class))

    everywhere = [n for n in refs(t, "_gate_step") if not inside(hook, n)]
    assert len(everywhere) == 1, (
        "_gate_step is referenced from %d places (%s) -- the receipt names ONE "
        "call site; a second one is a second hook"
        % (len(everywhere), _where(everywhere)))

    for n in ast.walk(hook):
        if isinstance(n, ast.Return):
            assert n.value is None, (
                "_gate_step returns a value at line %d -- the shadow gate must "
                "hand no verdict back to the loop" % n.lineno)


ALL_LAWS = (l1_credit_inside_record_result,
            l2_route_inside_record_result,
            l3_settle_before_bank,
            l4_plan_gate_on_the_cycle_path,
            l5_abduced_plan_becomes_the_action,
            l6_lp_steer_is_the_one_consumption_site,
            l7_gate_hook_is_module_level)
