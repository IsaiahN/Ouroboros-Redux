"""W4 B19: the cold-ship smoke — the Kaggle parity check (CK_LEDGER, THE SHIP-CLEAN LAW).

Runs the agent's knowledge substrate the way Kaggle will run it: a BARE interpreter
(stdlib + numpy, no dev deps), no network, a read-only seed mount. Two modes:

  * venv mode (default): creates (or reuses) .runs/cold_venv with ONLY numpy installed
    (pip install numpy --no-deps), then runs the smoke inside it — the real thing.
  * --inline fallback: runs the smoke under the CURRENT interpreter with a meta-path
    import blocker that refuses every module that is not stdlib, numpy, or a repo-local
    module — bare-ness enforced by construction when venv creation is slow/offline.
    venv-mode setup failures fall back to inline AUTOMATICALLY (loudly).

THE SMOKE (same script both modes):
  1. kills the network FIRST (socket.socket/create_connection/getaddrinfo raise);
  2. BARE imports every engines.egocentric module and records the truth per module;
  3. re-imports under a scipy SHIM (the one pinned ship-clean debt, simulated fixed)
     so the rest of the surface is still exercised while the debt stands;
  4. synthetic cycle: KnowledgeFabric against a temp dir + tests/gate/fixtures/old_books
     as read-only seed (query old atoms, append/query roundtrip), one
     learn_effect/apply_effect cycle, Gamma add/get/apply;
  5. asserts the network kill actually holds.

VERDICT (ratchet semantics, same as tests/gate/test_ship_clean.py): failures whose root
is the PINNED scipy debt are tolerated and loudly reported ("PASS-WITH-PINNED-DEBT" —
explicitly NOT Kaggle parity until the debt clears); any other failure = FAIL, exit 1.
Stdlib only; dev-time tool, never imported by agents.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_DIR = os.path.join(REPO, ".runs", "cold_venv")
FIXTURES = os.path.join(REPO, "tests", "gate", "fixtures", "old_books")

SMOKE = r'''
import importlib, json, os, sys, tempfile, traceback, types

REPO = os.environ["COLD_SHIP_REPO"]
FIXTURES = os.environ["COLD_SHIP_FIXTURES"]
MODE = os.environ.get("COLD_SHIP_MODE", "venv")
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# ── 1. the network dies first ─────────────────────────────────────────────────
import socket
def _no_net(*a, **k):
    raise RuntimeError("cold-ship: network access attempted")
socket.socket = _no_net
socket.create_connection = _no_net
socket.getaddrinfo = _no_net

# ── inline mode: bare-ness by import blocker ─────────────────────────────────
if MODE == "inline":
    import importlib.abc
    _local = set()
    for _n in os.listdir(REPO):
        if _n.endswith(".py"):
            _local.add(_n[:-3])
        elif os.path.isdir(os.path.join(REPO, _n)) and not _n.startswith("."):
            _local.add(_n)
    _allowed = set(sys.stdlib_module_names) | _local | {"numpy"}
    class _Blocker(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            top = name.split(".")[0]
            if top not in _allowed and top not in sys.modules:
                raise ImportError("cold-ship blocked non-bare module: %s" % name)
            return None
    sys.meta_path.insert(0, _Blocker())

results = []           # (phase, name, ok, note)
def rec(phase, name, ok, note=""):
    results.append((phase, name, ok, note))
    print("  %s %-4s %-38s %s" % ("OK " if ok else "FAIL", phase, name, note), flush=True)

EGO = os.path.join(REPO, "engines", "egocentric")
MODULES = ["engines.egocentric"] + sorted(
    "engines.egocentric." + f[:-3] for f in os.listdir(EGO)
    if f.endswith(".py") and f != "__init__.py")

def import_sweep(phase):
    for m in MODULES:
        for k in [k for k in list(sys.modules) if k == m or k.startswith("engines")]:
            sys.modules.pop(k, None)
        try:
            importlib.import_module(m)
            rec(phase, m, True)
        except Exception as e:
            rec(phase, m, False, "%s: %s" % (type(e).__name__, e))

print("cold-ship smoke (mode=%s, python=%s)" % (MODE, sys.version.split()[0]), flush=True)

# ── 2. the bare truth ─────────────────────────────────────────────────────────
print("phase BARE: import every engines.egocentric module, nothing shimmed", flush=True)
import_sweep("BARE")

# ── 3. the same surface with the one pinned debt simulated fixed ──────────────
print("phase SHIM: scipy shimmed (the pinned ship-clean debt), sweep repeated", flush=True)
_scipy = types.ModuleType("scipy")
_ndimage = types.ModuleType("scipy.ndimage")
def _debt(*a, **k):
    raise RuntimeError("cold-ship shim: scipy.ndimage called at runtime (pinned debt)")
for _fn in ("label", "sum", "generate_binary_structure", "find_objects"):
    setattr(_ndimage, _fn, _debt)
_scipy.ndimage = _ndimage
sys.modules["scipy"] = _scipy
sys.modules["scipy.ndimage"] = _ndimage
import_sweep("SHIM")

# ── 4. the synthetic cycle over a seed-mounted fabric ─────────────────────────
print("phase CYCLE: fabric seed-mount + learn/apply + append/query", flush=True)
try:
    import numpy as np
    from engines.egocentric.fabric import KnowledgeFabric
    from engines.egocentric.effects import Gamma, learn_effect, apply_effect

    tmp = tempfile.mkdtemp(prefix="cold_ship_")
    fab = KnowledgeFabric(os.path.join(tmp, "live"), seeds=[FIXTURES],
                          agent_id="cold_agent", kin_key="cold_kin")
    old_atoms = fab.query("collective", "atoms")
    rec("CYCLE", "seed-mount query old atoms", len(old_atoms) >= 3,
        "%d atoms through the read-only seed" % len(old_atoms))

    put = fab.append("collective", "settlements",
                     {"agent": "cold_agent", "game": "coldgame", "level": 0,
                      "action": 1, "members": 1, "best": 0.0, "nontrivial": False})
    back = fab.query("collective", "settlements",
                     where=lambda r: r.get("agent") == "cold_agent")
    rec("CYCLE", "fabric append/query roundtrip",
        bool(back) and back[-1]["seq"] == put["seq"])

    before = np.zeros((5, 5), dtype=int)
    before[1:3, 1:3] = np.array([[1, 2], [3, 4]])   # distinctive context: unique match
    after = before.copy()
    after[1:3, 1:3] = np.array([[5, 6], [7, 8]])
    atom = learn_effect(before, 6, after)
    replay = apply_effect(atom, before)
    rec("CYCLE", "learn_effect/apply_effect cycle",
        atom is not None and atom.get("kind") == "EFFECT"
        and replay is not None and (replay == after).all())

    g = Gamma(fab)
    aid = g.add(atom, "coldgame", 0)
    out = g.apply(aid, before)
    rec("CYCLE", "Gamma add/get/apply", out is not None and (out == after).all())
except Exception as e:
    traceback.print_exc()
    rec("CYCLE", "synthetic cycle", False, "%s: %s" % (type(e).__name__, e))

# ── 5. the network kill holds ─────────────────────────────────────────────────
try:
    socket.socket()
    rec("NET", "socket blocked", False, "socket.socket() succeeded")
except RuntimeError:
    rec("NET", "socket blocked", True)

# ── verdict: ratchet semantics ────────────────────────────────────────────────
bad = [(p, n, note) for p, n, ok, note in results if not ok]
debt = [(p, n, note) for p, n, note in bad if "scipy" in note]
hard = [(p, n, note) for p, n, note in bad if "scipy" not in note]
print("summary: %d checks, %d failed (%d pinned-scipy-debt, %d hard)"
      % (len(results), len(bad), len(debt), len(hard)), flush=True)
if hard:
    print("COLD-SHIP: FAIL — failures beyond the pinned scipy debt:")
    for p, n, note in hard:
        print("  %s %s %s" % (p, n, note))
    sys.exit(1)
if debt:
    print("COLD-SHIP: PASS-WITH-PINNED-DEBT — every failure roots in the pinned scipy "
          "debt (engines/egocentric/agency.py, perception.py, via the package __init__ "
          "chain). NOT Kaggle parity until scipy is guarded or vendored.")
    sys.exit(0)
print("COLD-SHIP: PASS — bare venv, no network, seed-mounted fabric, full cycle")
sys.exit(0)
'''


def _venv_python(venv_dir):
    return os.path.join(venv_dir, "Scripts" if os.name == "nt" else "bin",
                        "python.exe" if os.name == "nt" else "python")


def _ensure_venv(venv_dir):
    """Create (or reuse) the bare venv with ONLY numpy. Returns its python or None."""
    py = _venv_python(venv_dir)
    if os.path.isfile(py):
        chk = subprocess.run([py, "-c", "import numpy"], capture_output=True,
                             text=True, timeout=120, check=False)
        if chk.returncode == 0:
            print("cold venv reused: %s" % venv_dir, flush=True)
            return py
        print("cold venv exists but numpy import fails; reinstalling numpy")
    else:
        print("creating bare venv at %s" % venv_dir, flush=True)
        mk = subprocess.run([sys.executable, "-m", "venv", venv_dir],
                            capture_output=True, text=True, timeout=300, check=False)
        if mk.returncode != 0 or not os.path.isfile(py):
            print("venv creation FAILED:\n%s%s" % (mk.stdout, mk.stderr))
            return None
    pip = subprocess.run([py, "-m", "pip", "install", "numpy", "--no-deps", "--quiet"],
                         capture_output=True, text=True, timeout=420, check=False)
    if pip.returncode != 0:
        print("pip install numpy FAILED (offline box?):\n%s%s" % (pip.stdout, pip.stderr))
        return None
    return py


def run_smoke(python, mode):
    with tempfile.TemporaryDirectory(prefix="cold_ship_launch_") as td:
        script = os.path.join(td, "cold_smoke.py")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(SMOKE)
        env = dict(os.environ)
        env["COLD_SHIP_REPO"] = REPO
        env["COLD_SHIP_FIXTURES"] = FIXTURES
        env["COLD_SHIP_MODE"] = mode
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env.pop("PYTHONPATH", None)
        proc = subprocess.run([python, "-u", script], cwd=td, env=env,
                              timeout=600, check=False)
        return proc.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description="cold-ship smoke: the Kaggle parity check")
    ap.add_argument("--inline", action="store_true",
                    help="skip the venv; enforce bare-ness with an import blocker")
    ap.add_argument("--venv-dir", default=VENV_DIR)
    args = ap.parse_args(argv)

    if not os.path.isdir(FIXTURES):
        print("B17 fixture pack missing at %s — build it first" % FIXTURES)
        return 2

    if not args.inline:
        py = _ensure_venv(args.venv_dir)
        if py is not None:
            print("mode: venv (%s)" % py, flush=True)
            return run_smoke(py, "venv")
        print("FALLBACK: venv unavailable -> inline mode (import blocker)")
    print("mode: inline (%s)" % sys.executable, flush=True)
    return run_smoke(sys.executable, "inline")


if __name__ == "__main__":
    sys.exit(main())
