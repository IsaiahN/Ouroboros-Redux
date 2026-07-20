#!/usr/bin/env python3
"""Snapshot discipline for the Ouroboros dev copy.

Why this exists: mid-session the dev copy silently reverted and several edits vanished. Nothing errored -- the code
still parsed and still ran, so the A/Bs kept producing numbers, but they were numbers for code that no longer existed.
A measurement you cannot tie to a known file state is not a measurement. This makes drift loud and cheap to detect.

    python3 ouro_snap.py snap  [label]   # record the current state (content-hash manifest + a copy of every file)
    python3 ouro_snap.py verify          # compare live tree vs the latest snapshot; exit 1 on ANY drift
    python3 ouro_snap.py list            # show snapshots
    python3 ouro_snap.py restore <label> # put a snapshot's files back into the dev copy

Snapshots go to a DURABLE location (/mnt/user-data/outputs/_ouro_snapshots), because the thing that reverted was /tmp.
Code only -- no game data, no keys, nothing about any specific game's mechanics.
"""
import hashlib
import json
import os
import shutil
import sys
import time

SRC = "/tmp/verify_cpu/ouroboros_cpu"
SNAPROOT = "/mnt/user-data/outputs/_ouro_snapshots"


def _files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for fn in filenames:
            if fn.endswith(".py"):
                p = os.path.join(dirpath, fn)
                out.append(os.path.relpath(p, root))
    return sorted(out)


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest(root):
    return {rel: _md5(os.path.join(root, rel)) for rel in _files(root)}


def snap(label=None):
    label = label or time.strftime("%H%M%S")
    dest = os.path.join(SNAPROOT, label)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest, exist_ok=True)
    man = _manifest(SRC)
    for rel in man:
        d = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(SRC, rel), d)
    meta = {"label": label, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "src": SRC, "files": man}
    with open(os.path.join(SNAPROOT, "latest.json"), "w") as f:
        json.dump(meta, f, indent=1)
    with open(os.path.join(dest, "manifest.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("snapshot '%s': %d files -> %s" % (label, len(man), dest))
    return meta


def verify(quiet=False):
    lp = os.path.join(SNAPROOT, "latest.json")
    if not os.path.exists(lp):
        print("no snapshot yet -- run: ouro_snap.py snap"); return 2
    meta = json.load(open(lp))
    old, new = meta["files"], _manifest(SRC)
    changed = [f for f in old if f in new and old[f] != new[f]]
    gone = [f for f in old if f not in new]
    added = [f for f in new if f not in old]
    if not (changed or gone or added):
        if not quiet:
            print("OK: live tree identical to snapshot '%s' (%s)" % (meta["label"], meta["when"]))
        return 0
    print("DRIFT vs snapshot '%s' (%s):" % (meta["label"], meta["when"]))
    for f in changed:
        print("   CHANGED  %s" % f)
    for f in gone:
        print("   MISSING  %s   <-- file disappeared" % f)
    for f in added:
        print("   NEW      %s" % f)
    return 1


def restore(label):
    src = os.path.join(SNAPROOT, label)
    if not os.path.isdir(src):
        print("no such snapshot: %s" % label); return 2
    n = 0
    for rel in _files(src):
        if rel == "manifest.json":
            continue
        d = os.path.join(SRC, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(src, rel), d); n += 1
    print("restored %d files from '%s' -> %s" % (n, label, SRC))
    return 0


def lst():
    if not os.path.isdir(SNAPROOT):
        print("(none)"); return 0
    for d in sorted(os.listdir(SNAPROOT)):
        p = os.path.join(SNAPROOT, d, "manifest.json")
        if os.path.exists(p):
            m = json.load(open(p))
            print("  %-14s %s  (%d files)" % (m["label"], m["when"], len(m["files"])))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    sys.exit({"snap": lambda: (snap(arg), 0)[1], "verify": verify,
              "list": lst, "restore": lambda: restore(arg)}.get(cmd, verify)())
