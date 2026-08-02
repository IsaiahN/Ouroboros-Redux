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
import importlib.util, os, sys
from typing import List

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO, "src")

def _load(mod_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(_SRC, rel_path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = m
    spec.loader.exec_module(m)
    return m

# the kernel's evaluable predicate DSL Γ (redux_arch/dsl.py) and the objective grammar
DSL = _load("nexus_kernel_dsl", os.path.join("newhorse", "redux_arch", "dsl.py"))
GRAMMAR = _load("nexus_kernel_grammar", os.path.join("newhorse", "grammar.py"))

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
