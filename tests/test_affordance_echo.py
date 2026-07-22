"""
redux-arch P4.3 (mechanism gate): does an AFFORDANCE predicate survive the ECHO->PROMOTE path?

P3 proved ECHO->PROMOTE for a NAVIGATION predicate (colour==2 AND NEAR). Before spending a live beat rendering two
ARC mazes (P4.3 proper), charter guard #3 ("echo-before-promote") and guard #4 ("prove the minter where
perception is clean") demand the affordance predicate be shown flowing through the SAME consolidation path on a
known-answer curriculum. This file is that offline gate.

It also pins the design lesson the live runs already hinted at: tu93 minted INTENDED_COLOUR==5 and ls20 minted
INTENDED_COLOUR==3 -- PALETTE-SPECIFIC atoms. Those do NOT echo across mazes with different colourings; the
transferable abstraction is INTENDED_FREE (colour-agnostic passability). So:
  - the colour-agnostic affordance (INTENDED_FREE) SHOULD echo across two mazes and promote (transfer);
  - a colour-specific affordance (INTENDED_COLOUR==c) with different palettes must NOT falsely promote -- proving
    the echo guard is load-bearing, not vacuous.
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.dsl import Context
from newhorse.redux_arch.minting import two_part_mdl
from newhorse.redux_arch.consolidate import Consolidator, _key


def _free_maze(seed, focus_palette, wall_palette, n=140):
    """A maze whose move SUCCEEDS iff the cell ahead is background (colour 0). moved == intended_free, with the
    focus/wall colours drawn from a task-specific palette so nothing but passability correlates with the label."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        free = rng.random() < 0.5
        ahead = 0 if free else rng.choice(wall_palette)
        ctx = Context(focus_rc=(rng.randint(0, 9), rng.randint(0, 9)),
                      focus_colour=rng.choice(focus_palette),
                      target_rc=(rng.randint(0, 9), rng.randint(0, 9)),
                      action_vec=rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)]),
                      intended_free=free, intended_colour=ahead)
        out.append((ctx, free))               # moved iff the cell ahead is free
    return out


def _colour_gated_maze(seed, passable_colour, other_colours, n=160):
    """A maze whose move SUCCEEDS iff the cell ahead is a SPECIFIC passable colour (not background). intended_free
    is deliberately mis-set to (ahead==0) -- i.e. the naive 'free==background' read is WRONG here -- so the only
    clean predictor is INTENDED_COLOUR==passable_colour. This mirrors the live runs where the minter discovered
    the true passable colour from the residual instead of trusting a hardcoded background."""
    rng = random.Random(seed)
    palette = [passable_colour] + list(other_colours)
    out = []
    for _ in range(n):
        ahead = rng.choice(palette)
        moved = (ahead == passable_colour)
        ctx = Context(focus_rc=(rng.randint(0, 9), rng.randint(0, 9)), focus_colour=4,
                      target_rc=(rng.randint(0, 9), rng.randint(0, 9)), action_vec=(0, 1),
                      intended_free=(ahead == 0), intended_colour=ahead)
        out.append((ctx, moved))
    return out


def test_colour_agnostic_affordance_echoes_and_promotes_across_two_mazes():
    # two DIFFERENT mazes (different focus/wall palettes) that share the SAME hidden rule: move iff ahead is free.
    exA = _free_maze(seed=10, focus_palette=[1, 4], wall_palette=[5, 6])
    exB = _free_maze(seed=20, focus_palette=[2, 8], wall_palette=[5, 7])
    mA = two_part_mdl(exA, max_size=1)
    mB = two_part_mdl(exB, max_size=1)
    assert mA is not None and mB is not None
    assert {a.name for a in mA.predicate.atoms} == {"INTENDED_FREE"}, mA.predicate
    assert _key(mA.predicate) == _key(mB.predicate), "the affordance did not echo across the two mazes"

    con = Consolidator(echo_threshold=2)
    assert con.observe_mint("mazeA", mA) is False            # one task -> held
    assert con.observe_mint("mazeB", mB) is True             # second distinct task -> PROMOTE into Γ
    assert any(_key(p) == frozenset({"INTENDED_FREE"}) for p in con.library)

    # transfer: a THIRD maze's blocking residual is now explained by Γ WITHOUT re-minting.
    exC = _free_maze(seed=30, focus_palette=[3, 9], wall_palette=[5, 6])
    pred = con.explains(exC)
    assert pred is not None and _key(pred) == frozenset({"INTENDED_FREE"})


def test_palette_specific_affordance_does_not_falsely_promote():
    # honest guard: colour-SPECIFIC affordances (the tu93/ls20 case) must NOT echo across differently-coloured
    # mazes -- INTENDED_COLOUR==3 and INTENDED_COLOUR==7 are different predicates, so the echo guard holds them.
    mA = two_part_mdl(_colour_gated_maze(seed=11, passable_colour=3, other_colours=[5, 6]), max_size=1)
    mB = two_part_mdl(_colour_gated_maze(seed=21, passable_colour=7, other_colours=[2, 5]), max_size=1)
    assert mA is not None and mB is not None
    assert {a.name for a in mA.predicate.atoms} == {"INTENDED_COLOUR==3"}, mA.predicate
    assert {a.name for a in mB.predicate.atoms} == {"INTENDED_COLOUR==7"}, mB.predicate
    assert _key(mA.predicate) != _key(mB.predicate)          # different palettes -> different predicates

    con = Consolidator(echo_threshold=2)
    assert con.observe_mint("mazeA", mA) is False
    assert con.observe_mint("mazeB", mB) is False            # NOT an echo -> correctly NOT promoted
    assert con.library == []                                 # the guard is load-bearing, not vacuous
