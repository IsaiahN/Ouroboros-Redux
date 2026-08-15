"""janitor.py -- B14 FABRIC_JANITOR (PREREG_SMART_CLEANUP.md): compaction that changes
NO consumer answer.

Philosophy (the prereg): keep knowledge forever, cap telemetry; SIZE-triggered, never
cadence-triggered; LOUD, never silent (a [JANITOR] manifest prints on every sweep);
compaction, not deletion, where data has summary value.

THE FALSIFIER is byte-equality of every consumer-visible answer pre/post compaction --
the consumer's pending/open_not_found/candidates, affect's gains/narration/steer, the
idea economy's priors/credibility/reputation, harvest merge, mastery rate, the atoms
query. Any changed answer means this tool is WRONG (revert). The gate suite enumerates
those queries; here the policies are shaped so equality holds by construction:

  * import_queue -- ONLY entries closed by a CANDIDATE are dropped (the raw record, its
    sigma entry, its consumed marker): pending() already excludes them. Open items,
    their sigma entries, and the latest not-found per item survive untouched (the
    Chaitin rule: an open elimination is never deleted); superseded not-founds -- older
    generations of the same item's watermark chain -- fold away. A tombstone record
    keeps the stream's seq high-water mark, so no dropped seq is ever reused (candidate
    records reference src/match seqs by number forever).
  * settlements -- the last SETTLE_KEEP raw records are kept (affect's window is 20;
    margin 5x); older ones fold into ONE cumulative counter record (n, nontrivial_n).
  * mint_verdicts -- aged REJECTS (beyond the last VERDICT_KEEP records) are STRIPPED
    in place to {verdict, seq}: record counts -- and therefore the narration's
    mint/total arithmetic -- are preserved exactly; mints, rederivations and
    quarantines are never touched (mints are knowledge, not churn).

NEVER compacted, by construction (the policy table simply does not name them): atoms,
atom_narrowings, ideas, idea_events (priors/credibility/reputation), frontier_paths,
frontier_harvest, starvation, import_candidates, replay_outcomes. Seed roots are
read-only mounts and are never touched; only the LOCAL root is rewritten.

THE ARCHIVE LAW (VICTORY_PROTOCOL.md record-keeping): the janitor ARCHIVES before it
folds, strips or drops -- every record a sweep removes is appended VERBATIM (the
original line, never re-serialized) to <stream>.archive.jsonl BEFORE the stream is
rewritten. The archive is append-only, sits outside the size trigger (the trigger
stats only <topic>.jsonl) and outside every policy (never compacted, never read back
by consumers). FALSIFIER: archive + surviving original lines == the original stream,
as a multiset of verbatim lines -- compaction now loses NOTHING, it relocates.

Rewrites are atomic with a .bak (write tmp -> original becomes .bak -> tmp replaces
original); kept records are copied byte-verbatim (original lines, never re-serialized);
unparseable lines are preserved as-is (a crash mid-write is evidence, not garbage).
Offline discipline: run on a stopped or paused box (the swarm supervisor's contract).

Deterministic, stdlib only; failures degrade to an error count in the manifest.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["FabricJanitor"]

Line = Tuple[str, Optional[Dict[str, Any]]]         # (raw line, parsed record or None)


class FabricJanitor:
    """Size-triggered compactor for ONE fabric's high-churn local streams."""

    STREAM_MAX_BYTES = 2 * 1024 * 1024      # the prereg's 2 MB per-stream trigger
    SETTLE_KEEP = 100                       # affect's window is 20; margin 5x
    VERDICT_KEEP = 200                      # recent verdicts stay verbatim

    def __init__(self, fabric, max_stream_bytes: Optional[int] = None,
                 settle_keep: Optional[int] = None,
                 verdict_keep: Optional[int] = None):
        self.fabric = fabric
        self.max_stream_bytes = int(max_stream_bytes if max_stream_bytes is not None
                                    else self.STREAM_MAX_BYTES)
        self.settle_keep = int(settle_keep if settle_keep is not None
                               else self.SETTLE_KEEP)
        self.verdict_keep = int(verdict_keep if verdict_keep is not None
                                else self.VERDICT_KEEP)
        self.errors = 0

    # ── stream IO (local root only; seeds are read-only mounts) ──────────────

    def _path(self, topic: str) -> str:
        return os.path.join(str(self.fabric.root), "collective", topic + ".jsonl")

    @staticmethod
    def _read_lines(path: str) -> List[Line]:
        out: List[Line] = []
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.rstrip("\n")
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    rec = None
                out.append((line, rec if isinstance(rec, dict) else None))
        return out

    @staticmethod
    def _rewrite(path: str, lines: List[str]) -> None:
        """Atomic with .bak: tmp holds the new content, the original becomes .bak."""
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line + "\n")
        bak = path + ".bak"
        if os.path.isfile(bak):
            os.remove(bak)
        os.replace(path, bak)
        os.replace(tmp, path)

    @staticmethod
    def _dump(rec: Dict[str, Any]) -> str:
        return json.dumps(rec, ensure_ascii=False)

    @staticmethod
    def _archive_removed(path: str, original: List[Line],
                         kept: List[str]) -> int:
        """THE ARCHIVE LAW: append every original line NOT surviving verbatim in
        `kept` to <stream>.archive.jsonl (multiset-aware -- duplicates archived
        exactly as many times as they were removed), BEFORE the rewrite touches
        the stream: a crash between archive and rewrite duplicates a line into
        the archive at worst, it never loses one. Returns the archived count."""
        budget = Counter(kept)                       # kept lines still unclaimed
        removed: List[str] = []
        for line, _r in original:
            if budget[line] > 0:
                budget[line] -= 1                    # a verbatim survivor
            else:
                removed.append(line)
        if removed:
            base = path[:-6] if path.endswith(".jsonl") else path
            with open(base + ".archive.jsonl", "a", encoding="utf-8") as fh:
                for line in removed:
                    fh.write(line + "\n")
        return len(removed)

    # ── per-stream policies: (kept lines, manifest note) ─────────────────────

    def _compact_queue(self, lines: List[Line]) -> Tuple[List[str], Dict[str, Any]]:
        recs = [r for _l, r in lines if r is not None]
        closed = {int(r.get("src_seq", -1)) for r in recs
                  if r.get("kind") == "consumed"}
        latest_nf: Dict[int, int] = {}
        top_seq = 0
        for r in recs:
            top_seq = max(top_seq, int(r.get("seq", 0)))
            if r.get("kind") == "not_found":
                latest_nf[int(r.get("src_seq", -1))] = int(r.get("seq", 0))
        kept: List[str] = []
        dropped = 0                     # real drops this sweep (tombstones excluded)
        tombstoned = 0                  # cumulative count carried by old tombstones
        for line, r in lines:
            if r is None:                                   # evidence, not garbage
                kept.append(line)
                continue
            kind = r.get("kind")
            src = int(r.get("src_seq", -1))
            if kind == "compacted":                         # folded into the new tombstone
                tombstoned += int(r.get("dropped", 0))
                continue
            drop = (
                (kind is None and int(r.get("seq", -1)) in closed)      # consumed raw
                or (kind == "sigma" and src in closed)
                or (kind == "consumed")                     # the candidate holds the proof
                or (kind == "not_found"
                    and (src in closed                       # closed later by a candidate
                         or int(r.get("seq", 0)) != latest_nf.get(src)))  # superseded
            )
            if drop:
                dropped += 1
            else:
                kept.append(line)
        if dropped == 0:
            return [line for line, _r in lines], {"dropped_entries": 0}
        kept.append(self._dump({"kind": "compacted", "dropped": dropped + tombstoned,
                                "seq": top_seq}))           # seq high-water mark survives
        return kept, {"dropped_entries": dropped}

    def _compact_settlements(self, lines: List[Line]) -> Tuple[List[str],
                                                               Dict[str, Any]]:
        if len(lines) <= self.settle_keep:
            return [line for line, _r in lines], {"folded": 0}
        aged, kept_tail = lines[:-self.settle_keep], lines[-self.settle_keep:]
        n = nontrivial = 0
        seq = None
        for _line, r in aged:
            if r is None:
                continue
            if r.get("kind") == "fold":                     # merge the previous fold
                n += int(r.get("n", 0))
                nontrivial += int(r.get("nontrivial_n", 0))
            else:
                n += 1
                nontrivial += 1 if r.get("nontrivial") else 0
            if seq is None:
                seq = int(r.get("seq", 0))
        fold = self._dump({"kind": "fold", "n": n, "nontrivial_n": nontrivial,
                           "seq": int(seq or 0)})
        return [fold] + [line for line, _r in kept_tail], {"folded": n}

    def _compact_verdicts(self, lines: List[Line]) -> Tuple[List[str], Dict[str, Any]]:
        if len(lines) <= self.verdict_keep:
            return [line for line, _r in lines], {"stripped": 0}
        kept: List[str] = []
        stripped = 0
        for line, r in lines[:-self.verdict_keep]:
            if (r is not None and r.get("verdict") == "reject"
                    and set(r) != {"verdict", "seq"}):
                kept.append(self._dump({"verdict": "reject",
                                        "seq": int(r.get("seq", 0))}))
                stripped += 1
            else:
                kept.append(line)                           # mints etc: knowledge, kept
        kept.extend(line for line, _r in lines[-self.verdict_keep:])
        return kept, {"stripped": stripped}

    # ── the sweep ────────────────────────────────────────────────────────────

    def sweep(self) -> Dict[str, Dict[str, Any]]:
        """Check each compactable stream's size; compact the ones over threshold;
        print the manifest ALWAYS (the silent-failure fix); return the report."""
        policies = (("import_queue", self._compact_queue),
                    ("settlements", self._compact_settlements),
                    ("mint_verdicts", self._compact_verdicts))
        report: Dict[str, Dict[str, Any]] = {}
        for topic, policy in policies:
            path = self._path(topic)
            size = os.path.getsize(path) if os.path.isfile(path) else 0
            entry: Dict[str, Any] = {"bytes": size}
            if size <= self.max_stream_bytes:
                entry["action"] = "under-threshold"
                report[topic] = entry
                continue
            try:
                lines = self._read_lines(path)
                kept, note = policy(lines)
                if kept == [line for line, _r in lines]:
                    entry["action"] = "nothing-to-drop"
                else:
                    # ARCHIVE FIRST (VICTORY_PROTOCOL): removed records land in
                    # <stream>.archive.jsonl before the stream is rewritten.
                    entry["archived"] = self._archive_removed(path, lines, kept)
                    self._rewrite(path, kept)
                    entry["action"] = "compacted"
                    entry["bytes_after"] = os.path.getsize(path)
                    entry.update(note)
            except Exception as e:
                self.errors += 1
                entry["action"] = "ERROR"
                entry["error"] = repr(e)
            report[topic] = entry
        self._narrate(report)
        return report

    def _narrate(self, report: Dict[str, Dict[str, Any]]) -> None:
        parts = []
        for topic, entry in report.items():
            detail = " ".join("%s=%s" % (k, v) for k, v in sorted(entry.items())
                              if k != "action")
            parts.append("%s: %s (%s)" % (topic, entry.get("action"), detail))
        print("[JANITOR] " + " | ".join(parts) + " | errors=%d" % self.errors)
