"""RUNG 0d · CONSUMPTION SWEEP — the mechanical half that stops recurrence.

Two AST passes over production code. Neither requires anyone to remember anything.

PASS A · WRITER-READER PAIRING
    For every fabric stream published and every SQL table written, is there a read of it
    in a production path? Catches the empty-table family and stream-level severance.
    Each reader is further classified ABORT-LIKE vs DECIDE-LIKE, because rung 0d asks for
    a reader that CHANGES WHAT THE AGENT DOES, not one that merely halts it. A stream
    read only to stop satisfies naive pairing while exhibiting exactly the pathology.

PASS B · LITERAL-IN-DECISION vs MEASUREMENT-EXISTS
    For every numeric literal sitting in a feasibility/ranking/threshold decision, does a
    measured value for that quantity exist somewhere in the system?

THE HONESTY RULE (Seat 4, and it is the whole point):
    THREE OUTCOMES, NEVER TWO. A constant is only CONSTITUTIVE if something says so.
    "Nobody has measured it yet" is LATENT — unbuilt, not cleared. Anything unplaced is
    UNCLASSIFIED. The sweep must never convert absence-of-measurement into a clean bill.

Read-only. Exits 1 if any UNPAIRED stream/table or any MEASURED-ELSEWHERE hit is found,
so it can serve as a gate once CI enforcement exists.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

# Production scope: the live path. Tests, tools, archives and run dirs are NOT production
# — a reader that only exists in a test is exactly the green-and-inert genus.
PROD_DIRS = ["engines", "cognitive_loop.py", "cognitive_game_player.py", "database_interface.py"]
EXCLUDE_PARTS = {".runs", ".venv", ".git", "tests", "deprecated", "archive",
                 "environment_files", "__pycache__", "manual_tools", "tools"}

# A reader that only brakes. Rung 0d's abort/decide clause.
ABORT_TOKENS = ("abort", "halt", "stop", "reset", "stuck", "guard", "bail", "kill",
                "terminate", "give_up", "giveup", "escape", "panic", "corpse")
# A reader that changes a choice.
DECIDE_TOKENS = ("plan", "rank", "select", "choose", "score", "prefer", "plan_", "plan(",
                 "plan ", "target", "plan_toward", "propose", "bid", "weight", "order",
                 "priorit", "decide", "plan_step", "goal", "plan_action")

# Decision contexts for pass B: a literal here is deciding something.
DECISION_KW = ("budget", "limit", "max_actions", "threshold", "min_evidence", "cap",
               "ttl", "stall", "max_size", "max_shift", "occupancy", "overlap",
               "max_expand", "purity", "min_obs", "half_life", "max_condition_cells",
               "per_key", "max_keys", "demote", "eps")

# ── THE PROVENANCE MAP ──────────────────────────────────────────────────────────
# This is a CURATED map and it is deliberately small. Everything not named here is
# reported UNCLASSIFIED — never CLEARED. Populating this map is a human judgement and
# must stay one; the instrument's job is to refuse to guess.
#   MEASURED_ELSEWHERE: the system holds a measurement and the decision ignores it.
#   LATENT:             no measurement exists; one COULD. Unbuilt, not cleared.
#   CONSTITUTIVE:       fixed by the frame we chose, not by the world.
PROVENANCE: Dict[str, Tuple[str, str]] = {
    # KNOBS A13 / Register L sweep, 2026-08-18
    "max_actions": ("MEASURED_ELSEWHERE",
                    "BOARD_AUDIT s2: a 64-cell clock in column 63 is the real regime; "
                    "the literal is 500, consumed as feasibility at cognitive_loop.py"
                    ":1168-1169/:1250-1251. Measured OFFLINE and never read online."),
    "max_condition_cells": ("LATENT",
                            "caps precondition WIDTH; BOARD_AUDIT s4/s7 says ACTION6 is "
                            "gated by a precondition with no slot. No estimator exists."),
    "max_shift": ("LATENT", "how far a move carries — a per-game fact, unmeasured."),
    "stall_steps": ("LATENT", "when a goal counts as stalled = game tempo, unmeasured."),
    "max_size": ("LATENT", "largest targetable object — per-game, unmeasured."),
    "birth_min_overlap": ("LATENT", "object identity across frames = motion speed."),
    "death_occupancy": ("LATENT", "object identity across frames = motion speed."),
    "ttl": ("LATENT", "path lifetime — depends on board scale, unmeasured."),
    "max_expand": ("LATENT", "search ceiling; scales with board size."),
    # Epistemic thresholds — about how much evidence convinces us, NOT about the world.
    "min_evidence": ("CONSTITUTIVE", "the wheel rule: evidence semantics, KNOBS F8."),
    "min_obs": ("CONSTITUTIVE", "evidence semantics, not a world fact."),
    "purity": ("CONSTITUTIVE", "evidence semantics, not a world fact."),
    "eps": ("CONSTITUTIVE", "numerical guard, frame-fixed."),
    "half_life": ("CONSTITUTIVE", "credibility decay: our accounting, not the world's."),
}


def schema_tables() -> Set[str]:
    """The REAL table names, from the schema. Without this the SQL regexes below happily
    report `table:FROM`, `table:INTEGER` and `table:SET` as unpaired tables — an
    instrument that manufactures its own findings. Anything not declared in the schema is
    a parse artifact and is dropped, not counted."""
    out: Set[str] = set()
    p = ROOT / "complete_database_schema.sql"
    if p.exists():
        for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?(\w+)",
                             p.read_text(encoding="utf-8", errors="replace"), re.I):
            out.add(m.group(1))
    return out


def prod_files() -> List[Path]:
    out: List[Path] = []
    for spec in PROD_DIRS:
        p = ROOT / spec
        if p.is_file() and p.suffix == ".py":
            out.append(p)
        elif p.is_dir():
            for f in p.rglob("*.py"):
                if not (set(f.relative_to(ROOT).parts) & EXCLUDE_PARTS):
                    out.append(f)
    return sorted(set(out))


def _src(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _enclosing_names(tree: ast.AST) -> Dict[int, str]:
    """line -> enclosing function name, for the abort/decide classification."""
    m: Dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            for ln in range(node.lineno, end + 1):
                m[ln] = node.name
    return m


def _classify_reader(fn_name: str, context: str) -> str:
    blob = f"{fn_name} {context}".lower()
    if any(t in blob for t in DECIDE_TOKENS):
        return "DECIDE-LIKE"
    if any(t in blob for t in ABORT_TOKENS):
        return "ABORT-ONLY"
    return "UNKNOWN"


# ── PASS A ──────────────────────────────────────────────────────────────────────
def pass_a() -> Tuple[List[str], List[str], Dict[str, List[str]]]:
    """Fabric streams and SQL tables: written where, read where, and does the reader
    change a choice or only trip a brake?"""
    real_tables = schema_tables()
    writes: Dict[str, List[str]] = {}
    reads: Dict[str, List[Tuple[str, str]]] = {}

    sql_ins = re.compile(r"(?:INSERT\s+(?:OR\s+\w+\s+)?INTO|REPLACE\s+INTO|UPDATE)\s+"
                         r"[`\"\[]?(\w+)", re.I)
    sql_sel = re.compile(r"(?:FROM|JOIN)\s+[`\"\[]?(\w+)", re.I)

    for f in prod_files():
        src = _src(f)
        if not src:
            continue
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        fnmap = _enclosing_names(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fname = ""
            if isinstance(node.func, ast.Attribute):
                fname = node.func.attr
            elif isinstance(node.func, ast.Name):
                fname = node.func.id
            # fabric.append(scope, TOPIC, {...}) / fabric.query(scope, TOPIC, ...)
            if fname in ("append", "query") and len(node.args) >= 2:
                topic = None
                a = node.args[1]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    topic = a.value
                elif isinstance(a, ast.Name):
                    topic = f"<{a.id}>"
                elif isinstance(a, ast.Attribute):
                    topic = f"<{a.attr}>"
                if topic:
                    key = f"stream:{topic}"
                    site = f"{rel}:{node.lineno}"
                    if fname == "append":
                        writes.setdefault(key, []).append(site)
                    else:
                        ctx = ast.get_source_segment(src, node) or ""
                        fn = fnmap.get(node.lineno, "?")
                        reads.setdefault(key, []).append(
                            (site, _classify_reader(fn, ctx)))

        for m in sql_ins.finditer(src):
            if m.group(1) in real_tables:
                writes.setdefault(f"table:{m.group(1)}", []).append(rel)
        for m in sql_sel.finditer(src):
            if m.group(1) in real_tables:
                reads.setdefault(f"table:{m.group(1)}", []).append(
                    (rel, _classify_reader("?", "")))

    unpaired = sorted(k for k in writes if k not in reads)
    abort_only: Dict[str, List[str]] = {}
    for k, rs in reads.items():
        if k in writes and rs and all(c == "ABORT-ONLY" for _, c in rs):
            abort_only[k] = [s for s, _ in rs]
    write_only_tables = sorted(k for k in unpaired if k.startswith("table:"))
    return unpaired, write_only_tables, abort_only


# ── PASS B ──────────────────────────────────────────────────────────────────────
def pass_b() -> List[Dict[str, Any]]:
    """Numeric literals sitting in decision positions, each with a provenance verdict."""
    hits: List[Dict[str, Any]] = []
    for f in prod_files():
        src = _src(f)
        if not src:
            continue
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue

        def record(name: str, value: Any, lineno: int, kind: str,
                   _rel: str = rel) -> None:
            base = name.lower().lstrip("_")
            verdict, why = PROVENANCE.get(base, ("UNCLASSIFIED", ""))
            hits.append({"file": _rel, "line": lineno, "name": name, "value": value,
                         "kind": kind, "verdict": verdict, "why": why})

        for node in ast.walk(tree):
            # default arguments in signatures
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                a = node.args
                pairs = list(zip(a.args[len(a.args) - len(a.defaults):], a.defaults, strict=False)) \
                    if a.defaults else []
                pairs += list(zip(a.kwonlyargs, a.kw_defaults or [], strict=False))
                for arg, dflt in pairs:
                    if (isinstance(dflt, ast.Constant)
                            and isinstance(dflt.value, (int, float))
                            and not isinstance(dflt.value, bool)
                            and any(k in arg.arg.lower() for k in DECISION_KW)):
                        record(arg.arg, dflt.value, dflt.lineno, "default-arg")
            # module/class constants and self.X = <num>
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                    and isinstance(node.value.value, (int, float)) \
                    and not isinstance(node.value.value, bool):
                for t in node.targets:
                    nm = t.id if isinstance(t, ast.Name) else (
                        t.attr if isinstance(t, ast.Attribute) else None)
                    if nm and any(k in nm.lower() for k in DECISION_KW):
                        record(nm, node.value.value, node.lineno, "assignment")
            # literal fallbacks: x.get("budget", 500)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "get" and len(node.args) == 2:
                k, d = node.args
                if (isinstance(k, ast.Constant) and isinstance(k.value, str)
                        and isinstance(d, ast.Constant)
                        and isinstance(d.value, (int, float))
                        and not isinstance(d.value, bool)
                        and any(kw in k.value.lower() for kw in DECISION_KW)):
                    record(k.value, d.value, node.lineno, "get-default")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on NEW unpaired streams or NEW MEASURED_ELSEWHERE hits "
                         "(a RATCHET against tools/consumption_baseline.json, not an "
                         "absolute bar -- see --update-baseline)")
    ap.add_argument("--update-baseline", action="store_true",
                    help="rewrite the baseline to today's findings. Legitimate ONLY when "
                         "an item is deliberately accepted and recorded; shrinking it is "
                         "the point, growing it needs a ruling.")
    args = ap.parse_args()

    unpaired, write_only_tables, abort_only = pass_a()
    hits = pass_b()

    order = ["MEASURED_ELSEWHERE", "UNCLASSIFIED", "LATENT", "CONSTITUTIVE"]
    by: Dict[str, List[Dict[str, Any]]] = {v: [] for v in order}
    for h in hits:
        by.setdefault(h["verdict"], []).append(h)

    if args.json:
        print(json.dumps({"unpaired": unpaired, "write_only_tables": write_only_tables,
                          "abort_only": abort_only, "literals": hits}, indent=2))
    else:
        print("=" * 78)
        print("RUNG 0d · CONSUMPTION SWEEP")
        print("=" * 78)
        print("\nPASS A · WRITER-READER PAIRING  (production scope only)")
        print(f"  streams/tables WRITTEN AND NEVER READ: {len(unpaired)}")
        for k in unpaired[:40]:
            print(f"    UNPAIRED  {k}")
        if len(unpaired) > 40:
            print(f"    ... and {len(unpaired) - 40} more")
        # THE ABORT/DECIDE CLAUSE IS NOT IMPLEMENTED, AND THIS PRINTS THAT RATHER THAN A
        # NUMBER. The classifier is a token heuristic over enclosing function names. It
        # returned 0 on a system where two abort-only consumers were identified BY HAND
        # (reset detection, stuck-loop guard) — so a zero here is EVIDENCE THE HEURISTIC
        # DOES NOT WORK, not evidence the pathology is absent. A measurement nobody can
        # distinguish from a null result is exactly the guaranteed-number trap, and
        # printing "0" would get cited as a clean bill within a week.
        print("\n  READ ONLY TO BRAKE (rung 0d's abort/decide clause): NOT IMPLEMENTED")
        print("    The rung requires a reader that CHANGES A CHOICE, not one that halts.")
        print("    This pass CANNOT yet distinguish them. Two abort-only consumers are")
        print("    known by hand and this classifier finds neither. DO NOT CITE A COUNT")
        print(f"    HERE. (heuristic's raw output, for debugging only: {len(abort_only)})")

        print(f"\nPASS B · LITERALS IN DECISION PATHS: {len(hits)}")
        for v in order:
            rows = by.get(v, [])
            print(f"\n  {v}: {len(rows)}")
            for h in rows[:25]:
                print(f"    {h['file']}:{h['line']}  {h['name']} = {h['value']}"
                      f"  [{h['kind']}]")
                if h["why"]:
                    print(f"        {h['why']}")
            if len(rows) > 25:
                print(f"    ... and {len(rows) - 25} more")
        print("\n" + "-" * 78)
        print("THE HONESTY RULE: UNCLASSIFIED IS NOT CLEARED. A constant is CONSTITUTIVE")
        print("only where a human said so; absence of a measurement is LATENT (unbuilt).")
        print("-" * 78)

    # ── THE RATCHET ────────────────────────────────────────────────────────────────
    # A gate that is red on the day it is installed gets disabled within a week, and
    # THE_LADDER's own rule is NO PERMANENT RED. So --strict fails on what is NEW against
    # a recorded baseline, and ALSO fails when the baseline has grown stale -- an item
    # that has since been fixed must leave the baseline, so the list can only shrink.
    bl_path = ROOT / "tools" / "consumption_baseline.json"
    current = sorted(set(unpaired) |
                     {f"literal:{h['file']}:{h['name']}"
                      for h in by.get("MEASURED_ELSEWHERE", [])})

    if args.update_baseline:
        bl_path.write_text(json.dumps({"accepted": current}, indent=2) + "\n",
                           encoding="utf-8")
        print(f"\nbaseline rewritten: {len(current)} accepted item(s) -> {bl_path}")
        return 0

    accepted: Set[str] = set()
    if bl_path.exists():
        try:
            accepted = set(json.loads(bl_path.read_text(encoding="utf-8")).get("accepted", []))
        except (OSError, ValueError):
            accepted = set()

    new_items = [c for c in current if c not in accepted]
    fixed = sorted(accepted - set(current))

    if not args.json:
        print(f"\nRATCHET  accepted-baseline={len(accepted)}  current={len(current)}  "
              f"NEW={len(new_items)}  FIXED-BUT-STILL-LISTED={len(fixed)}")
        for c in new_items:
            print(f"    NEW VIOLATION  {c}")
        for c in fixed:
            print(f"    FIXED - REMOVE FROM BASELINE  {c}")

    if args.strict and (new_items or fixed):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
