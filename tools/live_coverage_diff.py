"""RUNG 0c, LAYER 3: THE LIVE-RUN COVERAGE DIFF -- the empirical half.

The deterministic gate (tests/gate/test_wiring_registry.py) proves a LIVE
receipt's line exists and its symbol is referenced from production. It CANNOT
prove the branch ever runs: ResidualRouter() built minerless has a real line,
a real reference, and a dead organ inside it. This tool closes that gap:

  1. run a BOUNDED SYNTHETIC live-shaped episode through the REAL
     CognitiveLoop (the hermetic drive pattern of
     tests/gate/test_e2e_pipeline.py: tmp cwd, 64x64 synthetic frames, seeded
     RNG, a deterministic clickable world, an independent mover, a level-up;
     NO network, NO real game) under coverage.py branch coverage, scoped to
     engines/egocentric/* + cognitive_loop.py;
  2. diff the executed lines against record/canon/WIRING_REGISTRY.md: every LIVE entry
     whose claimed call-site line never executed is reported
     SEVERED-EMPIRICAL;
  3. print the rung-0c line the proctor reads:  severed count=N

MODES. The synthetic episode is the CI-SAFE FLOOR: deterministic, hermetic,
seconds-scale -- but it cannot reach every deep branch (e.g. the plan path
needs verified atoms; the mute-probe path needs a demoted seeded goal), so a
SEVERED-EMPIRICAL report here means "not exercised by the floor episode",
which is a superset of "dead". The STRONGER MODE is a REAL-GAME run,
operator-invoked:

    coverage run --branch <the real player entrypoint> ...
    python tools/live_coverage_diff.py --coverage-file .coverage

which diffs the same registry against branches a real episode actually took;
only that mode can clear the deep-path entries. Registry rows already marked
SEVERED are NOT counted here -- they are declared, the deterministic gate
polices them; this tool polices the LIVE claims.

Usage:
    python tools/live_coverage_diff.py                # synthetic floor run
    python tools/live_coverage_diff.py --steps 36 --episodes 2
    python tools/live_coverage_diff.py --coverage-file .coverage   # real-run diff
"""
from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
import tempfile
from typing import Dict, List, NamedTuple, Optional, Set

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.wiring_receipts import parse_site  # noqa: E402  -- after the bootstrap

REGISTRY_DEFAULT = os.path.join(REPO, "record", "canon", "WIRING_REGISTRY.md")

# The measured scope (the empirical gate's universe). Entries whose claimed
# site lies outside it are reported UNMEASURED, never SEVERED-EMPIRICAL.
SCOPE_INCLUDE = [
    os.path.join(REPO, "cognitive_loop.py"),
    os.path.join(REPO, "engines", "egocentric", "*.py"),
]

# A claimed line may be the head of a multi-line call; coverage records the
# statement head. Tolerate a small window around the claimed line.
LINE_SLACK = 3


def _ensure_coverage():
    try:
        import coverage  # noqa: F401
    except ImportError:
        print("[live-coverage-diff] coverage.py absent -- installing into "
              "this interpreter's environment (%s)" % sys.executable)
        rc = subprocess.call([sys.executable, "-m", "pip", "install",
                              "coverage"])
        if rc != 0:
            raise SystemExit(
                "coverage.py is not installed and pip install failed "
                "(rc=%d). Install it manually: %s -m pip install coverage"
                % (rc, sys.executable)) from None
    import coverage
    return coverage


class Entry(NamedTuple):
    name: str
    symbol: str
    site_file: str
    site_line: int
    status: str
    note: str


def parse_registry(path: str) -> List[Entry]:
    if not os.path.exists(path):
        raise SystemExit("registry not found: %s" % path)
    entries: List[Entry] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != 6:
                continue
            name, symbol, site, status, _date, note = cells
            if name in ("name", "") or set(name) <= {"-", ":", " "}:
                continue
            if ":" not in site:
                continue
            # Both cell forms (PREREG_SYMBOL_RECEIPTS.md §1): the fingerprint
            # `file:ENCLOSING/KIND:NAME#ORDINAL@LINE` and, until the last row
            # leaves it, the old `file:line`. The empirical layer wants a LINE
            # to intersect with coverage, and the fingerprint's @LINE courtesy
            # is that line -- kept exact by `wiring_receipts refresh`, and now
            # pointing at the anchored node itself rather than at whatever was
            # within ±30 of it.
            parsed = parse_site(site)
            entries.append(Entry(name, symbol, parsed.file, parsed.line,
                                 status, note))
    return entries


# ─────────────────────────────────────────────────────────────────────────────
# The bounded synthetic live-shaped episode (hermetic drive pattern of
# tests/gate/test_e2e_pipeline.py -- tmp cwd, synthetic frames, NO network).
# ─────────────────────────────────────────────────────────────────────────────

class SynthEnv:
    """Deterministic toy world on a 64x64 board (test_e2e_pipeline.SynthEnv).

    Click on (x, y): if cells (y, x) and (y, x+1) are both 0 they become 5
    (the deterministic 2-cell transform the mint can learn); anything else is
    a dead click. Independent mover: colour 7 at row 40 advances one column
    every even step (world-caused change). Movement never changes the board.
    """

    def __init__(self):
        import numpy as np
        self.np = np
        self.board = np.zeros((64, 64), dtype=int)
        self.step = 0
        self.mover = [40, 5]
        self.board[40, 5] = 7

    def apply(self, action, data):
        pre = self.board.copy()
        if self.step % 2 == 0:
            r, c = self.mover
            self.board[r, c] = 0
            c2 = (c + 1) % 60
            self.mover = [r, c2]
            self.board[r, c2] = 7
        if action == 6 and data:
            x, y = int(data["x"]), int(data["y"])
            if (0 <= y < 64 and 0 <= x < 63
                    and self.board[y, x] == 0 and self.board[y, x + 1] == 0):
                self.board[y, x] = 5
                self.board[y, x + 1] = 5
        self.step += 1
        changed = bool((self.board != pre).any())
        return self.board.copy(), changed


def _run_one_episode(game_id: str, n_steps: int, seed: int) -> None:
    """One full episode through the REAL CognitiveLoop in the CURRENT cwd
    (books persist on disk, so a second episode hydrates/consumes them --
    reaching the seed/drain/verified wires a cold first episode cannot)."""
    import io
    import types
    from contextlib import redirect_stdout

    random.seed(seed)
    from cognitive_loop import CognitiveLoop
    loop = CognitiveLoop()
    loop.start_game(game_id, [1, 2, 3, 4, 5, 6], max_actions=500)
    env = SynthEnv()
    obs = types.SimpleNamespace(levels_completed=0)
    frame = env.board.copy()
    buf = io.StringIO()
    with redirect_stdout(buf):
        for i in range(n_steps):
            if i == n_steps - 1 and hasattr(loop, "_plan_gate"):
                # cadence fast-forward: the 200th-cycle narration site fires
                loop._plan_gate["cycles"] = 199
            action, data, _cf = loop.cycle(frame, obs)
            if i % 7 == 3:
                # a forced movement action banks move affordances; the bet
                # book's committed != executed VOID law is exercised too
                action, data = 1 + (i // 7) % 5, None
                loop._last_action_info = {
                    "type": action, "x": None, "y": None,
                    "frame_changed": False, "score_delta": 0.0,
                    "level_changed": False,
                    "consecutive_no_change": loop._consecutive_no_change,
                    "consecutive_same_action": 0,
                }
            post, changed = env.apply(action, data)
            level_changed = (i == n_steps - 1)
            if level_changed:
                obs.levels_completed = 1
            loop.record_result(post_frame=post, frame_changed=changed,
                               score_delta=0.0, level_changed=level_changed,
                               new_level=2 if level_changed else 0)
            frame = post
        loop.end_game()


def run_synthetic(coverage_mod, n_steps: int, n_episodes: int) -> object:
    cov = coverage_mod.Coverage(branch=True, include=SCOPE_INCLUDE,
                                data_file=None)
    run_dir = tempfile.mkdtemp(prefix="live_cov_diff_")
    cwd = os.getcwd()
    os.chdir(run_dir)
    try:
        cov.start()
        try:
            for ep in range(n_episodes):
                _run_one_episode("live_cov_g1", n_steps, seed=20260816 + ep)
        finally:
            cov.stop()
    finally:
        os.chdir(cwd)
    return cov.get_data()


def _executed_lines(data, abspath: str) -> Set[int]:
    lines = data.lines(abspath)
    return set(lines or ())


def diff(entries: List[Entry], data) -> Dict[str, List[Entry]]:
    """LIVE entries only: EXECUTED / SEVERED-EMPIRICAL / UNMEASURED."""
    scope_prefixes = ("cognitive_loop.py", "engines/egocentric/")
    out: Dict[str, List[Entry]] = {"EXECUTED": [], "SEVERED-EMPIRICAL": [],
                                   "UNMEASURED": []}
    for e in entries:
        if e.status != "LIVE":
            continue
        if not e.site_file.startswith(scope_prefixes):
            out["UNMEASURED"].append(e)
            continue
        abspath = os.path.abspath(os.path.join(REPO, e.site_file))
        executed = _executed_lines(data, abspath)
        window = range(e.site_line - LINE_SLACK, e.site_line + LINE_SLACK + 1)
        hit = any(ln in executed for ln in window)
        out["EXECUTED" if hit else "SEVERED-EMPIRICAL"].append(e)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", default=REGISTRY_DEFAULT)
    ap.add_argument("--steps", type=int, default=36,
                    help="cycles per synthetic episode (bounded; default 36)")
    ap.add_argument("--episodes", type=int, default=2,
                    help="synthetic episodes (2: the second hydrates the "
                         "first's books, reaching seed/drain/verified wires)")
    ap.add_argument("--coverage-file", default=None,
                    help="diff an EXISTING coverage data file (the stronger, "
                         "operator-invoked real-game mode) instead of "
                         "running the synthetic floor episode")
    args = ap.parse_args(argv)

    entries = parse_registry(args.registry)
    live = [e for e in entries if e.status == "LIVE"]
    declared_severed = [e for e in entries if e.status == "SEVERED"]
    if not live:
        raise SystemExit("registry holds no LIVE entries: %s" % args.registry)

    coverage_mod = _ensure_coverage()
    if args.coverage_file:
        cov = coverage_mod.Coverage(data_file=args.coverage_file)
        cov.load()
        data = cov.get_data()
        mode = "real-run (%s)" % args.coverage_file
    else:
        data = run_synthetic(coverage_mod, args.steps, args.episodes)
        mode = ("synthetic floor (%d episode(s) x %d steps, hermetic, "
                "no network)" % (args.episodes, args.steps))

    result = diff(entries, data)
    print("[live-coverage-diff] mode: %s" % mode)
    print("[live-coverage-diff] registry: %d entries -- %d LIVE / %d "
          "declared SEVERED (declared rows are the deterministic gate's "
          "jurisdiction, not counted below)"
          % (len(entries), len(live), len(declared_severed)))
    for e in result["EXECUTED"]:
        print("  EXECUTED           %-24s %s:%d"
              % (e.name, e.site_file, e.site_line))
    for e in result["UNMEASURED"]:
        print("  UNMEASURED         %-24s %s:%d (outside the measured scope "
              "engines/egocentric + cognitive_loop.py)"
              % (e.name, e.site_file, e.site_line))
    for e in result["SEVERED-EMPIRICAL"]:
        print("  SEVERED-EMPIRICAL  %-24s %s:%d -- receipt exists, symbol "
              "referenced, line NEVER EXECUTED in this episode"
              % (e.name, e.site_file, e.site_line))
    n = len(result["SEVERED-EMPIRICAL"])
    # THE RUNG-0c LINE (the proctor reads only this):
    print("severed count=%d" % n)
    if n and not args.coverage_file:
        print("[live-coverage-diff] NOTE: the synthetic floor cannot reach "
              "every deep branch; re-check the flagged entries against a "
              "real-game run (--coverage-file) before ruling them dead.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
