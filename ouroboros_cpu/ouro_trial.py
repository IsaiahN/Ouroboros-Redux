#!/usr/bin/env python3
"""ouro_trial.py -- run ONE trial and emit ONE line of JSON.

Exists because every claim from here on gets compared against a band, not against a single run. The same build has
produced booster collected=10/cyc=6 on one trial and 0/0 on the next; without a band, "it improved" is unfalsifiable.

    ARC_API_KEY=... python3 ouro_trial.py --game ls20 --secs 240 --tag baseline

Prints: {"tag":..., "max_level":..., "actions":..., "resets":..., ...}
Only max_level (levels_completed) is a METRIC. Everything else is a proxy, carried for diagnosis, never for ranking.
"""
import argparse
import json
import os
import sys
import time
import traceback
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def trial(game, secs, tag, cap=None):
    import online_harness as OH
    OH._ensure_agents_stub()
    import objective_validator as OV
    import my_agent as MA

    c = Counter()
    _orig = OV._emit

    def traced(adapter, step, once_key=None):
        for k, t in (('this trigger CYCLES', 'cyc'), ('MATCHES lock', 'match'),
                     ('SUBGOAL  REACHED trigger', 'reach_trig'), ('SUBGOAL  booster', 'boost_got'),
                     ('REACH-FAIL', 'reach_fail'), ('BUDGET-BREAK', 'boost_dead'),
                     ('STUCK', 'stuck'), ('RETRY', 'retry'), ('reached a WIN', 'win')):
            if k in step:
                c[t] += 1
        return _orig(adapter, step, once_key)
    OV._emit = traced

    src = Counter()
    _oq = MA._QueueAdapter.step

    def qstep(self, a, *ar, **kw):
        stk = [f.name for f in traceback.extract_stack()]
        src['avatar' if '_avatar_solve' in stk else ('descend' if 'descend' in stk else 'other')] += 1
        return _oq(self, a, *ar, **kw)
    MA._QueueAdapter.step = qstep

    import integrated_agent as IA
    if cap:
        IA.MyAgent.PER_LEVEL_ACTIONS = int(cap)
    import arc_agi
    import arcengine
    from arc_agi.base import OperationMode

    arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE, arc_api_key=os.environ['ARC_API_KEY'])
    sc = arc.open_scorecard(tags=['ouroboros', tag])
    env = arc.make(game, scorecard_id=sc, save_recording=False)
    agent = IA.MyAgent(game_id=game, card=sc)

    o = env.reset()
    frames = [o]
    t0 = time.time()
    steps = 0
    maxlvl = 0
    resets = 0
    while steps < 30000 and (time.time() - t0) < secs:
        lvl = int(getattr(o, 'levels_completed', 0) or 0)
        maxlvl = max(maxlvl, lvl)
        st = str(getattr(o, 'state', ''))
        if 'GAME_OVER' in st or 'WIN' in st:
            resets += 1
            try:
                R = arcengine.GameAction.from_name('RESET')
                R.reasoning = ''
                o = env.step(R, reasoning='')
                frames = [o]
                continue
            except Exception:
                break
        try:
            if agent.is_done(frames, o):
                break
            a = agent.choose_action(frames, o)
            if a is None:
                break
            d = None
            if getattr(a, 'value', None) == 6:
                ad = getattr(a, 'action_data', None)
                if ad:
                    d = {'x': int(getattr(ad, 'x', 0) or 0), 'y': int(getattr(ad, 'y', 0) or 0)}
            o = env.step(a, data=d, reasoning=getattr(a, 'reasoning', None) or '')
            if o is None:
                break
            steps += 1
            frames.append(o)
            frames = frames[-16:]
        except Exception as e:
            c['exc'] += 1
            c['exc_msg'] = repr(e)[:60]
            break
    try:
        arc.close_scorecard(sc)
    except Exception:
        pass

    tot = sum(src.values()) or 1
    return {"tag": tag, "game": game, "max_level": maxlvl, "actions": steps, "resets": resets,
            "avatar_pct": 100 * src['avatar'] // tot, "descend_pct": 100 * src['descend'] // tot,
            "cyc": c['cyc'], "match": c['match'], "reach_trig": c['reach_trig'], "boost_got": c['boost_got'],
            "stuck": c['stuck'], "retry": c['retry'], "wall_s": round(time.time() - t0, 1),
            "exc": c.get('exc_msg', "")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--secs", type=int, default=240)
    ap.add_argument("--tag", default="trial")
    ap.add_argument("--cap", type=int, default=None)
    a = ap.parse_args()
    print(json.dumps(trial(a.game, a.secs, a.tag, a.cap)), flush=True)
