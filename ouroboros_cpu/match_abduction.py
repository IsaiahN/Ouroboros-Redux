"""match_abduction.py -- ABDUCE the roles a MATCH sub-objective needs, from observation, game-agnostically.

The composition-layer question for lock/key-style games: which object is the MUTABLE one (its properties
change in response to the agent -- the "key") and which is the property-INVARIANT salient TEMPLATE it should
match (the "lock")? This is abduction, not a per-game rule: we read it off a SEQUENCE of observed frames.

  MUTABLE  = a tracked object whose PROPERTY VECTOR (colour / orientation-aware shape / size) changes across
             frames, and which is NOT the self (the self translates but keeps its property vector).
  TEMPLATE = a property-INVARIANT object whose vector the mutable one is observed moving toward.

Returns None (no match structure) unless BOTH a mutable and a stable template exist -- the negative case is a
first-class outcome, so this never invents a match where the scene has none. Objects are segmented on the
non-background MASK (multi-colour sprites stay whole, so a recolour is one object changing, not churn) and
tracked by position-continuity (recolour/reshape robust).
"""
import numpy as np
from collections import deque
import molecule_prediction as _mp


def _bg(grid):
    return int(np.bincount(np.asarray(grid).ravel()).argmax())


def _segment_mask(grid, bg):
    """Connected components of the non-bg MASK (4-conn). Each component = one whole object (any colours)."""
    g = np.asarray(grid); H, W = g.shape
    mask = g != bg; seen = np.zeros_like(mask, bool); objs = []
    for i in range(H):
        for j in range(W):
            if not mask[i, j] or seen[i, j]:
                continue
            comp = []; dq = deque([(i, j)]); seen[i, j] = True
            while dq:
                r, c = dq.popleft(); comp.append((r, c))
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < H and 0 <= nc < W and mask[nr, nc] and not seen[nr, nc]:
                        seen[nr, nc] = True; dq.append((nr, nc))
            cells = [(int(r), int(c)) for r, c in comp]
            cr = sum(r for r, _ in cells) / len(cells); cc = sum(c for _, c in cells) / len(cells)
            objs.append(dict(cells=cells, centroid=(cr, cc),
                             vec=_mp.object_property_vector(g, cells, bg)))
    return objs


def _track(frames, bg):
    """Position-continuity tracking across frames (nearest centroid, property change allowed). Returns a list
    of trajectories; each trajectory is a list of per-frame object dicts (only frames where it was found)."""
    per_frame = [_segment_mask(f, bg) for f in frames]
    if not per_frame or not per_frame[0]:
        return []
    trajs = [[o] for o in per_frame[0]]
    last = list(per_frame[0])                      # current head object of each trajectory
    for objs in per_frame[1:]:
        used = set()
        for ti, head in enumerate(last):
            if head is None:
                continue
            best, bd = None, 1e9
            for oi, o in enumerate(objs):
                if oi in used:
                    continue
                d = abs(o["centroid"][0] - head["centroid"][0]) + abs(o["centroid"][1] - head["centroid"][1])
                if d < bd:
                    bd, best = d, oi
            if best is not None and bd <= 6:           # continuity radius
                trajs[ti].append(objs[best]); last[ti] = objs[best]; used.add(best)
            else:
                last[ti] = None
    return trajs


def abduce_match_roles(frames, self_centroid=None, bg=None, min_template_size=2):
    """Abduce (mutable, template) roles for a MATCH sub-objective from a sequence of frames, or None.

    self_centroid: approx centroid of the controllable self (excluded from roles -- it translates, it is not
                   the key). Optional; if given, a trajectory whose start overlaps it is dropped.
    Returns dict(mutable_centroid, template_vec, template_centroid) or None when no match structure exists.
    """
    frames = [np.asarray(f) for f in frames]
    if len(frames) < 2:
        return None
    if bg is None:
        bg = _bg(frames[0])
    trajs = _track(frames, bg)
    mutable_cands, stable_cands = [], []
    for tr in trajs:
        vecs = [o["vec"] for o in tr]
        if len(vecs) < 2:
            continue
        # exclude the self (overlaps the given self centroid at the start)
        if self_centroid is not None:
            c0 = tr[0]["centroid"]
            if abs(c0[0] - self_centroid[0]) + abs(c0[1] - self_centroid[1]) <= 2:
                continue
        changed = any(v != vecs[0] for v in vecs)
        if changed:
            mutable_cands.append((tr, vecs))
        elif vecs[0][2] >= min_template_size:          # stable + salient enough to be a template
            stable_cands.append((tr, vecs))
    if not mutable_cands or not stable_cands:
        return None                                    # negative case: need BOTH a mutable and a template
    # mutable = the most actively changing object (most distinct property vectors observed)
    m_tr, m_vecs = max(mutable_cands, key=lambda x: len(set(x[1])))
    # template = the stable object the mutable is observed getting CLOSEST to (smallest min distance)
    t_tr, t_vecs = min(stable_cands,
                       key=lambda x: min(_mp.property_distance(mv, x[1][-1]) for mv in m_vecs))
    return dict(mutable_centroid=m_tr[-1]["centroid"],
                template_vec=t_vecs[-1],
                template_centroid=t_tr[-1]["centroid"])


def nearest_object_locator(centroid, bg=None):
    """A locate_fn(grid)->cells that returns the cells of the object nearest `centroid` -- the position-
    continuity locator the MATCH measure uses to re-find the mutable object as it recolours/reshapes."""
    def locate(grid):
        g = np.asarray(grid); b = _bg(g) if bg is None else bg
        objs = _segment_mask(g, b)
        if not objs:
            return []
        best = min(objs, key=lambda o: abs(o["centroid"][0] - centroid[0]) + abs(o["centroid"][1] - centroid[1]))
        return best["cells"]
    return locate
