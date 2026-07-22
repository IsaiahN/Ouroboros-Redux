"""
redux-arch P3: ECHO -> PROMOTE. A minted predicate is admitted into Γ only after it recurs on a DIFFERENT task;
once promoted, Γ explains a new task's residual without re-minting (transfer, the self-modifying loop closing).
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.dsl import Context
from newhorse.redux_arch.minting import two_part_mdl
from newhorse.redux_arch.consolidate import Consolidator, _key


def _ctx(rng):
    fr, fc = rng.randint(0, 9), rng.randint(0, 9)
    colour = rng.choice([1, 2, 2, 3])
    vec = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)])
    if rng.random() < 0.5:
        dr, dc = rng.choice([(0, 0), (0, 1), (1, 0), (0, -1), (-1, 0)])
        tr, tc = max(0, min(9, fr + dr)), max(0, min(9, fc + dc))
    else:
        tr, tc = rng.randint(0, 9), rng.randint(0, 9)
    return Context((fr, fc), colour, (tr, tc), vec)


def _shared_rule(ctx):                                   # the regularity common to BOTH tasks
    near = abs(ctx.focus_rc[0] - ctx.target_rc[0]) + abs(ctx.focus_rc[1] - ctx.target_rc[1]) <= 1
    return ctx.focus_colour == 2 and near


def _exceptions(seed, n=100):
    rng = random.Random(seed)
    return [(c, _shared_rule(c)) for c in (_ctx(rng) for _ in range(n))]


def test_mint_on_one_task_does_not_promote():
    con = Consolidator(echo_threshold=2)
    m = two_part_mdl(_exceptions(10), max_size=2)
    assert m is not None
    promoted = con.observe_mint("gameA", m)
    assert promoted is False and con.library == []          # one task -> held, not yet echoed


def test_echo_on_second_task_promotes_into_gamma():
    con = Consolidator(echo_threshold=2)
    mA = two_part_mdl(_exceptions(10), max_size=2)          # task A discovers the sub-rule
    mB = two_part_mdl(_exceptions(20), max_size=2)          # task B (different scenes) discovers the SAME φ
    assert _key(mA.predicate) == _key(mB.predicate)         # they echo -- the regularity recurs
    assert con.observe_mint("gameA", mA) is False
    assert con.observe_mint("gameB", mB) is True            # second distinct task -> PROMOTE
    assert any(_key(p) == {"colour==2", "NEAR(focus,target)"} for p in con.library)


def test_promoted_gamma_explains_a_new_task_without_reminting():
    con = Consolidator(echo_threshold=2)
    con.observe_mint("gameA", two_part_mdl(_exceptions(10)))
    con.observe_mint("gameB", two_part_mdl(_exceptions(20)))
    assert con.library                                      # φ is in Γ now
    # a THIRD task with the same regularity: Γ already explains its residual -> no search / no re-mint
    third = _exceptions(30)
    pred = con.explains(third)
    assert pred is not None and _key(pred) == {"colour==2", "NEAR(focus,target)"}
