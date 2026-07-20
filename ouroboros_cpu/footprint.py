"""footprint.py -- STANDALONE causal, modality-aware self-footprint extractor (observe-only).

Goal: extract the SET OF CELLS that constitute the self's effect, WITHOUT being handed a marker_color
(which would just inherit the controllable-ID wall). The marker is derived CAUSALLY:

  discriminative cells = changed(action_a) minus ambient(common to all actions)  -> where my action CHOICE
                         steers things (the destination I control).
  causal marker_color  = the dominant colour that APPEARS at those discriminative destinations -> the
                         agent's colour, derived from "what shows up where I steer", never guessed.
  footprint (translate)= that colour's cells (the agent blob).
  footprint (located)  = the cells a click writes that DIFFER by which cell I click (discriminative click).
  footprint (regional) = the discriminative recoloured cells.

The TEST compares this causal footprint to a ground truth computed by a DIFFERENT method (geometric rigid
translation for avatars; click-proximity for located) so agreement is informative, not circular.
"""
import numpy as np
from collections import Counter


def _arr(ad): return np.asarray(ad._grid(ad._obs))
def _changed(a, b): return set(map(tuple, np.argwhere(np.asarray(a) != np.asarray(b))))
def _bg(g):
    v, c = np.unique(g, return_counts=True); return int(v[np.argmax(c)])


# ---------------- LIVE causal self, no reset, no marker colour ---------------------------------------
def self_signature(inducer):
    """The self's colour SIGNATURE, derived causally from the agent's own play. No reset. No marker colour.

    `discriminative()` below probes each action once FROM RESET, so every probe starts from the same state and
    `changed(a)` is comparable across actions. That control is what buys `ambient` -- the cells that change no matter
    what you do. It is a good experiment and it is **unavailable**: RESET is hard-banned mid-game because it wipes
    level progress to 0, and this module predates that ban.

    The same answer is now free. `ObjectTransitionInducer` watches every transition the agent makes anyway and
    induces, per object TYPE, `(colour_signature, size_bucket, action, context) -> translate | stay | vanish`. The
    object whose confirmed law is TRANSLATE under a directional action is, by construction, the thing my action
    choice steers. That IS the discriminative test -- run continuously, on real play, at zero action cost.

    And it returns a **frozenset**, not a colour. That matters more than the reset does:
    `causal_marker_color()` below returns `cnt.most_common(1)[0][0]` -- ONE dominant colour -- which is precisely the
    controllable-ID wall this module's own docstring promises to avoid. The avatar here is a 5x5 composite (two rows
    of one colour over three of another), so any single-colour answer names half a body. The signature names all of it.
    """
    best, support = None, 0
    for key, ctr in (getattr(inducer, "table", {}) or {}).items():
        try:
            eff, status = inducer._rule(key)
        except Exception:
            continue
        if status != "confirmed" or not eff or eff[0] != "translate":
            continue
        n = sum(ctr.values())
        if n > support:
            best, support = key[0], n                      # key = (colour_sig, size_bucket, action, context)
    return (set(best) if best else None), support


def readout_hypotheses(inducer):
    """Everything my play has been confirmed to change, ranked most-credible first. A queue, not an answer.

    Returns [(identity, support, why)].

    CREDIBILITY IS SELECTIVITY, NOT A COUNT.

    A cause is specific. If a thing changes under ONE of the things I touch and holds still under the rest, that
    thing is its cause and my choice moved it. If it changes no matter WHAT I touch, then nothing I touched explains
    it -- it is running on something I am not holding, and it is a clock.

    Measured on ls20, accumulated across episodes, holding the action fixed:

        the glyph  action=1 -> {4: stay, 0: restate, 5: vanish}          changes under 1 contact
        the fuel bar action=2 -> {3: restate, 4: restate, 0: restate}    changes under all of them

    The previous version asked "does the effect vary at all?" -- both of these vary, so it separated nothing and fell
    through to ranking by observation count, 681 vs 505. It got the right answer for a reason it could not defend,
    and printed "my CHOICE moved it" next to a fuel bar. A count is not a reason.

    Ties break on breadth of evidence, not on raw support: a law seen under more distinct antecedents has been given
    more chances to be wrong.
    """
    from collections import defaultdict as _dd
    per = _dd(lambda: {"changed_on": set(), "held_on": set(), "sup": 0})
    for key, ctr in (getattr(inducer, "table", {}) or {}).items():
        d = per[key[0]]
        d["sup"] += sum(ctr.values())
        # EVERY observation counts, confirmed or not. Requiring `confirmed` here was a contradiction in terms: a
        # hypothesis that has to be confirmed before it may be a hypothesis is a conclusion. It also inverted the
        # ranking by construction -- confirmation needs REPETITION, and the readout's law is rare BY DESIGN (you
        # only reach a trigger occasionally: 3 changes in 522 live actions) while the fuel bar's is constant (469).
        # So the common thing confirmed instantly and the rare, selective, INFORMATIVE thing never became visible.
        for eff in ctr:
            if eff and eff[0] in ("restate", "recolor", "rotate"):
                d["changed_on"].add(key[3])                   # WHAT I TOUCHED. Not (action, contact): the same
            elif eff and eff[0] == "stay":                    # contact under four actions is one antecedent, not
                d["held_on"].add(key[3])                      # four, and counting pairs hid "it changes under one".
    out = []
    for ident, d in per.items():
        if not d["changed_on"]:
            continue
        seen = len(d["changed_on"]) + len(d["held_on"])
        if not seen:
            continue
        sel = 1.0 - (len(d["changed_on"]) / float(seen))     # 1.0 = changes under exactly one thing I do
        if len(d["changed_on"]) >= seen:
            why = ("changes no matter WHAT I touch (all %d) -> nothing I touch explains it; it is running on "
                   "something I am not holding" % seen)
        else:
            why = ("changes under %d of the %d things I have touched, and holds still under the other %d -> the more "
                   "of them it ignores, the more it is what I touched that moved it"
                   % (len(d["changed_on"]), seen, seen - len(d["changed_on"])))
        out.append((set(ident), d["sup"], why, sel, seen))
    out.sort(key=lambda t: (-t[3], -t[4]))
    return [(i_, n, w) for i_, n, w, _s, _seen in out]


def mutable_signature(inducer):
    """The READOUT: the object my own play RESTATES without steering. Derived, not declared.

    Sibling of `self_signature()`, from the same table, by the same protocol -- because it is the same question asked
    about a different verb. That function asks "what does my action choice STEER?" and the board answers `translate`.
    This asks "what does my play RESTATE?" and the board answers `rotate` or `recolor`: an object that changes what
    it LOOKS like while staying where it is. Nobody has to say the word display.

    WHY THIS EXISTS, WRITTEN DOWN SO IT IS NOT REPEATED
    ---------------------------------------------------
    I was told how this game works -- one glyph in the status bar, one on the board, triggers cycle the first until
    it matches the second -- and I wrote that into the detector as `key = the glyph whose extent is in the HUD`, and
    called it "a definition, not a heuristic," as though that were the virtue. It is the defect. A definition handed
    down from outside is a lookup table with better manners. It would have passed ls20 and taught the agent nothing,
    and the private eval is OOD by construction: no status bar I know of, no screenshot, nobody to ask.

    The exemplar was already in this file. `self_signature()` refuses a colour it was handed and earns identity from
    39 transitions of the agent's own play. The same move works here and costs nothing extra, because the inducer is
    watching every transition anyway:

        translate under my directional actions -> that is ME          (self_signature)
        rotate / recolor, in place             -> that is a READOUT   (here)
        confirmed `stay` under everything      -> that is a TARGET    (invariant_signatures)

    An object I change is a readout. An object I have never changed is a target. Neither fact needs to know what a
    HUD is, where the level designer put it, how big it is drawn, or that this is ls20.
    """
    best, support = None, 0
    for key, ctr in (getattr(inducer, "table", {}) or {}).items():
        try:
            eff, status = inducer._rule(key)
        except Exception:
            continue
        if status != "confirmed" or not eff or eff[0] not in ("rotate", "recolor", "restate"):
            continue
        n = sum(ctr.values())
        if n > support:
            best, support = key[0], n                      # key = (colour_sig, size_bucket, action, context)
    return (set(best) if best else None), support


def invariant_signatures(inducer, min_support=2):
    """The TARGETS: every object type whose ONLY confirmed law is `stay` -- nothing I have done has ever moved,
    turned, recoloured or removed it.

    This is the weakest possible claim and that is the point: it is not "the lock", it is "a thing I have never
    changed". Whether such a thing is a target, a wall decoration or scenery is not decided here -- it is decided by
    what happens when the readout comes to match one. That keeps the concept honest on a board where the target
    moves, where there are three of them, or where there is none.
    """
    out = {}
    for key, ctr in (getattr(inducer, "table", {}) or {}).items():
        try:
            eff, status = inducer._rule(key)
        except Exception:
            continue
        sig = key[0]
        n = sum(ctr.values())
        if status == "confirmed" and eff and eff[0] == "stay":
            if sig not in out or n > out[sig]:
                out[sig] = n
        elif eff and eff[0] in ("translate", "rotate", "recolor", "restate", "vanish"):
            out.pop(sig, None)                             # it changed once -> it was never invariant
            out[sig] = -1                                  # tombstone: never re-admit this signature
    return {s: n for s, n in out.items() if n >= min_support}


def self_footprint_live(grid, signature, terrain=()):
    """Every cell of the body, from the signature -- the connected object wearing those colours."""
    import numpy as _np
    if not signature:
        return set()
    g = _np.asarray(grid)
    if g.ndim == 3:
        g = g[0]
    sig, bad = set(int(c) for c in signature), set(int(c) for c in (terrain or ()))
    seed = _np.where(_np.isin(g, list(sig)))
    if not len(seed[0]):
        return set()
    H, W = g.shape
    stack = [(int(seed[0][0]), int(seed[1][0]))]
    seen = set(stack)
    while stack and len(seen) <= 200:
        r, c = stack.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and (nr, nc) not in seen and int(g[nr, nc]) not in bad:
                seen.add((nr, nc)); stack.append((nr, nc))
    return seen


# ---------------- causal discriminative core (no colour input) --------------------------------------
# WARNING: everything below calls ad.reset(). RESET IS HARD-BANNED during gameplay -- it wipes all accumulated
# level progress back to 0. These are usable ONLY offline, against a recording. Use self_signature() live.
def discriminative(ad):
    """Probe each discrete action once from reset; return (before0, {a:(after,changed)}, ambient, discr_union)."""
    g0 = _arr(ad); acts = list(getattr(ad, "discrete_actions", ad.actions)())
    per = {}
    for a in acts:
        ad.reset(); before = _arr(ad)
        try: ad.step(a)
        except Exception: continue
        per[a] = (_arr(ad), _changed(before, _arr(ad)))
    if len(per) < 2:
        return g0, per, set(), set()
    # ambient = cells that change under EVERY action that actually did something; a blocked action
    # (changed == empty) must NOT collapse the intersection to nothing.
    sets = [ch for _, ch in per.values() if ch]
    ambient = set.intersection(*sets) if sets else set()
    discr_union = set().union(*[ch - ambient for _, ch in per.values()])
    return g0, per, ambient, discr_union


def causal_marker_color(per, discr_union, bg=None):
    """The dominant NON-BACKGROUND colour that appears at discriminative destinations = the agent's
    colour (derived from what shows up where my action choice steers things)."""
    cnt = Counter()
    for after, ch in per.values():
        for (r, c) in (ch & discr_union):
            col = int(after[r, c])
            if bg is not None and col == bg:
                continue                      # background is not the agent
            cnt[col] += 1
    if not cnt:
        return None
    return cnt.most_common(1)[0][0]


def footprint_translate(ad, marker):
    """Agent blob = all cells of the causally-derived marker colour, in the reset frame."""
    if marker is None:
        return set()
    ad.reset(); g = _arr(ad)
    return set(map(tuple, np.argwhere(g == marker)))


def footprint_translate_causal(before, after, discr):
    """Color-AGNOSTIC avatar footprint: among DISCRIMINATIVE changed cells, the subset that moved
    coherently (arrived cells that are new occupancy + their vacated origins). Robust to an agent that
    shares a colour with floor/structure, because it keys on action-contingent MOTION, not colour."""
    before = np.asarray(before); after = np.asarray(after); bg = _bg(before)
    best = set()
    # colours that appear at discriminative destinations (where my action steered something)
    cols = Counter(int(after[r, c]) for (r, c) in discr if after[r, c] != bg)
    for color, _ in cols.most_common(4):
        src = set(map(tuple, np.argwhere(before == color)))
        dst = set(map(tuple, np.argwhere(after == color)))
        arrived = (dst - src) & discr          # new occupancy of this colour, action-contingent
        if not arrived:
            continue
        vacated = src - dst                     # where this colour left (the origin)
        fp = arrived | vacated
        if len(fp) > len(best):
            best = fp
    return best


def footprint_located(ad, k=14, radius=None):
    """Discriminative click footprint: clicking different cells changes different things; the cells that
    DIFFER by which cell I click are the self's located effect. Returns {click_cell: footprint_cells}."""
    pa = list(getattr(ad, "pointer_actions", lambda: [])())
    if not pa:
        return {}
    kind = pa[0]; ad.reset(); base = _arr(ad); bg = _bg(base)
    fg = [tuple(p) for p in np.argwhere(base != bg)]
    rng = np.random.default_rng(0)
    if len(fg) > k:
        fg = [fg[i] for i in rng.choice(len(fg), k, replace=False)]
    changes = {}
    for (r, c) in fg:
        ad.reset(); before = _arr(ad)
        try: ad.step_at(kind, int(r), int(c))
        except Exception: continue
        changes[(r, c)] = _changed(before, _arr(ad))
    if len(changes) < 2:
        return changes
    ambient = set.intersection(*changes.values())
    return {cell: (ch - ambient) for cell, ch in changes.items()}


# ---------------- INDEPENDENT ground truth (different method, so agreement is real) ------------------
def gt_translate(before, after, max_shift=8):
    """Geometric rigid-translation agent: the colour whose cells best shift by a single (dr,dc).
    GT footprint = vacated cells (old) UNION arrived cells (new). Colour+shift based -- NOT discriminative."""
    before = np.asarray(before); after = np.asarray(after)
    bg = _bg(before); best = None
    for color in np.unique(before):
        if color == bg: continue
        src = set(map(tuple, np.argwhere(before == color)))
        dst = set(map(tuple, np.argwhere(after == color)))
        if not src or not dst or src == dst: continue
        sr = np.array(sorted(src)); ds = np.array(sorted(dst))
        dr, dc = (ds.mean(0) - sr.mean(0)).round().astype(int)
        if (dr, dc) == (0, 0) or abs(dr) > max_shift or abs(dc) > max_shift: continue
        shifted = {(r + dr, c + dc) for r, c in src}
        ov = len(shifted & dst) / max(1, len(dst))
        if best is None or ov > best[1]:
            best = ((color, (dr, dc)), ov, src | shifted)
    if best is None or best[1] < 0.5:
        return set()
    return best[2]

def gt_click(before, after, click_rc, radius=4):
    """Positional GT: cells a click changes within `radius` of the clicked cell (local effect). Soft for
    place/select games whose effect lands elsewhere -- flagged in the test."""
    ch = _changed(before, after)
    r0, c0 = click_rc
    return {(r, c) for (r, c) in ch if abs(r - r0) <= radius and abs(c - c0) <= radius}
