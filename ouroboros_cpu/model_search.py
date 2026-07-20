"""
MODEL SEARCH  —  the missing molecule: search over an INDUCED model, on any game.

WHAT THIS DISSOLVES
-------------------
Three modules in this tree are game-specific planners that nothing can reach:

    joint_state_push.py   "Sokoban-family. State is (player, frozenset(crates)). A move into a crate pushes it."
    slot_cycle.py         "lp85's belt is a RING of fixed slots whose contents advance by a pitch."
    dynamics_forecast.py  "the world changes under a no-op; extrapolate each autonomous mover's centroid."

Strip the game off each and the same three sentences remain:

    push     = an OBJECT LAW.  (object, action) -> translate(dr, dc)
    belt     = an OBJECT LAW with a PERIOD.  (object, action) -> advance, every p steps
    autonomy = an OBJECT LAW under a NO-OP.  (object, noop) -> translate(dr, dc)

They are not three planners. They are one planner over three learned laws -- and the laws are not ours to write,
they are the board's to teach. `ObjectTransitionInducer` already induces exactly that shape, keyed by
(colour_signature, size_bucket, action), and already exposes `simulate()` to roll it forward. Both existed. Nothing
called `simulate()`. This module is the caller.

With this, the three modules are deletable: Sokoban is `plan(goal=crates_on_goals)`, the belt is
`plan(goal=item_at_grab_locus)`, forecasting is `simulate(state, noop, steps=k)`. **No Sokoban detector, no belt
detector, no regime router** -- the induced model tells you what game you are in, which is the whole kernel-not-
library claim stated as code rather than as a position.

THE LICENCE — why this refuses to run
-------------------------------------
Searching over a model that does not predict is searching over FICTION, and it spends real actions doing it, with
total confidence, which is worse than doing nothing. So this molecule does not get to decide it is ready. The model
decides, using the honesty machinery the inducer already carries:

    fidelity     = 1 - wrong/predicted        -- the model marking its own homework on real transitions
    degenerate   = fewer than 2 motion rules  -- "nothing ever moves" scores ~1.0 on a static board and is WORTHLESS
    identifiable = contradiction <= 0.15 AND fidelity >= 0.6 AND NOT degenerate

`identifiable` is the licence. Measured on ls20 right now: fidelity 0.353, degenerate True -> **NOT licensed**, so
this abstains. That is not a failure of this module; it is this module working. The same shape as TriggerChain
abstaining when the key is unknown: an agent that plans over a model it cannot predict with is not planning.
"""

import heapq


class ModelSearch:
    """A* over a forward model the agent INDUCED, rather than one anybody wrote down."""

    def __init__(self, inducer, actions=("ACTION1", "ACTION2", "ACTION3", "ACTION4"), emit=None):
        self.inducer = inducer
        self.actions = tuple(actions)
        self.expansions = 0
        self.last_refusal = None
        self.emit = emit or (lambda s: None)
        self._said = set()
        self.life_horizon = None       # set by whoever knows the board: you cannot plan past your own meter

    # ---- the licence -------------------------------------------------------------------------------------------
    def licence(self):
        """May this model be planned over? The MODEL answers, not the planner."""
        try:
            rep = self.inducer.report() or {}
        except Exception:
            return False, "no report"
        if rep.get("identifiable"):
            return True, "identifiable (fidelity %s, contradiction %s)" % (
                rep.get("fidelity"), rep.get("contradiction_rate"))
        why = []
        if rep.get("degenerate"):
            why.append("DEGENERATE: <2 motion rules -- it has learned 'nothing moves', which scores well and "
                       "means nothing")
        f = rep.get("fidelity")
        if f is not None and f < 0.6:
            why.append("fidelity %.3f < 0.6 -- it is wrong about the world more often than it is right" % f)
        c = rep.get("contradiction_rate")
        if c is not None and c > 0.15:
            why.append("contradiction %.2f > 0.15 -- the same precondition gives different effects, so the "
                       "partition is still wrong" % c)
        return False, "; ".join(why) or "not identifiable"

    # ---- the molecule ------------------------------------------------------------------------------------------
    def plan(self, state, goal_test, heuristic=None, max_expansions=4000, max_depth=None):
        """A* from `state` to any state where goal_test(state) holds, over the INDUCED dynamics.

        Game-agnostic by construction: it knows nothing about crates, belts, keys or mazes. It knows the actions the
        board offers and the laws the board taught. Everything the three dissolved modules did is a choice of
        `goal_test` -- which is the difference between a library of solvers and a kernel that composes.
        """
        # YOU CANNOT PLAN FURTHER THAN YOU CAN LIVE.
        #
        # max_depth was 40, on a board where a life is 42. A 40-step plan is a plan to spend the entire life
        # executing it and arrive with two actions left -- and every step past the meter is a step the agent will
        # never take, so searching them is not caution, it is fiction with a CPU bill. The horizon is a property of
        # the BOARD (how long you live), not of the planner.
        if max_depth is None:
            max_depth = self.life_horizon or 40
        ok, why = self.licence()
        if not ok:
            self.last_refusal = why
            # SAY IT. An agent that silently declines to plan is an agent whose decision can only be diagnosed from
            # outside itself -- and every wrong theory about this codebase came from outside it. The frame data is
            # the debugging surface; a refusal that never reaches the frame data did not happen, as far as anyone
            # reading the stream can tell.
            self._say("MODEL  I will NOT plan over my own world-model: %s" % why)
            return None                       # ABSTAIN. Do not spend the meter walking through a model's fiction.
        self._say("MODEL  planning over the model the BOARD taught me -- %s" % why)
        h = heuristic or (lambda s: 0)
        start = self._key(state)
        openq = [(h(state), 0, start, state, [])]
        seen = {start: 0}
        self.expansions = 0
        while openq and self.expansions < max_expansions:
            _f, g, k, st, path = heapq.heappop(openq)
            self.expansions += 1
            if goal_test(st):
                return path
            if g >= max_depth:
                continue
            for a in self.actions:
                try:
                    nxt = self.inducer.simulate(st, a, steps=1)
                except Exception:
                    continue
                if nxt is None:
                    continue
                nk = self._key(nxt)
                if nk == k:
                    continue                  # the model says this action changes nothing: not a move
                if nk in seen and seen[nk] <= g + 1:
                    continue
                seen[nk] = g + 1
                heapq.heappush(openq, (g + 1 + h(nxt), g + 1, nk, nxt, path + [a]))
        return None

    def forecast(self, state, steps=4, noop="ACTION5"):
        """dynamics_forecast, dissolved: autonomous motion is an object law under a no-op."""
        ok, _ = self.licence()
        if not ok:
            return None
        try:
            return self.inducer.simulate(state, noop, steps=steps)
        except Exception:
            return None

    def _say(self, msg):
        """Narrate once per distinct verdict: the stream is evidence, not a log."""
        k = msg[:60]
        if k in self._said:
            return
        self._said.add(k)
        try:
            self.emit(msg)
        except Exception:
            pass

    @staticmethod
    def _key(state):
        try:
            import numpy as np
            return hash(np.asarray(state).tobytes())
        except Exception:
            return hash(str(state))

    def report(self):
        ok, why = self.licence()
        return {"licensed": ok, "why": why, "expansions": self.expansions,
                "refused_because": None if ok else why}


# =================================================================================================================
# THE THREE, DISSOLVED. Each is now a goal_test, not a module.
# =================================================================================================================

def goal_objects_at(target_cells, tol=1):
    """joint_state_push, dissolved: 'every crate on a goal cell' is a goal_test over the induced state.

    The push RULE -- move into a crate and it translates by your vector -- is not written here and must not be. It is
    `(object, action) -> translate(dr,dc)`, which is exactly what the inducer induces from watching. If the board
    has pushing, the model learns pushing, and this goal_test plans it. If it does not, nothing here fires.
    """
    tgt = set(tuple(t) for t in target_cells)

    def _test(state):
        try:
            import numpy as np
            g = np.asarray(state)
            return all(g[r, c] != 0 for (r, c) in tgt)
        except Exception:
            return False
    return _test


def goal_property_at(pos, value, read_prop):
    """slot_cycle / ls20's key, dissolved: 'the thing at POS reads VALUE'.

    A belt arriving at a grab-locus and a key reaching an orientation are the same goal_test over different induced
    laws. The PERIOD that slot_cycle went to such trouble to learn is a property of the induced law, not of this.
    """
    def _test(state):
        try:
            return read_prop(state, pos) == value
        except Exception:
            return False
    return _test
