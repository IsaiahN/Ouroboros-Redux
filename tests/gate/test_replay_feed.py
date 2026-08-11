"""The replay observation feed: replayed actions teach; they never credit.

The sealed run's mechanism: handoff episodes arrive at the frontier with established=[] --
93 replayed actions bypass all learning. Frames and actions during replay are fully known;
feeding them observe-only delivers a named body + established move-map to the continuation.
THE LINE THAT MAY NOT BE CROSSED: no credit, no mint from replayed steps (no synthetic
signal -- the wheel rule).
"""
from __future__ import annotations
import os, sys
from types import SimpleNamespace
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl                                  # noqa: E402
from engines.egocentric.observer import EgoObserver          # noqa: E402
from engines.egocentric.spine import GoalSpine               # noqa: E402


def _feed():
    fn = getattr(cl.CognitiveLoop, "_ego_feed", None)
    assert fn is not None, "CognitiveLoop._ego_feed missing -- the replay feed has not landed"
    return fn


def _standin():
    return SimpleNamespace(_ego_observer=EgoObserver(), _goal_spine=GoalSpine(),
                           _ego_prev_centroid=None, _ego_last_known_cen=None)


class TestTheFeed:

    def test_replayed_movement_establishes_the_delta_map(self):
        s = _standin()
        feed = _feed()
        pos = 1
        g = np.zeros((12, 12), dtype=int); g[6, pos] = 4
        feed(s, g, 1)
        for i in range(8):
            act = 1 if i % 2 == 0 else 2
            if act == 1:
                pos = min(pos + 2, 10)
            g = np.zeros((12, 12), dtype=int); g[6, pos] = 4
            feed(s, g, act)
        assert s._goal_spine.established(), (
            "eight fed steps with contingent motion established nothing -- the feed is not "
            "reaching note_move and the frontier amnesia stands")

    def test_the_feed_never_credits_or_mints(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        i = src.find("def _ego_feed")
        j = src.find("\n    def ", i + 10)
        body = src[i:j if j != -1 else len(src)]
        for name in (".credit(", ".credit_click(", ".mint(", "level_changed"):
            assert name not in body, (
                "_ego_feed contains %s -- replayed steps must TEACH, never SIGNAL "
                "(no synthetic credit)" % name)

    def test_the_replay_loop_feeds_it(self):
        src = open(os.path.join(REPO, "cognitive_game_player.py"), encoding="utf-8",
                   errors="replace").read()
        i = src.find("def _replay_winning_sequences")
        j = src.find("\n    def ", i + 10)
        body = src[i:j if j != -1 else len(src)]
        assert "_ego_feed" in body, (
            "_replay_winning_sequences never feeds the ego machinery -- replayed actions "
            "still teach nothing (starvation)")
