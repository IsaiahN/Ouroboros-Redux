"""THE OFFLINE CONTRAST for the band mask across a restart — the leg of PREREG_the_mask_after_restart with no
confound in it.

The two live arms cannot answer the diagnostic question. The mask feeds `frozen()`, `escalate()`, `is_null()` and
`_act_directional`, so the moment it changes the agent chooses differently and the arms stop looking at the same
boards. This tool removes the agent entirely: it takes ONE recorded frame sequence and feeds it to two
`EngagementMeter`s, one at `keep` and one at `clear`, counting the steps at which a band was masked. Same frames,
same order, same restarts, one difference.

It measures the INSTRUMENT, not the agent, and it may not be cited as evidence about behaviour.

    PYTHONPATH=src python3.12 tools/replay_mask.py recordings/<sid>/*.jsonl
"""
from __future__ import annotations
import json
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np

from newhorse.redux_arch import engagement as E
from newhorse.redux_arch.engagement import EngagementMeter


def _grid(frame) -> np.ndarray:
    """Same rule as `arc3_env._grid_from_obs`: the LAST frame of a stack. Stated here rather than imported so the
    replay cannot silently drift from what the policy saw if either side changes."""
    a = np.asarray(frame)
    while a.ndim > 2:
        a = a[-1]
    return a


def _steps(path: str) -> List[Tuple[np.ndarray, str]]:
    """(frame, label) per recorded observation, with the label the policy would have carried: the action that
    PRODUCED this frame, or `RESET` for a restart frame. `EngagementMeter.observe` ignores RESET-labelled frames for
    the response charge but still appends them to the history, exactly as it does live."""
    out: List[Tuple[np.ndarray, str]] = []
    with open(path) as fh:
        for line in fh:
            d = json.loads(line)["data"]
            raw = str((d.get("action_input") or {}).get("id") or "?")
            lbl = "RESET" if raw.upper().startswith("RESET") else ("A" + raw[6:] if raw.startswith("ACTION") else "?")
            out.append((_grid(d["frame"]), lbl))
    return out


def replay(path: str) -> Dict[str, object]:
    steps = _steps(path)
    res: Dict[str, object] = {"game": path.split("/")[-1].split("-")[0], "frames": len(steps)}
    for mode in ("keep", "clear"):
        old = E.MASK_ON_RESTART
        E.MASK_ON_RESTART = mode
        try:
            m = EngagementMeter()
            banded = charged = live = band_only = still = sub = 0
            first_blind: Optional[int] = None
            for i, (g, lbl) in enumerate(steps):
                if lbl == "RESET" and i > 0:
                    m.note_restart()                       # the same call site the policy makes, one step earlier
                prev = m._frames[-1] if m._frames else None
                m.observe(g, lbl)
                if prev is None or lbl in ("RESET", "?") or prev.shape != g.shape:
                    continue
                charged += 1
                mask = m.mask()
                on = bool(mask.shape == g.shape and mask.any())
                banded += int(on)
                if not on and first_blind is None and i > 0:
                    first_blind = i
                eff = mask if mask.shape == g.shape else np.zeros(g.shape, dtype=bool)
                raw = int((prev != g).sum())
                cells = int(((prev != g) & ~eff).sum())
                if raw == 0:
                    still += 1
                elif cells == 0:
                    band_only += 1
                elif cells < E.MIN_CELLS:
                    sub += 1
                else:
                    live += 1
            res[mode] = dict(charged=charged, banded=banded, still=still, band_only=band_only, sub=sub, live=live)
        finally:
            E.MASK_ON_RESTART = old
    return res


def main(paths: List[str]) -> None:
    print("=== OFFLINE MASK CONTRAST (same frames, two meters; no agent in the loop) ===")
    print("  %-8s %7s %7s | %6s %6s | %6s %6s | %6s %6s" %
          ("game", "frames", "charged", "band:K", "band:C", "live:K", "live:C", "bnly:K", "bnly:C"))
    tot = {"keep": 0, "clear": 0}
    for p in paths:
        r = replay(p)
        k, c = r["keep"], r["clear"]
        tot["keep"] += k["banded"]; tot["clear"] += c["banded"]
        print("  %-8s %7d %7d | %6d %6d | %6d %6d | %6d %6d" %
              (r["game"], r["frames"], k["charged"], k["banded"], c["banded"],
               k["live"], c["live"], k["band_only"], c["band_only"]))
    print("  TOTAL banded  keep=%d  clear=%d  (delta %+d)" % (tot["keep"], tot["clear"], tot["clear"] - tot["keep"]))


if __name__ == "__main__":
    main(sys.argv[1:])
