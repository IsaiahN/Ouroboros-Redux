"""
test_sweep_denominator.py -- A CRASHED GAME IS NOT A GAME THAT REACHED LEVEL 0.

Found by reading the sweep that first fired the tether, not by a test. The pooled block printed:

    "games_reporting": 24,
    "max_level_histogram": {"0": 22, "1": 3}

24 and 25. One game (`g50t-5849a774`) failed to open its session, so it returned `family="error", levels=0` and no
`tether_stage` -- and then fell into the level histogram as a level-0 game. The sweep therefore reported a game that
never played as a game that played and got nowhere, in the very histogram used to argue that the agent is stuck at
level 0.

This is the SAME SHAPE as the earlier "break events=0" bug that HEARTBEAT already records: a silence printed as a
measured zero, because a count crossed a process boundary and its DENOMINATOR did not cross with it. The direction
matters -- it inflates the count of games that "reached only level 0", which is the count the build is trying to
move, so the error flatters nothing but it does make the ground look mute where the ground was never asked.

The fix is not to drop the crashed game silently either; that would be the same bug wearing a smaller number. It is
counted, under its own name, in `games_errored`.
"""
from __future__ import annotations

from newhorse.redux_arch.swarm import echo_pool, tether_distribution


def _played(gid: str, levels: int, stage: str = "MINT_UNFIRED"):
    return dict(game=gid, family="click", levels=levels, steps=40,
                tether_stage=dict(counts={stage: 1}, stalls=1, advances=(1 if levels else 0),
                                  furthest_stage=stage, furthest_rank=2),
                echo=dict(break_events=1, diff_ran=1, residual_nonempty=1, minted=0, promoted=0,
                          reuse_attempted=0, reuse_attempted_foreign=0, fired=0, cleared=0))


def _crashed(gid: str):
    """Exactly what `_play_policy` returns when the session will not open: levels=0, and NO tether_stage."""
    return dict(game=gid, family="error", levels=0, steps=0, outcome="open_error:HTTPError")


def test_a_game_that_never_opened_is_not_counted_as_a_game_that_reached_level_zero():
    results = {"aa11-x": _played("aa11-x", 0), "bb22-y": _played("bb22-y", 1), "zz99-dead": _crashed("zz99-dead")}
    pool = echo_pool(results)
    assert pool["max_level_histogram"] == {"0": 1, "1": 1}, "the crashed game must not appear as a level-0 game"
    assert pool["games_errored"] == 1


def test_the_histogram_sums_to_the_number_of_games_that_actually_reported():
    """The property, not the instance: whatever the mix, histogram total + errored == every game in the sweep, and
    the histogram total == games_reporting. If those two ever disagree again the sweep is lying about its own n."""
    results = {}
    for i in range(7):
        results["g%02d-ok" % i] = _played("g%02d-ok" % i, i % 3)
    for i in range(3):
        results["g%02d-dead" % i] = _crashed("g%02d-dead" % i)
    dist = tether_distribution(results)
    in_hist = sum(dist["max_level_histogram"].values())
    assert in_hist == dist["games_reporting"] == 7
    assert dist["games_errored"] == 3
    assert in_hist + dist["games_errored"] == len(results)


def test_the_L2_reach_count_also_excludes_crashes():
    """`games_reaching_L2` is the carrier-reach number that decides whether a within-run-across-levels echo has any
    live instance. A crash counted at level 0 cannot inflate it, but it can deflate the FRACTION a reader computes
    from it, so it has to leave by the same door."""
    results = {"a-1": _played("a-1", 2), "b-2": _played("b-2", 0), "c-3": _crashed("c-3")}
    pool = echo_pool(results)
    assert pool["games_reaching_L2"] == 1
    assert sum(pool["max_level_histogram"].values()) == 2


def test_a_crashed_game_still_contributes_nothing_to_the_echo_totals():
    """Guard against the opposite over-correction: the fix must not start counting a crash as evidence anywhere."""
    live = {"a-1": _played("a-1", 1)}
    withdead = dict(live, **{"z-9": _crashed("z-9")})
    assert echo_pool(live)["echo"] == echo_pool(withdead)["echo"]


def test_a_sweep_with_no_crashes_is_unchanged():
    """The common case must be bit-identical to before, or this fix is a behaviour change wearing a bug fix's name."""
    results = {"a-1": _played("a-1", 0), "b-2": _played("b-2", 1), "c-3": _played("c-3", 2)}
    pool = echo_pool(results)
    assert pool["max_level_histogram"] == {"0": 1, "1": 1, "2": 1}
    assert pool["games_errored"] == 0
