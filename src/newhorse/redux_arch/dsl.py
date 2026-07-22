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
import itertools

# ---- types (a tiny type system so pruning is real, not decorative) -----------------------------------------
OBJ, COLOUR, VEC, BOOL = "OBJ", "COLOUR", "VEC", "BOOL"


@dataclass(frozen=True)
class Context:
    """The BEFORE-state a predicate sees: the focus object, the target object, and the focus's displacement
    under the chosen action (an agency-supplied before-state fact). Coordinates are (row, col); a colour is int."""
    focus_rc: Tuple[int, int]
    focus_colour: int
    target_rc: Tuple[int, int]
    action_vec: Tuple[int, int]                          # focus displacement under the action (0,0 if none/blocked)

    def _dist(self) -> int:
        return abs(self.focus_rc[0] - self.target_rc[0]) + abs(self.focus_rc[1] - self.target_rc[1])


# ---- atoms: typed boolean constructors over the before-state -----------------------------------------------
@dataclass(frozen=True)
class Atom:
    name: str
    cost: int                                            # description-length weight (bits), used by the MDL score
    _eval: Callable[[Context], bool]
    def holds(self, ctx: Context) -> bool:
        return self._eval(ctx)


# each entry: kind -> (arg types, builder). The builder is only ever called with type-checked args.
def _has_colour(c: int) -> Atom:
    return Atom("colour==%d" % c, 3, lambda ctx: ctx.focus_colour == c)

def _near() -> Atom:
    return Atom("NEAR(focus,target)", 2, lambda ctx: ctx._dist() <= 1)

def _touch() -> Atom:
    return Atom("TOUCH(focus,target)", 2, lambda ctx: ctx._dist() == 1)

def _align_row() -> Atom:
    return Atom("SAME_ROW(focus,target)", 2, lambda ctx: ctx.focus_rc[0] == ctx.target_rc[0])

def _align_col() -> Atom:
    return Atom("SAME_COL(focus,target)", 2, lambda ctx: ctx.focus_rc[1] == ctx.target_rc[1])

def _acts_toward() -> Atom:
    def f(ctx: Context) -> bool:
        r0, c0 = ctx.focus_rc; dr, dc = ctx.action_vec
        d_before = abs(r0 - ctx.target_rc[0]) + abs(c0 - ctx.target_rc[1])
        d_after = abs(r0 + dr - ctx.target_rc[0]) + abs(c0 + dc - ctx.target_rc[1])
        return d_after < d_before
    return Atom("ACTS_TOWARD(focus,target)", 2, f)


# the typed atom registry: kind -> (arg_types, builder)
_ATOM_TYPES: Dict[str, Tuple[Tuple[str, ...], Callable[..., Atom]]] = {
    "HAS_COLOUR": ((COLOUR,), _has_colour),
    "NEAR":        ((), _near),
    "TOUCH":       ((), _touch),
    "SAME_ROW":    ((), _align_row),
    "SAME_COL":    ((), _align_col),
    "ACTS_TOWARD": ((), _acts_toward),
}


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


def atom_universe(colours: Iterable[int]) -> List[Atom]:
    """All well-typed atoms given the COLOUR domain present in the scene (type-directed instantiation)."""
    atoms: List[Atom] = [make_atom(k) for k, (argt, _) in _ATOM_TYPES.items() if not argt]
    for c in sorted(set(int(x) for x in colours)):
        atoms.append(make_atom("HAS_COLOUR", c))
    return atoms


def enumerate_predicates(colours: Iterable[int], max_size: int = 2) -> List[Predicate]:
    """Every well-typed conjunction of 1..max_size distinct atoms -- the space the minter searches (bounded)."""
    universe = atom_universe(colours)
    preds: List[Predicate] = []
    for size in range(1, max_size + 1):
        for combo in itertools.combinations(universe, size):
            preds.append(Predicate(frozenset(combo)))
    return preds
