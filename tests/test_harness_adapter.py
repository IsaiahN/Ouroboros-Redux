"""
redux-triality: the OFFICIAL-harness adapter. The eval harness calls choose_action(frames, latest)->GameAction and
is_done() per step; PolicyDriver bridges that to ReduxPolicy. These pin the pure conversion + routing against real
arcengine FrameData/GameAction, so the (throwaway) Agent-subclass shell in the clone carries no logic worth testing.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from arcengine import FrameData, GameAction, GameState
from newhorse.redux_arch.harness_adapter import (grid_from_framedata, available_from, to_game_action, PolicyDriver)
from newhorse.redux_arch.policy import Blackboard, TWO_BODY, CLICK


def _fd(grid, avail, level=0, state=GameState.NOT_FINISHED):
    return FrameData(frame=[np.asarray(grid).tolist()], available_actions=list(avail),
                     levels_completed=level, state=state)


def test_grid_and_available_conversion():
    g = np.zeros((8, 8), dtype=int); g[1, 1] = 7
    fd = _fd(g, [GameAction.ACTION1, GameAction.ACTION2])
    assert grid_from_framedata(fd).shape == (8, 8) and grid_from_framedata(fd)[1, 1] == 7
    assert available_from(fd) == [1, 2]                     # enums -> ints


def test_to_game_action_click_sets_xy():
    ga = to_game_action("A6", {"x": 5, "y": 9})
    assert ga == GameAction.ACTION6
    assert ga.action_data.x == 5 and ga.action_data.y == 9   # ACTION6 carries the coordinate
    assert to_game_action("A3", None) == GameAction.ACTION3


class _AMirror:
    def __init__(self):
        self.L = [10, 4]; self.R = [10, 15]; self.mv = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
    def frame(self):
        g = np.zeros((20, 20), dtype=int); g[tuple(self.L)] = 7; g[tuple(self.R)] = 7; return g
    def step(self, v):
        d = self.mv.get(v, (0, 0))
        if v in (1, 2):
            self.L = [self.L[0] + d[0], self.L[1] + d[1]]; self.R = [self.R[0] + d[0], self.R[1] + d[1]]
        else:
            self.L = [self.L[0], self.L[1] + d[1]]; self.R = [self.R[0], self.R[1] - d[1]]


def test_driver_routes_two_body_and_returns_valid_game_actions():
    drv = PolicyDriver(game_id="m0r0-x", blackboard=Blackboard())
    w = _AMirror()
    for _ in range(12):
        fd = _fd(w.frame(), [GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3, GameAction.ACTION4, GameAction.ACTION5])
        ga = drv.choose(fd)
        assert isinstance(ga, GameAction)                    # always a submit-ready action
        w.step(int(ga.value))
    assert drv.family == TWO_BODY                            # routed via the harness contract, no per-game wiring


def test_driver_click_game_emits_action6_with_coords():
    drv = PolicyDriver(game_id="s5i5-x", blackboard=Blackboard())
    board = np.full((24, 24), 5, dtype=int); board[3:5, 3:5] = 2
    ga = drv.choose(_fd(board, [GameAction.ACTION6]))
    assert drv.family == CLICK and ga == GameAction.ACTION6
    assert 0 <= ga.action_data.x < 24 and 0 <= ga.action_data.y < 24


def test_is_done_win_ends_but_game_over_retries_first():
    drv = PolicyDriver(retry_cap=3)
    g = np.zeros((4, 4), dtype=int)
    assert drv.is_done(_fd(g, [GameAction.ACTION1], state=GameState.WIN)) is True
    assert drv.is_done(_fd(g, [GameAction.ACTION1], state=GameState.NOT_FINISHED)) is False
    # GAME_OVER is NOT done while retries remain (the don't-die organ restarts the level)
    assert drv.is_done(_fd(g, [GameAction.ACTION1], state=GameState.GAME_OVER)) is False
    drv.retries = 3                                          # budget spent
    assert drv.is_done(_fd(g, [GameAction.ACTION1], state=GameState.GAME_OVER)) is True


def test_death_emits_reset_and_records_then_gives_up():
    """The harness-contract death-retry: on GAME_OVER choose() emits RESET (up to retry_cap), recording the death so
    the retry can avoid the fatal action -- replicating run_policy_live's loop inside the per-step Agent contract."""
    drv = PolicyDriver(game_id="x-1", blackboard=Blackboard(), retry_cap=2)
    g = np.zeros((6, 6), dtype=int); g[2, 2] = 3
    # a couple of live steps so the policy has frames/acts to attribute a death to
    for _ in range(3):
        drv.choose(_fd(g, [GameAction.ACTION1, GameAction.ACTION2]))
    over = _fd(g, [GameAction.ACTION1, GameAction.ACTION2], state=GameState.GAME_OVER)
    assert drv.choose(over) == GameAction.RESET and drv.retries == 1     # first death -> RESET
    assert drv.choose(over) == GameAction.RESET and drv.retries == 2     # second death -> RESET
    assert drv.policy.n_deaths >= 2                                      # deaths were recorded (state threaded through)
    # budget spent: is_done now True, so the harness loop will exit rather than RESET forever
    assert drv.is_done(over) is True
