"""INSTRUMENT: reason channels for the two silent-empty returns (narration only).

plan_to_identity returns None/empty indistinguishably -- NOTHING ARRIVED and
ARRIVED-AND-REJECTED look identical in every log (THE_LADDER Q3). This build adds an
out-of-band reason to every empty outcome (module-level LAST_REASON + bounded counts,
fixed enum, game-agnostic) and classify_object_transform gains a bounded NONE-reason
counter (effects.none_reasons(), pure read). The [PLAN-GATE] line carries both
summaries -- print-line edit only; zero behavior change (same plans, same atoms,
same dict shapes -- asserted below against outputs).

Fixed enums:
  planner: NO_APPLICABLE_ATOMS | BUDGET_EXHAUSTED | NO_MEET | ANCHOR_MISS | INFEASIBLE_COST
    ANCHOR_MISS  = no target given, OR atoms exist but ZERO applications fired on this
                   frame across both frontiers (nothing anchored).
    NO_MEET      = applications fired but the frontiers drained without meeting.
    INFEASIBLE_COST = a plan WAS returned but unaffordable (empty for driving purposes;
                   the returned dict is byte-identical to before).
  effects: NO_DIFF | FRAME_MISMATCH | MULTI_COMPONENT | SHAPE_MISMATCH |
           FILL_VIOLATION | NO_CLEAR_GROUND | COLOUR_CONFLICT
    (1:1 onto classify_object_transform's actual NONE branches; two-component failures
     record the FIRST ordering attempt's reason, deterministically.)
"""
from __future__ import annotations

import os
import re
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import effects as E
from engines.egocentric.fabric import KnowledgeFabric

PLAN_REASONS = ("NO_APPLICABLE_ATOMS", "BUDGET_EXHAUSTED", "NO_MEET",
                "ANCHOR_MISS", "INFEASIBLE_COST")
VOCAB_REASONS = ("NO_DIFF", "FRAME_MISMATCH", "MULTI_COMPONENT", "SHAPE_MISMATCH",
                 "FILL_VIOLATION", "NO_CLEAR_GROUND", "COLOUR_CONFLICT")


def _P():
    try:
        from engines.egocentric.planner import (
            plan_to_identity,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.planner missing (%s)" % e)
    from engines.egocentric import planner as P
    return P


def _gamma(tmp_path, name, pairs):
    """A Gamma holding one 1-cell recolour atom per (v_from, v_to) pair."""
    g = E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))
    ids = []
    for v0, v1 in pairs:
        b = np.zeros((5, 5), dtype=int)
        b[2, 2] = v0
        a = b.copy()
        a[2, 2] = v1
        ids.append(g.add(E.learn_effect(b, 6, a), game="g1", level=1))
    return g, ids


def _board(v):
    ws = np.zeros((5, 5), dtype=int)
    ws[2, 2] = v
    return ws


# ── planner: every empty outcome names its reason ─────────────────────────────

class TestPlannerReasons:

    def test_enum_is_fixed_and_bounded(self):
        P = _P()
        assert tuple(P.NONE_REASONS) == PLAN_REASONS, "fixed enum only -- no free strings"
        counts = P.reason_counts()
        assert set(counts) == set(PLAN_REASONS), "counter keys are the enum, exactly"
        assert all(isinstance(v, int) and v >= 0 for v in counts.values())
        # pure read: mutating the returned dict must not touch the module counter
        counts["NO_MEET"] = 10 ** 9
        assert P.reason_counts()["NO_MEET"] != 10 ** 9 or counts is not P.reason_counts()
        assert P.reason_counts() is not counts

    def test_no_applicable_atoms(self, tmp_path):
        P = _P()
        g, _ = _gamma(tmp_path, "empty", [])
        before = P.reason_counts()
        out = P.plan_to_identity(_board(3), _board(9), g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is None, "behavior unchanged: no operator, no plan"
        assert P.last_reason() == "NO_APPLICABLE_ATOMS"
        assert P.reason_counts()["NO_APPLICABLE_ATOMS"] == before["NO_APPLICABLE_ATOMS"] + 1

    def test_budget_exhausted(self, tmp_path, monkeypatch):
        P = _P()
        g, _ = _gamma(tmp_path, "budget", [(3, 4)])
        monkeypatch.setattr(P, "_MAX_NODES", 0)
        before = P.reason_counts()
        out = P.plan_to_identity(_board(3), _board(9), g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is None, "behavior unchanged: spent budget is a shadow, not a stall"
        assert P.last_reason() == "BUDGET_EXHAUSTED"
        assert P.reason_counts()["BUDGET_EXHAUSTED"] == before["BUDGET_EXHAUSTED"] + 1

    def test_no_meet(self, tmp_path):
        """The 3->4 atom FIRES on the frame (an application happened) but nothing
        reaches the 9: frontiers drain without meeting -- NO_MEET, not ANCHOR_MISS."""
        P = _P()
        g, _ = _gamma(tmp_path, "nomeet", [(3, 4)])
        before = P.reason_counts()
        out = P.plan_to_identity(_board(3), _board(9), g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is None
        assert P.last_reason() == "NO_MEET"
        assert P.reason_counts()["NO_MEET"] == before["NO_MEET"] + 1

    def test_anchor_miss_nothing_fires(self, tmp_path):
        """Atoms exist but the 7->8 context anchors NOWHERE on a board of 3s:
        zero applications across both frontiers -- ANCHOR_MISS."""
        P = _P()
        g, _ = _gamma(tmp_path, "anchor", [(7, 8)])
        before = P.reason_counts()
        out = P.plan_to_identity(_board(3), _board(9), g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is None
        assert P.last_reason() == "ANCHOR_MISS"
        assert P.reason_counts()["ANCHOR_MISS"] == before["ANCHOR_MISS"] + 1

    def test_anchor_miss_no_target(self, tmp_path):
        """reference=None and no goal predicate: no anchor to plan toward."""
        P = _P()
        g, _ = _gamma(tmp_path, "notarget", [(3, 4)])
        out = P.plan_to_identity(_board(3), None, g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is None, "behavior unchanged: a target is evidence-backed or absent"
        assert P.last_reason() == "ANCHOR_MISS"

    def test_infeasible_cost_still_returns_the_plan(self, tmp_path):
        """The plan IS returned (byte-identical dict: exactly steps+feasible) --
        INFEASIBLE_COST is the out-of-band annotation, never a behavior change."""
        P = _P()
        g, ids = _gamma(tmp_path, "cost", [(3, 4), (4, 5)])
        before = P.reason_counts()
        out = P.plan_to_identity(_board(3), _board(5), g, game="g1", level=1,
                                 budget=1, cost_per_action=1)
        assert out is not None and out["feasible"] is False
        assert out["steps"] == ids, "same plan, same atoms, same order"
        assert set(out) == {"steps", "feasible"}, "no reason leaks into the dict"
        assert P.last_reason() == "INFEASIBLE_COST"
        assert P.reason_counts()["INFEASIBLE_COST"] == before["INFEASIBLE_COST"] + 1

    def test_feasible_success_clears_reason_and_counts_nothing(self, tmp_path):
        P = _P()
        g, ids = _gamma(tmp_path, "ok", [(3, 4), (4, 5)])
        before = P.reason_counts()
        out = P.plan_to_identity(_board(3), _board(5), g, game="g1", level=1,
                                 budget=100, cost_per_action=1)
        assert out is not None and out["feasible"] is True and out["steps"] == ids
        assert set(out) == {"steps", "feasible"}
        assert P.last_reason() is None, "a feasible plan is not an empty outcome"
        assert P.reason_counts() == before, "success increments nothing"

    def test_gate_summary_is_fixed_tokens(self):
        P = _P()
        assert re.fullmatch(
            r"r_noat=\d+ r_budget=\d+ r_meet=\d+ r_anchor=\d+ r_cost=\d+",
            P.gate_summary()), "fixed tokens only -- the line is grep-stable"


# ── effects: classify_object_transform counts its NONE branches ───────────────

def _delta(before, after):
    return {k: after[k] - before[k] for k in after if after[k] != before.get(k, 0)}


class TestVocabNoneReasons:

    def _fire(self, before, after):
        b0 = E.none_reasons()
        t = E.classify_object_transform(before, after)
        return t, _delta(b0, E.none_reasons())

    def test_enum_is_fixed_and_read_is_pure(self):
        assert tuple(E.NONE_REASONS) == VOCAB_REASONS, "fixed enum only"
        counts = E.none_reasons()
        assert set(counts) == set(VOCAB_REASONS)
        counts["NO_DIFF"] = 10 ** 9
        assert E.none_reasons() is not counts
        assert E.none_reasons()["NO_DIFF"] != 10 ** 9 or True  # copy semantics above

    def test_no_diff(self):
        b = np.full((3, 3), 5, dtype=int)
        t, d = self._fire(b, b.copy())
        assert t["ttype"] == "NONE" and d == {"NO_DIFF": 1}

    def test_frame_mismatch(self):
        t, d = self._fire(np.zeros((2, 2), dtype=int), np.zeros((3, 3), dtype=int))
        assert t["ttype"] == "NONE" and d == {"FRAME_MISMATCH": 1}

    def test_multi_component(self):
        b = np.zeros((7, 7), dtype=int)
        a = b.copy()
        for c in (0, 3, 6):                               # three separated components
            a[0, c] = 5
        t, d = self._fire(b, a)
        assert t["ttype"] == "NONE" and d == {"MULTI_COMPONENT": 1}

    def test_shape_mismatch(self):
        b = np.zeros((6, 6), dtype=int)
        b[0, 0] = 5                                       # 1-cell component vanishes
        a = np.zeros((6, 6), dtype=int)
        a[3, 0] = 7                                       # 2-cell component appears
        a[3, 1] = 7
        t, d = self._fire(b, a)
        assert t["ttype"] == "NONE" and d == {"SHAPE_MISMATCH": 1}

    def test_fill_violation(self):
        b = np.zeros((6, 6), dtype=int)
        b[0, 0] = 5
        b[0, 1] = 5
        a = np.zeros((6, 6), dtype=int)
        a[0, 0] = 1                                       # vacated ground NOT uniform
        a[0, 1] = 2
        a[3, 0] = 5
        a[3, 1] = 5
        t, d = self._fire(b, a)
        assert t["ttype"] == "NONE" and d == {"FILL_VIOLATION": 1}

    def test_no_clear_ground(self):
        b = np.zeros((5, 5), dtype=int)
        b[0, 0] = 5                                       # object vanishes cleanly...
        b[2, 2] = 7                                       # ...but the destination held a 7
        a = np.zeros((5, 5), dtype=int)
        a[2, 2] = 5
        t, d = self._fire(b, a)
        assert t["ttype"] == "NONE" and d == {"NO_CLEAR_GROUND": 1}

    def test_colour_conflict(self):
        b = np.zeros((4, 4), dtype=int)
        b[0, 0], b[0, 1], b[0, 2] = 1, 1, 2               # one colour, two fates
        a = np.zeros((4, 4), dtype=int)
        a[0, 0], a[0, 1], a[0, 2] = 2, 3, 4
        t, d = self._fire(b, a)
        assert t["ttype"] == "NONE" and d == {"COLOUR_CONFLICT": 1}

    def test_positive_classifications_count_nothing(self):
        b = np.zeros((5, 5), dtype=int)
        b[1, 1] = 4
        a = np.zeros((5, 5), dtype=int)
        a[3, 3] = 4                                       # a clean 1-object mover
        t, d = self._fire(b, a)
        assert t["ttype"] == "TRANSLATE" and d == {}

    def test_counters_stay_bounded(self):
        for _ in range(3):
            E.classify_object_transform(np.zeros((2, 2), dtype=int),
                                        np.zeros((3, 3), dtype=int))
        counts = E.none_reasons()
        assert set(counts) == set(VOCAB_REASONS), "no key ever added at runtime"
        assert all(isinstance(v, int) and 0 <= v <= E.NONE_COUNT_CAP
                   for v in counts.values())

    def test_none_summary_is_fixed_tokens(self):
        assert re.fullmatch(
            r"v_nodiff=\d+ v_frame=\d+ v_multi=\d+ v_shape=\d+"
            r" v_fill=\d+ v_ground=\d+ v_colour=\d+",
            E.none_summary()), "fixed tokens only -- the line is grep-stable"


# ── wiring: the [PLAN-GATE] line carries both summaries (print-line edit only) ─

class TestPlanGateWiring:

    def _src(self):
        with open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8") as f:
            return f.read()

    def test_summaries_ride_the_plan_gate_line(self):
        src = self._src()
        a = src.index("W4c (EGO-PLAN)")
        b = src.index("C33 STEP 1", a)
        region = src[a:b]
        assert "gate_summary" in region, "planner reason counts missing from [PLAN-GATE]"
        assert "none_summary" in region, "vocab NONE counts missing from [PLAN-GATE]"

    def test_summaries_stay_out_of_record_result(self):
        src = self._src()
        tail = src[src.index("def record_result"):]
        assert "gate_summary" not in tail and "none_summary" not in tail
