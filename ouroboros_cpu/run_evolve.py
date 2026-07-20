import os, sys, time, json
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import online_harness as OH
OH._ensure_agents_stub()
import objective_validator as OV
import my_agent as MA
import integrated_agent as IA
# The DIAGNOSTIC per-level cap (500) enforces the opposite of the architecture being ported: the Ouroboros technique
# needs thousands of actions and hundreds of generations ON ONE LEVEL. Lift it on BOTH agents; the epoch (death) is
# the real boundary now.
for _c in (MA.MyAgent, IA.MyAgent):
    _c.PER_LEVEL_ACTIONS = 10**7
    if hasattr(_c, 'MAX_ACTIONS'):
        _c.MAX_ACTIONS = 10**7
c = Counter(); ev = []
_o = OV._emit
def tr(ad, step, once_key=None):
    for k, t in (('EPOCH','epoch'),('CULL','cull'),('HGT','hgt'),('VETO','veto'),('PARIAH','pariah')):
        if step.startswith(k): c[t] += 1
    if step.startswith(('EPOCH','HGT')) and len(ev) < 10: ev.append(step[:140])
    return _o(ad, step, once_key)
OV._emit = tr
import arc_agi, arcengine
from arc_agi.base import OperationMode
SECS = int(os.environ.get('RUN_SECS', '1500'))
arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE, arc_api_key=os.environ['ARC_API_KEY'])
sc = arc.open_scorecard(tags=['ouroboros','evolve'])
env = arc.make('ls20', scorecard_id=sc, save_recording=False)
agent = IA.MyAgent(game_id='ls20', card=sc)
o = env.reset(); frames = [o]; t0 = time.time()
steps = 0; maxlvl = 0; resets = 0; lvl_hist = Counter(); stop = 'wall'
def dump(final=False):
    ad = agent._composer.adapter if getattr(agent, '_composer', None) else None
    mk = getattr(ad, '_micro_market', None) if ad is not None else None
    e = mk.get('evo') if mk else None; ar = mk.get('arena') if mk else None
    d = {"final": final, "wall": round(time.time()-t0), "max_level": maxlvl, "actions": steps,
         "resets": resets, "levels_time": dict(lvl_hist), "stop": stop,
         "epochs": (mk.get('epoch', 0) if mk else 0), "decisions": (mk.get('n', 0) if mk else 0),
         "culled": (len(e.culled) if e else 0), "transfers": (e.transfers if e else 0),
         "chains": (len(ar.chains) if ar else 0),
         "standings": (ar.standings() if ar else {}),
         "emissions": {k: c[k] for k in ('epoch','cull','hgt','veto','pariah')}, "epoch_log": ev,
         "model": (ad._induced_report() if (ad is not None and hasattr(ad, '_induced_report')) else {}),
         "hud": (ad._hud_report() if (ad is not None and hasattr(ad, '_hud_report')) else {}),
         "percepts": (ad._percept_report() if (ad is not None and hasattr(ad, '_percept_report')) else {}),
         "residual": (ad._residual_router.report() if (ad is not None and getattr(ad, '_residual_router', None)) else {}),
         "macro": ((mk.get('macro').report() if (mk and mk.get('macro')) else {}))}
    open('/tmp/verify_cpu/evolve_status.json', 'w').write(json.dumps(d, indent=1))
while steps < 500000 and (time.time()-t0) < SECS:
    lvl = int(getattr(o, 'levels_completed', 0) or 0); maxlvl = max(maxlvl, lvl); lvl_hist[lvl] += 1
    s = str(getattr(o, 'state', ''))
    if 'GAME_OVER' in s or 'WIN' in s:
        resets += 1
        try:
            R = arcengine.GameAction.from_name('RESET'); R.reasoning = ''
            o = env.step(R, reasoning=''); frames = [o]; continue
        except Exception: stop = 'reset-failed'; break
    try:
        if agent.is_done(frames, o): stop = 'is_done@%d' % steps; break
        a = agent.choose_action(frames, o)
        if a is None: stop = 'none@%d' % steps; break
        d = None
        if getattr(a, 'value', None) == 6:
            ad2 = getattr(a, 'action_data', None)
            if ad2: d = {'x': int(getattr(ad2, 'x', 0) or 0), 'y': int(getattr(ad2, 'y', 0) or 0)}
        o = env.step(a, data=d, reasoning=getattr(a, 'reasoning', None) or '')
        if o is None: stop = 'env-none'; break
        steps += 1; frames.append(o); frames = frames[-16:]
        if steps % 250 == 0: dump()
    except Exception as e:
        stop = 'exc:%r' % (e,); c['exc'] += 1; break
try: arc.close_scorecard(sc)
except Exception: pass
dump(final=True)
