"""delay_operator.py -- TIME as a higher-order operator (a functor), not a molecule.

DELAY(M, k) lifts ANY spatial molecule M into a timed predicate: an object X is DELAY(M, k) of a reference
trajectory R iff  X(t) == M(R(t - k))  for all overlapping t. The operator is BLIND to which molecule it
lifts -- it is NOT hand-paired with 'mirror' to make a 'ghost'; it composes with whatever molecule it is
handed. The molecules stay the plain spatial primitives the system already needs (identity/copy, mirror,
translate). 'ghost' and 'delayed-mirror' are NOT stored types -- they are recovered:

    m0r0 mirrored agent  = DELAY(mirror(self), 0)     # lag 0 recovers the pure spatial molecule
    g50t ghost replay    = DELAY(self, k)             # a delayed exact copy of your own path
    delayed mirror       = DELAY(mirror(self), k)

The SAME operator yields all of them by varying (molecule, lag); none is a special case in code. If I had to
hand-pair DELAY with mirror to get a ghost, that would be a library entry in disguise -- so DELAY iterates a
generic molecule family and is told nothing about the game.

The reference R is the causal-residual self (the footprint / frame-history). Recognising a delayed self IS
fitting DELAY against R: the match is the recognition, and it forks action-invariant motion into delayed-self
(commits) vs reactive-trigger (no consistent (M,k) -> does not commit). Falsifiable: if no lag fits within
tolerance, the object is NOT a delayed anything.

A trajectory here is a list indexed by time; each entry is an (row, col) position or None (not present that
frame). DELAY operates on these; perception already produces per-object trajectories.
"""
from statistics import median


# ---- the plain spatial MOLECULES (generic; not game-specific). Each maps a position given a grid shape. ----
def _identity(p, shape, param=None):
    return p


def _mirror_h(p, shape, param=None):          # reflect across the vertical mid-axis (left<->right)
    return (p[0], shape[1] - 1 - p[1])


def _mirror_v(p, shape, param=None):          # reflect across the horizontal mid-axis (up<->down)
    return (shape[0] - 1 - p[0], p[1])


def _translate(p, shape, param):              # param = (dr, dc), derived during the fit
    return (p[0] + param[0], p[1] + param[1])


MOLECULES = ("identity", "mirror_h", "mirror_v", "translate")
_FN = {"identity": _identity, "mirror_h": _mirror_h, "mirror_v": _mirror_v, "translate": _translate}


def apply_molecule(pos, name, shape, param=None):
    return _FN[name](pos, shape, param)


def apply_delay(reference, name, lag, shape, param=None):
    """DELAY(molecule, lag) lifted onto a reference trajectory: predicted X(t) = molecule(reference(t-lag))."""
    pred = [None] * len(reference)
    for t in range(len(reference)):
        src = t - lag
        if 0 <= src < len(reference) and reference[src] is not None:
            pred[t] = apply_molecule(reference[src], name, shape, param)
    return pred


def _pairs(candidate, predicted):
    return [(candidate[t], predicted[t]) for t in range(min(len(candidate), len(predicted)))
            if candidate[t] is not None and predicted[t] is not None]


def _residual(candidate, name, reference, lag, shape):
    """L1 residual of candidate(t) vs molecule(reference(t-lag)). For 'translate' the offset is DERIVED from
    the data (median), so translate is discovered, not enumerated."""
    if name == "translate":
        base = apply_delay(reference, "identity", lag, shape)
        pr = _pairs(candidate, base)
        if len(pr) < 2:
            return None, None
        dr = median([c[0] - r[0] for c, r in pr])
        dc = median([c[1] - r[1] for c, r in pr])
        param = (dr, dc)
        pred = apply_delay(reference, "translate", lag, shape, param)
    else:
        param = None
        pred = apply_delay(reference, name, lag, shape, param)
    pr = _pairs(candidate, pred)
    if len(pr) < 2:
        return None, None
    err = sum(abs(c[0] - p[0]) + abs(c[1] - p[1]) for c, p in pr) / len(pr)
    return err, param


def fit_delayed_molecule(candidate, reference, shape, molecules=MOLECULES, max_lag=None, tol=1.0,
                         min_overlap=None):
    """The TIME FUNCTOR's discovery: find (molecule M, lag k) such that candidate(t) ~= M(reference(t-k)).
    Blind to which molecule -- searches the generic family over lags. Commit ONLY if residual <= tol and the
    overlap is a real fraction of the trajectory (>=40%, floor 4 frames) so a free-parameter molecule like
    'translate' cannot overfit a handful of cherry-picked frames at a large lag. Falsifiable: no fit -> not a
    delayed anything. 'translate' with a zero offset is demoted to 'identity' so the label is honest."""
    n = len(reference)
    if n == 0:
        return None
    n_present = sum(1 for x in reference if x is not None)
    if min_overlap is None:
        min_overlap = max(4, -(-2 * n_present // 5))      # ceil(0.4 * n_present)
    max_lag = (n - 1) if max_lag is None else min(max_lag, n - 1)
    best = None
    for name in molecules:
        for k in range(0, max_lag + 1):
            err, param = _residual(candidate, name, reference, k, shape)
            if err is None:
                continue
            overlap = len(_pairs(candidate, apply_delay(reference, name, k, shape, param)))
            if overlap < min_overlap:
                continue
            cand = dict(molecule=name, lag=k, residual=round(err, 3), param=param, overlap=overlap)
            if best is None or (cand["residual"], cand["lag"]) < (best["residual"], best["lag"]):
                best = cand
    if best is None:
        return None
    if best["molecule"] == "translate" and best.get("param") == (0, 0):
        best["molecule"] = "identity"; best["param"] = None
    best["committed"] = best["residual"] <= tol
    return best


def classify_action_invariant(candidates, reference, shape, tol=1.0, max_lag=None):
    """Fork the action-invariant (autonomous) bucket against the causal-residual self R. PRIMARY test is the
    coordinate-free MOVE-SEQUENCE match (the object reproduces the agent's move signature, lagged, wherever it
    sits); position-with-molecule match is the corroborating fallback.
       * fits DELAY of R (by sequence or position)  -> DELAYED-SELF (your own path/moves replayed)
       * fits neither                                -> REACTIVE-TRIGGER (action-invariant, not a copy of you)"""
    delayed_self, trigger = [], []
    for cid, traj in candidates.items():
        seqfit = fit_delayed_sequence(traj, reference, max_lag=max_lag)
        if seqfit and seqfit["committed"]:
            delayed_self.append((cid, seqfit)); continue
        posfit = fit_delayed_molecule(traj, reference, shape, tol=tol, max_lag=max_lag)
        if posfit and posfit["committed"]:
            delayed_self.append((cid, posfit))
        else:
            trigger.append((cid, seqfit or posfit))
    return dict(delayed_self=delayed_self, trigger=trigger)


# ---- MOVE / ACTION-SEQUENCE matching (coordinate-free): match the DERIVATIVE, not absolute positions ----
# A ghost is recognised by reproducing the agent's SEQUENCE OF MOVES (its action-effect signature), wherever
# it is on the grid. Differencing a trajectory into move-vectors removes absolute position, so this matches
# "you did right,down,right... and that object did right,down,right... three steps later" regardless of where
# it sits. Move-vectors carry magnitude AND direction, so "moved the same distance/direction I did" is the
# residual being ~0. Transforms act on the MOVE vectors (identity = same moves; mirror = reflected moves).
_DELTA_T = {
    "identity": lambda d: d,
    "mirror_h": lambda d: (d[0], -d[1]),       # left<->right reflected moves
    "mirror_v": lambda d: (-d[0], d[1]),       # up<->down reflected moves
    "rot180":   lambda d: (-d[0], -d[1]),
}


def deltas(traj):
    """Trajectory of positions -> sequence of move-vectors (None where a move is undefined)."""
    out = [None]
    for t in range(1, len(traj)):
        a, b = traj[t], traj[t - 1]
        out.append((a[0] - b[0], a[1] - b[1]) if (a is not None and b is not None) else None)
    return out


def fit_delayed_sequence(candidate, reference, transforms=tuple(_DELTA_T), max_lag=None, tol=0.75,
                         min_overlap=None, min_motion=2):
    """Recognise candidate as the self by its MOVE SEQUENCE, lagged and optionally transformed:
    deltas(candidate)[t] ~= T(deltas(reference)[t-k]). Coordinate-free (Q1) and distance/direction-aware
    (Q2). Requires the reference to actually MOVE (>= min_motion non-zero moves) so a stationary object can't
    be 'matched' by trivial zero-moves. Commit only on residual<=tol over a real fraction of moves."""
    rd, cd = deltas(reference), deltas(candidate)
    moving = sum(1 for d in rd if d is not None and (d[0] or d[1]))
    if moving < min_motion:
        return None                                            # no behavioural signature to match against
    n = len(rd)
    max_lag = (n - 1) if max_lag is None else min(max_lag, n - 1)
    n_present = sum(1 for d in rd if d is not None)
    if min_overlap is None:
        min_overlap = max(3, -(-2 * n_present // 5))           # ceil(0.4 * present)
    best = None
    for name in transforms:
        T = _DELTA_T[name]
        for k in range(0, max_lag + 1):
            errs = []
            nz = 0
            for t in range(len(cd)):
                s = t - k
                if 0 <= s < len(rd) and cd[t] is not None and rd[s] is not None:
                    p = T(rd[s]); errs.append(abs(cd[t][0] - p[0]) + abs(cd[t][1] - p[1]))
                    if rd[s][0] or rd[s][1]:
                        nz += 1
            if len(errs) >= min_overlap and nz >= min_motion:   # overlap must include real motion, not stillness
                resid = sum(errs) / len(errs)
                cand = dict(molecule=name, lag=k, residual=round(resid, 3), overlap=len(errs),
                            moving_overlap=nz, mode="sequence")
                if best is None or (cand["residual"], cand["lag"]) < (best["residual"], best["lag"]):
                    best = cand
    if best is None:
        return None
    best["committed"] = best["residual"] <= tol
    return best


def describe(fit):
    """Render a committed fit as the composition it is -- never as a stored 'ghost'/'delayed-mirror' type."""
    if not fit or not fit.get("committed"):
        return "no delayed-self fit (not a delayed copy of the self within tolerance)"
    m, k = fit["molecule"], fit["lag"]
    inner = "self" if m == "identity" else f"{m}(self)"
    return (f"DELAY({inner}, {k})  -- " +
            ("mirrored agent (lag 0)" if (k == 0 and m.startswith("mirror")) else
             "exact replay of own path" if (m == "identity" and k > 0) else
             "delayed mirror of own path" if (m.startswith("mirror") and k > 0) else
             f"delayed {m} of own path" if k > 0 else f"{m} of self"))
