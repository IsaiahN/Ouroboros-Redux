"""Tests for the two-stream architecture + the pose, incl. the map's I2a falsifier (Appendix E.3)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.two_streams import Pose


def test_decide_is_convex_blend():
    p = Pose(alpha=0.5)
    assert p.decide(private=10.0, social=0.0) == 5.0
    p.alpha = 1.0
    assert p.decide(10.0, 0.0) == 10.0          # all private
    p.alpha = 0.0
    assert p.decide(10.0, 0.0) == 0.0           # all social


def test_alpha_learns_toward_the_better_stream():
    # private stream consistently predicts better -> alpha rises toward trusting private
    p = Pose(alpha=0.5)
    for _ in range(20):
        p.learn(private_error=0.1, social_error=0.9)
    assert p.alpha > 0.6
    # social consistently better -> alpha falls
    q = Pose(alpha=0.5)
    for _ in range(20):
        q.learn(private_error=0.9, social_error=0.1)
    assert q.alpha < 0.4


def test_alpha_stays_bounded():
    p = Pose(alpha=0.5, lr0=5.0)
    for _ in range(50):
        p.learn(private_error=0.0, social_error=1.0)
    assert 0.0 <= p.alpha <= 1.0


def test_i2a_falsifier_divergent_order_diverges_alpha():
    # THE MAP'S OWN FALSIFIER (I2a / E.3): identical architecture, SAME set of encounters in DIFFERENT
    # ORDER -> alpha DIVERGES. If it did not, non-identity would be just noise and the pose mechanism false.
    encounters = [(0.1, 0.9), (0.9, 0.1), (0.2, 0.8), (0.8, 0.2), (0.05, 0.95)]
    a = Pose(); b = Pose()
    for e in encounters:
        a.learn(*e)
    for e in reversed(encounters):
        b.learn(*e)
    assert abs(a.alpha - b.alpha) > 1e-3        # order changed the pose -> the mechanism holds
    # and the behaviour diverges too (different alpha -> different decision)
    assert a.decide(1.0, 0.0) != b.decide(1.0, 0.0)


def test_same_order_is_deterministic_control():
    # control: SAME order -> SAME alpha (so the divergence above is really from order, not randomness).
    encounters = [(0.1, 0.9), (0.9, 0.1), (0.2, 0.8)]
    a = Pose(); b = Pose()
    for e in encounters:
        a.learn(*e)
    for e in encounters:
        b.learn(*e)
    assert a.alpha == b.alpha


def test_pose_is_alpha_plus_history():
    p = Pose()
    p.learn(0.1, 0.9)
    assert len(p.history) == 1 and 0.0 <= p.alpha <= 1.0     # the pose = (alpha, encounter history)


def test_nothing_silent():
    p = Pose()
    p.learn(0.1, 0.9)
    assert any(e.startswith("WEIGHT") for e in p.log)
