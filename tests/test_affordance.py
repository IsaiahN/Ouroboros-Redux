"""
redux-arch P4 (novel aim): mint an AFFORDANCE predicate from the grammar's PREDICTION-ERROR residual.

Where the navigation-progress residual could only ever be compressed by ACTS_TOWARD (already in the kernel), the
prediction-error residual -- "did the cursor MOVE as Γ predicted, or was it blocked?" -- is compressed by a
DIFFERENT predicate the navigation kernel lacked: INTENDED_FREE (the cell I'd enter is free -> I CAN move). This
is the point of residual-driven minting: change the AIM, and the minter invents a categorically new predicate,
not a re-derivation.
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.dsl import Context
from newhorse.redux_arch.minting import two_part_mdl


def _ctx(rng, intended_free, moved_helpers=True):
    # target/focus/action are irrelevant to the blocking label -- randomize them so ACTS_TOWARD can't sneak in
    fr, fc = rng.randint(0, 9), rng.randint(0, 9)
    tr, tc = rng.randint(0, 9), rng.randint(0, 9)
    vec = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
    icol = 0 if intended_free else rng.choice([2, 3, 5])   # a wall colour if occupied
    return Context(focus_rc=(fr, fc), focus_colour=rng.choice([1, 4]), target_rc=(tr, tc), action_vec=vec,
                   intended_free=intended_free, intended_colour=icol)


def test_minter_invents_the_affordance_predicate_from_prediction_error():
    rng = random.Random(0)
    # the maze rule: a move SUCCEEDS iff the cell ahead is free (walls block). Label = moved (== intended_free).
    exceptions = []
    for _ in range(120):
        free = rng.random() < 0.5
        exceptions.append((_ctx(rng, free), free))         # moved == intended_free
    mint = two_part_mdl(exceptions, max_size=2)
    assert mint is not None, "failed to compress the blocking residual"
    names = {a.name for a in mint.predicate.atoms}
    # the WINNING predicate is the affordance INTENDED_FREE -- NOT the navigation atom ACTS_TOWARD
    assert names == {"INTENDED_FREE"}, names


def test_navigation_atom_does_not_explain_blocking():
    # sanity: ACTS_TOWARD is uncorrelated with blocking here (target randomized), so a nav-only DSL could not
    # have minted this -- the new atom is doing real work, not decoration.
    rng = random.Random(1)
    exceptions = [(_ctx(rng, f), f) for f in (rng.random() < 0.5 for _ in range(120))]
    mint = two_part_mdl(exceptions, max_size=1)
    assert mint is not None and {a.name for a in mint.predicate.atoms} == {"INTENDED_FREE"}


def test_colour_gated_block_mints_the_occupying_colour():
    # a colour-GATED affordance: only colour-2 walls block; colour-7 items are passable. moved == (ahead is NOT 2).
    # with a size-1 search the best single atom that predicts NON-blocking is INTENDED_FREE (covers the free case);
    # but INTENDED_COLOUR==2 predicts BLOCKING purely -> the minter should find one of the occupancy atoms, never
    # a navigation atom. (Full NOT/disjunction is future DSL work; here we assert an OCCUPANCY atom wins.)
    rng = random.Random(2)
    exceptions = []
    for _ in range(160):
        ahead = rng.choice([0, 0, 2, 7])                   # 0 free, 2 wall, 7 item
        ctx = Context(focus_rc=(rng.randint(0, 9), rng.randint(0, 9)), focus_colour=4,
                      target_rc=(rng.randint(0, 9), rng.randint(0, 9)), action_vec=(0, 1),
                      intended_free=(ahead == 0), intended_colour=ahead)
        moved = (ahead != 2)                               # blocked only by walls
        exceptions.append((ctx, moved))
    mint = two_part_mdl(exceptions, max_size=1)
    assert mint is not None
    name = next(iter(mint.predicate.atoms)).name
    assert name.startswith("INTENDED_"), name              # an occupancy predicate, not navigation
