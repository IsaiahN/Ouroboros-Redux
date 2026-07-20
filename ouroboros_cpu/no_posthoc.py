"""
NO POST-HOC PREDICATES  —  a hard bound, enforced at import.

WHY THIS IS A BOUND AND NOT A DIAL
----------------------------------
HARD-BOUND WHERE A DIAL WOULD BE GAMED. This is the clearest case of that rule in the codebase, because the exploit
is not merely available -- it is *the highest-scoring move on the board*.

A primitive is minted when a predicate over the state makes the residual compressible and the total description gets
shorter:

    |phi| + |residual given phi|  <  |residual enumerated|

That test is exact and it rejects superstition without taste. Measured, on a synthetic residual (a mover a wall
blocks in some directions), enumerating a predicate family and scoring by description length:

    predicate                          |phi|   |R given phi|   MDL gain
    [TAUTOLOGY] "did it move"             36           0.0      +189.7   <- WINS
    ctx: colour at centroid+delta         52           0.0      +173.7   <- the truth, rediscovered unaided
    action / row / col                    ..           ..       NEGATIVE <- correctly rejected
    step parity / step mod 3              ..           ..       NEGATIVE <- superstition, rejected by arithmetic
    ctx BEHIND me (identical |phi|=52)    52         225.1       -51.4   <- same cost, wrong cell, rejected

Two results matter. The search DID rediscover the hand-picked predicate, unaided, by a wide margin over every other
real candidate -- so the mechanism is real. **And the tautology beat it.**

A predicate that reads the after-state compresses the residual to ZERO bits. It therefore beats every genuine
regularity, systematically, always -- not by a nose, by 16 bits and rising with the size of the residual. "The block
moved because the block moved" would score beautifully, pass MDL, promote on echo, and predict nothing on every game
we will ever run.

So "phi must be evaluable BEFORE the action" is not a footnote and not a standard caveat. **MDL alone does not
work.** The before-state constraint is not what makes the mechanism honest; it is what makes it FUNCTION. Everything
downstream -- the MDL test, the residual-restricted search, promotion-on-echo -- rests on it holding.

And a thing that must hold cannot be a runtime check, because a runtime check is a dial and a dial gets turned. It
goes at import, next to check_no_downsampling(), where the code will not load if it is violated.

WHAT IT CHECKS
--------------
That the functions which BUILD PREDICATES do not read the after-state. It does NOT forbid reading `after` anywhere:
the residual itself is a before/after diff, `_effect(oa, ob)` compares them, and settlement prices a stake against
the observed frame. Those are LABELS and OUTCOMES, and they must read the outcome -- that is their job. The bound is
narrower and exact:

    a predicate is a question asked of the world BEFORE you act.
    a label is what the world answered.
    Nothing may be both.
"""

import ast
import os

# (module, function) pairs that construct predicates / features used as preconditions.
GUARDED = [
    ("transition_induction.py", "_ctx"),        # what the object is about to enter
    ("transition_induction.py", "_key"),        # the rule's precondition
    ("transition_induction.py", "_delta_for"),  # the learned steer map the context is read through
    ("evolvability_engine.py", "_correlates"),  # the shadow: what already casts a signal here
]

AFTER_NAMES = {"g_after", "after", "post", "b_objs", "nxt", "observed"}


class PostHocPredicate(Exception):
    """A predicate that reads the outcome is a tautology with a name on it."""


def _reads_after(fn_node):
    bad = set()
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in AFTER_NAMES:
            bad.add(n.id)
        if isinstance(n, ast.arg) and n.arg in AFTER_NAMES:
            bad.add(n.arg)
    return bad


def check_no_posthoc_predicates(root=None):
    """Raise if any guarded predicate-builder reads the after-state. Called at import; not optional."""
    root = root or os.path.dirname(os.path.abspath(__file__))
    viol = []
    for fname, fnname in GUARDED:
        path = os.path.join(root, fname)
        if not os.path.exists(path):
            continue
        try:
            tree = ast.parse(open(path).read())
        except Exception:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name == fnname:
                bad = _reads_after(n)
                if bad:
                    viol.append("%s::%s reads the after-state via %s" % (fname, fnname, sorted(bad)))
    if viol:
        raise PostHocPredicate(
            "POST-HOC PREDICATE -- a predicate that reads the outcome scores +189.7 on MDL against the truth's "
            "+173.7, so it wins systematically and predicts nothing:\n  " + "\n  ".join(viol))
    return True


def announce(emit):
    """A bound that only speaks when violated is a bound nobody knows is there.

    check_no_posthoc_predicates() raises at import if a predicate reads the outcome -- so on a healthy tree it is
    perfectly, permanently silent, and a reader of the frame data has no way to know the agent is operating under it.
    The stream is the evidentiary record: a constraint the agent is bound by belongs IN it, once, stated plainly.
    """
    try:
        emit("BOUND  no predicate may read the after-state := ENFORCED at import over %d predicate-builders  "
             "[a predicate that reads the outcome compresses the residual to ZERO bits and scores +189.7 on MDL "
             "against the truth's +173.7 -- it wins systematically and predicts nothing. This is hard-bound rather "
             "than dialled BECAUSE it is the highest-scoring move on the board]" % len(GUARDED))
    except Exception:
        pass


def audit():
    """What the bound covers, and what it deliberately does not."""
    return {"guarded": ["%s::%s" % g for g in GUARDED],
            "not_guarded": ["_effect(oa, ob) -- a LABEL, must compare before/after",
                            "Prediction.settle(before, after) -- an OUTCOME, must read the frame",
                            "ResidualReporter.report(g_before, g_after) -- the residual IS a diff"],
            "rule": "a predicate is asked BEFORE the action; a label is what the world answered; "
                    "nothing may be both"}


check_no_posthoc_predicates()
