"""
grammar.py -- THE MAP SS9.1 + SSVII.1: a TYPED objective grammar. "Typing beats size" (B1a): a
typed grammar GROWS to cover new cases without paying the exponential branching cost of a flat bag.

Grounded via the FMap on small_world_network: a type system makes the COMPOSITION GRAPH sparse --
most primitives do not compose with most others (they are type-incompatible), and a few hub types
(PRED, OBJ) give short paths. Sparse-with-hubs is how typing shrinks V at the point of choice.

Vocabulary is MAP SS9.1 (Kant-organised, NSM-seeded primes; composable predicate heads; molecules
as named typed composites). The load-bearing addition over a flat bag is the TYPE SIGNATURE on every
prime and the TYPE-CHECK on every composition -- so the search space is the type-valid compositions,
not V^k.

Discipline: encodes NO game answer (only a basis + a typed search procedure); nothing silent
(every ill-typed composition raises with its reason).
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Dict, List, Optional


class T(Enum):
    OBJECT = "OBJECT"     # a perceived object / its identity
    ATTR = "ATTR"         # an attribute value (colour, shape, orientation, position)
    REGION = "REGION"     # a set of cells / an area / a target locus
    PRED = "PRED"         # a relation that holds or not (a hub type)
    OBJ = "OBJ"           # a complete objective (a quantified relation) -- the goal type (a hub type)


class TypeError_(TypeError):
    pass


@dataclass(frozen=True)
class Prime:
    name: str
    category: str                 # Kant category (Quantity/Quality/Relation/Modality/Space/Time)
    in_types: Tuple[T, ...]       # what it consumes
    out_type: T                   # what it produces  -- the type signature that makes the grammar TYPED
    gloss: str = ""


# --- THE PRIME BASIS (MAP SS9.1), each with a TYPE SIGNATURE -----------------------------------
_P = lambda *a, **k: Prime(*a, **k)
PRIMES: Dict[str, Prime] = {p.name: p for p in [
    # Relation primes: build a PRED from objects/attrs/regions
    _P("BE_AT",  "Relation", (T.OBJECT, T.REGION), T.PRED, "an object is located at a region"),
    _P("TOUCH",  "Relation", (T.OBJECT, T.OBJECT), T.PRED, "two objects are in contact"),
    _P("BECOME", "Relation", (T.OBJECT, T.ATTR),   T.PRED, "an object takes a target attribute"),
    _P("BECAUSE","Relation", (T.PRED, T.PRED),     T.PRED, "one relation causes another"),
    # Quality primes: build/compare ATTR and negate PRED
    _P("SAME",   "Quality",  (T.ATTR, T.ATTR),     T.PRED, "two attributes are equal"),
    _P("OTHER",  "Quality",  (T.ATTR, T.ATTR),     T.PRED, "two attributes differ"),
    _P("NOT",    "Quality",  (T.PRED,),            T.PRED, "negation of a relation"),
    _P("EXIST",  "Modality", (T.OBJECT,),          T.PRED, "an object exists"),
    _P("CAN",    "Modality", (T.PRED,),            T.PRED, "a relation is achievable (affordance)"),
    # Quantity primes: close a PRED over a scope into a complete OBJ (the goal)
    _P("ALL",    "Quantity", (T.PRED,),            T.OBJ,  "the relation holds for all in scope"),
    _P("SOME",   "Quantity", (T.PRED,),            T.OBJ,  "the relation holds for some in scope"),
    _P("ONE",    "Quantity", (T.PRED,),            T.OBJ,  "the relation holds for exactly one"),
    _P("NONE",   "Quantity", (T.PRED,),            T.OBJ,  "the relation holds for none"),
]}
KANT_CATEGORIES = sorted({p.category for p in PRIMES.values()})


@dataclass(frozen=True)
class Term:
    """A typed composition tree. Its type is head.out_type; constructed only if args type-check."""
    head: str
    args: Tuple = ()
    @property
    def type(self) -> T:
        return PRIMES[self.head].out_type


def _type_of(x) -> T:
    if isinstance(x, Term):
        return x.type
    if isinstance(x, T):
        return x                     # a bare typed hole (a leaf of a given type: OBJECT/ATTR/REGION)
    raise TypeError_("not a typed value: %r" % (x,))


def compose(head: str, *args) -> Term:
    """Type-checked composition. Raises TypeError_ (never silently) if arg types don't match the signature."""
    if head not in PRIMES:
        raise TypeError_("unknown prime '%s'" % head)
    sig = PRIMES[head]
    got = tuple(_type_of(a) for a in args)
    if got != sig.in_types:
        raise TypeError_("ill-typed: %s expects %s but got %s"
                         % (head, tuple(t.value for t in sig.in_types), tuple(t.value for t in got)))
    return Term(head, tuple(args))


def is_objective(t: Term) -> bool:
    return isinstance(t, Term) and t.type is T.OBJ


# --- MOLECULES: named typed composites (MAP SS9.1); each type-checks by construction -----------
def _match():   # SAME(colour_of_key, colour_of_lock) quantified -> the ls20-class "match" objective, TYPED
    return compose("SOME", compose("SAME", T.ATTR, T.ATTR))
def _reach():   # SOME object BE_AT a region (maze/reach), TYPED
    return compose("SOME", compose("BE_AT", T.OBJECT, T.REGION))
def _clear():   # NONE object EXISTs (erase/collect), TYPED
    return compose("NONE", compose("EXIST", T.OBJECT))
MOLECULES: Dict[str, Term] = {"MATCH": _match(), "REACH": _reach(), "CLEAR": _clear()}


# --- the search space is the TYPE-VALID compositions, not V^k (typing beats size) --------------
def count_typed_objectives(depth: int) -> int:
    """Count distinct well-typed OBJ templates up to `depth` composition steps (the AIMED search space)."""
    # build the reachable set of typed Terms by forward type-directed composition from leaf holes
    leaves = [T.OBJECT, T.ATTR, T.REGION]
    pool = list(leaves)
    for _ in range(depth):
        new = []
        for name, p in PRIMES.items():
            # try filling this prime's signature from the current pool (type-directed only)
            import itertools
            candidates = [pool] * len(p.in_types)
            for combo in itertools.product(*candidates):
                if tuple(_type_of(c) for c in combo) == p.in_types:
                    try:
                        new.append(compose(name, *combo))
                    except TypeError_:
                        pass
        pool = list(pool) + new
        # de-dup by (head, arg-types) signature to keep it finite and templatey
        seen = {}; dedup = []
        for x in pool:
            key = x if isinstance(x, T) else (x.head, tuple(_type_of(a).value for a in x.args))
            if key not in seen:
                seen[key] = 1; dedup.append(x)
        pool = dedup
    return sum(1 for x in pool if isinstance(x, Term) and x.type is T.OBJ)


def count_flat_bag(depth: int, n_leaf_types: int = 3) -> int:
    """A FLAT bag (no types) would admit ~V^depth compositions -- the exponential the type system avoids."""
    V = len(PRIMES) + n_leaf_types
    return V ** depth
