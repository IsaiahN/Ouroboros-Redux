"""THE LADDER-REMOVAL FALSIFIER -- and the ruling it reverted.

PRE-REGISTERED PREDICTION (record/findings/THE_MINIMAL_LIVE_SET.md sections 4,
4b, 4c; the removal brief of 2026-08-22):

    with the ladder absent, the loop's action sequence on a constructed board
    is IDENTICAL, because nothing the ladder computes reaches the loop.

LOSING CONDITION, pre-registered with it: *if the sequences differ, STOP,
report the divergence, and move NOTHING -- the trace is then wrong and the
ruling reverts.*

**THE SEQUENCES DIFFER. THE PREDICTION IS FALSIFIED AND NOTHING WAS MOVED.**

--------------------------------------------------------------------------
WHY THE TRACE MISSED IT -- AND IT IS A GENUS, NOT A SLIP
--------------------------------------------------------------------------
The ruling's load-bearing observation is TRUE AS WRITTEN and does not carry
the weight put on it:

    ``cognitive_loop.py`` imports NEITHER ``decision_rung_system`` NOR
    ``rungs``. Zero references.

Correct. **The ladder is not imported by the loop. It is INJECTED INTO IT.**

    evolution_runner.py:319   self.decision_system = DecisionRungSystem(...)
    game_player.py:71         self.decision_system = decision_system
    cognitive_game_player.py:115-116
                              loop = CognitiveLoop(
                                  decision_system=self._gp.decision_system, ...)
    cognitive_loop.py:824     self._decision_system = decision_system
    cognitive_loop.py:4331    if self._decision_system is not None and strategy
                                  in ("exploit", "experiment"):
    cognitive_loop.py:4338        result = self._decision_system.decide(obs, context)

That last line is SPEED 2: REASONED, inside ``CognitiveLoop._act`` -- the
loop's own action selection. ``loop.cycle(...)`` at cognitive_game_player.py
IS the whole of action selection, exactly as the ruling says; what the ruling
missed is that ``cycle`` itself delegates to the ladder for two of its four
strategies.

**AN IMPORT-CLOSURE TRACE CANNOT SEE DEPENDENCY INJECTION.** The transitive
import closure that produced THE MINIMAL LIVE SET's 46 modules is a static
instrument, and a constructor argument is a runtime edge. The ladder was
absent from the closure for the same reason it is present in every episode:
nobody names it where the instrument was looking.

This is the tree's own THE_LADDER.md rung 0c finding one level up -- *the gate
is reference-level, not reachability-level* -- with the polarity inverted. That
finding was about a symbol that is referenced and never reached. This is a
module that is never referenced and always reached.

--------------------------------------------------------------------------
THE LIVE COUNT, which is the part that outranks any constructed board
--------------------------------------------------------------------------
Fleet-wide census of the ACT narration records under ``.runs/swarm``
(read-only), as of 2026-08-22, population = every ``narration.jsonl`` on all
25 boxes:

    ACT records total ................................ 537,424
      carrying a non-empty ``rung`` label ............ 298,601
      whose label is the loop's own action_speed ..... 32,031  ("explore")
      **whose label is a NAMED RUNG** ................ **266,570**
      carrying the D-8 ``fallback`` flag = true ......  83,914

``cf.rung_name`` is assigned at exactly one place, cognitive_loop.py:4361-4364,
inside the REASONED block, out of ``self._decision_system.last_decision_metadata``.
``cf.fallback`` is assigned at exactly one place, cognitive_loop.py:4365, out of
the same dict's ``weighted_fallback`` key, which only ``DecisionRungSystem``
writes. Every one of the seven observed labels resolves into the moving set:

    wall_aware_navigation  112,988   rungs/exploitation.py:1796
    weighted_random         76,145   decision_rung_system.py:1232
    survey                  38,767   rungs/orientation.py:41
    grid_exploration        23,610   rungs/base.py:284
    controlled_movement_planning 7,476  rungs/exploitation.py:2433
    exploration_phase        6,959   rungs/orientation.py:195
    smart_action_selection     625   rungs/exploration.py:36

**THE LADDER HAS DECIDED 266,570 LIVE ACTIONS**, not zero. Section 4c's "the
ladder has never chosen an action in the project's history" is measuring the
``evolution_runner`` exception fallback, which is genuinely never taken -- and
that fallback is not the ladder's only entrance. It is the back door. The
front door is the injected constructor argument, and it is open every cycle.

--------------------------------------------------------------------------
WHAT THIS FILE ASSERTS
--------------------------------------------------------------------------
F1 · THE TWO ARMS DIVERGE. One constructed board, one seed, driven twice:
     with a real ``DecisionRungSystem`` injected, and with ``None``. The
     action sequences differ, and the first divergence is named.
F2 · AND THE DIVERGENCE IS CAUSAL, NOT RNG DRIFT. In the WITH arm the loop
     itself labels the divergent cycles ``action_speed == "reasoned"`` and
     stamps a rung name -- the loop RETURNED the ladder's action. A sequence
     difference alone would be consistent with the ladder merely consuming
     entropy; the attribution is not.
F3 · THE INJECTION SEAM EXISTS IN SOURCE (AST): the loop calls ``.decide`` on
     ``self._decision_system`` inside ``_act``, and the player passes
     ``decision_system=`` into ``CognitiveLoop(...)``. This is the edge the
     import-closure instrument could not see, so it is asserted structurally.
R4 · KNOWN-POSITIVE AND KNOWN-NEGATIVE for F3's detector: it must fire on the
     tree as it stands, and it must NOT fire on a constructed copy with the
     seam removed. A detector that cannot come back empty is not a check.

FIGURES. ASSERTED here: FIGURE 10 (install what can be violated) -- F1/F2 are
the violation the ``hasattr`` convention could not express, and R4 is the
violation check on the checker. FIGURE 3 (a link with no instrument is a link
nobody has looked at) -- F3 installs the instrument on the injected edge that
had none, which is why 266,570 decisions were invisible to the closure.
ASSUMED, not asserted: FIGURE 1 (removing a defect is not capability gained) --
nothing here is reported as progress; this file removes nothing and adds no
capability. It records a reverted ruling.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import random
import sys
import types
from contextlib import redirect_stdout

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

N_STEPS = 14
SEED = 777
GAME_ID = "ladder_gate_g1"

LOOP_FILE = "cognitive_loop.py"
PLAYER_FILE = "cognitive_game_player.py"


# ---------------------------------------------------------------------------
# The constructed board: a static 64x64 field with one marked cell.
#
# DELIBERATELY UNSTEERED. Nothing here forces the REASONED branch: no
# _prior_knowledge_loaded, no timer urgency, no repeat-counter priming. The
# loop reaches strategy "exploit" on its own from cycle 1, which is the point
# -- the ladder is not an edge case of the live path, it is its ordinary case.
# ---------------------------------------------------------------------------

def _board() -> np.ndarray:
    b = np.zeros((64, 64), dtype=int)
    b[40, 5] = 7
    return b


def _drive(run_root: str, with_ladder: bool):
    """One arm. Returns (actions, speeds, rungs).

    Both arms: same seed, same board, same step count, fresh data root. The
    ONLY difference between them is whether a real DecisionRungSystem is
    handed to the constructor -- i.e. exactly the edge the move would cut.
    """
    cwd = os.getcwd()
    os.chdir(run_root)
    try:
        random.seed(SEED)
        from cognitive_loop import CognitiveLoop

        ds = None
        if with_ladder:
            from decision_rung_system import DecisionRungSystem
            ds = DecisionRungSystem(strategy="ladder")

        loop = CognitiveLoop(decision_system=ds, data_root=str(run_root))
        loop.start_game(GAME_ID, [1, 2, 3, 4, 5, 6], max_actions=200)

        board = _board()
        obs = types.SimpleNamespace(levels_completed=0)

        actions, speeds, rungs = [], [], []
        buf = io.StringIO()
        with redirect_stdout(buf):
            for _ in range(N_STEPS):
                a, d, cf = loop.cycle(board.copy(), obs)
                actions.append((int(a),
                                None if not d else (d.get("x"), d.get("y"))))
                speeds.append(getattr(cf, "action_speed", None))
                rungs.append(getattr(cf, "rung_name", None) or "")
                loop.record_result(post_frame=board.copy(), frame_changed=False,
                                   score_delta=0.0, level_changed=False,
                                   new_level=0)
                # THE NOTIFICATION THE PLAYER SENDS, sent the way the player
                # sends it (cognitive_game_player.py:479-501) -- behind the
                # same hasattr guard, so the WITH arm is the live shape and
                # not a reduced one.
                if ds is not None and hasattr(ds, "notify_action_complete"):
                    # contextlib.suppress, not try/except/pass: same semantics
                    # as the player's own containment, and ruff-clean.
                    with contextlib.suppress(Exception):
                        ds.notify_action_complete(
                            action="ACTION%d" % a, action_data=d or {},
                            frame_before=board.tolist(),
                            frame_after=board.tolist(),
                            context={"frame_changed": False})
        return actions, speeds, rungs
    finally:
        os.chdir(cwd)


@pytest.fixture(scope="module")
def two_arms(tmp_path_factory):
    with_root = tmp_path_factory.mktemp("ladder_with")
    without_root = tmp_path_factory.mktemp("ladder_without")
    w = _drive(str(with_root), with_ladder=True)
    n = _drive(str(without_root), with_ladder=False)
    return {"with": w, "without": n}


def _first_divergence(a, b):
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i, x, y
    if len(a) != len(b):
        return min(len(a), len(b)), None, None
    return None, None, None


# ═════════════════════════════════════════════════════════════════════════════
# F1 -- the two arms diverge
# ═════════════════════════════════════════════════════════════════════════════

class TestThePreregisteredPrediction:

    def test_f1_the_action_sequences_are_not_identical(self, two_arms):
        """THE PREREGISTERED PREDICTION, TESTED, AND IT LOST.

        The brief predicted IDENTICAL sequences on the ground that nothing the
        ladder computes reaches the loop. They are not identical, so something
        the ladder computes reaches the loop -- and this assertion is what
        reddens if anyone severs the injection seam without re-running the
        census above.
        """
        wa, _ws, _wr = two_arms["with"]
        na, _ns, _nr = two_arms["without"]
        i, x, y = _first_divergence(wa, na)
        assert i is not None, (
            "THE TWO ARMS AGREE. If this ever passes-by-agreeing, the ladder "
            "genuinely contributes nothing to the decision and the removal "
            "ruling is back on -- re-run the .runs census in this module's "
            "docstring before acting on it, because 266,570 live actions "
            "carried a named rung label when it was taken.\n"
            "  with ladder: %r\n  without    : %r" % (wa, na))
        assert wa != na
        # The divergence is named, not merely counted -- a bare "they differ"
        # is the kind of finding this project keeps having to re-derive.
        print("\nFIRST DIVERGENCE at cycle %d: with-ladder=%r  without=%r"
              % (i, x, y))

    def test_f2_the_divergent_cycles_are_attributed_to_named_rungs(self, two_arms):
        """AND THE DIVERGENCE IS CAUSAL, NOT ENTROPY DRIFT.

        A differing sequence alone is consistent with the ladder merely
        consuming RNG that the explorer would otherwise have drawn. What is
        not consistent with that: the loop labelling its own cycle
        ``action_speed == "reasoned"`` and stamping a rung name it can only
        have read out of ``last_decision_metadata``. That is the loop saying,
        in its own record, that it returned the ladder's action.
        """
        _wa, ws, wr = two_arms["with"]
        _na, ns, _nr = two_arms["without"]

        reasoned = [i for i, s in enumerate(ws) if s == "reasoned"]
        assert reasoned, (
            "no cycle in the WITH arm reached SPEED 2 (REASONED) -- the "
            "comparison is VACUOUS: the ladder was injected and never "
            "consulted, so F1's divergence would have to be explained some "
            "other way. speeds=%r" % (ws,))

        named = [(i, wr[i]) for i in reasoned if wr[i]]
        assert named, (
            "cycles %r were REASONED but carry no rung name -- the "
            "attribution half of the evidence is missing" % (reasoned,))

        assert "reasoned" not in ns, (
            "the WITHOUT arm reached REASONED with no decision system "
            "injected -- the arms are not the contrast they claim to be: "
            "speeds=%r" % (ns,))

        print("\n%d/%d cycles REASONED in the WITH arm; rung labels: %r"
              % (len(reasoned), len(ws), sorted({n for _i, n in named})))

    def test_f2b_the_rung_labels_resolve_into_the_moving_set(self, two_arms):
        """The labels are not free text: each names a class in the set the
        ruling proposed to move. This is what makes the census in the
        docstring a measurement of THE LADDER rather than of a string field."""
        _wa, ws, wr = two_arms["with"]
        labels = {wr[i] for i, s in enumerate(ws) if s == "reasoned" and wr[i]}
        assert labels, "no rung labels to resolve"

        hay = ""
        for rel in ("decision_rung_system.py", "rungs/base.py",
                    "rungs/orientation.py", "rungs/hypothesis.py",
                    "rungs/exploitation.py", "rungs/filter_rungs.py",
                    "rungs/emergency.py", "rungs/exploration.py"):
            p = os.path.join(REPO, rel)
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="ignore") as fh:
                    hay += fh.read()
        unresolved = [lab for lab in labels
                      if ('"%s"' % lab) not in hay and ("'%s'" % lab) not in hay]
        assert not unresolved, (
            "rung label(s) %r do not appear in decision_rung_system.py or the "
            "rungs package -- either the label is not the ladder's, or the "
            "moving set is wrong" % (unresolved,))


# ═════════════════════════════════════════════════════════════════════════════
# F3 -- the injection seam, asserted structurally (the edge the closure missed)
# ═════════════════════════════════════════════════════════════════════════════

def _decide_on_decision_system(src: str):
    """Every ``self._decision_system.decide(...)`` call inside
    ``CognitiveLoop._act``, as (lineno,) tuples. The detector under R4."""
    tree = ast.parse(src)
    out = []
    for cls in ast.walk(tree):
        if not (isinstance(cls, ast.ClassDef) and cls.name == "CognitiveLoop"):
            continue
        for fn in ast.walk(cls):
            if not (isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and fn.name == "_act"):
                continue
            for n in ast.walk(fn):
                if (isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "decide"
                        and isinstance(n.func.value, ast.Attribute)
                        and n.func.value.attr == "_decision_system"):
                    out.append((n.lineno,))
    return out


def _decision_system_kwarg_to_loop(src: str):
    """Every ``CognitiveLoop(..., decision_system=<something>, ...)``."""
    tree = ast.parse(src)
    out = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "CognitiveLoop"):
            for kw in n.keywords:
                if kw.arg == "decision_system":
                    out.append((n.lineno,))
    return out


def _read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


class TestTheInjectionSeamIsInSource:

    def test_f3_the_loop_calls_decide_on_its_injected_decision_system(self):
        """FIGURE 3: this edge had no instrument, which is why a 77-rung
        machine deciding half the fleet's actions read as unreachable. The
        instrument is this assertion."""
        sites = _decide_on_decision_system(_read(LOOP_FILE))
        assert sites, (
            "CognitiveLoop._act no longer calls self._decision_system.decide "
            "-- if this was deliberate, the ladder really is off the decision "
            "path and the removal ruling can be re-opened; re-run the .runs "
            "census first. If it was not deliberate, SPEED 2 (REASONED) is "
            "gone and roughly half the fleet's action selection changed "
            "silently.")

    def test_f3b_the_player_injects_the_decision_system_into_the_loop(self):
        """The other half of the edge. Without this the loop's seam is
        unreachable in production no matter what _act says."""
        sites = _decision_system_kwarg_to_loop(_read(PLAYER_FILE))
        assert sites, (
            "%s no longer passes decision_system= into CognitiveLoop(...) -- "
            "the live path's ladder injection is gone" % PLAYER_FILE)

    def test_r4_the_detector_fires_on_the_tree_and_not_on_a_stripped_copy(self):
        """R4, BOTH HALVES. A known-positive proves sensitivity and says
        nothing about specificity (THE_LADDER.md, 2026-08-18). So: the
        detector must fire on the tree as it stands, and must come back EMPTY
        on a constructed copy of the same source with the seam removed.

        The stripped copy is derived FROM THE TREE by AST rather than written
        by hand, so it cannot drift away from what it is a counterfactual of.
        """
        src = _read(LOOP_FILE)
        assert _decide_on_decision_system(src), "known-positive did not fire"

        class _Strip(ast.NodeTransformer):
            def visit_Call(self, node):    # noqa: N802 -- ast.NodeTransformer API
                self.generic_visit(node)
                if (isinstance(node.func, ast.Attribute)
                        and node.func.attr == "decide"
                        and isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "_decision_system"):
                    return ast.copy_location(ast.Constant(value=None), node)
                return node

        stripped = ast.unparse(_Strip().visit(ast.parse(src)))
        assert not _decide_on_decision_system(stripped), (
            "THE DETECTOR CANNOT COME BACK EMPTY -- it reports the seam "
            "present in a copy the seam was removed from, so its positive "
            "verdict on the real tree is worth nothing")

        player = _read(PLAYER_FILE)
        assert _decision_system_kwarg_to_loop(player), (
            "known-positive did not fire on the player")

        class _StripKw(ast.NodeTransformer):
            def visit_Call(self, node):    # noqa: N802 -- ast.NodeTransformer API
                self.generic_visit(node)
                if isinstance(node.func, ast.Name) and node.func.id == "CognitiveLoop":
                    node.keywords = [k for k in node.keywords
                                     if k.arg != "decision_system"]
                return node

        stripped_p = ast.unparse(_StripKw().visit(ast.parse(player)))
        assert not _decision_system_kwarg_to_loop(stripped_p), (
            "the player-side detector cannot come back empty")


# ═════════════════════════════════════════════════════════════════════════════
# The moving set is still here -- the move did NOT happen
# ═════════════════════════════════════════════════════════════════════════════

class TestNothingWasMoved:

    def test_the_proposed_moving_set_is_still_on_the_live_path(self):
        """The pre-registered losing condition was *move NOTHING*. This
        records that the condition was honoured, and reddens if a later hand
        performs the move without re-running F1/F2.

        It is deliberately NOT a claim that these modules are good. It is a
        claim that they are LOAD-BEARING, which is a different and weaker
        thing -- and the only thing the evidence supports.
        """
        for rel in ("decision_rung_system.py",
                    "rungs/__init__.py", "rungs/base.py",
                    "rungs/orientation.py", "rungs/hypothesis.py",
                    "rungs/exploitation.py", "rungs/filter_rungs.py",
                    "rungs/emergency.py", "rungs/exploration.py"):
            assert os.path.exists(os.path.join(REPO, rel)), (
                "%s was moved to considered_dead/ -- the ladder-removal "
                "falsifier FAILED its own prediction on 2026-08-22 (the two "
                "arms diverge; 266,570 live actions carried a named rung "
                "label). Moving it needs a NEW measurement, not the old "
                "import-closure trace." % rel)
