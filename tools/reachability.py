"""INJECTION-AWARE MODULE REACHABILITY -- the instrument the import closure was not.

    python -m tools.reachability --seeds cognitive
    python -m tools.reachability --diff
    python -m tools.reachability --why decision_rung_system --seeds cognitive
    python -m tools.reachability --seams --grep decision_system

==========================================================================
WHY THIS EXISTS
==========================================================================
On 2026-08-22 the 77-rung decision ladder was ruled dead and 13 modules were
queued for deletion. The evidence was a transitive IMPORT CLOSURE and its
load-bearing claim was TRUE: ``cognitive_loop.py`` imports neither
``decision_rung_system`` nor ``rungs``; zero references.

**The ladder is not imported by the loop. It is INJECTED into it.**

    evolution_runner.py:321        self.decision_system = DecisionRungSystem(...)
    game_player.py:71              self.decision_system = decision_system
    cognitive_game_player.py:116   decision_system=self._gp.decision_system
    cognitive_loop.py:824          self._decision_system = decision_system
    cognitive_loop.py:4338         result = self._decision_system.decide(obs, context)

Live measurement, recounted independently over 3,788 ``narration.jsonl`` and
2,336,716 records: **266,570 actions decided by a NAMED RUNG.** An import-closure
trace cannot see a constructor argument, so a machine deciding half the fleet's
actions read as unreachable. The falsifier that caught it is
``tests/gate/test_ladder_removal.py``; the gate on THIS tool is
``tests/gate/test_reachability_instrument.py``.

==========================================================================
THE DIRECTION OF ERROR -- STATED, BECAUSE SOUNDNESS IS NOT AVAILABLE
==========================================================================
Whole-program dataflow is undecidable and this tool does not pretend otherwise.
It does not claim to be sound or complete. It claims a DIRECTION:

    **THIS INSTRUMENT OVER-APPROXIMATES. It reports REACHABLE when unsure.**

The consumer is a DELETE decision. A false "dead" costs the agent's behaviour --
that is exactly what 2026-08-22 nearly bought. A false "live" costs one module
left in a tree that already carries 215. The prices are not comparable, so every
ambiguity resolves toward REACHABLE:

  * an injected value whose provider cannot be resolved falls back to DUCK
    TYPING -- every class in the tree implementing the whole member set used on
    the sink becomes a candidate (edge kind ``INJECT_WIDE``);
  * an attribute expression is resolved by ATTRIBUTE NAME ALONE, ignoring which
    object owns it, so ``self._gp.decision_system`` matches every
    ``.decision_system = ...`` in the tree;
  * a string constant equal to a module's dotted name is treated as a load;
  * conditionals and boolean defaults contribute ALL of their branches.

THE ONE PLACE IT DECLINES TO GUESS, stated here because an undeclared exception
to a declared direction is worse than no declaration: when a seam resolves to
NOTHING and its duck-typed candidate set is larger than ``WIDE_MAX_CANDIDATES``,
or when the call site's callee name is owned by more than ``MAX_CALLEE_OWNERS``
definitions, the seam emits NO EDGE and is recorded in ``Tree.unresolved``
instead (``--unresolved``). An edge to half the tree is not a conservative
answer; it is the absence of one, and writing it into the graph is how the
absence gets hidden. This is the house convention for a resolver that cannot
resolve -- ``tools/wiring_receipts.py``: ties and empties are NAMED ABSENCES and
the tool never chooses. **On this tree the fallback is not load-bearing: the
closure from the cognitive seed is IDENTICAL with and without every
``INJECT_WIDE`` edge (170 either way). The 22 modules injection adds are added
by RESOLVED edges.**

WHAT IT STILL CANNOT SEE, and these are the ways it can under-report -- the
dangerous direction, so they are named rather than buried: values assembled at
runtime (``getattr(mod, name_from_a_file)``, a class read out of a database or
a config file), objects reached only through a container built at runtime,
``exec``/``eval``, C extensions, the named absences above, and any edge that
exists only in data this tool does not read. A module reported UNREACHED is a
module NOTHING IN THE SOURCE NAMES -- it is not a module proven dead. The
empirical instruments remain the stronger evidence:
``tools/live_coverage_diff.py`` and a real fleet run.

==========================================================================
THE EDGE KINDS
==========================================================================
``IMPORT``       module-level import.
``LAZY``         import inside a function body -- the deferred/circular-break
                 idiom; a prior finding puts 27 live modules behind it.
``PKG_INIT``     importing ``a.b.c`` EXECUTES ``a/__init__.py`` and
                 ``a/b/__init__.py``. Always true at runtime.
``REEXPORT``     an edge OUT of a package ``__init__`` for names that
                 ``__init__`` never uses itself. Split out from ``IMPORT``
                 because "reached only by a re-export nobody calls" is a
                 different fact from "reached", and it is the port's cheapest
                 subtraction: stop re-exporting and the module falls out of the
                 closure without anything being deleted.
``STRING``       ``importlib.import_module`` / ``__import__`` / a string
                 constant that IS a module's dotted name (registry-by-name,
                 entry-point tables).
``INJECT``       constructor/parameter injection with the provider RESOLVED to a
                 concrete class.
``INJECT_WIDE``  the same seam with the provider UNRESOLVED -- duck-typed
                 candidates. This is the over-approximating fallback and it is
                 tagged so a reader can tell a followed wire from a guess.

==========================================================================
THE SEAM GRAMMAR (what counts as injection)
==========================================================================
A SINK is a parameter that is stored and then used:

    class B:
        def __init__(self, y=None):
            self._y = y            # <- param stored to an attribute
        def step(self):
            self._y.method()       # <- and a member used on it

or the same without the store (``def f(y): y.method()``).

A PROVIDER is any call site in the tree that binds that parameter --
``B(y=EXPR)`` by keyword or by position. EXPR is resolved to CLASS NAMES by a
bounded backward walk (constructor call, local assignment, tree-wide attribute
assignment, factory return, enclosing parameter -> that function's own call
sites), depth-capped, cycle-guarded. Each resolved class contributes an edge
from the CONSUMER module to the class's DEFINING module -- because it is the
consumer that cannot run without it.

The provider's own module is recorded as EVIDENCE, not as a reached node. The
wiring that happens to construct the object today is replaceable; the class the
consumer calls methods on is not. (Decision D2 in the build report.)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

KIND_IMPORT = "IMPORT"
KIND_LAZY = "LAZY"
KIND_PKG_INIT = "PKG_INIT"
KIND_REEXPORT = "REEXPORT"
KIND_STRING = "STRING"
KIND_INJECT = "INJECT"
KIND_INJECT_WIDE = "INJECT_WIDE"

ALL_KINDS = (KIND_IMPORT, KIND_LAZY, KIND_PKG_INIT, KIND_REEXPORT,
             KIND_STRING, KIND_INJECT, KIND_INJECT_WIDE)

# Directories that are not the program: records, figures, the graveyard, tests.
# IDENTICAL to the skip set of the instrument this one replaces
# (``scratchpad/minimal_set.py``), so the differential compares instruments and
# not scopes. (``lab/`` and ``legacy/`` hold no .py and so need no entry.)
DEFAULT_SKIP_TOP = frozenset({
    "environment_files", "record", "figures", "models", "considered_dead",
    "preserve", "tests",
})

_DOTTED = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")

# The backward value walk terminates on its VISITED SET, not on depth: every
# expression node is resolved at most once per query, so the union is complete
# over the edges this tool models and the cost is linear rather than
# exponential. The two numbers below are safety rails, not the termination
# argument -- they bound one pathological query, and when either bites the walk
# has already stopped growing the answer.
MAX_RESOLVE_DEPTH = 12
MAX_RESOLVE_NODES = 6000
FANOUT = 64

# THE TWO PLACES THIS TOOL DECLINES TO GUESS, and the reason is not timidity.
#
# A method name is not an identity. ``x.update(percept=...)`` is bound to a
# parameter named ``percept`` on SOME class; if forty classes define ``update``,
# treating every one of those call sites as a provider does not over-approximate
# the seam, it replaces it with noise -- and noise is what makes a detector fire
# on everything, which the known-negative exists to forbid. So a callee defined
# by more than MAX_CALLEE_OWNERS definitions is AMBIGUOUS and binds nothing.
#
# Likewise the duck-typed fallback: if the member set used on a sink is
# ``{name}``, half the tree implements it. An edge to half the tree is not a
# conservative answer, it is the ABSENCE of one, and recording it as an edge is
# how the absence gets hidden. Above WIDE_MAX_CANDIDATES the seam is reported by
# name in ``Tree.unresolved`` instead -- the house convention for a resolver
# that cannot resolve (tools/wiring_receipts.py: ties and empties are NAMED
# ABSENCES; the tool never chooses).
MAX_CALLEE_OWNERS = 3
WIDE_MAX_CANDIDATES = 8


# ---------------------------------------------------------------------------
# records
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str
    lineno: int
    detail: str = ""

    def __str__(self) -> str:
        return "%s --%s--> %s  [%s:%d %s]" % (
            self.src, self.kind, self.dst, self.src, self.lineno, self.detail)


@dataclass(frozen=True)
class Provider:
    """A call site that binds the seam's parameter."""
    module: str
    lineno: int
    expr: str
    classes: Tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return bool(self.classes)

    def __str__(self) -> str:
        return "%s:%d  %s -> %s" % (self.module, self.lineno, self.expr,
                                    ",".join(self.classes) or "<unresolved>")


@dataclass
class Seam:
    """One injection point: a parameter that is stored and used."""
    consumer_module: str
    consumer_class: str          # "<module>" for a plain function sink
    callee: str                  # the name a provider must call to bind param
    func: str                    # the function whose parameter it is
    param: str
    attr: str                    # the sink attribute ("" == the param itself)
    lineno: int
    members: FrozenSet[str] = frozenset()
    called: FrozenSet[str] = frozenset()
    providers: List[Provider] = field(default_factory=list)
    ambiguous: bool = False      # callee name owned by too many definitions
    absent: bool = False         # NAMED ABSENCE: nothing could be resolved

    @property
    def sink(self) -> str:
        return ("self.%s" % self.attr) if self.attr else self.param

    def evidence(self) -> str:
        hot = sorted(self.called) or sorted(self.members)
        return "%s.%s(%s=) -> %s.%s()" % (
            self.consumer_class, self.func, self.param, self.sink,
            hot[0] if hot else "?")

    def __str__(self) -> str:
        return "%s:%d  %s  members=%s  providers=[%s]" % (
            self.consumer_module, self.lineno, self.evidence(),
            ",".join(sorted(self.members)),
            " | ".join(str(p) for p in self.providers) or "none")


@dataclass
class _CallSite:
    module: str
    node: ast.Call
    func: Optional[ast.AST]      # enclosing FunctionDef, or None at module level


# ---------------------------------------------------------------------------
# the tree
# ---------------------------------------------------------------------------

class Tree:
    """Every .py file under ``root`` that is part of the program, and every
    reachability edge this instrument can see between them."""

    KINDS = ALL_KINDS

    def __init__(self, root: str, skip_top: Iterable[str] = DEFAULT_SKIP_TOP,
                 class_name_strings: bool = True) -> None:
        self.root = os.path.abspath(root)
        self.skip_top = frozenset(skip_top)
        self._class_name_strings = class_name_strings

        self.modules: Dict[str, str] = {}
        self.asts: Dict[str, ast.Module] = {}
        self.unparsed: List[str] = []
        self.edges: List[Edge] = []
        self.seams: List[Seam] = []
        self.unresolved: List[Seam] = []

        # indices
        self._classes: Dict[str, Set[str]] = defaultdict(set)      # cls -> modules
        self._class_node: Dict[Tuple[str, str], ast.ClassDef] = {}
        self._funcs: Dict[str, List[Tuple[str, ast.AST]]] = defaultdict(list)
        self._calls: Dict[str, List[_CallSite]] = defaultdict(list)
        self._attr_assign: Dict[str, List[Tuple[str, ast.AST, Optional[ast.AST]]]] = \
            defaultdict(list)
        self._name_assign: Dict[Tuple[str, int], Dict[str, List[ast.AST]]] = \
            defaultdict(lambda: defaultdict(list))
        self._strings: List[Tuple[str, int, str]] = []
        self._members_by_class: Dict[Tuple[str, str], FrozenSet[str]] = {}
        self._imports: Dict[str, List[Tuple[ast.AST, bool]]] = defaultdict(list)
        self._params_cache: Dict[int, Set[str]] = {}
        self._no_strings: FrozenSet[int] = frozenset()
        self._posargs_cache: Dict[int, List[str]] = {}

        self._collect()
        self._parse()
        self._index()
        self._import_edges()
        self._string_edges()
        self._injection_edges()

        self._adj: Dict[str, List[Edge]] = defaultdict(list)
        for e in self.edges:
            self._adj[e.src].append(e)

    # -- discovery ---------------------------------------------------------

    def _modname(self, path: str) -> str:
        rel = os.path.relpath(path, self.root).replace("\\", "/")
        if rel.endswith("/__init__.py"):
            rel = rel[:-len("/__init__.py")]
        elif rel.endswith(".py"):
            rel = rel[:-3]
        return rel.replace("/", ".")

    def _collect(self) -> None:
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".") and d not in self.skip_top]
            for fn in filenames:
                if fn.endswith(".py"):
                    p = os.path.join(dirpath, fn)
                    self.modules[self._modname(p)] = p

    def _parse(self) -> None:
        for m, p in self.modules.items():
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    self.asts[m] = ast.parse(fh.read(), filename=p)
            except SyntaxError:
                self.unparsed.append(m)

    def is_pkg_init(self, mod: str) -> bool:
        p = self.modules.get(mod, "")
        return p.replace("\\", "/").endswith("/__init__.py")

    # -- one structural walk ----------------------------------------------

    def _index(self) -> None:
        for mod, tree in self.asts.items():
            self._no_strings = _annotation_and_fstring_nodes(tree)
            self._walk(mod, tree, None, None)
        for (mod, cname), node in self._class_node.items():
            self._members_by_class[(mod, cname)] = frozenset(
                n.name for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ) | frozenset(
                t.attr for st in node.body if isinstance(st, ast.Assign)
                for t in st.targets if isinstance(t, ast.Attribute)
            ) | frozenset(
                t.id for st in node.body if isinstance(st, ast.Assign)
                for t in st.targets if isinstance(t, ast.Name)
            )

    def _walk(self, mod: str, node: ast.AST, func: Optional[ast.AST],
              cls: Optional[ast.ClassDef]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._funcs[child.name].append((mod, child))
                if cls is not None and child.name == "__init__":
                    self._funcs[cls.name].append((mod, child))
                self._walk(mod, child, child, cls)
                continue
            if isinstance(child, ast.ClassDef):
                self._classes[child.name].add(mod)
                self._class_node[(mod, child.name)] = child
                self._walk(mod, child, func, child)
                continue

            if isinstance(child, (ast.Import, ast.ImportFrom)):
                self._imports[mod].append((child, func is not None))
            elif isinstance(child, ast.Call):
                name = _callee_name(child.func)
                if name:
                    self._calls[name].append(_CallSite(mod, child, func))
            elif isinstance(child, ast.Assign):
                if any(isinstance(t, ast.Name) and t.id == "__all__"
                       for t in child.targets):
                    # ``__all__`` is a RE-EXPORT DECLARATION, not a load. Its
                    # strings name symbols this module may not even import
                    # (engines/__init__.py lists nine classes it never touches),
                    # so reading them as string-loaded modules invents edges.
                    continue
                for t in child.targets:
                    if isinstance(t, ast.Attribute):
                        self._attr_assign[t.attr].append((mod, child.value, func))
                    elif isinstance(t, ast.Name):
                        self._name_assign[(mod, id(func) if func else 0)][t.id] \
                            .append(child.value)
            elif (isinstance(child, ast.Constant) and isinstance(child.value, str)
                    and id(child) not in self._no_strings):
                v = child.value
                if 0 < len(v) <= 160:
                    self._strings.append((mod, getattr(child, "lineno", 0), v))
            self._walk(mod, child, func, cls)

    # -- import edges ------------------------------------------------------

    def _resolve_target(self, dotted: str) -> Optional[str]:
        t = dotted
        while t:
            if t in self.modules:
                return t
            t = ".".join(t.split(".")[:-1])
        return None

    def _ancestors(self, mod: str) -> List[str]:
        parts = mod.split(".")
        return [".".join(parts[:i]) for i in range(1, len(parts))
                if ".".join(parts[:i]) in self.modules]

    def _add(self, src: str, dst: Optional[str], kind: str, lineno: int,
             detail: str) -> None:
        if dst and dst != src:
            self.edges.append(Edge(src, dst, kind, lineno, detail))

    def _import_edges(self) -> None:
        for mod, tree in self.asts.items():
            unused = _unused_import_names(tree) if self.is_pkg_init(mod) else frozenset()
            for n, lazy in self._imports.get(mod, ()):
                for dotted, bound in _import_targets(n, mod):
                    tgt = self._resolve_target(dotted)
                    if tgt is None:
                        continue
                    if unused and bound and bound in unused:
                        kind = KIND_REEXPORT
                    else:
                        kind = KIND_LAZY if lazy else KIND_IMPORT
                    self._add(mod, tgt, kind, n.lineno, "import %s" % dotted)
                    for anc in self._ancestors(tgt):
                        self._add(mod, anc, KIND_PKG_INIT, n.lineno,
                                  "importing %s runs %s/__init__" % (tgt, anc))

    # -- string-loaded modules --------------------------------------------

    def _string_edges(self) -> None:
        for mod, lineno, raw in self._strings:
            for cand in _string_candidates(raw):
                if cand in self.modules:
                    self._add(mod, cand, KIND_STRING, lineno,
                              "string names module %r" % raw)
                    for anc in self._ancestors(cand):
                        self._add(mod, anc, KIND_PKG_INIT, lineno,
                                  "string load of %s runs %s/__init__" % (cand, anc))
                    break
            else:
                if not self._class_name_strings or not _looks_like_class(raw):
                    continue
                for owner in self._classes.get(raw, ()):
                    self._add(mod, owner, KIND_STRING, lineno,
                              "string names class %r" % raw)

    # -- injection ---------------------------------------------------------

    def _injection_edges(self) -> None:
        self.seams = self._find_seams()
        for seam in self.seams:
            if len(self._funcs.get(seam.callee, ())) <= MAX_CALLEE_OWNERS:
                self._bind_providers(seam)
            else:
                seam.ambiguous = True
            classes = {c for p in seam.providers for c in p.classes}
            kind = KIND_INJECT
            if not classes:
                classes = self._duck_candidates(seam)
                kind = KIND_INJECT_WIDE
                if len(classes) > WIDE_MAX_CANDIDATES:
                    seam.absent = True
                    self.unresolved.append(seam)
                    continue
            if not classes:
                self.unresolved.append(seam)
                seam.absent = True
                continue
            for cname in sorted(classes):
                for owner in sorted(self._classes.get(cname, ())):
                    self._add(seam.consumer_module, owner, kind, seam.lineno,
                              "%s <= %s" % (seam.evidence(), cname))

    def _find_seams(self) -> List[Seam]:
        out: List[Seam] = []
        for mod, tree in self.asts.items():
            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                out.extend(self._class_seams(mod, cls))
            for fn in ast.iter_child_nodes(tree):
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.extend(self._param_seams(mod, "<module>", fn, fn.name))
        return out

    def _class_seams(self, mod: str, cls: ast.ClassDef) -> List[Seam]:
        out: List[Seam] = []
        attr_use = _self_attr_members(cls)      # ONE walk of the class body
        methods = [n for n in cls.body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for fn in methods:
            params = self._params(fn)
            callee = cls.name if fn.name == "__init__" else fn.name
            stored: Dict[str, str] = {}
            for n in ast.walk(fn):
                if not isinstance(n, ast.Assign):
                    continue
                for t in n.targets:
                    if not (isinstance(t, ast.Attribute) and _is_self(t.value)):
                        continue
                    for src in _names_in(n.value):
                        if src in params:
                            stored[t.attr] = src
            for attr, param in sorted(stored.items()):
                members, called = attr_use.get(attr, (set(), set()))
                if not members:
                    continue
                out.append(Seam(mod, cls.name, callee, fn.name, param, attr,
                                fn.lineno, frozenset(members), frozenset(called)))
            # a parameter used directly, without being stored
            out.extend(s for s in self._param_seams(mod, cls.name, fn, callee)
                       if s.param not in stored.values())
        return out

    def _param_seams(self, mod: str, cname: str, fn: ast.AST,
                     callee: str) -> List[Seam]:
        params = self._params(fn)
        if not params:
            return []
        use = _name_members(fn, params)         # ONE walk of the function body
        out: List[Seam] = []
        for param in sorted(params):
            members, called = use.get(param, (set(), set()))
            if members:
                out.append(Seam(mod, cname, callee, fn.name, param, "",
                                fn.lineno, frozenset(members), frozenset(called)))
        return out

    def _params(self, fn: ast.AST) -> Set[str]:
        key = id(fn)
        if key not in self._params_cache:
            self._params_cache[key] = _param_names(fn)
        return self._params_cache[key]

    def _posargs(self, fn: ast.AST) -> List[str]:
        key = id(fn)
        if key not in self._posargs_cache:
            self._posargs_cache[key] = _positional_names(fn)
        return self._posargs_cache[key]

    def _bind_providers(self, seam: Seam) -> None:
        sig = self._signature(seam.consumer_module, seam.callee, seam.func)
        for site in self._calls.get(seam.callee, ()):
            expr = _bound_arg(site.node, seam.param, sig)
            if expr is None:
                continue
            classes = self._resolve(expr, site.module, site.func, 0, set())
            seam.providers.append(Provider(
                site.module, getattr(site.node, "lineno", 0),
                _short(expr), tuple(sorted(classes))))

    def _signature(self, mod: str, callee: str, func: str) -> List[str]:
        for owner, node in self._funcs.get(callee, ()):
            if owner == mod and getattr(node, "name", None) in (func, "__init__"):
                return self._posargs(node)
        for _owner, node in self._funcs.get(callee, ()):
            return self._posargs(node)
        return []

    def _duck_candidates(self, seam: Seam) -> Set[str]:
        """THE OVER-APPROXIMATING FALLBACK. Nothing named a provider, so every
        class implementing the whole member set used on the sink is a
        candidate. This is where the tool chooses to be wrong in the cheap
        direction."""
        want = seam.called or seam.members
        if not want:
            return set()
        out = set()
        for (_mod, cname), have in self._members_by_class.items():
            if want <= have:
                out.add(cname)
        return out

    # -- the backward value walk ------------------------------------------

    def _resolve(self, expr: ast.AST, mod: str, func: Optional[ast.AST],
                 depth: int, seen: Set[int]) -> Set[str]:
        # ``seen`` is SHARED and MUTATED down the whole walk, deliberately: the
        # answer is a union, so one visit per node suffices, and giving each
        # branch its own copy is what turns this into an exponential walk.
        if (depth > MAX_RESOLVE_DEPTH or expr is None or id(expr) in seen
                or len(seen) > MAX_RESOLVE_NODES):
            return set()
        seen.add(id(expr))
        out: Set[str] = set()

        if isinstance(expr, ast.Call):
            name = _callee_name(expr.func)
            if name and name in self._classes:
                out.add(name)
            elif name:
                for owner, node in self._funcs.get(name, ())[:FANOUT]:
                    for r in _returns(node):
                        out |= self._resolve(r, owner, node, depth + 1, seen)
            return out

        if isinstance(expr, (ast.BoolOp, ast.IfExp)):
            parts = list(getattr(expr, "values", []))
            if isinstance(expr, ast.IfExp):
                parts = [expr.body, expr.orelse]
            for p in parts:
                out |= self._resolve(p, mod, func, depth + 1, seen)
            return out

        if isinstance(expr, ast.Name):
            if func is not None and expr.id in self._params(func):
                out |= self._resolve_param(mod, func, expr.id, depth, seen)
            for key in ((mod, id(func) if func else 0), (mod, 0)):
                for v in self._name_assign.get(key, {}).get(expr.id, ())[:FANOUT]:
                    out |= self._resolve(v, mod, func, depth + 1, seen)
            if expr.id in self._classes:
                out.add(expr.id)
            return out

        if isinstance(expr, ast.Attribute):
            # ATTRIBUTE NAME ALONE -- deliberately ignores the receiver.
            for owner, val, ofn in self._attr_assign.get(expr.attr, ())[:FANOUT]:
                out |= self._resolve(val, owner, ofn, depth + 1, seen)
            if expr.attr in self._classes:
                out.add(expr.attr)
            return out

        if isinstance(expr, ast.Subscript):
            return self._resolve(expr.value, mod, func, depth + 1, seen)
        return out

    def _resolve_param(self, mod: str, func: ast.AST, param: str,
                       depth: int, seen: Set[int]) -> Set[str]:
        """The parameter is itself fed from somewhere: walk to this function's
        own call sites. This is the hop that turns player -> loop into
        runner -> player -> loop."""
        holder = getattr(func, "name", "")
        callees = {holder}
        if holder == "__init__":
            callees = {c for c, mods in self._classes.items() if mod in mods}
        out: Set[str] = set()
        sig = self._posargs(func)
        for callee in callees:
            for site in self._calls.get(callee, ())[:FANOUT]:
                arg = _bound_arg(site.node, param, sig)
                if arg is not None:
                    out |= self._resolve(arg, site.module, site.func, depth + 1, seen)
        return out

    # -- queries -----------------------------------------------------------

    def closure(self, seeds: Sequence[str],
                kinds: Optional[Sequence[str]] = None) -> Set[str]:
        allow = frozenset(kinds or ALL_KINDS)
        seen = {s for s in seeds if s in self.modules}
        q = deque(seen)
        while q:
            cur = q.popleft()
            for e in self._adj.get(cur, ()):
                if e.kind in allow and e.dst not in seen:
                    seen.add(e.dst)
                    q.append(e.dst)
        return seen

    def witness(self, seeds: Sequence[str], target: str,
                kinds: Optional[Sequence[str]] = None) -> Optional[List[Edge]]:
        """A shortest edge path from some seed to ``target``. The PATH is the
        product, not the verdict: a reachability claim nobody can read back is
        the shape of finding this project keeps re-deriving."""
        allow = frozenset(kinds or ALL_KINDS)
        starts = [s for s in seeds if s in self.modules]
        if target in starts:
            return []
        back: Dict[str, Edge] = {}
        seen = set(starts)
        q = deque(starts)
        while q:
            cur = q.popleft()
            for e in self._adj.get(cur, ()):
                if e.kind not in allow or e.dst in seen:
                    continue
                seen.add(e.dst)
                back[e.dst] = e
                if e.dst == target:
                    path = []
                    node = target
                    while node in back:
                        path.append(back[node])
                        node = back[node].src
                    return list(reversed(path))
                q.append(e.dst)
        return None

    def reexport_only(self, seeds: Sequence[str],
                      kinds: Optional[Sequence[str]] = None) -> Set[str]:
        """Modules reached ONLY through a package ``__init__`` re-export that
        the ``__init__`` itself never uses. Stopping the re-export removes them
        from the closure without deleting anything -- the cheapest subtraction
        the port has, and the one that must survive this instrument.

        ``kinds`` narrows the graph first. Passing the resolved kinds (dropping
        ``INJECT_WIDE``) answers the sharper question: what falls out of the
        closure when re-export stops, counting only edges this tool FOLLOWED
        rather than edges it GUESSED. A duck-typed guess into a module can
        otherwise mask the fact that a re-export is its only real entrance --
        ``engines.egocentric.falsified_ledger`` is exactly that case.
        """
        allow = list(kinds or ALL_KINDS)
        full = self.closure(seeds, allow)
        without = self.closure(seeds, [k for k in allow if k != KIND_REEXPORT])
        return full - without


# ---------------------------------------------------------------------------
# THE OLD INSTRUMENT, kept verbatim for the differential
# ---------------------------------------------------------------------------

def blind_closure(tree: Tree, seeds: Sequence[str],
                  with_pkg_init: bool = True) -> Set[str]:
    """THE FALSIFIED INSTRUMENT (``scratchpad/minimal_set.py``, 2026-08-22),
    reimplemented over the same parsed tree so the differential compares
    INSTRUMENTS and not parses. Pure ``ast.Import``/``ast.ImportFrom`` closure,
    truncating each dotted name to the longest known module prefix, optionally
    plus the "a package pulls its own ``__init__``" edge. It is here to be
    subtracted from, not to be used."""
    known = set(tree.modules)
    tops = {m.split(".")[0] for m in known}
    g: Dict[str, Set[str]] = defaultdict(set)
    for m, node in tree.asts.items():
        for n in ast.walk(node):
            if isinstance(n, ast.Import):
                names = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                if n.level:
                    base = ".".join(m.split(".")[:-n.level])
                    names = ["%s.%s" % (base, n.module) if n.module else base]
                else:
                    names = [n.module or ""]
            else:
                continue
            for name in names:
                if not name or name.split(".")[0] not in tops:
                    continue
                t = name
                while t and t not in known:
                    t = ".".join(t.split(".")[:-1])
                if t and t != m:
                    g[m].add(t)
                    if with_pkg_init and "." in t:
                        pkg = ".".join(t.split(".")[:-1])
                        if pkg in known:
                            g[m].add(pkg)
    seen = {s for s in seeds if s in known}
    q = deque(seen)
    while q:
        cur = q.popleft()
        for nxt in g.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return seen


# ---------------------------------------------------------------------------
# AST helpers (module bottom by house convention -- receipts anchor on symbols)
# ---------------------------------------------------------------------------

def _callee_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _is_self(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "self"


def _names_in(node: ast.AST) -> Set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _param_names(fn: ast.AST) -> Set[str]:
    a = getattr(fn, "args", None)
    if a is None:
        return set()
    out = {p.arg for p in (list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs))}
    out.discard("self")
    out.discard("cls")
    return out


def _positional_names(fn: ast.AST) -> List[str]:
    a = getattr(fn, "args", None)
    if a is None:
        return []
    names = [p.arg for p in (list(a.posonlyargs) + list(a.args))]
    return [n for n in names if n not in ("self", "cls")]


def _returns(fn: ast.AST) -> List[ast.AST]:
    return [n.value for n in ast.walk(fn)
            if isinstance(n, ast.Return) and n.value is not None]


def _bound_arg(call: ast.Call, param: str,
               sig: Sequence[str]) -> Optional[ast.AST]:
    for kw in call.keywords:
        if kw.arg == param:
            return kw.value
    if param in sig:
        i = list(sig).index(param)
        if i < len(call.args) and not isinstance(call.args[i], ast.Starred):
            return call.args[i]
    return None


def _members_of_self_attr(scope: ast.AST, attr: str) -> Tuple[Set[str], Set[str]]:
    """Members used on ``self.<attr>`` in ``scope``, and the subset CALLED."""
    members, called = _self_attr_members(scope).get(attr, (set(), set()))
    return members, called


def _self_attr_members(scope: ast.AST) -> Dict[str, Tuple[Set[str], Set[str]]]:
    """ONE walk: every ``self.<attr>.<member>`` in ``scope``, and which of those
    members are CALLED. ``hasattr``/``getattr`` probes count as members -- they
    are how this tree spells an optional dependency, and four dead rungs hid
    behind exactly that guard."""
    out: Dict[str, Tuple[Set[str], Set[str]]] = defaultdict(lambda: (set(), set()))
    for n in ast.walk(scope):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute) \
                and _is_self(n.value.value):
            out[n.value.attr][0].add(n.attr)
        elif isinstance(n, ast.Call):
            if (_callee_name(n.func) in ("hasattr", "getattr") and len(n.args) >= 2
                    and isinstance(n.args[0], ast.Attribute)
                    and _is_self(n.args[0].value)
                    and isinstance(n.args[1], ast.Constant)
                    and isinstance(n.args[1].value, str)):
                out[n.args[0].attr][0].add(n.args[1].value)
            if isinstance(n.func, ast.Attribute) \
                    and isinstance(n.func.value, ast.Attribute) \
                    and _is_self(n.func.value.value):
                out[n.func.value.attr][1].add(n.func.attr)
    return out


def _name_members(scope: ast.AST,
                  names: Set[str]) -> Dict[str, Tuple[Set[str], Set[str]]]:
    """The same, for bare parameters used directly (``def f(y): y.step()``)."""
    out: Dict[str, Tuple[Set[str], Set[str]]] = defaultdict(lambda: (set(), set()))
    for n in ast.walk(scope):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and n.value.id in names:
            out[n.value.id][0].add(n.attr)
        elif isinstance(n, ast.Call):
            if (_callee_name(n.func) in ("hasattr", "getattr") and len(n.args) >= 2
                    and isinstance(n.args[0], ast.Name) and n.args[0].id in names
                    and isinstance(n.args[1], ast.Constant)
                    and isinstance(n.args[1].value, str)):
                out[n.args[0].id][0].add(n.args[1].value)
            if isinstance(n.func, ast.Attribute) \
                    and isinstance(n.func.value, ast.Name) \
                    and n.func.value.id in names:
                out[n.func.value.id][1].add(n.func.attr)
    return out


def _is_self_attr(node: ast.AST, attr: str) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == attr
            and _is_self(node.value))


def _import_targets(node: ast.AST, mod: str) -> List[Tuple[str, str]]:
    """(dotted target, locally bound name) for one import statement.

    ``from pkg import sub`` yields BOTH ``pkg`` and ``pkg.sub``: the second is
    the edge the old closure could not express, because it truncated every
    dotted name to its longest known module prefix.
    """
    out: List[Tuple[str, str]] = []
    if isinstance(node, ast.Import):
        for a in node.names:
            out.append((a.name, (a.asname or a.name.split(".")[0])))
    elif isinstance(node, ast.ImportFrom):
        if node.level:
            base = ".".join(mod.split(".")[:-node.level])
            head = "%s.%s" % (base, node.module) if node.module else base
        else:
            head = node.module or ""
        if head:
            for a in node.names:
                out.append((head, (a.asname or a.name)))
                if a.name != "*":
                    out.append(("%s.%s" % (head, a.name), (a.asname or a.name)))
    return out


def _unused_import_names(tree: ast.Module) -> FrozenSet[str]:
    """Names a package ``__init__`` imports and never uses in its own body.
    ``__all__`` membership is a re-export DECLARATION, not a use -- counting it
    as one would erase the distinction this function exists to draw."""
    bound: Set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                bound.add(a.asname or a.name.split(".")[0])
    used: Set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            used.add(n.id)
        elif isinstance(n, ast.Attribute):
            root = n
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                used.add(root.id)
    dunder: Set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets):
            dunder |= {c.value for c in ast.walk(n)
                       if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    return frozenset(bound - (used - dunder))


def _string_candidates(raw: str) -> List[str]:
    """A string that could name a module: the whole thing, the part before a
    ``:`` (entry-point form) and the part before the last dot (``mod.Class``).

    NOT stripped. ``" rungs"`` is an f-string fragment, not a module load, and
    stripping it into ``rungs`` invented a path from the cognitive seed to the
    whole rung package that had nothing to do with the ladder."""
    s = raw
    out = []
    for cand in (s, s.split(":")[0], s.rsplit(".", 1)[0]):
        if cand and _DOTTED.match(cand) and cand not in out:
            out.append(cand)
    return out


def _annotation_and_fstring_nodes(tree: ast.Module) -> FrozenSet[int]:
    """Every node inside a type annotation or an f-string.

    A forward reference (``-> "CrystallizedPath"``) is a TYPE, not a load, and
    an f-string fragment (``f"{n} rungs"``) is prose. Both were read as
    registry-by-name edges before this existed, and both invented a path.
    """
    out: Set[int] = set()

    def mark(node):
        if node is None:
            return
        for n in ast.walk(node):
            out.add(id(n))

    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mark(n.returns)
        elif isinstance(n, (ast.arg, ast.AnnAssign)):
            mark(n.annotation)
        elif isinstance(n, ast.JoinedStr):
            mark(n)
    return frozenset(out)


def _looks_like_class(raw: str) -> bool:
    return (len(raw) >= 6 and raw[0].isupper() and raw.isidentifier()
            and any(c.islower() for c in raw))


def _short(node: ast.AST, n: int = 60) -> str:
    try:
        s = ast.unparse(node)
    except Exception:
        s = "<expr>"
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 3] + "..."


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

COGNITIVE_SEED = ["cognitive_loop", "engines.egocentric.gate",
                  "engines.egocentric.composer", "engines.egocentric.narration",
                  "engines.egocentric.mint", "engines.egocentric.effects",
                  "engines.egocentric.fabric", "engines.egocentric.planner",
                  "engines.egocentric.perception"]
ENTRY_SEED = ["evolution_runner", "cognitive_game_player", "game_player",
              "arc_api_adapter", "tools.swarm_supervisor", "decision_rung_system"]
SEED_SETS = {"cognitive": COGNITIVE_SEED, "entry": ENTRY_SEED}


def _seeds(arg: str) -> List[str]:
    if arg in SEED_SETS:
        return SEED_SETS[arg]
    return [s.strip() for s in arg.split(",") if s.strip()]


def _report(tree: Tree, seeds: List[str], label: str) -> None:
    reached = tree.closure(seeds)
    only_re = tree.reexport_only(seeds)
    resolved = [k for k in ALL_KINDS if k != KIND_INJECT_WIDE]
    only_re_strict = tree.reexport_only(seeds, resolved)
    kinds = defaultdict(int)
    for e in tree.edges:
        kinds[e.kind] += 1
    print("=== %s SEED (%d) ===" % (label.upper(), len(seeds)))
    print("modules in scope        : %d  (unparsed: %d)"
          % (len(tree.modules), len(tree.unparsed)))
    print("REACHED                 : %d" % len(reached))
    print("  of which reached ONLY by an unused package re-export: %d" % len(only_re))
    print("UNREACHED               : %d" % (len(tree.modules) - len(reached)))
    print("edges by kind           : "
          + "  ".join("%s=%d" % (k, kinds[k]) for k in ALL_KINDS))
    print("injection seams         : %d over %d consumer modules"
          % (len(tree.seams), len({s.consumer_module for s in tree.seams})))
    print("  of which NAMED ABSENCES (nothing resolvable): %d over %d modules"
          % (len(tree.unresolved),
             len({s.consumer_module for s in tree.unresolved})))
    print("\n--- UNREACHED, in full (NOT a proof of death: see the docstring) ---")
    for m in sorted(set(tree.modules) - reached):
        print("   " + m)
    print("\n--- REACHED ONLY BY AN UNUSED RE-EXPORT (the cheapest subtraction) ---")
    for m in sorted(only_re):
        print("   " + m)
    print("--- the same over RESOLVED edges only (guesses dropped): %d ---"
          % len(only_re_strict))
    for m in sorted(only_re_strict - only_re):
        print("   %s   [masked by an INJECT_WIDE guess in the full graph]" % m)


def _diff(tree: Tree) -> None:
    for label, seed in (("cognitive", COGNITIVE_SEED), ("entry", ENTRY_SEED)):
        old = blind_closure(tree, seed, with_pkg_init=True)
        old_noinit = blind_closure(tree, seed, with_pkg_init=False)
        new = tree.closure(seed)
        gained = sorted(new - old)
        lost = sorted(old - new)
        print("=== DIFFERENTIAL, %s SEED ===" % label.upper())
        print("OLD blind closure (with pkg __init__ edge) : %d" % len(old))
        print("OLD blind closure (no pkg __init__ edge)   : %d" % len(old_noinit))
        print("NEW injection-aware closure                : %d" % len(new))
        print("LOST (must be zero -- the error direction) : %d %s"
              % (len(lost), lost or ""))
        print("GAINED -- CALLED DEAD BY THE OLD, LIVE BY THE NEW: %d" % len(gained))
        for m in gained:
            w = tree.witness(seed, m) or []
            print("   %-46s %s" % (m, "->".join(e.kind for e in w) or "?"))
        print()


def main(argv: Optional[Sequence[str]] = None) -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=here)
    ap.add_argument("--seeds", default="cognitive")
    ap.add_argument("--diff", action="store_true")
    ap.add_argument("--why", default="")
    ap.add_argument("--seams", action="store_true")
    ap.add_argument("--unresolved", action="store_true",
                    help="the NAMED ABSENCES: seams this tool could not type")
    ap.add_argument("--grep", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-class-strings", action="store_true")
    a = ap.parse_args(argv)

    tree = Tree(a.root, class_name_strings=not a.no_class_strings)
    seeds = _seeds(a.seeds)

    if a.diff:
        _diff(tree)
        return 0
    if a.why:
        path = tree.witness(seeds, a.why)
        if path is None:
            print("%s is NOT REACHED from %s" % (a.why, a.seeds))
            return 1
        print("WITNESS  %s -> %s" % (a.seeds, a.why))
        for e in path:
            print("   " + str(e))
        return 0
    if a.unresolved:
        print("NAMED ABSENCES -- %d seam(s) this tool could not type. The "
              "modules behind them are NOT measured, so they are NOT dead."
              % len(tree.unresolved))
        for s in tree.unresolved:
            if not a.grep or a.grep in str(s):
                print("  %s%s  %s" % ("AMBIGUOUS-CALLEE " if s.ambiguous else "",
                                      s.consumer_module, s.evidence()))
        return 0
    if a.seams:
        for s in tree.seams:
            if not a.grep or a.grep in str(s):
                print(s)
        return 0
    if a.json:
        print(json.dumps({
            "modules": sorted(tree.modules),
            "reached": sorted(tree.closure(seeds)),
            "reexport_only": sorted(tree.reexport_only(seeds)),
            "edges": [[e.src, e.kind, e.dst, e.lineno, e.detail] for e in tree.edges],
        }, indent=1))
        return 0
    _report(tree, seeds, a.seeds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
