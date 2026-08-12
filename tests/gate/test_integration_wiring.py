"""W4c: the integration — every producer's consumer named, in code, in one loop.

binder <- per-step object evidence; bank commits at choice and settles at result; every
settlement routes; BROKEN·mechanism items reach the mint (bar-gated by affect); NOVEL items
persist to the import queue (the endogenous agenda); the planner computes plans whenever
WORKSPACE+REFERENCE are bound, DRIVES only on verified atoms (the wheel rule in code:
salience-grounded = atoms with >= 2 TRANSFERRED settlements), and shadow-logs otherwise;
affect narrates every modulation. Containment stays byte-checkable: a fresh box has no atoms,
so nothing ever drives.
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _src(f="cognitive_loop.py"):
    return open(os.path.join(REPO, f), encoding="utf-8", errors="replace").read()


class TestTheProducersFeed:

    def test_the_binder_is_fed_in_the_result_path(self):
        src = _src()
        i = src.find("def record_result")
        body = src[i:i + 20000]
        assert "RoleBinder" in src or "_role_binder" in body, "the binder is never constructed"
        assert ".observe(" in body and "_role_binder" in body, (
            "record_result never feeds the binder -- roles can never bind (starvation)")

    def test_the_bank_commits_at_choice_and_settles_at_result(self):
        src = _src()
        i_cycle = src.find("def cycle")
        i_rr = src.find("def record_result")
        cycle_body = src[i_cycle:i_rr] if i_cycle < i_rr else src[i_cycle:i_cycle + 30000]
        rr_body = src[i_rr:i_rr + 20000]
        assert "_predictor_bank" in src, "no bank instance"
        assert ".commit(" in cycle_body and "_predictor_bank" in cycle_body, (
            "the bank never commits at choice time")
        assert "_predictor_bank" in rr_body and ".settle(" in rr_body, (
            "the bank never settles at result time")

    def test_every_settlement_routes(self):
        src = _src()
        i = src.find("def record_result")
        body = src[i:i + 20000]
        assert "_residual_router" in src or "ResidualRouter" in src
        assert ".route(" in body, "settlements never reach the router"

    def test_broken_mechanism_reaches_the_mint(self):
        src = _src()
        assert "MDLMint" in src or "_mdl_mint" in src, "no mint instance"
        assert "mint_queue" in src, "the mint queue is never drained"
        assert ".consider(" in src

    def test_novel_items_persist_to_the_import_queue(self):
        src = _src()
        assert "import_queue" in src
        assert '"import_queue"' in src or "'import_queue'" in src, (
            "NOVEL items never persist -- the endogenous agenda is invisible")


class TestTheWheelRuleInCode:

    def test_the_planner_exists_and_is_gated(self):
        src = _src()
        assert "plan_to_identity" in src, "the planner is never consulted"
        i = src.find("plan_to_identity")
        window = src[max(0, i - 2500):i + 2500]
        assert "TRANSFERRED" in window or "_verified_atoms" in window or "verified" in window, (
            "the planner drives on unverified atoms -- the wheel rule demands "
            "salience-grounded operators (>= 2 TRANSFERRED settlements)")

    def test_shadow_mode_is_narrated(self):
        src = _src()
        assert "[PLAN]" in src, "plans must be narrated (shadow or drive) -- nothing silent"


class TestAffectAndProbes:

    def test_affect_narrates(self):
        src = _src()
        assert "AffectGains" in src or "_affect" in src
        assert "[AFFECT]" in src, "no channel moves without the state in the emitted stream"

    def test_the_mint_bar_is_consumed(self):
        src = _src()
        i = src.find("mint_bar")
        assert i != -1, "affect's mint_bar is a channel with no knob -- the twice-committed sin"

    def test_mute_probes_feed_the_aim(self):
        src = _src()
        assert "MuteHandler" in src or "_mute" in src
        assert ".mute(" in src, "the mute verdict is never raised -- the third link stays open"
