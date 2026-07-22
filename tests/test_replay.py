"""
redux-arch P4.3: the recording replay harness, proven on a SYNTHETIC known-answer recording before it is trusted
on real ARC frames. A hand-built maze: a 1-px cursor (colour 4) walks black(0) corridors bounded by red(2) walls;
a move SUCCEEDS iff the destination cell is floor. The harness must (a) learn cursor=4 and the per-action vecs
from motion alone, (b) calibrate passable={0} from the cursor's own trajectory, (c) mint the colour-agnostic
INTENDED_FREE (cheaper than INTENDED_COLOUR==0, so it wins).
"""
import sys, os, json, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.replay import load_recording, learn_basis, replay_affordance


class _Maze:
    """A tiny grid maze. Floor=0, wall=2, cursor=4. The cursor moves one cell per action unless a wall blocks it."""
    def __init__(self):
        self.g = np.full((9, 9), 2, dtype=int)            # all wall
        self.g[1:8, 4] = 0                                 # a vertical corridor
        self.g[4, 1:8] = 0                                 # a horizontal corridor (a plus-shaped maze)
        self.pos = [4, 4]
        self.dirs = {"ACTION1": (-1, 0), "ACTION2": (1, 0), "ACTION3": (0, -1), "ACTION4": (0, 1)}

    def frame(self):
        f = self.g.copy(); f[tuple(self.pos)] = 4; return f

    def step(self, action):
        dr, dc = self.dirs[action]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if 0 <= nr < 9 and 0 <= nc < 9 and self.g[nr, nc] == 0:   # move iff destination is floor
            self.pos = [nr, nc]
        return self.frame()


def _write_recording(seq):
    fd, path = tempfile.mkstemp(suffix=".jsonl"); os.close(fd)
    with open(path, "w") as fh:
        for frame, action in seq:
            fh.write(json.dumps({"data": {"frame": [frame.tolist()],
                                          "action_input": {"id": action}, "levels_completed": 0}}) + "\n")
    return path


def _make_recording(n=120, seed=0):
    rng = np.random.RandomState(seed)
    m = _Maze()
    seq = [(m.frame(), "RESET")]
    acts = ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]
    for _ in range(n):
        a = acts[rng.randint(4)]
        f = m.step(a)
        seq.append((f, a))
    return _write_recording(seq)


def test_learn_basis_recovers_cursor_and_vecs():
    path = _make_recording()
    frames, acts = load_recording(path)
    cursor, vec_table = learn_basis(frames, acts)
    assert cursor == 4, cursor                              # the 1-px sprite, found by motion
    # each directional action's learned vec is the unit step in that direction
    assert vec_table.get("ACTION1") == (-1, 0) and vec_table.get("ACTION2") == (1, 0)
    assert vec_table.get("ACTION3") == (0, -1) and vec_table.get("ACTION4") == (0, 1)
    os.remove(path)


def test_replay_mints_colour_agnostic_intended_free():
    path = _make_recording(n=140)
    res = replay_affordance(path, warmup=30, min_exceptions=15, min_hits=2, max_size=1)
    assert res.cursor == 4
    assert res.passable == frozenset({0}), res.passable    # floor learned from the cursor's own trajectory
    assert res.minted_names, "nothing minted from the recording's blocking residual"
    # the winning predicate is the colour-AGNOSTIC affordance, not the palette-specific occupancy atom
    assert frozenset({"INTENDED_FREE"}) in res.minted_names, res.minted_names
    os.remove(path)
