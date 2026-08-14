"""G-C GATE: goal abduction — the thin link past d->0-to-reference (PREREG_FINAL_GAPS.md).

At the moment of a level-up, the frame delta is mined for STRUCTURAL predicates that
BECAME true across the transition (mechanics, never answers): region-became-uniform,
colour-count-reached-zero, two-regions-became-equal. GoalBook banks them as GOAL
HYPOTHESES in the collective fabric stream "goal_hypotheses" (game+level scoped,
credibility = co-occurrence count across episodes, falsified when a level-up occurs
WITHOUT the predicate). The planner gains a second target mode: with no reference
snapshot, plan toward the top credible abduced goal (>= 2 co-occurrences) under the
UNCHANGED drive gates (>= 2 TRANSFERRED settlements per step atom, frontier veto).

Prereg falsifiers pinned here: co-occurrence banks + credibility rises; no level-up
evidence -> no hypotheses (never invented); falsification drops credibility; a
no-reference episode produces a [PLAN] shadow toward the abduced goal; the
.credit/.route window laws hold, measured.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import effects as E
from engines.egocentric.fabric import KnowledgeFabric


def _GA():
    try:
        from engines.egocentric.goal_abduction import (
            GoalBook,  # noqa: F401 -- the import IS the availability probe
            extract_predicates,  # noqa: F401
            satisfies,  # noqa: F401
        )
    except Exception as e:
        pytest.fail("engines.egocentric.goal_abduction missing (%s) -- G-C has not landed" % e)
    from engines.egocentric import goal_abduction as GA
    return GA


def _loop_src():
    with open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
              errors="replace") as f:
        return f.read()


# ── synthetic level-up transitions (all frames derived, no magic coordinates) ────────

def _elimination_pair():
    """pre holds colour 3; the level-up transition removes every 3-cell."""
    pre = np.zeros((8, 8), dtype=int)
    pre[2, 2] = 3
    pre[5, 6] = 3
    post = np.zeros((8, 8), dtype=int)
    post[1, 1] = 7          # the new level is not blank -- full-uniform must not fire
    return pre, post


def _persistence_pair():
    """A level-up transition where colour 3 SURVIVES -- the hypothesis's miss."""
    pre = np.zeros((8, 8), dtype=int)
    pre[2, 2] = 3
    post = np.zeros((8, 8), dtype=int)
    post[3, 3] = 3
    post[1, 1] = 7
    return pre, post


class TestTheVocabulary:

    def test_colour_elimination_is_extracted(self):
        GA = _GA()
        pre, post = _elimination_pair()
        sigs = {GA.signature(p) for p in GA.extract_predicates(pre, post)}
        assert "colour_count_zero:3" in sigs, (
            "colour 3 present pre, count zero post -- the elimination predicate must extract")

    def test_region_became_uniform_is_extracted(self):
        GA = _GA()
        pre = np.zeros((8, 8), dtype=int)
        pre[1, 1] = 4                     # q0 (top-left quadrant) is mixed pre
        post = np.zeros((8, 8), dtype=int)
        post[6, 6] = 5                    # q3 stays mixed: full-uniform must not fire
        sigs = {GA.signature(p) for p in GA.extract_predicates(pre, post)}
        assert "region_uniform:q0" in sigs
        assert "region_uniform:full" not in sigs

    def test_two_regions_became_equal_is_extracted(self):
        GA = _GA()
        pre = np.zeros((8, 8), dtype=int)
        pre[1, 1] = 4                     # q0 != q1 pre
        post = np.zeros((8, 8), dtype=int)
        post[1, 1] = 4
        post[1, 5] = 4                    # q0 == q1 post (pattern A matches B)
        sigs = {GA.signature(p) for p in GA.extract_predicates(pre, post)}
        assert "regions_equal:q0:q1" in sigs

    def test_no_delta_extracts_nothing(self):
        GA = _GA()
        pre, _ = _elimination_pair()
        assert GA.extract_predicates(pre, pre.copy()) == [], (
            "a predicate that already held is not the level-up's delta -- never invented")

    def test_satisfies_is_the_predicate_checker(self):
        GA = _GA()
        pre, post = _elimination_pair()
        pred = {"kind": "colour_count_zero", "colour": 3}
        assert GA.satisfies(pred, post) is True
        assert GA.satisfies(pred, pre) is False
        assert GA.satisfies({"kind": "nonsense"}, post) is False
        assert GA.satisfies(None, post) is False


class TestTheBook:

    def _book(self, tmp_path, name="f"):
        GA = _GA()
        return GA.GoalBook(KnowledgeFabric(str(tmp_path / name), agent_id="a",
                                           kin_key="v4"))

    def test_cooccurrence_banks_and_credibility_rises(self, tmp_path):
        """Synthetic episodes where level-up always co-occurs with a predicate ->
        the hypothesis is banked with rising credibility."""
        book = self._book(tmp_path)
        pre, post = _elimination_pair()
        banked = book.observe_levelup("g1", 1, pre, post)
        assert any(b["sig"] == "colour_count_zero:3" for b in banked)
        h1 = {h["sig"]: h for h in book.hypotheses("g1", 1)}
        assert h1["colour_count_zero:3"]["credibility"] == 1
        book.observe_levelup("g1", 1, pre, post)          # a second episode agrees
        h2 = {h["sig"]: h for h in book.hypotheses("g1", 1)}
        assert h2["colour_count_zero:3"]["co"] == 2
        assert h2["colour_count_zero:3"]["credibility"] == 2, "credibility must RISE"
        top = book.top("g1", 1)
        assert top is not None and top["sig"] == "colour_count_zero:3"

    def test_no_evidence_no_hypotheses(self, tmp_path):
        book = self._book(tmp_path)
        assert book.hypotheses("g1", 1) == []
        assert book.top("g1", 1) is None, "no level-up evidence -> no hypotheses (never invented)"

    def test_falsification_drops_credibility(self, tmp_path):
        """A level-up that occurs WITHOUT the predicate is a miss -- credibility drops."""
        book = self._book(tmp_path)
        pre, post = _elimination_pair()
        book.observe_levelup("g1", 1, pre, post)
        book.observe_levelup("g1", 1, pre, post)
        before = {h["sig"]: h for h in book.hypotheses("g1", 1)}["colour_count_zero:3"]
        pre2, post2 = _persistence_pair()                 # colour 3 survives this level-up
        book.observe_levelup("g1", 1, pre2, post2)
        after = {h["sig"]: h for h in book.hypotheses("g1", 1)}["colour_count_zero:3"]
        assert after["miss"] == 1
        assert after["credibility"] < before["credibility"], "falsification must DROP credibility"

    def test_one_credible_cooccurrence_is_below_the_bar(self, tmp_path):
        book = self._book(tmp_path)
        pre, post = _elimination_pair()
        book.observe_levelup("g1", 1, pre, post)
        assert book.top("g1", 1) is None, (
            ">= 2 co-occurrences before a hypothesis may become a target (prereg bar)")

    def test_hypotheses_are_game_and_level_scoped(self, tmp_path):
        book = self._book(tmp_path)
        pre, post = _elimination_pair()
        book.observe_levelup("g1", 1, pre, post)
        book.observe_levelup("g1", 1, pre, post)
        assert book.top("g1", 1) is not None
        assert book.top("g1", 2) is None
        assert book.top("g2", 1) is None


class TestThePlannerTargetMode:

    def _gamma_with_eliminator(self, tmp_path):
        """One EFFECT atom whose application removes the 3-cell."""
        g = E.Gamma(KnowledgeFabric(str(tmp_path / "g"), agent_id="a", kin_key="v4"))
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = 3
        a = np.zeros((5, 5), dtype=int)
        aid = g.add(E.learn_effect(b, 6, a), game="g1", level=1)
        return g, aid, b

    def test_plans_to_predicate_satisfaction_without_a_reference(self, tmp_path):
        GA = _GA()  # noqa: F841 -- vocabulary availability gates the mode
        from engines.egocentric.planner import plan_to_identity
        g, _, ws = self._gamma_with_eliminator(tmp_path)
        pred = {"kind": "colour_count_zero", "colour": 3}
        out = plan_to_identity(ws, None, g, game="g1", level=1,
                               budget=10, cost_per_action=1, goal_predicate=pred)
        assert out is not None and out["feasible"] is True
        assert len(out["steps"]) == 1, "one application reaches predicate satisfaction"

    def test_no_reference_and_no_predicate_is_none(self, tmp_path):
        from engines.egocentric.planner import plan_to_identity
        g, _, ws = self._gamma_with_eliminator(tmp_path)
        out = plan_to_identity(ws, None, g, game="g1", level=1,
                               budget=10, cost_per_action=1)
        assert out is None, "no target at all -> None (nothing invented)"

    def test_already_satisfied_plans_nothing(self, tmp_path):
        from engines.egocentric.planner import plan_to_identity
        g, _, _ = self._gamma_with_eliminator(tmp_path)
        ws = np.zeros((5, 5), dtype=int)
        pred = {"kind": "colour_count_zero", "colour": 3}
        out = plan_to_identity(ws, None, g, game="g1", level=1,
                               budget=10, cost_per_action=1, goal_predicate=pred)
        assert out is not None and out["steps"] == []

    def test_reference_mode_is_unchanged(self, tmp_path):
        from engines.egocentric.planner import plan_to_identity
        g, _, ws = self._gamma_with_eliminator(tmp_path)
        ref = np.zeros((5, 5), dtype=int)
        out = plan_to_identity(ws, ref, g, game="g1", level=1,
                               budget=10, cost_per_action=1)
        assert out is not None and len(out["steps"]) == 1, (
            "the reference target mode must keep working exactly as before")


class TestTheFallback:

    def _armed(self, tmp_path):
        GA = _GA()
        fab = KnowledgeFabric(str(tmp_path / "fb"), agent_id="a", kin_key="v4")
        g = E.Gamma(fab)
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = 3
        a = np.zeros((5, 5), dtype=int)
        aid = g.add(E.learn_effect(b, 6, a), game="g1", level=1)
        book = GA.GoalBook(fab)
        pre, post = _elimination_pair()
        book.observe_levelup("g1", 1, pre, post)
        book.observe_levelup("g1", 1, pre, post)
        return GA, g, book, aid, b

    def test_a_no_reference_episode_shadows_toward_the_abduced_goal(self, tmp_path):
        """Unverified atoms -> the record says verified=False: the loop narrates
        [PLAN] shadow toward the abduced goal, never drives (the wheel rule)."""
        GA, g, book, _aid, ws = self._armed(tmp_path)
        ap = GA.abduced_plan(g, book, ws, game="g1", level=1, budget=10,
                             verified_counts={})
        assert ap is not None and ap["sig"] == "colour_count_zero:3"
        assert ap["credibility"] >= 2
        assert len(ap["steps"]) == 1
        assert ap["verified"] is False, "no TRANSFERRED settlements -> shadow only"

    def test_drive_gates_are_unchanged(self, tmp_path):
        """verified needs >= 2 TRANSFERRED settlements per step atom; a banked
        fatal site still vetoes -- the same gates as the reference mode."""
        GA, g, book, aid, ws = self._armed(tmp_path)
        ap = GA.abduced_plan(g, book, ws, game="g1", level=1, budget=10,
                             verified_counts={aid: 2})
        assert ap is not None and ap["verified"] is True
        assert ap["site"] is not None
        assert ap["veto"] is False
        vetoed = GA.abduced_plan(g, book, ws, game="g1", level=1, budget=10,
                                 verified_counts={aid: 2},
                                 harvest={"fatal": {ap["site"]}, "dead": set()})
        assert vetoed is not None and vetoed["veto"] is True

    def test_no_credible_goal_is_none(self, tmp_path):
        GA = _GA()
        fab = KnowledgeFabric(str(tmp_path / "nb"), agent_id="a", kin_key="v4")
        g = E.Gamma(fab)
        book = GA.GoalBook(fab)
        ws = np.zeros((5, 5), dtype=int)
        assert GA.abduced_plan(g, book, ws, game="g1", level=1, budget=10,
                               verified_counts={}) is None, "abduced=[] dies"


class TestTheWiring:

    def test_the_bank_site_is_wired_in_record_result(self):
        src = _loop_src()
        tail = src[src.find("def record_result"):]
        assert "_goal_abd(" in tail, (
            "record_result never banks the level-up frame delta -- goal abduction "
            "is unwired (starvation)")
        assert "goal_abduction" in src and "GoalBook" in src

    def test_goal_narration_exists(self):
        assert "[GOAL]" in _loop_src(), (
            "a banked hypothesis and a goal-targeting plan must narrate [GOAL]")

    def test_the_fallback_lives_in_the_ego_plan_block(self):
        src = _loop_src()
        a = src.index("W4c (EGO-PLAN)")
        b = src.index("C33 STEP 1", a)
        region = src[a:b]
        assert "abduced_plan" in region, (
            "the EGO-PLAN block never tries the abduced target after reference")
        assert "[PLAN]" in region

    def test_window_laws_hold_measured(self):
        """The 8000-char .credit and 20000-char .route windows from record_result
        survive the wiring -- measured, not assumed."""
        src = _loop_src()
        body = src[src.find("def record_result"):]
        ci = body.find(".credit(")
        ri = body.find(".route(")
        assert 0 <= ci < 8000, "the .credit window law broke (offset %d)" % ci
        assert 0 <= ri < 20000, "the .route window law broke (offset %d)" % ri
        gi = body.find("_goal_abd(")
        assert gi > ri, (
            "the goal-abduction call site must sit AFTER the .route window's "
            "anchor -- inserting before it breaks the window law")
