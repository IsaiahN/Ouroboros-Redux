"""
Tier-1 AFFORDANCE from the transition residual (Tether §4.4 Lane A). Non-translation games (paint/toggle/place)
route to EFFECT: the agent learns which actions actually change the board (from R_τ) and presses those, avoiding
no-ops and the undo action -- purposeful action where the old fallback just cycled blindly.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.affordance import EffectAffordance
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard, EFFECT


def _f(cells):
    g = np.zeros((10, 10), dtype=int)
    for (r, c), v in cells.items():
        g[r, c] = v
    return g


def test_effective_vs_noop():
    aff = EffectAffordance()
    on = _f({(5, 5): 2}); off = _f({(5, 5): 3})
    for _ in range(4):
        aff.update(on, "A5", off)     # ACTION5 changes 1 cell every time
        aff.update(off, "A7", off)    # ACTION7 no-op
    assert aff.effective() == ["A5"]  # A5 effective, A7 excluded (never changes)
    assert aff.effect("A5") >= 1.0 and aff.effect("A7") == 0.0


def test_undo_is_detected_and_not_chosen():
    aff = EffectAffordance()
    base = _f({(2, 2): 2}); painted = _f({(2, 2): 2, (4, 4): 9, (4, 5): 9})
    aff.update(base, "A2", painted)                 # A2 paints
    aff.update(painted, "A7", base, two_ago=base, prev_action="A2")   # A7 reverts A2's change -> undo
    assert aff.undo() == "A7"
    # A7 changed the board so it registers effect, but choose() must avoid the undo action
    assert aff.choose(["A2", "A7", "A6"], visits={}) == "A2"


def test_choose_prefers_effective_excludes_click_and_explores_cold():
    aff = EffectAffordance()
    # cold start: no effect evidence -> explore least-visited NON-click action
    assert aff.choose(["A5", "A6", "A7"], visits={"A5": 3, "A7": 0}) == "A7"
    # warm: A5 effective -> pick it (not the click A6)
    on = _f({(5, 5): 2}); off = _f({(5, 5): 3})
    for _ in range(3):
        aff.update(on, "A5", off); aff.update(off, "A5", on)
    assert aff.choose(["A5", "A6"], visits={}) == "A5"


class _Toggle:
    """A button game: ACTION5 toggles one fixed cell 2<->3 (no translation, no cursor); ACTION7 is a no-op. A static
    block sits in the corner. Nothing moves -> not directional/two-body -> must route EFFECT."""
    def __init__(self):
        self.on = False
    def frame(self):
        g = np.zeros((16, 16), dtype=int); g[0:2, 0:2] = 4        # static structure
        g[8, 8] = 3 if self.on else 2
        return g
    def step_val(self, lbl):
        if lbl == "A5":
            self.on = not self.on
        return self.frame()


def test_policy_routes_effect_and_presses_the_effective_button():
    p = ReduxPolicy(game_id="sb26-x", blackboard=Blackboard())
    w = _Toggle()
    grid = w.frame()
    presses = []
    for _ in range(18):
        p.observe(grid, [5, 7])                                   # only ACTION5 + ACTION7 available
        lbl, _ = p.choose()
        presses.append(lbl)
        grid = w.step_val(lbl)
    assert p.family == EFFECT                                     # not UNDRIVABLE -- it can act
    assert "A5" in p.effect_aff.effective()                       # learned ACTION5 is the effective button
    assert presses.count("A5") > presses.count("A7")             # and presses it more than the no-op
