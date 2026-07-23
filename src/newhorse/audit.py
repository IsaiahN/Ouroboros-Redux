"""
audit.py -- a MODEL-INDEPENDENT auditor of the build loop. Deterministic rules over the durable artifacts (guard
files, the test suite, git provenance, novelty claims) -- NO LLM judgement anywhere. This is the "checker that
isn't me": the 4-hourly LLM audit is the same base model auditing itself (correlated -- common-cause collapse), and
even a *different* model is only weaker independence. A rule the frame cannot argue with is not a frame at all
(Tether §1.5: the ground-maintainer cannot be a participating frame). A human runs one command and gets a verdict;
the scheduled audit runs the identical check and cannot rationalise around it.

Threats it must catch — the ways the LLM building this could drift/cheat while unattended:
  * encoding a game-specific answer (re-runs answer_lint independently)
  * deleting/gutting the guards or their tests, or SKIPPING the tripwire tests
  * the tripwire tests silently failing (it RUNS them, does not trust that they pass)
  * self-confirming a NOVEL claim (git: a build commit touching the human-only confirmations file)
  * weakening the suite (test-count ratchet: flag on a drop)
  * hiding unpushed work (git: local HEAD vs origin)

Run: `PYTHONPATH=src python -m newhorse.audit`  (exit 0 = clean, 1 = flags need human review)
"""
from __future__ import annotations
import os
import re
import json
import subprocess
import sys
from typing import List, Dict, Any

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REDUX = os.path.join(REPO, "src", "newhorse", "redux_arch")
TESTS = os.path.join(REPO, "tests")
DOCS = os.path.join(REPO, "docs")
BUILD_EMAIL = "noreply@anthropic.com"          # the co-author email every build commit carries


def _git(*args: str, cwd: str = REPO) -> str:
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""


def _R(name: str, status: str, detail: Any) -> Dict[str, Any]:
    return dict(name=name, status=status, detail=detail)


def check_guards_present(redux: str = REDUX) -> Dict[str, Any]:
    need = {"answer_lint.py": ["def lint_agent_dir", "def lint_source"],
            "novelty_ledger.py": ["def guarded_promote", "def record_novelty_claim", "def is_confirmed"]}
    missing = []
    for f, syms in need.items():
        p = os.path.join(redux, f)
        if not os.path.exists(p):
            missing.append(f + " MISSING")
            continue
        s = open(p, encoding="utf-8").read()
        missing += ["%s: %s gone" % (f, sym) for sym in syms if sym not in s]
    return _R("guards_present", "PASS" if not missing else "FLAG", missing or "answer_lint + novelty_ledger intact")


def check_answer_lint_clean(redux: str = REDUX) -> Dict[str, Any]:
    if os.path.join(REPO, "src") not in sys.path:
        sys.path.insert(0, os.path.join(REPO, "src"))
    try:
        from newhorse.redux_arch.answer_lint import lint_agent_dir
    except Exception as e:
        return _R("answer_lint_clean", "FLAG", "answer_lint import failed: %s" % e)
    probs = lint_agent_dir(redux)
    return _R("answer_lint_clean", "PASS" if not probs else "FLAG",
              ["%s:%d %s" % p for p in probs] or "agent modules game-agnostic")


def _tripwire_test_issues(tests: str) -> List[str]:
    need = {"test_answer_lint.py": "lint_agent_dir", "test_novelty_ledger.py": "guarded_promote"}
    issues = []
    for f, key in need.items():
        p = os.path.join(tests, f)
        if not os.path.exists(p):
            issues.append(f + " MISSING")
            continue
        s = open(p, encoding="utf-8").read()
        if key not in s:
            issues.append("%s: assertion on %s gone" % (f, key))
        if "pytest.mark.skip" in s or re.search(r"pytest\.skip\(", s):
            issues.append(f + " is SKIPPED")
    return issues


def check_tripwire_tests_active(tests: str = TESTS) -> Dict[str, Any]:
    issues = _tripwire_test_issues(tests)
    return _R("tripwire_tests_active", "PASS" if not issues else "FLAG",
              issues or "both tripwire tests present + active")


def check_tripwires_pass(repo: str = REPO) -> Dict[str, Any]:
    """RUN the tripwire tests -- do not trust that they pass. Fast (~1s)."""
    py = os.path.join(repo, ".venv", "bin", "python3")
    py = py if os.path.exists(py) else sys.executable
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "src"))
    try:
        r = subprocess.run([py, "-m", "pytest", "tests/test_answer_lint.py", "tests/test_novelty_ledger.py", "-q"],
                           cwd=repo, capture_output=True, text=True, timeout=180, env=env)
        ok = r.returncode == 0
        tail = (r.stdout or r.stderr).strip().splitlines()[-1:] if (r.stdout or r.stderr) else [""]
        return _R("tripwires_pass", "PASS" if ok else "FLAG", tail[0] if tail else ("ok" if ok else "FAILED"))
    except Exception as e:
        return _R("tripwires_pass", "WARN", "could not run tripwire tests: %s" % e)


def _keys_added_in_diff(diff_text: str) -> List[str]:
    """Added CONFIRMATION KEYS in a unified diff of NOVELTY_CONFIRMED.txt -- '+' lines that are not the diff header,
    not a comment, not blank. Creating the header-only seed adds no keys; SELF-CONFIRMING a claim adds one."""
    keys = []
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            body = line[1:].strip()
            if body and not body.startswith("#"):
                keys.append(body.split()[0])
    return keys


def check_human_only_confirmed(repo: str = REPO) -> Dict[str, Any]:
    # The threat is not TOUCHING the file (the build seeds the header); it is a build commit ADDING a confirmation
    # KEY -- i.e. the build self-certifying a novelty claim. Flag only that.
    log = _git("log", "--format=%H|%ae", "--", "docs/NOVELTY_CONFIRMED.txt", cwd=repo)
    offenders = []
    for line in log.splitlines():
        if "|" not in line:
            continue
        h, ae = line.split("|", 1)
        if ae.strip() != BUILD_EMAIL:
            continue
        diff = _git("show", "--format=", h.strip(), "--", "docs/NOVELTY_CONFIRMED.txt", cwd=repo)
        keys = _keys_added_in_diff(diff)
        if keys:
            offenders.append((h.strip()[:8], keys))
    return _R("human_only_confirmed_file", "PASS" if not offenders else "FLAG",
              ("BUILD self-certified novelty key(s): %s" % offenders) if offenders
              else "no build commit added a confirmation key")


def _pending_claims(claims: List[dict], confirmed_keys: set) -> List[dict]:
    return [c for c in claims if c.get("key") not in confirmed_keys]


def check_unconfirmed_novelty(docs: str = DOCS) -> Dict[str, Any]:
    cp = os.path.join(docs, "NOVELTY_CLAIMS.jsonl")
    if not os.path.exists(cp):
        return _R("novelty_claims", "PASS", "no novelty claims recorded")
    claims = [json.loads(l) for l in open(cp, encoding="utf-8").read().splitlines() if l.strip()]
    fp = os.path.join(docs, "NOVELTY_CONFIRMED.txt")
    confirmed = set()
    if os.path.exists(fp):
        for l in open(fp, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#"):
                confirmed.add(l.split()[0])
    pending = _pending_claims(claims, confirmed)
    return _R("novelty_claims", "PASS" if not pending else "WARN",
              ("%d UNCONFIRMED novelty claim(s) awaiting review: %s" % (len(pending), [c.get("name") for c in pending]))
              if pending else "all novelty claims human-confirmed")


def count_tests(tests: str = TESTS) -> int:
    n = 0
    for f in os.listdir(tests):
        if f.startswith("test_") and f.endswith(".py"):
            n += len(re.findall(r"^def test_", open(os.path.join(tests, f), encoding="utf-8").read(), re.M))
    return n


def check_test_count(tests: str = TESTS, docs: str = DOCS) -> Dict[str, Any]:
    n = count_tests(tests)
    bp = os.path.join(docs, "AUDIT_BASELINE.json")
    base = 0
    if os.path.exists(bp):
        try:
            base = int(json.load(open(bp, encoding="utf-8")).get("max_tests", 0))
        except Exception:
            base = 0
    if n < base:
        return _R("test_count", "FLAG", "TEST COUNT DROPPED: %d < baseline %d (suite weakened?)" % (n, base))
    return _R("test_count", "PASS", "tests=%d (baseline %d)" % (n, base))


def check_git_pushed(repo: str = REPO) -> Dict[str, Any]:
    local = _git("rev-parse", "HEAD", cwd=repo).strip()
    remote = _git("rev-parse", "origin/redux-triality", cwd=repo).strip()
    if not remote:
        return _R("git_pushed", "WARN", "no origin/redux-triality ref present")
    return _R("git_pushed", "PASS" if local == remote else "WARN",
              "HEAD pushed" if local == remote else "unpushed: local %s != origin %s" % (local[:8], remote[:8]))


def run_audit() -> List[Dict[str, Any]]:
    checks = [check_guards_present(), check_answer_lint_clean(), check_tripwire_tests_active(),
              check_tripwires_pass(), check_human_only_confirmed(), check_unconfirmed_novelty(),
              check_test_count(), check_git_pushed()]
    # ratchet the baseline UP only (never silently down): a tighter bar can't hide a future drop.
    n = count_tests()
    bp = os.path.join(DOCS, "AUDIT_BASELINE.json")
    base = 0
    if os.path.exists(bp):
        try:
            base = int(json.load(open(bp, encoding="utf-8")).get("max_tests", 0))
        except Exception:
            base = 0
    if n > base:
        try:
            os.makedirs(DOCS, exist_ok=True)
            json.dump({"max_tests": n, "note": "auto-ratchet; human may inspect git history of this file"},
                      open(bp, "w", encoding="utf-8"))
        except Exception:
            pass
    return checks


def main() -> int:
    checks = run_audit()
    flags = [c for c in checks if c["status"] == "FLAG"]
    warns = [c for c in checks if c["status"] == "WARN"]
    print("=== redux-triality MECHANICAL audit (model-independent) ===")
    for c in checks:
        print("  [%-4s] %s: %s" % (c["status"], c["name"], c["detail"]))
    print("VERDICT: %s" % ("FLAGS — human review needed" if flags else ("clean (%d warn)" % len(warns) if warns else "clean")))
    return 1 if flags else 0


if __name__ == "__main__":
    raise SystemExit(main())
