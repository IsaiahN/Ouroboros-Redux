"""THE INERTNESS RECEIPT -- of the actions the agent took, how many moved the board at all?

Why this test exists. CLASSIFIER 13 (the death the memory is recording is not the death that happened) rests on a
change-map a human LOOKED AT: on one game the agent's thirty actions appeared to change nothing while a bar depleted
across the top, which is what made three different actions "fatal" from one pixel-identical board. Nothing on any
receipt could say that. Worse, `tools/death_depth.py`'s `replay` verdict cannot be READ without it -- two deaths on an
identical board mean the agent walked back to the same place if it was moving, and mean nothing at all if it was not.

What is covered here: every observed frame is charged to exactly ONE literal at the observe site; frames that are not
the agent's doing are excluded BY NAME rather than dropped, so the identity can fail; a board where only a monotone
budget band ticks is charged `band_only` and NOT as a responsive board once the mask exists; the charge equals the
agent's action budget (`steps - retries`) end to end; and the printer renders a residue as a ★ rather than absorbing
it. Names no game; no board is pixel-fit to any real puzzle.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from newhorse.redux_arch.abort_code import ChainLedger
from newhorse.redux_arch.engagement import MIN_CELLS
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard


# ---- the ledger: one charge per frame, two denominators, an identity that can fail ----------------------------
def test_every_charge_lands_in_one_literal_and_the_two_denominators_stay_apart():
    c = ChainLedger()
    c.note_board("still", 0, True)
    c.note_board("band_only", 0, True)
    c.note_board("live", 12, True)
    c.note_board("sub_floor", 2, False)
    c.note_board("reshape")                                # an answer with no comparable cell count
    c.note_board_skip("no_predecessor")
    c.note_board_skip("label_reset")
    r = c.board_report()
    assert r["steps"] == 5 and r["skipped"] == 2 and r["frames"] == 7
    assert sum(r["split"].values()) == r["steps"]          # the partition closes on its own denominator
    assert sum(r["skip_split"].values()) == r["skipped"]
    assert r["moved_any"] == 4                             # everything but `still`
    assert r["moved_outside_band"] == 3                    # sub_floor + live + reshape
    assert r["cells_n"] == 4                               # the reshape contributes to NO mean
    assert abs(r["mean_masked_cells"] - (0 + 0 + 12 + 2) / 4.0) < 1e-9
    assert r["band_at_step"] == {"banded": 3, "unbanded": 1}   # its own denominator: the reshape passed no flag


def test_the_board_charge_is_run_level_and_a_segment_close_does_not_reset_it():
    """A segment-scoped inertness count would be unreadable beside the per-game `steps` it has to be compared with,
    and closing a segment mid-run would silently shrink it. The stage signals ARE segment-scoped; this is not."""
    c = ChainLedger()
    c.note_board("still", 0, False)
    c.note_step()
    c.end_segment("death")
    c.note_board("live", 9, False)
    assert c.board_report()["steps"] == 2


# ---- end to end: a board where only the budget bar moves ------------------------------------------------------
class _TimerOnlyWorld:
    """The pathology in its purest form: a bar ratchets along the bottom edge one cell per step, and NOTHING the
    agent does changes any other cell. A raw change-rate calls this a fully responsive board on every single step."""

    def __init__(self, H=20, W=48):
        self.g = np.zeros((H, W), dtype=int)
        self.k = 0

    def frame(self):
        return self.g.copy()

    def step(self, _label):
        if self.k < self.g.shape[1]:
            self.g[-1, self.k] = 4
            self.k += 1
        return self.frame()


def _play(world, n=40, avail=(1, 2, 3, 4, 5), gid="board-x"):
    p = ReduxPolicy(game_id=gid, blackboard=Blackboard(), warmup_cap=2)
    grid = world.frame()
    for _ in range(n):
        p.observe(grid, list(avail))
        lbl, _ = p.choose()
        grid = world.step(lbl)
    return p


def test_a_ticking_bar_is_not_a_responsive_board_once_the_mask_exists():
    p = _play(_TimerOnlyWorld(), n=40)
    r = p.engage_report()["board"]
    sp = r["split"]
    # The bar IS a change, so nothing is `still`; the whole run must be charged, and the charge is a partition.
    assert r["steps"] == 39 and sum(sp.values()) == 39     # 40 observes, the first has no predecessor
    assert r["skipped"] == 1 and r["skip_split"] == {"no_predecessor": 1}
    assert sp.get("still", 0) == 0
    # NOT ONE STEP of this run reads as a responsive board, which is the whole point: the raw reading would say 39.
    assert sp.get("live", 0) == 0
    # The band mask needs a window of history before it will mask anything, so the OPENING steps are charged on
    # their own merits -- one changed cell, below the smallness floor -- rather than being retro-masked. That is the
    # instrument refusing to mask on a guess, and it is asserted rather than smoothed away. Once the ratchet has
    # enough history, the same ticking is charged `band_only`: the clock moved, the puzzle did not.
    assert sp.get("band_only", 0) > sp.get("sub_floor", 0) > 0
    assert dict(_play(_TimerOnlyWorld(), n=20).chain.board_steps).get("band_only", 0) < sp["band_only"]


def test_the_charge_equals_the_agent_s_own_action_count():
    """CLASSIFIER 11's identity is the control on this receipt: one observed frame with an action label per action
    the agent emitted. A residue means a frame arrived with no action behind it, or an action produced no frame."""
    p = _play(_TimerOnlyWorld(), n=25)
    r = p.engage_report()["board"]
    assert r["steps"] == 24                                # 25 observes - the opening frame
    assert r["frames"] == 25


def test_the_meter_state_is_reported_and_the_two_halves_keep_their_own_denominators():
    p = _play(_TimerOnlyWorld(), n=40)
    e = p.engage_report()
    assert set(e) >= {"board", "meter", "escalations", "esc_branch", "family"}
    m = e["meter"]
    assert m["n_steps"] > 0 and m["labels"]                 # the organ HAS held this state since it shipped
    assert m["min_cells"] == MIN_CELLS
    assert m["band_cells"] and m["band_cells"] < m["board_cells"]   # a band was found and it is not the whole board
    for st in m["labels"].values():
        assert st["best"] < MIN_CELLS                       # nothing outside the band ever answered
    assert m["frozen"] is True


def test_a_frame_the_agent_did_not_cause_is_excluded_by_name_not_dropped():
    w = _TimerOnlyWorld()
    p = _play(w, n=12)
    before = p.engage_report()["board"]
    p.note_reset()                                          # the next frame is the RESTART's, not an action's
    p.observe(w.step("A1"), [1, 2, 3, 4, 5])
    after = p.engage_report()["board"]
    assert after["steps"] == before["steps"]                # no rate absorbed it
    assert after["skip_split"]["label_reset"] == 1          # ...it is on the record under its own name
    assert after["frames"] == before["frames"] + 1


# ---- the printer ----------------------------------------------------------------------------------------------
def _res(charged=10, steps=11, retries=1, live=3):
    return {"results": {"aa11-1": {
        "family": "effect", "steps": steps, "retries": retries,
        "engage": {"family": "effect", "escalations": 0, "esc_branch": {}, "escalated_at_end": None, "reverts": 0,
                   "board": {"steps": charged, "skipped": 1, "frames": charged + 1,
                             "split": {"still": 2, "band_only": charged - 2 - live, "live": live},
                             "skip_split": {"no_predecessor": 1}, "band_at_step": {"banded": charged},
                             "moved_any": charged - 2, "moved_outside_band": live, "live": live,
                             "mean_masked_cells": 1.5, "cells_n": charged},
                   "meter": {"n_steps": charged, "labels": {"A6": {"n": charged, "mean": 0.1, "best": 1.0}},
                             "frozen": True, "responsive_fraction": 0.0, "recent_window": [],
                             "band_cells": 40, "board_cells": 400, "min_cells": 4, "window": 12}}}}}


def test_the_printer_renders_a_clean_row_and_names_the_one_action_game(capsys):
    from sweep_chain import board_section
    board_section(_res())
    out = capsys.readouterr().out
    assert "BOARD RESPONSE PER GAME" in out and "aa11-1" in out
    assert "NON-ZERO residue" not in out                    # charged == steps - retries
    assert "A6" in out and "frozen=True" in out             # the one-label game names itself


def test_the_printer_stars_a_residue_instead_of_absorbing_it(capsys):
    from sweep_chain import board_section
    board_section(_res(charged=7))                          # steps-retries == 10, charge == 7
    out = capsys.readouterr().out
    assert "NON-ZERO residue" in out


def test_the_printer_reports_a_missing_instrument_as_an_absence(capsys):
    from sweep_chain import board_section
    board_section({"results": {"aa11-1": {"family": "effect", "steps": 5, "retries": 0}}})
    out = capsys.readouterr().out
    assert "ABSENCE" in out
