"""level_segmenter.py -- identify each level's TRUE board from a frame stream, robustly, for ANY number of levels.

THE BUG THIS GENERALISES AWAY: when a level is cleared, the frame at the moment the `levels_completed`
counter increments is the WIN-STATE of the level just finished -- NOT the new level. The new level's board
arrives on the NEXT frame, as a full-board RELOAD (a large fraction of the play area changes at once).
Selecting "the first frame at the new counter value" therefore grabs the wrong board (the old win-state).
Observed: counter-flip frame diff ~173; the reload one frame later ~2894 (of 4096).

THE GENERAL RULE (no hardcoded indices, scales to 100+ levels): a level boundary is a RELOAD event -- a
frame whose difference from the previous frame exceeds a large fraction of the frame. The level's true
starting board is the reload frame. The counter is used only to LABEL levels, never to locate their boards;
in fact reload-detection alone segments the stream even if the counter is absent or unreliable.
"""
import numpy as np

_HUD_ROWS = 3
RELOAD_FRAC = 0.15                    # a reload changes >=15% of the frame; normal play changes <7%. Wide margin.


def _diff(a, b):
    a = np.asarray(a); b = np.asarray(b)
    d = (a != b)
    if d.shape[0] > _HUD_ROWS:
        d = d.copy(); d[:_HUD_ROWS, :] = False      # ignore the HUD/counter row (advances every action)
    return int(d.sum())


def find_reloads(frames, reload_frac=RELOAD_FRAC):
    """Indices where the board fully reloads (a new level's board appears). Frame 0 is always a board start."""
    frames = [np.asarray(f) for f in frames]
    if not frames:
        return []
    area = frames[0].size
    thr = reload_frac * area
    reloads = [0]
    for i in range(1, len(frames)):
        if _diff(frames[i], frames[i - 1]) >= thr:
            reloads.append(i)
    return reloads


def segment_levels(frames, counters=None, reload_frac=RELOAD_FRAC):
    """Segment a frame stream into levels by RELOAD events. Returns a list of dicts, one per detected board:
        {board_idx, board, end_idx, n_frames, counter_at_start, counter_span}
    `board` is the TRUE starting board of the level (the reload frame). `counters` (levels_completed per frame),
    if given, only labels the segments -- boards are located by reload, never by the counter. Scales to any N."""
    frames = [np.asarray(f) for f in frames]
    if not frames:
        return []
    reloads = find_reloads(frames, reload_frac)
    segs = []
    for k, start in enumerate(reloads):
        end = (reloads[k + 1] - 1) if k + 1 < len(reloads) else (len(frames) - 1)
        seg = {"board_idx": start, "board": frames[start], "end_idx": end,
               "n_frames": end - start + 1}
        if counters is not None:
            seg["counter_at_start"] = counters[start]
            seg["counter_span"] = sorted(set(counters[start:end + 1]))
        segs.append(seg)
    return segs


def level_board(frames, level_index, counters=None, reload_frac=RELOAD_FRAC):
    """The TRUE starting board for a given level, located by reload. If `counters` is provided, `level_index`
    is matched against the counter value at each segment's start (robust to the win-state offset); otherwise it
    indexes the reload segments directly. Returns (board_ndarray, board_idx) or (None, None)."""
    segs = segment_levels(frames, counters=counters, reload_frac=reload_frac)
    if not segs:
        return None, None
    if counters is not None:
        # match on counter_at_start ONLY: the counter value AT the reload is the level's true label.
        # (counter_span is contaminated by the trailing win-state frame, whose counter already ticked up.)
        for s in segs:
            if s.get("counter_at_start") == level_index:
                return s["board"], s["board_idx"]
        return None, None
    if 0 <= level_index < len(segs):
        return segs[level_index]["board"], segs[level_index]["board_idx"]
    return None, None


if __name__ == "__main__":
    import json, sys
    recs = [json.loads(l)["data"] for l in open(sys.argv[1])]
    frames = [np.array(r["frame"][0]) for r in recs]
    counters = [r.get("levels_completed") for r in recs]
    segs = segment_levels(frames, counters=counters)
    print("detected %d level boards (by reload), for %d frames:" % (len(segs), len(frames)))
    from collections import Counter
    for k, s in enumerate(segs):
        h = dict(sorted(Counter(s["board"].flatten().tolist()).items()))
        print("  board %d: reload@idx=%3d  counter_at_start=%s  span=%s  n_frames=%3d  id-counts=%s"
              % (k, s["board_idx"], s.get("counter_at_start"), s.get("counter_span"), s["n_frames"], h))
