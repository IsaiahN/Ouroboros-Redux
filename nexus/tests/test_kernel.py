"""The kernel bridge: serialize/parse round-trips through the REAL dsl.py, and enumeration yields
evaluable predicates. Validity is the kernel's, not ours."""
from nexus import kernel


def test_serialize_parse_roundtrip():
    preds = kernel.enumerate_predicates([1, 2, 3], max_size=2)
    for p in preds:
        toks = kernel.serialize(p)
        assert kernel.is_valid(toks)
        assert str(kernel.parse(toks)) == str(p)


def test_invalid_tokens_rejected():
    assert not kernel.is_valid(["NOT_A_KIND"])
    assert not kernel.is_valid(["HAS_COLOUR"])          # colour atom missing its C<n> arg
    assert not kernel.is_valid(["NEAR", "C1"])          # relational atom takes no arg


def test_enumerated_predicates_are_evaluable():
    from nexus.ground.rlvr import sample_contexts
    ctxs = sample_contexts([1, 2, 3], 10)
    for p in kernel.enumerate_predicates([1, 2, 3], max_size=2)[:20]:
        assert isinstance(p.holds(ctxs[0]), bool)      # a predicate is a Context -> bool
