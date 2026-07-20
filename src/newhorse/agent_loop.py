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
        ctrl = min(objs, key=lambda o: o.size)             # generic: the small distinct object is the controllable
        self.log.append("PERCEIVE  %d object(s); controllable id=%s size=%d" % (len(objs), ctrl.oid, ctrl.size))
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
        """Commit the (action, transform) hypothesis we most believe AND that isn't refuted, blended with
        exploration by the pose's alpha (private belief vs a flat social prior)."""
        best = None
        for a in self.actions:
            for tname, delta in self.transforms.items():
                sig = self._sig(a, tname)
                if self.ledger.is_refuted(sig, self.clock):
                    continue                                # skip dead ideas (falsified ledger)
                conf = self.belief.get((a, tname), 0.0)
                social = 1.0 / len(self.transforms)         # flat prior (Stream B, no opinion yet)
                score = self.pose.decide(private=conf, social=social)   # alpha-weighted blend
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
        self.pose.learn(private_error=errs[committed_tname], social_error=errs.get("STAY", max(errs.values())))
        # the brake: bank the surprise the committed prediction actually left
        committed_pred = self._apply(before, ctrl, self.transforms[committed_tname])
        self.residuals.observe(sense(committed_pred, after))
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
