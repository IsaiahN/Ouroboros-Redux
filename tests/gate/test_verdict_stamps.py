"""A3-4 GATE: mint verdicts carry WHEN (ep) and WHAT-IT-LOOKED-LIKE (sigma).

⭐ WHY (KNOBS AMENDMENT 3, A3-4): no shared episode key crosses the streams, and
rederivation/reject verdicts carry no sigma -- the bracket's loudly-reported MISSING.
Every mint verdict record gains:

  ep    : an episode ordinal -- a counter the MDLMint instance advances when its
          (game, level) context changes, or on an explicit bump_episode(); callers
          may also pass ep= to consider() directly. No cognitive_loop change needed.
  sigma : the EVENT's sigma (consumer.sigma_of vocabulary) -- already computed for
          atoms at mint time (B13), now stamped on rederivation/reject/quarantine
          verdicts too.

The record shape stays ADDITIVE: old sigma-less/ep-less verdicts on disk (every
Kaggle seed mount) must still read -- bracket_rt live mode reports them MISSING,
never crashes, and reads the new stamps when present.

Run pre-build: FAILED (verdict records carried no "ep"/"sigma"; MDLMint had no
bump_episode; bracket_rt live mode could not surface verdict sigma).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric import effects as E
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.mint import MDLMint


def _g(tmp_path, name="f"):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a", kin_key="v4"))


def _event(v_from=3, v_to=4, pos=(2, 2)):
    before = np.zeros((5, 5), dtype=int)
    before[pos] = v_from
    after = before.copy()
    after[pos] = v_to
    return before, after


def _verdicts(g):
    return g.fabric.query("collective", "mint_verdicts")


def _assert_stamped(rec):
    assert "ep" in rec, "verdict record must carry the episode ordinal 'ep'"
    assert isinstance(rec["ep"], int)
    assert "sigma" in rec, "verdict record must carry the event's sigma"
    assert isinstance(rec["sigma"], dict)
    assert rec["sigma"].get("arity") == 2, "sigma speaks the consumer vocabulary"


# ── every verdict kind is stamped ─────────────────────────────────────────────

class TestStampsOnEveryVerdictKind:

    def test_mint_verdict_carries_ep_and_sigma(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        b, a = _event()
        out = m.consider(b, 6, a, "g1", 1)
        assert out["verdict"] == "mint"
        rec = _verdicts(g)[-1]
        assert rec["verdict"] == "mint"
        _assert_stamped(rec)
        assert rec["sigma"] == consumer.sigma_of(b, a), (
            "the stamped sigma IS the event's sigma, same vocabulary as the atom's")

    def test_rederivation_verdict_carries_ep_and_sigma(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        b, a = _event()
        m.consider(b, 6, a, "g1", 1)
        out = m.consider(b, 6, a, "g1", 1)
        assert out["verdict"] == "rederivation"
        rec = _verdicts(g)[-1]
        assert rec["verdict"] == "rederivation"
        _assert_stamped(rec)
        assert rec["sigma"] == consumer.sigma_of(b, a), (
            "A3-4: the rederiving EVENT's own sigma -- the bracket's MISSING leg")

    def test_zero_change_reject_carries_ep_and_sigma(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        b, _ = _event()
        out = m.consider(b, 6, b.copy(), "g1", 1)
        assert out["verdict"] == "reject"
        rec = _verdicts(g)[-1]
        assert rec["verdict"] == "reject"
        _assert_stamped(rec)

    def test_mdl_reject_carries_ep_and_sigma(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        rng_free = np.arange(36, dtype=int).reshape(6, 6) % 7
        scramble = (rng_free + np.arange(36).reshape(6, 6) * 3) % 9
        out = m.consider(rng_free, 6, scramble, "g1", 1)
        assert out["verdict"] == "reject"
        rec = _verdicts(g)[-1]
        assert rec["verdict"] == "reject"
        _assert_stamped(rec)

    def test_quarantine_carries_ep_and_degraded_sigma(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        out = m.consider(np.zeros((3, 3), dtype=int), 6,
                         np.zeros((4, 4), dtype=int), "g1", 1)
        assert out["verdict"] == "quarantine"
        rec = _verdicts(g)[-1]
        assert rec["verdict"] == "quarantine"
        _assert_stamped(rec)   # sigma degrades (no bbox axes), never vanishes


# ── the episode ordinal: monotone, context-driven, override-able ──────────────

class TestEpisodeOrdinal:

    def test_ep_starts_at_zero(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        b, a = _event()
        m.consider(b, 6, a, "g1", 1)
        assert _verdicts(g)[-1]["ep"] == 0

    def test_ep_bumps_when_game_level_context_changes(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        b, a = _event()
        m.consider(b, 6, a, "g1", 1)                       # ep 0
        m.consider(b, 6, a, "g1", 1)                       # same context: still 0
        m.consider(b, 6, a, "g1", 2)                       # level changed: 1
        m.consider(b, 6, a, "g2", 2)                       # game changed: 2
        eps = [r["ep"] for r in _verdicts(g)]
        assert eps == [0, 0, 1, 2]

    def test_bump_episode_advances_without_context_change(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        b, a = _event()
        m.consider(b, 6, a, "g1", 1)
        before_bump = _verdicts(g)[-1]["ep"]
        m.bump_episode()
        m.consider(b, 6, a, "g1", 1)
        assert _verdicts(g)[-1]["ep"] == before_bump + 1

    def test_ep_is_monotonic_across_bumps_and_context_changes(self, tmp_path):
        g = _g(tmp_path)
        m = MDLMint(g)
        b, a = _event()
        m.consider(b, 6, a, "g1", 1)
        m.bump_episode()
        m.consider(b, 6, a, "g1", 1)
        m.consider(b, 6, a, "g1", 3)
        m.bump_episode()
        m.consider(b, 6, a, "g1", 3)
        eps = [r["ep"] for r in _verdicts(g)]
        assert eps == sorted(eps), "ep must never run backwards"
        assert eps[-1] > eps[0], "bumps and context changes must advance ep"

    def test_explicit_ep_kwarg_overrides_the_counter(self, tmp_path):
        """The documented no-loop-change hook: a caller that already owns an
        episode counter may pass it straight through."""
        g = _g(tmp_path)
        m = MDLMint(g)
        b, a = _event()
        m.consider(b, 6, a, "g1", 1, ep=41)
        assert _verdicts(g)[-1]["ep"] == 41
        m.consider(b, 6, a, "g1", 1)                       # default: internal counter
        assert _verdicts(g)[-1]["ep"] == 0, (
            "an explicit ep must not corrupt the internal ordinal")


# ── old books still read; new stamps are read when present ────────────────────

def _write_stream(fabric_root, scope, topic, records):
    d = os.path.join(str(fabric_root), scope)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, topic + ".jsonl"), "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


class TestOldBooksCompat:

    KEY = "eff-00aa11bb22cc33dd"

    def _swarm(self, tmp_path, stamped):
        """Box X mints KEY; box Y re-derives it -- old shape or ep+sigma-stamped."""
        sig = consumer.sigma_of(*_event())
        atom = {"kind": "EFFECT", "key": self.KEY, "changed": 1, "sigma": dict(sig)}
        _write_stream(tmp_path / "x1" / "ego_fabric", "collective", "atoms",
                      [{"id": self.KEY + ":0", "type": "structural", "game": "gx",
                        "level": 1, "atom": atom, "seq": 1}])
        mint_v = {"verdict": "mint", "game": "gx", "level": 1, "key": self.KEY, "seq": 1}
        reder_v = {"verdict": "rederivation", "game": "gy", "level": 1,
                   "key": self.KEY, "seq": 7}
        if stamped:
            mint_v.update(ep=0, sigma=dict(sig))
            reder_v.update(ep=3, sigma=dict(sig))
        _write_stream(tmp_path / "x1" / "ego_fabric", "collective",
                      "mint_verdicts", [mint_v])
        _write_stream(tmp_path / "y2" / "ego_fabric", "collective",
                      "mint_verdicts", [reder_v])

    def test_old_sigma_less_verdicts_still_read_and_report_missing(
            self, tmp_path, capsys):
        from tools import bracket_rt
        self._swarm(tmp_path, stamped=False)
        code = bracket_rt.live_report(str(tmp_path))
        out = capsys.readouterr().out
        assert code == 0
        assert self.KEY in out and "R_T=0.000" in out
        assert "MISSING" in out, "old books lack the stamps -- say so, loudly"

    def test_stamped_verdicts_are_read_when_present(self, tmp_path, capsys):
        from tools import bracket_rt
        self._swarm(tmp_path, stamped=True)
        code = bracket_rt.live_report(str(tmp_path))
        out = capsys.readouterr().out
        assert code == 0
        assert "verdict_sigma_dist=0.000" in out, (
            "a sigma-stamped rederivation verdict makes the sigma leg MEASURABLE")
        assert "ep=" in out
        assert "carry no episode/evidence" not in out, (
            "fully stamped books must not be reported as missing the stamps")

    def test_mixed_books_still_flag_the_unstamped_remainder(self, tmp_path, capsys):
        from tools import bracket_rt
        self._swarm(tmp_path, stamped=True)
        # a third, old-era box: rederivation verdict without stamps
        _write_stream(tmp_path / "z3" / "ego_fabric", "collective", "mint_verdicts",
                      [{"verdict": "rederivation", "game": "gz", "level": 1,
                        "key": self.KEY, "seq": 2}])
        code = bracket_rt.live_report(str(tmp_path))
        out = capsys.readouterr().out
        assert code == 0
        assert "MISSING" in out, "any unstamped verdicts remain a loud MISSING"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
