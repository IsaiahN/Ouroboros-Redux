"""consumer.py -- B12 THE TRIANGULATION CONSUMER (C33 §14-16; CK_LEDGER retrieval law).

SIGNATURE-FIRST RECOGNITION, never candidate-first verification: the residual's sigma
is computed INSIDE the home frame, candidate-blind (`describe`), PERSISTED to the queue
stream before any match attempt, and matched against the prediction-signatures atoms
carry from mint time (B13) -- a one-pass lookup over every mounted fabric's atoms,
no application loop. Game ids are runtime keys throughout; nothing here names a game.

FIG 9 (a residual is CHARACTERIZED, not named): live queue records are written with
`characterize` at the W4c-4 persist site -- sigma at ENQUEUE time plus bounded
bbox-cropped pre/post patches (PATCH_BOARD_FRACTION) -- and `describe` returns a
record's persisted sigma verbatim (no recompute; the persisted description is the
one whose seq proves priority). Sigma-less legacy records still recompute (compat).

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

THE FOURTH BRANCH (RUNG-4, instrument only): the outcome enum {consumed, not_found,
candidates} could not express DECLINE -- a drain where atoms were PRESENT but every
comparison was refused by a match guard fell through to not_found, making
"never-matched" the union of two states. Such an exit now persists an axis-tagged
kind="declined" record whose reason comes from the FIXED DECLINE_REASONS enum
(currently one member: DECLINED_IMPOVERISHED, match()'s base-rate description guard,
previously silent); not_found henceforth means STRICTLY never-matched -- an empty
search or a fully-evaluated miss. Declined items ride the Chaitin reopen path exactly
as their not_found ancestors did (pending/open_not_found read both kinds): observation
only, zero behavior change.

THE KIN-ECHO LAW (CK_LEDGER ground criterion, the consumer-prereg flag): echo pays the
origin author, and cross-mounted fabrics let an author's own offspring/kin echo its
atoms -- a reputation reading partly owned by its beneficiary. Rule, in full: any
echo/reputation bookkeeping this module writes EXCLUDES candidates whose source lineage
equals the consuming lineage (no echo is ever paid to self or kin), and same-lineage
hits are DOWN-WEIGHTED in ranking (a stranger's equal atom always outranks kin's).
Lineage is read from the atom record's "agent"/"by"/"kin" fields where present; the
candidate's `kin_echo` flag makes the down-weight auditable.

THE RANKED DRAIN (PREREG_DRAIN_ORIGIN.md §A; KNOBS G21): the PHASE-2 agenda is a
BOUNDED RANKED SELECTION, not FIFO. The queue-order defect (THE_LADDER, "CORRECTION
TO THE TALLY READING"): 388,184 records of which 82,301 carry a COMPLETE sigma, while
a ~370k PRE-CHARACTERIZATION backlog of {slot,residual,seq} records sat at the FRONT --
describe() can only recompute the frame-free subset of those, so they fail the
completeness guard BY CONSTRUCTION and the complete descriptions were ~46,000 episodes
away at budget_n=8. `_drain_order` ranks the NEWEST `DRAIN_WINDOW` pending records by
  (1) CHARACTERIZED FIRST (all INVARIANTS present in describe()'s sigma)
  (2) then LARGEST RESIDUAL (most unexplained first)
  (3) then RECENCY (newest first) as the tiebreak
and never sorts the whole queue -- the window IS the bound (Register G, GUESSED).
THE OFF-ARM (CLAIM.md's ablation constraint, shipped as a PASSING test): DRAIN_RANKED=0
in the environment, or DRAIN_RANKED=False on this module, returns `pending(fabric)`
VERBATIM -- oldest-first, byte-identical on disk (tests/gate/test_ranked_drain.py).

THE RHO RANKING (G-A, PREREG_FINAL_GAPS.md): mounted fabrics are correlated
witnesses. Below the kin-echo key, multi-source hits prefer the LOW-rho source
(lowest weighted-Jaccard correlation with the HOME fabric's own atoms --
independence is the gate, Fig 8's debit); the COLLAPSE-4 GUARD folds source
fabrics with rho >= rho_mod.RHO_COLLAPSE into one witness cluster whose
agreement counts ONCE (the candidate's "rho" block carries k / rho_bar / n_eff /
clusters / support), and each consume pass narrates one [RHO] line. Ranking and
bookkeeping only -- no behavior change outside consumer ranking.

THE MULTI-RUNG LADDER, LIVE (KNOBS Amendment 2 x THE_LADDER rung 0c): a consume
pass that matched anything PERSISTS the identity-ladder reading the hand-run
tools used to produce off-line -- one compact record per pass on the collective
"rho_readings" stream (additive, seq'd, game + PLAYING level per A3-2):
{source_game: {r0, r1, r2, traffic}} vs the HOME fabric's own books, computed by
rho_mod.rho_report (which drives rho_at at every rung plus the
rederivation-traffic channel, both directions), BOUNDED to the sources this
pass actually matched against (hits or near-misses; hard cap
RHO_READING_SOURCES) -- so the partition-artifact fix is a measurement THE
SYSTEM TAKES, not a report artifact. The [RHO] line narrates r0/r2/traffic
beside the rung-1 aggregate. The stream's named consumer is the diagnostic beat
protocol (THE_LADDER rung 4: "traffic collapsed + r0 nonzero, or climbing +
r0 flat?"); gate: tests/gate/test_rho_ladder_live.py.

THE IMPORT ADMISSION GATE (the extent premium at the DOOR; Seat 3, 2026-08-20):
the mint prices every LOCALLY minted atom's context extent (mint.EXTENT_RATE --
PREREG_W2_STAGE2_CONTEXT_MIN.md, PI_REPLAY_RESULT.md's 976-cell medians), but an
atom arriving over the network entered local Gamma WITHOUT meeting the bargain --
a door with a wall beside it. seed_imports now prices ADMISSION with the mint's
own inequality, constants IMPORTED from mint (never duplicated):
    cost = effects.encoding_cost_atom + mint.EXTENT_RATE * retained_unchanged
    admit iff cost < R and cost < mint.MDL_MARGIN * R,
    R = mint.RESIDUAL_CELL_COST * changed + mint.UNEXPLAINED_PREMIUM.
An atom failing the bargain is NOT admitted; the refusal is an "import_reject"
record on the import_queue stream (the stream that already logs import outcomes),
price and bar recorded -- no silent drop, count(refusals) == count(records). A
ctx_min-minimised atom is priced on its RETAINED cells only (context_full NEVER
counts against it): arriving tight is how an old atom re-qualifies. At
EXTENT_RATE = 0 admission is byte-identical to the pre-gate code (the F3 dial).
Scope: ONE inequality, ONE refusal path, ONE record -- the independence debit,
provenance tags and all other import semantics are untouched.
Gate: tests/gate/test_import_gate.py.

Deterministic, stdlib + numpy only; failures degrade, never raise (house containment).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from engines.egocentric import applicability as applicability_mod
from engines.egocentric import effects as effects_mod
from engines.egocentric import rho as rho_mod

__all__ = ["sigma_of", "describe", "characterize", "match", "consume",
           "seed_imports", "pending", "open_not_found", "candidates",
           "INVARIANTS", "PATCH_BOARD_FRACTION",
           "KIND_DECLINED", "DECLINED_IMPOVERISHED", "DECLINE_REASONS",
           "DRAIN_RANKED", "DRAIN_WINDOW",
           "admission_price", "KIND_IMPORT_REJECT"]

QUEUE_TOPIC = "import_queue"
CAND_TOPIC = "import_candidates"
ATOMS_TOPIC = "atoms"
RHO_TOPIC = "rho_readings"          # the ladder's live measurement (Amendment 2)
VERDICTS_TOPIC = "mint_verdicts"    # the rederivation-traffic channel's source

# The per-pass reading is BOUNDED: only sources with hits or near-misses this
# pass are read, and never more than this many (sorted, deterministic).
RHO_READING_SOURCES = 8

# Fig 9 (the characterization law): evidence patches persist only for POCKET-sized
# changed regions -- bbox area <= this fraction of the board. Stricter than the
# mint's MAX_BBOX_BOARD_FRACTION (0.5), so a patch-carrying record has already
# passed the mint's bbox pocket test by construction. Sigma is kept ALWAYS.
PATCH_BOARD_FRACTION = 0.25

# The match invariants (C33 §16): both sides must carry ALL of them for a verdict;
# "slot" and "mag" are frame-local descriptors, never compared across frames.
INVARIANTS = ("arity", "bbox", "changed", "colour_delta", "conserved")

# THE FOURTH BRANCH (RUNG-4): the decline vocabulary -- a FIXED enum. A match
# guard that refuses a comparison while atoms are present must name its reason
# here and route to _declined, never fall through to _not_found (not_found
# means STRICTLY never-matched: an empty search or a fully-evaluated miss).
KIND_DECLINED = "declined"
DECLINED_IMPOVERISHED = "impoverished"  # match()'s base-rate guard: an INVARIANT missing on either side
DECLINE_REASONS = (DECLINED_IMPOVERISHED,)

# THE IMPORT ADMISSION GATE's refusal record kind (see admission_price /
# seed_imports below): NOT a member of DECLINE_REASONS -- a refused admission
# is a priced verdict on the import_queue outcome stream, never a swallow code.
KIND_IMPORT_REJECT = "import_reject"

# THE RANKED DRAIN (KNOBS G21, Register G, provenance GUESSED). DRAIN_RANKED is
# the MODULE FLAG; the environment variable of the same name OUTRANKS it when
# set, so the off-arm can be run without editing code. DRAIN_WINDOW bounds the
# ranking: only the NEWEST this-many pending records are scanned and sorted per
# pass -- a whole-queue sort over ~370k records is exactly what this refuses,
# and the newest end is where the characterized records live (a front-anchored
# window would rank the pre-characterization backlog against itself forever).
DRAIN_RANKED = True
DRAIN_WINDOW = 512
_OFF_WORDS = ("0", "false", "no", "off", "")


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
    """Candidate-blind sigma for one import-queue record. A record carrying a
    PERSISTED sigma (the Fig-9 characterization written at enqueue time) is
    returned verbatim -- no recompute: the enqueue-time description is the one
    whose seq precedes the match (the priority condition). Otherwise the sigma
    is computed from the record's before/after frames where present (legacy
    synthetic shape), degrading to slot + magnitude class without them."""
    rec = residual_record or {}
    sig = rec.get("sigma")
    if isinstance(sig, dict):
        return dict(sig)
    residual = rec.get("residual")
    try:
        residual = None if residual is None else float(residual)
    except Exception:
        residual = None
    return sigma_of(rec.get("before"), rec.get("after"),
                    slot=rec.get("slot"), residual=residual)


def characterize(before, after, slot=None, residual=None) -> Dict[str, Any]:
    """Fig 9: the enqueue-time CHARACTERIZATION of one residual -- the fields
    the W4c-4 persist site adds to a live import_queue record when before/after
    evidence is in hand. Always {"sigma": sigma_of(before, after, ...)} (the
    description step, the priority condition); plus compact bbox-cropped
    {"pre", "post"} patches and the absolute {"bbox": [r0, c0, r1, c1]} when
    the changed region is a pocket (bbox area <= PATCH_BOARD_FRACTION * board
    -- oversized regions keep sigma, skip patches). Pure, JSON-native,
    degrades to sigma-only, never raises (house containment)."""
    out: Dict[str, Any] = {"sigma": sigma_of(before, after, slot=slot,
                                             residual=residual)}
    try:
        b = np.asarray(before)
        a = np.asarray(after)
        if b.ndim == 2 and b.shape == a.shape and b.size:
            diff = b != a
            if bool(diff.any()):
                rows = np.flatnonzero(diff.any(axis=1))
                cols = np.flatnonzero(diff.any(axis=0))
                r0, r1 = int(rows[0]), int(rows[-1])
                c0, c1 = int(cols[0]), int(cols[-1])
                if (r1 - r0 + 1) * (c1 - c0 + 1) <= PATCH_BOARD_FRACTION * b.size:
                    out["bbox"] = [r0, c0, r1, c1]
                    out["pre"] = [[int(v) for v in row]
                                  for row in b[r0:r1 + 1, c0:c1 + 1]]
                    out["post"] = [[int(v) for v in row]
                                   for row in a[r0:r1 + 1, c0:c1 + 1]]
    except Exception:
        pass                    # malformed evidence degrades to sigma-only
    return out


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
          coarse_axes: Sequence[str] = (),
          stats: Optional[Dict[str, int]] = None) -> Tuple[List[Dict[str, Any]],
                                                           List[Dict[str, Any]]]:
    """(hits, near_misses) over atom RECORDS: a hit matches every invariant; a
    near-miss matches all but exactly ONE, and names the failing invariant.
    Signature-first: nothing is applied, one pass, no candidate frames touched.

    THE FOURTH BRANCH's tally (instrument only, matching unchanged): when
    `stats` is a dict it is filled ADDITIVELY with the walk's exits --
    "evaluated" (full comparisons), "declined" (the impoverished-description
    guard refused: an INVARIANT missing on either side -- previously a silent
    skip), "unsigmad" (no signature at all: nothing was offered)."""
    hits: List[Dict[str, Any]] = []
    near: List[Dict[str, Any]] = []
    tally = {"evaluated": 0, "declined": 0, "unsigmad": 0}
    for rec in atoms:
        asig = _atom_sigma(rec)
        if asig is None:
            tally["unsigmad"] += 1
            continue                    # an unsigma'd atom cannot be recognized (backfill)
        if any(k not in sigma or k not in asig for k in INVARIANTS):
            tally["declined"] += 1
            continue                    # impoverished description: base-rate, no verdict
        tally["evaluated"] += 1
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
    if isinstance(stats, dict):
        for k, v in tally.items():
            stats[k] = int(stats.get(k, 0)) + v
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
    closed = a consumed marker, a not-found, or a declined (the latter two
    live on the reopen path)."""
    rows = _local(fabric).query("collective", QUEUE_TOPIC)
    closed = {int(r.get("src_seq", -1)) for r in rows
              if r.get("kind") in ("consumed", "not_found", KIND_DECLINED)}
    raws = [r for r in rows if "kind" not in r]
    return sorted((r for r in raws if int(r.get("seq", 0)) not in closed),
                  key=lambda r: int(r.get("seq", 0)))


def _ranked_enabled() -> bool:
    """The toggle, read at every pass: the DRAIN_RANKED environment variable
    when set (0/false/no/off/empty => the off-arm), else the module flag."""
    raw = os.environ.get("DRAIN_RANKED")
    if raw is None:
        return bool(DRAIN_RANKED)
    return str(raw).strip().lower() not in _OFF_WORDS


def _characterized(rec: Dict[str, Any]) -> bool:
    """Rank key (1): does this record carry a COMPLETE sigma -- every INVARIANT
    the completeness guard demands? Read through describe(), so the predicate is
    the sigma the matcher will actually see (persisted verbatim where present,
    recomputed from frames otherwise, frame-free legacy records degrading)."""
    try:
        sig = describe(rec)
    except Exception:
        return False
    return all(k in sig for k in INVARIANTS)


def _residual_of(rec: Dict[str, Any]) -> float:
    """Rank key (2): the unexplained magnitude; unreadable => 0.0 (last)."""
    try:
        return float(rec.get("residual") or 0.0)
    except Exception:
        return 0.0


def _rank_key(rec: Dict[str, Any]) -> Tuple[int, float, int]:
    return (0 if _characterized(rec) else 1,     # (1) CHARACTERIZED FIRST
            -_residual_of(rec),                  # (2) LARGEST RESIDUAL
            -int(rec.get("seq", 0)))             # (3) RECENCY (newest first)


def _drain_order(fabric) -> List[Dict[str, Any]]:
    """THE PHASE-2 AGENDA (PREREG_DRAIN_ORIGIN.md §A). Ranked arm: the NEWEST
    DRAIN_WINDOW pending records, sorted by (characterized, -residual, -seq) --
    bounded by construction, never a whole-queue sort, so a characterized record
    older than the window is NOT promoted (that is the bound's falsifier).
    OFF-ARM (DRAIN_RANKED=0): `pending(fabric)` VERBATIM -- the same list object
    the pre-ranking code iterated, oldest-first, byte-identical on disk."""
    raws = pending(fabric)
    if not _ranked_enabled():
        return raws
    window = raws[-DRAIN_WINDOW:] if DRAIN_WINDOW > 0 else raws
    return sorted(window, key=_rank_key)


def open_not_found(fabric) -> List[Dict[str, Any]]:
    """The LATEST give-up (not-found OR declined) per src_seq, minus items later
    closed by a candidate -- the standing axis-tagged eliminations (defeasible,
    reversible, never load-bearing). Declined records ride the same reopen path:
    their shape is a not_found superset (kind/reason added, additively)."""
    rows = _local(fabric).query("collective", QUEUE_TOPIC)
    done = {int(r.get("src_seq", -1)) for r in rows if r.get("kind") == "consumed"}
    latest: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        if r.get("kind") in ("not_found", KIND_DECLINED):
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
    not_found / declined / import_reject); the returned record's seq is the
    proof timestamp."""
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


def _rho_context(fabric, atoms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-pass rho bookkeeping (G-A): atoms grouped by source game, each group's
    rho against the HOME fabric's OWN atoms (the independence debit the ranking
    reads), and the pairwise rho matrix the collapse-4 guard reads. Computed once
    per consume pass; degrades to an empty context, never raises."""
    ctx: Dict[str, Any] = {"src_rho": {}, "pairs": {}, "k": 0, "rho_bar": 0.0,
                           "n_eff": 0.0, "collapsed_pairs": 0}
    try:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in atoms:
            groups.setdefault(str(r.get("game")), []).append(r)
        home = _local(fabric).query("collective", ATOMS_TOPIC)
        ctx["src_rho"] = {g: rho_mod.rho(rows, home) for g, rows in groups.items()}
        names = sorted(groups)
        for i, ga in enumerate(names):
            for gb in names[i + 1:]:
                ctx["pairs"][(ga, gb)] = rho_mod.rho(groups[ga], groups[gb])
        pairs = ctx["pairs"]
        ctx["k"] = len(names)
        ctx["rho_bar"] = (sum(pairs.values()) / len(pairs)) if pairs else 0.0
        ctx["n_eff"] = rho_mod.n_eff(ctx["k"], ctx["rho_bar"])
        ctx["collapsed_pairs"] = sum(1 for v in pairs.values()
                                     if v >= rho_mod.RHO_COLLAPSE)
    except Exception:
        pass
    return ctx


def _pair_rho(ctx: Dict[str, Any]):
    pairs = ctx.get("pairs") or {}

    def pr(a: str, b: str) -> float:
        return float(pairs.get((a, b), pairs.get((b, a), 0.0)))
    return pr


def _rho_block(hits: List[Dict[str, Any]], best: Dict[str, Any],
               ctx: Dict[str, Any]) -> Dict[str, Any]:
    """The candidate's G-A support block: k distinct source fabrics agreed with
    mean pairwise correlation rho_bar -> n_eff effective witnesses; the
    COLLAPSE-4 GUARD then folds rho >= RHO_COLLAPSE sources into clusters so a
    replicated fabric's agreement counts ONCE (support = n_eff over clusters)."""
    pr = _pair_rho(ctx)
    sources = sorted({str(r.get("game")) for r in hits})
    k = len(sources)
    vals = [pr(a, b) for i, a in enumerate(sources) for b in sources[i + 1:]]
    rho_bar = sum(vals) / len(vals) if vals else 0.0
    clusters = rho_mod.collapse(sources, pr)
    reps = sorted(c[0] for c in clusters)
    cvals = [pr(a, b) for i, a in enumerate(reps) for b in reps[i + 1:]]
    crho = sum(cvals) / len(cvals) if cvals else 0.0
    src_rho = ctx.get("src_rho") or {}
    return {"source_rho": round(float(src_rho.get(str(best.get("game")), 0.0)), 4),
            "sources": sources, "k": k, "rho_bar": round(rho_bar, 4),
            "n_eff": round(rho_mod.n_eff(k, rho_bar), 4),
            "clusters": len(clusters),
            "support": round(rho_mod.n_eff(len(clusters), crho), 4),
            "collapsed": len(clusters) < k}


def _note_sources(touched: set, hits: List[Dict[str, Any]],
                  near: List[Dict[str, Any]]) -> None:
    """Record which source fabrics this item ACTUALLY matched against (hits or
    near-misses) -- the bound on the per-pass rho reading."""
    for r in hits:
        g = r.get("game")
        if g is not None:
            touched.add(str(g))
    for n in near:
        g = n.get("source_game")
        if g is not None:
            touched.add(str(g))


def _persist_rho_readings(fabric, game, level, touched: set,
                          atoms: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """THE LADDER'S LIVE MEASUREMENT (Amendment 2 x rung 0c): one compact
    multi-rung reading per consume pass, appended to the collective
    "rho_readings" stream -- {source_game: {r0, r1, r2, traffic}} vs the HOME
    fabric's own books, via rho_mod.rho_report (rho_at at rungs 0/1/2 plus the
    rederivation-traffic channel, counted BOTH directions: home's verdict
    stream vs the source's atom keys, and the source game's seed-mounted
    verdicts vs home's). Bounded to `touched` (sources with hits or
    near-misses this pass, capped at RHO_READING_SOURCES); a pass that matched
    nothing persists NOTHING (the stream grows with matches, not with passes).
    Returns the appended record, or None; degrades, never raises."""
    srcs = sorted(str(g) for g in touched)[:RHO_READING_SOURCES]
    if not srcs:
        return None
    try:
        home_atoms = _local(fabric).query("collective", ATOMS_TOPIC)
        home_verds = _local(fabric).query("collective", VERDICTS_TOPIC)
        all_verds = fabric.query("collective", VERDICTS_TOPIC)
        # seed mounts are queried FIRST, local LAST (fabric.query's documented
        # order): the seed-side verdicts are the prefix.
        seed_verds = (all_verds[:len(all_verds) - len(home_verds)]
                      if home_verds else all_verds)
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in atoms:
            groups.setdefault(str(r.get("game")), []).append(r)
        vgroups: Dict[str, List[Dict[str, Any]]] = {}
        for v in seed_verds:
            if isinstance(v, dict):
                vgroups.setdefault(str(v.get("game")), []).append(v)
        readings: Dict[str, Dict[str, Any]] = {}
        for g in srcs:
            rep = rho_mod.rho_report({
                "home": {"atoms": home_atoms, "verdicts": home_verds},
                "src": {"atoms": groups.get(g) or [],
                        "verdicts": vgroups.get(g) or []},
            }).get(("home", "src"))
            if not rep:
                continue
            readings[g] = {"r0": round(float(rep.get("r0", 0.0)), 4),
                           "r1": round(float(rep.get("r1", 0.0)), 4),
                           "r2": round(float(rep.get("r2", 0.0)), 4),
                           "traffic": int(rep.get("traffic", 0))}
        if not readings:
            return None
        return fabric.append("collective", RHO_TOPIC, {
            "game": str(game), "level": int(level),      # A3-2: PLAYING level
            "readings": readings,
            "home_atoms": len(home_atoms), "atoms_seen": len(atoms)})
    except Exception:
        return None                     # a failed reading degrades, never raises


def _close_hit(fabric, game, level, src_seq: int, sigma: Dict[str, Any],
               hits: List[Dict[str, Any]], near: List[Dict[str, Any]],
               priority_seq: int, axis: Optional[str] = None,
               rho_ctx: Optional[Dict[str, Any]] = None) -> None:
    """Rank hits (KIN-ECHO LAW first: same-lineage last; then the G-A rho key:
    LOW correlation with home preferred -- independence is the gate; then
    earliest mint), write the consumed marker (its seq IS the match seq), then
    the candidate; echo the origin author only across lineages."""
    ctx = rho_ctx if isinstance(rho_ctx, dict) else {}
    src_rho = ctx.get("src_rho") or {}
    ranked = sorted(hits, key=lambda r: (_same_lineage(r, fabric),
                                         float(src_rho.get(str(r.get("game")), 0.0)),
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
        "rho": _rho_block(hits, best, ctx),
    })
    idea_id = best.get("idea_id")
    if idea_id and not kin:                                 # never pay self or kin
        try:
            fabric.echo(idea_id, by=fabric.agent_id)
        except Exception:
            pass


def _counts(entry: Dict[str, Any], stats: Optional[Dict[str, int]]) -> Dict[str, Any]:
    """Additive audit counts from a match() stats tally (records additive)."""
    if isinstance(stats, dict):
        entry["evaluated_atoms"] = int(stats.get("evaluated", 0))
        entry["declined_atoms"] = int(stats.get("declined", 0))
        entry["unsigmad_atoms"] = int(stats.get("unsigmad", 0))
    return entry


def _not_found(fabric, game, level, src_seq: int, sigma: Dict[str, Any],
               axis: str, priority_seq: int, near: List[Dict[str, Any]],
               atoms_seen: int, stats: Optional[Dict[str, int]] = None) -> None:
    """STRICTLY never-matched: an empty search (no sigma-carrying atoms -- the
    Chaitin case) or a fully-evaluated miss. A refused comparison with atoms
    present is NOT this -- that routes to _declined (the fourth branch)."""
    _persist(fabric, _counts({"kind": "not_found", "src_seq": int(src_seq),
                              "sigma": dict(sigma), "axis": str(axis),
                              "atoms_seen": int(atoms_seen),
                              "priority_seq": int(priority_seq),
                              "near_misses": list(near),
                              "game": str(game), "level": int(level)}, stats))


def _declined(fabric, game, level, src_seq: int, sigma: Dict[str, Any],
              axis: str, priority_seq: int, near: List[Dict[str, Any]],
              atoms_seen: int, reason: str,
              stats: Optional[Dict[str, int]] = None) -> None:
    """THE FOURTH BRANCH's single write site: atoms were PRESENT and a match
    guard refused every comparison -- no verdict was ever reached. `reason`
    comes from the FIXED DECLINE_REASONS enum. The record is an additive
    not_found superset (kind/reason/counts added), so the Chaitin reopen
    machinery reads it unchanged."""
    _persist(fabric, _counts({"kind": KIND_DECLINED, "reason": str(reason),
                              "src_seq": int(src_seq),
                              "sigma": dict(sigma), "axis": str(axis),
                              "atoms_seen": int(atoms_seen),
                              "priority_seq": int(priority_seq),
                              "near_misses": list(near),
                              "game": str(game), "level": int(level)}, stats))


def _is_decline(stats: Dict[str, int]) -> bool:
    """The routing law: DECLINED iff comparisons were refused and NONE was ever
    fully evaluated (atoms present, verdict withheld on every one). An empty
    search -- no atoms, or none carrying sigma -- is not_found (silence is
    never a decline verdict); any fully-evaluated miss is not_found too."""
    return int(stats.get("evaluated", 0)) == 0 and int(stats.get("declined", 0)) > 0


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
    the Chaitin rule -- then pending raws in `_drain_order`: RANKED
    characterized-first / largest-residual / newest over a bounded window, or
    oldest-first verbatim under the DRAIN_RANKED off-arm): describe -> persist
    sigma -> match across ALL mounted fabrics' atoms; hit -> import_candidates
    record with the three conditions; miss with near-misses -> ONE redescription
    retry on the named axis; give up -> axis-tagged defeasible not-found, UNLESS
    atoms were present and every comparison was refused by a match guard --
    that give-up is the FOURTH BRANCH, an axis-tagged kind="declined" record
    with its reason from DECLINE_REASONS (same reopen path, observation only)."""
    report = {"drained": 0, "candidates": 0, "not_found": 0, "declined": 0,
              "reopened": 0, "retried": 0}
    budget = max(0, int(budget_n))
    used = 0
    atoms = all_atoms(fabric)
    rho_ctx = _rho_context(fabric, atoms)                   # G-A: once per pass
    touched: set = set()                # sources matched this pass (the bound)

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
        stats: Dict[str, int] = {}
        hits, near = match(sigma, atoms, stats=stats)
        redesc = None
        if not hits and axis in INVARIANTS:
            report["retried"] += 1
            hits, _ = match(sigma, atoms, coarse_axes=(axis,))
            redesc = axis if hits else None
        _note_sources(touched, hits, near)                  # the reading's bound
        if hits:
            _close_hit(fabric, game, level, src_seq, sigma, hits, near,
                       priority_seq, axis=redesc, rho_ctx=rho_ctx)
            report["candidates"] += 1
        elif _is_decline(stats):                        # the FOURTH BRANCH
            _declined(fabric, game, level, src_seq, sigma, axis,
                      priority_seq, near, len(atoms),
                      DECLINED_IMPOVERISHED, stats)
            report["declined"] += 1
        else:
            _not_found(fabric, game, level, src_seq, sigma, axis,
                       priority_seq, near, len(atoms), stats)
            report["not_found"] += 1

    for raw in _drain_order(fabric):                        # PHASE 2: the fresh agenda
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
        stats = {}
        hits, near = match(sigma, atoms, stats=stats)
        axis: Optional[str] = None
        if not hits and near:
            axis = _retry_axis(near)
            report["retried"] += 1                          # exactly ONE retry
            hits, _ = match(sigma, atoms, coarse_axes=(axis,))
        _note_sources(touched, hits, near)                  # the reading's bound
        if hits:
            _close_hit(fabric, game, level, src_seq, sigma, hits, near,
                       priority_seq, axis=axis, rho_ctx=rho_ctx)
            report["candidates"] += 1
        else:
            if axis is None:
                axis = ("any" if all(k in sigma for k in INVARIANTS)
                        else "vocabulary")
            if _is_decline(stats):                          # the FOURTH BRANCH
                _declined(fabric, game, level, src_seq, sigma, axis,
                          priority_seq, near, len(atoms),
                          DECLINED_IMPOVERISHED, stats)
                report["declined"] += 1
            else:
                _not_found(fabric, game, level, src_seq, sigma, axis,
                           priority_seq, near, len(atoms), stats)
                report["not_found"] += 1
    # Amendment 2 x rung 0c: the pass PERSISTS its multi-rung reading (bounded
    # to matched sources; a matchless pass persists nothing), then narrates.
    reading = _persist_rho_readings(fabric, game, level, touched, atoms)
    try:                                                    # G-A: one [RHO] line per pass
        rungs = (reading or {}).get("readings") or {}
        r0 = max((float(v.get("r0", 0.0)) for v in rungs.values()), default=0.0)
        r2 = max((float(v.get("r2", 0.0)) for v in rungs.values()), default=0.0)
        traffic = sum(int(v.get("traffic", 0)) for v in rungs.values())
        print("[RHO] sources=%d rho_bar=%.3f n_eff=%.2f collapsed_pairs=%d "
              "candidates=%d r0=%.3f r2=%.3f traffic=%d"
              % (rho_ctx.get("k", 0), rho_ctx.get("rho_bar", 0.0),
                 rho_ctx.get("n_eff", 0.0), rho_ctx.get("collapsed_pairs", 0),
                 report["candidates"], r0, r2, traffic))
    except Exception:
        pass
    return report


# ── THE IMPORT ADMISSION GATE: the extent premium at the door ─────────────────

def admission_price(atom: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Price one arriving atom's ADMISSION with the mint's own bargain
    (module docstring, THE IMPORT ADMISSION GATE). The constants and both
    pricing helpers are the MINT'S -- imported, never duplicated -- so the
    door and the mint can never quote different prices for the same extent:

        cost = effects.encoding_cost_atom(atom)            # 1.0 + changed
               + mint.EXTENT_RATE * effects.context_retained_cells(atom)
        R    = mint.RESIDUAL_CELL_COST * changed + mint.UNEXPLAINED_PREMIUM
        admit iff cost < R and cost < mint.MDL_MARGIN * R

    `changed` is derived from the atom's OWN patches (context vs transform
    .after) -- on a ctx_min-minimised atom DONT_CARE lands in both together,
    so the changed count is exactly the minted one, and retained counts ONLY
    the cells the context still insists on (context_full never enters the
    price: arriving tight is how an old atom re-qualifies). Returns
    {admit, cost, bar, changed, retained, rate}, or None when the atom
    carries NO priceable extent (no 2-D context/after pair, or no changed
    cell) -- such an atom passes the door exactly as it always did: this
    gate prices extent, and where none is measurable there is nothing to
    price. Lazy mint import (mint imports this module); at EXTENT_RATE = 0
    every priceable atom admits, byte-identical to the pre-gate door.
    COMPOSER STAGE 1 (PROPOSAL_COMPOSER_DESIGN.md §6.1) -- THE UNPRICED-
    COMPOSITE HOLE CLOSES: a COMPOSITE atom carries no context/after pair, so
    it always passed this door unpriced (the hole its builder stated). A
    composite carrying the compose-time DERIVED price (applicability.csig_of:
    price = start_extent + Σ unguaranteed_residue + length, ONE derivation
    with the index's precondition) is now priced with the SAME mint
    inequality -- the derived price standing where the atom's retained
    extent stands, the summed leaf `changed` standing where the atom's
    stands:

        cost = effects.encoding_cost_atom(changed=Σ leaf changed)
               + mint.EXTENT_RATE * derived_price
        admit iff cost < R and cost < mint.MDL_MARGIN * R.

    The returned dict's "retained" carries the derived price, so the
    seed_imports refusal record states it verbatim. An OLD or UNDERIVABLE
    composite (csig_of None) still returns None -- the hole persists exactly
    where nothing derivable exists to price, stated not silent. At
    EXTENT_RATE = 0 every derivable composite admits: byte-identical
    outcomes to the pre-build door (the dial).

    Pure, deterministic, degrades to None, never raises."""
    try:
        from engines.egocentric import mint as mint_mod  # lazy: no import cycle
        if (atom or {}).get("kind") == "COMPOSITE":
            csig = applicability_mod.csig_of(atom)
            if csig is None or int(csig["changed"]) <= 0:
                return None             # underivable: passes the door as it always did
            changed = int(csig["changed"])
            price = int(csig["price"])
            cost = (effects_mod.encoding_cost_atom({"kind": "COMPOSITE",
                                                    "changed": changed})
                    + mint_mod.EXTENT_RATE * float(price))
            r_cost = (mint_mod.RESIDUAL_CELL_COST * float(changed)
                      + mint_mod.UNEXPLAINED_PREMIUM)
            bar = mint_mod.MDL_MARGIN * r_cost
            return {"admit": bool(cost < r_cost and cost < bar),
                    "cost": float(cost), "bar": float(bar),
                    "changed": int(changed), "retained": int(price),
                    "rate": float(mint_mod.EXTENT_RATE)}
        ctx = np.asarray((atom or {}).get("context"))
        out = np.asarray(((atom or {}).get("transform") or {}).get("after"))
        if ctx.ndim != 2 or ctx.size == 0 or ctx.shape != out.shape:
            return None                     # no priceable extent: not this gate's atom
        changed = int((ctx != out).sum())
        if changed == 0:
            return None                     # no residual priced: the mint never emits these
        retained = effects_mod.context_retained_cells(atom)
        cost = (effects_mod.encoding_cost_atom(atom)
                + mint_mod.EXTENT_RATE * float(retained))
        r_cost = (mint_mod.RESIDUAL_CELL_COST * float(changed)
                  + mint_mod.UNEXPLAINED_PREMIUM)
        bar = mint_mod.MDL_MARGIN * r_cost
        return {"admit": bool(cost < r_cost and cost < bar),
                "cost": float(cost), "bar": float(bar),
                "changed": int(changed), "retained": int(retained),
                "rate": float(mint_mod.EXTENT_RATE)}
    except Exception:
        return None                         # a malformed copy degrades, never raises


# ── the W1 interface (EXACT SIGNATURE -- the loop wave wires this call) ───────

def seed_imports(gamma, fabric, game, level) -> int:
    """Enter this agent's import_candidates for (game, level) into Gamma, each
    atom flagged imported=True. Planner verification is UNCHANGED -- the wheel
    rule outranks imports: an imported atom still earns its 2x TRANSFERRED before
    the planner trusts it. Idempotent per atom key; returns the count entered.

    RECORD-KEEPING (VICTORY_PROTOCOL): the seeded atom RETAINS its provenance --
    the candidate's source_game is written into the atom (ADDITIVE: only when
    the atom does not already carry one), so the 25/25 census can name every
    atom's native + imported source.

    THE ORIGIN MARKER (PREREG_DRAIN_ORIGIN.md §B): this is the IMPORTED write
    site. Every seeded record is stamped origin="imported" + source_game (+ the
    source atom's seq) AT WRITE TIME by Gamma.add -- provenance recorded
    positively, never by the absence of fields. The already-have scan reads that
    marker through effects.origin_of BESIDE the legacy atom["imported"] flag, so
    old books keep deduping and an UNKNOWN-origin record is never mistaken for
    a local one (absence is not a claim).

    THE IMPORT ADMISSION GATE (module docstring): before the Gamma write --
    THE admission point -- every candidate atom is priced by admission_price
    with the mint's own inequality. A failing atom is NOT admitted; its
    refusal is a kind="import_reject" record via _persist on the import_queue
    stream (the stream that already logs this queue item's outcomes), carrying
    the price and the bar -- never a silent drop. Refusals are idempotent per
    CANDIDATE RECORD (cand_seq), never per atom key: a minimised re-arrival
    is a NEW candidate record and is re-priced -- arriving tight is how an
    old atom re-qualifies. Everything else here is unchanged."""
    have = set()
    for rec in _local(gamma.fabric).query("collective", ATOMS_TOPIC):
        atom = rec.get("atom") or {}
        key = atom.get("key")
        if not key:
            continue
        if (atom.get("imported")                        # legacy shape (old books)
                or effects_mod.origin_of(rec) == effects_mod.ORIGIN_IMPORTED):
            have.add(key)
    # Already-refused scan (the gate's `have` twin): one import_reject per
    # candidate record, ever -- re-runs neither re-price nor re-append.
    refused = {int(r.get("cand_seq", -1))
               for r in _local(fabric).query("collective", QUEUE_TOPIC)
               if r.get("kind") == KIND_IMPORT_REJECT}
    count = 0
    for cand in candidates(fabric, game, level):
        atom = dict(cand.get("atom") or {})
        key = atom.get("key")
        if not atom or (key and key in have):
            continue
        cand_seq = int(cand.get("seq", -1))
        if cand_seq in refused:
            continue                    # refusal already on record, not silence
        price = admission_price(atom)
        if price is not None and not price["admit"]:
            # THE REFUSAL PATH: the bargain was not met -- record it, loudly.
            _persist(fabric, {
                "kind": KIND_IMPORT_REJECT,
                "src_seq": int(cand.get("src_seq", -1)),
                "cand_seq": cand_seq, "key": key,
                "source_game": cand.get("source_game"),
                "cost": price["cost"], "bar": price["bar"],
                "changed": price["changed"], "retained": price["retained"],
                "rate": price["rate"],
                "game": str(game), "level": int(level)})
            refused.add(cand_seq)
            continue
        atom["imported"] = True
        src_game = cand.get("source_game")
        if src_game is not None and "source_game" not in atom:
            atom["source_game"] = src_game          # provenance retained, additively
        try:
            gamma.add(atom, str(game), int(level),
                      origin=effects_mod.ORIGIN_IMPORTED,
                      source_game=src_game, source_seq=cand.get("source_seq"))
        except Exception:
            continue                                        # a bad copy never crashes the loop
        if key:
            have.add(key)
        count += 1
    return count
