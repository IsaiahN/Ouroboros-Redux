"""B12/B13 GATE: THE TRIANGULATION CONSUMER + SIGMA AT MINT TIME (BUILD_PROGRAM_2 W3).

⭐ WHY (C33 §14-16; CK_LEDGER retrieval law). The import queue's consumer is
SIGNATURE-FIRST RECOGNITION, not candidate-first verification: σ(R) is computed inside
the home frame, candidate-blind, PERSISTED before any match attempt; atoms carry their
prediction-signature from mint time; match = signature equality — one pass, no
application loop. The three conditions become seq-provable from append-only ordering:
① priority (σ's seq precedes the match), ② prior existence (the atom's mint seq
precedes the match), ③ independence. On miss the consumer is a LOOP, not a lookup:
near-misses name WHICH invariant to sharpen, ONE redescription retry fires, and the
give-up is an axis-tagged DEFEASIBLE not-found (the Chaitin rule: reopened when new
atoms touch the axis). KIN-ECHO LAW: echo/reputation bookkeeping excludes or
down-weights candidates whose source lineage == consuming lineage.

Run pre-build: these failed (engines.egocentric.consumer absent).
"""
from __future__ import annotations

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric import consumer
from engines.egocentric.effects import Gamma, learn_effect
from engines.egocentric.fabric import KnowledgeFabric
from engines.egocentric.mint import MDLMint

# ── fixtures: synthetic frames and a two-fabric (home + seed) setup ───────────

def _recolour(n=5, cells=((2, 2),), src=2, dst=3):
    """A before/after pair: `cells` recoloured src -> dst on an n x n board of src."""
    b = np.full((n, n), src, dtype=int)
    a = b.copy()
    for r, c in cells:
        a[r, c] = dst
    return b, a


def _mint_into(root, game, cells=((2, 2),), src=2, dst=3, agent_id="agentB"):
    """Mint one atom into a fresh fabric at `root` via the REAL mint; return the fabric."""
    f = KnowledgeFabric(str(root), agent_id=agent_id, kin_key="kinB")
    b, a = _recolour(cells=cells, src=src, dst=dst)
    v = MDLMint(Gamma(f)).consider(b, 1, a, game, 1)
    assert v["verdict"] == "mint", "fixture mint failed: %r" % (v,)
    return f


def _home(tmp_path, seeds, name="home"):
    return KnowledgeFabric(str(tmp_path / name), seeds=[str(s) for s in seeds],
                           agent_id="agentA", kin_key="kinA")


def _enqueue(fabric, before, after, slot="WORKSPACE", residual=1.0):
    """One residual record on the HOME import queue (rich shape: patches included)."""
    return fabric.append("collective", "import_queue", {
        "slot": slot, "residual": float(residual),
        "before": [[int(v) for v in row] for row in np.asarray(before)],
        "after": [[int(v) for v in row] for row in np.asarray(after)],
    })


# ── B13: sigma at mint time ───────────────────────────────────────────────────

class TestSigmaAtMint:

    def test_minted_atom_record_carries_sigma(self, tmp_path):
        f = _mint_into(tmp_path / "src", "g_src")
        recs = f.query("collective", "atoms")
        assert len(recs) == 1
        sig = recs[0]["atom"].get("sigma")
        assert isinstance(sig, dict), "minted atom carries no sigma"
        assert sig["bbox"] == "cell"
        assert sig["changed"] == "1"
        assert sig["colour_delta"] == [[2, 3]]
        assert sig["conserved"] is False
        assert sig["arity"] == 2

    def test_existing_record_fields_unchanged(self, tmp_path):
        f = _mint_into(tmp_path / "src", "g_src")
        rec = f.query("collective", "atoms")[0]
        assert set(rec) >= {"id", "type", "game", "level", "atom", "seq"}
        atom = rec["atom"]
        assert atom["kind"] == "EFFECT" and atom["key"].startswith("eff-")
        assert atom["changed"] == 1

    def test_mint_sigma_equals_describe_vocabulary(self, tmp_path):
        """One vocabulary for holes and atoms (the retrieval law): the mint-time sigma
        equals the consumer's candidate-blind description of the same event."""
        f = _mint_into(tmp_path / "src", "g_src")
        b, a = _recolour()
        sig = consumer.describe({"slot": "WORKSPACE", "residual": 1.0,
                                 "before": b.tolist(), "after": a.tolist()})
        minted = f.query("collective", "atoms")[0]["atom"]["sigma"]
        for k in consumer.INVARIANTS:
            assert sig[k] == minted[k], "vocabulary split on %r" % (k,)


# ── B12: describe is candidate-blind ─────────────────────────────────────────

class TestDescribe:

    def test_full_sigma_from_patches(self):
        b, a = _recolour(cells=((1, 1), (1, 2), (1, 3)))
        sig = consumer.describe({"slot": "WORKSPACE", "residual": 3.0,
                                 "before": b.tolist(), "after": a.tolist()})
        assert sig["slot"] == "WORKSPACE"
        assert sig["mag"] == "medium"
        assert sig["bbox"] == "row"
        assert sig["changed"] == "2-4"
        assert sig["colour_delta"] == [[2, 3]]
        assert sig["conserved"] is False
        assert sig["arity"] == 2

    def test_conservation_true_for_a_swap(self):
        b = np.array([[1, 2], [3, 4]])
        a = np.array([[2, 1], [3, 4]])
        sig = consumer.sigma_of(b, a)
        assert sig["conserved"] is True

    def test_patchless_record_degrades_never_crashes(self):
        sig = consumer.describe({"slot": "WORKSPACE", "residual": 12.0})
        assert sig["slot"] == "WORKSPACE" and sig["mag"] == "large"
        assert "bbox" not in sig and "colour_delta" not in sig

    def test_sigma_is_json_native(self):
        import json
        b, a = _recolour()
        json.dumps(consumer.sigma_of(b, a, slot="S", residual=1.0))


# ── B12: consume — hit, three conditions, priority persisted ─────────────────

class TestTriangulationHit:

    def test_cross_fabric_hit_writes_candidate(self, tmp_path):
        src = _mint_into(tmp_path / "src", "g_src")
        home = _home(tmp_path, [src.root])
        b, a = _recolour()
        _enqueue(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["drained"] == 1 and rep["candidates"] == 1
        cands = consumer.candidates(home, "g_home", 1)
        assert len(cands) == 1
        cand = cands[0]
        minted = src.query("collective", "atoms")[0]
        assert cand["atom"]["key"] == minted["atom"]["key"], "atom not copied"
        assert cand["source_game"] == "g_src", "cross-game provenance lost"
        assert cand["source_seq"] == minted["seq"]
        assert cand["sigma"]["bbox"] == "cell"

    def test_three_conditions_seq_provable(self, tmp_path):
        src = _mint_into(tmp_path / "src", "g_src")
        home = _home(tmp_path, [src.root])
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        tc = consumer.candidates(home, "g_home", 1)[0]["three_conditions"]
        assert tc["priority_seq"] < tc["match_seq"], "sigma did not precede the match"
        assert tc["atom_mint_seq"] < tc["match_seq"], "the atom did not precede the match"

    def test_sigma_persisted_to_processing_entry_before_match(self, tmp_path):
        """Condition ① is on disk: a kind=sigma processing entry whose seq precedes
        the consumed marker's, both in the home queue stream."""
        src = _mint_into(tmp_path / "src", "g_src")
        home = _home(tmp_path, [src.root])
        b, a = _recolour()
        raw = _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        rows = KnowledgeFabric(home.root, agent_id="agentA",
                               kin_key="kinA").query("collective", "import_queue")
        sig = [r for r in rows if r.get("kind") == "sigma"
               and r.get("src_seq") == raw["seq"]]
        done = [r for r in rows if r.get("kind") == "consumed"
                and r.get("src_seq") == raw["seq"]]
        assert len(sig) == 1 and len(done) == 1
        assert sig[0]["seq"] < done[0]["seq"]
        assert sig[0]["sigma"]["bbox"] == "cell"

    def test_consumed_item_is_not_redrained(self, tmp_path):
        src = _mint_into(tmp_path / "src", "g_src")
        home = _home(tmp_path, [src.root])
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        rep2 = consumer.consume(home, "g_home", 1, 8)
        assert rep2["drained"] == 0 and rep2["candidates"] == 0
        assert len(consumer.candidates(home, "g_home", 1)) == 1

    def test_budget_drains_oldest_first_under_the_off_arm(self, tmp_path,
                                                          monkeypatch):
        """DISPOSITION 2026-08-17 (THE_LADDER "NO PERMANENT RED", rule 1): this
        test was `test_budget_drains_oldest_first` and it no longer tested what
        it named -- PREREG_DRAIN_ORIGIN.md §A replaced consume()'s FIFO agenda
        with the bounded RANKED drain. FIXED TO CURRENT REALITY rather than left
        red: oldest-first is now the OFF-ARM's contract (DRAIN_RANKED=0), and it
        is asserted as such. The ranked arm's own ordering is owned by
        tests/gate/test_ranked_drain.py."""
        monkeypatch.setenv("DRAIN_RANKED", "0")
        home = _home(tmp_path, [])
        pairs = [_recolour(cells=((i, i),)) for i in range(3)]
        seqs = [_enqueue(home, b, a)["seq"] for b, a in pairs]
        rep = consumer.consume(home, "g_home", 1, 2)
        assert rep["drained"] == 2
        left = consumer.pending(home)
        assert [r["seq"] for r in left] == [seqs[2]], "not oldest-first"

    def test_budget_drains_newest_first_when_ranked(self, tmp_path, monkeypatch):
        """The same fixture under the shipped default: three equally-described
        records with no residual tie-break fall through to RECENCY, so the
        OLDEST is the one left standing -- the exact inversion of the off-arm."""
        monkeypatch.delenv("DRAIN_RANKED", raising=False)
        home = _home(tmp_path, [])
        pairs = [_recolour(cells=((i, i),)) for i in range(3)]
        seqs = [_enqueue(home, b, a)["seq"] for b, a in pairs]
        rep = consumer.consume(home, "g_home", 1, 2)
        assert rep["drained"] == 2
        left = consumer.pending(home)
        assert [r["seq"] for r in left] == [seqs[0]]


# ── B12: near-miss naming + the redescription loop ───────────────────────────

class TestRedescriptionLoop:

    def test_near_miss_names_the_failing_invariant(self, tmp_path):
        # source atom: 1-cell 2->3; residual: 1-cell 2->7 -- colour_delta alone fails.
        src = _mint_into(tmp_path / "src", "g_src", dst=3)
        home = _home(tmp_path, [src.root])
        b, a = _recolour(dst=7)
        _enqueue(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["candidates"] == 0 and rep["not_found"] == 1
        nf = consumer.open_not_found(home)
        assert len(nf) == 1
        assert nf[0]["axis"] == "colour_delta"
        assert [m["failed"] for m in nf[0]["near_misses"]] == ["colour_delta"]

    def test_retry_fires_once_then_defeasible_not_found(self, tmp_path):
        src = _mint_into(tmp_path / "src", "g_src", dst=3)
        home = _home(tmp_path, [src.root])
        b, a = _recolour(dst=7)
        _enqueue(home, b, a)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["retried"] == 1, "the redescription retry must fire exactly once"
        assert rep["not_found"] == 1

    def test_sharpening_the_named_axis_recovers_the_hit(self, tmp_path):
        # source atom: TWO cells 2->3 (changed class "2-4"); residual: FIVE cells 2->3
        # in a row (changed class "5-16"). Everything else agrees -- the near-miss
        # names "changed"; coarsening that one axis makes the match fire.
        src = _mint_into(tmp_path / "src", "g_src", cells=((1, 1), (1, 2)))
        home = _home(tmp_path, [src.root])
        b, a = _recolour(n=7, cells=tuple((1, c) for c in range(1, 6)))
        _enqueue(home, b, a, residual=5.0)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["retried"] == 1 and rep["candidates"] == 1
        cand = consumer.candidates(home, "g_home", 1)[0]
        assert cand["redescribed_axis"] == "changed"
        assert [m["failed"] for m in cand["near_misses"]] == ["changed"]

    def test_not_found_reopens_when_a_new_atom_touches_the_axis(self, tmp_path):
        # No atoms anywhere -> defeasible not-found. Then the sibling mints a
        # matching atom; the next consume reopens the item and lands the candidate
        # with the ORIGINAL priority_seq (the Chaitin rule with its re-look trigger).
        srcroot = tmp_path / "src"
        os.makedirs(str(srcroot))
        home = _home(tmp_path, [srcroot])
        b, a = _recolour()
        raw = _enqueue(home, b, a)
        rep1 = consumer.consume(home, "g_home", 1, 8)
        assert rep1["not_found"] == 1
        nf = consumer.open_not_found(home)
        assert len(nf) == 1 and nf[0]["axis"] in ("any", "vocabulary")
        prio = nf[0]["priority_seq"]
        _mint_into(srcroot, "g_src")                    # the axis is touched
        rep2 = consumer.consume(home, "g_home", 1, 8)
        assert rep2["reopened"] == 1 and rep2["candidates"] == 1
        assert consumer.open_not_found(home) == []
        cand = consumer.candidates(home, "g_home", 1)[0]
        assert cand["src_seq"] == raw["seq"]
        assert cand["three_conditions"]["priority_seq"] == prio

    def test_no_reopen_without_new_atoms(self, tmp_path):
        home = _home(tmp_path, [])
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        rep = consumer.consume(home, "g_home", 1, 8)
        assert rep["reopened"] == 0, "an empty search must not spin on the same silence"
        assert len(consumer.open_not_found(home)) == 1, "the item stays open (Chaitin)"


# ── B12: the KIN-ECHO LAW ────────────────────────────────────────────────────

def _sigma_atom_record(fabric, game, key, agent=None, kin=None, idea_id=None,
                       src=2, dst=3):
    """Append one atom record carrying sigma + lineage fields directly."""
    b, a = _recolour(src=src, dst=dst)
    atom = learn_effect(b, 1, a)
    atom["key"] = key
    atom["sigma"] = consumer.sigma_of(b, a)
    rec = {"id": key + ":0", "type": "structural", "game": str(game), "level": 1,
           "atom": atom}
    if agent is not None:
        rec["agent"] = agent
    if kin is not None:
        rec["kin"] = kin
    if idea_id is not None:
        rec["idea_id"] = idea_id
    return fabric.append("collective", "atoms", rec)


class TestKinEchoLaw:

    def test_same_lineage_candidate_is_downweighted(self, tmp_path):
        home = _home(tmp_path, [])
        _sigma_atom_record(home, "g_kin", "eff-kin", agent="agentA", idea_id="idkin")
        _sigma_atom_record(home, "g_other", "eff-oth", agent="agentB", idea_id="idoth")
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        cand = consumer.candidates(home, "g_home", 1)[0]
        assert cand["atom"]["key"] == "eff-oth", "kin echo outranked a stranger's atom"
        assert cand["kin_echo"] is False

    def test_kin_only_hit_flagged_and_not_echoed(self, tmp_path):
        home = _home(tmp_path, [])
        _sigma_atom_record(home, "g_kin", "eff-kin", agent="agentA", idea_id="idkin")
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        cand = consumer.candidates(home, "g_home", 1)[0]
        assert cand["kin_echo"] is True
        evs = home.query("collective", "idea_events")
        assert evs == [], "a self/kin echo was paid -- status minted from self-dealing"

    def test_cross_lineage_hit_pays_the_origin_author(self, tmp_path):
        home = _home(tmp_path, [])
        _sigma_atom_record(home, "g_other", "eff-oth", agent="agentB", idea_id="idoth")
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        evs = home.query("collective", "idea_events")
        assert [(e["ev"], e["id"]) for e in evs] == [("echo", "idoth")]

    def test_kin_key_lineage_counts_as_kin(self, tmp_path):
        home = _home(tmp_path, [])
        _sigma_atom_record(home, "g_kin", "eff-kin", kin="kinA", idea_id="idkin")
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        assert consumer.candidates(home, "g_home", 1)[0]["kin_echo"] is True
        assert home.query("collective", "idea_events") == []


# ── B12: seed_imports — the W1 interface ─────────────────────────────────────

class TestSeedImports:

    def _consumed_home(self, tmp_path):
        src = _mint_into(tmp_path / "src", "g_src")
        home = _home(tmp_path, [src.root])
        b, a = _recolour()
        _enqueue(home, b, a)
        consumer.consume(home, "g_home", 1, 8)
        return home

    def test_exact_signature_and_imported_flag(self, tmp_path):
        home = self._consumed_home(tmp_path)
        gamma = Gamma(home)
        n = consumer.seed_imports(gamma, home, "g_home", 1)
        assert n == 1
        local = KnowledgeFabric(home.root, agent_id="agentA",
                                kin_key="kinA").query("collective", "atoms")
        imported = [r for r in local if (r.get("atom") or {}).get("imported")]
        assert len(imported) == 1
        assert imported[0]["atom"]["imported"] is True
        assert imported[0]["game"] == "g_home"

    def test_second_call_is_idempotent(self, tmp_path):
        home = self._consumed_home(tmp_path)
        gamma = Gamma(home)
        assert consumer.seed_imports(gamma, home, "g_home", 1) == 1
        assert consumer.seed_imports(gamma, home, "g_home", 1) == 0

    def test_level_scoped(self, tmp_path):
        home = self._consumed_home(tmp_path)
        gamma = Gamma(home)
        assert consumer.seed_imports(gamma, home, "g_home", 2) == 0
        assert consumer.seed_imports(gamma, home, "g_other", 1) == 0
