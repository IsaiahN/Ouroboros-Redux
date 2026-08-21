"""COMPOSER STAGE 3: THE COMPOSE LOOP (PROPOSAL_COMPOSER_DESIGN.md par.3/6.3).

Stage 1 factored the signatures (applicability.psig/csig); stage 2 built the
two edges that make composition FINDABLE (enables.enables_edges,
enables.cross_shelf_reach -- both shipped SEVERED with this loop as their
STATED consumer). This module is that consumer: one ordering over existing
machinery, engaged ONLY where the planner already engages (behind the W2b
scheduler's gates, cognitive_loop's plan seams) and ONLY after the planner's
own search returned None. No new scheduling, no new search elsewhere.

THE LOOP (design par.3, verbatim):
  WANT (diff cells or abduced predicate)
    -> Gamma candidates by effect-intersects-WANT: psig_of(atom)["written"]
       intersects the WANT's target colours (stored signatures only -- the
       same edge logic as enables_edges, pointed at the goal instead of at
       another atom)
    -> per candidate: matching anchors via the EXISTING vectorised matcher
       (effects._context_anchors -- the same scan apply_effect runs)
    -> where the atom carries act_offset and no act cell (anchor + offset)
       is the avatar's current position: enables.cross_shelf_reach for the
       BODY prefix (BFS over the per-action deltas, fatal-masked)
    -> where the candidate has NO matching anchor: the within-Gamma ENABLES
       edge (enables.enables_edges, computed lazily over the pool) supplies
       a one-step enabler A -> chain [A, B] (no movement combined with the
       enabler prefix at this stage -- stated scope, not a silent limit)
    -> chain = [BODY atoms..., Gamma atom] simulated seam by seam (below)
    -> verified chains ranked by the DERIVED price
       (applicability.composite_signature -- the stage-1 derivation, one
       computation, this is its third consumer)
    -> cheapest verified chain -> Gamma.compose() -> COMPOSITE minted as
       CANDIDATE. Nothing here (or anywhere yet) marks it citable: the
       settlement wire is STAGE 4's build, so every composite this loop
       mints is proposable-not-standable by construction. Simulation NEVER
       counts as the settle (design par.5).

THE SIMULATION APPROACH, EXACT SCOPE (Seat 4's amendment: the algebra
proposes, the simulation decides -- and the boundary of what we can simulate
is GATED, never blurred):
  * A no-movement chain ([B] or [A, B]) simulates exactly: each Gamma seam is
    effects.apply_effect on the running frame; any None kills the chain.
  * A movement-prefixed chain simulates ONLY when every BODY action resolves
    to a minted Gamma TRANSLATE atom (same action, params (dx, dy) equal to
    the reach's delta for that action). The prefix then simulates by
    sequential apply_effect -- the frame stays unchanged except the avatar's
    patch, which apply's context matching itself moves -- PLUS the ENDPOINT
    CHECK per step: the cells that application actually changed must include
    both the step's predicted departure and arrival cell (reach's "cells"
    trace). apply_effect moves the FIRST matching patch, which need not be
    the avatar; the endpoint check is what makes the movement simulation
    exact, and a mismatch (wrong patch moved, wall blocked, wake invisible)
    DEGRADES the chain to proposed-unverified.
  * Anything outside that scope -- a BODY action with no minted TRANSLATE
    atom (nothing to apply AND nothing to compose), an unknown avatar with a
    positional atom -- is proposed-unverified: reported in the counts,
    NEVER minted. An unverifiable chain is never minted at all, verified or
    otherwise (the composite's parts must all be Gamma ids anyway).
  * The final Gamma seam must ADVANCE the WANT on the simulated frame: some
    want cell attains its target colour (cells mode), or the predicate
    holds (goal_abduction.satisfies -- the planner's own stopping test).
    The seam applies at apply_effect's first matching anchor, which may not
    be the reach's chosen anchor -- context-keyed, not coordinate-keyed, is
    exactly the recording discriminator (design F3), and the WANT-advance
    check is the decider.

THE WANT, TRANSLATED (conservative, stated): cells mode is a sequence of
(row, col, target_colour) triples (the reference diff, cellwise); predicate
mode accepts the abduced predicates that NAME a colour to appear
(colour_present / colour_majority / region_contains_colour) -- any other
predicate shape is WANT-UNDERIVABLE (the written-colours edge cannot see
removals or uniformity), returned as that reason, never guessed at.

Design par.5 held: no new search (candidates from the stored-signature
indices; the reach is the stage-2 BFS; the enabler is the stage-2 edge), no
authored action semantics (the atoms and the book are the sources), no bulk
import, no self-settlement. Total: compose_attempt never raises; every
outcome is a dict carrying a fixed reason token (narrated verbatim at the
PLAN point by the loop seam). Deterministic throughout: pool in stream
order, ties broken by discovery order.

WIRING: consumed at cognitive_loop._w3c_compose (the ONE compose_attempt
call site), invoked from the two already-gated plan seams in cycle() when
the search returns None. This build flips enables_edges and
cross_shelf_reach SEVERED -> LIVE (WIRING_REGISTRY.md).

STAGE 4 (PREREG_COMPOSER_STAGE4_SETTLEMENT.md) appends the settlement wire
at the bottom of this module: drive_record / divergence / settle_verdict /
live_settle / is_citable / citation_allowed / conflict_component. Consumed
by cognitive_loop's _w3d_drive (the drive, under the planner's own gates),
_w3d_continue (the multi-cycle chain) and _w3d_settle (the ONE live_settle
call site, in record_result beside _w2b_abort).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from engines.egocentric import applicability as _app
from engines.egocentric import effects as _effects
from engines.egocentric import enables as _enables

__all__ = ["compose_attempt", "COMPOSED", "R_EMPTY_WANT",
           "R_WANT_UNDERIVABLE", "R_NO_FRAME", "R_NO_CANDIDATES",
           "R_UNREACHABLE", "R_UNVERIFIED", "R_ERROR",
           # stage 4: the settlement wire
           "SETTLED_FIELD", "ROLE_BET", "ROLE_GROUND", "S_SETTLED",
           "S_ALREADY", "S_NO_DRIVE", "S_NO_RECORD", "S_DIVERGED",
           "drive_record", "step_cells", "divergence", "settle_verdict",
           "composite_record", "is_citable", "citation_allowed",
           "live_settle", "conflict_component"]

# fixed reason tokens (narrated verbatim at the PLAN point -- never free prose)
COMPOSED = "composed"                  # a composite was minted as CANDIDATE
R_EMPTY_WANT = "empty-want"            # no WANT arrived: nothing to compose toward
R_WANT_UNDERIVABLE = "want-underivable"  # predicate names no colour to appear
R_NO_FRAME = "no-frame"                # frame unreadable: no anchors, no simulation
R_NO_CANDIDATES = "no-candidates"      # no atom's written colours touch the WANT
R_UNREACHABLE = "unreachable"          # candidates, but no chain even proposable
R_UNVERIFIED = "unverified-only"       # chains proposed; none simulation-verified
R_ERROR = "compose-error"              # containment: an internal error, stated

# the abduced predicate kinds whose target colour is NAMED -- the only shapes
# the written-colours candidate edge can consume (conservative, stated).
_COLOUR_PREDICATES = ("colour_present", "colour_majority",
                      "region_contains_colour")


# ── the WANT translation ──────────────────────────────────────────────────────

def _want_cells(want: Any) -> Optional[List[Tuple[int, int, int]]]:
    """Validated (row, col, target) triples from a cells-mode WANT, [] when
    the sequence is empty, None when it is not a readable cells sequence."""
    if not isinstance(want, (list, tuple, set, frozenset)):
        return None
    out: List[Tuple[int, int, int]] = []
    try:
        for cell in sorted(want) if isinstance(want, (set, frozenset)) else want:
            out.append((int(cell[0]), int(cell[1]), int(cell[2])))
    except (TypeError, ValueError, IndexError):
        return None
    return out


def _pred_colours(pred: Dict[str, Any]) -> Optional[Set[int]]:
    """The colours a predicate WANTs to appear, or None (underivable)."""
    if pred.get("kind") in _COLOUR_PREDICATES:
        try:
            return {int(pred.get("colour"))}
        except (TypeError, ValueError):
            return None
    return None


# ── the pieces of the loop (each pure over its inputs) ────────────────────────

def _anchors(frame: np.ndarray, atom: Any) -> List[Tuple[int, int]]:
    """The candidate's matching anchors in `frame` via the EXISTING vectorised
    matcher (effects._context_anchors -- the same scan apply_effect runs).
    [] on any doubt: no anchor is never a guessed anchor."""
    if not isinstance(atom, dict) or atom.get("kind") != "EFFECT":
        return []
    try:
        ctx = np.asarray(atom.get("context"))
        if ctx.ndim != 2 or ctx.size == 0:
            return []
        return [(int(r), int(c))
                for r, c in _effects._context_anchors(frame, ctx)]
    except Exception:
        return []


def _body_atom_id(order: List[str], atoms: Dict[str, Any], action: int,
                  delta: Tuple[int, int]) -> Optional[str]:
    """The FIRST minted Gamma TRANSLATE atom for `action` whose (dx, dy)
    equals the reach's delta -- the BODY step as a composable, simulable part.
    None when no such atom exists: the movement can then neither be simulated
    nor composed, and the chain degrades to proposed-unverified."""
    for aid in order:
        atom = atoms.get(aid)
        if (not isinstance(atom, dict) or atom.get("kind") != "EFFECT"
                or atom.get("ttype") != "TRANSLATE"):
            continue
        params = atom.get("params") or {}
        try:
            if (int(atom.get("action")) == int(action)
                    and (int(params.get("dx")), int(params.get("dy")))
                    == (int(delta[0]), int(delta[1]))):
                return aid
        except (TypeError, ValueError):
            continue
    return None


def _advances(frame: np.ndarray, result: np.ndarray,
              cells: Optional[List[Tuple[int, int, int]]],
              pred: Optional[Dict[str, Any]]) -> bool:
    """The final seam's decider: the simulated frame ADVANCES the WANT --
    some want cell attained a target it did not hold (cells mode), or the
    predicate holds (the planner's own stopping test)."""
    if cells is not None:
        h, w = result.shape[:2]
        for r, c, t in cells:
            if (0 <= r < h and 0 <= c < w and int(result[r, c]) == int(t)
                    and int(frame[r, c]) != int(t)):
                return True
        return False
    from engines.egocentric.goal_abduction import satisfies
    return bool(satisfies(pred, result))


def _simulate(frame: np.ndarray, atoms: Dict[str, Any],
              body_ids: List[str], trace: Optional[List[Tuple[int, int]]],
              core: List[str],
              cells: Optional[List[Tuple[int, int, int]]],
              pred: Optional[Dict[str, Any]]) -> Optional[List[np.ndarray]]:
    """Simulate the whole chain seam by seam on a COPY (self-settlement is
    banned by design par.5 -- this is admission-to-candidacy, nothing more).
    None on any seam failure, endpoint mismatch, or a WANT not advanced;
    otherwise the PREDICTED FRAME AFTER EACH PART, in chain order (stage 4
    carries these in the drive stash and compares them against the LIVE
    frame -- the simulation itself never settles anything)."""
    cur = frame.copy()
    frames: List[np.ndarray] = []
    for i, bid in enumerate(body_ids):
        nxt = _effects.apply_effect(atoms.get(bid), cur)
        if nxt is None:
            return None
        nxt = np.asarray(nxt)
        if trace is not None:
            # THE ENDPOINT CHECK: the application must visibly move the
            # avatar's predicted step -- both the departure and the arrival
            # cell are among the cells it changed, or the moved patch cannot
            # be confirmed as the avatar's (wrong patch, wall, silent wake).
            changed = {(int(r), int(c))
                       for r, c in np.argwhere(cur != nxt)}
            frm = (int(trace[i][0]), int(trace[i][1]))
            to = (int(trace[i + 1][0]), int(trace[i + 1][1]))
            if frm not in changed or to not in changed:
                return None
        cur = nxt
        frames.append(cur.copy())
    for aid in core:
        res = _effects.apply_effect(atoms.get(aid), cur)
        if res is None:
            return None
        cur = np.asarray(res)
        frames.append(cur.copy())
    if not _advances(frame, cur, cells, pred):
        return None
    return frames


# ── THE COMPOSE ATTEMPT ───────────────────────────────────────────────────────

def compose_attempt(want: Any, frame: Any, gamma: Any,
                    avatar: Optional[Tuple[int, int]],
                    deltas: Dict[int, Tuple[int, int]],
                    fatal: Optional[Set[Tuple[int, int]]],
                    game: str, level: int) -> Dict[str, Any]:
    """One compose attempt: the loop above, on the WANT the planner just
    searched and failed. `want` is cells mode (a sequence of (row, col,
    target_colour)) or predicate mode (an abduced predicate dict); `frame`
    the live workspace ((row, col) grid); `gamma` the effects.Gamma store;
    `avatar` the self-locus cell (row, col) or None; `deltas` per-action
    (dr, dc) (enables.book_deltas' shape); `fatal` the frontier mask already
    in (row, col) (enables.fatal_cells' output).

    Returns a dict ALWAYS (containment: never raises):
      {"composite": id-or-None, "chain": [part ids] (mint order),
       "actions": [BODY actions], "price": derived-or-None,
       "reason": fixed token, "candidates"/"proposed"/"verified": counts}.
    composite is non-None ONLY on reason "composed" -- and it is a CANDIDATE:
    nothing marks it citable (stage 4's settlement wire)."""
    out: Dict[str, Any] = {"composite": None, "chain": [], "actions": [],
                           "price": None, "reason": R_ERROR,
                           "candidates": 0, "proposed": 0, "verified": 0}
    try:
        return _attempt(out, want, frame, gamma, avatar, deltas, fatal,
                        game, level)
    except Exception:
        return out


def _attempt(out: Dict[str, Any], want: Any, frame: Any, gamma: Any,
             avatar: Optional[Tuple[int, int]],
             deltas: Dict[int, Tuple[int, int]],
             fatal: Optional[Set[Tuple[int, int]]],
             game: str, level: int) -> Dict[str, Any]:
    # -- the WANT, translated (conservative, stated) ---------------------------
    cells: Optional[List[Tuple[int, int, int]]] = None
    pred: Optional[Dict[str, Any]] = None
    if isinstance(want, dict):
        pred = want
        colours = _pred_colours(want)
        if colours is None:
            out["reason"] = R_WANT_UNDERIVABLE
            return out
    else:
        cells = _want_cells(want)
        if cells is None or not cells:
            out["reason"] = R_EMPTY_WANT
            return out
        colours = {t for _r, _c, t in cells}
    if not colours:
        out["reason"] = R_EMPTY_WANT
        return out
    # -- the frame -------------------------------------------------------------
    f = np.asarray(frame)
    if f.ndim != 2 or f.size == 0:
        out["reason"] = R_NO_FRAME
        return out
    shape = (int(f.shape[0]), int(f.shape[1]))
    # -- the pool (stream order; LAST record per id wins -- the supersede) -----
    recs = gamma.fabric.query("collective", gamma.TOPIC,
                              where=lambda r: r.get("game") == str(game))
    order: List[str] = []
    atoms: Dict[str, Any] = {}
    for rec in recs:
        aid = rec.get("id")
        if not aid:
            continue
        if str(aid) not in atoms:
            order.append(str(aid))
        atoms[str(aid)] = rec.get("atom")
    # -- Gamma candidates: effect intersects WANT (stored signatures only) -----
    cand = [aid for aid in order
            if colours & {int(v)
                          for v in _app.psig_of(atoms.get(aid))["written"]}]
    out["candidates"] = len(cand)
    if not cand:
        out["reason"] = R_NO_CANDIDATES
        return out
    # -- the within-Gamma enabler index (stage 2's edge), computed lazily ------
    enablers: Optional[Dict[str, List[str]]] = None

    def _enablers_of(bid: str) -> List[str]:
        nonlocal enablers
        if enablers is None:
            fsig = _app.frame_signature([f])
            edges = _enables.enables_edges(order, atoms, fsig)
            enablers = {}
            for a, outs in edges.items():
                for b in outs:
                    enablers.setdefault(b, []).append(a)
        return enablers.get(bid, [])

    # -- proposals: [BODY prefix..., enabler?, candidate] ----------------------
    # Each: (body_ids, trace, core_ids, body_actions); body unresolvable ->
    # proposed-unverified (counted, never simulated, never minted).
    proposals: List[Tuple[Optional[List[str]],
                          Optional[List[Tuple[int, int]]],
                          List[str], List[int]]] = []
    for bid in cand:
        atom = atoms.get(bid)
        anch = _anchors(f, atom)
        off = _enables.act_offset_of(atom)
        if anch:
            if off is None or (avatar is not None and any(
                    (a[0] + off[0], a[1] + off[1]) == tuple(avatar)
                    for a in anch)):
                proposals.append(([], None, [bid], []))
                continue
            if avatar is None:
                continue                       # positional atom, no self-locus
            reach = _enables.cross_shelf_reach(atom, anch, avatar, deltas,
                                               shape, fatal=fatal)
            if reach is None:
                continue                       # unreachable: stated, no guess
            body: Optional[List[str]] = []
            for action in reach["chain"]:
                mid = _body_atom_id(order, atoms, int(action),
                                    deltas.get(int(action), (0, 0)))
                if mid is None:
                    body = None                # unmintable AND unsimulable
                    break
                body.append(mid)
            proposals.append((body, list(reach["cells"]), [bid],
                              [int(a) for a in reach["chain"]]))
        else:
            for enabler in _enablers_of(bid):
                if _anchors(f, atoms.get(enabler)):
                    proposals.append(([], None, [enabler, bid], []))
    out["proposed"] = len(proposals)
    if not proposals:
        out["reason"] = R_UNREACHABLE
        return out
    # -- simulate (the decider), rank verified by the DERIVED price ------------
    scored: List[Tuple[float, int, List[str], List[int],
                       List[np.ndarray]]] = []
    for idx, (body, trace, core, actions) in enumerate(proposals):
        if body is None:
            continue                           # outside the simulable scope
        frames = _simulate(f, atoms, body, trace, core, cells, pred)
        if frames is None:
            continue
        parts = list(body) + list(core)
        csig = _app.composite_signature(parts, gamma.get)
        price = float(csig["price"]) if csig is not None else float("inf")
        scored.append((price, idx, parts, actions, frames))
    out["verified"] = len(scored)
    if not scored:
        out["reason"] = R_UNVERIFIED
        return out
    scored.sort(key=lambda s: (s[0], s[1]))    # cheapest; discovery order ties
    price, _idx, parts, actions, frames = scored[0]
    cid = gamma.compose(parts, str(game), int(level))
    if cid is None:
        return out                             # R_ERROR: compose refused
    out.update({"composite": str(cid), "chain": list(parts),
                "actions": list(actions),
                "price": (None if price == float("inf") else int(price)),
                "reason": COMPOSED,
                # STAGE 4's inputs: the plan-time frame, the predicted frame
                # after each part, the WANT cells (None in predicate mode).
                # Predictions, not claims -- the record minted above carries
                # no settlement field; only live_settle ever writes one.
                "frame0": f.copy(), "frames": list(frames),
                "want_cells": ([(r, c) for r, c, _t in cells]
                               if cells is not None else None)})
    return out


# ═════════════════════════════════════════════════════════════════════════════
# COMPOSER STAGE 4: THE SETTLEMENT WIRE (PREREG_COMPOSER_STAGE4_SETTLEMENT.md)
#
# ONE transition: CANDIDATE -> SETTLED, written ONLY by live_settle after
# settle_verdict compared the chain's predicted final frame against the LIVE
# frame observed when the driven chain completed. Simulation never settles
# (_simulate returns predictions; nothing here reads them as outcomes).
# Failure routes through machinery that already exists: scheduler.route_abort
# names world-moved vs plan-wrong from state keys; plan-wrong tightens the
# MISPREDICTING COMPONENT through the mint's own conflict/reinstate path
# (MDLMint._reinstate: context_full reinstated + pinned, superseding append,
# ctx_conflict recorded). Nothing is deleted; the composite stays a candidate.
# CITATION DISCIPLINE: an unsettled composite may appear in a BET, never as
# GROUND -- citation_allowed is the pure rule the shadow gate consumes.
# ═════════════════════════════════════════════════════════════════════════════

SETTLED_FIELD = "settled"              # envelope field; absent until live_settle

ROLE_BET = "BET"                       # proposable: any composite record
ROLE_GROUND = "GROUND"                 # standable: settled records only

# fixed outcome tokens for live_settle (narrated verbatim, never free prose)
S_SETTLED = "settled"                  # written this call: citable from here on
S_ALREADY = "already-settled"          # idempotent: nothing appended
S_NO_DRIVE = "no-drive-record"         # refused: no driven chain to settle
S_NO_RECORD = "no-composite-record"    # refused: the id has no record
S_DIVERGED = "diverged"                # the live frame contradicts the prediction


def drive_record(result: Any) -> Optional[Dict[str, Any]]:
    """The drive stash from a COMPOSED compose_attempt result: the composite
    id, its chain, the plan-time frame, the predicted frame after each part,
    the WANT cells. None unless the result composed and carries one
    predicted frame per part -- a malformed prediction never drives."""
    if not isinstance(result, dict) or result.get("reason") != COMPOSED:
        return None
    chain = [str(p) for p in (result.get("chain") or [])]
    frames = result.get("frames")
    frame0 = result.get("frame0")
    if (not chain or not result.get("composite") or frame0 is None
            or not isinstance(frames, list) or len(frames) != len(chain)):
        return None
    try:
        f0 = np.asarray(frame0)
        fr = [np.asarray(x) for x in frames]
        if f0.ndim != 2 or any(x.shape != f0.shape for x in fr):
            return None
    except Exception:
        return None
    wc = result.get("want_cells")
    return {"composite": str(result["composite"]), "chain": chain,
            "frame0": f0.copy(), "frames": [x.copy() for x in fr],
            "want_cells": ([(int(r), int(c)) for r, c in wc]
                           if wc is not None else None),
            "actions": list(result.get("actions") or [])}


def step_cells(drive: Dict[str, Any], i: int) -> Set[Tuple[int, int]]:
    """The cells part `i` PREDICTED to change: predicted frame after part i
    vs the frame before it (frame0 for i == 0). Empty on any doubt."""
    try:
        frames = drive["frames"]
        before = drive["frame0"] if i == 0 else frames[i - 1]
        after = frames[i]
        return {(int(r), int(c)) for r, c in np.argwhere(before != after)}
    except Exception:
        return set()


def divergence(drive: Dict[str, Any], i: int, live: Any) -> Dict[str, Any]:
    """THE LIVE COMPARISON at step `i` (pure): the observed frame after part
    i against the predicted frame after part i, on the cells the chain
    predicted so far (parts 0..i) -- plus the WANT cells when i is the last
    part (the settle's "match on the WANT cells"). Cells the chain never
    predicted are not contradictions. Returns {"diverged": sorted cells,
    "component": the FIRST part whose own predicted cells include a diverged
    cell (the mispredicting component) or None, "index": its index or None}.
    A shape mismatch diverges on every predicted cell with no component."""
    out: Dict[str, Any] = {"diverged": [], "component": None, "index": None}
    try:
        chain = drive["chain"]
        pred = np.asarray(drive["frames"][i])
        cells: Set[Tuple[int, int]] = set()
        per_step: List[Set[Tuple[int, int]]] = []
        for k in range(i + 1):
            sc = step_cells(drive, k)
            per_step.append(sc)
            cells |= sc
        if i == len(chain) - 1 and drive.get("want_cells"):
            cells |= set(drive["want_cells"])
        obs = np.asarray(live)
        if obs.ndim != 2 or obs.shape != pred.shape:
            out["diverged"] = sorted(cells)
            return out
        h, w = pred.shape
        div = {(r, c) for r, c in cells
               if 0 <= r < h and 0 <= c < w and int(obs[r, c]) != int(pred[r, c])}
        out["diverged"] = sorted(div)
        if div:
            for k, sc in enumerate(per_step):
                if sc & div:
                    out["component"] = str(chain[k])
                    out["index"] = int(k)
                    break
        return out
    except Exception:
        out["diverged"] = [(-1, -1)]            # unreadable: never a match
        return out


def settle_verdict(drive: Dict[str, Any], live: Any) -> Dict[str, Any]:
    """THE settle's live comparison: the chain complete, the predicted FINAL
    frame against the LIVE frame on the WANT cells and every cell the chain
    predicted. {"settled": bool} + divergence()'s fields. Pure: reads the
    drive stash and the live frame, writes nothing."""
    try:
        v = divergence(drive, len(drive["chain"]) - 1, live)
    except Exception:
        v = {"diverged": [(-1, -1)], "component": None, "index": None}
    return {**v, "settled": not v["diverged"]}


def composite_record(gamma: Any, cid: str) -> Optional[Dict[str, Any]]:
    """The LAST stream record for a composite id (Gamma.get's read rule --
    the superseding append IS the update), or None."""
    try:
        recs = gamma.fabric.query("collective", gamma.TOPIC,
                                  where=lambda r: r.get("id") == str(cid))
    except Exception:
        return None
    if not recs:
        return None
    rec = recs[-1]
    return rec if (rec.get("atom") or {}).get("kind") == "COMPOSITE" else None


def is_citable(composite_record: Any) -> bool:
    """THE CITABILITY RULE (pure): a composite record is citable iff its
    envelope carries settled: True -- written only by live_settle, only from
    a live-frame comparison. Anything else (no record, a non-composite,
    a candidate) is not citable."""
    if not isinstance(composite_record, dict):
        return False
    atom = composite_record.get("atom")
    kind = (atom.get("kind") if isinstance(atom, dict)
            else composite_record.get("kind"))
    if kind != "COMPOSITE":
        return False
    return composite_record.get(SETTLED_FIELD) is True


def citation_allowed(composite_record: Any, role: str) -> bool:
    """THE DISCIPLINE (pure): in a BET any composite record may appear
    (proposable-not-standable -- driving it IS the test); as GROUND only a
    settled one (is_citable). Unknown roles are refused."""
    if not isinstance(composite_record, dict):
        return False
    atom = composite_record.get("atom")
    kind = (atom.get("kind") if isinstance(atom, dict)
            else composite_record.get("kind"))
    if kind != "COMPOSITE":
        return False
    if role == ROLE_BET:
        return True
    if role == ROLE_GROUND:
        return is_citable(composite_record)
    return False


def live_settle(gamma: Any, drive: Optional[Dict[str, Any]],
                live: Any) -> Dict[str, Any]:
    """THE ONE WRITER of the settled flag. Refuses without a drive record
    (a settle needs a driven chain, S_NO_DRIVE) or without the composite's
    record (S_NO_RECORD); idempotent on an already-settled composite
    (S_ALREADY, nothing appended). Otherwise settle_verdict decides on the
    LIVE frame: a match -> superseding append, same id, settled: True +
    the settle's facts (Gamma's supersede idiom: dict(rec) appended to the
    same stream; the candidate record stays readable history); a divergence
    -> nothing written, the mispredicting component named (S_DIVERGED).
    Never raises; always returns {"settled", "reason", "written", ...}."""
    out: Dict[str, Any] = {"settled": False, "reason": S_NO_DRIVE,
                           "written": False, "composite": None}
    try:
        if not isinstance(drive, dict) or not drive.get("composite"):
            return out
        cid = str(drive["composite"])
        out["composite"] = cid
        rec = composite_record(gamma, cid)
        if rec is None:
            out["reason"] = S_NO_RECORD
            return out
        if rec.get(SETTLED_FIELD) is True:
            out.update({"settled": True, "reason": S_ALREADY})
            return out
        v = settle_verdict(drive, live)
        if not v["settled"]:
            out.update({"reason": S_DIVERGED, "component": v["component"],
                        "index": v["index"], "diverged": v["diverged"]})
            return out
        sup = dict(rec)
        sup[SETTLED_FIELD] = True                # the transition, recorded
        sup["settle"] = {"steps": len(drive["chain"]),
                         "cells": len({c for k in range(len(drive["chain"]))
                                       for c in step_cells(drive, k)}),
                         "want": len(drive.get("want_cells") or [])}
        gamma.fabric.append("collective", gamma.TOPIC, sup)
        out.update({"settled": True, "reason": S_SETTLED, "written": True})
        return out
    except Exception:
        out["reason"] = R_ERROR
        return out


def conflict_component(mint: Any, gamma: Any, part_id: str,
                       pre_frame: Any) -> Dict[str, Any]:
    """PLAN-WRONG's write, on ONE component, through the mint's EXISTING
    reinstate path (MDLMint._reinstate -- the conflict clause's writer):
    where the component's context is DONT_CARE but its context_full differs
    from the live pre-frame at the matched anchor, those cells are
    reinstated and PINNED (divergence tightens, never loosens), the record
    superseded with the same id and ctx_conflict recorded. A component with
    nothing to tighten (no context_full, or the full context matches too)
    still gets the event recorded -- the divergence is evidence against it
    either way; context_full itself is never touched, nothing is deleted.
    Returns {"conflicted": bool, "tightened": n} (+ "reason" on refusal)."""
    out: Dict[str, Any] = {"conflicted": False, "tightened": 0}
    try:
        if mint is None:
            out["reason"] = "no-mint"
            return out
        recs = gamma.fabric.query("collective", gamma.TOPIC,
                                  where=lambda r: r.get("id") == str(part_id))
        if not recs:
            out["reason"] = "no-record"
            return out
        rec = recs[-1]
        atom = rec.get("atom") or {}
        if atom.get("kind") != "EFFECT":
            out["reason"] = "not-an-effect"
            return out
        ctx = np.asarray(atom.get("context"))
        if ctx.ndim != 2 or ctx.size == 0:
            out["reason"] = "no-context"
            return out
        full = atom.get("context_full")
        fl = np.asarray(full) if full is not None else None
        has_full = fl is not None and fl.shape == ctx.shape
        if not has_full:
            fl = ctx.copy()                      # nothing to reinstate from
        distinguish = np.zeros(ctx.shape, dtype=bool)
        b = np.asarray(pre_frame)
        if b.ndim == 2 and has_full:
            ph, pw = ctx.shape
            for r, c in _effects._context_anchors(b, ctx):
                region = b[r:r + ph, c:c + pw]
                d = (ctx == _effects.DONT_CARE) & (fl != region)
                if bool(d.any()):
                    distinguish = d
                    break                        # one conflict event per atom
        mint._reinstate(str(part_id), rec, atom, fl, distinguish)
        out.update({"conflicted": True, "tightened": int(distinguish.sum())})
        return out
    except Exception:
        out["reason"] = R_ERROR
        return out
