"""The closed price->generation circuit: verdicts are classified from the ground, and each verdict
shapes the next proposal -- refute vetoes, mute routes to empowerment, confirm is preferred."""
from nexus.verdict import Verdict, classify, VerdictCircuit


def test_classify_reads_the_ground():
    assert classify(1, 2, level_delta=1, done=False, state="X") == Verdict.CONFIRM   # progress
    assert classify(1, 1, level_delta=0, done=True, state="GAME_OVER") == Verdict.REFUTE  # death
    assert classify(1, 1, level_delta=0, done=False, state="X") == Verdict.MUTE       # nothing changed
    assert classify(1, 2, level_delta=0, done=False, state="X") == Verdict.MOVED      # world changed, no reward


def test_refute_vetoes_the_move_next_time():
    c = VerdictCircuit()
    c.record(7, "A4", None, Verdict.REFUTE)                       # A4 from board 7 ended the run
    lbl, data, note = c.shape(7, "A4", None, [1, 2, 3, 4])
    assert lbl != "A4" and note.startswith("veto:refuted")       # vetoed to a non-fatal alternative
    assert (7, lbl) not in c.fatal


def test_mute_routes_to_empowerment():
    c = VerdictCircuit()
    c.record(7, "A1", None, Verdict.MUTE)                         # A1 from board 7 revealed nothing
    lbl, data, note = c.shape(7, "A1", None, [1, 2, 3, 4])
    assert lbl != "A1" and note.startswith("empower:mute")        # try something that might discriminate
    assert (7, lbl) not in c.mute


def test_confirm_is_preferred_when_overriding():
    c = VerdictCircuit()
    c.record(7, "A4", None, Verdict.REFUTE)                       # A4 fatal -> must override
    c.record(7, "A2", None, Verdict.CONFIRM)                      # A2 produced progress here
    lbl, _, _ = c.shape(7, "A4", None, [1, 2, 3, 4])
    assert lbl == "A2"                                            # the confirmed move wins the override


def test_forced_when_no_nonfatal_alternative():
    c = VerdictCircuit()
    c.record(7, "A1", None, Verdict.REFUTE)
    assert c.shape(7, "A1", None, [1]) == ("A1", None, None)     # only action available -> forced, no veto


def test_click_actions_are_counted_not_overridden():
    c = VerdictCircuit()
    v = c.record(7, "A6", {"x": 1, "y": 2}, Verdict.REFUTE)      # data action: counted only
    assert v == Verdict.REFUTE and c.counts["refute"] == 1 and not c.fatal
    assert c.shape(7, "A6", {"x": 1, "y": 2}, [6]) == ("A6", {"x": 1, "y": 2}, None)
