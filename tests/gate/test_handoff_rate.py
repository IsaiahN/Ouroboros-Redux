"""The handoff-rate lever: banked games stop re-fishing solved levels.

p=0.2 means 80% of a banked game's episodes blindly re-solve L1. Bank-aware probability
(0.8 banked / 0.2 unbanked) quadruples frontier tickets. EXACTLY ONE random draw either way --
the RNG stream must not shift (containment is byte-identity on fresh boxes).
"""
from __future__ import annotations
import os, sys, re
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _src():
    return open(os.path.join(REPO, "cognitive_game_player.py"), encoding="utf-8",
                errors="replace").read()


def test_the_probability_helper_contract():
    import cognitive_game_player as p
    fn = getattr(p.CognitiveGamePlayer, "_replay_probability", None)
    assert fn is not None, "no _replay_probability -- the lever has not landed"
    assert fn(True) == 0.8 and fn(False) == 0.2


def test_one_draw_and_bank_check_precedes_it():
    src = _src()
    i = src.find("_replay_winning_sequences(")
    window = src[max(0, i - 2500):i]
    assert "_replay_probability" in window, "the replay branch does not use the helper"
    draws = len(re.findall(r"random\.random\(\)", window))
    assert draws == 1, "the replay branch must make exactly ONE random draw (stream identity)"
