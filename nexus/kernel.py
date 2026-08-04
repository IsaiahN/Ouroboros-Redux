"""nexus.kernel -- the bridge to the EGOCENTRIC half.

Nexus is a branch of Ouroboros-Redux, so the kernel already lives in this repo at
`src/newhorse/`. This module loads the REAL, in-repo typed predicate DSL (`redux_arch/dsl.py`)
and objective grammar (`grammar.py`) and exposes exactly what the other Nexus layers need:
the evaluable predicate space Γ (Context, Predicate, atoms, enumeration) plus a canonical
token serialization so the fluent proposer can be trained over Γ.

Nothing here re-implements the type system or the semantics. Validity and truth are decided by
the kernel's own code -- the same code the mint search uses. That is the point of the membrane:
the population never gets its own private notion of what a predicate is or whether it holds.
"""
from __future__ import annotations
import os, sys
from typing import List

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# THE KERNEL IMPORTS Γ. IT DOES NOT LOAD A SECOND COPY OF IT.
#
# Until 2026-08-04 these two lines were `importlib.util.spec_from_file_location(...)` calls that read
# `redux_arch/dsl.py` and `grammar.py` off disk and registered them under private names (`nexus_kernel_dsl`,
# `nexus_kernel_grammar`). Same source text, DIFFERENT module objects -- and therefore different classes.
# Measured, not argued: with both halves imported in one process,
#
#     newhorse.redux_arch.dsl.Predicate is nexus.kernel.Predicate   ->  False
#     isinstance(<a Predicate the live agent built>, kernel.Predicate) -> False
#     dsl._ATOM_TYPES is kernel._ATOM_TYPES                          ->  False
#
# So the docstring's claim -- "the population never gets its own private notion of what a predicate is" -- was
# true of the SOURCE and false of the RUNTIME. It is the mechanical reason the objective composer could never be
# routed through the proposer: the two halves cannot hand each other a predicate, because a predicate built on
# one side is not an instance of the other side's type, and the atom-type registry each side consults is a
# different dict. A double-loaded module is a reinvention that no grep can see.
#
# A plain import fixes it: one module object, one Γ, one registry. Nothing under `src/` imports `nexus`, so the
# live agent's behaviour cannot move -- and that asymmetry is what makes this edit provable rather than risky.
from newhorse.redux_arch import dsl as DSL                    # noqa: E402  (path set immediately above)
from newhorse import grammar as GRAMMAR                       # noqa: E402

Context   = DSL.Context
Atom      = DSL.Atom
Predicate = DSL.Predicate
make_atom = DSL.make_atom
atom_universe = DSL.atom_universe
enumerate_predicates = DSL.enumerate_predicates
predicate_family = DSL.predicate_family
_ATOM_TYPES = DSL._ATOM_TYPES

# ---- canonical token serialization of a Predicate (for the fluent proposer) -------------------
# A predicate is a conjunction of typed atoms. Tokens are atom KINDS plus colour-argument tokens
# (C<n>), joined by '&'. Canonical order = sorted atom names, so one predicate <-> one string.
_COLOUR_KINDS = {"HAS_COLOUR", "INTENDED_COLOUR"}

def atom_tokens(atom) -> List[str]:
    if atom.kind in _COLOUR_KINDS:
        # name looks like "colour==2" or "INTENDED_COLOUR==2"; recover the int
        c = int(atom.name.split("==")[1])
        return [atom.kind, "C%d" % c]
    return [atom.kind]

def serialize(pred) -> List[str]:
    toks: List[str] = []
    for a in sorted(pred.atoms, key=lambda x: x.name):
        if toks:
            toks.append("&")
        toks += atom_tokens(a)
    return toks

def parse(tokens: List[str]):
    """Parse a token list back into a Predicate through the kernel's make_atom (raises on invalid)."""
    atoms = []
    for part in _split(tokens, "&"):
        if not part:
            raise ValueError("empty conjunct")
        kind = part[0]
        if kind in _COLOUR_KINDS:
            if len(part) != 2 or not part[1].startswith("C"):
                raise ValueError("colour atom needs a C<n> arg: %r" % part)
            atoms.append(make_atom(kind, int(part[1][1:])))
        else:
            if len(part) != 1:
                raise ValueError("relational atom takes no args: %r" % part)
            atoms.append(make_atom(kind))          # kind unknown -> make_atom raises (the type gate)
    return Predicate(frozenset(atoms))

def is_valid(tokens: List[str]) -> bool:
    try:
        parse(tokens); return True
    except Exception:
        return False

def _split(seq, sep):
    cur, out = [], []
    for x in seq:
        if x == sep:
            out.append(cur); cur = []
        else:
            cur.append(x)
    out.append(cur)
    return out

def vocab_for(colours) -> List[str]:
    """The fixed DSL-native alphabet over a colour palette: specials + '&' + atom kinds + C<n>."""
    kinds = sorted(_ATOM_TYPES.keys())
    cols = ["C%d" % c for c in sorted(set(int(x) for x in colours))]
    return ["<pad>", "<bos>", "<eos>", "&"] + kinds + cols

if __name__ == "__main__":
    preds = enumerate_predicates([1, 2, 3], max_size=2)
    print("enumerated predicates:", len(preds))
    p = preds[20]
    toks = serialize(p)
    print("example:", str(p), "->", toks, "-> roundtrip ok:", str(parse(toks)) == str(p))
    print("vocab:", vocab_for([1, 2, 3]))
