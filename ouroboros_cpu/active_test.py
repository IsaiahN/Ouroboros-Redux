"""active_test.py -- ACTIVE self-recognition. The agent does NOT wait for the environment to reveal the
rule; it INTERVENES to force the rule out. It injects a distinctive move-codeword (a 'ping') -- a short
action sequence whose displacement pattern is absent from its habitual moves -- and then checks which objects
echo that exact codeword, and at what lag. Because the ping is distinctive, its reproduction PINS the lag
unambiguously even when habitual movement is periodic (the case where passive matching went ambiguous). A
second, different ping is then chained to rule out coincidence: a true delayed self reproduces EVERY ping at
the SAME lag. If nothing reproduces a ping within budget, the agent falls back to exploration.

This is the experimentalist stance applied to the mirror self-recognition test: perturb to falsify.
"""
import itertools
import numpy as np

import perception as _perc


def _read(adapter):
    return np.asarray(adapter._grid(adapter._obs)).copy()


def _self_oid(objs, self_cells):
    best = None
    for o in objs:
        oc = {tuple(int(x) for x in c) for c in getattr(o, "cells", [])}
        ov = len(oc & self_cells)
        if ov > 0 and (best is None or ov > best[1]):
            best = (o.oid, ov)
    return best[0] if best else None


def learn_action_effects(adapter, self_cells, actions):
    """Establish the self's action->displacement map (what each of MY actions does to ME). The ping is
    designed in this space, so the agent only ever injects moves it actually controls."""
    sc = {tuple(int(x) for x in c) for c in self_cells}
    eff = {}
    for a in actions:
        try:
            adapter.reset(); tr = _perc.Perception()
            objs, _ = tr.update(_read(adapter)); soid = _self_oid(objs, sc)
            if soid is None:
                continue
            before = {o.oid: o.centroid for o in objs}
            adapter.step(a)
            objs2, _ = tr.update(_read(adapter)); after = {o.oid: o.centroid for o in objs2}
            if soid in before and soid in after:
                eff[a] = (round(after[soid][0] - before[soid][0]), round(after[soid][1] - before[soid][1]))
        except Exception:
            continue
    return eff


def design_ping(action_effects, recent_moves, length=3):
    """Choose a DISTINCTIVE move-codeword: a short action sequence whose displacement pattern (a) is not
    constant (so it carries information) and (b) does NOT occur as a contiguous run in the recent self-move
    history (so its later echo pins the lag, even if habitual movement is periodic). Returns (actions, disp)."""
    acts = [a for a, d in action_effects.items() if d != (0, 0)]
    recent = [tuple(m) for m in recent_moves if m]
    fallback = None
    for combo in itertools.product(acts, repeat=length):
        disp = [action_effects[a] for a in combo]
        if len(set(disp)) <= 1:                                # constant pattern -> not distinctive
            continue
        absent = all(recent[i:i + length] != disp for i in range(len(recent) - length + 1))
        if absent:
            return list(combo), disp
        if fallback is None:
            fallback = (list(combo), disp)
    return fallback if fallback else (None, None)


def find_ping(stream, ping_disp, tol=0.5):
    """Scan a candidate's move stream for the ping codeword; return the lag (index of first reproduction) or
    None. A distinctive codeword appears at most once by design, so the lag is unambiguous."""
    L = len(ping_disp)
    for start in range(len(stream) - L + 1):
        w = stream[start:start + L]
        if any(x is None for x in w):
            continue
        if all(abs(w[j][0] - ping_disp[j][0]) + abs(w[j][1] - ping_disp[j][1]) <= tol for j in range(L)):
            return start
    return None


def active_self_recognition(adapter, self_cells, rounds=2, length=3, warmup=4, settle=8, tol=0.5):
    """Run the active experiment. Inject `rounds` DISTINCT pings during one continuous rollout, tracking every
    object's move stream; a candidate is CONFIRMED a delayed self iff it echoes EVERY ping at a CONSISTENT lag
    (chaining rules out coincidence). Returns confirmed {oid: lag}, refuted, and a recommendation (exploit the
    recognised selves, or fall back to explore if nothing echoed)."""
    try:
        actions = list(adapter.discrete_actions() or [])
    except Exception:
        actions = []
    sc = {tuple(int(x) for x in c) for c in (self_cells or [])}
    if not actions or not sc:
        return dict(confirmed={}, refuted=[], recommend="explore", reason="no actions / no self")
    eff = learn_action_effects(adapter, sc, actions)
    if len({d for d in eff.values() if d != (0, 0)}) < 2:
        return dict(confirmed={}, refuted=[], recommend="explore",
                    reason="cannot design a distinctive ping (need >=2 distinct action-effects)")

    tr = _perc.Perception(); adapter.reset()
    streams = {}; prev = {}; t = [0]; self_oid = [None]

    def record():
        objs, _ = tr.update(_read(adapter))
        if self_oid[0] is None:
            self_oid[0] = _self_oid(objs, sc)
        cur = {o.oid: o.centroid for o in objs}
        for oid, c in cur.items():
            streams.setdefault(oid, [None] * t[0])
            streams[oid].append((round(c[0] - prev[oid][0]), round(c[1] - prev[oid][1])) if oid in prev else None)
        for oid in streams:
            if len(streams[oid]) < t[0] + 1:
                streams[oid] += [None] * (t[0] + 1 - len(streams[oid]))
        prev.clear(); prev.update(cur); t[0] += 1

    recent = []
    record()
    for i in range(warmup):                                    # habitual moves: establish the recent pattern
        a = actions[i % len(actions)]; adapter.step(a); recent.append(eff.get(a)); record()

    pings = []
    neutral = actions[0]
    for _ in range(rounds):
        combo, disp = design_ping(eff, recent, length)
        if combo is None:
            break
        Ti = t[0] - 1                                          # reference time: echoes are measured from here
        for a in combo:
            adapter.step(a); recent.append(eff.get(a)); record()
        for _ in range(settle):                                # let echoes arrive
            adapter.step(neutral); recent.append(eff.get(neutral)); record()
        pings.append((Ti, disp))

    confirmed = {}; refuted = []
    self_stream = streams.get(self_oid[0], [])
    for oid, stream in streams.items():
        if oid == self_oid[0]:
            continue
        lags = []
        for (Ti, disp) in pings:
            s_self = find_ping(self_stream[Ti:], disp, tol) if self_stream else 0
            s_cand = find_ping(stream[Ti:], disp, tol)
            # lag = when the candidate echoes my move MINUS when I made it (self-anchored, convention-free)
            lags.append((s_cand - s_self) if (s_cand is not None and s_self is not None) else None)
        good = [l for l in lags if l is not None]
        if pings and len(good) == len(pings) and len(set(good)) == 1:   # every ping echoed at ONE lag
            confirmed[oid] = good[0]
        else:
            refuted.append((oid, lags))
    return dict(confirmed=confirmed, refuted=refuted, pings=len(pings), self_oid=self_oid[0],
                recommend=("exploit-recognized-selves" if confirmed else "explore"))
