"""D-13: HOLD IS NOT A STOP -- the gate that makes it one, or makes the breach loud.

THE ERROR THIS EXISTS FOR (2026-08-21, record/log/PORT_LOG.md D-13): the working tree is
production -- spawn() imports it. `.runs/swarm/HOLD` suspended DEPLOYS (the fingerprint
path) and nothing else: the bounded-lifetime recycle (RECYCLE_MIN) fired regardless, and at
~18:03 all 25 workers recycled onto a dirty tree under HOLD and ran uncommitted code for
~40 min while deploys.jsonl showed a clean history over that dirty fleet. Crash restarts
and mem-kills respawn from the tree too.

THE TWO HALVES:
  DEFER    under HOLD a worker past RECYCLE_MIN is LEFT RUNNING, status.txt says so per
           worker ("RECYCLE DEFERRED (HOLD) up=Nm"), and the next poll after HOLD lifts
           recycles it through the EXISTING path, once. No new knob.
  LOUD     a forced respawn under HOLD (crash restart, mem-kill) cannot be avoided -- the
           tree is what exists -- so it is LEDGERED: one deploys.jsonl record with
           reason="respawn-under-hold", the game, the trigger, and head/dirty/fingerprint
           from THE SAME ASSEMBLY the deploy records use (deploy_record), plus a
           "!! RESPAWN UNDER HOLD" line in status.txt. The ledger can no longer show clean
           over dirty.

F4 IS THE ORACLE FOR EVERYTHING ELSE: without HOLD, recycle / restart / mem-kill behaviour
is byte-identical to the pre-D-13 supervisor. The expected status lines and ledger bytes
below were CAPTURED FROM THE PRE-EDIT CODE (HEAD 41886d6) by this same harness and frozen
here; they are not derived from the new code.

No .runs, no real processes, no real git: the supervisor's REAL main() runs against a
scripted fleet -- spawn faked (a fake Popen handle + an in-memory log), the clock faked
(sleep advances it), git faked (fixed head + dirty listing), taskkill faked, the memory
query fed from a dict. Every poll boundary runs the next scripted step.
"""
from __future__ import annotations

import builtins
import importlib
import io
import json
import os
import subprocess
import sys
import time as _real_time
from types import SimpleNamespace
from unittest import mock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

SUPERVISOR_SRC = os.path.join(REPO, "tools", "swarm_supervisor.py")

FLEET = ["ar25", "bp35", "cd82"]          # three roster games: the scripted fleet
GIT_HEAD = "0123456789abcdef0123456789abcdef01234567"
GIT_DIRTY = " M engines/egocentric/gate.py\n?? record/findings/NEW.md\n"
FP = "f" * 40
CLOCK0 = 1_700_000_000.0                  # the fake epoch; gmtime of it is TZ-independent


class _Stop(Exception):
    """Raised at the poll boundary after the last scripted step: main() never returns."""


class _Proc:
    def __init__(self, pid):
        self.pid = pid
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode


class Harness:
    """Drives the supervisor's REAL main() over a scripted fleet. Each scripted step runs
    at a poll boundary (the sleep(POLL_SEC) call) BEFORE that poll; the status.txt each
    poll wrote is captured at the next boundary; after the last step the loop is stopped."""

    def __init__(self, sup, root, hold, steps):
        self.sup, self.root, self.hold, self.steps = sup, root, hold, steps
        self.clock = CLOCK0
        self.rss = {}
        self.spawns = []
        self.polls = 0
        self.statuses = []
        self.next_pid = 100

    # -- the fakes the supervisor is handed -------------------------------------------
    def spawn(self, g):
        self.next_pid += 1
        self.spawns.append(g)
        self.rss[g] = 300.0                   # a fresh worker starts small
        self.sup.procs[g] = (_Proc(self.next_pid), io.StringIO(), self.clock)

    def sleep(self, secs):
        if secs == self.sup.POLL_SEC:
            if self.polls:
                self.statuses.append(self.status())
            if self.polls >= len(self.steps):
                raise _Stop()
            self.steps[self.polls](self)
            self.polls += 1
        self.clock += secs

    def working_sets(self):
        return {p.pid: (0, self.rss[g]) for g, (p, _l, _t) in self.sup.procs.items()}

    def git(self, args, **_kw):
        out = GIT_HEAD if "rev-parse" in args else GIT_DIRTY
        return SimpleNamespace(stdout=out, returncode=0)

    def strftime(self, fmt, t=None):
        return _real_time.strftime(fmt, _real_time.gmtime(self.clock))

    # -- the script's verbs -----------------------------------------------------------
    def age(self, g, minutes):
        p, logf, t0 = self.sup.procs[g]
        self.sup.procs[g] = (p, logf, t0 - minutes * 60.0)

    def crash(self, g, rc=1):
        self.sup.procs[g][0].returncode = rc

    def hold_on(self):
        open(self.hold, "w", encoding="utf-8").write("staging\n")

    def hold_off(self):
        os.remove(self.hold)

    # -- the evidence -----------------------------------------------------------------
    def status(self):
        return open(os.path.join(self.root, "status.txt"), encoding="utf-8").read()

    def ledger_lines(self):
        return open(os.path.join(self.root, "deploys.jsonl"), encoding="utf-8").read().splitlines()

    def ledger(self):
        return [json.loads(ln) for ln in self.ledger_lines()]

    def run(self):
        """One status per poll: the boundary after the last poll captures it, then stops."""
        with pytest.raises(_Stop):
            self.sup.main()
        assert len(self.statuses) == len(self.steps)
        return self


def _harness(monkeypatch, tmp_path, steps):
    sup = importlib.import_module("tools.swarm_supervisor")
    root = str(tmp_path / "swarm")
    hold = os.path.join(root, "HOLD")
    h = Harness(sup, root, hold, steps)
    monkeypatch.setattr(sup, "ROOT", root)
    monkeypatch.setattr(sup, "HOLD_FILE", hold)
    monkeypatch.setattr(sup, "GAMES", list(FLEET))
    monkeypatch.setattr(sup, "stats", {g: {"restarts": 0, "mem_kills": 0, "recycles": 0}
                                       for g in FLEET})
    monkeypatch.setattr(sup, "procs", {})
    monkeypatch.setattr(sup, "KEY", None)
    monkeypatch.setattr(sup, "read_arc_key", lambda *a, **k: "test-key-not-the-real-one")
    monkeypatch.setattr(sup, "spawn", h.spawn)
    monkeypatch.setattr(sup, "code_fingerprint", lambda: FP)
    monkeypatch.setattr(sup, "working_sets", h.working_sets)
    monkeypatch.setattr(sup, "kill_tree", lambda pid: None)
    monkeypatch.setattr(sup, "time", SimpleNamespace(
        time=lambda: h.clock, sleep=h.sleep, strftime=h.strftime,
        gmtime=lambda: _real_time.gmtime(h.clock)))
    monkeypatch.setattr(sup, "subprocess", SimpleNamespace(run=h.git, STDOUT=object()))
    return sup, h


def _nothing(_h):
    pass


# ── F4: THE ORACLE -- without HOLD, byte-identical to the pre-D-13 supervisor ───────────
# Captured from the PRE-EDIT code (HEAD 41886d6) by this harness on the script below:
#   poll 1  nothing
#   poll 2  ar25 aged past RECYCLE_MIN; bp35 crashed (rc=1); cd82 at 1500 MB (> MEM_CAP)
#   poll 3  nothing
# Frozen here as the oracle. NOT derived from the new code.

F4_SCRIPT = [
    _nothing,
    lambda h: (h.age("ar25", 121), h.crash("bp35"), h.rss.__setitem__("cd82", 1500.0)),
    _nothing,
]
F4_STATUSES = [
    "2023-11-14 22:14:26\n"
    "ar25 up=1m rss=300MB db=0MB r/m/c=0/0/0\n"
    "bp35 up=1m rss=300MB db=0MB r/m/c=0/0/0\n"
    "cd82 up=1m rss=300MB db=0MB r/m/c=0/0/0\n",
    "2023-11-14 22:15:26\nar25 RECYCLED#1\nbp35 RESTART#1\ncd82 MEM-KILL#1(1500MB)\n",
    "2023-11-14 22:16:26\n"
    "ar25 up=1m rss=300MB db=0MB r/m/c=0/0/1\n"
    "bp35 up=1m rss=300MB db=0MB r/m/c=1/0/0\n"
    "cd82 up=1m rss=300MB db=0MB r/m/c=0/1/0\n",
]
F4_LEDGER = [
    '{"utc": "2023-11-14T22:13:26", "reason": "initial", "fingerprint": "ffffffffffffffff", '
    '"head": "0123456789ab", "dirty": "M engines/egocentric/gate.py\\n?? record/findings/NEW.md", '
    '"dirty_count": 2}',
]
F4_SPAWNS = ["ar25", "bp35", "cd82", "ar25", "bp35", "cd82"]
F4_STATS = {"ar25": {"restarts": 0, "mem_kills": 0, "recycles": 1},
            "bp35": {"restarts": 1, "mem_kills": 0, "recycles": 0},
            "cd82": {"restarts": 0, "mem_kills": 1, "recycles": 0}}


def test_f4_without_hold_recycle_restart_memkill_are_unchanged(tmp_path, monkeypatch):
    sup, h = _harness(monkeypatch, tmp_path, F4_SCRIPT)
    h.run()
    assert h.statuses == F4_STATUSES, "status.txt changed on a HOLD-free sequence"
    assert h.ledger_lines() == F4_LEDGER, "deploys.jsonl changed on a HOLD-free sequence"
    assert h.spawns == F4_SPAWNS
    assert sup.stats == F4_STATS


# ── F1 + F2: the deferral, and the recycle when HOLD lifts ──────────────────────────────

def test_f1_f2_hold_defers_the_recycle_and_lifting_hold_recycles_once(tmp_path, monkeypatch):
    """poll 1: HOLD up, ar25 past RECYCLE_MIN -> deferred, said so, no spawn, counter 0
       poll 2: HOLD still up -> still deferred (a held worker is not recycled later either)
       poll 3: HOLD lifted -> ar25 RECYCLED#1 through the existing path, exactly one spawn
       poll 4: nothing -> ar25 runs fresh; the counter stays at 1"""
    sup, h = _harness(monkeypatch, tmp_path, [
        lambda h: (h.hold_on(), h.age("ar25", 121)),
        _nothing,
        lambda h: h.hold_off(),
        _nothing,
    ])
    # F1
    h.steps = h.steps[:1]
    h.run()
    (s1,) = h.statuses
    assert "HOLD present" in s1
    deferred = [ln for ln in s1.splitlines() if ln.startswith("ar25 ")]
    assert len(deferred) == 1, s1
    assert "RECYCLE DEFERRED (HOLD)" in deferred[0] and " up=122m" in deferred[0], deferred
    assert "RECYCLED#" not in s1
    assert sup.stats["ar25"]["recycles"] == 0 and h.spawns == FLEET, (
        "F1: the worker was recycled under HOLD -- D-13 is still open")
    # the other two, under RECYCLE_MIN, keep their ordinary lines under HOLD (known-negative)
    assert "bp35 up=1m rss=300MB db=0MB r/m/c=0/0/0" in s1
    assert "cd82 up=1m rss=300MB db=0MB r/m/c=0/0/0" in s1
    assert [r["reason"] for r in h.ledger()] == ["initial"], "a DEFERRAL is not a respawn"


def test_f2_the_deferred_worker_is_recycled_exactly_once_when_hold_lifts(tmp_path, monkeypatch):
    sup, h = _harness(monkeypatch, tmp_path, [
        lambda h: (h.hold_on(), h.age("ar25", 121)),
        _nothing,
        lambda h: h.hold_off(),
        _nothing,
    ])
    h.run()
    s1, s2, s3, s4 = h.statuses
    assert "RECYCLE DEFERRED (HOLD)" in s1 and "RECYCLE DEFERRED (HOLD)" in s2, (
        "a second held poll recycled the deferred worker")
    assert "RECYCLED#" not in s1 and "RECYCLED#" not in s2
    assert "HOLD present" not in s3 and "ar25 RECYCLED#1" in s3, s3
    assert "RECYCLE DEFERRED" not in s3
    assert h.spawns == FLEET + ["ar25"], "F2: the lifted HOLD did not recycle exactly once"
    assert sup.stats["ar25"]["recycles"] == 1
    assert "ar25 up=1m rss=300MB db=0MB r/m/c=0/0/1" in s4, s4
    assert h.spawns == FLEET + ["ar25"], "the recycle fired again on the following poll"
    assert [r["reason"] for r in h.ledger()] == ["initial"], (
        "a recycle through the existing path after HOLD lifts is NOT a respawn-under-hold")


# ── F3: a forced respawn under HOLD is LOUD, through the one assembly ───────────────────

def test_f3_crash_restart_under_hold_spawns_and_ledgers_respawn_under_hold(tmp_path, monkeypatch):
    """poll 1: HOLD up, bp35 crashed -> spawned (the tree is what exists), ONE ledger record
       poll 2: HOLD up, cd82 over MEM_CAP -> the same, trigger=mem_kill
       poll 3: HOLD lifted, ar25 crashed -> restart as today, NO respawn-under-hold record"""
    sup, h = _harness(monkeypatch, tmp_path, [
        lambda h: (h.hold_on(), h.crash("bp35")),
        lambda h: h.rss.__setitem__("cd82", 1500.0),
        lambda h: (h.hold_off(), h.crash("ar25")),
    ])
    h.run()
    s1, s2, s3 = h.statuses
    assert h.spawns == FLEET + ["bp35", "cd82", "ar25"], h.spawns
    assert "bp35 RESTART#1" in s1 and "!! RESPAWN UNDER HOLD" in s1, s1
    loud1 = [ln for ln in s1.splitlines() if ln.startswith("!! RESPAWN UNDER HOLD")]
    assert len(loud1) == 1 and "bp35" in loud1[0] and "restart" in loud1[0], loud1
    assert "cd82 MEM-KILL#1(1500MB)" in s2, s2
    loud2 = [ln for ln in s2.splitlines() if ln.startswith("!! RESPAWN UNDER HOLD")]
    assert len(loud2) == 1 and "cd82" in loud2[0] and "mem_kill" in loud2[0], loud2
    assert "ar25 RESTART#1" in s3 and "RESPAWN UNDER HOLD" not in s3, s3

    ledger = h.ledger()
    assert [r["reason"] for r in ledger] == ["initial", "respawn-under-hold", "respawn-under-hold"], (
        "F3: the ledger does not carry exactly one respawn-under-hold record per forced "
        "respawn under HOLD (and none for the restart after HOLD lifted)")
    initial, r_restart, r_memkill = ledger
    assert (r_restart["game"], r_restart["trigger"]) == ("bp35", "restart")
    assert (r_memkill["game"], r_memkill["trigger"]) == ("cd82", "mem_kill")
    for rec in (r_restart, r_memkill):
        # KEY SET IDENTITY with a deploy record from the same function, plus the two names
        assert set(rec) == set(initial) | {"game", "trigger"}, (set(rec), set(initial))
        for k in ("head", "dirty", "dirty_count", "fingerprint"):
            assert rec[k] == initial[k], (k, rec[k], initial[k])
    # the ledger's byte shape for a respawn record: the deploy fields first, in the deploy
    # order, then game, then trigger
    assert list(r_restart) == list(initial) + ["game", "trigger"]
    assert h.ledger_lines()[0] == F4_LEDGER[0], "the initial record's bytes changed"


def test_f3_one_assembly_cited_by_source():
    """The head/dirty assembly exists ONCE (deploy_record); record_deploy and
    record_respawn_under_hold both call it; neither rebuilds it. Asserted on the shipped
    file, by AST, not on this test's idea of it."""
    import ast
    text = open(SUPERVISOR_SRC, encoding="utf-8").read()
    assert text.count('"rev-parse"') == 1 and text.count('"--porcelain"') == 1, (
        "the git head/dirty assembly exists in more than one place")
    tree = ast.parse(text)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    for name in ("deploy_record", "record_deploy", "record_respawn_under_hold"):
        assert name in fns, "supervisor is missing %s" % name
    assert "rev-parse" in ast.unparse(fns["deploy_record"])   # unparse single-quotes strings
    for caller in ("record_deploy", "record_respawn_under_hold"):
        calls = [n.func.id for n in ast.walk(fns[caller])
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        assert "deploy_record" in calls, "%s does not go through deploy_record" % caller
    main_src = ast.unparse(fns["main"])
    assert main_src.count("record_respawn_under_hold(g, 'restart')") == 1
    assert main_src.count("record_respawn_under_hold(g, 'mem_kill')") == 1
    assert "RECYCLE DEFERRED (HOLD)" in main_src
    assert "RECYCLE_MIN" in main_src, "RECYCLE_MIN is no longer the recycle condition"
    for knob in ("RECYCLE_MIN = 120", "MEM_CAP_MB = 1200", "POLL_SEC = 60"):
        assert knob in text, "a knob moved: %r (no new knob, RECYCLE_MIN unchanged)" % knob


# ── F5: importing the supervisor still performs no I/O ──────────────────────────────────

def test_f5_import_performs_no_io(monkeypatch):
    """The D-6 lesson at tooling grain, re-asserted here in the same shape as
    test_sprint_keeper's gate: .env unreadable, makedirs / Popen mocked, sleep forbidden --
    a fresh import touches none of them, and the new functions are not called at top level."""
    real_open = builtins.open

    def no_env(path, *a, **kw):
        if str(path).endswith(".env"):
            raise FileNotFoundError(".env is absent in this test: %s" % path)
        return real_open(path, *a, **kw)

    makedirs, popen = mock.Mock(name="os.makedirs"), mock.Mock(name="subprocess.Popen")
    monkeypatch.setattr(builtins, "open", no_env)
    monkeypatch.setattr(os, "makedirs", makedirs)
    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(subprocess, "run", mock.Mock(side_effect=AssertionError("git ran at import")))
    monkeypatch.setattr(_real_time, "sleep", mock.Mock(side_effect=AssertionError("the poll loop ran")))
    sys.modules.pop("tools.swarm_supervisor", None)
    sup = importlib.import_module("tools.swarm_supervisor")
    assert makedirs.call_count == 0 and popen.call_count == 0
    assert sup.KEY is None and sup.procs == {}
    import ast
    tree = ast.parse(open(SUPERVISOR_SRC, encoding="utf-8").read())
    top = ast.unparse(ast.Module(body=[n for n in tree.body
                                       if not isinstance(n, (ast.FunctionDef, ast.If))],
                                 type_ignores=[]))
    for effect in ("deploy_record(", "record_respawn_under_hold(", "append_ledger(",
                   "code_fingerprint(", "makedirs", "Popen"):
        assert effect not in top, "module level performs %r" % effect
    assert 'if __name__ == "__main__":\n    main()' in open(SUPERVISOR_SRC, encoding="utf-8").read()
