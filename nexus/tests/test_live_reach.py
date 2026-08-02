"""The live gate is REACHABLE from Nexus without a key or network: drive the kernel's real
run_live loop against a FakeSession and get back the gate metric. This proves the Nexus -> kernel
-> live-gate wiring; the actual online run (nexus.live_test) needs ARC_API_KEY and is not run here."""
import numpy as np
import pytest
from nexus.ground.live_arc import LiveArcGround


class FakeSession:
    view_url = None
    def __init__(self):
        self.t = 0
        self.g = np.zeros((8, 8), dtype=int); self.g[2, 2] = 3; self.g[2, 3] = 4
    def _snap(self):
        return {"available": [1, 2, 3, 4], "grid": self.g.copy(), "levels_completed": 0, "done": False}
    def open(self):
        return self._snap()
    def step(self, action_value, reasoning=None):
        self.t += 1
        self.g = np.zeros((8, 8), dtype=int); self.g[2, (2 + self.t) % 8] = 3; self.g[2, 3] = 4
        return self._snap()
    def close(self):
        pass


def test_live_harness_reachable_offline():
    g = LiveArcGround()
    try:
        res = g.run_offline(FakeSession(), max_actions=15, wall_cap_s=10.0)
    except ImportError as e:
        pytest.skip(f"kernel live harness not importable in this interpreter: {e}")
    assert "levels_completed" in res            # the gate metric is present
    assert res["steps"] >= 1                     # the kernel loop actually stepped
    assert not g.has_key()                       # no key needed for the offline reach
