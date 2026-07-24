"""Brick 1 of the reasoning scaffold: a FRAME-NATIVE dense progress signal (the colour whose count rises most
monotonically) + reinforcement that nudges EXPLORATORY picks up that gradient -- the authors' 'follow the bar', with a
confidence gate so noise is not mistaken for progress, and the wins/committed plans left untouched. Names no game."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.progress import ProgressProbe
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard, EFFECT


def _fill(k, colour=3, shape=(8, 8)):
    """A board with the first k cells set to `colour` (a monotone 'bar' fills as k rises)."""
    g = np.zeros(shape, dtype=int)
    flat = g.ravel()
    flat[:k] = colour
    return flat.reshape(shape)


# ---- ProgressProbe: detection + precision ----------------------------------------------------------------------
def test_detects_monotone_fill_as_progress():
    p = ProgressProbe(min_obs=4)
    for k in range(0, 16, 2):                                 # colour-3 count 0,2,4,...,14 -> strictly rising
        p.observe(_fill(k))
    assert p.confident() and p.best_colour() == 3
    assert p.value() == 1.0                                   # currently at the max seen
    assert p.delta() == 2.0                                   # last step added 2 cells


def test_noise_is_not_progress():
    p = ProgressProbe(min_obs=4)
    rng = [3, 7, 1, 9, 2, 8, 4, 6]                            # colour-3 count flickers up and down -> not monotone
    for k in rng:
        p.observe(_fill(k))
    assert not p.confident()                                  # a dipping signal is rejected (precision)


def test_constant_and_tiny_signals_rejected():
    p = ProgressProbe(min_obs=4, min_range=3)
    for _ in range(8):
        p.observe(_fill(5))                                   # constant count -> no net increase -> not progress
    assert not p.confident()
    p2 = ProgressProbe(min_obs=4, min_range=3)
    for k in [0, 1, 1, 2, 2, 2]:                              # rises by only 2 (< min_range) -> rejected
        p2.observe(_fill(k))
    assert not p2.confident()


def test_backfills_late_appearing_colour():
    p = ProgressProbe(min_obs=3)
    for _ in range(3):
        p.observe(np.zeros((6, 6), dtype=int))               # only bg for a while
    for k in range(1, 9):
        p.observe(_fill(k, colour=5, shape=(6, 6)))          # colour 5 appears late and rises
    assert p.best_colour() == 5 and p.confident()


# ---- policy reinforcement: an exploratory pick follows the progress gradient ------------------------------------
class _EffectWorld:
    """No cursor (routes EFFECT). BOTH actions are EFFECTIVE (change the board), so the curiosity default alternates
    between them -- but only A5 RAISES progress (grows the colour-3 bar); A7 merely toggles an unrelated cell (no
    progress). The progress reinforcement should override the curiosity default toward A5. A static block keeps it out
    of the directional/two-body families."""
    def __init__(self):
        self.k = 0; self.tog = False
    def frame(self):
        g = np.zeros((12, 12), dtype=int); g[0:2, 0:2] = 4    # static structure -> not directional
        g[11, 11] = 9 if self.tog else 8                      # A7's toggle: effective but NOT progress (flickers)
        flat = g.ravel(); flat[20:20 + self.k] = 3            # colour-3 'bar' grows with A5 presses (monotone)
        return flat.reshape((12, 12))
    def step(self, lbl):
        if lbl == "A5":
            self.k = min(self.k + 1, 80)
        elif lbl == "A7":
            self.tog = not self.tog
        return self.frame()


def test_policy_reinforces_progress_raising_action():
    p = ReduxPolicy(game_id="prog-x", blackboard=Blackboard(), warmup_cap=2)
    w = _EffectWorld()
    grid = w.frame()
    presses = []
    for _ in range(40):
        p.observe(grid, [5, 7])
        lbl, _ = p.choose()
        presses.append(lbl)
        grid = w.step(lbl)
    assert p.family == EFFECT
    assert p.progress.confident() and p.progress.best_colour() == 3
    assert p._prog_credit.get("A5", 0.0) > 0.0                # A5 credited with raising progress
    assert p.n_prog_reinforce >= 1                            # reinforcement fired
    # over the SECOND half (after learning), A5 is pressed more than the no-op A7
    late = presses[20:]
    assert late.count("A5") > late.count("A7")
