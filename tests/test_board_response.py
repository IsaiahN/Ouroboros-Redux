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
from newhorse.redux_arch.abort_code import ChainLedger, LIVE_REDRAW_FRAC
from newhorse.redux_arch.engagement import MIN_CELLS
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard
from newhorse.redux_arch import policy as policy_mod


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


def test_the_cell_histogram_is_exact_and_shares_the_mean_s_denominator():
    """WHICH MEMBERS. `mean_masked_cells` pools four populations into one number, and every predicate downstream of
    this reading is a MAX. The histogram and the per-literal max exist so both of those can be checked instead of
    argued. The histogram's denominator must be the SAME `cells_n` the mean is divided by -- a charge that reached
    one site and not the other has to be a number that fails."""
    c = ChainLedger()
    for cells in (0, 0, 2, 2, 3, 12):
        c.note_board("live" if cells >= MIN_CELLS else ("still" if cells == 0 else "sub_floor"), cells, False)
    c.note_board("reshape")                                # no comparable count: in neither the mean nor the hist
    r = c.board_report()
    assert r["cells_hist"] == {"0": 2, "2": 2, "3": 1, "12": 1}
    assert r["cells_hist_n"] == r["cells_n"] == 6          # one denominator, two readouts
    assert sum(r["cells_hist"].values()) == r["cells_hist_n"]
    bk = r["cells_by_kind"]
    assert bk["sub_floor"] == {"n": 3, "mean": (2 + 2 + 3) / 3.0, "max": 3}
    assert bk["live"] == {"n": 1, "mean": 12.0, "max": 12}
    assert "reshape" not in bk                             # a fabricated count here would be averaged downstream
    assert max(int(k) for k in r["cells_hist"]) == 12       # the statistic the predicates read, recoverable


def test_the_histogram_is_a_readout_and_no_decision_reads_it():
    """An instrument that feeds a decision is not an instrument. `board_cells_hist`, `_board_cells_kind` and -- since
    2026-08-01 -- `board_live_hist` / `LIVE_REDRAW_FRAC` / `live_split` are written at exactly one site and read only
    by `board_report` and the sweep printer; if a decision path ever imports them this fails, which is the notice
    that the freeze in HEARTBEAT item 4 has been crossed.

    The `live` split is the reason this test is EXTENDED rather than duplicated: a second copy of this pin would let
    the two drift, and the whole claim is that ONE list of names is confined to ONE file."""
    import subprocess
    out = subprocess.run(["grep", "-rn",
                          "board_cells_hist\\|_board_cells_kind\\|cells_by_kind"
                          "\\|board_live_hist\\|_board_live_unsized\\|LIVE_REDRAW_FRAC\\|LIVE_FRAC_MARKS"
                          "\\|live_split\\|live_at_frac\\|live_max_frac\\|live_hist",
                          os.path.join(os.path.dirname(__file__), "..", "src")],
                         capture_output=True, text=True).stdout
    files = {ln.split(":")[0].rsplit("/", 1)[-1] for ln in out.splitlines() if ln.strip()}
    assert files <= {"abort_code.py"}, files


# ---- the `live` split: a partition of a literal that pooled two populations ------------------------------------
def test_the_live_split_is_a_partition_of_the_coarse_live_total_and_names_the_unsized():
    """WHICH MEMBERS, one level below `live`. The coarse column stays; this must sum back to it or fail. A `live`
    step that arrives with no board area is charged `live_unsized` at its own name rather than dropped, for the same
    reason `note_board_skip` exists: a split whose denominator silently omits rows cannot be checked."""
    c = ChainLedger()
    for cells, area in ((2, 100), (4, 100), (60, 100), (99, 100)):
        c.note_board("live", cells, True, area=area)
    c.note_board("live", 7, True)                          # no area reached the ledger
    c.note_board("sub_floor", 2, True, area=100)           # NOT live: contributes to neither side of the split
    c.note_board("still", 0, True, area=100)
    r = c.board_report()
    ls = r["live_split"]
    assert r["live"] == 5
    assert sum(ls.values()) == r["live"]                   # the identity, published so it can fail
    assert ls == {"live_local": 2, "live_redraw": 2, "live_unsized": 1}
    assert r["live_hist_n"] == 4                           # the unsized step is in the split, NOT in the joint hist
    assert "2/100" in r["live_hist"] and "7/100" not in r["live_hist"]


def test_the_live_split_is_recomputable_at_any_edge_from_the_banked_joint():
    """THE EDGE IS AN AUTHOR'S CHOICE, so the record must not depend on it. The joint (cells, area) distribution is
    exact and un-bucketed, which is what makes the printed split a VIEW rather than the measurement -- anybody who
    prefers another fraction recomputes it from this dict without spending a sweep."""
    c = ChainLedger()
    for cells in (1, 5, 40, 51, 80):
        c.note_board("live", cells, False, area=100)
    r = c.board_report()
    assert r["live_hist"] == {"1/100": 1, "5/100": 1, "40/100": 1, "51/100": 1, "80/100": 1}
    assert r["live_at_frac"] == {"0.25": 3, "0.50": 2, "0.75": 1}
    assert abs(float(r["live_max_frac"]) - 0.8) < 1e-9
    # the same reading, recomputed from the banked joint at an edge the ledger never printed
    at_third = sum(n for k, n in r["live_hist"].items()
                   if (int(k.split("/")[0]) / int(k.split("/")[1])) >= 1 / 3.0)
    assert at_third == 3                                   # 40, 51 and 80 all clear a third; 1 and 5 do not
    assert r["live_redraw_frac"] == LIVE_REDRAW_FRAC       # the edge that WAS applied is on the receipt


def test_two_boards_of_different_size_are_not_pooled_by_the_split():
    """The defect being repaired is a count read without its denominator. 40 changed cells is most of a 64-cell
    board and a corner of a 4096-cell one; if the area were dropped at the write site the split would re-commit the
    error one level down."""
    c = ChainLedger()
    c.note_board("live", 40, False, area=64)               # 62% of the board: the screen was replaced
    c.note_board("live", 40, False, area=4096)             # 1% of the board: something answered
    r = c.board_report()
    assert r["live_split"] == {"live_local": 1, "live_redraw": 1, "live_unsized": 0}
    assert r["live_hist"] == {"40/64": 1, "40/4096": 1}


def test_a_live_answer_that_replaces_the_whole_board_is_charged_live_and_ALSO_redraw():
    """WHAT THE SPLIT DOES NOT LICENSE. It is a readout: the step is still `live`, the `live` column still counts it,
    the smallness floor is untouched, and nothing about what counts as answered has moved. If a future edit makes
    `note_board` route a large answer somewhere other than `live`, this fails."""
    c = ChainLedger()
    c.note_board("live", 4096, False, area=4096)
    r = c.board_report()
    assert r["split"] == {"live": 1} and r["live"] == 1
    assert r["moved_outside_band"] == 1
    assert r["cells_by_kind"]["live"] == {"n": 1, "mean": 4096.0, "max": 4096}
    assert r["live_split"]["live_redraw"] == 1


def test_the_area_reaches_the_ledger_from_the_live_observe_site_end_to_end():
    """A field never COMPUTED and printed as a zero is a mis-labelled receipt. This drives the real policy over a
    real board and asserts the area actually crossed the call site -- no `live` step may be `unsized` on a run where
    every frame had a shape."""
    w = _BigAnswerWorld()
    p = _play(w, n=14, avail=(1, 2, 3, 4, 5), gid="board-live")
    r = p.engage_report()["board"]
    assert r["live"] > 0, r["split"]
    assert r["live_split"]["live_unsized"] == 0            # the area crossed the site on every live step
    assert sum(r["live_split"].values()) == r["live"]
    assert r["live_split"]["live_redraw"] > 0              # the world replaces most of the board on purpose
    assert all(k.endswith("/%d" % (w.g.shape[0] * w.g.shape[1])) for k in r["live_hist"])


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


class _BigAnswerWorld:
    """Every action repaints most of the board -- the purest form of the thing `live` was pooling: an answer so
    large it cannot be a puzzle responding to one action. Names no game and is pixel-fit to none."""

    def __init__(self, H=16, W=16):
        self.g = np.zeros((H, W), dtype=int)
        self.k = 0

    def frame(self):
        return self.g.copy()

    def step(self, _label):
        self.k += 1
        self.g[:, :] = (self.k % 5) + 1                    # the whole screen is replaced, every step
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
def _res(charged=10, steps=11, retries=1, live=3, outcome="death_retry_cap"):
    return {"results": {"aa11-1": {
        "family": "effect", "steps": steps, "retries": retries, "outcome": outcome,
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


def _res_split(local=7, redraw=3, unsized=0, live=10, area=400):
    r = _res(charged=20, steps=21, retries=1, live=live)
    b = r["results"]["aa11-1"]["engage"]["board"]
    b["live_split"] = {"live_local": local, "live_redraw": redraw, "live_unsized": unsized}
    b["live_hist"] = {"3/%d" % area: local, "%d/%d" % (area // 2, area): redraw}
    b["live_hist_n"] = local + redraw
    b["live_at_frac"] = {"0.25": redraw, "0.50": redraw, "0.75": 0}
    b["live_max_frac"] = 0.5
    b["live_redraw_frac"] = 0.5
    return r


def test_the_printer_splits_live_beside_the_coarse_column_and_keeps_both(capsys):
    from sweep_chain import board_section
    board_section(_res_split())
    out = capsys.readouterr().out
    assert "BOARD RESPONSE PER GAME" in out                # the coarse table is still printed...
    assert "the `live` column split by SIZE" in out        # ...and the finer reading sits beside it
    assert "READOUT ONLY" in out
    assert "NON-ZERO residue against the coarse `live` total" not in out


def test_the_printer_stars_a_split_that_does_not_sum_back_to_live(capsys):
    """The identity is only worth publishing if it can fail. 7 + 2 + 0 != 10."""
    from sweep_chain import board_section
    board_section(_res_split(local=7, redraw=2, unsized=0, live=10))
    out = capsys.readouterr().out
    assert "NON-ZERO residue against the coarse `live` total" in out
    assert "★-1" in out


def test_the_printer_reports_an_absent_split_as_an_absence_not_a_zero(capsys):
    """A run that predates the split carries no `live_split`, and a printer that rendered that as `local=0,
    redraw=0` would be the field-never-computed-printed-as-a-zero defect in a new column."""
    from sweep_chain import board_section
    board_section(_res())                                  # the pre-split receipt shape
    out = capsys.readouterr().out
    assert "the `live` column split by SIZE" in out
    assert "This is an ABSENCE and prices nothing" in out


# ---- the tail: the one action whose frame nobody observed -----------------------------------------------------
def test_the_unobserved_tail_is_read_off_the_exit_literal_and_both_branches_are_pinned():
    """`_play_policy` observes at the TOP of its loop. A run that ends on a `break` (WIN, any `death_*`) observed
    the frame it broke on; a run that falls out of the loop CONDITION never observed the frame its last action
    produced. One rule, both branches, and a literal nobody has classified gets a number from nobody."""
    from sweep_chain import observed_tail
    assert observed_tail("WIN") == 0
    for lit in ("death_no_reset_support", "death_no_new_cause", "death_retry_cap"):
        assert observed_tail(lit) == 0
    for lit in ("action_cap", "wall_cap", "action_and_wall_cap", "loop_exit_unattributed"):
        assert observed_tail(lit) == 1
    assert observed_tail("open_error:RuntimeError") is None  # reached no exit; it may NOT be given a number
    assert observed_tail(None) is None


def test_a_cap_exit_is_clean_one_short_and_a_death_exit_is_clean_dead_on(capsys):
    """THE POST-HOC CORRECTION, PINNED SO IT CAN FAIL. Arm N pre-registered `charged == steps - retries` flat and
    it failed by exactly -1 on exactly the capped games. This test states the fitted rule; the NEXT arm is where it
    stands or falls, and the printer must not absorb a violation of it silently."""
    from sweep_chain import board_section
    board_section(_res(charged=9, steps=11, retries=1, outcome="action_cap"))     # 10 actions, tail 1 -> clean
    out = capsys.readouterr().out
    assert "NON-ZERO residue" not in out
    board_section(_res(charged=10, steps=11, retries=1, outcome="action_cap"))    # the OLD identity now stars
    assert "NON-ZERO residue" in capsys.readouterr().out
    board_section(_res(charged=10, steps=11, retries=1, outcome="death_retry_cap"))
    assert "NON-ZERO residue" not in capsys.readouterr().out
    board_section(_res(charged=9, steps=11, retries=1, outcome="death_retry_cap"))
    assert "NON-ZERO residue" in capsys.readouterr().out


def test_a_game_with_no_exit_literal_forfeits_its_residue_rather_than_guessing(capsys):
    from sweep_chain import board_section
    board_section(_res(charged=3, steps=11, retries=1, outcome="open_error:RuntimeError"))
    out = capsys.readouterr().out
    assert "does not say whether the last frame was observed" in out
    assert "NON-ZERO residue" not in out                    # a wild residue is NOT claimed off an unclassified exit


def test_the_printer_reports_a_missing_instrument_as_an_absence(capsys):
    from sweep_chain import board_section
    board_section({"results": {"aa11-1": {"family": "effect", "steps": 5, "retries": 0}}})
    out = capsys.readouterr().out
    assert "ABSENCE" in out


# ---- the escalation organ: which games can even reach it -------------------------------------------------------
class _FrozenWorld:
    """Nothing the agent does changes anything, ever. The purest case for the organ that exists to refuse a null
    intervention: if it cannot fire here, it cannot fire."""

    def __init__(self, H=16, W=16):
        self.g = np.zeros((H, W), dtype=int)

    def frame(self):
        return self.g.copy()

    def step(self, _label):
        return self.frame()


def _play_frozen(avail, family=None, n=60):
    p = ReduxPolicy(game_id="frozen-x", blackboard=Blackboard(), warmup_cap=2)
    if family is not None:
        p.family = family                                   # as a game WITH directional actions would have routed
    w = _FrozenWorld()
    grid = w.frame()
    for _ in range(n):
        p.observe(grid, list(avail))
        lbl, _ = p.choose()
        grid = w.step(lbl)
    return p


def test_broad_a_natively_click_routed_game_never_reaches_the_escalation_organ_at_all(monkeypatch):
    """THE GUARD, AS A RECEIPT INSTEAD OF A CODE READING -- and, since 2026-08-01, THE CONTROL ARM RATHER THAN THE
    LIVE BEHAVIOUR. Under the broad exemption `_decide` returns at the `click_native` exit BEFORE
    `_modality_escalate` is called, so on a game whose action set carries no directional actions the organ built to
    break "one label forever" is never consulted -- however frozen the board and however many untried actions are
    available. The control below is the same board and the same action set routed to another organ.

    NOTE WHAT THIS DOES *NOT* SAY. On a game that advertises action 6 ALONE the point is moot: there is no other
    action to escalate to and the single label is the action set, not a pathology. The guard only bites where an
    alternative EXISTS, which is why this test gives the game two -- and that is precisely the case the narrowed
    exemption now hands to the organ (see the twin below)."""
    monkeypatch.setattr(policy_mod, "CLICK_EXEMPT", "broad")
    p = _play_frozen([6, 7])
    assert p.family == "click" and p._pre_esc_family is None      # natively routed, never escalated into
    assert p.n_modality_escalations == 0
    assert set((p.engage_report()["meter"]["labels"] or {})) == {"A6"}   # A7 was never once emitted
    # ...and it is not that there was nothing to escalate TO: the organ, asked directly, hands back A7.
    assert p.engage.frozen() is True
    assert p.engage.escalate(["A6", "A7"]) == "A7"


def test_narrow_the_same_game_DOES_reach_the_organ_and_tries_the_untried_action(monkeypatch):
    """The twin, and the whole of the 2026-08-01 change measured on the same board as its control. Same frozen
    world, same action set, same 60 steps -- the only difference is which exemption predicate is in force. The
    untried action is actually emitted, and the escalation is counted at the organ's own site.

    A game advertising action 6 ALONE is unaffected by this, which is what protects a committed click organ: with
    nothing to escalate TO, the narrowed predicate returns exactly what the broad one returned."""
    monkeypatch.setattr(policy_mod, "CLICK_EXEMPT", "narrow")
    p = _play_frozen([6, 7])
    assert p.family == "click" and p._pre_esc_family is None
    assert p.n_modality_escalations >= 1, p.n_modality_escalations
    assert set((p.engage_report()["meter"]["labels"] or {})) == {"A6", "A7"}

    q = _play_frozen([6])                                        # click-only action set: nothing to escalate to
    assert q.n_modality_escalations == 0, q.n_modality_escalations
    assert set((q.engage_report()["meter"]["labels"] or {})) == {"A6"}


def test_the_same_frozen_board_routed_to_another_organ_does_escalate():
    """The control that makes the guard the explanation rather than a coincidence: identical board, identical
    action set, one branch different."""
    p = _play_frozen([6, 7], family="effect")
    assert p.n_modality_escalations >= 1
    assert set((p.engage_report()["meter"]["labels"] or {})) == {"A6", "A7"}
