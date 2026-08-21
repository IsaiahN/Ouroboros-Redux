"""COMPOSER STAGE 4 -- THE SETTLEMENT WIRE (PREREG_COMPOSER_STAGE4_SETTLEMENT.md).

The build under test (engines/egocentric/composer.py's stage-4 section +
the cognitive_loop seams _w3d_drive / _w3d_continue / _w3d_settle):
  ONE transition, CANDIDATE -> SETTLED, written ONLY by composer.live_settle
  after composer.settle_verdict compared the chain's predicted final frame
  against the LIVE frame the driven chain ended on. A CANDIDATE composite
  DRIVES under the planner's own gates (verified x2 per part, site, veto);
  driving increments the SAME g7 counter the plan_to_identity path
  increments. Failure routes through scheduler.route_abort: world-moved
  (candidate intact, no penalty) vs plan-wrong (ctx_conflict on the
  MISPREDICTING component only, via MDLMint._reinstate). Nothing deleted.

The falsifiers, as gated here:
  F1  live-frame-only settle: a simulation-perfect chain composes and is
      NOT settled (no field; the simulated path never reaches the writer --
      structurally asserted); the same chain against a constructed LIVE
      outcome that matches settles; against one that diverges it does not.
  F2  unsettled never GROUND: citation_allowed refuses an unsettled
      composite as GROUND and accepts it in a BET; the settle flips exactly
      GROUND (is_citable both ways; a non-composite is never citable).
  F3  failure routed both ways through the loop seams: world-moved (the
      live key moved under the chain) -> candidate intact, no ctx_conflict
      anywhere, scheduler ledger empty; plan-wrong (state as predicted,
      the prediction failed) -> ctx_conflict on the mispredicting component
      ONLY (mid-chain: the body part; final: the Gamma part), tightened
      from context_full where a discriminator exists, composite unsettled.
  F4  g7 increments exactly on the drive: compose-only -> unchanged; an
      un-verified composite (shadow) -> unchanged; driven -> +1, on the SAME
      dict object the planner path increments (identity + source).
  R4  constructed drive->settle and drive->fail sequences through the real
      seams reproduce the expected records exactly (PLAN narration modes,
      the settled envelope, the conflict record).
  KNOWN-NEGATIVES: a settle with no drive record is refused; a second
      settle on a settled composite is idempotent (nothing appended).
  STRUCTURAL: no path writes the settled field except live_settle, and
      live_settle calls the live comparison; the loop seams never append to
      the atoms stream themselves; _simulate knows nothing of settling.

Seeded with a FIXED CONSTANT (the build date), never a clock.
"""
from __future__ import annotations

import ast
import os
import sys
from types import SimpleNamespace

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cognitive_loop as cl  # noqa: E402
from engines.egocentric import composer as C  # noqa: E402
from engines.egocentric import effects as E  # noqa: E402
from engines.egocentric import enables as EN  # noqa: E402
from engines.egocentric import narration as na  # noqa: E402
from engines.egocentric import scheduler as sch  # noqa: E402
from engines.egocentric.fabric import KnowledgeFabric  # noqa: E402
from engines.egocentric.mint import MDLMint  # noqa: E402

SEED = 20260821  # fixed constant (the build date) -- deterministic forever

DELTAS4 = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


# ── constructions (stage 3's world, driven) ───────────────────────────────────

def _gamma(tmp_path, name):
    return E.Gamma(KnowledgeFabric(str(tmp_path / name), agent_id="a",
                                   kin_key="v4"))


def _atom(ctx, out, key, action=6, ttype=None, params=None):
    ctx_l = [[int(v) for v in row] for row in ctx]
    out_l = [[int(v) for v in row] for row in out]
    a = {"kind": "EFFECT", "arity": 2, "key": key, "action": action,
         "context": ctx_l,
         "transform": {"before": ctx_l, "after": out_l},
         "changed": int((np.asarray(ctx) != np.asarray(out)).sum())}
    if ttype:
        a["ttype"] = ttype
        a["params"] = dict(params or {})
    return a


def _click_atom(ctx, out, key, dr, dc):
    a = _atom(ctx, out, key)
    a[EN.ACT_OFFSET_FIELD] = {"v": EN.ACT_OFFSET_VERSION,
                              "dr": int(dr), "dc": int(dc)}
    return a


def _mv_right(key="mv-right"):
    return _atom([[7, 0]], [[0, 7]], key, action=4, ttype="TRANSLATE",
                 params={"dx": 0, "dy": 1, "fill": 0})


def _world(tmp_path, name):
    """Avatar 7 at (0,0); button 3 at (2,4); B (writes 9) anchored on the
    button, act cell (0,4). WANT = 9 at (2,4). Chain: 4 right-steps + B."""
    f = np.zeros((3, 6), dtype=int)
    f[0, 0] = 7
    f[2, 4] = 3
    g = _gamma(tmp_path, name)
    ids = {"mv": g.add(_mv_right(), "g1", 1),
           "B": g.add(_click_atom([[3]], [[9]], "click-b", -2, 0), "g1", 1)}
    return f, g, ids, [(2, 4, 9)]


def _records(g, aid):
    return [r for r in g.fabric.query("collective", g.TOPIC)
            if r.get("id") == aid]


def _composites(g):
    return [r for r in g.fabric.query("collective", g.TOPIC)
            if (r.get("atom") or {}).get("kind") == "COMPOSITE"]


def _ns(tmp_path, name, g, verified=None):
    """The loop namespace at the stage-4 seams: enough real state for
    _w3c_compose / _w3d_drive / _w3d_continue / _w3d_settle / _narr_bet
    to run the LOOP'S OWN code paths (stage 3's namespace + the mint, the
    perceiver's numpy adapter, the chain slot)."""
    return SimpleNamespace(
        _ego_fabric=KnowledgeFabric(str(tmp_path / name), agent_id="a",
                                    kin_key="v4"),
        _game_id="g1", _actions_taken=0, _ego_agent_id="a", _ego_level=0,
        _w2b_sched=sch.PlannerScheduler(), _w2b_narr=None, _w2b_driven=None,
        _w2b_key=None, _w3d_chain=None,
        _w4c_counters={"mint_passed": 0}, _narr_import_n=0,
        _narration=None, _narr_slots=None,
        _atom_verified=dict(verified or {}),
        _residual_router=None,
        _plan_gate={"g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0, "g6": 0,
                    "g7": 0, "shadow": 0, "drive": 0, "cycles": 1},
        _narr_settle=None, _narr_mint=None, _prev_frame=None,
        _ego_seeded={}, _ego_seeded_clicks={}, _gamma=g, _mdl_mint=MDLMint(g),
        _ego_prev_centroid=(0, 0), _ego_frontier_book=None,
        _ego_harvest_cache=None,
        _perceiver=SimpleNamespace(_to_numpy=np.asarray))


def _cf(conf=0.0, speed="explore"):
    return SimpleNamespace(action_confidence=float(conf), rung_name="",
                           action_speed=str(speed))


def _plan_records(ns):
    return [r for r in ns._ego_fabric.query("personal", na.TOPIC)
            if r["point"] == na.PLAN]


def _compose(ns, f, want):
    """Engage the gate (the plan-time key), then compose the two-shelf
    chain with the CONSTRUCTED deltas (the loop seam _w3c_compose reads the
    action book, which a constructed game does not have -- the no-movement
    path through _w3c_compose is exercised in F4/R4). Stages the same
    narration _w3c_compose would; returns the attempt's result."""
    assert cl._w2b_engage(ns, f, _cf(0.0)) is True, "construction: gate opens"
    res = C.compose_attempt(want, f, ns._gamma, (0, 0), DELTAS4, set(), "g1", 1)
    assert res["reason"] == C.COMPOSED, (
        "construction: the two-shelf world must compose; got %r" % (res,))
    ns._w2b_narr = ("composed", res["composite"],
                    {"settled": False, "driven": False})
    return res


def _one_step_world(tmp_path, name):
    """Stage 3's no-movement construction: B (writes 9) anchored at (0,0);
    the chain is [B] alone and composes through the loop's own seam."""
    f = np.array([[3, 0], [0, 1]], dtype=int)
    g = _gamma(tmp_path, name)
    bid = g.add(_atom([[3]], [[9]], "eff-b"), "g1", 1)
    return f, g, bid


def _drive(ns, f, res):
    step = cl._w3d_drive(ns, f, res)
    cl._narr_bet(ns, step[0] if step else 6, _cf(0.0), {})
    return step


def _land(ns, pre, post, level_changed=False):
    """One record_result at the stage-4 seam: the loop stored `pre` as
    _prev_frame at the end of cycle; `post` is the LIVE observed frame."""
    ns._prev_frame = np.asarray(pre)
    cl._w3d_settle(ns, np.asarray(post), level_changed)
    cl._w2b_abort(ns, bool((np.asarray(pre) != np.asarray(post)).any()),
                  level_changed)


def _cont(ns, frame):
    ns._actions_taken += 1
    step = cl._w3d_continue(ns, frame)
    if step is not None:
        cl._narr_bet(ns, step[0], _cf(0.0), {})
    return step


# ── F1 · live-frame-only settle ───────────────────────────────────────────────

class TestF1LiveFrameOnlySettle:

    def test_a_simulation_perfect_chain_does_not_settle(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f1a")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        assert res["reason"] == C.COMPOSED and res["verified"] >= 1
        assert len(res["frames"]) == len(res["chain"]) == 5, (
            "construction: one predicted frame per part")
        rec = C.composite_record(g, res["composite"])
        assert rec is not None and C.SETTLED_FIELD not in rec, (
            "F1 FALSIFIED: the simulation settled the composite")
        assert not C.is_citable(rec)
        assert len(_records(g, res["composite"])) == 1, (
            "exactly the mint record: nothing superseded it")

    def test_the_same_chain_settles_on_a_matching_live_outcome(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f1b")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        drive = C.drive_record(res)
        assert drive is not None
        # the constructed LIVE outcome: the avatar walked to (0,4), the
        # button turned 9 -- observed, not simulated
        live = np.zeros((3, 6), dtype=int)
        live[0, 4] = 7
        live[2, 4] = 9
        out = C.live_settle(g, drive, live)
        assert out["settled"] is True and out["written"] is True, (
            "F1 FALSIFIED: a matching live outcome did not settle -- %r" % (out,))
        assert out["reason"] == C.S_SETTLED
        recs = _records(g, res["composite"])
        assert len(recs) == 2 and recs[-1][C.SETTLED_FIELD] is True, (
            "the settle must be a superseding append, same id")
        assert recs[0].get(C.SETTLED_FIELD) is None, (
            "the candidate record remains readable history, untouched")
        assert recs[-1]["atom"]["parts"] == res["chain"]
        assert C.is_citable(C.composite_record(g, res["composite"]))

    def test_a_diverging_live_outcome_does_not_settle(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f1c")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        drive = C.drive_record(res)
        live = np.zeros((3, 6), dtype=int)
        live[0, 4] = 7
        live[2, 4] = 3                          # the button did NOT turn
        out = C.live_settle(g, drive, live)
        assert out["settled"] is False and out["reason"] == C.S_DIVERGED
        assert out["component"] == ids["B"] and (2, 4) in out["diverged"], (
            "the mispredicting component must be named; got %r" % (out,))
        assert len(_records(g, res["composite"])) == 1, "nothing written"
        assert not C.is_citable(C.composite_record(g, res["composite"]))


# ── F2 · unsettled never GROUND ───────────────────────────────────────────────

class TestF2UnsettledNeverGround:

    def test_bet_allowed_ground_refused_then_the_settle_flips_ground(
            self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f2")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        rec = C.composite_record(g, res["composite"])
        assert C.citation_allowed(rec, C.ROLE_BET) is True, (
            "F2 FALSIFIED: an unsettled composite must be proposable in a BET")
        assert C.citation_allowed(rec, C.ROLE_GROUND) is False, (
            "F2 FALSIFIED: an unsettled composite stood as GROUND")
        assert C.is_citable(rec) is False
        live = np.zeros((3, 6), dtype=int)
        live[0, 4] = 7
        live[2, 4] = 9
        assert C.live_settle(g, C.drive_record(res), live)["settled"]
        rec2 = C.composite_record(g, res["composite"])
        assert C.is_citable(rec2) is True
        assert C.citation_allowed(rec2, C.ROLE_GROUND) is True, (
            "F2 FALSIFIED: the settle did not flip GROUND")
        assert C.citation_allowed(rec2, C.ROLE_BET) is True, (
            "the settle flips exactly GROUND; BET was already allowed")

    def test_non_composites_and_unknown_roles_are_never_citable(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f2b")
        eff = _records(g, ids["B"])[-1]
        assert C.is_citable(eff) is False
        assert C.citation_allowed(eff, C.ROLE_GROUND) is False
        assert C.citation_allowed(eff, C.ROLE_BET) is False
        assert C.is_citable(None) is False and C.is_citable({}) is False
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        rec = C.composite_record(g, res["composite"])
        assert C.citation_allowed(rec, "WHATEVER") is False
        forged = dict(rec)
        forged[C.SETTLED_FIELD] = "yes"          # only the boolean True counts
        assert C.is_citable(forged) is False


# ── F3 · failure routed both ways through the loop seams ──────────────────────

VERIFIED2 = {"mv-right:0": 2, "click-b:1": 2}


class TestF3FailureRoutedBothWays:

    def test_world_moved_leaves_the_candidate_intact_with_no_conflict(
            self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f3a")
        ns = _ns(tmp_path, "f3a_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want)
        step = _drive(ns, f, res)
        assert step == (4, None), "construction: the first part drives (right)"
        drive = ns._w3d_chain["drive"]
        _land(ns, f, drive["frames"][0])        # step 0 landed as predicted
        assert ns._w3d_chain["cursor"] == 1
        # the world moves under the chain before part 1: a new blob appears
        moved = drive["frames"][0].copy()
        moved[2, 0] = 5
        assert _cont(ns, moved) is None, (
            "F3 FALSIFIED: a part issued against a state the chain never bet on")
        assert ns._w3d_chain is None, "the chain is dropped"
        aborts = [r for r in _plan_records(ns) if r["mode"] == "abort"]
        assert len(aborts) == 1 and aborts[0]["gate"] == sch.ABORT_WORLD_MOVED, (
            "the world-moved route must be narrated; got %r" % (aborts,))
        assert aborts[0]["composite"] == res["composite"]
        assert aborts[0]["settled"] is False
        assert ns._w2b_sched.plan_wrong == {}, (
            "F3 FALSIFIED: world-moved penalised the chain's parts")
        for pid in (ids["mv"], ids["B"]):
            assert len(_records(g, pid)) == 1, (
                "F3 FALSIFIED: ctx_conflict fired on %s under world-moved" % pid)
        cand = C.composite_record(g, res["composite"])
        assert cand is not None and C.SETTLED_FIELD not in cand, (
            "the candidate stays a candidate, intact")
        assert len(_records(g, res["composite"])) == 1

    def test_plan_wrong_mid_chain_conflicts_the_body_part_only(self, tmp_path):
        """State as predicted, the move did nothing: plan-wrong on the
        body part (step 0) -- the Gamma part B is untouched."""
        f, g, ids, want = _world(tmp_path, "f3b")
        ns = _ns(tmp_path, "f3b_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want)
        assert _drive(ns, f, res) == (4, None)
        _land(ns, f, f)                         # the avatar did NOT move
        assert ns._w3d_chain is None
        aborts = [r for r in _plan_records(ns) if r["mode"] == "abort"]
        assert len(aborts) == 1 and aborts[0]["gate"] == sch.ABORT_PLAN_WRONG, (
            "F3 FALSIFIED: plan-wrong not routed; got %r" % (aborts,))
        assert aborts[0]["component"] == ids["mv"]
        assert ns._w2b_sched.plan_wrong == {ids["mv"]: 1}, (
            "the ledger records the mispredicting component only")
        mv = _records(g, ids["mv"])
        assert len(mv) == 2 and mv[-1].get("ctx_conflict") is True, (
            "F3 FALSIFIED: ctx_conflict did not fire on the mispredicting part")
        assert mv[-1]["id"] == ids["mv"] and mv[0].get("ctx_conflict") is None
        assert len(_records(g, ids["B"])) == 1, (
            "F3 FALSIFIED: ctx_conflict fired on a part that never mispredicted")
        assert not C.is_citable(C.composite_record(g, res["composite"]))

    def test_plan_wrong_at_the_settle_conflicts_the_gamma_part_only(
            self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f3c")
        ns = _ns(tmp_path, "f3c_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want)
        assert _drive(ns, f, res) == (4, None)
        drive = ns._w3d_chain["drive"]
        pre = f
        for i in range(4):                      # the four moves land exactly
            _land(ns, pre, drive["frames"][i])
            pre = drive["frames"][i]
            nxt = _cont(ns, pre)
            assert nxt is not None, "the chain must continue at step %d" % (i + 1)
        assert nxt == (6, {'x': 4, 'y': 0}), (
            "the Gamma part clicks its act cell; got %r" % (nxt,))
        bad = drive["frames"][4].copy()
        bad[2, 4] = 3                           # the button did not turn
        _land(ns, pre, bad)
        aborts = [r for r in _plan_records(ns) if r["mode"] == "abort"]
        assert len(aborts) == 1 and aborts[0]["gate"] == sch.ABORT_PLAN_WRONG
        assert aborts[0]["component"] == ids["B"]
        assert ns._w2b_sched.plan_wrong == {ids["B"]: 1}
        assert _records(g, ids["B"])[-1].get("ctx_conflict") is True
        assert len(_records(g, ids["mv"])) == 1, (
            "F3 FALSIFIED: the body part was conflicted for B's misprediction")
        assert not C.is_citable(C.composite_record(g, res["composite"]))
        assert len(_records(g, res["composite"])) == 1, "never settled"

    def test_plan_wrong_tightens_the_component_from_context_full(
            self, tmp_path):
        """The mint's reinstate path run for real: the component's context
        is DONT_CARE where context_full is specific and the live pre-frame
        differs -> that cell is reinstated and PINNED, ctx_conflict recorded,
        context_full untouched."""
        g = _gamma(tmp_path, "f3d")
        atom = _atom([[3, E.DONT_CARE]], [[9, E.DONT_CARE]], "loose-b")
        atom["context_full"] = [[3, 0]]
        bid = g.add(atom, "g1", 1)
        pre = np.array([[3, 5]], dtype=int)     # full says 0 here; live says 5
        out = C.conflict_component(MDLMint(g), g, bid, pre)
        assert out["conflicted"] is True and out["tightened"] == 1, (
            "the discriminating cell must be reinstated; got %r" % (out,))
        rec = _records(g, bid)[-1]
        assert rec.get("ctx_conflict") is True
        assert rec["atom"]["context"] == [[3, 0]]
        assert rec["atom"]["ctx_conflict_cells"] == [[0, 1]]
        assert rec["atom"]["context_full"] == [[3, 0]], "Condition 2: untouched"


# ── F4 · g7 increments exactly on the drive, on THE existing counter ──────────

class TestF4G7Identity:

    def test_compose_only_leaves_g7_unchanged(self, tmp_path):
        f, g, bid = _one_step_world(tmp_path, "f4a")
        ns = _ns(tmp_path, "f4a_n", g)
        pg = ns._plan_gate
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True
        res = cl._w3c_compose(ns, f, [(0, 0, 9)])      # the loop's own seam
        assert res is not None and res["reason"] == C.COMPOSED
        assert res["chain"] == [bid]
        assert pg["g7"] == 0 and pg["drive"] == 0, (
            "F4 FALSIFIED: composing alone moved g7/drive")
        # STAGE 4.5: the record also states the avatar source -- this
        # namespace holds a centroid and no exact self-locus cell, so the
        # fallback token is exactly what must be stated.
        assert ns._w2b_narr == ("composed", res["composite"],
                                {"settled": False, "driven": False,
                                 "avatar": C.AVATAR_CENTROID}), (
            "the PLAN record must carry the unsettled state at the compose")
        cl._narr_bet(ns, 6, _cf(0.0), {})
        plans = _plan_records(ns)
        assert len(plans) == 1 and plans[0]["mode"] == "composed"
        assert plans[0]["settled"] is False and plans[0]["driven"] is False

    def test_an_unverified_composite_shadows_and_g7_is_unchanged(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f4b")
        ns = _ns(tmp_path, "f4b_n", g, verified={ids["mv"]: 2, ids["B"]: 1})
        res = _compose(ns, f, want)
        assert cl._w3d_drive(ns, f, res) is None, "below the salience bar"
        assert ns._plan_gate["g7"] == 0 and ns._plan_gate["shadow"] == 1
        assert ns._w3d_chain is None and ns._w2b_driven is None
        assert ns._w2b_narr[0] == "composed" and ns._w2b_narr[2]["driven"] is False

    def test_the_drive_increments_g7_on_the_planner_paths_dict(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "f4c")
        ns = _ns(tmp_path, "f4c_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        pg = ns._plan_gate                      # the object the planner path uses
        res = _compose(ns, f, want)
        assert cl._w3d_drive(ns, f, res) == (4, None)
        assert ns._plan_gate is pg, "F4 FALSIFIED: a replacement dict (parallel counter)"
        assert pg["g7"] == 1 and pg["drive"] == 1, (
            "F4 FALSIFIED: the drive must move g7 by exactly one; got %r" % (pg,))
        assert ns._w2b_driven == {"key": sch.state_key(f), "steps": [ids["mv"]],
                                  "composite": res["composite"], "step": 0}, (
            "the part rides the existing abort-router stash (key + steps)")

    def test_structural_one_g7_counter(self):
        """The planner path increments `_pg["g7"]` on `_pg = self._plan_gate`
        inside cycle; _w3d_drive increments `_pg["g7"]` on
        `_pg = loop._plan_gate`. No other g7 writer exists in the loop."""
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        writers = [ln for ln in src.splitlines()
                   if '_pg["g7"]' in ln and ("+= 1" in ln or "= int(" in ln)]
        assert len(writers) == 2, (
            "F4 FALSIFIED: expected exactly the planner's and the composite's "
            "g7 writer; found %r" % (writers,))
        i = src.index("def cycle(")
        cyc = src[i:src.find("\n    def ", i + 10)]
        assert "_pg = self._plan_gate" in cyc and '_pg["g7"] += 1' in cyc
        j = src.index("def _w3d_drive(")
        fn = src[j:src.find("\ndef ", j + 10)]
        assert "_pg = loop._plan_gate" in fn and '_pg["g7"]' in fn


# ── R4 · exact drive->settle and drive->fail sequences ───────────────────────

class TestR4ExactSequences:

    def _run(self, ns, f, res, final):
        assert _drive(ns, f, res) == (4, None)
        drive = ns._w3d_chain["drive"]
        pre = f
        for i in range(4):
            _land(ns, pre, drive["frames"][i])
            pre = drive["frames"][i]
            assert _cont(ns, pre) is not None
        _land(ns, pre, final)
        return drive

    def test_drive_then_settle_reproduces_the_records(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "r4a")
        ns = _ns(tmp_path, "r4a_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want)
        live = np.zeros((3, 6), dtype=int)      # the constructed LIVE end state
        live[0, 4] = 7
        live[2, 4] = 9
        drive = self._run(ns, f, res, live)
        assert np.array_equal(drive["frames"][-1], live), "construction"
        assert ns._w3d_chain is None and ns._w2b_driven is None
        modes = [(r["mode"], r["gate"]) for r in _plan_records(ns)]
        cid = res["composite"]
        assert modes == [("composed", cid)] + [("composite-drive", cid)] * 4 + [
            ("settled", cid)], "R4 FALSIFIED: PLAN records %r" % (modes,)
        plans = _plan_records(ns)
        assert plans[0]["settled"] is False and plans[0]["driven"] is True
        assert [p["step"] for p in plans[1:5]] == [1, 2, 3, 4]
        assert plans[-1]["settled"] is True and plans[-1]["reason"] == C.S_SETTLED
        recs = _records(g, cid)
        assert len(recs) == 2 and recs[-1][C.SETTLED_FIELD] is True
        assert recs[-1]["settle"] == {"steps": 5, "cells": 6, "want": 1}, (
            "5 parts; cells (0,0..4) + (2,4) = 6 predicted cells; 1 WANT cell")
        assert C.is_citable(C.composite_record(g, cid))
        assert ns._w2b_sched.plan_wrong == {}
        assert ns._plan_gate["g7"] == 1 and ns._plan_gate["drive"] == 1
        for pid in (ids["mv"], ids["B"]):
            assert len(_records(g, pid)) == 1, "no part was touched"

    def test_drive_then_fail_reproduces_the_records(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "r4b")
        ns = _ns(tmp_path, "r4b_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want)
        bad = np.zeros((3, 6), dtype=int)
        bad[0, 4] = 7
        bad[2, 4] = 3                           # the click did nothing
        self._run(ns, f, res, bad)
        cid = res["composite"]
        modes = [(r["mode"], r["gate"]) for r in _plan_records(ns)]
        assert modes == [("composed", cid)] + [("composite-drive", cid)] * 4 + [
            ("abort", sch.ABORT_PLAN_WRONG)], "R4 FALSIFIED: %r" % (modes,)
        last = _plan_records(ns)[-1]
        assert last["composite"] == cid and last["component"] == ids["B"]
        assert last["settled"] is False
        assert last["conflict"]["conflicted"] is True
        assert len(_records(g, cid)) == 1, "unsettled: nothing superseded"
        assert _records(g, ids["B"])[-1].get("ctx_conflict") is True
        assert len(_records(g, ids["mv"])) == 1
        assert ns._w2b_sched.plan_wrong == {ids["B"]: 1}
        assert ns._plan_gate["g7"] == 1, "g7 counted the drive, not the outcome"

    def test_a_level_change_drops_the_chain_with_the_candidate_intact(
            self, tmp_path):
        f, g, ids, want = _world(tmp_path, "r4c")
        ns = _ns(tmp_path, "r4c_n", g, verified={ids["mv"]: 2, ids["B"]: 2})
        res = _compose(ns, f, want)
        assert _drive(ns, f, res) == (4, None)
        _land(ns, f, np.zeros((3, 6), dtype=int), level_changed=True)
        assert ns._w3d_chain is None
        aborts = [r for r in _plan_records(ns) if r["mode"] == "abort"]
        assert len(aborts) == 1 and aborts[0]["reason"] == "level-changed"
        assert ns._w2b_sched.plan_wrong == {}
        assert len(_records(g, res["composite"])) == 1
        for pid in (ids["mv"], ids["B"]):
            assert len(_records(g, pid)) == 1

    def test_one_step_chain_through_the_loops_own_compose_seam(self, tmp_path):
        """_w3c_compose -> _w3d_drive on the no-movement chain [B] where B
        carries NO act_offset. STAGE 4.5 (the seam read's silent #3): the
        composite is COMPOSE-ONLY -- the drive never synthesises a click
        site from the patch centre; it shadows with no-act-offset stated on
        the PLAN record, g7 untouched, no chain pending. (Before stage 4.5
        this test asserted the guessed site (0, 0) drove and settled.)"""
        f, g, bid = _one_step_world(tmp_path, "r4e")
        ns = _ns(tmp_path, "r4e_n", g, verified={bid: 2})
        assert cl._w2b_engage(ns, f, _cf(0.0)) is True
        res = cl._w3c_compose(ns, f, [(0, 0, 9)])
        assert res is not None and res["reason"] == C.COMPOSED
        step = _drive(ns, f, res)
        assert step is None, "R4 FALSIFIED: an offset-less part drove %r" % (step,)
        assert ns._plan_gate["g7"] == 0 and ns._plan_gate["shadow"] == 1
        assert ns._w3d_chain is None and ns._w2b_driven is None
        plans = _plan_records(ns)
        cid = res["composite"]
        assert [(r["mode"], r["gate"]) for r in plans] == [("composed", cid)]
        assert plans[0]["reason"] == C.NO_ACT_OFFSET and plans[0]["driven"] is False
        assert plans[0]["parts"] == [bid]
        assert not C.is_citable(C.composite_record(g, cid))

    def test_a_planner_stash_is_left_for_the_abort_router(self, tmp_path):
        """The seam consumes COMPOSITE stashes only: the planner's own
        (key + steps) passes through to _w2b_abort untouched."""
        f, g, ids, want = _world(tmp_path, "r4d")
        ns = _ns(tmp_path, "r4d_n", g)
        cl._w2b_engage(ns, f, _cf(0.0))
        cl._narr_bet(ns, 6, _cf(0.0), {})
        ns._w2b_driven = {"key": sch.state_key(f), "steps": ["atomA"]}
        ns._prev_frame = f.copy()
        cl._w3d_settle(ns, f.copy(), False)
        assert ns._w2b_driven == {"key": sch.state_key(f), "steps": ["atomA"]}
        cl._w2b_abort(ns, frame_changed=False, level_changed=False)
        assert ns._w2b_sched.plan_wrong == {"atomA": 1}


# ── known-negatives ───────────────────────────────────────────────────────────

class TestKnownNegatives:

    def test_a_settle_with_no_drive_record_is_refused(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "kn0")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        live = np.zeros((3, 6), dtype=int)
        live[0, 4] = 7
        live[2, 4] = 9
        for bad in (None, {}, {"chain": res["chain"]}, "drive"):
            out = C.live_settle(g, bad, live)
            assert out["settled"] is False and out["reason"] == C.S_NO_DRIVE
            assert out["written"] is False
        assert len(_records(g, res["composite"])) == 1
        ghost = dict(C.drive_record(res))
        ghost["composite"] = "cmp-ghost:99"
        out = C.live_settle(g, ghost, live)
        assert out["reason"] == C.S_NO_RECORD and out["written"] is False
        assert C.drive_record({"reason": C.R_UNVERIFIED}) is None
        assert C.drive_record(None) is None

    def test_a_second_settle_is_idempotent(self, tmp_path):
        f, g, ids, want = _world(tmp_path, "kn1")
        res = C.compose_attempt(want, f, g, (0, 0), DELTAS4, set(), "g1", 1)
        drive = C.drive_record(res)
        live = np.zeros((3, 6), dtype=int)
        live[0, 4] = 7
        live[2, 4] = 9
        first = C.live_settle(g, drive, live)
        assert first["written"] is True
        n = len(_records(g, res["composite"]))
        second = C.live_settle(g, drive, live)
        assert second["settled"] is True and second["written"] is False
        assert second["reason"] == C.S_ALREADY
        assert len(_records(g, res["composite"])) == n, (
            "a second settle appended a record")
        # even a diverging frame cannot un-settle or re-append
        third = C.live_settle(g, drive, f)
        assert third["reason"] == C.S_ALREADY
        assert len(_records(g, res["composite"])) == n


# ── structural: the writer is one function, and it compares live ─────────────

def _fn(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("%s not found" % name)


def _settled_stores(node):
    """Subscript STORES whose key is SETTLED_FIELD or the literal 'settled'."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Store):
            s = n.slice
            if ((isinstance(s, ast.Name) and s.id == "SETTLED_FIELD")
                    or (isinstance(s, ast.Constant) and s.value == "settled")):
                out.append(n)
    return out


def _calls(node, name):
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Call) and (
                (isinstance(n.func, ast.Name) and n.func.id == name)
                or (isinstance(n.func, ast.Attribute) and n.func.attr == name))]


class TestStructuralOneWriter:

    def test_only_live_settle_writes_the_settled_field(self):
        src = open(os.path.join(REPO, "engines", "egocentric", "composer.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        stores = _settled_stores(tree)
        inside = _settled_stores(_fn(tree, "live_settle"))
        assert len(stores) == 1 and len(inside) == 1, (
            "STRUCTURAL FALSIFIED: settled is written outside live_settle "
            "(%d store(s), %d inside)" % (len(stores), len(inside)))
        lsrc = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                    errors="replace").read()
        assert _settled_stores(ast.parse(lsrc)) == [], (
            "the loop must never write a settled field itself")

    def test_live_settle_calls_the_live_comparison(self):
        src = open(os.path.join(REPO, "engines", "egocentric", "composer.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        assert _calls(_fn(tree, "live_settle"), "settle_verdict"), (
            "STRUCTURAL FALSIFIED: the writer does not consult the live "
            "comparison")
        assert _calls(_fn(tree, "settle_verdict"), "divergence")
        sim = ast.get_source_segment(src, _fn(tree, "_simulate")) or ""
        assert "settle" not in sim.lower().replace("self-settlement", "") \
            .replace("never settles", ""), (
            "the simulation must know nothing of settling")
        assert not _calls(_fn(tree, "_attempt"), "live_settle")
        assert not _calls(_fn(tree, "compose_attempt"), "live_settle")

    def test_the_loop_seams_never_append_to_the_atoms_stream(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        tree = ast.parse(src)
        for name in ("_w3d_drive", "_w3d_continue", "_w3d_settle",
                     "_w3d_abort"):
            assert not _calls(_fn(tree, name), "append"), (
                "%s appends to a stream itself -- the settle's writer is "
                "composer.live_settle, the conflict's is the mint" % name)
        assert len(_calls(_fn(tree, "_w3d_settle"), "live_settle")) == 1, (
            "exactly ONE live_settle call site in the loop")
        others = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "live_settle"]
        assert len(others) == 1, "live_settle must have ONE loop call site"

    def test_record_result_settles_before_the_abort_router(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        i = src.index("def record_result(")
        body = src[i:src.find("\n    def ", i + 10)]
        assert "_w3d_settle(self" in body and "_w2b_abort(self" in body
        assert body.index("_w3d_settle(self") < body.index("_w2b_abort(self"), (
            "the composite seam must consume its stash BEFORE the router "
            "clears it")

    def test_cycle_continues_a_chain_and_drives_at_both_compose_seams(self):
        src = open(os.path.join(REPO, "cognitive_loop.py"), encoding="utf-8",
                   errors="replace").read()
        i = src.index("def cycle(")
        body = src[i:src.find("\n    def ", i + 10)]
        assert body.count("_w3d_drive(self") == 2, (
            "both compose seams (reference + abduced) must offer the drive")
        assert body.count("_w3d_continue(self") == 1
        assert body.count("_w2b_driven = {") == 2, (
            "the composite stashes live in the module-bottom helpers, not in "
            "cycle -- the scheduling gate's count must hold")
