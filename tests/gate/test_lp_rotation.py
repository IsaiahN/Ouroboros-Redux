"""LP ARM ROTATION GATE: arms rotate per recycle -- the confound killer.

A worker that carries ONE arm forever confounds arm with game: ar25's arm
verdict is also an ar25 verdict. Rotation breaks the confound at zero cost:

    arm = ARMS[(sha1(game) + recycle_count) mod 3]

so every game visits EVERY arm across any 3 consecutive recycles, assignment
stays deterministic (sha1, never the salted builtin hash -- same inputs, same
arm in every process and reboot), and recycle_count=0 reproduces the original
static assignment exactly (no history rewritten). The supervisor passes its
per-game recycle counter into assign_arm at every spawn and LOGS the pair --
an arm assignment that leaves no trace is unauditable.

Wiring is asserted by AST (the calls exist in the supervisor's spawn), never
by char-offset windows (KNOBS A4-2: no character economy).
"""
from __future__ import annotations

import ast
import hashlib
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _lp():
    from engines.egocentric import lp_drive
    return lp_drive


def _supervisor_tree():
    path = os.path.join(REPO, "tools", "swarm_supervisor.py")
    with open(path, encoding="utf-8", errors="replace") as f:
        return ast.parse(f.read())


def _games():
    for node in ast.walk(_supervisor_tree()):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "GAMES":
                    return ast.literal_eval(node.value)
    pytest.fail("GAMES list not found in tools/swarm_supervisor.py")


class TestTheRotationFormula:

    def test_arm_is_sha1_plus_recycle_count_mod_3(self):
        """The pinned formula: ARMS[(sha1(game) + recycle_count) mod 3]."""
        lp = _lp()
        for g in ("ar25", "ls20", "vc33", "anything"):
            h = int(hashlib.sha1(g.encode("utf-8"),
                                 usedforsecurity=False).hexdigest(), 16)
            for k in range(7):
                assert lp.assign_arm(g, k) == lp.ARMS[(h + k) % 3], (
                    "assign_arm(%r, %d) must be ARMS[(sha1+%d) mod 3]" % (g, k, k))

    def test_zero_recycles_reproduces_the_static_assignment(self):
        """recycle_count=0 (and the omitted default) is the original sha1 mod 3
        assignment -- no worker's history is rewritten by the rotation."""
        lp = _lp()
        for g in _games():
            assert lp.assign_arm(g) == lp.assign_arm(g, 0)

    def test_every_game_visits_every_arm_across_3_recycles(self):
        """The confound killer: any 3 consecutive recycles cover all arms."""
        lp = _lp()
        for g in _games():
            for start in range(3):
                arms = {lp.assign_arm(g, start + k) for k in range(3)}
                assert arms == set(lp.ARMS), (
                    "%s must visit all three arms across recycles %d..%d"
                    % (g, start, start + 2))

    def test_deterministic_across_calls(self):
        lp = _lp()
        for g in _games():
            for k in range(4):
                assert lp.assign_arm(g, k) == lp.assign_arm(g, k)


class TestTheSupervisorWiring:

    def _spawn(self):
        for node in ast.walk(_supervisor_tree()):
            if isinstance(node, ast.FunctionDef) and node.name == "spawn":
                return node
        pytest.fail("def spawn not found in tools/swarm_supervisor.py")

    def test_spawn_rotates_by_the_recycle_counter(self):
        """spawn() must call assign_arm with TWO arguments -- the game and the
        recycle count -- so the arm rotates on every recycle (AST, no windows)."""
        calls = [n for n in ast.walk(self._spawn())
                 if isinstance(n, ast.Call)
                 and ((isinstance(n.func, ast.Name) and n.func.id == "assign_arm")
                      or (isinstance(n.func, ast.Attribute)
                          and n.func.attr == "assign_arm"))]
        assert calls, "spawn() never calls assign_arm -- workers get no arm"
        assert any(len(c.args) >= 2 for c in calls), (
            "spawn() calls assign_arm without the recycle count -- the arm can "
            "never rotate and the arm/game confound stands")
        src = ast.unparse(self._spawn())
        assert "recycles" in src, (
            "the second argument must be the per-game recycle counter")

    def test_the_arm_and_recycle_count_are_logged_per_spawn(self):
        """Every spawn logs arm AND recycle count -- nothing silent."""
        src = ast.unparse(self._spawn())
        assert "LP_DRIVE_ARM" in src, "spawn() must set the arm env"
        assert "recycle" in src.lower() and (".write" in src or "print" in src), (
            "the spawn log must carry the recycle count beside the arm")
