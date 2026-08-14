"""The budget restoration: replayed levels fund like live levels; roles scale allowances.

Measured disease: handoff episodes die at the frontier with 50-150 remaining while fresh
L1-fishers carry full purses; and the committed role economy (ROLE_BASE_ATP) was never wired.
"""
from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _src():
    return open(os.path.join(REPO, "cognitive_game_player.py"), encoding="utf-8",
                errors="replace").read()


def test_the_role_multiplier_helper():
    import cognitive_game_player as p
    fn = getattr(p.CognitiveGamePlayer, "_role_allowance_multiplier", None)
    assert fn is not None, "no role multiplier helper -- the salary organ is still unwired"
    assert fn("pioneer") == 1.5
    assert fn("generalist") == 1.2
    assert fn("optimizer") == 1.0
    assert fn("exploiter") == 0.8
    assert fn("unknown-role") == 1.0
    assert fn(None) == 1.0


def test_the_allowance_is_role_scaled():
    src = _src()
    assert "_role_allowance_multiplier" in src
    i = src.find("actions_per_level = ")
    window = src[i:i + 300]
    assert "_role_allowance_multiplier" in window or "role_mult" in window, (
        "the episode allowance ignores the role -- pioneers still get a generalist's purse")


def test_replayed_levels_fund_like_live_levels():
    src = _src()
    i = src.find("remaining_budget = ")
    window = src[max(0, i - 200):i + 600]
    assert re.search(r"levels_replayed|replay_result\.levels_completed", window), (
        "handoff funding ignores replayed levels -- the frontier is still budget-starved "
        "(the 3c remainder-only conservatism, now overridden by owner directive)")
    assert "action_budget" in window
