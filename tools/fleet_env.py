"""FLEET ENV -- the single statement of the per-worker environment.

THE GAP THIS CLOSES (2026-08-21): the supervisor assembles two fleet-policy variables
for every worker it spawns -- OURO_FABRIC_SEEDS (the ego_fabric dir of every OTHER box
plus compound2's, ';'-joined, so fabrics cross-mount without merging) and LP_DRIVE_ARM
(assign_arm(game, recycles), the three-arm LP-drive control, rotating per recycle).
The sprint keeper needs the same two, for the same game, or the sprint runs under an
undeclared different config. Until now the keeper TRANSCRIBED the supervisor's lines,
because the supervisor could not be imported without side effects. A transcription
drifts. This module is the one place the assembly is written; the supervisor and the
keeper both import it, so there is nothing to keep in step.

No side effects on import: no .env read, no mkdir, no spawn. Pure functions over
their arguments plus the roster and the two path constants.
"""
from __future__ import annotations

import os
import sys

REDUX = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REDUX not in sys.path:
    sys.path.insert(0, REDUX)
from engines.egocentric.lp_drive import assign_arm  # G-D: three-arm LP-drive control

ROOT = os.path.join(REDUX, ".runs", "swarm")
COMPOUND2_SEED = os.path.join(REDUX, ".runs", "compound2", "ego_fabric")
SEED_SEP = ";"                     # the OURO_FABRIC_SEEDS separator (cognitive_loop splits on it)

# THE ROSTER. One worker per game in the full fleet; the keeper's sprint subset is
# chosen from this list. Edit it here and nowhere else.
GAMES = ["ar25", "bp35", "cd82", "cn04", "dc22", "ft09", "g50t", "ka59", "lf52", "lp85",
         "ls20", "m0r0", "r11l", "re86", "s5i5", "sb26", "sc25", "sk48", "sp80", "su15",
         "tn36", "tr87", "tu93", "vc33", "wa30"]


def fleet_seed_dirs(root=ROOT, games=None, compound2=COMPOUND2_SEED):
    """Every seed dir a worker may cross-mount: compound2/ego_fabric first, then
    <root>/<g>/ego_fabric for every g in the roster, in roster order. No existence
    filter: the worker's fabric init tolerates an absent seed, and a filter here
    would make the env depend on disk state at spawn time."""
    games = GAMES if games is None else list(games)
    return [compound2] + [os.path.join(root, g, "ego_fabric") for g in games]


def fleet_env_for(game, root=ROOT, games=None, recycles=0, compound2=COMPOUND2_SEED):
    """The two fleet-policy variables for `game`, in the order the supervisor has
    always set them:
      OURO_FABRIC_SEEDS  every seed dir EXCEPT this game's own box, ';'-joined
      LP_DRIVE_ARM       assign_arm(game, recycles) -- ARMS[(sha1(game) + recycles) mod 3],
                         so the arm rotates on every bounded-lifetime recycle and every
                         game visits every arm across 3 recycles; recycles=0 is the
                         static assignment (what the keeper uses: it never recycles).
    """
    own = os.path.join(root, game, "ego_fabric")
    seeds = [d for d in fleet_seed_dirs(root, games, compound2) if d != own]
    return {"OURO_FABRIC_SEEDS": SEED_SEP.join(seeds),
            "LP_DRIVE_ARM": assign_arm(game, recycles)}
