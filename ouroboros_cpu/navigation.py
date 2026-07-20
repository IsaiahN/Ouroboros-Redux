"""
NAVIGATION  —  the pure half: what it COSTS to get somewhere, and where "somewhere" even is.

WHY THIS FILE EXISTS
--------------------
`_path_cost`, `_closest_reachable`, `_candidate_doors` and `_act_toward` were nested inside `_avatar_solve` -- a
2002-line host. They are pure: given a view of the board they compute and return, they do not act. But they were
unreachable from anywhere else, untestable in isolation, and un-reusable by any other regime -- so the one part of
the agent that decides WHERE IT CAN GO could only be exercised by running an entire game.

That matters more than tidiness. Everything this session has diagnosed sits downstream of this code:
  - the booster is only ever grabbed at 8 actions from death, because pathing runs the budget down first;
  - a level costs 41 actions of a 42-action meter, so the whole game is a claim about path quality;
  - the composite-avatar mis-carve bites precisely here -- in absolute-position lookups, which is what these do.
A resource policy cannot repay a debt that pathing keeps running up, and pathing could not be looked at on its own.

THE INJECTED VIEW
-----------------
Every one of these wanted the same nine things from its host. That is not a closure; it is an interface that had not
been written down:

    grid()            the board, full resolution (never downsampled -- the ban is real and it is load-bearing)
    apos()            where the agent believes it is  [NB: currently the centroid of HALF the avatar]
    blocked()         cells the shared map has LEARNED are impassable (measured, not assumed)
    quantum           one step, in pixels
    steer             action -> unit direction
    walls, passable, floor   the colour ontology of the board

`apos` is passed in rather than computed here on purpose: WHICH percept answers "where am I" is a live question this
session opened (colour vs component vs delta), and navigation must not quietly pick a winner that the board has not
priced. It asks; it does not decide.
"""

import numpy as np


class BoardView:
    """The nine things the navigator needs. Injected, so navigation can be tested without playing a game."""

    def __init__(self, grid, apos, blocked, quantum, steer, walls=(), passable=(), floor=None, edges=None):
        self.grid = grid                # callable -> full-res grid
        self.apos = apos                # callable -> (r, c) or None
        self.blocked = blocked          # callable -> set of learned-impassable cells
        self.quantum = quantum
        self.steer = steer              # {action_name: (dy, dx)}
        self.walls = set(walls or ())
        self.passable = set(passable or ())
        self.floor = floor
        self.edges = edges              # callable -> learned edges, optional


def act_toward(view, dir_yx):
    """Which action moves us in this direction? The steer map is the agent\'s, not the author\'s."""
    best, bs = None, -1e9
    dy, dx = dir_yx
    n = (dy * dy + dx * dx) ** 0.5 or 1.0
    for name, (sy, sx) in (view.steer or {}).items():
        m = (sy * sy + sx * sx) ** 0.5 or 1.0
        dot = (dy * sy + dx * sx) / (n * m)
        if dot > bs:
            best, bs = name, dot
    return best


def reachable_from(view, start_cell, cap=4000):
    """Flood fill over cells the map has NOT learned to be blocked.

    Deliberately optimistic: unknown is passable. An agent that treats unexplored as impassable cannot explore, and
    that failure is invisible -- it just quietly stops going places and every step it does take looks reasonable.
    """
    g = view.grid()
    if g is None or start_cell is None:
        return set()
    H, W = np.asarray(g).shape[:2]
    hq, wq = H // view.quantum, W // view.quantum
    bad = view.blocked() or set()
    seen, stack = {start_cell}, [start_cell]
    while stack and len(seen) < cap:
        r, c = stack.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (r + dr, c + dc)
            if 0 <= n[0] < hq and 0 <= n[1] < wq and n not in seen and n not in bad:
                seen.add(n)
                stack.append(n)
    return seen


def path_cost(view, target_px):
    """Manhattan steps to a target, in ACTIONS -- the unit the meter is denominated in.

    Returned in actions, not pixels, because every caller is about to compare it against the budget. A cost in the
    wrong unit is how a plan comes to look affordable when it is not.
    """
    a = view.apos()
    if a is None or target_px is None:
        return None
    q = max(1, view.quantum)
    return int(abs(a[0] - target_px[0]) // q + abs(a[1] - target_px[1]) // q)


def closest_reachable(view, target_px, emit=None):
    """The nearest cell to the target that the agent can actually get to, and how far short it falls.

    'Unreachable' is a claim about the map, not the world -- so this reports the GAP rather than a verdict. The
    solvability axiom lives here: an unreachable target under the current map is a map problem until proven
    otherwise, and reporting the gap keeps that question open instead of closing it silently.
    """
    a = view.apos()
    if a is None or target_px is None:
        return {}
    q = max(1, view.quantum)
    start = (int(a[0] // q), int(a[1] // q))
    tgt = (int(target_px[0] // q), int(target_px[1] // q))
    seen = reachable_from(view, start)
    if not seen:
        return {}
    best = min(seen, key=lambda c: abs(c[0] - tgt[0]) + abs(c[1] - tgt[1]))
    gap = int(abs(best[0] - tgt[0]) + abs(best[1] - tgt[1]))
    # SAY IT. "I cannot get there" is a DECISION -- the agent will now do something else because of it -- and it
    # was returned as a dict to a caller that never spoke it. A finding that never reaches the frame data did not
    # happen, as far as anyone reading the stream can tell.
    if emit is not None and gap > 0:
        try:
            emit("REACH  target %s is UNREACHABLE := nearest cell I can stand on is %d steps short  "
                 "[%d cells reachable from here under the map I have LEARNED -- unreachable means unreachable "
                 "under my current map, never 'give up']" % (str(target_px), gap, len(seen)))
        except Exception:
            pass
    return {"closest": (best[0] * q, best[1] * q), "gap": gap, "reachable": len(seen)}
