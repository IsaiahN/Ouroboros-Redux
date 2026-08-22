"""THE REBINDING BIN MUST HAVE A DESTINATION. record/prereg/PREREG_REFIT_DESTINATION.md.

ROUTE sorts every settled bet into one of four bins. Three of them drained somewhere:
NOVEL -> the `import_queue` stream, BROKEN-mechanism -> the mint, TRANSFERRED -> settlements.
**BROKEN-rebinding appended to `ResidualRouter.refit_queue`, an in-memory list referenced
nowhere else in the tree** -- so the one bin whose meaning is *repair this, do not mint* died
with the process, and across 25 boxes its stream has never existed.

SCOPE: THE DESTINATION ONLY. `binding_stale` is set by nothing in production, so the bin
still cannot fire and the drain is a no-op on the live system. That is the ruled order --
a diagnosis that dies with the process is not a diagnosis, so the destination lands first.

R4 / the three prereg falsifiers:
  F1 it persists          -- a rebinding-routed record reaches the stream, whole
  F3 known-negative       -- NOVEL and BROKEN-mechanism records must NOT reach it, or F1
                             would pass on a drain that copies everything
  F2 it changes nothing   -- asserted here as: the router's own bin counts are untouched by
                             draining, and an empty refit_queue writes no records at all
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.router import (  # noqa: E402
    BROKEN_MECHANISM,
    BROKEN_REBINDING,
    NOVEL,
    TRANSFERRED,
    ResidualRouter,
)


class _Fab:
    """Minimal fabric double: records (scope, topic, record) appends."""

    def __init__(self):
        self.writes = []

    def append(self, scope, topic, rec):
        self.writes.append((scope, topic, rec))


def _settlement(residual=1.0, bet=True, binding_stale=False, from_known_atom=False):
    return {"bet": bet, "residual": residual,
            "binding_stale": binding_stale, "from_known_atom": from_known_atom}


def _drain(router, fab, game="gg01-abc", level=1):
    """The drain under test, mirroring cognitive_loop.py's refit block exactly."""
    while router.refit_queue:
        it = router.refit_queue.pop(0)
        fab.append("collective", "refit_queue", {
            "slot": it.get("slot"),
            "residual": float(it.get("residual", 0.0)),
            "game": str(game),
            "level": int(level) + 1,
        })


def test_f1_a_rebinding_record_reaches_the_stream_whole():
    r = ResidualRouter()
    assert r.route("REFERENCE", _settlement(2.0, binding_stale=True)) == BROKEN_REBINDING
    assert len(r.refit_queue) == 1, "router did not queue the rebinding item"

    fab = _Fab()
    _drain(r, fab, game="gg01-abc", level=1)

    assert len(fab.writes) == 1, "the rebinding diagnosis did not reach a destination"
    scope, topic, rec = fab.writes[0]
    assert (scope, topic) == ("collective", "refit_queue")
    # every field, because a record that loses one is a record that cannot be read back
    assert rec["slot"] == "REFERENCE"
    assert rec["residual"] == 2.0
    assert rec["game"] == "gg01-abc"
    assert rec["level"] == 2, "A3-2 PLAYING-level convention not applied"
    assert not r.refit_queue, "the queue was not drained"


def test_f3_known_negative_other_bins_do_not_reach_the_refit_stream():
    """Without this, F1 would pass on a drain that copied everything."""
    r = ResidualRouter()
    assert r.route("A", _settlement(2.0, from_known_atom=True)) == BROKEN_MECHANISM
    assert r.route("B", _settlement(2.0)) == NOVEL
    assert r.route("C", _settlement(0.0)) == TRANSFERRED

    fab = _Fab()
    _drain(r, fab)
    assert fab.writes == [], "a non-rebinding bin leaked onto the refit stream"
    # and the siblings still hold their own items, untouched by the refit drain
    assert len(r.mint_queue) == 1
    assert len(r.import_queue) == 1


def test_f2_an_empty_queue_writes_nothing_at_all():
    """The live prediction: with `binding_stale` never set, the drain is a NO-OP and no
    stream is created. An empty stream appearing would itself be the failure."""
    r = ResidualRouter()
    for _ in range(20):
        r.route("S", _settlement(1.0))                       # all NOVEL
    assert r.routed[BROKEN_REBINDING] == 0, "rebinding fired without binding_stale"

    fab = _Fab()
    _drain(r, fab)
    assert fab.writes == [], "the drain wrote on an empty queue"


def test_f2_draining_does_not_disturb_the_router_s_bin_counts():
    r = ResidualRouter()
    r.route("A", _settlement(2.0, binding_stale=True))
    r.route("B", _settlement(2.0, from_known_atom=True))
    r.route("C", _settlement(2.0))
    before = dict(r.routed)

    _drain(r, _Fab())
    assert dict(r.routed) == before, "the drain mutated the routing census"


def test_the_bin_is_still_unreachable_in_production_and_this_test_says_so():
    """STATED, not assumed: this build does NOT throw the switch. Nothing in production
    sets `binding_stale`, so a settlement built the way production builds one still routes
    away from rebinding. When the switch build lands, THIS test is the one that must be
    updated -- which is the point of writing it down."""
    r = ResidualRouter()
    production_shaped = {"bet": True, "residual": 2.0, "from_known_atom": False}
    assert r.route("S", production_shaped) == NOVEL
    assert r.routed[BROKEN_REBINDING] == 0
