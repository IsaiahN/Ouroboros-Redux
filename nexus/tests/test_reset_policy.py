"""The reset boundary is game-natural: death resets, WIN stops, an infinite game that stops revealing
anything stalls, a ceiling backstops a forever-changing game, and the society retunes patience."""
import numpy as np
from nexus.reset_policy import ResetPolicy
from nexus.generational import GenerationalRunner


def test_reset_reasons():
    rp = ResetPolicy(base_patience=10, hard_cap=100)
    assert rp.lifetime_over(done=True, state="WIN", steps_in_life=5, steps_since_progress=0) == "win"
    assert rp.lifetime_over(done=True, state="GAME_OVER", steps_in_life=5, steps_since_progress=0) == "death"
    assert rp.lifetime_over(done=False, state="X", steps_in_life=5, steps_since_progress=10) == "stall"
    assert rp.lifetime_over(done=False, state="X", steps_in_life=100, steps_since_progress=0) == "cap"
    assert rp.lifetime_over(done=False, state="X", steps_in_life=5, steps_since_progress=3) is None


def test_society_grows_patience_when_stalling_without_progress_and_resets_on_a_level():
    rp = ResetPolicy(base_patience=10, hard_cap=100, patience_ceiling=50)
    rp.adapt("stall", gained_level=False)
    assert rp.patience > 10                      # exhausted without progress -> more room next time
    rp.adapt("stall", gained_level=True)
    assert rp.patience == 10                      # a level gained -> back to base


class InfiniteCyclingSession:
    """Never returns done; the board cycles through 3 states -> after 3 novel frames it stops revealing,
    so the lifetime must end by STALL, not run forever."""
    view_url = None
    def __init__(self):
        self.t = 0
    def _snap(self):
        g = np.zeros((6, 6), dtype=int); g[1, self.t % 3] = 3; g[4, 4] = 2
        return {"grid": g, "available": [1, 2, 3, 4], "levels_completed": 0, "state": "NOT_FINISHED", "done": False}
    def open(self):
        return self._snap()
    def step(self, val, data=None, reasoning=None):
        self.t += 1; return self._snap()
    def reset_after_death(self, reasoning=None):
        self.t = 0; return self._snap()
    def close(self):
        pass


def test_infinite_game_resets_by_stall_not_forever(tmp_path):
    r = GenerationalRunner(run_dir=str(tmp_path)).run(
        InfiniteCyclingSession(), "infinite", max_generations=3, hard_cap=200,
        stall_patience=5, wall_cap_s=30)
    import json
    d = json.load(open(r["ledger"]))
    ends = d["generation_ends"]
    assert ends and all(e["reason"] == "stall" for e in ends)   # each lifetime ended by stall, not the cap
    assert r["generations"] == 3                                 # and it reset into new generations, not one forever
