"""G-B: the R_T bracket residual — the promote->seed->re-derive round trip measured.

Fig D's caption, finally an instrument: R_T = |T_A . T_E(x) - x|. A promoted
generator x (a collective EFFECT atom with mint provenance) is EXPORTED through the
membrane as a prior, T_E(x): only its sigma — the consumer's shared description
vocabulary — ever crosses; the atom's transform/context content and every playback/
winning-sequence channel stay behind (the membrane law, asserted, not assumed). A
fresh box then RE-DERIVES, T_A: it drives its own evidence, prior-guided, until the
mint re-constructs a sigma-equivalent atom. The bracket residual is the divergence
between the re-derived atom and the original:

    R_T = sigma_distance(x, x')  +  |cost(x) - cost(x')| / max(cost)

reported beside the kernel it cost to get there (evidence-to-rederivation), against
a COLD control box with no seed — the prior's value is the DELTA, never a vibe.

SYNTHETIC MODE (the gate's arm): two in-process fabrics per arm. Box A mints the
generator (provenance on A's books), promotes its sigma as a GENERATOR_PRIOR idea,
and a seed is built from A's PRIORS STREAM ONLY. Box B mounts that seed read-only
and drains a fixed synthetic evidence agenda — prior-guided when a prior is visible,
arrival order when cold. Three arms: sharp (full sigma), blunt (degraded sigma),
cold (no seed). Falsifiers: seeded re-derivation is cheaper than cold; R_T falls as
the prior sharpens; the membrane holds throughout.

LIVE MODE: read-only over swarm boxes (.runs/swarm/<game>/ego_fabric). The swarm
cross-mounts every box's fabric, so a generator promoted in one box surfaces in a
sibling as a NOVELTY-blocked "rederivation" verdict naming the same canonical key —
key identity is patch-level identity, so that leg's R_T is exactly 0. A3-4-stamped
verdicts (an "ep" episode ordinal + the rederiving event's own "sigma") are READ
when present: the rederivation-time sigma leg is then measured against the origin
atom's sigma. Everything the books do NOT carry (unstamped verdicts, seed-mount
manifests) is reported MISSING, loudly — an absent instrument is a routed fix; a
fabricated join is a captured ground.

  python tools/bracket_rt.py synthetic
  python tools/bracket_rt.py live [.runs/swarm | .runs/swarm/ar25]

[BRACKET] report lines. Deterministic; stdlib + numpy + the egocentric engine;
dev-time tool, never imported by agents.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import numpy as np

from engines.egocentric.consumer import INVARIANTS, sigma_of
from engines.egocentric.effects import Gamma, encoding_cost_atom
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.mint import MDLMint

DEFAULT_SWARM = os.path.join(REPO, ".runs", "swarm")

# ── the membrane law, as code ─────────────────────────────────────────────────
# Playback channels are DB-side by law (winning_sequences, salient_prefixes);
# none of their content may appear inside any fabric stream, ever. A SEED is
# stricter still: it carries priors only — never the atom itself, so no atoms
# stream and no atom transform/context content may cross.
PLAYBACK_TOPICS = ("winning_sequences", "salient_prefixes", "playback")
PLAYBACK_FIELDS = ("prefix_json", "winning_sequence", "salient_prefix")
ATOM_CONTENT_FIELDS = ("transform", "context")

# The seed copies the priors economy ONLY (fabric.priors reads exactly these).
PRIOR_TOPICS = ("ideas", "idea_events")


class MembraneViolation(AssertionError):
    """Playback or atom content crossed a boundary it must never cross."""


def _read_stream(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
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


def _jsonl_files(root: str) -> List[str]:
    hits: List[str] = []
    for dirpath, _dirs, files in os.walk(root):
        hits.extend(os.path.join(dirpath, f) for f in sorted(files)
                    if f.endswith(".jsonl"))
    return sorted(hits)


def _fields_present(value: Any, fields: Tuple[str, ...]) -> List[str]:
    """Which of `fields` appear as a dict key anywhere inside `value` (recursive)."""
    found: List[str] = []
    if isinstance(value, dict):
        for k, sub in value.items():
            if str(k) in fields:
                found.append(str(k))
            found.extend(_fields_present(sub, fields))
    elif isinstance(value, list):
        for sub in value:
            found.extend(_fields_present(sub, fields))
    return found


def membrane_violations(roots) -> List[str]:
    """Playback content inside ANY fabric root is a violation, topic or field."""
    out: List[str] = []
    for root in roots:
        for path in _jsonl_files(str(root)):
            topic = os.path.basename(path)[:-6]
            if topic in PLAYBACK_TOPICS:
                out.append("playback topic %r in fabric root: %s" % (topic, path))
                continue
            for i, rec in enumerate(_read_stream(path)):
                hit = _fields_present(rec, PLAYBACK_FIELDS)
                if hit:
                    out.append("playback field(s) %s in %s record %d"
                               % ("/".join(sorted(set(hit))), path, i))
    return out


def seed_violations(seed_root: str) -> List[str]:
    """A seed carries priors ONLY: playback rules plus never-the-atom-itself."""
    out = membrane_violations([seed_root])
    for path in _jsonl_files(str(seed_root)):
        topic = os.path.basename(path)[:-6]
        if topic == "atoms":
            out.append("the atoms stream crossed into a seed: %s" % path)
            continue
        for i, rec in enumerate(_read_stream(path)):
            hit = _fields_present(rec, ATOM_CONTENT_FIELDS)
            if hit:
                out.append("atom content (%s) crossed into seed %s record %d"
                           % ("/".join(sorted(set(hit))), path, i))
    return out


def assert_membrane(fabric_roots, seed_roots=()) -> None:
    """Raise MembraneViolation (loud, never silent) on any crossing."""
    problems = membrane_violations(fabric_roots)
    for seed in seed_roots:
        problems.extend(seed_violations(seed))
    if problems:
        raise MembraneViolation("MEMBRANE VIOLATED:\n  " + "\n  ".join(problems))


# ── the residual: sigma distance + cost delta ─────────────────────────────────

def sigma_distance(sa: Dict[str, Any], sb: Dict[str, Any]) -> float:
    """Fraction of the match INVARIANTS on which two sigmas disagree (a missing
    axis disagrees — an impoverished description is distance, not a free pass)."""
    diff = sum(1 for k in INVARIANTS
               if k not in sa or k not in sb or sa[k] != sb[k])
    return diff / float(len(INVARIANTS))


def cost_delta(ca: float, cb: float) -> float:
    """Normalized encoding-cost divergence in [0, 1)."""
    return abs(float(ca) - float(cb)) / max(float(ca), float(cb), 1.0)


# ── synthetic mode: two in-process fabrics per arm ────────────────────────────

GAME = "bracket-g"


def _board(cells) -> np.ndarray:
    b = np.zeros((8, 8), dtype=int)
    for r, c, v in cells:
        b[r, c] = v
    return b


def _true_event(pos: Tuple[int, int]):
    """THE generator: a 1-cell recolour 3 -> 5, position-free canonical key."""
    r, c = pos
    return _board([(r, c, 3)]), 6, _board([(r, c, 5)])


def _evidence() -> List[Tuple[np.ndarray, int, np.ndarray]]:
    """The fixed synthetic agenda a fresh box drives, arrival order. Three
    mintable noise mechanisms first, then a NEAR variant of the generator
    (one sigma axis off: colour_delta), then the generator itself."""
    z = np.zeros((8, 8), dtype=int)
    n1 = z.copy()
    n1[4:6, 1:3] = 7                                       # 2x2 block appears
    n2 = z.copy()
    n2[7, 2:5] = 2                                         # 1x3 row appears
    n3 = z.copy()
    n3[0:3, 0] = 6                                         # 3x1 col appears
    near_b, near_a = _board([(1, 6, 3)]), _board([(1, 6, 4)])   # recolour 3 -> 4
    true_b, act, true_a = _true_event((2, 3))
    return [(z, 6, n1), (z, 6, n2), (z, 6, n3),
            (near_b, 6, near_a), (true_b, act, true_a)]


def _affinity(prior_sigma: Dict[str, Any], ev_sigma: Dict[str, Any]) -> int:
    """How many of the PRIOR's axes this evidence matches — the kernel the
    prior lowers: attention, never a verdict (the mint's bars are untouched)."""
    return sum(1 for k, v in prior_sigma.items()
               if k in ev_sigma and ev_sigma[k] == v)


def _agenda(evidence, prior_sigma: Optional[Dict[str, Any]]) -> List[int]:
    """Evidence order: prior-guided (descending affinity, stable) when a prior
    is mounted; arrival order when cold."""
    if not prior_sigma:
        return list(range(len(evidence)))
    sigmas = [sigma_of(b, a) for b, _act, a in evidence]
    return sorted(range(len(evidence)),
                  key=lambda i: (-_affinity(prior_sigma, sigmas[i]), i))


def _promote(fabric_a: KnowledgeFabric, target: Dict[str, Any], arm: str) -> None:
    """T_E(x): export the generator as a PRIOR — its sigma only, sharpness per
    arm. The atom's transform/context content NEVER enters the idea."""
    sig = dict(target.get("sigma") or {})
    prior_sigma = sig if arm == "sharp" else {
        k: sig[k] for k in ("arity", "mag") if k in sig}
    fabric_a.mint({"kind": "GENERATOR_PRIOR", "sigma": prior_sigma}, GAME,
                  signal={"type": "promotion", "atom_key": target.get("key")},
                  scope="collective", level=1)


def build_prior_seed(a_root: str, seed_root: str) -> str:
    """The membrane crossing, as a copy: A's PRIOR streams only (collective
    ideas + idea_events), record-filtered through the seed rules. Anything
    else on A's books — atoms, queues, verdicts, playback — stays behind."""
    src_dir = os.path.join(a_root, "collective")
    dst_dir = os.path.join(seed_root, "collective")
    os.makedirs(dst_dir, exist_ok=True)
    for topic in PRIOR_TOPICS:
        recs = _read_stream(os.path.join(src_dir, topic + ".jsonl"))
        if not recs:
            continue
        with open(os.path.join(dst_dir, topic + ".jsonl"), "w",
                  encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    assert_membrane([], seed_roots=[seed_root])
    return seed_root


def run_bracket(workdir: str, arm: str) -> Dict[str, Any]:
    """One arm of the round trip: mint x in A, promote (unless cold), seed B,
    drive the fixed evidence until a sigma-equivalent atom is re-derived.
    Membrane asserted before AND after the measurement."""
    if arm not in ("sharp", "blunt", "cold"):
        raise ValueError("arm must be sharp|blunt|cold, got %r" % (arm,))
    a_root = os.path.join(str(workdir), arm, "box_a")
    b_root = os.path.join(str(workdir), arm, "box_b")
    seed_root = os.path.join(str(workdir), arm, "seed") if arm != "cold" else None

    # T_A in box A: the generator is minted with provenance (mint_verdicts).
    fabric_a = KnowledgeFabric(a_root, agent_id="box_a")
    mint_a = MDLMint(Gamma(fabric_a))
    tb, tact, ta = _true_event((5, 5))
    verdict = mint_a.consider(tb, tact, ta, GAME, 1)
    if verdict.get("verdict") != "mint":
        raise RuntimeError("the synthetic generator failed to mint in A: %r" % verdict)
    target = Gamma(fabric_a).get(verdict["id"]) or {}
    target_sigma = dict(target.get("sigma") or {})
    target_cost = encoding_cost_atom(target)

    seeds: List[str] = []
    if seed_root is not None:
        _promote(fabric_a, target, arm)                    # T_E(x): sigma crosses
        build_prior_seed(a_root, seed_root)
        seeds = [seed_root]
    assert_membrane([a_root], seed_roots=seeds)

    # T_A in box B: re-derive from B's OWN evidence, prior-guided attention.
    fabric_b = KnowledgeFabric(b_root, seeds=seeds, agent_id="box_b")
    mint_b = MDLMint(Gamma(fabric_b))
    prior_sigma = None
    for p in fabric_b.priors(GAME):
        idea = p.get("idea") or {}
        if isinstance(idea.get("sigma"), dict):
            prior_sigma = idea["sigma"]
            break
    evidence = _evidence()
    first_mint: Optional[Dict[str, Any]] = None
    evidence_to_rederivation: Optional[int] = None
    rederived_key: Optional[str] = None
    used = 0
    for i in _agenda(evidence, prior_sigma):
        eb, eact, ea = evidence[i]
        used += 1
        v = mint_b.consider(eb, eact, ea, GAME, 1)
        if v.get("verdict") != "mint":
            continue
        atom = Gamma(fabric_b).get(v["id"]) or {}
        dist = sigma_distance(target_sigma, atom.get("sigma") or {})
        cd = cost_delta(target_cost, encoding_cost_atom(atom))
        if first_mint is None:
            first_mint = {"key": atom.get("key"), "sigma_dist": dist,
                          "cost_delta": cd, "r_t": dist + cd}
        if dist == 0.0:
            evidence_to_rederivation = used
            rederived_key = atom.get("key")
            break

    assert_membrane([a_root, b_root], seed_roots=seeds)    # nothing crossed while measuring
    return {
        "arm": arm,
        "seeded": bool(seeds),
        "a_root": a_root, "b_root": b_root, "seed_root": seed_root,
        "target_key": target.get("key"),
        "evidence_used": used,
        "evidence_to_rederivation": evidence_to_rederivation,
        "first_mint": first_mint or {"key": None, "sigma_dist": 1.0,
                                     "cost_delta": 1.0, "r_t": 2.0},
        "key_match": rederived_key == target.get("key") and rederived_key is not None,
    }


def synthetic_report(workdir: str, out=print) -> Tuple[int, Dict[str, Any]]:
    """All three arms + the falsifier verdicts, [BRACKET] lines throughout."""
    arms = {arm: run_bracket(workdir, arm) for arm in ("sharp", "blunt", "cold")}
    for arm in ("sharp", "blunt", "cold"):
        r = arms[arm]
        fm = r["first_mint"]
        out("[BRACKET] synthetic game=%s arm=%s seeded=%d "
            "evidence_to_rederivation=%s sigma_dist=%.3f cost_delta=%.3f "
            "R_T=%.3f key_match=%d"
            % (GAME, arm, int(r["seeded"]),
               r["evidence_to_rederivation"], fm["sigma_dist"], fm["cost_delta"],
               fm["r_t"], int(r["key_match"])))
    cheaper = (arms["sharp"]["evidence_to_rederivation"] is not None
               and arms["cold"]["evidence_to_rederivation"] is not None
               and arms["sharp"]["evidence_to_rederivation"]
               < arms["cold"]["evidence_to_rederivation"])
    rt = {a: arms[a]["first_mint"]["r_t"] for a in arms}
    monotone = rt["sharp"] < rt["blunt"] < rt["cold"]
    roots = [p for r in arms.values()
             for p in (r["a_root"], r["b_root"], r["seed_root"]) if p]
    held = not membrane_violations(roots)
    out("[BRACKET] synthetic verdict: seeded_cheaper_than_cold=%s (%s < %s) "
        "R_T_monotone=%s (%.3f < %.3f < %.3f) membrane=%s"
        % ("PASS" if cheaper else "FAIL",
           arms["sharp"]["evidence_to_rederivation"],
           arms["cold"]["evidence_to_rederivation"],
           "PASS" if monotone else "FAIL", rt["sharp"], rt["blunt"], rt["cold"],
           "HELD" if held else "VIOLATED"))
    return (0 if (cheaper and monotone and held) else 1,
            {"arms": arms, "cheaper": cheaper, "monotone": monotone,
             "membrane_held": held})


# ── live mode: read-only over the swarm's real boxes ──────────────────────────

def _fabric_of(box: str) -> str:
    return os.path.join(box, "ego_fabric")


def _boxes_under(root: str) -> List[str]:
    root = os.path.abspath(root)
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return []
    return [os.path.join(root, n) for n in names
            if os.path.isdir(_fabric_of(os.path.join(root, n)))]


def _box_books(fabric_root: str) -> Dict[str, Any]:
    """One box's atoms + mint verdicts, LOCAL streams only (collective dir).
    A3-4: rederivation entries carry the verdict's ep + sigma stamps when the
    books have them (None when absent -- old books read unchanged)."""
    coll = os.path.join(fabric_root, "collective")
    atoms = _read_stream(os.path.join(coll, "atoms.jsonl"))
    verdicts = _read_stream(os.path.join(coll, "mint_verdicts.jsonl"))
    minted = {}                                            # key -> first mint seq
    reder = []                                             # {key, seq, ep, sigma}
    stamped = 0                                            # verdicts carrying ep+sigma
    for v in verdicts:
        if isinstance(v.get("ep"), int) and isinstance(v.get("sigma"), dict):
            stamped += 1
        key = v.get("key")
        if not key:
            continue
        if v.get("verdict") == "mint":
            minted.setdefault(key, v.get("seq"))
        elif v.get("verdict") == "rederivation":
            sig = v.get("sigma")
            reder.append({"key": key, "seq": v.get("seq"),
                          "ep": v.get("ep") if isinstance(v.get("ep"), int) else None,
                          "sigma": sig if isinstance(sig, dict) else None})
    atom_keys = {(r.get("atom") or {}).get("key") for r in atoms} - {None}
    key_sigma = {}                                         # key -> the atom's sigma
    for r in atoms:
        atom = r.get("atom") or {}
        if atom.get("key") and isinstance(atom.get("sigma"), dict):
            key_sigma.setdefault(atom["key"], atom["sigma"])
    return {"atoms": atoms, "verdicts": verdicts, "minted": minted,
            "rederivations": reder, "local_keys": atom_keys | set(minted),
            "key_sigma": key_sigma, "stamped": stamped}


def live_report(path: str, out=print) -> int:
    """Read-only bracket over real boxes: cross-box rederivations by canonical
    key (that leg's R_T is exactly 0 — key identity IS patch identity), honest
    MISSING for every linkage the books do not carry. Exit 1 when nothing is
    measurable."""
    path = os.path.abspath(str(path))
    if os.path.isdir(_fabric_of(path)):
        focus = [path]
        universe = _boxes_under(os.path.dirname(path)) or [path]
        if path not in universe:
            universe = [*universe, path]
    else:
        focus = universe = _boxes_under(path)
    if not focus:
        out("[BRACKET] live: no boxes with an ego_fabric under %s -- "
            "MISSING: nothing to measure" % path)
        return 1

    books = {box: _box_books(_fabric_of(box)) for box in universe}
    key_origins: Dict[str, List[str]] = {}
    origin_sigma: Dict[str, Dict[str, Any]] = {}           # key -> minted atom's sigma
    for box, bb in books.items():
        for key in bb["local_keys"]:
            key_origins.setdefault(key, []).append(box)
        for key, sig in bb["key_sigma"].items():
            origin_sigma.setdefault(key, sig)

    measurable = 0
    for box in focus:
        bb = books[box]
        name = os.path.basename(box)
        viols = membrane_violations([_fabric_of(box)])
        within = sum(1 for r in bb["rederivations"]
                     if r["key"] in bb["local_keys"])
        out("[BRACKET] live box=%s atoms=%d minted=%d rederivation_verdicts=%d "
            "(within_box=%d cross_box_candidates=%d) membrane=%s"
            % (name, len(bb["atoms"]), len(bb["minted"]),
               len(bb["rederivations"]), within,
               len(bb["rederivations"]) - within,
               "HELD" if not viols else "VIOLATED"))
        for v in viols:
            out("[BRACKET] live box=%s MEMBRANE VIOLATION: %s" % (name, v))
        cross: Dict[str, List[Dict[str, Any]]] = {}
        for r in bb["rederivations"]:
            if r["key"] not in bb["local_keys"]:
                cross.setdefault(r["key"], []).append(r)
        for key in sorted(cross):
            hits = cross[key]
            seqs = [r["seq"] for r in hits]
            origins = [os.path.basename(b) for b in key_origins.get(key, [])
                       if b != box]
            if origins:
                measurable += 1
                # A3-4: sigma-stamped verdicts make the rederivation-time sigma
                # leg MEASURABLE against the origin atom's sigma; ep gives WHEN.
                extra = ""
                stamped_hits = [r for r in hits if r["sigma"] is not None]
                osig = origin_sigma.get(key)
                if stamped_hits and isinstance(osig, dict):
                    dists = [sigma_distance(osig, r["sigma"])
                             for r in stamped_hits]
                    eps = sorted({r["ep"] for r in stamped_hits
                                  if r["ep"] is not None})
                    extra = (" verdict_sigma_dist=%.3f (over %d stamped) ep=%s"
                             % (min(dists), len(stamped_hits),
                                ",".join(str(e) for e in eps) or "?"))
                elif stamped_hits:
                    extra = (" verdict sigma stamped x%d but the origin atom "
                             "carries no sigma -- that leg stays MISSING"
                             % len(stamped_hits))
                out("[BRACKET] live box=%s cross-box rederivation key=%s "
                    "origin=%s first_verdict_seq=%s rederivations=%d "
                    "R_T=0.000 (key identity is patch-level identity: "
                    "sigma_dist=0, cost_delta=0)%s"
                    % (name, key, "|".join(origins),
                       min((s for s in seqs if s is not None), default=None),
                       len(seqs), extra))
                if len(origins) > 1:
                    out("[BRACKET] live box=%s MISSING: no seed-mount manifest "
                        "on disk -- origin of %s ambiguous across %d boxes"
                        % (name, key, len(origins)))
            else:
                out("[BRACKET] live box=%s MISSING: rederivation of %s names "
                    "no visible origin atom (compacted or out-of-universe) -- "
                    "the promote leg is unmeasurable here" % (name, key))
    # A3-4 stamps ledger: honest about what the books carry, either way.
    total_v = sum(len(books[b]["verdicts"]) for b in focus)
    stamped_v = sum(books[b]["stamped"] for b in focus)
    if stamped_v < total_v or total_v == 0:
        out("[BRACKET] live MISSING: %d/%d mint_verdicts carry no episode "
            "ordinal (ep) / event sigma -- evidence_to_rederivation and the "
            "full R_T bracket are UNMEASURABLE on the unstamped remainder; "
            "routed fix (A3-4, landed): new verdicts carry ep + sigma"
            % (total_v - stamped_v, total_v))
    else:
        out("[BRACKET] live stamps: ep+sigma present on all %d mint_verdicts "
            "-- episode ordinals and rederivation-time sigma are measurable "
            "on these books (A3-4)" % total_v)
    if measurable:
        out("[BRACKET] live verdict: %d cross-box rederivation(s) measured "
            "(R_T=0.000 on the key-identity leg); remaining legs MISSING as "
            "itemized above" % measurable)
        return 0
    out("[BRACKET] live verdict: MISSING -- no cross-box rederivation "
        "observable; the round trip leaves no measurable trace on these books")
    return 1


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="R_T bracket: the promote->seed->re-derive round trip")
    ap.add_argument("mode", choices=("synthetic", "live"),
                    help="synthetic: two in-process fabrics, three arms; "
                         "live: read-only over real swarm boxes")
    ap.add_argument("path", nargs="?", default=None,
                    help="live: swarm root or one box (default .runs/swarm); "
                         "synthetic: scratch workdir (default: a temp dir)")
    args = ap.parse_args(argv)
    if args.mode == "live":
        return live_report(args.path or DEFAULT_SWARM)
    if args.path:
        code, _ = synthetic_report(args.path)
        return code
    import tempfile
    with tempfile.TemporaryDirectory(prefix="bracket_rt_") as tmp:
        code, _ = synthetic_report(tmp)
        return code


if __name__ == "__main__":
    sys.exit(main())
