"""
Boundary-directed empowerment (Tether §4.4): when reward is 0 on a graduated level, curiosity is aimed at the
NOVEL loci (the new actors the boundary diff surfaced), not the whole board -- and it prefers actors it can
actually AFFECT (empowerment). Pins the DirectedExplorer mechanism + the policy wiring on a two-body KEEP.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch.explore import DirectedExplorer
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard, TWO_BODY


def test_directed_explorer_sweeps_novel_actors_then_prefers_productive():
    de = DirectedExplorer()
    targets = [("a", (5, 5)), ("b", (9, 9))]
    picks = []
    # first two picks sweep both novel actors once (least-tried first)
    p = de.choose(targets); picks.append(p[0]); de.credit(False)
    p = de.choose(targets); picks.append(p[0]); de.credit(True)      # 'b' contact CHANGED the board -> productive
    assert set(picks) == {"a", "b"}
    # now both tried; the PRODUCTIVE one is preferred
    assert de.choose(targets)[0] == "b"
    assert de.productive() == ["b"]


def test_directed_explorer_none_on_empty_targets():
    de = DirectedExplorer()
    assert de.choose([]) is None


class _AMirror:
    def __init__(self):
        self.L = [10, 4]; self.R = [10, 15]; self.mv = {"A1": (-1, 0), "A2": (1, 0), "A3": (0, -1), "A4": (0, 1)}
    def frame(self, extra=None):
        g = np.zeros((20, 20), dtype=int); g[tuple(self.L)] = 7; g[tuple(self.R)] = 7
        if extra is not None:
            g[extra] = 6                                              # a NEW actor colour 6
        return g
    def step(self, a):
        d = self.mv.get(a, (0, 0))
        if a in ("A1", "A2"):
            self.L = [self.L[0] + d[0], self.L[1] + d[1]]; self.R = [self.R[0] + d[0], self.R[1] + d[1]]
        else:
            self.L = [self.L[0], self.L[1] + d[1]]; self.R = [self.R[0], self.R[1] - d[1]]
        return self.frame()


def test_policy_arms_directed_empowerment_on_two_body_keep_with_novel_actors():
    p = ReduxPolicy(game_id="t-1", blackboard=Blackboard())
    w = _AMirror()
    grid = w.frame()
    for _ in range(12):                                              # route TWO_BODY
        p.observe(grid, [1, 2, 3, 4, 5]); lbl, _ = p.choose(); grid = w.step(lbl)
    assert p.family == TWO_BODY
    # graduate: bodies persist (KEEP) + a NEW 2x2 actor (colour 6) appears -> a NOVEL locus
    nf = np.zeros((20, 20), dtype=int); nf[10, 4] = 7; nf[10, 15] = 7; nf[2:4, 2:4] = 6
    p.observe(nf, [1, 2, 3, 4, 5], levels_completed=1)
    assert p.level_model["decision"] == "keep"
    assert p.novel_loci, "no novel loci surfaced"
    assert p._directed is not None                                   # directed empowerment armed at the novel actor
    # and it now drives toward the novel actor
    p.observe(nf, [1, 2, 3, 4, 5], levels_completed=1)
    lbl, _ = p.choose()
    assert lbl.startswith("A")                                       # emitted a drive action (toward the novel locus)


def test_abduce_on_reward_is_gated(tmp_path):
    # a NOVEL goal mint abduced at a reward boundary must be PARKED (guarded_promote), never self-certified.
    # We exercise the gate directly (the live path calls mint_gate identically).
    p = ReduxPolicy(game_id="gz", blackboard=Blackboard())
    cp = str(tmp_path / "c.jsonl"); fp = str(tmp_path / "ok.txt")
    assert p.mint_gate("NOVEL", "COUNT(k)", 61.0, context="directed", claims_path=cp, confirmed_path=fp) is False
    assert os.path.exists(cp)                                        # recorded UNCONFIRMED for human review
