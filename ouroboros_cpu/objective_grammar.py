# objective_grammar.py — a UNIVERSAL PRIME BASIS for ARC-AGI-3 objectives (NSM-seeded, Kant-organized).
#
# THE ESCAPE FROM THE OVERFIT-VS-RIGID DILEMMA:
#   Per-game modeling overfits (memorizes one game's answer). A fixed solver library imposes the wrong
#   ontology (also memorizes answers, just earlier). Both fail because they store ANSWERS. The escape is
#   to store a BASIS + a SEARCH PROCEDURE and never an answer: a small universal alphabet of primes, plus
#   the procedure for composing and TESTING them against the world. Each game's objective is a COMPOSITION
#   over the primes, RE-DERIVED at runtime by interaction. You cannot overfit (no game-specific rule is
#   stored); you can transfer (the alphabet is universal, and whether it spans is MEASURABLE on held-out
#   games). Memorizing the sentence is overfitting; knowing the words + grammar and writing a fresh
#   sentence per game is generalization.
#
# WHY NSM + KANT:
#   NSM (Natural Semantic Metalanguage) is an empirically-grounded universal basis: ~65 semantic primes
#   that recur across all human languages. They map onto ARC-3 dynamics directly. Kant's categories give
#   the ORGANIZING AXES that partition the primes: Quantity, Quality, Relation, Modality. NSM supplies the
#   alphabet; Kant tells you the axes it lives on.

# ---------------------------------------------------------------------------
# THE PRIME BASIS  (Kant category -> NSM-style primes -> ARC-3 dynamics meaning)
# ---------------------------------------------------------------------------
PRIMES = {
    "Quantity": ["ALL", "SOME", "ONE", "NONE"],          # how many objects must satisfy the relation
    "Quality":  ["SAME", "OTHER", "NOT"],                # matching / difference / negation (constraint)
    "Relation": ["BE_AT", "TOUCH", "BECOME", "BECAUSE"], # position / contact / change / causation
    "Modality": ["CAN", "EXIST"],                        # controllability (affordance) / existence
    # Spatial sub-primes (refine BE_AT when needed): ABOVE BELOW NEAR INSIDE
    # Temporal sub-primes (sequence objectives):     BEFORE AFTER
}
# OBJECT ROLES are discovered at runtime, not stored per game:
#   CONTROLLABLE (the cursor/player: the object whose motion obeys actions, §11.157),
#   TARGET (what the objective is about), HAZARD (what NOT must avoid).

# ---------------------------------------------------------------------------
# SEED objectives — the ones used to CONSTRUCT the basis (so they trivially fit)
# ---------------------------------------------------------------------------
SEED = {
    # CORRECTED against ground-truth concepts (the earlier recon'd predicates were WRONG; this is the
    # "fix the wrong priors" pass). Where a corrected concept does NOT cleanly decompose into the current
    # basis, it is annotated [GAP] -- that is a discovery signal, not something to paper over.
    "ar25 fitting+symmetry": "ALL(p in PIECE: BE_AT(p, fit_slot(p)))",
    #   was "cover-all / BECOME". TRUE concept = Object Fitting + Symmetry: place pieces into slots whose
    #   positions are fixed by a MIRROR relation. Primes: ALL, BE_AT. [GAP] the mirror/symmetry that
    #   determines fit_slot is a RELATION the projector must read from the scene, not an objective prime.
    "cn04 tip-matching":     "ALL(s in SHAPE: SAME(tip(s), target_tip(s)))",
    #   was "arrange / BE_AT". TRUE concept = Tip Matching: align the TIP/endpoint of each shape to a target.
    #   Primes: ALL, SAME. [GAP] "tip/endpoint" is a sub-object feature the perception layer must expose.
    "collect":               "NONE(t in TARGET: EXIST(t))  BECAUSE DO",            # consume every target (generic; OK)
    "bp35 gravity":          "ALL(o in OBJECT: BE_AT(o, rest_target(o)))",
    #   was "land-on-gem avoid-spike / TOUCH + NOT" -- WRONG. TRUE concept = Gravity Manipulation: the agent
    #   changes the gravity vector; objects fall and settle. Primes: ALL, BE_AT. [GAP] the load-bearing part is
    #   a DYNAMICS affordance (gravity direction) + DELAYED settle, NOT an objective prime. Belongs to the
    #   affordance/dynamics model, read after settle (the epigenetic delayed-attribution rule).
}

# ---------------------------------------------------------------------------
# HELD-OUT objectives — NOT used to build the basis. Test: do they compose from EXISTING primes?
# (Recon'd from DEV win-predicates; the STRONG universality test is the sealed set, reserved.)
# ---------------------------------------------------------------------------
HELDOUT = {
    "tu93 maze":     "ALL(m in MOVER: SOME(e in EXIT: BE_AT(m, e)))",              # maze routing to exit (OK)
    "re86 sticks+buttons": "ALL(r in TARGET_REGION: SAME(r, canvas)) AND ALL(b in BUTTON: pressed(b))",
    #   was "assemble" only; TRUE concept adds an ACTIVATION sub-goal (buttons). Primes: ALL, SAME + pressed().
    # --- NEW: entries that EXERCISE declared-but-unused primes / expose real gaps ---
    "g50t past-manip":  "ALL(s in STATE: SAME(s, BEFORE(s, action)))",
    #   Past Manipulation (temporal). EXERCISES the BEFORE/AFTER temporal sub-primes that were declared at
    #   line 28 and NEVER used by any seed/heldout. The "ghost" is a past-state echo, not an enemy.
    "lp85 conveyor":    "ALL(i in ITEM: SOME(t: BE_AT(i, grab) AFTER pass(i, grab)))",
    #   Revolving sushi bar: intercept an item AS it passes a fixed grab-point. EXERCISES temporal AFTER +
    #   a fixed interaction locus. (This is the one win, and it needs temporal primes the basis never ran.)
    "tr87 rosetta":     "ALL(x in SYM_A: SAME(meaning(x), key(x)))   # key: SYM_A <-> SYM_B mapping",
    #   Hieroglyphic encryption / rosetta. [GAP-STRONG] requires a learned CORRESPONDENCE/MAPPING between two
    #   symbol sets -- a construct the basis lacks. This is a genuine candidate for basis GROWTH (a missing
    #   universal word: MAP/CORRESPOND), surfaced by correcting the prior. Do NOT patch game-specifically.
}
# RESULT (CORRECTED, honest): the earlier "both held-out decompose into existing primes => basis spans"
# conclusion was built partly on MISCHARACTERIZED priors (bp35 especially). Re-examined against ground truth:
#   tu93 (maze)      -> ALL, SOME, BE_AT                       : composes. OK.
#   re86 (sticks+btn)-> ALL, SAME, + an ACTIVATION predicate   : composes IF pressed() is exposed.
#   g50t (past)      -> needs BEFORE/AFTER (declared, NEVER exercised) : composes only once temporal fires.
#   lp85 (conveyor)  -> needs AFTER + a fixed locus            : same -- temporal must fire.
#   tr87 (rosetta)   -> needs MAP/CORRESPOND                   : DOES NOT compose. A genuine missing word.
# => The basis spans the SPATIAL/QUANTITY/QUALITY games but (a) never exercised its own temporal primes and
#    (b) is missing a correspondence/mapping word for the rosetta class. The recurring deep form holds for the
#    spatial games -- QUANTIFIER(objects: RELATION(object, target)) -- but is NOT universal across the set.
#    The fix is NOT new game-specific primitives; it is (1) make the PROJECTION actually fire temporal +
#    relational primes from the visual scene (see visual_projection.py), and (2) treat MAP as a growth
#    candidate per the discovery rule below.

# ---------------------------------------------------------------------------
# THE SEARCH PROCEDURE (what makes this a method, not a library) + OVERFIT GUARD
# ---------------------------------------------------------------------------
# 1. Fix the universal basis above. NEVER add a game-specific primitive.
# 2. Per game: SEARCH compositions of primes that explain the observed objective signal; CONFIRM by
#    interaction (the recon->reset->exploit loop, §11.159). The composition is re-derived, never stored.
#    The search is exponential; a recognition prior over compositions (the objective-atlas, parallel to
#    the dynamics-atlas) prunes it exponential->near-constant (§11.155).
# 3. TRANSFER-TEST the basis+search on held-out games (fresh, sealed). Dev-only success = overfit signal.
# 4. GROW the basis ONLY when a held-out game CANNOT be composed, and ONLY with a UNIVERSAL prime (never
#    a game-specific patch). A composition failure is a DISCOVERY signal: a missing universal word found.
#    The basis is thus itself discovered by the discovery->recognition->transfer cycle, one level up.


# ===========================================================================================
# LIVE GRAMMAR API  (added this session)  --  the grammar is no longer doc-only.
# The composer/projection import this so they reason IN the basis and can EXPLAIN any predicate
# they use in words + grammar + prime-decomposition. Single source of truth; drift is asserted.
# ===========================================================================================
from dataclasses import dataclass as _dc

# flat set of every legal prime (incl. spatial + temporal sub-primes declared in comments above)
ALL_PRIMES = (set().union(*[set(v) for v in PRIMES.values()])
              | {"ABOVE", "BELOW", "NEAR", "INSIDE", "BEFORE", "AFTER"})

@_dc(frozen=True)
class Predicate:
    name: str          # the label the runtime/projection use (may be a composite shorthand)
    gloss: str         # WORDS: what it means in plain language
    primes: tuple      # GRAMMAR: decomposition into basis primes (every element must be in ALL_PRIMES)
    deep_form: str     # the QUANTIFIER(objects: RELATION(object,target)) template

# Every composite the runtime emits, decomposed back into the basis. THIS is the interpreter that
# was missing: it lets the composer say COVER *and* explain COVER = ALL(r: BECOME(r, fill)).
PREDICATES = {
    "BE_AT":      Predicate("BE_AT",      "be located at a target position",            ("BE_AT",),               "BE_AT(o, target)"),
    "TOUCH":      Predicate("TOUCH",      "make contact with a target",                 ("TOUCH",),               "TOUCH(o, target)"),
    "BECOME":     Predicate("BECOME",     "change to a target state/color",             ("BECOME",),              "BECOME(o, state)"),
    "SAME":       Predicate("SAME",       "match the target (become equal to it)",      ("SAME",),                "SAME(o, target)"),
    "SAME/FIT":   Predicate("SAME/FIT",   "fit/complete so the configuration is mirror-symmetric",
                                                                                        ("ALL", "SAME", "BE_AT"), "ALL(p in PIECE: BE_AT(p, mirror_slot(p)))"),
    "COVER":      Predicate("COVER",      "fill every enclosed region to the fill color",
                                                                                        ("ALL", "INSIDE", "BECOME"), "ALL(r in REGION: BECOME(r, fill))"),
    "BECOME/COVER": Predicate("BECOME/COVER", "select a color, then make regions become it to match a target",
                                                                                        ("ALL", "BECOME", "SAME"), "ALL(r in REGION: BECOME(r, SELECTED) ) s.t. SAME(canvas, target)"),
    "NONE.EXIST": Predicate("NONE.EXIST", "make every collectible cease to exist",      ("NONE", "EXIST"),        "NONE(t in TARGET: EXIST(t))"),
    "BE_AT@locus":Predicate("BE_AT@locus","be at a fixed locus when the moving item arrives there",
                                                                                        ("BE_AT", "AFTER"),       "SOME(t: BE_AT(item, locus) AFTER pass(item, locus))"),
    # perception-layer predicates (wired this session)
    "REACH":      Predicate("REACH",      "route a mover through free space to an exit (maze)",
                                                                                        ("ALL", "SOME", "BE_AT"), "ALL(m in MOVER: SOME(e in EXIT: BE_AT(m, e)))"),
    "MATCH_GOAL": Predicate("MATCH_GOAL", "make the play area match the shown goal template",
                                                                                        ("ALL", "SAME"),          "ALL(r in REGION: SAME(r, goal_template(r)))"),
    "REPLAY":     Predicate("REPLAY",     "make a state match a past state (manipulate the past)",
                                                                                        ("SAME", "BEFORE"),       "ALL(s in STATE: SAME(s, BEFORE(s, action)))"),
}

# growth candidate surfaced by tr87 (rosetta) -- declared but NOT yet a basis prime. Do not patch per-game.
GROWTH_CANDIDATES = {"MAP": "a learned correspondence SYM_A <-> SYM_B; needed by tr87, absent from the basis"}

def validate(name: str) -> bool:
    """Is `name` a registered predicate whose decomposition lies entirely in the prime basis?"""
    p = PREDICATES.get(name)
    return bool(p) and all(q in ALL_PRIMES for q in p.primes)

def explain(name: str) -> dict:
    """Return the composer's self-explanation of a predicate: WORDS + GRAMMAR + PRIMES."""
    p = PREDICATES.get(name)
    if not p:
        return {"name": name, "words": "(unknown predicate -- not in basis)", "grammar": None,
                "primes": (), "in_basis": False}
    return {"name": p.name, "words": p.gloss, "grammar": p.deep_form,
            "primes": p.primes, "in_basis": validate(name)}

def decompose(name: str) -> tuple:
    p = PREDICATES.get(name)
    return p.primes if p else ()

def relation_vocabulary() -> set:
    """The set of predicate labels the runtime may emit -- for the abductor to source from (one truth)."""
    return set(PREDICATES.keys())

# self-check at import: every predicate decomposes into the basis (catches drift immediately)
for _n, _p in PREDICATES.items():
    assert all(_q in ALL_PRIMES for _q in _p.primes), f"grammar drift: {_n} uses non-basis prime in {_p.primes}"


# ===========================================================================================
# EXPANDED PRIME BASIS  --  full NSM TIME + SPACE primes (added this session, per Isaiah).
# The grammar previously carried only ABOVE/BELOW/NEAR/INSIDE + BEFORE/AFTER. NSM decomposes time
# and space far finer; molecules below are built from THESE, not from ad-hoc concepts.
# ===========================================================================================
TIME_PRIMES  = {"WHEN", "TIME", "NOW", "BEFORE", "AFTER", "A_LONG_TIME", "A_SHORT_TIME", "FOR_SOME_TIME", "MOMENT"}
SPACE_PRIMES = {"WHERE", "PLACE", "HERE", "ABOVE", "BELOW", "FAR", "NEAR", "SIDE", "INSIDE"}
ALL_PRIMES |= TIME_PRIMES | SPACE_PRIMES

# Growth candidates: universal words NOT yet in the basis that some molecules need. Per the discovery
# rule, these are added as UNIVERSAL primes when a held-out game cannot compose without them -- never as
# game-specific patches. Flagged here so molecules can reference them honestly.
GROWTH_CANDIDATES.update({
    "MAP":  "a learned correspondence SYM_A <-> SYM_B (tr87 rosetta)",
    "MORE": "increase in quantity/extent (vc33 volume, sk48/r11l extension)",
    "LESS": "decrease in quantity/extent (vc33 volume)",
})
_RESOLVABLE = ALL_PRIMES | set(GROWTH_CANDIDATES)

# ===========================================================================================
# SEMANTIC MOLECULES  --  the 'cores for steering'. Mid-level concepts each composed of primes (or of
# other molecules), gleaned from the public-set concepts. The system reaches for a molecule FIRST; only
# if a needed concept is absent does it (a) composite from molecules or (b) invent from base primes.
# Every molecule's decomposition must lie in primes | molecules | growth-candidates (asserted at import).
# (ls20's concept is deliberately NOT represented here, per the standing constraint.)
# ===========================================================================================
@_dc(frozen=True)
class Molecule:
    name: str
    gloss: str
    parts: tuple        # primes and/or other molecule names it composes
    deep_form: str
    games: tuple = ()   # public games whose concept motivates it (evidence, not a lookup table)

MOLECULES = {
    # --- TIME family (built from the NSM time primes) ---
    "TIME":     Molecule("TIME", "a temporal frame: events ordered around now",
                         ("WHEN", "NOW", "BEFORE", "AFTER"), "order(events) by BEFORE/AFTER around NOW"),
    "PAST":     Molecule("PAST", "something that happened before now",
                         ("BEFORE", "NOW"), "BEFORE(NOW)"),
    "FUTURE":   Molecule("FUTURE", "something that will happen after now",
                         ("AFTER", "NOW"), "AFTER(NOW)"),
    "REPLAY":   Molecule("REPLAY", "make a state match a past state (manipulate the past)",
                         ("SAME", "BEFORE"), "ALL(s in STATE: SAME(s, BEFORE(s)))", ("g50t",)),
    "DURATION": Molecule("DURATION", "how long something lasts / a step-or-time budget",
                         ("FOR_SOME_TIME", "A_LONG_TIME", "A_SHORT_TIME"), "lasts FOR_SOME_TIME"),
    # --- MIRROR / SYMMETRY ---
    "MIRROR":   Molecule("MIRROR", "one thing is the reflection of another across an axis",
                         ("SAME", "OTHER", "SIDE"), "SAME(A, reflect_across(SIDE, B))", ("ar25", "m0r0")),
    "SYMMETRY": Molecule("SYMMETRY", "every part mirrors across an axis",
                         ("ALL", "MIRROR"), "ALL(part: MIRROR(part))", ("ar25",)),
    "COUPLED":  Molecule("COUPLED", "two agents move as mirror images of one control",
                         ("MIRROR", "BECAUSE", "BE_AT"), "BE_AT(b, reflect(a)) BECAUSE move(a)", ("m0r0",)),
    # --- SPATIAL placement ---
    "CONTAIN_FIT": Molecule("CONTAIN_FIT", "place/fit a piece inside a slot",
                         ("INSIDE", "BE_AT"), "BE_AT(piece, slot) & INSIDE(slot, frame)", ("ar25", "cd82", "cn04")),
    "REACH":    Molecule("REACH", "a goal is reachable through connected free space",
                         ("CAN", "BE_AT", "NEAR"), "CAN(BE_AT(agent, goal)) via NEAR-chain", ("tu93", "dc22", "wa30")),
    # --- PHYSICS / DYNAMICS ---
    "GRAVITY":  Molecule("GRAVITY", "objects settle in a force direction over time",
                         ("AFTER", "BELOW", "BE_AT", "BECOME"), "AFTER(act): ALL(o: BE_AT(o, farthest_BELOW(o)))", ("bp35",)),
    "FLOW":     Molecule("FLOW", "a substance propagates to neighbouring cells over time",
                         ("AFTER", "NEAR", "BECOME", "TOUCH"), "AFTER: ALL(c NEAR src: BECOME(c, fluid))", ("sp80",)),
    "CONVEYOR": Molecule("CONVEYOR", "items move along a repeating path/loop each step",
                         ("AFTER", "BE_AT", "BEFORE"), "BE_AT(i, pos) AFTER BE_AT(i, prev)  (cyclic)", ("lp85",)),
    "INTERCEPT":Molecule("INTERCEPT", "be at a fixed locus at the moment a moving item arrives",
                         ("BE_AT", "AFTER", "MOMENT"), "BE_AT(grab, locus) at MOMENT(item AT locus)", ("lp85",)),
    "PUSH":     Molecule("PUSH", "an agent moves an object by pushing into it",
                         ("TOUCH", "BECAUSE", "BE_AT", "BECOME"), "TOUCH(agent, o) BECAUSE BECOME(BE_AT(o, o+dir))", ("ka59", "wa30")),
    "TRANSPORT":Molecule("TRANSPORT", "deliver a non-agent object to a target location",
                         ("BE_AT", "BECAUSE", "PUSH"), "BE_AT(box, target) BECAUSE PUSH(box)", ("wa30", "dc22")),
    # --- CYCLE: general 'dial to a target' -- a control steps a target ATTRIBUTE through a repeating
    # set of states until it matches a goal state. Domain-agnostic (a counter, a rotator, a colour dial,
    # a state toggle): the CONTROL and the ATTRIBUTE and the GOAL are all discovered, never named here.
    "CYCLE":    Molecule("CYCLE", "a control steps a target's attribute forward through a repeating set toward a goal state",
                         ("BECAUSE", "AFTER", "BECOME", "SAME"),
                         "BECAUSE(act on control): AFTER: BECOME(attr, NEXT(attr)) [cyclic] -> drive until SAME(attr, goal)", ()),
    "EXTEND":   Molecule("EXTEND", "lengthen an object by adding adjacent cells",
                         ("BECOME", "NEAR", "MORE"), "BECOME(obj, obj + NEAR cell)  [needs MORE]", ("r11l", "sk48", "s5i5")),
    "MIX":      Molecule("MIX", "combine two objects into a new one",
                         ("BECOME", "OTHER", "SAME"), "BECOME({a,b}, c = combine(a,b))", ("su15",)),
    "ACCUMULATE":Molecule("ACCUMULATE", "drive a quantity up or down to a target level",
                         ("BECOME", "MORE", "LESS", "SAME"), "BECOME(level, target)  [needs MORE/LESS]", ("vc33",)),
    # --- MATCHING / DECODING ---
    "MATCH":    Molecule("MATCH", "make/realise sameness between objects or features",
                         ("SAME",), "SAME(a, b)", ("cn04", "sb26")),
    "MAP_DECODE":Molecule("MAP_DECODE", "decode via a learned symbol-to-symbol correspondence",
                         ("SAME", "MAP"), "ALL(x: SAME(meaning(x), MAP(x)))  [needs MAP]", ("tr87",)),
    # --- AFFORDANCE / CONTROL ---
    "ACTIVATE": Molecule("ACTIVATE", "trigger/toggle a target state by acting on a control",
                         ("TOUCH", "BECAUSE", "BECOME", "CAN"), "TOUCH(agent, button) BECAUSE BECOME(target, active)", ("ft09", "re86")),
    "COMMAND":  Molecule("COMMAND", "issue a command that takes effect elsewhere/later (indirection)",
                         ("CAN", "BECAUSE", "AFTER"), "issue(cmd) BECAUSE AFTER: effect_elsewhere", ("sc25", "tn36")),
    "PAINT":    Molecule("PAINT", "set regions to a selected value to match a target",
                         ("ALL", "BECOME", "SAME"), "ALL(r: BECOME(r, SELECTED)) s.t. SAME(canvas, target)", ("cd82",)),
    # --- ASSEMBLY / SHAPE-LINKER (select + rotate pieces so matching tips touch and overlap) ---
    "ASSEMBLY": Molecule("ASSEMBLY", "rotate/move rigid pieces so their matching extremities (tips) touch and link",
                         ("ALL", "BECOME", "SAME", "TOUCH"),
                         "ALL(p in PIECES: TOUCH(p.tip, NEXT(p).tip)) & SAME(p.tip_colour, NEXT(p).tip_colour)",
                         ("cn04",)),
    # --- REDUCTION / COLLECTION ---
    "JUMP_CAPTURE":Molecule("JUMP_CAPTURE", "move a piece over another to remove it (peg solitaire)",
                         ("BE_AT", "NONE", "EXIST", "BECAUSE"), "BE_AT(p, over(o)) BECAUSE NONE(EXIST(o))", ("lf52",)),
    "COLLECT":  Molecule("COLLECT", "remove every item of a kind",
                         ("NONE", "EXIST"), "NONE(t: EXIST(t))"),
}

def _decompose_molecule(name, _seen=None):
    """Transitively reduce a molecule to its base primes (+ any growth candidates it needs)."""
    _seen = _seen or set()
    if name in _seen:
        return set()
    _seen.add(name)
    if name in ALL_PRIMES or name in GROWTH_CANDIDATES:
        return {name}
    m = MOLECULES.get(name)
    if not m:
        return set()
    out = set()
    for p in m.parts:
        out |= _decompose_molecule(p, _seen)
    return out

def explain_molecule(name):
    m = MOLECULES.get(name)
    if not m:
        return {"name": name, "words": "(unknown molecule)", "primes": (), "known": False}
    primes = sorted(_decompose_molecule(name))
    needs = [p for p in primes if p in GROWTH_CANDIDATES]
    return {"name": m.name, "words": m.gloss, "deep_form": m.deep_form,
            "parts": m.parts, "primes": tuple(primes), "needs_growth": needs,
            "games": m.games, "known": True}

def resolve(concept):
    """Resolve a needed concept to grammar. Strategy:
       1) LIBRARY  -- it's a known molecule -> return its prime decomposition;
       2) COMPOSITE-- its name contains known molecule keywords -> combine them (e.g. 'TIME'+'X');
       3) INVENT   -- otherwise fall back to base primes and flag NEEDS_INVENTION."""
    key = concept.strip().upper().replace(" ", "_")
    if key in MOLECULES:
        return {"mode": "library", **explain_molecule(key)}
    hits = [m for m in MOLECULES if m in key]
    if hits:
        primes = sorted(set().union(*[_decompose_molecule(m) for m in hits]))
        return {"mode": "composite", "from": hits, "primes": tuple(primes),
                "words": " + ".join(MOLECULES[m].gloss for m in hits)}
    return {"mode": "invent", "primes_available": sorted(ALL_PRIMES),
            "note": "no molecule matched; compose from base primes (discovery signal -- may need a new universal prime)"}

# self-check at import: every molecule decomposes into primes | molecules | growth-candidates
for _mn, _m in MOLECULES.items():
    for _part in _m.parts:
        assert _part in _RESOLVABLE or _part in MOLECULES, f"molecule {_mn} references unknown part {_part}"


# ===========================================================================================
# PERCEPTUAL MOLECULE TIER  --  the "Helen Keller" layer (added this session).
# An agent waking to its senses must turn raw perception into meaningful chunks BEFORE it can hold
# game concepts. Its senses are: COLOUR+POSITION+SHAPE (static frame), FRAME-DELTAS (motion / appear /
# disappear), and ACTION-EFFECTS. So we add the molecules that have a GRID referent and SKIP the ones
# that do not (see CURATION_NOTE). These sit BELOW the concept molecules (GRAVITY, CONVEYOR, ...), which
# are built from them. They are a reference LIBRARY (resolve/compose), NOT active detectors -- wiring a
# specific one into the projection is a separate, regression-gated step.
# ===========================================================================================
# more standard NSM primes the perceptual layer needs (action/event, possession, descriptors, similarity)
_NEW_PRIMES = {"DO", "HAPPEN", "MOVE", "HAVE", "PART", "KIND", "LIKE", "BIG", "SMALL", "MUCH_MANY", "MORE", "VERY"}
ALL_PRIMES |= _NEW_PRIMES
GROWTH_CANDIDATES.pop("MORE", None)
ALL_PRIMES |= {"MAP"}                        # PROMOTED: rosetta correspondence word (tr87), validated legend-parse on real board
GROWTH_CANDIDATES.pop("MAP", None)           # MAP is now a real prime -> out of growth
          # MORE is a real NSM prime -> promoted out of growth
_RESOLVABLE = ALL_PRIMES | set(GROWTH_CANDIDATES)

CURATION_NOTE = (
    "Grounded in the agent's actual sensorium (colour+position+shape, frame-deltas, action-effects). "
    "SKIPPED on purpose (no grid referent): human anatomy; people/social (man/woman/mother); animals/"
    "plants; food/drink; other-modality sensory (sound/noise/echo/vibration; smell/taste; tactile texture "
    "hot/cold/wet/dry/sticky/oily). LITERAL interoception (hunger/thirst/pain) is re-grounded as RESOURCE "
    "(the HUD/step budget the agent spends by acting). This is the Helen-Keller principle applied honestly: "
    "ground meaning in the senses this agent actually has, not in ones it doesn't."
)

PERCEPTUAL_MOLECULE_NAMES = set()
def _addmol(name, gloss, parts, deep):
    MOLECULES[name] = Molecule(name, gloss, tuple(parts), deep)
    PERCEPTUAL_MOLECULE_NAMES.add(name)

# --- geometry / form -------------------------------------------------------------------------
_addmol("SHAPE","the form of a thing: how its sides and edges are",("HAVE","SIDE","KIND"),"kind-of(sides,edges)")
_addmol("LINE","cells continuing in one direction",("NEAR","SIDE","SAME"),"NEAR-chain along one SIDE")
_addmol("STRAIGHT","a line that does not bend",("LINE","SAME","NOT","OTHER"),"LINE keeping SAME direction")
_addmol("CURVE","a line that bends",("LINE","OTHER","NEAR"),"LINE that changes direction")
_addmol("EDGE","where a surface ends",("SIDE","NEAR","NOT","INSIDE"),"boundary SIDE of a region")
_addmol("CORNER","where two edges meet",("EDGE","TOUCH"),"TOUCH(EDGE,EDGE)")
_addmol("TIP","the sharp/extreme end of a shape",("EDGE","SMALL","ONE"),"smallest END of a shape")
_addmol("SURFACE","the outer face of a thing",("SIDE","ALL"),"outer SIDE")
_addmol("MIDDLE","the point equidistant from the edges",("NEAR","ALL","SAME","SIDE"),"SAME NEAR to all SIDEs")
_addmol("OUTSIDE","the exterior part",("NOT","INSIDE"),"NOT INSIDE")
_addmol("HOLLOW","empty inside",("INSIDE","NOT","EXIST"),"INSIDE and NOT EXIST")
_addmol("SOLID","full inside",("INSIDE","EXIST","ALL"),"ALL INSIDE EXISTs")
_addmol("HOLE","an enclosed empty region",("HOLLOW","SIDE"),"HOLLOW bounded by SIDEs")
_addmol("GAP","empty space between things",("NOT","EXIST","SIDE","OTHER"),"NOT EXIST between two SIDEs")
_addmol("ROUND","curved all around",("CURVE","ALL"),"CURVE on ALL sides")
_addmol("FLAT","having no height",("SURFACE","NOT","ABOVE"),"SURFACE without ABOVE extent")

# --- orientation / direction ----------------------------------------------------------------
_addmol("DIRECTION","a way of moving through space",("MOVE","SIDE","WHERE"),"MOVE toward a SIDE")
_addmol("UP","toward above",("MOVE","ABOVE"),"MOVE ABOVE"); _addmol("DOWN","toward below",("MOVE","BELOW"),"MOVE BELOW")
_addmol("TOWARDS","moving closer to something",("MOVE","NEAR"),"MOVE -> NEAR")
_addmol("AWAY","moving farther from something",("MOVE","FAR"),"MOVE -> FAR")
_addmol("ALONG","following the length of something",("MOVE","NEAR","SAME"),"MOVE NEAR a line")
_addmol("ACROSS","from one side to the other",("MOVE","SIDE","OTHER"),"MOVE SIDE->OTHER SIDE")
_addmol("THROUGH","in one side and out the opposite",("MOVE","INSIDE","OTHER"),"MOVE INSIDE then out OTHER side")
_addmol("AROUND","in a curve surrounding something",("MOVE","NEAR","ALL","SIDE"),"MOVE NEAR all SIDEs")
_addmol("BETWEEN","in the gap of two things",("WHERE","SIDE","OTHER","NEAR"),"WHERE NEAR two SIDEs")
_addmol("AMONG","in the middle of several",("WHERE","INSIDE","MUCH_MANY"),"INSIDE MANY")
_addmol("NEXT_TO","beside, touching or very near",("NEAR","TOUCH"),"NEAR (maybe TOUCH)")
_addmol("OPPOSITE","facing across a space",("OTHER","SIDE","FAR"),"OTHER SIDE, FAR")
_addmol("DIAGONAL","slanting corner to corner",("LINE","SIDE","OTHER"),"LINE from a SIDE to the OTHER")
_addmol("PARALLEL","side by side, never touching",("LINE","SAME","NOT","TOUCH"),"two LINES, SAME dir, NOT TOUCH")

# --- distance / dimension -------------------------------------------------------------------
_addmol("DISTANCE","the space between two points",("FAR","NEAR","BETWEEN"),"how FAR/NEAR between")
_addmol("LENGTH","extent end to end",("BIG","ONE","SIDE"),"BIG along ONE SIDE")
_addmol("WIDTH","extent side to side",("BIG","SIDE","OTHER"),"BIG across SIDEs")
_addmol("HEIGHT","extent bottom to top",("BIG","ABOVE","BELOW"),"BIG from BELOW to ABOVE")
_addmol("DEPTH","extent surface inward",("INSIDE","FAR"),"FAR INSIDE")
_addmol("SPAN","full extent across",("ALL","FAR","SIDE"),"ALL the way across")
_addmol("BORDER","outer boundary of an area",("EDGE","ALL","AROUND"),"EDGE AROUND all of it")
_addmol("OUTLINE","the line showing outer shape",("LINE","AROUND","SHAPE"),"LINE AROUND a SHAPE")

# --- forces (action-effects) ----------------------------------------------------------------
_addmol("PULL","draw an object toward you",("DO","TOUCH","BECOME","NEAR"),"DO: BECOME(NEAR(obj))")
_addmol("LIFT","move something upward",("DO","MOVE","ABOVE"),"DO MOVE ABOVE")
_addmol("DROP","let something fall downward",("MOVE","BELOW","AFTER"),"AFTER: MOVE BELOW")
_addmol("HIT","suddenly touch with force",("TOUCH","MOMENT","VERY"),"VERY TOUCH at a MOMENT")
_addmol("PRESS","push with steady force",("TOUCH","DO","FOR_SOME_TIME"),"TOUCH/DO over time")
_addmol("SQUEEZE","press from all sides",("PRESS","ALL","SIDE"),"PRESS on ALL SIDEs")
_addmol("HOLD","keep something in one place",("TOUCH","BE_AT","NOT","MOVE"),"TOUCH and NOT MOVE")
_addmol("CARRY","support weight while moving",("HOLD","MOVE"),"HOLD then MOVE")

# --- motions / transformations --------------------------------------------------------------
_addmol("ROLL","turn over and over while moving",("MOVE","AROUND","AFTER"),"MOVE AROUND over time")
_addmol("SPIN","turn around a centre in place",("MOVE","AROUND","BE_AT","SAME"),"AROUND at SAME place")
_addmol("TWIST","turn two ends oppositely",("MOVE","AROUND","OTHER"),"AROUND in OTHER directions")
_addmol("BEND","change from straight to curved",("BECOME","NOT","STRAIGHT"),"BECOME a CURVE")
_addmol("BREAK","split into pieces",("BECOME","PART","MUCH_MANY"),"ONE BECOMEs many PARTs")
_addmol("CRACK","a thin line of breakage",("LINE","BREAK","SMALL"),"a small BREAK LINE")
_addmol("FALL","drop down due to gravity",("MOVE","BELOW","AFTER"),"AFTER: MOVE BELOW")
_addmol("SLIDE","move smoothly across a surface",("MOVE","NEAR","SAME","SURFACE"),"MOVE along a SURFACE")
_addmol("BOUNCE","spring back after hitting",("MOVE","TOUCH","AFTER","OTHER"),"after TOUCH, MOVE the OTHER way")
_addmol("SWING","move back and forth from a point",("MOVE","AROUND","BEFORE","AFTER"),"AROUND, to and fro")

# --- existence / change / causation (CORE) --------------------------------------------------
_addmol("APPEAR","come into sight / existence",("BECOME","EXIST","AFTER"),"AFTER: NOT EXIST -> EXIST")
_addmol("DISAPPEAR","go out of sight / existence",("BECOME","NOT","EXIST","AFTER"),"AFTER: EXIST -> NOT EXIST")
_addmol("CHANGE","become different",("BECOME","OTHER"),"BECOME OTHER")
_addmol("START","begin to happen",("HAPPEN","BECOME","BEFORE"),"a HAPPENing begins")
_addmol("STOP","cease to happen",("HAPPEN","NOT","AFTER"),"AFTER: NOT HAPPEN")
_addmol("STAY","not move or change",("SAME","NOT","BECOME","AFTER"),"AFTER: SAME")
_addmol("CAUSE","one thing makes another happen",("BECAUSE","DO","HAPPEN"),"DO BECAUSE HAPPEN(other)")

# --- composition / connection ----------------------------------------------------------------
_addmol("WHOLE","all of it, complete",("ALL","PART"),"ALL PARTs")
_addmol("PIECE","a part of a whole",("PART","ONE"),"ONE PART")
_addmol("PILE","many things heaped together",("MUCH_MANY","NEAR","ABOVE"),"MANY NEAR/ABOVE each other")
_addmol("LAYER","a flat sheet on top of another",("FLAT","ABOVE","SAME"),"a FLAT thing ABOVE another")
_addmol("JOIN","put two things together",("BECOME","ONE","TOUCH"),"two TOUCH -> BECOME ONE")
_addmol("SEPARATE","pull two things apart",("BECOME","OTHER","NOT","TOUCH"),"ONE -> two, NOT TOUCH")
_addmol("ATTACH","make one thing stick to another",("JOIN","NOT","MOVE"),"JOIN and held fixed")
_addmol("GROUP","several of a kind together",("MUCH_MANY","SAME","NEAR"),"MANY SAME, NEAR")

# --- visual qualities (geometric only) ------------------------------------------------------
_addmol("LONG","big in one dimension",("BIG","ONE","SIDE"),"BIG along ONE SIDE")
_addmol("SHORT","small in one dimension",("SMALL","ONE","SIDE"),"SMALL along ONE SIDE")
_addmol("THIN","small across",("SMALL","SIDE"),"SMALL across")
_addmol("THICK","big across",("BIG","SIDE"),"BIG across")

# --- pattern (SAME + DO) --------------------------------------------------------------------
_addmol("PATTERN","the same arrangement repeating",("SAME","MORE","WHERE"),"SAME repeated across places")
_addmol("REPEAT","do the same thing again",("DO","SAME","MORE"),"DO the SAME once MORE")
_addmol("IMITATE","do something the same way as another",("DO","SAME","LIKE","OTHER"),"DO LIKE the OTHER")
_addmol("REFLECT","an image the same as the thing facing it",("MIRROR",),"= MIRROR")
_addmol("FOLLOW","do the same as another, after them",("DO","SAME","AFTER"),"DO SAME AFTER the OTHER")

# --- sequential ordering --------------------------------------------------------------------
_addmol("FIRST","the one before all others",("BEFORE","ALL"),"BEFORE all")
_addmol("NEXT","the one that follows",("AFTER","ONE"),"the ONE AFTER")
_addmol("LAST","the one after all others",("AFTER","ALL"),"AFTER all")
_addmol("AGAIN","once more, repeating",("MORE","TIME"),"one MORE TIME")
_addmol("SEQUENCE","things one after another",("BEFORE","AFTER","ALL"),"ALL ordered by BEFORE/AFTER")

# --- resource (the agent's interoception = the HUD it spends by acting) ----------------------
_addmol("RESOURCE","a quantity you spend by acting (steps/score/energy on the HUD)",
        ("HAVE","LESS","AFTER","DO"),"HAVE LESS AFTER each DO")

# self-check: every perceptual molecule resolves into primes | molecules | growth-candidates
for _mn in PERCEPTUAL_MOLECULE_NAMES:
    for _part in MOLECULES[_mn].parts:
        assert _part in _RESOLVABLE or _part in MOLECULES, f"perceptual molecule {_mn} -> unknown part {_part}"


# ===========================================================================================
# TIERING: rebuild a few CONCEPT molecules ON the perceptual tier, so the hierarchy is real:
#   primes  ->  perceptual molecules  ->  concept molecules.  Transitive resolution still bottoms
#   out in primes (asserted). This is the "built from them" claim made concrete, not asserted.
# ===========================================================================================
MOLECULES["GRAVITY"]  = Molecule("GRAVITY", "objects fall and settle in a force direction",
                                 ("FALL", "ALL", "STAY"), "ALL(o): FALL(o) then STAY", ("bp35",))
MOLECULES["CONVEYOR"] = Molecule("CONVEYOR", "items slide along a repeating loop each step",
                                 ("SLIDE", "REPEAT", "AROUND"), "REPEAT(SLIDE(items) AROUND loop)", ("lp85",))
MOLECULES["FLOW"]     = Molecule("FLOW", "a substance spreads to neighbouring cells over time",
                                 ("SLIDE", "NEAR", "MUCH_MANY", "AFTER"), "AFTER: SLIDE to MANY NEAR cells", ("sp80",))
MOLECULES["MIX"]      = Molecule("MIX", "combine two things into a new one",
                                 ("JOIN", "BECOME", "OTHER"), "JOIN(a,b) -> BECOME OTHER", ("su15",))

# verify the tiering: each rebuilt concept molecule still resolves entirely into the prime basis
import sys as _s
for _c in ("GRAVITY", "CONVEYOR", "FLOW", "MIX"):
    _pr = _decompose_molecule(_c)
    assert _pr and _pr <= _RESOLVABLE, f"{_c} does not bottom out in primes: {_pr - _RESOLVABLE}"


# ===========================================================================================
# (2) SPEAK + COVERAGE  --  confirm molecules are grammar-built, and let the composer narrate in
#     words + molecule + grammar deep-form + primes, so it can state hypotheses/perception clearly.
# (3) COMPOSE-OR-INVENT  --  when an interaction can't be named with the current set, compose it from
#     molecules, or MINT a provisional (TEMP) molecule from base primes + the object projection, to
#     build a hypothesis around. This is "composers not libraries": synthesise a new basis element.
# ===========================================================================================
def molecule_coverage():
    """Confirm every molecule bottoms out in the prime basis. Returns (total, clean, needs_growth)."""
    clean = growth = 0
    for n in MOLECULES:
        pr = _decompose_molecule(n)
        if any(p in GROWTH_CANDIDATES for p in pr):
            growth += 1
        elif pr <= ALL_PRIMES:
            clean += 1
    return dict(total=len(MOLECULES), clean_into_primes=clean, needs_growth=growth)

def speak(name):
    """The composer's unified self-explanation of what it perceives or hypothesises:
       words (gloss) + the molecule/predicate + grammar deep-form + the primes it is built from."""
    if name in MOLECULES:
        e = explain_molecule(name)
        s = (f"I read this as {name} \u2014 {e['words']}. Formally {e['deep_form']}; "
             f"built from primes [{', '.join(e['primes'])}]")
        if e["needs_growth"]:
            s += f"  (still needs a new universal prime: {e['needs_growth']})"
        if name in TEMP_MOLECULES:
            s += "  [PROVISIONAL \u2014 invented from observation, not yet proven]"
        return s + "."
    if name in PREDICATES:
        e = explain(name)
        return (f"I hypothesise the goal {name} \u2014 {e['words']}. Formally {e['grammar']}; "
                f"primes [{', '.join(e['primes'])}].")
    return f"I have no grounded word for '{name}' yet (would compose-or-invent one)."

TEMP_MOLECULES = set()
_temp_counter = [0]

def compose_or_invent(observed_primes, context="", name_hint=None, invent=True):
    """Resolve an observed interaction to grammar. Cascade:
       1) LIBRARY   -- an existing molecule whose primes match the observation exactly;
       2) NEAREST   -- the single molecule whose primes best match (subset/overlap) when none is exact;
       3) COMPOSITE -- a small set of molecules whose union covers the observed primes;
       4) INVENT    -- mint a PROVISIONAL (TEMP) molecule from the base primes that describe it
                       (+ the object/relation context), to build a hypothesis around.
       invent=False stops before (4) and returns {"mode":"gap"} -- for the FREQUENT read-only reach where
       the agent wants to SEE what the library holds without minting a provisional on every glance (that is
       the residual-router's cheap path; minting stays gated to a reproduced residual).
       Grounded: only primes already in the basis are used; the result always decomposes to primes."""
    prs = tuple(sorted(p for p in observed_primes if p in ALL_PRIMES))
    if not prs:
        return {"mode": "fail", "reason": "no observed prime is in the basis"}
    want = set(prs)
    # 1) library (exact)
    for n in MOLECULES:
        if _decompose_molecule(n) == want:
            return {"mode": "library", "name": n, "primes": prs}
    # 2) nearest single molecule -- the agent reaches for the closest tool it already has. Score = observed
    #    primes the molecule covers, minus the primes it asserts but were NOT observed (specificity penalty).
    _best, _bs = None, 0.0
    for n in MOLECULES:
        pr = _decompose_molecule(n)
        if not pr:
            continue
        sc = len(pr & want) - 0.5 * len(pr - want)
        if sc > _bs:
            _bs, _best = sc, n
    # 2b) TIGHT COVER: an existing molecule that covers EVERY observed prime with at most one extra IS the
    #     tool for this observation. Reach it -- do NOT mint a near-duplicate. (The residue rule: prefer the
    #     tool you have over a new atom.)
    if _best is not None:
        _bp = _decompose_molecule(_best)
        if want <= _bp and len(_bp - want) <= 1:
            return {"mode": "nearest", "name": _best, "primes": prs, "extra": sorted(_bp - want)}
    # 3) composite (greedy set cover by molecules)
    cover, need = [], set(want)
    for n in sorted(MOLECULES, key=lambda m: len(_decompose_molecule(m))):
        pr = _decompose_molecule(n)
        if pr and (pr <= want) and (pr & need):
            cover.append(n); need -= pr
        if not need:
            break
    if not need and len(cover) >= 2:
        return {"mode": "composite", "from": cover, "primes": prs, "nearest": _best}
    if not invent:
        return {"mode": "gap", "primes": prs, "nearest": _best, "nearest_score": round(_bs, 2),
                "context": context}
    # 4) invent a provisional molecule
    _temp_counter[0] += 1
    name = name_hint or f"TEMP_{_temp_counter[0]}"
    MOLECULES[name] = Molecule(name, f"provisional concept ({context})" if context else "provisional concept",
                               prs, f"<learned from observation: {context or 'unnamed interaction'}>", ())
    TEMP_MOLECULES.add(name)
    return {"mode": "invent", "name": name, "primes": prs, "provisional": True, "context": context,
            "nearest": _best}

def promote_temp_molecule(name, gloss=None, deep_form=None):
    """If a provisional molecule proves useful, make it permanent (drop the TEMP tag)."""
    if name in TEMP_MOLECULES:
        TEMP_MOLECULES.discard(name)
        if gloss or deep_form:
            m = MOLECULES[name]
            MOLECULES[name] = Molecule(name, gloss or m.gloss, m.parts, deep_form or m.deep_form, m.games)
        return True
    return False

def clear_temp_molecules():
    for n in list(TEMP_MOLECULES):
        MOLECULES.pop(n, None)
    TEMP_MOLECULES.clear()


# ===========================================================================================
# Admit the growth primes so the basis fully spans the current molecule set (Isaiah's call).
#   LESS  -> admitted as a real quantity prime (counterpart of MORE).
#   MAP   -> dissolved: MAP_DECODE is rebuilt on the existing similarity prime LIKE (rosetta = learning a
#            LIKE-correspondence), so no non-NSM "MAP" prime is needed.
#   SHRINK-> added as GROW/EXTEND's counterpart (a real dynamics molecule the tracker emits).
# ===========================================================================================
ALL_PRIMES |= {"LESS"}
GROWTH_CANDIDATES.clear()                      # nothing outstanding: basis now spans the set
_RESOLVABLE = ALL_PRIMES | set(GROWTH_CANDIDATES)
MOLECULES["MAP_DECODE"] = Molecule("MAP_DECODE", "decode via a learned symbol-to-symbol correspondence",
                                   ("ALL", "SAME", "LIKE"), "ALL(x: SAME(meaning(x), key(x)))  via a LIKE-mapping", ("tr87",))
MOLECULES["SHRINK"] = Molecule("SHRINK", "become smaller / lose cells",
                               ("BECOME", "SMALL", "LESS"), "BECOME SMALL (LESS cells)")
PERCEPTUAL_MOLECULE_NAMES.add("SHRINK")
# re-verify full coverage
for _mn, _m in MOLECULES.items():
    for _part in _m.parts:
        assert _part in _RESOLVABLE or _part in MOLECULES, f"{_mn} -> unknown part {_part}"


# ===========================================================================================
# SELF/WORLD NARRATION (11.320): let the composer speak about self vs world in the grounded basis.
# The self is the action-discriminative response (DO -> something happens to a PART that is "me"); the
# world is what HAPPENs beyond that; a constraint is an action after which NOT(something happens) = a wall.
# ===========================================================================================
_SELFWORLD_MODALITY = {
    "translate": ("I MOVE a PART (a marker that goes where I steer)", ("I", "DO", "MOVE", "PART")),
    "located":   ("I DO something at a PLACE (an effect where I act)", ("I", "DO", "HAPPEN", "WHERE")),
    "regional":  ("I make a PART BECOME OTHER (I change a region)",     ("I", "DO", "BECOME", "OTHER")),
    None:        ("I do not yet know which PART is me",                  ("I", "DO", "NOT", "KNOW")),
}

def narrate_self_world(summary):
    """Return a grammar-grounded narration of a self/world summary (dict from SelfWorldModel.summary())."""
    mod = summary.get("self_modality")
    gloss, primes = _SELFWORLD_MODALITY.get(mod, _SELFWORLD_MODALITY[None])
    lines = [f"SELF: {gloss}  [primes: {' '.join(primes)}]"]
    if summary.get("world_active"):
        lines.append("WORLD: after I DO, OTHER things HAPPEN that are NOT me (a world law responds)  "
                     "[primes: AFTER I DO, OTHER HAPPEN NOT I]")
    else:
        lines.append("WORLD: after I DO, nothing HAPPENs that is NOT me (turn-based, only I move)  "
                     "[primes: AFTER I DO, NOT(OTHER HAPPEN)]")
    if summary.get("blocked_actions"):
        lines.append(f"CONSTRAINT: when I DO {', '.join(summary['blocked_actions'])}, NOT(something HAPPENs) "
                     "= I CAN NOT move here (a wall)  [primes: I DO, NOT HAPPEN -> CAN NOT MOVE]")
    return "\n".join(lines)
