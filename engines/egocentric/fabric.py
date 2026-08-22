"""fabric.py -- Phase 3a: the knowledge fabric + the idea economy (PREREG_PHASE3A.md §1).

Pure-stdlib JSONL streams under scoped directories -- no database, no wall-clock, no threads:

  * scopes: "collective" -> collective/, "personal" -> personal/<agent_id>/,
    "kin" -> kin/<kin_key>/; a stream is <scopedir>/<topic>.jsonl;
  * `append()` adds a monotonic per-stream "seq" read back from disk (reopen continues);
    the seq high-water mark is CACHED PER PROCESS, per stream path (PREREG_FABRIC_IO.md,
    TARGET SHARPENED BY WINDOW 6-b): seeded from the stream's LAST record on first
    touch (one tail read, never a whole-file parse), advanced in memory on every
    append, and re-seeded whenever the file stops matching this writer's bookkeeping
    -- size AND the last ANCHOR_BYTES before it (the same anchor rule the read cache
    uses; a janitor shrink, a same-size rewrite, any out-of-band byte) -- or after
    reload_seqs() (the escape hatch: a full oracle re-read). CROSS-PROCESS INVARIANT:
    each stream has a single WRITER process by design (own-scope appends only; seed
    mounts are read-only and never appended to), so the in-memory advance can never
    hand out a seq twice; and the process-level key is what keeps the loop's several
    KnowledgeFabric instances on one root from re-parsing the stream for each other;
  * `query()` serves each root's stream from a process-level PARSED-STREAM CACHE
    (PREREG_FABRIC_IO.md STAGE 1): terminated lines are parsed once and kept; every
    call re-validates by stat + anchor, tail-parses only the bytes appended since, and
    re-reads the unterminated remainder every time. Bounded (LRU by stream bytes,
    READ_CACHE_CAP_BYTES); returned records are SHALLOW copies; `READ_CACHE = False`
    routes `query` back to `_read_stream`, which is unchanged and remains the oracle;
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
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple


class KnowledgeFabric:
    """Scoped JSONL memory with a seed overlay and the mint/echo/falsify economy."""

    IDEAS_TOPIC = "ideas"
    EVENTS_TOPIC = "idea_events"
    _SCOPE_PREF = {"personal": 0, "kin": 1, "collective": 2}
    # THE UNDO (PREREG_FABRIC_IO.md): False routes `query` to `_read_stream`, the
    # uncached oracle, in one dispatch. Class-level so a test or an operator flips
    # every instance at once; the seq cache is not on this switch (it has its own
    # escape hatch, reload_seqs()).
    READ_CACHE = True

    def __init__(self, root: str, seeds: Optional[List[str]] = None,
                 agent_id: str = "agent", kin_key: str = "kin"):
        # creates NOTHING on disk until the first append; reads are lazy
        self.root = str(root)
        self.seeds = [str(s) for s in (seeds or [])]
        self.agent_id = str(agent_id)
        self.kin_key = str(kin_key)
        # No per-instance seq cache any more: the seq tail lives in the PROCESS-
        # level _SEQ_TAIL (module bottom), keyed by the stream's absolute path, so
        # the loop's several instances on one root (cognitive_loop.py builds one per
        # reachability seam and one per game) share a single high-water mark
        # instead of each re-parsing the stream on its first append.

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

    def _next_seq(self, scope: str, topic: str) -> int:
        """1 + the seq high-water mark of the LOCAL stream (seeds are never appended
        to). Served from the process-level seq tail while the stream still matches
        the bookkeeping (size AND anchor -- `_anchor_size`, the one validity rule);
        re-seeded from the stream's LAST record otherwise (`_seed_seq`: a tail read,
        never a whole-file parse), or by the full oracle scan once after
        reload_seqs()."""
        path = self._stream_path(self.root, scope, topic)
        key = os.path.abspath(path)
        hit = _SEQ_TAIL.get(key)
        if hit is not None and not hit.get("verify"):
            size = _anchor_size(path, hit["upto"], hit["anchor"])
            if size is not None and size == hit["upto"]:
                return hit["seq"] + 1
        hit = _seed_seq(path, full=bool(hit is not None and hit.get("verify")))
        _SEQ_TAIL[key] = hit
        return hit["seq"] + 1

    def reload_seqs(self) -> None:
        """The escape hatch for an edit the anchor rule cannot see (a rewrite that
        keeps the size AND the last ANCHOR_BYTES -- e.g. a seq edited mid-file):
        every stream touched so far is marked for ONE full oracle re-read (the
        pre-cache `_next_seq` computation, max seq over `_read_stream`) on its next
        append. Process-wide, like the cache it resets."""
        for hit in _SEQ_TAIL.values():
            hit["verify"] = True

    @staticmethod
    def drop_read_cache() -> None:
        """Drop the parsed-stream read cache (the reload_seqs pattern): the next
        `query` of every stream is a full read. Derived state only -- nothing is
        lost, nothing is written."""
        _READ_CACHE.clear()
        _READ_CACHE_BYTES[0] = 0

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
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
        key = os.path.abspath(path)
        hit = _SEQ_TAIL[key]                 # _next_seq above ensured the entry
        if hit["clean"]:
            hit["seq"] = rec["seq"]          # advance in memory: no re-read next time
        # else: the record merged into a crash-truncated tail and is lost with it
        # (exactly what a re-reading _next_seq would conclude); our newline ended
        # the merged line, so the stream is clean again from here on.
        hit["clean"] = True
        # Advance the bookkeeping IN MEMORY by the bytes text mode just put on disk
        # (newline=None translates the one "\n" to os.linesep; json.dumps escapes
        # every other control character, so nothing else is translated) -- then
        # hold the disk to it: a size that disagrees means bytes we did not write,
        # and the entry is dropped so the next append re-seeds from the tail.
        written = line.replace("\n", os.linesep).encode("utf-8")
        hit["anchor"] = (hit["anchor"] + written)[-ANCHOR_BYTES:]
        hit["upto"] += len(written)
        try:
            if os.path.getsize(path) != hit["upto"]:
                del _SEQ_TAIL[key]
        except OSError:
            del _SEQ_TAIL[key]               # stat failed: force a re-seed next time
        return rec

    def query(self, scope: str, topic: str,
              where: Optional[Callable[[Dict[str, Any]], Any]] = None,
              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Records in insertion order: seed roots FIRST, then the local root.

        Served from the parsed-stream cache (`_cached_stream`, module bottom) unless
        READ_CACHE is False; `where`/`limit` are applied exactly as before over the
        same concatenation. Cached records are handed out as SHALLOW copies (a
        consumer assigning a top-level key cannot poison the next read); values
        nested inside a record are shared with the cache and are READ-ONLY by
        contract -- every production consumer was audited for in-place nested
        mutation (tests/gate/test_fabric_read_cache.py, RIDER 2: 44 sites, 40
        read-only, 4 copy-before-write, 0 nested writes). The live aliases to
        keep that way: Gamma.get returns rec["atom"] itself (effects.py), and the
        composer's atom pool holds the same objects -- `dict(atom)` before any
        write, as mint._reinstate and consumer.seed_imports already do.
        """
        out: List[Dict[str, Any]] = []
        cached = bool(self.READ_CACHE)
        for base in list(self.seeds) + [self.root]:
            path = self._stream_path(base, scope, topic)
            for raw in (_cached_stream(path) if cached else self._read_stream(path)):
                rec = dict(raw) if cached else raw
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


# ═══ FABRIC I/O (PREREG_FABRIC_IO.md): the two process-level caches + THE ONE anchor rule ═══
#
# Module bottom by the placement law: nothing above moves. Both caches are DERIVED
# state keyed by the stream's absolute path -- they hold nothing the file does not,
# are never written back, and are dropped by reload_seqs() / drop_read_cache().

# THE ANCHOR (PINNED by the prereg, KNOBS G35): the last 64 bytes before the byte
# offset a cache has synced to. A cache never trusts a stat alone -- a rewrite of any
# length, including one that grew the file or landed inside stat granularity, changes
# these bytes; mtime is not part of the rule because its granularity varies by
# filesystem and an identical-size rewrite inside one tick would pass it.
ANCHOR_BYTES = 64

# RIDER 1 (KNOBS G35, GUESSED from observation): the read cache's bound, in STREAM
# BYTES represented (sum of every entry's parsed span). 32 MiB is the smallest power
# of two above the largest per-box working set of the per-cycle `query` topics
# observed read-only under .runs/swarm/*/ego_fabric on 2026-08-21 (25 boxes; atoms +
# mint_verdicts + goal_hypotheses + frontier_* + starvation/swallow/ideas/idea_events/
# replay_outcomes + import_candidates + settlements = 24.3 MiB max, sb26/tn36; atoms
# alone <= 6.5 MB, mint_verdicts <= 9.5 MB, settlements <= 14.4 MB). import_queue
# (0.4-73.6 MB, 15 boxes > 15 MB) is deliberately NOT covered on the large boxes: a
# stream larger than the cap is served uncached (parsed as today, never retained).
# Held memory per stream byte measured 3.5x-6.5x (tracemalloc over _read_stream on
# real streams), so the cap's RSS ceiling is ~110-210 MB -- a PLATEAU, not growth
# (record/findings/MEMORY_PROFILE_L0.md: the kill suspects grow by retained state).
READ_CACHE_CAP_BYTES = 32 * 1024 * 1024

# seq tail: abspath -> {"seq": high-water mark, "upto": size at last sync, "anchor":
# the last ANCHOR_BYTES before upto, "clean": the file ends in a newline, "verify":
# reload_seqs() asked for one full oracle scan}
_SEQ_TAIL: Dict[str, Dict[str, Any]] = {}

# read cache: abspath -> {"records": parsed dicts of every TERMINATED line, in file
# order; "upto": byte offset just past the last terminator (never mid-line);
# "anchor": the last ANCHOR_BYTES before upto}. OrderedDict = LRU order; the
# unterminated remainder is NEVER here (parsed and returned, re-read next call).
_READ_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_READ_CACHE_BYTES = [0]                      # sum of "upto" over the entries

# The instrument the gates count by (never wall-clock): full = path-3 whole-stream
# decodes, tail = path-2 decodes of appended bytes, hit = nothing new on disk,
# bytes = bytes decoded, evict = LRU evictions, uncached = streams over the cap.
READ_STATS: Dict[str, int] = {"full": 0, "tail": 0, "hit": 0, "bytes": 0,
                              "evict": 0, "uncached": 0}


def _anchor_size(path: str, upto: int, anchor: bytes) -> Optional[int]:
    """THE ONE VALIDITY RULE, shared by both caches: the stream's current size, or
    None if the file is shorter than `upto` or the ANCHOR_BYTES at
    [upto - len(anchor), upto) are not `anchor` (one stat, one open, one seek, one
    short read). The seq cache additionally requires size == upto (any growth is
    foreign bytes); the read cache accepts size >= upto (growth is an append)."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    if size < upto:
        return None
    if anchor:
        try:
            with open(path, "rb") as fh:
                fh.seek(upto - len(anchor))
                if fh.read(len(anchor)) != anchor:
                    return None
        except OSError:
            return None
    return size


def _anchor_bytes(path: str, upto: int) -> bytes:
    """The last ANCHOR_BYTES before `upto` (fewer if the file is shorter)."""
    n = min(ANCHOR_BYTES, max(0, upto))
    if n <= 0:
        return b""
    try:
        with open(path, "rb") as fh:
            fh.seek(upto - n)
            return fh.read(n)
    except OSError:
        return b""


def _seed_seq(path: str, full: bool = False) -> Dict[str, Any]:
    """A fresh seq-tail entry for `path`. Default: the LAST well-formed record's seq
    via `_tail_records` (O(tail)). The full oracle scan (max seq over
    `_read_stream`, the pre-cache computation) runs only when asked (reload_seqs)
    or when the tail cannot answer -- no record, or a last record whose "seq" is
    missing/unparseable, where the oracle's answer lives in earlier records."""
    top = 0
    seeded = False
    if not full and os.path.isfile(path):
        tail = KnowledgeFabric._tail_records(path, 1)
        if tail and "seq" in tail[-1]:
            try:
                top = max(0, int(tail[-1].get("seq", 0)))
                seeded = True
            except Exception:
                seeded = False
    elif not full:
        seeded = True                        # missing: nothing to read, top = 0
    if not seeded:
        for rec in KnowledgeFabric._read_stream(path):
            try:
                top = max(top, int(rec.get("seq", 0)))
            except Exception:
                continue
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    anchor = _anchor_bytes(path, size)
    # "clean" = the file ends in a newline: the next append would otherwise MERGE
    # with a crash-truncated tail and be lost with it. Missing or empty: nothing
    # to merge with. Read off the anchor -- it already holds the last byte.
    clean = (anchor[-1:] == b"\n") if anchor else True
    return {"seq": top, "upto": size, "anchor": anchor, "clean": clean}


def _parse_lines(blob: bytes) -> List[Dict[str, Any]]:
    """`_read_stream`'s exact rules over a byte range that starts at a line
    boundary: `_tail_lines` splitting (universal newlines, the same decoder state
    as a whole-file decode), strip, skip blank / corrupt / non-dict."""
    out: List[Dict[str, Any]] = []
    for raw in KnowledgeFabric._tail_lines(blob):
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue                         # crash mid-write: skipped, never fatal
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _terminated_upto(blob: bytes) -> int:
    """The byte offset just past the last universal-newline terminator in `blob`
    (0 if none). A LONE "\\r" as the very last byte is NOT committed: its "\\n" may
    not have landed, so it stays in the volatile remainder and is re-read whole."""
    end = len(blob)
    if blob.endswith(b"\r"):
        end -= 1
    return max(blob.rfind(b"\n", 0, end), blob.rfind(b"\r", 0, end)) + 1


def _read_cache_evict(key: str) -> None:
    ent = _READ_CACHE.pop(key, None)
    if ent is not None:
        _READ_CACHE_BYTES[0] -= ent["upto"]
        READ_STATS["evict"] += 1


def _read_cache_trim() -> None:
    """LRU by bytes: drop least-recently-served entries until the represented
    bytes fit the cap (an entry that has grown past the cap on its own goes too)."""
    while _READ_CACHE and _READ_CACHE_BYTES[0] > READ_CACHE_CAP_BYTES:
        _read_cache_evict(next(iter(_READ_CACHE)))


def _cached_stream(path: str) -> List[Dict[str, Any]]:
    """The records of one stream file, byte-identical to `_read_stream(path)`, from
    the parsed-stream cache. Every call: stat -> exactly one of
      1. MISSING  -> drop the entry, return [];
      2. VALID    -> decode ONLY the bytes appended since (terminated lines are
                     cached; the unterminated remainder is returned, never cached);
      3. INVALID  -> full read from byte 0 through the same decoder, entry re-seeded.
    Records come back UNCOPIED -- `query` makes the shallow copies."""
    key = os.path.abspath(path)
    ent = _READ_CACHE.get(key)
    if not os.path.isfile(path):
        if ent is not None:
            _read_cache_evict(key)
        return []
    if ent is not None:
        size = _anchor_size(path, ent["upto"], ent["anchor"])
        if size is not None:
            blob: Optional[bytes]
            try:
                with open(path, "rb") as fh:
                    fh.seek(ent["upto"])
                    blob = fh.read(size - ent["upto"])
            except OSError:
                blob = None
            # a short read = the file shrank between the stat and this read
            if blob is not None and len(blob) == size - ent["upto"]:
                _READ_CACHE.move_to_end(key)
                if not blob:
                    READ_STATS["hit"] += 1
                    return ent["records"]
                READ_STATS["tail"] += 1
                READ_STATS["bytes"] += len(blob)
                cut = _terminated_upto(blob)
                if cut:
                    done = blob[:cut]
                    ent["records"].extend(_parse_lines(done))
                    ent["anchor"] = (ent["anchor"] + done)[-ANCHOR_BYTES:]
                    ent["upto"] += cut
                    _READ_CACHE_BYTES[0] += cut
                    _read_cache_trim()
                if cut < len(blob):
                    return ent["records"] + _parse_lines(blob[cut:])
                return ent["records"]
        _read_cache_evict(key)
    # path 3: the whole stream, once, through the decoder `_read_stream` would
    # have used line by line (the tail-read gate proved them identical)
    READ_STATS["full"] += 1
    try:
        with open(path, "rb") as fh:
            blob = fh.read()
    except OSError:
        return []
    READ_STATS["bytes"] += len(blob)
    cut = _terminated_upto(blob)
    records = _parse_lines(blob[:cut])
    if cut <= READ_CACHE_CAP_BYTES:
        _READ_CACHE[key] = {"records": records, "upto": cut,
                            "anchor": blob[max(0, cut - ANCHOR_BYTES):cut]}
        _READ_CACHE_BYTES[0] += cut
        _read_cache_trim()
    else:
        READ_STATS["uncached"] += 1
    if cut < len(blob):
        return records + _parse_lines(blob[cut:])
    return records
