"""DELTA FRAME-DATA VIEW.

The raw frame data / recording is huge because it stores a full grid (and a full reasoning snapshot) for EVERY action,
even when nothing changed. This module renders a frame sequence as a DIFF stream instead:

  - a frame IDENTICAL to the previous one becomes a single em-dash '\u2014',
  - consecutive identical frames COLLAPSE into one dash with a run length,
  - a changed frame lists only the cells that changed (and, if given, the delta of the reasoning).

Two immediate payoffs, exactly as specified:
  1) it is far smaller and faster to read (only changes are shown), and
  2) a spammed / duplicate / no-op action shows up instantly as a RUN OF DASHES -- e.g. an avatar pounding a wall reads
     as '\u2014 x1880  (no-op spam)', which is impossible to miss.

Pure/generic: it holds no game-specific content, so it never persists any particular game's grid.
"""
import numpy as np

DASH = "\u2014"


def _grid(f):
    g = np.asarray(f)
    return g[0] if g.ndim == 3 else g


def _reason_delta(cur, prev):
    """Compact per-field delta of two reasoning dicts: only changed keys, '\u2014' for unchanged. Non-dicts -> repr diff."""
    if not isinstance(cur, dict):
        return DASH if repr(cur) == repr(prev) else cur
    if not isinstance(prev, dict):
        return {k: v for k, v in cur.items()}
    out = {}
    for k, v in cur.items():
        out[k] = DASH if (k in prev and repr(prev[k]) == repr(v)) else v
    return {k: v for k, v in out.items() if v != DASH} or DASH


def frame_delta_view(frames, actions=None, reasonings=None, max_cells=8):
    """Render frames as a delta stream. `frames` is a list of grids (or objects with .frame); `actions`/`reasonings`
    are optional parallel lists. Returns a string: one line per CHANGE, dashes for runs of identical frames."""
    lines = []
    prev = None
    run = 0
    run_start = 0
    for i, f in enumerate(frames):
        g = _grid(getattr(f, "frame", f))
        act = actions[i] if actions and i < len(actions) else "?"
        if prev is not None and g.shape == prev.shape and np.array_equal(g, prev):
            if run == 0:
                run_start = i
            run += 1
            continue
        if run > 0:
            lines.append("   %s x%d   (frames %d..%d identical -> no-op / spam)" % (DASH, run, run_start, i - 1))
            run = 0
        if prev is None:
            lines.append("[%d] %-8s INITIAL %s colours=%s" %
                         (i, act, g.shape, sorted(set(g.flatten().tolist()))))
        else:
            dd = np.argwhere(g != prev)
            ex = ", ".join("(%d,%d):%d->%d" % (int(r), int(c), int(prev[r, c]), int(g[r, c]))
                           for r, c in dd[:max_cells])
            more = "" if len(dd) <= max_cells else "  (+%d more)" % (len(dd) - max_cells)
            rd = ""
            if reasonings is not None and i < len(reasonings):
                d = _reason_delta(reasonings[i], reasonings[i - 1] if i > 0 else None)
                if d and d != DASH:
                    rd = "  | reason\u0394: %s" % (str(d)[:90])
            lines.append("[%d] %-8s %d cell\u0394: %s%s%s" % (i, act, len(dd), ex, more, rd))
        prev = g
    if run > 0:
        lines.append("   %s x%d   (frames %d..%d identical -> no-op / spam)" % (DASH, run, run_start, len(frames) - 1))
    return "\n".join(lines)
