"""
recon.py  --  the RECON PROTOCOL that feeds the dynamics tracker (the missing piece).
================================================================================================
The tracker is correct but under-fed: arbitrary repeated actions don't elicit a game's characteristic
physics. Recon fixes that by PROBING: from a clean reset, apply ONE action and observe its short settle
animation, per action, so each action's effect is isolated and the tracker reads it cleanly. Produces:
  * an AFFORDANCE MAP {action -> dynamics it causes (+ the controllable's own motion)}, and
  * PROVISIONAL molecules (compose-or-invent) for any effect the current molecule set can't name.

This is the affordance/recon stage (Stage 3). It runs as a separate probe phase (observe-only w.r.t. the
scored path). The clean demonstrable win: discover the controllable's motion under each move action.
"""
from __future__ import annotations
import os, sys as _sys
from collections import Counter
import numpy as np

_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.join(_here, "latest_008")):
    if os.path.isdir(_p) and _p not in _sys.path:
        _sys.path.insert(0, _p)
from arcengine import GameAction, ActionInput
import dynamics as D
import visual_projection as VP
try:
    import objective_grammar as G
except Exception:
    G = None

_MOVES = [GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3, GameAction.ACTION4, GameAction.ACTION5]


def _grid(fd):
    return D._to_grid(fd.frame)


def _reset(game):
    game.full_reset()
    return game.perform_action(ActionInput(id=GameAction.RESET))


def _apply(game, act, xy=None):
    ai = ActionInput(id=act, data={"x": xy[0], "y": xy[1]}) if xy else ActionInput(id=act)
    return game.perform_action(ai)


def _probe(game, act, xy=None, settle=3):
    """Clean reset -> apply the action -> observe its settle animation. Returns a frame sequence."""
    fd = _reset(game)
    frames = [fd.frame]
    fd = _apply(game, act, xy)
    frames.append(fd.frame)
    for _ in range(settle):                 # let the action's animation play out (delayed effects)
        fd = _apply(game, act, xy)
        frames.append(fd.frame)
    return frames


def _controllable_motion(frames):
    """The dominant consistent translation = the controllable's response to the action (affordance)."""
    dr = D.track(frames)
    moves = [e for evs in dr.events_per_step for e in evs if e.kind in ("SLIDE", "FALL")]
    if not moves:
        return None
    vecs = Counter(e.vector for e in moves)
    v, n = vecs.most_common(1)[0]
    return {"vector": v, "kind": "FALL" if any(e.kind == "FALL" and e.vector == v for e in moves) else "SLIDE",
            "support": n}


def _changed(frames):
    g0 = D._to_grid(frames[0])
    for f in frames[1:]:
        g = D._to_grid(f)
        if g.shape == g0.shape and (g != g0).any():
            return True
    return False


def recon(game, settle=3, click_targets=3):
    """Probe every action; track the dynamics each elicits; build an affordance map; invent a provisional
    molecule for any effect the current molecule set cannot name."""
    report = {"affordance": {}, "elicited": set(), "provisional": [], "controllable": None}

    # --- parameterless (move) actions ---
    for act in _MOVES:
        try:
            frames = _probe(game, act, settle=settle)
        except Exception:
            continue
        dr = D.track(frames)
        mol = set(dr.molecules)
        cm = _controllable_motion(frames)
        report["affordance"][act.name] = {"molecules": sorted(mol), "controllable_motion": cm}
        report["elicited"] |= mol
        if cm and report["controllable"] is None:
            report["controllable"] = {"action": act.name, **cm}
        # Part 3: effect happened but nothing specific recognised -> invent a provisional concept
        recognised = mol - {"STAY", "APPEAR", "DISAPPEAR"}
        if G is not None and not recognised and _changed(frames):
            inv = G.compose_or_invent(["BECOME", "OTHER", "AFTER", "DO"],
                                      context=f"{act.name} caused an unnamed effect")
            if inv.get("mode") == "invent":
                report["provisional"].append({"action": act.name, "molecule": inv["name"], "primes": inv["primes"]})

    # --- click actions at salient cells ---
    try:
        fd = _reset(game); g0 = _grid(fd)
        objs, _ = VP.extract_objects(g0)
        for o in sorted(objs, key=lambda o: -o.size)[:click_targets]:
            y, x = int(o.centroid[0]), int(o.centroid[1])
            try:
                frames = _probe(game, GameAction.ACTION6, xy=(x, y), settle=settle)
            except Exception:
                continue
            dr = D.track(frames)
            report["affordance"][f"CLICK@({x},{y})"] = {"molecules": sorted(set(dr.molecules))}
            report["elicited"] |= set(dr.molecules)
    except Exception:
        pass

    report["elicited"] = sorted(report["elicited"])
    return report


def affordance_from_transitions(transitions, min_per_action=2):
    """PASSIVE / online affordance: build the action->dynamics map from transitions the agent ALREADY
    observed (grid_before, action, grid_after), without any probing or extra budget. Used to feed the
    scored path (objective_abductor.set_affordance). Noisier than active recon, but free."""
    by_act = {}
    for g0, a, g1 in transitions:
        if g0 is None or g1 is None:
            continue
        by_act.setdefault(a, []).append((g0, g1))
    elicited, per_action = set(), {}
    for a, pairs in by_act.items():
        if len(pairs) < min_per_action:
            continue
        mols = set()
        for g0, g1 in pairs:
            try:
                mols |= set(D.track([g0, g1]).molecules)
            except Exception:
                pass
        per_action[a] = sorted(mols)
        elicited |= mols
    return {"elicited": sorted(elicited), "per_action": per_action}
