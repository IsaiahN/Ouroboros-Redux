"""RUNG 0c FLIP GATE: THE RHO MULTI-RUNG LADDER, LIVE (KNOBS Amendment 2 x THE_LADDER 0c).

⭐ WHY: rho_at / rederivation_traffic / rho_report had ZERO production callers
(record/canon/WIRING_REGISTRY.md rho-ladder row, S8) -- every grain conclusion so far came from
hand-run tools, so the partition-artifact fix was a REPORT ARTIFACT, not a
measurement the system takes. THE DONE STANDARD (THE_LADDER rung 0c): a build is
done when something in the live path calls it with real inputs.

THE WIRE UNDER TEST: the consumer's consume() pass computes and PERSISTS a compact
multi-rung reading per drain -- {r0, r1, r2, traffic} vs each source fabric it
ACTUALLY MATCHED against this pass (bounded: only sources with hits or near-misses)
-- appended to the collective "rho_readings" stream (additive record, seq'd,
game + PLAYING level per A3-2). The [RHO] narration line gains r0/r2/traffic.
The beat protocol is the stream's named consumer (THE_LADDER rung 4: "traffic
collapsed + r0 nonzero, or climbing + r0 flat?").

FALSIFIERS: the r1=0-but-r2>0 partition case (same mechanism, different params)
must read exactly that IN THE PERSISTED RECORD; the key-identity traffic case
(the cn04/ka59 shape) must count cross-recognitions BOTH ways; unmatched sources
must NOT appear (bounded per pass); a pass that matched nothing persists nothing;
old-shape (sigma-less) atoms degrade, never raise; the registry row is flipped
LIVE with its receipt in the consumer.

Run pre-build: FAILED (consume() persisted no rho_readings record; the [RHO] line
carried no r0/r2/traffic; the registry row read SEVERED).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric.fabric import KnowledgeFabric

RHO_TOPIC = "rho_readings"


# ── fixtures: synthetic two-fabric books ─────────────────────────────────────

def _recolour(n=5, cells=((2, 2),), src=2, dst=3):
    b = np.full((n, n), src, dtype=int)
    a = b.copy()
    for r, c in cells:
        a[r, c] = dst
    return b, a


def _class_sig(i):
    """A distinct one-cell recolour signature class per integer i."""
    return {"arity": 2, "bbox": "cell", "changed": "1",
            "colour_delta": [[int(i), int(i) + 1]], "conserved": False,
            "mag": "small"}


def _disjoint_sig():
    """>= 2 invariants away from the match sigma: evaluated, neither hit nor
    near-miss -- the source must NOT be touched by the pass."""
    return {"arity": 2, "bbox": "rect", "changed": "5-16",
            "colour_delta": [[7, 8]], "conserved": True, "mag": "large"}


def _rec(game, key, sigma=None, ttype=None, params=None):
    atom = {"kind": "EFFECT", "arity": 2, "key": str(key)}
    if sigma is not None:
        atom["sigma"] = dict(sigma)
    if ttype is not None:
        atom["ttype"] = ttype
    if params is not None:
        atom["params"] = params
    return {"id": "%s:0" % key, "type": "structural", "game": str(game),
            "level": 1, "atom": atom}


def _fab(root, agent="agentX", kin="kinX", seeds=()):
    return KnowledgeFabric(str(root), seeds=[str(s) for s in seeds],
                           agent_id=agent, kin_key=kin)


def _put_atom(fabric, game, key, sigma=None, ttype=None, params=None):
    return fabric.append("collective", "atoms",
                         _rec(game, key, sigma, ttype, params))


def _put_verdict(fabric, game, key, level=1):
    return fabric.append("collective", "mint_verdicts",
                         {"verdict": "rederivation", "game": str(game),
                          "level": int(level), "key": str(key)})


def _enqueue(fabric, before, after, slot="WORKSPACE", residual=1.0):
    """Legacy-shape queue record (before/after, no persisted sigma): the
    old-books compat path rides through every test below."""
    return fabric.append("collective", "import_queue", {
        "slot": slot, "residual": float(residual),
        "before": [[int(v) for v in row] for row in np.asarray(before)],
        "after": [[int(v) for v in row] for row in np.asarray(after)],
    })


def _match_sigma():
    """The signature the enqueued residual will carry (1-cell 2->3 on 5x5)."""
    b, a = _recolour()
    return consumer.sigma_of(b, a)


def _readings(fabric):
    return fabric.query("collective", RHO_TOPIC)


def _books(tmp_path, old_shape=False, disjoint=False):
    """Two-fabric books wired for BOTH canonical cases at once:

    * THE PARTITION CASE (r1=0 but r2>0): home's h-match and gA's a-match carry
      the SAME sigma + ttype with DIFFERENT params -- rung 1 partitions them
      apart, rung 2 (params dropped) sees the correlation.
    * THE KEY-IDENTITY TRAFFIC CASE (the cn04/ka59 shape): home's verdict
      stream re-recognizes gA's atom key AND gA's verdict stream re-recognizes
      home's -- traffic must count both directions; plus a shared canonical
      key so rung 0 reads nonzero while rung 1 reads zero.
    """
    msig = _match_sigma()
    A = _fab(tmp_path / "A", agent="agentA", kin="kinA")
    _put_atom(A, "gA", "shared-k", _class_sig(5), ttype="ROTATE",
              params={"k": 1})                       # key identity, sigma differs
    _put_atom(A, "gA", "a-match", msig, ttype="TRANSLATE",
              params={"dx": 2})                      # the partition case, src half
    _put_verdict(A, "gA", "h-match")                 # gA re-recognized home's key
    if old_shape:
        A.append("collective", "atoms",              # sigma-less legacy atom
                 {"id": "a-old:0", "game": "gA",
                  "atom": {"kind": "EFFECT", "key": "a-old"}})
    seeds = [tmp_path / "A"]
    if disjoint:
        C = _fab(tmp_path / "C", agent="agentC", kin="kinC")
        _put_atom(C, "gC", "c0", _disjoint_sig())    # present, never matched
        seeds.append(tmp_path / "C")
    home = _fab(tmp_path / "home", agent="agentH", kin="kinH", seeds=seeds)
    _put_atom(home, "g_hist", "h-match", msig, ttype="TRANSLATE",
              params={"dx": 1})                      # the partition case, home half
    _put_atom(home, "g_hist", "shared-k", _class_sig(0))
    _put_verdict(home, "g_home", "a-match", level=2)  # home re-recognized gA's key
    b, a = _recolour()
    _enqueue(home, b, a)
    return home


# ── the persisted reading: correct at every rung ─────────────────────────────

class TestReadingPersisted:

    def test_pass_persists_a_seqd_multirung_record(self, tmp_path):
        home = _books(tmp_path)
        rep = consumer.consume(home, "g_home", 2, 8)
        assert rep["candidates"] == 1, "the fixture's queue item must match"
        rows = _readings(home)
        assert len(rows) == 1, (
            "one consume pass with matches must persist exactly ONE "
            "rho_readings record -- the measurement the system takes")
        rec = rows[0]
        assert int(rec["seq"]) >= 1, "additive record, seq'd"
        assert rec["game"] == "g_home" and int(rec["level"]) == 2, (
            "game + PLAYING level per A3-2")
        assert "gA" in (rec.get("readings") or {}), (
            "gA was matched against this pass -- it must be read")
        for stats in rec["readings"].values():
            assert {"r0", "r1", "r2", "traffic"} <= set(stats), (
                "every reading carries all four channels")

    def test_partition_case_r1_zero_but_r2_positive(self, tmp_path):
        """THE amendment's case, now IN THE BOOKS: same mechanism, different
        params -- rung 1 reads 0 (the old single-grain partition), rung 2
        reads the correlation. A record incapable of this split would be the
        artifact again."""
        home = _books(tmp_path)
        consumer.consume(home, "g_home", 2, 8)
        ga = _readings(home)[0]["readings"]["gA"]
        assert ga["r1"] == pytest.approx(0.0), "params split rung 1 classes"
        assert ga["r2"] > 0.0, "rung 2 drops params: correlation visible"
        assert ga["r2"] >= ga["r1"]

    def test_key_identity_reads_at_rung0_and_traffic_both_ways(self, tmp_path):
        """The cn04/ka59 shape: rung 1 blind, rung 0 + traffic must see it.
        Home re-recognized gA's key (1) and gA re-recognized home's (1)."""
        home = _books(tmp_path)
        consumer.consume(home, "g_home", 2, 8)
        ga = _readings(home)[0]["readings"]["gA"]
        assert ga["r0"] > 0.0, "the shared canonical key must read at rung 0"
        assert int(ga["traffic"]) == 2, (
            "cross-recognition counted in BOTH directions (1 + 1)")


# ── bounded per pass ─────────────────────────────────────────────────────────

class TestBounded:

    def test_only_matched_sources_are_read(self, tmp_path):
        """gC's atoms were PRESENT and evaluated but neither hit nor near-miss:
        the reading is bounded to sources the pass actually matched against."""
        home = _books(tmp_path, disjoint=True)
        consumer.consume(home, "g_home", 2, 8)
        rec = _readings(home)[0]
        assert "gC" not in rec["readings"], (
            "an unmatched source must NOT be read -- bounded per pass")
        assert "gA" in rec["readings"]

    def test_idle_pass_persists_nothing(self, tmp_path):
        """A drained queue (second pass) touches no sources: no record grows --
        the stream is bounded by matches, not by passes."""
        home = _books(tmp_path)
        consumer.consume(home, "g_home", 2, 8)
        consumer.consume(home, "g_home", 2, 8)
        assert len(_readings(home)) == 1

    def test_matchless_pass_persists_nothing(self, tmp_path):
        """A pass whose item finds NO atoms at all (the Chaitin empty search)
        writes a not_found, never a rho reading."""
        home = _fab(tmp_path / "home", agent="agentH", kin="kinH")
        b, a = _recolour()
        _enqueue(home, b, a)
        rep = consumer.consume(home, "g_home", 2, 8)
        assert rep["not_found"] == 1
        assert _readings(home) == []


# ── old books compat ─────────────────────────────────────────────────────────

class TestOldBooks:

    def test_sigma_less_atoms_degrade_never_raise(self, tmp_path):
        """gA carries a sigma-less legacy atom beside the live ones; the queue
        record is legacy-shaped (before/after, no persisted sigma). The pass
        must still read gA -- rung 0 keeps measuring over bare keys, rungs
        1/2 skip the unsigma'd atom, nothing raises."""
        home = _books(tmp_path, old_shape=True)
        rep = consumer.consume(home, "g_home", 2, 8)
        assert rep["candidates"] == 1
        ga = _readings(home)[0]["readings"]["gA"]
        # home keys {h-match, shared-k} vs gA keys {shared-k, a-match, a-old}
        assert ga["r0"] == pytest.approx(1.0 / 4.0), (
            "the bare-key atom still votes at rung 0")
        assert ga["r1"] == pytest.approx(0.0)


# ── the narration: [RHO] gains r0/r2/traffic ─────────────────────────────────

class TestNarration:

    def test_rho_line_carries_r0_r2_traffic(self, tmp_path, capsys):
        home = _books(tmp_path)
        consumer.consume(home, "g_home", 2, 8)
        lines = [ln for ln in capsys.readouterr().out.splitlines()
                 if ln.startswith("[RHO]")]
        assert len(lines) == 1, "still exactly one [RHO] line per pass"
        for field in ("r0=", "r2=", "traffic="):
            assert field in lines[0], (
                "[RHO] must narrate the ladder: %r missing from %r"
                % (field, lines[0]))

    def test_empty_pass_still_narrates_with_zeros(self, tmp_path, capsys):
        home = _fab(tmp_path / "home", agent="agentH", kin="kinH")
        consumer.consume(home, "g_home", 2, 8)
        lines = [ln for ln in capsys.readouterr().out.splitlines()
                 if ln.startswith("[RHO]")]
        assert len(lines) == 1 and "traffic=0" in lines[0]


# ── the registry: the row is flipped, with its receipt ───────────────────────

class TestRegistryFlipped:

    def _row(self):
        path = os.path.join(REPO, "record", "canon", "WIRING_REGISTRY.md")
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith("| rho-ladder |"):
                    return [c.strip() for c in line.strip().strip("|").split("|")]
        return None

    def test_rho_ladder_row_is_live_with_a_consumer_receipt(self):
        row = self._row()
        assert row is not None, "the rho-ladder row vanished from the registry"
        _name, symbol, site, status = row[0], row[1], row[2], row[3]
        assert status == "LIVE", (
            "the rho-ladder row must be flipped SEVERED->LIVE (got %r)" % status)
        assert "engines.egocentric.rho" in symbol
        assert "consumer.py" in site, (
            "the receipt must point at the live consumer call site, got %r" % site)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
