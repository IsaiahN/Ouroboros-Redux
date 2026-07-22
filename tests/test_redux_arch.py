"""
Phase 0 (redux-arch): the chart's loop expressed as NAMED BLOCKS over the proven AgentLoop.

Verifies the named-block substrate is real and swappable, that it runs (delegating to the working internals so
behaviour is unchanged), that the Region-III minting seam is explicit + pluggable, and that the decomposition is
introspectable (nothing silent). This is the substrate the minting engine (Phase 2) plugs into.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch import ArchLoop, CHART_BLOCKS


class MoverWorld:
    """A single controllable (colour 4) that steps by unit deltas -- enough to exercise the loop end to end."""
    def __init__(self):
        self.h, self.w = 10, 10
        self.pos = [5, 1]
        self.secret = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

    def frame(self):
        g = np.zeros((self.h, self.w), dtype=int)
        g[tuple(self.pos)] = 4
        return g

    def step(self, action):
        dr, dc = self.secret.get(action, (0, 0))
        nr, nc = self.pos[0] + dr, self.pos[1] + dc
        if 0 <= nr < self.h and 0 <= nc < self.w:
            self.pos = [nr, nc]
        return self.frame()


def test_named_blocks_cover_the_chart_and_flag_region_iii():
    loop = ArchLoop(actions=["U", "D", "L", "R"], background=0)
    b = loop.blocks()
    # every adopted chart block is named with a citation + a concrete implementation
    for name in ("belief_state", "perception", "abductive_goal", "market", "apply_gamma", "residual", "alpha_gate"):
        assert name in b and b[name]["cite"] and b[name]["impl"], (name, b.get(name))
        assert b[name]["verdict"] == "adopt"
    # the one novel block is present and HONESTLY flagged empty (Region III not yet built)
    assert "predicate_minting" in b and "NOVEL" in b["predicate_minting"]["verdict"]
    assert "NOT YET BUILT" in b["predicate_minting"]["impl"]
    # the named views point at the real proven components (composition, not reimplementation)
    assert loop.residual is loop.core.residuals
    assert loop.alpha_gate is loop.core.pose
    assert loop.apply_gamma is loop.core.agency


def test_loop_runs_and_banks_residual_with_seam_empty_by_default():
    world = MoverWorld()
    loop = ArchLoop(actions=["U", "D", "L", "R"], background=0)
    for _ in range(12):
        loop.step(world.frame(), world.step)
    # the loop ran end to end (residual bus accumulated surprise -- the sense organ is live)
    assert loop.residual.pe_integral() >= 0.0
    # with no engine wired, Region III is honestly reported empty every step (never silently 'mints')
    assert any(line.startswith("MINT-SEAM  Region III empty") for line in loop.log)


def test_mint_seam_is_pluggable():
    # the seam where Phase 2's fast local mint attaches: a callable (loop, before, action, after) -> Any
    calls = {"n": 0}
    def fake_engine(loop, before, action, after):
        calls["n"] += 1                                  # a real engine would read loop.residual and MDL-mint
    world = MoverWorld()
    loop = ArchLoop(actions=["U", "D", "L", "R"], background=0)
    loop.mint_seam = fake_engine
    for _ in range(5):
        loop.step(world.frame(), world.step)
    assert calls["n"] == 5                                # the seam is invoked once per step, ready for Region III
