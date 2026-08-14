"""consumer.py -- B12 THE TRIANGULATION CONSUMER (C33 §14-16; CK_LEDGER retrieval law).

SIGNATURE-FIRST RECOGNITION, never candidate-first verification: the residual's sigma
is computed INSIDE the home frame, candidate-blind (`describe`), PERSISTED to the queue
stream before any match attempt, and matched against the prediction-signatures atoms
carry from mint time (B13) -- a one-pass lookup over every mounted fabric's atoms,
no application loop. Game ids are runtime keys throughout; nothing here names a game.

THE THREE CONDITIONS are seq-provable from append-only ordering and travel on every
candidate: (1) priority -- sigma's processing-entry seq precedes the consumed marker's
(same stream, strictly ordered); (2) prior existence -- the atom's mint seq (its own
stream) is recorded beside the match seq; (3) independence -- the match compared
signatures only, never the residual's frame against the candidate.

THE REDESCRIPTION LOOP (Gick & Holyoak; Karmiloff-Smith): a miss with near-misses
(all-but-one invariant, failing invariant NAMED) earns exactly ONE retry with the named
axis coarsened; the give-up is an axis-tagged DEFEASIBLE not-found. THE CHAITIN RULE:
an empty search never closes an item -- not-founds reopen when new atoms touch their
axis (the recorded watermark is the visible-atom count).

THE KIN-ECHO LAW (CK_LEDGER ground criterion, the consumer-prereg flag): echo pays the
origin author, and cross-mounted fabrics let an author's own offspring/kin echo its
atoms -- a reputation reading partly owned by its beneficiary. Rule, in full: any
echo/reputation bookkeeping this module writes EXCLUDES candidates whose source lineage
equals the consuming lineage (no echo is ever paid to self or kin), and same-lineage
hits are DOWN-WEIGHTED in ranking (a stranger's equal atom always outranks kin's).
Lineage is read from the atom record's "agent"/"by"/"kin" fields where present; the
candidate's `kin_echo` flag makes the down-weight auditable.

Deterministic, stdlib + numpy only; failures degrade, never raise (house containment).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

__all__ = ["sigma_of", "describe", "match", "consume", "seed_imports",
           "pending", "open_not_found", "candidates", "INVARIANTS"]

QUEUE_TOPIC = "import_queue"
CAND_TOPIC = "import_candidates"
ATOMS_TOPIC = "atoms"

# The match invariants (C33 §16): both sides must carry ALL of them for a verdict;
# "slot" and "mag" are frame-local descriptors, never compared across frames.
INVARIANTS = ("arity", "bbox", "changed", "colour_delta", "conserved")


# ── the shared sigma vocabulary (one currency for holes AND atoms) ────────────

def _bbox_class(h: int, w: int) -> str:
    if h == 1 and w == 1:
        return "cell"
    if h == 1:
        return "row"
    if w == 1:
        return "col"
    return "square" if h == w else "rect"


def _count_class(n: int) -> str:
    if n <= 1:
        return "1"
    if n <= 4:
        return "2-4"
    return "5-16" if n <= 16 else "17+"


def _mag_class(x) -> str:
    if x is None:
        return "unknown"
    x = float(x)
    if x <= 0:
        return "zero"
    if x <= 2:
        return "small"
    return "medium" if x <= 8 else "large"


def sigma_of(before=None, after=None, slot=None, residual=None) -> Dict[str, Any]:
    """The residual/atom signature, computed WITHOUT reference to any candidate.

    Pure, deterministic, JSON-native. With a before/after pair: bbox shape class,
    changed-cell count class, colour-delta set, cell-count conservation, arity.
    Without one the description degrades to slot + magnitude class (retrieval at
    base rate -- the ledger's warning, not a crash)."""
    sig: Dict[str, Any] = {"arity": 2}
    if slot is not None:
        sig["slot"] = str(slot)
    changed: Optional[int] = None
    try:
        if before is not None and after is not None:
            b = np.asarray(before)
            a = np.asarray(after)
            if b.ndim == 2 and b.shape == a.shape and b.size:
                diff = b != a
                changed = int(diff.sum())
                if changed:
                    rows = np.flatnonzero(diff.any(axis=1))
                    cols = np.flatnonzero(diff.any(axis=0))
                    sig["bbox"] = _bbox_class(int(rows[-1] - rows[0] + 1),
                                              int(cols[-1] - cols[0] + 1))
                    sig["changed"] = _count_class(changed)
                    pairs = sorted({(int(s), int(d)) for s, d
                                    in zip(b[diff].tolist(), a[diff].tolist(),
                                           strict=True)})
                    sig["colour_delta"] = [[s, d] for s, d in pairs]
                    sig["conserved"] = bool(np.array_equal(np.sort(b.ravel()),
                                                           np.sort(a.ravel())))
    except Exception:
        pass                    # a malformed patch degrades the description, never crashes
    sig["mag"] = _mag_class(residual if residual is not None else changed)
    return sig


def describe(residual_record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Candidate-blind sigma for one import-queue record (slot, residual magnitude,
    and -- when the record carries before/after patches -- the full invariant set)."""
    rec = residual_record or {}
    residual = rec.get("residual")
    try:
        residual = None if residual is None else float(residual)
    except Exception:
        residual = None
    return sigma_of(rec.get("before"), rec.get("after"),
                    slot=rec.get("slot"), residual=residual)


# ── the match: signature equality, one pass, no application loop ──────────────

def _atom_sigma(rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    atom = rec.get("atom")
    sig = atom.get("sigma") if isinstance(atom, dict) else None
    if not isinstance(sig, dict):
        sig = rec.get("sigma")
    return sig if isinstance(sig, dict) else None


def _coarse(axis: str, value):
    """One step up the granularity ladder for `axis` (the redescription move:
    the named invariant is compared under a coarser projection on BOTH sides)."""
    if axis == "bbox":
        return "line" if value in ("cell", "row", "col") else "block"
    if axis == "colour_delta":
        try:
            return sorted({int(c) for pair in value for c in pair})
        except Exception:
            return "any"
    return "any"


def match(sigma: Dict[str, Any], atoms: Iterable[Dict[str, Any]],
          coarse_axes: Sequence[str] = ()) -> Tuple[List[Dict[str, Any]],
                                                    List[Dict[str, Any]]]:
    """(hits, near_misses) over atom RECORDS: a hit matches every invariant; a
    near-miss matches all but exactly ONE, and names the failing invariant.
    Signature-first: nothing is applied, one pass, no candidate frames touched."""
    hits: List[Dict[str, Any]] = []
    near: List[Dict[str, Any]] = []
    for rec in atoms:
        asig = _atom_sigma(rec)
        if asig is None:
            continue                    # an unsigma'd atom cannot be recognized (backfill)
        if any(k not in sigma or k not in asig for k in INVARIANTS):
            continue                    # impoverished description: base-rate, no verdict
        failed: List[str] = []
        for k in INVARIANTS:
            va, vb = sigma[k], asig[k]
            if k in coarse_axes:
                va, vb = _coarse(k, va), _coarse(k, vb)
            if va != vb:
                failed.append(k)
                if len(failed) > 1:
                    break
        if not failed:
            hits.append(rec)
        elif len(failed) == 1:
            near.append({"id": rec.get("id"), "key": (rec.get("atom") or {}).get("key"),
                         "source_game": rec.get("game"), "failed": failed[0]})
    return hits, near


# ── fabric views: own queue (local), everyone's atoms (all mounts) ────────────

def _local(fabric):
    """A seedless view of the HOME root: the queue and the candidates are this
    agent's own books; seed-mounted siblings' queues are theirs to drain."""
    return fabric.__class__(fabric.root, seeds=[],
                            agent_id=fabric.agent_id, kin_key=fabric.kin_key)


def all_atoms(fabric) -> List[Dict[str, Any]]:
    """Every atom record visible across ALL mounted fabrics (seed roots first,
    then local -- cross-game by design; game ids ride the records as data)."""
    return fabric.query("collective", ATOMS_TOPIC)


def pending(fabric) -> List[Dict[str, Any]]:
    """Unconsumed raw queue records, oldest first. Raw = no "kind" field;
    closed = a consumed marker or a not-found (the latter lives on the reopen path)."""
    rows = _local(fabric).query("collective", QUEUE_TOPIC)
    closed = {int(r.get("src_seq", -1)) for r in rows
              if r.get("kind") in ("consumed", "not_found")}
    raws = [r for r in rows if "kind" not in r]
    return sorted((r for r in raws if int(r.get("seq", 0)) not in closed),
                  key=lambda r: int(r.get("seq", 0)))


def open_not_found(fabric) -> List[Dict[str, Any]]:
    """The LATEST not-found per src_seq, minus items later closed by a candidate --
    the standing axis-tagged eliminations (defeasible, reversible, never load-bearing)."""
    rows = _local(fabric).query("collective", QUEUE_TOPIC)
    done = {int(r.get("src_seq", -1)) for r in rows if r.get("kind") == "consumed"}
    latest: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        if r.get("kind") == "not_found":
            latest[int(r.get("src_seq", -1))] = r
    return [latest[k] for k in sorted(latest) if k not in done]


def candidates(fabric, game, level) -> List[Dict[str, Any]]:
    """This agent's import_candidates for (game, level), insertion order."""
    g, lv = str(game), int(level)
    return _local(fabric).query(
        "collective", CAND_TOPIC,
        where=lambda r: r.get("game") == g and int(r.get("level", -1)) == lv)


# ── writers (single sites; the R3 gate reads the inventory off these) ─────────

def _persist(fabric, entry: Dict[str, Any]) -> Dict[str, Any]:
    """THE single write site for queue processing entries (sigma / consumed /
    not_found); the returned record's seq is the proof timestamp."""
    return fabric.append("collective", QUEUE_TOPIC, entry)


def _emit_candidate(fabric, cand: Dict[str, Any]) -> Dict[str, Any]:
    return fabric.append("collective", CAND_TOPIC, cand)


# ── lineage: the kin-echo law's predicate ─────────────────────────────────────

def _same_lineage(rec: Dict[str, Any], fabric) -> bool:
    """True iff the atom record's lineage (agent/by/kin fields, where present)
    equals the consuming fabric's -- the self-dealing case the ground audit flagged."""
    agent = rec.get("agent") or rec.get("by")
    if agent is not None and str(agent) == str(fabric.agent_id):
        return True
    kin = rec.get("kin")
    return kin is not None and str(kin) == str(fabric.kin_key)


def _close_hit(fabric, game, level, src_seq: int, sigma: Dict[str, Any],
               hits: List[Dict[str, Any]], near: List[Dict[str, Any]],
               priority_seq: int, axis: Optional[str] = None) -> None:
    """Rank hits (KIN-ECHO LAW: same-lineage last, then earliest mint), write the
    consumed marker (its seq IS the match seq), then the candidate; echo the origin
    author only across lineages."""
    ranked = sorted(hits, key=lambda r: (_same_lineage(r, fabric),
                                         int(r.get("seq", 0)), str(r.get("id"))))
    best = ranked[0]
    kin = _same_lineage(best, fabric)
    marker = _persist(fabric, {"kind": "consumed", "src_seq": int(src_seq),
                               "game": str(game), "level": int(level)})
    _emit_candidate(fabric, {
        "game": str(game), "level": int(level), "src_seq": int(src_seq),
        "atom": dict(best.get("atom") or {}),               # copied, never referenced
        "sigma": dict(sigma),
        "source_game": best.get("game"),
        "source_seq": int(best.get("seq", 0)),
        "source_id": best.get("id"),
        "three_conditions": {"priority_seq": int(priority_seq),
                             "atom_mint_seq": int(best.get("seq", 0)),
                             "match_seq": int(marker.get("seq", 0))},
        "near_misses": list(near),
        "kin_echo": bool(kin),
        "redescribed_axis": axis,
    })
    idea_id = best.get("idea_id")
    if idea_id and not kin:                                 # never pay self or kin
        try:
            fabric.echo(idea_id, by=fabric.agent_id)
        except Exception:
            pass


def _not_found(fabric, game, level, src_seq: int, sigma: Dict[str, Any],
               axis: str, priority_seq: int, near: List[Dict[str, Any]],
               atoms_seen: int) -> None:
    _persist(fabric, {"kind": "not_found", "src_seq": int(src_seq),
                      "sigma": dict(sigma), "axis": str(axis),
                      "atoms_seen": int(atoms_seen),
                      "priority_seq": int(priority_seq),
                      "near_misses": list(near),
                      "game": str(game), "level": int(level)})


def _retry_axis(near: List[Dict[str, Any]]) -> str:
    """The invariant to sharpen next: the most common near-miss failure
    (deterministic tie-break: alphabetical)."""
    tally: Dict[str, int] = {}
    for n in near:
        tally[n["failed"]] = tally.get(n["failed"], 0) + 1
    return sorted(tally, key=lambda k: (-tally[k], k))[0]


def _touches(axis: Optional[str], asig: Dict[str, Any]) -> bool:
    """Does a new atom's sigma touch a not-found's axis? A named invariant is
    touched by any atom carrying the field; the catch-all axes ("any" for a full
    description that matched nothing, "vocabulary" for a patch-less one) are
    touched by any sigma-carrying atom at all."""
    return axis in asig if axis in INVARIANTS else True


# ── the consumer ──────────────────────────────────────────────────────────────

def consume(fabric, game, level, budget_n) -> Dict[str, int]:
    """Drain up to `budget_n` import-queue items (reopened not-founds first --
    the Chaitin rule -- then pending raws, oldest first): describe -> persist
    sigma -> match across ALL mounted fabrics' atoms; hit -> import_candidates
    record with the three conditions; miss with near-misses -> ONE redescription
    retry on the named axis; give up -> axis-tagged defeasible not-found."""
    report = {"drained": 0, "candidates": 0, "not_found": 0,
              "reopened": 0, "retried": 0}
    budget = max(0, int(budget_n))
    used = 0
    atoms = all_atoms(fabric)

    for nf in open_not_found(fabric):                       # PHASE 1: the re-look trigger
        if used >= budget:
            break
        axis = nf.get("axis")
        seen = int(nf.get("atoms_seen", 0))
        fresh = [r for r in atoms[seen:]
                 if _atom_sigma(r) is not None and _touches(axis, _atom_sigma(r))]
        if not fresh:
            continue                                        # silence is never a verdict
        used += 1
        report["reopened"] += 1
        sigma = nf.get("sigma") or {}
        src_seq = int(nf.get("src_seq", 0))
        priority_seq = int(nf.get("priority_seq", nf.get("seq", 0)))
        hits, near = match(sigma, atoms)
        redesc = None
        if not hits and axis in INVARIANTS:
            report["retried"] += 1
            hits, _ = match(sigma, atoms, coarse_axes=(axis,))
            redesc = axis if hits else None
        if hits:
            _close_hit(fabric, game, level, src_seq, sigma, hits, near,
                       priority_seq, axis=redesc)
            report["candidates"] += 1
        else:
            _not_found(fabric, game, level, src_seq, sigma, axis,
                       priority_seq, near, len(atoms))
            report["not_found"] += 1

    for raw in pending(fabric):                             # PHASE 2: the fresh agenda
        if used >= budget:
            break
        used += 1
        report["drained"] += 1
        sigma = describe(raw)
        src_seq = int(raw.get("seq", 0))
        sig_rec = _persist(fabric, {"kind": "sigma", "src_seq": src_seq,
                                    "sigma": dict(sigma),
                                    "game": str(game), "level": int(level)})
        priority_seq = int(sig_rec.get("seq", 0))           # condition 1, on disk
        hits, near = match(sigma, atoms)
        axis: Optional[str] = None
        if not hits and near:
            axis = _retry_axis(near)
            report["retried"] += 1                          # exactly ONE retry
            hits, _ = match(sigma, atoms, coarse_axes=(axis,))
        if hits:
            _close_hit(fabric, game, level, src_seq, sigma, hits, near,
                       priority_seq, axis=axis)
            report["candidates"] += 1
        else:
            if axis is None:
                axis = ("any" if all(k in sigma for k in INVARIANTS)
                        else "vocabulary")
            _not_found(fabric, game, level, src_seq, sigma, axis,
                       priority_seq, near, len(atoms))
            report["not_found"] += 1
    return report


# ── the W1 interface (EXACT SIGNATURE -- the loop wave wires this call) ───────

def seed_imports(gamma, fabric, game, level) -> int:
    """Enter this agent's import_candidates for (game, level) into Gamma, each
    atom flagged imported=True. Planner verification is UNCHANGED -- the wheel
    rule outranks imports: an imported atom still earns its 2x TRANSFERRED before
    the planner trusts it. Idempotent per atom key; returns the count entered."""
    have = set()
    for rec in _local(gamma.fabric).query("collective", ATOMS_TOPIC):
        atom = rec.get("atom") or {}
        if atom.get("imported") and atom.get("key"):
            have.add(atom["key"])
    count = 0
    for cand in candidates(fabric, game, level):
        atom = dict(cand.get("atom") or {})
        key = atom.get("key")
        if not atom or (key and key in have):
            continue
        atom["imported"] = True
        try:
            gamma.add(atom, str(game), int(level))
        except Exception:
            continue                                        # a bad copy never crashes the loop
        if key:
            have.add(key)
        count += 1
    return count
