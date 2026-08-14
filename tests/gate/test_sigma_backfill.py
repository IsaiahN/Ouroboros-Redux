"""B13 GATE: tools/sigma_backfill.py — sigma for the legacy atoms, offline, atomically.

⭐ WHY (BUILD_PROGRAM_2 W3, B13). Signature-first recognition needs EVERY atom to carry
its prediction-signature; the legacy atoms predate sigma. The backfill derives sigma
from the STORED before/after patches (no re-observation — conservation, bbox class,
changed class and colour-delta over the bbox patch equal the full-frame values, because
cells outside the bbox are unchanged by construction). Fabrics are append-only in live
operation: the tool REWRITES atoms.jsonl atomically with a .bak and REFUSES to run
while other python workers are alive (--force overrides; the operator owns the outcome).

Run pre-build: these failed (tools.sigma_backfill absent).
"""
from __future__ import annotations

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric.effects import Gamma, learn_effect
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.mint import MDLMint
from tools import sigma_backfill


def _event(n=5, cell=(2, 2), src=2, dst=3):
    b = np.full((n, n), src, dtype=int)
    a = b.copy()
    a[cell] = dst
    return b, a


def _legacy_fabric(root):
    """A fabric whose atoms PREDATE sigma: raw learn_effect output via Gamma.add,
    plus one corrupt line (a crash mid-write) and one already-sigma'd atom."""
    f = KnowledgeFabric(str(root), agent_id="old", kin_key="kinOld")
    g = Gamma(f)
    b, a = _event()
    g.add(learn_effect(b, 1, a), "g_old", 1)                    # legacy: no sigma
    b2, a2 = _event(cell=(1, 3), dst=7)
    g.add(learn_effect(b2, 1, a2), "g_old", 1)                  # legacy: no sigma
    g.add({"kind": "INERT", "arity": 2, "action": 1, "changed": 0},
          "g_old", 1)                                           # no patches: untouched
    modern = learn_effect(b, 2, a)
    modern["sigma"] = consumer.sigma_of(b, a)
    g.add(modern, "g_old", 1)                                   # already sigma'd
    path = os.path.join(str(root), "collective", "atoms.jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write('{"id": "trunc')                               # crash mid-write
    return f, path


class TestBackfill:

    def test_adds_sigma_where_missing_only(self, tmp_path):
        _f, path = _legacy_fabric(tmp_path / "old")
        total, updated = sigma_backfill.backfill_file(path)
        assert (total, updated) == (4, 2)
        recs = KnowledgeFabric(str(tmp_path / "old")).query("collective", "atoms")
        effects = [r for r in recs if r["atom"].get("kind") == "EFFECT"]
        assert all(isinstance(r["atom"].get("sigma"), dict) for r in effects)
        inert = [r for r in recs if r["atom"].get("kind") == "INERT"]
        assert "sigma" not in inert[0]["atom"], "a patchless atom grew a fake sigma"

    def test_patch_derived_sigma_equals_mint_time_sigma(self, tmp_path):
        """The backfilled sigma is byte-identical to what the mint would have written
        from the full frames — the bbox patch carries the same invariants."""
        f = KnowledgeFabric(str(tmp_path / "new"), agent_id="x", kin_key="k")
        b, a = _event()
        assert MDLMint(Gamma(f)).consider(b, 1, a, "g", 1)["verdict"] == "mint"
        minted = f.query("collective", "atoms")[0]["atom"]["sigma"]
        _f2, path = _legacy_fabric(tmp_path / "old")
        sigma_backfill.backfill_file(path)
        legacy = KnowledgeFabric(str(tmp_path / "old")).query("collective", "atoms")
        back = legacy[0]["atom"]["sigma"]
        assert back == minted

    def test_rewrite_is_atomic_with_bak_and_preserves_other_lines(self, tmp_path):
        _f, path = _legacy_fabric(tmp_path / "old")
        with open(path, encoding="utf-8") as fh:
            before_lines = fh.read().splitlines()
        sigma_backfill.backfill_file(path)
        assert os.path.isfile(path + ".bak"), "no .bak written"
        with open(path + ".bak", encoding="utf-8") as fh:
            assert fh.read().splitlines() == before_lines, ".bak is not the original"
        with open(path, encoding="utf-8") as fh:
            after_lines = fh.read().splitlines()
        assert after_lines[-1] == '{"id": "trunc', "the corrupt line was destroyed"
        # untouched records are preserved byte-for-byte (the INERT and sigma'd lines)
        assert before_lines[2] == after_lines[2]
        assert before_lines[3] == after_lines[3]

    def test_idempotent(self, tmp_path):
        _f, path = _legacy_fabric(tmp_path / "old")
        sigma_backfill.backfill_file(path)
        with open(path, encoding="utf-8") as fh:
            once = fh.read()
        total, updated = sigma_backfill.backfill_file(path)
        assert updated == 0
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == once

    def test_backfill_root_walks_every_scope(self, tmp_path):
        root = tmp_path / "multi"
        for agent in ("a1", "a2"):
            f = KnowledgeFabric(str(root), agent_id=agent, kin_key="k")
            b, a = _event()
            atom = learn_effect(b, 1, a)
            f.append("personal", "atoms", {"id": "x:%s" % agent, "atom": atom})
        f.append("collective", "atoms", {"id": "c:0", "atom": learn_effect(b, 1, a)})
        report = sigma_backfill.backfill_root(str(root))
        assert report["files"] == 3 and report["updated"] == 3

    def test_seq_fields_survive(self, tmp_path):
        _f, path = _legacy_fabric(tmp_path / "old")
        pre = [r["seq"] for r in KnowledgeFabric(str(tmp_path / "old"))
               .query("collective", "atoms")]
        sigma_backfill.backfill_file(path)
        post = [r["seq"] for r in KnowledgeFabric(str(tmp_path / "old"))
                .query("collective", "atoms")]
        assert pre == post


class TestOperatorContract:

    def test_main_refuses_while_workers_alive(self, tmp_path, monkeypatch, capsys):
        _f, _path = _legacy_fabric(tmp_path / "old")
        monkeypatch.setattr(sigma_backfill, "_other_python_pids", lambda: [4242])
        rc = sigma_backfill.main([str(tmp_path / "old")])
        assert rc == 2, "the tool ran with workers alive -- append-only law broken"
        out = capsys.readouterr().out
        assert "REFUS" in out.upper() and "SWARM" in out.upper(), (
            "the refusal must be loud and name the operator contract")

    def test_force_overrides_and_backfills(self, tmp_path, monkeypatch):
        _f, path = _legacy_fabric(tmp_path / "old")
        monkeypatch.setattr(sigma_backfill, "_other_python_pids", lambda: [4242])
        rc = sigma_backfill.main([str(tmp_path / "old"), "--force"])
        assert rc == 0
        recs = KnowledgeFabric(str(tmp_path / "old")).query("collective", "atoms")
        assert isinstance(recs[0]["atom"].get("sigma"), dict)

    def test_main_runs_when_no_other_workers(self, tmp_path, monkeypatch, capsys):
        _f, _path = _legacy_fabric(tmp_path / "old")
        monkeypatch.setattr(sigma_backfill, "_other_python_pids", lambda: [])
        rc = sigma_backfill.main([str(tmp_path / "old")])
        assert rc == 0
        assert "[SIGMA-BACKFILL]" in capsys.readouterr().out, "the run must be loud"
