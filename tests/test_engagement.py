"""The BOARD-RESPONSE organ + MODALITY ESCALATION -- the lever SIGHT revealed (claude/DESIGN_see_before_proxy.md).

Rendering four zero-win games showed the agent locking onto ONE action for its whole budget while the puzzle sat frozen,
with a click modality available and untouched. An action the board does not answer has R_τ = 0: no gradient, nothing to
mint. This is the dual of Fig 2's residual duty -- refuse the intervention that says nothing.

Covered: the budget/timer band (an edge-flush ratchet that ticks every step regardless of the agent) is masked so it
cannot fake a responsive board; per-action response and the null test; frozen only when a full window says so; escalation
hands back an UNTRIED available action and stays silent when the board answers or when nothing is left to try; and the
end-to-end synthetic env -- directional does nothing, clicking a workspace cell sets it -> the policy detects the frozen
board, switches to the click modality, and engagement rises. Names no game; no board is pixel-fit to any real puzzle."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.engagement import EngagementMeter, monotone_band_mask, MIN_CELLS
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard, CLICK


def _board(H=20, W=20):
    return np.zeros((H, W), dtype=int)


# ---- the budget/timer band is masked so it cannot fake a responsive board -------------------------------------
def test_monotone_bottom_bar_is_masked_and_a_frozen_board_still_reads_frozen():
    """A bar filling along the bottom edge changes every step no matter what the agent does. Unmasked it would report a
    responsive board on a puzzle that never moves -- the proxy that talks while the ground is mute."""
    frames = []
    for k in range(14):
        g = _board()
        g[19, :k + 1] = 4                                  # the bar ratchets rightward, one cell per step
        frames.append(g)
    mask = monotone_band_mask(frames)
    assert mask[19, :].all()                               # the bottom band is masked
    assert not mask[:15, :].any()                          # the puzzle area is not
    m = EngagementMeter(window=6)
    for i, g in enumerate(frames):
        m.observe(g, "RESET" if i == 0 else "A1")
    assert m.frozen()                                      # only the budget bar moved -> the board is FROZEN
    assert m.is_null("A1")


def test_a_real_change_is_not_masked_and_the_board_reads_responsive():
    frames = []
    for k in range(14):
        g = _board()
        g[19, :k + 1] = 4                                  # same budget bar...
        g[5:9, 5:9] = (k % 3) + 1                          # ...but the puzzle itself also mutates
        frames.append(g)
    m = EngagementMeter(window=6)
    for i, g in enumerate(frames):
        m.observe(g, "RESET" if i == 0 else "A1")
    assert not m.frozen()
    assert m.mean("A1") >= MIN_CELLS
    assert not m.is_null("A1")
    assert m.responsive_fraction() > 0.5


def test_a_one_cell_blink_is_not_engagement():
    """A single cell toggling every step is a cursor/heartbeat, not a state change -- the board is still frozen."""
    m = EngagementMeter(window=6)
    for k in range(12):
        g = _board(); g[3, 3] = k % 2
        m.observe(g, "RESET" if k == 0 else "A2")
    assert m.frozen()
    assert m.is_null("A2")


def test_mask_refuses_to_guess_on_short_history():
    frames = [_board() for _ in range(3)]
    assert not monotone_band_mask(frames).any()            # never masks without enough evidence


# ---- escalation: hand back an UNTRIED modality, only when frozen ----------------------------------------------
def test_escalate_returns_an_untried_action_only_when_frozen():
    m = EngagementMeter(window=5)
    for k in range(4):
        g = _board(); g[19, :k + 1] = 4
        m.observe(g, "RESET" if k == 0 else "A5")
    assert m.escalate(["A5", "A6", "A7"]) is None          # window not full yet -> no verdict, no escalation
    for k in range(4, 12):
        g = _board(); g[19, :k + 1] = 4
        m.observe(g, "A5")
    assert m.frozen()
    assert m.escalate(["A5", "A6", "A7"]) in ("A6", "A7")  # a never-tried modality is handed back
    assert m.escalate(["A5"]) is None                      # nothing left to try -> the stall is real, not papered over


def test_escalate_is_silent_while_the_board_answers():
    m = EngagementMeter(window=5)
    for k in range(12):
        g = _board(); g[2:8, 2:8] = k % 4
        m.observe(g, "RESET" if k == 0 else "A1")
    assert not m.frozen()
    assert m.escalate(["A1", "A6"]) is None                # a working plan is never disturbed


# ---- end-to-end: a click-only env drives the policy to switch modality ----------------------------------------
class _ClickOnlyEnv:
    """Directional actions do NOTHING; clicking a workspace TILE sets that tile. A budget bar ratchets along the bottom
    every step regardless, so a naive change signal would call this board responsive. Available = directional + click,
    so the agent is never told which modality is the live one -- it has to find out by intervening.

    The workspace is TILED (2x2 cells per tile) because that is how a real board renders a unit of state, and because a
    fair test of the meter must produce a change the meter's general smallness floor accepts: MIN_CELLS exists to reject
    a cursor blink, so an env whose 'real' state change is smaller than a blink would be testing nothing."""

    TILE = 2

    def __init__(self, H=20, W=20):
        self.g = np.zeros((H, W), dtype=int)
        self.g[2:6, 2:14] = 8                              # a workspace region of 2x6 tiles to be set
        self.t = 0
        self.clicks = 0

    def step(self, label, data):
        self.t += 1
        self.g[19, :min(19, self.t)] = 4                   # the budget bar: moves no matter what
        if label == "A6" and data is not None:
            self.clicks += 1
            r, c = int(data["y"]), int(data["x"])
            if 2 <= r < 6 and 2 <= c < 14:
                r0 = 2 + ((r - 2) // self.TILE) * self.TILE     # snap to the tile the click landed in
                c0 = 2 + ((c - 2) // self.TILE) * self.TILE
                self.g[r0:r0 + self.TILE, c0:c0 + self.TILE] = 3   # a click on the workspace SETS that tile
        return self.g.copy()


def test_policy_switches_to_click_when_directional_is_inert():
    env = _ClickOnlyEnv()
    avail = [1, 2, 3, 4, 6]
    pol = ReduxPolicy(game_id="engage-x", blackboard=Blackboard(), warmup_cap=4)
    pol.observe(env.g.copy(), avail)
    for _ in range(60):
        lbl, data = pol.choose()
        pol.observe(env.step(lbl, data), avail)
    assert pol.n_modality_escalations >= 1                 # the frozen board forced a modality switch...
    assert pol.family == CLICK                             # ...and the switch to the answering modality is permanent
    assert env.clicks >= 5                                 # the agent is now actually intervening on the workspace
    assert int((env.g[2:6, 2:14] == 3).sum()) > 0          # and the workspace has been SET -- real engagement


class _ResponsiveEnv:
    """Every directional action moves a bar-shaped body (wrapping, so it never jams). A budget bar also ratchets."""

    def __init__(self):
        self.g = np.zeros((20, 20), dtype=int)
        self.r = 10
        self.t = 0
        self.g[self.r, 4:12] = 7

    def step(self, label, data):
        self.t += 1
        self.g[19, :min(19, self.t)] = 4
        self.g[self.r, 4:12] = 0
        self.r = 1 + (self.r + (1 if label in ("A2", "A4") else -1) - 1) % 15
        self.g[self.r, 4:12] = 7
        return self.g.copy()


def test_a_responsive_directional_env_never_escalates():
    """The control: when directional actions do move the board, the agent stays in its modality (no thrash)."""
    env = _ResponsiveEnv()
    avail = [1, 2, 3, 4, 6]
    pol = ReduxPolicy(game_id="engage-y", blackboard=Blackboard(), warmup_cap=4)
    pol.observe(env.g.copy(), avail)
    for _ in range(50):
        lbl, data = pol.choose()
        pol.observe(env.step(lbl, data), avail)
    assert pol.n_modality_escalations == 0
    assert pol.family != CLICK


def test_a_wrong_escalation_reverts_and_hands_the_game_back():
    """Safety: an env where NOTHING answers (the agent has merely jammed) must not be permanently converted to a click
    game. The escalation fires, finds clicks null too, undoes itself, and the original organ gets the game back -- and
    with no modality left to try, the stall stays visible instead of being papered over."""
    class _DeadEnv:
        def __init__(self):
            self.g = np.zeros((20, 20), dtype=int)
            self.g[6:10, 6:10] = 5
            self.t = 0

        def step(self, label, data):
            self.t += 1
            self.g[19, :min(19, self.t)] = 4              # only the budget bar ever moves
            return self.g.copy()

    env = _DeadEnv()
    avail = [1, 2, 3, 4, 6]
    pol = ReduxPolicy(game_id="engage-z", blackboard=Blackboard(), warmup_cap=4)
    pol.observe(env.g.copy(), avail)
    for _ in range(60):
        lbl, data = pol.choose()
        pol.observe(env.step(lbl, data), avail)
    assert pol.n_modality_escalations >= 1                 # it tried the untried modality...
    assert pol.n_modality_reverts >= 1                     # ...found it null too, and undid the switch
    assert pol.family != CLICK                             # the game was handed back to its own organ
    assert pol.engage.frozen()                             # and the stall is still reported, not hidden
