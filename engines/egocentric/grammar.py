"""grammar.py -- REASONING GATE STAGE 1 (PREREG_GATE_STAGE1_SHADOW.md par.1):
the utterance grammar, a TYPED extension of the salvaged primes.

SALVAGED AS-IS from origin/new-horse:src/newhorse/grammar.py (read
capability-at-write-time in PROPOSAL_REASONING_GATE.md, "THE GRAMMAR SALVAGE
READING"): the five world types (OBJECT / ATTR / REGION / PRED / OBJ), the 13
typed primes with their signatures, compose()'s discipline (an ill-typed
composition RAISES with its reason, never silently) and the typed hole (a
bare type as a leaf = a template without content). NOT carried: the
molecules (three goal templates), the search-space counters, the
single-terminal structure. Content-free throughout: nothing here knows what
any game wants.

AUTHORED NEW -- the speech-act layer, which encodes the loop (and the loop
did not exist when the primes were written):
  * two types: RECORD (a citable id: a gate PERCEIVE/BET/ACT utterance, a
    Gamma atom, a composite) and PRICE (a cost claim: a number with its
    evidence count, or an explicit null);
  * nine heads, each with ONE check-kind riding the head (the gate module
    runs the check; this module only types it): SEE, CHANGED, SETTLE, STAND,
    WANT, GROUND, DERIVE, PAY, NEED;
  * three terminals that PRODUCE a RECORD when emitted -- PERCEIVE, BET,
    ACT -- so precedence is type-checkable: a later terminal can only consume
    what an earlier one produced (BET's GROUND consumes a PERCEIVE record;
    ACT's NEED consumes a BET record).

THE BASIS RULE applies to the new layer: heads grow or merge ONLY on a
composition failure surfaced as a refusal with a named head. Nine is a
hypothesis stage 1 tests; nothing here decides it in advance.

Signatures may carry ONE starred position (the prereg's `*` / `+`): the type
at that index repeats zero or more times; `+` (at least one) is a terminal-
level rule (a non-probe DERIVE with no atoms is ill-typed there), because the
probe form legitimately cites none. RECORD *kinds* (perceive / bet / act /
atom / composite) are NOT types: a wrong kind is a LEDGER refusal at the
gate, a wrong TYPE is a parse refusal here (prereg F2: GROUND citing a
non-RECORD is ill-typed; NEED citing a PERCEIVE is a ledger refusal).

Stdlib only; deterministic; no numpy.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

__all__ = ["T", "Prime", "Term", "Leaf", "TypeError_", "PRIMES", "HEADS",
           "TERMINALS", "KANT_CATEGORIES", "CHECK_EXECUTABLE", "CHECK_LEDGER",
           "CHECK_COMPLETENESS", "CHECK_LEDGER_EXECUTABLE", "CHECK_KINDS",
           "SEE", "CHANGED", "SETTLE", "STAND", "WANT", "GROUND", "DERIVE",
           "PAY", "NEED", "PERCEIVE", "BET", "ACT", "compose", "is_hole",
           "is_objective", "type_of", "head_check", "ref", "price"]


class T(Enum):
    # -- the salvaged world types (new-horse, verbatim) --
    OBJECT = "OBJECT"     # a perceived object / its identity
    ATTR = "ATTR"         # an attribute value (colour, shape, orientation, position)
    REGION = "REGION"     # a set of cells / an area / a target locus
    PRED = "PRED"         # a relation that holds or not (a hub type)
    OBJ = "OBJ"           # a complete objective (a quantified relation) -- the goal type
    # -- the speech-act types (authored new) --
    RECORD = "RECORD"     # a citable id: gate utterance, Gamma atom, composite
    PRICE = "PRICE"       # a cost claim: (number, evidence n) or an explicit null


class TypeError_(TypeError):
    """An ill-typed composition. Raised with its reason -- never silent."""


# the check-kind that rides each speech-act head (the gate runs it)
CHECK_EXECUTABLE = "executable"
CHECK_LEDGER = "ledger"
CHECK_COMPLETENESS = "completeness"
CHECK_LEDGER_EXECUTABLE = "ledger+executable"
CHECK_KINDS = (CHECK_EXECUTABLE, CHECK_LEDGER, CHECK_COMPLETENESS,
               CHECK_LEDGER_EXECUTABLE)


@dataclass(frozen=True)
class Prime:
    name: str
    category: str                 # Kant category (salvaged) or "Speech-act" / "Terminal"
    in_types: Tuple[T, ...]       # what it consumes
    out_type: T                   # what it produces -- the signature that makes it TYPED
    gloss: str = ""
    check: Optional[str] = None   # speech-act heads only: the ONE check-kind
    star: Optional[int] = None    # index of the repeating position, if any


def _P(*a: Any, **k: Any) -> Prime:
    return Prime(*a, **k)


# --- THE PRIME BASIS (new-horse, salvaged verbatim), each with a TYPE SIGNATURE -------------
PRIMES: Dict[str, Prime] = {p.name: p for p in [
    # Relation primes: build a PRED from objects/attrs/regions
    _P("BE_AT", "Relation", (T.OBJECT, T.REGION), T.PRED, "an object is located at a region"),
    _P("TOUCH", "Relation", (T.OBJECT, T.OBJECT), T.PRED, "two objects are in contact"),
    _P("BECOME", "Relation", (T.OBJECT, T.ATTR), T.PRED, "an object takes a target attribute"),
    _P("BECAUSE", "Relation", (T.PRED, T.PRED), T.PRED, "one relation causes another"),
    # Quality primes: build/compare ATTR and negate PRED
    _P("SAME", "Quality", (T.ATTR, T.ATTR), T.PRED, "two attributes are equal"),
    _P("OTHER", "Quality", (T.ATTR, T.ATTR), T.PRED, "two attributes differ"),
    _P("NOT", "Quality", (T.PRED,), T.PRED, "negation of a relation"),
    _P("EXIST", "Modality", (T.OBJECT,), T.PRED, "an object exists"),
    _P("CAN", "Modality", (T.PRED,), T.PRED, "a relation is achievable (affordance)"),
    # Quantity primes: close a PRED over a scope into a complete OBJ (the goal)
    _P("ALL", "Quantity", (T.PRED,), T.OBJ, "the relation holds for all in scope"),
    _P("SOME", "Quantity", (T.PRED,), T.OBJ, "the relation holds for some in scope"),
    _P("ONE", "Quantity", (T.PRED,), T.OBJ, "the relation holds for exactly one"),
    _P("NONE", "Quantity", (T.PRED,), T.OBJ, "the relation holds for none"),
]}
KANT_CATEGORIES = sorted({p.category for p in PRIMES.values()})


# --- THE SPEECH-ACT HEADS (authored new): signature -> type, check-kind riding the head --------
SEE, CHANGED, SETTLE, STAND = "SEE", "CHANGED", "SETTLE", "STAND"
WANT, GROUND, DERIVE, PAY, NEED = "WANT", "GROUND", "DERIVE", "PAY", "NEED"

HEADS: Dict[str, Prime] = {p.name: p for p in [
    # PERCEIVE's clauses
    _P(SEE, "Speech-act", (T.OBJECT, T.REGION, T.ATTR), T.PRED,
       "per-slot state claim: this one, at this region, shows this attribute",
       check=CHECK_EXECUTABLE),
    _P(CHANGED, "Speech-act", (T.REGION, T.ATTR, T.ATTR), T.PRED,
       "a region went a -> b since the previous opener; the set asserts nothing else changed",
       check=CHECK_COMPLETENESS),
    _P(SETTLE, "Speech-act", (T.RECORD, T.PRED), T.PRED,
       "the previous step's bet by id: held or broke, by d",
       check=CHECK_LEDGER_EXECUTABLE),
    _P(STAND, "Speech-act", (T.RECORD, T.ATTR), T.PRED,
       "a held id strengthened / weakened / died this step",
       check=CHECK_LEDGER),
    # BET's clauses
    _P(WANT, "Speech-act", (T.OBJ,), T.PRED,
       "the goal: consumes the salvaged OBJ; compiles to a Discrepancy non-zero on the opener",
       check=CHECK_EXECUTABLE),
    _P(GROUND, "Speech-act", (T.RECORD, T.RECORD), T.PRED,
       "pure citation: this step's perceive, then held atoms / settled composites",
       check=CHECK_LEDGER, star=1),
    _P(DERIVE, "Speech-act", (T.PRED, T.RECORD, T.PRED), T.PRED,
       "the executable step: cited records applied to the ground equal the bet "
       "(positive / inverse / negative); a typed hole in the bet position is the probe",
       check=CHECK_EXECUTABLE, star=1),
    _P(PAY, "Speech-act", (T.PRICE,), T.PRED,
       "the acknowledged cost, from the action book with its evidence n, or the explicit null",
       check=CHECK_LEDGER),
    # ACT's clause (the action int rides an ATTR leaf; anchor as data)
    _P(NEED, "Speech-act", (T.RECORD, T.ATTR), T.PRED,
       "this step's bet by id, and the action it ran or the probe names",
       check=CHECK_LEDGER),
]}

# --- THE TERMINALS: each PRODUCES a RECORD -- precedence becomes type-checkable -----------------
PERCEIVE, BET, ACT = "PERCEIVE", "BET", "ACT"

# admitted clause heads per terminal; BET and ACT are fixed in order, PERCEIVE
# is a set with SETTLE at most once (the prereg's SEE*, CHANGED*, SETTLE?, STAND*)
TERMINALS: Dict[str, Prime] = {p.name: p for p in [
    _P(PERCEIVE, "Terminal", (T.PRED,), T.RECORD,
       "SEE*, CHANGED*, SETTLE?, STAND* -> a citable perceive record", star=0),
    _P(BET, "Terminal", (T.PRED, T.PRED, T.PRED, T.PRED), T.RECORD,
       "WANT, GROUND, DERIVE, PAY -> a citable bet record"),
    _P(ACT, "Terminal", (T.PRED,), T.RECORD, "NEED -> a citable act record"),
]}
_PERCEIVE_HEADS = (SEE, CHANGED, SETTLE, STAND)
_BET_ORDER = (WANT, GROUND, DERIVE, PAY)
_ACT_ORDER = (NEED,)


@dataclass(frozen=True)
class Leaf:
    """A typed VALUE leaf (the salvaged grammar had only holes). `kind` tags a
    RECORD's kind (perceive / bet / act / atom / composite) and `tag` an
    atom's memory range -- both are data the gate's LEDGER checks; neither
    is a type."""
    type: T
    value: Any
    kind: Optional[str] = None
    tag: Optional[str] = None


@dataclass(frozen=True)
class Term:
    """A typed composition tree. Its type is head.out_type; constructed only
    if args type-check (compose)."""
    head: str
    args: Tuple = ()

    @property
    def type(self) -> T:
        return _prime(self.head).out_type


def _prime(head: str) -> Prime:
    p = PRIMES.get(head) or HEADS.get(head) or TERMINALS.get(head)
    if p is None:
        raise TypeError_("unknown head '%s'" % head)
    return p


def is_hole(x: Any) -> bool:
    return isinstance(x, T)


def type_of(x: Any) -> T:
    if isinstance(x, Term):
        return x.type
    if isinstance(x, Leaf):
        return x.type
    if isinstance(x, T):
        return x                     # a bare typed hole (a leaf of a given type)
    raise TypeError_("not a typed value: %r" % (x,))


def _types(args: Tuple) -> Tuple[T, ...]:
    return tuple(type_of(a) for a in args)


def _signature_matches(sig: Tuple[T, ...], star: Optional[int],
                       got: Tuple[T, ...]) -> bool:
    if star is None:
        return got == sig
    pre, rep, post = sig[:star], sig[star], sig[star + 1:]
    if len(got) < len(pre) + len(post):
        return False
    mid = got[len(pre):len(got) - len(post)] if post else got[len(pre):]
    return (got[:len(pre)] == pre
            and (got[len(got) - len(post):] == post if post else True)
            and all(t == rep for t in mid))


def _render_sig(p: Prime) -> Tuple[str, ...]:
    out = []
    for i, t in enumerate(p.in_types):
        out.append(t.value + ("*" if p.star == i else ""))
    return tuple(out)


def compose(head: str, *args: Any) -> Term:
    """Type-checked composition (the salvaged discipline): raises TypeError_
    with its reason -- never silently -- if the args do not match the head's
    signature. Terminals additionally check their clause grammar."""
    p = _prime(head)
    got = _types(tuple(args))
    if not _signature_matches(p.in_types, p.star, got):
        raise TypeError_("ill-typed: %s expects %s but got %s"
                         % (head, _render_sig(p), tuple(t.value for t in got)))
    if head in TERMINALS:
        _check_terminal(head, args)
    return Term(head, tuple(args))


def _check_terminal(head: str, args: Tuple) -> None:
    heads = tuple(a.head if isinstance(a, Term) else None for a in args)
    if head == PERCEIVE:
        bad = [h for h in heads if h not in _PERCEIVE_HEADS]
        if bad:
            raise TypeError_("ill-typed: PERCEIVE admits %s, got %s"
                             % (_PERCEIVE_HEADS, bad[0]))
        if heads.count(SETTLE) > 1:
            raise TypeError_("ill-typed: PERCEIVE settles at most one bet (SETTLE?)")
        return
    order = _BET_ORDER if head == BET else _ACT_ORDER
    if heads != order:
        raise TypeError_("ill-typed: %s is %s in order, got %s" % (head, order, heads))
    if head == BET:
        want, derive = args[0], args[2]
        holed_want = is_hole(want.args[0])
        probe = is_hole(derive.args[-1])
        if holed_want and not probe:
            raise TypeError_("ill-typed: DERIVE against a holed WANT (a hole composes "
                             "with a probe only)")
        if not probe and len(derive.args) < 3:
            raise TypeError_("ill-typed: DERIVE cites no record (RECORD[atom]+) "
                             "and is not a probe")


def is_objective(t: Any) -> bool:
    return isinstance(t, Term) and t.type is T.OBJ


def head_check(head: str) -> Optional[str]:
    """The check-kind riding a speech-act head (None for primes/terminals)."""
    return _prime(head).check


# -- leaf constructors for the two new types (data rides the leaf; the gate reads it) --------

def ref(record_id: Any, kind: str, tag: Optional[str] = None) -> Leaf:
    """A RECORD leaf: a citable id with its kind (perceive/bet/act/atom/composite)."""
    return Leaf(T.RECORD, str(record_id), kind=str(kind), tag=tag)


def price(value: Optional[float], n: Optional[int] = None,
          reason: Optional[str] = None) -> Leaf:
    """A PRICE leaf: (number, evidence n) or the explicit null (None, reason).
    A number without evidence is representable here and REFUSED by the gate
    (price-invented) -- the grammar states it, the ledger refuses it."""
    return Leaf(T.PRICE, (value, n, reason))
