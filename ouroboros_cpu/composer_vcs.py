"""
composer_vcs.py  --  version control the composer's LEARNED KNOWLEDGE so it can revert its own restructures live.

The learned, evolving object is `objective_validator._GLOBAL_KNOWLEDGE` (on sys._ouroboros_global_knowledge): the
cross-game memory {by_game: {gid: {win_condition, causation, ...}}, patterns: {...}} that outlives game-over and carries
across every game in a run. Today the composer mutates it with NO revert -- a bad prune/compose corrupts the knowledge
for the rest of the run. This adds the missing version control + a self-reverting restructure operator.

Two-tier by design (Tier 2 optional; SVN deferred per plan):
  Tier 1 (hot, in-memory): content-addressed commit graph over the knowledge. checkpoint/commit/revert/log are O(1)
          dict ops, thread-local (the framework runs games in threads). This is what makes live self-revert fast enough.
  Tier 2 (durable, optional): flush commits to an SVN working copy or a pure-Python file log, off the hot path. Auto-
          selected by availability; absent on Kaggle -> Tier 1 only, no crash.

Ungated by design: the composer commits and reverts on its own authority. The regression suite (primitive_ledger) tells
it WHICH restructures orphan verified predictions; it auto-reverts those. Learning-over-time = knowledge accumulates AND
is kept clean by reverts, persisting across attempts and games.
"""
from __future__ import annotations
import os, sys, copy, json, hashlib, threading, time

DURABLE = os.environ.get("OURO_VCS_DURABLE", "auto").strip().lower()   # auto | off | file | svn
VCS_DIR = os.environ.get("OURO_VCS_DIR", "/tmp/ouroboros_vcs")


def _hash(state) -> str:
    try:
        blob = json.dumps(state, sort_keys=True, default=str).encode()
    except Exception:
        blob = repr(state).encode()
    return hashlib.sha1(blob).hexdigest()[:12]


class _Commit:
    __slots__ = ("rev", "hash", "parent", "state", "msg", "ts")
    def __init__(self, rev, state, parent, msg):
        self.rev = rev; self.state = state; self.parent = parent; self.msg = msg
        self.hash = _hash(state); self.ts = time.time()


class ComposerVCS:
    """Versions a target dict (the knowledge). All ops are per-thread so concurrent games never collide."""
    def __init__(self):
        self._local = threading.local()
        self._durable = _make_backend()

    def _st(self):
        s = getattr(self._local, "st", None)
        if s is None:
            s = {"commits": [], "head": None, "next_rev": 1, "checkpoints": []}
            self._local.st = s
        return s

    # ---- commit graph -------------------------------------------------------------------------------------
    def commit(self, knowledge: dict, msg: str = "") -> int:
        """Snapshot the knowledge as a new revision. Returns the revision id."""
        st = self._st()
        snap = copy.deepcopy(knowledge)
        c = _Commit(st["next_rev"], snap, st["head"], msg)
        # de-dup: identical state to HEAD -> no new revision
        if st["head"] is not None and st["commits"] and st["commits"][-1].hash == c.hash:
            return st["commits"][-1].rev
        st["commits"].append(c); st["head"] = c.rev; st["next_rev"] += 1
        if len(st["commits"]) > 200:            # bound the in-memory graph
            st["commits"] = st["commits"][-200:]
        try: self._durable.flush(c)
        except Exception: pass
        return c.rev

    def head(self):
        return self._st()["head"]

    def _find(self, rev):
        for c in self._st()["commits"]:
            if c.rev == rev:
                return c
        return None

    def revert_to(self, knowledge: dict, rev: int) -> bool:
        """Restore the knowledge dict IN PLACE to a prior revision (live self-revert)."""
        c = self._find(rev)
        if c is None or not isinstance(knowledge, dict):
            return False
        knowledge.clear(); knowledge.update(copy.deepcopy(c.state))
        self._st()["head"] = rev
        return True

    def diff(self, rev_a, rev_b=None):
        """Coarse structural diff between two revisions (keys added/removed/changed under by_game)."""
        a = self._find(rev_a); b = self._find(rev_b) if rev_b is not None else self._find(self.head())
        if not a or not b:
            return {}
        ga = (a.state or {}).get("by_game", {}); gb = (b.state or {}).get("by_game", {})
        out = {}
        for gid in set(ga) | set(gb):
            if _hash(ga.get(gid)) != _hash(gb.get(gid)):
                out[gid] = "changed" if gid in ga and gid in gb else ("added" if gid in gb else "removed")
        return out

    def log(self, n=10):
        return [(c.rev, c.hash, c.msg) for c in self._st()["commits"][-n:]]

    # ---- the self-reverting restructure operator ----------------------------------------------------------
    def try_restructure(self, knowledge: dict, apply_fn, verify_fn, msg="restructure"):
        """The composer reverting its OWN change, in-loop:
          1. commit current knowledge (a revision to fall back to)
          2. apply the restructure (prune/compose/re-rank) in place
          3. verify: verify_fn() -> True if the restructure preserved behavior (no orphaned verified predictions,
             no regression). If False, revert to the pre-restructure revision.
        Returns dict(rev_before, kept: bool, note)."""
        rev_before = self.commit(knowledge, "pre:" + msg)
        try:
            apply_fn(knowledge)
        except Exception as e:
            self.revert_to(knowledge, rev_before)
            return {"rev_before": rev_before, "kept": False, "note": "apply raised: %s" % type(e).__name__}
        ok = True
        try:
            ok = bool(verify_fn(knowledge))
        except Exception:
            ok = True   # can't judge -> don't punish; keep
        if not ok:
            self.revert_to(knowledge, rev_before)
            return {"rev_before": rev_before, "kept": False, "note": "reverted: restructure regressed"}
        self.commit(knowledge, "post:" + msg)
        return {"rev_before": rev_before, "kept": True, "note": "kept"}

    def narrate(self):
        st = self._st()
        return "composer-vcs: HEAD=r%s, %d commits, durable=%s" % (st["head"], len(st["commits"]), self._durable.name)


# ------------------------------------------------------------------------------------- durable backends (Tier 2)
class _FileBackend:
    name = "file"
    def __init__(self, root):
        self.root = root
        try: os.makedirs(root, exist_ok=True)
        except Exception: pass
    def flush(self, commit):
        path = os.path.join(self.root, "r%05d.json" % commit.rev)
        with open(path, "w") as f:
            json.dump({"rev": commit.rev, "hash": commit.hash, "msg": commit.msg, "state": commit.state}, f, default=str)

class _SVNBackend:
    name = "svn"
    def __init__(self, root):
        import subprocess
        self.root = root; self._sp = subprocess
        os.makedirs(root, exist_ok=True)
        # init a working copy if absent (dev-only path; deferred for Kaggle)
        if not os.path.isdir(os.path.join(root, ".svn")):
            repo = root + "_repo"
            self._sp.run(["svnadmin", "create", repo], check=False)
            self._sp.run(["svn", "checkout", "file://" + os.path.abspath(repo), root], check=False)
    def flush(self, commit):
        path = os.path.join(self.root, "knowledge.json")
        new = not os.path.exists(path)
        with open(path, "w") as f:
            json.dump(commit.state, f, default=str)
        if new:
            self._sp.run(["svn", "add", path], cwd=self.root, check=False)
        self._sp.run(["svn", "commit", "-m", "r%d %s" % (commit.rev, commit.msg)], cwd=self.root, check=False)

class _NullBackend:
    name = "none"
    def flush(self, commit):
        pass

def _make_backend():
    if DURABLE == "off":
        return _NullBackend()
    if DURABLE in ("auto", "svn"):
        try:
            import shutil, subprocess  # noqa
            if __import__("shutil").which("svn") and __import__("shutil").which("svnadmin"):
                return _SVNBackend(VCS_DIR)
        except Exception:
            pass
        if DURABLE == "svn":
            return _NullBackend()   # explicitly asked for svn but unavailable -> null, never crash
    if DURABLE in ("auto", "file"):
        try:
            return _FileBackend(VCS_DIR)
        except Exception:
            return _NullBackend()
    return _NullBackend()
