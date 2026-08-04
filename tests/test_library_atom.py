"""
C21.15 Stage 0 gate: A PROMOTED φ CAN BE A CONJUNCT, AND COSTS WHAT IT COSTS.

Until this beat the minter's search space was a pure function of the PALETTE -- `atom_universe` read `colours`
and nothing else -- so a φ promoted into Γ was TERMINAL: applicable (via `explains_scored` / `directives`) but
never EXTENDABLE. `library_atom` wraps a promoted φ as one atom so the next mint can compose WITH it.

What these tests pin, in order of what would hurt most if it broke:

 1. THE DEFAULT IS THE OLD BEHAVIOUR, EXACTLY. `library=()` must reproduce the pre-C21.15 universe and the
    pre-C21.15 search space element-for-element. Stage 0 is a shadow; if the default path moved, every number
    already on the record moved with it and the beat is void before it starts.
 2. FAMILY AND MOTION ARE INHERITED, NOT RE-DERIVED. A library atom is charged to the family of the φ it wraps
    and reports that φ's motion-reading. A wrapper that reported `unregistered` would poison `predicate_family`;
    one that reported motion-free while wrapping ACTS_TOWARD would walk a motion-reading predicate through a
    motion-free gate. Both are read off `Atom.source`, a RECORD, never parsed back out of the name.
 3. NO RE-USE DISCOUNT. A library atom costs its constituents' cost. A discount here would be a lowered
    promotion bar wearing a compression costume, and any win bought by it would be unattributable.
 4. NO DUPLICATES. A library φ whose rendered name already names a base atom is dropped -- re-offering an atom
    the universe already holds is not composition, it is the same hypothesis counted twice in `selection_cost`.
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.dsl import (Context, Predicate, make_atom, library_atom, atom_universe,
                                     enumerate_predicates, atom_family, predicate_family, reads_motion,
                                     LIB_ATOM_KIND)
from newhorse.redux_arch.minting import two_part_mdl

COLOURS = [1, 2, 3]


def _ctx(fr, fc, colour, tr, tc, vec=(0, 0)):
    return Context(focus_rc=(fr, fc), focus_colour=colour, target_rc=(tr, tc), action_vec=vec)


# ---- 1. the default path is untouched ----------------------------------------------------------------------

def test_empty_library_reproduces_todays_universe_exactly():
    base = atom_universe(COLOURS)
    assert [a.name for a in atom_universe(COLOURS, library=())] == [a.name for a in base]
    assert [a.name for a in atom_universe(COLOURS, library=[])] == [a.name for a in base]


def test_empty_library_reproduces_todays_search_space_exactly():
    base = enumerate_predicates(COLOURS, max_size=2)
    withlib = enumerate_predicates(COLOURS, max_size=2, library=())
    assert [str(p) for p in withlib] == [str(p) for p in base]


def test_empty_library_leaves_the_mdl_score_unchanged():
    """The gate that matters for Stage 0: an empty library is not merely a smaller space, it is the SAME
    decision. Same argmax, same bits, same accounting -- otherwise the shadow's `differs` field is measuring
    the plumbing rather than the library."""
    rng = random.Random(7)
    exc = []
    for _ in range(40):
        c = _ctx(rng.randint(0, 9), rng.randint(0, 9), rng.choice([1, 2, 2, 3]),
                 rng.randint(0, 9), rng.randint(0, 9))
        exc.append((c, c.focus_colour == 2))
    ra, rb = {}, {}
    a = two_part_mdl(exc, max_size=2, report=ra)
    b = two_part_mdl(exc, max_size=2, report=rb, library=())
    assert (a is None) == (b is None)
    if a is not None:
        assert str(a.predicate) == str(b.predicate)
        assert abs(a.saved_bits - b.saved_bits) < 1e-12
    assert ra == rb
    assert "n_eligible_library" not in ra          # absent means "no library offered" -- distinct from a 0


# ---- 2. family and motion are inherited from the source φ --------------------------------------------------

def test_library_atom_inherits_family():
    colour_phi = Predicate(frozenset({make_atom("HAS_COLOUR", 2)}))
    rel_phi = Predicate(frozenset({make_atom("NEAR")}))
    both_phi = Predicate(frozenset({make_atom("HAS_COLOUR", 2), make_atom("NEAR")}))
    assert atom_family(library_atom(colour_phi)) == "colour"
    assert atom_family(library_atom(rel_phi)) == "relational"
    assert atom_family(library_atom(both_phi)) == "both"
    # ...and a predicate holding one library atom is charged the same way
    assert predicate_family(Predicate(frozenset({library_atom(colour_phi)}))) == "colour"
    assert predicate_family(Predicate(frozenset({library_atom(both_phi)}))) == "both"
    # a colour φ conjoined with a relational library atom spans both families
    assert predicate_family(Predicate(frozenset({make_atom("HAS_COLOUR", 1),
                                                 library_atom(rel_phi)}))) == "both"


def test_library_atom_is_never_unregistered():
    """The failure this guards: `atom_family` falls through to 'unregistered' for any kind outside the registry,
    and LIB is outside the registry by design. A library atom charged 'unregistered' would make every predicate
    containing it 'unregistered' -- a wiring fault indistinguishable from a real one."""
    lib = library_atom(Predicate(frozenset({make_atom("TOUCH")})))
    assert lib.kind == LIB_ATOM_KIND
    assert atom_family(lib) != "unregistered"


def test_library_atom_inherits_motion_reading():
    motion_phi = Predicate(frozenset({make_atom("ACTS_TOWARD")}))
    still_phi = Predicate(frozenset({make_atom("NEAR")}))
    assert reads_motion(Predicate(frozenset({library_atom(motion_phi)}))) is True
    assert reads_motion(Predicate(frozenset({library_atom(still_phi)}))) is False
    # and the inheritance survives being conjoined with a motion-free atom
    assert reads_motion(Predicate(frozenset({library_atom(motion_phi), make_atom("NEAR")}))) is True


# ---- 3. price ----------------------------------------------------------------------------------------------

def test_library_atom_carries_no_reuse_discount():
    phi = Predicate(frozenset({make_atom("HAS_COLOUR", 2), make_atom("NEAR")}))
    assert library_atom(phi).cost == phi.cost() == 5      # 3 (colour literal) + 2 (relational)
    # the wrapped φ is not cheaper as a conjunct than it was as a predicate
    assert Predicate(frozenset({library_atom(phi)})).cost() == phi.cost()


def test_library_atom_evaluates_as_its_source():
    phi = Predicate(frozenset({make_atom("HAS_COLOUR", 2), make_atom("NEAR")}))
    lib = library_atom(phi)
    for ctx in (_ctx(0, 0, 2, 0, 1), _ctx(0, 0, 3, 0, 1), _ctx(0, 0, 2, 5, 5)):
        assert lib.holds(ctx) == phi.holds(ctx)


def test_the_vacuous_predicate_is_not_a_vocabulary_item():
    import pytest
    with pytest.raises(TypeError):
        library_atom(Predicate(frozenset()))


# ---- 4. the universe grows by exactly what was offered, and no duplicates ----------------------------------

def test_library_grows_the_universe_by_one_atom_per_novel_phi():
    base = atom_universe(COLOURS)
    phi = Predicate(frozenset({make_atom("HAS_COLOUR", 2), make_atom("NEAR")}))
    grown = atom_universe(COLOURS, library=[phi])
    assert len(grown) == len(base) + 1
    assert [a.name for a in grown[:len(base)]] == [a.name for a in base]   # appended, never re-ordered
    assert grown[-1].kind == LIB_ATOM_KIND


def test_a_library_phi_that_already_names_a_base_atom_is_dropped():
    """A promoted single-atom φ renders to the same name as the base atom it is made of. Admitting it would put
    the identical hypothesis in the pool twice, inflating `selection_cost` against every real candidate."""
    base = atom_universe(COLOURS)
    dup = Predicate(frozenset({make_atom("NEAR")}))
    assert [a.name for a in atom_universe(COLOURS, library=[dup])] == [a.name for a in base]
    # ...and a repeated offer of the SAME novel φ is admitted once
    phi = Predicate(frozenset({make_atom("HAS_COLOUR", 2), make_atom("NEAR")}))
    assert len(atom_universe(COLOURS, library=[phi, phi])) == len(base) + 1


def test_library_raises_n_eligible_and_is_counted_separately():
    """The library pays for its own size in the same currency as everything else: more candidates -> a higher
    `selection_cost`. `n_eligible_library` is the denominator that says whether Γ REACHED the contest at all --
    a Γ that is offered but constant across these contexts is filtered out and would otherwise leave no trace."""
    rng = random.Random(11)
    exc = []
    for _ in range(40):
        c = _ctx(rng.randint(0, 9), rng.randint(0, 9), rng.choice([1, 2, 2, 3]),
                 rng.randint(0, 9), rng.randint(0, 9))
        exc.append((c, c.focus_colour == 2))
    phi = Predicate(frozenset({make_atom("HAS_COLOUR", 2), make_atom("NEAR")}))
    ra, rb = {}, {}
    two_part_mdl(exc, max_size=2, report=ra)
    two_part_mdl(exc, max_size=2, report=rb, library=[phi])
    assert rb["n_constructed"] > ra["n_constructed"]
    assert rb["n_eligible"] >= ra["n_eligible"]
    assert rb["selection_cost_bits"] >= ra["selection_cost_bits"]
    assert rb["n_eligible_library"] >= 1
    assert rb["n_eligible_library"] <= rb["n_eligible"]


def test_a_library_phi_can_win_the_argmax_when_it_is_the_rule():
    """The mechanism, proven where the answer is known: plant a rule the BASE vocabulary can only express as a
    2-conjunction, then offer that same conjunction as ONE library atom and make the true rule a THREE-atom
    thing (the library φ AND a colour literal) -- outside `max_size=2` in the base space, inside it once the
    library φ is a single conjunct. If this fails, the wire is decorative."""
    rng = random.Random(3)
    exc = []
    for _ in range(120):
        fr, fc = rng.randint(0, 9), rng.randint(0, 9)
        colour = rng.choice([1, 2])
        near = rng.random() < 0.5
        if near:
            tr, tc = fr, min(9, fc + 1)
        else:
            tr, tc = (fr + 5) % 10, (fc + 5) % 10
        icol = rng.choice([1, 3])
        c = Context(focus_rc=(fr, fc), focus_colour=colour, target_rc=(tr, tc), action_vec=(0, 0),
                    intended_colour=icol)
        # the planted rule: (colour==2 AND NEAR) AND intended_colour==3  -- three atoms
        planted = (colour == 2 and abs(fr - tr) + abs(fc - tc) <= 1 and icol == 3)
        exc.append((c, planted))
    phi = Predicate(frozenset({make_atom("HAS_COLOUR", 2), make_atom("NEAR")}))
    with_lib = two_part_mdl(exc, max_size=2, library=[phi])
    assert with_lib is not None
    assert any(a.kind == LIB_ATOM_KIND for a in with_lib.predicate.atoms), str(with_lib.predicate)
    base = two_part_mdl(exc, max_size=2)
    # the library mint is a STRICTLY better compression, at no price break -- not merely a different one
    assert base is None or with_lib.saved_bits > base.saved_bits
