"""
redux-arch P5-GOAL: the goal-poser mints the game's objective off the PROGRESS residual, and the load-bearing
discovery is TARGET SELECTION -- picking the object the reward tracks out of several salient candidates (a
distractor is present as a red herring). Also pins the two guards: random progress poses NOTHING (no structure),
and a near-empty reward poses NOTHING (SUPPORT) -- exactly the ls20 zero-win / sparse-reward situation.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.goal import pose_goal, static_salient_targets


def _nav_steps(seed, n=220, reward_target=(6, 11), n_actions=4):
    """Avatar random-walks a 12x12 board; 'progressed' == it got closer to reward_target this step. A DISTRACTOR
    candidate (8) sits in the opposite corner. The poser sees both candidates and must select the reward-linked
    one purely from which relation compresses the progress stream."""
    rng = random.Random(seed)
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    avatar = [6, 6]
    steps = []
    for _ in range(n):
        dr, dc = dirs[rng.randint(0, n_actions - 1)]
        before = tuple(avatar)
        nr, nc = max(0, min(11, before[0] + dr)), max(0, min(11, before[1] + dc))
        d_b = abs(before[0] - reward_target[0]) + abs(before[1] - reward_target[1])
        d_a = abs(nr - reward_target[0]) + abs(nc - reward_target[1])
        avatar = [nr, nc]
        steps.append((before, (dr, dc), {7: reward_target, 8: (0, 0)}, d_a < d_b))
    return steps


def test_poser_selects_the_reward_linked_target_over_a_distractor():
    goal = pose_goal(_nav_steps(0), avatar_colour=4, max_size=1)
    assert goal is not None, "posed no goal despite a clear reward-linked target"
    assert goal.target == 7, ("selected the distractor / wrong target", goal.target)   # NOT 8
    assert "ACTS_TOWARD(focus,target)" in {a.name for a in goal.mint.predicate.atoms}, goal.mint.predicate


def test_poser_is_stable_for_a_target_in_a_different_place():
    # move the true reward target to a different corner: the poser must track it there, not memorize colour 7.
    goal = pose_goal(_nav_steps(1, reward_target=(0, 0)), avatar_colour=4, max_size=1)
    assert goal is not None and goal.target == 7
    # with the true target at (0,0) and the distractor ALSO at (0,0)? no -- distractor is fixed at (0,0) here,
    # so use a config where they differ:
    steps = _nav_steps(2, reward_target=(11, 11))
    g2 = pose_goal(steps, avatar_colour=4, max_size=1)
    assert g2 is not None and g2.target == 7


def test_random_progress_poses_nothing():
    rng = random.Random(3)
    steps = [(s[0], s[1], s[2], rng.random() < 0.5) for s in _nav_steps(3)]   # reward decorrelated from geometry
    assert pose_goal(steps, avatar_colour=4, max_size=1) is None               # no relation compresses noise


def test_near_empty_reward_poses_nothing_support_guard():
    # reward only when the avatar is EXACTLY on the target (essentially never on a random walk) -> k≈0 -> unmintable
    rng = random.Random(4)
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    avatar = [6, 6]; TRUE = (6, 11); steps = []
    for _ in range(220):
        dr, dc = dirs[rng.randint(0, 3)]
        before = tuple(avatar)
        nr, nc = max(0, min(11, before[0] + dr)), max(0, min(11, before[1] + dc))
        avatar = [nr, nc]
        steps.append((before, (dr, dc), {7: TRUE, 8: (0, 0)}, (nr, nc) == TRUE))
    assert pose_goal(steps, avatar_colour=4, max_size=1) is None               # SUPPORT: near-zero positive mass


def test_salient_targets_prior_ignores_noise_floor_and_the_moving_avatar():
    # a MOVING avatar (4), a huge floor (0) and field (2), a 1px noise fleck (1), and ONE static compact
    # landmark (7). The referent prior must pick 7 -- not the fleck (the first-live-run bug), not the floor/field,
    # not the mover. This is the fix for ls20 (where it now picks the grey box, colour 5, over a 2px fleck).
    from newhorse.redux_arch.goal import salient_targets
    frames = []
    for k in range(10):
        g = np.zeros((20, 20), dtype=int)          # floor 0 (large)
        g[:, 0:5] = 2                               # field/wall wash 2 (large)
        g[1, 15] = 1                                # 1px noise fleck
        g[2:5, 15:18] = 7                           # a compact static landmark (9px)
        g[10, 6 + k] = 4                            # the avatar, moving right each frame
        frames.append(g)
    tgts = salient_targets(frames, avatar_colour=4, exclude={0, 2}, top=3)
    assert tgts and tgts[0] == 7, tgts               # the distinct static landmark, not noise/floor/mover


def test_static_salient_targets_picks_the_distinct_landmark():
    # a moving avatar (4), a big background (0), a big wall wash (2), and ONE small static landmark (7).
    frames = []
    for k in range(6):
        g = np.zeros((12, 12), dtype=int)
        g[0:12, 0:3] = 2                                   # a static wall wash (large)
        g[1, 10] = 7                                        # the small static landmark
        g[6, 3 + k] = 4                                     # the avatar, moving
        frames.append(g)
    tgts = static_salient_targets(frames, avatar_colour=4, bg=0, top=2)
    assert tgts[0] == 7, tgts                               # the small distinct landmark ranks first
