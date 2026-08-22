"""R1 GATE (PREREG_READOUTS.md): socket starvation codes — the agent reads its RESIDUAL.

THE LINE: the agent may read its own residual; it may never read its own grade. R1 is the
residual readout: a fixed ENUM of game-agnostic machinery codes; when a socket is exercised
persistently within an episode and NEVER passes, ONE record {socket, code, level,
budget_spent} appends to the PERSONAL fabric stream "starvation" plus a [STARVE] narration.

Write-contract (the affect law):
  * pure function of the episode counters handed in — no wall-clock, no RNG, replayable;
  * bounded — AT MOST one record per socket per episode;
  * enum-coded — codes come only from the fixed CODES tuple, no free-form strings;
  * narrated — no record without its [STARVE] line.

CONSUMER (one-currency law): AffectGains.starvation_steer(game) reads the personal
"starvation" stream and returns a bounded multiplicative exploration boost. It STEERS
effort only — gains() (seed_bias, mint_bar) must be untouched by starvation records:
no bar, no support, no pricing, no reputation.

Run pre-build: these failed (module absent), per the beat-49 rule.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


def _B():
    try:
        from engines.egocentric.starvation import (
            StarvationBook,  # noqa: F401 -- the import IS the availability probe
        )
    except Exception as e:
        pytest.fail("engines.egocentric.starvation missing (%s) -- R1 has not landed; "
                    "see PREREG_READOUTS.md" % e)
    from engines.egocentric.starvation import StarvationBook as B
    return B


def _codes():
    from engines.egocentric.starvation import CODES
    return CODES


def _healthy():
    """Every socket exercised AND passing: nothing starves."""
    return {"g1": 200, "g2": 200, "g3": 180, "g4": 150, "g5": 140, "g6": 100,
            "g7": 80, "shadow": 60, "drive": 20, "cycles": 250,
            "mint_tried": 20, "mint_passed": 3,
            "bank_tried": 40, "bank_passed": 12}


def _starved_reference():
    """The plan-reference socket exercised 200x with ZERO passes; everything
    downstream unexercised (a starved gate starves its dependents silently —
    only the FIRST collapsed socket is the machinery fact)."""
    return {"g1": 200, "g2": 0, "g3": 0, "g4": 0, "g5": 0, "g6": 0, "g7": 0,
            "shadow": 0, "drive": 0, "cycles": 250,
            "mint_tried": 0, "mint_passed": 0,
            "bank_tried": 0, "bank_passed": 0}


class TestTheEnum:

    def test_the_enum_is_fixed_and_game_agnostic(self):
        _B()
        codes = _codes()
        assert isinstance(codes, tuple), "CODES must be a fixed module-level tuple"
        assert set(codes) == {"NO_STABLE_REFERENCE", "NO_REFERENCE_BINDING",
                              "EMPTY_PLAN", "NO_NEGATIVE_INSTANCES",
                              "MINT_STARVED", "BANK_NO_FAMILY"}, (
            "the enum is preregistered — machinery facts only, no additions on the fly")
        for c in codes:
            assert c == c.upper() and " " not in c, (
                "codes are game-agnostic machinery identifiers, not prose")


class TestTheFalsifier:

    def test_a_starved_socket_emits_exactly_one_enum_record_and_narrates(
            self, tmp_path, capsys):
        """⭐ THE FALSIFIER (failing first): an episode engineered to starve one
        socket yields exactly ONE enum-coded record + a [STARVE] line."""
        b = _B()(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))
        recs = b.settle_episode(_starved_reference(), game="g1", level=1,
                                budget_spent=147)
        assert len(recs) == 1, "one starved socket -> exactly one record"
        rec = recs[0]
        assert rec["code"] == "NO_STABLE_REFERENCE"
        assert rec["level"] == 1 and rec["budget_spent"] == 147
        assert "socket" in rec
        stored = b.fabric.query("personal", "starvation")
        assert len(stored) == 1 and stored[0]["code"] == "NO_STABLE_REFERENCE", (
            "the record must land in the PERSONAL 'starvation' stream")
        outp = capsys.readouterr().out
        assert "[STARVE]" in outp and "NO_STABLE_REFERENCE" in outp, (
            "no record without its narration — the legibility law")

    def test_a_healthy_episode_emits_none(self, tmp_path, capsys):
        b = _B()(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))
        recs = b.settle_episode(_healthy(), game="g1", level=2, budget_spent=300)
        assert recs == []
        assert b.fabric.query("personal", "starvation") == []
        assert "[STARVE]" not in capsys.readouterr().out

    def test_the_record_is_a_pure_function_of_the_counters(self, tmp_path):
        """Same counters -> byte-identical records (two fresh books, two fresh
        fabrics; no wall-clock, no RNG, no hidden state)."""
        B = _B()
        c = _starved_reference()
        assert B.starved(c) == B.starved(dict(c)), "the decision must be pure"
        r1 = B(KnowledgeFabric(str(tmp_path / "x"), agent_id="a",
                               kin_key="v4")).settle_episode(c, game="g1",
                                                             level=1,
                                                             budget_spent=99)
        r2 = B(KnowledgeFabric(str(tmp_path / "y"), agent_id="a",
                               kin_key="v4")).settle_episode(dict(c), game="g1",
                                                             level=1,
                                                             budget_spent=99)
        assert r1 == r2, "replayability: identical counters -> identical records"

    def test_codes_only_from_the_enum_and_at_most_one_per_socket(self, tmp_path):
        """Engineer THREE starving sockets: three records, distinct sockets,
        every code from the enum."""
        c = _starved_reference()
        c["mint_tried"], c["mint_passed"] = 50, 0
        c["bank_tried"], c["bank_passed"] = 50, 0
        b = _B()(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"))
        recs = b.settle_episode(c, game="g1", level=0, budget_spent=10)
        codes = _codes()
        assert len(recs) == 3
        assert all(r["code"] in codes for r in recs), "no free-form strings"
        sockets = [r["socket"] for r in recs]
        assert len(sockets) == len(set(sockets)), "<= 1 record per socket per episode"
        assert {r["code"] for r in recs} == {"NO_STABLE_REFERENCE",
                                             "MINT_STARVED", "BANK_NO_FAMILY"}

    def test_the_threshold_is_exercised_not_merely_zero(self, tmp_path):
        """A socket below the exercise threshold never starves — silence about an
        unexercised socket is honest, not a code."""
        from engines.egocentric.starvation import PLAN_N
        B = _B()
        under = dict(_starved_reference())
        under["g1"] = PLAN_N - 1
        assert B.starved(under) == []
        at = dict(_starved_reference())
        at["g1"] = PLAN_N
        got = B.starved(at)
        assert len(got) == 1 and got[0]["code"] == "NO_STABLE_REFERENCE"


class TestTheConsumer:
    """One-currency law: starvation STEERS exploration effort; it never prices."""

    def _fab(self, tmp_path, name="f"):
        return KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4")

    def test_steer_is_neutral_on_an_empty_stream(self, tmp_path):
        from engines.egocentric.affect import AffectGains
        _B()
        s = AffectGains(self._fab(tmp_path)).starvation_steer("g1")
        assert s["explore_boost"] == 1.0 and s["codes"] == ()

    def test_steer_rises_bounded_with_starvation_and_is_game_scoped(self, tmp_path):
        from engines.egocentric.affect import AffectGains
        f = self._fab(tmp_path)
        _B()(f).settle_episode(_starved_reference(), game="g1", level=1,
                               budget_spent=100)
        a = AffectGains(f)
        s = a.starvation_steer("g1")
        assert 1.0 < s["explore_boost"] <= a.STARVE_CEIL, (
            "a starved socket nudges exploration — bounded, multiplicative")
        assert "NO_STABLE_REFERENCE" in s["codes"]
        other = a.starvation_steer("g2")
        assert other["explore_boost"] == 1.0, "another game's starvation is not mine"

    def test_steer_is_pure_over_the_stream(self, tmp_path):
        from engines.egocentric.affect import AffectGains
        f = self._fab(tmp_path)
        _B()(f).settle_episode(_starved_reference(), game="g1", level=1,
                               budget_spent=100)
        f2 = KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4")
        assert (AffectGains(f).starvation_steer("g1")
                == AffectGains(f2).starvation_steer("g1")), (
            "the steer must replay from the books alone")

    def test_starvation_never_touches_the_priced_channels(self, tmp_path):
        """gains() before and after starvation records must be IDENTICAL — the
        steer moves effort, never the mint bar and never a support/price."""
        from engines.egocentric.affect import AffectGains
        f = self._fab(tmp_path)
        a = AffectGains(f)
        before = a.gains()
        _B()(f).settle_episode(_starved_reference(), game="g1", level=1,
                               budget_spent=100)
        after = AffectGains(f).gains()
        assert before == after, "one-currency law: starvation steers, never prices"
        assert set(after.keys()) == {"seed_bias", "mint_bar", "persist"}, (
            "the third key is the persistence modulator (PREREG_PERSISTENCE_"
            "MONITOR.md), read from the narration fold -- not from this stream")


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_the_episode_boundary_settles_the_book(self):
        src = self._src()
        i = src.find("def end_game")
        assert i != -1
        body = src[i:i + 6000]
        assert "StarvationBook" in body or "starvation" in body, (
            "end_game never settles the starvation book — the residual readout "
            "is unwired (R1)")
        assert "_plan_gate" in body, "the plan-gate counters never reach the book"

    def test_the_loop_reads_the_steer(self):
        src = self._src()
        assert "starvation_steer" in src, (
            "the consumer is unwired — a produced stream with no reader is the "
            "R3 sin, in the very build that named it")
