"""R3 GATE (PREREG_READOUTS.md): produced-but-never-consumed — the build gate.

Static source inventory over the repo's PRODUCTION python sources: every fabric topic
WRITTEN somewhere (an `.append(scope, "topic", record)` call whose topic resolves to a
literal string) must be READ somewhere OUTSIDE its writer (a `.query(scope, "topic", ...)`
site that is not one of the topic's own write sites), OR appear in the explicit ALLOWLIST
below, where each entry cites a prereg — an open socket is a named promise, not silence.

THE GATE TIGHTENS MONOTONICALLY: when a consumer lands, its allowlist entry is DELETED;
a stale entry (an allowlisted topic that HAS grown a reader, or is no longer written at
all) fails the gate too.

"outside its writer" is per WRITE SITE (module, enclosing function): the reader must be a
different site than the writer — a book that writes in `record_x` and reads in `load_x`
has a real consumer; a stream nothing ever queries does not.

Topic literals are resolved through module- and class-level string constants
(`TOPIC = "atoms"` etc.); unresolvable dynamic topics are outside this gate's reach.

KNOWN OPEN TODAY: "levelup_frames" (VICTORY_PROTOCOL.md record-keeping) — written by
GoalBook.observe_levelup so the level-up pre/post snapshots survive; its consumer is
the OFF-LINE 25/25 victory census (archive + annotate), not runtime code, so the
entry stands as a cited promise. import_queue's consumer landed (B12,
engines/egocentric/consumer.py — the triangulation consumer) and its entry was
deleted per the monotone rule; this gate asserts the reader by name below.
"starvation" is NOT allowlisted — R1's seed-bias reader (AffectGains.starvation_steer)
is its consumer, and this gate asserts that by name.
"""
from __future__ import annotations

import ast
import os
import sys
from typing import Dict, List, Set, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# topic -> prereg citation. DELETE the entry when the consumer lands.
# B15: import_queue's entry DELETED — the triangulation consumer (B12) reads it.
ALLOWLIST: Dict[str, str] = {
    "levelup_frames": (
        "VICTORY_PROTOCOL.md (records kept NOW, unrecoverable later): level-up "
        "pre/post frame snapshots, persisted by GoalBook.observe_levelup; the "
        "consumer is the off-line 25/25 victory census (archive + annotate)"),
    "rho_readings": (
        "THE_LADDER.md rung 4 (adoption: 'traffic collapsed + r0 nonzero, or "
        "climbing + r0 flat?') + the testimony law (every produced stream "
        "needs a NAMED consumer -- the beat protocol is this one's, by name): "
        "the per-pass multi-rung rho readings (KNOBS Amendment 2, persisted "
        "by consumer._persist_rho_readings) are read at every diagnostic "
        "beat beside the counters; runtime writes, the seat reads -- the "
        "adoption rung is unanswerable without this stream"),
    "narration": (
        "PREREG_W1_NARRATION.md (W1: the narration spine + memory at three "
        "ranges): the agent narrates its own loop in the loop's vocabulary -- "
        "bet-side records (BET/PLAN/ACT) BEFORE the action executes, "
        "outcome-side records (PERCEIVE/ROUTE/MINT/ECHO) closing against the "
        "bet by reference, every record tagged [EP]/[OWN]/[COL] ([REPLAY] for "
        "playback). THE CONSUMER LANDS WITH THE FALSIFIER EXPERIMENT (arm C, "
        "narrate-and-consume: ROUTE/MINT read their own immediately-prior "
        "narration state vs arm W write-but-never-read); this entry is "
        "deleted then"),
    "gate": (
        "PREREG_GATE_STAGE1_SHADOW.md (REASONING GATE STAGE 1: SHADOW MODE): one "
        "JSONL record per utterance (PERCEIVE / BET / ACT + a per-step SUMMARY, "
        "the MODE record, at most one DOWNGRADE) written by "
        "engines/egocentric/gate.py:ReasoningGate._emit from the ONE hook beside "
        "the spine's act() (cognitive_loop._gate_step). THE CONSUMER IS THE BEAT "
        "READ: the three-number per-game coverage report "
        "(gate.coverage_report -- derivations : negative derivations : probes, "
        "stratified by action-book evidence stratum, with the would-refuse rate "
        "per head) that stage 2's flip decision cites (the probe-share pin, the "
        "three-number rule). No runtime code reads this stream by design: shadow "
        "blocks nothing and no decision depends on a verdict. This entry is "
        "deleted when stage 2's enforcement consumer lands -- and the deadline "
        "mechanism (gate.deadline_violation) refuses that flip until the "
        "opener-side PERCEIVE has relocated into the spine"),
    "refit_queue": (
        "PREREG_REFIT_DESTINATION.md (Seat 3 ruling, 2026-08-19): ROUTE has four "
        "bins and BROKEN-rebinding was the only one with no destination -- it "
        "appended to an in-memory list referenced nowhere, so the bin that means "
        "'repair this, do not mint' died with the process. The ruled order is "
        "DESTINATION BEFORE SWITCH, because a diagnosis that dies with the "
        "process is not a diagnosis; `binding_stale` is still set by nothing, so "
        "the drain is a NO-OP today and the stream is empty by construction. THE "
        "CONSUMER LANDS WITH THE SWITCH BUILD, and this entry is deleted then -- "
        "which is also when the topic first carries a record"),
}

# Production sources only: tests are fixtures, not consumers; caches/vendored
# trees are noise; docs and any proctor material are off-limits by firewall.
_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "tests", "docs",
              ".pytest_cache", ".runs", ".gamma_library", ".residual_bank",
              ".claude", ".github", "node_modules"}

_SCOPES = {"personal", "kin", "collective"}

Site = Tuple[str, str]                      # (relative path, enclosing function)
Sites = Dict[str, Set[Site]]                # topic -> sites


def _py_files() -> List[str]:
    out: List[str] = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in sorted(dirs)
                   if d not in _SKIP_DIRS and "train set answers" not in d.lower()]
        for name in sorted(files):
            if name.endswith(".py"):
                out.append(os.path.join(root, name))
    return out


def _string_consts(tree: ast.Module) -> Dict[str, str]:
    """Module- and class-level NAME = "literal" assignments (topic constants)."""
    consts: Dict[str, str] = {}
    def take(node):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    consts[t.id] = node.value.value
    for node in tree.body:
        take(node)
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                take(sub)
    return consts


def _scan_file(path: str, rel: str, writes: Sites, reads: Sites) -> None:
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    # Cheap prefilter: a fabric site needs BOTH a call spelling and a scope
    # literal somewhere in the file -- parsing 300+ sources without one is waste.
    if not any('"%s"' % s in src or "'%s'" % s in src for s in _SCOPES):
        return
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    consts = _string_consts(tree)
    stack = ["<module>"]

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            stack.append(node.name)
            self.generic_visit(node)
            stack.pop()
        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr in ("append", "query")
                    and len(node.args) >= 2):
                a0, a1 = node.args[0], node.args[1]
                scoped = ((isinstance(a0, ast.Constant) and a0.value in _SCOPES)
                          or (isinstance(a0, ast.Name) and a0.id == "scope"))
                topic = None
                if isinstance(a1, ast.Constant) and isinstance(a1.value, str):
                    topic = a1.value
                elif isinstance(a1, ast.Name):
                    topic = consts.get(a1.id)
                elif isinstance(a1, ast.Attribute):
                    topic = consts.get(a1.attr)
                # fabric.append(scope, topic, record) has exactly 3 positional
                # args -- the arity plus the scope literal keeps list.append and
                # unrelated .query APIs out of the inventory.
                if scoped and topic is not None and (
                        f.attr == "query" or len(node.args) == 3):
                    book = writes if f.attr == "append" else reads
                    book.setdefault(topic, set()).add((rel, stack[-1]))
            self.generic_visit(node)

    V().visit(tree)


_SCAN_CACHE: List[Tuple[Sites, Sites]] = []


def _scan() -> Tuple[Sites, Sites]:
    """One inventory per test run (the sources do not change mid-run)."""
    if not _SCAN_CACHE:
        writes: Sites = {}
        reads: Sites = {}
        for path in _py_files():
            _scan_file(path, os.path.relpath(path, REPO).replace("\\", "/"),
                       writes, reads)
        _SCAN_CACHE.append((writes, reads))
    return _SCAN_CACHE[0]


def _outside_readers(topic: str, writes: Sites, reads: Sites) -> Set[Site]:
    return {s for s in reads.get(topic, set())
            if s not in writes.get(topic, set())}


def _violations(writes: Sites, reads: Sites,
                allowlist: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """PURE checker: (unconsumed topics, stale allowlist entries)."""
    unconsumed = [t for t in sorted(writes)
                  if t not in allowlist and not _outside_readers(t, writes, reads)]
    stale = [t for t in sorted(allowlist)
             if t not in writes or _outside_readers(t, writes, reads)]
    return unconsumed, stale


class TestTheGate:

    def test_every_written_topic_is_consumed_or_a_cited_promise(self):
        writes, reads = _scan()
        assert writes, "the scanner found no fabric writes at all -- it is broken"
        unconsumed, _ = _violations(writes, reads, ALLOWLIST)
        assert unconsumed == [], (
            "produced-but-never-consumed topics with no cited promise: %r -- "
            "wire a reader or add an allowlist entry citing its prereg"
            % (unconsumed,))

    def test_no_stale_allowlist_entries(self):
        """The gate tightens monotonically: a consumer landing DELETES its
        entry; an entry whose topic grew a reader (or vanished) fails."""
        writes, reads = _scan()
        _, stale = _violations(writes, reads, ALLOWLIST)
        assert stale == [], (
            "stale allowlist entries %r -- the topic has a consumer now (or is "
            "no longer written): delete the entry" % (stale,))

    def test_every_allowlist_entry_cites_a_prereg(self):
        for topic, cite in ALLOWLIST.items():
            assert isinstance(cite, str) and cite.strip(), (
                "allowlist entry %r carries no citation -- an open socket is a "
                "named promise, not silence" % (topic,))

    def test_import_queue_has_its_consumer_and_no_entry(self):
        """B15 (the monotone tightening): the triangulation consumer (B12) reads
        the queue now — the reader must exist BY NAME and the entry must be gone."""
        assert "import_queue" not in ALLOWLIST
        writes, reads = _scan()
        assert "import_queue" in writes, "the import_queue writer vanished"
        outside = _outside_readers("import_queue", writes, reads)
        assert outside, "import_queue lost its consumer (the triangulation consumer)"
        assert any("consumer" in path for path, _fn in outside), (
            "the import_queue reader is not the triangulation consumer")

    def test_starvation_is_consumed_and_not_allowlisted(self):
        """R1's stream must live by consumption, not by promise."""
        assert "starvation" not in ALLOWLIST
        writes, reads = _scan()
        assert "starvation" in writes, "the StarvationBook writer vanished"
        outside = _outside_readers("starvation", writes, reads)
        assert outside, "starvation lost its consumer (AffectGains.starvation_steer)"
        assert any("affect" in path for path, _fn in outside)


class TestTheFalsifier:
    """The checker itself, falsified on synthetic inventories (pure function)."""

    def test_a_writer_with_no_reader_and_no_entry_fails(self):
        writes = {"orphan": {("a.py", "write_it")}}
        unconsumed, _ = _violations(writes, {}, {})
        assert unconsumed == ["orphan"]

    def test_a_cited_entry_admits_the_orphan(self):
        writes = {"orphan": {("a.py", "write_it")}}
        unconsumed, stale = _violations(writes, {}, {"orphan": "PREREG_X §1"})
        assert unconsumed == [] and stale == []

    def test_a_reader_in_the_writers_own_site_does_not_count(self):
        writes = {"t": {("a.py", "f")}}
        reads = {"t": {("a.py", "f")}}
        unconsumed, _ = _violations(writes, reads, {})
        assert unconsumed == ["t"], "a site reading its own write is not a consumer"

    def test_deleting_the_real_consumer_turns_the_gate_red(self):
        writes = {"t": {("a.py", "w")}}
        reads = {"t": {("b.py", "r")}}
        assert _violations(writes, reads, {})[0] == []
        assert _violations(writes, {}, {})[0] == ["t"]

    def test_a_stale_entry_fails_when_the_consumer_lands(self):
        writes = {"t": {("a.py", "w")}}
        reads = {"t": {("b.py", "r")}}
        _, stale = _violations(writes, reads, {"t": "PREREG_X §1"})
        assert stale == ["t"], "the entry must be DELETED once the consumer exists"
