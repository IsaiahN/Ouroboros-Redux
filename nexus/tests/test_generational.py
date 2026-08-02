"""The fusion: one agent across many lifetimes over a run-local ledger. Drive it through death ->
reset -> win against a FakeSession (no key), and assert the generations COMPOUND: refuted causes
persist across resets, the ledger records the run's whole history, and the reasoning payload carries
the proposer section."""
import json
import numpy as np
from nexus.generational import GenerationalRunner


class FakeSession:
    view_url = "fake://card"
    def __init__(self):
        self.gen = 0; self.life_step = 0; self.levels = 0
    def _grid(self):
        g = np.zeros((8, 8), dtype=int)
        g[2, (2 + self.life_step) % 6] = 3
        g[5, 5] = 4
        return g
    def _snap(self, state="NOT_FINISHED", done=False):
        return {"grid": self._grid(), "available": [1, 2, 3, 4], "levels_completed": self.levels,
                "state": state, "done": done}
    def open(self):
        self.life_step = 0; return self._snap()
    def step(self, val, data=None, reasoning=None):
        self.life_step += 1
        if self.gen >= 2 and self.life_step == 3:          # generation 2 wins
            self.levels = 1; return self._snap(state="WIN", done=True)
        if self.life_step >= 6:                             # else die after 6 steps
            return self._snap(state="GAME_OVER", done=True)
        return self._snap()
    def reset_after_death(self, reasoning=None):
        self.gen += 1; self.life_step = 0; return self._snap()
    def close(self):
        pass


def test_generational_loop_compounds_across_lifetimes(tmp_path):
    r = GenerationalRunner(run_dir=str(tmp_path)).run(
        FakeSession(), "faketest", max_generations=6, hard_cap=12, wall_cap_s=60)

    assert r["outcome"] == "WIN"
    assert r["generations"] >= 2                # it took more than one lifetime
    assert r["best_level"] == 1

    d = json.load(open(r["ledger"]))
    assert len(d["deaths"]) >= 1               # deaths were recorded across generations
    assert len(d["refuted"]) >= 1              # and their causes carried into the refuted set (compounding)
    assert d["level_ups"] and d["level_ups"][-1]["to"] == 1
    assert len(d["actions"]) >= 1
    # every action carries the restored rich reasoning incl. the proposer section
    payload = d["actions"][-1]["reasoning"]
    for k in ("regime", "frame_read", "rule_hypothesis", "disproof", "status", "proposer"):
        assert k in payload
    assert "candidates" in payload["proposer"]


def test_ledger_summary_is_self_referenceable(tmp_path):
    r = GenerationalRunner(run_dir=str(tmp_path)).run(
        FakeSession(), "faketest2", max_generations=4, hard_cap=12, wall_cap_s=60)
    s = r["summary"]                            # the compact view a new lifetime would read first
    assert set(("best_level", "generations", "refuted", "death_causes")).issubset(s.keys())
