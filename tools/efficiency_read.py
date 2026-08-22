"""efficiency_read.py -- ITEM 2: THE EFFICIENCY READ (distance-to-that-player).

READ, NEVER TARGET.

THE REGISTRATION (record/canon/THE_GOALS.md, ITEM-2 QUALIFICATION, maintainer 2026-08-17):
this is a RUNG-0 RESOLUTION INSTRUMENT with an EXPLICIT PROHIBITION on being a
knob target or an arm objective until levels move. RHAE is a ratio against a
solution and is UNDEFINED AT ZERO LEVELS; optimizing it before solving is
optimizing a quantity that does not exist yet. What the read buys is RESOLUTION
ON A ZERO -- "closer without a level" becomes readable -- and nothing else. Its
output feeds beat reports (record/canon/THE_LADDER.md rung 0, levels_completed). No knob.

THE LABEL (EXECUTION RIDER 2, reviewer 2026-08-17): the reference is ONE WIN
REPLAY -- a single run, not the upper-median human distribution RHAE normalizes
against. So every line this instrument emits carries the words

    one reference run, not a reference distribution

because the convention has to do the remembering: the first close-looking number
would otherwise be read as closer to the bar than it is.

WHAT IT READS (all read-only; the instrument never writes a byte of the books):
  * THE REFERENCE -- `baseline_actions` in each game's replay metadata.json
    (`<box>/environment_files/<game>/<hash>/metadata.json`): a per-level list of
    the reference run's action counts, level 1 first. Read off disk, never
    hardcoded. record/canon/THE_GOALS.md cites ls20's counts inline; `verify_cited_ls20`
    checks that citation against the on-disk record and REPORTS the comparison
    (see CITED_LS20) -- the citation is a claim under audit, never a data source.
  * THE OBSERVATION -- the swarm boxes' `winning_sequences` (plus
    `archived_sequences` where present): one row per level actually beaten,
    `total_actions` = the actions spent ON THAT LEVEL. The swarm's best is the
    MINIMUM over observations, tail-scoped by `--since` / `--generation-min`.
  * THE BOUND -- `game_results` gives no per-level split, so the only honest
    thing it yields is an UPPER BOUND on actions-to-complete-level-L: the
    smallest episode total among episodes completing at least L levels. It is
    reported as a bound and never differenced against the reference.
  * `settlements.jsonl` carries NO action counts (agent/game/level/action/best
    only), so it cannot source this read; that limitation is printed, not hidden.

NOT-MEASURABLE IS AN OUTPUT. A game with a reference and no banked replay, or a
replay and no reference, reads NOT-MEASURABLE -- never 0, never a plausible
number standing in for an absent one (THE_LADDER, THE INEXPRESSIBLE-STATE GENUS).

INVOCATION: the beat protocol (a rung-0 read), operator-run:
    python tools/efficiency_read.py --root .runs/swarm [--since YYYY-MM-DD]
Pure stdlib, deterministic, read-only.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Sequence

__all__ = ["LABEL", "PROHIBITION", "CITED_LS20", "DEFAULT_ROOT",
           "discover_references", "discover_observations", "verify_cited_ls20",
           "efficiency_report", "render", "main"]

# EXECUTION RIDER 2's exact words. Carried on EVERY output line.
LABEL = "one reference run, not a reference distribution"

# ITEM-2 QUALIFICATION's exact words. Printed in the header.
PROHIBITION = "READ, NEVER TARGET"

# record/canon/THE_GOALS.md line 47 cites these as "ls20 replay expert counts". They are a
# CITATION UNDER AUDIT, not an input: `verify_cited_ls20` compares them against
# the on-disk metadata and reports the result. Nothing else in this module reads
# this tuple, and no reference value is ever taken from it.
CITED_LS20 = (21, 123, 39, 92, 54, 108, 109)

DEFAULT_ROOT = os.path.join(".runs", "swarm")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# The reference: replay metadata on disk
# ─────────────────────────────────────────────────────────────────────────────

def discover_references(roots: Sequence[str]) -> Dict[str, List[int]]:
    """{game_id: per-level reference action counts} from every metadata.json
    under `roots`. Later roots never overwrite an earlier root's answer, so the
    caller controls precedence. Malformed metadata is skipped, never raised on.
    Sources are recorded by `reference_sources`."""
    return {g: v for g, (v, _src) in _references_with_sources(roots).items()}


def reference_sources(roots: Sequence[str]) -> Dict[str, str]:
    """{game_id: the metadata.json path the reference came from}."""
    return {g: src for g, (_v, src) in _references_with_sources(roots).items()}


def _references_with_sources(roots) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for root in roots or ():
        if not root or not os.path.isdir(str(root)):
            continue
        pat = os.path.join(str(root), "**", "metadata.json")
        for path in sorted(glob.glob(pat, recursive=True)):
            try:
                with open(path, encoding="utf-8") as fh:
                    meta = json.load(fh)
            except Exception:
                continue
            if not isinstance(meta, dict):
                continue
            gid = str(meta.get("game_id") or "")
            base = meta.get("baseline_actions")
            if not gid or not isinstance(base, list) or not base:
                continue
            try:
                vals = [int(v) for v in base]
            except Exception:
                continue
            out.setdefault(gid, (vals, path.replace("\\", "/")))
    return out


def verify_cited_ls20(refs: Dict[str, List[int]],
                      sources: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Audit record/canon/THE_GOALS.md's inline ls20 citation against the on-disk record.

    Returns {found, game, on_disk, cited, match, mismatch_levels, source}.
    A mismatch is a REPORTED FINDING, never a silent substitution: the read
    keeps using the on-disk numbers either way."""
    game = next((g for g in sorted(refs) if g.startswith("ls20")), None)
    if game is None:
        return {"found": False, "game": None, "on_disk": None,
                "cited": list(CITED_LS20), "match": False,
                "mismatch_levels": [], "source": ""}
    on_disk = list(refs[game])
    cited = list(CITED_LS20)
    mism = [i + 1 for i in range(max(len(on_disk), len(cited)))
            if (on_disk[i] if i < len(on_disk) else None)
            != (cited[i] if i < len(cited) else None)]
    return {"found": True, "game": game, "on_disk": on_disk, "cited": cited,
            "match": on_disk == cited, "mismatch_levels": mism,
            "source": (sources or {}).get(game, "")}


# ─────────────────────────────────────────────────────────────────────────────
# The observation: the swarm boxes' DBs (read-only)
# ─────────────────────────────────────────────────────────────────────────────

def _open_ro(path: str):
    """Read-only sqlite handle, or None. `mode=ro` is the guarantee; the tool
    never opens a book any other way."""
    try:
        uri = "file:%s?mode=ro" % path.replace("\\", "/").replace("?", "%3f")
        return sqlite3.connect(uri, uri=True)
    except Exception:
        return None


def _columns(con, table: str) -> List[str]:
    try:
        return [str(r[1]) for r in
                con.execute("PRAGMA table_info(%s)" % table).fetchall()]
    except Exception:
        return []


def _rows(con, table: str, wanted: Sequence[str]) -> List[Dict[str, Any]]:
    """SELECT only the columns this box actually has (old boxes lack some) --
    a missing column degrades the field to None, never the whole read."""
    cols = _columns(con, table)
    if not cols:
        return []
    take = [c for c in wanted if c in cols]
    if not take:
        return []
    try:
        raw = con.execute("SELECT %s FROM %s"  # noqa: S608 - fixed identifiers
                          % (", ".join(take), table)).fetchall()
    except Exception:
        return []
    out = []
    for r in raw:
        rec = dict(zip(take, r, strict=False))
        for c in wanted:
            rec.setdefault(c, None)
        out.append(rec)
    return out


def _in_window(stamp, since: Optional[str]) -> Optional[bool]:
    """True/False in-window, or None when the row carries no stamp at all.
    An undated row under an active --since is DROPPED and counted: pooling two
    populations is exactly the defect the AS-OF rule exists to prevent."""
    if not since:
        return True
    if stamp in (None, ""):
        return None
    return str(stamp)[:len(str(since))] >= str(since)


def discover_observations(root: str, since: Optional[str] = None,
                          generation_min: Optional[int] = None) -> Dict[str, Any]:
    """Per game: the swarm's best observed actions per level (banked replays),
    the episode-total bound per level, exposure, and the AS-OF span.

    Shape: {"games": {game_id: {...}}, "boxes": [...], "dbs": [...],
            "dropped_undated": int, "span": [first, last] or None}"""
    games: Dict[str, Any] = {}
    boxes: List[str] = []
    dbs: List[str] = []
    dropped = 0
    span: List[str] = []

    root = str(root)
    if not os.path.isdir(root):
        return {"games": games, "boxes": boxes, "dbs": dbs,
                "dropped_undated": 0, "span": None}

    for db in sorted(glob.glob(os.path.join(root, "*", "core_data.db"))
                     + glob.glob(os.path.join(root, "core_data.db"))):
        box = os.path.basename(os.path.dirname(db))
        con = _open_ro(db)
        if con is None:
            continue
        dbs.append(db.replace("\\", "/"))
        if box not in boxes:
            boxes.append(box)
        try:
            wins = _rows(con, "winning_sequences",
                         ("game_id", "level_number", "total_actions",
                          "is_active", "discovered_at", "generation_discovered"))
            arch = _rows(con, "archived_sequences",
                         ("game_id", "level_number", "total_actions",
                          "archived_at"))
            eps = _rows(con, "game_results",
                        ("game_id", "total_actions", "level_completions",
                         "created_at"))
        finally:
            con.close()

        for rec, kind, stampcol in ([(w, "winning", "discovered_at") for w in wins]
                                    + [(a, "archived", "archived_at")
                                       for a in arch]):
            gid = str(rec.get("game_id") or "")
            if not gid or rec.get("level_number") is None:
                continue
            if kind == "winning" and rec.get("is_active") == 0:
                continue
            gen = rec.get("generation_discovered")
            if (generation_min is not None and gen is not None
                    and int(gen) < int(generation_min)):
                continue
            ok = _in_window(rec.get(stampcol), since)
            if ok is None:
                dropped += 1
                continue
            if not ok:
                continue
            if rec.get(stampcol):
                span.append(str(rec.get(stampcol)))
            try:
                lvl, acts = int(rec["level_number"]), int(rec["total_actions"])
            except Exception:
                continue
            g = games.setdefault(gid, _blank_game())
            if box not in g["boxes"]:
                g["boxes"].append(box)
            slot = g["observed"].setdefault(lvl, {"best": acts, "n": 0,
                                                  "kinds": []})
            slot["best"] = min(slot["best"], acts)
            slot["n"] += 1
            if kind not in slot["kinds"]:
                slot["kinds"].append(kind)

        for rec in eps:
            gid = str(rec.get("game_id") or "")
            if not gid:
                continue
            ok = _in_window(rec.get("created_at"), since)
            if ok is None:
                dropped += 1
                continue
            if not ok:
                continue
            g = games.setdefault(gid, _blank_game())
            if box not in g["boxes"]:
                g["boxes"].append(box)
            g["episodes"] += 1
            try:
                total = int(rec.get("total_actions") or 0)
                done = int(rec.get("level_completions") or 0)
            except Exception:
                continue
            for lvl in range(1, done + 1):
                cur = g["episode_bound"].get(lvl)
                g["episode_bound"][lvl] = total if cur is None else min(cur, total)

    return {"games": games, "boxes": boxes, "dbs": dbs,
            "dropped_undated": dropped,
            "span": [min(span), max(span)] if span else None}


def _blank_game() -> Dict[str, Any]:
    return {"boxes": [], "observed": {}, "episodes": 0, "episode_bound": {}}


# ─────────────────────────────────────────────────────────────────────────────
# The report
# ─────────────────────────────────────────────────────────────────────────────

def efficiency_report(root: str = DEFAULT_ROOT,
                      refs_roots: Optional[Sequence[str]] = None,
                      since: Optional[str] = None,
                      generation_min: Optional[int] = None) -> Dict[str, Any]:
    """The rung-0 resolution read: per game+level, distance-to-that-player.

    THE INSTRUMENT'S ONE PROHIBITION travels with its output: this number is a
    READ, NEVER A TARGET (no knob, no arm objective, until levels move)."""
    if refs_roots is None:
        refs_roots = [str(root), os.path.join(_REPO, "environment_files")]
    src_map = _references_with_sources(refs_roots)
    refs = {g: v for g, (v, _s) in src_map.items()}
    sources = {g: s for g, (_v, s) in src_map.items()}
    obs = discover_observations(root, since=since, generation_min=generation_min)

    games: List[Dict[str, Any]] = []
    for gid in sorted(set(refs) | set(obs["games"])):
        og = obs["games"].get(gid) or _blank_game()
        ref = refs.get(gid)
        observed = og["observed"]
        measurable = bool(ref) and bool(observed)
        reason = None
        if not ref and observed:
            reason = ("NOT-MEASURABLE: banked replay present, no reference "
                      "run on disk (no baseline_actions metadata)")
        elif ref and not observed:
            reason = ("NOT-MEASURABLE: reference run present, no banked win "
                      "replay in any box (nothing to compare)")
        elif not ref and not observed:
            reason = ("NOT-MEASURABLE: neither a reference run nor a banked "
                      "win replay")
        if ref is None and gid not in obs["games"]:
            continue

        n_levels = max(len(ref or ()), max(observed) if observed else 0)
        rows: List[Dict[str, Any]] = []
        ref_cum = obs_cum = 0
        cum_live = True
        for lvl in range(1, n_levels + 1):
            r = ref[lvl - 1] if ref and lvl <= len(ref) else None
            slot = observed.get(lvl)
            o = slot["best"] if slot else None
            if r is not None:
                ref_cum += r
            if o is not None and cum_live:
                obs_cum += o
            else:
                cum_live = cum_live and o is not None
            row = {
                "level": lvl,
                "reference": r,
                "observed_best": o,
                "n_observations": (slot or {}).get("n", 0),
                "sources": (slot or {}).get("kinds", []),
                "episode_total_bound": og["episode_bound"].get(lvl),
                "reference_cum": ref_cum if r is not None else None,
                "observed_cum": obs_cum if (o is not None and cum_live) else None,
                "distance": None, "distance_cum": None, "ratio": None,
                "measurable": False, "reason": None,
            }
            if r is None and o is None:
                row["reason"] = "NOT-MEASURABLE: no reference, no observation"
            elif r is None:
                row["reason"] = ("NOT-MEASURABLE: observed but the reference "
                                 "run has no count for this level")
            elif o is None:
                row["reason"] = ("NOT-MEASURABLE: reference present, level "
                                 "never banked by the swarm")
            else:
                row["measurable"] = True
                row["distance"] = o - r
                row["ratio"] = (float(o) / float(r)) if r else None
                if row["observed_cum"] is not None:
                    row["distance_cum"] = row["observed_cum"] - row["reference_cum"]
            rows.append(row)

        games.append({
            "game": gid, "boxes": og["boxes"], "measurable": measurable,
            "reason": reason, "reference": ref,
            "reference_source": sources.get(gid),
            "reference_levels": len(ref or ()), "episodes": og["episodes"],
            "levels": rows,
        })

    return {
        "root": str(root),
        "as_of": {"since": since, "generation_min": generation_min,
                  "boxes": len(obs["boxes"]), "dbs": len(obs["dbs"]),
                  "observed_span": obs["span"],
                  "dropped_undated": obs["dropped_undated"]},
        "games": games,
        "cited_check": verify_cited_ls20(refs, sources),
        "notes": [
            "reference = one banked win replay's per-level action counts "
            "(metadata.json baseline_actions), read off disk",
            "observed = MIN total_actions over banked winning_sequences / "
            "archived_sequences rows for that game+level",
            "episode_total_bound = smallest game_results episode total among "
            "episodes completing >= that level: an UPPER BOUND, never "
            "differenced against the reference",
            "settlements.jsonl carries no action counts and cannot source "
            "this read",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# The rendering: every line labelled
# ─────────────────────────────────────────────────────────────────────────────

def _line(text: str) -> str:
    return "%s | %s" % (text, LABEL)


def _fmt(v, none="n/a") -> str:
    return none if v is None else str(v)


def render(report: Dict[str, Any], as_json: bool = False) -> List[str]:
    """Beat-report lines. EVERY line carries LABEL -- in the human rendering as
    a suffix, in the JSON rendering as the record's own `label` field."""
    if as_json:
        out = [json.dumps({"kind": "header", "label": LABEL,
                           "prohibition": PROHIBITION,
                           "as_of": report["as_of"], "notes": report["notes"],
                           "cited_check": report["cited_check"]},
                          sort_keys=True)]
        for g in report["games"]:
            out.append(json.dumps({"kind": "game", "label": LABEL,
                                   **{k: v for k, v in g.items()
                                      if k != "levels"}}, sort_keys=True))
            for row in g["levels"]:
                out.append(json.dumps({"kind": "level", "label": LABEL,
                                       "game": g["game"], **row},
                                      sort_keys=True))
        return out

    a = report["as_of"]
    lines = [
        _line("[EFF] %s -- rung-0 RESOLUTION instrument (record/canon/THE_GOALS.md ITEM-2 "
              "QUALIFICATION; record/canon/THE_LADDER.md rung 0). No knob, no arm "
              "objective, until levels move." % PROHIBITION),
        _line("[EFF] distance-to-that-player = swarm best observed actions "
              "MINUS the reference run's actions, per game+level."),
        _line("[EFF] as-of: since=%s generation_min=%s boxes=%d dbs=%d "
              "observed_span=%s undated_rows_dropped=%d"
              % (_fmt(a["since"], "all"), _fmt(a["generation_min"], "all"),
                 a["boxes"], a["dbs"], _fmt(a["observed_span"], "none"),
                 a["dropped_undated"])),
    ]
    c = report["cited_check"]
    if c["found"]:
        lines.append(_line(
            "[EFF] CITED-CHECK %s: on-disk=%s cited=%s match=%s "
            "mismatch_levels=%s source=%s"
            % (c["game"], c["on_disk"], c["cited"], c["match"],
               c["mismatch_levels"], c["source"])))
    else:
        lines.append(_line("[EFF] CITED-CHECK: NOT-MEASURABLE -- no on-disk "
                           "ls20 reference to audit the citation against"))
    for note in report["notes"]:
        lines.append(_line("[EFF] note: %s" % note))
    if not report["games"]:
        lines.append(_line("[EFF] no swarm boxes and no references under %s -- "
                           "NOT-MEASURABLE" % report["root"]))

    for g in report["games"]:
        head = ("[EFF] %s boxes=%s episodes=%d ref_levels=%d"
                % (g["game"], ",".join(g["boxes"]) or "-", g["episodes"],
                   g["reference_levels"]))
        if not g["measurable"]:
            lines.append(_line("%s %s" % (head, g["reason"])))
        else:
            lines.append(_line("%s reference_source=%s"
                               % (head, g["reference_source"])))
        for row in g["levels"]:
            if row["measurable"]:
                lines.append(_line(
                    "[EFF]   %s L%d ref=%d best=%d dist=%+d ratio=%.2f n=%d "
                    "cum_ref=%s cum_best=%s cum_dist=%s ep_bound=%s"
                    % (g["game"], row["level"], row["reference"],
                       row["observed_best"], row["distance"], row["ratio"],
                       row["n_observations"], _fmt(row["reference_cum"]),
                       _fmt(row["observed_cum"]), _fmt(row["distance_cum"]),
                       _fmt(row["episode_total_bound"]))))
            else:
                lines.append(_line(
                    "[EFF]   %s L%d ref=%s best=%s %s"
                    % (g["game"], row["level"], _fmt(row["reference"]),
                       _fmt(row["observed_best"]), row["reason"])))
    n_meas = sum(1 for g in report["games"] if g["measurable"])
    lines.append(_line("[EFF] summary: %d/%d games measurable; %d level "
                       "comparisons"
                       % (n_meas, len(report["games"]),
                          sum(1 for g in report["games"] for r in g["levels"]
                              if r["measurable"]))))
    return lines


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="ITEM 2: the efficiency read -- %s" % PROHIBITION)
    ap.add_argument("--root", default=DEFAULT_ROOT,
                    help="swarm root holding the per-game boxes")
    ap.add_argument("--refs", action="append", default=None,
                    help="extra root to search for replay metadata.json "
                         "(repeatable; defaults to --root plus the repo's "
                         "environment_files/)")
    ap.add_argument("--since", default=None,
                    help="tail-scope: keep only rows stamped on/after this "
                         "ISO date (undated rows are dropped and counted)")
    ap.add_argument("--generation-min", type=int, default=None,
                    help="tail-scope: keep only sequences from this "
                         "generation onward")
    ap.add_argument("--json", action="store_true",
                    help="one JSON record per line (each carries `label`)")
    args = ap.parse_args(list(argv) if argv is not None else None)

    report = efficiency_report(args.root, refs_roots=args.refs,
                               since=args.since,
                               generation_min=args.generation_min)
    for line in render(report, as_json=args.json):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
