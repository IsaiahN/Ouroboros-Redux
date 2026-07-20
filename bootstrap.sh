#!/usr/bin/env bash
# bootstrap.sh -- prepare an ephemeral runner (GitHub Actions or any fresh box) to run the Redux agent.
# Installs only what the agent actually imports: the ARC-AGI-3 SDK + numpy/scipy. Idempotent.
# NEVER touches the API key -- that is injected as an env var by the caller (an Actions secret), never here.
set -euo pipefail

echo "== bootstrap: python =="
python3 --version
python3 -m pip install --upgrade pip >/dev/null

echo "== bootstrap: deps =="
# The agent imports: arc_agi, arcengine (both from the ARC SDK), numpy, scipy. arc-agi-3 is the SDK
# metapackage. --break-system-packages is harmless on a clean CI runner and needed on Debian-style images.
python3 -m pip install --break-system-packages \
    arc-agi \
    arcengine \
    arc-agi-3 \
    numpy \
    scipy

echo "== bootstrap: verify imports =="
python3 - <<'PY'
import importlib
for m in ("arc_agi", "arcengine", "numpy", "scipy"):
    importlib.import_module(m)
    print("  ok:", m)
print("bootstrap: all core imports resolved")
PY

echo "== bootstrap: done =="
