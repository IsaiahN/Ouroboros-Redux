"""THE BAND MASK MUST SURVIVE A RESTART.

`monotone_band_mask` qualifies a band only if its filled count is NON-DECREASING across the whole retained frame
history. A restart REFILLS the timer bar, so the count falls, so no band qualifies for up to `keep` frames after every
death -- and in that stretch the bar's own tick is charged as the board ANSWERING the agent. That is the proxy that
talks, admitted by a history that outlived the episode it described.

These tests pin the MECHANISM on a synthetic world where NOTHING but the bar ever moves, so any reading of
"responsive" is provably wrong by construction. They do not measure the effect size on a live game -- that is what the
control/treatment arms in `docs/tether/PREREG_the_mask_after_restart.md` are for.
"""
import numpy as np

from newhorse.redux_arch import engagement as E
from newhorse.redux_arch.engagement import EngagementMeter, monotone_band_mask
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard


class _BarOnlyWorld:
    """A board whose ONLY moving part is a top-edge timer bar that fills left to right. The puzzle never changes, so
    a truthful board-response meter must read this board as FROZEN for the entire run, restart or no restart."""

    # `per` is the bar's tick in cells. It is deliberately >= MIN_CELLS: a bar that ticks one cell at a time is
    # already below the smallness floor and could never be mistaken for an answer, so it would not exhibit the defect.
    def __init__(self, H: int = 16, W: int = 240, per: int = 4) -> None:
        self.H, self.W, self.per = H, W, per
        self.t = 0

    def restart(self) -> None:
        self.t = 0                                   # the bar REFILLS -- this is the whole point

    def frame(self) -> np.ndarray:
        g = np.zeros((self.H, self.W), dtype=int)
        g[0, :min(self.per * self.t, self.W)] = 5
        return g

    def step(self) -> np.ndarray:
        self.t += 1
        return self.frame()


def _run(meter: EngagementMeter, world: _BarOnlyWorld, n: int, label: str = "A2") -> None:
    for _ in range(n):
        meter.observe(world.step(), label)


# ---- the mechanism, isolated -------------------------------------------------------------------------------------

def test_the_ratchet_is_broken_by_a_refill_so_no_band_qualifies():
    """Stated at the level of the mask function itself: the same frames, in the same order, stop qualifying the
    moment a refilled prefix is prepended. Nothing about the agent is involved."""
    w = _BarOnlyWorld()
    first = [w.step() for _ in range(20)]
    assert monotone_band_mask(first).sum() > 0                 # a plain fill DOES qualify
    w.restart()
    second = [w.step() for _ in range(20)]
    assert monotone_band_mask(second).sum() > 0                # so does the refill, on its own
    assert monotone_band_mask(first + second).sum() == 0       # concatenated, the ratchet falls and the mask goes out


def test_without_the_clear_the_bar_is_charged_as_the_board_answering(monkeypatch):
    monkeypatch.setattr(E, "MASK_ON_RESTART", "keep")          # the pre-2026-07-31 wiring, exactly
    m = EngagementMeter()
    w = _BarOnlyWorld()
    _run(m, w, 40)
    assert m.mask().sum() > 0 and m.frozen() is True           # before the restart the mask holds and the board is mute
    w.restart(); m.note_restart()                              # ... a no-op under "keep"
    _run(m, w, 40)
    assert m.mask().sum() == 0                                 # the mask is blind
    assert m.frozen() is False                                 # and the board now reads as ANSWERING
    assert m.responsive_fraction() == 1.0                      # on every step of the window, on a board nothing moved


def test_with_the_clear_the_mask_re_qualifies_and_the_board_still_reads_frozen(monkeypatch):
    monkeypatch.setattr(E, "MASK_ON_RESTART", "clear")
    m = EngagementMeter()
    w = _BarOnlyWorld()
    _run(m, w, 40)
    assert m.frozen() is True
    w.restart(); m.note_restart()
    _run(m, w, 40)
    assert m.mask().sum() > 0                                  # history dropped -> the refill is a ratchet again
    assert m.frozen() is True                                  # and the truthful reading survives the restart
    assert m.responsive_fraction() == 0.0


def test_the_blindness_lasts_only_until_the_stale_history_ages_out(monkeypatch):
    """The defect is BOUNDED, and the bound is `keep`. Saying so is what stops 'the mask is broken' from being read as
    'the mask never works' -- a run with no restart is unaffected, and a run with one recovers after `keep` frames."""
    monkeypatch.setattr(E, "MASK_ON_RESTART", "keep")
    m = EngagementMeter(keep=24)
    w = _BarOnlyWorld()
    _run(m, w, 24)
    w.restart(); m.note_restart()
    _run(m, w, 10)
    assert m.mask().sum() == 0                                 # stale pre-restart frames still in the window
    _run(m, w, 24)                                             # ... now aged out entirely
    assert m.mask().sum() > 0


# ---- what the clear must NOT touch -------------------------------------------------------------------------------

def test_the_clear_drops_frames_only_and_keeps_what_the_agent_learned(monkeypatch):
    monkeypatch.setattr(E, "MASK_ON_RESTART", "clear")
    m = EngagementMeter()
    w = _BarOnlyWorld()
    _run(m, w, 40, label="A3")
    n_before, recent_before = m.observations("A3"), list(m._recent)
    m.note_restart()
    assert m._frames == [] and m._mask is None
    assert m.observations("A3") == n_before                    # per-action evidence is not evidence about the bar
    assert list(m._recent) == recent_before                    # nor is the frozen window: a restart does not wake a
    assert m.frozen() is True                                  # dead modality, and re-arming it would be change #2


def test_the_mask_is_askable_between_a_restart_and_the_next_frame(monkeypatch):
    """`mask()` indexes `_frames[-1]`. Every live caller observes first, but a guard that costs nothing is cheaper
    than a crash that ends a game and is then reported as `open_error`."""
    monkeypatch.setattr(E, "MASK_ON_RESTART", "clear")
    m = EngagementMeter()
    _run(m, _BarOnlyWorld(), 8)
    m.note_restart()
    assert m.mask().sum() == 0


# ---- the wiring: the policy's reset path actually calls it -------------------------------------------------------

def test_the_policy_reset_path_clears_the_meter(monkeypatch):
    monkeypatch.setattr(E, "MASK_ON_RESTART", "clear")
    p = ReduxPolicy(game_id="bar-x", blackboard=Blackboard(), warmup_cap=2)
    w = _BarOnlyWorld()
    for _ in range(10):
        p.observe(w.step(), [1, 2, 3, 4, 5])
        p.choose()
    assert p.engage._frames                                    # history accumulated...
    p.note_reset()
    assert p.engage._frames == []                              # ...and the restart drops it


def test_the_control_arm_switch_leaves_the_policy_reset_path_untouched(monkeypatch):
    monkeypatch.setattr(E, "MASK_ON_RESTART", "keep")
    p = ReduxPolicy(game_id="bar-x", blackboard=Blackboard(), warmup_cap=2)
    w = _BarOnlyWorld()
    for _ in range(10):
        p.observe(w.step(), [1, 2, 3, 4, 5])
        p.choose()
    n = len(p.engage._frames)
    p.note_reset()
    assert len(p.engage._frames) == n and n > 0                # the control arm is the OLD code path, bit for bit


def test_the_switch_default_is_the_shipped_wiring():
    """Read the module constant, not a re-parse of the environment: what ships is what the constant says."""
    assert E.MASK_ON_RESTART in ("clear", "keep")
