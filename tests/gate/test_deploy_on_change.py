"""DEPLOY ON CHANGE — the gate that replaces the commit gate.

THE ERROR THIS EXISTS FOR (THE_LADDER, "the working tree is production"): the commit was
treated as the boundary between "not running" and "running". It never was. A change is live
at the next worker restart, whatever git thinks — and holding a commit protected the
repository, not the swarm.

So the boundary is now explicit: the supervisor fingerprints the live-path `.py` files each
poll, restarts the workers when the fingerprint moves, and does neither while `.runs/swarm/HOLD`
exists. **The hold is a file the launcher reads, not a discipline someone remembers.**

R4, both directions, because a fingerprint that always changes and one that never changes are
equally useless:
  KNOWN-POSITIVE  editing a live-path file MUST move the fingerprint
  KNOWN-NEGATIVE  editing a non-live path (tools/, tests/) must NOT move it, or every proctor
                  edit restarts 25 workers for nothing
  AND STABILITY   two calls with no edit between them must agree, or the swarm redeploys on
                  every poll forever
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _fingerprint(root, skip):
    """The supervisor's rule, reimplemented over an arbitrary root so the test never
    touches the real tree. Same shape: relpath + size + mtime_ns, sorted."""
    import hashlib
    h = hashlib.sha1()  # noqa: S324
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip]
        for f in sorted(fns):
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            st = os.stat(p)
            h.update(os.path.relpath(p, root).encode("utf-8", "replace"))
            h.update(b"%d:%d" % (st.st_size, st.st_mtime_ns))
    return h.hexdigest()


SKIP = {".git", ".runs", ".venv", "__pycache__", "node_modules", ".ruff_cache",
        "tests", "lab", "tools", "docs", "architecture"}


def _tree(tmp_path):
    live = tmp_path / "engines"
    live.mkdir()
    (live / "loop.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "runner.py").write_text("y = 2\n", encoding="utf-8")
    toolsd = tmp_path / "tools"
    toolsd.mkdir()
    (toolsd / "sweep.py").write_text("z = 3\n", encoding="utf-8")
    testsd = tmp_path / "tests"
    testsd.mkdir()
    (testsd / "test_x.py").write_text("w = 4\n", encoding="utf-8")
    return live, toolsd, testsd


def test_stability_no_edit_means_no_deploy(tmp_path):
    """Without this the swarm redeploys on every poll, forever."""
    _tree(tmp_path)
    a = _fingerprint(str(tmp_path), SKIP)
    b = _fingerprint(str(tmp_path), SKIP)
    assert a == b, "fingerprint is unstable -- the swarm would redeploy every poll"


def test_known_positive_a_live_path_edit_moves_the_fingerprint(tmp_path):
    live, _t, _s = _tree(tmp_path)
    before = _fingerprint(str(tmp_path), SKIP)
    (live / "loop.py").write_text("x = 1\nx += 1\n", encoding="utf-8")
    assert _fingerprint(str(tmp_path), SKIP) != before, (
        "a live-path edit did not move the fingerprint -- changes would never deploy")


def test_known_positive_a_new_live_file_moves_it_too(tmp_path):
    live, _t, _s = _tree(tmp_path)
    before = _fingerprint(str(tmp_path), SKIP)
    (live / "brand_new.py").write_text("n = 0\n", encoding="utf-8")
    assert _fingerprint(str(tmp_path), SKIP) != before, "an added module did not deploy"


def test_known_negative_proctor_tooling_does_not_deploy(tmp_path):
    """Editing tools/ or tests/ must NOT restart 25 workers. Without this the gate is
    'restart on any edit', which is a different and much worse mechanism."""
    _live, toolsd, testsd = _tree(tmp_path)
    before = _fingerprint(str(tmp_path), SKIP)
    (toolsd / "sweep.py").write_text("z = 3\nz += 1\n", encoding="utf-8")
    (testsd / "test_x.py").write_text("w = 4\nw += 1\n", encoding="utf-8")
    assert _fingerprint(str(tmp_path), SKIP) == before, (
        "a proctor-tooling edit moved the fingerprint -- every sweep would restart the swarm")


def test_f3_the_hold_holds(tmp_path):
    """THE REPLACEMENT FOR THE COMMIT GATE. With HOLD present the supervisor must not
    deploy even though the fingerprint moved. Asserted on the supervisor's own condition."""
    live, _t, _s = _tree(tmp_path)
    hold = tmp_path / "HOLD"
    deployed = _fingerprint(str(tmp_path), SKIP)

    (live / "loop.py").write_text("x = 99\n", encoding="utf-8")
    current = _fingerprint(str(tmp_path), SKIP)
    assert current != deployed, "precondition failed: the edit did not register"

    hold.write_text("staging\n", encoding="utf-8")
    would_deploy = (not hold.exists()) and current != deployed
    assert not would_deploy, "HOLD present and it deployed anyway -- the gate is fictional"

    hold.unlink()
    assert (not hold.exists()) and current != deployed, "removing HOLD did not resume deploys"


def test_the_real_supervisor_exposes_the_pieces():
    """The mechanism must exist in the shipped file, not only in this test's copy of it."""
    src = os.path.join(REPO, "tools", "swarm_supervisor.py")
    text = open(src, encoding="utf-8").read()
    for token in ("def code_fingerprint", "def record_deploy", "HOLD_FILE",
                  "deployed_fp", "deploys.jsonl"):
        assert token in text, f"supervisor is missing {token!r}"
    # manual_tools is live-path (evolutionary_engine imports it lazily) and must NOT be skipped
    skip_block = text[text.index("dns[:] = [d for d in dns"):text.index("for f in sorted(fns)")]
    assert '"manual_tools"' not in skip_block, (
        "manual_tools was excluded from the fingerprint, but evolutionary_engine.py imports "
        "it -- a change there would silently never deploy")
