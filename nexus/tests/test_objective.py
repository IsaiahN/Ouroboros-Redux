"""Perception made generative (DESIGN §7.5): the self-percept composes a POSITIVE objective that
proposes an action, not just a veto. For a depleting resource, the objective prefers the mover that
preserves it -- learned from observed resource deltas, never asserted."""
import numpy as np
from nexus.sensorium import build_sensorium
from nexus.sensorium.objective import SelfObjective


def _bar(length, colour=11, h=12, w=12):
    g = np.zeros((h, w), dtype=int)
    for j in range(length):
        g[11, j] = colour
    return g


def test_resource_objective_prefers_the_preserving_mover():
    s = build_sensorium()
    # A1 depletes the bar by 1 each step; A3 leaves it unchanged (preserves). Teach both.
    length = 11
    for _ in range(6):
        s.observe(_bar(length), "A1", _bar(length - 1), fatal=False, available=[1, 2, 3, 4]); length -= 1
        s.observe(_bar(length), "A3", _bar(length), fatal=False, available=[1, 2, 3, 4])       # A3 preserves
    assert s.report()["selected"] == "value"
    obj = SelfObjective(min_gap=0.2)
    # the policy wants the depleting A1; the objective should propose the preserving A3
    lbl, note = obj.propose("A1", [1, 2, 3, 4], s.selfmodel)
    assert lbl == "A3" and note.startswith("objective:preserve-resource")


def test_no_override_when_chosen_is_already_best():
    s = build_sensorium()
    length = 11
    for _ in range(6):
        s.observe(_bar(length), "A1", _bar(length - 1), fatal=False, available=[1, 2, 3, 4]); length -= 1
        s.observe(_bar(length), "A3", _bar(length), fatal=False, available=[1, 2, 3, 4])
    obj = SelfObjective(min_gap=0.2)
    lbl, note = obj.propose("A3", [1, 2, 3, 4], s.selfmodel)   # already choosing the preserving move
    assert lbl is None and note is None


def test_no_objective_without_a_value_self():
    s = build_sensorium()
    # a translating sprite -> translation self, no resource objective
    c = 2
    for _ in range(5):
        g0 = np.zeros((12, 12), dtype=int); g0[5, c] = 3
        g1 = np.zeros((12, 12), dtype=int); g1[5, c + 1] = 3
        s.observe(g0, "A2", g1, fatal=False, available=[1, 2, 3, 4]); c += 1
    obj = SelfObjective()
    assert obj.propose("A2", [1, 2, 3, 4], s.selfmodel) == (None, None)
