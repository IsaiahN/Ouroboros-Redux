"""
render_run.py -- SEE BEFORE YOU SAY (RULE 0 OF EVIDENCE, enforced). Turn a recorded ARC-3 run into
IMAGES a human (or Claude) can actually look at, plus a change-decomposition, so no run is ever
diagnosed from telemetry alone again.

This exists because a run was once diagnosed as "large/global per-step change" from pe_integral and
belief numbers when the pixels showed a small maroon+lime piece moving around a maze. The numbers
pointed; the frames decided. This tool makes rendering the frames a one-command, no-excuse step.

Usage:
    python tools/render_run.py <recording.jsonl | scorecard_dir> [out_prefix]
Outputs:
    <prefix>_frames.png   -- a montage of frames spread across the run (with the action taken)
    <prefix>_active.png    -- heatmap of cells that EVER change (where the game actually lives)
    <prefix>_zoom.png      -- consecutive-step zoom into the active play region (the real dynamics)
and prints the change decomposition (per-step changed cells, split into candidate regions, per action).
"""
import sys, os, glob, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# ARC-standard 16-colour palette
_PAL = ['#000000', '#0074D9', '#FF4136', '#2ECC40', '#FFDC00', '#AAAAAA', '#F012BE', '#FF851B',
        '#7FDBFF', '#870C25', '#001f3f', '#39CCCC', '#01FF70', '#85144b', '#B10DC9', '#FFFFFF']
_CMAP = ListedColormap(_PAL)


def _load(path):
    if os.path.isdir(path):
        hits = glob.glob(os.path.join(path, "*.jsonl"))
        if not hits:
            raise SystemExit("no .jsonl recording under %s" % path)
        path = hits[0]
    recs = [json.loads(l)["data"] for l in open(path).read().splitlines()]
    frames = [np.array(r["frame"])[-1] for r in recs]
    acts = [r.get("action_input", {}).get("id", "?") for r in recs]
    lvls = [r.get("levels_completed", 0) for r in recs]
    return path, frames, acts, lvls


def _active_bbox(F):
    dyn = (F != F[0]).any(0)
    if not dyn.any():
        return None, dyn
    ys, xs = np.where(dyn)
    return (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())), dyn


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path, frames, acts, lvls = _load(sys.argv[1])
    prefix = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(path))[0]
    F = np.stack(frames)
    n = len(frames)
    print("=== SEE BEFORE YOU SAY: %d frames %s ===" % (n, frames[0].shape))
    print("levels: max=%d unique=%s   win at level? (check win_levels in the recording)" % (max(lvls), sorted(set(lvls))))
    print("colours present:", sorted(set(int(v) for f in frames for v in np.unique(f))))
    ch = [int((frames[i] != frames[i - 1]).sum()) for i in range(1, n)]
    print("per-step changed cells: med=%d mean=%.1f max=%d" % (int(np.median(ch)), float(np.mean(ch)), max(ch)))
    static = int((F.std(0) == 0).sum())
    print("cells NEVER changing: %d/%d (%.0f%% static -> the game lives in the other %d cells)"
          % (static, F[0].size, 100 * static / F[0].size, F[0].size - static))
    bbox, dyn = _active_bbox(F)
    print("active-region bbox (rows,cols):", bbox)
    # per-action change magnitude (near-identical across actions => much of the change is action-INDEPENDENT)
    from collections import defaultdict
    byact = defaultdict(list)
    for i in range(1, n):
        byact[acts[i]].append(ch[i - 1])
    for a in sorted(byact):
        v = byact[a]
        print("  action %-10s n=%3d changed-cells med=%d mean=%.1f" % (a, len(v), int(np.median(v)), float(np.mean(v))))

    # 1) montage across the run
    idx = sorted(set([0, 1, 2, n // 8, n // 4, n // 2, 3 * n // 4, n - 1]))
    fig, axs = plt.subplots(2, 4, figsize=(14, 7.5))
    for ax, i in zip(axs.ravel(), idx + [n - 1] * (8 - len(idx))):
        ax.imshow(frames[i], cmap=_CMAP, vmin=0, vmax=15, interpolation="nearest")
        ax.set_title("step %d act=%s" % (i, acts[i]), fontsize=9); ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout(); plt.savefig(prefix + "_frames.png", dpi=90, bbox_inches="tight"); plt.close()

    # 2) active-region heatmap
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(dyn.astype(int), cmap="hot", interpolation="nearest")
    ax.set_title("cells that EVER change (the active region)"); ax.set_xticks([]); ax.set_yticks([])
    plt.savefig(prefix + "_active.png", dpi=90, bbox_inches="tight"); plt.close()

    # 3) zoom into the active region over consecutive steps
    if bbox:
        r0, r1, c0, c1 = bbox
        pad = 3
        r0, c0 = max(0, r0 - pad), max(0, c0 - pad)
        r1, c1 = min(F.shape[1], r1 + pad + 1), min(F.shape[2], c1 + pad + 1)
        s0 = n // 3
        fig, axs = plt.subplots(1, 6, figsize=(18, 3.6))
        for k, ax in enumerate(axs):
            i = min(n - 1, s0 + k)
            ax.imshow(frames[i][r0:r1, c0:c1], cmap=_CMAP, vmin=0, vmax=15, interpolation="nearest")
            ax.set_title("step %d act=%s" % (i, acts[i]), fontsize=9); ax.set_xticks([]); ax.set_yticks([])
        plt.tight_layout(); plt.savefig(prefix + "_zoom.png", dpi=95, bbox_inches="tight"); plt.close()

    print("WROTE: %s_frames.png  %s_active.png  %s_zoom.png" % (prefix, prefix, prefix))
    print(">>> NOW READ THOSE IMAGES. Diagnosis is written from the pixels, not this printout.")


if __name__ == "__main__":
    main()
