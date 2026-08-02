"""The mined hardening: CUSUM fires on a PERSISTENT shift (not a spike), credibility DECAYS on the
clock (anti-incumbency), and a detected regime change discounts incumbents."""
from nexus.population.regime import Cusum
from nexus.population.credibility import CredibilityDB


def test_cusum_ignores_a_spike_but_fires_on_a_sustained_shift():
    c = Cusum(warmup=4)                   # default threshold sits above any single-step deviation
    for _ in range(10):
        assert not c.update(0.8)          # steady high -> no fire
    assert not c.update(0.1)              # a single dip is a flicker, not a regime change
    fired = any(c.update(0.1) for _ in range(12))   # but a sustained drop does fire
    assert fired and c.ever_fired


def test_clock_decay_unseats_a_stale_incumbent():
    db = CredibilityDB(half_life_rounds=3)
    db.vote("p", ground_score=1.0, redundancy=1, n_roles=4)   # earns standing
    hi = db.cred["p"]
    for _ in range(9):                    # 9 rounds pass; it is never re-voted (stale)
        db.tick()
    assert db.cred["p"] < 0.2 * hi        # ~3 half-lives -> standing has faded (was frozen before the mine)


def test_regime_change_discounts_incumbents_at_once():
    db = CredibilityDB(regime_discount=0.5)
    db.vote("p", 1.0, 1, 4)
    before = db.cred["p"]
    for _ in range(6):
        db.note_round(0.9)                # establish the baseline
    fired = any(db.note_round(0.05) for _ in range(12))   # success collapses -> regime change
    assert fired and db.regime_changes >= 1
    assert db.cred["p"] < before          # the incumbent, earned on the old regime, is discounted
