"""proprioception.py -- Step 3: ONE self/world service, replacing the two parallel self-ID mechanisms
(v18's motion SelfModel and the composer's discriminative_agency). It produces TYPED, JUSTIFIED
COMPONENTS (gate 1c) consumed by BOTH the mover (which needs the controllable's identity to pursue) and
the composer (which needs the self to bind objectives -- fixing the controllable=None black-box gap).

Grounded in the one principle that survived every test: ACTION IS THE ONLY AGENT IDENTIFIER.
  SELF       -- the action-DISCRIMINATIVE response (differs by which action; steerable). Modality read off
                AFTER (translate / located / regional), never assumed.
  CONSTRAINT -- an action that produces NO response (a wall / illegal move; non-response is positive info).
  AUTONOMOUS -- change that happens WITHOUT my action (observed under a no-op, when one exists).
  WORLD-LAW  -- a conditional higher-order response: a residual COMPONENT, disjoint from the self, that
                reacts only in some states (the 11.321 distinct-component detector).

Every component carries TYPE + IDENTITY + EVIDENCE + CONFIDENCE -- unexplainable = uncommitted, so a
component the service cannot justify is returned as an open question, not asserted as fact.

Verified on SYNTHETIC grid-worlds (constructed from this taxonomy, NOT from any real game). The strong
self-ID is RESET-ANCHORED (compares actions from common anchors); the live no-reset path is weaker and
handled by from_buffer().
"""
import numpy as np
from collections import Counter, defaultdict
try:
    import footprint as _FP
except Exception:
    _FP = None


def _arr(ad):
    return np.asarray(ad._grid(ad._obs))

def _changed(a, b):
    return set(map(tuple, np.argwhere(np.asarray(a) != np.asarray(b))))

def _components(cells):
    cs = set(cells); seen = set(); out = []
    for st in cs:
        if st in seen:
            continue
        stack = [st]; comp = []
        while stack:
            p = stack.pop()
            if p in seen or p not in cs:
                continue
            seen.add(p); comp.append(p)
            r, c = p
            stack += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
        out.append(set(comp))
    return out


class Component:
    """A typed, justified perceived component."""
    __slots__ = ("ctype", "identity", "evidence", "confidence", "cells", "modality", "location",
                 "theory", "prediction")

    def __init__(self, ctype, identity=None, evidence="", confidence=0.0, cells=None, modality=None):
        self.ctype = ctype           # 'self' | 'constraint' | 'autonomous' | 'world-law' | 'unknown'
        self.identity = identity     # color / action / descriptor
        self.evidence = evidence     # WHY this type (the work shown)
        self.confidence = confidence
        self.cells = cells or set()
        self.modality = modality     # for 'self': translate / located / command / regional
        self.location = None         # WHERE on the board: dict(centroid, bbox, zone)
        self.theory = None           # interpreted PURPOSE (esp. autonomous: gameplay vs HUD/diagnostic)
        self.prediction = None       # a SHARP, FALSIFIABLE claim its own footprints could disprove

    def falsifiable(self):
        return bool(self.prediction)

    def justified(self):
        return bool(self.evidence) and self.confidence > 0.0

    def __repr__(self):
        return (f"Component({self.ctype}"
                + (f"/{self.modality}" if self.modality else "")
                + f", conf={self.confidence:.2f}, evidence='{self.evidence}')")


class Proprioception:
    def __init__(self):
        self.components = []
        self._noop_action = None

    # ---------- strong, reset-anchored probe (level-start understanding phase) ----------
    def probe(self, adapter, n_anchors=5, walk=3, seed=0):
        self.components = []
        self._self_start_cells = None
        self._auto_smear = set()
        rng = np.random.default_rng(seed)
        adapter.reset()
        _init = _arr(adapter)                              # fixed bg reference (initial empty substrate);
        _v, _c = np.unique(_init, return_counts=True)      # do NOT recompute per-frame -- it flips once an
        self._bg0 = int(_v[np.argmax(_c)])                 # autonomous region grows to dominate the grid
        self._H, self._W = _init.shape                     # board dims, for localization/zone reasoning
        acts = list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions())
        if not acts:
            self._probe_located(adapter)        # pure-click game (no movers) -> located self
            self._localize_all(); self._theorize(); self._attach_predictions()
            return self.components
        # per-anchor discriminative analysis (ambient = common to all actions; self = the steerable residue)
        anchors = [[]]; seq = []
        for _ in range(n_anchors - 1):
            for _ in range(walk):
                a = acts[rng.integers(len(acts))]; _, _, d, _ = adapter.step(a); seq.append(a)
                if d:
                    adapter.reset(); seq = []
            anchors.append(list(seq))
        blocked_counts = Counter(); acted_counts = Counter()
        self_cells = set(); modal_votes = Counter(); self_evidence = defaultdict(list)
        world_hits = 0; world_total = 0
        ambient_samples = []      # action-INVARIANT change per anchor -> the autonomous-evolution signal
        for ai, anc in enumerate(anchors):
            adapter.reset(); ok = True
            for pa in anc:
                _, _, dd, _ = adapter.step(pa)
                if dd:
                    ok = False; break
            if not ok:
                continue
            chs = {}
            for a in acts:
                adapter.reset()
                for pa in anc:
                    adapter.step(pa)
                bf = _arr(adapter)
                try:
                    adapter.step(a)
                except Exception:
                    continue
                chs[a] = (bf, _arr(adapter), _changed(bf, _arr(adapter)))
            if len(chs) < 2:
                continue
            ambient = set.intersection(*[c for _, _, c in chs.values()]) if chs else set()
            if ambient:
                bf0, af0, _ = next(iter(chs.values()))   # ambient is action-invariant; any action's frame shows it
                ambient_samples.append((bf0, af0, ambient))
            for a, (bf, af, ch) in chs.items():
                acted_counts[a] += 1
                if not ch:
                    blocked_counts[a] += 1
                    continue
                discr = ch - ambient
                if not discr:
                    blocked_counts[a] += 1     # only ambient moved -> this action steered nothing
                    continue
                # self: coherent translate (modality read off), else located/regional
                if _FP is not None:
                    mv = _FP.footprint_translate_causal(bf, af, discr)
                else:
                    mv = set()
                if mv:
                    self_cells |= mv; modal_votes["translate"] += 1
                    self_evidence[a].append(f"translate {len(mv)}c")
                else:
                    self_cells |= discr
                    modal_votes["located" if len(discr) <= 6 else "regional"] += 1
                    self_evidence[a].append(f"{'located' if len(discr)<=6 else 'regional'} {len(discr)}c")
                # world-law: a residual component disjoint from the self's move (conditional)
                residual = ch - mv - ambient
                if residual:
                    world_total += 1
                    for comp in _components(residual):
                        if comp and not (comp & mv):
                            world_hits += 1; break
        # ---- assemble typed, justified components ----
        self._self_smear = set(self_cells)        # discriminative self cells (excludes ambient HUD movers)
        # SELF
        if modal_votes:
            modality = modal_votes.most_common(1)[0][0]
            n_steering = sum(1 for a in acts if blocked_counts[a] < acted_counts.get(a, 0))
            conf = min(1.0, 0.4 + 0.15 * n_steering)
            ev = "; ".join(f"{getattr(a,'name',a)}:{','.join(v[:1])}" for a, v in list(self_evidence.items())[:4])
            self.components.append(Component(
                "self", identity="action-discriminative", modality=modality,
                cells=self_cells, confidence=round(conf, 2),
                evidence=f"responds differently per action (steerable), distinct from ambient [{ev}]"))
        # CONSTRAINTS (actions that consistently produced no steerable response)
        for a in acts:
            n = acted_counts.get(a, 0)
            if n >= 2 and blocked_counts[a] >= max(2, int(0.8 * n)):
                self.components.append(Component(
                    "constraint", identity=getattr(a, "name", a),
                    confidence=round(min(1.0, blocked_counts[a] / n), 2),
                    evidence=f"action produced no steerable change in {blocked_counts[a]}/{n} anchors (a wall/illegal move)"))
        # WORLD-LAW (conditional higher-order response)
        if world_total > 0 and world_hits / world_total >= 0.12:
            self.components.append(Component(
                "world-law", identity="conditional-response",
                confidence=round(min(1.0, world_hits / world_total), 2),
                evidence=f"a component disjoint from the self reacted in {world_hits}/{world_total} probed transitions (conditional on state)"))
        # AUTONOMOUS (action-INVARIANT coherent evolution NOT attributable to me; no no-op required)
        self._detect_autonomous(ambient_samples, self_cells)
        # LOCATED self: if discrete probing found no steerable self but clicks exist, probe clicks. This is
        # the CLICK modality (lp85's) -- without it the service would report controllable=None on click
        # games exactly as the old composer did.
        if self.self_component() is None:
            self._probe_located(adapter)
        self._locate_self(adapter)        # pinpoint the avatar (clean, from initial state)
        self._localize_all()              # WHERE each component sits + zone
        self._theorize()                  # interpret autonomous purpose (gameplay vs HUD/diagnostic)
        self._attach_predictions()        # every committed component must be FALSIFIABLE (else uncommitted)
        return self.components

    def _probe_located(self, adapter):
        """Click-modality self. Distinguishes a LOCATED self (effect varies by WHERE I click -- a cursor)
        from COMMAND controls (effect is consistent per control IDENTITY and position-independent -- a UI
        button that transforms the world, e.g. lp85). Command is the third localization of the one self:
        the controllable whose effect is global and not co-located with the action."""
        pa = list(adapter.pointer_actions()) if hasattr(adapter, "pointer_actions") else []
        if not pa or _FP is None:
            return
        kind = pa[0]
        try:
            adapter.reset()
        except Exception:
            return
        base = _arr(adapter); bg = getattr(self, "_bg0", 0)
        fg = [tuple(map(int, p)) for p in np.argwhere(base != bg)]
        if len(fg) < 2:
            return
        rng = np.random.default_rng(0)
        by_color = defaultdict(list)
        for cell in fg:
            by_color[int(base[cell])].append(cell)
        raw = {}
        for color, cells in by_color.items():
            pick = cells if len(cells) <= 4 else [cells[i] for i in rng.choice(len(cells), 4, replace=False)]
            for (r, c) in pick:
                try:
                    adapter.reset(); before = _arr(adapter); adapter.step_at(kind, int(r), int(c))
                    raw[(r, c)] = (color, _changed(before, _arr(adapter)))
                except Exception:
                    continue
        nonempty = {cell: v for cell, v in raw.items() if v[1]}
        if len(nonempty) < 2:
            return
        ambient = set.intersection(*[ch for _, ch in nonempty.values()])      # common to all clicks = HUD
        eff = {cell: (col, ch - ambient) for cell, (col, ch) in nonempty.items()}
        eff = {cell: v for cell, v in eff.items() if v[1]}
        if len(eff) < 2:
            return
        by_col = defaultdict(list)
        for cell, (col, ch) in eff.items():
            by_col[col].append((cell, ch))
        commands = []; variable = False
        for col, items in by_col.items():
            sigs = {frozenset(ch) for _, ch in items}
            if len(items) >= 2 and len(sigs) >= 2:
                variable = True                                    # same colour, position-DEPENDENT -> located
            elif len(sigs) == 1:
                commands.append((col, items[0][0], items[0][1], len(items)))   # consistent -> command

        if variable:                                               # LOCATED self (cursor: effect by position)
            cells = set().union(*[ch for _, ch in eff.values()])
            self.components.append(Component(
                "self", identity="located-click", modality="located", cells=cells,
                confidence=round(min(1.0, 0.4 + 0.1 * len(eff)), 2),
                evidence=f"clicking different cells produces different effects (steerable by position) across {len(eff)} clicks"))
            return
        if commands:                                               # COMMAND controls (UI buttons -> world)
            for col, cell, ch, nseen in commands:
                r0, c0 = cell
                remote = not any(abs(r - r0) + abs(c - c0) <= 2 for (r, c) in ch)
                ctrl_cells = set(by_color[col])
                comp = Component(
                    "self", identity=f"command:c{col}", modality="command", cells=ctrl_cells,
                    confidence=round(min(1.0, 0.45 + 0.1 * nseen), 2),
                    evidence=(f"clicking any colour-{col} cell triggers the SAME {len(ch)}-cell "
                              f"{'remote/global' if remote else 'local'} transform, position-independent "
                              f"(corroborated on {nseen} cell(s)) -- a control, not an avatar"))
                comp.prediction = dict(
                    kind="command", color=col, size=len(ch), remote=remote,
                    text=(f"clicking ANY colour-{col} cell ALWAYS produces this same ~{len(ch)}-cell "
                          f"transform regardless of position or state (falsified by one differing outcome)"))
                self.components.append(comp)

    def _detect_autonomous(self, ambient_samples, self_cells):
        """AUTONOMOUS = world-evolution that happens regardless of my action. The strict definition needs a
        no-op (change while I do nothing), which most turn-based games lack. The operational signature in a
        turn-based game is ACTION-INVARIANCE: the same change occurs no matter which action -- the ambient
        set (intersection of per-action changes). Two corrections matter: (1) when every action moves the
        self, the self's VACATED ORIGIN is also action-invariant and leaks into the ambient -> subtract the
        self's cells first (autonomous = action-invariant change NOT attributable to me). (2) growth
        (fluid/spread: net expansion, filled >> vacated) must be told apart from translate (gravity/fall:
        filled ~= vacated, region moves). Small/scattered/static residue stays unasserted (incidental HUD).
        No no-op required."""
        if not ambient_samples:
            return
        n = 0; translate_votes = 0; growth_votes = 0; decay_votes = 0; total = 0
        auto_cells = set(); auto_repr = set()
        for bf, af, amb in ambient_samples:
            amb2 = amb - self_cells                       # remove the self's action-invariant origin leak
            if len(amb2) < 2:
                continue
            n += 1; total += len(amb2); auto_cells |= amb2
            if not auto_repr:
                auto_repr = set(amb2)                       # instantaneous footprint (one frame) for LOCALIZATION
            bf = np.asarray(bf); af = np.asarray(af)
            bg = getattr(self, "_bg0", 0)                  # fixed reference, not per-frame (avoids flip)
            filled = sum(1 for (r, cc) in amb2 if 0 <= r < af.shape[0] and 0 <= cc < af.shape[1]
                         and af[r, cc] != bg and bf[r, cc] == bg)
            vacated = sum(1 for (r, cc) in amb2 if 0 <= r < af.shape[0] and 0 <= cc < af.shape[1]
                          and af[r, cc] == bg and bf[r, cc] != bg)
            if filled >= 2 and filled > vacated + 1:       # net expansion -> growth (fluid/spread)
                growth_votes += 1
            elif vacated >= 2 and vacated > filled + 1:     # net contraction -> decay (depleting timer/bar)
                decay_votes += 1
            else:                                          # size-preserving move -> translate (gravity/fall)
                mv = _FP.footprint_translate_causal(bf, af, amb2) if _FP is not None else set()
                if mv and len(mv) >= 2:
                    translate_votes += 1
        if n == 0:
            return
        self._auto_smear = auto_cells                      # full trajectory -> confinement test in _theorize
        avg = total / n
        if growth_votes / n >= 0.5:
            self.components.append(Component(
                "autonomous", identity="world-evolution(growth)", cells=auto_repr,
                confidence=round(min(1.0, 0.4 + 0.1 * n), 2),
                evidence=(f"an action-INVARIANT region (not attributable to me) grew in {growth_votes}/{n} "
                          f"probes -- fluid/growth-like, no no-op needed")))
        elif decay_votes / n >= 0.5:
            self.components.append(Component(
                "autonomous", identity="world-evolution(decay)", cells=auto_repr,
                confidence=round(min(1.0, 0.4 + 0.1 * n), 2),
                evidence=(f"an action-INVARIANT region (not attributable to me) shrank in {decay_votes}/{n} "
                          f"probes -- depleting timer/bar-like, no no-op needed")))
        elif translate_votes / n >= 0.5 and avg >= 2:
            self.components.append(Component(
                "autonomous", identity="world-evolution(translate)", modality="translate", cells=auto_repr,
                confidence=round(min(1.0, 0.4 + 0.1 * n), 2),
                evidence=(f"an action-INVARIANT region (not attributable to me) translated coherently in "
                          f"{translate_votes}/{n} probes -- gravity/fall-like, no no-op needed")))

    # ---------- live, weaker path (no reset) ----------
    def from_buffer(self, transitions):
        """Weaker live typing from observed (before, action, after) -- per-transition motion only."""
        self.components = []
        if _FP is None or not transitions:
            return self.components
        hits = []
        for bf, a, af in transitions:
            ch = _changed(bf, af)
            if not ch:
                continue
            mv = _FP.footprint_translate_causal(np.asarray(bf), np.asarray(af), ch)
            if 1 <= len(mv) <= 24:
                hits.append(mv)
        if len(hits) >= 2:
            sizes = [len(h) for h in hits]
            if max(sizes) - min(sizes) <= max(4, int(0.5 * np.median(sizes))):
                self.components.append(Component(
                    "self", identity="action-discriminative", modality="translate",
                    cells=set().union(*hits), confidence=0.45,
                    evidence=f"a consistently-sized mover recurred across {len(hits)} live transitions (no-reset, weaker)"))
        self._attach_predictions()        # the live self carries the SAME falsifiable self_translate prediction
        return self.components

    # ---------- localization + interpretation (WHERE + WHAT-FOR) ----------
    def _zone(self, cells):
        """Classify where a cell-set sits on the board: corner / edge-margin / center / spanning."""
        if not cells:
            return "unknown"
        H = getattr(self, "_H", 64); W = getattr(self, "_W", 64)
        rs = [r for r, _ in cells]; cs = [c for _, c in cells]
        r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
        span_r = (r1 - r0 + 1) / H; span_c = (c1 - c0 + 1) / W
        if span_r > 0.7 or span_c > 0.7:
            return "spanning"
        m = 0.18
        edges = sum([r0 < H * m, r1 > H * (1 - m), c0 < W * m, c1 > W * (1 - m)])
        if edges >= 2 and span_r < 0.4 and span_c < 0.4:
            return "corner"
        if edges >= 1 and (span_r < 0.35 or span_c < 0.35):
            return "edge/margin"
        return "center"

    def _loc(self, cells):
        if not cells:
            return None
        rs = [r for r, _ in cells]; cs = [c for _, c in cells]
        return dict(centroid=(round(sum(rs) / len(rs), 1), round(sum(cs) / len(cs), 1)),
                    bbox=(min(rs), min(cs), max(rs), max(cs)), zone=self._zone(cells), size=len(cells))

    def _locate_self(self, adapter):
        """Pinpoint the avatar cleanly from the initial state (self_cells is a movement smear)."""
        s = self.self_component()
        if s is None or s.modality not in (None, "translate"):
            return
        try:
            adapter.reset()
        except Exception:
            return
        acts = list(adapter.discrete_actions() if hasattr(adapter, "discrete_actions") else adapter.actions())
        bg = getattr(self, "_bg0", 0); cands = []
        for a in acts[:6]:
            try:
                adapter.reset(); bf = _arr(adapter); adapter.step(a); af = _arr(adapter)
            except Exception:
                continue
            ch = _changed(bf, af)
            mv = _FP.footprint_translate_causal(bf, af, ch) if _FP is not None else set()
            smear = getattr(self, "_self_smear", None)
            if smear:
                mv = mv & smear                    # keep only the discriminative self, not an ambient HUD mover
            src = {(r, c) for (r, c) in mv if bf[r, c] != bg and af[r, c] == bg}   # avatar's pre-move cells
            if src:
                cands.append(src)
        if cands:
            self._self_start_cells = min(cands, key=len)   # tightest coherent source ~ avatar at start

    def _localize_all(self):
        for c in self.components:
            cells = getattr(self, "_self_start_cells", None) if c.ctype == "self" else None
            cells = cells or c.cells
            if cells:
                c.location = self._loc(cells)

    def _theorize(self):
        """Interpret each autonomous component's PURPOSE (the step beyond labelling): active gameplay vs a
        HUD/diagnostic readout -- with how to USE it and how to CONFIRM the guess. The discriminator is
        CONFINEMENT: a readout's whole trajectory hugs the margins; a gameplay element traverses the central
        field. Game-agnostic: keyed on where the motion lives, never on any specific game's mechanics."""
        H = getattr(self, "_H", 64); W = getattr(self, "_W", 64); m = 0.18
        smear = getattr(self, "_auto_smear", set())
        if smear:
            periph = sum(1 for (r, c) in smear
                         if r < H * m or r >= H * (1 - m) or c < W * m or c >= W * (1 - m))
            frac_periph = periph / len(smear)
        else:
            frac_periph = 0.0
        for c in self.components:
            if c.ctype != "autonomous":
                continue
            if frac_periph >= 0.85:                         # trajectory stays in the margins -> readout
                c.theory = ("its motion stays confined to the board MARGINS -> probably a HUD/DIAGNOSTIC "
                            "readout (turn/step/timer/score gauge), not a hazard. USE IT: read it as a "
                            "game-state gauge (how much time/progress remains). CONFIRM: it never collides "
                            "with or gates the self; if objective-progress changes its rate, it is a clock.")
            else:                                           # motion enters the play field -> gameplay
                c.theory = ("its motion TRAVERSES the central play field -> probably an ACTIVE gameplay "
                            "element (hazard / NPC / clock-driven mechanic) to model. USE IT: predict its "
                            "next state and route around or exploit it. CONFIRM: does it collide with / "
                            "gate the self, or change on contact?")

    def _attach_predictions(self):
        """Every committed component must carry a SHARP, FALSIFIABLE prediction -- one its own future
        footprints could disprove. unfalsifiable = uncommitted. (The command modality already sets a
        structured prediction in _probe_located; fill in the rest.)"""
        for c in self.components:
            if c.prediction is not None:
                continue
            if c.ctype == "self" and c.modality == "translate":
                c.prediction = dict(kind="self_translate", text=(
                    "a movement action displaces the controllable cluster; a movement press that never "
                    "moves it (outside a known constraint) falsifies this"))
            elif c.ctype == "self" and c.modality == "located":
                c.prediction = dict(kind="self_located", text=(
                    "clicking changes state, varying by where I click; a click that never changes anything "
                    "where one is expected falsifies this"))
            elif c.ctype == "constraint":
                c.prediction = dict(kind="constraint", action=c.identity, text=(
                    f"{c.identity} produces no change from these states; one state where it does change "
                    f"falsifies the constraint"))
            elif c.ctype == "autonomous":
                c.prediction = dict(kind="autonomous", cells=set(c.cells), text=(
                    "this region keeps changing on its own regardless of my action; a stretch where it "
                    "holds perfectly still under varied actions falsifies its autonomy"))
            elif c.ctype == "world-law":
                c.prediction = dict(kind="world_law", text=(
                    "a component disjoint from the self responds only in some states; falsified if it never "
                    "responds again under the conditions that triggered it"))

    # ---------- consumers ----------
    def self_component(self):
        for c in self.components:
            if c.ctype == "self" and c.justified():
                return c
        return None

    def controllable_for_mover(self):
        """The mover needs identity/cells to pursue. None if the self is not justified (honest)."""
        s = self.self_component()
        return None if s is None else dict(cells=s.cells, modality=s.modality, confidence=s.confidence)

    def self_for_composer(self):
        """The composer needs the self to bind objectives. Returns a justification string + modality, or
        None (-> the kernel treats the objective as uncommittable: unexplainable=uncommitted)."""
        s = self.self_component()
        if s is None:
            return None
        return dict(modality=s.modality, justification=s.evidence, confidence=s.confidence)

    def explain(self):
        """Gate 1c + proctor articulation: narrate the typed components, WHERE they are, and (for
        autonomous) what they are FOR."""
        if not self.components:
            return "proprioception: no components justified yet (open question, not a fact)"
        lines = []
        for c in self.components:
            head = c.ctype.upper() + (f"({c.modality})" if c.modality else "")
            loc = ""
            if c.location:
                loc = f" @ {c.location['zone']} centroid{c.location['centroid']} bbox{c.location['bbox']}"
            lines.append(f"{head} [{c.confidence:.2f}]{loc}: {c.evidence}")
            if c.theory:
                lines.append(f"    THEORY: {c.theory}")
        return "proprioception:\n  " + "\n  ".join(lines)
