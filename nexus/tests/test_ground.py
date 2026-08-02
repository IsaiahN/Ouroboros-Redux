"""The ground: verifiable (computed from data) and UNPERSUADABLE (a pure function of the candidate,
independent of who proposes or what the population believes)."""
from nexus.kernel import make_atom, Predicate
from nexus.ground.rlvr import SyntheticGround, Level


def _ground():
    target = Predicate(frozenset({make_atom("HAS_COLOUR", 1)}))
    return SyntheticGround(Level("t", target, [1, 2]), n=600, seed=0)


def test_target_scores_perfect_constant_scores_chance():
    g = _ground()
    assert g.score(g.level.target) == 1.0
    assert g.solved(g.level.target)
    # the vacuously-true predicate cannot win: balanced accuracy floors it at ~0.5 (Goodhart guard)
    always_true = Predicate(frozenset())
    assert abs(g.score(always_true) - 0.5) < 0.15
    assert not g.solved(always_true)


def test_unpersuadable_score_is_a_pure_function_of_the_candidate():
    g = _ground()
    wrong = Predicate(frozenset({make_atom("HAS_COLOUR", 2)}))
    s1 = g.score(wrong)
    # nothing about credibility, proposer, or repetition can move it -- there is no channel to
    for _ in range(5):
        assert g.score(wrong) == s1                      # deterministic, identity-independent
    assert not g.solved(wrong)
