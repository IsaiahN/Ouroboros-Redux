# submission_agent.py -- Kaggle submission ENTRY. Selects the agent by env flag:
#   default (unset)        -> the PROVEN integrated_agent.MyAgent (leaderboard-validated; no regression)
#   OURO_REASON_FIRST=1    -> the reason-first stack (the switchover) -- for the GAME GATE
import os, sys
os.environ.setdefault("ARC3_EPHEMERAL_STORE", "1")
os.environ.setdefault("MPLBACKEND", "agg")
_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, "/kaggle/working"):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

if os.environ.get("OURO_REASON_FIRST"):
    from reason_first_agent import MyAgent   # noqa: F401  -- the switchover, gated behind a flag
else:
    from integrated_agent import MyAgent     # noqa: F401  -- proven default
