"""ui_planner.py -- the UI OBJECTIVE-AND-PLANNING layer, for COMMAND games (no self avatar; the controls
are buttons that transform the world, e.g. lp85). The reach/assemble machinery the mover uses assumes a
self-target relation, which does not exist here -- so the lp85 objective compiled degenerately under the
integrated stack. The fix, agreed in design: for a command game the objective is a target WORLD-CONFIGURATION
and the plan is a SEARCH over COMMAND SEQUENCES that drives the world to it. "What to do", beyond "what can
I do".

Two parts:
  * TARGET abduction (best-effort): read a goal configuration from structure/goal-cues. This is the hard,
    game-specific part; here we accept an injected target_measure(grid)->float (0 at goal) so the PLANNER is
    verified independently, and expose a couple of structural target heuristics.
  * The PLANNER: deterministic best-first / beam search over command sequences, using FREE RESETS to reach
    any node by replaying its sequence (Go-Explore over commands). Game-agnostic: a "command" is a discrete
    action or a located click; commands are discovered from proprioception's command-modality components.
"""
import numpy as np


def _read(adapter):
    return np.asarray(adapter._grid(adapter._obs)).copy()


def commands_from_proprioception(prop):
    """Each COMMAND-modality component contributes one representative control cell -> a click command.
    (For lp85 these are the two control colours; the {command -> transform} map lives in persistent_model.)"""
    cmds = []
    for c in getattr(prop, "components", []) or []:
        if getattr(c, "modality", None) == "command" and getattr(c, "cells", None):
            r, cc = sorted(c.cells)[0]
            cmds.append(("click", int(r), int(cc)))
    return cmds


def _apply(adapter, cmd):
    if cmd[0] == "click":
        adapter.step_at("click", cmd[1], cmd[2])
    else:
        adapter.step(cmd[0])


def _replay(adapter, seq):
    """Reach a search node by replaying its command sequence from reset (adapters are deterministic)."""
    adapter.reset()
    for c in seq:
        _apply(adapter, c)
    return _read(adapter)


def plan_commands(adapter, commands, target_measure, budget=400, max_depth=10, beam=12):
    """Best-first/beam search over COMMAND SEQUENCES minimising target_measure(grid) (0 == goal config).
    Returns dict(solved, sequence, measure, expansions). FREE RESETS make every node reachable by replay,
    so this is a clean Go-Explore over the command space rather than a self-navigation."""
    if not commands:
        return dict(solved=False, sequence=[], measure=None, expansions=0, reason="no commands")
    adapter.reset(); g0 = _read(adapter)
    m0 = float(target_measure(g0))
    if m0 == 0:
        return dict(solved=True, sequence=[], measure=0.0, expansions=0)
    frontier = [(m0, [])]
    seen = {g0.tobytes()}
    best = (m0, [])
    expansions = 0
    while frontier and expansions < budget:
        frontier.sort(key=lambda x: x[0])
        frontier = frontier[:beam]
        nxt = []
        for score, seq in frontier:
            if len(seq) >= max_depth:
                continue
            for cmd in commands:
                g = _replay(adapter, seq + [cmd]); expansions += 1
                k = g.tobytes()
                if k in seen:
                    continue
                seen.add(k)
                m = float(target_measure(g))
                node = (m, seq + [cmd])
                if m < best[0]:
                    best = node
                if m == 0:
                    return dict(solved=True, sequence=seq + [cmd], measure=0.0, expansions=expansions)
                nxt.append(node)
                if expansions >= budget:
                    break
            if expansions >= budget:
                break
        frontier = nxt
    return dict(solved=(best[0] == 0), sequence=best[1], measure=best[0], expansions=expansions)


# ---- a couple of structural TARGET heuristics (target abduction is the harder, game-specific part) ----
def target_uniform(color):
    """Goal config: the whole non-background field is a single colour (an 'assemble/clear' style objective)."""
    def measure(g):
        bg = int(np.bincount(g.ravel()).argmax())
        fg = g[g != bg]
        return 0.0 if fg.size == 0 else float(np.count_nonzero(fg != color))
    return measure


def target_match(template):
    """Goal config: the grid equals a given template (cell-wise distance)."""
    t = np.asarray(template)
    def measure(g):
        g = np.asarray(g)
        if g.shape != t.shape:
            return float(t.size)
        return float(np.count_nonzero(g != t))
    return measure
