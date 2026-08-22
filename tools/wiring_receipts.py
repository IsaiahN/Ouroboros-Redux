"""SYMBOL-ANCHORED RECEIPTS -- the fingerprint grammar, its resolver, and the
three registry operations (PREREG_SYMBOL_RECEIPTS.md).

THE DEFECT THIS CLOSES. record/canon/WIRING_REGISTRY.md stores a claim about STRUCTURE
("this organ is called from inside that function") as a POSITION
(``file:line``, checked +/-30 lines). Every insertion above the position
invalidates the claim without touching the fact: ~140 receipt refreshes this
week, zero of them a broken wire. A receipt nothing can break is not a check.

THE CELL (six columns kept -- the 6-field unpack that caught the concatenation
defect stays)::

    file:ENCLOSING/KIND:NAME#ORDINAL@LINE

* ``ENCLOSING`` -- the innermost ``def``/``class`` QUALNAME containing the
  site; ``<module>`` at top level.
* ``KIND`` -- ``CALL`` (an ``ast.Call`` whose ``func`` is a ``Name``/
  ``Attribute`` named NAME), ``REF`` (a ``Name``/``Attribute`` of NAME that is
  NOT a call's ``func`` -- constants and annotations), ``DEF`` (the definition
  itself: a ``def``/``class`` statement or a module/class-level assignment).
* ``ORDINAL`` -- 0-based index among same-KIND same-NAME nodes whose INNERMOST
  enclosing scope is ENCLOSING, in ``(lineno, col_offset)`` order.
* ``@LINE`` -- A COURTESY. Never asserted by the gate. It exists so a reader
  can jump to the site and so ``demote`` can restore the old form exactly.

WHY THE ORDINAL COUNTS ONLY THE INNERMOST SCOPE: it makes the count a property
of one function body, so a new nested helper inside ENCLOSING cannot silently
renumber a sibling's claim.

--------------------------------------------------------------------------
THE MIGRATION METHOD -- LINE MAPPING, NEVER NEAREST-HIT
--------------------------------------------------------------------------
A claimed line was true at the commit that WROTE it, not at HEAD. Resolving it
by "the nearest node of that name within +/-30 lines of the claim, as HEAD
numbers lines" is a guess, and it guesses wrong: on 2026-08-21 a nearest-hit
refresh MIS-PICKED SIX ROWS in one sitting. This tool does not guess.

For every row it:
  1. asks ``git blame`` which commit last wrote THAT REGISTRY LINE -- that is
     the revision at which the claimed line was true;
  2. reads the site file AT THAT REVISION (``git show SHA:path``);
  3. maps the claimed line from that revision to the working tree through
     ``difflib.SequenceMatcher`` OPCODES over the two files' lines -- an
     ``equal`` block carries the line across exactly; a ``replace``/``delete``
     block swallowing the line yields NO mapping;
  4. resolves a CALL/REF node of NAME whose SPAN COVERS the mapped line; and
     only if nothing covers it, falls back to the prereg's second tier -- the
     UNIQUE NEAREST such node within +/-30 lines OF THE MAPPED LINE.

WHY THE FALLBACK IS NOT THE THING THE NOTE FORBIDS: the old gate checked a
+/-30-line REGION for a SUBSTRING, so no claimed line in this registry was ever
required to be exact -- 28 of 109 rows point at an import, a comment or a
neighbouring statement even AT THE COMMIT THAT WROTE THEM. Nearest-hit is a
mis-pick when it is asked to absorb BOTH errors at once (the row's own
imprecision AND every line inserted since). Steps 1-3 remove the second error
entirely; the fallback then searches +/-30 lines around a line that is
already correct-as-of-when-written, and it must find its nearest candidate
STRICTLY NEARER than every other one.

If step 3 or 4 does not produce exactly ONE node, the row is a NAMED ABSENCE:
it is printed with the claimed line and what the region actually holds, and
NOTHING IS WRITTEN FOR IT. Ties and empties are absences. The tool never
chooses; a human writes the fingerprint and the reason into the note.

(The claimed line is also tried directly against the working tree first: when a
row has not rotted at all, no blame or blob read is needed.)

--------------------------------------------------------------------------
COMMANDS
--------------------------------------------------------------------------
``migrate``  old form -> fingerprint. Census by KIND + the NAMED-ABSENCE list.
``refresh``  recompute the ``@LINE`` COURTESY of already-migrated rows from the
             fingerprint itself. Never a gate failure, never CI: the gate does
             not assert @LINE and does not write the registry.
``demote``   the undo -- every fingerprint cell back to ``file:@LINE``, which
             is why the courtesy is carried inside the new cell at all.

All three default to a DRY RUN; ``--write`` is required to touch the file.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import os
import re
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO, "record", "canon", "WIRING_REGISTRY.md")

MODULE_SCOPE = "<module>"
KINDS = ("CALL", "REF", "DEF")

# file:ENCLOSING/KIND:NAME#ORDINAL@LINE  (the part after the file's colon)
_FP = re.compile(
    r"^(?P<enclosing>[A-Za-z_<][A-Za-z0-9_.>]*)"
    r"/(?P<kind>CALL|REF|DEF)"
    r":(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"#(?P<ordinal>\d+)"
    r"@(?P<line>\d+)$")


# ─────────────────────────────────────────────────────────────────────────────
# The cell grammar
# ─────────────────────────────────────────────────────────────────────────────

class Site(NamedTuple):
    """A parsed site cell. ``enclosing is None`` -> the OLD position form."""
    file: str
    line: int
    enclosing: Optional[str] = None
    kind: Optional[str] = None
    name: Optional[str] = None
    ordinal: Optional[int] = None

    @property
    def fingerprinted(self) -> bool:
        return self.enclosing is not None

    def render(self) -> str:
        if not self.fingerprinted:
            return "%s:%d" % (self.file, self.line)
        return "%s:%s/%s:%s#%d@%d" % (self.file, self.enclosing, self.kind,
                                      self.name, self.ordinal, self.line)

    def demoted(self) -> str:
        return "%s:%d" % (self.file, self.line)


def parse_site(cell: str) -> Site:
    """Both forms. OLD = an integer after the file's colon; NEW = a
    fingerprint. Anything else raises -- an unparseable site is a defect in the
    row, not something to shrug at."""
    if ":" not in cell:
        raise ValueError("site cell %r has no ':' -- expected file:line or "
                         "file:ENCLOSING/KIND:NAME#ORDINAL@LINE" % cell)
    path, rest = cell.split(":", 1)
    path = path.replace("\\", "/").strip()
    rest = rest.strip()
    if rest.isdigit():
        return Site(path, int(rest))
    m = _FP.match(rest)
    if not m:
        raise ValueError(
            "site cell %r is neither file:line nor "
            "file:ENCLOSING/KIND:NAME#ORDINAL@LINE" % cell)
    return Site(path, int(m.group("line")), m.group("enclosing"),
                m.group("kind"), m.group("name"), int(m.group("ordinal")))


# ─────────────────────────────────────────────────────────────────────────────
# The AST index: (enclosing, kind, name) -> nodes, in (line, col) order
# ─────────────────────────────────────────────────────────────────────────────

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _call_func_nodes(tree: ast.AST) -> set:
    return {id(n.func) for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, (ast.Name, ast.Attribute))}


def _named(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def build_index(tree: ast.Module) -> Tuple[Dict[Tuple[str, str, str], List[ast.AST]],
                                           set]:
    """Return ``({(enclosing, kind, name): [nodes]}, {enclosing qualnames})``.

    Every node is filed under the qualname of its INNERMOST enclosing
    def/class. A ``def``/``class``/assignment is filed as a DEF under the scope
    that CONTAINS it (not under itself)."""
    func_funcs = _call_func_nodes(tree)
    index: Dict[Tuple[str, str, str], List[ast.AST]] = {}
    quals: set = {MODULE_SCOPE}

    def add(scope: str, kind: str, name: str, node: ast.AST) -> None:
        index.setdefault((scope, kind, name), []).append(node)

    def walk(node: ast.AST, scope: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPES):
                add(scope, "DEF", child.name, child)
                inner = child.name if scope == MODULE_SCOPE else scope + "." + child.name
                quals.add(inner)
                walk(child, inner)
                continue
            if isinstance(child, ast.Assign):
                for t in child.targets:
                    if isinstance(t, ast.Name):
                        add(scope, "DEF", t.id, t)
            elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                add(scope, "DEF", child.target.id, child.target)
            if isinstance(child, ast.Call) and isinstance(child.func, (ast.Name, ast.Attribute)):
                add(scope, "CALL", _named(child.func), child)
            elif (isinstance(child, (ast.Name, ast.Attribute))
                    and id(child) not in func_funcs):
                add(scope, "REF", _named(child), child)
            walk(child, scope)

    walk(tree, MODULE_SCOPE)
    for nodes in index.values():
        nodes.sort(key=lambda n: (n.lineno, n.col_offset))
    return index, quals


def parse_file(path: str) -> Optional[ast.Module]:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return ast.parse(fh.read())
    except (OSError, SyntaxError):
        return None


def node_span(node: ast.AST) -> Tuple[int, int]:
    if isinstance(node, _SCOPES):
        lo = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        return (lo, node.lineno)
    return (node.lineno, getattr(node, "end_lineno", None) or node.lineno)


# ─────────────────────────────────────────────────────────────────────────────
# Resolution (used by migrate) and courtesy recomputation (used by refresh)
# ─────────────────────────────────────────────────────────────────────────────

class Resolved(NamedTuple):
    enclosing: str
    kind: str
    name: str
    ordinal: int
    line: int


def covering(index, names: Sequence[str], line: int,
             kinds: Sequence[str] = ("CALL", "REF")) -> List[Resolved]:
    """Every CALL/REF node of one of ``names`` whose SPAN covers ``line``.
    No radius, no nearest-hit: covering or nothing."""
    hits: List[Resolved] = []
    for (scope, kind, name), nodes in index.items():
        if kind not in kinds or name not in names:
            continue
        for i, n in enumerate(nodes):
            lo, hi = node_span(n)
            if lo <= line <= hi:
                hits.append(Resolved(scope, kind, name, i, n.lineno))
    # A tighter span wins over a looser one enclosing it (a call spanning four
    # lines vs the same call's argument on one). Equal-width ties stay ties.
    if len(hits) > 1:
        def width(r: Resolved) -> int:
            for n in index[(r.enclosing, r.kind, r.name)][r.ordinal:r.ordinal + 1]:
                lo, hi = node_span(n)
                return hi - lo
            return 0
        best = min(width(h) for h in hits)
        hits = [h for h in hits if width(h) == best]
    return hits


DRIFT = 30      # the OLD gate's region tolerance, reused as the fallback radius


def nearest_unique(index, names: Sequence[str], line: int,
                   radius: int = DRIFT) -> List[Resolved]:
    """The prereg's second tier: CALL/REF nodes of ``names`` within ``radius``
    lines, reduced to those at the MINIMAL distance. Returns one entry only
    when that nearest node is STRICTLY nearer than every other candidate;
    otherwise it returns the tie, and a tie is an absence."""
    cands: List[Tuple[int, Resolved]] = []
    for (scope, kind, name), nodes in index.items():
        if kind not in ("CALL", "REF") or name not in names:
            continue
        for i, n in enumerate(nodes):
            d = abs(n.lineno - line)
            if d <= radius:
                cands.append((d, Resolved(scope, kind, name, i, n.lineno)))
    if not cands:
        return []
    best = min(d for d, _ in cands)
    return [r for d, r in cands if d == best]


def def_fingerprint(index, quals, qualname: str) -> Optional[Resolved]:
    """The organ's OWN definition -- what a SEVERED row anchors to."""
    parts = qualname.split(".")
    scope = MODULE_SCOPE if len(parts) == 1 else ".".join(parts[:-1])
    nodes = index.get((scope, "DEF", parts[-1]))
    if not nodes:
        return None
    return Resolved(scope, "DEF", parts[-1], 0, nodes[0].lineno)


def locate(index, site: Site) -> Optional[ast.AST]:
    """The node a FINGERPRINT names, or None if the claim no longer holds."""
    nodes = index.get((site.enclosing, site.kind, site.name)) or []
    if site.ordinal is None or len(nodes) <= site.ordinal:
        return None
    return nodes[site.ordinal]


# ─────────────────────────────────────────────────────────────────────────────
# git: the revision a registry line was written at, and the file as of then
# ─────────────────────────────────────────────────────────────────────────────

def _git(args: List[str]) -> Optional[str]:
    try:
        out = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                             check=False)
    except (OSError, ValueError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "replace")


def blame_shas(path: str) -> Dict[int, str]:
    """1-based registry line -> the sha that last wrote it. Empty if git is
    unavailable; ``0``*40 for a line not committed yet."""
    rel = os.path.relpath(path, REPO).replace("\\", "/")
    out = _git(["blame", "--line-porcelain", "--", rel])
    if not out:
        return {}
    shas: Dict[int, str] = {}
    for raw in out.splitlines():
        m = re.match(r"^([0-9a-f]{40}) \d+ (\d+)", raw)
        if m:
            shas[int(m.group(2))] = m.group(1)
    return shas


# THE ORACLE'S ANCHOR, PINNED (2026-08-22). 0c77eca is the last commit BEFORE the
# symbol-anchored migration (f891ba9), so it is the last tree whose registry is in the
# OLD file:line form and whose gate can still parse it. This must never become a moving
# reference again -- see head_blob's docstring for what happened when it was HEAD.
PRE_MIGRATION_SHA = "0c77eca"


def head_blob(rel: str, sha: str = PRE_MIGRATION_SHA) -> Optional[str]:
    """A file's content at the PRE-MIGRATION commit. THE ORACLE (prereg section
    4) needs the OLD gate and the OLD registry to compare verdict vectors
    against the new pair; they live in git, and this is how a tests-only
    harness reaches them without running a subprocess of its own.

    IT USED TO READ `HEAD`, AND THAT SELF-INVALIDATED (2026-08-22). The moment
    the migration commit became an ancestor of HEAD, `HEAD:record/canon/WIRING_REGISTRY.md`
    returned the MIGRATED registry and `HEAD:...test_wiring_registry.py` the
    NEW gate -- so the oracle compared the new gate against itself, reddened
    zero rows on a line shift instead of the pinned 37, and failed. The whole
    claim of this build is that a reference which moves under a claim rots it;
    the oracle anchored itself to the most mobile reference in the repo.
    FIGURE 2: the anchor must not update. It is now a fixed SHA."""
    return _git(["show", "%s:%s" % (sha or PRE_MIGRATION_SHA, rel)])


def blob_lines(sha: str, rel: str) -> Optional[List[str]]:
    if not sha or set(sha) == {"0"}:
        sha = "HEAD"
    out = _git(["show", "%s:%s" % (sha, rel)])
    if out is None:
        return None
    return out.splitlines()


def map_line(old_lines: List[str], new_lines: List[str], line: int) -> Optional[int]:
    """Carry a 1-based line from ``old_lines`` to ``new_lines`` through
    difflib OPCODES. A line inside a ``replace``/``delete`` block does not
    survive -- that returns None, and None is an absence, not a guess."""
    if line < 1 or line > len(old_lines):
        return None
    i = line - 1
    sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for tag, i1, i2, j1, _j2 in sm.get_opcodes():
        if i1 <= i < i2:
            if tag == "equal":
                return j1 + (i - i1) + 1
            return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# The registry file: rows in, rows out (the gate's own 6-cell parse)
# ─────────────────────────────────────────────────────────────────────────────

class Row(NamedTuple):
    idx: int              # 0-based index into the file's lines
    name: str
    module: str
    qualname: str
    site_cell: str
    status: str
    date: str
    note: str

    @property
    def refnames(self) -> Tuple[str, ...]:
        base = self.qualname.split(".")[-1]
        m = re.search(r"\[alias=([A-Za-z_][A-Za-z0-9_]*)\]", self.note)
        return (base, m.group(1)) if m else (base,)

    @property
    def module_file(self) -> str:
        return self.module.replace(".", "/") + ".py"


def read_rows(path: str) -> Tuple[List[str], List[Row]]:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    rows: List[Row] = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        name, symbol, site, status, date, note = cells
        if name in ("name", "") or set(name) <= {"-", ":", " "}:
            continue
        if ":" not in symbol:
            continue
        module, qualname = symbol.split(":", 1)
        rows.append(Row(i, name, module, qualname, site, status, date, note))
    return lines, rows


def _replace_site(raw: str, old_cell: str, new_cell: str) -> str:
    cells = raw.split("|")
    for k, c in enumerate(cells):
        if c.strip() == old_cell:
            lead = c[:len(c) - len(c.lstrip())]
            trail = c[len(c.rstrip()):]
            cells[k] = lead + new_cell + trail
            return "|".join(cells)
    raise ValueError("site cell %r not found in row" % old_cell)


# ─────────────────────────────────────────────────────────────────────────────
# migrate
# ─────────────────────────────────────────────────────────────────────────────

class Absence(NamedTuple):
    name: str
    claimed: str
    reason: str


def migrate(registry: str = DEFAULT_REGISTRY, write: bool = False,
            out=sys.stdout) -> Tuple[Dict[str, int], List[Absence], List[str]]:
    lines, rows = read_rows(registry)
    shas = blame_shas(registry)
    trees: Dict[str, Optional[ast.Module]] = {}
    indexes: Dict[str, Tuple] = {}
    census: Dict[str, int] = {"CALL": 0, "REF": 0, "DEF": 0,
                              "already-fingerprinted": 0, "exact": 0,
                              "mapped": 0, "nearest-unique": 0}
    absences: List[Absence] = []
    changed: List[str] = []

    def tree_of(rel: str):
        if rel not in trees:
            trees[rel] = parse_file(os.path.join(REPO, rel))
            indexes[rel] = build_index(trees[rel]) if trees[rel] else (None, None)
        return trees[rel], indexes[rel]

    for row in rows:
        try:
            site = parse_site(row.site_cell)
        except ValueError as e:
            absences.append(Absence(row.name, row.site_cell, str(e)))
            continue
        if site.fingerprinted:
            census["already-fingerprinted"] += 1
            continue
        tree, (index, quals) = tree_of(site.file)
        if tree is None:
            absences.append(Absence(row.name, row.site_cell,
                                    "site file absent or unparseable"))
            continue

        if row.status == "SEVERED":
            # The wire-break line is a courtesy; the anchor is the organ's own
            # DEF, which test_symbol_still_defined already guarantees exists.
            mtree, (mindex, mquals) = tree_of(row.module_file)
            res = def_fingerprint(mindex, mquals, row.qualname) if mtree else None
            if res is None:
                absences.append(Absence(row.name, row.site_cell,
                                        "SEVERED organ %s has no resolvable DEF in %s"
                                        % (row.qualname, row.module_file)))
                continue
            # THE COURTESY IS THE DEF'S OWN LINE, not the old wire-break line.
            # The prereg asked for the break line here; it cannot go here,
            # because for a break in a DIFFERENT file (mute-probe's break was
            # cognitive_loop.py:1885, its DEF is verdicts.py:17 in a 42-line
            # file) the pair "module file + foreign line" is a courtesy that
            # points at nothing and a `demote` that writes a lie. The break
            # line is a historical POSITION, which is exactly the thing this
            # migration stops treating as an anchor; where it differs it is
            # preserved verbatim in the row's note as [break=file:line].
            new = Site(row.module_file, res.line, res.enclosing, "DEF",
                       res.name, res.ordinal)
            census["DEF"] += 1
            census["exact"] += 1
            lines[row.idx] = _replace_site(lines[row.idx], row.site_cell, new.render())
            changed.append(row.name)
            continue

        rel = site.file
        hits = covering(index, row.refnames, site.line)
        how = "exact"
        if len(hits) != 1:
            # Step 1-3: which revision wrote this claim, and where does that
            # line land in the working tree?
            old = blob_lines(shas.get(row.idx + 1, ""), rel)
            mapped = None
            if old is not None:
                with open(os.path.join(REPO, rel), encoding="utf-8",
                          errors="ignore") as fh:
                    mapped = map_line(old, fh.read().splitlines(), site.line)
            if mapped is None:
                absences.append(Absence(
                    row.name, row.site_cell,
                    _region_report(rel, site.line, row.refnames, hits,
                                   "the claimed line does not map forward "
                                   "(rewritten or deleted since it was written)")))
                continue
            hits = covering(index, row.refnames, mapped)
            how = "mapped"
            if len(hits) != 1:
                # Step 4's second tier, at the MAPPED line.
                hits = nearest_unique(index, row.refnames, mapped)
                how = "nearest-unique"
                if len(hits) != 1:
                    absences.append(Absence(
                        row.name, row.site_cell,
                        _region_report(rel, mapped, row.refnames, hits,
                                       "mapped to line %d" % mapped)))
                    continue
        r = hits[0]
        new = Site(site.file, r.line, r.enclosing, r.kind, r.name, r.ordinal)
        census[r.kind] += 1
        census[how] += 1
        lines[row.idx] = _replace_site(lines[row.idx], row.site_cell, new.render())
        changed.append(row.name)

    print("MIGRATION CENSUS (%s)" % os.path.relpath(registry, REPO), file=out)
    for k in ("CALL", "REF", "DEF", "already-fingerprinted", "exact", "mapped",
              "nearest-unique"):
        print("  %-24s %d" % (k, census[k]), file=out)
    print("  %-24s %d" % ("rows written", len(changed)), file=out)
    print("  %-24s %d" % ("NAMED ABSENCES", len(absences)), file=out)
    if absences:
        print("\nNAMED ABSENCES -- nothing was written for these rows. A human "
              "writes the\nfingerprint and the reason into the note; the tool "
              "never chooses.", file=out)
        for a in absences:
            print("  * %-28s claimed %s\n      %s" % (a.name, a.claimed, a.reason),
                  file=out)
    if write and changed:
        with open(registry, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        print("\nWROTE %d rows to %s" % (len(changed), registry), file=out)
    elif not write:
        print("\n(dry run -- pass --write to touch the registry)", file=out)
    return census, absences, changed


def _region_report(rel: str, line: int, names: Sequence[str],
                   hits: Sequence[Resolved], why: str) -> str:
    try:
        with open(os.path.join(REPO, rel), encoding="utf-8", errors="ignore") as fh:
            src = fh.read().splitlines()
    except OSError:
        return "%s; %s unreadable" % (why, rel)
    at = src[line - 1].strip() if 1 <= line <= len(src) else "<beyond EOF>"
    if len(hits) > 1:
        tie = "; %d covering nodes tie: %s" % (
            len(hits), ", ".join("%s/%s:%s#%d@%d" % (h.enclosing, h.kind, h.name,
                                                     h.ordinal, h.line)
                                 for h in hits[:4]))
    else:
        tie = "; no CALL/REF node of %r covers it" % (tuple(names),)
    return "%s%s -- line %d of %s holds: %r" % (why, tie, line, rel, at[:110])


# ─────────────────────────────────────────────────────────────────────────────
# refresh (courtesy only) and demote (the undo)
# ─────────────────────────────────────────────────────────────────────────────

def refresh(registry: str = DEFAULT_REGISTRY, write: bool = False,
            out=sys.stdout) -> List[Tuple[str, int, int]]:
    """Recompute the @LINE COURTESY of fingerprinted rows. NEVER a gate
    failure and NEVER CI: the gate does not assert @LINE and does not write
    this file. A row whose fingerprint no longer resolves is left alone and
    reported -- that is a real structural change for the gate to red on."""
    lines, rows = read_rows(registry)
    trees: Dict[str, Optional[ast.Module]] = {}
    moved: List[Tuple[str, int, int]] = []
    stale: List[str] = []
    for row in rows:
        try:
            site = parse_site(row.site_cell)
        except ValueError:
            continue
        if not site.fingerprinted:
            continue
        if site.file not in trees:
            t = parse_file(os.path.join(REPO, site.file))
            trees[site.file] = t
            trees[site.file + "#idx"] = build_index(t)[0] if t else None
        index = trees[site.file + "#idx"]
        node = locate(index, site) if index else None
        if node is None:
            stale.append(row.name)
            continue
        if node.lineno != site.line:
            moved.append((row.name, site.line, node.lineno))
            lines[row.idx] = _replace_site(
                lines[row.idx], row.site_cell,
                site._replace(line=node.lineno).render())
    print("COURTESY REFRESH: %d line(s) moved, %d unresolvable"
          % (len(moved), len(stale)), file=out)
    for name, old, new in moved:
        print("  %-28s @%d -> @%d" % (name, old, new), file=out)
    for name in stale:
        print("  %-28s FINGERPRINT DOES NOT RESOLVE -- a structural change; "
              "the gate owns this, not refresh" % name, file=out)
    if write and moved:
        with open(registry, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        print("WROTE %d rows" % len(moved), file=out)
    elif not write:
        print("(dry run -- pass --write)", file=out)
    return moved


def demote(registry: str = DEFAULT_REGISTRY, write: bool = False,
           out=sys.stdout) -> List[str]:
    """THE UNDO (prereg section 7). Every fingerprint cell back to
    ``file:line``, taken from the courtesy the cell carries -- which is the
    whole reason the courtesy is carried."""
    lines, rows = read_rows(registry)
    changed: List[str] = []
    for row in rows:
        try:
            site = parse_site(row.site_cell)
        except ValueError:
            continue
        if not site.fingerprinted:
            continue
        lines[row.idx] = _replace_site(lines[row.idx], row.site_cell, site.demoted())
        changed.append(row.name)
    print("DEMOTE: %d fingerprint cell(s) -> file:line" % len(changed), file=out)
    if write and changed:
        with open(registry, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        print("WROTE %d rows" % len(changed), file=out)
    elif not write:
        print("(dry run -- pass --write)", file=out)
    return changed


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("command", choices=("migrate", "refresh", "demote"))
    p.add_argument("--registry", default=DEFAULT_REGISTRY)
    p.add_argument("--write", action="store_true")
    a = p.parse_args(argv)
    {"migrate": migrate, "refresh": refresh, "demote": demote}[a.command](
        a.registry, a.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
