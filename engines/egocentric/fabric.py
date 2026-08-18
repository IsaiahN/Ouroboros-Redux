"""fabric.py -- Phase 3a: the knowledge fabric + the idea economy (PREREG_PHASE3A.md §1).

Pure-stdlib JSONL streams under scoped directories -- no database, no wall-clock, no threads:

  * scopes: "collective" -> collective/, "personal" -> personal/<agent_id>/,
    "kin" -> kin/<kin_key>/; a stream is <scopedir>/<topic>.jsonl;
  * `append()` adds a monotonic per-stream "seq" read back from disk (reopen continues);
    the seq high-water mark is CACHED per stream after the first read and advanced in
    memory -- re-read only when the file's size stops matching this writer's own
    bookkeeping (a janitor rewrite shrinks it; any out-of-band byte is a reason to
    re-read) or on explicit reload_seqs(). CROSS-PROCESS INVARIANT: each stream has a
    single WRITER process by design (own-scope appends only; seed mounts are read-only
    and never appended to), so the in-memory advance can never hand out a seq twice;
  * `seeds` are READ-ONLY overlay roots (the verified Kaggle pattern: mounted input +
    local working) -- queried first, never written;
  * a corrupt line (a crash mid-write) is skipped silently, never fatal;
  * the idea economy on top: MINT only on signal (the wheel rule extends to memory),
    ECHO pays the origin author (reputation -- the viral reward), FALSIFY pariah-marks
    defeasibly (down-ranked, never deleted).
"""
from __future__ import annotations

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
        # seq cache: (scope, topic) -> {"seq": last LOCAL seq, "size": file size
        # after this writer's last sync, "clean": file ends in a newline}. Valid
        # only while the file's size still matches "size" -- our own appends keep
        # it matched; any out-of-band byte (janitor shrink, torn tail, foreign
        # write) forces a full re-read. Safe across the swarm because each stream
        # has ONE writer process (own-scope appends only; seeds are read-only).
        self._seq_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}

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
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue                     # crash mid-write: skipped, never fatal
                if isinstance(rec, dict):
                    out.append(rec)
        return out

    # Tail-read block: one read of this size answers a 20-record question against
    # every stream shape measured on the live boxes (ls20 settlements average 155
    # bytes/record, so 64 KiB is ~420 records of headroom). It is a starting point,
    # not a bound -- the reader doubles it until it holds enough RECORDS, so a
    # stream of 20 KiB records is slower, never wrong.
    _TAIL_BLOCK = 65536

    @classmethod
    def _tail_lines(cls, blob: bytes) -> List[str]:
        """Split a byte range on the SAME line boundaries text mode would.

        `_read_stream` opens with encoding="utf-8", errors="replace" and the default
        newline=None -- universal newlines -- so "\\r\\n", "\\r" and "\\n" are all
        terminators and nothing else is. `str.splitlines()` is NOT this function: it
        also breaks on \\v, \\f, \\x1c-\\x1e, \\x85, \\u2028 and \\u2029, any of which
        inside a JSON string would split one record into two and diverge.

        Decoding a slice rather than the file is safe ONLY because callers hand this a
        range that begins at a line boundary: 0x0A and 0x0D can never occur inside a
        multi-byte UTF-8 sequence (continuation bytes are >= 0x80), so a terminator
        always closes any sequence and the decoder starts the slice in the same state a
        whole-file decode would be in -- which is what keeps errors="replace" landing on
        identical replacement characters.
        """
        text = blob.decode("utf-8", errors="replace")
        return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    @classmethod
    def _tail_records(cls, path: str, n: int) -> List[Dict[str, Any]]:
        """The last `n` well-formed records of one stream -- identical to
        `_read_stream(path)[-n:]`, reading O(tail) bytes instead of O(stream).

        PERF_AUDIT.md Q4: the per-step affect read (affect.py:_recent_settlements ->
        cognitive_loop.py:1849, twice per step) asked a 20-record question by parsing
        every record ever written -- 0.314 ms at 20 records, 262.250 ms at 40,000.

        Walks backwards in doubling blocks, discarding the first (partial) line of every
        block that does not start at byte 0 -- which is also what makes a block boundary
        landing mid-character harmless: those bytes are dropped, never decoded into the
        result. Counts RECORDS, not lines, because blank lines, corrupt lines and
        non-dict lines are all skipped by `_read_stream` and a line-counting reader would
        return short windows on exactly the crash-torn streams the live boxes carry.
        """
        if n <= 0 or not os.path.isfile(path):
            return []
        try:
            size = os.path.getsize(path)
        except OSError:
            return []
        if size <= 0:
            return []
        block = cls._TAIL_BLOCK
        with open(path, "rb") as fh:
            while True:
                start = max(0, size - block)
                fh.seek(start)
                blob = fh.read(size - start)
                if start > 0:
                    # drop through the first terminator: the bytes before it belong to a
                    # line this window cannot see whole (and may split a character).
                    nl = blob.find(b"\n")
                    cr = blob.find(b"\r")
                    if nl < 0 and cr < 0:        # no terminator in the window at all
                        block *= 2               # (a record longer than the block)
                        continue                 # start reaches 0 -> always terminates
                    if cr < 0 or 0 <= nl < cr:
                        cut = nl + 1
                    else:
                        cut = cr + (2 if blob[cr + 1:cr + 2] == b"\n" else 1)
                    blob = blob[cut:]
                # parse BACKWARDS and stop at n: seeking without this still pays a
                # json.loads for every record in the block, which is the actual cost.
                out: List[Dict[str, Any]] = []
                lines = cls._tail_lines(blob)
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i].strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue                 # crash mid-write: skipped, never fatal
                    if isinstance(rec, dict):
                        out.append(rec)
                        if len(out) >= n:
                            break
                out.reverse()
                if len(out) >= n or start == 0:
                    return out
                block *= 2

    @staticmethod
    def _ends_in_newline(path: str) -> bool:
        """True unless the file ends mid-line (a crash-truncated tail): the next
        append would MERGE with that tail and be lost with it -- the cache must
        account the same way a from-disk re-read would."""
        try:
            with open(path, "rb") as fh:
                fh.seek(-1, os.SEEK_END)
                return fh.read(1) == b"\n"
        except OSError:
            return True                      # missing or empty: nothing to merge with

    def _next_seq(self, scope: str, topic: str) -> int:
        """1 + max existing seq in the LOCAL stream (seeds are never appended to).
        Cached per stream after the first full read (a size stat replaces the
        re-read); the stream is re-read whenever its size stops matching this
        writer's own bookkeeping, or after reload_seqs()."""
        key = (scope, str(topic))
        path = self._stream_path(self.root, scope, topic)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        hit = self._seq_cache.get(key)
        if hit is not None and hit["size"] == size:
            return hit["seq"] + 1
        top = 0
        for rec in self._read_stream(path):
            try:
                top = max(top, int(rec.get("seq", 0)))
            except Exception:
                continue
        self._seq_cache[key] = {"seq": top, "size": size,
                                "clean": self._ends_in_newline(path)}
        return top + 1

    def reload_seqs(self) -> None:
        """Drop the per-stream seq cache: the next append re-reads from disk.
        The escape hatch for an out-of-band edit the size check cannot see."""
        self._seq_cache.clear()

    # ── the fabric: append / query ────────────────────────────────────────────

    def append(self, scope: str, topic: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Append one record to the LOCAL stream; adds monotonic "seq"; returns it
        enriched. SINGLE-WRITER INVARIANT: one process owns each stream's appends
        (own-scope appends only; seed mounts are read-only), so advancing the seq
        cache in memory below is safe across the swarm."""
        rec = dict(record)
        rec["seq"] = self._next_seq(scope, topic)
        path = self._stream_path(self.root, scope, topic)
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        key = (scope, str(topic))
        hit = self._seq_cache[key]           # _next_seq above ensured the entry
        if hit["clean"]:
            hit["seq"] = rec["seq"]          # advance in memory: no re-read next time
        # else: the record merged into a crash-truncated tail and is lost with it
        # (exactly what a re-reading _next_seq would conclude); our newline ended
        # the merged line, so the stream is clean again from here on.
        hit["clean"] = True
        try:
            hit["size"] = os.path.getsize(path)
        except OSError:
            del self._seq_cache[key]         # stat failed: force a re-read next time
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

    def query_tail(self, scope: str, topic: str, n: int) -> List[Dict[str, Any]]:
        """`query(scope, topic)[-n:]` WITHOUT reading `query(scope, topic)`.

        Byte-identical to the slice by contract (tests/gate/test_tail_read.py asserts it
        against a literal transcription of the pre-tail-read code), and O(tail) instead
        of O(stream): PERF_AUDIT.md Q4 measured the full read at 0.314 ms over 20 records
        and 262.250 ms over 40,000, on a call the loop makes twice per step.

        The window is the tail of the SAME concatenation `query` builds -- seed roots in
        order, then the local root -- so the roots are walked in REVERSE and only far
        enough back to fill n. Seeds are read-only overlays and are usually where the
        long history lives, so a tail read that stopped at the local root would be both
        wrong and, on a seeded box, not even the faster half.

        n <= 0 is not a fast path: `rows[-0:]` is the WHOLE list, and the point of this
        method is that no caller can tell it from the slice, so that case defers to the
        full read rather than quietly returning nothing.
        """
        if n <= 0:
            return self.query(scope, topic)[-n:]
        out: List[Dict[str, Any]] = []
        for base in reversed(list(self.seeds) + [self.root]):
            part = self._tail_records(self._stream_path(base, scope, topic),
                                      n - len(out))
            if part:
                out = part + out
            if len(out) >= n:
                break
        return out

    # ── the idea economy ──────────────────────────────────────────────────────

    def mint(self, idea: Dict[str, Any], game: str, signal: Any,
             scope: str = "personal", level: Optional[int] = None) -> str:
        """Mint an idea into ONE scope's "ideas" stream. Raises WITHOUT a signal --
        the wheel rule extends to memory: nothing is minted on silence.
        `level` (optional): the levels_completed value the reward produced --
        records missing it are treated as level 1 by `priors` (historically true)."""
        if not signal:
            raise ValueError("mint requires a signal -- no idea is minted on silence")
        seq = self._next_seq(scope, self.IDEAS_TOPIC)
        idea_id = "%s:%s:%s:%d" % (game, scope, self.agent_id, seq)
        rec = {
            "id": idea_id, "idea": idea, "game": game,
            "by": self.agent_id, "scope": scope, "signal": signal,
        }
        if level is not None:
            rec["level"] = int(level)
        self.append(scope, self.IDEAS_TOPIC, rec)
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

    def priors(self, game: str,
               level: Optional[int] = None) -> List[Dict[str, Any]]:
        """All visible ideas for `game` across collective + own personal + own kin,
        deduped by id; ranked pariahs LAST, then credibility desc, then nearer evidence
        (personal < kin < collective), then id asc. Deterministic.
        `level` (optional): keep only ideas whose reward was produced at that
        levels_completed value; records missing the field default to level 1
        (every historical mint was a level-1 win). level=None: no filter."""
        counts = self._event_counts()
        out: List[Dict[str, Any]] = []
        seen: set = set()
        for scope in ("personal", "kin", "collective"):
            for rec in self.query(scope, self.IDEAS_TOPIC):
                if rec.get("game") != game:
                    continue
                if (level is not None
                        and int(rec.get("level") or 1) != int(level)):
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
