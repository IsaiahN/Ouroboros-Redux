"""The Isaiah-approved crash fix: no local import may shadow module-level `random`.

Stock v4's _act contains a redundant local `import random`, making `random` function-local and
crashing every episode of any game whose _act path touches `random.` earlier -- measured: 3 of
25 games permanently on the fallback stack, 109 crashes across the sealed baseline.
"""
from __future__ import annotations
import ast, os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_no_function_local_random_import_shadows_the_module():
    src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
               errors="replace").read()
    tree = ast.parse(src)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Import):
                    for a in inner.names:
                        if a.name == "random" and (a.asname or "random") == "random":
                            offenders.append("%s:%d" % (node.name, inner.lineno))
    assert not offenders, (
        "function-local `import random` shadows the module and crashes the loop on any "
        "earlier `random.` use in the same function: %s" % offenders)
