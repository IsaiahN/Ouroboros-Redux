"""The DON'T-DIE organ (Tether: R_ρ's negative pole). Beat G found 13/25 dev games are lost to GAME_OVER, often
long before the action cap -- the agent walks into a fatal action it never learns to avoid. The environment allows
a post-death RESET that restarts the level within the same budget, so death is learnable: remember the (board,
action) that killed you and, on the deterministic retry, take a different action from that exact board. These tests
pin the pure memory and prove the SAME fatal cause is not repeated once learned -- with NO per-game code."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.survival import DeathMemory, board_fingerprint
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard


def _f(cells, shape=(8, 8)):
    g = np.zeros(shape, dtype=int)
    for (r, c), v in cells.items():
        g[r, c] = v
    return g


# ---- pure DeathMemory -------------------------------------------------------------------------------------------
def test_fingerprint_exact_and_distinct():
    a = _f({(1, 1): 3}); b = _f({(1, 1): 3}); c = _f({(1, 2): 3})
    assert board_fingerprint(a) == board_fingerprint(b)      # pixel-identical -> same fingerprint
    assert board_fingerprint(a) != board_fingerprint(c)      # one pixel different -> different


def test_note_and_veto():
    dm = DeathMemory()
    board = _f({(2, 2): 5})
    assert dm.is_fatal(board, "A3") is False
    assert dm.note_death(board, "A3") is True                # new cause
    assert dm.is_fatal(board, "A3") is True
    assert dm.note_death(board, "A3") is False               # same cause again -> not new (a repeated death)
    assert dm.n_deaths == 2 and dm.distinct_causes == 1
    # veto: A3 removed from this board, others kept
    assert dm.safe(board, ["A1", "A3", "A4"]) == ["A1", "A4"]
    # a DIFFERENT board with the same action is NOT vetoed (zero false positives)
    other = _f({(2, 3): 5})
    assert dm.safe(other, ["A3"]) == ["A3"]


def test_safe_never_empties():
    dm = DeathMemory()
    board = _f({(0, 0): 1})
    dm.note_death(board, "A1"); dm.note_death(board, "A2")
    # every candidate fatal here -> return them all rather than freeze (divergence had to happen earlier)
    assert dm.safe(board, ["A1", "A2"]) == ["A1", "A2"]


def test_ignores_reset_and_none():
    dm = DeathMemory()
    assert dm.note_death(_f({(0, 0): 1}), "RESET") is False
    assert dm.note_death(None, "A1") is False
    assert dm.n_deaths == 0


# ---- policy integration on a synthetic CLIFF world --------------------------------------------------------------
class _Cliff:
    """A 1-D corridor. An avatar (colour 2) sits at column `pos` on row 3. ACTION3 moves it right, ACTION4 left.
    Column 6 is a CLIFF: moving onto it -> GAME_OVER. The only always-safe action from any board is to move away
    from the cliff, but a naive cycler walks right into it. Post-death, env RESET restarts at pos=1.
    No cursor jumps, deterministic -> the retry re-encounters identical boards."""
    START = 1
    def __init__(self):
        self.pos = self.START
        self.dead = False
    def _snap(self, state="NOT_FINISHED"):
        g = np.zeros((8, 8), dtype=int)
        if not self.dead:
            g[3, self.pos] = 2
        return dict(grid=g, available=[3, 4], levels_completed=0, state=state,
                    done=(state in ("GAME_OVER", "WIN")))
    def open(self):
        self.pos = self.START; self.dead = False
        return self._snap()
    def step(self, val, data=None):
        if val == 3:
            self.pos += 1
        elif val == 4:
            self.pos = max(0, self.pos - 1)
        if self.pos >= 6:                                    # stepped onto the cliff
            self.dead = True
            return self._snap("GAME_OVER")
        return self._snap()
    def reset_after_death(self, reasoning=None):
        self.pos = self.START; self.dead = False
        return self._snap()
    view_url = None


def test_policy_stops_repeating_the_same_fatal_death():
    """Drive ReduxPolicy through the cliff world with the runner's death-retry loop, verifying that once a (board,
    action) death is recorded, that exact fatal action is never emitted again from that exact board -> the SAME
    death never recurs (distinct_causes == n_deaths: every death has a distinct cause, none is a repeat)."""
    w = _Cliff()
    pol = ReduxPolicy(game_id="cliff-x", blackboard=Blackboard(), warmup_cap=2)
    snap = w.open()
    steps = 0; retries = 0; retry_cap = 8
    fatal_reemitted = 0
    while steps < 60:
        pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap["state"])
        if snap["done"]:
            if snap["state"] == "WIN":
                break
            if retries >= retry_cap:
                break
            retries += 1; steps += 1
            snap = w.reset_after_death(); pol.note_reset(); continue
        cur = np.asarray(snap["grid"])
        # was the about-to-be-chosen action known fatal here BEFORE choosing?
        lbl, data = pol.choose()
        if pol.deaths.is_fatal(cur, lbl):
            fatal_reemitted += 1                             # the veto let a known-fatal action through -> bug
        snap = w.step(int(lbl[1:]), data=data)
        steps += 1
    assert pol.n_deaths >= 1                                  # it did die at least once (learned from a real death)
    assert fatal_reemitted == 0                               # but NEVER re-emitted a known-fatal action
    assert pol.deaths.distinct_causes == pol.n_deaths         # no death cause ever repeated
    assert pol.n_vetoes >= 1                                  # the veto actually fired (steered away from the cliff)
