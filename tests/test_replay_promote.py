"""
redux-arch P4.3 -- THE LIVE JOIN: fail -> mint -> ECHO -> PROMOTE across two REAL ARC maze games.

ls20 (passable green=3) and tu93 (passable black=0) are DIFFERENT games with DIFFERENT palettes. From each game's
own recorded prediction-error residual the calibrated minter mints the SAME colour-agnostic predicate
INTENDED_FREE (leak-free: passability learned from the cursor's actual trajectory, minting on held-out steps).
Because the predicate is colour-agnostic it ECHOes across the two games -> the Consolidator PROMOTES it into Γ ->
Γ then explains a THIRD (held-out) maze residual WITHOUT re-minting. That is Region III filled end-to-end on real
frames: the first predicate the navigation kernel lacked, minted and consolidated from actual ARC play.
"""
import sys, os, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest
from newhorse.redux_arch.replay import replay_affordance
from newhorse.redux_arch.consolidate import Consolidator, _key

_REC = os.path.join(os.path.dirname(__file__), "..", "recordings")
INTENDED_FREE = frozenset({"INTENDED_FREE"})


def _recs(game):
    return sorted(glob.glob(os.path.join(_REC, "*", "%s-*.jsonl" % game)))


def _first_intended_free(paths):
    """Return (path, Mint, exceptions) for the first recording that mints INTENDED_FREE."""
    for p in paths:
        res = replay_affordance(p, warmup=20, min_exceptions=15, min_hits=2, max_size=1)
        for m in res.engine.minted:
            if _key(m.predicate) == INTENDED_FREE:
                return p, m, list(res.engine.buffer)
    return None, None, None


@pytest.mark.skipif(not _recs("ls20") or not _recs("tu93"), reason="need ls20 and tu93 recordings")
def test_intended_free_echoes_across_two_real_games_and_promotes():
    ls_path, ls_mint, _ = _first_intended_free(_recs("ls20"))
    tu_path, tu_mint, _ = _first_intended_free(_recs("tu93"))
    assert ls_mint is not None, "ls20 did not mint INTENDED_FREE from any recording"
    assert tu_mint is not None, "tu93 did not mint INTENDED_FREE from any recording"

    con = Consolidator(echo_threshold=2)
    assert con.observe_mint("ls20", ls_mint) is False        # one game -> held (not yet echoed)
    assert con.observe_mint("tu93", tu_mint) is True         # a DIFFERENT game echoes it -> PROMOTE into Γ
    assert any(_key(p) == INTENDED_FREE for p in con.library)

    # transfer: a THIRD, held-out recording with a GENUINE blocking residual (not a near-free run) is explained
    # by Γ WITHOUT re-minting. Require a real moved/blocked mix so INTENDED_FREE has both sub-streams to compress.
    used = {ls_path, tu_path}
    third_exc = None
    for p in _recs("ls20") + _recs("tu93"):
        if p in used:
            continue
        res = replay_affordance(p, warmup=20, min_exceptions=15, min_hits=2, max_size=1)
        if res.moved >= 5 and res.blocked >= 5:              # a wall-bumping run, not a free stroll
            third_exc = list(res.engine.buffer)
            break
    assert third_exc is not None, "no held-out recording with a blocking residual to test transfer"
    pred = con.explains(third_exc)
    assert pred is not None and _key(pred) == INTENDED_FREE   # Γ already accounts for it -> no re-mint needed
