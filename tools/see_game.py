"""see_game.py -- LOOK at what the agent actually does, because proxy measures (order/match discrepancy, tether_stage)
are NOISY when the objective ground is MUTE (Fig 2). Standing practice: when a game shows NO PROGRESS, render its frames
and visually process them BEFORE trusting any scalar. Diagnosis only; never calibrate detectors to what you see here.

Usage:  ARC_API_KEY=... python3.12 tools/see_game.py <game_id> [n_actions] [out_dir]
Writes three images to LOOK at:
  <gid>_montage.png    -- frames across a real-agent run (board + step + action + ORDER/MATCH discrepancy)
  <gid>_referents.png  -- a mid frame with detected referent bboxes (what perception latches onto vs the real structure)
  <gid>_changemap.png  -- per-cell CHANGE COUNT across the run (bright = mutates under the agent = the real workspace;
                          a frozen board with only a bar/timer moving means the agent is not engaging the puzzle)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.patches import Rectangle
from newhorse.redux_arch.sdk_guard import assert_online_sdk
from newhorse.arc3_env import Arc3Session
from newhorse.redux_arch.policy import ReduxPolicy, Blackboard
from newhorse.redux_arch.referent import find_referents

PAL = ["#000000","#1E93FF","#F93C31","#4FCC30","#FFDC00","#999999","#E53AA3",
       "#FF851B","#87D8F1","#921231","#4B0082","#00553E","#7B3F00","#555555","#FF69B4","#FFFFFF"]
CMAP = mcolors.ListedColormap(PAL); NORM = mcolors.BoundaryNorm(range(17), CMAP.N)


def see(game_id: str, n_actions: int = 70, out_dir: str = "."):
    assert_online_sdk()
    frames, acts, disc = [], [], []
    sess = Arc3Session(game_id, tags=["redux-triality", "see", game_id])
    try:
        snap = sess.open()
        pol = ReduxPolicy(game_id=game_id, blackboard=Blackboard(), warmup_cap=8)
        pol.observe(np.asarray(snap["grid"]), snap["available"])
        frames.append(np.asarray(snap["grid"])); acts.append("RESET")
        d = pol.relations.discrepancies(); disc.append((d.get("ORDER"), d.get("MATCH")))
        for _ in range(n_actions):
            lbl, data = pol.choose()
            v = int(lbl[1:]) if lbl.startswith("A") else 5
            snap = sess.step(v, data=data)
            g = np.asarray(snap["grid"]); pol.observe(g, snap["available"])
            frames.append(g); acts.append(lbl)
            d = pol.relations.discrepancies(); disc.append((d.get("ORDER"), d.get("MATCH")))
            if snap["done"]:
                break
        refs = find_referents(frames[len(frames) // 2]); levels = snap["levels_completed"]
    finally:
        sess.close()
    stack = np.stack(frames).astype(int)
    changed = int((stack.max(0) != stack.min(0)).sum())
    print("%s frames=%d levels=%d cells_ever_changed=%d ORDER/MATCH(last)=%s"
          % (game_id, len(frames), levels, changed, disc[-1]))

    idx = np.linspace(0, len(frames) - 1, min(8, len(frames))).astype(int)
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    for ax, k in zip(axes.ravel(), idx):
        ax.imshow(frames[k], cmap=CMAP, norm=NORM, interpolation="nearest")
        ax.set_title("step %d act=%s O=%s M=%s" % (k, acts[k], disc[k][0], disc[k][1]), fontsize=8)
        ax.set_xticks([]); ax.set_yticks([])
    for ax in axes.ravel()[len(idx):]:
        ax.axis("off")
    fig.suptitle("%s -- real-agent run (levels=%d, cells_ever_changed=%d)" % (game_id, levels, changed))
    fig.tight_layout(); fig.savefig(os.path.join(out_dir, "%s_montage.png" % game_id), dpi=90); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 9))
    ax.imshow(frames[len(frames) // 2], cmap=CMAP, norm=NORM, interpolation="nearest")
    col = {"legend": "cyan", "panel": "lime", "endpoints": "magenta"}
    for r in refs:
        r0, c0, r1, c1 = r.bbox
        ax.add_patch(Rectangle((c0 - 0.5, r0 - 0.5), c1 - c0 + 1, r1 - r0 + 1, fill=False,
                     edgecolor=col.get(r.kind, "white"), lw=2.0))
        lab = r.kind + (str(r.detail.get("sequence")) if r.kind == "legend" else "")
        ax.text(c0, r0 - 0.7, lab, color=col.get(r.kind, "white"), fontsize=8, weight="bold")
    ax.set_title("%s -- detected referents (cyan=legend lime=panel magenta=endpoints)" % game_id, fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(os.path.join(out_dir, "%s_referents.png" % game_id), dpi=90); plt.close(fig)

    changes = (np.abs(np.diff(stack, axis=0)) > 0).sum(0)
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(changes, cmap="hot", interpolation="nearest")
    ax.set_title("%s -- per-cell CHANGE COUNT (bright = mutates under the agent = the workspace)" % game_id, fontsize=11)
    ax.set_xticks([]); ax.set_yticks([]); fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout(); fig.savefig(os.path.join(out_dir, "%s_changemap.png" % game_id), dpi=90); plt.close(fig)
    print("wrote %s_{montage,referents,changemap}.png" % game_id)


if __name__ == "__main__":
    gid = sys.argv[1] if len(sys.argv) > 1 else "sb26-7fbdac44"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 70
    out = sys.argv[3] if len(sys.argv) > 3 else "."
    see(gid, n, out)
