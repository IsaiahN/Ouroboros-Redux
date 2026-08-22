"""
Engine Interfaces - Protocol Definitions for Decision Rung System
=================================================================

This module defines the interfaces (Protocols) that the 42 decision rungs
expect from their engine dependencies. Each Protocol specifies:
- What methods the rung will call
- What parameters are expected
- What return types are expected

Using Protocols (structural subtyping) instead of ABC allows:
- Existing classes to conform without modification
- Easier testing with mock objects
- Clear documentation of rung dependencies

Usage:
    from engines.interfaces import SelfModelInterface

    class MySelfModel:
        # Implement all methods from SelfModelInterface
        def get_embedding_suggested_action(...) -> ...:
            ...

    # Type checker will verify MySelfModel conforms to SelfModelInterface
    model: SelfModelInterface = MySelfModel()
"""

import os

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from typing import Any, Dict, List, Optional, Protocol, Tuple

# =============================================================================
# SELF MODEL INTERFACES
# Used by: EmbeddingSuggestionRung, MetacognitivePredictionRung,
#          FewShotInvariantsRung, NetworkObjectInventoryRung
# =============================================================================

class SelfModelInterface(Protocol):
    """
    Interface for agent self-model system.

    Provides:
    - Object control tracking ("I am this object")
    - Embedding-based frame matching
    - Network hypothesis sharing
    - Few-shot relation learning
    """

    def get_embedding_suggested_action(
        self,
        game_type: Optional[str],
        level: Optional[int],
        current_frame: Optional[List[List[int]]],
        action_scores: Optional[Dict[int, float]] = None,
        top_k: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Get action suggestion based on learned frame embeddings.

        Finds similar past situations and returns what action worked best.

        Returns:
            Dict with 'action', 'confidence', 'similar_count' or None
        """
        ...

    def get_current_prediction(self) -> Optional[Dict[str, Any]]:
        """
        Get the current hypothesis being tested.

        Returns:
            Dict with 'test_action', 'confidence', 'hypothesis' or None
        """
        ...

    def get_few_shot_control_relations(
        self,
        game_id: str,
        level: int,
        min_confidence: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Get few-shot invariants/variants from sequence abstraction.

        Returns:
            Dict with 'suggested_action', 'sample_size', 'confidence' or None
        """
        ...

    def get_network_object_inventory(
        self,
        game_type: str,
        level: int
    ) -> Dict[str, Any]:
        """
        Query network knowledge about interactable objects.

        Returns:
            Dict with 'total_unique', 'interactable', etc.
        """
        ...

    def share_control_discovery_to_network(
        self,
        agent_id: str,
        game_id: str,
        level: int,
        controlled_objects: List[str],
        action_response_map: Dict[str, List[str]],
        confidence: float,
        generation: int = 0
    ) -> Optional[str]:
        """
        Share "I am this object" discovery to network.

        Returns:
            hypothesis_id if shared, None otherwise
        """
        ...


# =============================================================================
# VISUAL ANALYZER INTERFACES
# Used by: VisualAnalyzerRung, GridExplorationRung
# =============================================================================

class VisualAnalyzerInterface(Protocol):
    """
    Interface for visual frame analysis.

    Provides:
    - Priority target identification for ACTION6 clicks
    - Grid-based systematic exploration
    - Salient feature detection
    """

    def get_priority_targets(
        self,
        frame: Optional[List[List[int]]]
    ) -> List[Dict[str, Any]]:
        """
        Get prioritized click targets from frame analysis.

        Returns:
            List of dicts with 'x', 'y', 'confidence', 'reason'
        """
        ...

    def get_grid_exploration_targets(self) -> List[Dict[str, Any]]:
        """
        Get systematic grid walk targets when stuck.

        Returns:
            List of dicts with 'x', 'y', 'grid_index'
        """
        ...

    def set_priority_color(self, color: int, reason: str = "") -> None:
        """Set a priority color to target based on learning."""
        ...

    def record_color_success(self, color: int) -> None:
        """Record that clicking a color led to success."""
        ...


# =============================================================================
# SCIENTIFIC METHOD INTERFACES
# Used by: ScientificMethodRung, QuestioningRung, TheoryGateRung
# =============================================================================

class QuestioningEngineInterface(Protocol):
    """Interface for Q1-Q9 questioning system.

    NAME CORRECTED 2026-08-22 (EXAM_02 DEFECT A). This Protocol declared
    ``get_blocking_questions()`` and ``get_allowed_actions(...)``. The live
    implementation -- ``QuestioningEngineWithTeeth`` in
    ``engines/reasoning/scientific_method_engine.py`` -- defines NEITHER; it
    answers both questions from ONE method, ``get_blocking_info()``, whose
    return carries both the blocking questions and the actions they allow.
    The implementation is live and working, so the declaration was the drift.
    """

    def get_blocking_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about why actions are being blocked.

        Returns:
            Dict with 'is_blocked', 'blocking_questions', 'allowed_actions',
            'total_score_penalty' -- or None when nothing is blocking.
        """
        ...


class ScientificMethodInterface(Protocol):
    """
    Interface for theory formation and testing.

    Provides:
    - Working theory management (the theory STAGE is a field of it)
    - Questioning engine access

    NAME CORRECTED 2026-08-22 (EXAM_02 DEFECT A). ``get_theory_stage()`` was
    declared here and defined by nothing; the stage is the ``'stage'`` key of
    ``get_working_theory(game_type, level_number)``, which IS implemented and
    IS already read that way by ``TheoryGateRung`` (``rungs/hypothesis.py``).
    ``get_working_theory``'s declared signature took no arguments; the
    implementation requires ``(game_type, level_number)``.
    """

    def get_working_theory(
        self,
        game_type: str,
        level_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get the current working theory for this game/level.

        Returns:
            Dict with 'theory', 'stage', 'confidence', 'evidence_for',
            'evidence_against' -- where 'stage' is one of 'speculating',
            'exploring', 'hypothesis_formed', 'partial_confirmation',
            'contradicted', 'confident', 'transferred'.
        """
        ...

    @property
    def questioning_engine(self) -> QuestioningEngineInterface:
        """Access the questioning engine.

        UNIMPLEMENTED -- see UNIMPLEMENTED_DECLARATIONS at the bottom of this
        module. Declared, guarded at ``rungs/orientation.py``, defined by no
        class in the tree.
        """
        ...


# =============================================================================
# TERMINAL PATTERN INTERFACES
# Used by: DeathAvoidanceRung, TerminalPatternRung
# =============================================================================

class TerminalPatternInterface(Protocol):
    """
    Interface for death/danger pattern detection.

    Provides:
    - Graduated action weights based on danger
    - Terminal state approach detection
    """

    def get_graduated_action_weights(
        self,
        game_type: str,
        level: int,
        position: Tuple[int, int],
        frontier_mode: bool = False
    ) -> Dict[str, float]:
        """
        Get safety weights for each action based on historical death patterns.

        Returns:
            Dict mapping action name to weight (0.0-1.0, lower = more dangerous)
        """
        ...

    def detect_terminal_approach(
        self,
        frame: Optional[List[List[int]]],
        recent_actions: List[str]
    ) -> Dict[str, Any]:
        """
        Detect if approaching a terminal (death) state.

        Returns:
            Dict with 'approaching_terminal', 'fatal_action', 'confidence'

        UNIMPLEMENTED -- see UNIMPLEMENTED_DECLARATIONS at the bottom of this
        module.
        """
        ...


# =============================================================================
# PRIMITIVE SUGGESTER INTERFACE (replaces CODS)
# Used by: PrimitiveSuggesterRung
# =============================================================================

class PrimitiveSuggesterInterface(Protocol):
    """
    Interface for direct primitive-to-action mapping.

    Replaces the deprecated CODSEngine with simpler approach:
    - Apply primitives to frames
    - Map outputs to actions
    - Track effectiveness via RLVR
    """

    def suggest_action(
        self,
        frame: List[List[int]],
        game_type: Optional[str] = None,
        recent_actions: Optional[List[int]] = None
    ) -> Any:
        """
        Suggest action based on primitive analysis.

        Returns:
            SuggestionResult with action, confidence, primitive, reasoning
        """
        ...

    def record_outcome(
        self,
        game_type: str,
        primitive: str,
        action: int,
        success: bool
    ) -> None:
        """Record outcome for RLVR learning."""
        ...


# Legacy alias for backward compatibility
class CODSEngineInterface(Protocol):
    """
    DEPRECATED: Use PrimitiveSuggesterInterface instead.

    Kept for backward compatibility with existing code.
    """

    def suggest_action(
        self,
        game_context: Dict[str, Any],
        available_actions: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get action suggestion."""
        ...


# =============================================================================
# VIRAL PACKAGE INTERFACE
# Used by: PariahAvoidanceRung
# =============================================================================

class ViralPackageInterface(Protocol):
    """
    Interface for viral knowledge spread system.

    Provides:
    - Pariah pattern queries (failed strategies)
    - Package creation and distribution

    NAME CORRECTED 2026-08-22 (EXAM_02 DEFECT A). ``get_pariahs`` was declared
    here and defined by neither ``ViralPackageEngine`` nor the ``PariahManager``
    it delegates to. The live method is ``get_top_pariahs(limit)`` -- present on
    both, one of the eight declared pass-throughs at
    ``engines/social/viral_package_engine.py``.
    """

    def get_top_pariahs(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the most toxic failed patterns (pariahs) by trigger count.

        Returns:
            List of dicts with the pariah's failed pattern and toxicity.
        """
        ...


# =============================================================================
# FRUSTRATION DETECTOR INTERFACE
# Used by: FrustrationDetectionRung
# =============================================================================

class FrustrationDetectorInterface(Protocol):
    """Interface for stuck/frustration detection."""

    def is_frustrated(self) -> Dict[str, Any]:
        """
        Check if agent is frustrated (stuck).

        Returns:
            Dict with 'is_frustrated', 'reason', 'severity'
        """
        ...


# =============================================================================
# SENSATION ENGINE INTERFACE
# Used by: SensationEngineRung
# =============================================================================

class SensationEngineInterface(Protocol):
    """
    Interface for emotional/sensation-based decision biasing.

    Provides:
    - Tetrahedral sensation model (approach/avoid/curiosity/threat)
    """

    def get_tetrahedral_sensation(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get emotional coloring for current situation.

        Returns:
            Dict with 'approach_score', 'threat_level', 'threat_direction', etc.
        """
        ...


# =============================================================================
# I-THREAD INTERFACE
# Used by: IThreadRung, TwoStreamsRung
# =============================================================================

class IThreadInterface(Protocol):
    """
    Interface for persistent agent identity.

    Provides:
    - Stream weight management (wA/wB), per agent
    - Death persona spawning

    NAME CORRECTED 2026-08-22 (EXAM_02 DEFECT A). ``get_wA()``/``get_wB()``
    were declared here and defined by nothing. The weights are fields of the
    ``IThreadState`` returned by ``get_state(agent_id)`` -- which IS
    implemented, and IS already read that way by ``TwoStreamsRung``
    (``rungs/hypothesis.py``). The weights are per-agent; the declared
    zero-argument form could not have been implemented as declared.
    """

    def get_state(self, agent_id: str) -> Any:
        """
        Get the current I-Thread state for an agent.

        Returns:
            IThreadState carrying ``w_a`` (private experience) and ``w_b``
            (network wisdom), which sum to 1.0.
        """
        ...

    def spawn_death_persona(
        self,
        role: str
    ) -> Optional[Dict[str, Any]]:
        """
        Spawn a death persona when near culling.

        Returns:
            Dict with 'name', 'suggested_action', 'reason' or None

        UNIMPLEMENTED -- see UNIMPLEMENTED_DECLARATIONS at the bottom of this
        module.
        """
        ...


# =============================================================================
# NEAR MISS ANALYZER INTERFACE
# Used by: NearMissAnalyzerRung
# =============================================================================

class NearMissAnalyzerInterface(Protocol):
    """Interface for learning from high-score failures.

    NAME CORRECTED 2026-08-22 (EXAM_02 DEFECT A). ``get_insights(game_type,
    level)`` was declared here and defined by nothing, which left
    ``NearMissAnalyzerRung`` (priority 48) with no reachable body at all. The
    live method is ``get_near_miss_report(agent_id, generation)``; its
    ``top_insights`` rows are the insights the rung was written to read, and
    they are scoped by AGENT and GENERATION, not by game and level.
    """

    def get_near_miss_report(
        self,
        agent_id: Optional[str] = None,
        generation: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get the comprehensive near-miss analysis report.

        Returns:
            Dict with 'statistics', 'common_patterns', 'top_insights',
            'thresholds'. ``top_insights`` rows carry 'insight_type',
            'insight_description', 'priority', 'effectiveness_score'.
        """
        ...


# =============================================================================
# SUBGOAL PLANNER INTERFACE
# Used by: SubgoalPlanningRung
# =============================================================================

class SubgoalPlannerInterface(Protocol):
    """Interface for subgoal decomposition."""

    def get_current_subgoal(self) -> Optional[Dict[str, Any]]:
        """
        Get the current subgoal being pursued.

        Returns:
            Dict with 'next_action', 'confidence', 'description', 'index', 'total'

        UNIMPLEMENTED -- see UNIMPLEMENTED_DECLARATIONS at the bottom of this
        module.
        """
        ...


# =============================================================================
# BUDGET ALLOCATOR INTERFACE
# Used by: BreakthroughBudgetRung
# =============================================================================

class BudgetAllocatorInterface(Protocol):
    """Interface for dynamic action budget allocation.

    NAME CORRECTED 2026-08-22 (EXAM_02 DEFECT A). ``get_budget(game_type)`` was
    declared here and defined by nothing. The live method is
    ``calculate_game_budget(game_id, agent_id=None)`` on
    ``BreakthroughBudgetAllocator``, and its keys are
    ``action_allowance_per_level`` / ``action_allowance_total``, not
    ``per_level`` / ``total``.
    """

    def calculate_game_budget(
        self,
        game_id: str,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate the optimal action budget for a game.

        Returns:
            Dict with 'action_allowance_per_level', 'action_allowance_total',
            'phase', 'reason', 'network_level_wins'.
        """
        ...


# =============================================================================
# REGULATORY SIGNAL INTERFACE
# Used by: RegulatorySignalRung
# =============================================================================

class RegulatorySignalInterface(Protocol):
    """Interface for network homeostasis signals."""

    def get_active_signals(self) -> List[Dict[str, Any]]:
        """
        Get currently active regulatory signals.

        Returns:
            List of dicts with 'type', 'strength', etc.

        UNIMPLEMENTED -- see UNIMPLEMENTED_DECLARATIONS at the bottom of this
        module.
        """
        ...


# =============================================================================
# RESONANCE DETECTOR INTERFACE
# Used by: ResonanceDetectorRung
# =============================================================================

class ResonanceDetectorInterface(Protocol):
    """Interface for cross-agent pattern discovery."""

    def get_resonant_patterns(
        self,
        game_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get patterns that resonate across agents.

        Returns:
            List of dicts with 'suggested_action', 'resonance_score', 'description'
        """
        ...


# DELETED 2026-08-22 (EXAM_02 DEFECT A): CounterfactualAnalyzerInterface.
# It declared `generate_micro_rollouts`, defined by no class in the tree, and
# named `MicroCounterfactualRung` as its consumer -- a rung that does not exist
# either. No registry row, no property, no call site, no implementation: there
# was nothing for the declaration to be true or false about. Deleted rather than
# allowlisted, because an allowlist entry claims something is still wanted.


# =============================================================================
# ACTION HANDLER INTERFACE
# Used by: CoordinateOscillationRung, ThreeLayerFilterRung
# =============================================================================

class ActionHandlerInterface(Protocol):
    """Interface for action execution and tracking."""

    def detect_oscillation(self) -> Dict[str, Any]:
        """
        Detect coordinate oscillation patterns.

        Returns:
            Dict with 'oscillation_detected', 'oscillating_coords'
        """
        ...


# =============================================================================
# MULTI-STAGE PIPELINE INTERFACE
# Used by: MultiStageMatchingRung
# =============================================================================

class MultiStagePipelineInterface(Protocol):
    """Interface for cascading sequence matching."""

    def get_sequence_with_fallback(
        self,
        game_type: str,
        level: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get sequence using multi-stage fallback.

        Returns:
            Dict with 'sequence', 'confidence', 'stage' or None
        """
        ...


# =============================================================================
# ABSTRACTION ENGINE INTERFACE
# Used by: AbstractionTemplatesRung
# =============================================================================

class AbstractionEngineInterface(Protocol):
    """Interface for pattern template abstraction."""

    def should_use_template(
        self,
        game_type: str,
        level: int
    ) -> bool:
        """Check if a template should be used for this game/level."""
        ...

    def get_template_for_replay(
        self,
        game_type: str,
        level: int
    ) -> Optional[List[str]]:
        """Get template sequence for replay."""
        ...


# =============================================================================
# REPLAY LEARNING INTERFACE
# Used by: ReplayLearningRung
# =============================================================================

class ReplayLearningInterface(Protocol):
    """Interface for prediction-based replay learning."""

    def get_current_prediction(self) -> Optional[Dict[str, Any]]:
        """
        Get current prediction during replay.

        Returns:
            Dict with 'action', 'confidence', 'hypothesis' or None

        UNIMPLEMENTED -- see UNIMPLEMENTED_DECLARATIONS at the bottom of this
        module. NOTE: two OTHER classes define this name
        (``MetacognitiveReasoningEngine``, ``CognitiveCore``); the engine this
        Protocol is bound to, ``ReplayLearningEngine``, does not. A tree-wide
        "does any class define this name" check passes and is WRONG here, which
        is why the gate binds Protocols to their loaded class.
        """
        ...


# =============================================================================
# IMAGINATION BUDGET INTERFACE
# Used by: ImaginationBudgetRung
# =============================================================================

class ImaginationBudgetInterface(Protocol):
    """Interface for cognitive budget allocation.

    NAME CORRECTED 2026-08-22 (EXAM_02 DEFECT A). ``calculate_budget(_is_novel,
    is_frontier, surprise_score)`` was declared here and defined by nothing,
    which left ``ImaginationBudgetRung`` (priority 4) with no reachable body at
    all. ``ImaginationBudgetManager`` does not take novelty as an ARGUMENT: it
    carries the budget as state and moves it with ``update_from_outcome``.
    ``get_stats()`` is the read side, and it is what the rung needs.
    """

    def get_stats(self) -> Dict[str, Any]:
        """
        Get the current imagination budget statistics.

        Returns:
            Dict with 'current_budget', 'base_budget', 'persona_allowance',
            'can_speculate', 'synthesis_depth', 'consecutive_zeros',
            'consecutive_wins', 'avg_recent_score'.
        """
        ...


# =============================================================================
# NETWORK EXPLORATION TRACKER INTERFACE
# Used by: NetworkExplorationStatsRung
# =============================================================================

class NetworkExplorationInterface(Protocol):
    """Interface for exploration coverage tracking.

    NAME CORRECTED 2026-08-22 (EXAM_02 DEFECT A). ``get_exploration_stats``
    was declared here and defined by nothing, which left
    ``NetworkExplorationStatsRung`` (priority 9) with no reachable body at all.
    ``get_exploration_context_for_reasoning`` is the tracker's own stated
    "main integration point"; it is the only method that returns BOTH the
    coverage figure and a direction, which is what the rung reads.
    """

    def get_exploration_context_for_reasoning(
        self,
        game_type: str,
        level: int,
        current_position: Optional[Tuple[int, int]] = None,
        frame_width: int = 64,
        frame_height: int = 64
    ) -> Dict[str, Any]:
        """
        Get the complete exploration context for the reasoning payload.

        Returns:
            Dict with 'network_exploration' (carrying 'coverage_percent' and
            'unexplored_count'), 'exploration_recommendations',
            'current_region', 'current_region_known', 'suggested_direction'.
        """
        ...


# DELETED 2026-08-22 (EXAM_02 DEFECT A): PrimitiveHelperInterface.
# It declared `detect_stuck_pattern`, defined by no class, and named
# `PrimitiveStuckDetectionRung` as its consumer -- a rung that does not exist.
# The capability is real but lives elsewhere and by a different mechanism:
# `detect_stuck_pattern` is a registered SEED PRIMITIVE (seed_primitives.py),
# reached through `DecisionRung.call_primitive("detect_stuck_pattern", ...)`,
# not through an engine attribute. The Protocol described an access path the
# build does not use.


# =============================================================================
# COMBINED ENGINE REGISTRY INTERFACE
# =============================================================================

class EngineRegistryInterface(Protocol):
    """
    Interface for the central engine registry.

    Provides lazy-loaded access to all engines via properties.
    """

    @property
    def self_model(self) -> Optional[SelfModelInterface]: ...

    @property
    def visual_analyzer(self) -> Optional[VisualAnalyzerInterface]: ...

    # NAME CORRECTED 2026-08-22: the registry property is
    # `scientific_method_engine`; `scientific_method` was declared here and
    # exists on no registry.
    @property
    def scientific_method_engine(self) -> Optional[ScientificMethodInterface]: ...

    @property
    def terminal_pattern_detector(self) -> Optional[TerminalPatternInterface]: ...

    @property
    def cods_engine(self) -> Optional[CODSEngineInterface]:
        """DEPRECATED: Use primitive_suggester instead."""
        ...

    @property
    def primitive_suggester(self) -> Optional[PrimitiveSuggesterInterface]: ...

    @property
    def viral_package_engine(self) -> Optional[ViralPackageInterface]: ...

    @property
    def frustration_detector(self) -> Optional[FrustrationDetectorInterface]: ...

    @property
    def sensation_engine(self) -> Optional[SensationEngineInterface]: ...

    @property
    def i_thread(self) -> Optional[IThreadInterface]: ...

    @property
    def near_miss_analyzer(self) -> Optional[NearMissAnalyzerInterface]: ...

    @property
    def subgoal_planner(self) -> Optional[SubgoalPlannerInterface]: ...

    @property
    def breakthrough_allocator(self) -> Optional[BudgetAllocatorInterface]: ...

    @property
    def regulatory_engine(self) -> Optional[RegulatorySignalInterface]: ...

    @property
    def resonance_detector(self) -> Optional[ResonanceDetectorInterface]: ...

    # `counterfactual_analyzer` deleted 2026-08-22 with its Protocol: no
    # registry row, no property, no consumer.

    @property
    def action_handler(self) -> Optional[ActionHandlerInterface]: ...

    @property
    def multi_stage_pipeline(self) -> Optional[MultiStagePipelineInterface]: ...

    @property
    def abstraction_engine(self) -> Optional[AbstractionEngineInterface]: ...

    @property
    def replay_learning_engine(self) -> Optional[ReplayLearningInterface]: ...

    @property
    def imagination_budget(self) -> Optional[ImaginationBudgetInterface]: ...

    @property
    def network_exploration_tracker(self) -> Optional[NetworkExplorationInterface]: ...

    # `primitive_helper` deleted 2026-08-22 with its Protocol: the capability is
    # a seed primitive, not an engine attribute.


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Self Model
    'SelfModelInterface',

    # Perception
    'VisualAnalyzerInterface',
    'TerminalPatternInterface',

    # Cognition
    'ScientificMethodInterface',
    'QuestioningEngineInterface',
    'CODSEngineInterface',

    # Memory/Planning
    'ViralPackageInterface',
    'MultiStagePipelineInterface',
    'AbstractionEngineInterface',
    'ReplayLearningInterface',

    # Regulation
    'FrustrationDetectorInterface',
    'BudgetAllocatorInterface',
    'ImaginationBudgetInterface',
    'RegulatorySignalInterface',
    'NetworkExplorationInterface',

    # Social
    'ResonanceDetectorInterface',

    # Consciousness
    'SensationEngineInterface',
    'IThreadInterface',

    # Analysis
    'NearMissAnalyzerInterface',
    'SubgoalPlannerInterface',
    'ActionHandlerInterface',

    # Registry
    'EngineRegistryInterface',

    # The conformance record (module-bottom, below)
    'PROTOCOL_BINDINGS',
    'UNIMPLEMENTED_DECLARATIONS',
]


# =============================================================================
# MODULE-BOTTOM: THE CONFORMANCE RECORD
# =============================================================================
# Added 2026-08-22 after EXAM_02 DEFECT A. These two tables are DATA, not
# behaviour -- strings only, no imports, no side effects. They exist because a
# Protocol on its own says nothing checkable: structural subtyping has no
# declaration site that binds a Protocol to the class the build actually loads,
# so nothing could ever be wrong. `tests/gate/test_protocol_conformance.py`
# reads both by AST and turns them into a check that CAN fail.
#
# FIGURE 10 -- install what can be violated. The whole of DEFECT A was 21
# `hasattr` guards that could only take one branch. A guard that cannot fail is
# not a check; neither is a Protocol nothing is measured against.

#: Protocol name -> ('module path', 'class name') of the implementation the
#: registry actually constructs. Derived from ``engines/registry.py``'s
#: ``ENGINE_CONFIGS`` and stated here so the binding is a fact a test can read
#: rather than an inference. A Protocol absent from this map is unbound: its
#: methods are checked tree-wide instead (any class may satisfy them).
PROTOCOL_BINDINGS = {
    'SelfModelInterface': ('engines/self_model/cognitive_core.py', 'CognitiveCore'),
    'VisualAnalyzerInterface': ('engines/perception/visual_analyzer.py', 'VisualAnalyzer'),
    'ScientificMethodInterface': ('engines/reasoning/scientific_method_engine.py',
                                  'ScientificMethodEngine'),
    'QuestioningEngineInterface': ('engines/reasoning/scientific_method_engine.py',
                                   'QuestioningEngineWithTeeth'),
    'TerminalPatternInterface': ('engines/perception/terminal_pattern_detector.py',
                                 'TerminalPatternDetector'),
    'PrimitiveSuggesterInterface': ('engines/social/primitive_suggester.py',
                                    'PrimitiveSuggester'),
    'ViralPackageInterface': ('engines/social/viral_package_engine.py', 'ViralPackageEngine'),
    'FrustrationDetectorInterface': ('engines/regulation/frustration_detector.py',
                                     'FrustrationDetector'),
    'SensationEngineInterface': ('engines/consciousness/sensation_engine.py', 'SensationEngine'),
    'IThreadInterface': ('engines/consciousness/i_thread.py', 'IThread'),
    'NearMissAnalyzerInterface': ('engines/memory/near_miss_analyzer.py', 'NearMissAnalyzer'),
    'SubgoalPlannerInterface': ('engines/planning/subgoal_planner.py', 'SubgoalPlanner'),
    'BudgetAllocatorInterface': ('breakthrough_budget_allocator.py',
                                 'BreakthroughBudgetAllocator'),
    'RegulatorySignalInterface': ('engines/regulation/regulatory_signal_engine.py',
                                  'RegulatorySignalEngine'),
    'ResonanceDetectorInterface': ('engines/social/resonance_detector.py', 'ResonanceDetector'),
    'MultiStagePipelineInterface': ('multi_stage_matching_pipeline.py',
                                    'MultiStageMatchingPipeline'),
    'AbstractionEngineInterface': ('engines/planning/sequence_abstraction.py',
                                   'SequenceAbstraction'),
    'ReplayLearningInterface': ('engines/planning/replay_learning_engine.py',
                                'ReplayLearningEngine'),
    'ImaginationBudgetInterface': ('engines/regulation/imagination_budget.py',
                                   'ImaginationBudgetManager'),
    'NetworkExplorationInterface': ('engines/regulation/network_exploration_tracker.py',
                                    'NetworkExplorationTracker'),
    'EngineRegistryInterface': ('engines/registry.py', 'EngineRegistry'),
}

#: ('ProtocolName', 'method') -> WHY it is declared with no implementation.
#: THIS IS THE CONVENTION THAT CAN BE VIOLATED (Figure 10): an entry with an
#: empty reason reds the gate, and an unlisted unimplemented method reds it too.
#: Every entry here is a capability the ladder ASKS FOR and does not have. That
#: is the finding, kept where it cannot be lost, not a licence to leave it.
UNIMPLEMENTED_DECLARATIONS = {
    ('ScientificMethodInterface', 'questioning_engine'):
        "QuestioningEngineWithTeeth exists in the same module but "
        "ScientificMethodEngine composes no instance of it and nothing in the "
        "tree constructs one, so QuestioningRung (orientation, priority 10-15 "
        "in four ladders) can never reach it. Kept declared because the rung is "
        "priority-ordered and the composition is the missing piece, not the "
        "interface; the absence is logged at the call site.",
    ('TerminalPatternInterface', 'detect_terminal_approach'):
        "TerminalPatternDetector answers danger per PLANNED ACTION AND POSITION "
        "(check_position_danger / check_for_terminal_danger); it has no method "
        "that takes a frame plus recent actions and answers 'am I approaching "
        "death'. TerminalPatternRung asks the second question and has neither "
        "the planned action nor the position in hand. Kept declared: the "
        "capability is wanted and absent, and inventing it here would be "
        "inventing a death predictor.",
    ('IThreadInterface', 'spawn_death_persona'):
        "No class in the tree spawns a death persona. PersonaManager "
        "(engines/consciousness/persona_runtime.py) has spawn_temporary_persona "
        "and is TEST-ONLY-reachable (EXAM_02 preserve row 7); IThread does not "
        "hold one. Kept declared because the near-cull branch of IThreadRung is "
        "the only consumer of that preserve row's capability.",
    ('SubgoalPlannerInterface', 'get_current_subgoal'):
        "SubgoalPlanner is plan-scoped: get_next_subgoal_actions(plan_id, "
        "frame, available_actions) requires a plan_id created by create_plan, "
        "and no plan_id is carried in the rung context. The missing piece is "
        "the plan's lifetime in context, not a rename.",
    ('RegulatorySignalInterface', 'get_active_signals'):
        "RegulatorySignalEngine only EMITS signals (emit_agent_signals, "
        "emit_role_need_signals) and summarises them per GENERATION "
        "(get_regulation_summary(generation)); it has no per-decision read of "
        "currently-live signals, and the rung has no generation in context.",
    ('ReplayLearningInterface', 'get_current_prediction'):
        "ReplayLearningEngine generates a prediction FOR A NAMED UPCOMING "
        "ACTION (generate_prediction(context, action_index, action_type, "
        "frame, sequence_actions)) inside a learning session; it holds no "
        "'current' prediction to be read back. Two other classes define this "
        "name, which is why the gate binds Protocols to their loaded class.",
}
