"""The DON'T-DIE organ (Tether: R_ρ's negative pole). Beat G found 13/25 dev games are lost to GAME_OVER, often
long before the action cap -- the agent walks into a fatal action it never learns to avoid. The environment allows
a post-death RESET that restarts the level within the same budget, so death is learnable: remember the (board,
action) that killed you and, on the deterministic retry, take a different action from that exact board. These tests
pin the pure memory and prove the SAME fatal cause is not repeated once learned -- with NO per-game code."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.survival import DeathMemory, board_fingerprint, AvatarHazard
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard, DIRECTIONAL


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


def test_would_be_new_is_pure_and_matches_note():
    dm = DeathMemory()
    board = _f({(1, 1): 4})
    assert dm.would_be_new(board, "A3") is True             # not yet recorded
    assert dm.n_deaths == 0 and dm.distinct_causes == 0     # ...and it did NOT mutate
    dm.note_death(board, "A3")
    assert dm.would_be_new(board, "A3") is False            # now known -> not new
    assert dm.would_be_new(board, "A4") is True             # different action -> still new
    assert dm.would_be_new(_f({(1, 2): 4}), "A3") is True   # different board -> still new
    assert dm.would_be_new(board, "RESET") is False         # RESET is never a cause


# ---- avatar-centric hazard generalization (fatal DESTINATION colours; generalizes the veto across boards) --------
def test_avatar_hazard_records_and_excludes_bg():
    hz = AvatarHazard()
    assert hz.note(10, bg=5) is True                        # colour 10 fatal, bg=5 -> learned
    assert hz.is_fatal_colour(10) is True
    assert hz.note(10, bg=5) is False                       # already known
    assert hz.note(5, bg=5) is False                        # moving onto BG is never a hazard (would freeze)
    assert hz.is_fatal_colour(5) is False
    assert hz.note(-1, bg=5) is False and hz.note(None, bg=5) is False   # off-board / absent -> ignored
    assert hz.fatal_colours() == {10}


def _board(cursor_rc, lava_rc, cur=7, lava=5, shape=(8, 10)):
    g = np.zeros(shape, dtype=int)
    g[cursor_rc] = cur
    g[lava_rc] = lava
    return g


def test_avatar_hazard_learns_on_death_and_vetoes_on_a_different_board():
    """The mechanism directly: a directional death where the cursor stepped onto colour 5 teaches 'colour 5 is fatal
    to enter' (bg=0 excluded); then on a DIFFERENT board (new fingerprint the exact-board veto can't match) a move
    that would step onto colour 5 is VETOED to a safe action. This is the cross-board generalization."""
    pol = ReduxPolicy(game_id="lava-x", blackboard=Blackboard())
    pol.family = DIRECTIONAL
    pol.cursor = 7; pol.vecs = {"A3": (0, -1), "A4": (0, 1)}
    # board before death: cursor at (3,2), lava (colour 5) at (3,3); the fatal action A4 steps cursor -> (3,3)=lava
    before = _board((3, 2), (3, 3))
    pol.frames.append(before); pol.acts.append("A4"); pol._pending = "A4"
    assert pol._dest_colour(before, "A4") == 5              # A4 would enter colour 5
    pol.observe(np.zeros((8, 10), dtype=int), [3, 4], 0, state="GAME_OVER")   # the death frame
    assert pol.hazard.fatal_colours() == {5}               # learned the fatal DESTINATION colour (bg 0 excluded)

    # DIFFERENT board (lava now at a new place): cursor (5,5), lava (colour 5) at (5,6). A4 -> (5,6)=lava -> hazard.
    pol.note_reset()
    newb = _board((5, 5), (5, 6))
    pol.frames.append(newb); pol._avail = [3, 4]
    lbl, _ = pol._survival_veto("A4", None)                 # A4 enters colour 5 (hazard) -> swap to safe A3
    assert lbl == "A3" and pol.n_hazard_vetoes == 1
    # a move that does NOT enter the hazard colour is left alone
    assert pol._survival_veto("A3", None)[0] == "A3"


def test_hazard_does_not_fire_for_click_or_two_body(monkeypatch):
    """PRECISION: the avatar-hazard is a DIRECTIONAL-cursor concept. Click (A6) and any policy without a cursor learn
    no destination hazard and the veto never fires -- so the wins (m0r0 two_body, tn36 click) are untouched."""
    pol = ReduxPolicy(game_id="click-x", blackboard=Blackboard())
    pol.cursor = None                                       # click / two-body have no directional cursor
    g = np.zeros((6, 6), dtype=int)
    pol.frames.append(g); pol._avail = [6]
    assert pol._dest_colour(g, "A6") is None                # no cursor -> no destination read
    assert pol._survival_veto("A6", {"x": 1, "y": 1}) == ("A6", {"x": 1, "y": 1})   # click untouched


def test_hazard_never_vetoes_when_no_safe_alternative(monkeypatch):
    """Precision/liveness: if EVERY available move is onto a hazard colour, the veto must not freeze -- the original
    action stands (better to act than to deadlock)."""
    pol = ReduxPolicy(game_id="z", blackboard=Blackboard())
    pol.cursor = 7; pol.vecs = {"A3": (0, -1), "A4": (0, 1)}
    pol.hazard.note(9, bg=0)
    g = np.zeros((5, 5), dtype=int); g[2, 2] = 7; g[2, 1] = 9; g[2, 3] = 9   # lava on BOTH sides
    pol.frames.append(g); pol._avail = [3, 4]
    lbl, _ = pol._survival_veto("A4", None)
    assert lbl in ("A3", "A4")                               # returns something, does not crash/freeze


# ---- §XIX reset-earned gate (Isaiah's ruling: reset needs reasoning backed by evidence from play/game-memory) ----
class _TwoTrap:
    """A corridor with TWO distinct fatal boards. ACTION3 moves right; column 4 kills AND column 6 kills, from two
    different board configs. First death (col4) is a NEW cause -> reset earned. If the agent then walks into the
    SAME col4 death again (veto disabled for the test), that repeat is NOT a new cause -> reset not earned."""
    def __init__(self):
        self.pos = 1; self.dead = False
    def _g(self, state="NOT_FINISHED"):
        g = np.zeros((8, 8), dtype=int)
        if not self.dead:
            g[3, self.pos] = 2
        return dict(grid=g, available=[3, 4], levels_completed=0, state=state, done=state in ("GAME_OVER", "WIN"))
    def open(self): self.pos = 1; self.dead = False; return self._g()
    def step(self, v):
        self.pos += 1 if v == 3 else -1
        if self.pos in (4, 6):
            self.dead = True; return self._g("GAME_OVER")
        return self._g()
    def reset(self): self.pos = 1; self.dead = False; return self._g()


def test_first_death_earns_reset_repeat_does_not():
    pol = ReduxPolicy(game_id="trap-x", blackboard=Blackboard(), warmup_cap=1)
    w = _TwoTrap()
    # drive to the FIRST death (a new cause) -> earned
    snap = w.open()
    pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap["state"])
    lbl, _ = pol.choose(); snap = w.step(int(lbl[1:]))
    while not snap["done"]:
        pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap["state"])
        lbl, _ = pol.choose(); snap = w.step(int(lbl[1:]))
    pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap["state"])
    earned1, why1 = pol.reset_earned()
    assert earned1 is True and "reset_earned" in why1 and "NEW avoidable cause" in why1
    # now FORCE the exact same death again (same board+action) and check it does NOT earn a reset
    fatal_board = pol.frames[-2]; fatal_act = pol.acts[-1]
    pol.note_reset()
    pol.frames.append(np.asarray(fatal_board)); pol.acts.append(fatal_act)  # re-enter the fatal board
    pol._pending = fatal_act
    pol.observe(np.zeros((8, 8), dtype=int), [3, 4], 0, state="GAME_OVER")   # same (board,action) death repeats
    earned2, why2 = pol.reset_earned()
    assert earned2 is False and "NOT earned" in why2 and "repeats" in why2   # no new learning -> not earned (§XIX)


def test_would_earn_reset_predicate_agrees_with_reset_earned():
    """The harness is_done uses would_earn_reset() BEFORE the death frame is observed; it must predict the same
    earned/not-earned that observe()->reset_earned() then produces."""
    pol = ReduxPolicy(game_id="trap-y", blackboard=Blackboard(), warmup_cap=1)
    w = _TwoTrap(); snap = w.open()
    pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap["state"])
    lbl, _ = pol.choose()
    # before submitting the (fatal) action, the predicate sees a fresh board+action -> would earn
    assert pol.would_earn_reset() is True
    snap = w.step(int(lbl[1:]))
    while not snap["done"]:
        pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap["state"])
        assert pol.would_earn_reset() == pol.deaths.would_be_new(pol.frames[-1], pol._pending)
        lbl, _ = pol.choose(); snap = w.step(int(lbl[1:]))


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
            earned, _why = pol.reset_earned()               # §XIX: retry only if the death EARNED it (new cause)
            if not earned or retries >= retry_cap:
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
