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
    -> verified chains PRICED by the DERIVED price
       (applicability.composite_signature -- the stage-1 derivation) and
       ADMITTED by the mint's own bargain (consumer.extent_bargain -- the
       ONE inequality the import door applies; stage 4.5 made the local
       mint its third consumer), ranked cheapest first
    -> cheapest admitted chain -> Gamma.compose() -> COMPOSITE minted as
       CANDIDATE. Nothing here (or anywhere yet) marks it citable: the
       settlement wire is STAGE 4's build, so every composite this loop
       mints is proposable-not-standable by construction. Simulation NEVER
       counts as the settle (design par.5).

THE SIMULATION APPROACH, EXACT SCOPE (Seat 4's amendment: the algebra
proposes, the simulation decides -- and the boundary of what we can simulate
is GATED, never blurred):
  * A no-movement chain ([B] or [A, B]) simulates exactly: each Gamma seam is
    stamped AT A NAMED ANCHOR (_apply_at: the raw after-patch at a cell the
    same vectorised matcher confirmed) on the running frame; any None kills
    the chain.
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
    FLIPS -- false on the plan-time frame, true on the result (predicate
    mode; goal_abduction.satisfies is the planner's own stopping test, and
    a WANT the frame already satisfies composes NOTHING: reason
    want-already-satisfied, stated before any candidate is read).

STAGE 4.5 -- THE SEAM REPAIRS (record/findings/COMPOSER_SEAM_READ.md: four
silent successes found where stages 1-4 met). Each now fails loudly or
cannot occur:
  #1 a satisfied WANT composes nothing (want-already-satisfied); predicate
     advance means a FLIP against the plan-time baseline; the drive record
     carries the predicate and the live settle re-verifies the flip
     (predicate-unmet) -- want_cells=None never means "no check".
  #2 a chain whose composite_signature is None is REFUSED (csig-underivable),
     never ranked; every local mint is PRICED by the import door's own
     inequality before compose() (price-refused, the price stated).
  #3 ONE ANCHOR: the reach's chosen anchor, the simulation's stamp and the
     drive's click site are the same cell, carried on the chain (no
     anchors[0] assumption anywhere); an offset-less atom composes as a
     no-movement chain ONLY and is never driven from a synthesised site
     (cognitive_loop._w3d_drive shadows it with no-act-offset).
  #4 after a BODY prefix the avatar's colour must occupy the act cell before
     the click seam (the AVATAR-AT-ACT-CELL CHECK); where the plan-time
     frame already wears it there, the shorter chain is proposed and
     preferred (prefix-unnecessary) over billing a prefix that contributed
     nothing; an actually needed prefix is stated prefix-required.
  handoffs: reach["verified"] is READ (True is a contract breach ->
     reach-contract-breach, the whole attempt refused); is_citable /
     citation_allowed read the STREAM RECORD through gamma's record access
     (an atom dict -- gamma.get's shape, which cannot carry the settled
     flag -- is refused, not misread); the loop narrates the avatar
     source (self-cell exact, or centroid-rounded as the stated fallback).

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
cross_shelf_reach SEVERED -> LIVE (record/canon/WIRING_REGISTRY.md).

STAGE 4 (PREREG_COMPOSER_STAGE4_SETTLEMENT.md) appends the settlement wire
at the bottom of this module: drive_record / divergence / settle_verdict /
live_settle / is_citable / citation_allowed / conflict_component. Consumed
by cognitive_loop's _w3d_drive (the drive, under the planner's own gates),
_w3d_continue (the multi-cycle chain) and _w3d_settle (the ONE live_settle
call site, in record_result beside _w2b_abort).

W2c (PREREG_W2C_PLANNER_RETENTION.md, item d): with `retained` (the W2b
scheduler's retention.RetentionStore) an attempt's apply_effect-grade work
is served from the level-scoped store -- _simulate's per-seam applications
and named-anchor stamps through the ONE memo the planner shares, _anchors'
results under (atom content key, frame key) in a SEPARATE structure (an
empty anchor list is raw-path-only knowledge, never a typed None), the
enabler index keyed by (pool mark, frame signature dims+palette), FIFO of 8.
retained=None is today's per-attempt behaviour, byte-identical (the undo).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from engines.egocentric import applicability as _app
from engines.egocentric import effects as _effects
from engines.egocentric import enables as _enables
from engines.egocentric import retention as _ret
from engines.egocentric import standing as _standing

__all__ = ["compose_attempt", "COMPOSED", "R_EMPTY_WANT",
           "R_WANT_UNDERIVABLE", "R_NO_FRAME", "R_NO_CANDIDATES",
           "R_UNREACHABLE", "R_UNVERIFIED", "R_ERROR",
           # stage 4.5: the seam repairs' tokens
           "R_WANT_SATISFIED", "R_CSIG_UNDERIVABLE", "R_PRICE_REFUSED",
           "R_REACH_BREACH", "R_NO_AVATAR", "PREFIX_REQUIRED",
           "PREFIX_UNNECESSARY", "NO_ACT_OFFSET", "NO_ANCHOR", "NO_REACH",
           "AVATAR_EXACT",
           "AVATAR_CENTROID", "AVATAR_NONE", "NOT_A_RECORD", "S_PRED_UNMET",
           "citation_state",
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

# stage 4.5 tokens
R_WANT_SATISFIED = "want-already-satisfied"  # silent #1: the frame already holds the WANT
R_CSIG_UNDERIVABLE = "csig-underivable"  # silent #2: no derived signature -> no mint
R_PRICE_REFUSED = "price-refused"      # silent #2: the mint's bargain refused the chain
R_REACH_BREACH = "reach-contract-breach"  # handoff: a reach claimed verified=True
R_NO_AVATAR = "no-avatar"              # a positional candidate with no self-locus (stated)
PREFIX_REQUIRED = "prefix-required"    # silent #4: the BODY prefix put the avatar there
PREFIX_UNNECESSARY = "prefix-unnecessary"  # silent #4: the act cell already wore it
NO_ACT_OFFSET = "no-act-offset"        # silent #3: compose-only; never driven (PLAN record)
# D-12 (PORT_LOG 2026-08-21): "unreachable" conflated NO-ANCHOR with NO-PATH --
# notes={} on every compose-none line. The two unnoted non-proposal branches
# now state themselves; the reason label is unchanged (the notes separate the
# causes, the label does not).
NO_ANCHOR = "no-anchor"                # candidate has no anchor AND no enabler anchors
NO_REACH = "no-reach"                  # anchored + offset + avatar, but the reach found no chain
AVATAR_EXACT = "self-cell"             # handoff: the self-locus exact cell was used
AVATAR_CENTROID = "centroid-rounded"   # handoff: the stated fallback (float mean, rounded)
AVATAR_NONE = "no-avatar"              # handoff: no self-locus at all
NOT_A_RECORD = "not-a-stream-record"   # handoff: gamma.get's atom cannot carry settled

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


def _satisfied(frame: np.ndarray,
               cells: Optional[List[Tuple[int, int, int]]],
               pred: Optional[Dict[str, Any]]) -> bool:
    """SILENT #1's guard: the WANT already holds in `frame` -- every want
    cell is at its target (cells mode), or the predicate is true (predicate
    mode). A satisfied WANT composes nothing; nothing can advance it."""
    if cells is not None:
        h, w = frame.shape[:2]
        return all(0 <= r < h and 0 <= c < w and int(frame[r, c]) == int(t)
                   for r, c, t in cells)
    from engines.egocentric.goal_abduction import satisfies
    return bool(satisfies(pred, frame))


# ── the pieces of the loop (each pure over its inputs) ────────────────────────

def _anchors(frame: np.ndarray, atom: Any, sess: Any = None,
             aid: Any = None) -> List[Tuple[int, int]]:
    """The candidate's matching anchors in `frame` via the EXISTING vectorised
    matcher (effects._context_anchors -- the same scan apply_effect runs).
    [] on any doubt: no anchor is never a guessed anchor. W2c: with a
    session the result is retained under (content key, frame key) -- the
    scan runs once per (atom, frame) per level; the empty list is stored
    THERE and never as a memo None (KN5)."""
    if not isinstance(atom, dict) or atom.get("kind") != "EFFECT":
        return []
    if sess is not None:
        try:
            return sess.anchors(aid, atom, frame, _ret.state_key(frame),
                                _scan_anchors)
        except Exception:
            return []
    return _scan_anchors(frame, atom)


def _apply_at(atom: Any, frame: np.ndarray,
              anchor: Tuple[int, int], sess: Any = None,
              aid: Any = None) -> Optional[np.ndarray]:
    """STAGE 4.5 (silent #3/#4): the Gamma seam stamped AT A NAMED ANCHOR --
    the atom's stored after-patch written at `anchor` (row, col) with
    apply_effect's own masked-stamp rule (a DONT_CARE after-cell leaves the
    frame's value), ONLY if `anchor` is among the cells the same vectorised
    matcher confirms for the context patch. None otherwise: the reconciled
    anchor is either a real match or the seam fails -- never apply's first
    anchor by default. The raw stored patch is the application this anchor
    means (the anchor came from the raw-context matcher); a typed op's
    parameterised path is not consulted here. W2c: with a session the
    membership read hits the anchors store and the stamp goes through memo
    (a) under the atom's content key + the anchor."""
    if tuple(anchor) not in _anchors(frame, atom, sess, aid):
        return None
    if sess is not None:
        try:
            return sess.apply_at(aid, atom, frame, _ret.state_key(frame),
                                 tuple(anchor), _stamp_at)
        except Exception:
            return None
    return _stamp_at(atom, frame, anchor)


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
    predicate FLIPPED: false on the pre-frame, true on the result (predicate
    mode, baseline compared -- silent #1's repair: holding already is not
    advancing)."""
    if cells is not None:
        h, w = result.shape[:2]
        for r, c, t in cells:
            if (0 <= r < h and 0 <= c < w and int(result[r, c]) == int(t)
                    and int(frame[r, c]) != int(t)):
                return True
        return False
    from engines.egocentric.goal_abduction import satisfies
    return (not bool(satisfies(pred, frame))) and bool(satisfies(pred, result))


def _simulate(frame: np.ndarray, atoms: Dict[str, Any],
              body_ids: List[str], trace: Optional[List[Tuple[int, int]]],
              core: List[str],
              cells: Optional[List[Tuple[int, int, int]]],
              pred: Optional[Dict[str, Any]],
              anchor: Optional[Tuple[int, int]] = None,
              act: Optional[Tuple[int, int]] = None,
              avatar_colour: Optional[int] = None,
              sess: Any = None,
              ) -> Optional[Tuple[List[np.ndarray],
                                  List[Optional[Tuple[int, int]]]]]:
    """Simulate the whole chain seam by seam on a COPY (self-settlement is
    banned by design par.5 -- this is admission-to-candidacy, nothing more).
    None on any seam failure, endpoint mismatch, a failed AVATAR-AT-ACT-CELL
    CHECK, or a WANT not advanced; otherwise (the PREDICTED FRAME AFTER EACH
    PART in chain order, the ANCHOR each Gamma part was stamped at -- None
    for BODY parts). Stage 4 carries both in the drive stash: the frames are
    compared against the LIVE frame and the anchors are the drive's click
    sites, so reach, simulation and drive name ONE anchor (silent #3). The
    final Gamma seam stamps at `anchor` when the proposal reconciled one
    (the reach's), else at the matcher's first anchor on the running frame
    -- recorded either way. The simulation itself never settles anything.
    W2c: every per-seam application goes through the session's memo (a)
    when one is given (_seam_apply / _apply_at); the predicted frames are
    COPIES, so served frozen arrays never reach the drive stash."""
    cur = frame.copy()
    frames: List[np.ndarray] = []
    anchors: List[Optional[Tuple[int, int]]] = []
    for i, bid in enumerate(body_ids):
        nxt = _seam_apply(sess, bid, atoms.get(bid), cur)
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
        anchors.append(None)
    if body_ids and act is not None:
        # THE AVATAR-AT-ACT-CELL CHECK (silent #4): after the prefix the
        # avatar's colour must occupy the act cell, or the prefix did not
        # deliver what the click seam stands on.
        try:
            if (avatar_colour is None
                    or int(cur[int(act[0]), int(act[1])]) != int(avatar_colour)):
                return None
        except (IndexError, TypeError, ValueError):
            return None
    for k, aid in enumerate(core):
        atom = atoms.get(aid)
        at: Optional[Tuple[int, int]] = (
            anchor if (k == len(core) - 1 and anchor is not None) else None)
        if at is None:
            found = _anchors(cur, atom, sess, aid)
            if not found:
                return None
            at = found[0]
        res = _apply_at(atom, cur, at, sess, aid)
        if res is None:
            return None
        cur = np.asarray(res)
        frames.append(cur.copy())
        anchors.append((int(at[0]), int(at[1])))
    if not _advances(frame, cur, cells, pred):
        return None
    return frames, anchors


def _proposal(body: Optional[List[str]],
              trace: Optional[List[Tuple[int, int]]], core: List[str],
              actions: List[int], anchor: Optional[Tuple[int, int]],
              act: Optional[Tuple[int, int]],
              prefix: Optional[str]) -> Dict[str, Any]:
    """One proposed chain: [BODY prefix..., core...] with the RECONCILED
    anchor (the cell the final Gamma seam stamps at and the drive clicks
    from) and act cell (anchor + act_offset, where the avatar must stand).
    body None = the movement is unmintable AND unsimulable (proposed-
    unverified, counted, never minted)."""
    return {"body": body, "trace": trace, "core": list(core),
            "actions": list(actions), "anchor": anchor, "act": act,
            "prefix": prefix}


# ── THE COMPOSE ATTEMPT ───────────────────────────────────────────────────────

def compose_attempt(want: Any, frame: Any, gamma: Any,
                    avatar: Optional[Tuple[int, int]],
                    deltas: Dict[int, Tuple[int, int]],
                    fatal: Optional[Set[Tuple[int, int]]],
                    game: str, level: int,
                    retained: Any = None) -> Dict[str, Any]:
    """One compose attempt: the loop above, on the WANT the planner just
    searched and failed. `want` is cells mode (a sequence of (row, col,
    target_colour)) or predicate mode (an abduced predicate dict); `frame`
    the live workspace ((row, col) grid); `gamma` the effects.Gamma store;
    `avatar` the self-locus cell (row, col) or None; `deltas` per-action
    (dr, dc) (enables.book_deltas' shape); `fatal` the frontier mask already
    in (row, col) (enables.fatal_cells' output); `retained` (W2c) the
    scheduler's retention.RetentionStore or None (per-attempt, the undo).

    Returns a dict ALWAYS (containment: never raises):
      {"composite": id-or-None, "chain": [part ids] (mint order),
       "actions": [BODY actions], "price": derived-or-None,
       "reason": fixed token, "candidates"/"proposed"/"verified": counts,
       "refused": [{"reason": token, "price": n-or-None}] (verified chains
       the pricing refused, discovery order), "notes": {token: count}
       (stated per-candidate non-proposals)}.
    composite is non-None ONLY on reason "composed" -- and it is a CANDIDATE:
    nothing marks it citable (stage 4's settlement wire). A composed result
    also carries "anchor"/"anchors"/"act"/"prefix"/"pred" -- the drive's
    reconciled inputs (drive_record)."""
    out: Dict[str, Any] = {"composite": None, "chain": [], "actions": [],
                           "price": None, "reason": R_ERROR,
                           "candidates": 0, "proposed": 0, "verified": 0,
                           "refused": [], "notes": {}}
    try:
        return _attempt(out, want, frame, gamma, avatar, deltas, fatal,
                        game, level, retained)
    except Exception:
        return out


def _attempt(out: Dict[str, Any], want: Any, frame: Any, gamma: Any,
             avatar: Optional[Tuple[int, int]],
             deltas: Dict[int, Tuple[int, int]],
             fatal: Optional[Set[Tuple[int, int]]],
             game: str, level: int, retained: Any = None) -> Dict[str, Any]:
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
    # -- SILENT #1 CLOSED: a WANT the frame already holds composes NOTHING ----
    if _satisfied(f, cells, pred):
        out["reason"] = R_WANT_SATISFIED
        return out
    # -- the avatar: its cell and the colour it wears there (the patch the
    #    BODY prefix moves; the AVATAR-AT-ACT-CELL CHECK compares against it)
    av: Optional[Tuple[int, int]] = None
    av_colour: Optional[int] = None
    if avatar is not None:
        try:
            cand_av = (int(avatar[0]), int(avatar[1]))
            if 0 <= cand_av[0] < shape[0] and 0 <= cand_av[1] < shape[1]:
                av = cand_av
                av_colour = int(f[av[0], av[1]])
        except (TypeError, ValueError, IndexError):
            av = None
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
    # W2c: the session over the retained store (None = per-attempt work);
    # opened AFTER the pool read so the attempt's instrument counts only
    # apply_effect-grade work, and bound to (game, level) like the planner's.
    sess = None if retained is None else _ret.Session(retained, game, level)
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

    def _build_enablers() -> Dict[str, List[str]]:
        fsig = _app.frame_signature([f])
        edges = _enables.enables_edges(order, atoms, fsig)
        idx: Dict[str, List[str]] = {}
        for a, outs in edges.items():
            for b in outs:
                idx.setdefault(b, []).append(a)
        return idx

    def _enablers_of(bid: str) -> List[str]:
        nonlocal enablers
        if enablers is None:
            if sess is None:
                enablers = _build_enablers()
            else:
                # W2c (d): retained under (pool mark, frame signature dims +
                # palette), FIFO of ENABLERS_CAP -- the pool mark is the
                # stream's own (record count, last seq): any mint, import or
                # supersede appends and moves it.
                enablers = sess.enablers(_pool_mark(recs), _fsig_key(f),
                                         _build_enablers)
        return enablers.get(bid, [])

    notes: Dict[str, int] = out["notes"]

    def _note(token: str) -> None:
        notes[token] = int(notes.get(token, 0)) + 1

    # -- proposals: [BODY prefix..., enabler?, candidate] ----------------------
    proposals: List[Dict[str, Any]] = []
    for bid in cand:
        atom = atoms.get(bid)
        anch = _anchors(f, atom, sess, bid)
        off = _enables.act_offset_of(atom)
        if anch:
            if off is None:
                # SILENT #3: no act_offset -> a no-movement chain ONLY. The
                # composite is compose-only; the drive refuses it
                # (no-act-offset) rather than guessing a site.
                _note(NO_ACT_OFFSET)
                proposals.append(_proposal([], None, [bid], [], None, None,
                                           None))
                continue
            at_avatar = [a for a in anch
                         if av is not None
                         and (a[0] + off[0], a[1] + off[1]) == av]
            if at_avatar:
                # the avatar already stands at this anchor's act cell: THAT
                # anchor is the reconciled one (not anchors[0])
                proposals.append(_proposal([], None, [bid], [], at_avatar[0],
                                           av, None))
                continue
            if av is None:
                _note(R_NO_AVATAR)           # positional atom, no self-locus
                continue
            reach = _enables.cross_shelf_reach(atom, anch, av, deltas,
                                               shape, fatal=fatal)
            if reach is None:
                _note(NO_REACH)                # D-12: no path -- stated, no guess
                continue
            if reach.get("verified") is not False:
                # THE CONTRACT, READ: the algebra may only PROPOSE. A reach
                # claiming otherwise is a breach -- the attempt refuses.
                out["reason"] = R_REACH_BREACH
                return out
            anchor = (int(reach["anchor"][0]), int(reach["anchor"][1]))
            act = (int(reach["target"][0]), int(reach["target"][1]))
            actions = [int(a) for a in reach["chain"]]
            body: Optional[List[str]] = []
            for action in actions:
                mid = _body_atom_id(order, atoms, action,
                                    deltas.get(action, (0, 0)))
                if mid is None:
                    body = None                # unmintable AND unsimulable
                    break
                body.append(mid)
            if (av_colour is not None
                    and int(f[act[0], act[1]]) == int(av_colour)):
                # SILENT #4: the plan-time frame ALREADY wears the avatar's
                # colour at the act cell -- the click seam verifies without
                # the prefix. Propose the shorter chain first; the price
                # ranking prefers it (shorter is never dearer).
                proposals.append(_proposal([], None, [bid], [], anchor, act,
                                           PREFIX_UNNECESSARY))
            proposals.append(_proposal(body, list(reach["cells"]), [bid],
                                       actions, anchor, act, PREFIX_REQUIRED))
        else:
            n_before = len(proposals)
            for enabler in _enablers_of(bid):
                if _anchors(f, atoms.get(enabler), sess, enabler):
                    proposals.append(_proposal([], None, [enabler, bid], [],
                                               None, None, None))
            if len(proposals) == n_before:
                _note(NO_ANCHOR)               # D-12: no candidate/enabler anchor
    out["proposed"] = len(proposals)
    if not proposals:
        out["reason"] = R_UNREACHABLE
        return out
    # -- simulate (the decider); PRICE + ADMIT (the mint's own bargain) -------
    from engines.egocentric import consumer as _consumer  # lazy: no cycle
    scored: List[Tuple[float, int, Dict[str, Any], List[str], List[np.ndarray],
                       List[Optional[Tuple[int, int]]]]] = []
    verified = 0
    refused: List[Dict[str, Any]] = out["refused"]
    for idx, p in enumerate(proposals):
        if p["body"] is None:
            continue                           # outside the simulable scope
        sim = _simulate(f, atoms, p["body"], p["trace"], p["core"], cells,
                        pred, anchor=p["anchor"], act=p["act"],
                        avatar_colour=av_colour, sess=sess)
        if sim is None:
            continue
        verified += 1
        frames, anchors = sim
        parts = list(p["body"]) + list(p["core"])
        # SILENT #2 CLOSED: no derived signature -> NO mint (never inf-ranked)
        csig = _app.composite_signature(parts, gamma.get)
        if csig is None or int(csig.get("changed", 0)) <= 0:
            refused.append({"reason": R_CSIG_UNDERIVABLE, "price": None})
            continue
        price = int(csig["price"])
        # the THIRD CONSUMER of the derived price: the local mint pays the
        # SAME inequality the import door applies (consumer.extent_bargain)
        bargain = _consumer.extent_bargain(int(csig["changed"]), float(price))
        if not bargain["admit"]:
            refused.append({"reason": R_PRICE_REFUSED, "price": price,
                            "cost": bargain["cost"], "bar": bargain["bar"]})
            continue
        scored.append((float(price), idx, p, parts, frames, anchors))
    out["verified"] = verified
    if not scored:
        if refused:
            out["reason"] = str(refused[0]["reason"])
            out["price"] = refused[0]["price"]
        else:
            out["reason"] = R_UNVERIFIED
        return out
    scored.sort(key=lambda s: (s[0], s[1]))    # cheapest; discovery order ties
    price_f, _idx, p, parts, frames, anchors = scored[0]
    cid = gamma.compose(parts, str(game), int(level))
    if cid is None:
        return out                             # R_ERROR: compose refused
    out.update({"composite": str(cid), "chain": list(parts),
                "actions": list(p["actions"]), "price": int(price_f),
                "reason": COMPOSED,
                # STAGE 4's inputs: the plan-time frame, the predicted frame
                # after each part, the WANT cells (None in predicate mode --
                # then "pred" carries the predicate the settle re-verifies),
                # the reconciled anchors (the drive's click sites).
                # Predictions, not claims -- the record minted above carries
                # no settlement field; only live_settle ever writes one.
                "frame0": f.copy(), "frames": list(frames),
                "anchors": list(anchors), "anchor": anchors[-1],
                "act": p["act"], "prefix": p["prefix"],
                "pred": (dict(pred) if pred is not None else None),
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
S_PRED_UNMET = "predicate-unmet"       # stage 4.5: the predicate did not flip live


def drive_record(result: Any) -> Optional[Dict[str, Any]]:
    """The drive stash from a COMPOSED compose_attempt result: the composite
    id, its chain, the plan-time frame, the predicted frame after each part,
    the reconciled anchor per part, the WANT cells OR the predicate. None
    unless the result composed and carries one predicted frame and one
    anchor slot per part -- a malformed prediction never drives. STAGE 4.5:
    want_cells None with no predicate is refused (None never means "no
    check"), and a predicate already true on the plan-time frame is refused
    (the settle verifies a FLIP; its baseline must be false)."""
    if not isinstance(result, dict) or result.get("reason") != COMPOSED:
        return None
    chain = [str(p) for p in (result.get("chain") or [])]
    frames = result.get("frames")
    frame0 = result.get("frame0")
    anchors = result.get("anchors")
    if (not chain or not result.get("composite") or frame0 is None
            or not isinstance(frames, list) or len(frames) != len(chain)
            or not isinstance(anchors, list) or len(anchors) != len(chain)):
        return None
    try:
        f0 = np.asarray(frame0)
        fr = [np.asarray(x) for x in frames]
        if f0.ndim != 2 or any(x.shape != f0.shape for x in fr):
            return None
        an = [(None if a is None else (int(a[0]), int(a[1]))) for a in anchors]
    except Exception:
        return None
    wc = result.get("want_cells")
    pred = result.get("pred")
    if wc is None and not isinstance(pred, dict):
        return None                            # no WANT to verify: never drives
    if isinstance(pred, dict):
        from engines.egocentric.goal_abduction import satisfies
        if satisfies(pred, f0):
            return None                        # no flip possible: never drives
    act = result.get("act")
    return {"composite": str(result["composite"]), "chain": chain,
            "frame0": f0.copy(), "frames": [x.copy() for x in fr],
            "anchors": an, "anchor": an[-1],
            "act": (None if act is None else (int(act[0]), int(act[1]))),
            "prefix": result.get("prefix"),
            "pred": (dict(pred) if isinstance(pred, dict) else None),
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
    predicted. {"settled": bool, "predicate": flip-or-None} + divergence()'s
    fields. STAGE 4.5: in predicate mode (want_cells None) the predicate
    must FLIP on the LIVE frame -- false on the plan-time frame, true on the
    observed one -- or the verdict is not settled (predicate-unmet); a cell
    match alone never settles a predicate WANT. Pure: reads the drive stash
    and the live frame, writes nothing."""
    try:
        v = divergence(drive, len(drive["chain"]) - 1, live)
    except Exception:
        v = {"diverged": [(-1, -1)], "component": None, "index": None}
    settled = not v["diverged"]
    flip: Optional[bool] = None
    try:
        if drive.get("want_cells") is None:
            pred = drive.get("pred")
            from engines.egocentric.goal_abduction import satisfies
            flip = bool(isinstance(pred, dict)
                        and not satisfies(pred, drive["frame0"])
                        and satisfies(pred, live))
            settled = settled and flip
    except Exception:
        flip = False
        settled = False
    return {**v, "settled": settled, "predicate": flip}


def composite_record(gamma: Any, cid: str) -> Optional[Dict[str, Any]]:
    """The LAST stream record for a composite id (Gamma.get's read rule --
    the superseding append IS the update), or None. THIS is the record
    access every citability read goes through: the envelope carries the
    settled flag; gamma.get's atom cannot."""
    try:
        recs = gamma.fabric.query("collective", gamma.TOPIC,
                                  where=lambda r: r.get("id") == str(cid))
    except Exception:
        return None
    if not recs:
        return None
    rec = recs[-1]
    return rec if (rec.get("atom") or {}).get("kind") == "COMPOSITE" else None


def _as_record(composite_record_or_id: Any, gamma: Any) -> Optional[Dict[str, Any]]:
    """The stream record behind a citability read: a record dict is taken as
    is; an id string is resolved through composite_record(gamma, id). An
    ATOM dict -- gamma.get's shape: kind COMPOSITE at the top level, no
    envelope -- is REFUSED loudly (TypeError, NOT_A_RECORD): it cannot carry
    the settled flag, so reading it would silently say "never citable".
    Anything else (None, non-dict, an empty dict) reads as no record."""
    x = composite_record_or_id
    if isinstance(x, str):
        if gamma is None:
            raise TypeError("is_citable: %s -- an id needs gamma to reach the "
                            "stream record" % NOT_A_RECORD)
        return composite_record(gamma, x)
    if not isinstance(x, dict):
        return None
    if "atom" not in x and x.get("kind") == "COMPOSITE":
        raise TypeError("is_citable: %s -- gamma.get's atom cannot carry %r; "
                        "pass composite_record(gamma, id) or (id, gamma)"
                        % (NOT_A_RECORD, SETTLED_FIELD))
    return x


def citation_state(gamma: Any, cid: str) -> Dict[str, Any]:
    """The production read (pure over the stream): {"citable": bool,
    "reason": token} for a composite id through gamma's record access --
    "settled" (citable), "candidate" (a record without the flag), or
    "no-record" (no composite record for the id)."""
    rec = composite_record(gamma, cid)
    if rec is None:
        return {"citable": False, "reason": S_NO_RECORD}
    if rec.get(SETTLED_FIELD) is True:
        return {"citable": True, "reason": S_SETTLED}
    return {"citable": False, "reason": "candidate"}


def is_citable(composite_record: Any, gamma: Any = None) -> bool:
    """THE CITABILITY RULE (pure): a composite record is citable iff its
    envelope carries settled: True -- written only by live_settle, only from
    a live-frame comparison. Reads the STREAM RECORD (or an id resolved via
    `gamma`); an atom dict is refused (TypeError, NOT_A_RECORD) rather than
    misread. Anything else (no record, a non-composite, a candidate) is not
    citable."""
    rec = _as_record(composite_record, gamma)
    if rec is None:
        return False
    if (rec.get("atom") or {}).get("kind") != "COMPOSITE":
        return False
    return rec.get(SETTLED_FIELD) is True


def citation_allowed(composite_record: Any, role: str,
                     gamma: Any = None) -> bool:
    """THE DISCIPLINE (pure): in a BET any composite record may appear
    (proposable-not-standable -- driving it IS the test); as GROUND only a
    settled one (is_citable). Unknown roles are refused. Same record access
    as is_citable: a stream record or (id, gamma); never an atom dict."""
    rec = _as_record(composite_record, gamma)
    if rec is None:
        return False
    if (rec.get("atom") or {}).get("kind") != "COMPOSITE":
        return False
    if role == ROLE_BET:
        return True
    if role == ROLE_GROUND:
        return is_citable(rec)
    return False


def live_settle(gamma: Any, drive: Optional[Dict[str, Any]],
                live: Any, ep: Optional[int] = None) -> Dict[str, Any]:
    """THE ONE WRITER of the settled flag. Refuses without a drive record
    (a settle needs a driven chain, S_NO_DRIVE) or without the composite's
    record (S_NO_RECORD); idempotent on an already-settled composite
    (S_ALREADY, nothing appended). Otherwise settle_verdict decides on the
    LIVE frame: a match -> superseding append, same id, settled: True +
    the settle's facts (Gamma's supersede idiom: dict(rec) appended to the
    same stream; the candidate record stays readable history); a divergence
    -> nothing written, the mispredicting component named (S_DIVERGED); a
    predicate that did not flip live -> nothing written (S_PRED_UNMET).
    Never raises; always returns {"settled", "reason", "written", ...}.

    R3/R4 (PREREG_STANDING_HALF_LIFE_ATOMS.md): the settle append carries the
    episode ordinal `ep` when the caller supplies it -- the CANDIDATE ->
    SETTLED transition IS a composite's earn event (e3), and an event with no
    clock is not counted. ep=None (every pre-existing caller) stamps nothing
    and the record is byte-identical to this build's predecessor."""
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
            out.update({"reason": (S_DIVERGED if v["diverged"] else S_PRED_UNMET),
                        "component": v["component"], "index": v["index"],
                        "diverged": v["diverged"],
                        "predicate": v.get("predicate")})
            return out
        sup = dict(rec)
        sup[SETTLED_FIELD] = True                # the transition, recorded
        facts = {"steps": len(drive["chain"]),
                 "cells": len({c for k in range(len(drive["chain"]))
                               for c in step_cells(drive, k)}),
                 "want": len(drive.get("want_cells") or [])}
        if v.get("predicate") is not None:
            facts["predicate"] = bool(v["predicate"])
        sup["settle"] = facts
        if ep is not None:
            sup["ep"] = int(ep)              # R3/R4: the earn event's clock
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
        # R3/R4: THE DISJOINTNESS MARKER. This path writes a ctx_conflict AND
        # a plan-wrong ledger increment for ONE event; the append is stamped
        # via="plan-wrong" so the standing reader counts it under m1 only.
        mint._reinstate(str(part_id), rec, atom, fl, distinguish,
                        via=_standing.VIA_PLAN_WRONG)
        out.update({"conflicted": True, "tightened": int(distinguish.sum())})
        return out
    except Exception:
        out["reason"] = R_ERROR
        return out


# ═════════════════════════════════════════════════════════════════════════════
# W2c (PREREG_W2C_PLANNER_RETENTION.md, item d): module-bottom helpers -- the
# cold paths the session wraps, and the two retention keys. Nothing here runs
# differently with retained=None; the helpers ARE the pre-W2c code, factored.
# ═════════════════════════════════════════════════════════════════════════════

def _scan_anchors(frame: np.ndarray, atom: Any) -> List[Tuple[int, int]]:
    """The cold anchor scan (pre-W2c _anchors body, verbatim): every anchor
    the vectorised matcher confirms for the atom's context patch."""
    try:
        ctx = np.asarray(atom.get("context"))
        if ctx.ndim != 2 or ctx.size == 0:
            return []
        return [(int(r), int(c))
                for r, c in _effects._context_anchors(frame, ctx)]
    except Exception:
        return []


def _stamp_at(atom: Any, frame: np.ndarray,
              anchor: Tuple[int, int]) -> Optional[np.ndarray]:
    """The cold named-anchor stamp (pre-W2c _apply_at body after the
    membership check, verbatim): the after-patch written at `anchor` with
    apply_effect's masked-stamp rule, on a copy."""
    try:
        ctx = np.asarray(atom["context"])
        out = np.asarray(atom["transform"]["after"])
        if out.shape != ctx.shape:
            return None
        r, c = int(anchor[0]), int(anchor[1])
        ph, pw = ctx.shape
        res = np.asarray(frame).copy()
        stamp = out != _effects.DONT_CARE
        res[r:r + ph, c:c + pw][stamp] = out[stamp]
        return res
    except Exception:
        return None


def _seam_apply(sess: Any, aid: Any, atom: Any,
                frame: np.ndarray) -> Optional[np.ndarray]:
    """A BODY seam: apply_effect(atom, frame) -- through memo (a) when a
    session exists (the key is the atom's content key + the frame key)."""
    if sess is None:
        return _effects.apply_effect(atom, frame)
    try:
        return sess.apply(aid, atom, frame, _ret.state_key(frame))
    except Exception:
        return None


def _pool_mark(recs: Any) -> Tuple[int, Any]:
    """The pool's change mark: (record count, last record's seq). The stream
    is append-only and a supersede is an append, so any mint, import or
    supersede moves the mark -- the enabler index's validity key."""
    try:
        n = len(recs)
        return (n, None if n == 0 else recs[-1].get("seq"))
    except Exception:
        return (-1, None)


def _fsig_key(frame: np.ndarray) -> Tuple[Any, ...]:
    """The frame signature's hashable (dims, palette) -- what enables_edges
    actually reads of the frame."""
    try:
        fsig = _app.frame_signature([frame]) or {}
        return (int(fsig.get("h", 0)), int(fsig.get("w", 0)),
                tuple(sorted(int(v) for v in (fsig.get("pal") or ()))))
    except Exception:
        return (-1, -1, ())
