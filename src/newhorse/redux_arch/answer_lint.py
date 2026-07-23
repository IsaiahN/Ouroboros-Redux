"""
answer_lint.py -- a MECHANICAL guard for the "never encode the answer" law. No LLM judgement: a rule the build
cannot argue with. It scans the AGENT-LOGIC modules for game-specific encoding, so a future beat that special-cases
a game (a game-id literal, or behaviour branching on game_id) turns the suite RED.

This is the externalised ground-maintainer for BUILD honesty (Tether §1.5: a frame cannot grade its own exam — so
the exam is a rule, not the frame's own judgement). It is the tripwire that lets a human step back from the loop and
AUDIT on return instead of having to trust the LLM's self-report: the LLM writes the code, but it cannot make this
check pass while cheating, and the check runs every beat.

AGENT-LOGIC modules must be game-agnostic. RUNNERS / adapters legitimately name games (default args, reasoning
strings) and are exempt. The linter MAY know the dev game codes (it is a guard); the AGENT may not mention them.
"""
from __future__ import annotations
import ast
import os
import re
from typing import List, Tuple

# The domain-general agent. If behaviour here depends on WHICH game it is, the generalisation claim is false.
AGENT_MODULES = ["policy.py", "coupled.py", "replay.py", "click.py", "goal.py", "planner.py", "bridge.py",
                 "explore.py", "dsl.py", "minting.py", "consolidate.py"]
# Runners/adapters/entrypoints: they name games as defaults or in logs; not agent logic.
RUNNER_EXEMPT = ["live_goal_run.py", "swarm.py", "loop.py", "harness_adapter.py", "__init__.py", "answer_lint.py",
                 "novelty_ledger.py"]

# Known ARC-AGI-3 dev-set game codes. The AGENT must not mention any as a code literal.
DEV_GAME_CODES = ["m0r0", "ka59", "s5i5", "lp85", "tn36", "vc33", "r11l", "ft09", "su15", "sb26", "lf52", "sc25",
                  "re86", "tr87", "g50t", "cn04", "cd82", "ls20", "dc22", "sp80", "bp35", "sk48", "ar25", "wa30",
                  "tu93"]

_GAME_ID_FORM = re.compile(r"[a-z0-9]{4}-[0-9a-f]{8}")          # full game id, e.g. m0r0-492f87ba -- unmistakable
_GAME_BRANCH = re.compile(r"game_id\s*(==|!=|\bin\b)|(==|!=)\s*game_id")   # behaviour switching on the game id
_CODE_RES = [re.compile(r"\b" + re.escape(c) + r"\b") for c in DEV_GAME_CODES]


def _docstring_node_ids(tree: ast.AST) -> set:
    ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def lint_source(src: str) -> List[Tuple[int, str]]:
    """Return (lineno, reason) findings for one module's source. Empty = clean."""
    findings: List[Tuple[int, str]] = []
    tree = ast.parse(src)
    doc_ids = _docstring_node_ids(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
            s = node.value
            if _GAME_ID_FORM.search(s):
                findings.append((getattr(node, "lineno", 0), "full game-id literal in agent code: %r" % s))
                continue
            for c, rx in zip(DEV_GAME_CODES, _CODE_RES):
                if rx.search(s):
                    findings.append((getattr(node, "lineno", 0), "game-code %r encoded in string literal %r" % (c, s)))
                    break
    for i, line in enumerate(src.splitlines(), 1):
        code = line.split("#", 1)[0]                            # ignore comments
        if _GAME_BRANCH.search(code):
            findings.append((i, "agent behaviour branches on game_id: %s" % line.strip()))
    return findings


def lint_agent_dir(redux_arch_dir: str) -> List[Tuple[str, int, str]]:
    """Scan all AGENT_MODULES under redux_arch_dir. Return (module, lineno, reason). Empty = the agent is honest."""
    out: List[Tuple[str, int, str]] = []
    for mod in AGENT_MODULES:
        p = os.path.join(redux_arch_dir, mod)
        if not os.path.exists(p):
            continue
        for lineno, reason in lint_source(open(p, encoding="utf-8").read()):
            out.append((mod, lineno, reason))
    return out


if __name__ == "__main__":                                     # standalone: `python -m newhorse.redux_arch.answer_lint`
    here = os.path.dirname(os.path.abspath(__file__))
    problems = lint_agent_dir(here)
    if problems:
        print("ANSWER-ENCODING VIOLATIONS (the agent is not game-agnostic):")
        for mod, lineno, reason in problems:
            print("  %s:%d  %s" % (mod, lineno, reason))
        raise SystemExit(1)
    print("clean: no game-specific encoding in the agent-logic modules")
