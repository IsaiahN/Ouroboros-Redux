"""PHASE 3a GATE: the knowledge fabric + the idea economy — memory that ports to Kaggle.

⭐ WHY. Agents must reference the collective stream, their personal stream, and their kin's
stream — WITHOUT a database: pure-Python JSONL directories, seed-overlay read-only (the
verified Kaggle pattern: mounted input + local working). The viral idea economy on top:
MINT only on signal, ECHO pays the origin author (reputation — the viral reward), FALSIFY
pariah-marks defeasibly. v4's version was measured consumer-less; this one is consumer-first.

THE CONTRACT (PREREG_PHASE3A.md / PHASE3_DESIGN.md):
  * `KnowledgeFabric(root, seeds=[...], agent_id=..., kin_key=...)` — stdlib only;
  * `append(scope, topic, record) -> record` (adds monotonic per-stream "seq"; no wall-clock
    in the default path); `query(scope, topic, where=None, limit=None)` — insertion order;
    scope strings: "collective", "personal", "kin" (resolved via agent_id/kin_key);
  * seeds are READ-ONLY overlays: queried, never appended to;
  * a corrupt trailing JSONL line is skipped, never fatal;
  * economy: `mint(idea, game, signal) -> id` (raises ValueError WITHOUT signal — the wheel
    rule extends to memory); `echo(idea_id, by)`; `falsify(idea_id, by)`;
    `credibility(idea_id)`; `reputation(agent_id)`; `priors(game)` ranked: credibility desc,
    personal > kin > collective on ties, pariahs (falsified>echoed) LAST.

Run pre-build: these failed (module absent).
"""
from __future__ import annotations

import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _F():
    try:
        from engines.egocentric.fabric import KnowledgeFabric
    except Exception as e:
        pytest.fail("engines.egocentric.fabric missing (%s) — Phase 3a has not landed" % e)
    from engines.egocentric.fabric import KnowledgeFabric as KF
    return KF


def _mk(tmp_path, name="f", **kw):
    kw.setdefault("agent_id", "agentA")
    kw.setdefault("kin_key", "kinX")
    return _F()(str(tmp_path / name), **kw)


class TestTheFabric:

    def test_append_query_roundtrip_across_scopes(self, tmp_path):
        f = _mk(tmp_path)
        f.append("collective", "ideas", {"x": 1})
        f.append("personal", "ideas", {"x": 2})
        f.append("kin", "ideas", {"x": 3})
        assert [r["x"] for r in f.query("collective", "ideas")] == [1]
        assert [r["x"] for r in f.query("personal", "ideas")] == [2]
        assert [r["x"] for r in f.query("kin", "ideas")] == [3]

    def test_sequence_numbers_are_monotonic_and_deterministic(self, tmp_path):
        f = _mk(tmp_path)
        a = f.append("collective", "t", {"v": "a"})
        b = f.append("collective", "t", {"v": "b"})
        assert b["seq"] == a["seq"] + 1
        f2 = _mk(tmp_path)                       # reopen the same root
        c = f2.append("collective", "t", {"v": "c"})
        assert c["seq"] == b["seq"] + 1, "sequence must continue across reopen (read from disk)"

    def test_where_filter_and_limit(self, tmp_path):
        f = _mk(tmp_path)
        for i in range(6):
            f.append("collective", "t", {"i": i, "even": i % 2 == 0})
        got = f.query("collective", "t", where=lambda r: r["even"], limit=2)
        assert [r["i"] for r in got] == [0, 2]

    def test_seed_overlay_is_readable_and_never_written(self, tmp_path):
        seed_root = tmp_path / "seedA"
        s = _F()(str(seed_root), agent_id="origin", kin_key="kinX")
        s.append("collective", "ideas", {"from": "seed"})
        f = _F()(str(tmp_path / "live"), seeds=[str(seed_root)],
                 agent_id="agentA", kin_key="kinX")
        assert any(r.get("from") == "seed" for r in f.query("collective", "ideas"))
        f.append("collective", "ideas", {"from": "live"})
        s2 = _F()(str(seed_root), agent_id="origin", kin_key="kinX")
        assert all(r.get("from") == "seed" for r in s2.query("collective", "ideas")), (
            "the live fabric wrote into its seed — seeds are READ-ONLY (the /kaggle/input rule)")

    def test_a_corrupt_trailing_line_is_skipped(self, tmp_path):
        f = _mk(tmp_path)
        f.append("collective", "t", {"ok": 1})
        p = tmp_path / "f" / "collective" / "t.jsonl"
        with open(p, "a", encoding="utf-8") as fh:
            fh.write('{"broken": tru')          # crash mid-write
        f2 = _mk(tmp_path)
        assert [r.get("ok") for r in f2.query("collective", "t")] == [1]


class TestTheIdeaEconomy:

    def test_mint_requires_signal(self, tmp_path):
        f = _mk(tmp_path)
        with pytest.raises(ValueError):
            f.mint({"kind": "BE_AT", "cell": [2, 3]}, game="g1", signal=None)
        i = f.mint({"kind": "BE_AT", "cell": [2, 3]}, game="g1",
                   signal={"type": "level_up"})
        assert i

    def test_echo_raises_credibility_and_pays_the_origin(self, tmp_path):
        f = _mk(tmp_path)
        i = f.mint({"kind": "BE_AT", "cell": [1, 1]}, game="g1",
                   signal={"type": "level_up"})
        c0, r0 = f.credibility(i), f.reputation("agentA")
        f2 = _F()(str(tmp_path / "f"), agent_id="agentB", kin_key="kinX")
        f2.echo(i, by="agentB")
        assert f2.credibility(i) > c0
        assert f2.reputation("agentA") > r0, (
            "an echo must pay the ORIGIN author — the viral reward is the economy's whole point")

    def test_falsify_pariah_ranks_defeasibly(self, tmp_path):
        f = _mk(tmp_path)
        good = f.mint({"kind": "BE_AT", "cell": [1, 1]}, game="g1", signal={"type": "level_up"})
        bad = f.mint({"kind": "BE_AT", "cell": [9, 9]}, game="g1", signal={"type": "level_up"})
        f.echo(good, by="agentB")
        f.falsify(bad, by="agentB")
        ids = [p["id"] for p in f.priors("g1")]
        assert ids.index(good) < ids.index(bad), "a pariah must rank below a corroborated idea"
        assert bad in ids, "pariahs are down-ranked, never deleted (defeasible)"

    def test_priors_prefer_nearer_evidence_on_ties(self, tmp_path):
        root = str(tmp_path / "f")
        origin = _F()(root, agent_id="stranger", kin_key="otherKin")
        i_col = origin.mint({"kind": "BE_AT", "cell": [5, 5]}, game="g1",
                            signal={"type": "level_up"}, scope="collective")
        me = _F()(root, agent_id="agentA", kin_key="kinX")
        i_per = me.mint({"kind": "BE_AT", "cell": [6, 6]}, game="g1",
                        signal={"type": "level_up"}, scope="personal")
        ids = [p["id"] for p in me.priors("g1")]
        assert ids.index(i_per) < ids.index(i_col), (
            "at equal credibility, personal evidence outranks collective")


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_mint_lives_only_in_the_credit_path(self):
        src = self._src()
        assert "[EGO-MINT]" in src, "no mint wiring — level-ups compound nothing (starvation)"
        i = src.find(".mint(")
        assert i != -1
        window = src[max(0, i - 1200):i]
        assert "level_changed" in window or "credit" in window, (
            "mint is called outside the credit/level-up path — the wheel rule extends to "
            "memory: the mint compounds nothing on silence")

    def test_the_seed_channel_exists(self):
        src = self._src()
        assert "[EGO-SEED]" in src, "no seed wiring — agents start from zero (starvation)"
        assert ".priors(" in src

    def test_the_falsify_writeback_exists(self):
        src = self._src()
        assert ".falsify(" in src, (
            "no falsify write-back — v4's pariah storage had readers and no writers from live "
            "play; the loop must close")

    def test_the_ledger_port_is_present(self):
        try:
            from engines.egocentric import falsified_ledger  # noqa: F401
        except Exception as e:
            pytest.fail("falsified_ledger port missing: %s" % e)
