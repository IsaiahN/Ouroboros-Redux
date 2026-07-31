"""★ THE OFFLINE ATTRIBUTOR GETS A TEST FOR THE SAME REASON THE PRINTER DID. ★

`tools/death_depth.py` turns a sweep capture into the sentence "the restart bought the agent nothing." That
sentence rests entirely on one subtraction -- the `EARNED RESET @N` mark is `steps` AFTER the reset's own
increment, so the raw gap between two marks overstates the actions the agent actually took by exactly one -- and
on a terminal depth that is DERIVED rather than printed. An off-by-one in either place would not crash; it would
quietly produce a table of near-misses and turn a flat result into a varied one, or the reverse.

So `lives()` is pinned arithmetically here, and `parse()` is driven against output from the REAL
`sweep_chain.report()` rather than a capture I typed by hand -- a hand-typed capture would only test that the
parser agrees with my memory of the printer, which is the exact drift this file exists to catch.

The refusals get tests too: a capture with no deaths section must RAISE rather than read as "nothing died", a
★ MISSING terminal rationale must not become a derived death, and a game whose lives VARY must be named rather
than folded into the flat count.
"""
import io
import os
import sys
import contextlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from death_depth import lives, parse, main                             # noqa: E402


# --------------------------------------------------------------------------------------------------------------
# the subtraction

def test_the_reset_increment_is_subtracted_exactly_once_per_life():
    """Arm L's three shapes, pinned by hand. `s5i5` marked one reset at @51 and ended at steps=101: that is 50
    actions before the first death and 50 before the second, NOT 51 and 50, and not an interval of 50 hanging off
    a first life of 51. `sp80` marked three resets and ended on the action cap, so it has no derived life."""
    assert lives([51], 101, True) == [50, 50]                          # s5i5 / vc33
    assert lives([52, 85], 117, True) == [51, 32, 32]                  # su15
    assert lives([31, 62, 93], None, False) == [30, 30, 30]            # sp80 -- terminal=False, nothing derived
    assert lives([17, 82], None, False) == [16, 64]                    # bp35 -- the counter-example


def test_a_game_that_never_died_and_a_game_that_died_once_have_nothing_to_compare():
    """A single life cannot reproduce or fail to reproduce anything. The tool must not manufacture a comparison
    out of one number, and must not treat a deathless game as a flat one."""
    assert lives([], None, False) == []
    assert lives([65], None, False) == [64]
    assert lives([], 40, True) == [40]                                 # died once, terminally, no reset granted


def test_the_terminal_life_does_NOT_get_the_increment_subtracted():
    """The `-1` exists because a mark is post-reset. The terminal death is followed by no reset, so its depth is
    the final `steps` outright. Subtracting there too would shorten every terminal life by one and make flat games
    look like decaying ones -- the single most likely way this table could lie."""
    assert lives([10], 20, True)[-1] == 10                             # 20 - 10, not 19 - 10
    assert lives([10], 20, True)[0] == 9                               # and the first life still pays it


# --------------------------------------------------------------------------------------------------------------
# the parser, against the real printer

def _real_capture(tmp_path):
    """Render a capture with `sweep_chain.report()` itself, from a result dict built out of REAL policy receipts
    (`tests/test_sweep_report.py` owns those helpers and they are reused rather than re-typed here, so this test
    breaks loudly if the printer's shape moves)."""
    sys.path.insert(0, os.path.dirname(__file__))
    from test_sweep_report import _res, _run, _priced, _logged, _render, _N
    # keyed with a DASH, the way every real ARC game id is (`s5i5-18d95033`) -- the parser requires one, and that
    # requirement is what keeps the section's header and summary lines out of the table.
    res = _logged(_priced(_res(**{"aa11-aaaa": _run("aa11-aaaa", _N, ("A1",))}), retries={"aa11-aaaa": 2},
                          outcome="death_no_new_cause", extra_deaths=1),
                  terminal="death_no_new_cause", earned=2, causes=2)
    p = tmp_path / "capture.txt"
    p.write_text(_render(res), encoding="utf-8")
    return str(p), res


def test_the_parser_reads_the_REAL_printer_output_and_not_a_shape_I_invented(tmp_path):
    path, res = _real_capture(tmp_path)
    d = parse(path)
    assert "aa11-aaaa" in d["per"], d["per"]
    g = d["per"]["aa11-aaaa"]
    assert len(g["at"]) == 2, g                                        # two EARNED marks, read as ints
    assert all(isinstance(x, int) for x in g["at"])
    assert g["terminal"] is not None, "the terminal rationale was printed and must be read"
    assert len(g["acts"]) == 2 and all(a.startswith("A") for a in g["acts"]), g["acts"]
    # and the budget row crossed over intact, so a derived terminal depth has something to derive from
    assert d["steps"]["aa11-aaaa"]["steps"] == res["results"]["aa11-aaaa"]["steps"]
    assert d["steps"]["aa11-aaaa"]["outcome"] == "death_no_new_cause"


def test_the_lives_computed_from_a_real_capture_close_against_the_receipt(tmp_path):
    """End to end: the lives read out of a rendered capture must sum, with their increments added back, to the
    `steps` the receipt reported. If they do not, the table is describing a run that did not happen."""
    path, _res_ = _real_capture(tmp_path)
    d = parse(path)
    g, s = d["per"]["aa11-aaaa"], d["steps"]["aa11-aaaa"]["steps"]
    lv = lives(g["at"], s, g["terminal"] is not None)
    assert len(lv) == 3                                                # two granted restarts, one terminal death
    assert sum(lv) + len(g["at"]) == s, (lv, s)                        # one increment per reset, and no more


# --------------------------------------------------------------------------------------------------------------
# the refusals

_BUDGET_HDR = ("=== THE ACTION BUDGET (max_actions=200) ===\n"
               "  game               steps  decide  retries  deaths  residue  outcome\n")


def _capture(rows, deaths_body):
    budget = _BUDGET_HDR + "".join("  %-18s %5d %7d %8d %7d %8d  %s\n" % r for r in rows)
    return ("=== DECIDE FUNNEL ===\n  nothing\n\n" + budget
            + "\n=== WHAT THE DEATHS TAUGHT (§XIX rationale) ===\n" + deaths_body + "\n=== FIRING RECEIPTS ===\n")


def test_a_capture_WITHOUT_a_deaths_section_is_refused_and_not_read_as_nothing_died(tmp_path):
    """Every capture taken before this beat's printer shipped lacks the section. Reading one as a sweep in which
    nothing died would be the absence-as-evidence error, committed by a tool instead of by a sentence."""
    p = tmp_path / "old.txt"
    p.write_text("=== THE ACTION BUDGET (max_actions=200) ===\n  nothing\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        parse(str(p))


def test_a_MISSING_terminal_rationale_never_becomes_a_derived_death(tmp_path):
    """`sweep_chain` prints `TERMINAL: ★ MISSING` when a `death_*` exit carried no rationale. That is an
    instrument defect. Deriving a depth from it would invent the very number the flag says is absent."""
    body = ("  zz99-000000              2        1       2  death_no_new_cause\n"
            "      TERMINAL: ★ MISSING -- this game exited on a death and carried NO rationale line.\n")
    p = tmp_path / "missing.txt"
    p.write_text(_capture([("zz99-000000", 40, 38, 1, 2, 0, "death_no_new_cause")], body), encoding="utf-8")
    d = parse(str(p))
    assert d["per"]["zz99-000000"]["terminal"] is None
    assert lives(d["per"]["zz99-000000"]["at"], 40, False) == []       # nothing marked, nothing derived


def test_a_game_whose_lives_VARY_is_named_rather_than_folded_into_the_flat_count(tmp_path):
    """The flat count is the finding; the exceptions are the check on it. A tool that reported `1 of 2 flat` and
    never said WHICH would leave the counter-example -- the only game in arm L where a restart bought depth --
    invisible behind a ratio."""
    earned = ("      EARNED  : EARNED RESET #%d @%d: reset_earned: death #%d at level 0 — action A6 from this"
              " board ended the run and is a NEW avoidable cause (%d distinct causes now in game-memory).\n")
    body = ("  flat-000000             2        0       2  action_cap\n" + earned % (1, 31, 1, 1)
            + earned % (2, 62, 2, 2)
            + "  vary-000000             2        0       2  action_cap\n" + earned % (1, 17, 1, 1)
            + earned % (2, 82, 2, 2))
    p = tmp_path / "mixed.txt"
    p.write_text(_capture([("flat-000000", 93, 91, 2, 2, 0, "action_cap"),
                           ("vary-000000", 93, 91, 2, 2, 0, "action_cap")], body), encoding="utf-8")
    buf = io.StringIO()
    argv = sys.argv
    sys.argv = ["death_depth.py", str(p)]
    try:
        with contextlib.redirect_stdout(buf):
            main()
    finally:
        sys.argv = argv
    out = buf.getvalue()
    assert "1 of 2 reproduce their per-life action count EXACTLY across every life: flat-000000" in out, out
    assert "★ vary-000000 did NOT" in out, out
    assert "30, 30" in out and "16, 64" in out, out
    assert "cannot tell them apart" in out, "the tool must refuse to say WHY the count is constant"
