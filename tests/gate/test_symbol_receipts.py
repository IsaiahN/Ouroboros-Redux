"""GATE: SYMBOL-ANCHORED RECEIPTS + AST LAWS (record/prereg/PREREG_SYMBOL_RECEIPTS.md §5).

THE CLAIM UNDER TEST. A receipt that only a LINE SHIFT can break is not a
check. Measured in the week to 2026-08-21: ~140 registry refreshes, every one
forced by code moving, ZERO of them a broken wire — while four of sixty rows
asserted nothing at all (decline-branch passed on the substring "match" inside
`return out`; goal-abduction-plan passed on an import line 36 lines above the
call). The fingerprint `file:ENCLOSING/KIND:NAME#ORDINAL@LINE` is a convention
that CAN be violated by a real structural change and by nothing else.

Every falsifier here builds a REAL SCRATCH CHECKOUT (the production globs plus
the two gate files), mutates it, and runs the SHIPPED gate and the SHIPPED
laws against it. Nothing is asserted about a string; every verdict comes from
the same code CI runs.

  F1  INSERTION IS INVISIBLE — 200 lines above EVERY claim site AND 100 lines
      inside record_result before its first credit call: ZERO receipts red,
      ZERO laws red.
  F2  REMOVAL IS NOT — delete an anchored node and its row goes red; delete
      the credit call and L1 goes red; delete _goal_abd and L3 goes red.
  F3  ORDER IS REAL — a bank call before the first route reds L3; a _plan_gate
      write inside record_result reds L4; a _plan_gate write in a NEW
      module-bottom helper is GREEN (and so is L7, which used to forbid the
      helper existing at all).
  F4  ORDINAL IS HONEST — an ordinal past the count reds, naming ordinal and
      count; a same-name call inserted AFTER the anchor stays green. The
      insert-BEFORE case is a NAMED RESIDUE, asserted as a residue below.
  F5  ABSENCES ARE NAMED — an unresolvable row is reported by name, nothing is
      written for it, and the gate still reads its old form.
  F6  THE ORACLE (§4) — old gate over the pre-migration registry vs new gate
      over the migrated one, same tree: per-row per-test verdict vectors
      IDENTICAL; then three mutations on both, including the 200-line shift
      that reds N rows on the old gate and ZERO on the new.

PRE-NAMED VERDICTS THE NEW LAWS MUST NOT REPRODUCE (prereg §4): the window-law
reds and the `_plan_gate` tail-law red of 2026-08-21. The facts held that day;
only positions moved. Every law is green on this tree — that is the assertion,
made in tests/gate/test_goal_spine.py, test_goal_abduction.py,
test_level_conventions.py, test_lp_drive.py, test_link3_hook_and_vocabulary.py,
test_plan_wire.py and test_gate_stage1.py, whose bodies now delegate here.

Run pre-build: F1-F6 all failed (no fingerprints, no _ast_laws.py).
"""
from __future__ import annotations

import ast
import glob
import hashlib
import importlib.util
import os
import shutil
import sys
import uuid
from typing import Dict, List, Tuple

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.wiring_receipts import (  # noqa: E402
    build_index,
    head_blob,
    migrate,
    parse_file,
    parse_site,
    read_rows,
)

GATE_REL = "tests/gate/test_wiring_registry.py"
LAWS_REL = "tests/gate/_ast_laws.py"
REGISTRY_REL = "WIRING_REGISTRY.md"
# The gate's PROD_GLOBS plus tools/: tools are excluded from the REFERENCE
# scan (they are instruments, never the live path) but four SEVERED rows point
# AT them, so a scratch tree without tools/ reds those rows for a reason that
# has nothing to do with the mutation under test.
FULL_GLOBS = ("*.py", "engines/**/*.py", "rungs/**/*.py", "src/**/*.py",
              "tools/**/*.py")
# A law falsifier only ever reads cognitive_loop.py. Copying one file instead
# of 239 keeps this gate to minutes: L6 (exactly ONE production lp_steer call)
# is still true and still checked in the one-file tree, and every other law is
# about the loop alone.
LOOP_ONLY = ("cognitive_loop.py",)
# The site files of the rows F2 anchors on, without the rest of engines/.
EGO_GLOBS = ("*.py", "engines/egocentric/*.py")

LIVE_TESTS = ("test_symbol_defined_where_claimed",
              "test_claim_site_region_references_symbol",
              "test_symbol_referenced_from_production")
SEVERED_TESTS = ("test_symbol_still_defined",
                 "test_break_site_exists",
                 "test_not_referenced_from_production")


# ─────────────────────────────────────────────────────────────────────────────
# Harness: a real scratch checkout, and the shipped gate/laws loaded inside it
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _no_registry_override(monkeypatch):
    """OURO_WIRING_REGISTRY steers the gate's registry path. Some gate file in
    this suite imports evolution_runner at module level, whose import calls
    load_dotenv() and pushes real environment into os.environ for the whole
    process — so a test that reasons about env must clear what it reasons
    about, or it passes alone and fails in suite order."""
    monkeypatch.delenv("OURO_WIRING_REGISTRY", raising=False)


@pytest.fixture(scope="module", autouse=True)
def _memoised_parse():
    """ast.parse memoised on the source TEXT for the duration of this module.
    Pure-function caching: the scratch trees differ from each other in ONE
    file, so the other 205 parses are shared and the oracle costs seconds
    instead of minutes. Restored afterwards."""
    real = ast.parse
    cache: Dict[int, ast.Module] = {}

    def parse(src, *a, **kw):
        if isinstance(src, str) and not a and not kw:
            key = hash(src)
            if key not in cache:
                cache[key] = real(src)
            return cache[key]
        return real(src, *a, **kw)

    ast.parse = parse
    try:
        yield
    finally:
        ast.parse = real


def _scratch(tmp_path_factory, name: str, globs=FULL_GLOBS) -> str:
    """Everything the gate reads: the production globs, the registry, the gate
    and the laws. Nothing is stubbed — the mutations below are made against a
    tree the shipped code cannot tell from the real one."""
    dst = str(tmp_path_factory.mktemp("sr_" + name))
    for pat in globs:
        for src in glob.glob(os.path.join(REPO, pat), recursive=True):
            rel = os.path.relpath(src, REPO).replace("\\", "/")
            if "__pycache__" in rel:
                continue
            out = os.path.join(dst, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copyfile(src, out)
    os.makedirs(os.path.join(dst, "tests", "gate"), exist_ok=True)
    for rel in (GATE_REL, LAWS_REL, REGISTRY_REL):
        shutil.copyfile(os.path.join(REPO, rel),
                        os.path.join(dst, rel.replace("/", os.sep)))
    return dst


def _load(path: str) -> object:
    spec = importlib.util.spec_from_file_location("ouro_scratch_%s" % uuid.uuid4().hex,
                                                  path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gate(root: str):
    return _load(os.path.join(root, GATE_REL.replace("/", os.sep)))


def _laws(root: str):
    return _load(os.path.join(root, LAWS_REL.replace("/", os.sep)))


# One scan of the production globs costs ~15s and is the whole cost of a
# verdict vector. It is a PURE FUNCTION of the tree's production files, so two
# gates over one tree -- and two trees with byte-identical production files --
# share one result. The value is always computed by THE GATE'S OWN _scan: this
# caches, it does not reimplement.
_SCAN_BY_TREE: Dict[str, object] = {}


def _prime_scan(gate) -> None:
    h = hashlib.sha1(usedforsecurity=False)
    for rel in gate._prod_files():
        h.update(rel.encode())
        try:
            with open(os.path.join(gate.REPO, rel), "rb") as fh:
                h.update(fh.read())
        except OSError:
            pass
    key = h.hexdigest()
    if key not in _SCAN_BY_TREE:
        _SCAN_BY_TREE[key] = gate._scan()
    value = _SCAN_BY_TREE[key]
    gate._scan = lambda: value


def _verdict1(gate, rowname: str, testname: str) -> bool:
    """One row, one test -- and never a production scan when the test does not
    need one, which is what makes the ordinal falsifiers cheap."""
    entries = gate._LIVE if testname in LIVE_TESTS else gate._SEVERED
    entry = [e for e in entries if e.name == rowname][0]
    obj = gate.TestLiveEntries() if testname in LIVE_TESTS else gate.TestSeveredEntries()
    try:
        getattr(obj, testname)(entry)
        return True
    except AssertionError:
        return False


def _verdicts(gate) -> Dict[Tuple[str, str], bool]:
    """Per row, per test: True = green. AssertionError is the only red; any
    other exception is a broken harness and is allowed to propagate."""
    _prime_scan(gate)
    out: Dict[Tuple[str, str], bool] = {}
    live, sev = gate.TestLiveEntries(), gate.TestSeveredEntries()
    for entries, obj, names in ((gate._LIVE, live, LIVE_TESTS),
                                (gate._SEVERED, sev, SEVERED_TESTS)):
        for e in entries:
            for n in names:
                try:
                    getattr(obj, n)(e)
                    out[(e.name, n)] = True
                except AssertionError:
                    out[(e.name, n)] = False
    return out


def _law_reds(laws) -> List[str]:
    reds = []
    for fn in laws.ALL_LAWS:
        try:
            fn()
        except AssertionError:
            reds.append(fn.__name__)
    return reds


def _rows(root: str):
    return read_rows(os.path.join(root, REGISTRY_REL))[1]


def _row(root: str, name: str):
    for r in _rows(root):
        if r.name == name:
            return r
    raise AssertionError("no registry row named %r" % name)


def _rewrite(root: str, rel: str, lines: List[str]) -> None:
    with open(os.path.join(root, rel.replace("/", os.sep)), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def _lines(root: str, rel: str) -> List[str]:
    with open(os.path.join(root, rel.replace("/", os.sep)), encoding="utf-8",
              errors="ignore") as fh:
        return fh.read().splitlines()


def _indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _anchored(root: str, name: str):
    """The exact AST node a row's fingerprint names, in the scratch tree."""
    r = _row(root, name)
    site = parse_site(r.site_cell)
    index, _ = build_index(parse_file(os.path.join(root, site.file)))
    nodes = index[(site.enclosing, site.kind, site.name)]
    return site, nodes[site.ordinal]


def _statement(root: str, rel: str, node: ast.AST) -> ast.stmt:
    """The innermost STATEMENT containing ``node``. Insertions and deletions
    happen at statement granularity: a call that spans four lines is one
    statement, and splicing text into the middle of it would only prove that
    the falsifier can write a syntax error."""
    stmt = None
    for n in ast.walk(parse_file(os.path.join(root, rel))):
        if (isinstance(n, ast.stmt)
                and n.lineno <= node.lineno <= (n.end_lineno or n.lineno)
                and (stmt is None or n.lineno >= stmt.lineno)):
            stmt = n
    assert stmt is not None
    return stmt


def _delete_statement(root: str, rel: str, node: ast.AST) -> None:
    """Replace the STATEMENT containing ``node`` with `pass` at its own indent
    -- a real deletion of the call, not a rename of it."""
    lines = _lines(root, rel)
    stmt = _statement(root, rel, node)
    head = _indent(lines[stmt.lineno - 1])
    lines[stmt.lineno - 1:stmt.end_lineno] = [head + "pass  # DELETED BY FALSIFIER"]
    _rewrite(root, rel, lines)


def _insert(root: str, rel: str, at: int, block: List[str]) -> None:
    """Insert ``block`` BEFORE 1-based line ``at``."""
    lines = _lines(root, rel)
    lines[at - 1:at - 1] = block
    _rewrite(root, rel, lines)


# ─────────────────────────────────────────────────────────────────────────────
# F1 · insertion is invisible
# ─────────────────────────────────────────────────────────────────────────────

class TestF1InsertionIsInvisible:

    @pytest.fixture(scope="class")
    def shifted(self, tmp_path_factory):
        root = _scratch(tmp_path_factory, "f1")
        # 200 lines above EVERY claim site -- every file any row points at.
        for rel in sorted({parse_site(r.site_cell).file for r in _rows(root)}):
            path = os.path.join(root, rel.replace("/", os.sep))
            if not os.path.exists(path):
                continue
            lines = _lines(root, rel)
            _rewrite(root, rel, ["# F1 shift %d" % i for i in range(200)] + lines)
        # 100 lines INSIDE record_result, above its first credit call.
        laws = _laws(root)
        rr = laws.scope(laws.tree(os.path.join(root, "cognitive_loop.py")),
                        "CognitiveLoop.record_result")
        first = laws.calls(rr, "credit")[0]
        pad = _indent(_lines(root, "cognitive_loop.py")[first.lineno - 1])
        _insert(root, "cognitive_loop.py", first.lineno,
                [pad + "# F1 filler %d" % i for i in range(100)])
        return root

    def test_zero_receipts_go_red(self, shifted):
        reds = sorted(k for k, ok in _verdicts(_gate(shifted)).items() if not ok)
        assert not reds, (
            "%d receipt verdict(s) went red on a PURE LINE SHIFT: %r. Nothing "
            "structural changed -- this is the ~140-refreshes-a-week defect, "
            "back." % (len(reds), reds[:12]))

    def test_zero_laws_go_red(self, shifted):
        reds = _law_reds(_laws(shifted))
        assert not reds, (
            "laws red on a pure insertion: %r. A law that a shift can break is "
            "a character window wearing an AST's clothes." % reds)

    def test_the_shift_was_real(self, shifted):
        """The falsifier's own falsifier: prove the tree actually moved, so a
        green F1 cannot be green because nothing happened."""
        laws = _laws(shifted)
        rr = laws.scope(laws.tree(os.path.join(shifted, "cognitive_loop.py")),
                        "CognitiveLoop.record_result")
        moved = laws.calls(rr, "credit")[0].lineno
        original = _row(REPO, "click-economy")
        assert moved > parse_site(original.site_cell).line, (
            "the first credit call did not move -- F1 proved nothing")


# ─────────────────────────────────────────────────────────────────────────────
# F2 · removal is not
# ─────────────────────────────────────────────────────────────────────────────

class TestF2RemovalIsNot:

    # One CALL row per site file family: the loop, an engine, a nested scope.
    ROWS = ("click-economy", "bank-core", "context-min", "standing-fence")

    @pytest.mark.parametrize("rowname", ROWS)
    def test_deleting_the_anchored_node_reds_its_row(self, tmp_path_factory, rowname):
        root = _scratch(tmp_path_factory, "f2_" + rowname.replace("-", "_"),
                        EGO_GLOBS)
        site, node = _anchored(root, rowname)
        _delete_statement(root, site.file, node)
        red = _verdict1(_gate(root), rowname,
                        "test_claim_site_region_references_symbol")
        assert red is False, (
            "%s: the anchored %s was DELETED and the receipt stayed green -- "
            "the fingerprint is not checking anything" % (rowname, site.kind))

    def test_deleting_the_credit_call_reds_l1(self, tmp_path_factory):
        root = _scratch(tmp_path_factory, "f2_credit", LOOP_ONLY)
        laws = _laws(root)
        loop = os.path.join(root, "cognitive_loop.py")
        rr = laws.scope(laws.tree(loop), "CognitiveLoop.record_result")
        for c in reversed(laws.calls(rr, "credit")):
            _delete_statement(root, "cognitive_loop.py", c)
        reds = _law_reds(_laws(root))
        assert "l1_credit_inside_record_result" in reds, (
            "every credit call was removed from record_result and L1 stayed "
            "green -- reward-disposes would be unwired and unnoticed")

    def test_deleting_the_goal_abd_call_reds_l3(self, tmp_path_factory):
        root = _scratch(tmp_path_factory, "f2_abd", LOOP_ONLY)
        laws = _laws(root)
        rr = laws.scope(laws.tree(os.path.join(root, "cognitive_loop.py")),
                        "CognitiveLoop.record_result")
        for c in reversed(laws.calls(rr, "_goal_abd")):
            _delete_statement(root, "cognitive_loop.py", c)
        assert "l3_settle_before_bank" in _law_reds(_laws(root))


# ─────────────────────────────────────────────────────────────────────────────
# F3 · order is real
# ─────────────────────────────────────────────────────────────────────────────

class TestF3OrderIsReal:

    def test_banking_before_routing_reds_l3(self, tmp_path_factory):
        root = _scratch(tmp_path_factory, "f3_order", LOOP_ONLY)
        laws = _laws(root)
        rr = laws.scope(laws.tree(os.path.join(root, "cognitive_loop.py")),
                        "CognitiveLoop.record_result")
        first_route = laws.calls(rr, "route")[0]
        stmt_line = first_route.lineno
        pad = _indent(_lines(root, "cognitive_loop.py")[stmt_line - 1])
        _insert(root, "cognitive_loop.py", stmt_line,
                [pad + "_goal_abd(self, None, None)  # BANKED BEFORE THE SETTLE"])
        assert "l3_settle_before_bank" in _law_reds(_laws(root)), (
            "a level-up banked BEFORE the settlement is routed stayed green -- "
            "the hypothesis would be formed from an unattributed delta")

    def test_plan_gate_written_inside_record_result_reds_l4(self, tmp_path_factory):
        root = _scratch(tmp_path_factory, "f3_leak", LOOP_ONLY)
        laws = _laws(root)
        rr = laws.scope(laws.tree(os.path.join(root, "cognitive_loop.py")),
                        "CognitiveLoop.record_result")
        first = laws.calls(rr, "credit")[0]
        pad = _indent(_lines(root, "cognitive_loop.py")[first.lineno - 1])
        _insert(root, "cognitive_loop.py", first.lineno,
                [pad + 'self._plan_gate["g7"] = 1  # RESULT-PATH LEAK'])
        assert "l4_plan_gate_on_the_cycle_path" in _law_reds(_laws(root))

    def test_a_module_bottom_helper_touching_plan_gate_is_green(self, tmp_path_factory):
        """THE FINDING THAT MATTERS, as a falsifier. The retired tail-slice law
        forbade this file shape outright; the module-bottom convention is what
        keeps registry receipts from rotting, and stage 4's g7 rule increments
        this dict from exactly such a helper BY DESIGN. L4 must accept it, and
        L7 must accept a new module-level helper appended after _gate_step --
        the positional law it replaces made that red and forced the persistence
        builder to place its helper above the hook instead."""
        root = _scratch(tmp_path_factory, "f3_bottom", LOOP_ONLY)
        lines = _lines(root, "cognitive_loop.py")
        lines += ["", "",
                  "def _pg_bump_falsifier(loop):",
                  '    """[PLAN-GATE] a module-bottom helper, appended AFTER the hook."""',
                  '    loop._plan_gate["g7"] = int(loop._plan_gate.get("g7", 0)) + 1']
        _rewrite(root, "cognitive_loop.py", lines)
        reds = _law_reds(_laws(root))
        assert "l4_plan_gate_on_the_cycle_path" not in reds, (
            "a module-bottom helper that touches _plan_gate went red -- the "
            "tail slice is back and the receipt-protecting convention is "
            "forbidden again")
        assert "l7_gate_hook_is_module_level" not in reds, (
            "appending a module-level helper AFTER _gate_step went red -- that "
            "is the positional law L7 replaced, and it is the reason a build "
            "was shaped by a gate rather than by design")

    def test_moving_the_hook_into_the_class_reds_l7(self, tmp_path_factory):
        root = _scratch(tmp_path_factory, "f3_hook", LOOP_ONLY)
        laws = _laws(root)
        loop = os.path.join(root, "cognitive_loop.py")
        t = laws.tree(loop)
        hook = [n for n in t.body if isinstance(n, ast.FunctionDef)
                and n.name == "_gate_step"][0]
        lines = _lines(root, "cognitive_loop.py")
        body = lines[hook.lineno - 1:hook.end_lineno]
        del lines[hook.lineno - 1:hook.end_lineno]
        cls = laws.scope(t, "CognitiveLoop")
        first_method = min(n.lineno for n in cls.body
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        lines[first_method - 1:first_method - 1] = ["    " + b for b in body] + [""]
        _rewrite(root, "cognitive_loop.py", lines)
        assert "l7_gate_hook_is_module_level" in _law_reds(_laws(root)), (
            "the shadow gate's hook was moved INSIDE CognitiveLoop and L7 "
            "stayed green -- the fact the positional law protected is lost")


# ─────────────────────────────────────────────────────────────────────────────
# F4 · ordinal is honest (and the residue it cannot see)
# ─────────────────────────────────────────────────────────────────────────────

class TestF4OrdinalIsHonest:

    def test_an_ordinal_past_the_count_reds_naming_ordinal_and_count(self, tmp_path_factory):
        root = _scratch(tmp_path_factory, "f4_beyond", LOOP_ONLY)
        r = _row(root, "bank-core")
        site = parse_site(r.site_cell)
        bad = site._replace(ordinal=site.ordinal + 9)
        reg = _lines(root, REGISTRY_REL)
        reg[r.idx] = reg[r.idx].replace(r.site_cell, bad.render())
        _rewrite(root, REGISTRY_REL, reg)
        gate = _gate(root)
        entry = [e for e in gate._LIVE if e.name == "bank-core"][0]
        with pytest.raises(AssertionError) as ei:
            gate.TestLiveEntries().test_claim_site_region_references_symbol(entry)
        msg = str(ei.value)
        assert "#%d" % bad.ordinal in msg and "node(s) exist" in msg, (
            "the ordinal failure must name the ordinal claimed AND the count "
            "seen, so the row can be repaired without a bisect: %r" % msg[:300])

    def test_a_same_name_call_inserted_after_the_anchor_stays_green(self, tmp_path_factory):
        root = _scratch(tmp_path_factory, "f4_after", LOOP_ONLY)
        site, node = _anchored(root, "bank-core")
        stmt = _statement(root, site.file, node)
        pad = _indent(_lines(root, site.file)[stmt.lineno - 1])
        _insert(root, site.file, (stmt.end_lineno or stmt.lineno) + 1,
                [pad + "PredictorBank()  # a SECOND call, AFTER the anchor"])
        green = _verdict1(_gate(root), "bank-core",
                          "test_claim_site_region_references_symbol")
        assert green is True, (
            "a same-name call added AFTER the anchored one forced a refresh -- "
            "the ordinal must not move when nothing before it changed")

    def test_residue_a_call_inserted_before_the_anchor_is_invisible(self, tmp_path_factory):
        """A NAMED RESIDUE, asserted so it cannot be forgotten.

        Prereg §1.4 calls "a NEW same-callee call inserted BEFORE the anchored
        one inside the same function" the one legitimate refresh trigger that
        remains. A six-cell fingerprint whose @LINE is NEVER asserted (§1.2,
        ruled) cannot see it: ORDINAL 0 now names the new node, the count grew
        rather than shrank, and the courtesy is not evidence. Asserting the
        courtesy as a floor WOULD catch it -- and would make every DELETION
        above a site red, which is the same rot in the other direction.

        So the gate is GREEN here, deliberately, and this test pins that fact.
        IT GOES RED THE DAY SOMEONE CLOSES IT -- which is the queued work:
        receiver-qualified fingerprints (PROCTOR decision 3) or a 7th column
        carrying the count (prereg OPEN FOR REVIEW). Until then the residue is
        on the record instead of in the dark."""
        root = _scratch(tmp_path_factory, "f4_before", LOOP_ONLY)
        site, node = _anchored(root, "bank-core")
        stmt = _statement(root, site.file, node)
        pad = _indent(_lines(root, site.file)[stmt.lineno - 1])
        _insert(root, site.file, stmt.lineno,
                [pad + "PredictorBank()  # a SECOND call, BEFORE the anchor"])
        green = _verdict1(_gate(root), "bank-core",
                          "test_claim_site_region_references_symbol")
        assert green is True, (
            "the insert-BEFORE residue has been CLOSED -- delete this test and "
            "record which mechanism closed it (receiver qualification, or a "
            "count column). Do not re-open the residue to make it pass.")


# ─────────────────────────────────────────────────────────────────────────────
# F5 · absences are named, and nothing is written for them
# ─────────────────────────────────────────────────────────────────────────────

class TestF5AbsencesAreNamed:

    def test_an_unresolvable_row_is_named_and_left_alone(self, tmp_path, capsys):
        """A registry holding ONE old-form row that points at a line with no
        node of its name: migrate reports it BY NAME, writes nothing for it,
        and the gate goes on reading the old form for that row."""
        reg = tmp_path / "R.md"
        reg.write_text(
            "| name | symbol | site | status | date | note |\n"
            "|---|---|---|---|---|---|\n"
            "| bank-core | engines.egocentric.bank:PredictorBank | "
            "cognitive_loop.py:1 | LIVE | 2026-08-21 | a claim pointing at the "
            "module docstring |\n", encoding="utf-8")
        before = reg.read_text(encoding="utf-8")
        census, absences, changed = migrate(str(reg), write=True)
        capsys.readouterr()
        assert [a.name for a in absences] == ["bank-core"], (
            "the unresolvable row was not NAMED: %r" % (absences,))
        assert absences[0].reason.strip(), "an absence with no reason is not named"
        assert changed == [], "the tool wrote a fingerprint it had to guess"
        assert reg.read_text(encoding="utf-8") == before, (
            "migrate rewrote a registry it could not resolve -- ties and "
            "empties are absences and the tool never chooses")
        assert parse_site("cognitive_loop.py:1").fingerprinted is False, (
            "the gate must still read the OLD form for a row that has not "
            "migrated (both forms are accepted until the last row leaves)")

    def test_the_shipped_registry_has_no_unnamed_absences(self):
        census, absences, changed = migrate(os.path.join(REPO, REGISTRY_REL),
                                            write=False)
        assert not absences, (
            "the shipped registry still holds unresolvable rows: %r"
            % [a.name for a in absences])
        assert changed == [], "migrate would rewrite the shipped registry"
        assert census["already-fingerprinted"] == len(read_rows(
            os.path.join(REPO, REGISTRY_REL))[1])


# ─────────────────────────────────────────────────────────────────────────────
# F6 · THE ORACLE (prereg §4)
# ─────────────────────────────────────────────────────────────────────────────
#
# The OLD gate cannot parse a fingerprint cell at all (its parser does
# `int(site.rsplit(":", 1)[1])`). So the comparison that carries the claim is:
# OLD gate over the PRE-MIGRATION registry (HEAD) vs NEW gate over the MIGRATED
# registry, over ONE tree. Same rows, same names, same tests -- and the verdict
# vectors must agree everywhere, with the reasons free to differ (decline-branch
# and goal-abduction-plan now pass for the right reason for the first time).

OLD_GATE_REL = "tests/gate/_oracle_old_gate.py"

# Measured on this tree, 2026-08-21. The prereg's figure was 24, taken when the
# registry held 60 LIVE rows; it now holds 89 LIVE + 20 SEVERED. The claim is
# the SHAPE -- every one of these is a pure line shift, so every one is a false
# positive -- and the number is pinned so it cannot drift unremarked.
SHIFT_REDS_OLD = 37


def _oracle_tree(tmp_path_factory, name: str) -> str:
    root = _scratch(tmp_path_factory, name)
    old_gate = head_blob(GATE_REL)
    old_reg = head_blob(REGISTRY_REL)
    assert old_gate and old_reg, (
        "the oracle needs the PRE-MIGRATION gate and registry from HEAD and "
        "git did not return them")
    with open(os.path.join(root, OLD_GATE_REL.replace("/", os.sep)), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(old_gate)
    with open(os.path.join(root, "OLD_REGISTRY.md"), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write(old_reg)
    return root


def _old_gate(root: str):
    """The PRE-MIGRATION gate, pointed at the PRE-MIGRATION registry. It cannot
    read a fingerprint cell at all (its parser does int(rsplit(":", 1)[1])), so
    the comparison the oracle can actually make is old-gate-over-old-registry
    against new-gate-over-new-registry, on ONE tree."""
    prev = os.environ.get("OURO_WIRING_REGISTRY")
    os.environ["OURO_WIRING_REGISTRY"] = os.path.join(root, "OLD_REGISTRY.md")
    try:
        return _load(os.path.join(root, OLD_GATE_REL.replace("/", os.sep)))
    finally:
        if prev is None:
            os.environ.pop("OURO_WIRING_REGISTRY", None)
        else:
            os.environ["OURO_WIRING_REGISTRY"] = prev


def _old_verdicts(root: str) -> Dict[Tuple[str, str], bool]:
    return _verdicts(_old_gate(root))


def _old_verdict1(root: str, rowname: str, testname: str) -> bool:
    return _verdict1(_old_gate(root), rowname, testname)


class TestF6TheOracle:

    @pytest.fixture(scope="class")
    def baseline(self, tmp_path_factory):
        root = _oracle_tree(tmp_path_factory, "oracle_base")
        return root, _old_verdicts(root), _verdicts(_gate(root))

    def test_the_verdict_vectors_are_identical(self, baseline):
        _, old, new = baseline
        assert set(old) == set(new), (
            "the two gates do not even see the same rows/tests: %r"
            % sorted(set(old) ^ set(new))[:10])
        differ = sorted(k for k in old if old[k] != new[k])
        assert not differ, (
            "the migration CHANGED a verdict: %r. The fingerprint must state "
            "the same facts the position stated, not new ones." % differ[:12])
        assert not [k for k, v in new.items() if not v], "the tree is not settled"

    def test_mutation_i_a_rotted_row_fails_on_both(self, tmp_path_factory):
        """Rot the SAME row in each registry the way each form can be rotted:
        old form -> the line set to 1; new form -> a bogus ENCLOSING."""
        root = _oracle_tree(tmp_path_factory, "oracle_rot")
        r = _row(root, "bank-core")
        site = parse_site(r.site_cell)
        reg = _lines(root, REGISTRY_REL)
        reg[r.idx] = reg[r.idx].replace(
            r.site_cell, site._replace(enclosing="CognitiveLoop.no_such_method").render())
        _rewrite(root, REGISTRY_REL, reg)
        old_lines = _lines(root, "OLD_REGISTRY.md")
        for i, ln in enumerate(old_lines):
            if ln.startswith("| bank-core |"):
                old_lines[i] = ln.replace("cognitive_loop.py:2227", "cognitive_loop.py:1")
        _rewrite(root, "OLD_REGISTRY.md", old_lines)
        name = "test_claim_site_region_references_symbol"
        assert _old_verdict1(root, "bank-core", name) is False, (
            "the OLD gate accepted a rotted row")
        assert _verdict1(_gate(root), "bank-core", name) is False, (
            "the NEW gate accepted a rotted row")

    def test_mutation_ii_a_broken_wire_fails_both_tests_on_both_gates(self, tmp_path_factory):
        """THE KNOWN-NEGATIVE (prereg §6: if this ever PASSES on the new gate,
        undo the build). Delete every production reference to the organ."""
        root = _oracle_tree(tmp_path_factory, "oracle_cut")
        rel = "cognitive_loop.py"
        laws = _laws(root)
        hits = [n for n in ast.walk(laws.tree(os.path.join(root, rel)))
                if (isinstance(n, ast.Name) and n.id == "PredictorBank")
                or (isinstance(n, ast.Attribute) and n.attr == "PredictorBank")]
        for n in sorted(hits, key=lambda n: -n.lineno):
            _delete_statement(root, rel, n)
        # ...and the `from ... import PredictorBank` beside it. An ImportFrom
        # produces no Name node, so the sweep above cannot see it -- which is
        # the vulture blind spot this registry exists to close. Left in place
        # it would satisfy the OLD gate's +/-30 substring region on its own: a
        # cut wire reading as wired, on an import. The class DEFINITION in
        # engines/egocentric/bank.py is untouched -- this is a CUT WIRE, not a
        # deleted organ.
        _rewrite(root, rel, [ln for ln in _lines(root, rel)
                             if "import PredictorBank" not in ln])
        for gate_v in (_old_verdicts(root), _verdicts(_gate(root))):
            assert gate_v[("bank-core", "test_claim_site_region_references_symbol")] is False
            assert gate_v[("bank-core", "test_symbol_referenced_from_production")] is False

    def test_mutation_iii_a_pure_line_shift_reds_the_old_gate_and_not_the_new(
            self, tmp_path_factory):
        """THE WHOLE ARGUMENT, in one number. 200 lines inserted above every
        cognitive_loop.py claim site: N rows red on the old gate, ZERO on the
        new. Every one of the N is a false positive -- the tree's structure is
        byte-for-byte the same, only its line numbers moved."""
        root = _oracle_tree(tmp_path_factory, "oracle_shift")
        lines = _lines(root, "cognitive_loop.py")
        _rewrite(root, "cognitive_loop.py",
                 ["# oracle shift %d" % i for i in range(200)] + lines)
        old = _old_verdicts(root)
        new = _verdicts(_gate(root))
        old_reds = sorted(k for k, v in old.items() if not v)
        new_reds = sorted(k for k, v in new.items() if not v)
        assert not new_reds, (
            "the NEW gate red on a pure line shift: %r -- the fingerprint is "
            "still carrying a position" % new_reds[:12])
        assert len(old_reds) == SHIFT_REDS_OLD, (
            "the old gate red %d rows on the shift, not the pinned %d: %r. If "
            "this number moved, say why in the commit -- it is the size of the "
            "false-positive load this build removes."
            % (len(old_reds), SHIFT_REDS_OLD, old_reds[:12]))
        assert all(k[1] == "test_claim_site_region_references_symbol"
                   for k in old_reds), (
            "the shift broke something other than the region check: %r" % old_reds[:6])


# ─────────────────────────────────────────────────────────────────────────────
# The cell grammar itself
# ─────────────────────────────────────────────────────────────────────────────

class TestTheCellGrammar:

    def test_both_forms_parse_and_round_trip(self):
        old = parse_site("cognitive_loop.py:2227")
        assert not old.fingerprinted and old.line == 2227
        assert old.render() == "cognitive_loop.py:2227"
        new = parse_site("cognitive_loop.py:CognitiveLoop.record_result/CALL:PredictorBank#0@2225")
        assert new.fingerprinted and new.enclosing == "CognitiveLoop.record_result"
        assert (new.kind, new.name, new.ordinal, new.line) == ("CALL", "PredictorBank", 0, 2225)
        assert new.render().endswith("#0@2225")
        assert new.demoted() == "cognitive_loop.py:2225", (
            "demote must recover the old form from the courtesy the cell "
            "carries -- that is the undo (prereg §7)")

    def test_a_malformed_cell_raises_rather_than_being_ignored(self):
        for bad in ("cognitive_loop.py:CognitiveLoop/CALL:x#0",      # no @LINE
                    "cognitive_loop.py:CognitiveLoop/WHAT:x#0@1",    # no such KIND
                    "cognitive_loop.py:CognitiveLoop/CALL:x@1",      # no ordinal
                    "no_colon_at_all"):
            with pytest.raises(ValueError):
                parse_site(bad)

    def test_the_registry_is_fully_migrated_and_the_old_branch_is_still_live(self):
        """State of the migration, asserted rather than remembered: every
        shipped row carries a fingerprint, AND the gate still accepts the old
        form. The old-form branch retires in the commit AFTER the last row
        leaves it (PROCTOR decision 5) -- which is the NEXT commit, not this
        one."""
        rows = read_rows(os.path.join(REPO, REGISTRY_REL))[1]
        stragglers = [r.name for r in rows if not parse_site(r.site_cell).fingerprinted]
        assert not stragglers, "rows still on the old form: %r" % stragglers
        gate = _load(os.path.join(REPO, GATE_REL.replace("/", os.sep)))
        assert not gate.Entry("n", "m", "q", "f.py", 1, "LIVE", "d", "").fingerprinted
