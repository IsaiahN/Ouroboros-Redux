"""
The MECHANICAL auditor (newhorse.audit) -- the model-independent checker. These pin its detection logic on
synthetic inputs, and confirm it passes clean on the REAL repo. The auditor is the "checker that isn't me": a
human runs `PYTHONPATH=src python -m newhorse.audit` and gets a verdict no LLM can rationalise around.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse import audit


def test_keys_added_in_diff_ignores_comments_seeds_but_catches_keys():
    seed = "+# HUMAN-WRITTEN ONLY\n+\n+# key    note\n"          # header-only seed -> no keys
    assert audit._keys_added_in_diff(seed) == []
    real = "+abc123def456    # confirmed after review\n+++ b/docs/x\n"  # a key added
    assert audit._keys_added_in_diff(real) == ["abc123def456"]


def test_pending_claims_are_the_unconfirmed_ones():
    claims = [{"key": "k1", "name": "A"}, {"key": "k2", "name": "B"}]
    assert audit._pending_claims(claims, {"k1"}) == [{"key": "k2", "name": "B"}]
    assert audit._pending_claims(claims, {"k1", "k2"}) == []


def test_guards_present_flags_a_gutted_guard(tmp_path):
    (tmp_path / "answer_lint.py").write_text("def lint_agent_dir(): pass\ndef lint_source(): pass\n")
    (tmp_path / "novelty_ledger.py").write_text("def guarded_promote(): pass\n")   # missing 2 symbols
    r = audit.check_guards_present(redux=str(tmp_path))
    assert r["status"] == "FLAG" and any("record_novelty_claim" in d for d in r["detail"])


def test_tripwire_test_issues_detects_skip_and_missing(tmp_path):
    (tmp_path / "test_answer_lint.py").write_text("import pytest\n@pytest.mark.skip\ndef test_x():\n    lint_agent_dir()\n")
    # test_novelty_ledger.py absent
    issues = audit._tripwire_test_issues(str(tmp_path))
    assert any("SKIPPED" in i for i in issues) and any("MISSING" in i for i in issues)


def test_test_count_flags_a_drop(tmp_path):
    td = tmp_path / "tests"; td.mkdir(); dd = tmp_path / "docs"; dd.mkdir()
    (td / "test_a.py").write_text("def test_one():\n    pass\n")           # 1 test now
    (dd / "AUDIT_BASELINE.json").write_text(json.dumps({"max_tests": 5}))  # baseline was 5
    r = audit.check_test_count(tests=str(td), docs=str(dd))
    assert r["status"] == "FLAG" and "DROPPED" in r["detail"]


def test_unconfirmed_novelty_warns(tmp_path):
    dd = tmp_path / "docs"; dd.mkdir()
    (dd / "NOVELTY_CLAIMS.jsonl").write_text(json.dumps({"key": "kk", "name": "COUNT(k)"}) + "\n")
    r = audit.check_unconfirmed_novelty(docs=str(dd))
    assert r["status"] == "WARN" and "COUNT(k)" in str(r["detail"])
    (dd / "NOVELTY_CONFIRMED.txt").write_text("kk\n")
    assert audit.check_unconfirmed_novelty(docs=str(dd))["status"] == "PASS"


def test_real_repo_audit_has_no_flags():
    # the auditor itself, run on the live repo, must be clean of FLAGS (WARNs like 'unpushed' are allowed).
    checks = audit.run_audit()
    flags = [c for c in checks if c["status"] == "FLAG"]
    assert flags == [], "auditor flagged the repo:\n" + "\n".join("  %s: %s" % (c["name"], c["detail"]) for c in flags)
