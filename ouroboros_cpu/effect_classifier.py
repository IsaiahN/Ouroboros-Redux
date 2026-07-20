# effect_classifier.py — the missing substrate: a logical-grid scale detector + a general action-effect
# signature classifier that characterizes what each action DOES without assuming a translating agent.
# Built because the global-transform composer returns (None,None) on the public set: those games are
# cursor/click/regional-recolor dynamics on small logical grids, not whole-grid geometric transforms.
import numpy as np
from collections import Counter, defaultdict


# ---------------------------------------------------------------------------
# 1) LOGICAL-GRID SCALE DETECTION
# The frame is a (mostly uniform) background with sprites placed at SCALED positions: a 1x1 logical
# sprite renders as an s x s block, so the cell size s divides every sprite's bbox dimensions AND every
# sprite's offset from the grid origin. We recover s as the GCD of those, robust to background texture.
# ---------------------------------------------------------------------------
def _components(frame, bg):
    """4-connected components of each non-background color; yields (color, (r0,r1,c0,c1), size)."""
    H, W = frame.shape
    seen = np.zeros((H, W), bool)
    for r in range(H):
        for c in range(W):
            v = int(frame[r, c])
            if v == bg or seen[r, c]:
                continue
            stack = [(r, c)]; seen[r, c] = True
            r0 = r1 = r; c0 = c1 = c; n = 0
            while stack:
                y, x = stack.pop(); n += 1
                r0 = min(r0, y); r1 = max(r1, y); c0 = min(c0, x); c1 = max(c1, x)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny, nx] and int(frame[ny, nx]) == v:
                        seen[ny, nx] = True; stack.append((ny, nx))
            yield v, (r0, r1, c0, c1), n


def _gcd_list(vals):
    from math import gcd
    from functools import reduce
    vals = [int(v) for v in vals if v > 0]
    return reduce(gcd, vals) if vals else 0


def detect_grid_dims(frame, max_n=56):
    """Return (n_rows, n_cols): inferred LOGICAL grid dims, via the GCD of sprite bbox spans + offsets.
    Robust to uniform/textured backgrounds (those carry no grid); falls back to the frame size."""
    frame = np.asarray(frame); H, W = frame.shape
    bg = int(np.bincount(frame.ravel()).argmax())
    comps = [c for c in _components(frame, bg) if c[2] >= 4]      # drop 1-3px texture dots
    if not comps:
        return (1, 1)
    h_spans, w_spans, r_off, c_off = [], [], [], []
    for _, (r0, r1, c0, c1), _ in comps:
        h_spans.append(r1 - r0 + 1); w_spans.append(c1 - c0 + 1)
        r_off.append(r0); c_off.append(c0)
    # cell size = GCD of spans AND offsets on each axis (a scaled grid makes both multiples of s)
    s_r = _gcd_list(h_spans + r_off) or _gcd_list(h_spans) or 1
    s_c = _gcd_list(w_spans + c_off) or _gcd_list(w_spans) or 1
    nr = min(max(1, round(H / s_r)), max_n) if s_r else H
    nc = min(max(1, round(W / s_c)), max_n) if s_c else W
    return (nr, nc)


def to_logical(frame, dims):
    """Downscale a frame to its logical grid by taking the mode within each (non-integer-safe) cell band."""
    frame = np.asarray(frame); H, W = frame.shape
    nr, nc = dims
    rb = [round(i * H / nr) for i in range(nr + 1)]
    cb = [round(j * W / nc) for j in range(nc + 1)]
    out = np.zeros((nr, nc), dtype=int)
    for i in range(nr):
        for j in range(nc):
            blk = frame[rb[i]:rb[i + 1], cb[j]:cb[j + 1]].ravel()
            if blk.size:
                v, c = np.unique(blk, return_counts=True); out[i, j] = int(v[c.argmax()])
    return out


# ---------------------------------------------------------------------------
# 2) ACTION-EFFECT SIGNATURE
# ---------------------------------------------------------------------------
def effect_signature(before, after):
    """Characterize a transition at LOGICAL resolution, with NO translating-agent assumption.
    Returns a dict signature: magnitude, region, colors added/removed, and a coarse TYPE."""
    before = np.asarray(before); after = np.asarray(after)
    ch = np.argwhere(before != after)
    if len(ch) == 0:
        return dict(type="noop", n=0, centroid=None, added=(), removed=(), bbox=None)
    bc = {(r, c, int(before[r, c])) for r, c in ch}
    ac = {(r, c, int(after[r, c])) for r, c in ch}
    cols_b = set(int(before[r, c]) for r, c in ch)
    cols_a = set(int(after[r, c]) for r, c in ch)
    added = tuple(sorted(cols_a - cols_b)); removed = tuple(sorted(cols_b - cols_a))
    cen = tuple(np.round(ch.mean(0), 1).tolist())
    bbox = (int(ch[:, 0].min()), int(ch[:, 0].max()), int(ch[:, 1].min()), int(ch[:, 1].max()))
    n = len(ch)
    # TYPE inference:
    #   tiny (<=2 cells, edge) -> counter (a step/score pixel)
    #   a colored cluster reappears shifted -> translate (cursor/object move)
    #   colors only swapped, same positions -> recolor
    #   colors removed/added without a shift -> regional update
    H = before.shape[0]
    edge = bbox[0] >= H - 2 or bbox[1] >= before.shape[0] - 2 or bbox[3] >= before.shape[1] - 2
    t = "regional"
    if n <= 2 and (bbox[0] >= H - 3 or bbox[2] >= before.shape[1] - 3):
        t = "counter"
    else:
        # translation test: does the set of (changed) BEFORE-foreground cells equal the AFTER-foreground
        # set under a single (dr,dc) shift? (object/cursor moved)
        moved = _translation_shift(before, after, ch)
        if moved is not None:
            t = "translate"
            return dict(type=t, n=n, centroid=cen, added=added, removed=removed, bbox=bbox,
                        shift=moved[0], color=moved[1])
        if not added and not removed:
            t = "rearrange"          # same palette, positions permuted
        elif removed and not added:
            t = "erase"              # colors removed (collection / clearing)
        elif added and not removed:
            t = "paint"              # colors added
    return dict(type=t, n=n, centroid=cen, added=added, removed=removed, bbox=bbox)


def _translation_shift(before, after, ch, max_shift=8):
    """If a single object moved by (dr,dc), return ((dr,dc), color). Tries each non-bg color that changed
    and picks the SMALLEST coherent mover (a cursor), not merely the most-changed color."""
    bg = int(np.bincount(before.ravel()).argmax())
    cand = [c for c in set(int(before[r, c]) for r, c in ch) if c != bg]
    best = None; best_key = None
    for color in cand:
        src = set(map(tuple, np.argwhere(before == color)))
        dst = set(map(tuple, np.argwhere(after == color)))
        if not src or not dst or abs(len(src) - len(dst)) > max(2, 0.25 * len(src)):
            continue
        if len(src) > 250:                      # not a cursor-sized object
            continue
        sc = np.array(list(src)).mean(0); dc_ = np.array(list(dst)).mean(0)
        dr, dcol = int(round(dc_[0] - sc[0])), int(round(dc_[1] - sc[1]))
        if (dr, dcol) == (0, 0) or abs(dr) > max_shift or abs(dcol) > max_shift:
            continue
        shifted = {(r + dr, c + dcol) for r, c in src}
        overlap = len(shifted & dst) / max(1, len(dst))
        if overlap < 0.6:
            continue
        # prefer high overlap, then SMALL object (cursor)
        key = (round(overlap, 2), -len(src))
        if best_key is None or key > best_key:
            best_key = key; best = ((dr, dcol), color)
    return best


# ---------------------------------------------------------------------------
# 3) ACTION-EFFECT CLASSIFIER (accumulates observations, learns per-action behavior, classifies the game)
# ---------------------------------------------------------------------------
class ActionEffectClassifier:
    """Characterizes what each action does, at PIXEL resolution (robust: needs no static scale detection).
    Where an action translates something, the pixel shift IS the effective cell scale, recovered for free."""

    def __init__(self):
        self.dims = None                    # best-effort static logical dims (may be unreliable)
        self.obs = defaultdict(list)        # action -> list of pixel-resolution signatures

    def observe(self, before, after, action):
        if self.dims is None:
            try: self.dims = detect_grid_dims(before)
            except Exception: self.dims = None
        self.obs[action].append(effect_signature(np.asarray(before), np.asarray(after)))

    def cell_scale(self):
        """Effective cell scale = median magnitude of the CONSOLIDATED per-action shifts (one mode-shift per
        action), filtering noise. Robust vs raw single-transition shifts that can catch 1px artifacts."""
        per_action = {}
        for a, sigs in self.obs.items():
            shifts = [s.get("shift") for s in sigs if s.get("type") == "translate" and s.get("shift")
                      and (s["shift"][0] == 0) != (s["shift"][1] == 0)]
            if shifts:
                per_action[a] = Counter(shifts).most_common(1)[0][0]
        mags = [abs(dr) + abs(dc) for (dr, dc) in per_action.values() if abs(dr) + abs(dc) >= 2]
        if not mags:
            return None
        return int(round(float(np.median(mags))))

    def action_profile(self, action):
        """Consolidated behavior of one action: dominant effect type, consistency, mean magnitude, shift."""
        sigs = self.obs.get(action, [])
        if not sigs:
            return None
        types = Counter(s["type"] for s in sigs)
        dom, dom_n = types.most_common(1)[0]
        consistency = dom_n / len(sigs)
        mags = [s["n"] for s in sigs if s["type"] == dom]
        shifts = [s.get("shift") for s in sigs if s["type"] == "translate" and s.get("shift")]
        shift = Counter(shifts).most_common(1)[0][0] if shifts else None
        return dict(type=dom, consistency=round(consistency, 2),
                    mean_cells=round(float(np.mean(mags)), 1) if mags else 0,
                    n_obs=len(sigs), shift=shift)

    def classify_game(self):
        """Coarse game family from per-action profiles + the recovered cell scale."""
        profs = {a: self.action_profile(a) for a in self.obs if self.action_profile(a)}
        profs = {a: p for a, p in profs.items() if p}
        if not profs:
            return dict(family="unknown", scale=None, actions={})
        move_acts = {a: p["shift"] for a, p in profs.items() if p["type"] == "translate" and p["shift"]}
        effective = [a for a, p in profs.items() if p["type"] not in ("noop", "counter")]
        if len(move_acts) >= 2:
            family = "navigable"                # >=2 actions translate something -> can route a planner
        elif any(p["type"] in ("erase", "paint", "rearrange", "regional") for p in profs.values()):
            family = "regional_or_click"        # actions cause regional edits, not translation
        elif effective:
            family = "single_effect"
        else:
            family = "inert"                    # only counters move -> wrong action interface
        return dict(family=family, scale=self.cell_scale(), move_actions=move_acts,
                    actions={a: p for a, p in profs.items()})


# ---------------------------------------------------------------------------
# 4) CONTROL LAYER — drive the controllable object to a target cell using the DISCOVERED action-map
#    (no assumed direction mapping; works off what was measured from interaction).
# ---------------------------------------------------------------------------
class DiscoveryController:
    """Given a classifier that has discovered the per-action shift map, identify the controllable object
    and emit the action that best moves it toward a target. The action-map is acquired from interaction,
    so this works even when the action->direction mapping is non-standard or game-specific."""

    def __init__(self, classifier):
        self.clf = classifier
        self.action_map = {}            # action -> (dr,dc), the discovered shifts
        self.obj_color = None

    def robust_action_map(self, frames, actions):
        """Identify the cursor as the mover whose displacement is CONSISTENT per action AND DISCRIMINATIVE
        across actions (different actions -> different shifts). Drift/animation moves the same way for every
        action (consistent but not discriminative) and is rejected. Then read the map from that object."""
        frames = [np.asarray(f) for f in frames]
        bg = int(np.bincount(frames[0].ravel()).argmax())
        colors = set()
        for f in frames[:8]:
            for v in np.unique(f):
                if int(v) != bg:
                    colors.add(int(v))

        def cen(f, color):
            comps = [c for c in _components(f, bg) if c[0] == color]
            if comps:
                comps.sort(key=lambda c: -(c[2] / max(1, (c[1][1]-c[1][0]+1)*(c[1][3]-c[1][2]+1))))
                _, (r0, r1, c0, c1), _ = comps[0]
                return ((r0 + r1) / 2.0, (c0 + c1) / 2.0)
            cells = np.argwhere(f == color)
            return (float(cells[:, 0].mean()), float(cells[:, 1].mean())) if 0 < len(cells) <= 400 else None

        best, best_key, best_map = None, None, {}
        for color in colors:
            disp = {}
            for i in range(min(len(actions), len(frames) - 1)):
                a = actions[i]; c0 = cen(frames[i], color); c1 = cen(frames[i + 1], color)
                if c0 and c1:
                    d = (int(round(c1[0] - c0[0])), int(round(c1[1] - c0[1])))
                    if abs(d[0]) + abs(d[1]) <= 12:
                        disp.setdefault(a, []).append(d)
            amap = {}
            for a, ds in disp.items():
                nz = [d for d in ds if d != (0, 0)]
                if nz:
                    shift, cnt = Counter(nz).most_common(1)[0]
                    if cnt >= max(1, len(ds) // 2):        # consistent majority for this action
                        amap[a] = shift
            if len(amap) < 2:
                continue
            consistent = len(amap)
            distinct = set(amap.values())
            discriminative = len(distinct)               # distinct shifts across actions
            axis_aligned = len({s for s in distinct if (s[0] == 0) != (s[1] == 0)})  # cursor moves along axes
            key = (axis_aligned, discriminative, consistent)
            if best_key is None or key > best_key:
                best_key, best, best_map = key, color, amap
        if best is not None and best_key[0] >= 2:            # require >=2 distinct AXIS-ALIGNED shifts
            self.obj_color = best; self.action_map = best_map
            return best_map
        return self.fit()

    def fit(self):
        """Consolidate the discovered action->shift map AND the controllable object's color (the color that
        the translate signatures report moving)."""
        amap = {}; colors = Counter()
        for a, sigs in self.clf.obs.items():
            shifts = [s.get("shift") for s in sigs if s.get("type") == "translate" and s.get("shift")]
            if shifts:
                amap[a] = Counter(shifts).most_common(1)[0][0]
            for s in sigs:
                if s.get("type") == "translate" and s.get("color") is not None:
                    colors[s["color"]] += 1
        self.action_map = amap
        self.obj_color = colors.most_common(1)[0][0] if colors else None
        return bool(amap)

    def robust_fit(self, frames, actions):
        """Identify the cursor by MOTION CORRELATION across many steps: the non-bg color whose centroid
        displacement most consistently matches the discovered action-map. Robust where single-transition
        object-ID is not (uses all observations, principled: the cursor IS the thing that obeys the map)."""
        self.fit()                                   # discover action_map from signatures
        if not self.action_map or len(frames) < 3:
            return self.obj_color
        frames = [np.asarray(f) for f in frames]
        bg = int(np.bincount(frames[0].ravel()).argmax())
        colors = set()
        for f in frames[:6]:
            for v in np.unique(f):
                if int(v) != bg:
                    colors.add(int(v))

        def color_centroid(f, color):
            cells = np.argwhere(f == color)
            return (float(cells[:, 0].mean()), float(cells[:, 1].mean())) if len(cells) and len(cells) <= 400 else None

        best, best_key = None, None
        for color in colors:
            cents = [color_centroid(f, color) for f in frames]
            match, n = 0, 0
            for i in range(min(len(actions), len(frames) - 1)):
                a = actions[i]
                if a not in self.action_map or cents[i] is None or cents[i + 1] is None:
                    continue
                pred = self.action_map[a]
                act = (cents[i + 1][0] - cents[i][0], cents[i + 1][1] - cents[i][1])
                if abs(act[0] - pred[0]) + abs(act[1] - pred[1]) <= 1.5:
                    match += 1
                n += 1
            if n < 2:
                continue
            score = match / n
            sizes = [int((f == color).sum()) for f in frames if (f == color).any()]
            med_size = float(np.median(sizes)) if sizes else 1e9
            key = (round(score, 2), -med_size)       # high correlation, then smaller object (cursor)
            if best_key is None or key > best_key:
                best_key = key; best = color
        if best is not None and best_key[0] >= 0.5:
            self.obj_color = best
        return self.obj_color

    def locate(self, frame):
        """Find the controllable object's centroid by tracking its DISCOVERED color. Falls back to the most
        compact small component only if the color is unknown."""
        frame = np.asarray(frame); bg = int(np.bincount(frame.ravel()).argmax())
        if self.obj_color is not None:
            cells = np.argwhere(frame == self.obj_color)
            if len(cells):
                # if the color forms multiple blobs, take the most compact connected component
                comps = [c for c in _components(frame, bg) if c[0] == self.obj_color]
                if comps:
                    comps.sort(key=lambda c: -(c[2] / max(1, (c[1][1]-c[1][0]+1)*(c[1][3]-c[1][2]+1))))
                    _, (r0, r1, c0, c1), _ = comps[0]
                    return ((r0 + r1) / 2.0, (c0 + c1) / 2.0)
                return (float(cells[:, 0].mean()), float(cells[:, 1].mean()))
        comps = [c for c in _components(frame, bg) if 1 <= c[2] <= 200]
        if not comps:
            return None
        comps.sort(key=lambda c: (-(c[2] / max(1, (c[1][1]-c[1][0]+1)*(c[1][3]-c[1][2]+1))), c[2]))
        _, (r0, r1, c0, c1), _ = comps[0]
        return ((r0 + r1) / 2.0, (c0 + c1) / 2.0)

    def best_action_toward(self, cur, target):
        """Pick the action whose DISCOVERED shift most reduces distance to target."""
        if not self.action_map or cur is None or target is None:
            return None
        d0 = abs(cur[0] - target[0]) + abs(cur[1] - target[1])
        best, gain = None, 1e-6
        for a, (dr, dc) in self.action_map.items():
            nd = abs(cur[0] + dr - target[0]) + abs(cur[1] + dc - target[1])
            if d0 - nd > gain:
                gain = d0 - nd; best = a
        return best
