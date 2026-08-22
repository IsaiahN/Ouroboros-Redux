"""GATE: THE ORIGIN MARKER (record/prereg/PREREG_DRAIN_ORIGIN.md §B; record/canon/CLAIM.md, verified-not-asserted).

⭐ WHY: READ, not asserted -- 1,514 atom records; ZERO carried `imported`, ZERO carried
`source_game`. local-vs-imported was carried by the ABSENCE OF FIELDS, which is the
INEXPRESSIBLE-STATE GENUS: the moment any path writes source_game (a schema default, a
migration, a seeding bug) the distinction collapses SILENTLY and RETROSPECTIVELY. And
provenance is the ONLY discriminator between CORROBORATION (convergent minting) and
SURPLUS (adopted import) -- contents cannot distinguish them, so it cannot be
reconstructed afterward.

THE BUILD (instrumentation; additive; no behavior change): every atom record gains AT
WRITE TIME a POSITIVE marker --
  origin = "local" | "imported";  mint_seq;  source_game (imported only).
Local mints stamp it at the Gamma.add path (MDLMint.consider -> gamma.add);
consumer.seed_imports stamps origin="imported" + source_game.

THE LAW UNDER TEST: a legacy record with NO origin reads UNKNOWN, and NO consumer may
infer LOCAL FROM ABSENCE -- asserted semantically (origin_of) AND mechanically (a scan
of production for `origin`-defaults-to-local).

Run pre-build: FAILED (effects had no ORIGIN_* / origin_of; Gamma.add wrote no origin
or mint_seq; seed_imports wrote no origin; the registry row did not exist).
"""
from __future__ import annotations

import ast
import glob
import os
import re
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer, effects
from engines.egocentric.effects import Gamma
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.mint import MDLMint
from tools.wiring_receipts import build_index, parse_file, parse_site  # noqa: E402

ATOMS_TOPIC = "atoms"
GAME, LEVEL = "g_home", 2


def _fab(root, agent="agentH", kin="kinH", seeds=()):
    return KnowledgeFabric(str(root), seeds=[str(s) for s in seeds],
                           agent_id=agent, kin_key=kin)


def _recolour(n=5, cell=(2, 2), src=2, dst=3):
    b = np.full((n, n), src, dtype=int)
    a = b.copy()
    a[cell] = dst
    return b, a


def _atoms(fabric):
    return fabric.query("collective", ATOMS_TOPIC)


# ── (1) the vocabulary: three words, and UNKNOWN is not LOCAL ────────────────

class TestVocabulary:

    def test_origin_words_exist_and_are_distinct(self):
        assert effects.ORIGIN_LOCAL == "local"
        assert effects.ORIGIN_IMPORTED == "imported"
        assert effects.ORIGIN_UNKNOWN not in (effects.ORIGIN_LOCAL,
                                              effects.ORIGIN_IMPORTED), (
            "UNKNOWN must be its own word -- collapsing it into LOCAL is the "
            "absence-as-signal defect this build exists to remove")

    def test_absence_reads_unknown_never_local(self):
        for rec in ({}, {"atom": {"key": "k"}}, {"origin": None},
                    {"origin": ""}, {"origin": "LOCAL-ish"}, None, 7):
            assert effects.origin_of(rec) == effects.ORIGIN_UNKNOWN, (
                "a record with no VALID origin must read UNKNOWN: %r" % (rec,))


# ── (2) local mints stamp origin=local + mint_seq at write time ──────────────

class TestLocalMint:

    def test_a_locally_minted_atom_carries_origin_local_and_mint_seq(self, tmp_path):
        fab = _fab(tmp_path / "mint")
        mint = MDLMint(Gamma(fab))
        b, a = _recolour()
        out = mint.consider(b, 1, a, GAME, LEVEL)
        assert out["verdict"] == "mint", "the fixture must actually mint"
        rows = _atoms(fab)
        assert len(rows) == 1
        rec = rows[0]
        assert rec["origin"] == effects.ORIGIN_LOCAL, (
            "a mint in this frame is LOCAL, written AT WRITE TIME")
        assert isinstance(rec["mint_seq"], int)
        assert "source_game" not in rec, (
            "source_game is IMPORTED-ONLY -- a local atom carrying one is the "
            "silent collapse record/canon/CLAIM.md names")
        assert effects.origin_of(rec) == effects.ORIGIN_LOCAL

    def test_mint_seq_is_positional_and_strictly_increasing(self, tmp_path):
        fab = _fab(tmp_path / "seqs")
        g = Gamma(fab)
        ids = [g.add({"kind": "EFFECT", "key": "k%d" % i,
                      "transform": {"before": [[0]], "after": [[1]]}},
                     GAME, LEVEL) for i in range(3)]
        assert len(set(ids)) == 3
        seqs = [int(r["mint_seq"]) for r in _atoms(fab)]
        assert seqs == sorted(seqs) and len(set(seqs)) == 3, (
            "mint_seq must be a monotone at-write-time stamp, got %r" % seqs)

    def test_composites_are_stamped_too(self, tmp_path):
        """A COMPOSITE is an atom record on the same stream: it gets the marker
        or the stream has a silent hole."""
        fab = _fab(tmp_path / "compose")
        g = Gamma(fab)
        a1 = g.add({"kind": "EFFECT", "key": "k1",
                    "transform": {"before": [[0]], "after": [[1]]}}, GAME, LEVEL)
        a2 = g.add({"kind": "EFFECT", "key": "k2",
                    "transform": {"before": [[1]], "after": [[2]]}}, GAME, LEVEL)
        cid = g.compose([a1, a2], GAME, LEVEL)
        assert cid is not None
        comp = [r for r in _atoms(fab) if r["id"] == cid][0]
        assert comp["origin"] == effects.ORIGIN_LOCAL
        assert isinstance(comp["mint_seq"], int)

    def test_a_bogus_origin_degrades_to_unknown_never_to_local(self, tmp_path):
        fab = _fab(tmp_path / "bogus")
        Gamma(fab).add({"kind": "EFFECT", "key": "kx"}, GAME, LEVEL,
                       origin="whatever")
        assert _atoms(fab)[0]["origin"] == effects.ORIGIN_UNKNOWN


# ── (3) seeded imports stamp origin=imported + source_game ───────────────────

def _import_books(tmp_path):
    """A home fabric holding one import_candidate carrying a source_game -- the
    shape _close_hit writes."""
    fab = _fab(tmp_path / "home")
    b, a = _recolour()
    fab.append("collective", "import_candidates", {
        "game": GAME, "level": LEVEL, "src_seq": 1,
        "atom": {"kind": "EFFECT", "arity": 2, "key": "imported-k",
                 "sigma": consumer.sigma_of(b, a)},
        "source_game": "gSRC", "source_seq": 4})
    return fab


class TestSeededImport:

    def test_a_seeded_import_carries_origin_imported_and_source_game(self, tmp_path):
        fab = _import_books(tmp_path)
        gamma = Gamma(fab)
        assert consumer.seed_imports(gamma, fab, GAME, LEVEL) == 1
        rec = _atoms(fab)[0]
        assert rec["origin"] == effects.ORIGIN_IMPORTED, (
            "an adopted import is the SURPLUS half of the claim -- it must say so")
        assert rec["source_game"] == "gSRC"
        assert isinstance(rec["mint_seq"], int)
        assert effects.origin_of(rec) == effects.ORIGIN_IMPORTED
        assert rec["atom"]["imported"] is True, "the legacy flag stays (additive)"

    def test_origin_is_on_the_record_never_inside_the_copied_atom(self, tmp_path):
        """The atom dict travels across fabrics (candidates copy it verbatim); an
        origin written INSIDE it would be re-adopted as another frame's truth."""
        fab = _import_books(tmp_path)
        consumer.seed_imports(Gamma(fab), fab, GAME, LEVEL)
        assert "origin" not in _atoms(fab)[0]["atom"]

    def test_seed_imports_is_idempotent_through_the_origin_read(self, tmp_path):
        fab = _import_books(tmp_path)
        gamma = Gamma(fab)
        assert consumer.seed_imports(gamma, fab, GAME, LEVEL) == 1
        assert consumer.seed_imports(gamma, fab, GAME, LEVEL) == 0
        assert len(_atoms(fab)) == 1


# ── (4) the law: nothing infers LOCAL from ABSENCE ───────────────────────────

class TestNoInferenceFromAbsence:

    def test_a_legacy_record_reads_unknown_and_is_not_local(self, tmp_path):
        """OLD BOOKS: an atom record written before this build. It must read
        UNKNOWN forever -- never be back-filled or assumed local."""
        fab = _fab(tmp_path / "legacy")
        fab.append("collective", ATOMS_TOPIC, {
            "id": "old:0", "type": "structural", "game": GAME, "level": 1,
            "atom": {"kind": "EFFECT", "key": "old-k"}})
        rec = _atoms(fab)[0]
        assert "origin" not in rec
        assert effects.origin_of(rec) == effects.ORIGIN_UNKNOWN
        assert effects.origin_of(rec) != effects.ORIGIN_LOCAL

    def test_a_legacy_imported_atom_is_not_read_as_local(self, tmp_path):
        """The pre-build import shape (atom["imported"]=True, no envelope
        origin): UNKNOWN provenance, and seed_imports still dedupes it."""
        fab = _import_books(tmp_path)
        fab.append("collective", ATOMS_TOPIC, {
            "id": "legacy-imp:0", "type": "structural", "game": GAME, "level": 1,
            "atom": {"kind": "EFFECT", "key": "imported-k", "imported": True}})
        assert effects.origin_of(_atoms(fab)[0]) == effects.ORIGIN_UNKNOWN
        assert consumer.seed_imports(Gamma(fab), fab, GAME, LEVEL) == 0, (
            "the legacy imported flag must keep deduping (old books unchanged)")

    def test_no_production_module_defaults_origin_to_local(self):
        """MECHANICAL: a `.get("origin", "local")` anywhere converts absence back
        into a positive claim -- exactly the collapse this build removes."""
        get_default = re.compile(r"""\.get\(\s*['"]origin['"]\s*,\s*([^)]*)\)""")
        or_local = re.compile(
            r"""origin[^\n]*\bor\b\s*(ORIGIN_LOCAL|['"]local['"])""")
        offenders = []
        for rel in _prod_files():
            with open(os.path.join(REPO, rel), encoding="utf-8",
                      errors="ignore") as fh:
                for n, line in enumerate(fh, 1):
                    for m in get_default.finditer(line):
                        d = m.group(1)
                        if "UNKNOWN" not in d and "unknown" not in d:
                            offenders.append("%s:%d %s" % (rel, n, line.strip()))
                    if or_local.search(line):
                        offenders.append("%s:%d %s" % (rel, n, line.strip()))
        assert not offenders, (
            "production infers LOCAL from ABSENCE (absence-as-signal is the "
            "inexpressible-state genus): %r" % offenders)

    def test_origin_of_is_the_only_reader_and_it_is_total(self):
        """No production module may read the raw "origin" key directly -- every
        read goes through origin_of, which is where UNKNOWN is guaranteed."""
        raw = re.compile(r"""\[\s*['"]origin['"]\s*\]|\.get\(\s*['"]origin['"]""")
        offenders = []
        for rel in _prod_files():
            if rel == "engines/egocentric/effects.py":
                continue                    # origin_of's own definition
            with open(os.path.join(REPO, rel), encoding="utf-8",
                      errors="ignore") as fh:
                for n, line in enumerate(fh, 1):
                    if raw.search(line):
                        offenders.append("%s:%d" % (rel, n))
        assert not offenders, (
            "raw 'origin' reads outside origin_of: %r" % offenders)


PROD_GLOBS = ("*.py", "engines/**/*.py", "rungs/**/*.py", "src/**/*.py")


def _prod_files():
    out, seen = [], set()
    for pat in PROD_GLOBS:
        for path in glob.glob(os.path.join(REPO, pat), recursive=True):
            rel = os.path.relpath(path, REPO).replace("\\", "/")
            base = os.path.basename(rel)
            if (rel in seen or "__pycache__" in rel
                    or base.startswith("_investigate")
                    or base in ("_temp_check.py", "vulture_whitelist.py")):
                continue
            seen.add(rel)
            out.append(rel)
    return sorted(out)


# ── (5) additive: old books still load, nothing else moved ───────────────────

class TestAdditive:

    def test_old_books_load_and_drain_unchanged(self, tmp_path):
        """A pre-build fabric (no origin anywhere): mint, match and consume all
        run; the marker is instrumentation, not a gate."""
        fab = _fab(tmp_path / "old")
        b, a = _recolour()
        fab.append("collective", ATOMS_TOPIC, {
            "id": "old:0", "type": "structural", "game": "gSRC", "level": 1,
            "atom": {"kind": "EFFECT", "arity": 2, "key": "old-k",
                     "sigma": consumer.sigma_of(b, a)}})
        rec = {"slot": "S", "residual": 1.0, "game": GAME, "level": LEVEL}
        rec.update(consumer.characterize(b, a, slot="S", residual=1.0))
        fab.append("collective", "import_queue", rec)
        rep = consumer.consume(fab, GAME, LEVEL, 8)
        assert rep["candidates"] == 1 and rep["drained"] == 1
        assert effects.origin_of(_atoms(fab)[0]) == effects.ORIGIN_UNKNOWN

    def test_gamma_add_signature_stays_backward_compatible(self):
        sig = [p.name for p in __import__("inspect").signature(Gamma.add)
               .parameters.values()]
        assert sig[:4] == ["self", "atom", "game", "level"], (
            "existing callers pass (atom, game, level) positionally: %r" % sig)

    def test_origin_fields_are_json_native(self, tmp_path):
        fab = _fab(tmp_path / "json")
        Gamma(fab).add({"kind": "EFFECT", "key": "k"}, GAME, LEVEL)
        path = os.path.join(str(tmp_path / "json"), "collective", "atoms.jsonl")
        with open(path, encoding="utf-8") as fh:
            line = fh.read()
        assert '"origin": "local"' in line or '"origin":"local"' in line


# ── (6) the registry receipt ─────────────────────────────────────────────────

class TestRegistryReceipt:

    def _row(self, name):
        path = os.path.join(REPO, "record", "canon", "WIRING_REGISTRY.md")
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith("| %s |" % name):
                    return [c.strip() for c in line.strip().strip("|").split("|")]
        return None

    def test_origin_marker_row_is_live_with_a_live_path_receipt(self):
        row = self._row("origin-marker")
        assert row is not None, "no origin-marker row in record/canon/WIRING_REGISTRY.md"
        assert row[3] == "LIVE", "the marker ships LIVE (got %r)" % row[3]
        assert "effects:origin_of" in row[1]
        assert ".py:" in row[2]

    def test_the_receipt_site_really_calls_origin_of(self):
        """UPDATED 2026-08-21 (PREREG_SYMBOL_RECEIPTS.md §1): the site cell is a
        SYMBOL FINGERPRINT, not a line. The old body read ±5 lines around the
        claimed line and looked for the substring "origin_of" — the same
        substring-in-a-region proxy that let decline-branch pass on the word
        "match" inside `return out`. Now the cell must NAME origin_of and the
        node it names must exist; the courtesy line is used only to read the
        source back for the reader."""
        row_cell = self._row("origin-marker")[2]
        site = parse_site(row_cell)
        assert site.fingerprinted, (
            "the origin-marker row is still on the old position form: %r" % row_cell)
        assert site.name == "origin_of", (
            "the receipt does not name origin_of at all: %r" % row_cell)
        index, _quals = build_index(parse_file(os.path.join(REPO, site.file)))
        nodes = index.get((site.enclosing, site.kind, site.name)) or []
        assert len(nodes) > site.ordinal, (
            "the claimed %s of origin_of inside %r does not exist in %s: %r"
            % (site.kind, site.enclosing, site.file, row_cell))
        with open(os.path.join(REPO, site.file), encoding="utf-8") as fh:
            lines = fh.readlines()
        assert "origin_of" in lines[nodes[site.ordinal].lineno - 1]

    def test_origin_of_has_a_production_caller(self):
        """rung 0c's DONE STANDARD: something in the live path calls it with real
        inputs -- an unread marker is a stream with no named consumer."""
        callers = []
        for rel in _prod_files():
            if rel == "engines/egocentric/effects.py":
                continue
            try:
                with open(os.path.join(REPO, rel), encoding="utf-8",
                          errors="ignore") as fh:
                    tree = ast.parse(fh.read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if ((isinstance(node, ast.Name) and node.id == "origin_of")
                        or (isinstance(node, ast.Attribute)
                            and node.attr == "origin_of")):
                    callers.append("%s:%d" % (rel, node.lineno))
        assert callers, "origin_of has ZERO production callers"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
