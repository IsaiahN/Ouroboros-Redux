"""Free run: keep ONE submission agent alive on ls20 across deaths/restarts, up to N total actions.
The agent's cross-life memory (cmap, refutation_ledger, persistent_model, self-assess) persists in
GLOBAL_KNOWLEDGE across restarts, so this is the 'evolve across generations' mode. Tees the DSL stream.
Key is env-only."""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
WALL = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
STREAM = sys.argv[3] if len(sys.argv) > 3 else "/tmp/nb/free_stream.log"

import objective_validator as OV
_stream = open(STREAM, "w", buffering=1); _n = [0]; _orig = OV._emit
def _tee(adapter, step, once_key=None):
    try:
        lvl = getattr(getattr(adapter, "_obs", None), "levels_completed", None)
        _n[0] += 1; _stream.write("[#%d lvl=%s] %s\n" % (_n[0], lvl, step))
    except Exception:
        pass
    return _orig(adapter, step, once_key=once_key)
OV._emit = _tee

import arc_agi
try:
    from arc_agi.base import OperationMode
except Exception:
    from arc_agi import OperationMode
import online_harness as OH
OH._ensure_agents_stub()
import integrated_agent as IA
from arcengine import GameAction
import logging
log = logging.getLogger("free"); logging.basicConfig(level=logging.WARNING)

key = os.environ["ARC_API_KEY"]
arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE, arc_api_key=key, logger=log)
sc = arc.open_scorecard(tags=["ouroboros", "free-run"])
url = "https://arcprize.org/scorecards/%s" % sc
print("=== FREE RUN ls20  cap=%d actions  wall=%ss ===" % (CAP, WALL), flush=True)
print("scorecard:", url, flush=True)
env = arc.make("ls20", scorecard_id=sc, save_recording=True)
try:
    agent = IA.MyAgent(game_id="ls20", card=sc)
except Exception:
    agent = IA.MyAgent(game_id="ls20")

t0 = time.time(); deadline = t0 + WALL
o = OH._retry_none(lambda: env.reset(), tries=5, base=1.2)
frames = [o] if o is not None else []
acts = 0; deaths = 0; max_level = 0; gens = 1
last_lv = 0

def _terminal(fr):
    st = str(getattr(fr, "state", "") or "")
    return ("GAME_OVER" in st) or ("WIN" in st) or ("NOT_STARTED" in st) or ("NOT_PLAYED" in st)

while acts < CAP and time.time() < deadline:
    if o is None:
        deaths += 1; gens += 1
        o = OH._retry_none(lambda: env.reset(), tries=3, base=0.8)
        frames = [o] if o is not None else []
        continue
    try:
        lv = int(getattr(o, "levels_completed", 0) or 0)
        max_level = max(max_level, lv); last_lv = lv
    except Exception:
        pass
    if _terminal(o):
        deaths += 1; gens += 1
        o = OH._retry_none(lambda: env.step(GameAction.RESET), tries=3, base=0.8)
        if o is None:
            o = OH._retry_none(lambda: env.reset(), tries=3, base=0.8)
        frames = [o] if o is not None else []
        continue
    action = agent.choose_action(frames, o)
    if action is None:
        o = OH._retry_none(lambda: env.step(GameAction.RESET), tries=2, base=0.8)
        frames = [o] if o is not None else []
        continue
    reasoning = getattr(action, "reasoning", None)
    step_data = None
    if getattr(action, "value", None) == 6:
        _ad = getattr(action, "action_data", None)
        if _ad is not None:
            step_data = {"x": int(getattr(_ad, "x", 0) or 0), "y": int(getattr(_ad, "y", 0) or 0)}
    o = OH._retry_none(lambda: env.step(action, data=step_data, reasoning=reasoning), tries=3, base=0.6)
    acts += 1
    if o is not None:
        frames.append(o); frames = frames[-16:]
    if acts % 100 == 0:
        print("  ... %d actions, max_level=%d, deaths=%d, %ds" % (acts, max_level, deaths, round(time.time()-t0)), flush=True)

try:
    arc.close_scorecard(sc)
except Exception:
    pass
_stream.write("\n=== %d actions | max_level %d | deaths %d | gens %d | %ds ===\n"
              % (acts, max_level, deaths, gens, round(time.time()-t0)))
_stream.close()
print(json.dumps(dict(actions=acts, max_level=max_level, deaths=deaths, gens=gens,
                      seconds=round(time.time()-t0), scorecard=url), indent=2), flush=True)
print("=== emits captured: %d ===" % _n[0], flush=True)
