"""The two fixes the ls20 death-loop exposed (FINDINGS_the_death_loop_the_ledger_exposed):
  1. an unearned death (taught nothing new) stops the game as 'stuck' instead of resetting into the
     same trap forever (kernel §XIX);
  2. a (board, action) proved fatal in a past lifetime is VETOED to a non-fatal alternative across
     resets -- the 'return-to-start apply the veto' primitive the agent said it lacked."""
import numpy as np
from nexus.generational import apply_fatal_veto, GenerationalRunner


def test_fatal_veto_overrides_only_when_fatal_and_an_alternative_exists():
    fatal = {(111, "A4")}
    assert apply_fatal_veto(111, "A4", None, [1, 2, 3, 4], fatal) == ("A1", None, "A4")   # overridden
    assert apply_fatal_veto(111, "A1", None, [1, 2, 3, 4], fatal) == ("A1", None, None)   # not fatal
    assert apply_fatal_veto(111, "A6", {"x": 1, "y": 2}, [6], fatal) == ("A6", {"x": 1, "y": 2}, None)  # click: record-only
    assert apply_fatal_veto(111, "A4", None, [4], {(111, "A4")}) == ("A4", None, None)    # no alternative -> forced


class StuckSession:
    """Always dies the same way (one action, constant board) -> after the cause is known, further
    deaths are UNEARNED and the run must stop, not loop forever."""
    view_url = None
    def __init__(self):
        self.n = 0
    def _g(self):
        g = np.zeros((6, 6), dtype=int); g[2, 2] = 3; g[4, 4] = 5; return g
    def _snap(self, done=False, state="NOT_FINISHED"):
        return {"grid": self._g(), "available": [1], "levels_completed": 0, "state": state, "done": done}
    def open(self):
        self.n = 0; return self._snap()
    def step(self, val, data=None, reasoning=None):
        self.n += 1
        return self._snap(done=(self.n >= 2), state="GAME_OVER" if self.n >= 2 else "NOT_FINISHED")
    def reset_after_death(self, reasoning=None):
        self.n = 0; return self._snap()
    def close(self):
        pass


def test_identical_deaths_stop_as_stuck_not_forever(tmp_path):
    r = GenerationalRunner(run_dir=str(tmp_path)).run(
        StuckSession(), "stuck", max_generations=10, unearned_patience=2,
        hard_cap=50, stall_patience=50, wall_cap_s=30)
    assert r["outcome"] == "stuck"
    assert r["generations"] < 10               # stopped early instead of re-running the same failure 10x
