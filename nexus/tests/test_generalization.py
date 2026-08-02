"""Ground-verified refutation GENERALIZATION over an injected (open) signature. A fatal action learned
on similar boards abstracts to the signature after echo (>= sig_echo distinct grounded instances), and
then vetoes the action on a NEW board sharing the signature -- fixing the ls20 pattern where deaths at
near-identical boards never generalized. An over-general signature is refuted by a counterexample."""
from nexus.verdict import Verdict, VerdictCircuit


def test_refutation_generalizes_after_echo_and_vetoes_a_new_matching_board():
    c = VerdictCircuit(sig_echo=2)
    sig = ("S",)                                   # a stand-in signature shared by several boards
    c.record(1, "A4", None, Verdict.REFUTE, signature=sig)   # fatal at board 1
    assert ("A4" and (sig, "A4")) not in c.sig_confirmed     # one instance -> not yet generalized
    _, _, note1 = c.shape(3, "A4", None, [1, 2, 3, 4], signature=sig)  # board 3 (never seen) not yet vetoed
    assert note1 is None
    c.record(2, "A4", None, Verdict.REFUTE, signature=sig)   # fatal at board 2 -> echo of 2 distinct boards
    assert (sig, "A4") in c.sig_confirmed                     # generalization CONFIRMED by the ground
    lbl, _, note = c.shape(99, "A4", None, [1, 2, 3, 4], signature=sig)  # a brand-new matching board
    assert lbl != "A4" and note.startswith("veto:general")   # vetoed by generalization, never seen before


def test_counterexample_refutes_an_overgeneral_signature():
    c = VerdictCircuit(sig_echo=2)
    sig = ("S",)
    c.record(1, "A4", None, Verdict.REFUTE, signature=sig)   # one fatal instance recorded under the signature
    # ... but at another board with the same signature, A4 SURVIVES (the world moved, run continued)
    c.record(5, "A4", None, Verdict.MOVED, signature=sig)
    assert (sig, "A4") in c.sig_refuted                       # signature relaxed -> not a reliable fatal
    c.record(6, "A4", None, Verdict.REFUTE, signature=sig)   # further fatals do NOT re-confirm a refuted sig
    assert (sig, "A4") not in c.sig_confirmed


def test_signature_none_preserves_exact_only_behavior():
    c = VerdictCircuit()
    c.record(1, "A4", None, Verdict.REFUTE)                   # no signature -> exact-board only
    assert not c.sig_confirmed and not c.sig_fatal_boards
    assert c.shape(2, "A4", None, [1, 2, 3, 4]) == ("A4", None, None)  # a different board is NOT vetoed
