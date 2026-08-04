"""Molecule grounding (invention loop Half A.5): quantifier over a scope makes ORDER/MATCH/CLEAR evaluable --
the richness a single-pair relation cannot express. These pin the bridge so molecules stay live + rich."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ["OURO_COMPOSE"] = "1"                          # the generated relation basis (for the LT ORDER relation)

from newhorse.redux_arch.molecule import Molecule, enumerate_molecules, score_molecule
from newhorse.redux_arch.dsl import composed_relational_atoms, make_atom


def _rel(name):
    return next(a for a in composed_relational_atoms() if a.name == name)


def test_order_molecule_distinguishes_sorted_from_shuffled():
    """ALL consecutive pairs left-to-right ordered -- the thing a single (focus,target) relation cannot say."""
    order = Molecule("ALL", _rel("focus.col<target.col"), "consecutive")
    sorted_scene = [((0, 1), 5), ((0, 3), 5), ((0, 6), 5), ((0, 9), 5)]
    shuffled = [((0, 6), 5), ((0, 1), 5), ((0, 9), 5), ((0, 3), 5)]
    assert order.evaluate(sorted_scene) == (True, 1.0)
    v, d = order.evaluate(shuffled)
    assert v is False and d < 1.0


def test_clear_molecule_monotone_as_objects_collected():
    """NONE object has the target colour -- collect/erase-all, with a degree that rises as the colour disappears."""
    clear = Molecule("NONE", make_atom("HAS_COLOUR", 5), "unary")
    assert clear.evaluate([((0, 6), 7), ((0, 2), 7)]) == (True, 1.0)          # cleared
    assert clear.degree([((0, 1), 5), ((0, 3), 5), ((0, 6), 7)]) < 1.0        # some remain
    # monotone: fewer target-colour objects -> higher degree
    assert clear.degree([((0, 3), 5), ((0, 6), 7)]) > clear.degree([((0, 1), 5), ((0, 3), 5), ((0, 6), 7)])


def test_match_molecule_some_pair_shares_attribute():
    match = Molecule("SOME", _rel("focus.colour=target.colour"), "all_pairs")
    assert match.evaluate([((0, 1), 5), ((0, 3), 7), ((0, 6), 5)])[0] is True     # two 5s
    assert match.evaluate([((0, 1), 5), ((0, 3), 7), ((0, 6), 9)])[0] is False    # all distinct


def test_ground_prices_a_fitting_molecule():
    """The molecule is priced by the SAME MDL logic as flat atoms, one level up: a molecule whose degree tracks
    progress scores > 0; the space is quantifier x relation x pairing (typed, not a flat bag)."""
    order = Molecule("ALL", _rel("focus.col<target.col"), "consecutive")
    scene = [((0, 6), 5), ((0, 1), 5), ((0, 9), 5), ((0, 3), 5)]
    stream, progress = [], []
    for step in range(12):
        if step >= 6:
            scene = sorted(scene, key=lambda o: o[0][1])
        stream.append(list(scene)); progress.append(step >= 6)
    assert score_molecule(order, stream, progress) is not None
    assert len(enumerate_molecules(composed_relational_atoms())) > 0
