"""ci_run.py -- CI / unattended entrypoint for the Redux composer agent.

Runs the ACTUAL submission agent (integrated_agent.MyAgent) live against the ARC-AGI-3 online API and
writes results to results/<run_tag>/ so a scheduled GitHub Actions run leaves a durable, reviewable trace
that the proctor (in a Cowork session) can clone and reason over. This is the clean unattended loop:
the key lives as an Actions SECRET, injected natively into the runner as $ARC_API_KEY, and NEVER leaves
GitHub's environment or gets printed. The agent runs where the key already is; the proctor consumes only
the committed OUTPUTS (never the key).

Mode:
  free  (default) -- keep ONE agent alive across deaths/restarts up to CAP actions, per game. Cross-life
                     memory (cmap, refutation_ledger, persistent_model, self-assess) persists in
                     GLOBAL_KNOWLEDGE across restarts -> the 'evolve across generations' mode. This is the
                     valuable mode for depth on a single game (ls20).
  sweep           -- play each game once through run_online (breadth over the game list).

Config (all via env, all with sane defaults):
  ARC_API_KEY    the online key. REQUIRED. env-only, never written or printed.
  OURO_GAMES     comma-separated game ids       (default "ls20")
  OURO_MODE      "free" | "sweep"                (default "free")
  OURO_CAP       actions cap per game (free)     (default 1500)
  OURO_WALL      wall-seconds cap per game       (default 1200)
  OURO_RUN_TAG   results subdir name             (default: GH run number, else epoch)

Writes:
  results/<run_tag>/summary.json          machine-readable outcome for every game
  results/<run_tag>/<game>.stream.log     the agent's own DSL narration (text; key never appears)

Nothing else is written to the tree. Recordings stay in the runner and are discarded.
"""
import os, sys, time, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- config -----------------------------------------------------------------
KEY = os.environ.get("ARC_API_KEY", "")
if not KEY:
    print("FATAL: ARC_API_KEY not set (expected as a GitHub Actions secret, injected env-only).",
          file=sys.stderr)
    sys.exit(2)

GAMES = [g.strip() for g in os.environ.get("OURO_GAMES", "ls20").split(",") if g.strip()]
MODE  = os.environ.get("OURO_MODE", "free").strip().lower()
CAP   = int(os.environ.get("OURO_CAP", "1500"))
WALL  = int(os.environ.get("OURO_WALL", "1200"))
RUN_TAG = (os.environ.get("OURO_RUN_TAG")
           or os.environ.get("GITHUB_RUN_NUMBER")
           or str(int(time.time())))

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", RUN_TAG)
os.makedirs(OUT_DIR, exist_ok=True)

# ---- tee the agent's DSL narration into a per-game stream --------------------
import objective_validator as OV
_orig_emit = OV._emit
_stream = {"fh": None, "n": 0}

def _tee(adapter, step, once_key=None):
    fh = _stream["fh"]
    if fh is not None:
        try:
            lvl = getattr(getattr(adapter, "_obs", None), "levels_completed", None)
            _stream["n"] += 1
            fh.write("[#%d lvl=%s] %s\n" % (_stream["n"], lvl, step))
        except Exception:
            pass
    return _orig_emit(adapter, step, once_key=once_key)

OV._emit = _tee

# ---- SDK / agent ------------------------------------------------------------
import arc_agi
try:
    from arc_agi.base import OperationMode
except Exception:
    from arc_agi import OperationMode
import online_harness as OH
OH._ensure_agents_stub()
import integrated_agent as IA
from arcengine import GameAction
import logging
log = logging.getLogger("ci"); logging.basicConfig(level=logging.WARNING)


def _terminal(fr):
    st = str(getattr(fr, "state", "") or "")
    return ("GAME_OVER" in st) or ("WIN" in st) or ("NOT_STARTED" in st) or ("NOT_PLAYED" in st)


def _free_run(arc, sc, game):
    """One agent, kept alive across deaths/restarts up to CAP actions. Returns a summary dict."""
    fh = open(os.path.join(OUT_DIR, "%s.stream.log" % game), "w", buffering=1)
    _stream["fh"] = fh; _stream["n"] = 0
    url = "https://arcprize.org/scorecards/%s" % sc
    env = arc.make(game, scorecard_id=sc, save_recording=True)
    try:
        agent = IA.MyAgent(game_id=game, card=sc)
    except Exception:
        agent = IA.MyAgent(game_id=game)

    t0 = time.time(); deadline = t0 + WALL
    o = OH._retry_none(lambda: env.reset(), tries=5, base=1.2)
    frames = [o] if o is not None else []
    acts = deaths = max_level = 0; gens = 1

    while acts < CAP and time.time() < deadline:
        if o is None:
            deaths += 1; gens += 1
            o = OH._retry_none(lambda: env.reset(), tries=3, base=0.8)
            frames = [o] if o is not None else []
            continue
        try:
            lv = int(getattr(o, "levels_completed", 0) or 0)
            max_level = max(max_level, lv)
        except Exception:
            pass
        if _terminal(o):
            deaths += 1; gens += 1
            o = OH._retry_none(lambda: env.step(GameAction.RESET), tries=3, base=0.8)
            if o is None:
                o = OH._retry_none(lambda: env.reset(), tries=3, base=0.8)
            frames = [o] if o is not None else []
            continue
        action = agent.choose_action(frames, o)
        if action is None:
            o = OH._retry_none(lambda: env.step(GameAction.RESET), tries=2, base=0.8)
            frames = [o] if o is not None else []
            continue
        reasoning = getattr(action, "reasoning", None)
        step_data = None
        if getattr(action, "value", None) == 6:
            _ad = getattr(action, "action_data", None)
            if _ad is not None:
                step_data = {"x": int(getattr(_ad, "x", 0) or 0), "y": int(getattr(_ad, "y", 0) or 0)}
        o = OH._retry_none(lambda: env.step(action, data=step_data, reasoning=reasoning), tries=3, base=0.6)
        acts += 1
        if o is not None:
            frames.append(o); frames = frames[-16:]
        if acts % 100 == 0:
            print("  [%s] %d actions, max_level=%d, deaths=%d, %ds"
                  % (game, acts, max_level, deaths, round(time.time() - t0)), flush=True)

    dt = round(time.time() - t0)
    fh.write("\n=== %d actions | max_level %d | deaths %d | gens %d | %ds ===\n"
             % (acts, max_level, deaths, gens, dt))
    emits = _stream["n"]
    fh.close(); _stream["fh"] = None
    return dict(game=game, mode="free", actions=acts, max_level=max_level, deaths=deaths,
                gens=gens, seconds=dt, emits=emits, scorecard=url)


def main():
    arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE, arc_api_key=KEY, logger=log)
    sc = arc.open_scorecard(tags=["ouroboros", "redux", "ci", MODE])
    url = "https://arcprize.org/scorecards/%s" % sc
    print("=== CI RUN  mode=%s  games=%s  cap=%d  wall=%ss  run_tag=%s ==="
          % (MODE, ",".join(GAMES), CAP, WALL, RUN_TAG), flush=True)
    print("scorecard:", url, flush=True)

    summaries = []
    try:
        if MODE == "sweep":
            # one pass per game -- reuse the harness path directly for breadth
            for game in GAMES:
                fh = open(os.path.join(OUT_DIR, "%s.stream.log" % game), "w", buffering=1)
                _stream["fh"] = fh; _stream["n"] = 0
                r = OH.play_game_submission(arc, game, sc, log, wall_cap_s=WALL, save_recording=True)
                fh.close(); _stream["fh"] = None
                r = dict(r); r["mode"] = "sweep"; r["emits"] = _stream["n"]; r["scorecard"] = url
                summaries.append(r)
                print("  [%s] level=%s outcome=%s %ss"
                      % (game, r.get("max_level"), r.get("outcome"), r.get("seconds")), flush=True)
        else:
            for game in GAMES:
                summaries.append(_free_run(arc, sc, game))
    finally:
        try:
            final = arc.close_scorecard(sc)
            score = getattr(final, "score", None)
        except Exception:
            score = None

    out = dict(run_tag=RUN_TAG, mode=MODE, scorecard=url, score=score,
               games=GAMES, cap=CAP, wall=WALL, results=summaries)
    with open(os.path.join(OUT_DIR, "summary.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2), flush=True)


if __name__ == "__main__":
    main()
