"""W4 B17 GATE: new code reads old books — fabric schema compat (CK_LEDGER G4).

⭐ WHY. Builders extend record shapes (ttype, params, sigma, w); Kaggle seed-mounts are
old books BY DEFINITION, and a compat crash today would be SWALLOWED by the containment
style (G1). So: a FROZEN fixture pack of real earlier-era record shapes lives in
tests/gate/fixtures/old_books/ (atoms WITHOUT ttype/params/sigma; settlements and
mint_verdicts WITHOUT w; harvest records; import_queue {slot,residual,seq}), and every
reader that exists is driven against it through the read-only seed-mount pattern.

THE FREEZE IS THE POINT: the fixture files are never "upgraded" to new shapes — a test
here asserts the old fields are still absent. If a reader needs a new field to function,
that reader is broken for every old book on disk, including every Kaggle seed mount.

The consumer (W3 B12, engines/egocentric/consumer.py) may or may not exist while this
gate runs — probe-import pattern: driven when present, skipped (loudly) when absent.

Run pre-build: failed (fixture pack absent).
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "old_books")

OLD_GAME = "og42-deadbeef01"          # the game string old records carry (a runtime key)
OLD_EFFECT_ID = "eff-0ldb00k000000001:0"
OLD_INERT_ID = "INERT:1"
OLD_STREAMS = ("atoms", "settlements", "mint_verdicts",
               "frontier_harvest", "import_queue")


def _fab(tmp_path):
    from engines.egocentric.fabric import KnowledgeFabric
    return KnowledgeFabric(str(tmp_path / "live"), seeds=[FIXTURES],
                           agent_id="agentA", kin_key="kinX")


def _stream_lines(topic):
    p = os.path.join(FIXTURES, "collective", topic + ".jsonl")
    assert os.path.isfile(p), "fixture stream missing: %s" % p
    with open(p, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


class TestTheFrozenPack:

    def test_the_pack_exists(self):
        assert os.path.isdir(FIXTURES), (
            "tests/gate/fixtures/old_books/ missing — the G4 compat gate has no books")
        for topic in OLD_STREAMS:
            assert _stream_lines(topic), "empty fixture stream: %s" % topic

    def test_old_atoms_carry_no_new_era_fields(self):
        """The freeze law: fixtures stay OLD-shaped forever. ttype/params/sigma
        arriving here means someone upgraded the books instead of the readers."""
        for rec in _stream_lines("atoms"):
            atom = rec.get("atom") or {}
            for banned in ("ttype", "params", "sigma"):
                assert banned not in atom, (
                    "fixture atom %r gained new-era field %r — old books must stay old"
                    % (rec.get("id"), banned))
            assert set(rec) == {"id", "type", "game", "level", "atom", "seq"}

    def test_old_settlements_and_verdicts_carry_no_w(self):
        for rec in _stream_lines("settlements"):
            assert "w" not in rec, "old settlement gained w — the fixture is not frozen"
        for rec in _stream_lines("mint_verdicts"):
            assert "w" not in rec, "old mint_verdict gained w — the fixture is not frozen"

    def test_import_queue_entries_are_the_old_triple(self):
        for rec in _stream_lines("import_queue"):
            assert set(rec) == {"slot", "residual", "seq"}


class TestEveryReaderReadsOldBooks:

    def test_fabric_query_returns_records_for_every_old_stream(self, tmp_path):
        f = _fab(tmp_path)
        for topic in OLD_STREAMS:
            got = f.query("collective", topic)
            assert got, "fabric.query returned nothing for old stream %r" % topic
            assert all(isinstance(r.get("seq"), int) for r in got)

    def test_the_seed_mount_is_never_written(self, tmp_path):
        before = {t: open(os.path.join(FIXTURES, "collective", t + ".jsonl"),
                          "rb").read() for t in OLD_STREAMS}
        f = _fab(tmp_path)
        f.append("collective", "settlements", {"agent": "agentA", "game": OLD_GAME,
                                               "level": 0, "action": 1, "members": 1,
                                               "best": 0.0, "nontrivial": False})
        for t in OLD_STREAMS:
            now = open(os.path.join(FIXTURES, "collective", t + ".jsonl"), "rb").read()
            assert now == before[t], (
                "appending to the live fabric mutated fixture stream %r — seeds are "
                "READ-ONLY (the /kaggle/input rule)" % t)

    def test_gamma_loads_and_applies_a_sigma_less_atom(self, tmp_path):
        from engines.egocentric.effects import Gamma, encoding_cost_atom
        g = Gamma(_fab(tmp_path))
        atom = g.get(OLD_EFFECT_ID)
        assert atom is not None, "Gamma cannot see the old EFFECT atom through the seed"
        assert "ttype" not in atom and "sigma" not in atom
        board = np.zeros((4, 4), dtype=int)
        board[1:3, 1:3] = np.asarray(atom["context"])
        out = g.apply(OLD_EFFECT_ID, board)
        assert out is not None, (
            "apply_effect refused a ttype-less atom — the raw path must carry old books")
        assert (out[1:3, 1:3] == np.asarray(atom["transform"]["after"])).all()
        assert encoding_cost_atom(atom) < float("inf")
        lex = g.get(OLD_INERT_ID)
        assert lex is not None and lex.get("kind") == "INERT"

    def test_the_planner_plans_through_an_old_atom(self, tmp_path):
        from engines.egocentric.effects import Gamma
        from engines.egocentric.planner import plan_to_identity
        g = Gamma(_fab(tmp_path))
        atom = g.get(OLD_EFFECT_ID)
        ws = np.zeros((4, 4), dtype=int)
        ws[1:3, 1:3] = np.asarray(atom["context"])
        ref = ws.copy()
        ref[1:3, 1:3] = np.asarray(atom["transform"]["after"])
        plan = plan_to_identity(ws, ref, g, OLD_GAME, 1,
                                budget=100.0, cost_per_action=1.0)
        assert plan is not None and plan["steps"] == [OLD_EFFECT_ID], (
            "the planner cannot route through a sigma-less atom — old vocabulary lost")

    def test_affect_gains_over_w_less_settlements_and_verdicts(self, tmp_path):
        from engines.egocentric.affect import AffectGains
        a = AffectGains(_fab(tmp_path))
        gains = a.gains()
        assert 0.0 <= gains["seed_bias"] <= 1.0
        assert a.MINT_BAR_FLOOR <= gains["mint_bar"] <= a.MINT_BAR_CEIL
        assert "mint_verdicts" in a.narrate()
        assert a.errors == 0, "AffectGains swallowed a read failure on old books"

    def test_frontier_merges_old_harvest_records(self, tmp_path):
        from engines.egocentric.frontier import FrontierBook
        fb = FrontierBook(_fab(tmp_path))
        h = fb.load_harvest(OLD_GAME, 1)
        assert (12, 44) in h["dead"], "conservative dead-merge lost the old records"
        assert (20, 36) in h["effects"]
        assert h["fatal"] and h["deltas"]
        assert fb.errors == 0

    def test_the_mint_prices_against_old_atoms_without_crashing(self, tmp_path):
        from engines.egocentric.effects import Gamma
        from engines.egocentric.mint import MDLMint
        mint = MDLMint(Gamma(_fab(tmp_path)))
        before = np.zeros((4, 4), dtype=int)
        after = before.copy()
        after[0, 0] = 3
        out = mint.consider(before, 2, after, OLD_GAME, 1)
        assert isinstance(out, dict) and "verdict" in out, (
            "MDLMint.consider crashed or went silent over a seed of old-shape atoms")


class TestTheConsumerProbe:
    """W3's consumer may land while this gate runs — drive it when present."""

    def _consumer(self):
        try:
            return importlib.import_module("engines.egocentric.consumer")
        except ImportError:
            pytest.skip("engines/egocentric/consumer.py not landed yet (W3 in flight)")

    def test_seed_imports_tolerates_sigma_less_atoms(self, tmp_path):
        consumer = self._consumer()
        if not hasattr(consumer, "seed_imports"):
            pytest.skip("consumer has no seed_imports yet (interface still landing)")
        from engines.egocentric.effects import Gamma
        f = _fab(tmp_path)
        g = Gamma(f)
        try:
            n = consumer.seed_imports(g, f, OLD_GAME, 1)
        except (KeyError, TypeError, AttributeError) as e:
            pytest.fail(
                "seed_imports crashed over a seed of sigma-less atoms (%r) — old books "
                "must be skipped gracefully, never fatally" % (e,))
        assert isinstance(n, int)

    def test_describe_and_match_skip_sigma_less_atoms_gracefully(self, tmp_path):
        consumer = self._consumer()
        old_atom = _stream_lines("atoms")[0]["atom"]
        for name in ("describe", "match"):
            fn = getattr(consumer, name, None)
            if fn is None:
                continue                     # not part of the landed surface: nothing to hold
            try:
                fn(old_atom)
            except TypeError:
                continue                     # different arity than probed — not a sigma crash
            except (KeyError, AttributeError) as e:
                pytest.fail("consumer.%s crashed on a sigma-less atom (%r) — must skip, "
                            "not crash" % (name, e))
