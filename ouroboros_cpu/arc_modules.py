"""arc_modules.py — environment-SPECIFIC interface for REAL ARC-AGI-3 games (arc_agi.Arcade, OFFLINE, local).
Conforms to the SAME EnvAdapter contract as SparseworldAdapter, so the pure core (prime_modules) and the
intrinsic-gradient race harness run on real games UNCHANGED by swapping this adapter in. No API, local only.
This is the modularity payoff: one new interface, everything above it reused."""
import numpy as np
import arc_agi
try:
    from arc_agi.base import OperationMode
except Exception:
    try:
        from arc_agi import OperationMode
    except Exception:
        OperationMode = None
from arcengine import GameAction, GameState
from self_model import SelfLocusModel
import grid_perception as GP
_AM={i:getattr(GameAction,f"ACTION{i}") for i in range(1,8)}; _AM[0]=GameAction.RESET

import os
class ArcAdapter:
    def __init__(self, game_id, env_dir='env/environment_files'):
        os.environ.setdefault("ONLY_RESET_LEVELS", "true")   # engine: RESET resets the CURRENT level, not the whole game
        self.arc=arc_agi.Arcade(arc_api_key="", operation_mode=OperationMode.OFFLINE, environments_dir=env_dir)
        self.game_id=game_id; self.env=None; self._obs=None; self.slm=SelfLocusModel(); self._spec=None
        self.level_local=False                               # when True, reset() resets only the current level
        from collections import deque as _dq
        self.transition_buffer=_dq(maxlen=8)                 # RF1: objective-keyed frame buffer
        self.reasoning=None; self._fresh=False; self._last_meta=None
    def set_reasoning(self, meta):
        from collections import deque as _dq
        self.reasoning=dict(meta) if isinstance(meta,dict) else {"why":str(meta)}; self._fresh=True
        self.transition_buffer=_dq([getattr(self,'_last_grid',np.zeros((64,64),dtype=int)).copy()], maxlen=8)
    def reset(self):
        if self.level_local and self.env is not None:
            o=self.env.step(GameAction.RESET)                # LEVEL-LOCAL reset: keep completed levels (multi-level)
        else:
            self.env=self.arc.make(self.game_id); o=self.env.reset()
        self._obs=o; self._lvl0=getattr(o,'levels_completed',0) or 0; self._reward=False
        self.slm.locus=None
        f=np.array(o.frame); raw=(f[-1] if f.ndim==3 else f) if f.size else np.zeros((64,64),dtype=int)
        acts=[_AM[int(a)] for a in (o.available_actions or [])]
        pure_click = (GameAction.ACTION6 in acts) and not any(a!=GameAction.ACTION6 for a in acts)
        self._spec = None   # reason at NATIVE 64x64; logical-grid spec is unused (removed to prevent coord regressions)
        return self._grid(o)
    def _grid(self,o):
        f=np.array(o.frame)
        if f.size==0: return getattr(self,'_last_grid', np.zeros((64,64),dtype=int))
        g=f[-1] if f.ndim==3 else f
        # REASON AT NATIVE 64x64 -- full stop. Downsampling to the board's logical grid (e.g. 12x12) discarded 5/6 of
        # the information and put the agent's coordinates in a different space than ACTION6 (which is 0-63 on 64x64),
        # so clicks landed bunched in a corner. The agent reasons at full resolution; a logical cell is just a block.
        self._last_grid=g; return g
    def actions(self):
        return [_AM[int(a)] for a in (self._obs.available_actions if self._obs else [])]
    def discrete_actions(self):
        """Nullary actions only (located/pointer actions are exposed via pointer_actions/step_at)."""
        return [a for a in self.actions() if a != GameAction.ACTION6]
    def step(self, action):
        prev=self._grid(self._obs) if self._obs is not None else None
        if isinstance(action, tuple) and action[0]=='click':
            o=self.env.step(GameAction.ACTION6, data={"x":int(action[2]),"y":int(action[1])})  # x=col, y=row
        else:
            o=self.env.step(action)
        self._obs=o
        cur=self._grid(o)
        try: self.transition_buffer.append(cur.copy())         # RF1: record the frame
        except Exception: pass
        if prev is not None and not isinstance(action,tuple) and prev.shape==cur.shape: self.slm.update(prev, action, cur)
        lvl=getattr(o,'levels_completed',0) or 0
        rew = 1.0 if lvl>self._lvl0 else 0.0
        if lvl>self._lvl0: self._reward=True; self._lvl0=lvl
        if o.state==GameState.WIN: self._reward=True
        done = (o.state in (GameState.WIN, GameState.GAME_OVER)) or self._reward
        return self._grid(o), rew, done, {'state':o.state.name}
    def satisfied(self): return self._reward
    def agent_cell(self): return self.slm.agent_cell()      # DISCOVERED locus (not a handed-in role)
    def move_map(self): return self.slm.coherent_actions()  # discovered action->displacement
    def random_action(self, rng):
        acts=self.actions()
        if not acts: return GameAction.ACTION1
        a=acts[int(rng.integers(len(acts)))]
        return ('click',int(rng.integers(64)),int(rng.integers(64))) if a==GameAction.ACTION6 else a
    # --- platform-agnostic LOCATED-action affordance (the DSL sees "act at a cell", not ACTION6) ---
    def pointer_actions(self):
        """Located action KINDS available (parameterized by a cell). Platform encoding stays here."""
        return ['click'] if GameAction.ACTION6 in self.actions() else []
    def step_at(self, kind, r, c):
        """Apply a located action at cell (row r, col c). Reasoning is native 64x64, so pass (row, col) STRAIGHT
        through -- platform step() maps it to the ACTION6 payload (x=col, y=row). No logical-cell conversion: the old
        _spec/cell_to_frame path treated 64x64 coords as 12x12 cells and clamped clicks into the corner."""
        return self.step((kind, int(r), int(c)))
        raise ValueError(f"unknown pointer kind {kind}")
