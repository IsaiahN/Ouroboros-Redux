"""RUNG 0c GATE: THE WIRING REGISTRY -- deterministic layer (THE_LADDER.md).

THE STANDARD: a build is DONE when something in the live path calls it with
real inputs -- and the receipt is checked by CI, not by the reviewer. The last
eleven receipt-claims were all wrong (PIPELINE_AUDIT.md, the full sweep), so a
registry alone is a convention nothing can check. This gate is the checker.

WIRING_REGISTRY.md holds one machine-parseable row per organ:

    | name | symbol (module:qualname) | site | status | date | note |

THE SITE CELL IS A SYMBOL FINGERPRINT, NOT A POSITION (2026-08-21,
record/prereg/PREREG_SYMBOL_RECEIPTS.md)::

    file:ENCLOSING/KIND:NAME#ORDINAL@LINE

A claim about STRUCTURE ("this organ is called from inside that function") used
to be stored as a POSITION (``file:line``, checked +/-30 lines), so every
insertion above the position invalidated the claim without touching the fact:
~140 receipt refreshes in one week, ZERO of them a broken wire. A receipt that
only a line-shift can break is not a check -- it is a constant carrying the
author's authority (FIGURE 10). The fingerprint can be broken by a real
structural change and by nothing else. ``@LINE`` is A COURTESY and is NEVER
asserted: a stale @LINE is not red. ``tools/wiring_receipts.py refresh``
repairs courtesies; this gate never writes the registry.

DURING MIGRATION both cell forms are accepted per row (old form = an integer
after the file's colon). The old-form branch retires in the commit AFTER the
last row leaves it (PROCTOR decision 5).

For every LIVE entry this gate asserts:
  (a) THE SITE FINGERPRINT RESOLVES: the site file parses, ENCLOSING exists in
      it, and at least ORDINAL+1 same-KIND same-NAME nodes live inside
      ENCLOSING. (Old-form rows: the +/-DRIFT-line region around the claimed
      line still mentions the symbol.)
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

COVERAGE (2026-08-21, from record/findings/CODEBASE_INVENTORY.md FINDING 2):
the completeness check above can only see CLASSES. A module of bare functions
is invisible to it -- engines/egocentric/relations.py is LIVE by import (depth
3, via the package __init__), carries no row, and none of its three public
functions is referenced anywhere in the tree, INSIDE the very package this gate
was written to cover. So: every module REACHABLE from the six production
entrypoints (module-level AND in-function imports -- the live path is 27
modules wider than a static scan shows) either has a row or is named in
NO_ROW_ALLOWLIST with a reason. The allowlist is the convention that CAN be
violated (FIGURE 10); a new reachable module with neither goes red.

Run pre-registry: every test here failed (registry file absent).
"""
from __future__ import annotations

import ast
import functools
import glob
import os
import re
import sys
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.wiring_receipts import (  # noqa: E402  -- the fingerprint grammar
    MODULE_SCOPE,
    build_index,
    parse_site,
)

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
    site_line: int       # the COURTESY line -- never asserted for a fingerprint
    status: str
    date: str
    note: str
    # The fingerprint. All four are None on an old-form (file:line) row.
    enclosing: Optional[str] = None
    kind: Optional[str] = None
    nodename: Optional[str] = None
    ordinal: Optional[int] = None

    @property
    def fingerprinted(self) -> bool:
        return self.enclosing is not None

    @property
    def site_cell(self) -> str:
        if not self.fingerprinted:
            return "%s:%d" % (self.site_file, self.site_line)
        return "%s:%s/%s:%s#%d@%d" % (self.site_file, self.enclosing, self.kind,
                                      self.nodename, self.ordinal, self.site_line)

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
                    "registry row %r: symbol must be module:qualname and site "
                    "must be file:ENCLOSING/KIND:NAME#ORDINAL@LINE (or, until "
                    "the old form retires, file:line)" % name)
            module, qualname = symbol.split(":", 1)
            s = parse_site(site)      # BOTH forms, during the migration
            entries.append(Entry(name, module, qualname, s.file, s.line,
                                 status, date, note,
                                 s.enclosing, s.kind, s.name, s.ordinal))
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


@functools.lru_cache(maxsize=64)
def _index(rel: str):
    """``(index, qualnames)`` for one site file, or ``(None, None)`` if it does
    not parse. Cached: a 5000-line loop is parsed once per session, not once
    per row."""
    path = os.path.join(REPO, rel)
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError):
        return (None, None)
    return build_index(tree)


def _assert_fingerprint(entry: Entry) -> None:
    """THE THREE ASSERTIONS OF A SYMBOL-ANCHORED RECEIPT (prereg section 1.2).
    The courtesy line is NOT among them: a stale @LINE is not red."""
    index, quals = _index(entry.site_file)
    assert index is not None, (
        "%s: site file %s does not exist or does not parse -- the receipt "
        "cannot be checked at all" % (entry.name, entry.site_file))
    assert entry.enclosing == MODULE_SCOPE or entry.enclosing in quals, (
        "%s: the receipt is anchored inside %r, which does not exist in %s. "
        "The enclosing function or class was RENAMED or REMOVED -- that is a "
        "structural change to the organ's wiring (prereg 1.4), so name the new "
        "scope in the row. Nothing above this site can cause this."
        % (entry.name, entry.enclosing, entry.site_file))
    nodes = index.get((entry.enclosing, entry.kind, entry.nodename)) or []
    assert len(nodes) > entry.ordinal, (
        "%s: the receipt claims %s #%d of %r inside %r in %s, and only %d "
        "such node(s) exist. Either the anchored %s WAS DELETED (the wire is "
        "broken -- mark the row SEVERED with the break, do not renumber it), "
        "or same-named nodes were removed from that scope. This is never "
        "caused by inserting code elsewhere."
        % (entry.name, entry.kind, entry.ordinal, entry.nodename,
           entry.enclosing, entry.site_file, len(nodes), entry.kind))


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
        if entry.fingerprinted:
            _assert_fingerprint(entry)
            return
        # ── the OLD form, kept only until the last row leaves it ───────────
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
        """A SEVERED row anchors to the organ's OWN def (always resolvable --
        test_symbol_still_defined asserts it), with the def's line as the
        courtesy. The historic wire-break line rides in the note as
        [break=file:line] where it differed: a break line is a POSITION, and a
        position is exactly what stopped being an anchor here.

        The old assertion -- "the break line is <= the file's line count" --
        was very nearly vacuous, and five of these twenty rows were pointing
        at the wrong place under it (role-multiplier claimed :245 for a def at
        :1441; agent-motion :209 for :37; broken-rebinding :71 for :19)."""
        if entry.fingerprinted:
            _assert_fingerprint(entry)
            return
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


# ─────────────────────────────────────────────────────────────────────────────
# Coverage: a module the gate CANNOT SEE is the blind spot, not a clean sheet
# ─────────────────────────────────────────────────────────────────────────────
#
# The completeness check above sees CLASSES. relations.py is bare functions:
# LIVE by import via the package __init__, no row, and none of its three public
# names referenced anywhere -- invisible. This falsifier is over MODULES.
#
# THE ALLOWLIST IS THE CONVENTION THAT CAN BE VIOLATED (FIGURE 10). Inside
# engines/egocentric/ -- the package this registry governs -- only EXACT module
# paths may be listed, each with its reason, so a new organ cannot slip in
# under a wildcard. Outside it, a DIRECTORY PREFIX with a reason is allowed:
# those modules are reachable but are not this registry's jurisdiction, and
# 146 hand-authored reasons would be exactly the "constant the seat authored"
# this whole build is retiring.

ENTRYPOINTS = ("evolution_runner.py", "tools/swarm_supervisor.py",
               "tools/sprint_keeper.py", "cognitive_game_player.py",
               "game_player.py", "arc_api_adapter.py")

NO_ROW_ALLOWLIST: Dict[str, str] = {
    # ── engines/egocentric/: EXACT paths only, one reason each ──────────────
    "engines/egocentric/__init__.py":
        "the package re-export shim -- it defines no organ; it is the very "
        "mechanism that carries modules into the live set unreferenced, which "
        "is why this falsifier exists",
    "engines/egocentric/planner.py":
        "a CONSUMER, not an organ: five rows name call sites INSIDE it "
        "(cost-flip, applicability-index, standing-rank, standing-population, "
        "retention-session). Its wiring is receipted from the other end",
    "engines/egocentric/discrepancy.py":
        "W3b's d, the self-authored objective -- a pure computation over "
        "frames with no organ of its own; consumed through the gate's WANT "
        "compilation (engines/egocentric/gate.py want_discrepancy)",
    "engines/egocentric/relations.py":
        "THE NAMED BLIND SPOT (CODEBASE_INVENTORY.md FINDING 2, 2026-08-21): "
        "LIVE by import at depth 3 via the package __init__, and its three "
        "public functions (quantified_candidates, class_member_cells, "
        "candidate_relations) are called from NOWHERE in the tree. It is "
        "listed here, not rowed, because a row would have to claim a call "
        "site and there is none. QUEUED: a SEVERED row with the reason, or a "
        "deletion. It is named so that it cannot go on being invisible",
    # ── outside the registry's jurisdiction: prefixes with reasons ──────────
    "engines/": "outside engines/egocentric/ -- the legacy and adjacent engine "
                "stacks are not this registry's jurisdiction (rung 0c covers "
                "the egocentric substrate); their reachability is inventoried "
                "in record/findings/CODEBASE_INVENTORY.md",
    "rungs/": "the rung ladder is receipted by THE_LADDER.md, not here",
    "tools/": "instruments, never the live path -- the gate's own PROD_GLOBS "
              "exclude them from the reference scan for the same reason",
    "config/": "configuration, no organs",
    "manual_tools/": "operator one-offs; inventoried, not rowed",
    "": "repo-root entrypoints and their direct helpers -- game_player, "
        "cognitive_game_player, evolution_runner and the modules they pull in "
        "are the HOSTS of the egocentric substrate, not organs of it; the "
        "loop's own helpers that ARE organs carry rows (hydration, "
        "reasoning-gate-hook, narration-arm-route, ...)",
}


def _module_edges(rel: str) -> List[str]:
    """Every module file this one imports -- MODULE-LEVEL AND IN-FUNCTION.
    The lazy edges are not an extra: the live path is 27 modules wider than a
    static scan shows (CODEBASE_INVENTORY.md FINDING 1), so a scan that drops
    them would declare modules unreachable that run every episode."""
    def _exists(p: str) -> bool:
        return os.path.exists(os.path.join(REPO, p))

    def _for(mod: str) -> List[str]:
        out, p = [], mod.replace(".", "/")
        if _exists(p + ".py"):
            out.append(p + ".py")
        parts = mod.split(".")
        for i in range(1, len(parts) + 1):
            q = "/".join(parts[:i]) + "/__init__.py"
            if _exists(q):
                out.append(q)
        return out

    try:
        with open(os.path.join(REPO, rel), encoding="utf-8",
                  errors="ignore") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError):
        return []
    pkg = os.path.dirname(rel).replace("/", ".")
    out: List[str] = []
    for node in ast.walk(tree):          # walk, not tree.body: lazy imports
        if isinstance(node, ast.Import):
            for a in node.names:
                out += _for(a.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = pkg.split(".") if pkg else []
                if node.level > 1:
                    parts = parts[:len(parts) - (node.level - 1)]
                base = ".".join([p for p in parts if p] + ([base] if base else []))
            if base:
                out += _for(base)
                for a in node.names:
                    out += _for(base + "." + a.name)
    return out


@functools.lru_cache(maxsize=1)
def _reachable() -> Set[str]:
    seen = {e for e in ENTRYPOINTS if os.path.exists(os.path.join(REPO, e))}
    stack = list(seen)
    while stack:
        for dst in _module_edges(stack.pop()):
            if dst not in seen:
                seen.add(dst)
                stack.append(dst)
    return seen


def _allowlisted(rel: str) -> bool:
    if rel in NO_ROW_ALLOWLIST:
        return True
    if rel.startswith("engines/egocentric/"):
        return False          # jurisdiction: exact paths only, no wildcards
    return any(k and rel.startswith(k) for k in NO_ROW_ALLOWLIST) or "/" not in rel


class TestReachableModulesAreCovered:

    def test_every_reachable_module_has_a_row_or_a_named_reason(self):
        rowed = {e.module_file for e in _ENTRIES}
        missing = sorted(rel for rel in _reachable()
                         if rel not in rowed and not _allowlisted(rel))
        assert not missing, (
            "modules reachable from the production entrypoints with NEITHER a "
            "registry row NOR an entry in NO_ROW_ALLOWLIST: %r. A module the "
            "registry cannot see is the blind spot relations.py sat in -- add "
            "a row (LIVE with its call-site fingerprint, SEVERED with the "
            "break) or allowlist it WITH A REASON." % missing)

    def test_the_allowlist_is_not_a_wildcard_inside_the_registrys_package(self):
        """Every allowlist key under engines/egocentric/ must name a real
        module -- a stale entry silently re-opens the blind spot it closed."""
        ghosts = [k for k in NO_ROW_ALLOWLIST
                  if k.startswith("engines/egocentric/")
                  and not os.path.exists(os.path.join(REPO, k))]
        assert not ghosts, "allowlist entries for modules that no longer exist: %r" % ghosts
        thin = [k for k, v in NO_ROW_ALLOWLIST.items() if len(v.strip()) < 20]
        assert not thin, (
            "allowlist entries whose 'reason' says nothing: %r -- an "
            "unreasoned exemption is a constant wearing a convention's clothes"
            % thin)

    def test_the_reachability_scan_includes_lazy_imports(self):
        """The falsifier for the falsifier: engines/egocentric/mastery.py is
        reached ONLY through in-function imports of the egocentric package
        chain. A module-level-only scan would drop 27 modules and declare the
        live path clean by not looking at it."""
        assert "engines/egocentric/relations.py" in _reachable(), (
            "the reachability scan lost relations.py -- the module this "
            "falsifier was written for")
        assert len(_reachable()) > 150, (
            "only %d modules reachable -- the scan collapsed; the measured "
            "figure at 2026-08-21 was 188" % len(_reachable()))
