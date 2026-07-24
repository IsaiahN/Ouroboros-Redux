"""sdk_guard.py -- fail LOUD, with an actionable message, when the online ARC-AGI-3 SDK is not the package
imported as `arc_agi`.

Why this exists: the PyPI name `arc_agi` is overloaded. The ONLINE game SDK (`arc_agi.Arcade`,
`OperationMode.ONLINE`, scorecards) is what the live stack needs; a DIFFERENT package publishes the same import
name as a STATIC ARC-1/ARC-2 dataset library (`Grid`, `Task`, `Dataset`, no `Arcade`). On a fresh container the
default interpreter can silently resolve to the static one -- e.g. python3.11 gets `arc-agi==0.0.7` (static) while
python3.12/3.13 carry the online SDK. A run under the wrong interpreter does not fabricate anything (it ImportErrors),
but the message is opaque. This guard turns that into a precise instruction, and gives the swarm/diagnostic
entrypoints a single call to assert the world is sane before touching the wire.

Domain-general, names no game: it only checks the SDK surface the live loop depends on.
"""
from __future__ import annotations
import sys


def online_sdk_present() -> bool:
    """True iff `arc_agi` is the ONLINE game SDK (has Arcade + OperationMode.ONLINE)."""
    try:
        import arc_agi
    except Exception:
        return False
    if not hasattr(arc_agi, "Arcade"):
        return False
    try:
        try:
            from arc_agi.base import OperationMode
        except Exception:
            from arc_agi import OperationMode
        return hasattr(OperationMode, "ONLINE")
    except Exception:
        return False


def assert_online_sdk() -> None:
    """Raise a clear, actionable RuntimeError if the online SDK is not importable under this interpreter."""
    if online_sdk_present():
        return
    py = "%d.%d.%d" % sys.version_info[:3]
    installed = "unknown"
    try:
        import arc_agi
        surface = [n for n in ("Arcade", "Grid", "Task", "Dataset") if hasattr(arc_agi, n)]
        installed = "arc_agi present but surface=%s (static dataset lib, NOT the online SDK)" % surface
    except Exception as e:  # pragma: no cover - arc_agi missing entirely
        installed = "arc_agi not importable (%r)" % e
    raise RuntimeError(
        "Online ARC-AGI-3 SDK (arc_agi.Arcade + OperationMode.ONLINE) is NOT available under python %s.\n"
        "  Found: %s.\n"
        "  Fix: run the live stack under an interpreter that carries the online SDK (python3.12 / python3.13 on "
        "this container), NOT the default python3 if it resolved to the static arc-agi dataset package.\n"
        "  The live stack fails loud here on purpose -- it will not fabricate results against the wrong SDK."
        % (py, installed)
    )
