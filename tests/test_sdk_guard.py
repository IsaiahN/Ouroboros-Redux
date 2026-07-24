"""The online ARC-AGI-3 SDK and a static ARC-1/2 dataset library share the import name `arc_agi`. On a fresh
container the default interpreter can resolve to the static one (no `Arcade`), which would ImportError opaquely mid
run. sdk_guard turns that into a precise, actionable failure and lets the live entrypoints assert sanity before
touching the wire -- never fabricating results against the wrong SDK."""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from newhorse.redux_arch import sdk_guard


class _FakeStatic:
    """Mimics the STATIC arc-agi dataset lib: has Grid/Task, but NO Arcade / OperationMode."""
    Grid = object; Task = object; Dataset = object


class _OnlineMode:
    ONLINE = "OperationMode.ONLINE"


class _FakeOnline:
    """Mimics the ONLINE game SDK: has Arcade and OperationMode.ONLINE."""
    Arcade = object
    OperationMode = _OnlineMode


def test_present_true_on_online(monkeypatch):
    monkeypatch.setitem(sys.modules, "arc_agi", _FakeOnline)
    assert sdk_guard.online_sdk_present() is True
    sdk_guard.assert_online_sdk()                     # must NOT raise


def test_present_false_on_static(monkeypatch):
    monkeypatch.setitem(sys.modules, "arc_agi", _FakeStatic)
    assert sdk_guard.online_sdk_present() is False


def test_assert_raises_actionable_message_on_static(monkeypatch):
    monkeypatch.setitem(sys.modules, "arc_agi", _FakeStatic)
    with pytest.raises(RuntimeError) as ei:
        sdk_guard.assert_online_sdk()
    msg = str(ei.value)
    assert "python3.12" in msg                        # tells the operator exactly how to fix it
    assert "will not fabricate" in msg                # states the fail-loud contract


def test_real_interpreter_has_online_sdk_or_is_honestly_absent():
    """On the interpreter that actually runs the live suite, either the online SDK is present, or the guard says so
    honestly -- there is no third (silent) state."""
    present = sdk_guard.online_sdk_present()
    if present:
        sdk_guard.assert_online_sdk()                 # no raise
    else:
        with pytest.raises(RuntimeError):
            sdk_guard.assert_online_sdk()
