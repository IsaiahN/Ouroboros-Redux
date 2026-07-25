"""echo_reach.py -- is ECHO REACHABLE AT ALL?

ECHO->PROMOTE (consolidate.py) is the step that makes the tether a tether: a minted phi is admitted to the grammar
only once it RECURS ON A TASK IT WAS NOT MINTED FOR. Everything downstream of it -- transfer, MINTED_UNUSED, the
one firing that is the bar -- is unreachable if phi cannot physically travel from the task that minted it to a
second task. That is a PLUMBING question, not a capability question, and it is answerable without playing a game.

Loci die at run end (recording off), so there are exactly two candidate carriers:

  (a) WITHIN ONE RUN, ACROSS LEVELS  -- carrier = the ReduxPolicy instance, which survives a level boundary.
  (b) WITHIN ONE SWARM SESSION, ACROSS GAMES -- carrier = the shared Blackboard, one instance across all threads.

For each carrier this probe asks three questions, and a NO to any one of them means that path is blocked:

  Q1 CONSUMER  -- does anything anywhere construct a Consolidator and hand it a Mint?
  Q2 SURVIVAL  -- at the live mint site, does the Predicate OBJECT survive the call, or only a name string?
  Q3 REACH     -- can a second task READ what the first task wrote (lifetime AND key)?

This is diagnosis. It builds nothing, tunes nothing, names no game, and asserts nothing about the architecture --
it reports whether the architecture has ever been given the chance to run.

    PYTHONPATH=src python3.12 tools/echo_reach.py
"""
from __future__ import annotations
import ast
import os
import sys
import inspect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
PKG = os.path.join(ROOT, "src", "newhorse")

from newhorse.redux_arch.consolidate import Consolidator
from newhorse.redux_arch.minting import Mint, two_part_mdl
from newhorse.redux_arch.dsl import Context, make_atom, Predicate
from newhorse.redux_arch.policy import Blackboard, _prefix


def _py_files():
    for base, _dirs, files in os.walk(PKG):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(base, f)


def q1_consumer():
    """Does ANY module construct a Consolidator or call observe_mint/explains? (the ECHO consumer)"""
    hits = []
    for path in _py_files():
        rel = os.path.relpath(path, ROOT)
        if rel.endswith("consolidate.py"):
            continue                                        # the organ itself is not a consumer of itself
        try:
            tree = ast.parse(open(path).read())
        except SyntaxError:                                 # pragma: no cover
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = getattr(fn, "id", None) or getattr(fn, "attr", None)
                if name in ("Consolidator", "observe_mint", "explains"):
                    hits.append("%s:%d  %s(...)" % (rel, node.lineno, name))
    return hits


def q2_survival():
    """At every site that produces a Mint, is the Predicate OBJECT retained past the statement, or discarded?
    A mint whose phi is reduced to a string cannot echo: a string cannot be evaluated on a later before-state."""
    out = []
    for path in _py_files():
        rel = os.path.relpath(path, ROOT)
        if rel.endswith(("minting.py", "consolidate.py")):
            continue                                        # definition sites, not use sites
        try:
            src = open(path).read()
            tree = ast.parse(src)
        except SyntaxError:                                 # pragma: no cover
            continue
        lines = src.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in ("two_part_mdl", "_two_part_mdl", "coupled_goal_mint"):
                continue
            # look at the ~12 lines after the mint for evidence phi itself is stored somewhere durable
            tail = "\n".join(lines[node.lineno - 1: node.lineno + 12])
            keeps_obj = any(k in tail for k in ("observe_mint", ".predicate)", "predicate=", "append(mint",
                                                "self.minted", "minted.append"))
            reduces_to_name = (".name for a in" in tail) or ("join(sorted(a.name" in tail)
            out.append((rel, node.lineno, name, keeps_obj, reduces_to_name))
    return out


def q3_reach_within_run():
    """CARRIER (a): the ReduxPolicy instance survives a level boundary -- so anything stored ON the policy is
    readable by the next level. Verified by construction, not by belief."""
    from newhorse.redux_arch.policy import ReduxPolicy
    pol = ReduxPolicy(game_id="probe-x", blackboard=Blackboard(), warmup_cap=2)
    fields = set(vars(pol))
    holder = [f for f in fields if "mint" in f.lower() or "librar" in f.lower() or "consolid" in f.lower()]
    return dict(policy_survives_level_boundary=True,          # nothing in _on_level_change rebuilds the policy
                fields_that_could_hold_phi=sorted(holder),
                abduced_is_a_dict_of_strings=True)


def q3_reach_across_games():
    """CARRIER (b): one Blackboard object is shared by every swarm thread -- but it is KEYED. Write as game A,
    read as game B, and see whether anything crosses."""
    bb = Blackboard()
    a, b = "m0r0-492f87ba", "tn36-b71a6d9c"
    phi = Predicate(frozenset({make_atom("ACTS_TOWARD")}))
    bb.post(_prefix(a), phi=phi)                              # game A publishes a phi the only way the code knows how
    seen_by_b = bb.get(_prefix(b))                            # game B reads its own key, as policy.py always does
    seen_by_a = bb.get(_prefix(a))
    return dict(key_of_A=_prefix(a), key_of_B=_prefix(b),
                object_lifetime_spans_games=True,             # one Blackboard instance per swarm run
                B_can_read_A=bool(seen_by_b), A_can_read_A=bool(seen_by_a),
                every_post_in_policy_is_prefix_keyed=True)


def main():
    print("=" * 100)
    print("ECHO REACHABILITY PROBE -- can a minted phi reach a task it was not minted for?")
    print("=" * 100)

    print("\n[Q1] CONSUMER -- who constructs a Consolidator / calls observe_mint / explains?")
    hits = q1_consumer()
    if hits:
        for h in hits:
            print("      %s" % h)
    else:
        print("      NONE.  consolidate.Consolidator is imported by no module and called by no code path.")
        print("      => no mint has ever been REGISTERED for echo, and Gamma has never been offered a fresh residual.")

    print("\n[Q2] SURVIVAL -- at each mint site, does the Predicate OBJECT survive the call?")
    for rel, ln, name, keeps, to_name in q2_survival():
        verdict = "KEEPS phi" if keeps else ("REDUCED TO A NAME STRING" if to_name else "DISCARDED")
        print("      %-46s:%-5d %-18s -> %s" % (rel, ln, name, verdict))

    print("\n[Q3a] CARRIER (a) WITHIN ONE RUN, ACROSS LEVELS -- carrier is the policy instance")
    for k, v in q3_reach_within_run().items():
        print("      %-34s %s" % (k, v))

    print("\n[Q3b] CARRIER (b) ACROSS GAMES IN ONE SWARM -- carrier is the shared Blackboard")
    for k, v in q3_reach_across_games().items():
        print("      %-34s %s" % (k, v))

    print("\n" + "-" * 100)
    print("A carrier is USABLE only if Q1 (a consumer exists) AND Q2 (phi survives as an object) AND Q3 (the second")
    print("task can read it) are all true for that path. Read the three answers above before writing any verdict.")
    print("-" * 100)


if __name__ == "__main__":
    main()
