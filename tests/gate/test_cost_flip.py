"""THE COST-FLIP GATE (KNOBS A2, REGISTER L -- L1 goes LIVE at the call sites).

The estimator (latents.ESTIMATOR) and the planner's cost_per_action=None path
landed earlier, gated on the ls20 ground-truth recovery test; flipping the LIVE
call sites to consume the estimate is the SEPARATE decision this gate pins.

Isaiah's three conditions, verified here:

1. BOTH live call sites pass cost_per_action=None (cognitive_loop.py's
   plan_to_identity call; goal_abduction.abduced_plan's plan call) so the
   planner consumes ActionCostEstimator -- checked by AST, not grep.
2. FAIL CLOSED: an estimate resting on fewer than MIN_OBS=3 completion runs
   (Register G provenance GUESSED, documented in latents.py) OR missing
   entirely returns the old constant 1.0 with missing=True -- thin books never
   move the price.
3. LOG BOTH, per call site: every plan narrates a [COST] line carrying the
   estimate AND the 1.0 it replaced -- "[COST] fallback=1.0" when the books
   are cold, "[COST] est=X.XX (was 1.0)" when they support the estimate --
   verified by DRIVING the loop's real plan path (a live CognitiveLoop cycle)
   and the abduced-goal fallback site.

Run pre-flip: the call sites still pass 1.0, there is no MIN_OBS, and nothing
narrates [COST] -- every class here fails.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import types
from contextlib import redirect_stdout

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402

GAME = "cf25-c057f11b"       # knowledge streams ride the FULL version id (A3-3)
CELL = (20, 20)              # the transforming cell: colour 3 -> 4


def _L():
    from engines.egocentric import latents
    return latents


def _settle_row(agent, game, level, nontrivial):
    """One fabric settlements record in BetBook.settle's exact shape."""
    return {"agent": str(agent), "game": str(game), "level": int(level),
            "action": 6, "members": 1, "best": 0.0,
            "nontrivial": bool(nontrivial), "atom_key": None, "atom_bin": None}


def _completion_runs(fab, game, level, n):
    """n closed completion runs at (game, level), each 2 actions / 1 effective
    -> the ledgered cost is exactly 2.0 once the runs are trusted."""
    for i in range(int(n)):
        a = "m%d" % i
        fab.append("collective", "settlements", _settle_row(a, game, level, True))
        fab.append("collective", "settlements", _settle_row(a, game, level, False))
        fab.append("collective", "settlements",
                   _settle_row(a, game, level + 1, True))  # the level-up: run closed


# ── condition 1: both live call sites pass None (AST, no grep) ───────────────────────

def _cost_kwargs(path):
    """Every cost_per_action keyword on every plan_to_identity call in `path`."""
    with open(path, encoding="utf-8", errors="replace") as f:
        tree = ast.parse(f.read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name == "plan_to_identity":
                out.extend(kw.value for kw in node.keywords
                           if kw.arg == "cost_per_action")
    return out


class TestTheCallSitesPassNone:

    def test_the_loop_site_passes_none(self):
        vals = _cost_kwargs(os.path.join(REPO, "cognitive_loop.py"))
        assert vals, "cognitive_loop.py never passes cost_per_action to the planner"
        assert all(isinstance(v, ast.Constant) and v.value is None for v in vals), (
            "the loop's plan_to_identity call still hard-codes the cost -- the "
            "estimator is unwired (L1 stays a constant)")

    def test_the_abduction_site_passes_none(self):
        vals = _cost_kwargs(
            os.path.join(REPO, "engines", "egocentric", "goal_abduction.py"))
        assert vals, "abduced_plan never passes cost_per_action to the planner"
        assert all(isinstance(v, ast.Constant) and v.value is None for v in vals), (
            "abduced_plan's plan call still hard-codes the cost")


# ── condition 2: the fail-closed guard (MIN_OBS completion runs or bust) ─────────────

class TestTheFailClosedGuard:

    def test_min_obs_is_three_and_documented_guessed(self):
        lat = _L()
        assert getattr(lat, "MIN_OBS", None) == 3, (
            "latents.MIN_OBS missing or not 3 -- the fail-closed support bar "
            "has not landed")
        with open(lat.__file__, encoding="utf-8") as f:
            src = f.read()
        assert "GUESSED" in src, (
            "MIN_OBS=3 is a Register G value picked without measurement -- its "
            "provenance must be documented GUESSED (KNOBS A5)")

    def test_below_min_obs_fails_closed_flagged(self, tmp_path):
        """2 completion runs at a ledgered 2.0 rate: below the bar the estimate
        is the old constant, flagged -- with the honest counts still reported."""
        lat = _L()
        fab = KnowledgeFabric(str(tmp_path / "thin"), agent_id="a", kin_key="v4")
        _completion_runs(fab, "g1", 1, n=lat.MIN_OBS - 1)
        est = lat.ESTIMATOR.cost_per_action(fab, "g1", 1)
        assert est["cost"] == 1.0 and est["missing"] is True, (
            "an estimate resting on %d < MIN_OBS completion runs must fail "
            "closed to the flagged 1.0" % (lat.MIN_OBS - 1))
        assert est["completions"] == lat.MIN_OBS - 1, (
            "the guard must not hide the evidence it refused -- counts stay honest")

    def test_at_min_obs_the_estimate_is_trusted(self, tmp_path):
        lat = _L()
        fab = KnowledgeFabric(str(tmp_path / "warm"), agent_id="a", kin_key="v4")
        _completion_runs(fab, "g1", 1, n=lat.MIN_OBS)
        est = lat.ESTIMATOR.cost_per_action(fab, "g1", 1)
        assert est["missing"] is False and est["completions"] == lat.MIN_OBS
        assert est["cost"] == 2.0

    def test_no_evidence_is_still_the_flagged_fallback(self, tmp_path):
        lat = _L()
        fab = KnowledgeFabric(str(tmp_path / "empty"), agent_id="a", kin_key="v4")
        est = lat.ESTIMATOR.cost_per_action(fab, "g1", 1)
        assert est["cost"] == 1.0 and est["missing"] is True


# ── condition 3a: the LOOP's live plan path, driven (narration + consumption) ────────

def _frames():
    before = np.zeros((64, 64), dtype=int)
    before[CELL] = 3
    after = before.copy()
    after[CELL] = 4
    return before, after


def _drive_the_loop_plan_path(tmp_path, monkeypatch, warm):
    """A real CognitiveLoop cycle through the W4c EGO-PLAN block (the recipe
    proven by test_verified_hydration): returns the cycle's narration."""
    from cognitive_loop import CognitiveLoop
    from engines.egocentric import consumer
    from engines.egocentric.effects import learn_effect
    monkeypatch.chdir(tmp_path)
    before, after = _frames()
    loop = CognitiveLoop(data_root=str(tmp_path))
    loop.start_game(GAME, [6], max_actions=200)
    obs = types.SimpleNamespace(levels_completed=1)      # playing level 2
    with redirect_stdout(io.StringIO()):
        loop.cycle(before, obs)
        loop.record_result(before, False, 0.0, False)
    atom = learn_effect(before, 6, after)
    assert atom is not None and atom["kind"] == "EFFECT"
    atom["sigma"] = consumer.sigma_of(before, after)
    loop._gamma.add(atom, GAME, 2)
    if warm:
        # MIN_OBS closed completion runs at the playing level: cost 2.0 exactly
        _completion_runs(loop._ego_fabric, GAME, 2, n=_L().MIN_OBS)
    # plan-gate preconditions the loop earns live: level >= 1, a
    # REFERENCE-bound class, a reference snapshot
    for _ in range(4):
        loop._role_binder.observe_attributed(
            9, 6, False, True, {(40, 6), (40, 7)}, {(5, 5)}, 0)
    loop._reference_snapshot = after.copy()
    buf = io.StringIO()
    with redirect_stdout(buf):
        loop.cycle(before, obs)
    return buf.getvalue()


class TestTheLoopPlanPath:

    def test_cold_books_narrate_the_fallback(self, tmp_path, monkeypatch):
        out = _drive_the_loop_plan_path(tmp_path, monkeypatch, warm=False)
        assert "[PLAN]" in out, (
            "the plan path never ran -- the drive recipe broke:\n%s" % out)
        assert "[COST] fallback=1.0" in out, (
            "cold books must narrate the flagged fallback -- nothing silent:\n%s"
            % out)
        assert "[COST] est=" not in out

    def test_warm_books_narrate_the_estimate_and_what_it_replaced(
            self, tmp_path, monkeypatch):
        out = _drive_the_loop_plan_path(tmp_path, monkeypatch, warm=True)
        assert "[PLAN]" in out, (
            "the plan path never ran -- the drive recipe broke:\n%s" % out)
        assert "[COST] est=2.00 (was 1.0)" in out, (
            "MIN_OBS completion runs at a ledgered 2.0 rate must be consumed "
            "AND logged with the 1.0 they replaced:\n%s" % out)
        assert "[COST] fallback=" not in out


# ── condition 3b: the abduced-goal fallback site (the second live call site) ─────────

def _armed_abduction(tmp_path, warm):
    from engines.egocentric import goal_abduction as GA
    lat = _L()
    fab = KnowledgeFabric(str(tmp_path / "ab"), agent_id="a", kin_key="v4")
    g = E.Gamma(fab)
    ws = np.zeros((5, 5), dtype=int)
    ws[2, 2] = 3
    blank = np.zeros((5, 5), dtype=int)
    g.add(E.learn_effect(ws, 6, blank), game="g1", level=1)
    book = GA.GoalBook(fab)
    pre = np.zeros((8, 8), dtype=int)
    pre[2, 2] = 3
    post = np.zeros((8, 8), dtype=int)
    post[1, 1] = 7
    book.observe_levelup("g1", 1, pre, post)
    book.observe_levelup("g1", 1, pre, post)
    if warm:
        _completion_runs(fab, "g1", 1, n=lat.MIN_OBS)    # cost 2.0, trusted
    return GA, g, book, ws


class TestTheAbductionSite:

    def test_cold_books_narrate_the_fallback(self, tmp_path):
        GA, g, book, ws = _armed_abduction(tmp_path, warm=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            ap = GA.abduced_plan(g, book, ws, game="g1", level=1, budget=10,
                                 verified_counts={})
        out = buf.getvalue()
        assert ap is not None and ap["sig"] == "colour_count_zero:3"
        assert "[COST] fallback=1.0" in out, (
            "the abduced-goal site must narrate its own [COST] line:\n%s" % out)
        assert ap.get("cost_per_action") == 1.0 and ap.get("cost_missing") is True, (
            "the estimate must ride the abduced plan as data")

    def test_warm_books_price_feasibility_and_log_both_values(self, tmp_path):
        GA, g, book, ws = _armed_abduction(tmp_path, warm=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            ap = GA.abduced_plan(g, book, ws, game="g1", level=1, budget=10,
                                 verified_counts={})
        out = buf.getvalue()
        assert ap is not None
        assert "[COST] est=2.00 (was 1.0)" in out, (
            "the [COST] line must carry the estimate AND the 1.0 it "
            "replaced:\n%s" % out)
        assert ap.get("cost_per_action") == 2.0 and ap.get("cost_missing") is False
        assert ap["feasible"] is True                     # 1 step * 2.0 <= 10
        with redirect_stdout(io.StringIO()):
            tight = GA.abduced_plan(g, book, ws, game="g1", level=1, budget=1.5,
                                    verified_counts={})
        assert tight is not None and tight["feasible"] is False, (
            "1 step at the ledgered 2.0 rate costs 2.0 > 1.5 -- the estimate "
            "must actually price feasibility at the live site")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
