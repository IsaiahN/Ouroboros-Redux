"""
policy.py -- redux-triality: the CONTROL-INVERSION adapter. The ARC-AGI-3 eval harness owns the loop
(`Agent.main`: `while not is_done and action_counter <= MAX_ACTIONS: choose_action(frames, latest)`) and, when no
single game is pinned, runs a SWARM -- one agent instance per game on its own thread, all under one scorecard. Our
reclaimed organs were loop-owned (run_*_live drove their own for/while); the harness cannot score that shape.

`ReduxPolicy` re-expresses the organs as a STATEFUL per-step policy: warmup -> route (classify game family) ->
dispatch the matching organ, all as internal phase state advanced one action per call. Two payoffs, both forced by
the harness:
  * swarm/eval-native by construction (drop-in behind a 10-line Agent subclass), and
  * precise per-action spend -- which is the SCORE. RHAE = (human_actions / ai_actions)^2, and THINKING is free
    (only state-changing actions count). So we burn the MINIMUM warmup that identifies the family, then act to
    the organ. A 40-action warmup would be near-zero RHAE even on a win.

The `Blackboard` is the cross-game transfer the official swarm lacks (it shares no state between concurrent
agents): a family/organ prior keyed by game-id PREFIX, so a MECHANISM recognised on one game seeds the router on a
structurally-similar one -- reclaim mechanisms, not answers, and let them compound across the set.
"""
from __future__ import annotations
from typing import List, Optional, Tuple, Dict, Any
import threading
import numpy as np
from scipy import ndimage as _ndi
from .replay import learn_basis, learn_basis_trailaware
from .goal import salient_targets, approachable_component_centroid
from .planner import plan_action, bfs_path_action
from .explore import CuriosityExplorer, DirectedExplorer
from .coupled import coupled_goal_mint
from .coupled import (learn_two_body, two_body_search_action, two_body_drive_action, two_body_goal_action,
                      two_body_deliver_action, independent_multi, multi_avatar_action)
from .click import click_targets, grid_sweep, ClickProber
from .engagement import EngagementMeter, MIN_CELLS
from .loci import LociTracker
from .boundary import BoundaryDiff, diff_identities, Quarantine
from .affordance import EffectAffordance
from .survival import DeathMemory, AvatarHazard
from .progress import ProgressProbe
from .referent import find_referents, Referent
from .relation import RelationBank, RelationCtx
from .novelty_ledger import guarded_promote
from .abort_code import ChainLedger
from .bridge import _px_centroid, transition_residual, click_residual, decision_context
from .consolidate import Consolidator
from .minting import two_part_mdl, _entropy_bits
from .receipt import ResidualEvent, task_id as _task_id, echo_kind as _echo_kind, summary as _receipt_summary
from .residual_bank import ResidualBank
from .dsl import Predicate, make_atom
from .live_goal_run import _learn_passable, _two_bodies

ACTS_TOWARD = Predicate(frozenset({make_atom("ACTS_TOWARD")}))

# game families the router dispatches to
PENDING, CLICK, TWO_BODY, DIRECTIONAL, EFFECT, UNDRIVABLE, MULTI_AVATAR = \
    "pending", "click", "two_body", "directional", "effect", "undrivable", "multi_avatar"

# THE PERSISTENT RESIDUAL BANK, shared by every policy in the process and by every process through its files.
# One instance, because the bank's whole purpose is to outlive the object that fills it: a per-policy bank would
# die with the episode and re-create the exact discard it exists to remove. Keyed per game FAMILY inside; two
# families can never pool. See residual_bank.py for the decay bound and the evidence-not-conclusions rule.
RESIDUAL_BANK = ResidualBank()

# Γ, THE PROMOTED GRAMMAR, SHARED ACROSS GAMES. One instance for the process, because a per-policy Γ can only ever
# promote a φ that ONE game minted twice, and the strongest transfer claim the chain can make -- a φ minted on game
# A explaining a residual on game B -- was structurally unreachable while it stayed per-policy. This was wired only
# after the carrier was MEASURED to have a live instance: last sweep's `keys_minted_on_2plus_games` was 1
# (`INTENDED_FREE`, minted independently on re86 and wa30), so a shared library has something real to promote. Do
# not widen it further without the same evidence.
#
# WHAT THIS DELIBERATELY DOES NOT DO: it does not persist to disk. The residual bank persists because it holds
# EVIDENCE; Γ holds CONCLUSIONS, and a conclusions-store that accumulates across builder runs is an answer key with
# a slow fuse -- one bad promotion outlives every run that could have overturned it, and no later sweep re-derives
# it. Γ is rebuilt from live play every sweep, which keeps every promotion in it attributable to the run that is
# reporting it.
#
# ORDER-DEPENDENCE IS REAL AND MUST BE READ AS A CAVEAT, NOT AS A RESULT: whether a game is offered a non-empty Γ
# depends on when its threads run relative to the games that fill it. Early-scheduled games see less library than
# late ones, so per-game reuse counts are NOT comparable within a sweep; only the pooled totals are.
SHARED_ECHO = Consolidator(echo_threshold=2)


class Blackboard:
    """Thread-safe cross-game memory for the swarm. Keyed by game-id PREFIX (family, not instance). Stores learned
    MECHANISMS (which organ / which coupled colour), never per-game answers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._d: Dict[str, Dict[str, Any]] = {}

    def post(self, key: str, **facts: Any) -> None:
        with self._lock:
            self._d.setdefault(key, {}).update(facts)

    def get(self, key: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._d.get(key, {}))


BLACKBOARD = Blackboard()


class GoalProbe:
    """Abductive GOAL-HYPOTHESIS search for a two-body game after a KEEP graduation. The motion model transferred,
    but the transferred goal (MEET) stopped yielding reward on the new level -- so the OBJECTIVE changed even though
    the coupling didn't. With no reward yet to abduce from (cold start: no L2 recording), we ENUMERATE candidate
    goals -- MEET first (cheap: maybe it still works), then NEAR(body, X) for each NEW actor colour X the level
    added -- and probe each for a budget of actions, rotating when it doesn't pay off. Live reward arbitrates; once
    a hypothesis pays, coupled_goal_mint can CONSOLIDATE it. Reclaim the mechanism (abduce-then-verify), never the
    answer."""

    def __init__(self, referent_colours, meet_first: bool = True, budget: int = 22):
        self.hypotheses = [("meet", None)] if meet_first else []
        if referent_colours:
            self.hypotheses.append(("deliver", None))          # paired two-zone goal (route each body to its zone)
        self.hypotheses += [("near", int(c)) for c in referent_colours]
        if not self.hypotheses:
            self.hypotheses = [("meet", None)]
        self.idx = 0
        self.steps = 0
        self.budget = int(budget)
        self.locked = False

    def current(self):
        return self.hypotheses[self.idx]

    def tick(self) -> None:
        if self.locked:
            return
        self.steps += 1
        if self.steps >= self.budget:
            self.rotate()

    def rotate(self) -> None:
        self.idx = (self.idx + 1) % len(self.hypotheses)
        self.steps = 0

    def lock(self) -> None:
        """A hypothesis paid off (reward). Stop rotating -- this is the level's objective."""
        self.locked = True


def _prefix(game_id: str) -> str:
    return (game_id or "").split("-")[0]


def _bg_colour(grid) -> int:
    """The background = the most common colour (never a hazard; the avatar-hazard learner excludes it)."""
    g = np.asarray(grid)
    vals, cnts = np.unique(g, return_counts=True)
    return int(vals[int(np.argmax(cnts))])


def _md(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _largest_zones(grid, colours, exclude: Optional[int] = None, k: int = 2):
    """The k largest components among `colours` (the level's new actors), each as (size, centroid_px, radius_px,
    colour). Used to resolve a paired DELIVER goal to the two big symmetric zones a curriculum level added."""
    g = np.asarray(grid)
    out = []
    for col in colours:
        if exclude is not None and int(col) == int(exclude):
            continue
        m = g == int(col)
        if not m.any():
            continue
        lab, n = _ndi.label(m)
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            cen = (int(round(ys.mean())), int(round(xs.mean())))
            rad = max(int(ys.max() - ys.min()), int(xs.max() - xs.min())) / 2.0
            out.append((int(ys.size), cen, rad, int(col)))
    out.sort(key=lambda t: t[0], reverse=True)
    return out[:k]


def _assign_zones(bodies, zones, stride: int):
    """Assign the two bodies to the two zones minimising total distance; return ((c0,reach0),(c1,reach1)) for
    body0→zone, body1→zone, reach in CELLS (from the zone radius)."""
    _, cA, rA, _ = zones[0]
    _, cB, rB, _ = zones[1]
    reachA = max(1, int(rA / max(1, stride)))
    reachB = max(1, int(rB / max(1, stride)))
    if _md(bodies[0], cB) + _md(bodies[1], cA) < _md(bodies[0], cA) + _md(bodies[1], cB):
        return (cB, reachB), (cA, reachA)
    return (cA, reachA), (cB, reachB)


def _nearest_colour_centroid(grid, colour: int, ref_cell, exclude: Optional[int] = None):
    """Centroid of the colour-`colour` component nearest `ref_cell` (the candidate goal referent to drive toward).
    None if the colour is absent. `exclude` skips the bodies' own colour so a body never targets itself."""
    if exclude is not None and int(colour) == int(exclude):
        return None
    m = np.asarray(grid) == int(colour)
    if not m.any():
        return None
    lab, k = _ndi.label(m)
    best, best_d = None, None
    for i in range(1, k + 1):
        ys, xs = np.where(lab == i)
        c = (int(round(ys.mean())), int(round(xs.mean())))
        d = abs(c[0] - ref_cell[0]) + abs(c[1] - ref_cell[1])
        if best_d is None or d < best_d:
            best_d, best = d, c
    return best


def level_delta(prev_frame, new_frame, prev_avail, new_avail) -> Dict[str, Any]:
    """The curriculum diff at a level boundary: what's NEW in the graduated environment. A level transition is a
    distribution shift (the board redraws + mechanics are added); the residual/mint architecture wants to know what
    changed so it can KEEP what transferred and mint only against the surprise. Pure + testable."""
    pv = {int(x) for x in np.unique(np.asarray(prev_frame))}
    nv = {int(x) for x in np.unique(np.asarray(new_frame))}
    pa = {int(a) for a in prev_avail}
    na = {int(a) for a in new_avail}
    return dict(new_colours=sorted(nv - pv), gone_colours=sorted(pv - nv),
                new_actions=sorted(na - pa), gone_actions=sorted(pa - na))


class ReduxPolicy:
    """Stateful per-step brain fitting the ARC-AGI-3 Agent contract. Feed each observed frame via observe(grid,
    available); call choose() for the next (label, data). label is 'A<n>'; data is {'x','y'} for A6 (click) else None."""

    def __init__(self, game_id: str = "", blackboard: Optional[Blackboard] = None, warmup_cap: int = 8) -> None:
        self.game_id = game_id
        self.bb = blackboard if blackboard is not None else BLACKBOARD
        self.warmup_cap = int(warmup_cap)
        self.frames: List[np.ndarray] = []
        self.acts: List[str] = []
        # THE COORDINATE THE ACTION CARRIED, parallel to `self.acts` (None for every non-coordinate action). A click
        # game's action is a cell, and until this list existed the cell was thrown away the instant it was emitted --
        # so R_κ had no carrier and "just read the coordinate" would have been a plan asserting a field that is not
        # populated. Recording it is instrumentation at the real call site, not a detector.
        self.click_rc: List[Optional[Tuple[int, int]]] = []
        self._pending_rc: Optional[Tuple[int, int]] = None
        self._pending = "RESET"                 # the action that will have produced the NEXT observed frame
        self.n_emitted = 0
        self.family = PENDING
        self._avail: List[int] = []
        # curriculum / level-boundary state
        self.level = 0
        self._lvl0 = 0                          # index in self.frames where the CURRENT level's stream begins
        self._warm_start = 0                    # n_emitted at the current level's start (per-level warmup gate)
        self.prior: Optional[Dict[str, Any]] = None     # the frozen transferred model at the last boundary
        self.level_model: Optional[Dict[str, Any]] = None   # current hypothesis of THIS level's mechanics
        self.level_deltas: List[Dict[str, Any]] = []
        self._probe: Optional[GoalProbe] = None         # active goal-hypothesis search (two-body, post-KEEP)
        self.tracker = LociTracker()                    # persistent-identity substrate the boundary diff reads
        self.quarantine = Quarantine()                  # PARK unresolved boundary residuals under a decay bound
        self.boundary: Optional[BoundaryDiff] = None    # the latest loci-based boundary diff
        self.novel_loci: List[int] = []                 # NOVEL locus ids at the last boundary (beat C explores these)
        self._directed: Optional[DirectedExplorer] = None   # boundary-directed empowerment over the novel actors
        self.effect_aff = EffectAffordance()            # Tier-1 affordance: which actions are effective (from R_τ)
        self._effect_visits: Dict[str, int] = {}        # curiosity within the effective-action set
        self.deaths = DeathMemory()                     # DON'T-DIE organ: remembers (board, action) that killed us
        self.hazard = AvatarHazard()                    # avatar-centric: fatal DESTINATION colours (generalizes veto)
        self.n_hazard_vetoes = 0                        # times a move into a known-fatal colour was swapped out
        self.n_deaths = 0                               # deaths observed this episode (GAME_OVER transitions)
        self.n_vetoes = 0                               # times a known-fatal action was swapped for a safe one
        self._state = "NOT_FINISHED"                    # last observed game state (for death detection)
        self._reset_earned = False                      # §XIX reset-earned gate: did the last death EARN a retry?
        self._reset_rationale = ""                      # the agent's evidence-cited reasoning for (not) resetting
        # TETHER-STAGE instrument: per-SEGMENT chain accounting. Not a proxy -- every signal below is set from the
        # exact call site of the event it names, so an unwired organ reports as unwired instead of as absent evidence.
        self.chain = ChainLedger()
        # ECHO -> PROMOTE (directive 2b). Γ starts EMPTY and grows only by the echo rule; a residual is offered to it
        # BEFORE any new mint, so reuse is tested on a residual φ was not minted for. Γ IS NOW THE PROCESS-WIDE
        # SHARED LIBRARY, not a per-policy one -- see SHARED_ECHO above for why, what it costs, and what it refuses
        # to do. Promotion is UNCHANGED: still two DISTINCT tasks, still one task credited per mint. Sharing widens
        # WHO can echo, never HOW EASILY.
        self.echo = SHARED_ECHO
        self.bank = RESIDUAL_BANK                        # persistent per-family residual EVIDENCE (never conclusions)
        self.receipts: List[ResidualEvent] = []          # one record per break event -- firing or not (directive 5)
        self._seg0 = 0                                   # index in self.frames where the OPEN chain segment begins
        self._seg_n = 0                                  # how many chain segments have been closed (task counter)
        self.progress = ProgressProbe()               # Brick 1: dense monotone progress signal (the authors' gradient)
        self._prog_credit: Dict[str, float] = {}        # action -> EMA of progress-delta after it (reinforcement)
        self.n_prog_reinforce = 0                       # times an exploratory pick was biased toward progress
        self._referents: List[Referent] = []            # Brick 2: frame-native reference regions in the CURRENT frame
        self.n_referent_frames = 0                       # frames on which >=1 referent was detected (telemetry)
        self._referent_kinds_seen: set = set()           # union of referent kinds seen across the episode (telemetry)
        self.relations = RelationBank()                  # Brick 3: relation-hypothesis tester (MATCH/CONNECT/…/REACH)
        self._relation_selected: Optional[str] = None    # the relation the env is confidently rewarding (or None)
        self._probe_rel: Optional[str] = None            # the relation the effect tier drives: selected, else largest measured gap
        self._relation_kinds_seen: set = set()           # union of relations ever selected this episode (telemetry)
        self.n_relation_drive = 0                        # times a directional move was steered toward a relation target
        self._rel_credit: Dict[str, float] = {}          # Brick 4b: action -> EMA of the SELECTED relation's gap-drop
        self.n_rel_reinforce = 0                          # times an effect pick was biased toward closing the relation
        self.n_multi_avatar_drive = 0                     # G5: times two independent avatars were routed to their goals
        # THE Γ DECISION SITE's per-SEGMENT counters. Segment-scoped for the same reason the chain signals are: a
        # directive taken in segment 3 must not decorate the receipt of segment 7. `_close_segment` copies them
        # onto that segment's receipt and zeroes them; nothing else may touch them.
        # ★ FOUR COUNTERS, NOT ONE, BECAUSE A SINGLE ZERO WOULD BE AMBIGUOUS. `_g_consult == 0` alone cannot say
        # whether the decision site was never REACHED (this game never took a directional action), reached with no
        # calibrated seam (no cursor / no learned vectors), or reached with a seam and offered nothing by Γ. Those
        # are three different findings with three different fixes, and collapsing them is the silence-printed-as-a-
        # measured-zero shape this instrument keeps finding elsewhere. The first sweep of this organ made the point
        # itself: it reported `segments_consulted=0` beside a Γ snapshot that showed six games ending with a signed
        # directive available, and there was no number on the record that could say which of the three it was.
        self._g_reached = 0                               # times `_gamma_directive` was entered at all
        self._g_noseam = 0                                # ...and returned early: no calibrated cursor / vectors
        self._g_empty = 0                                 # ...and Γ had no signed directive to offer
        # ★ A FIFTH, ADDED THE BEAT AFTER THE FOUR -- BECAUSE `_g_empty` WAS ITSELF AMBIGUOUS. The `except
        # Exception` guard around `echo.directives` (Γ must never sink a run) incremented the SAME counter as the
        # honest `if not dirs` path, so a library raising on every call and a library with nothing to say printed
        # the identical number. That is the exact defect these counters were added to close, sitting inside the
        # close. A swallowed exception is a BROKEN Γ; an empty offer is a WORKING Γ with no evidence yet.
        self._g_error = 0                                 # ...and `echo.directives` RAISED (swallowed, never silent)
        self._g_consult = 0                               # steps where Γ had >=1 signed directive to offer
        self._g_dirs = 0                                  # how many it had, at the last such step
        self._g_act = 0                                   # steps where a directive actually chose the action
        self._g_uneval = 0                                # candidate actions the live seam could not build a ctx for
        # ★ Γ'S STATE AT THE MOMENT OF CONSULT, NOT ONLY AT SEGMENT CLOSE. The first sweep of the funnel reported
        # `Γ had nothing for this game=18` beside an END-OF-RUN snapshot showing eight games with one signed
        # directive available -- and the close-time snapshot cannot tell whether the sign ARRIVED AFTER the site
        # was entered (Γ warms up too late to be used, a capability finding) or was already there and the guard
        # disagreed with `sign_report` (a defect). Both readings fit the same pair of numbers, so the pair is not
        # a measurement. Captured at the FIRST entry of each segment only: it is a snapshot of a shared library,
        # and one per step would be the same library counted many times.
        self._g_entry_report: Dict[str, int] = {}
        self._seg_boundary_diff = False                   # the §3.5 boundary diff ran INSIDE this segment (see below)
        # ★★★ THE DECIDE FUNNEL -- REACH IS UPSTREAM OF BEHAVIOUR, AND MUST BE MEASURED FIRST. ★★★
        # Last beat's finding: the Γ decision site was ENTERED on ONE game out of twenty-four, and for two beats
        # its zero was read as a statement about Γ. It was a statement about the agent's own control flow: on the
        # other DIRECTIONAL games, some EARLIER `return` in the decision path answered first, every step. A
        # per-guard funnel INSIDE an organ can never see the calls that never arrived at it, so the counter has to
        # live at every real exit of the path, not inside the organ at the end of it.
        # RULES THIS OBEYS, and why:
        #  (a) EVERY exit increments at ITS OWN `return`, with a literal name written at that site. Nothing is
        #      derived from `family`, from a label, or from another counter -- a derived exit reason would be the
        #      proxy defect ("never derive a chain signal from another organ") one layer down.
        #  (b) `_dec_calls` is incremented at the TOP of `_decide`, so `sum(exits) == calls` is a real identity and
        #      an uncounted `return` added by a later beat shows up as a non-zero `uncounted`, in the suite.
        #  (c) The dispatch `return self._act_directional(labels)` is deliberately NOT counted -- that call has not
        #      exited the path yet; its five own returns do the counting. Counting both would double the total and
        #      close the identity by inflating it.
        # It is SEGMENT-scoped like the Γ counters above, for the same reason: an exit taken in segment 3 must not
        # decorate segment 7's receipt.
        self._dec_calls = 0                               # entries to `_decide` (the denominator of the funnel)
        self._dec_exits: Dict[str, int] = {}              # exit-site name -> times that `return` was the one taken
        # ★★★ REACH IS NOT COMPETENCE -- THE OUTCOME COLUMN. ★★★
        # The funnel says WHICH exit answered. It says nothing about whether the answer was any GOOD, and the last
        # beat's finding turns on that gap: `dir_target_colour` answered 461 steps across 12 games and pre-empts the
        # Γ site on all of them, so "should Γ be reached more?" is unanswerable until the incumbent is priced.
        # The cheapest true price of a step is whether the board ANSWERED it. Rules this obeys:
        #  (a) The exit NAME comes from the exit's own site (`_exit` records it); nothing is re-derived from
        #      `family` or from the emitted label at attribution time.
        #  (b) The outcome is only knowable at the NEXT `observe()`, so the name is carried forward one step and
        #      CONSUMED there. A frame that arrives with nothing pending (a restart frame) is attributed to nobody.
        #  (c) ★ THE SURVIVAL VETO IS ALLOWED TO REPLACE THE ACTION AFTER THE EXIT IS COUNTED. A board change that
        #      followed a REPLACED action is not this exit's outcome. Those steps go in their own `_dec_veto`
        #      bucket and are excluded from the numerator AND the denominator -- crediting them either way would
        #      be attributing one organ's result to another, which is the proxy defect this instrument exists for.
        #  (d) TWO change readings are published, never one: RAW (any cell differs) and MASKED (>= MIN_CELLS cells
        #      differ outside the monotone budget/timer band). A raw-only column would read ~100% everywhere on
        #      any game with a ticking bar -- the proxy that talks while the ground is mute. Publishing both makes
        #      the mask's effect visible instead of trusting it.
        self._dec_attr: Dict[str, int] = {}               # exit -> steps whose RESULT FRAME was seen (the denominator)
        self._dec_moved: Dict[str, int] = {}              # exit -> of those, board answered on the MASKED reading
        self._dec_moved_raw: Dict[str, int] = {}          # exit -> of those, ANY cell differed (mask off)
        self._dec_veto: Dict[str, int] = {}               # exit -> steps whose action the survival veto REPLACED
        self._dec_unattr = 0                              # decisions whose result frame never arrived (the residue)
        self._pend_exit: Optional[str] = None             # exit that chose the action now in flight (carried 1 step)
        self._pend_vetoed = False                         # that action was replaced before it was emitted
        # ★★★ THE SELF-MOTION CONTROL -- A PERFECT SCORE IS A SMELL, NOT A TROPHY. ★★★
        # Last beat the outcome column read masked 100.0% AND raw 100.0% for `dir_target_colour` on three games,
        # over 105-115 consecutive priced steps. masked==raw rules out the budget-bar artefact. It does NOT rule
        # out the other way a column like this reads 100%: A BOARD THAT MOVES ANYWAY. "Did the board change after
        # my action?" and "did MY ACTION change the board?" are the same number on a board with an animation, a
        # patrolling hazard, or a cycling display -- and they have opposite fixes. Until they are separated, those
        # three 100%s may not be cited as competence (RANKING 5: a mis-labelled receipt is re-measured, not cited).
        # TWO CONTROLS, both read off steps the agent ALREADY TOOK -- no new detector, no extra action, nothing the
        # policy can see. Both are computed at the SAME call site as the column they control, from the SAME change
        # reading (`_change_reading`), so a drift between control and subject is not expressible.
        #  (A) CONDITION ON THE ACTION. If the change is the agent's, the answer rate depends on WHICH action it
        #      sent. If the board moves anyway, every action reads alike. Keyed "<exit>|<action>" -- a FLAT dict, so
        #      the existing union pooler and the per-game carry both apply unchanged (a second merge written by
        #      hand is where this printer last closed an identity by re-adding a term).
        #  (B) PRICE THE VETOED STEPS. On a vetoed step the emitted action was the SURVIVAL VETO's arbitrary safe
        #      pick, not the exit's reasoned choice. They stay excluded from `attr`/`moved` -- that identity is not
        #      being touched -- but their change is now READ into their own bucket. Same game, same board, same
        #      exit, an action the exit did not choose: the cheapest within-game control on the board itself.
        # What this can prove: if the rate varies sharply across actions, the motion IS the agent's. What it cannot
        # prove: uniform 100% is consistent with self-motion AND with every action being individually effective --
        # it narrows the claim, it does not settle it, and the report must say so.
        self._dec_act_attr: Dict[str, int] = {}           # "<exit>|<action>" -> priced steps under that action
        self._dec_act_moved: Dict[str, int] = {}          # of those, the MASKED reading answered
        self._dec_act_moved_raw: Dict[str, int] = {}      # of those, ANY cell differed
        self._dec_act_cells: Dict[str, int] = {}          # SUM of masked changed-cell counts (footprint SIZE)
        self._dec_act_cells_n: Dict[str, int] = {}        # its own denominator: reshape steps have no cell count and
        #                                                   are excluded rather than given a fabricated one
        # ★★★ THE CLICK REGION -- THE CONTROL THE SELF-MOTION SPLIT COULD NOT HAVE. ★★★
        # The action split above conditions on the EMITTED LABEL, and every click carries the same label `A6`. So
        # on 45.4% of all decisions the split has exactly ONE row, nothing to vary over, and renders MUTE on every
        # game -- a control that cannot fail is not a control. But the agent DOES vary its click: it varies WHERE.
        # This keys the same reading by the COARSE REGION of the coordinate actually emitted (`click_rc[-1]`, read
        # after the veto, never the prober's intent), so the rate has something to vary over on click games too.
        # THE REGION IS A THIRDS GRID OVER THE BOARD'S OWN SHAPE -- frame-relative, no threshold, no colour, no
        # component: it is DESCRIPTIVE ONLY and no organ reads it, which is what keeps it from becoming a detector.
        # A6 steps with no recorded coordinate get their own name (`noxy`) rather than being dropped, so the sum
        # over regions must equal the `|A6` rows of the action split exactly -- published as a residue.
        self._dec_click_reg_attr: Dict[str, int] = {}     # "<exit>|A6@r<i>c<j>" -> priced click steps in that region
        self._dec_click_reg_moved: Dict[str, int] = {}    # of those, the MASKED reading answered
        self._dec_click_reg_moved_raw: Dict[str, int] = {}  # of those, ANY cell differed
        # ★ THE CLICK BRANCH: which `return` of `ClickProber.choose` produced the click. Owned here (segment-scoped,
        # cleared IN PLACE) and passed INTO the prober, which writes the literal at its own return.
        self._click_branch: Dict[str, int] = {}
        self._dec_veto_attr: Dict[str, int] = {}          # exit -> vetoed steps whose result frame WAS seen
        self._dec_veto_moved: Dict[str, int] = {}         # of those, masked answered (the control reading)
        self._dec_veto_moved_raw: Dict[str, int] = {}     # of those, raw answered
        self._levels: List[int] = []                    # per-frame levels_completed (reward stream for goal abduction)
        self.abduced: List[Dict[str, Any]] = []         # goal mints attempted at reward boundaries (gated)
        # learned organ params
        self.cursor: Optional[int] = None
        self.vecs: Dict[str, Tuple[int, int]] = {}
        self.passable: set = set()
        self.target_colour: Optional[int] = None
        self.stride = 1
        self.tb_colour: Optional[int] = None
        self.ag = None
        self.tb_pass: List[set] = [set(), set()]
        self.prober: Optional[ClickProber] = None
        self.explorer: Optional[CuriosityExplorer] = None
        # board-response organ: does the board ANSWER what we do (budget/timer bands masked out)? Drives the modality
        # escalation that refuses a null intervention -- see engagement.py and _modality_escalate.
        self.engage = EngagementMeter()
        self._escalated: Optional[str] = None            # the action a modality escalation switched us to (if any)
        self._pre_esc_family: Optional[str] = None       # family to restore if an escalation to CLICK proves null too
        self.n_modality_escalations = 0                  # telemetry: times a frozen board forced a modality switch
        self.n_modality_reverts = 0                      # telemetry: escalations undone because the new modality was null too
        # ★ THE ESCALATION BRANCH. `escalate` holds ~1 decision in 7 and answers ~1 step in 20, uniform across all
        # seven of its games -- a rate that low, that flat, is not a description of seven boards, it is a
        # description of the organ. But the exit name cannot say WHICH of the organ's three returns produced the
        # step, so the rate is unattributable. This dict is that attribution and nothing else: each key is a STRING
        # LITERAL written at the return that produces it, inside `_modality_escalate`, which is the real call site.
        # It is not derived from the exit counts, the engagement meter, or any other organ. SEGMENT-scoped, and its
        # sum must equal `escalate` + `escalate_click` exactly -- published as a residue, never assumed.
        self._esc_branch: Dict[str, int] = {}

    # ---- observation -------------------------------------------------------------------------------------------
    def observe(self, grid, available: List[int], levels_completed: int = 0, state: Optional[str] = None) -> None:
        """Record the freshly observed frame (result of the previously emitted action) + its available actions. If
        the level advanced, run the curriculum re-derivation (freeze prior, diff, keep/re-parameterize/re-derive).
        If `state` is GAME_OVER, the just-emitted action ended the run -> record the death so the retry avoids it."""
        old_avail = list(self._avail)
        prev_ids = set(self.tracker.ids())              # object identities as of the PREVIOUS frame (pre-redraw)
        self.frames.append(np.asarray(grid))
        self.acts.append(self._pending if len(self.frames) > 1 else "RESET")
        self.click_rc.append(self._pending_rc if len(self.frames) > 1 else None)
        self.chain.note_step()                          # this frame belongs to the currently open chain segment
        if state is not None:
            self._state = str(state)
            if str(state) == "GAME_OVER" and len(self.frames) >= 2:
                # the action self.acts[-1] (taken from board self.frames[-2]) ended the run -> remember it as fatal
                new_cause = self.deaths.note_death(self.frames[-2], self.acts[-1])
                self.n_deaths += 1
                # avatar-centric: if a cursor+vec is known, learn the DESTINATION COLOUR the cursor died entering
                # (bg excluded) so the veto generalizes across boards, not just this pixel-identical one.
                dcol = self._dest_colour(self.frames[-2], self.acts[-1])
                if dcol is not None:
                    self.hazard.note(dcol, _bg_colour(self.frames[-2]))
                # §XIX RESET-EARNED gate (Isaiah's ruling, option B): a post-GAME_OVER restart is EARNED only when the
                # agent can reason its way to needing it AND back that reasoning with evidence from play / past losses.
                # Mechanical criterion: this death taught a NEW avoidable cause (a fresh board+action the death-memory
                # did not already hold) -> the agent has a concrete, evidence-backed veto it can ONLY apply by
                # retrying, and no in-play action escapes GAME_OVER. A death that REPEATS a known cause taught nothing
                # new -> a retry would farm the restart with no reasoned basis -> NOT earned, the session ends (§XIX).
                # a death CLOSES the chain segment: this is the "task failed" event the whole chain hangs off, and it
                # is scored at whatever stage the segment actually reached (never inferred, never back-filled).
                self._close_segment("death")
                self._reset_earned = bool(new_cause)
                if new_cause:
                    self._reset_rationale = (
                        "reset_earned: death #%d at level %d — action %s from this board ended the run and is a NEW "
                        "avoidable cause (%d distinct causes now in game-memory); GAME_OVER leaves no in-play action, "
                        "so return-to-start is the missing primitive I need to apply the learned veto."
                        % (self.n_deaths, self.level, self.acts[-1], self.deaths.distinct_causes))
                else:
                    self._reset_rationale = (
                        "reset NOT earned: death #%d repeats a cause already in game-memory (action %s from a board I "
                        "already recorded as fatal) — this attempt taught nothing new, so a retry has no reasoned "
                        "basis for a different outcome. Session ends at GAME_OVER (§XIX)."
                        % (self.n_deaths, self.acts[-1]))
        self._avail = [int(a) for a in available]
        self._levels.append(int(levels_completed))      # reward stream (for goal abduction on reward)
        self.tracker.observe(self.frames[-1])           # maintain persistent object identity across the frame
        # board-response: how much did the board ANSWER the action that produced this frame (budget bands masked)?
        self.engage.observe(self.frames[-1], self.acts[-1] if self.acts else None)
        self._price_pending_exit()                      # did the board ANSWER the exit that chose the last action?
        if len(self.frames) >= 2:                       # Tier-1 affordance: accumulate per-action effect from R_τ
            two_ago = self.frames[-3] if len(self.frames) >= 3 else None
            prev_action = self.acts[-2] if len(self.acts) >= 2 else None
            self.effect_aff.update(self.frames[-2], self.acts[-1], self.frames[-1], two_ago, prev_action)
        # Brick 1: track the dense progress gradient and credit the last action with the progress it produced
        self.progress.observe(self.frames[-1])
        if len(self.frames) >= 2 and self.progress.confident():
            a = self.acts[-1]
            if a not in ("RESET", "?", None):
                d = self.progress.delta()
                self._prog_credit[a] = 0.6 * self._prog_credit.get(a, 0.0) + 0.4 * d   # EMA of progress-per-action
        # Brick 2: read the frame-native reference regions in the current frame (the authors' 'find the legend' step).
        # Stored for Brick 3 to reason a win relation over; it does not steer any action yet (see referents()).
        self._referents = find_referents(self.frames[-1])
        if self._referents:
            self.n_referent_frames += 1
            self._referent_kinds_seen.update(r.kind for r in self._referents)
        # Brick 3: test the relation hypotheses against the env's own signal. The bank measures each relation's
        # frame-native discrepancy every step; a relation is SELECTED only once its discrepancy is confidently shrinking
        # under play. Observing-only here; the selected relation steers the DIRECTIONAL target in _act_directional (the
        # two-body + click committed plans never consult it, so the wins are preserved).
        rctx = RelationCtx(cursor=self.cursor, passable=frozenset(self.passable or ()),
                           bg=_bg_colour(self.frames[-1]))
        self.relations.observe(self.frames[-1], self._referents, rctx)
        self._relation_selected = self.relations.selected()
        if self._relation_selected is not None:
            self._relation_kinds_seen.add(self._relation_selected)
        # The relation the effect tier drives toward: the confidently-SELECTED one if there is one, else the LARGEST
        # MEASURED gap as an EPISTEMIC PROBE. This closes the bootstrap chicken-and-egg -- selection can only fire once
        # some action is seen to shrink a relation, but before selection the pre-4b code credited nothing, so a measured
        # gap (e.g. ORDER on an effect game) sat flat and never got a chance to be driven. Probing the largest measured
        # gap is the spec's "act to test drivability" (§3.5 probe-to-isolate): general, names no game, credits only real
        # drops. Committed win plans (two-body, click) never consult this, so the wins are untouched.
        self._probe_rel = self._relation_selected or self.relations.max_measured()
        if self._probe_rel is not None:
            # Brick 4b + probe: credit the last action with the DROP it produced in the driven relation's discrepancy
            # (EMA) -- the dense reward the effect tier reinforces on so no-cursor games still follow the gap the env
            # rewards, and so a measured-but-unselected gap can be intervened on until the tester can select it.
            if len(self.frames) >= 2:
                a = self.acts[-1]
                if a not in ("RESET", "?", None):
                    d = self.relations.delta(self._probe_rel)
                    self._rel_credit[a] = 0.6 * self._rel_credit.get(a, 0.0) + 0.4 * d
        if int(levels_completed) > self.level:
            if self._probe is not None and not self._probe.locked:
                self._probe.lock()                          # the active hypothesis paid off -> it IS the objective
            self._on_level_change(int(levels_completed), old_avail, prev_ids)
        self.level = int(levels_completed)

    def _labels(self, avail: List[int]) -> List[str]:
        return ["A%d" % v for v in avail]

    def _cycle(self, labels: List[str]) -> str:
        return labels[self.n_emitted % len(labels)] if labels else "A5"

    # ---- the per-step decision (control-inversion core) --------------------------------------------------------
    def choose(self) -> Tuple[str, Optional[dict]]:
        lbl, data = self._decide()
        chosen = lbl
        lbl, data = self._survival_veto(lbl, data)
        # the veto is allowed to change the label AFTER the exit has been counted; record that so the next frame's
        # change is not credited to an exit whose action was never emitted.
        self._pend_vetoed = (lbl != chosen)
        self._pending = lbl
        # read AFTER the veto, which is allowed to change both the label and the coordinate
        self._pending_rc = None
        if isinstance(data, dict) and "x" in data and "y" in data:
            self._pending_rc = (int(data["y"]), int(data["x"]))   # stored (row, col); the wire carries (x, y)
        self.n_emitted += 1
        return lbl, data

    def referents(self) -> List[Referent]:
        """§Brick 2 accessor: the frame-native reference regions detected in the most recent frame (bordered panels,
        edge legends, matched endpoint pairs). Brick 3 reads these to hypothesise a win relation and test it against the
        environment's own signal; empty until a structural referent appears. Names no game; decides no action."""
        return self._referents

    def relation(self) -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
        """§Brick 3 accessor: (selected relation name, its drive-target cell). The selected relation is the one whose
        frame-native discrepancy is confidently shrinking under play -- the hypothesis the environment is rewarding.
        None until the tester is confident. The relation SET is general; which one wins is discovered, never encoded."""
        return self._relation_selected, self.relations.drive_target()

    def note_reset(self) -> None:
        """Called by the runner after a post-death RESET restarts the level. The next observed frame is the restart,
        not the product of a chosen action -> label it RESET so no spurious effect/death is attributed to an action."""
        self._pending = "RESET"
        self._state = "NOT_FINISHED"
        self._reset_earned = False                      # the earned grant is consumed by the reset

    def reset_earned(self) -> Tuple[bool, str]:
        """§XIX gate: (earned?, rationale). True only when the last death taught a NEW avoidable cause -- the agent
        has reasoned, from its own play + game-memory, that it needs the return-to-start primitive to apply a learned
        veto. Callers must NOT issue a post-GAME_OVER RESET unless this is True. The rationale is recorded (nothing
        silent) so every earned/denied reset carries the agent's evidence-cited reasoning."""
        return self._reset_earned, self._reset_rationale

    def would_earn_reset(self) -> bool:
        """Predicate form for the harness is_done (which is consulted BEFORE the death frame is observed): would the
        death about to be recorded -- fatal action self._pending taken from the last-observed board -- be a NEW cause?
        Mirrors the reset_earned criterion without mutating, so is_done and choose() agree."""
        if not self.frames:
            return False
        return self.deaths.would_be_new(self.frames[-1], self._pending)

    def _dest_colour(self, grid, lbl: str) -> Optional[int]:
        """The colour the cursor would ENTER by taking directional action `lbl` from `grid` -- cursor centroid +
        learned vec, read off the board. None unless a cursor colour + a vec for lbl are known and in-bounds. This is
        what the avatar-centric hazard reads/writes: 'moving onto colour X ended the run'."""
        if self.cursor is None or lbl not in (self.vecs or {}):
            return None
        g = np.asarray(grid)
        m = (g == self.cursor)
        if not m.any():
            return None
        ys, xs = np.where(m)
        r0, c0 = int(round(ys.mean())), int(round(xs.mean()))
        dr, dc = self.vecs[lbl]
        r, c = r0 + dr, c0 + dc
        h, w = g.shape
        return int(g[r, c]) if (0 <= r < h and 0 <= c < w) else None

    def _hazard_dest(self, lbl: str) -> bool:
        """True iff directional action lbl would move the cursor onto a colour LEARNED to be fatal (avatar-centric)."""
        if lbl == "A6" or not self.frames or not self.hazard.fatal_colours():
            return False
        return self.hazard.is_fatal_colour(self._dest_colour(self.frames[-1], lbl))

    def _survival_veto(self, lbl: str, data: Optional[dict]) -> Tuple[str, Optional[dict]]:
        """DON'T-DIE: veto the chosen directional/effect action if it is known-fatal, then pick a safe alternative.
        TWO complementary vetoes: (1) EXACT-board -- this action killed us from this pixel-identical board; and
        (2) AVATAR-CENTRIC -- this directional move would step the cursor onto a colour we LEARNED is fatal, on ANY
        board (generalizes across boards, so we avoid a hazard we have only met once, elsewhere). Click (A6) is exempt
        (its hazard is the coordinate, not the label). If every available action is fatal here, the original stands
        (never freeze)."""
        if lbl == "A6" or not self.frames:
            return lbl, data
        cur = self.frames[-1]
        exact_fatal = self.deaths.is_fatal(cur, lbl)
        hazard_fatal = self._hazard_dest(lbl)
        if not (exact_fatal or hazard_fatal):
            return lbl, data
        # pick a still-available action that is NEITHER exact-fatal here NOR a move onto a learned hazard colour
        candidates = [l for l in self._labels(self._avail) if l != "A6"]
        safe = [l for l in self.deaths.safe(cur, candidates)
                if l != lbl and not self._hazard_dest(l)]
        if not safe:
            return lbl, data                            # dead-end board: divergence had to happen earlier
        # least-recently-emitted safe action (curiosity), deterministic tiebreak
        pick = min(safe, key=lambda x: (self.acts.count(x), x))
        if hazard_fatal and not exact_fatal:
            self.n_hazard_vetoes += 1
        else:
            self.n_vetoes += 1
        return pick, None

    def _exit(self, where: str, out: Tuple[str, Optional[dict]]) -> Tuple[str, Optional[dict]]:
        """Count ONE decision-path exit, named at the site that takes it. Returns its argument unchanged so it can
        wrap a `return` without changing what is returned -- the counter must not be able to alter the decision it
        is measuring. `where` is a LITERAL at each call site on purpose: a name computed from state would make the
        funnel a derivation of the thing it is supposed to audit."""
        self._dec_exits[where] = self._dec_exits.get(where, 0) + 1
        if self._pend_exit is not None:
            # a previous decision's result frame never arrived (segment closed under it, or two decisions ran back
            # to back). It is the RESIDUE, published, never silently folded into either outcome bucket.
            self._dec_unattr += 1
        self._pend_exit = where                          # carried exactly one step, to the `observe` that answers it
        self._pend_vetoed = False
        return out

    def _price_pending_exit(self) -> None:
        """PRICE the exit that chose the action which produced the frame just observed. Called once per observed
        frame, from `observe`, AFTER the frame has been appended -- so `frames[-2]` is the board the decision was
        made from and `frames[-1]` is the board it produced.

        It answers ONE question and no more: did the board ANSWER that step? That is the cheapest honest price of a
        decision, and it is deliberately not a claim about whether the answer was USEFUL. Reach is not competence,
        and neither is motion -- an exit that moves the board every step may still be moving it pointlessly. What
        this rules out is the opposite and much cheaper failure: an exit that holds most of the agent's turns while
        the board never answers it at all, which is the null intervention of `engagement.py` read per-exit.

        The pending name is CONSUMED here whatever happens, so a frame that arrives with no decision behind it (the
        restart frame that opens a segment) is attributed to nobody rather than to the last exit of the previous
        segment."""
        where, vetoed = self._pend_exit, self._pend_vetoed
        self._pend_exit, self._pend_vetoed = None, False
        if where is None:
            return
        if vetoed:
            # the emitted action was NOT this exit's; the resulting frame prices the veto, not the exit
            self._dec_veto[where] = self._dec_veto.get(where, 0) + 1
            # ...but it is still a step of real play on this game's board, and the one control the agent gets for
            # free: an action IT DID NOT CHOOSE, taken from the same board, in the same segment. Read it into the
            # veto's own bucket. It stays out of `attr`/`moved` -- the exit is not being credited or debited here.
            if len(self.frames) >= 2:
                self._dec_veto_attr[where] = self._dec_veto_attr.get(where, 0) + 1
                raw, masked, _cells = self._change_reading(self.frames[-2], self.frames[-1])
                if raw:
                    self._dec_veto_moved_raw[where] = self._dec_veto_moved_raw.get(where, 0) + 1
                if masked:
                    self._dec_veto_moved[where] = self._dec_veto_moved.get(where, 0) + 1
            return
        if len(self.frames) < 2:
            self._dec_unattr += 1                        # no `before` board to compare against
            return
        prev, cur = self.frames[-2], self.frames[-1]
        self._dec_attr[where] = self._dec_attr.get(where, 0) + 1
        raw, masked, cells = self._change_reading(prev, cur)
        if raw:
            self._dec_moved_raw[where] = self._dec_moved_raw.get(where, 0) + 1
        if masked:
            self._dec_moved[where] = self._dec_moved.get(where, 0) + 1
        # THE ACTION SPLIT, taken at the same site from the same reading. The action name is read off `acts[-1]` --
        # the label that was actually EMITTED and actually produced `cur` -- not re-derived from the exit or from
        # what the exit intended, which would make the control a restatement of its subject.
        ak = "%s|%s" % (where, self.acts[-1] if self.acts else "?")
        self._dec_act_attr[ak] = self._dec_act_attr.get(ak, 0) + 1
        if raw:
            self._dec_act_moved_raw[ak] = self._dec_act_moved_raw.get(ak, 0) + 1
        if masked:
            self._dec_act_moved[ak] = self._dec_act_moved.get(ak, 0) + 1
        if cells is not None:                            # None == a reshape, which has no comparable cell count
            self._dec_act_cells[ak] = self._dec_act_cells.get(ak, 0) + int(cells)
            self._dec_act_cells_n[ak] = self._dec_act_cells_n.get(ak, 0) + 1
        # THE CLICK REGION, taken from the SAME reading at the SAME site. Only A6 steps have a coordinate, and the
        # coordinate is read off `click_rc[-1]` -- what was EMITTED -- against the shape of `prev`, the board it was
        # clicked on. An A6 with no recorded coordinate is NAMED, not dropped: the sum over these keys must equal
        # the `|A6` rows of the action split, and a silently-skipped step would make that residue unable to fail.
        if (self.acts[-1] if self.acts else None) == "A6":
            rc = self.click_rc[-1] if self.click_rc else None
            if rc is None:
                rk = "%s|A6@noxy" % where
            else:
                h, w = prev.shape
                ri = min(2, max(0, int(rc[0]) * 3 // max(1, int(h))))
                ci = min(2, max(0, int(rc[1]) * 3 // max(1, int(w))))
                rk = "%s|A6@r%dc%d" % (where, ri, ci)
            self._dec_click_reg_attr[rk] = self._dec_click_reg_attr.get(rk, 0) + 1
            if raw:
                self._dec_click_reg_moved_raw[rk] = self._dec_click_reg_moved_raw.get(rk, 0) + 1
            if masked:
                self._dec_click_reg_moved[rk] = self._dec_click_reg_moved.get(rk, 0) + 1

    def _change_reading(self, prev, cur) -> Tuple[bool, bool, Optional[int]]:
        """The ONE implementation of 'did the board answer?', shared by the priced column and by its own control.
        Returns (raw, masked, masked_changed_cells). `cells` is None for a reshape: a reshape is an answer by any
        reading, but it has no cell count comparable with the others, and inventing one would put a fabricated
        number into a column that is later averaged -- the field-never-computed-printed-as-a-number defect."""
        if prev.shape != cur.shape:
            return True, True, None
        diff = (prev != cur)
        try:
            m = self.engage.mask()                       # the monotone budget/timer band, computed structurally
            if m.shape != cur.shape:
                m = np.zeros(cur.shape, dtype=bool)
        except Exception:
            m = np.zeros(cur.shape, dtype=bool)
        cells = int((diff & ~m).sum())
        return bool(diff.any()), cells >= MIN_CELLS, cells

    def _decide(self) -> Tuple[str, Optional[dict]]:
        self._dec_calls += 1                             # the funnel's denominator, incremented before any guard
        avail = self._avail
        dirs = [v for v in avail if 1 <= v <= 5]
        labels = self._labels(avail)
        # action-set routing knowable immediately: click-only games have NO directional actions
        if self.family == PENDING and not dirs and 6 in avail:
            self.family = CLICK
            self.bb.post(_prefix(self.game_id), family=CLICK)
        if self.family == CLICK and self._pre_esc_family is None:
            return self._exit("click_native", self._act_click())   # natively-routed click game (committed click win)
        # minimal warmup: observe each directional action ~once (THINKING is free; ACTIONS are squared-costly).
        # Counted PER LEVEL (self._warm_start), so a re-derivation on a graduated level re-warms cleanly.
        warmup_needed = 0 if not dirs else min(self.warmup_cap, max(len(dirs), 2))
        if (self.n_emitted - self._warm_start) < warmup_needed:
            return self._exit("warmup", (self._cycle(labels), None))
        if self.family == PENDING:
            self._route(avail, dirs)
        esc = self._modality_escalate(labels)            # refuse the null intervention: switch modality on a frozen board
        if esc is not None:
            if esc == "A6":
                return self._exit("escalate_click", self._act_click())
            return self._exit("escalate", (esc, None))
        if self.family == TWO_BODY:
            return self._exit("family_two_body", self._act_two_body(labels))
        if self.family == MULTI_AVATAR:
            return self._exit("family_multi_avatar", self._act_multi_avatar(labels))
        if self.family == DIRECTIONAL:
            # ★ NOT WRAPPED, ON PURPOSE. This dispatch has not exited the decision path -- `_act_directional`'s own
            # five returns are the exits, and each counts itself. Wrapping here as well would double every
            # directional step and make `sum(exits) == calls` close by inflation, which is the identity-closed-by-
            # merging-terms defect this instrument caught inside its own printer last beat.
            return self._act_directional(labels)
        if self.family == EFFECT:
            return self._exit("family_effect", self._act_effect(labels))
        return self._exit("family_fallback", self._act_fallback(labels))

    def _modality_escalate(self, labels: List[str]) -> Optional[str]:
        """REFUSE THE NULL INTERVENTION. An action that leaves the board unchanged is predicted perfectly by 'nothing
        happens' -> R_τ = 0 -> no gradient, nothing to mint, nothing to transfer. When the board has been FROZEN under
        everything tried for a full window and an AVAILABLE action has never been tried, switch modality and try it;
        sight showed the agent burning whole budgets on one inert action while a click modality sat unused. Escalating
        to click makes the switch permanent (the click organ then runs its own prober), because a game whose board only
        answers clicks is a click game however many directional labels it advertises.

        The switch is REVERSIBLE, which is what keeps it safe: a directional game whose agent has merely jammed against
        a wall will escalate, find clicks null too, and be handed back to its own organ (n_modality_reverts). The verdict
        on the NEW modality uses `failed_trial`, not `is_null` -- EQUAL EVIDENCE before a verdict: the modality we
        escalated TO gets at least as many probes as the window that condemned the one it replaced. A modality that
        carries a coordinate misses for reasons of AIM, and a couple of misses must not be read as the modality being
        dead. Conversely one real board response commits us to it. Committed
        verified win organs (two-body, multi-avatar, and a natively-routed click game) are exempt outright, and
        escalation cannot fire while the board is answering. General: names no game, reads no pixels."""
        if self.family in (TWO_BODY, MULTI_AVATAR):
            return None
        if self.family == CLICK and self._pre_esc_family is None:
            return None                                  # the committed click organ owns this game
        if self._escalated is not None and self._escalated in labels:
            if not self.engage.failed_trial(self._escalated):
                if self._escalated == "A6" and self._pre_esc_family is not None \
                        and self.engage.answered("A6"):
                    self._pre_esc_family = None          # the click modality has moved the board -> commit to it
                if self.engage.answered(self._escalated):
                    # ★ THE RELEASE. `failed_trial` is `observations >= window AND best < min_cells`, and `best` is
                    # a MAX -- so ONE answer makes it False for the rest of the episode. Before this release that
                    # meant the escalation held the agent on one label at EVERY subsequent decision (measured at
                    # fbd10df: 87.6% of all escalate steps). The organ's job is to REFUSE A NULL INTERVENTION, and
                    # a label that has answered is no longer null: the reason to hold it is gone, so the escalation
                    # is over and the game goes back to the organ that owns it.
                    #
                    # A6 is the ONE case that still holds, and it holds for a different reason: the commit above has
                    # just set `_pre_esc_family = None` while `family` is CLICK, so the game IS a click game now and
                    # the click organ is where it already belongs. It is served here once and every later `_decide`
                    # is caught by the natively-routed click exit before reaching this organ.
                    if self._escalated == "A6" and self.family == CLICK:
                        self._esc_branch["hold_answered"] = self._esc_branch.get("hold_answered", 0) + 1
                        return self._escalated
                    self._escalated = None
                    # ★ ITS OWN NAME AT ITS OWN RETURN. This return produces NO escalate step -- `_decide` falls
                    # through to the family dispatch -- so it is deliberately OUTSIDE the
                    # `escalate + escalate_click == new + hold_untried + hold_answered` identity, which stays
                    # falsifiable. `receipt.summary` excludes it from that sum by name.
                    self._esc_branch["released_answered"] = self._esc_branch.get("released_answered", 0) + 1
                    return None
                self._esc_branch["hold_untried"] = self._esc_branch.get("hold_untried", 0) + 1
                return self._escalated                   # the new modality still has its fair trial -> stay in it
            if self._escalated == "A6" and self._pre_esc_family is not None:
                self.family = self._pre_esc_family       # the new modality is null too -> undo, hand the game back
                self._pre_esc_family = None
                self.n_modality_reverts += 1
            self._escalated = None                       # fall through and look for another untried modality
        esc = self.engage.escalate(labels)
        if esc is None:
            return None
        self._escalated = esc
        self.n_modality_escalations += 1
        self._esc_branch["new"] = self._esc_branch.get("new", 0) + 1
        if esc == "A6":
            self._pre_esc_family = self.family
            self.family = CLICK
            self.bb.post(_prefix(self.game_id), family=CLICK, via="modality_escalation")
        return esc

    # ---- routing -----------------------------------------------------------------------------------------------
    def _route(self, avail: List[int], dirs: List[int]) -> None:
        """Classify the game family from the CURRENT LEVEL's warmup stream, learn the organ's params, and post the
        mechanism to the blackboard. Windowed to self._lvl0 so a re-derivation on a graduated level learns from the
        new level's frames only (not the previous level's, which would corrupt the basis). Two-body is tried first
        (its coupled-colour test is specific); then single-body drivable; else undrivable."""
        fw, aw = self.frames[self._lvl0:], self.acts[self._lvl0:]
        colour, ag = learn_two_body(fw, aw)
        if ag is not None and ag.is_coupled():             # real coupling (conserved invariant + co-moving), not paint
            self.family = TWO_BODY
            self.tb_colour = colour
            self.ag = ag
            self._learn_tb_passable(colour)
            self.stride = max((max(abs(v[0]), abs(v[1])) for m in (ag.body_map(0), ag.body_map(1)) for v in m.values()),
                              default=1) or 1
            self.bb.post(_prefix(self.game_id), family=TWO_BODY, colour=colour)
            return
        if independent_multi(ag):                          # G5: 2 bodies each steerable but NOT coupled -> route each
            self.family = MULTI_AVATAR
            self.tb_colour = colour
            self.ag = ag
            self._learn_tb_passable(colour)
            self.stride = max((max(abs(v[0]), abs(v[1])) for m in (ag.body_map(0), ag.body_map(1)) for v in m.values()),
                              default=1) or 1
            self.bb.post(_prefix(self.game_id), family=MULTI_AVATAR, colour=colour)
            return
        cursor, vecs = learn_basis(fw, aw)
        if not (cursor is not None and vecs):             # trail-drawing / multi-mover games defeat the footprint
            cursor, vecs = learn_basis_trailaware(fw, aw)  # detector -> fall back to the constant-size translator
        if cursor is not None and vecs:
            self.family = DIRECTIONAL
            self.cursor = cursor
            self.vecs = vecs
            self.passable = _learn_passable(fw, cursor)
            self.stride = max((max(abs(v[0]), abs(v[1])) for v in vecs.values()), default=1) or 1
            cands = salient_targets(fw, avatar_colour=cursor, exclude=set(self.passable), top=3)
            self.target_colour = cands[0] if cands else None
            self.bb.post(_prefix(self.game_id), family=DIRECTIONAL, cursor=cursor)
            return
        # no cursor and no coupling -> not translation-drivable. But the actions may still DO things (paint/toggle/
        # place): Tier-1 affordance drives by per-action EFFECT (from R_τ). Only truly-empty action sets are UNDRIVABLE.
        if [v for v in avail if 1 <= v <= 5 or v == 7]:
            self.family = EFFECT
            self.bb.post(_prefix(self.game_id), family=EFFECT)
        else:
            self.family = UNDRIVABLE
            self.bb.post(_prefix(self.game_id), family=UNDRIVABLE)

    def _learn_tb_passable(self, colour: int) -> None:
        self.tb_pass = [set(), set()]
        fw = self.frames[self._lvl0:]
        for i in range(1, len(fw)):
            b0, b1 = _two_bodies(fw[i - 1], colour), _two_bodies(fw[i], colour)
            if len(b0) == 2 and len(b1) == 2:
                for j in range(2):
                    if b0[j] != b1[j]:
                        r, c = b1[j]
                        h, w = fw[i - 1].shape
                        if 0 <= r < h and 0 <= c < w:
                            self.tb_pass[j].add(int(fw[i - 1][r, c]))

    def _novel_changed(self, key) -> bool:
        """Empowerment signal: did the board change inside the last-targeted NOVEL actor's footprint (or did the
        actor itself vanish/transform)? Evidence the agent AFFECTED the new actor."""
        if key is None or len(self.frames) < 2:
            return False
        l = self.tracker.get(key)
        if l is None:
            return True                                     # the novel actor changed/vanished -> we affected it
        r0, c0, r1, c1 = l.bbox
        a = np.asarray(self.frames[-2]); b = np.asarray(self.frames[-1])
        if not (0 <= r0 <= r1 < a.shape[0] and 0 <= c0 <= c1 < a.shape[1] and a.shape == b.shape):
            return False
        return not np.array_equal(a[r0:r1 + 1, c0:c1 + 1], b[r0:r1 + 1, c0:c1 + 1])

    def mint_gate(self, verdict: str, name: str, bits: float, context: str = "", **paths) -> bool:
        """Every predicate promotion goes through here: a NOVEL mint is parked for HUMAN confirmation
        (novelty_ledger.guarded_promote), never self-certified by the build. RE-DERIVATION passes. Returns whether
        the build may ACT on the minted predicate. Beat B wires the discipline; beats C/D route real mints through it."""
        return guarded_promote(verdict, name, bits, self.game_id, context=context, **paths)

    # ---- TETHER-STAGE instrument (per-stall abort code) ---------------------------------------------------------
    def _residual_pass(self, reason: str) -> Optional[ResidualEvent]:
        """THE BRICK. At the break event that is closing the current segment: build the segment's R_τ residual, offer
        it to the promoted library BEFORE minting anything, then mint from it and feed the mint to the echo clock.
        Every chain signal below is noted from THIS site, which is the site where the thing it names actually happens.

        WHY AT EVERY BREAK AND NOT ONLY AT AN ADVANCE. The measurement said `diff_identities` is invoked from exactly
        one place, `_on_level_change`, which fires only when levels_completed increases -- so on a game that never
        advances a level there is NO residual, ever, and DIED_PRE_DIFF was reporting a GATE, not a perception verdict.
        §4.3 SUPPORT is the ground: R_τ (transition residual) answers every step and is near-ideal; R_ρ (reward
        residual) speaks only on success and is near-mute -- and the build minted only off R_ρ. A DEATH is the
        tether's canonical first term ("a task FAILS -> an operator is minted from the residual"); computing a
        residual only when the drive layer SUCCEEDS inverts that. This widens a TRIGGER. It adds no referent kind, no
        atom, no detector (directive 4 stands).

        OVERTURN TEST (the one the ground-maintainer named): if this trigger collapses DIED_PRE_DIFF into
        RESIDUAL_EMPTY rather than into MINT_UNFIRED, it is manufacturing reach and must be reverted."""
        lo = max(0, min(int(self._seg0), len(self.frames)))
        frames, acts = self.frames[lo:], self.acts[lo:]
        why: Dict[str, Any] = {}
        stream = "R_tau"
        exc = transition_residual(frames, acts, self.cursor, self.vecs,
                                  passable=self.passable, stride=self.stride, report=why)
        if exc is None:
            # THE SECOND STREAM (§5.3), tried ONLY where the first could not run. That ordering is what keeps the
            # next sweep attributable: R_κ cannot inflate any stage R_τ already reached, so ALL movement out of
            # DIED_PRE_DIFF belongs to R_κ and to nothing else. The two are never summed -- the receipt carries the
            # stream that produced it and `summary()` reports the distribution per stream.
            why2: Dict[str, Any] = {}
            exc2 = click_residual(frames, acts, self.click_rc[lo:], report=why2)
            if exc2 is not None:
                stream, exc, why = "R_click", exc2, why2
            else:
                why["click_reason"] = why2.get("reason")     # both streams silent: record BOTH classifiers
        # THE TASK ID CARRIES THE STREAM. `task_id` has had a `stream` field since R_ρ was described, precisely so a
        # φ that echoed ACROSS streams is READABLE as having echoed on genuinely different evidence. Filing an R_κ
        # residual under `.tau` would not just mislabel the receipt -- it would let the echo clock count a click
        # segment and a transition segment as two sightings of the same thing with nothing in the record to say so.
        tid = _task_id(self.game_id, self.level, self._seg_n,
                       stream="click" if stream == "R_click" else "tau")
        if exc is None:
            # NO OBSERVABLE -> the diff could not run. DIED_PRE_DIFF, honestly -- AND NOW WITH A RECEIPT.
            # This path used to return None before building anything, so the largest stage in the distribution was
            # the only one with no evidence under it, and `break_events` (len(receipts)) quietly meant "break
            # events where the diff ran". Emitting here is REPORTING ONLY: `note_diff` is still not called, the
            # signals are untouched, and `classify` still returns DIED_PRE_DIFF. Nothing about what the chain DOES
            # changes, so the next sweep stays attributable.
            dead = ResidualEvent(game=self.game_id, level=self.level, segment=self._seg_n, reason=str(reason),
                                 steps=int(self.chain.steps_in_segment), task_id=tid, diff_ran=False,
                                 stream=stream,
                                 click_no_diff_reason=(str(why.get("click_reason"))
                                                       if why.get("click_reason") else None),
                                 no_diff_reason=str(why.get("reason") or "unrecorded"),
                                 scan_pairs=int(why.get("scan_pairs") or 0),
                                 scan_no_vec=int(why.get("scan_no_vec") or 0),
                                 scan_unlocatable=int(why.get("scan_unlocatable") or 0),
                                 scan_no_coord=int(why2.get("scan_no_coord") or 0),
                                 scan_off_board=int(why2.get("scan_off_board") or 0),
                                 library_size_before=len(self.echo.library),
                                 library_foreign_before=len(self.echo.foreign(self.game_id)))
            self.receipts.append(dead)
            return dead
        n = len(exc)
        k = sum(1 for _, o in exc if o)
        base = _entropy_bits(n, k)
        # non-empty means "structure the base grammar does not account for": the outcomes are MIXED. A uniform
        # residual is pure -- Γ was right every time, or wrong every time -- and there is nothing for a predicate to
        # split. This is exactly the precondition two_part_mdl tests, so RESIDUAL_EMPTY cannot be a rubber stamp.
        nonempty = bool(n >= 2 and base > 0.0)
        self.chain.note_diff(residual_nonempty=nonempty)
        ev = ResidualEvent(game=self.game_id, level=self.level, segment=self._seg_n, reason=str(reason),
                           steps=int(self.chain.steps_in_segment), task_id=tid, diff_ran=True,
                           stream=stream,
                           scan_pairs=int(why.get("scan_pairs") or 0),
                           scan_no_vec=int(why.get("scan_no_vec") or 0),
                           scan_unlocatable=int(why.get("scan_unlocatable") or 0),
                           scan_no_coord=int(why.get("scan_no_coord") or 0),
                           scan_off_board=int(why.get("scan_off_board") or 0),
                           n_exceptions=n, n_positive=k, baseline_bits=float(base),
                           residual_nonempty=nonempty, library_size_before=len(self.echo.library),
                           library_foreign_before=len(self.echo.foreign(self.game_id)))
        self.receipts.append(ev)
        if not nonempty:
            return ev
        # (c) OFFER THE FRESH RESIDUAL TO Γ *BEFORE* MINTING. Order is load-bearing: scoring the library after a
        # fresh mint would let the mint answer its own question. Only counted as an ATTEMPT when Γ is NON-EMPTY --
        # offering a residual to an empty library is not an attempt at reuse, and calling it one would manufacture
        # MINTED_UNUSED, the single code that indicts the architecture.
        # ONE READ of the shared library serves BOTH the branch and the size recorded for it. Γ is a process-wide
        # singleton written by every other game's thread, so a second read here could return a different number
        # than the one that chose the branch -- and the disagreement would appear exactly in the runs this counter
        # is here to explain. Read once, charge once.
        gamma_n = len(self.echo.library)
        if gamma_n:
            self.chain.note_offer_gate("offered", gamma_n)
            self.chain.note_reuse_attempt()
            ev.reuse_attempted = True
            # The offer is made to the WHOLE library -- a within-game echo is still a real transfer across tasks and
            # is not suppressed. What is recorded separately is whether any φ on offer came from a DIFFERENT game,
            # because that is the condition the shared Γ was built for and the one its undo is written against. A
            # shared library whose every offer is same-game has not crossed anything, however busy `reuse_attempted`
            # looks.
            ev.reuse_attempted_foreign = ev.library_foreign_before > 0
            # THE PEN IS THE LEDGER'S OWN METHOD: whichever way `explains_scored` comes out, the name is written
            # from inside it, into the same object that scores the segment. Nothing here reads the branch back.
            hit = self.echo.explains_scored(exc, branch=self.chain.note_reuse_exit,
                                            phi_branch=self.chain.note_no_eligible_phi,
                                            kind_branch=self.chain.note_phi_kind)
            if hit is not None:
                pred, gain = hit
                self.chain.note_reuse()
                ev.transferred = str(pred)
                ev.transfer_gain_bits = float(gain)
                ev.minted_on = self.echo.echo_tasks(pred)
                ev.echo_kind = _echo_kind(tid, ev.minted_on)
        else:
            # THE BRANCH THAT USED TO BE SILENT. A real residual arrived, wanted an answer, and found nothing to
            # ask -- and for fourteen beats the only trace was a stage name, `REUSE_UNWIRED`, which says "the reuse
            # path is not wired" when what actually happened is "the shared library was still empty when we asked".
            # An exit name covering a state nobody wrote down is the same defect as an exit name covering two
            # returns. Nothing is minted, transferred or suppressed here; the ONLY effect is the receipt.
            self.chain.note_offer_gate("skipped_gamma_empty", 0)
        # NOTE-transfer-CLEAR stays deliberately UNWIRED this beat: `cleared` requires the transferred φ to STEER
        # ACTION, which is the operator layer -- the last link, and the worst place for a first end-to-end run. The
        # honest ceiling here is USED_NOCLEAR, and a receipt says so in words.
        rep: Dict[str, Any] = {}
        mint = two_part_mdl(exc, max_size=2, report=rep)
        ev.n_constructed = int(rep.get("n_constructed", 0))
        ev.n_eligible = int(rep.get("n_eligible", 0))
        ev.selection_cost_bits = float(rep.get("selection_cost_bits", 0.0))
        # (d) BANK THE FRESH RESIDUAL -- unconditionally, and AFTER it has been scored on its own. §3.5
        # ACCUMULATE: "deferred residual accumulates across boundaries". This is the line that removes the
        # discard: until now `exc` died here with the segment. Evidence only; no verdict is written.
        # KEYED BY STREAM, not by game. Pooling an R_κ residual with an R_τ one would be summing two grounds inside
        # the mint itself -- the exact thing §5.3 forbids -- and it would do so invisibly, since the pool is only
        # ever seen as a count. R_τ keeps the bare game id so the banks already on disk stay valid.
        bank_key = self.game_id if stream == "R_tau" else "%s:%s" % (self.game_id, stream)
        try:
            self.bank.deposit(bank_key, tid, exc)
        except Exception:
            pass                                                 # the bank must never sink a run
        pool: List[Any] = []
        if mint is None:
            # (e) THE POOLED RETRY, and ONLY when the fresh residual failed to mint. The fresh attempt above is
            # left exactly as it was so the old measurement stays comparable; this is a strictly additional
            # attempt on strictly more evidence, recorded in its own fields. A segment's ~5 exceptions cannot pay
            # a ~6-bit selection cost no matter how real the rule is -- that is an arithmetic fact about the
            # sample size, not a verdict on the architecture, and pooling is the only thing that changes it.
            try:
                pool, ptasks = self.bank.pool(bank_key)
            except Exception:
                pool, ptasks = [], []
            ev.pool_size, ev.pool_tasks = len(pool), list(ptasks)
            if len(pool) > len(exc):                             # nothing to gain from a pool that IS this segment
                ev.pool_attempted = True
                prep: Dict[str, Any] = {}
                pmint = two_part_mdl(pool, max_size=2, report=prep)
                ev.pool_n_eligible = int(prep.get("n_eligible", 0))
                ev.pool_selection_cost_bits = float(prep.get("selection_cost_bits", 0.0))
                if pmint is not None:
                    ev.minted_from_pool = True
                    mint = pmint
        if mint is not None:
            self.chain.note_mint()
            ev.minted = True
            ev.minted_phi = str(mint.predicate)
            ev.minted_bits = float(getattr(mint, "saved_bits", 0.0))
            ev.minted_support = int(getattr(mint, "support", 0))
            ev.key = "+".join(sorted(a.name for a in mint.predicate.atoms))
            # CREDITED TO EXACTLY ONE TASK -- this one -- even when the evidence came from a pool spanning many.
            # Crediting the pool's tasks would clear echo_threshold=2 on a single mint, auto-fill Γ, and make
            # MINTED_UNUSED (the one code that indicts the architecture) reachable by bookkeeping rather than by
            # play. Two pooled mints of the same φ on two different pools still echo, legitimately and slower.
            # THE EVIDENCE φ WAS ACTUALLY FITTED TO GOES WITH IT -- `pool` when the mint came from the pooled
            # retry, `exc` when it came fresh. Passing the wrong one would bank an outcome split computed on
            # steps the predicate was never scored against, which is a fabricated sign rather than a weak one.
            # Both are keyed to THIS task id, which is correct in both cases: the bank pools within a game.
            src = pool if ev.minted_from_pool else exc
            ev.promoted = self.echo.observe_mint(tid, mint, exceptions=src)  # the Predicate OBJECT (directive 2a)
            ev.echo_count = len(self.echo.echo_tasks(mint.predicate))
        return ev

    def _close_segment(self, reason: str) -> None:
        """The ONE route by which a chain segment ends. Runs the residual pass first (so the segment's own signals
        are set before it is scored), then closes and scores it, then re-bases the segment window.

        `_seg0` after a DEATH is len(frames): the next frame is the post-death restart board, and the
        death-board -> restart-board discontinuity is not play. After an ADVANCE it is len(frames)-1: the redraw
        frame legitimately opens the new level's stream (this matches `_lvl0`)."""
        # A decision still IN FLIGHT at the boundary belongs to NEITHER segment's outcome tally: its result frame
        # arrives in the next segment, where `frames[-2]` is a pre-restart board and the diff would price the
        # restart rather than the step. Charge it to THIS segment's residue -- the decision was taken here -- and
        # drop the carry, rather than pricing a step across a boundary.
        if self._pend_exit is not None:
            self._dec_unattr += 1
            self._pend_exit, self._pend_vetoed = None, False
        if self.chain.steps_in_segment > 0:
            try:
                ev = self._residual_pass(reason)
            except Exception as exc:                            # a residual that raises must not sink the run
                # ...but it must not vanish either. A raise here scores DIED_PRE_DIFF exactly like a residual that
                # could not be computed, and the two have completely different fixes. Swallowing it left a crash
                # indistinguishable from an honest "no observable" -- the same silence-as-a-measured-zero shape
                # this instrument keeps finding. The exception TYPE is recorded, not the traceback: a classifier.
                tid = _task_id(self.game_id, self.level, self._seg_n)
                ev = ResidualEvent(game=self.game_id, level=self.level, segment=self._seg_n, reason=str(reason),
                                   steps=int(self.chain.steps_in_segment), diff_ran=False, task_id=tid,
                                   no_diff_reason="residual_raised:%s" % type(exc).__name__)
                # ONE RECEIPT PER SEGMENT, always. If the pass already filed one for this task and then raised
                # further down, a second receipt would inflate `break_events` -- fixing an undercount with an
                # overcount is not a fix.
                if self.receipts and self.receipts[-1].task_id == tid:
                    self.receipts[-1].no_diff_reason = self.receipts[-1].no_diff_reason or ev.no_diff_reason
                    ev = self.receipts[-1]
                else:
                    self.receipts.append(ev)
        else:
            ev = None
        # READ BEFORE THE CLOSE. `end_segment` zeroes the segment's reuse tally, and this receipt is the ONLY row on
        # which the segment's STAGE and the branches that produced that stage ever appear together. Reading it after
        # the close would print a measured zero on every segment -- a field never computed, rendered as evidence.
        seg_att = self.chain.reuse_attempts_in_segment
        seg_reuse = dict(self.chain.reuse_branch_in_segment)
        seg_phi = dict(self.chain.no_eligible_phi_in_segment)
        seg_phi_kind = dict(self.chain.phi_kind_in_segment)
        seg_offer = dict(self.chain.offer_gate_in_segment)
        seg_gamma = dict(self.chain.gamma_at_offer_in_segment)
        st = self.chain.end_segment(reason)
        if ev is not None:
            ev.stage = None if st is None else st.name
            ev.reuse_attempts = int(seg_att)
            ev.reuse_branch = seg_reuse
            ev.no_eligible_phi = seg_phi
            ev.phi_kind = seg_phi_kind
            ev.offer_gate = seg_offer
            ev.gamma_at_offer = seg_gamma
            ev.boundary_diff_ran = bool(self._seg_boundary_diff)
            # THE DECISION SITE's segment tally lands on the SAME receipt that carries the segment's stage, so a
            # lifted stage and the organ that lifted it are always read off one row. `reuse_source` is composed
            # here rather than at either call site because BOTH organs write the same ledger signal, and a signal
            # with two possible authors is unattributable -- which is the failure mode the whole instrument
            # exists to prevent.
            ev.gamma_consulted, ev.gamma_directives = int(self._g_consult), int(self._g_dirs)
            ev.gamma_actions, ev.gamma_unevaluable = int(self._g_act), int(self._g_uneval)
            ev.gamma_reached, ev.gamma_noseam = int(self._g_reached), int(self._g_noseam)
            ev.gamma_empty, ev.gamma_error = int(self._g_empty), int(self._g_error)
            ev.gamma_sign_report_at_entry = dict(self._g_entry_report)
            ev.decide_calls, ev.decide_exits = int(self._dec_calls), dict(self._dec_exits)
            ev.decide_attr, ev.decide_moved = dict(self._dec_attr), dict(self._dec_moved)
            ev.decide_moved_raw, ev.decide_veto = dict(self._dec_moved_raw), dict(self._dec_veto)
            ev.decide_unattr = int(self._dec_unattr)
            ev.decide_act_attr, ev.decide_act_moved = dict(self._dec_act_attr), dict(self._dec_act_moved)
            ev.decide_act_moved_raw = dict(self._dec_act_moved_raw)
            ev.decide_act_cells, ev.decide_act_cells_n = dict(self._dec_act_cells), dict(self._dec_act_cells_n)
            ev.decide_veto_attr, ev.decide_veto_moved = dict(self._dec_veto_attr), dict(self._dec_veto_moved)
            ev.decide_veto_moved_raw = dict(self._dec_veto_moved_raw)
            ev.decide_esc_branch = dict(self._esc_branch)
            ev.decide_click_branch = dict(self._click_branch)
            ev.decide_click_reg_attr = dict(self._dec_click_reg_attr)
            ev.decide_click_reg_moved = dict(self._dec_click_reg_moved)
            ev.decide_click_reg_moved_raw = dict(self._dec_click_reg_moved_raw)
            src = ([] if not ev.transferred else ["explains"]) + ([] if not self._g_act else ["directive"])
            ev.reuse_source = "+".join(src) or None
            try:
                ev.gamma_sign_report = dict(self.echo.sign_report(self.game_id))
            except Exception:
                ev.gamma_sign_report = {}
        # zeroed whether or not a receipt was filed: an EMPTY segment files none, and carrying its tally into the
        # next segment would attribute a directive to a segment that did not take it.
        self._g_consult = self._g_dirs = self._g_act = self._g_uneval = 0
        self._g_reached = self._g_noseam = self._g_empty = self._g_error = 0
        self._g_entry_report = {}
        self._seg_boundary_diff = False
        self._dec_calls = 0
        self._dec_exits = {}
        self._dec_attr = {}
        self._dec_moved = {}
        self._dec_moved_raw = {}
        self._dec_veto = {}
        self._dec_unattr = 0
        self._dec_act_attr = {}
        self._dec_act_moved = {}
        self._dec_act_moved_raw = {}
        self._dec_act_cells = {}
        self._dec_act_cells_n = {}
        self._esc_branch = {}
        # ★ CLEARED IN PLACE, NOT REBOUND. The ClickProber holds a REFERENCE to this dict and outlives the segment
        # (it is only rebuilt on a level change), so rebinding here would leave the prober writing into a dict
        # nobody reads and every segment after the first would report zero clicks -- a field never COMPUTED,
        # printed as a zero, which is a mis-labelled receipt. Pinned by a two-segment test.
        self._click_branch.clear()
        self._dec_click_reg_attr = {}
        self._dec_click_reg_moved = {}
        self._dec_click_reg_moved_raw = {}
        self._dec_veto_attr = {}
        self._dec_veto_moved = {}
        self._dec_veto_moved_raw = {}
        self._seg_n += 1
        self._seg0 = max(0, len(self.frames) - 1) if reason == "advance" else len(self.frames)

    def end_run(self) -> None:
        """Close the final chain segment. A run that ends on the action cap / wall clock / a GAME_OVER with no earned
        reset is a STALL and is scored, exactly like a death: the task did not close. Runners MUST call this, or the
        last segment silently never reports. Idempotent -- a segment with no observed frame is a no-op."""
        self._close_segment("run_end")

    def echo_report(self) -> Dict[str, Any]:
        """The ECHO clock's state plus the break-event accounting. `firing_kinds` is reported SEPARATELY per kind so
        no pooled summary can add a within-run echo to a cross-game one and call the total 'transfers'."""
        r = dict(_receipt_summary(self.receipts))
        r.update(library=[str(p) for p in self.echo.library], echo_threshold=self.echo.echo_threshold)
        return r

    def firing_receipts(self) -> List[Dict[str, Any]]:
        """Rendered-ready dicts for every FIRING. Empty list is the honest report that nothing fired -- no receipt,
        no firing, and no prose is permitted to bridge that gap."""
        return [e.to_dict() for e in self.receipts if e.fired]

    def chain_report(self) -> Dict[str, Any]:
        """The measured stage distribution. This REPLACES the old per-run `_tether_stage` proxy, which inferred
        `diff_ran` from the relation layer and conflated MINTED with the human gate's `acted`. Report what it says,
        however low: an instrument built to read higher measures nothing."""
        return self.chain.report()

    # ---- curriculum: level-boundary diff + re-derivation (Tether §3.5) ------------------------------------------
    def _on_level_change(self, new_level: int, old_avail: List[int], prev_ids: set) -> None:
        """A level graduated. Build the loci-based BOUNDARY DIFF (TRANSFERRED/NOVEL/GONE by tracked identity, plus
        the colour/action deltas), freeze the transferred model as PRIOR, and decide:
          - REBINDING (the control set changed → new/gone actions) → RE-DERIVE: re-fit params, do not treat as a new
            mechanism (Tether: broken-by-rebinding, the ACTS_TOWARD-in-a-new-costume trap);
          - KEEP (organ referent survives) → transfer the model; two-body arms the goal probe on the NOVEL actors;
          - RE-DERIVE (referent gone) → re-warm + re-route on the new level, prior retained.
        NOVEL loci are surfaced for beat C (direct empowerment there first). The quarantine DECAYS each boundary."""
        # The segment that just ended ended in an ADVANCE. A level cleared by search/drive is NOT a tether firing
        # (membrane rule §3.6/§5.1 + sole-metric §0), so it is counted apart and never scored as a stage -- it can
        # neither be read as CLEARED nor dilute the stall distribution. Everything noted below belongs to the NEW
        # segment, which is the one that will have to either reuse what this boundary produced, or stall.
        self._close_segment("advance")
        # ABDUCE-ON-REWARD: if we were directed-exploring the novel actors and the level just advanced, the directed
        # empowerment MANUFACTURED a reward -> abduce the objective from the reward residual, GATED (never self-certified).
        if self._directed is not None:
            fw, lw = self.frames[self._lvl0:], self._levels[self._lvl0:]
            try:
                mint, verdict = coupled_goal_mint(fw, lw, colour=self.tb_colour)
            except Exception:
                mint, verdict = None, "no-mint"
            if mint is not None:
                # MINTED is recorded here, upstream of mint_gate: parking a novel predicate for human confirmation is
                # a GATE decision, and scoring it as "no mint" would report the gate as a library failure.
                self.chain.note_mint()
                name = "+".join(sorted(a.name for a in mint.predicate.atoms))
                acted = self.mint_gate(verdict, name, float(getattr(mint, "bits", 0.0)),
                                       context="directed-empowerment@L%d" % self.level)
                # DIRECTIVE 2a: the Predicate OBJECT survives the mint site. φ did not die at run end -- it died
                # HERE, where this site used to reduce it to `name`, a string the echo clock cannot score and
                # `explains()` cannot evaluate. The gate still receives the name (it gates on identity); the OBJECT
                # goes to Γ's echo clock, keyed by its atom set, so a later residual can be scored against it.
                # NO `exceptions` HERE, ON PURPOSE. The sign is a per-family outcome split over the residual φ was
                # fitted to, and `coupled_goal_mint` does not return one -- it abduces an objective from the
                # REWARD stream, not from a scored (context, outcome) list. Synthesising one here would be
                # inventing evidence to fill an argument. A φ promoted by this route therefore reaches Γ as an
                # unsigned partition and can never become a directive, which is the correct and readable state:
                # `sign_report`'s `foreign_with_split` will show it as foreign-without-evidence rather than as a
                # sign that failed to agree. R_ρ owes its own outcome bit before it can steer anything.
                promoted = self.echo.observe_mint(
                    _task_id(self.game_id, self.level, self._seg_n, stream="rho"), mint)
                self.abduced.append(dict(from_level=self.level, verdict=verdict, name=name, acted=acted,
                                         predicate=mint.predicate, promoted=promoted,
                                         echo_tasks=self.echo.echo_tasks(mint.predicate)))
            self._directed = None

        prev = self.frames[-2] if len(self.frames) >= 2 else self.frames[-1]
        cur = self.frames[-1]
        delta = level_delta(prev, cur, old_avail, self._avail)
        transferred, novel, gone = diff_identities(prev_ids, self.tracker.loci())
        self.boundary = BoundaryDiff(level=new_level, transferred=transferred, novel=novel, gone=gone,
                                     new_colours=delta["new_colours"], gone_colours=delta["gone_colours"],
                                     new_actions=delta["new_actions"], gone_actions=delta["gone_actions"])
        # the §3.5 boundary diff RAN for the new segment. The residual is non-empty exactly when the transferred model
        # fails to account for the graduated environment: identities appeared/vanished, or the control set rebound.
        self.chain.note_diff(residual_nonempty=bool(novel or gone or self.boundary.rebinding))
        # ★ THE SEGMENT'S OTHER EVIDENCE, NAMED. `_close_segment("advance")` ran ABOVE, so this `note_diff` lands
        # in the NEW segment's ledger -- and that segment's own break-event receipt will still say
        # `diff_ran=False` if the transition/click residual never ran on it. Two DIFFERENT diffs, one ledger bit:
        # the open denominator candidate (R_τ had 6 receipts with a dead diff but only 4 DIED_PRE_DIFF) is exactly
        # that shape. This flag is set at the REAL call site so the receipt can SAY the boundary diff supplied the
        # segment's `diff_ran`, instead of the reader inferring it. Recording it is not endorsing it: if the two
        # numbers still do not reconcile with this on the record, the remainder is a different finding.
        self._seg_boundary_diff = True
        self.novel_loci = list(novel)                           # the new actors -> exploration/empowerment targets
        self.quarantine.tick()                                  # PARK decay: unresolved residuals age out

        self.prior = dict(family=self.family, cursor=self.cursor, vecs=dict(self.vecs),
                          passable=set(self.passable), tb_colour=self.tb_colour,
                          target_colour=self.target_colour, from_level=self.level)
        survives = self._referent_survives(cur)
        self._lvl0 = len(self.frames) - 1                       # the redraw frame starts the new level's stream
        # broken-by-REBINDING (control set changed) forces a re-fit even if the referent survives
        if self.boundary.rebinding:
            decision = "rederive(rebinding)"
        elif survives:
            decision = "keep"
        else:
            decision = "rederive"
        self.level_model = dict(level=new_level, family_before=self.family, decision=decision,
                                transferred=transferred, novel=novel, gone=gone, rebinding=self.boundary.rebinding,
                                new_colours=delta["new_colours"], gone_colours=delta["gone_colours"],
                                new_actions=delta["new_actions"], gone_actions=delta["gone_actions"])
        self.level_deltas.append(self.level_model)
        self.bb.post(_prefix(self.game_id), graduated_to=new_level, last_delta=self.level_model)
        if decision == "keep":
            self._reparameterize(cur)
            # two-body KEEP: the coupling transferred but the OBJECTIVE may have graduated -> aim empowerment at the
            # NOVEL loci (directed curiosity, primary) with the goal-hypothesis probe as fallback.
            if self.family == TWO_BODY:
                self._probe = GoalProbe(referent_colours=delta["new_colours"])
                self._directed = DirectedExplorer() if novel else None
        else:
            # unresolved mechanism at this boundary: PARK the novel-actor residual with a decay budget (beat C wakes
            # it by manufacturing reward). Any predicate minted from it later MUST clear novelty_ledger.guarded_promote.
            if novel:
                self.quarantine.park("novel@L%d" % new_level, dict(novel=novel, colours=delta["new_colours"]), budget=3)
            self._rederive()

    def _referent_survives(self, cur) -> bool:
        """Does the transferred organ's key referent still exist on the graduated level? (The cheap KEEP test.)"""
        if self.family == TWO_BODY and self.tb_colour is not None:
            return len(_two_bodies(cur, self.tb_colour)) >= 2
        if self.family == DIRECTIONAL and self.cursor is not None:
            return bool(np.any(np.asarray(cur) == self.cursor))
        if self.family == CLICK:
            return True
        return False

    def _reparameterize(self, cur) -> None:
        """Referent transferred: keep the family + motion/coupling model (the organ reads the live grid each step);
        only rebuild the cheap per-level bits."""
        if self.family == CLICK:
            self.prober = self._new_prober(cur)
        self.explorer = None                                     # coverage novelty is per-layout

    def _rederive(self) -> None:
        """Referent gone → a mechanic changed. Re-warm + re-route on the new level; the prior is retained (transfer)
        but the organ caches are cleared so the router relearns against the graduated environment."""
        self.family = PENDING
        self._warm_start = self.n_emitted
        self.cursor = None; self.vecs = {}; self.passable = set(); self.target_colour = None
        self.tb_colour = None; self.ag = None; self.tb_pass = [set(), set()]
        self.prober = None; self.explorer = None

    # ---- organ dispatch ----------------------------------------------------------------------------------------
    def _new_prober(self, grid) -> ClickProber:
        """THE ONLY PLACE A PROBER IS BUILT. There were two construction sites and only one of them passed the
        branch dict, so every click after a level re-parameterization was written into a private dict nobody
        reads: 126 clicks of a 1393-click sweep, counted at the exit and MISSING from the branch split. The
        published residue is what caught it -- but a second call site is how it happened, so there is now one.
        A carrier must be verified to have a LIVE INSTANCE before anything is wired to it."""
        return ClickProber(click_targets(grid), grid_sweep(grid, n=8), branch=self._click_branch)

    def _act_click(self) -> Tuple[str, Optional[dict]]:
        grid = self.frames[-1]
        if self.prober is None:
            self.prober = self._new_prober(grid)
        elif len(self.frames) >= 2:
            self.prober.observe(self.frames[-2], self.frames[-1])   # credit the previous click
            self.prober.refresh(click_targets(grid))
        tgt = self.prober.choose()
        if tgt is None:
            return "A6", {"x": 0, "y": 0}
        r, c = tgt
        return "A6", {"x": int(c), "y": int(r)}

    def _act_two_body(self, labels: List[str]) -> Tuple[str, Optional[dict]]:
        grid = self.frames[-1]; h, w = grid.shape
        bodies = _two_bodies(grid, self.tb_colour)
        def passpx(i, dest, _g=grid, _h=h, _w=w, _p=self.tb_pass):
            r, c = dest
            return 0 <= r < _h and 0 <= c < _w and (not _p[i] or int(_g[r, c]) in _p[i])
        def passcell(i, cell, _g=grid, _h=h, _w=w, _s=self.stride, _p=self.tb_pass):
            r, c = cell[0] * _s, cell[1] * _s
            return 0 <= r < _h and 0 <= c < _w and (not _p[i] or int(_g[r, c]) in _p[i])
        # BOUNDARY-DIRECTED EMPOWERMENT (post-KEEP, reward still 0): aim curiosity at the NOVEL loci -- drive a body
        # toward the least-probed / most-affectable new actor, crediting contact that CHANGES it. Manufactures a
        # gradient where the objective is a needle (Tether §4.4). Preferred over the undirected goal-hypothesis probe.
        if self._directed is not None and self.novel_loci and len(bodies) >= 2:
            self._directed.credit(self._novel_changed(self._directed._last))   # empowerment feedback for last target
            targets = []
            for lid in self.novel_loci:
                l = self.tracker.get(lid)
                if l is not None:
                    targets.append((lid, (int(round(l.centroid[0])), int(round(l.centroid[1])))))
            pick = self._directed.choose(targets)
            if pick is not None:
                lbl = two_body_goal_action(bodies, self.ag, passpx, pick[1], which=0) or self._cycle(labels)
                return lbl, None
        # GOAL-HYPOTHESIS probe (post-KEEP graduation): drive toward the current hypothesis referent, rotating
        if self._probe is not None:
            kind, colour = self._probe.current()
            self._probe.tick()
            new_actors = (self.level_model or {}).get("new_colours", []) if self.level_model else []
            if kind == "deliver" and len(bodies) >= 2:
                zones = _largest_zones(grid, new_actors, exclude=self.tb_colour, k=2)
                if len(zones) >= 2:
                    (c0, r0), (c1, r1) = _assign_zones(bodies, zones, self.stride)
                    lbl = (two_body_deliver_action(bodies, self.ag, passcell, c0, c1, self.stride,
                                                   reach0=r0, reach1=r1)
                           or two_body_goal_action(bodies, self.ag, passpx, c0, which=0)
                           or self._cycle(labels))
                    return lbl, None
            elif kind == "near" and colour is not None and len(bodies) >= 2:
                tgt = _nearest_colour_centroid(grid, colour, bodies[0], exclude=self.tb_colour)
                if tgt is not None:
                    lbl = two_body_goal_action(bodies, self.ag, passpx, tgt, which=0) or self._cycle(labels)
                    return lbl, None
            # kind == "meet" (or unresolved) -> fall through to the MEET driver below
        if len(bodies) < 2:
            return self._cycle(labels), None                        # merged/lost -> nudge
        lbl = (two_body_search_action(bodies, self.ag, passcell, self.stride)
               or two_body_drive_action(bodies, self.ag, passpx)
               or self._cycle(labels))
        return lbl, None

    def _ma_targets(self, bodies, grid) -> Optional[List[Tuple[int, int]]]:
        """Assign each independently-steerable avatar to its OWN goal, FRAME-NATIVELY: candidate goals are the referent
        regions the avatars are NOT standing on (the reference cells they must reach); each avatar takes its nearest
        distinct goal (greedy). None if there are fewer goal referents than avatars (nothing to route to). Names no
        game -- the goals come from the referent detector, the assignment from geometry."""
        goals: List[Tuple[int, int]] = []
        for r in self._referents:
            r0, c0, r1, c1 = r.bbox
            if any(r0 <= b[0] <= r1 and c0 <= b[1] <= c1 for b in bodies):    # skip the region an avatar occupies
                continue
            goals.append((int(round((r0 + r1) / 2.0)), int(round((c0 + c1) / 2.0))))
        if len(goals) < len(bodies):
            return None
        assigned: List[Optional[Tuple[int, int]]] = [None] * len(bodies)
        used: set = set()
        for i in range(len(bodies)):
            best, bd = None, None
            for j, g in enumerate(goals):
                if j in used:
                    continue
                d = abs(bodies[i][0] - g[0]) + abs(bodies[i][1] - g[1])
                if bd is None or d < bd:
                    bd, best = d, j
            if best is None:
                return None
            used.add(best); assigned[i] = goals[best]
        return [t for t in assigned if t is not None]

    def _act_multi_avatar(self, labels: List[str]) -> Tuple[str, Optional[dict]]:
        """G5: route TWO independently-steerable avatars, each toward its own goal referent, using the learned per-body
        maps (the coupled organ's is_coupled bar rejected these, so the two-body driver never fired). Falls back to a
        cycle when goals or a helpful action are missing -- so it never freezes and keeps gathering evidence."""
        grid = self.frames[-1]; h, w = grid.shape
        bodies = _two_bodies(grid, self.tb_colour)
        if len(bodies) < 2:
            return self._cycle(labels), None
        targets = self._ma_targets(bodies, grid)
        if targets is None:
            return self._cycle(labels), None
        def passpx(i, dest, _g=grid, _h=h, _w=w, _p=self.tb_pass):
            r, c = dest
            return 0 <= r < _h and 0 <= c < _w and (not _p[i] or int(_g[r, c]) in _p[i])
        lbl = multi_avatar_action(bodies, self.ag, passpx, targets)
        if lbl is not None:
            self.n_multi_avatar_drive += 1
        return (lbl or self._cycle(labels)), None

    def _act_directional(self, labels: List[str]) -> Tuple[str, Optional[dict]]:
        grid = self.frames[-1]; h, w = grid.shape
        cur = _px_centroid(grid, self.cursor)
        if cur is None:
            return self._exit("dir_no_avatar", (self._cycle(labels), None))
        def passable_px(dest, _g=grid, _h=h, _w=w, _p=self.passable):
            r, c = dest
            return 0 <= r < _h and 0 <= c < _w and int(_g[r, c]) in _p
        avatar = (int(round(cur[0])), int(round(cur[1])))
        # Brick 3: steer toward the relation the env is REWARDING -- but only once EARNED. A relation drives the target
        # ONLY when the tester has CONFIDENTLY selected it (its discrepancy is measurably shrinking under play). Before
        # that, exploration is left untouched, so curiosity still gathers affordance/effect evidence (the earlier organs
        # are not starved by an unconfirmed hypothesis). Committed wins never reach here (two-body + click are separate
        # families). This is the honest test-then-commit: hypothesise, watch the env's own signal, steer only on confirm.
        rsel, rtgt = self._relation_selected, self.relations.drive_target()
        if rsel is not None and rtgt is not None:
            target = (max(0, min(h - 1, int(rtgt[0]))), max(0, min(w - 1, int(rtgt[1]))))
            lbl = (bfs_path_action(grid, avatar, target, self.vecs, self.passable, self.stride)
                   or plan_action(avatar, target, self.vecs, ACTS_TOWARD, passable_px))
            if lbl:
                self.n_relation_drive += 1
                return self._exit("dir_relation_drive", (lbl, None))
        if self.target_colour is not None:
            tgt = approachable_component_centroid(grid, self.target_colour, self.passable)
            if tgt is not None:
                target = (int(round(tgt[0])), int(round(tgt[1])))
                lbl = (bfs_path_action(grid, avatar, target, self.vecs, self.passable, self.stride)
                       or plan_action(avatar, target, self.vecs, ACTS_TOWARD, passable_px))
                if lbl:
                    return self._exit("dir_target_colour", (lbl, None))
        gl = self._gamma_directive(labels)
        if gl is not None:
            return self._exit("dir_gamma", (gl, None))
        # `dir_gamma` + `dir_explore` is the REACH of the Γ site, counted here at the two exits BELOW it, entirely
        # independently of `_g_reached`, which is counted INSIDE it. Two independent counters of the same event
        # that disagree mean one of them is wrong, and the summary publishes the difference rather than trusting
        # either -- the point of a receipt is that it can be contradicted.
        return self._exit("dir_explore",
                          (self._explore(avatar, passable_px, labels), None))   # no target / boxed -> curiosity

    def _gamma_directive(self, labels: List[str]) -> Optional[str]:
        """★ THE ONLY PLACE THE SHARED LIBRARY IS ALLOWED TO CHANGE WHAT THE AGENT DOES.

        Until this existed, Γ was a museum: φ minted on one game, promoted when it echoed on another, and then
        consulted only to EXPLAIN a residual after the fact. Explaining is a claim about the past. This is the
        first site where a rule learned on one game can pick the next action on a different one.

        FOUR REFUSALS, each of which is the whole point:

        (1) IT ASKS `directives`, NOT `library`. Γ's promoted list is a set of PARTITIONS -- "these steps differ
            from those" -- and a partition is not advice. `directives` returns only the φ this game did not mint
            AND on which every family that could vote agreed which side carries the outcome. An offline audit of
            the real library found four promoted φ and ZERO that pass that, so the expected return here is [] for
            a long time yet. That is the honest state of Γ, not a bug in this function.

        (2) AN EMPTY OFFER IS NOT AN ATTEMPT. `note_reuse_attempt` fires only when Γ actually had something to
            say -- identical to the rule at the residual site, and for the identical reason: counting a consult
            of an empty library as a reuse attempt would manufacture MINTED_UNUSED, the one code that indicts the
            architecture, out of bookkeeping.

        (3) THE CONTEXT IS BUILT BY `bridge.decision_context`, THE SAME FUNCTION THE RESIDUAL SITE USES. Every
            promoted φ was fitted to contexts where `target_rc` IS the focus and `intended_free` is keyed off the
            CALIBRATED passable set. `planner.plan_action` builds a Context too, but with `focus_colour=0` and
            default `intended_*` -- so a φ evaluated there would silently be answering about a board that does
            not exist. A predicate asked the wrong question still returns a bool; that is exactly why there must
            be one construction and why this site does not roll its own.

        (4) A TIE IS NOT A PREFERENCE. If two candidate actions score equally, Γ is refused the pick and control
            falls through to curiosity. Otherwise label ordering would break the tie and the receipt would credit
            Γ for a choice an alphabet made.

        ★ WHAT THIS DOES TO THE STAGE DISTRIBUTION, SAID BEFORE IT HAPPENS. `note_reuse` here sets the same
        segment signal the `explains` route sets, and `classify` coerces "reused implies minted" -- so a segment
        whose diff ran on a non-empty residual and did not mint would be lifted from MINT_UNFIRED to
        USED_NOCLEAR by a directive. That is a defensible reading (a transferred rule really was used, and really
        did not clear anything) but it is also precisely the shape of a chain built to make its own instrument
        read higher. Two guards: the receipt records `reuse_source` so the two organs are never one number, and
        the pre-registration for the first sweep is ZERO directives and therefore ZERO movement in the
        distribution. If the distribution moves, that is a finding to investigate, not a result to report.

        Placed LAST in `_act_directional`, after every earned drive: Γ advises only where the agent had no reason
        of its own. A first wiring that could override a confirmed relation target would make any change in
        outcome unattributable between the two."""
        self._g_reached += 1
        if not self._g_entry_report:
            try:                                            # Γ's state AS SEEN HERE, once per segment (see __init__)
                self._g_entry_report = dict(self.echo.sign_report(self.game_id))
            except Exception:
                self._g_entry_report = {}
        if self.cursor is None or not self.vecs or not self.frames:
            self._g_noseam += 1
            return None
        try:
            dirs = self.echo.directives(self.game_id)
        except Exception:
            self._g_error += 1                              # BROKEN, not empty -- counted apart (see __init__)
            return None                                     # Γ must never sink a run
        if not dirs:
            self._g_empty += 1
            return None                                     # NOT an attempt -- see refusal (2)
        self.chain.note_reuse_attempt()
        self._g_consult += 1
        self._g_dirs = len(dirs)
        grid = self.frames[-1]
        best: Optional[str] = None
        best_score = 0.0
        ties = 0
        for lbl in labels:
            vec = (self.vecs or {}).get(lbl)
            if not vec or tuple(vec) == (0, 0):
                continue
            ctx = decision_context(grid, self.cursor, vec, stride=self.stride, passable=self.passable)
            if ctx is None:
                self._g_uneval += 1
                continue
            # +s when φ holds, -s when it does not: a NEGATIVE sign means the outcome lives on the ¬φ side, so
            # ¬φ is the endorsement. Reading a negative sign as "no opinion" would throw away half of what was
            # measured and would quietly make every directive a one-sided rule.
            score = float(sum(s if p.holds(ctx) else -s for p, s in dirs))
            if best is None or score > best_score:
                best, best_score, ties = lbl, score, 1
            elif score == best_score:
                ties += 1
        # THE THREE WAYS A CONSULTED Γ STILL SAYS NOTHING, SPLIT. These were one `return None` under a three-clause
        # `or`, which is an exit name covering three branches: "no label had an evaluable context", "Γ endorsed
        # nothing positively" and "two candidates tied" are a seam failure, a sign failure and a refusal, and they
        # have nothing to do with each other. Split in the ORIGINAL short-circuit order, so what the agent does is
        # bit-identical; only the name is new.
        if best is None:
            self.chain.note_reuse_exit("dir_no_evaluable")
            return None
        if best_score <= 0.0:
            self.chain.note_reuse_exit("dir_no_endorsement")
            return None
        if ties > 1:
            self.chain.note_reuse_exit("dir_tie")
            return None                                     # no preference between equals -- refusal (4)
        self.chain.note_reuse()
        self.chain.note_reuse_exit("dir_acted")
        self._g_act += 1
        return best

    def _explore(self, avatar, passable_px, labels: List[str]) -> str:
        if self.explorer is None:
            self.explorer = CuriosityExplorer()
        pick = self.explorer.choose(avatar, self.vecs, passable_px, self.stride)
        if pick is None:
            return self._progress_reinforce(self._cycle(labels), labels)
        lbl, cell = pick
        self.explorer.visit(lbl, cell)
        return self._progress_reinforce(lbl, labels)          # bias undirected exploration up the progress gradient

    def _progress_reinforce(self, lbl: str, labels: List[str]) -> str:
        """Brick 1: when a CONFIDENT progress signal exists, nudge an EXPLORATORY pick toward the available action that
        has historically RAISED progress the most (the authors' 'follow the bar'). Only swaps to a strictly-positive,
        better-credited action; otherwise the original curiosity pick stands. Applied ONLY at exploratory picks
        (directional curiosity / effect) -- committed organ plans (two-body BFS, reach-target, click coords) are
        untouched, so the wins are preserved. General: it ranks by measured progress-per-action, names no game."""
        if not self.progress.confident() or not self._prog_credit:
            return lbl
        cand = [l for l in labels if l != "A6"]               # click coords aren't a per-label credit
        best = max(cand, key=lambda x: self._prog_credit.get(x, 0.0), default=None)
        if best is not None and self._prog_credit.get(best, 0.0) > self._prog_credit.get(lbl, 0.0) \
                and self._prog_credit.get(best, 0.0) > 0.0 and best != lbl:
            self.n_prog_reinforce += 1
            return best
        return lbl

    def _relation_reinforce(self, lbl: str, labels: List[str]) -> str:
        """Brick 4b + probe: nudge an EXPLORATORY effect pick toward the action that has historically CLOSED the DRIVEN
        relation's discrepancy the most -- the no-cursor analogue of the directional relation drive (a legend/effect game
        has no cursor to route, but the effect action that shrinks the gap is still learnable and repeatable). The driven
        relation is the confidently-SELECTED one, or -- before selection -- the largest MEASURED gap being epistemically
        probed (`_probe_rel`), so a measured-but-unselected relation gets intervened on until the tester can select it.
        Leaves click (A6) coords untouched so the click win is safe. Only swaps to a strictly-positive, better-credited
        action; else lbl stands -- so a probe with no gap-closing evidence yet changes nothing."""
        if self._probe_rel is None or not self._rel_credit:
            return lbl
        cand = [l for l in labels if l != "A6"]
        best = max(cand, key=lambda x: self._rel_credit.get(x, 0.0), default=None)
        if best is not None and self._rel_credit.get(best, 0.0) > self._rel_credit.get(lbl, 0.0) \
                and self._rel_credit.get(best, 0.0) > 0.0 and best != lbl:
            self.n_rel_reinforce += 1
            return best
        return lbl

    def _act_effect(self, labels: List[str]) -> Tuple[str, Optional[dict]]:
        """Tier-1 affordance drive: press the EFFECTIVE actions (learned live from R_τ), avoiding no-ops / undo,
        curiosity-ordered within the effective set. Cold start explores to gather effect evidence. Purposeful action
        on paint/toggle/place games that have no drivable cursor."""
        a = self.effect_aff.choose(labels, self._effect_visits)
        a = self._progress_reinforce(a, labels)               # bias the effective-action pick up the progress gradient
        a = self._relation_reinforce(a, labels)               # then toward closing the SELECTED relation's discrepancy
        self._effect_visits[a] = self._effect_visits.get(a, 0) + 1
        return a, None

    def _act_fallback(self, labels: List[str]) -> Tuple[str, Optional[dict]]:
        return self._cycle(labels), None
