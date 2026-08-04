"""THE CLICK DRIVE CONSUMES THE COMPOSED OBJECTIVE (cycle 21, stage 2b) -- de-fragmentation, one family.

Stage 1 gave the composer a self in every family, so it poses on 25/25 games. But `_posed_goal` had exactly ONE
consumer in the whole agent (`_act_directional`), and CLICK is the largest family on the public set. So on most
games the agent composed an objective and then acted as if it had not. An objective nothing consumes is a log
line. These pin the wiring, and -- just as importantly -- pin the LIMITS of it:

  * the drive evaluates THE POSED PREDICATE, `Predicate.holds(Context(...))`, over candidate click cells -- it
    does not approximate the objective as "click the target". The headline test is that the SAME target under two
    different relations names two DIFFERENT sets of cells; a consumer that could not tell them apart would be a
    colour-picker wearing a composer's name;
  * a DISPLACEMENT relation (ACTS_TOWARD) needs a self to measure displacement FROM, and with no effect-locus yet
    the drive says nothing rather than guessing -- silence is the correct reading of "I have no self here";
  * the posed goal is a PRIOR: it orders the untried queue, breaks ties BELOW measured empowerment
    (`novel`/`changed`), and speaks in the nothing-ever-moved fallback -- but it never overrides evidence;
  * re-posing is idempotent (priority is a set); a changed objective re-marks rather than accumulating;
  * a colour that shatters into a texture is not a referent and must not flood the queue;
  * with no posed goal, nothing changes at all -- the pre-cycle-21 click drive, exactly;
  * `OURO_POSE_CONSUME=0` restores that as an A/B arm.

Nothing here names a game.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.click import ClickProber
from newhorse.redux_arch.policy import ReduxPolicy
from newhorse.redux_arch.goal import PosedGoal
from newhorse.redux_arch.dsl import Predicate, make_atom

TOWARD = Predicate(frozenset({make_atom("ACTS_TOWARD")}))
TOUCH = Predicate(frozenset({make_atom("TOUCH")}))
SAMEROW = Predicate(frozenset({make_atom("SAME_ROW")}))


class _M:
    def __init__(self, pred):
        self.predicate = pred


def _goal(target, pred=TOUCH):
    return PosedGoal(target=target, mint=_M(pred), saved_bits=9.0, support=10)


# ---- the prober's side --------------------------------------------------------------------------------------

def test_prioritized_cells_are_drained_first_among_untried():
    p = ClickProber([(1, 1), (2, 2), (3, 3)], sweep=[])
    p.prioritize([(3, 3)])
    assert p.choose() == (3, 3)
    assert p.branch.get("untried_posed") == 1


def test_a_prioritized_cell_not_in_the_pool_is_admitted():
    p = ClickProber([(1, 1)], sweep=[])
    assert p.prioritize([(9, 9)]) == 1
    assert (9, 9) in p.tries and p.origin[(9, 9)] == "posed"
    assert p.choose() == (9, 9)


def test_prioritize_is_idempotent():
    p = ClickProber([(1, 1)], sweep=[])
    assert p.prioritize([(9, 9)]) == 1
    assert p.prioritize([(9, 9)]) == 0                   # re-posing the same objective admits nothing new
    assert len(p.targets) == 2


def test_marking_replaces_rather_than_accumulates():
    """A priority that only ever grows is not a priority. The first sweep of this wiring unioned, and one game
    finished with 258 cells marked -- an agent that adopts a new reading of the game but never withdraws the old
    one is not changing its mind, it is accumulating minds. Cells ADMITTED by a retracted objective stay in the
    pool: they were legitimate candidates once proposed, and the evidence since gathered on them is real."""
    p = ClickProber([(1, 1)], sweep=[])
    p.prioritize([(9, 9)])
    p.prioritize([(1, 1)])                               # the objective changed its mind
    assert p._priority == {(1, 1)}
    assert (9, 9) in p.tries                             # ...but the candidate it introduced is not thrown away


def test_an_objective_that_names_nothing_retracts_its_marking():
    """The stale-incumbent failure of stage 2a, one layer down: an early return would leave a dead objective
    steering the drive. Here the referent leaves the board, and the cells it named stop being priority."""
    g = _grid()
    p = _pol(g, [(4, 5)], _goal(5, TOUCH))
    assert p._click_posed_cells(g) == 1
    g2 = np.zeros((24, 24), dtype=int)                   # the referent colour is gone from the board
    assert p._click_posed_cells(g2) == 0
    assert p.prober._priority == set()


def test_priority_does_not_override_measured_empowerment():
    """THE EPISTEMICS. A prior orders a search; evidence decides one. Once every candidate has been tried, the
    exploit ranking is `novel`/`changed` -- what this agent actually watched happen -- and a posed cell that never
    moved the board must NOT outrank a cell that did."""
    p = ClickProber([(1, 1), (2, 2)], sweep=[])
    p.prioritize([(2, 2)])
    p.tries[(1, 1)] = 3; p.changed[(1, 1)] = 3; p.novel[(1, 1)] = 3   # (1,1) is productive
    p.tries[(2, 2)] = 3                                               # the posed cell never moved anything
    assert p.choose() == (1, 1)
    assert p.branch.get("exploit_scored") == 1


def test_priority_breaks_the_tie_that_evidence_cannot():
    """The correction that made stage 2b audible at all. Priority on the UNTRIED queue alone was a voice with
    nothing to say -- a click game drains its pool long before the composer has a window to pose from -- so it
    also ranks in the exploit key, BELOW the evidence and ABOVE least-tried. Here the evidence is a dead heat and
    the objective is the only thing either cell has going for it."""
    p = ClickProber([(1, 1), (2, 2)], sweep=[])
    for t in ((1, 1), (2, 2)):
        p.tries[t] = 2; p.changed[t] = 1; p.novel[t] = 1
    p.prioritize([(2, 2)])
    assert p.choose() == (2, 2)
    assert p.branch.get("exploit_scored") == 1


def test_priority_speaks_where_nothing_ever_moved():
    """The other half of the same correction: on a board where no click this agent made has ever changed anything,
    `least-tried` is the ranking admitting it has nothing. A posed objective is precisely something."""
    p = ClickProber([(1, 1), (2, 2)], sweep=[])
    p.tries[(1, 1)] = 1; p.tries[(2, 2)] = 1             # both tried, neither ever moved the board
    p.prioritize([(2, 2)])
    assert p.choose() == (2, 2)
    assert p.branch.get("nothing_moved_posed") == 1


def test_with_no_posed_goal_the_order_is_exactly_as_before():
    a = ClickProber([(1, 1), (2, 2)], sweep=[])
    b = ClickProber([(1, 1), (2, 2)], sweep=[])
    b.prioritize([])                                     # posing nothing must be a no-op, not a reordering
    assert a.choose() == b.choose() == (1, 1)


# ---- the policy's side --------------------------------------------------------------------------------------

def _grid():
    g = np.zeros((24, 24), dtype=int)
    g[4:7, 4:7] = 5                                      # two components of the posed colour: centroids (5,5)...
    g[16:19, 16:19] = 5                                  # ...and (17,17)
    g[10, 10] = 8                                        # a distractor colour
    return g


def _pol(grid, pool, goal, eff=None):
    p = ReduxPolicy(game_id="test")
    p.frames = [grid]
    p.prober = ClickProber(list(pool), sweep=[])
    p._posed_goal = goal
    p._eff_locus = eff
    return p


def test_the_same_target_under_two_relations_names_two_different_sets():
    """THE HEADLINE. What makes this a consumed OBJECTIVE rather than a colour lookup is that the relation
    changes WHICH cells satisfy it. Same board, same posed target, same candidate pool -- two relations, two
    answers. TOUCH names the cell beside a referent; SAME_ROW names the cells on a referent's row (including the
    referents themselves, which trivially share their own row -- that is the relation being read honestly, not a
    special case)."""
    g = _grid()
    pool = [(5, 0), (4, 5), (9, 9)]
    a = _pol(g, pool, _goal(5, TOUCH))
    b = _pol(g, pool, _goal(5, SAMEROW))
    assert a._click_posed_cells(g) == 1
    assert b._click_posed_cells(g) == 3
    assert a.prober._priority == {(4, 5)}
    assert b.prober._priority == {(5, 0), (5, 5), (17, 17)}


def test_a_referent_nobody_proposed_as_a_click_point_is_still_reachable():
    """The candidate pool is the prober's targets PLUS the referent centroids -- otherwise an objective could name
    a place the drive had no way to click."""
    g = _grid()
    p = _pol(g, [(9, 9)], _goal(5, SAMEROW))
    assert p._click_posed_cells(g) == 2
    assert (5, 5) in p.prober.tries and p.prober.origin[(5, 5)] == "posed"


def test_a_displacement_relation_says_nothing_without_a_self():
    """ACTS_TOWARD is about a MOVE, and a move is measured from where the effect last was. With no effect-locus
    the agent has no self in this family yet, and the honest output is silence -- not a guess with `action_vec`
    quietly set to (0,0), which would make the predicate uniformly false while LOOKING like it was evaluated."""
    g = _grid()
    p = _pol(g, [(5, 0), (4, 5), (9, 9)], _goal(5, TOWARD))
    assert p._eff_locus is None
    assert p._click_posed_cells(g) == 0


def test_a_displacement_relation_names_the_cells_that_close_the_gap():
    g = np.zeros((24, 24), dtype=int)
    g[4:7, 4:7] = 5                                      # one referent, centroid (5,5)
    p = _pol(g, [(8, 8), (16, 16)], _goal(5, TOWARD), eff=(12, 12))
    assert p._click_posed_cells(g) == 1                  # (8,8) moves the effect toward (5,5); (16,16) away
    assert p.prober._priority == {(8, 8)}


def test_no_posed_goal_offers_nothing():
    p = ReduxPolicy(game_id="test")
    p.prober = ClickProber([(0, 0)], sweep=[])
    assert p._posed_goal is None
    assert p._click_posed_cells(_grid()) == 0
    assert p.prober._priority == set()


def test_a_shattered_colour_is_a_texture_not_a_referent():
    """Flooding the untried queue with hundreds of specks would be the composer STARVING curiosity rather than
    directing it, which is the opposite of what consuming an objective is for."""
    g = np.zeros((24, 24), dtype=int)
    g[::2, ::2] = 5                                      # 144 isolated single-pixel components
    p = _pol(g, [(0, 1)], _goal(5, TOUCH))
    assert p._click_posed_cells(g) == 0


def test_an_absent_colour_offers_nothing():
    p = _pol(_grid(), [(0, 0)], _goal(11, TOUCH))        # colour 11 is not on the board
    assert p._click_posed_cells(_grid()) == 0


def test_the_consumer_flag_restores_the_old_click_drive(monkeypatch):
    """The A/B arm. Same board and same pool that name a cell above; with the flag off, nothing is named."""
    monkeypatch.setenv("OURO_POSE_CONSUME", "0")
    g = _grid()
    p = _pol(g, [(4, 5)], _goal(5, TOUCH))
    assert p._click_posed_cells(g) == 0
    assert p.prober._priority == set()


def test_end_to_end_the_click_drive_clicks_what_it_posed():
    """The headline at the level the environment sees: given a posed objective, the very next click the agent
    emits is on a cell that SATISFIES it."""
    g = _grid()
    p = _pol(g, [(9, 9), (4, 5)], _goal(5, TOUCH))
    lbl, data = p._act_click()
    assert lbl == "A6"
    assert (data["y"], data["x"]) == (4, 5)
    assert p.prober.branch.get("untried_posed") == 1
