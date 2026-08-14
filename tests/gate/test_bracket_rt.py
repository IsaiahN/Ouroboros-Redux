"""G-B GATE: tools/bracket_rt.py — the R_T bracket residual (PREREG_FINAL_GAPS §G-B).

⭐ WHY. Fig D's caption claims the promote->seed->re-derive round trip closes:
R_T = |T_A . T_E(x) - x|. A promoted generator (a collective atom with provenance)
is projected through the membrane as a PRIOR (its sigma — the consumer's shared
vocabulary — never the atom's transform/context content), a FRESH box re-derives a
sigma-equivalent atom from its own evidence, and the divergence (sigma distance +
cost delta) is the bracket residual. The tool must show, synthetically:

  * FALSIFIER 1 (the prior lowered the kernel): a seeded box re-derives the
    generator with LESS evidence than a cold control box (no seed);
  * FALSIFIER 2 (the membrane holds): the seed carries priors ONLY — never the
    atom itself (no atoms stream, no transform/context content) and never
    playback/winning-sequence material; a playback record anywhere is a LOUD
    MembraneViolation, and a full measurement leaves every fabric root clean;
  * FALSIFIER 3 (R_T decreases as priors sharpen): full-sigma prior < degraded
    prior < cold on the first-mint R_T.

Live mode is read-only over swarm boxes and reports what the books actually
carry — cross-box rederivations by canonical key — with honest MISSING lines
where linkage is absent, never a fabricated join.

Run pre-build: failed (tools.bracket_rt absent).
"""
from __future__ import annotations

import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools import bracket_rt


def _write_stream(root, scope, topic, records):
    d = os.path.join(root, scope)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, topic + ".jsonl"), "a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


# ── FALSIFIER 1 + 3: the round trip, seeded vs cold ──────────────────────────

class TestTheRoundTrip:

    def test_a_seeded_rederivation_is_cheaper_than_cold(self, tmp_path):
        sharp = bracket_rt.run_bracket(str(tmp_path), "sharp")
        cold = bracket_rt.run_bracket(str(tmp_path), "cold")
        assert sharp["seeded"] is True and cold["seeded"] is False
        assert sharp["evidence_to_rederivation"] is not None, (
            "the seeded box never re-derived a sigma-equivalent atom")
        assert cold["evidence_to_rederivation"] is not None, (
            "the cold box must ALSO get there eventually — same evidence")
        assert (sharp["evidence_to_rederivation"]
                < cold["evidence_to_rederivation"]), (
            "the prior did not lower the kernel: seeded %s vs cold %s"
            % (sharp["evidence_to_rederivation"], cold["evidence_to_rederivation"]))
        assert sharp["key_match"] is True, (
            "the re-derived atom is not the SAME canonical generator")

    def test_r_t_decreases_as_priors_sharpen(self, tmp_path):
        runs = {arm: bracket_rt.run_bracket(str(tmp_path), arm)
                for arm in ("sharp", "blunt", "cold")}
        rt = {arm: r["first_mint"]["r_t"] for arm, r in runs.items()}
        assert rt["sharp"] == 0.0, (
            "a full-sigma prior must guide straight to the generator: R_T %r"
            % rt["sharp"])
        assert rt["sharp"] < rt["blunt"] < rt["cold"], (
            "R_T must fall as the prior sharpens: %r" % rt)

    def test_the_promoted_generator_carries_provenance(self, tmp_path):
        r = bracket_rt.run_bracket(str(tmp_path), "sharp")
        assert r["target_key"], "no promoted generator was minted in A"
        verdicts = os.path.join(r["a_root"], "collective", "mint_verdicts.jsonl")
        assert os.path.isfile(verdicts), "A's mint left no verdict ledger"
        keys = [json.loads(ln).get("key")
                for ln in open(verdicts, encoding="utf-8") if ln.strip()]
        assert r["target_key"] in keys, "the atom's provenance is not on A's books"


# ── FALSIFIER 2: the membrane ────────────────────────────────────────────────

class TestTheMembrane:

    def test_the_seed_never_carries_the_atom_or_playback(self, tmp_path):
        r = bracket_rt.run_bracket(str(tmp_path), "sharp")
        seed = r["seed_root"]
        assert seed and os.path.isdir(seed)
        for dirpath, _dirs, files in os.walk(seed):
            assert "atoms.jsonl" not in files, (
                "the atom stream crossed the membrane: %s" % dirpath)
        assert bracket_rt.seed_violations(seed) == []

    def test_playback_topic_in_a_seed_is_a_loud_violation(self, tmp_path):
        seed = str(tmp_path / "seed")
        _write_stream(seed, "collective", "winning_sequences",
                      [{"game": "g", "actions": [1, 2, 3], "seq": 1}])
        assert bracket_rt.seed_violations(seed), (
            "a winning-sequence stream in the seed went unnoticed")
        with pytest.raises(bracket_rt.MembraneViolation):
            bracket_rt.assert_membrane([], seed_roots=[seed])

    def test_playback_field_in_any_fabric_root_is_a_violation(self, tmp_path):
        root = str(tmp_path / "box")
        _write_stream(root, "collective", "ideas",
                      [{"idea": {"prefix_json": "[6,6,6]"}, "game": "g", "seq": 1}])
        v = bracket_rt.membrane_violations([root])
        assert v, "playback-shaped content inside a fabric stream went unnoticed"
        with pytest.raises(bracket_rt.MembraneViolation):
            bracket_rt.assert_membrane([root])

    def test_atom_content_in_a_seed_is_a_violation(self, tmp_path):
        seed = str(tmp_path / "seed")
        _write_stream(seed, "collective", "ideas",
                      [{"idea": {"kind": "GENERATOR_PRIOR",
                                 "transform": {"before": [[1]], "after": [[2]]}},
                        "game": "g", "seq": 1}])
        assert bracket_rt.seed_violations(seed), (
            "atom content (transform) crossed into a seed unnoticed")

    def test_a_full_synthetic_run_leaves_every_root_clean(self, tmp_path):
        code, report = bracket_rt.synthetic_report(str(tmp_path))
        assert code == 0
        roots = [r for arm in report["arms"].values()
                 for r in (arm["a_root"], arm["b_root"], arm["seed_root"]) if r]
        assert roots and bracket_rt.membrane_violations(roots) == []


# ── the report: [BRACKET] lines, and an honest live mode ─────────────────────

class TestTheReport:

    def test_synthetic_report_speaks_bracket_lines(self, tmp_path, capsys):
        code, _report = bracket_rt.synthetic_report(str(tmp_path))
        out = capsys.readouterr().out
        assert code == 0
        assert "[BRACKET]" in out
        assert "arm=sharp" in out and "arm=cold" in out
        assert "R_T" in out and "membrane=HELD" in out

    def _fake_swarm(self, tmp_path):
        """Box X promotes key K (atom + mint verdict); box Y re-derives it."""
        key = "eff-00aa11bb22cc33dd"
        xf = str(tmp_path / "x1" / "ego_fabric")
        _write_stream(xf, "collective", "atoms",
                      [{"id": key + ":0", "type": "structural", "game": "gx",
                        "level": 1, "atom": {"kind": "EFFECT", "key": key,
                                             "changed": 1}, "seq": 1}])
        _write_stream(xf, "collective", "mint_verdicts",
                      [{"verdict": "mint", "game": "gx", "level": 1,
                        "key": key, "seq": 1}])
        yf = str(tmp_path / "y2" / "ego_fabric")
        _write_stream(yf, "collective", "mint_verdicts",
                      [{"verdict": "rederivation", "game": "gy", "level": 1,
                        "key": key, "seq": 7}])
        return key

    def test_live_mode_reports_cross_box_rederivation(self, tmp_path, capsys):
        key = self._fake_swarm(tmp_path)
        code = bracket_rt.live_report(str(tmp_path))
        out = capsys.readouterr().out
        assert code == 0
        assert "[BRACKET]" in out and key in out
        assert "R_T=0.000" in out, "key-identical rederivation is R_T zero"
        assert "MISSING" in out, (
            "the books carry no episode linkage — the report must say so")

    def test_live_mode_with_nothing_measurable_is_honest(self, tmp_path, capsys):
        os.makedirs(tmp_path / "z9" / "ego_fabric" / "collective")
        code = bracket_rt.live_report(str(tmp_path))
        out = capsys.readouterr().out
        assert code == 1
        assert "MISSING" in out
