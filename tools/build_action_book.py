"""build_action_book.py -- STAGE 0 of the reasoning gate (PROPOSAL_REASONING_GATE.md
§3): THE ACTION BOOK, the builder.

A TOOL, operator-invoked. Per game box it derives, from two recorded sources
ONLY, everything the agent's own history supports about each action int:

  (a) the Γ atoms stream (ego_fabric/collective/atoms.jsonl) -- each atom
      carries its action int, its patches, sigma.colour_delta, ttype ->
      observed effect distribution: changed-cell counts, dominant ttypes,
      colour deltas, and direction stats where derivable (TRANSLATE dx/dy);
  (b) the action_traces DB (core_data.db, READ-ONLY) -- frame_before/
      frame_after/action_number/score_change plus the budget columns
      (budget_total/budget_spend, produced-and-unread before this build) ->
      per-action frequency, frame-change rate, score-change distribution, and
      COST evidence where the budget columns are non-null.

INVERSE PAIRINGS, evidence-counted, never a bare boolean:
  * from traces: consecutive steps f0 -a-> f1 -b-> f2 inside one session where
    f2 == f0 AND f1 != f0 (b restored a change a actually made; two no-ops
    prove nothing) AND the steps chain (frame_before of the b-step equals
    frame_after of the a-step -- replay seams and resets never fake a pair).
    A row whose frame text fails json.loads (the pre-fix writer stored lossy,
    ellipsis-truncated numpy reprs) is SKIPPED for pair detection -- it can
    neither open nor close a pair -- and counted in the header as
    `skipped_unparseable`; truncated text is never hashed verbatim as equal;
  * from atoms: ordered pairs of TYPED atoms whose deltas compose to identity,
    checked through effects.invert_transform -- the world's own inverse
    algebra, authored nowhere here.

THE CLEAN-WINDOW FILTER (--since "YYYY-MM-DD HH:MM:SS", UTC): restricts the
TRACE side ONLY -- per-action frequency, frame-change rate, score
distribution, cost evidence and every trace-derived inverse pair -- to rows
with action_traces.created_at >= the given text (SQLite's CURRENT_TIMESTAMP
form; rows with NULL created_at cannot be dated and are excluded). The atoms
side was never lossy and is never filtered. The header records the filter
VERBATIM as `trace_since`; without --since nothing changes and no filter
field is written.

THE ARTIFACT: <box>/ego_fabric/collective/action_book.json -- REBUILT FROM
SCRATCH every run (the header field says so and carries the source stream
positions). A derived, rebuildable artifact, never the sole holder of
anything. The sources are never written; this file is the tool's ONLY output.

HONESTY RULES: every derived claim carries its evidence count; absence of
evidence is an explicit null with a NAMED reason, never a guess or an
authored default. NOTHING here maps an action int to a meaning -- every field
flows from the input records (gated structurally and by permutation
equivariance in tests/gate/test_action_book.py). The tool prints a per-game
coverage summary (actions seen, inverses with n>=2, cost evidence present) --
the artifact's own evidence-availability report.

Usage: python tools/build_action_book.py [--since "YYYY-MM-DD HH:MM:SS"]
                                          [BOX_DIR_OR_ROOT ...]
       (no box args: every box under .runs/swarm)

Deterministic: same inputs -> byte-identical artifact (gated). Stdlib +
engines.egocentric only; no wall-clock anywhere in the output.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sqlite3
import sys
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import action_book, effects

# ── the named reasons (the honesty rule's vocabulary; asserted verbatim in the gate) ──
R_NO_ATOM_STREAM = "no atoms stream recorded for this box"
R_NO_ATOMS_ACTION = "no atoms recorded for this action"
R_NO_TRACE_DB = "no action_traces DB recorded for this box"
R_NO_TRACES_ACTION = "no traces recorded for this action"
R_NO_BUDGET = "no traces with non-null budget"
R_NO_CHANGED = "atoms carry no changed-cell counts"
R_NO_COLOUR_DELTA = "no sigma colour deltas recorded"
R_NO_TRANSLATE = "no TRANSLATE-typed atoms recorded"
R_NO_FRAME_PAIRS = "no repeated frame pairs for this action"
R_NO_TYPED_ATOMS = "no composable typed atom deltas for this action"

# The one accepted --since form: SQLite CURRENT_TIMESTAMP's own text, so the
# filter is a plain text compare against created_at (UTC, no timezone suffix).
SINCE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ── source readers (read-only, streaming) ─────────────────────────────────────

def read_atom_stream(path: str) -> List[Dict[str, Any]]:
    """Parseable records in stream order; torn tails skipped, never fatal."""
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def canon_frame_hash(frame_text: Any) -> Optional[str]:
    """Content hash of one recorded frame: the JSON re-serialised canonically,
    so formatting differences never split equal frames. Unparseable text
    hashes verbatim (stated behaviour, not a guess); None stays None."""
    if frame_text is None:
        return None
    s = str(frame_text)
    try:
        s = json.dumps(json.loads(s), separators=(",", ":"), sort_keys=True)
    except Exception:
        pass
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def strict_frame_hash(frame_text: Any) -> Tuple[Optional[str], bool]:
    """(canonical content hash, unparseable) for INVERSE detection: a frame
    that is not valid JSON (a lossy numpy repr: '[[0 0 ... 0]') yields
    (None, True) -- it is never hashed verbatim, so two truncated reprs can
    never be 'equal'. None (absent) yields (None, False): absence is not
    unparseability."""
    if frame_text is None:
        return None, False
    try:
        s = json.dumps(json.loads(str(frame_text)), separators=(",", ":"),
                       sort_keys=True)
    except Exception:
        return None, True
    return hashlib.sha1(s.encode("utf-8")).hexdigest(), False


# ── the typed-mechanism identity (composition checked via the world's algebra) ─

def _canon_shape(shape: Any) -> Tuple[Tuple[int, int, int], ...]:
    return tuple(sorted((int(s[0]), int(s[1]), int(s[2])) for s in (shape or [])))


def mech_key(ttype: Any, params: Any) -> Optional[Tuple]:
    """Canonical identity of a typed mechanism, or None when there is no typed
    delta to compose (raw/NONE/unknown/malformed: no claim, never a guess).
    Mirrors exactly the parameters effects.invert_transform reasons over."""
    p = params or {}
    try:
        if ttype == "TRANSLATE":
            return ("TRANSLATE", int(p.get("dx", 0)), int(p.get("dy", 0)),
                    int(p.get("fill", 0)), _canon_shape(p.get("shape")))
        if ttype == "ROTATE":
            return ("ROTATE", int(p.get("k", 0)) % 4)
        if ttype == "REFLECT":
            axis = p.get("axis")
            return ("REFLECT", str(axis)) if axis in ("h", "v") else None
        if ttype == "SCALE":
            return ("SCALE", int(p.get("fx", 1)), int(p.get("fy", 1)),
                    str(p.get("mode")))
        if ttype == "COLOUR_PERM":
            mapping = tuple(sorted((int(s), int(d))
                            for s, d in (p.get("mapping") or [])))
            return ("COLOUR_PERM", mapping, _canon_shape(p.get("shape"))) \
                if mapping else None
        if ttype in ("OBJ_APPEAR", "OBJ_VANISH"):
            shape = _canon_shape(p.get("shape"))
            return (str(ttype), shape, int(p.get("fill", 0))) if shape else None
    except Exception:
        return None
    return None


def inverse_mech_key(ttype: Any, params: Any) -> Optional[Tuple]:
    """mech_key of the mechanism's computable inverse, through
    effects.invert_transform -- the world's own inverse algebra. None when the
    world names no inverse."""
    if not ttype or ttype == "NONE":
        return None
    try:
        inv = effects.invert_transform(str(ttype), dict(params or {}))
    except Exception:
        return None
    if inv is None:
        return None
    return mech_key(inv[0], inv[1])


# ── derivation: atoms side ────────────────────────────────────────────────────

def fold_atoms(records: Iterable[Dict[str, Any]]) -> Tuple[Dict[int, Dict[str, Any]],
                                                           List[str]]:
    """Per-action working aggregates from the atoms stream, deduped by record
    id LAST-WINS (a superseding append -- ctx_min etc. -- is an update to one
    observation, not a new one; Gamma.get reads the same way)."""
    last: OrderedDict[str, Dict[str, Any]] = OrderedDict()
    for i, rec in enumerate(records):
        if not isinstance(rec.get("atom"), dict):
            continue
        rid = str(rec.get("id") or "anon:%d" % i)
        last[rid] = rec
    per: Dict[int, Dict[str, Any]] = {}
    games: List[str] = []
    for rec in last.values():
        atom = rec["atom"]
        game = rec.get("game")
        if game and str(game) not in games:
            games.append(str(game))
        try:
            a = int(atom.get("action"))
        except (TypeError, ValueError):
            continue
        w = per.setdefault(a, {"n": 0, "changed": [], "ttypes": {},
                               "deltas": {}, "translate": {}, "mechs": {}})
        w["n"] += 1
        ch = atom.get("changed")
        if isinstance(ch, int) and not isinstance(ch, bool):
            w["changed"].append(ch)
        ttype = atom.get("ttype") or "NONE"
        w["ttypes"][str(ttype)] = w["ttypes"].get(str(ttype), 0) + 1
        delta = (atom.get("sigma") or {}).get("colour_delta")
        if isinstance(delta, list) and delta:
            try:
                dkey = json.dumps(sorted([int(s), int(d)] for s, d in delta),
                                  separators=(",", ":"))
            except (TypeError, ValueError):
                dkey = None
            if dkey is not None:
                w["deltas"][dkey] = w["deltas"].get(dkey, 0) + 1
        params = atom.get("params") or {}
        if ttype == "TRANSLATE":
            try:
                dxdy = (int(params.get("dx", 0)), int(params.get("dy", 0)))
                w["translate"][dxdy] = w["translate"].get(dxdy, 0) + 1
            except (TypeError, ValueError):
                pass
        mk = mech_key(atom.get("ttype"), params)
        if mk is not None:
            cnt, _tp = w["mechs"].get(mk, (0, None))
            w["mechs"][mk] = (cnt + 1, (atom.get("ttype"), params))
    return per, sorted(games)


def atom_inverse_pairs(per: Dict[int, Dict[str, Any]]) -> Dict[Tuple[int, int], int]:
    """(a, b) -> n atom pairs whose typed deltas compose to identity: for each
    of a's mechanisms m, every b-atom carrying inverse(m) pairs with every
    a-atom carrying m (ordered pairs of DISTINCT atoms -- a self-inverse
    mechanism inside one action never pairs an atom with itself)."""
    pairs: Dict[Tuple[int, int], int] = {}
    for a, wa in per.items():
        for mk, (cnt_a, tp) in wa["mechs"].items():
            ik = inverse_mech_key(tp[0], tp[1])
            if ik is None:
                continue
            for b, wb in per.items():
                got = wb["mechs"].get(ik)
                if not got:
                    continue
                cnt_b = got[0]
                n = cnt_a * cnt_b
                if a == b and ik == mk:
                    n = cnt_a * (cnt_a - 1)          # distinct atoms only
                if n > 0:
                    pairs[(a, b)] = pairs.get((a, b), 0) + n
    return pairs


# ── derivation: traces side ───────────────────────────────────────────────────

def fold_traces(rows: Iterable[Dict[str, Any]]) -> Tuple[Dict[int, Dict[str, Any]],
                                                         Dict[Tuple[int, int], int],
                                                         int]:
    """Per-action aggregates + inverse pair counts + the number of rows whose
    frames were unparseable (skipped for pair detection) from action_traces
    rows (dicts with id, session_id, action_number, score_change,
    budget_total, budget_spend, frame_before, frame_after), streamed in id
    order."""
    per: Dict[int, Dict[str, Any]] = {}
    pairs: Dict[Tuple[int, int], int] = {}
    prev: Dict[Any, Tuple[int, Optional[str], Optional[str]]] = {}
    skipped_unparseable = 0
    for row in rows:
        try:
            a = int(row.get("action_number") or 0)
        except (TypeError, ValueError):
            a = 0
        w = per.setdefault(a, {"n": 0, "changed_n": 0, "score": [],
                               "budget_n": 0, "spend": [], "total": []})
        w["n"] += 1
        hb = canon_frame_hash(row.get("frame_before"))
        ha = canon_frame_hash(row.get("frame_after"))
        if hb is not None and ha is not None and hb != ha:
            w["changed_n"] += 1
        sc = row.get("score_change")
        if sc is not None:
            try:
                w["score"].append(float(sc))
            except (TypeError, ValueError):
                pass
        bt, bs = row.get("budget_total"), row.get("budget_spend")
        if bt is not None or bs is not None:
            w["budget_n"] += 1
            if bt is not None:
                try:
                    w["total"].append(float(bt))
                except (TypeError, ValueError):
                    pass
            if bs is not None:
                try:
                    w["spend"].append(float(bs))
                except (TypeError, ValueError):
                    pass
        # inverse detection reads the STRICT hashes: an unparseable frame is
        # None here (the row can neither open nor close a pair), never the
        # verbatim-text hash the change-rate above tolerates
        sb, ub = strict_frame_hash(row.get("frame_before"))
        sa, ua = strict_frame_hash(row.get("frame_after"))
        if ub or ua:
            skipped_unparseable += 1
        sess = row.get("session_id")
        got = prev.get(sess)
        if got is not None:
            pa, p_hb, p_ha = got
            if (None not in (p_hb, p_ha, sb, sa)
                    and sb == p_ha                    # the steps chain
                    and p_ha != p_hb                  # a actually changed something
                    and sa == p_hb):                  # b restored it
                pairs[(pa, a)] = pairs.get((pa, a), 0) + 1
        prev[sess] = (a, sb, sa)
    return per, pairs, skipped_unparseable


# ── assembly ──────────────────────────────────────────────────────────────────

def _stats(xs: List[float]) -> Optional[Dict[str, Any]]:
    if not xs:
        return None
    return {"n": len(xs), "min": round(min(xs), 6), "max": round(max(xs), 6),
            "mean": round(sum(xs) / len(xs), 6)}


def _score_dist(xs: List[float]) -> Optional[Dict[str, Any]]:
    if not xs:
        return None
    return {"n": len(xs),
            "zero_n": sum(1 for x in xs if x == 0.0),
            "pos_n": sum(1 for x in xs if x > 0.0),
            "neg_n": sum(1 for x in xs if x < 0.0),
            "min": round(min(xs), 6), "max": round(max(xs), 6),
            "sum": round(sum(xs), 6)}


def _atoms_entry(w: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"n": w["n"]}
    changed = _stats([float(c) for c in w["changed"]])
    if changed is None:
        out["changed_cells"] = None
        out["changed_cells_absent"] = R_NO_CHANGED
    else:
        out["changed_cells"] = changed
    out["ttypes"] = {k: w["ttypes"][k] for k in sorted(w["ttypes"])}
    if w["deltas"]:
        out["colour_deltas"] = [
            {"delta": json.loads(k), "n": n}
            for k, n in sorted(w["deltas"].items(), key=lambda kv: (-kv[1], kv[0]))]
    else:
        out["colour_deltas"] = None
        out["colour_deltas_absent"] = R_NO_COLOUR_DELTA
    if w["translate"]:
        out["translate"] = [
            {"dx": dx, "dy": dy, "n": n}
            for (dx, dy), n in sorted(w["translate"].items(),
                                      key=lambda kv: (-kv[1], kv[0]))]
    else:
        out["translate"] = None
        out["translate_absent"] = R_NO_TRANSLATE
    return out


def build_book(box: str,
               atom_records: Optional[List[Dict[str, Any]]],
               trace_rows: Optional[Iterable[Dict[str, Any]]],
               sources: Optional[Dict[str, Any]] = None,
               trace_games: Optional[List[str]] = None,
               trace_since: Optional[str] = None) -> Dict[str, Any]:
    """The whole derivation, pure: records in, the book dict out. `None` for a
    source means the source itself is absent (a different named reason than a
    present-but-silent source). `trace_since` is the clean-window filter the
    caller ALREADY applied to `trace_rows` (the DB read does the restricting);
    here it is recorded verbatim in the header, never re-applied.
    Deterministic; JSON-safe throughout."""
    atoms_per, atom_games = ({}, []) if atom_records is None else fold_atoms(atom_records)
    skipped_unparseable = 0
    if trace_rows is None:
        traces_per: Dict[int, Dict[str, Any]] = {}
        trace_pairs: Dict[Tuple[int, int], int] = {}
    else:
        traces_per, trace_pairs, skipped_unparseable = fold_traces(trace_rows)
    a_pairs = atom_inverse_pairs(atoms_per)

    actions = sorted(set(atoms_per) | set(traces_per))
    entries: Dict[str, Any] = {}
    for a in actions:
        entry: Dict[str, Any] = {}
        aw = atoms_per.get(a)
        if atom_records is None:
            entry["atoms"] = None
            entry["atoms_absent"] = R_NO_ATOM_STREAM
        elif aw is None:
            entry["atoms"] = None
            entry["atoms_absent"] = R_NO_ATOMS_ACTION
        else:
            entry["atoms"] = _atoms_entry(aw)
        tw = traces_per.get(a)
        if trace_rows is None:
            entry["traces"] = None
            entry["traces_absent"] = R_NO_TRACE_DB
            entry["cost"] = None
            entry["cost_absent"] = R_NO_TRACE_DB
        elif tw is None:
            entry["traces"] = None
            entry["traces_absent"] = R_NO_TRACES_ACTION
            entry["cost"] = None
            entry["cost_absent"] = R_NO_TRACES_ACTION
        else:
            entry["traces"] = {
                "n": tw["n"],
                "frame_changed_n": tw["changed_n"],
                "frame_change_rate": round(tw["changed_n"] / tw["n"], 6),
                "score": _score_dist(tw["score"]),
            }
            if tw["budget_n"] > 0:
                entry["cost"] = {"n": tw["budget_n"],
                                 "budget_spend": _stats(tw["spend"]),
                                 "budget_total": _stats(tw["total"])}
            else:
                entry["cost"] = None
                entry["cost_absent"] = R_NO_BUDGET
        entries[str(a)] = entry

    inverses: Dict[str, Any] = {}
    for a in actions:
        pairs: Dict[str, Any] = {}
        for b in actions:
            nt = trace_pairs.get((a, b), 0)
            na = a_pairs.get((a, b), 0)
            if nt + na > 0:
                pairs[str(b)] = {"n_traces": nt, "n_atoms": na}
        if pairs:
            inverses[str(a)] = {"pairs": pairs}
        else:
            reasons = []
            if trace_rows is None:
                reasons.append(R_NO_TRACE_DB)
            elif a not in traces_per:
                reasons.append(R_NO_TRACES_ACTION)
            else:
                reasons.append(R_NO_FRAME_PAIRS)
            if atom_records is None:
                reasons.append(R_NO_ATOM_STREAM)
            else:
                reasons.append(R_NO_TYPED_ATOMS)
            inverses[str(a)] = {"pairs": None, "reason": "; ".join(reasons)}

    all_pair_n = {(a, b): trace_pairs.get((a, b), 0) + a_pairs.get((a, b), 0)
                  for (a, b) in set(trace_pairs) | set(a_pairs)}
    coverage = {
        "actions_seen": actions,
        "actions_n": len(actions),
        "inverse_pairs_n2": sorted("%d<-%d n=%d" % (b, a, n)
                                   for (a, b), n in all_pair_n.items() if n >= 2),
        "inverse_pairs_n1": sorted("%d<-%d" % (b, a)
                                   for (a, b), n in all_pair_n.items() if n == 1),
        "cost_evidence": any(w["budget_n"] > 0 for w in traces_per.values()),
    }

    games = list(atom_games)
    for g in sorted(trace_games or []):
        if str(g) not in games:
            games.append(str(g))
    book = {
        "artifact": action_book.ARTIFACT,
        "version": action_book.BOOK_VERSION,
        "derived": ("REBUILT FROM SCRATCH this run from the recorded sources "
                    "below -- a derived, rebuildable artifact; never the sole "
                    "holder of anything"),
        "box": str(box),
        "game_ids": sorted(games),
        "sources": sources or {},
        "actions": entries,
        "inverses": inverses,
        "coverage": coverage,
    }
    # The header additions are written ONLY when they say something: the
    # filter verbatim when one was applied, the skip count whenever a filter
    # was applied or a row was actually skipped. An unfiltered build over
    # fully parseable sources is byte-identical to one that never knew of
    # either field (gated).
    if trace_since is not None:
        book["trace_since"] = str(trace_since)
    if trace_since is not None or skipped_unparseable > 0:
        book["skipped_unparseable"] = skipped_unparseable
    return book


def serialise_book(book: Dict[str, Any]) -> str:
    """The one canonical byte form (rebuild identity is gated on it)."""
    return json.dumps(book, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False) + "\n"


# ── per-box IO (read-only on both sources; ONE output file) ───────────────────

# Every trace-side statement exists in two FIXED forms: unfiltered, and the
# clean window -- a text compare on created_at (SQLite CURRENT_TIMESTAMP form;
# NULL created_at never satisfies >=, so an undatable row is outside every
# window). The first element of each pair is today's exact statement.
_TRACE_SQL = (
    "SELECT id, session_id, action_number, score_change, "
    "budget_total, budget_spend, frame_before, frame_after "
    "FROM action_traces ORDER BY id",
    "SELECT id, session_id, action_number, score_change, "
    "budget_total, budget_spend, frame_before, frame_after "
    "FROM action_traces WHERE created_at >= ? ORDER BY id",
)
_COUNT_SQL = (
    "SELECT COUNT(*), COALESCE(MAX(id), 0) FROM action_traces",
    "SELECT COUNT(*), COALESCE(MAX(id), 0) FROM action_traces WHERE created_at >= ?",
)
_GAMES_SQL = (
    "SELECT DISTINCT game_id FROM action_traces "
    "WHERE game_id IS NOT NULL ORDER BY game_id",
    "SELECT DISTINCT game_id FROM action_traces "
    "WHERE game_id IS NOT NULL AND created_at >= ? ORDER BY game_id",
)


def _sql(pair: Tuple[str, str], trace_since: Optional[str]) -> Tuple[str, Tuple[str, ...]]:
    """(statement, bound params): the unfiltered form, or the windowed form
    with the verbatim --since text bound as its one parameter."""
    if trace_since is None:
        return pair[0], ()
    return pair[1], (str(trace_since),)


def _trace_row_iter(cur, trace_since: Optional[str] = None) -> Iterable[Dict[str, Any]]:
    cols = ("id", "session_id", "action_number", "score_change",
            "budget_total", "budget_spend", "frame_before", "frame_after")
    sql, params = _sql(_TRACE_SQL, trace_since)
    for row in cur.execute(sql, params):
        yield dict(zip(cols, row, strict=True))


def build_for_box(box_dir: str,
                  trace_since: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Derive and write one box's book; returns the book (None when the box
    holds NEITHER source -- nothing derivable, nothing written). With
    `trace_since`, every trace-side read (row count, game ids, the rows
    themselves) is restricted to created_at >= trace_since."""
    box = os.path.basename(os.path.normpath(box_dir))
    atoms_path = os.path.join(box_dir, "ego_fabric", "collective", "atoms.jsonl")
    db_path = os.path.join(box_dir, "core_data.db")
    have_atoms = os.path.isfile(atoms_path)
    have_db = os.path.isfile(db_path)
    if not have_atoms and not have_db:
        return None

    atom_records: Optional[List[Dict[str, Any]]] = None
    atoms_src: Dict[str, Any] = {"present": False,
                                 "path": "ego_fabric/collective/atoms.jsonl"}
    if have_atoms:
        atom_records = read_atom_stream(atoms_path)
        last_seq = 0
        for rec in atom_records:
            try:
                last_seq = max(last_seq, int(rec.get("seq", 0)))
            except (TypeError, ValueError):
                continue
        atoms_src = {"present": True,
                     "path": "ego_fabric/collective/atoms.jsonl",
                     "records_read": len(atom_records), "last_seq": last_seq}

    conn = None
    trace_rows: Optional[Iterable[Dict[str, Any]]] = None
    trace_games: List[str] = []
    traces_src: Dict[str, Any] = {"present": False, "path": "core_data.db"}
    if have_db:
        uri = "file:%s?mode=ro" % db_path.replace("\\", "/")
        conn = sqlite3.connect(uri, uri=True)
        try:
            n_rows, max_id = conn.execute(*_sql(_COUNT_SQL, trace_since)).fetchone()
            trace_games = [str(g) for (g,) in
                           conn.execute(*_sql(_GAMES_SQL, trace_since))]
            traces_src = {"present": True, "path": "core_data.db",
                          "rows_read": int(n_rows), "max_trace_id": int(max_id)}
            if trace_since is not None:
                n_all, _ = conn.execute(_COUNT_SQL[0]).fetchone()
                traces_src["rows_excluded_by_since"] = int(n_all) - int(n_rows)
            trace_rows = _trace_row_iter(conn.cursor(), trace_since)
        except sqlite3.Error as exc:
            conn.close()
            conn = None
            trace_rows = None
            traces_src = {"present": False, "path": "core_data.db",
                          "error": "unreadable: %s" % exc}
    try:
        book = build_book(box, atom_records, trace_rows,
                          sources={"atoms_stream": atoms_src,
                                   "traces_db": traces_src},
                          trace_games=trace_games,
                          trace_since=trace_since)
    finally:
        if conn is not None:
            conn.close()

    out_path = os.path.join(box_dir, action_book.BOOK_RELPATH)
    out_dir = os.path.dirname(out_path)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(serialise_book(book))
    return book


def coverage_line(book: Dict[str, Any]) -> str:
    """The per-game evidence-availability report, one line."""
    cov = book["coverage"]
    n2 = cov["inverse_pairs_n2"]
    n1 = cov["inverse_pairs_n1"]
    return ("action_book[%s]: actions seen %s | inverses n>=2: %d%s | "
            "inverses n=1: %d | cost evidence: %s" % (
                book["box"], cov["actions_seen"], len(n2),
                (" (%s)" % ", ".join(n2)) if n2 else "",
                len(n1),
                "PRESENT" if cov["cost_evidence"] else "NONE (%s)" % R_NO_BUDGET))


def _expand(args: List[str]) -> List[str]:
    """Each arg is a box dir (marked by its ego_fabric subdir -- the swarm
    root's own stray core_data.db must never classify the ROOT as a box) or a
    root of box dirs; no args -> .runs/swarm."""
    roots = args or [os.path.join(REPO, ".runs", "swarm")]
    boxes: List[str] = []
    for arg in roots:
        if os.path.isdir(os.path.join(arg, "ego_fabric")):
            boxes.append(arg)
            continue
        if os.path.isdir(arg):
            for name in sorted(os.listdir(arg)):
                sub = os.path.join(arg, name)
                if os.path.isdir(os.path.join(sub, "ego_fabric")):
                    boxes.append(sub)
    return boxes


def parse_since(text: str) -> str:
    """Validate one --since value against SINCE_FORMAT; returns it VERBATIM
    (the header carries exactly what the operator typed). ValueError when it
    is not that form -- a silently normalised filter would misreport."""
    try:
        _dt.datetime.strptime(text, SINCE_FORMAT)   # naive by design: UTC text compare
    except ValueError:
        raise ValueError(
            "--since must be 'YYYY-MM-DD HH:MM:SS' (UTC, SQLite CURRENT_TIMESTAMP "
            "form); got %r" % (text,)) from None
    return text


def parse_args(argv: List[str]) -> Tuple[List[str], Optional[str]]:
    """(box/root args, trace_since or None). Accepts --since VALUE and
    --since=VALUE, anywhere in argv; every other arg is a path."""
    paths: List[str] = []
    since: Optional[str] = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--since":
            if i + 1 >= len(argv):
                raise ValueError("--since requires a value")
            since = parse_since(argv[i + 1])
            i += 2
            continue
        if arg.startswith("--since="):
            since = parse_since(arg[len("--since="):])
            i += 1
            continue
        paths.append(arg)
        i += 1
    return paths, since


def main(argv: List[str]) -> int:
    try:
        paths, trace_since = parse_args(argv)
    except ValueError as exc:
        print("build_action_book: %s" % exc)
        return 2
    boxes = _expand(paths)
    if not boxes:
        print("build_action_book: no game boxes found (args: %r)" % (argv,))
        return 2
    if trace_since is not None:
        print("build_action_book: trace side restricted to created_at >= %r "
              "(atoms side unfiltered)" % trace_since)
    built = 0
    for box_dir in boxes:
        try:
            book = build_for_box(box_dir, trace_since=trace_since)
        except Exception as exc:
            print("action_book[%s]: FAILED -- %s"
                  % (os.path.basename(os.path.normpath(box_dir)), exc))
            continue
        if book is None:
            continue
        built += 1
        print(coverage_line(book))
    print("build_action_book: %d/%d boxes rebuilt from scratch" % (built, len(boxes)))
    return 0 if built else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
