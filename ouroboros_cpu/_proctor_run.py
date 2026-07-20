"""Proctor live-run capture harness (throwaway; not part of the agent).
Tees every _emit grammar step to a log so Claude can read the agent's own reasoning
stream, then drives the real submission trunk on the dev API. Key is env-only."""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GAME = sys.argv[1] if len(sys.argv) > 1 else "ls20"
WALL = int(sys.argv[2]) if len(sys.argv) > 2 else 300
STREAM_PATH = sys.argv[3] if len(sys.argv) > 3 else "/tmp/nb/run_stream.log"

import objective_validator as OV

_stream = open(STREAM_PATH, "w", buffering=1)
_orig_emit = OV._emit
_n = {"i": 0}
def _tee_emit(adapter, step, once_key=None):
    try:
        lvl = getattr(getattr(adapter, "_obs", None), "levels_completed", None)
        na = getattr(adapter, "_n_action", None)
        _n["i"] += 1
        _stream.write("[#%d act=%s lvl=%s] %s\n" % (_n["i"], na, lvl, step))
    except Exception:
        pass
    return _orig_emit(adapter, step, once_key=once_key)
OV._emit = _tee_emit

import online_harness as OH

t0 = time.time()
print("=== LIVE RUN start game=%s wall=%ss ===" % (GAME, WALL), flush=True)
try:
    sc, url, results = OH.run_online([GAME], wall_cap_s=WALL, brain="submission", verbose=True)
    print("=== RESULTS ===", flush=True)
    print(json.dumps(results, default=str, indent=2), flush=True)
    print("scorecard:", url, flush=True)
except Exception as e:
    import traceback; traceback.print_exc()
finally:
    _stream.write("\n=== emits total: %d | wall: %ds ===\n" % (_n["i"], round(time.time()-t0)))
    _stream.close()
    print("=== emits captured: %d ===" % _n["i"], flush=True)
    print("=== wall: %ds ===" % round(time.time()-t0), flush=True)
