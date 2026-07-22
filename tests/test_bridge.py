"""
redux-arch P4 step 1: the Perception->Context bridge wires the minter to live frames. On a wall-free mover world
whose progress ⟺ moving toward the target, the loop should re-derive ACTS_TOWARD from its own progress-residual
(the docs' MOVE_TOWARD example, now from real perception rather than a synthetic Context).
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch import ArchLoop
from newhorse.redux_arch.minting import MintingEngine
from newhorse.redux_arch.bridge import LiveMintBridge


class MoverTargetWorld:
    """Cursor (colour 4) moves unit steps on a small board; a fixed target (colour 7). No walls, so progress
    ⟺ the action reduces distance to the target -- exactly what ACTS_TOWARD tests."""
    def __init__(self):
        self.h, self.w = 12, 12
        self.pos = [6, 2]
        self.target = (6, 9)
        self.secret = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

    def frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        g[self.target] = 7
        g[tuple(self.pos)] = 4
        return g

    def step(self, action):
        dr, dc = self.secret.get(action, (0, 0))
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if 0 <= nr < self.h and 0 <= nc < self.w:
            self.pos = [nr, nc]
        return self.frame()


def test_bridge_runs_and_buffers_before_state_exceptions():
    world = MoverTargetWorld()
    loop = ArchLoop(actions=["U", "D", "L", "R"], background=0)
    eng = MintingEngine(min_exceptions=1000, max_size=2)   # huge threshold: never mint, just observe/buffer
    loop.mint_seam = LiveMintBridge(eng, target_colour=7)
    for _ in range(40):
        loop.step(world.frame(), world.step)
    assert len(eng.buffer) > 0                             # the bridge produced live exceptions
    # every buffered context is a BEFORE-state Context (focus, target, action_vec) -- no outcome leakage
    ctx, outcome = eng.buffer[0]
    assert hasattr(ctx, "focus_rc") and hasattr(ctx, "target_rc") and hasattr(ctx, "action_vec")
    assert isinstance(outcome, bool)


def test_loop_rederives_acts_toward_from_its_own_progress_residual():
    world = MoverTargetWorld()
    loop = ArchLoop(actions=["U", "D", "L", "R"], background=0)
    eng = MintingEngine(min_exceptions=30, max_size=1)     # size-1: expect the single atom ACTS_TOWARD
    loop.mint_seam = LiveMintBridge(eng, target_colour=7)
    for _ in range(120):
        loop.step(world.frame(), world.step)
    # the agent explores + navigates, producing both toward (progress) and away (no progress) steps; the
    # predicate that compresses that residual is ACTS_TOWARD -- MOVE_TOWARD re-derived from live perception.
    assert eng.minted, "no predicate minted from the live progress-residual"
    names = set().union(*[{a.name for a in m.predicate.atoms} for m in eng.minted])
    assert "ACTS_TOWARD(focus,target)" in names, names
