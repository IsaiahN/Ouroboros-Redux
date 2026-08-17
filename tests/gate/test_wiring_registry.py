"""RUNG 0c GATE: THE WIRING REGISTRY -- deterministic layer (THE_LADDER.md).

THE STANDARD: a build is DONE when something in the live path calls it with
real inputs -- and the receipt is checked by CI, not by the reviewer. The last
eleven receipt-claims were all wrong (PIPELINE_AUDIT.md, the full sweep), so a
registry alone is a convention nothing can check. This gate is the checker.

WIRING_REGISTRY.md holds one machine-parseable row per organ:

    | name | symbol (module:qualname) | site (file:line) | status | date | note |

For every LIVE entry this gate asserts:
  (a) the claimed call-site file exists and the +/-DRIFT-line region around the
      claimed line still references the symbol (receipts that rot when code
      moves go RED so they get refreshed, never silently trusted);
  (b) the symbol is REFERENCED from a production module -- by AST scan over
      ast.Name / ast.Attribute nodes, which import statements never produce,
      so a bare ``from x import Y`` re-export does NOT count (the vulture
      blind spot that hid FalsifiedLedger, fixed here), excluding tests/,
      tools/, and the symbol's own defining module.

For every SEVERED entry the gate asserts the INVERSE: no production reference
beyond definition/re-export -- so a silent reconnection without a registry
update goes RED too. The registry states reality; it does not hide it.

Note markers (square brackets inside the note column):
  [helper]              -- an internal organ of a LIVE module: a non-import
                           reference inside its OWN module counts (e.g. the
                           loop's _hyd_ver, perception's DownsampleError).
  [alias=NAME]          -- the symbol is consumed under NAME (e.g. the
                           ActionCostEstimator singleton latents.ESTIMATOR).
  [referenced-but-dead] -- SEVERED organs the deterministic scan CAN see a
                           call to, whose deadness is semantic (role
                           multiplier fed None forever; mute probe fed
                           hardcoded zeros; mint's ep kwarg never passed).
                           The inverse-reference assert is waived WITH THIS
                           LOUD MARKER ONLY; the empirical layer
                           (tools/live_coverage_diff.py) owns them.

COMPLETENESS: every class defined in engines/egocentric/*.py must have an
entry (LIVE, SEVERED, or DELETED-PENDING) -- a new organ with no receipt is
UNSHIPPABLE.

Run pre-registry: every test here failed (registry file absent).
"""
from __future__ import annotations

import ast
import functools
import glob
import os
import re
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# OURO_WIRING_REGISTRY overrides the registry path (used by the failing-first
# demonstrations and by operators dry-running a registry edit).
REGISTRY_PATH = (os.environ.get("OURO_WIRING_REGISTRY")
                 or os.path.join(REPO, "WIRING_REGISTRY.md"))

DRIFT = 30          # +/- lines of receipt drift tolerated before going red
VALID_STATUS = ("LIVE", "SEVERED", "DELETED-PENDING")

# Production scope: the live path. Tests and tools are instruments, never the
# live path; investigation scratch and the vulture whitelist are neither.
PROD_GLOBS = ("*.py", "engines/**/*.py", "rungs/**/*.py", "src/**/*.py")
PROD_EXCLUDE_NAMES = ("_temp_check.py", "vulture_whitelist.py")


class Entry(NamedTuple):
    name: str
    module: str          # dotted module path, e.g. engines.egocentric.mint
    qualname: str        # e.g. MDLMint or MDLMint.consider
    site_file: str       # repo-relative, forward slashes
    site_line: int
    status: str
    date: str
    note: str

    @property
    def refname(self) -> str:
        """The identifier a caller actually writes: last qualname segment."""
        return self.qualname.split(".")[-1]

    @property
    def alias(self) -> Optional[str]:
        m = re.search(r"\[alias=([A-Za-z_][A-Za-z0-9_]*)\]", self.note)
        return m.group(1) if m else None

    @property
    def helper(self) -> bool:
        return "[helper]" in self.note

    @property
    def referenced_but_dead(self) -> bool:
        return "[referenced-but-dead]" in self.note

    @property
    def refnames(self) -> Tuple[str, ...]:
        return (self.refname,) + ((self.alias,) if self.alias else ())

    @property
    def module_file(self) -> str:
        return self.module.replace(".", "/") + ".py"


def _parse_registry(path: str) -> List[Entry]:
    if not os.path.exists(path):
        return []
    entries: List[Entry] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != 6:
                continue
            name, symbol, site, status, date, note = cells
            if name in ("name", "") or set(name) <= {"-", ":", " "}:
                continue  # header / separator rows
            if ":" not in symbol or ":" not in site:
                raise ValueError(
                    "registry row %r: symbol must be module:qualname and "
                    "site must be file:line" % name)
            module, qualname = symbol.split(":", 1)
            site_file, site_line = site.rsplit(":", 1)
            entries.append(Entry(name, module, qualname,
                                 site_file.replace("\\", "/"), int(site_line),
                                 status, date, note))
    return entries


_ENTRIES = _parse_registry(REGISTRY_PATH)
_LIVE = [e for e in _ENTRIES if e.status == "LIVE"]
_SEVERED = [e for e in _ENTRIES if e.status == "SEVERED"]


def _prod_files() -> List[str]:
    out, seen = [], set()
    for pat in PROD_GLOBS:
        for path in glob.glob(os.path.join(REPO, pat), recursive=True):
            rel = os.path.relpath(path, REPO).replace("\\", "/")
            if rel in seen or "__pycache__" in rel:
                continue
            base = os.path.basename(rel)
            if base.startswith("_investigate") or base in PROD_EXCLUDE_NAMES:
                continue
            seen.add(rel)
            out.append(rel)
    return sorted(out)


@functools.lru_cache(maxsize=1)
def _scan() -> Dict[str, Tuple[Dict[str, int], Dict[str, int], Set[str]]]:
    """Per production file: {Name id: first line}, {Attribute attr: first
    line}, {top-level defined names}. Import statements produce neither Name
    nor Attribute nodes, so re-exports contribute NOTHING here -- that is the
    point (the vulture blind spot)."""
    out: Dict[str, Tuple[Dict[str, int], Dict[str, int], Set[str]]] = {}
    for rel in _prod_files():
        try:
            with open(os.path.join(REPO, rel), encoding="utf-8",
                      errors="ignore") as fh:
                tree = ast.parse(fh.read())
        except SyntaxError:
            continue
        names: Dict[str, int] = {}
        attrs: Dict[str, int] = {}
        defs: Set[str] = set()
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                defs.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        defs.add(t.id)
            elif (isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)):
                defs.add(node.target.id)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.setdefault(node.id, node.lineno)
            elif isinstance(node, ast.Attribute):
                attrs.setdefault(node.attr, node.lineno)
        out[rel] = (names, attrs, defs)
    return out


def _production_references(entry: Entry) -> List[str]:
    """file:line witnesses of non-import references to the entry's symbol,
    outside its own defining module (inside too, iff [helper]), skipping
    files that top-level-define the same name (local shadowing: their uses
    refer to their own symbol, not this one)."""
    witnesses: List[str] = []
    own = entry.module_file
    for rel, (names, attrs, defs) in _scan().items():
        if rel == own and not entry.helper:
            continue
        for ref in entry.refnames:
            if rel != own and ref in defs:
                continue  # shadowed: that file's `ref` is its own symbol
            line = names.get(ref) or attrs.get(ref)
            if line:
                witnesses.append("%s:%d" % (rel, line))
    return witnesses


def _symbol_defined(entry: Entry) -> bool:
    """The symbol exists where the registry says it does (class, function,
    method, or module-level assignment)."""
    path = os.path.join(REPO, entry.module_file)
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8", errors="ignore") as fh:
        tree = ast.parse(fh.read())
    parts = entry.qualname.split(".")
    body = tree.body
    for i, part in enumerate(parts):
        found = None
        for node in body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)) and node.name == part:
                found = node
                break
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == part
                    for t in node.targets):
                found = node
                break
            if (isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)
                    and node.target.id == part):
                found = node
                break
        if found is None:
            return False
        if i + 1 < len(parts):
            if not isinstance(found, ast.ClassDef):
                return False
            body = found.body
    return True


def _ids(entries: List[Entry]) -> List[str]:
    return [e.name for e in entries]


# ─────────────────────────────────────────────────────────────────────────────
# The registry itself
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistryWellFormed:

    def test_registry_exists_and_parses(self):
        assert os.path.exists(REGISTRY_PATH), (
            "WIRING_REGISTRY.md is missing -- rung 0c has no declaration "
            "layer; nothing below it is interpretable (%s)" % REGISTRY_PATH)
        assert _ENTRIES, "WIRING_REGISTRY.md parsed to ZERO entries"

    def test_statuses_and_dates_valid(self):
        bad = [(e.name, e.status) for e in _ENTRIES
               if e.status not in VALID_STATUS]
        assert not bad, "invalid status (not %s): %r" % (VALID_STATUS, bad)
        undated = [e.name for e in _ENTRIES
                   if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", e.date)]
        assert not undated, "entries without a YYYY-MM-DD date: %r" % undated

    def test_names_unique(self):
        seen, dup = set(), []
        for e in _ENTRIES:
            if e.name in seen:
                dup.append(e.name)
            seen.add(e.name)
        assert not dup, "duplicate registry names: %r" % dup


# ─────────────────────────────────────────────────────────────────────────────
# LIVE entries: the receipt is real and the wire is referenced
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("entry", _LIVE, ids=_ids(_LIVE))
class TestLiveEntries:

    def test_symbol_defined_where_claimed(self, entry: Entry):
        assert _symbol_defined(entry), (
            "%s: symbol %s:%s does not exist -- the organ moved or died; "
            "refresh the registry row" % (entry.name, entry.module,
                                          entry.qualname))

    def test_claim_site_region_references_symbol(self, entry: Entry):
        path = os.path.join(REPO, entry.site_file)
        assert os.path.exists(path), (
            "%s: claimed call-site file %s does not exist -- receipt rotted; "
            "refresh the registry row" % (entry.name, entry.site_file))
        with open(path, encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        lo = max(0, entry.site_line - 1 - DRIFT)
        hi = min(len(lines), entry.site_line + DRIFT)
        region = "".join(lines[lo:hi])
        assert any(ref in region for ref in entry.refnames), (
            "%s: no mention of %r within +/-%d lines of %s:%d -- the receipt "
            "rotted (code moved more than the drift tolerance); find the real "
            "call site and refresh the registry row, LOUDLY, not silently"
            % (entry.name, entry.refnames, DRIFT, entry.site_file,
               entry.site_line))

    def test_symbol_referenced_from_production(self, entry: Entry):
        witnesses = _production_references(entry)
        assert witnesses, (
            "%s: %s:%s claims LIVE but NO production module references %r "
            "(non-import AST scan; re-exports do not count -- the vulture "
            "blind spot). Either the wire was cut (mark it SEVERED with the "
            "break line) or the organ was deleted (DELETED-PENDING)."
            % (entry.name, entry.module, entry.qualname, entry.refnames))


# ─────────────────────────────────────────────────────────────────────────────
# SEVERED entries: the inverse -- a silent reconnection goes red
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("entry", _SEVERED, ids=_ids(_SEVERED))
class TestSeveredEntries:

    def test_symbol_still_defined(self, entry: Entry):
        assert _symbol_defined(entry), (
            "%s: SEVERED symbol %s:%s no longer exists -- if it was deleted, "
            "the registry row moves to DELETED-PENDING (or is retired with "
            "the deletion commit named in the note)"
            % (entry.name, entry.module, entry.qualname))

    def test_break_site_exists(self, entry: Entry):
        path = os.path.join(REPO, entry.site_file)
        assert os.path.exists(path), (
            "%s: wire-break site file %s does not exist"
            % (entry.name, entry.site_file))
        with open(path, encoding="utf-8", errors="ignore") as fh:
            n = sum(1 for _ in fh)
        assert entry.site_line <= n, (
            "%s: wire-break line %d beyond end of %s (%d lines)"
            % (entry.name, entry.site_line, entry.site_file, n))

    def test_not_referenced_from_production(self, entry: Entry):
        if entry.referenced_but_dead:
            # Deterministic AST CAN see a call to these; the deadness is
            # semantic (None/zero inputs, an unpassed kwarg). The marker is
            # the loud waiver; the coverage diff owns the empirical check.
            assert "[referenced-but-dead]" in entry.note
            return
        witnesses = _production_references(entry)
        assert not witnesses, (
            "%s: registry says SEVERED but production references %r at %s -- "
            "either a RECONNECTION landed without updating the registry "
            "(update the row to LIVE with the new receipt: reconnection is a "
            "FIRST ACTIVATION and enters as a fresh arm, per the sweep), or "
            "this is a new caller of a dead organ."
            % (entry.name, entry.refnames, witnesses[:5]))


# ─────────────────────────────────────────────────────────────────────────────
# Completeness: a new organ with no entry is UNSHIPPABLE
# ─────────────────────────────────────────────────────────────────────────────

def _egocentric_classes() -> List[Tuple[str, str]]:
    out = []
    for path in sorted(glob.glob(os.path.join(REPO, "engines", "egocentric",
                                              "*.py"))):
        rel = os.path.relpath(path, REPO).replace("\\", "/")
        module = rel[:-3].replace("/", ".")
        with open(path, encoding="utf-8", errors="ignore") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                out.append((module, node.name))
    return out


class TestRegistryCompleteness:

    def test_every_egocentric_class_has_an_entry(self):
        covered = {(e.module, e.qualname.split(".")[0]) for e in _ENTRIES}
        missing = [(m, c) for (m, c) in _egocentric_classes()
                   if (m, c) not in covered]
        assert not missing, (
            "engines/egocentric classes with NO registry entry (a new organ "
            "with no receipt is UNSHIPPABLE -- add a row: LIVE with its "
            "call-site receipt, SEVERED with its break line, or "
            "DELETED-PENDING): %r" % missing)

    def test_entries_point_at_real_modules(self):
        ghosts = [e.name for e in _ENTRIES
                  if not os.path.exists(os.path.join(REPO, e.module_file))]
        assert not ghosts, (
            "registry entries whose module file does not exist: %r" % ghosts)
