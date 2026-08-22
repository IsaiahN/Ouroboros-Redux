"""SPRINT KEEPER -- the relaunch-only watchdog for sprint-mode workers.

THE ERROR THIS EXISTS FOR (2026-08-21): sprint mode runs three workers directly, no
supervisor. A worker that reaches --max-generations EXITS, nothing relaunches it, and the
fleet goes to zero with no line written anywhere. The keeper notices ABSENCE and relaunches;
it must never do anything else -- no kills, no deploys, no HOLD.

R4, both directions, because a keeper that relaunches everything and one that relaunches
nothing are equally useless:
  KNOWN-POSITIVE  a game with no live worker MUST be spawned, once, in its own box, with
                  its own --game
  KNOWN-NEGATIVE  a game whose worker is live must NOT be spawned; a worker for a
                  DIFFERENT game, or a python that is not evolution_runner, does not count
                  as "live" for this game
  AND STABILITY   a second pass over the same (now complete) process list spawns nothing

FLEET-ENV PARITY (the second gap, 2026-08-21): the supervisor assembles OURO_FABRIC_SEEDS
and LP_DRIVE_ARM per worker; a keeper that relaunched with a bare env ran an undeclared
different config. So:
  PARITY          for a constructed root, the keeper's env for game X equals the
                  supervisor's assembly for X -- same seed set, same ';' separator, own box
                  excluded, arm = assign_arm(X, 0). The expected value is the supervisor's
                  PRE-fleet_env lines, FROZEN HERE as the oracle (commit e1cce38,
                  swarm_supervisor.py 64-65 + 191-192 + 200) -- not any helper's idea of
                  them -- and the supervisor's OWN spawn() (Popen faked) must produce the
                  same bytes, at every recycle count
  OPT-OUT         --no-fleet-env sets neither variable, and the log line says bare-env
  ONE STATEMENT   (2026-08-21, the third gap) the keeper carries NO transcription: roster
                  and assembly come from tools/fleet_env.py, which the supervisor imports
                  too. A transcription drifts; a shared function cannot.
  CLEAN IMPORT    the supervisor imports with NO side effects -- no .env read, no mkdir,
                  no spawn, no loop (the D-6 lesson at tooling grain) -- so the parity gate
                  can run the real spawn() instead of a copy of it

No .runs, no real processes: enumeration is a constructed list, Popen is a fake.
"""
from __future__ import annotations

import ast
import builtins
import importlib
import os
import subprocess
import sys
import time
from unittest import mock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.lp_drive import assign_arm  # noqa: E402
from tools import fleet_env as fe  # noqa: E402
from tools import sprint_keeper as sk  # noqa: E402

SUPERVISOR_SRC = os.path.join(REPO, "tools", "swarm_supervisor.py")
FLEET_ENV_SRC = os.path.join(REPO, "tools", "fleet_env.py")
KEEPER_SRC = os.path.join(REPO, "tools", "sprint_keeper.py")

PY = r"C:\Users\Admin\Documents\GitHub\Ouroboros-Redux\.venv\Scripts\python.exe"
RUNNER = r"C:\Users\Admin\Documents\GitHub\Ouroboros-Redux\evolution_runner.py"
TEMPLATE_LINE = ("%s %s --verbose --mode offline --game sk48 --population 6 "
                 "--agents-per-gen 4 --games-per-gen 1 --max-generations 50" % (PY, RUNNER))


def _cmd(game, runner=RUNNER):
    return "%s %s --verbose --mode offline --game %s --population 6 --max-generations 50" % (
        PY, runner, game)


# ── argv templating ──────────────────────────────────────────────────────────

def test_game_substitution_touches_only_the_game_token():
    toks = sk.tokenize(TEMPLATE_LINE)
    out = sk.render_argv(toks, "ar25")
    assert out[out.index("--game") + 1] == "ar25"
    # everything else survives verbatim, in order
    assert [t for t in out if t != "ar25"] == [t for t in toks if t != "sk48"]
    assert out[0] == PY and out[1] == RUNNER, "python / runner path was disturbed"
    assert toks[toks.index("--game") + 1] == "sk48", "render_argv mutated its input"


def test_game_equals_form_is_also_substituted():
    toks = sk.tokenize(TEMPLATE_LINE.replace("--game sk48", "--game=sk48"))
    out = sk.render_argv(toks, "g50t")
    assert "--game=g50t" in out and "--game=sk48" not in out


def test_trailing_pid_is_stripped_but_a_trailing_option_value_is_not():
    toks = sk.tokenize(TEMPLATE_LINE + " 18324")
    assert sk.strip_trailing_pid(toks)[-2:] == ["--max-generations", "50"], (
        "the stray PID copied from a process listing reached the worker argv")
    clean = sk.tokenize(TEMPLATE_LINE)
    assert sk.strip_trailing_pid(clean) == clean, (
        "the real --max-generations value was mistaken for a PID")


def test_missing_game_token_is_a_clear_error():
    toks = sk.tokenize(TEMPLATE_LINE.replace("--game sk48 ", ""))
    with pytest.raises(ValueError, match="--game"):
        sk.render_argv(toks, "ar25")
    with pytest.raises(ValueError, match="--game"):
        sk.render_argv(sk.tokenize("%s %s --verbose --game" % (PY, RUNNER)), "ar25")


def test_load_template_reads_validates_and_strips(tmp_path):
    f = tmp_path / "sprint_argv.txt"
    f.write_text("\n" + TEMPLATE_LINE + " 4242\n", encoding="utf-8")
    toks = sk.load_template(str(f))
    assert toks[-1] == "50" and "--game" in toks
    f.write_text("%s %s --verbose\n" % (PY, RUNNER), encoding="utf-8")
    with pytest.raises(ValueError, match="--game"):
        sk.load_template(str(f))
    with pytest.raises(FileNotFoundError, match="sprint argv"):
        sk.load_template(str(tmp_path / "absent.txt"))


# ── the liveness predicate ───────────────────────────────────────────────────

def test_liveness_present_absent_wrong_game():
    procs = [
        (100, _cmd("sk48")),
        (101, _cmd("sk48")),                       # venv launcher + real interpreter
        (200, _cmd("ar25")),
        (300, PY + " tools/sprint_keeper.py sk48 ar25 g50t"),   # the keeper itself
        (301, PY + " some_other_script.py --game g50t"),         # not the runner
    ]
    assert sk.live_pids("sk48", procs) == [100, 101]
    assert sk.live_pids("ar25", procs) == [200]
    assert sk.live_pids("g50t", procs) == [], (
        "a non-runner python carrying --game g50t counted as the g50t worker")
    assert sk.live_pids("bp35", procs) == []


def test_liveness_is_whole_token_not_prefix():
    assert sk.is_worker_for(_cmd("sk48"), "sk4") is False
    assert sk.is_worker_for(_cmd("sk48"), "sk48x") is False
    assert sk.is_worker_for(_cmd("sk48"), "sk48") is True
    assert sk.is_worker_for(_cmd("sk48").replace("--game sk48", "--game=sk48"), "sk48") is True
    assert sk.is_worker_for("", "sk48") is False


# ── relaunch decision + logging ──────────────────────────────────────────────

class _Spawns:
    def __init__(self):
        self.calls = []
        self.modes = []      # the fleet_env each spawn was asked for, in order
        self.next_pid = 5000

    def __call__(self, game, argv, root, fleet_env=True):
        self.calls.append((game, list(argv), root))
        self.modes.append(fleet_env)
        self.next_pid += 1
        return self.next_pid


def test_absent_spawns_once_with_right_cwd_and_argv(tmp_path):
    template = sk.tokenize(TEMPLATE_LINE)
    spawns = _Spawns()
    log = tmp_path / "sprint_keeper.log"
    events = sk.run_once(["ar25"], template, [], root=str(tmp_path), log_path=str(log),
                         spawn_fn=spawns)
    assert len(spawns.calls) == 1
    game, argv, root = spawns.calls[0]
    assert game == "ar25" and root == str(tmp_path)
    assert argv[argv.index("--game") + 1] == "ar25" and argv[0] == PY
    assert events == [("ar25", "spawn", 5001)]


def test_present_does_not_spawn(tmp_path):
    template = sk.tokenize(TEMPLATE_LINE)
    spawns = _Spawns()
    events = sk.run_once(["ar25"], template, [(7, _cmd("ar25"))], root=str(tmp_path),
                         log_path=str(tmp_path / "k.log"), spawn_fn=spawns)
    assert spawns.calls == [] and events == []
    assert not (tmp_path / "k.log").exists(), "a no-op pass wrote a log line"


def test_spawn_uses_popen_detached_in_the_box_and_appends_worker_log(tmp_path, monkeypatch):
    """The real spawn(), with Popen faked: cwd is the game's box, stdout/stderr go to
    <box>/worker.log, the process is DETACHED (Ctrl-C on the keeper never reaches it)."""
    seen = {}

    class FakePopen:
        def __init__(self, argv, **kw):
            seen["argv"] = argv
            seen.update(kw)
            self.pid = 777

    monkeypatch.setattr(sk.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(sk, "DETACHED_PROCESS", 0x8)
    argv = sk.render_argv(sk.tokenize(TEMPLATE_LINE), "g50t")
    pid = sk.spawn("g50t", argv, root=str(tmp_path))
    assert pid == 777
    box = os.path.join(str(tmp_path), "g50t")
    assert seen["cwd"] == box and os.path.isdir(box)
    assert seen["creationflags"] == 0x8
    assert seen["stderr"] is sk.subprocess.STDOUT
    assert os.path.abspath(seen["stdout"].name) == os.path.join(box, "worker.log")
    assert seen["env"]["PYTHONPATH"] == sk.REDUX
    assert seen["argv"][seen["argv"].index("--game") + 1] == "g50t"
    assert "[KEEPER] relaunch" in open(os.path.join(box, "worker.log"), encoding="utf-8").read()


def test_log_line_format(tmp_path):
    assert sk.format_log_line("2026-08-21T10:00:00Z", "sk48", "spawn", 4321) == \
        "2026-08-21T10:00:00Z sk48 spawn 4321"
    assert sk.format_log_line("2026-08-21T10:00:00Z", "sk48", "spawn", 4321, "fleet-env") == \
        "2026-08-21T10:00:00Z sk48 spawn 4321 fleet-env"
    assert sk.format_log_line("2026-08-21T10:00:00Z", "sk48", "spawn", 4321, "bare-env") == \
        "2026-08-21T10:00:00Z sk48 spawn 4321 bare-env"
    log = tmp_path / "nested" / "sprint_keeper.log"
    sk.log_event("ar25", "spawn", 99, str(log))
    (line,) = log.read_text(encoding="utf-8").splitlines()
    utc, game, action, pid = line.split(" ")
    assert game == "ar25" and action == "spawn" and pid == "99"
    assert len(utc) == 20 and utc[10] == "T" and utc.endswith("Z"), utc


# ── fleet-env parity with the supervisor ─────────────────────────────────────

def _roster_from_source():
    """This test's OWN read of the GAMES literal from its home, tools/fleet_env.py --
    by ast, not by import -- so the parity assertion below is against the roster as
    written, not against any module's idea of it."""
    tree = ast.parse(open(FLEET_ENV_SRC, encoding="utf-8").read())
    lits = [ast.literal_eval(n.value) for n in tree.body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == "GAMES"]
    assert len(lits) == 1, "fleet_env.GAMES literal not found exactly once"
    return lits[0]


def _supervisor_assembly(game, root, recycles=0, redux=REPO):
    """THE ORACLE: swarm_supervisor.py lines 64-65 + 191-192 + 200 AS THEY STOOD
    BEFORE fleet_env existed (commit e1cce38), transcribed and frozen here. Every
    launcher -- the keeper, fleet_env_for, the supervisor's own spawn() -- must
    reproduce these bytes for `game` under `root`. Do not 'simplify' this to a call
    into tools/fleet_env: then the gate would compare the function with itself."""
    games = _roster_from_source()
    box = os.path.join(root, game)
    seed_dirs = [os.path.join(redux, ".runs", "compound2", "ego_fabric")] + \
                [os.path.join(root, g, "ego_fabric") for g in games]
    return {"OURO_FABRIC_SEEDS": ";".join(d for d in seed_dirs
                                          if d != os.path.join(box, "ego_fabric")),
            "LP_DRIVE_ARM": assign_arm(game, recycles),
            # D-11 (2026-08-21): the third variable, added to the oracle in lockstep
            # with fleet_env_for -- the headless render guard (arc_api_adapter).
            "OURO_HEADLESS": "1"}


def _keeper_imports():
    """(module, [names]) for every `from X import ...` / `import X` in the keeper."""
    tree = ast.parse(open(KEEPER_SRC, encoding="utf-8").read())
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            out.append((n.module or "", [a.name for a in n.names]))
        elif isinstance(n, ast.Import):
            out.extend((a.name, []) for a in n.names)
    return out


def test_the_keeper_never_imports_the_supervisor():
    """The keeper takes the roster and the assembly from tools/fleet_env.py -- the
    module the supervisor ALSO imports -- and never from the supervisor itself: the
    sprint watchdog must not depend on the full-fleet tool, only on what they share."""
    mods = [m for m, _names in _keeper_imports()]
    assert not any("swarm_supervisor" in m for m in mods), mods
    assert ("tools.fleet_env", ["GAMES", "SEED_SEP", "fleet_env_for"]) in _keeper_imports(), (
        "the keeper must import GAMES and fleet_env_for from tools.fleet_env")
    assert sk.GAMES is fe.GAMES and list(sk.GAMES) == _roster_from_source()
    assert len(sk.GAMES) == 25 and "sk48" in sk.GAMES


def test_the_keeper_carries_no_transcription():
    """THE THIRD GAP. Asserted on the shipped file: no local fleet_env_for /
    fleet_seed_dirs / supervisor_games, no ast read of the supervisor's source, and
    none of the assembly's ingredients ('ego_fabric', 'compound2', assign_arm) in
    the keeper's CODE (docstrings stripped -- prose may still explain the history)."""
    tree = ast.parse(open(KEEPER_SRC, encoding="utf-8").read())
    defs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for banned in ("fleet_env_for", "fleet_seed_dirs", "supervisor_games"):
        assert banned not in defs, "the keeper still defines its own %s" % banned
    assert "ast" not in [m for m, _n in _keeper_imports()], "the ast-roster hack is back"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef)) and ast.get_docstring(node):
            node.body = node.body[1:]
    code = ast.unparse(tree)
    for ingredient in ("ego_fabric", "compound2", "assign_arm", "SUPERVISOR_FILE",
                       "_GAMES_CACHE", "swarm_supervisor.py"):
        assert ingredient not in code, (
            "the keeper's code still carries the transcription ingredient %r" % ingredient)


def _import_supervisor_with_env_absent(monkeypatch):
    """Import tools.swarm_supervisor FRESH with .env unreadable and every side-effect
    primitive faked: open(.env) raises, os.makedirs / subprocess.Popen are Mocks,
    time.sleep raises (the loop must not start). Returns (module, makedirs, popen)."""
    real_open = builtins.open

    def no_env(path, *a, **kw):
        if str(path).endswith(".env"):
            raise FileNotFoundError(".env is absent in this test: %s" % path)
        return real_open(path, *a, **kw)

    makedirs, popen = mock.Mock(name="os.makedirs"), mock.Mock(name="subprocess.Popen")
    monkeypatch.setattr(builtins, "open", no_env)
    monkeypatch.setattr(os, "makedirs", makedirs)
    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(time, "sleep", mock.Mock(side_effect=AssertionError("the poll loop ran")))
    sys.modules.pop("tools.swarm_supervisor", None)
    return importlib.import_module("tools.swarm_supervisor"), makedirs, popen


def test_the_supervisor_imports_with_no_side_effects(monkeypatch):
    """CLEAN IMPORT. Before this gate, importing the supervisor read .env (raised if
    absent), made .runs/swarm, spawned all 25 workers and looped forever -- which is
    why the keeper transcribed it. Now: zero makedirs, zero Popen, no sleep, no .env
    read, and everything that DID those things sits in main() under __main__."""
    sup, makedirs, popen = _import_supervisor_with_env_absent(monkeypatch)
    assert makedirs.call_count == 0, makedirs.call_args_list
    assert popen.call_count == 0, popen.call_args_list
    assert sup.KEY is None, "the key was read at import time"
    assert sup.procs == {} and all(v["recycles"] == 0 for v in sup.stats.values())
    assert callable(sup.main) and callable(sup.read_arc_key)
    text = open(SUPERVISOR_SRC, encoding="utf-8").read()
    assert 'if __name__ == "__main__":\n    main()' in text
    # the side effects are all INSIDE main(): none at module level
    tree = ast.parse(text)
    top = ast.unparse(ast.Module(body=[n for n in tree.body
                                       if not isinstance(n, (ast.FunctionDef, ast.If))],
                                 type_ignores=[]))
    for effect in ("makedirs", "Popen", "read_arc_key(", "code_fingerprint(", "while True"):
        assert effect not in top, "module level still performs %r" % effect
    main_src = ast.unparse(next(n for n in tree.body
                                if isinstance(n, ast.FunctionDef) and n.name == "main"))
    for piece in ("read_arc_key()", "os.makedirs(ROOT", "for g in GAMES:", "spawn(g)",
                  "record_deploy(deployed_fp, 'initial')", "while True:", "HOLD_FILE",
                  "code_fingerprint()", "status.txt"):
        assert piece in main_src, "main() lost %r -- RUN behaviour changed" % piece
    # the supervisor takes the roster and the assembly from the same place the keeper does
    assert sup.GAMES is fe.GAMES and sup.fleet_env_for is fe.fleet_env_for


def _supervisor_spawn_env(sup, monkeypatch, game, root, recycles):
    """Run the supervisor's REAL spawn() for `game` under `root` with Popen faked
    and return the env it handed the worker. Box dir + worker.log are really made
    (under tmp), exactly as spawn() does them."""
    seen = {}

    class FakePopen:
        def __init__(self, argv, **kw):
            seen["argv"], seen["env"] = argv, dict(kw["env"])
            seen["cwd"] = kw["cwd"]
            self.pid = 4242

    monkeypatch.setattr(sup.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(sup, "ROOT", root)
    monkeypatch.setattr(sup, "KEY", "test-key-not-the-real-one")
    monkeypatch.setitem(sup.stats[game], "recycles", recycles)
    sup.spawn(game)
    _p, logf, _t0 = sup.procs.pop(game)
    logf.close()
    assert seen["cwd"] == os.path.join(root, game)
    assert seen["argv"][seen["argv"].index("--game") + 1] == game
    return seen["env"]


def test_fleet_env_parity_with_supervisor_assembly(tmp_path, monkeypatch):
    """THREE-WAY PARITY against the frozen oracle, for EVERY roster game on a
    constructed root (a few real box dirs, many absent): the supervisor's own spawn()
    env == fleet_env_for == the keeper's env, byte for byte, with the arm rotating
    identically through recycles 0..3 on the supervisor side."""
    root = str(tmp_path / "swarm")
    for g in ("sk48", "ar25", "g50t", "bp35"):
        os.makedirs(os.path.join(root, g, "ego_fabric"))
    games = _roster_from_source()
    sup = importlib.import_module("tools.swarm_supervisor")
    monkeypatch.delenv("OURO_FABRIC_SEEDS", raising=False)
    monkeypatch.delenv("LP_DRIVE_ARM", raising=False)
    # TEST-ISOLATION (2026-08-21): `added` below asks which keys the LAUNCHER inserts, so it
    # must not depend on what the ambient process environment already holds. Another gate
    # file imports evolution_runner at module level, and that import calls load_dotenv()
    # (evolution_runner.py:38), which puts ARC_API_KEY into os.environ for the whole pytest
    # process -- so this test passed alone and failed in the suite, deterministically, by
    # file order. Delete it here, as the two lines above already do for the fleet vars; the
    # launcher still supplies its own key, asserted below.
    monkeypatch.delenv("ARC_API_KEY", raising=False)
    for x in ("sk48", "ar25", "g50t", "wa30"):
        got = fe.fleet_env_for(x, root)
        assert got == _supervisor_assembly(x, root), x
        seeds = got["OURO_FABRIC_SEEDS"].split(";")
        assert os.path.join(root, x, "ego_fabric") not in seeds, "own box was cross-mounted"
        assert seeds[0] == os.path.join(REPO, ".runs", "compound2", "ego_fabric")
        assert seeds[1:] == [os.path.join(root, g, "ego_fabric") for g in games if g != x]
        assert len(seeds) == len(games), "one other box per roster game, plus compound2"
        assert got["LP_DRIVE_ARM"] == assign_arm(x, 0) and got["LP_DRIVE_ARM"] in ("fixed", "random", "lp")
        assert list(got) == ["OURO_FABRIC_SEEDS", "LP_DRIVE_ARM", "OURO_HEADLESS"], "insertion order changed"
        assert got["OURO_HEADLESS"] == "1", "D-11: every worker boots headless"
    for x in games:
        # 1) fleet_env_for == oracle, at every recycle count the supervisor will use
        for rc in range(4):
            assert fe.fleet_env_for(x, root, recycles=rc) == _supervisor_assembly(x, root, rc), (x, rc)
            assert fe.fleet_env_for(x, root, games, rc) == _supervisor_assembly(x, root, rc), (x, rc)
        # 2) the SUPERVISOR'S spawn() == oracle, same recycle counts, same fixed vars
        for rc in range(4):
            env = _supervisor_spawn_env(sup, monkeypatch, x, root, rc)
            exp = _supervisor_assembly(x, root, rc)
            assert env["OURO_FABRIC_SEEDS"] == exp["OURO_FABRIC_SEEDS"], (x, rc)
            assert env["LP_DRIVE_ARM"] == exp["LP_DRIVE_ARM"], (x, rc)
            assert env["PYTHONPATH"] == REPO and env["PYTHONDONTWRITEBYTECODE"] == "1"
            assert env["ARC_API_KEY"] == "test-key-not-the-real-one"
            added = [k for k in env if k not in os.environ]
            assert added in (["ARC_API_KEY", "PYTHONPATH", "OURO_FABRIC_SEEDS", "LP_DRIVE_ARM",
                              "OURO_HEADLESS"],
                             ["ARC_API_KEY", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
                              "OURO_FABRIC_SEEDS", "LP_DRIVE_ARM", "OURO_HEADLESS"]), (
                "the env's key insertion order changed: %r" % added)
        # 3) the KEEPER'S env == oracle at recycles=0 (it keeps no recycle stats)
        kenv = sk._worker_env(x, root, fleet_env=True)
        exp0 = _supervisor_assembly(x, root, 0)
        assert kenv["OURO_FABRIC_SEEDS"] == exp0["OURO_FABRIC_SEEDS"], x
        assert kenv["LP_DRIVE_ARM"] == exp0["LP_DRIVE_ARM"] == assign_arm(x, 0), x
        assert kenv["PYTHONPATH"] == REPO and kenv["PYTHONDONTWRITEBYTECODE"] == "1"
    assert sup.procs == {}, "the parity run left a worker handle behind"


def test_spawn_default_is_fleet_env_and_says_so(tmp_path, monkeypatch):
    seen = {}

    class FakePopen:
        def __init__(self, argv, **kw):
            seen.update(kw)
            self.pid = 778

    monkeypatch.setattr(sk.subprocess, "Popen", FakePopen)
    monkeypatch.delenv("OURO_FABRIC_SEEDS", raising=False)
    monkeypatch.delenv("LP_DRIVE_ARM", raising=False)
    root = str(tmp_path)
    sk.spawn("ar25", sk.render_argv(sk.tokenize(TEMPLATE_LINE), "ar25"), root=root)
    env = seen["env"]
    expect = _supervisor_assembly("ar25", root)
    assert env["OURO_FABRIC_SEEDS"] == expect["OURO_FABRIC_SEEDS"]
    assert env["LP_DRIVE_ARM"] == expect["LP_DRIVE_ARM"]
    assert env["PYTHONPATH"] == sk.REDUX and env["PYTHONDONTWRITEBYTECODE"] == "1"
    wl = open(os.path.join(root, "ar25", "worker.log"), encoding="utf-8").read()
    assert "fleet-env" in wl and "LP_DRIVE_ARM=%s" % expect["LP_DRIVE_ARM"] in wl
    assert "recycles=0" in wl, "the arm's recycles=0 basis must be stated in the evidence"


def test_no_fleet_env_sets_neither_var_and_logs_bare(tmp_path, monkeypatch):
    seen = {}

    class FakePopen:
        def __init__(self, argv, **kw):
            seen.update(kw)
            self.pid = 779

    monkeypatch.setattr(sk.subprocess, "Popen", FakePopen)
    monkeypatch.delenv("OURO_FABRIC_SEEDS", raising=False)
    monkeypatch.delenv("LP_DRIVE_ARM", raising=False)
    root = str(tmp_path)
    sk.spawn("ar25", sk.render_argv(sk.tokenize(TEMPLATE_LINE), "ar25"), root=root,
             fleet_env=False)
    env = seen["env"]
    assert "OURO_FABRIC_SEEDS" not in env and "LP_DRIVE_ARM" not in env
    assert env["PYTHONPATH"] == sk.REDUX, "the bare mode still carries the import path"
    wl = open(os.path.join(root, "ar25", "worker.log"), encoding="utf-8").read()
    assert "bare-env" in wl and "fleet-env" not in wl
    # the keeper log line carries the mode, in both directions
    spawns = _Spawns()
    log = tmp_path / "k.log"
    sk.run_once(["ar25"], sk.tokenize(TEMPLATE_LINE), [], root=root, log_path=str(log),
                spawn_fn=spawns, fleet_env=False)
    sk.run_once(["g50t"], sk.tokenize(TEMPLATE_LINE), [], root=root, log_path=str(log),
                spawn_fn=spawns)
    assert spawns.modes == [False, True]
    lines = [ln.split(" ")[1:] for ln in log.read_text(encoding="utf-8").splitlines()]
    assert lines == [["ar25", "spawn", "5001", "bare-env"], ["g50t", "spawn", "5002", "fleet-env"]]


def test_cli_flag_routes_the_mode_and_default_is_fleet(tmp_path, monkeypatch):
    """`--no-fleet-env` is the only way to bare mode; a bare argv is fleet mode."""
    seen = []
    # NO .runs. This test drives the REAL main(), which takes a seq-watermark tick per
    # pass (tools/watermark.py) against the module-level ROOT -- the live fleet. Every
    # other side effect main() has is already patched out here for the same reason; the
    # tick is patched out by pointing ROOT at tmp (where no box has a fabric, so the
    # writer creates nothing at all). The tick itself is gated in test_seq_watermark.py.
    monkeypatch.setattr(sk, "ROOT", str(tmp_path / "swarm"))
    monkeypatch.setattr(sk, "load_template", lambda: sk.tokenize(TEMPLATE_LINE))
    monkeypatch.setattr(sk, "list_python_processes", lambda: [])
    monkeypatch.setattr(sk, "run_once", lambda *a, **kw: seen.append(kw.get("fleet_env")))
    monkeypatch.setattr(sk, "log_event", lambda *a, **kw: seen.append(("log", kw.get("mode"))))
    assert sk.main(["--once", "ar25"]) == 0
    assert sk.main(["--once", "--no-fleet-env", "ar25"]) == 0
    assert [s for s in seen if not isinstance(s, tuple)] == [True, False]
    assert [s for s in seen if isinstance(s, tuple) and s[1]] == \
        [("log", "fleet-env"), ("log", "bare-env")], "keeper_start must declare its mode"


# ── R4 on the three-game sprint ──────────────────────────────────────────────

def test_r4_three_game_sprint(tmp_path):
    template = sk.tokenize(TEMPLATE_LINE)
    games = ["sk48", "ar25", "g50t"]
    log = tmp_path / "sprint_keeper.log"
    procs = [
        (11, _cmd("sk48")),                                   # live
        (12, _cmd("sk48")),                                   # ...and its launcher
        (21, _cmd("bp35")),                                   # a worker, wrong game
        (31, PY + " tools/sprint_keeper.py sk48 ar25 g50t"),  # the keeper: not a worker
    ]
    spawns = _Spawns()
    events = sk.run_once(games, template, procs, root=str(tmp_path), log_path=str(log),
                         spawn_fn=spawns)
    # KNOWN-POSITIVE: the two absent games, once each, own box, own --game
    assert [c[0] for c in spawns.calls] == ["ar25", "g50t"]
    for game, argv, _root in spawns.calls:
        assert argv[argv.index("--game") + 1] == game
    # KNOWN-NEGATIVE: the live game was left alone
    assert "sk48" not in [c[0] for c in spawns.calls]
    assert [(g, a) for g, a, _p in events] == [("ar25", "spawn"), ("g50t", "spawn")]
    lines = log.read_text(encoding="utf-8").splitlines()
    assert [ln.split(" ")[1:] for ln in lines] == [["ar25", "spawn", "5001", "fleet-env"],
                                                   ["g50t", "spawn", "5002", "fleet-env"]]
    assert spawns.modes == [True, True], "the default pass did not ask for fleet-env"
    # STABILITY: once the relaunched workers show up, the next pass does nothing
    procs2 = procs + [(5001, _cmd("ar25")), (5002, _cmd("g50t"))]
    events2 = sk.run_once(games, template, procs2, root=str(tmp_path), log_path=str(log),
                          spawn_fn=spawns)
    assert events2 == [] and len(spawns.calls) == 2, "a complete fleet was relaunched again"
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2


def test_spawn_failure_is_logged_not_raised(tmp_path):
    """One game's bad spawn must not take the other two games' keeper down with it."""
    def boom(game, argv, root, fleet_env=True):
        raise OSError("no such python")
    log = tmp_path / "k.log"
    events = sk.run_once(["sk48"], sk.tokenize(TEMPLATE_LINE), [], root=str(tmp_path),
                         log_path=str(log), spawn_fn=boom)
    assert events == [("sk48", "spawn_failed:OSError", "-")]
    assert log.read_text(encoding="utf-8").split(" ")[2] == "spawn_failed:OSError"


def test_the_keeper_does_not_carry_supervisor_machinery():
    """No kills, no deploys, no HOLD, no fingerprinting -- asserted on the shipped file,
    not on this test's idea of it."""
    text = open(os.path.join(REPO, "tools", "sprint_keeper.py"), encoding="utf-8").read()
    for forbidden in ("taskkill", "code_fingerprint", "HOLD_FILE", ".kill(", ".terminate(",
                      "deploys.jsonl", "record_deploy"):
        assert forbidden not in text, "sprint_keeper grew supervisor machinery: %r" % forbidden
    assert "DETACHED_PROCESS" in text and "swarm_supervisor" in text
