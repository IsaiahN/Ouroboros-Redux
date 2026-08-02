"""The market arbiter's covariance discount, and an end-to-end smoke of the two-scale loop."""
from nexus.kernel import make_atom, Predicate
from nexus.population.credibility import CredibilityDB
from nexus.population.loop import run_curriculum
from nexus.proposer.enumerate import EnumerationProposer
from nexus.ground.rlvr import make_curriculum


def test_covariance_discount_prices_redundancy_down():
    db = CredibilityDB(lam=0.5)
    solo = db.market_value(0.9, redundancy=1, n_roles=4)         # nobody else proposed it
    crowd = db.market_value(0.9, redundancy=4, n_roles=4)        # the whole population co-proposed it
    assert crowd < solo                                          # correlated proposals priced lower


def test_promotion_enters_shared_gamma_only_via_promote():
    db = CredibilityDB()
    p = Predicate(frozenset({make_atom("TOUCH")}))
    assert db.shared_gamma() == {}
    db.vote(str(p), 1.0, 1, 4)                                   # voting alone never promotes
    assert db.shared_gamma() == {}
    db.promote(str(p), p)
    assert str(p) in db.shared_gamma()


def test_loop_runs_end_to_end_and_solves_something():
    palette = [1, 2]
    cur = make_curriculum(palette)
    res = run_curriculum(cur, EnumerationProposer(palette), use_db=True, k=16, max_rounds=6)
    assert res["solved"] >= 1                                    # the wiring produces verified solutions
    assert isinstance(res["gamma"], list)
