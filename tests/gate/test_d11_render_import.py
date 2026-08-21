"""D-11 GATE: THE TOOLKIT'S VISUALISER NEVER LOADS IN A HEADLESS WORKER.

The defect (D-11, 2026-08-21): `python -X importtime -c "import evolution_runner"`
showed matplotlib (plus fontTools via matplotlib.dviread) imported first by
arc_agi.rendering -- the toolkit's visualiser, which no headless worker ever
calls -- at seconds of import and ~40MB RSS per process, x25 workers per fleet
restart.

The chain, as found in the installed package: arc_agi/__init__ -> arc_agi.base
(the module that defines Arcade) -> `from .rendering import render_frames,
render_frames_terminal` (base.py:21, eager) -> matplotlib at the top of
rendering.py. So no narrower import of the toolkit avoids it, and the package
honours no environment variable that would.

The build under test: arc_api_adapter.install_headless_render_guard(), run at
the adapter's import BEFORE its first `arc_agi` statement. With OURO_HEADLESS
"1"/"true" (any case) it pre-seeds sys.modules["arc_agi.rendering"] with a
stub module carrying the two names base.py binds, whose functions RAISE if
called. evolution_runner imports the adapter before its own `arc_agi` line.
Flag unset: the guard returns False without touching sys.modules -- today's
path, byte-identical.

The falsifiers, as gated here (every toolkit import in a FRESH subprocess;
this test process never imports the toolkit):
  F1  guard on, `import evolution_runner`: no matplotlib* or fontTools* module
      in sys.modules; arc_agi.rendering IS the stub.
  F2  guard on ("1"), `import arc_api_adapter` alone: the same.
  F3  guard off (flag absent): the real arc_agi.rendering (its __file__) and
      matplotlib load; the arc_agi*/matplotlib*/fontTools* module footprint of
      `import arc_api_adapter` equals that of a bare `import arc_agi` -- the
      adapter adds nothing to and removes nothing from the toolkit's import.
  F4  every toolkit symbol our code binds -- the set read off the AST of the
      three import sites, asserted by identity -- resolves under the guard to
      the same objects the adapter exposes; the stub's functions raise
      RuntimeError naming the flag (loud, never a silent no-draw).
  F5  the guard is idempotent (second call False, same stub object) and never
      replaces an already-loaded real module (flag "true", toolkit imported
      first, adapter after: rendering stays real).
  F6  ordering, asserted on the AST: in arc_api_adapter the guard CALL
      precedes the first arc_agi import; in evolution_runner
      `import arc_api_adapter` precedes `from arc_agi import ...`.
  F7  game_player binds the toolkit only lazily (inside a def), so a process
      reaches that line only after its caller built an Arcade through the
      guarded path.

No .runs, no DB, no Arcade constructed, no network.
"""
from __future__ import annotations

import ast
import functools
import json
import os
import subprocess
import sys
import tempfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADAPTER = os.path.join(REPO, "arc_api_adapter.py")
RUNNER = os.path.join(REPO, "evolution_runner.py")
PLAYER = os.path.join(REPO, "game_player.py")
IMPORT_SITES = (ADAPTER, RUNNER, PLAYER)

FLAG = "OURO_HEADLESS"
RENDERING = "arc_agi.rendering"
STUB_MARK = "__ouro_headless_stub__"
VIZ_ROOTS = ("matplotlib", "fontTools")
TOOLKIT_ROOTS = ("arc_agi",) + VIZ_ROOTS

# The probe. argv: target-module, out-path, json-list of symbol names. It records
# the module footprint straight after the target import (before it touches the
# adapter itself), then imports arc_agi + the adapter for the symbol and stub checks.
PROBE = r"""
import json, sys
target, out, names = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
ROOTS = ("arc_agi", "matplotlib", "fontTools")
__import__(target)
footprint = sorted(m for m in sys.modules if m.split(".")[0] in ROOTS)
import arc_agi
import arc_api_adapter as A
r = sys.modules.get("arc_agi.rendering")
is_stub = bool(getattr(r, A.HEADLESS_STUB_MARK, False))
raised = {}
if is_stub:
    for fn in A.RENDERING_STUB_NAMES:
        try:
            getattr(r, fn)(steps=0, frame_data=None, default_fps=1, scale=1)
            raised[fn] = None
        except RuntimeError as e:
            raised[fn] = str(e)
second = A.install_headless_render_guard()
rep = {
    "footprint": footprint,
    "viz": [m for m in footprint if m.split(".")[0] in ("matplotlib", "fontTools")],
    "rendering_is_stub": is_stub,
    "rendering_file": getattr(r, "__file__", None),
    "has_matplotlib_flag": getattr(r, "HAS_MATPLOTLIB", None),
    "stub_names_present": [fn for fn in A.RENDERING_STUB_NAMES if hasattr(r, fn)],
    "raised": raised,
    "resolves": {n: hasattr(arc_agi, n) for n in names},
    "same_as_adapter": {n: getattr(arc_agi, n, 0) is getattr(A, n, 1) for n in names},
    "opmode_members": sorted(arc_agi.OperationMode.__members__),
    "second_call": second,
    "same_object_after": sys.modules.get("arc_agi.rendering") is r,
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(rep, f)
"""


# ----------------------------------------------------------------------------
# The symbol set: what our three import sites bind from the toolkit, off the AST
# ----------------------------------------------------------------------------

def _toolkit_bindings(path):
    """(module_level_names, lazy_names, attribute_uses) bound from arc_agi in `path`.

    module_level: names in `from arc_agi import ...` at module scope.
    lazy: the same, nested inside a def/class body.
    attribute_uses: `arc_agi.X` attribute reads anywhere (docstrings excluded: AST).
    """
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    top, lazy, attrs = set(), set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == "arc_agi":
            attrs.add(node.attr)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "arc_agi":
            top.update(a.name for a in node.names)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.ImportFrom) and sub.module == "arc_agi":
                    lazy.update(a.name for a in sub.names)
    return top, lazy, attrs


def _all_symbols():
    names = set()
    for p in IMPORT_SITES:
        top, lazy, attrs = _toolkit_bindings(p)
        names |= top | lazy | attrs
    return sorted(names)


# ----------------------------------------------------------------------------
# Fresh-subprocess probes, one per (target, flag), cached for the session
# ----------------------------------------------------------------------------

@functools.cache
def probe(target, flag):
    """Run PROBE on `target` in a fresh interpreter with OURO_HEADLESS=flag (None: absent)."""
    env = dict(os.environ)
    env.pop(FLAG, None)
    if flag is not None:
        env[FLAG] = flag
    env["PYTHONPATH"] = REPO
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "rep.json")
        argv = [sys.executable, "-c", PROBE, target, out, json.dumps(_all_symbols())]
        done = subprocess.run(  # noqa: S603 -- fixed argv, our interpreter, our probe
            argv, cwd=REPO, env=env, capture_output=True, text=True, timeout=900,
            check=False,  # the returncode is asserted below, with stderr in the message
        )
        assert done.returncode == 0, f"probe {target!r} {FLAG}={flag!r} failed:\n{done.stderr[-3000:]}"
        with open(out, encoding="utf-8") as f:
            return json.load(f)


# ----------------------------------------------------------------------------
# F1 / F2: guard on -> no visualiser
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("target,flag", [("evolution_runner", "1"), ("arc_api_adapter", "1")])
def test_f1_f2_guard_on_no_matplotlib(target, flag):
    rep = probe(target, flag)
    assert rep["viz"] == [], f"visualiser modules loaded under {FLAG}={flag}: {rep['viz']}"
    assert rep["rendering_is_stub"] is True
    assert rep["rendering_file"] is None
    assert rep["has_matplotlib_flag"] is False
    assert RENDERING in rep["footprint"]  # the name IS there -- the stub, found by base.py


# ----------------------------------------------------------------------------
# F3: guard off -> today's path, byte-identical footprint
# ----------------------------------------------------------------------------

def test_f3_default_path_loads_real_rendering_and_matplotlib():
    rep = probe("arc_api_adapter", None)
    assert rep["rendering_is_stub"] is False
    f = rep["rendering_file"]
    assert f and os.path.basename(f) == "rendering.py" and "arc_agi" in f.replace("\\", "/")
    assert "matplotlib" in rep["footprint"]
    assert any(m.startswith("matplotlib") for m in rep["viz"])
    assert rep["has_matplotlib_flag"] is True
    assert rep["second_call"] is False  # flag off: the guard does nothing


def test_f3_default_footprint_equals_bare_toolkit_import():
    via_adapter = probe("arc_api_adapter", None)["footprint"]
    bare = probe("arc_agi", "true")["footprint"]  # recorded before the adapter is touched
    assert via_adapter == bare


# ----------------------------------------------------------------------------
# F4: every symbol our code binds resolves under the guard; the stub is loud
# ----------------------------------------------------------------------------

def test_f4_symbol_set_is_the_grep_result():
    top_a, lazy_a, attrs_a = _toolkit_bindings(ADAPTER)
    top_r, lazy_r, attrs_r = _toolkit_bindings(RUNNER)
    top_p, lazy_p, attrs_p = _toolkit_bindings(PLAYER)
    assert (top_a, lazy_a, attrs_a) == ({"Arcade", "OperationMode"}, set(), set())
    assert (top_r, lazy_r, attrs_r) == ({"Arcade", "OperationMode"}, set(), set())
    assert (top_p, lazy_p, attrs_p) == (set(), {"OperationMode"}, set())
    assert _all_symbols() == ["Arcade", "OperationMode"]


def test_f4_symbols_resolve_under_guard_to_the_adapters_objects():
    rep = probe("evolution_runner", "1")
    assert rep["resolves"] == dict.fromkeys(_all_symbols(), True)
    assert rep["same_as_adapter"] == dict.fromkeys(_all_symbols(), True)
    # The members our code compares against (evolution_runner mode map, game_player tags).
    assert {"NORMAL", "OFFLINE", "ONLINE"} <= set(rep["opmode_members"])


def test_f4_stub_functions_raise_naming_the_flag():
    rep = probe("arc_api_adapter", "1")
    assert sorted(rep["stub_names_present"]) == ["render_frames", "render_frames_terminal"]
    assert set(rep["raised"]) == {"render_frames", "render_frames_terminal"}
    for fn, msg in rep["raised"].items():
        assert msg and FLAG in msg and RENDERING in msg, (fn, msg)


# ----------------------------------------------------------------------------
# F5: idempotent; never replaces a loaded real module
# ----------------------------------------------------------------------------

def test_f5_second_call_is_noop_and_keeps_the_stub():
    rep = probe("arc_api_adapter", "1")
    assert rep["second_call"] is False
    assert rep["same_object_after"] is True
    assert rep["rendering_is_stub"] is True


def test_f5_real_module_loaded_first_is_never_replaced():
    rep = probe("arc_agi", "true")  # toolkit first, adapter (and its guard) after
    assert rep["rendering_is_stub"] is False
    assert rep["rendering_file"] and os.path.basename(rep["rendering_file"]) == "rendering.py"
    assert rep["second_call"] is False
    assert rep["same_object_after"] is True


# ----------------------------------------------------------------------------
# F6 / F7: ordering and laziness, on the AST
# ----------------------------------------------------------------------------

def _top_level_lines(path):
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    guard_call = first_arc_agi = first_adapter = None
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                and isinstance(node.value.func, ast.Name) \
                and node.value.func.id == "install_headless_render_guard":
            guard_call = guard_call or node.lineno
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "arc_agi"
                                                 for a in node.names):
            first_arc_agi = first_arc_agi or node.lineno
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "arc_agi":
            first_arc_agi = first_arc_agi or node.lineno
        if isinstance(node, ast.Import) and any(a.name == "arc_api_adapter" for a in node.names):
            first_adapter = first_adapter or node.lineno
        if isinstance(node, ast.ImportFrom) and node.module == "arc_api_adapter":
            first_adapter = first_adapter or node.lineno
    return guard_call, first_arc_agi, first_adapter


def test_f6_adapter_guard_call_precedes_its_first_toolkit_import():
    guard_call, first_arc_agi, _ = _top_level_lines(ADAPTER)
    assert guard_call is not None and first_arc_agi is not None
    assert guard_call < first_arc_agi, (guard_call, first_arc_agi)


def test_f6_runner_imports_adapter_before_toolkit():
    _, first_arc_agi, first_adapter = _top_level_lines(RUNNER)
    assert first_adapter is not None and first_arc_agi is not None
    assert first_adapter < first_arc_agi, (first_adapter, first_arc_agi)


def test_f7_game_player_binds_toolkit_only_lazily():
    top, lazy, attrs = _toolkit_bindings(PLAYER)
    _, first_arc_agi, _ = _top_level_lines(PLAYER)
    assert top == set() and attrs == set() and first_arc_agi is None
    assert lazy == {"OperationMode"}
