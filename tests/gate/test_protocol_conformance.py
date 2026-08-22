"""PROTOCOL CONFORMANCE -- a declared method is not an optional capability.

THE DEFECT THIS CLOSES (EXAM_02 DEFECT A, measured 2026-08-22).
``engines/interfaces.py`` declared 25 Protocols. Eleven of them declared
fourteen methods that NO implementation in the tree defined. Structural
subtyping has no declaration site, so nothing bound a Protocol to the class the
registry actually constructs; ``engines/registry.py`` had its TYPE_CHECKING
imports commented out, so no checker looked either. Each missing name was
exactly the string a live rung ``hasattr``-guarded -- twenty-one call sites --
so every one of those guards took the False branch on every decision of every
episode. No error, no log line, no test. THREE priority-ordered rungs
(``NearMissAnalyzerRung`` 48, ``ImaginationBudgetRung`` 4,
``NetworkExplorationStatsRung`` 9) had no reachable body at all, and
``ScientificMethodRung`` fell back to the literal ``'exploring'`` on every call
so its contradiction branch could never be taken.

FIGURE 10 -- INSTALL WHAT CAN BE VIOLATED (ASSERTED, six ways). A guard that
cannot fail is not a check. F1 and F2 are the checks that CAN fail, and F2
proves it is not vacuous by constructing a violation and requiring the same
function body to red on it. The allowlist is the convention that can be
violated: an entry with an empty reason reds, and a stale entry -- one naming a
method that is no longer declared, or one that IS now implemented -- reds too.

FIGURE 3 -- A LINK WITH NO INSTRUMENT IS A LINK NOBODY HAS LOOKED AT
(ASSERTED). F3 is that instrument for the three rungs, and it asserts by CALLING
them with a constructed collaborator and observing the true branch taken -- not
by reading their source. F4 is the same instrument for the theory stage.

FIGURE 1 -- RESTORING A RUNG IS NOT PROGRESS, IT IS THE REMOVAL OF A DEFECT
(ASSUMED, not asserted; it is a rule about how the work is reported, and a test
cannot assert a report). Nothing here claims new capability. Every assertion
below is of the form "this branch is reachable", never "this branch is good".

WHAT THIS FILE ASSUMES AND DOES NOT CHECK:
  * that a method defined on the bound class is CORRECT -- only that the name
    exists and the call site speaks its shape. Shape is checked only where F3/F4
    exercise it.
  * that a name injected at runtime (``setattr``, ``__getattr__``, a dynamic
    mixin) does not exist. The AST cannot see one. None was found in these
    classes; absence of a hit is not proof (EXAM_02 LIMITS item 2).
"""
from __future__ import annotations

import ast
import glob
import os
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INTERFACES = "engines/interfaces.py"

# The same production scope tests/gate/_ast_laws.py uses: the live path. Tests
# and tools are instruments, never the live path.
PROD_GLOBS = ("*.py", "engines/**/*.py", "rungs/**/*.py", "src/**/*.py")
PROD_EXCLUDE_NAMES = ("_temp_check.py", "vulture_whitelist.py")


# =============================================================================
# F1 -- every declared method has an implementation, or a REASONED allowlist row
# =============================================================================

def test_f1_every_declared_method_is_implemented_or_reasoned() -> None:
    """Every method declared by every Protocol in engines/interfaces.py either
    exists on the implementation, or is on the allowlist WITH A REASON.

    Bound Protocols (``PROTOCOL_BINDINGS``) are checked against the one class
    the registry constructs -- not tree-wide. That distinction is the finding:
    ``get_current_prediction`` IS defined by two classes in the tree and is NOT
    defined by ``ReplayLearningEngine``, which is the class the guard runs
    against, so a tree-wide check passes and is wrong.
    """
    _assert_declarations_conform(
        _protocol_methods(), _bindings(), _allowlist(), _impl_names())


def test_f1_the_allowlist_is_the_convention_that_can_be_violated() -> None:
    """An allowlist row with an empty reason reds. A row naming something that
    is not declared, or that IS implemented, reds. Figure 10: the convention
    has to be violable or it is decoration."""
    declared = _protocol_methods()
    bindings = _bindings()
    allow = _allowlist()
    impl = _impl_names()

    for (proto, method), reason in sorted(allow.items()):
        assert isinstance(reason, str) and reason.strip(), (
            "UNIMPLEMENTED_DECLARATIONS[%r] has an empty reason -- an "
            "allowlist entry with no argument is a silence with extra steps"
            % ((proto, method),))
        assert proto in declared, (
            "UNIMPLEMENTED_DECLARATIONS names Protocol %r, which no longer "
            "exists in %s -- a stale exemption outlives the thing it excused"
            % (proto, INTERFACES))
        assert method in declared[proto], (
            "UNIMPLEMENTED_DECLARATIONS names %s.%s, which %s no longer "
            "declares -- delete the row with the declaration"
            % (proto, method, INTERFACES))
        if proto in bindings:
            members = _class_members(*bindings[proto])
            assert method not in members, (
                "%s.%s IS now defined by %s -- the allowlist row is stale and "
                "is hiding a capability that arrived"
                % (proto, method, bindings[proto][1]))
        else:
            assert method not in impl, (
                "%s.%s IS now defined somewhere in the tree -- the allowlist "
                "row is stale" % (proto, method))


# The violation F1's own body must red on, kept beside the law it falsifies.
def test_f1_is_not_vacuous() -> None:
    """Constructed violation: declare a method nothing implements and leave it
    off the allowlist. The SAME function body that passes above must raise."""
    with pytest.raises(AssertionError, match="declared by"):
        _assert_declarations_conform(
            declared={"FakeInterface": {"a_method_nothing_defines": "method"}},
            bindings={},
            allow={},
            impl_names={"some_other_name"})

    with pytest.raises(AssertionError, match="declared by"):
        # Bound to a real class that does not define it: tree-wide presence
        # must NOT rescue it. This is the get_current_prediction shape.
        _assert_declarations_conform(
            declared={"FakeInterface": {"get_diff": "method"}},
            bindings={"FakeInterface": ("engines/regulation/imagination_budget.py",
                                        "ImaginationBudgetManager")},
            allow={},
            impl_names={"get_diff"})


# =============================================================================
# F2 -- a hasattr guard on a DECLARED name must not be able to fail silently
# =============================================================================

def test_f2_hasattr_on_a_declared_name_is_never_silently_false() -> None:
    """THE REVIEWER'S RULE. ``hasattr`` exists for OPTIONAL capability. A method
    a Protocol DECLARES is not optional, so a ``hasattr`` guard on a declared
    name must name something an implementation defines -- or be on the reasoned
    allowlist, where the absence is stated instead of silent.

    This is the rule whose violation was invisible 21 times.
    """
    _assert_guards_conform(
        _guarded_names(), _protocol_methods(), _allowlist(), _impl_names())


def test_f2_is_not_vacuous() -> None:
    """Constructed violation: a guard on a declared, unimplemented, unlisted
    name. The same body must red -- and must name the file and line, because a
    rule that cannot say WHERE is not usable."""
    with pytest.raises(AssertionError, match=r"rungs/constructed\.py:99"):
        _assert_guards_conform(
            guards=[("a_declared_name", "rungs/constructed.py", 99)],
            declared={"FakeInterface": {"a_declared_name": "method"}},
            allow={},
            impl_names={"something_else"})


# =============================================================================
# F5 -- the known-negative: genuinely optional capability still guards silently
# =============================================================================

def test_f5_undeclared_capability_still_guards_silently() -> None:
    """KNOWN-NEGATIVE. ``hasattr`` is the RIGHT tool when no Protocol declares
    the name -- the capability really is optional, the False branch really is a
    degradation, and it must stay quiet. F2 must not touch those guards.

    Checked two ways: the rule ignores a constructed undeclared guard even when
    nothing implements it, and the tree's own undeclared guards are numerous
    and untouched (if that count ever went to zero this test would be asserting
    nothing).
    """
    # 1 -- constructed: undeclared name, no implementation, no allowlist row.
    #      Silence is correct here, so the rule must pass.
    _assert_guards_conform(
        guards=[("a_name_no_protocol_declares", "rungs/constructed.py", 1)],
        declared={"FakeInterface": {"a_different_name": "method"}},
        allow={},
        impl_names=set())

    # 2 -- the tree: undeclared guards exist in quantity and are not swept in.
    declared_names = {m for ms in _protocol_methods().values() for m in ms}
    undeclared = [g for g in _guarded_names() if g[0] not in declared_names]
    assert len(undeclared) > 50, (
        "only %d hasattr guards in the tree are on undeclared names -- F5 is "
        "asserting nothing if there is no optional capability left to protect"
        % len(undeclared))
    # And one named exemplar, so the negative is a fact and not a headcount:
    # SymbolicTrackerRung guards `identify_symbolic_objects`, which no Protocol
    # declares. That guard is correct and this file leaves it alone.
    assert any(n == "identify_symbolic_objects" for n, _f, _l in undeclared), (
        "the named known-negative exemplar (identify_symbolic_objects, guarded "
        "at rungs/hypothesis.py) is gone -- pick another and name it here")


# =============================================================================
# F3 -- the three rungs have reachable bodies, asserted BY CALLING THEM
# =============================================================================

def test_f3_near_miss_analyzer_rung_reaches_its_true_branch() -> None:
    """``NearMissAnalyzerRung`` (priority 48) had no reachable body: it guarded
    ``get_insights``, which ``NearMissAnalyzer`` does not define. It now reads
    ``get_near_miss_report``. Asserted by CALLING the rung with a constructed
    collaborator and observing the branch taken -- not by reading the source."""
    from rungs.exploitation import NearMissAnalyzerRung

    calls: List[Tuple[Any, ...]] = []

    class _Analyzer:
        def get_near_miss_report(self, agent_id=None, generation=None):
            calls.append((agent_id, generation))
            return {'top_insights': [
                {'insight_type': 'wasted', 'effectiveness_score': 0.5,
                 'insight_description': 'repeat ACTION3 at the gap instead'},
            ]}

    rung = NearMissAnalyzerRung(engine_registry=_Registry(near_miss_analyzer=_Analyzer()))
    result = rung.evaluate({}, {'agent_id': 'a1', 'generation': 3,
                                'available_actions': [1, 2, 3, 4]})

    assert calls, "the true branch was not taken -- the engine was never asked"
    assert result.action == 'ACTION3', (
        "the rung reached the engine but produced no action (%r / %r)"
        % (result.action, result.reason))
    assert 'Near-miss insight' in result.reason


def test_f3_imagination_budget_rung_reaches_its_true_branch() -> None:
    """``ImaginationBudgetRung`` (priority 4) had no reachable body: it guarded
    ``calculate_budget``, which ``ImaginationBudgetManager`` does not define. It
    now reads ``get_stats``, and it publishes into CONTEXT -- so the observation
    is the context mutation, which is the whole point of a context modifier."""
    from rungs.orientation import ImaginationBudgetRung

    calls: List[int] = []

    class _Budget:
        def get_stats(self):
            calls.append(1)
            return {'current_budget': 0.75, 'synthesis_depth': 3}

    context: Dict[str, Any] = {}
    rung = ImaginationBudgetRung(engine_registry=_Registry(imagination_budget=_Budget()))
    result = rung.evaluate({}, context)

    assert calls, "the true branch was not taken -- the engine was never asked"
    assert context.get('imagination_budget_remaining') == 0.75, (
        "the budget never reached context: %r" % (context,))
    assert context.get('question_tier') == 'Q3'
    assert result.confidence == pytest.approx(0.1)


def test_f3_network_exploration_stats_rung_reaches_its_true_branch() -> None:
    """``NetworkExplorationStatsRung`` (priority 9) had no reachable body: it
    guarded ``get_exploration_stats``, which ``NetworkExplorationTracker`` does
    not define. It now reads ``get_exploration_context_for_reasoning`` -- whose
    direction vocabulary is up/down/left/right, NOT the north/south/west/east
    the dead branch was written against, which is why a rename alone would have
    left it dead in a second way."""
    from rungs.orientation import NetworkExplorationStatsRung

    calls: List[Tuple[Any, ...]] = []

    class _Tracker:
        def get_exploration_context_for_reasoning(self, game_type, level,
                                                  current_position=None,
                                                  frame_width=64, frame_height=64):
            calls.append((game_type, level, current_position))
            return {
                'network_exploration': {'coverage_percent': 0.4},
                'exploration_recommendations': {'unexplored_regions': [{'x': 3, 'y': 1}]},
                'suggested_direction': 'left',
            }

    context: Dict[str, Any] = {'game_type': 'gt', 'level': 2, 'player_position': (1, 1)}
    rung = NetworkExplorationStatsRung(
        engine_registry=_Registry(network_exploration_tracker=_Tracker()))
    result = rung.evaluate({}, context)

    assert calls, "the true branch was not taken -- the tracker was never asked"
    assert context.get('coverage_percent') == 0.4, (
        "coverage never reached context: %r" % (context,))
    assert result.action == 'ACTION3', (
        "the coldspot direction did not become an action (%r / %r)"
        % (result.action, result.reason))


# =============================================================================
# F4 -- the theory stage can be something other than the literal 'exploring'
# =============================================================================

def test_f4_scientific_method_rung_can_leave_exploring() -> None:
    """``rungs/hypothesis.py`` read ``get_theory_stage()`` behind a guard on a
    name no class defines, so the stage was the literal ``'exploring'`` on every
    call and the 'theory contradicted -> force exploration' branch was
    unreachable. The stage is the 'stage' key of ``get_working_theory``.

    Constructed both ways: a contradicted theory must take the branch, and a
    speculating one must take the other -- one value proves the literal is gone,
    two prove the value is actually being read."""
    from rungs.hypothesis import ScientificMethodRung

    class _Engine:
        def __init__(self, stage):
            self.stage = stage
            self.asked: List[Tuple[str, int]] = []

        def get_working_theory(self, game_type, level_number):
            self.asked.append((game_type, level_number))
            return {'stage': self.stage, 'theory': None, 'confidence': 0.4}

    ctx = {'game_type': 'gt', 'level': 5, 'available_actions': [1, 2, 3, 4]}

    contradicted = _Engine('contradicted')
    r1 = ScientificMethodRung(
        engine_registry=_Registry(scientific_method_engine=contradicted)).evaluate({}, dict(ctx))
    assert contradicted.asked == [('gt', 5)], (
        "the engine was not asked for the working theory: %r" % (contradicted.asked,))
    assert r1.metadata.get('theory_stage') == 'contradicted', (
        "the stage is still the literal fallback: %r" % (r1.metadata,))
    assert r1.action in ('ACTION1', 'ACTION2', 'ACTION3', 'ACTION4'), (
        "the contradiction branch did not force exploration: %r" % (r1,))
    assert r1.confidence == pytest.approx(0.7)

    speculating = _Engine('speculating')
    r2 = ScientificMethodRung(
        engine_registry=_Registry(scientific_method_engine=speculating)).evaluate({}, dict(ctx))
    assert r2.metadata.get('theory_stage') == 'speculating'
    assert r2.action is None and r2.weights, (
        "the speculating branch should boost weights, not pick an action: %r" % (r2,))


# =============================================================================
# MODULE-BOTTOM HELPERS
# =============================================================================
# Appended below the laws, per the tree's module-bottom convention: adding one
# moves no line inside a law and rots no receipt.


def _read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _parse(rel: str) -> ast.Module:
    return ast.parse(_read(rel))


def _prod_files() -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
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


def _protocol_methods() -> Dict[str, Dict[str, str]]:
    """Protocol name -> {declared member name: 'method' | 'property'}."""
    out: Dict[str, Dict[str, str]] = {}
    for node in _parse(INTERFACES).body:
        if not isinstance(node, ast.ClassDef):
            continue
        if "Protocol" not in [ast.unparse(b) for b in node.bases]:
            continue
        members: Dict[str, str] = {}
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decs = [ast.unparse(d) for d in item.decorator_list]
                members[item.name] = "property" if "property" in decs else "method"
        out[node.name] = members
    assert out, "no Protocols found in %s -- the whole file is asserting nothing" % INTERFACES
    return out


def _module_dict(rel: str, name: str) -> Dict[Any, Any]:
    """Read a module-level dict literal by AST. No import, so no side effect --
    importing ``engines.interfaces`` runs ``engines/__init__.py``, which builds
    a database log handler."""
    for node in _parse(rel).body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    return dict(ast.literal_eval(node.value))
    raise AssertionError("%s does not define %s" % (rel, name))


def _bindings() -> Dict[str, Tuple[str, str]]:
    raw = _module_dict(INTERFACES, "PROTOCOL_BINDINGS")
    return {k: (v[0], v[1]) for k, v in raw.items()}


def _allowlist() -> Dict[Tuple[str, str], str]:
    return {tuple(k): v for k, v in _module_dict(
        INTERFACES, "UNIMPLEMENTED_DECLARATIONS").items()}


def _class_members(rel: str, cls: str) -> Set[str]:
    """Every name a class binds: methods, properties, class attributes, and
    ``self.X = ...`` instance attributes. Instance attributes count because
    ``hasattr`` cannot tell them from methods, and neither can a rung."""
    out: Set[str] = set()
    found = False
    for node in ast.walk(_parse(rel)):
        if not (isinstance(node, ast.ClassDef) and node.name == cls):
            continue
        found = True
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.add(item.name)
            elif isinstance(item, ast.Assign):
                out.update(t.id for t in item.targets if isinstance(t, ast.Name))
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                out.add(item.target.id)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for t in sub.targets:
                    if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                            and t.value.id == "self"):
                        out.add(t.attr)
    assert found, (
        "PROTOCOL_BINDINGS points at %s::%s and that class does not exist -- "
        "the binding is a claim about a class, and the class is gone" % (rel, cls))
    return out


def _impl_names() -> Set[str]:
    """Every attribute name bound by any class across the production scope,
    excluding the Protocol declarations themselves."""
    out: Set[str] = set()
    for rel in _prod_files():
        if rel == INTERFACES:
            continue
        try:
            t = _parse(rel)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(t):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.add(item.name)
                elif isinstance(item, ast.Assign):
                    out.update(x.id for x in item.targets if isinstance(x, ast.Name))
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    for x in sub.targets:
                        if (isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name)
                                and x.value.id == "self"):
                            out.add(x.attr)
    return out


def _guarded_names() -> List[Tuple[str, str, int]]:
    """(name, file, line) for every ``hasattr(obj, "NAME")`` literal in the
    production scope."""
    out: List[Tuple[str, str, int]] = []
    for rel in _prod_files():
        try:
            t = _parse(rel)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(t):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "hasattr" and len(node.args) >= 2
                    and isinstance(node.args[1], ast.Constant)
                    and isinstance(node.args[1].value, str)):
                out.append((node.args[1].value, rel, node.lineno))
    assert out, "no hasattr guards found at all -- the scope is wrong"
    return sorted(out)


def _assert_declarations_conform(
    declared: Dict[str, Dict[str, str]],
    bindings: Dict[str, Tuple[str, str]],
    allow: Dict[Tuple[str, str], str],
    impl_names: Set[str],
) -> None:
    """THE F1 BODY. Parameterised so a falsifier can drive it with constructed
    inputs -- a law with no falsifier is a law nobody has looked at."""
    holes: List[str] = []
    for proto in sorted(declared):
        members = None if proto not in bindings else _class_members(*bindings[proto])
        for method in sorted(declared[proto]):
            if (proto, method) in allow:
                continue
            if members is not None:
                if method not in members:
                    holes.append("%s.%s declared by %s, not defined by %s (%s)"
                                 % (bindings[proto][1], method, proto,
                                    bindings[proto][1], bindings[proto][0]))
            elif method not in impl_names:
                holes.append("%s declared by %s, defined by no class in the tree"
                             % (method, proto))
    assert not holes, (
        "%d Protocol declaration(s) have no implementation and no reasoned "
        "allowlist row:\n  %s\n\nEither wire the call site to the method the "
        "implementation actually defines, delete the declaration, or add a row "
        "to UNIMPLEMENTED_DECLARATIONS in %s saying WHY it stays declared."
        % (len(holes), "\n  ".join(holes), INTERFACES))


def _assert_guards_conform(
    guards: List[Tuple[str, str, int]],
    declared: Dict[str, Dict[str, str]],
    allow: Dict[Tuple[str, str], str],
    impl_names: Set[str],
) -> None:
    """THE F2 BODY. Parameterised for the same reason as F1's."""
    declared_names = {m for ms in declared.values() for m in ms}
    allowed_names = {m for _p, m in allow}
    bad: List[str] = []
    for name, rel, line in guards:
        if name not in declared_names:
            continue  # optional capability: hasattr is the right tool (F5)
        if name in allowed_names or name in impl_names:
            continue
        bad.append("%s:%d guards %r, which a Protocol DECLARES and no class "
                   "defines" % (rel, line, name))
    assert not bad, (
        "%d hasattr guard(s) on DECLARED names can only take the False "
        "branch:\n  %s\n\nA hasattr guard exists for OPTIONAL capability; a "
        "declared method is not optional."
        % (len(bad), "\n  ".join(bad)))


class _Registry:
    """A constructed collaborator standing in for ``EngineRegistry``.

    ``DecisionRung`` takes any object as ``engine_registry`` and reads engines
    off it by attribute, so the whole registry -- and the database it opens --
    stays out of these tests. Every engine not named returns None, which is the
    "engine unavailable" path the rungs already handle.
    """

    def __init__(self, **engines: Any) -> None:
        self._engines = engines

    def __getattr__(self, name: str) -> Optional[Any]:
        return self._engines.get(name)
