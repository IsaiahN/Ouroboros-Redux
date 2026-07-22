"""
loop.py -- the Ouroboros-Redux per-step loop as NAMED BLOCKS (Phase 0 of the redux-arch charter).

The chart's egocentric loop is:  belief-state -> object-perception -> [ abductive-goal -> market -> apply-Gamma
-> act ]xN -> innovation-residual -> alpha-gate -> objective? ,  with the novel red block (residual-driven
predicate MINTING, Region III) hanging off "R won't compress under Gamma".

Phase 0 does NOT rebuild any of this. It COMPOSES the proven `AgentLoop` (which already implements every
"adopt"-verdict block) and exposes its parts under the chart's canonical names, plus an explicit `mint_seam`
where Region III plugs in. This gives the architecture a clean, swappable substrate with the working internals
intact -- monolith-then-carve: name the seams first, carve behind them later. Nothing silent: `blocks()` and the
mint-seam log make the decomposition and the still-empty Region III visible.
"""
from __future__ import annotations
from typing import Callable, Dict, Any, List, Optional
import numpy as np
from ..agent_loop import AgentLoop

# chart block -> (canonical term, citation, which new-horse component implements it, verdict)
CHART_BLOCKS: Dict[str, Dict[str, str]] = {
    "belief_state":    {"term": "POMDP sufficient statistic", "cite": "Kaelbling 1998",
                        "impl": "AgentLoop.tracker (object identities carried across frames)", "verdict": "adopt"},
    "perception":      {"term": "object slots / object files", "cite": "Locatello 2020; Kahneman 1992",
                        "impl": "perception.segment + ObjectTracker + agency/coupled_agency", "verdict": "adopt"},
    "abductive_goal":  {"term": "inverse problem / IRL / BToM", "cite": "Ng&Russell 2000; Baker 2009",
                        "impl": "relations.candidate_relations/quantified_candidates + GoalManager", "verdict": "adopt"},
    "market":          {"term": "bucket-brigade / economy of agents", "cite": "Holland 1986; Baum 1999",
                        "impl": "marketplace.informative_salience + GoalManager price market", "verdict": "adopt"},
    "apply_gamma":     {"term": "type-directed proof search (predict, before-state)", "cite": "Ellis 2021",
                        "impl": "agency.predict + AgentLoop._apply (predict next frame)", "verdict": "adopt"},
    "residual":        {"term": "innovation / prediction error", "cite": "Kalman 1960; Rao&Ballard 1999",
                        "impl": "residual.ResidualBus (aim + sense + currency + self)", "verdict": "adopt"},
    "alpha_gate":      {"term": "adaptive convex mixing coefficient", "cite": "Jacobs&Jordan 1991",
                        "impl": "two_streams.Pose (learnable alpha over private residual vs social grammar)", "verdict": "adopt"},
    "predicate_minting": {"term": "residual-driven predicate invention (MDL)", "cite": "Muggleton&Buntine 1988; Rissanen 1978",
                        "impl": "REGION III -- NOT YET BUILT (the seam)", "verdict": "NOVEL / empty"},
}


class ArchLoop:
    """The chart's loop, named-block view over a proven AgentLoop, with the Region-III minting seam explicit."""

    def __init__(self, actions: List[str], background: int = 0):
        self.core = AgentLoop(actions=actions, background=background)
        # named-block views onto the proven internals (composition, not reimplementation)
        self.belief_state = self.core.tracker
        self.perception = self.core                     # segment/track/agency live on the core
        self.abductive_goal = self.core.goals
        self.market = self.core.goals                   # the price market is the GoalManager
        self.apply_gamma = self.core.agency
        self.residual = self.core.residuals
        self.alpha_gate = self.core.pose
        # Region III: the fast local mint plugs in here. Default: no engine (the seam is honest about being empty).
        self.mint_seam: Optional[Callable[["ArchLoop", np.ndarray, str, np.ndarray], Any]] = None
        self.log: List[str] = self.core.log

    def blocks(self) -> Dict[str, Dict[str, str]]:
        """The chart decomposition, for introspection (nothing silent). Region III is flagged empty."""
        return CHART_BLOCKS

    def step(self, frame: np.ndarray, env_step: Callable[[str], np.ndarray]) -> str:
        """One closed cycle. Delegates to the proven loop, then runs the Region-III seam (if an engine is set).
        The residual R = |Gamma(b,a) - o'| is already banked by the core each step; the seam reads it to decide
        whether to mint. With no engine, it records that Region III is still empty (never silently 'succeeds')."""
        frame = np.asarray(frame)
        ctrl = self.core.perceive(frame)
        if ctrl is None:
            return self.core.actions[0]
        action, tname, _pred = self.core.choose(frame, ctrl)
        after = np.asarray(env_step(action))
        self.core.observe(frame, ctrl, action, tname, after)
        if self.mint_seam is not None:
            self.mint_seam(self, frame, action, after)          # Region III: residual -> MDL mint (Phase 2+)
        else:
            self.log.append("MINT-SEAM  Region III empty (no minting engine wired yet)")
        return action
