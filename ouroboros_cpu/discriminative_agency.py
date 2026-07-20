"""
discriminative_agency.py — generalizes the agency prior BEYOND translation, by composition.

The §11.241 gap: SelfLocusModel assumes the controllable thing is a marker that TRANSLATES, and
nothing separates the agent's effect from AMBIENT change (animation/HUD that happens regardless of
which action is taken). This module composes two pieces already in the DSL vocabulary:
  - effect_signature() from effect_classifier.py  (typed effect vocabulary: translate/erase/paint/
    rearrange/regional/counter/noop) — "what kind of change", no translating-agent assumption;
  - the AGENCY prior, sharpened to ACTION-DISCRIMINATIVE change: the agent's effect is the part of
    the per-step change that DIFFERS across actions; the part common to ALL actions is ambient.

It does NOT lookup or hardcode any game. It probes from anchor states (reset + short replays, all via
free resets on the deterministic env) and reports, per game: the control MODALITY, the controllable
LOCUS, and the per-action discriminative effect. This is the agency-anchor the objective grammar needs:
goal hypotheses are RELATION(locus, target) where `locus` is modality-typed, not assumed to be a marker.
"""
import numpy as np
from collections import Counter, defaultdict
from effect_classifier import effect_signature


def _changed(before, after):
    return set(map(tuple, np.argwhere(np.asarray(before) != np.asarray(after))))


def probe_agency(adapter, n_anchors=4, walk=3, seed=0):
    """Probe each action from several anchor states (reset + short random valid replays).
    Returns list of {action: (changed_cells:set, signature:dict)} — one dict per anchor."""
    rng = np.random.default_rng(seed)
    g = adapter.reset()
    acts = list(getattr(adapter, 'discrete_actions', adapter.actions)())   # nullary only; located handled separately
    if not acts:
        return []
    # build anchor action-sequences via short valid random walks
    anchors = [[]]
    seq = []
    for _ in range(n_anchors - 1):
        for _ in range(walk):
            a = acts[rng.integers(len(acts))]
            g, _, d, _ = adapter.step(a); seq.append(a)
            if d:
                g = adapter.reset(); seq = []
        anchors.append(list(seq))
    per_anchor = []
    for anc in anchors:
        d_at = {}
        for a in acts:
            adapter.reset(); ok = True
            for pa in anc:
                _, _, dd, _ = adapter.step(pa)
                if dd:
                    ok = False; break
            if not ok:
                continue
            before = adapter._grid(adapter._obs)
            try:
                after, _, _, _ = adapter.step(a)
            except Exception:
                continue                                  # skip an action that fails (robustness)
            d_at[a] = (_changed(before, after), effect_signature(before, after))
        if len(d_at) >= 2:
            per_anchor.append(d_at)
    return per_anchor


def analyze_agency(per_anchor):
    """Separate ambient (common to all actions) from discriminative (agent) change; type the modality."""
    ambient = set()
    agentive_types = Counter()           # effect type of the discriminative part, per (anchor,action)
    translate_shifts = defaultdict(list)
    translate_colors = Counter()         # colors that translate coherently (marker candidates)
    discr_regions = []                   # bounding regions of discriminative change (the locus support)
    n_actions_seen = set()
    for d_at in per_anchor:
        n_actions_seen |= set(d_at.keys())
        changed_sets = [ch for ch, _ in d_at.values()]
        common = set.intersection(*changed_sets) if changed_sets else set()
        ambient |= common
        for a, (ch, sig) in d_at.items():
            discr = ch - common
            if not discr:
                continue                  # blocked or purely ambient under this action
            agentive_types[sig["type"]] += 1
            discr_regions.append(discr)
            if sig["type"] == "translate" and sig.get("shift"):
                translate_shifts[a].append(sig["shift"])
                if sig.get("color") is not None:
                    translate_colors[int(sig["color"])] += 1
    if not agentive_types:
        return dict(modality="inert", ambient_size=len(ambient), types={}, shifts={}, locus=None)
    modality = agentive_types.most_common(1)[0][0]
    # consolidate per-action translation shifts (the move-map, when modality is translate)
    shifts = {a: Counter(s).most_common(1)[0][0] for a, s in translate_shifts.items()}
    # locus support: cells most frequently involved in discriminative change (the controllable region)
    cellfreq = Counter()
    for reg in discr_regions:
        for c in reg:
            cellfreq[c] += 1
    locus_cells = [c for c, _ in cellfreq.most_common(12)]
    locus = (tuple(np.round(np.mean(locus_cells, 0), 1).tolist()) if locus_cells else None)
    return dict(modality=modality, ambient_size=len(ambient),
                types=dict(agentive_types), shifts=shifts,
                marker_color=(translate_colors.most_common(1)[0][0] if translate_colors else None),
                locus=locus, n_discr_actions=len(shifts) if modality == "translate" else
                sum(1 for _ in agentive_types))


def _sample_cells(grid, k=16, seed=0):
    """Salient candidate cells for located actions: members of each non-bg colour + a coarse grid."""
    rng = np.random.default_rng(seed)
    bg = int(np.bincount(grid.ravel()).argmax())
    cells = []
    for c in np.unique(grid):
        if c == bg:
            continue
        ys, xs = np.where(grid == c)
        idx = rng.choice(len(ys), size=min(3, len(ys)), replace=False)
        cells += [(int(ys[i]), int(xs[i])) for i in idx]
    cells += [(r, c) for r in range(6, 64, 18) for c in range(6, 64, 18)]   # coarse grid (click-anywhere)
    seen, out = set(), []
    for cell in cells:
        if cell not in seen:
            seen.add(cell); out.append(cell)
    return out[:k]


def probe_located(adapter, n_anchors=2, walk=2, seed=0, k=16):
    """Probe LOCATED (act-at-cell) actions agnostically via the adapter's pointer affordance.
    Returns {kind: [((r,c), changed_cells, signature), ...]}.  Empty for discrete-only envs."""
    kinds = getattr(adapter, 'pointer_actions', lambda: [])()
    if not kinds:
        return {}
    rng = np.random.default_rng(seed)
    adapter.reset()
    dacts = list(getattr(adapter, 'discrete_actions', adapter.actions)())
    anchors = [[]]
    seq = []
    for _ in range(n_anchors - 1):
        for _ in range(walk):
            if not dacts:
                break
            a = dacts[rng.integers(len(dacts))]
            _, _, d, _ = adapter.step(a); seq.append(a)
            if d:
                adapter.reset(); seq = []
        anchors.append(list(seq))
    results = {kind: [] for kind in kinds}
    for kind in kinds:
        for anc in anchors:
            adapter.reset(); ok = True
            for pa in anc:
                _, _, dd, _ = adapter.step(pa)
                if dd:
                    ok = False; break
            if not ok:
                continue
            base = adapter._grid(adapter._obs)
            for (r, c) in _sample_cells(base, k, seed):
                adapter.reset()
                for pa in anc:
                    adapter.step(pa)
                before = adapter._grid(adapter._obs)
                try:
                    after, _, _, _ = adapter.step_at(kind, r, c)
                except Exception:
                    continue
                results[kind].append(((r, c), _changed(before, after), effect_signature(before, after)))
    return results


def analyze_located(results):
    """Type the located modality: which clicks change things, the dominant effect, and locality
    (effect AT the clicked cell = local paint/toggle; elsewhere = place/select)."""
    out = {}
    for kind, recs in results.items():
        active = [(cell, ch, sig) for cell, ch, sig in recs if ch]
        if not active:
            out[kind] = dict(controllable=False, n_total=len(recs)); continue
        types = Counter(sig["type"] for _, _, sig in active)
        local = sum(1 for cell, ch, _ in active if cell in ch) / len(active)
        out[kind] = dict(controllable=True, n_active=len(active), n_total=len(recs),
                         dominant_effect=types.most_common(1)[0][0], types=dict(types),
                         locality=round(local, 2))
    return out


def agency_report(adapter):
    """Combined: discrete modality + located (pointer) modality, both platform-agnostic."""
    rpt = analyze_agency(probe_agency(adapter))
    rpt["located"] = analyze_located(probe_located(adapter))
    return rpt
