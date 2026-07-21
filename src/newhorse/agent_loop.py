"""
agent_loop.py -- THE MAP SS9.6: loop closure. PERCEIVE -> THINK -> MAP -> ACT, both feedback arrows.
Monolith-then-carve: this is the small COMPLETE loop that turns the six bricks into one running thing.

Wiring (LOOSELY coupled -- FMap: kauffman_nk_landscapes warns that tight coupling makes an untunable
rugged landscape, so each module stays independently constructed + swappable):
  PERCEIVE  perception.segment + ObjectTracker   -> the controllable object, held steady through change
  THINK     GENERIC transforms as hypotheses      -> filtered by the falsified ledger (skip dead ones)
  MAP       marketplace.informative_salience      -> score each hypothesis by the residual it leaves
  ACT       commit the best-believed action        -> take it, observe the real next frame
  FEEDBACK  residual bus banks surprise (brake); ledger records what predicted wrong (express-before-
            judge); pose.learn moves alpha (did private belief beat a naive social prior?); belief updates.

NEVER ENCODE THE ANSWER: the transforms are GENERIC perceptual moves (identity + unit shifts); WHICH
action causes WHICH transform is the game's secret, DISCOVERED by prediction error, never given.
Nothing silent: every step narrates perceive/commit/learn.

HARD BOUNDS live on the loop's MANDATORY paths (brick 8, bounds.py): perceive() admits every frame
through the ResolutionBound (no downsampling), and reset() routes through the ResetGate (RESET is
banned in active play unless a credit was EARNED by a completed level). Neither has an off-switch.
"""
from __future__ import annotations
from typing import Callable, Dict, List, Tuple, Optional
import numpy as np
from .perception import segment, ObjectTracker, Object
from .residual import ResidualBus, sense
from .falsified_ledger import FalsifiedLedger
from .two_streams import Pose
from .marketplace import informative_salience
from .bounds import ResetGate, ResolutionBound   # the hard bounds, enforced on the loop's mandatory paths
from .exploration import Explorer                 # brick 10a: novelty drive (anti-collapse)
from .self_locus import SelfLocus                 # brick 10b: controllable-ID by action contingency
from .agency import CursorAgency                  # brick 12: agent-vs-environment separation (discriminative cursor)
from .navigation import GridNav, _unit            # brick 13: directed-edge maze navigation
from .goal import GoalManager                     # brick 14: candidate goals priced by reward
from .budget import BudgetModel                    # brick 15: induced action budget (the depleting HUD bar)
from .relations import candidate_relations, quantified_candidates, class_member_cells  # brick 17/18: typed + quantified win-relations


# --- GENERIC transforms (NOT answers): move the controllable's cells by a unit delta, or identity ---
def unit_transforms() -> Dict[str, Tuple[int, int]]:
    return {"STAY": (0, 0), "UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


class AgentLoop:
    def __init__(self, actions: List[str], transforms: Optional[Dict[str, Tuple[int, int]]] = None,
                 background: int = 0):
        self.actions = list(actions)
        self.transforms = transforms or unit_transforms()
        self.bg = background
        self.tracker = ObjectTracker()
        self.residuals = ResidualBus()
        self.ledger = FalsifiedLedger(half_life=12.0)
        self.pose = Pose()
        self.belief: Dict[Tuple[str, str], float] = {}     # (action, transform) -> learned confidence
        self.clock = 0
        self.log: List[str] = []
        # HARD BOUNDS (bounds.py, constitutional -- no flag disables them; instantiated unconditionally):
        self.reset_gate = ResetGate()                       # RESET banned in active play unless earned
        self.res_bound = ResolutionBound()                  # the grid is never downsampled
        # brick 10: exploration drive (anti-collapse) + self-locus controllable-ID (action contingency)
        self.explorer = Explorer()
        self.locus = SelfLocus()
        self._cur_objs: List[Object] = []
        # brick 12: agent-vs-environment separation -- the discriminative cursor + its per-action move map
        self.agency = CursorAgency(background=background)
        # brick 13/14: maze navigation (directed-edge walls) + a reward-priced market of candidate goals
        self.nav = GridNav()
        self.goals = GoalManager()
        self.budget = BudgetModel()               # brick 15: know the action budget (the depleting HUD bar)
        self._base_stall = self.goals.stall_steps
        self._pending_reward = False              # set by signal_reward() on a level-up; consumed in observe()
        self._quant_key: Optional[Tuple] = None   # brick 18: the ALL-class currently pursued
        self._visited: set = set()                # members of the active ALL-class the cursor has reached

    def signal_reward(self) -> None:
        """Tell the goal market a REWARD just occurred (a level advanced) -- consumed on the next observe()
        to CONFIRM the goal being pursued. Called by the live runner / harness when levels_completed rises."""
        self._pending_reward = True

    def _cell(self, centroid: Tuple[float, float], stride: int) -> Tuple[int, int]:
        """Logical-cell coordinate of a pixel centroid at the world's move quantum (stride)."""
        s = max(1, stride)
        return (int(round(centroid[0] / s)), int(round(centroid[1] / s)))

    def _nav_subgoal(self, gkey: Tuple, ccell: Tuple[int, int], stride: int) -> Optional[Tuple[int, int]]:
        """The cell to navigate to for the active goal. A single-target relation -> its target cell. A
        QUANTIFIED ALL(colour) -> the NEAREST UNVISITED member of that class (reduce violators one at a time,
        lindblom); None if all members are already visited (the whole-set objective is complete this cycle)."""
        if gkey[0] != "ALL":
            self._quant_key = None
            return gkey[1]
        if self._quant_key != gkey:                          # switched to a new ALL-class -> fresh visited set
            self._quant_key = gkey
            self._visited = set()
        members = class_member_cells(self._cur_objs, gkey[1], stride)
        unvisited = [m for m in members if m not in self._visited]
        if not unvisited:
            return None                                      # all members reached -> nothing left to navigate to
        return min(unvisited, key=lambda m: abs(m[0] - ccell[0]) + abs(m[1] - ccell[1]))

    def _cursor_cell_in(self, frame: np.ndarray, stride: int) -> Optional[Tuple[int, int]]:
        """Logical cell of the cursor as seen in `frame` (largest component of the cursor colour)."""
        col = self.agency.cursor_colour()
        if col is None:
            return None
        cands = [o for o in segment(frame, background=self.bg) if col in o.colours]
        if not cands:
            return None
        return self._cell(max(cands, key=lambda o: o.size).centroid, stride)

    # ---- HARD BOUNDS on the mandatory paths --------------------------------------------
    def earn_progress(self, *, level_completed: bool, reason: str = "") -> bool:
        """The ONLY way a reset credit is minted -- and only on a genuinely completed level, never a
        mere attempt. (Brick 9's live gate calls this when levels_completed increments.)"""
        ok = self.reset_gate.earn(level_completed=level_completed, reason=reason)
        self.log.append("PROGRESS  level_completed=%s -> reset credit %s (%s)"
                        % (level_completed, "minted" if ok else "denied", reason))
        return ok

    def reset(self, *, reason: str = "") -> None:
        """A RESET routes THROUGH the gate: it raises ResetForbidden unless a credit was earned -- there
        is no bypass. A permitted reset clears the BOARD state (a fresh tracker) but NEVER the learned
        lineage (belief/pose/ledger) and NEVER the brake's PE-integral (the man dies, the lineage learns)."""
        self.reset_gate.request_reset(reason=reason)        # raises ResetForbidden if unearned
        self.tracker = ObjectTracker()                      # fresh board identities only
        self.log.append("RESET  permitted+executed; board cleared, lineage+brake preserved (%s)" % reason)

    # ---- PERCEIVE ----------------------------------------------------------------------
    def perceive(self, frame: np.ndarray) -> Optional[Object]:
        frame = self.res_bound.admit(frame)                 # HARD BOUND: no downsampling, on the mandatory path
        objs = self.tracker.update(segment(frame, background=self.bg))
        if not objs:
            return None
        self._cur_objs = objs
        ctrl = None
        cur_col = self.agency.cursor_colour()               # brick 12: the discriminative cursor (best evidence)
        if cur_col is not None:
            cands = [o for o in objs if cur_col in o.colours]
            if cands:
                ctrl = min(cands, key=lambda o: o.size)
        if ctrl is None:                                    # brick 10b fallback: colour contingency
            ctrl = self.locus.pick(objs)
        if ctrl is None:                                    # cold start -> heuristic (smallest distinct object)
            ctrl = min(objs, key=lambda o: o.size)
        self.log.append("PERCEIVE  %d object(s); controllable id=%s size=%d (cursor_colour=%s)"
                        % (len(objs), ctrl.oid, ctrl.size, cur_col))
        return ctrl

    def _apply(self, frame: np.ndarray, ctrl: Object, delta: Tuple[int, int]) -> np.ndarray:
        """Predict the next frame if the controllable moves by delta (generic; bounded to the grid)."""
        out = np.array(frame); dr, dc = delta
        colour = next(iter(ctrl.colours))
        for (r, c) in ctrl.cells:
            out[r, c] = self.bg
        for (r, c) in ctrl.cells:
            nr, nc = r + dr, c + dc
            if 0 <= nr < out.shape[0] and 0 <= nc < out.shape[1]:
                out[nr, nc] = colour
            else:
                out[r, c] = colour                          # blocked at the wall -> stays (a plausible hypothesis)
        return out

    def _sig(self, action: str, tname: str) -> str:
        return "%s->%s" % (action, tname)

    # ---- THINK + MAP + ACT -------------------------------------------------------------
    def choose(self, frame: np.ndarray, ctrl: Object) -> Tuple[str, str, np.ndarray]:
        """Commit an action + its predicted effect. Once the agency has SEPARATED the cursor from the
        environment (brick 12), predict the cursor's true multi-cell MOVE from the learned per-action map;
        keep covering under-tried actions so the whole map is learned. Cold start: the unit-transform path."""
        if self.agency.ready():
            amap = self.agency.action_map()
            dir2action = {_unit(v): a for a, v in amap.items()}   # unit direction -> the action that causes it
            stride = self.agency.stride() or 1
            # COVERAGE-FIRST: try every action enough to complete the move-map BEFORE navigating -- else we'd
            # path with only some directions known and get stuck moving toward a goal we can't approach.
            undertried = [a for a in self.actions if self.explorer.visits.get(a, 0) < 2]
            if not undertried:
                # brick 15: as the budget depletes, COMMIT -- persist longer on the best goal before rotating
                # (optimal foraging: commit to the best patch as time runs low). A proven-unreachable goal is
                # still abandoned (nav can't reach it -> it eventually stalls even at the raised tolerance).
                frac = self.budget.fraction_left(frame)
                self.goals.stall_steps = int(self._base_stall * (3 if (frac is not None and frac < 0.4) else 1))
                # propose TYPED (brick 17: BE_AT/TOUCH/COVER) + QUANTIFIED (brick 18: ALL over a colour-class)
                # relation hypotheses; reward confirms which actually wins (brick 14 market)
                cc = self.agency.cursor_colour()
                self.goals.propose(candidate_relations(self._cur_objs, cc, stride))
                self.goals.propose(quantified_candidates(self._cur_objs, cc, stride))
                gkey = self.goals.active_goal()
                if gkey is not None and dir2action:
                    ccell = self._cell(ctrl.centroid, stride)
                    gcell = self._nav_subgoal(gkey, ccell, stride)    # brick 18: nearest unvisited member for ALL
                    if gcell is not None:
                        d = self.nav.step_toward(ccell, gcell, list(dir2action))
                        if d is not None and d in dir2action:
                            action = dir2action[d]
                            pred = self._apply(frame, ctrl, amap[action])
                            self.log.append("COMMIT(nav)  %s dir=%s from=%s goal=%s(%s)"
                                            % (action, d, ccell, gkey[0], gcell))
                            return action, "MOVE", pred
            # still learning the map (or no target/route) -> coverage-first, then novelty
            target = min(self.actions, key=lambda a: (self.explorer.visits.get(a, 0), -self.explorer.bonus(a)))
            vec = self.agency.predict(target)
            delta = vec if vec is not None else (0, 0)      # unmapped action -> STAY probe (its move gets learned)
            pred = self._apply(frame, ctrl, delta)
            self.log.append("COMMIT(agency)  %s move=%s stride=%s" % (target, delta, self.agency.stride()))
            return target, "MOVE", pred
        best = None
        for a in self.actions:
            for tname, delta in self.transforms.items():
                sig = self._sig(a, tname)
                if self.ledger.is_refuted(sig, self.clock):
                    continue                                # skip dead ideas (falsified ledger)
                conf = self.belief.get((a, tname), 0.0)
                social = 1.0 / len(self.transforms)         # flat prior (Stream B, no opinion yet)
                # exploit (alpha-weighted belief) + EXPLORE (novelty bonus per action -> can't collapse to one)
                score = self.pose.decide(private=conf, social=social) + self.explorer.bonus(a)
                if best is None or score > best[0]:
                    best = (score, a, tname, delta)
        if best is None:                                    # everything refuted -> forced explore (STAY)
            a, tname = self.actions[0], "STAY"; return a, tname, self._apply(frame, ctrl, (0, 0))
        _, a, tname, delta = best
        pred = self._apply(frame, ctrl, delta)
        self.log.append("COMMIT  %s (belief=%.2f, alpha=%.2f)" % (self._sig(a, tname), self.belief.get((a, tname), 0.0), self.pose.alpha))
        return a, tname, pred

    # ---- FEEDBACK ----------------------------------------------------------------------
    def observe(self, before: np.ndarray, ctrl: Object, action: str, committed_tname: str, after: np.ndarray):
        # score EVERY transform of the taken action against the real outcome (the residual is the currency)
        errs = {}
        for tname, delta in self.transforms.items():
            pred = self._apply(before, ctrl, delta)
            errs[tname] = float(sense(pred, after).bits)    # prediction error in bits
            sal = informative_salience(before, pred, after)
            self.belief[(action, tname)] = 0.8 * self.belief.get((action, tname), 0.0) + 0.2 * sal  # learn confidence
        # the transforms that got it WRONG this trial are recorded (express-before-judge: the action RAN)
        best_t = min(errs, key=errs.get)
        for tname in self.transforms:
            sig = self._sig(action, tname)
            self.ledger.record(sig, trial_ran=True, made_progress=(tname == best_t), now=self.clock)
        # the pose learns: did our COMMITTED (private) hypothesis beat a naive social prior (assume STAY)?
        private_err = errs.get(committed_tname, min(errs.values()))   # "MOVE" is not a unit transform -> proxy
        self.pose.learn(private_error=private_err, social_error=errs.get("STAY", max(errs.values())))
        # the brake: bank the surprise the committed prediction actually left (unit transform OR the agency MOVE)
        committed_delta = self.transforms.get(committed_tname)
        if committed_delta is None:                          # "MOVE" -> the agency's learned per-action vector
            committed_delta = self.agency.predict(action) or (0, 0)
        committed_pred = self._apply(before, ctrl, committed_delta)
        self.residuals.observe(sense(committed_pred, after))
        # brick 12: the agency learns which colour is the cursor + its per-action move (agent vs environment)
        self.agency.observe(before, action, after)
        # brick 15: the budget model watches the HUD bar deplete
        self.budget.observe(before, after)
        # brick 13: navigation learns walls -- a committed MOVE that did NOT move the cursor is a BLOCKED edge
        if committed_tname == "MOVE" and self.agency.ready():
            stride = self.agency.stride() or 1
            d = _unit(self.agency.predict(action) or (0, 0))
            after_cell = self._cursor_cell_in(after, stride)
            prev_cell = self._cell(ctrl.centroid, stride)
            if d != (0, 0) and after_cell is not None:
                self.nav.observe_move(prev_cell, d, moved=(after_cell != prev_cell))
            self.nav.decay()
            # brick 14/17: the goal market learns which RELATION wins. On a REWARD, credit the relation whose
            # target is the cell the cursor WON at (its pre-respawn destination), not the nominally-active one.
            if self._pending_reward:
                win_cell = (prev_cell[0] + d[0], prev_cell[1] + d[1])
                self.goals.credit(win_cell)
            else:
                active = self.goals.active
                if active is not None and active[0] == "ALL":
                    # brick 18: mark the reached member visited; the goal is "reached" only when ALL are
                    # visited (goodhart guard: one member is NOT the whole set). No reward then -> demote.
                    if after_cell is not None:
                        members = set(class_member_cells(self._cur_objs, active[1], stride))
                        if after_cell in members:
                            self._visited.add(after_cell)
                        reached = members.issubset(self._visited) and len(members) > 0
                    else:
                        reached = False
                    self.goals.observe(reached=reached, reward=False)
                    if reached:
                        self._visited = set()                # completed the set with no reward -> reset to re-test
                else:
                    reached = (active is not None and after_cell is not None and after_cell == active[1])
                    self.goals.observe(reached=reached, reward=False)
        self._pending_reward = False                        # consume the one-shot reward signal each step
        # brick 10b: self-locus learns which colour's motion is CONTINGENT on this action (fallback ID)
        self.locus.observe(action, segment(before, background=self.bg), segment(after, background=self.bg))
        # brick 10a: the action ran -> its novelty is partly spent (drives coverage on the next choose)
        self.explorer.visit(action)
        self.clock += 1

    def step(self, frame: np.ndarray, env_step: Callable[[str], np.ndarray]) -> str:
        """One closed cycle. env_step(action) -> next frame (the world). Returns the action taken."""
        ctrl = self.perceive(frame)
        if ctrl is None:
            return self.actions[0]
        action, tname, _pred = self.choose(frame, ctrl)
        after = np.asarray(env_step(action))
        self.observe(frame, ctrl, action, tname, after)
        return action
