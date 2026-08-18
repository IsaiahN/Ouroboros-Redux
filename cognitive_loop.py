import os

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # Rule 1: Disable pycache

"""
Cognitive Loop - Perceive -> Think -> Map -> Act

This is the central nervous system that makes the agent an ORGANISM
rather than a bag of organs. It orchestrates:

1. PERCEIVE: Multimodal scene understanding (parallel channels)
2. THINK: Phenomenological compression (felt-state + strategy)
3. MAP: Causal knowledge update/query (the leapfrog enabler)
4. ACT: Three-speed decision making (mapped/reasoned/explore)

And crucially: the output of ACT feeds back into PERCEIVE on the next
cycle, closing the loop. The causal map informs perception, perception
informs thinking, thinking consults the map, the map drives action.

This module does NOT replace the existing DecisionRungSystem.
It WRAPS it, adding structured perception and causal reasoning around
the existing rung evaluation. Rungs become the "REASONED" speed of
action selection — the middle path between fast mapped execution and
slow exploratory discovery.

Usage:
    loop = CognitiveLoop(decision_system, db)
    loop.start_game(game_id, available_actions)

    # Per action:
    action, data, frame_record = loop.cycle(frame, obs)
    # ... execute action ...
    loop.record_result(frame_changed, score_delta, level_changed)

    # After game:
    replay = loop.get_replay()
"""

import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from engines.cognition.causal_map import CausalMap, PlannedAction
from engines.cognition.cognitive_frame import CognitiveFrame
from engines.cognition.phenomenology_layer import FeltState, PhenomenologyLayer, Valence
from engines.egocentric.swallow import swallow_note as _swal  # B4: swallow counter
from engines.perception.perceiver import Perceiver
from engines.perception.perceptual_field import PerceptualField

logger = logging.getLogger(__name__)

# ── Movement-stack + reset-discipline knobs (Register G; provenance GUESSED,
#    arm-testable — the A5 law: marked so they never read as settled;
#    registered in KNOBS.md AMENDMENT 9) ─────────────────────────────────────
NAV_BIAS_P = 0.5     # GUESSED: cap on the [NAV] steer's share of blind draws
RESET_MIN_RUN = 3    # GUESSED: frame-changing steps that make a run "solid"
#                      (the [RESET] counter is INSTRUMENTATION ONLY — no
#                      selection guard ships until the counter has reported)


def _neg_feed(loop, mut) -> None:
    """B6 (BUILD_PROGRAM_2 W1): the negative-evidence feeder — every W4c-1
    class comparison examined counts neg_tried; an UNMUTATED comparison IS a
    negative instance accrued (neg_passed). Feeds the reserved
    NO_NEGATIVE_INSTANCES starvation socket (R1). One-line call site by the
    .credit/.route window law; containment: never raises."""
    try:
        _c = getattr(loop, "_w4c_counters", None)
        if _c is not None:
            _c["neg_tried"] = _c.get("neg_tried", 0) + 1
            if not mut:
                _c["neg_passed"] = _c.get("neg_passed", 0) + 1
    except Exception:
        pass


def _seed_imp(loop) -> None:
    """W1 (CONSUMER DRIVER, seed side): enter this agent's import_candidates
    for (game, playing level) into Gamma at the gamma init site — episode N's
    end_game consumed the queue; episode N+1 seeds the candidates here, each
    atom flagged imported=True (consumer.seed_imports' exact signature; the
    wheel rule outranks imports — 2x TRANSFERRED still required to drive).
    One-line call site by the .credit/.route window law; containment: never
    raises."""
    try:
        _g = getattr(loop, "_gamma", None)
        _f = getattr(loop, "_ego_fabric", None)
        if _g is not None and _f is not None:
            from engines.egocentric.consumer import seed_imports
            _n = seed_imports(_g, _f, str(getattr(loop, "_game_id", "") or "game"),
                              int(getattr(loop, "_ego_level", 0) or 0) + 1)
            if _n:
                print(f"[IMPORT] seeded {_n} candidate atom(s) imported=True")
    except Exception:
        _swal(loop, "OTHER")


def _goal_bank(loop, game, level, pre, post) -> int:
    """G-C: THE ONE BANKING CORE — every route to the abduction bank enters here.

    LINK3_AUDIT: `_goal_abd` used to hold this body and had exactly ONE call
    site, inside the cognitive cycle. A level-up reached by PREFIX REPLAY never
    enters that cycle, so it never reached the bank — which is why every banked
    record was level 1 (level 1 is reached by exploration, level 2 only by
    replay: SUCCESS SUPPRESSES THE EVIDENCE CHANNEL). The body is therefore
    factored out here rather than copied, so the two routes cannot drift and
    the cognitive cycle is not duplicated.

    Mines the pre->post frame delta for STRUCTURAL predicates (mechanics, never
    answers) and banks them as game+level-scoped GOAL HYPOTHESES on the
    collective "goal_hypotheses" stream; a level-up WITHOUT a known predicate
    falsifies it (credibility drops). Returns the number banked; containment:
    0 on anything at all, never raises."""
    _n = 0
    try:
        _fab = getattr(loop, "_ego_fabric", None)
        if _fab is None or pre is None or post is None:
            return 0
        if getattr(loop, "_goal_book", None) is None:
            from engines.egocentric.goal_abduction import GoalBook
            loop._goal_book = GoalBook(_fab)
        for _b in loop._goal_book.observe_levelup(
                str(game or "game"), int(level),
                np.asarray(pre), np.asarray(post)):
            _n += 1
            print(f"[GOAL] banked {_b.get('sig')} (level-up delta hypothesis)")
    except Exception:
        _swal(loop, "SPINE")
    return _n


def _goal_abd(loop, level_changed, post_array) -> None:
    """G-C (PREREG_FINAL_GAPS): goal abduction's COGNITIVE-CYCLE bank site — on a
    level-up, hand the pre->post frame delta to `_goal_bank`. A3-2 CONVENTION
    (PLAYING level): _ego_level has already been incremented on this
    level-changed step, so the bare value banked here IS the playing level at
    which the goal was achieved (pre-increment + 1). One-line call site placed
    AFTER the .credit/.route anchors by the window law; containment: never
    raises."""
    try:
        _pre = getattr(loop, "_prev_frame", None)
        if not level_changed or _pre is None or post_array is None:
            return
        _goal_bank(loop, str(getattr(loop, "_game_id", "") or "game"),
                   int(getattr(loop, "_ego_level", 0) or 0), _pre, post_array)
    except Exception:
        _swal(loop, "SPINE")


def _hyd_ver(loop) -> Dict[str, int]:
    """A3-1 (KNOBS.md AMENDMENT 3): "verified" is BOOK-DERIVED. Hydrate the
    planner's per-atom TRANSFERRED tally from the settlements books at the W4c
    lazy-init, so cross-episode verification persists (pre-fix the dict was
    born empty and every atom -- imported atoms especially -- had to re-earn
    its 2x TRANSFERRED inside a single episode). The in-episode increment path
    is unchanged: it adds to this hydrated base.

    Scope: THIS game at the FULL version-id grain (A3-3 knowledge grain) at
    the PLAYING level (_ego_level + 1 -- A3-2 CONVENTION (PLAYING level):
    settlements carry the level being played). Reads the personal AND
    collective settlements streams (BetBook writes collective today; personal
    is the forward-compatible half of the pair), BOUNDED to the last N=500
    records per scope -- the janitor's settlements retention is 100 raw
    records, so 500 covers every survivor without an unbounded scan. One-line
    call site by the .credit/.route window law; containment: empty dict,
    never raises."""
    out: Dict[str, int] = {}
    try:
        fab = getattr(loop, "_ego_fabric", None)
        if fab is None:
            return out
        g = str(getattr(loop, "_game_id", "") or "game")
        lv = int(getattr(loop, "_ego_level", 0) or 0) + 1
        for scope in ("personal", "collective"):
            try:
                rows = fab.query(scope, "settlements")
            except Exception:
                continue
            for rec in rows[-500:]:                  # bounded read: last N=500
                try:
                    if (rec.get("atom_bin") == "TRANSFERRED"
                            and rec.get("atom_key") is not None
                            and str(rec.get("game")) == g
                            and int(rec.get("level", -1)) == lv):
                        k = str(rec.get("atom_key"))
                        out[k] = out.get(k, 0) + 1
                except Exception:
                    continue
        if out:
            print("[VERIFIED] hydrated %d atom(s) from the books "
                  "(game=%s level=%d)" % (len(out), g, lv))
    except Exception:
        pass
    return out


# =============================================================================
# PERCEPTUAL BLACKBOARD ADAPTER
# =============================================================================


class PerceptualBlackboardAdapter:
    """
    Adapter that makes PerceptualField + CognitiveLoop state look like a
    Blackboard for PhenomenologyLayer.

    PhenomenologyLayer reads from ``blackboard.get(key, default)`` and writes
    via ``blackboard.slot(key, value, source_rung=...)``.  This adapter
    translates those reads into live PerceptualField fields and CognitiveLoop
    game state so PhenomenologyLayer can compress perception without
    depending on the full Blackboard infrastructure.

    Written values (from ``inject()``) are stored in a local overlay dict
    and returned on subsequent ``get()`` calls, closing the feedback loop.
    """

    def __init__(self) -> None:
        self._percept: Optional[PerceptualField] = None
        self._loop_state: Dict[str, Any] = {}
        self._injected: Dict[str, Any] = {}
        self._prev_confidence: float = 0.0
        self._recent_strategies: List[str] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def update(
        self, percept: PerceptualField, loop_state: Dict[str, Any]
    ) -> None:
        """Refresh with fresh perception + loop state each cycle."""
        if self._percept is not None:
            self._prev_confidence = self._percept.overall_confidence
        self._percept = percept
        self._loop_state = loop_state

    def reset(self) -> None:
        """Reset for a new game."""
        self._percept = None
        self._loop_state = {}
        self._injected = {}
        self._prev_confidence = 0.0
        self._recent_strategies = []

    # ------------------------------------------------------------------
    # Blackboard-compatible read (used by PhenomenologyLayer.compress)
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Blackboard-compatible ``get``."""
        # Injected values (written by PhenomenologyLayer.inject) win
        if key in self._injected:
            return self._injected[key]

        if self._percept is None:
            return default

        value = self._resolve(key)
        return value if value is not None else default

    # ------------------------------------------------------------------
    # Blackboard-compatible write (used by PhenomenologyLayer.inject)
    # ------------------------------------------------------------------

    def slot(
        self,
        key: str,
        value: Any = None,
        *,
        source_rung: str = "unknown",
        confidence: float = 1.0,
        source_primitive: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Any:
        """Blackboard-compatible ``slot`` (write when *value* given)."""
        if value is not None:
            self._injected[key] = value
            return value
        return self._injected.get(key)

    # ------------------------------------------------------------------
    # Slot resolution: maps blackboard key -> PerceptualField/loop state
    # ------------------------------------------------------------------

    def _resolve(self, key: str) -> Any:  # noqa: C901 — intentionally flat dispatch
        """Translate a single blackboard key to perception data."""
        p = self._percept
        s = self._loop_state
        if p is None:
            return None

        # -- Epistemic quadrant (derived from confidence) --
        if key == "epistemic_quadrant":
            c = p.overall_confidence
            if c > 0.7:
                return "KK"
            if c > 0.4:
                return "KU"
            if c > 0.2:
                return "UK"
            return "UU"

        # -- Theory / control --
        if key == "working_theory":
            return True if (p.has_plan or p.map_completeness > 0.5) else None
        if key == "controlled_object":
            return True if len(p.known_effects) > 2 else None

        # -- Threat signals --
        if key == "contradiction_detected":
            return p.surprise > 0.7
        if key == "cascade_failure":
            return False
        if key == "action_budget_critical":
            max_a = s.get("max_actions", 500)
            return p.actions_remaining < max_a * 0.1

        # -- Frame / delta --
        if key == "frame_delta_magnitude":
            eff = p.last_action_effect
            return eff.pixels_changed if eff else 0
        if key == "no_change_frames":
            return p.consecutive_no_change

        # -- Strategy stability --
        if key == "strategy_stability":
            strats = self._recent_strategies
            if len(strats) < 3:
                return 1.0
            recent = strats[-5:]
            same = sum(1 for a, b in zip(recent, recent[1:]) if a == b)
            return same / max(len(recent) - 1, 1)

        # -- Success rate --
        if key == "recent_success_rate":
            if p.actions_taken == 0:
                return 0.5
            base_rate = max(
                0.0,
                1.0 - p.consecutive_no_change / max(p.actions_taken, 1),
            )
            # Penalize monotonous action repetition: repeating the same
            # action isn't "success" even if the frame changes (e.g.
            # walking in one direction forever).  Each repetition past 5
            # reduces the success rate by 10%.
            same_action = getattr(self, '_consecutive_same_action', 0)
            if same_action > 5:
                penalty = min(0.8, (same_action - 5) * 0.10)
                base_rate = max(0.0, base_rate - penalty)
            return base_rate

        # -- Novelty / surprise --
        if key == "novelty_score":
            return p.surprise * 0.5
        if key == "surprise_score":
            return p.surprise
        if key == "pattern_break":
            return p.surprise > 0.5

        # -- Stuck --
        if key == "stuck_detected":
            return p.consecutive_no_change > 5

        # -- Game progress --
        if key == "levels_completed":
            return s.get("levels_completed", 0)
        if key == "total_levels":
            return s.get("total_levels", 6)
        if key == "death_count":
            return 0

        # -- Confidence delta --
        if key == "confidence_delta":
            return p.overall_confidence - self._prev_confidence

        # -- Score delta --
        if key == "score_delta":
            eff = p.last_action_effect
            return eff.score_delta if eff else 0

        # -- Open questions / unknowns --
        if key == "known_unknowns":
            return list(p.unexplored_positions)
        if key == "open_questions":
            return list(p.unexplored_positions)

        # -- Tick / path --
        if key == "current_tick":
            return s.get("actions_taken", 0)
        if key == "recent_path":
            return s.get("recent_path", [])

        return None


class CognitiveLoop:
    """
    Perceive -> Think -> Map -> Act orchestrator.

    Wraps the existing DecisionRungSystem with structured perception
    and causal reasoning. Produces observable CognitiveFrames.
    """

    def __init__(
        self,
        decision_system: Any = None,
        context_builder: Any = None,
        db: Any = None,
        verbose: bool = False,
    ):
        """
        Initialize the cognitive loop.

        Args:
            decision_system: DecisionRungSystem instance (for REASONED speed)
            context_builder: ContextBuilder instance (for backward compat context)
            db: Database interface for loading prior knowledge
            verbose: Print cognitive frames to console
        """
        self._decision_system = decision_system
        self._context_builder = context_builder
        self._db = db
        self._verbose = verbose

        # Core components
        self._perceiver = Perceiver()
        self._causal_map: Optional[CausalMap] = None

        # Phenomenology: blackboard adapter + compression layer
        self._bb_adapter = PerceptualBlackboardAdapter()
        self._phenomenology = PhenomenologyLayer(self._bb_adapter)  # type: ignore[arg-type]

        # Game state
        self._game_id: str = ""
        self._available_actions: List[int] = []
        self._max_actions: int = 500
        self._actions_taken: int = 0
        self._current_level: int = 1
        self._score: float = 0.0

        # Frame tracking
        self._prev_frame: Optional[np.ndarray] = None
        self._consecutive_no_change: int = 0

        # Action repetition tracking (monopoly detection)
        self._last_action_type: Optional[int] = None
        self._consecutive_same_action: int = 0

        # Replay
        self._frames: List[CognitiveFrame] = []
        self._current_frame: Optional[CognitiveFrame] = None

        # Last action info (for temporal perception)
        self._last_action_info: Optional[Dict[str, Any]] = None

        # Prior knowledge state
        self._prior_knowledge_loaded: bool = False
        self._prior_effects_count: int = 0  # How many position effects loaded from DB
        self._prior_rules_count: int = 0    # How many rules loaded from DB

        # ═══ GAP 1: Frame history for stable region detection ═══
        self._frame_history: List[np.ndarray] = []  # Last N frames
        self._stable_mask: Optional[np.ndarray] = None  # Boolean: True = never changed
        self._stable_region_attempts: int = 0  # How many times we've tried (allow retry)
        self._reference_snapshot: Optional[np.ndarray] = None  # Stable pixels snapshot

        # ═══ GAP 2: Goal-delta tracking ═══
        self._last_goal_delta_count: int = 0  # Cells wrong before last action
        self._goal_cells_total: int = 0  # Total goal cells detected

        # ═══ GAP 3: Active plan for execution ═══
        self._active_plan: List[Any] = []
        self._agent_position: Optional[Tuple[int, int]] = None  # For movement games

        # ═══ GAP 5: HUD state tracking ═══
        self._prev_hud_hash: int = 0
        self._hud_edge_size: int = 6  # Pixels from frame edge considered HUD

        # ═══ GAP 5C: Per-region HUD tracking ═══
        self._prev_hud_region_hashes: Dict[str, int] = {
            'top': 0, 'bottom': 0, 'left': 0, 'right': 0
        }
        self._prev_hud_region_states: Dict[str, Dict[str, Any]] = {}
        # Tracks per-region: {hash, unique_colors, colored_fraction, object_count}

        # ═══ SEMANTIC GOAL: Reference panel detection ═══
        self._reference_panel: Optional[Dict[str, Any]] = None
        # {region: (y1,y2,x1,x2), cells: {(x,y): color}, detected_at_action: N}

    # ─── Game Lifecycle ───────────────────────────────────────────────

    def start_game(
        self,
        game_id: str,
        available_actions: List[int],
        max_actions: int = 500,
    ):
        """Initialize for a new game."""
        self._game_id = game_id
        self._available_actions = available_actions
        self._max_actions = max_actions
        self._actions_taken = 0
        self._current_level = 1
        self._score = 0.0
        self._prev_frame = None
        self._consecutive_no_change = 0
        self._last_action_type = None
        self._consecutive_same_action = 0
        self._last_action_info = None
        self._frames = []
        self._current_frame = None

        # Reset gap state
        self._frame_history = []
        self._stable_mask = None
        self._stable_region_attempts = 0
        self._reference_snapshot = None
        self._last_goal_delta_count = 0
        self._goal_cells_total = 0
        self._active_plan = []
        self._agent_position = None
        self._prev_hud_hash = 0
        self._prev_hud_region_hashes = {
            'top': 0, 'bottom': 0, 'left': 0, 'right': 0
        }
        self._prev_hud_region_states = {}
        self._reference_panel = None
        self._productive_rotation_index = 0  # Fix 3: rotate among productive targets

        # ═══ RESET COUNTER (instrumentation pair) + MOVEMENT STACK state ═══
        self._reset_anchor = None        # (shape, bytes) of the anchor board
        self._reset_run = 0              # frame-changing steps since the anchor
        self._reset_ep_count = 0         # resets detected this episode
        self._reset_actions = {}         # action -> times it caused a reset
        self._ep_settled = False         # end_game settle (bump_episode) ran
        self._cursor_agency = None       # first activation: own-avatar map
        self._grid_nav = None            # first activation: BFS traversability
        self._nav_cell = None            # the body's current logical cell
        self._nav_goal_px = None         # abduced-goal site (px x,y) if any
        self._nav_steers = 0             # [NAV] fires this episode (the arm marker)

        # Create fresh causal map for this game
        self._causal_map = CausalMap(game_id=game_id)

        # Reset perceiver
        self._perceiver.reset()

        # Reset phenomenology layer for fresh game
        self._bb_adapter.reset()
        self._phenomenology.reset()

        # Reset prior knowledge state
        self._prior_knowledge_loaded = False
        self._prior_effects_count = 0
        self._prior_rules_count = 0

        # ═══ LOAD PRIOR KNOWLEDGE FROM DATABASE ═══
        # This is the key difference from a blank-slate approach:
        # we seed the causal map with knowledge from prior games,
        # so the agent starts with understanding, not ignorance.
        self._load_prior_knowledge(game_id)

        # Import any existing causal knowledge from context builder
        if self._context_builder is not None:
            try:
                wm = getattr(self._context_builder, '_world_model', None)
                if wm:
                    self._causal_map.import_from_world_model(wm)
            except Exception:
                pass

        if self._verbose:
            print(f"\n[COGNITIVE-LOOP] Game started: {game_id}")
            print(f"    Available actions: {available_actions}")
            print(f"    Budget: {max_actions} actions")
            if self._prior_knowledge_loaded:
                print(
                    f"    Prior knowledge: {self._prior_effects_count} effects, "
                    f"{self._prior_rules_count} rules loaded"
                )
                print(f"    {self._causal_map.summary()}")
            else:
                print("    Prior knowledge: none (first encounter)")

    def end_game(self) -> List[CognitiveFrame]:
        """End the game and return the replay."""
        # ═══ R1 (EGO-STARVE): the episode boundary settles the starvation book ═══
        # PREREG_READOUTS.md: a socket exercised all episode with ZERO passes
        # emits ONE enum-coded record to the PERSONAL "starvation" stream —
        # pure function of the counters (plan gates + mint/bank), narrated,
        # <= 1 per socket per episode (guarded by the settled flag).
        try:
            _sfab = getattr(self, "_ego_fabric", None)
            if _sfab is not None and not getattr(self, "_starve_settled", False):
                from engines.egocentric.starvation import StarvationBook
                _sc = dict(getattr(self, "_plan_gate", None) or {})
                _sc.update(getattr(self, "_w4c_counters", None) or {})
                StarvationBook(_sfab).settle_episode(
                    _sc, game=str(getattr(self, "_game_id", "") or "game"),
                    level=int(getattr(self, "_ego_level", 0) or 0),
                    budget_spent=int(getattr(self, "_actions_taken", 0) or 0))
                self._starve_settled = True
        except Exception:
            _swal(self, "STARVATION")
        # ═══ W1 (CONSUMER DRIVER): the SAME boundary drains the import queue ═══
        # consumer.consume was built (B12) but had NO production call site —
        # the queue never drained at runtime. Once per episode, budgeted:
        # sigma-match the queued residuals against every mounted fabric's
        # atoms; candidates land in import_candidates and the NEXT episode's
        # gamma init seeds them (seed_imports, imported=True).
        try:
            _cofab = getattr(self, "_ego_fabric", None)
            if _cofab is not None and not getattr(self, "_consume_settled", False):
                from engines.egocentric import consumer as _con
                _crep = _con.consume(
                    _cofab, str(getattr(self, "_game_id", "") or "game"),
                    int(getattr(self, "_ego_level", 0) or 0) + 1, budget_n=8)
                self._consume_settled = True
                if _crep.get("drained") or _crep.get("reopened"):
                    print(f"[IMPORT] consumed drained={_crep['drained']} "
                          f"candidates={_crep['candidates']} "
                          f"not_found={_crep['not_found']} "
                          f"declined={_crep.get('declined', 0)} "
                          f"reopened={_crep['reopened']}")
        except Exception:
            _swal(self, "OTHER")
        # ═══ B4 (BUILD_PROGRAM_2 W1): the SAME boundary settles the swallow book ═══
        # <= 1 enum-coded record per guarded block per episode to the PERSONAL
        # "swallow" stream, [SWALLOW]-narrated — a pure function of the counts
        # the instrumented except-branches accrued via _swal.
        try:
            _swfab = getattr(self, "_ego_fabric", None)
            if _swfab is not None and not getattr(self, "_swallow_settled", False):
                from engines.egocentric.swallow import SwallowBook
                SwallowBook(_swfab).settle_episode(
                    getattr(self, "_swallow_counts", None) or {},
                    game=str(getattr(self, "_game_id", "") or "game"),
                    level=int(getattr(self, "_ego_level", 0) or 0))
                self._swallow_settled = True
        except Exception:
            _swal(self, "OTHER")
        # ═══ MAINTAINER'S ORDER: the SAME boundary settles the RESET testimony ═══
        # (instrumentation pair: the counter REPORTS; no selection guard ships
        # until it has) and advances the mint's episode ordinal EXACTLY ONCE
        # (A3-4 bump_episode) so ep stamps are retry-precise across same-level
        # retries the (game, level) context cannot see. Guarded by the settled
        # flag: a double end_game never double-bumps.
        try:
            if not getattr(self, "_ep_settled", False):
                self._ep_settled = True
                _rc = int(getattr(self, "_reset_ep_count", 0) or 0)
                print(f"[RESET] episode resets={_rc} actions="
                      f"{sorted((getattr(self, '_reset_actions', None) or {}).items())}")
                if getattr(self, "_cursor_agency", None) is not None:
                    # the comparison verdict's arm marker: steers>0 episodes
                    # vs steers=0 incumbents, same game+level move books
                    print(f"[NAV] episode steers="
                          f"{int(getattr(self, '_nav_steers', 0) or 0)}")
                _mm = getattr(self, "_mdl_mint", None)
                if _mm is not None:
                    _mm.bump_episode()
        except Exception:
            _swal(self, "OTHER")
        if self._verbose and self._frames:
            print(f"\n[COGNITIVE-LOOP] Game ended: {self._game_id}")
            print(f"    Actions: {self._actions_taken}")
            print(f"    Level: {self._current_level}")
            print(f"    Score: {self._score}")
            if self._causal_map:
                print(f"    {self._causal_map.summary()}")
        return self._frames

    # ─── Prior Knowledge Loading ──────────────────────────────────────

    def _load_prior_knowledge(self, game_id: str):
        """
        Load accumulated knowledge from the database into the causal map.

        This is what makes the system LEARN ACROSS GAMES rather than
        starting from scratch. We load:

        1. World model states — causal maps from prior sessions with
           this same game, containing position-effect mappings that
           were empirically discovered.

        2. Action effectiveness — which actions produce frame changes
           for this game type, so the agent knows what kinds of actions
           are productive before taking its first step.

        3. Game lessons — distilled insights from hundreds of games,
           like "clicking toggles neighbors" or "avoid edges."

        The loaded knowledge seeds the causal map with non-zero
        completeness, which shifts strategy from "explore" (random)
        to "experiment"/"exploit" (rung-system-informed), so the
        cognitive architecture actually gets used.
        """
        if self._db is None:
            return
        if self._causal_map is None:
            return

        import json

        causal_map = self._causal_map  # Local ref for Pylance narrowing
        game_type = game_id[:4] if len(game_id) >= 4 else game_id
        effects_loaded = 0
        rules_loaded = 0

        # ─── 1. Load best causal map from prior sessions ─────────────
        try:
            # First: try exact game_id match (best — same game instance)
            rows = self._db.execute_query("""
                SELECT objects_json FROM world_model_states
                WHERE game_id = ?
                ORDER BY step_number DESC
                LIMIT 1
            """, (game_id,))

            # Second: if no exact match, load from same game TYPE
            # (cross-agent knowledge — other agents who played the
            # same game type, including horizontal transfers)
            if not rows:
                rows = self._db.execute_query("""
                    SELECT objects_json FROM world_model_states
                    WHERE game_id LIKE ?
                    ORDER BY step_number DESC
                    LIMIT 3
                """, (f'{game_type}%',))

            if rows:
                for row_entry in rows:
                    obj_json = row_entry.get('objects_json') if isinstance(row_entry, dict) else row_entry[0]
                    if not obj_json:
                        continue
                    data = json.loads(obj_json)
                    causal_data = data.get('causal_map', {})

                    for pos_key, effect_data in causal_data.items():
                        try:
                            if isinstance(pos_key, str):
                                parts = pos_key.strip('()').split(',')
                                pos = (int(parts[0].strip()), int(parts[1].strip()))
                            elif isinstance(pos_key, tuple):
                                pos = pos_key
                            else:
                                continue

                            # Import into causal map
                            observations = effect_data.get('observations', [])
                            obs_count = effect_data.get('observation_count', 0)
                            productive = effect_data.get('productive_count', 0)
                            destructive = effect_data.get('destructive_count', 0)
                            if observations:
                                # Determine if this position produces changes
                                any_change = any(
                                    len(obs.get('changes', [])) > 0
                                    for obs in observations
                                )
                                affected: list = []
                                # color_transitions must use tuple keys and
                                # list-of-tuple values to match TileEffect's
                                # type: Dict[Tuple[int,int], List[Tuple[int,int]]]
                                color_transitions: dict = {}

                                for obs in observations:
                                    for ch in obs.get('changes', []):
                                        cell = (ch.get('x', 0), ch.get('y', 0))
                                        if cell not in affected:
                                            affected.append(cell)
                                        from_c = ch.get('from_color', 0)
                                        to_c = ch.get('to_color', 0)
                                        if cell not in color_transitions:
                                            color_transitions[cell] = []
                                        color_transitions[cell].append(
                                            (from_c, to_c)
                                        )

                                from engines.cognition.causal_map import TileEffect
                                causal_map._effects[pos] = TileEffect(
                                    position=pos,
                                    affected=affected,
                                    color_transitions=color_transitions,
                                    observation_count=max(len(observations), obs_count),
                                    last_frame_changed=any_change,
                                    productive_count=productive,
                                    destructive_count=destructive,
                                )
                                causal_map._explored.add(pos)
                                causal_map._all_positions.add(pos)
                                effects_loaded += 1

                        except Exception:
                            continue

                    # ── Load color cycles ──
                    color_cycles_data = data.get('color_cycles', {})
                    for pos_key, cycle in color_cycles_data.items():
                        try:
                            if isinstance(pos_key, str):
                                parts = pos_key.strip('()').split(',')
                                pos = (int(parts[0].strip()), int(parts[1].strip()))
                            else:
                                continue
                            if isinstance(cycle, list) and cycle:
                                causal_map._color_cycles[pos] = cycle
                        except Exception:
                            continue

                    # ── Load walls ──
                    walls_data = data.get('walls', [])
                    for wall in walls_data:
                        try:
                            wpos = wall.get('pos', [])
                            wact = wall.get('action', 0)
                            if len(wpos) == 2:
                                causal_map._walls.add(
                                    (tuple(wpos), wact)
                                )
                        except Exception:
                            continue

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] World model load failed: {e}")

        # ─── 2. Load action effectiveness for this game ──────────────
        try:
            rows = self._db.execute_query("""
                SELECT action_number, success_rate, attempts, successes
                FROM action_effectiveness
                WHERE game_id = ?
            """, (game_id,))

            if rows:
                for row in rows:
                    if isinstance(row, dict):
                        action_num = row.get('action_number', 0)
                        success_rate = row.get('success_rate', 0.0)
                    else:
                        action_num = row[0]
                        success_rate = row[1] if len(row) > 1 else 0.0

                    # Store as a rule-like insight
                    if success_rate > 0.5:
                        from engines.cognition.causal_map import CausalRule
                        causal_map._rules.append(CausalRule(
                            rule_type=f"action{action_num}_effective",
                            description=(
                                f"ACTION{action_num} produces frame changes "
                                f"{success_rate:.0%} of the time"
                            ),
                            evidence_count=1,
                            confidence=min(0.8, success_rate),
                        ))
                        rules_loaded += 1

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] Action effectiveness load failed: {e}")

        # ─── 3. Load game lessons ────────────────────────────────────
        try:
            rows = self._db.execute_query("""
                SELECT lesson_text, lesson_type, confidence, key_action
                FROM game_lessons_learned
                WHERE game_type = ? AND confidence > 0.5
                ORDER BY times_retrieved DESC, confidence DESC
                LIMIT 10
            """, (game_type,))

            if rows:
                for row in rows:
                    if isinstance(row, dict):
                        lesson = row.get('lesson_text', '')
                        lesson_type = row.get('lesson_type', 'info')
                        confidence = row.get('confidence', 0.5)
                    else:
                        lesson = row[0] if row else ''
                        lesson_type = row[1] if len(row) > 1 else 'info'
                        confidence = row[2] if len(row) > 2 else 0.5

                    # Store as rules in the causal map
                    from engines.cognition.causal_map import CausalRule
                    causal_map._rules.append(CausalRule(
                        rule_type=f"lesson_{lesson_type}",
                        description=str(lesson)[:200],
                        evidence_count=1,
                        confidence=float(confidence) * 0.7,  # Discount slightly
                    ))
                    rules_loaded += 1

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] Game lessons load failed: {e}")

        # ─── 4. Load death zones as anti-knowledge ───────────────────
        try:
            rows = self._db.execute_query("""
                SELECT x_min, x_max, y_min, y_max, danger_score
                FROM death_zones
                WHERE game_type = ? AND is_active = 1
                ORDER BY danger_score DESC
                LIMIT 20
            """, (game_type,))

            if rows:
                for row in rows:
                    if isinstance(row, dict):
                        x_min = row.get('x_min', 0)
                        x_max = row.get('x_max', 0)
                        y_min = row.get('y_min', 0)
                        y_max = row.get('y_max', 0)
                    else:
                        x_min, x_max, y_min, y_max = row[0], row[1], row[2], row[3]

                    # Mark these positions as explored-and-dangerous
                    for x in range(x_min, x_max + 1):
                        for y in range(y_min, y_max + 1):
                            pos = (x, y)
                            causal_map._explored.add(pos)
                            causal_map._all_positions.add(pos)

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] Death zones load failed: {e}")

        # ─── 5. Cross-game mechanic transfer ─────────────────────────
        # Query ALL learned mechanics from ALL game types. Mechanics
        # from the *same* game type arrive with full confidence.
        # Mechanics from *other* game types arrive discounted — they
        # are hypotheses ("this new game MIGHT work like that one"),
        # not certainties. This is the meta-level transfer path.
        try:
            rows = self._db.execute_query("""
                SELECT game_type, mechanic_type, mechanic_data,
                       observation_count, confidence
                FROM learned_game_mechanics
                WHERE confidence > 0.3
                ORDER BY confidence DESC
                LIMIT 50
            """)

            if rows:
                from engines.cognition.causal_map import CausalRule
                for row in rows:
                    if isinstance(row, dict):
                        src_game = row.get('game_type', '')
                        mech_type = row.get('mechanic_type', '')
                        mech_data = row.get('mechanic_data', '{}')
                        obs_count = row.get('observation_count', 1)
                        confidence = row.get('confidence', 0.3)
                    else:
                        src_game = row[0] if row else ''
                        mech_type = row[1] if len(row) > 1 else ''
                        mech_data = row[2] if len(row) > 2 else '{}'
                        obs_count = row[3] if len(row) > 3 else 1
                        confidence = row[4] if len(row) > 4 else 0.3

                    # Same game type -> full import
                    # Different game type -> heavy discount (hypothesis only)
                    same_game = src_game == game_type
                    weight = float(confidence) if same_game else float(confidence) * 0.25

                    # Skip very weak cross-game signals
                    if weight < 0.1:
                        continue

                    origin_tag = "same-type" if same_game else f"transfer:{src_game}"

                    # Parse mechanic data to surface relevant params
                    try:
                        params = json.loads(mech_data)
                    except Exception:
                        params = {}

                    causal_map._rules.append(CausalRule(
                        rule_type=f"mechanic_{mech_type}",
                        description=(
                            f"[{origin_tag}] Mechanic '{mech_type}' "
                            f"(obs={obs_count})"
                        ),
                        evidence_count=int(obs_count),
                        confidence=weight,
                        parameters=params,
                    ))
                    rules_loaded += 1

        except Exception as e:
            logger.debug(f"[PRIOR-KNOWLEDGE] Cross-game mechanics load failed: {e}")

        # ─── Summary ─────────────────────────────────────────────────
        if effects_loaded > 0 or rules_loaded > 0:
            self._prior_knowledge_loaded = True
            self._prior_effects_count = effects_loaded
            self._prior_rules_count = rules_loaded

    # ─── The Main Loop: Perceive -> Think -> Map -> Act ───────────────

    def cycle(
        self,
        frame: Any,
        obs: Any,
        agent_id: str = "",
        agent_role: str = "pioneer",
        w_A: float = 0.5,
        w_B: float = 0.5,
        available_actions: Optional[List[int]] = None,
        **extra_context,
    ) -> Tuple[int, Optional[Dict], CognitiveFrame]:
        """
        Execute one complete Perceive-Think-Map-Act cycle.

        Args:
            frame: Raw game frame (64x64)
            obs: Full observation object from API
            agent_id: Agent identifier
            agent_role: Agent role
            w_A: Stream A weight
            w_B: Stream B weight
            available_actions: Current available actions from API
                (may change between levels — e.g. FT09 Level 1 has
                [6] only, later levels add [1,2,3,4,5,6]).
            **extra_context: Additional context passed to rung system

        Returns:
            (action_number, action_data, cognitive_frame)
            action_number: 1-7
            action_data: {x, y} for ACTION6, None otherwise
            cognitive_frame: Observable record of this cycle
        """
        # ═══ Per-level action availability update ═══
        # Games can change available_actions between levels (e.g. FT09
        # Level 1 = [6] only, Level 2+ = [1,2,3,4,5,6] with camera pan).
        # Update our internal state when the API reports a change.
        if available_actions and sorted(available_actions) != sorted(self._available_actions):
            old = self._available_actions
            self._available_actions = list(available_actions)
            if self._verbose:
                print(
                    f"    [ACTIONS-UPDATE] Available actions changed: "
                    f"{old} -> {self._available_actions}"
                )
            # Reset stable regions since new actions may change the viewport
            # (e.g. camera pan actions reveal new parts of the board)
            if any(a in available_actions for a in (1, 2, 3, 4)) and not any(a in old for a in (1, 2, 3, 4)):
                self._stable_region_attempts = 0
                self._stable_mask = None
                self._reference_snapshot = None
                self._reference_panel = None
        cf = CognitiveFrame(
            action_number=self._actions_taken,
            timestamp=time.time(),
            level=self._current_level,
        )

        # ═══════════════════════════════════════════════════════════════
        # PHASE 1: PERCEIVE
        # ═══════════════════════════════════════════════════════════════
        percept = self._perceive(frame, cf)

        # ═══════════════════════════════════════════════════════════════
        # PHASE 2: THINK
        # ═══════════════════════════════════════════════════════════════
        strategy, certainty = self._think(percept, cf)

        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: MAP (consult, don't update yet — update after action)
        # ═══════════════════════════════════════════════════════════════
        plan_action = self._consult_map(percept, strategy, cf)

        # ═══════════════════════════════════════════════════════════════
        # PHASE 4: ACT (three speeds)
        # ═══════════════════════════════════════════════════════════════
        action_num, action_data = self._act(
            percept, strategy, certainty, plan_action,
            obs, agent_id, agent_role, w_A, w_B, cf, **extra_context,
        )

        # ═══ PHASE 2 (EGO-GOAL): the ONE pre-empt site — a confirmed goal earns the wheel ═══
        # drive() is None unless a reward CONFIRMED a goal AND an established action helps;
        # None changes NOTHING, ever (the wheel rule, PREREG_PHASE2.md).
        try:
            # PHASE 3a: remember the agent's identity for the knowledge fabric
            self._ego_agent_id = str(agent_id) if agent_id else "agent"
            _spine = getattr(self, "_goal_spine", None)
            _cen = getattr(self, "_ego_prev_centroid", None)
            _ego_drive = None
            if _spine is not None and _cen is not None:
                _self_cell = (int(round(_cen[0])), int(round(_cen[1])))
                _ego_drive = _spine.drive(_self_cell)
                if _ego_drive is not None:
                    action_num = int(_ego_drive)
                    if action_num != 6:
                        action_data = None   # a movement action carries no click coordinates
                    print(f"[EGO-GOAL] DRIVE action={action_num} from={_self_cell}")
            # ═══ PHASE 3b2: movement drive first, then click drive (needs no centroid) ═══
            if _spine is not None and _ego_drive is None:
                _click = _spine.drive_click()
                if _click is not None:
                    action_num = 6
                    action_data = {'x': int(_click[0]), 'y': int(_click[1])}
                    print(f"[EGO-GOAL] DRIVE-CLICK at {_click}")
            # ═══ 3d-i (EGO-FRONTIER): a banked fatal opening vetoes the final click ═══
            # Handoff episodes learn the frontier from the observation (max seen);
            # exploration ORDERING only — the remap never claims a goal.
            self._ego_level = max(int(getattr(self, "_ego_level", 0) or 0),
                                  int(getattr(obs, 'levels_completed', 0) or 0))
            _book = getattr(self, "_ego_frontier_book", None)
            _shape = getattr(self, "_ego_frame_shape", None)
            # B1 (BUILD_PROGRAM_2 W1): level 0 admitted — the CK-1b write was
            # un-gated; the read side now matches (same conservative rules).
            if (_book is not None and _shape is not None and _spine is not None
                    and self._ego_level >= 0 and int(action_num) == 6
                    and action_data and action_data.get('x') is not None
                    and action_data.get('y') is not None):
                _fcell = (int(action_data['x']), int(action_data['y']))
                _h = (getattr(self, "_ego_harvest_cache", None)
                      or {}).get(self._ego_level)
                if _h is not None:
                    # 3d-ii: the harvest veto — a fatal or merged-dead cell is
                    # remapped to the nearest UNTRIED cell (one cumulative sweep)
                    if _fcell in _h["fatal"] or _fcell in _h["dead"]:
                        _re = _spine.remap_to_untried(
                            _fcell, _h["tried"], _h["fatal"], _shape)
                        action_data = {'x': int(_re[0]), 'y': int(_re[1])}
                        print(f"[EGO-FRONTIER] avoid {_fcell} -> {_re} "
                              f"(level={self._ego_level} "
                              f"tried={len(_h['tried'])})")
                else:
                    # 3d-i fallback: no harvest loaded yet — the fatal-opening ban
                    _avoid = _book.avoid_set(
                        str(getattr(self, "_game_id", "") or "game"),
                        self._ego_level)
                    if _fcell in _avoid:
                        _re = _spine.remap_avoided(_fcell, _avoid, _shape)
                        action_data = {'x': int(_re[0]), 'y': int(_re[1])}
                        print(f"[EGO-FRONTIER] avoid {_fcell} -> {_re} "
                              f"(level={self._ego_level} banked={len(_avoid)})")
            # ═══ W4c (EGO-PLAN): the wheel rule in code — a plan DRIVES only on atoms
            # salience-grounded by >= 2 TRANSFERRED settlements (self._atom_verified);
            # anything less is shadow-narrated. A fresh box has no atoms: nothing drives. ═══
            try:
                # PREREG_PLAN_WIRE: per-gate pass counters (narration only) — the
                # [PLAN-GATE] line names the first gate whose count collapses to ~0.
                if not hasattr(self, "_plan_gate"):
                    self._plan_gate = {"g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0,
                                       "g6": 0, "g7": 0, "shadow": 0, "drive": 0,
                                       "cycles": 0}
                _pg = self._plan_gate
                _pg["cycles"] += 1
                if _pg["cycles"] % 200 == 0:
                    print(f"[PLAN-GATE] cyc={_pg['cycles']} g1={_pg['g1']} "
                          f"g2={_pg['g2']} g3={_pg['g3']} g4={_pg['g4']} "
                          f"g5={_pg['g5']} g6={_pg['g6']} g7={_pg['g7']} "
                          f"shadow={_pg['shadow']} drive={_pg['drive']} "
                          f"{__import__('engines.egocentric.planner', fromlist=['gate_summary']).gate_summary()} "
                          f"{__import__('engines.egocentric.effects', fromlist=['none_summary']).none_summary()}")
                _gm = getattr(self, "_gamma", None)
                _rbind = getattr(self, "_role_binder", None)
                _refsnap = getattr(self, "_reference_snapshot", None)
                if _gm is not None and _rbind is not None:
                    _pg["g1"] += 1
                    if _refsnap is not None:
                        _pg["g2"] += 1
                        if int(getattr(self, "_ego_level", 0) or 0) >= 1:
                            _pg["g3"] += 1
                if (_gm is not None and _rbind is not None and _refsnap is not None
                        and int(getattr(self, "_ego_level", 0) or 0) >= 1):
                    # v1 trigger: a REFERENCE-bound class exists AND its region
                    # snapshot is stored; if unavailable, log NOTHING.
                    _ref_bound = any(
                        (_rbind.binding(_kc) or {}).get("slot") == "REFERENCE"
                        for _kc in list(getattr(_rbind, "_evidence", {}) or {}))
                    if _ref_bound:
                        _pg["g4"] += 1
                    _pframe = self._perceiver._to_numpy(frame)
                    if (_ref_bound and _pframe is not None
                            and _pframe.shape == _refsnap.shape):
                        _pg["g5"] += 1
                        _atoms = _gm.fabric.query(
                            "collective", "atoms",
                            where=lambda r: r.get("game") == str(self._game_id))
                        if _atoms:
                            _pg["g6"] += 1
                            from engines.egocentric.discrepancy import compute_d
                            from engines.egocentric.planner import plan_to_identity
                            _d = compute_d(_pframe, _refsnap)
                            _plan = plan_to_identity(
                                _pframe, _refsnap, _gm,
                                game=str(self._game_id),
                                level=int(getattr(self, "_ego_level", 0) or 0) + 1,
                                budget=float(max(
                                    0, self._max_actions - self._actions_taken)),
                                cost_per_action=None)  # L1 LIVE: the books price it
                            if _plan is not None and "cost_per_action" in _plan:
                                # L1 narration -- BOTH values on the line: the
                                # estimate AND the 1.0 constant it replaced.
                                if _plan.get("cost_missing"):
                                    print("[COST] fallback=1.0")
                                else:
                                    print(f"[COST] "
                                          f"est={_plan['cost_per_action']:.2f} "
                                          f"(was 1.0)")
                            if _plan is not None and _plan.get("steps"):
                                _pg["g7"] += 1
                                _av = getattr(self, "_atom_verified", None) or {}
                                # verified = every step atom carries >= 2 TRANSFERRED
                                # settlements (the salience-grounding bar)
                                _verified = all(int(_av.get(_sid, 0)) >= 2
                                                for _sid in _plan["steps"])
                                _site = None
                                if _verified:
                                    _a0 = _gm.get(_plan["steps"][0])
                                    if _a0 is not None and _a0.get("kind") == "EFFECT":
                                        _ctx0 = np.asarray(_a0["context"])
                                        _ph0, _pw0 = _ctx0.shape
                                        _bh0, _bw0 = _pframe.shape[:2]
                                        for _r0 in range(_bh0 - _ph0 + 1):
                                            for _c0 in range(_bw0 - _pw0 + 1):
                                                if (_pframe[_r0:_r0 + _ph0,
                                                            _c0:_c0 + _pw0]
                                                        == _ctx0).all():
                                                    _site = (_c0 + _pw0 // 2,
                                                             _r0 + _ph0 // 2)
                                                    break
                                            if _site is not None:
                                                break
                                # B3 (BUILD_PROGRAM_2 W1): the frontier veto —
                                # a banked fatal/dead target never drives; the
                                # plan falls back to the shadow narration.
                                from engines.egocentric.frontier import plan_veto
                                _fb3 = getattr(self, "_ego_frontier_book", None)
                                _veto = plan_veto(
                                    _site,
                                    (getattr(self, "_ego_harvest_cache", None)
                                     or {}).get(self._ego_level),
                                    avoid=(_fb3.avoid_set(
                                        str(getattr(self, "_game_id", "")
                                            or "game"),
                                        int(getattr(self, "_ego_level", 0) or 0))
                                        if _fb3 is not None else None))
                                if _verified and _site is not None and not _veto:
                                    action_num = 6
                                    action_data = {'x': int(_site[0]),
                                                   'y': int(_site[1])}
                                    _pg["drive"] += 1
                                    print(f"[PLAN] DRIVE steps={len(_plan['steps'])} "
                                          f"site={_site} d={_d.get('differing')}")
                                else:
                                    _pg["shadow"] += 1
                                    print(f"[PLAN] shadow steps={len(_plan['steps'])} "
                                          f"feasible={_plan.get('feasible')} "
                                          f"verified={_verified} veto={_veto} "
                                          f"d={_d.get('differing')}")
                # ═══ G-C (PREREG_FINAL_GAPS): reference first, then ABDUCED ═══
                # The g4=0 episodes get a target: with NO reference snapshot but
                # a credible abduced goal (>= 2 co-occurrences on the collective
                # "goal_hypotheses" stream), plan toward the predicate. The
                # DRIVE gates are UNCHANGED — verified (2x TRANSFERRED per step
                # atom) + site + frontier veto — and anything less is shadow.
                elif (_gm is not None and _rbind is not None and _refsnap is None
                        and getattr(self, "_ego_fabric", None) is not None):
                    _pframe = self._perceiver._to_numpy(frame)
                    if _pframe is not None:
                        from engines.egocentric.goal_abduction import (
                            GoalBook, abduced_plan)
                        if getattr(self, "_goal_book", None) is None:
                            self._goal_book = GoalBook(self._ego_fabric)
                        _fb4 = getattr(self, "_ego_frontier_book", None)
                        _lv4 = int(getattr(self, "_ego_level", 0) or 0)
                        _ap = abduced_plan(
                            _gm, self._goal_book, _pframe,
                            game=str(self._game_id), level=_lv4 + 1,
                            budget=float(max(
                                0, self._max_actions - self._actions_taken)),
                            verified_counts=getattr(self, "_atom_verified",
                                                    None) or {},
                            harvest=(getattr(self, "_ego_harvest_cache", None)
                                     or {}).get(_lv4),
                            avoid=(_fb4.avoid_set(
                                str(getattr(self, "_game_id", "") or "game"),
                                _lv4) if _fb4 is not None else None))
                        if _ap is not None:
                            # [NAV] the abduced predicate's site doubles as the
                            # movement stack's target (px x,y; a steer, only)
                            self._nav_goal_px = _ap.get("site")
                            print(f"[GOAL] plan targets {_ap['sig']} "
                                  f"cred={_ap['credibility']}")
                            if (_ap["verified"] and _ap["site"] is not None
                                    and not _ap["veto"]):
                                action_num = 6
                                action_data = {'x': int(_ap["site"][0]),
                                               'y': int(_ap["site"][1])}
                                _pg["drive"] += 1
                                print(f"[PLAN] DRIVE steps={len(_ap['steps'])} "
                                      f"site={_ap['site']} goal={_ap['sig']}")
                            else:
                                _pg["shadow"] += 1
                                print(f"[PLAN] shadow steps={len(_ap['steps'])} "
                                      f"feasible={_ap['feasible']} "
                                      f"verified={_ap['verified']} "
                                      f"veto={_ap['veto']} goal={_ap['sig']}")
            except Exception:
                _swal(self, "PLANNER")
            # ═══ C33 STEP 1 (EGO-BET): every action carries a bet — commit at choice ═══
            # A prediction family is committed on the FINAL action (after every
            # pre-empt) and settled in record_result. NO CONSUMER in this step:
            # nothing in _think/_act/pre-empt reads the book (containment).
            try:
                _fab = getattr(self, "_ego_fabric", None)
                if _fab is not None:
                    if getattr(self, "_bet_book", None) is None:
                        from engines.egocentric.betting import BetBook
                        self._bet_book = BetBook(
                            _fab,
                            agent_id=str(getattr(self, "_ego_agent_id", "") or "agent"),
                            game=str(getattr(self, "_game_id", "") or "game"))
                        self._bet_transitions = {}  # action -> (before, after) at settle
                    _bframe = self._perceiver._to_numpy(frame)
                    if _bframe is not None:
                        _bact = int(action_num)
                        # paste member: the current frame with the taken action's
                        # LAST observed delta applied (the iced family's anchor)
                        _paste = _bframe.copy()
                        _btr = (getattr(self, "_bet_transitions", None) or {}).get(_bact)
                        if _btr is not None:
                            _lb, _la = _btr
                            if (_lb is not None and _la is not None
                                    and _lb.shape == _paste.shape
                                    and _la.shape == _paste.shape):
                                _dmask = (_la != _lb)
                                _paste[_dmask] = _la[_dmask]
                        # transform member: None until harvest v2 lands the
                        # temporal-transform (the tests allow transform=None)
                        self._bet_book.commit(action=_bact, before=_bframe,
                                              paste=_paste, transform=None)
            except Exception:
                _swal(self, "OTHER")
            # ═══ W4c (EGO-BANK): every capable slot bets the FINAL settled action ═══
            # Committed at choice; settled (and routed) in record_result.
            try:
                _pbk = getattr(self, "_predictor_bank", None)
                if _pbk is not None:
                    _cframe = self._perceiver._to_numpy(frame)
                    if _cframe is not None:
                        _slot_states = {"WORKSPACE": _cframe}
                        # BODY: the ego centroid cell when the binder binds the
                        # controllable's class to BODY — falling back to the mere
                        # existence of a last-known centroid (v1 pragmatics).
                        _cen_b = getattr(self, "_ego_last_known_cen", None)
                        if _cen_b is not None:
                            _slot_states["BODY"] = (int(round(_cen_b[0])),
                                                    int(round(_cen_b[1])))
                        _rb_b = getattr(self, "_role_binder", None)
                        if _rb_b is not None and any(
                                (_rb_b.binding(_kb) or {}).get("slot") == "REFERENCE"
                                for _kb in list(getattr(_rb_b, "_evidence", {}) or {})):
                            # v1: the REFERENCE "region" is still the full frame
                            _slot_states["REFERENCE"] = _cframe
                        self._predictor_bank.commit(_slot_states,
                                                    action=int(action_num))
                        # retain the committed pre-frame: the mint's `before`
                        self._w4c_pre_frame = _cframe.copy()
            except Exception:
                _swal(self, "BANK_SETTLE")
        except Exception:
            _swal(self, "SPINE")

        # Store frame and action info for next cycle
        frame_array = self._perceiver._to_numpy(frame)
        self._prev_frame = frame_array
        # Track action repetition (monopoly detection)
        if self._last_action_type == action_num:
            self._consecutive_same_action += 1
        else:
            self._consecutive_same_action = 0
        self._last_action_type = action_num

        self._last_action_info = {
            'type': action_num,
            'x': action_data.get('x') if action_data else None,
            'y': action_data.get('y') if action_data else None,
            'frame_changed': False,  # Will be updated by record_result
            'score_delta': 0.0,
            'level_changed': False,
            'consecutive_no_change': self._consecutive_no_change,
            'consecutive_same_action': self._consecutive_same_action,
        }

        self._actions_taken += 1
        self._current_frame = cf
        self._frames.append(cf)

        # NOTE: Don't print cf.to_log_line() here — frame_changed is not yet known.
        # The caller should print AFTER calling record_result().

        return action_num, action_data, cf

    def _ego_feed(self, frame, action):
        """Observe-only feed for replayed steps: replayed actions TEACH, never SIGNAL.

        Feeds the egocentric observer and accrues the per-action centroid delta
        map on the goal spine (the same sensing path record_result uses), so a
        post-replay handoff arrives with a named body and an established
        move-map instead of frontier amnesia. Pure by construction: no fabric,
        no seeding, and absolutely no synthetic reward from replayed steps
        (the wheel rule).
        """
        try:
            if getattr(self, "_ego_observer", None) is None:
                from engines.egocentric.observer import EgoObserver
                self._ego_observer = EgoObserver()
            if getattr(self, "_goal_spine", None) is None:
                from engines.egocentric.spine import GoalSpine
                self._goal_spine = GoalSpine()
                self._ego_prev_centroid = None
                self._ego_last_known_cen = None
            info = self._ego_observer.observe(np.asarray(frame), action)
            _cen = info.get('centroid') if isinstance(info, dict) else None
            if _cen is not None:
                self._ego_last_known_cen = _cen
            if _cen is not None and self._ego_prev_centroid is not None:
                _dr = _cen[0] - self._ego_prev_centroid[0]
                _dc = _cen[1] - self._ego_prev_centroid[1]
                self._goal_spine.note_move(
                    str(action), (int(round(_dr)), int(round(_dc))))
            self._ego_prev_centroid = _cen
        except Exception:
            self._ego_feed_errors = getattr(self, "_ego_feed_errors", 0) + 1
            _swal(self, "OBSERVER")

    def bank_replay_levelup(self, game, level, pre, post) -> int:
        """G-C REPLAY SEAM (LINK3_AUDIT addendum): the second — and until now
        missing — route into the abduction bank.

        The cognitive cycle banks a level-up at `_goal_abd`; a level-up reached
        by PREFIX REPLAY never enters that cycle, so link 3 only ever saw the
        transitions the agent achieved WITHOUT goals. This is the sibling of
        `_ego_feed` and carries the same rule: REPLAYED STEPS TEACH, NEVER
        SIGNAL. What crosses here is an OBSERVATION — the pre/post frames the
        environment produced at the boundary — and never the replayed prefix
        itself, so the membrane law (no replay material in a knowledge stream)
        is untouched and no synthetic credit is minted.

        `level` is the NEW levels_completed, matching the cycle's A3-2 PLAYING
        level convention (`_ego_level` post-increment). Returns the number of
        hypotheses banked; containment: 0, never raises into the replay path."""
        return _goal_bank(self, game, level, pre, post)

    def record_result(
        self,
        post_frame: Any,
        frame_changed: bool,
        score_delta: float,
        level_changed: bool,
        new_level: int = 0,
        new_score: float = 0.0,
    ):
        """
        Record the result of the last action.

        This is where MAP gets updated -- we now know what our action DID.
        This closes the loop: the updated map will inform the next PERCEIVE.

        Enhanced with Gap 1-5 cognitive machinery:
        - Gap 1: Frame history for stable region detection
        - Gap 4: Rich action outcome (goal-progress tracking)
        - Gap 4B: Feed goal progress into CausalMap
        - Gap 5: HUD state change detection
        """
        cf = self._current_frame
        if cf is None:
            return

        # Update cognitive frame with result
        cf.frame_changed = frame_changed
        cf.score_delta = score_delta
        cf.level_changed = level_changed

        if frame_changed:
            self._consecutive_no_change = 0
        else:
            self._consecutive_no_change += 1

        # ═══ GAP 1: Update frame history for stable region detection ═══
        post_array = self._perceiver._to_numpy(post_frame)
        if post_array is not None:
            self._frame_history.append(post_array.copy())
            # Keep last 15 frames (enough to detect stable vs changing regions)
            if len(self._frame_history) > 15:
                self._frame_history = self._frame_history[-15:]

            # Compute stable regions: first try at 5 frames, retry at 10 if first attempt
            # failed to find a useful split (e.g. intro animation, camera panning)
            min_frames = 5 if self._stable_region_attempts == 0 else 10
            if (len(self._frame_history) >= min_frames
                    and self._stable_mask is None
                    and self._stable_region_attempts < 2):
                self._compute_stable_regions()

        # ═══ PHASE 1 (EGO): read-only egocentric observation — feeds NOTHING ═══
        # The observer senses (segment/track/contingency) but no decision code reads it.
        try:
            if getattr(self, "_ego_observer", None) is None:
                from engines.egocentric.observer import EgoObserver
                self._ego_observer = EgoObserver()
            _ego_action = (getattr(self, "_last_action_info", None) or {}).get('type', 0)
            info = self._ego_observer.observe(post_array, _ego_action)
            if self._ego_observer.calls % 10 == 0:
                print(f"[EGO] colour={info.get('colour')} objects={info.get('objects')}")
        except Exception:
            _swal(self, "OBSERVER")

        # ═══ PHASE 2 (EGO-GOAL): the goal spine — confirmed reward earns the wheel ═══
        # Accrue the per-action centroid delta map (the means), propose candidate cells
        # (cue-proposes), and on a level-up credit the controllable's cell (reward-disposes).
        # Only spine.drive() — the ONE pre-empt site in cycle() — ever reads this back.
        try:
            if getattr(self, "_goal_spine", None) is None:
                from engines.egocentric.spine import GoalSpine
                self._goal_spine = GoalSpine()
                self._ego_prev_centroid = None
                self._ego_last_known_cen = None  # AMENDMENT 3b3: survives None steps
            # ═══ PHASE 3a: the knowledge fabric — lazy init + SEED once per game ═══
            # Relative root (cwd-scoped: hermetic). Priors feed the spine at an
            # INHERITED price (credibility>=1 opens the gate; below, bias only).
            # Init-once flag: replay-fed episodes still need fabric + seeding.
            if not getattr(self, "_ego_fabric_inited", False):
                try:
                    from engines.egocentric.fabric import KnowledgeFabric
                    _sd = [_s.strip() for _s in os.environ.get(
                        "OURO_FABRIC_SEEDS", "").split(";")
                        if _s.strip() and os.path.isdir(_s.strip())]
                    self._ego_fabric = KnowledgeFabric(
                        "ego_fabric", seeds=_sd,
                        agent_id=str(getattr(self, "_ego_agent_id", "") or "agent"),
                        kin_key="v4")
                    self._ego_seeded = {}          # seeded cell -> prior idea id
                    self._ego_seeded_clicks = {}   # PHASE 3b2: seeded CLICK_AT cell -> prior id
                    self._ego_self_clicks = set()  # PHASE 3b2: self-confirmed CLICK_AT cells
                    _gkey = str(getattr(self, "_game_id", "") or "game")
                    _bonus = self._goal_spine.manager.confirm_bonus
                    _plv = int(getattr(self, "_ego_level", 0) or 0) + 1
                    for _p in self._ego_fabric.priors(_gkey, level=_plv)[:3]:
                        if _p.get("pariah"):
                            continue
                        _pi = _p.get("idea") or {}
                        _pk = _pi.get("kind")
                        if _pk not in ("BE_AT", "CLICK_AT"):
                            continue
                        _pc = _pi.get("cell") or []
                        if len(_pc) != 2:
                            continue
                        _pcell = (int(_pc[0]), int(_pc[1]))
                        _price = _bonus if _p.get("credibility", 0) >= 1 else _bonus * 0.6
                        if _pk == "CLICK_AT":
                            self._goal_spine.seed_confirmed_click(_pcell, price=_price)
                            self._ego_seeded_clicks[_pcell] = _p["id"]
                        else:
                            self._goal_spine.seed_confirmed(_pcell, price=_price)
                            self._ego_seeded[_pcell] = _p["id"]
                    self._ego_seed_level = _plv
                    if self._ego_seeded or self._ego_seeded_clicks:
                        print(f"[EGO-SEED] level={_plv} n="
                              f"{len(self._ego_seeded) + len(self._ego_seeded_clicks)}")
                except Exception:
                    self._ego_fabric = None
                    self._ego_seeded = {}
                    self._ego_seeded_clicks = {}
                    self._ego_self_clicks = set()
                self._ego_fabric_inited = True  # once per game, success or fail
            # hoisted above credit: mints carry the reward's level
            self._ego_level = (int(getattr(self, "_ego_level", 0) or 0)
                               + (1 if level_changed else 0))
            _cen = info.get('centroid') if isinstance(info, dict) else None
            if _cen is not None:
                # AMENDMENT 3b3: retain the last non-None centroid — the level-up
                # frame breaks the pick; attribution needs the pre-transition cell.
                self._ego_last_known_cen = _cen
            if _cen is not None and self._ego_prev_centroid is not None:
                _delta = (int(round(_cen[0] - self._ego_prev_centroid[0])),
                          int(round(_cen[1] - self._ego_prev_centroid[1])))
                self._goal_spine.note_move(str(_ego_action), _delta)
            self._ego_prev_centroid = _cen
            # Candidates: non-self objects, smallest (marker-like) first, cap 5
            _colour = info.get('colour') if isinstance(info, dict) else None
            _objs = list(getattr(self._ego_observer, "_prev_objs", None) or [])
            _objs = [o for o in _objs if _colour is None or _colour not in o.colours]
            _objs.sort(key=lambda o: o.size)
            self._goal_spine.propose(
                (int(round(o.centroid[0])), int(round(o.centroid[1]))) for o in _objs[:5])
            _lai = getattr(self, "_last_action_info", None) or {}
            _ax, _ay = _lai.get('x'), _lai.get('y')
            if level_changed and _cen is not None:
                _cell = (int(round(_cen[0])), int(round(_cen[1])))
                self._goal_spine.credit(_cell)
                print(f"[EGO-GOAL] CONFIRM at {_cell} (level-up credits the market's winner)")
                # ═══ PHASE 3a: MINT on credit — signal only (the wheel rule for memory) ═══
                try:
                    _fab = getattr(self, "_ego_fabric", None)
                    if _fab is not None:
                        _gkey = str(getattr(self, "_game_id", "") or "game")
                        _mi = {"kind": "BE_AT", "cell": [_cell[0], _cell[1]]}
                        _sig = {"type": "level_up"}
                        _id_p = _fab.mint(_mi, game=_gkey, signal=_sig, scope="personal",
                                          level=self._ego_level)
                        _id_c = _fab.mint(_mi, game=_gkey, signal=_sig, scope="collective",
                                          level=self._ego_level)
                        print(f"[EGO-MINT] {_id_p} {_id_c}")
                        # a level-up at a SEEDED cell corroborates the inherited idea
                        _pid = (getattr(self, "_ego_seeded", None) or {}).get(_cell)
                        if _pid is not None:
                            _fab.echo(_pid, by=_fab.agent_id)
                except Exception:
                    pass
            # ═══ AMENDMENT 3b3: NON-DROPPABLE — fall back to the LAST-KNOWN centroid ═══
            # (the body's cell BEFORE the transition — the correct attribution anyway)
            elif level_changed and getattr(self, "_ego_last_known_cen", None) is not None:
                _lkc = self._ego_last_known_cen
                _cell = (int(round(_lkc[0])), int(round(_lkc[1])))
                self._goal_spine.credit(_cell)
                print(f"[EGO-GOAL] CONFIRM at {_cell} (level-up credits the last-known cell)")
                try:
                    _fab = getattr(self, "_ego_fabric", None)
                    if _fab is not None:
                        _gkey = str(getattr(self, "_game_id", "") or "game")
                        _mi = {"kind": "BE_AT", "cell": [_cell[0], _cell[1]]}
                        _sig = {"type": "level_up"}
                        _id_p = _fab.mint(_mi, game=_gkey, signal=_sig, scope="personal",
                                          level=self._ego_level)
                        _id_c = _fab.mint(_mi, game=_gkey, signal=_sig, scope="collective",
                                          level=self._ego_level)
                        print(f"[EGO-MINT] {_id_p} {_id_c}")
                        # a level-up at a SEEDED cell corroborates the inherited idea
                        _pid = (getattr(self, "_ego_seeded", None) or {}).get(_cell)
                        if _pid is not None:
                            _fab.echo(_pid, by=_fab.agent_id)
                except Exception:
                    pass
            # ═══ AMENDMENT 3b3: last resort — a bare LEVEL mint, no spine credit ═══
            # (only when NO cell is attributable at all: no centroid, no last-known,
            #  no click coords — a real level-up must never leave zero trace)
            elif level_changed and (_ax is None or _ay is None):
                try:
                    _fab = getattr(self, "_ego_fabric", None)
                    if _fab is not None:
                        _gkey = str(getattr(self, "_game_id", "") or "game")
                        _mi = {"kind": "LEVEL", "action": int(_lai.get('type') or 0)}
                        _sig = {"type": "level_up"}
                        _id_p = _fab.mint(_mi, game=_gkey, signal=_sig, scope="personal",
                                          level=self._ego_level)
                        _id_c = _fab.mint(_mi, game=_gkey, signal=_sig, scope="collective",
                                          level=self._ego_level)
                        print(f"[EGO-MINT] {_id_p} {_id_c}")
                except Exception:
                    pass
            # ═══ PHASE 3b2: credit the ACTED-ON cell — a click needs no centroid ═══
            if level_changed and _ax is not None and _ay is not None:
                _ccell = (int(_ax), int(_ay))
                self._goal_spine.credit_click(_ccell)
                getattr(self, "_ego_self_clicks", set()).add(_ccell)
                print(f"[EGO-GOAL] CONFIRM-CLICK at {_ccell} (level-up credits the acted-on cell)")
                # MINT on click-credit — same fabric guards as the BE_AT path
                try:
                    _fab = getattr(self, "_ego_fabric", None)
                    if _fab is not None:
                        _gkey = str(getattr(self, "_game_id", "") or "game")
                        _mi = {"kind": "CLICK_AT", "cell": [_ccell[0], _ccell[1]]}
                        _sig = {"type": "level_up"}
                        _id_p = _fab.mint(_mi, game=_gkey, signal=_sig, scope="personal",
                                          level=self._ego_level)
                        _id_c = _fab.mint(_mi, game=_gkey, signal=_sig, scope="collective",
                                          level=self._ego_level)
                        print(f"[EGO-MINT] {_id_p} {_id_c}")
                        # a level-up at a SEEDED click cell corroborates the inherited idea
                        _pid = (getattr(self, "_ego_seeded_clicks", None) or {}).get(_ccell)
                        if _pid is not None:
                            _fab.echo(_pid, by=_fab.agent_id)
                except Exception:
                    pass
            # ═══ W4c (EGO-WIRE): every producer's consumer, named in code ═══
            # Lazy init alongside the fabric: binder/bank/router/mint/gamma/affect/mute.
            try:
                _wfab = getattr(self, "_ego_fabric", None)
                if _wfab is not None and getattr(self, "_gamma", None) is None:
                    from engines.egocentric.binder import RoleBinder
                    from engines.egocentric.bank import PredictorBank
                    from engines.egocentric.router import ResidualRouter
                    from engines.egocentric.mint import MDLMint
                    from engines.egocentric.affect import AffectGains
                    from engines.egocentric.verdicts import MuteHandler
                    from engines.egocentric.effects import Gamma
                    self._gamma = Gamma(_wfab)
                    self._role_binder = RoleBinder()
                    self._predictor_bank = PredictorBank(
                        gamma=self._gamma,
                        game=str(getattr(self, "_game_id", "") or "game"),
                        level=int(getattr(self, "_ego_level", 0) or 0) + 1)
                    self._residual_router = ResidualRouter()
                    self._mdl_mint = MDLMint(self._gamma)
                    self._affect = AffectGains(_wfab)
                    self._mute = MuteHandler()
                    self._atom_verified = _hyd_ver(self)  # A3-1 book-derived
                    # R1: per-episode mint/bank socket counters
                    self._w4c_counters = {"mint_tried": 0, "mint_passed": 0,
                                          "bank_tried": 0, "bank_passed": 0,
                                          "neg_tried": 0, "neg_passed": 0}
                    self._w4c_calls = 0
                    self._w4c_cls_prev = None
                    _seed_imp(self)
            except Exception:
                _swal(self, "FABRIC")
            # W4c-1: FEED THE BINDER — per-step, per-class invariance evidence.
            try:
                _rb = getattr(self, "_role_binder", None)
                if _rb is not None:
                    if level_changed:
                        _rb.on_level_change()  # the maze redraws; bindings re-earn
                        self._w4c_cls_prev = None
                    _w_lai = getattr(self, "_last_action_info", None) or {}
                    _w_act = int(_w_lai.get('type', 0) or 0)
                    _w_x, _w_y = _w_lai.get('x'), _w_lai.get('y')
                    _w_click = (_w_act == 6 and _w_x is not None
                                and _w_y is not None)
                    # CK-2a: the efference copy — cells MY action should change
                    _pmask = (_rb.predicted_change_mask(
                        getattr(self, "_w4c_pre_frame", None), _w_act,
                        (int(_w_y), int(_w_x)),
                        bank=getattr(self, "_predictor_bank", None))
                        if _w_click else set())
                    _now = {}
                    for _wo in (getattr(self._ego_observer, "_prev_objs", None)
                                or []):
                        _now.setdefault(min(_wo.colours), set()).update(_wo.cells)
                    _prevmap = getattr(self, "_w4c_cls_prev", None)
                    if _prevmap is not None and not level_changed:
                        for _wc, _wcells in _now.items():
                            _pcells = _prevmap.get(_wc)
                            if not _pcells or not _wcells:
                                continue
                            _cn = (sum(p[0] for p in _wcells) / len(_wcells),
                                   sum(p[1] for p in _wcells) / len(_wcells))
                            _cp = (sum(p[0] for p in _pcells) / len(_pcells),
                                   sum(p[1] for p in _pcells) / len(_pcells))
                            _moved = (int(round(_cn[0])) != int(round(_cp[0]))
                                      or int(round(_cn[1])) != int(round(_cp[1])))
                            _mut = _wcells != _pcells
                            _neg_feed(self, _mut)  # B6: negative evidence
                            # CK-2a: subtract the efference copy — self-caused
                            # iff the change intersects the predicted mask
                            self._role_binder.observe_attributed(
                                _wc, _w_act, _moved,
                                bool(_w_click and _mut),
                                _pcells ^ _wcells, _pmask, 0)
                    self._w4c_cls_prev = _now
            except Exception:
                _swal(self, "BINDER_FEED")
            # W4c-2: THE BANK settles at result; EVERY settlement routes.
            try:
                _pb = getattr(self, "_predictor_bank", None)
                _rt = getattr(self, "_residual_router", None)
                if _pb is not None and _rt is not None and post_array is not None:
                    _pb.game = str(getattr(self, "_game_id", "") or "game")
                    _pb.level = int(getattr(self, "_ego_level", 0) or 0) + 1
                    _obs_states = {"WORKSPACE": post_array,
                                   "REFERENCE": post_array}
                    _bcen = (getattr(self, "_ego_prev_centroid", None)
                             or getattr(self, "_ego_last_known_cen", None))
                    if _bcen is not None:
                        _obs_states["BODY"] = (int(round(_bcen[0])),
                                               int(round(_bcen[1])))
                    _wexec = int((getattr(self, "_last_action_info", None)
                                  or {}).get('type', 0) or 0)
                    _wpre = getattr(self, "_w4c_pre_frame", None)
                    out = self._predictor_bank.settle(_obs_states)
                    # R1: bank socket counters — a non-REFERENCE bet is a
                    # learned family (REFERENCE's identity bet is free)
                    _wct = getattr(self, "_w4c_counters", None)
                    if _wct is not None:
                        _wct["bank_tried"] += 1
                        if any(_sv.get("bet") and _sk != "REFERENCE"
                               for _sk, _sv in out.items()):
                            _wct["bank_passed"] += 1
                    # F4 n=1 linkage: this step's known-atom bet (id, bin)
                    self._w4c_step_atom = (None, None)
                    for _slot, _stl in out.items():
                        _bin = self._residual_router.route(_slot, _stl)
                        if (_slot == "WORKSPACE"
                                and _stl.get("from_known_atom")
                                and _stl.get("atom_key") is not None):
                            self._w4c_step_atom = (_stl.get("atom_key"), _bin)
                        # the wheel rule's ledger: a TRANSFERRED WORKSPACE
                        # settlement from a known atom verifies WHICH atom bet
                        # (re-scan gamma: whose apply reproduces the post frame)
                        if (_bin == "TRANSFERRED" and _slot == "WORKSPACE"
                                and _stl.get("from_known_atom")
                                and _wpre is not None):
                            from engines.egocentric.effects import (
                                Gamma as _Gm, apply_effect as _apf)
                            for _rec2 in self._gamma.fabric.query(
                                    "collective", _Gm.TOPIC):
                                _at = _rec2.get("atom") or {}
                                if (_at.get("kind") != "EFFECT"
                                        or str(_rec2.get("game")) != _pb.game
                                        or int(_rec2.get("level", -1)) != _pb.level
                                        or int(_at.get("action", -1)) != _wexec):
                                    continue
                                _pr2 = _apf(_at, np.asarray(_wpre))
                                if (_pr2 is not None
                                        and _pr2.shape == post_array.shape
                                        and bool((_pr2 == post_array).all())):
                                    _aid2 = _rec2.get("id")
                                    self._atom_verified[_aid2] = (
                                        self._atom_verified.get(_aid2, 0) + 1)
                                    break
            except Exception:
                _swal(self, "BANK_SETTLE")
            _goal_abd(self, level_changed, post_array)  # G-C: bank the level-up delta
            # W4c-3: THE MINT — bar-gated by affect (picky when desperate).
            try:
                _rt = getattr(self, "_residual_router", None)
                _aff = getattr(self, "_affect", None)
                if (getattr(self, "_mdl_mint", None) is not None
                        and _rt is not None and _aff is not None):
                    _bar = float(_aff.gains()["mint_bar"])
                    # R1: mint socket counters ride every offer below (readout
                    # only — no verdict, bar, or support is touched)
                    _wct = getattr(self, "_w4c_counters", None)
                    _wpre = getattr(self, "_w4c_pre_frame", None)
                    _wexec = int((getattr(self, "_last_action_info", None)
                                  or {}).get('type', 0) or 0)
                    # MINT BOOTSTRAP: with an empty Gamma, BROKEN-mechanism can
                    # never fire (it needs a KNOWN atom to be wrong), so every
                    # residual routes NOVEL and the mint starves. NOVEL WORKSPACE
                    # evidence is the mint's first meal, offered under the SAME
                    # bar; the mint's guards (SUPPORT x NOVELTY x MDL) filter.
                    # Peek only -- W4c-4 still persists these to the fabric.
                    for _wit in list(_rt.import_queue):
                        if (_wit.get("slot") == "WORKSPACE"
                                and float(_wit.get("residual", 0.0)) >= _bar
                                and _wpre is not None
                                and post_array is not None):
                            _wv = self._mdl_mint.consider(
                                before=_wpre, action=_wexec, after=post_array,
                                game=str(getattr(self, "_game_id", "") or "game"),
                                level=int(getattr(self, "_ego_level", 0) or 0) + 1)
                            if _wct is not None:
                                _wct["mint_tried"] += 1
                                _wct["mint_passed"] += (
                                    1 if _wv.get("verdict") == "mint" else 0)
                            print(f"[MINT] verdict={_wv.get('verdict')} "
                                  f"id={_wv.get('id')} (NOVEL bootstrap)")
                    while _rt.mint_queue:
                        _wit = _rt.mint_queue.pop(0)
                        if (float(_wit.get("residual", 0.0)) >= _bar
                                and _wpre is not None
                                and post_array is not None):
                            _wv = self._mdl_mint.consider(
                                before=_wpre, action=_wexec, after=post_array,
                                game=str(getattr(self, "_game_id", "") or "game"),
                                level=int(getattr(self, "_ego_level", 0) or 0) + 1)
                            if _wct is not None:
                                _wct["mint_tried"] += 1
                                _wct["mint_passed"] += (
                                    1 if _wv.get("verdict") == "mint" else 0)
                            print(f"[MINT] verdict={_wv.get('verdict')} "
                                  f"id={_wv.get('id')}")
                        # below the bar: dropped — desperation makes the
                        # mint pickier, never looser
                    # PRIMAL path: a click that CHANGED the frame is offered
                    # to the mint DIRECTLY — no routing, no bet (WORKSPACE
                    # cannot bet with an empty Gamma, so the starvation moved
                    # one link up). NOVELTY dedups repeats, MDL filters junk;
                    # the SAME bar gates, with changed-cell count as residual.
                    _wlai = getattr(self, "_last_action_info", None) or {}
                    if (frame_changed and _wlai.get('x') is not None
                            and _wlai.get('y') is not None
                            and _wpre is not None and post_array is not None):
                        _wpa = np.asarray(_wpre)
                        _wres = (float((_wpa != post_array).sum())
                                 if _wpa.shape == post_array.shape
                                 else float(post_array.size))
                        if _wres >= _bar:
                            _wv = self._mdl_mint.consider(
                                before=_wpre, action=_wexec, after=post_array,
                                game=str(getattr(self, "_game_id", "") or "game"),
                                level=int(getattr(self, "_ego_level", 0) or 0) + 1)
                            if _wct is not None:
                                _wct["mint_tried"] += 1
                                _wct["mint_passed"] += (
                                    1 if _wv.get("verdict") == "mint" else 0)
                            print(f"[MINT] verdict={_wv.get('verdict')} "
                                  f"id={_wv.get('id')} (primal)")
            except Exception:
                _swal(self, "MINT_DRAIN")
            # W4c-4: NOVEL items persist — the endogenous agenda stays visible.
            # Fig 9: a residual is CHARACTERIZED, not named — with before/after
            # in hand the record also carries sigma (the enqueue-time
            # description, the priority condition) + bounded bbox patches
            # (consumer.characterize; oversized regions keep sigma only).
            try:
                _rt = getattr(self, "_residual_router", None)
                _wfab = getattr(self, "_ego_fabric", None)
                if _rt is not None and _wfab is not None:
                    from engines.egocentric import consumer as _con9
                    _wpre = getattr(self, "_w4c_pre_frame", None)
                    while _rt.import_queue:
                        _wit = _rt.import_queue.pop(0)
                        # A3-2 CONVENTION (PLAYING level): import_queue records
                        # carry game (full-id grain) + the level being played.
                        _wrec = {"slot": _wit.get("slot"),
                                 "residual": float(_wit.get("residual", 0.0)),
                                 "game": str(getattr(self, "_game_id", "")
                                             or "game"),
                                 "level": int(getattr(self, "_ego_level", 0)
                                              or 0) + 1}
                        if _wpre is not None and post_array is not None:
                            _wrec.update(_con9.characterize(
                                _wpre, post_array, slot=_wrec["slot"],
                                residual=_wrec["residual"]))
                        _wfab.append("collective", "import_queue", _wrec)
            except Exception:
                _swal(self, "MINT_DRAIN")
            # W4c-6: AFFECT NARRATES — no channel moves without the state emitted.
            # B5 (BUILD_PROGRAM_2 W1): the SEED-BIAS consumption site — the
            # APPLIED bias (seed_gain: starvation+swallow-widened, bounded,
            # multiplicative) feeds the explore rotation and rides the line.
            try:
                if getattr(self, "_affect", None) is not None:
                    self._w4c_calls = int(getattr(self, "_w4c_calls", 0)) + 1
                    _sg = self._affect.seed_gain(
                        str(getattr(self, "_game_id", "") or "game"))
                    self._ego_explore_widen = float(_sg["boost"])
                    if self._w4c_calls % 25 == 0:
                        print("[AFFECT] " + self._affect.narrate()
                              + " seed_applied=%.4f widen=%.2f"
                              % (_sg["applied"], _sg["boost"]))
            except Exception:
                _swal(self, "AFFECT")
            # ═══ PHASE 3a: FALSIFY write-back — a seeded cell reached WITHOUT reward ═══
            _seeded = getattr(self, "_ego_seeded", None)
            if _seeded and not level_changed and _cen is not None:
                _cur = (int(round(_cen[0])), int(round(_cen[1])))
                _pid = _seeded.get(_cur)
                if _pid is not None:
                    try:
                        _fab = getattr(self, "_ego_fabric", None)
                        if _fab is not None:
                            _fab.falsify(_pid, by=_fab.agent_id)
                        self._goal_spine.demote_inherited(_cur)
                        del _seeded[_cur]
                        print("[EGO-GOAL] falsified inherited")
                    except Exception:
                        pass
            # ═══ PHASE 3b2: click falsify write-back — clicked WITHOUT reward closes it ═══
            if not level_changed and _ax is not None and _ay is not None:
                _ccell = (int(_ax), int(_ay))
                _sclk = getattr(self, "_ego_seeded_clicks", None)
                if _sclk and _ccell in _sclk:
                    try:
                        _fab = getattr(self, "_ego_fabric", None)
                        if _fab is not None:
                            _fab.falsify(_sclk[_ccell], by=_fab.agent_id)
                        self._goal_spine.demote_inherited_click(_ccell)
                        del _sclk[_ccell]
                        print("[EGO-GOAL] falsified inherited click")
                    except Exception:
                        pass
                elif _ccell in (getattr(self, "_ego_self_clicks", None) or set()):
                    # a SELF-confirmed click that failed on re-click: demote, don't falsify
                    self._goal_spine.demote_inherited_click(_ccell)
                    self._ego_self_clicks.discard(_ccell)
                    print("[EGO-GOAL] demoted self-confirmed click (no reward)")
            # ═══ W4c-7 (EGO-MUTE): a seeded goal demoted by the falsify path is MUTE —
            # the ground said nothing; quarantine the prior and answer with the
            # empowerment probe (least-observed untried cell from the harvest). ═══
            try:
                if getattr(self, "_mute", None) is not None:
                    _cur_ids = (
                        set((getattr(self, "_ego_seeded", None) or {}).values())
                        | set((getattr(self, "_ego_seeded_clicks", None)
                               or {}).values()))
                    _prev_ids = getattr(self, "_w4c_seed_ids", None)
                    _slv_now = getattr(self, "_ego_seed_level", None)
                    if (_prev_ids is not None and not level_changed
                            and _slv_now == getattr(self, "_w4c_seed_lvl", None)):
                        for _mid in sorted(_prev_ids - _cur_ids):
                            _hh = getattr(self, "_ego_harvest", None) or {}
                            _tried2 = _hh.get("tried") or set()
                            _shape3 = (getattr(self, "_ego_frame_shape", None)
                                       or (64, 64))
                            # R1 CONSUMER (one-currency law): the agent's own
                            # starvation records STEER exploration effort —
                            # a bounded multiplicative widening of the probe's
                            # candidate budget. Never a bar/support/price.
                            _scap = 5
                            try:
                                _aff3 = getattr(self, "_affect", None)
                                if _aff3 is not None:
                                    _scap = int(round(5 * float(
                                        _aff3.starvation_steer(
                                            str(getattr(self, "_game_id", "")
                                                or "game"))["explore_boost"])))
                            except Exception:
                                _scap = 5
                            _cands = []  # untried cells from the harvest
                            for _my in range(4, int(_shape3[0]), 8):
                                for _mx in range(4, int(_shape3[1]), 8):
                                    if len(_cands) >= _scap:
                                        break
                                    if (_mx, _my) not in _tried2:
                                        _cands.append((_mx, _my))
                                if len(_cands) >= _scap:
                                    break
                            _pv = self._mute.mute(
                                item={"id": _mid, "kind": "objective"},
                                candidates=_cands,
                                observed_counts={_cc: 0 for _cc in _cands})
                            # no explore-aim variable exists yet: log the probe
                            print(f"[MUTE] probe={_pv.get('probe')} item={_mid}")
                    self._w4c_seed_ids = _cur_ids
                    self._w4c_seed_lvl = _slv_now
            except Exception:
                _swal(self, "OTHER")
            # ═══ 3d-i (EGO-FRONTIER): frontier level + first post-frontier click ═══
            # Per-episode by construction (the loop instance is per-episode).
            # The fatal-opening book rides the fabric (lazy, once per episode).
            if not hasattr(self, "_ego_frontier_book"):
                try:
                    from engines.egocentric.frontier import FrontierBook
                    _fab = getattr(self, "_ego_fabric", None)
                    self._ego_frontier_book = (
                        FrontierBook(_fab) if _fab is not None else None)
                except Exception:
                    self._ego_frontier_book = None
                    _swal(self, "FRONTIER")
                # 3d-ii: per-episode harvest material (banked at episode end)
                self._ego_frontier_dead = []      # frontier clicks with NO effect
                self._ego_frontier_effects = []   # frontier clicks that changed the frame
            if post_array is not None:
                self._ego_frame_shape = post_array.shape[:2]
            # ═══ LEVEL-SCOPED IDEAS: RE-SEED on level change ═══
            # The playing level is levels_completed + 1; whenever it drifts from
            # the seeded level (live increment above, OR the obs-based max in
            # cycle() on a handoff), demote the previous level's inherited seeds
            # (their gate closes; pariah status untouched) and reload priors
            # scoped to the level now being played. Runs AFTER the credit
            # branches so a level-up at a seeded cell still echoes its prior.
            try:
                _fab = getattr(self, "_ego_fabric", None)
                _plv = self._ego_level + 1
                if (_fab is not None
                        and getattr(self, "_ego_seed_level", None) != _plv):
                    for _dc in list(getattr(self, "_ego_seeded", None) or {}):
                        self._goal_spine.demote_inherited(_dc)
                    for _dc in list(getattr(self, "_ego_seeded_clicks", None)
                                    or {}):
                        self._goal_spine.demote_inherited_click(_dc)
                    self._ego_seeded = {}
                    self._ego_seeded_clicks = {}
                    _gkey = str(getattr(self, "_game_id", "") or "game")
                    _bonus = self._goal_spine.manager.confirm_bonus
                    for _p in _fab.priors(_gkey, level=_plv)[:3]:
                        if _p.get("pariah"):
                            continue
                        _pi = _p.get("idea") or {}
                        _pk = _pi.get("kind")
                        if _pk not in ("BE_AT", "CLICK_AT"):
                            continue
                        _pc = _pi.get("cell") or []
                        if len(_pc) != 2:
                            continue
                        _pcell = (int(_pc[0]), int(_pc[1]))
                        _price = (_bonus if _p.get("credibility", 0) >= 1
                                  else _bonus * 0.6)
                        if _pk == "CLICK_AT":
                            self._goal_spine.seed_confirmed_click(
                                _pcell, price=_price)
                            self._ego_seeded_clicks[_pcell] = _p["id"]
                        else:
                            self._goal_spine.seed_confirmed(_pcell, price=_price)
                            self._ego_seeded[_pcell] = _p["id"]
                    self._ego_seed_level = _plv
                    print(f"[EGO-SEED] level={_plv} n="
                          f"{len(self._ego_seeded) + len(self._ego_seeded_clicks)}")
            except Exception:
                _swal(self, "FABRIC")
            # The FIRST click made AT the frontier (not the one that opened it):
            # a level-up step's click belongs to the level below, so it is skipped.
            if (not level_changed and self._ego_level >= 1
                    and getattr(self, "_ego_first_frontier_click", None) is None
                    and _ax is not None and _ay is not None):
                self._ego_first_frontier_click = (int(_ax), int(_ay))
            # ═══ 3d-ii (EGO-FRONTIER): accrue the harvest material ═══
            # Every click is an OBSERVATION — effectful or dead — banked at
            # episode end. CK-1b (PREREG_CK_WAVE1.md): level 0 accrues too —
            # the affordance harvest is un-gated from the frontier (18 level-0
            # games banked nothing across 48-112 episodes each). A level-up
            # step's click belongs to the level below, so it is skipped (the
            # same convention as the first-frontier click).
            if (not level_changed
                    and _ax is not None and _ay is not None):
                (self._ego_frontier_effects if frame_changed
                 else self._ego_frontier_dead).append((int(_ax), int(_ay)))
            # ═══ 3d-ii (EGO-FRONTIER): consume the population harvest, ONCE per level ═══
            # deltas pre-establish the spine's move-map (means, not signal — drive still
            # requires a confirmed goal); dead/fatal/tried feed the pre-empt veto.
            # B1 (BUILD_PROGRAM_2 W1): _ego_level >= 0 — level-0 records load
            # too (18 level-0 games banked harvests nobody consumed); the
            # conservative >=2-report dead rule lives in load_harvest itself.
            # A3-2 CONVENTION (COMPLETED level): frontier streams (harvest /
            # fatal openings / moves) are keyed by bare _ego_level -- the level
            # already completed, where the banked experience was earned.
            if self._ego_frontier_book is not None and self._ego_level >= 0:
                if not hasattr(self, "_ego_harvest_cache"):
                    self._ego_harvest_cache = {}
                if self._ego_level not in self._ego_harvest_cache:
                    _h = self._ego_frontier_book.load_harvest(
                        str(getattr(self, "_game_id", "") or "game"),
                        self._ego_level)
                    self._ego_harvest_cache[self._ego_level] = _h
                    for _ha, _hd in _h["deltas"].items():
                        for _ in range(self._goal_spine.min_evidence):
                            self._goal_spine.note_move(str(_ha), _hd)
                    print(f"[EGO-FRONTIER] harvest loaded level={self._ego_level} "
                          f"dead={len(_h['dead'])} effects={len(_h['effects'])} "
                          f"fatal={len(_h['fatal'])} tried={len(_h['tried'])} "
                          f"deltas={len(_h['deltas'])}")
                self._ego_harvest = self._ego_harvest_cache[self._ego_level]
            # ═══ C33 STEP 1 (EGO-BET): settle the pending bet in the result path ═══
            # Settled against the EXECUTED action's frame; committed != executed is
            # VOID (nothing priced) but the executed transition is recorded either
            # way — it feeds the NEXT commit's paste member, never a decision.
            try:
                _bb = getattr(self, "_bet_book", None)
                if (_bb is not None and getattr(_bb, "pending", None) is not None
                        and post_array is not None):
                    # A3-2 CONVENTION (PLAYING level): settlements carry the
                    # level being played (_ego_level + 1) -- registered with
                    # atoms/mint_verdicts/import*/goal_hypotheses; the frontier
                    # streams alone carry the COMPLETED level. A3-1's hydrator
                    # (_hyd_ver) reads this back at the same grain.
                    _bb.level = int(getattr(self, "_ego_level", 0) or 0) + 1
                    _bexec = int((getattr(self, "_last_action_info", None)
                                  or {}).get('type', 0) or 0)
                    _bbefore = _bb.pending.get("before")
                    # F4: thread this step's known-atom bet (id + bin) from the
                    # bank settle above into the settlement record; consume it
                    # so a stale key never rides a later settle.
                    _wsa = getattr(self, "_w4c_step_atom", None) or (None, None)
                    self._w4c_step_atom = (None, None)
                    _bout = _bb.settle(post=post_array, executed_action=_bexec,
                                       atom_key=_wsa[0], atom_bin=_wsa[1])
                    if _bout is not None and _bbefore is not None:
                        if not hasattr(self, "_bet_transitions"):
                            self._bet_transitions = {}
                        self._bet_transitions[_bexec] = (_bbefore, post_array.copy())
                    if _bout is not None and _bb.settled % 25 == 0:
                        print(f"[BET] settles={_bb.settled} voids={_bb.voided} "
                              f"actions={len(_bb.records)} errors={_bb.errors}")
            except Exception:
                _swal(self, "BANK_SETTLE")
            if self._ego_observer.calls % 25 == 0:
                print(f"[EGO-GOAL] confirmed={self._goal_spine.has_confirmed()} "
                      f"candidates={len(self._goal_spine.manager.price)} "
                      f"established={sorted(self._goal_spine.established())}")
        except Exception:
            _swal(self, "SPINE")

        # ═══ MOVEMENT STACK (FIRST ACTIVATION, rung 0c): CursorAgency + GridNav ═══
        # CursorAgency learns the own-avatar displacement map from REAL move
        # outcomes (pre/post frames + the executed action); GridNav builds
        # directed-edge traversability from that map + the observed frames.
        # Consumed ONLY by the [NAV] steer in _act (a capped bias, wheel rule).
        # House containment: never raises; compact site.
        try:
            _mvact = int((getattr(self, "_last_action_info", None)
                          or {}).get('type', 0) or 0)
            _mvpre = getattr(self, "_prev_frame", None)
            if level_changed and getattr(self, "_grid_nav", None) is not None:
                from engines.egocentric.navigation import GridNav
                self._grid_nav = GridNav()   # the maze redraws: walls re-earn
                self._nav_cell = None
            if (_mvact in (1, 2, 3, 4, 5) and not level_changed
                    and _mvpre is not None and post_array is not None
                    and getattr(_mvpre, "shape", None) == post_array.shape):
                if getattr(self, "_cursor_agency", None) is None:
                    from engines.egocentric.agency import CursorAgency
                    from engines.egocentric.navigation import GridNav
                    self._cursor_agency = CursorAgency()
                    self._grid_nav = GridNav()
                    self._nav_cell = None
                _ag = self._cursor_agency
                _ag.observe(_mvpre, str(_mvact), post_array)
                if _ag.ready():
                    _st = int(_ag.stride() or 1) or 1
                    _p0 = _ag.locate(_mvpre)
                    _p1 = _ag.locate(post_array)
                    _sh = _ag.predict(str(_mvact))
                    if _p0 is not None and _p1 is not None:
                        _cl0 = (int(round(_p0[0] / _st)),
                                int(round(_p0[1] / _st)))
                        _cl1 = (int(round(_p1[0] / _st)),
                                int(round(_p1[1] / _st)))
                        if _sh is not None:
                            self._grid_nav.observe_move(_cl0, _sh, _cl1 != _cl0)
                            self._grid_nav.decay()
                        self._nav_cell = _cl1
        except Exception:
            _swal(self, "OTHER")

        # ═══ RESET COUNTER (maintainer's order, part a — instrumentation) ═══
        # A board reverting to the episode/level ANCHOR frame after a solid run
        # (>= RESET_MIN_RUN frame-changing steps) is a RESET: counted,
        # attributed to the executed action, narrated [RESET]; the end_game
        # settle line testifies the count. INSTRUMENTATION ONLY — the counter
        # REPORTS; any selection guard enters singly, later, after the books
        # read. Returning to the anchor WITHOUT a solid run is ordinary
        # back-and-forth and counts nothing.
        try:
            if post_array is not None:
                _rsig = (post_array.shape, post_array.tobytes())
                if getattr(self, "_reset_anchor", None) is None:
                    _rpre = getattr(self, "_prev_frame", None)
                    self._reset_anchor = ((_rpre.shape, _rpre.tobytes())
                                          if _rpre is not None else _rsig)
                if level_changed:
                    self._reset_anchor = _rsig   # the new level's start board
                    self._reset_run = 0
                elif _rsig == self._reset_anchor:
                    if int(getattr(self, "_reset_run", 0)) >= RESET_MIN_RUN:
                        self._reset_ep_count = int(
                            getattr(self, "_reset_ep_count", 0) or 0) + 1
                        _rsa = int((getattr(self, "_last_action_info", None)
                                    or {}).get('type', 0) or 0)
                        _rd = getattr(self, "_reset_actions", None)
                        if _rd is None:
                            _rd = self._reset_actions = {}
                        _rd[_rsa] = int(_rd.get(_rsa, 0)) + 1
                        print(f"[RESET] detected action={_rsa} "
                              f"resets={self._reset_ep_count} "
                              f"run={self._reset_run}")
                    self._reset_run = 0
                elif frame_changed:
                    self._reset_run = int(getattr(self, "_reset_run", 0)) + 1
        except Exception:
            _swal(self, "OTHER")

        # ═══ GAP 4: Rich action outcome computation ═══
        self._compute_rich_outcome(cf, post_array)

        # ═══ GAP 5: HUD state tracking ═══
        self._check_hud_state(cf, post_array)

        # ═══ GAP 5B: Feed HUD changes into CausalMap ═══
        # If the HUD changed after this action, record the association
        # so the system learns which actions affect environmental state.
        if cf.hud_state_changed and self._causal_map and self._last_action_info:
            action_pos = None
            if self._last_action_info.get('x') is not None:
                action_pos = (self._last_action_info['x'], self._last_action_info['y'])
            self._causal_map.record_hud_change(
                action_pos=action_pos,
                action_type=self._last_action_info.get('type', 0),
                _timer_urgency=cf.timer_urgency,
            )

        # Calculate surprise using the CausalMap's prediction system
        if self._causal_map and self._last_action_info:
            click_pos = None
            if self._last_action_info.get('x') is not None:
                click_pos = (self._last_action_info['x'], self._last_action_info['y'])

            if click_pos:
                prediction = self._causal_map.predict(click_pos)
                if prediction is not None:
                    # We had a prediction -- how surprising is the result?
                    if prediction.confidence > 0.5:
                        expected_change = len(prediction.expected_affected) > 0
                        if expected_change == frame_changed:
                            cf.surprise = 0.1  # As expected
                        else:
                            cf.surprise = 0.8  # Surprising!
                    else:
                        cf.surprise = 0.4  # Low-confidence prediction
                else:
                    cf.surprise = 0.5  # No prediction, moderate surprise
            else:
                cf.surprise = 0.3  # Non-click action

        # ═══ MAP UPDATE: Learn from the action's consequence ═══
        if self._causal_map and self._last_action_info:
            click_x = self._last_action_info.get('x')
            click_y = self._last_action_info.get('y')
            action_type = self._last_action_info.get('type', 0)

            # ═══ CONTEXT TRACKING: Record every action type ═══
            # This feeds the prediction-surprise system. Non-click
            # actions (pans, movements) are the CONTEXT that explains
            # why click effects change. Must record ALL actions.
            self._causal_map.record_action_context(action_type)

            # ═══ TEMPORAL CAUSAL LEARNING: Feed frame to delayed observers ═══
            # Every frame is fed into active delayed observation windows,
            # regardless of what action was just taken. This lets us detect
            # effects that unfold over multiple frames (VC33 fluid dynamics).
            if post_array is not None and self._causal_map.has_active_delayed_observations:
                self._causal_map.observe_delayed_frame(post_array)

            if click_x is not None and click_y is not None:
                pre = self._prev_frame
                post = post_array

                self._causal_map.update_from_action(
                    click_pos=(click_x, click_y),
                    pre_frame=pre,
                    post_frame=post,
                    frame_changed=frame_changed,
                )

                # ═══ GAP 2A: Feed abstract state to CausalMap ═══
                # Keep CausalMap aware of current cell states for planning
                if post is not None:
                    abstract_state = self._abstract_frame_state(post)
                    if abstract_state:
                        self._causal_map.set_current_state(abstract_state)

                # ═══ TEMPORAL CAUSAL LEARNING: Start delayed observation ═══
                # For click-only games (likely VC33), start watching for
                # delayed effects that unfold over subsequent frames.
                # Only for click actions that DIDN'T produce immediate change.
                is_click_only_game = (
                    6 in self._available_actions
                    and not any(a in self._available_actions for a in (1, 2, 3, 4))
                )
                if is_click_only_game and post is not None:
                    # Start delayed observation for EVERY click in click-only games
                    # because even "immediate" changes may have delayed secondary effects
                    self._causal_map.start_delayed_observation(
                        action_pos=(click_x, click_y),
                        action_type=action_type,
                        frame_at_action=post,
                        window_size=5,
                    )

                # ═══ GAP 4B: Feed goal progress into CausalMap ═══
                if cf.goal_progress_delta != 0 or cf.was_productive or cf.was_destructive:
                    self._causal_map.record_goal_progress(
                        click_pos=(click_x, click_y),
                        goal_delta_before=cf.goal_delta_before,
                        goal_delta_after=cf.goal_delta_after,
                    )

                cf.map_update = f"Recorded effect at ({click_x},{click_y})"
                if not frame_changed:
                    cf.map_update += " [no effect]"
                elif cf.was_productive:
                    cf.map_update += f" [PRODUCTIVE +{cf.goal_progress_delta}]"
                elif cf.was_destructive:
                    cf.map_update += f" [destructive {cf.goal_progress_delta}]"

                # Update map summary
                cf.map_completeness = self._causal_map.completeness
                cf.effects_known = len(self._causal_map._effects)
                cf.positions_explored = len(self._causal_map._explored)
                cf.map_summary = self._causal_map.summary()

            # ═══ GAP 3C: Track movement results for directional games ═══
            elif action_type in (1, 2, 3, 4) and post_array is not None:
                # ═══ CAMERA-PAN DETECTION ═══
                # For hybrid games (FT09): directional actions may PAN
                # the camera rather than move an agent. A pan shifts >80%
                # of pixels uniformly. Detect this to avoid misclassifying
                # a pan as agent movement.
                is_hybrid = (6 in self._available_actions
                             and any(a in self._available_actions for a in (1, 2, 3, 4)))
                detected_pan = False

                if is_hybrid and self._prev_frame is not None:
                    try:
                        if self._prev_frame.shape == post_array.shape:
                            diff_mask = self._prev_frame != post_array
                            total_px = diff_mask.size
                            changed_px = int(diff_mask.sum())
                            # Pan: >80% of pixels changed (whole viewport shifted)
                            if total_px > 0 and changed_px / total_px > 0.80:
                                detected_pan = True
                                cf.map_update = (
                                    f"Camera pan via ACTION{action_type}"
                                    f" ({changed_px}/{total_px} px changed)"
                                )
                                # Reset stable regions since the viewport changed
                                self._stable_region_attempts = 0
                                self._stable_mask = None
                                self._reference_snapshot = None
                    except Exception:
                        pass

                if not detected_pan:
                    # Directional action -- detect agent movement
                    new_agent_pos = self._detect_agent_position(post_array)
                    if new_agent_pos is not None:
                        self._causal_map.record_movement_result(
                            action_type=action_type,
                            agent_pos_before=self._agent_position,
                            agent_pos_after=new_agent_pos,
                        )
                        if self._agent_position != new_agent_pos:
                            cf.map_update = f"Moved to ({new_agent_pos[0]},{new_agent_pos[1]})"

                            # ═══ Object Collision Detection (LS20) ═══
                            # If the agent moved AND extra frame changes
                            # occurred beyond agent movement, the agent
                            # may have collided with an interactive object.
                            if (self._prev_frame is not None
                                    and post_array is not None
                                    and frame_changed):
                                try:
                                    diff_mask = self._prev_frame != post_array
                                    changed_px = int(diff_mask.sum())
                                    # Agent movement alone changes ~10-30 pixels.
                                    # If >50 pixels changed, something else happened.
                                    if changed_px > 50:
                                        # Check what color was at the new position
                                        # in the PREVIOUS frame (before collision)
                                        nx, ny = new_agent_pos
                                        if (0 <= ny < self._prev_frame.shape[0]
                                                and 0 <= nx < self._prev_frame.shape[1]):
                                            object_color = int(self._prev_frame[ny, nx])
                                            bg_color = 0  # Background is usually black
                                            if object_color != bg_color:
                                                self._causal_map.record_collision(
                                                    agent_pos=new_agent_pos,
                                                    object_color=object_color,
                                                    hud_snapshot_before=None,
                                                    hud_snapshot_after=None,
                                                )
                                                cf.map_update += (
                                                    f" [COLLISION color={object_color}"
                                                    f" extra_px={changed_px}]"
                                                )
                                except Exception:
                                    pass
                        else:
                            cf.map_update = f"Wall at ({self._agent_position[0] if self._agent_position else '?'},{self._agent_position[1] if self._agent_position else '?'}) dir={action_type}"
                        self._agent_position = new_agent_pos

        # Update last action info for next temporal perception
        if self._last_action_info:
            self._last_action_info['frame_changed'] = frame_changed
            self._last_action_info['score_delta'] = score_delta
            self._last_action_info['level_changed'] = level_changed
            self._last_action_info['consecutive_no_change'] = self._consecutive_no_change

        # Update game state
        if level_changed:
            self._current_level = new_level if new_level > 0 else self._current_level + 1
            # Reset stable regions for new level (visual layout may change)
            self._stable_region_attempts = 0
            self._stable_mask = None
            self._reference_snapshot = None
            self._frame_history = []
            self._active_plan = []  # Plan is invalid for new level
            # Fix 2: Reset goal tracking so stale data from previous level
            # doesn't produce phantom deltas on the first action of new level
            self._goal_cells_total = 0
            self._last_goal_delta_count = 0
            self._productive_rotation_index = 0
            # Reset action monotony -- new level is a fresh context
            self._consecutive_same_action = 0
            self._last_action_type = None
            # Reset level-specific causal map data while preserving
            # game-level mechanics (rules, effects, color cycles)
            if self._causal_map:
                self._causal_map.reset_for_new_level()
        self._score = new_score if new_score else self._score + score_delta

        # Build result summary
        parts = []
        if frame_changed:
            parts.append("Frame changed")
        else:
            parts.append(f"No change (x{self._consecutive_no_change})")
        if score_delta > 0:
            parts.append(f"score +{score_delta:.2f}")
        elif score_delta < 0:
            parts.append(f"score {score_delta:.2f}")
        if level_changed:
            parts.append("[LEVEL-UP]")
        if cf.goal_cells_total > 0:
            parts.append(f"goal:{cf.goal_cells_correct}/{cf.goal_cells_total}")
        if cf.was_productive:
            parts.append("[PROGRESS]")
        cf.result_summary = " | ".join(parts)

    # ═══════════════════════════════════════════════════════════════════
    # GAP IMPLEMENTATIONS: Cognitive machinery for learning
    # ═══════════════════════════════════════════════════════════════════

    def _compute_stable_regions(self):
        """
        Gap 1: Identify pixels that NEVER change across frame history.

        Stable regions are likely reference/goal displays, HUD elements,
        or background. Changing regions are likely interactive workspace.

        This is game-agnostic: the agent discovers the goal structure
        from observation, not from game-specific knowledge.
        """
        if len(self._frame_history) < 3:
            return

        self._stable_region_attempts += 1

        try:
            base = self._frame_history[0]
            # Build a mask: True where pixel NEVER changed from the base
            stable = np.ones(base.shape, dtype=bool)

            for frame in self._frame_history[1:]:
                if frame.shape == base.shape:
                    stable &= (frame == base)

            # ═══ Fix 4: Exclude HUD edge pixels from stable mask ═══
            # Edge strips contain timer bars, lives, and decorations that
            # are stable initially but change later (timer ticks, life lost).
            # Including them corrupts the workspace delta computation.
            edge = self._hud_edge_size
            h, w = stable.shape[:2]
            if h > edge * 2 and w > edge * 2:
                stable[:edge, :] = False   # top strip
                stable[-edge:, :] = False  # bottom strip
                stable[:, :edge] = False   # left strip
                stable[:, -edge:] = False  # right strip

            # A region is "stable" if a meaningful fraction of its pixels
            # never changed. Compute the fraction of stable pixels.
            total_pixels = stable.size
            stable_pixels = int(stable.sum())
            stable_fraction = stable_pixels / max(total_pixels, 1)

            # Only accept if there's a meaningful split (not all stable, not all changing)
            if 0.1 < stable_fraction < 0.95:
                self._stable_mask = stable
                self._reference_snapshot = base.copy()

                if self._verbose:
                    print(f"    [GAP1-STABLE] Stable region: {stable_fraction:.0%} pixels never changed")

                # Try to detect a reference/goal panel among the stable pixels
                self._detect_reference_panel(base)
            else:
                # Everything changes or nothing changes -- can't split
                # Don't set _stable_mask so retry is possible with more frames
                if self._verbose:
                    print(f"    [GAP1-STABLE] No useful split ({stable_fraction:.0%} stable, attempt {self._stable_region_attempts})")

        except Exception as e:
            logger.debug(f"[GAP1] Stable region computation failed: {e}")

    def _abstract_frame_state(
        self, frame: np.ndarray
    ) -> Dict[Tuple[int, int], int]:
        """
        Gap 2A: Convert raw frame into abstract {(x,y): color} dict.

        Uses the stable mask to focus on the INTERACTIVE workspace
        (changing pixels only). Each pixel in the workspace becomes
        a keyed cell. This abstract state is suitable for:
        - Goal comparison (diff against reference)
        - CausalMap state tracking (set_current_state)
        - Frame-to-frame delta computation

        Returns empty dict if stable mask hasn't been computed yet.
        """
        if self._stable_mask is None:
            return {}

        try:
            if frame.shape != self._stable_mask.shape:
                return {}

            # The changing region IS the interactive workspace
            changing = ~self._stable_mask
            if not changing.any():
                return {}

            # Extract (y, x) positions of changing pixels
            ys, xs = np.where(changing)

            state: Dict[Tuple[int, int], int] = {}
            for i in range(len(ys)):
                pos = (int(xs[i]), int(ys[i]))
                state[pos] = int(frame[ys[i], xs[i]])

            return state

        except Exception:
            return {}

    def _compute_workspace_delta(
        self, current_frame: np.ndarray
    ) -> Tuple[int, int]:
        """
        Gap 1 + Gap 2: Measure how much the workspace has changed.

        Compares the CHANGING regions of the current frame against
        the initial snapshot (frame[0]). This measures "cells that
        have been modified" — exploration coverage — NOT "cells
        matching a goal." We don't know the goal state.

        The score_delta from the API is the ground truth for whether
        modifications are moving toward the goal. This method just
        counts HOW MANY cells have been touched.

        Returns (total_workspace_cells, cells_modified_from_initial).
        """
        if self._stable_mask is None or self._reference_snapshot is None:
            return 0, 0

        try:
            if current_frame.shape != self._reference_snapshot.shape:
                return 0, 0

            # The changing pixels are the interactive workspace.
            changing = ~self._stable_mask
            if not changing.any():
                return 0, 0

            # Count workspace cells that DIFFER from initial state.
            # More modified = more exploration coverage.
            total = int(changing.sum())
            modified = int((current_frame[changing] != self._reference_snapshot[changing]).sum())

            return total, modified

        except Exception:
            return 0, 0

    def _detect_reference_panel(self, frame: np.ndarray) -> bool:
        """
        Goal-discovery: find stable colored regions that may encode goals.

        IMPORTANT: This does NOT assume a separate "reference panel" that
        spatially maps to the workspace. In many games:
        - FT09: Key sprites are INLINE within the interactive grid,
          adjacent to each tile. The agent sees through a camera viewport.
        - LS20: Lock pattern is displayed in the HUD (already tracked
          by _check_hud_state's region analysis).
        - VC33: Goals are dynamic (fluid reaching target positions).

        Game-agnostic strategy:
        1. Find stable, non-background, non-HUD colored pixels
        2. Group them into small clusters (connected components)
        3. Record each cluster's position and color — these are
           candidate "goal indicators" (key sprites, markers, etc.)
        4. Do NOT assume a single bounding-box panel or spatial scaling

        The CausalMap + constraint decoder use these indicators to
        determine per-tile target colors.

        Returns True if any goal indicators were found or updated.
        """
        if self._stable_mask is None:
            return False

        try:
            h, w = frame.shape[:2]
            edge = self._hud_edge_size

            # Build mask: stable, non-HUD, non-background
            stable_inner = self._stable_mask.copy()
            if h > edge * 2 and w > edge * 2:
                stable_inner[:edge, :] = False
                stable_inner[-edge:, :] = False
                stable_inner[:, :edge] = False
                stable_inner[:, -edge:] = False

            non_bg = frame != 0
            indicator_mask = stable_inner & non_bg

            if not indicator_mask.any():
                return False

            # Find individual colored pixels that are stable
            ys, xs = np.where(indicator_mask)
            if len(ys) < 2:
                return False

            # Group into clusters using simple flood-fill
            visited = set()
            clusters: list = []
            for i in range(len(ys)):
                pos = (int(xs[i]), int(ys[i]))
                if pos in visited:
                    continue
                # BFS to find connected component
                cluster_cells: Dict[Tuple[int, int], int] = {}
                stack = [pos]
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in visited:
                        continue
                    if not (0 <= cy < h and 0 <= cx < w):
                        continue
                    if not indicator_mask[cy, cx]:
                        continue
                    visited.add((cx, cy))
                    cluster_cells[(cx, cy)] = int(frame[cy, cx])
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = cx + dx, cy + dy
                        if (nx, ny) not in visited:
                            stack.append((nx, ny))

                if len(cluster_cells) >= 2:
                    # Compute cluster centroid and color
                    cxs = [p[0] for p in cluster_cells]
                    cys = [p[1] for p in cluster_cells]
                    centroid = (
                        sum(cxs) // len(cxs),
                        sum(cys) // len(cys),
                    )
                    colors = list(set(cluster_cells.values()))
                    clusters.append({
                        'centroid': centroid,
                        'cells': cluster_cells,
                        'colors': colors,
                        'primary_color': colors[0] if len(colors) == 1 else max(
                            set(cluster_cells.values()),
                            key=list(cluster_cells.values()).count,
                        ),
                        'size': len(cluster_cells),
                    })

            if not clusters:
                return False

            # Store as goal indicators (not a single panel)
            self._reference_panel = {
                'type': 'distributed_indicators',
                'clusters': clusters,
                'total_indicators': len(clusters),
                'region': None,  # No single bounding box
                'cells': {},  # Flatten for backward compat
            }
            # Flatten all cluster cells into cells dict
            for cluster in clusters:
                self._reference_panel['cells'].update(cluster['cells'])

            if self._verbose:
                print(
                    f"    [GOAL-DETECT] Found {len(clusters)} goal indicators, "
                    f"{sum(c['size'] for c in clusters)} pixels, "
                    f"colors: {sorted(set(c['primary_color'] for c in clusters))}"
                )

            return True

        except Exception as e:
            logger.debug(f"[GOAL-DETECT] Goal indicator detection failed: {e}")
            return False

    def _compute_goal_match(
        self, frame: np.ndarray
    ) -> Tuple[int, int, float]:
        """
        Goal-match: compare current interactive cells against known targets.

        Instead of assuming a spatial correspondence between a "reference
        panel" and the "workspace," this method uses the CausalMap's
        knowledge to count how many interactive tiles currently match
        their target colors.

        Target colors come from:
        1. Goal indicators (stable colored clusters detected by
           _detect_reference_panel) — used as hints, not spatial maps
        2. CausalMap's goal_cells (if set by constraint decoder)
        3. Score-delta feedback (positions where changes improved score)

        For camera-viewport games (FT09): the goal match is computed
        only for the CURRENTLY VISIBLE portion of the game. The agent
        must pan to see other quadrants.

        Returns (match_cells, mismatch_cells, match_fraction).
        """
        if self._causal_map is None:
            return 0, 0, 0.0

        try:
            # Strategy 1: Use CausalMap's goal cells if available
            goal_cells = self._causal_map._goal_cells
            if goal_cells:
                match_count = 0
                mismatch_count = 0
                h, w = frame.shape[:2]
                for (gx, gy), target_color in goal_cells.items():
                    if 0 <= gy < h and 0 <= gx < w:
                        current_color = int(frame[gy, gx])
                        if current_color == target_color:
                            match_count += 1
                        else:
                            mismatch_count += 1
                total = match_count + mismatch_count
                if total > 0:
                    return match_count, mismatch_count, match_count / total

            # Strategy 2: Use goal indicators + CausalMap effects to
            # count tiles at their target color. Each indicator cluster
            # near a known interactive position suggests a target color.
            if (self._reference_panel
                    and self._reference_panel.get('type') == 'distributed_indicators'):
                clusters = self._reference_panel.get('clusters', [])
                if not clusters:
                    return 0, 0, 0.0

                match_count = 0
                mismatch_count = 0
                h, w = frame.shape[:2]

                for cluster in clusters:
                    indicator_color = cluster.get('primary_color', 0)
                    centroid = cluster.get('centroid', (0, 0))

                    # Find the nearest interactive (explored) position
                    nearest_pos = None
                    nearest_dist = float('inf')
                    for pos in self._causal_map._explored:
                        dist = abs(pos[0] - centroid[0]) + abs(pos[1] - centroid[1])
                        if dist < nearest_dist:
                            nearest_dist = dist
                            nearest_pos = pos

                    if nearest_pos and nearest_dist < 20:
                        px, py = nearest_pos
                        if 0 <= py < h and 0 <= px < w:
                            current_color = int(frame[py, px])
                            if current_color == indicator_color:
                                match_count += 1
                            else:
                                mismatch_count += 1

                total = match_count + mismatch_count
                if total > 0:
                    return match_count, mismatch_count, match_count / total

            # Strategy 3: Use productive target tracking as a proxy
            # (positions where clicking improved the score)
            productive = self._causal_map.get_productive_targets()
            if productive:
                # Count how many productive positions still need clicks
                match_count = len([p for p in productive if p[1] >= 0.8])
                mismatch_count = len([p for p in productive if p[1] < 0.8])
                total = match_count + mismatch_count
                if total > 0:
                    return match_count, mismatch_count, match_count / total

            return 0, 0, 0.0

        except Exception as e:
            logger.debug(f"[GOAL-MATCH] Goal match computation failed: {e}")
            return 0, 0, 0.0

    def _compute_rich_outcome(self, cf: CognitiveFrame, post_array: Optional[np.ndarray]):
        """
        Gap 4: Compute rich action outcome with goal-progress tracking.

        Replaces binary frame_changed with multi-dimensional signal:
        - pixels_changed: raw pixel count
        - goal_delta_before/after: cells wrong before/after action
        - goal_progress_delta: improvement toward goal
        - was_productive/destructive/neutral/wasted: categorical outcome
        """
        # Compute pixels changed
        if self._prev_frame is not None and post_array is not None:
            try:
                if self._prev_frame.shape == post_array.shape:
                    diff = self._prev_frame != post_array
                    cf.pixels_changed = int(diff.sum())
            except Exception:
                pass

        # Goal-delta tracking: how many workspace cells differ from initial state
        # This tracks "exploration coverage" not "goal correctness" since we
        # don't know the target state game-agnostically.
        cf.goal_delta_before = self._last_goal_delta_count

        if post_array is not None:
            goal_total, cells_modified = self._compute_workspace_delta(post_array)
            cf.goal_cells_total = goal_total
            cf.goal_cells_correct = cells_modified  # cells touched, not "correct"
            cf.goal_completion = cells_modified / max(goal_total, 1)
            cf.goal_delta_after = goal_total - cells_modified
            # Update loop-level goal awareness
            if goal_total > 0:
                self._goal_cells_total = goal_total

            # ═══ Semantic goal matching: use TRUE goal match when available ═══
            # If we have a detected reference panel, compute how many
            # workspace cells actually match the goal pattern. This
            # replaces the "exploration coverage" proxy with a real metric.
            if self._reference_panel is not None:
                match_cells, mismatch_cells, match_frac = (
                    self._compute_goal_match(post_array)
                )
                cf.reference_panel_detected = True
                cf.goal_match_cells = match_cells
                cf.goal_mismatch_cells = mismatch_cells
                cf.goal_match_fraction = match_frac

                # Override the exploration-based goal_cells with true match
                ref_total = match_cells + mismatch_cells
                if ref_total > 0:
                    cf.goal_cells_total = ref_total
                    cf.goal_cells_correct = match_cells
                    cf.goal_completion = match_frac
                    cf.goal_delta_after = mismatch_cells

            # Update for next action
            self._last_goal_delta_count = cf.goal_delta_after
        else:
            cf.goal_delta_after = cf.goal_delta_before

        # Compute goal progress delta (change in remaining cells)
        cf.goal_progress_delta = cf.goal_delta_before - cf.goal_delta_after

        # Categorize outcome — score_delta from API is the ground truth.
        # Pixel-based delta is a secondary signal when score is flat.
        if not cf.frame_changed:
            cf.was_wasted = True
        elif cf.score_delta > 0:
            # API says we scored — this is definitively productive
            cf.was_productive = True
        elif cf.score_delta < 0:
            # API says we lost — this is definitively destructive
            cf.was_destructive = True
        elif cf.goal_progress_delta > 0:
            # Score flat but workspace delta improved — cautiously productive
            cf.was_productive = True
        elif cf.goal_progress_delta < 0:
            # Score flat but workspace delta worsened
            cf.was_destructive = True
        elif cf.goal_cells_total > 0:
            cf.was_neutral = True  # Frame changed but neither score nor delta moved
        # If no goal detected yet, frame_changed is the only signal

    def _check_hud_state(self, cf: CognitiveFrame, frame_array: Optional[np.ndarray]):
        """
        Gap 5 + 5C: Semantic HUD state extraction from frame edges.

        Splits the HUD into 4 independent sub-regions (top, bottom,
        left, right). For each region:
        - Tracks hash for change detection
        - Extracts color composition
        - Counts discrete objects (connected non-background blobs)
        - Estimates timer (bottom row shrinking bar)
        - Detects carried-state changes (non-timer regions changing)
        - Estimates lives (discrete same-colored objects)

        Game-agnostic: discovers what the edges mean by observing
        how they change over time.
        """
        if frame_array is None:
            return

        try:
            h, w = frame_array.shape[:2]
            edge = self._hud_edge_size

            if h <= edge * 2 or w <= edge * 2:
                return

            # Extract the 4 edge regions as 2D arrays (not raveled)
            regions: Dict[str, np.ndarray] = {
                'top': frame_array[:edge, :],
                'bottom': frame_array[-edge:, :],
                'left': frame_array[:, :edge],
                'right': frame_array[:, -edge:],
            }

            # ─── Overall hash (backward compat) ───
            all_edges = np.concatenate([r.ravel() for r in regions.values()])
            hud_hash = hash(all_edges.tobytes())
            cf.hud_state_hash = hud_hash
            cf.hud_state_changed = (
                self._prev_hud_hash != 0 and hud_hash != self._prev_hud_hash
            )
            self._prev_hud_hash = hud_hash

            # ─── Per-region semantic analysis ───
            region_changes: Dict[str, bool] = {}
            region_states: Dict[str, Dict[str, Any]] = {}
            non_timer_changed = False

            for name, region_2d in regions.items():
                region_flat = region_2d.ravel()
                region_hash = hash(region_flat.tobytes())

                # Did this specific region change?
                prev_hash = self._prev_hud_region_hashes.get(name, 0)
                changed = (prev_hash != 0 and region_hash != prev_hash)
                region_changes[name] = changed
                self._prev_hud_region_hashes[name] = region_hash

                # Color composition
                unique_colors = set(int(c) for c in np.unique(region_flat))
                colored_pixels = int(np.count_nonzero(region_flat))
                total_pixels = len(region_flat)
                colored_fraction = colored_pixels / max(total_pixels, 1)

                # Object counting: connected non-background blobs
                # Use simple run-length counting on rows for speed
                object_count = self._count_hud_objects(region_2d)

                state = {
                    'hash': region_hash,
                    'unique_colors': sorted(unique_colors),
                    'colored_fraction': round(colored_fraction, 3),
                    'object_count': object_count,
                    'changed': changed,
                }
                region_states[name] = state

                # Non-timer regions changing = carried state change
                if changed and name != 'bottom':
                    non_timer_changed = True

            # ─── Timer estimation (bottom region) ───
            bottom_state = region_states.get('bottom', {})
            cf.timer_fraction = bottom_state.get('colored_fraction', 1.0)
            if cf.timer_fraction < 0.2:
                cf.timer_urgency = "critical"
            elif cf.timer_fraction < 0.5:
                cf.timer_urgency = "moderate"
            else:
                cf.timer_urgency = "safe"

            # ─── Lives estimation ───
            # Look for discrete objects in top or right region that
            # could be life indicators. Prefer top region.
            lives_region = region_states.get('top', {})
            obj_count = lives_region.get('object_count', 0)
            if obj_count > 0 and obj_count <= 10:
                # Plausible life count (1-10)
                cf.lives_remaining = obj_count
            else:
                cf.lives_remaining = -1  # Unknown

            # ─── Carried state ───
            cf.carried_state_changed = non_timer_changed
            cf.hud_region_changes = region_changes
            cf.carried_state = {
                name: {
                    'colors': st.get('unique_colors', []),
                    'colored_frac': st.get('colored_fraction', 0),
                    'objects': st.get('object_count', 0),
                    'changed': st.get('changed', False),
                }
                for name, st in region_states.items()
            }

            self._prev_hud_region_states = region_states

        except Exception as e:
            logger.debug(f"[GAP5C] Semantic HUD check failed: {e}")

    @staticmethod
    def _count_hud_objects(region_2d: np.ndarray) -> int:
        """
        Count discrete non-background objects in a HUD region.

        Uses simple flood-fill on non-zero pixels. Objects are
        connected components of non-background color. Counts
        objects >= 2 pixels to filter noise.

        Returns count of distinct objects found.
        """
        if region_2d.size == 0:
            return 0
        try:
            # Binary mask: non-background pixels
            mask = region_2d != 0
            if not mask.any():
                return 0

            h, w = mask.shape
            visited = np.zeros_like(mask, dtype=bool)
            objects = 0

            for y in range(h):
                for x in range(w):
                    if mask[y, x] and not visited[y, x]:
                        # Flood-fill this component
                        size = 0
                        stack = [(y, x)]
                        while stack:
                            cy, cx = stack.pop()
                            if (0 <= cy < h and 0 <= cx < w
                                    and mask[cy, cx]
                                    and not visited[cy, cx]):
                                visited[cy, cx] = True
                                size += 1
                                stack.extend([
                                    (cy - 1, cx), (cy + 1, cx),
                                    (cy, cx - 1), (cy, cx + 1),
                                ])
                        if size >= 2:  # Filter single-pixel noise
                            objects += 1

            return objects
        except Exception:
            return 0

    def _detect_agent_position(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Gap 3C: Detect agent position in a movement game.

        For movement games, the agent is typically the only object
        that moves between frames. We detect it by diffing against
        the previous frame and finding where the "moved object"
        ended up.

        Game-agnostic: finds the centroid of the largest changed
        region that appeared in the new frame.
        """
        if self._prev_frame is None or frame.shape != self._prev_frame.shape:
            return self._agent_position

        try:
            diff = frame != self._prev_frame
            if not diff.any():
                return self._agent_position  # No change, same position

            # Find positions that are NEW (present in post but not pre)
            # These are where the agent moved TO
            changed_ys, changed_xs = np.where(diff)
            if len(changed_xs) == 0:
                return self._agent_position

            # Use centroid of changed pixels as approximate agent position
            cx = int(np.mean(changed_xs))
            cy = int(np.mean(changed_ys))
            return (cx, cy)

        except Exception:
            return self._agent_position

    # ─── Phase Implementations ────────────────────────────────────────

    def _perceive(self, frame: Any, cf: CognitiveFrame) -> PerceptualField:
        """PHASE 1: Run all perception channels and integrate."""
        percept = self._perceiver.perceive(
            frame,
            last_action=self._last_action_info,
            causal_map=self._causal_map,
            available_actions=self._available_actions,
            actions_taken=self._actions_taken,
            max_actions=self._max_actions,
            game_id=self._game_id,
        )

        # ── Bridge: Feed perception back into the causal map ──────────
        if self._causal_map:
            # Register discovered positions so completeness can rise above 0%
            positions_to_register = []

            # From detected objects (centroid positions)
            # Filter to small objects (< 1/8 frame area) = likely interactive
            # tiles, not background panels. Large blobs add noise.
            frame_area = 64 * 64
            for obj in percept.objects:
                if obj.get('size', frame_area) >= frame_area // 8:
                    continue  # Skip large background regions
                cx = int(obj.get('centroid_x', obj.get('x', 0)))
                cy = int(obj.get('centroid_y', obj.get('y', 0)))
                if 0 < cx < 64 and 0 < cy < 64:
                    positions_to_register.append((cx, cy))

            # From tile grid (inferred cell centers)
            if percept.tile_count > 0 and percept.interactive_bounds:
                y_min, x_min, y_max, x_max = percept.interactive_bounds
                rows = max(1, percept.grid_rows)
                cols = max(1, percept.grid_cols)
                tile_h = (y_max - y_min) // rows
                tile_w = (x_max - x_min) // cols
                for r in range(rows):
                    for c in range(cols):
                        tx = x_min + c * tile_w + tile_w // 2
                        ty = y_min + r * tile_h + tile_h // 2
                        positions_to_register.append((tx, ty))

            if positions_to_register:
                self._causal_map.register_positions(positions_to_register)

            # ── Bridge: Feed tile grid structure into CausalMap ────────
            # When VisualCortex detects a tile grid, pass the grid geometry
            # to CausalMap so it can aggregate pixel-level diffs into
            # tile-level effects. This is the key fix for the pixel-vs-tile
            # granularity problem.
            if (percept.tile_count > 0
                    and percept.interactive_bounds
                    and self._causal_map._tile_map is None):
                y_min, x_min, y_max, x_max = percept.interactive_bounds
                rows = max(1, percept.grid_rows)
                cols = max(1, percept.grid_cols)
                tile_h = (y_max - y_min) // rows if rows > 0 else 0
                tile_w = (x_max - x_min) // cols if cols > 0 else 0

                # Also try to get separator width from visual scene
                sep_w = 0
                if percept.visual_scene_dict:
                    tg_list = percept.visual_scene_dict.get('tile_grids', [])
                    if tg_list:
                        sep_w = tg_list[0].get('separator_width', 0)
                        # Use more precise tile dimensions if available
                        precise_tw = tg_list[0].get('tile_width', 0)
                        precise_th = tg_list[0].get('tile_height', 0)
                        precise_rows = tg_list[0].get('tile_rows', 0)
                        precise_cols = tg_list[0].get('tile_cols', 0)
                        if precise_tw > 0 and precise_th > 0:
                            tile_w = precise_tw
                            tile_h = precise_th
                        if precise_rows > 0:
                            rows = precise_rows
                        if precise_cols > 0:
                            cols = precise_cols

                if tile_w > 0 and tile_h > 0:
                    self._causal_map.set_tile_map(
                        bounds=(y_min, x_min, y_max, x_max),
                        rows=rows,
                        cols=cols,
                        tile_w=tile_w,
                        tile_h=tile_h,
                        sep_w=sep_w,
                    )

            # Forward goal cells to causal map so plan_to_goal() can work
            if percept.has_goal and percept.goal_cells:
                self._causal_map.set_goal(percept.goal_cells)
            if percept.current_cells:
                self._causal_map.set_current_state(percept.current_cells)

        # Record in cognitive frame
        cf.perception_summary = percept.summary()
        cf.panel_count = percept.panel_count
        cf.tile_count = percept.tile_count
        cf.goal_progress = percept.goal_progress
        cf.delta_count = len(percept.delta)
        cf.colors_present = sorted(percept.colors_present)
        cf.puzzle_type = percept.puzzle_type
        cf.spatial_confidence = percept.spatial_confidence
        cf.overall_confidence = percept.overall_confidence

        # ═══ GAP 1: Enrich with stable-region workspace detection ═══
        # If the perceiver's Channel 3 didn't find a goal (reference_panel
        # is None), use our frame-history approach to identify the workspace
        # and track modification coverage.
        if not percept.has_goal and self._stable_mask is not None:
            frame_array = self._perceiver._to_numpy(frame)
            if frame_array is not None:
                goal_total, cells_modified = self._compute_workspace_delta(
                    frame_array
                )
                if goal_total > 0:
                    cf.goal_cells_total = goal_total
                    cf.goal_cells_correct = cells_modified
                    cf.goal_completion = cells_modified / max(goal_total, 1)
                    cf.stable_region_detected = True
                    self._goal_cells_total = goal_total  # loop-level
                    # Update percept so downstream strategy can use it
                    percept.cells_total = goal_total
                    percept.cells_matching_goal = cells_modified
                    percept.goal_progress = cells_modified / max(goal_total, 1)
                    percept.has_goal = True
                    # Store delta count for strategy
                    cf.delta_count = goal_total - cells_modified
                    self._last_goal_delta_count = cf.delta_count

        # ═══ GAP 5: Detect agent position on first frame ═══
        if self._agent_position is None and 6 not in self._available_actions:
            # Movement-only game: try to detect agent position
            frame_array = self._perceiver._to_numpy(frame)
            if frame_array is not None:
                self._agent_position = self._detect_agent_position(frame_array)

        return percept

    def _think(
        self, percept: PerceptualField, cf: CognitiveFrame
    ) -> Tuple[str, float]:
        """
        PHASE 2: Phenomenological compression + strategy selection.

        Delegates to PhenomenologyLayer.compress() which produces a 5-D
        FeltState (valence, arousal, certainty, agency, salience) with
        momentum, hysteresis stabilization, and trace logging.  The
        FeltState is then injected back into the adapter so that the
        next cycle's compression is informed by the previous one (the
        consciousness-like feedback loop).

        Strategy is derived from FeltState + game-specific signals.
        """
        # Prepare loop-level state for the adapter
        recent_path: List[Any] = [
            (f.action_x, f.action_y)
            for f in self._frames[-5:]
            if f.action_x is not None
        ]
        loop_state: Dict[str, Any] = {
            "levels_completed": max(0, self._current_level - 1),
            "total_levels": 6,
            "max_actions": self._max_actions,
            "actions_taken": self._actions_taken,
            "recent_path": recent_path,
        }

        # Feed fresh perception into adapter -> PhenomenologyLayer
        self._bb_adapter.update(percept, loop_state)

        # Compress perception to 5-D FeltState
        felt: FeltState = self._phenomenology.compress()

        # Inject back for feedback loop (writes felt_* into adapter)
        self._phenomenology.inject(felt)

        # Derive action strategy from FeltState + game signals
        strategy = self._derive_strategy(
            felt, percept, _prior_loaded=self._prior_knowledge_loaded
        )

        # Track strategy history for stability computation
        self._bb_adapter._recent_strategies.append(strategy)
        if len(self._bb_adapter._recent_strategies) > 10:
            self._bb_adapter._recent_strategies = (
                self._bb_adapter._recent_strategies[-10:]
            )

        # Record on cognitive frame
        cf.thought_summary = (
            f"{felt.valence.value.upper()} | "
            f"certainty:{felt.certainty:.2f} | "
            f"strategy:{strategy}"
        )
        cf.valence = felt.valence.value  # Valence enum -> string
        cf.arousal = felt.arousal
        cf.certainty = felt.certainty
        cf.agency = felt.agency
        cf.salience = felt.salience
        cf.momentum = felt.momentum
        cf.dominant_contributors = list(felt.dominant_contributors)
        cf.information_gain = felt.compression_ratio
        cf.strategy = strategy

        # Try to get epistemic state from cognitive router
        if self._decision_system:
            try:
                router = getattr(self._decision_system, '_cognitive_router', None)
                if router and hasattr(router, 'epistemic_tracker'):
                    cf.epistemic_state = (
                        router.epistemic_tracker.current_state.primary_quadrant.name
                    )
            except Exception:
                pass

        return strategy, felt.certainty

    # ------------------------------------------------------------------
    # Strategy derivation from FeltState
    # ------------------------------------------------------------------

    def _derive_strategy(
        self,
        felt: FeltState,
        percept: PerceptualField,
        _prior_loaded: bool = False,
    ) -> str:
        """
        Derive action strategy from FeltState + game state.

        Strategy hierarchy (most to least committed):
          execute   - Plan exists, high certainty, favourable valence
          exploit   - Good understanding, use what we know
          experiment - Something is wrong, break out of local optimum
          explore   - Low understanding, gather information

        Enhanced with Gap 2C (goal-delta awareness) and
        Gap 5D (timer urgency awareness).
        """
        # ═══ ACTION MONOPOLY BREAKER ═══
        # If the same action has been repeated many times without level
        # progress, the rung system is stuck in a loop.  Force a strategy
        # change so the agent tries something different.
        if self._consecutive_same_action >= 8:
            # Escalating response: experiment first, then explore
            if self._consecutive_same_action >= 20:
                return "explore"   # Full reset — random walk
            return "experiment"    # Break the pattern

        # ═══ GAP 5D: Timer urgency override ═══
        # When the timer is critical, stop exploring — exploit what we know NOW.
        last_cf = self._frames[-1] if self._frames else None
        if last_cf is not None:
            if last_cf.timer_urgency == "critical":
                # No time left to explore — use whatever knowledge we have
                if percept.has_plan:
                    return "execute"
                return "exploit"

            # HUD state changed → something new happened in the environment.
            # Re-evaluate by experimenting (the world just shifted).
            if last_cf.hud_state_changed and felt.certainty < 0.7:
                return "experiment"

            # ═══ GAP 5C: Lives awareness ═══
            # If we detect lives and they're dropping, shift to exploit
            # (stop experimenting, use what we know before game over).
            if (getattr(last_cf, 'lives_remaining', -1) > 0
                    and getattr(last_cf, 'lives_remaining', -1) <= 1):
                if percept.has_plan:
                    return "execute"
                return "exploit"

            # Carried-state change (non-timer HUD changed, e.g. picked up key)
            # → something interesting happened, experiment to learn the effect
            if getattr(last_cf, 'carried_state_changed', False) and felt.certainty < 0.6:
                return "experiment"
        # EXECUTE: plan ready + confident + positive valence
        if (
            percept.has_plan
            and percept.map_completeness > 0.7
            and felt.valence in (Valence.OPPORTUNITY, Valence.STABILITY)
        ):
            return "execute"

        # Gap 2C: Goal-delta-aware strategy
        if percept.has_goal and percept.cells_total > 0:
            cells_remaining = percept.cells_total - percept.cells_matching_goal
            fraction_done = percept.cells_matching_goal / max(percept.cells_total, 1)

            # Close to goal -- exploit known causal rules to finish
            if cells_remaining <= 3 and percept.map_completeness > 0.2:
                return "exploit"

            # Far from goal and map is reasonably complete -- can plan
            if percept.map_completeness > 0.5 and fraction_done > 0.3:
                return "execute"

        # EXPERIMENT: bored / stuck / confidently threatened
        if felt.valence == Valence.BOREDOM:
            return "experiment"
        if felt.valence == Valence.THREAT and felt.certainty > 0.5:
            return "experiment"
        if percept.consecutive_no_change > 8:
            return "experiment"

        # With prior knowledge, we start with enough understanding to
        # use the rung system (experiment/exploit) rather than random explore.
        if _prior_loaded:
            # EXPLOIT: even modest map coverage suffices with prior knowledge
            if percept.map_completeness > 0.1 or felt.certainty > 0.2:
                return "exploit"
            # EXPERIMENT: we have knowledge, try applying it
            return "experiment"

        # EXPLOIT: medium-high certainty with some map coverage
        if felt.certainty > 0.5 and percept.map_completeness > 0.4:
            return "exploit"
        if felt.valence == Valence.OPPORTUNITY and felt.agency > 0.5:
            return "exploit"

        # EXPLORE: default -- gather information
        return "explore"

    def _consult_map(
        self,
        percept: PerceptualField,
        strategy: str,
        cf: CognitiveFrame,
    ) -> Optional[PlannedAction]:
        """
        PHASE 3: Consult the causal map for planned actions.

        If strategy is "execute" and we have a plan, return the next step.
        Otherwise, return None and let ACT decide.
        """
        if self._causal_map is None:
            cf.map_summary = "[MAP] No causal map"
            return None

        # Record map state
        cf.map_completeness = self._causal_map.completeness
        cf.effects_known = len(self._causal_map._effects)
        cf.positions_explored = len(self._causal_map._explored)
        cf.positions_total = len(self._causal_map._all_positions)
        cf.rules_discovered = [r.rule_type for r in self._causal_map._rules]
        cf.has_plan = self._causal_map.has_plan
        cf.plan_length = len(self._causal_map._plan)
        cf.plan_step = self._causal_map.plan_step
        cf.map_summary = self._causal_map.summary()

        # If strategy is execute and we have a plan, return next step
        if strategy == "execute":
            plan_action = self._causal_map.get_next_plan_action()
            if plan_action:
                return plan_action

            # Try to generate a plan
            plan = self._causal_map.plan_to_goal()
            if plan:
                return plan[0]

        return None

    def _movebias(self, _cands):
        """B2 (BUILD_PROGRAM_2 W1): banked movement affordances deprioritize
        actions with many observed no-op outcomes for this game+level — a
        bounded bias, never a veto (frontier.bias_moves weights, no removal).
        Loaded once per level through the frontier book; neutral without one."""
        try:
            from engines.egocentric.frontier import bias_moves
            _bk = getattr(self, "_ego_frontier_book", None)
            _lv = int(getattr(self, "_ego_level", 0) or 0)
            _mc = getattr(self, "_ego_moves_cache", None)
            if _bk is not None and (_mc is None or _mc[0] != _lv):
                _mc = (_lv, _bk.load_moves(
                    str(getattr(self, "_game_id", "") or "game"), _lv))
                self._ego_moves_cache = _mc
            return bias_moves(_cands, _mc[1] if _mc else {})
        except Exception:
            return list(_cands)

    def _nav_step_action(self):
        """[NAV] FIRST ACTIVATION (movement stack, rung 0c): GridNav's BFS
        next step as an ACTION NUMBER, or None. None unless the game shows
        mover-behavior (CursorAgency confident: ready(), >= 2 mapped
        directions currently available) AND a target exists — the abduced
        goal predicate's site when banked, else the nearest unexplored
        region. The wheel rule: a None changes NOTHING downstream, and this
        helper consumes no RNG."""
        ag = getattr(self, "_cursor_agency", None)
        nav = getattr(self, "_grid_nav", None)
        cell = getattr(self, "_nav_cell", None)
        if ag is None or nav is None or cell is None or not ag.ready():
            return None
        st = int(ag.stride() or 1) or 1
        dirs = {}
        for a, shift in ag.action_map().items():
            try:
                ai = int(a)
            except (TypeError, ValueError):
                continue
            u = ((shift[0] > 0) - (shift[0] < 0),
                 (shift[1] > 0) - (shift[1] < 0))
            if ai in self._available_actions and 1 <= ai <= 5 and u != (0, 0):
                dirs[u] = ai
        if len(dirs) < 2:
            return None
        # Target: the abduced-goal predicate site first (px x,y -> cell) ...
        goal = None
        gp = getattr(self, "_nav_goal_px", None)
        if gp is not None:
            try:
                goal = (int(round(int(gp[1]) / st)),
                        int(round(int(gp[0]) / st)))
            except (TypeError, ValueError, IndexError):
                goal = None
        if goal is None or goal == cell:
            # ... else the nearest unexplored region (bounded ring scan)
            shape = getattr(self, "_ego_frame_shape", None) or (64, 64)
            mr, mc = max(1, int(shape[0]) // st), max(1, int(shape[1]) // st)
            goal = None
            for rad in range(1, 9):
                ring = []
                for dr in range(-rad, rad + 1):
                    cols = ((-rad, rad) if abs(dr) != rad
                            else range(-rad, rad + 1))
                    for dc in cols:
                        cand = (cell[0] + dr, cell[1] + dc)
                        if (0 <= cand[0] < mr and 0 <= cand[1] < mc
                                and cand not in nav.visits):
                            ring.append(cand)
                if ring:
                    goal = min(ring, key=lambda c: (abs(c[0] - cell[0])
                                                    + abs(c[1] - cell[1]), c))
                    break
            if goal is None:
                return None
        d = nav.step_toward(cell, goal, list(dirs))
        return dirs.get(d) if d is not None else None

    def _act(
        self,
        percept: PerceptualField,
        strategy: str,
        certainty: float,
        plan_action: Optional[PlannedAction],
        obs: Any,
        agent_id: str,
        agent_role: str,
        w_A: float,
        w_B: float,
        cf: CognitiveFrame,
        **extra_context,
    ) -> Tuple[int, Optional[Dict]]:
        """
        PHASE 4: Three-speed action selection.

        SPEED 1 - MAPPED (fast): Execute plan step from causal map
        SPEED 2 - REASONED (medium): Use rung system with enriched context
        SPEED 3 - EXPLORE (slow): Maximize information gain
        """
        action_num: int = 1
        action_data: Optional[Dict] = None

        # ─── SPEED 1: MAPPED ─────────────────────────────────────────
        if plan_action is not None and strategy == "execute":
            pos = plan_action.position
            action_num = 6  # Click action
            action_data = {'x': pos[0], 'y': pos[1]}

            cf.action_speed = "mapped"
            cf.action_type = 6
            cf.action_x = pos[0]
            cf.action_y = pos[1]
            cf.action_reason = plan_action.reason
            cf.action_confidence = plan_action.confidence
            cf.action_summary = (
                f"MAPPED: Click ({pos[0]},{pos[1]}) | "
                f"plan step {plan_action.step_number + 1}/{cf.plan_length}"
            )

            # Advance the plan
            if self._causal_map:
                self._causal_map.advance_plan()

            return action_num, action_data

        # ─── SPEED 1b: MAPPED MOVEMENT (BFS pathfinding) ─────────────
        # For movement games with a known target, use BFS to find
        # shortest path avoiding known walls (Gap 3C).
        if (strategy == "execute"
                and self._causal_map
                and self._agent_position is not None
                and any(a in self._available_actions for a in (1, 2, 3, 4))
                and 6 not in self._available_actions):
            # Movement-only game: try BFS to an unvisited position
            visited = self._causal_map.get_visited_positions()
            # Pick an exploration target: nearest unvisited adjacent cell
            # or a known interesting position from perception
            target = None
            if percept.visual_scene_dict:
                # Try to reach an interesting detected object
                objects = percept.visual_scene_dict.get('objects', [])
                for obj in objects:
                    obj_pos = (obj.get('cx', 0), obj.get('cy', 0))
                    if obj_pos not in visited:
                        target = obj_pos
                        break

            if target is not None:
                path = self._causal_map.find_path_bfs(
                    self._agent_position, target
                )
                if path:
                    action_num = path[0]  # Take first step
                    cf.action_speed = "mapped"
                    cf.action_type = action_num
                    cf.action_reason = (
                        f"BFS path to ({target[0]},{target[1]}), "
                        f"{len(path)} steps"
                    )
                    cf.action_summary = (
                        f"MAPPED-BFS: ACTION{action_num}"
                        f" | target=({target[0]},{target[1]})"
                        f" | path_len={len(path)}"
                    )
                    return action_num, None

        # ─── SPEED 2: REASONED (delegate to rung system) ─────────────
        if self._decision_system is not None and strategy in ("exploit", "experiment"):
            try:
                # Build context for the rung system (backward compatible)
                context = self._build_rung_context(
                    percept, obs, agent_id, agent_role, w_A, w_B, **extra_context
                )

                result = self._decision_system.decide(obs, context)
                if isinstance(result, tuple):
                    action_str, reason = result
                    if isinstance(action_str, str) and action_str.startswith('ACTION'):
                        action_num = int(action_str.replace('ACTION', ''))
                    else:
                        action_num = random.choice(self._available_actions)

                    # Extract coordinates for ACTION6
                    if action_num == 6 and hasattr(self._decision_system, 'last_decision_metadata'):
                        metadata = self._decision_system.last_decision_metadata or {}
                        if 'pixel_position' in metadata:
                            px, py = metadata['pixel_position']
                            action_data = {'x': int(px), 'y': int(py)}
                        elif 'target' in metadata:
                            t = metadata['target']
                            action_data = {'x': int(t.get('x', 32)), 'y': int(t.get('y', 32))}
                        elif 'x' in metadata and 'y' in metadata:
                            action_data = {'x': int(metadata['x']), 'y': int(metadata['y'])}

                    cf.action_speed = "reasoned"
                    cf.action_type = action_num
                    cf.action_reason = reason[:100] if reason else "rung decision"
                    cf.rung_name = ""
                    if hasattr(self._decision_system, 'last_decision_metadata'):
                        md = self._decision_system.last_decision_metadata or {}
                        cf.rung_name = md.get('rung_name', md.get('rung', ''))
                        cf.action_confidence = md.get('confidence', 0.0)

                    if action_data:
                        cf.action_x = action_data.get('x')
                        cf.action_y = action_data.get('y')

                    cf.action_summary = (
                        f"REASONED: ACTION{action_num}"
                        + (f" @({cf.action_x},{cf.action_y})" if cf.action_x else "")
                        + (f" [{cf.rung_name}]" if cf.rung_name else "")
                    )

                    return action_num, action_data

            except Exception as e:
                logger.debug(f"[COGNITIVE-LOOP] Rung system failed: {e}")

        # ─── SPEED 3: EXPLORE (maximize information gain) ─────────────

        # --- 3a: Goal-guided exploration for click games ---
        # If we have goal awareness AND productive targets, rotate among
        # the top candidates to avoid fixating on one position.
        if self._causal_map and 6 in self._available_actions:
            productive = self._causal_map.get_productive_targets()
            if productive and self._goal_cells_total > 0:
                # G-D (PREREG_FINAL_GAPS): the lp arm may REORDER the explore
                # candidates toward large+compressible NOVEL residual sites —
                # steering only; fixed/random arms return them unchanged.
                if getattr(self, "_affect", None) is not None:
                    productive = self._affect.lp_steer(
                        productive, str(getattr(self, "_game_id", "") or "game"))
                # Rotate among the top productive positions. B5: starvation
                # widens the rotation window (bounded, STARVE_CEIL caps at x2).
                top_n = min(max(1, int(round(
                    3 * getattr(self, "_ego_explore_widen", 1.0)))),
                    len(productive))
                idx = self._productive_rotation_index % top_n
                self._productive_rotation_index += 1
                chosen_pos = productive[idx][0]
                rate = productive[idx][1]
                action_num = 6
                action_data = {'x': chosen_pos[0], 'y': chosen_pos[1]}

                cf.action_speed = "explore"
                cf.action_type = 6
                cf.action_x = chosen_pos[0]
                cf.action_y = chosen_pos[1]
                cf.action_reason = f"Guided: productive_rate={rate:.2f} [#{idx+1}/{top_n}]"
                cf.action_confidence = min(0.8, rate)
                cf.action_summary = (
                    f"EXPLORE-GUIDED: Click ({chosen_pos[0]},{chosen_pos[1]})"
                    f" | productive_rate={rate:.2f} [#{idx+1}/{top_n}]"
                )
                return action_num, action_data

        # --- 3b: Information-gain exploration for click games ---
        if self._causal_map and 6 in self._available_actions:
            target = self._causal_map.best_exploration_target()
            if target:
                action_num = 6
                action_data = {'x': target[0], 'y': target[1]}
                info_gain = self._causal_map.information_gain(target)

                cf.action_speed = "explore"
                cf.action_type = 6
                cf.action_x = target[0]
                cf.action_y = target[1]
                cf.action_reason = f"Explore: info_gain={info_gain:.2f}"
                cf.action_confidence = info_gain
                cf.information_gain = info_gain
                cf.action_summary = (
                    f"EXPLORE: Click ({target[0]},{target[1]})"
                    f" | info_gain={info_gain:.2f}"
                )
                return action_num, action_data

        # --- 3c: Perception-guided fallback for click games ---
        if 6 in self._available_actions:
            target_x, target_y = self._find_explore_target(percept)
            action_num = 6
            action_data = {'x': target_x, 'y': target_y}

            cf.action_speed = "explore"
            cf.action_type = 6
            cf.action_x = target_x
            cf.action_y = target_y
            cf.action_reason = "Explore: perception-guided"
            cf.action_confidence = 0.2
            cf.action_summary = (
                f"EXPLORE: Click ({target_x},{target_y})"
                " | perception-guided"
            )
            return action_num, action_data

        # --- 3c.5: Occasional pan for hybrid games (e.g. FT09) ---
        # Hybrid games have both click (6) and movement/pan (1-4) actions.
        # Sections 3a-3c always return clicks, so pan is never explored.
        # Periodically choose a pan action to discover other quadrants.
        movement_actions = [a for a in self._available_actions if a in (1, 2, 3, 4)]
        if movement_actions and 6 in self._available_actions:
            # Hybrid game: pan every 5th EXPLORE action
            if self._actions_taken % 5 == 0:
                action_num = random.choice(movement_actions)
                cf.action_speed = "explore"
                cf.action_type = action_num
                cf.action_reason = "Explore: pan to new quadrant (hybrid game)"
                cf.action_summary = (
                    f"EXPLORE-PAN: ACTION{action_num}"
                    f" | periodic quadrant discovery"
                )
                return action_num, None

        # --- 3d: Wall-avoiding exploration for movement-only games ---
        if movement_actions and self._causal_map:
            # ═══ [NAV] FIRST ACTIVATION (movement stack, rung 0c) ═══
            # CursorAgency confident + a target (abduced-goal site or nearest
            # unexplored region) -> GridNav's BFS next step steers the blind
            # draw. A BIAS under the wheel rule: blind explore stays
            # incumbent, the steer's share is capped at NAV_BIAS_P (<=0.5,
            # Register G GUESSED), never a veto; with no confidence this
            # block consumes NO RNG and the path stays byte-identical.
            try:
                _nava = self._nav_step_action()
                if (_nava is not None and _nava in movement_actions
                        and random.random() < NAV_BIAS_P):
                    self._nav_steers = int(
                        getattr(self, "_nav_steers", 0) or 0) + 1
                    cf.action_speed = "explore"
                    cf.action_type = _nava
                    cf.action_reason = "Explore: [NAV] gridnav step"
                    cf.action_summary = (
                        f"EXPLORE-NAV: ACTION{_nava}"
                        f" | cell={getattr(self, '_nav_cell', None)}")
                    print(f"[NAV] steer action={_nava} "
                          f"cell={getattr(self, '_nav_cell', None)} "
                          f"(p<={NAV_BIAS_P})")
                    return _nava, None
            except Exception:
                _swal(self, "OTHER")
            # Filter out known walls from current position
            pos = self._agent_position
            open_dirs = []
            unknown_dirs = []
            for a in movement_actions:
                if pos and self._causal_map.is_wall(pos, a):
                    continue  # skip known walls
                # Check if we know this direction is open
                if pos and (pos, a) in self._causal_map._open_paths:
                    open_dirs.append(a)
                else:
                    unknown_dirs.append(a)

            # Prefer unknown directions (exploration), then open ones.
            # B2: every blind draw passes through the banked-move bias.
            if unknown_dirs:
                action_num = random.choice(self._movebias(unknown_dirs))
                cf.action_reason = "Explore: unknown direction"
            elif open_dirs:
                action_num = random.choice(self._movebias(open_dirs))
                cf.action_reason = "Explore: open path"
            else:
                # All known walls from here - try any direction
                action_num = random.choice(self._movebias(movement_actions))
                cf.action_reason = "Explore: all-walls-retry"

            cf.action_speed = "explore"
            cf.action_type = action_num
            cf.action_summary = (
                f"EXPLORE-MOVE: ACTION{action_num}"
                f" | pos={pos} | {cf.action_reason}"
            )
            return action_num, None

        # Absolute fallback: random available action (B2: bias-weighted)
        action_num = random.choice(self._movebias(self._available_actions))
        cf.action_speed = "random"
        cf.action_type = action_num
        cf.action_reason = "random fallback"
        cf.action_summary = f"RANDOM: ACTION{action_num}"

        return action_num, action_data

    # ─── Context Bridge ───────────────────────────────────────────────

    def _find_explore_target(
        self, percept: PerceptualField
    ) -> tuple:
        """
        Find an interesting position to click based on perception.

        Uses multiple strategies in priority order:
        1. Object centroids from perception
        2. Tile positions from spatial analysis
        3. Positions with non-background colors
        4. Random position within interactive bounds
        """

        # Strategy 1: Click objects we haven't clicked yet
        # For click games, prefer small discrete objects (tiles/buttons) over
        # large background regions. Sort by size ascending so we try tiles first.
        if percept.objects:
            explored = set()
            if self._causal_map:
                explored = self._causal_map._explored
            sorted_objects = sorted(
                percept.objects,
                key=lambda o: o.get('size', 9999),
            )
            for obj in sorted_objects:
                cx = int(obj.get('centroid_x', obj.get('x', 0)))
                cy = int(obj.get('centroid_y', obj.get('y', 0)))
                if (cx, cy) not in explored and 0 < cx < 64 and 0 < cy < 64:
                    return (cx, cy)

        # Strategy 2: Use tile positions if available
        if percept.tile_count > 0 and percept.interactive_bounds:
            y_min, x_min, y_max, x_max = percept.interactive_bounds
            rows = max(1, percept.grid_rows)
            cols = max(1, percept.grid_cols)
            tile_h = (y_max - y_min) // rows
            tile_w = (x_max - x_min) // cols
            tiles = []
            for r in range(rows):
                for c in range(cols):
                    tx = x_min + c * tile_w + tile_w // 2
                    ty = y_min + r * tile_h + tile_h // 2
                    tiles.append((tx, ty))
            explored = set()
            if self._causal_map:
                explored = self._causal_map._explored
            unexplored = [t for t in tiles if t not in explored]
            if unexplored:
                return random.choice(unexplored)
            if tiles:
                return random.choice(tiles)

        # Strategy 3: Find non-background pixels in the frame
        if percept.frame is not None:
            try:
                arr = self._perceiver._to_numpy(percept.frame)
                if arr is not None:
                    nonzero = list(zip(*np.where(arr > 0)))
                    if nonzero:
                        # Sample a few and pick one not yet explored
                        sample = random.sample(nonzero, min(20, len(nonzero)))
                        explored = set()
                        if self._causal_map:
                            explored = self._causal_map._explored
                        for (y, x) in sample:
                            if (int(x), int(y)) not in explored:
                                return (int(x), int(y))
                        y, x = sample[0]
                        return (int(x), int(y))
            except Exception:
                pass

        # Strategy 4: Random position within interactive bounds or full frame
        if percept.interactive_bounds:
            y_min, x_min, y_max, x_max = percept.interactive_bounds
            return (random.randint(x_min, x_max), random.randint(y_min, y_max))

        return (random.randint(5, 58), random.randint(5, 58))

    def _build_rung_context(
        self,
        percept: PerceptualField,
        obs: Any,
        agent_id: str,
        agent_role: str,
        w_A: float,
        w_B: float,
        **extra_context,
    ) -> Dict[str, Any]:
        """
        Build a context dict compatible with the existing rung system.

        This bridges the new PerceptualField to the old 60-key context dict.
        Existing rungs continue to work unchanged.

        NEW: Adds 'percept' key with the full PerceptualField,
        so rungs that want structured perception can use it.
        """
        # Start with context_builder output if available
        context: Dict[str, Any] = {}

        if self._context_builder is not None:
            try:
                dc = self._context_builder.build_from_runner_state(
                    game_id=self._game_id,
                    obs=obs,
                    agent_id=agent_id,
                    agent_role=agent_role,
                    w_A=w_A,
                    w_B=w_B,
                    actions_taken=self._actions_taken,
                    max_actions=self._max_actions,
                    available_actions=self._available_actions,
                    win_levels=self._current_level - 1,
                    score=self._score,
                    **{k: v for k, v in extra_context.items()
                       if k in {
                           'last_action', 'recent_actions', 'last_frame_changed',
                           'failed_actions', 'score_delta', 'last_outcome',
                           'has_full_win', 'active_sequence', 'sequence_position',
                           'is_replay_mode', 'has_level_sequence', 'stuck_count',
                           'tried_colors', 'frame_hash', 'level_start_action_index',
                           'session_id', 'scorecard_id',
                       }},
                )
                context = dc.to_dict()
            except Exception as e:
                logger.debug(f"[COGNITIVE-LOOP] Context builder failed: {e}")

        # Enrich with structured perception
        context['percept'] = percept
        context['perceptual_field'] = percept.to_dict()
        context['causal_map'] = self._causal_map

        # Ensure visual_scene is populated (backward compat)
        if percept.visual_scene_dict and 'visual_scene' not in context:
            context['visual_scene'] = percept.visual_scene_dict

        # Ensure world_model is populated
        if 'world_model' not in context:
            context['world_model'] = {}
        if self._causal_map:
            context['world_model']['causal_map_typed'] = self._causal_map
            context['world_model']['map_completeness'] = self._causal_map.completeness

        # ═══ GAP 4D: Inject last-action outcome so rungs can read it ═══
        # Rungs can use these to adjust confidence: a rung whose last
        # suggestion was_destructive should lower its confidence.
        last_cf = self._frames[-1] if self._frames else None
        if last_cf is not None:
            context['last_was_productive'] = last_cf.was_productive
            context['last_was_destructive'] = last_cf.was_destructive
            context['last_was_wasted'] = last_cf.was_wasted
            context['last_was_neutral'] = last_cf.was_neutral
            context['last_goal_progress_delta'] = last_cf.goal_progress_delta
            context['last_pixels_changed'] = last_cf.pixels_changed
        # ═══ GAP 5D: Inject timer/HUD state for strategy-aware rungs ═══
        context['timer_urgency'] = getattr(last_cf, 'timer_urgency', 'safe') if last_cf else 'safe'
        context['hud_state_changed'] = getattr(last_cf, 'hud_state_changed', False) if last_cf else False

        # ═══ GAP 5C: Inject semantic HUD state for rungs ═══
        if last_cf is not None:
            context['carried_state'] = getattr(last_cf, 'carried_state', {})
            context['carried_state_changed'] = getattr(last_cf, 'carried_state_changed', False)
            context['lives_remaining'] = getattr(last_cf, 'lives_remaining', -1)
            context['hud_region_changes'] = getattr(last_cf, 'hud_region_changes', {})

        # ═══ Semantic goal matching: inject reference panel awareness ═══
        if last_cf is not None and getattr(last_cf, 'reference_panel_detected', False):
            context['reference_panel_detected'] = True
            context['goal_match_fraction'] = getattr(last_cf, 'goal_match_fraction', 0.0)
            context['goal_match_cells'] = getattr(last_cf, 'goal_match_cells', 0)
            context['goal_mismatch_cells'] = getattr(last_cf, 'goal_mismatch_cells', 0)

        return context

    # ─── Replay Access ────────────────────────────────────────────────

    def get_replay(self) -> List[CognitiveFrame]:
        """Get all cognitive frames from this game session."""
        return self._frames

    def print_replay(self, start: int = 0, end: Optional[int] = None):
        """Print replay to console in dashboard format."""
        frames = self._frames[start:end]
        for cf in frames:
            print(cf.to_dashboard())
            print()

    def print_log(self, start: int = 0, end: Optional[int] = None):
        """Print replay to console in single-line log format."""
        frames = self._frames[start:end]
        for cf in frames:
            print(cf.to_log_line())

    @property
    def causal_map(self) -> Optional[CausalMap]:
        """Access the causal map for external inspection."""
        return self._causal_map
