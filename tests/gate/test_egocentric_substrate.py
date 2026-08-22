"""PHASE 1 GATE: the egocentric perception substrate — the loop learns which body is ITS OWN.

⭐ WHY. The 20-generation cold baseline: 6 games at L1, ZERO L2 in 1800 episodes. v4's depth
failure begins with not knowing what the game wants; knowing what the game wants begins with
knowing which object is *me*. This phase ports the new horse's belief-state bricks and wires
them READ-ONLY (the wheel rule: Phase 1 is sensing, not even signal).

THE CONTRACT (record/prereg/PREREG_PHASE1.md):
  * `engines/egocentric/` carries verbatim ports: `perception.segment` + `Object` +
    `ObjectTracker`, `SelfLocus` (contingency, not correlation), `CursorAgency`;
  * `EgoObserver` wrapper: holds the previous frame internally; `observe(frame, action)` →
    dict with at least `colour` (controllable colour or None) and `objects` (count); first
    call (no previous frame) returns colour=None and stores state; deterministic; exceptions
    swallowed to a counter attribute `errors`;
  * ⭐ THE GOARDHART GUARD IS THE POINT: an object that moves the same under EVERY action is
    autonomous, not self. Only action-CONTINGENT motion names the controllable.
  * wiring: the cognitive loop's result path calls the observer and logs `[EGO]`; NOTHING in
    the decision path reads the result (read-only phase).

Run pre-build: these failed (package absent), per the iced branch's beat-49 rule.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _mods():
    try:
        from engines.egocentric import perception, self_locus  # noqa: F401
        from engines.egocentric.observer import EgoObserver  # noqa: F401
    except Exception as e:
        pytest.fail("engines.egocentric is missing or broken (%s) — Phase 1 has not landed; "
                    "see record/prereg/PREREG_PHASE1.md" % e)
    from engines.egocentric import perception as P
    from engines.egocentric import self_locus as SL
    from engines.egocentric.observer import EgoObserver as EO
    return P, SL, EO


class TestSegmentationAndTracking:

    def test_two_objects_are_found_with_their_colours(self):
        P, _, _ = _mods()
        g = np.zeros((10, 10), dtype=int)
        g[2, 2] = 3
        g[7, 7] = 5
        g[7, 8] = 5
        objs = P.segment(g, background=0)
        assert len(objs) == 2
        sizes = sorted(o.size for o in objs)
        assert sizes == [1, 2]
        assert {min(o.colours) for o in objs} == {3, 5}

    def test_tracker_holds_identity_across_a_small_move(self):
        P, _, _ = _mods()
        t = P.ObjectTracker()
        g1 = np.zeros((10, 10), dtype=int)
        g1[2, 2] = 3
        g1[2, 3] = 3
        g2 = np.zeros((10, 10), dtype=int)
        g2[2, 3] = 3
        g2[2, 4] = 3
        a = t.update(P.segment(g1, background=0))
        b = t.update(P.segment(g2, background=0))
        assert len(a) == 1 and len(b) == 1


class TestTheContingencyGuard:

    def _objs(self, P, positions_colours):
        g = np.zeros((16, 16), dtype=int)
        for (r, c), col in positions_colours:
            g[r, c] = col
        return P.segment(g, background=0)

    def test_action_contingent_motion_beats_autonomous_drift(self):
        """⭐ THE GUARD. Colour 3 moves 2 cells under A1 and 0 under A2 (contingent). Colour 7
        drifts 1 cell under EVERY action (autonomous). The self is 3, never 7."""
        P, SL, _ = _mods()
        s = SL.SelfLocus()
        r3, r7 = 4, 12
        for i in range(3):
            before = self._objs(P, [((r3, 2 + 2 * i), 3), ((r7, 2 + i), 7)])
            after = self._objs(P, [((r3, 4 + 2 * i), 3), ((r7, 3 + i), 7)])
            s.observe("A1", before, after)
            before2 = self._objs(P, [((r3, 8), 3), ((r7, 6 + i), 7)])
            after2 = self._objs(P, [((r3, 8), 3), ((r7, 7 + i), 7)])
            s.observe("A2", before2, after2)
        assert s.controllable_colour() == 3, (
            "an object drifting identically under every action was preferred over the "
            "action-contingent one — the Goodhart guard is broken")

    def test_cold_start_names_nobody(self):
        P, SL, _ = _mods()
        s = SL.SelfLocus()
        assert s.controllable_colour() is None
        assert s.pick(self._objs(P, [((2, 2), 3)])) is None


class TestTheObserver:

    def test_first_call_stores_and_returns_none_colour(self):
        _, _, EO = _mods()
        o = EO()
        g = np.zeros((8, 8), dtype=int)
        g[1, 1] = 4
        r = o.observe(g, "A1")
        assert r is not None and r.get("colour") is None
        assert r.get("objects", -1) >= 1

    def test_contingent_colour_emerges_through_the_observer(self):
        _, _, EO = _mods()
        o = EO()
        # colour 4 moves 2 cells under A1, stays under A2 -- across enough steps to clear
        # min_events; the observer must eventually name it.
        pos = 1
        g = np.zeros((12, 12), dtype=int)
        g[6, pos] = 4
        o.observe(g, "A1")
        named = None
        for i in range(8):
            act = "A1" if i % 2 == 0 else "A2"
            if act == "A1":
                pos = min(pos + 2, 10)
            g = np.zeros((12, 12), dtype=int)
            g[6, pos] = 4
            named = o.observe(g, act).get("colour")
        assert named == 4

    def test_exceptions_are_swallowed_to_a_counter(self):
        _, _, EO = _mods()
        o = EO()
        r = o.observe("not a frame", "A1")
        assert r is not None and o.errors >= 1

    def test_determinism(self):
        _, _, EO = _mods()
        def run():
            o = EO()
            seq = []
            pos = 1
            for i in range(6):
                g = np.zeros((10, 10), dtype=int)
                g[3, pos] = 2
                seq.append(str(o.observe(g, "A%d" % (i % 2 + 1))))
                pos += (1 if i % 2 == 0 else 0)
            return "|".join(seq)
        assert run() == run()


class TestTheWiringIsReadOnly:

    def test_the_result_path_calls_the_observer_and_logs(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        assert "EgoObserver" in src or "_ego_observer" in src, (
            "cognitive_loop never touches the observer — Phase 1 wiring absent (starvation).")
        assert "[EGO]" in src, "the [EGO] log line is missing — nothing is observable from logs"

    def test_nothing_in_the_decision_path_reads_it(self):
        """⭐ READ-ONLY. The observer's output must not reach action selection in Phase 1 —
        the wheel rule: sensing is not signal. Scan the think/act bodies for ego references."""
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        for fname in ("def _think", "def _act"):
            i = src.find(fname)
            if i == -1:
                continue
            j = src.find("\n    def ", i + 10)
            body = src[i:j if j != -1 else len(src)]
            for name in ("_ego_observer", "EgoObserver", "ego_state", "[EGO]"):
                assert name not in body, (
                    "%s references %s — Phase 1 is READ-ONLY; the wheel rule forbids this "
                    "wire until signal has earned it (Phase 2's prereg)." % (fname, name))
