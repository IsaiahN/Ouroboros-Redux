"""D-5 BASELINE WRAPPER — profile a slow worker for a FIXED WINDOW, then dump and exit.

cn04 at 0.1 actions/min cannot finish a generation inside any sane profiling window, and
cProfile writes nothing on a kill. So: run the worker in-process, and a timer dumps the
stats and exits cleanly at PROFILE_SECONDS regardless of where the episode is.

PROPORTIONS, NOT ABSOLUTES (Seat 4): cProfile inflates absolute times; the deliverable is
the dominant term's SHARE. No threshold may be set against these numbers — F2's 5% cap is
measured against un-profiled wall-clock, never against this.

Usage: python tools/d5_profile_wrapper.py <game> <seconds> <out.pstats>  (cwd = the box)
"""
from __future__ import annotations

import cProfile
import os
import runpy
import sys
import threading


def main() -> None:
    game, seconds, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    runner = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "evolution_runner.py")
    pr = cProfile.Profile()

    def dump_and_exit() -> None:
        pr.disable()
        try:
            pr.dump_stats(out)
            print("[D5-PROFILE] stats dumped to", out, flush=True)
        finally:
            os._exit(0)   # the worker has no clean mid-episode stop; the stats are the point

    sys.argv = [runner, "--mode", "offline", "--game", game,
                "--population", "1", "--agents-per-gen", "1",
                "--games-per-gen", "1", "--max-generations", "1"]
    threading.Timer(seconds, dump_and_exit).start()
    pr.enable()
    try:
        runpy.run_path(runner, run_name="__main__")
    finally:
        dump_and_exit()

if __name__ == "__main__":
    main()
