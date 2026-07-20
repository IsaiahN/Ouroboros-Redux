"""Tests for the typed grammar. Pins 'typing beats size' + type-checked composition."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.grammar import (T, PRIMES, KANT_CATEGORIES, compose, Term, TypeError_,
                              is_objective, MOLECULES, count_typed_objectives, count_flat_bag)


def test_prime_basis_is_kant_organised_and_typed():
    assert set(KANT_CATEGORIES) >= {"Quantity", "Quality", "Relation", "Modality"}
    for p in PRIMES.values():                      # every prime carries a type signature (that is what TYPED means)
        assert isinstance(p.out_type, T) and all(isinstance(t, T) for t in p.in_types)


def test_composition_type_checks():
    # BE_AT : (OBJECT, REGION) -> PRED ; ALL : (PRED,) -> OBJ
    pred = compose("BE_AT", T.OBJECT, T.REGION)
    assert pred.type is T.PRED
    obj = compose("ALL", pred)
    assert obj.type is T.OBJ and is_objective(obj)


def test_ill_typed_composition_raises_not_silent():
    # feeding an OBJECT where a PRED is required must RAISE with a reason (nothing silent)
    try:
        compose("ALL", T.OBJECT)                    # ALL expects a PRED, got an OBJECT
        assert False, "should have raised"
    except TypeError_ as e:
        assert "ill-typed" in str(e) and "ALL" in str(e)
    try:
        compose("BE_AT", T.OBJECT, T.OBJECT)        # BE_AT expects (OBJECT, REGION)
        assert False
    except TypeError_:
        pass


def test_molecules_are_well_typed_objectives():
    for name, term in MOLECULES.items():
        assert isinstance(term, Term) and term.type is T.OBJ, name


def test_typing_beats_size():
    # THE load-bearing property (B1a): the type-valid objective space is DRAMATICALLY smaller than a flat V^k bag.
    for depth in (2, 3):
        typed = count_typed_objectives(depth)
        flat = count_flat_bag(depth)
        assert typed >= 1
        assert typed < flat / 10, "typing must shrink the search space by >10x at depth %d (typed=%d flat=%d)" % (
            depth, typed, flat)


def test_typed_space_grows_but_stays_bounded():
    # it GROWS with depth (covers more objectives) yet stays far below exponential -> grows without the branching cost
    d2 = count_typed_objectives(2)
    d3 = count_typed_objectives(3)
    assert d3 >= d2 >= 1
    assert d3 < count_flat_bag(3)


def test_encodes_no_answer():
    # the grammar is a basis + a typed search procedure; it names no game-specific solution.
    # molecules are generic (MATCH/REACH/CLEAR), built from primes, not from any board's answer.
    assert set(MOLECULES) == {"MATCH", "REACH", "CLEAR"}
    for term in MOLECULES.values():
        assert all(a in (T.OBJECT, T.ATTR, T.REGION) or isinstance(a, Term)
                   for a in term.args)               # leaves are TYPE HOLES, not concrete board values
