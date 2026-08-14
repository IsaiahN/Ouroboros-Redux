"""W4 B16: the OOD lint — "no id-based nonsense... everything transfers out of distribution".

Full-scan (never diff-scan) of PRODUCTION sources — engines/**, cognitive_loop.py,
cognitive_game_player.py; NOT tests, NOT tools — for three smells that encode answers:

  (a) GAME-ID LITERALS: a hardcoded game-id-shaped string ([a-z]{2}\\d{2}, optionally
      with the -<hex> session suffix) in production code is a trained answer. Runtime
      keying by VARIABLES (game=self._game_id, per-game dict keys built from data) is
      legitimate and never flagged — the mechanics transfer, the keys are data.
      Docstrings are commentary, not behavior: skipped.
  (b) ABSOLUTE-COORDINATE MAGIC: a literal pair of ints both > 8 (e.g. (12, 44)) reads
      as a memorized board coordinate. Heuristic by design — pairs inside obvious
      geometry/array math (range/zeros/ones/full/empty/reshape/arange calls, .shape
      comparisons) are skipped, and any flagged line can carry an inline waiver:
          ... # ood: <reason why this is geometry, not an answer>
  (c) LEVEL SPECIAL-CASING: comparing a level variable to a literal level > 1
      (if level == 3: ...) is per-level answer-keying. Gate reads like level >= 1 and
      counts like levels_completed are not flagged.

The 25-game ops list may live ONLY in tools/ (launcher config, not agent knowledge);
its occurrences there are reported as INFO, never as flags.

Output: one line per flag (file:line [CATEGORY] detail), waivers listed, then a verdict
line. Exit 1 on any unwaived flag. Stdlib only; dev-time tool, never imported by agents.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRODUCTION_FILES = ("cognitive_loop.py", "cognitive_game_player.py")
PRODUCTION_DIRS = ("engines",)

# The ops list (acceptable ONLY as launcher config in tools/ — reported as INFO there).
KNOWN_GAMES = ("ar25", "bp35", "cd82", "cn04", "dc22", "ft09", "g50t", "ka59", "lf52",
               "lp85", "ls20", "m0r0", "r11l", "re86", "s5i5", "sb26", "sc25", "sk48",
               "sp80", "su15", "tn36", "tr87", "tu93", "vc33", "wa30")

GAME_ID_FULL = re.compile(r"^[a-z]\d?[a-z0-9]\d{2}(-[0-9a-f]{4,})?$")
GAME_ID_SHAPE = re.compile(r"^[a-z]{2}\d{2}(-[0-9a-f]{4,})?$")
KNOWN_WORD = re.compile(r"\b(%s)\b" % "|".join(KNOWN_GAMES))
WAIVER = re.compile(r"#\s*ood:\s*(\S.*)")

COORD_MIN = 9                     # both members of a literal pair >= this -> suspicious
COORD_MAX = 127                   # boards are 64x64; beyond this it is config, not a cell
GEOMETRY_CALLS = {"range", "zeros", "ones", "full", "empty", "reshape", "arange",
                  "linspace", "randint", "tile", "repeat"}
GEOMETRY_NAMES = ("shape", "size", "dim", "bound", "extent")   # assignment-target words
LEVEL_NAMES = {"level", "lvl", "lv", "cur_level", "current_level"}


def production_sources(root):
    files = [os.path.join(root, f) for f in PRODUCTION_FILES
             if os.path.isfile(os.path.join(root, f))]
    for d in PRODUCTION_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, d)):
            dirnames[:] = [x for x in dirnames if x != "__pycache__"]
            files.extend(os.path.join(dirpath, f) for f in filenames if f.endswith(".py"))
    return sorted(files)


def _docstring_nodes(tree):
    """The Constant nodes that are documentation, not behavior."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def _parents(tree):
    par = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            par[id(child)] = node
    return par


def _int_of(node):
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int):
        return -node.operand.value
    return None


def _in_geometry_context(node, parents):
    """Climb ancestors: literal pairs inside obvious array/geometry math are fine."""
    cur = node
    for _ in range(12):                       # bounded climb; enough for real nesting
        cur = parents.get(id(cur))
        if cur is None:
            return False
        if isinstance(cur, ast.Call):
            fn = cur.func
            name = fn.id if isinstance(fn, ast.Name) else (
                fn.attr if isinstance(fn, ast.Attribute) else "")
            if name in GEOMETRY_CALLS:
                return True
        if isinstance(cur, ast.Compare):
            for sub in ast.walk(cur):
                if isinstance(sub, ast.Attribute) and sub.attr == "shape":
                    return True
        if isinstance(cur, (ast.Assign, ast.AnnAssign)):
            targets = cur.targets if isinstance(cur, ast.Assign) else [cur.target]
            for t in targets:
                for sub in ast.walk(t):
                    name = (sub.id if isinstance(sub, ast.Name) else
                            sub.attr if isinstance(sub, ast.Attribute) else "")
                    if any(w in name.lower() for w in GEOMETRY_NAMES):
                        return True
    return False


def _level_side(node):
    """True when a comparator subtree references a level VARIABLE (not a count)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id.lower() in LEVEL_NAMES:
            return True
        if isinstance(sub, ast.Attribute) and sub.attr.lower() in LEVEL_NAMES:
            return True
    return False


def scan_file(path, root):
    """-> (flags, waived) lists of (relpath, lineno, category, detail)."""
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    lines = src.splitlines()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [(rel, e.lineno or 0, "PARSE", "unparseable production source: %s" % e)], []
    docs = _docstring_nodes(tree)
    parents = _parents(tree)
    hits = []

    for node in ast.walk(tree):
        # (a) game-id-shaped string literals ------------------------------------
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docs):
            s = node.value
            if GAME_ID_SHAPE.match(s):
                hits.append((rel, node.lineno, "GAME-ID",
                             "hardcoded game-id-shaped literal %r" % s))
            elif len(s) < 400 and KNOWN_WORD.search(s):
                hits.append((rel, node.lineno, "GAME-ID",
                             "known game id %r inside literal %r"
                             % (KNOWN_WORD.search(s).group(0), s[:60])))
        # (b) absolute-coordinate magic pairs -----------------------------------
        elif isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) == 2:
            a, b = (_int_of(e) for e in node.elts)
            if (a is not None and b is not None
                    and COORD_MIN <= abs(a) <= COORD_MAX
                    and COORD_MIN <= abs(b) <= COORD_MAX
                    and not _in_geometry_context(node, parents)):
                hits.append((rel, node.lineno, "COORD",
                             "literal pair (%d, %d) reads as an absolute coordinate"
                             % (a, b)))
        # (c) level-number special-casing ---------------------------------------
        elif isinstance(node, ast.Compare):
            sides = [node.left, *node.comparators]
            consts = [v for v in (_int_of(s) for s in sides) if v is not None]
            if any(v > 1 for v in consts) and any(_level_side(s) for s in sides
                                                  if _int_of(s) is None):
                hits.append((rel, node.lineno, "LEVEL",
                             "level variable compared to literal %d — per-level "
                             "special-casing" % max(consts)))

    flags, waived = [], []
    for rel_, ln, cat, detail in hits:
        line = lines[ln - 1] if 0 < ln <= len(lines) else ""
        m = WAIVER.search(line)
        if m:
            waived.append((rel_, ln, cat, detail + " [waived: %s]" % m.group(1).strip()))
        else:
            flags.append((rel_, ln, cat, detail + (" | %s" % line.strip() if line else "")))
    return flags, waived


def ops_list_info(root):
    """INFO: where the 25-game list ids appear under tools/ (acceptable ops config)."""
    info = []
    tdir = os.path.join(root, "tools")
    if not os.path.isdir(tdir):
        return info
    for dirpath, dirnames, filenames in os.walk(tdir):
        dirnames[:] = [x for x in dirnames if x != "__pycache__"]
        for f in filenames:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dirpath, f)
            with open(p, encoding="utf-8", errors="replace") as fh:
                n = len(KNOWN_WORD.findall(fh.read()))
            if n:
                info.append((os.path.relpath(p, root).replace(os.sep, "/"), n))
    return info


def main(argv=None):
    ap = argparse.ArgumentParser(description="OOD lint: no id-based nonsense in production")
    ap.add_argument("--root", default=REPO, help="repo root to scan (default: this repo)")
    args = ap.parse_args(argv)

    flags, waived = [], []
    files = production_sources(args.root)
    for path in files:
        f, w = scan_file(path, args.root)
        flags.extend(f)
        waived.extend(w)

    print("OOD LINT — full scan of %d production sources" % len(files))
    for rel, ln, cat, detail in flags:
        print("  FLAG %s:%d [%s] %s" % (rel, ln, cat, detail))
    for rel, ln, cat, detail in waived:
        print("  ok   %s:%d [%s] %s" % (rel, ln, cat, detail))
    for rel, n in ops_list_info(args.root):
        print("  INFO tools ops-config: %s carries %d known-game-id mentions "
              "(acceptable ONLY here)" % (rel, n))
    if flags:
        print("OOD VERDICT: %d FLAG(S) — id-based nonsense in production (fix or waive "
              "with '# ood: <reason>')" % len(flags))
        return 1
    print("OOD VERDICT: CLEAN (%d waiver(s) documented)" % len(waived))
    return 0


if __name__ == "__main__":
    sys.exit(main())
