"""
redux-arch P2 correctness gate: residual-driven MDL minting on a SYNTHETIC known-answer task.

We PLANT a rule, hand the minter the residual exceptions, and verify it (a) recovers a predicate equivalent to
the planted one, (b) that predicate GENERALIZES to held-out before-states (a regularity, not memorization),
(c) mints NOTHING on random noise, and (d) cannot mint a tautology -- the DSL sees only the before-state, so
peeking at the outcome is not even constructible. This is the falsifiable core proven where we know the answer,
before it ever meets ARC noise (charter: synthetic-first as the correctness harness).
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.dsl import Context, make_atom, enumerate_predicates
from newhorse.redux_arch.minting import two_part_mdl, MintingEngine


def _rand_ctx(rng: random.Random) -> Context:
    fr, fc = rng.randint(0, 9), rng.randint(0, 9)
    colour = rng.choice([1, 2, 2, 3])                    # colour 2 ~50% so both classes populate
    vec = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)])
    if rng.random() < 0.5:                               # ~half the time place the target NEAR the focus
        dr, dc = rng.choice([(0, 0), (0, 1), (1, 0), (0, -1), (-1, 0)])
        tr, tc = max(0, min(9, fr + dr)), max(0, min(9, fc + dc))
    else:
        tr, tc = rng.randint(0, 9), rng.randint(0, 9)
    return Context(focus_rc=(fr, fc), focus_colour=colour, target_rc=(tr, tc), action_vec=vec)


def _planted(ctx: Context) -> bool:
    # the hidden rule: success iff the focus is colour 2 AND within distance 1 of the target (NEAR)
    near = abs(ctx.focus_rc[0] - ctx.target_rc[0]) + abs(ctx.focus_rc[1] - ctx.target_rc[1]) <= 1
    return ctx.focus_colour == 2 and near


def _dataset(rng, n, label):
    return [(c, label(c)) for c in (_rand_ctx(rng) for _ in range(n))]


def test_minter_recovers_the_planted_rule():
    rng = random.Random(0)
    # bias sampling so both classes are populated (a residual list, not a degenerate one)
    exceptions = []
    while len(exceptions) < 80:
        c = _rand_ctx(rng)
        exceptions.append((c, _planted(c)))
    assert 0 < sum(o for _, o in exceptions) < len(exceptions)      # genuinely mixed outcomes

    mint = two_part_mdl(exceptions, max_size=2)
    assert mint is not None, "minter failed to compress a real rule"
    assert mint.saved_bits > 0
    names = {a.name for a in mint.predicate.atoms}
    assert names == {"colour==2", "NEAR(focus,target)"}, names       # recovered EXACTLY the planted conjunction


def test_minted_predicate_generalizes_to_heldout():
    rng = random.Random(1)
    train = [(c, _planted(c)) for c in (_rand_ctx(rng) for _ in range(120))]
    mint = two_part_mdl(train, max_size=2)
    assert mint is not None
    held = [_rand_ctx(rng) for _ in range(200)]
    # a regularity, not memorization: φ on unseen before-states matches the planted rule exactly
    assert all(mint.predicate.holds(c) == _planted(c) for c in held)


def test_noise_mints_nothing():
    rng = random.Random(2)
    noise = [(_rand_ctx(rng), rng.random() < 0.5) for _ in range(120)]   # outcome independent of the before-state
    assert two_part_mdl(noise, max_size=2) is None                    # MDL cost rejects a chance split


def test_tautology_is_unconstructible_by_type():
    # the DSL's Context exposes ONLY before-state fields -- no 'after'/'outcome' accessor exists, so a predicate
    # that peeks at the result cannot be built. The tautology guard is a TYPE property, not a remembered rule.
    fields = set(Context.__dataclass_fields__)
    assert "after" not in fields and "outcome" not in fields and "result" not in fields
    # and an ill-typed atom is refused at construction (type-directed pruning is real)
    try:
        make_atom("HAS_COLOUR", "not-a-colour")
        assert False, "ill-typed atom was accepted"
    except TypeError:
        pass


def test_engine_buffers_and_mints():
    rng = random.Random(3)
    eng = MintingEngine(min_exceptions=40, max_size=2)
    assert eng.maybe_mint() is None                                   # below threshold -> no premature mint
    for _ in range(60):
        c = _rand_ctx(rng)
        eng.observe(c, _planted(c))
    mint = eng.maybe_mint()
    assert mint is not None and eng.minted
    assert {a.name for a in mint.predicate.atoms} == {"colour==2", "NEAR(focus,target)"}
