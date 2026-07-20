"""Batch A/B runner: run N ls20 sessions sequentially, print max_level per session.
Tees the last session's grammar stream. Key is env-only."""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
WALL = int(sys.argv[2]) if len(sys.argv) > 2 else 200
TAG = sys.argv[3] if len(sys.argv) > 3 else "batch"
STREAM = sys.argv[4] if len(sys.argv) > 4 else "/tmp/nb/batch_stream.log"

import objective_validator as OV
_stream = open(STREAM, "w", buffering=1)
_orig = OV._emit
_cap = {"on": False, "i": 0}
def _tee(adapter, step, once_key=None):
    if _cap["on"]:
        try:
            lvl = getattr(getattr(adapter, "_obs", None), "levels_completed", None)
            _cap["i"] += 1
            _stream.write("[#%d lvl=%s] %s\n" % (_cap["i"], lvl, step))
        except Exception: pass
    return _orig(adapter, step, once_key=once_key)
OV._emit = _tee

import online_harness as OH
levels = []
for k in range(N):
    _cap["on"] = (k == N - 1)   # tee only the last session
    print("=== [%s] session %d/%d ===" % (TAG, k+1, N), flush=True)
    try:
        sc, url, res = OH.run_online(["ls20"], wall_cap_s=WALL, brain="submission", verbose=False)
        ml = res[0].get("max_level"); st = res[0].get("steps"); oc = res[0].get("outcome")
        levels.append(ml)
        print("  -> max_level=%s steps=%s outcome=%s  %s" % (ml, st, oc, url), flush=True)
    except Exception as e:
        import traceback; traceback.print_exc()
        levels.append(None)
    time.sleep(3)   # breathe between scorecards (avoid startup race)
_stream.close()
print("=== [%s] max_levels: %s  (mean=%.2f of %d) ===" % (
    TAG, levels, (sum(x for x in levels if x is not None)/max(1,len([x for x in levels if x is not None]))), N), flush=True)
