"""
dsl.py -- redux-arch P1: a TYPED predicate DSL Γ over the BEFORE-state, with type-directed enumeration.

Harvested from Redux `objective_grammar` (the NSM/Kant prime basis: Quantity/Quality/Relation/Modality) and
re-expressed as the search space the minter (P2) partitions a residual with. The load-bearing constraint: a
predicate φ is a function of the BEFORE-state ONLY -- `Context = (focus, target, action_vec)`, everything known
BEFORE observing the outcome (the action's effect on the focus is a before-state fact supplied by the agency).
There is no accessor to the after-state or the outcome, so a φ that "predicts" by peeking is not constructible
-- the tautology guard is a TYPE property, not a rule to remember (spec: "φ must be evaluable on the before-state").

Type-directed pruning [Osera&Zdancewic 2015; Ellis 2021]: atoms declare argument TYPES; ill-typed atoms are
never constructed, so enumeration stays bounded as the vocabulary grows. A predicate is a conjunction (Quality
prime AND over Relation atoms) -- the smallest composition that lets an MDL split test fire.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Optional, FrozenSet, Iterable
import itertools, os

# ★ VOCABULARY GROWTH (blend M2, flag-gated). The relational atoms below are geometry-only {NEAR,TOUCH,SAME_ROW/
# COL,ACTS_TOWARD} -- a navigation-only objective vocabulary (the B-VOCAB gap: the composer is on-path for
# navigation games, off-path for MATCH/ORDER/REFLECT). SAME_COLOUR grounds the grammar's MATCH = SAME(ATTR,ATTR)
# molecule as an EVALUABLE before-state predicate over the shared Γ, so BOTH the live composer (pose_goal /
# two_part_mdl) AND the nexus proposer gain it. It is always in the REGISTRY (make_atom works), but only enters
# `atom_universe` (the enumerated search space) when OURO_VOCAB_MATCH is set -- default OFF keeps every existing
# MDL decision, and the suite, byte-for-byte unchanged; ON is A/B-able.
_VOCAB_MATCH = os.environ.get("OURO_VOCAB_MATCH", "") not in ("", "0", "false", "False", "off")

# ---- types (a tiny type system so pruning is real, not decorative) -----------------------------------------
OBJ, COLOUR, VEC, BOOL = "OBJ", "COLOUR", "VEC", "BOOL"


@dataclass(frozen=True)
class Context:
    """The BEFORE-state a predicate sees: the focus object, the target object, the focus's displacement under
    the chosen action, and what occupies the cell the focus would ENTER (an affordance fact -- all before-state,
    all known before the outcome). Coordinates are (row, col); a colour is int."""
    focus_rc: Tuple[int, int]
    focus_colour: int
    target_rc: Tuple[int, int]
    action_vec: Tuple[int, int]                          # focus displacement under the action (0,0 if none/blocked)
    intended_free: bool = True                           # is the cell the focus would enter background/free?
    intended_colour: Optional[int] = None                # colour occupying that cell (None if unknown/edge)
    target_colour: Optional[int] = None                  # the TARGET object's colour (for MATCH = SAME(ATTR,ATTR));
    #                                                      None where unsupplied -> SAME_COLOUR is simply never true

    def _dist(self) -> int:
        return abs(self.focus_rc[0] - self.target_rc[0]) + abs(self.focus_rc[1] - self.target_rc[1])


# ---- atoms: typed boolean constructors over the before-state -----------------------------------------------
@dataclass(frozen=True)
class Atom:
    name: str
    cost: int                                            # description-length weight (bits), used by the MDL score
    _eval: Callable[[Context], bool]
    kind: str = ""                                       # the REGISTRY KIND, written by the builder that made it
    def holds(self, ctx: Context) -> bool:
        return self._eval(ctx)


# each entry: kind -> (arg types, builder). The builder is only ever called with type-checked args.
# Each builder stamps its OWN registry kind onto the atom it returns. That is deliberate: the alternative is to
# recover the kind later by parsing `name`, and a name parsed after the fact is a guess about what a branch did
# rather than a record of it. The builder is the branch; it writes its own literal.
def _has_colour(c: int) -> Atom:
    return Atom("colour==%d" % c, 3, lambda ctx: ctx.focus_colour == c, kind="HAS_COLOUR")

def _near() -> Atom:
    return Atom("NEAR(focus,target)", 2, lambda ctx: ctx._dist() <= 1, kind="NEAR")

def _touch() -> Atom:
    return Atom("TOUCH(focus,target)", 2, lambda ctx: ctx._dist() == 1, kind="TOUCH")

def _align_row() -> Atom:
    return Atom("SAME_ROW(focus,target)", 2, lambda ctx: ctx.focus_rc[0] == ctx.target_rc[0], kind="SAME_ROW")

def _align_col() -> Atom:
    return Atom("SAME_COL(focus,target)", 2, lambda ctx: ctx.focus_rc[1] == ctx.target_rc[1], kind="SAME_COL")

def _acts_toward() -> Atom:
    def f(ctx: Context) -> bool:
        r0, c0 = ctx.focus_rc; dr, dc = ctx.action_vec
        d_before = abs(r0 - ctx.target_rc[0]) + abs(c0 - ctx.target_rc[1])
        d_after = abs(r0 + dr - ctx.target_rc[0]) + abs(c0 + dc - ctx.target_rc[1])
        return d_after < d_before
    return Atom("ACTS_TOWARD(focus,target)", 2, f, kind="ACTS_TOWARD")

def _same_colour() -> Atom:                              # MATCH = SAME(ATTR,ATTR): focus attr equals target attr
    return Atom("SAME_COLOUR(focus,target)", 2,
                lambda ctx: ctx.target_colour is not None and ctx.focus_colour == ctx.target_colour,
                kind="SAME_COLOUR")

def _intended_free() -> Atom:                            # affordance: is the cell I'd enter free? (CAN move)
    return Atom("INTENDED_FREE", 2, lambda ctx: bool(ctx.intended_free), kind="INTENDED_FREE")

def _intended_colour(c: int) -> Atom:                    # colour-gated affordance: what's in the way is colour c
    return Atom("INTENDED_COLOUR==%d" % c, 3, lambda ctx: ctx.intended_colour == c, kind="INTENDED_COLOUR")


# the typed atom registry: kind -> (arg_types, builder)
_ATOM_TYPES: Dict[str, Tuple[Tuple[str, ...], Callable[..., Atom]]] = {
    "HAS_COLOUR":      ((COLOUR,), _has_colour),
    "NEAR":            ((), _near),
    "TOUCH":           ((), _touch),
    "SAME_ROW":        ((), _align_row),
    "SAME_COL":        ((), _align_col),
    "SAME_COLOUR":     ((), _same_colour),               # MATCH-by-attribute (grammar SAME molecule, grounded)
    "ACTS_TOWARD":     ((), _acts_toward),
    "INTENDED_FREE":   ((), _intended_free),             # the occupancy vocabulary (not the answer) for affordances
    "INTENDED_COLOUR": ((COLOUR,), _intended_colour),
}


# ---- the vocabulary partition: GROUND-COLOUR literals vs RELATIONAL atoms -----------------------------------
# Two families, defined over the REGISTRY KINDS and nothing else. A ground-colour literal names a colour and is
# therefore tied to the palette of the board it was learned on; a relational atom names a geometric or affordance
# relation between focus and target and carries no palette with it. The partition exists so a rejected predicate
# can be charged to a family AT THE POINT OF REJECTION -- it is a bookkeeping split of the existing vocabulary,
# not a new detector, not a new atom, and not a gate: nothing in the search or the MDL score reads it.
COLOUR_ATOM_KINDS = frozenset({"HAS_COLOUR", "INTENDED_COLOUR"})
RELATIONAL_ATOM_KINDS = frozenset({"NEAR", "TOUCH", "SAME_ROW", "SAME_COL", "SAME_COLOUR", "ACTS_TOWARD", "INTENDED_FREE"})
assert COLOUR_ATOM_KINDS | RELATIONAL_ATOM_KINDS == frozenset(_ATOM_TYPES)   # exhaustive over the registry
assert not (COLOUR_ATOM_KINDS & RELATIONAL_ATOM_KINDS)                       # and exclusive


# ---- the second partition: which atoms read the agent's OWN MOTION -------------------------------------------
# `action_vec` is the one field of `Context` that is not a fact about the board -- it is a fact about the AGENT,
# the displacement its own action produces. An atom that reads it cannot be evaluated by a drive that has not yet
# established a self, and evaluating it anyway with `action_vec=(0,0)` is worse than abstaining: the predicate
# comes back uniformly False while LOOKING like it was evaluated, which prints "the objective named nothing" for
# what is really "I had nothing to evaluate it with". Declared here, beside the registry, so a future motion atom
# is registered in one place rather than discovered by a caller that guessed wrong.
MOTION_ATOM_KINDS = frozenset({"ACTS_TOWARD"})
assert MOTION_ATOM_KINDS <= frozenset(_ATOM_TYPES)       # every motion kind is a real registered atom


def reads_motion(pred: "Predicate") -> bool:
    """Does this predicate's truth depend on the agent's own displacement? Composed atoms (`COMPOSED:`) are built
    from before-state EXTRACTORS over focus/target only and never touch `action_vec`, so they are motion-free by
    construction; the assert above is what keeps that claim honest for the hand-written half."""
    return any(a.kind in MOTION_ATOM_KINDS for a in pred.atoms)


def atom_family(atom: Atom) -> str:
    """Which vocabulary family an atom belongs to: 'colour', 'relational', or 'unregistered'. The last is named
    rather than folded into either side: an atom whose kind is not in the registry is a wiring fault, and a
    wiring fault silently counted as 'relational' is exactly the mis-labelled receipt this file exists to avoid."""
    if atom.kind in COLOUR_ATOM_KINDS:
        return "colour"
    if atom.kind in RELATIONAL_ATOM_KINDS or atom.kind.startswith("COMPOSED:"):   # composed relations are relational
        return "relational"
    return "unregistered"


def predicate_family(pred: "Predicate") -> str:
    """The COMPOSITION of a predicate over the two families: 'colour' (every atom is a ground-colour literal),
    'relational' (every atom is relational), 'both' (a conjunction spanning the two), 'empty' (no atoms at all --
    the vacuously-true predicate, which cannot arise from `enumerate_predicates` but is representable), or
    'unregistered' if any atom is unregistered. Exhaustive and exclusive by construction; no threshold."""
    fams = {atom_family(a) for a in pred.atoms}
    if not fams:
        return "empty"
    if "unregistered" in fams:
        return "unregistered"
    if fams == {"colour"}:
        return "colour"
    if fams == {"relational"}:
        return "relational"
    return "both"


def make_atom(kind: str, *args) -> Atom:
    """Construct a typed atom; raise TypeError on ill-typed args (this is the type-directed pruning gate)."""
    if kind not in _ATOM_TYPES:
        raise TypeError("unknown atom kind %r" % kind)
    argtypes, builder = _ATOM_TYPES[kind]
    if len(args) != len(argtypes):
        raise TypeError("%s expects %d arg(s), got %d" % (kind, len(argtypes), len(args)))
    for a, t in zip(args, argtypes):
        if t == COLOUR and not isinstance(a, int):
            raise TypeError("%s expects a COLOUR (int), got %r" % (kind, a))
    return builder(*args)


# ---- predicates: conjunctions of atoms (Quality AND over Relation atoms) ------------------------------------
@dataclass(frozen=True)
class Predicate:
    atoms: FrozenSet[Atom]
    def holds(self, ctx: Context) -> bool:
        return all(a.holds(ctx) for a in self.atoms)
    def cost(self) -> int:
        return sum(a.cost for a in self.atoms) or 1
    def __str__(self) -> str:
        return " ∧ ".join(sorted(a.name for a in self.atoms)) or "TRUE"


# ═══ THE SENSOR BASIS -- the invention loop, Half A (flag OURO_COMPOSE) ══════════════════════════════════════
# Relational atoms are not a hand-list; they are COMPOSITIONS of typed before-state EXTRACTORS (what the agent can
# read of focus/target) under comparison PRIMES. {SAME_ROW,SAME_COL,SAME_COLOUR} = EQ over extractor pairs
# (re-DERIVED, not hand-written); LT over a position axis INVENTS an ORDER/directional relation with no ORDER atom
# ever written. The composer enumerates these; the GROUND (MDL over the progress residual) keeps the ones that
# pay and biodegrades the rest. This is the agent composing the relation it needs from a basis, per
# DESIGN_the_invention_loop_compose_dont_hand_add. Default OFF (OURO_COMPOSE unset) -> universe unchanged.
_COMPOSE = os.environ.get("OURO_COMPOSE", "") not in ("", "0", "false", "False", "off")

# name -> (value TYPE, before-state extractor). A None read makes any comparison False (honest abstain, no smuggle).
# Each extractor's value TYPE gates which pairs compose. ROW and COL are DISTINCT types (not a shared COORD):
# the 25-sweep with OURO_COMPOSE on showed cross-axis comparisons (focus.row<target.col, focus.col=target.row)
# are semantically meaningless yet SPURIOUSLY compress a short progress residual -- on wa30 a row-vs-col relation
# scored 13.4 bits and OUTSCORED the real objective. The ground did NOT prune them; strict typing prevents them
# at construction (row~row, col~col, colour~colour only), which is the honest type-directed pruning, not a patch.
_EXTRACTORS: Dict[str, Tuple[str, Callable[["Context"], Optional[int]]]] = {
    "focus.colour":  ("COLOUR", lambda c: c.focus_colour),
    "target.colour": ("COLOUR", lambda c: c.target_colour),
    "focus.row":     ("ROW",    lambda c: c.focus_rc[0]),
    "focus.col":     ("COL",    lambda c: c.focus_rc[1]),
    "target.row":    ("ROW",    lambda c: c.target_rc[0]),
    "target.col":    ("COL",    lambda c: c.target_rc[1]),
}
# comparison primes: symbol, fn, symmetric?  EQ symmetric (one atom/unordered pair); LT directional (both orders).
_COMPARE_PRIMES: Dict[str, Tuple[str, Callable[[int, int], bool], bool]] = {
    "EQ": ("=", lambda a, b: a == b, True),
    "LT": ("<", lambda a, b: a < b, False),
}

def _compose_atom(prime: str, ea: str, eb: str) -> Atom:
    """One composed evaluable relation: prime(extractor_a, extractor_b), a before-state function -> bool."""
    sym, fn, _sym = _COMPARE_PRIMES[prime]
    _ta, fa = _EXTRACTORS[ea]; _tb, fb = _EXTRACTORS[eb]
    def _eval(ctx: "Context") -> bool:
        va, vb = fa(ctx), fb(ctx)
        return va is not None and vb is not None and fn(va, vb)
    return Atom("%s%s%s" % (ea, sym, eb), 2, _eval, kind="COMPOSED:%s" % prime)

def composed_relational_atoms() -> List[Atom]:
    """The GENERATED relational vocabulary: every type-valid EXTRACTOR pair under every comparison PRIME. EQ
    re-derives SAME_ROW/SAME_COL/SAME_COLOUR; LT invents the ordering/directional relations -- none hand-written."""
    out: List[Atom] = []
    names = list(_EXTRACTORS)
    for prime, (_symb, _fn, symmetric) in _COMPARE_PRIMES.items():
        for i, ea in enumerate(names):
            for j, eb in enumerate(names):
                if ea == eb:
                    continue
                if symmetric and j <= i:                       # unordered pairs for a symmetric prime
                    continue
                if _EXTRACTORS[ea][0] != _EXTRACTORS[eb][0]:    # type-valid: colour~colour, coord~coord
                    continue
                out.append(_compose_atom(prime, ea, eb))
    return out


def atom_universe(colours: Iterable[int]) -> List[Atom]:
    """All well-typed atoms given the COLOUR domain present in the scene (type-directed instantiation).
    With OURO_COMPOSE the relational vocabulary becomes GENERATIVE (composed_relational_atoms), so the composer
    can select relations -- e.g. an ORDER (LT) relation -- that were never hand-written."""
    atoms: List[Atom] = [make_atom(k) for k, (argt, _) in _ATOM_TYPES.items()
                         if not argt and (k != "SAME_COLOUR" or _VOCAB_MATCH)]   # MATCH atom gated (blend M2)
    for c in sorted(set(int(x) for x in colours)):
        atoms.append(make_atom("HAS_COLOUR", c))
        atoms.append(make_atom("INTENDED_COLOUR", c))
    if _COMPOSE:
        atoms.extend(composed_relational_atoms())              # invention loop: the generated relation basis
    return atoms


def enumerate_predicates(colours: Iterable[int], max_size: int = 2) -> List[Predicate]:
    """Every well-typed conjunction of 1..max_size distinct atoms -- the space the minter searches (bounded)."""
    universe = atom_universe(colours)
    preds: List[Predicate] = []
    for size in range(1, max_size + 1):
        for combo in itertools.combinations(universe, size):
            preds.append(Predicate(frozenset(combo)))
    return preds
