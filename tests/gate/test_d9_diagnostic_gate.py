"""D-9 GATE: THE SYSTEM DIAGNOSTIC IS OPT-IN, READ ONCE, BYTE-IDENTICAL WHEN ON.

The defect (D-9, 2026-08-21, record/findings/PRIMITIVE_SORT_AND_CENSUS.md):
evolution_runner.py constructed SystemDiagnostic unconditionally at init and
evolve() ran it (~23s per run(), measured) with the result reaching three
print() lines only -- no table, no stream, no programmatic reader -- x25
workers.

The build under test: OURO_DIAGNOSTIC (KNOBS.md Register O, row O4) gates the
CONSTRUCTION at evolution_runner.EvolutionRunner._init_system_diagnostic.
Default OFF: self.system_diagnostic stays None and the sole downstream reader
-- `if self.system_diagnostic:` in evolve() -- skips run() and its prints.
"1"/"true" (any case): the pre-D-9 path, byte-identical.

The falsifiers, as gated here:
  F1  flag absent -> SystemDiagnostic NEVER constructed and run() NEVER called
      across a constructed 3-generation run() loop (class mocked, zero calls).
  F2  flag "1" -> constructed exactly once (db, health_gauges=...) and run()
      called once per cadence-eligible generation WITH the generation number.
      The cadence is the EXISTING one (`% 10 == 0` in evolve()), asserted as
      found, not as D-9's prose described it.
  F3  the flag is read ONCE at init -- zero reads per generation (os.environ
      spied across init + a 3-generation loop + three cadence generations).
  F4  the existing prints are unchanged when on (stdout captured against the
      frozen pre-D-9 format, non-verbose and verbose); no [DIAGNOSTIC] line
      when off.
  F5  the only readers of self.system_diagnostic are the gate site and the
      evolve() guard + run() call -- the grep result, asserted by identity.

No .runs, no DB, no Arcade: the runner is a __new__ skeleton carrying exactly
the attributes run()/evolve() touch, every optional engine None.
"""
from __future__ import annotations

import ast
import inspect
import os
import sys
from unittest.mock import MagicMock, call, patch

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import evolution_runner as ER  # noqa: E402

FLAG = ER.DIAGNOSTIC_ENV_FLAG

# A report shaped like SystemDiagnostic.run()'s return, with values whose
# formatting is unambiguous under the frozen print path.
DIAG_REPORT = {
    "health_status": "degraded",
    "overall_health": 0.75,
    "disconnected_systems": [
        {"table": "alpha"}, {"table": "beta"}, {"table": "gamma"}, {"table": "delta"},
    ],
    "bottleneck_systems": [{"table": "omega"}],
    "knowledge_utilisation": 0.5,
    "compression_effectiveness": 0.25,
    "resonance_connectivity": 0.125,
}

# The pre-D-9 print path, frozen here as the oracle.
EXPECTED_LINES = [
    "  [DIAGNOSTIC] System health: degraded (0.750)",
    "  [DIAGNOSTIC] Disconnected: alpha, beta, gamma",
    "  [DIAGNOSTIC] Bottlenecks: omega",
]
EXPECTED_VERBOSE_LINE = (
    "  [DIAGNOSTIC] Knowledge util: 50.0%, compression: 0.250, resonance conn: 0.125"
)

_OPTIONAL_ENGINES = (
    "horizontal_transfer_engine",
    "network_intelligence_engine",
    "health_responder",
    "resonance_detector",
    "concept_discovery_engine",
    "primitive_unlock_manager",
    "lifecycle_manager",
    "operating_mode_system",
)


class _PipeStub:
    """PipelineAssertions stand-in. A plain class, not a MagicMock: mock refuses
    attribute names starting with `assert` (assert_population_size)."""

    def run_contract_spot_check(self, generation):
        return {"failed": 0, "checked": 0, "passed": 0}

    def assert_population_size(self, population_size, generation):
        return None


def _skeleton(*, verbose: bool = False, start_gen: int = 0, max_gens: int = 3):
    """An EvolutionRunner that never ran __init__: only what run()/evolve() touch."""
    r = ER.EvolutionRunner.__new__(ER.EvolutionRunner)
    r.verbose = verbose
    r.mode = "offline"
    r.population_size = 1
    r.agents_per_generation = 1
    r.games_per_generation = 1
    r.max_actions = 1
    r.max_generations = max_gens
    r.target_game = None
    r.db = MagicMock(name="db")
    r.health_gauges = None
    r.pipe = _PipeStub()
    r._evolution_strategy = {}
    r.evolutionary_engine = MagicMock(name="evolutionary_engine")
    r.evolutionary_engine.evolve_population.return_value = []
    for name in _OPTIONAL_ENGINES:
        setattr(r, name, None)
    r.agents = []
    r.current_generation = start_gen
    r._start_generation = start_gen
    r.running = True
    r.initialize_population = MagicMock(name="initialize_population", return_value=[])
    r.run_generation = MagicMock(name="run_generation", return_value={})
    r._health_monitor = MagicMock(name="health_monitor")
    return r


def _drive_cadence_generations(r, gens):
    """Call evolve() directly at the given generation numbers (cadence-eligible or not)."""
    for g in gens:
        r.current_generation = g
        r.evolve()


@pytest.fixture
def diag_cls():
    """SystemDiagnostic replaced by a mock class; availability forced True (hermetic)."""
    cls = MagicMock(name="SystemDiagnostic")
    cls.return_value.run.return_value = dict(DIAG_REPORT)
    with patch.object(ER, "SystemDiagnostic", cls), \
         patch.object(ER, "SYSTEM_DIAGNOSTIC_AVAILABLE", True):
        yield cls


def _env(value):
    """Context: OURO_DIAGNOSTIC set to value, or removed when value is None."""
    if value is None:
        scrubbed = {k: v for k, v in os.environ.items() if k != FLAG}
        return patch.dict(os.environ, scrubbed, clear=True)
    return patch.dict(os.environ, {FLAG: value})


# ---------------------------------------------------------------- F1: default OFF

def test_flag_absent_never_constructed_never_run_over_three_generations(diag_cls):
    r = _skeleton(start_gen=0, max_gens=3)
    with _env(None):
        assert FLAG not in os.environ
        r._init_system_diagnostic()
        assert r._diagnostic_enabled is False
        assert r.system_diagnostic is None
        r.run()

    # The loop really ran three generations through the real evolve().
    assert r.current_generation == 3
    assert r.run_generation.call_count == 3
    assert r.evolutionary_engine.evolve_population.call_count == 3
    # ...and the diagnostic was neither built nor run.
    diag_cls.assert_not_called()
    diag_cls.return_value.run.assert_not_called()


@pytest.mark.parametrize("value", ["", "0", "false", "off", "no", "yes", "on", " "])
def test_non_opt_in_values_stay_off(diag_cls, value):
    r = _skeleton()
    with _env(value):
        r._init_system_diagnostic()
        _drive_cadence_generations(r, [10, 20, 30])
    assert r.system_diagnostic is None
    diag_cls.assert_not_called()
    diag_cls.return_value.run.assert_not_called()


# ---------------------------------------------------------------- F2: opt-in path

@pytest.mark.parametrize("value", ["1", "true", "TRUE", "True", " 1 "])
def test_flag_on_constructs_once_with_existing_signature(diag_cls, value):
    r = _skeleton()
    with _env(value):
        r._init_system_diagnostic()
    assert r._diagnostic_enabled is True
    assert r.system_diagnostic is diag_cls.return_value
    diag_cls.assert_called_once_with(r.db, health_gauges=r.health_gauges)


def test_flag_on_three_generation_loop_runs_at_existing_cadence(diag_cls):
    """run() loop over generations 0,1,2: the existing `% 10` cadence fires at 0 only."""
    r = _skeleton(start_gen=0, max_gens=3)
    with _env("1"):
        r._init_system_diagnostic()
        r.run()
    assert r.current_generation == 3
    diag_cls.assert_called_once()
    assert diag_cls.return_value.run.call_args_list == [call(0)]


def test_flag_on_run_called_once_per_cadence_generation_with_its_number(diag_cls):
    r = _skeleton()
    with _env("1"):
        r._init_system_diagnostic()
        _drive_cadence_generations(r, [10, 20, 30])
    diag_cls.assert_called_once()
    assert diag_cls.return_value.run.call_args_list == [call(10), call(20), call(30)]


# ---------------------------------------------------------------- F3: read ONCE

def test_flag_read_exactly_once_at_init_never_per_generation(diag_cls):
    env_spy = MagicMock(name="environ")
    env_spy.get.return_value = "1"
    r = _skeleton(start_gen=0, max_gens=3)
    # evolution_runner reads through `os.environ.get`; os.getenv routes there too.
    with patch.object(ER.os, "environ", env_spy):
        r._init_system_diagnostic()
        assert env_spy.get.call_count == 1
        assert env_spy.get.call_args == call(FLAG, "")
        r.run()
        _drive_cadence_generations(r, [10, 20, 30])
        assert env_spy.get.call_count == 1
    assert r.system_diagnostic is diag_cls.return_value
    assert diag_cls.return_value.run.call_args_list == [call(0), call(10), call(20), call(30)]


def test_diagnostic_enabled_is_a_pure_read_of_the_flag():
    with _env(None):
        assert ER.diagnostic_enabled() is False
    with _env("1"):
        assert ER.diagnostic_enabled() is True
    with _env("true"):
        assert ER.diagnostic_enabled() is True
    with _env("0"):
        assert ER.diagnostic_enabled() is False


# ---------------------------------------------------------------- F4: prints unchanged

def test_prints_unchanged_when_on_non_verbose(diag_cls, capsys):
    r = _skeleton(verbose=False)
    with _env("1"):
        r._init_system_diagnostic()
        _drive_cadence_generations(r, [10])
    out = capsys.readouterr().out
    lines = out.splitlines()
    diag_lines = [ln for ln in lines if "[DIAGNOSTIC]" in ln]
    assert diag_lines == EXPECTED_LINES
    assert "[INIT] System diagnostic initialized" not in out


def test_prints_unchanged_when_on_verbose(diag_cls, capsys):
    r = _skeleton(verbose=True)
    with _env("1"):
        r._init_system_diagnostic()
        _drive_cadence_generations(r, [10])
    out = capsys.readouterr().out
    assert "[INIT] System diagnostic initialized" in out
    diag_lines = [ln for ln in out.splitlines() if "[DIAGNOSTIC]" in ln]
    assert diag_lines == [*EXPECTED_LINES, EXPECTED_VERBOSE_LINE]


def test_no_diagnostic_output_when_off(diag_cls, capsys):
    r = _skeleton(verbose=True)
    with _env(None):
        r._init_system_diagnostic()
        r.run()
        _drive_cadence_generations(r, [10, 20, 30])
    out = capsys.readouterr().out
    assert "[DIAGNOSTIC]" not in out
    assert "System diagnostic" not in out


# ---------------------------------------------------------------- F5: the only readers

def _self_attr_sites(src: str, attr: str):
    """(function_name, lineno) for every `self.<attr>` in code -- comments/docstrings excluded."""
    tree = ast.parse(src)
    sites = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == attr
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            ):
                sites.append((fn.name, node.lineno))
    return sites


def test_system_diagnostic_has_no_reader_beyond_gate_and_evolve_guard():
    src = inspect.getsource(ER)
    # Two writes in the gate method, one guard and one run() call in evolve() --
    # counted on the AST so prose mentions in comments/docstrings cannot move it.
    sites = _self_attr_sites(src, "system_diagnostic")
    by_fn = sorted({fn for fn, _ in sites})
    assert by_fn == ["_init_system_diagnostic", "evolve"], sites
    assert sum(1 for fn, _ in sites if fn == "_init_system_diagnostic") == 2, sites
    assert sum(1 for fn, _ in sites if fn == "evolve") == 2, sites
    assert src.count("self.system_diagnostic.run(") == 1
    gate_src = inspect.getsource(ER.EvolutionRunner._init_system_diagnostic)
    assert gate_src.count("self.system_diagnostic = None") == 1
    assert gate_src.count("self.system_diagnostic = SystemDiagnostic(") == 1
    evolve_src = inspect.getsource(ER.EvolutionRunner.evolve)
    assert evolve_src.count("if self.system_diagnostic:") == 1
    assert evolve_src.count("self.system_diagnostic.run(self.current_generation)") == 1
    init_src = inspect.getsource(ER.EvolutionRunner.__init__)
    assert "SystemDiagnostic(" not in init_src
    assert "self._init_system_diagnostic()" in init_src
