"""fabric.py -- Phase 3a: the knowledge fabric + the idea economy (PREREG_PHASE3A.md §1).

Pure-stdlib JSONL streams under scoped directories -- no database, no wall-clock, no threads:

  * scopes: "collective" -> collective/, "personal" -> personal/<agent_id>/,
    "kin" -> kin/<kin_key>/; a stream is <scopedir>/<topic>.jsonl;
  * `append()` adds a monotonic per-stream "seq" read back from disk (reopen continues);
  * `seeds` are READ-ONLY overlay roots (the verified Kaggle pattern: mounted input +
    local working) -- queried first, never written;
  * a corrupt line (a crash mid-write) is skipped silently, never fatal;
  * the idea economy on top: MINT only on signal (the wheel rule extends to memory),
    ECHO pays the origin author (reputation -- the viral reward), FALSIFY pariah-marks
    defeasibly (down-ranked, never deleted).
"""
from __future__ import annotations

import io
import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple


class KnowledgeFabric:
    """Scoped JSONL memory with a seed overlay and the mint/echo/falsify economy."""

    IDEAS_TOPIC = "ideas"
    EVENTS_TOPIC = "idea_events"
    _SCOPE_PREF = {"personal": 0, "kin": 1, "collective": 2}

    def __init__(self, root: str, seeds: Optional[List[str]] = None,
                 agent_id: str = "agent", kin_key: str = "kin"):
        # creates NOTHING on disk until the first append; reads are lazy
        self.root = str(root)
        self.seeds = [str(s) for s in (seeds or [])]
        self.agent_id = str(agent_id)
        self.kin_key = str(kin_key)

    # ── scope / stream resolution ─────────────────────────────────────────────

    def _scope_rel(self, scope: str) -> str:
        if scope == "collective":
            return "collective"
        if scope == "personal":
            return os.path.join("personal", self.agent_id)
        if scope == "kin":
            return os.path.join("kin", self.kin_key)
        raise ValueError("unknown scope: %r" % (scope,))

    def _stream_path(self, base: str, scope: str, topic: str) -> str:
        return os.path.join(base, self._scope_rel(scope), str(topic) + ".jsonl")

    @staticmethod
    def _read_stream(path: str) -> List[Dict[str, Any]]:
        """All well-formed records in one stream file; corrupt lines skipped silently."""
        out: List[Dict[str, Any]] = []
        if not os.path.isfile(path):
            return out
        with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue                     # crash mid-write: skipped, never fatal
                if isinstance(rec, dict):
                    out.append(rec)
        return out

    def _next_seq(self, scope: str, topic: str) -> int:
        """1 + max existing seq in the LOCAL stream (seeds are never appended to)."""
        top = 0
        for rec in self._read_stream(self._stream_path(self.root, scope, topic)):
            try:
                top = max(top, int(rec.get("seq", 0)))
            except Exception:
                continue
        return top + 1

    # ── the fabric: append / query ────────────────────────────────────────────

    def append(self, scope: str, topic: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Append one record to the LOCAL stream; adds monotonic "seq"; returns it enriched."""
        rec = dict(record)
        rec["seq"] = self._next_seq(scope, topic)
        path = self._stream_path(self.root, scope, topic)
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with io.open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def query(self, scope: str, topic: str,
              where: Optional[Callable[[Dict[str, Any]], Any]] = None,
              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Records in insertion order: seed roots FIRST, then the local root."""
        out: List[Dict[str, Any]] = []
        for base in list(self.seeds) + [self.root]:
            for rec in self._read_stream(self._stream_path(base, scope, topic)):
                if where is not None and not where(rec):
                    continue
                out.append(rec)
                if limit is not None and len(out) >= limit:
                    return out
        return out

    # ── the idea economy ──────────────────────────────────────────────────────

    def mint(self, idea: Dict[str, Any], game: str, signal: Any,
             scope: str = "personal") -> str:
        """Mint an idea into ONE scope's "ideas" stream. Raises WITHOUT a signal --
        the wheel rule extends to memory: nothing is minted on silence."""
        if not signal:
            raise ValueError("mint requires a signal -- no idea is minted on silence")
        seq = self._next_seq(scope, self.IDEAS_TOPIC)
        idea_id = "%s:%s:%s:%d" % (game, scope, self.agent_id, seq)
        self.append(scope, self.IDEAS_TOPIC, {
            "id": idea_id, "idea": idea, "game": game,
            "by": self.agent_id, "scope": scope, "signal": signal,
        })
        return idea_id

    def echo(self, idea_id: str, by: str) -> Dict[str, Any]:
        """Corroborate: visible to everyone (COLLECTIVE events stream)."""
        return self.append("collective", self.EVENTS_TOPIC,
                           {"ev": "echo", "id": str(idea_id), "by": str(by)})

    def falsify(self, idea_id: str, by: str) -> Dict[str, Any]:
        """Refute defeasibly: down-ranks (pariah), never deletes."""
        return self.append("collective", self.EVENTS_TOPIC,
                           {"ev": "falsify", "id": str(idea_id), "by": str(by)})

    def _event_counts(self) -> Dict[str, Tuple[int, int]]:
        """idea id -> (#echoes, #falsifies) over ALL visible events (seeds + local)."""
        counts: Dict[str, List[int]] = {}
        for rec in self.query("collective", self.EVENTS_TOPIC):
            iid = rec.get("id")
            if iid is None:
                continue
            pair = counts.setdefault(str(iid), [0, 0])
            ev = rec.get("ev")
            if ev == "echo":
                pair[0] += 1
            elif ev == "falsify":
                pair[1] += 1
        return {k: (v[0], v[1]) for k, v in counts.items()}

    def credibility(self, idea_id: str) -> int:
        e, f = self._event_counts().get(str(idea_id), (0, 0))
        return e - 2 * f

    def _all_idea_streams(self) -> List[str]:
        """Every "ideas" stream visible anywhere: collective + ALL personal/kin subdirs
        that exist in the seed roots and the local root (walked, not assumed)."""
        paths: List[str] = []
        for base in list(self.seeds) + [self.root]:
            paths.append(os.path.join(base, "collective", self.IDEAS_TOPIC + ".jsonl"))
            for family in ("personal", "kin"):
                d = os.path.join(base, family)
                if not os.path.isdir(d):
                    continue
                for name in sorted(os.listdir(d)):
                    paths.append(os.path.join(d, name, self.IDEAS_TOPIC + ".jsonl"))
        return paths

    def reputation(self, agent_id: str) -> int:
        """Sum over ideas MINTED BY `agent_id` of max(0, #echoes) -- the viral reward:
        an echo pays the ORIGIN author, wherever the idea was minted."""
        counts = self._event_counts()
        seen: set = set()
        total = 0
        for path in self._all_idea_streams():
            for rec in self._read_stream(path):
                if rec.get("by") != agent_id:
                    continue
                iid = rec.get("id")
                if iid is None or iid in seen:
                    continue
                seen.add(iid)
                total += max(0, counts.get(str(iid), (0, 0))[0])
        return total

    def priors(self, game: str) -> List[Dict[str, Any]]:
        """All visible ideas for `game` across collective + own personal + own kin,
        deduped by id; ranked pariahs LAST, then credibility desc, then nearer evidence
        (personal < kin < collective), then id asc. Deterministic."""
        counts = self._event_counts()
        out: List[Dict[str, Any]] = []
        seen: set = set()
        for scope in ("personal", "kin", "collective"):
            for rec in self.query(scope, self.IDEAS_TOPIC):
                if rec.get("game") != game:
                    continue
                iid = rec.get("id")
                if iid is None or iid in seen:
                    continue
                seen.add(iid)
                e, f = counts.get(str(iid), (0, 0))
                out.append({
                    "id": iid,
                    "idea": rec.get("idea"),
                    "game": rec.get("game"),
                    "by": rec.get("by"),
                    "scope": rec.get("scope", scope),
                    "credibility": e - 2 * f,
                    "pariah": f > e,
                })
        out.sort(key=lambda p: (bool(p["pariah"]), -int(p["credibility"]),
                                self._SCOPE_PREF.get(p["scope"], 3), str(p["id"])))
        return out
