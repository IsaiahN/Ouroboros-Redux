"""
redux-arch P4.3: real-data guard for the replay harness on ls20 (the pixel-CONFIRMED clean maze). Pins the solid,
reproducible claim so it cannot silently regress: over the ls20 recordings on disk, the ONLY thing the affordance
minter ever mints is the colour-agnostic INTENDED_FREE, and at least one blocking-rich recording does mint it.
(tu93's current INTENDED_COLOUR==0 behaviour is documented in docs/, deliberately NOT pinned here -- its passable
basis is still noisy and is the next fix; pinning it would lock in an imperfect state.)
"""
import sys, os, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest
from newhorse.redux_arch.replay import replay_affordance

_LS20 = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "recordings", "*", "ls20-*.jsonl")))


@pytest.mark.skipif(not _LS20, reason="no ls20 recordings on disk")
def test_ls20_only_ever_mints_colour_agnostic_intended_free():
    any_mint = False
    for path in _LS20:
        res = replay_affordance(path, warmup=20, min_exceptions=15, min_hits=2, max_size=1)
        for name in res.minted_names:
            any_mint = True
            assert name == frozenset({"INTENDED_FREE"}), (os.path.basename(path), set(name))
    assert any_mint, "no ls20 recording produced an affordance mint -- expected at least one blocking-rich run"


@pytest.mark.skipif(not _LS20, reason="no ls20 recordings on disk")
def test_ls20_passable_is_the_green_floor():
    # the leak-free calibration must recover colour 3 (green) as passable on every ls20 run (pixel-confirmed).
    for path in _LS20:
        res = replay_affordance(path, warmup=20, min_exceptions=15, min_hits=2, max_size=1)
        assert res.cursor == 12, (os.path.basename(path), res.cursor)
        assert 3 in res.passable, (os.path.basename(path), set(res.passable))
