"""W4 B21: the n=1 discontinuity metric — refit-vs-remint audit over a fabric dir.

THE QUESTION: for every minted atom, how long from mint to independent verification?
Time is fabric seq (the only clock the books carry): an atom's mint time is its seq in
the atoms stream (cross-checked against the mint_verdicts entry that carries its key);
its verification time is the first settlement/verification record that says TRANSFERRED
*about that atom*. A vocabulary that transfers (Isaiah's OOD directive) shows small
mint-to-verification gaps; a vocabulary that must be re-minted per level shows atoms
verified never.

THE HONESTY CLAUSE: verification linkage requires the settling record to NAME the atom
(an id/key field) or carry a TRANSFERRED bin. This tool DISCOVERS the linkage fields
from the records themselves; when the current books carry no such field — and 2026-08's
settlements are {agent,game,level,action,members,best,nontrivial,seq}, atom-blind — it
reports MISSING LINKAGE, loudly, rather than faking a join through game/level/action
coincidence. A missing instrument reported is a routed fix; a fabricated join is a
captured ground.

  python tools/n1_metric.py .runs/swarm/ar25/ego_fabric

Stdlib only; read-only over the fabric; dev-time tool, never imported by agents.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FABRIC = os.path.join(REPO, ".runs", "swarm", "ar25", "ego_fabric")

ATOM_KEY_SHAPE = re.compile(r"^(eff|cmp)-[0-9a-f]{6,}")
VERIF_STREAM_HINT = re.compile(r"settle|verif|replay|transfer", re.I)
LINK_FIELD_HINT = re.compile(r"^(key|atom|atom_id|atom_key|id|ids|steps)$")


def _read_stream(path):
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def _streams(root):
    """{topic: [records...]} merged across collective/ + personal/* + kin/*."""
    dirs = [os.path.join(root, "collective")]
    for family in ("personal", "kin"):
        d = os.path.join(root, family)
        if os.path.isdir(d):
            dirs.extend(os.path.join(d, sub) for sub in sorted(os.listdir(d)))
    topics = {}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.endswith(".jsonl"):
                topics.setdefault(name[:-6], []).extend(
                    _read_stream(os.path.join(d, name)))
    return topics


def _atom_mentions(rec, ids, keys):
    """Atom ids/keys this record names, wherever it names them (discovered, not assumed)."""
    found = set()
    def walk(v):
        if isinstance(v, str):
            if v in ids or v in keys:
                found.add(v)
        elif isinstance(v, dict):
            for k, sub in v.items():
                if (LINK_FIELD_HINT.match(str(k)) or isinstance(sub, (dict, list))
                        or (isinstance(sub, str) and ATOM_KEY_SHAPE.match(sub))):
                    walk(sub)
        elif isinstance(v, list):
            for sub in v:
                walk(sub)
    walk(rec)
    return found


def _is_transferred(rec):
    return any(isinstance(v, str) and v.upper() == "TRANSFERRED" for v in rec.values())


def main(argv=None):
    ap = argparse.ArgumentParser(description="per-atom time-to-first-mint vs "
                                             "time-to-first-TRANSFERRED (fabric seq)")
    ap.add_argument("fabric", nargs="?", default=DEFAULT_FABRIC, help="fabric root dir")
    args = ap.parse_args(argv)
    root = args.fabric
    if not os.path.isdir(root):
        print("no fabric dir at %s" % root)
        return 2

    topics = _streams(root)
    atoms = topics.get("atoms", [])
    verdicts = topics.get("mint_verdicts", [])
    print("n=1 metric over %s" % root)
    print("streams: %s" % ", ".join("%s(%d)" % (t, len(r))
                                    for t, r in sorted(topics.items())))
    if not atoms:
        print("VERDICT: no atoms stream — nothing minted here yet")
        return 0

    ids = {r.get("id") for r in atoms if r.get("id")}
    keys = {(r.get("atom") or {}).get("key") for r in atoms} - {None}

    # mint-verdict seq per key (first "mint" verdict carrying the key)
    mint_seq_by_key = {}
    for v in verdicts:
        if v.get("verdict") == "mint" and v.get("key") in keys:
            mint_seq_by_key.setdefault(v["key"], v.get("seq"))

    # ── linkage discovery over every settlement/verification-shaped stream ────
    verif_topics = {t: recs for t, recs in topics.items()
                    if VERIF_STREAM_HINT.search(t) and t != "mint_verdicts"}
    linkage = {}          # atom id/key -> first (topic, seq) that verified it
    linked_records = 0
    transferred_records = 0
    for t, recs in sorted(verif_topics.items()):
        for rec in recs:
            mentions = _atom_mentions(rec, ids, keys)
            transferred = _is_transferred(rec)
            if transferred:
                transferred_records += 1
            if mentions:
                linked_records += 1
            if mentions and (transferred or t != "settlements"):
                for m in mentions:
                    prev = linkage.get(m)
                    cur = (t, rec.get("seq") or 0)
                    if prev is None or cur[1] < prev[1]:
                        linkage[m] = cur

    # ── the per-atom table ────────────────────────────────────────────────────
    print("%-28s %-6s %5s %9s %11s %s" % ("atom id", "game", "lvl",
                                          "mint_seq", "verdict_seq", "first_verified"))
    verified = 0
    for r in sorted(atoms, key=lambda a: int(a.get("seq") or 0)):
        aid = r.get("id")
        key = (r.get("atom") or {}).get("key")
        hit = linkage.get(aid) or linkage.get(key)
        if hit:
            verified += 1
            v = "%s seq %s (gap %+d)" % (hit[0], hit[1],
                                         int(hit[1]) - int(r.get("seq") or 0))
        else:
            v = "—"
        print("%-28s %-6s %5s %9s %11s %s"
              % (aid, str(r.get("game"))[:6], r.get("level"),
                 r.get("seq"), mint_seq_by_key.get(key, "—"), v))

    # ── the verdict ───────────────────────────────────────────────────────────
    print("atoms=%d | with mint_verdict key-link=%d | verified=%d"
          % (len(atoms), sum(1 for r in atoms
                             if (r.get("atom") or {}).get("key") in mint_seq_by_key),
             verified))
    if verified == 0:
        fields = set()
        for recs in verif_topics.values():
            for rec in recs[:50]:
                fields.update(rec.keys())
        print("VERDICT: MISSING LINKAGE — %d records across %s carry no atom id/key "
              "and no TRANSFERRED bin naming an atom (observed fields: %s). "
              "Time-to-first-TRANSFERRED is UNMEASURABLE on these books; the router's "
              "TRANSFERRED bin settles in-process and is never written with the atom's "
              "identity. Routed fix: settlements (or a verification stream) must carry "
              "the atom id it settled."
              % (sum(len(r) for r in verif_topics.values()),
                 "/".join(sorted(verif_topics)) or "(no verification-shaped streams)",
                 ", ".join(sorted(fields))))
        return 1
    print("VERDICT: %d/%d atoms verified via discovered linkage" % (verified, len(atoms)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
