"""GATE: THE INJECTION-AWARE REACHABILITY INSTRUMENT (tools/reachability.py).

PRE-REGISTERED 2026-08-22, BEFORE THE INSTRUMENT EXISTED. This file was written
first and its claims were fixed before a line of the tool was typed; only the
mechanics of calling the API were adjusted afterwards. Every assertion below can
come back red, and two of them are DESIGNED to be the thing that reds.

--------------------------------------------------------------------------
WHY THIS GATE EXISTS -- THE FAILURE IT IS THE INSTRUMENT FOR
--------------------------------------------------------------------------
On 2026-08-22 the 77-rung decision ladder was ruled dead and 13 modules were
queued for deletion. The evidence was a transitive IMPORT CLOSURE, and its
load-bearing claim was TRUE:

    ``cognitive_loop.py`` imports neither ``decision_rung_system`` nor
    ``rungs``. Zero references.

**The ladder is not imported by the loop. It is INJECTED into it.**

    evolution_runner.py:321        self.decision_system = DecisionRungSystem(...)
    game_player.py:71              self.decision_system = decision_system
    cognitive_game_player.py:116   decision_system=self._gp.decision_system
    cognitive_loop.py:824          self._decision_system = decision_system
    cognitive_loop.py:4338         result = self._decision_system.decide(obs, context)

Fleet-wide, independently recounted by the proctor over 3,788 ``narration.jsonl``
and 2,336,716 records: **266,570 actions decided by a NAMED RUNG.** The blind
closure called every one of those modules unreachable from the cognitive path.
Deleting them removes the agent's action variety -- measured, in
``tests/gate/test_ladder_removal.py``, which is this gate's regression neighbour
and which must stay green.

--------------------------------------------------------------------------
WHAT IS ASSERTED
--------------------------------------------------------------------------
KP · KNOWN-POSITIVE, and it is the exact case that broke us. The instrument must
     report ``decision_rung_system`` and every ``rungs/*`` module REACHED from
     the cognitive seed and from the production entry points -- and **the PATH
     is asserted, not the verdict**: the witness must contain an ``INJECT`` edge
     out of ``cognitive_loop`` naming the sink attribute and the called method,
     and the seam must name the provider that constructs the class.

KN · KNOWN-NEGATIVE, non-negotiable. A known-positive proves SENSITIVITY and
     says NOTHING about SPECIFICITY (THE_LADDER.md, 2026-08-18). So the
     instrument must come back EMPTY on trees built FROM REAL TREE CODE with
     the seam removed by AST -- never from a toy, because a toy cannot drift
     with the thing it is a counterfactual of:
       KN1/KN2  one seam stripped  -> that seam gone, that module unreached.
       KN3      the same copy UNSTRIPPED still reaches it (the fixture control:
                without this, KN2 could be passing because the copy is broken).
       KN4      EVERY seam stripped -> the INJECT edge set is EXACTLY EMPTY.

DF · THE DIFFERENTIAL. The OLD blind closure and the NEW instrument, over the
     SAME seeds. The new set must be a strict SUPERSET of the old -- that is the
     over-approximation direction asserted as a law, not stated as an intention
     -- and the difference must name the ladder.

RX · THE RE-EXPORT DISTINCTION, which is the port's cheapest subtraction and
     must survive this instrument. Modules reached ONLY through a package
     ``__init__`` re-export that nothing calls are reported as such, and the
     claim is checked by re-running the closure with those edges removed.

--------------------------------------------------------------------------
FIGURES
--------------------------------------------------------------------------
ASSERTED. FIGURE 3 -- a link with no instrument is a link nobody looked at: the
injected edge had no instrument, which is why 266,570 decisions read as
unreachable; KP installs one. FIGURE 10 -- install what can be violated: KN is
the violation check ON THE CHECKER, and DF's superset law is a violable statement
of the error direction.
ASSUMED, not asserted. FIGURE 1 -- an instrument is not capability gained.
Nothing here is progress: no level moved, no defect removed. This gate makes a
blind spot measurable and that is all it does.
"""
from __future__ import annotations

import ast
import os
import shutil
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.reachability import (  # noqa: E402
    KIND_INJECT,
    KIND_INJECT_WIDE,
    KIND_REEXPORT,
    Tree,
    blind_closure,
)

LADDER = "decision_rung_system"
RUNGS = ("rungs", "rungs.base", "rungs.emergency", "rungs.exploitation",
         "rungs.exploration", "rungs.filter_rungs", "rungs.hypothesis",
         "rungs.orientation")

# The seeds are the OLD instrument's own seeds, verbatim, so the differential is
# a comparison of INSTRUMENTS and not of questions.
COGNITIVE_SEED = ["cognitive_loop", "engines.egocentric.gate",
                  "engines.egocentric.composer", "engines.egocentric.narration",
                  "engines.egocentric.mint", "engines.egocentric.effects",
                  "engines.egocentric.fabric", "engines.egocentric.planner",
                  "engines.egocentric.perception"]
ENTRY_SEED = ["evolution_runner", "cognitive_game_player", "game_player",
              "arc_api_adapter", "tools.swarm_supervisor", "decision_rung_system"]


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES -- the counterfactual trees are REAL TREE CODE, transformed by AST
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def tree():
    return Tree(REPO)


def _copy_tree(dst: str, transform=None) -> str:
    """Copy every in-scope .py file of the real repo to ``dst``.

    ``transform(relpath, source) -> source`` may rewrite any file on the way
    through. Nothing is imported and nothing is executed; the copy exists so the
    instrument can be run over a tree that differs from the real one by exactly
    one stated edit.
    """
    src_tree = Tree(REPO)
    for mod, path in src_tree.modules.items():
        rel = os.path.relpath(path, REPO)
        out = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if transform is None:
            shutil.copyfile(path, out)
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(transform(mod, src))
    # pyproject.toml marks the repo root for the tool's own scoping.
    shutil.copyfile(os.path.join(REPO, "pyproject.toml"),
                    os.path.join(dst, "pyproject.toml"))
    return dst


class _StripOneSeam(ast.NodeTransformer):
    """Remove the ladder seam from ``cognitive_loop``: the parameter, the
    assignment that makes it a sink, and every use of the sink attribute."""

    ATTR = "_decision_system"

    def visit_FunctionDef(self, node):          # noqa: N802 -- ast API
        node.args.args = [a for a in node.args.args if a.arg != "decision_system"]
        n_args = len(node.args.args) + len(node.args.posonlyargs)
        node.args.defaults = node.args.defaults[-n_args:] if n_args else []
        self.generic_visit(node)
        return node

    def visit_Assign(self, node):               # noqa: N802 -- ast API
        for t in node.targets:
            if isinstance(t, ast.Attribute) and t.attr == self.ATTR:
                return None
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node):            # noqa: N802 -- ast API
        self.generic_visit(node)
        if isinstance(node.value, ast.Attribute) and node.value.attr == self.ATTR:
            # self._decision_system.<anything>  ->  None
            return ast.copy_location(ast.Constant(value=None), node)
        if node.attr == self.ATTR:
            return ast.copy_location(ast.Constant(value=None), node)
        return node


class _StripKwarg(ast.NodeTransformer):
    """Remove ``decision_system=`` from every ``CognitiveLoop(...)`` call."""

    def visit_Call(self, node):                 # noqa: N802 -- ast API
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "CognitiveLoop":
            node.keywords = [k for k in node.keywords if k.arg != "decision_system"]
        return node


class _StripEverySink(ast.NodeTransformer):
    """Sever EVERY injection sink in a module by RENAMING ITS PARAMETERS.

    The seam grammar has two forms -- ``self._y = y`` then ``self._y.m()``, and
    the bare ``def f(y): y.m()`` -- so severing only the first leaves the second
    standing, which is what the first draft of this fixture did and why it read
    3,000 surviving edges. Renaming the SIGNATURE and leaving the body alone
    severs both at once: after this, no name used in any body is a parameter of
    its enclosing function, so nothing is stored FROM a parameter and no member
    is used ON one. The result is real tree code, still parses, and contains no
    instance of the grammar. ``self``/``cls`` are left alone -- they are not
    injectable and touching them would change what the fixture is a
    counterfactual of.
    """

    def _visit_fn(self, node):
        args = node.args
        slots = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
        if args.vararg:
            slots.append(args.vararg)
        if args.kwarg:
            slots.append(args.kwarg)
        for i, a in enumerate(slots):
            if a.arg not in ("self", "cls"):
                a.arg = "_severed_%d" % i
        self.generic_visit(node)
        return node

    visit_FunctionDef = _visit_fn                 # noqa: N815 -- ast API
    visit_AsyncFunctionDef = _visit_fn            # noqa: N815 -- ast API


def _rewrite(src: str, *transformers) -> str:
    mod = ast.parse(src)
    for t in transformers:
        mod = t.visit(mod)
    ast.fix_missing_locations(mod)
    return ast.unparse(mod)


@pytest.fixture(scope="module")
def control_tree(tmp_path_factory):
    """THE FIXTURE CONTROL: the same copy pipeline, no edit. If this does not
    behave like the real tree, KN2's emptiness is an artefact of copying."""
    d = str(tmp_path_factory.mktemp("reach_control"))
    return Tree(_copy_tree(d))


@pytest.fixture(scope="module")
def one_seam_stripped(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("reach_stripped"))

    def xform(mod, src):
        if mod == "cognitive_loop":
            return _rewrite(src, _StripOneSeam())
        if mod == "cognitive_game_player":
            return _rewrite(src, _StripKwarg())
        return src

    return Tree(_copy_tree(d, xform))


@pytest.fixture(scope="module")
def every_seam_stripped(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("reach_noseam"))

    def xform(mod, src):
        return _rewrite(src, _StripEverySink())

    return Tree(_copy_tree(d, xform))


# ═════════════════════════════════════════════════════════════════════════════
# KP -- THE KNOWN-POSITIVE. The case that broke the last ruling.
# ═════════════════════════════════════════════════════════════════════════════

class TestKnownPositive:

    def test_kp1_the_ladder_is_reached_from_the_cognitive_seed(self, tree):
        """The verdict the blind closure got wrong."""
        reached = tree.closure(COGNITIVE_SEED)
        assert LADDER in reached, (
            "the instrument still calls the ladder unreachable from the "
            "cognitive seed -- this is the 2026-08-22 failure verbatim, and "
            "266,570 live actions carried a named rung label")

    def test_kp2_the_witness_path_runs_through_the_injection_edge(self, tree):
        """ASSERT THE PATH, NOT THE VERDICT.

        Reaching the ladder by some other route would leave the injection edge
        untested and this instrument no better than the last one. The witness
        must contain an INJECT edge out of ``cognitive_loop``, and its evidence
        must name the sink attribute and the method called on it.
        """
        path = tree.witness(COGNITIVE_SEED, LADDER)
        assert path, "no witness path to the ladder at all"
        rendered = "\n  ".join(str(e) for e in path)
        inject = [e for e in path
                  if e.kind in (KIND_INJECT, KIND_INJECT_WIDE)
                  and e.src == "cognitive_loop"]
        assert inject, (
            "the ladder is reached, but NOT through an injection edge out of "
            "cognitive_loop -- the edge that broke the ruling is still "
            "untested. path:\n  %s" % rendered)
        ev = " ".join(e.detail for e in inject)
        assert "_decision_system" in ev, (
            "the injection edge does not name the sink attribute: %s" % ev)
        assert "decide" in ev, (
            "the injection edge does not name the method called on the sink "
            "-- an edge that cannot say WHAT is called is not evidence: %s" % ev)
        print("\nWITNESS  cognitive seed -> %s:\n  %s" % (LADDER, rendered))

    def test_kp3_every_rungs_module_is_reached_from_the_cognitive_seed(self, tree):
        reached = tree.closure(COGNITIVE_SEED)
        missing = [m for m in RUNGS if m not in reached]
        assert not missing, (
            "rung modules still unreachable from the cognitive seed: %r -- the "
            "seven observed live rung labels resolve into these files" % (missing,))

    def test_kp4_the_same_holds_from_the_production_entrypoints(self, tree):
        reached = tree.closure(ENTRY_SEED)
        missing = [m for m in (LADDER, *RUNGS) if m not in reached]
        assert not missing, "unreachable from production entrypoints: %r" % (missing,)

    def test_kp5_the_seam_names_its_provider_chain(self, tree):
        """The other half of the path: something must CONSTRUCT the injected
        object, or the sink is fed by nothing and the module really is dead."""
        seams = [s for s in tree.seams
                 if s.consumer_module == "cognitive_loop"
                 and s.param == "decision_system"]
        assert seams, (
            "no injection seam found for cognitive_loop(decision_system=) -- "
            "the detector does not see the seam it exists for")
        seam = seams[0]
        assert "decide" in seam.members, (
            "the seam does not record the method called on the sink: %r"
            % (sorted(seam.members),))
        provider_mods = {p.module for p in seam.providers}
        assert "cognitive_game_player" in provider_mods, (
            "the call site that passes decision_system= is not recorded: %r"
            % (sorted(provider_mods),))
        classes = {c for p in seam.providers for c in p.classes}
        assert "DecisionRungSystem" in classes, (
            "the seam resolves no provider CLASS -- the chain "
            "player -> game_player -> evolution_runner:DecisionRungSystem was "
            "not followed. resolved: %r" % (sorted(classes),))
        print("\nSEAM  %s" % seam)


# ═════════════════════════════════════════════════════════════════════════════
# KN -- THE KNOWN-NEGATIVE. A detector that cannot come back empty is not one.
# ═════════════════════════════════════════════════════════════════════════════

class TestKnownNegative:

    def test_kn3_the_fixture_control_still_reaches_the_ladder(self, control_tree):
        """THE CONTROL, AND IT COMES FIRST because it is what makes KN1/KN2
        mean anything. Same copy pipeline, no edit. If this is red, an empty
        result below is an artefact of copying, not of the strip."""
        assert LADDER in control_tree.closure(COGNITIVE_SEED), (
            "the UNEDITED copy does not reach the ladder -- the fixture is "
            "broken and every negative result in this class is worthless")

    def test_kn1_the_stripped_copy_has_no_such_seam(self, one_seam_stripped):
        seams = [s for s in one_seam_stripped.seams
                 if s.consumer_module == "cognitive_loop"
                 and s.param == "decision_system"]
        assert not seams, (
            "THE DETECTOR CANNOT COME BACK EMPTY: it reports the seam present "
            "in a copy the seam was removed from, so its positive verdict on "
            "the real tree is worth nothing. %r" % (seams,))

    def test_kn2_the_stripped_copy_does_not_reach_the_ladder(self, one_seam_stripped):
        reached = one_seam_stripped.closure(COGNITIVE_SEED)
        if LADDER in reached:
            path = one_seam_stripped.witness(COGNITIVE_SEED, LADDER)
            pytest.fail(
                "the ladder is still reached with its only seam severed -- "
                "either another edge genuinely reaches it (then NAME it here "
                "and this assertion is wrong) or the instrument fires on "
                "everything. path:\n  %s"
                % "\n  ".join(str(e) for e in (path or [])))

    def test_kn4_a_tree_with_no_sinks_yields_no_injection_edges(self, every_seam_stripped):
        """THE STRONGEST FORM OF EMPTY, from real code. Every parameter in all
        216 modules renamed in its signature and nowhere else, so no body name
        is a parameter any more and the seam grammar occurs nowhere in the
        tree. The injection edge set must then be EXACTLY empty. A tool that
        still emits edges here is emitting them from something other than the
        seam, and its positive verdicts mean nothing."""
        edges = [e for e in every_seam_stripped.edges
                 if e.kind in (KIND_INJECT, KIND_INJECT_WIDE)]
        assert not edges, (
            "%d injection edges survive on a tree with every sink severed; "
            "first five: %r" % (len(edges), edges[:5]))
        assert not every_seam_stripped.seams, (
            "%d seams survive on a tree with every sink severed"
            % len(every_seam_stripped.seams))


# ═════════════════════════════════════════════════════════════════════════════
# DF -- THE DIFFERENTIAL. What the old instrument called dead and the new one
#      calls live. This is the port's real correction.
# ═════════════════════════════════════════════════════════════════════════════

class TestTheDifferential:

    def test_df1_the_new_closure_is_a_superset_of_the_old(self, tree):
        """THE ERROR DIRECTION, ASSERTED RATHER THAN INTENDED.

        Whole-program dataflow is undecidable, so this instrument does not
        claim soundness; it claims a DIRECTION. Over-approximate: report
        reachable when unsure, because the consumer is a DELETE decision and a
        false 'dead' costs the agent's behaviour while a false 'live' costs a
        module left in the tree. If the new tool ever drops a module the blind
        closure found, that direction has been violated and the tool is unsafe
        for the consumer it was built for.
        """
        for label, seed in (("cognitive", COGNITIVE_SEED), ("entry", ENTRY_SEED)):
            old = blind_closure(tree, seed, with_pkg_init=True)
            new = tree.closure(seed)
            lost = sorted(old - new)
            assert not lost, (
                "the NEW instrument lost %d module(s) the OLD one reached from "
                "the %s seed -- the over-approximation direction is violated: "
                "%r" % (len(lost), label, lost))

    def test_df2_the_differential_names_the_ladder(self, tree):
        old = blind_closure(tree, COGNITIVE_SEED, with_pkg_init=True)
        new = tree.closure(COGNITIVE_SEED)
        gained = new - old
        assert gained, (
            "the new instrument finds NOTHING the blind closure missed -- "
            "either the tree has no injection, which the 2026-08-22 falsifier "
            "disproves, or the new edges are not being walked")
        missed_by_old = [m for m in (LADDER, *RUNGS) if m in gained]
        assert LADDER in missed_by_old, (
            "the ladder is not in the differential; the blind closure already "
            "had it, so this gate is not testing what it says it tests")
        print("\nDIFFERENTIAL (cognitive seed) -- old=%d new=%d gained=%d:\n  %s"
              % (len(old), len(new), len(gained), "\n  ".join(sorted(gained))))

    def test_df3_the_differential_is_reported_in_full(self, tree):
        """The deliverable is a NAMED SET, not a count. A differential nobody
        can read module-by-module is the same shape of finding this project
        keeps having to re-derive."""
        for label, seed in (("COGNITIVE", COGNITIVE_SEED), ("ENTRY", ENTRY_SEED)):
            old = blind_closure(tree, seed, with_pkg_init=True)
            new = tree.closure(seed)
            gained = sorted(new - old)
            print("\n=== %s SEED: old %d -> new %d, %d GAINED ==="
                  % (label, len(old), len(new), len(gained)))
            for m in gained:
                w = tree.witness(seed, m)
                kinds = "->".join(e.kind for e in w) if w else "?"
                print("  %-46s %s" % (m, kinds))
            assert len(new) >= len(old)


# ═════════════════════════════════════════════════════════════════════════════
# RX -- THE RE-EXPORT DISTINCTION. The port's cheapest subtraction; it survives.
# ═════════════════════════════════════════════════════════════════════════════

class TestTheReexportDistinction:

    def test_rx1_reexport_only_modules_are_named_and_checked(self, tree):
        """"Reached only via a re-export nobody calls" must stay separable from
        "genuinely reached", because the cheapest subtraction available to the
        port is stopping the packages from re-exporting -- not deleting."""
        full = tree.closure(ENTRY_SEED)
        without = tree.closure(ENTRY_SEED,
                               kinds=tuple(k for k in tree.KINDS if k != KIND_REEXPORT))
        only = tree.reexport_only(ENTRY_SEED)
        assert only == (full - without), (
            "reexport_only() disagrees with re-running the closure without "
            "REEXPORT edges -- the claim is not checked by its own tool")
        assert only, (
            "no module is reached only by re-export; the 55-module finding "
            "says otherwise and one of the two is wrong")
        print("\nREACHED ONLY BY RE-EXPORT (entry seed), %d:\n  %s"
              % (len(only), "\n  ".join(sorted(only))))

    def test_rx2_a_used_package_import_is_not_called_a_reexport(self, tree):
        """``rungs/__init__.py`` imports its six domain modules AND USES them at
        module level to build RUNG_REGISTRY. That is a dependency, not a
        re-export, and calling it one would make the cheapest subtraction look
        cheaper than it is."""
        kinds = {(e.dst, e.kind) for e in tree.edges if e.src == "rungs"}
        for dom in ("rungs.orientation", "rungs.hypothesis", "rungs.exploitation",
                    "rungs.filter_rungs", "rungs.emergency", "rungs.exploration"):
            assert (dom, KIND_REEXPORT) not in kinds, (
                "%s is imported by rungs/__init__ and referenced in its body "
                "(the _DOMAIN_NAMES table) -- classifying it as a pure "
                "re-export would overstate what stopping re-export buys" % dom)
