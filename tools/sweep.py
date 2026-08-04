"""sweep.py -- THE ONE SWEEP HARNESS. Every measurement arm lives here; the play loop is written once.

WHY THIS FILE EXISTS (Isaiah, 2026-08-04): "I need all this reinvention to stop and i need all the relevant code
that is useful for our current purpose to be subsummed into one." By that date the same twenty-line play loop had
been re-typed from scratch in ten throwaway scripts -- pose_sweep, triage_sweep, ab_sweep, ab_consume,
probe_consume, lib_shadow_sweep, compose_sweep and more -- once per beat, each copy free to drift in its budget,
its reset rule, its session tag, and its digest. That is not ten instruments. That is one instrument measured ten
times with an unrecorded amount of slippage between the readings, which is exactly the failure this project's
whole measurement discipline exists to prevent.

THE SPLIT THIS FILE ENFORCES. The harness owns HOW THE GAME IS PLAYED: budget, reset-on-death, step order, the
action digest. An Arm owns only WHAT IS RECORDED. An arm cannot change the loop, because it is never handed the
loop -- it is handed the policy after each choose() and again at the end. So two arms are comparable by
construction rather than by my promise that I copied the loop faithfully.

WHY `tag` AND `why` ARE ARM FIELDS AND NOT CONSTANTS. The scripts this file replaces disagreed on them
(`tags=["c2115s0"]` vs `["compose_fix"]`, `why="triage"` vs `"ab"`). They are carried, not normalised away, for
one reason: a consolidation whose faithfulness is checked by `seq_sha` identity against the originals must be
able to reproduce the originals exactly, including the fields that are probably inert. "Probably inert" is a
hypothesis, and this file is not the place to test it.

THE DIGEST IS COMPUTED HERE, ONCE. `sha1` over a json dump of `(label, x, y)` per step -- never `hash(tuple(...))`,
whose str hashing is seed-randomized per process, so two arms are two hash functions. Arms cannot override it.

CORE FIELDS ARE ALWAYS RECORDED. Every arm gets `seq_sha`, `levels`, `n_posed`, `steps`, `resets`, `family` --
the fields the COUNTER-CLEAR TRAP leaves trustworthy across arms -- so any two runs of any two arms remain
comparable on the set that is allowed to carry an A/B claim.

    OURO_OFFLINE=1 OURO_ENV_DIR=/tmp/environment_files \
        python3.12 tools/sweep.py <arm> [--out FILE] [--only pre,fix] [--steps N] [--wall S]

Flags are NOT set here. An arm is a recorder, not a configuration: the flag vector belongs on the command line so
it lands in the shell history and in the capture header, because A MEASUREMENT TAKEN UNDER DEFAULT FLAGS IS A
CLAIM ABOUT THE DEFAULT, NOT ABOUT THE AGENT. The header prints the full OURO_*/NEWHORSE_* vector it ran under.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from newhorse.arc3_env import Arc3Session                      # noqa: E402
from newhorse.redux_arch.policy import ReduxPolicy             # noqa: E402

DEFAULT_IDS = "/tmp/game_ids.json"


# --------------------------------------------------------------------------------------------------------------
# helpers shared by arms -- defined ONCE so two arms cannot disagree about what "arity" or "kind" means
# --------------------------------------------------------------------------------------------------------------
def kinds_of(pred) -> List[str]:
    """The distinct atom KINDS in a predicate. A `COMPOSED:*` kind marks an INVENTED relation."""
    try:
        return sorted({str(getattr(a, "kind", "")) for a in pred.atoms})
    except Exception:
        return []


def arity_of(pred) -> int:
    """CONJUNCT COUNT -- not composition depth. An invented relation is a composition INSIDE one conjunct, so
    arity 1 does not mean 'nothing was composed'. Conflating those two is a mistake this project has already
    published once; the two are separate functions here so they cannot be collapsed again by accident."""
    try:
        return len(pred.atoms)
    except Exception:
        return 0


def phi_arity(s: str) -> int:
    """Conjunct count read off a rendered φ, for receipts that expose the string and not the predicate."""
    return 1 + str(s).count(" ∧ ")


# --------------------------------------------------------------------------------------------------------------
# the arm
# --------------------------------------------------------------------------------------------------------------
@dataclass
class Arm:
    """WHAT TO RECORD. Never how to play.

    `on_step(pol, snap, state)` is called after `pol.observe()` and before `pol.choose()`; `after_choose(pol, lbl,
    data, state)` after the action is chosen and before it is submitted; `finish(pol, state)` once at the end and
    its dict is merged into the record. `state` is a per-game scratch dict the harness hands back to the arm.
    """
    name: str
    doc: str
    tag: str
    why: str
    steps: int = 260
    wall: float = 30.0
    max_resets: int = 6
    on_step: Optional[Callable[[Any, dict, dict], None]] = None
    after_choose: Optional[Callable[[Any, str, Optional[dict], dict], None]] = None
    finish: Optional[Callable[[Any, dict], Dict[str, Any]]] = None


ARMS: Dict[str, Arm] = {}


def register(arm: Arm) -> Arm:
    ARMS[arm.name] = arm
    return arm


# --------------------------------------------------------------------------------------------------------------
# the loop -- written once
# --------------------------------------------------------------------------------------------------------------
def play(arm: Arm, gid: str, steps_cap: int, wall_cap: float) -> Dict[str, Any]:
    """Play one game under the arm's budget and return its record. The ONLY place a game is played."""
    state: Dict[str, Any] = {"gid": gid}
    session = Arc3Session(gid, tags=[arm.tag, gid], save_recording=False)
    snap = session.open()
    pol = ReduxPolicy()
    t0 = time.time()
    n_steps = 0
    resets = 0
    seq: List[list] = []
    best = int(snap.get("levels_completed", 0))
    while n_steps < steps_cap and (time.time() - t0) < wall_cap:
        pol.observe(snap["grid"], snap["available"], snap["levels_completed"], state=snap["state"])
        if snap.get("done"):                                   # lifetime over -> new generation, same policy
            snap = session.reset_after_death(reasoning={"why": arm.why + " reset"})
            pol.note_reset()
            resets += 1
            if resets > arm.max_resets:
                break
            continue
        if arm.on_step is not None:
            arm.on_step(pol, snap, state)
        lbl, data = pol.choose()
        if arm.after_choose is not None:
            arm.after_choose(pol, lbl, data, state)
        seq.append([lbl, (data or {}).get("x"), (data or {}).get("y")])
        snap = session.step(int(lbl[1:]), data=data, reasoning={"why": arm.why})
        best = max(best, int(snap.get("levels_completed", 0)))
        n_steps += 1
    receipts = list(getattr(pol, "receipts", []) or [])
    minted = [r for r in receipts if getattr(r, "minted", False)]
    rec: Dict[str, Any] = {
        # THE TRUSTWORTHY SET (COUNTER-CLEAR TRAP): these survive across arms and may carry an A/B claim.
        "game": gid,
        "steps": n_steps,
        "levels": best,
        "resets": resets,
        "family": str(getattr(pol, "family", None)),
        "n_posed": int(getattr(pol, "n_posed", 0)),
        "priority": len(getattr(pol.prober, "_priority", []) or []) if getattr(pol, "prober", None) else None,
        "seq_sha": hashlib.sha1(json.dumps(seq).encode()).hexdigest()[:16],
        # cheap always-on context; counters below this line are cleared at epoch publish -- see the trap.
        "receipts": len(receipts),
        "live_minted": len(minted),
        "minted_phis": [str(getattr(r, "minted_phi", "")) for r in minted],
        "minted_arity": [phi_arity(getattr(r, "minted_phi", "")) for r in minted],
        "library_end": sorted(str(p) for p in (getattr(pol.echo, "library", []) or []))[:16],
        "library_arity": sorted(phi_arity(p) for p in (getattr(pol.echo, "library", []) or [])),
    }
    if arm.finish is not None:
        rec.update(arm.finish(pol, state))
    session.close()
    return rec


def flag_vector() -> Dict[str, str]:
    """The full OURO_*/NEWHORSE_* vector this process ran under, recorded IN the capture. A finding of the form
    'the agent never X' is a claim about this vector and nothing wider."""
    return {k: v for k, v in sorted(os.environ.items())
            if k.startswith("OURO_") or k.startswith("NEWHORSE_")}


def select(gids: List[str], only: str):
    """Keep roster entries matching any prefix; return (kept, dropped, unmatched). A prefix matching NOTHING is
    returned rather than ignored -- silently measuring a smaller set than the prereg named is the defect."""
    pref = [p.strip() for p in (only or "").split(",") if p.strip()]
    if not pref:
        return list(gids), 0, []
    kept = [g for g in gids if any(g.startswith(p) for p in pref)]
    unmatched = [p for p in pref if not any(g.startswith(p) for g in gids)]
    return kept, len(gids) - len(kept), unmatched


def main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("arms: " + ", ".join(sorted(ARMS)))
        for a in sorted(ARMS.values(), key=lambda x: x.name):
            print("\n  %-9s %s" % (a.name, a.doc.strip().splitlines()[0]))
        return 0
    name = argv[0]
    if name not in ARMS:
        print("unknown arm %r; known: %s" % (name, ", ".join(sorted(ARMS))))
        return 2
    arm = ARMS[name]
    opts = {}
    i = 1
    while i < len(argv) - 1:
        if argv[i].startswith("--"):
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            i += 1
    steps_cap = int(opts.get("steps", os.environ.get("SWEEP_STEPS", arm.steps)))
    wall_cap = float(opts.get("wall", os.environ.get("SWEEP_WALL", arm.wall)))
    out_path = opts.get("out", os.environ.get("SWEEP_OUT", "/tmp/sweep_%s.json" % name))
    ids = json.load(open(opts.get("ids", DEFAULT_IDS)))
    kept, dropped, unmatched = select(ids, opts.get("only", ""))
    header = {"arm": name, "doc": arm.doc.strip().splitlines()[0], "tag": arm.tag, "why": arm.why,
              "steps_cap": steps_cap, "wall_cap": wall_cap, "max_resets": arm.max_resets,
              "flags": flag_vector(), "n_games": len(kept), "dropped": dropped,
              "unmatched_prefixes": unmatched, "games": kept}
    print("HEADER " + json.dumps(header))
    sys.stdout.flush()
    if unmatched:
        print("WARNING: prefixes matched nothing: %s -- this sweep measures a SMALLER set than asked for"
              % unmatched)
    out = []
    for gid in kept:
        try:
            rec = play(arm, gid, steps_cap, wall_cap)
        except Exception as exc:                                # a dead game is recorded, never silently dropped
            rec = {"game": gid, "error": repr(exc)[:220]}
        out.append(rec)
        print(json.dumps(rec))
        sys.stdout.flush()
    json.dump({"header": header, "records": out}, open(out_path, "w"), indent=1)
    print("DONE %d -> %s" % (len(out), out_path))
    return 0


# --------------------------------------------------------------------------------------------------------------
# THE ARMS. Each is WHAT TO RECORD and nothing else. Budget/tag/why are declared so an A/B cannot drift.
# --------------------------------------------------------------------------------------------------------------
def _compose_on_step(pol, snap, state):
    """Sample the POSED objective EACH STEP -- the policy holds only the current one, so an end-of-run read sees
    at most the last. Keyed by rendered φ, keeping the best-scoring sighting of each."""
    posed = state.setdefault("posed", {})
    g = getattr(pol, "_posed_goal", None)
    if g is not None and getattr(g, "mint", None) is not None:
        p = g.mint.predicate
        key = str(p)
        bits = float(getattr(g.mint, "saved_bits", 0.0))
        cur = posed.get(key)
        if cur is None or bits > cur[2]:
            posed[key] = [arity_of(p), kinds_of(p), round(bits, 2)]


def _compose_finish(pol, state):
    posed = state.get("posed", {})
    hist: Dict[str, int] = {}
    for v in posed.values():
        hist[str(v[0])] = hist.get(str(v[0]), 0) + 1
    return {"posed_phis": posed, "posed_distinct": len(posed),
            "posed_composed": sum(1 for v in posed.values()
                                  if any(k.startswith("COMPOSED:") for k in v[1])),
            "posed_arity_hist": hist}


register(Arm(
    name="compose",
    doc="""DID THE COMPOSER COMPOSE? Records every posed objective with its atom KINDS and saved bits.

    Run it with the invention loop ON (`OURO_COMPOSE=1`) and with it off, and compare `posed_composed`. The atom
    kinds are recorded alongside arity precisely so a `COMPOSED:*` relation is never collapsed into 'arity 1'.""",
    tag="compose_fix", why="compose sweep",
    on_step=_compose_on_step, finish=_compose_finish))


def _shadow_finish(pol, state):
    """The C21.15 shadow ladder, rung by rung. The shadow is a SECOND, DISCARDED mint over a universe admitting
    the promoted φ this game did NOT mint. PRE-REGISTERED GATE: `seq_sha` must be identical to the arm with the
    shadow off, on all 25 -- any movement means the shadow leaked into the live path and the beat is VOID.
    PRE-REGISTERED READING: `lib_in_argmax` 0 across all 25 means the wire is INERT, and that sentence is the
    output -- not a next stage."""
    receipts = list(getattr(pol, "receipts", []) or [])
    sh = [r for r in receipts if getattr(r, "shadow_ran", False)]
    gid = state.get("gid")
    return {
        "shadow_ran": len(sh),
        "lib_foreign_max": max([int(getattr(r, "shadow_lib_n", 0)) for r in sh] or [0]),
        "shadow_with_lib": sum(1 for r in sh if int(getattr(r, "shadow_lib_n", 0)) > 0),
        "lib_admitted_ge1": sum(1 for r in sh if int(getattr(r, "shadow_lib_admitted", 0)) > 0),
        "lib_admitted_max": max([int(getattr(r, "shadow_lib_admitted", 0)) for r in sh] or [0]),
        "lib_eligible_ge1": sum(1 for r in sh if int(getattr(r, "shadow_lib_eligible", 0)) > 0),
        "lib_in_argmax": sum(1 for r in sh if bool(getattr(r, "shadow_lib_in_argmax", False))),
        "shadow_differs": sum(1 for r in sh if bool(getattr(r, "shadow_differs", False))),
        "shadow_phis": sorted({str(getattr(r, "shadow_phi", None)) for r in sh
                               if getattr(r, "shadow_lib_in_argmax", False)})[:5],
        "shadow_ms_total": round(sum(float(getattr(r, "shadow_ms", 0.0)) for r in sh), 1),
        "foreign_end": sorted(str(p) for p in (pol.echo.foreign(gid) if getattr(pol, "echo", None) and gid
                                               else []))[:8],
        "echo_counts": [int(getattr(r, "echo_count", 0)) for r in receipts if getattr(r, "minted", False)],
        "n_exc": [int(getattr(r, "n_exceptions", 0)) for r in receipts
                  if getattr(r, "residual_nonempty", False)],
        "pool_sizes": [int(getattr(r, "pool_size", 0)) for r in receipts if getattr(r, "pool_attempted", False)],
        "minted_from_pool": sum(1 for r in receipts if getattr(r, "minted_from_pool", False)),
    }


register(Arm(
    name="shadow",
    doc="""C21.15 STAGE 0 -- the shadow mint ladder. Nothing reads a shadow field back; the arm exists to say
    which rung the library reaches before it stops.""",
    tag="c2115s0", why="c2115 stage0",
    finish=_shadow_finish))


def _triage_after_choose(pol, lbl, data, state):
    fam = str(getattr(pol, "family", None))
    fh = state.setdefault("fam_hist", {})
    fh[fam] = fh.get(fam, 0) + 1
    pe = getattr(pol, "_pend_exit", None)                      # the exit that chose THIS action
    if pe:                                                     # `_dec_exits` is CLEARED at epoch publish, so an
        ex = state.setdefault("exits", {})                     # end-of-run read is empty for any game that died
        ex[pe] = ex.get(pe, 0) + 1


def _triage_finish(pol, state):
    posed = [{"target": a.get("target"), "relation": a.get("name"),
              "bits": round(float(a.get("saved_bits", 0.0)), 2)}
             for a in (pol.abduced or []) if a.get("source") == "pose_goal"]
    other = [a.get("name") for a in (pol.abduced or []) if a.get("source") != "pose_goal"]
    return {"family_hist": state.get("fam_hist", {}), "exits": state.get("exits", {}),
            "posed_seq": posed, "other_abduced": other[:5],
            "relations_seen": sorted(getattr(pol, "_relation_kinds_seen", set())),
            "rel_sel": str(getattr(pol, "_relation_selected", None)),
            "deaths": int(getattr(pol, "n_deaths", 0))}


register(Arm(
    name="triage",
    doc="""Which link breaks, per game: family history, the exit that chose each action, the posed sequence.

    Buckets (EXECUTION / PERCEPTION / COMMITMENT) are applied AFTERWARDS by a rule declared in the analysis and
    applied uniformly -- never per game. This arm records only what the agent itself publishes.""",
    tag="triage2", why="triage",
    after_choose=_triage_after_choose, finish=_triage_finish))


register(Arm(
    name="base",
    doc="""The control. Core fields only -- the digest, the levels, the pose count. Every A/B needs one arm that
    adds no instrumentation at all, so 'the recorder changed the run' has somewhere to show up.""",
    tag="base", why="base sweep"))


if __name__ == "__main__":                                     # pragma: no cover -- builder-only instrument
    raise SystemExit(main(sys.argv[1:]))
