"""C33 STEP 1: every action carries a bet — the iced pricing spine, consumer-less, on the fabric.

⭐ WHY. Nothing re-clears because nothing is priced: the anti-hardening mechanism at per-action
granularity, and the room chain's admission substrate. The spine was proven on the iced branch
(nine lifecycles); its three paid-for laws are baked in from commit one. IN THIS STEP THE BETS
DRIVE NOTHING — containment is byte-identity.

THE CONTRACT (PREREG_MARKETPLACE_MERGE.md):
  * engines/egocentric/pricing.py — the iced marketplace core VERBATIM (sha-verified):
    Hypothesis, informative_salience (no-change frame → match fraction; hallucination
    penalised; normalised by n_changed), Marketplace.resolve (name tie-break, positive-to-
    drive);
  * engines/egocentric/betting.py — BetBook(fabric): per-action commit of a prediction family
    (paste + temporal-transform members) and settle against the EXECUTED action's next frame;
    LAWS: committed≠executed → VOID (nothing priced, transition recorded under executed);
    family-best recorded (never below the paste alone); settlement records to collective
    "settlements" topic with LINEAGE fields (agent, game, level, action, members, best, seq) —
    ρ_deriv needs lineage from birth; a per-episode in-memory record keeps volume sane (one
    fabric line per settle, compact).
  * loop wiring: commit at choice time, settle in the result path, inside the existing EGO
    try/except discipline; **NO CONSUMER**: bet scores must not be read by _act/_think or the
    pre-empt block in this step.

Run pre-build: these failed (modules absent).
"""
from __future__ import annotations
import os, sys
import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engines.egocentric.fabric import KnowledgeFabric


def _mods():
    try:
        from engines.egocentric import pricing, betting  # noqa: F401
    except Exception as e:
        pytest.fail("pricing/betting missing (%s) — the merge has not landed" % e)
    from engines.egocentric import pricing as P
    from engines.egocentric.betting import BetBook as B
    return P, B


class TestThePricingCore:

    def test_no_change_frame_scores_match_fraction(self):
        P, _ = _mods()
        before = np.zeros((4, 4), dtype=int)
        assert P.informative_salience(before, before.copy(), before.copy()) == 1.0

    def test_no_change_predictor_scores_zero_on_a_changed_frame(self):
        P, _ = _mods()
        before = np.zeros((4, 4), dtype=int)
        after = before.copy(); after[1, 1] = 5
        assert P.informative_salience(before, before.copy(), after) == 0.0

    def test_hallucination_is_penalised(self):
        P, _ = _mods()
        before = np.zeros((4, 4), dtype=int)
        after = before.copy(); after[1, 1] = 5
        pred = before.copy(); pred[1, 1] = 5; pred[2, 2] = 7   # right + invented
        assert P.informative_salience(before, pred, after) == 0.0  # (1-1)/1


class TestTheLaws:

    def _book(self, tmp_path):
        _, B = _mods()
        return B(KnowledgeFabric(str(tmp_path / "f"), agent_id="a", kin_key="v4"),
                 agent_id="a", game="g1")

    def test_a_counterfactual_is_never_priced(self, tmp_path):
        b = self._book(tmp_path)
        before = np.zeros((4, 4), dtype=int)
        after = before.copy(); after[1, 1] = 5
        b.commit(action=6, before=before, paste=before.copy(), transform=None)
        out = b.settle(post=after, executed_action=1)
        assert out is None or out.get("void"), "committed 6, executed 1 — VOID, nothing priced"
        assert b.records.get(6) in (None, []), "a voided bet must leave no score"

    def test_family_best_never_below_the_paste(self, tmp_path):
        b = self._book(tmp_path)
        before = np.zeros((4, 4), dtype=int)
        after = before.copy()                                   # static frame
        bad_transform = before.copy(); bad_transform[2, 2] = 9  # hallucinates
        b.commit(action=6, before=before, paste=before.copy(), transform=bad_transform)
        out = b.settle(post=after, executed_action=6)
        assert out["best"] == 1.0, "the paste's static 1.0 must survive a hallucinating sibling"

    def test_settlements_land_in_the_fabric_with_lineage(self, tmp_path):
        b = self._book(tmp_path)
        before = np.zeros((4, 4), dtype=int)
        after = before.copy(); after[1, 1] = 5
        b.commit(action=6, before=before, paste=before.copy(), transform=None)
        b.settle(post=after, executed_action=6)
        recs = b.fabric.query("collective", "settlements")
        assert recs, "no settlement record — the ledger the replay test needs is empty"
        r = recs[-1]
        for field in ("agent", "game", "action", "best", "nontrivial"):
            assert field in r, "settlement lacks lineage/debasement field %r" % field
        assert r["nontrivial"] is True

    def test_the_debasement_field_marks_trivial_settles(self, tmp_path):
        b = self._book(tmp_path)
        before = np.zeros((4, 4), dtype=int)
        b.commit(action=6, before=before, paste=before.copy(), transform=None)
        b.settle(post=before.copy(), executed_action=6)         # nothing changed
        assert b.fabric.query("collective", "settlements")[-1]["nontrivial"] is False


class TestTheWiring:

    def _src(self):
        return open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()

    def test_commit_and_settle_are_wired(self):
        src = self._src()
        assert "BetBook" in src or "_bet_book" in src, "no bet wiring (starvation)"
        assert ".settle(" in src

    def test_no_consumer_in_this_step(self):
        """⭐ THE STEP'S CONTAINMENT PROPERTY. Bets drive NOTHING: the decision paths must not
        read bet scores."""
        src = self._src()
        for fname in ("def _think", "def _act"):
            i = src.find(fname)
            if i == -1:
                continue
            j = src.find("\n    def ", i + 10)
            body = src[i:j if j != -1 else len(src)]
            for name in ("_bet_book", "BetBook", ".records"):
                assert name not in body, (
                    "%s reads the bet book — this step is consumer-less by prereg; the wheel "
                    "rule decides consumers later" % fname)
