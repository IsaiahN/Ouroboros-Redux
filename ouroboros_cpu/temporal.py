"""temporal.py -- the TEMPORAL modality: games where the controllable is your position in a navigable
HISTORY, not a body in the present. This is the one case where "self-as-causality" is literally true --
the object you act on IS the sequence of states you have produced (the footprints, not the walker).

Operational signature (game-agnostic, NOT reverse-engineered from g50t):
  * TIMELINE / REWIND -- some actions ADVANCE the world to new global frames while others REWIND it to
    GLOBAL frames already seen. A forward-only world (translate / autonomous / command) never revisits a
    whole prior frame on purpose; a timeline does. The substrate is the frame-history itself.
  * PAST-MANIPULATION (the stronger signature) -- after rewinding to an earlier state, an intervening
    action CHANGES a future you had already observed: the edit propagates forward. Mere reversible movement
    does not do this; editing the past does. (Best-effort here; flagged honestly.)

The self produced is modality='temporal': the controllable is timeline NAVIGATION (and, if past-manip,
EDITING). Its prediction is falsifiable: a forward-only world disproves the rewind claim. Distinguishing
true past-manipulation from a merely reversible mover needs the propagation probe; without it, only the
timeline claim is committed.
"""
import numpy as np
from collections import Counter


def _snap(ad):
    return np.asarray(ad._grid(ad._obs)).copy()


def analyze_timeline(adapter, depth=12, seed=0):
    """Classify each action as ADVANCE (new global frame) / REWIND (revisits a seen global frame) / noop."""
    try:
        adapter.reset()
    except Exception:
        return dict(is_timeline=False, reason="reset failed")
    acts = list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions())
    if not acts:
        return dict(is_timeline=False, reason="no discrete actions")
    rng = np.random.default_rng(seed)
    f0 = _snap(adapter); seen = {f0.tobytes(): 0}; n_states = 1
    role = {a: Counter() for a in acts}
    for _ in range(depth * len(acts)):
        a = acts[rng.integers(len(acts))]
        bf = _snap(adapter)
        try:
            adapter.step(a)
        except Exception:
            continue
        af = _snap(adapter)
        if np.array_equal(af, bf):
            role[a]["noop"] += 1; continue
        k = af.tobytes()
        if k in seen:
            role[a]["rewind"] += 1
        else:
            role[a]["advance"] += 1; seen[k] = n_states; n_states += 1
    rewinders = [a for a in acts if role[a]["rewind"] >= 2 and role[a]["rewind"] > role[a]["advance"]]
    advancers = [a for a in acts if role[a]["advance"] >= 2 and role[a]["advance"] > role[a]["rewind"]]
    return dict(is_timeline=bool(rewinders and advancers), rewinders=rewinders, advancers=advancers,
                n_states=n_states, role={getattr(a, "name", a): dict(v) for a, v in role.items()})


def detect_past_manipulation(adapter, advancers, rewinders, editors, span=3, seed=0):
    """Stronger signature: experience a future, REWIND to the past, EDIT it, RE-EXPERIENCE the future --
    if an already-observed future comes out DIFFERENT, the past edit propagated (true past-manipulation,
    not a mere forward persistent effect, because the change is to a future you had ALREADY seen)."""
    if not (advancers and rewinders and editors):
        return dict(past_manip=False, reason="need advancer + rewinder + a distinct editor action")
    adv = advancers[0]; rew = rewinders[0]
    try:
        adapter.reset()
    except Exception:
        return dict(past_manip=False)
    future = [_snap(adapter)]
    for _ in range(span):
        adapter.step(adv); future.append(_snap(adapter))      # the future as originally experienced
    for ed in editors:
        try:
            adapter.reset()
        except Exception:
            break
        for _ in range(span):
            adapter.step(adv)                                  # go forward into the timeline
        for _ in range(span):
            adapter.step(rew)                                  # REWIND back to the past
        adapter.step(ed)                                       # EDIT the past state
        edited = [_snap(adapter)]
        for _ in range(span):
            adapter.step(adv); edited.append(_snap(adapter))   # re-experience the (now edited) future
        if any(i < len(future) and not np.array_equal(future[i], edited[i]) for i in range(1, len(edited))):
            return dict(past_manip=True, editor=getattr(ed, "name", ed),
                        evidence="rewinding to the past, editing it, then re-advancing changed an "
                                 "ALREADY-OBSERVED future (the edit propagated) -- past-manipulation")
    return dict(past_manip=False, reason="no past edit changed an already-observed future (mere reversibility)")


def _nav_pairs_and_editors(adapter, acts):
    """A NAVIGATOR has an INVERSE (reset->A->B returns to the start frame) -- reversible. An EDITOR does
    something but has NO inverse -- a persistent change. Past-manipulation must EDIT with an editor; using a
    navigator as the 'editor' just shifts the cursor and gives false positives."""
    try:
        adapter.reset()
    except Exception:
        return [], []
    f0 = _snap(adapter)
    pairs = []; reversible = set()
    for A in acts:
        adapter.reset(); adapter.step(A)
        if np.array_equal(_snap(adapter), f0):
            continue                                   # A is a no-op from start
        for B in acts:
            if B is A:
                continue
            adapter.reset(); adapter.step(A); adapter.step(B)
            if np.array_equal(_snap(adapter), f0):
                pairs.append((A, B)); reversible.add(A); reversible.add(B); break
    editors = []
    for a in acts:
        if a in reversible:
            continue
        adapter.reset(); adapter.step(a)
        if not np.array_equal(_snap(adapter), f0):     # does something, but has no inverse -> persistent edit
            editors.append(a)
    return pairs, editors


def probe_temporal(adapter, depth=12, seed=0, search=True):
    """Temporal probe. The COMMITTED discriminator is PAST-MANIPULATION PROPAGATION: editing the past
    changes an already-observed future -- which a reversible mover CANNOT do (frame-revisitation alone does
    not distinguish them; a maze-walker revisits global frames too, and accumulating edits defeat
    revisitation entirely). So we discover inverse-paired NAVIGATORS vs persistent EDITORS and test whether
    rewinding + editing + re-advancing changes a future we had already seen. Navigability is fallback
    evidence only."""
    tl = analyze_timeline(adapter, depth=depth, seed=seed)
    if "role" not in tl:
        return None
    acts = list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions())
    revisits = sum((r.get("rewind", 0) if isinstance(r, dict) else 0) for r in tl["role"].values())
    pm = dict(past_manip=False)
    if search and len(acts) >= 2:
        pairs, editors = _nav_pairs_and_editors(adapter, acts)
        for adv, rew in pairs:
            if not editors:
                break
            pm = detect_past_manipulation(adapter, [adv], [rew], editors, seed=seed)
            if pm.get("past_manip"):
                break
    if pm.get("past_manip"):
        return dict(ctype="self", modality="temporal", identity="timeline-edit", substrate="frame-history",
                    confidence=round(min(1.0, 0.55 + 0.05 * tl["n_states"]), 2), past_manipulation=True,
                    evidence="past-manipulation: " + pm["evidence"],
                    prediction=dict(kind="temporal_edit",
                                    text="editing a rewound (past) state changes an already-observed FUTURE; "
                                         "immutable futures falsify past-manipulation"))
    if revisits >= 3:        # navigable but no demonstrated propagation -> reversible, NOT committed temporal
        return dict(ctype="self", modality="temporal?", identity="navigable-reversible",
                    substrate="frame-history", confidence=0.4, past_manipulation=False,
                    evidence=(f"navigable/reversible state space (revisits {revisits} prior global frames) "
                              f"but NO past-edit propagation demonstrated -- may be a reversible mover, not "
                              f"true past-manipulation (uncommitted)"),
                    prediction=dict(kind="temporal_navigable",
                                    text="some action sequence returns the whole world to an earlier global "
                                         "frame; a forward-only world falsifies this"))
    return None              # forward-only and no propagation -> not temporal
