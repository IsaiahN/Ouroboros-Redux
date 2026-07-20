# reason_first_agent.py -- the SWITCHOVER's submission form. Reuses the PROVEN thread-inversion
# (my_agent.MyAgent: queues + _QueueAdapter + choose_action/is_done) and swaps only the BRAIN to the
# reason-first stack (ouroboros_integrated), which drives the kernel against the same queue-adapter.
import os, sys
for _p in ((os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()), "/kaggle/working"):
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
from my_agent import MyAgent as _Base
import ouroboros_integrated as _OI


class MyAgent(_Base):
    """Identical harness contract to the proven agent; the composer thread runs the reason-first stack:
    perception/proprioception -> temporal -> DELAY self-recognition (induced + active) -> kernel -> coast ->
    persistent_model -> live causal-history validation (the proctor gate)."""
    def _run_composer(self):
        try:
            try:
                import ouroboros_redux as _OIR
                oi = _OIR.OuroborosRedux()          # REDUX: v18 perception under the reason-first spine
            except Exception:
                oi = _OI.OuroborosIntegrated()      # in-process fallback: proven reason-first spine
            guard = 0
            while not self._done and guard < 256:        # one level per run_level; loop across levels
                guard += 1
                oi.run(self.adapter, max_steps=self.BUDGET)
        except Exception:
            pass
        finally:
            self._done = True
            self.action_q.put(("__end__",))
